from unittest import mock

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.ai_review import model
from hub.models import (
    AIReview,
    AssignmentReviewConfig,
    AssignmentSubmission,
    ReviewExample,
    UserProfile,
)

from .test_ai_review_model import CRITERIA
from .test_ai_review_models import make_assignment


class AuthoringAIReviewTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user('aa_cc', password='x')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.module, self.activity, self.resource = make_assignment()
        self.course.created_by = self.creator
        self.course.save()
        kw = {'pk': self.course.id, 'module_pk': self.module.id, 'lesson_pk': self.activity.id, 'resource_pk': self.resource.id}
        self.url = reverse('authoring-ai-review', kwargs=kw)
        self.draft_url = reverse('authoring-ai-review-draft', kwargs=kw)
        self.examples_url = reverse('authoring-ai-review-examples', kwargs=kw)
        self.client.force_authenticate(self.creator)

    def test_get_creates_default_config(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data['enabled'], res.data['criteria'], res.data['unlocked']), (False, [], False))
        self.assertEqual(res.data['stats']['reviews'], 0)

    def test_save_and_approve_rubric(self):
        res = self.client.put(self.url, {'enabled': True, 'criteria': CRITERIA, 'rubric_approved': True}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        config = AssignmentReviewConfig.objects.get(resource=self.resource)
        self.assertTrue(config.is_ready())
        res = self.client.put(self.url, {'criteria': CRITERIA[:1]}, format='json')
        self.assertFalse(res.data['rubric_approved'])     # changed criteria need re-approval

    def test_invalid_criteria_rejected(self):
        for bad in ([{'name': ''}], [{'id': 'c1', 'name': 'x', 'met': 'y', 'required': 'yes'}], 'nope', [{}] * 11):
            res = self.client.put(self.url, {'criteria': bad}, format='json')
            self.assertEqual(res.status_code, 400, bad)

    def test_auto_approve_refused_while_locked(self):
        res = self.client.put(self.url, {'auto_approve': True}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_draft_uses_model(self):
        with mock.patch.object(model, 'draft_rubric', return_value=CRITERIA) as draft:
            res = self.client.post(self.draft_url)
        self.assertEqual((res.status_code, res.data['criteria']), (200, CRITERIA))
        self.assertEqual(draft.call_args.kwargs['instructions'], self.resource.instructions)

    def test_draft_offline_is_503(self):
        with mock.patch.object(model, 'draft_rubric', side_effect=model.ModelOffline('down')):
            self.assertEqual(self.client.post(self.draft_url).status_code, 503)

    def test_examples_crud(self):
        res = self.client.post(self.examples_url, {'text': 'Bias, privacy', 'verdict': 'approve', 'reason': 'ok'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(self.client.get(self.examples_url).data), 1)
        for _ in range(4):
            self.client.post(self.examples_url, {'text': 'x', 'verdict': 'approve'}, format='json')
        self.assertEqual(self.client.post(self.examples_url, {'text': 'x', 'verdict': 'approve'}, format='json').status_code, 400)
        example = ReviewExample.objects.first()
        url = reverse('authoring-ai-review-example', kwargs={'pk': self.course.id, 'module_pk': self.module.id,
                      'lesson_pk': self.activity.id, 'resource_pk': self.resource.id, 'example_pk': example.id})
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_other_creator_forbidden_and_non_assignment_400(self):
        other = User.objects.create_user('aa_o', password='x')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(self.creator)
        self.resource.type = 'text'
        self.resource.save()
        self.assertEqual(self.client.get(self.url).status_code, 400)

    def test_criteria_translated_on_approval(self):
        self.course.translation_status = {'el': 'done'}
        self.course.save()
        with mock.patch('hub.translation._ollama_generate', side_effect=lambda prompt: 'Τρεις κίνδυνοι'):
            self.client.put(self.url, {'enabled': True, 'criteria': CRITERIA[:1], 'rubric_approved': True}, format='json')
        config = AssignmentReviewConfig.objects.get(resource=self.resource)
        self.assertEqual(config.criteria_translations, {'el': {'c1': 'Τρεις κίνδυνοι'}})

    def test_unlocked_reported(self):
        learner = User.objects.create_user('aa_l', password='x')
        UserProfile.objects.create(user=learner)
        sub = AssignmentSubmission.objects.create(user=learner, lesson=self.activity, resource=self.resource, text='t')
        for _ in range(35):
            AIReview.objects.create(submission=sub, status='done', verdict='approve', human_verdict='approve', agreed=True)
        data = self.client.get(self.url).data
        self.assertTrue(data['unlocked'])
        self.assertEqual((data['unlock_min_reviews'], data['unlock_min_lower_bound']), (30, 0.9))
        self.assertIn('kappa', data['stats'])
        self.assertEqual(self.client.put(self.url, {'auto_approve': True}, format='json').status_code, 200)
