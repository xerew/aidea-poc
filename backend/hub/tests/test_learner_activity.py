from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import (
    Course,
    Enrollment,
    LearningPillar,
    Lesson,
    LessonProgress,
    Module,
    UserProfile,
)


class LessonProgressFieldsTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='lp1', password='pass')
        pillar = LearningPillar.objects.create(name='P1', slug='p1', description='')
        course = Course.objects.create(title='C1', pillar=pillar)
        module = Module.objects.create(title='M1', course=course, order=1)
        lesson = Lesson.objects.create(title='L1', module=module, order=1, is_required=True)
        self.lp = LessonProgress.objects.create(user=user, lesson=lesson)

    def test_time_spent_seconds_null_by_default(self):
        self.assertIsNone(self.lp.time_spent_seconds)

    def test_quiz_score_null_by_default(self):
        self.assertIsNone(self.lp.quiz_score)

    def test_quiz_answers_empty_by_default(self):
        self.assertEqual(self.lp.quiz_answers, [])

    def test_engagement_data_empty_by_default(self):
        self.assertEqual(self.lp.engagement_data, {})

    def test_completed_at_null_by_default(self):
        self.assertIsNone(self.lp.completed_at)


class LessonSessionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ls1', password='pass')
        pillar = LearningPillar.objects.create(name='P2', slug='p2', description='')
        course = Course.objects.create(title='C2', pillar=pillar)
        module = Module.objects.create(title='M2', course=course, order=1)
        self.lesson = Lesson.objects.create(title='L2', module=module, order=1, is_required=True)

    def test_session_created_with_started_at(self):
        from hub.models.activity import LessonSession
        session = LessonSession.objects.create(user=self.user, lesson=self.lesson)
        self.assertIsNotNone(session.started_at)

    def test_multiple_sessions_allowed_for_same_user_lesson(self):
        from hub.models.activity import LessonSession
        LessonSession.objects.create(user=self.user, lesson=self.lesson)
        LessonSession.objects.create(user=self.user, lesson=self.lesson)
        self.assertEqual(
            LessonSession.objects.filter(user=self.user, lesson=self.lesson).count(), 2
        )


class LearnerActivityConfigTest(TestCase):
    def test_get_creates_singleton(self):
        from hub.models.activity import LearnerActivityConfig
        config = LearnerActivityConfig.get()
        self.assertEqual(config.pk, 1)

    def test_get_returns_same_instance(self):
        from hub.models.activity import LearnerActivityConfig
        config1 = LearnerActivityConfig.get()
        config2 = LearnerActivityConfig.get()
        self.assertEqual(LearnerActivityConfig.objects.count(), 1)
        self.assertEqual(config1.pk, config2.pk)

    def test_defaults(self):
        from hub.models.activity import LearnerActivityConfig
        config = LearnerActivityConfig.get()
        self.assertFalse(config.quiz_affects_competency)
        self.assertAlmostEqual(config.quiz_pass_threshold, 0.7)
        self.assertAlmostEqual(config.quiz_weight_pass, 1.0)
        self.assertAlmostEqual(config.quiz_weight_fail, 0.5)

    def test_save_enforces_singleton(self):
        from hub.models.activity import LearnerActivityConfig
        config = LearnerActivityConfig.get()
        config.quiz_affects_competency = True
        config.save()
        self.assertEqual(LearnerActivityConfig.objects.count(), 1)
        self.assertEqual(config.pk, 1)


class LessonSessionOnOpenTest(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.user = User.objects.create_user(username='lo1', password='pass')
        from hub.models import UserProfile
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P3', slug='p3', description='')
        self.course = Course.objects.create(title='C3', pillar=pillar, is_published=True)
        module = Module.objects.create(title='M3', course=self.course, order=1)
        self.lesson = Lesson.objects.create(title='L3', module=module, order=1, is_required=True)
        from hub.models import Enrollment
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_session_created_on_lesson_get(self):
        from hub.models.activity import LessonSession
        self.client.get(f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/')
        self.assertEqual(
            LessonSession.objects.filter(user=self.user, lesson=self.lesson).count(), 1
        )

    def test_multiple_opens_create_multiple_sessions(self):
        from hub.models.activity import LessonSession
        self.client.get(f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/')
        self.client.get(f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/')
        self.assertEqual(
            LessonSession.objects.filter(user=self.user, lesson=self.lesson).count(), 2
        )


class EngagementTrackingTest(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.user = User.objects.create_user(username='et1', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P4', slug='p4', description='')
        self.course = Course.objects.create(title='C4', pillar=pillar, is_published=True)
        self.module = Module.objects.create(title='M4', course=self.course, order=1)
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _lesson(self, title, lesson_type='text', quiz_data=None):
        return Lesson.objects.create(
            title=title,
            module=self.module,
            order=Lesson.objects.filter(module=self.module).count() + 1,
            is_required=True,
            lesson_type=lesson_type,
            quiz_data=quiz_data or [],
        )

    def test_time_spent_computed_when_session_exists(self):
        lesson = self._lesson('T1')
        self.client.get(f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/', {}, format='json'
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertIsNotNone(lp.time_spent_seconds)
        self.assertGreaterEqual(lp.time_spent_seconds, 0)

    def test_time_spent_null_without_session(self):
        lesson = self._lesson('T2')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/', {}, format='json'
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertIsNone(lp.time_spent_seconds)

    def test_completed_at_set_on_first_complete(self):
        lesson = self._lesson('T3')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/', {}, format='json'
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertIsNotNone(lp.completed_at)

    def test_quiz_score_computed_server_side(self):
        quiz_data = [
            {'question': 'Q1', 'options': [
                {'text': 'A', 'is_correct': False},
                {'text': 'B', 'is_correct': True},
            ]},
            {'question': 'Q2', 'options': [
                {'text': 'C', 'is_correct': True},
                {'text': 'D', 'is_correct': False},
            ]},
        ]
        lesson = self._lesson('Q1', lesson_type='quiz', quiz_data=quiz_data)
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'quiz_answers': [1, 0]},
            format='json',
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertAlmostEqual(lp.quiz_score, 1.0)
        self.assertEqual(lp.quiz_answers, [True, True])

    def test_quiz_score_partial(self):
        quiz_data = [
            {'question': 'Q1', 'options': [
                {'text': 'A', 'is_correct': False},
                {'text': 'B', 'is_correct': True},
            ]},
            {'question': 'Q2', 'options': [
                {'text': 'C', 'is_correct': True},
                {'text': 'D', 'is_correct': False},
            ]},
        ]
        lesson = self._lesson('Q2', lesson_type='quiz', quiz_data=quiz_data)
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'quiz_answers': [0, 0]},
            format='json',
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertAlmostEqual(lp.quiz_score, 0.5)
        self.assertEqual(lp.quiz_answers, [False, True])

    def test_text_scroll_pct_stored(self):
        lesson = self._lesson('T4', lesson_type='text')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'engagement_data': {'scroll_pct': 85}},
            format='json',
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertEqual(lp.engagement_data.get('scroll_pct'), 85)

    # updated fully in assignment-review Task 3
    def test_assignment_word_count_derived(self):
        # Assignments no longer complete via this endpoint; word-count
        # derivation is exercised through the review-approval flow (Task 3).
        lesson = self._lesson('A1', lesson_type='assignment')
        res = self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'engagement_data': {'submission': 'hello world this is a test'}},
            format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_engagement_not_overwritten_on_repeat_complete(self):
        lesson = self._lesson('T5', lesson_type='text')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'engagement_data': {'scroll_pct': 50}},
            format='json',
        )
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'engagement_data': {'scroll_pct': 99}},
            format='json',
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertEqual(lp.engagement_data.get('scroll_pct'), 50)


class CompetencyWeightingTest(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient

        from hub.models.activity import LearnerActivityConfig
        self.user = User.objects.create_user(username='cw1', password='pass')
        self.profile = UserProfile.objects.create(
            user=self.user,
            user_type=UserProfile.UserType.TEACHER,
            competency_score=0,
            onboarding_completed=True,
        )
        pillar = LearningPillar.objects.create(name='P5', slug='p5', description='')
        self.course = Course.objects.create(title='C5', pillar=pillar)
        module = Module.objects.create(title='M5', course=self.course, order=1)
        self.required_lesson = Lesson.objects.create(
            title='RL', module=module, order=1, is_required=True, lesson_type='text',
        )
        self.quiz_lesson = Lesson.objects.create(
            title='QL',
            module=module,
            order=2,
            is_required=False,
            lesson_type='quiz',
            quiz_data=[{
                'question': 'Q',
                'options': [
                    {'text': 'Right', 'is_correct': True},
                    {'text': 'Wrong', 'is_correct': False},
                ],
            }],
        )
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.config = LearnerActivityConfig.get()

    def _complete_required(self):
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.required_lesson.pk}/complete/',
            {}, format='json',
        )

    def _complete_quiz(self, answers):
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.quiz_lesson.pk}/complete/',
            {'quiz_answers': answers},
            format='json',
        )

    def test_toggle_off_always_gives_increment_of_1(self):
        self.config.quiz_affects_competency = False
        self.config.save()
        self._complete_required()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 1)

    def test_toggle_on_pass_gives_full_increment(self):
        self.config.quiz_affects_competency = True
        self.config.quiz_pass_threshold = 0.7
        self.config.quiz_weight_pass = 1.0
        self.config.save()
        self._complete_quiz([0])  # correct answer → score 1.0
        self._complete_required()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 1)

    def test_toggle_on_fail_gives_no_increment(self):
        self.config.quiz_affects_competency = True
        self.config.quiz_pass_threshold = 0.7
        self.config.quiz_weight_fail = 0.5  # int(0.5) = 0 → no increment
        self.config.save()
        self._complete_quiz([1])  # wrong answer → score 0.0
        self._complete_required()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 0)

    def test_toggle_on_no_quizzes_falls_back_to_full_increment(self):
        pillar = LearningPillar.objects.create(name='P6', slug='p6', description='')
        course2 = Course.objects.create(title='C6', pillar=pillar)
        module2 = Module.objects.create(title='M6', course=course2, order=1)
        lesson2 = Lesson.objects.create(
            title='L6', module=module2, order=1, is_required=True, lesson_type='text',
        )
        Enrollment.objects.create(user=self.user, course=course2)
        self.config.quiz_affects_competency = True
        self.config.save()
        self.client.post(
            f'/api/courses/{course2.pk}/lessons/{lesson2.pk}/complete/', {}, format='json',
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 1)
