# ReconAgent — Production Dockerfile (Backend API)
# Build: docker build -t reconagent:latest .
# Run:   docker run -p 8000:8000 --env-file .env reconagent:latest

FROM python:3.12.3-slim AS base

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY .python-version .

# Create data directory and set permissions
RUN mkdir -p /app/backend/data && \
    chown -R appuser:appuser /app

USER appuser

# Environment variables (can be overridden at runtime)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    RECON_DB_PATH=/app/backend/data/recon.sqlite3 \
    LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=2)" || exit 1

EXPOSE 8000

# Run the FastAPI application with uvicorn
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]