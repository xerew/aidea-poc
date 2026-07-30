from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase

from hub.models import (
    OnboardingConfig,
    OnboardingDimension,
    OnboardingQuestion,
    UserProfile,
)

URL = '/api/admin/onboarding-translations/'


def make_user(username, user_type):
    user = User.objects.create_user(username=username, password='pass12345')
    UserProfile.objects.create(user=user, user_type=user_type)
    return user


class TranslateOnboardingTaskTests(TestCase):
    def setUp(self):
        self.dim = OnboardingDimension.objects.create(name='AI Knowledge', slug='ai-knowledge-t', order=1)
        self.q = OnboardingQuestion.objects.create(
            dimension=self.dim, text='I can explain what AI is.', order=1)
        # An inactive question must be skipped.
        self.inactive = OnboardingQuestion.objects.create(
            dimension=self.dim, text='Old', order=9, is_active=False)

    @patch('hub.tasks.translate_text', side_effect=lambda text, src, dst: f'[{dst}] {text}')
    def test_translates_active_dimensions_and_questions(self, _m):
        from hub.tasks import translate_onboarding
        translate_onboarding('el')
        self.dim.refresh_from_db()
        self.q.refresh_from_db()
        self.inactive.refresh_from_db()
        self.assertEqual(self.dim.translations['el'], '[el] AI Knowledge')
        self.assertEqual(self.q.translations['el'], '[el] I can explain what AI is.')
        self.assertEqual(OnboardingConfig.get().translation_status['el'], 'done')
        # Inactive question left untouched.
        self.assertEqual(self.inactive.translations, {})

    def test_failure_marks_status_failed(self):
        from hub.tasks import translate_onboarding
        from hub.translation import TranslationError
        with patch('hub.tasks.translate_text', side_effect=TranslationError('down')):
            translate_onboarding('fr')
        self.assertEqual(OnboardingConfig.get().translation_status['fr'], 'failed')


class OnboardingTranslationEndpointTests(APITestCase):
    def setUp(self):
        self.admin = make_user('onb_admin', UserProfile.UserType.ADMIN)
        self.teacher = make_user('onb_teacher', UserProfile.UserType.TEACHER)
        OnboardingQuestion.objects.create(text='Q1', order=1)

    def test_get_returns_status_and_languages(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['source_language'], 'en')
        self.assertTrue(res.data['has_questions'])
        codes = {lang['code'] for lang in res.data['languages']}
        self.assertIn('el', codes)
        self.assertNotIn('en', codes)  # source excluded

    @patch('hub.tasks.translate_onboarding.delay')
    def test_translate_enqueues_and_sets_pending(self, mock_delay):
        self.client.force_authenticate(self.admin)
        res = self.client.post(URL, {'language': 'el'}, format='json')
        self.assertEqual(res.status_code, 202)
        mock_delay.assert_called_once_with('el')
        self.assertEqual(res.data['translation_status']['el'], 'pending')

    @patch('hub.tasks.translate_onboarding.delay')
    def test_rejects_source_and_unknown_language(self, _m):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(URL, {'language': 'en'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(URL, {'language': 'xx'}, format='json').status_code, 400)

    def test_teacher_forbidden(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(self.client.post(URL, {'language': 'el'}, format='json').status_code, 403)

    def test_review_marks_done_translation_reviewed(self):
        cfg = OnboardingConfig.get()
        cfg.translation_status = {'el': 'done'}
        cfg.save()
        self.client.force_authenticate(self.admin)
        res = self.client.patch(URL, {'language': 'el', 'reviewed': True}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['translation_status']['el'], 'reviewed')

    def test_unmark_reviewed_back_to_done(self):
        cfg = OnboardingConfig.get()
        cfg.translation_status = {'el': 'reviewed'}
        cfg.save()
        self.client.force_authenticate(self.admin)
        res = self.client.patch(URL, {'language': 'el', 'reviewed': False}, format='json')
        self.assertEqual(res.data['translation_status']['el'], 'done')

    def test_cannot_review_pending_translation(self):
        cfg = OnboardingConfig.get()
        cfg.translation_status = {'el': 'pending'}
        cfg.save()
        self.client.force_authenticate(self.admin)
        res = self.client.patch(URL, {'language': 'el', 'reviewed': True}, format='json')
        self.assertEqual(res.status_code, 400)
