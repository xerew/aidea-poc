# Per-user Activity Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admins open one page per user, from the admin Users table, that shows everything the user does on the platform (summary, courses, authoring, activity feed, logins) and can be downloaded as Excel.

**Architecture:**
- **New records:** two models (`LoginRecord`, `PlatformAction`) record what has no trace today.
- **`hub/user_activity.py`** merges them with the existing tables into one feed plus a summary, courses and authoring.
- **Admin-only views** serve them as JSON and `.xlsx`.
- **The React page** renders it and links into the existing per-course learner timeline and Matomo.

**Tech Stack:** Django 5 + DRF, Celery beat, openpyxl, React 19 + react-router 7 + react-i18next, node:test.

**Spec:** `docs/superpowers/specs/2026-11-21-user-activity-page-design.md`

## Global Constraints

- **Access:** admins only, via `IsAdmin` from `hub/views/permissions.py`. A non-admin gets 403 and an unknown user 404.
- **Login records:**
  - fields: time, `device` in `desktop|tablet|mobile|""`, `browser` in `Edge|Opera|Firefox|Chrome|Safari|Other`;
  - **no IP address;**
  - created on `POST /api/auth/login/` and on registration, **not** on token refresh;
  - deleted when older than **365 days**, by a nightly beat job.
- **`PlatformAction` kinds:** `translation_requested`, `resource_edited`, `resource_deleted`, `course_deleted`, `collaborator_added`, `collaborator_removed`, `role_changed`, `ai_review_saved`, `pathways_rebuilt`.
- **Recording is best-effort:** a failure is logged with `logger.warning` and never breaks the request.
- **Feed:**
  - newest first, **50** items per page;
  - `?before=<ISO>&category=<learning|authoring|reviews|account>`;
  - learning visits grouped by `page_key`;
  - excluded events: video play/pause/seek, PDF open, image open, single quiz/H5P answers;
  - message items carry **no content and no recipient**.
- **Matomo:**
  - receives only the internal user id (`String(user.id)`), with `resetUserId` on logout;
  - the visitor-log link uses `segment=userId==<id>`;
  - it is hidden unless both `VITE_MATOMO_URL` and `VITE_MATOMO_SITE_ID` are set.
- **Excel export:** file name `<username>-activity.xlsx`; sheets `Summary`, `Courses`, `Authoring`, `Activity`, `Logins`; the Activity sheet has the full feed, not paged.
- **Frontend:** all new text in all 9 locales (en, el, fr, es, it, fi, sv, no, de); icons from `lucide-react`; per-component CSS files.
- **Runners:**
  - backend, from `backend/`: `"/c/Users/Nikos A. Grammatikos/.local/bin/uv.exe" run manage.py test hub.tests.<module>`;
  - frontend, from `frontend/`: `npm test`, `npm run lint`, `VITE_API_URL=http://localhost:8000/api npm run build`.
- **Commits:** on `master`, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Decisions this plan adds to the spec

- **Feed item shape:**
  ```
  {at, category, kind, params: {...}, text, course: {id, title} | null}
  ```
  - `text` is plain English, used by the Excel export.
  - The page renders `t('admin.activity.kinds.<kind>', params)`, so the 9 languages work.
- **`CourseEditHistory` rows:** the kind is `edit_<key>` when the row's single key is one of `course_created`, `course_published`, `course_unpublished`, `course_imported`, `module_added`, `module_edited`, `module_deleted`, `modules_reordered`, `module_imported`, `lesson_added`, `lesson_edited`, `lesson_deleted`, `lessons_reordered`, `resource_added`, `presentation_uploaded`. Anything else (field diffs) becomes `edit_course_edited`.
- **Page boundary:**
  - after cutting to 50, also include every remaining item with the **same `at`** as the last one;
  - `next_before` is that `at`, and the next page uses `at < before`;
  - so items sharing a timestamp are never split or lost.

## Review Focus

1. **Items sharing the timestamp at a page boundary** must all appear exactly once, across the two pages. Pinned in Task 3.
2. **A user without a `UserProfile`** (e.g. a `createsuperuser` account) opens without a crash; the summary shows an empty role and level. Pinned in Task 4.
3. **A missing or empty `User-Agent`** gives device `""` and browser `Other`, and the login is still recorded. Pinned in Task 1.
4. **Text in the export starting with `= + - @`** (course titles, names) is stored as text, not a formula. Pinned in Task 5.
5. **Items about a deleted course** (`PlatformAction` with course set to null) still show the title from `label`. Pinned in Task 3.

---

### Task 1: Login records

**Files:**
- Create: `backend/hub/models/activity_log.py` (`LoginRecord`; `PlatformAction` comes in Task 2)
- Create: `backend/hub/activity_log.py`
- Modify:
  - `backend/hub/models/__init__.py`: export `LoginRecord`;
  - `backend/hub/views/auth.py`: `LoginView.post`, `RegisterView.post`;
  - `backend/hub/tasks.py`: add a task;
  - `backend/aidea/settings.py`: `CELERY_BEAT_SCHEDULE`;
  - `backend/hub/admin.py`: register `LoginRecord`, read-only.
- Migration: `0074_login_record`
- Test: `backend/hub/tests/test_activity_log.py`

**Interfaces:**
- Produces:
  - `parse_user_agent(ua: str | None) -> tuple[str, str]` (device, browser);
  - `record_login(request, user) -> None`;
  - task `delete_old_login_records() -> int` (number deleted);
  - model `LoginRecord(user, at, device, browser)`, with `at` set by `auto_now_add`, `Meta.ordering = ['-at']`, and an index on `(user, at)`.

- [ ] **Step 1: Write the failing tests** in `test_activity_log.py`, class `LoginRecordTests(APITestCase)`:
  - `test_parse_user_agent` checks these cases:
    - an iPhone Safari UA → `('mobile','Safari')`;
    - an Android Chrome Mobile UA → `('mobile','Chrome')`;
    - an iPad UA → `('tablet','Safari')`;
    - Windows Edge (`Edg/`) → `('desktop','Edge')`;
    - Windows Firefox → `('desktop','Firefox')`;
    - `OPR/` → `('desktop','Opera')`;
    - `''` and `None` → `('', 'Other')`.
  - `test_login_is_recorded`: POST `auth-login` with valid credentials and `HTTP_USER_AGENT` set to an iPhone UA. Expect status 200 and one `LoginRecord`, with `device == 'mobile'`.
  - `test_failed_login_is_not_recorded`: a wrong password gives 401 and 0 records.
  - `test_register_is_recorded`: posting to the register endpoint with the payload the existing register tests use gives 1 record.
  - `test_refresh_is_not_a_login`: log in, then POST `auth-refresh` with the refresh token. The count stays at 1.
  - `test_missing_user_agent_still_recorded`: log in without a UA header. Expect 1 record with `device == ''` and `browser == 'Other'`.
  - `test_old_records_deleted`:
    - create three records, then set their `at` with `update()` to now − 366 days, now − 365 days + 1 hour, and now;
    - `delete_old_login_records()` returns 1, and 2 records remain.

- [ ] **Step 2: Run** `... test hub.tests.test_activity_log`. Expected: an ImportError or FAIL for every test.

- [ ] **Step 3: Implement.**
  - **`parse_user_agent`** uses plain substring checks, in this order:
    - device: `iPad` or `Tablet` → tablet; `Mobi`, `Android` or `iPhone` → mobile; an empty UA → `''`; anything else → desktop;
    - browser: `Edg/` → Edge; `OPR/` or `Opera` → Opera; `Firefox/` → Firefox; `Chrome/` → Chrome; `Safari/` → Safari; anything else → Other.
  - **`record_login`** wraps creation in `try/except Exception` and logs a warning.
  - **Hooks:**
    - in `LoginView.post`: call `super().post`, and if the status is 200, look up the user by `request.data['username']` and record the login;
    - in `RegisterView.post`: record after the user is created.
  - **Nightly job:** add `'delete-old-login-records': {'task': 'hub.tasks.delete_old_login_records', 'schedule': crontab(hour=4, minute=30)}` to the beat schedule.

- [ ] **Step 4: Run** the same command. Expected: all PASS. Then run `ruff check .`. Expected: `All checks passed!`

- [ ] **Step 5: Commit** with `feat: record logins (time, device, browser) and delete them after 12 months`.

### Task 2: Platform actions log

**Files:**
- Modify:
  - `backend/hub/models/activity_log.py`: add `PlatformAction`;
  - `backend/hub/models/__init__.py`;
  - `backend/hub/activity_log.py`: add `record_action`;
  - `backend/hub/admin.py`: register `PlatformAction`, read-only.
- Hook points:

  | Kind | File and place |
  |---|---|
  | `translation_requested` | `backend/hub/views/authoring_course.py`, `AuthoringCourseTranslateView.post` |
  | `course_deleted` | the same file, course delete view (before `course.delete()`, with `course=None`, `label=course.title`) |
  | `resource_edited` | `backend/hub/views/authoring_resource.py`, `AuthoringResourceDetailView.patch` |
  | `resource_deleted` | the same view's `delete` |
  | `collaborator_added` | `backend/hub/views/collaborators.py`, `post` (only when the role is new or changed, the same condition as the email) |
  | `collaborator_removed` | the same file, detail `delete` |
  | `role_changed` | `backend/hub/views/admin.py`, `AdminUserRoleView.patch` |
  | `pathways_rebuilt` | the same file, `AdminPathwaysRebuildView.post` |
  | `ai_review_saved` | `backend/hub/views/ai_review.py`, `AuthoringAIReviewView.put` |

- Migration: `0075_platform_action`
- Test: `backend/hub/tests/test_activity_log.py`

**Interfaces:**
- Produces:
  - `PlatformAction(user, at, kind, course FK SET_NULL null, label ≤255, details JSON)` with `Kind` TextChoices holding exactly the 9 kinds in Global Constraints, `ordering ['-at']` and an index on `(user, at)`;
  - `record_action(user, kind, course=None, label='', **details) -> None` (best-effort).
- `details` keys per kind:

  | Kind | `details` |
  |---|---|
  | `translation_requested` | `{language, scope}` |
  | `resource_edited`, `resource_deleted` | `{resource_title, resource_type}` |
  | `collaborator_added` | `{collaborator: username, role}` |
  | `collaborator_removed` | `{collaborator: username}` |
  | `role_changed` | `{target: username, old_role, new_role}` |
  | `pathways_rebuilt` | `{applied: n}` |
  | `ai_review_saved` | `{resource_title}` |

  `label` is the course title, or the target username for `role_changed`.

- [ ] **Step 1: Write failing tests** in class `PlatformActionTests`, one test per hook. Each calls the endpoint the way its existing test module does, reusing those fixtures where they're importable (`AuthoringTestCase` from `test_authoring_courses`, `make_assignment` from `test_ai_review_models`), and asserts that exactly one `PlatformAction` row exists with the expected `kind`, `user`, `label` and the `details` keys above. Also:
  - `test_course_deleted_keeps_title`: after deleting, the row's `course` is `None` and `label` is the old title;
  - `test_recording_failure_never_breaks_request`: patch `PlatformAction.objects.create` to raise; the endpoint still returns its normal status.

- [ ] **Step 2: Run** `... test hub.tests.test_activity_log`. Expected: the new tests FAIL.

- [ ] **Step 3: Implement** the model, `record_action` and the hooks. Each hook goes after the change succeeds (after `save`/`delete` and before `return`). Generate the migration with `makemigrations hub -n platform_action`.

- [ ] **Step 4: Run** the module, then the whole `hub` suite with `--parallel 4`. Expected: all OK.

- [ ] **Step 5: Commit** with `feat: log platform actions that left no trace (translations, resource edits, deletes, collaborators, roles, AI reviewer, pathway rebuilds)`.

### Task 3: Activity feed builder

**Files:**
- Create: `backend/hub/user_activity.py`
- Test: `backend/hub/tests/test_user_activity.py`

**Interfaces:**
- Consumes: `LoginRecord`, `PlatformAction` (Tasks 1–2); the existing models `ResourceVisit`, `LearningEvent`, `Enrollment`, `AssignmentSubmission` (`user`, `submitted_at`, `reviewed_by`, `reviewed_at`, `status`, `lesson`), `CompetencyChange`, `CourseView`, `CourseEditHistory` (`editor`, `edited_at`, `changes`), `PathwayCourseChange` (`changed_by`), `Message` (`sender`, `created_at`), `Feedback` (`user`, `created_at`), `AccessRequest` (`user`, `created_at`).
- Produces:
  - `FEED_PAGE = 50`;
  - `CATEGORIES = ('learning', 'authoring', 'reviews', 'account')`;
  - `feed(user, before: datetime | None = None, category: str | None = None, limit: int | None = FEED_PAGE) -> tuple[list[dict], datetime | None]`, which returns `(items, next_before)`. `limit=None` returns everything (for the export) with `next_before=None`;
  - the item dict: `{'at', 'category', 'kind', 'params', 'text', 'course'}`.
- Kinds by category:
  - **learning:** `studied` (params `activity`, `minutes`), `video_finished`, `file_downloaded` (`file_type`: pdf/presentation), `h5p_attempt` (`score`, `max_score` when present), `h5p_error`, `enrolled`, `completed`, `assignment_submitted`, `competency_changed` (`old`, `new`), `course_viewed`;
  - **reviews:** `assignment_reviewed` (`learner`, `outcome`: approved / changes_requested);
  - **authoring:** `edit_<key>` (see "Decisions"), `pathway_published`, `pathway_unpublished`, plus the 7 authoring `PlatformAction` kinds (`translation_requested`, `resource_edited`, `resource_deleted`, `course_deleted`, `collaborator_added`, `collaborator_removed`, `ai_review_saved`);
  - **account:** `role_changed`, `pathways_rebuilt`, `message_sent`, `feedback_sent`, `access_requested`, `signed_in` (`device`, `browser`).

- [ ] **Step 1: Write failing tests** in class `FeedTests(TestCase)`. Each builds rows for one user (plus a second user whose rows must never appear):
  - `test_visits_grouped_per_page`: three `ResourceVisit`s share one `page_key`, with 120+60+60 active seconds. Expect one `studied` item with `params['minutes'] == 4` and its `at` equal to the earliest `started_at`.
  - `test_noise_events_excluded`: `video_play`, `video_seek`, `pdf_open` and `quiz_answer` events produce no items; `video_ended` and `pdf_download` produce `video_finished` and `file_downloaded`.
  - `test_each_source_has_its_category`: one row per source gives the expected `(category, kind)` pairs.
  - `test_review_done_by_user`: a submission by learner B, reviewed by the user, shows as `assignment_reviewed` with `params['learner']` set to B's display name. B's own submission is not in the user's feed.
  - `test_publish_not_duplicated`: a `CourseEditHistory` row `course_published` and a `PathwayCourseChange` row (published, same course, same user, 2 s apart) give exactly one item, `edit_course_published`.
  - `test_message_has_no_content_or_recipient`: the `message_sent` item's `params == {}` and its `text == 'Sent a message'`.
  - `test_deleted_course_uses_label`: a `PlatformAction` with `course=None` and `label='Old course'` gives an item whose text contains `Old course` and whose `course` is `None`.
  - `test_category_filter`: `category='account'` returns only account items.
  - `test_paging`: 120 `LoginRecord`s with distinct times. Page 1 has 50 items, newest first; page 2 (`before=next_before`) has the next 50; page 3 has 20 and `next_before is None`.
  - `test_same_timestamp_at_boundary` (Review Focus 1): 49 logins at distinct times plus 3 logins sharing the 50th timestamp. Page 1 has 52 items, page 2 has the rest, and no item repeats.
  - `test_limit_none_returns_everything`: `feed(user, limit=None)` returns all items and `None`.

- [ ] **Step 2: Run** `... test hub.tests.test_user_activity`. Expected: ImportError.

- [ ] **Step 3: Implement `feed`.**
  - **One function per source**, each `(user, before, n) -> list[dict]`. Each applies `at < before` when `before` is given, orders newest first, and slices `[:n]` when `n` is not None.
  - **Visit grouping in the database:**
    ```python
    .values('page_key','activity_id','course_id')
    .annotate(at=Min('started_at'), active=Sum('active_seconds'))
    ```
    then filter on `at` and order by `-at`.
  - **Publish de-duplication:** drop a `PathwayCourseChange` item when the same user has a `CourseEditHistory` row with `course_published`/`course_unpublished` for that course within 5 seconds.
  - **Merging:** merge all sources, sort by `at` descending, cut to `limit`, then add the remaining items equal to the last `at` (see "Decisions").
  - **`next_before`:** the last item's `at` when more items exist, else `None`.
  - **Category filter:** skip sources that can't produce the requested category.

- [ ] **Step 4: Run** the module. Expected: all PASS.

- [ ] **Step 5: Commit** with `feat: one activity feed per user across learning, authoring, reviews and account`.

### Task 4: Activity API (summary, courses, authoring, logins, feed pages)

**Files:**
- Modify:
  - `backend/hub/user_activity.py`: add `summary`, `course_rows`, `authoring_rows`, `login_rows`;
  - `backend/hub/urls.py`, `backend/hub/views/__init__.py`;
  - `CLAUDE.md`: list the 3 endpoints under API endpoints.
- Create: `backend/hub/views/admin_user_activity.py`
- Test: `backend/hub/tests/test_user_activity.py`

**Interfaces:**
- Consumes: `feed` (Task 3); `analytics.learning.CourseData`, `learner_row(cd, enrollment)` (returns `progress_pct`, `active_s`, `status`, `last_active`, `enrolled_at`, `completed_at`); `CourseCollaborator`; `CourseEditHistory`.
- Produces:
  - `summary(user) -> dict` with keys `id`, `name`, `username`, `email`, `role` (`''` without a profile), `joined`, `last_login`, `onboarding_completed`, `competency_score` (`None` without a profile), `total_active_s`, `logins_30d`;
  - `course_rows(user) -> list[dict]` with keys `course_id`, `title`, `pillar`, `progress_pct`, `active_s`, `status`, `enrolled_at`, `last_active`, `completed_at`;
  - `authoring_rows(user) -> list[dict]` with keys `course_id`, `title`, `role` (author / co_editor / translator), `is_published`, `edits` (that user's `CourseEditHistory` count for the course);
  - `login_rows(user) -> list[dict]` with keys `at`, `device`, `browser`: the last 365 days, at most 500, newest first;
  - URL names: `admin-user-activity` (`admin/users/<int:pk>/activity/`), `admin-user-activity-feed` (`…/activity/feed/`), `admin-user-activity-export` (`…/activity/export/`, in Task 5).
- Response of `admin-user-activity`: `{summary, courses, authoring, logins, feed, next_before}`.
- Response of the feed endpoint: `{items, next_before}`.
  - An invalid `before` returns 400 with `{'detail': 'Invalid before.'}`.
  - An unknown `category` returns 400.

- [ ] **Step 1: Write failing tests** in class `ActivityApiTests(APITestCase)`:
  - `test_admin_gets_all_sections`: the six keys exist; `courses[0]['status']` equals what `learner_row` gives for that enrollment.
  - `test_authoring_roles`: the user authors course A and co-edits course B. Expect two rows with roles `author` and `co_editor`, and `edits` counts that match.
  - `test_feed_endpoint_pages`: following `next_before` returns the next page.
  - `test_bad_params_400`: `before=nonsense` and `category=x` each give 400.
  - `test_non_admin_403_unknown_404`: a content creator gets 403; an admin asking for an unknown id gets 404.
  - `test_user_without_profile` (Review Focus 2): `User.objects.create_user('noprof')` gives 200, `summary['role'] == ''` and `summary['competency_score'] is None`.

- [ ] **Step 2: Run.** Expected: FAIL (NoReverseMatch).

- [ ] **Step 3: Implement** the helpers and two `APIView`s with `permission_classes = [IsAdmin]`. Look the user up with `User.objects.filter(pk=pk).first()` and return 404 when it's `None`. Parse `before` with `django.utils.dateparse.parse_datetime`.

- [ ] **Step 4: Run** the module, then `ruff check .`. Expected: PASS, `All checks passed!`

- [ ] **Step 5: Commit** with `feat: admin API for a user's activity (summary, courses, authoring, logins, feed)`.

### Task 5: Excel export

**Files:**
- Create: `backend/hub/user_activity_workbook.py`
- Modify:
  - `backend/hub/views/admin_user_activity.py`: add `AdminUserActivityExportView`;
  - `backend/hub/urls.py`.
- Test: `backend/hub/tests/test_user_activity.py`

**Interfaces:**
- Consumes: `summary`, `course_rows`, `authoring_rows`, `login_rows`, `feed(user, limit=None)`; `analytics.workbook._append(ws, row)` (it already neutralises `= + - @` and illegal characters) and `iso(dt)`.
- Produces: `build_user_workbook(user) -> openpyxl.Workbook`.
- Sheets and headers:

  | Sheet | Headers |
  |---|---|
  | `Summary` | two columns, `Field` and `Value`, one row per summary key |
  | `Courses` | Course ID, Course, Pillar, Progress %, Active minutes, Status, Enrolled, Last active, Completed |
  | `Authoring` | Course ID, Course, Role, Published, Edits |
  | `Activity` | Time, Category, Kind, Description, Course ID, Course |
  | `Logins` | Time, Device, Browser |

- The response mirrors `analytics.views._xlsx_response`, with file name `f'{user.username}-activity.xlsx'`.

- [ ] **Step 1: Write failing tests:**
  - `test_export_sheets_and_rows`: the response has the xlsx content type and a `Content-Disposition` containing `<username>-activity.xlsx`. Load it with `openpyxl.load_workbook(BytesIO(res.content))`. The sheet names equal the 5 above, in order. The `Activity` row count equals `len(feed(user, limit=None)[0]) + 1`.
  - `test_formula_text_is_neutralised` (Review Focus 4): a course titled `=HYPERLINK("x")` appears in `Courses` as the string `'=HYPERLINK("x")` (with the leading apostrophe).
  - `test_export_admin_only`: a non-admin gets 403.

- [ ] **Step 2: Run.** Expected: FAIL.

- [ ] **Step 3: Implement** `build_user_workbook` and the view. Bold the header row with the same `Font(bold=True)` the analytics workbook uses.

- [ ] **Step 4: Run** the module, then the full `hub` suite with `--parallel 4`. Expected: all OK.

- [ ] **Step 5: Commit** with `feat: download a user's activity as Excel`.

### Task 6: Matomo user number, Matomo link, and direct learner links

**Files:**
- Modify:
  - `frontend/src/lib/analytics.js`: add `setAnalyticsUser`;
  - `frontend/src/context/AuthContext.jsx`: call it after `login`, `loginSession` and the `/auth/me/` refresh, and with `null` in `logout`;
  - `frontend/src/pages/AnalyticsCoursePage.jsx`: open the learner from `?learner=`.
- Create: `frontend/src/lib/matomoLink.js`, `frontend/src/lib/learnerParam.js`
- Test: `frontend/src/lib/matomoLink.test.js`, `frontend/src/lib/learnerParam.test.js`

**Interfaces:**
- Produces:
  - `setAnalyticsUser(id: number | null) -> void`. It does nothing unless the provider is matomo and `window._paq` exists. Otherwise it pushes `['setUserId', String(id)]`, or `['resetUserId']` for null.
  - `matomoVisitorLogUrl(env, userId) -> string | null`, defined as:
    ```
    `${base}index.php?module=CoreHome&action=index&idSite=${site}&period=year&date=today#?idSite=${site}&period=year&date=today&category=General_Visitors&subcategory=Live_VisitorLog&segment=${encodeURIComponent(`userId==${userId}`)}`
    ```
    `base` is `VITE_MATOMO_URL` trimmed, with a `/` added at the end if missing. It returns null when either env value is blank.
  - `learnerFromSearch(search: string) -> number | null`: a positive integer `learner` parameter, otherwise null.
  - `matomoSetupCommands(base: string, siteId: string) -> Array`, in `frontend/src/lib/matomoSetup.js`: the `_paq` commands that `initMatomo` pushes, in this order: `['disableCookies']`, `['enableLinkTracking']`, `['enableHeartBeatTimer', 15]` (accurate time on every page, including Documentation; added 2026-11-21), `['setTrackerUrl', base + 'matomo.php']`, `['setSiteId', String(siteId)]`. `initMatomo` in `analytics.js` uses it.

- [ ] **Step 1: Write failing node tests.**
  - For `matomoVisitorLogUrl`, using `{VITE_MATOMO_URL: 'https://analytics.aidea-hub.eu', VITE_MATOMO_SITE_ID: '1'}` with user 42:
    - the URL starts with `https://analytics.aidea-hub.eu/index.php?`;
    - it contains `idSite=1`;
    - it contains `segment=userId%3D%3D42`.
  - Missing URL → null; missing site id → null.
  - For `matomoSetupCommands('https://a.example/', '1')`: it deep-equals the five commands above, in order (so the heartbeat stays on and cookies stay off).
  - For `learnerFromSearch`:
    - `'?learner=7'` → 7;
    - `''` → null;
    - `'?learner=abc'` → null;
    - `'?learner=-3'` → null;
    - `'?tab=x&learner=12'` → 12.

- [ ] **Step 2: Run** `npm test`. Expected: the new tests FAIL with ERR_MODULE_NOT_FOUND.

- [ ] **Step 3: Implement** the helpers and wire them in.
  - **`setAnalyticsUser` call sites:** after `setUser(data.user)` in `login` and `loginSession`, when `/auth/me/` returns, and in `logout`.
  - **Analytics course page:** initialise `learnerId` from `learnerFromSearch(location.search)`.

- [ ] **Step 4: Run** `npm test` and `npm run lint`. Expected: all pass, and eslint prints no problems.

- [ ] **Step 5: Commit** with `feat: Matomo knows the user number; direct links to a learner's course timeline`.

### Task 7: User activity page and the admin Users table button

**Files:**
- Create: `frontend/src/pages/UserActivityPage.jsx`, `frontend/src/pages/UserActivityPage.css`
- Modify:
  - `frontend/src/App.jsx`: add the route `/admin/users/:id/activity` with `<AdminRoute element={<UserActivityPage />} />`;
  - `frontend/src/pages/AdminPage.jsx`: in `UsersTab`, add a new last column with the header `t('admin.activity.column')` and a `Link` button (`Activity` icon from lucide-react) to `/admin/users/${u.id}/activity`;
  - all 9 `frontend/src/locales/*.json` files.
- Test: `frontend/src/lib/userActivityLocales.test.js`

**Interfaces:**
- Consumes: `GET /admin/users/<id>/activity/`, `GET …/activity/feed/?before=&category=`, `GET …/activity/export/` (download through `client.get(url, {responseType: 'blob'})`, the same pattern as the existing analytics export button); `matomoVisitorLogUrl(import.meta.env, id)`; course rows link to `/analytics/courses/${course_id}?learner=${id}`.
- Locale keys, all under `admin.activity`:
  - page texts: `column`, `button`, `title`, `back`, `download`, `openMatomo`, `summary`, `courses`, `authoring`, `feed`, `logins`, `loadMore`, `empty`, `noLogins`;
  - filters: `filters.all|learning|authoring|reviews|account`;
  - summary labels: `fields.role|joined|lastLogin|onboarding|competency|totalTime|logins30d`;
  - table headers: `cols.*`, as the page needs;
  - feed items: one `kinds.<kind>` for every kind in Task 3, using i18next interpolation for its params (e.g. `"Studied “{{activity}}” in {{course}} — {{minutes}} min"`).

- [ ] **Step 1: Write the failing locale test.** It hard-codes the full key list above (every `kinds.*`, written out) and asserts that each key is a non-empty string in all 9 locales. It also checks that every `{{param}}` used in the English `kinds.*` value appears in the other 8 languages too.

- [ ] **Step 2: Run** `npm test`. Expected: the locale test FAILs on the first missing key.

- [ ] **Step 3: Implement** the locale texts (9 languages; write the JSON edits with a node script file, not inline shell quoting), the route, the table button and the page.
  - **Page sections, in order:** header (name, @username, role, **Download Excel** button, **Open in Matomo** link when the helper returns a URL), Summary, Courses, Authoring (hidden when empty), Activity feed with the filter chips and **Load more**, Logins.
  - **Dates:** `toLocaleString(i18n.language)`.
  - **Feed lines:** `t('admin.activity.kinds.' + item.kind, {...item.params, course: item.course?.title ?? item.params.course ?? ''})`. Fall back to `item.text` when the key is missing.

- [ ] **Step 4: Run** `npm test`, `npm run lint` and the build. Expected: all pass, and the build prints `built in`.

- [ ] **Step 5: Manual check.** Run the backend and `npm run dev`. As an admin, open Admin → Users → **Activity** for a teacher and for a content creator. Check that the sections render, **Load more** appends items, the filters work, **Download Excel** saves a file, and clicking a course opens that learner's timeline.

- [ ] **Step 6: Commit** with `feat: admin per-user activity page with feed, logins, Matomo link and Excel download`.
