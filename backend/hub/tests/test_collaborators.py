from django.contrib.auth.models import User
from django.urls import reverse

from hub.models import (
    AssignmentSubmission,
    CourseCollaborator,
    Enrollment,
    Lesson,
    UserProfile,
)

from .test_authoring_courses import AuthoringTestCase


class CollaboratorBase(AuthoringTestCase):
    """Adds an admin and an AIDEA partner on top of the authoring fixtures.
    self.creator authors self.course; self.other_creator is a second creator."""

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(username='admin1', password='testpass123')
        UserProfile.objects.create(user=self.admin, user_type=UserProfile.UserType.ADMIN)
        self.partner = User.objects.create_user(username='partner1', password='testpass123')
        UserProfile.objects.create(user=self.partner, user_type=UserProfile.UserType.AIDEA_PARTNER)

    def _collaborators_url(self):
        return reverse('authoring-course-collaborators', kwargs={'pk': self.course.pk})

    def _collaborator_detail_url(self, user):
        return reverse('authoring-course-collaborator-detail',
                       kwargs={'pk': self.course.pk, 'user_id': user.pk})

    def _detail_url(self):
        return reverse('authoring-course-detail', kwargs={'pk': self.course.pk})

    def _add(self, user, role):
        return CourseCollaborator.objects.create(course=self.course, user=user, role=role)


class CollaboratorManagementTests(CollaboratorBase):
    def test_owner_can_add_co_editor(self):
        self._login_as(self.creator)
        res = self.client.post(self._collaborators_url(),
                               {'user_id': self.other_creator.id, 'role': 'co_editor'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(CourseCollaborator.objects.filter(
            course=self.course, user=self.other_creator, role='co_editor').exists())

    def test_admin_can_add_translator(self):
        self._login_as(self.admin)
        res = self.client.post(self._collaborators_url(),
                               {'user_id': self.partner.id, 'role': 'translator'}, format='json')
        self.assertEqual(res.status_code, 201)

    def test_co_editor_cannot_manage_collaborators(self):
        self._add(self.other_creator, 'co_editor')
        self._login_as(self.other_creator)
        res = self.client.post(self._collaborators_url(),
                               {'user_id': self.partner.id, 'role': 'translator'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_cannot_add_teacher(self):
        self._login_as(self.creator)
        res = self.client.post(self._collaborators_url(),
                               {'user_id': self.teacher.id, 'role': 'co_editor'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_cannot_add_owner(self):
        self._login_as(self.creator)
        res = self.client.post(self._collaborators_url(),
                               {'user_id': self.creator.id, 'role': 'co_editor'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_invalid_role_rejected(self):
        self._login_as(self.creator)
        res = self.client.post(self._collaborators_url(),
                               {'user_id': self.other_creator.id, 'role': 'boss'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_adding_existing_updates_role(self):
        self._add(self.other_creator, 'translator')
        self._login_as(self.creator)
        res = self.client.post(self._collaborators_url(),
                               {'user_id': self.other_creator.id, 'role': 'co_editor'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(CourseCollaborator.objects.get(
            course=self.course, user=self.other_creator).role, 'co_editor')

    def test_owner_can_remove(self):
        self._add(self.other_creator, 'co_editor')
        self._login_as(self.creator)
        res = self.client.delete(self._collaborator_detail_url(self.other_creator))
        self.assertEqual(res.status_code, 204)
        self.assertFalse(CourseCollaborator.objects.filter(
            course=self.course, user=self.other_creator).exists())

    def test_co_editor_cannot_remove(self):
        self._add(self.other_creator, 'co_editor')
        self._add(self.partner, 'translator')
        self._login_as(self.other_creator)
        res = self.client.delete(self._collaborator_detail_url(self.partner))
        self.assertEqual(res.status_code, 403)

    def test_list_collaborators(self):
        self._add(self.other_creator, 'co_editor')
        self._login_as(self.creator)
        res = self.client.get(self._collaborators_url())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['role'], 'co_editor')

    def test_candidates_lists_creators_and_partners_not_teachers(self):
        self._login_as(self.creator)
        res = self.client.get(reverse('authoring-collaborator-candidates'))
        self.assertEqual(res.status_code, 200)
        ids = {row['id'] for row in res.data}
        self.assertIn(self.other_creator.id, ids)
        self.assertIn(self.partner.id, ids)
        self.assertNotIn(self.teacher.id, ids)


class CoEditorPermissionTests(CollaboratorBase):
    def test_co_editor_can_edit_source(self):
        self._add(self.other_creator, 'co_editor')
        self._login_as(self.other_creator)
        res = self.client.patch(self._detail_url(), {'title': 'Edited by co-editor'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Edited by co-editor')

    def test_co_editor_can_publish(self):
        self._add(self.other_creator, 'co_editor')
        self._login_as(self.other_creator)
        res = self.client.post(reverse('authoring-course-publish', kwargs={'pk': self.course.pk}))
        self.assertEqual(res.status_code, 200)
        self.course.refresh_from_db()
        self.assertTrue(self.course.is_published)

    def test_co_editor_cannot_delete(self):
        self._add(self.other_creator, 'co_editor')
        self._login_as(self.other_creator)
        res = self.client.delete(self._detail_url())
        self.assertEqual(res.status_code, 403)

    def test_non_collaborator_cannot_edit(self):
        self._login_as(self.other_creator)
        res = self.client.patch(self._detail_url(), {'title': 'Nope'}, format='json')
        self.assertEqual(res.status_code, 403)


class TranslatorPermissionTests(CollaboratorBase):
    def setUp(self):
        super().setUp()
        self._add(self.other_creator, 'translator')
        self._login_as(self.other_creator)

    def test_translator_cannot_edit_source(self):
        res = self.client.patch(self._detail_url(), {'title': 'Hacked'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_translator_can_edit_translation(self):
        res = self.client.patch(f'{self._detail_url()}?lang=el', {'title': 'Τίτλος'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.translations['el']['title'], 'Τίτλος')

    def test_translator_cannot_publish(self):
        res = self.client.post(reverse('authoring-course-publish', kwargs={'pk': self.course.pk}))
        self.assertEqual(res.status_code, 403)


class CoEditorReviewScopeTests(CollaboratorBase):
    def setUp(self):
        super().setUp()
        self.assignment = Lesson.objects.create(
            module=self.module1, title='Task', lesson_type='assignment', order=1,
        )
        self.learner = User.objects.create_user(username='learner1', password='testpass123')
        UserProfile.objects.create(user=self.learner, user_type=UserProfile.UserType.TEACHER)
        Enrollment.objects.create(user=self.learner, course=self.course)
        self.submission = AssignmentSubmission.objects.create(
            user=self.learner, lesson=self.assignment, text='my answer',
        )

    def test_co_editor_sees_and_reviews(self):
        self._add(self.other_creator, 'co_editor')
        self._login_as(self.other_creator)
        queue = self.client.get(reverse('review-queue'))
        self.assertEqual(queue.status_code, 200)
        self.assertTrue(any(r['id'] == self.submission.id for r in queue.data))
        res = self.client.post(reverse('review-action', kwargs={'pk': self.submission.pk}),
                               {'action': 'approve'}, format='json')
        self.assertEqual(res.status_code, 200)

    def test_translator_cannot_review(self):
        self._add(self.other_creator, 'translator')
        self._login_as(self.other_creator)
        res = self.client.post(reverse('review-action', kwargs={'pk': self.submission.pk}),
                               {'action': 'approve'}, format='json')
        self.assertEqual(res.status_code, 403)


class CollaboratorSerializerFlagsTests(CollaboratorBase):
    def _flags_for(self, user):
        self._login_as(user)
        return self.client.get(self._detail_url()).data

    def test_author_flags(self):
        d = self._flags_for(self.creator)
        self.assertEqual(d['my_role'], 'author')
        self.assertTrue(d['can_edit'] and d['can_translate'] and d['can_manage'])

    def test_co_editor_flags(self):
        self._add(self.other_creator, 'co_editor')
        d = self._flags_for(self.other_creator)
        self.assertEqual(d['my_role'], 'co_editor')
        self.assertTrue(d['can_edit'] and d['can_translate'])
        self.assertFalse(d['can_manage'])

    def test_translator_flags(self):
        self._add(self.other_creator, 'translator')
        d = self._flags_for(self.other_creator)
        self.assertEqual(d['my_role'], 'translator')
        self.assertFalse(d['can_edit'])
        self.assertTrue(d['can_translate'])
        self.assertFalse(d['can_manage'])

    def test_non_collaborator_flags(self):
        d = self._flags_for(self.other_creator)
        self.assertIsNone(d['my_role'])
        self.assertFalse(d['can_edit'] or d['can_translate'] or d['can_manage'])
