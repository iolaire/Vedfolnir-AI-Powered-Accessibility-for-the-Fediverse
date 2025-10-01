#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Validate Nginx configuration for Docker Compose deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Validating Nginx configuration for Vedfolnir Docker deployment..."

cd "$PROJECT_ROOT"

# Check if required files exist
echo "Checking configuration files..."

REQUIRED_FILES=(
    "config/nginx/nginx.conf"
    "config/nginx/default.conf"
    "config/nginx/nginx_status.conf"
    "ssl/certs/vedfolnir.crt"
    "ssl/keys/vedfolnir.key"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
        exit 1
    fi
done

# Check SSL certificate validity
echo ""
echo "Checking SSL certificate..."
if openssl x509 -in ssl/certs/vedfolnir.crt -noout -checkend 86400; then
    echo "✅ SSL certificate is valid"
else
    echo "❌ SSL certificate is invalid or expired"
    exit 1
fi

# Check certificate and key match
CERT_MODULUS=$(openssl x509 -noout -modulus -in ssl/certs/vedfolnir.crt | openssl md5)
KEY_MODULUS=$(openssl rsa -noout -modulus -in ssl/keys/vedfolnir.key 2>/dev/null | openssl md5)

if [ "$CERT_MODULUS" = "$KEY_MODULUS" ]; then
    echo "✅ SSL certificate and key match"
else
    echo "❌ SSL certificate and key do not match"
    exit 1
fi

# Check Docker Compose configuration
echo ""
echo "Checking Docker Compose configuration..."
if docker-compose config >/dev/null 2>&1; then
    echo "✅ Docker Compose configuration is valid"
else
    echo "❌ Docker Compose configuration is invalid"
    docker-compose config
    exit 1
fi

# Check if Nginx service is defined
if docker-compose config | grep -q "nginx:"; then
    echo "✅ Nginx service is defined in Docker Compose"
else
    echo "❌ Nginx service not found in Docker Compose"
    exit 1
fi

# Test Nginx configuration syntax (if container is available)
echo ""
echo "Testing Nginx configuration syntax..."
if docker ps | grep -q vedfolnir_nginx; then
    echo "Nginx container is running, testing configuration..."
    if docker exec vedfolnir_nginx nginx -t; then
        echo "✅ Nginx configuration syntax is valid"
    else
        echo "❌ Nginx configuration syntax error"
        exit 1
    fi
else
    echo "⚠️  Nginx container not running, skipping syntax test"
    echo "   Start container with: docker-compose up -d nginx"
fi

# Check directory permissions
echo ""
echo "Checking directory permissions..."
if [ -r "ssl/keys/vedfolnir.key" ]; then
    KEY_PERMS=$(stat -f "%A" ssl/keys/vedfolnir.key 2>/dev/null || stat -c "%a" ssl/keys/vedfolnir.key 2>/dev/null)
    if [ "$KEY_PERMS" = "600" ] || [ "$KEY_PERMS" = "400" ]; then
        echo "✅ SSL key has secure permissions ($KEY_PERMS)"
    else
        echo "⚠️  SSL key permissions could be more secure (current: $KEY_PERMS, recommended: 600)"
    fi
else
    echo "❌ Cannot read SSL key file"
    exit 1
fi

# Check configuration content
echo ""
echo "Checking configuration content..."

# Check for security headers
if grep -q "X-Content-Type-Options" config/nginx/default.conf; then
    echo "✅ Security headers configured"
else
    echo "❌ Security headers missing"
    exit 1
fi

# Check for rate limiting
if grep -q "limit_req_zone" config/nginx/default.conf; then
    echo "✅ Rate limiting configured"
else
    echo "❌ Rate limiting not configured"
    exit 1
fi

# Check for SSL configuration
if grep -q "ssl_certificate" config/nginx/default.conf; then
    echo "✅ SSL configuration present"
else
    echo "❌ SSL configuration missing"
    exit 1
fi

# Check for WebSocket support
if grep -q "proxy_set_header Upgrade" config/nginx/default.conf; then
    echo "✅ WebSocket proxy support configured"
else
    echo "❌ WebSocket proxy support missing"
    exit 1
fi

# Check for static file serving
if grep -q "location /static/" config/nginx/default.conf; then
    echo "✅ Static file serving configured"
else
    echo "❌ Static file serving not configured"
    exit 1
fi

echo ""
echo "✅ Nginx configuration validation complete!"
echo ""
echo "Configuration summary:"
echo "  - SSL/TLS termination: Enabled"
echo "  - Security headers: Configured"
echo "  - Rate limiting: Enabled"
echo "  - WebSocket support: Enabled"
echo "  - Static file serving: Enabled"
echo "  - Monitoring endpoint: Enabled"
echo ""
echo "To start Nginx service:"
echo "  docker-compose up -d nginx"
echo ""
echo "To test the deployment:"
echo "  curl -I http://localhost"
echo "  curl -k -I https://localhost"