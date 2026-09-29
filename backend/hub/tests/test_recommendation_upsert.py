from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import Course, LearningPillar
from hub.models.recommendations import CourseRecommendation


class RecommendationUpsertTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='x')
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        self.course = Course.objects.create(title='C', pillar=pillar, is_published=True)

    def test_upsert_does_not_duplicate_across_sources(self):
        """A course already recommended by one pass (cf) must not raise when the
        other pass (personal) selects it too — it upserts to a single row."""
        from hub.tasks import _upsert_recommendation

        CourseRecommendation.objects.create(
            user=self.user, course=self.course, score=0.5, reason='cf', source='cf',
        )
        # Would raise IntegrityError with a plain create():
        _upsert_recommendation(self.user, self.course.id, 0.9, 'personal', 'personal')

        recs = CourseRecommendation.objects.filter(user=self.user, course=self.course)
        self.assertEqual(recs.count(), 1)
        self.assertEqual(recs.first().source, 'personal')
        self.assertEqual(recs.first().score, 0.9)
