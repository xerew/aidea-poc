# Activities & Resources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure course content so a Module contains **Activities** (renamed from Lessons), and each Activity contains multiple ordered **Resources** (text/video/image/pdf/quiz/assignment), with per-resource progress aggregated up.

**Architecture:** New `Resource` child table under an `Activity` (renamed `Lesson`); `ResourceProgress` replaces `LessonProgress`; a Django data migration converts every existing lesson into one activity plus resources, preserving progress, submissions and translations. Full rename across models, API and UI. Backend + frontend ship together (the API renames).

**Tech Stack:** Django 6 / DRF, PostgreSQL (pgvector), Celery, React 19 / Vite, react-i18next (9 locales).

**Spec:** `docs/superpowers/specs/2026-09-29-activities-resources-design.md`

## Plan revision (2026-09-29, middle path)

Agreed adjustments to reduce risk without losing structural value:
- **Rename the model** `Lesson`→`Activity` (cheap `RenameModel`), but **keep the
  `/lessons/` endpoint paths** — no API break, no dead deep-links. Task 1.6 and
  Phase 2 keep URL paths as `/lessons/…`; only identifiers/serializers/UI labels
  change.
- **Keep the legacy columns** (`lesson_type/content/media_items/quiz_data`,
  `LessonProgress`, `AssignmentSubmission.lesson`) at cutover — they are the
  rollback window. Task 1.6 does NOT drop them; a separate cleanup migration
  drops them weeks later once stable.
- **Progress parity gate:** after the data migration, assert every existing
  `Enrollment.progress_pct` is unchanged.
- Prep (done): recommendation `IntegrityError` fixed on `master`; work proceeds
  on branch `feature/activities-resources`.

## Global Constraints

- Runner: `.venv/Scripts/uv.exe run manage.py …` from `backend/` (or global `~/.local/bin/uv.exe`). Tests: `… test hub analytics`. Lint: `ruff check hub analytics` (E501 ignored; `--fix` for import order).
- Frontend: `npm run lint`, `npm run build` (needs `VITE_API_URL`); locale parity via `node scripts/check-locales.mjs` — **all 9 locales** (en, el, fr, es, it, fi, sv, no, de) must stay at equal key counts. Edit locales with a Python script using literal UTF-8, `object_pairs_hook=OrderedDict`, `json.dump(ensure_ascii=False, indent=2)` + trailing newline.
- Resource types: `text`, `video`, `image`, `pdf`, `quiz`, `assignment` (exactly one per resource).
- Resource payload = **typed columns** (not one JSON): `title`, `content`, `url`, `caption`, `quiz_data` (JSON), `instructions`, `translations` (JSON).
- Completion: `text/video/image/pdf` → viewed; `quiz` → passed (reuse `LearnerActivityConfig` quiz threshold); `assignment` → approved. Activity complete ⇔ all **required** resources complete. Course/module % counted over **required resources**.
- Commit trailer on every commit: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Work on a feature branch; take a fresh `pg_dump` before running the data migration at cutover.
- New `Activity` model lives in `hub/models/content.py` (NOT `hub/models/activity.py`, which already holds `LessonSession`/`LearnerActivityConfig`).

## File Structure

**Backend**
- `hub/models/content.py` — rename `Lesson`→`Activity`; add `Resource`. (`Module` unchanged.)
- `hub/models/enrollment.py` — `LessonProgress`→`ResourceProgress` (FK `lesson`→`resource`).
- `hub/models/assignment.py` — `AssignmentSubmission.lesson`→`resource`.
- `hub/models/activity.py` — `LessonSession`→`ActivitySession` (FK retargeted).
- `hub/migrations/00NN_*` — schema + **data** migrations (the core risk).
- `hub/completion.py` — `record_lesson_completion`→resource-based completion + activity/module/course aggregation.
- `hub/serializers/content.py`, `hub/serializers/course.py` — Activity/Resource serializers; learner + authoring shapes.
- `hub/views/authoring_lesson.py`→`authoring_activity.py` (+ new `authoring_resource.py`); `hub/views/learner.py`, `hub/views/assignments.py` — retarget to activities/resources.
- `hub/views/__init__.py`, `hub/urls.py` — endpoint renames + new resource routes.
- `hub/tasks.py` — `compute_course_embeddings` reads resources.
- `hub/xlsx_transfer.py`, `hub/views/authoring_xlsx.py` — activities→resources columns.
- `hub/admin.py` — `ActivityAdmin` + `ResourceInline`.
- `analytics/views.py`, `analytics/serializers.py`, `analytics/reports.py` — activities/resources/ResourceProgress.
- `hub/management/commands/seed.py` — seed activities+resources.

**Frontend**
- `src/pages/LessonPage.jsx`→`ActivityPage.jsx` — render an activity's resources in order with per-resource progress; per-resource quiz/assignment.
- `src/pages/ModuleEditorPage.jsx` — edit activities and their resources (resource list + per-type editors).
- `src/pages/CourseDetailPage.jsx`, `CourseLearnPage`/redirects, `MyLearningPage.jsx`, `PathwayPage.jsx` — activity terminology + navigation.
- New `src/components/authoring/ResourceEditor.jsx` + per-type sub-editors.
- New `src/components/learner/ResourceView.jsx` + per-type renderers.
- `src/locales/*.json` (9) — Lesson→Activity, add Resource keys.

---

## Phase 1 — Models & data migration (foundation, fully specified)

> Phase 1 adds the new structure and converts existing data. After Phase 1 the
> old names still exist only where later phases rewire them; the **test suite
> stays green** because Phase 1 tasks add models + migrations without deleting
> the old read paths until Task 1.6.

### Task 1.1: `Resource` model

**Files:**
- Modify: `hub/models/content.py` (add `Resource` after `Lesson`)
- Modify: `hub/models/__init__.py` (export `Resource`)
- Test: `hub/tests/test_resources.py`

**Interfaces:**
- Produces: `Resource(activity FK, type, order, is_required, title, content, url, caption, quiz_data, instructions, translations)`; `Resource.Type` choices `TEXT/VIDEO/IMAGE/PDF/QUIZ/ASSIGNMENT`.

- [ ] **Step 1: Failing test**
```python
# hub/tests/test_resources.py
from django.test import TestCase
from hub.models import Course, LearningPillar, Module, Lesson, Resource

class ResourceModelTest(TestCase):
    def setUp(self):
        p = LearningPillar.objects.create(name='P', slug='p', order=1)
        c = Course.objects.create(title='C', pillar=p)
        self.m = Module.objects.create(title='M', course=c, order=1)
        self.a = Lesson.objects.create(module=self.m, title='A', order=1)  # Lesson == Activity pre-rename

    def test_create_resource(self):
        r = Resource.objects.create(activity=self.a, type='text', order=1, content='hello')
        self.assertEqual(self.a.resources.count(), 1)
        self.assertTrue(r.is_required)
        self.assertEqual(r.type, 'text')
```
- [ ] **Step 2: Run → fails** (`… test hub.tests.test_resources` → ImportError `Resource`).
- [ ] **Step 3: Implement** — add to `content.py`:
```python
class Resource(models.Model):
    class Type(models.TextChoices):
        TEXT = 'text', 'Text'; VIDEO = 'video', 'Video'; IMAGE = 'image', 'Image'
        PDF = 'pdf', 'PDF'; QUIZ = 'quiz', 'Quiz'; ASSIGNMENT = 'assignment', 'Assignment'
    activity     = models.ForeignKey('hub.Lesson', on_delete=models.CASCADE, related_name='resources')
    type         = models.CharField(max_length=20, choices=Type.choices)
    order        = models.PositiveSmallIntegerField(default=0)
    is_required  = models.BooleanField(default=True)
    title        = models.CharField(max_length=200, blank=True)
    content      = models.TextField(blank=True)
    url          = models.CharField(max_length=500, blank=True)
    caption      = models.CharField(max_length=300, blank=True)
    quiz_data    = models.JSONField(default=list, blank=True)
    instructions = models.TextField(blank=True)
    translations = models.JSONField(default=dict, blank=True)
    class Meta:
        ordering = ['order']
    def __str__(self):
        return f'{self.activity.title} — {self.get_type_display()}'
```
(FK targets `'hub.Lesson'` now; Task 1.6 renames the model to `Activity` and this string updates to `'hub.Activity'`.)
- [ ] **Step 4: makemigrations + migrate + test → pass.**
- [ ] **Step 5: Commit** `feat: add Resource model`.

### Task 1.2: `ResourceProgress` model

**Files:** Modify `hub/models/enrollment.py` (add `ResourceProgress` alongside `LessonProgress`), `hub/models/__init__.py`; Test `hub/tests/test_resource_progress.py`.

**Interfaces:** Produces `ResourceProgress(user, resource FK, completed_at, time_spent_seconds, quiz_score, quiz_answers, engagement_data, updated_at)`, unique `(user, resource)`.

- [ ] **Step 1: Failing test** — create a ResourceProgress, assert unique_together raises on duplicate `(user, resource)`.
- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement** (mirror `LessonProgress` fields, FK → `Resource`, add `unique_together = ('user', 'resource')` and `updated_at = auto_now`). Keep `LessonProgress` untouched for now.
- [ ] **Step 4: makemigrations + migrate + test → pass.**
- [ ] **Step 5: Commit** `feat: add ResourceProgress model`.

### Task 1.3: `AssignmentSubmission.resource` FK (add, keep `lesson`)

**Files:** Modify `hub/models/assignment.py`; Test `hub/tests/test_assignment_resource_fk.py`.

- [ ] **Step 1: Failing test** — create submission with `resource=`, assert reachable via `resource.submissions`.
- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement** — add `resource = models.ForeignKey('hub.Resource', null=True, blank=True, on_delete=models.CASCADE, related_name='submissions')`. (Keep `lesson` FK for the data migration; drop it in Task 1.6.)
- [ ] **Step 4: migrate + test → pass.**
- [ ] **Step 5: Commit** `feat: add AssignmentSubmission.resource fk`.

### Task 1.4: Data migration — lessons → activities + resources

**Files:** Create `hub/migrations/00NN_split_lessons_into_resources.py` (a `RunPython` data migration); Test `hub/tests/test_content_migration.py` (uses the migration's forward function directly against a built fixture).

**Interfaces:** Produces, for every `Lesson`: `Resource` rows per the mapping in the spec. Consumes Tasks 1.1–1.3 models.

- [ ] **Step 1: Failing test** — build a module with four lessons (text+2 media_items; video; quiz with quiz_data; assignment), call `migrate_lessons_to_resources(apps, None)`, assert:
  - text lesson → 1 text resource (content) + 2 media resources (correct type/url/caption, order 2,3);
  - video lesson → 1 video resource (url from content or media);
  - quiz lesson → 1 quiz resource (quiz_data preserved);
  - assignment lesson → 1 assignment resource (instructions from content/description);
  - each resource `is_required` = parent lesson `is_required`; translations copied to the matching resource fields.
- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement** the forward function (historical models via `apps.get_model`). Mapping rules exactly as the spec's "Data migration" section. Deterministic ordering: content(→text) first, then media_items in order, then quiz/assignment. For video/image/pdf lessons whose `content` is a URL, use it as the resource `url`.
- [ ] **Step 4: Run test → pass.** Also run full suite → green.
- [ ] **Step 5: Commit** `feat: data migration splitting lessons into resources`.

### Task 1.5: Data migration — LessonProgress → ResourceProgress, submissions → resource

**Files:** Same migration module or a follow-on `00NN_migrate_progress_and_submissions.py`; Test extends `test_content_migration.py`.

- [ ] **Step 1: Failing test** — with progress on a completed text-lesson and a quiz-lesson (quiz_score=0.8) and a pending AssignmentSubmission on the assignment-lesson: after migration assert
  - a `ResourceProgress` exists (completed) for each required resource of the completed activities;
  - the quiz resource's ResourceProgress carries `quiz_score=0.8`;
  - the AssignmentSubmission now points to the assignment resource (`submission.resource_id` set), status preserved.
- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement** — for each `LessonProgress`, create `ResourceProgress` for every resource of the migrated activity, copying `completed_at`/`time_spent_seconds`/`quiz_answers`/`engagement_data`; put `quiz_score` on the quiz resource. Repoint each `AssignmentSubmission.resource` to the activity's assignment resource.
- [ ] **Step 4: Test → pass; full suite → green.**
- [ ] **Step 5: Commit** `feat: migrate progress and submissions to resources`.

### Task 1.6: Rename Lesson→Activity, LessonProgress→ResourceProgress cleanup, drop legacy columns

**Files:** `content.py`, `enrollment.py`, `assignment.py`, `activity.py`, `__init__.py`, `admin.py`; migration `00NN_rename_and_drop_legacy.py`.

- [ ] **Step 1: Failing test** — `from hub.models import Activity` works; `Lesson` no longer importable; `Activity` has no `lesson_type/content/media_items/quiz_data`; `LessonProgress` gone.
- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement** — `migrations.RenameModel('Lesson','Activity')`; update `Resource.activity` FK string to `'hub.Activity'`; `RenameModel('LessonSession','ActivitySession')` + FK; **remove** `Activity` fields `lesson_type/content/media_items/quiz_data`; **delete** `LessonProgress` model + `AssignmentSubmission.lesson` field; rename reverse relations (`progress_records`→`resource_progress`, etc.). Update `hub/models/__init__.py` `__all__` and `admin.py` inlines to `ActivityAdmin`+`ResourceInline`.
- [ ] **Step 4: makemigrations (review the auto-generated ops carefully — ensure RenameModel not Delete+Create), migrate, test → pass; full suite (will have failures in views referencing old names — those are Phase 2).**
- [ ] **Step 5: Commit** `refactor: rename Lesson→Activity, drop legacy lesson columns`.

> **Phase 1 gate:** models + migrations complete and tested on a **copy of prod data** (`pg_dump` prod → restore locally → run migrations → spot-check a sample of courses/enrollments/submissions). Do NOT proceed to cutover; Phases 2–3 must land first.

---

## Phase 2 — Backend rewire (task list; step-level code pinned at phase start)

Each task is TDD (write/adjust the failing test from the existing suite, implement, green, commit). Detailed code is filled in when Phase 2 begins, against the concrete models from Phase 1.

- [ ] **Task 2.1 — Completion & aggregation** (`hub/completion.py`): resource completion writes `ResourceProgress`; new `recompute_activity/module/course_progress`. Tests: activity completes only when all required resources complete; optional resources don't block; `Enrollment.progress_pct` correct.
- [ ] **Task 2.2 — Serializers** (`serializers/content.py`, `serializers/course.py`): `ResourceSerializer`, `ActivityAuthoringSerializer` (with ordered resources), learner activity serializer (resources + per-resource progress). Tests: shape + `my` progress fields.
- [ ] **Task 2.3 — Authoring endpoints** (`views/authoring_activity.py`, new `authoring_resource.py`, `urls.py`): activity CRUD + resource CRUD + reorder, gated by `can_edit_course`; translations per-resource via `?lang=` gated by `can_translate_course`. Tests: co-editor/translator parity (reuse `test_collaborators` patterns).
- [ ] **Task 2.4 — Learner endpoints** (`views/learner.py`, `urls.py`): course/activity read; mark-resource-viewed; per-resource **quiz-check** (`/activities/<id>/resources/<rid>/quiz-check/`) reusing the quiz threshold. Tests: viewing/ passing a quiz resource completes it and re-aggregates.
- [ ] **Task 2.5 — Assignments & review** (`views/assignments.py`): submit + review target a **resource**; review queue lists one item per assignment resource; approve completes that resource. Tests: multiple assignment resources reviewed independently; co-author scoping (course→module→activity→resource) still holds.
- [ ] **Task 2.6 — Embeddings** (`tasks.py`): `compute_course_embeddings` reads resource text. Test: embedding input concatenates activity+resource content.
- [ ] **Task 2.7 — Analytics** (`analytics/*`): stats + teacher drill-down over activities/resources/ResourceProgress. Tests: counts match; co-editor scoping intact.
- [ ] **Task 2.8 — XLSX import/export** (`xlsx_transfer.py`, `authoring_xlsx.py`): activities→resources rows/columns (resource `type` + payload). Tests: round-trip a course with a mixed activity.
- [ ] **Task 2.9 — Seed + fixtures** (`management/commands/seed.py`): seed demo courses as activities+resources (incl. one mixed activity). Test: seed runs; sample activity has ≥2 resources.
- [ ] **Task 2.10 — Full suite + ruff green; commit.**

## Phase 3 — Frontend + i18n (task list)

- [x] **Task 3.1 — Learner ActivityPage** (`ActivityPage.jsx` + `components/learner/ResourceView.jsx` per-type renderers): render resources in order with per-resource completion; per-resource quiz/assignment widgets.
- [x] **Task 3.2 — Authoring resources** (`ModuleEditorPage.jsx` + `components/authoring/ResourceEditor.jsx`): add/reorder resources with per-type editors; `is_required` toggle; per-resource translation editing (reuse language bar). Respect `can_edit`/`can_translate`/`can_manage` caps.
- [x] **Task 3.3 — Navigation & terminology** (`CourseDetailPage`, learn redirects, `MyLearningPage`, `PathwayPage`, `HomePage`): activity-level nav; "Continue learning" → next activity.
- [x] **Task 3.4 — i18n rename** (`locales/*.json` ×9): Lesson→Activity, add Resource keys; parity check green.
- [x] **Task 3.5 — Lint + build; commit.**

**Phase 3 notes:** every activity keeps ≥1 resource (seeded on create, last one undeletable); machine translation covers resources; navigation needed no structural change (learn redirect/continue already activity-level); unused editor keys pruned. Still deferred: resource-aware content XLSX, user-guide wording (lessons → activities), legacy-column cleanup migration.

## Cutover (after all phases pass)

- [ ] Take a fresh manual `pg_dump` (in addition to the scheduled backup).
- [ ] Deploy backend+frontend together: `git pull` → `up -d --build backend frontend celery` → `migrate` → recompute embeddings.
- [ ] Smoke-test: an existing course renders; a mid-progress enrollment keeps its %; author a mixed activity; submit + review an assignment resource.

## Self-Review

**Spec coverage:** models (1.1–1.3, 1.6) ✓; completion/aggregation (2.1) ✓; API rename (2.3–2.5) ✓; quizzes/assignments per-resource (2.4–2.5) ✓; learner UX (3.1) ✓; authoring UX (3.2) ✓; data migration (1.4–1.5) ✓; embeddings (2.6) ✓; analytics (2.7) ✓; XLSX (2.8) ✓; i18n (3.4) ✓; permissions parity (2.3, 2.5) ✓; admin (1.6) ✓; `LessonSession`→`ActivitySession` (1.6) ✓.

**Open questions resolved:** progress % counted over **required resources** (spec §Completion); `LessonSession`→`ActivitySession` renamed (Task 1.6); Phase-1 authoring editor allows any resource types incl. multiple assignments (uniform resource model — no special-casing).

**Placeholder note:** Phase 1 is fully code-specified. Phases 2–3 are task-scoped with explicit files, deliverables and tests; their step-level code is written at each task's execution against Phase 1's concrete shapes (deliberate — the code depends on exact model/serializer names finalized in Phase 1, and writing it speculatively now would drift). Each Phase 2–3 task still follows the TDD five-step cycle.
