# syntax=docker/dockerfile:1.7
# ---- base ----
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Minimal system deps
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# ---- lock: resolve and hash-lock runtime deps ----
FROM base AS lock

WORKDIR /lock
RUN pip install --no-cache-dir pip-tools
COPY requirements.runtime.in /lock/requirements.runtime.in
# If you later add constraints.txt, append: -c constraints.txt
RUN pip-compile --generate-hashes -o /lock/requirements.runtime.txt /lock/requirements.runtime.in

# ---- runtime ----
FROM base AS runtime

# Create non-root user & working dir
RUN useradd -m -u 10001 appuser
WORKDIR /app

# Install only hashed, minimal runtime deps
COPY --from=lock /lock/requirements.runtime.txt /app/requirements.runtime.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --require-hashes -r /app/requirements.runtime.txt

# Copy source with proper ownership (avoid root-owned files)
COPY --chown=appuser:appuser . /app

# Drop privileges
USER appuser

# Pass-through CLI args to simulator
ENTRYPOINT ["python", "/app/simulate.py"]


