from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, UserProfile

from .fixtures import CourseFixture, make_user


class CourseAnalyticsApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.f = CourseFixture()
        cls.outsider = make_user('la_other', UserProfile.UserType.CONTENT_CREATOR)
        cls.admin = make_user('la_admin', UserProfile.UserType.ADMIN)

    def url(self, name, **kw):
        return reverse(name, kwargs={'pk': self.f.course.id, **kw})

    def test_author_gets_content_tree(self):
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(self.url('analytics-course-content'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['learners'], 6)
        self.assertEqual([m['title'] for m in res.data['modules']], ['Basics', 'Practice'])

    def test_learners_list_with_status(self):
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(self.url('analytics-course-learners'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        status_by_name = {row['name']: row['status'] for row in res.data['learners']}
        self.assertEqual(status_by_name['Ada Byte'], 'on_track')
        self.assertEqual(status_by_name['di'], 'stuck')

    def test_learner_timeline(self):
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(self.url('analytics-course-learner', user_id=self.f.ada.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['learner']['email'], 'ada@example.org')
        self.assertEqual(len(res.data['modules']), 2)

    def test_timeline_404_for_someone_not_enrolled(self):
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(self.url('analytics-course-learner', user_id=self.outsider.id))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_creator_gets_404(self):
        self.client.force_authenticate(self.outsider)
        for name in ('analytics-course-content', 'analytics-course-learners'):
            self.assertEqual(self.client.get(self.url(name)).status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_forbidden(self):
        self.client.force_authenticate(self.f.ada)
        self.assertEqual(self.client.get(self.url('analytics-course-content')).status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_sees_any_course(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.url('analytics-course-learners')).status_code, status.HTTP_200_OK)

    def test_empty_course(self):
        empty = Course.objects.create(
            title='Empty', pillar=self.f.course.pillar, level='beginner', duration_hours=1,
            is_published=False, created_by=self.f.creator,
        )
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(reverse('analytics-course-content', kwargs={'pk': empty.id}))
        self.assertEqual(res.data, {'course': {'id': empty.id, 'title': 'Empty'}, 'learners': 0, 'modules': []})
        res = self.client.get(reverse('analytics-course-learners', kwargs={'pk': empty.id}))
        self.assertEqual(res.data['learners'], [])
