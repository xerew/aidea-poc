from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import (
    AIReview,
    AssignmentReviewConfig,
    AssignmentSubmission,
    Enrollment,
    ReviewExample,
    UserProfile,
)

from .test_ai_review_model import CRITERIA
from .test_ai_review_models import make_assignment


class ReviewerAPITests(APITestCase):
    def setUp(self):
        self.course, _, self.activity, self.resource = make_assignment()
        self.config = AssignmentReviewConfig.objects.create(resource=self.resource, enabled=True,
                                                            criteria=CRITERIA, rubric_approved=True,
                                                            criteria_translations={'el': {'c1': 'Τρεις κίνδυνοι'}})
        self.admin = User.objects.create_user('ra_admin', password='x')
        UserProfile.objects.create(user=self.admin, user_type=UserProfile.UserType.ADMIN)
        self.learner = User.objects.create_user('ra_l', password='x', first_name='Maria', last_name='Pappa',
                                                email='maria@example.org')
        UserProfile.objects.create(user=self.learner, language='el')
        Enrollment.objects.create(user=self.learner, course=self.course)
        self.sub = AssignmentSubmission.objects.create(
            user=self.learner, lesson=self.activity, resource=self.resource,
            text='I am Maria Pappa (maria@example.org). Risks: bias, privacy, errors.')
        self.review = AIReview.objects.create(
            submission=self.sub, status='done', rubric=CRITERIA, verdict='approve', confidence=0.9,
            criteria_results=[{'id': 'c1', 'status': 'met', 'reason': 'ok'}, {'id': 'c2', 'status': 'not_met', 'reason': 'no'}],
            learner_feedback='Καλή δουλειά.', reviewer_notes='Fine.')
        self.client.force_authenticate(self.admin)

    def test_queue_includes_ai_review(self):
        row = self.client.get(reverse('review-queue')).data[0]
        self.assertEqual((row['ai_review']['verdict'], row['ai_review']['criteria'][0]['name']), ('approve', 'Three risks'))

    def test_queue_filters(self):
        url = reverse('review-queue')
        self.assertEqual(len(self.client.get(url, {'filter': 'ai_approve'}).data), 1)
        self.assertEqual(len(self.client.get(url, {'filter': 'ai_unsure'}).data), 0)
        self.assertEqual(len(self.client.get(url, {'filter': 'flagged'}).data), 0)
        AssignmentSubmission.objects.filter(pk=self.sub.pk).update(status='approved')
        AIReview.objects.filter(pk=self.review.pk).update(auto_approved=True)
        self.assertEqual(len(self.client.get(url, {'filter': 'auto_approved'}).data), 1)

    def test_decision_records_agreement_and_reason(self):
        self.client.post(reverse('review-action', kwargs={'pk': self.sub.pk}),
                         {'action': 'request_changes', 'feedback': 'More detail', 'disagreement_reason': 'too_lenient',
                          'used_ai_feedback': True}, format='json')
        self.review.refresh_from_db()
        self.assertEqual((self.review.agreed, self.review.disagreement_reason), (False, 'too_lenient'))
        self.assertTrue(self.review.feedback_used)
        self.assertLess(self.review.feedback_similarity, 0.5)

    def test_example_from_submission_is_anonymised(self):
        res = self.client.post(reverse('review-example', kwargs={'pk': self.sub.pk}),
                               {'verdict': 'approve', 'reason': 'Three clear risks'}, format='json')
        self.assertEqual(res.status_code, 201)
        example = ReviewExample.objects.get()
        self.assertNotIn('Maria', example.text)
        self.assertNotIn('Pappa', example.text)
        self.assertNotIn('maria@example.org', example.text)
        self.assertIn('bias, privacy, errors', example.text)
        self.assertEqual(example.source_submission, self.sub)

    def test_reopen_only_auto_approved(self):
        url = reverse('review-reopen', kwargs={'pk': self.sub.pk})
        self.assertEqual(self.client.post(url).status_code, 400)
        AssignmentSubmission.objects.filter(pk=self.sub.pk).update(status='approved')
        AIReview.objects.filter(pk=self.review.pk).update(auto_approved=True)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'pending')


class ResubmitWhilePendingTests(APITestCase):
    def test_pending_submission_can_be_revised_and_gets_a_fresh_ai_review(self):
        from hub.models import AIReviewSettings
        settings = AIReviewSettings.get()
        settings.enabled = True
        settings.save()
        course, _, activity, resource = make_assignment()
        AssignmentReviewConfig.objects.create(resource=resource, enabled=True, criteria=CRITERIA, rubric_approved=True)
        learner = User.objects.create_user('rs_l', password='x')
        UserProfile.objects.create(user=learner)
        Enrollment.objects.create(user=learner, course=course)
        self.client.force_authenticate(learner)
        url = reverse('resource-submit-assignment', kwargs={'pk': course.pk, 'lesson_pk': activity.pk, 'resource_pk': resource.pk})
        self.assertEqual(self.client.post(url, {'text': 'First try'}, format='json').status_code, 201)
        res = self.client.post(url, {'text': 'Revised'}, format='json')
        self.assertEqual((res.status_code, res.data['status'], res.data['text']), (200, 'pending', 'Revised'))
        self.assertEqual(AIReview.objects.filter(submission__user=learner).count(), 2)


class LearnerAPITests(ReviewerAPITests):
    def precheck(self):
        from types import SimpleNamespace

        from hub.serializers.assignments import AssignmentSubmissionSerializer
        return AssignmentSubmissionSerializer(self.sub, context={'request': SimpleNamespace(user=self.learner)}).data['ai_precheck']

    def test_precheck_hidden_unless_learner_visible(self):
        self.assertIsNone(self.precheck())

    def test_precheck_in_learner_language(self):
        self.config.learner_visible = True
        self.config.save()
        pre = self.precheck()
        self.assertEqual((pre['status'], pre['feedback']), ('done', 'Καλή δουλειά.'))
        self.assertEqual([c['name'] for c in pre['criteria']], ['Τρεις κίνδυνοι', 'Sources'])

    def test_profile_opt_out(self):
        self.client.force_authenticate(self.learner)
        res = self.client.patch(reverse('profile-settings'), {'ai_training_opt_out': True}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.learner.profile.refresh_from_db()
        self.assertTrue(self.learner.profile.ai_training_opt_out)
