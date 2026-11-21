"""Login records and the platform-actions log (spec 2026-11-21-user-activity-page)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from hub.models import LoginRecord, UserProfile

from .test_emails import VALID_REGISTER

IPHONE = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
          '(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
ANDROID = ('Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) '
           'Chrome/124.0.0.0 Mobile Safari/537.36')
IPAD = ('Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) '
        'Version/17.0 Mobile/15E148 Safari/604.1')
EDGE = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0')
FIREFOX = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'
OPERA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
         'Chrome/124.0.0.0 Safari/537.36 OPR/110.0.0.0')


class LoginRecordTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('lr_user', password='pass12345')
        UserProfile.objects.create(user=self.user)

    def _login(self, password='pass12345', **headers):
        return self.client.post(reverse('auth-login'), {'username': 'lr_user', 'password': password},
                                format='json', **headers)

    def test_parse_user_agent(self):
        from hub.activity_log import parse_user_agent
        cases = {
            IPHONE: ('mobile', 'Safari'), ANDROID: ('mobile', 'Chrome'), IPAD: ('tablet', 'Safari'),
            EDGE: ('desktop', 'Edge'), FIREFOX: ('desktop', 'Firefox'), OPERA: ('desktop', 'Opera'),
            '': ('', 'Other'), None: ('', 'Other'),
        }
        for ua, expected in cases.items():
            self.assertEqual(parse_user_agent(ua), expected, ua)

    def test_login_is_recorded(self):
        self.assertEqual(self._login(HTTP_USER_AGENT=IPHONE).status_code, 200)
        record = LoginRecord.objects.get()
        self.assertEqual((record.user, record.device, record.browser), (self.user, 'mobile', 'Safari'))

    def test_failed_login_is_not_recorded(self):
        self.assertEqual(self._login(password='wrong').status_code, 401)
        self.assertEqual(LoginRecord.objects.count(), 0)

    def test_register_is_recorded(self):
        res = self.client.post(reverse('auth-register'), VALID_REGISTER, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(LoginRecord.objects.filter(user__username=VALID_REGISTER['username']).count(), 1)

    def test_refresh_is_not_a_login(self):
        refresh = self._login().data['refresh']
        self.assertEqual(self.client.post(reverse('auth-refresh'), {'refresh': refresh}, format='json').status_code, 200)
        self.assertEqual(LoginRecord.objects.count(), 1)

    def test_missing_user_agent_still_recorded(self):
        self._login()
        record = LoginRecord.objects.get()
        self.assertEqual((record.device, record.browser), ('', 'Other'))

    def test_old_records_deleted(self):
        from hub.tasks import delete_old_login_records
        now = timezone.now()
        ages = [timedelta(days=366), timedelta(days=365) - timedelta(hours=1), timedelta(0)]
        for age in ages:
            record = LoginRecord.objects.create(user=self.user)
            LoginRecord.objects.filter(pk=record.pk).update(at=now - age)
        self.assertEqual(delete_old_login_records(), 1)
        self.assertEqual(LoginRecord.objects.count(), 2)
