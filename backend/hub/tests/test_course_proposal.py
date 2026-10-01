"""Course-proposal fields (extra pillars, audience, levels, prior knowledge,
cross-axis relevance) and module ↔ learning-outcome links."""

from django.urls import reverse

from .test_authoring_courses import AuthoringTestCase


class CourseProposalFieldsTests(AuthoringTestCase):
    def _detail_url(self, course=None):
        return reverse('authoring-course-detail', kwargs={'pk': (course or self.course).pk})

    def test_create_course_with_all_proposal_fields(self):
        self._login_as(self.creator)
        res = self.client.post(reverse('authoring-courses'), {
            'title': 'New', 'pillar_id': self.pillar1.id,
            'additional_pillar_ids': [self.pillar2.id, self.pillar1.id],  # primary dropped
            'cross_axis_relevance': 'Also prepares students for AI.',
            'target_audience': ['school_leaders', 'teachers', 'teachers'],
            'target_audience_other': 'Teacher trainers',
            'educational_levels': ['upper_secondary', 'primary'],
            'educational_level_other': '',
            'prior_knowledge': 'None',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual([p['id'] for p in res.data['additional_pillars']], [self.pillar2.id])
        self.assertEqual(res.data['target_audience'], ['teachers', 'school_leaders'])
        self.assertEqual(res.data['educational_levels'], ['primary', 'upper_secondary'])
        self.assertEqual(res.data['prior_knowledge'], 'None')

    def test_unknown_audience_or_level_rejected(self):
        self._login_as(self.creator)
        res = self.client.patch(self._detail_url(), {'target_audience': ['parents']}, format='json')
        self.assertEqual(res.status_code, 400)
        res = self.client.patch(self._detail_url(), {'educational_levels': ['kindergarten']}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_learner_detail_localizes_proposal_texts(self):
        self.course.is_published = True
        self.course.prior_knowledge = 'None'
        self.course.translations = {'el': {'prior_knowledge': 'Καμία'}}
        self.course.save()
        self.course.additional_pillars.add(self.pillar2)
        self.teacher.profile.language = 'el'
        self.teacher.profile.save()
        self._login_as(self.teacher)
        res = self.client.get(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.data['prior_knowledge'], 'Καμία')
        self.assertEqual([p['slug'] for p in res.data['additional_pillars']], ['teach-for-ai'])

    def test_course_list_pillar_filter_matches_additional_pillars(self):
        self.course.is_published = True
        self.course.save()
        self.course.additional_pillars.add(self.pillar2)
        self._login_as(self.teacher)
        res = self.client.get('/api/courses/?pillar=teach-for-ai')
        self.assertEqual([c['id'] for c in res.data], [self.course.id])

    def test_translation_endpoint_accepts_proposal_texts(self):
        self._login_as(self.creator)
        res = self.client.patch(f'{self._detail_url()}?lang=el',
                                {'cross_axis_relevance': 'Κείμενο'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.translations['el']['cross_axis_relevance'], 'Κείμενο')


class ModuleOutcomeLinkTests(AuthoringTestCase):
    def _module_url(self, module):
        return reverse('authoring-module-detail', kwargs={'pk': self.course.pk, 'module_pk': module.pk})

    def test_module_saves_related_outcomes(self):
        self._login_as(self.creator)
        res = self.client.patch(self._module_url(self.module1), {'related_outcomes': [1, 0, 1]}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['related_outcomes'], [0, 1])

    def test_invalid_related_outcomes_rejected(self):
        self._login_as(self.creator)
        res = self.client.patch(self._module_url(self.module1), {'related_outcomes': ['a']}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_removed_outcomes_are_pruned_from_modules(self):
        self.module1.related_outcomes = [0, 1]
        self.module1.save()
        self._login_as(self.creator)
        self.client.patch(reverse('authoring-course-detail', kwargs={'pk': self.course.pk}),
                          {'learning_outcomes': ['Outcome A']}, format='json')
        self.module1.refresh_from_db()
        self.assertEqual(self.module1.related_outcomes, [0])

