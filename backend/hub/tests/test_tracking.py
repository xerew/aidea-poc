import uuid

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from hub.models import (
    Activity,
    Course,
    LearnerActivityConfig,
    LearningEvent,
    LearningPillar,
    Module,
    Resource,
    ResourceVisit,
)


class TrackingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tm_user', password='pass12345')
        pillar = LearningPillar.objects.create(name='P', slug='p-tm', order=1)
        self.course = Course.objects.create(
            title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        self.module = Module.objects.create(course=self.course, title='M', order=1)
        self.activity = Activity.objects.create(module=self.module, title='A', order=1)
        self.resource = Resource.objects.create(activity=self.activity, type='text', order=1)

    def _visit(self, key):
        now = timezone.now()
        return ResourceVisit.objects.create(
            user=self.user, resource=self.resource, activity=self.activity,
            module=self.module, course=self.course, visit_key=key, page_key=uuid.uuid4(),
            started_at=now, last_seen_at=now,
        )

    def test_visit_defaults(self):
        v = self._visit(uuid.uuid4())
        self.assertEqual((v.active_seconds, v.visible_seconds), (0, 0))
        self.assertFalse(v.completed_during)
        self.assertEqual(v.media_progress, {})

    def test_visit_key_unique_per_user(self):
        key = uuid.uuid4()
        self._visit(key)
        with self.assertRaises(IntegrityError):
            self._visit(key)

    def test_event_key_unique_per_user(self):
        key = uuid.uuid4()
        fields = dict(
            user=self.user, resource=self.resource, course=self.course, event_key=key,
            event_type=LearningEvent.Type.PDF_OPEN, occurred_at=timezone.now(),
        )
        LearningEvent.objects.create(**fields)
        with self.assertRaises(IntegrityError):
            LearningEvent.objects.create(**fields)

    def test_tracking_enabled_by_default(self):
        self.assertTrue(LearnerActivityConfig.get().tracking_enabled)
