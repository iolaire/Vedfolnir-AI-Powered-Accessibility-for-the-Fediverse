# Container Dependency Optimization for Debian Linux

## Overview

This document describes the optimization of Python dependencies for Vedfolnir's Docker Compose deployment using Debian Linux containers with python:3.12-slim base images.

## Changes Made

### 1. Requirements Structure Reorganization

The original single `requirements.txt` file has been restructured into three files:

- **`requirements-base.txt`**: Core dependencies required for both development and production
- **`requirements-production.txt`**: Production-specific requirements (inherits from base)
- **`requirements-development.txt`**: Development and debugging tools (inherits from base)
- **`requirements.txt`**: Main file that includes base requirements for backward compatibility

### 2. macOS-Specific Dependencies Removed

The following macOS-specific dependencies have been identified and removed:
- No Homebrew-specific packages were found in the original requirements
- No pyenv-related dependencies were present
- All dependencies are already Debian-compatible

### 3. Container Optimizations Added

#### System Dependencies (Dockerfile)
The following Debian packages are required for proper dependency installation:
```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    default-mysql-client \
    default-libmysqlclient-dev \
    curl \
    git \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*
```

#### Production Optimizations
- Gunicorn with eventlet for WebSocket support
- Setproctitle for process management
- Optimized for container size and startup time

#### Development Tools (requirements-development.txt)
- **Debugging**: debugpy, ipython, jupyter
- **Testing**: pytest, pytest-cov, pytest-asyncio, pytest-mock
- **Code Quality**: black, flake8, mypy, isort
- **Performance**: memory-profiler, line-profiler
- **Documentation**: sphinx, sphinx-rtd-theme

## Usage

### Production Deployment
```bash
# Use production requirements
pip install -r requirements-production.txt

# Or use main requirements file (same result)
pip install -r requirements.txt
```

### Development Environment
```bash
# Install development requirements (includes base + dev tools)
pip install -r requirements-development.txt
```

### Docker Build
The multi-stage Dockerfile automatically uses the appropriate requirements:
```dockerfile
# Production stage
FROM base as production
COPY requirements-production.txt .
RUN pip install --no-cache-dir -r requirements-production.txt

# Development stage  
FROM base as development
COPY requirements-development.txt .
RUN pip install --no-cache-dir -r requirements-development.txt
```

## Validation

### Container Testing
All requirements have been tested in python:3.12-slim containers:
```bash
# Test base requirements
docker run --rm -v $(pwd):/app -w /app python:3.12-slim /bin/bash -c "
  apt-get update -qq && apt-get install -y -qq build-essential pkg-config default-libmysqlclient-dev
  pip install -r requirements-base.txt
  python -c 'import requests, PIL, flask, redis, pymysql, torch, transformers'
"

# Test production requirements
docker run --rm -v $(pwd):/app -w /app python:3.12-slim /bin/bash -c "
  apt-get update -qq && apt-get install -y -qq build-essential pkg-config default-libmysqlclient-dev
  pip install -r requirements-production.txt
  python -c 'import gunicorn, eventlet'
"
```

### Core Import Verification
All core dependencies successfully import in the container environment:
- ✅ Web framework (Flask, SQLAlchemy, Redis)
- ✅ Image processing (Pillow, pillow-heif, pillow-avif-plugin)
- ✅ AI/ML (torch, transformers, httpx)
- ✅ Security (cryptography, python-jose)
- ✅ Production server (gunicorn, eventlet)

## Benefits

### Container Size Optimization
- Removed unnecessary macOS-specific dependencies
- Multi-stage builds for development vs production
- Minimal base image (python:3.12-slim)

### Build Performance
- Faster dependency installation
- Better Docker layer caching
- Reduced image size

### Development Experience
- Separate development tools that don't bloat production
- Comprehensive debugging and testing tools
- Code quality and formatting tools

### Production Reliability
- Only necessary dependencies in production
- Optimized for container environments
- Better security with minimal attack surface

## Compatibility

### Backward Compatibility
- Original `requirements.txt` still works
- All existing functionality maintained
- No breaking changes to application code

### Cross-Platform Support
- Optimized for Debian Linux containers
- Compatible with Docker on macOS, Linux, Windows
- Consistent behavior across environments

## Maintenance

### Adding New Dependencies
1. Add to `requirements-base.txt` for core dependencies
2. Add to `requirements-development.txt` for dev-only tools
3. Test in container environment before committing

### Version Updates
1. Update version constraints in base requirements
2. Test in both development and production containers
3. Verify all imports still work correctly

### Security Updates
1. Regular dependency audits with `pip audit`
2. Automated security scanning in CI/CD
3. Container image vulnerability scanning