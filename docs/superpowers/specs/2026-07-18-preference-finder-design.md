# Learning Preference Finder — Design

Approved decisions (user): questions managed in the Django admin (seeded
with placeholders, editable without deploys); button lives in the Profile's
Learning Preferences card; result maps to the existing four learning styles.

## Data model

Two new tables (app `hub`), admin-editable with inline options:

- `PreferenceQuestion`: `text` (char 300), `order` (int, list-editable),
  `is_active` (bool, default true). Ordering: `order`.
- `PreferenceOption`: FK `question` (related_name `options`), `text`
  (char 300), `maps_to` (choices = `UserProfile.LearningStyle`:
  video/text/visual/interactive), `order`. Ordering: `order`.

Seeded by `manage.py seed` (idempotent, keyed by question order) with 4
placeholder questions, each carrying one option per style.

## API — `/api/preference-quiz/` (any authenticated user)

- **GET** → active questions in order:
  `[{id, text, options: [{id, text}]}]` — `maps_to` is NOT exposed.
- **POST** `{answers: [{question_id, option_id}]}` →
  validates: non-empty list, every option exists and belongs to an active
  question, at most one answer per question (else 400 `{error}`).
  Tallies `maps_to` across chosen options; winner = highest count, ties
  break toward the first style in the `LearningStyle` declaration order
  (video → text → visual → interactive). Saves
  `profile.learning_style = winner`, triggers
  `compute_user_recommendations`, returns
  `{learning_style, label}`.

Answering fewer questions than exist is allowed (skip = fewer votes).

## UI

In `PreferencesSection` (ProfilePage), under the "Preferred Learning
Format" select: a **"Find your learning preference"** button opening a
modal wizard (`frontend/src/components/PreferenceFinderModal.jsx`):

- Loads questions from GET; one question per step with a progress bar,
  option buttons, Back/Next; Next disabled until an option is chosen
- Final step submits to POST and shows the result ("You learn best with
  **Visual** content") with a Done button
- On completion the parent form's `learning_style` select updates to the
  new value (server already saved it); the user can still override
  manually and press Save Preferences as before
- Empty state: if no active questions exist, the modal says so and closes

## Out of scope

Weighted options, multi-style results, per-question analytics, using the
finder during onboarding.
