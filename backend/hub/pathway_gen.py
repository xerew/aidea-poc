"""Personalised learning-pathway generation.

Deterministic and embedding-free (works on any database, unlike the pgvector
recommendation engine), so a teacher's pathway responds to their competency,
preferred pillars, subject and goals — and can be recomputed synchronously
whenever the profile changes.
"""

PATHWAY_SIZE = 6

# Goals steer the pathway toward a pillar's courses.
GOAL_TO_PILLAR = {
    'save_time':        'teach-with-ai',
    'stay_current':     'teach-with-ai',
    'prepare_students': 'teach-for-ai',
    'teach_about_ai':   'teach-about-ai',
    'address_ethics':   'teach-about-ai',
}

_LEVEL_NUM = {'beginner': 0, 'intermediate': 1, 'advanced': 2}

# Scoring weights.
W_PILLAR  = 3.0   # course pillar is one the teacher prefers
W_GOAL    = 1.5   # course pillar is implied by a chosen goal
W_SUBJECT = 1.0   # course targets the teacher's subject (or General/All)


def competency_band(score):
    return 0 if score <= 2 else (1 if score <= 4 else 2)


def generate_pathway(user, limit=PATHWAY_SIZE):
    """Return an ordered list of course ids tailored to the teacher."""
    from hub.models import Course

    profile = user.profile
    band = competency_band(profile.competency_score)
    preferred = set(profile.preferred_pillars or [])
    goal_pillars = {
        GOAL_TO_PILLAR[g] for g in (profile.goals or []) if g in GOAL_TO_PILLAR
    }
    subject_id = profile.subject_id

    courses = (
        Course.objects
        .filter(is_published=True)
        .select_related('pillar')
        .prefetch_related('subjects')
    )

    scored = []
    for course in courses:
        clevel = _LEVEL_NUM.get(course.level, 0)
        if clevel > band + 1:
            continue  # too far above the teacher's competency

        score = 3.0 - abs(clevel - band)  # closeness to the teacher's band
        if course.pillar.slug in preferred:
            score += W_PILLAR
        if course.pillar.slug in goal_pillars:
            score += W_GOAL
        if subject_id:
            subject_slugs = {s.slug for s in course.subjects.all()}
            subject_ids = {s.id for s in course.subjects.all()}
            if subject_id in subject_ids or 'general' in subject_slugs:
                score += W_SUBJECT

        # Tie-break deterministically on pillar order then id.
        scored.append((-score, course.pillar.order, course.id))

    scored.sort()
    return [course_id for _, _, course_id in scored[:limit]]
