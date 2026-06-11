# Learner Activity Tracking — Design Spec

## Goal

Capture rich engagement data for every lesson interaction — timing, quiz performance, and type-specific signals — so the platform produces research-grade longitudinal data from the moment teachers onboard. Quiz performance can optionally influence competency scoring via a configurable toggle and weights.

## Architecture

All tracking data lands on an enriched `LessonProgress` row. A lightweight `LessonSession` model captures when a lesson is opened so that `time_spent_seconds` can be computed server-side without any frontend timing logic. A new `LearnerActivityConfig` singleton (same pattern as `RecommendationConfig`) holds the quiz-competency toggle and weights. The `POST .../complete/` endpoint is extended to accept engagement signals from the frontend; the server computes quiz scores itself — never trusting the client.

## Tech Stack

Django 5.1, Django REST Framework, uv, ruff, SQLite (dev), PostgreSQL (prod)

---

## Data Model

### 1. `LessonProgress` — enriched

Current fields: `user`, `lesson`, `completed_at` (auto_now_add).

**Changes:**

| Field | Type | Notes |
|---|---|---|
| `completed_at` | `DateTimeField(null=True, blank=True)` | Change from `auto_now_add` to explicit; set in `LessonCompleteView` |
| `time_spent_seconds` | `IntegerField(null=True, blank=True)` | Computed server-side from `LessonSession` |
| `quiz_score` | `FloatField(null=True, blank=True)` | 0.0–1.0; computed server-side from `quiz_answers`; null for non-quiz lessons |
| `quiz_answers` | `JSONField(default=list)` | `[true, false, true]` — one boolean per question; empty for non-quiz lessons |
| `engagement_data` | `JSONField(default=dict)` | Type-specific signals (see below) |

**`engagement_data` shape by lesson type:**

| Lesson type | Shape |
|---|---|
| `text` | `{"scroll_pct": 85}` — how far down the page the teacher scrolled (0–100) |
| `video` | `{"video_pct": 90}` — how far through the video they got (0–100) |
| `assignment` | `{"submission": "...", "word_count": 150}` — submitted text; `word_count` computed server-side as `len(submission.split())` |
| `quiz` | `{}` — quiz data lives in `quiz_answers` / `quiz_score` |
| `pdf`, `image` | `{}` — timing only (no type-specific signal) |

### 2. `LessonSession` — new model

Created each time `LessonDetailView.get()` is called. No unique constraint — a teacher can open a lesson multiple times. `LessonCompleteView` picks the most recent session to compute `time_spent_seconds`.

```python
class LessonSession(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_sessions')
    lesson     = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']
```

### 3. `LearnerActivityConfig` — new singleton

Same pattern as `RecommendationConfig`: `pk=1`, `save()` forces `self.pk = 1`, `get()` classmethod.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `quiz_affects_competency` | `BooleanField` | `False` | Master toggle; when False, completion increments competency exactly as today |
| `quiz_pass_threshold` | `FloatField` | `0.7` | Minimum `quiz_score` average to be considered "passing" the course |
| `quiz_weight_pass` | `FloatField` | `1.0` | Competency increment multiplier when average quiz score ≥ threshold |
| `quiz_weight_fail` | `FloatField` | `0.5` | Competency increment multiplier when average quiz score < threshold |

---

## API Changes

### `POST /api/courses/<pk>/lessons/<lesson_pk>/complete/`

Accepts an optional JSON body. All fields are optional and backward-compatible — existing callers that send no body continue to work.

**Request body (new optional fields):**

```json
{
  "quiz_answers": [2, 0, 2],
  "engagement_data": {
    "scroll_pct": 85
  }
}
```

- `quiz_answers`: array of selected option indices (one integer per question). Only sent for quiz lessons. Server evaluates each against `lesson.quiz_data[i].options[answer].is_correct` and stores the boolean results.
- `engagement_data`: type-specific signals. Frontend sends what it knows; server stores it verbatim. For assignment lessons, server derives `word_count` from `submission` text.

**Server-side processing in `LessonCompleteView.post()`:**

1. Find most recent `LessonSession` for this user+lesson → compute `time_spent_seconds = (now - session.started_at).seconds`. If no session exists (e.g., direct API call), `time_spent_seconds` stays `null`.
2. If `quiz_answers` provided and `lesson.lesson_type == 'quiz'`: evaluate each answer, store boolean array, compute `quiz_score`.
3. Store `engagement_data` (add `word_count` for assignment type).
4. Set `completed_at = timezone.now()` on `LessonProgress`.
5. If `just_completed`: run competency progression (see below).

### `GET /api/courses/<pk>/lessons/<lesson_pk>/`

No change to response. Side effect added: creates a `LessonSession` row for the requesting user.

---

## Competency Progression (updated)

Controlled by `LearnerActivityConfig`.

**When `quiz_affects_competency = False` (default):**
Behaviour unchanged. Course completion → `competency_score += 1` (capped at 6).

**When `quiz_affects_competency = True`:**
On first course completion, compute the average `quiz_score` across all quiz-type `LessonProgress` rows for that enrollment.

- If no quiz lessons exist in the course → fall back to full increment (treated as passing).
- If average ≥ `quiz_pass_threshold` → apply `quiz_weight_pass`.
- If average < `quiz_pass_threshold` → apply `quiz_weight_fail`.

Increment = `min(competency_score + quiz_weight_pass_or_fail, 6)`.

Example with defaults: passing teacher gets +1.0, struggling teacher gets +0.5 (rounds to nearest integer for storage since `competency_score` is `PositiveSmallIntegerField`; fractional progress is lost unless the field type is changed — keep as integer for now).

> **Note:** Fractional competency scores would require changing `competency_score` to `FloatField`. Deferred — integer is sufficient for phase 1.

---

## Analytics Impact

The existing `AnalyticsOverviewView` counts quiz attempts via `LessonProgress.objects.filter(lesson__lesson_type='quiz')`. Once `quiz_score` is populated, the analytics app can expose:
- Average quiz score per course
- Average time spent per lesson type
- Assignment submission text for qualitative analysis

No analytics view changes are in scope for this spec — the data will be present for future querying.

---

## What the Frontend Needs to Send

| Lesson type | Extra field(s) to send on complete |
|---|---|
| `quiz` | `quiz_answers: [2, 0, 1, ...]` — selected option index per question |
| `text` | `engagement_data: {"scroll_pct": N}` |
| `video` | `engagement_data: {"video_pct": N}` |
| `assignment` | `engagement_data: {"submission": "..."}` |
| `pdf`, `image` | nothing extra (timing captured server-side) |

---

## Out of Scope

- Fractional `competency_score` (integer is sufficient for now)
- Analytics dashboard UI changes
- Retry/re-attempt tracking for quizzes (first attempt only)
- Raw mouse-movement tracking
