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
