# Multi-stage Dockerfile for OPTIX Adaptive Intelligence Engine

# Stage 1: Builder
FROM python:3.9-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.9-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 optix && \
    chown -R optix:optix /app

# Copy installed dependencies from builder
COPY --from=builder /root/.local /home/optix/.local

# Copy application code
COPY --chown=optix:optix src/ ./src/
COPY --chown=optix:optix config/ ./config/

# Set environment variables
ENV PATH=/home/optix/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER optix

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
