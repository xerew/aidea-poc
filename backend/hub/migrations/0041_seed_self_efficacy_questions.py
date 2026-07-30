from django.db import migrations

# The AI self-efficacy instrument: six dimensions, four statements each, all
# rated on the shared 5-point Likert scale. (dimension_name, slug, [statements])
DIMENSIONS = [
    ('AI Knowledge', 'ai-knowledge', [
        'I can distinguish whether a tool is AI-based or not.',
        'I can create content using AI.',
        'I can explain what artificial intelligence is.',
        'I know how to choose the right AI tool to complete a task effectively.',
    ]),
    ('AI Pedagogy', 'ai-pedagogy', [
        'I can choose an AI tool for my classroom that improves what I teach, how I teach, and what students learn.',
        'I can choose an AI tool that enhances the subject content of a lesson.',
        'I can teach lessons that appropriately combine subject content, AI tools, and teaching approaches.',
        'I can help other educators coordinate subject content, AI tools, and teaching approaches.',
    ]),
    ('AI Assessment', 'ai-assessment', [
        'I can use AI tools to support assessment for learning.',
        'I can design an assessment approach that improves student learning in an AI-based environment, such as learning with ChatGPT.',
        'I can assess student learning in an AI-based environment.',
        'I can choose an AI tool that supports student self-assessment.',
    ]),
    ('AI Ethics', 'ai-ethics', [
        'I can teach students about ethical issues related to AI.',
        'I can protect sensitive information from AI tools, including examinations, student grades, and personal data.',
        'I can maintain my health and well-being while using AI tools.',
        'I can teach students how to behave safely and responsibly when learning with AI tools.',
    ]),
    ('Human-Centred Education', 'human-centred-education', [
        'I can assess the benefits of an AI tool.',
        'I can assess the risks of an AI tool.',
        'I recognise that humans are responsible for identifying and addressing AI bias.',
        'I can explain how AI affects society.',
    ]),
    ('Professional Engagement', 'professional-engagement', [
        'I can use different websites and search strategies to find and select appropriate AI tools.',
        'I actively search for continuous professional-development activities outside my educational organisation.',
        'I actively share my AI teaching experiences with colleagues inside and outside my educational organisation.',
        'I am willing to help colleagues design learning activities that use AI.',
    ]),
]


def seed(apps, schema_editor):
    OnboardingDimension = apps.get_model('hub', 'OnboardingDimension')
    OnboardingQuestion = apps.get_model('hub', 'OnboardingQuestion')

    # Retire the old scored competency quiz (3 questions, now dimension-less).
    OnboardingQuestion.objects.filter(dimension__isnull=True).delete()

    if OnboardingDimension.objects.exists():
        return

    for dim_order, (name, slug, statements) in enumerate(DIMENSIONS, start=1):
        dimension = OnboardingDimension.objects.create(
            name=name, slug=slug, order=dim_order, is_active=True,
        )
        for q_order, text in enumerate(statements, start=1):
            OnboardingQuestion.objects.create(
                dimension=dimension, text=text, order=q_order, is_active=True,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0040_onboardingdimension_alter_onboardingquestion_options_and_more'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
