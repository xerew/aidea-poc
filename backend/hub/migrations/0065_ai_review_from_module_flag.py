from django.db import migrations


def forwards(apps, schema_editor):
    """Assignments in modules that had the old LLM-review switch on start with
    AI review on (they still need an approved rubric before anything runs)."""
    Resource = apps.get_model('hub', 'Resource')
    Config = apps.get_model('hub', 'AssignmentReviewConfig')
    for resource in Resource.objects.filter(type='assignment', activity__module__llm_review_enabled=True):
        Config.objects.get_or_create(resource=resource, defaults={'enabled': True})


class Migration(migrations.Migration):
    dependencies = [('hub', '0064_ai_review')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
