from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from hub.competency import (
    apply_competency_delta,
    apply_missed_competency_changes,
    course_completion_change,
    course_performance,
    performance_delta,
)
from hub.models import (
    Activity,
    AssignmentSubmission,
    CompetencyChange,
    Course,
    Enrollment,
    LearnerActivityConfig,
    LearningPillar,
    Module,
    Resource,
    ResourceProgress,
    UserProfile,
)

QUIZ = [{'question': 'Q', 'options': [{'text': 'A', 'is_correct': True}, {'text': 'B', 'is_correct': False}]}]


def make_course(level='intermediate', modules=2):
    pillar = LearningPillar.objects.get_or_create(slug='p-cp', defaults={'name': 'P', 'order': 1})[0]
    course = Course.objects.create(title=f'{level} course', pillar=pillar, level=level, duration_hours=1,
                                   is_published=True)
    return course, [Module.objects.create(course=course, title=f'M{i}', order=i) for i in range(1, modules + 1)]


def add(module, kind, order=1, minutes=0):
    activity = Activity.objects.create(module=module, title=f'{kind} {order}', order=order, duration_minutes=minutes)
    return Resource.objects.create(activity=activity, type=kind, order=1, quiz_data=QUIZ if kind == 'quiz' else [])


class Base(TestCase):
    score = 3   # intermediate

    def setUp(self):
        self.user = User.objects.create_user('cp_t', password='x')
        UserProfile.objects.create(user=self.user, competency_score=self.score)

    def done(self, resource, score=None, seconds=None):
        return ResourceProgress.objects.create(user=self.user, resource=resource, completed_at=timezone.now(),
                                               quiz_score=score, time_spent_seconds=seconds)

    def assignment(self, resource, first):
        AssignmentSubmission.objects.create(user=self.user, lesson=resource.activity, resource=resource, text='t',
                                            status='approved', first_review_status=first)
        self.done(resource)


class PerformanceDeltaTableTests(TestCase):
    def test_every_cell(self):
        cells = {(2, True): 2, (2, False): 0, (1, True): 1, (1, False): 0, (0, True): 1, (0, False): 0,
                 (-1, True): 0, (-1, False): -1, (-2, True): 0, (-2, False): -1}
        for (gap, passed), expected in cells.items():
            self.assertEqual(performance_delta(passed, gap), expected, (gap, passed))


class CoursePerformanceTests(Base):
    def test_modules_count_equally(self):
        course, (m1, m2) = make_course()
        for i in range(3):
            self.done(add(m1, 'quiz', order=i + 1), score=1.0)
        self.assignment(add(m2, 'assignment'), 'changes_requested')
        self.assertAlmostEqual(course_performance(self.user, course), 0.5)

    def test_assignment_counts_by_first_review(self):
        course, (m1, _) = make_course()
        self.assignment(add(m1, 'assignment'), 'approved')
        self.assertEqual(course_performance(self.user, course), 1.0)

    def test_h5p_score_counts(self):
        course, (m1, _) = make_course()
        self.done(add(m1, 'h5p'), score=0.6)
        self.assertAlmostEqual(course_performance(self.user, course), 0.6)

    def test_unscored_and_unfinished_items_are_ignored(self):
        course, (m1, m2) = make_course()
        self.done(add(m1, 'quiz'), score=0.8)
        self.done(add(m1, 'h5p', order=2))          # reported no score
        self.done(add(m1, 'quiz', order=3))         # completed without answers
        add(m2, 'quiz')                             # never done
        self.done(add(m2, 'text', order=2))
        self.assertAlmostEqual(course_performance(self.user, course), 0.8)

    def test_no_scored_items(self):
        course, (m1, _) = make_course()
        self.done(add(m1, 'text'))
        self.assertIsNone(course_performance(self.user, course))

    def test_first_attempt_counts(self):
        from hub.completion import _mark_resource_complete
        course, (m1, _) = make_course()
        quiz = add(m1, 'quiz')
        _mark_resource_complete(self.user, quiz, quiz_answers_raw=[1])   # wrong first
        _mark_resource_complete(self.user, quiz, quiz_answers_raw=[0])   # right on a retake
        self.assertEqual(course_performance(self.user, course), 0.0)


class CourseCompletionChangeTests(Base):
    def change(self, level, score=None):
        course, (m1, _) = make_course(level)
        self.done(add(m1, 'quiz'), score=score) if score is not None else self.done(add(m1, 'text'))
        return course_completion_change(self.user, course)

    def test_harder_course_passed(self):
        delta, reason = self.change('advanced', 0.9)
        self.assertEqual((delta, reason['rule'], reason['gap'], reason['passed']), (1, 'performance', 1, True))

    def test_harder_course_failed_is_zero(self):
        self.assertEqual(self.change('advanced', 0.3)[0], 0)

    def test_same_level(self):
        self.assertEqual(self.change('intermediate', 0.7)[0], 1)
        self.assertEqual(self.change('intermediate', 0.5)[0], 0)

    def test_easier_course(self):
        self.assertEqual(self.change('beginner', 0.9)[0], 0)
        delta, reason = self.change('beginner', 0.4)
        self.assertEqual((delta, reason['gap'], reason['performance']), (-1, -1, 0.4))

    def test_no_scored_items_gives_one(self):
        delta, reason = self.change('beginner')
        self.assertEqual((delta, reason['rule'], reason['performance']), (1, 'completion', None))

    def test_threshold_comes_from_settings(self):
        config = LearnerActivityConfig.get()
        config.quiz_pass_threshold = 0.9
        config.save()
        self.assertEqual(self.change('intermediate', 0.8)[0], 0)

    def test_slow_penalty_has_its_own_switch(self):
        course, (m1, _) = make_course('beginner')
        self.done(add(m1, 'text', minutes=10), seconds=40 * 60)       # 4× the planned time
        delta, reason = course_completion_change(self.user, course)
        self.assertEqual((delta, reason['slow_penalty']), (0, 1))
        config = LearnerActivityConfig.get()
        config.slow_penalty_enabled = False
        config.save()
        self.assertEqual(course_completion_change(self.user, course)[0], 1)


class TwoLevelsHarderTests(Base):
    score = 0   # beginner

    def test_two_levels_harder_passed(self):
        course, (m1, _) = make_course('advanced')
        self.done(add(m1, 'quiz'), score=1.0)
        self.assertEqual(course_completion_change(self.user, course)[0], 2)


class ChangeRecordTests(Base):
    def test_change_is_recorded_with_reason(self):
        course, _ = make_course()
        apply_competency_delta(self.user, 1, recompute=False, course=course, reason={'rule': 'performance'})
        change = CompetencyChange.objects.get()
        self.assertEqual((change.old_score, change.new_score, change.delta, change.course, change.reason['rule']),
                         (3, 4, 1, course, 'performance'))

    def test_clamped_change_records_nothing(self):
        self.user.profile.competency_score = 6
        self.user.profile.save()
        apply_competency_delta(self.user, 2, recompute=False)
        self.assertFalse(CompetencyChange.objects.exists())

    def test_completing_a_course_records_the_rule(self):
        from hub.completion import record_resource_completion
        course, (m1,) = make_course('advanced', modules=1)
        quiz = add(m1, 'quiz')
        enrollment = Enrollment.objects.create(user=self.user, course=course)
        record_resource_completion(self.user, enrollment, quiz, quiz_answers_raw=[0])
        self.user.profile.refresh_from_db()
        change = CompetencyChange.objects.get()
        self.assertEqual((self.user.profile.competency_score, change.reason['rule'], change.course),
                         (4, 'performance', course))


class NightlySafetyNetTests(Base):
    def setUp(self):
        super().setUp()
        self.course, (m1,) = make_course('advanced', modules=1)
        self.quiz = add(m1, 'quiz')
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)

    def complete(self):
        from hub.completion import record_resource_completion
        record_resource_completion(self.user, self.enrollment, self.quiz, quiz_answers_raw=[0])
        self.enrollment.refresh_from_db()
        self.user.profile.refresh_from_db()

    def age(self, **delta):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(completed_at=timezone.now() - timedelta(**delta))

    def test_completion_sets_the_marker(self):
        self.complete()
        self.assertIsNotNone(self.enrollment.competency_applied_at)
        self.assertEqual(apply_missed_competency_changes(), 0)

    def test_failure_on_completion_is_applied_once_by_the_nightly_check(self):
        with mock.patch('hub.competency.course_completion_change', side_effect=RuntimeError('boom')):
            self.complete()                                   # no exception reaches the learner
        self.assertIsNotNone(self.enrollment.completed_at)
        self.assertIsNone(self.enrollment.competency_applied_at)
        self.assertEqual(self.user.profile.competency_score, 3)
        self.age(hours=2)
        self.assertEqual(apply_missed_competency_changes(), 1)
        self.user.profile.refresh_from_db()
        change = CompetencyChange.objects.get()
        self.assertEqual((self.user.profile.competency_score, change.reason['applied_by']), (4, 'nightly'))
        self.assertEqual(apply_missed_competency_changes(), 0)  # a second night does nothing
        self.assertEqual(CompetencyChange.objects.count(), 1)

    def test_recent_completions_are_left_alone(self):
        with mock.patch('hub.competency.course_completion_change', side_effect=RuntimeError('boom')):
            self.complete()
        self.age(minutes=10)
        self.assertEqual(apply_missed_competency_changes(), 0)

    def test_clamped_change_still_sets_the_marker(self):
        self.user.profile.competency_score = 6
        self.user.profile.save()
        self.complete()                                       # advanced vs advanced, passed: +1 -> still 6
        self.assertIsNotNone(self.enrollment.competency_applied_at)
        self.assertFalse(CompetencyChange.objects.exists())

    def test_nightly_task_runs_the_safety_net(self):
        from hub.tasks import nightly_competency_check
        with mock.patch('hub.competency.course_completion_change', side_effect=RuntimeError('boom')):
            self.complete()
        self.age(hours=2)
        nightly_competency_check()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.competency_score, 4)
