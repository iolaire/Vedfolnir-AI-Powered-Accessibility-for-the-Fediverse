#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Vedfolnir Observability Stack Validation Script

set -e

echo "=== Validating Observability Stack ==="

# Check if containers are running
echo "Checking container status..."
containers=("prometheus" "grafana" "loki" "mysql-exporter" "redis-exporter" "nginx-exporter" "node-exporter" "cadvisor")

for container in "${containers[@]}"; do
    if docker-compose ps | grep -q "vedfolnir_${container}.*Up"; then
        echo "✅ ${container} is running"
    else
        echo "❌ ${container} is not running"
    fi
done

# Check service endpoints
echo "Checking service endpoints..."
services=(
    "prometheus:9090/-/healthy"
    "grafana:3000/api/health"
    "loki:3100/ready"
    "mysql-exporter:9104/metrics"
    "redis-exporter:9121/metrics"
    "nginx-exporter:9113/metrics"
    "node-exporter:9100/metrics"
    "cadvisor:8080/healthz"
)

for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    endpoint=$(echo $service | cut -d: -f2-)
    
    if curl -s -f "http://localhost:${endpoint}" > /dev/null 2>&1; then
        echo "✅ ${name} endpoint is healthy"
    else
        echo "❌ ${name} endpoint is not responding"
    fi
done

echo "Observability stack validation complete!"