# Assignment Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assignment lessons complete only when a reviewer (course creator for own courses; new AIDEA Partner role or admin for all) approves the learner's submission; "request changes" returns it with feedback for resubmission; a per-module LLM-reviewer toggle is stubbed for later.

**Architecture:** New `AssignmentSubmission` model + `aidea_partner` role; lesson-completion side effects extracted to `hub/completion.py` so review approval reuses them; submission + review APIs; LessonPage assignment states + a Reviews queue page. Spec: `docs/superpowers/specs/2026-07-19-assignment-review-design.md`.

**Tech Stack:** Django/DRF, React (per-component CSS, lucide-react).

## Global Constraints

- Backend runner from `backend/`: `.venv/Scripts/uv.exe run ...` (fallback `C:\Users\Nikos A. Grammatikos\.local\bin\uv.exe run ...`; ignore VIRTUAL_ENV stderr warning)
- Tests: `uv.exe run manage.py test hub.tests.test_assignment_review -v 2`; full `uv.exe run manage.py test hub analytics -v 1` stays green (393+). Legacy tests that complete ASSIGNMENT lessons via `/complete/` must be updated to the new submit→approve flow (or to expect the new 400) — every change listed + justified in the report; other legacy failures = STOP and report BLOCKED.
- Lint: backend ruff; frontend `npm run lint && npm run build` warning-free
- Role value exactly `aidea_partner`, label `AIDEA Partner`
- `/complete/` returns 400 `{'detail': 'Assignments are completed through review.'}` for assignment lessons; approval completes via the SAME `record_lesson_completion` helper (no duplicated completion logic anywhere)
- Reviewer scoping: content_creator → only `course.created_by == user`; aidea_partner/admin → all; everyone else 403
- Resubmission: overwrites text, resets status to pending, PRESERVES previous feedback/reviewer fields
- Approve on non-pending submission (or on a learner no longer enrolled) → 400
- Already-completed assignment lessons stay completed (no data migration)
- Commit after each task; messages end with the project's Co-Authored-By trailer

---

### Task 1: Role, models, admin, seed, LLM stub

**Files:**
- Modify: `backend/hub/models/user.py` (UserType choice)
- Create: `backend/hub/models/assignment.py`
- Modify: `backend/hub/models/content.py` (Module.llm_review_enabled)
- Modify: `backend/hub/models/__init__.py`
- Create: migration via `makemigrations hub -n assignment_review`
- Create: `backend/hub/llm_review.py`
- Modify: `backend/hub/admin.py`
- Modify: `backend/hub/management/commands/seed.py` (demo_partner)
- Test: `backend/hub/tests/test_assignment_review.py` (new)

**Interfaces:**
- Produces: `UserProfile.UserType.AIDEA_PARTNER`; `AssignmentSubmission` (user FK related_name `assignment_submissions`, lesson FK related_name `submissions`, text, status TextChoices PENDING/APPROVED/CHANGES_REQUESTED default PENDING, feedback blank, reviewed_by nullable FK related_name `reviewed_submissions`, reviewed_at nullable, submitted_at auto_now_add, updated_at auto_now, unique_together (user, lesson), ordering ['submitted_at']); `Module.llm_review_enabled` bool default False; `hub.llm_review.review_submission(submission) -> None`.

- [ ] **Step 1: Failing tests — new file `backend/hub/tests/test_assignment_review.py`**

```python
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase  # noqa: F401  (used by later tasks)

from hub.models import (
    AssignmentSubmission,
    Course,
    Enrollment,  # noqa: F401
    LearningPillar,
    Lesson,
    Module,
    UserProfile,
)


def make_assignment_course(creator=None, slug='par1'):
    pillar = LearningPillar.objects.create(name=f'P-{slug}', slug=slug, order=1)
    course = Course.objects.create(
        title=f'C-{slug}', pillar=pillar, level='beginner', duration_hours=1,
        is_published=True, created_by=creator,
    )
    module = Module.objects.create(course=course, title='M', order=1)
    assignment = Lesson.objects.create(
        module=module, title='A', lesson_type='assignment', order=1,
        is_required=True, content='Write an essay.',
    )
    return course, module, assignment


class AssignmentModelTests(TestCase):
    def test_partner_role_exists(self):
        self.assertEqual(UserProfile.UserType.AIDEA_PARTNER, 'aidea_partner')
        self.assertEqual(UserProfile.UserType.AIDEA_PARTNER.label, 'AIDEA Partner')

    def test_submission_unique_per_user_lesson(self):
        user = User.objects.create_user(username='sub_u', password='pass12345')
        UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
        _, _, assignment = make_assignment_course()
        AssignmentSubmission.objects.create(user=user, lesson=assignment, text='v1')
        sub = AssignmentSubmission.objects.get(user=user, lesson=assignment)
        self.assertEqual(sub.status, AssignmentSubmission.Status.PENDING)

    def test_module_llm_toggle_default_off(self):
        _, module, _ = make_assignment_course(slug='par2')
        self.assertFalse(module.llm_review_enabled)

    def test_llm_stub_returns_none(self):
        from hub.llm_review import review_submission
        self.assertIsNone(review_submission(None))
```

Run: `uv.exe run manage.py test hub.tests.test_assignment_review -v 2` → FAIL (ImportError).

- [ ] **Step 2: Models**

`backend/hub/models/user.py` — add to `UserType`:

```python
        AIDEA_PARTNER   = 'aidea_partner',   'AIDEA Partner'
```

`backend/hub/models/content.py` — add to `Module` after `duration_minutes`:

```python
    # Stub toggle: per-module LLM assignment reviewer ("later turned on")
    llm_review_enabled = models.BooleanField(default=False)
```

Create `backend/hub/models/assignment.py`:

```python
from django.contrib.auth.models import User
from django.db import models

from .content import Lesson


class AssignmentSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING           = 'pending',           'Pending review'
        APPROVED          = 'approved',          'Approved'
        CHANGES_REQUESTED = 'changes_requested', 'Changes requested'

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    lesson       = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='submissions')
    text         = models.TextField()
    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    feedback     = models.TextField(blank=True)
    reviewed_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_submissions',
    )
    reviewed_at  = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'lesson')
        ordering = ['submitted_at']

    def __str__(self):
        return f'{self.user.username} -> {self.lesson.title} ({self.status})'
```

Export `AssignmentSubmission` from `models/__init__.py` (alphabetical + `__all__`). Run `makemigrations hub -n assignment_review && migrate`.

- [ ] **Step 3: LLM stub — `backend/hub/llm_review.py`**

```python
"""Per-module LLM assignment reviewer — stub until models are trained.

review_submission is called when a submission arrives for a module with
llm_review_enabled. Returning None means "no verdict — leave it in the
human review queue". A future implementation returns a (status, feedback)
decision instead; only this module changes when that happens.
"""


def review_submission(submission):
    return None
```

- [ ] **Step 4: Admin + seed**

`backend/hub/admin.py`:
- `CustomUserAdmin.get_user_type` colours/labels dicts gain `'aidea_partner': '#0d9488'` / `'aidea_partner': 'AIDEA Partner'`
- Register submissions (new section):

```python
@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'lesson', 'get_course', 'status', 'reviewed_by', 'submitted_at']
    list_filter   = ['status']
    search_fields = ['user__username', 'lesson__title', 'text']
    readonly_fields = ['user', 'lesson', 'text', 'submitted_at', 'updated_at']
    ordering = ['-submitted_at']

    @admin.display(description='Course', ordering='lesson__module__course__title')
    def get_course(self, obj):
        return obj.lesson.module.course.title
```

(import AssignmentSubmission in the models import block)

`backend/hub/management/commands/seed.py` — add a `_seed_demo_partner` creating `demo_partner / demo1234` with `user_type=UserProfile.UserType.AIDEA_PARTNER` (mirror `_seed_demo_content_creator`'s idempotent pattern — read it first), called from `handle()`.

- [ ] **Step 5: GREEN, full suite, ruff, commit**

```bash
git add backend/hub
git commit -m "feat: AIDEA Partner role, assignment submissions model, LLM review stub"
```

---

### Task 2: Completion extraction + assignment gate

**Files:**
- Create: `backend/hub/completion.py`
- Modify: `backend/hub/views/learner.py` (LessonCompleteView)
- Test: `backend/hub/tests/test_assignment_review.py` (append)

**Interfaces:**
- Produces: `record_lesson_completion(user, enrollment, lesson, quiz_answers_raw=None, engagement_data=None) -> (lesson_progress, progress_pct)` — the ONLY place completion side effects live. Task 3 consumes it.

- [ ] **Step 1: Failing tests (append)**

```python
class CompleteEndpointAssignmentGateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='gate_u', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.course, _, self.assignment = make_assignment_course(slug='gate1')
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(self.user)

    def test_complete_rejects_assignment_lessons(self):
        url = f'/api/courses/{self.course.id}/lessons/{self.assignment.id}/complete/'
        res = self.client.post(url, {'engagement_data': {'submission': 'hi'}}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('review', res.data['detail'].lower())

    def test_complete_still_works_for_text_lessons(self):
        text = Lesson.objects.create(
            module=self.assignment.module, title='T', lesson_type='text',
            order=2, is_required=True,
        )
        url = f'/api/courses/{self.course.id}/lessons/{text.id}/complete/'
        res = self.client.post(url, {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['progress_pct'], 50)  # 1 of 2 required done
```

Run → FAIL (assignment completes with 200 today).

- [ ] **Step 2: Create `backend/hub/completion.py`** — move the body verbatim from `LessonCompleteView.post` (backend/hub/views/learner.py lines ~244-300):

```python
"""Lesson-completion side effects — shared by learner self-completion and
assignment-review approval. Single source of truth for progress/competency."""
from django.utils import timezone

from hub.models import Lesson, LessonProgress, LessonSession


def record_lesson_completion(user, enrollment, lesson, quiz_answers_raw=None, engagement_data=None):
    """Create the LessonProgress row (first completion only) and update the
    enrollment's progress/current-module/completed-at plus the competency
    score. Returns (lesson_progress, progress_pct)."""
    course = enrollment.course
    quiz_answers_raw = quiz_answers_raw or []

    lp, created = LessonProgress.objects.get_or_create(user=user, lesson=lesson)

    if created:
        now = timezone.now()
        lp.completed_at = now

        session = LessonSession.objects.filter(
            user=user, lesson=lesson,
        ).order_by('-started_at').first()
        if session:
            lp.time_spent_seconds = max(0, int((now - session.started_at).total_seconds()))

        if lesson.lesson_type == 'quiz' and quiz_answers_raw and lesson.quiz_data:
            booleans = []
            for i, selected in enumerate(quiz_answers_raw):
                if i < len(lesson.quiz_data):
                    options = lesson.quiz_data[i].get('options', [])
                    if isinstance(selected, int) and 0 <= selected < len(options):
                        booleans.append(bool(options[selected].get('is_correct', False)))
                    else:
                        booleans.append(False)
            # Pad to full question count so score denominator is always len(quiz_data)
            while len(booleans) < len(lesson.quiz_data):
                booleans.append(False)
            lp.quiz_answers = booleans
            lp.quiz_score = sum(booleans) / len(booleans) if booleans else 0.0

        engagement = dict(engagement_data or {})
        if lesson.lesson_type == 'assignment' and 'submission' in engagement:
            engagement['word_count'] = len(str(engagement['submission']).split())
        if lesson.lesson_type == 'quiz' and quiz_answers_raw:
            engagement['quiz_selected'] = quiz_answers_raw
        lp.engagement_data = engagement

        lp.save()

    total = Lesson.objects.filter(module__course=course, is_required=True).count()
    completed_count = LessonProgress.objects.filter(
        user=user,
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

    if just_completed and hasattr(user, 'profile'):
        from hub.competency import apply_competency_delta, course_completion_delta
        apply_competency_delta(user, course_completion_delta(user, course))

    return lp, progress_pct
```

- [ ] **Step 3: Delegate in `LessonCompleteView.post`** — after the existing enrollment/lesson guards, replace everything from `lp, created = ...` to the final `return Response(...)` with:

```python
        if lesson.lesson_type == 'assignment':
            return Response(
                {'detail': 'Assignments are completed through review.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from hub.completion import record_lesson_completion
        lp, progress_pct = record_lesson_completion(
            request.user, enrollment, lesson,
            quiz_answers_raw=request.data.get('quiz_answers', []),
            engagement_data=request.data.get('engagement_data'),
        )

        return Response({
            'lesson_id': lesson.id,
            'is_completed': True,
            'progress_pct': progress_pct,
            'quiz_results': lp.quiz_answers if lesson.lesson_type == 'quiz' else None,
        })
```

Prune imports that became unused in learner.py (ruff will flag; `timezone`/`LessonSession`/`LessonProgress` are still used elsewhere in the file — verify before removing anything).

- [ ] **Step 4: GREEN + full suite.** Legacy tests completing assignment lessons via `/complete/` (grep `lesson_type='assignment'` and `'assignment'` in `hub/tests/` — expect hits in `test_learner_activity.py` word-count/engagement tests) must be updated: either switch the fixture lesson to another type when the test's subject is generic engagement, or route through the Task 3 flow if it lands later — for THIS task, updating the fixture lesson type is acceptable ONLY when the test isn't specifically about assignments; if it is, mark it with `# updated fully in assignment-review Task 3` and assert the new 400. List every change. Ruff, commit:

```bash
git add backend/hub
git commit -m "refactor: extract lesson completion side effects, gate assignments behind review"
```

---

### Task 3: Submission + review APIs

**Files:**
- Create: `backend/hub/serializers/assignments.py`
- Create: `backend/hub/views/assignments.py`
- Modify: `backend/hub/views/permissions.py` (IsReviewer)
- Modify: `backend/hub/views/learner.py` (LessonDetailView payload)
- Modify: `backend/hub/views/__init__.py`, `backend/hub/urls.py`
- Test: `backend/hub/tests/test_assignment_review.py` (append)

**Interfaces:**
- Consumes: Task 1 model + stub, Task 2 `record_lesson_completion`
- Produces: `POST /api/courses/<pk>/lessons/<lesson_pk>/submit-assignment/`; `assignment_submission` on lesson detail; `GET /api/reviews/`; `POST /api/reviews/<id>/` — all per the spec

- [ ] **Step 1: Failing tests (append)**

```python
class AssignmentFlowTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='flow_cc', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.partner = User.objects.create_user(username='flow_pa', password='pass12345')
        UserProfile.objects.create(user=self.partner, user_type=UserProfile.UserType.AIDEA_PARTNER)
        self.other_creator = User.objects.create_user(username='flow_cc2', password='pass12345')
        UserProfile.objects.create(user=self.other_creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.learner = User.objects.create_user(username='flow_t', password='pass12345')
        UserProfile.objects.create(user=self.learner, user_type=UserProfile.UserType.TEACHER)

        self.course, self.module, self.assignment = make_assignment_course(self.creator, slug='flow1')
        self.enrollment = Enrollment.objects.create(user=self.learner, course=self.course)
        self.submit_url = f'/api/courses/{self.course.id}/lessons/{self.assignment.id}/submit-assignment/'

    def _submit(self, text='My essay text'):
        self.client.force_authenticate(self.learner)
        return self.client.post(self.submit_url, {'text': text}, format='json')

    def test_submit_creates_pending_submission_without_completing(self):
        res = self._submit()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'pending')
        from hub.models import LessonProgress
        self.assertFalse(LessonProgress.objects.filter(user=self.learner, lesson=self.assignment).exists())

    def test_submit_rejects_empty_and_non_assignment(self):
        res = self._submit(text='   ')
        self.assertEqual(res.status_code, 400)
        text_lesson = Lesson.objects.create(
            module=self.module, title='T', lesson_type='text', order=2,
        )
        self.client.force_authenticate(self.learner)
        res = self.client.post(
            f'/api/courses/{self.course.id}/lessons/{text_lesson.id}/submit-assignment/',
            {'text': 'x'}, format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_lesson_detail_includes_submission(self):
        self._submit()
        res = self.client.get(f'/api/courses/{self.course.id}/lessons/{self.assignment.id}/')
        self.assertEqual(res.data['assignment_submission']['status'], 'pending')

    def test_queue_scoping(self):
        self._submit()
        self.client.force_authenticate(self.creator)
        self.assertEqual(len(self.client.get('/api/reviews/').data), 1)
        self.client.force_authenticate(self.other_creator)
        self.assertEqual(len(self.client.get('/api/reviews/').data), 0)
        self.client.force_authenticate(self.partner)
        self.assertEqual(len(self.client.get('/api/reviews/').data), 1)
        self.client.force_authenticate(self.learner)
        self.assertEqual(self.client.get('/api/reviews/').status_code, 403)

    def test_approve_completes_lesson_and_progress(self):
        self._submit()
        sub = AssignmentSubmission.objects.get(user=self.learner, lesson=self.assignment)
        self.client.force_authenticate(self.creator)
        res = self.client.post(f'/api/reviews/{sub.id}/', {'action': 'approve'}, format='json')
        self.assertEqual(res.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'approved')
        self.assertEqual(sub.reviewed_by, self.creator)
        from hub.models import LessonProgress
        lp = LessonProgress.objects.get(user=self.learner, lesson=self.assignment)
        self.assertEqual(lp.engagement_data.get('word_count'), 3)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.progress_pct, 100)

    def test_request_changes_requires_feedback_then_resubmit(self):
        self._submit()
        sub = AssignmentSubmission.objects.get(user=self.learner, lesson=self.assignment)
        self.client.force_authenticate(self.partner)
        res = self.client.post(f'/api/reviews/{sub.id}/', {'action': 'request_changes', 'feedback': ''}, format='json')
        self.assertEqual(res.status_code, 400)
        res = self.client.post(
            f'/api/reviews/{sub.id}/', {'action': 'request_changes', 'feedback': 'Add sources.'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'changes_requested')

        res = self._submit(text='Better essay with sources')  # resubmit
        self.assertEqual(res.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'pending')
        self.assertEqual(sub.feedback, 'Add sources.')  # history preserved

    def test_other_creator_cannot_review_foreign_course(self):
        self._submit()
        sub = AssignmentSubmission.objects.get(user=self.learner, lesson=self.assignment)
        self.client.force_authenticate(self.other_creator)
        res = self.client.post(f'/api/reviews/{sub.id}/', {'action': 'approve'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_review_non_pending_rejected(self):
        self._submit()
        sub = AssignmentSubmission.objects.get(user=self.learner, lesson=self.assignment)
        self.client.force_authenticate(self.creator)
        self.client.post(f'/api/reviews/{sub.id}/', {'action': 'approve'}, format='json')
        res = self.client.post(f'/api/reviews/{sub.id}/', {'action': 'approve'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_submit_after_approval_rejected(self):
        self._submit()
        sub = AssignmentSubmission.objects.get(user=self.learner, lesson=self.assignment)
        self.client.force_authenticate(self.creator)
        self.client.post(f'/api/reviews/{sub.id}/', {'action': 'approve'}, format='json')
        res = self._submit(text='another try')
        self.assertEqual(res.status_code, 400)
```

Run → FAIL (404s).

- [ ] **Step 2: Serializers — `backend/hub/serializers/assignments.py`**

```python
from rest_framework import serializers

from hub.models import AssignmentSubmission


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AssignmentSubmission
        fields = ['id', 'status', 'text', 'feedback', 'submitted_at', 'reviewed_at']


class ReviewQueueSerializer(serializers.ModelSerializer):
    learner_name = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='lesson.module.course.title', read_only=True)
    course_id    = serializers.IntegerField(source='lesson.module.course.id', read_only=True)
    module_title = serializers.CharField(source='lesson.module.title', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)

    class Meta:
        model  = AssignmentSubmission
        fields = ['id', 'learner_name', 'course_id', 'course_title', 'module_title',
                  'lesson_title', 'text', 'feedback', 'submitted_at']

    def get_learner_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
```

Follow the serializers package's re-export convention.

- [ ] **Step 3: Permission — append to `backend/hub/views/permissions.py`**

```python
class IsReviewer(BasePermission):
    """Course creators, AIDEA Partners, and admins may review assignment submissions."""

    def has_permission(self, request, view):
        profile = getattr(request.user, 'profile', None)
        return (
            request.user.is_authenticated
            and profile is not None
            and profile.user_type in (
                UserProfile.UserType.CONTENT_CREATOR,
                UserProfile.UserType.AIDEA_PARTNER,
                UserProfile.UserType.ADMIN,
            )
        )
```

- [ ] **Step 4: Views — `backend/hub/views/assignments.py`**

```python
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import AssignmentSubmission, Course, Enrollment, Lesson, UserProfile
from hub.serializers.assignments import AssignmentSubmissionSerializer, ReviewQueueSerializer

from .permissions import IsReviewer


def _reviewer_scope(queryset, user):
    """Creators see their own courses' submissions; partners/admins see all."""
    if user.profile.user_type == UserProfile.UserType.CONTENT_CREATOR:
        return queryset.filter(lesson__module__course__created_by=user)
    return queryset


class AssignmentSubmitView(APIView):
    """POST /courses/<pk>/lessons/<lesson_pk>/submit-assignment/ — learner submits/resubmits."""

    def post(self, request, pk, lesson_pk):
        if not Enrollment.objects.filter(user=request.user, course_id=pk).exists():
            if not Course.objects.filter(pk=pk).exists():
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            lesson = Lesson.objects.select_related('module').get(pk=lesson_pk, module__course_id=pk)
        except Lesson.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if lesson.lesson_type != 'assignment':
            return Response(
                {'detail': 'Only assignment lessons accept submissions.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        text = str(request.data.get('text', '')).strip()
        if not text:
            return Response({'detail': 'text is required.'}, status=status.HTTP_400_BAD_REQUEST)

        submission = AssignmentSubmission.objects.filter(user=request.user, lesson=lesson).first()
        if submission and submission.status == AssignmentSubmission.Status.APPROVED:
            return Response(
                {'detail': 'This assignment is already approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if submission:
            submission.text = text
            submission.status = AssignmentSubmission.Status.PENDING
            submission.save(update_fields=['text', 'status', 'updated_at'])
            created = False
        else:
            submission = AssignmentSubmission.objects.create(
                user=request.user, lesson=lesson, text=text,
            )
            created = True

        if lesson.module.llm_review_enabled:
            from hub.llm_review import review_submission
            review_submission(submission)  # stub: returns None, humans review

        return Response(
            AssignmentSubmissionSerializer(submission).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ReviewQueueView(APIView):
    permission_classes = [IsReviewer]

    def get(self, request):
        queryset = _reviewer_scope(
            AssignmentSubmission.objects.filter(status=AssignmentSubmission.Status.PENDING)
            .select_related('user', 'lesson__module__course'),
            request.user,
        )
        return Response(ReviewQueueSerializer(queryset, many=True).data)


class ReviewActionView(APIView):
    permission_classes = [IsReviewer]

    def post(self, request, pk):
        try:
            submission = AssignmentSubmission.objects.select_related(
                'user', 'lesson__module__course',
            ).get(pk=pk)
        except AssignmentSubmission.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        course = submission.lesson.module.course
        if (
            request.user.profile.user_type == UserProfile.UserType.CONTENT_CREATOR
            and course.created_by_id != request.user.id
        ):
            return Response(
                {'detail': 'You can only review submissions to your own courses.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if submission.status != AssignmentSubmission.Status.PENDING:
            return Response(
                {'detail': 'Only pending submissions can be reviewed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = request.data.get('action')
        feedback = str(request.data.get('feedback', '')).strip()

        if action == 'approve':
            enrollment = Enrollment.objects.filter(user=submission.user, course=course).first()
            if enrollment is None:
                return Response(
                    {'detail': 'The learner is no longer enrolled in this course.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            submission.status = AssignmentSubmission.Status.APPROVED
            if feedback:
                submission.feedback = feedback
            submission.reviewed_by = request.user
            submission.reviewed_at = timezone.now()
            submission.save()

            from hub.completion import record_lesson_completion
            record_lesson_completion(
                submission.user, enrollment, submission.lesson,
                engagement_data={'submission': submission.text},
            )
        elif action == 'request_changes':
            if not feedback:
                return Response(
                    {'detail': 'feedback is required when requesting changes.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            submission.status = AssignmentSubmission.Status.CHANGES_REQUESTED
            submission.feedback = feedback
            submission.reviewed_by = request.user
            submission.reviewed_at = timezone.now()
            submission.save()
        else:
            return Response(
                {'detail': "action must be 'approve' or 'request_changes'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(AssignmentSubmissionSerializer(submission).data)
```

- [ ] **Step 5: Lesson detail payload** — in `LessonDetailView.get` (learner.py), alongside `quiz_review`, add:

```python
        assignment_submission = None
        if lesson.lesson_type == 'assignment':
            from hub.models import AssignmentSubmission
            from hub.serializers.assignments import AssignmentSubmissionSerializer
            sub = AssignmentSubmission.objects.filter(user=request.user, lesson=lesson).first()
            if sub:
                assignment_submission = AssignmentSubmissionSerializer(sub).data
```

and include `'assignment_submission': assignment_submission,` in the response dict.

- [ ] **Step 6: Routes** (`urls.py`; export views in `__init__.py`):

```python
    path('courses/<int:pk>/lessons/<int:lesson_pk>/submit-assignment/', AssignmentSubmitView.as_view(), name='assignment-submit'),
    path('reviews/', ReviewQueueView.as_view(), name='review-queue'),
    path('reviews/<int:pk>/', ReviewActionView.as_view(), name='review-action'),
```

- [ ] **Step 7: GREEN, full suite (legacy-assignment-test rule from Task 2 applies), ruff, commit**

```bash
git add backend/hub
git commit -m "feat: assignment submission and review APIs with role-scoped queue"
```

---

### Task 4: LessonPage assignment states

**Files:**
- Modify: `frontend/src/pages/LessonPage.jsx`
- Modify: `frontend/src/pages/LessonPage.css`

**Interfaces:**
- Consumes: `assignment_submission` on lesson detail; submit endpoint (201/200 returns the submission payload)

- [ ] **Step 1: Rework `AssignmentLesson`** — replace the existing component (and remove the now-dead `onSubmissionChange`/`submissionText` plumbing from LessonPage — assignments no longer complete via `markComplete`):

```jsx
AssignmentLesson.propTypes = {
  lesson: lessonShape.isRequired,
  courseId: PropTypes.string.isRequired,
  onSubmissionChange: PropTypes.func.isRequired,  // receives the new submission payload
}
function AssignmentLesson({ lesson, courseId, onSubmissionChange }) {
  const submission = lesson.assignment_submission
  const [text, setText] = useState(submission?.text ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const status = submission?.status
  const locked = status === 'pending' || status === 'approved'

  const handleSubmit = async () => {
    if (!text.trim()) { setError('Write your response before submitting.'); return }
    setSubmitting(true)
    setError('')
    try {
      const res = await client.post(
        `/courses/${courseId}/lessons/${lesson.id}/submit-assignment/`, { text },
      )
      onSubmissionChange(res.data)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Submission failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="lp-content-card">
      <div className="lp-assignment-body">
        <h3 className="lp-assignment-heading">Instructions</h3>
        <p className="lp-text-content">{lesson.content || 'No instructions provided.'}</p>

        {status === 'pending' && (
          <div className="lp-assignment-banner lp-assignment-banner--pending">
            Submitted — pending review. You will see feedback here once it is reviewed.
          </div>
        )}
        {status === 'approved' && (
          <div className="lp-assignment-banner lp-assignment-banner--approved">
            Approved{submission.feedback ? ` — ${submission.feedback}` : ''} ✓
          </div>
        )}
        {status === 'changes_requested' && (
          <div className="lp-assignment-banner lp-assignment-banner--changes">
            <strong>Changes requested:</strong> {submission.feedback}
          </div>
        )}

        <h3 className="lp-assignment-heading lp-assignment-heading--response">Your Response</h3>
        <textarea
          className="lp-notes-input"
          placeholder="Write your response here…"
          value={text}
          disabled={locked || submitting}
          onChange={(e) => setText(e.target.value)}
        />
        {error && <p className="lp-assignment-error">{error}</p>}
        {!locked && (
          <button
            type="button"
            className="lp-complete-btn lp-assignment-submit"
            disabled={submitting}
            onClick={handleSubmit}
          >
            {submitting
              ? 'Submitting…'
              : status === 'changes_requested' ? 'Resubmit for review' : 'Submit for review'}
          </button>
        )}
      </div>
    </div>
  )
}
```

Wiring in LessonPage:
- `LessonContent` passes `courseId` and `onSubmissionChange` to AssignmentLesson: `case 'assignment': return <AssignmentLesson lesson={lesson} courseId={courseId} onSubmissionChange={onSubmissionChange} />` (add the prop to LessonContent's propTypes/signature)
- In `LessonPage`, define `const handleSubmissionChange = (sub) => setLesson(prev => ({ ...prev, assignment_submission: sub }))` and pass it down; delete the old `submissionText` state, its `useEffect` reset, and the assignment branch in `handleMarkComplete`
- Hide the Mark Complete button for assignments like quizzes: change the condition to `lesson.lesson_type !== 'quiz' && lesson.lesson_type !== 'assignment'`; next to it, for assignments show `{lesson.lesson_type === 'assignment' && lesson.is_completed && (<span className="lp-complete-btn lp-complete-btn--done">✓ Completed</span>)}` and for a pending submission a muted `Pending review` pill (reuse `lp-complete-btn` styling, disabled look)
- Extend `lessonShape` with `assignment_submission: PropTypes.object`

- [ ] **Step 2: CSS (`LessonPage.css`)**

```css
.lp-assignment-banner {
  border-radius: 8px;
  padding: 0.7rem 0.9rem;
  font-size: 0.88rem;
  margin: 0.75rem 0;
}
.lp-assignment-banner--pending  { background: #fef9c3; color: #854d0e; }
.lp-assignment-banner--approved { background: #dcfce7; color: #166534; }
.lp-assignment-banner--changes  { background: #fee2e2; color: #991b1b; }
.lp-assignment-error { color: #b91c1c; font-size: 0.85rem; margin: 0.5rem 0 0; }
.lp-assignment-submit { margin-top: 0.75rem; }
```

- [ ] **Step 3: Verify + commit**

`cd frontend && npm run lint && npm run build`

```bash
git add frontend/src/pages/LessonPage.jsx frontend/src/pages/LessonPage.css
git commit -m "feat: assignment submission states in the lesson player"
```

---

### Task 5: ReviewsPage + routing + sidebar + admin role option

**Files:**
- Create: `frontend/src/pages/ReviewsPage.jsx`, `frontend/src/pages/ReviewsPage.css`
- Modify: `frontend/src/App.jsx` (route + guard)
- Modify: `frontend/src/components/layout/Sidebar.jsx`
- Modify: `frontend/src/pages/AdminPage.jsx` (role options + ROLE_ORDER)

**Interfaces:**
- Consumes: `GET /api/reviews/`, `POST /api/reviews/<id>/`

- [ ] **Step 1: `frontend/src/pages/ReviewsPage.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { ClipboardCheck, ChevronDown, ChevronUp } from 'lucide-react'
import PropTypes from 'prop-types'
import client from '../api/client'
import './ReviewsPage.css'

SubmissionRow.propTypes = {
  sub: PropTypes.object.isRequired,
  onDone: PropTypes.func.isRequired,
}

function SubmissionRow({ sub, onDone }) {
  const [openRow, setOpenRow] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const act = async (action) => {
    if (action === 'request_changes' && !feedback.trim()) {
      setError('Write feedback before requesting changes.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await client.post(`/reviews/${sub.id}/`, { action, feedback })
      onDone(sub.id)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Action failed. Please try again.')
      setBusy(false)
    }
  }

  return (
    <div className="rv-row">
      <button type="button" className="rv-row-head" onClick={() => setOpenRow(o => !o)}>
        <div className="rv-row-title">
          <span className="rv-learner">{sub.learner_name}</span>
          <span className="rv-meta">{sub.course_title} · {sub.module_title} · {sub.lesson_title}</span>
        </div>
        <span className="rv-date">{new Date(sub.submitted_at).toLocaleDateString()}</span>
        {openRow ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {openRow && (
        <div className="rv-row-body">
          <p className="rv-text">{sub.text}</p>
          {sub.feedback && (
            <p className="rv-prev-feedback"><strong>Previous feedback:</strong> {sub.feedback}</p>
          )}
          <textarea
            className="rv-feedback-input"
            placeholder="Feedback for the learner (required to request changes, optional on approve)…"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
          />
          {error && <p className="rv-error">{error}</p>}
          <div className="rv-actions">
            <button type="button" className="rv-btn rv-btn--changes" disabled={busy} onClick={() => act('request_changes')}>
              Request changes
            </button>
            <button type="button" className="rv-btn rv-btn--approve" disabled={busy} onClick={() => act('approve')}>
              {busy ? 'Working…' : 'Approve'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ReviewsPage() {
  const [subs, setSubs] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get('/reviews/')
      .then(res => setSubs(res.data))
      .catch(() => setError('Failed to load the review queue.'))
  }, [])

  if (error) return <p className="page-error">{error}</p>
  if (!subs) return <p className="page-loading">Loading…</p>

  return (
    <div className="reviews-page">
      <div className="rv-header">
        <ClipboardCheck size={22} className="rv-header-icon" />
        <div>
          <h1>Assignment Reviews</h1>
          <p className="rv-sub">Submissions waiting for your review</p>
        </div>
      </div>

      {subs.length === 0
        ? <p className="rv-empty">No submissions waiting for review. 🎉</p>
        : subs.map(sub => (
            <SubmissionRow key={sub.id} sub={sub} onDone={(id) => setSubs(prev => prev.filter(s => s.id !== id))} />
          ))}
    </div>
  )
}
```

- [ ] **Step 2: `ReviewsPage.css`**

```css
.reviews-page { max-width: 860px; }
.rv-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.25rem; }
.rv-header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
.rv-header-icon { color: var(--color-primary); }
.rv-sub { font-size: 0.875rem; color: var(--color-text-muted); margin: 0.15rem 0 0; }
.rv-empty { color: var(--color-text-muted); }

.rv-row {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 10px);
  margin-bottom: 0.75rem;
  overflow: hidden;
}
.rv-row-head {
  display: flex; align-items: center; gap: 0.75rem;
  width: 100%; padding: 0.9rem 1.1rem;
  background: none; border: 0; cursor: pointer; text-align: left;
}
.rv-row-title { flex: 1; min-width: 0; }
.rv-learner { display: block; font-weight: 600; }
.rv-meta { display: block; font-size: 0.8rem; color: var(--color-text-muted); }
.rv-date { font-size: 0.8rem; color: var(--color-text-muted); }

.rv-row-body { border-top: 1px solid var(--color-border); padding: 1rem 1.1rem; }
.rv-text { white-space: pre-wrap; font-size: 0.9rem; margin: 0 0 0.75rem; }
.rv-prev-feedback { font-size: 0.85rem; color: #92400e; background: #fef9c3; border-radius: 6px; padding: 0.5rem 0.7rem; }
.rv-feedback-input {
  width: 100%; min-height: 70px; box-sizing: border-box;
  border: 1px solid var(--color-border); border-radius: 8px;
  padding: 0.6rem 0.75rem; font-size: 0.88rem; font-family: inherit;
}
.rv-error { color: #b91c1c; font-size: 0.85rem; margin: 0.4rem 0 0; }
.rv-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.75rem; }
.rv-btn { padding: 0.5rem 1rem; border-radius: 8px; border: 0; font-size: 0.875rem; cursor: pointer; }
.rv-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.rv-btn--approve { background: var(--color-primary); color: #fff; }
.rv-btn--changes { background: none; border: 1px solid #b91c1c; color: #b91c1c; }
```

- [ ] **Step 3: Route + guard (`App.jsx`)**

```jsx
const REVIEWER_TYPES = ['content_creator', 'aidea_partner', 'admin']

ReviewerRoute.propTypes = { element: PropTypes.node.isRequired }

function ReviewerRoute({ element }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (!REVIEWER_TYPES.includes(user.profile?.user_type)) return <Navigate to="/" replace />
  return element
}
```

Route inside the Layout group: `<Route path="/reviews" element={<ReviewerRoute element={<ReviewsPage />} />} />` (+ import).

- [ ] **Step 4: Sidebar (`Sidebar.jsx`)** — add `ClipboardCheck` to the lucide import and:

```jsx
const REVIEWS_ITEM = { to: '/reviews', label: 'Reviews', Icon: ClipboardCheck }
```

Nav logic becomes:

```jsx
  let navItems
  if (userType === 'admin') {
    navItems = [...BASE_NAV.filter(item => item.to !== '/pathway'), REVIEWS_ITEM, ADMIN_ITEM]
  } else if (userType === 'content_creator') {
    navItems = [...BASE_NAV.filter(item => item.to !== '/pathway'), REVIEWS_ITEM, AUTHORING_ITEM]
  } else if (userType === 'aidea_partner') {
    navItems = [
      ...BASE_NAV.filter(item => ['/', '/courses', '/profile'].includes(item.to)),
      REVIEWS_ITEM,
    ]
  } else {
    navItems = BASE_NAV
  }
```

(Keep Reviews before Authoring/Admin; partner nav = Home, Courses, Reviews, Profile.)

- [ ] **Step 5: AdminPage role options** — in both `<select>`s add `<option value="aidea_partner">AIDEA Partner</option>` after Content Creator, and update `ROLE_ORDER` to `{ admin: 0, content_creator: 1, aidea_partner: 2, teacher: 3 }`.

- [ ] **Step 6: Verify + commit**

`cd frontend && npm run lint && npm run build`

```bash
git add frontend/src
git commit -m "feat: reviews queue page, partner navigation, admin role option"
```

---

### Final verification

- [ ] `cd backend && uv.exe run coverage run manage.py test hub analytics -v 1` — green, ≥70%
- [ ] `uv.exe run ruff check .` — clean
- [ ] `cd frontend && npm run lint && npm run build` — clean
- [ ] Dispatch final whole-branch code review

## Deployment notes

Migration required (`0023_assignment_review`): on the VM `git pull`,
`docker compose up -d`, `docker compose exec backend uv run python manage.py migrate`,
and `docker compose exec backend uv run python manage.py seed` (adds demo_partner).
Existing tester accounts keep their roles; create partners via the app's
Admin page or Django admin. Old completed assignments remain completed.
