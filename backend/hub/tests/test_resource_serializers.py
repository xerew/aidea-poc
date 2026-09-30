from django.test import TestCase

from hub.models import Activity, Course, LearningPillar, Module, Resource
from hub.serializers import LessonLearnDetailSerializer, LessonSerializer


class ResourceSerializerTest(TestCase):
    def setUp(self):
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        course = Course.objects.create(title='C', pillar=pillar)
        module = Module.objects.create(title='M', course=course, order=1)
        self.activity = Activity.objects.create(module=module, title='A', order=1)
        Resource.objects.create(activity=self.activity, type='text', order=1, content='hi')
        Resource.objects.create(
            activity=self.activity, type='quiz', order=2,
            quiz_data=[{'question': 'Q', 'options': [
                {'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': False}]}],
        )

    def test_authoring_serializer_includes_resources_with_answers(self):
        data = LessonSerializer(self.activity).data
        self.assertEqual(len(data['resources']), 2)
        quiz = next(r for r in data['resources'] if r['type'] == 'quiz')
        # authoring keeps is_correct
        self.assertIn('is_correct', quiz['quiz_data'][0]['options'][0])

    def test_learner_serializer_strips_quiz_answers(self):
        data = LessonLearnDetailSerializer(self.activity, context={}).data
        self.assertEqual(len(data['resources']), 2)
        quiz = next(r for r in data['resources'] if r['type'] == 'quiz')
        self.assertNotIn('is_correct', quiz['quiz_data'][0]['options'][0])
        self.assertEqual(quiz['quiz_data'][0]['options'][0], {'text': 'a'})
