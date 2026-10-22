"""Per-item translation flags and the review record — spec
docs/superpowers/specs/2026-10-21-targeted-retranslation-design.md.

Course, Module, Activity and Resource each carry `translation_flags`:
{lang: {"edited": bool, "changed": bool, "replaced_edit": bool}}.
`edited` = a person corrected this item's translation; `changed` = it was
machine-translated again after the language was last marked reviewed;
`replaced_edit` = that re-translation replaced a person's correction."""
from django.db import transaction
from django.utils import timezone


def _update(model_cls, pk, lang, change):
    with transaction.atomic():
        obj = model_cls.objects.select_for_update().get(pk=pk)
        all_flags = dict(obj.translation_flags or {})
        all_flags[lang] = change(dict(all_flags.get(lang, {})))
        obj.translation_flags = all_flags
        obj.save(update_fields=['translation_flags'])
    return all_flags


def mark_edited(obj, lang):
    obj.translation_flags = _update(type(obj), obj.pk, lang, lambda f: {**f, 'edited': True})


def note_machine_translated(obj, course_id, lang):
    """`obj` was just machine-translated into `lang`."""
    from hub.models import Course
    record = Course.objects.filter(pk=course_id).values_list('translation_reviewed_at', flat=True).first() or {}
    reviewed = lang in record

    def change(f):
        if reviewed:
            f['changed'] = True
            if f.get('edited'):
                f['replaced_edit'] = True
        f['edited'] = False
        return f
    obj.translation_flags = _update(type(obj), obj.pk, lang, change)


def course_items(course):
    from hub.models import Activity, Module, Resource
    yield 'course', course
    for module in Module.objects.filter(course=course).order_by('order'):
        yield 'module', module
    for activity in Activity.objects.filter(module__course=course).order_by('module__order', 'order'):
        yield 'activity', activity
    for resource in (Resource.objects.filter(activity__module__course=course)
                     .select_related('activity').order_by('activity__module__order', 'activity__order', 'order')):
        yield 'resource', resource


def _clear(course, lang, keys):
    for _, obj in course_items(course):
        current = (obj.translation_flags or {}).get(lang) or {}
        if any(k in current for k in keys):
            _update(type(obj), obj.pk, lang, lambda f: {k: v for k, v in f.items() if k not in keys})


def set_reviewed(course, lang, reviewed):
    """Mark (or unmark) `lang` reviewed: record or drop the review, clear the re-check list."""
    from hub.models import Course
    with transaction.atomic():
        fresh = Course.objects.select_for_update().get(pk=course.pk)
        record = dict(fresh.translation_reviewed_at or {})
        status = dict(fresh.translation_status or {})
        if reviewed:
            record[lang] = timezone.now().isoformat()
            status[lang] = 'reviewed'
        else:
            record.pop(lang, None)
            if status.get(lang) == 'reviewed':
                status[lang] = 'done'
        fresh.translation_reviewed_at, fresh.translation_status = record, status
        fresh.save(update_fields=['translation_reviewed_at', 'translation_status'])
    course.translation_reviewed_at, course.translation_status = record, status
    _clear(course, lang, ('changed', 'replaced_edit'))


def forget_review(course, lang):
    """Whole-course re-translation: the review and every flag for `lang` go."""
    from hub.models import Course
    with transaction.atomic():
        fresh = Course.objects.select_for_update().get(pk=course.pk)
        record = dict(fresh.translation_reviewed_at or {})
        record.pop(lang, None)
        fresh.translation_reviewed_at = record
        fresh.save(update_fields=['translation_reviewed_at'])
    course.translation_reviewed_at = record
    _clear(course, lang, ('changed', 'replaced_edit', 'edited'))


def _ids(kind, obj):
    if kind == 'course':
        return None, None
    if kind == 'module':
        return obj.id, None
    if kind == 'activity':
        return obj.module_id, obj.id
    return obj.activity.module_id, obj.activity_id


def recheck_items(course, lang):
    items = []
    for kind, obj in course_items(course):
        f = (obj.translation_flags or {}).get(lang) or {}
        if f.get('changed'):
            module_id, activity_id = _ids(kind, obj)
            title = obj.title or (obj.get_type_display() if kind == 'resource' else '')
            items.append({'kind': kind, 'id': obj.id, 'title': title, 'module_id': module_id,
                          'activity_id': activity_id, 'replaced_edit': bool(f.get('replaced_edit'))})
    return items


def count_edited(course, lang, scope, module_id=None, activity_id=None):
    def in_scope(kind, obj):
        if scope == 'course':
            return True
        if scope == 'details':
            return kind == 'course'
        item_module, item_activity = _ids(kind, obj)
        if scope == 'module':
            return item_module == module_id
        return scope == 'activity' and item_activity == activity_id
    return sum(1 for kind, obj in course_items(course)
               if in_scope(kind, obj) and ((obj.translation_flags or {}).get(lang) or {}).get('edited'))
