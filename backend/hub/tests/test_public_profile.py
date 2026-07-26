from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, Enrollment, LearningPillar, Subject, UserProfile


def make_user(username, role, **profile):
    u = User.objects.create_user(username=username, password='pass12345',
                                 first_name=username.title(), last_name='X', email=f'{username}@x.com')
    UserProfile.objects.create(user=u, user_type=role, avatar_initials='XX', **profile)
    return u


class PublicProfileTests(APITestCase):
    def setUp(self):
        self.viewer = make_user('viewer', UserProfile.UserType.TEACHER)
        self.client.force_authenticate(self.viewer)
        self.pillar = LearningPillar.objects.create(name='P', slug='p-pp', order=1)

    def _url(self, user):
        return reverse('public-profile', kwargs={'pk': user.id})

    def test_requires_auth(self):
        self.client.force_authenticate(None)
        u = make_user('someone', UserProfile.UserType.TEACHER, profile_public=True)
        self.assertEqual(self.client.get(self._url(u)).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_user_404(self):
        self.assertEqual(self.client.get(reverse('public-profile', kwargs={'pk': 999999})).status_code,
                         status.HTTP_404_NOT_FOUND)

    def test_private_profile_returns_minimal(self):
        u = make_user('priv', UserProfile.UserType.TEACHER, profile_public=False, bio='secret')
        res = self.client.get(self._url(u))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['is_public'])
        self.assertIn('name', res.data)
        self.assertNotIn('bio', res.data)

    def test_public_teacher_profile(self):
        subject = Subject.objects.get(slug='mathematics')
        u = make_user('pubt', UserProfile.UserType.TEACHER, profile_public=True,
                      bio='Hi', subject=subject, school='Athens High', competency_score=5)
        res = self.client.get(self._url(u))
        self.assertTrue(res.data['is_public'])
        self.assertEqual(res.data['bio'], 'Hi')
        self.assertEqual(res.data['subject_name'], 'Mathematics')
        self.assertEqual(res.data['school'], 'Athens High')
        self.assertEqual(res.data['competency']['level'], 'advanced')
        # No share_progress -> no progress block.
        self.assertNotIn('progress', res.data)

    def test_progress_only_when_shared(self):
        u = make_user('pubp', UserProfile.UserType.TEACHER, profile_public=True, share_progress=True)
        course = Course.objects.create(title='C', pillar=self.pillar, is_published=True)
        Enrollment.objects.create(user=u, course=course, progress_pct=100)
        res = self.client.get(self._url(u))
        self.assertEqual(res.data['progress'], {'completed': 1, 'in_progress': 0})

    def test_public_creator_lists_published_courses(self):
        u = make_user('pubc', UserProfile.UserType.CONTENT_CREATOR, profile_public=True)
        Course.objects.create(title='Live', pillar=self.pillar, is_published=True, created_by=u)
        Course.objects.create(title='Draft', pillar=self.pillar, is_published=False, created_by=u)
        res = self.client.get(self._url(u))
        titles = [c['title'] for c in res.data['authored_courses']]
        self.assertEqual(titles, ['Live'])

    def test_admin_has_no_authored_courses_block(self):
        u = make_user('puba', UserProfile.UserType.ADMIN, profile_public=True)
        res = self.client.get(self._url(u))
        self.assertNotIn('authored_courses', res.data)
