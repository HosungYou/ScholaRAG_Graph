# ScholaRAG_Graph Backend Dockerfile
# Multi-stage build for optimized image size

# ===== Stage 1: Builder =====
FROM python:3.14-slim as builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
# Use requirements-base.txt for lightweight image (~200MB less without PyTorch)
# Set ENABLE_SPECTER2=true to include SPECTER2 embeddings (adds ~700MB)
WORKDIR /build
ARG ENABLE_SPECTER2=false
COPY backend/requirements-base.txt .
COPY backend/requirements-specter.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-base.txt && \
    if [ "$ENABLE_SPECTER2" = "true" ]; then \
        pip install --no-cache-dir -r requirements-specter.txt; \
    fi

# ===== Stage 2: Runtime =====
FROM python:3.14-slim as runtime

# Labels
LABEL maintainer="Hosung You"
LABEL description="ScholaRAG_Graph Backend API Server"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy application code
COPY backend/ .

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port (Render uses PORT env var, default 10000)
EXPOSE 10000

# Health check (using PORT env var)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

# Run the application (Render injects PORT env var)
# CRITICAL: --proxy-headers enables X-Forwarded-Proto support for HTTPS redirects
# --forwarded-allow-ips="*" trusts all proxies (Render's load balancer)
# Without this, FastAPI redirects use http:// causing Mixed Content errors
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips="*"
