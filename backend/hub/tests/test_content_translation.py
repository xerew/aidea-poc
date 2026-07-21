from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, Lesson, Module, UserProfile


class TranslationFieldsTests(TestCase):
    def test_defaults(self):
        pillar = LearningPillar.objects.create(name='P', slug='ptr', order=1)
        c = Course.objects.create(title='C', pillar=pillar, level='beginner', duration_hours=1)
        self.assertEqual(c.source_language, 'en')
        self.assertEqual(c.translations, {})
        self.assertEqual(c.translation_status, {})
        m = Module.objects.create(course=c, title='M', order=1)
        self.assertEqual(m.translations, {})
        lesson = Lesson.objects.create(module=m, title='L', lesson_type='text', order=1)
        self.assertEqual(lesson.translations, {})

    def test_stores_translation_blob(self):
        pillar = LearningPillar.objects.create(name='P2', slug='ptr2', order=1)
        c = Course.objects.create(title='C', pillar=pillar, level='beginner', duration_hours=1,
                                  translations={'el': {'title': 'Τίτλος'}})
        c.refresh_from_db()
        self.assertEqual(c.translations['el']['title'], 'Τίτλος')


class TranslateCourseTaskTests(TestCase):
    def setUp(self):
        self.pillar = LearningPillar.objects.create(name='P', slug='ptc', order=1)
        self.course = Course.objects.create(title='Hello', description='Desc', pillar=self.pillar,
            level='beginner', duration_hours=1, source_language='en',
            learning_outcomes=['Outcome A'], is_published=True)
        self.module = Module.objects.create(course=self.course, title='Mod', description='md', order=1)
        self.lesson = Lesson.objects.create(module=self.module, title='Les', description='ld',
            content='Body', lesson_type='quiz', order=1,
            quiz_data=[{'question': 'Q?', 'options': [
                {'text': 'A', 'is_correct': True}, {'text': 'B', 'is_correct': False}]}])

    @patch('hub.tasks.translate_text', side_effect=lambda t, s, d: f'[{d}] {t}')
    def test_translate_course_populates_all_levels(self, _m):
        from hub.tasks import translate_course
        translate_course(self.course.id, 'el')
        self.course.refresh_from_db()
        self.module.refresh_from_db()
        self.lesson.refresh_from_db()
        self.assertEqual(self.course.translations['el']['title'], '[el] Hello')
        self.assertEqual(self.course.translations['el']['learning_outcomes'], ['[el] Outcome A'])
        self.assertEqual(self.course.translation_status['el'], 'done')
        self.assertEqual(self.module.translations['el']['title'], '[el] Mod')
        qd = self.lesson.translations['el']['quiz_data']
        self.assertEqual(qd[0]['question'], '[el] Q?')
        self.assertEqual(qd[0]['options'][0]['text'], '[el] A')
        self.assertTrue(qd[0]['options'][0]['is_correct'])  # flag preserved

    @patch('hub.tasks.translate_text', side_effect=Exception('down'))
    def test_failure_marks_status_failed(self, _m):
        from hub.tasks import translate_course

        # wrap: translate_course should catch TranslationError; use TranslationError
        from hub.translation import TranslationError
        with patch('hub.tasks.translate_text', side_effect=TranslationError('down')):
            translate_course(self.course.id, 'el')
        self.course.refresh_from_db()
        self.assertEqual(self.course.translation_status['el'], 'failed')


class TranslateEndpointTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='tr_cc', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.pillar = LearningPillar.objects.create(name='P', slug='pte', order=1)
        self.course = Course.objects.create(title='C', pillar=self.pillar, level='beginner',
            duration_hours=1, source_language='en', created_by=self.creator)
        self.url = f'/api/authoring/courses/{self.course.id}/translate/'

    @patch('hub.tasks.translate_course.delay')
    def test_enqueues_and_sets_pending(self, mock_delay):
        self.client.force_authenticate(self.creator)
        res = self.client.post(self.url, {'language': 'el'}, format='json')
        self.assertEqual(res.status_code, 202)
        mock_delay.assert_called_once_with(self.course.id, 'el')
        self.course.refresh_from_db()
        self.assertEqual(self.course.translation_status['el'], 'pending')

    def test_rejects_source_language_and_unknown(self):
        self.client.force_authenticate(self.creator)
        self.assertEqual(self.client.post(self.url, {'language': 'en'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, {'language': 'xx'}, format='json').status_code, 400)

    def test_non_author_forbidden(self):
        other = User.objects.create_user(username='tr_other', password='pass12345')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course.is_published = True
        self.course.save()
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post(self.url, {'language': 'el'}, format='json').status_code, 403)
