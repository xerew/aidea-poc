# Rich Text (Tables, Images) and One-Click Activity Completion — Design

Date: 2026-10-21 · Status: approved in conversation, awaiting spec review

## Purpose

This answers partner feedback (V. Gkamas, via the partner feedback stream). Authors want:
- a course page with text, tables and pictures together;
- not three disconnected resources (text, image, text) that learners must each mark as done.

### Decisions taken

| Topic | Decision |
|---|---|
| Tables | In the rich-text editor: insert, add/remove rows and columns, header row, merge cells. No colours or fixed sizes; site styling; wide tables scroll sideways on phones. |
| Images in text | Upload from the computer (existing upload endpoint and checks) or an `https` link; image description (alt text); resizable; never wider than the page. |
| Where | Every use of the rich-text editor: text resources and assignment instructions. |
| Image resource type | **Kept**, for stand-alone images with a caption. |
| Translation | HTML translated **block by block** with a structure check, a retry, then a plain-text fallback for that block. Images are never sent; alt text is translated separately. |
| Completion | **One "Mark activity as done" button per activity** for text, image, video, PDF, presentation and self-completed H5P. Quizzes, assignments and scoring H5P complete themselves as now. |

## 1. Editor and rendering

**Editor** (`frontend/src/components/lesson/RichTextEditor.jsx`, self-hosted TinyMCE):
- Plugins: add `table` and `image`. Toolbar: add `table` and `image`.
- The table toolbar gives insert/delete row and column, header row, and merge/split cells. Table styling options are off: no border/colour/class dialogs (`table_appearance_options: false`, `table_advtab: false`, `table_cell_advtab: false`, `table_row_advtab: false`).
- **Images:**
  - `images_upload_handler` posts the file to `POST /api/authoring/upload/` (the existing authoring upload, the same checks as image resources) and inserts the returned URL;
  - `image_description: true` (alt text); `image_dimensions: true`; `automatic_uploads: true`;
  - pasted images are uploaded the same way.
- **`valid_elements`** gains:
  - `table`, `thead`, `tbody`, `tr`;
  - `th[colspan|rowspan|scope]`, `td[colspan|rowspan]`, `caption`;
  - `img[src|alt|width|height]`.

  Everything else stays as today.
- Pasting from Word or Google Docs: TinyMCE's default paste handling. Elements outside `valid_elements` are dropped.

**Rendering** (`HtmlContent.jsx`, DOMPurify):
- Allowed tags and attributes are the editor's list.
- An `img` whose `src` isn't `https:` or a site-relative `/media/` path is removed.
- Links keep `target`/`rel` as today.
- **CSS:** `.rich-html table` is full width with borders and padding from the site theme, and wraps in a sideways-scrolling container on narrow screens. `.rich-html img { max-width: 100%; height: auto }`.

## 2. Structure-safe translation

`translate_text` stays for plain text. A new `translate_html(html, source, target)` is used whenever a translated field contains HTML: resource `content` and `instructions`, plus any other rich-text field already translated through `translate_text`.

1. **Parse** the fragment (lxml, already installed as a dependency).
2. **Blocks** are `p`, `h2`, `h3`, `li`, `td`, `th`, `caption` and `blockquote`, plus text directly inside them; a block must not contain other blocks. Container structure (`table`/`tr`/`ul`/`ol`), images and order are kept as they are.
3. **Each block's inner HTML** is translated by the model with the instruction to keep every HTML tag and attribute unchanged.
4. **Check:**
   - the result must have the same multiset of tags, and the same `href` values in the same order;
   - otherwise retry once;
   - otherwise translate the block's plain text, which drops its inline formatting but never breaks the structure.
5. **`img alt`** is translated as a short plain text. `src`, `width` and `height` never change.
6. **Empty or whitespace-only blocks** are skipped.

Unchanged: when translations run (the existing sync), the model and tunnel, the translation status, and manual editing of translations.

## 3. One "Mark activity as done" per activity

**Self-completed resource types:** `text`, `image`, `video`, `pdf`, `presentation`, and `h5p` with `h5p_self_complete`.

**Learner UI** (`ResourceView` / activity page):
- The per-resource "Mark as done" button is removed for those types.
- **At the bottom of the activity:** "Mark activity as done" when at least one of those resources is not done. It shows "Completed ✓" when all of them are done. There's no button when the activity has none.
- **A note** when the activity also has an unfinished quiz, assignment or scoring H5P: *"Quizzes and assignments are completed when you submit them."*
- **After the click,** each covered resource shows its tick, and progress updates as today.

**Backend:**
- `POST /api/courses/<pk>/lessons/<activity_pk>/complete-resources/` (learner, enrolled). It:
  - marks every not-yet-completed resource of the self-completed types in the activity as complete (required and optional), with the same per-resource data as the existing completion (time spent, engagement);
  - then recalculates the enrollment's progress **once**;
  - returns the activity's resource states and the course progress.
- A second call changes nothing.
- The existing per-resource completion endpoint is unchanged (quizzes, scoring H5P and the API still use it).
- **Tracking and analytics:** each resource still has its own completion time and time spent. The timeline, Excel and the competency slow-pace check need no change. The tracker's `completed` call is made for each resource that was completed.

## Testing

- **Editor/rendering:**
  - the sanitizer keeps tables, `img` with an https or `/media/` src, and alt text;
  - it removes `img` with `javascript:`/`data:`/`http:` sources, and drops style attributes and other tags.
- **Translation:**
  - a page with a table, an image, bold text and a link keeps identical structure, with only text changed;
  - a dropped tag triggers a retry, then the plain-text fallback for that block only;
  - `src` and `href` never change; alt text is translated;
  - plain-text content behaves exactly as before.
- **Completion:**
  - the endpoint completes only the self-completed types (optional ones too), skipping quizzes, assignments and scoring H5P;
  - it's idempotent;
  - course completion and the competency change happen once;
  - a learner who isn't enrolled gets 403.
  - Frontend helper: which resources the button covers, and when the note and button show.

## Out of scope

- Converting existing text + image + text activities into single resources (authors can do this by hand).
- Video embeds inside text.
- Automatic completion on viewing.
- Table colours and themes.
