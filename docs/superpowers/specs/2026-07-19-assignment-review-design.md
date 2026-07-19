# Assignment Review — Design

Approved decisions (user): review is BLOCKING (assignment lessons complete
only on approval); reviewers = course creator for own courses, new
"AIDEA Partner" role and admins for all courses; LLM reviewer is a stubbed
per-module toggle ("later turned on"); resubmission allowed after
"request changes"; already-completed assignment lessons are grandfathered.

## Roles

`UserProfile.UserType` gains `AIDEA_PARTNER = 'aidea_partner'` ("AIDEA
Partner"). Partners: no onboarding gate (it only gates teachers), sidebar =
Home / Courses / Reviews / Profile; cannot author. Reviews sidebar item also
appears for content creators and admins. Partners are created by admins
(Django admin or the app's user-management page — its role dropdowns gain
the option). Seed adds `demo_partner / demo1234`.

## Data

`AssignmentSubmission`: `user` FK, `lesson` FK (assignment lessons only),
`text`, `status` (`pending` / `approved` / `changes_requested`, default
pending), `feedback` (text, blank), `reviewed_by` (nullable user FK),
`reviewed_at` (nullable), `submitted_at` (auto), `updated_at` (auto).
`unique_together (user, lesson)` — resubmitting overwrites `text`, resets
`status` to pending, and keeps the previous `feedback`/reviewer visible as
history. No attempt log in the POC.

`Module.llm_review_enabled` (bool, default False) — admin-editable stub
toggle. `hub/llm_review.py` exposes `review_submission(submission) ->
None` returning None ("model not trained yet"); the review queue calls it
on submission arrival when the module has the toggle on, and a None result
means "leave it for humans". Only the stub body changes when real models
arrive.

## Completion refactor

The completion side-effects (LessonProgress creation with
timing/quiz/engagement, enrollment progress/current-module/completed-at,
competency delta) move out of `LessonCompleteView.post` into
`hub/completion.py`: `record_lesson_completion(user, enrollment, lesson,
quiz_answers_raw=None, engagement_data=None) -> (lesson_progress,
progress_pct)`. `LessonCompleteView` delegates to it and now returns 400
`{'detail': 'Assignments are completed through review.'}` for
`lesson_type='assignment'`. Approval calls the same helper on the
learner's behalf — no duplicated logic, competency/progress semantics
identical.

## API

- `POST /api/courses/<pk>/lessons/<lesson_pk>/submit-assignment/`
  `{text}` (learner; enrolled; assignment lessons only; non-empty text;
  409-style 400 when already approved) → creates/updates the submission to
  pending, calls the LLM stub if the module toggle is on, returns the
  submission payload.
- `GET /api/courses/<pk>/lessons/<lesson_pk>/` gains
  `assignment_submission: {id, status, text, feedback, submitted_at,
  reviewed_at} | null` for assignment lessons.
- `GET /api/reviews/` (reviewer-only) → pending submissions in
  `submitted_at` order, scoped: creators see their own courses' submissions,
  partners/admins see all. Each row: id, learner name, course/lesson/module
  titles, text, submitted_at, previous feedback.
- `POST /api/reviews/<id>/` `{action: 'approve'|'request_changes',
  feedback}` (reviewer-only, same scoping): approve → status approved,
  reviewer stamped, lesson completed for the learner via
  `record_lesson_completion` (engagement carries submission + word count);
  request_changes → requires non-empty feedback, status changes_requested.
  Reviewing a non-pending submission → 400.

Permission: `IsReviewer` (content_creator / aidea_partner / admin);
creators additionally object-scoped to `course.created_by == user`.

## Frontend

- **LessonPage** assignment states driven by `assignment_submission`:
  none → editable textarea + "Submit for review" (Mark Complete hidden for
  assignments, like quizzes); pending → read-only text + "Submitted —
  pending review" banner; changes_requested → feedback panel + editable
  textarea + "Resubmit"; approved → completed state (server already marked
  the lesson complete).
- **ReviewsPage** (`/reviews`): pending queue; expanding a row shows the
  submission text and previous feedback; Approve button and Request-changes
  (textarea + button). Visible to creator/partner/admin via sidebar
  "Reviews"; others redirected home.
- **AdminPage** role dropdowns gain AIDEA Partner.

## Out of scope

Attempt history, reviewer assignment/routing, notifications, actual LLM
calls, deadlines/SLAs, grading scores.
