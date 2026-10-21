# Rich Text (Tables, Images) and One-Click Activity Completion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
- Authors can put tables and images inside text resources.
- Rich-text translation keeps that structure.
- Learners complete all non-interactive resources of an activity with one button.

**Architecture:**
- `hub/html_translate.py` translates HTML block by block (lxml), checks each answer, retries, then falls back to plain text. `translate_text` sends HTML through it.
- A new endpoint completes an activity's self-completed resources in one go, recalculating progress once.
- The TinyMCE editor gains the table and image plugins, with an upload handler.
- `HtmlContent` sanitizes to the editor's allowed list.
- The activity page replaces the per-resource "Mark as done" buttons with one activity button.

**Tech Stack:** Django 5 + DRF, lxml (already installed, via python-docx), React 19, TinyMCE 8 (self-hosted), DOMPurify.

**Spec:** `docs/superpowers/specs/2026-10-21-rich-text-and-activity-completion-design.md`

## Global Constraints

- **Allowed rich-text elements** (editor `valid_elements` and learner sanitizer):
  - `p,br,strong/b,em/i,u,h2,h3,ul,ol,li,a[href|target|rel],blockquote`;
  - `table,thead,tbody,tr,th[colspan|rowspan|scope],td[colspan|rowspan],caption`;
  - `img[src|alt|width|height]`.
  - Nothing else; no `style`.
- **Image `src`:**
  - kept only when it is `https:`, site-relative `/media/…`, or `http://localhost`/`http://127.0.0.1` (development uploads);
  - otherwise the `img` is removed when shown.
- **Editor images** upload to `POST /api/authoring/upload/` (existing: png/jpg/jpeg/gif/webp/pdf, ≤ 20 MB; response `{url}`).
- **Translation:**
  - blocks are `p, h2, h3, li, td, th, caption, blockquote` that contain no other block;
  - each block's inner HTML goes to the model with images replaced by `<img data-k="N">` placeholders, so the model never sees an image address;
  - an answer is accepted when its multiset of tags, the order of `href` values and the set of placeholders all match; otherwise retry once, then translate that block's plain text (inline formatting dropped, images kept);
  - `alt` is translated as plain text; `src`, `width` and `height` never change;
  - plain-text (non-HTML) input is translated exactly as before.
- **Self-completed types:** `text`, `image`, `video`, `pdf`, `presentation`, plus `h5p` with `h5p_self_complete`.
  - The bulk endpoint completes every not-yet-completed resource of those types in the activity (required and optional), then recalculates progress **once**.
  - Text resources get `engagement_data = {'scroll_pct': <sent value>}`, as today.
- **Learner UI:**
  - no per-resource "Mark as done" for self-completed types;
  - one "Mark activity as done" button under the activity's resources when at least one such resource is not done; "✓ Completed" when all are done; nothing when the activity has none;
  - the note "Quizzes and assignments are completed when you submit them." shows while the activity also has an unfinished quiz, assignment or scoring H5P.
- **Shared rules:**
  - keep all 9 locales in sync; icons from lucide-react;
  - ESLint ES2020 with the React-compiler purity rule.
- **Runner and git:**
  - from `backend/`, set `UV="/c/Users/Nikos A. Grammatikos/.local/bin/uv.exe"`, then `"$UV" run manage.py test …` and `"$UV" run ruff check hub analytics`;
  - frontend from `frontend/`: `npm test`, `npm run lint`, `node scripts/check-locales.mjs`, `VITE_API_URL=http://localhost:8000/api npm run build`;
  - keep line endings; work on `master`, commit and push per task, with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **An image inside a paragraph** (TinyMCE wraps images in `<p>`): the model must not receive or change its URL, and the image must survive both the success path and the plain-text fallback. Pinned by Task 1 `test_image_inside_paragraph_survives_and_url_never_sent` and `test_fallback_keeps_images`.
2. **The model returning prose around the HTML, or malformed HTML:** treated as a failed check (retry, then fallback), never a crash or a broken page. Pinned by Task 1 `test_unparseable_answer_falls_back`.
3. **An activity whose only resources are a quiz or an assignment:** no activity button. **An activity with text plus an unfinished quiz:** the button completes the text only, and the activity stays incomplete until the quiz is done. Pinned by Task 2 `test_quiz_is_not_completed_by_the_button` and Task 4 `activityCompletion.test.js`.
4. **Clicking the activity button twice** (double click, or two tabs): the second call changes nothing and doesn't trigger a second competency change. Pinned by Task 2 `test_second_call_changes_nothing`.
5. **An image pasted with a `data:` or `javascript:` source,** or from a plain `http://` site: never rendered to learners. Pinned by Task 3 `richText.test.js`.

---

## File Structure

**Backend**
- `hub/html_translate.py` (new): `looks_like_html`, `translate_html`.
- `hub/translation.py`: `_translate_plain`, `_translate_fragment`; `translate_text` sends HTML through `translate_html`.
- `hub/completion.py`: `SELF_COMPLETED_TYPES`, `self_completes(resource)`, `complete_self_completed(user, enrollment, activity, scroll_pct=None)`.
- `hub/views/learner.py`: `ActivityCompleteResourcesView`; `hub/urls.py`.
- Tests: `hub/tests/test_html_translate.py`, `hub/tests/test_activity_complete_resources.py`.

**Frontend**
- `src/lib/richText.js` and `.test.js` (new): `RICH_TEXT_VALID_ELEMENTS`, `SANITIZE_CONFIG`, `isAllowedImageSrc`.
- `src/components/lesson/RichTextEditor.jsx` and `.css`; `src/components/lesson/HtmlContent.jsx`; the rich-html CSS.
- `src/lib/activityCompletion.js` and `.test.js` (new): `selfCompletes`, `activityButtonState`.
- `src/components/learner/ResourceView.jsx` (remove the per-resource footer button); `src/pages/ActivityPage.jsx` and `.css`.
- `src/locales/*.json`.

---

### Task 1: Structure-safe HTML translation

**Files:**
- Create: `backend/hub/html_translate.py`, `backend/hub/tests/test_html_translate.py`
- Modify: `backend/hub/translation.py`

**Interfaces — Produces:**
- `looks_like_html(text) -> bool`.
- `translate_html(html, translate_fragment, translate_plain) -> str`, where both translators are `str -> str`.
- `hub.translation.translate_text(text, source, target)`: unchanged signature. HTML input goes through `translate_html` with the model-backed `_translate_fragment` and `_translate_plain`.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_html_translate.py`:

```python
import re
from unittest import mock

from django.test import SimpleTestCase

from hub.html_translate import looks_like_html, translate_html


def upper_text(fragment):
    """A well-behaved fake model: uppercases the text between tags only."""
    return re.sub(r'>([^<]+)<', lambda m: '>' + m.group(1).upper() + '<', '>' + fragment + '<')[1:-1]


def upper(text):
    return text.upper()


class TranslateHtmlTests(SimpleTestCase):
    def test_looks_like_html(self):
        self.assertTrue(looks_like_html('<p>Hi</p>'))
        self.assertFalse(looks_like_html('Plain text, 3 < 4'))

    def test_table_and_formatting_keep_their_structure(self):
        html = ('<h2>Risks</h2><p>Some <strong>bold</strong> and a <a href="https://x.eu/a">link</a>.</p>'
                '<table><thead><tr><th>Name</th><th>Level</th></tr></thead>'
                '<tbody><tr><td colspan="2">Bias</td></tr></tbody></table>')
        out = translate_html(html, upper_text, upper)
        self.assertEqual(out, '<h2>RISKS</h2><p>SOME <strong>BOLD</strong> AND A <a href="https://x.eu/a">LINK</a>.</p>'
                              '<table><thead><tr><th>NAME</th><th>LEVEL</th></tr></thead>'
                              '<tbody><tr><td colspan="2">BIAS</td></tr></tbody></table>')

    def test_image_inside_paragraph_survives_and_url_never_sent(self):
        seen = []

        def model(fragment):
            seen.append(fragment)
            return upper_text(fragment)
        html = '<p>Look <img src="https://aidea-hub.eu/media/x.png" alt="a chart" width="300"> here</p>'
        out = translate_html(html, model, upper)
        self.assertNotIn('aidea-hub.eu', ''.join(seen))
        self.assertIn('<img src="https://aidea-hub.eu/media/x.png" alt="A CHART" width="300">', out)
        self.assertTrue(out.startswith('<p>LOOK ') and out.endswith(' HERE</p>'))

    def test_dropped_tag_retries_then_falls_back_to_plain_text(self):
        calls = []

        def drops_tags(fragment):
            calls.append(fragment)
            return re.sub(r'<[^>]+>', '', fragment).upper()
        out = translate_html('<p>Keep <strong>this</strong> bold</p><p>Second</p>', drops_tags, upper)
        self.assertEqual(out, '<p>KEEP THIS BOLD</p><p>SECOND</p>')
        self.assertEqual(len(calls), 3)          # 2 tries for the first block, 1 for the plain second block

    def test_changed_link_is_rejected(self):
        def changes_link(fragment):
            return fragment.replace('https://x.eu/a', 'https://evil.example').upper()
        out = translate_html('<p>See <a href="https://x.eu/a">this</a></p>', changes_link, upper)
        self.assertNotIn('evil', out)
        self.assertEqual(out, '<p>SEE THIS</p>')     # plain-text fallback drops the link markup, never the page

    def test_fallback_keeps_images(self):
        out = translate_html('<p>Hi <b>there</b> <img src="/media/a.png" alt=""></p>',
                             lambda f: 'garbage without tags', upper)
        self.assertIn('<img src="/media/a.png" alt="">', out)
        self.assertTrue(out.startswith('<p>HI THERE'))

    def test_unparseable_answer_falls_back(self):
        out = translate_html('<p>One <em>two</em></p>', lambda f: 'Sure! Here: <<<>>>', upper)
        self.assertEqual(out, '<p>ONE TWO</p>')

    def test_inline_only_content(self):
        self.assertEqual(translate_html('Hello <b>world</b>', upper_text, upper), 'HELLO <b>WORLD</b>')

    def test_empty_blocks_are_not_sent(self):
        model = mock.Mock(side_effect=upper_text)
        translate_html('<p> </p><p>Text</p>', model, upper)
        self.assertEqual(model.call_count, 1)


class TranslateTextRoutingTests(SimpleTestCase):
    @mock.patch('hub.translation._ollama_generate', side_effect=lambda prompt: prompt.rsplit('\n\n', 1)[1].upper())
    def test_html_goes_block_by_block_and_plain_text_as_before(self, generate):
        from hub.translation import translate_text
        self.assertEqual(translate_text('<p>Hi <b>you</b></p><p>Two</p>', 'en', 'el'), '<p>HI <b>YOU</b></p><p>TWO</p>')
        self.assertEqual(generate.call_count, 2)
        self.assertIn('Keep every HTML tag', generate.call_args_list[0].args[0])
        generate.reset_mock()
        self.assertEqual(translate_text('Plain words', 'en', 'el'), 'PLAIN WORDS')
        self.assertNotIn('HTML', generate.call_args.args[0])
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_html_translate -v 2`
  - Expected: ImportError, `No module named 'hub.html_translate'`.

- [ ] **Step 3: Implement.** `backend/hub/html_translate.py`:

```python
"""Translate rich-text HTML block by block, keeping its structure — spec
docs/superpowers/specs/2026-10-21-rich-text-and-activity-completion-design.md §2.

Only the text inside paragraphs, headings, list items, table cells, captions
and quotes goes to the model; tables, lists, images and order stay as they
are. Images are swapped for bare placeholders, so the model never sees their
addresses. Every answer is checked (same tags, same link targets, same
placeholders); a bad answer is retried once, then that block is translated as
plain text (inline formatting dropped, images kept)."""
import re
from collections import Counter

from lxml import etree
from lxml import html as lhtml

BLOCK_TAGS = frozenset({'p', 'h2', 'h3', 'li', 'td', 'th', 'caption', 'blockquote'})
_HTML = re.compile(r'</?[a-z][^>]*>', re.I)


def looks_like_html(text):
    return bool(text) and bool(_HTML.search(text))


def _parse(fragment):
    return lhtml.fragment_fromstring(fragment, create_parent='div')


def _inner(el):
    return (el.text or '') + ''.join(etree.tostring(c, encoding='unicode', method='html') for c in el)


def _elements(root):
    return [e for e in root.iter() if isinstance(e.tag, str) and e is not root]


def _signature(root):
    elements = _elements(root)
    return (
        Counter(e.tag for e in elements),
        [e.get('href') for e in elements if e.tag == 'a'],
        sorted(e.get('data-k') or '' for e in elements if e.tag == 'img'),
    )


def _is_leaf_block(el):
    return el.tag in BLOCK_TAGS and not any(
        isinstance(d.tag, str) and d.tag in BLOCK_TAGS for d in el.iterdescendants())


def _swap_images(el):
    """Replace each <img> in `el` with <img data-k="i">; return the originals."""
    originals = []
    for i, img in enumerate(list(el.iter('img'))):
        placeholder = etree.Element('img', {'data-k': str(i)})
        placeholder.tail, img.tail = img.tail, None
        img.getparent().replace(img, placeholder)
        originals.append(img)
    return originals


def _restore_images(el, originals):
    for placeholder in [e for e in el.iter('img') if e.get('data-k') is not None]:
        original = originals[int(placeholder.get('data-k'))]
        original.tail = placeholder.tail
        placeholder.getparent().replace(placeholder, original)


def _set_inner(el, source):
    for child in list(el):
        el.remove(child)
    el.text = source.text
    for child in list(source):
        el.append(child)


def _translate_block(el, translate_fragment, translate_plain):
    if not el.text_content().strip():
        return
    originals = _swap_images(el)
    fragment = _inner(el)
    expected = _signature(_parse(fragment))
    for _ in range(2):
        answer = translate_fragment(fragment)
        try:
            candidate = _parse(answer)
        except (etree.ParserError, ValueError):
            continue
        if _signature(candidate) == expected:
            _set_inner(el, candidate)
            _restore_images(el, originals)
            return
    # Plain-text fallback: the block keeps its place and its images.
    text = translate_plain(el.text_content())
    for child in list(el):
        el.remove(child)
    el.text = text
    for img in originals:
        el.append(img)


def translate_html(html, translate_fragment, translate_plain):
    root = _parse(html)
    for img in root.iter('img'):
        if (img.get('alt') or '').strip():
            img.set('alt', translate_plain(img.get('alt')))
    blocks = [e for e in _elements(root) if _is_leaf_block(e)]
    if not blocks:                  # inline-only content, e.g. 'Hello <b>world</b>'
        blocks = [root]
    for el in blocks:
        _translate_block(el, translate_fragment, translate_plain)
    if blocks != [root]:            # stray text between top-level blocks
        if (root.text or '').strip():
            root.text = translate_plain(root.text)
        for child in root:
            if (child.tail or '').strip():
                child.tail = translate_plain(child.tail)
    return _inner(root)
```

`backend/hub/translation.py`: replace `translate_text` with the three functions below (`_ollama_generate`, `LANGUAGE_NAMES` and the rest are unchanged):

```python
def _translate_plain(text: str, source: str, target: str) -> str:
    src = LANGUAGE_NAMES.get(source, source)
    tgt = LANGUAGE_NAMES.get(target, target)
    prompt = (
        f'Translate the following text from {src} to {tgt}. '
        f'Output only the translation, with no notes, quotes, or explanation.\n\n{text}'
    )
    return _ollama_generate(prompt)


def _translate_fragment(fragment: str, source: str, target: str) -> str:
    src = LANGUAGE_NAMES.get(source, source)
    tgt = LANGUAGE_NAMES.get(target, target)
    prompt = (
        f'Translate the text in this HTML fragment from {src} to {tgt}. '
        f'Keep every HTML tag and attribute exactly as it is; translate only the text between tags. '
        f'Output only the translated HTML, with no notes or explanation.\n\n{fragment}'
    )
    return _ollama_generate(prompt)


def translate_text(text: str, source: str, target: str) -> str:
    if not text or not text.strip():
        return text
    if source == target:
        return text
    from hub.html_translate import looks_like_html, translate_html
    if looks_like_html(text):
        return translate_html(
            text,
            lambda fragment: _translate_fragment(fragment, source, target),
            lambda plain: _translate_plain(plain, source, target),
        )
    return _translate_plain(text, source, target)
```

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_html_translate hub.tests.test_translation hub.tests.test_content_translation hub.tests.test_translation_review -v 2`
  - Expected: all pass.
  - If a `test_translation_review` test that mocks `_ollama_generate` with a fixed `'TR'` now fails only because HTML content comes back wrapped (e.g. `<p>TR</p>` instead of `TR`), update its expectation to the structure-preserving result and record a ruling.
  - If `test_table_and_formatting_keep_their_structure` differs only in lxml's attribute quoting or `<br>` serialisation, assert on the parsed structure with `lxml` instead of the string, and record a ruling.

- [ ] **Step 5: Lint and commit.**

```bash
"$UV" run ruff check hub analytics
git add hub/html_translate.py hub/translation.py hub/tests/test_html_translate.py
git commit -m "feat: translate rich text block by block, keeping tables, images and links"
git push
```

---

### Task 2: Complete an activity's self-completed resources in one call

**Files:**
- Modify: `backend/hub/completion.py`, `backend/hub/views/learner.py`, `backend/hub/urls.py`
- Create: `backend/hub/tests/test_activity_complete_resources.py`

**Interfaces — Produces:**
- `hub.completion.SELF_COMPLETED_TYPES = ('text', 'image', 'video', 'pdf', 'presentation')`.
- `self_completes(resource) -> bool`.
- `complete_self_completed(user, enrollment, activity, scroll_pct=None) -> (completed_ids: list[int], progress_pct: int)`.
- `POST /api/courses/<pk>/lessons/<lesson_pk>/complete-resources/` (`activity-complete-resources`), body `{scroll_pct?}`. It returns `{completed_resource_ids, activity_completed, progress_pct}`: 403 when not enrolled, 404 when the activity isn't in the course.

- [ ] **Step 1: Write the failing tests.** `backend/hub/tests/test_activity_complete_resources.py`:

```python
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import (
    Activity,
    CompetencyChange,
    Course,
    Enrollment,
    LearningPillar,
    Module,
    Resource,
    ResourceProgress,
    UserProfile,
)


class ActivityCompleteResourcesTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('acr_u', password='x')
        UserProfile.objects.create(user=self.user, competency_score=0)
        pillar = LearningPillar.objects.get_or_create(slug='p-acr', defaults={'name': 'P', 'order': 1})[0]
        self.course = Course.objects.create(title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True)
        module = Module.objects.create(course=self.course, title='M', order=1)
        self.activity = Activity.objects.create(module=module, title='A', order=1)
        make = lambda kind, order, **kw: Resource.objects.create(activity=self.activity, type=kind, order=order, **kw)  # noqa: E731
        self.text = make('text', 1, content='<p>Hi</p>')
        self.image = make('image', 2, url='https://x/a.png')
        self.optional_pdf = make('pdf', 3, url='https://x/a.pdf', is_required=False)
        self.h5p_self = make('h5p', 4, h5p_self_complete=True)
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        self.url = reverse('activity-complete-resources', kwargs={'pk': self.course.id, 'lesson_pk': self.activity.id})
        self.client.force_authenticate(self.user)

    def done_ids(self):
        return set(ResourceProgress.objects.filter(user=self.user, completed_at__isnull=False)
                   .values_list('resource_id', flat=True))

    def test_completes_all_self_completed_resources_and_the_course(self):
        res = self.client.post(self.url, {'scroll_pct': 80}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(set(res.data['completed_resource_ids']), {self.text.id, self.image.id, self.optional_pdf.id, self.h5p_self.id})
        self.assertEqual((res.data['activity_completed'], res.data['progress_pct']), (True, 100))
        self.assertEqual(ResourceProgress.objects.get(user=self.user, resource=self.text).engagement_data.get('scroll_pct'), 80)
        self.assertEqual(CompetencyChange.objects.filter(user=self.user).count(), 1)

    def test_second_call_changes_nothing(self):
        self.client.post(self.url, {}, format='json')
        res = self.client.post(self.url, {}, format='json')
        self.assertEqual(res.data['completed_resource_ids'], [])
        self.assertEqual(CompetencyChange.objects.filter(user=self.user).count(), 1)

    def test_quiz_is_not_completed_by_the_button(self):
        quiz = Resource.objects.create(activity=self.activity, type='quiz', order=5,
                                       quiz_data=[{'question': 'Q', 'options': [{'text': 'A', 'is_correct': True}]}])
        scoring_h5p = Resource.objects.create(activity=self.activity, type='h5p', order=6)
        assignment = Resource.objects.create(activity=self.activity, type='assignment', order=7, instructions='Do')
        res = self.client.post(self.url, {}, format='json')
        self.assertNotIn(quiz.id, self.done_ids())
        self.assertNotIn(scoring_h5p.id, self.done_ids())
        self.assertNotIn(assignment.id, self.done_ids())
        self.assertEqual(res.data['activity_completed'], False)

    def test_not_enrolled_and_wrong_activity(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).delete()
        self.assertEqual(self.client.post(self.url, {}, format='json').status_code, 403)
        Enrollment.objects.create(user=self.user, course=self.course)
        other = reverse('activity-complete-resources', kwargs={'pk': self.course.id, 'lesson_pk': 999999})
        self.assertEqual(self.client.post(other, {}, format='json').status_code, 404)
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_activity_complete_resources -v 2`
  - Expected: `NoReverseMatch: 'activity-complete-resources'`.

- [ ] **Step 3: Implement.** `backend/hub/completion.py`: add after `record_resource_completion`:

```python
# Resources the learner completes with the activity's "Mark activity as done"
# button (spec 2026-10-21): everything except quizzes, assignments and H5P that
# report their own finish.
SELF_COMPLETED_TYPES = ('text', 'image', 'video', 'pdf', 'presentation')


def self_completes(resource):
    return resource.type in SELF_COMPLETED_TYPES or (resource.type == 'h5p' and resource.h5p_self_complete)


def complete_self_completed(user, enrollment, activity, scroll_pct=None):
    """Complete every not-yet-done self-completed resource of the activity,
    then re-aggregate the enrollment once. Returns (completed ids, progress_pct)."""
    done = set(
        ResourceProgress.objects.filter(user=user, resource__activity=activity, completed_at__isnull=False)
        .values_list('resource_id', flat=True)
    )
    completed = []
    for resource in activity.resources.order_by('order'):
        if resource.id in done or not self_completes(resource):
            continue
        engagement = {'scroll_pct': scroll_pct} if resource.type == 'text' and scroll_pct is not None else None
        _mark_resource_complete(user, resource, engagement_data=engagement)
        completed.append(resource.id)
    if not completed:
        return [], enrollment.progress_pct
    _mirror_legacy_progress(user, activity)
    _advance_pointer(enrollment, activity, False)
    return completed, recompute_course_progress(user, enrollment)
```

`backend/hub/views/learner.py`: add after `ResourceCompleteView`:

```python
class ActivityCompleteResourcesView(APIView):
    """POST .../lessons/<lesson_pk>/complete-resources/ — the activity's "Mark
    activity as done": completes its text, image, video, PDF, presentation and
    self-completed H5P resources at once, then recomputes progress once."""

    def post(self, request, pk, lesson_pk):
        try:
            enrollment = Enrollment.objects.select_related('course').get(user=request.user, course_id=pk)
        except Enrollment.DoesNotExist:
            if not Course.objects.filter(pk=pk).exists():
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)
        activity = Activity.objects.filter(pk=lesson_pk, module__course_id=pk).first()
        if activity is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        scroll = request.data.get('scroll_pct')
        scroll_pct = scroll if isinstance(scroll, (int, float)) and not isinstance(scroll, bool) else None

        from hub.completion import complete_self_completed, completed_activity_ids
        completed, progress_pct = complete_self_completed(request.user, enrollment, activity, scroll_pct)
        return Response({
            'completed_resource_ids': completed,
            'activity_completed': activity.id in completed_activity_ids(request.user, enrollment.course),
            'progress_pct': progress_pct,
        })
```

Check that `Activity` and `Course` are imported in `learner.py` (`grep -n "^from hub.models import" -A20 hub/views/learner.py`) and add whatever is missing. Make sure `ActivityCompleteResourcesView` is exported the same way `ResourceCompleteView` reaches `hub/urls.py`: if it's imported through `hub/views/__init__.py`, add it there; otherwise import it from `.views.learner` in `urls.py`.

`backend/hub/urls.py`: next to `resource-complete`, add:

```python
    path('courses/<int:pk>/lessons/<int:lesson_pk>/complete-resources/', ActivityCompleteResourcesView.as_view(), name='activity-complete-resources'),
```

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `"$UV" run manage.py test hub.tests.test_activity_complete_resources hub.tests.test_competency_performance -v 2`
  - Expected: all pass.

- [ ] **Step 5: Full suite, lint, commit.**

```bash
"$UV" run ruff check hub analytics
"$UV" run manage.py test hub analytics
git add hub/completion.py hub/views hub/urls.py hub/tests/test_activity_complete_resources.py
git commit -m "feat: complete an activity's self-completed resources in one call"
git push
```

---

### Task 3: Tables and images in the editor; safe rendering

**Files:**
- Create: `frontend/src/lib/richText.js`, `frontend/src/lib/richText.test.js`
- Modify:
  - `frontend/src/components/lesson/RichTextEditor.jsx`, `frontend/src/components/lesson/HtmlContent.jsx`
  - the CSS that styles `.rich-html` (find it with `grep -rn "\.rich-html" frontend/src --include=*.css`)

**Interfaces — Produces:**
- `RICH_TEXT_VALID_ELEMENTS` (string).
- `SANITIZE_CONFIG` (DOMPurify options).
- `isAllowedImageSrc(src) -> boolean`.
- `uploadImage(blobInfo) -> Promise<string>` (used by TinyMCE).

- [ ] **Step 1: Write the failing test.** `frontend/src/lib/richText.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { RICH_TEXT_VALID_ELEMENTS, SANITIZE_CONFIG, isAllowedImageSrc } from './richText.js'

test('image sources: https, uploaded media and local development only', () => {
  for (const ok of ['https://aidea-hub.eu/media/a.png', '/media/lesson_assets/a.png',
    'http://localhost:8000/media/a.png', 'http://127.0.0.1:8000/media/a.png']) {
    assert.equal(isAllowedImageSrc(ok), true, ok)
  }
  for (const bad of ['javascript:alert(1)', 'data:image/png;base64,AAAA', 'http://example.com/a.png',
    '//evil.example/a.png', '', null, undefined, ' JAVASCRIPT:alert(1)']) {
    assert.equal(isAllowedImageSrc(bad), false, String(bad))
  }
})

test('editor and sanitizer allow tables and images and nothing new besides', () => {
  for (const el of ['table', 'thead', 'tbody', 'tr', 'th', 'td', 'caption', 'img']) {
    assert.ok(RICH_TEXT_VALID_ELEMENTS.includes(el), el)
    assert.ok(SANITIZE_CONFIG.ALLOWED_TAGS.includes(el), el)
  }
  for (const attr of ['src', 'alt', 'width', 'height', 'colspan', 'rowspan', 'scope', 'href', 'target', 'rel']) {
    assert.ok(SANITIZE_CONFIG.ALLOWED_ATTR.includes(attr), attr)
  }
  assert.ok(!SANITIZE_CONFIG.ALLOWED_ATTR.includes('style'))
  assert.ok(!SANITIZE_CONFIG.ALLOWED_TAGS.includes('script'))
  assert.ok(!SANITIZE_CONFIG.ALLOWED_TAGS.includes('iframe'))
})
```

Run `npm test` from `frontend/`. Expected: `ERR_MODULE_NOT_FOUND …/richText.js`.

- [ ] **Step 2: Implement the helpers.** `frontend/src/lib/richText.js`:

```js
// One list of what rich text may contain — used by the editor (TinyMCE
// valid_elements) and the learner view (DOMPurify). Spec 2026-10-21 §1.

export const RICH_TEXT_VALID_ELEMENTS = [
  'p,br,strong/b,em/i,u,h2,h3,ul,ol,li,a[href|target|rel],blockquote',
  'table,thead,tbody,tr,th[colspan|rowspan|scope],td[colspan|rowspan],caption',
  'img[src|alt|width|height]',
].join(',')

export const SANITIZE_CONFIG = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'b', 'em', 'i', 'u', 'h2', 'h3', 'ul', 'ol', 'li', 'a', 'blockquote',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'caption', 'img'],
  ALLOWED_ATTR: ['href', 'target', 'rel', 'src', 'alt', 'width', 'height', 'colspan', 'rowspan', 'scope'],
}

const LOCAL_DEV = /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?\//i

/** https images, our uploaded /media/ files, and local development uploads. */
export function isAllowedImageSrc(src) {
  if (typeof src !== 'string') return false
  const value = src.trim()
  return /^https:\/\//i.test(value) || /^\/media\//.test(value) || LOCAL_DEV.test(value)
}
```

`frontend/src/components/lesson/HtmlContent.jsx`: sanitize with the shared config and drop images with other sources:

```jsx
import PropTypes from 'prop-types'
import DOMPurify from 'dompurify'
import { SANITIZE_CONFIG, isAllowedImageSrc } from '../../lib/richText'

const looksLikeHtml = (s) => /<\/?[a-z][\s\S]*>/i.test(s)

// Images are kept only from https, our /media/ uploads or local development.
DOMPurify.addHook('uponSanitizeElement', (node, data) => {
  if (data.tagName === 'img' && !isAllowedImageSrc(node.getAttribute('src'))) {
    node.parentNode?.removeChild(node)
  }
})
```

The component body stays the same, except the sanitize call becomes `DOMPurify.sanitize(text, SANITIZE_CONFIG)`. Also add a wrapper so wide tables scroll sideways, and keep the existing plain-text branch. Then, in the CSS that styles `.rich-html`, add:

```css
.rich-html table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; display: block; overflow-x: auto; }
.rich-html th, .rich-html td { border: 1px solid var(--color-border); padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }
.rich-html th { background: var(--color-bg); font-weight: 600; }
.rich-html caption { caption-side: top; text-align: left; font-weight: 600; padding-bottom: 0.35rem; }
.rich-html img { max-width: 100%; height: auto; border-radius: 6px; }
```

`frontend/src/components/lesson/RichTextEditor.jsx`:
- import `client` from `'../../api/client'` and `RICH_TEXT_VALID_ELEMENTS` from `'../../lib/richText'`;
- add the upload function at module level:

```jsx
// TinyMCE image upload: same endpoint and checks as image resources.
async function uploadImage(blobInfo) {
  const form = new FormData()
  form.append('file', blobInfo.blob(), blobInfo.filename())
  try {
    const res = await client.post('/authoring/upload/', form)
    return res.data.url
  } catch (err) {
    throw new Error(err.response?.data?.error ?? 'Upload failed.')
  }
}
```

- change `init` to:

```jsx
          plugins: 'lists link autolink table image',
          toolbar:
            'undo redo | blocks | bold italic underline | bullist numlist | link image table | removeformat',
          table_toolbar: 'tableprops tabledelete | tableinsertrowbefore tableinsertrowafter tabledeleterow | tableinsertcolbefore tableinsertcolafter tabledeletecol | tablemergecells tablesplitcells',
          table_appearance_options: false,
          table_advtab: false,
          table_cell_advtab: false,
          table_row_advtab: false,
          table_default_styles: {},
          table_default_attributes: {},
          image_description: true,
          image_dimensions: true,
          image_title: false,
          automatic_uploads: true,
          images_upload_handler: uploadImage,
          images_file_types: 'png,jpg,jpeg,gif,webp',
          paste_data_images: true,
          // Content creators are trusted, but keep the output conservative.
          valid_elements: RICH_TEXT_VALID_ELEMENTS,
```

  Keep `menubar`, `statusbar`, `branding`, `promotion`, `height`, `placeholder`, `block_formats` and `content_style`. Add `table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px}img{max-width:100%;height:auto}` to `content_style`, so tables are visible while editing.

Run `npm test` (expected: pass) and `npm run lint` (expected: clean).

- [ ] **Step 3: Verify.**
  - Run `VITE_API_URL=http://localhost:8000/api npm run build`. Expected: built.
  - Manual (dev):
    1. In an activity's text resource, insert a 2×2 table and type into it.
    2. Upload a PNG with the image button and fill in the description.
    3. Save, then open the activity as a learner. The table and image show, the table scrolls sideways on a narrow window, and the image fits.

- [ ] **Step 4: Commit.**

```bash
git add frontend/src
git commit -m "feat: tables and images in the rich-text editor, sanitized for learners"
git push
```

---

### Task 4: One "Mark activity as done" button

**Files:**
- Create: `frontend/src/lib/activityCompletion.js`, `frontend/src/lib/activityCompletion.test.js`
- Modify:
  - `frontend/src/components/learner/ResourceView.jsx`
  - `frontend/src/pages/ActivityPage.jsx` and `.css`
  - `frontend/src/locales/*.json`

**Interfaces:**
- **Consumes:** Task 2's endpoint.
- **Produces:**
  - `selfCompletes(resource) -> boolean`;
  - `activityButtonState(resources) -> { show: boolean, done: boolean, pendingIds: number[], showNote: boolean }`.

- [ ] **Step 1: Write the failing test.** `frontend/src/lib/activityCompletion.test.js`:

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { activityButtonState, selfCompletes } from './activityCompletion.js'

const r = (id, type, extra = {}) => ({ id, type, is_completed: false, ...extra })

test('which resources the activity button covers', () => {
  for (const type of ['text', 'image', 'video', 'pdf', 'presentation']) assert.equal(selfCompletes(r(1, type)), true, type)
  assert.equal(selfCompletes(r(1, 'h5p', { h5p_self_complete: true })), true)
  for (const res of [r(1, 'quiz'), r(1, 'assignment'), r(1, 'h5p')]) assert.equal(selfCompletes(res), false, res.type)
})

test('button with a pending text and an unfinished quiz', () => {
  assert.deepEqual(activityButtonState([r(1, 'text'), r(2, 'quiz'), r(3, 'image', { is_completed: true })]),
    { show: true, done: false, pendingIds: [1], showNote: true })
})

test('all covered resources done: completed state, no note when the quiz is done too', () => {
  assert.deepEqual(activityButtonState([r(1, 'text', { is_completed: true }), r(2, 'quiz', { is_completed: true })]),
    { show: true, done: true, pendingIds: [], showNote: false })
})

test('no button for an activity with only a quiz or an assignment', () => {
  assert.equal(activityButtonState([r(1, 'quiz')]).show, false)
  assert.equal(activityButtonState([r(1, 'assignment')]).show, false)
  assert.equal(activityButtonState([]).show, false)
})
```

Run `npm test`. Expected: `ERR_MODULE_NOT_FOUND …/activityCompletion.js`.

- [ ] **Step 2: Implement the helpers.** `frontend/src/lib/activityCompletion.js`:

```js
// The activity's single "Mark activity as done" button (spec 2026-10-21 §3).
// Quizzes, assignments and H5P that report their own finish complete themselves.

const SELF_COMPLETED_TYPES = ['text', 'image', 'video', 'pdf', 'presentation']

export const selfCompletes = (resource) =>
  SELF_COMPLETED_TYPES.includes(resource.type) || (resource.type === 'h5p' && Boolean(resource.h5p_self_complete))

export function activityButtonState(resources) {
  const covered = resources.filter(selfCompletes)
  const pendingIds = covered.filter(res => !res.is_completed).map(res => res.id)
  const others = resources.filter(res => !selfCompletes(res))
  return {
    show: covered.length > 0,
    done: covered.length > 0 && pendingIds.length === 0,
    pendingIds,
    showNote: covered.length > 0 && others.some(res => !res.is_completed),
  }
}
```

Run `npm test`. Expected: pass.

- [ ] **Step 3: Wire it in.**
- **`ResourceView.jsx`:** delete the `selfCompletes` constant and the `{selfCompletes && ( <div className="lp-resource-footer"> … </div> )}` block. Quizzes and scoring H5P keep calling `complete` from their bodies; the assignment footer stays.
- **`ActivityPage.jsx`:**
  - import `activityButtonState` from `'../lib/activityCompletion'`;
  - add, next to `completeResource`:

```jsx
  const [completingActivity, setCompletingActivity] = useState(false)
  const completeActivity = useCallback(async () => {
    setCompletingActivity(true)
    try {
      const res = await client.post(`/courses/${courseId}/lessons/${activityId}/complete-resources/`,
        { scroll_pct: scrollPctRef.current })
      const { completed_resource_ids: ids, progress_pct: progressPct, activity_completed: activityDone } = res.data
      ids.forEach(id => tracking.completed(id))
      setActivity(prev => prev && ({
        ...prev,
        is_completed: activityDone,
        resources: prev.resources.map(r => (ids.includes(r.id) ? { ...r, is_completed: true } : r)),
      }))
      setCourseLearn(prev => prev && ({
        ...prev,
        progress_pct: progressPct,
        modules: prev.modules.map(mod => ({
          ...mod,
          lessons: mod.lessons.map(a => (a.id === Number(activityId) ? { ...a, is_completed: activityDone } : a)),
        })),
      }))
    } finally {
      setCompletingActivity(false)
    }
  }, [courseId, activityId, setActivity, tracking])
```

  - Make sure `useState` is imported. Right after the `resources.map(...)` block (inside the resources section, before "Navigation"), render:

```jsx
              {(() => {
                const state = activityButtonState(resources)
                if (!state.show) return null
                return (
                  <div className="lp-activity-done">
                    <button type="button"
                      className={`lp-complete-btn lp-activity-done-btn ${state.done ? 'lp-complete-btn--done' : ''}`}
                      onClick={completeActivity} disabled={state.done || completingActivity}>
                      {state.done ? t('common.completedCheck')
                        : completingActivity ? t('common.saving') : t('lesson.activityDone.button')}
                    </button>
                    {state.showNote && <p className="lp-activity-done-note">{t('lesson.activityDone.note')}</p>}
                  </div>
                )
              })()}
```

  - If the React-compiler lint rule rejects the inline IIFE, compute `const doneState = activityButtonState(resources)` in the component body after `resources` is known, and render from `doneState`.
- **`ActivityPage.css`:** add:

```css
.lp-activity-done { display: flex; flex-direction: column; align-items: flex-start; gap: 0.4rem; margin: 1rem 0 0.5rem; }
.lp-activity-done-note { margin: 0; font-size: 0.85rem; color: var(--color-text-muted); }
```

- [ ] **Step 4: Locales (9 languages).** Add `lesson.activityDone.button` and `lesson.activityDone.note`. `en`:
  - button: "Mark activity as done"
  - note: "Quizzes and assignments are completed when you submit them."

  Write real translations for el, fr, es, it, fi, sv, no and de in each locale's tone. Merge with a script that never overwrites existing keys and keeps line endings and the final newline.

- [ ] **Step 5: Verify.**
  - From `frontend/`: `npm run lint`, `npm test`, `node scripts/check-locales.mjs` and `VITE_API_URL=http://localhost:8000/api npm run build`. Expected: all clean.
  - Manual (dev): an activity with a text and a video shows one "Mark activity as done" and no per-resource buttons. Clicking it ticks both, and the course progress bar updates.

- [ ] **Step 6: Commit.**

```bash
git add frontend/src
git commit -m "feat: one 'Mark activity as done' button per activity"
git push
```

---

### Task 5: Full verification, docs, rollout

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md.** Under API endpoints add `` `POST /api/courses/<id>/lessons/<a>/complete-resources/` — the activity's "Mark activity as done": completes its text/image/video/PDF/presentation/self-completed H5P resources at once ``. Under the architecture notes, add one line: rich text may hold tables and images (`frontend/src/lib/richText.js` is the single allow-list), and HTML is translated block by block (`hub/html_translate.py`).

- [ ] **Step 2: Full verification.**
  - From `backend/`: `"$UV" run ruff check .`, `"$UV" run coverage run manage.py test hub analytics --verbosity=1`, `"$UV" run coverage report --fail-under=70` and `"$UV" run manage.py makemigrations --check --dry-run`.
  - From `frontend/`: `npm run lint && npm test && node scripts/check-locales.mjs && VITE_API_URL=http://localhost:8000/api npm run build`.
  - Expected: all pass, and "No changes detected".

- [ ] **Step 3: Commit.**

```bash
git add CLAUDE.md
git commit -m "docs: activity completion endpoint, rich-text tables/images and HTML translation"
git push
```

- [ ] **Step 4: Rollout note for the user.** On the VM, with `COMPOSE_FILE` set:

```bash
git pull
docker compose up -d --build backend celery frontend
```

There are no migrations. Then:
1. In a test course, build a page with text, a table and an uploaded image in one text resource.
2. Translate the course to one language and check that the table and image survive.
3. Open the page as a learner: one "Mark activity as done" button.
