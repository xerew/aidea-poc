"""Course-proposal fields (extra pillars, audience, levels, prior knowledge,
cross-axis relevance), module ↔ learning-outcome links, and module reuse."""
from unittest.mock import patch

from django.urls import reverse

from hub.models import Activity, Course, Enrollment, Module, Resource

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


class ModuleReuseTests(AuthoringTestCase):
    def setUp(self):
        super().setUp()
        self.source = Course.objects.create(
            title='Other course', pillar=self.pillar2, created_by=self.other_creator, is_published=True,
        )
        self.src_module = Module.objects.create(
            course=self.source, title='Reusable', order=1, related_outcomes=[0],
            translations={'el': {'title': 'Επαναχρησιμοποιήσιμο'}},
        )
        act = Activity.objects.create(module=self.src_module, title='Act', order=1)
        Resource.objects.create(activity=act, type='text', order=1, content='Hello')
        Resource.objects.create(activity=act, type='quiz', order=2, quiz_data=[
            {'question': 'Q', 'options': [{'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': False}]}])
        self.draft = Course.objects.create(title='Someone else draft', pillar=self.pillar1,
                                           created_by=self.other_creator)
        Module.objects.create(course=self.draft, title='Private', order=1)
        self.import_url = reverse('authoring-module-import', kwargs={'pk': self.course.pk})

    def test_library_lists_published_and_own_modules_only(self):
        self._login_as(self.creator)
        res = self.client.get(reverse('authoring-module-library'), {'exclude_course': self.course.pk})
        titles = {m['title'] for m in res.data}
        self.assertIn('Reusable', titles)
        self.assertNotIn('Private', titles)          # another creator's draft
        self.assertNotIn('Module 1', titles)         # the course being edited

    def test_import_deep_copies_module_at_the_end(self):
        self._login_as(self.creator)
        res = self.client.post(self.import_url, {'module_id': self.src_module.id}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        copy = Module.objects.get(pk=res.data['id'])
        self.assertEqual(copy.course, self.course)
        self.assertEqual(copy.order, 3)
        self.assertEqual(copy.related_outcomes, [])  # outcomes belong to the source course
        self.assertEqual(copy.translations['el']['title'], 'Επαναχρησιμοποιήσιμο')
        act = copy.lessons.get()
        self.assertEqual([r.type for r in act.resources.order_by('order')], ['text', 'quiz'])
        # The source is untouched.
        self.assertEqual(self.src_module.lessons.get().resources.count(), 2)

    def test_copied_module_progress_is_independent(self):
        self._login_as(self.creator)
        res = self.client.post(self.import_url, {'module_id': self.src_module.id}, format='json')
        copy_resource_ids = set(
            Resource.objects.filter(activity__module_id=res.data['id']).values_list('id', flat=True))
        source_ids = set(Resource.objects.filter(activity__module=self.src_module).values_list('id', flat=True))
        self.assertFalse(copy_resource_ids & source_ids)

    def test_cannot_import_from_someone_elses_draft(self):
        self._login_as(self.creator)
        private = self.draft.modules.get()
        res = self.client.post(self.import_url, {'module_id': private.id}, format='json')
        self.assertEqual(res.status_code, 404)

    def test_non_editor_cannot_import(self):
        self._login_as(self.other_creator)
        res = self.client.post(self.import_url, {'module_id': self.src_module.id}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_import_translates_missing_languages(self):
        self.course.translation_status = {'fr': 'done'}
        self.course.save()
        self._login_as(self.creator)
        with patch('hub.tasks.translate_module_meta.delay') as mod_delay, \
                patch('hub.tasks.translate_lesson_meta.delay') as act_delay:
            self.client.post(self.import_url, {'module_id': self.src_module.id}, format='json')
        mod_delay.assert_called_once()
        act_delay.assert_called_once()

    def test_enrollment_unaffected(self):
        Enrollment.objects.create(user=self.teacher, course=self.source)
        self._login_as(self.creator)
        self.client.post(self.import_url, {'module_id': self.src_module.id}, format='json')
        self.assertEqual(Enrollment.objects.filter(course=self.course).count(), 0)
