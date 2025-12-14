# Production Dockerfile for Django Backend Service
# Optimized for Google Cloud Run

# Use Python 3.12 slim image (latest stable)
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files (skip if fails - not critical for startup)
RUN python manage.py collectstatic --noinput || echo "Warning: collectstatic failed, continuing..."

# Expose port (Cloud Run uses PORT env var, defaults to 8080)
EXPOSE 8080

# Use PORT environment variable (Cloud Run sets this)
# Run both PBX monitor and Gunicorn
# PBX monitor runs in background, Gunicorn runs in foreground
# Both log to stdout → GCP captures all logs
CMD sh -c "python manage.py monitor_pbx & exec gunicorn config.wsgi:application --bind 0.0.0.0:\${PORT:-8080} --workers 2 --worker-class sync --timeout 300 --keep-alive 5 --access-logfile - --error-logfile - --log-level info --capture-output"

