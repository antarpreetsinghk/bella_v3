# ===== Stage 1: build dependencies =====
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ===== Stage 2: runtime =====
FROM python:3.11-slim

# Non-root user
RUN useradd -ms /bin/bash appuser

# Minimal system deps (+ curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Wheels → install
COPY --from=builder /wheels /wheels
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir /wheels/*

# App code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY entrypoint.sh ./entrypoint.sh

USER appuser

ENV PYTHONUNBUFFERED=1 \
    UVICORN_WORKERS=2 \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000

EXPOSE 8000

# Healthcheck (simple & valid for Dockerfile)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

ENTRYPOINT ["/bin/bash", "entrypoint.sh"]