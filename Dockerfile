# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Multi-stage Dockerfile for Vedfolnir - optimized for python:3.12-slim with Debian dependencies

# Base stage with common dependencies
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for Debian
RUN apt-get update && apt-get install -y \
    # Essential build tools
    build-essential \
    pkg-config \
    # MySQL client and development libraries
    default-mysql-client \
    default-libmysqlclient-dev \
    # Network and security tools
    curl \
    wget \
    ca-certificates \
    # Git for version control
    git \
    # Image processing libraries
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    # Additional libraries for Python packages
    libffi-dev \
    libssl-dev \
    # Process management
    procps \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r vedfolnir && useradd -r -g vedfolnir -d /app -s /bin/bash vedfolnir

# Development stage
FROM base as development

# Install development dependencies
RUN apt-get update && apt-get install -y \
    # Development tools
    vim \
    less \
    htop \
    tree \
    # Debugging tools
    strace \
    gdb \
    # Network debugging
    netcat-openbsd \
    telnet \
    iputils-ping \
    # Process monitoring
    procps \
    psmisc \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY requirements.txt requirements-development.txt ./

# Install Python dependencies with development packages
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-development.txt \
    && pip install --no-cache-dir \
        debugpy \
        pytest \
        pytest-cov \
        pytest-mock \
        black \
        flake8 \
        mypy \
        ipython \
        memory-profiler \
        py-spy \
        gunicorn[eventlet]

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs/{app,gunicorn,rq,audit,debug} \
    /app/storage/{images,backups,temp,debug} \
    /app/config \
    /app/test-results \
    && chown -R vedfolnir:vedfolnir /app

# Copy and set permissions for scripts
COPY docker/scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh \
    && chown -R vedfolnir:vedfolnir /app/scripts

# Switch to non-root user
USER vedfolnir

# Set environment variables for development
ENV FLASK_ENV=development \
    FLASK_DEBUG=1 \
    LOG_LEVEL=DEBUG \
    CONTAINER_ENV=true \
    RQ_ENABLE_INTEGRATED_WORKERS=false \
    DEBUGPY_ENABLED=true \
    DEBUGPY_PORT=5678 \
    DEBUGPY_WAIT_FOR_CLIENT=false \
    PYTHONPATH=/app \
    HOT_RELOAD=true \
    PROFILING_ENABLED=true

# Expose ports (Flask app, debugger, Node.js debugger)
EXPOSE 5000 5678 9229

# Health check for development
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD /app/scripts/health-check-dev.sh

# Development command with debugger support
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "web_app.py"]

# Production stage
FROM base as production

# Copy requirements first for better caching
COPY requirements.txt requirements-production.txt ./

# Install Python dependencies (production only)
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-production.txt \
    && pip install --no-cache-dir \
        gunicorn[eventlet] \
        prometheus-client

# Copy application code
COPY . .

# Remove development files and unnecessary content for production
RUN rm -rf \
    tests/ \
    docs/ \
    .git/ \
    .pytest_cache/ \
    __pycache__/ \
    *.pyc \
    requirements-development.txt \
    .gitignore

# Create necessary directories with proper structure
RUN mkdir -p /app/logs/{app,gunicorn,rq,audit} \
    /app/storage/{images,backups,temp} \
    /app/config \
    && chown -R vedfolnir:vedfolnir /app

# Copy and set permissions for scripts
COPY docker/scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh \
    && chown -R vedfolnir:vedfolnir /app/scripts

# Switch to non-root user
USER vedfolnir

# Set environment variables for production
ENV FLASK_ENV=production \
    FLASK_DEBUG=0 \
    LOG_LEVEL=INFO \
    CONTAINER_ENV=true \
    RQ_ENABLE_INTEGRATED_WORKERS=true \
    ENABLE_JSON_LOGGING=true \
    PERFORMANCE_MONITORING_ENABLED=true \
    HEALTH_CHECK_ENABLED=true \
    PYTHONPATH=/app \
    PROMETHEUS_ENABLED=true \
    METRICS_ENABLED=true

# Health check using production script
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=3 \
    CMD /app/scripts/health-check.sh

# Expose application port
EXPOSE 5000

# Production command using Gunicorn
CMD ["gunicorn", "--config", "gunicorn.conf.py", "web_app:app"]