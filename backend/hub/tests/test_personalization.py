"""Personalisation rules: educational level, target audience / school role,
additional pillars, embedding text, and when recomputation happens."""
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, Subject, UserProfile
from hub.pathway_gen import generate_pathway
from hub.personalization import (
    MATCH,
    MISMATCH,
    NEUTRAL,
    audience_match,
    course_embedding_text,
    course_pillar_slugs,
    level_match,
    pathway_bonus,
    profile_text,
    recommendation_factor,
)


def _profile(**kw):
    return UserProfile(**kw)


def _course(**kw):
    return Course(**kw)


class MatchRuleTests(TestCase):
    def test_level_match(self):
        primary, secondary, vet = (_profile(teaching_level=v) for v in ('primary', 'secondary', 'vocational'))
        self.assertEqual(level_match(primary, _course(educational_levels=['primary'])), MATCH)
        self.assertEqual(level_match(secondary, _course(educational_levels=['upper_secondary'])), MATCH)
        self.assertEqual(level_match(primary, _course(educational_levels=['lower_secondary'])), MISMATCH)
        self.assertEqual(level_match(primary, _course(educational_levels=['cross_level'])), MATCH)
        self.assertEqual(level_match(vet, _course(educational_levels=['primary'])), NEUTRAL)
        self.assertEqual(level_match(primary, _course(educational_levels=[])), NEUTRAL)

    def test_audience_match(self):
        teacher, leader, both, unset = (
            _profile(school_role=v) for v in ('teacher', 'school_leader', 'both', ''))
        leaders_only = _course(target_audience=['school_leaders'])
        self.assertEqual(audience_match(leader, leaders_only), MATCH)
        self.assertEqual(audience_match(teacher, leaders_only), MISMATCH)
        self.assertEqual(audience_match(both, leaders_only), MATCH)
        self.assertEqual(audience_match(unset, leaders_only), NEUTRAL)
        self.assertEqual(audience_match(teacher, _course(target_audience=[])), NEUTRAL)

    def test_factor_and_bonus(self):
        p = _profile(teaching_level='primary', school_role='teacher')
        good = _course(educational_levels=['primary'], target_audience=['teachers'])
        bad = _course(educational_levels=['upper_secondary'], target_audience=['school_leaders'])
        self.assertGreater(recommendation_factor(p, good), 1.0)
        self.assertLess(recommendation_factor(p, bad), 1.0)
        self.assertEqual(recommendation_factor(p, _course()), 1.0)
        self.assertGreater(pathway_bonus(p, good), 0)
        self.assertLess(pathway_bonus(p, bad), 0)

    def test_profile_text_mentions_role(self):
        p = _profile(school_role='school_leader', teaching_level='secondary', competency_score=3)
        self.assertIn('school leader', profile_text(p))


class CourseDataTests(TestCase):
    def setUp(self):
        self.twa = LearningPillar.objects.create(name='TWA', slug='teach-with-ai', order=1)
        self.tfa = LearningPillar.objects.create(name='TFA', slug='teach-for-ai', order=2)

    def test_course_pillars_include_additional(self):
        course = Course.objects.create(title='C', pillar=self.twa)
        course.additional_pillars.add(self.tfa)
        self.assertEqual(course_pillar_slugs(course), {'teach-with-ai', 'teach-for-ai'})

    def test_embedding_text_covers_new_fields(self):
        course = Course.objects.create(
            title='Prompting', description='Write prompts.', pillar=self.twa,
            learning_outcomes=['Design prompts', 'Evaluate output'],
            prior_knowledge='Basic digital skills', cross_axis_relevance='Builds AI literacy',
        )
        course.subjects.add(Subject.objects.get(slug='mathematics'))
        text = course_embedding_text(course)
        for fragment in ('Prompting', 'Design prompts; Evaluate output', 'Basic digital skills',
                         'Builds AI literacy', 'Mathematics'):
            self.assertIn(fragment, text)


class PathwayRankingTests(TestCase):
    def setUp(self):
        pillar = LearningPillar.objects.create(name='TWA', slug='teach-with-ai', order=1)

        def course(title, **kw):
            return Course.objects.create(title=title, pillar=pillar, level='beginner', is_published=True, **kw)
        self.secondary_only = course('Secondary', educational_levels=['upper_secondary'])
        self.primary = course('Primary', educational_levels=['primary'])
        self.leaders = course('Leaders', target_audience=['school_leaders'])
        self.neutral = course('Neutral')

    def _user(self, **kw):
        user = User.objects.create_user(username=f'pr{User.objects.count()}', password='x')
        UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER, competency_score=1, **kw)
        return user

    def test_primary_teacher(self):
        ids = generate_pathway(self._user(teaching_level='primary', school_role='teacher'))
        self.assertEqual(ids[0], self.primary.id)
        self.assertLess(ids.index(self.neutral.id), ids.index(self.secondary_only.id))
        self.assertEqual(ids[-1], self.leaders.id)  # aimed at school leaders only

    def test_school_leader_gets_leader_course_first(self):
        ids = generate_pathway(self._user(school_role='school_leader'))
        self.assertEqual(ids[0], self.leaders.id)

    def test_additional_pillar_counts_as_preferred(self):
        tfa = LearningPillar.objects.create(name='TFA', slug='teach-for-ai', order=2)
        self.neutral.additional_pillars.add(tfa)
        ids = generate_pathway(self._user(preferred_pillars=['teach-for-ai']))
        self.assertEqual(ids[0], self.neutral.id)


class SchoolRoleProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='role_t', password='x')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.client.force_authenticate(self.user)
        self.url = reverse('profile-info')

    @patch('hub.views.profile.compute_user_recommendations.delay')
    def test_role_saved_and_recommendations_recomputed_on_change(self, recompute):
        res = self.client.patch(self.url, {'school_role': 'school_leader'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['school_role'], 'school_leader')
        recompute.assert_called_once_with(self.user.id)

        recompute.reset_mock()
        self.client.patch(self.url, {'bio': 'Hi'}, format='json')  # no personalising change
        recompute.assert_not_called()

    def test_invalid_role_rejected(self):
        self.assertEqual(self.client.patch(self.url, {'school_role': 'janitor'}, format='json').status_code, 400)


class RecomputeEmbeddingsCommandTests(TestCase):
    @patch('hub.management.commands.recompute_course_embeddings.recompute_all_recommendations.delay')
    @patch('hub.management.commands.recompute_course_embeddings.compute_course_embeddings')
    def test_recomputes_published_courses_then_queues_refresh(self, compute, refresh):
        pillar = LearningPillar.objects.create(name='P', slug='p-emb', order=1)
        live = Course.objects.create(title='Live', pillar=pillar, is_published=True)
        Course.objects.create(title='Draft', pillar=pillar)
        compute.reset_mock()  # publishing via post_save may have queued one already
        call_command('recompute_course_embeddings', stdout=StringIO())
        compute.assert_called_once_with(live.id)
        refresh.assert_called_once_with()
