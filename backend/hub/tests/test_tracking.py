import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import (
    Activity,
    Course,
    Enrollment,
    LearnerActivityConfig,
    LearningEvent,
    LearningPillar,
    Module,
    Resource,
    ResourceVisit,
    UserProfile,
)


class TrackingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tm_user', password='pass12345')
        pillar = LearningPillar.objects.create(name='P', slug='p-tm', order=1)
        self.course = Course.objects.create(
            title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        self.module = Module.objects.create(course=self.course, title='M', order=1)
        self.activity = Activity.objects.create(module=self.module, title='A', order=1)
        self.resource = Resource.objects.create(activity=self.activity, type='text', order=1)

    def _visit(self, key):
        now = timezone.now()
        return ResourceVisit.objects.create(
            user=self.user, resource=self.resource, activity=self.activity,
            module=self.module, course=self.course, visit_key=key, page_key=uuid.uuid4(),
            started_at=now, last_seen_at=now,
        )

    def test_visit_defaults(self):
        v = self._visit(uuid.uuid4())
        self.assertEqual((v.active_seconds, v.visible_seconds), (0, 0))
        self.assertFalse(v.completed_during)
        self.assertEqual(v.media_progress, {})

    def test_visit_key_unique_per_user(self):
        key = uuid.uuid4()
        self._visit(key)
        with self.assertRaises(IntegrityError):
            self._visit(key)

    def test_event_key_unique_per_user(self):
        key = uuid.uuid4()
        fields = dict(
            user=self.user, resource=self.resource, course=self.course, event_key=key,
            event_type=LearningEvent.Type.PDF_OPEN, occurred_at=timezone.now(),
        )
        LearningEvent.objects.create(**fields)
        with self.assertRaises(IntegrityError):
            LearningEvent.objects.create(**fields)

    def test_tracking_enabled_by_default(self):
        self.assertTrue(LearnerActivityConfig.get().tracking_enabled)


class TrackingEndpointTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('te_user', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P', slug='p-te', order=1)
        self.course = Course.objects.create(
            title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        self.module = Module.objects.create(course=self.course, title='M', order=1)
        self.activity = Activity.objects.create(module=self.module, title='A', order=1)
        self.text = Resource.objects.create(activity=self.activity, type='text', order=1)
        self.video = Resource.objects.create(activity=self.activity, type='video', order=2)
        Enrollment.objects.create(user=self.user, course=self.course)
        other = Course.objects.create(
            title='Other', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        other_module = Module.objects.create(course=other, title='OM', order=1)
        other_activity = Activity.objects.create(module=other_module, title='OA', order=1)
        self.foreign = Resource.objects.create(activity=other_activity, type='text', order=1)
        self.page = uuid.uuid4()
        self.url = reverse('tracking')
        self.client.force_authenticate(self.user)

    def post(self, visits=(), events=(), page=None):
        payload = {'page_key': str(page or self.page), 'visits': list(visits), 'events': list(events)}
        return self.client.post(self.url, payload, format='json')

    def visit(self, key, resource=None, **fields):
        return {'visit_key': str(key), 'resource_id': (resource or self.text).id, **fields}

    def test_first_message_creates_visit_with_context(self):
        key = uuid.uuid4()
        res = self.post([self.visit(key, active_s=20, visible_s=28, context={
            'language': 'el', 'device': 'mobile', 'local_hour': 14, 'tz_offset_minutes': 180,
        })])
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {'visits': 1, 'events': 0})
        v = ResourceVisit.objects.get(user=self.user, visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (20, 28))
        self.assertEqual(
            (v.activity_id, v.module_id, v.course_id, v.page_key),
            (self.activity.id, self.module.id, self.course.id, self.page),
        )
        self.assertEqual((v.language, v.device, v.local_hour, v.tz_offset_minutes), ('el', 'mobile', 14, 180))
        self.assertAlmostEqual((v.last_seen_at - v.started_at).total_seconds(), 28, delta=1)

    def test_resending_the_same_totals_is_harmless(self):
        key = uuid.uuid4()
        self.post([self.visit(key, active_s=20, visible_s=25)])
        self.post([self.visit(key, active_s=20, visible_s=25)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (20, 25))
        self.assertEqual(ResourceVisit.objects.count(), 1)

    def test_growth_per_message_capped(self):
        key = uuid.uuid4()
        self.post([self.visit(key, active_s=20, visible_s=20)])
        self.post([self.visit(key, active_s=500, visible_s=500)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (55, 55))

    def test_first_message_capped_too(self):
        key = uuid.uuid4()
        self.post([self.visit(key, active_s=900, visible_s=900)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (35, 35))

    def test_active_never_exceeds_on_screen(self):
        key = uuid.uuid4()
        self.post([self.visit(key, active_s=30, visible_s=10)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (10, 10))

    def test_totals_never_go_backwards(self):
        key = uuid.uuid4()
        self.post([self.visit(key, active_s=30, visible_s=30)])
        self.post([self.visit(key, active_s=5, visible_s=-40)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (30, 30))

    def test_not_enrolled_resource_ignored(self):
        res = self.post([self.visit(uuid.uuid4(), self.foreign, active_s=10, visible_s=10)])
        self.assertEqual(res.data, {'visits': 0, 'events': 0})
        self.assertFalse(ResourceVisit.objects.exists())

    def test_visit_key_cannot_switch_resource(self):
        key = uuid.uuid4()
        self.post([self.visit(key, self.text, active_s=10, visible_s=10)])
        self.post([self.visit(key, self.video, active_s=30, visible_s=30)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.resource_id, v.visible_seconds), (self.text.id, 10))

    def test_invalid_context_values_dropped(self):
        key = uuid.uuid4()
        self.post([self.visit(key, visible_s=5, context={
            'language': 'el-GR-extra-long', 'device': 'fridge', 'local_hour': 99, 'tz_offset_minutes': 5000,
        })])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.language, v.device, v.local_hour, v.tz_offset_minutes), ('el-GR-ex', '', None, None))

    def test_media_progress_keeps_maximums(self):
        key = uuid.uuid4()
        self.post([self.visit(key, self.video, visible_s=10, media={'covered_pct': 40, 'furthest_s': 120, 'duration_s': 300})])
        self.post([self.visit(key, self.video, visible_s=20, media={'covered_pct': 30, 'furthest_s': 60, 'duration_s': 300})])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual(v.media_progress, {'covered_pct': 40, 'furthest_s': 120, 'duration_s': 300})

    def test_completed_flag(self):
        key = uuid.uuid4()
        self.post([self.visit(key, visible_s=5, completed=True)])
        self.post([self.visit(key, visible_s=8)])
        self.assertTrue(ResourceVisit.objects.get(visit_key=key).completed_during)

    def test_events_stored_and_deduplicated(self):
        key, ev = uuid.uuid4(), uuid.uuid4()
        event = {
            'event_key': str(ev), 'visit_key': str(key), 'resource_id': self.video.id,
            'type': 'video_seek', 'at': timezone.now().isoformat(), 'data': {'from': 30, 'to': 90},
        }
        self.post([self.visit(key, self.video, visible_s=5)], [event])
        self.post([self.visit(key, self.video, visible_s=5)], [event])
        stored = LearningEvent.objects.get()
        self.assertEqual(stored.event_type, 'video_seek')
        self.assertEqual(stored.data, {'from': 30, 'to': 90})
        self.assertEqual(stored.visit.visit_key, key)
        self.assertEqual(stored.course_id, self.course.id)

    def test_unknown_event_types_and_extra_data_dropped(self):
        self.post([], [
            {'event_key': str(uuid.uuid4()), 'resource_id': self.text.id, 'type': 'keylogger', 'data': {}},
            {'event_key': str(uuid.uuid4()), 'resource_id': self.text.id, 'type': 'quiz_answer',
             'data': {'question_index': 1, 'selected': 0, 'seconds_on_question': 4.25, 'secret': 'x', 'selected_text': 'y'}},
        ])
        stored = LearningEvent.objects.get()
        self.assertEqual(stored.data, {'question_index': 1, 'selected': 0, 'seconds_on_question': 4.2})

    def test_event_time_in_future_or_garbage_replaced_by_now(self):
        for at in [(timezone.now() + timedelta(days=2)).isoformat(), 'yesterday', '2026-13-45T99:00:00Z']:
            self.post([], [{'event_key': str(uuid.uuid4()), 'resource_id': self.text.id, 'type': 'pdf_open', 'at': at}])
        self.assertEqual(LearningEvent.objects.count(), 3)
        for ev in LearningEvent.objects.all():
            self.assertLess(abs((timezone.now() - ev.occurred_at).total_seconds()), 60)

    def test_tracking_switched_off_returns_204_and_stores_nothing(self):
        config = LearnerActivityConfig.get()
        config.tracking_enabled = False
        config.save()
        res = self.post([self.visit(uuid.uuid4(), visible_s=5)])
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResourceVisit.objects.exists())

    def test_malformed_payloads_do_not_fail(self):
        payloads = [
            [],
            {'visits': {}},
            {'page_key': 'not-a-uuid', 'visits': [self.visit(uuid.uuid4(), visible_s=5)]},
            {'page_key': str(self.page), 'visits': ['a', 1, None], 'events': 'zzz'},
            {'page_key': str(self.page), 'visits': [{'visit_key': 'nope', 'resource_id': '1'}]},
            {'page_key': str(self.page), 'visits': [self.visit(uuid.uuid4(), visible_s='lots', media='x', context=[1])]},
        ]
        for payload in payloads:
            res = self.client.post(self.url, payload, format='json')
            self.assertEqual(res.status_code, status.HTTP_200_OK, payload)
        # Only the last one names a real visit; its non-numeric totals are ignored.
        self.assertEqual(ResourceVisit.objects.get().visible_seconds, 0)

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.post().status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        'DEFAULT_THROTTLE_RATES': {**settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'], 'tracking': '2/min'},
    })
    def test_throttled_per_user(self):
        cache.clear()
        codes = [self.post().status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])
