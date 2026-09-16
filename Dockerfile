
# ═══════════════════════════════════════════════════════════════
# DataTrust — Docker Image
# ═══════════════════════════════════════════════════════════════
FROM python:3.12-slim

LABEL maintainer="Khethukuthula Sabela"
LABEL description="DataTrust — Autonomous Data Integrity, Observability & Recovery"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY config.yaml .
COPY datatrust.py .
COPY src/ src/
COPY tests/ tests/

# Create data directories
RUN mkdir -p data/clean data/corrupted data/recovered data/quarantine \
    data/reports data/dashboard logs

# Environment variables
ENV PYTHONPATH=/app/src/validation:/app/src/data_generation:/app/src/utils:/app/src
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command: show status
CMD ["python", "datatrust.py", "status"]

