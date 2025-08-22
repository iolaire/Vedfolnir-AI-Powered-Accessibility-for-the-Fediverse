# Production Dockerfile for Vedfolnir with MySQL support
# This replaces any SQLite-based Docker configurations

FROM python:3.11-slim as base

# Set build arguments
ARG BUILD_ENV=production
ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies including MySQL client
RUN apt-get update && apt-get install -y \
    # MySQL client and development libraries
    default-mysql-client \
    default-libmysqlclient-dev \
    pkg-config \
    # Build tools for Python packages
    build-essential \
    gcc \
    g++ \
    # Network and utility tools
    curl \
    wget \
    # Process management
    supervisor \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application user (non-root for security)
RUN groupadd -r vedfolnir && useradd -r -g vedfolnir -d /app -s /bin/bash vedfolnir

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p storage/images logs backups/mysql && \
    chown -R vedfolnir:vedfolnir /app && \
    chmod +x scripts/deploy_mysql.sh && \
    chmod +x docker/scripts/*.sh

# Copy Docker-specific scripts
COPY docker/scripts/wait-for-mysql.sh /usr/local/bin/
COPY docker/scripts/init-app.sh /usr/local/bin/
COPY docker/scripts/health-check.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/*.sh

# Switch to non-root user
USER vedfolnir

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/health-check.sh

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=web_app.py
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["/usr/local/bin/wait-for-mysql.sh", "mysql", "/usr/local/bin/init-app.sh"]

# Development stage
FROM base as development

# Switch back to root for development tools installation
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    # Development tools
    vim \
    git \
    htop \
    # Debugging tools
    gdb \
    strace \
    # Network debugging
    netcat-openbsd \
    telnet \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    debugpy \
    pytest \
    pytest-cov \
    flask-debugtoolbar \
    memory-profiler

# Switch back to application user
USER vedfolnir

# Development-specific environment
ENV FLASK_ENV=development
ENV FLASK_DEBUG=true
ENV LOG_LEVEL=DEBUG

# Development command with debugger support
CMD ["/usr/local/bin/wait-for-mysql.sh", "mysql", "python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "web_app.py"]

# Production stage (default)
FROM base as production

# Production-specific optimizations
ENV FLASK_ENV=production
ENV FLASK_DEBUG=false
ENV LOG_LEVEL=INFO
ENV PRODUCTION_MODE=true

# Production command
CMD ["/usr/local/bin/wait-for-mysql.sh", "mysql", "/usr/local/bin/init-app.sh"]
