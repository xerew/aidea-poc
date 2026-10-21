# Targeted Re-translation and Review Tracking — Design

Date: 2026-10-21 · Status: approved in conversation, awaiting spec review

## Purpose

Today **Re-translate** always redoes the whole course in the open language, overwriting every manual correction. One English edit also drops a Reviewed language back to Done, with nothing showing what changed. Authors want three things:
- re-translate only what they are working on;
- see clearly which translation activity is running;
- know exactly what to re-check after changes, so a review is not lost to a single edit.

### Decisions taken

| Topic | Decision |
|---|---|
| Re-translate scope | **The author chooses each time:** this activity / this module / whole course (module editor); course details / whole course (course editor). Only the open language. |
| Status wording | **"Translating…"** for a (re)translation the author asked for; **"Updating…"** for the automatic sync after an English edit. |
| Review tracking | Each part re-translated **after** the language was marked Reviewed is flagged **"Changed since review"**, and **"corrections replaced"** too if it had been hand-corrected. |
| Reviewed language after changes | **Stays Reviewed**, shown as **"Reviewed · N to re-check"**. Marking Reviewed again clears the list. |
| Hand-corrected part whose English changes | **Re-translated** (learners see current content) **and flagged** for re-check. |
| Empty items | The sync starts only when an item has something to translate (no job for a just-added empty resource). |
| First translation | Unchanged: "Translate to X" translates the whole course. |
| Learners | Unchanged: they always see the current translation, falling back to the original until it exists. |

## Data

- **`translation_flags`** (JSON, default `{}`) on **Course, Module, Activity and Resource**: `{lang: {"edited": bool, "changed": bool, "replaced_edit": bool}}`.
  - **`edited`:** set when that item's translation in `lang` is changed by hand (the existing `PATCH …?lang=` endpoints for course, module, activity and resource).
  - **`changed`:** set when the item is machine-translated in `lang` **while the language has a review on record** (`translation_reviewed_at[lang]` exists).
  - **`replaced_edit`:** set at the same moment when the item was `edited`. `edited` is then cleared.
- **`Course.translation_reviewed_at`** (JSON, default `{}`): `{lang: ISO time}`.
  - Set by "Mark as reviewed"; removed by "Unmark reviewed" and by a whole-course re-translate.
- **Status values in `Course.translation_status[lang]`:**
  - `pending`: a whole-course translation is queued or running.
  - `updating` (new): sync or partial re-translate jobs are running.
  - `done`, `reviewed`, `failed`: as now.

## Behaviour

**Automatic sync** (an English edit, a new module, activity or resource, a copied module, an H5P or presentation upload):
- Runs only when the item has translatable content: a non-empty title, content, caption, instructions, quiz data or description. A just-added empty resource starts nothing.
- For each language that is `done`, `reviewed`, `updating` or `pending`, the language shows `updating` and only that item is re-translated.
- **At the end of each job,** the status becomes `reviewed` when `translation_reviewed_at[lang]` exists, otherwise `done`. `failed` stays as now on errors.
- **The item's flags** are set as in **Data** above.

**Re-translate menu** (only for a language that is `done` or `reviewed`):
- **This activity:** the activity (title, description) and all its resources.
- **This module:** the module (title, description) and all its activities and resources.
- **Course details:** course title, description and learning outcomes.
- These three behave **like the sync**: status `updating`, review kept, items flagged.
- **Whole course…:** as today, plus:
  - status `pending` then `done`;
  - the review record and every flag for that language are cleared (all corrections are overwritten).
- **Confirmation:** each choice asks once and names its scope. When it would overwrite hand-corrected items, the message says how many (e.g. *"…will replace 2 hand-corrected parts in this activity (Greek)"*).

**Mark as reviewed:**
- sets `translation_reviewed_at[lang]`;
- clears `changed` and `replaced_edit` for `lang` on every item of the course;
- status `reviewed`.

**Unmark reviewed:**
- removes `translation_reviewed_at[lang]`;
- status `done`;
- flags cleared.

## API

- `POST /api/authoring/courses/<pk>/translate/` gains optional fields:
  - `scope`: `course` (default) | `details` | `module` | `activity`;
  - `module_id` / `activity_id` as needed.
- **Validation:**
  - partial scopes require the language to be `done` or `reviewed`;
  - the module or activity must belong to the course;
  - otherwise the request gets a 400.
- **Responses:** 202 with `translation_status`.
- `GET /api/authoring/courses/<pk>/translation-changes/?language=xx` lists the items to re-check: `[{kind: course|module|activity|resource, id, title, module_id, activity_id, replaced_edit}]`. Permission: can translate the course.
- **The overwrite count for the confirmation** comes from the same endpoint with `?language=xx&edited=1&scope=…&module_id|activity_id=…`, which counts items with `edited` in that scope.
- **The course and module payloads** used by the editors include `translation_flags`, so badges can show.

## Frontend

- **`TranslationBar`:**
  - status labels `Translating…` (pending) and `Updating…` (updating);
  - **"Reviewed · N to re-check"**, or **"N to re-check"** under Done, when the list for the open language is not empty. Clicking it shows the list, each entry linking to its module editor (with the activity selected);
  - **Re-translate ▾** menu with the scopes allowed on that page;
  - polling treats `updating` like `pending`.
- **Module editor (translating mode):** a "Changed since review" badge on flagged activities and resources (+ "corrections replaced").
- All new strings in the 9 locales.

## Testing

- **Backend:**
  - each scope re-translates only its part, and another module's translation and manual edit stay untouched;
  - a partial scope keeps `reviewed`, while a whole-course scope clears the review and flags;
  - the sync sets `changed`/`replaced_edit` only when a review exists;
  - Mark reviewed clears the flags;
  - an empty new resource starts no job;
  - validation (untranslated language, foreign module or activity, bad scope);
  - `translation-changes` lists the right items, and the `edited` count works;
  - a manual `?lang=` PATCH sets `edited`.
- **Frontend helpers:** menu options per page (no "This activity" without a saved selected activity), status label mapping, re-check count text.

## Out of scope

- Per-item review sign-off (the language-level "Mark as reviewed" stays the only sign-off).
- Keeping old manual corrections instead of re-translating.
- Showing learners whether a translation is reviewed.
- Accuracy of the status while several sync jobs run at once: the status returns to Done/Reviewed when each job ends, as today.
