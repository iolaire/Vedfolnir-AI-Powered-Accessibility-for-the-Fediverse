#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Docker Compose validation script for Vedfolnir
# Validates configuration files and directory structure

set -e

echo "=== Vedfolnir Docker Compose Validation ==="

# Check Docker and Docker Compose
echo "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Validate Docker Compose file
echo "Validating docker-compose.yml..."
if docker-compose config > /dev/null 2>&1; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors"
    docker-compose config
    exit 1
fi

# Check required directories
echo "Checking directory structure..."
required_dirs=(
    "config/mysql"
    "config/redis"
    "config/nginx"
    "config/prometheus"
    "config/grafana"
    "config/loki"
    "config/vault"
    "secrets"
    "storage/backups"
    "logs"
    "ssl"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ Directory $dir exists"
    else
        echo "❌ Directory $dir is missing"
        exit 1
    fi
done

# Check required configuration files
echo "Checking configuration files..."
required_files=(
    "Dockerfile"
    "gunicorn.conf.py"
    "config/mysql/vedfolnir.cnf"
    "config/redis/redis.conf"
    "config/nginx/default.conf"
    "config/prometheus/prometheus.yml"
    "config/loki/loki.yml"
    "config/vault/vault.hcl"
    "config/grafana/grafana.ini"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ Configuration file $file exists"
    else
        echo "❌ Configuration file $file is missing"
        exit 1
    fi
done

# Check secret files (should exist but may contain placeholders)
echo "Checking secret files..."
secret_files=(
    "secrets/flask_secret_key.txt"
    "secrets/platform_encryption_key.txt"
    "secrets/mysql_root_password.txt"
    "secrets/mysql_password.txt"
    "secrets/redis_password.txt"
    "secrets/vault_token.txt"
)

for file in "${secret_files[@]}"; do
    if [ -f "$file" ]; then
        if grep -q "CHANGE_ME" "$file"; then
            echo "⚠️  Secret file $file contains placeholder - update before deployment"
        else
            echo "✅ Secret file $file exists and appears configured"
        fi
    else
        echo "❌ Secret file $file is missing"
        exit 1
    fi
done

# Check environment file
if [ -f ".env" ]; then
    echo "✅ Environment file .env exists"
    if grep -q "your_secure.*password" .env; then
        echo "⚠️  Environment file contains placeholder passwords - update before deployment"
    fi
elif [ -f ".env.docker" ]; then
    echo "⚠️  Template .env.docker exists but .env is missing - copy and configure .env"
else
    echo "❌ No environment configuration found"
    exit 1
fi

# Validate Dockerfile
echo "Validating Dockerfile..."
if docker build --target base -t vedfolnir-test . > /dev/null 2>&1; then
    echo "✅ Dockerfile builds successfully"
    docker rmi vedfolnir-test > /dev/null 2>&1
else
    echo "❌ Dockerfile has build errors"
    exit 1
fi

# Check network configuration
echo "Checking network configuration..."
if docker-compose config | grep -q "vedfolnir_internal"; then
    echo "✅ Internal network configured"
else
    echo "❌ Internal network configuration missing"
    exit 1
fi

# Check volume configuration
echo "Checking volume configuration..."
if docker-compose config | grep -q "mysql_data"; then
    echo "✅ Volume configuration found"
else
    echo "❌ Volume configuration missing"
    exit 1
fi

# Check service dependencies
echo "Checking service dependencies..."
if docker-compose config | grep -q "depends_on"; then
    echo "✅ Service dependencies configured"
else
    echo "❌ Service dependencies missing"
    exit 1
fi

echo ""
echo "=== Validation Summary ==="
echo "✅ All basic validation checks passed"
echo ""
echo "Next steps:"
echo "1. Update secret files with secure values"
echo "2. Configure .env file with your settings"
echo "3. Generate SSL certificates if needed"
echo "4. Run: docker-compose up -d"
echo ""
echo "For detailed setup instructions, see DOCKER_SETUP.md"