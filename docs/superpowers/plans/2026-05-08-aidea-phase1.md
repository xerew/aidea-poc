# AIDEA Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Docker + PostgreSQL + Redis + Celery infrastructure, an AI Competency Assessment onboarding flow, personalized learning pathways, and a Phase 1 pgvector recommendation engine to the existing Django/React POC.

**Architecture:** Sequential layers — infrastructure first, then backend models + APIs (TDD), then frontend new pages. Existing React pages are untouched. Three new React pages (Onboarding, Pathway, Recommendations on Home) use shadcn/ui components.

**Tech Stack:** Django 6 + DRF, PostgreSQL 16 + pgvector, Redis 7, Celery 5, sentence-transformers (all-MiniLM-L6-v2), React 19 + Vite, shadcn/ui + Tailwind v4, Docker Compose

**Spec:** `docs/superpowers/specs/2026-05-08-aidea-phase1-design.md`

---

## File Map

**Create:**
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `Caddyfile`
- `.env.example`
- `docker/postgres-init.sql`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/Caddyfile.spa`
- `backend/aidea/celery.py`
- `backend/hub/models/pathway.py`
- `backend/hub/models/recommendations.py`
- `backend/hub/tasks.py`
- `backend/hub/signals.py`
- `backend/hub/serializers/onboarding.py`
- `backend/hub/serializers/pathway.py`
- `backend/hub/views/onboarding.py`
- `backend/hub/views/pathway.py`
- `backend/hub/views/recommendations.py`
- `backend/hub/management/commands/seed_data/pathways.py`
- `backend/hub/tests/test_competency_scoring.py`
- `backend/hub/tests/test_onboarding.py`
- `backend/hub/tests/test_pathway.py`
- `backend/hub/tests/test_recommendations.py`
- `frontend/src/components/RequireOnboarding.jsx`
- `frontend/src/pages/OnboardingPage.jsx`
- `frontend/src/pages/OnboardingPage.css`
- `frontend/src/pages/PathwayPage.jsx`
- `frontend/src/pages/PathwayPage.css`

**Modify:**
- `backend/pyproject.toml` — add 6 new dependencies
- `backend/aidea/settings.py` — DATABASE_URL, Redis, Celery, STATIC_ROOT, beat schedule
- `backend/aidea/__init__.py` — import celery app
- `backend/hub/models/user.py` — 5 new fields on UserProfile
- `backend/hub/models/__init__.py` — export new models
- `backend/hub/apps.py` — register signals in ready()
- `backend/hub/views/permissions.py` — add IsTeacher
- `backend/hub/serializers/auth.py` — add onboarding_completed to UserProfileSerializer
- `backend/hub/serializers/__init__.py` — export new serializers
- `backend/hub/views/__init__.py` — export new views
- `backend/hub/urls.py` — 4 new URL patterns
- `backend/hub/management/commands/seed.py` — call seed_pathways()
- `frontend/vite.config.js` — add path alias + Tailwind plugin
- `frontend/src/index.css` — add Tailwind import at top
- `frontend/src/context/AuthContext.jsx` — add updateUser()
- `frontend/src/App.jsx` — add new routes + RequireOnboarding
- `frontend/src/components/layout/Sidebar.jsx` — add My Pathway nav item
- `frontend/src/pages/HomePage.jsx` — add recommendations section
- `.github/workflows/ci.yml` — add PostgreSQL service to backend job

---

## Phase 1 — Infrastructure

### Task 1: Backend dependencies + settings

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/aidea/settings.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Add new dependencies to pyproject.toml**

Replace the `[project]` dependencies list:

```toml
[project]
name = "aidea-backend"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "django==6.0.3",
    "djangorestframework==3.17.0",
    "djangorestframework-simplejwt==5.5.1",
    "django-cors-headers==4.9.0",
    "django-jazzmin==3.0.4",
    "python-dotenv==1.2.2",
    "psycopg[binary]>=3.2",
    "dj-database-url>=2.3",
    "celery[redis]>=5.4",
    "django-celery-beat>=2.7",
    "pgvector>=0.3",
    "sentence-transformers>=3.3",
    "gunicorn>=23.0",
]
```

- [ ] **Step 2: Regenerate the lock file**

```bash
cd backend
.venv/Scripts/uv.exe lock
```

Expected: `uv.lock` updated with new packages (no errors).

- [ ] **Step 3: Update settings.py — database, Celery, static root**

In `backend/aidea/settings.py`, replace the `DATABASES` block and add new config. Full changes:

```python
# At the top, add this import after existing imports:
import dj_database_url
```

Replace the existing `DATABASES` block:

```python
# Database — PostgreSQL when DATABASE_URL is set, SQLite fallback for bare-metal dev
_DB_URL = os.getenv('DATABASE_URL')
if _DB_URL:
    DATABASES = {'default': dj_database_url.parse(_DB_URL, conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

Add after the `DATABASES` block:

```python
# Static files root (used by collectstatic in production)
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Celery
REDIS_URL = os.getenv('REDIS_URL', '')
CELERY_BROKER_URL = REDIS_URL or 'memory://'
CELERY_RESULT_BACKEND = REDIS_URL or 'cache+memory://'
if 'test' in sys.argv or not REDIS_URL:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# Celery Beat — nightly recommendation recompute
from celery.schedules import crontab  # noqa: E402
CELERY_BEAT_SCHEDULE = {
    'recompute-all-recommendations-nightly': {
        'task': 'hub.tasks.recompute_all_recommendations',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

Add `'django_celery_beat'` to `INSTALLED_APPS` after `'rest_framework_simplejwt.token_blacklist'`:

```python
    'django_celery_beat',
```

- [ ] **Step 4: Update backend/.env.example**

Replace the file contents:

```
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=

# Database — leave empty to use SQLite (bare-metal dev without Docker)
# Set to postgresql://aidea:aidea@localhost:5432/aidea when using Docker
DATABASE_URL=

# Redis — leave empty to run Celery tasks synchronously (bare-metal dev)
# Set to redis://localhost:6379/0 when using Docker or local Redis
REDIS_URL=
```

- [ ] **Step 5: Verify bare-metal dev still works**

```bash
cd backend
.venv/Scripts/uv.exe run manage.py migrate
.venv/Scripts/uv.exe run manage.py test hub --verbosity=2
```

Expected: all existing tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/aidea/settings.py backend/.env.example
git commit -m "feat: add postgres/redis/celery dependencies and settings"
```

---

### Task 2: Celery application

**Files:**
- Create: `backend/aidea/celery.py`
- Modify: `backend/aidea/__init__.py`

- [ ] **Step 1: Create celery.py**

```python
# backend/aidea/celery.py
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aidea.settings')

app = Celery('aidea')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

- [ ] **Step 2: Update __init__.py**

```python
# backend/aidea/__init__.py
from .celery import app as celery_app

__all__ = ('celery_app',)
```

- [ ] **Step 3: Commit**

```bash
git add backend/aidea/celery.py backend/aidea/__init__.py
git commit -m "feat: add Celery application"
```

---

### Task 3: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Create the multi-stage Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.14-slim AS base

WORKDIR /app

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

# ── dev ──────────────────────────────────────────────────────────────────────
FROM base AS dev

RUN uv sync --frozen --group dev

COPY . .

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]

# ── prod ─────────────────────────────────────────────────────────────────────
FROM base AS prod

RUN uv sync --frozen

COPY . .

RUN uv run python manage.py collectstatic --noinput

CMD ["uv", "run", "gunicorn", "aidea.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

- [ ] **Step 2: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat: add backend Dockerfile (dev + prod targets)"
```

---

### Task 4: Frontend Dockerfile

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/Caddyfile.spa`

- [ ] **Step 1: Create the frontend Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:22-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./

# ── dev ──────────────────────────────────────────────────────────────────────
FROM base AS dev

RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ── prod ─────────────────────────────────────────────────────────────────────
FROM base AS prod-builder

ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine AS prod
COPY --from=prod-builder /app/dist /srv
COPY Caddyfile.spa /etc/caddy/Caddyfile
EXPOSE 80
```

- [ ] **Step 2: Create Caddyfile.spa**

```
# frontend/Caddyfile.spa
:80 {
    root * /srv
    try_files {path} /index.html
    file_server
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/Dockerfile frontend/Caddyfile.spa
git commit -m "feat: add frontend Dockerfile (dev + prod targets)"
```

---

### Task 5: docker-compose.yml (dev)

**Files:**
- Create: `docker-compose.yml`
- Create: `docker/postgres-init.sql`
- Create: `.env.example`

- [ ] **Step 1: Create postgres-init.sql**

```bash
mkdir docker
```

```sql
-- docker/postgres-init.sql
CREATE EXTENSION IF NOT EXISTS vector;
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
# docker-compose.yml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: aidea
      POSTGRES_USER: aidea
      POSTGRES_PASSWORD: aidea
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres-init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aidea"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      target: dev
    env_file: .env
    environment:
      DATABASE_URL: postgresql://aidea:aidea@db:5432/aidea
      REDIS_URL: redis://redis:6379/0
      DEBUG: "True"
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: >
      sh -c "uv run python manage.py migrate &&
             uv run python manage.py runserver 0.0.0.0:8000"

  celery:
    build:
      context: ./backend
      target: dev
    env_file: .env
    environment:
      DATABASE_URL: postgresql://aidea:aidea@db:5432/aidea
      REDIS_URL: redis://redis:6379/0
      DEBUG: "True"
    volumes:
      - ./backend:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uv run celery -A aidea worker -l info

  celery-beat:
    build:
      context: ./backend
      target: dev
    env_file: .env
    environment:
      DATABASE_URL: postgresql://aidea:aidea@db:5432/aidea
      REDIS_URL: redis://redis:6379/0
      DEBUG: "True"
    volumes:
      - ./backend:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uv run celery -A aidea beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

  frontend:
    build:
      context: ./frontend
      target: dev
    environment:
      VITE_API_URL: http://localhost:8000/api
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    ports:
      - "5173:5173"

volumes:
  postgres_data:
  redis_data:
```

- [ ] **Step 3: Create root .env.example**

```
# .env.example — root-level env file consumed by docker-compose
# Copy to .env and fill in values

# Django
SECRET_KEY=change-me-to-a-long-random-string

# For production: your domain
DOMAIN=yourdomain.com
VITE_API_URL=https://yourdomain.com/api
```

- [ ] **Step 4: Create root .env from example**

```bash
cp .env.example .env
```

Open `.env` and set `SECRET_KEY` to any string (e.g. `dev-secret-key`).

- [ ] **Step 5: Add .env to .gitignore**

Open `.gitignore` and add:
```
.env
backend/.env
```

- [ ] **Step 6: Boot Docker and verify**

```bash
docker compose up --build
```

Expected:
- `db` starts and shows `database system is ready to accept connections`
- `redis` starts and shows `Ready to accept connections`
- `backend` runs migrations then starts on port 8000
- `celery` starts and shows `[tasks] hub.tasks...`
- `frontend` starts on port 5173

Visit `http://localhost:8000/api/home/` — should return 401 (not authenticated). That means it's working.

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml docker/postgres-init.sql .env.example .gitignore
git commit -m "feat: add docker-compose dev environment"
```

---

### Task 6: docker-compose.prod.yml skeleton

**Files:**
- Create: `docker-compose.prod.yml`
- Create: `Caddyfile`

- [ ] **Step 1: Create docker-compose.prod.yml**

```yaml
# docker-compose.prod.yml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: aidea
      POSTGRES_USER: aidea
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres-init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      target: prod
    environment:
      DATABASE_URL: postgresql://aidea:${POSTGRES_PASSWORD}@db:5432/aidea
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY:?SECRET_KEY is required}
      DEBUG: "False"
      ALLOWED_HOSTS: ${DOMAIN:-localhost}
    volumes:
      - static_files:/app/staticfiles
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery:
    build:
      context: ./backend
      target: prod
    environment:
      DATABASE_URL: postgresql://aidea:${POSTGRES_PASSWORD}@db:5432/aidea
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "False"
    command: uv run celery -A aidea worker -l warning
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery-beat:
    build:
      context: ./backend
      target: prod
    environment:
      DATABASE_URL: postgresql://aidea:${POSTGRES_PASSWORD}@db:5432/aidea
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "False"
    command: uv run celery -A aidea beat -l warning --scheduler django_celery_beat.schedulers:DatabaseScheduler
    depends_on:
      - db
      - redis
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      target: prod
      args:
        VITE_API_URL: ${VITE_API_URL:?VITE_API_URL is required}
    restart: unless-stopped

  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - static_files:/srv/static
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  static_files:
  caddy_data:
  caddy_config:
```

- [ ] **Step 2: Create root Caddyfile**

```
# Caddyfile — production reverse proxy
{$DOMAIN:localhost} {
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle /admin/* {
        reverse_proxy backend:8000
    }
    handle /static/* {
        root * /srv
        file_server
    }
    handle {
        reverse_proxy frontend:80
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.prod.yml Caddyfile
git commit -m "feat: add production docker-compose skeleton and Caddyfile"
```

---

## Phase 2 — Backend Models

### Task 7: UserProfile new fields + migration

**Files:**
- Modify: `backend/hub/models/user.py`

- [ ] **Step 1: Update UserProfile with 5 new fields**

Replace the contents of `backend/hub/models/user.py`:

```python
from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    class UserType(models.TextChoices):
        TEACHER         = 'teacher',         'Teacher'
        CONTENT_CREATOR = 'content_creator', 'Content Creator'
        ADMIN           = 'admin',           'Admin'

    class SubjectArea(models.TextChoices):
        STEM       = 'stem',       'STEM'
        HUMANITIES = 'humanities', 'Humanities'
        LANGUAGES  = 'languages',  'Languages'
        ARTS       = 'arts',       'Arts'
        GENERAL    = 'general',    'General / Multiple'

    class TeachingLevel(models.TextChoices):
        PRIMARY    = 'primary',    'Primary (K-6)'
        SECONDARY  = 'secondary',  'Secondary (7-12)'
        HIGHER_ED  = 'higher_ed',  'Higher Education'
        VOCATIONAL = 'vocational', 'Vocational'
        ADULT_ED   = 'adult_ed',   'Adult Education'

    user                 = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type            = models.CharField(max_length=20, choices=UserType.choices, default=UserType.TEACHER)
    avatar_initials      = models.CharField(max_length=4, blank=True)
    competency_score     = models.PositiveSmallIntegerField(default=0)
    subject_area         = models.CharField(max_length=20, choices=SubjectArea.choices, blank=True)
    teaching_level       = models.CharField(max_length=20, choices=TeachingLevel.choices, blank=True)
    goals                = models.JSONField(default=list, blank=True)
    onboarding_completed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.get_user_type_display()})'
```

- [ ] **Step 2: Generate and apply migration**

```bash
cd backend
.venv/Scripts/uv.exe run python manage.py makemigrations hub --name add_onboarding_fields_to_userprofile
.venv/Scripts/uv.exe run python manage.py migrate
```

Expected output: `Applying hub.0010_add_onboarding_fields_to_userprofile... OK`

- [ ] **Step 3: Verify existing tests still pass**

```bash
.venv/Scripts/uv.exe run python manage.py test hub --verbosity=2
```

Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/hub/models/user.py backend/hub/migrations/
git commit -m "feat: add onboarding fields to UserProfile"
```

---

### Task 8: Pathway models + migration

**Files:**
- Create: `backend/hub/models/pathway.py`
- Modify: `backend/hub/models/__init__.py`

- [ ] **Step 1: Create pathway.py**

```python
# backend/hub/models/pathway.py
from django.contrib.auth.models import User
from django.db import models

from .content import Course


class LearningPath(models.Model):
    name           = models.CharField(max_length=200)
    slug           = models.SlugField(unique=True)
    description    = models.TextField(blank=True)
    competency_min = models.PositiveSmallIntegerField(default=0)
    competency_max = models.PositiveSmallIntegerField(default=6)
    courses        = models.ManyToManyField(Course, through='LearningPathCourse', blank=True)

    class Meta:
        ordering = ['competency_min']

    def __str__(self):
        return self.name


class LearningPathCourse(models.Model):
    path   = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='path_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    order  = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('path', 'course')

    def __str__(self):
        return f'{self.path.name} — {self.course.title} (#{self.order})'


class UserLearningPath(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='learning_path')
    path        = models.ForeignKey(LearningPath, on_delete=models.PROTECT)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} → {self.path.name}'
```

- [ ] **Step 2: Update models/__init__.py**

```python
from .content import Course, LearningPillar, Lesson, Module
from .enrollment import Enrollment, LessonProgress
from .history import CourseEditHistory
from .pathway import LearningPath, LearningPathCourse, UserLearningPath
from .recommendations import CourseEmbedding, CourseRecommendation
from .user import UserProfile

__all__ = [
    'Course',
    'CourseEditHistory',
    'CourseEmbedding',
    'CourseRecommendation',
    'Enrollment',
    'Lesson',
    'LearningPath',
    'LearningPathCourse',
    'LearningPillar',
    'LessonProgress',
    'Module',
    'UserLearningPath',
    'UserProfile',
]
```

Note: `recommendations.py` is created in the next task — don't apply this `__init__` update until after Task 9.

- [ ] **Step 3: Generate migration**

```bash
cd backend
.venv/Scripts/uv.exe run python manage.py makemigrations hub --name add_learningpath_models
```

Expected: creates `hub/migrations/0011_add_learningpath_models.py`.

- [ ] **Step 4: Commit**

```bash
git add backend/hub/models/pathway.py
git commit -m "feat: add LearningPath, LearningPathCourse, UserLearningPath models"
```

---

### Task 9: Recommendation models + pgvector migration

**Files:**
- Create: `backend/hub/models/recommendations.py`
- Modify: `backend/hub/models/__init__.py` (apply the update from Task 8 Step 2)
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Create recommendations.py**

```python
# backend/hub/models/recommendations.py
from django.contrib.auth.models import User
from django.db import models
from pgvector.django import VectorField

from .content import Course


class CourseEmbedding(models.Model):
    course      = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='embedding')
    embedding   = VectorField(dimensions=384)
    computed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Embedding for {self.course.title}'


class CourseRecommendation(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='recommendations')
    score       = models.FloatField()
    reason      = models.CharField(max_length=200)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-score']

    def __str__(self):
        return f'{self.user.username} → {self.course.title} ({self.score:.2f})'
```

- [ ] **Step 2: Apply the models/__init__.py update from Task 8 Step 2**

Now update `backend/hub/models/__init__.py` with the full import list shown in Task 8 Step 2.

- [ ] **Step 3: Generate migration with pgvector extension**

```bash
cd backend
.venv/Scripts/uv.exe run python manage.py makemigrations hub --name add_recommendation_models
```

Open the generated migration file (`0012_add_recommendation_models.py`) and add a `RunPython` operation **before** the `CreateModel` operations to create the pgvector extension on PostgreSQL:

```python
from django.db import migrations
from pgvector.django import VectorField


def create_vector_extension(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('CREATE EXTENSION IF NOT EXISTS vector')


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0011_add_learningpath_models'),
    ]

    operations = [
        migrations.RunPython(create_vector_extension, migrations.RunPython.noop),
        migrations.CreateModel(
            name='CourseEmbedding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('embedding', VectorField(dimensions=384)),
                ('computed_at', models.DateTimeField(auto_now=True)),
                ('course', models.OneToOneField(on_delete=models.CASCADE, related_name='embedding', to='hub.course')),
            ],
        ),
        migrations.CreateModel(
            name='CourseRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField()),
                ('reason', models.CharField(max_length=200)),
                ('computed_at', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(on_delete=models.CASCADE, related_name='recommendations', to='hub.course')),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='recommendations', to='auth.user')),
            ],
            options={
                'ordering': ['-score'],
                'unique_together': {('user', 'course')},
            },
        ),
    ]
```

- [ ] **Step 4: Update CI to use PostgreSQL**

In `.github/workflows/ci.yml`, update the `backend` job to add a PostgreSQL service and DATABASE_URL:

```yaml
  backend:
    name: Backend — lint · test · coverage
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: aidea_test
          POSTGRES_USER: aidea
          POSTGRES_PASSWORD: aidea
        options: >-
          --health-cmd "pg_isready -U aidea"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    env:
      DJANGO_SETTINGS_MODULE: aidea.settings
      SECRET_KEY: ci-only-secret-key-not-used-in-production
      DEBUG: "True"
      ALLOWED_HOSTS: "localhost"
      DATABASE_URL: postgresql://aidea:aidea@localhost:5432/aidea_test
```

- [ ] **Step 5: Commit**

```bash
git add backend/hub/models/recommendations.py backend/hub/models/__init__.py backend/hub/migrations/ .github/workflows/ci.yml
git commit -m "feat: add CourseEmbedding and CourseRecommendation models with pgvector"
```

---

### Task 10: Celery tasks + signals

**Files:**
- Create: `backend/hub/tasks.py`
- Create: `backend/hub/signals.py`
- Modify: `backend/hub/apps.py`

- [ ] **Step 1: Create hub/tasks.py**

```python
# backend/hub/tasks.py
from celery import shared_task


@shared_task
def compute_course_embeddings(course_id: int) -> None:
    from sentence_transformers import SentenceTransformer

    from hub.models import Course
    from hub.models.recommendations import CourseEmbedding

    course = Course.objects.get(pk=course_id)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    text = f"{course.title} {course.description}"
    embedding = model.encode(text).tolist()
    CourseEmbedding.objects.update_or_create(
        course=course,
        defaults={'embedding': embedding},
    )


@shared_task
def compute_user_recommendations(user_id: int) -> None:
    from pgvector.django import CosineDistance
    from sentence_transformers import SentenceTransformer
    from django.contrib.auth.models import User

    from hub.models.enrollment import Enrollment
    from hub.models.recommendations import CourseEmbedding, CourseRecommendation

    user = User.objects.select_related('profile').get(pk=user_id)
    profile = user.profile

    goals_str = ', '.join(profile.goals) if profile.goals else 'general'
    subject = profile.get_subject_area_display() if profile.subject_area else 'general'
    level_str = profile.get_teaching_level_display() if profile.teaching_level else 'unknown'
    profile_text = (
        f"{subject} teacher, {level_str}, "
        f"competency {profile.competency_score}/6, goals: {goals_str}"
    )

    model = SentenceTransformer('all-MiniLM-L6-v2')
    user_embedding = model.encode(profile_text).tolist()

    enrolled_ids = set(
        Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
    )

    score = profile.competency_score
    level_num = 0 if score <= 2 else (1 if score <= 4 else 2)
    level_name = ('beginner', 'intermediate', 'advanced')[level_num]
    course_level_nums = {'beginner': 0, 'intermediate': 1, 'advanced': 2}

    candidates = (
        CourseEmbedding.objects
        .select_related('course__pillar')
        .exclude(course_id__in=enrolled_ids)
        .filter(course__is_published=True)
        .annotate(distance=CosineDistance('embedding', user_embedding))
        .order_by('distance')[:15]
    )

    filtered = []
    for emb in candidates:
        course_level = course_level_nums.get(emb.course.level, 0)
        if course_level <= level_num + 1:
            filtered.append(emb)
        if len(filtered) >= 5:
            break

    CourseRecommendation.objects.filter(user=user).delete()

    subject_display = profile.subject_area.replace('_', ' ') if profile.subject_area else 'general'
    for emb in filtered:
        CourseRecommendation.objects.create(
            user=user,
            course=emb.course,
            score=max(0.0, 1.0 - float(emb.distance)),
            reason=f"Matches your {level_name} level and {subject_display} focus",
        )


@shared_task
def recompute_all_recommendations() -> None:
    from django.contrib.auth.models import User

    user_ids = list(
        User.objects.filter(
            profile__onboarding_completed=True,
        ).values_list('id', flat=True)
    )
    for uid in user_ids:
        compute_user_recommendations.delay(uid)
```

- [ ] **Step 2: Create hub/signals.py**

```python
# backend/hub/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from hub.models.content import Course


@receiver(post_save, sender=Course)
def course_published_handler(sender, instance, created, **kwargs):
    if instance.is_published:
        from hub.tasks import compute_course_embeddings
        compute_course_embeddings.delay(instance.pk)
```

- [ ] **Step 3: Update apps.py to register signals**

```python
# backend/hub/apps.py
from django.apps import AppConfig


class HubConfig(AppConfig):
    name = 'hub'

    def ready(self):
        import hub.signals  # noqa: F401
```

- [ ] **Step 4: Commit**

```bash
git add backend/hub/tasks.py backend/hub/signals.py backend/hub/apps.py
git commit -m "feat: add Celery tasks for embeddings and recommendations, register signals"
```

---

## Phase 3 — Backend APIs (TDD)

### Task 11: IsTeacher permission + auth serializer update

**Files:**
- Modify: `backend/hub/views/permissions.py`
- Modify: `backend/hub/serializers/auth.py`

- [ ] **Step 1: Write failing test for IsTeacher permission**

Add a new test class to `backend/hub/tests/test_auth.py`:

```python
class IsTeacherPermissionTestCase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='t1', password='pass')
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)
        self.creator = User.objects.create_user(username='c1', password='pass')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)

    def test_login_includes_onboarding_completed(self):
        response = self.client.post(reverse('auth-login'), {
            'username': 't1', 'password': 'pass',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('onboarding_completed', response.data['user']['profile'])
        self.assertFalse(response.data['user']['profile']['onboarding_completed'])
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd backend
.venv/Scripts/uv.exe run python manage.py test hub.tests.test_auth.IsTeacherPermissionTestCase --verbosity=2
```

Expected: FAIL — `onboarding_completed` not in response.

- [ ] **Step 3: Update UserProfileSerializer to include onboarding_completed**

In `backend/hub/serializers/auth.py`:

```python
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['user_type', 'avatar_initials', 'onboarding_completed']
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/Scripts/uv.exe run python manage.py test hub.tests.test_auth.IsTeacherPermissionTestCase --verbosity=2
```

Expected: PASS.

- [ ] **Step 5: Add IsTeacher to permissions.py**

```python
# backend/hub/views/permissions.py
from rest_framework.permissions import BasePermission

from hub.models import UserProfile


class IsContentCreator(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.user_type == UserProfile.UserType.CONTENT_CREATOR
        )


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.user_type == UserProfile.UserType.TEACHER
        )
```

- [ ] **Step 6: Commit**

```bash
git add backend/hub/views/permissions.py backend/hub/serializers/auth.py backend/hub/tests/test_auth.py
git commit -m "feat: add IsTeacher permission, expose onboarding_completed in auth response"
```

---

### Task 12: Onboarding API (TDD)

**Files:**
- Create: `backend/hub/tests/test_competency_scoring.py`
- Create: `backend/hub/tests/test_onboarding.py`
- Create: `backend/hub/serializers/onboarding.py`
- Create: `backend/hub/views/onboarding.py`

- [ ] **Step 1: Write competency scoring unit tests**

Create `backend/hub/tests/test_competency_scoring.py`:

```python
from django.test import SimpleTestCase


class CompetencyScoringTestCase(SimpleTestCase):
    def _score(self, answers):
        from hub.views.onboarding import score_answers
        return score_answers(answers)

    def _level(self, score):
        from hub.views.onboarding import get_competency_level
        return get_competency_level(score)

    def test_all_correct_gives_6(self):
        self.assertEqual(self._score({'q3': 'b', 'q4': 'b', 'q5': 'b'}), 6)

    def test_all_wrong_gives_0(self):
        self.assertEqual(self._score({'q3': 'a', 'q4': 'a', 'q5': 'a'}), 0)

    def test_partial_correct_q3(self):
        self.assertEqual(self._score({'q3': 'c', 'q4': 'a', 'q5': 'a'}), 1)

    def test_partial_correct_q5(self):
        self.assertEqual(self._score({'q3': 'a', 'q4': 'a', 'q5': 'c'}), 1)

    def test_mixed_gives_correct_total(self):
        # q3=b(2) + q4=c(1) + q5=b(2) = 5
        self.assertEqual(self._score({'q3': 'b', 'q4': 'c', 'q5': 'b'}), 5)

    def test_missing_question_scores_zero(self):
        self.assertEqual(self._score({'q3': 'b'}), 2)

    def test_score_0_is_beginner(self):
        self.assertEqual(self._level(0), 'beginner')

    def test_score_2_is_beginner(self):
        self.assertEqual(self._level(2), 'beginner')

    def test_score_3_is_intermediate(self):
        self.assertEqual(self._level(3), 'intermediate')

    def test_score_4_is_intermediate(self):
        self.assertEqual(self._level(4), 'intermediate')

    def test_score_5_is_advanced(self):
        self.assertEqual(self._level(5), 'advanced')

    def test_score_6_is_advanced(self):
        self.assertEqual(self._level(6), 'advanced')
```

- [ ] **Step 2: Run to verify it fails (function not yet defined)**

```bash
cd backend
.venv/Scripts/uv.exe run python manage.py test hub.tests.test_competency_scoring --verbosity=2
```

Expected: FAIL with ImportError.

- [ ] **Step 3: Create onboarding serializer**

Create `backend/hub/serializers/onboarding.py`:

```python
from rest_framework import serializers

_SUBJECT_AREAS   = ['stem', 'humanities', 'languages', 'arts', 'general']
_TEACHING_LEVELS = ['primary', 'secondary', 'higher_ed', 'vocational', 'adult_ed']
_ANSWER_KEYS     = {'q3', 'q4', 'q5'}
_ANSWER_OPTIONS  = {'a', 'b', 'c', 'd'}
_GOALS           = ['save_time', 'teach_about_ai', 'prepare_students', 'stay_current', 'address_ethics']


class OnboardingSubmitSerializer(serializers.Serializer):
    subject_area   = serializers.ChoiceField(choices=_SUBJECT_AREAS)
    teaching_level = serializers.ChoiceField(choices=_TEACHING_LEVELS)
    answers        = serializers.DictField(child=serializers.ChoiceField(choices=_ANSWER_OPTIONS))
    goals          = serializers.ListField(
        child=serializers.ChoiceField(choices=_GOALS),
        allow_empty=True,
    )

    def validate_answers(self, value):
        for key in value:
            if key not in _ANSWER_KEYS:
                raise serializers.ValidationError(f"Unknown question key: {key}")
        return value
```

- [ ] **Step 4: Create onboarding view**

Create `backend/hub/views/onboarding.py`:

```python
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models.pathway import LearningPath, UserLearningPath
from hub.serializers.onboarding import OnboardingSubmitSerializer
from hub.views.permissions import IsTeacher

ANSWER_SCORES = {
    'q3': {'b': 2, 'c': 1},
    'q4': {'b': 2, 'c': 1},
    'q5': {'b': 2, 'c': 1, 'd': 1},
}


def score_answers(answers: dict) -> int:
    return sum(ANSWER_SCORES.get(q, {}).get(a, 0) for q, a in answers.items())


def get_competency_level(score: int) -> str:
    if score <= 2:
        return 'beginner'
    if score <= 4:
        return 'intermediate'
    return 'advanced'


def assign_path(score: int) -> LearningPath:
    path = LearningPath.objects.filter(
        competency_min__lte=score,
        competency_max__gte=score,
    ).first()
    if not path:
        path = LearningPath.objects.get(slug='beginner-foundations')
    return path


class OnboardingView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        profile = request.user.profile
        return Response({
            'completed': profile.onboarding_completed,
            'competency_level': (
                get_competency_level(profile.competency_score)
                if profile.onboarding_completed else None
            ),
        })

    def post(self, request):
        serializer = OnboardingSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        score = score_answers(data['answers'])
        level = get_competency_level(score)
        path  = assign_path(score)

        profile = request.user.profile
        profile.subject_area         = data['subject_area']
        profile.teaching_level       = data['teaching_level']
        profile.goals                = data['goals']
        profile.competency_score     = score
        profile.onboarding_completed = True
        profile.save()

        UserLearningPath.objects.update_or_create(
            user=request.user,
            defaults={'path': path},
        )

        from hub.tasks import compute_user_recommendations
        compute_user_recommendations.delay(request.user.id)

        return Response({
            'competency_score': score,
            'competency_level': level,
            'pathway_id':   path.id,
            'pathway_name': path.name,
        })
```

- [ ] **Step 5: Run scoring tests to verify they pass**

```bash
.venv/Scripts/uv.exe run python manage.py test hub.tests.test_competency_scoring --verbosity=2
```

Expected: 12 tests PASS.

- [ ] **Step 6: Write onboarding API integration tests**

Create `backend/hub/tests/test_onboarding.py`:

```python
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import UserProfile
from hub.models.pathway import LearningPath, UserLearningPath


def make_teacher(username='teacher1', onboarding=False):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(
        user=user,
        user_type=UserProfile.UserType.TEACHER,
        onboarding_completed=onboarding,
    )
    return user


def make_path(slug, competency_min, competency_max):
    return LearningPath.objects.create(
        name=slug.replace('-', ' ').title(),
        slug=slug,
        competency_min=competency_min,
        competency_max=competency_max,
    )


VALID_PAYLOAD = {
    'subject_area':   'stem',
    'teaching_level': 'secondary',
    'answers':        {'q3': 'b', 'q4': 'b', 'q5': 'b'},
    'goals':          ['save_time'],
}


class OnboardingGetTestCase(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_returns_not_completed_for_new_teacher(self):
        response = self.client.get(reverse('onboarding'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['completed'])
        self.assertIsNone(response.data['competency_level'])

    def test_content_creator_cannot_access(self):
        creator = User.objects.create_user(username='creator1', password='pass')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        login = self.client.post(reverse('auth-login'), {'username': 'creator1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.get(reverse('onboarding'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OnboardingPostTestCase(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        make_path('beginner-foundations', 0, 2)
        make_path('intermediate-growth', 3, 4)
        make_path('advanced-integration', 5, 6)
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_correct_answers_score_6_and_assign_advanced_path(self, mock_task):
        response = self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['competency_score'], 6)
        self.assertEqual(response.data['competency_level'], 'advanced')
        self.assertEqual(response.data['pathway_name'], 'Advanced Integration')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_profile_saved_correctly(self, mock_task):
        self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.onboarding_completed)
        self.assertEqual(self.user.profile.subject_area, 'stem')
        self.assertEqual(self.user.profile.competency_score, 6)

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_user_learning_path_created(self, mock_task):
        self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        self.assertTrue(UserLearningPath.objects.filter(user=self.user).exists())

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_celery_task_fired(self, mock_task):
        self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        mock_task.assert_called_once_with(self.user.id)

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_wrong_answers_score_0_and_assign_beginner_path(self, mock_task):
        payload = {**VALID_PAYLOAD, 'answers': {'q3': 'a', 'q4': 'a', 'q5': 'a'}}
        response = self.client.post(reverse('onboarding'), payload, format='json')
        self.assertEqual(response.data['competency_score'], 0)
        self.assertEqual(response.data['competency_level'], 'beginner')
        self.assertEqual(response.data['pathway_name'], 'Beginner Foundations')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_fallback_path_assigned_when_no_match(self, mock_task):
        LearningPath.objects.all().delete()
        LearningPath.objects.create(name='Beginner Foundations', slug='beginner-foundations', competency_min=0, competency_max=2)
        payload = {**VALID_PAYLOAD, 'answers': {'q3': 'b', 'q4': 'b', 'q5': 'b'}}
        response = self.client.post(reverse('onboarding'), payload, format='json')
        self.assertEqual(response.data['pathway_name'], 'Beginner Foundations')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_submit_twice_is_idempotent(self, mock_task):
        self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        response = self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserLearningPath.objects.filter(user=self.user).count(), 1)

    def test_invalid_subject_area_rejected(self):
        payload = {**VALID_PAYLOAD, 'subject_area': 'invalid'}
        response = self.client.post(reverse('onboarding'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
```

- [ ] **Step 7: Run onboarding tests — they should fail (URL not wired yet)**

```bash
.venv/Scripts/uv.exe run python manage.py test hub.tests.test_onboarding --verbosity=2
```

Expected: FAIL with NoReverseMatch or 404 (URL `onboarding` not yet defined).

This is expected — we'll wire URLs in Task 15.

- [ ] **Step 8: Commit**

```bash
git add backend/hub/serializers/onboarding.py backend/hub/views/onboarding.py backend/hub/tests/test_competency_scoring.py backend/hub/tests/test_onboarding.py
git commit -m "feat: onboarding scoring logic, serializer, view, and tests"
```

---

### Task 13: Pathway and Recommendations APIs (TDD)

**Files:**
- Create: `backend/hub/serializers/pathway.py`
- Create: `backend/hub/views/pathway.py`
- Create: `backend/hub/views/recommendations.py`
- Create: `backend/hub/tests/test_pathway.py`
- Create: `backend/hub/tests/test_recommendations.py`

- [ ] **Step 1: Create pathway serializer**

Create `backend/hub/serializers/pathway.py`:

```python
from rest_framework import serializers

from hub.models.content import Course
from hub.models.enrollment import Enrollment
from hub.models.pathway import LearningPath, LearningPathCourse, UserLearningPath
from hub.models.recommendations import CourseRecommendation


class PathwayCourseSerializer(serializers.ModelSerializer):
    pillar_name = serializers.CharField(source='pillar.name', read_only=True)
    status      = serializers.SerializerMethodField()
    order       = serializers.SerializerMethodField()

    class Meta:
        model  = Course
        fields = ['id', 'title', 'pillar_name', 'duration_hours', 'level', 'status', 'order']

    def get_status(self, obj):
        user = self.context.get('user')
        if not user:
            return 'not_started'
        enrollment = Enrollment.objects.filter(user=user, course=obj).first()
        if not enrollment:
            return 'not_started'
        return 'completed' if enrollment.progress_pct == 100 else 'in_progress'

    def get_order(self, obj):
        path = self.context.get('path')
        if not path:
            return 0
        lpc = LearningPathCourse.objects.filter(path=path, course=obj).first()
        return lpc.order if lpc else 0


class UserLearningPathSerializer(serializers.ModelSerializer):
    path_name        = serializers.CharField(source='path.name', read_only=True)
    path_description = serializers.CharField(source='path.description', read_only=True)
    competency_level = serializers.SerializerMethodField()
    courses          = serializers.SerializerMethodField()
    progress         = serializers.SerializerMethodField()

    class Meta:
        model  = UserLearningPath
        fields = ['path_name', 'path_description', 'competency_level', 'courses', 'progress']

    def get_competency_level(self, obj):
        score = obj.user.profile.competency_score
        if score <= 2:
            return 'beginner'
        if score <= 4:
            return 'intermediate'
        return 'advanced'

    def get_courses(self, obj):
        courses = obj.path.courses.order_by('path_courses__order')
        return PathwayCourseSerializer(
            courses, many=True, context={**self.context, 'path': obj.path},
        ).data

    def get_progress(self, obj):
        user       = obj.user
        course_ids = list(obj.path.courses.values_list('id', flat=True))
        total      = len(course_ids)
        completed  = Enrollment.objects.filter(
            user=user, course_id__in=course_ids, progress_pct=100,
        ).count()
        return {'completed': completed, 'total': total}


class RecommendationSerializer(serializers.ModelSerializer):
    course_id      = serializers.IntegerField(source='course.id')
    title          = serializers.CharField(source='course.title')
    pillar_name    = serializers.CharField(source='course.pillar.name')
    level          = serializers.CharField(source='course.level')
    duration_hours = serializers.IntegerField(source='course.duration_hours')

    class Meta:
        model  = CourseRecommendation
        fields = ['course_id', 'title', 'pillar_name', 'level', 'duration_hours', 'score', 'reason']
```

- [ ] **Step 2: Create pathway view**

Create `backend/hub/views/pathway.py`:

```python
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models.pathway import UserLearningPath
from hub.serializers.pathway import UserLearningPathSerializer
from hub.views.permissions import IsTeacher


class PathwayView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            user_path = (
                UserLearningPath.objects
                .select_related('path', 'user__profile')
                .get(user=request.user)
            )
        except UserLearningPath.DoesNotExist:
            return Response(
                {'detail': 'No pathway assigned. Complete onboarding first.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UserLearningPathSerializer(
            user_path, context={'user': request.user, 'request': request},
        )
        return Response(serializer.data)
```

- [ ] **Step 3: Create recommendations view**

Create `backend/hub/views/recommendations.py`:

```python
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models.recommendations import CourseRecommendation
from hub.serializers.pathway import RecommendationSerializer
from hub.views.permissions import IsTeacher


class RecommendationsView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        recs = (
            CourseRecommendation.objects
            .filter(user=request.user)
            .select_related('course__pillar')
            .order_by('-score')[:5]
        )
        return Response(RecommendationSerializer(recs, many=True).data)
```

- [ ] **Step 4: Write pathway tests**

Create `backend/hub/tests/test_pathway.py`:

```python
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, Enrollment, LearningPillar, UserProfile
from hub.models.pathway import LearningPath, LearningPathCourse, UserLearningPath


def make_teacher(username='teacher1'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER, competency_score=6)
    return user


def make_pillar():
    return LearningPillar.objects.create(name='Pillar', slug='pillar', description='')


def make_course(pillar, title='Course A'):
    return Course.objects.create(
        title=title, pillar=pillar, level='beginner', is_published=True,
    )


def make_path_with_courses(courses):
    path = LearningPath.objects.create(
        name='Test Path', slug='test-path', competency_min=5, competency_max=6,
    )
    for i, course in enumerate(courses):
        LearningPathCourse.objects.create(path=path, course=course, order=i + 1)
    return path


class PathwayGetTestCase(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_404_before_onboarding(self):
        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_path_with_courses(self):
        pillar  = make_pillar()
        course1 = make_course(pillar, 'Course A')
        course2 = make_course(pillar, 'Course B')
        path    = make_path_with_courses([course1, course2])
        UserLearningPath.objects.create(user=self.user, path=path)

        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['path_name'], 'Test Path')
        self.assertEqual(len(response.data['courses']), 2)
        self.assertEqual(response.data['progress']['total'], 2)
        self.assertEqual(response.data['progress']['completed'], 0)

    def test_course_status_is_completed_when_enrolled_at_100(self):
        pillar  = make_pillar()
        course  = make_course(pillar)
        path    = make_path_with_courses([course])
        UserLearningPath.objects.create(user=self.user, path=path)
        Enrollment.objects.create(user=self.user, course=course, progress_pct=100)

        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.data['courses'][0]['status'], 'completed')

    def test_competency_level_advanced_for_score_6(self):
        path = make_path_with_courses([])
        UserLearningPath.objects.create(user=self.user, path=path)
        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.data['competency_level'], 'advanced')

    def test_content_creator_gets_403(self):
        creator = User.objects.create_user(username='creator1', password='pass')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        login = self.client.post(reverse('auth-login'), {'username': 'creator1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.get(reverse('pathway'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
```

- [ ] **Step 5: Write recommendations tests**

Create `backend/hub/tests/test_recommendations.py`:

```python
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, UserProfile
from hub.models.recommendations import CourseRecommendation


def make_teacher(username='teacher1'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
    return user


class RecommendationsGetTestCase(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_empty_list_when_no_recommendations(self):
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_returns_precomputed_recommendations(self):
        pillar = LearningPillar.objects.create(name='P', slug='p', description='')
        course = Course.objects.create(title='AI Basics', pillar=pillar, level='beginner', is_published=True)
        CourseRecommendation.objects.create(
            user=self.user, course=course, score=0.95,
            reason='Matches your beginner level and stem focus',
        )
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'AI Basics')
        self.assertEqual(response.data[0]['score'], 0.95)

    def test_content_creator_gets_403(self):
        creator = User.objects.create_user(username='creator1', password='pass')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        login = self.client.post(reverse('auth-login'), {'username': 'creator1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
```

- [ ] **Step 6: Commit**

```bash
git add backend/hub/serializers/pathway.py backend/hub/views/pathway.py backend/hub/views/recommendations.py backend/hub/tests/test_pathway.py backend/hub/tests/test_recommendations.py
git commit -m "feat: pathway and recommendations serializers, views, and tests"
```

---

### Task 14: Wire up URLs + update exports

**Files:**
- Modify: `backend/hub/urls.py`
- Modify: `backend/hub/views/__init__.py`
- Modify: `backend/hub/serializers/__init__.py`

- [ ] **Step 1: Add new URL patterns to hub/urls.py**

Add these imports at the top of the existing import block:

```python
from .views import (
    ...existing imports...,
    OnboardingView,
    PathwayView,
    RecommendationsView,
)
```

Add these URL patterns to `urlpatterns`:

```python
    path('onboarding/',       OnboardingView.as_view(),       name='onboarding'),
    path('pathway/',          PathwayView.as_view(),          name='pathway'),
    path('recommendations/',  RecommendationsView.as_view(),  name='recommendations'),
```

- [ ] **Step 2: Update views/__init__.py**

Add to the imports and `__all__`:

```python
from .onboarding import OnboardingView
from .pathway import PathwayView
from .recommendations import RecommendationsView
```

And add to `__all__`:
```python
    'IsTeacher',
    'OnboardingView',
    'PathwayView',
    'RecommendationsView',
```

- [ ] **Step 3: Update serializers/__init__.py**

Add to the imports:

```python
from .onboarding import OnboardingSubmitSerializer
from .pathway import RecommendationSerializer, UserLearningPathSerializer
```

And add to `__all__`:
```python
    'OnboardingSubmitSerializer',
    'RecommendationSerializer',
    'UserLearningPathSerializer',
```

- [ ] **Step 4: Run all backend tests**

```bash
cd backend
.venv/Scripts/uv.exe run python manage.py test hub analytics --verbosity=2
```

Expected: all tests pass, including the previously written onboarding, pathway, and recommendation tests.

- [ ] **Step 5: Commit**

```bash
git add backend/hub/urls.py backend/hub/views/__init__.py backend/hub/serializers/__init__.py
git commit -m "feat: wire up onboarding, pathway, and recommendations URLs"
```

---

## Phase 4 — Seed Data

### Task 15: Pathway seed data

**Files:**
- Create: `backend/hub/management/commands/seed_data/pathways.py`
- Modify: `backend/hub/management/commands/seed.py`

- [ ] **Step 1: Create pathways.py seed module**

Create `backend/hub/management/commands/seed_data/pathways.py`:

```python
from hub.models.content import Course, LearningPillar
from hub.models.pathway import LearningPath, LearningPathCourse

_PATH_CONFIGS = [
    {
        'slug':            'beginner-foundations',
        'name':            'Beginner Foundations',
        'description':     'Start your AI journey with practical tools for the classroom.',
        'competency_min':  0,
        'competency_max':  2,
        'pillar_slug':     'teach-with-ai',
    },
    {
        'slug':            'intermediate-growth',
        'name':            'Intermediate Growth',
        'description':     'Deepen your understanding of AI and expand your teaching toolkit.',
        'competency_min':  3,
        'competency_max':  4,
        'pillar_slug':     'teach-about-ai',
    },
    {
        'slug':            'advanced-integration',
        'name':            'Advanced Integration',
        'description':     'Master AI integration and prepare your students for an AI-driven future.',
        'competency_min':  5,
        'competency_max':  6,
        'pillar_slug':     'teach-for-ai',
    },
]


def seed_pathways():
    for config in _PATH_CONFIGS:
        pillar_slug = config.pop('pillar_slug')
        path, _ = LearningPath.objects.update_or_create(
            slug=config['slug'],
            defaults={k: v for k, v in config.items() if k != 'slug'},
        )
        config['pillar_slug'] = pillar_slug  # restore for idempotency

        try:
            pillar = LearningPillar.objects.get(slug=pillar_slug)
        except LearningPillar.DoesNotExist:
            continue

        courses = list(
            Course.objects.filter(pillar=pillar, is_published=True).order_by('title')[:5]
        )
        LearningPathCourse.objects.filter(path=path).delete()
        for i, course in enumerate(courses):
            LearningPathCourse.objects.create(path=path, course=course, order=i + 1)
```

- [ ] **Step 2: Update seed command to call seed_pathways**

In `backend/hub/management/commands/seed.py`, add the import:

```python
from .seed_data.pathways import seed_pathways
```

And in the `handle` method, call it after `_seed_pillars()`:

```python
    def handle(self, *args, **options):
        self._seed_pillars()
        seed_pathways()
        self._seed_demo_user()
        creator = self._seed_demo_content_creator()
        self._assign_creator_courses(creator)
        self._seed_teacher_cohort(creator)
        self.stdout.write(self.style.SUCCESS('Seed data created successfully.'))
```

- [ ] **Step 3: Run the seed command via Docker and verify**

```bash
docker compose exec backend uv run python manage.py seed
```

Expected output ends with: `Seed data created successfully.`

Check in Django admin (`http://localhost:8000/admin/`) that 3 LearningPath objects exist under hub > Learning paths.

- [ ] **Step 4: Commit**

```bash
git add backend/hub/management/commands/seed_data/pathways.py backend/hub/management/commands/seed.py
git commit -m "feat: seed learning pathways (beginner, intermediate, advanced)"
```

---

## Phase 5 — Frontend

### Task 16: Install shadcn/ui

**Files:**
- Modify: `frontend/vite.config.js`
- Modify: `frontend/package.json` (via npm)
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Install Tailwind CSS v4 and shadcn**

```bash
cd frontend
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: Update vite.config.js to add Tailwind plugin and @ alias**

```js
import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

- [ ] **Step 3: Add Tailwind import at the top of src/index.css**

Open `frontend/src/index.css` and add as the very first line:

```css
@import "tailwindcss";
```

- [ ] **Step 4: Install shadcn and initialise**

```bash
cd frontend
npx shadcn@latest init -d
```

When prompted, accept defaults. This creates `src/components/ui/` and `components.json`.

- [ ] **Step 5: Add required components**

```bash
cd frontend
npx shadcn@latest add button card progress radio-group checkbox badge label skeleton
```

- [ ] **Step 6: Verify app still works**

```bash
npm run dev
```

Open `http://localhost:5173` and log in. Verify existing pages still look correct (no CSS breakage).

- [ ] **Step 7: Commit**

```bash
git add frontend/vite.config.js frontend/src/index.css frontend/package.json frontend/package-lock.json frontend/components.json frontend/src/components/ui/
git commit -m "chore: install Tailwind v4 and shadcn/ui components"
```

---

### Task 17: Update AuthContext + create RequireOnboarding

**Files:**
- Modify: `frontend/src/context/AuthContext.jsx`
- Create: `frontend/src/components/RequireOnboarding.jsx`

- [ ] **Step 1: Add updateUser to AuthContext**

Replace `frontend/src/context/AuthContext.jsx`:

```jsx
import { createContext, useContext, useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import client from '../api/client'

const AuthContext = createContext(null)

AuthProvider.propTypes = { children: PropTypes.node }

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('user')
    return stored ? JSON.parse(stored) : null
  })

  const login = useCallback(async (username, password) => {
    const { data } = await client.post('/auth/login/', { username, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    localStorage.setItem('user', JSON.stringify(data.user))
    setUser(data.user)
  }, [])

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('refresh_token')
    try {
      await client.post('/auth/logout/', { refresh })
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      setUser(null)
    }
  }, [])

  const updateUser = useCallback((updates) => {
    setUser(prev => {
      const updated = { ...prev, ...updates }
      localStorage.setItem('user', JSON.stringify(updated))
      return updated
    })
  }, [])

  return (
    <AuthContext.Provider value={{ user, login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
```

- [ ] **Step 2: Create RequireOnboarding component**

Create `frontend/src/components/RequireOnboarding.jsx`:

```jsx
import PropTypes from 'prop-types'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

RequireOnboarding.propTypes = { children: PropTypes.node.isRequired }

export default function RequireOnboarding({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (
    user.profile?.user_type === 'teacher' &&
    !user.profile?.onboarding_completed
  ) {
    return <Navigate to="/onboarding" replace />
  }
  return children
}
```

- [ ] **Step 3: Update App.jsx to add new routes and RequireOnboarding**

Add these imports at the top of `frontend/src/App.jsx`:

```jsx
import RequireOnboarding from './components/RequireOnboarding'
import OnboardingPage from './pages/OnboardingPage'
import PathwayPage from './pages/PathwayPage'
```

Replace the routing structure inside `<Routes>`:

```jsx
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route element={<RequireOnboarding><Layout /></RequireOnboarding>}>
            <Route index element={<HomePage />} />
            <Route path="/courses"              element={<CoursesPage />} />
            <Route path="/courses/:id"          element={<CourseDetailPage />} />
            <Route path="/learning"             element={<MyLearningPage />} />
            <Route path="/pathway"              element={<PathwayPage />} />
            <Route path="/analytics"            element={<AnalyticsPage />} />
            <Route path="/profile"              element={<PlaceholderPage title="Profile" />} />
            <Route path="/authoring"                  element={<ContentCreatorRoute element={<AuthoringPage />} />} />
            <Route path="/authoring/courses/new"      element={<ContentCreatorRoute element={<CourseCreatePage />} />} />
            <Route path="/authoring/courses/:id"      element={<ContentCreatorRoute element={<CourseEditorPage />} />} />
            <Route path="/authoring/courses/:id/modules/:moduleId" element={<ContentCreatorRoute element={<ModuleEditorPage />} />} />
          </Route>
          <Route path="/courses/:id/learn"                element={<LearnRedirect />} />
          <Route path="/courses/:courseId/learn/:lessonId" element={<LessonPage />} />
        </Routes>
```

Note: `RequireOnboarding` wraps `Layout` so it acts as a layout wrapper. `Layout` uses `<Outlet />` internally so this works.

- [ ] **Step 4: Update Sidebar to add My Pathway nav item**

In `frontend/src/components/layout/Sidebar.jsx`, add `Map` to the lucide import:

```jsx
import { House, BookOpen, GraduationCap, BarChart2, User, PenLine, Map } from 'lucide-react'
```

Add a new item to `BASE_NAV`:

```jsx
const BASE_NAV = [
  { to: '/',          label: 'Home',              Icon: House },
  { to: '/courses',   label: 'Courses',           Icon: BookOpen },
  { to: '/learning',  label: 'My Learning',       Icon: GraduationCap },
  { to: '/pathway',   label: 'My Pathway',        Icon: Map },
  { to: '/analytics', label: 'Content Analytics', Icon: BarChart2 },
  { to: '/profile',   label: 'Profile',           Icon: User },
]
```

And filter it so teachers see "My Pathway" but content creators don't:

```jsx
export default function Sidebar() {
  const { user } = useAuth()
  const isContentCreator = user?.profile?.user_type === 'content_creator'
  const navItems = isContentCreator
    ? [...BASE_NAV.filter(item => item.to !== '/pathway'), AUTHORING_ITEM]
    : BASE_NAV
  // rest of component unchanged
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/context/AuthContext.jsx frontend/src/components/RequireOnboarding.jsx frontend/src/App.jsx frontend/src/components/layout/Sidebar.jsx
git commit -m "feat: add RequireOnboarding guard, My Pathway nav item, updateUser in AuthContext"
```

---

### Task 18: OnboardingPage

**Files:**
- Create: `frontend/src/pages/OnboardingPage.jsx`
- Create: `frontend/src/pages/OnboardingPage.css`

- [ ] **Step 1: Create OnboardingPage.jsx**

Create `frontend/src/pages/OnboardingPage.jsx`:

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'
import { Label } from '@/components/ui/label'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './OnboardingPage.css'

const STEPS = [
  {
    key: 'subject_area',
    question: 'Which subject area do you primarily teach?',
    type: 'radio',
    options: [
      { value: 'stem',       label: 'STEM (Science, Technology, Engineering, Math)' },
      { value: 'humanities', label: 'Humanities & Social Sciences' },
      { value: 'languages',  label: 'Languages' },
      { value: 'arts',       label: 'Arts' },
      { value: 'general',    label: 'General / Multiple subjects' },
    ],
  },
  {
    key: 'teaching_level',
    question: 'What level do you teach?',
    type: 'radio',
    options: [
      { value: 'primary',    label: 'Primary (K–6)' },
      { value: 'secondary',  label: 'Secondary (7–12)' },
      { value: 'higher_ed',  label: 'Higher Education' },
      { value: 'vocational', label: 'Vocational' },
      { value: 'adult_ed',   label: 'Adult Education' },
    ],
  },
  {
    key: 'q3',
    question: "You ask an AI to summarise a student's essay. It gives a confident but factually wrong summary. What do you do?",
    type: 'radio',
    options: [
      { value: 'a', label: "Trust the AI — it's usually accurate" },
      { value: 'b', label: 'Check it yourself and correct it' },
      { value: 'c', label: 'Use a different AI tool instead' },
      { value: 'd', label: "I wouldn't use AI for this task" },
    ],
  },
  {
    key: 'q4',
    question: 'What does it mean when an AI model "hallucinates"?',
    type: 'radio',
    options: [
      { value: 'a', label: 'The AI crashes or freezes' },
      { value: 'b', label: 'The AI generates false information that sounds plausible' },
      { value: 'c', label: 'The AI gives creative or unexpected responses' },
      { value: 'd', label: "I'm not sure" },
    ],
  },
  {
    key: 'q5',
    question: 'Which of these is the best AI prompt for generating a lesson plan?',
    type: 'radio',
    options: [
      { value: 'a', label: '"Write a lesson plan"' },
      { value: 'b', label: '"Write a 45-minute lesson plan for 14-year-olds about fractions, include 3 activities"' },
      { value: 'c', label: '"Help me teach math"' },
      { value: 'd', label: '"I need a lesson plan about math, make it good"' },
    ],
  },
  {
    key: 'goals',
    question: 'What are your main learning goals? (Select all that apply)',
    type: 'multiselect',
    options: [
      { value: 'save_time',        label: 'Save time on lesson planning' },
      { value: 'teach_about_ai',   label: 'Learn to teach students about AI' },
      { value: 'prepare_students', label: 'Prepare students for an AI-driven world' },
      { value: 'stay_current',     label: 'Stay current with technology trends' },
      { value: 'address_ethics',   label: 'Address ethical concerns about AI' },
    ],
  },
]

export default function OnboardingPage() {
  const navigate = useNavigate()
  const { user, updateUser } = useAuth()
  const [step, setStep]       = useState(0)
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  const current = STEPS[step]
  const isLast  = step === STEPS.length - 1
  const hasAnswer = current.type === 'multiselect'
    ? true  // goals are optional — allow empty
    : !!answers[current.key]

  function handleRadio(value) {
    setAnswers(prev => ({ ...prev, [current.key]: value }))
  }

  function handleCheckbox(value, checked) {
    setAnswers(prev => {
      const vals = prev[current.key] || []
      return {
        ...prev,
        [current.key]: checked ? [...vals, value] : vals.filter(v => v !== value),
      }
    })
  }

  async function handleSubmit() {
    setLoading(true)
    setError('')
    try {
      await client.post('/onboarding/', {
        subject_area:   answers.subject_area,
        teaching_level: answers.teaching_level,
        answers:        { q3: answers.q3, q4: answers.q4, q5: answers.q5 },
        goals:          answers.goals || [],
      })
      updateUser({
        profile: { ...user.profile, onboarding_completed: true },
      })
      navigate('/pathway')
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="onboarding-container">
      <div className="onboarding-card">
        <div className="onboarding-header">
          <h1 className="onboarding-title">Welcome to AIDEA</h1>
          <p className="onboarding-subtitle">
            Let&apos;s personalise your learning path. This takes about 2 minutes.
          </p>
          <Progress value={((step + 1) / STEPS.length) * 100} className="onboarding-progress" />
          <span className="onboarding-step-label">Step {step + 1} of {STEPS.length}</span>
        </div>

        <div className="onboarding-question">
          <h2 className="onboarding-question-text">{current.question}</h2>

          {current.type === 'radio' && (
            <RadioGroup
              value={answers[current.key] || ''}
              onValueChange={handleRadio}
              className="onboarding-options"
            >
              {current.options.map(opt => (
                <div key={opt.value} className="onboarding-option">
                  <RadioGroupItem value={opt.value} id={`opt-${opt.value}`} />
                  <Label htmlFor={`opt-${opt.value}`} className="onboarding-option-label">
                    {opt.label}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          )}

          {current.type === 'multiselect' && (
            <div className="onboarding-options">
              {current.options.map(opt => (
                <div key={opt.value} className="onboarding-option">
                  <Checkbox
                    id={`goal-${opt.value}`}
                    checked={(answers[current.key] || []).includes(opt.value)}
                    onCheckedChange={checked => handleCheckbox(opt.value, checked)}
                  />
                  <Label htmlFor={`goal-${opt.value}`} className="onboarding-option-label">
                    {opt.label}
                  </Label>
                </div>
              ))}
            </div>
          )}
        </div>

        {error && <p className="onboarding-error">{error}</p>}

        <div className="onboarding-nav">
          {step > 0 && (
            <Button variant="outline" onClick={() => setStep(s => s - 1)} disabled={loading}>
              Back
            </Button>
          )}
          {!isLast && (
            <Button onClick={() => setStep(s => s + 1)} disabled={!hasAnswer}>
              Next
            </Button>
          )}
          {isLast && (
            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? 'Building your learning path…' : 'Complete Setup'}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create OnboardingPage.css**

Create `frontend/src/pages/OnboardingPage.css`:

```css
.onboarding-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-background, #f8fafc);
  padding: 2rem;
}

.onboarding-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 2.5rem;
  width: 100%;
  max-width: 640px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.onboarding-header {
  margin-bottom: 2rem;
}

.onboarding-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
}

.onboarding-subtitle {
  color: #64748b;
  margin: 0 0 1.25rem;
}

.onboarding-progress {
  height: 6px;
  margin-bottom: 0.5rem;
}

.onboarding-step-label {
  font-size: 0.75rem;
  color: #94a3b8;
}

.onboarding-question {
  margin-bottom: 2rem;
}

.onboarding-question-text {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0 0 1.25rem;
  line-height: 1.5;
}

.onboarding-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.onboarding-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.onboarding-option:hover {
  border-color: #94a3b8;
}

.onboarding-option-label {
  cursor: pointer;
  font-size: 0.9375rem;
}

.onboarding-error {
  color: #dc2626;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.onboarding-nav {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}
```

- [ ] **Step 3: Test the onboarding flow manually**

1. Start the Docker dev stack (`docker compose up`)
2. Run seed: `docker compose exec backend uv run python manage.py seed`
3. Open `http://localhost:5173`, log in as `demo_teacher / demo1234`
4. Verify redirect to `/onboarding`
5. Complete all 6 steps
6. Verify redirect to `/pathway` after completion
7. Log in again — verify no redirect to `/onboarding` (already completed)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/OnboardingPage.jsx frontend/src/pages/OnboardingPage.css
git commit -m "feat: OnboardingPage — 6-step AI competency assessment wizard"
```

---

### Task 19: PathwayPage

**Files:**
- Create: `frontend/src/pages/PathwayPage.jsx`
- Create: `frontend/src/pages/PathwayPage.css`

- [ ] **Step 1: Create PathwayPage.jsx**

Create `frontend/src/pages/PathwayPage.jsx`:

```jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CheckCircle, PlayCircle, Circle } from 'lucide-react'
import client from '../api/client'
import './PathwayPage.css'

const LEVEL_VARIANT = { beginner: 'secondary', intermediate: 'outline', advanced: 'default' }

const STATUS_ICON = {
  completed:   CheckCircle,
  in_progress: PlayCircle,
  not_started: Circle,
}

export default function PathwayPage() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  useEffect(() => {
    client.get('/pathway/')
      .then(res => setData(res.data))
      .catch(() => setError('Could not load your pathway.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="pathway-loading">Loading your pathway…</div>
  if (error)   return <div className="pathway-error">{error}</div>

  const nextCourse  = data.courses.find(c => c.status !== 'completed')
  const progressPct = data.progress.total > 0
    ? Math.round((data.progress.completed / data.progress.total) * 100)
    : 0

  return (
    <div className="pathway-page">
      <div className="pathway-header">
        <div className="pathway-title-row">
          <h1 className="pathway-title">{data.path_name}</h1>
          <Badge variant={LEVEL_VARIANT[data.competency_level]}>
            {data.competency_level.charAt(0).toUpperCase() + data.competency_level.slice(1)}
          </Badge>
        </div>
        <p className="pathway-description">{data.path_description}</p>
        <div className="pathway-progress-row">
          <Progress value={progressPct} className="pathway-progress-bar" />
          <span className="pathway-progress-label">
            {data.progress.completed} of {data.progress.total} courses completed
          </span>
        </div>
      </div>

      <div className="pathway-courses">
        {data.courses.map((course, idx) => {
          const StatusIcon = STATUS_ICON[course.status] || Circle
          const isNext     = nextCourse?.id === course.id
          return (
            <Card key={course.id} className={`pathway-course-card pathway-course-${course.status}`}>
              <CardContent className="pathway-course-content">
                <div className="pathway-course-left">
                  <span className="pathway-course-number">{idx + 1}</span>
                  <StatusIcon size={20} className={`pathway-status-icon pathway-status-${course.status}`} />
                </div>
                <div className="pathway-course-info">
                  <h3 className="pathway-course-title">{course.title}</h3>
                  <div className="pathway-course-meta">
                    <span>{course.pillar_name}</span>
                    <span className="pathway-meta-dot">·</span>
                    <span>{course.duration_hours}h</span>
                    <span className="pathway-meta-dot">·</span>
                    <Badge variant="outline" className="pathway-level-badge">{course.level}</Badge>
                  </div>
                </div>
                {isNext && (
                  <Button asChild size="sm" className="pathway-cta">
                    <Link to={`/courses/${course.id}`}>
                      {course.status === 'in_progress' ? 'Continue' : 'Start'}
                    </Link>
                  </Button>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create PathwayPage.css**

Create `frontend/src/pages/PathwayPage.css`:

```css
.pathway-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

.pathway-header {
  margin-bottom: 2rem;
}

.pathway-title-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.pathway-title {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0;
}

.pathway-description {
  color: #64748b;
  margin: 0 0 1.25rem;
}

.pathway-progress-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.pathway-progress-bar {
  flex: 1;
  height: 8px;
}

.pathway-progress-label {
  font-size: 0.875rem;
  color: #64748b;
  white-space: nowrap;
}

.pathway-courses {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.pathway-course-card {
  border-radius: 10px;
  transition: box-shadow 0.15s;
}

.pathway-course-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.pathway-course-completed {
  opacity: 0.65;
}

.pathway-course-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem !important;
}

.pathway-course-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 52px;
}

.pathway-course-number {
  font-size: 0.8125rem;
  color: #94a3b8;
  font-weight: 600;
  width: 20px;
  text-align: right;
}

.pathway-status-icon.pathway-status-completed   { color: #16a34a; }
.pathway-status-icon.pathway-status-in_progress { color: #2563eb; }
.pathway-status-icon.pathway-status-not_started { color: #cbd5e1; }

.pathway-course-info {
  flex: 1;
}

.pathway-course-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 0.25rem;
}

.pathway-course-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: #64748b;
}

.pathway-meta-dot {
  color: #cbd5e1;
}

.pathway-level-badge {
  font-size: 0.75rem;
}

.pathway-cta {
  flex-shrink: 0;
}

.pathway-loading,
.pathway-error {
  padding: 3rem;
  text-align: center;
  color: #64748b;
}
```

- [ ] **Step 3: Verify Pathway page manually**

After completing onboarding, navigate to `/pathway`. Verify:
- Path name and level badge appear
- Progress bar shows 0 / N courses
- Courses are listed with "Start" button on the first one

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/PathwayPage.jsx frontend/src/pages/PathwayPage.css
git commit -m "feat: PathwayPage — learning path with course list and progress"
```

---

### Task 20: Recommendations on HomePage

**Files:**
- Modify: `frontend/src/pages/HomePage.jsx`

- [ ] **Step 1: Read the current HomePage.jsx**

Read `frontend/src/pages/HomePage.jsx` to understand its current structure before modifying.

- [ ] **Step 2: Add recommendations state and fetch**

Near the top of the `HomePage` component, add:

```jsx
import { useAuth } from '../context/AuthContext'
```

Add inside the component, after existing state declarations:

```jsx
  const { user } = useAuth()
  const [recommendations, setRecommendations] = useState([])
  const [recsLoading, setRecsLoading] = useState(false)

  useEffect(() => {
    if (user?.profile?.onboarding_completed) {
      setRecsLoading(true)
      client.get('/recommendations/')
        .then(res => setRecommendations(res.data))
        .catch(() => {})
        .finally(() => setRecsLoading(false))
    }
  }, [user])
```

- [ ] **Step 3: Add the recommendations section to the JSX**

At the bottom of the returned JSX, just before the closing tag of the page container, add:

```jsx
      {user?.profile?.onboarding_completed && (
        <section className="recommendations-section">
          <h2 className="recommendations-title">Recommended for you</h2>
          {recsLoading ? (
            <div className="recommendations-grid">
              {[1, 2, 3].map(i => (
                <div key={i} className="rec-card rec-card-skeleton" />
              ))}
            </div>
          ) : recommendations.length > 0 ? (
            <div className="recommendations-grid">
              {recommendations.map(rec => (
                <div key={rec.course_id} className="rec-card">
                  <span className="rec-pillar">{rec.pillar_name}</span>
                  <h3 className="rec-title">{rec.title}</h3>
                  <p className="rec-reason">{rec.reason}</p>
                  <a href={`/courses/${rec.course_id}`} className="rec-link">
                    Start course →
                  </a>
                </div>
              ))}
            </div>
          ) : null}
        </section>
      )}
```

- [ ] **Step 4: Add CSS for recommendations to HomePage.css**

Open `frontend/src/pages/HomePage.css` and add at the bottom:

```css
.recommendations-section {
  margin-top: 2.5rem;
}

.recommendations-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 1.25rem;
}

.recommendations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem;
}

.rec-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  transition: box-shadow 0.15s;
}

.rec-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.rec-card-skeleton {
  height: 160px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.rec-pillar {
  font-size: 0.75rem;
  font-weight: 600;
  color: #6366f1;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.rec-title {
  font-size: 0.9375rem;
  font-weight: 600;
  margin: 0;
  line-height: 1.4;
}

.rec-reason {
  font-size: 0.8125rem;
  color: #64748b;
  margin: 0;
  flex: 1;
}

.rec-link {
  font-size: 0.875rem;
  font-weight: 600;
  color: #2563eb;
  text-decoration: none;
  margin-top: 0.25rem;
}

.rec-link:hover {
  text-decoration: underline;
}
```

- [ ] **Step 5: Run linter**

```bash
cd frontend
npm run lint
```

Fix any ESLint errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/HomePage.jsx frontend/src/pages/HomePage.css
git commit -m "feat: add recommendations section to HomePage"
```

---

## Final verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend
.venv/Scripts/uv.exe run python manage.py test hub analytics --verbosity=2
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend linter and build**

```bash
cd frontend
npm run lint
VITE_API_URL=http://localhost:8000/api npm run build
```

Expected: no lint errors, build succeeds.

- [ ] **Step 3: Full end-to-end smoke test via Docker**

```bash
docker compose down -v   # fresh start
docker compose up --build
docker compose exec backend uv run python manage.py seed
```

1. Open `http://localhost:5173`
2. Log in as `demo_teacher / demo1234` → lands on `/onboarding`
3. Complete the 6-step wizard → lands on `/pathway`
4. Verify pathway shows 3 path courses
5. Navigate to Home → recommendations skeleton appears (Celery processing)
6. Wait ~10s, refresh Home → recommendations cards appear
7. Log in as `demo_creator / demo1234` → lands on Home directly (no onboarding redirect)
8. Verify "My Pathway" is not in sidebar for content creator

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: phase 1 complete — docker, onboarding, pathways, recommendations"
```
