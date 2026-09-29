from django.test import TestCase

from hub.models import Course, LearningPillar, Lesson, Module, Resource


class ResourceModelTest(TestCase):
    def setUp(self):
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        course = Course.objects.create(title='C', pillar=pillar)
        self.module = Module.objects.create(title='M', course=course, order=1)
        # Lesson is the (pre-rename) Activity.
        self.activity = Lesson.objects.create(module=self.module, title='A', order=1)

    def test_create_resource(self):
        r = Resource.objects.create(
            activity=self.activity, type='text', order=1, content='hello',
        )
        self.assertEqual(self.activity.resources.count(), 1)
        self.assertTrue(r.is_required)
        self.assertEqual(r.type, 'text')

    def test_resources_ordered(self):
        Resource.objects.create(activity=self.activity, type='video', order=2, url='v')
        Resource.objects.create(activity=self.activity, type='text', order=1, content='t')
        types = list(self.activity.resources.values_list('type', flat=True))
        self.assertEqual(types, ['text', 'video'])
