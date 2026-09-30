from django.db import migrations

from hub.content_migration_logic import migrate_progress_row, repoint_submission


def migrate_progress_and_submissions(apps, schema_editor):
    """Map LessonProgress → ResourceProgress (one per resource of the migrated
    activity) and repoint each AssignmentSubmission to the activity's assignment
    resource. Legacy rows are kept (rollback window)."""
    LessonProgress = apps.get_model('hub', 'LessonProgress')
    ResourceProgress = apps.get_model('hub', 'ResourceProgress')
    Resource = apps.get_model('hub', 'Resource')
    AssignmentSubmission = apps.get_model('hub', 'AssignmentSubmission')

    for lp in LessonProgress.objects.all().iterator():
        migrate_progress_row(lp, Resource, ResourceProgress)

    for sub in AssignmentSubmission.objects.filter(resource__isnull=True).iterator():
        repoint_submission(sub, Resource)


def noop_reverse(apps, schema_editor):
    apps.get_model('hub', 'ResourceProgress').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [('hub', '0054_split_lessons_into_resources')]
    operations = [migrations.RunPython(migrate_progress_and_submissions, noop_reverse)]
