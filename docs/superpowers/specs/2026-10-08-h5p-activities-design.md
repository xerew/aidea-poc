# H5P Activities as a Resource Type — Design

Date: 2026-10-08 · Status: approved in conversation, awaiting spec review

## Purpose

Let authors add **ready-made H5P activities** (made elsewhere — Lumi, H5P.com, H5P.org, Moodle) to an activity, and let AIDEA **capture what learners do in them**: scores, answers, attempts and completion, feeding progress, analytics and the Excel export.

### Decisions taken

| Topic | Decision |
|---|---|
| Scope | H5P only, uploaded as a `.h5p` file. No link/embed type, no PhET or other simulations. |
| Why upload, not embed | Embeds from other sites are cross-origin: the browser blocks reading results, so no data. Data is only possible when AIDEA plays the file. |
| Player | **h5p-standalone** (open source, runs in the browser) playing the extracted package; no H5P server, no H5P editor. |
| Isolation | The H5P runs in a **sandboxed iframe** that cannot read AIDEA's pages, cookies or sign-in token; it only passes xAPI statements and its height to the page. |
| When "done" | When H5P reports the learner **finished**, whatever the score; the score is kept, and a low score marks the learner *stuck* like a failed quiz. Types that never report finishing get a **"Mark as done"** button. |
| Retries | Allowed. The **first finished attempt** is the score; later attempts are kept as practice data. |
| Languages | Optional **per-language `.h5p` versions**; learners get their language's version, else the main one. Each attempt records the version used. |
| Size | Max **100 MB** per file, **300 MB** unpacked. |

## Authoring and storage

- New `Resource.Type.H5P = 'h5p'` ("H5P activity").
- In the activity editor, an H5P resource shows: an upload box; after upload, the activity name and H5P type (e.g. Interactive Video, Question Set) and a **Preview**; a **Language versions** list to add/remove a `.h5p` per language; a checkbox **"Learners mark it done themselves"** (default set from the H5P type; see below).
- Re-uploading replaces the file for that language; earlier attempts stay, each tied to the file version used.

### `H5PPackage` — one row per resource × language

| Field | Notes |
|---|---|
| `resource` FK | |
| `language` | `''` = main file; else one of the 9 language codes. Unique with `resource`. |
| `file` | the original `.h5p` |
| `folder` | extracted location, `media/h5p/<random id>/` |
| `title`, `main_library` | read from `h5p.json` (e.g. `H5P.InteractiveVideo`) |
| `size_bytes`, `uploaded_by`, `uploaded_at` | |

`Resource` gains `h5p_self_complete` (bool): learners mark it done themselves. Default on upload: true when the main library is a type that never reports completion (Accordion, Dialog Cards, Image Hotspots, Timeline, Agamotto, Collage, …), false otherwise (question types, Question Set, Interactive Video, Course Presentation). The author ticks it for a Course Presentation or Interactive Video that contains no questions.

### Upload checks

- Only course authors, co-editors, AIDEA partners and admins (as for other course files).
- File ≤ 100 MB; total uncompressed ≤ 300 MB (zip-bomb guard).
- A valid zip containing `h5p.json` and `content/content.json`.
- Every entry's extension on H5P's allowed list (images, audio/video, fonts, documents, library JS/CSS, JSON, text); anything else → rejected.
- No entry may resolve outside its target folder (zip-slip).
- The libraries the content needs (main library + preloaded dependencies from `h5p.json`) must be inside the file; otherwise: "This file doesn't include its H5P libraries — export it again with libraries included."
- Clear error messages in the author's language.

## Learner experience

- The activity page shows the H5P resource like any other: header, the activity, done tick.
- The activity runs in an iframe loading `/h5p/player.html` (shipped with the frontend, containing h5p-standalone) with `sandbox="allow-scripts allow-popups allow-forms"` (**no** `allow-same-origin`) and `allow="fullscreen"`.
- The player loads the package from `/media/h5p/<id>/`, listens to H5P's xAPI events and posts them, plus its height, to the parent with `postMessage`. The parent accepts messages only from that iframe's window.
- Because the sandboxed frame has an opaque origin, Caddy adds `Access-Control-Allow-Origin: *` for `/media/h5p/*`. Files are public by unguessable URL, like uploaded PDFs today.
- Package choice: the learner's interface language version if present, else the main file.
- Done: automatically on the first "finished" statement; or a **Mark as done** button when `h5p_self_complete` is on.
- Load failure → "This activity could not be loaded" for the learner; the error is recorded.

## Data captured

Two xAPI statement kinds are kept (others, e.g. "interacted", "paused", are ignored):

| Event type | Data |
|---|---|
| `h5p_answer` (per question answered) | question text, learner response, correct (bool or null), score raw / max, seconds, attempt number, sub-content id |
| `h5p_attempt` (per finished attempt) | score raw / max, passed (bool or null), duration seconds, attempt number, language version, package id |

- Sent through the existing tracking (`POST /api/tracking/`) as `LearningEvent`s with browser-made keys (stored once); text fields cleaned (control characters removed) and length-limited (question 500, response 500 chars).
- The **first finished attempt** completes the resource through the normal completion path (`record_resource_completion`): `ResourceProgress.quiz_score` = raw ÷ max (or null when the activity has no maximum), `engagement_data.h5p` = that attempt's summary. Progress and course % update; a score below the quiz pass threshold makes the learner *stuck*.
- H5P scores do **not** change competency (only quizzes can, today).
- Scores come from the learner's browser; a determined learner could fake them with developer tools — acceptable for research and course improvement, not for certification.

## Analytics and Excel

- **Content tab** notes for H5P resources: finished count, average first-attempt score %, average attempts, hardest question (lowest % correct).
- **Learner timeline**: first score, the list of attempts (score, duration, language), and each answer with right/wrong and seconds.
- **Excel**: the Resources sheet's "Quiz score %" becomes **"Score %"** (quiz and H5P) and gains **"H5P attempts"**; a new **"H5P answers"** sheet (learner × attempt × question: course, learner and item IDs, attempt #, question, response, right?, points, max, seconds, answered at); both event types appear in Events; README updated.

## Privacy

Privacy Policy section 11 adds "answers and scores in interactive H5P activities" to what is recorded. Same visibility and retention as other learning records.

## Rollout

One migration (the `H5PPackage` table, `Resource.h5p_self_complete`, the new type). h5p-standalone files ship in the frontend build. One Caddy header for `/media/h5p/`. Existing courses are unaffected.

## Testing

- **Backend:** upload accepts a valid package and rejects each failure (no `h5p.json`, missing libraries, bad extension, zip-slip, too large, too large unpacked); replacing and removing language versions; language version chosen for a learner; statements stored once; first finished attempt completes and scores; later attempts don't change the score; low score → stuck; self-complete types; analytics notes, timeline, Excel columns and H5P answers sheet; tracking rejects malformed H5P data.
- **Frontend:** lint, unit tests for the xAPI → event mapping, build, locale parity.
- **Manual (browser):** Question Set, Interactive Video, Drag and Drop, Accordion; the iframe cannot read AIDEA's storage; resizing and fullscreen work; Greek UI picks the Greek version when present.

## Out of scope

Creating or editing H5P on AIDEA; links/embeds from other sites, PhET or other simulations; machine translation of H5P content; H5P affecting competency; server-side score verification.
