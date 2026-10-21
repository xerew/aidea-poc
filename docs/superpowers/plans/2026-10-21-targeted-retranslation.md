# Targeted Re-translation and Review Tracking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
- Re-translate only the chosen part (activity, module, course details or whole course) in the open language.
- Show "Updating…" vs "Translating…".
- Keep a Reviewed language reviewed, with a "N to re-check" list of the parts machine-translated since the review.

**Architecture:**
- **Stored data:** `translation_flags` on Course, Module, Activity and Resource, plus `Course.translation_reviewed_at`, managed by `hub/translation_flags.py`.
- **Translation helpers** flag each item they machine-translate.
- **Partial jobs** finish as `reviewed` when a review is on record.
- **Endpoints:** the translate endpoint gains `scope`, and a new endpoint lists the items to re-check and counts hand-corrected ones.
- **`TranslationBar`** gains the scope menu, the status wording and the re-check list.

**Tech Stack:** Django 5 + DRF + Celery (eager in tests), React 19.

**Spec:** `docs/superpowers/specs/2026-10-21-targeted-retranslation-design.md`

## Global Constraints

- **Flags:** `translation_flags[lang] = {"edited": bool, "changed": bool, "replaced_edit": bool}`.
  - `edited` is set by a manual `PATCH …?lang=` on that item.
  - On every machine translation of an item into `lang`:
    - if `lang` is in `Course.translation_reviewed_at`, set `changed`, and set `replaced_edit` when it was `edited`;
    - then `edited = False`.
- **Statuses:**
  - `pending` = a whole-course translation (the initial one or "Whole course…");
  - `updating` = sync or partial re-translate;
  - **When a partial or sync job ends,** the status becomes `reviewed` if `lang` is in `translation_reviewed_at`, else `done`. On a `TranslationError`, `failed`.
  - **A whole-course job** ends as `done`.
- **Scopes:** `course` (default) | `details` | `module` (+`module_id`) | `activity` (+`activity_id`).
  - Partial scopes require a status of `done` or `reviewed`, and the item must belong to the course; otherwise 400.
  - Before a whole-course re-translate, `forget_review` removes the review record and every flag for that language.
- **Mark reviewed** records `translation_reviewed_at[lang]` and clears `changed`/`replaced_edit` on all items. **Unmark** removes the record, sets the status to `done` and clears those flags.
- **The sync** only starts for a resource with translatable content (`title`, `content`, `caption`, `instructions` or `quiz_data` non-empty).
- **Shared rules:** keep all 9 locales in sync; lucide icons; ESLint ES2020 with the React-compiler purity rule.
- **Runner and git:**
  - from `backend/`, set `UV="/c/Users/Nikos A. Grammatikos/.local/bin/uv.exe"`, then `"$UV" run manage.py test …` and `"$UV" run ruff check hub analytics`;
  - frontend from `frontend/`: `npm test`, `npm run lint`, `node scripts/check-locales.mjs`, `VITE_API_URL=http://localhost:8000/api npm run build`;
  - keep line endings; commit and push per task on `master`, with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **"This activity" re-translate** touches only that activity and its resources: another activity's translation, including a manual correction, stays byte-identical. Pinned by Task 3 `test_activity_scope_touches_only_that_activity`.
2. **A Reviewed language stays Reviewed after a sync or partial re-translate,** and only a whole-course re-translate drops the review. Pinned by Task 2 `test_sync_on_reviewed_language_stays_reviewed_and_flags` and Task 3 `test_whole_course_forgets_the_review`.
3. **A just-added empty resource** starts no job and leaves every status as it was. Pinned by Task 2 `test_empty_new_resource_starts_nothing`.
4. **A forged `module_id`/`activity_id`** (another course, not a number) or a partial scope on an untranslated language gives a 400, never a 500 or a job. Pinned by Task 3 `test_partial_scope_validation`.
5. **Polling stops** when a partial job ends as `reviewed` (not only `done`), so the bar doesn't spin forever. Pinned by Task 4 `translationUi.test.js` (`isFinished('reviewed')`).

---

## File Structure

- **Backend:**
  - `hub/translation_flags.py` (new);
  - `hub/models/content.py` (`translation_flags` ×4, `translation_reviewed_at`); migration `0071` (generated);
  - `hub/views/authoring_course.py`, `authoring_module.py`, `authoring_lesson.py`, `authoring_resource.py` (mark edited; scope; changes endpoint; review);
  - `hub/serializers/course.py`, `hub/serializers/content.py` (expose flags);
  - `hub/tasks.py`, `hub/translation_sync.py`, `hub/urls.py`.
- **Backend tests:** `hub/tests/test_translation_flags.py`, `test_translation_status.py`, `test_targeted_retranslation.py`.
- **Frontend:**
  - `src/lib/translationUi.js` and `.test.js` (new);
  - `src/components/authoring/TranslationBar.jsx` and `.css`;
  - `src/pages/ModuleEditorPage.jsx` and `.css`, `src/pages/CourseEditorPage.jsx`;
  - `src/components/authoring/ResourceEditor.jsx`;
  - `src/locales/*.json`.

---

### Task 1: Flags data, manual-edit marking, payloads

**Files:**
- Create: `backend/hub/translation_flags.py`, `backend/hub/tests/test_translation_flags.py`
- Modify:
  - `backend/hub/models/content.py`
  - `backend/hub/views/authoring_course.py`, `authoring_module.py`, `authoring_lesson.py`, `authoring_resource.py`
  - `backend/hub/serializers/course.py`, `backend/hub/serializers/content.py`
  - migration `0071` (generated)

**Interfaces — Produces** (in `hub.translation_flags`):
- `mark_edited(obj, lang)`;
- `note_machine_translated(obj, course_id, lang)`;
- `set_reviewed(course, lang, reviewed: bool)`;
- `forget_review(course, lang)`;
- `recheck_items(course, lang) -> list[dict]`;
- `count_edited(course, lang, scope, module_id=None, activity_id=None) -> int`;
- `course_items(course)`, yielding `(kind, obj)`.

The payloads expose `translation_flags` (course, module authoring, lesson, resource) and `translation_reviewed_at` (course).

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_translation_flags.py`:

```python
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub import translation_flags as tf
from hub.models import Activity, Course, LearningPillar, Module, Resource, UserProfile


def make_course(creator=None):
    pillar = LearningPillar.objects.get_or_create(slug='p-tf', defaults={'name': 'P', 'order': 1})[0]
    course = Course.objects.create(title='C', pillar=pillar, level='beginner', duration_hours=1, created_by=creator,
                                   translation_status={'el': 'done'})
    m1 = Module.objects.create(course=course, title='M1', order=1)
    m2 = Module.objects.create(course=course, title='M2', order=2)
    a1 = Activity.objects.create(module=m1, title='A1', order=1)
    a2 = Activity.objects.create(module=m2, title='A2', order=1)
    r1 = Resource.objects.create(activity=a1, type='text', order=1, content='<p>One</p>')
    r2 = Resource.objects.create(activity=a2, type='text', order=1, content='<p>Two</p>')
    return course, m1, m2, a1, a2, r1, r2


def flags(obj, lang='el'):
    obj.refresh_from_db()
    return obj.translation_flags.get(lang, {})


class FlagFunctionTests(APITestCase):
    def setUp(self):
        self.course, self.m1, self.m2, self.a1, self.a2, self.r1, self.r2 = make_course()

    def test_machine_translation_without_review_only_clears_edited(self):
        tf.mark_edited(self.r1, 'el')
        tf.note_machine_translated(self.r1, self.course.id, 'el')
        self.assertEqual(flags(self.r1), {'edited': False})

    def test_machine_translation_after_review_flags_and_notes_replaced_edits(self):
        tf.set_reviewed(self.course, 'el', True)
        tf.mark_edited(self.r1, 'el')
        tf.note_machine_translated(self.r1, self.course.id, 'el')
        tf.note_machine_translated(self.r2, self.course.id, 'el')
        self.assertEqual(flags(self.r1), {'edited': False, 'changed': True, 'replaced_edit': True})
        self.assertEqual(flags(self.r2), {'edited': False, 'changed': True})

    def test_review_clears_the_recheck_list(self):
        tf.set_reviewed(self.course, 'el', True)
        tf.note_machine_translated(self.r1, self.course.id, 'el')
        self.assertEqual([i['id'] for i in tf.recheck_items(self.course, 'el')], [self.r1.id])
        tf.set_reviewed(self.course, 'el', True)
        self.course.refresh_from_db()
        self.assertEqual(tf.recheck_items(self.course, 'el'), [])
        self.assertIn('el', self.course.translation_reviewed_at)
        self.assertEqual(self.course.translation_status['el'], 'reviewed')

    def test_unmark_and_forget(self):
        tf.set_reviewed(self.course, 'el', True)
        tf.set_reviewed(self.course, 'el', False)
        self.course.refresh_from_db()
        self.assertNotIn('el', self.course.translation_reviewed_at)
        self.assertEqual(self.course.translation_status['el'], 'done')
        tf.mark_edited(self.r1, 'el')
        tf.forget_review(self.course, 'el')
        self.assertEqual(flags(self.r1), {})

    def test_recheck_items_shape(self):
        tf.set_reviewed(self.course, 'el', True)
        for obj in (self.course, self.m1, self.a1, self.r1):
            tf.note_machine_translated(obj, self.course.id, 'el')
        items = {i['kind']: i for i in tf.recheck_items(self.course, 'el')}
        self.assertEqual(set(items), {'course', 'module', 'activity', 'resource'})
        self.assertEqual((items['resource']['module_id'], items['resource']['activity_id']), (self.m1.id, self.a1.id))
        self.assertEqual((items['activity']['module_id'], items['activity']['activity_id']), (self.m1.id, self.a1.id))
        self.assertEqual(items['module']['module_id'], self.m1.id)
        self.assertIsNone(items['course']['module_id'])

    def test_count_edited_per_scope(self):
        for obj in (self.course, self.m1, self.a1, self.r1, self.r2):
            tf.mark_edited(obj, 'el')
        self.assertEqual(tf.count_edited(self.course, 'el', 'course'), 5)
        self.assertEqual(tf.count_edited(self.course, 'el', 'details'), 1)
        self.assertEqual(tf.count_edited(self.course, 'el', 'module', module_id=self.m1.id), 3)
        self.assertEqual(tf.count_edited(self.course, 'el', 'activity', activity_id=self.a1.id), 2)


class ManualEditTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user('tf_cc', password='x')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.m1, _, self.a1, _, self.r1, _ = make_course(creator=self.creator)
        self.client.force_authenticate(self.creator)

    def test_manual_translation_edits_set_edited_and_payload_shows_flags(self):
        url = reverse('authoring-resource-detail', kwargs={'pk': self.course.id, 'module_pk': self.m1.id,
                                                           'lesson_pk': self.a1.id, 'resource_pk': self.r1.id})
        res = self.client.patch(f'{url}?lang=el', {'content': '<p>Ένα</p>'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['translation_flags'], {'el': {'edited': True}})
        res = self.client.patch(f'/api/authoring/courses/{self.course.id}/?lang=el', {'title': 'Γ'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(flags(self.course)['edited'])
        self.assertIn('translation_reviewed_at', res.data)
        self.client.patch(f'/api/authoring/courses/{self.course.id}/modules/{self.m1.id}/?lang=el', {'title': 'Μ'}, format='json')
        self.assertTrue(flags(self.m1)['edited'])
        self.client.patch(f'/api/authoring/courses/{self.course.id}/modules/{self.m1.id}/lessons/{self.a1.id}/?lang=el',
                          {'title': 'Δ'}, format='json')
        self.assertTrue(flags(self.a1)['edited'])
```

Before running, check the URL paths of the course, module and lesson PATCH endpoints in `hub/urls.py` (`grep -n "AuthoringCourseDetail\|AuthoringModuleDetail\|AuthoringLessonDetail" hub/urls.py`). If they differ from the strings above, use `reverse` with their names and record a ruling.

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_translation_flags -v 2`
  - Expected: ImportError, `cannot import name 'translation_flags'`.

- [ ] **Step 3: Implement.** `backend/hub/translation_flags.py`:

```python
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
```

`backend/hub/models/content.py`:
- add `translation_flags = models.JSONField(default=dict, blank=True)` to **Course, Module, Activity and Resource**, each next to that model's `translations`/`translation_status` field;
- on Course also add:

```python
    # {lang: ISO time} — when each language was last marked reviewed (spec 2026-10-21).
    translation_reviewed_at = models.JSONField(default=dict, blank=True)
```

Generate the migration with `"$UV" run manage.py makemigrations hub --name translation_flags`, then run `"$UV" run manage.py migrate`.

**Manual edits:** in each `?lang=` branch, right after `….save(update_fields=['translations'])`, add `mark_edited(<obj>, lang)` (import `from hub.translation_flags import mark_edited`). That's:
- `authoring_course.py` (`course`);
- `authoring_module.py` (`module`);
- `authoring_lesson.py` (`lesson`);
- `authoring_resource.py` (`resource`).

**Serializers:**
- `CourseAuthoringSerializer` (`hub/serializers/course.py`): add `'translation_flags', 'translation_reviewed_at'` to `fields` and `read_only_fields`;
- `ModuleAuthoringSerializer`, `LessonSerializer` and `ResourceSerializer` (`hub/serializers/content.py`): add `'translation_flags'` to `fields` and to `read_only_fields`. For `ModuleAuthoringSerializer`, write `read_only_fields = ['translations', 'translation_flags']`.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_translation_flags hub.tests.test_content_translation hub.tests.test_translation_review -v 2`
  - Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/translation_flags.py hub/models hub/migrations/0071_translation_flags.py hub/views hub/serializers hub/tests/test_translation_flags.py
git commit -m "feat: per-item translation flags and review record"
git push
```

---

### Task 2: Status semantics, flagging in jobs, quiet sync, review endpoint

**Files:**
- Modify:
  - `backend/hub/tasks.py`, `backend/hub/translation_sync.py`
  - `backend/hub/views/authoring_course.py` (`AuthoringTranslationReviewView`)
- Create: `backend/hub/tests/test_translation_status.py`

**Interfaces:**
- **Consumes:** Task 1's functions.
- **Produces:**
  - `_finish(course, target, work, update=False)`;
  - Celery `translate_module_full(module_id, target)` (module + all its activities and resources, `update=True`);
  - `translate_course_meta`, `translate_module_meta`, `translate_lesson_meta` and `translate_resource_meta` finish with `update=True`;
  - `hub.translation_sync.has_translatable_content(resource) -> bool`.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_translation_status.py`:

```python
from unittest import mock

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub import translation_flags as tf
from hub.models import Resource, UserProfile
from hub.translation_sync import resync_resource

from .test_translation_flags import make_course

TR = mock.patch('hub.tasks.translate_text', side_effect=lambda t, s, d: f'[{d}] {t}')


class StatusTests(APITestCase):
    def setUp(self):
        self.course, self.m1, self.m2, self.a1, self.a2, self.r1, self.r2 = make_course()

    def status(self):
        self.course.refresh_from_db()
        return self.course.translation_status['el']

    @TR
    def test_sync_on_reviewed_language_stays_reviewed_and_flags(self, _tr):
        tf.set_reviewed(self.course, 'el', True)
        resync_resource(self.r1)
        self.assertEqual(self.status(), 'reviewed')
        self.r1.refresh_from_db()
        self.assertEqual(self.r1.translations['el']['content'], '[el] <p>One</p>')
        self.assertTrue(self.r1.translation_flags['el']['changed'])

    @TR
    def test_sync_on_done_language_stays_done_without_flags(self, _tr):
        resync_resource(self.r1)
        self.assertEqual(self.status(), 'done')
        self.r1.refresh_from_db()
        self.assertFalse(self.r1.translation_flags['el'].get('changed', False))

    def test_sync_marks_updating_while_running(self):
        with mock.patch('hub.tasks.translate_resource_meta.delay') as delay:
            resync_resource(self.r1)
        self.assertEqual(self.status(), 'updating')
        delay.assert_called_once_with(self.r1.id, 'el')

    def test_empty_new_resource_starts_nothing(self):
        empty = Resource.objects.create(activity=self.a1, type='text', order=2)
        with mock.patch('hub.tasks.translate_resource_meta.delay') as delay:
            resync_resource(empty)
        self.assertFalse(delay.called)
        self.assertEqual(self.status(), 'done')

    @TR
    def test_module_full_translates_only_that_module(self, _tr):
        from hub.tasks import translate_module_full
        self.r2.translations = {'el': {'content': 'manual'}}
        self.r2.save()
        translate_module_full(self.m1.id, 'el')
        self.r1.refresh_from_db()
        self.r2.refresh_from_db()
        self.a1.refresh_from_db()
        self.assertEqual(self.r1.translations['el']['content'], '[el] <p>One</p>')
        self.assertEqual(self.a1.translations['el']['title'], '[el] A1')
        self.assertEqual(self.r2.translations['el'], {'content': 'manual'})

    @TR
    def test_whole_course_job_ends_done(self, _tr):
        from hub.tasks import translate_course
        translate_course(self.course.id, 'el')
        self.assertEqual(self.status(), 'done')


class ReviewEndpointTests(APITestCase):
    def test_marking_reviewed_records_it_and_clears_the_list(self):
        admin = User.objects.create_user('ts_admin', password='x')
        UserProfile.objects.create(user=admin, user_type=UserProfile.UserType.ADMIN)
        course, *_rest, r1, _r2 = make_course(creator=admin)
        tf.set_reviewed(course, 'el', True)
        tf.note_machine_translated(r1, course.id, 'el')
        self.client.force_authenticate(admin)
        res = self.client.post(f'/api/authoring/courses/{course.id}/translation-review/', {'language': 'el'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        course.refresh_from_db()
        self.assertEqual((course.translation_status['el'], tf.recheck_items(course, 'el')), ('reviewed', []))
        res = self.client.post(f'/api/authoring/courses/{course.id}/translation-review/',
                               {'language': 'el', 'reviewed': False}, format='json')
        course.refresh_from_db()
        self.assertEqual(course.translation_status['el'], 'done')
        self.assertNotIn('el', course.translation_reviewed_at)
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_translation_status -v 2`
  - Expected: failures (`done` instead of `reviewed`, `pending` instead of `updating`, the empty resource starting a job, `translate_module_full` missing).

- [ ] **Step 3: Implement.**

**`backend/hub/tasks.py`:**
- **`_finish`** becomes:

```python
def _finish(course, target, work, update=False):
    """Run a translation unit of work, then set the language's status:
    'failed' on error; otherwise 'done' — or, for an update (sync / partial
    re-translate) of a language with a review on record, 'reviewed' again."""
    from hub.models import Course
    from hub.translation import TranslationError
    try:
        work()
    except TranslationError as exc:
        logger.error('Translation of course %s into %s failed: %s', course.id, target, exc)
        _merge_json(Course, course.pk, 'translation_status', target, 'failed')
        return
    reviewed = target in (Course.objects.filter(pk=course.pk).values_list('translation_reviewed_at', flat=True).first() or {})
    _merge_json(Course, course.pk, 'translation_status', target, 'reviewed' if update and reviewed else 'done')
```

- In `translate_course_meta`, `translate_module_meta`, `translate_lesson_meta` and `translate_resource_meta`, pass `update=True` to `_finish`. `translate_course` keeps the default.
- **Flag every machine-translated item.** At the end of each helper, after its `_merge_json(… 'translations' …)`, add the matching call (import `from hub.translation_flags import note_machine_translated` inside each helper):
  - `_translate_course_meta`: `note_machine_translated(course, course.pk, target)`;
  - `_translate_module`: `note_machine_translated(module, module.course_id, target)`;
  - `_translate_lesson`: `note_machine_translated(lesson, lesson.module.course_id, target)`, placed after the lesson's own `_merge_json` and before the resource loop;
  - `_translate_resource`: `note_machine_translated(resource, resource.activity.module.course_id, target)`, placed after `if blob: _merge_json(...)`. Call it always, even when the blob is empty.
- **Add after `translate_module_meta`:**

```python
@shared_task
def translate_module_full(module_id: int, target: str) -> None:
    """Re-translate one module and all its activities and resources (the
    editor's "Re-translate → This module")."""
    from hub.models import Module
    try:
        module = Module.objects.select_related('course').prefetch_related('lessons__resources').get(pk=module_id)
    except Module.DoesNotExist:
        return

    def work():
        _translate_module(module, target)
        for lesson in module.lessons.all():
            _translate_lesson(lesson, target)

    _finish(module.course, target, work, update=True)
```

**`backend/hub/translation_sync.py`:**
- `_SYNCABLE = {'done', 'reviewed', 'pending', 'updating'}`;
- in `_mark_pending`, set `status[lang] = 'updating'`, and rename the function `_mark_updating` (update its four callers);
- add:

```python
def has_translatable_content(resource):
    return any([resource.title, resource.content, resource.caption, resource.instructions, resource.quiz_data])
```

- at the top of `resync_resource`, add `if not has_translatable_content(resource): return`.

**`AuthoringTranslationReviewView.post`** (`authoring_course.py`):
- replace the block from `reviewed = request.data.get('reviewed', True)` to the `course.save(...)` with:

```python
        reviewed = request.data.get('reviewed', True)
        if reviewed and current not in ('done', 'reviewed'):
            return Response(
                {'detail': 'Only a completed translation can be marked reviewed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from hub.translation_flags import set_reviewed
        if reviewed or current == 'reviewed':
            set_reviewed(course, language, bool(reviewed))
        return Response({'translation_status': course.translation_status})
```

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_translation_status hub.tests.test_translation_flags hub.tests.test_content_translation hub.tests.test_translation_review -v 2`
  - Expected: all pass.
  - If an existing test expects `'pending'` after a sync or `'done'` after a sync of a reviewed language, update it to the new behaviour (`'updating'` / `'reviewed'`) and record a ruling.

- [ ] **Step 5: Full suite, lint, commit.**

```bash
"$UV" run ruff check hub analytics
"$UV" run manage.py test hub analytics
git add hub/tasks.py hub/translation_sync.py hub/views/authoring_course.py hub/tests
git commit -m "feat: partial translations keep the review and flag what changed; quiet sync for empty items"
git push
```

---

### Task 3: Scoped re-translate and the re-check endpoint

**Files:**
- Modify: `backend/hub/views/authoring_course.py`, `backend/hub/urls.py`
- Create: `backend/hub/tests/test_targeted_retranslation.py`

**Interfaces:**
- **Consumes:** Tasks 1–2.
- **Produces:**
  - `POST /api/authoring/courses/<pk>/translate/` with `{language, scope?, module_id?, activity_id?}`;
  - `GET /api/authoring/courses/<pk>/translation-changes/?language=xx` (`authoring-course-translation-changes`), returning `{items: [...]}`, or `{edited_count: n}` when `edited=1` (with `scope`, `module_id`, `activity_id`).

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_targeted_retranslation.py`:

```python
from unittest import mock

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub import translation_flags as tf
from hub.models import UserProfile

from .test_translation_flags import make_course

ONLINE = mock.patch('hub.translation_health.check_now', return_value={'online': True})
TR = mock.patch('hub.tasks.translate_text', side_effect=lambda t, s, d: f'[{d}] {t}')


class TargetedRetranslationTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user('trt_cc', password='x')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.m1, self.m2, self.a1, self.a2, self.r1, self.r2 = make_course(creator=self.creator)
        self.r2.translations = {'el': {'content': 'manual two'}}
        self.r2.save()
        self.url = f'/api/authoring/courses/{self.course.id}/translate/'
        self.client.force_authenticate(self.creator)

    def post(self, **body):
        return self.client.post(self.url, {'language': 'el', **body}, format='json')

    @ONLINE
    @TR
    def test_activity_scope_touches_only_that_activity(self, _tr, _online):
        tf.set_reviewed(self.course, 'el', True)
        res = self.post(scope='activity', activity_id=self.a1.id)
        self.assertEqual(res.status_code, 202, res.data)
        for obj in (self.r1, self.r2, self.a1, self.course):
            obj.refresh_from_db()
        self.assertEqual(self.r1.translations['el']['content'], '[el] <p>One</p>')
        self.assertEqual(self.r2.translations['el'], {'content': 'manual two'})
        self.assertEqual(self.course.translation_status['el'], 'reviewed')
        self.assertEqual({i['id'] for i in tf.recheck_items(self.course, 'el') if i['kind'] == 'resource'}, {self.r1.id})

    @ONLINE
    @TR
    def test_module_and_details_scopes(self, _tr, _online):
        self.assertEqual(self.post(scope='module', module_id=self.m1.id).status_code, 202)
        self.r2.refresh_from_db()
        self.assertEqual(self.r2.translations['el'], {'content': 'manual two'})
        self.assertEqual(self.post(scope='details').status_code, 202)
        self.course.refresh_from_db()
        self.assertEqual(self.course.translations['el']['title'], '[el] C')

    @ONLINE
    @TR
    def test_whole_course_forgets_the_review(self, _tr, _online):
        tf.set_reviewed(self.course, 'el', True)
        tf.mark_edited(self.r2, 'el')
        self.assertEqual(self.post().status_code, 202)
        self.course.refresh_from_db()
        self.assertEqual(self.course.translation_status['el'], 'done')
        self.assertNotIn('el', self.course.translation_reviewed_at)
        self.assertEqual(tf.count_edited(self.course, 'el', 'course'), 0)

    @ONLINE
    def test_partial_scope_validation(self, _online):
        other, *_ = make_course()
        other_module = other.modules.first()
        self.assertEqual(self.post(scope='activity', activity_id=other_module.lessons.first().id).status_code, 400)
        self.assertEqual(self.post(scope='module', module_id=other_module.id).status_code, 400)
        self.assertEqual(self.post(scope='module', module_id='abc').status_code, 400)
        self.assertEqual(self.post(scope='weird').status_code, 400)
        self.assertEqual(self.client.post(self.url, {'language': 'fr', 'scope': 'details'}, format='json').status_code, 400)

    def test_changes_endpoint(self):
        tf.set_reviewed(self.course, 'el', True)
        tf.note_machine_translated(self.r1, self.course.id, 'el')
        tf.mark_edited(self.r2, 'el')
        url = reverse('authoring-course-translation-changes', kwargs={'pk': self.course.id})
        res = self.client.get(url, {'language': 'el'})
        self.assertEqual([i['id'] for i in res.data['items']], [self.r1.id])
        res = self.client.get(url, {'language': 'el', 'edited': 1, 'scope': 'module', 'module_id': self.m2.id})
        self.assertEqual(res.data, {'edited_count': 1})
        other = User.objects.create_user('trt_o', password='x')
        UserProfile.objects.create(user=other)
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(url, {'language': 'el'}).status_code, 403)
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_targeted_retranslation -v 2`
  - Expected: failures (scope ignored, so the whole course gets translated and manual two is overwritten), plus `NoReverseMatch` for the changes endpoint.

- [ ] **Step 3: Implement.** In `AuthoringCourseTranslateView.post` (`authoring_course.py`):

1. After the `language` validation, add:

```python
        scope = request.data.get('scope') or 'course'
        if scope not in ('course', 'details', 'module', 'activity'):
            return Response({'detail': 'Unknown scope.'}, status=status.HTTP_400_BAD_REQUEST)
        target = None
        if scope != 'course':
            if (course.translation_status or {}).get(language) not in ('done', 'reviewed'):
                return Response({'detail': 'Translate the whole course into this language first.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if scope in ('module', 'activity'):
                try:
                    item_id = int(request.data.get(f'{scope}_id'))
                except (TypeError, ValueError):
                    return Response({'detail': f'{scope}_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
                target = (course.modules.filter(pk=item_id).first() if scope == 'module'
                          else Activity.objects.filter(pk=item_id, module__course=course).first())
                if target is None:
                    return Response({'detail': 'Not part of this course.'}, status=status.HTTP_400_BAD_REQUEST)
```

2. Replace the tail, from `course.translation_status[language] = 'pending'` to the `return`, with:

```python
        from hub import tasks
        from hub.translation_flags import forget_review
        from hub.translation_sync import _mark_updating
        if scope == 'course':
            forget_review(course, language)
            course.translation_status[language] = 'pending'
            course.save(update_fields=['translation_status'])
            tasks.translate_course.delay(course.id, language)
        else:
            _mark_updating(course, [language])
            if scope == 'details':
                tasks.translate_course_meta.delay(course.id, language)
            elif scope == 'module':
                tasks.translate_module_full.delay(target.id, language)
            else:
                tasks.translate_lesson_meta.delay(target.id, language)
        return Response({'translation_status': course.translation_status}, status=status.HTTP_202_ACCEPTED)
```

   Import `Activity` from `hub.models` if it isn't already imported in this file.

3. Add the changes view:

```python
class AuthoringCourseTranslationChangesView(APIView):
    """GET ?language= — items machine-translated since the last review
    ({items}); with edited=1&scope=… — how many hand-corrected items that
    re-translation would replace ({edited_count})."""
    permission_classes = [IsContentCreator]

    def get(self, request, pk):
        course = Course.objects.filter(pk=pk).first()
        if course is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_translate_course(request.user, course):
            return Response({'detail': 'You cannot translate this course.'}, status=status.HTTP_403_FORBIDDEN)
        language = request.query_params.get('language', '')
        from hub.translation_flags import count_edited, recheck_items
        if request.query_params.get('edited'):
            def as_int(name):
                try:
                    return int(request.query_params.get(name))
                except (TypeError, ValueError):
                    return None
            scope = request.query_params.get('scope', 'course')
            return Response({'edited_count': count_edited(course, language, scope,
                                                          as_int('module_id'), as_int('activity_id'))})
        return Response({'items': recheck_items(course, language)})
```

`backend/hub/urls.py`: import the view and add, next to the translate route:

```python
    path('authoring/courses/<int:pk>/translation-changes/', AuthoringCourseTranslationChangesView.as_view(), name='authoring-course-translation-changes'),
```

If `IsContentCreator` rejects a plain learner before the view runs (403), the test's 403 expectation already holds.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_targeted_retranslation hub.tests.test_translation_status hub.tests.test_content_translation -v 2`
  - Expected: all pass.

- [ ] **Step 5: Full suite, lint, commit.**

```bash
"$UV" run ruff check hub analytics
"$UV" run manage.py test hub analytics
git add hub/views/authoring_course.py hub/urls.py hub/tests/test_targeted_retranslation.py
git commit -m "feat: re-translate an activity, module or the course details only; re-check list endpoint"
git push
```

---

### Task 4: Translation bar menu, status wording, re-check list, badges

**Files:**
- Create: `frontend/src/lib/translationUi.js`, `frontend/src/lib/translationUi.test.js`
- Modify:
  - `frontend/src/components/authoring/TranslationBar.jsx` and `.css`
  - `frontend/src/pages/ModuleEditorPage.jsx` and `.css`, `frontend/src/pages/CourseEditorPage.jsx`
  - `frontend/src/components/authoring/ResourceEditor.jsx`
  - `frontend/src/locales/*.json`

**Interfaces:**
- **Consumes:** Task 3's endpoints; the `translation_flags` fields.
- **Produces** (in `translationUi.js`):
  - `statusLabelKey(status)`;
  - `isRunning(status)`, `isFinished(status)`;
  - `retranslateOptions({ page, moduleId, activityId }) -> [{scope, module_id?, activity_id?}]`.

- [ ] **Step 1: Write the failing test.** `frontend/src/lib/translationUi.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { isFinished, isRunning, retranslateOptions, statusLabelKey } from './translationUi.js'

test('status wording and running/finished states', () => {
  assert.equal(statusLabelKey('updating'), 'authoring.translate.statusUpdating')
  assert.equal(statusLabelKey('pending'), 'authoring.translate.statusPending')
  assert.equal(statusLabelKey(undefined), 'authoring.translate.statusNone')
  assert.equal(isRunning('updating'), true)
  assert.equal(isRunning('reviewed'), false)
  for (const st of ['done', 'reviewed', 'failed']) assert.equal(isFinished(st), true, st)
  assert.equal(isFinished('updating'), false)
})

test('re-translate options per page', () => {
  assert.deepEqual(retranslateOptions({ page: 'course' }), [{ scope: 'details' }, { scope: 'course' }])
  assert.deepEqual(retranslateOptions({ page: 'module', moduleId: 4, activityId: 9 }),
    [{ scope: 'activity', activity_id: 9 }, { scope: 'module', module_id: 4 }, { scope: 'course' }])
  assert.deepEqual(retranslateOptions({ page: 'module', moduleId: 4, activityId: null }),
    [{ scope: 'module', module_id: 4 }, { scope: 'course' }])
})
```

Run `npm test`. Expected: `ERR_MODULE_NOT_FOUND`.

- [ ] **Step 2: Implement the helpers.** `frontend/src/lib/translationUi.js`:

```js
// Translation bar helpers (spec 2026-10-21 targeted re-translation).

const LABELS = {
  pending: 'statusPending', updating: 'statusUpdating', done: 'statusDone',
  reviewed: 'statusReviewed', failed: 'statusFailed',
}

export const statusLabelKey = (status) => `authoring.translate.${LABELS[status] ?? 'statusNone'}`
export const isRunning = (status) => status === 'pending' || status === 'updating'
export const isFinished = (status) => ['done', 'reviewed', 'failed'].includes(status)

export function retranslateOptions({ page, moduleId, activityId }) {
  if (page === 'course') return [{ scope: 'details' }, { scope: 'course' }]
  const options = []
  if (activityId) options.push({ scope: 'activity', activity_id: activityId })
  if (moduleId) options.push({ scope: 'module', module_id: moduleId })
  options.push({ scope: 'course' })
  return options
}
```

Run `npm test`. Expected: pass.

- [ ] **Step 3: TranslationBar.**
- **New props:** `page` (`'course'|'module'`, default `'course'`), `moduleId`, `activityId` (numbers or null).
- **Polling** (`startPolling`): stop when `isFinished(status[lang])` (replacing the `done`/`failed` check), and pass `status[lang]` to `onTranslated` as now.
- **Tab badges:** replace the five status `&&` lines with `{t(statusLabelKey(st))}`. Keep the `translation-status--${st ?? 'none'}` class, and add CSS for `--updating`, reusing the pending colours.
- **Action area:** replace `activeStatus === 'pending' ? (<span …translating…/>)` with `isRunning(activeStatus) ? (<span className="translation-translating">{t(activeStatus === 'updating' ? 'authoring.translate.updating' : 'authoring.translate.translating')}</span>)`.
- **Re-check list:**

```jsx
  const [recheck, setRecheck] = useState([])
  const [showRecheck, setShowRecheck] = useState(false)
  useEffect(() => {
    if (activeLang === 'original' || !['done', 'reviewed'].includes(activeStatus)) return undefined
    let alive = true
    client.get(`/authoring/courses/${courseId}/translation-changes/`, { params: { language: activeLang } })
      .then(res => { if (alive) setRecheck(res.data.items ?? []) })
      .catch(() => {})
    return () => { alive = false }
  }, [courseId, activeLang, activeStatus])
  const visibleRecheck = ['done', 'reviewed'].includes(activeStatus) ? recheck : []
```

  Under the reviewed/done notes, when `visibleRecheck.length > 0`, render a button `t('authoring.translate.recheckCount', { count })`. It toggles a list of `<a href={`/authoring/courses/${courseId}/modules/${item.module_id}${item.activity_id ? `?activity=${item.activity_id}` : ''}`}>` entries, labelled `t(`authoring.translate.kind.${item.kind}`)` + `item.title`, plus `t('authoring.translate.correctionsReplaced')` when `item.replaced_edit`. Items of kind `course` link to `/authoring/courses/${courseId}`.
  - **Also show** the "Mark as reviewed" button when `activeStatus === 'reviewed' && visibleRecheck.length > 0`, labelled `t('authoring.translate.markReviewedAgain')` and calling `reviewTranslation(activeLang, true)`.
- **Re-translate menu:** replace the single re-translate button (for `done`/`reviewed`) with a toggle button `t('authoring.translate.retranslate')` + `<ChevronDown size={13}/>`, which opens a list of `retranslateOptions({ page, moduleId, activityId })`. Each entry is labelled `t(`authoring.translate.scope.${o.scope}`)` and calls:

```jsx
  const retranslate = async (option) => {
    setMenuOpen(false)
    let edited = 0
    try {
      const res = await client.get(`/authoring/courses/${courseId}/translation-changes/`,
        { params: { language: activeLang, edited: 1, ...option } })
      edited = res.data.edited_count ?? 0
    } catch { /* confirm without the count */ }
    const scopeName = t(`authoring.translate.scopeName.${option.scope}`)
    const message = edited > 0
      ? t('authoring.translate.reconfirmEdited', { scope: scopeName, count: edited, language: activeLabel })
      : t('authoring.translate.reconfirmScope', { scope: scopeName, language: activeLabel })
    if (!window.confirm(message)) return
    setBusy(true)
    try {
      const res = await client.post(`/authoring/courses/${courseId}/translate/`, { language: activeLang, ...option })
      onStatusUpdate(res.data.translation_status ?? translationStatus)
      startPolling(activeLang)
    } catch (err) {
      if (err.response?.status === 503 && err.response.data?.service) setService(err.response.data.service)
      setBusy(false)
    }
  }
```

  - Keep the first-time "Translate to X" button path (`triggerTranslate(lang, false)`) unchanged. Remove the now-unused `isRetranslate` branch and the `reconfirm` string use.
  - Add `menuOpen` state, and `ChevronDown` to the lucide import.
- **CSS** (`TranslationBar.css`): `.translation-menu` (absolute dropdown under the button: surface background, border, radius, shadow), `.translation-menu button` (block, full width, left-aligned), `.translation-recheck-list` (small list with links), `.translation-status--updating` (same as `--pending`).

- [ ] **Step 4: Pages.**
- **`ModuleEditorPage.jsx`:**
  - pass `page="module"`, `moduleId={Number(moduleId)}` and `activityId={selectedLesson && !selectedLesson.isNew ? selectedLesson.id : null}` to `<TranslationBar>`;
  - in the lesson list item, after the title span, add `{translating && lesson.translation_flags?.[activeLang]?.changed && <span className="me-lesson-changed">{t('authoring.translate.changedBadge')}</span>}`;
  - pass `reviewFlag={translating ? resource.translation_flags?.[activeLang] ?? null : null}` to `<ResourceEditor>`;
  - **open the activity from the re-check link:** import `useSearchParams`, and in the load `.then`, replace `setSelectedLessonId(loaded[0]?.id ?? null)` with:

```jsx
          const wanted = Number(searchParams.get('activity'))
          setSelectedLessonId(loaded.find(l => l.id === wanted)?.id ?? loaded[0]?.id ?? null)
```

  - add `const [searchParams] = useSearchParams()` next to `useParams`, and add `searchParams` to that effect's dependency list.
- **`ModuleEditorPage.css`:** `.me-lesson-changed { font-size: 0.7rem; padding: 0.05rem 0.4rem; border-radius: 999px; background: #fef9c3; color: #854d0e; margin-left: auto; }`.
- **`ResourceEditor.jsx`:** add the prop `reviewFlag = null` (propTypes `reviewFlag: PropTypes.object`). In the topbar, after the kind label, render `{reviewFlag?.changed && <span className="resource-editor-changed">{t('authoring.translate.changedBadge')}{reviewFlag.replaced_edit ? ` · ${t('authoring.translate.correctionsReplaced')}` : ''}</span>}`. Add matching CSS to `ResourceEditor`'s stylesheet, with the same look as `.me-lesson-changed`.
- **`CourseEditorPage.jsx`:** pass `page="course"`.

- [ ] **Step 5: Locales (9 languages).** Under `authoring.translate`, add (en shown; write real translations for the other 8, keeping `{{placeholders}}`):

```json
"statusUpdating": "Updating",
"updating": "Updating translations…",
"recheckCount": "{{count}} to re-check",
"correctionsReplaced": "corrections replaced",
"changedBadge": "Changed since review",
"markReviewedAgain": "Mark as reviewed again",
"reconfirmScope": "Re-translating {{scope}} into {{language}} will overwrite manual edits to it. Continue?",
"reconfirmEdited": "Re-translating {{scope}} into {{language}} will replace {{count}} hand-corrected parts. Continue?",
"scope": { "activity": "This activity", "module": "This module", "details": "Course details", "course": "Whole course…" },
"scopeName": { "activity": "this activity", "module": "this module", "details": "the course details", "course": "the whole course" },
"kind": { "course": "Course details", "module": "Module", "activity": "Activity", "resource": "Resource" }
```

Merge with a script that never overwrites existing keys and keeps line endings.

- [ ] **Step 6: Verify.**
  - From `frontend/`: `npm run lint`, `npm test`, `node scripts/check-locales.mjs` and `VITE_API_URL=http://localhost:8000/api npm run build`. Expected: all clean.
  - Manual: in a translated course, Re-translate → This activity; only that activity changes. After Mark reviewed and an English edit, "1 to re-check" appears and links to the item.

- [ ] **Step 7: Commit.**

```bash
git add frontend/src
git commit -m "feat: re-translate menu, Updating status, re-check list and 'changed since review' badges"
git push
```

---

### Task 5: Docs and full verification

- [ ] **Step 1: CLAUDE.md.** Under API endpoints:
  - extend the translate line (if absent, add `` `POST /api/authoring/courses/<id>/translate/` — `{language, scope: course|details|module|activity, module_id?, activity_id?}` ``);
  - add `` `GET /api/authoring/courses/<id>/translation-changes/?language=` — items machine-translated since the last review (or `edited=1&scope=…` → hand-corrected count) ``.

- [ ] **Step 2: Full verification.**
  - From `backend/`: `"$UV" run ruff check .`, `"$UV" run coverage run manage.py test hub analytics --verbosity=1`, `"$UV" run coverage report --fail-under=70` and `"$UV" run manage.py makemigrations --check --dry-run`.
  - Frontend: lint, test, locales and build.
  - Expected: all pass.

- [ ] **Step 3: Commit and rollout note.**

```bash
git add CLAUDE.md
git commit -m "docs: scoped re-translation and re-check endpoints"
git push
```

On the VM: `git pull`, `docker compose up -d --build backend celery frontend`, then `docker compose exec -T backend uv run python manage.py migrate` (0071).
