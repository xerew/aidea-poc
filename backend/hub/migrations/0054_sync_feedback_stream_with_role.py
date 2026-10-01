"""One-off: put every feedback item in the stream that matches its author's
current role. Feedback was stamped with the role at submission time, so users
promoted to AIDEA partner kept their earlier feedback under "User feedback".
From now on hub.signals keeps them in sync when a role changes."""

from django.db import migrations


def sync_streams(apps, schema_editor):
    Feedback = apps.get_model('hub', 'Feedback')
    partner_ids = apps.get_model('hub', 'UserProfile').objects.filter(
        user_type='aidea_partner',
    ).values_list('user_id', flat=True)
    Feedback.objects.filter(user_id__in=partner_ids).exclude(stream='partner').update(stream='partner')
    Feedback.objects.exclude(user_id__in=partner_ids).exclude(stream='user').update(stream='user')


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0053_userprofile_school_role'),
    ]

    operations = [
        migrations.RunPython(sync_streams, migrations.RunPython.noop),
    ]
