"""Queueing and running AI reviews; auto-approve; agreement statistics."""
import logging
import random
import time
from difflib import SequenceMatcher

from django.db import transaction
from django.utils import timezone

from hub.ai_review import model
from hub.ai_review.evidence import find_duplicates, gather
from hub.ai_review.metrics import summarise
from hub.models import AIReview, AIReviewSettings, AssignmentReviewConfig, AssignmentSubmission

log = logging.getLogger(__name__)


def queue_review(submission):
    if not submission.resource_id or not AIReviewSettings.get().enabled:
        return None
    config = getattr(submission.resource, 'ai_review_config', None)
    if config is None or not config.is_ready():
        return None
    review = AIReview.objects.create(
        submission=submission, model_name=AIReviewSettings.get().model_name,
        prompt_version=model.PROMPT_VERSION, rubric=config.criteria,
        submission_text=submission.text or '',
        attachment_names=[a.get('name') or a.get('url', '') for a in submission.attachments or []],
    )
    transaction.on_commit(lambda: _dispatch(review.id))
    return review


def _dispatch(review_id):
    """Hand the review to Celery; if the broker is down the submission is
    already saved, so the review is just marked failed (humans review)."""
    from hub.tasks import run_ai_review
    try:
        run_ai_review.delay(review_id)
    except Exception as exc:  # noqa: BLE001 — any broker error
        log.warning('AI review %s could not be queued: %s', review_id, exc)
        mark_failed(review_id, f'Could not be queued: {exc}')


def _switched_on(resource_id):
    """Platform switch and the assignment's set-up, read fresh (an admin may
    have switched AI review off while this review waited)."""
    config = AssignmentReviewConfig.objects.filter(resource_id=resource_id).first()
    return AIReviewSettings.get().enabled and config is not None and config.is_ready(), config


def _is_latest(review):
    return review.submission.ai_reviews.values_list('id', flat=True).first() == review.id


def _examples(resource):
    return [{'text': e.text, 'verdict': e.verdict, 'reason': e.reason} for e in resource.ai_review_examples.all()[:5]]


def run_review(review_id):
    review = AIReview.objects.select_related(
        'submission__user__profile', 'submission__resource__ai_review_config',
    ).get(pk=review_id)
    if review.status in (AIReview.Status.DONE, AIReview.Status.FAILED):
        return
    submission = review.submission
    if not _is_latest(review):
        mark_failed(review.id, 'Superseded by a newer version of the submission.')
        return
    on, config = _switched_on(submission.resource_id)
    if not on:
        mark_failed(review.id, 'AI review was switched off.')
        return
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
    _maybe_auto_approve(review)


def mark_failed(review_id, message):
    AIReview.objects.filter(pk=review_id).exclude(status=AIReview.Status.DONE).update(
        status=AIReview.Status.FAILED, error=message[:2000], finished_at=timezone.now())


def assignment_stats(resource):
    return summarise(AIReview.objects.filter(submission__resource=resource, status=AIReview.Status.DONE))


def auto_approve_unlocked(resource, settings):
    stats = assignment_stats(resource)
    return (stats['decided'] >= settings.unlock_min_reviews
            and (stats['approve_lower_bound'] or 0) >= settings.unlock_min_lower_bound)


def _maybe_auto_approve(review):
    """Approve a clear pass — re-checking everything against fresh state, since
    a human, the learner or an admin may have acted during the model call."""
    settings = AIReviewSettings.get()
    on, config = _switched_on(review.submission.resource_id)
    if not (on and config.auto_approve and auto_approve_unlocked(config.resource, settings)):
        return
    required = {c['id'] for c in review.rubric if c.get('required')}
    clear = (
        review.verdict == AIReview.Verdict.APPROVE
        and (review.confidence or 0) >= settings.confidence_threshold
        and all(c['status'] == 'met' for c in review.criteria_results if c['id'] in required)
        and not review.flagged
    )
    if not clear:
        return
    if random.random() < settings.spot_check_rate:
        review.spot_check = True
        review.save(update_fields=['spot_check'])
        return
    from hub.assignment_review import ReviewError, approve_submission
    with transaction.atomic():
        submission = AssignmentSubmission.objects.select_for_update().get(pk=review.submission_id)
        if submission.status != AssignmentSubmission.Status.PENDING or not _is_latest(review):
            return
        try:
            approve_submission(submission, reviewer=None, feedback=review.learner_feedback)
        except ReviewError:
            return
        review.auto_approved = True
        review.save(update_fields=['auto_approved'])


def record_human_verdict(submission, verdict, reason='', feedback_used=False, feedback=''):
    """Store the human decision on the review of *this* version only: if the
    newest review is not done yet (or failed), there is nothing to compare."""
    review = submission.ai_reviews.first()
    if review is None or review.status != AIReview.Status.DONE:
        return
    review.human_verdict = verdict
    review.agreed = (review.verdict == verdict) if review.verdict in ('approve', 'changes_requested') else None
    review.disagreement_reason = reason if review.agreed is False and reason in AIReview.DISAGREEMENT_REASONS else ''
    review.feedback_used = bool(feedback_used and review.learner_feedback)
    review.feedback_similarity = (round(SequenceMatcher(None, review.learner_feedback, feedback or '').ratio(), 3)
                                  if review.feedback_used else None)
    review.sent_feedback = feedback or ''
    review.save(update_fields=['human_verdict', 'agreed', 'disagreement_reason', 'feedback_used',
                               'feedback_similarity', 'sent_feedback'])
