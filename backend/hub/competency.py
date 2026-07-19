"""Competency score changes: clamping, band-based pathway re-assignment, decay math.

Spec: docs/superpowers/specs/2026-07-19-competency-decay-design.md
"""
from hub.models import LearnerActivityConfig, LearningPath, LessonProgress, UserLearningPath

SCORE_MIN = 0
SCORE_MAX = 6


def _band(score: int) -> int:
    if score <= 2:
        return 0
    if score <= 4:
        return 1
    return 2


def apply_competency_delta(user, delta: int) -> int:
    """Apply delta to the user's competency score.

    Clamps to 0..6; re-assigns the learning path when the band changes in
    either direction; schedules a recommendations recompute when the score
    actually changed. Returns the (possibly unchanged) score.
    """
    profile = user.profile
    old = profile.competency_score
    new = max(SCORE_MIN, min(SCORE_MAX, old + delta))
    if new == old:
        return old

    profile.competency_score = new
    profile.save(update_fields=['competency_score'])

    if _band(new) != _band(old):
        path = LearningPath.objects.filter(
            competency_min__lte=new, competency_max__gte=new,
        ).first()
        if path:
            UserLearningPath.objects.update_or_create(user=user, defaults={'path': path})

    from hub.tasks import compute_user_recommendations
    compute_user_recommendations.delay(user.id)
    return new


def course_completion_delta(user, course) -> int:
    """Score increment for a just-completed course (may be negative)."""
    config = LearnerActivityConfig.get()

    if config.quiz_affects_competency:
        quiz_scores = list(
            LessonProgress.objects.filter(
                user=user,
                lesson__module__course=course,
                lesson__lesson_type='quiz',
                quiz_score__isnull=False,
            ).values_list('quiz_score', flat=True)
        )
        if quiz_scores:
            avg = sum(quiz_scores) / len(quiz_scores)
            weight = (
                config.quiz_weight_pass
                if avg >= config.quiz_pass_threshold
                else config.quiz_weight_fail
            )
        else:
            weight = config.quiz_weight_pass
        delta = round(weight)
    else:
        delta = 1

    if config.decay_enabled:
        timed = list(
            LessonProgress.objects.filter(
                user=user,
                lesson__module__course=course,
                time_spent_seconds__isnull=False,
                lesson__duration_minutes__gt=0,
            ).select_related('lesson')
        )
        if timed:
            ratios = [
                (lp.time_spent_seconds / 60) / lp.lesson.duration_minutes
                for lp in timed
            ]
            if sum(ratios) / len(ratios) > config.slow_ratio_threshold:
                delta -= config.slow_penalty

    return delta
