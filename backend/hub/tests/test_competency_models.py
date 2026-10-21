from django.contrib.auth.models import User
from django.test import TestCase

from hub.assignment_review import approve_submission, reopen_submission, request_changes
from hub.models import (
    AssignmentSubmission,
    CompetencyChange,
    Enrollment,
    LearnerActivityConfig,
    UserProfile,
)

from .test_ai_review_models import make_assignment


class CompetencyModelTests(TestCase):
    def setUp(self):
        self.course, _, self.activity, self.resource = make_assignment()
        self.learner = User.objects.create_user('cm_l', password='x', email='cm@example.org')
        UserProfile.objects.create(user=self.learner)
        Enrollment.objects.create(user=self.learner, course=self.course)
        self.reviewer = User.objects.create_user('cm_r', password='x')

    def submit(self):
        sub, _ = AssignmentSubmission.objects.update_or_create(
            user=self.learner, lesson=self.activity,
            defaults={'resource': self.resource, 'text': 't', 'status': 'pending'})
        return sub

    def test_config_switch_defaults(self):
        config = LearnerActivityConfig.get()
        self.assertEqual((config.slow_penalty_enabled, config.idle_decay_enabled), (True, False))

    def test_first_review_approved_directly(self):
        sub = self.submit()
        approve_submission(sub, self.reviewer)
        sub.refresh_from_db()
        self.assertEqual((sub.status, sub.first_review_status), ('approved', 'approved'))

    def test_first_review_is_never_overwritten(self):
        sub = self.submit()
        request_changes(sub, self.reviewer, 'Add detail')
        sub = self.submit()                                  # learner resubmits
        approve_submission(sub, self.reviewer)
        reopen_submission(sub)
        sub.refresh_from_db()
        self.assertEqual((sub.status, sub.first_review_status), ('pending', 'changes_requested'))

    def test_enrollment_marker_default(self):
        self.assertIsNone(Enrollment.objects.get(user=self.learner).competency_applied_at)

    def test_change_record(self):
        change = CompetencyChange.objects.create(user=self.learner, course=self.course, old_score=3, new_score=4,
                                                 delta=1, reason={'rule': 'performance'})
        self.assertEqual(list(self.learner.competency_changes.all()), [change])
        self.assertEqual(change.reason['rule'], 'performance')
