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

    def test_404_before_onboarding(self):
        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_path_with_courses(self):
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
        pillar  = make_pillar()
        course  = make_course(pillar)
        path    = make_path_with_courses([course])
        UserLearningPath.objects.create(user=self.user, path=path, course_ids=[course.id])
        Enrollment.objects.create(user=self.user, course=course, progress_pct=100)

        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.data['courses'][0]['status'], 'completed')

    def test_competency_level_advanced_for_score_6(self):
        path = make_path_with_courses([])
        UserLearningPath.objects.create(user=self.user, path=path, course_ids=[])
        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.data['competency_level'], 'advanced')

    def test_content_creator_gets_403(self):
        creator = User.objects.create_user(username='creator1', password='pass')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        login = self.client.post(reverse('auth-login'), {'username': 'creator1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


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
