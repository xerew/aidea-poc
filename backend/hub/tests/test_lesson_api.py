from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from hub.models import (
    Course,
    Enrollment,
    LearningPillar,
    Lesson,
    Module,
    UserProfile,
)


class LessonDetailSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ldt1', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P_LD', slug='p-ld', description='')
        self.course = Course.objects.create(title='C_LD', pillar=pillar, is_published=True)
        module = Module.objects.create(title='M_LD', course=self.course, order=1)
        self.lesson = Lesson.objects.create(
            title='Quiz Lesson',
            module=module,
            order=1,
            is_required=True,
            lesson_type='quiz',
            quiz_data=[{
                'question': 'Q1',
                'options': [
                    {'text': 'A', 'is_correct': False},
                    {'text': 'B', 'is_correct': True},
                ],
            }],
        )
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_is_correct_stripped_from_lesson_detail(self):
        res = self.client.get(f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/')
        self.assertEqual(res.status_code, 200)
        options = res.data['quiz_data'][0]['options']
        for opt in options:
            self.assertNotIn('is_correct', opt)

    def test_quiz_results_in_complete_response(self):
        res = self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/',
            {'quiz_answers': [1]},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('quiz_results', res.data)
        self.assertEqual(res.data['quiz_results'], [True])

    def test_quiz_results_null_for_non_quiz(self):
        lesson2 = Lesson.objects.create(
            title='Text Lesson', module=self.lesson.module, order=2,
            is_required=True, lesson_type='text',
        )
        res = self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson2.pk}/complete/', {}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.data['quiz_results'])
