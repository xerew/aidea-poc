import logging
import math
import random

from celery import shared_task

from hub.translation import translate_text

logger = logging.getLogger(__name__)

# Multiplicative nudge for courses whose subjects match the teacher's subject
# (or the catch-all General/All). Kept as a fixed constant here; the
# recommendations rework (#24) may move signal tuning into RecommendationConfig.
SUBJECT_MATCH_BOOST = 1.2


@shared_task
def compute_course_embeddings(course_id: int) -> None:
    from django.db import connection

    if connection.vendor != 'postgresql':
        return

    from sentence_transformers import SentenceTransformer

    from hub.models import Course
    from hub.models.recommendations import CourseEmbedding

    course = Course.objects.get(pk=course_id)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    subjects = ' '.join(course.subjects.values_list('name', flat=True))
    text = f"{course.title} {course.description} {subjects}".strip()
    embedding = model.encode(text).tolist()
    CourseEmbedding.objects.update_or_create(
        course=course,
        defaults={'embedding': embedding},
    )


@shared_task
def compute_user_recommendations(user_id: int) -> None:
    from django.db import connection

    if connection.vendor != 'postgresql':
        return

    import numpy as np
    from django.contrib.auth.models import User
    from django.db.models import Count
    from django.utils import timezone
    from pgvector.django import CosineDistance
    from sentence_transformers import SentenceTransformer

    from hub.models.enrollment import Enrollment, LessonProgress
    from hub.models.recommendations import (
        CourseEmbedding,
        CourseRecommendation,
        CourseView,
        RecommendationConfig,
        RecommendationEvent,
    )

    config = RecommendationConfig.get()
    model = SentenceTransformer('all-MiniLM-L6-v2')
    now = timezone.now()

    user = User.objects.select_related('profile').get(pk=user_id)
    profile = user.profile

    # ── ε-greedy weight selection ─────────────────────────────────────────
    event_count = RecommendationEvent.objects.filter(source='personal').count()
    if config.bandit_active and config.n_min <= event_count < config.n_full:
        span = max(1, config.n_full - config.n_min)
        epsilon = 0.1 * max(0.0, 1.0 - (event_count - config.n_min) / span)
        if random.random() < epsilon:
            alpha = max(0.0, config.alpha + random.uniform(-0.05, 0.05))
            beta  = max(0.0, config.beta  + random.uniform(-0.05, 0.05))
            gamma = max(0.0, config.gamma + random.uniform(-0.05, 0.05))
            total = alpha + beta + gamma or 1.0
            alpha, beta, gamma = alpha / total, beta / total, gamma / total
        else:
            alpha, beta, gamma = config.alpha, config.beta, config.gamma
    else:
        alpha, beta, gamma = config.alpha, config.beta, config.gamma

    # ── Signal ①: Profile vector ──────────────────────────────────────────
    goals_str = ', '.join(profile.goals) if profile.goals else 'general'
    subject   = profile.subject.name if profile.subject else 'general'
    level_str = profile.get_teaching_level_display() if profile.teaching_level else 'unknown'
    profile_text = (
        f"{subject} teacher, {level_str}, "
        f"competency {profile.competency_score}/6, goals: {goals_str}"
    )
    profile_vec = model.encode(profile_text)

    # ── Signal ②: Pillar bias vector ──────────────────────────────────────
    pillar_vec = None
    if profile.preferred_pillars:
        raw_embeddings = list(
            CourseEmbedding.objects
            .filter(
                course__pillar__slug__in=profile.preferred_pillars,
                course__is_published=True,
            )
            .values_list('embedding', flat=True)
        )
        if raw_embeddings:
            arr = np.array(raw_embeddings, dtype=np.float32)
            mean_vec = arr.mean(axis=0)
            norm = np.linalg.norm(mean_vec)
            if norm > 0:
                pillar_vec = mean_vec / norm

    # ── Signal ③: Behavioural vector ─────────────────────────────────────
    enrollments = list(Enrollment.objects.filter(user=user).select_related('course'))
    enrolled_ids = {e.course_id for e in enrollments}

    lesson_counts: dict[int, int] = {}
    if enrolled_ids:
        rows = (
            LessonProgress.objects
            .filter(user=user, lesson__module__course_id__in=enrolled_ids)
            .values('lesson__module__course_id')
            .annotate(n=Count('id'))
        )
        lesson_counts = {r['lesson__module__course_id']: r['n'] for r in rows}

    view_counts: dict[int, int] = {}
    rows = (
        CourseView.objects
        .filter(user=user)
        .values('course_id')
        .annotate(n=Count('id'))
    )
    view_counts = {r['course_id']: r['n'] for r in rows}

    weighted_vecs = []
    seen_course_ids: set[int] = set()

    for enr in enrollments:
        days_idle = max(0, (now - enr.last_accessed_at).days)
        decay = math.exp(-days_idle / 30.0)
        p = enr.progress_pct
        if p == 100:
            base = config.w_completed
        elif p >= 50:
            base = config.w_deep
        elif p >= 10:
            base = config.w_active
        elif days_idle <= 7:
            base = config.w_enrolled
        else:
            base = config.w_abandoned

        lesson_bonus = lesson_counts.get(enr.course_id, 0) * config.w_lesson
        score = min(max(base + lesson_bonus, -0.2), 1.0) * decay

        try:
            emb = CourseEmbedding.objects.get(course=enr.course)
        except CourseEmbedding.DoesNotExist:
            continue

        weighted_vecs.append(score * np.array(emb.embedding, dtype=np.float32))
        seen_course_ids.add(enr.course_id)

    for course_id, n in view_counts.items():
        if course_id in seen_course_ids:
            continue
        view_score = min(max(n * config.w_view, -0.2), 1.0)
        try:
            emb = CourseEmbedding.objects.get(course_id=course_id)
        except CourseEmbedding.DoesNotExist:
            continue
        weighted_vecs.append(view_score * np.array(emb.embedding, dtype=np.float32))

    behaviour_vec = None
    if weighted_vecs:
        raw = np.sum(weighted_vecs, axis=0)
        norm = np.linalg.norm(raw)
        if norm > 0:
            behaviour_vec = raw / norm

    # ── Combine signals ───────────────────────────────────────────────────
    user_vec = alpha * profile_vec
    if behaviour_vec is not None:
        user_vec = user_vec + beta * behaviour_vec
    if pillar_vec is not None:
        user_vec = user_vec + gamma * pillar_vec

    norm = np.linalg.norm(user_vec)
    # Fallback to profile-only vector if combined sum is zero (all signals cancelled out)
    user_vec_list = (user_vec / norm).tolist() if norm > 0 else profile_vec.tolist()

    # ── Score and filter candidates ───────────────────────────────────────
    score_val = profile.competency_score
    level_num = 0 if score_val <= 2 else (1 if score_val <= 4 else 2)
    course_level_nums = {'beginner': 0, 'intermediate': 1, 'advanced': 2}

    candidates = (
        CourseEmbedding.objects
        .select_related('course__pillar')
        .prefetch_related('course__subjects')
        .exclude(course_id__in=enrolled_ids)
        .filter(course__is_published=True)
        .annotate(distance=CosineDistance('embedding', user_vec_list))
        .order_by('distance')[:20]
    )

    # A course tagged with the teacher's subject (or the catch-all General/All)
    # is nudged up. Deeper signal-weight tuning lives in the recommendations
    # rework (#24); this is a light, fixed alignment boost.
    teacher_subject_slug = profile.subject.slug if profile.subject else None

    filtered = []
    for emb in candidates:
        if course_level_nums.get(emb.course.level, 0) > level_num + 1:
            continue
        similarity = max(0.0, 1.0 - float(emb.distance))
        if profile.learning_style and emb.course.content_format == profile.learning_style:
            similarity *= config.style_boost
        if teacher_subject_slug:
            course_subject_slugs = {s.slug for s in emb.course.subjects.all()}
            if teacher_subject_slug in course_subject_slugs or 'general' in course_subject_slugs:
                similarity *= SUBJECT_MATCH_BOOST
        filtered.append((emb.course, similarity))
        if len(filtered) >= 5:
            break

    # ── Write personal recommendations ───────────────────────────────────
    CourseRecommendation.objects.filter(user=user, source='personal').delete()

    subject_display = profile.subject.name if profile.subject else 'general'
    level_name = ('beginner', 'intermediate', 'advanced')[level_num]
    for course, similarity in filtered:
        CourseRecommendation.objects.create(
            user=user,
            course=course,
            score=similarity,
            reason=f"Matches your {level_name} level and {subject_display} focus",
            source='personal',
        )

    # ── Trigger CF task ───────────────────────────────────────────────────
    compute_cf_recommendations.delay(user_id)


@shared_task
def compute_cf_recommendations(user_id: int) -> None:
    from django.db import connection

    if connection.vendor != 'postgresql':
        return

    from django.contrib.auth.models import User
    from django.db.models import Count

    from hub.models.enrollment import Enrollment
    from hub.models.recommendations import CourseRecommendation
    from hub.models.user import UserProfile

    user = User.objects.select_related('profile').get(pk=user_id)
    profile = user.profile

    score = profile.competency_score
    if score <= 2:
        band_filter = {'competency_score__lte': 2}
    elif score <= 4:
        band_filter = {'competency_score__gte': 3, 'competency_score__lte': 4}
    else:
        band_filter = {'competency_score__gte': 5}

    peer_ids = list(
        UserProfile.objects
        .filter(
            subject=profile.subject,
            teaching_level=profile.teaching_level,
            onboarding_completed=True,
            **band_filter,
        )
        .exclude(user=user)
        .values_list('user_id', flat=True)
    )
    group_size = len(peer_ids)
    if group_size == 0:
        return

    enrolled_ids = set(
        Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
    )
    personal_ids = set(
        CourseRecommendation.objects
        .filter(user=user, source='personal')
        .values_list('course_id', flat=True)
    )
    exclude_ids = enrolled_ids | personal_ids

    top_courses = (
        Enrollment.objects
        .filter(user_id__in=peer_ids, course__is_published=True)
        .exclude(course_id__in=exclude_ids)
        .values('course_id')
        .annotate(n=Count('user_id', distinct=True))
        .order_by('-n')[:3]
    )

    CourseRecommendation.objects.filter(user=user, source='cf').delete()

    subject_display = profile.subject.name if profile.subject else 'teachers'
    for item in top_courses:
        pct = round(item['n'] / group_size * 100)
        CourseRecommendation.objects.create(
            user=user,
            course_id=item['course_id'],
            score=item['n'] / group_size,
            reason=f"{pct}% of {subject_display} teachers also enrolled",
            source='cf',
        )


@shared_task
def tune_recommendation_weights() -> None:
    from django.db import connection

    if connection.vendor != 'postgresql':
        return

    from collections import defaultdict
    from datetime import timedelta

    from django.utils import timezone

    from hub.models.recommendations import RecommendationConfig, RecommendationEvent

    config = RecommendationConfig.get()
    event_count = RecommendationEvent.objects.filter(source='personal').count()

    if event_count < config.n_min:
        if config.bandit_active:
            config.bandit_active = False
            config.save()
        return

    if not config.bandit_active:
        config.bandit_active = True
        config.save()

    if event_count < config.n_full:
        return

    # Phase 3: gradient update using last 30 days of personal events
    cutoff = timezone.now() - timedelta(days=30)
    reward_map = {
        'clicked':   config.reward_click,
        'enrolled':  config.reward_enroll,
        'completed': config.reward_complete,
        'shown':     0.0,
    }

    events = list(
        RecommendationEvent.objects
        .filter(source='personal', created_at__gte=cutoff)
        .exclude(weights_snapshot={})
        .values('weights_snapshot', 'event_type')
    )
    if not events:
        return

    snapshot_rewards: dict[tuple, list] = defaultdict(list)
    for event in events:
        snap = event['weights_snapshot']
        key = (
            snap.get('alpha', config.alpha),
            snap.get('beta',  config.beta),
            snap.get('gamma', config.gamma),
        )
        snapshot_rewards[key].append(reward_map.get(event['event_type'], 0.0))

    best_key = max(
        snapshot_rewards,
        key=lambda k: sum(snapshot_rewards[k]) / len(snapshot_rewards[k]),
    )
    best_alpha, best_beta, best_gamma = best_key

    lr = config.learning_rate
    config.alpha = config.alpha + lr * (best_alpha - config.alpha)
    config.beta  = config.beta  + lr * (best_beta  - config.beta)
    config.gamma = config.gamma + lr * (best_gamma - config.gamma)
    config.save()


@shared_task
def apply_competency_decay() -> None:
    """Nightly: dock competency for enrollments abandoned mid-course."""
    from datetime import timedelta

    from django.utils import timezone

    from hub.competency import apply_competency_delta
    from hub.models import Enrollment, LearnerActivityConfig

    config = LearnerActivityConfig.get()
    if not config.decay_enabled:
        return

    cutoff = timezone.now() - timedelta(days=config.idle_decay_days)
    stale = (
        Enrollment.objects
        .filter(
            progress_pct__gt=0,
            progress_pct__lt=100,
            last_accessed_at__lt=cutoff,
            decay_applied_at__isnull=True,
        )
        .select_related('user__profile')
    )
    now = timezone.now()
    decayed_user_ids = set()
    for enrollment in stale:
        # Batch the recompute: one per affected user, not one per enrollment
        apply_competency_delta(
            enrollment.user, -config.idle_decay_points, recompute=False,
        )
        decayed_user_ids.add(enrollment.user_id)
        enrollment.decay_applied_at = now
        enrollment.save(update_fields=['decay_applied_at'])

    for user_id in decayed_user_ids:
        compute_user_recommendations.delay(user_id)


@shared_task
def recompute_all_recommendations() -> None:
    from django.contrib.auth.models import User

    user_ids = list(
        User.objects.filter(
            profile__onboarding_completed=True,
        ).values_list('id', flat=True)
    )
    for uid in user_ids:
        compute_user_recommendations.delay(uid)


@shared_task
def translate_course(course_id: int, target: str) -> None:
    from hub.models import Course
    from hub.translation import TranslationError

    try:
        course = Course.objects.prefetch_related('modules__lessons').get(pk=course_id)
    except Course.DoesNotExist:
        return
    src = course.source_language

    def tr(text):
        return translate_text(text, src, target)

    def tr_quiz(quiz_data):
        out = []
        for q in quiz_data or []:
            out.append({
                'question': tr(q.get('question', '')),
                'options': [
                    {'text': tr(o.get('text', '')), 'is_correct': bool(o.get('is_correct'))}
                    for o in q.get('options', [])
                ],
            })
        return out

    try:
        course.translations[target] = {
            'title': tr(course.title),
            'description': tr(course.description),
            'learning_outcomes': [tr(o) for o in (course.learning_outcomes or [])],
        }
        for module in course.modules.all():
            module.translations[target] = {'title': tr(module.title), 'description': tr(module.description)}
            module.save(update_fields=['translations'])
            for lesson in module.lessons.all():
                blob = {'title': tr(lesson.title), 'description': tr(lesson.description)}
                # `content` is prose only for text/assignment; for video/image/pdf
                # it's a URL — translating it would mangle the link, so leave it
                # to fall back to the original.
                if lesson.lesson_type in ('text', 'assignment'):
                    blob['content'] = tr(lesson.content)
                elif lesson.lesson_type == 'quiz':
                    blob['quiz_data'] = tr_quiz(lesson.quiz_data)
                lesson.translations[target] = blob
                lesson.save(update_fields=['translations'])
        course.translation_status[target] = 'done'
    except TranslationError as exc:
        logger.error(
            'Translation of course %s into %s failed: %s', course_id, target, exc,
        )
        course.translation_status[target] = 'failed'
    course.save(update_fields=['translations', 'translation_status'])
