from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_BASE_URL='https://aidea-hub.eu',
    DEFAULT_FROM_EMAIL='AIDEA <info@aidea-hub.eu>',
)
class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='reset_u', email='eva@example.com', password='OldPass123!',
            first_name='Eva', last_name='K',
        )

    def _uid_token(self, user=None):
        user = user or self.user
        return (
            urlsafe_base64_encode(force_bytes(user.pk)),
            default_token_generator.make_token(user),
        )

    def test_request_sends_email_for_known_address(self):
        res = self.client.post('/api/auth/password-reset/', {'email': 'eva@example.com'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset-password', mail.outbox[0].body)

    def test_request_unknown_email_still_ok_and_no_mail(self):
        res = self.client.post('/api/auth/password-reset/', {'email': 'nobody@x.com'}, format='json')
        self.assertEqual(res.status_code, 200)  # same response, no leak
        self.assertEqual(len(mail.outbox), 0)

    def test_request_is_case_insensitive(self):
        self.client.post('/api/auth/password-reset/', {'email': 'EVA@EXAMPLE.COM'}, format='json')
        self.assertEqual(len(mail.outbox), 1)

    def test_confirm_sets_new_password(self):
        uid, token = self._uid_token()
        res = self.client.post(
            '/api/auth/password-reset/confirm/',
            {'uid': uid, 'token': token, 'new_password': 'BrandNew123!'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNew123!'))

    def test_confirm_rejects_bad_token(self):
        uid, _ = self._uid_token()
        res = self.client.post(
            '/api/auth/password-reset/confirm/',
            {'uid': uid, 'token': 'not-a-real-token', 'new_password': 'BrandNew123!'}, format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_confirm_rejects_weak_password(self):
        uid, token = self._uid_token()
        res = self.client.post(
            '/api/auth/password-reset/confirm/',
            {'uid': uid, 'token': token, 'new_password': '123'}, format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_token_single_use(self):
        uid, token = self._uid_token()
        self.client.post(
            '/api/auth/password-reset/confirm/',
            {'uid': uid, 'token': token, 'new_password': 'BrandNew123!'}, format='json',
        )
        # The same token must not work again (password hash changed).
        res = self.client.post(
            '/api/auth/password-reset/confirm/',
            {'uid': uid, 'token': token, 'new_password': 'Another123!'}, format='json',
        )
        self.assertEqual(res.status_code, 400)
