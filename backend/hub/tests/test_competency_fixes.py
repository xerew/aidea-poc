"""Regression tests for the final-review findings on the competency rework."""
import importlib
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from hub.assignment_review import ReviewError, approve_submission, request_changes
from hub.competency import apply_course_completion, apply_missed_competency_changes
from hub.models import AssignmentSubmission, CompetencyChange, Enrollment, UserProfile

from .test_ai_review_models import make_assignment
from .test_competency_performance import add, make_course


class SafetyNetSameUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('cf_u', password='x')
        UserProfile.objects.create(user=self.user, competency_score=3)

    def missed_completion(self, title):
        course, (m1,) = make_course('advanced', modules=1)
        course.title = title
        course.save()
        quiz = add(m1, 'quiz')
        from hub.models import ResourceProgress
        ResourceProgress.objects.create(user=self.user, resource=quiz, completed_at=timezone.now(), quiz_score=1.0)
        return Enrollment.objects.create(user=self.user, course=course, progress_pct=100,
                                         completed_at=timezone.now() - timedelta(hours=3))

    def test_two_missed_courses_for_one_teacher_both_count(self):
        self.missed_completion('A')
        self.missed_completion('B')
        self.assertEqual(apply_missed_competency_changes(), 2)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.competency_score, 5)
        self.assertEqual(sorted((c.old_score, c.new_score) for c in CompetencyChange.objects.all()), [(3, 4), (4, 5)])

    def test_stale_user_object_uses_the_current_score(self):
        enrollment = self.missed_completion('A')
        stale = User.objects.select_related('profile').get(pk=self.user.pk)     # score 3 cached
        UserProfile.objects.filter(user=self.user).update(competency_score=5)   # changed meanwhile
        apply_course_completion(stale, enrollment, applied_by='nightly')
        change = CompetencyChange.objects.get()
        self.assertEqual((change.old_score, change.reason['teacher_level']), (5, 2))


class FirstDecisionRaceTests(TestCase):
    def setUp(self):
        self.course, _, self.activity, self.resource = make_assignment()
        self.learner = User.objects.create_user('cf_l', password='x')
        UserProfile.objects.create(user=self.learner)
        Enrollment.objects.create(user=self.learner, course=self.course)
        self.reviewer = User.objects.create_user('cf_r', password='x')
        self.sub = AssignmentSubmission.objects.create(user=self.learner, lesson=self.activity,
                                                       resource=self.resource, text='t')

    def test_a_stale_reviewer_cannot_overwrite_an_ai_approval(self):
        stale = AssignmentSubmission.objects.get(pk=self.sub.pk)     # reviewer opened it while pending
        approve_submission(self.sub, reviewer=None)                  # AI auto-approves first
        with self.assertRaises(ReviewError):
            request_changes(stale, self.reviewer, 'Needs more')
        self.sub.refresh_from_db()
        self.assertEqual((self.sub.status, self.sub.first_review_status), ('approved', 'approved'))

    def test_a_stale_approval_of_an_already_reviewed_submission_is_refused(self):
        stale = AssignmentSubmission.objects.get(pk=self.sub.pk)
        request_changes(self.sub, self.reviewer, 'Needs more')
        with self.assertRaises(ReviewError):
            approve_submission(stale, self.reviewer)
        self.sub.refresh_from_db()
        self.assertEqual((self.sub.status, self.sub.first_review_status), ('changes_requested', 'changes_requested'))


class BackfillTests(TestCase):
    def test_resubmitted_after_changes_counts_as_changes_requested(self):
        migration = importlib.import_module('hub.migrations.0069_competency_settings_data')
        course, _, activity, resource = make_assignment()
        users = [User.objects.create_user(f'cf_b{i}', password='x') for i in range(4)]
        now = timezone.now()
        rows = {
            'approved': AssignmentSubmission.objects.create(user=users[0], lesson=activity, resource=resource,
                                                            status='approved', reviewed_at=now),
            'changes': AssignmentSubmission.objects.create(user=users[1], lesson=activity, resource=resource,
                                                           status='changes_requested', reviewed_at=now),
            'resubmitted': AssignmentSubmission.objects.create(user=users[2], lesson=activity, resource=resource,
                                                               status='pending', reviewed_at=now),
            'never': AssignmentSubmission.objects.create(user=users[3], lesson=activity, resource=resource,
                                                         status='pending'),
        }
        migration.backfill_first_reviews(AssignmentSubmission)
        got = {k: AssignmentSubmission.objects.get(pk=v.pk).first_review_status for k, v in rows.items()}
        self.assertEqual(got, {'approved': 'approved', 'changes': 'changes_requested',
                               'resubmitted': 'changes_requested', 'never': ''})


class RecomputeAfterCommitTests(TestCase):
    def test_recommendations_recompute_waits_for_commit(self):
        user = User.objects.create_user('cf_c', password='x')
        UserProfile.objects.create(user=user, competency_score=3)
        course, (m1,) = make_course('advanced', modules=1)
        from hub.models import ResourceProgress
        ResourceProgress.objects.create(user=user, resource=add(m1, 'quiz'), completed_at=timezone.now(), quiz_score=1.0)
        enrollment = Enrollment.objects.create(user=user, course=course, completed_at=timezone.now())
        with mock.patch('hub.tasks.compute_user_recommendations.delay') as delay:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                apply_course_completion(user, enrollment)
            self.assertFalse(delay.called)            # not before the transaction commits
            for callback in callbacks:
                callback()
            delay.assert_called_once_with(user.id)
