from django.db import migrations


def migrate_lessons_to_resources(apps, schema_editor):
    """Create Resource rows from each Lesson's content / media_items / quiz_data /
    assignment. One lesson → one activity (this same row) with an ordered list of
    resources. Legacy columns are kept (rollback window)."""
    Lesson = apps.get_model('hub', 'Lesson')
    Resource = apps.get_model('hub', 'Resource')

    for lesson in Lesson.objects.all().iterator():
        trans = lesson.translations or {}
        order = 0

        def _pick(field):
            # per-language {lang: {field: value}} from the lesson's translations
            return {
                lang: {field: (blob or {}).get(field)}
                for lang, blob in trans.items()
                if (blob or {}).get(field)
            }

        if lesson.lesson_type == 'assignment':
            order += 1
            Resource.objects.create(
                activity_id=lesson.id, type='assignment', order=order,
                is_required=lesson.is_required,
                instructions=lesson.content or lesson.description or '',
                translations={
                    lang: {'instructions': (blob or {}).get('content')}
                    for lang, blob in trans.items() if (blob or {}).get('content')
                },
            )
        elif (lesson.content or '').strip():
            order += 1
            Resource.objects.create(
                activity_id=lesson.id, type='text', order=order,
                is_required=lesson.is_required, content=lesson.content,
                translations=_pick('content'),
            )

        media = lesson.media_items if isinstance(lesson.media_items, list) else []
        for mi in media:
            if not isinstance(mi, dict):
                continue
            mtype = mi.get('type')
            if mtype in ('image', 'video', 'pdf') and mi.get('url'):
                order += 1
                Resource.objects.create(
                    activity_id=lesson.id, type=mtype, order=order,
                    is_required=lesson.is_required,
                    url=mi.get('url', ''), caption=str(mi.get('caption', '') or ''),
                )

        if lesson.lesson_type == 'quiz':
            order += 1
            Resource.objects.create(
                activity_id=lesson.id, type='quiz', order=order,
                is_required=lesson.is_required, quiz_data=lesson.quiz_data or [],
                translations=_pick('quiz_data'),
            )

        # An empty lesson still needs one resource so the activity isn't blank.
        if order == 0:
            Resource.objects.create(
                activity_id=lesson.id, type='text', order=1, is_required=lesson.is_required,
            )


def clear_resources(apps, schema_editor):
    apps.get_model('hub', 'Resource').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [('hub', '0053_assignmentsubmission_resource')]
    operations = [migrations.RunPython(migrate_lessons_to_resources, clear_resources)]
