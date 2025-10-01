#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Vedfolnir Observability Stack Setup Script

set -e

echo "=== Vedfolnir Observability Stack Setup ==="

# Create necessary directories
echo "Creating observability directories..."
mkdir -p data/{prometheus,grafana,loki}
mkdir -p logs/{prometheus,grafana,loki}
mkdir -p config/{prometheus/rules,grafana/{provisioning/{datasources,dashboards},dashboards},loki}

# Set proper permissions
echo "Setting directory permissions..."
sudo chown -R 472:472 data/grafana  # Grafana user
sudo chown -R 65534:65534 data/prometheus  # Nobody user for Prometheus
sudo chown -R 10001:10001 data/loki  # Loki user

# Generate secrets if they don't exist
echo "Generating observability secrets..."
if [ ! -f secrets/grafana_admin_password.txt ]; then
    openssl rand -base64 32 > secrets/grafana_admin_password.txt
    echo "Generated Grafana admin password"
fi

if [ ! -f secrets/grafana_secret_key.txt ]; then
    openssl rand -base64 32 > secrets/grafana_secret_key.txt
    echo "Generated Grafana secret key"
fi

if [ ! -f secrets/mysql_exporter_password.txt ]; then
    openssl rand -base64 16 > secrets/mysql_exporter_password.txt
    echo "Generated MySQL exporter password"
fi

echo "Observability stack setup complete!"
echo "Next steps:"
echo "1. Update .env file with observability configuration"
echo "2. Start the observability stack: docker-compose up -d prometheus grafana loki"
echo "3. Access Grafana at http://localhost:3000 (admin/[generated_password])"