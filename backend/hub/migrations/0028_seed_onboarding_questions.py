from django.db import migrations

# The three competency knowledge-check questions, migrated from the previously
# hard-coded onboarding wizard. (question_text, order, [(option_text, score, order)])
QUESTIONS = [
    (
        "You ask an AI to summarise a student's essay. It gives a confident but "
        "factually wrong summary. What do you do?",
        1,
        [
            ("Trust the AI — it's usually accurate", 0, 1),
            ("Check it yourself and correct it", 2, 2),
            ("Use a different AI tool instead", 1, 3),
            ("I wouldn't use AI for this task", 0, 4),
        ],
    ),
    (
        'What does it mean when an AI model "hallucinates"?',
        2,
        [
            ("The AI crashes or freezes", 0, 1),
            ("The AI generates false information that sounds plausible", 2, 2),
            ("The AI gives creative or unexpected responses", 1, 3),
            ("I'm not sure", 0, 4),
        ],
    ),
    (
        "Which of these is the best AI prompt for generating a lesson plan?",
        3,
        [
            ('"Write a lesson plan"', 0, 1),
            ('"Write a 45-minute lesson plan for 14-year-olds about fractions, include 3 activities"', 2, 2),
            ('"Help me teach math"', 0, 3),
            ('"I need a lesson plan about math, make it good"', 1, 4),
        ],
    ),
]


def seed(apps, schema_editor):
    OnboardingQuestion = apps.get_model('hub', 'OnboardingQuestion')
    OnboardingOption = apps.get_model('hub', 'OnboardingOption')
    if OnboardingQuestion.objects.exists():
        return
    for text, order, options in QUESTIONS:
        question = OnboardingQuestion.objects.create(text=text, order=order, is_active=True)
        for opt_text, score, opt_order in options:
            OnboardingOption.objects.create(
                question=question, text=opt_text, score=score, order=opt_order,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0027_onboardingquestion_onboardingoption'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
