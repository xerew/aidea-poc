from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import UserProfile


class AuthTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='teacher1',
            password='testpass123',
            first_name='Nikos',
            last_name='Grammatikos',
        )
        UserProfile.objects.create(
            user=self.user,
            user_type=UserProfile.UserType.TEACHER,
            avatar_initials='NG',
        )

    def test_login_returns_tokens_and_user(self):
        response = self.client.post(reverse('auth-login'), {
            'username': 'teacher1',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'teacher1')
        self.assertEqual(response.data['user']['profile']['user_type'], 'teacher')
        self.assertEqual(response.data['user']['profile']['avatar_initials'], 'NG')

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('auth-login'), {
            'username': 'teacher1',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_returns_new_access_token(self):
        login = self.client.post(reverse('auth-login'), {
            'username': 'teacher1',
            'password': 'testpass123',
        })
        response = self.client.post(reverse('auth-refresh'), {
            'refresh': login.data['refresh'],
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_logout_blacklists_refresh_token(self):
        login = self.client.post(reverse('auth-login'), {
            'username': 'teacher1',
            'password': 'testpass123',
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.post(reverse('auth-logout'), {
            'refresh': login.data['refresh'],
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Blacklisted token can no longer be refreshed
        refresh_response = self.client.post(reverse('auth-refresh'), {
            'refresh': login.data['refresh'],
        })
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_authentication(self):
        response = self.client.post(reverse('auth-logout'), {'refresh': 'sometoken'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
