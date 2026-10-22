from unittest import mock

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub import translation_flags as tf
from hub.models import UserProfile

from .test_translation_flags import make_course

ONLINE = mock.patch('hub.translation_health.check_now', return_value={'online': True})
TR = mock.patch('hub.tasks.translate_text', side_effect=lambda t, s, d: f'[{d}] {t}')


class TargetedRetranslationTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user('trt_cc', password='x')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.m1, self.m2, self.a1, self.a2, self.r1, self.r2 = make_course(creator=self.creator)
        self.r2.translations = {'el': {'content': 'manual two'}}
        self.r2.save()
        self.url = f'/api/authoring/courses/{self.course.id}/translate/'
        self.client.force_authenticate(self.creator)

    def post(self, **body):
        return self.client.post(self.url, {'language': 'el', **body}, format='json')

    @ONLINE
    @TR
    def test_activity_scope_touches_only_that_activity(self, _tr, _online):
        tf.set_reviewed(self.course, 'el', True)
        res = self.post(scope='activity', activity_id=self.a1.id)
        self.assertEqual(res.status_code, 202, res.data)
        for obj in (self.r1, self.r2, self.a1, self.course):
            obj.refresh_from_db()
        self.assertEqual(self.r1.translations['el']['content'], '[el] <p>One</p>')
        self.assertEqual(self.r2.translations['el'], {'content': 'manual two'})
        self.assertEqual(self.course.translation_status['el'], 'reviewed')
        self.assertEqual({i['id'] for i in tf.recheck_items(self.course, 'el') if i['kind'] == 'resource'}, {self.r1.id})

    @ONLINE
    @TR
    def test_module_and_details_scopes(self, _tr, _online):
        self.assertEqual(self.post(scope='module', module_id=self.m1.id).status_code, 202)
        self.r2.refresh_from_db()
        self.assertEqual(self.r2.translations['el'], {'content': 'manual two'})
        self.assertEqual(self.post(scope='details').status_code, 202)
        self.course.refresh_from_db()
        self.assertEqual(self.course.translations['el']['title'], '[el] C')

    @ONLINE
    @TR
    def test_whole_course_forgets_the_review(self, _tr, _online):
        tf.set_reviewed(self.course, 'el', True)
        tf.mark_edited(self.r2, 'el')
        self.assertEqual(self.post().status_code, 202)
        self.course.refresh_from_db()
        self.assertEqual(self.course.translation_status['el'], 'done')
        self.assertNotIn('el', self.course.translation_reviewed_at)
        self.assertEqual(tf.count_edited(self.course, 'el', 'course'), 0)

    @ONLINE
    def test_partial_scope_validation(self, _online):
        other, *_ = make_course()
        other_module = other.modules.first()
        self.assertEqual(self.post(scope='activity', activity_id=other_module.lessons.first().id).status_code, 400)
        self.assertEqual(self.post(scope='module', module_id=other_module.id).status_code, 400)
        self.assertEqual(self.post(scope='module', module_id='abc').status_code, 400)
        self.assertEqual(self.post(scope='weird').status_code, 400)
        self.assertEqual(self.client.post(self.url, {'language': 'fr', 'scope': 'details'}, format='json').status_code, 400)

    def test_changes_endpoint(self):
        tf.set_reviewed(self.course, 'el', True)
        tf.note_machine_translated(self.r1, self.course.id, 'el')
        tf.mark_edited(self.r2, 'el')
        url = reverse('authoring-course-translation-changes', kwargs={'pk': self.course.id})
        res = self.client.get(url, {'language': 'el'})
        self.assertEqual([i['id'] for i in res.data['items']], [self.r1.id])
        res = self.client.get(url, {'language': 'el', 'edited': 1, 'scope': 'module', 'module_id': self.m2.id})
        self.assertEqual(res.data, {'edited_count': 1})
        other = User.objects.create_user('trt_o', password='x')
        UserProfile.objects.create(user=other)
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(url, {'language': 'el'}).status_code, 403)
