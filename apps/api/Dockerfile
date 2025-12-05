FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY apps/api/requirements.txt /app/apps/api/requirements.txt

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Install numpy and cython first (needed for hdbscan)
RUN pip install --no-cache-dir numpy==1.26.3 cython

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt || \
    (pip install --no-cache-dir scikit-learn-intelex && \
     pip install --no-cache-dir -r /app/apps/api/requirements.txt)

# Copy application code
COPY apps/api /app/apps/api
COPY packages /app/packages
COPY infra /app/infra
COPY samples /app/samples
COPY alembic.ini /app/alembic.ini

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Default command (overridden in docker-compose)
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
