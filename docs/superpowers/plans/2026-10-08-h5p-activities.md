# H5P Activities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Authors upload ready-made `.h5p` files as a new resource type; learners play them inside a sandboxed frame; AIDEA records scores, answers, attempts and completion, and shows them in analytics and Excel.

**Architecture:**
- The backend checks and unpacks uploads (`hub/h5p.py`) into `media/h5p/<id>/`, with one `H5PPackage` per resource × language.
- The frontend ships the open-source **h5p-standalone** player at `/h5p/player.html`. The learner page embeds it in an `<iframe sandbox="allow-scripts …">` (opaque origin, so it cannot read AIDEA's storage). The player posts xAPI statements to the page, a pure mapper (`h5pStatements.js`) turns them into `h5p_answer`/`h5p_attempt` tracking events, and the first finished attempt completes the resource through the existing completion endpoint.
- Analytics and the workbook read those events.

**Tech Stack:** Django 5 + DRF, `zipfile`; React 19 + Vite; `h5p-standalone@^3.8.2` (MIT); Node's built-in test runner; Caddy.

**Spec:** `docs/superpowers/specs/2026-10-08-h5p-activities-design.md`

## Global Constraints

- **Scope:** H5P uploaded as `.h5p` only. No link or embed type, no PhET or other simulations, no H5P editor.
- **Done:** done when H5P reports the learner **finished**, whatever the score. A score below the quiz pass threshold makes the learner *stuck*. Types that never report finishing get **Mark as done** (`Resource.h5p_self_complete`).
- **Retries:** the **first finished attempt** is the score (`ResourceProgress.quiz_score` = raw ÷ max). Later attempts are recorded as events only.
- **Languages:** optional per-language `.h5p` versions. A learner gets their profile language's version, else the main file (`language=''`). Language codes: en, el, fr, es, it, fi, sv, no, de.
- **Limits:** file ≤ **100 MB**; unpacked ≤ **300 MB**; at most 10,000 entries.
- **Allowed extensions** (H5P core's list without swf): `json png jpg jpeg gif bmp tif tiff svg eot ttf woff woff2 otf webm mp4 ogg mp3 m4a wav txt pdf rtf doc docx xls xlsx ppt pptx odt ods odp xml csv diff patch md textile vtt webvtt gltf glb js css`. Entries under `__MACOSX/` and dot-files are ignored.
- **Isolation:** the learner frame uses `sandbox="allow-scripts allow-popups allow-forms"` (never `allow-same-origin`) and `allow="fullscreen"`. `/media/h5p/*` and `/h5p/*` are served with `Access-Control-Allow-Origin: *`, `Content-Security-Policy: sandbox …` and `X-Content-Type-Options: nosniff`.
- **H5P scores never change competency.**
- **Unpacked folders are never deleted.** Re-uploads and copied modules may still point at them.
- Keep all 9 locales in sync; `npm run check:locales` must pass. Icons come from `lucide-react` only. Use per-component CSS.
- **Backend runner:** from `backend/`, `UV="/c/Users/Nikos A. Grammatikos/.local/bin/uv.exe"`; `"$UV" run manage.py …` and `"$UV" run ruff check hub analytics`.
- **Frontend:** the ESLint parser is ES2020 (no numeric separators like `60_000`). The React compiler lint rejects `Date.now()` inside components, so use module-level helpers.
- Keep each file's line endings. Work on `master`; commit and push after each task. Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A malicious `.h5p`** whose JavaScript tries to read AIDEA's sign-in token, or a link that opens `/h5p/player.html` or a package file directly as a top-level page. Both must run sandboxed with an opaque origin. Pinned by Task 4 `test_dev_media_h5p_headers` and Task 7's Caddyfile plus a manual check.
2. **Zip bombs, path traversal and disallowed files** inside an upload must be rejected with nothing written outside the package folder. Pinned by Task 2's extraction tests.
3. **Re-uploading or removing a version after learners attempted it, or copying a module that holds H5P.** Old attempts keep working and copies keep their packages. Pinned by Task 3 `test_replace_keeps_old_folder` and `test_copy_module_copies_packages`.
4. **One finish reported twice** (H5P sending both "answered" and "completed"), or finishing again after completion. Only one attempt is recorded and the first score stays. Pinned by Task 6 `dedupes a finish reported twice` and Task 4 `test_second_completion_keeps_first_score`.
5. **Garbage from the browser** (`h5p_result` with strings or negative numbers, oversized or control-character text in answers) is cleaned and never causes a 500. Pinned by Task 4 `test_clean_result_rejects_garbage` and `test_tracking_cleans_h5p_text`.

---

## File Structure

**Backend**
- `hub/models/h5p.py` (new): `H5PPackage`.
- `hub/models/content.py`: `Resource.Type.H5P` and `Resource.h5p_self_complete`.
- `hub/models/tracking.py`: event types `h5p_answer`, `h5p_attempt`, `h5p_error`.
- `hub/models/__init__.py`: export `H5PPackage`.
- `hub/migrations/0062_h5p.py` (generated).
- `hub/h5p.py` (new): `extract_package`, `default_self_complete`, `clean_result`, `H5PError`.
- `hub/views/authoring_h5p.py` (new): `AuthoringH5PView` upload and delete.
- `hub/views/authoring_module_library.py`: `copy_module` also copies packages.
- `hub/serializers/content.py`: `h5p_packages` and `h5p_self_complete` (authoring); `h5p` and `h5p_self_complete` (learner).
- `hub/completion.py` and `hub/views/learner.py`: `h5p_result` on completion.
- `hub/tracking.py`: text fields for the H5P events.
- `hub/urls.py`: the upload route.
- `aidea/urls.py`: headers for dev media under `h5p/`.
- `backend/Dockerfile`: `gunicorn --timeout 120` (slow 100 MB uploads).
- `analytics/learning.py`: `h5p_attempts`, `h5p_answers`, notes, detail, status, timeline.
- `analytics/workbook.py`: Score %, H5P attempts, H5P answers sheet, Events Data column, README.
- Tests: `hub/tests/test_h5p.py` (new), `analytics/tests/test_h5p_analytics.py` (new), updates to `analytics/tests/test_workbook.py`.

**Frontend**
- `package.json` (dependency and scripts), `scripts/copy-h5p.mjs` (new), `.gitignore`.
- `public/h5p/player.html` and `public/h5p/player.js` (new).
- `src/lib/tracking/h5pStatements.js` and `h5pStatements.test.js` (new).
- `src/lib/mediaUrl.js` (new).
- `src/components/lesson/H5PFrame.jsx` and `H5PFrame.css` (new): sandboxed frame plus messaging, shared by the learner page and the authoring preview.
- `src/components/learner/ResourceView.jsx` and `resourceMeta.js`: H5P body and icon.
- `src/components/authoring/H5PPanel.jsx` and `H5PPanel.css` (new); `ResourceEditor.jsx`; `src/pages/ModuleEditorPage.jsx` and `.css`.
- `src/components/analytics/ContentTree.jsx` and `LearnerTimeline.jsx`: H5P notes and attempts.
- `src/locales/*.json`, `src/pages/PrivacyPage.jsx`.

**Infra and docs:** `Caddyfile`, `CLAUDE.md`.

---

### Task 1: Models and migration

**Files:**
- Create: `backend/hub/models/h5p.py`
- Modify: `backend/hub/models/content.py` (`Resource`), `backend/hub/models/tracking.py` (`LearningEvent.Type`), `backend/hub/models/__init__.py`
- Create: `backend/hub/migrations/0062_h5p.py` (generated)
- Test: `backend/hub/tests/test_h5p.py`

**Interfaces:**
- Produces:
  - `H5PPackage(resource, language, file, folder, title, main_library, size_bytes, version, uploaded_by, uploaded_at)`, with property `media_path` (for example `/media/h5p/ab12…`) and `related_name='h5p_packages'`.
  - `Resource.Type.H5P == 'h5p'` and `Resource.h5p_self_complete`.
  - `LearningEvent.Type.H5P_ANSWER` (`'h5p_answer'`), `H5P_ATTEMPT` (`'h5p_attempt'`) and `H5P_ERROR` (`'h5p_error'`).

- [ ] **Step 1: Write the failing test.** Create `backend/hub/tests/test_h5p.py`:

```python
import io
import json
import tempfile
import zipfile

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from hub.models import (
    Activity,
    Course,
    H5PPackage,
    LearningEvent,
    LearningPillar,
    Module,
    Resource,
)


def make_course(title='H5P course', creator=None):
    pillar = LearningPillar.objects.get_or_create(slug='p-h5p', defaults={'name': 'P', 'order': 1})[0]
    course = Course.objects.create(
        title=title, pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        created_by=creator,
    )
    module = Module.objects.create(course=course, title='M', order=1)
    activity = Activity.objects.create(module=module, title='A', order=1)
    resource = Resource.objects.create(activity=activity, type='h5p', order=1)
    return course, module, activity, resource


def make_h5p(main='H5P.MultiChoice', title='Quiz one', drop=(), extra=None, meta=None):
    """An in-memory .h5p archive: h5p.json, content.json and the library folders."""
    deps = [
        {'machineName': main, 'majorVersion': 1, 'minorVersion': 16},
        {'machineName': 'H5P.Question', 'majorVersion': 1, 'minorVersion': 5},
    ]
    files = {
        'h5p.json': json.dumps(meta if meta is not None else {
            'title': title, 'mainLibrary': main, 'language': 'en',
            'embedTypes': ['iframe'], 'preloadedDependencies': deps,
        }),
        'content/content.json': '{}',
        f'{main}-1.16/library.json': '{}',
        f'{main}-1.16/js/main.js': '',
        'H5P.Question-1.5/library.json': '{}',
    }
    files.update(extra or {})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for name, data in files.items():
            if not any(name.startswith(d) for d in drop):
                zf.writestr(name, data)
    buf.seek(0)
    return buf


class H5PModelTests(TestCase):
    def setUp(self):
        self.course, self.module, self.activity, self.resource = make_course()

    def _package(self, language=''):
        return H5PPackage.objects.create(
            resource=self.resource, language=language, file='h5p_uploads/x.h5p',
            folder='h5p/abc', main_library='H5P.MultiChoice',
        )

    def test_one_package_per_language(self):
        self._package('')
        self._package('el')
        with self.assertRaises(IntegrityError):
            self._package('el')

    def test_media_path(self):
        self.assertEqual(self._package().media_path, '/media/h5p/abc')

    def test_resource_defaults(self):
        self.assertEqual(Resource.Type.H5P, 'h5p')
        self.assertFalse(self.resource.h5p_self_complete)

    def test_event_types(self):
        self.assertEqual(
            (LearningEvent.Type.H5P_ANSWER, LearningEvent.Type.H5P_ATTEMPT, LearningEvent.Type.H5P_ERROR),
            ('h5p_answer', 'h5p_attempt', 'h5p_error'),
        )


TMP_MEDIA = tempfile.mkdtemp(prefix='aidea-h5p-test-')
```

- [ ] **Step 2: Run it to verify it fails.**
  - Run (from `backend/`): `"$UV" run manage.py test hub.tests.test_h5p -v 2`
  - Expected: ImportError, `cannot import name 'H5PPackage'`.

- [ ] **Step 3: Implement.** Create `backend/hub/models/h5p.py`:

```python
"""Uploaded H5P activities — see docs/superpowers/specs/2026-10-08-h5p-activities-design.md.

One H5PPackage per H5P resource × language ('' = the main file). The archive
is unpacked under MEDIA_ROOT/<folder> and played by h5p-standalone in a
sandboxed frame. Re-uploading bumps `version`; old folders are kept because
copied modules and earlier attempts may still point at them."""
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class H5PPackage(models.Model):
    resource     = models.ForeignKey('hub.Resource', on_delete=models.CASCADE, related_name='h5p_packages')
    language     = models.CharField(max_length=8, blank=True)  # '' = main file
    file         = models.FileField(upload_to='h5p_uploads/')
    folder       = models.CharField(max_length=100)             # e.g. 'h5p/3f2a…' under MEDIA_ROOT
    title        = models.CharField(max_length=255, blank=True)
    main_library = models.CharField(max_length=100)
    size_bytes   = models.PositiveBigIntegerField(default=0)
    version      = models.PositiveIntegerField(default=1)
    uploaded_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    uploaded_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('resource', 'language')
        ordering = ['language']

    def __str__(self):
        return f'{self.main_library} for resource {self.resource_id} [{self.language or "main"}]'

    @property
    def media_path(self):
        """Site-relative URL of the unpacked folder."""
        return f'{settings.MEDIA_URL}{self.folder}'
```

In `backend/hub/models/content.py`, in `Resource`:
- Add `H5P = 'h5p', 'H5P activity'` after `ASSIGNMENT` in `Type`.
- Add this after `translations`:

```python
    # h5p: learners mark it done themselves (types that never report finishing).
    h5p_self_complete = models.BooleanField(default=False)
```

In `backend/hub/models/tracking.py`, add to `LearningEvent.Type` after `QUIZ_ANSWER`:

```python
        H5P_ANSWER   = 'h5p_answer',   'H5P answer'
        H5P_ATTEMPT  = 'h5p_attempt',  'H5P attempt finished'
        H5P_ERROR    = 'h5p_error',    'H5P failed to load'
```

In `backend/hub/models/__init__.py`, add `from .h5p import H5PPackage` (between `.feedback` and `.history`) and add `'H5PPackage'` to `__all__`.

Then generate and apply the migration:

```bash
"$UV" run manage.py makemigrations hub --name h5p
"$UV" run manage.py migrate
```

Expected: `hub/migrations/0062_h5p.py` creates `H5PPackage`, adds `resource.h5p_self_complete`, and alters the choices of `resource.type` and `learningevent.event_type`.

- [ ] **Step 4: Run the tests to verify they pass.** Run `"$UV" run manage.py test hub.tests.test_h5p -v 2`. Expected: 4 tests pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/models hub/migrations/0062_h5p.py hub/tests/test_h5p.py
git commit -m "feat: H5PPackage model, h5p resource type and H5P event types"
git push
```

---

### Task 2: Package checks and unpacking (`hub/h5p.py`)

**Files:**
- Create: `backend/hub/h5p.py`
- Test: `backend/hub/tests/test_h5p.py` (append)

**Interfaces:**
- Produces:
  - `MAX_FILE_BYTES`, `MAX_UNPACKED_BYTES`, `MAX_ENTRIES`, `ALLOWED_EXTENSIONS`, `SELF_COMPLETE_LIBRARIES`.
  - `class H5PError(Exception)` with attributes `.code` and `.detail`. Codes: `not_zip`, `too_many_files`, `too_large_unpacked`, `unsafe_path`, `bad_extension`, `no_h5p_json`, `no_content`, `missing_libraries`.
  - `PackageInfo(title, main_library, unpacked_bytes)`.
  - `extract_package(fileobj, dest) -> PackageInfo`. It creates `dest` and leaves nothing behind on failure.
  - `default_self_complete(main_library) -> bool`.
  - `clean_result(raw) -> dict | None`. Used by Task 4.

- [ ] **Step 1: Write the failing tests.** Append to `backend/hub/tests/test_h5p.py`, adding `import os`, `from pathlib import Path` and `from unittest import mock` to the imports:

```python
from hub import h5p  # noqa: E402  (module under test)


class ExtractPackageTests(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='aidea-h5p-x-'))
        self.dest = self.root / 'pkg'

    def assertCode(self, code, archive):
        with self.assertRaises(h5p.H5PError) as ctx:
            h5p.extract_package(archive, self.dest)
        self.assertEqual(ctx.exception.code, code)
        self.assertFalse(self.dest.exists(), 'nothing may be left behind')

    def test_valid_package_is_unpacked(self):
        info = h5p.extract_package(make_h5p(), self.dest)
        self.assertEqual((info.title, info.main_library), ('Quiz one', 'H5P.MultiChoice'))
        self.assertTrue((self.dest / 'h5p.json').is_file())
        self.assertTrue((self.dest / 'H5P.MultiChoice-1.16' / 'js' / 'main.js').is_file())
        self.assertGreater(info.unpacked_bytes, 0)

    def test_mac_metadata_and_dotfiles_are_ignored(self):
        h5p.extract_package(make_h5p(extra={'__MACOSX/._h5p.json': 'x', 'content/.DS_Store': 'x'}), self.dest)
        self.assertFalse((self.dest / '__MACOSX').exists())
        self.assertFalse((self.dest / 'content' / '.DS_Store').exists())

    def test_not_a_zip(self):
        self.assertCode('not_zip', io.BytesIO(b'definitely not a zip'))

    def test_missing_h5p_json(self):
        self.assertCode('no_h5p_json', make_h5p(drop=('h5p.json',)))

    def test_unreadable_h5p_json(self):
        self.assertCode('no_h5p_json', make_h5p(meta='not json'.split()))

    def test_missing_content(self):
        self.assertCode('no_content', make_h5p(drop=('content/',)))

    def test_disallowed_extension(self):
        self.assertCode('bad_extension', make_h5p(extra={'content/page.html': '<script></script>'}))

    def test_path_traversal_is_rejected(self):
        self.assertCode('unsafe_path', make_h5p(extra={'../evil.js': 'x'}))
        self.assertFalse((self.root / 'evil.js').exists())

    def test_missing_libraries(self):
        self.assertCode('missing_libraries', make_h5p(drop=('H5P.Question-1.5/',)))
        self.assertCode('missing_libraries', make_h5p(drop=('H5P.MultiChoice-1.16/',)))

    def test_unpacked_size_limit(self):
        with mock.patch.object(h5p, 'MAX_UNPACKED_BYTES', 10):
            self.assertCode('too_large_unpacked', make_h5p())

    def test_entry_count_limit(self):
        with mock.patch.object(h5p, 'MAX_ENTRIES', 2):
            self.assertCode('too_many_files', make_h5p())

    def test_default_self_complete(self):
        self.assertTrue(h5p.default_self_complete('H5P.Accordion'))
        self.assertFalse(h5p.default_self_complete('H5P.QuestionSet'))
        self.assertFalse(h5p.default_self_complete('H5P.InteractiveVideo'))
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_h5p -v 2`
  - Expected: ImportError, `cannot import name 'h5p' from 'hub'`.

- [ ] **Step 3: Implement.** Create `backend/hub/h5p.py`:

```python
"""Checking and unpacking uploaded .h5p files (zip archives) — see
docs/superpowers/specs/2026-10-08-h5p-activities-design.md.

An upload must be a real H5P package (h5p.json + content/content.json) that
bundles the libraries it needs, hold only file types H5P itself allows, stay
inside its folder, and stay within the size limits. Nothing is left on disk
when a check fails."""
import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_UNPACKED_BYTES = 300 * 1024 * 1024
MAX_ENTRIES = 10000

# H5P core's default whitelist, minus swf.
ALLOWED_EXTENSIONS = frozenset(
    'json png jpg jpeg gif bmp tif tiff svg eot ttf woff woff2 otf webm mp4 ogg mp3 m4a '
    'wav txt pdf rtf doc docx xls xlsx ppt pptx odt ods odp xml csv diff patch md textile '
    'vtt webvtt gltf glb js css'.split()
)

# Content types that never report "finished": learners mark them done themselves.
SELF_COMPLETE_LIBRARIES = frozenset({
    'H5P.Accordion', 'H5P.Agamotto', 'H5P.Chart', 'H5P.Collage', 'H5P.Dialogcards',
    'H5P.IFrameEmbed', 'H5P.ImageHotspots', 'H5P.ImageJuxtaposition', 'H5P.ImageSlider',
    'H5P.Link', 'H5P.Table', 'H5P.Timeline',
})


class H5PError(Exception):
    def __init__(self, code, detail):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass
class PackageInfo:
    title: str
    main_library: str
    unpacked_bytes: int


def default_self_complete(main_library):
    return main_library in SELF_COMPLETE_LIBRARIES


def _ignored(name):
    return name.startswith('__MACOSX/') or PurePosixPath(name).name.startswith('.')


def _check_entries(members):
    if len(members) > MAX_ENTRIES:
        raise H5PError('too_many_files', 'The package contains too many files.')
    total = sum(info.file_size for info in members)
    if total > MAX_UNPACKED_BYTES:
        raise H5PError('too_large_unpacked', 'The package is too large once unpacked.')
    for info in members:
        name = info.filename
        path = PurePosixPath(name)
        if name.startswith('/') or '\\' in name or ':' in name or '..' in path.parts:
            raise H5PError('unsafe_path', f'Unsafe file path in package: {name}')
        if path.suffix.lower().lstrip('.') not in ALLOWED_EXTENSIONS:
            raise H5PError('bad_extension', f'File type not allowed in an H5P package: {path.name}')
    return total


def _read_meta(archive, names):
    if 'h5p.json' not in names:
        raise H5PError('no_h5p_json', 'h5p.json is missing — this is not an H5P package.')
    if 'content/content.json' not in names:
        raise H5PError('no_content', 'content/content.json is missing.')
    try:
        meta = json.loads(archive.read('h5p.json').decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError) as exc:
        raise H5PError('no_h5p_json', 'h5p.json cannot be read.') from exc
    if not isinstance(meta, dict) or not isinstance(meta.get('mainLibrary'), str) or not meta['mainLibrary']:
        raise H5PError('no_h5p_json', 'h5p.json does not name a main library.')
    return meta


def _check_libraries(meta, names):
    deps = [d for d in meta.get('preloadedDependencies') or [] if isinstance(d, dict)]
    folders = [f"{d.get('machineName')}-{d.get('majorVersion')}.{d.get('minorVersion')}/" for d in deps]
    main_present = any(n.startswith(f"{meta['mainLibrary']}-") for n in names)
    if not main_present or any(not any(n.startswith(f) for n in names) for f in folders):
        raise H5PError(
            'missing_libraries',
            "This file doesn't include its H5P libraries — export it again with libraries included.",
        )


def extract_package(fileobj, dest):
    """Check an .h5p archive and unpack it into `dest` (created here)."""
    dest = Path(dest)
    try:
        archive = zipfile.ZipFile(fileobj)
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        raise H5PError('not_zip', 'This is not a valid .h5p file.') from exc
    with archive:
        members = [i for i in archive.infolist() if not i.is_dir() and not _ignored(i.filename)]
        total = _check_entries(members)
        names = {i.filename for i in members}
        meta = _read_meta(archive, names)
        _check_libraries(meta, names)
        try:
            dest.mkdir(parents=True)
            root = dest.resolve()
            for info in members:
                target = (dest / info.filename).resolve()
                if root not in target.parents:
                    raise H5PError('unsafe_path', f'Unsafe file path in package: {info.filename}')
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, open(target, 'wb') as out:
                    shutil.copyfileobj(src, out)
        except zipfile.BadZipFile as exc:
            shutil.rmtree(dest, ignore_errors=True)
            raise H5PError('not_zip', 'This is not a valid .h5p file.') from exc
        except BaseException:
            shutil.rmtree(dest, ignore_errors=True)
            raise
    title = meta.get('title') if isinstance(meta.get('title'), str) else ''
    return PackageInfo(title=title[:255], main_library=meta['mainLibrary'][:100], unpacked_bytes=total)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float('inf'), float('-inf')):
        return None
    return value


def clean_result(raw):
    """The learner's first finished attempt as sent by the page, reduced to
    known fields: raw/max score, success, duration, language and package.
    Returns None when `raw` is not a dict."""
    from hub.translation import LANGUAGE_NAMES
    if not isinstance(raw, dict):
        return None
    out = {}
    score_max, score_raw = _number(raw.get('max')), _number(raw.get('raw'))
    if score_max is not None and score_max > 0 and score_raw is not None:
        out['max'] = score_max
        out['raw'] = min(max(score_raw, 0), score_max)
    if isinstance(raw.get('success'), bool):
        out['success'] = raw['success']
    duration = _number(raw.get('duration_s'))
    if duration is not None and duration >= 0:
        out['duration_s'] = round(min(duration, 86400), 1)
    language = raw.get('language')
    if isinstance(language, str) and (language == '' or language in LANGUAGE_NAMES):
        out['language'] = language
    for key in ('package_id', 'package_version'):
        value = raw.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            out[key] = value
    return out
```

- [ ] **Step 4: Run the tests to verify they pass.** Run `"$UV" run manage.py test hub.tests.test_h5p -v 2`. Expected: all pass (4 model + 12 extraction).

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/h5p.py hub/tests/test_h5p.py
git commit -m "feat: check and unpack uploaded .h5p packages safely"
git push
```

---

### Task 3: Authoring endpoint, serializer, module copy, upload timeout

**Files:**
- Create: `backend/hub/views/authoring_h5p.py`
- Modify:
  - `backend/hub/serializers/content.py` (`ResourceSerializer`)
  - `backend/hub/urls.py`
  - `backend/hub/views/authoring_module_library.py` (`copy_module`)
  - `backend/Dockerfile` (gunicorn CMD)
- Test: `backend/hub/tests/test_h5p.py` (append)

**Interfaces:**
- Consumes: Task 2's `extract_package`, `default_self_complete`, `H5PError` and `MAX_FILE_BYTES`.
- Produces:
  - `POST /api/authoring/courses/<pk>/modules/<module_pk>/lessons/<lesson_pk>/resources/<resource_pk>/h5p/`, multipart with `file` and an optional `language`. Returns 201 with the `ResourceSerializer` data, or 400 `{code, detail}`.
  - `DELETE` on the same URL with `?language=`. Returns 200 with the `ResourceSerializer` data, or 404.
  - Route name `authoring-resource-h5p`.
  - `ResourceSerializer` gains `h5p_self_complete` (writable) and `h5p_packages` (read-only): a list of `{id, language, title, main_library, size_bytes, version, path, uploaded_at}`.

- [ ] **Step 1: Write the failing tests.** Append to `backend/hub/tests/test_h5p.py`, adding `import shutil`, `from django.core.files.uploadedfile import SimpleUploadedFile`, `from django.test import override_settings`, `from django.urls import reverse`, `from rest_framework import status`, `from rest_framework.test import APITestCase` and `UserProfile` (in the `hub.models` import):

```python
def upload_file(archive, name='activity.h5p'):
    return SimpleUploadedFile(name, archive.getvalue(), content_type='application/zip')


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class AuthoringH5PTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.creator = User.objects.create_user('h5p_cc', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.module, self.activity, self.resource = make_course(creator=self.creator)
        self.url = reverse('authoring-resource-h5p', kwargs={
            'pk': self.course.id, 'module_pk': self.module.id,
            'lesson_pk': self.activity.id, 'resource_pk': self.resource.id,
        })
        self.client.force_authenticate(self.creator)

    def post(self, archive, language=''):
        return self.client.post(self.url, {'file': upload_file(archive), 'language': language}, format='multipart')

    def test_upload_main_file(self):
        res = self.post(make_h5p())
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        pkg = H5PPackage.objects.get(resource=self.resource)
        self.assertEqual((pkg.language, pkg.main_library, pkg.version), ('', 'H5P.MultiChoice', 1))
        self.assertTrue((Path(TMP_MEDIA) / pkg.folder / 'h5p.json').is_file())
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.title, 'Quiz one')       # taken from h5p.json
        self.assertFalse(self.resource.h5p_self_complete)
        self.assertEqual(res.data['h5p_packages'][0]['path'], f'/media/{pkg.folder}')

    def test_no_question_type_defaults_to_self_complete(self):
        self.post(make_h5p(main='H5P.Accordion'))
        self.resource.refresh_from_db()
        self.assertTrue(self.resource.h5p_self_complete)

    def test_language_versions(self):
        self.post(make_h5p())
        self.assertEqual(self.post(make_h5p(title='Κουίζ'), language='el').status_code, 201)
        self.assertEqual(sorted(p.language for p in self.resource.h5p_packages.all()), ['', 'el'])
        self.assertEqual(self.post(make_h5p(), language='xx').status_code, 400)

    def test_replace_keeps_old_folder(self):
        self.post(make_h5p())
        old = H5PPackage.objects.get(resource=self.resource)
        self.post(make_h5p(title='Quiz two'))
        new = H5PPackage.objects.get(resource=self.resource)
        self.assertEqual(new.version, 2)
        self.assertNotEqual(new.folder, old.folder)
        self.assertTrue((Path(TMP_MEDIA) / old.folder / 'h5p.json').is_file())

    def test_bad_package_reports_code(self):
        res = self.post(make_h5p(extra={'content/page.html': 'x'}))
        self.assertEqual((res.status_code, res.data['code']), (400, 'bad_extension'))
        self.assertFalse(H5PPackage.objects.exists())

    def test_too_large(self):
        with mock.patch.object(h5p, 'MAX_FILE_BYTES', 10):
            res = self.post(make_h5p())
        self.assertEqual((res.status_code, res.data['code']), (400, 'too_large'))

    def test_only_h5p_resources(self):
        self.resource.type = 'text'
        self.resource.save()
        self.assertEqual(self.post(make_h5p()).status_code, 400)

    def test_permissions(self):
        other = User.objects.create_user('h5p_other', password='pass12345')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(other)
        self.assertEqual(self.post(make_h5p()).status_code, 403)
        teacher = User.objects.create_user('h5p_t', password='pass12345')
        UserProfile.objects.create(user=teacher, user_type=UserProfile.UserType.TEACHER)
        self.client.force_authenticate(teacher)
        self.assertEqual(self.post(make_h5p()).status_code, 403)

    def test_delete_language_version(self):
        self.post(make_h5p())
        self.post(make_h5p(), language='el')
        res = self.client.delete(f'{self.url}?language=el')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([p.language for p in self.resource.h5p_packages.all()], [''])
        self.assertEqual(self.client.delete(f'{self.url}?language=fr').status_code, 404)

    def test_self_complete_is_editable(self):
        detail = reverse('authoring-resource-detail', kwargs={
            'pk': self.course.id, 'module_pk': self.module.id,
            'lesson_pk': self.activity.id, 'resource_pk': self.resource.id,
        })
        self.client.patch(detail, {'h5p_self_complete': True}, format='json')
        self.resource.refresh_from_db()
        self.assertTrue(self.resource.h5p_self_complete)

    def test_copy_module_copies_packages(self):
        from hub.views.authoring_module_library import copy_module
        self.post(make_h5p())
        self.post(make_h5p(), language='el')
        target, *_ = make_course(title='Target', creator=self.creator)
        new_module = copy_module(self.module, target, order=2)
        copied = Resource.objects.get(activity__module=new_module)
        self.assertEqual(sorted(p.language for p in copied.h5p_packages.all()), ['', 'el'])
        self.assertEqual(
            {p.folder for p in copied.h5p_packages.all()},
            {p.folder for p in self.resource.h5p_packages.all()},
        )
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_h5p -v 2`
  - Expected: `NoReverseMatch: 'authoring-resource-h5p'`.

- [ ] **Step 3: Implement.** Create `backend/hub/views/authoring_h5p.py`:

```python
import uuid
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub import h5p
from hub.models import CourseEditHistory, H5PPackage, Resource
from hub.serializers import ResourceSerializer
from hub.translation import LANGUAGE_NAMES
from hub.translation_sync import resync_resource

from .permissions import IsContentCreator, can_edit_course


def _error(code, detail):
    return Response({'code': code, 'detail': detail}, status=status.HTTP_400_BAD_REQUEST)


class AuthoringH5PView(APIView):
    """POST (multipart: file, language) — upload or replace an H5P resource's
    package for one language ('' = main file). DELETE ?language= — remove it.
    Unpacked folders are kept on replace/remove (copies and past attempts)."""

    permission_classes = [IsContentCreator]

    def _resource(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource = (
            Resource.objects.select_related('activity__module__course')
            .filter(
                pk=resource_pk, activity_id=lesson_pk,
                activity__module_id=module_pk, activity__module__course_id=pk,
            )
            .first()
        )
        if resource is None:
            return None, Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_edit_course(request.user, resource.activity.module.course):
            return None, Response({'detail': 'You cannot edit this course.'}, status=status.HTTP_403_FORBIDDEN)
        if resource.type != Resource.Type.H5P:
            return None, _error('not_h5p', 'This resource is not an H5P activity.')
        return resource, None

    def post(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource, failure = self._resource(request, pk, module_pk, lesson_pk, resource_pk)
        if failure:
            return failure
        language = str(request.data.get('language') or '').strip()
        if language and language not in LANGUAGE_NAMES:
            return _error('bad_language', 'Unknown language.')
        upload = request.FILES.get('file')
        if not upload:
            return _error('no_file', 'No file provided.')
        if upload.size > h5p.MAX_FILE_BYTES:
            return _error('too_large', 'The file is larger than 100 MB.')

        folder = f'h5p/{uuid.uuid4().hex}'
        try:
            info = h5p.extract_package(upload, Path(settings.MEDIA_ROOT) / folder)
        except h5p.H5PError as exc:
            return _error(exc.code, exc.detail)
        upload.seek(0)

        first_main = not language and not resource.h5p_packages.filter(language='').exists()
        package = resource.h5p_packages.filter(language=language).first()
        if package is None:
            package = H5PPackage(resource=resource, language=language)
        else:
            package.version += 1
        package.file.save(f'{uuid.uuid4().hex}.h5p', upload, save=False)
        package.folder = folder
        package.title = info.title
        package.main_library = info.main_library
        package.size_bytes = upload.size
        package.uploaded_by = request.user
        package.save()

        if first_main:
            resource.h5p_self_complete = h5p.default_self_complete(info.main_library)
            fields = ['h5p_self_complete']
            if not resource.title and info.title:
                resource.title = info.title[:200]
                fields.append('title')
            resource.save(update_fields=fields)
            if 'title' in fields:
                resync_resource(resource)
        CourseEditHistory.objects.create(
            course=resource.activity.module.course, editor=request.user,
            changes={'h5p_uploaded': {
                'resource': resource.id, 'language': language or 'main',
                'library': info.main_library, 'version': package.version,
            }},
        )
        return Response(ResourceSerializer(resource).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource, failure = self._resource(request, pk, module_pk, lesson_pk, resource_pk)
        if failure:
            return failure
        language = request.query_params.get('language', '')
        deleted, _ = resource.h5p_packages.filter(language=language).delete()
        if not deleted:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ResourceSerializer(resource).data)
```

In `backend/hub/serializers/content.py`, change `ResourceSerializer` to:

```python
class ResourceSerializer(serializers.ModelSerializer):
    """Authoring view of one resource block within an activity."""
    h5p_packages = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = [
            'id', 'type', 'order', 'is_required', 'title', 'content', 'url',
            'caption', 'quiz_data', 'instructions', 'translations',
            'h5p_self_complete', 'h5p_packages',
        ]
        read_only_fields = ['translations']

    def validate_quiz_data(self, value):
        return LessonSerializer().validate_quiz_data(value)

    def get_h5p_packages(self, obj):
        if obj.type != Resource.Type.H5P:
            return []
        return [
            {
                'id': p.id, 'language': p.language, 'title': p.title,
                'main_library': p.main_library, 'size_bytes': p.size_bytes,
                'version': p.version, 'path': p.media_path, 'uploaded_at': p.uploaded_at,
            }
            for p in obj.h5p_packages.all()
        ]
```

In `backend/hub/urls.py`:
- Import `from .views.authoring_h5p import AuthoringH5PView` (ruff sorts it).
- Add this after `authoring-resource-detail`:

```python
    path('authoring/courses/<int:pk>/modules/<int:module_pk>/lessons/<int:lesson_pk>/resources/<int:resource_pk>/h5p/', AuthoringH5PView.as_view(), name='authoring-resource-h5p'),
```

In `backend/hub/views/authoring_module_library.py`, change the inner loop of `copy_module`:

```python
        for resource in activity.resources.order_by('order'):
            new_resource = _clone(resource, activity_id=new_activity.id)
            # Copies share the unpacked folders, which are never deleted.
            for package in resource.h5p_packages.all():
                _clone(package, resource_id=new_resource.id, file=package.file.name)
```

In `backend/Dockerfile`, change the CMD to:

```dockerfile
CMD ["uv", "run", "gunicorn", "aidea.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
```

- [ ] **Step 4: Run the tests to verify they pass.** Run `"$UV" run manage.py test hub.tests.test_h5p hub.tests.test_course_proposal -v 2`. Expected: all pass (the module-copy tests still pass).

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/views/authoring_h5p.py hub/serializers/content.py hub/urls.py hub/views/authoring_module_library.py hub/tests/test_h5p.py Dockerfile
git commit -m "feat: upload, replace and remove H5P packages per language"
git push
```

---

### Task 4: Learner payload, completion with score, H5P events, dev media headers

**Files:**
- Modify:
  - `backend/hub/serializers/content.py` (`ResourceLearnSerializer`)
  - `backend/hub/completion.py`
  - `backend/hub/views/learner.py` (`ResourceCompleteView`)
  - `backend/hub/tracking.py`
  - `backend/aidea/urls.py`
- Test: `backend/hub/tests/test_h5p.py` (append)

**Interfaces:**
- Consumes: from Task 2, `clean_result`.
- Produces:
  - The learner resource payload gains `h5p_self_complete` and `h5p`, which is either None or `{package_id, path, language, version, title, main_library}`, using the viewer's language version, else the main file.
  - `record_resource_completion(..., h5p_result=None)`. For `h5p` resources it sets `quiz_score = raw/max` (or None) and `engagement_data['h5p'] = clean_result(...)`, on first completion only.
  - `POST …/resources/<id>/complete/` accepts `h5p_result`.
  - Tracking stores the `h5p_answer`, `h5p_attempt` and `h5p_error` data keys. Text keys: `question` (500), `response` (500), `sub_content_id` (64), `language` (8), `message` (200). Numeric and boolean keys: `raw`, `max`, `correct`, `success`, `duration_s`, `seconds`, `attempt`, `package_id`, `package_version`.
  - `aidea.urls._serve_media(request, path, document_root)` adds the sandbox headers for `h5p/…` paths.

- [ ] **Step 1: Write the failing tests.** Append to `backend/hub/tests/test_h5p.py`, adding `import uuid`, `from types import SimpleNamespace`, `from django.test import RequestFactory`, `Enrollment` and `ResourceProgress` to the imports:

```python
class LearnerH5PTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user('h5p_cc2', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.module, self.activity, self.resource = make_course(creator=self.creator)
        for language, folder in (('', 'h5p/main'), ('el', 'h5p/greek')):
            H5PPackage.objects.create(
                resource=self.resource, language=language, file='h5p_uploads/x.h5p',
                folder=folder, main_library='H5P.QuestionSet', title='QS',
            )
        self.learner = User.objects.create_user('h5p_learner', password='pass12345')
        self.profile = UserProfile.objects.create(user=self.learner, user_type=UserProfile.UserType.TEACHER)
        Enrollment.objects.create(user=self.learner, course=self.course)
        self.client.force_authenticate(self.learner)
        self.complete_url = reverse('resource-complete', kwargs={
            'pk': self.course.id, 'lesson_pk': self.activity.id, 'resource_pk': self.resource.id,
        })

    def payload(self):
        from hub.serializers import ResourceLearnSerializer
        request = SimpleNamespace(user=self.learner)
        return ResourceLearnSerializer(self.resource, context={'request': request}).data

    def test_learner_gets_their_language_version(self):
        self.profile.language = 'el'
        self.profile.save()
        self.assertEqual(self.payload()['h5p']['path'], '/media/h5p/greek')
        self.profile.language = 'fr'
        self.profile.save()
        data = self.payload()
        self.assertEqual((data['h5p']['path'], data['h5p']['language']), ('/media/h5p/main', ''))
        self.assertFalse(data['h5p_self_complete'])

    def test_no_package_means_no_player(self):
        self.resource.h5p_packages.all().delete()
        self.assertIsNone(self.payload()['h5p'])

    def test_first_finished_attempt_sets_score(self):
        res = self.client.post(self.complete_url, {'h5p_result': {
            'raw': 7, 'max': 10, 'success': True, 'duration_s': 42.25, 'language': '', 'package_id': 1, 'package_version': 2,
        }}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        rp = ResourceProgress.objects.get(user=self.learner, resource=self.resource)
        self.assertAlmostEqual(rp.quiz_score, 0.7)
        self.assertEqual(rp.engagement_data['h5p'], {
            'raw': 7, 'max': 10, 'success': True, 'duration_s': 42.2, 'language': '', 'package_id': 1, 'package_version': 2,
        })

    def test_second_completion_keeps_first_score(self):
        self.client.post(self.complete_url, {'h5p_result': {'raw': 3, 'max': 10}}, format='json')
        self.client.post(self.complete_url, {'h5p_result': {'raw': 10, 'max': 10}}, format='json')
        self.assertAlmostEqual(ResourceProgress.objects.get(user=self.learner).quiz_score, 0.3)

    def test_self_complete_without_result(self):
        res = self.client.post(self.complete_url, {}, format='json')
        self.assertEqual(res.status_code, 200)
        rp = ResourceProgress.objects.get(user=self.learner)
        self.assertIsNone(rp.quiz_score)
        self.assertIsNotNone(rp.completed_at)

    def test_clean_result_rejects_garbage(self):
        self.assertIsNone(h5p.clean_result('nope'))
        self.assertEqual(h5p.clean_result({'raw': '7', 'max': 0, 'success': 'yes', 'duration_s': -3, 'language': 'xx', 'package_id': True}), {})
        self.assertEqual(h5p.clean_result({'raw': 15, 'max': 10}), {'raw': 10, 'max': 10})
        res = self.client.post(self.complete_url, {'h5p_result': ['x']}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(ResourceProgress.objects.get(user=self.learner).quiz_score)

    def test_tracking_cleans_h5p_text(self):
        res = self.client.post(reverse('tracking'), {'page_key': str(uuid.uuid4()), 'visits': [], 'events': [{
            'event_key': str(uuid.uuid4()), 'resource_id': self.resource.id, 'type': 'h5p_answer',
            'data': {'question': 'Q\x01 ' + 'x' * 700, 'response': '1[,]2', 'correct': False,
                     'raw': 0, 'max': 1, 'seconds': 3.5, 'attempt': 1, 'evil': 'no'},
        }]}, format='json')
        self.assertEqual(res.status_code, 200)
        data = LearningEvent.objects.get().data
        self.assertEqual(len(data['question']), 500)
        self.assertTrue(data['question'].startswith('Q x'))
        self.assertEqual(
            {k: data[k] for k in ('response', 'correct', 'raw', 'max', 'seconds', 'attempt')},
            {'response': '1[,]2', 'correct': False, 'raw': 0, 'max': 1, 'seconds': 3.5, 'attempt': 1},
        )
        self.assertNotIn('evil', data)

    def test_dev_media_h5p_headers(self):
        from aidea.urls import _serve_media
        root = Path(tempfile.mkdtemp(prefix='aidea-media-'))
        (root / 'h5p' / 'x').mkdir(parents=True)
        (root / 'h5p' / 'x' / 'h5p.json').write_text('{}')
        (root / 'other.txt').write_text('x')
        request = RequestFactory().get('/media/h5p/x/h5p.json')
        response = _serve_media(request, 'h5p/x/h5p.json', document_root=str(root))
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
        self.assertTrue(response['Content-Security-Policy'].startswith('sandbox'))
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        plain = _serve_media(RequestFactory().get('/media/other.txt'), 'other.txt', document_root=str(root))
        self.assertNotIn('Access-Control-Allow-Origin', plain)
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_h5p.LearnerH5PTests -v 2`
  - Expected: errors and failures. `KeyError: 'h5p'` in the payload tests, a `None` score, `ImportError: _serve_media`, and the text fields missing from the stored event data.

- [ ] **Step 3: Implement.** In `backend/hub/serializers/content.py`, in `ResourceLearnSerializer`:
- Add `h5p = serializers.SerializerMethodField()`.
- Add `'h5p_self_complete', 'h5p'` to `Meta.fields`.
- Add this method:

```python
    def get_h5p(self, obj):
        """The package to play: the viewer's language version, else the main file."""
        if obj.type != Resource.Type.H5P:
            return None
        packages = {p.language: p for p in obj.h5p_packages.all()}
        package = packages.get(viewer_language(self.context)) or packages.get('')
        if package is None:
            return None
        return {
            'package_id': package.id, 'path': package.media_path, 'language': package.language,
            'version': package.version, 'title': package.title, 'main_library': package.main_library,
        }
```

In `backend/hub/completion.py`:
- Give `_mark_resource_complete` and `record_resource_completion` an extra keyword `h5p_result=None`.
- In `_mark_resource_complete`, right after `rp.engagement_data = _engagement(...)`:

```python
        if resource.type == 'h5p':
            from hub.h5p import clean_result
            summary = clean_result(h5p_result)
            if summary is not None:
                rp.engagement_data = {**rp.engagement_data, 'h5p': summary}
                if 'max' in summary:
                    rp.quiz_score = summary['raw'] / summary['max']
```

- In `record_resource_completion`, pass it through: `rp = _mark_resource_complete(user, resource, quiz_answers_raw, engagement_data, h5p_result)`.

In `backend/hub/views/learner.py`, `ResourceCompleteView.post`, add `h5p_result=request.data.get('h5p_result'),` to the `record_resource_completion(...)` call.

In `backend/hub/tracking.py`:
- Replace `EVENT_DATA_KEYS` with:

```python
EVENT_DATA_KEYS = {
    'position', 'from', 'to', 'question_index', 'selected', 'seconds_on_question',
    'raw', 'max', 'correct', 'success', 'duration_s', 'seconds', 'attempt',
    'package_id', 'package_version',
}
# Free-text keys (H5P answers, load errors): control characters removed, length capped.
EVENT_TEXT_LIMITS = {'question': 500, 'response': 500, 'sub_content_id': 64, 'language': 8, 'message': 200}
CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
```

- In `_event_data`, before `return clean`:

```python
    for key, limit in EVENT_TEXT_LIMITS.items():
        if isinstance(data.get(key), str):
            clean[key] = CONTROL_CHARS.sub('', data[key])[:limit]
```

In `backend/aidea/urls.py`:
- Add this function after the imports:

```python
def _serve_media(request, path, document_root=None):
    """Dev media serving. Unpacked H5P packages are fetched from a sandboxed
    (opaque-origin) frame and must never run as AIDEA pages: allow any origin
    to read them, and sandbox them if opened directly. Caddy does the same in
    production (see Caddyfile)."""
    response = serve(request, path, document_root=document_root)
    if path.startswith('h5p/'):
        response['Access-Control-Allow-Origin'] = '*'
        response['Content-Security-Policy'] = 'sandbox allow-scripts'
        response['X-Content-Type-Options'] = 'nosniff'
    return response
```

- Change the DEBUG media route to use `xframe_options_exempt(_serve_media)`.

- [ ] **Step 4: Run the tests to verify they pass.** Run `"$UV" run manage.py test hub.tests.test_h5p hub.tests.test_tracking hub.tests.test_resource_completion -v 2`. Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/serializers/content.py hub/completion.py hub/views/learner.py hub/tracking.py aidea/urls.py hub/tests/test_h5p.py
git commit -m "feat: learners get their H5P version; first finished attempt scores; H5P events"
git push
```

---

### Task 5: Analytics and workbook

**Files:**
- Modify: `backend/analytics/learning.py`, `backend/analytics/workbook.py`
- Create: `backend/analytics/tests/test_h5p_analytics.py`
- Modify: `backend/analytics/tests/test_workbook.py` (sheet list and renamed column)

**Interfaces:**
- Consumes: the Task 1 event types and the Task 4 score in `ResourceProgress.quiz_score`.
- Produces:
  - `CourseData.h5p_attempts(uid, resource) -> [{number, raw, max, success, duration_s, language, finished_at}]`, ordered by time and numbered from 1.
  - `CourseData.h5p_answers(uid, resource) -> [{attempt, question, response, correct, raw, max, seconds, answered_at}]`. Each answer belongs to the first attempt that finished at or after it; answers after the last finish belong to attempt n + 1 (unfinished).
  - `resource_detail` gains `h5p_attempts` (a count for h5p resources, else None), and `quiz_score` now also covers h5p.
  - The timeline resource gains `h5p: {attempts, answers} | None`.
  - Notes for h5p resources: `{finished, avg_score_pct, avg_attempts, hardest_question: {question, pct_correct} | None}`.
  - An h5p score below the pass threshold makes the learner stuck.
  - Workbook:
    - `SHEET_NAMES` gains `'H5P answers'` after `'Quiz answers'`.
    - Resources: `'Quiz score %'` becomes `'Score %'`, plus `'H5P attempts'`.
    - Events gets a `'Data'` column (JSON).

- [ ] **Step 1: Write the failing tests.** Create `backend/analytics/tests/test_h5p_analytics.py`:

```python
from datetime import timedelta

from django.test import TestCase

from analytics.learning import CourseData, content_tree, learner_timeline
from analytics.workbook import build_learning_workbook
from hub.models import Activity, Course, LearningPillar, Module, Resource, UserProfile

from .fixtures import NOW, add_event, complete, enroll, make_user
from .test_workbook import by_learner


def at(minute):
    return NOW - timedelta(minutes=60 - minute)


class H5PAnalyticsTests(TestCase):
    """ann: Q1 ✓, Q2 ✗ → attempt 1 (8/10); Q1 ✓ → attempt 2 (10/10); Q1 ✗ (unfinished)
    bob: Q1 ✗, Q2 ✗ → attempt 1 (4/10) — first score 0.4 → stuck
    cat: enrolled, nothing yet"""

    @classmethod
    def setUpTestData(cls):
        creator = make_user('h5pa_cc', UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-h5pa', order=1)
        cls.course = Course.objects.create(title='H5P', pillar=pillar, level='beginner',
                                           duration_hours=1, is_published=True, created_by=creator)
        module = Module.objects.create(course=cls.course, title='M', order=1)
        activity = Activity.objects.create(module=module, title='Practice', order=1)
        cls.r = Resource.objects.create(activity=activity, type='h5p', order=1, title='Drag task')
        cls.ann, cls.bob, cls.cat = make_user('ann', first='Ann'), make_user('bob', first='Bob'), make_user('cat', first='Cat')
        for u in (cls.ann, cls.bob, cls.cat):
            enroll(u, cls.course)
        r = cls.r
        add_event(cls.ann, r, 'h5p_answer', at=at(1), question='Q1', correct=True, raw=1, max=1, seconds=4)
        add_event(cls.ann, r, 'h5p_answer', at=at(2), question='Q2', correct=False, raw=0, max=1, seconds=6)
        add_event(cls.ann, r, 'h5p_attempt', at=at(3), raw=8, max=10, success=True, duration_s=30, language='')
        add_event(cls.ann, r, 'h5p_answer', at=at(4), question='Q1', correct=True, raw=1, max=1, seconds=2)
        add_event(cls.ann, r, 'h5p_attempt', at=at(5), raw=10, max=10, success=True, duration_s=12, language='')
        add_event(cls.ann, r, 'h5p_answer', at=at(6), question='Q1', correct=False, raw=0, max=1, seconds=1)
        complete(cls.ann, r, at=at(3), quiz_score=0.8, engagement_data={'h5p': {'raw': 8, 'max': 10}})
        add_event(cls.bob, r, 'h5p_answer', at=at(1), question='Q1', correct=False, raw=0, max=1, seconds=9)
        add_event(cls.bob, r, 'h5p_answer', at=at(2), question='Q2', correct=False, raw=0, max=1, seconds=9)
        add_event(cls.bob, r, 'h5p_attempt', at=at(3), raw=4, max=10, success=False, duration_s=40, language='el')
        complete(cls.bob, r, at=at(3), quiz_score=0.4, engagement_data={'h5p': {'raw': 4, 'max': 10}})

    def setUp(self):
        self.cd = CourseData(self.course, now=NOW)

    def test_attempts_numbered_by_time(self):
        attempts = self.cd.h5p_attempts(self.ann.id, self.r)
        self.assertEqual([(a['number'], a['raw']) for a in attempts], [(1, 8), (2, 10)])

    def test_answers_belong_to_their_attempt(self):
        answers = self.cd.h5p_answers(self.ann.id, self.r)
        self.assertEqual([(a['attempt'], a['question'], a['correct']) for a in answers],
                         [(1, 'Q1', True), (1, 'Q2', False), (2, 'Q1', True), (3, 'Q1', False)])

    def test_notes(self):
        notes = content_tree(self.cd)['modules'][0]['activities'][0]['resources'][0]['notes']
        self.assertEqual(notes, {
            'finished': 2, 'avg_score_pct': 60, 'avg_attempts': 1.5,
            'hardest_question': {'question': 'Q2', 'pct_correct': 0},
        })

    def test_low_first_score_is_stuck(self):
        status = {e.user.username: self.cd.status(e) for e in self.cd.enrollments}
        self.assertEqual(status, {'ann': 'on_track', 'bob': 'stuck', 'cat': 'on_track'})

    def test_detail_and_timeline(self):
        detail = self.cd.resource_detail(self.ann.id, self.r)
        self.assertEqual((detail['quiz_score'], detail['h5p_attempts']), (0.8, 2))
        res = learner_timeline(self.cd, self.ann.id)['modules'][0]['activities'][0]['resources'][0]
        self.assertEqual((len(res['h5p']['attempts']), len(res['h5p']['answers'])), (2, 4))
        cat = learner_timeline(self.cd, self.cat.id)['modules'][0]['activities'][0]['resources'][0]
        self.assertEqual(cat['h5p'], {'attempts': [], 'answers': []})

    def test_workbook(self):
        wb = build_learning_workbook([self.course], now=NOW)
        [row] = by_learner(wb['Resources'], 'Ann')
        self.assertEqual((row['Score %'], row['H5P attempts']), (80, 2))
        answers = by_learner(wb['H5P answers'], 'Ann')
        self.assertEqual([(a['Attempt #'], a['Question'], a['Right']) for a in answers],
                         [(1, 'Q1', 'yes'), (1, 'Q2', 'no'), (2, 'Q1', 'yes'), (3, 'Q1', 'no')])
        first = by_learner(wb['Events'], 'Bob')[0]
        self.assertIn('"question": "Q1"', first['Data'])
```

In `backend/analytics/tests/test_workbook.py`:
- In `test_sheet_order`, change the expected list to `['README', 'Overview', 'Learners', 'Modules', 'Activities', 'Resources', 'Visits', 'Quiz answers', 'H5P answers', 'Events']`.
- No test reads `'Quiz score %'`, so no other edit is needed.

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test analytics -v 2`
  - Expected: `AttributeError: 'CourseData' object has no attribute 'h5p_attempts'`, and the sheet-order test fails.

- [ ] **Step 3: Implement.** In `backend/analytics/learning.py`, add these methods to `CourseData` after `quiz_answers`:

```python
    def h5p_attempts(self, uid, resource):
        """Finished H5P attempts in time order, numbered from 1."""
        events = self.events_for(uid, resource.id, LearningEvent.Type.H5P_ATTEMPT)
        return [{
            'number': i, 'raw': e.data.get('raw'), 'max': e.data.get('max'),
            'success': e.data.get('success'), 'duration_s': e.data.get('duration_s'),
            'language': e.data.get('language', ''), 'finished_at': e.occurred_at,
        } for i, e in enumerate(events, start=1)]

    def h5p_answers(self, uid, resource):
        """H5P answers, each in the first attempt finishing at or after it;
        answers after the last finish form an unfinished attempt (n + 1)."""
        ends = [e.occurred_at for e in self.events_for(uid, resource.id, LearningEvent.Type.H5P_ATTEMPT)]
        rows = []
        for e in self.events_for(uid, resource.id, LearningEvent.Type.H5P_ANSWER):
            number = next((i for i, end in enumerate(ends, start=1) if e.occurred_at <= end), len(ends) + 1)
            rows.append({
                'attempt': number, 'question': e.data.get('question', ''),
                'response': e.data.get('response', ''), 'correct': e.data.get('correct'),
                'raw': e.data.get('raw'), 'max': e.data.get('max'),
                'seconds': e.data.get('seconds'), 'answered_at': e.occurred_at,
            })
        return rows
```

In `resource_detail`:
- Change `'quiz_score': progress.quiz_score if progress and kind == 'quiz' else None,` to `'quiz_score': progress.quiz_score if progress and kind in ('quiz', 'h5p') else None,`.
- Add `'h5p_attempts': count('h5p_attempt') if kind == 'h5p' else None,`.

In `_stuck`, change `resource.type == 'quiz'` to `resource.type in ('quiz', 'h5p')`.

In `resource_notes`, add before the `if kind in ('pdf', 'image'):` branch:

```python
    if kind == 'h5p':
        scores, attempts, right_by_question = [], [], defaultdict(list)
        finished = 0
        for uid in uids:
            progress = cd.progress_for(uid, resource.id)
            if progress and progress.completed_at:
                finished += 1
            if progress and progress.quiz_score is not None:
                scores.append(progress.quiz_score)
            count = len(cd.h5p_attempts(uid, resource))
            if count:
                attempts.append(count)
            for answer in cd.h5p_answers(uid, resource):
                if isinstance(answer['correct'], bool) and answer['question']:
                    right_by_question[answer['question']].append(answer['correct'])
        hardest = min(right_by_question.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), default=None)
        return {
            'finished': finished,
            'avg_score_pct': _avg([s * 100 for s in scores]),
            'avg_attempts': _avg(attempts, 1),
            'hardest_question': {
                'question': hardest[0], 'pct_correct': round(100 * sum(hardest[1]) / len(hardest[1])),
            } if hardest else None,
        }
```

In `learner_timeline`, add this to each resource dict after `'quiz_answers': …`:

```python
                'h5p': {
                    'attempts': cd.h5p_attempts(user_id, r), 'answers': cd.h5p_answers(user_id, r),
                } if r.type == 'h5p' else None,
```

In `backend/analytics/workbook.py`:
- Add `import json` at the top.
- In `SHEET_NAMES`, insert `'H5P answers'` after `'Quiz answers'`.
- In `HEADERS['Resources']`, replace `'Quiz score %'` with `'Score %', 'H5P attempts'`.
- In `_resources`, after the score cell, add `blank(d['h5p_attempts']),`.
- Add `HEADERS['H5P answers'] = BASE + ['Module ID', 'Activity ID', 'Activity', 'Resource ID', 'Resource', 'Attempt #', 'Question', 'Response', 'Right', 'Points', 'Max points', 'Seconds', 'Answered at']`.
- Append `'Data'` to `HEADERS['Events']`.
- Add this generator:

```python
def _h5p_answers(cd):
    for e in cd.enrollments:
        for r in cd.resources:
            if r.type != 'h5p':
                continue
            for answer in cd.h5p_answers(e.user_id, r):
                right = answer['correct']
                yield _base(cd, e.user) + [
                    r.activity.module_id, r.activity_id, r.activity.title, r.id, resource_label(r),
                    answer['attempt'], answer['question'], answer['response'],
                    '' if right is None else yes_no(right), blank(answer['raw']), blank(answer['max']),
                    blank(answer['seconds']), iso(answer['answered_at']),
                ]
```

- Register it in `ROWS` after `'Quiz answers'`: `'H5P answers': _h5p_answers,`.
- In `_events`, append `json.dumps(data, ensure_ascii=False, sort_keys=True)` as the last cell.
- Add these README lines before the `'Sheets: …'` line:

```python
    'H5P activities: Score % is the first finished attempt (raw ÷ max). Later attempts are practice; '
    'every attempt and answer is in H5P answers and Events (types h5p_attempt, h5p_answer). '
    'Attempt # = the attempt an answer belongs to; the last number with no finished attempt is unfinished.',
```

- Update the `'Sheets: …'` line so it lists `H5P answers` after `Quiz answers`.

- [ ] **Step 4: Run the tests to verify they pass.** Run `"$UV" run manage.py test analytics -v 2`. Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add analytics
git commit -m "feat: H5P attempts, answers and scores in analytics and Excel"
git push
```

---

### Task 6: Player page and xAPI mapping (frontend core)

**Files:**
- Modify: `frontend/package.json`, `frontend/.gitignore`
- Create: `frontend/scripts/copy-h5p.mjs`, `frontend/public/h5p/player.html`, `frontend/public/h5p/player.js`
- Create: `frontend/src/lib/tracking/h5pStatements.js`, `h5pStatements.test.js`
- Create: `frontend/src/lib/mediaUrl.js`

**Interfaces:**
- Produces:
  - The player URL is `/h5p/player.html?src=<absolute package URL>&channel=<id>&origin=<page origin>`.
  - It posts `{source: 'aidea-h5p', channel, kind: 'ready'|'height'|'xapi'|'error', height?, statement?, message?}` to the parent.
  - `createH5PSession({language, packageId, packageVersion})` returns `.handle(statement, nowMs)`, which returns `{events: [{type: 'h5p_answer'|'h5p_attempt', data}], finished: data | null}`.
  - `langText(map)` and `durationSeconds(iso)`.
  - `mediaUrl(path)` returns an absolute URL on the API host.

- [ ] **Step 1: Write the failing tests.** Create `frontend/src/lib/tracking/h5pStatements.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createH5PSession, durationSeconds, langText } from './h5pStatements.js'

const ROOT = 'https://aidea-hub.eu/h5p'
const stmt = (verb, { sub = null, result = null, description = null } = {}) => ({
  verb: { id: `http://adlnet.gov/expapi/verbs/${verb}` },
  object: {
    id: sub ? `${ROOT}?subContentId=${sub}` : ROOT,
    definition: description ? { description: { 'en-US': description } } : {},
  },
  ...(result && { result }),
})
const session = () => createH5PSession({ language: 'el', packageId: 4, packageVersion: 2 })

test('a question answered inside the activity is an answer, not a finish', () => {
  const { events, finished } = session().handle(stmt('answered', {
    sub: 'abc', description: '<p>Capital of <b>France</b>?</p>',
    result: { response: '2', success: true, score: { raw: 1, max: 1 }, duration: 'PT4.5S' },
  }), 0)
  assert.equal(finished, null)
  assert.deepEqual(events, [{ type: 'h5p_answer', data: {
    question: 'Capital of France ?', response: '2', correct: true, raw: 1, max: 1, seconds: 4.5, attempt: 1, sub_content_id: 'abc',
  } }])
})

test('the whole activity completed is a finished attempt; the next attempt is numbered 2', () => {
  const s = session()
  const first = s.handle(stmt('completed', { result: { score: { raw: 7, max: 10 }, success: true, duration: 'PT1M2S', completion: true } }), 0)
  assert.deepEqual(first.finished, { raw: 7, max: 10, success: true, duration_s: 62, attempt: 1, language: 'el', package_id: 4, package_version: 2 })
  assert.deepEqual(first.events.map(e => e.type), ['h5p_attempt'])
  const answer = s.handle(stmt('answered', { sub: 'q1', result: { response: '0' } }), 10000)
  assert.equal(answer.events[0].data.attempt, 2)
})

test('a single question at top level is both an answer and a finished attempt', () => {
  const { events, finished } = session().handle(stmt('answered', { description: 'Q', result: { score: { raw: 0, max: 1 }, success: false } }), 0)
  assert.deepEqual(events.map(e => e.type), ['h5p_answer', 'h5p_attempt'])
  assert.equal(finished.raw, 0)
})

test('dedupes a finish reported twice', () => {
  const s = session()
  s.handle(stmt('answered', { result: { score: { raw: 1, max: 2 } } }), 1000)
  const again = s.handle(stmt('completed', { result: { score: { raw: 1, max: 2 } } }), 1800)
  assert.equal(again.finished, null)
  assert.deepEqual(again.events, [])
})

test('other verbs and malformed statements are ignored', () => {
  const s = session()
  assert.deepEqual(s.handle(stmt('interacted', { sub: 'x' }), 0), { events: [], finished: null })
  assert.deepEqual(s.handle(null, 0), { events: [], finished: null })
  assert.deepEqual(s.handle({ verb: 'odd' }, 0), { events: [], finished: null })
  assert.deepEqual(s.handle(stmt('completed', { result: { completion: false } }), 0), { events: [], finished: null })
})

test('durationSeconds and langText', () => {
  assert.equal(durationSeconds('PT1H2M3.25S'), 3723.3)
  assert.equal(durationSeconds('nope'), null)
  assert.equal(langText({ 'de-DE': 'Hallo' }), 'Hallo')
  assert.equal(langText(null), '')
  assert.equal(langText({ 'en-US': 'x'.repeat(900) }).length, 500)
})
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run (from `frontend/`): `npm test`
  - Expected: `ERR_MODULE_NOT_FOUND …/h5pStatements.js`.

- [ ] **Step 3: Implement.** Create `frontend/src/lib/tracking/h5pStatements.js`:

```js
// Turns H5P xAPI statements into AIDEA learning events (see
// docs/superpowers/specs/2026-10-08-h5p-activities-design.md). Kept: answers
// (one per question answered) and finished attempts (the whole activity, top
// level). Everything else ("interacted", "progressed", …) is ignored.

const MAX_TEXT = 500
const DEDUPE_MS = 1500 // H5P can report one finish as both "answered" and "completed"

const verbOf = (s) => String(s?.verb?.id ?? '').split('/').pop()
const subContentId = (s) => /[?&]subContentId=([^&#]+)/.exec(String(s?.object?.id ?? ''))?.[1] ?? null

export function langText(map) {
  if (!map || typeof map !== 'object') return ''
  const value = map['en-US'] ?? Object.values(map)[0] ?? ''
  return String(value).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, MAX_TEXT)
}

export function durationSeconds(iso) {
  const m = /^PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?$/.exec(String(iso ?? ''))
  if (!m) return null
  const seconds = Number(m[1] || 0) * 3600 + Number(m[2] || 0) * 60 + Number(m[3] || 0)
  return Math.round(seconds * 10) / 10
}

const score = (result) => {
  const raw = result?.score?.raw
  const max = result?.score?.max
  return Number.isFinite(raw) && Number.isFinite(max) ? { raw, max } : {}
}

// One session per H5P resource on the page.
export function createH5PSession({ language, packageId, packageVersion }) {
  let attempt = 1
  let lastFinishAt = -Infinity
  return {
    handle(statement, now) {
      const events = []
      let finished = null
      if (!statement || typeof statement !== 'object') return { events, finished }
      const verb = verbOf(statement)
      const result = statement.result && typeof statement.result === 'object' ? statement.result : null
      const sub = subContentId(statement)
      const seconds = durationSeconds(result?.duration)

      if (verb === 'answered' && result) {
        const definition = statement.object?.definition
        events.push({ type: 'h5p_answer', data: {
          question: langText(definition?.description) || langText(definition?.name),
          response: typeof result.response === 'string' ? result.response.slice(0, MAX_TEXT) : '',
          ...(typeof result.success === 'boolean' && { correct: result.success }),
          ...score(result),
          ...(seconds != null && { seconds }),
          attempt,
          ...(sub && { sub_content_id: sub.slice(0, 64) }),
        } })
      }

      const isFinish = !sub && (verb === 'completed' || verb === 'answered')
        && result && result.completion !== false
      if (isFinish && now - lastFinishAt > DEDUPE_MS) {
        lastFinishAt = now
        finished = {
          ...score(result),
          ...(typeof result.success === 'boolean' && { success: result.success }),
          ...(seconds != null && { duration_s: seconds }),
          attempt, language, package_id: packageId, package_version: packageVersion,
        }
        events.push({ type: 'h5p_attempt', data: finished })
        attempt += 1
      } else if (isFinish) {
        // Second report of the same finish: drop the duplicate answer too.
        return { events: [], finished: null }
      }
      return { events, finished }
    },
  }
}
```

Note the duplicate-finish branch: when a finish arrives within 1.5 s of the previous one, it is a re-report, so neither its answer nor its attempt is recorded. That is what `dedupes a finish reported twice` asserts.

Create `frontend/src/lib/mediaUrl.js`:

```js
import client from '../api/client'

// A site-relative media path ("/media/…") as an absolute URL on the API's host
// (the dev server serves media from the backend, not from Vite).
export const mediaUrl = (path) => new URL(path, client.defaults.baseURL).href
```

Install the player:

```bash
npm install h5p-standalone@^3.8.2
```

Create `frontend/scripts/copy-h5p.mjs`:

```js
// Copy the h5p-standalone player into public/h5p/vendor so /h5p/player.html can
// load it (dev) and it is bundled into dist (build). Runs via predev/prebuild.
import { cpSync, existsSync, rmSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const src = join(here, '..', 'node_modules', 'h5p-standalone', 'dist')
const dest = join(here, '..', 'public', 'h5p', 'vendor')

if (!existsSync(src)) {
  console.error('[copy-h5p] node_modules/h5p-standalone not found — run npm install first.')
  process.exit(1)
}

rmSync(dest, { recursive: true, force: true })
cpSync(src, dest, { recursive: true })
console.log('[copy-h5p] copied h5p-standalone to public/h5p/vendor')
```

In `frontend/package.json` `scripts`:

```json
    "copy-h5p": "node scripts/copy-h5p.mjs",
    "predev": "node scripts/copy-tinymce.mjs && node scripts/copy-h5p.mjs",
    "prebuild": "node scripts/copy-tinymce.mjs && node scripts/copy-h5p.mjs",
```

Append to `frontend/.gitignore`:

```gitignore

# h5p-standalone player (copied from node_modules by scripts/copy-h5p.mjs)
public/h5p/vendor/
```

Create `frontend/public/h5p/player.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>H5P</title>
    <style>
      html, body { margin: 0; padding: 0; background: transparent; }
      #h5p { max-width: 100%; }
    </style>
  </head>
  <body>
    <div id="h5p"></div>
    <script src="player.js"></script>
    <script src="vendor/main.bundle.js"></script>
  </body>
</html>
```

Create `frontend/public/h5p/player.js`:

```js
// AIDEA H5P player. Runs ONLY inside the learner page's sandboxed iframe
// (opaque origin: no access to AIDEA's storage or sign-in token). Plays one
// unpacked .h5p with h5p-standalone and posts xAPI statements and its height
// to the parent. See docs/superpowers/specs/2026-10-08-h5p-activities-design.md.
(function () {
  var params = new URLSearchParams(window.location.search)
  var src = params.get('src')
  var channel = params.get('channel')
  var parentOrigin = params.get('origin') || '*'

  function post(kind, extra) {
    var message = { source: 'aidea-h5p', channel: channel, kind: kind }
    for (var key in extra || {}) message[key] = extra[key]
    window.parent.postMessage(message, parentOrigin)
  }

  // Never run as a top-level page, and only play AIDEA's unpacked packages.
  var framed = window.top !== window.self
  var validSrc = false
  try { validSrc = new URL(src).pathname.indexOf('/media/h5p/') === 0 } catch (e) { validSrc = false }

  // Storage throws in an opaque origin; H5P only uses it for an anonymous id
  // and copy/paste, so an in-memory stand-in is enough.
  try { window.localStorage.getItem('probe') } catch (e) {
    var memory = {}
    var shim = {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(memory, k) ? memory[k] : null },
      setItem: function (k, v) { memory[k] = String(v) },
      removeItem: function (k) { delete memory[k] },
      clear: function () { memory = {} },
    }
    try { Object.defineProperty(window, 'localStorage', { value: shim, configurable: true }) } catch (e2) { /* keep going */ }
  }

  function reportHeight() {
    post('height', { height: document.documentElement.scrollHeight })
  }

  window.addEventListener('load', function () {
    if (!framed || !validSrc || !window.H5PStandalone) {
      post('error', { message: !framed ? 'not framed' : !validSrc ? 'invalid package' : 'player missing' })
      return
    }
    var vendor = new URL('vendor/', window.location.href).href
    new window.H5PStandalone.H5P(document.getElementById('h5p'), {
      h5pJsonPath: src,
      frameJs: vendor + 'frame.bundle.js',
      frameCss: vendor + 'styles/h5p.css',
      fullScreen: true,
      // A fixed actor keeps H5P away from storage for an anonymous id; AIDEA
      // knows the learner from the page, not from the statement.
      user: { name: 'AIDEA learner', mail: 'learner@aidea-hub.eu' },
    }).then(function () {
      window.H5P.externalDispatcher.on('xAPI', function (event) {
        try {
          post('xapi', { statement: JSON.parse(JSON.stringify(event.data.statement)) })
        } catch (e) { /* not serialisable: skip */ }
      })
      post('ready')
      reportHeight()
      if (window.ResizeObserver) new window.ResizeObserver(reportHeight).observe(document.body)
      else window.setInterval(reportHeight, 1000)
    }).catch(function (err) {
      post('error', { message: String((err && err.message) || err).slice(0, 200) })
    })
  })
})()
```

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `npm test && npm run lint && node scripts/copy-h5p.mjs && ls public/h5p/vendor`
  - Expected: all tests pass (the earlier 25 plus 6 new); lint is clean; `vendor` contains `main.bundle.js`, `frame.bundle.js` and `styles/`.

- [ ] **Step 5: Commit.**

```bash
git add package.json package-lock.json .gitignore scripts/copy-h5p.mjs public/h5p/player.html public/h5p/player.js src/lib/tracking/h5pStatements.js src/lib/tracking/h5pStatements.test.js src/lib/mediaUrl.js
git commit -m "feat: sandbox-only H5P player page and xAPI → event mapping"
git push
```

---

### Task 7: Learner H5P resource, sandboxed frame, Caddy headers

**Files:**
- Create: `frontend/src/components/lesson/H5PFrame.jsx`, `H5PFrame.css`
- Modify:
  - `frontend/src/components/learner/ResourceView.jsx`
  - `frontend/src/components/learner/resourceMeta.js`
  - `frontend/src/locales/*.json` (`lesson.type.h5p`, `lesson.h5p.*`)
  - `Caddyfile`

**Interfaces:**
- Consumes:
  - From Task 6: `createH5PSession` and `mediaUrl`.
  - From Task 4: `resource.h5p` and `resource.h5p_self_complete`.
  - From the analytics work: `useResourceTracking(resourceId)` (`event(type, data)`).
  - The completion endpoint's `h5p_result`.
- Produces: `<H5PFrame pkg title onStatement? onError?/>`. Task 8 uses it for the authoring preview.

- [ ] **Step 1: Shared frame component.** Create `frontend/src/components/lesson/H5PFrame.jsx`:

```jsx
import { useEffect, useMemo, useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { mediaUrl } from '../../lib/mediaUrl'
import './H5PFrame.css'

const LOAD_TIMEOUT_MS = 30000
// Clock reads live outside components (React compiler purity rule).
const nowMs = () => Date.now()

/** One H5P package in a sandboxed (opaque-origin) frame. The frame can run
 *  the activity's scripts but cannot read AIDEA's pages, cookies or tokens.
 *  Messages are accepted only from this frame's window and channel. */
export default function H5PFrame({ pkg, title, onStatement, onError }) {
  const { t } = useTranslation()
  const frameRef = useRef(null)
  const [height, setHeight] = useState(480)
  const [failed, setFailed] = useState(false)
  const channel = `h5p-${pkg.package_id}-${pkg.version}`
  const src = useMemo(() => {
    const params = new URLSearchParams({ src: mediaUrl(pkg.path), channel, origin: window.location.origin })
    return `/h5p/player.html?${params}`
  }, [pkg.path, channel])

  const handlersRef = useRef({ onStatement, onError })
  useEffect(() => { handlersRef.current = { onStatement, onError } })

  useEffect(() => {
    let ready = false
    const fail = (message) => {
      setFailed(true)
      handlersRef.current.onError?.(message)
    }
    const timer = setTimeout(() => { if (!ready) fail('timeout') }, LOAD_TIMEOUT_MS)
    const onMessage = (e) => {
      const msg = e.data
      if (e.source !== frameRef.current?.contentWindow || msg?.source !== 'aidea-h5p' || msg.channel !== channel) return
      if (msg.kind === 'ready') ready = true
      else if (msg.kind === 'height' && Number.isFinite(msg.height)) setHeight(Math.min(Math.max(msg.height, 200), 4000))
      else if (msg.kind === 'error') fail(String(msg.message || 'error'))
      else if (msg.kind === 'xapi') handlersRef.current.onStatement?.(msg.statement, nowMs())
    }
    window.addEventListener('message', onMessage)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('message', onMessage)
    }
  }, [channel])

  if (failed) return <p className="lp-empty">{t('lesson.h5p.loadError')}</p>
  return (
    <iframe
      ref={frameRef}
      className="h5p-frame"
      title={title}
      src={src}
      sandbox="allow-scripts allow-popups allow-forms"
      allow="fullscreen"
      style={{ height }}
    />
  )
}

H5PFrame.propTypes = {
  pkg: PropTypes.shape({
    package_id: PropTypes.number.isRequired,
    version: PropTypes.number.isRequired,
    path: PropTypes.string.isRequired,
  }).isRequired,
  title: PropTypes.string.isRequired,
  onStatement: PropTypes.func,
  onError: PropTypes.func,
}
```

Create `frontend/src/components/lesson/H5PFrame.css`:

```css
.h5p-frame {
  display: block;
  width: 100%;
  min-height: 200px;
  border: 0;
  background: transparent;
}
```

- [ ] **Step 2: Learner body and done rule.** In `frontend/src/components/learner/ResourceView.jsx`:
- Import `H5PFrame from '../lesson/H5PFrame'` and `{ createH5PSession } from '../../lib/tracking/h5pStatements'`.
- Add this component before `ResourceView`:

```jsx
// ─── H5P ─────────────────────────────────────────────────────────────────────

H5PBody.propTypes = { resource: resourceShape.isRequired, onComplete: PropTypes.func.isRequired }
function H5PBody({ resource, onComplete }) {
  const { t } = useTranslation()
  const track = useResourceTracking(resource.id)
  const pkg = resource.h5p
  const session = useMemo(
    () => (pkg ? createH5PSession({ language: pkg.language, packageId: pkg.package_id, packageVersion: pkg.version }) : null),
    [pkg],
  )
  // The first finished attempt completes the resource (its score counts).
  const doneRef = useRef(resource.is_completed)
  useEffect(() => { doneRef.current = resource.is_completed }, [resource.is_completed])

  if (!pkg) return <p className="lp-empty">{t('lesson.h5p.missing')}</p>

  const onStatement = (statement, now) => {
    const { events, finished } = session.handle(statement, now)
    events.forEach(e => track.event(e.type, e.data))
    if (finished && !doneRef.current) {
      doneRef.current = true
      onComplete({ h5p_result: finished })
    }
  }
  return (
    <H5PFrame
      key={`${pkg.package_id}-${pkg.version}`}
      pkg={pkg}
      title={resource.title || t('lesson.type.h5p')}
      onStatement={onStatement}
      onError={(message) => track.event('h5p_error', { message })}
    />
  )
}
```

- Change `selfCompletes`:

```jsx
  const selfCompletes = resource.type === 'h5p'
    ? Boolean(resource.h5p_self_complete)
    : !['quiz', 'assignment'].includes(resource.type)
```

- Add this case to the `switch` before `default`:

```jsx
    case 'h5p':
      body = <H5PBody resource={resource} onComplete={complete} />
      break
```

In `frontend/src/components/learner/resourceMeta.js`:
- Import `Puzzle` from lucide.
- Add `h5p: Puzzle` to `TYPE_ICONS`.
- Add these to `resourceShape`:

```js
  h5p_self_complete: PropTypes.bool,
  h5p: PropTypes.shape({
    package_id: PropTypes.number,
    path: PropTypes.string,
    language: PropTypes.string,
    version: PropTypes.number,
    title: PropTypes.string,
    main_library: PropTypes.string,
  }),
```

Add the locale keys in all 9 languages with a Node script that preserves indent, line endings and the final newline (same pattern as before):

| key | en | el | fr | es | it | fi | sv | no | de |
|---|---|---|---|---|---|---|---|---|---|
| `lesson.type.h5p` | H5P activity | Δραστηριότητα H5P | Activité H5P | Actividad H5P | Attività H5P | H5P-tehtävä | H5P-aktivitet | H5P-aktivitet | H5P-Aktivität |
| `lesson.h5p.missing` | This H5P activity has no file yet. | Αυτή η δραστηριότητα H5P δεν έχει ακόμη αρχείο. | Cette activité H5P n'a pas encore de fichier. | Esta actividad H5P aún no tiene archivo. | Questa attività H5P non ha ancora un file. | Tällä H5P-tehtävällä ei ole vielä tiedostoa. | Den här H5P-aktiviteten har ingen fil än. | Denne H5P-aktiviteten har ingen fil ennå. | Für diese H5P-Aktivität gibt es noch keine Datei. |
| `lesson.h5p.loadError` | This activity could not be loaded. | Δεν ήταν δυνατή η φόρτωση της δραστηριότητας. | Impossible de charger cette activité. | No se pudo cargar esta actividad. | Impossibile caricare questa attività. | Tehtävää ei voitu ladata. | Aktiviteten kunde inte laddas. | Aktiviteten kunne ikke lastes inn. | Diese Aktivität konnte nicht geladen werden. |

- [ ] **Step 3: Caddy headers.** In `Caddyfile`, replace the `handle /media/* { … }` block and add a `/h5p/*` block before the final `handle { reverse_proxy frontend:80 }`:

```caddyfile
    handle /media/* {
        root * /srv
        # Unpacked H5P packages: readable from the sandboxed player frame
        # (opaque origin), never runnable as AIDEA pages if opened directly.
        header /media/h5p/* {
            Access-Control-Allow-Origin "*"
            Content-Security-Policy "sandbox allow-scripts"
            X-Content-Type-Options "nosniff"
        }
        file_server
    }
    # The H5P player page: sandboxed even when opened as a top-level page.
    handle /h5p/* {
        header {
            Access-Control-Allow-Origin "*"
            Content-Security-Policy "sandbox allow-scripts allow-popups allow-forms"
            X-Content-Type-Options "nosniff"
        }
        reverse_proxy frontend:80
    }
```

- [ ] **Step 4: Verify.**
  - From `frontend/`: `npm run lint`, `npm test`, `node scripts/check-locales.mjs`, and `VITE_API_URL=http://localhost:8000/api npm run build`. Expected: all clean, and `dist/h5p/player.html` plus `dist/h5p/vendor/main.bundle.js` exist.
  - Manual browser check (dev servers; a real `.h5p` from h5p.org such as "Multiple Choice" or "Question Set", uploaded through the API with curl or after Task 8 through the editor; as demo_teacher):
    1. The activity plays and resizes.
    2. Answering produces `h5p_answer` events, and finishing produces `h5p_attempt` and marks the resource done.
    3. In DevTools, in the frame's console context, `window.parent.localStorage` throws and `document.cookie` is empty.

- [ ] **Step 5: Commit** (from the repo root).

```bash
git add frontend/src/components/lesson/H5PFrame.jsx frontend/src/components/lesson/H5PFrame.css frontend/src/components/learner/ResourceView.jsx frontend/src/components/learner/resourceMeta.js frontend/src/locales Caddyfile
git commit -m "feat: learners play H5P activities in a sandboxed frame; results tracked"
git push
```

---

### Task 8: Authoring UI (upload, language versions, self-complete, preview)

**Files:**
- Create: `frontend/src/components/authoring/H5PPanel.jsx`, `H5PPanel.css`
- Modify:
  - `frontend/src/components/authoring/ResourceEditor.jsx`
  - `frontend/src/pages/ModuleEditorPage.jsx` and `.css`
  - `frontend/src/locales/*.json` (`authoring.h5p.*`)

**Interfaces:**
- Consumes:
  - Task 3's endpoint and the `h5p_packages` and `h5p_self_complete` fields.
  - Task 7's `H5PFrame` and `mediaUrl`.
- Produces: `<H5PPanel resource uploadUrl locked onChange onRefresh/>`.

- [ ] **Step 1: Panel.** Create `frontend/src/components/authoring/H5PPanel.jsx`:

```jsx
import { useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { Upload, Trash2, Eye, EyeOff } from 'lucide-react'
import client from '../../api/client'
import H5PFrame from '../lesson/H5PFrame'
import './H5PPanel.css'

const LANGUAGES = ['en', 'el', 'fr', 'es', 'it', 'fi', 'sv', 'no', 'de']
const mb = (bytes) => (bytes / (1024 * 1024)).toFixed(1)
const typeName = (lib) => (lib || '').replace(/^H5P\./, '')

/** H5P resource: main .h5p, optional language versions, self-complete toggle
 *  and an in-page (sandboxed) preview. */
export default function H5PPanel({ resource, uploadUrl, locked, onChange, onRefresh }) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState('')         // language being uploaded
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(false)
  const [newLang, setNewLang] = useState('')
  const packages = resource.h5p_packages ?? []
  const main = packages.find(p => p.language === '')
  const versions = packages.filter(p => p.language !== '')
  const free = LANGUAGES.filter(l => !versions.some(v => v.language === l))

  const upload = async (file, language) => {
    if (!file) return
    setError('')
    setBusy(language || 'main')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('language', language)
      const res = await client.post(uploadUrl, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      onRefresh(res.data)
      setNewLang('')
    } catch (err) {
      const code = err.response?.data?.code
      setError(t(`authoring.h5p.errors.${code}`, { defaultValue: t('authoring.h5p.errors.generic') }))
    } finally {
      setBusy('')
    }
  }

  const remove = async (language) => {
    setError('')
    try {
      const res = await client.delete(uploadUrl, { params: { language } })
      onRefresh(res.data)
    } catch {
      setError(t('authoring.h5p.errors.generic'))
    }
  }

  const fileButton = (language, label) => (
    <label className="lesson-upload-btn">
      <Upload size={14} />
      {busy === (language || 'main') ? t('authoring.h5p.uploading') : label}
      <input type="file" hidden accept=".h5p" disabled={Boolean(busy)}
        onChange={(e) => { upload(e.target.files?.[0], language); e.target.value = '' }} />
    </label>
  )

  return (
    <div className="h5p-panel">
      {main ? (
        <div className="h5p-package">
          <div className="h5p-package-info">
            <strong>{main.title || typeName(main.main_library)}</strong>
            <span className="h5p-package-meta">
              {typeName(main.main_library)} · {mb(main.size_bytes)} MB · {t('authoring.h5p.version', { n: main.version })}
            </span>
          </div>
          <div className="h5p-package-actions">
            <button type="button" className="me-media-btn" onClick={() => setPreview(p => !p)}>
              {preview ? <EyeOff size={14} /> : <Eye size={14} />} {preview ? t('authoring.h5p.hidePreview') : t('authoring.h5p.preview')}
            </button>
            {!locked && fileButton('', t('authoring.h5p.replace'))}
          </div>
        </div>
      ) : (
        !locked && fileButton('', t('authoring.h5p.upload'))
      )}
      {preview && main && (
        <div className="h5p-preview">
          <H5PFrame key={`${main.id}-${main.version}`} pkg={{ package_id: main.id, version: main.version, path: main.path }} title={main.title || 'H5P'} />
        </div>
      )}

      {main && (
        <div className="h5p-versions">
          <p className="lesson-field-label">{t('authoring.h5p.languageVersions')}</p>
          <p className="h5p-hint">{t('authoring.h5p.languageVersionsHint')}</p>
          {versions.map(v => (
            <div key={v.language} className="h5p-version-row">
              <span className="h5p-version-lang">{t(`common.languages.${v.language}`, { defaultValue: v.language })}</span>
              <span className="h5p-package-meta">{v.title} · {t('authoring.h5p.version', { n: v.version })}</span>
              {!locked && fileButton(v.language, t('authoring.h5p.replace'))}
              {!locked && (
                <button type="button" className="me-media-btn me-media-btn--danger" onClick={() => remove(v.language)}
                  title={t('authoring.h5p.remove')}>
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
          {!locked && free.length > 0 && (
            <div className="h5p-version-row">
              <select value={newLang} onChange={(e) => setNewLang(e.target.value)}>
                <option value="">{t('authoring.h5p.addLanguage')}</option>
                {free.map(l => <option key={l} value={l}>{t(`common.languages.${l}`, { defaultValue: l })}</option>)}
              </select>
              {newLang && fileButton(newLang, t('authoring.h5p.upload'))}
            </div>
          )}
        </div>
      )}

      <label className="resource-editor-required">
        <input type="checkbox" checked={Boolean(resource.h5p_self_complete)} disabled={locked}
          onChange={(e) => onChange('h5p_self_complete', e.target.checked)} />
        {t('authoring.h5p.selfComplete')}
      </label>
      <p className="h5p-hint">{t('authoring.h5p.selfCompleteHint')}</p>
      {error && <p className="media-item-error">{error}</p>}
    </div>
  )
}

H5PPanel.propTypes = {
  resource: PropTypes.shape({
    h5p_packages: PropTypes.array,
    h5p_self_complete: PropTypes.bool,
  }).isRequired,
  uploadUrl: PropTypes.string.isRequired,
  locked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  onRefresh: PropTypes.func.isRequired,
}
```

Before writing the language labels, check whether `common.languages.<code>` exists in `en.json`: `node -e "console.log(require('./src/locales/en.json').common?.languages)"`. If it doesn't, use whichever key the existing language pickers use (grep `'el'` in `src/components` for the pattern) and replace `common.languages` above with it. Record a ledger ruling if you change it.

Create `frontend/src/components/authoring/H5PPanel.css`:

```css
.h5p-panel { display: flex; flex-direction: column; gap: 0.6rem; }
.h5p-package { display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.h5p-package-info { display: flex; flex-direction: column; gap: 0.15rem; }
.h5p-package-meta, .h5p-hint { color: var(--color-text-muted); font-size: 0.8rem; margin: 0; }
.h5p-package-actions { display: flex; gap: 0.5rem; align-items: center; }
.h5p-preview { border: 1px solid var(--color-border); border-radius: var(--radius); padding: 0.5rem; }
.h5p-versions { display: flex; flex-direction: column; gap: 0.4rem; }
.h5p-version-row { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.h5p-version-lang { font-weight: 500; min-width: 6rem; }
```

- [ ] **Step 2: Wire it in.**

In `frontend/src/components/authoring/ResourceEditor.jsx`:
- Import `H5PPanel from './H5PPanel'`.
- Add props `uploadUrl` and `onRefresh` to the function signature and to `propTypes` (`uploadUrl: PropTypes.string`, `onRefresh: PropTypes.func`).
- Add `h5p_packages: PropTypes.array` and `h5p_self_complete: PropTypes.bool` to the `resource` shape.
- After the assignment block, add:

```jsx
        {resource.type === 'h5p' && !translating && (
          <H5PPanel resource={resource} uploadUrl={uploadUrl} locked={structureLocked}
            onChange={onChange} onRefresh={onRefresh} />
        )}
```

In `frontend/src/pages/ModuleEditorPage.jsx`:
- Import `Puzzle` from lucide.
- Add `{ type: 'h5p', Icon: Puzzle, color: 'teal' },` to `RESOURCE_TYPES`.
- In `validateResource`, add:

```jsx
  if (resource.type === 'h5p' && !(resource.h5p_packages ?? []).some(p => p.language === '')) {
    return t('authoring.h5p.fileRequiredError')
  }
```

- In `saveResource`'s original-language branch, add `h5p_self_complete: h5pSelfComplete` to the destructuring and to the PATCH body:

```jsx
        const { title, content, url: link, caption, quiz_data: quizData, instructions, is_required: isRequired, h5p_self_complete: h5pSelfComplete } = resource
        res = await client.patch(url, {
          title, content, url: link, caption, quiz_data: quizData, instructions, is_required: isRequired,
          ...(resource.type === 'h5p' && { h5p_self_complete: Boolean(h5pSelfComplete) }),
        })
```

- `ActivityEditor`: add the props `resourceUrl` (a function from resource id to URL) and `onResourceRefresh` (resource id and data). Add them to its propTypes (`PropTypes.func.isRequired`), and pass them to each `<ResourceEditor>`:

```jsx
                  uploadUrl={`${resourceUrl(resource.id)}h5p/`}
                  onRefresh={(data) => onResourceRefresh(resource.id, data)}
```

- Where `<ActivityEditor` is rendered (beside `onResourceMove={moveResource}`), add:

```jsx
              resourceUrl={(resourceId) => `${resourcesUrl(selectedLessonId)}${resourceId}/`}
              onResourceRefresh={(resourceId, data) => patchResource(resourceId, {
                h5p_packages: data.h5p_packages,
                h5p_self_complete: data.h5p_self_complete,
                ...(data.title && { title: data.title }),
              })}
```

In `frontend/src/pages/ModuleEditorPage.css`, add teal versions of the three per-colour rules (next to the `--indigo` lines):

```css
.me-type-btn--teal { background: #f0fdfa; color: #0d9488; border-color: #99f6e4; }
.lesson-type-icon--teal { color: #0d9488; }
.lesson-editor-icon-wrap--teal { background: #f0fdfa; color: #0d9488; }
```

- [ ] **Step 3: Locales (9 languages).** Add `authoring.h5p` to every locale with the same Node-script pattern. Write `en` exactly as below. For el, fr, es, it, fi, sv, no and de, write real translations in each locale's existing tone, keeping `{{n}}` unchanged:

```json
"h5p": {
  "upload": "Upload .h5p file",
  "replace": "Replace file",
  "uploading": "Uploading…",
  "preview": "Preview",
  "hidePreview": "Hide preview",
  "version": "version {{n}}",
  "languageVersions": "Language versions",
  "languageVersionsHint": "Optional: a translated .h5p for learners using that language. Others see the main file.",
  "addLanguage": "Add a language version…",
  "remove": "Remove",
  "selfComplete": "Learners mark it done themselves",
  "selfCompleteHint": "Tick this for activities without questions, such as Accordion or plain slides.",
  "fileRequiredError": "Upload the .h5p file first.",
  "errors": {
    "generic": "The upload failed. Please try again.",
    "no_file": "Choose a .h5p file.",
    "not_zip": "This is not a valid .h5p file.",
    "too_large": "The file is larger than 100 MB.",
    "too_large_unpacked": "The package is too large once unpacked (over 300 MB).",
    "too_many_files": "The package contains too many files.",
    "unsafe_path": "The package contains an unsafe file path.",
    "bad_extension": "The package contains a file type H5P does not allow.",
    "no_h5p_json": "This is not an H5P package (h5p.json is missing or unreadable).",
    "no_content": "The package has no content (content/content.json is missing).",
    "missing_libraries": "This file doesn't include its H5P libraries — export it again with libraries included.",
    "bad_language": "Unknown language.",
    "not_h5p": "This resource is not an H5P activity."
  }
}
```

- [ ] **Step 4: Verify.**
  - From `frontend/`: `npm run lint`, `npm test`, `node scripts/check-locales.mjs` and `VITE_API_URL=http://localhost:8000/api npm run build`. Expected: all clean.
  - Manual check as demo_creator:
    1. Add an "H5P activity" and upload a `.h5p`. The name, type and size show, and Preview plays it.
    2. Add a Greek version, then remove it.
    3. Tick "Learners mark it done themselves" and save.
    4. Upload a `.html` renamed to `.h5p`: the "not a valid .h5p" message appears.

- [ ] **Step 5: Commit.**

```bash
git add src/components/authoring/H5PPanel.jsx src/components/authoring/H5PPanel.css src/components/authoring/ResourceEditor.jsx src/pages/ModuleEditorPage.jsx src/pages/ModuleEditorPage.css src/locales
git commit -m "feat: authors upload H5P activities with language versions and preview"
git push
```

---

### Task 9: Analytics display, privacy line, docs, full verification

**Files:**
- Modify:
  - `frontend/src/components/analytics/ContentTree.jsx`
  - `frontend/src/components/analytics/LearnerTimeline.jsx`
  - `frontend/src/locales/*.json` (`analytics.course.notes.*`, `analytics.course.detail.*`)
  - `frontend/src/pages/PrivacyPage.jsx`
  - `CLAUDE.md`

**Interfaces:**
- Consumes: Task 5's notes keys and the timeline `h5p` block.

- [ ] **Step 1: Content notes.** In `ContentTree.jsx` `ResourceNotes`, add before `if (!parts.length)`:

```jsx
  if (type === 'h5p') {
    if (notes.finished) parts.push(t('analytics.course.notes.h5pFinished', { count: notes.finished }))
    if (notes.avg_score_pct != null) parts.push(t('analytics.course.notes.score', { pct: notes.avg_score_pct }))
    if (notes.avg_attempts != null) parts.push(t('analytics.course.notes.avgAttempts', { n: notes.avg_attempts }))
    if (notes.hardest_question) parts.push(t('analytics.course.notes.hardestText', { pct: notes.hardest_question.pct_correct }))
  }
```

(The existing `title={notes.hardest_question?.question}` already shows the question text on hover.)

- [ ] **Step 2: Timeline.** In `LearnerTimeline.jsx` `ResourceDetails`:
- After the quiz-score line, add `if (r.h5p_attempts) bits.push(t('analytics.course.detail.attempts', { count: r.h5p_attempts }))`.
- After the quiz answers list, add:

```jsx
      {r.h5p?.answers?.length > 0 && (
        <ol className="acp-answers">
          {r.h5p.answers.map((a, i) => (
            <li key={i}>
              {a.correct === true ? <CheckCircle2 size={13} className="acp-right" />
                : a.correct === false ? <XCircle size={13} className="acp-wrong" />
                  : <Circle size={13} className="acp-muted" />}
              <span className="acp-answer-t">{t('analytics.course.detail.attemptN', { n: a.attempt })}</span>
              <span className="acp-answer-q">{a.question}</span>
              <span className="acp-answer-a">{a.response || '—'}</span>
              {a.seconds != null && <span className="acp-answer-t">{t('analytics.course.detail.answerTime', { s: a.seconds })}</span>}
            </li>
          ))}
        </ol>
      )}
```

- [ ] **Step 3: Locales.** Add these in all 9 languages (en shown; translate the rest in the existing tone):
  - `analytics.course.notes.h5pFinished`: `"finished by {{count}}"`
  - `analytics.course.notes.avgAttempts`: `"avg. {{n}} attempts"`
  - `analytics.course.notes.hardestText`: `"hardest question {{pct}}% right"`
  - `analytics.course.detail.attempts`: `"{{count}} attempts"`
  - `analytics.course.detail.attemptN`: `"#{{n}}"`

- [ ] **Step 4: Privacy and docs.**
  - In `PrivacyPage.jsx` section 11, change the second bullet to: `<li>video playback (play, pause, skipping and how much was watched), your quiz answers and the time taken per question, your answers and scores in interactive H5P activities, and when a PDF or image is opened or downloaded;</li>`
  - In `CLAUDE.md` API endpoints, add: ``- `POST/DELETE /api/authoring/courses/<id>/modules/<m>/lessons/<a>/resources/<r>/h5p/` — upload (multipart `file`, `language`) or remove an H5P package; played by `/h5p/player.html` (h5p-standalone) in a sandboxed iframe``

- [ ] **Step 5: Full verification.**

From `backend/`:

```bash
"$UV" run ruff check .
"$UV" run coverage run manage.py test hub analytics --verbosity=1
"$UV" run coverage report --fail-under=70
"$UV" run manage.py makemigrations --check --dry-run
```

From `frontend/`: `npm run lint && npm test && node scripts/check-locales.mjs && VITE_API_URL=http://localhost:8000/api npm run build`

Expected: everything passes, and makemigrations reports "No changes detected".

- [ ] **Step 6: Commit** (from the repo root).

```bash
git add frontend/src/components/analytics frontend/src/locales frontend/src/pages/PrivacyPage.jsx CLAUDE.md
git commit -m "feat: H5P results on the analytics page; privacy policy and docs"
git push
```

- [ ] **Step 7: Deployment note for the user.** The VM's `.env` must contain `COMPOSE_FILE=…`. Then:

```bash
git pull
docker compose up -d --build backend celery celery-beat frontend   # backend Dockerfile changed (timeout)
docker compose exec -T backend uv run python manage.py migrate       # 0062_h5p (adds a table + columns)
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile # new H5P headers
```

Never use `--remove-orphans` or `down -v`.
