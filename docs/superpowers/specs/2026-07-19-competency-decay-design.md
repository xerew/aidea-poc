# Competency Decay — Design

Approved decisions (user): score can drop from failed quizzes, slowness,
and abandonment; pathway re-assigns on band change in BOTH directions
(this also fixes the pre-existing gap where growth never updated the
pathway); floor 0, cap 6; all knobs admin-editable; backend-only.

## Shared helper — `backend/hub/competency.py`

`apply_competency_delta(user, delta) -> int` (returns the new score):
- no-op when delta is 0 or the clamped score is unchanged
- clamps to 0..6, saves with `update_fields=['competency_score']`
- band = 0-2 beginner / 3-4 intermediate / 5-6 advanced; when the band
  changes (either direction), re-assigns `UserLearningPath` to the
  `LearningPath` whose `competency_min..competency_max` contains the new
  score (`update_or_create`)
- schedules `compute_user_recommendations.delay(user.id)` when the score
  changed

`course_completion_delta(user, course) -> int` computes the increment for
a just-completed course:
- base: `1` when `quiz_affects_competency` is off; otherwise
  `round(quiz_weight_pass)` / `round(quiz_weight_fail)` by comparing the
  user's average quiz score in the course against `quiz_pass_threshold`
  (no quizzes = pass). `quiz_weight_fail` MAY be negative → completing a
  course with failed quizzes can lower the score.
- slowness: when `decay_enabled`, take every completed lesson in the
  course with `duration_minutes > 0` and a recorded
  `time_spent_seconds`; if the average of
  `(time_spent_seconds/60) / duration_minutes` exceeds
  `slow_ratio_threshold`, subtract `slow_penalty`.

The completion hook in `LessonCompleteView` replaces its inline block
(including the old `competency_score < 6` gate — removed so negative
deltas apply at 6) with these two calls.

Behavior change (accepted): recommendations recompute fires only when the
score actually changes, no longer on every completion — the nightly
recompute covers freshness.

## Abandonment — nightly task

`apply_competency_decay` (Celery beat, 04:00, after the recommendation
jobs): when `decay_enabled`, every enrollment with
`0 < progress_pct < 100`, `last_accessed_at` older than
`idle_decay_days`, and `decay_applied_at IS NULL` costs
`idle_decay_points` via the helper and is stamped
(`decay_applied_at = now`) so it is punished at most once per enrollment.
Multiple abandoned courses each cost points. 0%-progress enrollments are
exempt (never started).

## Config (LearnerActivityConfig singleton, admin-editable)

New fields (migration): `decay_enabled` (default True),
`slow_ratio_threshold` (float, default 3.0), `slow_penalty` (int, default
1), `idle_decay_days` (int, default 30), `idle_decay_points` (int,
default 1). Existing quiz fields unchanged (`quiz_weight_fail` default
stays 0.5; set it negative to punish failing). Admin fieldsets gain a
"Decay" section.

New `Enrollment.decay_applied_at` (nullable datetime, migration).

## Out of scope

Frontend changes (badge/pathway update automatically), decay
notifications, re-decay after a user resumes and re-abandons the same
enrollment, session-end heartbeats.
