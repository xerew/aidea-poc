"""Lesson-completion side effects — shared by learner self-completion and
assignment-review approval. Single source of truth for progress/competency."""
from django.utils import timezone

from hub.models import Lesson, LessonProgress, LessonSession


def record_lesson_completion(user, enrollment, lesson, quiz_answers_raw=None,
                             engagement_data=None, advance_only=False):
    """Create the LessonProgress row (first completion only) and update the
    enrollment's progress/current-module/completed-at plus the competency
    score. Returns (lesson_progress, progress_pct).

    advance_only: asynchronous callers (assignment-review approval) pass True
    so a late approval never moves the learner's resume pointer backward.
    """
    course = enrollment.course
    quiz_answers_raw = quiz_answers_raw or []

    lp, created = LessonProgress.objects.get_or_create(user=user, lesson=lesson)

    if created:
        now = timezone.now()
        lp.completed_at = now

        session = LessonSession.objects.filter(
            user=user, lesson=lesson,
        ).order_by('-started_at').first()
        if session:
            lp.time_spent_seconds = max(0, int((now - session.started_at).total_seconds()))

        if lesson.lesson_type == 'quiz' and quiz_answers_raw and lesson.quiz_data:
            booleans = []
            for i, selected in enumerate(quiz_answers_raw):
                if i < len(lesson.quiz_data):
                    options = lesson.quiz_data[i].get('options', [])
                    if isinstance(selected, int) and 0 <= selected < len(options):
                        booleans.append(bool(options[selected].get('is_correct', False)))
                    else:
                        booleans.append(False)
            # Pad to full question count so score denominator is always len(quiz_data)
            while len(booleans) < len(lesson.quiz_data):
                booleans.append(False)
            lp.quiz_answers = booleans
            lp.quiz_score = sum(booleans) / len(booleans) if booleans else 0.0

        engagement = dict(engagement_data or {})
        if lesson.lesson_type == 'assignment' and 'submission' in engagement:
            engagement['word_count'] = len(str(engagement['submission']).split())
        if lesson.lesson_type == 'quiz' and quiz_answers_raw:
            engagement['quiz_selected'] = quiz_answers_raw
        lp.engagement_data = engagement

        lp.save()

    total = Lesson.objects.filter(module__course=course, is_required=True).count()
    completed_count = LessonProgress.objects.filter(
        user=user,
        lesson__module__course=course,
        lesson__is_required=True,
    ).count()
    progress_pct = round((completed_count / total) * 100) if total > 0 else 0

    just_completed = progress_pct == 100 and enrollment.completed_at is None
    enrollment.progress_pct = progress_pct
    if not (
        advance_only
        and enrollment.current_module is not None
        and lesson.module.order < enrollment.current_module.order
    ):
        enrollment.current_module = lesson.module
    if just_completed:
        enrollment.completed_at = timezone.now()
    enrollment.save()

    if just_completed and hasattr(user, 'profile'):
        from hub.competency import apply_competency_delta, course_completion_delta
        apply_competency_delta(user, course_completion_delta(user, course))

    return lp, progress_pct
