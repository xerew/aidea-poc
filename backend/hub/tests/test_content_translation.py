from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase

from hub.models import Course, Enrollment, LearningPillar, Lesson, Module, UserProfile


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


class LearnerResolutionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='gr_learner', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER, language='el')
        self.pillar = LearningPillar.objects.create(name='P', slug='plr', order=1)
        self.course = Course.objects.create(title='Original', description='OrigDesc', pillar=self.pillar,
            level='beginner', duration_hours=1, is_published=True,
            translations={'el': {'title': 'Πρωτότυπο'}})
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(self.user)

    def test_detail_uses_greek_title_with_english_fallback_for_description(self):
        res = self.client.get(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.data['title'], 'Πρωτότυπο')        # translated
        self.assertEqual(res.data['description'], 'OrigDesc')    # falls back to original

    def test_english_user_sees_original(self):
        en = User.objects.create_user(username='en_learner', password='pass12345')
        UserProfile.objects.create(user=en, user_type=UserProfile.UserType.TEACHER, language='en')
        self.client.force_authenticate(en)
        res = self.client.get(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.data['title'], 'Original')


class AuthoringTranslationTests(APITestCase):
    """Task 5: authoring API exposes source_language/translations/translation_status,
    and PATCH ?lang=<code> writes into the translations blob instead of base fields."""

    def setUp(self):
        self.creator = User.objects.create_user(username='at_cc', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.other = User.objects.create_user(username='at_other', password='pass12345')
        UserProfile.objects.create(user=self.other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.pillar = LearningPillar.objects.create(name='P', slug='pat', order=1)
        self.course = Course.objects.create(
            title='Original Title', description='Original Desc', pillar=self.pillar,
            level='beginner', duration_hours=1, source_language='en',
            learning_outcomes=['Outcome A'], created_by=self.creator,
        )
        self.module = Module.objects.create(
            course=self.course, title='Module Title', description='Module Desc', order=1,
        )
        self.lesson = Lesson.objects.create(
            module=self.module, title='Lesson Title', description='Lesson Desc',
            content='Lesson Body', lesson_type='quiz', order=1,
            quiz_data=[{'question': 'Q?', 'options': [
                {'text': 'A', 'is_correct': True}, {'text': 'B', 'is_correct': False}]}],
        )
        self.course_url = f'/api/authoring/courses/{self.course.id}/'
        self.module_url = f'/api/authoring/courses/{self.course.id}/modules/{self.module.id}/'
        self.lesson_url = (
            f'/api/authoring/courses/{self.course.id}/modules/{self.module.id}/'
            f'lessons/{self.lesson.id}/'
        )

    # -- GET exposes translation fields -----------------------------------

    def test_get_course_includes_translation_fields(self):
        self.client.force_authenticate(self.creator)
        res = self.client.get(self.course_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['source_language'], 'en')
        self.assertEqual(res.data['translations'], {})
        self.assertEqual(res.data['translation_status'], {})

    # -- course PATCH with ?lang= writes to blob, not base fields ---------

    def test_patch_course_with_lang_writes_translation_blob_only(self):
        self.client.force_authenticate(self.creator)
        res = self.client.patch(f'{self.course_url}?lang=el', {'title': 'X'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.translations['el']['title'], 'X')
        self.assertEqual(self.course.title, 'Original Title')

    def test_patch_course_without_lang_edits_base_field(self):
        self.client.force_authenticate(self.creator)
        res = self.client.patch(self.course_url, {'title': 'Y'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Y')
        self.assertEqual(self.course.translations, {})

    def test_patch_course_lang_rejects_source_language(self):
        self.client.force_authenticate(self.creator)
        res = self.client.patch(f'{self.course_url}?lang=en', {'title': 'X'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_patch_course_lang_rejects_unknown_language(self):
        self.client.force_authenticate(self.creator)
        res = self.client.patch(f'{self.course_url}?lang=xx', {'title': 'X'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_setting_source_language_via_normal_patch_persists(self):
        self.client.force_authenticate(self.creator)
        res = self.client.patch(self.course_url, {'source_language': 'fr'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.source_language, 'fr')

    def test_lang_edit_on_published_course_scoped_to_author(self):
        self.course.is_published = True
        self.course.save()
        self.client.force_authenticate(self.other)
        res = self.client.patch(f'{self.course_url}?lang=el', {'title': 'X'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.course.refresh_from_db()
        self.assertEqual(self.course.translations, {})

    def test_lang_edit_on_published_course_allowed_for_author(self):
        self.course.is_published = True
        self.course.save()
        self.client.force_authenticate(self.creator)
        res = self.client.patch(f'{self.course_url}?lang=el', {'title': 'X'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.translations['el']['title'], 'X')

    # -- module PATCH with ?lang= ------------------------------------------

    def test_patch_module_with_lang_writes_translation_blob_only(self):
        self.client.force_authenticate(self.creator)
        res = self.client.patch(
            f'{self.module_url}?lang=el', {'title': 'ModX', 'description': 'DescX'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.module.refresh_from_db()
        self.assertEqual(self.module.translations['el']['title'], 'ModX')
        self.assertEqual(self.module.translations['el']['description'], 'DescX')
        self.assertEqual(self.module.title, 'Module Title')
        self.assertEqual(self.module.description, 'Module Desc')

    def test_patch_module_without_lang_edits_base_field(self):
        self.client.force_authenticate(self.creator)
        res = self.client.patch(self.module_url, {'title': 'ModY'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.module.refresh_from_db()
        self.assertEqual(self.module.title, 'ModY')
        self.assertEqual(self.module.translations, {})

    # -- lesson PATCH with ?lang= -------------------------------------------

    def test_patch_lesson_with_lang_writes_translation_blob_only(self):
        self.client.force_authenticate(self.creator)
        new_quiz = [{'question': 'QX?', 'options': [
            {'text': 'AX', 'is_correct': True}, {'text': 'BX', 'is_correct': False}]}]
        res = self.client.patch(
            f'{self.lesson_url}?lang=el',
            {
                'title': 'LesX', 'description': 'LesDescX', 'content': 'LesBodyX',
                'quiz_data': new_quiz,
            },
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.lesson.refresh_from_db()
        blob = self.lesson.translations['el']
        self.assertEqual(blob['title'], 'LesX')
        self.assertEqual(blob['description'], 'LesDescX')
        self.assertEqual(blob['content'], 'LesBodyX')
        self.assertEqual(blob['quiz_data'], new_quiz)
        self.assertEqual(self.lesson.title, 'Lesson Title')
        self.assertEqual(self.lesson.description, 'Lesson Desc')
        self.assertEqual(self.lesson.content, 'Lesson Body')
        self.assertEqual(self.lesson.quiz_data[0]['question'], 'Q?')

    def test_patch_lesson_without_lang_edits_base_field(self):
        self.client.force_authenticate(self.creator)
        res = self.client.patch(self.lesson_url, {'title': 'LesY'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'LesY')
        self.assertEqual(self.lesson.translations, {})

    def test_lesson_lang_edit_on_published_course_scoped_to_author(self):
        self.course.is_published = True
        self.course.save()
        self.client.force_authenticate(self.other)
        res = self.client.patch(f'{self.lesson_url}?lang=el', {'title': 'LesX'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.translations, {})

    def test_lesson_lang_edit_rejects_malformed_quiz_data(self):
        # Translated quiz_data goes through the same structural validation as the base path
        self.client.force_authenticate(self.creator)
        bad = [{'question': 'Q?', 'options': [{'text': 'only one'}]}]  # < 2 options
        res = self.client.patch(f'{self.lesson_url}?lang=el', {'quiz_data': bad}, format='json')
        self.assertEqual(res.status_code, 400)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.translations, {})


class FinalReviewFixTests(APITestCase):
    """Whole-branch-review fixes: non-en source language, URL content, module
    localization on course detail, and quiz-shape parity on lang edits."""

    def setUp(self):
        self.creator = User.objects.create_user(username='fr_cc', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.pillar = LearningPillar.objects.create(name='P', slug='pfr', order=1)

    def test_english_learner_sees_english_translation_of_greek_course(self):
        # Course authored in Greek, translated INTO English — an English learner
        # must get the English translation, not the Greek source.
        course = Course.objects.create(
            title='Ελληνικός', description='Περιγραφή', pillar=self.pillar, level='beginner',
            duration_hours=1, is_published=True, source_language='el',
            translations={'en': {'title': 'English Title'}},
        )
        learner = User.objects.create_user(username='en_l', password='pass12345')
        UserProfile.objects.create(user=learner, user_type=UserProfile.UserType.TEACHER, language='en')
        self.client.force_authenticate(learner)
        res = self.client.get(f'/api/courses/{course.id}/')
        self.assertEqual(res.data['title'], 'English Title')          # translated
        self.assertEqual(res.data['description'], 'Περιγραφή')          # falls back to Greek source

    def test_course_detail_localizes_module_titles(self):
        course = Course.objects.create(title='C', pillar=self.pillar, level='beginner',
                                       duration_hours=1, is_published=True)
        Module.objects.create(course=course, title='Orig Mod', order=1,
                              translations={'el': {'title': 'Ενότητα'}})
        learner = User.objects.create_user(username='gr_l', password='pass12345')
        UserProfile.objects.create(user=learner, user_type=UserProfile.UserType.TEACHER, language='el')
        self.client.force_authenticate(learner)
        res = self.client.get(f'/api/courses/{course.id}/')
        self.assertEqual(res.data['modules'][0]['title'], 'Ενότητα')

    def test_url_lesson_content_not_translated(self):
        from hub.tasks import translate_course
        course = Course.objects.create(title='C', pillar=self.pillar, level='beginner',
                                       duration_hours=1, source_language='en')
        module = Module.objects.create(course=course, title='M', order=1)
        video = Lesson.objects.create(module=module, title='V', content='https://youtu.be/abc',
                                      lesson_type='video', order=1)
        text = Lesson.objects.create(module=module, title='T', content='Prose body',
                                     lesson_type='text', order=2)
        with patch('hub.tasks.translate_text', side_effect=lambda t, s, d: f'[{d}] {t}'):
            translate_course(course.id, 'el')
        video.refresh_from_db()
        text.refresh_from_db()
        self.assertNotIn('content', video.translations['el'])          # URL left untranslated
        self.assertEqual(text.translations['el']['content'], '[el] Prose body')

    def test_lang_quiz_shape_mismatch_rejected(self):
        course = Course.objects.create(title='C', pillar=self.pillar, level='beginner',
                                       duration_hours=1, source_language='en', created_by=self.creator)
        module = Module.objects.create(course=course, title='M', order=1)
        quiz = Lesson.objects.create(module=module, title='Q', lesson_type='quiz', order=1,
            quiz_data=[{'question': 'Q?', 'options': [
                {'text': 'A', 'is_correct': True}, {'text': 'B', 'is_correct': False}]}])
        url = f'/api/authoring/courses/{course.id}/modules/{module.id}/lessons/{quiz.id}/?lang=el'
        self.client.force_authenticate(self.creator)
        # 3 options translated where base has 2 → structurally valid but mismatched → 400
        mismatched = [{'question': 'Ερ;', 'options': [
            {'text': 'Α', 'is_correct': True}, {'text': 'Β', 'is_correct': False},
            {'text': 'Γ', 'is_correct': False}]}]
        res = self.client.patch(url, {'quiz_data': mismatched}, format='json')
        self.assertEqual(res.status_code, 400)
        # matching shape (2 options) → accepted
        matched = [{'question': 'Ερ;', 'options': [
            {'text': 'Α', 'is_correct': True}, {'text': 'Β', 'is_correct': False}]}]
        res = self.client.patch(url, {'quiz_data': matched}, format='json')
        self.assertEqual(res.status_code, 200)
        quiz.refresh_from_db()
        self.assertEqual(quiz.translations['el']['quiz_data'][0]['question'], 'Ερ;')
