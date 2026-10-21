"""Competency score changes: clamping, band-based pathway re-assignment, and
the course-completion rule (performance vs course difficulty).

Spec: docs/superpowers/specs/2026-10-21-competency-performance-design.md
(replaces the score rules of 2026-07-19-competency-decay-design.md).
"""
from collections import defaultdict

from hub.models import (
    AssignmentSubmission,
    CompetencyChange,
    LearnerActivityConfig,
    LearningPath,
    ResourceProgress,
    UserLearningPath,
)

SCORE_MIN = 0
SCORE_MAX = 6
COURSE_LEVELS = {'beginner': 0, 'intermediate': 1, 'advanced': 2}
SCORED_TYPES = ('quiz', 'h5p', 'assignment')
FIRST_REVIEW_SCORES = {'approved': 1.0, 'changes_requested': 0.0}


def _band(score: int) -> int:
    if score <= 2:
        return 0
    if score <= 4:
        return 1
    return 2


def apply_competency_delta(user, delta: int, recompute: bool = True, course=None, reason=None) -> int:
    """Apply delta to the user's competency score.

    Clamps to 0..6; records a CompetencyChange (with `course` and `reason`)
    when the score actually changes; re-assigns the learning path when the
    band changes in either direction; schedules a recommendations recompute
    (pass recompute=False when the caller batches several deltas). Returns
    the (possibly unchanged) score.
    """
    profile = user.profile
    old = profile.competency_score
    new = max(SCORE_MIN, min(SCORE_MAX, old + delta))
    if new == old:
        return old

    profile.competency_score = new
    profile.save(update_fields=['competency_score'])
    CompetencyChange.objects.create(user=user, course=course, old_score=old, new_score=new,
                                    delta=new - old, reason=reason or {})

    if _band(new) != _band(old):
        path = LearningPath.objects.filter(
            competency_min__lte=new, competency_max__gte=new,
        ).first()
        if path:
            # New level: new path and a course list rebuilt for that level.
            from hub.pathway_gen import generate_pathway
            UserLearningPath.objects.update_or_create(
                user=user, defaults={'path': path, 'course_ids': generate_pathway(user)},
            )

    if recompute:
        from hub.tasks import compute_user_recommendations
        compute_user_recommendations.delay(user.id)
    return new


def course_performance(user, course):
    """Mean over modules of the mean first-attempt score (0–1) of the scored
    items the user completed; None when nothing in the course counts."""
    rows = (
        ResourceProgress.objects
        .filter(user=user, resource__activity__module__course=course,
                completed_at__isnull=False, resource__type__in=SCORED_TYPES)
        .select_related('resource__activity')
    )
    first_reviews = dict(
        AssignmentSubmission.objects
        .filter(user=user, resource__activity__module__course=course)
        .exclude(first_review_status='')
        .values_list('resource_id', 'first_review_status')
    )
    by_module = defaultdict(list)
    for rp in rows:
        if rp.resource.type == 'assignment':
            score = FIRST_REVIEW_SCORES.get(first_reviews.get(rp.resource_id))
        else:
            score = rp.quiz_score          # set once, on the first completion
        if score is not None:
            by_module[rp.resource.activity.module_id].append(score)
    if not by_module:
        return None
    averages = [sum(scores) / len(scores) for scores in by_module.values()]
    return sum(averages) / len(averages)


def performance_delta(passed: bool, gap: int) -> int:
    """Change from the course-vs-teacher level gap (course level − teacher level)."""
    if gap < 0:
        return 0 if passed else -1
    if not passed:
        return 0
    return 2 if gap >= 2 else 1


def _is_slow(user, course, config) -> bool:
    """Mean ratio of time spent to planned time over the course's timed activities."""
    timed = list(
        ResourceProgress.objects.filter(
            user=user,
            resource__activity__module__course=course,
            completed_at__isnull=False,
            time_spent_seconds__isnull=False,
            resource__activity__duration_minutes__gt=0,
        ).select_related('resource__activity')
    )
    # One pace ratio per activity: its time is the max over its resources.
    per_activity = {}
    for rp in timed:
        act = rp.resource.activity
        per_activity[act.id] = (max(per_activity.get(act.id, (0, act))[0], rp.time_spent_seconds), act)
    if not per_activity:
        return False
    ratios = [(secs / 60) / act.duration_minutes for secs, act in per_activity.values()]
    return sum(ratios) / len(ratios) > config.slow_ratio_threshold


def course_completion_change(user, course):
    """(delta, reason) for a just-completed course."""
    config = LearnerActivityConfig.get()
    performance = course_performance(user, course)
    teacher_level = _band(user.profile.competency_score)
    course_level = COURSE_LEVELS.get(course.level, 0)
    gap = course_level - teacher_level
    if performance is None:
        rule, passed, base = 'completion', None, 1
    else:
        passed = performance >= config.quiz_pass_threshold
        rule, base = 'performance', performance_delta(passed, gap)
    slow = config.slow_penalty if config.slow_penalty_enabled and _is_slow(user, course, config) else 0
    reason = {
        'rule': rule, 'performance': None if performance is None else round(performance, 3), 'passed': passed,
        'course_level': course_level, 'teacher_level': teacher_level, 'gap': gap,
        'base_delta': base, 'slow_penalty': slow,
    }
    return base - slow, reason


def course_completion_delta(user, course) -> int:
    return course_completion_change(user, course)[0]


def apply_course_completion(user, enrollment, applied_by='completion'):
    """Apply a completed course's change once, stamping the enrollment in the
    same transaction (also when the change is 0 or clamped). Returns the delta,
    or None when it was already applied."""
    from django.db import transaction
    from django.utils import timezone

    from hub.models import Enrollment
    with transaction.atomic():
        locked = Enrollment.objects.select_for_update().select_related('course').get(pk=enrollment.pk)
        if locked.competency_applied_at is not None:
            return None
        delta, reason = course_completion_change(user, locked.course)
        if applied_by != 'completion':
            reason['applied_by'] = applied_by
        old = user.profile.competency_score
        new = apply_competency_delta(user, delta, recompute=False, course=locked.course, reason=reason)
        locked.competency_applied_at = timezone.now()
        locked.save(update_fields=['competency_applied_at'])
    enrollment.competency_applied_at = locked.competency_applied_at
    if new != old:
        from hub.tasks import compute_user_recommendations
        compute_user_recommendations.delay(user.id)   # after commit: reads the new score
    return delta


NIGHTLY_GRACE_HOURS = 1   # never race a completion that is still being handled


def apply_missed_competency_changes(now=None) -> int:
    """Nightly safety net: completed courses whose change was never applied
    (e.g. an error during completion) get it once, by the same rule."""
    import logging
    from datetime import timedelta

    from django.utils import timezone

    from hub.models import Enrollment
    cutoff = (now or timezone.now()) - timedelta(hours=NIGHTLY_GRACE_HOURS)
    missed = (
        Enrollment.objects
        .filter(completed_at__isnull=False, completed_at__lt=cutoff, competency_applied_at__isnull=True,
                user__profile__isnull=False)
        .select_related('user__profile', 'course')
    )
    fixed = 0
    for enrollment in missed:
        try:
            if apply_course_completion(enrollment.user, enrollment, applied_by='nightly') is not None:
                fixed += 1
        except Exception:  # noqa: BLE001 — one bad enrollment must not stop the others
            logging.getLogger(__name__).exception('Nightly competency check failed for enrollment %s', enrollment.pk)
    return fixed
