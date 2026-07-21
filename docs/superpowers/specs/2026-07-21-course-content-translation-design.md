# Course-Content Translation (Phase 2) — Design

Approved decisions (user, 2026-07-21): on-demand translation per language;
per-course source language; JSON `translations` field per model; engine is
the user's self-hosted Ollama (`gemma3-translator`) reached via an autossh
SSH-tunnel sidecar. Builds on Phase 1 (UserProfile.language, 9 languages:
en/el/fr/es/it/fi/sv/no/de). See [[aidea-multilingual-plan]].

## Ollama connection (infra)

- New compose service `ollama-tunnel` (custom minimal image: alpine +
  autossh + openssh-client) holding
  `autossh -M 0 -N -o ServerAliveInterval=30 -o ExitOnForwardFailure=yes
  -o StrictHostKeyChecking=accept-new -i /keys/id_ed25519
  -L 0.0.0.0:11434:127.0.0.1:11434 ${SSH_REMOTE_USER}@${SSH_REMOTE_HOST}`.
  Private key mounted read-only from `docker/ollama-tunnel/keys/` (git-ignored).
  Deploy-time ops (user): generate keypair, add public key to the NTUA box's
  authorized_keys, drop the private key in that folder.
- `backend/hub/translation.py`: `translate_text(text, source, target) -> str`.
  POSTs to `${OLLAMA_URL}/api/generate` (default `http://ollama-tunnel:11434`)
  with model `${OLLAMA_MODEL}` (default `gemma3-translator`), `stream: false`,
  a strict prompt ("Translate from <source-name> to <target-name>. Output only
  the translation, no notes."), a timeout, stdlib `urllib` (no new dep).
  Empty/whitespace input returns unchanged. Network/HTTP/timeout errors raise
  a `TranslationError`. Fully mockable — tests never hit Ollama.
- Env on backend + celery services: `OLLAMA_URL`, `OLLAMA_MODEL`. Documented
  in `.env.example`.

## Data model

- `Course.source_language` (CharField, 9-lang choices, default `en`).
- `translations` JSONField (default `dict`) on **Course**, **Module**,
  **Lesson**: `{ "<lang>": { "<field>": <value>, ... } }`.
  - Course fields: `title`, `description`, `learning_outcomes` (list).
  - Module fields: `title`, `description`.
  - Lesson fields: `title`, `description`, `content`, `quiz_data` (same
    structure; only question + option `text` translated, `is_correct` and
    ordering preserved).
- `Course.translation_status` JSONField (default `dict`):
  `{ "<lang>": "pending" | "done" | "failed" }` for the polling UI.

## Translation flow (on-demand per language)

- `POST /api/authoring/courses/<pk>/translate/ {language}` (author/admin
  scoped via the existing `can_edit_published`-style ownership check;
  `IsContentCreator`). Rejects the course's own `source_language` and
  unknown languages. Sets `translation_status[lang]='pending'`, enqueues
  Celery `translate_course(pk, lang)`, returns the status.
- `translate_course(course_id, target)`: translates every text field of the
  course + its modules + lessons from `course.source_language` → target via
  `translate_text`, writing into each object's `translations[target]`;
  `quiz_data` translated element-by-element. On success sets status `done`;
  on any `TranslationError` sets `failed` and stops. Idempotent (re-running
  overwrites that language).

## Creator override (authoring)

- `CourseAuthoringSerializer` exposes `source_language` (writable),
  `translations`, `translation_status` (read). Authoring module/lesson
  payloads include `translations`.
- Saving translated fields: the existing authoring PATCH endpoints accept an
  optional `?lang=<code>` (or a `translations` sub-object); when present,
  writes land in `translations[lang]` instead of the base fields. Base
  (source-language) fields are edited as today when no lang is given.
- Frontend editors (Course/Module/Lesson) gain a **language dropdown**
  ("English (original) / Ελληνικά / …"), a **Translate to <language>**
  button (POSTs, polls `translation_status`), and — when a translated
  language is selected — the fields become editable translations saved into
  `translations[lang]`. **Re-translate** re-runs the job behind a confirm
  ("overwrites edits in this language"); no per-field edited tracking.

## Learner side

- A helper `localized(obj, field, lang, default)` returns
  `obj.translations.get(lang, {}).get(field)` or the base field. Applied in
  the learner-facing serializers (course list/detail, continue-learning,
  my-learning, lesson learn detail, module/lesson learn, pathway course,
  recommendation) using the requesting user's `profile.language`. Never
  blank — missing translation falls back to the original. `quiz_data`
  resolves to the translated variant when present.

## Out of scope

Pillar names/descriptions (seeded taxonomy), URLs/media/`lesson_type`/
`is_correct`, review gate (auto-translations are live; creators refine),
per-field edited tracking, RTL, translating the Django admin. The SSH key
setup is deploy-time ops.
