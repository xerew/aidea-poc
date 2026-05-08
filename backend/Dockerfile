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
