# AutoPlanner AI Gateway — Production Containerfile for Google Cloud Run

FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Runtime stage ---
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PATH=/home/appuser/.local/bin:$PATH

# Create unprivileged application user
RUN groupadd -g 10001 appuser && \
    useradd -u 10000 -g appuser -m -s /bin/bash appuser

# Copy installed dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local
RUN chown -R appuser:appuser /home/appuser/.local

# Copy application source
COPY --chown=appuser:appuser app /app/app

USER appuser

EXPOSE 8080

# Cloud Run injects $PORT at runtime
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
