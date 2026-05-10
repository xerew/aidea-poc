from celery import shared_task


@shared_task
def compute_course_embeddings(course_id: int) -> None:
    from sentence_transformers import SentenceTransformer

    from hub.models import Course
    from hub.models.recommendations import CourseEmbedding

    course = Course.objects.get(pk=course_id)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    text = f"{course.title} {course.description}"
    embedding = model.encode(text).tolist()
    CourseEmbedding.objects.update_or_create(
        course=course,
        defaults={'embedding': embedding},
    )


@shared_task
def compute_user_recommendations(user_id: int) -> None:
    from pgvector.django import CosineDistance
    from sentence_transformers import SentenceTransformer
    from django.contrib.auth.models import User

    from hub.models.enrollment import Enrollment
    from hub.models.recommendations import CourseEmbedding, CourseRecommendation

    user = User.objects.select_related('profile').get(pk=user_id)
    profile = user.profile

    goals_str = ', '.join(profile.goals) if profile.goals else 'general'
    subject = profile.get_subject_area_display() if profile.subject_area else 'general'
    level_str = profile.get_teaching_level_display() if profile.teaching_level else 'unknown'
    profile_text = (
        f"{subject} teacher, {level_str}, "
        f"competency {profile.competency_score}/6, goals: {goals_str}"
    )

    model = SentenceTransformer('all-MiniLM-L6-v2')
    user_embedding = model.encode(profile_text).tolist()

    enrolled_ids = set(
        Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
    )

    score = profile.competency_score
    level_num = 0 if score <= 2 else (1 if score <= 4 else 2)
    level_name = ('beginner', 'intermediate', 'advanced')[level_num]
    course_level_nums = {'beginner': 0, 'intermediate': 1, 'advanced': 2}

    candidates = (
        CourseEmbedding.objects
        .select_related('course__pillar')
        .exclude(course_id__in=enrolled_ids)
        .filter(course__is_published=True)
        .annotate(distance=CosineDistance('embedding', user_embedding))
        .order_by('distance')[:15]
    )

    filtered = []
    for emb in candidates:
        course_level = course_level_nums.get(emb.course.level, 0)
        if course_level <= level_num + 1:
            filtered.append(emb)
        if len(filtered) >= 5:
            break

    CourseRecommendation.objects.filter(user=user).delete()

    subject_display = profile.subject_area.replace('_', ' ') if profile.subject_area else 'general'
    for emb in filtered:
        CourseRecommendation.objects.create(
            user=user,
            course=emb.course,
            score=max(0.0, 1.0 - float(emb.distance)),
            reason=f"Matches your {level_name} level and {subject_display} focus",
        )


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
