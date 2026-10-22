from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub import translation_flags as tf
from hub.models import Activity, Course, LearningPillar, Module, Resource, UserProfile


def make_course(creator=None):
    pillar = LearningPillar.objects.get_or_create(slug='p-tf', defaults={'name': 'P', 'order': 1})[0]
    course = Course.objects.create(title='C', pillar=pillar, level='beginner', duration_hours=1, created_by=creator,
                                   translation_status={'el': 'done'})
    m1 = Module.objects.create(course=course, title='M1', order=1)
    m2 = Module.objects.create(course=course, title='M2', order=2)
    a1 = Activity.objects.create(module=m1, title='A1', order=1)
    a2 = Activity.objects.create(module=m2, title='A2', order=1)
    r1 = Resource.objects.create(activity=a1, type='text', order=1, content='<p>One</p>')
    r2 = Resource.objects.create(activity=a2, type='text', order=1, content='<p>Two</p>')
    return course, m1, m2, a1, a2, r1, r2


def flags(obj, lang='el'):
    obj.refresh_from_db()
    return obj.translation_flags.get(lang, {})


class FlagFunctionTests(APITestCase):
    def setUp(self):
        self.course, self.m1, self.m2, self.a1, self.a2, self.r1, self.r2 = make_course()

    def test_machine_translation_without_review_only_clears_edited(self):
        tf.mark_edited(self.r1, 'el')
        tf.note_machine_translated(self.r1, self.course.id, 'el')
        self.assertEqual(flags(self.r1), {'edited': False})

    def test_machine_translation_after_review_flags_and_notes_replaced_edits(self):
        tf.set_reviewed(self.course, 'el', True)
        tf.mark_edited(self.r1, 'el')
        tf.note_machine_translated(self.r1, self.course.id, 'el')
        tf.note_machine_translated(self.r2, self.course.id, 'el')
        self.assertEqual(flags(self.r1), {'edited': False, 'changed': True, 'replaced_edit': True})
        self.assertEqual(flags(self.r2), {'edited': False, 'changed': True})

    def test_review_clears_the_recheck_list(self):
        tf.set_reviewed(self.course, 'el', True)
        tf.note_machine_translated(self.r1, self.course.id, 'el')
        self.assertEqual([i['id'] for i in tf.recheck_items(self.course, 'el')], [self.r1.id])
        tf.set_reviewed(self.course, 'el', True)
        self.course.refresh_from_db()
        self.assertEqual(tf.recheck_items(self.course, 'el'), [])
        self.assertIn('el', self.course.translation_reviewed_at)
        self.assertEqual(self.course.translation_status['el'], 'reviewed')

    def test_unmark_and_forget(self):
        tf.set_reviewed(self.course, 'el', True)
        tf.set_reviewed(self.course, 'el', False)
        self.course.refresh_from_db()
        self.assertNotIn('el', self.course.translation_reviewed_at)
        self.assertEqual(self.course.translation_status['el'], 'done')
        tf.mark_edited(self.r1, 'el')
        tf.forget_review(self.course, 'el')
        self.assertEqual(flags(self.r1), {})

    def test_recheck_items_shape(self):
        tf.set_reviewed(self.course, 'el', True)
        for obj in (self.course, self.m1, self.a1, self.r1):
            tf.note_machine_translated(obj, self.course.id, 'el')
        items = {i['kind']: i for i in tf.recheck_items(self.course, 'el')}
        self.assertEqual(set(items), {'course', 'module', 'activity', 'resource'})
        self.assertEqual((items['resource']['module_id'], items['resource']['activity_id']), (self.m1.id, self.a1.id))
        self.assertEqual((items['activity']['module_id'], items['activity']['activity_id']), (self.m1.id, self.a1.id))
        self.assertEqual(items['module']['module_id'], self.m1.id)
        self.assertIsNone(items['course']['module_id'])

    def test_count_edited_per_scope(self):
        for obj in (self.course, self.m1, self.a1, self.r1, self.r2):
            tf.mark_edited(obj, 'el')
        self.assertEqual(tf.count_edited(self.course, 'el', 'course'), 5)
        self.assertEqual(tf.count_edited(self.course, 'el', 'details'), 1)
        self.assertEqual(tf.count_edited(self.course, 'el', 'module', module_id=self.m1.id), 3)
        self.assertEqual(tf.count_edited(self.course, 'el', 'activity', activity_id=self.a1.id), 2)


class ManualEditTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user('tf_cc', password='x')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.m1, _, self.a1, _, self.r1, _ = make_course(creator=self.creator)
        self.client.force_authenticate(self.creator)

    def test_manual_translation_edits_set_edited_and_payload_shows_flags(self):
        url = reverse('authoring-resource-detail', kwargs={'pk': self.course.id, 'module_pk': self.m1.id,
                                                           'lesson_pk': self.a1.id, 'resource_pk': self.r1.id})
        res = self.client.patch(f'{url}?lang=el', {'content': '<p>Ένα</p>'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['translation_flags'], {'el': {'edited': True}})
        res = self.client.patch(f'/api/authoring/courses/{self.course.id}/?lang=el', {'title': 'Γ'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(flags(self.course)['edited'])
        self.assertIn('translation_reviewed_at', res.data)
        self.client.patch(f'/api/authoring/courses/{self.course.id}/modules/{self.m1.id}/?lang=el', {'title': 'Μ'}, format='json')
        self.assertTrue(flags(self.m1)['edited'])
        self.client.patch(f'/api/authoring/courses/{self.course.id}/modules/{self.m1.id}/lessons/{self.a1.id}/?lang=el',
                          {'title': 'Δ'}, format='json')
        self.assertTrue(flags(self.a1)['edited'])
