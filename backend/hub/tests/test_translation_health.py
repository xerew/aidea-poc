import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, UserProfile
from hub.translation_health import STATUS_KEY, check_now, get_status, probe

URLOPEN = 'hub.translation_health.urllib.request.urlopen'
PROBE = 'hub.translation_health.probe'


def _tags_response(*names):
    resp = MagicMock()
    resp.__enter__.return_value = BytesIO(json.dumps({'models': [{'name': n} for n in names]}).encode())
    return resp


class ProbeTests(TestCase):
    def test_online_when_model_installed(self):
        with patch(URLOPEN, return_value=_tags_response('llama3:8b', 'gemma3-translator:latest')):
            self.assertEqual(probe(), (True, ''))

    def test_offline_when_model_missing(self):
        with patch(URLOPEN, return_value=_tags_response('llama3:8b')):
            online, error = probe()
        self.assertFalse(online)
        self.assertIn('not installed', error)

    def test_offline_when_unreachable(self):
        with patch(URLOPEN, side_effect=urllib.error.URLError('Connection refused')):
            online, error = probe()
        self.assertFalse(online)
        self.assertIn('Connection refused', error)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CheckNowTests(TestCase):
    def setUp(self):
        cache.delete(STATUS_KEY)
        admin = User.objects.create_user(username='adm', password='x', email='admin@example.org')
        UserProfile.objects.create(user=admin, user_type=UserProfile.UserType.ADMIN)

    def test_admins_emailed_on_outage_and_recovery_only(self):
        with patch(PROBE, return_value=(False, 'Cannot reach the translation server: refused')):
            first = check_now()
            check_now()  # still down: no second email
        self.assertFalse(first['online'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('offline', mail.outbox[0].subject)
        self.assertIn('refused', mail.outbox[0].body)
        self.assertEqual(get_status()['since'], first['since'])  # outage start is kept

        with patch(PROBE, return_value=(True, '')):
            back = check_now()
        self.assertTrue(back['online'])
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('back online', mail.outbox[1].subject)

    def test_first_check_online_sends_nothing(self):
        with patch(PROBE, return_value=(True, '')):
            check_now()
        self.assertEqual(len(mail.outbox), 0)

    def test_scheduled_task_runs_the_check(self):
        from hub.tasks import check_translation_service
        with patch(PROBE, return_value=(True, '')):
            check_translation_service()
        self.assertTrue(get_status()['online'])

    def test_task_is_scheduled_every_15_minutes(self):
        from django.conf import settings
        entry = settings.CELERY_BEAT_SCHEDULE['check-translation-service']
        self.assertEqual(entry['task'], 'hub.tasks.check_translation_service')
        self.assertEqual(entry['schedule']._orig_minute, '*/15')


class TranslateWhenOfflineTests(APITestCase):
    def setUp(self):
        cache.delete(STATUS_KEY)
        self.creator = User.objects.create_user(username='hc_cc', password='x')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-hc', order=1)
        self.course = Course.objects.create(title='C', pillar=pillar, created_by=self.creator)
        self.client.force_authenticate(self.creator)

    @patch('hub.tasks.translate_course.delay')
    def test_translate_returns_503_and_queues_nothing(self, delay):
        with patch(PROBE, return_value=(False, 'Cannot reach the translation server: timed out')):
            res = self.client.post(f'/api/authoring/courses/{self.course.id}/translate/',
                                   {'language': 'el'}, format='json')
        self.assertEqual(res.status_code, 503)
        self.assertFalse(res.data['service']['online'])
        delay.assert_not_called()
        self.course.refresh_from_db()
        self.assertNotIn('el', self.course.translation_status)

    def test_status_endpoint_uses_cache_and_refreshes_on_request(self):
        with patch(PROBE, return_value=(True, '')) as live:
            self.assertTrue(self.client.get('/api/authoring/translation-service/').data['online'])
            self.client.get('/api/authoring/translation-service/')
            self.assertEqual(live.call_count, 1)  # second call served from cache
        with patch(PROBE, return_value=(False, 'down')):
            res = self.client.get('/api/authoring/translation-service/?refresh=1')
        self.assertFalse(res.data['online'])

    def test_status_endpoint_forbidden_for_teachers(self):
        teacher = User.objects.create_user(username='hc_t', password='x')
        UserProfile.objects.create(user=teacher, user_type=UserProfile.UserType.TEACHER)
        self.client.force_authenticate(teacher)
        self.assertEqual(self.client.get('/api/authoring/translation-service/').status_code, 403)
