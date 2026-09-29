# Activities & Resources — Design Spec

**Date:** 2026-09-29
**Status:** Draft for review
**Author:** Nikos (with Claude)

## Goal

Restructure course content so that a learning unit ("Activity", renamed from
"Lesson") can contain **multiple ordered "Resources"** of mixed types (text,
video, image, PDF, quiz, assignment), instead of today's one-type-per-lesson
model. An author can, for example, build a single activity that combines a
reading, a video, and a quiz.

## Background: the current model

```
LearningPillar → Course → Module → Lesson
```

`Lesson` carries a single `lesson_type` (`text`/`video`/`image`/`pdf`/`quiz`/
`assignment`) plus `content` (rich text), `media_items` (JSON list of extra
image/video/pdf attachments), and `quiz_data` (JSON, used only when the type is
`quiz`). Progress is one `LessonProgress` row per user × lesson
(`completed_at`, `time_spent_seconds`, `quiz_score`). `AssignmentSubmission`
FKs a `Lesson`. Quiz checking, assignment submission/review, analytics,
recommendation embeddings, XLSX import/export, and the learner/authoring UIs all
key off the lesson.

So mixing text + images/videos/PDFs in one unit is *partly* supported already
(via `content` + `media_items`); the true single-type constraints are the
**quiz** and **assignment** behaviours and the `lesson_type` label.

## Decisions (locked in brainstorming)

1. **Storage:** a **Resource child table** — each block is a row with its own id
   (so quizzes and assignments get real identities for scoring, submission and
   review).
2. **Completion:** **per-resource, aggregated up** — track each resource's state
   individually; an activity is complete when all its *required* resources are.
3. **Rename depth:** **full rename** — model, API and UI (`Lesson`→`Activity`,
   `lesson_type` removed, `/lessons/`→`/activities/`, `LessonProgress`→
   `ResourceProgress`).
4. **Resource payload:** **typed columns** (not one opaque JSON), to keep
   validation and reporting simple.
5. **Assignment** is in scope (existing assignment lessons must migrate to
   assignment resources); the *authoring UI* for multiple assignments per
   activity may be a fast-follow (see Phasing).

## New data model

### Activity (renamed from `Lesson`)
- `module` (FK), `title`, `description`, `order`, `duration_minutes`,
  `is_required`, `translations` (JSON: `{lang: {title, description}}`).
- **Removed:** `lesson_type`, `content`, `media_items`, `quiz_data` (move to
  Resource).

### Resource (new)
- `activity` (FK, `related_name='resources'`), `order`, `is_required`.
- `type` — `text` | `video` | `image` | `pdf` | `quiz` | `assignment`.
- Typed payload columns:
  - `title` (optional, per-resource heading), `content` (text body, for `text`),
  - `url`, `caption` (for `video`/`image`/`pdf`),
  - `quiz_data` (JSON, for `quiz`) — same shape as today,
  - `instructions` (text, for `assignment`).
- `translations` (JSON: `{lang: {title, content, caption, instructions,
  quiz_data}}` — only the fields relevant to the type).

### ResourceProgress (replaces `LessonProgress`)
- `user` (FK), `resource` (FK), `completed_at` (nullable), `time_spent_seconds`,
  `quiz_score` (nullable; for quiz resources), `updated_at`.
- Unique `(user, resource)`.

## Completion & progress aggregation

Per-resource completion rule by type:
- `text`/`video`/`image`/`pdf` → complete when viewed / marked done.
- `quiz` → complete when **passed** (reuse the existing quiz pass threshold from
  `LearnerActivityConfig`); `quiz_score` stored on the ResourceProgress.
- `assignment` → complete when the submission is **approved** by a reviewer.

Aggregation:
- **Activity complete** ⇔ every *required* resource has a completed
  ResourceProgress for that user.
- **Module / Course progress %** derived from completed vs. total required
  resources (or activities — to be pinned in the plan; recommend counting
  required resources for accuracy, exposed as activity-level ticks in the UI).
- `Enrollment.progress_pct` recomputed from resource completion.

## Quizzes, assignments & review

- **Quiz check** becomes per-resource:
  `POST /activities/<id>/resources/<rid>/quiz-check/` scores one quiz resource
  and writes its ResourceProgress `quiz_score` + completion.
- **Assignment submission** FK moves `lesson` → `resource`. An activity may hold
  several assignment resources; each is submitted and reviewed independently.
- **Review queue** lists one item per pending assignment *resource*. The
  reviewer approve/return flow is unchanged except it targets a resource; on
  approve, that resource's ResourceProgress completes and the activity re-checks
  its aggregate.
- **Co-author review scoping** (recently added) already walks
  course→module→lesson; it becomes course→module→activity→resource. `can_edit`
  gating is unchanged in spirit.

## API changes (full rename)

- Authoring: `/authoring/courses/<id>/modules/<mid>/lessons/…` →
  `…/activities/…`; new nested `…/activities/<aid>/resources/…` (create,
  update, delete, reorder).
- Learner: `/courses/<id>/lessons/<lid>/…` → `…/activities/<aid>/…`;
  quiz-check and submit-assignment move under the resource.
- Serializers renamed (`LessonAuthoringSerializer` → `ActivityAuthoringSerializer`,
  add `ResourceSerializer`); learner serializers expose an activity with its
  ordered resources and per-resource progress.

## Learner experience

An activity renders as **one page** listing its resources in order: a text
block, then an embedded video, then a quiz widget, etc. Each resource shows its
own completion state; the activity marks complete when required resources are
done. "Continue learning" and pathway/next-activity navigation operate at the
activity level.

## Authoring experience

Within a module the author adds **activities**; within an activity they add and
reorder **resources**, each with a type-appropriate editor (rich-text, URL /
file upload, quiz builder, assignment instructions) and an `is_required`
toggle. Replaces the current one-type-per-lesson editor. Translation editing is
per-resource, reusing the existing language-bar pattern.

## Data migration (existing production data)

For each existing `Lesson` create one `Activity` (same title/description/order/
duration/is_required/translations), then create resources:
- A `text` resource from `content` (if non-empty).
- One resource per `media_items` entry (`image`/`video`/`pdf` with `url`/`caption`).
- If `lesson_type == 'quiz'`: a `quiz` resource from `quiz_data`.
- If `lesson_type == 'assignment'`: an `assignment` resource from `content`/
  `description` as `instructions`.
- Preserve order (content first, then media, then quiz/assignment).

Progress & submissions:
- Each `LessonProgress` → a `ResourceProgress` on the migrated activity's
  resources: completion maps to all its required resources (so previously
  completed lessons stay complete); `quiz_score` maps to the quiz resource.
- `AssignmentSubmission.lesson` → the migrated `assignment` resource.
- Recompute `Enrollment.progress_pct` post-migration.
- Migrate translations into per-resource `translations`.

The migration must be reversible-enough to test on a **copy of prod data** and
idempotent where practical.

## Cross-cutting updates

- **Recommendations/embeddings:** `compute_course_embeddings` reads lesson text;
  update to read activity/resource text.
- **Analytics:** per-course stats and the teacher drill-down read lessons/
  progress; update to activities/resources/ResourceProgress. (Optional: expose
  per-resource stats later.)
- **XLSX import/export:** `authoring_xlsx` sheets/rows model modules→lessons;
  extend to activities→resources (new columns for resource type & payload).
- **i18n:** rename "Lesson"→"Activity" and add "Resource" across **all 9
  locales**; keep parity (`check-locales.mjs`).
- **Django admin:** `LessonInline`/`LessonAdmin` → `ActivityAdmin` with a
  `ResourceInline`.
- **LessonSession** (time tracking) → `ActivitySession` (or keep, retargeted).

## Permissions

Unchanged in spirit: authoring/edit gated by `can_edit_course` (author/admin/
co-editor); translation by `can_translate_course`; delete/manage by
`can_manage_course`. Resource CRUD inherits the parent course's gate.

## Phasing / build order

Because the API renames, backend and frontend must ship together. Build order,
on a feature branch:

1. **Models + migration** (Activity, Resource, ResourceProgress) with the data
   migration; verified on a prod-data copy. Tests for the migration mapping.
2. **Backend APIs & logic** rewritten to activities/resources: authoring CRUD,
   learner rendering, per-resource quiz-check, assignment submit/review,
   completion aggregation, analytics, embeddings, XLSX. Full test suite green.
3. **Frontend:** learner activity/resource renderer; authoring activity/resource
   editor; i18n rename (9 locales). Lint + build.
4. **Cutover:** deploy backend+frontend together; run migration.

Optional fast-follow (kept out of Phase 1 if we want to de-risk): authoring UI
for *multiple assignments per activity* (the model supports it from day one; the
editor can start with at most one assignment resource per activity).

## Testing

- Migration: fixture of representative lessons (text+media, quiz, assignment,
  translated) → asserts resources, progress, submissions, translations, and
  recomputed `progress_pct` are correct.
- Completion aggregation: activity completes only when all required resources do;
  optional resources don't block.
- Per-resource quiz-check and assignment review update the right resource and
  re-aggregate.
- Permissions parity with co-author roles.
- Locale parity.

## Risks & rollout

- **Largest change to date**: core model + production data migration + learner/
  authoring rewrites + 9-locale rename. Multi-step, multi-session.
- **Data migration on real content** is the top risk — mitigate by testing on a
  DB copy and taking a fresh backup immediately before cutover (the scheduled
  pg_dump + a manual dump).
- **API break**: frontend and backend must deploy together; no partial rollout.
- Recommendation embeddings should be recomputed after migration.

## Open questions (to resolve in the plan)

1. Course/module progress %: count required **resources** or **activities**?
   (Recommend resources for accuracy, shown as activity ticks.)
2. Keep `LessonSession` retargeted vs. rename to `ActivitySession`.
3. Whether the Phase-1 authoring editor allows multiple assignment resources per
   activity or defers that to the fast-follow.
