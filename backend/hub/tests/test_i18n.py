from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase

from hub.models import UserProfile


class CountryLanguageTests(TestCase):
    def test_mapping(self):
        from hub.i18n import language_for_country
        self.assertEqual(language_for_country('GR'), 'el')
        self.assertEqual(language_for_country('DE'), 'de')
        self.assertEqual(language_for_country('AT'), 'de')
        self.assertEqual(language_for_country('MX'), 'es')
        self.assertEqual(language_for_country('US'), 'en')  # unmapped -> en
        self.assertEqual(language_for_country(''), 'en')
        self.assertEqual(language_for_country('gr'), 'el')  # case-insensitive


class ProfileLanguageApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='lang_u', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)

    def test_default_language_is_en(self):
        self.assertEqual(self.user.profile.language, 'en')

    def test_me_includes_language(self):
        self.client.force_authenticate(self.user)
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.data['profile']['language'], 'en')

    def test_patch_language(self):
        self.client.force_authenticate(self.user)
        res = self.client.patch('/api/profile/language/', {'language': 'el'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.language, 'el')

    def test_patch_invalid_language_rejected(self):
        self.client.force_authenticate(self.user)
        res = self.client.patch('/api/profile/language/', {'language': 'xx'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_register_defaults_language_from_country(self):
        res = self.client.post('/api/auth/register/', {
            'username': 'greek_teacher', 'password': 'Str0ng!pass9',
            'confirm_password': 'Str0ng!pass9', 'email': 'g@example.com',
            'first_name': 'Nikos', 'last_name': 'P', 'country': 'GR',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(User.objects.get(username='greek_teacher').profile.language, 'el')
