from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, Lesson, Module, UserProfile


def make_user(username, role):
    u = User.objects.create_user(username=username, password='pass12345')
    UserProfile.objects.create(user=u, user_type=role, avatar_initials='XX')
    return u


class TranslationReviewTests(APITestCase):
    def setUp(self):
        self.creator = make_user('tr_author', UserProfile.UserType.CONTENT_CREATOR)
        self.other = make_user('tr_other', UserProfile.UserType.CONTENT_CREATOR)
        self.partner = make_user('tr_partner', UserProfile.UserType.AIDEA_PARTNER)
        self.admin = make_user('tr_admin', UserProfile.UserType.ADMIN)
        self.teacher = make_user('tr_teacher', UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P', slug='p-tr', order=1)
        self.course = Course.objects.create(
            title='C', pillar=pillar, source_language='en', is_published=False,
            created_by=self.creator, translation_status={'el': 'done'},
        )
        self.url = f'/api/authoring/courses/{self.course.id}/translation-review/'

    def _review(self, user, language='el', reviewed=True):
        self.client.force_authenticate(user)
        return self.client.post(self.url, {'language': language, 'reviewed': reviewed}, format='json')

    def test_author_marks_reviewed(self):
        res = self._review(self.creator)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['translation_status']['el'], 'reviewed')

    def test_partner_and_admin_can_review(self):
        self.assertEqual(self._review(self.partner).data['translation_status']['el'], 'reviewed')
        # reset then admin
        self.course.translation_status = {'el': 'done'}
        self.course.save()
        self.assertEqual(self._review(self.admin).data['translation_status']['el'], 'reviewed')

    def test_non_author_creator_forbidden(self):
        self.assertEqual(self._review(self.other).status_code, 403)

    def test_teacher_forbidden(self):
        self.assertEqual(self._review(self.teacher).status_code, 403)

    def test_unmark_review(self):
        self.course.translation_status = {'el': 'reviewed'}
        self.course.save()
        res = self._review(self.creator, reviewed=False)
        self.assertEqual(res.data['translation_status']['el'], 'done')

    def test_cannot_review_untranslated_language(self):
        self.assertEqual(self._review(self.creator, language='fr').status_code, 400)

    def test_cannot_review_pending(self):
        self.course.translation_status = {'el': 'pending'}
        self.course.save()
        self.assertEqual(self._review(self.creator).status_code, 400)


@patch('hub.translation._ollama_generate', return_value='TR')
class TranslationResyncTests(APITestCase):
    def setUp(self):
        self.creator = make_user('rs_author', UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-rs', order=1)
        self.course = Course.objects.create(
            title='C', description='D', pillar=pillar, source_language='en',
            is_published=False, created_by=self.creator,
            translation_status={'el': 'reviewed'},
            translations={'el': {'title': 'OLD', 'description': 'OLD'}},
        )
        self.module = Module.objects.create(
            course=self.course, title='M', description='MD', order=1,
            translations={'el': {'title': 'OLD', 'description': 'OLD'}},
        )
        self.lesson1 = Lesson.objects.create(
            module=self.module, title='L1', description='D1', content='Content one',
            lesson_type='text', order=1, translations={'el': {'title': 'OLD1', 'content': 'OLD1'}},
        )
        self.lesson2 = Lesson.objects.create(
            module=self.module, title='L2', description='D2', content='Content two',
            lesson_type='text', order=2, translations={'el': {'title': 'KEEP2', 'content': 'KEEP2'}},
        )
        self.client.force_authenticate(self.creator)

    def test_editing_lesson_retranslates_only_that_lesson(self, _mock):
        url = f'/api/authoring/courses/{self.course.id}/modules/{self.module.id}/lessons/{self.lesson1.id}/'
        res = self.client.patch(url, {'content': 'Brand new content'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.lesson1.refresh_from_db()
        self.lesson2.refresh_from_db()
        self.course.refresh_from_db()
        # Changed lesson re-translated…
        self.assertEqual(self.lesson1.translations['el']['content'], 'TR')
        # …the other lesson left intact…
        self.assertEqual(self.lesson2.translations['el']['content'], 'KEEP2')
        # …and the human-reviewed sign-off dropped back to needs-review.
        self.assertEqual(self.course.translation_status['el'], 'done')

    def test_editing_course_meta_retranslates_meta(self, _mock):
        url = f'/api/authoring/courses/{self.course.id}/'
        self.client.patch(url, {'title': 'New title'}, format='json')
        self.course.refresh_from_db()
        self.assertEqual(self.course.translations['el']['title'], 'TR')
        self.assertEqual(self.course.translation_status['el'], 'done')

    def test_new_lesson_is_translated(self, _mock):
        url = f'/api/authoring/courses/{self.course.id}/modules/{self.module.id}/lessons/'
        res = self.client.post(url, {'title': 'L3', 'lesson_type': 'text', 'content': 'Third'}, format='json')
        self.assertEqual(res.status_code, 201)
        lesson = Lesson.objects.get(pk=res.data['id'])
        self.assertEqual(lesson.translations['el']['content'], 'TR')

    def test_untranslated_course_is_not_touched(self, _mock):
        self.course.translation_status = {}
        self.course.save()
        url = f'/api/authoring/courses/{self.course.id}/modules/{self.module.id}/lessons/{self.lesson1.id}/'
        self.client.patch(url, {'content': 'Another edit'}, format='json')
        self.course.refresh_from_db()
        self.assertEqual(self.course.translation_status, {})

    def test_retranslating_one_language_keeps_the_other(self, _mock):
        # Re-translating one language must not drop another language's data
        # (the atomic-merge fix for the concurrent lost-update bug).
        from hub.tasks import _translate_course_meta
        self.course.translations = {'el': {'title': 'EL'}, 'fr': {'title': 'FR'}}
        self.course.save()
        _translate_course_meta(self.course, 'el')
        self.course.refresh_from_db()
        self.assertEqual(self.course.translations['fr']['title'], 'FR')  # untouched
        self.assertEqual(self.course.translations['el']['title'], 'TR')  # re-translated
