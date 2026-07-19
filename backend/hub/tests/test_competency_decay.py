from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase  # noqa: F401  (used by later task's classes)

from hub.models import (
    Course,
    Enrollment,
    LearnerActivityConfig,
    LearningPillar,
    UserProfile,
)


def _make_course_with_lesson(pillar_slug='pdec2', duration_minutes=10):
    from hub.models import Lesson, Module
    pillar = LearningPillar.objects.create(name='P2', slug=pillar_slug, order=2)
    course = Course.objects.create(
        title=f'C-{pillar_slug}', pillar=pillar, level='beginner',
        duration_hours=1, is_published=True,
    )
    module = Module.objects.create(course=course, title='M', order=1)
    lesson = Lesson.objects.create(
        module=module, title='L', lesson_type='text', order=1,
        is_required=True, duration_minutes=duration_minutes,
    )
    return course, lesson


def _make_paths():
    from hub.models import LearningPath
    for slug, lo, hi in [
        ('beginner-foundations', 0, 2),
        ('intermediate-growth', 3, 4),
        ('advanced-integration', 5, 6),
    ]:
        LearningPath.objects.update_or_create(
            slug=slug,
            defaults={'name': slug, 'competency_min': lo, 'competency_max': hi},
        )


class ApplyCompetencyDeltaTests(TestCase):
    def setUp(self):
        _make_paths()
        self.user = User.objects.create_user(username='delta_u', password='pass12345')
        self.profile = UserProfile.objects.create(
            user=self.user, user_type=UserProfile.UserType.TEACHER, competency_score=3,
        )

    def test_clamps_floor_and_cap(self):
        from hub.competency import apply_competency_delta
        self.assertEqual(apply_competency_delta(self.user, -10), 0)
        self.assertEqual(apply_competency_delta(self.user, +10), 6)

    def test_band_drop_reassigns_path(self):
        from hub.competency import apply_competency_delta
        from hub.models import UserLearningPath
        apply_competency_delta(self.user, -1)  # 3 -> 2: intermediate -> beginner
        self.assertEqual(
            UserLearningPath.objects.get(user=self.user).path.slug,
            'beginner-foundations',
        )

    def test_band_climb_reassigns_path(self):
        from hub.competency import apply_competency_delta
        from hub.models import UserLearningPath
        apply_competency_delta(self.user, +2)  # 3 -> 5: intermediate -> advanced
        self.assertEqual(
            UserLearningPath.objects.get(user=self.user).path.slug,
            'advanced-integration',
        )

    def test_zero_delta_is_noop(self):
        from hub.competency import apply_competency_delta
        from hub.models import UserLearningPath
        apply_competency_delta(self.user, 0)
        self.assertFalse(UserLearningPath.objects.filter(user=self.user).exists())

    def test_within_band_change_keeps_path(self):
        from hub.competency import apply_competency_delta
        from hub.models import UserLearningPath
        apply_competency_delta(self.user, +1)  # 3 -> 4, still intermediate
        self.assertFalse(UserLearningPath.objects.filter(user=self.user).exists())


class CourseCompletionDeltaTests(TestCase):
    def setUp(self):
        _make_paths()
        self.user = User.objects.create_user(username='ccd_u', password='pass12345')
        UserProfile.objects.create(
            user=self.user, user_type=UserProfile.UserType.TEACHER, competency_score=3,
        )

    def _progress(self, lesson, seconds=None, quiz_score=None):
        from hub.models import LessonProgress
        return LessonProgress.objects.create(
            user=self.user, lesson=lesson,
            time_spent_seconds=seconds, quiz_score=quiz_score,
            completed_at=timezone.now(),
        )

    def test_default_delta_is_one(self):
        from hub.competency import course_completion_delta
        course, lesson = _make_course_with_lesson('ccd1')
        self._progress(lesson, seconds=600)  # 10 min for a 10-min lesson
        self.assertEqual(course_completion_delta(self.user, course), 1)

    def test_slow_completion_reduces_delta(self):
        from hub.competency import course_completion_delta
        course, lesson = _make_course_with_lesson('ccd2', duration_minutes=10)
        self._progress(lesson, seconds=4 * 600)  # 40 min: ratio 4 > 3.0
        self.assertEqual(course_completion_delta(self.user, course), 0)

    def test_negative_fail_weight_gives_negative_delta(self):
        from hub.competency import course_completion_delta
        from hub.models import Lesson, Module
        config = LearnerActivityConfig.get()
        config.quiz_affects_competency = True
        config.quiz_weight_fail = -1.0
        config.save()
        course, lesson = _make_course_with_lesson('ccd3')
        quiz = Lesson.objects.create(
            module=Module.objects.get(course=course), title='Q', lesson_type='quiz',
            order=2, is_required=True,
        )
        self._progress(lesson, seconds=600)
        self._progress(quiz, quiz_score=0.2)  # below 0.7 threshold
        self.assertEqual(course_completion_delta(self.user, course), -1)

    def test_decay_disabled_skips_slow_penalty(self):
        from hub.competency import course_completion_delta
        config = LearnerActivityConfig.get()
        config.decay_enabled = False
        config.save()
        course, lesson = _make_course_with_lesson('ccd4', duration_minutes=10)
        self._progress(lesson, seconds=4 * 600)
        self.assertEqual(course_completion_delta(self.user, course), 1)


class DecayConfigTests(TestCase):
    def test_new_config_defaults(self):
        config = LearnerActivityConfig.get()
        self.assertTrue(config.decay_enabled)
        self.assertEqual(config.slow_ratio_threshold, 3.0)
        self.assertEqual(config.slow_penalty, 1)
        self.assertEqual(config.idle_decay_days, 30)
        self.assertEqual(config.idle_decay_points, 1)

    def test_enrollment_decay_stamp_default_null(self):
        user = User.objects.create_user(username='stamp_u', password='pass12345')
        UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P', slug='pdec', order=1)
        course = Course.objects.create(
            title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        e = Enrollment.objects.create(user=user, course=course)
        self.assertIsNone(e.decay_applied_at)
        e.decay_applied_at = timezone.now() - timedelta(days=1)
        e.save(update_fields=['decay_applied_at'])
