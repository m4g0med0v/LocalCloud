FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ── Dependencies ──────────────────────────────────────────────────────────────
FROM base AS deps

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[prod]"

# ── Development image ─────────────────────────────────────────────────────────
FROM deps AS dev

RUN pip install --no-cache-dir watchfiles
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production image ──────────────────────────────────────────────────────────
FROM deps AS prod

COPY . .
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
