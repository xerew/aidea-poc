from hub.models.content import Course, LearningPillar
from hub.models.pathway import LearningPath, LearningPathCourse

_PATH_CONFIGS = [
    {
        'slug':            'beginner-foundations',
        'name':            'Beginner Foundations',
        'description':     'Start your AI journey with practical tools for the classroom.',
        'competency_min':  0,
        'competency_max':  2,
        'pillar_slug':     'teach-with-ai',
    },
    {
        'slug':            'intermediate-growth',
        'name':            'Intermediate Growth',
        'description':     'Deepen your understanding of AI and expand your teaching toolkit.',
        'competency_min':  3,
        'competency_max':  4,
        'pillar_slug':     'teach-about-ai',
    },
    {
        'slug':            'advanced-integration',
        'name':            'Advanced Integration',
        'description':     'Master AI integration and prepare your students for an AI-driven future.',
        'competency_min':  5,
        'competency_max':  6,
        'pillar_slug':     'teach-for-ai',
    },
]


def seed_pathways():
    for config in _PATH_CONFIGS:
        pillar_slug = config.pop('pillar_slug')
        path, _ = LearningPath.objects.update_or_create(
            slug=config['slug'],
            defaults={k: v for k, v in config.items() if k != 'slug'},
        )
        config['pillar_slug'] = pillar_slug  # restore for idempotency

        try:
            pillar = LearningPillar.objects.get(slug=pillar_slug)
        except LearningPillar.DoesNotExist:
            continue

        courses = list(
            Course.objects.filter(pillar=pillar, is_published=True).order_by('title')[:5]
        )
        LearningPathCourse.objects.filter(path=path).delete()
        for i, course in enumerate(courses):
            LearningPathCourse.objects.create(path=path, course=course, order=i + 1)
