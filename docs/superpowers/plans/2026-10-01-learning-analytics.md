# Detailed Learning Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure each learner's active and on-screen time per resource, plus video, quiz, PDF and image interactions. Show this per course on the web (Content and Learners tabs, plus a learner timeline) and export it to a research-grade Excel workbook.

**Architecture:**
- The activity page runs a small tracker that sends running totals per visit (and queued events) to `POST /api/tracking/`. The server stores them in two new tables, `ResourceVisit` and `LearningEvent`.
- `analytics/learning.py` loads one course's structure and learner data once (`CourseData`) and derives every number from it. Both the new web endpoints and the new workbook builder (`analytics/workbook.py`) read from it, so the web view and Excel always agree.

**Tech Stack:** Django 5 + DRF and openpyxl on the backend; React 19 + Vite on the frontend, with the YouTube IFrame API and Vimeo Player.js loaded on demand. Pure tracker logic is tested with Node's built-in test runner (`node --test`), so no new npm dependency is needed.

**Spec:** `docs/superpowers/specs/2026-10-01-learning-analytics-design.md`

## Global Constraints

- Active time = page visible and (scroll, key, click, touch or pointer move in the last 60 s, or a video playing). On-screen time = page visible. Active is the headline figure, and active ≤ on-screen always.
- Time goes to one resource at a time: **a playing video**, else **the resource being interacted with**, else **the resource occupying most of the viewport**.
- Sending: every **30 s**, and immediately on tab hide or page leave (`fetch` with `keepalive`, carrying the auth header).
- Server caps: each visit's time grows by at most **35 s per message**; only resources in courses the user is enrolled in are stored; rate-limited per user; a visit is upserted by `visit_key`; when tracking is switched off the server returns **204**, stores nothing, and the page stops sending.
- Status rules, applied in this order: **completed** (course done), **inactive** (no activity for 14+ days), **stuck** (3+ visits to one resource without finishing it, or a failed quiz), otherwise **on track**.
- "Dropped here" = the learner's last activity in the course was on this item, the course is not finished, and there has been no activity for 14+ days.
- Typical time = **median** among learners who reached the item and have measured visits. The average is shown on hover.
- Items with no measured visits but with progress (work done before tracking began) show **"not tracked"** for time; completion, scores and dates are still shown.
- Excel: plain seconds in long sheets, minutes in Overview, timestamps as UTC ISO text, ID and order columns on every sheet. Sheets, in order: README, Overview, Learners, Modules, Activities, Resources, Visits, Quiz answers, Events.
- Context data only: language (≤8 chars), device (`desktop`/`tablet`/`mobile`), local hour (0–23), time-zone offset. No IP address, no precise location.
- Scope for every analytics endpoint: `analytics.views.scoped_courses(user)` behind `IsContentCreator`.
- Keep all 9 locales in sync: en, el, fr, es, it, fi, sv, no, de. `npm run check:locales` must pass.
- Icons come from `lucide-react` only. Styling uses per-component CSS files.
- Backend commands run from `backend/` with `UV="/c/Users/Nikos A. Grammatikos/.local/bin/uv.exe"` (the `.venv/Scripts/uv.exe` from CLAUDE.md is missing on this machine): `"$UV" run manage.py …`, `"$UV" run ruff check hub analytics`.
- Run git commands from the directory the task's commands use: `backend/` for Tasks 1, 2, 5, 6 and 7; `frontend/` for Tasks 3, 4 and 8. Commit paths in the steps are relative to it.
- Edit files without changing their line endings: files are CRLF, so keep CRLF.
- Two small additions to the spec's data model, both for correctness:
  - `ResourceVisit.page_key` (one per activity-page visit), so that activity and module "visits" count page openings rather than summing resource visits.
  - `LearningEvent.event_key`, so that a resent event is stored once.
- `quiz_answer` events carry `{question_index, selected, seconds_on_question}`. Analytics derives right/wrong from the stored quiz result rather than trusting the browser.
- The page sends **running totals** per visit rather than deltas, which makes resends harmless; the 35 s cap applies to each message's growth.
- The old per-course "View teachers" drill-down (`/api/analytics/courses/<id>/teachers/` and `analytics/reports.py`) is replaced by the Learners tab and the new workbook, and is removed.
- Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Work happens on `master`; push after each task.

## Review Focus

1. **A resent or overlapping message** (a lost response, a keepalive racing a periodic send) must not double-count time or duplicate events. This is pinned by Task 2's `test_resending_the_same_totals_is_harmless` and `test_events_stored_and_deduplicated`.
2. **A hidden tab, a sleeping laptop or throttled background timers** must add no time. A tick is worth at most 5 s, and nothing accrues while the page is hidden. This is pinned by Task 3's `elapsedSeconds` tests.
3. **A learner whose work predates tracking** (progress but no visits) must show "not tracked", be left out of medians, and not break the timeline or the workbook. This is pinned by the `old` learner in the Task 5, 6 and 7 tests.
4. **Content edited after learners used it:** a quiz shortened so a stored answer index points past the options, a resource deleted, or an empty course. This must not crash analytics. Pinned by Task 5 `test_quiz_answers_survive_edited_quiz` and Task 7 `test_workbook_for_empty_course`.
5. **Malformed or hostile tracking payloads** (wrong types, unknown resources, another course's resources, absurd numbers) must be ignored without a 500 error. Pinned by Task 2 `test_malformed_payloads_do_not_fail`, `test_not_enrolled_resource_ignored` and `test_invalid_context_values_dropped`.

---

## File Structure

**Backend**
- Create `backend/hub/models/tracking.py`: the `ResourceVisit` and `LearningEvent` models.
- Modify `backend/hub/models/activity.py`: add `LearnerActivityConfig.tracking_enabled`.
- Modify `backend/hub/models/__init__.py`: export the new models.
- Create migration `backend/hub/migrations/0061_learning_tracking.py` (generated).
- Modify `backend/hub/admin.py`: add the switch to the config admin and register read-only admins for the new tables.
- Create `backend/hub/tracking.py`: `ingest(user, payload)`, which validates, caps and upserts.
- Create `backend/hub/views/tracking.py`: `TrackingView`.
- Modify `backend/hub/throttling.py`, `backend/aidea/settings.py` and `backend/hub/urls.py`: the throttle and the route.
- Create `backend/hub/tests/test_tracking.py`.
- Create `backend/analytics/learning.py`: `CourseData`, `content_tree`, `learner_row(s)`, `learner_timeline`.
- Create `backend/analytics/workbook.py`: `build_learning_workbook`.
- Modify `backend/analytics/views.py` and `backend/analytics/urls.py`: four new views. The old export switches to the new builder; the old teachers drill-down is removed.
- Delete `backend/analytics/reports.py` and `backend/analytics/tests/test_teacher_detail.py`. They are replaced by the new modules and tests.
- Create `backend/analytics/tests/fixtures.py`, `test_learning.py`, `test_learning_api.py` and `test_workbook.py`.

**Frontend**
- Create in `frontend/src/lib/tracking/`:
  - `coverage.js`, `attention.js`, `ledger.js`, `context.js`: pure logic, with `*.test.js` beside each.
  - `videoPlayers.js`: adapters for `<video>`, YouTube and Vimeo.
  - `tracker.js`: wires the DOM, timers and sending.
  - `TrackingContext.js`: context and the per-resource hook.
  - `useActivityTracker.js`: the page hook.
- Modify `frontend/package.json` (adds a `test` script) and `.github/workflows/ci.yml` (runs `npm test`).
- Modify `frontend/src/pages/ActivityPage.jsx`, `frontend/src/components/learner/ResourceView.jsx`, `frontend/src/components/lesson/MediaItem.jsx` and `frontend/src/components/lesson/MediaEmbeds.jsx`.
- Create `frontend/src/pages/AnalyticsCoursePage.jsx` and `.css`.
- Create `frontend/src/components/analytics/ContentTree.jsx`, `LearnersTable.jsx`, `LearnerTimeline.jsx`, `format.js` and `download.js`.
- Modify `frontend/src/pages/AnalyticsPage.jsx` and `.css` (adds Open and Excel buttons; removes the inline teachers drill-down), and `frontend/src/App.jsx` (adds the route).
- Modify `frontend/src/locales/*.json` (9 files) and `frontend/src/pages/PrivacyPage.jsx`.
- Modify `CLAUDE.md` to list the new endpoints.

---

### Task 1: Tracking models, switch, migration, admin

**Files:**
- Create: `backend/hub/models/tracking.py`
- Modify: `backend/hub/models/activity.py` (`LearnerActivityConfig`)
- Modify: `backend/hub/models/__init__.py`
- Modify: `backend/hub/admin.py` (`LearnerActivityConfigAdmin` near line 430, plus imports)
- Create: `backend/hub/migrations/0061_learning_tracking.py` (generated)
- Test: `backend/hub/tests/test_tracking.py`

**Interfaces:**
- Produces:
  - `hub.models.ResourceVisit`, with fields `user, resource, activity, module, course, visit_key (UUID), page_key (UUID), started_at, last_seen_at, active_seconds, visible_seconds, completed_during, language, device, local_hour, tz_offset_minutes, media_progress` and `ResourceVisit.Device` choices.
  - `hub.models.LearningEvent`, with fields `user, resource, visit (nullable), course, event_key (UUID), event_type, occurred_at, data` and `LearningEvent.Type` choices.
  - `LearnerActivityConfig.tracking_enabled`.

- [ ] **Step 1: Write the failing test**

Create `backend/hub/tests/test_tracking.py`:

```python
import uuid

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from hub.models import (
    Activity,
    Course,
    LearnerActivityConfig,
    LearningEvent,
    LearningPillar,
    Module,
    Resource,
    ResourceVisit,
)


class TrackingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tm_user', password='pass12345')
        pillar = LearningPillar.objects.create(name='P', slug='p-tm', order=1)
        self.course = Course.objects.create(
            title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        self.module = Module.objects.create(course=self.course, title='M', order=1)
        self.activity = Activity.objects.create(module=self.module, title='A', order=1)
        self.resource = Resource.objects.create(activity=self.activity, type='text', order=1)

    def _visit(self, key):
        now = timezone.now()
        return ResourceVisit.objects.create(
            user=self.user, resource=self.resource, activity=self.activity,
            module=self.module, course=self.course, visit_key=key, page_key=uuid.uuid4(),
            started_at=now, last_seen_at=now,
        )

    def test_visit_defaults(self):
        v = self._visit(uuid.uuid4())
        self.assertEqual((v.active_seconds, v.visible_seconds), (0, 0))
        self.assertFalse(v.completed_during)
        self.assertEqual(v.media_progress, {})

    def test_visit_key_unique_per_user(self):
        key = uuid.uuid4()
        self._visit(key)
        with self.assertRaises(IntegrityError):
            self._visit(key)

    def test_event_key_unique_per_user(self):
        key = uuid.uuid4()
        fields = dict(
            user=self.user, resource=self.resource, course=self.course, event_key=key,
            event_type=LearningEvent.Type.PDF_OPEN, occurred_at=timezone.now(),
        )
        LearningEvent.objects.create(**fields)
        with self.assertRaises(IntegrityError):
            LearningEvent.objects.create(**fields)

    def test_tracking_enabled_by_default(self):
        self.assertTrue(LearnerActivityConfig.get().tracking_enabled)
```

- [ ] **Step 2: Run the test to verify it fails**

Run (from `backend/`): `"$UV" run manage.py test hub.tests.test_tracking -v 2`
Expected: an ImportError (`cannot import name 'LearningEvent'`).

- [ ] **Step 3: Implement**

Create `backend/hub/models/tracking.py`:

```python
"""Measured learning activity — see
docs/superpowers/specs/2026-10-01-learning-analytics-design.md.

ResourceVisit: one row per learner, per resource, per activity-page visit, with
active / on-screen seconds accumulated from the page's messages.
LearningEvent: one row per discrete moment (video play/seek, PDF download,
quiz answer …). Module and activity times are derived from visits, never stored."""
from django.contrib.auth.models import User
from django.db import models


class ResourceVisit(models.Model):
    class Device(models.TextChoices):
        DESKTOP = 'desktop', 'Desktop'
        TABLET  = 'tablet',  'Tablet'
        MOBILE  = 'mobile',  'Mobile'

    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resource_visits')
    resource = models.ForeignKey('hub.Resource', on_delete=models.CASCADE, related_name='visits')
    # Denormalised from resource for fast per-course / per-module queries.
    activity = models.ForeignKey('hub.Activity', on_delete=models.CASCADE, related_name='+')
    module   = models.ForeignKey('hub.Module', on_delete=models.CASCADE, related_name='+')
    course   = models.ForeignKey('hub.Course', on_delete=models.CASCADE, related_name='+')
    visit_key = models.UUIDField()  # made by the browser: one per resource per page visit
    page_key  = models.UUIDField()  # made by the browser: one per activity-page visit
    started_at   = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    active_seconds   = models.PositiveIntegerField(default=0)
    visible_seconds  = models.PositiveIntegerField(default=0)
    completed_during = models.BooleanField(default=False)
    language = models.CharField(max_length=8, blank=True)
    device   = models.CharField(max_length=10, choices=Device.choices, blank=True)
    local_hour        = models.PositiveSmallIntegerField(null=True, blank=True)
    tz_offset_minutes = models.SmallIntegerField(null=True, blank=True)  # minutes ahead of UTC
    # Videos: {covered_pct, furthest_s, duration_s} for this visit.
    media_progress = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('user', 'visit_key')
        indexes = [
            models.Index(fields=['course', 'user']),
            models.Index(fields=['resource', 'user']),
            models.Index(fields=['user', 'last_seen_at']),
        ]

    def __str__(self):
        return f'{self.user.username} on resource {self.resource_id} at {self.started_at}'


class LearningEvent(models.Model):
    class Type(models.TextChoices):
        VIDEO_PLAY   = 'video_play',   'Video play'
        VIDEO_PAUSE  = 'video_pause',  'Video pause'
        VIDEO_SEEK   = 'video_seek',   'Video seek'
        VIDEO_ENDED  = 'video_ended',  'Video ended'
        PDF_OPEN     = 'pdf_open',     'PDF opened'
        PDF_DOWNLOAD = 'pdf_download', 'PDF downloaded'
        IMAGE_OPEN   = 'image_open',   'Image opened'
        QUIZ_ANSWER  = 'quiz_answer',  'Quiz answer'

    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_events')
    resource = models.ForeignKey('hub.Resource', on_delete=models.CASCADE, related_name='events')
    visit    = models.ForeignKey(
        ResourceVisit, on_delete=models.SET_NULL, null=True, blank=True, related_name='events',
    )
    course    = models.ForeignKey('hub.Course', on_delete=models.CASCADE, related_name='+')
    event_key = models.UUIDField()  # made by the browser, so a resent event is stored once
    event_type  = models.CharField(max_length=20, choices=Type.choices)
    occurred_at = models.DateTimeField()
    # e.g. {position} · {from, to} · {question_index, selected, seconds_on_question}
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('user', 'event_key')
        ordering = ['occurred_at']
        indexes = [
            models.Index(fields=['course', 'user']),
            models.Index(fields=['resource', 'event_type']),
        ]

    def __str__(self):
        return f'{self.user.username} {self.event_type} at {self.occurred_at}'
```

In `backend/hub/models/activity.py`, add this to `LearnerActivityConfig` after `idle_decay_points`:

```python

    # Learning analytics: when off, the activity page stops sending time and
    # interaction data (see hub/tracking.py). Existing data is kept.
    tracking_enabled = models.BooleanField(default=True)
```

In `backend/hub/models/__init__.py`, add `from .tracking import LearningEvent, ResourceVisit` between the `.subject` and `.user` imports. Add `'LearningEvent'` and `'ResourceVisit'` to `__all__`, keeping it alphabetical.

In `backend/hub/admin.py`:
- Add `LearningEvent` and `ResourceVisit` to the `from .models import (...)` list, alphabetically.
- Add this to `LearnerActivityConfigAdmin.fieldsets` after the `('Decay', …)` entry:

```python
        ('Learning analytics', {
            'fields': ['tracking_enabled'],
            'description': (
                'When off, activity pages stop sending time and interaction data. '
                'Data already collected is kept.'
            ),
        }),
```

Then add these read-only admins after `LearnerActivityConfigAdmin`:

```python
class _ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ResourceVisit)
class ResourceVisitAdmin(_ReadOnlyAdmin):
    list_display = ['user', 'course', 'resource', 'started_at', 'active_seconds', 'visible_seconds', 'device']
    list_filter = ['device', 'completed_during']
    search_fields = ['user__username', 'course__title']
    raw_id_fields = ['user', 'resource', 'activity', 'module', 'course']


@admin.register(LearningEvent)
class LearningEventAdmin(_ReadOnlyAdmin):
    list_display = ['user', 'course', 'resource', 'event_type', 'occurred_at']
    list_filter = ['event_type']
    search_fields = ['user__username', 'course__title']
    raw_id_fields = ['user', 'resource', 'visit', 'course']
```

Generate the migration: `"$UV" run manage.py makemigrations hub --name learning_tracking`
Expected: `hub/migrations/0061_learning_tracking.py`, containing the two models plus `learneractivityconfig.tracking_enabled`.

Apply it to the local database: `"$UV" run manage.py migrate`

- [ ] **Step 4: Run the tests to verify they pass**

Run: `"$UV" run manage.py test hub.tests.test_tracking -v 2`
Expected: 4 tests pass.

- [ ] **Step 5: Lint and commit**

```bash
"$UV" run ruff check hub analytics
git add hub/models/tracking.py hub/models/activity.py hub/models/__init__.py hub/admin.py hub/migrations/0061_learning_tracking.py hub/tests/test_tracking.py
git commit -m "feat: ResourceVisit and LearningEvent models with tracking switch"
git push
```

---

### Task 2: `POST /api/tracking/`, the ingest service

**Files:**
- Create: `backend/hub/tracking.py`
- Create: `backend/hub/views/tracking.py`
- Modify: `backend/hub/throttling.py` (append a class)
- Modify: `backend/aidea/settings.py` (`DEFAULT_THROTTLE_RATES`, around line 245)
- Modify: `backend/hub/urls.py` (add the route next to `maintenance/`)
- Test: `backend/hub/tests/test_tracking.py` (append)

**Interfaces:**
- Consumes: the Task 1 models.
- Produces the HTTP contract the frontend tracker (Tasks 3–4) relies on.

**Request:** `POST /api/tracking/`, sending JSON:

```json
{
  "page_key": "uuid — one per activity-page visit",
  "visits": [{
    "visit_key": "uuid", "resource_id": 12,
    "active_s": 40, "visible_s": 55,
    "completed": true,
    "media": {"covered_pct": 40, "furthest_s": 120, "duration_s": 300},
    "context": {"language": "el", "device": "mobile", "local_hour": 14, "tz_offset_minutes": 180}
  }],
  "events": [{
    "event_key": "uuid", "visit_key": "uuid", "resource_id": 12,
    "type": "video_seek", "at": "2026-10-01T10:00:00.000Z", "data": {"from": 30, "to": 90}
  }]
}
```

- `active_s` and `visible_s` are **running totals** for the visit, not deltas, so resending is harmless.
- `completed`, `media` and `context` are optional.

**Response:**
- `200 {"visits": n, "events": m}`.
- `204` when tracking is switched off; the page stops sending.
- `429` when throttled; the page keeps its data and retries.

- [ ] **Step 1: Write the failing tests**

Append to `backend/hub/tests/test_tracking.py`. Merge the new imports into the file's import block so ruff's isort passes; the full import block is shown first.

```python
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import (
    Activity,
    Course,
    Enrollment,
    LearnerActivityConfig,
    LearningEvent,
    LearningPillar,
    Module,
    Resource,
    ResourceVisit,
    UserProfile,
)
```

```python
class TrackingEndpointTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('te_user', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P', slug='p-te', order=1)
        self.course = Course.objects.create(
            title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        self.module = Module.objects.create(course=self.course, title='M', order=1)
        self.activity = Activity.objects.create(module=self.module, title='A', order=1)
        self.text = Resource.objects.create(activity=self.activity, type='text', order=1)
        self.video = Resource.objects.create(activity=self.activity, type='video', order=2)
        Enrollment.objects.create(user=self.user, course=self.course)
        other = Course.objects.create(
            title='Other', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        other_module = Module.objects.create(course=other, title='OM', order=1)
        other_activity = Activity.objects.create(module=other_module, title='OA', order=1)
        self.foreign = Resource.objects.create(activity=other_activity, type='text', order=1)
        self.page = uuid.uuid4()
        self.url = reverse('tracking')
        self.client.force_authenticate(self.user)

    def post(self, visits=(), events=(), page=None):
        payload = {'page_key': str(page or self.page), 'visits': list(visits), 'events': list(events)}
        return self.client.post(self.url, payload, format='json')

    def visit(self, key, resource=None, **fields):
        return {'visit_key': str(key), 'resource_id': (resource or self.text).id, **fields}

    def test_first_message_creates_visit_with_context(self):
        key = uuid.uuid4()
        res = self.post([self.visit(key, active_s=20, visible_s=28, context={
            'language': 'el', 'device': 'mobile', 'local_hour': 14, 'tz_offset_minutes': 180,
        })])
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {'visits': 1, 'events': 0})
        v = ResourceVisit.objects.get(user=self.user, visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (20, 28))
        self.assertEqual(
            (v.activity_id, v.module_id, v.course_id, v.page_key),
            (self.activity.id, self.module.id, self.course.id, self.page),
        )
        self.assertEqual((v.language, v.device, v.local_hour, v.tz_offset_minutes), ('el', 'mobile', 14, 180))
        self.assertAlmostEqual((v.last_seen_at - v.started_at).total_seconds(), 28, delta=1)

    def test_resending_the_same_totals_is_harmless(self):
        key = uuid.uuid4()
        self.post([self.visit(key, active_s=20, visible_s=25)])
        self.post([self.visit(key, active_s=20, visible_s=25)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (20, 25))
        self.assertEqual(ResourceVisit.objects.count(), 1)

    def test_growth_per_message_capped(self):
        key = uuid.uuid4()
        self.post([self.visit(key, active_s=20, visible_s=20)])
        self.post([self.visit(key, active_s=500, visible_s=500)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (55, 55))

    def test_first_message_capped_too(self):
        key = uuid.uuid4()
        self.post([self.visit(key, active_s=900, visible_s=900)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (35, 35))

    def test_active_never_exceeds_on_screen(self):
        key = uuid.uuid4()
        self.post([self.visit(key, active_s=30, visible_s=10)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (10, 10))

    def test_totals_never_go_backwards(self):
        key = uuid.uuid4()
        self.post([self.visit(key, active_s=30, visible_s=30)])
        self.post([self.visit(key, active_s=5, visible_s=-40)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.active_seconds, v.visible_seconds), (30, 30))

    def test_not_enrolled_resource_ignored(self):
        res = self.post([self.visit(uuid.uuid4(), self.foreign, active_s=10, visible_s=10)])
        self.assertEqual(res.data, {'visits': 0, 'events': 0})
        self.assertFalse(ResourceVisit.objects.exists())

    def test_visit_key_cannot_switch_resource(self):
        key = uuid.uuid4()
        self.post([self.visit(key, self.text, active_s=10, visible_s=10)])
        self.post([self.visit(key, self.video, active_s=30, visible_s=30)])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.resource_id, v.visible_seconds), (self.text.id, 10))

    def test_invalid_context_values_dropped(self):
        key = uuid.uuid4()
        self.post([self.visit(key, visible_s=5, context={
            'language': 'el-GR-extra-long', 'device': 'fridge', 'local_hour': 99, 'tz_offset_minutes': 5000,
        })])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual((v.language, v.device, v.local_hour, v.tz_offset_minutes), ('el-GR-ex', '', None, None))

    def test_media_progress_keeps_maximums(self):
        key = uuid.uuid4()
        self.post([self.visit(key, self.video, visible_s=10, media={'covered_pct': 40, 'furthest_s': 120, 'duration_s': 300})])
        self.post([self.visit(key, self.video, visible_s=20, media={'covered_pct': 30, 'furthest_s': 60, 'duration_s': 300})])
        v = ResourceVisit.objects.get(visit_key=key)
        self.assertEqual(v.media_progress, {'covered_pct': 40, 'furthest_s': 120, 'duration_s': 300})

    def test_completed_flag(self):
        key = uuid.uuid4()
        self.post([self.visit(key, visible_s=5, completed=True)])
        self.post([self.visit(key, visible_s=8)])
        self.assertTrue(ResourceVisit.objects.get(visit_key=key).completed_during)

    def test_events_stored_and_deduplicated(self):
        key, ev = uuid.uuid4(), uuid.uuid4()
        event = {
            'event_key': str(ev), 'visit_key': str(key), 'resource_id': self.video.id,
            'type': 'video_seek', 'at': timezone.now().isoformat(), 'data': {'from': 30, 'to': 90},
        }
        self.post([self.visit(key, self.video, visible_s=5)], [event])
        self.post([self.visit(key, self.video, visible_s=5)], [event])
        stored = LearningEvent.objects.get()
        self.assertEqual(stored.event_type, 'video_seek')
        self.assertEqual(stored.data, {'from': 30, 'to': 90})
        self.assertEqual(stored.visit.visit_key, key)
        self.assertEqual(stored.course_id, self.course.id)

    def test_unknown_event_types_and_extra_data_dropped(self):
        self.post([], [
            {'event_key': str(uuid.uuid4()), 'resource_id': self.text.id, 'type': 'keylogger', 'data': {}},
            {'event_key': str(uuid.uuid4()), 'resource_id': self.text.id, 'type': 'quiz_answer',
             'data': {'question_index': 1, 'selected': 0, 'seconds_on_question': 4.25, 'secret': 'x', 'selected_text': 'y'}},
        ])
        stored = LearningEvent.objects.get()
        self.assertEqual(stored.data, {'question_index': 1, 'selected': 0, 'seconds_on_question': 4.2})

    def test_event_time_in_future_or_garbage_replaced_by_now(self):
        for at in [(timezone.now() + timedelta(days=2)).isoformat(), 'yesterday', '2026-13-45T99:00:00Z']:
            self.post([], [{'event_key': str(uuid.uuid4()), 'resource_id': self.text.id, 'type': 'pdf_open', 'at': at}])
        for ev in LearningEvent.objects.all():
            self.assertLess(abs((timezone.now() - ev.occurred_at).total_seconds()), 60)

    def test_tracking_switched_off_returns_204_and_stores_nothing(self):
        config = LearnerActivityConfig.get()
        config.tracking_enabled = False
        config.save()
        res = self.post([self.visit(uuid.uuid4(), visible_s=5)])
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResourceVisit.objects.exists())

    def test_malformed_payloads_do_not_fail(self):
        payloads = [
            [],
            {'visits': {}},
            {'page_key': 'not-a-uuid', 'visits': [self.visit(uuid.uuid4(), visible_s=5)]},
            {'page_key': str(self.page), 'visits': ['a', 1, None], 'events': 'zzz'},
            {'page_key': str(self.page), 'visits': [{'visit_key': 'nope', 'resource_id': '1'}]},
            {'page_key': str(self.page), 'visits': [self.visit(uuid.uuid4(), visible_s='lots', media='x', context=[1])]},
        ]
        for payload in payloads:
            res = self.client.post(self.url, payload, format='json')
            self.assertEqual(res.status_code, status.HTTP_200_OK, payload)
        # Only the last one names a real visit; its non-numeric totals are ignored.
        self.assertEqual(ResourceVisit.objects.get().visible_seconds, 0)

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.post().status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        'DEFAULT_THROTTLE_RATES': {**settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'], 'tracking': '2/min'},
    })
    def test_throttled_per_user(self):
        cache.clear()
        codes = [self.post().status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `"$UV" run manage.py test hub.tests.test_tracking -v 2`
Expected: the new tests error with `NoReverseMatch: Reverse for 'tracking' not found`.

- [ ] **Step 3: Implement**

Create `backend/hub/tracking.py`:

```python
"""Ingest of the activity page's tracking messages (POST /api/tracking/).

The page sends running totals per visit, so a resent message is harmless:
totals only move forward, and by at most MAX_STEP_SECONDS per message. Events
carry a browser-made key and are stored once. Anything malformed, or about a
course the user is not enrolled in, is skipped silently."""
import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from hub.models import LearningEvent, Resource, ResourceVisit

MAX_STEP_SECONDS = 35        # most a visit's time may grow per message
MAX_VISITS_PER_MESSAGE = 50
MAX_EVENTS_PER_MESSAGE = 200
MAX_EVENT_AGE = timedelta(days=1)
MAX_TZ_OFFSET = 14 * 60      # UTC-14 … UTC+14
DEVICES = {value for value, _ in ResourceVisit.Device.choices}
EVENT_TYPES = {value for value, _ in LearningEvent.Type.choices}
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
    if isinstance(context.get('language'), str):
        fields['language'] = context['language'][:8]
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


def _step(old, new_total):
    """Advance a running total by at most MAX_STEP_SECONDS; never backwards."""
    n = _number(new_total)
    if n is None:
        return old
    return max(old, min(int(n), old + MAX_STEP_SECONDS))


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
    visible = _step(visit.visible_seconds, entry.get('visible_s'))
    active = min(_step(visit.active_seconds, entry.get('active_s')), visible)
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
```

Note: `round(4.25, 1)` gives `4.2` (banker's rounding on a binary float), which matches the test.

Create `backend/hub/views/tracking.py`:

```python
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import LearnerActivityConfig
from hub.throttling import TrackingUserThrottle
from hub.tracking import ingest


class TrackingView(APIView):
    """POST /api/tracking/ — the activity page's time and interaction data
    (see hub/tracking.py). 204 means tracking is switched off: the page stops."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [TrackingUserThrottle]

    def post(self, request):
        if not LearnerActivityConfig.get().tracking_enabled:
            return Response(status=status.HTTP_204_NO_CONTENT)
        visits, events = ingest(request.user, request.data)
        return Response({'visits': visits, 'events': events})
```

Append to `backend/hub/throttling.py`:

```python


class TrackingUserThrottle(_LiveRateThrottle):
    """Activity-page tracking messages, per signed-in user."""
    scope = 'tracking'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': request.user.pk}
```

In `backend/aidea/settings.py`, add this line to `DEFAULT_THROTTLE_RATES` after `'pw_reset_ip'`:

```python
        'tracking':        '30/min',   # activity-page messages per user (normal use ≈ 2–4/min)
```

In `backend/hub/urls.py`:
- Add the import: `from .views.tracking import TrackingView`, placed after the existing `from .views.authoring_course import …` line.
- Add the route next to `maintenance/`:

```python
    path('tracking/',             TrackingView.as_view(),             name='tracking'),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `"$UV" run manage.py test hub.tests.test_tracking -v 2`
Expected: all tests pass (4 model + 18 endpoint).

- [ ] **Step 5: Lint and commit**

```bash
"$UV" run ruff check hub analytics
git add hub/tracking.py hub/views/tracking.py hub/throttling.py aidea/settings.py hub/urls.py hub/tests/test_tracking.py
git commit -m "feat: tracking endpoint with per-message caps, enrolment check and idempotent upsert"
git push
```

---

### Task 3: Tracker core logic (pure JS + Node tests)

**Files:**
- Create: `frontend/src/lib/tracking/coverage.js`, `coverage.test.js`
- Create: `frontend/src/lib/tracking/attention.js`, `attention.test.js`
- Create: `frontend/src/lib/tracking/ledger.js`, `ledger.test.js`
- Create: `frontend/src/lib/tracking/context.js`, `context.test.js`
- Modify: `frontend/package.json` (`scripts`)
- Modify: `.github/workflows/ci.yml` (frontend job)

**Interfaces:**
- Produces:
  - `coverage.js`:
    - `mergeRanges(ranges) → [[start, end], …]`
    - `coveredPct(ranges, duration) → 0..100`
    - `createRangeRecorder() → { sample(pos), cut(), ranges(), furthest() }`
  - `attention.js`:
    - `IDLE_MS = 60000`, `MAX_TICK_GAP_S = 5`
    - `elapsedSeconds(prevMs, nowMs, visible)`
    - `pickTarget({ playing, lastResourceInput, visiblePx, now }) → resourceId | null`
    - `isActive({ visible, lastInputAt, playing, now }) → bool`
  - `ledger.js`: `MAX_EVENTS_PER_MESSAGE = 200` and `createLedger({ pageKey, newKey, context })`, returning:
    - `{ addTime(id, seconds, active), markCompleted(id), setMedia(id, media), addEvent(id, type, data, at?), isEmpty(), payload(), ack(payload) }`
    - `payload()` returns the Task 2 request body.
  - `context.js`: `deviceFromUserAgent(ua, touchPoints) → 'desktop'|'tablet'|'mobile'` and `pageContext(language) → {language, device, local_hour, tz_offset_minutes}`.

- [ ] **Step 1: Write the failing tests**

`frontend/src/lib/tracking/coverage.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { coveredPct, createRangeRecorder, mergeRanges } from './coverage.js'

test('mergeRanges joins overlapping and touching ranges', () => {
  assert.deepEqual(mergeRanges([[20, 60], [0, 30], [60, 70], [90, 95], [5, 5]]), [[0, 70], [90, 95]])
})

test('coveredPct counts each second once and clamps to the duration', () => {
  assert.equal(coveredPct([[0, 30], [20, 60]], 120), 50)
  assert.equal(coveredPct([[100, 200]], 120), 17)
  assert.equal(coveredPct([[0, 10]], 0), 0)
})

test('recorder extends a range while playing and cuts on jumps', () => {
  const rec = createRangeRecorder()
  ;[0, 1, 2, 3].forEach(p => rec.sample(p))
  rec.sample(50)            // jump forward: a seek
  rec.sample(51)
  rec.sample(10)            // jump back: another seek
  rec.sample(11.5)
  assert.deepEqual(rec.ranges(), [[0, 3], [10, 11.5], [50, 51]])
  assert.equal(rec.furthest(), 51)
})

test('recorder cut() starts a new range at the next sample', () => {
  const rec = createRangeRecorder()
  rec.sample(0); rec.sample(1); rec.cut(); rec.sample(1.5); rec.sample(2)
  assert.deepEqual(rec.ranges(), [[0, 1], [1.5, 2]])   // the paused gap is not "played"
})

test('recorder ignores invalid positions', () => {
  const rec = createRangeRecorder()
  rec.sample(NaN); rec.sample(-1); rec.sample(undefined)
  assert.deepEqual(rec.ranges(), [])
})
```

`frontend/src/lib/tracking/attention.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { IDLE_MS, elapsedSeconds, isActive, pickTarget } from './attention.js'

const px = (entries) => new Map(entries)

test('a playing video wins, most recent first', () => {
  const target = pickTarget({ playing: [3, 7], lastResourceInput: { resourceId: 1, at: 0 }, visiblePx: px([[1, 500]]), now: 10 })
  assert.equal(target, 7)
})

test('recent interaction with a resource still on screen wins over size', () => {
  const visiblePx = px([[1, 50], [2, 600]])
  assert.equal(pickTarget({ playing: [], lastResourceInput: { resourceId: 1, at: 1000 }, visiblePx, now: 2000 }), 1)
})

test('stale or off-screen interaction falls back to the largest visible resource', () => {
  const visiblePx = px([[1, 0], [2, 600], [3, 200]])
  assert.equal(pickTarget({ playing: [], lastResourceInput: { resourceId: 1, at: 1000 }, visiblePx, now: 2000 }), 2)
  assert.equal(pickTarget({ playing: [], lastResourceInput: { resourceId: 3, at: 0 }, visiblePx, now: IDLE_MS + 1 }), 2)
})

test('nothing on screen means no target', () => {
  assert.equal(pickTarget({ playing: [], lastResourceInput: null, visiblePx: px([]), now: 0 }), null)
})

test('active needs a visible page and recent input or a playing video', () => {
  assert.equal(isActive({ visible: true, lastInputAt: 0, playing: [], now: IDLE_MS - 1 }), true)
  assert.equal(isActive({ visible: true, lastInputAt: 0, playing: [], now: IDLE_MS }), false)
  assert.equal(isActive({ visible: true, lastInputAt: 0, playing: [4], now: IDLE_MS * 5 }), true)
  assert.equal(isActive({ visible: false, lastInputAt: 0, playing: [4], now: 1 }), false)
})

test('elapsedSeconds: nothing while hidden, at most 5 s per tick', () => {
  assert.equal(elapsedSeconds(0, 1000, true), 1)
  assert.equal(elapsedSeconds(0, 1000, false), 0)
  assert.equal(elapsedSeconds(0, 3_600_000, true), 5)   // laptop slept
  assert.equal(elapsedSeconds(2000, 1000, true), 0)     // clock went back
})
```

`frontend/src/lib/tracking/ledger.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { MAX_EVENTS_PER_MESSAGE, createLedger } from './ledger.js'

const makeLedger = () => {
  let n = 0
  return createLedger({ pageKey: 'page', newKey: () => `k${++n}`, context: { device: 'desktop' } })
}

test('time accumulates per resource; totals are floored; context sent once', () => {
  const l = makeLedger()
  l.addTime(5, 1.6, true)
  l.addTime(5, 1.6, false)
  l.addTime(6, 2, true)
  const body = l.payload()
  assert.equal(body.page_key, 'page')
  assert.deepEqual(body.visits[0], { visit_key: 'k1', resource_id: 5, active_s: 1, visible_s: 3, context: { device: 'desktop' } })
  assert.equal(body.visits[1].resource_id, 6)
  l.ack(body)
  assert.equal(l.isEmpty(), true)
  l.addTime(5, 1, true)
  assert.deepEqual(l.payload().visits, [{ visit_key: 'k1', resource_id: 5, active_s: 2, visible_s: 4 }])
})

test('changes made while a message is in flight stay pending after ack', () => {
  const l = makeLedger()
  l.addTime(5, 2, true)
  const body = l.payload()
  l.addTime(5, 2, true)
  l.ack(body)
  assert.equal(l.isEmpty(), false)
  assert.equal(l.payload().visits[0].visible_s, 4)
})

test('events link to the visit, mark it pending and clear on ack', () => {
  const l = makeLedger()
  l.addEvent(9, 'pdf_open', {}, new Date('2026-10-01T10:00:00Z'))
  const body = l.payload()
  assert.deepEqual(body.events, [{ event_key: 'k2', visit_key: 'k1', resource_id: 9, type: 'pdf_open', at: '2026-10-01T10:00:00.000Z', data: {} }])
  assert.equal(body.visits[0].visit_key, 'k1')
  l.ack(body)
  assert.equal(l.isEmpty(), true)
})

test('completed and media ride along with the visit', () => {
  const l = makeLedger()
  l.markCompleted(5)
  l.setMedia(5, { covered_pct: 10, furthest_s: 30, duration_s: 300 })
  const [visit] = l.payload().visits
  assert.equal(visit.completed, true)
  assert.deepEqual(visit.media, { covered_pct: 10, furthest_s: 30, duration_s: 300 })
})

test('events are sent in batches of at most 200', () => {
  const l = makeLedger()
  for (let i = 0; i < 250; i++) l.addEvent(1, 'video_play', { position: i })
  const first = l.payload()
  assert.equal(first.events.length, MAX_EVENTS_PER_MESSAGE)
  l.ack(first)
  assert.equal(l.payload().events.length, 50)
})
```

`frontend/src/lib/tracking/context.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { deviceFromUserAgent, pageContext } from './context.js'

test('device type from the user agent', () => {
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148', 5), 'mobile')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (Linux; Android 14; Pixel 8) Mobile Safari/537.36', 5), 'mobile')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (Linux; Android 13; SM-X200) Safari/537.36', 5), 'tablet')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X)', 5), 'tablet')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15', 5), 'tablet')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15', 0), 'desktop')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0', 0), 'desktop')
})

test('page context: language, local hour and offset ahead of UTC', () => {
  const ctx = pageContext('el', new Date(2026, 9, 1, 14, 30), 'Mozilla/5.0 (Windows NT 10.0)', 0)
  assert.equal(ctx.language, 'el')
  assert.equal(ctx.local_hour, 14)
  assert.equal(ctx.tz_offset_minutes, -new Date(2026, 9, 1, 14, 30).getTimezoneOffset())
  assert.equal(ctx.device, 'desktop')
})
```

- [ ] **Step 2: Add the test script and run it to verify it fails**

In `frontend/package.json`, add this after `"check:locales"` in `scripts`:

```json
    "test": "node --test \"src/lib/tracking/*.test.js\"",
```

Run (from `frontend/`): `npm test`
Expected: FAIL with `Cannot find module …/coverage.js`.

- [ ] **Step 3: Implement**

`frontend/src/lib/tracking/coverage.js`:

```js
// Which parts of a video were actually played: [start, end] second ranges.
// Coverage = played seconds ÷ duration, each second counted once.

const MAX_STEP_S = 2 // samples further apart than this (or backwards) are a seek

export function mergeRanges(ranges) {
  const sorted = ranges
    .filter(([a, b]) => b > a)
    .map(([a, b]) => [a, b])
    .sort((x, y) => x[0] - y[0])
  const out = []
  for (const range of sorted) {
    const last = out[out.length - 1]
    if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1])
    else out.push(range)
  }
  return out
}

export function coveredPct(ranges, duration) {
  if (!(duration > 0)) return 0
  const played = mergeRanges(ranges)
    .reduce((sum, [a, b]) => sum + Math.max(0, Math.min(b, duration) - Math.max(a, 0)), 0)
  return Math.min(100, Math.round((played / duration) * 100))
}

// Turns a stream of playback positions into played ranges.
export function createRangeRecorder() {
  const ranges = []
  let current = null
  let furthest = 0
  return {
    sample(position) {
      if (!(position >= 0)) return
      if (current && position >= current[1] && position - current[1] <= MAX_STEP_S) {
        current[1] = position
      } else {
        current = [position, position]
        ranges.push(current)
      }
      furthest = Math.max(furthest, position)
    },
    // Pause / seek / end: the next sample starts a new range.
    cut() { current = null },
    ranges: () => mergeRanges(ranges),
    furthest: () => furthest,
  }
}
```

`frontend/src/lib/tracking/attention.js`:

```js
// Where each second of the activity page goes, and whether it counts as active.

export const IDLE_MS = 60_000      // input older than this no longer makes the learner "active"
export const MAX_TICK_GAP_S = 5    // a longer gap between ticks means timers were frozen (sleep)

export function elapsedSeconds(prevMs, nowMs, visible) {
  if (!visible) return 0
  return Math.max(0, Math.min((nowMs - prevMs) / 1000, MAX_TICK_GAP_S))
}

// A playing video, else the resource the learner last interacted with (if
// recent and still on screen), else the resource filling most of the viewport.
export function pickTarget({ playing, lastResourceInput, visiblePx, now }) {
  if (playing.length) return playing[playing.length - 1]
  if (
    lastResourceInput
    && now - lastResourceInput.at < IDLE_MS
    && (visiblePx.get(lastResourceInput.resourceId) ?? 0) > 0
  ) {
    return lastResourceInput.resourceId
  }
  let best = null
  let bestPx = 0
  for (const [id, px] of visiblePx) {
    if (px > bestPx) { best = id; bestPx = px }
  }
  return best
}

export function isActive({ visible, lastInputAt, playing, now }) {
  return visible && (playing.length > 0 || now - lastInputAt < IDLE_MS)
}
```

`frontend/src/lib/tracking/ledger.js`:

```js
// What the page has measured and the server has not yet confirmed: running
// totals per visit (one visit = one resource during one page visit) and the
// queued events. Totals, not deltas, so a resent message is harmless.

export const MAX_EVENTS_PER_MESSAGE = 200

export function createLedger({ pageKey, newKey, context }) {
  const visits = new Map()   // resourceId → visit
  const pending = new Set()  // resourceIds changed since the last ack
  let events = []

  const visitFor = (resourceId) => {
    let visit = visits.get(resourceId)
    if (!visit) {
      visit = { visit_key: newKey(), resource_id: resourceId, active: 0, visible: 0, completed: false, media: null, contextSent: false }
      visits.set(resourceId, visit)
    }
    pending.add(resourceId)
    return visit
  }

  const entryOf = (visit) => ({
    visit_key: visit.visit_key,
    resource_id: visit.resource_id,
    active_s: Math.floor(visit.active),
    visible_s: Math.floor(visit.visible),
    ...(visit.completed && { completed: true }),
    ...(visit.media && { media: visit.media }),
    ...(!visit.contextSent && { context }),
  })

  return {
    addTime(resourceId, seconds, active) {
      const visit = visitFor(resourceId)
      visit.visible += seconds
      if (active) visit.active += seconds
    },
    markCompleted(resourceId) { visitFor(resourceId).completed = true },
    setMedia(resourceId, media) { visitFor(resourceId).media = media },
    addEvent(resourceId, type, data = {}, at = new Date()) {
      const visit = visitFor(resourceId)
      events.push({ event_key: newKey(), visit_key: visit.visit_key, resource_id: resourceId, type, at: at.toISOString(), data })
    },
    isEmpty: () => pending.size === 0 && events.length === 0,
    // The message to send now; pass it to ack() once the server stored it.
    payload() {
      return {
        page_key: pageKey,
        visits: [...pending].map(id => entryOf(visits.get(id))),
        events: events.slice(0, MAX_EVENTS_PER_MESSAGE),
      }
    },
    ack(sent) {
      for (const entry of sent.visits) {
        const visit = visits.get(entry.resource_id)
        visit.contextSent = true
        const now = entryOf(visit)
        const unchanged = now.active_s === entry.active_s && now.visible_s === entry.visible_s
          && Boolean(now.completed) === Boolean(entry.completed) && now.media === entry.media
        if (unchanged) pending.delete(entry.resource_id)
      }
      const sentKeys = new Set(sent.events.map(e => e.event_key))
      events = events.filter(e => !sentKeys.has(e.event_key))
    },
  }
}
```

`frontend/src/lib/tracking/context.js`:

```js
// Context sent once per visit: no IP address, no precise location.

export function deviceFromUserAgent(ua, touchPoints) {
  if (/iPhone|iPod|Android.+Mobile|Mobi/i.test(ua)) return 'mobile'
  if (/iPad|Tablet|Android/i.test(ua)) return 'tablet'
  if (/Macintosh/.test(ua) && touchPoints > 1) return 'tablet' // iPadOS reports a Mac
  return 'desktop'
}

export function pageContext(
  language,
  now = new Date(),
  ua = globalThis.navigator?.userAgent ?? '',
  touchPoints = globalThis.navigator?.maxTouchPoints ?? 0,
) {
  return {
    language: (language || '').slice(0, 8),
    device: deviceFromUserAgent(ua, touchPoints),
    local_hour: now.getHours(),
    tz_offset_minutes: -now.getTimezoneOffset(), // minutes ahead of UTC (Athens summer = 180)
  }
}
```

In `.github/workflows/ci.yml`, add this to the frontend job after the "Check locale parity" step:

```yaml
      - name: Unit tests — tracking
        run: npm test
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test` then `npm run lint`
Expected: every test passes (`# fail 0`), and lint is clean.

- [ ] **Step 5: Commit**

```bash
git add src/lib/tracking package.json ../.github/workflows/ci.yml
git commit -m "feat: tracker core — attention, video coverage, pending-totals ledger"
git push
```

---

### Task 4: Tracker runtime on the activity page

**Files:**
- Create: `frontend/src/lib/tracking/videoPlayers.js`
- Create: `frontend/src/lib/tracking/tracker.js`
- Create: `frontend/src/lib/tracking/TrackingContext.js`
- Create: `frontend/src/lib/tracking/useActivityTracker.js`
- Modify: `frontend/src/components/lesson/MediaEmbeds.jsx`, `frontend/src/components/lesson/MediaItem.jsx`
- Modify: `frontend/src/components/learner/ResourceView.jsx`
- Modify: `frontend/src/pages/ActivityPage.jsx`
- Modify: `frontend/src/locales/*.json` (one key: `media.download`)

**Interfaces:**
- Consumes: Task 3 modules, and the Task 2 HTTP contract (200 = stored, 204 = stop).
- Produces:
  - `TrackingContext`, plus `useResourceTracking(resourceId) → { event(type, data), video(e) }`, which is a no-op outside the activity page.
  - Video events have the shape `{ type: 'play'|'pause'|'seek'|'ended'|'time', position, duration, from?, to? }`.

- [ ] **Step 1: Video adapters**

`frontend/src/lib/tracking/videoPlayers.js`:

```js
// Report playback of an embedded video as
// { type: 'play'|'pause'|'seek'|'ended'|'time', position, duration, from?, to? }.
// Each tracker returns a function that stops reporting.

const SEEK_JUMP_S = 2

let youTubeReady = null
function loadYouTube() {
  if (!youTubeReady) {
    youTubeReady = new Promise((resolve) => {
      if (window.YT?.Player) { resolve(window.YT); return }
      const previous = window.onYouTubeIframeAPIReady
      window.onYouTubeIframeAPIReady = () => { previous?.(); resolve(window.YT) }
      const script = document.createElement('script')
      script.src = 'https://www.youtube.com/iframe_api'
      script.async = true
      document.head.appendChild(script)
    })
  }
  return youTubeReady
}

let vimeoReady = null
function loadVimeo() {
  if (!vimeoReady) {
    vimeoReady = new Promise((resolve, reject) => {
      if (window.Vimeo?.Player) { resolve(window.Vimeo); return }
      const script = document.createElement('script')
      script.src = 'https://player.vimeo.com/api/player.js'
      script.async = true
      script.onload = () => resolve(window.Vimeo)
      script.onerror = reject
      document.head.appendChild(script)
    })
  }
  return vimeoReady
}

export function trackFileVideo(video, emit) {
  let last = 0
  const state = () => ({
    position: video.currentTime,
    duration: Number.isFinite(video.duration) ? video.duration : 0,
  })
  const handlers = {
    play: () => emit({ type: 'play', ...state() }),
    pause: () => { if (!video.ended) emit({ type: 'pause', ...state() }) },
    seeked: () => { const s = state(); emit({ type: 'seek', from: last, to: s.position, ...s }); last = s.position },
    ended: () => emit({ type: 'ended', ...state() }),
    timeupdate: () => {
      if (video.seeking) return
      const s = state()
      last = s.position
      emit({ type: 'time', ...s })
    },
  }
  Object.entries(handlers).forEach(([name, fn]) => video.addEventListener(name, fn))
  return () => Object.entries(handlers).forEach(([name, fn]) => video.removeEventListener(name, fn))
}

export function trackYouTube(iframe, emit) {
  let player = null
  let timer = null
  let last = 0
  let stopped = false
  const state = () => ({ position: player.getCurrentTime(), duration: player.getDuration() })
  const poll = () => {
    const s = state()
    if (s.position < last || s.position - last > SEEK_JUMP_S + 1) emit({ type: 'seek', from: last, to: s.position, ...s })
    else emit({ type: 'time', ...s })
    last = s.position
  }
  const onStateChange = ({ data }) => {
    if (stopped) return
    const { PLAYING, PAUSED, ENDED } = window.YT.PlayerState
    const s = state()
    clearInterval(timer)
    if (data === PLAYING) {
      if (Math.abs(s.position - last) > SEEK_JUMP_S) emit({ type: 'seek', from: last, to: s.position, ...s })
      emit({ type: 'play', ...s })
      last = s.position
      timer = setInterval(poll, 1000)
    } else if (data === PAUSED) {
      emit({ type: 'pause', ...s })
      last = s.position
    } else if (data === ENDED) {
      emit({ type: 'ended', ...s })
      last = s.position
    }
  }
  loadYouTube()
    .then((YT) => { if (!stopped) player = new YT.Player(iframe, { events: { onStateChange } }) })
    .catch(() => {})
  return () => { stopped = true; clearInterval(timer) }
}

export function trackVimeo(iframe, emit) {
  let player = null
  let last = 0
  let seekFrom = null
  const handlers = {
    play: (d) => { last = d.seconds; emit({ type: 'play', position: d.seconds, duration: d.duration }) },
    pause: (d) => emit({ type: 'pause', position: d.seconds, duration: d.duration }),
    ended: (d) => emit({ type: 'ended', position: d.seconds, duration: d.duration }),
    seeking: () => { if (seekFrom === null) seekFrom = last },
    seeked: (d) => {
      emit({ type: 'seek', from: seekFrom ?? last, to: d.seconds, position: d.seconds, duration: d.duration })
      seekFrom = null
      last = d.seconds
    },
    timeupdate: (d) => {
      if (seekFrom !== null) return
      last = d.seconds
      emit({ type: 'time', position: d.seconds, duration: d.duration })
    },
  }
  let stopped = false
  loadVimeo()
    .then((Vimeo) => {
      if (stopped) return
      player = new Vimeo.Player(iframe)
      Object.entries(handlers).forEach(([name, fn]) => player.on(name, fn))
    })
    .catch(() => {})
  return () => {
    stopped = true
    if (player) Object.keys(handlers).forEach(name => player.off(name))
  }
}
```

- [ ] **Step 2: Tracker and React glue**

`frontend/src/lib/tracking/tracker.js`:

```js
import client from '../../api/client'
import { elapsedSeconds, isActive, pickTarget } from './attention'
import { pageContext } from './context'
import { coveredPct, createRangeRecorder } from './coverage'
import { createLedger } from './ledger'

const TICK_MS = 1000
const FLUSH_MS = 30_000
const ENDPOINT = '/tracking/'
const INPUT_EVENTS = ['pointerdown', 'pointermove', 'keydown', 'wheel', 'touchstart', 'scroll', 'input']

const accessToken = () => localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
const tenth = (n) => Math.round(n * 10) / 10

// Measures how the learner uses the resources of one activity page (elements
// with data-resource-id inside `root`) and sends it every 30 s and when the
// page is hidden or left. See docs/superpowers/specs/2026-10-01-learning-analytics-design.md.
export function createTracker({ root, language }) {
  const newKey = () => crypto.randomUUID()
  const ledger = createLedger({ pageKey: newKey(), newKey, context: pageContext(language) })
  const visiblePx = new Map()   // resourceId → visible height in px
  const playing = []            // resourceIds with a playing video, most recent last
  const recorders = new Map()   // resourceId → played-range recorder
  let lastInputAt = Date.now()
  let lastResourceInput = null
  let lastTick = Date.now()
  let stopped = false
  let inFlight = false

  const onInput = (e) => {
    lastInputAt = Date.now()
    const el = e.target instanceof Element ? e.target.closest('[data-resource-id]') : null
    if (el && root.contains(el)) lastResourceInput = { resourceId: Number(el.dataset.resourceId), at: lastInputAt }
  }

  const tick = () => {
    const now = Date.now()
    const visible = document.visibilityState === 'visible'
    const seconds = elapsedSeconds(lastTick, now, visible)
    lastTick = now
    if (stopped || seconds === 0) return
    const target = pickTarget({ playing, lastResourceInput, visiblePx, now })
    if (target != null) ledger.addTime(target, seconds, isActive({ visible, lastInputAt, playing, now }))
  }

  const post = async (body, keepalive) => {
    if (!keepalive) return (await client.post(ENDPOINT, body)).status
    // keepalive lets the request finish after the page is gone.
    const token = accessToken()
    const res = await fetch(`${client.defaults.baseURL}${ENDPOINT}`, {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', ...(token && { Authorization: `Bearer ${token}` }) },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(String(res.status))
    return res.status
  }

  const flush = async ({ keepalive = false } = {}) => {
    tick()
    if (stopped || ledger.isEmpty() || (inFlight && !keepalive)) return
    const body = ledger.payload()
    inFlight = true
    try {
      const status = await post(body, keepalive)
      if (status === 204) stop() // tracking switched off by an admin
      else ledger.ack(body)
    } catch {
      // Kept: the next message carries the same totals and events.
    } finally {
      inFlight = false
    }
  }

  const onVisibility = () => {
    if (document.visibilityState === 'hidden') flush({ keepalive: true })
    else lastTick = Date.now()
  }
  const onPageHide = () => flush({ keepalive: true })

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      visiblePx.set(Number(entry.target.dataset.resourceId), entry.isIntersecting ? entry.intersectionRect.height : 0)
    }
  }, { threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] })
  root.querySelectorAll('[data-resource-id]').forEach(el => observer.observe(el))

  INPUT_EVENTS.forEach(type => window.addEventListener(type, onInput, { passive: true, capture: true }))
  document.addEventListener('visibilitychange', onVisibility)
  window.addEventListener('pagehide', onPageHide)
  const ticker = setInterval(tick, TICK_MS)
  const flusher = setInterval(() => flush(), FLUSH_MS)

  function stop() {
    stopped = true
    clearInterval(ticker)
    clearInterval(flusher)
    observer.disconnect()
    INPUT_EVENTS.forEach(type => window.removeEventListener(type, onInput, { capture: true }))
    document.removeEventListener('visibilitychange', onVisibility)
    window.removeEventListener('pagehide', onPageHide)
  }

  const setPlaying = (resourceId, on) => {
    const i = playing.indexOf(resourceId)
    if (i >= 0) playing.splice(i, 1)
    if (on) playing.push(resourceId)
  }

  const video = (resourceId, e) => {
    if (stopped) return
    let rec = recorders.get(resourceId)
    if (!rec) { rec = createRangeRecorder(); recorders.set(resourceId, rec) }
    switch (e.type) {
      case 'play':
        setPlaying(resourceId, true)
        rec.sample(e.position)
        ledger.addEvent(resourceId, 'video_play', { position: tenth(e.position) })
        break
      case 'pause':
        setPlaying(resourceId, false)
        rec.cut()
        ledger.addEvent(resourceId, 'video_pause', { position: tenth(e.position) })
        break
      case 'seek':
        rec.cut()
        rec.sample(e.to)
        ledger.addEvent(resourceId, 'video_seek', { from: tenth(e.from), to: tenth(e.to) })
        break
      case 'ended':
        setPlaying(resourceId, false)
        rec.cut()
        ledger.addEvent(resourceId, 'video_ended', { position: tenth(e.position) })
        break
      default:
        rec.sample(e.position)
    }
    if (e.duration > 0) {
      ledger.setMedia(resourceId, {
        covered_pct: coveredPct(rec.ranges(), e.duration),
        furthest_s: Math.round(rec.furthest()),
        duration_s: Math.round(e.duration),
      })
    }
  }

  const api = {
    event: (resourceId, type, data) => { if (!stopped) ledger.addEvent(resourceId, type, data) },
    completed: (resourceId) => { if (!stopped) ledger.markCompleted(resourceId) },
    video,
  }
  return { api, flush, stop }
}
```

`frontend/src/lib/tracking/TrackingContext.js`:

```js
import { createContext, useContext, useMemo } from 'react'

const NOOP = { event() {}, completed() {}, video() {} }

// Provided by the activity page; anywhere else (e.g. authoring preview)
// tracking calls do nothing.
export const TrackingContext = createContext(NOOP)

// Tracking calls bound to one resource.
export function useResourceTracking(resourceId) {
  const api = useContext(TrackingContext)
  return useMemo(() => ({
    event: (type, data) => api.event(resourceId, type, data),
    video: (e) => api.video(resourceId, e),
  }), [api, resourceId])
}
```

`frontend/src/lib/tracking/useActivityTracker.js`:

```js
import { useEffect, useMemo, useRef } from 'react'
import { createTracker } from './tracker'

// Runs a tracker for the activity page while its resources are shown. A new
// page visit (new page_key) starts per activity; leaving sends what is left.
// Returns a stable API that forwards to the live tracker.
export function useActivityTracker(rootRef, activityId, resourceCount, language) {
  const trackerRef = useRef(null)

  useEffect(() => {
    const root = rootRef.current
    if (!root || resourceCount === 0) return undefined
    const tracker = createTracker({ root, language })
    trackerRef.current = tracker
    return () => {
      tracker.flush({ keepalive: true })
      tracker.stop()
      trackerRef.current = null
    }
  }, [rootRef, activityId, resourceCount, language])

  return useMemo(() => ({
    event: (...args) => trackerRef.current?.api.event(...args),
    completed: (...args) => trackerRef.current?.api.completed(...args),
    video: (...args) => trackerRef.current?.api.video(...args),
  }), [])
}
```

- [ ] **Step 3: Embeds report playback, PDF and image use**

Replace the body of `frontend/src/components/lesson/MediaEmbeds.jsx` with the following. `toVideoEmbedUrl` is unchanged.

```jsx
import { useEffect, useRef } from 'react'
import PropTypes from 'prop-types'
import { Video, FileIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { trackFileVideo, trackVimeo, trackYouTube } from '../../lib/tracking/videoPlayers'
import './MediaEmbeds.css'

// eslint-disable-next-line react-refresh/only-export-components
export function toVideoEmbedUrl(url) {
  if (!url) return null
  const yt = url.match(/(?:youtube\.com\/watch\?.*v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{11})/)
  if (yt) return `https://www.youtube.com/embed/${yt[1]}`
  const vimeo = url.match(/vimeo\.com\/(\d+)/)
  if (vimeo) return `https://player.vimeo.com/video/${vimeo[1]}`
  return null
}

const FILE_VIDEO = /\.(mp4|webm|ogg)(\?.*)?$/i
const PLAYER_TRACKERS = { file: trackFileVideo, youtube: trackYouTube, vimeo: trackVimeo }

function videoKind(url, embedUrl) {
  if (embedUrl) return embedUrl.includes('youtube.com') ? 'youtube' : 'vimeo'
  return url && FILE_VIDEO.test(url) ? 'file' : null
}

VideoEmbed.propTypes = { url: PropTypes.string, onPlayerEvent: PropTypes.func }

export function VideoEmbed({ url, onPlayerEvent }) {
  const { t } = useTranslation()
  const playerRef = useRef(null)
  const embedUrl = toVideoEmbedUrl(url)
  const kind = videoKind(url, embedUrl)

  // Report playback when the page tracks it (learner activity page only).
  useEffect(() => {
    if (!onPlayerEvent || !kind || !playerRef.current) return undefined
    return PLAYER_TRACKERS[kind](playerRef.current, onPlayerEvent)
  }, [kind, embedUrl, url, onPlayerEvent])

  if (embedUrl) {
    // The YouTube player API only talks to iframes loaded with enablejsapi=1.
    const src = onPlayerEvent && kind === 'youtube'
      ? `${embedUrl}?enablejsapi=1&origin=${encodeURIComponent(window.location.origin)}`
      : embedUrl
    return (
      <div className="media-video-wrap">
        <iframe
          ref={playerRef}
          src={src}
          title={t('media.videoLessonTitle')}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    )
  }
  if (kind === 'file') {
    return <video ref={playerRef} className="media-video-file" src={url} controls />
  }
  return (
    <div className="media-placeholder">
      <Video size={48} className="media-placeholder-icon" />
      <p className="media-placeholder-label">{t('media.videoPlayer')}</p>
      {url && <a href={url} target="_blank" rel="noreferrer" className="media-open-link">{t('media.openVideo')}</a>}
    </div>
  )
}

PdfEmbed.propTypes = { url: PropTypes.string, onOpen: PropTypes.func, onDownload: PropTypes.func }

export function PdfEmbed({ url, onOpen, onDownload }) {
  const { t } = useTranslation()
  if (!url) {
    return (
      <div className="media-placeholder">
        <FileIcon size={48} className="media-placeholder-icon" />
        <p className="media-placeholder-label">{t('media.pdfDocument')}</p>
      </div>
    )
  }
  return (
    <div className="media-pdf-wrap">
      <iframe src={url} title={t('media.pdfLessonTitle')} />
      <div className="media-pdf-links">
        <a href={url} target="_blank" rel="noreferrer" className="media-open-link media-pdf-fallback" onClick={onOpen}>
          {t('media.openInNewTab')}
        </a>
        <a href={url} download className="media-open-link" onClick={onDownload}>
          {t('media.download')}
        </a>
      </div>
    </div>
  )
}
```

Append to `frontend/src/components/lesson/MediaEmbeds.css`:

```css
.media-pdf-links {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}
```

In `frontend/src/components/lesson/MediaItem.jsx`, accept the optional `tracking` prop and pass it through:

```jsx
export default function MediaItem({ item, tracking }) {
  const { type, url, caption } = item
  if (!url) return null
  const image = <img src={url} alt={caption || ''} className="media-item-image" />
  return (
    <figure className="media-item-view">
      {type === 'video' && <VideoEmbed url={url} onPlayerEvent={tracking?.onPlayerEvent} />}
      {type === 'pdf' && <PdfEmbed url={url} onOpen={tracking?.onPdfOpen} onDownload={tracking?.onPdfDownload} />}
      {type === 'image' && (tracking
        ? <a href={url} target="_blank" rel="noreferrer" onClick={tracking.onImageOpen}>{image}</a>
        : image)}
      {caption && <figcaption className="media-item-caption-text">{caption}</figcaption>}
    </figure>
  )
}

MediaItem.propTypes = {
  item: PropTypes.shape({
    type: PropTypes.string,
    url: PropTypes.string,
    caption: PropTypes.string,
  }).isRequired,
  // Learner page only: report video playback, PDF open/download, image open.
  tracking: PropTypes.shape({
    onPlayerEvent: PropTypes.func,
    onPdfOpen: PropTypes.func,
    onPdfDownload: PropTypes.func,
    onImageOpen: PropTypes.func,
  }),
}
```

Add the `media.download` locale key to all 9 locales, using a Node script in the scratchpad that preserves each file's indent and trailing newline (the same pattern as earlier locale scripts):

| lang | `media.download` |
|---|---|
| en | Download |
| el | Λήψη |
| fr | Télécharger |
| es | Descargar |
| it | Scarica |
| fi | Lataa |
| sv | Ladda ner |
| no | Last ned |
| de | Herunterladen |

- [ ] **Step 4: Wire the learner page**

`frontend/src/components/learner/ResourceView.jsx`:
- Change the React import to `import { useState, useRef, useEffect, useMemo } from 'react'`.
- Add `import { useResourceTracking } from '../../lib/tracking/TrackingContext'`.
- `MediaBody` becomes:

```jsx
function MediaBody({ resource }) {
  const { t } = useTranslation()
  const track = useResourceTracking(resource.id)
  const tracking = useMemo(() => ({
    onPlayerEvent: track.video,
    onPdfOpen: () => track.event('pdf_open'),
    onPdfDownload: () => track.event('pdf_download'),
    onImageOpen: () => track.event('image_open'),
  }), [track])
  if (!resource.url) return <p className="lp-empty">{t('lesson.noContent')}</p>
  return <MediaItem item={{ type: resource.type, url: resource.url, caption: resource.caption }} tracking={tracking} />
}
```

- In `QuizBody`, after the three `useState` lines and before `if (questions.length === 0)`, add:

```jsx
  const track = useResourceTracking(resource.id)
  // When the current question appeared, for the seconds-per-question figure.
  const shownAtRef = useRef(0)
  useEffect(() => { shownAtRef.current = Date.now() }, [currentIdx])
```

- In `handleSelect`, right after `setAnswers(...)`, add:

```jsx
    track.event('quiz_answer', {
      question_index: currentIdx,
      selected: optionIdx,
      seconds_on_question: Math.round((Date.now() - shownAtRef.current) / 100) / 10,
    })
```

- On the root `<section>` of `ResourceView`, add `data-resource-id={resource.id}`.

`frontend/src/pages/ActivityPage.jsx`:
- Imports: add `import { TrackingContext } from '../lib/tracking/TrackingContext'` and `import { useActivityTracker } from '../lib/tracking/useActivityTracker'`.
- Change `const { t } = useTranslation()` in `ActivityPage` to `const { t, i18n } = useTranslation()`.
- After `const scrollPctRef = useRef(0)`, add `const mainRef = useRef(null)`.
- After the `setActivity` `useCallback`, add:

```jsx
  // Time and interaction measurement for learning analytics.
  const tracking = useActivityTracker(mainRef, activityId, activity?.resources?.length ?? 0, i18n.language)
```

- In `completeResource`, right after the `const res = await client.post(...)` statement, add `tracking.completed(resource.id)`. Change its dependency list to `[courseId, activityId, setActivity, tracking]`.
- `<main className="lp-main">` becomes `<main className="lp-main" ref={mainRef}>`.
- Wrap the resources list `resources.map(resource => (<ResourceView …/>))` in `<TrackingContext.Provider value={tracking}> … </TrackingContext.Provider>`. Keep the ternary's empty branch outside the provider:

```jsx
              ) : (
                <TrackingContext.Provider value={tracking}>
                  {resources.map(resource => (
                    <ResourceView
                      key={resource.id}
                      resource={resource}
                      courseId={courseId}
                      activityId={activityId}
                      onComplete={completeResource}
                      onSubmissionChange={handleSubmissionChange}
                    />
                  ))}
                </TrackingContext.Provider>
              )}
```

- [ ] **Step 5: Verify**

From `frontend/`:
- `npm run lint`: clean.
- `npm test`: passes.
- `node scripts/check-locales.mjs`: OK.
- `VITE_API_URL=http://localhost:8000/api npm run build`: succeeds.

Manual browser check, with backend and frontend dev servers running as demo_teacher on an enrolled course's activity:
1. In DevTools Network, a `tracking/` POST appears every ~30 s and when switching tabs. Its body has growing `active_s`/`visible_s`.
2. Leave the mouse untouched for over 60 s: `visible_s` keeps growing while `active_s` stops.
3. Play a YouTube or `.mp4` video: `video_play` and `video_pause` events appear, and `media.covered_pct` grows.
4. Answer a quiz question: a `quiz_answer` event appears with `seconds_on_question`.
5. Click a PDF's "Download": a `pdf_download` event appears.
6. In Django admin, Resource visits and Learning events show rows.

- [ ] **Step 6: Commit**

```bash
git add src/lib/tracking src/components/lesson src/components/learner/ResourceView.jsx src/pages/ActivityPage.jsx src/locales
git commit -m "feat: activity page measures active/on-screen time, video, quiz and PDF use"
git push
```

---

### Task 5: Aggregation, `analytics/learning.py`

**Files:**
- Create: `backend/analytics/learning.py`
- Create: `backend/analytics/tests/fixtures.py`
- Test: `backend/analytics/tests/test_learning.py`

**Interfaces:**
- Consumes: `ResourceVisit`, `LearningEvent`, `ResourceProgress`, `AssignmentSubmission`, `Enrollment`, `LearnerActivityConfig`, `StudyParticipant` (via `user.study`), and `hub.completion.activity_completion(user, course) → (required, completed_required, completed)`.
- Produces:
  - `INACTIVE_DAYS = 14`, `STUCK_VISITS = 3`, `VIDEO_FINISHED_PCT = 90`
  - `display_name(user) → str`, `resource_label(resource) → str`
  - `time_summary(visits) → {'active_s', 'visible_s', 'visits', 'first_opened', 'last_seen'}`
  - `class CourseData(course, now=None)`:
    - attributes: `course, now, modules, activities_of[module_id], resources_of[activity_id], resources, resource_by_id, enrollments, pass_threshold`
    - methods:
      - `resource_visits(uid, rid)`, `activity_visits(uid, aid)`, `module_visits(uid, mid)`, `user_visits(uid)`
      - `events_for(uid, rid, *types)`, `progress_for(uid, rid)`, `completed_at(uid, rid)`, `reached(uid, rid)`
      - `activity_done(uid, aid)`, `module_pct(uid, mid) → int|None`, `video_pct(uid, rid)`, `video_furthest(uid, rid)`
      - `quiz_answers(uid, resource) → [{'index','question','selected_text','correct_text','is_correct','seconds','answered_at'}]`
      - `resource_detail(uid, resource) → dict`, `last_active(enrollment)`, `position(uid) → Resource|None`, `status(enrollment) → 'completed'|'inactive'|'stuck'|'on_track'`, `dropped_at(enrollment) → Resource|None`
  - `content_tree(cd) → {'course', 'learners', 'modules': [...]}`
  - `learner_row(cd, enrollment) → dict`, `learner_rows(cd) → [dict]`
  - `learner_timeline(cd, user_id) → dict | None`

- [ ] **Step 1: Shared fixture**

`backend/analytics/tests/fixtures.py`:

```python
"""One course and six learners shared by the learning-analytics tests.

M1 Basics:   A1 "Read and watch" (text, video) · A2 "Check" (quiz, 2 questions)
M2 Practice: A3 "Apply" (pdf, optional assignment)

ada — active: two page visits on the text (completed), part of the video
bo  — finished the course; quiz answered with timings; PDF opened + downloaded
cy  — inactive: last seen 20 days ago on the video
di  — stuck: 3 visits to the video without finishing it
ev  — stuck: failed the quiz
old — completed the text before tracking began (no visits)
"""
import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from hub.models import (
    Activity,
    AssignmentSubmission,
    Course,
    Enrollment,
    LearningEvent,
    LearningPillar,
    Module,
    Resource,
    ResourceProgress,
    ResourceVisit,
    StudyParticipant,
    UserProfile,
)

NOW = timezone.now()
AGO = NOW - timedelta(minutes=30)


def make_user(username, user_type=UserProfile.UserType.TEACHER, first='', last=''):
    user = User.objects.create_user(
        username=username, password='pass12345', email=f'{username}@example.org',
        first_name=first, last_name=last,
    )
    UserProfile.objects.create(user=user, user_type=user_type)
    return user


def enroll(user, course, days_ago=0, **fields):
    enrollment = Enrollment.objects.create(user=user, course=course, **fields)
    Enrollment.objects.filter(pk=enrollment.pk).update(enrolled_at=NOW - timedelta(days=days_ago))
    enrollment.refresh_from_db()
    return enrollment


def add_visit(user, resource, *, page=None, start=None, active=0, visible=0, **fields):
    start = start or NOW - timedelta(hours=1)
    return ResourceVisit.objects.create(
        user=user, resource=resource, activity=resource.activity,
        module=resource.activity.module, course=resource.activity.module.course,
        visit_key=uuid.uuid4(), page_key=page or uuid.uuid4(),
        started_at=start, last_seen_at=start + timedelta(seconds=visible),
        active_seconds=active, visible_seconds=visible, **fields,
    )


def add_event(user, resource, event_type, at=None, **data):
    return LearningEvent.objects.create(
        user=user, resource=resource, course=resource.activity.module.course,
        event_key=uuid.uuid4(), event_type=event_type, occurred_at=at or AGO, data=data,
    )


def complete(user, resource, at=None, **fields):
    progress = ResourceProgress.objects.create(
        user=user, resource=resource, completed_at=at or AGO, **fields,
    )
    ResourceProgress.objects.filter(pk=progress.pk).update(updated_at=at or AGO)
    return progress


class CourseFixture:
    def __init__(self):
        self.creator = make_user('la_creator', UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-la', order=1)
        self.course = Course.objects.create(
            title='Analytics Course', pillar=pillar, level='beginner', duration_hours=1,
            is_published=True, created_by=self.creator,
        )
        self.m1 = Module.objects.create(course=self.course, title='Basics', order=1)
        self.m2 = Module.objects.create(course=self.course, title='Practice', order=2)
        self.a1 = Activity.objects.create(module=self.m1, title='Read and watch', order=1)
        self.a2 = Activity.objects.create(module=self.m1, title='Check', order=2)
        self.a3 = Activity.objects.create(module=self.m2, title='Apply', order=1)
        self.text = Resource.objects.create(activity=self.a1, type='text', order=1, title='Intro')
        self.video = Resource.objects.create(activity=self.a1, type='video', order=2, title='Clip')
        self.quiz = Resource.objects.create(activity=self.a2, type='quiz', order=1, title='Quiz', quiz_data=[
            {'question': 'Q one', 'options': [{'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': False}]},
            {'question': 'Q two', 'options': [{'text': 'c', 'is_correct': False}, {'text': 'd', 'is_correct': True}]},
        ])
        self.pdf = Resource.objects.create(activity=self.a3, type='pdf', order=1, title='Sheet')
        self.assign = Resource.objects.create(
            activity=self.a3, type='assignment', order=2, title='Task', is_required=False,
        )

        self.ada = make_user('ada', first='Ada', last='Byte')
        self.ada_enr = enroll(self.ada, self.course, progress_pct=0)
        StudyParticipant.objects.create(user=self.ada, in_study=True, consented_at=NOW)
        page1, page2 = uuid.uuid4(), uuid.uuid4()
        add_visit(self.ada, self.text, page=page1, start=NOW - timedelta(hours=3), active=100, visible=120)
        add_visit(self.ada, self.video, page=page1, start=NOW - timedelta(hours=3), active=200, visible=210,
                  media_progress={'covered_pct': 40, 'furthest_s': 120, 'duration_s': 300})
        add_visit(self.ada, self.text, page=page2, start=NOW - timedelta(hours=1), active=50, visible=60,
                  completed_during=True, language='el', device='mobile', local_hour=14, tz_offset_minutes=180)
        complete(self.ada, self.text, engagement_data={'scroll_pct': 80})
        add_event(self.ada, self.video, 'video_play', position=0)
        add_event(self.ada, self.video, 'video_seek', **{'from': 30, 'to': 90})

        self.bo = make_user('bo', first='Bo', last='Bit')
        self.bo_enr = enroll(self.bo, self.course, progress_pct=100, completed_at=NOW - timedelta(days=1))
        add_visit(self.bo, self.text, active=300, visible=320)
        complete(self.bo, self.text)
        complete(self.bo, self.video)
        complete(self.bo, self.quiz, quiz_score=1.0, quiz_answers=[True, True],
                 engagement_data={'quiz_selected': [0, 1]})
        complete(self.bo, self.pdf)
        add_event(self.bo, self.quiz, 'quiz_answer', question_index=0, selected=0, seconds_on_question=12.5)
        add_event(self.bo, self.quiz, 'quiz_answer', question_index=1, selected=1, seconds_on_question=7.5)
        add_event(self.bo, self.pdf, 'pdf_open')
        add_event(self.bo, self.pdf, 'pdf_download')
        AssignmentSubmission.objects.create(
            user=self.bo, lesson=self.a3, resource=self.assign, text='done',
            status=AssignmentSubmission.Status.APPROVED,
        )

        self.cy = make_user('cy')
        self.cy_enr = enroll(self.cy, self.course, days_ago=30)
        add_visit(self.cy, self.video, start=NOW - timedelta(days=20), active=30, visible=40,
                  media_progress={'covered_pct': 10, 'furthest_s': 30, 'duration_s': 300})

        self.di = make_user('di')
        self.di_enr = enroll(self.di, self.course)
        for hours in (5, 4, 3):
            add_visit(self.di, self.video, start=NOW - timedelta(hours=hours), active=20, visible=25)

        self.ev = make_user('ev')
        self.ev_enr = enroll(self.ev, self.course)
        complete(self.ev, self.quiz, quiz_score=0.0, quiz_answers=[False, False],
                 engagement_data={'quiz_selected': [1, 0]})
        add_event(self.ev, self.quiz, 'quiz_answer', question_index=0, selected=1, seconds_on_question=30)

        self.old = make_user('old')
        self.old_enr = enroll(self.old, self.course)
        complete(self.old, self.text)
```

- [ ] **Step 2: Write the failing tests**

`backend/analytics/tests/test_learning.py`:

```python
from django.test import TestCase

from analytics.learning import (
    CourseData,
    content_tree,
    learner_row,
    learner_timeline,
    time_summary,
)
from hub.models import ResourceVisit

from .fixtures import NOW, CourseFixture


class LearningAggregationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.f = CourseFixture()

    def setUp(self):
        self.cd = CourseData(self.f.course, now=NOW)

    def node(self, tree, *path):
        """Walk the content tree by ids: module, activity, resource."""
        node = next(m for m in tree['modules'] if m['id'] == path[0])
        if len(path) > 1:
            node = next(a for a in node['activities'] if a['id'] == path[1])
        if len(path) > 2:
            node = next(r for r in node['resources'] if r['id'] == path[2])
        return node

    def test_time_summary_counts_page_visits_once(self):
        t = time_summary(ResourceVisit.objects.filter(user=self.f.ada))
        self.assertEqual((t['active_s'], t['visible_s'], t['visits']), (350, 390, 2))

    def test_statuses(self):
        status = {e.user.username: self.cd.status(e) for e in self.cd.enrollments}
        self.assertEqual(status, {
            'ada': 'on_track', 'bo': 'completed', 'cy': 'inactive',
            'di': 'stuck', 'ev': 'stuck', 'old': 'on_track',
        })

    def test_text_resource_stats(self):
        f = self.f
        stats = self.node(content_tree(self.cd), f.m1.id, f.a1.id, f.text.id)['stats']
        # Reached by ada, bo (visits) and old (progress only); median over measured.
        self.assertEqual(stats, {'reached': 3, 'done': 3, 'median_active_s': 225, 'mean_active_s': 225, 'dropped': 0})

    def test_video_resource_stats_and_notes(self):
        f = self.f
        node = self.node(content_tree(self.cd), f.m1.id, f.a1.id, f.video.id)
        self.assertEqual(node['stats'], {'reached': 4, 'done': 1, 'median_active_s': 60, 'mean_active_s': 97, 'dropped': 1})
        self.assertEqual(node['notes'], {'avg_watched_pct': 25, 'typical_stop_s': 75})

    def test_quiz_notes(self):
        f = self.f
        node = self.node(content_tree(self.cd), f.m1.id, f.a2.id, f.quiz.id)
        self.assertIsNone(node['stats']['median_active_s'])  # reached, but never measured
        self.assertEqual(node['notes'], {
            'avg_score_pct': 50,
            'hardest_question': {'number': 1, 'question': 'Q one', 'pct_correct': 50},
            'avg_seconds_per_question': 16.7,
        })

    def test_pdf_and_assignment_notes(self):
        f = self.f
        tree = content_tree(self.cd)
        self.assertEqual(self.node(tree, f.m2.id, f.a3.id, f.pdf.id)['notes'], {'opened': 1, 'downloaded': 1})
        self.assertEqual(
            self.node(tree, f.m2.id, f.a3.id, f.assign.id)['notes'],
            {'submitted': 1, 'approved': 1, 'waiting': 0, 'changes_requested': 0},
        )

    def test_activity_and_module_aggregate_children(self):
        f = self.f
        tree = content_tree(self.cd)
        self.assertEqual(self.node(tree, f.m1.id, f.a1.id)['stats'],
                         {'reached': 5, 'done': 1, 'median_active_s': 180, 'mean_active_s': 185, 'dropped': 1})
        m1 = self.node(tree, f.m1.id)['stats']
        self.assertEqual((m1['reached'], m1['done'], m1['dropped']), (6, 1, 1))
        self.assertEqual(tree['learners'], 6)

    def test_learner_row(self):
        row = learner_row(self.cd, self.f.ada_enr)
        self.assertEqual((row['active_s'], row['visible_s'], row['visits']), (350, 390, 2))
        self.assertEqual(row['position']['resource_id'], self.f.text.id)
        self.assertEqual(row['status'], 'on_track')
        self.assertTrue(row['tracked'])
        self.assertFalse(learner_row(self.cd, self.f.old_enr)['tracked'])

    def test_timeline(self):
        f = self.f
        tl = learner_timeline(self.cd, f.ada.id)
        m1 = tl['modules'][0]
        self.assertEqual((m1['active_s'], m1['visits'], m1['pct']), (350, 2, 0))
        text = m1['activities'][0]['resources'][0]
        self.assertEqual((text['active_s'], text['visits'], text['scroll_pct']), (150, 2, 80))
        self.assertIsNotNone(text['completed_at'])
        video = m1['activities'][0]['resources'][1]
        self.assertEqual(video['video_pct'], 40)
        self.assertIsNone(learner_timeline(self.cd, f.creator.id))

    def test_timeline_quiz_answers_with_timing(self):
        quiz = learner_timeline(self.cd, self.f.ev.id)['modules'][0]['activities'][1]['resources'][0]
        first, second = quiz['quiz_answers']
        self.assertEqual((first['selected_text'], first['is_correct'], first['seconds']), ('b', False, 30))
        self.assertEqual((second['selected_text'], second['is_correct'], second['seconds']), ('c', False, None))

    def test_not_tracked_learner(self):
        text = learner_timeline(self.cd, self.f.old.id)['modules'][0]['activities'][0]['resources'][0]
        self.assertEqual(text['visits'], 0)
        self.assertIsNotNone(text['completed_at'])

    def test_quiz_answers_survive_edited_quiz(self):
        f = self.f
        f.quiz.quiz_data = f.quiz.quiz_data[:1]
        f.quiz.quiz_data[0]['options'] = f.quiz.quiz_data[0]['options'][:1]
        f.quiz.save()
        cd = CourseData(f.course, now=NOW)
        answers = cd.quiz_answers(f.ev.id, cd.resource_by_id[f.quiz.id])
        self.assertEqual(len(answers), 1)
        self.assertIsNone(answers[0]['selected_text'])   # picked option 1 no longer exists
        self.assertFalse(answers[0]['is_correct'])       # stored result still wins
        content_tree(cd)                                 # and nothing else breaks
```

The expected numbers are checked by hand against the fixture:
- A1 median: the measured activity times are ada 350, bo 300, cy 30, di 60. Sorted, that is 30, 60, 300, 350, so the median is (60 + 300) / 2 = 180 and the mean is 740 / 4 = 185.
- Video mean: (200 + 30 + 60) / 3 = 96.7, which rounds to 97.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `"$UV" run manage.py test analytics.tests.test_learning -v 2`
Expected: ImportError, `No module named 'analytics.learning'`.

- [ ] **Step 4: Implement**

`backend/analytics/learning.py`:

```python
"""Per-course learning analytics from measured visits and events — see
docs/superpowers/specs/2026-10-01-learning-analytics-design.md.

CourseData loads one course's structure and every enrolled learner's data
once; the web endpoints (content tree, learners, timeline) and the Excel
workbook all read from it, so they always agree. Module and activity times
are sums over resource visits."""
from collections import defaultdict
from datetime import timedelta
from statistics import mean, median

from django.utils import timezone

from hub.completion import activity_completion
from hub.models import (
    Activity,
    AssignmentSubmission,
    Enrollment,
    LearnerActivityConfig,
    LearningEvent,
    Module,
    Resource,
    ResourceProgress,
    ResourceVisit,
)

INACTIVE_DAYS = 14       # no activity for this long → inactive (and "dropped here")
STUCK_VISITS = 3         # this many visits to one resource without finishing it → stuck
VIDEO_FINISHED_PCT = 90  # watching less than this counts as stopping early


def display_name(user):
    return user.get_full_name() or user.username


def resource_label(resource):
    return resource.title or f'{resource.get_type_display()} {resource.order}'


def time_summary(visits):
    """Active / on-screen seconds, page visits and first / last time of visits."""
    visits = list(visits)
    return {
        'active_s': sum(v.active_seconds for v in visits),
        'visible_s': sum(v.visible_seconds for v in visits),
        'visits': len({v.page_key for v in visits}),
        'first_opened': min((v.started_at for v in visits), default=None),
        'last_seen': max((v.last_seen_at for v in visits), default=None),
    }


class CourseData:
    def __init__(self, course, now=None):
        self.course = course
        self.now = now or timezone.now()
        self.modules = list(Module.objects.filter(course=course).order_by('order', 'id'))
        self.activities_of = defaultdict(list)
        for activity in Activity.objects.filter(module__course=course).order_by('order', 'id'):
            self.activities_of[activity.module_id].append(activity)
        self.resources = list(
            Resource.objects.filter(activity__module__course=course)
            .select_related('activity__module')
            .order_by('activity__module__order', 'activity__module_id', 'activity__order',
                      'activity_id', 'order', 'id')
        )
        self.resources_of = defaultdict(list)
        for resource in self.resources:
            self.resources_of[resource.activity_id].append(resource)
        self.resource_by_id = {r.id: r for r in self.resources}

        self.enrollments = list(
            Enrollment.objects.filter(course=course)
            .select_related('user__profile__subject', 'user__study')
            .order_by('user__first_name', 'user__last_name', 'user__username')
        )
        user_ids = [e.user_id for e in self.enrollments]

        self._visits = defaultdict(list)
        for v in ResourceVisit.objects.filter(course=course, user_id__in=user_ids).order_by('started_at'):
            for key in (('u', v.user_id), ('r', v.user_id, v.resource_id),
                        ('a', v.user_id, v.activity_id), ('m', v.user_id, v.module_id)):
                self._visits[key].append(v)
        self._events = defaultdict(list)
        for e in LearningEvent.objects.filter(course=course, user_id__in=user_ids).order_by('occurred_at', 'id'):
            self._events[(e.user_id, e.resource_id)].append(e)
        self._progress = {}
        self._progress_of = defaultdict(list)
        for p in ResourceProgress.objects.filter(resource__activity__module__course=course, user_id__in=user_ids):
            self._progress[(p.user_id, p.resource_id)] = p
            self._progress_of[p.user_id].append(p)
        self.submissions = {}
        for s in (AssignmentSubmission.objects
                  .filter(resource__activity__module__course=course, user_id__in=user_ids)
                  .order_by('submitted_at')):
            self.submissions[(s.user_id, s.resource_id)] = s  # latest wins
        self._submissions_of = defaultdict(list)
        for s in self.submissions.values():
            self._submissions_of[s.user_id].append(s)
        self._completion = {e.user_id: activity_completion(e.user, course) for e in self.enrollments}
        self.pass_threshold = LearnerActivityConfig.get().quiz_pass_threshold

    # ── Raw lookups ──────────────────────────────────────────────────────────

    def user_visits(self, uid):
        return self._visits.get(('u', uid), [])

    def resource_visits(self, uid, rid):
        return self._visits.get(('r', uid, rid), [])

    def activity_visits(self, uid, aid):
        return self._visits.get(('a', uid, aid), [])

    def module_visits(self, uid, mid):
        return self._visits.get(('m', uid, mid), [])

    def events_for(self, uid, rid, *types):
        events = self._events.get((uid, rid), [])
        return [e for e in events if e.event_type in types] if types else events

    def progress_for(self, uid, rid):
        return self._progress.get((uid, rid))

    def completed_at(self, uid, rid):
        progress = self.progress_for(uid, rid)
        return progress.completed_at if progress else None

    def reached(self, uid, rid):
        """Opened at least once: a measured visit, or progress from before tracking."""
        return bool(self.resource_visits(uid, rid)) or (uid, rid) in self._progress

    # ── Completion ───────────────────────────────────────────────────────────

    def activity_done(self, uid, aid):
        return aid in self._completion[uid][2]

    def module_pct(self, uid, mid):
        """% of the module's required activities done (all activities when none
        is required); None for a module without activities."""
        required, completed_required, completed = self._completion[uid]
        ids = [a.id for a in self.activities_of.get(mid, [])]
        req = [i for i in ids if i in required]
        if req:
            return round(100 * sum(i in completed_required for i in req) / len(req))
        if ids:
            return round(100 * sum(i in completed for i in ids) / len(ids))
        return None

    # ── Per-resource detail ──────────────────────────────────────────────────

    def video_pct(self, uid, rid):
        """% of the video played in the learner's best single visit."""
        values = [v.media_progress.get('covered_pct') for v in self.resource_visits(uid, rid)]
        values = [x for x in values if isinstance(x, (int, float))]
        return max(values) if values else None

    def video_furthest(self, uid, rid):
        values = [v.media_progress.get('furthest_s') for v in self.resource_visits(uid, rid)]
        values = [x for x in values if isinstance(x, (int, float))]
        return max(values) if values else None

    def quiz_answers(self, uid, resource):
        """One dict per answered question of a quiz. Stored results win over
        recomputation, so a quiz edited later still reports what was scored."""
        progress = self.progress_for(uid, resource.id)
        done = progress is not None and progress.completed_at is not None
        selected = (progress.engagement_data or {}).get('quiz_selected', []) if progress else []
        stored = (progress.quiz_answers or []) if progress else []
        timing = {}
        for e in self.events_for(uid, resource.id, LearningEvent.Type.QUIZ_ANSWER):
            if isinstance(e.data.get('question_index'), int):
                timing[e.data['question_index']] = e  # the last answer wins
        rows = []
        for i, question in enumerate(resource.quiz_data or []):
            event = timing.get(i)
            if not done and event is None:
                continue
            options = question.get('options', [])
            pick = selected[i] if i < len(selected) else (event.data.get('selected') if event else None)
            valid = isinstance(pick, int) and 0 <= pick < len(options)
            if i < len(stored):
                right = bool(stored[i])
            elif valid:
                right = bool(options[pick].get('is_correct'))
            else:
                right = None
            rows.append({
                'index': i,
                'question': question.get('question', ''),
                'selected_text': options[pick].get('text') if valid else None,
                'correct_text': next((o.get('text') for o in options if o.get('is_correct')), None),
                'is_correct': right,
                'seconds': event.data.get('seconds_on_question') if event else None,
                'answered_at': event.occurred_at if event else (progress.completed_at if done else None),
            })
        return rows

    def resource_detail(self, uid, resource):
        progress = self.progress_for(uid, resource.id)
        engagement = (progress.engagement_data or {}) if progress else {}
        submission = self.submissions.get((uid, resource.id))
        kind = resource.type

        def count(*types):
            return len(self.events_for(uid, resource.id, *types))

        return {
            **time_summary(self.resource_visits(uid, resource.id)),
            'completed_at': progress.completed_at if progress else None,
            'quiz_score': progress.quiz_score if progress and kind == 'quiz' else None,
            'video_pct': self.video_pct(uid, resource.id) if kind == 'video' else None,
            'scroll_pct': engagement.get('scroll_pct') if kind == 'text' else None,
            'pdf_opened': count('pdf_open') if kind == 'pdf' else None,
            'pdf_downloaded': count('pdf_download') if kind == 'pdf' else None,
            'image_opened': count('image_open') if kind == 'image' else None,
            'assignment_status': submission.status if submission else None,
        }

    # ── Learner state ────────────────────────────────────────────────────────

    def last_active(self, enrollment):
        uid = enrollment.user_id
        times = [enrollment.enrolled_at]
        times += [v.last_seen_at for v in self.user_visits(uid)]
        times += [p.updated_at for p in self._progress_of.get(uid, [])]
        times += [s.submitted_at for s in self._submissions_of.get(uid, [])]
        return max(times)

    def position(self, uid):
        """The resource the learner touched last (visit or progress)."""
        moments = [(v.last_seen_at, v.resource_id) for v in self.user_visits(uid)]
        moments += [(p.updated_at, p.resource_id) for p in self._progress_of.get(uid, [])]
        if not moments:
            return None
        return self.resource_by_id.get(max(moments, key=lambda m: m[0])[1])

    def _stuck(self, uid):
        for resource in self.resources:
            if (self.completed_at(uid, resource.id) is None
                    and len(self.resource_visits(uid, resource.id)) >= STUCK_VISITS):
                return True
            progress = self.progress_for(uid, resource.id)
            if (resource.type == 'quiz' and progress and progress.quiz_score is not None
                    and progress.quiz_score < self.pass_threshold):
                return True
        return False

    def status(self, enrollment):
        if enrollment.completed_at is not None or enrollment.progress_pct >= 100:
            return 'completed'
        if self.now - self.last_active(enrollment) >= timedelta(days=INACTIVE_DAYS):
            return 'inactive'
        if self._stuck(enrollment.user_id):
            return 'stuck'
        return 'on_track'

    def dropped_at(self, enrollment):
        """Where an unfinished learner with no activity for 14+ days stopped."""
        return self.position(enrollment.user_id) if self.status(enrollment) == 'inactive' else None


# ── Content tree ─────────────────────────────────────────────────────────────


def _level_stats(rows):
    """rows: one (reached, done, active_s or None when unmeasured, dropped) per learner."""
    times = [active for reached, _, active, _ in rows if reached and active is not None]
    return {
        'reached': sum(1 for reached, *_ in rows if reached),
        'done': sum(1 for _, done, *_ in rows if done),
        'median_active_s': round(median(times)) if times else None,
        'mean_active_s': round(mean(times)) if times else None,
        'dropped': sum(1 for *_, dropped in rows if dropped),
    }


def _measured(visits):
    return sum(v.active_seconds for v in visits) if visits else None


def _avg(values, digits=0):
    if not values:
        return None
    value = round(mean(values), digits)
    return int(value) if digits == 0 else value


def resource_notes(cd, resource):
    uids = [e.user_id for e in cd.enrollments]
    kind = resource.type
    if kind == 'text':
        scrolls = []
        for uid in uids:
            progress = cd.progress_for(uid, resource.id)
            value = (progress.engagement_data or {}).get('scroll_pct') if progress else None
            if isinstance(value, (int, float)):
                scrolls.append(value)
        return {'avg_scroll_pct': _avg(scrolls)}
    if kind == 'video':
        watched, stops = [], []
        for uid in uids:
            pct = cd.video_pct(uid, resource.id)
            if pct is None:
                continue
            watched.append(pct)
            furthest = cd.video_furthest(uid, resource.id)
            if pct < VIDEO_FINISHED_PCT and furthest is not None:
                stops.append(furthest)
        return {'avg_watched_pct': _avg(watched), 'typical_stop_s': round(median(stops)) if stops else None}
    if kind == 'quiz':
        scores = [p.quiz_score for uid in uids
                  if (p := cd.progress_for(uid, resource.id)) and p.quiz_score is not None]
        right_by_question, seconds = defaultdict(list), []
        for uid in uids:
            for answer in cd.quiz_answers(uid, resource):
                if answer['is_correct'] is not None:
                    right_by_question[answer['index']].append(answer['is_correct'])
                if isinstance(answer['seconds'], (int, float)):
                    seconds.append(answer['seconds'])
        hardest = min(right_by_question.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), default=None)
        return {
            'avg_score_pct': _avg([s * 100 for s in scores]),
            'hardest_question': {
                'number': hardest[0] + 1,
                'question': resource.quiz_data[hardest[0]].get('question', ''),
                'pct_correct': round(100 * sum(hardest[1]) / len(hardest[1])),
            } if hardest else None,
            'avg_seconds_per_question': _avg(seconds, 1),
        }
    if kind in ('pdf', 'image'):
        opened = sum(1 for uid in uids if cd.events_for(uid, resource.id, f'{kind}_open'))
        if kind == 'image':
            return {'opened': opened}
        downloaded = sum(1 for uid in uids if cd.events_for(uid, resource.id, 'pdf_download'))
        return {'opened': opened, 'downloaded': downloaded}
    if kind == 'assignment':
        statuses = [s.status for uid in uids if (s := cd.submissions.get((uid, resource.id)))]
        status = AssignmentSubmission.Status
        return {
            'submitted': len(statuses),
            'approved': statuses.count(status.APPROVED),
            'waiting': statuses.count(status.PENDING),
            'changes_requested': statuses.count(status.CHANGES_REQUESTED),
        }
    return {}


def content_tree(cd):
    uids = [e.user_id for e in cd.enrollments]
    drops = {e.user_id: cd.dropped_at(e) for e in cd.enrollments}
    reached = {uid: {r.id for r in cd.resources if cd.reached(uid, r.id)} for uid in uids}

    def dropped(uid, test):
        return drops[uid] is not None and test(drops[uid])

    modules = []
    for module in cd.modules:
        activities = []
        for activity in cd.activities_of.get(module.id, []):
            resources = []
            for r in cd.resources_of.get(activity.id, []):
                rows = [(r.id in reached[uid], cd.completed_at(uid, r.id) is not None,
                         _measured(cd.resource_visits(uid, r.id)),
                         dropped(uid, lambda d, r=r: d.id == r.id)) for uid in uids]
                resources.append({
                    'id': r.id, 'title': resource_label(r), 'type': r.type, 'order': r.order,
                    'is_required': r.is_required, 'stats': _level_stats(rows),
                    'notes': resource_notes(cd, r),
                })
            ids = {r.id for r in cd.resources_of.get(activity.id, [])}
            rows = [(bool(ids & reached[uid]), cd.activity_done(uid, activity.id),
                     _measured(cd.activity_visits(uid, activity.id)),
                     dropped(uid, lambda d, a=activity: d.activity_id == a.id)) for uid in uids]
            activities.append({
                'id': activity.id, 'title': activity.title, 'order': activity.order,
                'stats': _level_stats(rows), 'resources': resources,
            })
        ids = {r.id for a in cd.activities_of.get(module.id, []) for r in cd.resources_of.get(a.id, [])}
        rows = [(bool(ids & reached[uid]), cd.module_pct(uid, module.id) == 100,
                 _measured(cd.module_visits(uid, module.id)),
                 dropped(uid, lambda d, m=module: d.activity.module_id == m.id)) for uid in uids]
        modules.append({
            'id': module.id, 'title': module.title, 'order': module.order,
            'stats': _level_stats(rows), 'activities': activities,
        })
    return {
        'course': {'id': cd.course.id, 'title': cd.course.title},
        'learners': len(uids),
        'modules': modules,
    }


# ── Learners ─────────────────────────────────────────────────────────────────


def _position_dict(resource):
    if resource is None:
        return None
    return {
        'resource_id': resource.id,
        'resource': resource_label(resource),
        'activity': resource.activity.title,
        'module': resource.activity.module.title,
    }


def learner_row(cd, enrollment):
    user = enrollment.user
    totals = time_summary(cd.user_visits(user.id))
    return {
        'user_id': user.id,
        'name': display_name(user),
        'email': user.email,
        'enrolled_at': enrollment.enrolled_at,
        'completed_at': enrollment.completed_at,
        'progress_pct': enrollment.progress_pct,
        'active_s': totals['active_s'],
        'visible_s': totals['visible_s'],
        'visits': totals['visits'],
        'tracked': bool(cd.user_visits(user.id)),
        'last_active': cd.last_active(enrollment),
        'position': _position_dict(cd.position(user.id)),
        'status': cd.status(enrollment),
    }


def learner_rows(cd):
    return [learner_row(cd, e) for e in cd.enrollments]


def learner_timeline(cd, user_id):
    """One learner's module → activity → resource tree, or None if not enrolled."""
    enrollment = next((e for e in cd.enrollments if e.user_id == user_id), None)
    if enrollment is None:
        return None
    modules = []
    for module in cd.modules:
        activities = []
        for activity in cd.activities_of.get(module.id, []):
            resources = [{
                'id': r.id, 'title': resource_label(r), 'type': r.type, 'order': r.order,
                'is_required': r.is_required,
                **cd.resource_detail(user_id, r),
                'quiz_answers': cd.quiz_answers(user_id, r) if r.type == 'quiz' else None,
            } for r in cd.resources_of.get(activity.id, [])]
            activities.append({
                'id': activity.id, 'title': activity.title, 'order': activity.order,
                'done': cd.activity_done(user_id, activity.id),
                **time_summary(cd.activity_visits(user_id, activity.id)),
                'resources': resources,
            })
        modules.append({
            'id': module.id, 'title': module.title, 'order': module.order,
            'pct': cd.module_pct(user_id, module.id),
            **time_summary(cd.module_visits(user_id, module.id)),
            'activities': activities,
        })
    return {'learner': learner_row(cd, enrollment), 'modules': modules}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `"$UV" run manage.py test analytics.tests.test_learning -v 2`
Expected: all 13 tests pass. If a hand-computed expectation disagrees, re-derive it from the fixture's docstring numbers before touching the code. The fixture is the spec's rules applied by hand.

- [ ] **Step 6: Lint and commit**

```bash
"$UV" run ruff check hub analytics
git add analytics/learning.py analytics/tests/fixtures.py analytics/tests/test_learning.py
git commit -m "feat: learning analytics aggregation — content tree, learner status, timeline"
git push
```

---

### Task 6: Course analytics API (content, learners, timeline)

**Files:**
- Modify: `backend/analytics/views.py`
- Modify: `backend/analytics/urls.py`
- Test: `backend/analytics/tests/test_learning_api.py`

**Interfaces:**
- Consumes: from Task 5, `CourseData`, `content_tree`, `learner_rows`, `learner_timeline`.
- Produces:
  - `GET /api/analytics/courses/<pk>/content/` (`analytics-course-content`) → the `content_tree` dict.
  - `GET /api/analytics/courses/<pk>/learners/` (`analytics-course-learners`) → `{'course': {id, title}, 'learners': [learner_row…]}`.
  - `GET /api/analytics/courses/<pk>/learners/<user_id>/` (`analytics-course-learner`) → the `learner_timeline` dict, or 404.
  - All three return 404 for a course outside `scoped_courses` and 403 for non-creators.

- [ ] **Step 1: Write the failing tests**

`backend/analytics/tests/test_learning_api.py`:

```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, UserProfile

from .fixtures import CourseFixture, make_user


class CourseAnalyticsApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.f = CourseFixture()
        cls.outsider = make_user('la_other', UserProfile.UserType.CONTENT_CREATOR)
        cls.admin = make_user('la_admin', UserProfile.UserType.ADMIN)

    def url(self, name, **kw):
        return reverse(name, kwargs={'pk': self.f.course.id, **kw})

    def test_author_gets_content_tree(self):
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(self.url('analytics-course-content'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['learners'], 6)
        self.assertEqual([m['title'] for m in res.data['modules']], ['Basics', 'Practice'])

    def test_learners_list_with_status(self):
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(self.url('analytics-course-learners'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        status_by_name = {row['name']: row['status'] for row in res.data['learners']}
        self.assertEqual(status_by_name['Ada Byte'], 'on_track')
        self.assertEqual(status_by_name['di'], 'stuck')

    def test_learner_timeline(self):
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(self.url('analytics-course-learner', user_id=self.f.ada.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['learner']['email'], 'ada@example.org')
        self.assertEqual(len(res.data['modules']), 2)

    def test_timeline_404_for_someone_not_enrolled(self):
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(self.url('analytics-course-learner', user_id=self.outsider.id))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_creator_gets_404(self):
        self.client.force_authenticate(self.outsider)
        for name in ('analytics-course-content', 'analytics-course-learners'):
            self.assertEqual(self.client.get(self.url(name)).status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_forbidden(self):
        self.client.force_authenticate(self.f.ada)
        self.assertEqual(self.client.get(self.url('analytics-course-content')).status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_sees_any_course(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.url('analytics-course-learners')).status_code, status.HTTP_200_OK)

    def test_empty_course(self):
        empty = Course.objects.create(
            title='Empty', pillar=self.f.course.pillar, level='beginner', duration_hours=1,
            is_published=False, created_by=self.f.creator,
        )
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(reverse('analytics-course-content', kwargs={'pk': empty.id}))
        self.assertEqual(res.data, {'course': {'id': empty.id, 'title': 'Empty'}, 'learners': 0, 'modules': []})
        res = self.client.get(reverse('analytics-course-learners', kwargs={'pk': empty.id}))
        self.assertEqual(res.data['learners'], [])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `"$UV" run manage.py test analytics.tests.test_learning_api -v 2`
Expected: `NoReverseMatch` errors.

- [ ] **Step 3: Implement**

In `backend/analytics/views.py`, add `from .learning import CourseData, content_tree, learner_rows, learner_timeline` beside the other local imports, then append:

```python
class _CourseAnalyticsView(APIView):
    """Base for one course's analytics: 404 outside the viewer's scope."""

    permission_classes = [IsContentCreator]

    def course_or_none(self, request, pk):
        return scoped_courses(request.user).filter(pk=pk).first()


def _not_found():
    return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


class CourseContentView(_CourseAnalyticsView):
    """GET — module → activity → resource tree with reached / done / typical
    time / dropped-here and notes per resource type."""

    def get(self, request, pk):
        course = self.course_or_none(request, pk)
        if course is None:
            return _not_found()
        return Response(content_tree(CourseData(course)))


class CourseLearnersView(_CourseAnalyticsView):
    """GET — one row per enrolled learner with time, position and status."""

    def get(self, request, pk):
        course = self.course_or_none(request, pk)
        if course is None:
            return _not_found()
        return Response({
            'course': {'id': course.id, 'title': course.title},
            'learners': learner_rows(CourseData(course)),
        })


class CourseLearnerTimelineView(_CourseAnalyticsView):
    """GET — one learner's timeline through the course."""

    def get(self, request, pk, user_id):
        course = self.course_or_none(request, pk)
        timeline = learner_timeline(CourseData(course), user_id) if course else None
        if timeline is None:
            return _not_found()
        return Response(timeline)
```

In `backend/analytics/urls.py`, import the three views and add:

```python
    path('courses/<int:pk>/content/', CourseContentView.as_view(), name='analytics-course-content'),
    path('courses/<int:pk>/learners/', CourseLearnersView.as_view(), name='analytics-course-learners'),
    path('courses/<int:pk>/learners/<int:user_id>/', CourseLearnerTimelineView.as_view(), name='analytics-course-learner'),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `"$UV" run manage.py test analytics -v 2`
Expected: all analytics tests pass, old and new.

- [ ] **Step 5: Lint and commit**

```bash
"$UV" run ruff check hub analytics
git add analytics/views.py analytics/urls.py analytics/tests/test_learning_api.py
git commit -m "feat: course analytics API — content tree, learners, learner timeline"
git push
```

---

### Task 7: Excel workbook (9 sheets) and exports

**Files:**
- Create: `backend/analytics/workbook.py`
- Modify: `backend/analytics/views.py`: add `CourseExportView`; `AnalyticsExportView` now uses the new builder; remove `AnalyticsCourseTeachersView` and the `reports` import.
- Modify: `backend/analytics/urls.py`: add `courses/<pk>/export/`; remove `courses/<pk>/teachers/`.
- Delete: `backend/analytics/reports.py`, `backend/analytics/tests/test_teacher_detail.py`. Their export tests are replaced below, and the drill-down is replaced by the Learners tab.
- Test: `backend/analytics/tests/test_workbook.py`

**Interfaces:**
- Consumes: from Task 5, `CourseData`, `learner_row`, `time_summary`, `display_name`, `resource_label`.
- Produces:
  - `build_learning_workbook(courses, now=None) → openpyxl.Workbook`, with sheets `SHEET_NAMES` in order.
  - `GET /api/analytics/courses/<pk>/export/` (`analytics-course-export`).
  - `GET /api/analytics/export/?ids=` (unchanged URL, new content).

- [ ] **Step 1: Write the failing tests**

`backend/analytics/tests/test_workbook.py`:

```python
from io import BytesIO

from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APITestCase

from analytics.workbook import SHEET_NAMES, build_learning_workbook
from hub.models import Course, UserProfile

from .fixtures import NOW, CourseFixture, make_user


def rows(ws):
    """Sheet rows as dicts keyed by the header row."""
    values = list(ws.values)
    return [dict(zip(values[0], row)) for row in values[1:]]


def by_learner(ws, name):
    return [r for r in rows(ws) if r['Learner'] == name]


class WorkbookTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.f = CourseFixture()

    def setUp(self):
        self.wb = build_learning_workbook([self.f.course], now=NOW)

    def test_sheet_order(self):
        self.assertEqual(self.wb.sheetnames, SHEET_NAMES)
        self.assertEqual(SHEET_NAMES, [
            'README', 'Overview', 'Learners', 'Modules', 'Activities', 'Resources',
            'Visits', 'Quiz answers', 'Events',
        ])

    def test_learners_sheet(self):
        [ada] = by_learner(self.wb['Learners'], 'Ada Byte')
        self.assertEqual(ada['Email'], 'ada@example.org')
        self.assertEqual((ada['Active s'], ada['On-screen s'], ada['Visits']), (350, 390, 2))
        self.assertEqual(ada['Status'], 'on_track')
        self.assertEqual(ada['Study participant (consented)'], 'yes')
        self.assertEqual(ada['Course ID'], self.f.course.id)
        [di] = by_learner(self.wb['Learners'], 'di')
        self.assertEqual((di['Status'], di['Study participant (consented)']), ('stuck', 'no'))

    def test_overview_is_wide_in_minutes(self):
        ws = self.wb['Overview']
        header = [c.value for c in ws[1]]
        self.assertIn('M1 Basics — active min', header)
        self.assertIn('M2 Practice — % complete', header)
        [ada] = by_learner(ws, 'Ada Byte')
        self.assertEqual(ada['M1 Basics — active min'], 5.8)   # 350 s
        self.assertEqual(ada['Total active min'], 5.8)

    def test_modules_and_activities_sheets(self):
        m1 = next(r for r in by_learner(self.wb['Modules'], 'Ada Byte') if r['Module'] == 'Basics')
        self.assertEqual((m1['Active s'], m1['Visits'], m1['Activities done'], m1['Activities total']), (350, 2, 0, 2))
        a1 = next(r for r in by_learner(self.wb['Activities'], 'Bo Bit') if r['Activity'] == 'Read and watch')
        self.assertEqual((a1['Resources done'], a1['Resources total'], a1['Done']), (2, 2, 'yes'))
        self.assertTrue(a1['Completed at'].endswith('Z'))

    def test_resources_sheet_one_row_per_learner_and_resource(self):
        ws = self.wb['Resources']
        self.assertEqual(len(rows(ws)), 6 * 5)
        text = next(r for r in by_learner(ws, 'Ada Byte') if r['Resource'] == 'Intro')
        self.assertEqual((text['Active s'], text['Scroll %'], text['Type'], text['Required']), (150, 80, 'text', 'yes'))
        pdf = next(r for r in by_learner(ws, 'Bo Bit') if r['Resource'] == 'Sheet')
        self.assertEqual((pdf['PDF opened'], pdf['PDF downloaded']), (1, 1))
        old_text = next(r for r in by_learner(ws, 'old') if r['Resource'] == 'Intro')
        self.assertEqual((old_text['Visits'], old_text['Active s']), (0, 0))
        self.assertTrue(old_text['Completed at'])

    def test_visits_sheet(self):
        visits = by_learner(self.wb['Visits'], 'Ada Byte')
        self.assertEqual(len(visits), 3)
        mobile = next(v for v in visits if v['Device'] == 'mobile')
        self.assertEqual((mobile['Language'], mobile['Local hour'], mobile['TZ offset (min)'], mobile['Completed during']),
                         ('el', 14, 180, 'yes'))
        self.assertTrue(mobile['Started at'].endswith('Z'))

    def test_quiz_answers_sheet(self):
        answers = by_learner(self.wb['Quiz answers'], 'Bo Bit')
        self.assertEqual([(a['Question #'], a['Option picked'], a['Right'], a['Seconds on question']) for a in answers],
                         [(1, 'a', 'yes', 12.5), (2, 'd', 'yes', 7.5)])

    def test_events_sheet(self):
        seek = next(e for e in by_learner(self.wb['Events'], 'Ada Byte') if e['Event'] == 'video_seek')
        self.assertEqual((seek['From s'], seek['To s']), (30, 90))

    def test_workbook_for_empty_course(self):
        empty = Course.objects.create(title='Empty', pillar=self.f.course.pillar, level='beginner', duration_hours=1)
        wb = build_learning_workbook([empty], now=NOW)
        self.assertEqual(wb.sheetnames, SHEET_NAMES)
        self.assertEqual(rows(wb['Learners']), [])


class ExportEndpointTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.f = CourseFixture()
        cls.outsider = make_user('la_other', UserProfile.UserType.CONTENT_CREATOR)

    def test_course_export(self):
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(reverse('analytics-course-export', kwargs={'pk': self.f.course.id}))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('spreadsheetml', res['Content-Type'])
        self.assertIn('analytics-course-analytics.xlsx', res['Content-Disposition'])
        wb = load_workbook(BytesIO(res.getvalue()))
        self.assertEqual(wb.sheetnames, SHEET_NAMES)

    def test_course_export_scoped(self):
        self.client.force_authenticate(self.outsider)
        res = self.client.get(reverse('analytics-course-export', kwargs={'pk': self.f.course.id}))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_all_courses_export_uses_same_sheets(self):
        self.client.force_authenticate(self.f.creator)
        res = self.client.get(reverse('analytics-export'), {'ids': str(self.f.course.id)})
        wb = load_workbook(BytesIO(res.getvalue()))
        self.assertEqual(wb.sheetnames, SHEET_NAMES)
        self.assertEqual(len(rows(wb['Learners'])), 6)

    def test_all_courses_export_with_nothing_in_scope(self):
        self.client.force_authenticate(self.outsider)
        wb = load_workbook(BytesIO(self.client.get(reverse('analytics-export')).getvalue()))
        self.assertEqual(wb.sheetnames, SHEET_NAMES)
        self.assertEqual(rows(wb['Learners']), [])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `"$UV" run manage.py test analytics.tests.test_workbook -v 2`
Expected: ImportError, `No module named 'analytics.workbook'`.

- [ ] **Step 3: Implement**

`backend/analytics/workbook.py`:

```python
"""Learning analytics workbook — see the spec's "Excel workbook" section.

Long-format sheets (one row per learner × item, per visit, per event) for
statistical analysis, plus a wide Overview sheet. Seconds are plain numbers,
Overview uses minutes; timestamps are UTC ISO-8601 text. The all-courses
export uses the same sheets, with course columns on every row."""
from datetime import UTC

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from .learning import (
    INACTIVE_DAYS,
    STUCK_VISITS,
    CourseData,
    display_name,
    learner_row,
    resource_label,
    time_summary,
)

SHEET_NAMES = [
    'README', 'Overview', 'Learners', 'Modules', 'Activities', 'Resources',
    'Visits', 'Quiz answers', 'Events',
]

BASE = ['Course ID', 'Course', 'Learner ID', 'Learner']

HEADERS = {
    'Learners': BASE + [
        'Email', 'Enrolled at', 'Last active', 'Completed at', 'Progress %', 'Active s',
        'On-screen s', 'Visits', 'Status', 'Current position', 'Subject', 'Teaching level',
        'Role at school', 'Country', 'Interface language', 'Competency score',
        'Study participant (consented)',
    ],
    'Modules': BASE + [
        'Module ID', 'Module order', 'Module', 'Active s', 'On-screen s', 'Visits',
        'Activities done', 'Activities total', '% complete', 'First opened', 'Last seen',
        'Completed at',
    ],
    'Activities': BASE + [
        'Module ID', 'Module order', 'Module', 'Activity ID', 'Activity order', 'Activity',
        'Active s', 'On-screen s', 'Visits', 'Resources done', 'Resources total', 'Done',
        'First opened', 'Last seen', 'Completed at',
    ],
    'Resources': BASE + [
        'Module ID', 'Module order', 'Activity ID', 'Activity order', 'Activity',
        'Resource ID', 'Resource order', 'Resource', 'Type', 'Required', 'Active s',
        'On-screen s', 'Visits', 'First opened', 'Completed at', 'Quiz score %',
        'Video % watched', 'Scroll %', 'PDF opened', 'PDF downloaded', 'Image opened',
        'Assignment status',
    ],
    'Visits': BASE + [
        'Module ID', 'Module', 'Activity ID', 'Activity', 'Resource ID', 'Resource', 'Type',
        'Visit ID', 'Page visit', 'Started at', 'Last seen at', 'Active s', 'On-screen s',
        'Completed during', 'Language', 'Device', 'Local hour', 'TZ offset (min)',
        'Video % this visit',
    ],
    'Quiz answers': BASE + [
        'Module ID', 'Activity ID', 'Activity', 'Resource ID', 'Quiz', 'Question #',
        'Question', 'Option picked', 'Correct option', 'Right', 'Seconds on question',
        'Answered at',
    ],
    'Events': BASE + [
        'Resource ID', 'Resource', 'Type', 'Event', 'Time', 'Position s', 'From s', 'To s',
        'Question #', 'Option picked', 'Seconds on question',
    ],
}

README = [
    'AIDEA learning analytics export',
    'All times are UTC in ISO 8601 (…Z). Durations are seconds, except the Overview sheet (minutes).',
    'Active time: the page was visible and the learner scrolled, typed, clicked, touched or moved the pointer within the last 60 seconds, or a video was playing.',
    'On-screen time: the page was visible. Active time is never more than on-screen time.',
    'Each second of an activity page is credited to one resource: a playing video, else the resource last interacted with, else the one filling most of the screen.',
    'Module and activity times are sums of their resources. Visits = separate openings of an activity page.',
    'Typical time on the website = median among learners who opened the item and have measured time.',
    f'Status: completed = course finished; inactive = no activity for {INACTIVE_DAYS}+ days; '
    f'stuck = {STUCK_VISITS}+ visits to one resource without finishing it, or a quiz score below '
    'the pass threshold; on_track = otherwise. Checked in that order.',
    'Not tracked: work done before time tracking began has completion dates and scores but 0 visits and no time.',
    'Video % watched: share of the video actually played, in the best single visit.',
    "TZ offset: minutes ahead of UTC on the learner's device (Athens in summer = 180).",
    'Study participant (consented): the learner joined the AIDEA research study and gave consent.',
    'Sheets: Overview (one row per learner, wide), Learners, Modules, Activities, Resources '
    '(learner × item), Visits (raw), Quiz answers, Events (raw).',
]


def iso(dt):
    return dt.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ') if dt else ''


def yes_no(value):
    return 'yes' if value else 'no'


def blank(value):
    return '' if value is None else value


def _minutes(seconds):
    return round(seconds / 60, 1)


def _base(cd, user):
    return [cd.course.id, cd.course.title, user.id, display_name(user)]


def _profile_columns(user):
    profile = getattr(user, 'profile', None)
    study = getattr(user, 'study', None)
    if profile is None:
        values = ['', '', '', '', '', '']
    else:
        values = [
            profile.subject.name if profile.subject else '',
            profile.teaching_level, profile.school_role, profile.country, profile.language,
            profile.competency_score,
        ]
    consented = bool(study and study.in_study and study.consented_at)
    return values + [yes_no(consented)]


def _learners(cd):
    for e in cd.enrollments:
        row = learner_row(cd, e)
        pos = row['position']
        position = f"{pos['module']} › {pos['activity']} › {pos['resource']}" if pos else ''
        yield _base(cd, e.user) + [
            e.user.email, iso(e.enrolled_at), iso(row['last_active']), iso(e.completed_at),
            e.progress_pct, row['active_s'], row['visible_s'], row['visits'], row['status'],
            position,
        ] + _profile_columns(e.user)


def _latest_completion(cd, uid, resources):
    times = [cd.completed_at(uid, r.id) for r in resources]
    return max((t for t in times if t), default=None)


def _modules(cd):
    for e in cd.enrollments:
        uid = e.user_id
        for m in cd.modules:
            t = time_summary(cd.module_visits(uid, m.id))
            activities = cd.activities_of.get(m.id, [])
            pct = cd.module_pct(uid, m.id)
            resources = [r for a in activities for r in cd.resources_of.get(a.id, [])]
            yield _base(cd, e.user) + [
                m.id, m.order, m.title, t['active_s'], t['visible_s'], t['visits'],
                sum(cd.activity_done(uid, a.id) for a in activities), len(activities), blank(pct),
                iso(t['first_opened']), iso(t['last_seen']),
                iso(_latest_completion(cd, uid, resources)) if pct == 100 else '',
            ]


def _activities(cd):
    for e in cd.enrollments:
        uid = e.user_id
        for m in cd.modules:
            for a in cd.activities_of.get(m.id, []):
                t = time_summary(cd.activity_visits(uid, a.id))
                resources = cd.resources_of.get(a.id, [])
                done = cd.activity_done(uid, a.id)
                yield _base(cd, e.user) + [
                    m.id, m.order, m.title, a.id, a.order, a.title, t['active_s'], t['visible_s'],
                    t['visits'], sum(cd.completed_at(uid, r.id) is not None for r in resources),
                    len(resources), yes_no(done), iso(t['first_opened']), iso(t['last_seen']),
                    iso(_latest_completion(cd, uid, resources)) if done else '',
                ]


def _resources(cd):
    for e in cd.enrollments:
        for r in cd.resources:
            d = cd.resource_detail(e.user_id, r)
            a = r.activity
            score = d['quiz_score']
            yield _base(cd, e.user) + [
                a.module_id, a.module.order, a.id, a.order, a.title, r.id, r.order,
                resource_label(r), r.type, yes_no(r.is_required), d['active_s'], d['visible_s'],
                d['visits'], iso(d['first_opened']), iso(d['completed_at']),
                round(score * 100) if score is not None else '', blank(d['video_pct']),
                blank(d['scroll_pct']), blank(d['pdf_opened']), blank(d['pdf_downloaded']),
                blank(d['image_opened']), blank(d['assignment_status']),
            ]


def _visits(cd):
    for e in cd.enrollments:
        for v in cd.user_visits(e.user_id):
            r = cd.resource_by_id.get(v.resource_id)
            if r is None:
                continue
            yield _base(cd, e.user) + [
                r.activity.module_id, r.activity.module.title, r.activity_id, r.activity.title,
                r.id, resource_label(r), r.type, v.id, str(v.page_key), iso(v.started_at),
                iso(v.last_seen_at), v.active_seconds, v.visible_seconds,
                yes_no(v.completed_during), v.language, v.device, blank(v.local_hour),
                blank(v.tz_offset_minutes), blank(v.media_progress.get('covered_pct')),
            ]


def _quiz_answers(cd):
    for e in cd.enrollments:
        for r in cd.resources:
            if r.type != 'quiz':
                continue
            for answer in cd.quiz_answers(e.user_id, r):
                right = answer['is_correct']
                yield _base(cd, e.user) + [
                    r.activity.module_id, r.activity_id, r.activity.title, r.id,
                    resource_label(r), answer['index'] + 1, answer['question'],
                    blank(answer['selected_text']), blank(answer['correct_text']),
                    '' if right is None else yes_no(right), blank(answer['seconds']),
                    iso(answer['answered_at']),
                ]


def _events(cd):
    for e in cd.enrollments:
        for r in cd.resources:
            for ev in cd.events_for(e.user_id, r.id):
                data = ev.data or {}
                index = data.get('question_index')
                yield _base(cd, e.user) + [
                    r.id, resource_label(r), r.type, ev.event_type, iso(ev.occurred_at),
                    blank(data.get('position')), blank(data.get('from')), blank(data.get('to')),
                    index + 1 if isinstance(index, int) else '', blank(data.get('selected')),
                    blank(data.get('seconds_on_question')),
                ]


ROWS = {
    'Learners': _learners, 'Modules': _modules, 'Activities': _activities,
    'Resources': _resources, 'Visits': _visits, 'Quiz answers': _quiz_answers,
    'Events': _events,
}


def _overview(ws, data):
    """Wide sheet: one row per learner; per module active minutes and % complete.
    With one course the module titles are in the headers; with several, the
    columns are by module position (titles are on the Modules sheet)."""
    width = max((len(cd.modules) for cd in data), default=0)
    single = data[0] if len(data) == 1 else None
    header = list(BASE)
    for i in range(width):
        label = f'M{i + 1} {single.modules[i].title}' if single else f'M{i + 1}'
        header += [f'{label} — active min', f'{label} — % complete']
    header += ['Total active min', 'Total on-screen min', 'Progress %', 'Status']
    _write_header(ws, header)
    for cd in data:
        for e in cd.enrollments:
            row = _base(cd, e.user)
            for i in range(width):
                if i < len(cd.modules):
                    m = cd.modules[i]
                    t = time_summary(cd.module_visits(e.user_id, m.id))
                    row += [_minutes(t['active_s']), blank(cd.module_pct(e.user_id, m.id))]
                else:
                    row += ['', '']
            t = time_summary(cd.user_visits(e.user_id))
            row += [_minutes(t['active_s']), _minutes(t['visible_s']), e.progress_pct, cd.status(e)]
            ws.append(row)


def _write_header(ws, header):
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = 'A2'
    for col in range(1, len(header) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 16


def build_learning_workbook(courses, now=None):
    data = [CourseData(course, now) for course in courses]
    wb = Workbook()
    readme = wb.active
    readme.title = 'README'
    for line in README:
        readme.append([line])
    readme['A1'].font = Font(bold=True)
    readme.column_dimensions['A'].width = 120
    _overview(wb.create_sheet('Overview'), data)
    for name, rows in ROWS.items():
        ws = wb.create_sheet(name)
        _write_header(ws, HEADERS[name])
        for cd in data:
            for row in rows(cd):
                ws.append(row)
    return wb
```

`backend/analytics/views.py`:
- Remove `from .reports import build_analytics_workbook, build_course_teacher_report`.
- Add `from .workbook import build_learning_workbook`.
- Delete the `AnalyticsCourseTeachersView` class.
- Add a helper and change `AnalyticsExportView.get`'s body to the following:

```python
def _xlsx_response(workbook, name):
    buffer = BytesIO()
    workbook.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type=XLSX_MIME)
    response['Content-Disposition'] = f'attachment; filename="{name}"'
    return response
```

```python
    def get(self, request):
        courses = scoped_courses(request.user).order_by('title')
        # Optional subset selected in the export dialog: ?ids=1,2,3
        ids_param = request.query_params.get('ids')
        if ids_param:
            wanted = {int(x) for x in ids_param.split(',') if x.strip().isdigit()}
            courses = courses.filter(id__in=wanted)
        name = f'{slugify(request.user.username) or "analytics"}-analytics.xlsx'
        return _xlsx_response(build_learning_workbook(courses), name)
```

Update `AnalyticsExportView`'s docstring to `"""GET — the learning analytics workbook for every course in scope (or ?ids=)."""`. Then append:

```python
class CourseExportView(_CourseAnalyticsView):
    """GET — the learning analytics workbook for one course."""

    def get(self, request, pk):
        course = self.course_or_none(request, pk)
        if course is None:
            return _not_found()
        name = f'{slugify(course.title) or "course"}-analytics.xlsx'
        return _xlsx_response(build_learning_workbook([course]), name)
```

`backend/analytics/urls.py`:
- Remove the `AnalyticsCourseTeachersView` import and its `courses/<int:pk>/teachers/` route.
- Import `CourseExportView`.
- Add: `path('courses/<int:pk>/export/', CourseExportView.as_view(), name='analytics-course-export'),`

Delete the replaced files: `git rm analytics/reports.py analytics/tests/test_teacher_detail.py`.

Check nothing else imports them: `grep -rn "analytics.reports\|from .reports\|teachers/" backend frontend/src --include=*.py --include=*.js --include=*.jsx`. The frontend's use of `teachers/` is removed in Task 8.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `"$UV" run manage.py test analytics -v 2`
Expected: all pass, including `test_analytics.py::test_export_subset_by_ids`.

- [ ] **Step 5: Lint and commit**

```bash
"$UV" run ruff check hub analytics
git add analytics
git commit -m "feat: 9-sheet learning analytics workbook; per-course and all-courses export"
git push
```

---

### Task 8: Analytics course page (web)

**Files:**
- Create: `frontend/src/components/analytics/format.js`, `download.js`
- Create: `frontend/src/components/analytics/ContentTree.jsx`, `LearnersTable.jsx`, `LearnerTimeline.jsx`
- Create: `frontend/src/pages/AnalyticsCoursePage.jsx`, `AnalyticsCoursePage.css`
- Modify: `frontend/src/App.jsx` (route)
- Modify: `frontend/src/pages/AnalyticsPage.jsx`, `AnalyticsPage.css`
- Modify: `frontend/src/locales/*.json` (9 files)

**Interfaces:**
- Consumes: the Task 6 endpoint shapes and Task 7's `/analytics/courses/<id>/export/`.
- Produces: the route `/analytics/courses/:id`.

- [ ] **Step 1: Helpers**

`frontend/src/components/analytics/format.js`:

```js
// Display helpers for the learning analytics pages.

// Seconds as "1 h 05 min", "4 min 10 s" or "35 s"; null → "—".
export function formatDuration(seconds, t) {
  if (seconds == null) return '—'
  const s = Math.round(seconds)
  if (s >= 3600) {
    return t('analytics.course.dur.hm', { h: Math.floor(s / 3600), m: String(Math.floor((s % 3600) / 60)).padStart(2, '0') })
  }
  if (s >= 60) return t('analytics.course.dur.ms', { m: Math.floor(s / 60), s: s % 60 })
  return t('analytics.course.dur.s', { s })
}

// A position in a video as m:ss.
export function formatClock(seconds) {
  const s = Math.round(seconds)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

export function formatDate(iso, language) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(language, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// Time for an item a learner has: measured, "not tracked" (done before
// tracking began) or "—" (never opened).
export function itemTime(seconds, visits, completedAt, t) {
  if (visits > 0) return formatDuration(seconds, t)
  return completedAt ? t('analytics.course.notTracked') : '—'
}
```

`frontend/src/components/analytics/download.js`:

```js
import client from '../../api/client'

// Fetch an xlsx export with the auth header and save it as `filename`.
export async function downloadXlsx(path, params, filename) {
  const res = await client.get(path, { params, responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
```

- [ ] **Step 2: Content tree**

`frontend/src/components/analytics/ContentTree.jsx`:

```jsx
import { useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { ChevronDown, ChevronRight } from 'lucide-react'
import TypeIcon from '../learner/TypeIcon'
import { formatClock, formatDuration } from './format'

const statsShape = PropTypes.shape({
  reached: PropTypes.number,
  done: PropTypes.number,
  median_active_s: PropTypes.number,
  mean_active_s: PropTypes.number,
  dropped: PropTypes.number,
})

StatCells.propTypes = { stats: statsShape.isRequired, learners: PropTypes.number.isRequired }
function StatCells({ stats, learners }) {
  const { t } = useTranslation()
  const pct = (n) => (learners ? Math.round((n / learners) * 100) : 0)
  let typical = '—'
  if (stats.median_active_s != null) typical = formatDuration(stats.median_active_s, t)
  else if (stats.reached) typical = t('analytics.course.notTracked')
  return (
    <>
      <td className="acp-num">{stats.reached} <span className="acp-pct">({pct(stats.reached)}%)</span></td>
      <td className="acp-num">{stats.done} <span className="acp-pct">({pct(stats.done)}%)</span></td>
      <td
        className="acp-num"
        title={stats.mean_active_s != null ? t('analytics.course.average', { value: formatDuration(stats.mean_active_s, t) }) : undefined}
      >
        {typical}
      </td>
      <td className="acp-num">{stats.dropped || '—'}</td>
    </>
  )
}

ResourceNotes.propTypes = { type: PropTypes.string.isRequired, notes: PropTypes.object.isRequired }
function ResourceNotes({ type, notes }) {
  const { t } = useTranslation()
  const parts = []
  if (type === 'text' && notes.avg_scroll_pct != null) parts.push(t('analytics.course.notes.scroll', { pct: notes.avg_scroll_pct }))
  if (type === 'video') {
    if (notes.avg_watched_pct != null) parts.push(t('analytics.course.notes.watched', { pct: notes.avg_watched_pct }))
    if (notes.typical_stop_s != null) parts.push(t('analytics.course.notes.stop', { time: formatClock(notes.typical_stop_s) }))
  }
  if (type === 'quiz') {
    if (notes.avg_score_pct != null) parts.push(t('analytics.course.notes.score', { pct: notes.avg_score_pct }))
    if (notes.hardest_question) {
      parts.push(t('analytics.course.notes.hardest', { n: notes.hardest_question.number, pct: notes.hardest_question.pct_correct }))
    }
    if (notes.avg_seconds_per_question != null) parts.push(t('analytics.course.notes.perQuestion', { s: notes.avg_seconds_per_question }))
  }
  if ((type === 'pdf' || type === 'image') && notes.opened) parts.push(t('analytics.course.notes.opened', { count: notes.opened }))
  if (type === 'pdf' && notes.downloaded) parts.push(t('analytics.course.notes.downloaded', { count: notes.downloaded }))
  if (type === 'assignment' && notes.submitted) parts.push(t('analytics.course.notes.assignment', notes))
  if (!parts.length) return null
  return <p className="acp-notes" title={notes.hardest_question?.question}>{parts.join(' · ')}</p>
}

Chevron.propTypes = { open: PropTypes.bool.isRequired }
function Chevron({ open }) {
  return open ? <ChevronDown size={14} /> : <ChevronRight size={14} />
}

ContentTree.propTypes = {
  tree: PropTypes.shape({
    learners: PropTypes.number.isRequired,
    modules: PropTypes.arrayOf(PropTypes.object).isRequired,
  }).isRequired,
}

export default function ContentTree({ tree }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(() => new Set(tree.modules.map(m => `m${m.id}`)))
  const toggle = (key) => setOpen((prev) => {
    const next = new Set(prev)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    return next
  })

  if (!tree.modules.length) return <p className="acp-empty">{t('analytics.course.noContent')}</p>

  return (
    <div className="acp-table-wrap">
      <table className="acp-table">
        <thead>
          <tr>
            <th>{t('analytics.course.col.item')}</th>
            <th className="acp-num">{t('analytics.course.col.reached')}</th>
            <th className="acp-num">{t('analytics.course.col.done')}</th>
            <th className="acp-num">{t('analytics.course.col.typical')}</th>
            <th className="acp-num">{t('analytics.course.col.dropped')}</th>
          </tr>
        </thead>
        <tbody>
          {tree.modules.map(m => (
            <ModuleRows key={m.id} module={m} open={open} toggle={toggle} learners={tree.learners} />
          ))}
        </tbody>
      </table>
    </div>
  )
}

ModuleRows.propTypes = {
  module: PropTypes.object.isRequired,
  open: PropTypes.instanceOf(Set).isRequired,
  toggle: PropTypes.func.isRequired,
  learners: PropTypes.number.isRequired,
}
function ModuleRows({ module, open, toggle, learners }) {
  const { t } = useTranslation()
  const mk = `m${module.id}`
  return (
    <>
      <tr className="acp-row acp-row--module" onClick={() => toggle(mk)}>
        <td><Chevron open={open.has(mk)} /> {t('common.moduleLabel', { order: module.order, title: module.title })}</td>
        <StatCells stats={module.stats} learners={learners} />
      </tr>
      {open.has(mk) && module.activities.map(a => {
        const ak = `a${a.id}`
        return [
          <tr key={ak} className="acp-row acp-row--activity" onClick={() => toggle(ak)}>
            <td><Chevron open={open.has(ak)} /> {a.title}</td>
            <StatCells stats={a.stats} learners={learners} />
          </tr>,
          ...(open.has(ak) ? a.resources.map(r => (
            <tr key={`r${r.id}`} className="acp-row acp-row--resource">
              <td>
                <span className="acp-resource-title"><TypeIcon type={r.type} size={14} /> {r.title}</span>
                <ResourceNotes type={r.type} notes={r.notes} />
              </td>
              <StatCells stats={r.stats} learners={learners} />
            </tr>
          )) : []),
        ]
      })}
    </>
  )
}
```

- [ ] **Step 3: Learners table and timeline**

`frontend/src/components/analytics/LearnersTable.jsx`:

```jsx
import { useMemo, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { formatDate, formatDuration } from './format'

const STATUSES = ['completed', 'on_track', 'stuck', 'inactive']
const COLUMNS = [
  { key: 'name', label: 'learner' },
  { key: 'progress_pct', label: 'progress' },
  { key: 'active_s', label: 'active' },
  { key: 'visible_s', label: 'onScreen' },
  { key: 'visits', label: 'visits' },
  { key: 'last_active', label: 'lastActive' },
  { key: 'position', label: 'position' },
  { key: 'status', label: 'status' },
]

function compare(key, dir) {
  return (a, b) => {
    const x = key === 'position' ? a.position?.resource ?? '' : a[key]
    const y = key === 'position' ? b.position?.resource ?? '' : b[key]
    if (x == null) return 1
    if (y == null) return -1
    const order = typeof x === 'string' ? x.localeCompare(y) : x - y
    return order * dir
  }
}

LearnersTable.propTypes = {
  learners: PropTypes.arrayOf(PropTypes.object).isRequired,
  onOpen: PropTypes.func.isRequired,
}

export default function LearnersTable({ learners, onOpen }) {
  const { t, i18n } = useTranslation()
  const [sort, setSort] = useState({ key: 'name', dir: 1 })
  const [status, setStatus] = useState('all')
  const counts = useMemo(() => Object.fromEntries(STATUSES.map(s => [s, learners.filter(l => l.status === s).length])), [learners])
  const rows = useMemo(
    () => learners.filter(l => status === 'all' || l.status === status).sort(compare(sort.key, sort.dir)),
    [learners, status, sort],
  )
  const sortBy = (key) => setSort(prev => ({ key, dir: prev.key === key ? -prev.dir : 1 }))

  if (!learners.length) return <p className="acp-empty">{t('analytics.course.empty')}</p>

  return (
    <>
      <select className="acp-status-filter" value={status} onChange={e => setStatus(e.target.value)}>
        <option value="all">{t('analytics.course.status.all')} ({learners.length})</option>
        {STATUSES.map(s => <option key={s} value={s}>{t(`analytics.course.status.${s}`)} ({counts[s]})</option>)}
      </select>
      <div className="acp-table-wrap">
        <table className="acp-table">
          <thead>
            <tr>
              {COLUMNS.map(c => (
                <th key={c.key} className="acp-sortable" onClick={() => sortBy(c.key)}>
                  {t(`analytics.course.col.${c.label}`)}
                  {sort.key === c.key && (sort.dir > 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(l => (
              <tr key={l.user_id} className="acp-row acp-row--learner" onClick={() => onOpen(l.user_id)}>
                <td>
                  <span className="acp-learner-name">{l.name}</span>
                  <span className="acp-learner-email">{l.email}</span>
                </td>
                <td className="acp-num">{l.progress_pct}%</td>
                <td className="acp-num">{l.tracked ? formatDuration(l.active_s, t) : t('analytics.course.notTracked')}</td>
                <td className="acp-num">{l.tracked ? formatDuration(l.visible_s, t) : '—'}</td>
                <td className="acp-num">{l.visits}</td>
                <td>{formatDate(l.last_active, i18n.language)}</td>
                <td className="acp-position">{l.position ? `${l.position.activity} › ${l.position.resource}` : '—'}</td>
                <td><span className={`acp-status acp-status--${l.status}`}>{t(`analytics.course.status.${l.status}`)}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
```

`frontend/src/components/analytics/LearnerTimeline.jsx`:

```jsx
import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, CheckCircle2, Circle, XCircle } from 'lucide-react'
import client from '../../api/client'
import TypeIcon from '../learner/TypeIcon'
import { formatDate, formatDuration, itemTime } from './format'

ResourceDetails.propTypes = { r: PropTypes.object.isRequired }
function ResourceDetails({ r }) {
  const { t } = useTranslation()
  const bits = []
  if (r.quiz_score != null) bits.push(t('analytics.course.detail.score', { pct: Math.round(r.quiz_score * 100) }))
  if (r.video_pct != null) bits.push(t('analytics.course.detail.watched', { pct: r.video_pct }))
  if (r.scroll_pct != null) bits.push(t('analytics.course.detail.scrolled', { pct: r.scroll_pct }))
  if (r.pdf_opened) bits.push(t('analytics.course.detail.opened'))
  if (r.image_opened) bits.push(t('analytics.course.detail.opened'))
  if (r.pdf_downloaded) bits.push(t('analytics.course.detail.downloaded'))
  if (r.assignment_status) bits.push(t(`analytics.course.detail.assignment.${r.assignment_status}`))
  return (
    <>
      {bits.length > 0 && <span>{bits.join(' · ')}</span>}
      {r.quiz_answers?.length > 0 && (
        <ol className="acp-answers">
          {r.quiz_answers.map(a => (
            <li key={a.index}>
              {a.is_correct ? <CheckCircle2 size={13} className="acp-right" /> : <XCircle size={13} className="acp-wrong" />}
              <span className="acp-answer-q">{a.question}</span>
              <span className="acp-answer-a">{a.selected_text ?? '—'}</span>
              {a.seconds != null && <span className="acp-answer-t">{t('analytics.course.detail.answerTime', { s: a.seconds })}</span>}
            </li>
          ))}
        </ol>
      )}
    </>
  )
}

LearnerTimeline.propTypes = {
  courseId: PropTypes.string.isRequired,
  userId: PropTypes.number.isRequired,
  onBack: PropTypes.func.isRequired,
}

export default function LearnerTimeline({ courseId, userId, onBack }) {
  const { t, i18n } = useTranslation()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get(`/analytics/courses/${courseId}/learners/${userId}/`)
      .then(res => setData(res.data))
      .catch(() => setError(t('analytics.loadError')))
  }, [courseId, userId, t])

  const back = (
    <button className="acp-back" onClick={onBack}><ArrowLeft size={14} /> {t('analytics.course.backToLearners')}</button>
  )
  if (error) return <>{back}<p className="page-error">{error}</p></>
  if (!data) return <>{back}<p className="page-loading">{t('common.loading')}</p></>

  const { learner } = data
  return (
    <div className="acp-timeline">
      {back}
      <div className="acp-timeline-head">
        <h2>{learner.name}</h2>
        <span className="acp-learner-email">{learner.email}</span>
        <span className={`acp-status acp-status--${learner.status}`}>{t(`analytics.course.status.${learner.status}`)}</span>
        <span>{learner.progress_pct}%</span>
        <span>{t('analytics.course.totals', {
          active: formatDuration(learner.active_s, t), onScreen: formatDuration(learner.visible_s, t), visits: learner.visits,
        })}</span>
      </div>
      {data.modules.map(m => (
        <section key={m.id} className="acp-tl-module">
          <h3>
            {t('common.moduleLabel', { order: m.order, title: m.title })}
            <span className="acp-tl-meta">{m.pct ?? 0}% · {itemTime(m.active_s, m.visits, null, t)}</span>
          </h3>
          {m.activities.map(a => (
            <div key={a.id} className="acp-tl-activity">
              <h4>
                {a.done ? <CheckCircle2 size={15} className="acp-right" /> : <Circle size={15} className="acp-muted" />}
                {a.title}
                <span className="acp-tl-meta">{itemTime(a.active_s, a.visits, null, t)}</span>
              </h4>
              <div className="acp-table-wrap">
                <table className="acp-table acp-table--compact">
                  <thead>
                    <tr>
                      <th>{t('analytics.course.col.resource')}</th>
                      <th className="acp-num">{t('analytics.course.col.active')}</th>
                      <th className="acp-num">{t('analytics.course.col.onScreen')}</th>
                      <th className="acp-num">{t('analytics.course.col.visits')}</th>
                      <th>{t('analytics.course.col.firstOpened')}</th>
                      <th>{t('analytics.course.col.completed')}</th>
                      <th>{t('analytics.course.col.details')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.resources.map(r => (
                      <tr key={r.id}>
                        <td><span className="acp-resource-title"><TypeIcon type={r.type} size={14} /> {r.title}</span></td>
                        <td className="acp-num">{itemTime(r.active_s, r.visits, r.completed_at, t)}</td>
                        <td className="acp-num">{r.visits ? formatDuration(r.visible_s, t) : '—'}</td>
                        <td className="acp-num">{r.visits}</td>
                        <td>{formatDate(r.first_opened, i18n.language)}</td>
                        <td>{formatDate(r.completed_at, i18n.language)}</td>
                        <td><ResourceDetails r={r} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </section>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Page, route, list buttons**

`frontend/src/pages/AnalyticsCoursePage.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, Download, Info } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import ContentTree from '../components/analytics/ContentTree'
import LearnersTable from '../components/analytics/LearnersTable'
import LearnerTimeline from '../components/analytics/LearnerTimeline'
import { downloadXlsx } from '../components/analytics/download'
import './AnalyticsCoursePage.css'

const TABS = ['content', 'learners']

export default function AnalyticsCoursePage() {
  const { t } = useTranslation()
  const { id } = useParams()
  const { user } = useAuth()
  const isCreator = ['content_creator', 'aidea_partner', 'admin'].includes(user?.profile?.user_type)
  const [tab, setTab] = useState('content')
  const [content, setContent] = useState(null)
  const [learners, setLearners] = useState(null)
  const [learnerId, setLearnerId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isCreator) return
    Promise.all([
      client.get(`/analytics/courses/${id}/content/`),
      client.get(`/analytics/courses/${id}/learners/`),
    ])
      .then(([c, l]) => { setContent(c.data); setLearners(l.data.learners) })
      .catch(err => setError(err.response?.status === 404 ? t('analytics.course.notFound') : t('analytics.loadError')))
  }, [id, isCreator, t])

  if (!isCreator) return <div className="an-restricted"><p>{t('analytics.restricted')}</p></div>
  if (error) return <p className="page-error">{error}</p>
  if (!content || !learners) return <p className="page-loading">{t('common.loading')}</p>

  const exportCourse = () => downloadXlsx(`/analytics/courses/${id}/export/`, {}, `course-${id}-analytics.xlsx`).catch(() => {})

  return (
    <div className="acp-page">
      <Link className="acp-back" to="/analytics"><ArrowLeft size={14} /> {t('analytics.course.back')}</Link>
      <div className="acp-header">
        <div>
          <h1 className="acp-title">{content.course.title}</h1>
          <p className="acp-subtitle">{t('analytics.course.learnersCount', { count: content.learners })}</p>
        </div>
        <button className="an-export-btn" onClick={exportCourse}><Download size={15} /> {t('analytics.downloadExcel')}</button>
      </div>
      <p className="acp-help"><Info size={14} /> {t('analytics.course.help')}</p>

      {learnerId ? (
        <LearnerTimeline key={learnerId} courseId={id} userId={learnerId} onBack={() => setLearnerId(null)} />
      ) : (
        <>
          <div className="acp-tabs" role="tablist">
            {TABS.map(k => (
              <button key={k} role="tab" aria-selected={tab === k} className={`acp-tab ${tab === k ? 'acp-tab--active' : ''}`} onClick={() => setTab(k)}>
                {t(`analytics.course.tabs.${k}`)}
              </button>
            ))}
          </div>
          {tab === 'content'
            ? <ContentTree tree={content} />
            : <LearnersTable learners={learners} onOpen={setLearnerId} />}
        </>
      )}
    </div>
  )
}
```

`frontend/src/pages/AnalyticsCoursePage.css`:

```css
.acp-page { display: flex; flex-direction: column; gap: 1.25rem; }
.acp-back {
  display: inline-flex; align-items: center; gap: 0.3rem; align-self: flex-start;
  background: none; border: none; padding: 0; color: var(--color-primary);
  font-size: 0.85rem; cursor: pointer; text-decoration: none;
}
.acp-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; flex-wrap: wrap; }
.acp-title { margin: 0; font-size: 1.4rem; }
.acp-subtitle, .acp-help { margin: 0; color: var(--color-text-muted); font-size: 0.88rem; }
.acp-help { display: flex; gap: 0.4rem; align-items: flex-start; }
.acp-tabs { display: flex; gap: 0.25rem; border-bottom: 1px solid var(--color-border); }
.acp-tab {
  background: none; border: none; border-bottom: 2px solid transparent;
  padding: 0.55rem 1rem; font-size: 0.92rem; cursor: pointer; color: var(--color-text-muted);
}
.acp-tab--active { color: var(--color-primary); border-bottom-color: var(--color-primary); font-weight: 600; }
.acp-table-wrap {
  overflow-x: auto; background: var(--color-surface);
  border: 1px solid var(--color-border); border-radius: var(--radius-lg);
}
.acp-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
.acp-table th, .acp-table td { padding: 0.55rem 0.75rem; text-align: left; border-bottom: 1px solid var(--color-border); vertical-align: top; }
.acp-table th { font-weight: 600; white-space: nowrap; }
.acp-table--compact th, .acp-table--compact td { padding: 0.4rem 0.6rem; }
.acp-num { text-align: right !important; white-space: nowrap; }
.acp-pct { color: var(--color-text-muted); font-size: 0.78rem; }
.acp-row--module { cursor: pointer; font-weight: 600; background: rgba(0, 0, 0, 0.02); }
.acp-row--activity { cursor: pointer; }
.acp-row--activity td:first-child { padding-left: 1.75rem; }
.acp-row--resource td:first-child { padding-left: 3.25rem; }
.acp-row--learner { cursor: pointer; }
.acp-row--learner:hover, .acp-row--activity:hover, .acp-row--module:hover { background: rgba(37, 99, 235, 0.05); }
.acp-resource-title { display: inline-flex; align-items: center; gap: 0.35rem; }
.acp-notes { margin: 0.2rem 0 0; color: var(--color-text-muted); font-size: 0.78rem; }
.acp-sortable { cursor: pointer; user-select: none; }
.acp-sortable svg { margin-left: 0.25rem; vertical-align: middle; }
.acp-learner-name { display: block; font-weight: 500; }
.acp-learner-email { display: block; color: var(--color-text-muted); font-size: 0.78rem; }
.acp-position { max-width: 16rem; }
.acp-status-filter { align-self: flex-start; padding: 0.4rem 0.6rem; border: 1px solid var(--color-border); border-radius: var(--radius); }
.acp-status { display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; white-space: nowrap; }
.acp-status--completed { background: #dcfce7; color: #166534; }
.acp-status--on_track { background: #dbeafe; color: #1e40af; }
.acp-status--stuck { background: #fef3c7; color: #92400e; }
.acp-status--inactive { background: #f3f4f6; color: #4b5563; }
.acp-empty { color: var(--color-text-muted); }
.acp-timeline { display: flex; flex-direction: column; gap: 1.25rem; }
.acp-timeline-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.5rem 1rem; }
.acp-timeline-head h2 { margin: 0; font-size: 1.2rem; }
.acp-tl-module h3 { display: flex; gap: 0.75rem; align-items: baseline; font-size: 1rem; margin: 0 0 0.5rem; }
.acp-tl-activity { margin: 0 0 0.9rem 0.75rem; }
.acp-tl-activity h4 { display: flex; align-items: center; gap: 0.4rem; font-size: 0.92rem; margin: 0 0 0.4rem; }
.acp-tl-meta { color: var(--color-text-muted); font-size: 0.8rem; font-weight: 400; }
.acp-answers { margin: 0.35rem 0 0; padding-left: 1.1rem; font-size: 0.8rem; }
.acp-answers li { display: flex; gap: 0.35rem; align-items: baseline; flex-wrap: wrap; }
.acp-answer-q { color: var(--color-text-muted); }
.acp-answer-a { font-weight: 500; }
.acp-answer-t { color: var(--color-text-muted); }
.acp-right { color: #16a34a; flex-shrink: 0; }
.acp-wrong { color: #dc2626; flex-shrink: 0; }
.acp-muted { color: var(--color-text-muted); }
```

`frontend/src/App.jsx`: import `AnalyticsCoursePage` beside `AnalyticsPage`, and add this after the `/analytics` route:

```jsx
            <Route path="/analytics/courses/:id" element={<AnalyticsCoursePage />} />
```

`frontend/src/pages/AnalyticsPage.jsx`:
- Replace the local `downloadExport` function with `const downloadExport = (ids) => downloadXlsx('/analytics/export/', ids && ids.length ? { ids: ids.join(',') } : {}, 'analytics.xlsx')`, and add `import { downloadXlsx } from '../components/analytics/download'`.
- Delete the `TeacherDetail` component and its propTypes.
- In `CourseRow`, delete the `expanded`/`teachers`/`loadingTeachers` state and `toggle`. Replace the `{course.can_view_teachers && (<> … </>)}` block with:

```jsx
      {course.can_view_teachers && (
        <div className="an-course-actions">
          <Link className="an-course-open" to={`/analytics/courses/${course.id}`}>{t('analytics.open')}</Link>
          <button
            className="an-course-excel"
            onClick={() => downloadXlsx(`/analytics/courses/${course.id}/export/`, {}, `course-${course.id}-analytics.xlsx`).catch(() => {})}
          >
            <Download size={14} /> {t('analytics.excel')}
          </button>
        </div>
      )}
```

- Remove the lucide imports that are now unused (`ChevronDown`, `ChevronRight`, `Clock` if only `TeacherDetail` used them). Run lint to confirm.

`frontend/src/pages/AnalyticsPage.css`:
- Delete the `.an-teachers-toggle`, `.an-teachers*`, `.an-teacher*`, `.an-quiz*` and `.an-answer*` rules that `TeacherDetail` used. Grep each class in `src/` first and delete only the unreferenced ones.
- Add:

```css
.an-course-actions { display: flex; gap: 0.6rem; margin-top: 0.75rem; }
.an-course-open, .an-course-excel {
  display: inline-flex; align-items: center; gap: 0.3rem;
  padding: 0.35rem 0.8rem; border-radius: var(--radius);
  font-size: 0.82rem; font-weight: 500; cursor: pointer; text-decoration: none;
}
.an-course-open { background: #2563eb; color: #fff; border: 1px solid #2563eb; }
.an-course-excel { background: none; color: #2563eb; border: 1px solid var(--color-border); }
```

- [ ] **Step 5: Locales (9 languages)**

Add the keys below to `analytics` in every locale, using a Node script in the scratchpad that preserves indent, trailing newline and key order (the same pattern as earlier locale scripts):
- Write `en` exactly as shown.
- For el, fr, es, it, fi, sv, no, de, write real translations in the platform's existing tone (formal "you" where the locale already uses it, e.g. de "Sie").
- Keep every `{{placeholder}}` unchanged.

In the same script, delete the keys used only by the removed `TeacherDetail`: `viewTeachers`, `hideTeachers`, `noTeachers`, `minutes`, `avgScore`, `chose`, `correctAnswer`, `notAnswered`. Grep `analytics.<key>` in `src/` first and delete only the unreferenced ones.

```json
"open": "Open",
"excel": "Excel",
"course": {
  "back": "All courses",
  "notFound": "This course was not found, or you cannot see its analytics.",
  "learnersCount": "{{count}} learners enrolled",
  "help": "Active time counts only while the learner is using the page (input in the last minute, or a video playing). Typical = median; hover for the average.",
  "tabs": { "content": "Content", "learners": "Learners" },
  "col": {
    "item": "Module / activity / resource",
    "reached": "Reached",
    "done": "Done",
    "typical": "Typical active time",
    "dropped": "Dropped here",
    "learner": "Learner",
    "progress": "Progress",
    "active": "Active",
    "onScreen": "On screen",
    "visits": "Visits",
    "lastActive": "Last active",
    "position": "Current position",
    "status": "Status",
    "resource": "Resource",
    "firstOpened": "First opened",
    "completed": "Completed",
    "details": "Details"
  },
  "average": "Average: {{value}}",
  "notTracked": "not tracked",
  "noContent": "This course has no modules yet.",
  "empty": "No learners are enrolled in this course yet.",
  "status": { "all": "All statuses", "completed": "Completed", "on_track": "On track", "stuck": "Stuck", "inactive": "Inactive" },
  "notes": {
    "scroll": "avg. scrolled {{pct}}%",
    "watched": "avg. watched {{pct}}%",
    "stop": "often stops at {{time}}",
    "score": "avg. score {{pct}}%",
    "hardest": "hardest: Q{{n}} ({{pct}}% right)",
    "perQuestion": "{{s}} s per question",
    "opened": "opened by {{count}}",
    "downloaded": "downloaded by {{count}}",
    "assignment": "{{submitted}} submitted · {{approved}} approved · {{waiting}} waiting"
  },
  "detail": {
    "score": "Score {{pct}}%",
    "watched": "Watched {{pct}}%",
    "scrolled": "Scrolled {{pct}}%",
    "opened": "Opened",
    "downloaded": "Downloaded",
    "answerTime": "{{s}} s",
    "assignment": { "pending": "Waiting for review", "approved": "Approved", "changes_requested": "Changes requested" }
  },
  "backToLearners": "Back to learners",
  "totals": "Active {{active}} · on screen {{onScreen}} · {{visits}} visits",
  "dur": { "hm": "{{h}} h {{m}} min", "ms": "{{m}} min {{s}} s", "s": "{{s}} s" }
}
```

- [ ] **Step 6: Verify**

From `frontend/`:
- `npm run lint`, `npm test` and `node scripts/check-locales.mjs`: all clean.
- `VITE_API_URL=http://localhost:8000/api npm run build`: succeeds.

Manual check, with backend and frontend dev servers running as demo_creator, and after Task 4's check produced some data:
1. On `/analytics`, a course row shows **Open** and **Excel**.
2. **Open** leads to the Content tab. The tree expands, the typical time shows the average on hover, and resources completed before tracking show "not tracked".
3. On the Learners tab, sorting, the status filter and the counts work. Clicking a learner shows the timeline, and "Back to learners" returns.
4. **Excel** downloads a workbook with the 9 sheets.
5. Switch the interface to Greek and confirm every label is translated.

- [ ] **Step 7: Commit**

```bash
git add src/components/analytics src/pages/AnalyticsCoursePage.jsx src/pages/AnalyticsCoursePage.css src/pages/AnalyticsPage.jsx src/pages/AnalyticsPage.css src/App.jsx src/locales
git commit -m "feat: course analytics page — content tree, learners with status, learner timeline"
git push
```

---

### Task 9: Privacy Policy, docs, full verification

**Files:**
- Modify: `frontend/src/pages/PrivacyPage.jsx`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Privacy Policy section**

In `frontend/src/pages/PrivacyPage.jsx`, the page is English-only legal text like the rest of it.

Change the "Learning activity" bullet in section 2 to:

```jsx
        <li><strong>Learning activity:</strong> enrolments, progress, quiz results, assignment submissions, engagement data and how you use each course resource (see section 11).</li>
```

Insert this after section 10 (Analytics), and renumber "Changes and complaints" to 12:

```jsx
      <h2>11. Learning activity records</h2>
      <p>
        When you study an activity, the platform records how you use each of its resources, so that
        we can improve courses, support learners who get stuck, and carry out the AIDEA research. We record:
      </p>
      <ul>
        <li>the time spent on each resource — both the time you were actively using the page and the time it was on screen;</li>
        <li>video playback (play, pause, skipping and how much was watched), your quiz answers and the time taken per question, and when a PDF or image is opened or downloaded;</li>
        <li>the interface language, the type of device (desktop, tablet or mobile) and your local time of day.</li>
      </ul>
      <p>
        We do not record your IP address, your precise location or what you type for this purpose. These
        records are visible, with your name, to the authors and co-editors of the course, to AIDEA
        partners and to administrators, and may be exported by them for analysis. They are kept like the
        rest of your account data and deleted with your account. The legal basis is our legitimate
        interest in running and improving an educational platform; for study participants, the study
        consent also applies.
      </p>
```

- [ ] **Step 2: CLAUDE.md endpoints**

In `CLAUDE.md` under **API endpoints**, add the following after the `GET /api/analytics/overview/` line, and change the "Two Django apps" sentence's analytics description to `analytics (content creator analytics — reads hub models, no own models)`. The description stays valid because the tracking models live in `hub`.

```markdown
- `POST /api/tracking/` — activity page time/interaction data (running totals per visit; 204 = tracking switched off)
- `GET /api/analytics/courses/<id>/content/` — content tree: reached / done / typical active time / dropped-here per module, activity, resource
- `GET /api/analytics/courses/<id>/learners/` — learners with time, position and status (completed / on track / stuck / inactive)
- `GET /api/analytics/courses/<id>/learners/<user_id>/` — one learner's timeline
- `GET /api/analytics/courses/<id>/export/` and `GET /api/analytics/export/?ids=` — 9-sheet learning analytics workbook
```

- [ ] **Step 3: Full verification**

From `backend/`:

```bash
"$UV" run ruff check .
"$UV" run coverage run manage.py test hub analytics --verbosity=1
"$UV" run coverage report --fail-under=70
"$UV" run manage.py makemigrations --check --dry-run
```

Expected: lint clean; all tests pass; coverage ≥ 70%; "No changes detected".

From `frontend/`: `npm run lint && npm test && node scripts/check-locales.mjs && VITE_API_URL=http://localhost:8000/api npm run build`
Expected: all succeed.

- [ ] **Step 4: Commit** (from the repository root)

```bash
git add frontend/src/pages/PrivacyPage.jsx CLAUDE.md
git commit -m "docs: privacy policy section on learning activity records; list analytics endpoints"
git push
```

- [ ] **Step 5: Deployment note for the user** (the user runs this; it is not part of the task)

The VM's `.env` must contain `COMPOSE_FILE=docker-compose.prod.yml:docker-compose.matomo.yml`. Then run:

```bash
git pull
docker compose up -d --build backend celery celery-beat frontend
docker compose exec -T backend uv run python manage.py migrate
```

- Migration 0061 only adds tables and a column, so a backup is not required, but it is cheap: `pg_dump -Fc`.
- Never use `--remove-orphans` or `down -v`.
- Tracking starts at deploy. Earlier time shows as "not tracked".
- To pause collection: Django admin → Learner activity config → Learning analytics → untick "Tracking enabled".
