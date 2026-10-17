# AI Assignment Reviewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A self-hosted AI reviewer that pre-checks assignment submissions against an author-approved criteria rubric, shows its suggestion to reviewers (and optionally learners), auto-approves proven clear passes, and records every human decision for measurement and future training.

**Architecture:**
- Per-assignment settings live in `AssignmentReviewConfig`. Each run is an `AIReview` row, processed by a Celery task that runs these steps in order:
  1. gather the evidence (`hub/ai_review/evidence.py`: text, PDF and Word text, images, fingerprints for duplicate checks);
  2. ask the NTUA Ollama model through `/api/chat` with a JSON-schema `format` (`hub/ai_review/model.py`);
  3. validate the answer, store it, and possibly auto-approve through a shared approval function (`hub/ai_review/pipeline.py`).
- The Reviews page, the activity editor, the learner's assignment view and analytics read these rows.

**Tech Stack:** Django 5 + DRF, Celery, Ollama `/api/chat` (structured outputs, images), Pillow (already installed), `pypdf` and `python-docx` (new), React 19.

**Spec:** `docs/superpowers/specs/2026-10-16-ai-assignment-review-design.md` (its *Methodology* section lists the research each part draws on)

## Global Constraints

- **Model:** self-hosted only, through the existing Ollama tunnel (`hub.translation.OLLAMA_URL` / `OLLAMA_HOST_HEADER`). The model name is set in `AIReviewSettings.model_name` (default `qwen2.5vl:32b`). No hosted APIs.
- **Rubric:** criteria `{id, name, met, required}`. AI review runs only when the platform switch is on, the assignment's AI review is on, and its rubric is approved.
- **Verdicts:** `approve` / `changes_requested` / `unsure`. Criterion statuses: `met` / `partly_met` / `not_met` / `cannot_judge`. Confidence is 0–1.
- **Auto-approve:**
  - approvals only;
  - unlocked when the assignment has ≥ `unlock_min_reviews` (30) human-decided AI reviews, **and** the 95% Wilson lower bound of the share of the AI's *approve* suggestions that humans approved is ≥ `unlock_min_lower_bound` (0.90). With no disagreements at all this needs 35 approvals;
  - requires verdict `approve`, confidence ≥ `confidence_threshold` (0.8), every required criterion `met`, and no duplicate flag;
  - `spot_check_rate` (0.1) of eligible submissions stay pending for a human;
  - rejections are always human.
- **Measurement:**
  - agreement is always reported with Cohen's kappa (chance-corrected, over approve / changes-requested pairs) next to raw agreement;
  - every human decision records whether the reviewer started from the AI's feedback (`feedback_used`) and how close the sent feedback is to it (`feedback_similarity`, `difflib.SequenceMatcher` ratio, 1.0 = unchanged; "unchanged" means ≥ 0.95);
  - all statistics come from one module, `hub/ai_review/metrics.py`, used by the pipeline, the authoring API and analytics.
- **Failures never block:** a model error or the server being offline leaves the submission pending for humans, exactly as today.
- **Learner-visible feedback** is per assignment, default off. Learners may resubmit while their submission is pending.
- **Training data:** anonymised, excluding learners with `UserProfile.ai_training_opt_out`.
- **Tests never call Ollama:** mock `hub.ai_review.model._chat`.
- Keep all 9 locales in sync (`npm run check:locales`). Icons from `lucide-react` only. Per-component CSS.
- **Runner:** from `backend/`, set `UV="/c/Users/Nikos A. Grammatikos/.local/bin/uv.exe"`, then use `"$UV" run manage.py …` and `"$UV" run ruff check hub analytics`. Frontend ESLint is ES2020 (no numeric separators), and `Date.now()` stays out of component bodies.
- Keep each file's line endings. Work on `master`; commit and push after each task. Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **The model returns nonsense:** wrong criterion ids, unknown statuses, confidence outside 0–1, extra prose around the JSON. It must be retried once and then marked *failed*, never crash, and never auto-approve. Pinned by Task 3 `test_parse_rejects_*` and Task 4 `test_malformed_answer_twice_marks_failed`.
2. **Auto-approve firing when it shouldn't:** still locked, low confidence, a required criterion not `met`, a duplicate flag, a spot check, or the platform switch off. Pinned by Task 4's auto-approve tests (one per rule).
3. **The NTUA server is offline or slow:** the submission stays pending, the task retries with back-off, then gives up as *failed*. Pinned by Task 4 `test_offline_is_retried_then_failed`.
4. **Attachment paths:** an attachment URL pointing outside `MEDIA_ROOT`, a missing file, a non-image renamed `.png`, or a corrupt PDF must be skipped, not crash or read arbitrary files. Pinned by Task 2 `test_media_path_*` and `test_corrupt_files_are_skipped`.
5. **Learner privacy:** examples made from real submissions must not carry the learner's name or email, and opted-out learners must never appear in the training export. Pinned by Task 6 `test_example_from_submission_is_anonymised` and Task 8 `test_export_excludes_opted_out`.

---

## File Structure

**Backend**
- `hub/models/ai_review.py` (new): `AIReviewSettings`, `AssignmentReviewConfig`, `ReviewExample`, `AIReview`.
- `hub/models/user.py`: `ai_training_opt_out`.
- `hub/models/__init__.py`, `hub/admin.py`, `hub/migrations/0064_ai_review.py` (generated) and `0065_ai_review_from_module_flag.py` (data migration).
- `hub/ai_review/__init__.py`, `evidence.py`, `model.py`, `pipeline.py` (new).
- `hub/assignment_review.py` (new): `approve_submission`, `request_changes`, `reopen_submission` (shared by humans and the AI).
- `hub/tasks.py`: `run_ai_review`, `translate_review_criteria`.
- `hub/views/assignments.py`: queue on submit; reviewer AI data, filters, verdict recording, examples, reopen.
- `hub/views/ai_review.py` (new): authoring config, draft, examples.
- `hub/serializers/assignments.py`: AI data for reviewers and learners.
- `hub/serializers/profile.py`: opt-out in `ProfileSettingsSerializer`.
- `hub/urls.py`.
- `hub/llm_review.py`: removed.
- `analytics/learning.py`, `analytics/workbook.py`.
- `hub/management/commands/ai_review_benchmark.py` and `ai_review_export.py` (new).
- `pyproject.toml` and `uv.lock`: `pypdf`, `python-docx`.
- Tests: `hub/tests/test_ai_review_*.py` (new), `analytics/tests/test_ai_review_analytics.py` (new).

**Frontend**
- `src/components/authoring/AIReviewPanel.jsx` and `.css` (new); `ResourceEditor.jsx` (shows it for assignments).
- `src/pages/ReviewsPage.jsx` and `.css` (AI panel, filters, examples, reopen).
- `src/components/reviews/aiReview.js` and `aiReview.test.js` (new): pure helpers.
- `src/components/learner/ResourceView.jsx` (pre-check box; pending no longer locked).
- `src/components/analytics/ContentTree.jsx` and `LearnerTimeline.jsx`.
- `src/pages/ProfilePage.jsx` (opt-out toggle), `src/pages/PrivacyPage.jsx`.
- `src/locales/*.json`.

---

### Task 1: Models, settings, opt-out, migrations

**Files:**
- Create: `backend/hub/models/ai_review.py`
- Modify: `backend/hub/models/user.py`, `backend/hub/models/__init__.py`, `backend/hub/admin.py`
- Create: `backend/hub/migrations/0064_ai_review.py` (generated), `backend/hub/migrations/0065_ai_review_from_module_flag.py`
- Test: `backend/hub/tests/test_ai_review_models.py`

**Interfaces — Produces:**
- `AIReviewSettings.get()`, with fields `enabled`, `model_name`, `confidence_threshold`, `spot_check_rate`, `unlock_min_reviews` and `unlock_min_lower_bound`.
- `AssignmentReviewConfig`:
  - `resource` (OneToOne, `related_name='ai_review_config'`);
  - `enabled`, `criteria` (a list of `{id, name, met, required}`), `rubric_approved`, `criteria_translations` (`{lang: {id: name}}`);
  - `learner_visible`, `auto_approve`, `duplicate_check`;
  - `is_ready()` (enabled, approved, and with criteria).
- `ReviewExample`: `resource` (`related_name='ai_review_examples'`), `text`, `image_path`, `verdict`, `reason`, `source_submission`, `created_by`, `created_at`.
- `AIReview`: `submission` (`related_name='ai_reviews'`), `status` (`queued`/`running`/`done`/`failed`), `model_name`, `prompt_version`, `rubric`, `checks`, `criteria_results`, `verdict`, `confidence`, `learner_feedback`, `reviewer_notes`, `error`, `attempts`, `created_at`, `finished_at`, `duration_s`, `auto_approved`, `spot_check`, `human_verdict`, `agreed`, `disagreement_reason`, `feedback_used`, `feedback_similarity`. Properties `flagged` and `resource`.
- `AIReview.Verdict` (`APPROVE`, `CHANGES`, `UNSURE`), `AIReview.DISAGREEMENT_REASONS`.
- `UserProfile.ai_training_opt_out`.

- [ ] **Step 1: Write the failing test.** `backend/hub/tests/test_ai_review_models.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import (
    Activity,
    AIReview,
    AIReviewSettings,
    AssignmentReviewConfig,
    AssignmentSubmission,
    Course,
    LearningPillar,
    Module,
    Resource,
    UserProfile,
)


def make_assignment(title='AI course'):
    pillar = LearningPillar.objects.get_or_create(slug='p-air', defaults={'name': 'P', 'order': 1})[0]
    course = Course.objects.create(title=title, pillar=pillar, level='beginner', duration_hours=1, is_published=True)
    module = Module.objects.create(course=course, title='M', order=1)
    activity = Activity.objects.create(module=module, title='Task', order=1)
    resource = Resource.objects.create(activity=activity, type='assignment', order=1,
                                       instructions='<p>Describe three AI risks.</p>')
    return course, module, activity, resource


class AIReviewModelTests(TestCase):
    def test_settings_singleton_defaults(self):
        s = AIReviewSettings.get()
        self.assertEqual((s.enabled, s.model_name, s.confidence_threshold, s.spot_check_rate,
                          s.unlock_min_reviews, s.unlock_min_lower_bound),
                         (False, 'qwen2.5vl:32b', 0.8, 0.1, 30, 0.9))
        self.assertEqual(AIReviewSettings.get().pk, s.pk)

    def test_config_ready_only_when_enabled_approved_with_criteria(self):
        *_, resource = make_assignment()
        config = AssignmentReviewConfig.objects.create(resource=resource)
        self.assertFalse(config.is_ready())
        config.enabled = True
        config.criteria = [{'id': 'c1', 'name': 'Risks', 'met': 'Names 3 risks', 'required': True}]
        self.assertFalse(config.is_ready())
        config.rubric_approved = True
        self.assertTrue(config.is_ready())
        self.assertTrue(config.duplicate_check)
        self.assertFalse(config.learner_visible or config.auto_approve)

    def test_ai_review_flagged_and_resource(self):
        *_, activity, resource = make_assignment()
        user = User.objects.create_user('air_l', password='x')
        UserProfile.objects.create(user=user)
        sub = AssignmentSubmission.objects.create(user=user, lesson=activity, resource=resource, text='t')
        review = AIReview.objects.create(submission=sub, rubric=[])
        self.assertEqual((review.status, review.flagged, review.resource), ('queued', False, resource))
        review.checks = {'duplicates': [{'submission_id': 9}]}
        self.assertTrue(review.flagged)

    def test_opt_out_default(self):
        user = User.objects.create_user('air_o', password='x')
        self.assertFalse(UserProfile.objects.create(user=user).ai_training_opt_out)
```

- [ ] **Step 2: Run the test to verify it fails.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_models -v 2`
  - Expected: ImportError, `cannot import name 'AIReview'`.

- [ ] **Step 3: Implement.** `backend/hub/models/ai_review.py`:

```python
"""AI assignment reviewer — see docs/superpowers/specs/2026-10-16-ai-assignment-review-design.md."""
from django.contrib.auth.models import User
from django.db import models


class AIReviewSettings(models.Model):
    """Platform-wide switch and thresholds (singleton, edited in Django admin)."""
    enabled              = models.BooleanField(default=False)
    model_name           = models.CharField(max_length=100, default='qwen2.5vl:32b')
    confidence_threshold = models.FloatField(default=0.8)
    spot_check_rate      = models.FloatField(default=0.1)
    unlock_min_reviews   = models.PositiveIntegerField(default=30)
    # Auto-approve unlocks when the 95% Wilson lower bound of agreement on the
    # AI's approvals reaches this (0.9 needs at least 35 agreeing approvals).
    unlock_min_lower_bound = models.FloatField(default=0.9)

    class Meta:
        verbose_name = verbose_name_plural = 'AI review settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def __str__(self):
        return 'AI review settings'


class AssignmentReviewConfig(models.Model):
    """One assignment's AI review set-up: rubric, examples policy, visibility."""
    resource              = models.OneToOneField('hub.Resource', on_delete=models.CASCADE, related_name='ai_review_config')
    enabled               = models.BooleanField(default=False)
    criteria              = models.JSONField(default=list, blank=True)   # [{id, name, met, required}]
    rubric_approved       = models.BooleanField(default=False)
    criteria_translations = models.JSONField(default=dict, blank=True)   # {lang: {criterion id: name}}
    learner_visible       = models.BooleanField(default=False)
    auto_approve          = models.BooleanField(default=False)
    duplicate_check       = models.BooleanField(default=True)
    updated_at            = models.DateTimeField(auto_now=True)

    def is_ready(self):
        return self.enabled and self.rubric_approved and bool(self.criteria)

    def __str__(self):
        return f'AI review config for resource {self.resource_id}'


class ReviewExample(models.Model):
    """A sample submission with its correct verdict, shown to the model."""
    resource          = models.ForeignKey('hub.Resource', on_delete=models.CASCADE, related_name='ai_review_examples')
    text              = models.TextField(blank=True)
    image_path        = models.CharField(max_length=500, blank=True)  # reserved: image examples come later
    verdict           = models.CharField(max_length=20, choices=[('approve', 'Approve'), ('changes_requested', 'Changes requested')])
    reason            = models.TextField(blank=True)
    source_submission = models.ForeignKey('hub.AssignmentSubmission', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_by        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class AIReview(models.Model):
    """One AI review of one submission version."""
    class Status(models.TextChoices):
        QUEUED  = 'queued',  'Queued'
        RUNNING = 'running', 'Running'
        DONE    = 'done',    'Done'
        FAILED  = 'failed',  'Failed'

    class Verdict(models.TextChoices):
        APPROVE = 'approve',           'Approve'
        CHANGES = 'changes_requested', 'Changes requested'
        UNSURE  = 'unsure',            'Unsure'

    DISAGREEMENT_REASONS = ('missed_evidence', 'too_strict', 'too_lenient', 'misread_image', 'other')

    submission          = models.ForeignKey('hub.AssignmentSubmission', on_delete=models.CASCADE, related_name='ai_reviews')
    status              = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    model_name          = models.CharField(max_length=100, blank=True)
    prompt_version      = models.CharField(max_length=40, blank=True)
    rubric              = models.JSONField(default=list, blank=True)        # snapshot of the criteria used
    checks              = models.JSONField(default=dict, blank=True)        # {fingerprints: [...], duplicates: [...]}
    criteria_results    = models.JSONField(default=list, blank=True)        # [{id, status, reason}]
    verdict             = models.CharField(max_length=20, choices=Verdict.choices, blank=True)
    confidence          = models.FloatField(null=True, blank=True)
    learner_feedback    = models.TextField(blank=True)
    reviewer_notes      = models.TextField(blank=True)
    error               = models.TextField(blank=True)
    attempts            = models.PositiveSmallIntegerField(default=0)
    created_at          = models.DateTimeField(auto_now_add=True)
    finished_at         = models.DateTimeField(null=True, blank=True)
    duration_s          = models.FloatField(null=True, blank=True)
    auto_approved       = models.BooleanField(default=False)
    spot_check          = models.BooleanField(default=False)
    human_verdict       = models.CharField(max_length=20, blank=True)
    agreed              = models.BooleanField(null=True, blank=True)
    disagreement_reason = models.CharField(max_length=20, blank=True)
    feedback_used       = models.BooleanField(default=False)            # reviewer started from the AI's feedback
    feedback_similarity = models.FloatField(null=True, blank=True)     # 1.0 = sent unchanged

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['submission', 'status'])]

    @property
    def flagged(self):
        return bool((self.checks or {}).get('duplicates'))

    @property
    def resource(self):
        return self.submission.resource

    def __str__(self):
        return f'AI review {self.id} of submission {self.submission_id} ({self.status})'
```

`backend/hub/models/user.py`: add this to `UserProfile` after `share_progress`:

```python
    # Exclude this learner's assignments from AI-reviewer training data.
    ai_training_opt_out  = models.BooleanField(default=False)
```

`backend/hub/models/__init__.py`: add `from .ai_review import AIReview, AIReviewSettings, AssignmentReviewConfig, ReviewExample` (before `.assignment`), and add the four names to `__all__`.

`backend/hub/admin.py`:
- import `AIReview`, `AIReviewSettings` and `ReviewExample` from `.models`;
- register a settings admin like `LearnerActivityConfigAdmin` (no add once one exists, no delete);
- register read-only admins for `AIReview` (`list_display = ['submission', 'status', 'verdict', 'confidence', 'auto_approved', 'agreed', 'created_at']`, `list_filter = ['status', 'verdict', 'auto_approved', 'agreed']`) and `ReviewExample`, reusing the existing `_ReadOnlyAdmin`.

Generate the schema migration with `"$UV" run manage.py makemigrations hub --name ai_review`. Expected: `0064_ai_review.py`.

Create the data migration `backend/hub/migrations/0065_ai_review_from_module_flag.py`:

```python
from django.db import migrations


def forwards(apps, schema_editor):
    """Assignments in modules that had the old LLM-review switch on start with
    AI review on (they still need an approved rubric before anything runs)."""
    Resource = apps.get_model('hub', 'Resource')
    Config = apps.get_model('hub', 'AssignmentReviewConfig')
    for resource in Resource.objects.filter(type='assignment', activity__module__llm_review_enabled=True):
        Config.objects.get_or_create(resource=resource, defaults={'enabled': True})


class Migration(migrations.Migration):
    dependencies = [('hub', '0064_ai_review')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
```

Run `"$UV" run manage.py migrate`.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_models -v 2`
  - Expected: 4 tests pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/models hub/admin.py hub/migrations/0064_ai_review.py hub/migrations/0065_ai_review_from_module_flag.py hub/tests/test_ai_review_models.py
git commit -m "feat: AI review models, settings and training opt-out"
git push
```

---

### Task 2: Evidence (text, documents, images, fingerprints, duplicates)

**Files:**
- Create: `backend/hub/ai_review/__init__.py` (empty) and `backend/hub/ai_review/evidence.py`
- Modify: `backend/pyproject.toml` and `uv.lock`, via `"$UV" add pypdf python-docx`
- Test: `backend/hub/tests/test_ai_review_evidence.py`

**Interfaces — Produces:**
- `media_path(url) -> Path | None`: the attachment's local file inside `MEDIA_ROOT`, else None.
- `extract_text(path) -> str`: handles `.pdf`, `.docx` and `.txt`; returns `''` on failure. Capped at `MAX_TEXT_CHARS`.
- `image_b64(path) -> str | None`: JPEG, longest side at most `MAX_IMAGE_SIDE`.
- `fingerprint(path) -> {'sha256', 'dhash'}`, where `dhash` is a 16-char hex string or `''`.
- `hamming(a, b) -> int`.
- `Evidence` dataclass: `text`, `documents` (a list of `{name, text}`), `images` (a list of `{name, b64}`), `links` (a list of strings), `fingerprints` (a list of `{name, sha256, dhash}`).
- `gather(submission) -> Evidence`.
- `find_duplicates(submission, fingerprints) -> list[{submission_id, learner, file, match}]`, where `match` is `'identical'` or `'similar'`.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_ai_review_evidence.py`:

```python
import tempfile
from pathlib import Path

import docx
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from PIL import Image, ImageDraw

from hub.ai_review import evidence
from hub.models import AIReview, AssignmentSubmission, UserProfile

from .test_ai_review_models import make_assignment

MEDIA = tempfile.mkdtemp(prefix='aidea-air-media-')

# Smallest PDF with one line of text ("Risk register") that pypdf can read.
PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 18 Tf 20 60 Td (Risk register) Tj ET
endstream endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
trailer<</Root 1 0 R>>
%%EOF"""


def write(name, data):
    path = Path(MEDIA) / 'submission_uploads' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data) if isinstance(data, bytes) else path.write_text(data)
    return path


def picture(name, shift=0, size=(400, 300)):
    img = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(img)
    draw.rectangle([50 + shift, 50, 250 + shift, 200], fill='navy')
    draw.ellipse([260, 60, 380, 180], fill='orange')
    path = Path(MEDIA) / 'submission_uploads' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def url(path):
    return f'http://testserver/media/{path.relative_to(MEDIA).as_posix()}'


@override_settings(MEDIA_ROOT=MEDIA, MEDIA_URL='/media/')
class EvidenceTests(TestCase):
    def setUp(self):
        *_, self.activity, self.resource = make_assignment()

    def submission(self, username, attachments, text=''):
        user = User.objects.create_user(username, password='x', first_name=username.title())
        UserProfile.objects.create(user=user)
        return AssignmentSubmission.objects.create(
            user=user, lesson=self.activity, resource=self.resource, text=text, attachments=attachments,
        )

    def test_media_path_inside_media_root_only(self):
        good = write('a.txt', 'hello')
        self.assertEqual(evidence.media_path(url(good)), good.resolve())
        self.assertIsNone(evidence.media_path('http://testserver/media/../../etc/passwd'))
        self.assertIsNone(evidence.media_path('https://youtube.com/watch?v=x'))
        self.assertIsNone(evidence.media_path('http://testserver/media/submission_uploads/missing.png'))

    def test_extract_text_from_pdf_docx_txt(self):
        doc = docx.Document()
        doc.add_paragraph('Mitigation plan')
        docx_path = Path(MEDIA) / 'submission_uploads' / 'plan.docx'
        doc.save(docx_path)
        self.assertIn('Risk register', evidence.extract_text(write('r.pdf', PDF)))
        self.assertIn('Mitigation plan', evidence.extract_text(docx_path))
        self.assertEqual(evidence.extract_text(write('n.txt', 'notes')), 'notes')

    def test_corrupt_files_are_skipped(self):
        self.assertEqual(evidence.extract_text(write('bad.pdf', b'not a pdf')), '')
        self.assertIsNone(evidence.image_b64(write('fake.png', b'not an image')))
        self.assertEqual(evidence.fingerprint(write('fake2.png', b'xx'))['dhash'], '')

    def test_images_are_resized_and_encoded(self):
        big = picture('big.png', size=(3000, 2000))
        encoded = evidence.image_b64(big)
        import base64
        import io
        with Image.open(io.BytesIO(base64.b64decode(encoded))) as img:
            self.assertLessEqual(max(img.size), evidence.MAX_IMAGE_SIDE)

    def test_gather_collects_everything(self):
        shot = picture('shot.png')
        pdf = write('report.pdf', PDF)
        sub = self.submission('ann', [
            {'type': 'image', 'url': url(shot), 'name': 'shot.png'},
            {'type': 'file', 'url': url(pdf), 'name': 'report.pdf'},
            {'type': 'video', 'url': 'https://youtu.be/x', 'name': 'demo'},
        ], text='My answer')
        ev = evidence.gather(sub)
        self.assertEqual(ev.text, 'My answer')
        self.assertEqual([i['name'] for i in ev.images], ['shot.png'])
        self.assertEqual([d['name'] for d in ev.documents], ['report.pdf'])
        self.assertEqual(ev.links, ['demo (https://youtu.be/x)'])
        self.assertEqual(len(ev.fingerprints), 2)

    def test_duplicates_identical_and_similar(self):
        original = picture('orig.png')
        same = write('copy.png', original.read_bytes())
        resized = picture('resized.png', shift=2)      # nearly the same picture
        other = self.submission('bob', [{'type': 'image', 'url': url(original), 'name': 'orig.png'}])
        AIReview.objects.create(submission=other, rubric=[], status='done',
                                checks={'fingerprints': [evidence.fingerprint(original) | {'name': 'orig.png'}]})
        mine = self.submission('cat', [])
        prints = [evidence.fingerprint(same) | {'name': 'copy.png'}, evidence.fingerprint(resized) | {'name': 'resized.png'}]
        dupes = evidence.find_duplicates(mine, prints)
        self.assertEqual({(d['file'], d['match']) for d in dupes}, {('copy.png', 'identical'), ('resized.png', 'similar')})
        self.assertEqual(dupes[0]['learner'], 'Bob')
        self.assertEqual(evidence.find_duplicates(other, prints), [])   # never against your own work
```

- [ ] **Step 2: Install the dependencies and run the tests to verify they fail.**
  - Run: `"$UV" add pypdf python-docx`, then `"$UV" run manage.py test hub.tests.test_ai_review_evidence -v 2`
  - Expected: ImportError, `cannot import name 'evidence'`.

- [ ] **Step 3: Implement.** `backend/hub/ai_review/evidence.py`:

```python
"""What the AI reviewer gets to see from a submission, and duplicate checks.

Only files inside MEDIA_ROOT are read (uploaded attachments); anything else is
treated as a link. Corrupt or unreadable files are skipped, never fatal."""
import base64
import hashlib
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from PIL import Image, UnidentifiedImageError

log = logging.getLogger(__name__)

MAX_IMAGE_SIDE = 1280
MAX_IMAGES = 6
MAX_TEXT_CHARS = 20000
DHASH_MAX_DISTANCE = 6
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}


@dataclass
class Evidence:
    text: str = ''
    documents: list = field(default_factory=list)
    images: list = field(default_factory=list)
    links: list = field(default_factory=list)
    fingerprints: list = field(default_factory=list)


def media_path(url):
    path = unquote(urlparse(str(url)).path)
    if not path.startswith(settings.MEDIA_URL):
        return None
    root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (root / path[len(settings.MEDIA_URL):]).resolve()
    if root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def extract_text(path):
    suffix = Path(path).suffix.lower()
    try:
        if suffix == '.pdf':
            from pypdf import PdfReader
            text = '\n'.join(page.extract_text() or '' for page in PdfReader(str(path)).pages)
        elif suffix == '.docx':
            import docx
            text = '\n'.join(p.text for p in docx.Document(str(path)).paragraphs)
        elif suffix == '.txt':
            text = Path(path).read_text(encoding='utf-8', errors='replace')
        else:
            return ''
    except Exception as exc:  # noqa: BLE001 — any parser failure means "no text"
        log.info('AI review: could not read %s: %s', path, exc)
        return ''
    return text.strip()[:MAX_TEXT_CHARS]


def image_b64(path):
    try:
        with Image.open(path) as img:
            img = img.convert('RGB')
            img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    return base64.b64encode(buffer.getvalue()).decode()


def _dhash(path):
    try:
        with Image.open(path) as img:
            small = img.convert('L').resize((9, 8))
    except (UnidentifiedImageError, OSError, ValueError):
        return ''
    pixels = list(small.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    return f'{bits:016x}'


def fingerprint(path):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    dhash = _dhash(path) if Path(path).suffix.lower() in IMAGE_SUFFIXES else ''
    return {'sha256': digest, 'dhash': dhash}


def hamming(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count('1')


def gather(submission):
    ev = Evidence(text=(submission.text or '').strip()[:MAX_TEXT_CHARS])
    for att in submission.attachments or []:
        name = att.get('name') or att.get('url', '')
        path = media_path(att.get('url', ''))
        if att.get('type') == 'video' or path is None:
            ev.links.append(f"{name} ({att.get('url', '')})" if name != att.get('url') else name)
            continue
        ev.fingerprints.append({'name': name, **fingerprint(path)})
        if path.suffix.lower() in IMAGE_SUFFIXES:
            encoded = image_b64(path) if len(ev.images) < MAX_IMAGES else None
            if encoded:
                ev.images.append({'name': name, 'b64': encoded})
        else:
            text = extract_text(path)
            if text:
                ev.documents.append({'name': name, 'text': text})
    return ev


def find_duplicates(submission, fingerprints):
    """Files matching another learner's submission to the same assignment."""
    from hub.models import AIReview
    others = (
        AIReview.objects.filter(submission__resource_id=submission.resource_id)
        .exclude(submission__user_id=submission.user_id)
        .select_related('submission__user')
    )
    found, seen = [], set()
    for other in others:
        for theirs in (other.checks or {}).get('fingerprints', []):
            for mine in fingerprints:
                if mine['sha256'] == theirs.get('sha256'):
                    match = 'identical'
                elif mine.get('dhash') and theirs.get('dhash') and hamming(mine['dhash'], theirs['dhash']) <= DHASH_MAX_DISTANCE:
                    match = 'similar'
                else:
                    continue
                key = (other.submission_id, mine['name'])
                if key in seen:
                    continue
                seen.add(key)
                user = other.submission.user
                found.append({
                    'submission_id': other.submission_id, 'learner': user.get_full_name() or user.username,
                    'file': mine['name'], 'match': match,
                })
    return found
```

If `test_duplicates_identical_and_similar` shows `resized.png` as *identical* or not found, adjust only `DHASH_MAX_DISTANCE`, within 4–10, and record a ledger ruling.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_evidence -v 2`
  - Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/ai_review pyproject.toml uv.lock hub/tests/test_ai_review_evidence.py
git commit -m "feat: AI review evidence — text, documents, images, duplicate fingerprints"
git push
```

---

### Task 3: Model client: prompt, structured answer, validation, rubric draft

**Files:**
- Create: `backend/hub/ai_review/model.py`
- Test: `backend/hub/tests/test_ai_review_model.py`

**Interfaces — Produces:**
- `PROMPT_VERSION = '2026-10-16.1'`.
- `ReviewModelError` and its subclass `ModelOffline`.
- `_chat(messages, schema, model) -> str`: the raw JSON text, and the only network call.
- `build_messages(*, instructions, criteria, examples, evidence, checks, language) -> list`.
- `parse_review(raw, criteria) -> dict`, returning `{criteria: [{id, status, reason}], verdict, confidence, learner_feedback, reviewer_notes}`; raises `ReviewModelError`.
- `review_submission(*, instructions, criteria, examples, evidence, checks, language, model) -> dict`: tries twice, then raises.
- `draft_rubric(*, title, instructions, language, model) -> list[{id, name, met, required}]`.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_ai_review_model.py`:

```python
import json
from unittest import mock

from django.test import SimpleTestCase

from hub.ai_review import model
from hub.ai_review.evidence import Evidence

CRITERIA = [
    {'id': 'c1', 'name': 'Three risks', 'met': 'Names at least three AI risks', 'required': True},
    {'id': 'c2', 'name': 'Sources', 'met': 'Cites a source', 'required': False},
]


def answer(**over):
    data = {
        'criteria': [{'id': 'c1', 'status': 'met', 'reason': 'Lists bias, privacy, errors.'},
                     {'id': 'c2', 'status': 'not_met', 'reason': 'No source.'}],
        'verdict': 'approve', 'confidence': 0.86,
        'learner_feedback': 'Good list.', 'reviewer_notes': '',
    }
    data.update(over)
    return json.dumps(data)


class ParseTests(SimpleTestCase):
    def test_parse_good_answer(self):
        out = model.parse_review(answer(), CRITERIA)
        self.assertEqual((out['verdict'], out['confidence']), ('approve', 0.86))
        self.assertEqual([c['status'] for c in out['criteria']], ['met', 'not_met'])

    def test_parse_rejects_wrong_or_missing_criteria(self):
        with self.assertRaises(model.ReviewModelError):
            model.parse_review(answer(criteria=[{'id': 'c1', 'status': 'met', 'reason': ''}]), CRITERIA)
        with self.assertRaises(model.ReviewModelError):
            model.parse_review(answer(criteria=[{'id': 'zz', 'status': 'met', 'reason': ''},
                                                {'id': 'c2', 'status': 'met', 'reason': ''}]), CRITERIA)

    def test_parse_rejects_bad_values(self):
        for bad in (answer(verdict='maybe'), answer(confidence='high'),
                    answer(criteria=[{'id': 'c1', 'status': 'great', 'reason': ''},
                                     {'id': 'c2', 'status': 'met', 'reason': ''}]),
                    'not json at all', '[]'):
            with self.assertRaises(model.ReviewModelError, msg=bad[:40]):
                model.parse_review(bad, CRITERIA)

    def test_parse_clamps_confidence_and_strips_prose(self):
        out = model.parse_review('Here you go:\n' + answer(confidence=1.7) + '\nThanks', CRITERIA)
        self.assertEqual(out['confidence'], 1.0)


class MessageTests(SimpleTestCase):
    def test_messages_carry_rubric_evidence_checks_language_and_images(self):
        ev = Evidence(text='My answer', documents=[{'name': 'r.pdf', 'text': 'Risk register'}],
                      images=[{'name': 's.png', 'b64': 'AAAA'}], links=['demo (https://youtu.be/x)'])
        msgs = model.build_messages(
            instructions='<p>Describe three AI risks.</p>', criteria=CRITERIA,
            examples=[{'text': 'Bias, privacy, jobs', 'verdict': 'approve', 'reason': 'Three risks'}],
            evidence=ev, checks={'duplicates': [{'learner': 'Bob', 'file': 's.png', 'match': 'identical'}]},
            language='el',
        )
        user = msgs[-1]
        self.assertEqual(user['images'], ['AAAA'])
        for needle in ('Describe three AI risks.', '[c1]', 'Names at least three AI risks', 'My answer',
                       'Risk register', 'cannot be watched', 'Bob', 'Greek', 'Bias, privacy, jobs'):
            self.assertIn(needle, user['content'])
        self.assertNotIn('<p>', user['content'])


class ReviewCallTests(SimpleTestCase):
    def call(self):
        return model.review_submission(instructions='x', criteria=CRITERIA, examples=[], evidence=Evidence(text='a'),
                                       checks={}, language='en', model='m')

    def test_retries_once_after_a_malformed_answer(self):
        with mock.patch.object(model, '_chat', side_effect=['nope', answer()]) as chat:
            self.assertEqual(self.call()['verdict'], 'approve')
        self.assertEqual(chat.call_count, 2)

    def test_two_malformed_answers_raise(self):
        with mock.patch.object(model, '_chat', side_effect=['nope', 'still nope']):
            with self.assertRaises(model.ReviewModelError):
                self.call()

    def test_offline_is_not_retried_here(self):
        with mock.patch.object(model, '_chat', side_effect=model.ModelOffline('down')) as chat:
            with self.assertRaises(model.ModelOffline):
                self.call()
        self.assertEqual(chat.call_count, 1)


class DraftTests(SimpleTestCase):
    def test_draft_rubric_returns_ids_and_flags(self):
        raw = json.dumps({'criteria': [
            {'name': 'Three risks', 'met': 'Names three risks', 'required': True},
            {'name': 'Source', 'met': 'Cites a source', 'required': False},
        ]})
        with mock.patch.object(model, '_chat', return_value=raw):
            crit = model.draft_rubric(title='T', instructions='<p>Describe</p>', language='en', model='m')
        self.assertEqual([(c['id'], c['required']) for c in crit], [('c1', True), ('c2', False)])
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_model -v 2`
  - Expected: ImportError, `cannot import name 'model'`.

- [ ] **Step 3: Implement.** `backend/hub/ai_review/model.py`:

```python
"""Talking to the self-hosted review model (Ollama /api/chat, JSON-schema
output, images). `_chat` is the only network call, so tests mock it."""
import json
import os
import re
import urllib.error
import urllib.request

from django.utils.html import strip_tags

from hub.translation import LANGUAGE_NAMES, OLLAMA_HOST_HEADER, OLLAMA_URL

PROMPT_VERSION = '2026-10-16.1'
TIMEOUT = int(os.getenv('AI_REVIEW_TIMEOUT', '300'))
STATUSES = ('met', 'partly_met', 'not_met', 'cannot_judge')
VERDICTS = ('approve', 'changes_requested', 'unsure')

REVIEW_SCHEMA = {
    'type': 'object',
    'properties': {
        'criteria': {'type': 'array', 'items': {
            'type': 'object',
            'properties': {'id': {'type': 'string'}, 'status': {'type': 'string', 'enum': list(STATUSES)},
                           'reason': {'type': 'string'}},
            'required': ['id', 'status', 'reason'],
        }},
        'verdict': {'type': 'string', 'enum': list(VERDICTS)},
        'confidence': {'type': 'number'},
        'learner_feedback': {'type': 'string'},
        'reviewer_notes': {'type': 'string'},
    },
    'required': ['criteria', 'verdict', 'confidence', 'learner_feedback', 'reviewer_notes'],
}
RUBRIC_SCHEMA = {
    'type': 'object',
    'properties': {'criteria': {'type': 'array', 'items': {
        'type': 'object',
        'properties': {'name': {'type': 'string'}, 'met': {'type': 'string'}, 'required': {'type': 'boolean'}},
        'required': ['name', 'met', 'required'],
    }}},
    'required': ['criteria'],
}

SYSTEM = (
    'You review teachers\' assignment submissions for an AI-literacy course. '
    'Judge each rubric criterion only from the evidence given; if the evidence cannot show it '
    '(e.g. a video you cannot watch), use "cannot_judge". Be fair and specific. '
    'Suggest "approve" only when every required criterion is met; "changes_requested" when a '
    'required criterion is clearly not met; otherwise "unsure". Confidence is how sure you are of '
    'the verdict (0 to 1). Answer only with JSON matching the schema.'
)


class ReviewModelError(Exception):
    pass


class ModelOffline(ReviewModelError):
    pass


def _chat(messages, schema, model):
    payload = json.dumps({
        'model': model, 'messages': messages, 'stream': False, 'format': schema,
        'options': {'temperature': 0},
    }).encode()
    request = urllib.request.Request(
        f'{OLLAMA_URL}/api/chat', data=payload,
        headers={'Content-Type': 'application/json', 'Host': OLLAMA_HOST_HEADER},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ModelOffline(str(exc)) from exc
    except ValueError as exc:
        raise ReviewModelError(f'Unreadable response: {exc}') from exc
    return (data.get('message') or {}).get('content') or ''


def _plain(html):
    return re.sub(r'\s+', ' ', strip_tags(html or '')).strip()


def build_messages(*, instructions, criteria, examples, evidence, checks, language):
    rubric = '\n'.join(
        f"[{c['id']}] {c['name']} — met when: {c['met']} ({'required' if c.get('required') else 'nice to have'})"
        for c in criteria
    )
    parts = [
        f'ASSIGNMENT INSTRUCTIONS:\n{_plain(instructions)}',
        f'RUBRIC (answer for every id):\n{rubric}',
    ]
    for i, ex in enumerate(examples, start=1):
        parts.append(f"EXAMPLE {i} (correct verdict: {ex['verdict']}; why: {ex.get('reason', '')}):\n{ex.get('text', '')}")
    parts.append(f'SUBMISSION TEXT:\n{evidence.text or "(none)"}')
    for doc in evidence.documents:
        parts.append(f"ATTACHED DOCUMENT {doc['name']}:\n{doc['text']}")
    if evidence.images:
        parts.append('ATTACHED IMAGES (in order): ' + ', '.join(i['name'] for i in evidence.images))
    if evidence.links:
        parts.append('LINKS (cannot be watched or opened by you): ' + '; '.join(evidence.links))
    duplicates = (checks or {}).get('duplicates') or []
    if duplicates:
        parts.append('CHECK — same file also submitted by another learner: ' + '; '.join(
            f"{d['file']} ({d['match']}, also from {d['learner']})" for d in duplicates))
    parts.append(f"Write learner_feedback and each criterion reason in {LANGUAGE_NAMES.get(language, 'English')}. "
                 'Write reviewer_notes in English.')
    user = {'role': 'user', 'content': '\n\n'.join(parts)}
    if evidence.images:
        user['images'] = [i['b64'] for i in evidence.images]
    return [{'role': 'system', 'content': SYSTEM}, user]


def _load_json(raw):
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        match = re.search(r'\{.*\}', raw or '', re.S)
        if not match:
            raise ReviewModelError('No JSON in the answer.') from None
        try:
            return json.loads(match.group(0))
        except ValueError as exc:
            raise ReviewModelError(f'Malformed JSON: {exc}') from exc


def parse_review(raw, criteria):
    data = _load_json(raw)
    if not isinstance(data, dict):
        raise ReviewModelError('Answer is not an object.')
    results = data.get('criteria')
    wanted = [c['id'] for c in criteria]
    if not isinstance(results, list) or sorted(r.get('id') for r in results if isinstance(r, dict)) != sorted(wanted):
        raise ReviewModelError('Criteria do not match the rubric.')
    by_id = {r['id']: r for r in results}
    out_criteria = []
    for cid in wanted:
        r = by_id[cid]
        if r.get('status') not in STATUSES:
            raise ReviewModelError(f'Bad status for {cid}.')
        out_criteria.append({'id': cid, 'status': r['status'], 'reason': str(r.get('reason', ''))[:1000]})
    if data.get('verdict') not in VERDICTS:
        raise ReviewModelError('Bad verdict.')
    confidence = data.get('confidence')
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ReviewModelError('Bad confidence.')
    return {
        'criteria': out_criteria,
        'verdict': data['verdict'],
        'confidence': round(min(max(float(confidence), 0.0), 1.0), 3),
        'learner_feedback': str(data.get('learner_feedback', ''))[:4000],
        'reviewer_notes': str(data.get('reviewer_notes', ''))[:4000],
    }


def review_submission(*, instructions, criteria, examples, evidence, checks, language, model):
    messages = build_messages(instructions=instructions, criteria=criteria, examples=examples,
                              evidence=evidence, checks=checks, language=language)
    last = None
    for _ in range(2):
        raw = _chat(messages, REVIEW_SCHEMA, model)   # ModelOffline propagates (the task retries later)
        try:
            return parse_review(raw, criteria)
        except ReviewModelError as exc:
            last = exc
    raise last


def draft_rubric(*, title, instructions, language, model):
    prompt = (
        f'Propose 3 to 6 assessment criteria for this assignment. Each has a short name, a one-sentence '
        f'description of what "met" looks like, and whether it is required. Write them in '
        f"{LANGUAGE_NAMES.get(language, 'English')}.\n\nTITLE: {title}\n\nINSTRUCTIONS:\n{_plain(instructions)}"
    )
    data = _load_json(_chat([{'role': 'user', 'content': prompt}], RUBRIC_SCHEMA, model))
    items = data.get('criteria') if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise ReviewModelError('No criteria proposed.')
    return [
        {'id': f'c{i}', 'name': str(c.get('name', ''))[:120], 'met': str(c.get('met', ''))[:500],
         'required': bool(c.get('required', True))}
        for i, c in enumerate(items[:6], start=1) if isinstance(c, dict) and c.get('name')
    ]
```

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_model -v 2`
  - Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/ai_review/model.py hub/tests/test_ai_review_model.py
git commit -m "feat: AI review model client — prompt, structured answer, validation, rubric draft"
git push
```

---

### Task 4: Pipeline: queue on submit, run, auto-approve, shared approval, Celery task

**Files:**
- Create: `backend/hub/ai_review/metrics.py`, `backend/hub/ai_review/pipeline.py`, `backend/hub/assignment_review.py`
- Modify:
  - `backend/hub/tasks.py`: add `run_ai_review`.
  - `backend/hub/views/assignments.py`: both submit views queue an AI review; `ReviewActionView` uses `hub.assignment_review`.
- Delete: `backend/hub/llm_review.py`
- Test: `backend/hub/tests/test_ai_review_metrics.py`, `backend/hub/tests/test_ai_review_pipeline.py`

**Interfaces:**
- **Consumes:** Task 1's models, Task 2's `gather` and `find_duplicates`, and Task 3's `review_submission`, `ModelOffline`, `ReviewModelError` and `PROMPT_VERSION`.
- **Produces:**
  - `hub.assignment_review.approve_submission(submission, reviewer, feedback='')`: sets status, feedback and reviewer, records completion, sends the email.
  - `hub.assignment_review.request_changes(submission, reviewer, feedback)`.
  - `hub.assignment_review.reopen_submission(submission)`: back to pending, completion removed, progress recomputed, email sent.
  - `pipeline.queue_review(submission) -> AIReview | None`.
  - `pipeline.run_review(review_id)`: raises `ModelOffline` for the task to retry.
  - `pipeline.mark_failed(review_id, message)`.
  - `metrics.wilson_lower(successes, n, z=1.96) -> float | None`.
  - `metrics.cohen_kappa(pairs) -> float | None`, over `(ai_verdict, human_verdict)` pairs; only approve / changes_requested count, and it's None when undefined.
  - `metrics.summarise(reviews) -> {'reviews', 'decided', 'agreement', 'kappa', 'approve_agreement', 'approve_lower_bound', 'feedback_used', 'feedback_unchanged', 'most_missed', 'most_missed_name'}`. Ratios are rounded to 3 places, or None when there's nothing to count.
  - `pipeline.assignment_stats(resource)`: `summarise` over the assignment's done AI reviews.
  - `pipeline.auto_approve_unlocked(resource, settings) -> bool`.
  - `pipeline.record_human_verdict(submission, verdict, reason='', feedback_used=False, feedback='')`.
  - Celery task `hub.tasks.run_ai_review(review_id)`, retried every 10 minutes up to 12 times on `ModelOffline`.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_ai_review_pipeline.py`:

```python
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase

from hub.ai_review import model, pipeline
from hub.models import (
    AIReview,
    AIReviewSettings,
    AssignmentReviewConfig,
    AssignmentSubmission,
    Enrollment,
    ResourceProgress,
    UserProfile,
)

from .test_ai_review_models import make_assignment
from .test_ai_review_model import CRITERIA, answer


class PipelineTests(TestCase):
    def setUp(self):
        self.course, _, self.activity, self.resource = make_assignment()
        self.settings = AIReviewSettings.get()
        self.settings.enabled = True
        self.settings.save()
        self.config = AssignmentReviewConfig.objects.create(
            resource=self.resource, enabled=True, criteria=CRITERIA, rubric_approved=True,
        )
        self.learner = User.objects.create_user('pl', password='x', email='pl@example.org')
        UserProfile.objects.create(user=self.learner, language='el')
        Enrollment.objects.create(user=self.learner, course=self.course)

    def submit(self, text='Bias, privacy, errors'):
        # One submission per learner and activity (unique_together); submitting
        # again updates it, as a real resubmission does.
        sub, _ = AssignmentSubmission.objects.update_or_create(
            user=self.learner, lesson=self.activity,
            defaults={'resource': self.resource, 'text': text, 'status': 'pending'},
        )
        return sub

    def other_submission(self):
        """Another learner's submission to the same assignment (history for stats)."""
        self._others = getattr(self, '_others', 0) + 1
        user = User.objects.create_user(f'pl_other{self._others}', password='x')
        UserProfile.objects.create(user=user)
        return AssignmentSubmission.objects.create(user=user, lesson=self.activity, resource=self.resource, text='t')

    def run_with(self, *answers):
        sub = self.submit()
        review = pipeline.queue_review(sub)
        with mock.patch.object(model, '_chat', side_effect=list(answers)):
            pipeline.run_review(review.id)
        review.refresh_from_db()
        sub.refresh_from_db()
        return review, sub

    # queueing
    def test_queue_needs_platform_switch_config_and_resource(self):
        self.settings.enabled = False
        self.settings.save()
        self.assertIsNone(pipeline.queue_review(self.submit()))
        self.settings.enabled = True
        self.settings.save()
        self.config.rubric_approved = False
        self.config.save()
        self.assertIsNone(pipeline.queue_review(self.submit()))

    def test_review_stored(self):
        review, sub = self.run_with(answer())
        self.assertEqual((review.status, review.verdict, review.confidence), ('done', 'approve', 0.86))
        self.assertEqual(review.model_name, 'qwen2.5vl:32b')
        self.assertEqual(review.prompt_version, model.PROMPT_VERSION)
        self.assertEqual(review.rubric, CRITERIA)
        self.assertEqual([c['id'] for c in review.criteria_results], ['c1', 'c2'])
        self.assertEqual(sub.status, 'pending')          # shadow mode: humans still decide
        self.assertIsNotNone(review.finished_at)

    def test_malformed_answer_twice_marks_failed(self):
        review, sub = self.run_with('nope', 'nope')
        self.assertEqual(review.status, 'failed')
        self.assertTrue(review.error)
        self.assertEqual(sub.status, 'pending')

    def test_offline_is_retried_then_failed(self):
        sub = self.submit()
        review = pipeline.queue_review(sub)
        with mock.patch.object(model, '_chat', side_effect=model.ModelOffline('down')):
            with self.assertRaises(model.ModelOffline):
                pipeline.run_review(review.id)
        review.refresh_from_db()
        self.assertEqual(review.status, 'queued')         # waiting for the retry
        pipeline.mark_failed(review.id, 'gave up')
        review.refresh_from_db()
        self.assertEqual((review.status, review.error), ('failed', 'gave up'))

    # auto-approve rules
    def unlock(self):
        self.config.auto_approve = True
        self.config.save()
        other = self.other_submission()
        for _ in range(40):      # 40/40 agreeing: lower bound 0.912
            AIReview.objects.create(submission=other, status='done', verdict='approve', human_verdict='approve', agreed=True)

    def test_locked_assignment_never_auto_approves(self):
        self.config.auto_approve = True
        self.config.save()
        review, sub = self.run_with(answer())
        self.assertEqual((sub.status, review.auto_approved), ('pending', False))

    def test_unlocked_clear_pass_is_auto_approved(self):
        self.unlock()
        with mock.patch('hub.ai_review.pipeline.random.random', return_value=0.5):
            review, sub = self.run_with(answer())
        self.assertEqual((sub.status, review.auto_approved), ('approved', True))
        self.assertIsNone(sub.reviewed_by)
        self.assertTrue(ResourceProgress.objects.filter(user=self.learner, resource=self.resource, completed_at__isnull=False).exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_each_rule_blocks_auto_approval(self):
        self.unlock()
        cases = {
            'low confidence': answer(confidence=0.5),
            'not approve': answer(verdict='unsure'),
            'required partly met': answer(criteria=[{'id': 'c1', 'status': 'partly_met', 'reason': ''},
                                                    {'id': 'c2', 'status': 'met', 'reason': ''}]),
        }
        for label, raw in cases.items():
            with mock.patch('hub.ai_review.pipeline.random.random', return_value=0.5):
                review, sub = self.run_with(raw)
            self.assertEqual(sub.status, 'pending', label)

    def test_duplicate_flag_blocks_auto_approval(self):
        self.unlock()
        with mock.patch('hub.ai_review.pipeline.random.random', return_value=0.5), \
             mock.patch('hub.ai_review.pipeline.find_duplicates', return_value=[{'submission_id': 1, 'learner': 'Bo', 'file': 'a.png', 'match': 'identical'}]):
            review, sub = self.run_with(answer())
        self.assertTrue(review.flagged)
        self.assertEqual(sub.status, 'pending')

    def test_spot_check_keeps_it_for_a_human(self):
        self.unlock()
        with mock.patch('hub.ai_review.pipeline.random.random', return_value=0.05):
            review, sub = self.run_with(answer())
        self.assertEqual((sub.status, review.spot_check, review.auto_approved), ('pending', True, False))

    # stats and human verdicts
    def test_stats_and_unlock(self):
        AIReview.objects.create(submission=self.other_submission(), status='done', verdict='approve', human_verdict='approve', agreed=True)
        AIReview.objects.create(submission=self.other_submission(), status='done', verdict='approve', human_verdict='changes_requested', agreed=False)
        AIReview.objects.create(submission=self.other_submission(), status='done', verdict='changes_requested', human_verdict='changes_requested', agreed=True,
                                criteria_results=[{'id': 'c1', 'status': 'not_met', 'reason': ''}])
        stats = pipeline.assignment_stats(self.resource)
        self.assertEqual((stats['reviews'], stats['decided']), (3, 3))
        self.assertAlmostEqual(stats['agreement'], 2 / 3, places=3)
        self.assertAlmostEqual(stats['kappa'], 0.4, places=3)
        self.assertAlmostEqual(stats['approve_agreement'], 0.5)
        self.assertAlmostEqual(stats['approve_lower_bound'], 0.095, places=3)
        self.assertEqual(stats['most_missed'], 'c1')
        self.assertFalse(pipeline.auto_approve_unlocked(self.resource, self.settings))

    def test_unlock_needs_a_reliable_lower_bound(self):
        other = self.other_submission()
        for _ in range(34):
            AIReview.objects.create(submission=other, status='done', verdict='approve', human_verdict='approve', agreed=True)
        self.assertFalse(pipeline.auto_approve_unlocked(self.resource, self.settings))   # 34/34: lower bound 0.898
        AIReview.objects.create(submission=other, status='done', verdict='approve', human_verdict='approve', agreed=True)
        self.assertTrue(pipeline.auto_approve_unlocked(self.resource, self.settings))    # 35/35: 0.901

    def test_record_human_verdict(self):
        review, sub = self.run_with(answer())
        pipeline.record_human_verdict(sub, 'changes_requested', reason='too_lenient')
        review.refresh_from_db()
        self.assertEqual((review.human_verdict, review.agreed, review.disagreement_reason),
                         ('changes_requested', False, 'too_lenient'))
        pipeline.record_human_verdict(sub, 'approve', reason='bogus')
        review.refresh_from_db()
        self.assertEqual((review.agreed, review.disagreement_reason), (True, ''))

    def test_feedback_use_is_recorded(self):
        review, sub = self.run_with(answer(learner_feedback='Good list of three risks.'))
        pipeline.record_human_verdict(sub, 'approve', feedback_used=True, feedback='Good list of three risks.')
        review.refresh_from_db()
        self.assertEqual((review.feedback_used, review.feedback_similarity), (True, 1.0))
        pipeline.record_human_verdict(sub, 'approve', feedback_used=True, feedback='Good list. Add a source next time.')
        review.refresh_from_db()
        self.assertLess(review.feedback_similarity, 0.95)
        pipeline.record_human_verdict(sub, 'approve')
        review.refresh_from_db()
        self.assertEqual((review.feedback_used, review.feedback_similarity), (False, None))

    def test_reopen_auto_approved(self):
        from hub.assignment_review import reopen_submission
        self.unlock()
        with mock.patch('hub.ai_review.pipeline.random.random', return_value=0.5):
            review, sub = self.run_with(answer())
        mail.outbox.clear()
        reopen_submission(sub)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'pending')
        self.assertFalse(ResourceProgress.objects.filter(user=self.learner, resource=self.resource).exists())
        self.assertEqual(mail.outbox[0].subject, 'Your submission is being reviewed again')

    def test_review_of_an_older_version_never_auto_approves(self):
        self.unlock()
        sub = self.submit()
        old = pipeline.queue_review(sub)
        self.submit(text='Revised answer')            # learner resubmits while pending
        pipeline.queue_review(sub)
        with mock.patch.object(model, '_chat', side_effect=[answer()]), \
             mock.patch('hub.ai_review.pipeline.random.random', return_value=0.5):
            pipeline.run_review(old.id)
        sub.refresh_from_db()
        old.refresh_from_db()
        self.assertEqual((old.status, old.auto_approved, sub.status), ('done', False, 'pending'))
```

`backend/hub/tests/test_ai_review_metrics.py`:

```python
from types import SimpleNamespace

from django.test import SimpleTestCase

from hub.ai_review.metrics import cohen_kappa, summarise, wilson_lower

A, C = 'approve', 'changes_requested'


class MetricsTests(SimpleTestCase):
    def test_wilson_lower_bound(self):
        self.assertAlmostEqual(wilson_lower(29, 30), 0.833, places=3)   # 97% observed, 83% safe
        self.assertAlmostEqual(wilson_lower(30, 30), 0.886, places=3)
        self.assertAlmostEqual(wilson_lower(35, 35), 0.901, places=3)
        self.assertIsNone(wilson_lower(0, 0))

    def test_kappa_corrects_for_chance(self):
        # An AI that always approves, where humans approve 9 in 10: 90% agreement, no skill.
        self.assertAlmostEqual(cohen_kappa([(A, A)] * 9 + [(A, C)]), 0.0)
        self.assertAlmostEqual(cohen_kappa([(A, A)] * 8 + [(A, C), (C, C)]), 0.615, places=3)
        self.assertIsNone(cohen_kappa([(A, A)] * 5))       # undefined: both only ever approve
        self.assertIsNone(cohen_kappa([]))
        self.assertAlmostEqual(cohen_kappa([('unsure', A), (A, A), (C, C)]), 1.0)   # unsure is ignored

    def test_summarise_feedback_use(self):
        def review(used, similarity):
            return SimpleNamespace(verdict=A, human_verdict=A, agreed=True, criteria_results=[], rubric=[],
                                   feedback_used=used, feedback_similarity=similarity)
        stats = summarise([review(True, 1.0), review(True, 0.6), review(False, None), review(False, None)])
        self.assertEqual((stats['feedback_used'], stats['feedback_unchanged']), (0.5, 0.5))

    def test_summarise_empty(self):
        stats = summarise([])
        self.assertEqual((stats['reviews'], stats['agreement'], stats['kappa'], stats['most_missed']), (0, None, None, None))
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_metrics hub.tests.test_ai_review_pipeline -v 2`
  - Expected: ImportError, `cannot import name 'metrics'` / `'pipeline'`.

- [ ] **Step 3: Implement.** `backend/hub/assignment_review.py`:

```python
"""Approving / requesting changes / reopening an assignment submission —
shared by human reviewers and the AI reviewer's auto-approve."""
from django.db import transaction
from django.utils import timezone

from hub.models import AssignmentSubmission, Enrollment, ResourceProgress


class ReviewError(Exception):
    pass


def approve_submission(submission, reviewer, feedback=''):
    course = submission.lesson.module.course
    enrollment = Enrollment.objects.filter(user=submission.user, course=course).first()
    if enrollment is None:
        raise ReviewError('The learner is no longer enrolled in this course.')
    from hub.completion import record_lesson_completion, record_resource_completion
    with transaction.atomic():
        submission.status = AssignmentSubmission.Status.APPROVED
        if feedback:
            submission.feedback = feedback
        submission.reviewed_by = reviewer
        submission.reviewed_at = timezone.now()
        submission.save()
        if submission.resource_id:
            record_resource_completion(submission.user, enrollment, submission.resource,
                                       engagement_data={'submission': submission.text}, advance_only=True)
        else:
            record_lesson_completion(submission.user, enrollment, submission.lesson,
                                     engagement_data={'submission': submission.text}, advance_only=True)
    from hub.emails import send_assignment_reviewed_email
    send_assignment_reviewed_email(submission)


def request_changes(submission, reviewer, feedback):
    submission.status = AssignmentSubmission.Status.CHANGES_REQUESTED
    submission.feedback = feedback
    submission.reviewed_by = reviewer
    submission.reviewed_at = timezone.now()
    submission.save()
    from hub.emails import send_assignment_reviewed_email
    send_assignment_reviewed_email(submission)


def reopen_submission(submission):
    """Undo an approval: the submission waits for a human again and its
    resource is no longer complete."""
    from hub.completion import recompute_course_progress
    with transaction.atomic():
        submission.status = AssignmentSubmission.Status.PENDING
        submission.reviewed_by = None
        submission.reviewed_at = None
        submission.save()
        if submission.resource_id:
            ResourceProgress.objects.filter(user=submission.user, resource=submission.resource).delete()
        enrollment = Enrollment.objects.filter(user=submission.user, course=submission.lesson.module.course).first()
        if enrollment:
            if recompute_course_progress(submission.user, enrollment) < 100 and enrollment.completed_at:
                enrollment.completed_at = None
                enrollment.save(update_fields=['completed_at'])
    from hub.emails import send_assignment_reviewed_email
    send_assignment_reviewed_email(submission)
```

`backend/hub/emails.py`: `send_assignment_reviewed_email` today treats every non-approved status as "sent back with change requests", which is wrong for a reopened submission. At the top of the function, after the `if not user.email: return` guard and the `lesson`, `course` and `link` lines, add a branch for `PENDING`:

```python
    if submission.status == submission.Status.PENDING:
        _send(
            to=user.email,
            subject='Your submission is being reviewed again',
            name=user.get_full_name() or user.username,
            tag='Assignment reviewed',
            heading='Your submission is being reviewed again',
            paragraphs=[f'Your submission for “{lesson.title}” in “{course.title}” was approved '
                        'automatically and is now being checked by a reviewer. You will hear back soon.'],
            cta_label='Open the lesson',
            cta_link=link,
        )
        return
```

Match the remaining `_send` arguments to the existing call below it (copy any extra keyword it passes).

`backend/hub/ai_review/metrics.py`:

```python
"""Agreement statistics for the AI reviewer.

- Cohen's kappa: agreement beyond what chance would give (an AI that always
  says "approve" scores 0 however often humans approve).
- Wilson lower bound: how low the true approve-agreement could plausibly be
  given how few reviews exist (29/30 looks like 97% but may be 83%).
- Feedback use: how often reviewers send the AI's feedback (nearly) unchanged —
  the warning sign for rubber-stamping."""
import math

DEFINITE = ('approve', 'changes_requested')
UNCHANGED_SIMILARITY = 0.95


def _r(x):
    return None if x is None else round(x, 3)


def wilson_lower(successes, n, z=1.96):
    if n == 0:
        return None
    p = successes / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / (1 + z * z / n)


def cohen_kappa(pairs):
    pairs = [(a, h) for a, h in pairs if a in DEFINITE and h in DEFINITE]
    n = len(pairs)
    if n == 0:
        return None
    observed = sum(a == h for a, h in pairs) / n
    expected = sum((sum(a == v for a, _ in pairs) / n) * (sum(h == v for _, h in pairs) / n) for v in DEFINITE)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def summarise(reviews):
    reviews = list(reviews)
    decided = [r for r in reviews if r.human_verdict and r.agreed is not None]
    ai_approves = [r for r in decided if r.verdict == 'approve']
    approve_ok = sum(r.human_verdict == 'approve' for r in ai_approves)
    used = [r for r in decided if r.feedback_used]
    missed = {}
    for r in reviews:
        for c in r.criteria_results or []:
            if c.get('status') in ('not_met', 'partly_met'):
                missed[c['id']] = missed.get(c['id'], 0) + 1
    names = {c['id']: c['name'] for r in reviews for c in (r.rubric or [])}
    worst = max(missed, key=missed.get) if missed else None
    return {
        'reviews': len(reviews),
        'decided': len(decided),
        'agreement': _r(sum(r.agreed for r in decided) / len(decided)) if decided else None,
        'kappa': _r(cohen_kappa((r.verdict, r.human_verdict) for r in decided)),
        'approve_agreement': _r(approve_ok / len(ai_approves)) if ai_approves else None,
        'approve_lower_bound': _r(wilson_lower(approve_ok, len(ai_approves))),
        'feedback_used': _r(len(used) / len(decided)) if decided else None,
        'feedback_unchanged': (_r(sum((r.feedback_similarity or 0) >= UNCHANGED_SIMILARITY for r in used) / len(used))
                               if used else None),
        'most_missed': worst,
        'most_missed_name': names.get(worst) if worst else None,
    }
```

`backend/hub/ai_review/pipeline.py`:

```python
"""Queueing and running AI reviews; auto-approve; agreement statistics."""
import random
import time
from difflib import SequenceMatcher

from django.db import transaction
from django.utils import timezone

from hub.ai_review import model
from hub.ai_review.evidence import find_duplicates, gather
from hub.ai_review.metrics import summarise
from hub.models import AIReview, AIReviewSettings, AssignmentSubmission


def queue_review(submission):
    if not submission.resource_id or not AIReviewSettings.get().enabled:
        return None
    config = getattr(submission.resource, 'ai_review_config', None)
    if config is None or not config.is_ready():
        return None
    review = AIReview.objects.create(
        submission=submission, model_name=AIReviewSettings.get().model_name,
        prompt_version=model.PROMPT_VERSION, rubric=config.criteria,
    )
    from hub.tasks import run_ai_review
    transaction.on_commit(lambda: run_ai_review.delay(review.id))
    return review


def _examples(resource):
    return [{'text': e.text, 'verdict': e.verdict, 'reason': e.reason} for e in resource.ai_review_examples.all()[:5]]


def run_review(review_id):
    review = AIReview.objects.select_related(
        'submission__user__profile', 'submission__resource__ai_review_config',
    ).get(pk=review_id)
    if review.status in (AIReview.Status.DONE, AIReview.Status.FAILED):
        return
    submission, config = review.submission, review.submission.resource.ai_review_config
    started = time.monotonic()
    review.status, review.attempts = AIReview.Status.RUNNING, review.attempts + 1
    review.save(update_fields=['status', 'attempts'])
    ev = gather(submission)
    checks = {'fingerprints': ev.fingerprints,
              'duplicates': find_duplicates(submission, ev.fingerprints) if config.duplicate_check else []}
    language = getattr(getattr(submission.user, 'profile', None), 'language', 'en') or 'en'
    try:
        result = model.review_submission(
            instructions=submission.resource.instructions, criteria=review.rubric,
            examples=_examples(submission.resource), evidence=ev, checks=checks,
            language=language, model=review.model_name,
        )
    except model.ModelOffline:
        review.status = AIReview.Status.QUEUED
        review.checks = checks
        review.save(update_fields=['status', 'checks'])
        raise
    except model.ReviewModelError as exc:
        review.status, review.error, review.checks = AIReview.Status.FAILED, str(exc)[:2000], checks
        review.finished_at = timezone.now()
        review.save()
        return
    review.checks = checks
    review.criteria_results = result['criteria']
    review.verdict, review.confidence = result['verdict'], result['confidence']
    review.learner_feedback, review.reviewer_notes = result['learner_feedback'], result['reviewer_notes']
    review.status, review.finished_at = AIReview.Status.DONE, timezone.now()
    review.duration_s = round(time.monotonic() - started, 1)
    review.save()
    _maybe_auto_approve(review, config)


def mark_failed(review_id, message):
    AIReview.objects.filter(pk=review_id).exclude(status=AIReview.Status.DONE).update(
        status=AIReview.Status.FAILED, error=message[:2000], finished_at=timezone.now())


def assignment_stats(resource):
    return summarise(AIReview.objects.filter(submission__resource=resource, status=AIReview.Status.DONE))


def auto_approve_unlocked(resource, settings):
    stats = assignment_stats(resource)
    return (stats['decided'] >= settings.unlock_min_reviews
            and (stats['approve_lower_bound'] or 0) >= settings.unlock_min_lower_bound)


def _maybe_auto_approve(review, config):
    settings = AIReviewSettings.get()
    if not (config.auto_approve and auto_approve_unlocked(config.resource, settings)):
        return
    required = {c['id'] for c in review.rubric if c.get('required')}
    clear = (
        review.verdict == AIReview.Verdict.APPROVE
        and (review.confidence or 0) >= settings.confidence_threshold
        and all(c['status'] == 'met' for c in review.criteria_results if c['id'] in required)
        and not review.flagged
        and review.submission.status == AssignmentSubmission.Status.PENDING
        and review.submission.ai_reviews.first().id == review.id   # not an older version
    )
    if not clear:
        return
    if random.random() < settings.spot_check_rate:
        review.spot_check = True
        review.save(update_fields=['spot_check'])
        return
    from hub.assignment_review import ReviewError, approve_submission
    try:
        approve_submission(review.submission, reviewer=None, feedback=review.learner_feedback)
    except ReviewError:
        return
    review.auto_approved = True
    review.save(update_fields=['auto_approved'])


def record_human_verdict(submission, verdict, reason='', feedback_used=False, feedback=''):
    review = submission.ai_reviews.filter(status=AIReview.Status.DONE).first()
    if review is None:
        return
    review.human_verdict = verdict
    review.agreed = (review.verdict == verdict) if review.verdict in ('approve', 'changes_requested') else None
    review.disagreement_reason = reason if review.agreed is False and reason in AIReview.DISAGREEMENT_REASONS else ''
    review.feedback_used = bool(feedback_used and review.learner_feedback)
    review.feedback_similarity = (round(SequenceMatcher(None, review.learner_feedback, feedback or '').ratio(), 3)
                                  if review.feedback_used else None)
    review.save(update_fields=['human_verdict', 'agreed', 'disagreement_reason', 'feedback_used', 'feedback_similarity'])
```

Note on the stats test:
- three decided reviews, two agreed, so agreement is 2/3;
- kappa: the AI approved 2/3 and humans 1/3, so chance agreement is 2/9 + 2/9 = 4/9, and kappa = (2/3 − 4/9) / (5/9) = 0.4;
- the AI said approve twice and humans approved once, so `approve_agreement` is 0.5, and its lower bound with only 2 reviews is 0.095.

`backend/hub/tasks.py`: add

```python
@shared_task(bind=True, max_retries=12, default_retry_delay=600)
def run_ai_review(self, review_id: int) -> None:
    """Run one AI review; retried every 10 minutes while the NTUA server is
    offline, then given up (the submission simply waits for a human)."""
    from hub.ai_review.model import ModelOffline
    from hub.ai_review.pipeline import mark_failed, run_review
    try:
        run_review(review_id)
    except ModelOffline as exc:
        if self.request.retries >= self.max_retries:
            mark_failed(review_id, f'Model server offline: {exc}')
            return
        raise self.retry(exc=exc)
```

`backend/hub/views/assignments.py`:
- In both submit views, replace the `if ….llm_review_enabled: from hub.llm_review import review_submission; review_submission(submission)` blocks with:

```python
        from hub.ai_review.pipeline import queue_review
        queue_review(submission)
```

- In `ReviewActionView.post`, replace the approve and request-changes bodies with calls to `approve_submission(submission, request.user, feedback)` (catch `ReviewError` and return 400 with its message) and `request_changes(submission, request.user, feedback)`.
- Remove the trailing `send_assignment_reviewed_email` call, which now lives in those functions.
- After either action, call `record_human_verdict(submission, 'approve' | 'changes_requested', reason=str(request.data.get('disagreement_reason', '')), feedback_used=request.data.get('used_ai_feedback') is True, feedback=feedback)`.

Delete `backend/hub/llm_review.py`. Then grep for `llm_review` in `hub/` and `tests/`, and update any test that patched it to patch `hub.ai_review.pipeline.queue_review` instead.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_metrics hub.tests.test_ai_review_pipeline hub.tests.test_assignment_review hub.tests.test_resource_assignment -v 2`
  - Expected: all pass. The existing review tests must still pass unchanged.

- [ ] **Step 5: Lint, full suite and commit.**

```bash
"$UV" run ruff check hub analytics
"$UV" run manage.py test hub analytics
git add hub/ai_review/metrics.py hub/ai_review/pipeline.py hub/assignment_review.py hub/tasks.py hub/views/assignments.py hub/tests/test_ai_review_metrics.py hub/tests/test_ai_review_pipeline.py hub/emails.py
git rm hub/llm_review.py
git commit -m "feat: AI review pipeline — queue on submit, run, auto-approve rules, agreement metrics"
git push
```

---

### Task 5: Authoring API (config, rubric draft and approval, examples, translation of criteria)

**Files:**
- Create: `backend/hub/views/ai_review.py`
- Modify: `backend/hub/urls.py`, `backend/hub/tasks.py` (adds `translate_review_criteria`)
- Test: `backend/hub/tests/test_ai_review_authoring.py`

**Interfaces — Produces:**
- `GET` and `PUT` on `/api/authoring/courses/<pk>/modules/<m>/lessons/<a>/resources/<r>/ai-review/` (`authoring-ai-review`):
  - The response is `{enabled, criteria, rubric_approved, learner_visible, auto_approve, duplicate_check, platform_enabled, unlocked, unlock_min_reviews, unlock_min_lower_bound, stats}`.
  - `PUT` validates the criteria. Changing the criteria clears `rubric_approved` unless the same request sets it true. `auto_approve: true` is refused with 400 while locked. Approving queues `translate_review_criteria`.
- `POST …/ai-review/draft/` (`authoring-ai-review-draft`): returns `{criteria}`, or 503 when the model is offline.
- `GET` and `POST …/ai-review/examples/` (`authoring-ai-review-examples`) and `DELETE …/ai-review/examples/<id>/` (`authoring-ai-review-example`).
- Celery `translate_review_criteria(config_id)` fills `criteria_translations[lang][id]` for the course's target languages.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_ai_review_authoring.py`:

```python
from unittest import mock

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.ai_review import model
from hub.models import AIReview, AssignmentReviewConfig, AssignmentSubmission, ReviewExample, UserProfile

from .test_ai_review_model import CRITERIA
from .test_ai_review_models import make_assignment


class AuthoringAIReviewTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user('aa_cc', password='x')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.module, self.activity, self.resource = make_assignment()
        self.course.created_by = self.creator
        self.course.save()
        kw = {'pk': self.course.id, 'module_pk': self.module.id, 'lesson_pk': self.activity.id, 'resource_pk': self.resource.id}
        self.url = reverse('authoring-ai-review', kwargs=kw)
        self.draft_url = reverse('authoring-ai-review-draft', kwargs=kw)
        self.examples_url = reverse('authoring-ai-review-examples', kwargs=kw)
        self.client.force_authenticate(self.creator)

    def test_get_creates_default_config(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data['enabled'], res.data['criteria'], res.data['unlocked']), (False, [], False))
        self.assertEqual(res.data['stats']['reviews'], 0)

    def test_save_and_approve_rubric(self):
        res = self.client.put(self.url, {'enabled': True, 'criteria': CRITERIA, 'rubric_approved': True}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        config = AssignmentReviewConfig.objects.get(resource=self.resource)
        self.assertTrue(config.is_ready())
        res = self.client.put(self.url, {'criteria': CRITERIA[:1]}, format='json')
        self.assertFalse(res.data['rubric_approved'])     # changed criteria need re-approval

    def test_invalid_criteria_rejected(self):
        for bad in ([{'name': ''}], [{'id': 'c1', 'name': 'x', 'met': 'y', 'required': 'yes'}], 'nope', [{}] * 11):
            res = self.client.put(self.url, {'criteria': bad}, format='json')
            self.assertEqual(res.status_code, 400, bad)

    def test_auto_approve_refused_while_locked(self):
        res = self.client.put(self.url, {'auto_approve': True}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_draft_uses_model(self):
        with mock.patch.object(model, 'draft_rubric', return_value=CRITERIA) as draft:
            res = self.client.post(self.draft_url)
        self.assertEqual((res.status_code, res.data['criteria']), (200, CRITERIA))
        self.assertEqual(draft.call_args.kwargs['instructions'], self.resource.instructions)

    def test_draft_offline_is_503(self):
        with mock.patch.object(model, 'draft_rubric', side_effect=model.ModelOffline('down')):
            self.assertEqual(self.client.post(self.draft_url).status_code, 503)

    def test_examples_crud(self):
        res = self.client.post(self.examples_url, {'text': 'Bias, privacy', 'verdict': 'approve', 'reason': 'ok'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(self.client.get(self.examples_url).data), 1)
        for _ in range(4):
            self.client.post(self.examples_url, {'text': 'x', 'verdict': 'approve'}, format='json')
        self.assertEqual(self.client.post(self.examples_url, {'text': 'x', 'verdict': 'approve'}, format='json').status_code, 400)
        example = ReviewExample.objects.first()
        url = reverse('authoring-ai-review-example', kwargs={'pk': self.course.id, 'module_pk': self.module.id,
                      'lesson_pk': self.activity.id, 'resource_pk': self.resource.id, 'example_pk': example.id})
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_other_creator_forbidden_and_non_assignment_400(self):
        other = User.objects.create_user('aa_o', password='x')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(self.creator)
        self.resource.type = 'text'
        self.resource.save()
        self.assertEqual(self.client.get(self.url).status_code, 400)

    def test_criteria_translated_on_approval(self):
        self.course.translation_status = {'el': 'done'}
        self.course.save()
        with mock.patch('hub.translation._ollama_generate', side_effect=lambda prompt: 'Τρεις κίνδυνοι'):
            self.client.put(self.url, {'enabled': True, 'criteria': CRITERIA[:1], 'rubric_approved': True}, format='json')
        config = AssignmentReviewConfig.objects.get(resource=self.resource)
        self.assertEqual(config.criteria_translations, {'el': {'c1': 'Τρεις κίνδυνοι'}})

    def test_unlocked_reported(self):
        learner = User.objects.create_user('aa_l', password='x')
        UserProfile.objects.create(user=learner)
        sub = AssignmentSubmission.objects.create(user=learner, lesson=self.activity, resource=self.resource, text='t')
        for _ in range(35):
            AIReview.objects.create(submission=sub, status='done', verdict='approve', human_verdict='approve', agreed=True)
        data = self.client.get(self.url).data
        self.assertTrue(data['unlocked'])
        self.assertEqual((data['unlock_min_reviews'], data['unlock_min_lower_bound']), (30, 0.9))
        self.assertIn('kappa', data['stats'])
        self.assertEqual(self.client.put(self.url, {'auto_approve': True}, format='json').status_code, 200)
```

`'done'` is one of the statuses `_target_langs` accepts (`_SYNCABLE = {'done', 'reviewed', 'pending'}` in `hub/translation_sync.py`).

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_authoring -v 2`
  - Expected: `NoReverseMatch: 'authoring-ai-review'`.

- [ ] **Step 3: Implement.** `backend/hub/views/ai_review.py`:

```python
"""Authoring endpoints for an assignment's AI review set-up."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.ai_review import model
from hub.ai_review.pipeline import assignment_stats, auto_approve_unlocked
from hub.models import AIReviewSettings, AssignmentReviewConfig, Resource, ReviewExample

from .permissions import IsContentCreator, can_edit_course

MAX_CRITERIA = 10
MAX_EXAMPLES = 5
FLAGS = ('enabled', 'learner_visible', 'duplicate_check')


def _resource(request, pk, module_pk, lesson_pk, resource_pk):
    resource = (Resource.objects.select_related('activity__module__course')
                .filter(pk=resource_pk, activity_id=lesson_pk, activity__module_id=module_pk,
                        activity__module__course_id=pk).first())
    if resource is None:
        return None, Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not can_edit_course(request.user, resource.activity.module.course):
        return None, Response({'detail': 'You cannot edit this course.'}, status=status.HTTP_403_FORBIDDEN)
    if resource.type != Resource.Type.ASSIGNMENT:
        return None, Response({'detail': 'AI review is only for assignments.'}, status=status.HTTP_400_BAD_REQUEST)
    return resource, None


def _clean_criteria(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_CRITERIA:
        return None
    cleaned = []
    for i, c in enumerate(raw, start=1):
        if not isinstance(c, dict) or not str(c.get('name', '')).strip() or not isinstance(c.get('required', True), bool):
            return None
        cleaned.append({'id': str(c.get('id') or f'c{i}')[:20], 'name': str(c['name']).strip()[:120],
                        'met': str(c.get('met', '')).strip()[:500], 'required': c.get('required', True)})
    if len({c['id'] for c in cleaned}) != len(cleaned):
        return None
    return cleaned


def _payload(config):
    settings = AIReviewSettings.get()
    return {
        'enabled': config.enabled, 'criteria': config.criteria, 'rubric_approved': config.rubric_approved,
        'learner_visible': config.learner_visible, 'auto_approve': config.auto_approve,
        'duplicate_check': config.duplicate_check, 'platform_enabled': settings.enabled,
        'unlocked': auto_approve_unlocked(config.resource, settings),
        'unlock_min_reviews': settings.unlock_min_reviews,
        'unlock_min_lower_bound': settings.unlock_min_lower_bound,
        'stats': assignment_stats(config.resource),
    }


class AuthoringAIReviewView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        config, _ = AssignmentReviewConfig.objects.get_or_create(resource=resource)
        return Response(_payload(config))

    def put(self, request, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        config, _ = AssignmentReviewConfig.objects.get_or_create(resource=resource)
        data = request.data
        if 'criteria' in data:
            criteria = _clean_criteria(data['criteria'])
            if criteria is None:
                return Response({'detail': 'Invalid criteria.'}, status=status.HTTP_400_BAD_REQUEST)
            if criteria != config.criteria:
                config.criteria, config.rubric_approved = criteria, False
        for flag in FLAGS:
            if flag in data:
                setattr(config, flag, bool(data[flag]))
        newly_approved = False
        if data.get('rubric_approved') is True and config.criteria:
            newly_approved = not config.rubric_approved
            config.rubric_approved = True
        if 'auto_approve' in data:
            wanted = bool(data['auto_approve'])
            if wanted and not auto_approve_unlocked(resource, AIReviewSettings.get()):
                return Response({'detail': 'Auto-approve unlocks after enough agreeing reviews.'},
                                status=status.HTTP_400_BAD_REQUEST)
            config.auto_approve = wanted
        config.save()
        if newly_approved:
            from hub.tasks import translate_review_criteria
            translate_review_criteria.delay(config.id)
            config.refresh_from_db()
        return Response(_payload(config))


class AuthoringAIReviewDraftView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        course = resource.activity.module.course
        try:
            criteria = model.draft_rubric(
                title=resource.title or resource.activity.title, instructions=resource.instructions,
                language=course.source_language or 'en', model=AIReviewSettings.get().model_name,
            )
        except model.ModelOffline:
            return Response({'detail': 'The AI server is not reachable right now.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except model.ReviewModelError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'criteria': criteria})


class AuthoringAIReviewExamplesView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        return Response([_example(e) for e in resource.ai_review_examples.all()])

    def post(self, request, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        if resource.ai_review_examples.count() >= MAX_EXAMPLES:
            return Response({'detail': f'At most {MAX_EXAMPLES} examples.'}, status=status.HTTP_400_BAD_REQUEST)
        verdict = request.data.get('verdict')
        text = str(request.data.get('text', '')).strip()
        if verdict not in ('approve', 'changes_requested') or not text:
            return Response({'detail': 'An example needs text and a verdict.'}, status=status.HTTP_400_BAD_REQUEST)
        example = ReviewExample.objects.create(resource=resource, text=text[:8000], verdict=verdict,
                                               reason=str(request.data.get('reason', ''))[:1000], created_by=request.user)
        return Response(_example(example), status=status.HTTP_201_CREATED)


class AuthoringAIReviewExampleView(APIView):
    permission_classes = [IsContentCreator]

    def delete(self, request, example_pk, **kw):
        resource, failure = _resource(request, **kw)
        if failure:
            return failure
        deleted, _ = resource.ai_review_examples.filter(pk=example_pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT if deleted else status.HTTP_404_NOT_FOUND)


def _example(e):
    return {'id': e.id, 'text': e.text, 'verdict': e.verdict, 'reason': e.reason,
            'from_submission': e.source_submission_id is not None, 'created_at': e.created_at}
```

`backend/hub/urls.py`: import the four views and add, beside `authoring-resource-h5p`:

```python
    path('authoring/courses/<int:pk>/modules/<int:module_pk>/lessons/<int:lesson_pk>/resources/<int:resource_pk>/ai-review/', AuthoringAIReviewView.as_view(), name='authoring-ai-review'),
    path('authoring/courses/<int:pk>/modules/<int:module_pk>/lessons/<int:lesson_pk>/resources/<int:resource_pk>/ai-review/draft/', AuthoringAIReviewDraftView.as_view(), name='authoring-ai-review-draft'),
    path('authoring/courses/<int:pk>/modules/<int:module_pk>/lessons/<int:lesson_pk>/resources/<int:resource_pk>/ai-review/examples/', AuthoringAIReviewExamplesView.as_view(), name='authoring-ai-review-examples'),
    path('authoring/courses/<int:pk>/modules/<int:module_pk>/lessons/<int:lesson_pk>/resources/<int:resource_pk>/ai-review/examples/<int:example_pk>/', AuthoringAIReviewExampleView.as_view(), name='authoring-ai-review-example'),
```

`backend/hub/tasks.py`: add

```python
@shared_task
def translate_review_criteria(config_id: int) -> None:
    """Criterion names in each of the course's translated languages, so the
    learner's pre-check reads in their language."""
    from hub.models import AssignmentReviewConfig
    from hub.translation import TranslationError, translate_text
    from hub.translation_sync import _target_langs
    config = AssignmentReviewConfig.objects.select_related('resource__activity__module__course').get(pk=config_id)
    course = config.resource.activity.module.course
    source = course.source_language or 'en'
    translations = dict(config.criteria_translations or {})
    for lang in _target_langs(course):
        try:
            translations[lang] = {c['id']: translate_text(c['name'], source, lang) for c in config.criteria}
        except TranslationError:
            continue
    AssignmentReviewConfig.objects.filter(pk=config_id).update(criteria_translations=translations)
```

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_authoring -v 2`
  - Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/views/ai_review.py hub/urls.py hub/tasks.py hub/tests/test_ai_review_authoring.py
git commit -m "feat: AI review authoring API — rubric draft/approval, examples, criteria translation"
git push
```

---

### Task 6: Reviewer and learner API (queue data, filters, examples from submissions, reopen, pre-check, opt-out)

**Files:**
- Modify:
  - `backend/hub/serializers/assignments.py`
  - `backend/hub/views/assignments.py`
  - `backend/hub/urls.py`
  - `backend/hub/serializers/profile.py`: `ProfileSettingsSerializer` gains `ai_training_opt_out`.
  - Wherever the learner activity payload serialises `submission` (`hub/views/learner.py`, `AssignmentSubmissionSerializer(sub).data`): pass `context={'request': request}`.
- Test: `backend/hub/tests/test_ai_review_api.py`

**Interfaces — Produces:**
- `ReviewQueueSerializer.ai_review`: None, or `{status, verdict, confidence, criteria: [{id, name, status, reason}], learner_feedback, reviewer_notes, duplicates, auto_approved, spot_check}`.
- `GET /api/reviews/?filter=` accepts `ai_approve`, `ai_unsure`, `flagged` and `auto_approved`. The last one lists *approved* submissions whose latest AI review has `auto_approved`.
- `POST /api/reviews/<pk>/` accepts an optional `disagreement_reason` and `used_ai_feedback` (boolean).
- `POST /api/reviews/<pk>/example/` (`review-example`): body `{verdict, reason}`; creates an anonymised `ReviewExample`; 400 when the assignment already has 5.
- `POST /api/reviews/<pk>/reopen/` (`review-reopen`): only for auto-approved submissions.
- `AssignmentSubmissionSerializer.ai_precheck`: None unless the assignment is `learner_visible`. Otherwise `{status, criteria: [{name, status, reason}], feedback}`, with criterion names in the request user's language, falling back to the source.
- `GET` and `PATCH /api/profile/settings/` include `ai_training_opt_out`.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_ai_review_api.py`:

```python
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import (
    AIReview,
    AssignmentReviewConfig,
    AssignmentSubmission,
    Enrollment,
    ReviewExample,
    UserProfile,
)

from .test_ai_review_model import CRITERIA
from .test_ai_review_models import make_assignment


class ReviewerAPITests(APITestCase):
    def setUp(self):
        self.course, _, self.activity, self.resource = make_assignment()
        self.config = AssignmentReviewConfig.objects.create(resource=self.resource, enabled=True,
                                                            criteria=CRITERIA, rubric_approved=True,
                                                            criteria_translations={'el': {'c1': 'Τρεις κίνδυνοι'}})
        self.admin = User.objects.create_user('ra_admin', password='x')
        UserProfile.objects.create(user=self.admin, user_type=UserProfile.UserType.ADMIN)
        self.learner = User.objects.create_user('ra_l', password='x', first_name='Maria', last_name='Pappa',
                                                email='maria@example.org')
        UserProfile.objects.create(user=self.learner, language='el')
        Enrollment.objects.create(user=self.learner, course=self.course)
        self.sub = AssignmentSubmission.objects.create(
            user=self.learner, lesson=self.activity, resource=self.resource,
            text='I am Maria Pappa (maria@example.org). Risks: bias, privacy, errors.')
        self.review = AIReview.objects.create(
            submission=self.sub, status='done', rubric=CRITERIA, verdict='approve', confidence=0.9,
            criteria_results=[{'id': 'c1', 'status': 'met', 'reason': 'ok'}, {'id': 'c2', 'status': 'not_met', 'reason': 'no'}],
            learner_feedback='Καλή δουλειά.', reviewer_notes='Fine.')
        self.client.force_authenticate(self.admin)

    def test_queue_includes_ai_review(self):
        row = self.client.get(reverse('review-queue')).data[0]
        self.assertEqual((row['ai_review']['verdict'], row['ai_review']['criteria'][0]['name']), ('approve', 'Three risks'))

    def test_queue_filters(self):
        url = reverse('review-queue')
        self.assertEqual(len(self.client.get(url, {'filter': 'ai_approve'}).data), 1)
        self.assertEqual(len(self.client.get(url, {'filter': 'ai_unsure'}).data), 0)
        self.assertEqual(len(self.client.get(url, {'filter': 'flagged'}).data), 0)
        AssignmentSubmission.objects.filter(pk=self.sub.pk).update(status='approved')
        AIReview.objects.filter(pk=self.review.pk).update(auto_approved=True)
        self.assertEqual(len(self.client.get(url, {'filter': 'auto_approved'}).data), 1)

    def test_decision_records_agreement_and_reason(self):
        self.client.post(reverse('review-action', kwargs={'pk': self.sub.pk}),
                         {'action': 'request_changes', 'feedback': 'More detail', 'disagreement_reason': 'too_lenient',
                          'used_ai_feedback': True}, format='json')
        self.review.refresh_from_db()
        self.assertEqual((self.review.agreed, self.review.disagreement_reason), (False, 'too_lenient'))
        self.assertTrue(self.review.feedback_used)
        self.assertLess(self.review.feedback_similarity, 0.5)

    def test_example_from_submission_is_anonymised(self):
        res = self.client.post(reverse('review-example', kwargs={'pk': self.sub.pk}),
                               {'verdict': 'approve', 'reason': 'Three clear risks'}, format='json')
        self.assertEqual(res.status_code, 201)
        example = ReviewExample.objects.get()
        self.assertNotIn('Maria', example.text)
        self.assertNotIn('Pappa', example.text)
        self.assertNotIn('maria@example.org', example.text)
        self.assertIn('bias, privacy, errors', example.text)
        self.assertEqual(example.source_submission, self.sub)

    def test_reopen_only_auto_approved(self):
        url = reverse('review-reopen', kwargs={'pk': self.sub.pk})
        self.assertEqual(self.client.post(url).status_code, 400)
        AssignmentSubmission.objects.filter(pk=self.sub.pk).update(status='approved')
        AIReview.objects.filter(pk=self.review.pk).update(auto_approved=True)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'pending')


class LearnerAPITests(ReviewerAPITests):
    def precheck(self):
        from types import SimpleNamespace

        from hub.serializers.assignments import AssignmentSubmissionSerializer
        return AssignmentSubmissionSerializer(self.sub, context={'request': SimpleNamespace(user=self.learner)}).data['ai_precheck']

    def test_precheck_hidden_unless_learner_visible(self):
        self.assertIsNone(self.precheck())

    def test_precheck_in_learner_language(self):
        self.config.learner_visible = True
        self.config.save()
        pre = self.precheck()
        self.assertEqual((pre['status'], pre['feedback']), ('done', 'Καλή δουλειά.'))
        self.assertEqual([c['name'] for c in pre['criteria']], ['Τρεις κίνδυνοι', 'Sources'])

    def test_profile_opt_out(self):
        self.client.force_authenticate(self.learner)
        res = self.client.patch(reverse('profile-settings'), {'ai_training_opt_out': True}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.learner.profile.refresh_from_db()
        self.assertTrue(self.learner.profile.ai_training_opt_out)
```

`/api/profile/settings/` (`profile-settings`) takes PATCH with `partial=True`, which is what `ProfilePage.jsx`'s `useSectionSave` sends.

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_api -v 2`
  - Expected: failures and errors (no `ai_review` key, no routes, no opt-out field).

- [ ] **Step 3: Implement.** `backend/hub/serializers/assignments.py`:

```python
from rest_framework import serializers

from hub.models import AIReview, AssignmentSubmission


def latest_ai_review(submission):
    return submission.ai_reviews.exclude(status=AIReview.Status.FAILED).first()


def _criterion_names(review, language=None, translations=None):
    names = {c['id']: c['name'] for c in review.rubric or []}
    if language and translations:
        names.update((translations or {}).get(language, {}))
    return names


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    ai_precheck = serializers.SerializerMethodField()

    class Meta:
        model  = AssignmentSubmission
        fields = ['id', 'status', 'text', 'attachments', 'feedback', 'submitted_at', 'reviewed_at', 'ai_precheck']

    def get_ai_precheck(self, obj):
        config = getattr(obj.resource, 'ai_review_config', None) if obj.resource_id else None
        if config is None or not config.learner_visible:
            return None
        review = latest_ai_review(obj)
        if review is None:
            return None
        if review.status != AIReview.Status.DONE:
            return {'status': review.status, 'criteria': [], 'feedback': ''}
        request = self.context.get('request')
        language = getattr(getattr(getattr(request, 'user', None), 'profile', None), 'language', None)
        names = _criterion_names(review, language, config.criteria_translations)
        return {
            'status': 'done',
            'criteria': [{'name': names.get(c['id'], c['id']), 'status': c['status'], 'reason': c['reason']}
                         for c in review.criteria_results],
            'feedback': review.learner_feedback,
        }


class ReviewQueueSerializer(serializers.ModelSerializer):
    learner_name = serializers.SerializerMethodField()
    learner_id   = serializers.IntegerField(source='user.id', read_only=True)
    course_title = serializers.CharField(source='lesson.module.course.title', read_only=True)
    course_id    = serializers.IntegerField(source='lesson.module.course.id', read_only=True)
    module_title = serializers.CharField(source='lesson.module.title', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    ai_review    = serializers.SerializerMethodField()

    class Meta:
        model  = AssignmentSubmission
        fields = ['id', 'status', 'learner_name', 'learner_id', 'course_id', 'course_title', 'module_title',
                  'lesson_title', 'text', 'attachments', 'feedback', 'submitted_at', 'ai_review']

    def get_learner_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_ai_review(self, obj):
        review = latest_ai_review(obj)
        if review is None:
            return None
        names = _criterion_names(review)
        return {
            'status': review.status, 'verdict': review.verdict, 'confidence': review.confidence,
            'criteria': [{'id': c['id'], 'name': names.get(c['id'], c['id']), 'status': c['status'], 'reason': c['reason']}
                         for c in review.criteria_results],
            'learner_feedback': review.learner_feedback, 'reviewer_notes': review.reviewer_notes,
            'duplicates': (review.checks or {}).get('duplicates', []),
            'auto_approved': review.auto_approved, 'spot_check': review.spot_check,
        }
```

`backend/hub/views/assignments.py`:
- `ReviewQueueView.get` gains the filter:

```python
    FILTERS = ('ai_approve', 'ai_unsure', 'flagged', 'auto_approved')

    def get(self, request):
        wanted = request.query_params.get('filter')
        base = AssignmentSubmission.objects.select_related('user', 'lesson__module__course', 'resource__ai_review_config')
        if wanted == 'auto_approved':
            base = base.filter(status=AssignmentSubmission.Status.APPROVED, ai_reviews__auto_approved=True).distinct()
        else:
            base = base.filter(status=AssignmentSubmission.Status.PENDING)
        rows = list(_reviewer_scope(base, request.user))
        if wanted in ('ai_approve', 'ai_unsure', 'flagged'):
            from hub.serializers.assignments import latest_ai_review

            def keep(sub):
                review = latest_ai_review(sub)
                if review is None or review.status != 'done':
                    return False
                return {'ai_approve': review.verdict == 'approve', 'ai_unsure': review.verdict == 'unsure',
                        'flagged': review.flagged}[wanted]
            rows = [s for s in rows if keep(s)]
        return Response(ReviewQueueSerializer(rows, many=True).data)
```

- Add these views:

```python
def _anonymise(text, user):
    for value in filter(None, [user.get_full_name(), user.first_name, user.last_name, user.username, user.email]):
        text = re.sub(re.escape(value), '[learner]', text, flags=re.I)
    return re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '[email]', text)


class ReviewExampleView(APIView):
    """POST — use this submission (anonymised) as an AI-review example."""
    permission_classes = [IsReviewer]

    def post(self, request, pk):
        submission = AssignmentSubmission.objects.select_related('user', 'resource__activity__module__course').filter(pk=pk).first()
        if submission is None or not submission.resource_id:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_review(request.user, submission):
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        verdict = request.data.get('verdict')
        if verdict not in ('approve', 'changes_requested'):
            return Response({'detail': 'verdict must be approve or changes_requested.'}, status=status.HTTP_400_BAD_REQUEST)
        if submission.resource.ai_review_examples.count() >= 5:
            return Response({'detail': 'This assignment already has 5 examples.'}, status=status.HTTP_400_BAD_REQUEST)
        from hub.models import ReviewExample
        ReviewExample.objects.create(
            resource=submission.resource, text=_anonymise(submission.text or '', submission.user)[:8000],
            verdict=verdict, reason=str(request.data.get('reason', ''))[:1000],
            source_submission=submission, created_by=request.user,
        )
        return Response(status=status.HTTP_201_CREATED)


class ReviewReopenView(APIView):
    """POST — send an auto-approved submission back to the review queue."""
    permission_classes = [IsReviewer]

    def post(self, request, pk):
        submission = AssignmentSubmission.objects.select_related('user', 'lesson__module__course').filter(pk=pk).first()
        if submission is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_review(request.user, submission):
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        if submission.status != AssignmentSubmission.Status.APPROVED or not submission.ai_reviews.filter(auto_approved=True).exists():
            return Response({'detail': 'Only AI-approved submissions can be reopened.'}, status=status.HTTP_400_BAD_REQUEST)
        from hub.assignment_review import reopen_submission
        reopen_submission(submission)
        return Response(AssignmentSubmissionSerializer(submission).data)
```

- Add `import re` at the top and the helper `can_review(user, submission)`. A content creator must be able to edit the course; partners and admins always can, the same rule as in `ReviewActionView`. Use the helper in `ReviewActionView` too, replacing the inline check.

`backend/hub/urls.py`: add `path('reviews/<int:pk>/example/', ReviewExampleView.as_view(), name='review-example')` and `path('reviews/<int:pk>/reopen/', ReviewReopenView.as_view(), name='review-reopen')`.

`backend/hub/serializers/profile.py`: set `ProfileSettingsSerializer.Meta.fields = ['profile_public', 'share_progress', 'ai_training_opt_out']`. If the view saves with `update_fields`, add the field there too.

Learner payload: in `hub/views/learner.py`, where `AssignmentSubmissionSerializer(sub).data` is built, pass `context={'request': request}`. Do the same in the submit views' responses.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_api hub.tests.test_assignment_review hub.tests.test_resource_assignment hub.tests.test_phase2_profile -v 2`
  - Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/serializers hub/views hub/urls.py hub/tests/test_ai_review_api.py
git commit -m "feat: AI review for reviewers and learners — queue data, filters, examples, reopen, pre-check, opt-out"
git push
```

---

### Task 7: Analytics, Excel sheet, timeline

**Files:**
- Modify: `backend/analytics/learning.py`, `backend/analytics/workbook.py`, `backend/analytics/tests/test_workbook.py` (adds the sheet name)
- Test: `backend/analytics/tests/test_ai_review_analytics.py`

**Interfaces — Produces:**
- `CourseData` loads the AI reviews of the course's submissions (latest per submission) in `self.ai_reviews = {(uid, rid): AIReview}`.
- Assignment notes gain `ai`: `hub.ai_review.metrics.summarise(...)` over the assignment's latest AI reviews (including `kappa`, `approve_lower_bound`, `feedback_unchanged` and `most_missed_name`), or None when there are none.
- `resource_detail` for an assignment gains `ai_verdict` and `ai_auto_approved`.
- Workbook `SHEET_NAMES` gains `'AI reviews'` after `'H5P answers'`, with these columns: BASE + `Module ID`, `Activity ID`, `Activity`, `Resource ID`, `Assignment`, `Submitted at`, `AI status`, `AI verdict`, `Confidence`, one column per criterion `Criterion <id>: <name>` (written as `id=status` pairs in one `Criteria` column), `Human verdict`, `Agreed`, `Disagreement reason`, `Used AI feedback`, `Feedback similarity`, `Auto-approved`, `Spot check`, `Duplicate flag`, `Model`, `Prompt version`.

- [ ] **Step 1: Write the failing tests.** `backend/analytics/tests/test_ai_review_analytics.py`:

```python
from django.test import TestCase

from analytics.learning import CourseData, content_tree, learner_timeline
from analytics.workbook import SHEET_NAMES, build_learning_workbook
from hub.models import (
    Activity,
    AIReview,
    AssignmentSubmission,
    Course,
    LearningPillar,
    Module,
    Resource,
    UserProfile,
)

from .fixtures import NOW, enroll, make_user
from .test_workbook import by_learner


class AIReviewAnalyticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        creator = make_user('aia_cc', UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-aia', order=1)
        cls.course = Course.objects.create(title='AI', pillar=pillar, level='beginner', duration_hours=1,
                                           is_published=True, created_by=creator)
        module = Module.objects.create(course=cls.course, title='M', order=1)
        activity = Activity.objects.create(module=module, title='Task', order=1)
        cls.r = Resource.objects.create(activity=activity, type='assignment', order=1, title='Risks')
        cls.ann, cls.bob = make_user('ann', first='Ann'), make_user('bob', first='Bob')
        for u, verdict, human, agreed in ((cls.ann, 'approve', 'approve', True), (cls.bob, 'approve', 'changes_requested', False)):
            enroll(u, cls.course)
            sub = AssignmentSubmission.objects.create(user=u, lesson=activity, resource=cls.r, text='t',
                                                      status='approved' if human == 'approve' else 'changes_requested')
            AIReview.objects.create(submission=sub, status='done', verdict=verdict, confidence=0.9, human_verdict=human,
                                    agreed=agreed, rubric=[{'id': 'c1', 'name': 'Three risks', 'met': '', 'required': True}],
                                    criteria_results=[{'id': 'c1', 'status': 'met', 'reason': ''}],
                                    model_name='qwen2.5vl:32b', prompt_version='p1',
                                    disagreement_reason='' if agreed else 'too_lenient')

    def test_assignment_notes_include_ai_agreement(self):
        notes = content_tree(CourseData(self.course, now=NOW))['modules'][0]['activities'][0]['resources'][0]['notes']
        self.assertEqual((notes['ai']['reviews'], notes['ai']['agreement']), (2, 0.5))
        self.assertEqual(notes['ai']['kappa'], 0.0)        # the AI approved both: no skill beyond chance

    def test_timeline_shows_ai_verdict(self):
        res = learner_timeline(CourseData(self.course, now=NOW), self.bob.id)['modules'][0]['activities'][0]['resources'][0]
        self.assertEqual(res['ai_verdict'], 'approve')

    def test_ai_reviews_sheet(self):
        self.assertIn('AI reviews', SHEET_NAMES)
        wb = build_learning_workbook([self.course], now=NOW)
        [row] = by_learner(wb['AI reviews'], 'Bob')
        self.assertEqual((row['AI verdict'], row['Human verdict'], row['Agreed'], row['Disagreement reason']),
                         ('approve', 'changes_requested', 'no', 'too_lenient'))
        self.assertEqual(row['Criteria'], 'c1=met')
```

In `analytics/tests/test_workbook.py`, update `test_sheet_order` so the expected list has `'AI reviews'` after `'H5P answers'`.

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test analytics -v 2`
  - Expected: `KeyError: 'ai'`, a missing `ai_verdict`, and sheet-order failures.

- [ ] **Step 3: Implement.**

In `CourseData.__init__`, after `self.submissions` is built:

```python
        from hub.models import AIReview
        self.ai_reviews = {}
        for review in (AIReview.objects
                       .filter(submission__resource__activity__module__course=course, submission__user_id__in=user_ids)
                       .exclude(status=AIReview.Status.FAILED)
                       .select_related('submission').order_by('created_at')):
            self.ai_reviews[(review.submission.user_id, review.submission.resource_id)] = review   # latest wins
```

In `resource_notes`, for `assignment`, add to the returned dict:

```python
            'ai': _ai_notes([cd.ai_reviews[(uid, resource.id)] for uid in uids if (uid, resource.id) in cd.ai_reviews]),
```

and add this helper:

```python
def _ai_notes(reviews):
    from hub.ai_review.metrics import summarise
    return summarise(reviews) if reviews else None
```

In `resource_detail`, add:

```python
            'ai_verdict': (cd.ai_reviews[(uid, resource.id)].verdict if kind == 'assignment' and (uid, resource.id) in cd.ai_reviews else None),
            'ai_auto_approved': bool(kind == 'assignment' and (uid, resource.id) in cd.ai_reviews and cd.ai_reviews[(uid, resource.id)].auto_approved),
```

Here `cd` is `self`; adapt to the method's existing variable names.

`analytics/workbook.py`:
- add `'AI reviews'` to `SHEET_NAMES` after `'H5P answers'`;
- add `HEADERS['AI reviews'] = BASE + ['Module ID', 'Activity ID', 'Activity', 'Resource ID', 'Assignment', 'Submitted at', 'AI status', 'AI verdict', 'Confidence', 'Criteria', 'Human verdict', 'Agreed', 'Disagreement reason', 'Used AI feedback', 'Feedback similarity', 'Auto-approved', 'Spot check', 'Duplicate flag', 'Model', 'Prompt version']`;
- add this generator and register it in `ROWS` after `'H5P answers'`:

```python
def _ai_reviews(cd):
    for e in cd.enrollments:
        for r in cd.resources:
            review = cd.ai_reviews.get((e.user_id, r.id))
            if r.type != 'assignment' or review is None:
                continue
            yield _base(cd, e.user) + [
                r.activity.module_id, r.activity_id, r.activity.title, r.id, resource_label(r),
                iso(review.submission.submitted_at), review.status, review.verdict, blank(review.confidence),
                ', '.join(f"{c['id']}={c['status']}" for c in review.criteria_results or []),
                review.human_verdict, '' if review.agreed is None else yes_no(review.agreed),
                review.disagreement_reason, yes_no(review.feedback_used), blank(review.feedback_similarity),
                yes_no(review.auto_approved), yes_no(review.spot_check),
                yes_no(review.flagged), review.model_name, review.prompt_version,
            ]
```

- add a README line: `'AI reviews: one row per learner × assignment (latest AI review); Agreed compares the AI verdict with the human decision; Feedback similarity is 1.0 when the reviewer sent the AI feedback unchanged.'`

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test analytics -v 2`
  - Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add analytics
git commit -m "feat: AI review agreement in analytics, timeline and an 'AI reviews' Excel sheet"
git push
```

---

### Task 8: Benchmark and training-export commands

**Files:**
- Create: `backend/hub/management/commands/ai_review_benchmark.py`, `backend/hub/management/commands/ai_review_export.py`
- Test: `backend/hub/tests/test_ai_review_commands.py`

**Interfaces — Produces:**
- `manage.py ai_review_benchmark --models m1,m2 [--limit 30] [--out file.xlsx]`:
  - runs `model.review_submission` on human-decided submissions (approved or changes requested) of assignments with a non-empty rubric, each model in turn;
  - prints agreement, average seconds and failures per model;
  - writes an xlsx with sheets `Summary` and `Answers`, one row per model × submission;
  - stores nothing in the database.
- `manage.py ai_review_export --out file.jsonl`:
  - one JSON line per human-decided AI review: `{assignment_id, instructions, rubric, submission_text (anonymised), ai: {...}, human_verdict, feedback (anonymised)}`;
  - skips learners with `ai_training_opt_out`;
  - images are not exported.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_ai_review_commands.py`:

```python
import io
import json
import tempfile
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from openpyxl import load_workbook

from hub.ai_review import model
from hub.models import AIReview, AssignmentReviewConfig, AssignmentSubmission, UserProfile

from .test_ai_review_model import CRITERIA, answer
from .test_ai_review_models import make_assignment


class CommandTests(TestCase):
    def setUp(self):
        _, _, self.activity, self.resource = make_assignment()
        AssignmentReviewConfig.objects.create(resource=self.resource, enabled=True, criteria=CRITERIA, rubric_approved=True)
        self.subs = []
        for name, status, opt_out in (('ann', 'approved', False), ('bob', 'changes_requested', True)):
            user = User.objects.create_user(name, password='x', first_name=name.title(), email=f'{name}@example.org')
            UserProfile.objects.create(user=user, ai_training_opt_out=opt_out)
            sub = AssignmentSubmission.objects.create(user=user, lesson=self.activity, resource=self.resource,
                                                      text=f'{name.title()} wrote: bias, privacy', status=status,
                                                      feedback=f'Thanks {name.title()}')
            AIReview.objects.create(submission=sub, status='done', rubric=CRITERIA, verdict='approve', confidence=0.9,
                                    human_verdict='approve' if status == 'approved' else 'changes_requested',
                                    agreed=status == 'approved')
            self.subs.append(sub)

    def test_benchmark_writes_summary(self):
        out = Path(tempfile.mkdtemp()) / 'bench.xlsx'
        with mock.patch.object(model, '_chat', return_value=answer()):
            call_command('ai_review_benchmark', '--models', 'm1,m2', '--out', str(out), stdout=io.StringIO())
        wb = load_workbook(out)
        summary = list(wb['Summary'].values)
        self.assertEqual(summary[0][:3], ('Model', 'Submissions', 'Agreement'))
        self.assertEqual({r[0] for r in summary[1:]}, {'m1', 'm2'})
        self.assertEqual(wb['Answers'].max_row, 1 + 2 * 2)
        self.assertEqual(AIReview.objects.count(), 2)            # nothing stored

    def test_export_excludes_opted_out_and_anonymises(self):
        out = Path(tempfile.mkdtemp()) / 'train.jsonl'
        call_command('ai_review_export', '--out', str(out), stdout=io.StringIO())
        lines = [json.loads(line) for line in out.read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(lines), 1)                          # Bob opted out
        self.assertNotIn('Ann', lines[0]['submission_text'] + lines[0]['feedback'])
        self.assertEqual(lines[0]['human_verdict'], 'approve')
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_commands -v 2`
  - Expected: `Unknown command: 'ai_review_benchmark'`.

- [ ] **Step 3: Implement.** Move `_anonymise` from `hub/views/assignments.py` into `hub/ai_review/evidence.py` as `anonymise(text, user)`, and import it in both places, so there's one implementation.

`backend/hub/management/commands/ai_review_benchmark.py`:

```python
"""Compare candidate models on submissions humans already decided.

    uv run manage.py ai_review_benchmark --models qwen2.5vl:32b,gemma3:27b --limit 30
"""
import time

from django.core.management.base import BaseCommand
from openpyxl import Workbook

from hub.ai_review import model
from hub.ai_review.evidence import gather
from hub.models import AssignmentSubmission

HUMAN = {'approved': 'approve', 'changes_requested': 'changes_requested'}


class Command(BaseCommand):
    help = 'Benchmark AI review models against human decisions (nothing is stored).'

    def add_arguments(self, parser):
        parser.add_argument('--models', required=True, help='comma-separated Ollama model names')
        parser.add_argument('--limit', type=int, default=30)
        parser.add_argument('--out', default='ai_review_benchmark.xlsx')

    def handle(self, *args, **opts):
        subs = list(
            AssignmentSubmission.objects.filter(status__in=HUMAN, resource__ai_review_config__isnull=False)
            .exclude(resource__ai_review_config__criteria=[])
            .select_related('user__profile', 'resource__ai_review_config').order_by('-submitted_at')[:opts['limit']]
        )
        wb = Workbook()
        summary = wb.active
        summary.title = 'Summary'
        summary.append(['Model', 'Submissions', 'Agreement', 'Approve agreement', 'Avg seconds', 'Failures'])
        answers = wb.create_sheet('Answers')
        answers.append(['Model', 'Submission ID', 'Human', 'AI verdict', 'Confidence', 'Seconds', 'Error', 'Feedback'])
        for name in [m.strip() for m in opts['models'].split(',') if m.strip()]:
            agree = approve_total = approve_ok = failures = 0
            seconds = []
            for sub in subs:
                config = sub.resource.ai_review_config
                started = time.monotonic()
                try:
                    result = model.review_submission(
                        instructions=sub.resource.instructions, criteria=config.criteria,
                        examples=[{'text': e.text, 'verdict': e.verdict, 'reason': e.reason}
                                  for e in sub.resource.ai_review_examples.exclude(source_submission=sub)[:5]],
                        evidence=gather(sub), checks={}, language=getattr(sub.user.profile, 'language', 'en'), model=name)
                    error = ''
                except model.ReviewModelError as exc:
                    result, error = None, str(exc)
                    failures += 1
                took = round(time.monotonic() - started, 1)
                seconds.append(took)
                human = HUMAN[sub.status]
                if result:
                    agree += result['verdict'] == human
                    if result['verdict'] == 'approve':
                        approve_total += 1
                        approve_ok += human == 'approve'
                answers.append([name, sub.id, human, result and result['verdict'], result and result['confidence'],
                                took, error, result and result['learner_feedback']])
            n = len(subs) or 1
            row = [name, len(subs), round(agree / n, 3), round(approve_ok / approve_total, 3) if approve_total else None,
                   round(sum(seconds) / n, 1), failures]
            summary.append(row)
            self.stdout.write(f'{name}: agreement {row[2]}, approve agreement {row[3]}, avg {row[4]} s, failures {failures}')
        wb.save(opts['out'])
        self.stdout.write(f'Wrote {opts["out"]}')
```

`backend/hub/management/commands/ai_review_export.py`:

```python
"""Anonymised training data for a future fine-tune (JSON lines)."""
import json

from django.core.management.base import BaseCommand

from hub.ai_review.evidence import anonymise
from hub.models import AIReview


class Command(BaseCommand):
    help = 'Export human-decided AI reviews as anonymised JSON lines (opted-out learners excluded).'

    def add_arguments(self, parser):
        parser.add_argument('--out', default='ai_review_training.jsonl')

    def handle(self, *args, **opts):
        reviews = (AIReview.objects.filter(status='done').exclude(human_verdict='')
                   .exclude(submission__user__profile__ai_training_opt_out=True)
                   .select_related('submission__user', 'submission__resource'))
        count = 0
        with open(opts['out'], 'w', encoding='utf-8') as out:
            for r in reviews:
                sub, user = r.submission, r.submission.user
                out.write(json.dumps({
                    'assignment_id': sub.resource_id,
                    'instructions': sub.resource.instructions if sub.resource_id else '',
                    'rubric': r.rubric,
                    'submission_text': anonymise(sub.text or '', user),
                    'ai': {'verdict': r.verdict, 'confidence': r.confidence, 'criteria': r.criteria_results},
                    'human_verdict': r.human_verdict,
                    'feedback': anonymise(sub.feedback or '', user),
                }, ensure_ascii=False) + '\n')
                count += 1
        self.stdout.write(f'Wrote {count} examples to {opts["out"]}')
```

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_ai_review_commands hub.tests.test_ai_review_api -v 2`
  - Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/management/commands/ai_review_benchmark.py hub/management/commands/ai_review_export.py hub/ai_review/evidence.py hub/views/assignments.py hub/tests/test_ai_review_commands.py
git commit -m "feat: AI review benchmark and anonymised training export commands"
git push
```

---

### Task 9: Frontend: author panel, reviewer AI panel, learner pre-check, analytics, profile, privacy, locales

**Files:**
- Create: `frontend/src/components/reviews/aiReview.js` and `aiReview.test.js`, `frontend/src/components/authoring/AIReviewPanel.jsx` and `.css`
- Modify:
  - `frontend/src/components/authoring/ResourceEditor.jsx`
  - `frontend/src/pages/ModuleEditorPage.jsx`: pass `resourceUrl` to the editor for AI review, as for H5P.
  - `frontend/src/pages/ReviewsPage.jsx` and `.css`
  - `frontend/src/components/learner/ResourceView.jsx`
  - `frontend/src/components/analytics/ContentTree.jsx`, `LearnerTimeline.jsx`
  - `frontend/src/pages/ProfilePage.jsx`, `frontend/src/pages/PrivacyPage.jsx`
  - `frontend/src/locales/*.json`

**Interfaces:**
- **Consumes:** the APIs from Tasks 5–7.
- **Produces** pure helpers in `aiReview.js`:
  - `verdictTone(verdict)`: `'approve'` → `'ok'`, `'changes_requested'` → `'bad'`, otherwise `'unsure'`;
  - `statusIcon(status)`: `'met'` → `'check'`, `'partly_met'` → `'half'`, `'not_met'` → `'cross'`, otherwise `'question'`;
  - `percent(x)`: `0.953` → `'95%'`, `null` → `'—'`;
  - `kappaText(k)`: `0.4` → `'0.40'`, `null` → `'—'`;
  - `disagrees(aiVerdict, action)`: true when the AI said `approve` or `changes_requested` and the human chose the other.

- [ ] **Step 1: Write the failing helper tests.** `frontend/src/components/reviews/aiReview.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { disagrees, kappaText, percent, statusIcon, verdictTone } from './aiReview.js'

test('verdict tone and criterion icons', () => {
  assert.equal(verdictTone('approve'), 'ok')
  assert.equal(verdictTone('changes_requested'), 'bad')
  assert.equal(verdictTone('unsure'), 'unsure')
  assert.deepEqual(['met', 'partly_met', 'not_met', 'cannot_judge'].map(statusIcon), ['check', 'half', 'cross', 'question'])
})

test('percent and kappa', () => {
  assert.equal(percent(0.953), '95%')
  assert.equal(percent(null), '—')
  assert.equal(kappaText(0.4), '0.40')
  assert.equal(kappaText(null), '—')
})

test('a human decision disagrees only with a definite AI verdict', () => {
  assert.equal(disagrees('approve', 'request_changes'), true)
  assert.equal(disagrees('changes_requested', 'approve'), true)
  assert.equal(disagrees('approve', 'approve'), false)
  assert.equal(disagrees('unsure', 'approve'), false)
  assert.equal(disagrees(undefined, 'approve'), false)
})
```

Run `npm test` from `frontend/`. Expected: `ERR_MODULE_NOT_FOUND …/aiReview.js`.

- [ ] **Step 2: Implement the helpers.** `frontend/src/components/reviews/aiReview.js`:

```js
// Small display helpers for AI review data (reviews page, editor, learner box).

export const verdictTone = (verdict) => (
  verdict === 'approve' ? 'ok' : verdict === 'changes_requested' ? 'bad' : 'unsure'
)

const ICONS = { met: 'check', partly_met: 'half', not_met: 'cross' }
export const statusIcon = (status) => ICONS[status] ?? 'question'

export const percent = (x) => (x == null ? '—' : `${Math.round(x * 100)}%`)

export const kappaText = (k) => (k == null ? '—' : k.toFixed(2))

const HUMAN = { approve: 'approve', request_changes: 'changes_requested' }
export const disagrees = (aiVerdict, action) => (
  ['approve', 'changes_requested'].includes(aiVerdict) && HUMAN[action] !== aiVerdict
)
```

Run `npm test`. Expected: pass.

- [ ] **Step 3: Author panel.** `frontend/src/components/authoring/AIReviewPanel.jsx`. Shown in `ResourceEditor` for `resource.type === 'assignment' && !translating`, under the instructions, with `baseUrl={`${uploadUrl.replace(/h5p\/$/, '')}ai-review/`}`. Simpler: pass `aiReviewUrl` from `ModuleEditorPage` as `${resourceUrl(resource.id)}ai-review/` (`uploadUrl` there ends in `h5p/`, so `resourceUrl` is the shared base).

The panel:
- loads `GET aiReviewUrl` on mount;
- shows "AI review" with a toggle (`enabled`) and a note if `platform_enabled` is false ("Switched off for the platform — an admin can enable it");
- **rubric editor:** rows with name, met and a required checkbox, plus add, remove and up/down buttons; **"Draft with AI"** (`POST draft/`, which fills the rows with a spinner and shows the 503 message on failure); **"Approve rubric"** (`PUT` with `{criteria, rubric_approved: true}`). An "Approved ✓" badge shows when approved, and a "Changes not yet approved" warning when there are local edits;
- **examples:** a list of `GET examples/`, each with text, verdict and reason, and remove (`DELETE examples/<id>/`); an "Add example" form (textarea, verdict select, reason; `POST examples/`); disabled at 5;
- **checkboxes:** "Check for duplicate files" (`duplicate_check`) and "Learners see the AI pre-check immediately" (`learner_visible`). Each saves with `PUT` straight away. Below them, a disabled "Trust-AI Lab scenario check" row labelled "coming soon" (`authoring.aiReview.trustAiSoon`);
- **"Approve clear passes automatically":** disabled unless `unlocked`, with the hint `authoring.aiReview.autoLocked` filled with `min` = `unlock_min_reviews`, `pct` = `percent(unlock_min_lower_bound)`, `decided` = `stats.decided` and `now` = `percent(stats.approve_lower_bound)`;
- **stats line:** `authoring.aiReview.stats` with `reviews`, `agreement` = `percent(agreement)`, `kappa` = `kappaText(kappa)`, `approvals` = `percent(approve_agreement)`, `unchanged` = `percent(feedback_unchanged)` and `missed` = `most_missed_name ?? '—'`.

Implement with `useState` and `useEffect` like `H5PPanel` (`client` calls, error text via `t('authoring.aiReview.errors.*')`). Keep one component with small inner components: `CriteriaEditor`, `ExamplesList`. CSS prefix `.air-`.

- [ ] **Step 4: Reviewer AI panel.** `ReviewsPage.jsx`:
- A **filter** select above the list (*All waiting*, *AI says approve*, *AI unsure*, *Flagged*, *Auto-approved*), which calls `client.get('/reviews/', { params: { filter } })`.
- In `SubmissionRow`, when `sub.ai_review?.status === 'done'`, an **AI panel** above the feedback box:
  - a verdict chip using the tone class `rv-ai--${verdictTone(v)}`, with confidence via `percent()`;
  - a criteria list with an icon from `statusIcon()` (✓ / ◐ / ✗ / ? via lucide `CheckCircle2` / `CircleDot` / `XCircle` / `HelpCircle`) plus name and reason;
  - the duplicates as warning lines, "Same file as {learner} ({match})";
  - the reviewer notes;
  - a **"Use AI feedback"** button that sets `feedback` to `ai_review.learner_feedback` and sets a `usedAI` state to true. The decision POST sends `used_ai_feedback: usedAI`, so the backend can measure how much the reviewer edited it.
- When the AI review is queued or running: "AI pre-check running…".
- **Disagreement reason:** when the reviewer clicks an action and `disagrees(sub.ai_review?.verdict, action)`, show an inline select (*missed evidence*, *too strict*, *too lenient*, *misread the image*, *other*, *skip*) before sending. Include `disagreement_reason` in the POST body. Keep it one extra step: the select appears with "Send" and "Skip".
- **"Use as AI example"** button: `POST /reviews/<id>/example/` with `{ verdict: 'approve' | 'changes_requested', reason }`, from a small inline form; shows "Added" or the error.
- **Auto-approved filter:** rows show "Approved by AI" and a **Reopen** button (`POST /reviews/<id>/reopen/`), and the row disappears when done.

- [ ] **Step 5: Learner pre-check and resubmission.** `ResourceView.jsx` `AssignmentBody`:
- change `const locked = status === 'pending' || status === 'approved'` to `const locked = status === 'approved'`, so a pending submission can be revised and resubmitted;
- keep the pending banner;
- below the banner, if `submission?.ai_precheck`:
  - status `queued` or `running`: "AI pre-check in progress…";
  - status `done`: a box titled "AI pre-check (preliminary)" listing criteria with icons from `statusIcon()`, plus name and reason, then the feedback paragraph, then "A reviewer will confirm.";
- the submit button label for a pending submission is "Update submission".

- [ ] **Step 6: Analytics, profile, privacy.**
- **`ContentTree.jsx` `ResourceNotes`:** for an assignment with `notes.ai`, push `t('analytics.course.notes.aiAgreement', { pct: Math.round(notes.ai.agreement * 100) })` when `agreement != null`, then `t('analytics.course.notes.aiKappa', { kappa: kappaText(notes.ai.kappa) })` when `kappa != null`, then `t('analytics.course.notes.aiReviews', { count: notes.ai.reviews })`.
- **`LearnerTimeline.jsx` `ResourceDetails`:** when `r.ai_verdict`, push `t('analytics.course.detail.aiVerdict', { verdict: t(`reviews.ai.verdict.${r.ai_verdict}`) })`, plus `t('analytics.course.detail.aiAuto')` if `r.ai_auto_approved`.
- **`ProfilePage.jsx` `PrivacySection`:** add `ai_training_opt_out: false` to the initial form, and a third toggle row: `profile.privacy.aiOptOutTitle` / `aiOptOutSub`.
- **`PrivacyPage.jsx`:** insert a section after "11. Learning activity records", renumbering "Changes and complaints" to 13:

```jsx
      <h2>12. AI review of assignments</h2>
      <p>
        Assignment submissions may be checked by an AI model running on servers operated by the
        AIDEA project (not an external AI service). It compares your submission with the
        assignment&rsquo;s criteria and suggests feedback. A person makes or confirms every decision to
        ask for changes; when the course enables it, clear passes may be approved automatically and
        are spot-checked by a person. Anonymised submissions and review decisions may be used to
        improve the AI reviewer. You can opt out of that use in your profile&rsquo;s privacy settings;
        your submissions are still reviewed as usual.
      </p>
```

- [ ] **Step 7: Locales (9 languages).** Add these keys. `en` is shown; write real translations for el, fr, es, it, fi, sv, no and de in each locale's existing tone, keeping `{{placeholders}}`, with a Node script that preserves indent, line endings and the final newline:

```json
"authoring": { "aiReview": {
  "title": "AI review", "enable": "Use the AI reviewer for this assignment",
  "platformOff": "AI review is switched off for the platform — an admin can enable it.",
  "rubric": "Rubric (criteria)", "criterionName": "Criterion", "criterionMet": "Met when…", "required": "Required",
  "addCriterion": "Add criterion", "draft": "Draft with AI", "drafting": "Drafting…",
  "approve": "Approve rubric", "approved": "Rubric approved", "unapproved": "Changes not yet approved",
  "examples": "Examples", "addExample": "Add example", "exampleText": "Example submission", "verdict": "Correct verdict",
  "reason": "Why", "maxExamples": "At most 5 examples.",
  "duplicateCheck": "Check for duplicate files", "learnerVisible": "Learners see the AI pre-check immediately",
  "trustAiSoon": "Trust-AI Lab scenario check (coming soon)",
  "autoApprove": "Approve clear passes automatically",
  "autoLocked": "Unlocks once at least {{min}} AI reviews are human-checked and approvals agree reliably (95% lower bound ≥ {{pct}}) — now {{decided}} reviews, lower bound {{now}}.",
  "stats": "{{reviews}} AI reviews · agreement {{agreement}} (κ {{kappa}}) · approvals {{approvals}} · AI feedback sent unchanged {{unchanged}} · most missed: {{missed}}",
  "errors": { "offline": "The AI server is not reachable right now. Try again later.", "generic": "Something went wrong. Please try again." }
}},
"reviews": { "ai": {
  "title": "AI pre-check", "running": "AI pre-check running…", "confidence": "confidence {{pct}}",
  "verdict": { "approve": "Suggests approve", "changes_requested": "Suggests changes", "unsure": "Unsure" },
  "useFeedback": "Use AI feedback", "duplicate": "Same file as {{learner}} ({{match}})", "notes": "AI notes",
  "whyDisagree": "Why do you disagree with the AI? (optional)",
  "reason": { "missed_evidence": "Missed evidence", "too_strict": "Too strict", "too_lenient": "Too lenient", "misread_image": "Misread the image", "other": "Other" },
  "send": "Send", "skip": "Skip", "useAsExample": "Use as AI example", "exampleAdded": "Added as example",
  "filter": { "all": "All waiting", "ai_approve": "AI says approve", "ai_unsure": "AI unsure", "flagged": "Flagged", "auto_approved": "Approved by AI" },
  "approvedByAI": "Approved by AI", "reopen": "Reopen"
}},
"lesson": { "assignment": {
  "precheckTitle": "AI pre-check (preliminary)", "precheckRunning": "AI pre-check in progress…",
  "precheckConfirm": "A reviewer will confirm.", "update": "Update submission"
}},
"analytics": { "course": {
  "notes": { "aiAgreement": "AI agrees with reviewers {{pct}}%", "aiKappa": "κ {{kappa}} beyond chance", "aiReviews": "{{count}} AI reviews" },
  "detail": { "aiVerdict": "AI: {{verdict}}", "aiAuto": "approved by AI" }
}},
"profile": { "privacy": {
  "aiOptOutTitle": "Don't use my assignments to improve the AI reviewer",
  "aiOptOutSub": "Your submissions are still reviewed as usual."
}}
```

Merge these into the existing objects; don't replace them.

- [ ] **Step 8: Verify.**
  - From `frontend/`: `npm run lint`, `npm test`, `node scripts/check-locales.mjs` and `VITE_API_URL=http://localhost:8000/api npm run build`. Expected: all clean.
  - Manual check:
    - **As demo_creator:** open an assignment and the AI review panel; Draft with AI (with a reachable model) or add criteria by hand; approve; add an example.
    - **As demo_teacher:** submit, then revise while pending.
    - **On the Reviews page:** filters, the AI panel and "Use AI feedback".

- [ ] **Step 9: Commit** (from the repository root).

```bash
git add frontend
git commit -m "feat: AI reviewer UI — author panel, reviewer AI panel, learner pre-check, analytics, opt-out, privacy"
git push
```

---

### Task 10: Full verification, docs, rollout note

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md.**
  - Under backend commands, add `.venv/Scripts/uv.exe run manage.py ai_review_benchmark --models a,b  # Compare AI review models on decided submissions` and `… ai_review_export --out train.jsonl  # Anonymised training data`.
  - Under API endpoints, add `…/resources/<r>/ai-review/` (config, `draft/`, `examples/`), `reviews/?filter=`, `reviews/<id>/example/` and `reviews/<id>/reopen/`.

- [ ] **Step 2: Full verification.** From `backend/`: `"$UV" run ruff check .`; `"$UV" run coverage run manage.py test hub analytics --verbosity=1`; `"$UV" run coverage report --fail-under=70`; `"$UV" run manage.py makemigrations --check --dry-run`. From `frontend/`: `npm run lint && npm test && node scripts/check-locales.mjs && VITE_API_URL=http://localhost:8000/api npm run build`. Expected: all pass, and "No changes detected".

- [ ] **Step 3: Commit.**

```bash
git add CLAUDE.md
git commit -m "docs: AI reviewer commands and endpoints"
git push
```

- [ ] **Step 4: Rollout note for the user.**

On the NTUA server:
- `ollama pull qwen2.5vl:32b` (and `gemma3:27b` to compare);
- pin the reviewer to the second GPU, for example `CUDA_VISIBLE_DEVICES=1` for that Ollama instance, or Ollama's GPU scheduling.

On the VM (with `COMPOSE_FILE` set):

```bash
git pull
docker compose up -d --build backend celery celery-beat frontend
docker compose exec -T backend uv run python manage.py migrate      # 0064_ai_review, 0065
docker compose exec -T backend uv run python manage.py ai_review_benchmark --models qwen2.5vl:32b,gemma3:27b --limit 30
```

Then:
1. Django admin → AI review settings: set the model, then tick **enabled**.
2. In one or two assignments, draft and approve a rubric, and switch AI review on (reviewers only).
3. Watch the agreement numbers.
