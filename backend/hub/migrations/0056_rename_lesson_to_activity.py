from django.db import migrations


class Migration(migrations.Migration):
    """Rename the Lesson model to Activity (data-preserving). Endpoints and the
    legacy content columns are kept; only the model/table name changes. Must run
    AFTER the data migrations (0054/0055) so those still see the historical
    'Lesson' model."""

    dependencies = [('hub', '0055_migrate_progress_and_submissions')]

    operations = [
        migrations.RenameModel(old_name='Lesson', new_name='Activity'),
    ]
