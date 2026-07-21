# Course-Content Translation (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Content creators translate a course's text into any of the 9 languages on demand (via the user's self-hosted Ollama), edit specific translations, and learners see course content in their profile language with fallback to the original.

**Architecture:** An autossh sidecar tunnels to Ollama; a mockable `translate_text` client; per-model `translations` JSON storage; a Celery `translate_course` task + authoring endpoint; learner serializers resolve fields to the viewer's language. Spec: `docs/superpowers/specs/2026-07-21-course-content-translation-design.md`.

**Tech Stack:** Django/DRF, Celery, Ollama (`/api/generate`), stdlib `urllib` (no new dep), React authoring editors.

## Global Constraints

- 9 languages: en/el/fr/es/it/fi/sv/no/de (en = default). Backend runner from `backend/`: `.venv/Scripts/uv.exe run ...` (fallback `C:\Users\Nikos A. Grammatikos\.local\bin\uv.exe run ...`; ignore VIRTUAL_ENV warning).
- Tests: `uv.exe run manage.py test hub -v 2`; full `uv.exe run manage.py test hub analytics -v 1` stays green (415+). Lint: ruff; frontend `npm run lint && npm run build` + `npm run check:locales` warning-free.
- **`translate_text` MUST be mockable** — no test may make a real network call. Ollama is unreachable from CI/dev; only the VM (with the tunnel) reaches it.
- Translating `quiz_data` preserves structure and every `is_correct` flag and option order — only `question` and option `text` strings change.
- Learner-facing fields NEVER render blank: missing translation → original field.
- Commit after each task; messages end with the project's Co-Authored-By trailer.

---

### Task 1: Ollama tunnel sidecar + translation client

**Files:**
- Create: `docker/ollama-tunnel/Dockerfile`, `docker/ollama-tunnel/entrypoint.sh`, `docker/ollama-tunnel/keys/.gitkeep`
- Modify: `.gitignore` (ignore the private key), `docker-compose.yml`, `.env.example`
- Create: `backend/hub/translation.py`
- Test: `backend/hub/tests/test_translation.py` (new)

**Interfaces:**
- Produces: `translate_text(text, source, target) -> str`; `TranslationError`; `LANGUAGE_NAMES` dict. Tasks 3 consumes them.

- [ ] **Step 1: Failing tests — `backend/hub/tests/test_translation.py`**

```python
from unittest.mock import patch

from django.test import TestCase

from hub.translation import TranslationError, translate_text


class TranslateTextTests(TestCase):
    def test_blank_input_returned_unchanged(self):
        self.assertEqual(translate_text('   ', 'en', 'el'), '   ')
        self.assertEqual(translate_text('', 'en', 'el'), '')

    def test_same_language_is_noop(self):
        self.assertEqual(translate_text('Hello', 'en', 'en'), 'Hello')

    @patch('hub.translation._ollama_generate')
    def test_calls_ollama_and_returns_translation(self, mock_gen):
        mock_gen.return_value = 'Γεια σου'
        out = translate_text('Hello', 'en', 'el')
        self.assertEqual(out, 'Γεια σου')
        prompt = mock_gen.call_args[0][0]
        self.assertIn('English', prompt)
        self.assertIn('Greek', prompt)
        self.assertIn('Hello', prompt)

    @patch('hub.translation._ollama_generate', side_effect=TranslationError('boom'))
    def test_error_propagates(self, _mock):
        with self.assertRaises(TranslationError):
            translate_text('Hello', 'en', 'el')
```

Run: `uv.exe run manage.py test hub.tests.test_translation -v 2` → FAIL (ImportError).

- [ ] **Step 2: `backend/hub/translation.py`**

```python
"""Ollama-backed text translation (Phase 2). Network I/O is isolated in
_ollama_generate so tests can mock it — no test hits Ollama."""
import json
import os
import urllib.error
import urllib.request

LANGUAGE_NAMES = {
    'en': 'English', 'el': 'Greek', 'fr': 'French', 'es': 'Spanish',
    'it': 'Italian', 'fi': 'Finnish', 'sv': 'Swedish', 'no': 'Norwegian',
    'de': 'German',
}

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://ollama-tunnel:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma3-translator')
_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '120'))


class TranslationError(Exception):
    pass


def _ollama_generate(prompt: str) -> str:
    payload = json.dumps({'model': OLLAMA_MODEL, 'prompt': prompt, 'stream': False}).encode()
    req = urllib.request.Request(
        f'{OLLAMA_URL}/api/generate', data=payload,
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise TranslationError(str(exc)) from exc
    text = (data.get('response') or '').strip()
    if not text:
        raise TranslationError('Empty response from Ollama.')
    return text


def translate_text(text: str, source: str, target: str) -> str:
    if not text or not text.strip():
        return text
    if source == target:
        return text
    src = LANGUAGE_NAMES.get(source, source)
    tgt = LANGUAGE_NAMES.get(target, target)
    prompt = (
        f'Translate the following text from {src} to {tgt}. '
        f'Output only the translation, with no notes, quotes, or explanation.\n\n{text}'
    )
    return _ollama_generate(prompt)
```

- [ ] **Step 3: Sidecar image**

`docker/ollama-tunnel/Dockerfile`:

```dockerfile
FROM alpine:3.20
RUN apk add --no-cache autossh openssh-client
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

`docker/ollama-tunnel/entrypoint.sh`:

```sh
#!/bin/sh
set -e
exec autossh -M 0 -N \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile=/dev/null \
  -i /keys/id_ed25519 \
  -L 0.0.0.0:11434:127.0.0.1:11434 \
  "${SSH_REMOTE_USER}@${SSH_REMOTE_HOST}"
```

Create `docker/ollama-tunnel/keys/.gitkeep` (empty). In `.gitignore` add:

```
docker/ollama-tunnel/keys/*
!docker/ollama-tunnel/keys/.gitkeep
```

- [ ] **Step 4: compose + env**

In `docker-compose.yml` add the service:

```yaml
  ollama-tunnel:
    build: ./docker/ollama-tunnel
    environment:
      SSH_REMOTE_USER: ${SSH_REMOTE_USER:-ngrammatikos}
      SSH_REMOTE_HOST: ${SSH_REMOTE_HOST:-147.102.17.66}
    volumes:
      - ./docker/ollama-tunnel/keys:/keys:ro
    restart: unless-stopped
```

Add `OLLAMA_URL: http://ollama-tunnel:11434` and `OLLAMA_MODEL: ${OLLAMA_MODEL:-gemma3-translator}` to the `environment:` of BOTH `backend` and `celery` services, and add `ollama-tunnel` to each of their `depends_on`. Document `OLLAMA_MODEL`, `SSH_REMOTE_USER`, `SSH_REMOTE_HOST` in `.env.example` with a comment that the private key goes in `docker/ollama-tunnel/keys/id_ed25519` and its public half in the NTUA box's authorized_keys.

- [ ] **Step 5: GREEN, full suite, ruff, commit**

```bash
git add backend/hub/translation.py backend/hub/tests/test_translation.py docker/ollama-tunnel .gitignore docker-compose.yml .env.example
git commit -m "feat: Ollama translation client and autossh tunnel sidecar"
```

---

### Task 2: Translation storage fields + migration

**Files:**
- Modify: `backend/hub/models/content.py` (Course/Module/Lesson)
- Create: migration `makemigrations hub -n content_translations`
- Test: `backend/hub/tests/test_content_translation.py` (new)

**Interfaces:**
- Produces: `Course.source_language` (default 'en'), `Course.translations`/`Course.translation_status` (default dict), `Module.translations`, `Lesson.translations` (default dict). Tasks 3-5 consume them.

- [ ] **Step 1: Failing test**

```python
from django.test import TestCase

from hub.models import Course, LearningPillar, Lesson, Module


class TranslationFieldsTests(TestCase):
    def test_defaults(self):
        pillar = LearningPillar.objects.create(name='P', slug='ptr', order=1)
        c = Course.objects.create(title='C', pillar=pillar, level='beginner', duration_hours=1)
        self.assertEqual(c.source_language, 'en')
        self.assertEqual(c.translations, {})
        self.assertEqual(c.translation_status, {})
        m = Module.objects.create(course=c, title='M', order=1)
        self.assertEqual(m.translations, {})
        l = Lesson.objects.create(module=m, title='L', lesson_type='text', order=1)
        self.assertEqual(l.translations, {})

    def test_stores_translation_blob(self):
        pillar = LearningPillar.objects.create(name='P2', slug='ptr2', order=1)
        c = Course.objects.create(title='C', pillar=pillar, level='beginner', duration_hours=1,
                                  translations={'el': {'title': 'Τίτλος'}})
        c.refresh_from_db()
        self.assertEqual(c.translations['el']['title'], 'Τίτλος')
```

Run → FAIL.

- [ ] **Step 2: Add fields** (use `UserProfile.Language.choices` for source_language, or import the 9-code list; `content.py` shouldn't import user.py circularly — define a local `LANGUAGE_CODES` or reuse `hub.translation.LANGUAGE_NAMES.keys()`). On `Course`:

```python
    source_language    = models.CharField(max_length=5, default='en')
    translations       = models.JSONField(default=dict, blank=True)
    translation_status = models.JSONField(default=dict, blank=True)
```

On `Module` and `Lesson`: `translations = models.JSONField(default=dict, blank=True)`. Migrate.

- [ ] **Step 3: GREEN, full suite, ruff, commit** `feat: per-model translation storage fields`.

---

### Task 3: translate_course task + authoring translate endpoint

**Files:**
- Modify: `backend/hub/tasks.py` (translate_course)
- Modify: `backend/hub/views/authoring_course.py` (AuthoringCourseTranslateView) or a new views module; export + route
- Test: `backend/hub/tests/test_content_translation.py` (append)

**Interfaces:**
- Consumes: `translate_text` (Task 1), models (Task 2), `can_edit_published` scoping
- Produces: `translate_course(course_id, target)` task; `POST /api/authoring/courses/<pk>/translate/`

- [ ] **Step 1: Failing tests (append)** — mock `hub.translation.translate_text` to return `f'[{target}] {text}'`, then:

```python
class TranslateCourseTaskTests(TestCase):
    def setUp(self):
        self.pillar = LearningPillar.objects.create(name='P', slug='ptc', order=1)
        self.course = Course.objects.create(title='Hello', description='Desc', pillar=self.pillar,
            level='beginner', duration_hours=1, source_language='en',
            learning_outcomes=['Outcome A'], is_published=True)
        self.module = Module.objects.create(course=self.course, title='Mod', description='md', order=1)
        self.lesson = Lesson.objects.create(module=self.module, title='Les', description='ld',
            content='Body', lesson_type='quiz', order=1,
            quiz_data=[{'question': 'Q?', 'options': [
                {'text': 'A', 'is_correct': True}, {'text': 'B', 'is_correct': False}]}])

    @patch('hub.tasks.translate_text', side_effect=lambda t, s, d: f'[{d}] {t}')
    def test_translate_course_populates_all_levels(self, _m):
        from hub.tasks import translate_course
        translate_course(self.course.id, 'el')
        self.course.refresh_from_db(); self.module.refresh_from_db(); self.lesson.refresh_from_db()
        self.assertEqual(self.course.translations['el']['title'], '[el] Hello')
        self.assertEqual(self.course.translations['el']['learning_outcomes'], ['[el] Outcome A'])
        self.assertEqual(self.course.translation_status['el'], 'done')
        self.assertEqual(self.module.translations['el']['title'], '[el] Mod')
        qd = self.lesson.translations['el']['quiz_data']
        self.assertEqual(qd[0]['question'], '[el] Q?')
        self.assertEqual(qd[0]['options'][0]['text'], '[el] A')
        self.assertTrue(qd[0]['options'][0]['is_correct'])  # flag preserved

    @patch('hub.tasks.translate_text', side_effect=Exception('down'))
    def test_failure_marks_status_failed(self, _m):
        from hub.models import Course as C
        from hub.tasks import translate_course
        # wrap: translate_course should catch TranslationError; use TranslationError
        from hub.translation import TranslationError
        with patch('hub.tasks.translate_text', side_effect=TranslationError('down')):
            translate_course(self.course.id, 'el')
        self.course.refresh_from_db()
        self.assertEqual(self.course.translation_status['el'], 'failed')


class TranslateEndpointTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='tr_cc', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.pillar = LearningPillar.objects.create(name='P', slug='pte', order=1)
        self.course = Course.objects.create(title='C', pillar=self.pillar, level='beginner',
            duration_hours=1, source_language='en', created_by=self.creator)
        self.url = f'/api/authoring/courses/{self.course.id}/translate/'

    @patch('hub.tasks.translate_course.delay')
    def test_enqueues_and_sets_pending(self, mock_delay):
        self.client.force_authenticate(self.creator)
        res = self.client.post(self.url, {'language': 'el'}, format='json')
        self.assertEqual(res.status_code, 202)
        mock_delay.assert_called_once_with(self.course.id, 'el')
        self.course.refresh_from_db()
        self.assertEqual(self.course.translation_status['el'], 'pending')

    def test_rejects_source_language_and_unknown(self):
        self.client.force_authenticate(self.creator)
        self.assertEqual(self.client.post(self.url, {'language': 'en'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, {'language': 'xx'}, format='json').status_code, 400)

    def test_non_author_forbidden(self):
        other = User.objects.create_user(username='tr_other', password='pass12345')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course.is_published = True; self.course.save()
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post(self.url, {'language': 'el'}, format='json').status_code, 403)
```

- [ ] **Step 2: Implement `translate_course` in `backend/hub/tasks.py`**

```python
@shared_task
def translate_course(course_id: int, target: str) -> None:
    from hub.models import Course
    from hub.translation import TranslationError, translate_text

    try:
        course = Course.objects.prefetch_related('modules__lessons').get(pk=course_id)
    except Course.DoesNotExist:
        return
    src = course.source_language

    def tr(text):
        return translate_text(text, src, target)

    def tr_quiz(quiz_data):
        out = []
        for q in quiz_data or []:
            out.append({
                'question': tr(q.get('question', '')),
                'options': [
                    {'text': tr(o.get('text', '')), 'is_correct': bool(o.get('is_correct'))}
                    for o in q.get('options', [])
                ],
            })
        return out

    try:
        course.translations[target] = {
            'title': tr(course.title),
            'description': tr(course.description),
            'learning_outcomes': [tr(o) for o in (course.learning_outcomes or [])],
        }
        for module in course.modules.all():
            module.translations[target] = {'title': tr(module.title), 'description': tr(module.description)}
            module.save(update_fields=['translations'])
            for lesson in module.lessons.all():
                blob = {'title': tr(lesson.title), 'description': tr(lesson.description),
                        'content': tr(lesson.content)}
                if lesson.lesson_type == 'quiz':
                    blob['quiz_data'] = tr_quiz(lesson.quiz_data)
                lesson.translations[target] = blob
                lesson.save(update_fields=['translations'])
        course.translation_status[target] = 'done'
    except TranslationError:
        course.translation_status[target] = 'failed'
    course.save(update_fields=['translations', 'translation_status'])
```

Add `from hub.translation import translate_text` at the point of use (or top; other tasks import locally — follow convention: the tests patch `hub.tasks.translate_text`, so it MUST be importable as a module-level name in tasks.py — add `from hub.translation import translate_text` at module top).

- [ ] **Step 3: Endpoint** — `AuthoringCourseTranslateView` (IsContentCreator; author/admin scoping like the publish views):

```python
class AuthoringCourseTranslateView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if course.is_published and not can_edit_published(request.user, course):
            return Response({'detail': 'Only the author can translate this course.'},
                            status=status.HTTP_403_FORBIDDEN)
        language = request.data.get('language')
        valid = set(LANGUAGE_NAMES) - {course.source_language}
        if language not in valid:
            return Response({'detail': 'Invalid or source language.'}, status=status.HTTP_400_BAD_REQUEST)
        course.translation_status[language] = 'pending'
        course.save(update_fields=['translation_status'])
        from hub.tasks import translate_course
        translate_course.delay(course.id, language)
        return Response({'translation_status': course.translation_status}, status=status.HTTP_202_ACCEPTED)
```

Import `LANGUAGE_NAMES` from `hub.translation`, `can_edit_published` from permissions. Export the view; route `path('authoring/courses/<int:pk>/translate/', AuthoringCourseTranslateView.as_view(), name='authoring-course-translate')`.

- [ ] **Step 4: GREEN, full suite, ruff, commit** `feat: on-demand course translation task and endpoint`.

Note: under eager Celery (dev/test with no Redis) `translate_course.delay` runs inline, so the endpoint test patches `.delay` to assert enqueue without running the (network) task; the task test calls `translate_course(...)` directly with `translate_text` mocked.

---

### Task 4: Learner-side language resolution

**Files:**
- Create: `backend/hub/serializers/localize.py` (helper)
- Modify: `backend/hub/serializers/course.py`, `content.py`, `pathway.py` (learner serializers)
- Test: `backend/hub/tests/test_content_translation.py` (append)

**Interfaces:**
- Produces: `localized(obj, field, lang)` — returns `obj.translations.get(lang, {}).get(field)` if truthy else `getattr(obj, field)`; `viewer_language(context)` — reads `context['request'].user.profile.language`, default 'en'.

- [ ] **Step 1: Failing test (append)** — a course/lesson with `translations={'el': {...}}`, GET as a Greek-profile user returns Greek; as an English user returns original; a lesson missing a field's translation falls back:

```python
class LearnerResolutionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='gr_learner', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER, language='el')
        self.pillar = LearningPillar.objects.create(name='P', slug='plr', order=1)
        self.course = Course.objects.create(title='Original', description='OrigDesc', pillar=self.pillar,
            level='beginner', duration_hours=1, is_published=True,
            translations={'el': {'title': 'Πρωτότυπο'}})
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(self.user)

    def test_detail_uses_greek_title_with_english_fallback_for_description(self):
        res = self.client.get(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.data['title'], 'Πρωτότυπο')        # translated
        self.assertEqual(res.data['description'], 'OrigDesc')    # falls back to original

    def test_english_user_sees_original(self):
        en = User.objects.create_user(username='en_learner', password='pass12345')
        UserProfile.objects.create(user=en, user_type=UserProfile.UserType.TEACHER, language='en')
        self.client.force_authenticate(en)
        res = self.client.get(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.data['title'], 'Original')
```

- [ ] **Step 2: `backend/hub/serializers/localize.py`**

```python
def viewer_language(context):
    request = context.get('request')
    profile = getattr(getattr(request, 'user', None), 'profile', None)
    return getattr(profile, 'language', 'en') or 'en'


def localized(obj, field, lang):
    if lang and lang != 'en':
        value = (obj.translations or {}).get(lang, {}).get(field)
        if value:
            return value
    return getattr(obj, field)
```

- [ ] **Step 3: Apply in learner serializers.** Convert the relevant `title`/`description`/`content`/`learning_outcomes`/`quiz_data` fields to `SerializerMethodField`s that call `localized(obj, '<field>', viewer_language(self.context))`. Cover: `CourseListSerializer`, `CourseDetailSerializer` (title, description, learning_outcomes), `ContinueLearningSerializer` (course_title), `MyLearningEnrollmentSerializer` (course_title), `PathwayCourseSerializer` (title), `RecommendationSerializer` (title), `LessonLearnDetailSerializer` (title, description, content, quiz_data — the learner-facing one that already strips is_correct; resolve to translated quiz_data first, THEN strip is_correct), `ModuleLearnSerializer`/`LessonLearnSerializer` (title). Do NOT change the authoring serializers (creators edit originals + translations explicitly — Task 5). Ensure each serializer's context carries `request` (most already do; verify the pathway/recommendation ones pass it).

- [ ] **Step 4: GREEN, full suite, ruff, commit** `feat: resolve course content to the learner's language with English fallback`.

---

### Task 5: Authoring API — expose + edit translations

**Files:**
- Modify: `backend/hub/serializers/course.py` (`CourseAuthoringSerializer`), `content.py` (authoring module/lesson serializers), authoring views for save-with-lang
- Test: `backend/hub/tests/test_content_translation.py` (append)

**Interfaces:**
- Produces: `source_language`/`translations`/`translation_status` on authoring course payload; module/lesson authoring payloads include `translations`; PATCH endpoints accept `?lang=<code>` to write into `translations[lang]`.

- [ ] **Step 1: Failing tests (append)** — GET authoring course includes `source_language`/`translations`/`translation_status`; PATCH course with `?lang=el` and `{title: 'X'}` writes `translations['el']['title']='X'` WITHOUT changing the base title; PATCH without lang still edits the base title; same for module + lesson. Setting `source_language` via PATCH persists.

- [ ] **Step 2: Serializers** — add `source_language` (writable), `translations` + `translation_status` (read-only) to `CourseAuthoringSerializer.Meta.fields`; add `translations` (read-only) to the authoring `ModuleSerializer`/`LessonSerializer` used by the editor payloads (verify which serializer the module-editor/course-editor endpoints return, and add there).

- [ ] **Step 3: save-with-lang** — in `AuthoringCourseDetailView.patch`, `AuthoringModuleDetailView.patch`, `AuthoringLessonDetailView.patch`: if `request.query_params.get('lang')` is a valid non-source language, merge the incoming translatable fields into `obj.translations[lang]` and `save(update_fields=['translations'])` instead of touching base fields (leave `source_language`, ordering, `is_correct` etc. untouched; only title/description/content/learning_outcomes/quiz_data go into the blob). No lang → existing behavior. Keep the published-course author guard.

- [ ] **Step 4: GREEN, full suite, ruff, commit** `feat: authoring API exposes and edits per-language translations`.

---

### Task 6: Frontend — authoring language switch, translate button, editable translations

**Files:** `frontend/src/pages/CourseEditorPage.jsx` (+ `CourseCreatePage.jsx` for source_language on create), `frontend/src/pages/ModuleEditorPage.jsx`, their CSS; extend locale keys (`authoring.translate.*`) in all 9 files + mirror; parity check.

**Interfaces:** consumes `POST /authoring/courses/<id>/translate/`, `translation_status`, `?lang=` PATCH, `translations` on payloads.

- [ ] **Step 1: Course source language** — CourseCreatePage/CourseEditorPage: a `source_language` dropdown (9 languages) on the course form, saved via the normal course PATCH.
- [ ] **Step 2: Language switch + translate** — In CourseEditorPage and ModuleEditorPage add a language selector: "Editing: <source> (original)" + one entry per other language showing its `translation_status` (—/pending/done/failed). Picking a non-source language:
  - shows a **Translate to <language>** button when no translation exists (or a **Re-translate** button when it does, behind a `window.confirm(t('authoring.translate.reconfirm'))`). Clicking POSTs `/authoring/courses/<id>/translate/ {language}`, then polls `GET /authoring/courses/<id>/` every ~3s until `translation_status[lang]` is `done`/`failed`, updating the UI.
  - makes the editable fields (title/description/content/learning_outcomes; module/lesson fields; quiz builder) bind to `translations[lang]` — edits PATCH with `?lang=<code>`. The source-language view edits base fields as today.
- [ ] **Step 3:** add `authoring.translate.*` keys (button labels, status words, confirm, "machine-translated — review recommended" note) to en.json + mirror into all 8; `npm run check:locales`.
- [ ] **Step 4:** `npm run lint && npm run build`; commit `feat: translate and edit course content per language in the authoring UI`.

---

### Task 7: Final verification

- [ ] `cd backend && uv.exe run coverage run manage.py test hub analytics -v 1` — green, ≥70%; `ruff check .` clean
- [ ] `cd frontend && node scripts/check-locales.mjs && npm run lint && npm run build` — clean
- [ ] Dispatch final whole-branch review (checks: quiz `is_correct`/order preserved through translate + learner resolution; learner never sees blank; no test hits the network; author scoping on translate; source-language ≠ target enforced; docker/compose sanity for the sidecar)

## Deployment notes

Migration + new sidecar + frontend deps → on the VM:
1. Generate a keypair, e.g. `ssh-keygen -t ed25519 -f docker/ollama-tunnel/keys/id_ed25519 -N ''`; append the `.pub` to `ngrammatikos@147.102.17.66`'s `~/.ssh/authorized_keys`.
2. Set `OLLAMA_MODEL` in `.env` to the exact `ollama list` tag; optionally `SSH_REMOTE_USER`/`SSH_REMOTE_HOST`.
3. `git pull && docker compose up -d --build` (builds the sidecar, rebuilds backend/celery/frontend), then `docker compose exec backend uv run python manage.py migrate`.
4. Verify the tunnel: `docker compose exec backend python -c "import urllib.request,os; print(urllib.request.urlopen(os.getenv('OLLAMA_URL','http://ollama-tunnel:11434')+'/api/tags', timeout=10).status)"` → 200.
Existing courses default `source_language='en'` and are untranslated until a creator runs a translation.
