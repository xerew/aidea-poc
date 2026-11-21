# Per-user activity page — Design

Date: 2026-11-21 · Status: approved in chat, awaiting written-spec review

## Intent

Admins want to see what each person does on the platform. Today:
- **Learning is recorded** per person: resource visits, time, interactions, progress, quizzes, H5P, assignments, competency.
- **It can only be seen per course,** in Analytics → course → Learners.
- **Some activity is anonymous or missing:** navigation outside courses is anonymous in Matomo, logins aren't recorded (only the last one), and several platform actions leave no trace.

**Goal:** from the admin Users table, an admin opens one page per person showing everything that person does on the platform:
- learning;
- authoring;
- reviewing;
- logins;
- navigation (via Matomo).

They can download all of it as one Excel workbook.

## Decisions (from the user)

| Topic | Decision |
|---|---|
| Page parts | Summary, courses & progress, authoring, activity feed (whole platform, incl. authoring), login history |
| Login record | Time + device type + browser name. **No IP address.** |
| Login retention | 12 months; older records deleted nightly |
| Matomo | Send the internal user number (never name/email); page links to Matomo's visit log for that person. No Matomo token stored in AIDEA. |
| Export | One Excel workbook with all of the person's data |
| Who sees it | Admins only |

## Goals

1. **Admin Users table:** an **Activity** button on every row opens `/admin/users/<id>/activity`, an admin-only page.
2. **The page shows:**
   - **Summary:**
     - name, @username, email, role;
     - joined date and last login;
     - onboarding completed;
     - AI competency score/level;
     - total learning time;
     - number of logins in the last 30 days;
     - an **Open in Matomo** link (only when Matomo is configured).
   - **Courses as a learner:**
     - each enrollment: course title, pillar, progress %, active time, status (completed / on track / stuck / inactive, the same rule as Analytics), enrolled date, last activity;
     - clicking a row opens the existing per-course timeline for that person (`/analytics/courses/<course>?learner=<user>`).
   - **Authoring:**
     - courses the person created, co-edits or translates (role, published or draft);
     - their number of recorded edits per course.
   - **Activity feed:**
     - one chronological list, newest first, across the whole platform;
     - filters: All · Learning · Authoring · Reviews · Account (logins, messages, feedback, access requests);
     - 50 items per load, with a **Load more** button.
   - **Login history:** the last 12 months, newest first, with time, device and browser.
   - **Download Excel:** sheets Summary, Courses, Authoring, Activity (the complete feed, not paged), Logins.
3. **Login records:**
   - a successful sign-in (`POST /api/auth/login/`) or registration (which signs the person in) stores a `LoginRecord`;
   - a token refresh is **not** a login;
   - a nightly Celery beat job deletes records older than 365 days.
4. **Platform actions log:**
   - a small `PlatformAction` model records actions that leave no trace today, **from the deploy onwards** (earlier ones can't be recovered):
     - translation requested;
     - resource edited;
     - resource deleted;
     - course deleted;
     - collaborator added;
     - collaborator removed;
     - role changed (who changed whose role);
     - AI reviewer set-up saved;
     - pathways rebuilt.
   - It is kept like the rest of the learning data (no automatic deletion).
5. **Matomo:**
   - after sign-in, and on every page load while signed in, the tracker sets `userId` to the internal user number;
   - on logout it calls `resetUserId`;
   - the **Open in Matomo** link opens Matomo's Visits Log filtered with `segment=userId==<id>`;
   - Matomo only links visits to people from the deploy onwards.

## Feed sources and items

Each item has `at` (time), `category` (learning / authoring / reviews / account), `kind`, a short `text`, and an optional `course` (id and title) plus `link`.

| Source (existing unless marked new) | Item(s) | Category |
|---|---|---|
| `ResourceVisit` grouped by `page_key` | "Studied *activity* in *course*: N min" (sum of active seconds; time = first visit start) | learning |
| `LearningEvent` | video finished, PDF/presentation downloaded, H5P attempt finished (score if present), H5P failed to load. Excluded: play/pause/seek/PDF open/image open/single quiz and H5P answers (they stay in the course timeline). | learning |
| `Enrollment` | enrolled in *course* (`enrolled_at`); completed *course* (`completed_at`) | learning |
| `AssignmentSubmission` (as learner) | submitted an assignment in *course* | learning |
| `AssignmentSubmission.reviewed_by` | reviewed an assignment by *learner* in *course* (approved / changes requested) | reviews |
| `CompetencyChange` | AI competency changed from `old_score` to `new_score` (course title when set) | learning |
| `CourseView` | opened the *course* page | learning |
| `CourseEditHistory.editor` | created / edited / published / unpublished / imported *course*; added/edited/deleted/reordered modules and activities; added resources; uploaded a presentation | authoring |
| `PathwayCourseChange.changed_by` | published / unpublished *course* (pathway list) — **only when no `CourseEditHistory` row for the same course and change exists within 5 seconds**, to avoid duplicates | authoring |
| `PlatformAction` (new) | the actions listed in Goal 4 | authoring (translation, resource, course, collaborator, AI reviewer); account (role changed, pathways rebuilt) |
| `Message.sender` | sent a message (no content, no recipient) | account |
| `Feedback` | sent feedback | account |
| `AccessRequest` | requested content-creator access | account |
| `LoginRecord` (new) | signed in (device, browser) | account |

**Paging:**
- the feed endpoint takes `?before=<ISO time>&category=<c>` and returns the next 50 items plus `next_before`;
- each source is queried with `at < before`, ordered by time and limited to 50, then everything is merged and cut to 50;
- this way no source is loaded in full.

## API

All endpoints are admin-only (`IsAdmin`); any other user gets 403, and an unknown user id gets 404.

- `GET /api/admin/users/<id>/activity/` returns:
  - `summary`
  - `courses`
  - `authoring`
  - `logins`: the last 12 months, at most 500
  - `feed`: the first page
  - `next_before`
- `GET /api/admin/users/<id>/activity/feed/?before=&category=` returns:
  - `items`
  - `next_before`
- `GET /api/admin/users/<id>/activity/export/` returns the `.xlsx` file, named `<username>-activity.xlsx`.

## Data model (new)

- `LoginRecord(user FK CASCADE, at auto_now_add, device: desktop|tablet|mobile|"" , browser: short name ≤ 40)`, indexed on `(user, at)`.
  - Device and browser come from the `User-Agent` header by simple matching, with no new dependency:
    - device: "iPad" or "Tablet" means tablet; "Mobi", "Android" or "iPhone" means mobile; anything else is desktop;
    - browser: Edge, Opera, Firefox, Chrome, Safari or Other, checked in that order.
- `PlatformAction(user FK CASCADE, at auto_now_add, kind: TextChoices, course FK SET_NULL null, label CharField ≤ 255 snapshot, details JSON)`, indexed on `(user, at)`.
  - The `label` keeps the course or resource title, so the item still reads correctly after a deletion.
- Recording uses one helper per model: `record_login(request, user)` and `record_action(user, kind, course=None, label='', **details)`.
  - Both are best-effort: a failure is logged and never breaks the request.

## Frontend

- **Admin Users table:** a new last column holds an **Activity** button, a link to `/admin/users/<id>/activity`.
- **New route:** `/admin/users/:id/activity`, behind `AdminRoute`, rendering `UserActivityPage` (with its own CSS file).
- **Analytics course page:** reads `?learner=<id>` and opens that person's timeline directly.
- **The Matomo link** comes from a pure helper `matomoVisitorLogUrl(env, userId)`, built from `VITE_MATOMO_URL` and `VITE_MATOMO_SITE_ID`. It returns null when either is missing.
- **The tracker:** `analytics.js` gains `setAnalyticsUser(id | null)`.
  - It's called with the user's id after login and on start-up when signed in, and with null on logout.
  - It does nothing when Matomo isn't the provider.
- **Languages:** all new text in the 9 locales.
- **Icons:** lucide-react.

## Non-goals

- Live or real-time views, and charts.
- Recording page navigation inside AIDEA itself (Matomo does that).
- IP addresses or locations.
- Message contents.
- Teachers or creators seeing their own activity page.
- Back-filling logins or platform actions from before the deploy.
- Pulling Matomo data into AIDEA.

## Privacy

- **Privacy notice:** the platform owner updates it to say that logins (time, device, browser) are kept for 12 months, that platform actions are recorded, and that Matomo links visits to a pseudonymous user number.
- **Access:** only admins can open the page or the export.

## Testing

- **Backend:**
  - login records are created by login and register, not by refresh;
  - the device and browser parsing;
  - the nightly deletion keeps records up to 365 days old and deletes older ones;
  - every `PlatformAction` hook writes its row;
  - the feed has the right category and text for each source, paging with `before`, the category filter, and no duplicate publish rows;
  - a non-admin gets 403 and an unknown user 404;
  - the export has 5 sheets with the expected headers and rows.
- **Frontend (node tests):**
  - `matomoVisitorLogUrl`;
  - the `?learner=` parsing helper;
  - every new locale key in all 9 locales.
- **Manual:** open the page in a browser for a teacher and for a content creator.
