"""Matching rules shared by the two personalisation engines: the rule-based
pathway (hub.pathway_gen) and the embedding recommendations (hub.tasks).

Pure functions over a profile and a course, so they are testable without
PostgreSQL/pgvector. Changes here change what the study's adaptive group
sees; record them in docs/personalization-changelog.md.
"""

# Bump when the ranking rules change (see docs/personalization-changelog.md).
ALGORITHM_VERSION = '2026-10-01'

# A teacher's level (onboarding/profile) → course educational levels it fits.
# Higher-ed, vocational and adult-ed teachers have no counterpart in the course
# form, so they are neither boosted nor penalised.
_LEVEL_FIT = {
    'primary': {'primary'},
    'secondary': {'lower_secondary', 'upper_secondary'},
}

# Profile school role → course target-audience values it fits.
_AUDIENCE_FIT = {
    'teacher': {'teachers'},
    'school_leader': {'school_leaders'},
    'both': {'teachers', 'school_leaders'},
}

MATCH, NEUTRAL, MISMATCH = 1, 0, -1

# Recommendations: multiplicative nudges on cosine similarity.
LEVEL_BOOST, LEVEL_PENALTY = 1.15, 0.85
AUDIENCE_BOOST, AUDIENCE_PENALTY = 1.15, 0.7

# Pathway: additive score terms (same scale as pathway_gen's W_* weights).
W_LEVEL, W_LEVEL_MISMATCH = 1.0, -1.0
W_AUDIENCE, W_AUDIENCE_MISMATCH = 1.0, -1.5


def course_pillar_slugs(course):
    """Primary + additional Academy Pillars (additional_pillars prefetched)."""
    return {course.pillar.slug, *(p.slug for p in course.additional_pillars.all())}


def level_match(profile, course):
    """Does the course's educational level fit the teacher's level?"""
    levels = set(course.educational_levels or [])
    if not levels:
        return NEUTRAL
    if 'cross_level' in levels:
        return MATCH
    fit = _LEVEL_FIT.get(profile.teaching_level)
    if not fit:
        return NEUTRAL
    return MATCH if levels & fit else MISMATCH


def audience_match(profile, course):
    """Is the course aimed at the user's school role?"""
    audience = set(course.target_audience or [])
    fit = _AUDIENCE_FIT.get(profile.school_role)
    if not audience or not fit:
        return NEUTRAL
    return MATCH if audience & fit else MISMATCH


def recommendation_factor(profile, course):
    """Multiplier for a candidate's similarity from level and audience fit."""
    factor = 1.0
    factor *= {MATCH: LEVEL_BOOST, MISMATCH: LEVEL_PENALTY}.get(level_match(profile, course), 1.0)
    factor *= {MATCH: AUDIENCE_BOOST, MISMATCH: AUDIENCE_PENALTY}.get(audience_match(profile, course), 1.0)
    return factor


def pathway_bonus(profile, course):
    """Additive pathway score from level and audience fit."""
    bonus = {MATCH: W_LEVEL, MISMATCH: W_LEVEL_MISMATCH}.get(level_match(profile, course), 0.0)
    bonus += {MATCH: W_AUDIENCE, MISMATCH: W_AUDIENCE_MISMATCH}.get(audience_match(profile, course), 0.0)
    return bonus


def course_embedding_text(course):
    """What a course 'is about' for the sentence embedding: title, description,
    learning outcomes, prior knowledge, cross-axis relevance and subjects."""
    parts = [course.title, course.description]
    if course.learning_outcomes:
        parts.append('Learning outcomes: ' + '; '.join(course.learning_outcomes))
    if course.prior_knowledge:
        parts.append(f'Prior knowledge: {course.prior_knowledge}')
    if course.cross_axis_relevance:
        parts.append(course.cross_axis_relevance)
    subjects = ', '.join(course.subjects.values_list('name', flat=True))
    if subjects:
        parts.append(f'Subjects: {subjects}')
    return '. '.join(p.strip().rstrip('.') for p in parts if p and p.strip())


def profile_text(profile):
    """The user's side of the embedding comparison."""
    goals = ', '.join(profile.goals) if profile.goals else 'general'
    subject = profile.subject.name if profile.subject else 'general'
    level = profile.get_teaching_level_display() if profile.teaching_level else 'unknown level'
    role = {
        'school_leader': 'school leader',
        'both': 'teacher and school leader',
    }.get(profile.school_role, 'teacher')
    return f'{subject} {role}, {level}, competency {profile.competency_score}/6, goals: {goals}'
