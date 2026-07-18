from hub.models import PreferenceOption, PreferenceQuestion

_QUESTIONS = [
    {
        'order': 1,
        'text': 'When you learn something new, what helps you most?',
        'options': [
            ('Watching someone demonstrate it', 'video'),
            ('Reading a clear explanation', 'text'),
            ('Studying a diagram or infographic', 'visual'),
            ('Trying it hands-on right away', 'interactive'),
        ],
    },
    {
        'order': 2,
        'text': 'Think of the best training you ever attended. What made it work for you?',
        'options': [
            ('Engaging video lectures', 'video'),
            ('Well-written materials I could re-read', 'text'),
            ('Strong slides, charts and visuals', 'visual'),
            ('Exercises and group activities', 'interactive'),
        ],
    },
    {
        'order': 3,
        'text': 'You have to master a new classroom tool by Friday. What is your first move?',
        'options': [
            ('Find a video walkthrough', 'video'),
            ('Read the manual or a how-to guide', 'text'),
            ('Look for an annotated screenshot tour', 'visual'),
            ('Open it and click around', 'interactive'),
        ],
    },
    {
        'order': 4,
        'text': 'Which kind of online content do you actually finish?',
        'options': [
            ('Short video series', 'video'),
            ('Long-form articles', 'text'),
            ('Visual explainers', 'visual'),
            ('Interactive quizzes and simulations', 'interactive'),
        ],
    },
]


def seed_preference_quiz():
    for data in _QUESTIONS:
        question, _ = PreferenceQuestion.objects.update_or_create(
            order=data['order'],
            defaults={'text': data['text'], 'is_active': True},
        )
        question.options.all().delete()
        for opt_order, (text, maps_to) in enumerate(data['options'], start=1):
            PreferenceOption.objects.create(
                question=question, text=text, maps_to=maps_to, order=opt_order,
            )
