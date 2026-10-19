# Presentation Resource Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new **Presentation** resource. The author uploads a .pptx (optionally one per language) and learners watch it in Microsoft's Office viewer inside the activity, with animations and media. It completes with "Mark as done", records time and downloads, and the author decides whether learners may download it.

**Architecture:**
- `PresentationFile` rows hold the uploaded decks: one per resource × language (`''` = main deck).
- `hub/presentation.py` checks the upload (a real .pptx, no macros, slide count and title).
- An authoring endpoint uploads and removes decks, shaped like the H5P one.
- The learner payload gives the deck in the viewer's language.
- React shows the deck in an iframe pointing at `view.officeapps.live.com`, with a notice instead on development hosts.
- Focus inside the frame counts as active time.

**Tech Stack:** Django 5 + DRF, `zipfile` + `xml.etree` (standard library), React 19, lucide-react, Caddy.

**Spec:** `docs/superpowers/specs/2026-10-19-presentation-resource-design.md`

## Global Constraints

- **Format:** .pptx only.
  - .ppt and .odp get error code `convert_to_pptx` with the advice: *"Save it as .pptx (in Impress: File → Save As → PowerPoint), then upload again."*
  - Macro-enabled decks get `macros`. Non-.pptx files get `not_pptx`, broken ones `corrupt`, decks with no slides `no_slides`.
- **Size:**
  - uploads up to `settings.PRESENTATION_MAX_MB` (default **100**; over it, error `too_large`);
  - the viewer warning threshold is `settings.PRESENTATION_VIEWER_LIMIT_MB` (default **10**);
  - both can be overridden from the environment.
- **Download:** the learner payload's `downloadable` is `resource.presentation_downloadable OR the deck is over the viewer limit`. `presentation_downloadable` defaults to **False**.
- **Viewer:** `https://view.officeapps.live.com/op/embed.aspx?src=` + `encodeURIComponent(absolute file URL)`.
  - On private or development hosts (`localhost`, `*.localhost`, `*.local`, `127.*`, `10.*`, `192.168.*`, `172.16–31.*`, `0.0.0.0`, `::1`) the frame is replaced by a notice plus a download link.
- **Completion:** "Mark as done", as for PDF and video. No automatic completion.
- **Tracking:**
  - focus inside the presentation frame counts as active for up to `PRESENTATION_FOCUS_MS` = **5 minutes** per focus;
  - downloads are sent as event `presentation_download` with `{language}` when it isn't the main deck.
- **Files:**
  - stored at `media/presentations/<resource id>/<32-hex>.pptx`;
  - replacing deletes the old file, and removing a deck or deleting the resource deletes its file;
  - a copied module gets its **own copy** of each deck.
- **Language versions:** a learner gets the deck in their language when one exists, else the main deck. Only languages in `hub.translation.LANGUAGE_NAMES` (or `''`) are accepted.
- **Shared rules:**
  - keep all 9 locales in sync (`node scripts/check-locales.mjs`);
  - icons from `lucide-react`; per-component CSS;
  - ESLint is ES2020 (no numeric separators) with the React-compiler purity rule (`Date.now()` stays out of component bodies).
- **Runner and git:**
  - from `backend/`, set `UV="/c/Users/Nikos A. Grammatikos/.local/bin/uv.exe"`, then `"$UV" run manage.py test …` and `"$UV" run ruff check hub analytics`;
  - frontend from `frontend/`: `npm test`, `npm run lint`, `VITE_API_URL=http://localhost:8000/api npm run build`;
  - keep each file's line endings (CRLF files stay CRLF);
  - work on `master`; commit and push after each task, with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A copied module, then a replaced deck in the original:** the copy must keep playing its own deck, because each copy owns a file. Pinned by Task 3 `test_copied_module_gets_its_own_deck_file`.
2. **Replacing a deck:** the old file is removed from disk, the version goes up, and the language versions are untouched. Pinned by Task 3 `test_replace_deletes_old_file_and_bumps_version`.
3. **Hostile or odd uploads:**
   - a .docx (a valid OOXML zip that isn't a deck), a renamed .txt, a .ppt, an .odp, a zip bomb in `presentation.xml`, a deck with no slides;
   - each must give its own error code and never a 500.
   - Pinned by Task 2's tests, one per case.
4. **The learner's language has no deck:** fall back to the main deck. If there's no main deck either, `presentation` is `null` and the page shows "no file yet" rather than crashing. Pinned by Task 4 `test_falls_back_to_main_deck` and `test_no_deck_gives_null`.
5. **The frame focus timer:**
   - focus counts only while inside *this* frame (not another iframe, such as a YouTube player in the same activity);
   - it stops at the 5-minute cap or when focus returns.
   - Pinned by Task 6 `frameFocus.test.js`.

---

## File Structure

**Backend**
- `hub/models/presentation.py` (new): `PresentationFile`, `presentation_upload_to`, and a post-delete file cleanup.
- `hub/models/content.py`: `Resource.Type.PRESENTATION`, `Activity.LessonType.PRESENTATION`, `Resource.presentation_downloadable`.
- `hub/models/tracking.py`: `LearningEvent.Type.PRESENTATION_DOWNLOAD`; `event_type` max_length 20 → 30.
- `hub/models/__init__.py`; `hub/migrations/0067_presentation.py` (generated).
- `aidea/settings.py`: `PRESENTATION_MAX_MB`, `PRESENTATION_VIEWER_LIMIT_MB`.
- `hub/presentation.py` (new): `check_pptx`, `PresentationError`, `DeckInfo`.
- `hub/views/authoring_presentation.py` (new): `AuthoringPresentationView`.
- `hub/urls.py`; `hub/serializers/content.py` (authoring and learner payloads); `hub/views/authoring_module_library.py` (copy decks).
- `analytics/learning.py`, `analytics/workbook.py`.
- `Caddyfile`.
- Tests: `hub/tests/test_presentation_models.py`, `test_presentation_check.py`, `test_presentation_api.py`, `test_presentation_learner.py`, `analytics/tests/test_presentation_analytics.py`.

**Frontend**
- `src/lib/presentation.js` and `.test.js` (new): `officeViewerUrl`, `isPrivateHost`, `absoluteUrl`.
- `src/lib/tracking/frameFocus.js` and `.test.js` (new): `watchFrameFocus`, `PRESENTATION_FOCUS_MS`.
- `src/lib/tracking/tracker.js`, `TrackingContext.js`: `attending(resourceId, on)`.
- `src/api/client.js`: export `API_BASE`.
- `src/components/lesson/PresentationFrame.jsx` and `.css` (new): viewer frame, full screen, development notice, focus hook-up.
- `src/components/authoring/PresentationPanel.jsx` and `.css` (new); `ResourceEditor.jsx`; `pages/ModuleEditorPage.jsx` and `.css`.
- `src/components/learner/ResourceView.jsx` (`PresentationBody`), `resourceMeta.js`.
- `src/components/analytics/ContentTree.jsx`, `LearnerTimeline.jsx`.
- `src/pages/PrivacyPage.jsx`; `src/locales/*.json`.

---

### Task 1: Models, settings, event type, migration

**Files:**
- Create: `backend/hub/models/presentation.py`, `backend/hub/tests/test_presentation_models.py`
- Modify:
  - `backend/hub/models/content.py`, `backend/hub/models/tracking.py`, `backend/hub/models/__init__.py`
  - `backend/aidea/settings.py`
  - `backend/hub/migrations/0067_presentation.py` (generated)

**Interfaces — Produces:**
- `Resource.Type.PRESENTATION == 'presentation'`, `Activity.LessonType.PRESENTATION == 'presentation'`.
- `Resource.presentation_downloadable` (bool, default False).
- `PresentationFile`:
  - fields: `resource` (related_name `presentation_files`), `language`, `file`, `title`, `slide_count`, `size_bytes`, `version`, `uploaded_by`, `uploaded_at`; unique `(resource, language)`;
  - properties `over_viewer_limit` (bool) and `media_path` (site-relative URL);
  - deleting a row deletes its file.
- `LearningEvent.Type.PRESENTATION_DOWNLOAD == 'presentation_download'`.
- `settings.PRESENTATION_MAX_MB` (100), `settings.PRESENTATION_VIEWER_LIMIT_MB` (10).

- [ ] **Step 1: Write the failing test.** `backend/hub/tests/test_presentation_models.py`:

```python
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from hub.models import (
    Activity,
    Course,
    LearningEvent,
    LearningPillar,
    Module,
    PresentationFile,
    Resource,
)

MEDIA = tempfile.mkdtemp(prefix='aidea-pres-media-')


def make_presentation_resource(title='Deck course', creator=None):
    pillar = LearningPillar.objects.get_or_create(slug='p-pres', defaults={'name': 'P', 'order': 1})[0]
    course = Course.objects.create(title=title, pillar=pillar, level='beginner', duration_hours=1,
                                   is_published=True, created_by=creator)
    module = Module.objects.create(course=course, title='M', order=1)
    activity = Activity.objects.create(module=module, title='A', order=1, lesson_type='presentation')
    resource = Resource.objects.create(activity=activity, type='presentation', order=1)
    return course, module, activity, resource


@override_settings(MEDIA_ROOT=MEDIA)
class PresentationModelTests(TestCase):
    def test_types_and_defaults(self):
        *_, resource = make_presentation_resource()
        self.assertEqual(resource.get_type_display(), 'Presentation')
        self.assertFalse(resource.presentation_downloadable)
        self.assertIn('presentation_download', LearningEvent.Type.values)
        event_type = LearningEvent._meta.get_field('event_type')
        self.assertGreaterEqual(event_type.max_length, len('presentation_download'))

    def test_file_path_size_flag_and_media_path(self):
        *_, resource = make_presentation_resource()
        deck = PresentationFile(resource=resource, language='', size_bytes=11 * 1024 * 1024)
        deck.file.save('anything.pptx', ContentFile(b'PK'), save=False)
        deck.save()
        self.assertRegex(deck.file.name, rf'^presentations/{resource.id}/[0-9a-f]{{32}}\.pptx$')
        self.assertTrue(deck.over_viewer_limit)
        self.assertEqual(deck.media_path, f'/media/{deck.file.name}')
        with override_settings(PRESENTATION_VIEWER_LIMIT_MB=20):
            self.assertFalse(deck.over_viewer_limit)

    def test_deleting_the_resource_deletes_the_file(self):
        *_, resource = make_presentation_resource()
        deck = PresentationFile(resource=resource)
        deck.file.save('x.pptx', ContentFile(b'PK'), save=False)
        deck.save()
        path = Path(MEDIA) / deck.file.name
        self.assertTrue(path.exists())
        resource.delete()
        self.assertFalse(path.exists())

    def test_settings_defaults(self):
        from django.conf import settings
        self.assertEqual((settings.PRESENTATION_MAX_MB, settings.PRESENTATION_VIEWER_LIMIT_MB), (100, 10))
```

- [ ] **Step 2: Run the test to verify it fails.**
  - Run: `"$UV" run manage.py test hub.tests.test_presentation_models -v 2`
  - Expected: ImportError, `cannot import name 'PresentationFile'`.

- [ ] **Step 3: Implement.** `backend/hub/models/presentation.py`:

```python
"""Uploaded PowerPoint decks for presentation resources — see
docs/superpowers/specs/2026-10-19-presentation-resource-design.md.

One PresentationFile per presentation resource × language ('' = the main
deck), played in Microsoft's Office viewer, which fetches the file by its
public (but unguessable) URL. Each file belongs to exactly one resource —
copied modules get their own copy — so replacing or removing deletes it."""
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


def presentation_upload_to(instance, filename):
    return f'presentations/{instance.resource_id}/{uuid.uuid4().hex}.pptx'


class PresentationFile(models.Model):
    resource    = models.ForeignKey('hub.Resource', on_delete=models.CASCADE, related_name='presentation_files')
    language    = models.CharField(max_length=8, blank=True)  # '' = main deck
    file        = models.FileField(upload_to=presentation_upload_to, max_length=255)
    title       = models.CharField(max_length=255, blank=True)
    slide_count = models.PositiveIntegerField(default=0)
    size_bytes  = models.PositiveBigIntegerField(default=0)
    version     = models.PositiveIntegerField(default=1)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    uploaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('resource', 'language')
        ordering = ['language']

    def __str__(self):
        return f'Deck for resource {self.resource_id} [{self.language or "main"}]'

    @property
    def over_viewer_limit(self):
        return self.size_bytes > settings.PRESENTATION_VIEWER_LIMIT_MB * 1024 * 1024

    @property
    def media_path(self):
        """Site-relative URL of the file."""
        return f'{settings.MEDIA_URL}{self.file.name}'


@receiver(post_delete, sender=PresentationFile)
def _delete_deck_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
```

`backend/hub/models/content.py`:
- add `PRESENTATION = 'presentation', 'Presentation'` to both `Resource.Type` and `Activity.LessonType`, after `H5P`;
- after `h5p_self_complete`, add:

```python
    # presentation: learners may download the .pptx (forced on for decks over the viewer limit).
    presentation_downloadable = models.BooleanField(default=False)
```

`backend/hub/models/tracking.py`:
- in `LearningEvent.Type`, add `PRESENTATION_DOWNLOAD = 'presentation_download', 'Presentation downloaded'`;
- change `event_type = models.CharField(max_length=20, …)` to `max_length=30`.

`backend/hub/models/__init__.py`: add `from .presentation import PresentationFile` (alphabetically, after `.preference_quiz`) and add `'PresentationFile'` to `__all__`.

`backend/aidea/settings.py`: after the media settings (`MEDIA_ROOT`), add:

```python
# Presentation (.pptx) resources: upload limit, and the size above which
# Microsoft's Office viewer may refuse to play a deck (learners then also get a download).
PRESENTATION_MAX_MB = int(os.getenv('PRESENTATION_MAX_MB', '100'))
PRESENTATION_VIEWER_LIMIT_MB = int(os.getenv('PRESENTATION_VIEWER_LIMIT_MB', '10'))
```

Generate the migration with `"$UV" run manage.py makemigrations hub --name presentation`. Expected: `0067_presentation.py` with the new model, the field, the choices and the alter. Then run `"$UV" run manage.py migrate`.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_presentation_models -v 2`
  - Expected: 4 tests pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/models aidea/settings.py hub/migrations/0067_presentation.py hub/tests/test_presentation_models.py
git commit -m "feat: presentation resource type, deck model and settings"
git push
```

---

### Task 2: Checking an uploaded deck

**Files:**
- Create: `backend/hub/presentation.py`, `backend/hub/tests/test_presentation_check.py`

**Interfaces — Produces:**
- `PresentationError(code)`, with `.code` and `.detail` (the English message from `MESSAGES`). The codes are `not_pptx`, `convert_to_pptx`, `macros`, `corrupt` and `no_slides`.
- `DeckInfo(title: str, slide_count: int)`.
- `check_pptx(fileobj) -> DeckInfo`: reads a file-like object and **rewinds it to 0** before returning or raising.
- `PPTX_MAIN_TYPE`: the content-type string.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_presentation_check.py`:

```python
import io
import zipfile

from django.test import SimpleTestCase

from hub import presentation
from hub.presentation import PPTX_MAIN_TYPE, PresentationError, check_pptx

MACRO_TYPE = 'application/vnd.ms-powerpoint.presentation.macroEnabled.main+xml'


def make_pptx(slides=3, title='AI risks', main_type=PPTX_MAIN_TYPE, extra=None, drop=(), presentation_xml=None):
    """A minimal .pptx: just the parts check_pptx reads."""
    ids = ''.join(f'<p:sldId id="{256 + i}" r:id="rId{i + 2}"/>' for i in range(slides))
    parts = {
        '[Content_Types].xml': (
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            f'<Override PartName="/ppt/presentation.xml" ContentType="{main_type}"/></Types>'
        ),
        'ppt/presentation.xml': presentation_xml or (
            '<?xml version="1.0"?><p:presentation '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<p:sldIdLst>{ids}</p:sldIdLst></p:presentation>'
        ),
        'docProps/core.xml': (
            '<?xml version="1.0"?><cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            f'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{title}</dc:title></cp:coreProperties>'
        ),
    }
    parts.update(extra or {})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            if name not in drop:
                z.writestr(name, data)
    buffer.seek(0)
    return buffer


class CheckPptxTests(SimpleTestCase):
    def code(self, fileobj):
        with self.assertRaises(PresentationError) as ctx:
            check_pptx(fileobj)
        return ctx.exception.code

    def test_valid_deck(self):
        f = make_pptx(slides=3, title='AI risks')
        info = check_pptx(f)
        self.assertEqual((info.title, info.slide_count), ('AI risks', 3))
        self.assertEqual(f.tell(), 0)

    def test_missing_title_is_empty(self):
        self.assertEqual(check_pptx(make_pptx(drop=('docProps/core.xml',))).title, '')

    def test_old_ppt_asks_to_convert(self):
        self.assertEqual(self.code(io.BytesIO(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\0' * 100)), 'convert_to_pptx')

    def test_odp_asks_to_convert(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            z.writestr('mimetype', 'application/vnd.oasis.opendocument.presentation')
            z.writestr('content.xml', '<x/>')
        buffer.seek(0)
        self.assertEqual(self.code(buffer), 'convert_to_pptx')

    def test_renamed_text_file_is_not_pptx(self):
        self.assertEqual(self.code(io.BytesIO(b'just some notes')), 'not_pptx')

    def test_word_document_is_not_pptx(self):
        docx_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
        f = make_pptx(main_type=docx_type, drop=('ppt/presentation.xml',), extra={'word/document.xml': '<w/>'})
        self.assertEqual(self.code(f), 'not_pptx')

    def test_macros_are_refused(self):
        self.assertEqual(self.code(make_pptx(main_type=MACRO_TYPE)), 'macros')
        self.assertEqual(self.code(make_pptx(extra={'ppt/vbaProject.bin': b'\0'})), 'macros')

    def test_broken_zip_is_corrupt(self):
        self.assertEqual(self.code(io.BytesIO(b'PK\x03\x04' + b'garbage' * 20)), 'corrupt')

    def test_unreadable_xml_is_corrupt(self):
        self.assertEqual(self.code(make_pptx(presentation_xml='<p:presentation><unclosed>')), 'corrupt')

    def test_oversized_xml_part_is_corrupt(self):
        big = '<p:presentation xmlns:p="x">' + ' ' * (presentation.MAX_XML_BYTES + 1) + '</p:presentation>'
        self.assertEqual(self.code(make_pptx(presentation_xml=big)), 'corrupt')

    def test_no_slides(self):
        self.assertEqual(self.code(make_pptx(slides=0)), 'no_slides')

    def test_position_reset_after_error(self):
        f = io.BytesIO(b'just some notes')
        self.code(f)
        self.assertEqual(f.tell(), 0)
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_presentation_check -v 2`
  - Expected: ImportError, `cannot import name 'presentation' from 'hub'`.

- [ ] **Step 3: Implement.** `backend/hub/presentation.py`:

```python
"""Checking uploaded PowerPoint decks (.pptx) for presentation resources.

Only what the slideshow needs is read: the content types (is it a real,
macro-free presentation?), the slide list and the title. Parts are size-capped
before parsing so a crafted file cannot exhaust memory."""
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree

PPTX_MAIN_TYPE = 'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'
MACRO_MAIN_TYPE = 'application/vnd.ms-powerpoint.presentation.macroEnabled.main+xml'
OLE_MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'      # .ppt and other pre-2007 Office files
ODF_PREFIX = b'application/vnd.oasis.opendocument'
NS_P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
NS_DC = 'http://purl.org/dc/elements/1.1/'
MAX_XML_BYTES = 5 * 1024 * 1024

MESSAGES = {
    'not_pptx': 'This is not a PowerPoint (.pptx) file.',
    'convert_to_pptx': 'Save it as .pptx (in Impress: File → Save As → PowerPoint), then upload again.',
    'macros': 'Presentations with macros cannot be used. Save it as a normal .pptx.',
    'corrupt': 'The file is damaged or could not be read.',
    'no_slides': 'This presentation has no slides.',
}


class PresentationError(Exception):
    def __init__(self, code):
        super().__init__(MESSAGES[code])
        self.code = code
        self.detail = MESSAGES[code]


@dataclass
class DeckInfo:
    title: str
    slide_count: int


def _read(archive, name):
    info = archive.getinfo(name)
    if info.file_size > MAX_XML_BYTES:
        raise PresentationError('corrupt')
    return archive.read(name)


def _title(archive, names):
    if 'docProps/core.xml' not in names:
        return ''
    try:
        root = ElementTree.fromstring(_read(archive, 'docProps/core.xml'))
    except (ElementTree.ParseError, PresentationError):
        return ''
    node = root.find(f'{{{NS_DC}}}title')
    return (node.text or '').strip()[:255] if node is not None else ''


def _inspect(fileobj):
    head = fileobj.read(8)
    fileobj.seek(0)
    if head == OLE_MAGIC:
        raise PresentationError('convert_to_pptx')
    if not head.startswith(b'PK'):
        raise PresentationError('not_pptx')
    try:
        with zipfile.ZipFile(fileobj) as archive:
            names = set(archive.namelist())
            if 'mimetype' in names and _read(archive, 'mimetype').strip().startswith(ODF_PREFIX):
                raise PresentationError('convert_to_pptx')
            if '[Content_Types].xml' not in names:
                raise PresentationError('not_pptx')
            types = _read(archive, '[Content_Types].xml').decode('utf-8', 'replace')
            if MACRO_MAIN_TYPE in types or 'ppt/vbaProject.bin' in names:
                raise PresentationError('macros')
            if PPTX_MAIN_TYPE not in types or 'ppt/presentation.xml' not in names:
                raise PresentationError('not_pptx')
            root = ElementTree.fromstring(_read(archive, 'ppt/presentation.xml'))
            slides = root.find(f'{{{NS_P}}}sldIdLst')
            count = len(slides) if slides is not None else 0
            if count == 0:
                raise PresentationError('no_slides')
            return DeckInfo(title=_title(archive, names), slide_count=count)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ElementTree.ParseError, KeyError, OSError, EOFError):
        raise PresentationError('corrupt') from None


def check_pptx(fileobj):
    try:
        return _inspect(fileobj)
    finally:
        fileobj.seek(0)
```

Note: `zlib.error` from a broken deflate stream is a subclass of `Exception`, not of the errors above. If `test_broken_zip_is_corrupt` raises `zlib.error`, add `zlib.error` to the `except` tuple (with `import zlib`) and record a ruling.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_presentation_check -v 2`
  - Expected: 12 tests pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/presentation.py hub/tests/test_presentation_check.py
git commit -m "feat: check uploaded .pptx decks (format, macros, slides, title)"
git push
```

---

### Task 3: Authoring API, authoring payload, module copy, Caddy

**Files:**
- Create: `backend/hub/views/authoring_presentation.py`, `backend/hub/tests/test_presentation_api.py`
- Modify:
  - `backend/hub/urls.py`
  - `backend/hub/serializers/content.py` (`ResourceSerializer`)
  - `backend/hub/views/authoring_module_library.py` (`copy_module`)
  - `Caddyfile`

**Interfaces:**
- **Consumes:** Task 1's `PresentationFile` and settings; Task 2's `check_pptx` and `PresentationError`.
- **Produces:**
  - `POST /api/authoring/courses/<pk>/modules/<module_pk>/lessons/<lesson_pk>/resources/<resource_pk>/presentation/` (`authoring-resource-presentation`), multipart `file` and `language`. Returns 201 and `ResourceSerializer` data. Errors are 400 `{code, detail}`, with the codes from Task 2 plus `no_file`, `too_large`, `bad_language` and `not_presentation`.
  - `DELETE …/presentation/?language=`: 200 and the serializer data, or 404.
  - `ResourceSerializer`:
    - `presentation_downloadable` is writable;
    - `presentation_files` is read-only: a list of `{id, language, title, slide_count, size_bytes, version, path, over_viewer_limit, uploaded_at}`.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_presentation_api.py`:

```python
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import CourseEditHistory, PresentationFile, UserProfile
from hub.views.authoring_module_library import copy_module

from .test_presentation_check import make_pptx
from .test_presentation_models import make_presentation_resource

MEDIA = tempfile.mkdtemp(prefix='aidea-pres-api-')


def deck(name='deck.pptx', **kw):
    return SimpleUploadedFile(name, make_pptx(**kw).read(),
                              content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation')


@override_settings(MEDIA_ROOT=MEDIA)
class PresentationAPITests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user('pres_cc', password='x')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.module, self.activity, self.resource = make_presentation_resource(creator=self.creator)
        self.url = reverse('authoring-resource-presentation', kwargs={
            'pk': self.course.id, 'module_pk': self.module.id, 'lesson_pk': self.activity.id,
            'resource_pk': self.resource.id})
        self.client.force_authenticate(self.creator)

    def upload(self, language='', **kw):
        return self.client.post(self.url, {'file': deck(**kw), 'language': language}, format='multipart')

    def test_upload_main_deck(self):
        res = self.upload(slides=4, title='AI risks')
        self.assertEqual(res.status_code, 201, res.data)
        [info] = res.data['presentation_files']
        self.assertEqual((info['language'], info['slide_count'], info['title'], info['version'],
                          info['over_viewer_limit']), ('', 4, 'AI risks', 1, False))
        self.assertTrue(info['path'].startswith('/media/presentations/'))
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.title, 'AI risks')            # first main deck names an untitled resource
        self.assertTrue(CourseEditHistory.objects.filter(course=self.course).exists())

    def test_title_falls_back_to_file_name(self):
        res = self.client.post(self.url, {'file': deck('Week 1 slides.pptx', title=''), 'language': ''}, format='multipart')
        self.assertEqual(res.data['presentation_files'][0]['title'], 'Week 1 slides')

    def test_errors_have_codes(self):
        bad = SimpleUploadedFile('notes.pptx', b'plain text')
        self.assertEqual(self.client.post(self.url, {'file': bad}, format='multipart').data['code'], 'not_pptx')
        self.assertEqual(self.client.post(self.url, {}, format='multipart').data['code'], 'no_file')
        self.assertEqual(self.upload(language='xx').data['code'], 'bad_language')
        with override_settings(PRESENTATION_MAX_MB=0):
            self.assertEqual(self.upload().data['code'], 'too_large')

    def test_replace_deletes_old_file_and_bumps_version(self):
        self.upload()
        self.upload(language='el')
        old = PresentationFile.objects.get(resource=self.resource, language='')
        old_path = Path(MEDIA) / old.file.name
        res = self.upload(slides=7)
        main = next(p for p in res.data['presentation_files'] if p['language'] == '')
        self.assertEqual((main['version'], main['slide_count']), (2, 7))
        self.assertFalse(old_path.exists())
        self.assertTrue(PresentationFile.objects.filter(resource=self.resource, language='el', version=1).exists())

    def test_delete_language_version(self):
        self.upload()
        self.upload(language='el')
        el = PresentationFile.objects.get(resource=self.resource, language='el')
        path = Path(MEDIA) / el.file.name
        res = self.client.delete(f'{self.url}?language=el')
        self.assertEqual([p['language'] for p in res.data['presentation_files']], [''])
        self.assertFalse(path.exists())
        self.assertEqual(self.client.delete(f'{self.url}?language=el').status_code, 404)

    def test_permissions_and_type(self):
        other = User.objects.create_user('pres_other', password='x')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(other)
        self.assertEqual(self.upload().status_code, 403)
        learner = User.objects.create_user('pres_l', password='x')
        UserProfile.objects.create(user=learner)
        self.client.force_authenticate(learner)
        self.assertEqual(self.upload().status_code, 403)
        self.client.force_authenticate(self.creator)
        self.resource.type = 'pdf'
        self.resource.save()
        self.assertEqual(self.upload().data['code'], 'not_presentation')

    def test_download_flag_saved_through_resource_patch(self):
        url = reverse('authoring-resource-detail', kwargs={
            'pk': self.course.id, 'module_pk': self.module.id, 'lesson_pk': self.activity.id,
            'resource_pk': self.resource.id})
        res = self.client.patch(url, {'presentation_downloadable': True}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data['presentation_downloadable'])

    def test_copied_module_gets_its_own_deck_file(self):
        self.upload()
        new_module = copy_module(self.module, self.course, order=2)
        copy = PresentationFile.objects.get(resource__activity__module=new_module)
        original = PresentationFile.objects.get(resource=self.resource)
        self.assertNotEqual(copy.file.name, original.file.name)
        self.upload(slides=9)                                        # replace in the original
        self.assertTrue((Path(MEDIA) / copy.file.name).exists())
        self.assertEqual((copy.slide_count, copy.title, copy.version), (original.slide_count, original.title, 1))


class CaddyConfigTests(APITestCase):
    def test_caddy_caps_presentation_uploads_and_sets_file_headers(self):
        from django.conf import settings
        text = (Path(settings.BASE_DIR).parent / 'Caddyfile').read_text(encoding='utf-8')
        self.assertIn('path_regexp ^/api/authoring/.*/presentation/$', text)
        self.assertIn('header /media/presentations/*', text)
        self.assertIn('application/vnd.openxmlformats-officedocument.presentationml.presentation', text)
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_presentation_api -v 2`
  - Expected: `NoReverseMatch: 'authoring-resource-presentation'`.

- [ ] **Step 3: Implement.** `backend/hub/views/authoring_presentation.py`:

```python
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub import presentation
from hub.models import CourseEditHistory, PresentationFile, Resource
from hub.serializers import ResourceSerializer
from hub.translation import LANGUAGE_NAMES
from hub.translation_sync import resync_resource

from .permissions import IsContentCreator, can_edit_course


def _error(code, detail):
    return Response({'code': code, 'detail': detail}, status=status.HTTP_400_BAD_REQUEST)


class AuthoringPresentationView(APIView):
    """POST (multipart: file, language) — upload or replace a presentation
    resource's .pptx for one language ('' = main deck). DELETE ?language= —
    remove it. Replaced and removed files are deleted from disk."""

    permission_classes = [IsContentCreator]

    def _resource(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource = (
            Resource.objects.select_related('activity__module__course')
            .filter(pk=resource_pk, activity_id=lesson_pk,
                    activity__module_id=module_pk, activity__module__course_id=pk)
            .first()
        )
        if resource is None:
            return None, Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_edit_course(request.user, resource.activity.module.course):
            return None, Response({'detail': 'You cannot edit this course.'}, status=status.HTTP_403_FORBIDDEN)
        if resource.type != Resource.Type.PRESENTATION:
            return None, _error('not_presentation', 'This resource is not a presentation.')
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
        if upload.size > settings.PRESENTATION_MAX_MB * 1024 * 1024:
            return _error('too_large', f'The file is larger than {settings.PRESENTATION_MAX_MB} MB.')
        try:
            info = presentation.check_pptx(upload)
        except presentation.PresentationError as exc:
            return _error(exc.code, exc.detail)

        first_main = not language and not resource.presentation_files.filter(language='').exists()
        deck = resource.presentation_files.filter(language=language).first()
        old_name = None
        if deck is None:
            deck = PresentationFile(resource=resource, language=language)
        else:
            old_name = deck.file.name
            deck.version += 1
        deck.file.save('deck.pptx', upload, save=False)
        deck.title = info.title or Path(upload.name).stem[:255]
        deck.slide_count = info.slide_count
        deck.size_bytes = upload.size
        deck.uploaded_by = request.user
        deck.save()
        if old_name and old_name != deck.file.name:
            default_storage.delete(old_name)

        if first_main and not resource.title and deck.title:
            resource.title = deck.title[:200]
            resource.save(update_fields=['title'])
            resync_resource(resource)
        CourseEditHistory.objects.create(
            course=resource.activity.module.course, editor=request.user,
            changes={'presentation_uploaded': {
                'resource': resource.id, 'language': language or 'main',
                'slides': deck.slide_count, 'version': deck.version,
            }},
        )
        return Response(ResourceSerializer(resource).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource, failure = self._resource(request, pk, module_pk, lesson_pk, resource_pk)
        if failure:
            return failure
        deck = resource.presentation_files.filter(language=request.query_params.get('language', '')).first()
        if deck is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        deck.delete()   # the post_delete signal removes the file
        return Response(ResourceSerializer(resource).data)
```

`backend/hub/urls.py`: add `from .views.authoring_presentation import AuthoringPresentationView` next to the `authoring_h5p` import. After `authoring-resource-h5p`, add:

```python
    path('authoring/courses/<int:pk>/modules/<int:module_pk>/lessons/<int:lesson_pk>/resources/<int:resource_pk>/presentation/', AuthoringPresentationView.as_view(), name='authoring-resource-presentation'),
```

`backend/hub/serializers/content.py`, `ResourceSerializer`:
- add `presentation_files = serializers.SerializerMethodField()`;
- add `'presentation_downloadable', 'presentation_files'` to `fields`, after `'h5p_packages'`;
- add:

```python
    def get_presentation_files(self, obj):
        if obj.type != Resource.Type.PRESENTATION:
            return []
        return [
            {
                'id': d.id, 'language': d.language, 'title': d.title, 'slide_count': d.slide_count,
                'size_bytes': d.size_bytes, 'version': d.version, 'path': d.media_path,
                'over_viewer_limit': d.over_viewer_limit, 'uploaded_at': d.uploaded_at,
            }
            for d in obj.presentation_files.all()
        ]
```

`backend/hub/views/authoring_module_library.py`, in `copy_module`: after the H5P-package loop, inside `for resource in …`, add:

```python
            # Decks are deleted on replace, so every copy owns its file.
            for deck in resource.presentation_files.all():
                _copy_deck(deck, new_resource)
```

and this helper at module level, above `copy_module`:

```python
def _copy_deck(deck, new_resource):
    from django.core.files.base import File

    from hub.models import PresentationFile
    try:
        source = deck.file.open('rb')
    except (FileNotFoundError, OSError):
        return   # file missing on disk: the copy starts without that deck
    with source:
        clone = PresentationFile(
            resource=new_resource, language=deck.language, title=deck.title,
            slide_count=deck.slide_count, size_bytes=deck.size_bytes, uploaded_by=deck.uploaded_by,
        )
        clone.file.save('deck.pptx', File(source), save=False)
        clone.save()
```

`Caddyfile`, in the `handle /api/*` block after the H5P matcher, add:

```
        # Presentation uploads: refuse anything over the 100 MB limit before it is sent on.
        @presentationUpload path_regexp ^/api/authoring/.*/presentation/$
        request_body @presentationUpload {
            max_size 105MB
        }
```

In `handle /media/*`, after the `header /media/h5p/*` block, add:

```
        # .pptx decks: fetched by Microsoft's Office viewer; served as PowerPoint, never sniffed.
        header /media/presentations/* {
            Content-Type "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            X-Content-Type-Options "nosniff"
            defer
        }
```

Docker isn't available locally, so the Caddyfile can't be validated with `caddy validate` here. Record a ledger ruling, and include "`docker compose restart caddy` after deploying" in the Task 9 rollout note.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_presentation_api hub.tests.test_h5p -v 2`
  - Expected: all pass, including the existing H5P tests.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/views/authoring_presentation.py hub/urls.py hub/serializers/content.py hub/views/authoring_module_library.py ../Caddyfile hub/tests/test_presentation_api.py
git commit -m "feat: presentation upload API, authoring payload, module copies, Caddy limits"
git push
```

---

### Task 4: Learner payload

**Files:**
- Modify: `backend/hub/serializers/content.py` (`ResourceLearnSerializer`)
- Test: `backend/hub/tests/test_presentation_learner.py`

**Interfaces — Produces:** `ResourceLearnSerializer.presentation` is `None`, or:

```
{url, title, slides, language, size_bytes, over_viewer_limit, downloadable}
```

- `url` is absolute when a request is in the context, otherwise site-relative.
- `downloadable` = `resource.presentation_downloadable or over_viewer_limit`.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_presentation_learner.py`:

```python
import tempfile

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import RequestFactory, TestCase, override_settings

from hub.models import PresentationFile, UserProfile
from hub.serializers.content import ResourceLearnSerializer

from .test_presentation_models import make_presentation_resource

MEDIA = tempfile.mkdtemp(prefix='aidea-pres-learn-')


@override_settings(MEDIA_ROOT=MEDIA, MEDIA_URL='/media/')
class LearnerPresentationTests(TestCase):
    def setUp(self):
        *_, self.resource = make_presentation_resource()
        self.user = User.objects.create_user('pres_learner', password='x')
        UserProfile.objects.create(user=self.user, language='el')

    def add(self, language, size=1000, title='Deck'):
        deck = PresentationFile(resource=self.resource, language=language, title=title, slide_count=5, size_bytes=size)
        deck.file.save('d.pptx', ContentFile(b'PK'), save=False)
        deck.save()
        return deck

    def payload(self):
        request = RequestFactory().get('/')          # host 'testserver' (allowed in tests)
        request.user = self.user
        return ResourceLearnSerializer(self.resource, context={'request': request}).data['presentation']

    def test_viewers_language_wins(self):
        self.add('')
        el = self.add('el', title='Διαφάνειες')
        p = self.payload()
        self.assertEqual((p['language'], p['title'], p['slides']), ('el', 'Διαφάνειες', 5))
        self.assertEqual(p['url'], f'http://testserver/media/{el.file.name}')

    def test_falls_back_to_main_deck(self):
        self.add('')
        self.add('fr')
        self.assertEqual(self.payload()['language'], '')

    def test_no_deck_gives_null(self):
        self.add('fr')
        self.assertIsNone(self.payload())

    def test_download_flag_and_forced_download_over_limit(self):
        self.add('')
        self.assertFalse(self.payload()['downloadable'])
        self.resource.presentation_downloadable = True
        self.resource.save()
        self.assertTrue(self.payload()['downloadable'])
        self.resource.presentation_downloadable = False
        self.resource.save()
        PresentationFile.objects.filter(resource=self.resource).update(size_bytes=50 * 1024 * 1024)
        p = self.payload()
        self.assertEqual((p['over_viewer_limit'], p['downloadable']), (True, True))

    def test_other_types_have_no_presentation(self):
        self.resource.type = 'pdf'
        self.resource.save()
        self.assertIsNone(self.payload())
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_presentation_learner -v 2`
  - Expected: `KeyError: 'presentation'`.

- [ ] **Step 3: Implement.** In `ResourceLearnSerializer`:
- add `presentation = serializers.SerializerMethodField()`;
- add `'presentation'` to `fields`, after `'h5p'`;
- add:

```python
    def get_presentation(self, obj):
        """The deck to show: the viewer's language version, else the main deck."""
        if obj.type != Resource.Type.PRESENTATION:
            return None
        decks = {d.language: d for d in obj.presentation_files.all()}
        deck = decks.get(viewer_language(self.context)) or decks.get('')
        if deck is None:
            return None
        request = self.context.get('request')
        url = request.build_absolute_uri(deck.media_path) if request else deck.media_path
        return {
            'url': url, 'title': deck.title, 'slides': deck.slide_count, 'language': deck.language,
            'size_bytes': deck.size_bytes, 'over_viewer_limit': deck.over_viewer_limit,
            'downloadable': obj.presentation_downloadable or deck.over_viewer_limit,
        }
```

Check that the activity-page queries prefetch resources. If `LessonLearnDetailSerializer` prefetches `h5p_packages`, add `presentation_files` the same way: `grep -n "h5p_packages" hub/views/learner.py hub/serializers/*.py`. If nothing is prefetched for H5P either, leave it.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_presentation_learner hub.tests.test_h5p -v 2`
  - Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/serializers/content.py hub/tests/test_presentation_learner.py
git commit -m "feat: presentation deck in the learner payload (language fallback, downloads)"
git push
```

---

### Task 5: Analytics (notes, timeline detail, Excel)

**Files:**
- Modify: `backend/analytics/learning.py`, `backend/analytics/workbook.py`
- Test: `backend/analytics/tests/test_presentation_analytics.py`

**Interfaces — Produces:**
- `resource_notes(cd, presentation_resource) -> {'downloaded': int}`.
- `CourseData.resource_detail(uid, r)['presentation_downloaded']`: the count for presentations, else None.
- Workbook `HEADERS['Resources']` ends with the new column `'Presentation downloaded'`.

- [ ] **Step 1: Write the failing tests.** `backend/analytics/tests/test_presentation_analytics.py`:

```python
from django.test import TestCase

from analytics.learning import CourseData, content_tree, learner_timeline
from analytics.workbook import build_learning_workbook
from hub.models import Activity, Course, LearningEvent, LearningPillar, Module, Resource, UserProfile

from .fixtures import NOW, enroll, make_user
from .test_workbook import by_learner


class PresentationAnalyticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        creator = make_user('pa_cc', UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-pa', order=1)
        cls.course = Course.objects.create(title='Decks', pillar=pillar, level='beginner', duration_hours=1,
                                           is_published=True, created_by=creator)
        module = Module.objects.create(course=cls.course, title='M', order=1)
        activity = Activity.objects.create(module=module, title='Slides', order=1)
        cls.r = Resource.objects.create(activity=activity, type='presentation', order=1, title='Week 1')
        cls.ann, cls.bob = make_user('ann', first='Ann'), make_user('bob', first='Bob')
        for u in (cls.ann, cls.bob):
            enroll(u, cls.course)
        LearningEvent.objects.create(user=cls.ann, course=cls.course, resource=cls.r,
                                     event_type='presentation_download', occurred_at=NOW, data={})

    def test_notes_count_downloads(self):
        notes = content_tree(CourseData(self.course, now=NOW))['modules'][0]['activities'][0]['resources'][0]['notes']
        self.assertEqual(notes, {'downloaded': 1})

    def test_timeline_detail(self):
        cd = CourseData(self.course, now=NOW)
        res = learner_timeline(cd, self.ann.id)['modules'][0]['activities'][0]['resources'][0]
        self.assertEqual(res['presentation_downloaded'], 1)

    def test_resources_sheet_column(self):
        wb = build_learning_workbook([self.course], now=NOW)
        [row] = by_learner(wb['Resources'], 'Ann')
        self.assertEqual(row['Presentation downloaded'], 1)
        self.assertEqual(row['Type'], 'presentation')
```

Before running, check how `LearningEvent` rows are created in `analytics/tests/fixtures.py` (look for an event helper, e.g. `grep -n "LearningEvent" analytics/tests/fixtures.py`). If the model needs more fields (e.g. `event_key`, `visit`), use the fixture helper instead of `objects.create`, with the same `event_type` and resource.

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test analytics.tests.test_presentation_analytics -v 2`
  - Expected: failures (notes `{}`, no `presentation_downloaded` key, no column).

- [ ] **Step 3: Implement.**

`analytics/learning.py`, `resource_notes`: before `if kind == 'assignment':`, add:

```python
    if kind == 'presentation':
        return {'downloaded': sum(1 for uid in uids if cd.events_for(uid, resource.id, 'presentation_download'))}
```

`resource_detail`: after `'pdf_downloaded'`, add:

```python
            'presentation_downloaded': count('presentation_download') if kind == 'presentation' else None,
```

`analytics/workbook.py`:
- add `'Presentation downloaded'` as the last entry of `HEADERS['Resources']`;
- in `_resources`, after `blank(d['assignment_status'])`, add `, blank(d['presentation_downloaded'])`.

Run `"$UV" run manage.py test analytics`. If an existing workbook test compares the full Resources header list or a row's length, add the new column to its expectation and record a ruling.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test analytics -v 2`
  - Expected: all pass.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add analytics
git commit -m "feat: presentation downloads in analytics, timeline and Excel"
git push
```

---

### Task 6: Frontend helpers and tracking (viewer URL, private hosts, frame focus)

**Files:**
- Create:
  - `frontend/src/lib/presentation.js` and `presentation.test.js`
  - `frontend/src/lib/tracking/frameFocus.js` and `frameFocus.test.js`
- Modify:
  - `frontend/src/lib/tracking/tracker.js` (`attending`)
  - `frontend/src/lib/tracking/TrackingContext.js`
  - `frontend/src/api/client.js` (export `API_BASE`)

**Interfaces — Produces:**
- `officeViewerUrl(fileUrl: string) -> string`.
- `isPrivateHost(url: string) -> boolean`: true for development or private hosts and for unparseable URLs.
- `absoluteUrl(url: string, base: string) -> string`.
- `PRESENTATION_FOCUS_MS = 300000`.
- `watchFrameFocus(frame, onChange, opts?) -> stop()`, where `opts = {win, doc, capMs, setTimer, clearTimer}`.
- The tracker API gains `attending(resourceId, on)`; `useResourceTracking(id)` gains `attending(on)`.
- `API_BASE`, exported from `api/client.js`.

- [ ] **Step 1: Write the failing tests.**

`frontend/src/lib/presentation.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { absoluteUrl, isPrivateHost, officeViewerUrl } from './presentation.js'

test('office viewer url encodes the file url', () => {
  assert.equal(
    officeViewerUrl('https://aidea-hub.eu/media/presentations/3/ab.pptx?x=1&y=2'),
    'https://view.officeapps.live.com/op/embed.aspx?src=https%3A%2F%2Faidea-hub.eu%2Fmedia%2Fpresentations%2F3%2Fab.pptx%3Fx%3D1%26y%3D2',
  )
})

test('private and development hosts', () => {
  for (const url of ['http://localhost:8000/media/a.pptx', 'http://api.localhost/a', 'http://box.local/a',
    'http://127.0.0.1/a', 'http://10.1.2.3/a', 'http://192.168.0.5/a', 'http://172.16.0.1/a',
    'http://172.31.255.1/a', 'http://0.0.0.0/a', 'http://[::1]/a', 'not a url']) {
    assert.equal(isPrivateHost(url), true, url)
  }
  for (const url of ['https://aidea-hub.eu/media/a.pptx', 'http://172.32.0.1/a', 'http://11.0.0.1/a']) {
    assert.equal(isPrivateHost(url), false, url)
  }
})

test('absolute url resolves site-relative paths against the API origin', () => {
  assert.equal(absoluteUrl('/media/p/a.pptx', 'https://aidea-hub.eu/api'), 'https://aidea-hub.eu/media/p/a.pptx')
  assert.equal(absoluteUrl('https://cdn.example/a.pptx', 'https://aidea-hub.eu/api'), 'https://cdn.example/a.pptx')
})
```

`frontend/src/lib/tracking/frameFocus.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PRESENTATION_FOCUS_MS, watchFrameFocus } from './frameFocus.js'

function fakeClock() {
  let now = 0
  let id = 0
  const timers = new Map()
  return {
    setTimer: (fn, ms) => { id += 1; timers.set(id, { fn, at: now + ms }); return id },
    clearTimer: (t) => { timers.delete(t) },
    advance(ms) {
      now += ms
      for (const [key, t] of [...timers].sort((a, b) => a[1].at - b[1].at)) {
        if (t.at <= now && timers.has(key)) { timers.delete(key); t.fn() }
      }
    },
  }
}

function setup() {
  const win = new EventTarget()
  const doc = { activeElement: null }
  const frame = { name: 'deck' }
  const clock = fakeClock()
  const changes = []
  const stop = watchFrameFocus(frame, (on) => changes.push(on), { win, doc, ...clock })
  return { win, doc, frame, clock, changes, stop }
}

test('focus entering the frame counts until focus returns', () => {
  const s = setup()
  s.doc.activeElement = s.frame
  s.win.dispatchEvent(new Event('blur'))
  s.clock.advance(0)
  assert.deepEqual(s.changes, [true])
  s.win.dispatchEvent(new Event('focus'))
  assert.deepEqual(s.changes, [true, false])
})

test('another iframe taking focus does not count', () => {
  const s = setup()
  s.doc.activeElement = { name: 'youtube' }
  s.win.dispatchEvent(new Event('blur'))
  s.clock.advance(0)
  assert.deepEqual(s.changes, [])
})

test('counting stops at the cap', () => {
  const s = setup()
  s.doc.activeElement = s.frame
  s.win.dispatchEvent(new Event('blur'))
  s.clock.advance(0)
  s.clock.advance(PRESENTATION_FOCUS_MS - 1)
  assert.deepEqual(s.changes, [true])
  s.clock.advance(1)
  assert.deepEqual(s.changes, [true, false])
  assert.equal(PRESENTATION_FOCUS_MS, 300000)
})

test('stop clears listeners and reports not attending', () => {
  const s = setup()
  s.doc.activeElement = s.frame
  s.win.dispatchEvent(new Event('blur'))
  s.clock.advance(0)
  s.stop()
  assert.deepEqual(s.changes, [true, false])
  s.win.dispatchEvent(new Event('blur'))
  s.clock.advance(0)
  assert.deepEqual(s.changes, [true, false])
})
```

Run `npm test` from `frontend/`. Expected: `ERR_MODULE_NOT_FOUND` for both modules.

- [ ] **Step 2: Implement.**

`frontend/src/lib/presentation.js`:

```js
// Presentation (.pptx) resources are played by Microsoft's Office viewer,
// which fetches the file itself — so it must be on a public address.

const VIEWER = 'https://view.officeapps.live.com/op/embed.aspx?src='

export const officeViewerUrl = (fileUrl) => VIEWER + encodeURIComponent(fileUrl)

export function absoluteUrl(url, base) {
  return new URL(url, base).href
}

const PRIVATE = [
  /^localhost$/, /\.localhost$/, /\.local$/, /^127\./, /^10\./, /^192\.168\./,
  /^172\.(1[6-9]|2\d|3[01])\./, /^0\.0\.0\.0$/, /^\[?::1\]?$/,
]

/** True when Microsoft's servers could not fetch this address (development). */
export function isPrivateHost(url) {
  let host
  try {
    host = new URL(url).hostname
  } catch {
    return true
  }
  return PRIVATE.some(re => re.test(host))
}
```

`frontend/src/lib/tracking/frameFocus.js`:

```js
// Clicks inside a cross-origin frame (Microsoft's slideshow viewer) never
// reach our page, so "the learner is using the slideshow" is read from focus:
// when the window loses focus to this frame, it counts as attending, until
// focus comes back or PRESENTATION_FOCUS_MS passes (a deck left open on screen
// must not count forever).

export const PRESENTATION_FOCUS_MS = 5 * 60 * 1000

export function watchFrameFocus(frame, onChange, {
  win = window, doc = document, capMs = PRESENTATION_FOCUS_MS,
  setTimer = setTimeout, clearTimer = clearTimeout,
} = {}) {
  let attending = false
  let capTimer = null
  let checkTimer = null
  const set = (on) => {
    if (on !== attending) { attending = on; onChange(on) }
  }
  const clearCap = () => {
    if (capTimer != null) { clearTimer(capTimer); capTimer = null }
  }
  const onBlur = () => {
    // activeElement moves to the iframe just after the window's blur event.
    checkTimer = setTimer(() => {
      checkTimer = null
      if (doc.activeElement !== frame) return
      set(true)
      clearCap()
      capTimer = setTimer(() => { capTimer = null; set(false) }, capMs)
    }, 0)
  }
  const onFocus = () => { clearCap(); set(false) }
  win.addEventListener('blur', onBlur)
  win.addEventListener('focus', onFocus)
  return () => {
    win.removeEventListener('blur', onBlur)
    win.removeEventListener('focus', onFocus)
    if (checkTimer != null) clearTimer(checkTimer)
    clearCap()
    set(false)
  }
}
```

`frontend/src/lib/tracking/tracker.js`: in `const api = { … }`, add:

```js
    // A presentation frame has focus: credited like a playing video (see frameFocus.js).
    attending: (resourceId, on) => { if (!stopped) setPlaying(resourceId, on) },
```

`frontend/src/lib/tracking/TrackingContext.js`:
- set `NOOP` to `{ event() {}, completed() {}, video() {}, attending() {} }`;
- in `useResourceTracking`, add `attending: (on) => api.attending(resourceId, on),` to the returned object.

`frontend/src/api/client.js`: after `const BASE = …`, add `export const API_BASE = BASE`.

Run `npm test`. Expected: all pass. Run `npm run lint`. Expected: clean.

- [ ] **Step 3: Commit.**

```bash
git add frontend/src/lib frontend/src/api/client.js
git commit -m "feat: presentation viewer helpers and focus-based active time"
git push
```

---

### Task 7: Author panel and editor wiring

**Files:**
- Create:
  - `frontend/src/components/lesson/PresentationFrame.jsx` and `.css` (shared with Task 8)
  - `frontend/src/components/authoring/PresentationPanel.jsx` and `.css`
- Modify:
  - `frontend/src/components/authoring/ResourceEditor.jsx`
  - `frontend/src/pages/ModuleEditorPage.jsx` and `.css`
  - `frontend/src/components/learner/resourceMeta.js`

**Interfaces:**
- **Consumes:** Task 3's API and `presentation_files`; Task 6's helpers and `API_BASE`.
- **Produces:** `<PresentationFrame url title onFocusChange? />`.
  - It shows the Office viewer in a 16:9 frame with a "Open full screen" button. On private hosts it shows the notice instead.
  - It calls `onFocusChange(on)` from `watchFrameFocus`.

- [ ] **Step 1: The shared frame.** `frontend/src/components/lesson/PresentationFrame.jsx`:

```jsx
import { useEffect, useRef } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { Maximize2 } from 'lucide-react'
import { API_BASE } from '../../api/client'
import { absoluteUrl, isPrivateHost, officeViewerUrl } from '../../lib/presentation'
import { watchFrameFocus } from '../../lib/tracking/frameFocus'
import './PresentationFrame.css'

/** A .pptx played by Microsoft's Office viewer (16:9), or — on development
 *  hosts Microsoft cannot reach — a notice. */
export default function PresentationFrame({ url, title, onFocusChange }) {
  const { t } = useTranslation()
  const frameRef = useRef(null)
  const fileUrl = absoluteUrl(url, API_BASE)
  const local = isPrivateHost(fileUrl)

  useEffect(() => {
    if (local || !onFocusChange || !frameRef.current) return undefined
    return watchFrameFocus(frameRef.current, onFocusChange)
  }, [local, onFocusChange])

  if (local) {
    return <p className="pres-notice">{t('lesson.presentation.livePreviewOnly')}</p>
  }
  return (
    <div className="pres-frame">
      <div className="pres-wrap">
        <iframe ref={frameRef} src={officeViewerUrl(fileUrl)} title={t('lesson.presentation.frameTitle', { title })}
          allowFullScreen />
      </div>
      <button type="button" className="pres-fullscreen" onClick={() => frameRef.current?.requestFullscreen?.()}>
        <Maximize2 size={14} /> {t('lesson.presentation.fullscreen')}
      </button>
    </div>
  )
}

PresentationFrame.propTypes = {
  url: PropTypes.string.isRequired,
  title: PropTypes.string,
  onFocusChange: PropTypes.func,
}
```

`frontend/src/components/lesson/PresentationFrame.css`:

```css
.pres-frame { display: flex; flex-direction: column; gap: 0.5rem; }
.pres-wrap { position: relative; width: 100%; aspect-ratio: 16 / 9; background: #111; border-radius: var(--radius); overflow: hidden; }
.pres-wrap iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
.pres-fullscreen {
  align-self: flex-start; display: inline-flex; align-items: center; gap: 0.35rem;
  background: none; border: 1px solid var(--color-border); border-radius: 8px;
  padding: 0.35rem 0.7rem; font-size: 0.85rem; color: inherit; cursor: pointer;
}
.pres-notice {
  border: 1px dashed var(--color-border); border-radius: var(--radius);
  padding: 1rem; margin: 0; color: var(--color-text-muted); font-size: 0.9rem;
}
```

- [ ] **Step 2: The author panel.** `frontend/src/components/authoring/PresentationPanel.jsx`. Model it on `H5PPanel.jsx`, using the same props: `resource`, `uploadUrl`, `locked`, `onChange`, `onRefresh`.

```jsx
import { useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Eye, EyeOff, Trash2, Upload } from 'lucide-react'
import client from '../../api/client'
import { LANGUAGES } from '../../i18n'
import PresentationFrame from '../lesson/PresentationFrame'
import './PresentationPanel.css'

const mb = (bytes) => (bytes / (1024 * 1024)).toFixed(1)
const languageLabel = (code) => LANGUAGES.find(l => l.code === code)?.label ?? code

/** Presentation resource: main .pptx, optional language versions, download
 *  setting and an in-page preview. */
export default function PresentationPanel({ resource, uploadUrl, locked, onChange, onRefresh }) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(false)
  const [newLang, setNewLang] = useState('')
  const decks = resource.presentation_files ?? []
  const main = decks.find(d => d.language === '')
  const versions = decks.filter(d => d.language !== '')
  const free = LANGUAGES.filter(l => !versions.some(v => v.language === l.code))

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
      setError(t(`authoring.presentation.errors.${code}`, { defaultValue: t('authoring.presentation.errors.generic') }))
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
      setError(t('authoring.presentation.errors.generic'))
    }
  }

  const fileButton = (language, label) => (
    <label className="lesson-upload-btn">
      <Upload size={14} />
      {busy === (language || 'main') ? t('authoring.presentation.uploading') : label}
      <input type="file" hidden accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
        disabled={Boolean(busy)} onChange={(e) => { upload(e.target.files?.[0], language); e.target.value = '' }} />
    </label>
  )

  const meta = (d) => `${t('authoring.presentation.slides', { count: d.slide_count })} · ${mb(d.size_bytes)} MB · ${t('authoring.presentation.version', { n: d.version })}`

  return (
    <div className="pres-panel">
      <p className="pres-hint">{t('authoring.presentation.formatHint')}</p>
      {main ? (
        <div className="pres-deck">
          <div className="pres-deck-info">
            <strong>{main.title}</strong>
            <span className="pres-deck-meta">{meta(main)}</span>
          </div>
          <div className="pres-deck-actions">
            <button type="button" className="lesson-upload-btn" onClick={() => setPreview(p => !p)}>
              {preview ? <EyeOff size={14} /> : <Eye size={14} />} {preview ? t('authoring.presentation.hidePreview') : t('authoring.presentation.preview')}
            </button>
            {!locked && fileButton('', t('authoring.presentation.replace'))}
          </div>
        </div>
      ) : (
        !locked && fileButton('', t('authoring.presentation.upload'))
      )}
      {main?.over_viewer_limit && (
        <p className="pres-warning"><AlertTriangle size={14} /> {t('authoring.presentation.overLimit')}</p>
      )}
      {preview && main && <PresentationFrame key={`${main.id}-${main.version}`} url={main.path} title={main.title} />}

      {main && (
        <div className="pres-versions">
          <p className="lesson-field-label">{t('authoring.presentation.languageVersions')}</p>
          <p className="pres-hint">{t('authoring.presentation.languageVersionsHint')}</p>
          {versions.map(v => (
            <div key={v.language} className="pres-version-row">
              <span className="pres-version-lang">{languageLabel(v.language)}</span>
              <span className="pres-deck-meta">{v.title} · {meta(v)}</span>
              {v.over_viewer_limit && <AlertTriangle size={14} className="pres-warning-icon" aria-label={t('authoring.presentation.overLimit')} />}
              {!locked && fileButton(v.language, t('authoring.presentation.replace'))}
              {!locked && (
                <button type="button" className="me-media-btn me-media-btn--danger" onClick={() => remove(v.language)}
                  title={t('authoring.presentation.remove')}>
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
          {!locked && free.length > 0 && (
            <div className="pres-version-row">
              <select value={newLang} onChange={(e) => setNewLang(e.target.value)}>
                <option value="">{t('authoring.presentation.addLanguage')}</option>
                {free.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
              </select>
              {newLang && fileButton(newLang, t('authoring.presentation.upload'))}
            </div>
          )}
        </div>
      )}

      <label className="resource-editor-required">
        <input type="checkbox" checked={Boolean(resource.presentation_downloadable)} disabled={locked}
          onChange={(e) => onChange('presentation_downloadable', e.target.checked)} />
        {t('authoring.presentation.downloadable')}
      </label>
      <p className="pres-hint">{t('authoring.presentation.downloadableHint')}</p>
      {error && <p className="media-item-error">{error}</p>}
    </div>
  )
}

PresentationPanel.propTypes = {
  resource: PropTypes.shape({
    presentation_files: PropTypes.array,
    presentation_downloadable: PropTypes.bool,
  }).isRequired,
  uploadUrl: PropTypes.string.isRequired,
  locked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  onRefresh: PropTypes.func.isRequired,
}
```

`frontend/src/components/authoring/PresentationPanel.css`:

```css
.pres-panel { display: flex; flex-direction: column; gap: 0.6rem; }
.pres-deck { display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.pres-deck-info { display: flex; flex-direction: column; gap: 0.15rem; }
.pres-deck-meta, .pres-hint { color: var(--color-text-muted); font-size: 0.8rem; margin: 0; }
.pres-deck-actions { display: flex; gap: 0.5rem; align-items: center; }
.pres-warning { display: flex; align-items: flex-start; gap: 0.4rem; margin: 0; font-size: 0.85rem; color: #b45309; }
.pres-warning-icon { color: #b45309; }
.pres-versions { display: flex; flex-direction: column; gap: 0.4rem; }
.pres-version-row { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.pres-version-lang { font-weight: 500; min-width: 6rem; }
```

- [ ] **Step 3: Wire it into the editor.**
- `ResourceEditor.jsx`:
  - import `PresentationPanel`;
  - add the prop `presentationUrl = ''` (and `presentationUrl: PropTypes.string` to propTypes);
  - after the H5P block, render:

```jsx
        {resource.type === 'presentation' && !translating && (
          <PresentationPanel resource={resource} uploadUrl={presentationUrl} locked={structureLocked}
            onChange={onChange} onRefresh={onRefresh} />
        )}
```

- `ModuleEditorPage.jsx`:
  - add `Presentation` to the lucide import;
  - add `{ type: 'presentation', Icon: Presentation, color: 'orange' }` to `RESOURCE_TYPES`, after `h5p`;
  - pass `presentationUrl={`${resourceUrl(resource.id)}presentation/`}` to `<ResourceEditor>`, next to `uploadUrl`;
  - in `validateResource`, add:

```js
  if (resource.type === 'presentation' && !(resource.presentation_files ?? []).some(p => p.language === '')) {
    return t('authoring.presentation.fileRequiredError')
  }
```

- `ModuleEditorPage.css`: next to the `--teal` variants, add:

```css
.me-type-btn--orange { background: #fff7ed; color: #ea580c; border-color: #fed7aa; }
.lesson-type-icon--orange { color: #ea580c; }
.lesson-editor-icon-wrap--orange { background: #fff7ed; color: #ea580c; }
```

- `resourceMeta.js`: import `Presentation` from lucide and add `presentation: Presentation` to `TYPE_ICONS`. Add to `resourceShape`:

```js
  presentation: PropTypes.shape({
    url:               PropTypes.string,
    title:             PropTypes.string,
    slides:            PropTypes.number,
    language:          PropTypes.string,
    size_bytes:        PropTypes.number,
    over_viewer_limit: PropTypes.bool,
    downloadable:      PropTypes.bool,
  }),
```

Also check that the H5P resource-save path ignores the read-only `presentation_files` when the editor saves a resource: run `grep -n "h5p_packages" src/pages/ModuleEditorPage.jsx`. If the editor strips `h5p_packages` before PATCHing, strip `presentation_files` the same way. If it sends the whole object, DRF ignores read-only fields; no change is needed.

Locale strings come in Task 8. Until then the new keys show as raw key text, which is acceptable for this commit.

- [ ] **Step 4: Verify.** From `frontend/`: `npm run lint && npm test && VITE_API_URL=http://localhost:8000/api npm run build`. Expected: clean.

- [ ] **Step 5: Commit.**

```bash
git add frontend/src
git commit -m "feat: presentation author panel and editor wiring"
git push
```

---

### Task 8: Learner view, analytics UI, privacy, locales

**Files:**
- Modify:
  - `frontend/src/components/learner/ResourceView.jsx`
  - `frontend/src/components/analytics/ContentTree.jsx`, `LearnerTimeline.jsx`
  - `frontend/src/pages/PrivacyPage.jsx`
  - `frontend/src/locales/*.json` (9 files)

**Interfaces — Consumes:** Task 4's `resource.presentation`; Task 7's `PresentationFrame`; Task 6's `useResourceTracking(id).attending`.

- [ ] **Step 1: The learner body.** In `ResourceView.jsx`, import `PresentationFrame` from `'../lesson/PresentationFrame'` and `Download` from lucide. Add:

```jsx
PresentationBody.propTypes = { resource: resourceShape.isRequired }
function PresentationBody({ resource }) {
  const { t } = useTranslation()
  const track = useResourceTracking(resource.id)
  const deck = resource.presentation
  const onFocusChange = useCallback((on) => track.attending(on), [track])
  if (!deck) return <p className="lp-empty">{t('lesson.presentation.missing')}</p>
  const canDownload = deck.downloadable || isPrivateHost(absoluteUrl(deck.url, API_BASE))
  return (
    <div className="lp-presentation">
      <PresentationFrame url={deck.url} title={deck.title || resource.title} onFocusChange={onFocusChange} />
      {canDownload && (
        <a className="media-open-link lp-presentation-download" href={deck.url} download
          onClick={() => track.event('presentation_download', deck.language ? { language: deck.language } : {})}>
          <Download size={14} /> {t('lesson.presentation.download')}
        </a>
      )}
    </div>
  )
}
```

Then:
- add `useCallback` to the React import;
- import `absoluteUrl, isPrivateHost` from `'../../lib/presentation'` and `API_BASE` from `'../../api/client'`;
- in the `switch`, add `case 'presentation': body = <PresentationBody resource={resource} />; break`.

`selfCompletes` already covers the new type ("Mark as done"). Add `.lp-presentation { display: flex; flex-direction: column; gap: 0.6rem; }` to `PresentationFrame.css`.

- [ ] **Step 2: Analytics UI.**
- `ContentTree.jsx` `ResourceNotes`: after the PDF lines, add `if (type === 'presentation' && notes.downloaded) parts.push(t('analytics.course.notes.downloaded', { count: notes.downloaded }))`.
- `LearnerTimeline.jsx` `ResourceDetails`: after the PDF line, add `if (r.presentation_downloaded) bits.push(t('analytics.course.detail.downloaded'))`.

- [ ] **Step 3: Privacy Policy.** In `PrivacyPage.jsx`, insert before `<h2>13. Changes and complaints</h2>` and renumber that heading to `14.`:

```jsx
      <h2>13. Presentations</h2>
      <p>
        Some activities show slide presentations in Microsoft&rsquo;s Office viewer, embedded in the
        page. To play them, your browser loads the viewer from Microsoft, so Microsoft receives your IP
        address and browser details, and Microsoft&rsquo;s servers fetch the presentation file from
        AIDEA. No names or learning records are sent to Microsoft.
      </p>
```

- [ ] **Step 4: Locales (9 languages).** Add these keys; `en` is shown. Write real translations for el, fr, es, it, fi, sv, no and de in each locale's tone, keeping `{{placeholders}}`. Merge into the existing objects with a script that keeps indentation, line endings and the final newline, and that **never overwrites** an existing key.

```json
"lesson": {
  "type": { "presentation": "Presentation" },
  "presentation": {
    "missing": "This presentation has no file yet.",
    "fullscreen": "Open full screen",
    "download": "Download (.pptx)",
    "livePreviewOnly": "The slideshow plays on the live site. Here you can download the file.",
    "frameTitle": "Presentation: {{title}}"
  }
},
"authoring": { "presentation": {
  "upload": "Upload .pptx file", "replace": "Replace", "uploading": "Uploading…",
  "preview": "Preview", "hidePreview": "Hide preview", "remove": "Remove",
  "version": "version {{n}}", "slides": "{{count}} slides",
  "formatHint": "PowerPoint .pptx only, up to 100 MB. From LibreOffice Impress: File → Save As → PowerPoint (.pptx).",
  "languageVersions": "Language versions",
  "languageVersionsHint": "Optional: a translated .pptx for learners using that language. Others see the main deck.",
  "addLanguage": "Add language…",
  "downloadable": "Learners can download the file",
  "downloadableHint": "Off: learners can only watch the slideshow.",
  "overLimit": "Over 10 MB — Microsoft's viewer may not play it; check the preview on the live site. Learners will also get a download button.",
  "fileRequiredError": "Upload the .pptx file first.",
  "errors": {
    "generic": "The upload failed. Please try again.",
    "no_file": "Choose a .pptx file.",
    "too_large": "The file is larger than 100 MB. In PowerPoint use File → Compress Media and Compress Pictures, or put videos online and link them.",
    "not_pptx": "This is not a PowerPoint (.pptx) file.",
    "convert_to_pptx": "Save it as .pptx (in Impress: File → Save As → PowerPoint), then upload again.",
    "macros": "Presentations with macros cannot be used. Save it as a normal .pptx.",
    "corrupt": "The file is damaged or could not be read.",
    "no_slides": "This presentation has no slides.",
    "bad_language": "Unknown language.",
    "not_presentation": "This resource is not a presentation."
  }
}}
```

The "100 MB" and "10 MB" in the strings match the defaults. If either setting is changed later, update the strings.

- [ ] **Step 5: Verify.**
  - From `frontend/`: `npm run lint`, `npm test`, `node scripts/check-locales.mjs` and `VITE_API_URL=http://localhost:8000/api npm run build`. Expected: all clean.
  - Manual, locally: create a presentation resource, upload a .pptx (the panel shows title, slide count and size), and open the activity as a learner. Expected: the "plays on the live site" notice with a download link, plus Mark as done.

- [ ] **Step 6: Commit.**

```bash
git add frontend/src
git commit -m "feat: presentation slideshow for learners, analytics notes, privacy section, locales"
git push
```

---

### Task 9: Full verification, docs, rollout note

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md.**
  - Under API endpoints, add `` `POST/DELETE /api/authoring/courses/<id>/modules/<m>/lessons/<a>/resources/<r>/presentation/` — upload (multipart `file`, `language`) or remove a .pptx deck; played in Microsoft's Office viewer (`view.officeapps.live.com`), so the file URL must be public ``.
  - Under the architecture notes, add one line: presentation resources (`hub/presentation.py` checks decks; `PRESENTATION_MAX_MB` / `PRESENTATION_VIEWER_LIMIT_MB` settings).

- [ ] **Step 2: Full verification.**
  - From `backend/`: `"$UV" run ruff check .`, `"$UV" run coverage run manage.py test hub analytics --verbosity=1`, `"$UV" run coverage report --fail-under=70` and `"$UV" run manage.py makemigrations --check --dry-run`.
  - From `frontend/`: `npm run lint && npm test && node scripts/check-locales.mjs && VITE_API_URL=http://localhost:8000/api npm run build`.
  - Expected: all pass, and "No changes detected".

- [ ] **Step 3: Commit.**

```bash
git add CLAUDE.md
git commit -m "docs: presentation resource endpoint and settings"
git push
```

- [ ] **Step 4: Rollout note for the user.** On the VM, with `COMPOSE_FILE` set:

```bash
git pull
docker compose up -d --build backend celery celery-beat frontend
docker compose exec -T backend uv run python manage.py migrate      # 0067_presentation
docker compose restart caddy                                         # Caddyfile changed — restart, not reload
```

Then:
1. Add a presentation resource with a real deck (animations, plus an embedded video).
2. Play it on desktop and on a phone.
3. Upload one 10–100 MB deck. If the viewer plays it, raise `PRESENTATION_VIEWER_LIMIT_MB` in the environment and update the "10 MB" in the `overLimit` string.
