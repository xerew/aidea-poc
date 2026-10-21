from django.db import migrations
from django.db.models import F


def backfill_first_reviews(Submission):
    """Reviewed submissions take their current status as the first decision.
    A pending one that was already reviewed (reviewed_at kept on resubmission;
    reopen clears it) can only be "changes requested, then resubmitted"."""
    for status in ('approved', 'changes_requested'):
        Submission.objects.filter(status=status, first_review_status='').update(first_review_status=status)
    Submission.objects.filter(status='pending', first_review_status='', reviewed_at__isnull=False).update(
        first_review_status='changes_requested')


def forwards(apps, schema_editor):
    """Slow penalty stays on; idle decay follows the old single switch (which
    the admin turned off). Reviewed submissions take their current status as
    the first decision — their history was not kept."""
    Config = apps.get_model('hub', 'LearnerActivityConfig')
    for config in Config.objects.all():
        config.slow_penalty_enabled = True
        config.idle_decay_enabled = config.decay_enabled
        config.save(update_fields=['slow_penalty_enabled', 'idle_decay_enabled'])
    backfill_first_reviews(apps.get_model('hub', 'AssignmentSubmission'))
    # Past completions were already scored by the old rule: never re-score them.
    Enrollment = apps.get_model('hub', 'Enrollment')
    Enrollment.objects.filter(completed_at__isnull=False, competency_applied_at__isnull=True).update(
        competency_applied_at=F('completed_at'))


def backwards(apps, schema_editor):
    Config = apps.get_model('hub', 'LearnerActivityConfig')
    for config in Config.objects.all():
        config.decay_enabled = config.idle_decay_enabled
        config.save(update_fields=['decay_enabled'])


class Migration(migrations.Migration):
    dependencies = [('hub', '0068_competency_performance')]
    operations = [migrations.RunPython(forwards, backwards)]
