# backend/Dockerfile
FROM python:3.14-slim AS base

WORKDIR /app

# Install uv from PyPI (avoids depending on ghcr.io being reachable at build time)
RUN pip install --no-cache-dir uv

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
