# Presentation Resource — Design

Date: 2026-10-19 · Status: approved in conversation, awaiting spec review

## Purpose

A new resource type, **Presentation**. The author uploads a PowerPoint deck (.pptx). Learners watch it inside the activity as a slideshow, with animations, transitions and embedded media playing as in PowerPoint. Learners don't have to download it to see it.

### Decisions taken

| Topic | Decision |
|---|---|
| Playback | **Microsoft's Office viewer** embedded in an iframe (`https://view.officeapps.live.com/op/embed.aspx?src=<file URL>`). It keeps animations, transitions and most embedded media. Converting slides to images was rejected because it loses animations and media. |
| File format | **.pptx only.** Authors convert .odp/.ppt themselves (Impress: File → Save As → PowerPoint). The upload error says how. |
| Size | Uploads up to **100 MB**. Above `PRESENTATION_VIEWER_LIMIT_MB` (default **10**, the viewer's documented limit as far as we know) the author sees a warning, and learners always get a download button for that deck. |
| Language versions | **Optional per-language decks**, like H5P. A learner sees their language when it exists, otherwise the main deck. |
| Download | **The author decides per deck** ("Learners can download the file", off by default). It is forced on for decks over the viewer limit. |
| Completion | **Mark as done**, like PDFs and videos. The viewer reports nothing to our page. |

## Authoring

In the activity editor, **Presentation** joins Text, Video, Image, PDF, Quiz, Assignment and H5P.

1. **Upload .pptx.** The upload is checked:
   - It must be a real .pptx: a ZIP containing `[Content_Types].xml` and `ppt/presentation.xml`, with the PowerPoint presentation content type. Otherwise the error is `not_pptx`.
   - **.odp / .ppt or a renamed file:** error `convert_to_pptx`, *"Save it as .pptx (in Impress: File → Save As → PowerPoint), then upload again."*
   - **Macro-enabled deck** (`.pptm` content type or a `vbaProject.bin` part): error `macros`.
   - **Corrupt ZIP:** error `corrupt`.
   - **Over 100 MB:** error `too_large`, *"Max 100 MB. In PowerPoint use File → Compress Media and Compress Pictures, or put videos online and link them."*
2. **When accepted:** the panel shows the title (from the deck's properties, else the file name), slide count, size and version, plus **Replace**, **Preview** and **Remove**.
   - Over the viewer limit, a warning: *"Over 10 MB — Microsoft's viewer may not play it; check the preview on the live site. Learners will also get a download button."*
3. **Language versions:** "Add language → upload .pptx", with replace and remove per language. Same layout as the H5P panel.
4. **Checkbox:** "Learners can download the file" (off by default).
5. **Translating mode** (editing a course's translation): the panel is hidden, as for H5P. Language decks are managed in the original.

Editable by anyone who can edit the course.

**Storage:**
- Files go to `media/presentations/<resource id>/<random>.pptx`.
- The name is unguessable but public, because Microsoft's viewer must fetch it.
- Replacing a file increments the version and deletes the old file. Removing deletes the file.
- Deleting the resource deletes its files.

## Learners

- **The frame:** a responsive **16:9 frame** showing the Office viewer for the deck in the learner's language (falling back to the main deck). Its own controls (next/previous, slide counter, full screen) and click-through animations work as in PowerPoint.
- **Below the frame:**
  - **Open full screen** (useful on phones);
  - **Download (.pptx)**, when the author allowed it or the deck is over the viewer limit;
  - **Mark as done**.
- **No deck uploaded yet:** a placeholder, like the other media types.
- **The viewer can't reach the file:** when the file URL's host is `localhost`, `127.0.0.1` or a private address (development), the frame is replaced by a notice (*"The slideshow plays on the live site"*) and a download link.
- **Microsoft-side errors** (the viewer is down, the file is damaged, the file is too big): learners still have Mark as done, and the download where it applies. We can't detect these errors from our page.

## Tracking and analytics

- **Completion:** Mark as done.
- **Active time:** clicks inside the cross-origin viewer never reach our page.
  - When focus enters the presentation frame (window blur with `document.activeElement` = that iframe), the resource counts as **active**, like a playing video.
  - That stops when focus returns to our page, the tab is hidden, or **5 minutes** after focus entered (constant `PRESENTATION_FOCUS_MS`).
  - On-screen time is unchanged.
- **Events:** `presentation_download` when the download button is used. The deck language shown is recorded with the visit's events, as for H5P.
- **Analytics:**
  - **Content tree note:** typical time, and "downloaded by N" when a download was offered.
  - **Learner timeline:** time, done/not done, downloaded.
  - **Excel:** presentation rows in Resources (time, completed, downloaded), and `presentation_download` in Events.
- **Not possible:** which slides were seen, or how far a learner got. The viewer doesn't report it.

## Privacy

A Privacy Policy section:
- Presentations play in Microsoft's Office viewer.
- The learner's browser loads the viewer from Microsoft, so Microsoft receives their IP address and browser details.
- Microsoft fetches the course file.
- No names or learning data are sent.

## Architecture

**Backend:**
- **Model and resource fields:**
  - `Resource.Type.PRESENTATION = 'presentation'`;
  - `Resource.presentation_downloadable` (bool, default False);
  - `PresentationFile`: resource FK (`presentation_files`), language (`''` = main, unique with resource), file, title, slide_count, size_bytes, version, uploaded_by, uploaded_at.
- **`hub/presentation.py`:** `check_pptx(uploaded_file) -> {title, slide_count}` or `PresentationError(code)`. The slide count is the number of `p:sldId` entries in `ppt/presentation.xml`; the title comes from `docProps/core.xml` `dc:title`.
- **Upload API:**
  - `POST /api/authoring/courses/<id>/modules/<m>/lessons/<a>/resources/<r>/presentation/` (multipart `file`, `language`) and `DELETE …/presentation/?language=`;
  - both return the updated resource;
  - course-editor permission;
  - the language must be one of the platform's languages, or empty.
- **Settings:** `PRESENTATION_MAX_MB` = 100 and `PRESENTATION_VIEWER_LIMIT_MB` = 10, both environment-overridable.
- **Learner payload:** `presentation: {url (absolute), title, slides, language, size_bytes, over_viewer_limit, downloadable}`. Here `downloadable` = the author's setting OR `over_viewer_limit`.
- **Authoring payload:** `presentation_files` (all languages, with an `over_viewer_limit` flag each) and `presentation_downloadable`.
- **Analytics:** presentation branches in `resource_notes`, `resource_detail` and the workbook rows.
- **Caddy:**
  - `request_body max_size 105MB` for `^/api/authoring/.*/presentation/$`;
  - `/media/presentations/*` served with the .pptx content type and `X-Content-Type-Options nosniff`;
  - after deploying, `docker compose restart caddy`.

**Frontend:**
- `PresentationPanel` (editor), modelled on `H5PPanel`.
- `PresentationBody` (learner), with:
  - `officeViewerUrl(fileUrl)`;
  - `isPrivateHost(url)`;
  - the focus tracking hook-up.
- Tracking: `tracker.setPlaying(resourceId, true/false)` driven by frame focus, with the 5-minute cap.
- The editor's "add resource" menu gains Presentation (lucide `Presentation` icon).
- A Privacy Policy section, and locale strings in all 9 languages.

## Testing

- **Backend:**
  - a minimal real .pptx (built in the test with `zipfile`) is accepted, with slide count and title read;
  - rejected: .odp, a renamed .txt, .ppt (OLE), macro-enabled, corrupt ZIP, over 100 MB (with a lowered setting);
  - permissions (other creator 403, learner 403);
  - versioning and replacement (old file deleted);
  - per-language upload and delete;
  - the learner payload picks the viewer's language, else main;
  - `downloadable` is forced on over the viewer limit;
  - analytics notes, timeline and Excel rows.
- **Frontend:**
  - unit tests for `officeViewerUrl` (encoding), `isPrivateHost` (localhost, 127.x, 10.x, 192.168.x, 172.16–31.x, public), and the focus cap;
  - lint, the 9-language check and the build.
- **Manual (on the live site):** a real deck with animations and an embedded video, on desktop and phone. Plus one 10–100 MB deck, to see whether the viewer plays it; raise `PRESENTATION_VIEWER_LIMIT_MB` if it does.

## Out of scope

- Per-slide tracking.
- .odp/.ppt conversion on the server.
- Converting slides to images.
- Presentations inside quizzes or assignments.
- Microsoft-side error detection.
