"""Pure mapping logic for the lessons→resources data migration, shared by the
migrations (which pass historical models) and the tests (which pass current
models). Only uses field access + the passed-in model classes, so it works with
either. Referenced by hub/migrations/0054 and 0055."""


def build_resources_for_lesson(lesson, Resource):
    """Create the ordered Resource rows for one lesson/activity."""
    trans = lesson.translations or {}
    order = 0

    def _pick(field):
        return {
            lang: {field: (blob or {}).get(field)}
            for lang, blob in trans.items() if (blob or {}).get(field)
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

    if order == 0:
        Resource.objects.create(
            activity_id=lesson.id, type='text', order=1, is_required=lesson.is_required,
        )


def migrate_progress_row(lp, Resource, ResourceProgress):
    """Create ResourceProgress rows for every resource of the migrated activity."""
    for r in Resource.objects.filter(activity_id=lp.lesson_id):
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


def repoint_submission(sub, Resource):
    """Point an AssignmentSubmission at the activity's assignment resource."""
    res = Resource.objects.filter(activity_id=sub.lesson_id, type='assignment').first()
    if res:
        sub.resource_id = res.id
        sub.save(update_fields=['resource'])
