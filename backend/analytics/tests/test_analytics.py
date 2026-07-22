from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import (
    Course,
    Enrollment,
    LearningPillar,
    Lesson,
    LessonProgress,
    Module,
    UserProfile,
)


def make_teacher(username='teacher1'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
    return user


def make_creator(username='creator1'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.CONTENT_CREATOR)
    return user


class AnalyticsOverviewPermissionTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('analytics-overview')
        self.pillar = LearningPillar.objects.create(name='P', slug='p', description='', order=1)

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_teacher_returns_403(self):
        self.client.force_authenticate(user=make_teacher())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_content_creator_returns_200(self):
        self.client.force_authenticate(user=make_creator())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AnalyticsOverviewDataTestCase(APITestCase):
    def setUp(self):
        self.creator = make_creator()
        self.other_creator = make_creator('creator2')
        self.pillar = LearningPillar.objects.create(name='P', slug='p', description='', order=1)

        self.course1 = Course.objects.create(
            title='Course 1', pillar=self.pillar, created_by=self.creator,
        )
        self.course2 = Course.objects.create(
            title='Course 2', pillar=self.pillar, created_by=self.creator,
        )
        self.other_course = Course.objects.create(
            title='Other Course', pillar=self.pillar, created_by=self.other_creator,
        )

        self.module1 = Module.objects.create(title='M1', course=self.course1, order=1)
        self.module2 = Module.objects.create(title='M2', course=self.course2, order=1)

        self.lesson_text = Lesson.objects.create(
            title='L1', module=self.module1, lesson_type='text', duration_minutes=30, order=1,
        )
        self.lesson_quiz = Lesson.objects.create(
            title='L2', module=self.module1, lesson_type='quiz', duration_minutes=20, order=2,
        )

        teacher1 = make_teacher('t1')
        teacher2 = make_teacher('t2')
        teacher3 = make_teacher('t3')

        self.enroll1 = Enrollment.objects.create(user=teacher1, course=self.course1, progress_pct=100)
        self.enroll2 = Enrollment.objects.create(user=teacher2, course=self.course1, progress_pct=50)
        self.enroll3 = Enrollment.objects.create(user=teacher3, course=self.course1, progress_pct=0)
        self.enroll4 = Enrollment.objects.create(user=teacher1, course=self.course2, progress_pct=100)

        LessonProgress.objects.create(user=teacher1, lesson=self.lesson_quiz)
        LessonProgress.objects.create(user=teacher2, lesson=self.lesson_quiz)

        # Enrollment on other creator's course — must not appear
        Enrollment.objects.create(user=teacher1, course=self.other_course, progress_pct=100)

        self.client.force_authenticate(user=self.creator)
        self.url = reverse('analytics-overview')

    def test_summary_courses_created(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data['summary']['courses_created'], 2)

    def test_summary_total_enrollments(self):
        response = self.client.get(self.url)
        # 3 on course1 + 1 on course2 = 4 (other_course excluded)
        self.assertEqual(response.data['summary']['total_enrollments'], 4)

    def test_summary_completion_rate(self):
        response = self.client.get(self.url)
        # completed: enroll1 (100%) + enroll4 (100%) = 2 out of 4 → 50%
        self.assertEqual(response.data['summary']['completion_rate'], 50)

    def test_summary_quiz_attempts(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data['summary']['quiz_attempts'], 2)

    def test_no_cross_creator_data(self):
        self.client.force_authenticate(user=self.other_creator)
        response = self.client.get(self.url)
        self.assertEqual(response.data['summary']['courses_created'], 1)
        self.assertEqual(response.data['summary']['total_enrollments'], 1)

    def test_course_breakdown_enrolled(self):
        response = self.client.get(self.url)
        courses = {c['title']: c for c in response.data['courses']}
        self.assertEqual(courses['Course 1']['enrolled'], 3)
        self.assertEqual(courses['Course 2']['enrolled'], 1)

    def test_course_breakdown_completed(self):
        response = self.client.get(self.url)
        courses = {c['title']: c for c in response.data['courses']}
        self.assertEqual(courses['Course 1']['completed'], 1)
        self.assertEqual(courses['Course 2']['completed'], 1)

    def test_course_breakdown_in_progress(self):
        response = self.client.get(self.url)
        courses = {c['title']: c for c in response.data['courses']}
        self.assertEqual(courses['Course 1']['in_progress'], 1)  # teacher2 at 50%
        self.assertEqual(courses['Course 2']['in_progress'], 0)

    def test_course_breakdown_completion_rate(self):
        response = self.client.get(self.url)
        courses = {c['title']: c for c in response.data['courses']}
        self.assertEqual(courses['Course 1']['completion_rate'], 33)  # 1/3 rounded
        self.assertEqual(courses['Course 2']['completion_rate'], 100)

    def test_course_breakdown_avg_time_minutes(self):
        response = self.client.get(self.url)
        courses = {c['title']: c for c in response.data['courses']}
        self.assertEqual(courses['Course 1']['avg_time_minutes'], 50)  # 30 + 20
        self.assertEqual(courses['Course 2']['avg_time_minutes'], 0)   # no lessons

    def test_empty_for_creator_with_no_courses(self):
        creator3 = make_creator('creator3')
        self.client.force_authenticate(user=creator3)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['courses_created'], 0)
        self.assertEqual(response.data['summary']['total_enrollments'], 0)
        self.assertEqual(response.data['summary']['completion_rate'], 0)
        self.assertEqual(response.data['summary']['quiz_attempts'], 0)
        self.assertEqual(response.data['courses'], [])

    def test_unpublished_courses_counted(self):
        Course.objects.create(
            title='Draft course', pillar=self.pillar, level='beginner',
            duration_hours=1, is_published=False, created_by=self.creator,
        )
        res = self.client.get(self.url)
        titles = [c['title'] for c in res.data['courses']]
        self.assertIn('Draft course', titles)

    def test_other_creators_published_courses_included(self):
        # #11: published courses by anyone show up (platform-wide engagement),
        # but they do NOT inflate the viewer's "courses created" count.
        other = User.objects.create_user(username='other_creator2', password='pass12345')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        Course.objects.create(
            title='Someone elses published', pillar=self.pillar, level='beginner',
            duration_hours=1, is_published=True, created_by=other,
        )
        res = self.client.get(self.url)
        titles = [c['title'] for c in res.data['courses']]
        self.assertIn('Someone elses published', titles)
        self.assertEqual(res.data['summary']['courses_created'], 2)  # still only own

    def test_other_creators_unpublished_courses_excluded(self):
        other = User.objects.create_user(username='other_creator3', password='pass12345')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        Course.objects.create(
            title='Someone elses draft', pillar=self.pillar, level='beginner',
            duration_hours=1, is_published=False, created_by=other,
        )
        res = self.client.get(self.url)
        titles = [c['title'] for c in res.data['courses']]
        self.assertNotIn('Someone elses draft', titles)
