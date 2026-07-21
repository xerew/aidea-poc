from django.test import TestCase

from hub.models import Course, LearningPillar, Lesson, Module


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
