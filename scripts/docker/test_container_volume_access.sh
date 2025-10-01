#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Test script to verify container volume access
# This script tests that containers can properly access mounted volumes

set -e

echo "=== Container Volume Access Test ==="
echo "Testing volume access from within containers"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗${NC} docker-compose not found"
    exit 1
fi

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}✗${NC} docker-compose.yml not found"
    exit 1
fi

echo "1. Testing Volume Mount Configuration"
echo "===================================="

# Test that all required directories exist
required_dirs=(
    "./storage"
    "./logs"
    "./config"
    "./data"
    "./secrets"
    "./ssl"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} Directory exists: $dir"
    else
        echo -e "${RED}✗${NC} Directory missing: $dir"
        mkdir -p "$dir"
        echo -e "${YELLOW}  Created: $dir${NC}"
    fi
done

echo
echo "2. Testing Docker Compose Configuration"
echo "======================================"

# Validate docker-compose.yml
if docker-compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker Compose configuration is valid"
else
    echo -e "${RED}✗${NC} Docker Compose configuration has errors"
    docker-compose config
    exit 1
fi

echo
echo "3. Creating Test Files for Volume Access"
echo "======================================="

# Create test files in each directory
test_timestamp=$(date +%s)

test_files=(
    "./storage/volume_test_${test_timestamp}.txt"
    "./logs/volume_test_${test_timestamp}.txt"
    "./config/app/volume_test_${test_timestamp}.txt"
    "./data/mysql/volume_test_${test_timestamp}.txt"
    "./data/redis/volume_test_${test_timestamp}.txt"
    "./data/prometheus/volume_test_${test_timestamp}.txt"
    "./data/grafana/volume_test_${test_timestamp}.txt"
    "./data/loki/volume_test_${test_timestamp}.txt"
)

for test_file in "${test_files[@]}"; do
    # Ensure directory exists
    mkdir -p "$(dirname "$test_file")"
    
    # Create test file
    echo "Volume mount test - created at $(date)" > "$test_file"
    if [ -f "$test_file" ]; then
        echo -e "${GREEN}✓${NC} Created test file: $test_file"
    else
        echo -e "${RED}✗${NC} Failed to create test file: $test_file"
    fi
done

echo
echo "4. Testing Container Volume Access (requires running containers)"
echo "=============================================================="

# Check if containers are running
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Some containers are running"
    
    # Test Vedfolnir app container volume access
    if docker-compose ps vedfolnir | grep -q "Up"; then
        echo "Testing Vedfolnir app container volume access:"
        
        # Test storage volume
        if docker-compose exec -T vedfolnir test -f "/app/storage/volume_test_${test_timestamp}.txt"; then
            echo -e "${GREEN}  ✓${NC} Storage volume accessible: /app/storage"
        else
            echo -e "${RED}  ✗${NC} Storage volume not accessible: /app/storage"
        fi
        
        # Test logs volume
        if docker-compose exec -T vedfolnir test -d "/app/logs"; then
            echo -e "${GREEN}  ✓${NC} Logs volume accessible: /app/logs"
        else
            echo -e "${RED}  ✗${NC} Logs volume not accessible: /app/logs"
        fi
        
        # Test config volume
        if docker-compose exec -T vedfolnir test -d "/app/config"; then
            echo -e "${GREEN}  ✓${NC} Config volume accessible: /app/config"
        else
            echo -e "${RED}  ✗${NC} Config volume not accessible: /app/config"
        fi
    else
        echo -e "${YELLOW}!${NC} Vedfolnir container not running - skipping container tests"
    fi
    
    # Test MySQL container volume access
    if docker-compose ps mysql | grep -q "Up"; then
        echo "Testing MySQL container volume access:"
        
        if docker-compose exec -T mysql test -f "/var/lib/mysql/volume_test_${test_timestamp}.txt"; then
            echo -e "${GREEN}  ✓${NC} MySQL data volume accessible: /var/lib/mysql"
        else
            echo -e "${RED}  ✗${NC} MySQL data volume not accessible: /var/lib/mysql"
        fi
    else
        echo -e "${YELLOW}!${NC} MySQL container not running - skipping MySQL tests"
    fi
    
    # Test Redis container volume access
    if docker-compose ps redis | grep -q "Up"; then
        echo "Testing Redis container volume access:"
        
        if docker-compose exec -T redis test -f "/data/volume_test_${test_timestamp}.txt"; then
            echo -e "${GREEN}  ✓${NC} Redis data volume accessible: /data"
        else
            echo -e "${RED}  ✗${NC} Redis data volume not accessible: /data"
        fi
    else
        echo -e "${YELLOW}!${NC} Redis container not running - skipping Redis tests"
    fi
    
else
    echo -e "${YELLOW}!${NC} No containers are running"
    echo "To test container volume access, start the services with:"
    echo "  docker-compose up -d"
    echo "Then run this script again."
fi

echo
echo "5. Cleanup Test Files"
echo "===================="

# Clean up test files
for test_file in "${test_files[@]}"; do
    if [ -f "$test_file" ]; then
        rm -f "$test_file"
        echo -e "${GREEN}✓${NC} Cleaned up: $test_file"
    fi
done

echo
echo "6. Volume Mount Summary"
echo "======================"
echo "Volume mount configuration test completed."
echo
echo "Key volume mounts configured:"
echo "- Application storage: ./storage → /app/storage"
echo "- Application logs: ./logs/app → /app/logs"
echo "- Application config: ./config/app → /app/config"
echo "- MySQL data: ./data/mysql → /var/lib/mysql"
echo "- Redis data: ./data/redis → /data"
echo "- Prometheus data: ./data/prometheus → /prometheus"
echo "- Grafana data: ./data/grafana → /var/lib/grafana"
echo "- Loki data: ./data/loki → /loki"
echo "- Vault data: ./data/vault → /vault/data"
echo "- Secrets: ./secrets → /vault/secrets"
echo
echo -e "${GREEN}Container volume access test completed!${NC}"