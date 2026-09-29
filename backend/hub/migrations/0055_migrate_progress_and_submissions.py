from django.db import migrations


def migrate_progress_and_submissions(apps, schema_editor):
    """Map LessonProgress → ResourceProgress (one per resource of the migrated
    activity) and repoint each AssignmentSubmission to the activity's assignment
    resource. Legacy rows are kept (rollback window)."""
    LessonProgress = apps.get_model('hub', 'LessonProgress')
    ResourceProgress = apps.get_model('hub', 'ResourceProgress')
    Resource = apps.get_model('hub', 'Resource')
    AssignmentSubmission = apps.get_model('hub', 'AssignmentSubmission')

    for lp in LessonProgress.objects.all().iterator():
        resources = list(Resource.objects.filter(activity_id=lp.lesson_id))
        for r in resources:
            ResourceProgress.objects.get_or_create(
                user_id=lp.user_id, resource_id=r.id,
                defaults={
                    'completed_at': lp.completed_at,
                    'time_spent_seconds': lp.time_spent_seconds,
                    'quiz_score': lp.quiz_score if r.type == 'quiz' else None,
                    'quiz_answers': lp.quiz_answers if r.type == 'quiz' else [],
                    'engagement_data': lp.engagement_data or {},
                },
            )

    for sub in AssignmentSubmission.objects.filter(resource__isnull=True).iterator():
        res = Resource.objects.filter(activity_id=sub.lesson_id, type='assignment').first()
        if res:
            sub.resource_id = res.id
            sub.save(update_fields=['resource'])


def noop_reverse(apps, schema_editor):
    apps.get_model('hub', 'ResourceProgress').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [('hub', '0054_split_lessons_into_resources')]
    operations = [migrations.RunPython(migrate_progress_and_submissions, noop_reverse)]
