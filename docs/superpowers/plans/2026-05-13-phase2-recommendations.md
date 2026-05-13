# Phase 2 — Intelligent Recommendation Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-signal content-based recommender with a four-signal hybrid engine that produces two recommendation rows on the Home page — "Recommended for you" (personal engine, 5 cards) and "Teachers like you also took" (CF engine, 3 cards) — and introduces a hybrid bandit that auto-tunes weights once enough interaction data has been collected.

**Architecture:** Signals ①②③ (onboarding profile, explicit preferences, implicit behaviour) feed a personal engine whose weights start deterministic and are gradient-nudged nightly by a bandit once N_MIN events are collected. Signal ④ (peer co-enrollment) runs in a fully independent CF pipeline. Both pipelines write to `CourseRecommendation` with a `source` field ('personal' / 'cf') so the frontend can split them into two UI rows.

**Tech Stack:** Django 6, PostgreSQL + pgvector, Celery + celery-beat, sentence-transformers `all-MiniLM-L6-v2`, numpy, React 19 + Vite

---

## File map

### New files
| File | Purpose |
|---|---|
| `backend/hub/serializers/recommendations.py` | `RecommendationEventSerializer` for the events endpoint |
| `backend/hub/serializers/profile.py` | `ProfilePreferencesSerializer` for PATCH endpoint |
| `backend/hub/views/profile.py` | `ProfilePreferencesView` (GET + PATCH) |
| `frontend/src/pages/ProfilePage.jsx` | Profile page with learning preferences section |
| `frontend/src/pages/ProfilePage.css` | Styling for profile page |

### Modified files
| File | Change |
|---|---|
| `backend/hub/models/user.py` | Add `preferred_pillars`, `learning_style` to `UserProfile` |
| `backend/hub/models/content.py` | Add `content_format` to `Course` |
| `backend/hub/models/recommendations.py` | Add `source` to `CourseRecommendation`; add `RecommendationConfig`, `RecommendationEvent`, `CourseView` |
| `backend/hub/models/__init__.py` | Export new models |
| `backend/hub/tasks.py` | Rewrite `compute_user_recommendations`; add `compute_cf_recommendations`, `tune_recommendation_weights`; extend `recompute_all_recommendations` |
| `backend/hub/views/recommendations.py` | Add `RecommendationEventView` |
| `backend/hub/views/learner.py` | Log `CourseView` in `CourseDetailView`; fire enrolled event in `CourseEnrollView` |
| `backend/hub/views/__init__.py` | Export new views |
| `backend/hub/serializers/pathway.py` | Add `source` field to `RecommendationSerializer` |
| `backend/hub/serializers/auth.py` | Add `preferred_pillars`, `learning_style` to `UserProfileSerializer` |
| `backend/hub/urls.py` | Add `recommendation-event` and `profile-preferences` URL patterns |
| `backend/hub/admin.py` | Register `RecommendationConfig`, `RecommendationEvent`, `CourseView` |
| `backend/aidea/settings.py` | Add `tune_recommendation_weights` to `CELERY_BEAT_SCHEDULE` |
| `frontend/src/App.jsx` | Replace `PlaceholderPage` at `/profile` with `ProfilePage` |
| `frontend/src/pages/HomePage.jsx` | Add CF row; fire shown + clicked recommendation events |
| `frontend/src/pages/HomePage.css` | Styles for CF row |
| `frontend/src/pages/CourseDetailPage.jsx` | Fire enrolled event when enrolling from a recommendation |

---

## Task 1: Extend existing models — UserProfile, Course, CourseRecommendation

**Files:**
- Modify: `backend/hub/models/user.py`
- Modify: `backend/hub/models/content.py`
- Modify: `backend/hub/models/recommendations.py`
- Test: `backend/hub/tests/test_phase2_models.py` (create new file)

- [ ] **Step 1: Write the failing test**

Create `backend/hub/tests/test_phase2_models.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import Course, LearningPillar, UserProfile
from hub.models.recommendations import CourseRecommendation


class UserProfileNewFieldsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='t1', password='pass')

    def test_preferred_pillars_defaults_to_empty_list(self):
        profile = UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.assertEqual(profile.preferred_pillars, [])

    def test_learning_style_defaults_to_blank(self):
        profile = UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.assertEqual(profile.learning_style, '')


class CourseNewFieldsTest(TestCase):
    def setUp(self):
        self.pillar = LearningPillar.objects.create(name='P', slug='p', description='')

    def test_content_format_defaults_to_mixed(self):
        course = Course.objects.create(title='T', pillar=self.pillar)
        self.assertEqual(course.content_format, 'mixed')

    def test_content_format_choices_accepted(self):
        for fmt in ['video', 'text', 'visual', 'interactive', 'mixed']:
            c = Course.objects.create(title=f'C-{fmt}', pillar=self.pillar, content_format=fmt)
            self.assertEqual(c.content_format, fmt)


class CourseRecommendationSourceFieldTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='t2', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P2', slug='p2', description='')
        self.course = Course.objects.create(title='T2', pillar=pillar)

    def test_source_defaults_to_personal(self):
        rec = CourseRecommendation.objects.create(
            user=self.user, course=self.course, score=0.8, reason='test'
        )
        self.assertEqual(rec.source, 'personal')

    def test_source_cf_accepted(self):
        rec = CourseRecommendation.objects.create(
            user=self.user, course=self.course, score=0.6, reason='cf test', source='cf'
        )
        self.assertEqual(rec.source, 'cf')
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_models --verbosity=2
```

Expected: `django.db.utils.OperationalError` — columns do not exist yet.

- [ ] **Step 3: Extend `UserProfile` in `backend/hub/models/user.py`**

Add the two inner choice classes and two fields. Full file after edit:

```python
from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    class UserType(models.TextChoices):
        TEACHER         = 'teacher',         'Teacher'
        CONTENT_CREATOR = 'content_creator', 'Content Creator'
        ADMIN           = 'admin',           'Admin'

    class SubjectArea(models.TextChoices):
        STEM       = 'stem',       'STEM'
        HUMANITIES = 'humanities', 'Humanities'
        LANGUAGES  = 'languages',  'Languages'
        ARTS       = 'arts',       'Arts'
        GENERAL    = 'general',    'General / Multiple'

    class TeachingLevel(models.TextChoices):
        PRIMARY    = 'primary',    'Primary (K-6)'
        SECONDARY  = 'secondary',  'Secondary (7-12)'
        HIGHER_ED  = 'higher_ed',  'Higher Education'
        VOCATIONAL = 'vocational', 'Vocational'
        ADULT_ED   = 'adult_ed',   'Adult Education'

    class LearningStyle(models.TextChoices):
        VIDEO       = 'video',       'Video'
        TEXT        = 'text',        'Text'
        VISUAL      = 'visual',      'Visual'
        INTERACTIVE = 'interactive', 'Interactive'

    user                 = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type            = models.CharField(max_length=20, choices=UserType.choices, default=UserType.TEACHER)
    avatar_initials      = models.CharField(max_length=4, blank=True)
    competency_score     = models.PositiveSmallIntegerField(default=0)
    subject_area         = models.CharField(max_length=20, choices=SubjectArea.choices, blank=True)
    teaching_level       = models.CharField(max_length=20, choices=TeachingLevel.choices, blank=True)
    goals                = models.JSONField(default=list, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    preferred_pillars    = models.JSONField(default=list, blank=True)
    learning_style       = models.CharField(
        max_length=20, choices=LearningStyle.choices, blank=True,
    )

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.get_user_type_display()})'
```

- [ ] **Step 4: Add `content_format` to `Course` in `backend/hub/models/content.py`**

Add a new inner `ContentFormat` choice class and field to `Course`. Add right after the `Level` class and add the field at the end of the `Course` model fields:

```python
class ContentFormat(models.TextChoices):
    VIDEO       = 'video',       'Video'
    TEXT        = 'text',        'Text'
    VISUAL      = 'visual',      'Visual'
    INTERACTIVE = 'interactive', 'Interactive'
    MIXED       = 'mixed',       'Mixed'
```

And at the end of `Course`'s field list (before the `Meta` class):

```python
content_format = models.CharField(
    max_length=20, choices=ContentFormat.choices, default=ContentFormat.MIXED,
)
```

- [ ] **Step 5: Add `source` field to `CourseRecommendation` in `backend/hub/models/recommendations.py`**

The existing `CourseRecommendation` ends at line 29. Add one field inside the class, before `class Meta`:

```python
source = models.CharField(max_length=20, default='personal')
```

Full `CourseRecommendation` model after the edit:

```python
class CourseRecommendation(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='recommendations')
    score       = models.FloatField()
    reason      = models.CharField(max_length=200)
    source      = models.CharField(max_length=20, default='personal')
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-score']

    def __str__(self):
        return f'{self.user.username} → {self.course.title} ({self.score:.2f})'
```

- [ ] **Step 6: Run tests — should still fail (no migration yet)**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_models --verbosity=2
```

Expected: still `OperationalError` — migration not yet applied.

- [ ] **Step 7: Commit the model changes (pre-migration)**

```bash
git add backend/hub/models/user.py backend/hub/models/content.py backend/hub/models/recommendations.py
git commit -m "feat: add phase2 fields to UserProfile, Course, CourseRecommendation"
```

---

## Task 2: New models — RecommendationConfig, RecommendationEvent, CourseView

**Files:**
- Modify: `backend/hub/models/recommendations.py`
- Test: `backend/hub/tests/test_phase2_models.py`

- [ ] **Step 1: Write failing tests for new models — add to `test_phase2_models.py`**

Append this block to the existing `test_phase2_models.py`:

```python
from hub.models.recommendations import CourseView, RecommendationConfig, RecommendationEvent


class RecommendationConfigTest(TestCase):
    def test_get_creates_singleton_on_first_call(self):
        config = RecommendationConfig.get()
        self.assertEqual(RecommendationConfig.objects.count(), 1)
        self.assertEqual(config.pk, 1)

    def test_get_returns_same_instance_on_second_call(self):
        c1 = RecommendationConfig.get()
        c2 = RecommendationConfig.get()
        self.assertEqual(c1.pk, c2.pk)
        self.assertEqual(RecommendationConfig.objects.count(), 1)

    def test_default_blend_weights(self):
        config = RecommendationConfig.get()
        self.assertAlmostEqual(config.alpha, 0.3)
        self.assertAlmostEqual(config.beta, 0.5)
        self.assertAlmostEqual(config.gamma, 0.2)

    def test_bandit_inactive_by_default(self):
        config = RecommendationConfig.get()
        self.assertFalse(config.bandit_active)

    def test_save_always_uses_pk_1(self):
        config = RecommendationConfig.get()
        config.alpha = 0.4
        config.save()
        self.assertEqual(RecommendationConfig.objects.count(), 1)
        self.assertAlmostEqual(RecommendationConfig.objects.get(pk=1).alpha, 0.4)


class CourseViewModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tv1', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P3', slug='p3', description='')
        self.course = Course.objects.create(title='TV', pillar=pillar)

    def test_course_view_created(self):
        cv = CourseView.objects.create(user=self.user, course=self.course)
        self.assertIsNotNone(cv.created_at)
        self.assertEqual(CourseView.objects.filter(user=self.user).count(), 1)

    def test_multiple_views_allowed(self):
        CourseView.objects.create(user=self.user, course=self.course)
        CourseView.objects.create(user=self.user, course=self.course)
        self.assertEqual(CourseView.objects.filter(user=self.user, course=self.course).count(), 2)


class RecommendationEventModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='re1', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P4', slug='p4', description='')
        self.course = Course.objects.create(title='RE', pillar=pillar)

    def test_all_event_types_accepted(self):
        for et in ['shown', 'clicked', 'enrolled', 'completed']:
            ev = RecommendationEvent.objects.create(
                user=self.user,
                course=self.course,
                event_type=et,
                rank=1,
                source='personal',
                weights_snapshot={'alpha': 0.3},
            )
            self.assertEqual(ev.event_type, et)

    def test_cf_source_accepted(self):
        ev = RecommendationEvent.objects.create(
            user=self.user, course=self.course,
            event_type='shown', rank=1, source='cf',
            weights_snapshot={},
        )
        self.assertEqual(ev.source, 'cf')
```

- [ ] **Step 2: Run tests — confirm they fail (models not defined yet)**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_models --verbosity=2
```

Expected: `ImportError` or `OperationalError`.

- [ ] **Step 3: Add new models to `backend/hub/models/recommendations.py`**

Full file after this step:

```python
from django.contrib.auth.models import User
from django.db import models
from pgvector.django import VectorField

from .content import Course


class CourseEmbedding(models.Model):
    course      = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='embedding')
    embedding   = VectorField(dimensions=384)
    computed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Embedding for {self.course.title}'


class CourseRecommendation(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='recommendations')
    score       = models.FloatField()
    reason      = models.CharField(max_length=200)
    source      = models.CharField(max_length=20, default='personal')
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-score']

    def __str__(self):
        return f'{self.user.username} → {self.course.title} ({self.score:.2f})'


class CourseView(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_views')
    course     = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_views')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} viewed {self.course.title}'


class RecommendationEvent(models.Model):
    class EventType(models.TextChoices):
        SHOWN     = 'shown',     'Shown'
        CLICKED   = 'clicked',   'Clicked'
        ENROLLED  = 'enrolled',  'Enrolled'
        COMPLETED = 'completed', 'Completed'

    user             = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recommendation_events',
    )
    course           = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='recommendation_events',
    )
    event_type       = models.CharField(max_length=20, choices=EventType.choices)
    rank             = models.PositiveSmallIntegerField(default=0)
    source           = models.CharField(max_length=20)
    weights_snapshot = models.JSONField(default=dict)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} {self.event_type} {self.course.title}'


class RecommendationConfig(models.Model):
    # Signal ③ weights
    w_completed = models.FloatField(default=1.0)
    w_deep      = models.FloatField(default=0.7)
    w_active    = models.FloatField(default=0.4)
    w_enrolled  = models.FloatField(default=0.2)
    w_abandoned = models.FloatField(default=-0.1)
    w_lesson    = models.FloatField(default=0.03)
    w_view      = models.FloatField(default=0.1)
    # Blend weights
    alpha       = models.FloatField(default=0.3)
    beta        = models.FloatField(default=0.5)
    gamma       = models.FloatField(default=0.2)
    style_boost = models.FloatField(default=1.2)
    # Bandit config
    bandit_active   = models.BooleanField(default=False)
    n_min           = models.IntegerField(default=200)
    n_full          = models.IntegerField(default=1000)
    learning_rate   = models.FloatField(default=0.01)
    reward_click    = models.FloatField(default=0.3)
    reward_enroll   = models.FloatField(default=0.5)
    reward_complete = models.FloatField(default=1.0)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'RecommendationConfig (α={self.alpha}, β={self.beta}, γ={self.gamma})'
```

- [ ] **Step 4: Run tests — should fail only on OperationalError (tables not yet created)**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_models --verbosity=2
```

Expected: `OperationalError: no such table`.

- [ ] **Step 5: Commit**

```bash
git add backend/hub/models/recommendations.py backend/hub/tests/test_phase2_models.py
git commit -m "feat: add RecommendationConfig, RecommendationEvent, CourseView models"
```

---

## Task 3: Migrations and model exports

**Files:**
- Modify: `backend/hub/models/__init__.py`
- Generate: `backend/hub/migrations/0013_phase2_recommendations.py` (auto-generated)

- [ ] **Step 1: Update `backend/hub/models/__init__.py`** to export all new models

```python
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
    'Lesson',
    'LearningPath',
    'LearningPathCourse',
    'LearningPillar',
    'LessonProgress',
    'Module',
    'RecommendationConfig',
    'RecommendationEvent',
    'UserLearningPath',
    'UserProfile',
]
```

- [ ] **Step 2: Generate the migration**

```bash
cd backend
.venv/Scripts/uv.exe run manage.py makemigrations hub --name phase2_recommendations
```

Expected output: `Migrations for 'hub': hub/migrations/0013_phase2_recommendations.py`

- [ ] **Step 3: Apply the migration**

```bash
.venv/Scripts/uv.exe run manage.py migrate
```

Expected output ends with: `Applying hub.0013_phase2_recommendations... OK`

- [ ] **Step 4: Run all tests to confirm they pass**

```bash
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_models --verbosity=2
```

Expected: All tests pass (no errors).

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
.venv/Scripts/uv.exe run coverage run manage.py test hub --verbosity=2
```

Expected: All previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/hub/models/__init__.py backend/hub/migrations/0013_phase2_recommendations.py
git commit -m "feat: add migration for phase2 recommendation models"
```

---

## Task 4: Rewrite `compute_user_recommendations` — four-signal personal engine

**Files:**
- Modify: `backend/hub/tasks.py`
- Test: `backend/hub/tests/test_phase2_tasks.py` (create new)

The rewritten task combines:
- Signal ①: profile text → embedding (existing logic, kept)
- Signal ②: `preferred_pillars` → mean embedding of pillar's published courses
- Signal ③: behavioural history → weighted sum of course embeddings with recency decay
- ε-greedy: when `bandit_active=True` and events < `n_full`, randomly perturbs weights 10% of the time
- Competency filter + style boost remain as before
- At completion, fires `compute_cf_recommendations.delay(user_id)`

- [ ] **Step 1: Write the failing test**

Create `backend/hub/tests/test_phase2_tasks.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import Course, LearningPillar, UserProfile
from hub.models.recommendations import CourseRecommendation
from hub.tasks import compute_user_recommendations


class ComputeUserRecommendationsSQLiteTest(TestCase):
    """Tasks exit early on SQLite — verify no crash and no writes."""

    def setUp(self):
        self.user = User.objects.create_user(username='trec', password='pass')
        UserProfile.objects.create(
            user=self.user,
            user_type=UserProfile.UserType.TEACHER,
            onboarding_completed=True,
            subject_area='stem',
            teaching_level='secondary',
            competency_score=3,
        )

    def test_no_crash_on_sqlite(self):
        compute_user_recommendations(self.user.id)

    def test_no_recommendations_written_on_sqlite(self):
        compute_user_recommendations(self.user.id)
        self.assertEqual(
            CourseRecommendation.objects.filter(user=self.user).count(), 0
        )
```

- [ ] **Step 2: Run test — confirm it passes (task already exits early on SQLite)**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_tasks --verbosity=2
```

Expected: PASS (current task already returns early for non-postgres).

- [ ] **Step 3: Rewrite `backend/hub/tasks.py` with the four-signal engine**

Full file:

```python
import math
import random

from celery import shared_task


@shared_task
def compute_course_embeddings(course_id: int) -> None:
    from django.db import connection

    if connection.vendor != 'postgresql':
        return

    from sentence_transformers import SentenceTransformer

    from hub.models import Course
    from hub.models.recommendations import CourseEmbedding

    course = Course.objects.get(pk=course_id)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    text = f"{course.title} {course.description}"
    embedding = model.encode(text).tolist()
    CourseEmbedding.objects.update_or_create(
        course=course,
        defaults={'embedding': embedding},
    )


@shared_task
def compute_user_recommendations(user_id: int) -> None:
    from django.db import connection

    if connection.vendor != 'postgresql':
        return

    import numpy as np
    from django.contrib.auth.models import User
    from django.db.models import Count
    from django.utils import timezone
    from pgvector.django import CosineDistance
    from sentence_transformers import SentenceTransformer

    from hub.models.enrollment import Enrollment, LessonProgress
    from hub.models.recommendations import (
        CourseEmbedding,
        CourseRecommendation,
        CourseView,
        RecommendationConfig,
        RecommendationEvent,
    )

    config = RecommendationConfig.get()
    model = SentenceTransformer('all-MiniLM-L6-v2')
    now = timezone.now()

    user = User.objects.select_related('profile').get(pk=user_id)
    profile = user.profile

    # ── ε-greedy weight selection ─────────────────────────────────────────
    event_count = RecommendationEvent.objects.filter(source='personal').count()
    if config.bandit_active and config.n_min <= event_count < config.n_full:
        span = max(1, config.n_full - config.n_min)
        epsilon = 0.1 * max(0.0, 1.0 - (event_count - config.n_min) / span)
        if random.random() < epsilon:
            alpha = max(0.0, config.alpha + random.uniform(-0.05, 0.05))
            beta  = max(0.0, config.beta  + random.uniform(-0.05, 0.05))
            gamma = max(0.0, config.gamma + random.uniform(-0.05, 0.05))
            total = alpha + beta + gamma or 1.0
            alpha, beta, gamma = alpha / total, beta / total, gamma / total
        else:
            alpha, beta, gamma = config.alpha, config.beta, config.gamma
    else:
        alpha, beta, gamma = config.alpha, config.beta, config.gamma

    # ── Signal ①: Profile vector ──────────────────────────────────────────
    goals_str = ', '.join(profile.goals) if profile.goals else 'general'
    subject   = profile.get_subject_area_display() if profile.subject_area else 'general'
    level_str = profile.get_teaching_level_display() if profile.teaching_level else 'unknown'
    profile_text = (
        f"{subject} teacher, {level_str}, "
        f"competency {profile.competency_score}/6, goals: {goals_str}"
    )
    profile_vec = model.encode(profile_text)

    # ── Signal ②: Pillar bias vector ──────────────────────────────────────
    pillar_vec = None
    if profile.preferred_pillars:
        raw_embeddings = list(
            CourseEmbedding.objects
            .filter(
                course__pillar__slug__in=profile.preferred_pillars,
                course__is_published=True,
            )
            .values_list('embedding', flat=True)
        )
        if raw_embeddings:
            arr = np.array(raw_embeddings, dtype=np.float32)
            mean_vec = arr.mean(axis=0)
            norm = np.linalg.norm(mean_vec)
            if norm > 0:
                pillar_vec = mean_vec / norm

    # ── Signal ③: Behavioural vector ─────────────────────────────────────
    enrollments = list(Enrollment.objects.filter(user=user).select_related('course'))
    enrolled_ids = {e.course_id for e in enrollments}

    lesson_counts: dict[int, int] = {}
    if enrolled_ids:
        rows = (
            LessonProgress.objects
            .filter(user=user, lesson__module__course_id__in=enrolled_ids)
            .values('lesson__module__course_id')
            .annotate(n=Count('id'))
        )
        lesson_counts = {r['lesson__module__course_id']: r['n'] for r in rows}

    view_counts: dict[int, int] = {}
    rows = (
        CourseView.objects
        .filter(user=user)
        .values('course_id')
        .annotate(n=Count('id'))
    )
    view_counts = {r['course_id']: r['n'] for r in rows}

    weighted_vecs = []
    seen_course_ids: set[int] = set()

    for enr in enrollments:
        days_idle = max(0, (now - enr.last_accessed_at).days)
        decay = math.exp(-days_idle / 30.0)
        p = enr.progress_pct
        if p == 100:
            base = config.w_completed
        elif p >= 50:
            base = config.w_deep
        elif p >= 10:
            base = config.w_active
        elif days_idle <= 7:
            base = config.w_enrolled
        else:
            base = config.w_abandoned

        lesson_bonus = lesson_counts.get(enr.course_id, 0) * config.w_lesson
        score = min(max(base + lesson_bonus, -0.2), 1.0) * decay

        try:
            emb = CourseEmbedding.objects.get(course=enr.course)
        except CourseEmbedding.DoesNotExist:
            continue

        weighted_vecs.append(score * np.array(emb.embedding, dtype=np.float32))
        seen_course_ids.add(enr.course_id)

    for course_id, n in view_counts.items():
        if course_id in seen_course_ids:
            continue
        view_score = min(max(n * config.w_view, -0.2), 1.0)
        try:
            emb = CourseEmbedding.objects.get(course_id=course_id)
        except CourseEmbedding.DoesNotExist:
            continue
        weighted_vecs.append(view_score * np.array(emb.embedding, dtype=np.float32))

    behaviour_vec = None
    if weighted_vecs:
        raw = np.sum(weighted_vecs, axis=0)
        norm = np.linalg.norm(raw)
        if norm > 0:
            behaviour_vec = raw / norm

    # ── Combine signals ───────────────────────────────────────────────────
    user_vec = alpha * profile_vec
    if behaviour_vec is not None:
        user_vec = user_vec + beta * behaviour_vec
    if pillar_vec is not None:
        user_vec = user_vec + gamma * pillar_vec

    norm = np.linalg.norm(user_vec)
    user_vec_list = (user_vec / norm).tolist() if norm > 0 else profile_vec.tolist()

    # ── Score and filter candidates ───────────────────────────────────────
    score_val = profile.competency_score
    level_num = 0 if score_val <= 2 else (1 if score_val <= 4 else 2)
    course_level_nums = {'beginner': 0, 'intermediate': 1, 'advanced': 2}

    candidates = (
        CourseEmbedding.objects
        .select_related('course__pillar')
        .exclude(course_id__in=enrolled_ids)
        .filter(course__is_published=True)
        .annotate(distance=CosineDistance('embedding', user_vec_list))
        .order_by('distance')[:20]
    )

    filtered = []
    for emb in candidates:
        if course_level_nums.get(emb.course.level, 0) > level_num + 1:
            continue
        similarity = max(0.0, 1.0 - float(emb.distance))
        if profile.learning_style and emb.course.content_format == profile.learning_style:
            similarity *= config.style_boost
        filtered.append((emb.course, similarity))
        if len(filtered) >= 5:
            break

    # ── Write personal recommendations ───────────────────────────────────
    CourseRecommendation.objects.filter(user=user, source='personal').delete()

    subject_display = profile.get_subject_area_display() if profile.subject_area else 'general'
    level_name = ('beginner', 'intermediate', 'advanced')[level_num]
    for course, similarity in filtered:
        CourseRecommendation.objects.create(
            user=user,
            course=course,
            score=similarity,
            reason=f"Matches your {level_name} level and {subject_display} focus",
            source='personal',
        )

    # ── Trigger CF task ───────────────────────────────────────────────────
    compute_cf_recommendations.delay(user_id)


@shared_task
def compute_cf_recommendations(user_id: int) -> None:
    from django.db import connection

    if connection.vendor != 'postgresql':
        return

    from django.contrib.auth.models import User
    from django.db.models import Count

    from hub.models.enrollment import Enrollment
    from hub.models.recommendations import CourseRecommendation
    from hub.models.user import UserProfile

    user = User.objects.select_related('profile').get(pk=user_id)
    profile = user.profile

    score = profile.competency_score
    if score <= 2:
        band_filter = {'competency_score__lte': 2}
    elif score <= 4:
        band_filter = {'competency_score__gte': 3, 'competency_score__lte': 4}
    else:
        band_filter = {'competency_score__gte': 5}

    peer_ids = list(
        UserProfile.objects
        .filter(
            subject_area=profile.subject_area,
            teaching_level=profile.teaching_level,
            onboarding_completed=True,
            **band_filter,
        )
        .exclude(user=user)
        .values_list('user_id', flat=True)
    )
    group_size = len(peer_ids)
    if group_size == 0:
        return

    enrolled_ids = set(
        Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
    )
    personal_ids = set(
        CourseRecommendation.objects
        .filter(user=user, source='personal')
        .values_list('course_id', flat=True)
    )
    exclude_ids = enrolled_ids | personal_ids

    top_courses = (
        Enrollment.objects
        .filter(user_id__in=peer_ids, course__is_published=True)
        .exclude(course_id__in=exclude_ids)
        .values('course_id')
        .annotate(n=Count('user_id', distinct=True))
        .order_by('-n')[:3]
    )

    CourseRecommendation.objects.filter(user=user, source='cf').delete()

    subject_display = profile.get_subject_area_display() if profile.subject_area else 'teachers'
    for item in top_courses:
        pct = round(item['n'] / group_size * 100)
        CourseRecommendation.objects.create(
            user=user,
            course_id=item['course_id'],
            score=item['n'] / group_size,
            reason=f"{pct}% of {subject_display} teachers also enrolled",
            source='cf',
        )


@shared_task
def tune_recommendation_weights() -> None:
    from django.db import connection

    if connection.vendor != 'postgresql':
        return

    from collections import defaultdict
    from datetime import timedelta

    from django.utils import timezone

    from hub.models.recommendations import RecommendationConfig, RecommendationEvent

    config = RecommendationConfig.get()
    event_count = RecommendationEvent.objects.filter(source='personal').count()

    if event_count < config.n_min:
        if config.bandit_active:
            config.bandit_active = False
            config.save()
        return

    if not config.bandit_active:
        config.bandit_active = True
        config.save()

    if event_count < config.n_full:
        return

    # Phase 3: gradient update using last 30 days of personal events
    cutoff = timezone.now() - timedelta(days=30)
    reward_map = {
        'clicked':   config.reward_click,
        'enrolled':  config.reward_enroll,
        'completed': config.reward_complete,
        'shown':     0.0,
    }

    events = list(
        RecommendationEvent.objects
        .filter(source='personal', created_at__gte=cutoff)
        .exclude(weights_snapshot={})
        .values('weights_snapshot', 'event_type')
    )
    if not events:
        return

    snapshot_rewards: dict[tuple, list] = defaultdict(list)
    for event in events:
        snap = event['weights_snapshot']
        key = (
            snap.get('alpha', config.alpha),
            snap.get('beta',  config.beta),
            snap.get('gamma', config.gamma),
        )
        snapshot_rewards[key].append(reward_map.get(event['event_type'], 0.0))

    best_key = max(
        snapshot_rewards,
        key=lambda k: sum(snapshot_rewards[k]) / len(snapshot_rewards[k]),
    )
    best_alpha, best_beta, best_gamma = best_key

    lr = config.learning_rate
    config.alpha = config.alpha + lr * (best_alpha - config.alpha)
    config.beta  = config.beta  + lr * (best_beta  - config.beta)
    config.gamma = config.gamma + lr * (best_gamma - config.gamma)
    config.save()


@shared_task
def recompute_all_recommendations() -> None:
    from django.contrib.auth.models import User

    user_ids = list(
        User.objects.filter(
            profile__onboarding_completed=True,
        ).values_list('id', flat=True)
    )
    for uid in user_ids:
        compute_user_recommendations.delay(uid)
```

Note: `compute_cf_recommendations` is defined in the same file and called at the end of `compute_user_recommendations`. The `recompute_all_recommendations` only calls `compute_user_recommendations` — CF is chained automatically.

- [ ] **Step 4: Run tests — confirm still passing**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_tasks --verbosity=2
```

Expected: All pass (SQLite guard still returns early).

- [ ] **Step 5: Run full test suite**

```bash
.venv/Scripts/uv.exe run coverage run manage.py test hub --verbosity=2
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/hub/tasks.py backend/hub/tests/test_phase2_tasks.py
git commit -m "feat: rewrite compute_user_recommendations with 4-signal engine + add CF + bandit tasks"
```

---

## Task 5: Update celery-beat schedule and Django admin

**Files:**
- Modify: `backend/aidea/settings.py`
- Modify: `backend/hub/admin.py`

- [ ] **Step 1: Add `tune_recommendation_weights` to beat schedule in `backend/aidea/settings.py`**

Find `CELERY_BEAT_SCHEDULE` (around line 120) and add the new entry:

```python
CELERY_BEAT_SCHEDULE = {
    'recompute-all-recommendations-nightly': {
        'task': 'hub.tasks.recompute_all_recommendations',
        'schedule': crontab(hour=2, minute=0),
    },
    'tune-recommendation-weights-nightly': {
        'task': 'hub.tasks.tune_recommendation_weights',
        'schedule': crontab(hour=3, minute=0),
    },
}
```

- [ ] **Step 2: Add `content_format` to `CourseAdmin` in `backend/hub/admin.py`**

In the existing `CourseAdmin`, update `list_display`:

```python
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'pillar', 'level', 'content_format', 'is_published']
    list_filter = ['pillar', 'is_published', 'content_format']
    search_fields = ['title']
    inlines = [ModuleInline]
```

- [ ] **Step 3: Register new models in `backend/hub/admin.py`**

Add to the imports at the top:

```python
from .models import (
    Course,
    CourseEditHistory,
    Enrollment,
    LearningPillar,
    Lesson,
    LessonProgress,
    Module,
    UserProfile,
)
from .models.recommendations import CourseView, RecommendationConfig, RecommendationEvent
```

Append these three admin registrations at the end of `admin.py`:

```python
@admin.register(RecommendationConfig)
class RecommendationConfigAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Signal weights', {
            'fields': ['w_completed', 'w_deep', 'w_active', 'w_enrolled', 'w_abandoned', 'w_lesson', 'w_view'],
        }),
        ('Blend weights', {
            'fields': ['alpha', 'beta', 'gamma', 'style_boost'],
        }),
        ('Bandit config', {
            'fields': ['bandit_active', 'n_min', 'n_full', 'learning_rate',
                       'reward_click', 'reward_enroll', 'reward_complete'],
        }),
    ]

    def has_add_permission(self, request):
        return not RecommendationConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RecommendationEvent)
class RecommendationEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'event_type', 'source', 'rank', 'created_at']
    list_filter = ['event_type', 'source']
    search_fields = ['user__username', 'course__title']
    readonly_fields = ['user', 'course', 'event_type', 'rank', 'source', 'weights_snapshot', 'created_at']
    ordering = ['-created_at']


@admin.register(CourseView)
class CourseViewAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'created_at']
    list_filter = ['course__pillar']
    search_fields = ['user__username', 'course__title']
    readonly_fields = ['user', 'course', 'created_at']
    ordering = ['-created_at']
```

- [ ] **Step 4: Run full test suite to confirm no regressions**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub --verbosity=2
```

Expected: All tests pass.

- [ ] **Step 5: Verify admin loads without errors**

```bash
.venv/Scripts/uv.exe run manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 6: Commit**

```bash
git add backend/aidea/settings.py backend/hub/admin.py
git commit -m "feat: add tune_recommendation_weights to beat schedule + admin for new models"
```

---

## Task 6: Recommendations API — source field + events endpoint

**Files:**
- Modify: `backend/hub/serializers/pathway.py`
- Modify: `backend/hub/views/recommendations.py`
- Create: `backend/hub/serializers/recommendations.py`
- Test: add to `backend/hub/tests/test_recommendations.py`

- [ ] **Step 1: Write failing tests — append to `backend/hub/tests/test_recommendations.py`**

Add at the bottom of the existing file (the `make_teacher` helper is already defined there):

```python
from hub.models.recommendations import RecommendationEvent


class RecommendationSourceFieldTest(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_source_personal_in_response(self):
        pillar = LearningPillar.objects.create(name='SP', slug='sp', description='')
        course = Course.objects.create(
            title='Source Test', pillar=pillar, level='beginner', is_published=True,
        )
        CourseRecommendation.objects.create(
            user=self.user, course=course, score=0.9, reason='test', source='personal',
        )
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['source'], 'personal')

    def test_source_cf_in_response(self):
        pillar = LearningPillar.objects.create(name='CF', slug='cf', description='')
        course = Course.objects.create(
            title='CF Test', pillar=pillar, level='beginner', is_published=True,
        )
        CourseRecommendation.objects.create(
            user=self.user, course=course, score=0.6, reason='67% of STEM', source='cf',
        )
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['source'], 'cf')


class RecommendationEventAPITest(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        pillar = LearningPillar.objects.create(name='EV', slug='ev', description='')
        self.course = Course.objects.create(
            title='Event Course', pillar=pillar, level='beginner', is_published=True,
        )

    def test_shown_event_created(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'shown',
            'rank': 1,
            'source': 'personal',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RecommendationEvent.objects.count(), 1)
        ev = RecommendationEvent.objects.first()
        self.assertEqual(ev.event_type, 'shown')
        self.assertEqual(ev.source, 'personal')
        self.assertIn('alpha', ev.weights_snapshot)

    def test_clicked_event_created(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'clicked',
            'rank': 2,
            'source': 'cf',
        })
        self.assertEqual(response.status_code, 201)
        ev = RecommendationEvent.objects.first()
        self.assertEqual(ev.rank, 2)

    def test_invalid_event_type_rejected(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'unknown_type',
            'rank': 1,
            'source': 'personal',
        })
        self.assertEqual(response.status_code, 400)

    def test_invalid_source_rejected(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'shown',
            'rank': 1,
            'source': 'invalid',
        })
        self.assertEqual(response.status_code, 400)

    def test_content_creator_gets_403(self):
        from hub.models import UserProfile as UP
        creator = User.objects.create_user(username='creator2', password='pass')
        UP.objects.create(user=creator, user_type=UP.UserType.CONTENT_CREATOR)
        login = self.client.post(reverse('auth-login'), {'username': 'creator2', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id, 'event_type': 'shown', 'rank': 1, 'source': 'personal',
        })
        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run tests — confirm they fail (URL name `recommendation-event` not yet defined)**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_recommendations --verbosity=2
```

Expected: `NoReverseMatch` for `recommendation-event`.

- [ ] **Step 3: Add `source` to `RecommendationSerializer` in `backend/hub/serializers/pathway.py`**

Add `source` to both the field list and `Meta.fields`:

```python
class RecommendationSerializer(serializers.ModelSerializer):
    course_id      = serializers.IntegerField(source='course.id')
    title          = serializers.CharField(source='course.title')
    pillar_name    = serializers.CharField(source='course.pillar.name')
    level          = serializers.CharField(source='course.level')
    duration_hours = serializers.IntegerField(source='course.duration_hours')

    class Meta:
        model  = CourseRecommendation
        fields = ['course_id', 'title', 'pillar_name', 'level', 'duration_hours', 'score', 'reason', 'source']
```

- [ ] **Step 4: Create `backend/hub/serializers/recommendations.py`**

```python
from rest_framework import serializers

from hub.models.recommendations import RecommendationEvent


class RecommendationEventSerializer(serializers.Serializer):
    course_id  = serializers.IntegerField()
    event_type = serializers.ChoiceField(choices=RecommendationEvent.EventType.choices)
    rank       = serializers.IntegerField(min_value=0, max_value=20)
    source     = serializers.ChoiceField(choices=['personal', 'cf'])
```

- [ ] **Step 5: Rewrite `backend/hub/views/recommendations.py`** to add `RecommendationEventView`

```python
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models.recommendations import CourseRecommendation, RecommendationConfig, RecommendationEvent
from hub.serializers.pathway import RecommendationSerializer
from hub.views.permissions import IsTeacher


class RecommendationsView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        recs = (
            CourseRecommendation.objects
            .filter(user=request.user)
            .select_related('course__pillar')
            .order_by('-score')
        )
        return Response(RecommendationSerializer(recs, many=True).data)


class RecommendationEventView(APIView):
    permission_classes = [IsTeacher]

    def post(self, request):
        from hub.serializers.recommendations import RecommendationEventSerializer

        serializer = RecommendationEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        config = RecommendationConfig.get()
        weights_snapshot = {
            'alpha':         config.alpha,
            'beta':          config.beta,
            'gamma':         config.gamma,
            'style_boost':   config.style_boost,
            'bandit_active': config.bandit_active,
        }

        RecommendationEvent.objects.create(
            user=request.user,
            course_id=d['course_id'],
            event_type=d['event_type'],
            rank=d['rank'],
            source=d['source'],
            weights_snapshot=weights_snapshot,
        )
        return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)
```

- [ ] **Step 6: Add URL + export**

In `backend/hub/urls.py`, add after the `recommendations/` line:

```python
path('recommendations/events/', RecommendationEventView.as_view(), name='recommendation-event'),
```

In `backend/hub/views/__init__.py`, add to imports and `__all__`:

```python
from .recommendations import RecommendationEventView, RecommendationsView
```

And add `'RecommendationEventView'` to `__all__`.

In `backend/hub/urls.py` imports, add `RecommendationEventView`.

- [ ] **Step 7: Run tests — all should pass**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_recommendations --verbosity=2
```

Expected: All pass.

- [ ] **Step 8: Run full test suite**

```bash
.venv/Scripts/uv.exe run coverage run manage.py test hub --verbosity=2
```

Expected: All pass.

- [ ] **Step 9: Commit**

```bash
git add backend/hub/serializers/pathway.py backend/hub/serializers/recommendations.py \
        backend/hub/views/recommendations.py backend/hub/views/__init__.py \
        backend/hub/urls.py backend/hub/tests/test_recommendations.py
git commit -m "feat: add source field to recommendations + recommendation events endpoint"
```

---

## Task 7: Profile preferences API — GET + PATCH /api/profile/preferences/

**Files:**
- Create: `backend/hub/serializers/profile.py`
- Create: `backend/hub/views/profile.py`
- Modify: `backend/hub/serializers/auth.py`
- Modify: `backend/hub/urls.py`
- Modify: `backend/hub/views/__init__.py`
- Test: `backend/hub/tests/test_phase2_profile.py` (create new)

- [ ] **Step 1: Write failing tests**

Create `backend/hub/tests/test_phase2_profile.py`:

```python
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import UserProfile


def make_teacher(username='pref_teacher'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
    return user


class ProfilePreferencesGetTest(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'pref_teacher', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_get_returns_empty_defaults(self):
        response = self.client.get(reverse('profile-preferences'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['preferred_pillars'], [])
        self.assertEqual(response.data['learning_style'], '')


class ProfilePreferencesPatchTest(APITestCase):
    def setUp(self):
        self.user = make_teacher('pref_teacher2')
        login = self.client.post(reverse('auth-login'), {'username': 'pref_teacher2', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_patch_preferred_pillars(self):
        response = self.client.patch(
            reverse('profile-preferences'),
            {'preferred_pillars': ['teach-with-ai', 'teach-about-ai']},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.preferred_pillars, ['teach-with-ai', 'teach-about-ai'])

    def test_patch_learning_style(self):
        response = self.client.patch(
            reverse('profile-preferences'),
            {'learning_style': 'video'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.learning_style, 'video')

    def test_patch_both_fields(self):
        response = self.client.patch(
            reverse('profile-preferences'),
            {'preferred_pillars': ['teach-for-ai'], 'learning_style': 'text'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.preferred_pillars, ['teach-for-ai'])
        self.assertEqual(self.user.profile.learning_style, 'text')

    def test_invalid_pillar_rejected(self):
        response = self.client.patch(
            reverse('profile-preferences'),
            {'preferred_pillars': ['not-a-real-pillar']},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_learning_style_rejected(self):
        response = self.client.patch(
            reverse('profile-preferences'),
            {'learning_style': 'podcast'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_content_creator_gets_403(self):
        creator = User.objects.create_user(username='prof_creator', password='pass')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        login = self.client.post(reverse('auth-login'), {'username': 'prof_creator', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.get(reverse('profile-preferences'))
        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run tests — confirm they fail (`profile-preferences` URL not found)**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_profile --verbosity=2
```

Expected: `NoReverseMatch` for `profile-preferences`.

- [ ] **Step 3: Create `backend/hub/serializers/profile.py`**

```python
from rest_framework import serializers

from hub.models import UserProfile

_VALID_PILLARS = ['teach-with-ai', 'teach-for-ai', 'teach-about-ai']
_VALID_STYLES  = [c[0] for c in UserProfile.LearningStyle.choices]


class ProfilePreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserProfile
        fields = ['preferred_pillars', 'learning_style']

    def validate_preferred_pillars(self, value):
        for pillar in value:
            if pillar not in _VALID_PILLARS:
                raise serializers.ValidationError(
                    f"'{pillar}' is not a valid pillar. Choose from {_VALID_PILLARS}."
                )
        return value

    def validate_learning_style(self, value):
        if value and value not in _VALID_STYLES:
            raise serializers.ValidationError(
                f"'{value}' is not a valid learning style. Choose from {_VALID_STYLES}."
            )
        return value
```

- [ ] **Step 4: Create `backend/hub/views/profile.py`**

```python
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.serializers.profile import ProfilePreferencesSerializer
from hub.views.permissions import IsTeacher


class ProfilePreferencesView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        serializer = ProfilePreferencesSerializer(request.user.profile)
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfilePreferencesSerializer(
            request.user.profile, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        from hub.tasks import compute_user_recommendations
        compute_user_recommendations.delay(request.user.id)

        return Response(serializer.data)
```

- [ ] **Step 5: Add `preferred_pillars` and `learning_style` to `UserProfileSerializer` in `backend/hub/serializers/auth.py`**

```python
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserProfile
        fields = ['user_type', 'avatar_initials', 'onboarding_completed',
                  'preferred_pillars', 'learning_style']
```

- [ ] **Step 6: Add URL pattern and exports**

In `backend/hub/urls.py`, add:

```python
path('profile/preferences/', ProfilePreferencesView.as_view(), name='profile-preferences'),
```

In `backend/hub/views/__init__.py`, add to imports:

```python
from .profile import ProfilePreferencesView
```

And add `'ProfilePreferencesView'` to `__all__`.

In `backend/hub/urls.py` imports, add `ProfilePreferencesView`.

- [ ] **Step 7: Run tests — all should pass**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_profile --verbosity=2
```

Expected: All pass.

- [ ] **Step 8: Run full test suite**

```bash
.venv/Scripts/uv.exe run coverage run manage.py test hub --verbosity=2
```

Expected: All pass.

- [ ] **Step 9: Commit**

```bash
git add backend/hub/serializers/profile.py backend/hub/views/profile.py \
        backend/hub/serializers/auth.py backend/hub/urls.py \
        backend/hub/views/__init__.py backend/hub/tests/test_phase2_profile.py
git commit -m "feat: add profile preferences GET/PATCH endpoint"
```

---

## Task 8: CourseView logging + auto-enrolled events

**Files:**
- Modify: `backend/hub/views/learner.py`
- Test: `backend/hub/tests/test_phase2_courseview.py` (create new)

- [ ] **Step 1: Write failing tests**

Create `backend/hub/tests/test_phase2_courseview.py`:

```python
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, Enrollment, LearningPillar, UserProfile
from hub.models.recommendations import CourseRecommendation, CourseView, RecommendationEvent


def make_teacher(username='cv_teacher'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
    return user


class CourseViewLoggingTest(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'cv_teacher', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        pillar = LearningPillar.objects.create(name='CVP', slug='cvp', description='')
        self.course = Course.objects.create(
            title='CV Course', pillar=pillar, level='beginner', is_published=True,
        )

    def test_view_logged_on_course_detail_request(self):
        self.client.get(reverse('course-detail', kwargs={'pk': self.course.pk}))
        self.assertEqual(
            CourseView.objects.filter(user=self.user, course=self.course).count(), 1,
        )

    def test_each_visit_logged_separately(self):
        self.client.get(reverse('course-detail', kwargs={'pk': self.course.pk}))
        self.client.get(reverse('course-detail', kwargs={'pk': self.course.pk}))
        self.assertEqual(
            CourseView.objects.filter(user=self.user, course=self.course).count(), 2,
        )

    def test_view_not_logged_for_nonexistent_course(self):
        self.client.get(reverse('course-detail', kwargs={'pk': 99999}))
        self.assertEqual(CourseView.objects.count(), 0)


class EnrolledEventAutoFireTest(APITestCase):
    def setUp(self):
        self.user = make_teacher('enroll_ev_teacher')
        login = self.client.post(reverse('auth-login'), {'username': 'enroll_ev_teacher', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        pillar = LearningPillar.objects.create(name='EEP', slug='eep', description='')
        self.course = Course.objects.create(
            title='Enroll Event', pillar=pillar, level='beginner', is_published=True,
        )

    def test_enrolled_event_fired_when_recommendation_exists(self):
        CourseRecommendation.objects.create(
            user=self.user, course=self.course, score=0.9, reason='test', source='personal',
        )
        self.client.post(reverse('course-enroll', kwargs={'pk': self.course.pk}))
        self.assertEqual(
            RecommendationEvent.objects.filter(
                user=self.user, course=self.course, event_type='enrolled',
            ).count(),
            1,
        )

    def test_no_event_when_no_recommendation(self):
        self.client.post(reverse('course-enroll', kwargs={'pk': self.course.pk}))
        self.assertEqual(RecommendationEvent.objects.count(), 0)

    def test_no_duplicate_event_on_re_enroll(self):
        CourseRecommendation.objects.create(
            user=self.user, course=self.course, score=0.9, reason='test', source='personal',
        )
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.post(reverse('course-enroll', kwargs={'pk': self.course.pk}))
        self.assertEqual(RecommendationEvent.objects.count(), 0)
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_courseview --verbosity=2
```

Expected: AssertionError — CourseView count is 0 (logging not yet added).

- [ ] **Step 3: Modify `CourseDetailView` in `backend/hub/views/learner.py`**

Replace the existing `CourseDetailView.get` method body so it logs a CourseView after finding the course:

```python
class CourseDetailView(APIView):
    def get(self, request, pk):
        try:
            course = Course.objects.prefetch_related('modules').select_related('pillar').get(
                pk=pk, is_published=True,
            )
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            from hub.models.recommendations import CourseView
            CourseView.objects.create(user=request.user, course=course)

        serializer = CourseDetailSerializer(course, context={'request': request})
        return Response(serializer.data)
```

- [ ] **Step 4: Modify `CourseEnrollView` in `backend/hub/views/learner.py`** to fire enrolled event when a recommendation exists

Replace the existing `CourseEnrollView.post` method body:

```python
class CourseEnrollView(APIView):
    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk, is_published=True)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
        )

        if created:
            from hub.models.recommendations import (
                CourseRecommendation, RecommendationConfig, RecommendationEvent,
            )
            rec = CourseRecommendation.objects.filter(
                user=request.user, course=course,
            ).first()
            if rec:
                config = RecommendationConfig.get()
                RecommendationEvent.objects.create(
                    user=request.user,
                    course=course,
                    event_type=RecommendationEvent.EventType.ENROLLED,
                    rank=0,
                    source=rec.source,
                    weights_snapshot={
                        'alpha':         config.alpha,
                        'beta':          config.beta,
                        'gamma':         config.gamma,
                        'bandit_active': config.bandit_active,
                    },
                )

        return Response(
            {'enrolled': True, 'created': created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
```

- [ ] **Step 5: Run new tests**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.test_phase2_courseview --verbosity=2
```

Expected: All pass.

- [ ] **Step 6: Run full test suite**

```bash
.venv/Scripts/uv.exe run coverage run manage.py test hub --verbosity=2
```

Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add backend/hub/views/learner.py backend/hub/tests/test_phase2_courseview.py
git commit -m "feat: log CourseView on detail requests + auto-fire enrolled event on enroll"
```

---

## Task 9: Frontend ProfilePage with learning preferences

**Files:**
- Create: `frontend/src/pages/ProfilePage.jsx`
- Create: `frontend/src/pages/ProfilePage.css`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Create `frontend/src/pages/ProfilePage.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './ProfilePage.css'

const PILLARS = [
  { value: 'teach-with-ai',  label: 'Teach with AI' },
  { value: 'teach-for-ai',   label: 'Teach for AI' },
  { value: 'teach-about-ai', label: 'Teach about AI' },
]

const LEARNING_STYLES = [
  { value: 'video',       label: 'Video' },
  { value: 'text',        label: 'Text / Reading' },
  { value: 'visual',      label: 'Visual (slides, diagrams)' },
  { value: 'interactive', label: 'Interactive (quizzes, exercises)' },
]

export default function ProfilePage() {
  const { user } = useAuth()
  const [pillars, setPillars]   = useState([])
  const [style, setStyle]       = useState('')
  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState(false)
  const [saved, setSaved]       = useState(false)
  const [error, setError]       = useState('')

  useEffect(() => {
    client.get('/profile/preferences/')
      .then((res) => {
        setPillars(res.data.preferred_pillars ?? [])
        setStyle(res.data.learning_style ?? '')
      })
      .catch(() => setError('Failed to load preferences.'))
      .finally(() => setLoading(false))
  }, [])

  const togglePillar = (val) => {
    setSaved(false)
    setPillars((prev) =>
      prev.includes(val) ? prev.filter((p) => p !== val) : [...prev, val],
    )
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      await client.patch('/profile/preferences/', {
        preferred_pillars: pillars,
        learning_style: style,
      })
      setSaved(true)
    } catch {
      setError('Failed to save preferences.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="profile-page">
      <h1 className="profile-heading">Profile</h1>

      {user && (
        <div className="profile-identity">
          <div className="profile-avatar">{user.profile?.avatar_initials || '?'}</div>
          <div>
            <p className="profile-name">{user.first_name} {user.last_name}</p>
            <p className="profile-username">@{user.username}</p>
          </div>
        </div>
      )}

      <section className="prefs-section">
        <h2>Learning Preferences</h2>
        <p className="prefs-hint">
          These preferences personalise your &ldquo;Recommended for you&rdquo; course list.
        </p>

        {loading ? (
          <p className="prefs-loading">Loading…</p>
        ) : (
          <>
            <div className="prefs-group">
              <h3>AI Learning Pillars</h3>
              <p className="prefs-sub">Select the pillars you want to focus on.</p>
              {PILLARS.map(({ value, label }) => (
                <label key={value} className="prefs-checkbox-label">
                  <input
                    type="checkbox"
                    checked={pillars.includes(value)}
                    onChange={() => togglePillar(value)}
                  />
                  {label}
                </label>
              ))}
            </div>

            <div className="prefs-group">
              <h3>Preferred Learning Style</h3>
              <p className="prefs-sub">How do you learn best?</p>
              {LEARNING_STYLES.map(({ value, label }) => (
                <label key={value} className="prefs-radio-label">
                  <input
                    type="radio"
                    name="learning_style"
                    value={value}
                    checked={style === value}
                    onChange={() => { setSaved(false); setStyle(value) }}
                  />
                  {label}
                </label>
              ))}
            </div>

            {error && <p className="prefs-error">{error}</p>}
            {saved && <p className="prefs-success">Preferences saved! Your recommendations will update shortly.</p>}

            <button
              className="prefs-save-btn"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving…' : 'Save Preferences'}
            </button>
          </>
        )}
      </section>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/pages/ProfilePage.css`**

```css
.profile-page {
  max-width: 680px;
}

.profile-heading {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 1.5rem;
  color: var(--color-text);
}

.profile-identity {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin-bottom: 2rem;
}

.profile-avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.profile-name {
  font-weight: 600;
  margin: 0 0 0.2rem;
}

.profile-username {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin: 0;
}

.prefs-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
}

.prefs-section h2 {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0 0 0.4rem;
}

.prefs-hint {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  margin: 0 0 1.5rem;
}

.prefs-loading {
  color: var(--color-text-muted);
}

.prefs-group {
  margin-bottom: 1.5rem;
}

.prefs-group h3 {
  font-size: 0.9375rem;
  font-weight: 600;
  margin: 0 0 0.25rem;
}

.prefs-sub {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin: 0 0 0.75rem;
}

.prefs-checkbox-label,
.prefs-radio-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  padding: 0.35rem 0;
  cursor: pointer;
}

.prefs-error {
  color: var(--color-red, #dc2626);
  font-size: 0.875rem;
  margin: 0 0 0.75rem;
}

.prefs-success {
  color: #16a34a;
  font-size: 0.875rem;
  margin: 0 0 0.75rem;
}

.prefs-save-btn {
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  padding: 0.6rem 1.4rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.prefs-save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.prefs-save-btn:hover:not(:disabled) {
  opacity: 0.88;
}
```

- [ ] **Step 3: Update `frontend/src/App.jsx`** — replace the PlaceholderPage at `/profile` with ProfilePage

Add the import:

```jsx
import ProfilePage from './pages/ProfilePage'
```

Replace:

```jsx
<Route path="/profile" element={<PlaceholderPage title="Profile" />} />
```

with:

```jsx
<Route path="/profile" element={<ProfilePage />} />
```

- [ ] **Step 4: Build and verify**

```bash
cd frontend
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 5: Start dev server and manually verify**

```bash
npm run dev
```

Navigate to `http://localhost:5173/profile` (after logging in as `demo_teacher / demo1234`). Verify:
- Profile identity card shows initials, name, username
- Pillar checkboxes and learning style radio buttons render
- Selecting options and clicking "Save Preferences" shows success message
- Refreshing the page reloads the saved preferences via GET

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ProfilePage.jsx frontend/src/pages/ProfilePage.css frontend/src/App.jsx
git commit -m "feat: add ProfilePage with learning preferences section"
```

---

## Task 10: Frontend — CF row on HomePage + shown/clicked events

**Files:**
- Modify: `frontend/src/pages/HomePage.jsx`
- Modify: `frontend/src/pages/HomePage.css`

The personal row already renders from `recommendations` state (`source='personal'`). After this task:
1. `recommendations` state is split into `personalRecs` (source='personal') and `cfRecs` (source='cf')
2. "Teachers like you also took" row is shown below the personal row for CF recs
3. On mount: fire `shown` events for every visible rec card
4. On card link click: fire `clicked` event before navigating

- [ ] **Step 1: Update `frontend/src/pages/HomePage.jsx`**

Full file after changes:

```jsx
import { useCallback, useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import ContinueLearningBanner from '../components/ContinueLearningBanner'
import { useAuth } from '../context/AuthContext'
import './HomePage.css'

PillarCard.propTypes = {
  pillar: PropTypes.shape({
    name: PropTypes.string,
    description: PropTypes.string,
    progress_pct: PropTypes.number,
    course_count: PropTypes.number,
    slug: PropTypes.string,
  }),
}

function PillarCard({ pillar }) {
  return (
    <div className="pillar-card">
      <h3>{pillar.name}</h3>
      <p className="pillar-desc">{pillar.description}</p>
      <div className="pillar-progress">
        <span>Overall Progress</span>
        <span className="pillar-pct">{pillar.progress_pct}%</span>
      </div>
      <div className="progress-bar">
        <div className="progress-fill dark" style={{ width: `${pillar.progress_pct}%` }} />
      </div>
      <div className="pillar-footer">
        <span>{pillar.course_count} courses</span>
        <a href={`/courses?pillar=${pillar.slug}`}>View courses →</a>
      </div>
    </div>
  )
}

RecCard.propTypes = {
  rec: PropTypes.shape({
    course_id: PropTypes.number,
    title: PropTypes.string,
    pillar_name: PropTypes.string,
    reason: PropTypes.string,
    source: PropTypes.string,
  }),
  rank: PropTypes.number,
  onFireEvent: PropTypes.func,
}

function RecCard({ rec, rank, onFireEvent }) {
  const navigate = useNavigate()

  const handleClick = (e) => {
    e.preventDefault()
    onFireEvent('clicked', rec.course_id, rank, rec.source)
    navigate(`/courses/${rec.course_id}`, {
      state: { fromRec: true, recRank: rank, recSource: rec.source },
    })
  }

  return (
    <div className="rec-card">
      <span className="rec-pillar">{rec.pillar_name}</span>
      <h3 className="rec-title">{rec.title}</h3>
      <p className="rec-reason">{rec.reason}</p>
      <a href={`/courses/${rec.course_id}`} className="rec-link" onClick={handleClick}>
        Start course →
      </a>
    </div>
  )
}

CfRecCard.propTypes = {
  rec: PropTypes.shape({
    course_id: PropTypes.number,
    title: PropTypes.string,
    reason: PropTypes.string,
    source: PropTypes.string,
  }),
  rank: PropTypes.number,
  onFireEvent: PropTypes.func,
}

function CfRecCard({ rec, rank, onFireEvent }) {
  const navigate = useNavigate()

  const handleClick = (e) => {
    e.preventDefault()
    onFireEvent('clicked', rec.course_id, rank, rec.source)
    navigate(`/courses/${rec.course_id}`, {
      state: { fromRec: true, recRank: rank, recSource: rec.source },
    })
  }

  return (
    <div className="rec-card cf-card">
      <h3 className="rec-title">{rec.title}</h3>
      <p className="rec-reason cf-reason">{rec.reason}</p>
      <a href={`/courses/${rec.course_id}`} className="rec-link" onClick={handleClick}>
        View course →
      </a>
    </div>
  )
}

export default function HomePage() {
  const { user } = useAuth()
  const [data, setData]             = useState(null)
  const [error, setError]           = useState('')
  const [personalRecs, setPersonal] = useState([])
  const [cfRecs, setCf]             = useState([])
  const [recsLoading, setRecsLoading] = useState(false)

  useEffect(() => {
    client.get('/home/')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load dashboard.'))
  }, [])

  const fireEvent = useCallback((eventType, courseId, rank, source) => {
    client.post('/recommendations/events/', {
      course_id: courseId,
      event_type: eventType,
      rank,
      source,
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!user?.profile?.onboarding_completed) return
    let cancelled = false

    const fetchRecs = async () => {
      setRecsLoading(true)
      try {
        const res = await client.get('/recommendations/')
        if (cancelled) return
        const all = res.data
        const personal = all.filter((r) => r.source === 'personal')
        const cf       = all.filter((r) => r.source === 'cf')
        setPersonal(personal)
        setCf(cf)
        // Fire shown events
        personal.forEach((r, i) => fireEvent('shown', r.course_id, i + 1, 'personal'))
        cf.forEach((r, i)       => fireEvent('shown', r.course_id, i + 1, 'cf'))
      } catch {
        // silently ignore
      } finally {
        if (!cancelled) setRecsLoading(false)
      }
    }

    fetchRecs()
    return () => { cancelled = true }
  }, [user, fireEvent])

  if (error) return <p className="page-error">{error}</p>
  if (!data)  return <p className="page-loading">Loading…</p>

  const showRecs = user?.profile?.onboarding_completed

  return (
    <div className="home-page">
      <ContinueLearningBanner data={data.continue_learning} />

      <section className="pillars-section">
        <h2>AI Learning Pillars</h2>
        <div className="pillars-grid">
          {data.pillars.map((pillar) => (
            <PillarCard key={pillar.id} pillar={pillar} />
          ))}
        </div>
      </section>

      {showRecs && (
        <section className="recommendations-section">
          <h2 className="recommendations-title">Recommended for you</h2>
          {recsLoading ? (
            <div className="recommendations-grid">
              {[1, 2, 3].map((i) => <div key={i} className="rec-card rec-card-skeleton" />)}
            </div>
          ) : personalRecs.length > 0 ? (
            <div className="recommendations-grid">
              {personalRecs.map((rec, i) => (
                <RecCard key={rec.course_id} rec={rec} rank={i + 1} onFireEvent={fireEvent} />
              ))}
            </div>
          ) : null}
        </section>
      )}

      {showRecs && cfRecs.length > 0 && (
        <section className="recommendations-section cf-section">
          <h2 className="recommendations-title cf-title">Teachers like you also took</h2>
          <div className="cf-grid">
            {cfRecs.map((rec, i) => (
              <CfRecCard key={rec.course_id} rec={rec} rank={i + 1} onFireEvent={fireEvent} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Add CF section styles to `frontend/src/pages/HomePage.css`**

Append to the existing file:

```css
.cf-section {
  margin-top: 0;
}

.cf-title {
  color: #16a34a;
}

.cf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem;
}

.cf-card {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.cf-reason {
  color: #15803d;
  font-weight: 500;
}
```

- [ ] **Step 3: Build to confirm no errors**

```bash
cd frontend
npm run build
```

Expected: Build succeeds.

- [ ] **Step 4: Manually verify in browser**

Start backend + frontend via Docker or dev servers. Log in as `demo_teacher / demo1234`.

Verify:
- "Recommended for you" section still renders personal recs
- If there are CF recommendations (requires peer group data), "Teachers like you also took" section appears below
- Opening browser network tab: on page load, POST requests to `/api/recommendations/events/` fire with `event_type: 'shown'` for each visible card
- Clicking "Start course →" fires a `clicked` event (visible in network tab) then navigates to the course detail page

Since the seeded database has only one teacher per peer group, CF recommendations may be empty — that's correct behaviour (no peers = no CF row shown).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/HomePage.jsx frontend/src/pages/HomePage.css
git commit -m "feat: add CF row to HomePage + fire shown/clicked recommendation events"
```

---

## Task 11: Frontend — enrolled event from CourseDetailPage

**Files:**
- Modify: `frontend/src/pages/CourseDetailPage.jsx`

When a teacher navigates from a recommendation card (Task 10 passes `{ fromRec, recRank, recSource }` in router state) and then clicks Enroll, fire an `enrolled` event.

- [ ] **Step 1: Update `frontend/src/pages/CourseDetailPage.jsx`**

Add `useLocation` import and event-fire logic in `handleEnroll`:

Add to the imports at the top:

```jsx
import { useParams, useNavigate, useLocation } from 'react-router-dom'
```

Add inside the component, after the existing state declarations:

```jsx
const location = useLocation()
const recMeta = location.state  // may be { fromRec, recRank, recSource }
```

In `handleEnroll`, after the successful enroll (after `setCourse(res.data)`), add:

```jsx
if (recMeta?.fromRec) {
  client.post('/recommendations/events/', {
    course_id: Number(id),
    event_type: 'enrolled',
    rank: recMeta.recRank ?? 0,
    source: recMeta.recSource ?? 'personal',
  }).catch(() => {})
}
```

Full updated `handleEnroll` function:

```jsx
const handleEnroll = async () => {
  setEnrolling(true)
  try {
    await client.post(`/courses/${id}/enroll/`)
    const res = await client.get(`/courses/${id}/`)
    setCourse(res.data)
    if (recMeta?.fromRec) {
      client.post('/recommendations/events/', {
        course_id: Number(id),
        event_type: 'enrolled',
        rank: recMeta.recRank ?? 0,
        source: recMeta.recSource ?? 'personal',
      }).catch(() => {})
    }
  } catch {
    setError('Enrollment failed.')
  } finally {
    setEnrolling(false)
  }
}
```

- [ ] **Step 2: Build**

```bash
cd frontend
npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Manually verify enrolled event flow**

1. Log in as `demo_teacher / demo1234`
2. Go to Home page — click "Start course →" on a personal recommendation card
3. On the Course Detail page, open the browser network tab
4. Click "Enroll Now"
5. Confirm: a POST to `/api/recommendations/events/` fires with `event_type: 'enrolled'`

- [ ] **Step 4: Run frontend lint**

```bash
cd frontend
npm run lint
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CourseDetailPage.jsx
git commit -m "feat: fire enrolled recommendation event from CourseDetailPage"
```

---

## Final verification

- [ ] **Run full backend test suite with coverage**

```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub --verbosity=2
.venv/Scripts/uv.exe run coverage report --fail-under=70
```

Expected: All tests pass, coverage ≥ 70%.

- [ ] **Run frontend lint + build**

```bash
cd frontend
npm run lint && npm run build
```

Expected: No lint errors, build succeeds.

- [ ] **End-to-end smoke test with Docker**

```bash
cd ..  # project root
docker compose up -d
docker compose exec backend .venv/Scripts/uv.exe run manage.py migrate
docker compose exec backend .venv/Scripts/uv.exe run manage.py seed
```

Navigate to `http://localhost:5173`:
1. Log in as `demo_teacher / demo1234`
2. Home page loads — "Recommended for you" row renders (seeded recs from nightly task or manual trigger)
3. Profile page at `/profile` — pillar checkboxes + style radio + save button work
4. Network tab confirms events fire on card impression and click
5. Course detail page logs a CourseView (verify in Django admin at `http://localhost:8000/admin/hub/courseview/`)
6. Enrolling from a recommended course fires enrolled event (visible in admin at `hub/recommendationevent/`)
