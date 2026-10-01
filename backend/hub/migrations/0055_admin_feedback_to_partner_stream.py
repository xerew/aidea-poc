"""One-off: admins count as AIDEA partners for feedback, so their existing
feedback moves to the partner stream. New feedback and role changes follow
Feedback.stream_for_role (via hub.signals)."""

from django.db import migrations

PARTNER_ROLES = ('aidea_partner', 'admin')


def sync_streams(apps, schema_editor):
    Feedback = apps.get_model('hub', 'Feedback')
    partner_ids = apps.get_model('hub', 'UserProfile').objects.filter(
        user_type__in=PARTNER_ROLES,
    ).values_list('user_id', flat=True)
    Feedback.objects.filter(user_id__in=partner_ids).exclude(stream='partner').update(stream='partner')
    Feedback.objects.exclude(user_id__in=partner_ids).exclude(stream='user').update(stream='user')


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0054_sync_feedback_stream_with_role'),
    ]

    operations = [
        migrations.RunPython(sync_streams, migrations.RunPython.noop),
    ]
