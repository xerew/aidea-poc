from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, UserProfile
from hub.models.recommendations import CourseRecommendation, RecommendationEvent


def make_teacher(username='teacher1'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
    return user


class RecommendationsGetTestCase(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_empty_list_when_no_recommendations(self):
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_returns_precomputed_recommendations(self):
        pillar = LearningPillar.objects.create(name='P', slug='p', description='')
        course = Course.objects.create(title='AI Basics', pillar=pillar, level='beginner', is_published=True)
        CourseRecommendation.objects.create(
            user=self.user, course=course, score=0.95,
            reason='Matches your beginner level and stem focus',
        )
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'AI Basics')
        self.assertEqual(response.data[0]['score'], 0.95)

    def _login_staff(self, user_type, username):
        user = User.objects.create_user(username=username, password='pass')
        UserProfile.objects.create(user=user, user_type=user_type)
        self.client.force_authenticate(user)
        return user

    def test_staff_roles_get_recommendations_computed_on_first_visit(self):
        from unittest.mock import patch

        from django.core.cache import cache
        for i, role in enumerate([UserProfile.UserType.CONTENT_CREATOR,
                                  UserProfile.UserType.AIDEA_PARTNER,
                                  UserProfile.UserType.ADMIN]):
            user = self._login_staff(role, f'staff{i}')
            cache.delete(f'recs_first_compute:{user.id}')
            with patch('hub.tasks.compute_user_recommendations.delay') as compute:
                first = self.client.get(reverse('recommendations'))
                self.client.get(reverse('recommendations'))  # no second queueing
            self.assertEqual(first.status_code, status.HTTP_200_OK, role)
            compute.assert_called_once_with(user.id)

    def test_teacher_without_recommendations_does_not_queue(self):
        from unittest.mock import patch
        with patch('hub.tasks.compute_user_recommendations.delay') as compute:
            self.client.get(reverse('recommendations'))
        compute.assert_not_called()  # teachers get theirs at onboarding


class RecommendationSourceFieldTest(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_source_personal_in_response(self):
        pillar = LearningPillar.objects.create(name='SP', slug='sp', description='')
        course = Course.objects.create(
            title='Source Test', pillar=pillar, level='beginner', is_published=True,
        )
        CourseRecommendation.objects.create(
            user=self.user, course=course, score=0.9, reason='test', source='personal',
        )
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['source'], 'personal')

    def test_source_cf_in_response(self):
        pillar = LearningPillar.objects.create(name='CF', slug='cf', description='')
        course = Course.objects.create(
            title='CF Test', pillar=pillar, level='beginner', is_published=True,
        )
        CourseRecommendation.objects.create(
            user=self.user, course=course, score=0.6, reason='67% of STEM', source='cf',
        )
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['source'], 'cf')


class RecommendationEventAPITest(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        pillar = LearningPillar.objects.create(name='EV', slug='ev', description='')
        self.course = Course.objects.create(
            title='Event Course', pillar=pillar, level='beginner', is_published=True,
        )

    def test_shown_event_created(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'shown',
            'rank': 1,
            'source': 'personal',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RecommendationEvent.objects.count(), 1)
        ev = RecommendationEvent.objects.first()
        self.assertEqual(ev.event_type, 'shown')
        self.assertEqual(ev.source, 'personal')
        self.assertIn('alpha', ev.weights_snapshot)

    def test_clicked_event_created(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'clicked',
            'rank': 2,
            'source': 'cf',
        })
        self.assertEqual(response.status_code, 201)
        ev = RecommendationEvent.objects.first()
        self.assertEqual(ev.rank, 2)

    def test_invalid_event_type_rejected(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'unknown_type',
            'rank': 1,
            'source': 'personal',
        })
        self.assertEqual(response.status_code, 400)

    def test_invalid_source_rejected(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'shown',
            'rank': 1,
            'source': 'invalid',
        })
        self.assertEqual(response.status_code, 400)

    def test_staff_events_are_accepted_but_not_stored(self):
        # Events tune the weights and are study data: teachers only.
        from hub.models import UserProfile as UP
        creator = User.objects.create_user(username='creator2', password='pass')
        UP.objects.create(user=creator, user_type=UP.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(creator)
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id, 'event_type': 'shown', 'rank': 1, 'source': 'personal',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RecommendationEvent.objects.count(), 0)

    def test_staff_enrolment_from_recommendation_not_logged(self):
        from hub.models import UserProfile as UP
        creator = User.objects.create_user(username='creator3', password='pass')
        UP.objects.create(user=creator, user_type=UP.UserType.CONTENT_CREATOR)
        CourseRecommendation.objects.create(user=creator, course=self.course, score=0.9, reason='r')
        self.client.force_authenticate(creator)
        self.client.post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(RecommendationEvent.objects.count(), 0)


class RecomputeAllIncludesStaffTest(APITestCase):
    def test_nightly_refresh_covers_onboarded_teachers_and_staff(self):
        from unittest.mock import patch

        from hub.tasks import recompute_all_recommendations
        onboarded = make_teacher('t_on')
        onboarded.profile.onboarding_completed = True
        onboarded.profile.save()
        make_teacher('t_off')  # not onboarded: skipped
        partner = User.objects.create_user(username='partner_n', password='pass')
        UserProfile.objects.create(user=partner, user_type=UserProfile.UserType.AIDEA_PARTNER)
        with patch('hub.tasks.compute_user_recommendations.delay') as compute:
            recompute_all_recommendations()
        self.assertEqual({c.args[0] for c in compute.call_args_list}, {onboarded.id, partner.id})
