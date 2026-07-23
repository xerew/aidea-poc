from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, Subject, UserProfile


class SubjectsEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='subj_teacher', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.url = reverse('subjects')

    def test_requires_auth(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lists_active_subjects(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # The migration seeds 17 subjects.
        self.assertEqual(len(res.data), 17)
        self.assertEqual(set(res.data[0].keys()), {'id', 'name', 'slug'})

    def test_excludes_inactive_subjects(self):
        Subject.objects.filter(slug='music').update(is_active=False)
        self.client.force_authenticate(self.user)
        res = self.client.get(self.url)
        slugs = [s['slug'] for s in res.data]
        self.assertNotIn('music', slugs)


class CourseSubjectsAuthoringTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='subj_cc', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.pillar = LearningPillar.objects.create(name='P', slug='p-subj', order=1)
        self.physics = Subject.objects.get(slug='physics')
        self.astronomy = Subject.objects.get(slug='astronomy')
        self.client.force_authenticate(self.creator)

    def test_create_course_with_subjects(self):
        res = self.client.post(reverse('authoring-courses'), {
            'title': 'Astro course', 'description': 'd', 'pillar_id': self.pillar.id,
            'level': 'beginner', 'duration_hours': 1,
            'subject_ids': [self.physics.id, self.astronomy.id],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        slugs = {s['slug'] for s in res.data['subjects']}
        self.assertEqual(slugs, {'physics', 'astronomy'})
        course = Course.objects.get(id=res.data['id'])
        self.assertEqual(course.subjects.count(), 2)

    def test_patch_course_subjects(self):
        course = Course.objects.create(
            title='C', pillar=self.pillar, level='beginner', duration_hours=1,
            created_by=self.creator,
        )
        course.subjects.set([self.physics])
        url = reverse('authoring-course-detail', kwargs={'pk': course.pk})
        res = self.client.patch(url, {'subject_ids': [self.astronomy.id]}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([s['slug'] for s in res.data['subjects']], ['astronomy'])
        self.assertEqual(list(course.subjects.values_list('slug', flat=True)), ['astronomy'])
