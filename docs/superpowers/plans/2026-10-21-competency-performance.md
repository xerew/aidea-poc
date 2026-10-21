# Performance-Based AI Competency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On course completion, the teacher's AI competency score (0–6) moves by first-attempt performance on every scored item (quizzes, scored H5P, assignments by their first review), relative to course difficulty. The slow-pace penalty and idle decay get separate switches, and every change is recorded with its reason.

**Architecture:**
- `hub/competency.py` gains:
  - `course_performance` (per-module averages of first-attempt scores);
  - `performance_delta` (the difficulty table);
  - `course_completion_change` (the delta plus a reason dict).
- `apply_competency_delta` writes a `CompetencyChange` row whenever the score moves.
- Assignment submissions keep their `first_review_status`.
- `LearnerActivityConfig`'s single `decay_enabled` switch becomes `slow_penalty_enabled` + `idle_decay_enabled`, and the old quiz toggle and weights are removed.

**Tech Stack:** Django 5 + DRF, Celery (nightly idle task).

**Spec:** `docs/superpowers/specs/2026-10-21-competency-performance-design.md`

## Global Constraints

- **Score:** stays within 0–6. Teacher level: 0–2 → 0 (beginner), 3–4 → 1 (intermediate), 5–6 → 2 (advanced). Course level: beginner 0, intermediate 1, advanced 2. `gap = course level − teacher level`.
- **Table:**

  | gap | passed | not passed |
  |---|---|---|
  | ≥ +2 | +2 | 0 |
  | +1 | +1 | 0 |
  | 0 | +1 | 0 |
  | ≤ −1 | 0 | −1 |

- **Passed** = performance ≥ `LearnerActivityConfig.quiz_pass_threshold` (default 0.70).
- **Performance:**
  - the mean over modules of the mean first-attempt score (0–1) of completed scored items;
  - a quiz counts by `quiz_score`, an H5P by `quiz_score` (set only when it reports a score), an assignment by `first_review_status` (`approved` = 1.0, `changes_requested` = 0.0);
  - items without a score are skipped; modules without counting items are skipped;
  - **no counting items in the course → change +1** (rule `completion`).
- **Slow penalty:** unchanged maths (mean time / planned ratio > `slow_ratio_threshold` → subtract `slow_penalty`), only when `slow_penalty_enabled`. Applied after the table.
- **Idle decay:** the nightly task runs only when `idle_decay_enabled`.
- **Defaults:** `slow_penalty_enabled` = True and `idle_decay_enabled` = False. The migration sets slow = True and idle = the old `decay_enabled`.
- **`first_review_status`:**
  - set once, by the first `approve_submission` / `request_changes` (human or AI auto-approve);
  - never overwritten (not by a later review or `reopen_submission`);
  - the migration backfills `approved` / `changes_requested` submissions from their status.
- **`CompetencyChange`:**
  - one row per actual score change, with `old_score`, `new_score`, `delta` = new − old, `course` and `reason`;
  - `reason.rule` ∈ `performance` | `completion` | `idle`;
  - for idle decay, `course` = the abandoned course;
  - clamped no-op changes record nothing.
- **Existing scores** are not recalculated.
- **Runner and git:**
  - from `backend/`, set `UV="/c/Users/Nikos A. Grammatikos/.local/bin/uv.exe"`, then `"$UV" run manage.py test …` and `"$UV" run ruff check hub analytics`;
  - keep line endings; work on `master`, commit and push per task, with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A reviewer decides while the AI's auto-approve runs, or the learner resubmits:** the first decision must be the first one ever made, never a later one. Pinned by Task 1 `test_first_review_is_never_overwritten`.
2. **An H5P activity that reports no score** (a self-completed type) or a quiz completed without answers must not count as 0%; it's skipped. Pinned by Task 2 `test_unscored_and_unfinished_items_are_ignored`.
3. **A teacher at the score boundaries** (0 with −1, 6 with +2): the score stays within 0–6, and a clamped no-op leaves no change record. Pinned by Task 2 `test_clamped_change_records_nothing` and the existing clamp test.
4. **Retaking a quiz with a better result** must not raise performance (first attempt only). Pinned by Task 2 `test_first_attempt_counts`.
5. **The production config row** (where the admin unticked `decay_enabled`) must end up with slow on and idle off, and courses with only text, video or PDF must still give +1. Pinned by the Task 1 migration check and Task 2 `test_no_scored_items_gives_one`.

---

## File Structure

- `backend/hub/models/competency.py` (new): `CompetencyChange`.
- `backend/hub/models/activity.py`: `slow_penalty_enabled` and `idle_decay_enabled` (Task 1); remove `quiz_affects_competency`, `quiz_weight_pass`, `quiz_weight_fail` and `decay_enabled` (Task 3).
- `backend/hub/models/assignment.py`: `first_review_status`.
- `backend/hub/models/__init__.py`, `backend/hub/admin.py`.
- `backend/hub/migrations/0068_competency_performance.py` (generated), `0069_competency_settings_data.py` (hand-written), `0070_remove_old_competency_settings.py` (generated).
- `backend/hub/assignment_review.py`: record the first decision.
- `backend/hub/competency.py`: the new rule and the change record.
- `backend/hub/completion.py`: call `course_completion_change`.
- `backend/hub/tasks.py`: the idle task uses `idle_decay_enabled` and records the course.
- Tests:
  - new: `hub/tests/test_competency_models.py`, `hub/tests/test_competency_performance.py`;
  - updated: `hub/tests/test_competency_decay.py`, `hub/tests/test_learner_activity.py`.

---

### Task 1: New fields, change record, first review decision, data migration

**Files:**
- Create: `backend/hub/models/competency.py`, `backend/hub/migrations/0069_competency_settings_data.py`, `backend/hub/tests/test_competency_models.py`
- Modify:
  - `backend/hub/models/activity.py`, `backend/hub/models/assignment.py`, `backend/hub/models/__init__.py`
  - `backend/hub/assignment_review.py`, `backend/hub/admin.py`
  - `backend/hub/migrations/0068_competency_performance.py` (generated)

**Interfaces — Produces:**
- `LearnerActivityConfig.slow_penalty_enabled` (default True) and `.idle_decay_enabled` (default False).
- `AssignmentSubmission.first_review_status` (str, `''` / `'approved'` / `'changes_requested'`).
- `CompetencyChange(user, course|None, old_score, new_score, delta, reason: dict, created_at)`.
- `approve_submission` and `request_changes` set `first_review_status` only when it is blank.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_competency_models.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase

from hub.assignment_review import approve_submission, reopen_submission, request_changes
from hub.models import (
    AssignmentSubmission,
    CompetencyChange,
    Enrollment,
    LearnerActivityConfig,
    UserProfile,
)

from .test_ai_review_models import make_assignment


class CompetencyModelTests(TestCase):
    def setUp(self):
        self.course, _, self.activity, self.resource = make_assignment()
        self.learner = User.objects.create_user('cm_l', password='x', email='cm@example.org')
        UserProfile.objects.create(user=self.learner)
        Enrollment.objects.create(user=self.learner, course=self.course)
        self.reviewer = User.objects.create_user('cm_r', password='x')

    def submit(self):
        sub, _ = AssignmentSubmission.objects.update_or_create(
            user=self.learner, lesson=self.activity,
            defaults={'resource': self.resource, 'text': 't', 'status': 'pending'})
        return sub

    def test_config_switch_defaults(self):
        config = LearnerActivityConfig.get()
        self.assertEqual((config.slow_penalty_enabled, config.idle_decay_enabled), (True, False))

    def test_first_review_approved_directly(self):
        sub = self.submit()
        approve_submission(sub, self.reviewer)
        sub.refresh_from_db()
        self.assertEqual((sub.status, sub.first_review_status), ('approved', 'approved'))

    def test_first_review_is_never_overwritten(self):
        sub = self.submit()
        request_changes(sub, self.reviewer, 'Add detail')
        sub = self.submit()                                  # learner resubmits
        approve_submission(sub, self.reviewer)
        reopen_submission(sub)
        sub.refresh_from_db()
        self.assertEqual((sub.status, sub.first_review_status), ('pending', 'changes_requested'))

    def test_change_record(self):
        change = CompetencyChange.objects.create(user=self.learner, course=self.course, old_score=3, new_score=4,
                                                 delta=1, reason={'rule': 'performance'})
        self.assertEqual(list(self.learner.competency_changes.all()), [change])
        self.assertEqual(change.reason['rule'], 'performance')
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_competency_models -v 2`
  - Expected: ImportError, `cannot import name 'CompetencyChange'`.

- [ ] **Step 3: Implement.** `backend/hub/models/competency.py`:

```python
"""Every change to a teacher's AI competency score, with its reason — see
docs/superpowers/specs/2026-10-21-competency-performance-design.md."""
from django.contrib.auth.models import User
from django.db import models


class CompetencyChange(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='competency_changes')
    course     = models.ForeignKey('hub.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    old_score  = models.PositiveSmallIntegerField()
    new_score  = models.PositiveSmallIntegerField()
    delta      = models.SmallIntegerField()                 # new − old (after clamping to 0..6)
    # {rule: performance|completion|idle, performance, passed, course_level,
    #  teacher_level, gap, base_delta, slow_penalty} — see hub/competency.py
    reason     = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.user} {self.old_score}→{self.new_score}'
```

`backend/hub/models/activity.py`, in `LearnerActivityConfig`, after `idle_decay_points`:

```python
    # Separate switches (spec 2026-10-21): the slow-pace penalty on course
    # completion, and the nightly idle decay. `decay_enabled` is removed in a later migration.
    slow_penalty_enabled = models.BooleanField(default=True)
    idle_decay_enabled   = models.BooleanField(default=False)
```

`backend/hub/models/assignment.py`, in `AssignmentSubmission`, after `status`:

```python
    # The first review decision, never overwritten — what counts for competency.
    first_review_status = models.CharField(max_length=20, blank=True)
```

`backend/hub/models/__init__.py`: add `from .competency import CompetencyChange` (alphabetical position) and `'CompetencyChange'` to `__all__`.

`backend/hub/assignment_review.py`:
- in `approve_submission`, right after `submission.status = AssignmentSubmission.Status.APPROVED`, add:

```python
        if not submission.first_review_status:
            submission.first_review_status = AssignmentSubmission.Status.APPROVED
```

- in `request_changes`, right after `submission.status = AssignmentSubmission.Status.CHANGES_REQUESTED`, add:

```python
    if not submission.first_review_status:
        submission.first_review_status = AssignmentSubmission.Status.CHANGES_REQUESTED
```

`backend/hub/admin.py`: import `CompetencyChange` and register it read-only, next to the AI review admins:

```python
@admin.register(CompetencyChange)
class CompetencyChangeAdmin(_ReadOnlyAdmin):
    list_display = ['user', 'course', 'old_score', 'new_score', 'delta', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'course', 'old_score', 'new_score', 'delta', 'reason', 'created_at']
```

Generate the migration with `"$UV" run manage.py makemigrations hub --name competency_performance`. Expected: `0068_competency_performance.py` with the two config fields, `first_review_status` and `CompetencyChange`.

Create `backend/hub/migrations/0069_competency_settings_data.py`:

```python
from django.db import migrations


def forwards(apps, schema_editor):
    """Slow penalty stays on; idle decay follows the old single switch (which
    the admin turned off). Reviewed submissions take their current status as
    the first decision — their history was not kept."""
    Config = apps.get_model('hub', 'LearnerActivityConfig')
    for config in Config.objects.all():
        config.slow_penalty_enabled = True
        config.idle_decay_enabled = config.decay_enabled
        config.save(update_fields=['slow_penalty_enabled', 'idle_decay_enabled'])
    Submission = apps.get_model('hub', 'AssignmentSubmission')
    for status in ('approved', 'changes_requested'):
        Submission.objects.filter(status=status, first_review_status='').update(first_review_status=status)


def backwards(apps, schema_editor):
    Config = apps.get_model('hub', 'LearnerActivityConfig')
    for config in Config.objects.all():
        config.decay_enabled = config.idle_decay_enabled
        config.save(update_fields=['decay_enabled'])


class Migration(migrations.Migration):
    dependencies = [('hub', '0068_competency_performance')]
    operations = [migrations.RunPython(forwards, backwards)]
```

**Migration check** (Review Focus 5), on the dev database:
1. Run `"$UV" run manage.py shell -c "from hub.models import LearnerActivityConfig as C; c=C.get(); c.decay_enabled=False; c.save(); print('before', c.decay_enabled)"` **before** migrating.
2. Run `"$UV" run manage.py migrate`.
3. Run `"$UV" run manage.py shell -c "from hub.models import LearnerActivityConfig as C; c=C.get(); print(c.slow_penalty_enabled, c.idle_decay_enabled)"`.
4. Expected: `True False`.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_competency_models hub.tests.test_assignment_review hub.tests.test_ai_review_pipeline -v 2`
  - Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/models hub/assignment_review.py hub/admin.py hub/migrations/0068_competency_performance.py hub/migrations/0069_competency_settings_data.py hub/tests/test_competency_models.py
git commit -m "feat: competency change record, first review decision, separate decay switches"
git push
```

---

### Task 2: The new rule

**Files:**
- Modify: `backend/hub/competency.py`, `backend/hub/completion.py`, `backend/hub/tasks.py`
- Create: `backend/hub/tests/test_competency_performance.py`
- Modify tests: `backend/hub/tests/test_competency_decay.py`, `backend/hub/tests/test_learner_activity.py`

**Interfaces:**
- **Consumes:** Task 1's fields and `CompetencyChange`.
- **Produces:**
  - `course_performance(user, course) -> float | None`;
  - `performance_delta(passed: bool, gap: int) -> int`;
  - `course_completion_change(user, course) -> (int, dict)`;
  - `course_completion_delta(user, course) -> int`, kept as a thin wrapper;
  - `apply_competency_delta(user, delta, recompute=True, course=None, reason=None) -> int`, which records a `CompetencyChange`.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_competency_performance.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from hub.competency import (
    apply_competency_delta,
    course_completion_change,
    course_performance,
    performance_delta,
)
from hub.models import (
    Activity,
    AssignmentSubmission,
    CompetencyChange,
    Course,
    Enrollment,
    LearnerActivityConfig,
    LearningPillar,
    Module,
    Resource,
    ResourceProgress,
    UserProfile,
)

QUIZ = [{'question': 'Q', 'options': [{'text': 'A', 'is_correct': True}, {'text': 'B', 'is_correct': False}]}]


def make_course(level='intermediate', modules=2):
    pillar = LearningPillar.objects.get_or_create(slug='p-cp', defaults={'name': 'P', 'order': 1})[0]
    course = Course.objects.create(title=f'{level} course', pillar=pillar, level=level, duration_hours=1,
                                   is_published=True)
    return course, [Module.objects.create(course=course, title=f'M{i}', order=i) for i in range(1, modules + 1)]


def add(module, kind, order=1, minutes=0):
    activity = Activity.objects.create(module=module, title=f'{kind} {order}', order=order, duration_minutes=minutes)
    return Resource.objects.create(activity=activity, type=kind, order=1, quiz_data=QUIZ if kind == 'quiz' else [])


class Base(TestCase):
    score = 3   # intermediate

    def setUp(self):
        self.user = User.objects.create_user('cp_t', password='x')
        UserProfile.objects.create(user=self.user, competency_score=self.score)

    def done(self, resource, score=None, seconds=None):
        return ResourceProgress.objects.create(user=self.user, resource=resource, completed_at=timezone.now(),
                                               quiz_score=score, time_spent_seconds=seconds)

    def assignment(self, resource, first):
        AssignmentSubmission.objects.create(user=self.user, lesson=resource.activity, resource=resource, text='t',
                                            status='approved', first_review_status=first)
        self.done(resource)


class PerformanceDeltaTableTests(TestCase):
    def test_every_cell(self):
        cells = {(2, True): 2, (2, False): 0, (1, True): 1, (1, False): 0, (0, True): 1, (0, False): 0,
                 (-1, True): 0, (-1, False): -1, (-2, True): 0, (-2, False): -1}
        for (gap, passed), expected in cells.items():
            self.assertEqual(performance_delta(passed, gap), expected, (gap, passed))


class CoursePerformanceTests(Base):
    def test_modules_count_equally(self):
        course, (m1, m2) = make_course()
        for i in range(3):
            self.done(add(m1, 'quiz', order=i + 1), score=1.0)
        self.assignment(add(m2, 'assignment'), 'changes_requested')
        self.assertAlmostEqual(course_performance(self.user, course), 0.5)

    def test_assignment_counts_by_first_review(self):
        course, (m1, _) = make_course()
        self.assignment(add(m1, 'assignment'), 'approved')
        self.assertEqual(course_performance(self.user, course), 1.0)

    def test_h5p_score_counts(self):
        course, (m1, _) = make_course()
        self.done(add(m1, 'h5p'), score=0.6)
        self.assertAlmostEqual(course_performance(self.user, course), 0.6)

    def test_unscored_and_unfinished_items_are_ignored(self):
        course, (m1, m2) = make_course()
        self.done(add(m1, 'quiz'), score=0.8)
        self.done(add(m1, 'h5p', order=2))          # reported no score
        self.done(add(m1, 'quiz', order=3))         # completed without answers
        add(m2, 'quiz')                             # never done
        self.done(add(m2, 'text', order=2))
        self.assertAlmostEqual(course_performance(self.user, course), 0.8)

    def test_no_scored_items(self):
        course, (m1, _) = make_course()
        self.done(add(m1, 'text'))
        self.assertIsNone(course_performance(self.user, course))

    def test_first_attempt_counts(self):
        from hub.completion import _mark_resource_complete
        course, (m1, _) = make_course()
        quiz = add(m1, 'quiz')
        _mark_resource_complete(self.user, quiz, quiz_answers_raw=[1])   # wrong first
        _mark_resource_complete(self.user, quiz, quiz_answers_raw=[0])   # right on a retake
        self.assertEqual(course_performance(self.user, course), 0.0)


class CourseCompletionChangeTests(Base):
    def change(self, level, score=None):
        course, (m1, _) = make_course(level)
        self.done(add(m1, 'quiz'), score=score) if score is not None else self.done(add(m1, 'text'))
        return course_completion_change(self.user, course)

    def test_harder_course_passed(self):
        delta, reason = self.change('advanced', 0.9)
        self.assertEqual((delta, reason['rule'], reason['gap'], reason['passed']), (1, 'performance', 1, True))

    def test_harder_course_failed_is_zero(self):
        self.assertEqual(self.change('advanced', 0.3)[0], 0)

    def test_same_level(self):
        self.assertEqual(self.change('intermediate', 0.7)[0], 1)
        self.assertEqual(self.change('intermediate', 0.5)[0], 0)

    def test_easier_course(self):
        self.assertEqual(self.change('beginner', 0.9)[0], 0)
        delta, reason = self.change('beginner', 0.4)
        self.assertEqual((delta, reason['gap'], reason['performance']), (-1, -1, 0.4))

    def test_no_scored_items_gives_one(self):
        delta, reason = self.change('beginner')
        self.assertEqual((delta, reason['rule'], reason['performance']), (1, 'completion', None))

    def test_threshold_comes_from_settings(self):
        config = LearnerActivityConfig.get()
        config.quiz_pass_threshold = 0.9
        config.save()
        self.assertEqual(self.change('intermediate', 0.8)[0], 0)

    def test_slow_penalty_has_its_own_switch(self):
        course, (m1, _) = make_course('beginner')
        self.done(add(m1, 'text', minutes=10), seconds=40 * 60)       # 4× the planned time
        delta, reason = course_completion_change(self.user, course)
        self.assertEqual((delta, reason['slow_penalty']), (0, 1))
        config = LearnerActivityConfig.get()
        config.slow_penalty_enabled = False
        config.save()
        self.assertEqual(course_completion_change(self.user, course)[0], 1)


class TwoLevelsHarderTests(Base):
    score = 0   # beginner

    def test_two_levels_harder_passed(self):
        course, (m1, _) = make_course('advanced')
        self.done(add(m1, 'quiz'), score=1.0)
        self.assertEqual(course_completion_change(self.user, course)[0], 2)


class ChangeRecordTests(Base):
    def test_change_is_recorded_with_reason(self):
        course, _ = make_course()
        apply_competency_delta(self.user, 1, recompute=False, course=course, reason={'rule': 'performance'})
        change = CompetencyChange.objects.get()
        self.assertEqual((change.old_score, change.new_score, change.delta, change.course, change.reason['rule']),
                         (3, 4, 1, course, 'performance'))

    def test_clamped_change_records_nothing(self):
        self.user.profile.competency_score = 6
        self.user.profile.save()
        apply_competency_delta(self.user, 2, recompute=False)
        self.assertFalse(CompetencyChange.objects.exists())

    def test_completing_a_course_records_the_rule(self):
        from hub.completion import record_resource_completion
        course, (m1, _) = make_course('advanced', modules=1)
        quiz = add(m1, 'quiz')
        enrollment = Enrollment.objects.create(user=self.user, course=course)
        record_resource_completion(self.user, enrollment, quiz, quiz_answers_raw=[0])
        self.user.profile.refresh_from_db()
        change = CompetencyChange.objects.get()
        self.assertEqual((self.user.profile.competency_score, change.reason['rule'], change.course),
                         (4, 'performance', course))
```

Update the existing tests whose switches change:
- `hub/tests/test_competency_decay.py`:
  - `test_negative_fail_weight_gives_negative_delta`: **delete** it. The quiz toggle and weights are gone, and the new table tests cover failing.
  - `test_decay_disabled_skips_slow_penalty`: set `config.slow_penalty_enabled = False` instead of `config.decay_enabled = False`. Rename it `test_slow_penalty_switch_off_skips_penalty`.
  - `DecayConfigTests.test_new_config_defaults`: replace `self.assertTrue(config.decay_enabled)` with `self.assertEqual((config.slow_penalty_enabled, config.idle_decay_enabled), (True, False))`.
  - `IdleDecayTaskTests`:
    - at the end of its `setUp`, add `config = LearnerActivityConfig.get(); config.idle_decay_enabled = True; config.save()` (idle decay is now off by default);
    - in `test_disabled_toggle_skips`, set `config.idle_decay_enabled = False` instead of `decay_enabled`;
    - add `test_idle_decay_is_recorded`: after `apply_competency_decay()`, `CompetencyChange.objects.get()` has `reason['rule'] == 'idle'` and `course == self.enrollment.course`.
- `hub/tests/test_learner_activity.py`: the four "toggle" tests keep their expected scores (a beginner course for a beginner teacher is gap 0, so a pass gives +1, a fail 0, and no quizzes +1). Delete the lines that set `quiz_affects_competency`, `quiz_weight_pass` and `quiz_weight_fail`, and rename the tests:
  - `test_toggle_off_always_gives_increment_of_1` → `test_course_without_scored_items_gives_one`;
  - `test_toggle_on_pass_gives_full_increment` → `test_passed_same_level_gives_one`;
  - `test_toggle_on_fail_gives_no_increment` → `test_failed_same_level_gives_zero`;
  - `test_toggle_on_no_quizzes_falls_back_to_full_increment` → `test_no_quizzes_gives_one`.

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_competency_performance -v 2`
  - Expected: ImportError, `cannot import name 'course_completion_change'`.

- [ ] **Step 3: Implement.** Replace `course_completion_delta` and extend `apply_competency_delta` in `backend/hub/competency.py`:

```python
"""Competency score changes: clamping, band-based pathway re-assignment, and
the course-completion rule (performance vs course difficulty).

Spec: docs/superpowers/specs/2026-10-21-competency-performance-design.md
(replaces the score rules of 2026-07-19-competency-decay-design.md).
"""
from collections import defaultdict

from hub.models import (
    AssignmentSubmission,
    CompetencyChange,
    LearnerActivityConfig,
    LearningPath,
    ResourceProgress,
    UserLearningPath,
)

SCORE_MIN = 0
SCORE_MAX = 6
COURSE_LEVELS = {'beginner': 0, 'intermediate': 1, 'advanced': 2}
SCORED_TYPES = ('quiz', 'h5p', 'assignment')
FIRST_REVIEW_SCORES = {'approved': 1.0, 'changes_requested': 0.0}


def _band(score: int) -> int:
    if score <= 2:
        return 0
    if score <= 4:
        return 1
    return 2


def apply_competency_delta(user, delta: int, recompute: bool = True, course=None, reason=None) -> int:
    """Apply delta to the user's competency score.

    Clamps to 0..6; records a CompetencyChange (with `course` and `reason`)
    when the score actually changes; re-assigns the learning path when the
    band changes in either direction; schedules a recommendations recompute
    (pass recompute=False when the caller batches several deltas). Returns
    the (possibly unchanged) score.
    """
    profile = user.profile
    old = profile.competency_score
    new = max(SCORE_MIN, min(SCORE_MAX, old + delta))
    if new == old:
        return old

    profile.competency_score = new
    profile.save(update_fields=['competency_score'])
    CompetencyChange.objects.create(user=user, course=course, old_score=old, new_score=new,
                                    delta=new - old, reason=reason or {})

    if _band(new) != _band(old):
        path = LearningPath.objects.filter(
            competency_min__lte=new, competency_max__gte=new,
        ).first()
        if path:
            # New level: new path and a course list rebuilt for that level.
            from hub.pathway_gen import generate_pathway
            UserLearningPath.objects.update_or_create(
                user=user, defaults={'path': path, 'course_ids': generate_pathway(user)},
            )

    if recompute:
        from hub.tasks import compute_user_recommendations
        compute_user_recommendations.delay(user.id)
    return new


def course_performance(user, course):
    """Mean over modules of the mean first-attempt score (0–1) of the scored
    items the user completed; None when nothing in the course counts."""
    rows = (
        ResourceProgress.objects
        .filter(user=user, resource__activity__module__course=course,
                completed_at__isnull=False, resource__type__in=SCORED_TYPES)
        .select_related('resource__activity')
    )
    first_reviews = dict(
        AssignmentSubmission.objects
        .filter(user=user, resource__activity__module__course=course)
        .exclude(first_review_status='')
        .values_list('resource_id', 'first_review_status')
    )
    by_module = defaultdict(list)
    for rp in rows:
        if rp.resource.type == 'assignment':
            score = FIRST_REVIEW_SCORES.get(first_reviews.get(rp.resource_id))
        else:
            score = rp.quiz_score          # set once, on the first completion
        if score is not None:
            by_module[rp.resource.activity.module_id].append(score)
    if not by_module:
        return None
    averages = [sum(scores) / len(scores) for scores in by_module.values()]
    return sum(averages) / len(averages)


def performance_delta(passed: bool, gap: int) -> int:
    """Change from the course-vs-teacher level gap (course level − teacher level)."""
    if gap < 0:
        return 0 if passed else -1
    if not passed:
        return 0
    return 2 if gap >= 2 else 1


def _is_slow(user, course, config) -> bool:
    """Mean ratio of time spent to planned time over the course's timed activities."""
    timed = list(
        ResourceProgress.objects.filter(
            user=user,
            resource__activity__module__course=course,
            completed_at__isnull=False,
            time_spent_seconds__isnull=False,
            resource__activity__duration_minutes__gt=0,
        ).select_related('resource__activity')
    )
    # One pace ratio per activity: its time is the max over its resources.
    per_activity = {}
    for rp in timed:
        act = rp.resource.activity
        per_activity[act.id] = (max(per_activity.get(act.id, (0, act))[0], rp.time_spent_seconds), act)
    if not per_activity:
        return False
    ratios = [(secs / 60) / act.duration_minutes for secs, act in per_activity.values()]
    return sum(ratios) / len(ratios) > config.slow_ratio_threshold


def course_completion_change(user, course):
    """(delta, reason) for a just-completed course."""
    config = LearnerActivityConfig.get()
    performance = course_performance(user, course)
    teacher_level = _band(user.profile.competency_score)
    course_level = COURSE_LEVELS.get(course.level, 0)
    gap = course_level - teacher_level
    if performance is None:
        rule, passed, base = 'completion', None, 1
    else:
        passed = performance >= config.quiz_pass_threshold
        rule, base = 'performance', performance_delta(passed, gap)
    slow = config.slow_penalty if config.slow_penalty_enabled and _is_slow(user, course, config) else 0
    reason = {
        'rule': rule, 'performance': None if performance is None else round(performance, 3), 'passed': passed,
        'course_level': course_level, 'teacher_level': teacher_level, 'gap': gap,
        'base_delta': base, 'slow_penalty': slow,
    }
    return base - slow, reason


def course_completion_delta(user, course) -> int:
    return course_completion_change(user, course)[0]
```

`backend/hub/completion.py`, in `recompute_course_progress`, replace:

```python
        from hub.competency import apply_competency_delta, course_completion_delta
        apply_competency_delta(user, course_completion_delta(user, course))
```

with:

```python
        from hub.competency import apply_competency_delta, course_completion_change
        delta, reason = course_completion_change(user, course)
        apply_competency_delta(user, delta, course=course, reason=reason)
```

`backend/hub/tasks.py`, `apply_competency_decay`:
- change `if not config.decay_enabled:` to `if not config.idle_decay_enabled:`;
- change `.select_related('user__profile')` to `.select_related('user__profile', 'course')`;
- pass the course and reason:

```python
        apply_competency_delta(
            enrollment.user, -config.idle_decay_points, recompute=False,
            course=enrollment.course, reason={'rule': 'idle', 'idle_days': config.idle_decay_days},
        )
```

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_competency_performance hub.tests.test_competency_decay hub.tests.test_learner_activity hub.tests.test_competency_scoring -v 2`
  - Expected: all pass.

- [ ] **Step 5: Full suite, lint, commit.**

```bash
"$UV" run ruff check hub analytics
"$UV" run manage.py test hub analytics
git add hub/competency.py hub/completion.py hub/tasks.py hub/tests/test_competency_performance.py hub/tests/test_competency_decay.py hub/tests/test_learner_activity.py
git commit -m "feat: competency from first-attempt performance vs course difficulty"
git push
```

---

### Task 3: Remove the old settings, admin labels, docs

**Files:**
- Modify: `backend/hub/models/activity.py`, `backend/hub/admin.py`, `backend/hub/tests/test_learner_activity.py`, `CLAUDE.md`
- Create: `backend/hub/migrations/0070_remove_old_competency_settings.py` (generated)

**Interfaces — Consumes:** nothing new. After this task, no code reads `decay_enabled`, `quiz_affects_competency` or `quiz_weight_*`.

- [ ] **Step 1: Write the failing test.** In `hub/tests/test_learner_activity.py`:
  - in `test_defaults`, replace the three asserts on `quiz_affects_competency`, `quiz_weight_pass` and `quiz_weight_fail` with:

```python
        for removed in ('quiz_affects_competency', 'quiz_weight_pass', 'quiz_weight_fail', 'decay_enabled'):
            self.assertFalse(hasattr(config, removed), removed)
```

  - in `test_save_enforces_singleton`, change `config.quiz_affects_competency = True` to `config.tracking_enabled = False`.

- [ ] **Step 2: Run it to verify it fails.**
  - Run: `"$UV" run manage.py test hub.tests.test_learner_activity -v 2`
  - Expected: `test_defaults` FAIL with "quiz_affects_competency".

- [ ] **Step 3: Implement.**
- In `LearnerActivityConfig`:
  - delete `quiz_affects_competency`, `quiz_weight_pass`, `quiz_weight_fail` and `decay_enabled`;
  - update the field comments so `quiz_pass_threshold` reads as the competency pass threshold (`# Competency: a course counts as passed at this first-attempt performance (0–1).`);
  - change `__str__` to return `'Learner activity settings'`.
- Remove the `slow_penalty_enabled` / `idle_decay_enabled` comment's mention of `decay_enabled`.
- Generate the migration with `"$UV" run manage.py makemigrations hub --name remove_old_competency_settings`. Expected: `0070_…` with four `RemoveField` operations, after 0069.

`backend/hub/admin.py`, `LearnerActivityConfigAdmin.fieldsets`: replace the first three sections with:

```python
        ('AI competency from performance', {
            'fields': ['quiz_pass_threshold'],
            'description': (
                'On completing a course, the first-attempt scores of its quizzes, scored H5P activities '
                'and assignments (approved on the first review = 100%, changes requested = 0%) are '
                'averaged per module, then across modules; passed = at least this threshold. '
                'Course harder than the teacher\'s level: +1 (+2 if two levels) when passed; same level: '
                '+1 when passed; easier: −1 when not passed; otherwise no change. Courses with no scored '
                'items give +1. Every change is listed under "Competency changes".'
            ),
        }),
        ('Slow-pace penalty', {
            'fields': ['slow_penalty_enabled', 'slow_ratio_threshold', 'slow_penalty'],
            'description': 'Subtracted on completion when the time spent averages more than the ratio × the planned time.',
        }),
        ('Idle decay', {
            'fields': ['idle_decay_enabled', 'idle_decay_days', 'idle_decay_points'],
            'description': 'Nightly: subtract points for each course started and not opened for this many days.',
        }),
```

`CLAUDE.md`: under the architecture notes, add one line: **AI competency** (`hub/competency.py`): on course completion the score moves by first-attempt performance vs course difficulty (spec `2026-10-21-competency-performance-design.md`); every change is a `CompetencyChange` row with its reason; slow-pace penalty and idle decay have separate switches in Learner activity settings.

- [ ] **Step 4: Verify.**
  - From `backend/`: `"$UV" run manage.py migrate`, `"$UV" run ruff check .`, `"$UV" run coverage run manage.py test hub analytics --verbosity=1`, `"$UV" run coverage report --fail-under=70` and `"$UV" run manage.py makemigrations --check --dry-run`.
  - Expected: all pass, and "No changes detected".
  - Also run `grep -rn "decay_enabled\|quiz_affects_competency\|quiz_weight_" hub --include=*.py | grep -v migrations`. Expected: no matches except `slow_penalty_enabled` / `idle_decay_enabled`.

- [ ] **Step 5: Commit.**

```bash
git add hub/models/activity.py hub/admin.py hub/migrations/0070_remove_old_competency_settings.py hub/tests/test_learner_activity.py ../CLAUDE.md
git commit -m "refactor: remove the old quiz toggle and single decay switch; admin explains the competency rule"
git push
```

- [ ] **Step 6: Rollout note for the user.** On the VM, with `COMPOSE_FILE` set:

```bash
git pull
docker compose up -d --build backend celery celery-beat
docker compose exec -T backend uv run python manage.py migrate      # 0068–0070
```

Then check in Django admin → Learner activity settings: **Slow-pace penalty** ticked and **Idle decay** unticked. Score changes from then on appear under **Competency changes**.
