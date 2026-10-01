"""Ingest of the activity page's tracking messages (POST /api/tracking/).

The page sends running totals per visit, so a resent message is harmless:
totals only move forward. Each message may add MAX_STEP_SECONDS, or the
wall-clock time since the visit's previous message when that is longer (so
time from a lost message is recovered), and a visit's total never exceeds its
own age plus MAX_STEP_SECONDS (so rapid messages cannot inflate it). Events
carry a browser-made key and are stored once. Anything malformed, or about a
course the user is not enrolled in, is skipped silently."""
import re
import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from hub.models import LearningEvent, Resource, ResourceVisit

MAX_STEP_SECONDS = 35        # most a visit's time may grow per message (beyond elapsed time)
CLOCK_SLACK_SECONDS = 5      # timer jitter allowed on top of wall-clock time
MAX_VISITS_PER_MESSAGE = 50
MAX_EVENTS_PER_MESSAGE = 200
MAX_EVENT_AGE = timedelta(days=1)
MAX_TZ_OFFSET = 14 * 60      # UTC-14 … UTC+14
DEVICES = {value for value, _ in ResourceVisit.Device.choices}
EVENT_TYPES = {value for value, _ in LearningEvent.Type.choices}
LANGUAGE_TAG = re.compile(r'^[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*$')  # e.g. el, pt-BR
EVENT_DATA_KEYS = {'position', 'from', 'to', 'question_index', 'selected', 'seconds_on_question'}


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _number(value):
    """A finite int/float (not bool), else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float('inf'), float('-inf')):
        return None
    return value


def _list(value):
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _int_in(value, lo, hi):
    n = _number(value)
    return int(n) if n is not None and lo <= n <= hi else None


def _context_fields(context):
    if not isinstance(context, dict):
        return {}
    fields = {}
    language = context.get('language')
    if isinstance(language, str) and LANGUAGE_TAG.match(language):
        fields['language'] = language[:8]
    if context.get('device') in DEVICES:
        fields['device'] = context['device']
    fields['local_hour'] = _int_in(context.get('local_hour'), 0, 23)
    fields['tz_offset_minutes'] = _int_in(context.get('tz_offset_minutes'), -MAX_TZ_OFFSET, MAX_TZ_OFFSET)
    return fields


def _merge_media(old, new):
    if not isinstance(new, dict):
        return old
    merged = dict(old or {})
    pct = _number(new.get('covered_pct'))
    if pct is not None:
        merged['covered_pct'] = max(merged.get('covered_pct', 0), min(100, max(0, round(pct))))
    furthest = _number(new.get('furthest_s'))
    if furthest is not None and furthest >= 0:
        merged['furthest_s'] = max(merged.get('furthest_s', 0), round(furthest))
    duration = _number(new.get('duration_s'))
    if duration is not None and duration > 0:
        merged['duration_s'] = round(duration)
    return merged


def _step(old, new_total, limit):
    """Advance a running total towards new_total, never past limit(old) and
    never backwards."""
    n = _number(new_total)
    if n is None:
        return old
    return max(old, min(int(n), limit(old)))


def _limit_for(visit, now):
    """How far a total may grow in this message (see the module docstring)."""
    if visit.pk is None:
        return lambda old: old + MAX_STEP_SECONDS
    since_last = int((now - visit.last_seen_at).total_seconds())
    age = int((now - visit.started_at).total_seconds())
    step = max(MAX_STEP_SECONDS, since_last + CLOCK_SLACK_SECONDS)
    return lambda old: min(old + step, age + MAX_STEP_SECONDS)


def _apply_visit(user, entry, resource, visit_key, page_key, now):
    visit = (
        ResourceVisit.objects.select_for_update()
        .filter(user=user, visit_key=visit_key).first()
    )
    if visit is None:
        visit = ResourceVisit(
            user=user, resource=resource, activity=resource.activity,
            module=resource.activity.module, course_id=resource.activity.module.course_id,
            visit_key=visit_key, page_key=page_key, started_at=now, last_seen_at=now,
            **_context_fields(entry.get('context')),
        )
    elif visit.resource_id != resource.id:
        return None
    limit = _limit_for(visit, now)
    visible = _step(visit.visible_seconds, entry.get('visible_s'), limit)
    active = min(_step(visit.active_seconds, entry.get('active_s'), limit), visible)
    visit.visible_seconds, visit.active_seconds = visible, active
    if entry.get('completed') is True:
        visit.completed_during = True
    visit.media_progress = _merge_media(visit.media_progress, entry.get('media'))
    visit.last_seen_at = now
    if visit.pk is None:
        visit.started_at = now - timedelta(seconds=visible)
    visit.save()
    return visit


def _save_visit(user, entry, resources, page_key, now):
    visit_key = _uuid(entry.get('visit_key'))
    resource = resources.get(entry.get('resource_id'))
    if visit_key is None or resource is None:
        return None
    for _ in range(2):
        try:
            with transaction.atomic():
                return _apply_visit(user, entry, resource, visit_key, page_key, now)
        except IntegrityError:
            continue  # created by a concurrent message: the retry applies onto it
    return None


def _event_time(value, now):
    try:
        at = parse_datetime(value) if isinstance(value, str) else None
    except ValueError:
        at = None
    if at is None or timezone.is_naive(at) or at > now or now - at > MAX_EVENT_AGE:
        return now
    return at


def _event_data(data):
    if not isinstance(data, dict):
        return {}
    clean = {}
    for key in EVENT_DATA_KEYS & data.keys():
        value = data[key]
        if isinstance(value, bool):
            clean[key] = value
        elif _number(value) is not None:
            clean[key] = round(value, 1) if isinstance(value, float) else value
    return clean


def _save_events(user, events, resources, visits, now):
    rows = []
    for entry in events:
        event_key = _uuid(entry.get('event_key'))
        resource = resources.get(entry.get('resource_id'))
        if event_key is None or resource is None or entry.get('type') not in EVENT_TYPES:
            continue
        visit = visits.get(_uuid(entry.get('visit_key')))
        rows.append(LearningEvent(
            user=user, resource=resource,
            visit=visit if visit is not None and visit.resource_id == resource.id else None,
            course_id=resource.activity.module.course_id, event_key=event_key,
            event_type=entry['type'], occurred_at=_event_time(entry.get('at'), now),
            data=_event_data(entry.get('data')),
        ))
    LearningEvent.objects.bulk_create(rows, ignore_conflicts=True)
    return len(rows)


def ingest(user, payload):
    """Apply one tracking message. Returns (visits stored, events stored)."""
    if not isinstance(payload, dict):
        return 0, 0
    page_key = _uuid(payload.get('page_key'))
    if page_key is None:
        return 0, 0
    entries = _list(payload.get('visits'))[:MAX_VISITS_PER_MESSAGE]
    events = _list(payload.get('events'))[:MAX_EVENTS_PER_MESSAGE]
    ids = {
        e.get('resource_id') for e in entries + events
        if isinstance(e.get('resource_id'), int) and not isinstance(e.get('resource_id'), bool)
    }
    resources = {
        r.id: r for r in Resource.objects.filter(
            id__in=ids, activity__module__course__enrollments__user=user,
        ).select_related('activity__module')
    }
    now = timezone.now()
    visits = {}
    for entry in entries:
        visit = _save_visit(user, entry, resources, page_key, now)
        if visit is not None:
            visits[visit.visit_key] = visit
    return len(visits), _save_events(user, events, resources, visits, now)
