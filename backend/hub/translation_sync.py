"""Keep translations in sync when the source course content changes.

When a course/module/lesson's translatable content is edited, only the
changed unit is re-translated into each already-translated language; the rest
of the translation is left intact. The course-level status drops back to
'pending' → 'done', so any human-reviewed sign-off must be re-done.
"""

# Languages whose translation should be refreshed when the source changes: any
# that have been translated (or are mid-translation). Not 'failed'/absent.
_SYNCABLE = {'done', 'reviewed', 'pending'}


def _target_langs(course):
    return [lang for lang, st in (course.translation_status or {}).items() if st in _SYNCABLE]


def _mark_pending(course, langs):
    # Re-read under a row lock and merge, so this doesn't clobber a still-running
    # translation task writing the same status dict (see hub.tasks._merge_json).
    from django.db import transaction

    from hub.models import Course
    with transaction.atomic():
        fresh = Course.objects.select_for_update().get(pk=course.pk)
        status = dict(fresh.translation_status or {})
        for lang in langs:
            status[lang] = 'pending'
        fresh.translation_status = status
        fresh.save(update_fields=['translation_status'])
    course.translation_status = status


def resync_course_meta(course):
    """Course title/description/outcomes changed."""
    langs = _target_langs(course)
    if not langs:
        return
    _mark_pending(course, langs)
    from hub.tasks import translate_course_meta
    for lang in langs:
        translate_course_meta.delay(course.id, lang)


def resync_module(module):
    """One module's title/description changed (or it was just added)."""
    course = module.course
    langs = _target_langs(course)
    if not langs:
        return
    _mark_pending(course, langs)
    from hub.tasks import translate_module_meta
    for lang in langs:
        translate_module_meta.delay(module.id, lang)


def resync_lesson(lesson):
    """One lesson's content changed (or it was just added)."""
    course = lesson.module.course
    langs = _target_langs(course)
    if not langs:
        return
    _mark_pending(course, langs)
    from hub.tasks import translate_lesson_meta
    for lang in langs:
        translate_lesson_meta.delay(lesson.id, lang)
