"""Activity-completion side effects — shared by learner self-completion and
assignment-review approval. Single source of truth for progress/competency.

ResourceProgress is the source of truth. The legacy activity-level entry point
(record_lesson_completion) completes every resource of the activity and also
keeps writing LessonProgress, so the rollback window stays current."""
from django.db.models import Count, Q
from django.utils import timezone

from hub.models import (
    Activity,
    LessonProgress,
    LessonSession,
    Resource,
    ResourceProgress,
)

# ── Reads ─────────────────────────────────────────────────────────────────────


def activity_completion(user, course):
    """Return (required_ids, completed_required_ids, completed_ids) for a course.

    An activity is *required* when it has at least one required resource (the
    data migration copies lesson.is_required onto every resource, so this
    matches the legacy required lessons) — or when it has no resources yet but
    is marked is_required, so it still counts toward the total. It is *complete*
    when every required resource is done; an optional-only activity counts as
    complete once any of its resources is done (but never counts toward %)."""
    activities = (
        Activity.objects.filter(module__course=course)
        .annotate(
            req=Count('resources', filter=Q(resources__is_required=True), distinct=True),
            n_res=Count('resources', distinct=True),
        )
    )
    done = ResourceProgress.objects.filter(
        user=user, resource__activity__module__course=course, completed_at__isnull=False,
    )
    done_required = dict(
        done.filter(resource__is_required=True)
        .values_list('resource__activity_id')
        .annotate(n=Count('id'))
    )
    any_done = set(done.values_list('resource__activity_id', flat=True))

    required, completed_required, completed = set(), set(), set()
    for a in activities:
        if a.req:
            required.add(a.id)
            if done_required.get(a.id, 0) >= a.req:
                completed_required.add(a.id)
                completed.add(a.id)
        elif a.n_res == 0:
            if a.is_required:
                required.add(a.id)
        elif a.id in any_done:
            completed.add(a.id)
    return required, completed_required, completed


def completed_activity_ids(user, course):
    """Ids of the course's activities the user has completed."""
    return activity_completion(user, course)[2]


def activity_time_seconds(resource_progress_rows):
    """Total time across activities from ResourceProgress rows. Each resource of
    an activity records elapsed time since the activity session began, so the
    activity's time is the max over its resources (summing would double-count).
    Rows must have `resource` loaded (select_related)."""
    per_activity = {}
    for rp in resource_progress_rows:
        aid = rp.resource.activity_id
        per_activity[aid] = max(per_activity.get(aid, 0), rp.time_spent_seconds or 0)
    return sum(per_activity.values())


def recompute_course_progress(user, enrollment):
    """Recompute an enrollment's progress_pct from completed *required activities*
    across the course, updating completed_at and competency on first 100%.
    Returns progress_pct."""
    course = enrollment.course
    # Activity-weighted (not resource-weighted) so migrated enrollments keep the
    # exact percentage the legacy lesson-based calculation gave them.
    required, completed_required, _ = activity_completion(user, course)
    total = len(required)
    progress_pct = round((len(completed_required) / total) * 100) if total > 0 else 0

    just_completed = progress_pct == 100 and enrollment.completed_at is None
    enrollment.progress_pct = progress_pct
    if just_completed:
        enrollment.completed_at = timezone.now()
    enrollment.save()

    if just_completed and hasattr(user, 'profile'):
        from hub.competency import apply_competency_delta, course_completion_delta
        apply_competency_delta(user, course_completion_delta(user, course))

    return progress_pct


# ── Writes ────────────────────────────────────────────────────────────────────


def _score_quiz(quiz_data, quiz_answers_raw):
    """Return (booleans, score) for a quiz given the learner's selected option
    indices. Score denominator is always len(quiz_data)."""
    booleans = []
    for i, selected in enumerate(quiz_answers_raw):
        if i < len(quiz_data):
            options = quiz_data[i].get('options', [])
            booleans.append(
                isinstance(selected, int) and 0 <= selected < len(options)
                and bool(options[selected].get('is_correct', False))
            )
    while len(booleans) < len(quiz_data):
        booleans.append(False)
    score = sum(booleans) / len(booleans) if booleans else 0.0
    return booleans, score


def _session_seconds(user, activity, now):
    """Seconds since the learner's latest session on the activity, or None."""
    session = LessonSession.objects.filter(
        user=user, lesson=activity,
    ).order_by('-started_at').first()
    return max(0, int((now - session.started_at).total_seconds())) if session else None


def _engagement(kind, engagement_data, quiz_answers_raw):
    engagement = dict(engagement_data or {})
    if kind == 'assignment' and 'submission' in engagement:
        engagement['word_count'] = len(str(engagement['submission']).split())
    if kind == 'quiz' and quiz_answers_raw:
        engagement['quiz_selected'] = quiz_answers_raw
    return engagement


def _mark_resource_complete(user, resource, quiz_answers_raw=None, engagement_data=None):
    """Idempotently mark one resource complete, scoring a quiz resource."""
    rp, _ = ResourceProgress.objects.get_or_create(user=user, resource=resource)
    if rp.completed_at is None:
        now = timezone.now()
        rp.completed_at = now
        rp.time_spent_seconds = _session_seconds(user, resource.activity, now)
        if resource.type == 'quiz' and quiz_answers_raw and resource.quiz_data:
            rp.quiz_answers, rp.quiz_score = _score_quiz(resource.quiz_data, quiz_answers_raw)
        rp.engagement_data = _engagement(resource.type, engagement_data, quiz_answers_raw)
        rp.save()
    return rp


def _advance_pointer(enrollment, activity, advance_only):
    """Move the resume pointer to the activity's module. advance_only: async
    callers (assignment approval) pass True so a late approval never moves the
    pointer backward."""
    if not (
        advance_only
        and enrollment.current_module is not None
        and activity.module.order < enrollment.current_module.order
    ):
        enrollment.current_module = activity.module
        enrollment.save(update_fields=['current_module'])


def ensure_resources(activity):
    """Build resources from an activity's legacy fields when it has none, so
    activities created through legacy paths take part in resource progress."""
    if not activity.resources.exists():
        from hub.content_migration_logic import build_resources_for_lesson
        build_resources_for_lesson(activity, Resource)


def _mirror_legacy_progress(user, activity):
    """Rollback window: once an activity is complete on the resource path, write
    the matching LessonProgress row so a rollback to the lesson-based code keeps
    the learner's progress. Removed with the legacy columns."""
    if activity.id not in completed_activity_ids(user, activity.module.course):
        return
    rows = list(
        ResourceProgress.objects.filter(user=user, resource__activity=activity)
        .select_related('resource')
    )
    quiz = next((r for r in rows if r.resource.type == 'quiz'), None)
    assignment = next((r for r in rows if r.resource.type == 'assignment'), None)
    LessonProgress.objects.get_or_create(
        user=user, lesson=activity,
        defaults={
            'completed_at': timezone.now(),
            'time_spent_seconds': activity_time_seconds(rows) or None,
            'quiz_score': quiz.quiz_score if quiz else None,
            'quiz_answers': quiz.quiz_answers if quiz else [],
            'engagement_data': (quiz or assignment).engagement_data if (quiz or assignment) else {},
        },
    )


def record_resource_completion(user, enrollment, resource, quiz_answers_raw=None,
                               engagement_data=None, advance_only=False):
    """Mark one resource complete for the learner (idempotent), scoring a quiz
    resource, then re-aggregate the enrollment. Returns (resource_progress,
    progress_pct)."""
    rp = _mark_resource_complete(user, resource, quiz_answers_raw, engagement_data)
    _mirror_legacy_progress(user, resource.activity)
    _advance_pointer(enrollment, resource.activity, advance_only)
    return rp, recompute_course_progress(user, enrollment)


def record_lesson_completion(user, enrollment, lesson, quiz_answers_raw=None,
                             engagement_data=None, advance_only=False):
    """Legacy activity-level completion (old /lessons/ endpoints and approvals
    of legacy submissions). Completes every resource of the activity — scoring
    quiz resources — and dual-writes LessonProgress for the rollback window.
    Returns (progress_row, progress_pct); for a quiz activity progress_row is
    the quiz resource's ResourceProgress (carries quiz_answers/quiz_score)."""
    quiz_answers_raw = quiz_answers_raw or []

    lp, created = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    if created:
        now = timezone.now()
        lp.completed_at = now
        lp.time_spent_seconds = _session_seconds(user, lesson, now)
        if lesson.lesson_type == 'quiz' and quiz_answers_raw and lesson.quiz_data:
            lp.quiz_answers, lp.quiz_score = _score_quiz(lesson.quiz_data, quiz_answers_raw)
        lp.engagement_data = _engagement(lesson.lesson_type, engagement_data, quiz_answers_raw)
        lp.save()

    ensure_resources(lesson)
    quiz_rp = None
    for resource in lesson.resources.order_by('order'):
        rp = _mark_resource_complete(
            user, resource,
            quiz_answers_raw if resource.type == 'quiz' else None,
            engagement_data,
        )
        if resource.type == 'quiz' and quiz_rp is None:
            quiz_rp = rp

    _advance_pointer(enrollment, lesson, advance_only)
    return (quiz_rp or lp), recompute_course_progress(user, enrollment)
