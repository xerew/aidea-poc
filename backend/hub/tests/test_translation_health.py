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


STATUS_FILE = 'hub.translation_health.TUNNEL_STATUS_FILE'


class TunnelAddressTests(TestCase):
    """Which NTUA address the ollama-tunnel container is using (its status file)."""

    def status_file(self, text):
        import tempfile
        from pathlib import Path
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__('shutil').rmtree, folder, ignore_errors=True)
        path = folder / 'ollama-tunnel.json'
        path.write_text(text, encoding='utf-8')
        return str(path)

    def test_reads_the_address_and_since(self):
        from hub.translation_health import tunnel_address
        path = self.status_file('{"host": "147.102.17.66", "since": "2026-11-12T08:42:00Z"}\n')
        with patch(STATUS_FILE, path):
            host, since = tunnel_address()
        self.assertEqual(host, '147.102.17.66')
        self.assertEqual(since.isoformat(), '2026-11-12T08:42:00+00:00')

    def test_unknown_when_the_file_is_missing_or_garbled(self):
        from hub.translation_health import tunnel_address
        with patch(STATUS_FILE, '/nowhere/ollama-tunnel.json'):
            self.assertEqual(tunnel_address(), (None, None))
        with patch(STATUS_FILE, self.status_file('{not json')):
            self.assertEqual(tunnel_address(), (None, None))

    @override_settings(TIME_ZONE='UTC')
    def test_summary_when_connected_and_when_not(self):
        from hub.translation_health import server_summary
        path = self.status_file('{"host": "147.102.23.222", "since": "2026-11-12T08:42:00Z"}')
        with patch(STATUS_FILE, path), patch(PROBE, return_value=(True, '')):
            self.assertEqual(server_summary(), 'Connected via 147.102.23.222 since 12 Nov 2026, 08:42.')
        with patch(STATUS_FILE, path), patch(PROBE, return_value=(False, 'Cannot reach the translation server: refused')):
            summary = server_summary()
        self.assertTrue(summary.startswith('Not connected. Trying 147.102.23.222 now.'), summary)
        self.assertIn('refused', summary)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_check_records_the_address_and_the_outage_email_names_it(self):
        cache.delete(STATUS_KEY)
        admin = User.objects.create_user(username='adm2', password='x', email='admin2@example.org')
        UserProfile.objects.create(user=admin, user_type=UserProfile.UserType.ADMIN)
        path = self.status_file('{"host": "147.102.17.66", "since": "2026-11-12T08:42:00Z"}')
        with patch(STATUS_FILE, path), patch(PROBE, return_value=(False, 'refused')):
            status = check_now()
        self.assertEqual(status['host'], '147.102.17.66')
        self.assertIn('147.102.17.66', mail.outbox[0].body)


class OllamaServerAdminTests(TestCase):
    def test_ai_review_settings_page_shows_the_ollama_server(self):
        from hub.models import AIReviewSettings
        superuser = User.objects.create_superuser('root', 'root@example.org', 'x')
        self.client.force_login(superuser)
        obj = AIReviewSettings.objects.first() or AIReviewSettings.objects.create()
        with patch('hub.admin.server_summary', return_value='Connected via 147.102.17.66 since 12 Nov 2026, 08:42.'):
            res = self.client.get(f'/django-admin/hub/aireviewsettings/{obj.pk}/change/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Ollama server')
        self.assertContains(res, 'Connected via 147.102.17.66')
