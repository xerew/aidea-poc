from unittest import mock

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub import translation_flags as tf
from hub.models import Resource, UserProfile
from hub.translation_sync import resync_resource

from .test_translation_flags import make_course

TR = mock.patch('hub.tasks.translate_text', side_effect=lambda t, s, d: f'[{d}] {t}')


class StatusTests(APITestCase):
    def setUp(self):
        self.course, self.m1, self.m2, self.a1, self.a2, self.r1, self.r2 = make_course()

    def status(self):
        self.course.refresh_from_db()
        return self.course.translation_status['el']

    @TR
    def test_sync_on_reviewed_language_stays_reviewed_and_flags(self, _tr):
        tf.set_reviewed(self.course, 'el', True)
        resync_resource(self.r1)
        self.assertEqual(self.status(), 'reviewed')
        self.r1.refresh_from_db()
        self.assertEqual(self.r1.translations['el']['content'], '[el] <p>One</p>')
        self.assertTrue(self.r1.translation_flags['el']['changed'])

    @TR
    def test_sync_on_done_language_stays_done_without_flags(self, _tr):
        resync_resource(self.r1)
        self.assertEqual(self.status(), 'done')
        self.r1.refresh_from_db()
        self.assertFalse(self.r1.translation_flags['el'].get('changed', False))

    def test_sync_marks_updating_while_running(self):
        with mock.patch('hub.tasks.translate_resource_meta.delay') as delay:
            resync_resource(self.r1)
        self.assertEqual(self.status(), 'updating')
        delay.assert_called_once_with(self.r1.id, 'el')

    def test_empty_new_resource_starts_nothing(self):
        empty = Resource.objects.create(activity=self.a1, type='text', order=2)
        with mock.patch('hub.tasks.translate_resource_meta.delay') as delay:
            resync_resource(empty)
        self.assertFalse(delay.called)
        self.assertEqual(self.status(), 'done')

    @TR
    def test_module_full_translates_only_that_module(self, _tr):
        from hub.tasks import translate_module_full
        self.r2.translations = {'el': {'content': 'manual'}}
        self.r2.save()
        translate_module_full(self.m1.id, 'el')
        self.r1.refresh_from_db()
        self.r2.refresh_from_db()
        self.a1.refresh_from_db()
        self.assertEqual(self.r1.translations['el']['content'], '[el] <p>One</p>')
        self.assertEqual(self.a1.translations['el']['title'], '[el] A1')
        self.assertEqual(self.r2.translations['el'], {'content': 'manual'})

    @TR
    def test_whole_course_job_ends_done(self, _tr):
        from hub.tasks import translate_course
        translate_course(self.course.id, 'el')
        self.assertEqual(self.status(), 'done')


class ReviewEndpointTests(APITestCase):
    def test_marking_reviewed_records_it_and_clears_the_list(self):
        admin = User.objects.create_user('ts_admin', password='x')
        UserProfile.objects.create(user=admin, user_type=UserProfile.UserType.ADMIN)
        course, *_rest, r1, _r2 = make_course(creator=admin)
        tf.set_reviewed(course, 'el', True)
        tf.note_machine_translated(r1, course.id, 'el')
        self.client.force_authenticate(admin)
        res = self.client.post(f'/api/authoring/courses/{course.id}/translation-review/', {'language': 'el'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        course.refresh_from_db()
        self.assertEqual((course.translation_status['el'], tf.recheck_items(course, 'el')), ('reviewed', []))
        res = self.client.post(f'/api/authoring/courses/{course.id}/translation-review/',
                               {'language': 'el', 'reviewed': False}, format='json')
        course.refresh_from_db()
        self.assertEqual(course.translation_status['el'], 'done')
        self.assertNotIn('el', course.translation_reviewed_at)
