#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Validation script for container dependency optimization
# Tests Python dependencies in python:3.12-slim container environment

set -e

echo "🐳 Container Dependency Validation Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

print_status "Docker is available"

# Test base requirements
print_status "Testing base requirements in python:3.12-slim container..."
docker run --rm -v "$(pwd):/app" -w /app python:3.12-slim /bin/bash -c "
    echo 'Installing system dependencies...'
    apt-get update -qq
    apt-get install -y -qq \
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
        libssl-dev
    
    echo 'Installing base requirements...'
    pip install --no-cache-dir -r requirements-base.txt
    
    echo 'Testing core imports...'
    python -c '
import sys
try:
    import requests
    print(\"✅ requests imported successfully\")
except ImportError as e:
    print(f\"❌ requests import failed: {e}\")
    sys.exit(1)

try:
    import PIL
    print(\"✅ Pillow imported successfully\")
except ImportError as e:
    print(f\"❌ Pillow import failed: {e}\")
    sys.exit(1)

try:
    import flask
    print(\"✅ Flask imported successfully\")
except ImportError as e:
    print(f\"❌ Flask import failed: {e}\")
    sys.exit(1)

try:
    import redis
    print(\"✅ Redis imported successfully\")
except ImportError as e:
    print(f\"❌ Redis import failed: {e}\")
    sys.exit(1)

try:
    import pymysql
    print(\"✅ PyMySQL imported successfully\")
except ImportError as e:
    print(f\"❌ PyMySQL import failed: {e}\")
    sys.exit(1)

try:
    import torch
    print(\"✅ PyTorch imported successfully\")
except ImportError as e:
    print(f\"❌ PyTorch import failed: {e}\")
    sys.exit(1)

try:
    import transformers
    print(\"✅ Transformers imported successfully\")
except ImportError as e:
    print(f\"❌ Transformers import failed: {e}\")
    sys.exit(1)

print(\"🎉 All base requirements imported successfully!\")
'
"

if [ $? -eq 0 ]; then
    print_success "Base requirements validation passed"
else
    print_error "Base requirements validation failed"
    exit 1
fi

# Test production requirements
print_status "Testing production requirements..."
docker run --rm -v "$(pwd):/app" -w /app python:3.12-slim /bin/bash -c "
    echo 'Installing system dependencies...'
    apt-get update -qq
    apt-get install -y -qq \
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
        libssl-dev
    
    echo 'Installing production requirements...'
    pip install --no-cache-dir -r requirements-production.txt
    
    echo 'Testing production imports...'
    python -c '
import sys
try:
    import gunicorn
    print(\"✅ Gunicorn imported successfully\")
except ImportError as e:
    print(f\"❌ Gunicorn import failed: {e}\")
    sys.exit(1)

try:
    import eventlet
    print(\"✅ Eventlet imported successfully\")
except ImportError as e:
    print(f\"❌ Eventlet import failed: {e}\")
    sys.exit(1)

print(\"🎉 All production requirements imported successfully!\")
'
"

if [ $? -eq 0 ]; then
    print_success "Production requirements validation passed"
else
    print_error "Production requirements validation failed"
    exit 1
fi

# Test development requirements (optional, as it's large)
read -p "Test development requirements? This will take longer due to additional packages (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Testing development requirements..."
    docker run --rm -v "$(pwd):/app" -w /app python:3.12-slim /bin/bash -c "
        echo 'Installing system dependencies...'
        apt-get update -qq
        apt-get install -y -qq \
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
            libssl-dev
        
        echo 'Installing development requirements...'
        pip install --no-cache-dir -r requirements-development.txt
        
        echo 'Testing development imports...'
        python -c '
import sys
try:
    import pytest
    print(\"✅ Pytest imported successfully\")
except ImportError as e:
    print(f\"❌ Pytest import failed: {e}\")
    sys.exit(1)

try:
    import black
    print(\"✅ Black imported successfully\")
except ImportError as e:
    print(f\"❌ Black import failed: {e}\")
    sys.exit(1)

try:
    import debugpy
    print(\"✅ Debugpy imported successfully\")
except ImportError as e:
    print(f\"❌ Debugpy import failed: {e}\")
    sys.exit(1)

print(\"🎉 All development requirements imported successfully!\")
'
    "
    
    if [ $? -eq 0 ]; then
        print_success "Development requirements validation passed"
    else
        print_error "Development requirements validation failed"
        exit 1
    fi
else
    print_warning "Skipping development requirements test"
fi

# Test main requirements.txt for backward compatibility
print_status "Testing main requirements.txt for backward compatibility..."
docker run --rm -v "$(pwd):/app" -w /app python:3.12-slim /bin/bash -c "
    echo 'Installing system dependencies...'
    apt-get update -qq
    apt-get install -y -qq \
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
        libssl-dev
    
    echo 'Installing main requirements...'
    pip install --no-cache-dir -r requirements.txt
    
    echo 'Testing backward compatibility...'
    python -c 'import requests, flask, redis, pymysql; print(\"✅ Backward compatibility maintained\")'
"

if [ $? -eq 0 ]; then
    print_success "Backward compatibility validation passed"
else
    print_error "Backward compatibility validation failed"
    exit 1
fi

# Summary
echo
echo "🎉 Container Dependency Validation Complete!"
echo "============================================="
print_success "✅ Base requirements: PASSED"
print_success "✅ Production requirements: PASSED"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_success "✅ Development requirements: PASSED"
fi
print_success "✅ Backward compatibility: PASSED"
echo
print_status "All dependencies are optimized for Debian Linux containers!"
print_status "Ready for Docker Compose deployment with python:3.12-slim"