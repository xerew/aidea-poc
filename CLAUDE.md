# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIDEA POC is a Teacher AI Training Platform — a monorepo with a Django REST API backend and a React/Vite SPA frontend. Teachers learn to use, teach about, and prepare students for AI through structured courses organized into three learning pillars.

## Commands

### Backend (Django)

The virtualenv is at `backend/.venv`. Use `.venv/Scripts/uv.exe run` — `uv` is bundled inside the venv and is the preferred runner; system `python`/`uv` may not be on PATH.

```bash
cd backend
.venv/Scripts/uv.exe run manage.py migrate   # Apply migrations
.venv/Scripts/uv.exe run manage.py seed      # Populate DB with demo data (3 pillars, 11 courses, 55+ modules, demo_teacher/demo1234, demo_creator/demo1234)
.venv/Scripts/uv.exe run manage.py runserver # Start dev server at localhost:8000
```

**Testing:**
```bash
cd backend
.venv/Scripts/uv.exe run coverage run manage.py test hub --verbosity=2   # Run all tests
.venv/Scripts/uv.exe run coverage run manage.py test hub.tests.TestFoo   # Run a single test class
```

**Linting:**
```bash
cd backend
.venv/Scripts/uv.exe run ruff check .   # Line length 100; E501 ignored
```

**Environment:** Copy `backend/.env.example` to `backend/.env` and set `SECRET_KEY`.

### Frontend (React/Vite)

```bash
cd frontend
npm ci           # Install dependencies
npm run dev      # Start dev server at localhost:5173
npm run lint     # ESLint
npm run build    # Production build (requires VITE_API_URL env var)
```

**Environment:** Copy `frontend/.env.example` to `frontend/.env.local` and set `VITE_API_URL=http://localhost:8000/api`.

**Icons:** Use `lucide-react` for all icons (`import { IconName } from 'lucide-react'`).

## Architecture

### Backend (`backend/`)

Two Django apps under the `aidea` project: `hub` (courses, enrollments, authoring) and `analytics` (content creator analytics — reads hub models, no own models). All API routes are under `/api/`.

**Data model hierarchy:**
```
LearningPillar → Course → Module
User (+ UserProfile) → Enrollment → Course
```

- `UserProfile` extends Django User with `user_type` (teacher/content_creator/admin)
- `Enrollment` tracks per-user progress (completion %, current module) for a course

**API endpoints** (`hub/urls.py`):
- `POST /api/auth/login/` — returns JWT access+refresh tokens with user data
- `POST /api/auth/refresh/` — token refresh
- `POST /api/auth/logout/` — blacklists refresh token
- `GET /api/courses/` — list with `?pillar=`, `?level=`, `?search=` filters
- `GET /api/courses/<id>/` — detail with modules
- `POST /api/courses/<id>/enroll/` — enroll authenticated user
- `GET /api/home/` — dashboard: in-progress enrollment + pillar summaries
- `GET /api/my-learning/` — user's enrollments split into `continue_learning`, `in_progress`, `completed`
- `GET /api/analytics/overview/` — content creator analytics: summary stats + per-course breakdown (content_creator only)

**Auth:** JWT via `djangorestframework-simplejwt`. 60-min access tokens, 7-day refresh with rotation. Token blacklisting enabled for logout.

**Admin:** Jazzmin-themed Django admin at `/admin/` with inline module editing.

### Frontend (`frontend/src/`)

React 19 SPA with Vite, using react-router-dom v7 and Axios.

**Auth flow:** `AuthContext` manages JWT tokens in localStorage. `api/client.js` (Axios instance) has:
- Request interceptor: attaches `Authorization: Bearer <token>` header
- Response interceptor: auto-refreshes on 401; redirects to `/login` on refresh failure

**Routing** (`App.jsx`): Public route `/login`; all other routes are wrapped in `Layout` (Header + Sidebar + Footer) and require authentication.

**Pages:**
- `MyLearningPage` — continue-learning banner + in-progress and completed enrollment cards
- `AnalyticsPage` — content creator analytics dashboard (shows restricted message for other roles)
- `HomePage` — continue-learning banner (latest enrollment) + pillar cards with progress
- `CoursesPage` — searchable grid with pillar/level filters
- `CourseDetailPage` — course info, module list, enroll button, progress
- `PlaceholderPage` — stub for `/learning`, `/analytics`, `/profile`, `/authoring`

Styling uses per-component CSS files (no CSS framework).

### CI/CD (`.github/workflows/ci.yml`)

Runs on push/PR to `master`. Two parallel jobs:
- **backend**: Python 3.14 + uv → ruff lint → coverage test (70% minimum) → upload to Codecov
- **frontend**: Node 22 + npm → ESLint → Vite build → upload `dist/`
