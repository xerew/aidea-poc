from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, UserProfile
from hub.models.recommendations import CourseRecommendation, RecommendationEvent


def make_teacher(username='teacher1', onboarded=True):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER,
                               onboarding_completed=onboarded)
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

    def test_every_role_sees_recommendations_only_after_onboarding(self):
        pillar = LearningPillar.objects.create(name='P2', slug='p2', description='')
        course = Course.objects.create(title='C', pillar=pillar, level='beginner', is_published=True)
        for i, role in enumerate([UserProfile.UserType.CONTENT_CREATOR,
                                  UserProfile.UserType.AIDEA_PARTNER,
                                  UserProfile.UserType.ADMIN]):
            user = self._login_staff(role, f'staff{i}')
            CourseRecommendation.objects.create(user=user, course=course, score=0.9, reason='r')
            self.assertEqual(self.client.get(reverse('recommendations')).data, [], role)
            user.profile.onboarding_completed = True
            user.profile.save()
            self.assertEqual(len(self.client.get(reverse('recommendations')).data), 1, role)

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


class RecomputeAllTest(APITestCase):
    def test_nightly_refresh_covers_onboarded_users_of_every_role(self):
        from unittest.mock import patch

        from hub.tasks import recompute_all_recommendations
        teacher = make_teacher('t_on')
        make_teacher('t_off', onboarded=False)
        partner = User.objects.create_user(username='partner_on', password='pass')
        UserProfile.objects.create(user=partner, user_type=UserProfile.UserType.AIDEA_PARTNER,
                                   onboarding_completed=True)
        admin = User.objects.create_user(username='admin_off', password='pass')
        UserProfile.objects.create(user=admin, user_type=UserProfile.UserType.ADMIN)
        with patch('hub.tasks.compute_user_recommendations.delay') as compute:
            recompute_all_recommendations()
        self.assertEqual({c.args[0] for c in compute.call_args_list}, {teacher.id, partner.id})


class RecommendedCompletionEventTests(APITestCase):
    """Completing a course enrolled in from a recommendation records the
    'completed' reward, credited to the weights of the original enrolment."""

    def setUp(self):
        from hub.models import Enrollment, Module, Resource
        from hub.models.content import Activity
        pillar = LearningPillar.objects.create(name='RC', slug='rc', description='')
        self.course = Course.objects.create(title='Rec course', pillar=pillar, is_published=True)
        module = Module.objects.create(course=self.course, title='M', order=1)
        activity = Activity.objects.create(module=module, title='A', order=1)
        self.resource = Resource.objects.create(activity=activity, type='text', order=1)
        self.teacher = make_teacher('rc_t')
        self.enrollment = Enrollment.objects.create(user=self.teacher, course=self.course)

    def _complete(self, user, enrollment):
        from hub.completion import record_resource_completion
        record_resource_completion(user, enrollment, self.resource)

    def test_completion_logged_with_enrolment_weights(self):
        snapshot = {'alpha': 0.4, 'beta': 0.4, 'gamma': 0.2, 'bandit_active': True}
        RecommendationEvent.objects.create(
            user=self.teacher, course=self.course, event_type='enrolled',
            rank=2, source='cf', weights_snapshot=snapshot,
        )
        self._complete(self.teacher, self.enrollment)
        done = RecommendationEvent.objects.get(user=self.teacher, event_type='completed')
        self.assertEqual((done.source, done.rank, done.weights_snapshot), ('cf', 2, snapshot))

    def test_no_event_when_course_was_not_recommended(self):
        self._complete(self.teacher, self.enrollment)
        self.assertFalse(RecommendationEvent.objects.filter(event_type='completed').exists())

    def test_staff_completion_not_logged(self):
        from hub.models import Enrollment
        creator = User.objects.create_user(username='rc_cc', password='pass')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        RecommendationEvent.objects.create(
            user=creator, course=self.course, event_type='enrolled', rank=1, source='personal',
        )
        self._complete(creator, Enrollment.objects.create(user=creator, course=self.course))
        self.assertFalse(RecommendationEvent.objects.filter(event_type='completed').exists())


class RecommendationReasonParamsTests(APITestCase):
    def test_reason_params_for_personal_and_peer_cards(self):
        from hub.models import Subject
        user = make_teacher('rp_t')
        user.profile.subject = Subject.objects.get(slug='mathematics')
        user.profile.competency_score = 3
        user.profile.save()
        pillar = LearningPillar.objects.create(name='RP', slug='rp', description='')
        c1 = Course.objects.create(title='One', pillar=pillar, is_published=True)
        c2 = Course.objects.create(title='Two', pillar=pillar, is_published=True)
        CourseRecommendation.objects.create(user=user, course=c1, score=0.9, reason='r', source='personal')
        CourseRecommendation.objects.create(user=user, course=c2, score=0.4, reason='r', source='cf')
        self.client.force_authenticate(user)
        by_source = {r['source']: r['reason_params'] for r in self.client.get(reverse('recommendations')).data}
        self.assertEqual(by_source['personal'],
                         {'level': 'intermediate', 'subject_slug': 'mathematics', 'subject_name': 'Mathematics'})
        self.assertEqual(by_source['cf']['pct'], 40)
