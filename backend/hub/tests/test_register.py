from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub.models import UserProfile


class RegisterViewTest(APITestCase):
    URL = '/api/auth/register/'
    VALID = {
        'first_name': 'Test', 'last_name': 'User',
        'username': 'testuser', 'email': 'test@example.com',
        'password': 'Secure#123', 'confirm_password': 'Secure#123',
    }

    def test_register_creates_user_and_returns_201(self):
        res = self.client.post(self.URL, self.VALID, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_register_creates_teacher_profile(self):
        self.client.post(self.URL, self.VALID, format='json')
        profile = UserProfile.objects.get(user__username='testuser')
        self.assertEqual(profile.user_type, 'teacher')

    def test_register_sets_avatar_initials_from_name(self):
        self.client.post(self.URL, self.VALID, format='json')
        profile = UserProfile.objects.get(user__username='testuser')
        self.assertEqual(profile.avatar_initials, 'TU')

    def test_register_returns_jwt_tokens_and_user(self):
        res = self.client.post(self.URL, self.VALID, format='json')
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)
        self.assertIn('user', res.data)
        self.assertEqual(res.data['user']['username'], 'testuser')

    def test_register_duplicate_username_returns_400(self):
        self.client.post(self.URL, self.VALID, format='json')
        res = self.client.post(
            self.URL, {**self.VALID, 'email': 'other@example.com'}, format='json'
        )
        self.assertEqual(res.status_code, 400)

    def test_register_duplicate_email_returns_400(self):
        self.client.post(self.URL, self.VALID, format='json')
        res = self.client.post(
            self.URL, {**self.VALID, 'username': 'otheruser'}, format='json'
        )
        self.assertEqual(res.status_code, 400)

    def test_register_weak_password_returns_400(self):
        data = {**self.VALID, 'password': 'weakpass', 'confirm_password': 'weakpass'}
        res = self.client.post(self.URL, data, format='json')
        self.assertEqual(res.status_code, 400)

    def test_register_password_mismatch_returns_400(self):
        data = {**self.VALID, 'confirm_password': 'Different#999'}
        res = self.client.post(self.URL, data, format='json')
        self.assertEqual(res.status_code, 400)
