from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import Course, Enrollment, LearningPillar, UserProfile
from hub.models.recommendations import CourseRecommendation, CourseView, RecommendationEvent


def make_teacher(username='cv_teacher'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
    return user


class CourseViewLoggingTest(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'cv_teacher', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        pillar = LearningPillar.objects.create(name='CVP', slug='cvp', description='')
        self.course = Course.objects.create(
            title='CV Course', pillar=pillar, level='beginner', is_published=True,
        )

    def test_view_logged_on_course_detail_request(self):
        self.client.get(reverse('course-detail', kwargs={'pk': self.course.pk}))
        self.assertEqual(
            CourseView.objects.filter(user=self.user, course=self.course).count(), 1,
        )

    def test_each_visit_logged_separately(self):
        self.client.get(reverse('course-detail', kwargs={'pk': self.course.pk}))
        self.client.get(reverse('course-detail', kwargs={'pk': self.course.pk}))
        self.assertEqual(
            CourseView.objects.filter(user=self.user, course=self.course).count(), 2,
        )

    def test_view_not_logged_for_nonexistent_course(self):
        self.client.get(reverse('course-detail', kwargs={'pk': 99999}))
        self.assertEqual(CourseView.objects.count(), 0)


class EnrolledEventAutoFireTest(APITestCase):
    def setUp(self):
        self.user = make_teacher('enroll_ev_teacher')
        login = self.client.post(reverse('auth-login'), {'username': 'enroll_ev_teacher', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        pillar = LearningPillar.objects.create(name='EEP', slug='eep', description='')
        self.course = Course.objects.create(
            title='Enroll Event', pillar=pillar, level='beginner', is_published=True,
        )

    def test_enrolled_event_fired_when_recommendation_exists(self):
        CourseRecommendation.objects.create(
            user=self.user, course=self.course, score=0.9, reason='test', source='personal',
        )
        self.client.post(reverse('course-enroll', kwargs={'pk': self.course.pk}))
        self.assertEqual(
            RecommendationEvent.objects.filter(
                user=self.user, course=self.course, event_type='enrolled',
            ).count(),
            1,
        )

    def test_no_event_when_no_recommendation(self):
        self.client.post(reverse('course-enroll', kwargs={'pk': self.course.pk}))
        self.assertEqual(RecommendationEvent.objects.count(), 0)

    def test_no_duplicate_event_on_re_enroll(self):
        CourseRecommendation.objects.create(
            user=self.user, course=self.course, score=0.9, reason='test', source='personal',
        )
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.post(reverse('course-enroll', kwargs={'pk': self.course.pk}))
        self.assertEqual(RecommendationEvent.objects.count(), 0)
