"""Login records and the platform-actions log (spec 2026-11-21-user-activity-page)."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from hub.models import Activity, LoginRecord, Resource, UserProfile

from .test_collaborators import CollaboratorBase
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


class PlatformActionTests(CollaboratorBase):
    """Actions that left no trace are logged, with a title snapshot in `label`."""

    def setUp(self):
        super().setUp()
        self.activity = Activity.objects.create(module=self.module1, title='A', order=1)
        self.res1 = Resource.objects.create(activity=self.activity, type='text', title='Intro text', order=1)
        self.res2 = Resource.objects.create(activity=self.activity, type='text', title='Second', order=2)

    def _resource_url(self, resource):
        return reverse('authoring-resource-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk,
            'lesson_pk': self.activity.pk, 'resource_pk': resource.pk})

    def _only(self, kind):
        from hub.models import PlatformAction
        rows = list(PlatformAction.objects.all())
        self.assertEqual([r.kind for r in rows], [kind])
        return rows[0]

    @patch('hub.translation_health.probe', return_value=(True, ''))
    @patch('hub.tasks.translate_course.delay')
    def test_translation_requested(self, _delay, _probe):
        self._login_as(self.creator)
        res = self.client.post(reverse('authoring-course-translate', kwargs={'pk': self.course.pk}),
                               {'language': 'el'}, format='json')
        self.assertEqual(res.status_code, 202)
        row = self._only('translation_requested')
        self.assertEqual((row.user, row.course, row.label), (self.creator, self.course, 'Intro to AI'))
        self.assertEqual(row.details, {'language': 'el', 'scope': 'course'})

    def test_course_deleted_keeps_title(self):
        self._login_as(self.creator)
        self.assertEqual(self.client.delete(self._detail_url()).status_code, 204)
        row = self._only('course_deleted')
        self.assertEqual((row.user, row.course, row.label), (self.creator, None, 'Intro to AI'))

    def test_resource_edited(self):
        self._login_as(self.creator)
        self.assertEqual(self.client.patch(self._resource_url(self.res1), {'content': 'New'}, format='json').status_code, 200)
        row = self._only('resource_edited')
        self.assertEqual((row.course, row.label), (self.course, 'Intro to AI'))
        self.assertEqual(row.details, {'resource_title': 'Intro text', 'resource_type': 'text'})

    def test_resource_deleted(self):
        self._login_as(self.creator)
        self.assertEqual(self.client.delete(self._resource_url(self.res2)).status_code, 204)
        row = self._only('resource_deleted')
        self.assertEqual(row.details, {'resource_title': 'Second', 'resource_type': 'text'})

    def test_collaborator_added_once_per_role(self):
        self._login_as(self.creator)
        for _ in range(2):
            self.client.post(self._collaborators_url(), {'user_id': self.other_creator.id, 'role': 'co_editor'}, format='json')
        row = self._only('collaborator_added')
        self.assertEqual(row.details, {'collaborator': 'creator2', 'role': 'co_editor'})

    def test_collaborator_removed(self):
        self._add(self.other_creator, 'translator')
        self._login_as(self.creator)
        self.assertEqual(self.client.delete(self._collaborator_detail_url(self.other_creator)).status_code, 204)
        row = self._only('collaborator_removed')
        self.assertEqual((row.label, row.details), ('Intro to AI', {'collaborator': 'creator2'}))

    def test_role_changed(self):
        self._login_as(self.admin)
        res = self.client.patch(reverse('admin-user-role', kwargs={'pk': self.teacher.pk}),
                                {'user_type': 'content_creator'}, format='json')
        self.assertEqual(res.status_code, 200)
        row = self._only('role_changed')
        self.assertEqual((row.user, row.label), (self.admin, 'teacher1'))
        self.assertEqual(row.details, {'target': 'teacher1', 'old_role': 'teacher', 'new_role': 'content_creator'})

    def test_pathways_rebuilt(self):
        self._login_as(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(reverse('admin-pathways-rebuild')).status_code, 202)
        row = self._only('pathways_rebuilt')
        self.assertEqual((row.user, row.details), (self.admin, {'applied': 0}))

    def test_ai_review_saved(self):
        from .test_ai_review_models import make_assignment
        course, module, activity, resource = make_assignment()
        self._login_as(self.admin)
        url = reverse('authoring-ai-review', kwargs={'pk': course.id, 'module_pk': module.id,
                                                      'lesson_pk': activity.id, 'resource_pk': resource.id})
        self.assertEqual(self.client.put(url, {'enabled': True}, format='json').status_code, 200)
        row = self._only('ai_review_saved')
        self.assertEqual((row.course, row.label), (course, course.title))
        self.assertEqual(row.details, {'resource_title': resource.title or resource.type})

    def test_recording_failure_never_breaks_request(self):
        from hub.models import PlatformAction
        self._login_as(self.creator)
        with patch.object(PlatformAction.objects, 'create', side_effect=RuntimeError('db down')):
            res = self.client.patch(self._resource_url(self.res1), {'content': 'New'}, format='json')
        self.assertEqual(res.status_code, 200)
