# Learning Preference Finder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A "Find your learning preference" wizard in the profile that quizzes the user with admin-managed questions and saves the winning learning style.

**Architecture:** Two new models (`PreferenceQuestion`/`PreferenceOption`) with admin inlines and idempotent seed data; one API view (GET questions / POST answers → tally → save style + recompute recommendations); a modal wizard component wired into the Profile's Learning Preferences card. Spec: `docs/superpowers/specs/2026-07-18-preference-finder-design.md`.

**Tech Stack:** Django/DRF, React modal component (per-component CSS, lucide-react icons).

## Global Constraints

- Backend runner from `backend/`: `.venv/Scripts/uv.exe run ...` (fallback `C:\Users\Nikos A. Grammatikos\.local\bin\uv.exe run ...`; ignore VIRTUAL_ENV stderr warning)
- Tests: `uv.exe run manage.py test hub.tests.test_preference_quiz -v 2`; full `uv.exe run manage.py test hub analytics -v 1` stays green (367+)
- Lint: `uv.exe run ruff check . --fix`; frontend `npm run lint && npm run build` warning-free
- `maps_to` must NEVER appear in the GET payload (no answer leaking)
- Tie-break: first style in `UserProfile.LearningStyle` declaration order (video, text, visual, interactive)
- POST saves `profile.learning_style` with `save(update_fields=['learning_style'])` and calls `compute_user_recommendations.delay(user.id)`
- Seed is idempotent (re-running `manage.py seed` must not duplicate questions)
- Commit after each task; messages end with the project's Co-Authored-By trailer

---

### Task 1: Models, migration, admin, seed

**Files:**
- Create: `backend/hub/models/preference_quiz.py`
- Modify: `backend/hub/models/__init__.py`
- Create: migration via `makemigrations` (expected `0021_preference_quiz`)
- Modify: `backend/hub/admin.py`
- Create: `backend/hub/management/commands/seed_data/preference_quiz.py`
- Modify: `backend/hub/management/commands/seed.py`
- Test: `backend/hub/tests/test_preference_quiz.py` (new)

**Interfaces:**
- Produces: `PreferenceQuestion` (text, order, is_active; Meta ordering `['order']`) and `PreferenceOption` (question FK related_name `options`, text, maps_to, order; Meta ordering `['order']`), exported from `hub.models`; `seed_preference_quiz()` idempotent. Task 2 consumes the models.

- [ ] **Step 1: Write the failing model/seed tests — new file `backend/hub/tests/test_preference_quiz.py`**

```python
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase  # noqa: F401  (used by Task 2 classes)

from hub.models import PreferenceOption, PreferenceQuestion, UserProfile  # noqa: F401


class PreferenceQuizModelTests(TestCase):
    def test_question_option_roundtrip(self):
        q = PreferenceQuestion.objects.create(text='Q1?', order=1)
        PreferenceOption.objects.create(question=q, text='Watch', maps_to='video', order=1)
        PreferenceOption.objects.create(question=q, text='Read', maps_to='text', order=2)
        self.assertEqual(list(q.options.values_list('maps_to', flat=True)), ['video', 'text'])

    def test_seed_is_idempotent(self):
        from hub.management.commands.seed_data.preference_quiz import seed_preference_quiz
        seed_preference_quiz()
        first_count = PreferenceQuestion.objects.count()
        self.assertGreaterEqual(first_count, 4)
        seed_preference_quiz()
        self.assertEqual(PreferenceQuestion.objects.count(), first_count)
        for question in PreferenceQuestion.objects.all():
            self.assertEqual(question.options.count(), 4)
            self.assertEqual(
                sorted(question.options.values_list('maps_to', flat=True)),
                sorted(['video', 'text', 'visual', 'interactive']),
            )
```

Run: `uv.exe run manage.py test hub.tests.test_preference_quiz -v 2` → FAIL (ImportError).

- [ ] **Step 2: Create `backend/hub/models/preference_quiz.py`**

```python
from django.db import models

from .user import UserProfile


class PreferenceQuestion(models.Model):
    text      = models.CharField(max_length=300)
    order     = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text


class PreferenceOption(models.Model):
    question = models.ForeignKey(
        PreferenceQuestion, on_delete=models.CASCADE, related_name='options',
    )
    text     = models.CharField(max_length=300)
    maps_to  = models.CharField(max_length=20, choices=UserProfile.LearningStyle.choices)
    order    = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.text} -> {self.maps_to}'
```

Export both from `backend/hub/models/__init__.py` (alphabetical placement, add to `__all__`). Then:

Run: `uv.exe run manage.py makemigrations hub -n preference_quiz` and `uv.exe run manage.py migrate`

- [ ] **Step 3: Admin registration (append to `backend/hub/admin.py`)**

```python
class PreferenceOptionInline(admin.TabularInline):
    model = PreferenceOption
    extra = 2
    fields = ['text', 'maps_to', 'order']
    ordering = ['order']


@admin.register(PreferenceQuestion)
class PreferenceQuestionAdmin(admin.ModelAdmin):
    list_display  = ['text', 'order', 'is_active', 'option_count']
    list_editable = ['order', 'is_active']
    inlines = [PreferenceOptionInline]

    @admin.display(description='Options')
    def option_count(self, obj):
        return obj.options.count()
```

Add `PreferenceOption`, `PreferenceQuestion` to the existing `from .models import (...)` block. Place the classes in a new `# ── Preference quiz ──` section near the profile admin.

- [ ] **Step 4: Seed data — `backend/hub/management/commands/seed_data/preference_quiz.py`**

```python
from hub.models import PreferenceOption, PreferenceQuestion

_QUESTIONS = [
    {
        'order': 1,
        'text': 'When you learn something new, what helps you most?',
        'options': [
            ('Watching someone demonstrate it', 'video'),
            ('Reading a clear explanation', 'text'),
            ('Studying a diagram or infographic', 'visual'),
            ('Trying it hands-on right away', 'interactive'),
        ],
    },
    {
        'order': 2,
        'text': 'Think of the best training you ever attended. What made it work for you?',
        'options': [
            ('Engaging video lectures', 'video'),
            ('Well-written materials I could re-read', 'text'),
            ('Strong slides, charts and visuals', 'visual'),
            ('Exercises and group activities', 'interactive'),
        ],
    },
    {
        'order': 3,
        'text': 'You have to master a new classroom tool by Friday. What is your first move?',
        'options': [
            ('Find a video walkthrough', 'video'),
            ('Read the manual or a how-to guide', 'text'),
            ('Look for an annotated screenshot tour', 'visual'),
            ('Open it and click around', 'interactive'),
        ],
    },
    {
        'order': 4,
        'text': 'Which kind of online content do you actually finish?',
        'options': [
            ('Short video series', 'video'),
            ('Long-form articles', 'text'),
            ('Visual explainers', 'visual'),
            ('Interactive quizzes and simulations', 'interactive'),
        ],
    },
]


def seed_preference_quiz():
    for data in _QUESTIONS:
        question, _ = PreferenceQuestion.objects.update_or_create(
            order=data['order'],
            defaults={'text': data['text'], 'is_active': True},
        )
        question.options.all().delete()
        for opt_order, (text, maps_to) in enumerate(data['options'], start=1):
            PreferenceOption.objects.create(
                question=question, text=text, maps_to=maps_to, order=opt_order,
            )
```

Wire into `backend/hub/management/commands/seed.py`: import `from .seed_data.preference_quiz import seed_preference_quiz` and call `seed_preference_quiz()` in `handle()` after `seed_pathways()`.

- [ ] **Step 5: Run tests (GREEN), full suite, ruff, commit**

```bash
git add backend/hub
git commit -m "feat: preference quiz models, admin, and seed data"
```

---

### Task 2: API — GET questions / POST answers

**Files:**
- Create: `backend/hub/serializers/preference_quiz.py`
- Modify: `backend/hub/serializers/__init__.py` (if the package re-exports; check and follow convention)
- Create: `backend/hub/views/preference_quiz.py`
- Modify: `backend/hub/views/__init__.py`, `backend/hub/urls.py`
- Test: `backend/hub/tests/test_preference_quiz.py` (append)

**Interfaces:**
- Consumes: Task 1 models
- Produces: `GET/POST /api/preference-quiz/` per the spec. Task 3 consumes it.

- [ ] **Step 1: Write failing API tests (append)**

```python
class PreferenceQuizApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pref_user', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.q1 = PreferenceQuestion.objects.create(text='Q1?', order=1)
        self.q2 = PreferenceQuestion.objects.create(text='Q2?', order=2)
        self.inactive = PreferenceQuestion.objects.create(text='Old?', order=3, is_active=False)
        self.q1_video = PreferenceOption.objects.create(question=self.q1, text='a', maps_to='video', order=1)
        self.q1_text  = PreferenceOption.objects.create(question=self.q1, text='b', maps_to='text', order=2)
        self.q2_video = PreferenceOption.objects.create(question=self.q2, text='c', maps_to='video', order=1)
        self.q2_visual = PreferenceOption.objects.create(question=self.q2, text='d', maps_to='visual', order=2)
        PreferenceOption.objects.create(question=self.inactive, text='e', maps_to='text', order=1)
        self.url = '/api/preference-quiz/'
        self.client.force_authenticate(self.user)

    def test_get_returns_active_questions_without_maps_to(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([q['text'] for q in res.data], ['Q1?', 'Q2?'])
        self.assertNotIn('maps_to', res.data[0]['options'][0])

    def test_post_saves_winner(self):
        res = self.client.post(self.url, {'answers': [
            {'question_id': self.q1.id, 'option_id': self.q1_video.id},
            {'question_id': self.q2.id, 'option_id': self.q2_video.id},
        ]}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['learning_style'], 'video')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.learning_style, 'video')

    def test_tie_breaks_toward_declaration_order(self):
        # one video vote, one visual vote -> video wins (declared first)
        res = self.client.post(self.url, {'answers': [
            {'question_id': self.q1.id, 'option_id': self.q1_video.id},
            {'question_id': self.q2.id, 'option_id': self.q2_visual.id},
        ]}, format='json')
        self.assertEqual(res.data['learning_style'], 'video')

    def test_invalid_option_rejected(self):
        res = self.client.post(self.url, {'answers': [{'question_id': self.q1.id, 'option_id': 999999}]}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_two_answers_for_same_question_rejected(self):
        res = self.client.post(self.url, {'answers': [
            {'question_id': self.q1.id, 'option_id': self.q1_video.id},
            {'question_id': self.q1.id, 'option_id': self.q1_text.id},
        ]}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_empty_answers_rejected(self):
        res = self.client.post(self.url, {'answers': []}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_requires_auth(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
```

Run → FAIL (404).

- [ ] **Step 2: Serializers — `backend/hub/serializers/preference_quiz.py`**

```python
from rest_framework import serializers

from hub.models import PreferenceOption, PreferenceQuestion


class PreferenceOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PreferenceOption
        fields = ['id', 'text']  # maps_to deliberately hidden


class PreferenceQuestionSerializer(serializers.ModelSerializer):
    options = PreferenceOptionSerializer(many=True, read_only=True)

    class Meta:
        model  = PreferenceQuestion
        fields = ['id', 'text', 'options']
```

Follow the serializers package's existing re-export convention (check `hub/serializers/__init__.py`).

- [ ] **Step 3: View — `backend/hub/views/preference_quiz.py`**

```python
from collections import Counter

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import PreferenceOption, PreferenceQuestion, UserProfile
from hub.serializers.preference_quiz import PreferenceQuestionSerializer
from hub.tasks import compute_user_recommendations


class PreferenceQuizView(APIView):
    """GET /api/preference-quiz/ — active questions. POST — tally answers, save style."""

    def get(self, request):
        questions = (
            PreferenceQuestion.objects
            .filter(is_active=True)
            .prefetch_related('options')
        )
        return Response(PreferenceQuestionSerializer(questions, many=True).data)

    def post(self, request):
        answers = request.data.get('answers')
        if not isinstance(answers, list) or not answers:
            return Response({'error': 'answers must be a non-empty list.'},
                            status=status.HTTP_400_BAD_REQUEST)

        option_ids = []
        for answer in answers:
            if not isinstance(answer, dict) or 'option_id' not in answer:
                return Response({'error': 'each answer needs an option_id.'},
                                status=status.HTTP_400_BAD_REQUEST)
            option_ids.append(answer['option_id'])

        options = list(
            PreferenceOption.objects
            .filter(id__in=option_ids, question__is_active=True)
            .select_related('question')
        )
        if len(options) != len(set(option_ids)) or len(option_ids) != len(set(option_ids)):
            return Response({'error': 'invalid or duplicate option ids.'},
                            status=status.HTTP_400_BAD_REQUEST)

        seen_questions = set()
        for option in options:
            if option.question_id in seen_questions:
                return Response({'error': 'only one answer per question is allowed.'},
                                status=status.HTTP_400_BAD_REQUEST)
            seen_questions.add(option.question_id)

        counts = Counter(option.maps_to for option in options)
        best = max(counts.values())
        winner = next(
            style for style in UserProfile.LearningStyle.values
            if counts.get(style, 0) == best
        )

        profile = request.user.profile
        profile.learning_style = winner
        profile.save(update_fields=['learning_style'])
        compute_user_recommendations.delay(request.user.id)

        return Response({
            'learning_style': winner,
            'label': UserProfile.LearningStyle(winner).label,
        })
```

Export in `views/__init__.py`; route in `urls.py`:

```python
    path('preference-quiz/', PreferenceQuizView.as_view(), name='preference-quiz'),
```

- [ ] **Step 4: Run tests (GREEN), full suite, ruff, commit**

```bash
git add backend/hub
git commit -m "feat: preference quiz API with server-side tally"
```

---

### Task 3: Frontend — modal wizard + profile button

**Files:**
- Create: `frontend/src/components/PreferenceFinderModal.jsx`
- Create: `frontend/src/components/PreferenceFinderModal.css`
- Modify: `frontend/src/pages/ProfilePage.jsx` (PreferencesSection)

**Interfaces:**
- Consumes: `GET/POST /api/preference-quiz/`
- Produces: `<PreferenceFinderModal open onClose onComplete(styleValue) />`

- [ ] **Step 1: Create `frontend/src/components/PreferenceFinderModal.jsx`**

```jsx
import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { X, Sparkles } from 'lucide-react'
import client from '../api/client'
import './PreferenceFinderModal.css'

const STYLE_LABELS = { video: 'Video', text: 'Text', visual: 'Visual', interactive: 'Interactive' }

PreferenceFinderModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onComplete: PropTypes.func.isRequired,
}

export default function PreferenceFinderModal({ open, onClose, onComplete }) {
  const [questions, setQuestions] = useState(null)
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState({})   // { [questionId]: optionId }
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setQuestions(null)
    setStep(0)
    setAnswers({})
    setResult(null)
    setError('')
    client.get('/preference-quiz/')
      .then(res => setQuestions(res.data))
      .catch(() => setError('Could not load the questions. Please try again later.'))
  }, [open])

  if (!open) return null

  const current = questions?.[step]
  const isLast = questions && step === questions.length - 1
  const chosen = current ? answers[current.id] : undefined

  const handleSubmit = async () => {
    setSubmitting(true)
    setError('')
    try {
      const payload = {
        answers: Object.entries(answers).map(([questionId, optionId]) => ({
          question_id: Number(questionId), option_id: optionId,
        })),
      }
      const res = await client.post('/preference-quiz/', payload)
      setResult(res.data)
      onComplete(res.data.learning_style)
    } catch {
      setError('Something went wrong saving your result. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="pf-overlay" onClick={onClose}>
      <div className="pf-modal" onClick={(e) => e.stopPropagation()}>
        <button className="pf-close" aria-label="Close" onClick={onClose}><X size={18} /></button>

        {error && <p className="pf-error">{error}</p>}

        {!error && !questions && <p className="pf-loading">Loading questions…</p>}

        {!error && questions && questions.length === 0 && (
          <p className="pf-loading">No questions are configured yet. Check back soon!</p>
        )}

        {!error && questions && questions.length > 0 && !result && current && (
          <>
            <div className="pf-head">
              <Sparkles size={18} className="pf-head-icon" />
              <h2>Find your learning preference</h2>
            </div>
            <div className="pf-progress">
              <div className="pf-progress-fill" style={{ width: `${((step + 1) / questions.length) * 100}%` }} />
            </div>
            <p className="pf-counter">Question {step + 1} of {questions.length}</p>
            <p className="pf-question">{current.text}</p>
            <div className="pf-options">
              {current.options.map(opt => (
                <button
                  key={opt.id}
                  className={`pf-option ${chosen === opt.id ? 'pf-option--selected' : ''}`}
                  onClick={() => setAnswers(prev => ({ ...prev, [current.id]: opt.id }))}
                >
                  {opt.text}
                </button>
              ))}
            </div>
            <div className="pf-nav">
              {step > 0 && (
                <button className="pf-btn pf-btn--ghost" onClick={() => setStep(s => s - 1)}>Back</button>
              )}
              {!isLast && (
                <button className="pf-btn" disabled={chosen === undefined} onClick={() => setStep(s => s + 1)}>
                  Next
                </button>
              )}
              {isLast && (
                <button className="pf-btn" disabled={chosen === undefined || submitting} onClick={handleSubmit}>
                  {submitting ? 'Working…' : 'See my result'}
                </button>
              )}
            </div>
          </>
        )}

        {result && (
          <div className="pf-result">
            <Sparkles size={28} className="pf-result-icon" />
            <h2>You learn best with <span className="pf-result-style">{STYLE_LABELS[result.learning_style] ?? result.label}</span> content</h2>
            <p className="pf-result-sub">
              We saved this as your preferred learning format — recommendations will favour
              {' '}{(STYLE_LABELS[result.learning_style] ?? result.label).toLowerCase()} courses.
              You can change it anytime in Learning Preferences.
            </p>
            <button className="pf-btn" onClick={onClose}>Done</button>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/PreferenceFinderModal.css`**

```css
.pf-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.pf-modal {
  position: relative;
  width: min(520px, calc(100vw - 2rem));
  background: #fff;
  border-radius: 12px;
  padding: 1.75rem;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
}

.pf-close {
  position: absolute;
  top: 0.9rem;
  right: 0.9rem;
  border: 0;
  background: none;
  cursor: pointer;
  color: #6b7280;
}

.pf-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.9rem; }
.pf-head h2 { font-size: 1.15rem; margin: 0; }
.pf-head-icon { color: var(--color-primary); }

.pf-progress {
  height: 6px;
  border-radius: 3px;
  background: #e5e7eb;
  overflow: hidden;
  margin-bottom: 0.4rem;
}
.pf-progress-fill { height: 100%; background: var(--color-primary); transition: width 0.25s; }
.pf-counter { font-size: 0.78rem; color: #6b7280; margin: 0 0 0.9rem; }
.pf-question { font-weight: 600; margin: 0 0 0.9rem; }

.pf-options { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.1rem; }
.pf-option {
  text-align: left;
  padding: 0.65rem 0.9rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 0.9rem;
}
.pf-option:hover { background: #f9fafb; }
.pf-option--selected { border-color: var(--color-primary); background: #eef2ff; }

.pf-nav { display: flex; justify-content: flex-end; gap: 0.5rem; }
.pf-btn {
  padding: 0.5rem 1.1rem;
  border: 0;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  font-size: 0.9rem;
  cursor: pointer;
}
.pf-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.pf-btn--ghost { background: none; color: var(--color-primary); border: 1px solid var(--color-primary); }

.pf-loading, .pf-error { padding: 1.5rem 0; text-align: center; }
.pf-error { color: #b91c1c; }

.pf-result { text-align: center; padding: 0.5rem 0; }
.pf-result h2 { font-size: 1.2rem; margin: 0.6rem 0; }
.pf-result-icon { color: var(--color-primary); }
.pf-result-style { color: var(--color-primary); }
.pf-result-sub { font-size: 0.88rem; color: #6b7280; margin-bottom: 1.1rem; }
```

- [ ] **Step 3: Wire into `PreferencesSection` (ProfilePage.jsx)**

Import at the top of the file: `import PreferenceFinderModal from '../components/PreferenceFinderModal'` and add `Sparkles` to the lucide-react import if not present.

In `PreferencesSection`, add state `const [finderOpen, setFinderOpen] = useState(false)`. Directly under the "Preferred Learning Format" `profile-field` div, add:

```jsx
        <button
          type="button"
          className="profile-finder-btn"
          onClick={() => setFinderOpen(true)}
        >
          <Sparkles size={14} /> Find your learning preference
        </button>

        <PreferenceFinderModal
          open={finderOpen}
          onClose={() => setFinderOpen(false)}
          onComplete={(style) => setForm(prev => ({ ...prev, learning_style: style }))}
        />
```

CSS in `ProfilePage.css`:

```css
.profile-finder-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin: -0.5rem 0 1rem;
  padding: 0.4rem 0.8rem;
  border: 1px dashed var(--color-primary);
  border-radius: 8px;
  background: none;
  color: var(--color-primary);
  font-size: 0.82rem;
  cursor: pointer;
}

.profile-finder-btn:hover { background: #eef2ff; }
```

- [ ] **Step 4: Verify + commit**

`cd frontend && npm run lint && npm run build` — pass, warning-free.

```bash
git add frontend/src
git commit -m "feat: learning preference finder wizard in profile"
```

---

### Final verification

- [ ] `cd backend && uv.exe run coverage run manage.py test hub analytics -v 1` — green, ≥70%
- [ ] `uv.exe run ruff check .` — clean
- [ ] `cd frontend && npm run lint && npm run build` — clean
- [ ] Dispatch final whole-branch review

## Deployment notes

New migration + seed: on the VM run `git pull`, `docker compose up -d`, then
`docker compose exec backend uv run python manage.py migrate` and
`docker compose exec backend uv run python manage.py seed` (adds the 4 questions).
