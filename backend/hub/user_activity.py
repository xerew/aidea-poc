"""Everything one person does on the platform, for the admin activity page
(spec docs/superpowers/specs/2026-11-21-user-activity-page-design.md).

The feed merges many tables. Each source is a queryset whose rows carry an
`at` time plus a function that turns rows into feed items:
    {'at', 'category', 'kind', 'params', 'text', 'course': {id, title} | None}
`text` is plain English (the Excel export); the page renders `kind` + `params`
in the viewer's language."""
from datetime import timedelta

from django.db.models import Exists, F, Min, OuterRef, Q, Sum

FEED_PAGE = 50
CATEGORIES = ('learning', 'authoring', 'reviews', 'account')

# CourseEditHistory rows whose single key names the change; anything else
# (field diffs from the course form) is a plain course edit.
EDIT_TEXT = {
    'course_created': 'Created the course',
    'course_edited': 'Edited the course details of',
    'course_published': 'Published the course',
    'course_unpublished': 'Unpublished the course',
    'course_imported': 'Imported the course',
    'module_added': 'Added a module to',
    'module_edited': 'Edited a module of',
    'module_deleted': 'Deleted a module of',
    'modules_reordered': 'Reordered the modules of',
    'module_imported': 'Imported a module into',
    'lesson_added': 'Added an activity to',
    'lesson_edited': 'Edited an activity of',
    'lesson_deleted': 'Deleted an activity of',
    'lessons_reordered': 'Reordered the activities of',
    'resource_added': 'Added a resource to',
    'presentation_uploaded': 'Uploaded a presentation to',
}

# Learning events worth a feed line; play/pause/seek, PDF/image opens and single
# answers stay in the per-course timeline.
EVENT_KINDS = {
    'video_ended': 'video_finished',
    'pdf_download': 'file_downloaded',
    'presentation_download': 'file_downloaded',
    'h5p_attempt': 'h5p_attempt',
    'h5p_error': 'h5p_error',
}

ACCOUNT_ACTIONS = ('role_changed', 'pathways_rebuilt')
AUTHORING_ACTIONS = ('translation_requested', 'resource_edited', 'resource_deleted', 'course_deleted',
                     'collaborator_added', 'collaborator_removed', 'ai_review_saved')


def _course(course):
    return {'id': course.id, 'title': course.title} if course is not None else None


def _item(at, category, kind, text, course_obj=None, **params):
    return {'at': at, 'category': category, 'kind': kind, 'params': params, 'text': text,
            'course': _course(course_obj)}


def _name(user):
    return user.get_full_name() or user.username


class _Source:
    def __init__(self, category, queryset, build):
        self.category = category
        self.queryset = queryset   # user -> QuerySet with an `at` field or annotation
        self.build = build         # rows -> list of items


# ── Learning ──────────────────────────────────────────────────────────────────

def _visits_qs(user):
    from hub.models.tracking import ResourceVisit
    return (ResourceVisit.objects.filter(user=user)
            .values('page_key', 'activity_id', 'course_id')
            .annotate(at=Min('started_at'), active=Sum('active_seconds')))


def _visits_build(rows):
    from hub.models import Activity, Course
    rows = list(rows)
    activities = Activity.objects.in_bulk({r['activity_id'] for r in rows})
    courses = Course.objects.in_bulk({r['course_id'] for r in rows})
    items = []
    for r in rows:
        activity, course = activities.get(r['activity_id']), courses.get(r['course_id'])
        title = activity.title if activity else ''
        minutes = round((r['active'] or 0) / 60)
        items.append(_item(r['at'], 'learning', 'studied',
                           f'Studied "{title}" in {course.title if course else ""} — {minutes} min',
                           course, activity=title, minutes=minutes))
    return items


def _events_qs(user):
    from hub.models.tracking import LearningEvent
    return (LearningEvent.objects.filter(user=user, event_type__in=EVENT_KINDS)
            .annotate(at=F('occurred_at')).select_related('course', 'resource'))


def _events_build(rows):
    items = []
    for e in rows:
        kind, resource = EVENT_KINDS[e.event_type], e.resource.title or e.resource.type
        if kind == 'file_downloaded':
            file_type = 'presentation' if e.event_type == 'presentation_download' else 'pdf'
            items.append(_item(e.at, 'learning', kind, f'Downloaded the {file_type} "{resource}" in {e.course.title}',
                               e.course, resource=resource, file_type=file_type))
        elif kind == 'h5p_attempt':
            score = {k: e.data[src] for k, src in (('score', 'raw'), ('max_score', 'max')) if src in (e.data or {})}
            result = f' ({score["score"]}/{score["max_score"]})' if len(score) == 2 else ''
            items.append(_item(e.at, 'learning', kind, f'Finished the interactive "{resource}"{result} in {e.course.title}',
                               e.course, resource=resource, **score))
        elif kind == 'h5p_error':
            items.append(_item(e.at, 'learning', kind, f'The interactive "{resource}" failed to load in {e.course.title}',
                               e.course, resource=resource))
        else:
            items.append(_item(e.at, 'learning', kind, f'Watched the video "{resource}" to the end in {e.course.title}',
                               e.course, resource=resource))
    return items


def _enrolled_qs(user):
    from hub.models import Enrollment
    return Enrollment.objects.filter(user=user).annotate(at=F('enrolled_at')).select_related('course')


def _enrolled_build(rows):
    return [_item(e.at, 'learning', 'enrolled', f'Enrolled in {e.course.title}', e.course) for e in rows]


def _completed_qs(user):
    from hub.models import Enrollment
    return (Enrollment.objects.filter(user=user, completed_at__isnull=False)
            .annotate(at=F('completed_at')).select_related('course'))


def _completed_build(rows):
    return [_item(e.at, 'learning', 'completed', f'Completed {e.course.title}', e.course) for e in rows]


def _submitted_qs(user):
    from hub.models import AssignmentSubmission
    return (AssignmentSubmission.objects.filter(user=user).annotate(at=F('submitted_at'))
            .select_related('lesson__module__course'))


def _submitted_build(rows):
    return [_item(s.at, 'learning', 'assignment_submitted',
                  f'Submitted the assignment in "{s.lesson.title}" ({s.lesson.module.course.title})',
                  s.lesson.module.course, activity=s.lesson.title) for s in rows]


def _competency_qs(user):
    from hub.models import CompetencyChange
    return CompetencyChange.objects.filter(user=user).annotate(at=F('created_at')).select_related('course')


def _competency_build(rows):
    return [_item(c.at, 'learning', 'competency_changed',
                  f'AI competency changed from {c.old_score} to {c.new_score}'
                  + (f' ({c.course.title})' if c.course else ''),
                  c.course, old=c.old_score, new=c.new_score) for c in rows]


def _views_qs(user):
    from hub.models.recommendations import CourseView
    return CourseView.objects.filter(user=user).annotate(at=F('created_at')).select_related('course')


def _views_build(rows):
    return [_item(v.at, 'learning', 'course_viewed', f'Opened the course page of {v.course.title}', v.course)
            for v in rows]


# ── Reviews ───────────────────────────────────────────────────────────────────

def _reviews_qs(user):
    from hub.models import AssignmentSubmission
    return (AssignmentSubmission.objects.filter(reviewed_by=user, reviewed_at__isnull=False)
            .annotate(at=F('reviewed_at')).select_related('user', 'lesson__module__course'))


def _reviews_build(rows):
    items = []
    for s in rows:
        course, learner = s.lesson.module.course, _name(s.user)
        outcome = 'approved' if s.status == 'approved' else 'changes_requested'
        verb = 'approved' if outcome == 'approved' else 'requested changes on'
        items.append(_item(s.at, 'reviews', 'assignment_reviewed',
                           f'Reviewed and {verb} the assignment by {learner} in {course.title}',
                           course, learner=learner, outcome=outcome))
    return items


# ── Authoring ─────────────────────────────────────────────────────────────────

def _edits_qs(user):
    from hub.models import CourseEditHistory
    return CourseEditHistory.objects.filter(editor=user).annotate(at=F('edited_at')).select_related('course')


def _edit_key(changes):
    keys = list(changes or {})
    return keys[0] if len(keys) == 1 and keys[0] in EDIT_TEXT else 'course_edited'


def _edits_build(rows):
    items = []
    for e in rows:
        key = _edit_key(e.changes)
        items.append(_item(e.at, 'authoring', f'edit_{key}', f'{EDIT_TEXT[key]} {e.course.title}', e.course))
    return items


def _pathway_changes_qs(user):
    """Publish/unpublish rows of the pathway list, minus those the course's own
    edit history already shows (same user and course, within 5 seconds)."""
    from hub.models import CourseEditHistory, PathwayCourseChange
    window = timedelta(seconds=5)
    duplicate = CourseEditHistory.objects.filter(
        editor=user, course=OuterRef('course'),
        edited_at__gte=OuterRef('changed_at') - window, edited_at__lte=OuterRef('changed_at') + window,
    ).filter(Q(changes__has_key='course_published') | Q(changes__has_key='course_unpublished'))
    return (PathwayCourseChange.objects.filter(changed_by=user).annotate(at=F('changed_at'))
            .exclude(Exists(duplicate)).select_related('course'))


def _pathway_changes_build(rows):
    return [_item(c.at, 'authoring', f'pathway_{c.change}', f'{c.get_change_display()} the course {c.course_title}',
                  c.course, course=c.course_title) for c in rows]


ACTION_TEXT = {
    'translation_requested': lambda a: f'Requested a {a.details.get("language", "")} translation ({a.details.get("scope", "course")}) of {a.label}',
    'resource_edited': lambda a: f'Edited the resource "{a.details.get("resource_title", "")}" in {a.label}',
    'resource_deleted': lambda a: f'Deleted the resource "{a.details.get("resource_title", "")}" in {a.label}',
    'course_deleted': lambda a: f'Deleted the course "{a.label}"',
    'collaborator_added': lambda a: f'Added {a.details.get("collaborator", "")} as {a.details.get("role", "").replace("_", "-")} to {a.label}',
    'collaborator_removed': lambda a: f'Removed {a.details.get("collaborator", "")} from {a.label}',
    'ai_review_saved': lambda a: f'Saved the AI reviewer set-up of "{a.details.get("resource_title", "")}" in {a.label}',
    'role_changed': lambda a: f'Changed the role of {a.label} from {a.details.get("old_role", "")} to {a.details.get("new_role", "")}',
    'pathways_rebuilt': lambda a: 'Rebuilt everyone\'s learning pathways',
}


def _actions_qs(kinds):
    def qs(user):
        from hub.models import PlatformAction
        return PlatformAction.objects.filter(user=user, kind__in=kinds).select_related('course')
    return qs


def _actions_build(category):
    def build(rows):
        items = []
        for a in rows:
            params = dict(a.details or {})
            if a.kind not in ACCOUNT_ACTIONS:
                params['course'] = a.label
            items.append(_item(a.at, category, a.kind, ACTION_TEXT[a.kind](a), a.course, **params))
        return items
    return build


# ── Account ───────────────────────────────────────────────────────────────────

def _messages_qs(user):
    from hub.models.messaging import Message
    return Message.objects.filter(sender=user).annotate(at=F('created_at')).only('id', 'created_at')


def _messages_build(rows):
    # Never the content, never the recipient.
    return [_item(m.at, 'account', 'message_sent', 'Sent a message') for m in rows]


def _feedback_qs(user):
    from hub.models import Feedback
    return Feedback.objects.filter(user=user).annotate(at=F('created_at'))


def _feedback_build(rows):
    return [_item(f.at, 'account', 'feedback_sent', 'Sent feedback') for f in rows]


def _access_qs(user):
    from hub.models import AccessRequest
    return AccessRequest.objects.filter(user=user).annotate(at=F('created_at'))


def _access_build(rows):
    return [_item(r.at, 'account', 'access_requested', 'Requested content-creator access') for r in rows]


def _logins_qs(user):
    from hub.models import LoginRecord
    return LoginRecord.objects.filter(user=user)


def _logins_build(rows):
    return [_item(r.at, 'account', 'signed_in', f'Signed in ({r.get_device_display() or "unknown device"}, {r.browser or "Other"})',
                  device=r.device, browser=r.browser) for r in rows]


SOURCES = (
    _Source('learning', _visits_qs, _visits_build),
    _Source('learning', _events_qs, _events_build),
    _Source('learning', _enrolled_qs, _enrolled_build),
    _Source('learning', _completed_qs, _completed_build),
    _Source('learning', _submitted_qs, _submitted_build),
    _Source('learning', _competency_qs, _competency_build),
    _Source('learning', _views_qs, _views_build),
    _Source('reviews', _reviews_qs, _reviews_build),
    _Source('authoring', _edits_qs, _edits_build),
    _Source('authoring', _pathway_changes_qs, _pathway_changes_build),
    _Source('authoring', _actions_qs(AUTHORING_ACTIONS), _actions_build('authoring')),
    _Source('account', _actions_qs(ACCOUNT_ACTIONS), _actions_build('account')),
    _Source('account', _messages_qs, _messages_build),
    _Source('account', _feedback_qs, _feedback_build),
    _Source('account', _access_qs, _access_build),
    _Source('account', _logins_qs, _logins_build),
)


def _newest_first(items):
    return sorted(items, key=lambda i: i['at'], reverse=True)


def feed(user, before=None, category=None, limit=FEED_PAGE):
    """(items, next_before): the user's activity, newest first.

    With a limit, each source fetches limit + 1 rows, so the merge knows whether
    more exist. Items sharing the timestamp of the last one kept all stay on this
    page, and the next page starts strictly before it, so none is split or lost.
    limit=None returns everything (the export) and next_before None."""
    if category is not None and category not in CATEGORIES:
        raise ValueError(f'Unknown category: {category}')
    querysets = []
    for source in SOURCES:
        if category not in (None, source.category):
            continue
        qs = source.queryset(user)
        if before is not None:
            qs = qs.filter(at__lt=before)
        querysets.append((source, qs.order_by('-at')))

    if limit is None:
        return _newest_first(i for source, qs in querysets for i in source.build(qs)), None

    fetched = _newest_first(i for source, qs in querysets for i in source.build(qs[:limit + 1]))
    if len(fetched) <= limit:
        return fetched, None
    cut = fetched[limit - 1]['at']
    page = [i for i in fetched if i['at'] > cut]
    for source, qs in querysets:
        page.extend(source.build(qs.filter(at=cut)))
    more = any(qs.filter(at__lt=cut).exists() for _, qs in querysets)
    return _newest_first(page), (cut if more else None)
