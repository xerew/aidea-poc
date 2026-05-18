from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import UserProfile
from hub.models.recommendations import CourseRecommendation
from hub.tasks import compute_user_recommendations


class ComputeUserRecommendationsSQLiteTest(TestCase):
    """Tasks exit early on SQLite — verify no crash and no writes."""

    def setUp(self):
        self.user = User.objects.create_user(username='trec', password='pass')
        UserProfile.objects.create(
            user=self.user,
            user_type=UserProfile.UserType.TEACHER,
            onboarding_completed=True,
            subject_area='stem',
            teaching_level='secondary',
            competency_score=3,
        )

    def test_no_crash_on_sqlite(self):
        compute_user_recommendations(self.user.id)

    def test_no_recommendations_written_on_sqlite(self):
        compute_user_recommendations(self.user.id)
        self.assertEqual(
            CourseRecommendation.objects.filter(user=self.user).count(), 0
        )
