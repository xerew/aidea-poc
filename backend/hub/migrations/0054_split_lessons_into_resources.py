from django.db import migrations

from hub.content_migration_logic import build_resources_for_lesson


def migrate_lessons_to_resources(apps, schema_editor):
    """Create Resource rows from each Lesson's content / media_items / quiz_data /
    assignment. One lesson → one activity (this same row) with an ordered list of
    resources. Legacy columns are kept (rollback window)."""
    Lesson = apps.get_model('hub', 'Lesson')
    Resource = apps.get_model('hub', 'Resource')
    for lesson in Lesson.objects.all().iterator():
        build_resources_for_lesson(lesson, Resource)


def clear_resources(apps, schema_editor):
    apps.get_model('hub', 'Resource').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [('hub', '0053_assignmentsubmission_resource')]
    operations = [migrations.RunPython(migrate_lessons_to_resources, clear_resources)]
