# Tester Feedback Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all 20 issues from the AIDEA Platform tester feedback PDF (2026-07): broken logos, invisible button text, wrong redirects, stale-role bugs, quiz feedback, inline PDF/video, authoring fixes, and file upload.

**Architecture:** Monorepo — Django REST backend (`backend/`, apps `hub` + `analytics`) and React 19/Vite SPA (`frontend/`). JWT auth with user data cached in localStorage. Fixes span both sides; several issues share one root cause (stale localStorage user → add `/auth/me/` refresh).

**Tech Stack:** Django 6 + DRF + simplejwt, React 19 + react-router v7 + Axios, Tailwind v4 (via `@import "tailwindcss"`), lucide-react icons, per-page CSS files.

## Global Constraints

- Backend venv runner: `cd backend` then `.venv/Scripts/uv.exe run ...` (bundled uv; system python may be absent). If `.venv/Scripts/uv.exe` is missing, use `%USERPROFILE%\.local\bin\uv.exe run ...` from `backend/`.
- Backend tests: `.venv/Scripts/uv.exe run coverage run manage.py test hub --verbosity=2` (single class: `... test hub.tests.test_foo.TestClass`)
- Backend lint: `.venv/Scripts/uv.exe run ruff check .` (line length 100, E501 ignored; import sorting enforced — run `--fix` for I001)
- Frontend: `cd frontend` then `npm run lint` and `npm run build` must pass (no frontend test framework exists — lint + build is the verification)
- Icons: `lucide-react` only
- Frontend styling: per-component CSS files, no CSS framework classes in JSX beyond existing shadcn/ui components
- All API routes live under `/api/` (`hub/urls.py` unless stated otherwise)
- Do not break existing tests — the CI gate is 70% coverage minimum
- Commit after each task with a conventional-commit message

## Design Decisions (from tester's own suggestions)

- **Issue 13/17:** Published courses become editable by their **author** (`created_by`) or an **admin**; other content creators see read-only. Publish confirm dialog text updated (unpublish already exists).
- **Issue 9:** Per-question quiz feedback via a new server-side check endpoint (correct answers stay out of the lesson payload). Completed quizzes show a review of saved answers instead of allowing re-answering.
- **Issue 3:** After onboarding, land on Home (`/`), not `/pathway`.
- **Issue 6:** Learning preferences become available to any authenticated profile (content creators also learn).
- **Issues 7/8:** Root cause is stale user data in localStorage after a server-side role change. Fix = new `GET /api/auth/me/` + AuthContext refresh on mount.
- **Issue 20:** No reproducible code defect (first-video slowness was the Vite dev server cold-transforming). The video embed (Task 10) changes rendering anyway; no separate task.

---

### Task 1: Local logo assets + EU logo in sidebar (Issue 1)

The sidebar loads the AIDEA logo from `https://aideaacademy.eu/...` which renders as a broken image on the VM (see tester screenshots). The EU co-funding logo only appears on the login page.

**Files:**
- Create: `frontend/public/images/logos/aidea-logo.png` (downloaded)
- Create: `frontend/public/images/logos/eu-cofunded.jpg` (downloaded)
- Modify: `frontend/src/components/layout/Sidebar.jsx`
- Modify: `frontend/src/pages/LoginPage.jsx:34,74`
- Modify: any other file referencing `aideaacademy.eu` (check `RegisterPage.jsx`)
- Modify: `frontend/src/components/layout/Sidebar.css`

**Interfaces:**
- Produces: logo files at `/images/logos/aidea-logo.png` and `/images/logos/eu-cofunded.jpg` served by Vite from `public/`

- [ ] **Step 1: Download both logos into public assets**

```bash
mkdir -p frontend/public/images/logos
curl -L -o frontend/public/images/logos/aidea-logo.png "https://aideaacademy.eu/demo/wp-content/uploads/2026/01/aidea-logo-3-AIdEA-COLORED-162px.png"
curl -L -o frontend/public/images/logos/eu-cofunded.jpg "https://aideaacademy.eu/demo/wp-content/uploads/2026/03/EN-Co-funded-by-the-EU_PANTONE-300x63-1.jpg"
```

Verify both files are non-empty images (`file` or open them). If the download fails (site unreachable), ask the human partner to supply the logo files — do not ship broken references.

- [ ] **Step 2: Replace every remote logo URL with the local path**

Run: `grep -rn "aideaacademy.eu" frontend/src`

In each match (at minimum `LoginPage.jsx` and `Sidebar.jsx`; check `RegisterPage.jsx`):
- `https://aideaacademy.eu/.../aidea-logo-3-AIdEA-COLORED-162px.png` → `/images/logos/aidea-logo.png`
- `https://aideaacademy.eu/.../EN-Co-funded-by-the-EU_PANTONE-300x63-1.jpg` → `/images/logos/eu-cofunded.jpg`

- [ ] **Step 3: Add the EU logo to the sidebar footer**

In `frontend/src/components/layout/Sidebar.jsx`, after the closing `</nav>` and before `</aside>`:

```jsx
      <div className="sidebar-eu">
        <img src="/images/logos/eu-cofunded.jpg" alt="Co-funded by the European Union" />
      </div>
```

In `frontend/src/components/layout/Sidebar.css` add:

```css
.sidebar-eu {
  margin-top: auto;
  padding: 1rem;
}

.sidebar-eu img {
  width: 100%;
  max-width: 180px;
  display: block;
}
```

If `.sidebar` is not already a flex column, add `display: flex; flex-direction: column;` to the existing `.sidebar` rule so `margin-top: auto` pins the logo to the bottom.

- [ ] **Step 4: Verify**

Run: `cd frontend && npm run lint && npm run build`
Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/public/images/logos frontend/src
git commit -m "fix: serve AIDEA and EU logos locally, add EU logo to sidebar"
```

---

### Task 2: Fix invisible "Start" button text on Pathway page (Issue 2)

`frontend/src/index.css` has an **unlayered** rule `a { color: var(--color-primary) }`. Unlayered CSS beats `@layer utilities`, so the `Button asChild` → `<Link>` on the pathway page renders primary-on-primary (invisible "Start").

**Files:**
- Modify: `frontend/src/index.css:92-94`

- [ ] **Step 1: Move the anchor rule into the base layer**

In `frontend/src/index.css` replace:

```css
a {
  color: var(--color-primary);
}
```

with:

```css
@layer base {
  a {
    color: var(--color-primary);
  }
}
```

Tailwind utility classes (e.g. `text-primary-foreground` inside the shadcn Button) live in `@layer utilities`, which now wins over the base-layer anchor color.

- [ ] **Step 2: Verify**

Run: `cd frontend && npm run lint && npm run build`
Expected: pass. Manually: `npm run dev`, log in as a teacher (`demo_teacher/demo1234`), open My Pathway — the "Start"/"Continue" button label must be visible (white on dark blue).

Also spot-check that ordinary links (e.g. "View courses →" on Home) are still primary-colored.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "fix: layer global anchor color so button-styled links keep readable text"
```

---

### Task 3: Redirect to Home after onboarding (Issue 3)

**Files:**
- Modify: `frontend/src/pages/OnboardingPage.jsx:125`

- [ ] **Step 1: Change the post-onboarding navigation**

In `handleSubmit`, replace:

```js
      navigate('/pathway')
```

with:

```js
      navigate('/')
```

- [ ] **Step 2: Verify + commit**

Run: `cd frontend && npm run lint && npm run build`

```bash
git add frontend/src/pages/OnboardingPage.jsx
git commit -m "fix: land on home page after onboarding instead of pathway"
```

---

### Task 4: Hide "Recommended for you" heading when there are no recommendations (Issue 5)

**Files:**
- Modify: `frontend/src/pages/HomePage.jsx:175-190`

- [ ] **Step 1: Gate the whole section on content**

Replace:

```jsx
      {showRecs && (
        <section className="recommendations-section">
          <h2 className="recommendations-title">Recommended for you</h2>
          {recsLoading ? (
            <div className="recommendations-grid">
              {[1, 2, 3].map((i) => <div key={i} className="rec-card rec-card-skeleton" />)}
            </div>
          ) : personalRecs.length > 0 ? (
            <div className="recommendations-grid">
              {personalRecs.map((rec, i) => (
                <RecCard key={rec.course_id} rec={rec} rank={i + 1} onFireEvent={fireEvent} />
              ))}
            </div>
          ) : null}
        </section>
      )}
```

with:

```jsx
      {showRecs && (recsLoading || personalRecs.length > 0) && (
        <section className="recommendations-section">
          <h2 className="recommendations-title">Recommended for you</h2>
          {recsLoading ? (
            <div className="recommendations-grid">
              {[1, 2, 3].map((i) => <div key={i} className="rec-card rec-card-skeleton" />)}
            </div>
          ) : (
            <div className="recommendations-grid">
              {personalRecs.map((rec, i) => (
                <RecCard key={rec.course_id} rec={rec} rank={i + 1} onFireEvent={fireEvent} />
              ))}
            </div>
          )}
        </section>
      )}
```

- [ ] **Step 2: Verify + commit**

Run: `cd frontend && npm run lint && npm run build`

```bash
git add frontend/src/pages/HomePage.jsx
git commit -m "fix: hide Recommended for you heading when no recommendations exist"
```

---

### Task 5: Order pathway courses by level (Issue 4)

`seed_pathways()` picks courses `order_by('title')`, so "Beginner Foundations" starts with an *advanced* course. Order by level rank instead.

**Files:**
- Modify: `backend/hub/management/commands/seed_data/pathways.py`
- Test: `backend/hub/tests/test_pathway.py` (append a test)

**Interfaces:**
- Consumes: `Course.level` values `'beginner' | 'intermediate' | 'advanced'`

- [ ] **Step 1: Write the failing test**

Append to `backend/hub/tests/test_pathway.py` (match the file's existing setup helpers/imports — read it first; the test below shows intent and must be adapted to existing fixtures):

```python
class PathwaySeedOrderingTests(TestCase):
    def test_seeded_path_courses_ordered_by_level(self):
        from hub.management.commands.seed_data.pathways import seed_pathways
        from hub.models import Course, LearningPillar
        from hub.models.pathway import LearningPath

        pillar = LearningPillar.objects.create(name='Teach with AI', slug='teach-with-ai', order=1)
        Course.objects.create(title='A Advanced', pillar=pillar, level='advanced',
                              duration_hours=1, is_published=True)
        Course.objects.create(title='B Beginner', pillar=pillar, level='beginner',
                              duration_hours=1, is_published=True)
        Course.objects.create(title='C Intermediate', pillar=pillar, level='intermediate',
                              duration_hours=1, is_published=True)

        seed_pathways()

        path = LearningPath.objects.get(slug='beginner-foundations')
        ordered = list(
            path.path_courses.order_by('order').values_list('course__level', flat=True)
        )
        self.assertEqual(ordered, ['beginner', 'intermediate', 'advanced'])
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_pathway.PathwaySeedOrderingTests -v 2`
Expected: FAIL (order is alphabetical: advanced first).

- [ ] **Step 3: Fix the seeder**

In `backend/hub/management/commands/seed_data/pathways.py`, replace:

```python
        courses = list(
            Course.objects.filter(pillar=pillar, is_published=True).order_by('title')[:5]
        )
```

with:

```python
        level_rank = Case(
            When(level='beginner', then=Value(0)),
            When(level='intermediate', then=Value(1)),
            When(level='advanced', then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
        courses = list(
            Course.objects.filter(pillar=pillar, is_published=True)
            .annotate(level_rank=level_rank)
            .order_by('level_rank', 'title')[:5]
        )
```

and add to the imports at the top:

```python
from django.db.models import Case, IntegerField, Value, When
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_pathway -v 2`
Expected: all pass.

- [ ] **Step 5: Lint + commit**

```bash
cd backend && .venv/Scripts/uv.exe run ruff check . --fix
git add backend/hub/management/commands/seed_data/pathways.py backend/hub/tests/test_pathway.py
git commit -m "fix: order pathway courses beginner-to-advanced in seeder"
```

Note for deployment: re-run `manage.py seed` on the VM so existing `LearningPathCourse` rows get rebuilt (the seeder deletes and recreates them).

---

### Task 6: `GET /api/auth/me/` + AuthContext refresh (Issues 7, 8)

Root cause of "can't submit content creator request", "Content Analytics only for creators" while having the Authoring nav, and "pages broken until sign out/in": the SPA trusts the `user` object written to localStorage **at login**. When an admin changes the user's role server-side, every role-gated view disagrees with the stale client state. Fix: expose the current user and refresh on app mount.

**Files:**
- Modify: `backend/hub/views/auth.py` (add `MeView`)
- Modify: `backend/hub/views/__init__.py` (export)
- Modify: `backend/hub/urls.py` (route)
- Modify: `frontend/src/context/AuthContext.jsx`
- Test: `backend/hub/tests/test_auth.py` (append)

**Interfaces:**
- Produces: `GET /api/auth/me/` → same shape as the `user` object from `POST /api/auth/login/` (i.e. `UserSerializer` output, including `profile.user_type`, `profile.avatar_url`)
- Consumes: `UserSerializer` from `hub/serializers/auth.py` (already context-aware for `avatar_url`)

- [ ] **Step 1: Write the failing test**

Append to `backend/hub/tests/test_auth.py` (adapt imports/client setup to the file's existing conventions):

```python
class MeEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='me_user', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type='teacher')

    def test_me_returns_current_role(self):
        self.client.force_authenticate(self.user)
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['profile']['user_type'], 'teacher')

        self.user.profile.user_type = 'content_creator'
        self.user.profile.save()
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.data['profile']['user_type'], 'content_creator')

    def test_me_requires_auth(self):
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, 401)
```

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_auth.MeEndpointTests -v 2`
Expected: FAIL (404 — route missing).

- [ ] **Step 2: Add the view**

In `backend/hub/views/auth.py` add (match existing imports — `UserSerializer` is already imported there or import it):

```python
class MeView(APIView):
    """GET /api/auth/me/ — current user with fresh profile (role) data."""

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)
```

Export `MeView` in `backend/hub/views/__init__.py`, and add to `backend/hub/urls.py`:

```python
    path('auth/me/', MeView.as_view(), name='auth-me'),
```

(DRF default permission is `IsAuthenticated` per `settings.py`, so no explicit permission needed.)

- [ ] **Step 3: Run tests — expect PASS**

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_auth -v 2`

- [ ] **Step 4: Refresh user data on app mount**

In `frontend/src/context/AuthContext.jsx`, add `useEffect` to the react import, then inside `AuthProvider` after the `updateUser` definition:

```jsx
  // Refresh user data from the server on mount so server-side role changes
  // (e.g. content-creator approval) propagate without re-login.
  useEffect(() => {
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
    if (!token) return
    client.get('/auth/me/')
      .then(({ data }) => {
        const store = localStorage.getItem('user') ? localStorage : sessionStorage
        store.setItem('user', JSON.stringify(data))
        setUser(data)
      })
      .catch(() => {}) // interceptor handles 401 → login redirect
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
```

- [ ] **Step 5: Verify frontend + commit**

Run: `cd frontend && npm run lint && npm run build`

```bash
git add backend/hub/views backend/hub/urls.py backend/hub/tests/test_auth.py frontend/src/context/AuthContext.jsx
git commit -m "fix: add /auth/me/ and refresh cached user on app mount so role changes propagate"
```

---

### Task 7: Open learning preferences to all authenticated users (Issue 6)

"Failed to load preferences." happens because `ProfilePreferencesView` is `IsTeacher`-only — content creators (like the tester after approval) get 403.

**Files:**
- Modify: `backend/hub/views/profile.py:16-17`
- Test: `backend/hub/tests/test_phase2_profile.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/hub/tests/test_phase2_profile.py` (adapt to existing conventions):

```python
class CreatorPreferencesTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='cc_prefs', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type='content_creator')

    def test_content_creator_can_read_preferences(self):
        self.client.force_authenticate(self.creator)
        res = self.client.get('/api/profile/preferences/')
        self.assertEqual(res.status_code, 200)

    def test_content_creator_can_update_preferences(self):
        self.client.force_authenticate(self.creator)
        res = self.client.patch('/api/profile/preferences/', {'learning_style': 'video'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.creator.profile.learning_style, 'video')
```

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_phase2_profile.CreatorPreferencesTests -v 2`
Expected: FAIL with 403.

- [ ] **Step 2: Relax the permission**

In `backend/hub/views/profile.py`, `ProfilePreferencesView`: replace `permission_classes = [IsTeacher]` with `permission_classes = [IsAuthenticated]`. Remove the now-unused `IsTeacher` import if nothing else in the file uses it.

- [ ] **Step 3: Run tests, lint, commit**

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub -v 1` (full app — permission changes can ripple)

```bash
cd backend && .venv/Scripts/uv.exe run ruff check . --fix
git add backend/hub/views/profile.py backend/hub/tests/test_phase2_profile.py
git commit -m "fix: allow content creators to read and update learning preferences"
```

---

### Task 8: Mark completed modules on the course detail page (Issue 10)

The page checkmarks only `current_module_id` — the last module touched — while genuinely completed modules 1–2 show empty circles. Backend must expose per-module completion.

**Files:**
- Modify: `backend/hub/serializers/course.py` (`CourseDetailSerializer`)
- Modify: `frontend/src/pages/CourseDetailPage.jsx:132-149`
- Test: `backend/hub/tests/test_learner_progress.py` (append)

**Interfaces:**
- Produces: `completed_module_ids: number[]` on `GET /api/courses/<id>/` — modules where every **required** lesson has a `LessonProgress` row for the requesting user.

- [ ] **Step 1: Write the failing test**

Append to `backend/hub/tests/test_learner_progress.py` (adapt setup to the file's existing fixtures — it already creates courses/modules/lessons/enrollments):

```python
class CompletedModuleIdsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='mod_done', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type='teacher')
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        self.course = Course.objects.create(
            title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        self.m1 = Module.objects.create(course=self.course, title='M1', order=1)
        self.m2 = Module.objects.create(course=self.course, title='M2', order=2)
        self.l1 = Lesson.objects.create(module=self.m1, title='L1', lesson_type='text', order=1, is_required=True)
        self.l2 = Lesson.objects.create(module=self.m2, title='L2', lesson_type='text', order=1, is_required=True)
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(self.user)

    def test_completed_module_ids(self):
        LessonProgress.objects.create(user=self.user, lesson=self.l1)
        res = self.client.get(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['completed_module_ids'], [self.m1.id])
```

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_learner_progress.CompletedModuleIdsTests -v 2`
Expected: FAIL with KeyError `completed_module_ids`.

- [ ] **Step 2: Add the field to `CourseDetailSerializer`**

In `backend/hub/serializers/course.py`:

```python
    completed_module_ids = serializers.SerializerMethodField()
```

Add `'completed_module_ids'` to `Meta.fields`, and implement:

```python
    def get_completed_module_ids(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return []
        from hub.models import LessonProgress
        completed_lesson_ids = set(
            LessonProgress.objects.filter(
                user=user, lesson__module__course=obj,
            ).values_list('lesson_id', flat=True)
        )
        result = []
        for module in obj.modules.all():
            required = [
                lesson.id for lesson in module.lessons.all() if lesson.is_required
            ]
            if required and all(lid in completed_lesson_ids for lid in required):
                result.append(module.id)
        return result
```

Also update `CourseDetailView` in `backend/hub/views/learner.py` to prefetch lessons so this doesn't N+1:

```python
            course = Course.objects.prefetch_related('modules__lessons').select_related('pillar').get(
                pk=pk, is_published=True,
            )
```

- [ ] **Step 3: Run tests — expect PASS**

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_learner_progress -v 2`

- [ ] **Step 4: Use it in the frontend**

In `frontend/src/pages/CourseDetailPage.jsx`, replace the module row rendering:

```jsx
          {course.modules.map((mod) => {
            const isCompleted = course.completed_module_ids?.includes(mod.id)
            const isCurrent = mod.id === course.current_module_id
            return (
              <div key={mod.id} className={`module-row ${isCurrent ? 'module-row--current' : ''}`}>
                <div className="module-number">{mod.order}</div>
                <div className="module-body">
                  <p className="module-title">Module {mod.order} — {mod.title}</p>
                  {mod.description && <p className="module-desc">{mod.description}</p>}
                  <p className="module-meta">
                    {mod.duration_minutes > 0 && <span>{mod.duration_minutes} min</span>}
                  </p>
                </div>
                <div className="module-status">
                  {isCompleted
                    ? <CheckCircle2 size={22} className="module-status--done" />
                    : <Circle size={22} className="module-status--empty" />
                  }
                </div>
              </div>
            )
          })}
```

- [ ] **Step 5: Verify, lint, commit**

Run: `cd frontend && npm run lint && npm run build` and `cd backend && .venv/Scripts/uv.exe run ruff check . --fix`

```bash
git add backend/hub/serializers/course.py backend/hub/views/learner.py backend/hub/tests/test_learner_progress.py frontend/src/pages/CourseDetailPage.jsx
git commit -m "fix: show checkmarks on genuinely completed modules in course detail"
```

---

### Task 9: Per-question quiz feedback + review mode (Issue 9)

Today the correct/wrong colors only appear on the **last** question (results arrive with final submission), and revisiting a completed quiz lets the user "re-answer" into the void (first submission is what's stored — `LessonCompleteView` only writes on `created`).

Design:
1. New endpoint `POST /api/courses/<pk>/lessons/<lesson_pk>/quiz-check/` `{question_index, selected}` → `{correct, correct_index}` — grades one answer server-side without persisting (correct answers stay out of the lesson payload).
2. `LessonCompleteView` also stores the raw selections in `engagement_data['quiz_selected']`.
3. `LessonDetailView` returns `quiz_review: {selected: [...], results: [...]}` for completed quizzes.
4. `QuizLesson` component: instant feedback per question; review mode (read-only, shows saved answers) when completed.

**Files:**
- Modify: `backend/hub/views/learner.py`
- Modify: `backend/hub/views/__init__.py`, `backend/hub/urls.py`
- Modify: `frontend/src/pages/LessonPage.jsx` (QuizLesson)
- Test: `backend/hub/tests/test_lesson_api.py` (append)

**Interfaces:**
- Produces: `POST .../quiz-check/` → `200 {correct: bool, correct_index: int}`; `GET .../lessons/<id>/` gains `quiz_review: {selected: int[], results: bool[]} | null`
- Consumes: `lesson.quiz_data[i].options[j].is_correct` (authoring shape), `LessonProgress.quiz_answers` (bool[]), `LessonProgress.engagement_data`

- [ ] **Step 1: Write failing tests**

Append to `backend/hub/tests/test_lesson_api.py` (adapt fixtures — the file already builds quiz lessons):

```python
class QuizCheckTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='quiz_user', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type='teacher')
        pillar = LearningPillar.objects.create(name='P', slug='pq', order=1)
        self.course = Course.objects.create(
            title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        )
        module = Module.objects.create(course=self.course, title='M', order=1)
        self.quiz = Lesson.objects.create(
            module=module, title='Q', lesson_type='quiz', order=1, is_required=True,
            quiz_data=[{
                'question': '1+1?',
                'options': [
                    {'text': '1', 'is_correct': False},
                    {'text': '2', 'is_correct': True},
                ],
            }],
        )
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(self.user)
        self.url = f'/api/courses/{self.course.id}/lessons/{self.quiz.id}/quiz-check/'

    def test_correct_answer(self):
        res = self.client.post(self.url, {'question_index': 0, 'selected': 1}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['correct'])
        self.assertEqual(res.data['correct_index'], 1)

    def test_wrong_answer(self):
        res = self.client.post(self.url, {'question_index': 0, 'selected': 0}, format='json')
        self.assertFalse(res.data['correct'])

    def test_invalid_index_rejected(self):
        res = self.client.post(self.url, {'question_index': 5, 'selected': 0}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_quiz_review_returned_after_completion(self):
        complete_url = f'/api/courses/{self.course.id}/lessons/{self.quiz.id}/complete/'
        self.client.post(complete_url, {'quiz_answers': [1]}, format='json')
        res = self.client.get(f'/api/courses/{self.course.id}/lessons/{self.quiz.id}/')
        self.assertEqual(res.data['quiz_review'], {'selected': [1], 'results': [True]})
```

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_lesson_api.QuizCheckTests -v 2`
Expected: FAIL (404 route, missing key).

- [ ] **Step 2: Implement backend**

In `backend/hub/views/learner.py` add:

```python
class QuizCheckView(APIView):
    """POST /courses/<pk>/lessons/<lesson_pk>/quiz-check/ — grade one answer, no persistence."""

    def post(self, request, pk, lesson_pk):
        if not Enrollment.objects.filter(user=request.user, course_id=pk).exists():
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            lesson = Lesson.objects.get(pk=lesson_pk, module__course_id=pk, lesson_type='quiz')
        except Lesson.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        q_index = request.data.get('question_index')
        selected = request.data.get('selected')
        quiz_data = lesson.quiz_data or []
        if not isinstance(q_index, int) or not 0 <= q_index < len(quiz_data):
            return Response({'detail': 'Invalid question_index.'}, status=status.HTTP_400_BAD_REQUEST)
        options = quiz_data[q_index].get('options', [])
        if not isinstance(selected, int) or not 0 <= selected < len(options):
            return Response({'detail': 'Invalid selected.'}, status=status.HTTP_400_BAD_REQUEST)

        correct_index = next(
            (i for i, opt in enumerate(options) if opt.get('is_correct')), -1,
        )
        return Response({
            'correct': bool(options[selected].get('is_correct', False)),
            'correct_index': correct_index,
        })
```

In `LessonCompleteView.post`, inside the `if created:` block, after the quiz grading block, change the engagement lines to also store selections:

```python
            engagement = dict(request.data.get('engagement_data') or {})
            if lesson.lesson_type == 'assignment' and 'submission' in engagement:
                engagement['word_count'] = len(str(engagement['submission']).split())
            if lesson.lesson_type == 'quiz' and quiz_answers_raw:
                engagement['quiz_selected'] = quiz_answers_raw
            lp.engagement_data = engagement
```

In `LessonDetailView.get`, before the return, add:

```python
        quiz_review = None
        if lesson.lesson_type == 'quiz' and is_completed:
            lp = LessonProgress.objects.filter(user=request.user, lesson=lesson).first()
            if lp and lp.quiz_answers:
                quiz_review = {
                    'selected': (lp.engagement_data or {}).get('quiz_selected', []),
                    'results': lp.quiz_answers,
                }
```

and include `'quiz_review': quiz_review,` in the response dict.

Export `QuizCheckView` in `backend/hub/views/__init__.py` and route it in `backend/hub/urls.py`:

```python
    path('courses/<int:pk>/lessons/<int:lesson_pk>/quiz-check/', QuizCheckView.as_view(), name='quiz-check'),
```

- [ ] **Step 3: Run backend tests — expect PASS**

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_lesson_api hub.tests.test_learner_progress -v 2`

- [ ] **Step 4: Rework `QuizLesson` in `frontend/src/pages/LessonPage.jsx`**

Replace the whole `QuizLesson` component with:

```jsx
QuizLesson.propTypes = {
  lesson:     lessonShape.isRequired,
  onComplete: PropTypes.func.isRequired,
  courseId:   PropTypes.string.isRequired,
}
function QuizLesson({ lesson, onComplete, courseId }) {
  const questions = lesson.quiz_data ?? []
  const review = lesson.quiz_review
  const isReview = Boolean(lesson.is_completed && review?.selected?.length)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState({})     // { [qIdx]: selectedOption }
  const [feedback, setFeedback] = useState({})   // { [qIdx]: {correct, correct_index} }

  if (questions.length === 0) {
    return <div className="lp-content-card"><p className="lp-empty">No questions yet.</p></div>
  }

  const q = questions[currentIdx]
  const isLastQuestion = currentIdx === questions.length - 1
  const answered = isReview || answers[currentIdx] !== undefined

  const handleSelect = async (optionIdx) => {
    if (answered) return
    setAnswers(prev => ({ ...prev, [currentIdx]: optionIdx }))
    try {
      const res = await client.post(
        `/courses/${courseId}/lessons/${lesson.id}/quiz-check/`,
        { question_index: currentIdx, selected: optionIdx },
      )
      setFeedback(prev => ({ ...prev, [currentIdx]: res.data }))
    } catch { /* leave selected highlight only */ }

    if (isLastQuestion) {
      const finalAnswers = { ...answers, [currentIdx]: optionIdx }
      const answersArray = questions.map((_, i) => finalAnswers[i] ?? -1)
      setTimeout(() => onComplete({ quiz_answers: answersArray }), 1200)
    }
  }

  const selectedOf = (qIdx) => isReview ? review.selected[qIdx] : answers[qIdx]
  const resultOf   = (qIdx) => {
    if (isReview) return { correct: review.results[qIdx], correct_index: null }
    return feedback[qIdx] ?? null
  }

  const getOptionState = (optionIdx) => {
    const selected = selectedOf(currentIdx)
    if (selected === undefined || selected === null) return ''
    const res = resultOf(currentIdx)
    const isSelected = selected === optionIdx
    if (res) {
      if (isSelected) return res.correct ? 'lp-option--correct' : 'lp-option--wrong'
      if (res.correct_index === optionIdx) return 'lp-option--correct'
      return 'lp-option--dimmed'
    }
    return isSelected ? 'lp-option--selected' : 'lp-option--dimmed'
  }

  const badgeFor = (optionIdx) => {
    const selected = selectedOf(currentIdx)
    const res = resultOf(currentIdx)
    if (selected === undefined || selected === null || !res) return null
    if (selected === optionIdx) {
      return res.correct
        ? <span className="lp-option-badge lp-option-badge--correct">✓ Correct</span>
        : <span className="lp-option-badge lp-option-badge--wrong">✗ Incorrect</span>
    }
    if (!res.correct && res.correct_index === optionIdx) {
      return <span className="lp-option-badge lp-option-badge--correct">Correct answer</span>
    }
    return null
  }

  return (
    <div className="lp-content-card lp-quiz-card">
      <div className="lp-question-block">
        <p className="lp-question-counter">
          Question {currentIdx + 1} of {questions.length}
          {isReview && ' — review'}
        </p>
        <p className="lp-question-text">{q.question}</p>
      </div>

      <div className="lp-options">
        {(q.options ?? []).map((opt, i) => (
          <button
            key={i}
            className={`lp-option lp-option--btn ${getOptionState(i)}`}
            onClick={() => handleSelect(i)}
            disabled={answered}
          >
            <span className="lp-option-radio" />
            <span>{opt.text}</span>
            {badgeFor(i)}
          </button>
        ))}
      </div>

      <div className="lp-quiz-nav">
        {currentIdx > 0 && (
          <button className="lp-quiz-arrow" onClick={() => setCurrentIdx(i => i - 1)}>
            ← Previous question
          </button>
        )}
        {answered && !isLastQuestion && (
          <button
            className="lp-quiz-arrow lp-quiz-arrow--next"
            onClick={() => setCurrentIdx(i => i + 1)}
          >
            Next question →
          </button>
        )}
      </div>
    </div>
  )
}
```

In `LessonContent`, pass `courseId` through:

```jsx
    case 'quiz':       return <QuizLesson key={lesson.id} lesson={lesson} onComplete={onComplete} courseId={courseId} />
```

Add `courseId: PropTypes.string` to `LessonContent.propTypes`, accept it as a prop, and at the call site in `LessonPage`:

```jsx
              <LessonContent lesson={lesson} onComplete={markComplete} onSubmissionChange={setSubmissionText} courseId={courseId} />
```

Note: `markComplete` already guards against double-completion; the quiz no longer needs the returned results (feedback is per-question now), so `setQuizResults` and related dead code are gone with this replacement.

- [ ] **Step 5: Verify, lint, commit**

Run: `cd frontend && npm run lint && npm run build`; `cd backend && .venv/Scripts/uv.exe run ruff check . --fix`

```bash
git add backend/hub frontend/src/pages/LessonPage.jsx
git commit -m "feat: instant per-question quiz feedback and read-only review of completed quizzes"
```

---

### Task 10: Inline PDF and video rendering in the lesson player (Issues 18, 19, 20)

Replace the "Open PDF ↗" and "Video Player" placeholder cards with real embeds. Extract the embeds into shared components so Task 11 (editor preview) reuses them.

**Files:**
- Create: `frontend/src/components/lesson/MediaEmbeds.jsx`
- Create: `frontend/src/components/lesson/MediaEmbeds.css`
- Modify: `frontend/src/pages/LessonPage.jsx` (`VideoLesson`, `PdfLesson`)

**Interfaces:**
- Produces: `VideoEmbed({ url })` and `PdfEmbed({ url })` React components (named exports from `MediaEmbeds.jsx`); `toVideoEmbedUrl(url)` helper (exported for reuse)

- [ ] **Step 1: Create `frontend/src/components/lesson/MediaEmbeds.jsx`**

```jsx
import PropTypes from 'prop-types'
import { Video, FileIcon } from 'lucide-react'
import './MediaEmbeds.css'

export function toVideoEmbedUrl(url) {
  if (!url) return null
  const yt = url.match(/(?:youtube\.com\/watch\?.*v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{11})/)
  if (yt) return `https://www.youtube.com/embed/${yt[1]}`
  const vimeo = url.match(/vimeo\.com\/(\d+)/)
  if (vimeo) return `https://player.vimeo.com/video/${vimeo[1]}`
  return null
}

const FILE_VIDEO = /\.(mp4|webm|ogg)(\?.*)?$/i

VideoEmbed.propTypes = { url: PropTypes.string }

export function VideoEmbed({ url }) {
  const embedUrl = toVideoEmbedUrl(url)
  if (embedUrl) {
    return (
      <div className="media-video-wrap">
        <iframe
          src={embedUrl}
          title="Video lesson"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    )
  }
  if (url && FILE_VIDEO.test(url)) {
    return <video className="media-video-file" src={url} controls />
  }
  return (
    <div className="media-placeholder">
      <Video size={48} className="media-placeholder-icon" />
      <p className="media-placeholder-label">Video Player</p>
      {url && <a href={url} target="_blank" rel="noreferrer" className="media-open-link">Open video ↗</a>}
    </div>
  )
}

PdfEmbed.propTypes = { url: PropTypes.string }

export function PdfEmbed({ url }) {
  if (!url) {
    return (
      <div className="media-placeholder">
        <FileIcon size={48} className="media-placeholder-icon" />
        <p className="media-placeholder-label">PDF Document</p>
      </div>
    )
  }
  return (
    <div className="media-pdf-wrap">
      <iframe src={url} title="PDF lesson" />
      <a href={url} target="_blank" rel="noreferrer" className="media-open-link media-pdf-fallback">
        Open in new tab ↗ (if the preview does not load)
      </a>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/lesson/MediaEmbeds.css`**

```css
.media-video-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.media-video-wrap iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
}

.media-video-file {
  width: 100%;
  border-radius: 8px;
  background: #000;
}

.media-pdf-wrap iframe {
  width: 100%;
  height: 70vh;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
  background: #fff;
}

.media-pdf-fallback {
  display: inline-block;
  margin-top: 0.5rem;
  font-size: 0.85rem;
}

.media-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 3rem 1rem;
  color: #6b7280;
}
```

- [ ] **Step 3: Use the embeds in `LessonPage.jsx`**

Add the import:

```jsx
import { VideoEmbed, PdfEmbed } from '../components/lesson/MediaEmbeds'
```

Replace `VideoLesson` and `PdfLesson` bodies:

```jsx
function VideoLesson({ lesson }) {
  return (
    <div className="lp-content-card">
      <VideoEmbed url={lesson.content} />
    </div>
  )
}
```

```jsx
function PdfLesson({ lesson }) {
  return (
    <div className="lp-content-card">
      <PdfEmbed url={lesson.content} />
    </div>
  )
}
```

Note: some external PDF hosts send `X-Frame-Options: DENY` and will refuse to render in the iframe — that is why the "Open in new tab" fallback link stays visible below the frame. PDFs uploaded to our own backend (Task 14) always render.

- [ ] **Step 4: Verify + commit**

Run: `cd frontend && npm run lint && npm run build`
Manual check with a YouTube URL lesson and a PDF lesson (seed data has both types).

```bash
git add frontend/src/components/lesson frontend/src/pages/LessonPage.jsx
git commit -m "feat: render videos and PDFs inline in the lesson player"
```

---

### Task 11: Live preview in the lesson editor (Issue 14)

The editor's "Preview" card is an empty stub. Render an actual preview per lesson type, reusing Task 10's embeds.

**Files:**
- Modify: `frontend/src/pages/ModuleEditorPage.jsx` (LessonEditor preview card)
- Modify: `frontend/src/pages/ModuleEditorPage.css`

**Interfaces:**
- Consumes: `VideoEmbed`, `PdfEmbed` from `frontend/src/components/lesson/MediaEmbeds.jsx` (Task 10)

- [ ] **Step 1: Replace the preview stub**

In `ModuleEditorPage.jsx` add the import:

```jsx
import { VideoEmbed, PdfEmbed } from '../components/lesson/MediaEmbeds'
```

Add a preview component above `LessonEditor`:

```jsx
LessonPreview.propTypes = { lesson: lessonShape.isRequired }

function LessonPreview({ lesson }) {
  switch (lesson.lesson_type) {
    case 'text':
      return lesson.content
        ? <p className="lesson-preview-text">{lesson.content}</p>
        : <p className="lesson-preview-empty">Write content above to see the preview.</p>
    case 'video':
      return <VideoEmbed url={lesson.content} />
    case 'pdf':
      return <PdfEmbed url={lesson.content} />
    case 'image':
      return lesson.content
        ? <img src={lesson.content} alt={lesson.title} className="lesson-preview-image" />
        : <p className="lesson-preview-empty">Paste an image URL above to see the preview.</p>
    case 'assignment':
      return lesson.content
        ? (
          <div>
            <h4 className="lesson-preview-subheading">Instructions</h4>
            <p className="lesson-preview-text">{lesson.content}</p>
          </div>
        )
        : <p className="lesson-preview-empty">Write instructions above to see the preview.</p>
    case 'quiz': {
      const first = (lesson.quiz_data ?? [])[0]
      if (!first?.question) return <p className="lesson-preview-empty">Add a question to see the preview.</p>
      return (
        <div>
          <p className="lesson-preview-quiz-q">{first.question}</p>
          <ul className="lesson-preview-quiz-opts">
            {first.options.filter(o => o.text).map((o, i) => <li key={i}>{o.text}</li>)}
          </ul>
        </div>
      )
    }
    default:
      return null
  }
}
```

Replace the stub card at the bottom of `LessonEditor`:

```jsx
        <div className="lesson-preview-card">
          <h3 className="lesson-preview-title">Preview</h3>
          <p className="lesson-preview-sub">How this lesson will appear to students</p>
          <div className="lesson-preview-body">
            <LessonPreview lesson={lesson} />
          </div>
        </div>
```

- [ ] **Step 2: Add preview styles to `ModuleEditorPage.css`**

```css
.lesson-preview-body {
  margin-top: 0.75rem;
  padding: 1rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.lesson-preview-text { white-space: pre-wrap; font-size: 0.9rem; }
.lesson-preview-empty { color: #9ca3af; font-size: 0.85rem; font-style: italic; }
.lesson-preview-image { max-width: 100%; border-radius: 6px; }
.lesson-preview-subheading { font-size: 0.85rem; font-weight: 600; margin-bottom: 0.35rem; }
.lesson-preview-quiz-q { font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem; }
.lesson-preview-quiz-opts { margin: 0; padding-left: 1.25rem; font-size: 0.85rem; }
.lesson-preview-quiz-opts li { margin-bottom: 0.25rem; }
```

- [ ] **Step 3: Verify + commit**

Run: `cd frontend && npm run lint && npm run build`

```bash
git add frontend/src/pages/ModuleEditorPage.jsx frontend/src/pages/ModuleEditorPage.css
git commit -m "feat: live lesson preview in the module editor"
```

---

### Task 12: Show the course author in authoring (Issue 12)

**Files:**
- Modify: `backend/hub/serializers/course.py` (`CourseAuthoringSerializer`)
- Modify: `frontend/src/pages/AuthoringPage.jsx` + `AuthoringPage.css`
- Modify: `frontend/src/pages/CourseEditorPage.jsx`
- Test: `backend/hub/tests/test_authoring_courses.py` (append)

**Interfaces:**
- Produces: `created_by_id: number|null`, `created_by_name: string` on all authoring course payloads (list + detail). Task 13 consumes `created_by_id`.

- [ ] **Step 1: Write the failing test**

Append to `backend/hub/tests/test_authoring_courses.py` (adapt to its fixtures — it already has a content-creator client):

```python
    def test_authoring_course_includes_author(self):
        res = self.client.get('/api/authoring/courses/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('created_by_name', res.data[0])
        self.assertIn('created_by_id', res.data[0])
```

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_authoring_courses -v 2`
Expected: new test FAILS.

- [ ] **Step 2: Add the fields**

In `CourseAuthoringSerializer` (`backend/hub/serializers/course.py`):

```python
    created_by_id = serializers.IntegerField(source='created_by.id', read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()
```

Add both to `Meta.fields`, and:

```python
    def get_created_by_name(self, obj):
        if not obj.created_by:
            return 'AIDEA team'
        return obj.created_by.get_full_name() or obj.created_by.username
```

In `AuthoringCoursesView.get` add `.select_related('pillar', 'created_by')` to avoid N+1.

- [ ] **Step 3: Run tests — expect PASS**

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_authoring_courses -v 2`

- [ ] **Step 4: Show the author in the UI**

In `frontend/src/pages/AuthoringPage.jsx`, inside the course card markup (below the title/status-badge row — read the file and place it where the card meta renders):

```jsx
                  <p className="course-card-author">By {course.created_by_name}</p>
```

In `AuthoringPage.css`:

```css
.course-card-author {
  font-size: 0.8rem;
  color: #6b7280;
  margin: 0.25rem 0 0;
}
```

In `CourseEditorPage.jsx`, keep `created_by_id` and `created_by_name` from the course response in state (extend the `useEffect` that sets the form):

```jsx
        setAuthor({ id: c.created_by_id, name: c.created_by_name })
```

with `const [author, setAuthor] = useState({ id: null, name: '' })`, and render near the page heading:

```jsx
        {author.name && <p className="course-editor-author">Author: {author.name}</p>}
```

plus CSS in `CourseEditorPage.css`:

```css
.course-editor-author { font-size: 0.85rem; color: #6b7280; margin-top: 0.25rem; }
```

- [ ] **Step 5: Verify, lint, commit**

Run: `cd frontend && npm run lint && npm run build`; `cd backend && .venv/Scripts/uv.exe run ruff check . --fix`

```bash
git add backend/hub frontend/src/pages
git commit -m "feat: show course author in authoring list and editor"
```

---

### Task 13: Authors (and admins) can edit published courses (Issues 13, 17)

Every authoring mutation currently hard-blocks on `is_published`. Change the rule: published courses are editable by their **author** or an **admin**; everyone else stays read-only. Also fix the stale publish-confirm text (unpublish exists since commit 573dcea).

**Files:**
- Modify: `backend/hub/views/permissions.py` (add helper)
- Modify: `backend/hub/views/authoring_course.py`, `backend/hub/views/authoring_module.py`, `backend/hub/views/authoring_lesson.py`
- Modify: `frontend/src/pages/CourseEditorPage.jsx`, `frontend/src/pages/ModuleEditorPage.jsx`
- Test: `backend/hub/tests/test_authoring_courses.py`, `backend/hub/tests/test_authoring_modules_lessons.py` (append)

**Interfaces:**
- Consumes: `created_by_id` from Task 12; `user.id` from `useAuth()` on the frontend
- Produces: helper `can_edit_published(user, course) -> bool` in `hub/views/permissions.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/hub/tests/test_authoring_courses.py`:

```python
class PublishedCourseEditTests(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author_cc', password='pass12345')
        UserProfile.objects.create(user=self.author, user_type='content_creator')
        self.other = User.objects.create_user(username='other_cc', password='pass12345')
        UserProfile.objects.create(user=self.other, user_type='content_creator')
        pillar = LearningPillar.objects.create(name='P', slug='ppub', order=1)
        self.course = Course.objects.create(
            title='Published', pillar=pillar, level='beginner', duration_hours=1,
            is_published=True, created_by=self.author,
        )
        self.url = f'/api/authoring/courses/{self.course.id}/'

    def test_author_can_edit_published_course(self):
        self.client.force_authenticate(self.author)
        res = self.client.patch(self.url, {'title': 'Updated'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Updated')

    def test_non_author_cannot_edit_published_course(self):
        self.client.force_authenticate(self.other)
        res = self.client.patch(self.url, {'title': 'Nope'}, format='json')
        self.assertEqual(res.status_code, 403)
```

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_authoring_courses.PublishedCourseEditTests -v 2`
Expected: `test_author_can_edit_published_course` FAILS with 400.

- [ ] **Step 2: Add the helper**

In `backend/hub/views/permissions.py`:

```python
def can_edit_published(user, course):
    """Published courses may only be edited by their author or an admin."""
    profile = getattr(user, 'profile', None)
    is_admin = profile is not None and profile.user_type == UserProfile.UserType.ADMIN
    return course.created_by_id == user.id or is_admin
```

- [ ] **Step 3: Replace every published-course guard**

Run: `grep -rn "Published courses cannot be edited" backend/hub/views`

Every match (in `authoring_course.py` patch; `authoring_module.py` create/patch/delete/reorder; `authoring_lesson.py` create/patch/delete/reorder) follows this pattern:

```python
        if course.is_published:
            return Response({'detail': 'Published courses cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)
```

Replace each with (adjusting the variable — `course`, `module.course`, or `lesson.module.course`):

```python
        if course.is_published and not can_edit_published(request.user, course):
            return Response(
                {'detail': 'Published courses can only be edited by their author.'},
                status=status.HTTP_403_FORBIDDEN,
            )
```

Import in each file: `from .permissions import IsContentCreator, can_edit_published`

- [ ] **Step 4: Run backend tests — expect PASS, watch for ripples**

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub -v 1`

Existing tests asserting the old 400 behaviour will fail — update them to expect 403 for non-authors, and add `created_by` to their course fixtures where the test intends the edit to be blocked (a course with `created_by=None` is editable by admins only once published).

- [ ] **Step 5: Unlock the frontend editors for the author**

In `CourseEditorPage.jsx` (using `author` state from Task 12):

```jsx
import { useAuth } from '../context/AuthContext'
```

```jsx
  const { user } = useAuth()
  const isAuthor = author.id != null && user?.id === author.id
  const isAdmin = user?.profile?.user_type === 'admin'
```

Change `const locked = isPublished` to:

```jsx
  const locked = isPublished && !isAuthor && !isAdmin
```

Update the published banner text (`This course is published and can no longer be edited.`) to:

```jsx
          <Lock size={14} />
          {locked
            ? 'This course is published — only its author can edit it.'
            : 'This course is published — your edits go live immediately.'}
```

Update the publish confirm ([CourseEditorPage.jsx:112](frontend/src/pages/CourseEditorPage.jsx#L112)):

```jsx
    if (!window.confirm('Publish this course? Learners will see it immediately. As the author you can still edit or unpublish it.')) return
```

In `ModuleEditorPage.jsx`, the course GET response now includes `created_by_id`; compute `locked` the same way:

```jsx
        setIsPublished(courseRes.data.is_published)
        setCourseAuthorId(courseRes.data.created_by_id)
```

with `const [courseAuthorId, setCourseAuthorId] = useState(null)`, plus:

```jsx
  const { user } = useAuth()
  const isAuthor = courseAuthorId != null && user?.id === courseAuthorId
  const isAdmin = user?.profile?.user_type === 'admin'
  const locked = isPublished && !isAuthor && !isAdmin
```

(import `useAuth` and delete the old `const locked = isPublished` line). Update its banner text the same way.

Also in `AuthoringPage.jsx:79`, the button label `{course.is_published ? 'View' : 'Edit'}` becomes:

```jsx
                  <Pencil size={14} /> {course.is_published && course.created_by_id !== user?.id && user?.profile?.user_type !== 'admin' ? 'View' : 'Edit'}
```

(import and call `useAuth()` in that component).

- [ ] **Step 6: Verify, lint, commit**

Run: `cd frontend && npm run lint && npm run build`; `cd backend && .venv/Scripts/uv.exe run ruff check . --fix && .venv/Scripts/uv.exe run manage.py test hub -v 1`

```bash
git add backend/hub frontend/src/pages
git commit -m "feat: authors and admins can edit published courses"
```

---

### Task 14: Surface lesson-save failures in the module editor (Issue 16)

The tester "saved" a PDF lesson that silently vanished: `saveLesson`'s `catch {}` swallows API errors (her course was published, so the API rejected the write and nothing told her).

**Files:**
- Modify: `frontend/src/pages/ModuleEditorPage.jsx` (`saveLesson`, `deleteLesson`, `LessonEditor`)

- [ ] **Step 1: Capture and display the API error**

In `saveLesson`, replace the catch block:

```jsx
    } catch (err) {
      const detail = err.response?.data?.detail
        ?? Object.values(err.response?.data ?? {})[0]
        ?? 'Save failed. Please try again.'
      setLessonErrors((prev) => ({
        ...prev,
        [lesson.id]: { ...(prev[lesson.id] ?? {}), general: String(detail) },
      }))
      setLessons((ls) => ls.map((l) => (l.id === lesson.id ? { ...l, saving: false } : l)))
    }
```

In `deleteLesson`, replace `catch { /* user can retry */ }` with:

```jsx
    } catch (err) {
      const detail = err.response?.data?.detail ?? 'Delete failed. Please try again.'
      setLessonErrors((prev) => ({
        ...prev,
        [lesson.id]: { ...(prev[lesson.id] ?? {}), general: String(detail) },
      }))
    }
```

- [ ] **Step 2: Render the general error near the save button**

In `LessonEditor`, just above the save button block (`{!locked && lesson.isDirty && (`):

```jsx
        <FieldError msg={err.general} />
```

- [ ] **Step 3: Verify + commit**

Run: `cd frontend && npm run lint && npm run build`

```bash
git add frontend/src/pages/ModuleEditorPage.jsx
git commit -m "fix: surface lesson save/delete errors in the module editor"
```

---

### Task 15: Upload PDF (and image) files from disk (Issue 15)

Authors can only paste URLs. Add an upload endpoint saving to `MEDIA_ROOT` (already configured, with Pillow installed) and a file input in the lesson editor.

**Files:**
- Create: `backend/hub/views/authoring_upload.py`
- Modify: `backend/hub/views/__init__.py`, `backend/hub/urls.py`
- Modify: `frontend/src/pages/ModuleEditorPage.jsx` (LessonEditor URL field)
- Test: `backend/hub/tests/test_authoring_upload.py` (new file)

**Interfaces:**
- Produces: `POST /api/authoring/upload/` (multipart, field `file`) → `201 {"url": "<absolute url>"}`; errors `400 {"error": "..."}`. Allowed: `.pdf .png .jpg .jpeg .gif .webp`, ≤ 20 MB. Content-creator only.

- [ ] **Step 1: Write failing tests — new file `backend/hub/tests/test_authoring_upload.py`**

```python
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from hub.models import UserProfile


class AuthoringUploadTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='uploader', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type='content_creator')
        self.teacher = User.objects.create_user(username='not_creator', password='pass12345')
        UserProfile.objects.create(user=self.teacher, user_type='teacher')
        self.url = '/api/authoring/upload/'

    def _pdf(self, name='doc.pdf', size=100):
        return SimpleUploadedFile(name, b'%PDF-1.4 ' + b'0' * size, content_type='application/pdf')

    def test_creator_can_upload_pdf(self):
        self.client.force_authenticate(self.creator)
        res = self.client.post(self.url, {'file': self._pdf()}, format='multipart')
        self.assertEqual(res.status_code, 201)
        self.assertIn('/media/lesson_uploads/', res.data['url'])
        self.assertTrue(res.data['url'].startswith('http'))

    def test_teacher_rejected(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.post(self.url, {'file': self._pdf()}, format='multipart')
        self.assertEqual(res.status_code, 403)

    def test_bad_extension_rejected(self):
        self.client.force_authenticate(self.creator)
        bad = SimpleUploadedFile('run.exe', b'MZ', content_type='application/octet-stream')
        res = self.client.post(self.url, {'file': bad}, format='multipart')
        self.assertEqual(res.status_code, 400)

    def test_oversize_rejected(self):
        self.client.force_authenticate(self.creator)
        big = SimpleUploadedFile('big.pdf', b'0' * (21 * 1024 * 1024), content_type='application/pdf')
        res = self.client.post(self.url, {'file': big}, format='multipart')
        self.assertEqual(res.status_code, 400)
```

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_authoring_upload -v 2`
Expected: FAIL (404).

- [ ] **Step 2: Implement `backend/hub/views/authoring_upload.py`**

```python
import os
import uuid

from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsContentCreator

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp'}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


class AuthoringUploadView(APIView):
    """POST /api/authoring/upload/ — store a lesson asset, return its absolute URL."""

    permission_classes = [IsContentCreator]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            allowed = ', '.join(sorted(ALLOWED_EXTENSIONS))
            return Response(
                {'error': f'File type not allowed. Allowed: {allowed}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file.size > MAX_UPLOAD_BYTES:
            return Response({'error': 'File too large (max 20 MB).'}, status=status.HTTP_400_BAD_REQUEST)

        path = default_storage.save(f'lesson_uploads/{uuid.uuid4().hex}{ext}', file)
        return Response(
            {'url': request.build_absolute_uri(default_storage.url(path))},
            status=status.HTTP_201_CREATED,
        )
```

Export in `backend/hub/views/__init__.py`, route in `backend/hub/urls.py`:

```python
    path('authoring/upload/', AuthoringUploadView.as_view(), name='authoring-upload'),
```

- [ ] **Step 3: Run tests — expect PASS**

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test hub.tests.test_authoring_upload -v 2`

- [ ] **Step 4: Add the file input to the lesson editor**

In `ModuleEditorPage.jsx` `LessonEditor`, extend the URL field block for `video/image/pdf` — after the existing URL `<input>` (inside the same `lesson-field` div), add for `pdf` and `image` only:

```jsx
            {['pdf', 'image'].includes(lesson.lesson_type) && !locked && (
              <div className="lesson-upload-row">
                <span className="lesson-upload-or">or</span>
                <label className="lesson-upload-btn">
                  <Upload size={14} />
                  {uploading ? 'Uploading…' : 'Upload file'}
                  <input
                    type="file"
                    accept={lesson.lesson_type === 'pdf' ? '.pdf' : 'image/*'}
                    hidden
                    disabled={uploading}
                    onChange={handleFileUpload}
                  />
                </label>
              </div>
            )}
```

Inside `LessonEditor` add the state + handler (imports: add `Upload` to the lucide-react import list, add `useState` to the react import, and `client` from `../api/client`):

```jsx
  const [uploading, setUploading] = useState(false)

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await client.post('/authoring/upload/', fd)
      onChange('content', res.data.url)
    } catch (err) {
      onChange('content', lesson.content) // keep as-is; surface error below
      window.alert(err.response?.data?.error ?? 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }
```

CSS in `ModuleEditorPage.css`:

```css
.lesson-upload-row { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.5rem; }
.lesson-upload-or { font-size: 0.8rem; color: #9ca3af; }
.lesson-upload-btn {
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.35rem 0.75rem; border: 1px solid #d1d5db; border-radius: 6px;
  font-size: 0.8rem; cursor: pointer; background: #fff;
}
.lesson-upload-btn:hover { background: #f9fafb; }
```

- [ ] **Step 5: Verify, lint, commit**

Run: `cd frontend && npm run lint && npm run build`; `cd backend && .venv/Scripts/uv.exe run ruff check . --fix`

```bash
git add backend/hub frontend/src/pages
git commit -m "feat: upload PDF and image lesson files from disk"
```

Deployment note: uploaded files land in `backend/media/` — in docker the `./backend:/app` volume already persists them. `MEDIA_URL` is served by Django only when `DEBUG=True` (current VM setup) — fine for the POC.

---

### Task 16: Content analytics — verify and harden (Issue 11)

The tester saw zeros/"No courses created yet". Investigation found no defect in the query (`created_by=request.user` is set on creation) — the likely explanations are (a) the screenshot predates her course creation, or (b) her lesson saves silently failed (fixed in Task 14). Harden with regression tests and a clearer empty state so this stops looking broken.

**Files:**
- Test: `backend/analytics/tests/test_analytics.py` (append)
- Modify: `frontend/src/pages/AnalyticsPage.jsx` (empty-state copy)

- [ ] **Step 1: Add regression tests**

Append to `backend/analytics/tests/test_analytics.py` (adapt to existing fixtures):

```python
    def test_unpublished_courses_counted(self):
        Course.objects.create(
            title='Draft course', pillar=self.pillar, level='beginner',
            duration_hours=1, is_published=False, created_by=self.creator,
        )
        res = self.client.get('/api/analytics/overview/')
        titles = [c['title'] for c in res.data['courses']]
        self.assertIn('Draft course', titles)

    def test_other_creators_courses_excluded(self):
        other = User.objects.create_user(username='other_creator2', password='pass12345')
        UserProfile.objects.create(user=other, user_type='content_creator')
        Course.objects.create(
            title='Not mine', pillar=self.pillar, level='beginner',
            duration_hours=1, is_published=True, created_by=other,
        )
        res = self.client.get('/api/analytics/overview/')
        titles = [c['title'] for c in res.data['courses']]
        self.assertNotIn('Not mine', titles)
```

Run: `cd backend && .venv/Scripts/uv.exe run manage.py test analytics -v 2`
Expected: PASS (they document current correct behaviour; if either fails, fix `AnalyticsOverviewView` accordingly).

- [ ] **Step 2: Clarify the empty state**

In `frontend/src/pages/AnalyticsPage.jsx`, find the "No courses created yet." empty state and replace the copy with:

```jsx
            <p>No courses created by you yet. Courses you create in Authoring will appear here — including drafts.</p>
```

- [ ] **Step 3: Verify + commit**

Run: `cd frontend && npm run lint && npm run build`

```bash
git add backend/analytics frontend/src/pages/AnalyticsPage.jsx
git commit -m "test: pin analytics course attribution, clarify empty state"
```

---

### Final: full verification

- [ ] Run the whole backend suite with coverage: `cd backend && .venv/Scripts/uv.exe run coverage run manage.py test hub analytics -v 1` — all pass
- [ ] `cd backend && .venv/Scripts/uv.exe run ruff check .` — clean
- [ ] `cd frontend && npm run lint && npm run build` — clean
- [ ] Dispatch final whole-branch code review

## Deployment notes (VM at 83.212.202.56)

After merging and pulling on the VM:

```bash
docker compose up -d --build            # rebuild images (new backend view files)
docker compose exec backend uv run python manage.py migrate
docker compose exec backend uv run python manage.py seed   # rebuilds pathway course ordering (Task 5)
```

`docker compose restart` is NOT enough — it does not re-read `.env` or rebuild code baked into images.

## Issue → Task map

| # | Issue (translated) | Task |
|---|---|---|
| 1 | EU + AIDEA logos | 1 |
| 2 | "Start" label invisible | 2 |
| 3 | Login lands on My Pathway | 3 |
| 4 | Pathway order vs level mismatch | 5 |
| 5 | Empty "Recommended for you" | 4 |
| 6 | Learning preferences update broken | 7 (+6) |
| 7 | Cannot submit content creator request | 6 |
| 8 | Pages broken until re-login | 6 |
| 9 | Quiz feedback/persistence confusion | 9 |
| 10 | Modules 1–2 not marked completed | 8 |
| 11 | Content analytics "doesn't work" | 16 (+14) |
| 12 | Show course author | 12 |
| 13 | Published courses not editable | 13 |
| 14 | No preview in lesson editor | 11 |
| 15 | PDF only via URL | 15 |
| 16 | Saved PDF activity disappeared | 14 |
| 17 | Publish dialog says no edit/unpublish | 13 |
| 18 | PDF should render inline | 10 |
| 19 | Video should play inline | 10 |
| 20 | Slow first video load | 10 (note: dev-server cold start, no code defect) |
