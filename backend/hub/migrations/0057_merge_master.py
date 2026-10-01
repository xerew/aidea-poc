# Joins the activities/resources chain (0051_resource … 0056) with master's
# chain (0051_userprofile_website, 0052_course_proposal_fields).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0052_course_proposal_fields'),
        ('hub', '0056_rename_lesson_to_activity'),
    ]

    operations = [
    ]
