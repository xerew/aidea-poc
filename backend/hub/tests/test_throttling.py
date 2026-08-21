from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

# Throttling is disabled by default under the test runner (see settings). These
# tests opt back in with small rates so the limits are quick to hit.
THROTTLE_SETTINGS = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_THROTTLE_RATES': {
        'login_user':     '5/min',
        'login_ip':       '60/min',
        'pw_reset_email': '3/hour',
        'pw_reset_ip':    '50/hour',
    },
}


@override_settings(REST_FRAMEWORK=THROTTLE_SETTINGS)
class LoginThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()  # throttle history lives in the cache
        self.url = reverse('auth-login')
        User.objects.create_user(username='victim', password='CorrectHorse9!')

    def _attempt(self, username, password='wrong-pass'):
        return self.client.post(self.url, {'username': username, 'password': password})

    def test_repeated_failures_on_one_account_get_locked(self):
        for _ in range(5):
            self.assertNotEqual(self._attempt('victim').status_code, 429)
        # 6th attempt within the window is throttled.
        self.assertEqual(self._attempt('victim').status_code, 429)

    def test_lockout_is_per_username_not_shared_ip(self):
        # Five different teachers behind the same (school) IP each log in once —
        # none should be throttled even though they share an address.
        for i in range(5):
            User.objects.create_user(username=f'teacher{i}', password='pw')
            res = self._attempt(f'teacher{i}', password='pw')
            self.assertNotEqual(res.status_code, 429)

    def test_successful_login_still_counts_toward_the_limit(self):
        # The rate limit protects the endpoint regardless of success/failure.
        for _ in range(5):
            self._attempt('victim', password='CorrectHorse9!')
        self.assertEqual(self._attempt('victim', password='CorrectHorse9!').status_code, 429)


@override_settings(REST_FRAMEWORK=THROTTLE_SETTINGS)
class PasswordResetThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('auth-password-reset')

    def test_reset_requests_for_one_email_are_capped(self):
        for _ in range(3):
            self.assertNotEqual(
                self.client.post(self.url, {'email': 'a@example.com'}).status_code, 429,
            )
        self.assertEqual(
            self.client.post(self.url, {'email': 'a@example.com'}).status_code, 429,
        )

    def test_reset_cap_is_per_email(self):
        # A different email is unaffected by another email's limit.
        for _ in range(3):
            self.client.post(self.url, {'email': 'a@example.com'})
        res = self.client.post(self.url, {'email': 'b@example.com'})
        self.assertNotEqual(res.status_code, 429)


class ThrottlingDisabledByDefaultTests(APITestCase):
    """Without the override, ordinary login flows are never throttled."""

    def setUp(self):
        cache.clear()
        self.url = reverse('auth-login')
        User.objects.create_user(username='normal', password='pw')

    def test_many_logins_not_throttled_in_default_test_config(self):
        for _ in range(20):
            res = self.client.post(self.url, {'username': 'normal', 'password': 'pw'})
            self.assertNotEqual(res.status_code, 429)
