from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from hub.models import (
    Activity,
    Course,
    LearningPillar,
    Module,
    Resource,
    ResourceProgress,
)


class ResourceProgressModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='x')
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        course = Course.objects.create(title='C', pillar=pillar)
        module = Module.objects.create(title='M', course=course, order=1)
        activity = Activity.objects.create(module=module, title='A', order=1)
        self.resource = Resource.objects.create(activity=activity, type='text', order=1)

    def test_create_and_uniqueness(self):
        ResourceProgress.objects.create(user=self.user, resource=self.resource)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ResourceProgress.objects.create(user=self.user, resource=self.resource)
