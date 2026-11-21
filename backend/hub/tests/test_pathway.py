from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, Enrollment, LearningPillar, UserProfile
from hub.models.pathway import LearningPath, LearningPathCourse, UserLearningPath


def make_teacher(username='teacher1'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER, competency_score=6)
    return user


def make_pillar():
    return LearningPillar.objects.create(name='Pillar', slug='pillar', description='')


def make_course(pillar, title='Course A'):
    return Course.objects.create(
        title=title, pillar=pillar, level='beginner', is_published=True,
    )


def make_path_with_courses(courses):
    path = LearningPath.objects.create(
        name='Test Path', slug='test-path', competency_min=5, competency_max=6,
    )
    for i, course in enumerate(courses):
        LearningPathCourse.objects.create(path=path, course=course, order=i + 1)
    return path


class PathwayGetTestCase(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def _onboarded(self):
        self.user.profile.onboarding_completed = True
        self.user.profile.save()

    def test_404_before_onboarding(self):
        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_path_with_courses(self):
        self._onboarded()
        pillar  = make_pillar()
        course1 = make_course(pillar, 'Course A')
        course2 = make_course(pillar, 'Course B')
        path    = make_path_with_courses([course1, course2])
        # The personalised course list lives on the UserLearningPath now.
        UserLearningPath.objects.create(
            user=self.user, path=path, course_ids=[course1.id, course2.id],
        )

        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['path_name'], 'Test Path')
        self.assertEqual(len(response.data['courses']), 2)
        self.assertEqual([c['order'] for c in response.data['courses']], [1, 2])
        self.assertEqual(response.data['progress']['total'], 2)
        self.assertEqual(response.data['progress']['completed'], 0)

    def test_course_status_is_completed_when_enrolled_at_100(self):
        self._onboarded()
        pillar  = make_pillar()
        course  = make_course(pillar)
        path    = make_path_with_courses([course])
        UserLearningPath.objects.create(user=self.user, path=path, course_ids=[course.id])
        Enrollment.objects.create(user=self.user, course=course, progress_pct=100)

        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.data['courses'][0]['status'], 'completed')

    def test_competency_level_advanced_for_score_6(self):
        self._onboarded()
        path = make_path_with_courses([])
        UserLearningPath.objects.create(user=self.user, path=path, course_ids=[])
        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.data['competency_level'], 'advanced')

    def _login_as(self, user_type, username):
        user = User.objects.create_user(username=username, password='pass')
        UserProfile.objects.create(user=user, user_type=user_type, competency_score=6)
        login = self.client.post(reverse('auth-login'), {'username': username, 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        return user

    def test_every_role_needs_onboarding_for_a_pathway(self):
        from unittest.mock import patch

        from hub.models import Subject
        make_path_with_courses([make_course(make_pillar())])
        LearningPath.objects.create(name='Beginner', slug='beginner-foundations',
                                    competency_min=0, competency_max=4)
        subject = Subject.objects.get(slug='mathematics')
        for i, user_type in enumerate([
            UserProfile.UserType.CONTENT_CREATOR,
            UserProfile.UserType.AIDEA_PARTNER,
            UserProfile.UserType.ADMIN,
        ]):
            self._login_as(user_type, f'staff{i}')
            self.assertEqual(self.client.get(reverse('pathway')).status_code,
                             status.HTTP_404_NOT_FOUND, user_type)
            with patch('hub.tasks.compute_user_recommendations.delay'):
                res = self.client.post(reverse('onboarding'), {
                    'subject': subject.id, 'teaching_level': 'secondary',
                    'school_role': 'school_leader', 'goals': [],
                }, format='json')
            self.assertEqual(res.status_code, status.HTTP_200_OK, user_type)
            self.assertEqual(self.client.get(reverse('pathway')).status_code,
                             status.HTTP_200_OK, user_type)

    def test_pathway_without_onboarding_is_not_served(self):
        # e.g. created for a staff account before onboarding applied to every role
        creator = self._login_as(UserProfile.UserType.CONTENT_CREATOR, 'early_creator')
        path = make_path_with_courses([make_course(make_pillar())])
        UserLearningPath.objects.create(user=creator, path=path, course_ids=[])
        self.assertEqual(self.client.get(reverse('pathway')).status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_still_needs_onboarding(self):
        make_path_with_courses([make_course(make_pillar())])
        response = self.client.get(reverse('pathway'))  # teacher1, not onboarded
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(UserLearningPath.objects.filter(user=self.user).exists())


class GeneratePathwayTests(TestCase):
    def setUp(self):
        from hub.models import Subject
        self.twa = LearningPillar.objects.create(name='Teach with AI', slug='teach-with-ai', description='', order=1)
        self.tfa = LearningPillar.objects.create(name='Teach for AI', slug='teach-for-ai', description='', order=2)
        self.taa = LearningPillar.objects.create(name='Teach about AI', slug='teach-about-ai', description='', order=3)
        # One beginner course per pillar.
        self.c_twa = Course.objects.create(title='TWA', pillar=self.twa, level='beginner', is_published=True)
        self.c_tfa = Course.objects.create(title='TFA', pillar=self.tfa, level='beginner', is_published=True)
        self.c_taa = Course.objects.create(title='TAA', pillar=self.taa, level='beginner', is_published=True)
        self.subject = Subject.objects.get(slug='mathematics')

    def _teacher(self, **profile_kwargs):
        user = User.objects.create_user(username=f'gp_{User.objects.count()}', password='pass')
        UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER, **profile_kwargs)
        return user

    def test_preferred_pillar_ranks_first(self):
        from hub.pathway_gen import generate_pathway
        user = self._teacher(competency_score=1, preferred_pillars=['teach-about-ai'])
        ids = generate_pathway(user)
        self.assertEqual(ids[0], self.c_taa.id)

    def test_changing_preferred_pillar_changes_order(self):
        from hub.pathway_gen import generate_pathway
        user = self._teacher(competency_score=1, preferred_pillars=['teach-for-ai'])
        self.assertEqual(generate_pathway(user)[0], self.c_tfa.id)
        user.profile.preferred_pillars = ['teach-with-ai']
        user.profile.save()
        self.assertEqual(generate_pathway(user)[0], self.c_twa.id)

    def test_goal_steers_pathway(self):
        from hub.pathway_gen import generate_pathway
        # No preferred pillar, but the 'address_ethics' goal maps to teach-about-ai.
        user = self._teacher(competency_score=1, goals=['address_ethics'])
        self.assertEqual(generate_pathway(user)[0], self.c_taa.id)

    def test_excludes_courses_far_above_competency(self):
        from hub.pathway_gen import generate_pathway
        advanced = Course.objects.create(title='Adv', pillar=self.twa, level='advanced', is_published=True)
        user = self._teacher(competency_score=0)  # band 0 — advanced (2) > 0+1
        self.assertNotIn(advanced.id, generate_pathway(user))


class PathwaySeedOrderingTests(TestCase):
    def test_seeded_path_courses_ordered_by_level(self):
        from hub.management.commands.seed_data.pathways import seed_pathways

        pillar = LearningPillar.objects.create(name='Teach with AI', slug='teach-with-ai', description='')
        Course.objects.create(title='A Advanced', pillar=pillar, level='advanced',
                               duration_hours=1, is_published=True)
        Course.objects.create(title='B Beginner', pillar=pillar, level='beginner',
                               duration_hours=1, is_published=True)
        Course.objects.create(title='C Intermediate', pillar=pillar, level='intermediate',
                               duration_hours=1, is_published=True)

        seed_pathways()

        path = LearningPath.objects.get(slug='beginner-foundations')
        ordered = list(
            LearningPathCourse.objects.filter(path=path).order_by('order').values_list('course__level', flat=True)
        )
        self.assertEqual(ordered, ['beginner', 'intermediate', 'advanced'])


class PathwayEmptyStateTests(APITestCase):
    """An empty pathway says why, and fills itself once suitable courses exist."""

    def setUp(self):
        self.user = make_teacher('empty_t')
        self.user.profile.competency_score = 0      # beginner
        self.user.profile.onboarding_completed = True
        self.user.profile.save()
        self.path = LearningPath.objects.create(name='B', slug='b-empty', competency_min=0, competency_max=6)
        self.user_path = UserLearningPath.objects.create(user=self.user, path=self.path, course_ids=[])
        self.client.force_authenticate(self.user)
        self.pillar = make_pillar()

    def _get(self):
        return self.client.get(reverse('pathway')).data

    def test_no_published_courses(self):
        data = self._get()
        self.assertEqual(data['courses'], [])
        self.assertEqual(data['empty_reason'], 'no_published_courses')

    def test_all_courses_above_level(self):
        Course.objects.create(title='Adv', pillar=self.pillar, level='advanced', is_published=True)
        self.assertEqual(self._get()['empty_reason'], 'above_level')

    def test_regenerates_when_a_suitable_course_appears(self):
        course = make_course(self.pillar, 'Fits')  # beginner, published
        data = self._get()
        self.assertEqual([c['id'] for c in data['courses']], [course.id])
        self.assertIsNone(data['empty_reason'])
        self.user_path.refresh_from_db()
        self.assertEqual(self.user_path.course_ids, [course.id])

    def test_unpublished_course_drops_out_of_list_and_progress(self):
        live = make_course(self.pillar, 'Live')
        gone = make_course(self.pillar, 'Gone')
        self.user_path.course_ids = [gone.id, live.id]
        self.user_path.save()
        gone.is_published = False
        gone.save()
        data = self._get()
        self.assertEqual([c['id'] for c in data['courses']], [live.id])
        self.assertEqual(data['progress']['total'], 1)


class PathwayFollowsCompetencyChangeTests(TestCase):
    def test_level_change_rebuilds_course_list(self):
        from hub.competency import apply_competency_delta
        pillar = make_pillar()
        beginner = make_course(pillar, 'Beginner course')
        advanced = Course.objects.create(title='Advanced course', pillar=pillar, level='advanced',
                                         is_published=True)
        LearningPath.objects.create(name='Beginner', slug='beg', competency_min=0, competency_max=2)
        LearningPath.objects.create(name='Advanced', slug='adv', competency_min=5, competency_max=6)
        user = make_teacher('climber')
        user.profile.competency_score = 2
        user.profile.save()
        from hub.pathway_gen import generate_pathway
        UserLearningPath.objects.create(user=user, path=LearningPath.objects.get(slug='beg'),
                                        course_ids=generate_pathway(user))
        self.assertNotIn(advanced.id, UserLearningPath.objects.get(user=user).course_ids)

        apply_competency_delta(user, 4, recompute=False)  # 2 -> 6: beginner -> advanced band
        user_path = UserLearningPath.objects.get(user=user)
        self.assertEqual(user_path.path.slug, 'adv')
        self.assertIn(advanced.id, user_path.course_ids)
        self.assertIn(beginner.id, user_path.course_ids)


class PathwayRefreshOnPublishTests(APITestCase):
    """Publishing or unpublishing a course rebuilds everyone's recommendations and
    pathways; courses a person has already started stay in their pathway."""

    def setUp(self):
        from unittest import mock
        self.pillar = make_pillar()
        self.creator = User.objects.create_user(username='author', password='pass')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.teacher = make_teacher()
        self.teacher.profile.competency_score = 1      # beginner band: advanced courses are out of range
        self.teacher.profile.onboarding_completed = True
        self.teacher.profile.save()
        self.started = Course.objects.create(title='Started', pillar=self.pillar, level='advanced', is_published=True)
        Enrollment.objects.create(user=self.teacher, course=self.started, progress_pct=30)
        self.path = LearningPath.objects.create(name='P', slug='p', competency_min=0, competency_max=10)
        self.user_path = UserLearningPath.objects.create(user=self.teacher, path=self.path, course_ids=[self.started.id])
        self.draft = Course.objects.create(title='New', pillar=self.pillar, level='beginner',
                                           is_published=False, created_by=self.creator)
        self.client.force_authenticate(self.creator)
        patcher = mock.patch('hub.tasks.recompute_all_recommendations')
        self.recompute = patcher.start()
        self.addCleanup(patcher.stop)

    def _post(self, action):
        url = reverse(f'authoring-course-{action}', kwargs={'pk': self.draft.pk})
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url)

    def test_publishing_adds_the_course_to_pathways_and_refreshes_recommendations(self):
        self.assertEqual(self._post('publish').status_code, 200)
        self.user_path.refresh_from_db()
        self.assertIn(self.draft.id, self.user_path.course_ids)
        self.recompute.assert_called_once()

    def test_a_started_course_stays_in_the_pathway(self):
        self._post('publish')
        self.user_path.refresh_from_db()
        self.assertEqual(self.user_path.course_ids, [self.started.id, self.draft.id])

    def test_unpublishing_also_refreshes(self):
        self._post('publish')
        self.recompute.reset_mock()
        self.assertEqual(self._post('unpublish').status_code, 200)
        self.user_path.refresh_from_db()
        self.assertEqual(self.user_path.course_ids, [self.started.id])
        self.recompute.assert_called_once()

    def test_publishing_from_django_admin_also_refreshes(self):
        from django.contrib.admin.sites import site
        from django.test import RequestFactory

        from hub.admin import CourseAdmin
        admin_obj = CourseAdmin(Course, site)
        admin_obj.message_user = lambda *a, **k: None
        with self.captureOnCommitCallbacks(execute=True):
            admin_obj.publish_courses(RequestFactory().post('/'), Course.objects.filter(pk=self.draft.pk))
        self.user_path.refresh_from_db()
        self.assertIn(self.draft.id, self.user_path.course_ids)
        self.recompute.assert_called_once()
