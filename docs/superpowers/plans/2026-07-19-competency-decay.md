# Competency Decay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The AI competency score can decrease — failed quizzes and slow completions shrink the course-completion increment (possibly below zero), abandoned courses decay nightly — and the assigned pathway re-tracks the score's band in both directions.

**Architecture:** A new `hub/competency.py` owns the delta/band logic; `LessonCompleteView`'s inline block delegates to it; a nightly Celery task applies idle decay. Config knobs extend the `LearnerActivityConfig` singleton. Spec: `docs/superpowers/specs/2026-07-19-competency-decay-design.md`.

**Tech Stack:** Django/DRF, Celery beat. Backend only.

## Global Constraints

- Backend runner from `backend/`: `.venv/Scripts/uv.exe run ...` (fallback `C:\Users\Nikos A. Grammatikos\.local\bin\uv.exe run ...`; ignore VIRTUAL_ENV stderr warning)
- Tests: `uv.exe run manage.py test hub.tests.test_competency_decay -v 2`; full `uv.exe run manage.py test hub analytics -v 1` stays green (377+). Existing tests in `hub/tests/test_competency_scoring.py` that assert the old inline behavior may legitimately need updates — every change must be listed in the report with its justification.
- Lint: `uv.exe run ruff check . --fix`
- Score clamps to 0..6; bands: 0-2 / 3-4 / 5-6; band change re-assigns `UserLearningPath` BOTH directions
- The old `competency_score < 6` gate is REMOVED (negative deltas must apply at 6)
- `apply_competency_delta` is a no-op (no save, no recompute, no re-assign) when the clamped score equals the old score
- Idle decay: `0 < progress_pct < 100`, idle > `idle_decay_days`, `decay_applied_at IS NULL`, once per enrollment, master-gated by `decay_enabled`
- Commit after each task; messages end with the project's Co-Authored-By trailer

---

### Task 1: Config fields + Enrollment stamp + admin

**Files:**
- Modify: `backend/hub/models/activity.py` (LearnerActivityConfig fields)
- Modify: `backend/hub/models/enrollment.py` (decay_applied_at)
- Create: migrations via `makemigrations hub -n competency_decay` (single migration covering both models is fine)
- Modify: `backend/hub/admin.py` (LearnerActivityConfigAdmin fieldsets)
- Test: `backend/hub/tests/test_competency_decay.py` (new)

**Interfaces:**
- Produces: `LearnerActivityConfig.decay_enabled` (bool, True), `slow_ratio_threshold` (float, 3.0), `slow_penalty` (int, 1), `idle_decay_days` (int, 30), `idle_decay_points` (int, 1); `Enrollment.decay_applied_at` (DateTimeField null/blank). Tasks 2-3 consume them.

- [ ] **Step 1: Write the failing test — new file `backend/hub/tests/test_competency_decay.py`**

```python
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase  # noqa: F401  (used by later task's classes)

from hub.models import (
    Course,
    Enrollment,
    LearnerActivityConfig,
    LearningPillar,
    UserProfile,
)


class DecayConfigTests(TestCase):
    def test_new_config_defaults(self):
        config = LearnerActivityConfig.get()
        self.assertTrue(config.decay_enabled)
        self.assertEqual(config.slow_ratio_threshold, 3.0)
        self.assertEqual(config.slow_penalty, 1)
        self.assertEqual(config.idle_decay_days, 30)
        self.assertEqual(config.idle_decay_points, 1)

    def test_enrollment_decay_stamp_default_null(self):
        user = User.objects.create_user(username='stamp_u', password='pass12345')
        UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P', slug='pdec', order=1)
        course = Course.objects.create(
            title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        e = Enrollment.objects.create(user=user, course=course)
        self.assertIsNone(e.decay_applied_at)
        e.decay_applied_at = timezone.now() - timedelta(days=1)
        e.save(update_fields=['decay_applied_at'])
```

Run: `uv.exe run manage.py test hub.tests.test_competency_decay -v 2` → FAIL (missing attributes).

- [ ] **Step 2: Add the fields**

`backend/hub/models/activity.py`, inside `LearnerActivityConfig` after the quiz fields:

```python
    # Decay (see docs/superpowers/specs/2026-07-19-competency-decay-design.md)
    decay_enabled        = models.BooleanField(default=True)
    slow_ratio_threshold = models.FloatField(default=3.0)
    slow_penalty         = models.PositiveSmallIntegerField(default=1)
    idle_decay_days      = models.PositiveSmallIntegerField(default=30)
    idle_decay_points    = models.PositiveSmallIntegerField(default=1)
```

`backend/hub/models/enrollment.py`, in `Enrollment` after `completed_at`:

```python
    decay_applied_at = models.DateTimeField(null=True, blank=True)
```

Run: `uv.exe run manage.py makemigrations hub -n competency_decay && uv.exe run manage.py migrate`

- [ ] **Step 3: Admin fieldsets**

In `backend/hub/admin.py`, `LearnerActivityConfigAdmin.fieldsets` gains:

```python
        ('Decay', {'fields': ['decay_enabled', 'slow_ratio_threshold', 'slow_penalty',
                              'idle_decay_days', 'idle_decay_points']}),
```

- [ ] **Step 4: GREEN, full suite, ruff, commit**

```bash
git add backend/hub
git commit -m "feat: decay config knobs and enrollment decay stamp"
```

---

### Task 2: `hub/competency.py` helper + completion-hook rework

**Files:**
- Create: `backend/hub/competency.py`
- Modify: `backend/hub/views/learner.py` (LessonCompleteView inline block)
- Test: `backend/hub/tests/test_competency_decay.py` (append)

**Interfaces:**
- Consumes: Task 1 config fields; `LearningPath`/`UserLearningPath`; `compute_user_recommendations`
- Produces: `apply_competency_delta(user, delta) -> int` and `course_completion_delta(user, course) -> int`. Task 3 consumes `apply_competency_delta`.

- [ ] **Step 1: Write failing tests (append)**

```python
def _make_course_with_lesson(pillar_slug='pdec2', duration_minutes=10):
    from hub.models import Lesson, Module
    pillar = LearningPillar.objects.create(name='P2', slug=pillar_slug, order=2)
    course = Course.objects.create(
        title=f'C-{pillar_slug}', pillar=pillar, level='beginner',
        duration_hours=1, is_published=True,
    )
    module = Module.objects.create(course=course, title='M', order=1)
    lesson = Lesson.objects.create(
        module=module, title='L', lesson_type='text', order=1,
        is_required=True, duration_minutes=duration_minutes,
    )
    return course, lesson


def _make_paths():
    from hub.models import LearningPath
    for slug, lo, hi in [
        ('beginner-foundations', 0, 2),
        ('intermediate-growth', 3, 4),
        ('advanced-integration', 5, 6),
    ]:
        LearningPath.objects.update_or_create(
            slug=slug,
            defaults={'name': slug, 'competency_min': lo, 'competency_max': hi},
        )


class ApplyCompetencyDeltaTests(TestCase):
    def setUp(self):
        _make_paths()
        self.user = User.objects.create_user(username='delta_u', password='pass12345')
        self.profile = UserProfile.objects.create(
            user=self.user, user_type=UserProfile.UserType.TEACHER, competency_score=3,
        )

    def test_clamps_floor_and_cap(self):
        from hub.competency import apply_competency_delta
        self.assertEqual(apply_competency_delta(self.user, -10), 0)
        self.assertEqual(apply_competency_delta(self.user, +10), 6)

    def test_band_drop_reassigns_path(self):
        from hub.competency import apply_competency_delta
        from hub.models import UserLearningPath
        apply_competency_delta(self.user, -1)  # 3 -> 2: intermediate -> beginner
        self.assertEqual(
            UserLearningPath.objects.get(user=self.user).path.slug,
            'beginner-foundations',
        )

    def test_band_climb_reassigns_path(self):
        from hub.competency import apply_competency_delta
        from hub.models import UserLearningPath
        apply_competency_delta(self.user, +2)  # 3 -> 5: intermediate -> advanced
        self.assertEqual(
            UserLearningPath.objects.get(user=self.user).path.slug,
            'advanced-integration',
        )

    def test_zero_delta_is_noop(self):
        from hub.competency import apply_competency_delta
        from hub.models import UserLearningPath
        apply_competency_delta(self.user, 0)
        self.assertFalse(UserLearningPath.objects.filter(user=self.user).exists())

    def test_within_band_change_keeps_path(self):
        from hub.competency import apply_competency_delta
        from hub.models import UserLearningPath
        apply_competency_delta(self.user, +1)  # 3 -> 4, still intermediate
        self.assertFalse(UserLearningPath.objects.filter(user=self.user).exists())


class CourseCompletionDeltaTests(TestCase):
    def setUp(self):
        _make_paths()
        self.user = User.objects.create_user(username='ccd_u', password='pass12345')
        UserProfile.objects.create(
            user=self.user, user_type=UserProfile.UserType.TEACHER, competency_score=3,
        )

    def _progress(self, lesson, seconds=None, quiz_score=None):
        from hub.models import LessonProgress
        return LessonProgress.objects.create(
            user=self.user, lesson=lesson,
            time_spent_seconds=seconds, quiz_score=quiz_score,
            completed_at=timezone.now(),
        )

    def test_default_delta_is_one(self):
        from hub.competency import course_completion_delta
        course, lesson = _make_course_with_lesson('ccd1')
        self._progress(lesson, seconds=600)  # 10 min for a 10-min lesson
        self.assertEqual(course_completion_delta(self.user, course), 1)

    def test_slow_completion_reduces_delta(self):
        from hub.competency import course_completion_delta
        course, lesson = _make_course_with_lesson('ccd2', duration_minutes=10)
        self._progress(lesson, seconds=4 * 600)  # 40 min: ratio 4 > 3.0
        self.assertEqual(course_completion_delta(self.user, course), 0)

    def test_negative_fail_weight_gives_negative_delta(self):
        from hub.models import Lesson, Module
        from hub.competency import course_completion_delta
        config = LearnerActivityConfig.get()
        config.quiz_affects_competency = True
        config.quiz_weight_fail = -1.0
        config.save()
        course, lesson = _make_course_with_lesson('ccd3')
        quiz = Lesson.objects.create(
            module=Module.objects.get(course=course), title='Q', lesson_type='quiz',
            order=2, is_required=True,
        )
        self._progress(lesson, seconds=600)
        self._progress(quiz, quiz_score=0.2)  # below 0.7 threshold
        self.assertEqual(course_completion_delta(self.user, course), -1)

    def test_decay_disabled_skips_slow_penalty(self):
        from hub.competency import course_completion_delta
        config = LearnerActivityConfig.get()
        config.decay_enabled = False
        config.save()
        course, lesson = _make_course_with_lesson('ccd4', duration_minutes=10)
        self._progress(lesson, seconds=4 * 600)
        self.assertEqual(course_completion_delta(self.user, course), 1)
```

Run → FAIL (ModuleNotFoundError: hub.competency).

- [ ] **Step 2: Create `backend/hub/competency.py`**

```python
"""Competency score changes: clamping, band-based pathway re-assignment, decay math.

Spec: docs/superpowers/specs/2026-07-19-competency-decay-design.md
"""
from hub.models import LearnerActivityConfig, LearningPath, LessonProgress, UserLearningPath

SCORE_MIN = 0
SCORE_MAX = 6


def _band(score: int) -> int:
    if score <= 2:
        return 0
    if score <= 4:
        return 1
    return 2


def apply_competency_delta(user, delta: int) -> int:
    """Apply delta to the user's competency score.

    Clamps to 0..6; re-assigns the learning path when the band changes in
    either direction; schedules a recommendations recompute when the score
    actually changed. Returns the (possibly unchanged) score.
    """
    profile = user.profile
    old = profile.competency_score
    new = max(SCORE_MIN, min(SCORE_MAX, old + delta))
    if new == old:
        return old

    profile.competency_score = new
    profile.save(update_fields=['competency_score'])

    if _band(new) != _band(old):
        path = LearningPath.objects.filter(
            competency_min__lte=new, competency_max__gte=new,
        ).first()
        if path:
            UserLearningPath.objects.update_or_create(user=user, defaults={'path': path})

    from hub.tasks import compute_user_recommendations
    compute_user_recommendations.delay(user.id)
    return new


def course_completion_delta(user, course) -> int:
    """Score increment for a just-completed course (may be negative)."""
    config = LearnerActivityConfig.get()

    if config.quiz_affects_competency:
        quiz_scores = list(
            LessonProgress.objects.filter(
                user=user,
                lesson__module__course=course,
                lesson__lesson_type='quiz',
                quiz_score__isnull=False,
            ).values_list('quiz_score', flat=True)
        )
        if quiz_scores:
            avg = sum(quiz_scores) / len(quiz_scores)
            weight = (
                config.quiz_weight_pass
                if avg >= config.quiz_pass_threshold
                else config.quiz_weight_fail
            )
        else:
            weight = config.quiz_weight_pass
        delta = round(weight)
    else:
        delta = 1

    if config.decay_enabled:
        timed = list(
            LessonProgress.objects.filter(
                user=user,
                lesson__module__course=course,
                time_spent_seconds__isnull=False,
                lesson__duration_minutes__gt=0,
            ).select_related('lesson')
        )
        if timed:
            ratios = [
                (lp.time_spent_seconds / 60) / lp.lesson.duration_minutes
                for lp in timed
            ]
            if sum(ratios) / len(ratios) > config.slow_ratio_threshold:
                delta -= config.slow_penalty

    return delta
```

- [ ] **Step 3: Rework the completion hook**

In `backend/hub/views/learner.py`, replace the entire block starting `if just_completed and hasattr(request.user, 'profile'):` (through the `compute_user_recommendations.delay(...)` line) with:

```python
        if just_completed and hasattr(request.user, 'profile'):
            from hub.competency import apply_competency_delta, course_completion_delta
            apply_competency_delta(
                request.user, course_completion_delta(request.user, course),
            )
```

Remove the now-unused `LearnerActivityConfig` local import from that block if nothing else in the file uses it.

- [ ] **Step 4: GREEN, full suite (update legacy test_competency_scoring.py expectations ONLY where they encode the removed `< 6` gate or the always-recompute behavior — document each change), ruff, commit**

```bash
git add backend/hub
git commit -m "feat: competency delta helper with band-based pathway re-assignment"
```

---

### Task 3: Nightly idle-decay task

**Files:**
- Modify: `backend/hub/tasks.py` (new task)
- Modify: `backend/aidea/settings.py` (CELERY_BEAT_SCHEDULE entry)
- Test: `backend/hub/tests/test_competency_decay.py` (append)

**Interfaces:**
- Consumes: `apply_competency_delta`, Task 1 fields

- [ ] **Step 1: Write failing tests (append)**

```python
class IdleDecayTaskTests(TestCase):
    def setUp(self):
        _make_paths()
        self.user = User.objects.create_user(username='idle_u', password='pass12345')
        UserProfile.objects.create(
            user=self.user, user_type=UserProfile.UserType.TEACHER, competency_score=3,
        )
        self.course, _ = _make_course_with_lesson('idle1')
        self.enrollment = Enrollment.objects.create(
            user=self.user, course=self.course, progress_pct=40,
        )
        # last_accessed_at is auto_now — backdate via queryset update
        Enrollment.objects.filter(pk=self.enrollment.pk).update(
            last_accessed_at=timezone.now() - timedelta(days=45),
        )

    def _refresh(self):
        self.user.profile.refresh_from_db()
        self.enrollment.refresh_from_db()

    def test_idle_enrollment_decays_once(self):
        from hub.tasks import apply_competency_decay
        apply_competency_decay()
        self._refresh()
        self.assertEqual(self.user.profile.competency_score, 2)
        self.assertIsNotNone(self.enrollment.decay_applied_at)

        apply_competency_decay()  # second run: stamped, no further decay
        self._refresh()
        self.assertEqual(self.user.profile.competency_score, 2)

    def test_disabled_toggle_skips(self):
        from hub.tasks import apply_competency_decay
        config = LearnerActivityConfig.get()
        config.decay_enabled = False
        config.save()
        apply_competency_decay()
        self._refresh()
        self.assertEqual(self.user.profile.competency_score, 3)
        self.assertIsNone(self.enrollment.decay_applied_at)

    def test_fresh_and_complete_enrollments_exempt(self):
        from hub.tasks import apply_competency_decay
        Enrollment.objects.filter(pk=self.enrollment.pk).update(
            last_accessed_at=timezone.now(),  # fresh again
        )
        apply_competency_decay()
        self._refresh()
        self.assertEqual(self.user.profile.competency_score, 3)

    def test_zero_progress_exempt(self):
        from hub.tasks import apply_competency_decay
        Enrollment.objects.filter(pk=self.enrollment.pk).update(progress_pct=0)
        apply_competency_decay()
        self._refresh()
        self.assertEqual(self.user.profile.competency_score, 3)
```

Run → FAIL (ImportError: apply_competency_decay).

- [ ] **Step 2: Implement the task (append to `backend/hub/tasks.py`)**

```python
@shared_task
def apply_competency_decay() -> None:
    """Nightly: dock competency for enrollments abandoned mid-course."""
    from datetime import timedelta

    from django.utils import timezone

    from hub.competency import apply_competency_delta
    from hub.models import Enrollment, LearnerActivityConfig

    config = LearnerActivityConfig.get()
    if not config.decay_enabled:
        return

    cutoff = timezone.now() - timedelta(days=config.idle_decay_days)
    stale = (
        Enrollment.objects
        .filter(
            progress_pct__gt=0,
            progress_pct__lt=100,
            last_accessed_at__lt=cutoff,
            decay_applied_at__isnull=True,
        )
        .select_related('user__profile')
    )
    now = timezone.now()
    for enrollment in stale:
        apply_competency_delta(enrollment.user, -config.idle_decay_points)
        enrollment.decay_applied_at = now
        enrollment.save(update_fields=['decay_applied_at'])
```

(Match the file's existing import style — other tasks in this file import inside the function body; follow that convention.)

- [ ] **Step 3: Beat schedule**

In `backend/aidea/settings.py`, add to `CELERY_BEAT_SCHEDULE`:

```python
    'apply-competency-decay-nightly': {
        'task': 'hub.tasks.apply_competency_decay',
        'schedule': crontab(hour=4, minute=0),
    },
```

- [ ] **Step 4: GREEN, full suite, ruff, commit**

```bash
git add backend/hub backend/aidea/settings.py
git commit -m "feat: nightly competency decay for abandoned enrollments"
```

---

### Final verification

- [ ] `cd backend && uv.exe run coverage run manage.py test hub analytics -v 1` — green, ≥70%
- [ ] `uv.exe run ruff check .` — clean
- [ ] `cd frontend && npm run lint && npm run build` — clean (no frontend changes expected; sanity only)
- [ ] Dispatch final whole-branch review

## Deployment notes

Migration required: on the VM, `git pull`, `docker compose up -d`, then
`docker compose exec backend uv run python manage.py migrate`.
The nightly decay runs via the existing celery-beat container. To make
failing quizzes actually LOWER scores, set `quiz_affects_competency=True`
and a negative `quiz_weight_fail` in Django admin → Learner activity configs.
