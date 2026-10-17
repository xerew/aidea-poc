"""Queueing and running AI reviews; auto-approve; agreement statistics."""
import random
import time
from difflib import SequenceMatcher

from django.db import transaction
from django.utils import timezone

from hub.ai_review import model
from hub.ai_review.evidence import find_duplicates, gather
from hub.ai_review.metrics import summarise
from hub.models import AIReview, AIReviewSettings, AssignmentSubmission


def queue_review(submission):
    if not submission.resource_id or not AIReviewSettings.get().enabled:
        return None
    config = getattr(submission.resource, 'ai_review_config', None)
    if config is None or not config.is_ready():
        return None
    review = AIReview.objects.create(
        submission=submission, model_name=AIReviewSettings.get().model_name,
        prompt_version=model.PROMPT_VERSION, rubric=config.criteria,
    )
    from hub.tasks import run_ai_review
    transaction.on_commit(lambda: run_ai_review.delay(review.id))
    return review


def _examples(resource):
    return [{'text': e.text, 'verdict': e.verdict, 'reason': e.reason} for e in resource.ai_review_examples.all()[:5]]


def run_review(review_id):
    review = AIReview.objects.select_related(
        'submission__user__profile', 'submission__resource__ai_review_config',
    ).get(pk=review_id)
    if review.status in (AIReview.Status.DONE, AIReview.Status.FAILED):
        return
    submission, config = review.submission, review.submission.resource.ai_review_config
    started = time.monotonic()
    review.status, review.attempts = AIReview.Status.RUNNING, review.attempts + 1
    review.save(update_fields=['status', 'attempts'])
    ev = gather(submission)
    checks = {'fingerprints': ev.fingerprints,
              'duplicates': find_duplicates(submission, ev.fingerprints) if config.duplicate_check else []}
    language = getattr(getattr(submission.user, 'profile', None), 'language', 'en') or 'en'
    try:
        result = model.review_submission(
            instructions=submission.resource.instructions, criteria=review.rubric,
            examples=_examples(submission.resource), evidence=ev, checks=checks,
            language=language, model=review.model_name,
        )
    except model.ModelOffline:
        review.status = AIReview.Status.QUEUED
        review.checks = checks
        review.save(update_fields=['status', 'checks'])
        raise
    except model.ReviewModelError as exc:
        review.status, review.error, review.checks = AIReview.Status.FAILED, str(exc)[:2000], checks
        review.finished_at = timezone.now()
        review.save()
        return
    review.checks = checks
    review.criteria_results = result['criteria']
    review.verdict, review.confidence = result['verdict'], result['confidence']
    review.learner_feedback, review.reviewer_notes = result['learner_feedback'], result['reviewer_notes']
    review.status, review.finished_at = AIReview.Status.DONE, timezone.now()
    review.duration_s = round(time.monotonic() - started, 1)
    review.save()
    _maybe_auto_approve(review, config)


def mark_failed(review_id, message):
    AIReview.objects.filter(pk=review_id).exclude(status=AIReview.Status.DONE).update(
        status=AIReview.Status.FAILED, error=message[:2000], finished_at=timezone.now())


def assignment_stats(resource):
    return summarise(AIReview.objects.filter(submission__resource=resource, status=AIReview.Status.DONE))


def auto_approve_unlocked(resource, settings):
    stats = assignment_stats(resource)
    return (stats['decided'] >= settings.unlock_min_reviews
            and (stats['approve_lower_bound'] or 0) >= settings.unlock_min_lower_bound)


def _maybe_auto_approve(review, config):
    settings = AIReviewSettings.get()
    if not (config.auto_approve and auto_approve_unlocked(config.resource, settings)):
        return
    required = {c['id'] for c in review.rubric if c.get('required')}
    clear = (
        review.verdict == AIReview.Verdict.APPROVE
        and (review.confidence or 0) >= settings.confidence_threshold
        and all(c['status'] == 'met' for c in review.criteria_results if c['id'] in required)
        and not review.flagged
        and review.submission.status == AssignmentSubmission.Status.PENDING
        and review.submission.ai_reviews.first().id == review.id   # not an older version
    )
    if not clear:
        return
    if random.random() < settings.spot_check_rate:
        review.spot_check = True
        review.save(update_fields=['spot_check'])
        return
    from hub.assignment_review import ReviewError, approve_submission
    try:
        approve_submission(review.submission, reviewer=None, feedback=review.learner_feedback)
    except ReviewError:
        return
    review.auto_approved = True
    review.save(update_fields=['auto_approved'])


def record_human_verdict(submission, verdict, reason='', feedback_used=False, feedback=''):
    review = submission.ai_reviews.filter(status=AIReview.Status.DONE).first()
    if review is None:
        return
    review.human_verdict = verdict
    review.agreed = (review.verdict == verdict) if review.verdict in ('approve', 'changes_requested') else None
    review.disagreement_reason = reason if review.agreed is False and reason in AIReview.DISAGREEMENT_REASONS else ''
    review.feedback_used = bool(feedback_used and review.learner_feedback)
    review.feedback_similarity = (round(SequenceMatcher(None, review.learner_feedback, feedback or '').ratio(), 3)
                                  if review.feedback_used else None)
    review.save(update_fields=['human_verdict', 'agreed', 'disagreement_reason', 'feedback_used', 'feedback_similarity'])
