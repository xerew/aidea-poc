from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import UserProfile


def make_teacher(username='pref_teacher'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
    return user


class ProfilePreferencesGetTest(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'pref_teacher', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_get_returns_empty_defaults(self):
        response = self.client.get(reverse('profile-preferences'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['preferred_pillars'], [])
        self.assertEqual(response.data['learning_style'], '')


class ProfilePreferencesPatchTest(APITestCase):
    def setUp(self):
        self.user = make_teacher('pref_teacher2')
        login = self.client.post(reverse('auth-login'), {'username': 'pref_teacher2', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_patch_preferred_pillars(self):
        response = self.client.patch(
            reverse('profile-preferences'),
            {'preferred_pillars': ['teach-with-ai', 'teach-about-ai']},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.preferred_pillars, ['teach-with-ai', 'teach-about-ai'])

    def test_patch_learning_style(self):
        response = self.client.patch(
            reverse('profile-preferences'),
            {'learning_style': 'video'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.learning_style, 'video')

    def test_patch_both_fields(self):
        response = self.client.patch(
            reverse('profile-preferences'),
            {'preferred_pillars': ['teach-for-ai'], 'learning_style': 'text'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.preferred_pillars, ['teach-for-ai'])
        self.assertEqual(self.user.profile.learning_style, 'text')

    def test_invalid_pillar_rejected(self):
        response = self.client.patch(
            reverse('profile-preferences'),
            {'preferred_pillars': ['not-a-real-pillar']},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_learning_style_rejected(self):
        response = self.client.patch(
            reverse('profile-preferences'),
            {'learning_style': 'podcast'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_content_creator_gets_403(self):
        creator = User.objects.create_user(username='prof_creator', password='pass')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        login = self.client.post(reverse('auth-login'), {'username': 'prof_creator', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.get(reverse('profile-preferences'))
        self.assertEqual(response.status_code, 403)
