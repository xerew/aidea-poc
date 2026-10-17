from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase

from hub.ai_review import model, pipeline
from hub.models import (
    AIReview,
    AIReviewSettings,
    AssignmentReviewConfig,
    AssignmentSubmission,
    Enrollment,
    ResourceProgress,
    UserProfile,
)

from .test_ai_review_model import CRITERIA, answer
from .test_ai_review_models import make_assignment


class PipelineTests(TestCase):
    def setUp(self):
        self.course, _, self.activity, self.resource = make_assignment()
        self.settings = AIReviewSettings.get()
        self.settings.enabled = True
        self.settings.save()
        self.config = AssignmentReviewConfig.objects.create(
            resource=self.resource, enabled=True, criteria=CRITERIA, rubric_approved=True,
        )
        self.learner = User.objects.create_user('pl', password='x', email='pl@example.org')
        UserProfile.objects.create(user=self.learner, language='el')
        Enrollment.objects.create(user=self.learner, course=self.course)

    def submit(self, text='Bias, privacy, errors'):
        # One submission per learner and activity (unique_together); submitting
        # again updates it, as a real resubmission does.
        sub, _ = AssignmentSubmission.objects.update_or_create(
            user=self.learner, lesson=self.activity,
            defaults={'resource': self.resource, 'text': text, 'status': 'pending'},
        )
        return sub

    def other_submission(self):
        """Another learner's submission to the same assignment (history for stats)."""
        self._others = getattr(self, '_others', 0) + 1
        user = User.objects.create_user(f'pl_other{self._others}', password='x')
        UserProfile.objects.create(user=user)
        return AssignmentSubmission.objects.create(user=user, lesson=self.activity, resource=self.resource, text='t')

    def run_with(self, *answers):
        sub = self.submit()
        review = pipeline.queue_review(sub)
        with mock.patch.object(model, '_chat', side_effect=list(answers)):
            pipeline.run_review(review.id)
        review.refresh_from_db()
        sub.refresh_from_db()
        return review, sub

    # queueing
    def test_queue_needs_platform_switch_config_and_resource(self):
        self.settings.enabled = False
        self.settings.save()
        self.assertIsNone(pipeline.queue_review(self.submit()))
        self.settings.enabled = True
        self.settings.save()
        self.config.rubric_approved = False
        self.config.save()
        self.assertIsNone(pipeline.queue_review(self.submit()))

    def test_review_stored(self):
        review, sub = self.run_with(answer())
        self.assertEqual((review.status, review.verdict, review.confidence), ('done', 'approve', 0.86))
        self.assertEqual(review.model_name, 'qwen2.5vl:32b')
        self.assertEqual(review.prompt_version, model.PROMPT_VERSION)
        self.assertEqual(review.rubric, CRITERIA)
        self.assertEqual([c['id'] for c in review.criteria_results], ['c1', 'c2'])
        self.assertEqual(sub.status, 'pending')          # shadow mode: humans still decide
        self.assertIsNotNone(review.finished_at)

    def test_malformed_answer_twice_marks_failed(self):
        review, sub = self.run_with('nope', 'nope')
        self.assertEqual(review.status, 'failed')
        self.assertTrue(review.error)
        self.assertEqual(sub.status, 'pending')

    def test_offline_is_retried_then_failed(self):
        sub = self.submit()
        review = pipeline.queue_review(sub)
        with mock.patch.object(model, '_chat', side_effect=model.ModelOffline('down')):
            with self.assertRaises(model.ModelOffline):
                pipeline.run_review(review.id)
        review.refresh_from_db()
        self.assertEqual(review.status, 'queued')         # waiting for the retry
        pipeline.mark_failed(review.id, 'gave up')
        review.refresh_from_db()
        self.assertEqual((review.status, review.error), ('failed', 'gave up'))

    # auto-approve rules
    def unlock(self):
        self.config.auto_approve = True
        self.config.save()
        other = self.other_submission()
        for _ in range(40):      # 40/40 agreeing: lower bound 0.912
            AIReview.objects.create(submission=other, status='done', verdict='approve', human_verdict='approve', agreed=True)

    def test_locked_assignment_never_auto_approves(self):
        self.config.auto_approve = True
        self.config.save()
        review, sub = self.run_with(answer())
        self.assertEqual((sub.status, review.auto_approved), ('pending', False))

    def test_unlocked_clear_pass_is_auto_approved(self):
        self.unlock()
        with mock.patch('hub.ai_review.pipeline.random.random', return_value=0.5):
            review, sub = self.run_with(answer())
        self.assertEqual((sub.status, review.auto_approved), ('approved', True))
        self.assertIsNone(sub.reviewed_by)
        self.assertTrue(ResourceProgress.objects.filter(user=self.learner, resource=self.resource, completed_at__isnull=False).exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_each_rule_blocks_auto_approval(self):
        self.unlock()
        cases = {
            'low confidence': answer(confidence=0.5),
            'not approve': answer(verdict='unsure'),
            'required partly met': answer(criteria=[{'id': 'c1', 'status': 'partly_met', 'reason': ''},
                                                    {'id': 'c2', 'status': 'met', 'reason': ''}]),
        }
        for label, raw in cases.items():
            with mock.patch('hub.ai_review.pipeline.random.random', return_value=0.5):
                review, sub = self.run_with(raw)
            self.assertEqual(sub.status, 'pending', label)

    def test_duplicate_flag_blocks_auto_approval(self):
        self.unlock()
        with mock.patch('hub.ai_review.pipeline.random.random', return_value=0.5), \
             mock.patch('hub.ai_review.pipeline.find_duplicates', return_value=[{'submission_id': 1, 'learner': 'Bo', 'file': 'a.png', 'match': 'identical'}]):
            review, sub = self.run_with(answer())
        self.assertTrue(review.flagged)
        self.assertEqual(sub.status, 'pending')

    def test_spot_check_keeps_it_for_a_human(self):
        self.unlock()
        with mock.patch('hub.ai_review.pipeline.random.random', return_value=0.05):
            review, sub = self.run_with(answer())
        self.assertEqual((sub.status, review.spot_check, review.auto_approved), ('pending', True, False))

    # stats and human verdicts
    def test_stats_and_unlock(self):
        AIReview.objects.create(submission=self.other_submission(), status='done', verdict='approve', human_verdict='approve', agreed=True)
        AIReview.objects.create(submission=self.other_submission(), status='done', verdict='approve', human_verdict='changes_requested', agreed=False)
        AIReview.objects.create(submission=self.other_submission(), status='done', verdict='changes_requested', human_verdict='changes_requested', agreed=True,
                                criteria_results=[{'id': 'c1', 'status': 'not_met', 'reason': ''}])
        stats = pipeline.assignment_stats(self.resource)
        self.assertEqual((stats['reviews'], stats['decided']), (3, 3))
        self.assertAlmostEqual(stats['agreement'], 2 / 3, places=3)
        self.assertAlmostEqual(stats['kappa'], 0.4, places=3)
        self.assertAlmostEqual(stats['approve_agreement'], 0.5)
        self.assertAlmostEqual(stats['approve_lower_bound'], 0.095, places=3)
        self.assertEqual(stats['most_missed'], 'c1')
        self.assertFalse(pipeline.auto_approve_unlocked(self.resource, self.settings))

    def test_unlock_needs_a_reliable_lower_bound(self):
        other = self.other_submission()
        for _ in range(34):
            AIReview.objects.create(submission=other, status='done', verdict='approve', human_verdict='approve', agreed=True)
        self.assertFalse(pipeline.auto_approve_unlocked(self.resource, self.settings))   # 34/34: lower bound 0.898
        AIReview.objects.create(submission=other, status='done', verdict='approve', human_verdict='approve', agreed=True)
        self.assertTrue(pipeline.auto_approve_unlocked(self.resource, self.settings))    # 35/35: 0.901

    def test_record_human_verdict(self):
        review, sub = self.run_with(answer())
        pipeline.record_human_verdict(sub, 'changes_requested', reason='too_lenient')
        review.refresh_from_db()
        self.assertEqual((review.human_verdict, review.agreed, review.disagreement_reason),
                         ('changes_requested', False, 'too_lenient'))
        pipeline.record_human_verdict(sub, 'approve', reason='bogus')
        review.refresh_from_db()
        self.assertEqual((review.agreed, review.disagreement_reason), (True, ''))

    def test_feedback_use_is_recorded(self):
        review, sub = self.run_with(answer(learner_feedback='Good list of three risks.'))
        pipeline.record_human_verdict(sub, 'approve', feedback_used=True, feedback='Good list of three risks.')
        review.refresh_from_db()
        self.assertEqual((review.feedback_used, review.feedback_similarity), (True, 1.0))
        pipeline.record_human_verdict(sub, 'approve', feedback_used=True, feedback='Good list. Add a source next time.')
        review.refresh_from_db()
        self.assertLess(review.feedback_similarity, 0.95)
        pipeline.record_human_verdict(sub, 'approve')
        review.refresh_from_db()
        self.assertEqual((review.feedback_used, review.feedback_similarity), (False, None))

    def test_reopen_auto_approved(self):
        from hub.assignment_review import reopen_submission
        self.unlock()
        with mock.patch('hub.ai_review.pipeline.random.random', return_value=0.5):
            review, sub = self.run_with(answer())
        mail.outbox.clear()
        reopen_submission(sub)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'pending')
        self.assertFalse(ResourceProgress.objects.filter(user=self.learner, resource=self.resource).exists())
        self.assertEqual(mail.outbox[0].subject, 'Your submission is being reviewed again')

    def test_review_of_an_older_version_never_auto_approves(self):
        self.unlock()
        sub = self.submit()
        old = pipeline.queue_review(sub)
        self.submit(text='Revised answer')            # learner resubmits while pending
        pipeline.queue_review(sub)
        with mock.patch.object(model, '_chat', side_effect=[answer()]), \
             mock.patch('hub.ai_review.pipeline.random.random', return_value=0.5):
            pipeline.run_review(old.id)
        sub.refresh_from_db()
        old.refresh_from_db()
        # The older version's review is superseded (not run at all), so it cannot approve.
        self.assertEqual((old.status, old.auto_approved, sub.status), ('failed', False, 'pending'))
