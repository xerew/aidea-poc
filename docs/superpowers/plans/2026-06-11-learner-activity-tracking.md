# Learner Activity Tracking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture timing, quiz performance, and type-specific engagement signals for every lesson interaction, and wire quiz performance optionally into competency scoring via a configurable toggle and weights.

**Architecture:** `LessonProgress` gains four new fields (`time_spent_seconds`, `quiz_score`, `quiz_answers`, `engagement_data`) and `completed_at` changes from `auto_now_add` to an explicit field. A new lightweight `LessonSession` model records when each lesson is opened; `LessonCompleteView` reads the latest session to compute `time_spent_seconds`. A `LearnerActivityConfig` singleton (same pattern as existing `RecommendationConfig`) holds the quiz-competency toggle and weights. The `POST .../complete/` endpoint accepts quiz answer indices and engagement metadata from the frontend; quiz scores are computed server-side.

**Tech Stack:** Django 5.1, Django REST Framework, uv runner (`backend/.venv/Scripts/uv.exe`), ruff

---

## File Map

| File | Change |
|------|--------|
| `backend/hub/models/enrollment.py` | Enrich `LessonProgress`: 4 new fields, `completed_at` → explicit `null=True` |
| `backend/hub/models/activity.py` | **New**: `LessonSession`, `LearnerActivityConfig` |
| `backend/hub/models/__init__.py` | Export `LessonSession`, `LearnerActivityConfig` |
| `backend/hub/admin.py` | Fix `completed_at` None-safety; register new models |
| `backend/hub/views/learner.py` | `LessonDetailView.get()` creates `LessonSession`; full `LessonCompleteView.post()` rewrite |
| `backend/hub/migrations/0015_lessonprogress_activity_fields.py` | Auto-generated |
| `backend/hub/migrations/0016_activity_models.py` | Auto-generated |
| `backend/hub/tests/test_learner_activity.py` | **New**: all tests for this feature |

---

### Task 1: Enrich `LessonProgress` + fix admin

**Files:**
- Modify: `backend/hub/models/enrollment.py:26-35`
- Modify: `backend/hub/admin.py:94`
- Create: `backend/hub/migrations/0015_lessonprogress_activity_fields.py` (generated)
- Create: `backend/hub/tests/test_learner_activity.py`

- [ ] **Step 1: Write failing tests**

Create `backend/hub/tests/test_learner_activity.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import Course, Enrollment, LearningPillar, Lesson, LessonProgress, Module
from hub.models.user import UserProfile


class LessonProgressFieldsTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='lp1', password='pass')
        pillar = LearningPillar.objects.create(name='P1', slug='p1', description='')
        course = Course.objects.create(title='C1', pillar=pillar)
        module = Module.objects.create(title='M1', course=course, order=1)
        lesson = Lesson.objects.create(title='L1', module=module, order=1, is_required=True)
        self.lp = LessonProgress.objects.create(user=user, lesson=lesson)

    def test_time_spent_seconds_null_by_default(self):
        self.assertIsNone(self.lp.time_spent_seconds)

    def test_quiz_score_null_by_default(self):
        self.assertIsNone(self.lp.quiz_score)

    def test_quiz_answers_empty_by_default(self):
        self.assertEqual(self.lp.quiz_answers, [])

    def test_engagement_data_empty_by_default(self):
        self.assertEqual(self.lp.engagement_data, {})

    def test_completed_at_null_by_default(self):
        self.assertIsNone(self.lp.completed_at)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py test hub.tests.test_learner_activity --verbosity=2
```

Expected: 5 failures — fields do not exist yet.

- [ ] **Step 3: Modify `LessonProgress` in `backend/hub/models/enrollment.py`**

Replace the `LessonProgress` class (lines 26–35):

**Before:**
```python
class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress_records')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f'{self.user.username} → {self.lesson.title}'
```

**After:**
```python
class LessonProgress(models.Model):
    user               = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson             = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress_records')
    completed_at       = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.IntegerField(null=True, blank=True)
    quiz_score         = models.FloatField(null=True, blank=True)
    quiz_answers       = models.JSONField(default=list)
    engagement_data    = models.JSONField(default=dict)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f'{self.user.username} → {self.lesson.title}'
```

- [ ] **Step 4: Fix `completed_at` None-safety in `backend/hub/admin.py`**

Line 94 calls `.strftime()` on `r.completed_at` which will crash once `completed_at` can be `None`.

**Before (line 94):**
```python
            f'<td style="padding:4px 10px;border-bottom:1px solid #eee">{r.completed_at.strftime("%Y-%m-%d %H:%M UTC")}</td>'
```

**After:**
```python
            f'<td style="padding:4px 10px;border-bottom:1px solid #eee">{r.completed_at.strftime("%Y-%m-%d %H:%M UTC") if r.completed_at else "—"}</td>'
```

- [ ] **Step 5: Generate and apply migration**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py makemigrations hub --name lessonprogress_activity_fields
.venv\Scripts\uv.exe run manage.py migrate
```

Expected output ends with: `Applying hub.0015_lessonprogress_activity_fields... OK`

- [ ] **Step 6: Run tests — expect 5 to pass**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py test hub.tests.test_learner_activity --verbosity=2
```

Expected: 5 tests pass.

- [ ] **Step 7: Ruff check**

```bash
cd backend
.venv\Scripts\uv.exe run ruff check .
```

Expected: no output.

- [ ] **Step 8: Commit**

```bash
git add backend/hub/models/enrollment.py \
        backend/hub/admin.py \
        backend/hub/migrations/0015_lessonprogress_activity_fields.py \
        backend/hub/tests/test_learner_activity.py
git commit -m "feat: enrich LessonProgress with activity tracking fields"
```

---

### Task 2: `LessonSession` and `LearnerActivityConfig` models

**Files:**
- Create: `backend/hub/models/activity.py`
- Modify: `backend/hub/models/__init__.py`
- Modify: `backend/hub/admin.py`
- Create: `backend/hub/migrations/0016_activity_models.py` (generated)
- Modify: `backend/hub/tests/test_learner_activity.py` (append)

- [ ] **Step 1: Append failing tests**

Append to `backend/hub/tests/test_learner_activity.py`:

```python


class LessonSessionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ls1', password='pass')
        pillar = LearningPillar.objects.create(name='P2', slug='p2', description='')
        course = Course.objects.create(title='C2', pillar=pillar)
        module = Module.objects.create(title='M2', course=course, order=1)
        self.lesson = Lesson.objects.create(title='L2', module=module, order=1, is_required=True)

    def test_session_created_with_started_at(self):
        from hub.models.activity import LessonSession
        session = LessonSession.objects.create(user=self.user, lesson=self.lesson)
        self.assertIsNotNone(session.started_at)

    def test_multiple_sessions_allowed_for_same_user_lesson(self):
        from hub.models.activity import LessonSession
        LessonSession.objects.create(user=self.user, lesson=self.lesson)
        LessonSession.objects.create(user=self.user, lesson=self.lesson)
        self.assertEqual(
            LessonSession.objects.filter(user=self.user, lesson=self.lesson).count(), 2
        )


class LearnerActivityConfigTest(TestCase):
    def test_get_creates_singleton(self):
        from hub.models.activity import LearnerActivityConfig
        config = LearnerActivityConfig.get()
        self.assertEqual(config.pk, 1)

    def test_get_returns_same_instance(self):
        from hub.models.activity import LearnerActivityConfig
        config1 = LearnerActivityConfig.get()
        config2 = LearnerActivityConfig.get()
        self.assertEqual(LearnerActivityConfig.objects.count(), 1)
        self.assertEqual(config1.pk, config2.pk)

    def test_defaults(self):
        from hub.models.activity import LearnerActivityConfig
        config = LearnerActivityConfig.get()
        self.assertFalse(config.quiz_affects_competency)
        self.assertAlmostEqual(config.quiz_pass_threshold, 0.7)
        self.assertAlmostEqual(config.quiz_weight_pass, 1.0)
        self.assertAlmostEqual(config.quiz_weight_fail, 0.5)

    def test_save_enforces_singleton(self):
        from hub.models.activity import LearnerActivityConfig
        config = LearnerActivityConfig.get()
        config.quiz_affects_competency = True
        config.save()
        self.assertEqual(LearnerActivityConfig.objects.count(), 1)
```

- [ ] **Step 2: Run new tests to confirm failure**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py test hub.tests.test_learner_activity.LessonSessionTest hub.tests.test_learner_activity.LearnerActivityConfigTest --verbosity=2
```

Expected: 6 failures — `activity` module does not exist yet.

- [ ] **Step 3: Create `backend/hub/models/activity.py`**

```python
from django.contrib.auth.models import User
from django.db import models

from .content import Lesson


class LessonSession(models.Model):
    """Records the moment a teacher opens a lesson — used to compute time_spent_seconds."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_sessions')
    lesson     = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.user.username} opened {self.lesson.title} at {self.started_at}'


class LearnerActivityConfig(models.Model):
    """Singleton config for learner activity tracking and quiz-competency weighting."""
    quiz_affects_competency = models.BooleanField(default=False)
    quiz_pass_threshold     = models.FloatField(default=0.7)
    quiz_weight_pass        = models.FloatField(default=1.0)
    quiz_weight_fail        = models.FloatField(default=0.5)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'LearnerActivityConfig (quiz_affects_competency={self.quiz_affects_competency})'
```

- [ ] **Step 4: Update `backend/hub/models/__init__.py`**

Add the new models to the imports and `__all__`:

```python
from .activity import LearnerActivityConfig, LessonSession
from .content import Course, LearningPillar, Lesson, Module
from .enrollment import Enrollment, LessonProgress
from .history import CourseEditHistory
from .pathway import LearningPath, LearningPathCourse, UserLearningPath
from .recommendations import (
    CourseEmbedding,
    CourseRecommendation,
    CourseView,
    RecommendationConfig,
    RecommendationEvent,
)
from .user import UserProfile

__all__ = [
    'Course',
    'CourseEditHistory',
    'CourseEmbedding',
    'CourseRecommendation',
    'CourseView',
    'Enrollment',
    'LearnerActivityConfig',
    'LearningPath',
    'LearningPathCourse',
    'LearningPillar',
    'LessonProgress',
    'LessonSession',
    'Module',
    'Lesson',
    'RecommendationConfig',
    'RecommendationEvent',
    'UserLearningPath',
    'UserProfile',
]
```

- [ ] **Step 5: Register new models in `backend/hub/admin.py`**

Add to the imports at the top of `admin.py` (update the existing hub.models import line):

```python
from .models import (
    Course,
    CourseEditHistory,
    Enrollment,
    LearnerActivityConfig,
    LearningPillar,
    Lesson,
    LessonProgress,
    LessonSession,
    Module,
    UserProfile,
)
```

Append at the bottom of `admin.py`:

```python
@admin.register(LessonSession)
class LessonSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'started_at']
    list_filter = ['lesson__lesson_type', 'lesson__module__course__pillar']
    search_fields = ['user__username', 'lesson__title']
    readonly_fields = ['user', 'lesson', 'started_at']
    ordering = ['-started_at']


@admin.register(LearnerActivityConfig)
class LearnerActivityConfigAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Quiz → Competency toggle', {
            'fields': ['quiz_affects_competency'],
        }),
        ('Weights (active when toggle is on)', {
            'fields': ['quiz_pass_threshold', 'quiz_weight_pass', 'quiz_weight_fail'],
        }),
    ]

    def has_add_permission(self, request):
        return not LearnerActivityConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
```

- [ ] **Step 6: Generate and apply migration**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py makemigrations hub --name activity_models
.venv\Scripts\uv.exe run manage.py migrate
```

Expected output ends with: `Applying hub.0016_activity_models... OK`

- [ ] **Step 7: Run tests — expect 6 new tests to pass (11 total)**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py test hub.tests.test_learner_activity --verbosity=2
```

Expected: 11 tests pass.

- [ ] **Step 8: Ruff check**

```bash
cd backend
.venv\Scripts\uv.exe run ruff check .
```

Expected: no output.

- [ ] **Step 9: Commit**

```bash
git add backend/hub/models/activity.py \
        backend/hub/models/__init__.py \
        backend/hub/admin.py \
        backend/hub/migrations/0016_activity_models.py \
        backend/hub/tests/test_learner_activity.py
git commit -m "feat: add LessonSession and LearnerActivityConfig models"
```

---

### Task 3: `LessonDetailView` creates `LessonSession` on open

**Files:**
- Modify: `backend/hub/views/learner.py:138-177`
- Modify: `backend/hub/tests/test_learner_activity.py` (append)

- [ ] **Step 1: Append failing tests**

Append to `backend/hub/tests/test_learner_activity.py`:

```python


class LessonSessionOnOpenTest(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.user = User.objects.create_user(username='lo1', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P3', slug='p3', description='')
        self.course = Course.objects.create(title='C3', pillar=pillar)
        module = Module.objects.create(title='M3', course=self.course, order=1)
        self.lesson = Lesson.objects.create(title='L3', module=module, order=1, is_required=True)
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_session_created_on_lesson_get(self):
        from hub.models.activity import LessonSession
        self.client.get(f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/')
        self.assertEqual(
            LessonSession.objects.filter(user=self.user, lesson=self.lesson).count(), 1
        )

    def test_multiple_opens_create_multiple_sessions(self):
        from hub.models.activity import LessonSession
        self.client.get(f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/')
        self.client.get(f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/')
        self.assertEqual(
            LessonSession.objects.filter(user=self.user, lesson=self.lesson).count(), 2
        )
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py test hub.tests.test_learner_activity.LessonSessionOnOpenTest --verbosity=2
```

Expected: 2 failures — no session created yet.

- [ ] **Step 3: Update `LessonDetailView.get()` in `backend/hub/views/learner.py`**

Add `LessonSession` to the hub.models import at the top of `learner.py`:

**Before:**
```python
from hub.models import Course, Enrollment, LearningPillar, Lesson, LessonProgress
```

**After:**
```python
from hub.models import Course, Enrollment, LearningPillar, Lesson, LessonProgress, LessonSession
```

In `LessonDetailView.get()`, add session creation after the lesson is fetched (after the `except Lesson.DoesNotExist` block, before building `all_ids`):

**Before (line ~152–160):**
```python
        try:
            lesson = Lesson.objects.select_related('module').get(
                pk=lesson_pk, module__course=course,
            )
        except Lesson.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        all_ids = list(
```

**After:**
```python
        try:
            lesson = Lesson.objects.select_related('module').get(
                pk=lesson_pk, module__course=course,
            )
        except Lesson.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        LessonSession.objects.create(user=request.user, lesson=lesson)

        all_ids = list(
```

- [ ] **Step 4: Run tests — expect 2 new tests to pass (13 total)**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py test hub.tests.test_learner_activity --verbosity=2
```

Expected: 13 tests pass.

- [ ] **Step 5: Ruff check**

```bash
cd backend
.venv\Scripts\uv.exe run ruff check .
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add backend/hub/views/learner.py \
        backend/hub/tests/test_learner_activity.py
git commit -m "feat: create LessonSession when teacher opens a lesson"
```

---

### Task 4: `LessonCompleteView` — timing, quiz scoring, engagement data

**Files:**
- Modify: `backend/hub/views/learner.py:180-232`
- Modify: `backend/hub/tests/test_learner_activity.py` (append)

- [ ] **Step 1: Append failing tests**

Append to `backend/hub/tests/test_learner_activity.py`:

```python


class EngagementTrackingTest(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.user = User.objects.create_user(username='et1', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P4', slug='p4', description='')
        self.course = Course.objects.create(title='C4', pillar=pillar)
        self.module = Module.objects.create(title='M4', course=self.course, order=1)
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _lesson(self, title, lesson_type='text', quiz_data=None):
        return Lesson.objects.create(
            title=title,
            module=self.module,
            order=Lesson.objects.filter(module=self.module).count() + 1,
            is_required=True,
            lesson_type=lesson_type,
            quiz_data=quiz_data or [],
        )

    def test_time_spent_computed_when_session_exists(self):
        lesson = self._lesson('T1')
        self.client.get(f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/', {}, format='json'
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertIsNotNone(lp.time_spent_seconds)
        self.assertGreaterEqual(lp.time_spent_seconds, 0)

    def test_time_spent_null_without_session(self):
        lesson = self._lesson('T2')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/', {}, format='json'
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertIsNone(lp.time_spent_seconds)

    def test_completed_at_set_on_first_complete(self):
        lesson = self._lesson('T3')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/', {}, format='json'
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertIsNotNone(lp.completed_at)

    def test_quiz_score_computed_server_side(self):
        quiz_data = [
            {'question': 'Q1', 'options': [
                {'text': 'A', 'is_correct': False},
                {'text': 'B', 'is_correct': True},
            ]},
            {'question': 'Q2', 'options': [
                {'text': 'C', 'is_correct': True},
                {'text': 'D', 'is_correct': False},
            ]},
        ]
        lesson = self._lesson('Q1', lesson_type='quiz', quiz_data=quiz_data)
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'quiz_answers': [1, 0]},
            format='json',
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertAlmostEqual(lp.quiz_score, 1.0)
        self.assertEqual(lp.quiz_answers, [True, True])

    def test_quiz_score_partial(self):
        quiz_data = [
            {'question': 'Q1', 'options': [
                {'text': 'A', 'is_correct': False},
                {'text': 'B', 'is_correct': True},
            ]},
            {'question': 'Q2', 'options': [
                {'text': 'C', 'is_correct': True},
                {'text': 'D', 'is_correct': False},
            ]},
        ]
        lesson = self._lesson('Q2', lesson_type='quiz', quiz_data=quiz_data)
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'quiz_answers': [0, 0]},
            format='json',
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertAlmostEqual(lp.quiz_score, 0.5)
        self.assertEqual(lp.quiz_answers, [False, True])

    def test_text_scroll_pct_stored(self):
        lesson = self._lesson('T4', lesson_type='text')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'engagement_data': {'scroll_pct': 85}},
            format='json',
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertEqual(lp.engagement_data.get('scroll_pct'), 85)

    def test_assignment_word_count_derived(self):
        lesson = self._lesson('A1', lesson_type='assignment')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'engagement_data': {'submission': 'hello world this is a test'}},
            format='json',
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertEqual(lp.engagement_data.get('word_count'), 6)
        self.assertEqual(lp.engagement_data.get('submission'), 'hello world this is a test')

    def test_engagement_not_overwritten_on_repeat_complete(self):
        lesson = self._lesson('T5', lesson_type='text')
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'engagement_data': {'scroll_pct': 50}},
            format='json',
        )
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{lesson.pk}/complete/',
            {'engagement_data': {'scroll_pct': 99}},
            format='json',
        )
        lp = LessonProgress.objects.get(user=self.user, lesson=lesson)
        self.assertEqual(lp.engagement_data.get('scroll_pct'), 50)
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py test hub.tests.test_learner_activity.EngagementTrackingTest --verbosity=2
```

Expected: 8 failures — `LessonProgress` rows created by the view still have `completed_at=None` (auto_now_add removed, not yet explicitly set) and no engagement fields populated.

- [ ] **Step 3: Rewrite `LessonCompleteView.post()` in `backend/hub/views/learner.py`**

Replace the entire `post` method of `LessonCompleteView` (lines 183–232):

```python
    def post(self, request, pk, lesson_pk):
        try:
            enrollment = Enrollment.objects.select_related('course').get(
                user=request.user, course_id=pk,
            )
        except Enrollment.DoesNotExist:
            if not Course.objects.filter(pk=pk).exists():
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)

        course = enrollment.course

        try:
            lesson = Lesson.objects.select_related('module').get(
                pk=lesson_pk, module__course=course,
            )
        except Lesson.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        lp, created = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

        if created:
            now = timezone.now()
            lp.completed_at = now

            session = LessonSession.objects.filter(
                user=request.user, lesson=lesson,
            ).order_by('-started_at').first()
            if session:
                lp.time_spent_seconds = int((now - session.started_at).total_seconds())

            quiz_answers_raw = request.data.get('quiz_answers', [])
            if lesson.lesson_type == 'quiz' and quiz_answers_raw and lesson.quiz_data:
                booleans = []
                for i, selected in enumerate(quiz_answers_raw):
                    if i < len(lesson.quiz_data):
                        options = lesson.quiz_data[i].get('options', [])
                        if isinstance(selected, int) and 0 <= selected < len(options):
                            booleans.append(bool(options[selected].get('is_correct', False)))
                        else:
                            booleans.append(False)
                lp.quiz_answers = booleans
                lp.quiz_score = sum(booleans) / len(booleans) if booleans else 0.0

            engagement = dict(request.data.get('engagement_data') or {})
            if lesson.lesson_type == 'assignment' and 'submission' in engagement:
                engagement['word_count'] = len(str(engagement['submission']).split())
            lp.engagement_data = engagement

            lp.save()

        total = Lesson.objects.filter(module__course=course, is_required=True).count()
        completed_count = LessonProgress.objects.filter(
            user=request.user,
            lesson__module__course=course,
            lesson__is_required=True,
        ).count()
        progress_pct = round((completed_count / total) * 100) if total > 0 else 0

        just_completed = progress_pct == 100 and enrollment.completed_at is None
        enrollment.progress_pct = progress_pct
        enrollment.current_module = lesson.module
        if just_completed:
            enrollment.completed_at = timezone.now()
        enrollment.save()

        if just_completed and hasattr(request.user, 'profile'):
            profile = request.user.profile
            if profile.competency_score < 6:
                profile.competency_score = min(profile.competency_score + 1, 6)
                profile.save(update_fields=['competency_score'])
                from hub.tasks import compute_user_recommendations
                compute_user_recommendations.delay(request.user.id)

        return Response({
            'lesson_id': lesson.id,
            'is_completed': True,
            'progress_pct': progress_pct,
        })
```

Note: The competency block still uses `+1` here — Task 5 will wire in the config-based weighting.

- [ ] **Step 4: Run engagement tests — expect 8 to pass (21 total)**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py test hub.tests.test_learner_activity --verbosity=2
```

Expected: 21 tests pass.

- [ ] **Step 5: Run full test suite to check no regressions**

```bash
cd backend
.venv\Scripts\uv.exe run coverage run manage.py test hub --verbosity=2
.venv\Scripts\uv.exe run coverage report
```

Expected: all existing tests still pass, coverage ≥ 85%.

- [ ] **Step 6: Ruff check**

```bash
cd backend
.venv\Scripts\uv.exe run ruff check .
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add backend/hub/views/learner.py \
        backend/hub/tests/test_learner_activity.py
git commit -m "feat: track timing, quiz scores, and engagement data on lesson completion"
```

---

### Task 5: Competency weighting via `LearnerActivityConfig`

**Files:**
- Modify: `backend/hub/views/learner.py` (competency block inside `LessonCompleteView.post()`)
- Modify: `backend/hub/tests/test_learner_activity.py` (append)

- [ ] **Step 1: Append failing tests**

Append to `backend/hub/tests/test_learner_activity.py`:

```python


class CompetencyWeightingTest(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from hub.models.activity import LearnerActivityConfig
        self.user = User.objects.create_user(username='cw1', password='pass')
        self.profile = UserProfile.objects.create(
            user=self.user,
            user_type=UserProfile.UserType.TEACHER,
            competency_score=0,
            onboarding_completed=True,
        )
        pillar = LearningPillar.objects.create(name='P5', slug='p5', description='')
        self.course = Course.objects.create(title='C5', pillar=pillar)
        module = Module.objects.create(title='M5', course=self.course, order=1)
        self.required_lesson = Lesson.objects.create(
            title='RL', module=module, order=1, is_required=True, lesson_type='text',
        )
        self.quiz_lesson = Lesson.objects.create(
            title='QL',
            module=module,
            order=2,
            is_required=False,
            lesson_type='quiz',
            quiz_data=[{
                'question': 'Q',
                'options': [
                    {'text': 'Right', 'is_correct': True},
                    {'text': 'Wrong', 'is_correct': False},
                ],
            }],
        )
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.config = LearnerActivityConfig.get()

    def _complete_required(self):
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.required_lesson.pk}/complete/',
            {}, format='json',
        )

    def _complete_quiz(self, answers):
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.quiz_lesson.pk}/complete/',
            {'quiz_answers': answers},
            format='json',
        )

    def test_toggle_off_always_gives_increment_of_1(self):
        self.config.quiz_affects_competency = False
        self.config.save()
        self._complete_required()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 1)

    def test_toggle_on_pass_gives_full_increment(self):
        self.config.quiz_affects_competency = True
        self.config.quiz_pass_threshold = 0.7
        self.config.quiz_weight_pass = 1.0
        self.config.save()
        self._complete_quiz([0])  # correct answer → score 1.0
        self._complete_required()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 1)

    def test_toggle_on_fail_gives_no_increment(self):
        self.config.quiz_affects_competency = True
        self.config.quiz_pass_threshold = 0.7
        self.config.quiz_weight_fail = 0.5  # int(0.5) = 0 → no increment
        self.config.save()
        self._complete_quiz([1])  # wrong answer → score 0.0
        self._complete_required()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 0)

    def test_toggle_on_no_quizzes_falls_back_to_full_increment(self):
        pillar = LearningPillar.objects.create(name='P6', slug='p6', description='')
        course2 = Course.objects.create(title='C6', pillar=pillar)
        module2 = Module.objects.create(title='M6', course=course2, order=1)
        lesson2 = Lesson.objects.create(
            title='L6', module=module2, order=1, is_required=True, lesson_type='text',
        )
        Enrollment.objects.create(user=self.user, course=course2)
        self.config.quiz_affects_competency = True
        self.config.save()
        self.client.post(
            f'/api/courses/{course2.pk}/lessons/{lesson2.pk}/complete/', {}, format='json',
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 1)
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py test hub.tests.test_learner_activity.CompetencyWeightingTest --verbosity=2
```

Expected: `test_toggle_on_pass_gives_full_increment` passes (coincidentally correct), `test_toggle_on_fail_gives_no_increment` fails (still gives +1 regardless of config), `test_toggle_on_no_quizzes_falls_back_to_full_increment` passes. So at least 1 failure.

- [ ] **Step 3: Replace the competency block in `LessonCompleteView.post()`**

Find this block in `backend/hub/views/learner.py` (inside `LessonCompleteView.post()`):

**Before:**
```python
        if just_completed and hasattr(request.user, 'profile'):
            profile = request.user.profile
            if profile.competency_score < 6:
                profile.competency_score = min(profile.competency_score + 1, 6)
                profile.save(update_fields=['competency_score'])
                from hub.tasks import compute_user_recommendations
                compute_user_recommendations.delay(request.user.id)
```

**After:**
```python
        if just_completed and hasattr(request.user, 'profile'):
            profile = request.user.profile
            if profile.competency_score < 6:
                from hub.models.activity import LearnerActivityConfig
                config = LearnerActivityConfig.get()
                if config.quiz_affects_competency:
                    quiz_scores = list(
                        LessonProgress.objects.filter(
                            user=request.user,
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
                    increment = int(weight)
                else:
                    increment = 1
                profile.competency_score = min(profile.competency_score + increment, 6)
                profile.save(update_fields=['competency_score'])
                from hub.tasks import compute_user_recommendations
                compute_user_recommendations.delay(request.user.id)
```

- [ ] **Step 4: Run all learner activity tests — expect all 25 to pass**

```bash
cd backend
.venv\Scripts\uv.exe run manage.py test hub.tests.test_learner_activity --verbosity=2
```

Expected: 25 tests pass.

- [ ] **Step 5: Run full test suite — expect no regressions**

```bash
cd backend
.venv\Scripts\uv.exe run coverage run manage.py test hub --verbosity=2
.venv\Scripts\uv.exe run coverage report
```

Expected: all tests pass, coverage ≥ 85%.

- [ ] **Step 6: Ruff check**

```bash
cd backend
.venv\Scripts\uv.exe run ruff check .
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add backend/hub/views/learner.py \
        backend/hub/tests/test_learner_activity.py
git commit -m "feat: weight competency increment by quiz score via LearnerActivityConfig"
```

---

## Done

After all five tasks every lesson completion produces:
- `LessonProgress.completed_at` — explicit timestamp
- `LessonProgress.time_spent_seconds` — seconds from lesson open to completion (null if lesson not opened via the API first)
- `LessonProgress.quiz_score` — 0.0–1.0 float, server-computed (quiz lessons only)
- `LessonProgress.quiz_answers` — `[true, false, ...]` boolean per question (quiz lessons only)
- `LessonProgress.engagement_data` — `{"scroll_pct": N}` / `{"video_pct": N}` / `{"submission": "...", "word_count": N}` depending on lesson type

The `LearnerActivityConfig` singleton (editable in Django admin) controls whether and how quiz performance weights the competency score increment.
