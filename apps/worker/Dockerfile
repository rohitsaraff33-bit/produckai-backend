FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (same as API)
COPY apps/api/requirements.txt /app/apps/api/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt

# Copy application code
COPY apps/api /app/apps/api
COPY apps/worker /app/apps/worker
COPY packages /app/packages
COPY infra /app/infra
COPY samples /app/samples

# Set Python path
ENV PYTHONPATH=/app

# Default command (overridden in docker-compose)
CMD ["celery", "-A", "apps.worker.celery_app", "worker", "--loglevel=info"]
