#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Test script to verify all Docker volume mounts are working correctly
# This script tests external access to all mounted volumes from the host system

set -e

echo "=== Docker Volume Mount Test ==="
echo "Testing external access to all mounted volumes from host system"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_directory() {
    local dir="$1"
    local description="$2"
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $description: $dir exists"
        
        # Test write access
        test_file="$dir/.volume_test_$(date +%s)"
        if echo "test" > "$test_file" 2>/dev/null; then
            echo -e "${GREEN}  ✓${NC} Write access confirmed"
            rm -f "$test_file"
        else
            echo -e "${YELLOW}  !${NC} Write access limited (may be read-only)"
        fi
    else
        echo -e "${RED}✗${NC} $description: $dir does not exist"
        return 1
    fi
}

# Test function for files
test_file() {
    local file="$1"
    local description="$2"
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description: $file exists"
    else
        echo -e "${YELLOW}!${NC} $description: $file does not exist (will be created by service)"
    fi
}

echo "1. Testing Application Storage Volume Mounts"
echo "============================================="
test_directory "./storage" "Application storage root"
test_directory "./storage/images" "Image storage"
test_directory "./storage/backups" "Backup storage"
test_directory "./storage/backups/mysql" "MySQL backup storage"
test_directory "./storage/backups/redis" "Redis backup storage"
test_directory "./storage/backups/app" "Application backup storage"
test_directory "./storage/temp" "Temporary storage"
echo

echo "2. Testing Logs Volume Mounts"
echo "=============================="
test_directory "./logs" "Logs root directory"
test_directory "./logs/app" "Application logs"
test_directory "./logs/mysql" "MySQL logs"
test_directory "./logs/redis" "Redis logs"
test_directory "./logs/nginx" "Nginx logs"
test_directory "./logs/vault" "Vault logs"
test_directory "./logs/audit" "Audit logs"
echo

echo "3. Testing Configuration Volume Mounts"
echo "======================================"
test_directory "./config" "Configuration root"
test_directory "./config/app" "Application configuration"
test_directory "./config/mysql" "MySQL configuration"
test_directory "./config/redis" "Redis configuration"
test_directory "./config/nginx" "Nginx configuration"
test_directory "./config/prometheus" "Prometheus configuration"
test_directory "./config/grafana" "Grafana configuration"
test_directory "./config/loki" "Loki configuration"
test_directory "./config/vault" "Vault configuration"

# Test specific config files
test_file "./config/mysql/vedfolnir.cnf" "MySQL config file"
test_file "./config/redis/redis.conf" "Redis config file"
test_file "./config/nginx/default.conf" "Nginx config file"
test_file "./config/prometheus/prometheus.yml" "Prometheus config file"
test_file "./config/grafana/grafana.ini" "Grafana config file"
test_file "./config/loki/loki.yml" "Loki config file"
test_file "./config/vault/vault.hcl" "Vault config file"
echo

echo "4. Testing Monitoring Data Volume Mounts"
echo "========================================"
test_directory "./data" "Data root directory"
test_directory "./data/mysql" "MySQL data directory"
test_directory "./data/redis" "Redis data directory"
test_directory "./data/prometheus" "Prometheus data directory"
test_directory "./data/grafana" "Grafana data directory"
test_directory "./data/loki" "Loki data directory"
test_directory "./data/vault" "Vault data directory"
echo

echo "5. Testing Secrets Volume Mounts"
echo "================================="
test_directory "./secrets" "Secrets directory"
test_file "./secrets/flask_secret_key.txt" "Flask secret key"
test_file "./secrets/mysql_password.txt" "MySQL password"
test_file "./secrets/mysql_root_password.txt" "MySQL root password"
test_file "./secrets/redis_password.txt" "Redis password"
test_file "./secrets/vault_token.txt" "Vault token"
test_file "./secrets/platform_encryption_key.txt" "Platform encryption key"
echo

echo "6. Testing SSL Certificate Volume Mounts"
echo "========================================"
test_directory "./ssl" "SSL certificates directory"
echo

echo "7. Testing Docker Compose Volume Configuration"
echo "=============================================="

# Check if docker-compose.yml exists and contains volume mounts
if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✓${NC} docker-compose.yml exists"
    
    # Check for key volume mounts in docker-compose.yml
    volume_mounts=(
        "./storage:/app/storage"
        "./logs/app:/app/logs"
        "./config/app:/app/config"
        "./data/mysql:/var/lib/mysql"
        "./data/redis:/data"
        "./secrets:/vault/secrets"
        "./config/prometheus:/etc/prometheus"
        "./data/prometheus:/prometheus"
        "./config/grafana"
        "./data/grafana:/var/lib/grafana"
        "./config/loki"
        "./data/loki:/loki"
    )
    
    for mount in "${volume_mounts[@]}"; do
        if grep -q "$mount" docker-compose.yml; then
            echo -e "${GREEN}  ✓${NC} Volume mount configured: $mount"
        else
            echo -e "${RED}  ✗${NC} Volume mount missing: $mount"
        fi
    done
else
    echo -e "${RED}✗${NC} docker-compose.yml not found"
fi
echo

echo "8. Testing Volume Mount Permissions"
echo "==================================="

# Test creating test files in each directory to verify write permissions
test_dirs=(
    "./storage/images"
    "./storage/backups"
    "./logs/app"
    "./config/app"
    "./data/mysql"
    "./data/redis"
    "./data/prometheus"
    "./data/grafana"
    "./data/loki"
)

for dir in "${test_dirs[@]}"; do
    if [ -d "$dir" ]; then
        test_file="$dir/.permission_test_$(date +%s)"
        if echo "permission test" > "$test_file" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Write permission confirmed: $dir"
            rm -f "$test_file"
        else
            echo -e "${YELLOW}!${NC} Write permission denied: $dir (may need container user)"
        fi
    fi
done
echo

echo "9. Volume Mount Summary"
echo "======================"
echo "All volume mounts have been tested for:"
echo "- Directory existence"
echo "- Write access from host"
echo "- Docker Compose configuration"
echo
echo "Note: Some directories may show write permission issues from the host"
echo "but will work correctly when accessed from within containers with"
echo "appropriate user permissions."
echo
echo -e "${GREEN}Volume mount test completed!${NC}"