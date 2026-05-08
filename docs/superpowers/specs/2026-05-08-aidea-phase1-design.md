# AIDEA Phase 1 — Design Spec

**Date:** 2026-05-08
**Scope:** Docker + PostgreSQL + Redis + Celery + Onboarding Assessment + Personalized Pathways + Phase 1 Recommendation Engine
**Approach:** Sequential layers — infrastructure → backend → frontend → features
**Frontend:** React 19 + Vite (unchanged). New pages use shadcn/ui. Existing pages untouched.

---

## 1. Infrastructure

### Repository layout

```
aidea-poc/
├── docker-compose.yml          # dev: hot reload, DEBUG=True
├── docker-compose.prod.yml     # prod skeleton: Caddy, gunicorn, DEBUG=False
├── .env.example                # root-level env vars consumed by docker-compose
├── backend/
│   ├── Dockerfile              # multi-stage: dev target + prod target
│   └── ...
└── frontend/
    ├── Dockerfile              # dev target (npm run dev) + prod target (standalone)
    └── ...
```

### Docker services — dev (`docker-compose.yml`)

| Service    | Image                        | Notes                                                   |
|------------|------------------------------|---------------------------------------------------------|
| `db`       | `pgvector/pgvector:pg16`     | PostgreSQL 16 + pgvector pre-installed. Persistent vol. |
| `redis`    | `redis:7-alpine`             | Celery broker + future cache. Persistent vol.           |
| `backend`  | built from `backend/Dockerfile` | Django dev server, hot reload via volume mount. Depends on `db` + `redis`. |
| `celery`   | same image as backend        | `celery -A aidea worker -l info`. Same code volume.     |
| `frontend` | built from `frontend/Dockerfile` | `npm run dev` on port 3000. Volume-mounted `src/`.  |

### Docker services — prod skeleton (`docker-compose.prod.yml`)

Same services plus:
- `caddy` (`caddy:2-alpine`) — terminates HTTPS, proxies to `backend:8000` and `frontend:3000`
- Django runs via `gunicorn aidea.wsgi`
- Frontend runs as Vite static build output (HTML/JS/CSS served by Caddy)
- `DEBUG=False`, `SECRET_KEY` from environment secrets
- Not battle-tested for production launch — a clear path, not a finished deployment

### Backend dependency additions (`pyproject.toml`)

```toml
"psycopg[binary]>=3.2"           # PostgreSQL driver
"celery[redis]>=5.4"             # async task queue
"django-celery-beat>=2.7"        # periodic tasks via DB
"pgvector>=0.3"                  # Django ORM VectorField
"sentence-transformers>=3.3"     # all-MiniLM-L6-v2 embeddings
```

### Settings changes

- `DATABASES`: reads `DATABASE_URL` from env. PostgreSQL inside Docker; SQLite fallback for bare-metal dev (backward compatible — `manage.py test` outside Docker still works).
- `CELERY_BROKER_URL`: reads `REDIS_URL` from env.
- `CELERY_TASK_ALWAYS_EAGER`: `True` when `TEST=True` (synchronous execution in tests).

### Environment files

- `.env.example` at repo root — all vars consumed by docker-compose
- `backend/.env.example` — subset for bare-metal dev
- Both documented with comments

---

## 2. Backend

### New models

#### `UserProfile` extensions (new fields on existing model)

```python
competency_score     = IntegerField(default=0)           # 0–6, computed from assessment
subject_area         = CharField(choices=[...])          # stem / humanities / languages / arts / general
teaching_level       = CharField(choices=[...])          # primary / secondary / higher_ed / vocational / adult_ed
goals                = JSONField(default=list)           # e.g. ["save_time", "teach_about_ai"]
onboarding_completed = BooleanField(default=False)
```

Competency band mapping:
- 0–2 → `beginner`
- 3–4 → `intermediate`
- 5–6 → `advanced`

#### `LearningPath`

```python
name              CharField
slug              SlugField(unique=True)   # e.g. "beginner-foundations", used for fallback lookup
description       TextField
competency_min    IntegerField(0–6)
competency_max    IntegerField(0–6)
courses           ManyToManyField(Course, through=LearningPathCourse)
```

#### `LearningPathCourse` (through table)

```python
path    FK → LearningPath
course  FK → Course
order   PositiveSmallIntegerField
```

#### `UserLearningPath`

```python
user        OneToOneField → User
path        FK → LearningPath
assigned_at DateTimeField(auto_now_add=True)
```

#### `CourseEmbedding`

```python
course      OneToOneField → Course
embedding   VectorField(dimensions=384)   # all-MiniLM-L6-v2
computed_at DateTimeField(auto_now=True)
```

#### `CourseRecommendation`

```python
user    FK → User
course  FK → Course
score   FloatField              # cosine similarity (higher = more relevant)
reason  CharField               # human-readable, e.g. "Matches your beginner level and STEM focus"
computed_at DateTimeField(auto_now=True)

Meta: unique_together = ('user', 'course')
     ordering = ['-score']
```

---

### Onboarding assessment (6 questions)

| # | Question | Scoring |
|---|----------|---------|
| 1 | Which subject do you primarily teach? | Profile only (not scored) |
| 2 | What level do you teach? | Profile only (not scored) |
| 3 | An AI confidently summarises a student's essay but gets facts wrong. What do you do? | 0–2 pts |
| 4 | What does it mean when an AI model "hallucinates"? | 0–2 pts |
| 5 | Which of these is the best AI prompt for a lesson plan? | 0–2 pts |
| 6 | What are your main goals? (multi-select) | Pathway matching, not scored |

Total scored range: 0–6. Correct answer = 2 pts, partially correct = 1 pt, wrong = 0 pts.

**Goal slugs:** `save_time`, `teach_about_ai`, `prepare_students`, `stay_current`, `address_ethics`

---

### New API endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET`  | `/api/onboarding/` | teacher | Returns `{ completed: bool, competency_level: str\|null }` |
| `POST` | `/api/onboarding/` | teacher | Submit answers → score → assign path → fire Celery task |
| `GET`  | `/api/pathway/` | teacher | User's assigned path with ordered courses + completion status |
| `GET`  | `/api/recommendations/` | teacher | Pre-computed recs, empty list if none yet |

`POST /api/onboarding/` request body:
```json
{
  "subject_area": "stem",
  "teaching_level": "secondary",
  "answers": { "q3": "b", "q4": "b", "q5": "b" },
  "goals": ["save_time", "teach_about_ai"]
}
```

`POST /api/onboarding/` response:
```json
{
  "competency_score": 6,
  "competency_level": "advanced",
  "pathway_id": 3,
  "pathway_name": "Advanced AI Integration"
}
```

Onboarding is **teachers-only**. Content creators and admins receive `403`.
Submitting onboarding twice is idempotent — profile overwritten, path reassigned, recommendations recomputed.

---

### Celery tasks

| Task | Trigger | What it does |
|------|---------|--------------|
| `compute_course_embeddings(course_id)` | `post_save` signal on Course (published) | Embeds `title + " " + description` via all-MiniLM-L6-v2, saves to `CourseEmbedding` |
| `compute_user_recommendations(user_id)` | After successful onboarding POST | Builds profile text, embeds it, runs pgvector cosine similarity query, saves top-5 to `CourseRecommendation` |
| `recompute_all_recommendations` | Celery Beat, nightly 02:00 UTC | Re-runs `compute_user_recommendations` for all users with completed onboarding |

**Profile text format for embedding:**
```
"{subject_area} teacher, {teaching_level}, competency {score}/6, goals: {goals_joined}"
```

**Recommendation filtering:**
1. Exclude courses the user is already enrolled in
2. Exclude courses above user's level (advanced courses hidden from beginners)
3. Take top-5 by cosine similarity score

**Reason string generation:**
- Beginner: "Matches your beginner level and {subject_area} focus"
- Intermediate/Advanced: "Recommended based on your profile and learning goals"

---

### Pathway assignment logic

```
POST /api/onboarding/ received
  → compute competency_score (0–6)
  → query: LearningPath where competency_min <= score <= competency_max
  → if found: assign first match
  → if not found: assign fallback path (slug="beginner-foundations", always seeded)
  → create/update UserLearningPath
  → compute_user_recommendations.delay(user_id)
```

Seed data includes 3 pre-built paths:
- `beginner-foundations` (score 0–2)
- `intermediate-growth` (score 3–4)
- `advanced-integration` (score 5–6)

---

### Auth response update

`POST /api/auth/login/` response extended to include:
```json
{
  "access": "...",
  "refresh": "...",
  "user": {
    "id": 1,
    "username": "demo_teacher",
    "user_type": "teacher",
    "onboarding_completed": false
  }
}
```

---

## 3. Frontend

### New pages

**`/onboarding` → `src/pages/OnboardingPage.jsx`**

- Full-screen wizard, no Layout wrapper (no sidebar/header)
- Progress bar: step X of 6
- Steps 1–5: single-question radio group per step
- Step 6: multi-select checkboxes (goals)
- Back / Next navigation; Next disabled until answer selected
- On submit: shows "Building your learning path..." spinner
- On API success: navigate to `/pathway`
- Only teachers reach this page (route guard handles redirection)

**`/pathway` → `src/pages/PathwayPage.jsx`**

- Layout wrapper (sidebar + header)
- Header: path name + description + competency level badge
- Overall progress bar: X of N courses completed
- Ordered course list: title, pillar tag, duration, status (not started / in progress / completed)
- "Continue" CTA button on the next incomplete course → navigates to that course's detail page

**`HomePage.jsx` — recommendations section added**

- New section below existing pillar cards: "Recommended for you"
- Horizontal row of up to 5 course cards
- Each card: course title, pillar tag, reason string, "Start" button
- Skeleton loader shown while recommendations are computing (empty array but onboarding completed)
- Section hidden entirely if user hasn't completed onboarding

---

### Route guard — `RequireOnboarding`

Added to `App.jsx`, wraps all teacher routes inside the auth guard:

```
/login                      → LoginPage (public)
/onboarding                 → OnboardingPage (auth required, no Layout, no RequireOnboarding)
/* all other routes:
    → RequireOnboarding
        if teacher && !onboarding_completed → redirect /onboarding
        else → Layout → page
```

`AuthContext` updated:
- Login response now includes `onboarding_completed`
- Stored in context state alongside `user_type`

---

### Sidebar update

New nav item added for teachers: **"My Pathway"** → `/pathway`
Hidden for `content_creator` and `admin` user types.

---

### shadcn/ui integration

Installed once via `npx shadcn init` in the `frontend/` directory. Used **only** on `OnboardingPage` and `PathwayPage`. Existing pages keep their current CSS files — no migration.

Components used: `Button`, `Card`, `CardContent`, `Progress`, `RadioGroup`, `RadioGroupItem`, `Checkbox`, `Badge`, `Skeleton`, `Label`.

---

## 4. End-to-End Flow

### Happy path — new teacher

```
1. Login (accounts created via admin or seed command)
2. JWT response → onboarding_completed: false
3. RequireOnboarding → redirect /onboarding
4. Complete 6-step wizard → POST /api/onboarding/
5. Backend: score → assign path → fire Celery task → respond
6. Frontend: navigate to /pathway
7. Celery (background): embed profile → cosine similarity → save recommendations
8. User visits / (home) → recommendations section shows top-5 courses
```

### Error handling

| Scenario | Behaviour |
|----------|-----------|
| No matching `LearningPath` for competency score | Assign hardcoded fallback `beginner-foundations` path (always seeded) |
| Celery task fails / Redis unreachable | `CourseRecommendation` stays empty; recommendations section hidden — no crash |
| `CourseEmbedding` missing for a course | That course is skipped in the similarity query |
| Teacher submits onboarding twice | Idempotent: profile overwritten, path reassigned, recommendations recomputed |
| Content creator / admin hits `POST /api/onboarding/` | `403 Forbidden` |
| User visits `/pathway` before onboarding | `GET /api/pathway/` returns `404` (no `UserLearningPath` exists yet) |

---

## 5. Tests Added

| File | What it covers |
|------|---------------|
| `hub/tests/test_onboarding.py` | POST answers → correct score computed, profile saved, path assigned, Celery task fired |
| `hub/tests/test_competency_scoring.py` | Unit: all answer combinations produce correct scores |
| `hub/tests/test_pathway_assignment.py` | Correct path for each band; fallback when no path matches |
| `hub/tests/test_recommendations_api.py` | GET returns pre-computed recs; empty list when none; 403 for non-teachers |
| `hub/tests/test_pathway_api.py` | GET returns ordered courses with completion status; 404 before onboarding |

Celery tasks run synchronously in tests via `CELERY_TASK_ALWAYS_EAGER = True` set in test settings.

---

## 6. Out of Scope (future phases)

- Meilisearch full-text search (Phase 3)
- Collaborative filtering / "teachers like you" recommendations (Phase 2 — needs 200+ users)
- Badges & gamification (Phase 2)
- Engagement / time tracking events (Phase 2)
- xAPI / Ralph LRS (Phase 4)
- TypeScript migration of existing frontend pages
- Next.js migration
