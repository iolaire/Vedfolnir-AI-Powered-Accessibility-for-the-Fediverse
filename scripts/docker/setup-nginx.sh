#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Setup Nginx reverse proxy for Vedfolnir Docker deployment

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NGINX_CONFIG_DIR="$PROJECT_ROOT/config/nginx"
SSL_DIR="$PROJECT_ROOT/ssl"
LOGS_DIR="$PROJECT_ROOT/logs/nginx"

echo "Setting up Nginx reverse proxy for Vedfolnir..."

# Create required directories
echo "Creating directories..."
mkdir -p "$NGINX_CONFIG_DIR"
mkdir -p "$SSL_DIR/certs"
mkdir -p "$SSL_DIR/keys"
mkdir -p "$LOGS_DIR"

# Set proper permissions
chmod 755 "$NGINX_CONFIG_DIR"
chmod 700 "$SSL_DIR/keys"
chmod 755 "$SSL_DIR/certs"
chmod 755 "$LOGS_DIR"

# Generate SSL certificates if they don't exist
if [ ! -f "$SSL_DIR/certs/vedfolnir.crt" ] || [ ! -f "$SSL_DIR/keys/vedfolnir.key" ]; then
    echo "Generating SSL certificates..."
    cd "$PROJECT_ROOT"
    ./scripts/docker/generate-ssl-certs.sh
else
    echo "SSL certificates already exist"
fi

# Validate Nginx configuration files
echo "Validating Nginx configuration..."
if [ -f "$NGINX_CONFIG_DIR/nginx.conf" ] && [ -f "$NGINX_CONFIG_DIR/default.conf" ]; then
    echo "✅ Nginx configuration files found"
else
    echo "❌ Nginx configuration files missing"
    exit 1
fi

# Test Nginx configuration syntax (if nginx is available)
if command -v nginx >/dev/null 2>&1; then
    echo "Testing Nginx configuration syntax..."
    nginx -t -c "$NGINX_CONFIG_DIR/nginx.conf" -p "$PROJECT_ROOT" || {
        echo "❌ Nginx configuration syntax error"
        exit 1
    }
    echo "✅ Nginx configuration syntax is valid"
else
    echo "⚠️  Nginx not installed locally, skipping syntax check"
fi

# Create Nginx service health check script
cat > "$PROJECT_ROOT/scripts/docker/nginx-health-check.sh" << 'EOF'
#!/bin/bash
# Nginx health check script for Docker

# Test Nginx configuration
nginx -t >/dev/null 2>&1 || exit 1

# Test HTTP response
curl -f -s http://localhost:8080/health >/dev/null 2>&1 || exit 1

# Test if Nginx is serving requests
curl -f -s -I http://localhost >/dev/null 2>&1 || exit 1

echo "Nginx is healthy"
exit 0
EOF

chmod +x "$PROJECT_ROOT/scripts/docker/nginx-health-check.sh"

# Create Nginx management script
cat > "$PROJECT_ROOT/scripts/docker/manage-nginx.sh" << 'EOF'
#!/bin/bash
# Nginx management script for Docker Compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

case "${1:-help}" in
    start)
        echo "Starting Nginx service..."
        docker-compose up -d nginx
        ;;
    stop)
        echo "Stopping Nginx service..."
        docker-compose stop nginx
        ;;
    restart)
        echo "Restarting Nginx service..."
        docker-compose restart nginx
        ;;
    reload)
        echo "Reloading Nginx configuration..."
        docker-compose exec nginx nginx -s reload
        ;;
    test)
        echo "Testing Nginx configuration..."
        docker-compose exec nginx nginx -t
        ;;
    logs)
        echo "Showing Nginx logs..."
        docker-compose logs -f nginx
        ;;
    status)
        echo "Nginx service status:"
        docker-compose ps nginx
        echo ""
        echo "Nginx health check:"
        docker-compose exec nginx /scripts/nginx-health-check.sh || echo "Health check failed"
        ;;
    stats)
        echo "Nginx statistics:"
        curl -s http://localhost:8080/nginx_status || echo "Status endpoint not available"
        ;;
    ssl-info)
        echo "SSL certificate information:"
        openssl x509 -in ssl/certs/vedfolnir.crt -text -noout | grep -E "(Subject:|DNS:|IP Address:|Not Before|Not After)" || echo "Certificate not found"
        ;;
    help|*)
        echo "Nginx management script"
        echo ""
        echo "Usage: $0 {start|stop|restart|reload|test|logs|status|stats|ssl-info|help}"
        echo ""
        echo "Commands:"
        echo "  start     - Start Nginx service"
        echo "  stop      - Stop Nginx service"
        echo "  restart   - Restart Nginx service"
        echo "  reload    - Reload Nginx configuration"
        echo "  test      - Test Nginx configuration"
        echo "  logs      - Show Nginx logs"
        echo "  status    - Show Nginx service status"
        echo "  stats     - Show Nginx statistics"
        echo "  ssl-info  - Show SSL certificate information"
        echo "  help      - Show this help message"
        ;;
esac
EOF

chmod +x "$PROJECT_ROOT/scripts/docker/manage-nginx.sh"

# Create Nginx security configuration validation script
cat > "$PROJECT_ROOT/scripts/docker/validate-nginx-security.sh" << 'EOF'
#!/bin/bash
# Validate Nginx security configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Validating Nginx security configuration..."

# Test security headers
echo "Testing security headers..."
HEADERS=$(curl -s -I http://localhost/ || echo "")

if echo "$HEADERS" | grep -q "X-Content-Type-Options: nosniff"; then
    echo "✅ X-Content-Type-Options header present"
else
    echo "❌ X-Content-Type-Options header missing"
fi

if echo "$HEADERS" | grep -q "X-Frame-Options: DENY"; then
    echo "✅ X-Frame-Options header present"
else
    echo "❌ X-Frame-Options header missing"
fi

if echo "$HEADERS" | grep -q "X-XSS-Protection"; then
    echo "✅ X-XSS-Protection header present"
else
    echo "❌ X-XSS-Protection header missing"
fi

# Test SSL configuration (if HTTPS is available)
if curl -k -s -I https://localhost/ >/dev/null 2>&1; then
    echo "Testing SSL configuration..."
    
    SSL_HEADERS=$(curl -k -s -I https://localhost/ || echo "")
    
    if echo "$SSL_HEADERS" | grep -q "Strict-Transport-Security"; then
        echo "✅ HSTS header present"
    else
        echo "❌ HSTS header missing"
    fi
    
    # Test SSL protocols
    if openssl s_client -connect localhost:443 -tls1_2 </dev/null >/dev/null 2>&1; then
        echo "✅ TLS 1.2 supported"
    else
        echo "❌ TLS 1.2 not supported"
    fi
else
    echo "⚠️  HTTPS not available, skipping SSL tests"
fi

# Test rate limiting
echo "Testing rate limiting..."
for i in {1..10}; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/test 2>/dev/null || echo "000")
    if [ "$RESPONSE" = "429" ]; then
        echo "✅ Rate limiting is working (got 429 after $i requests)"
        break
    fi
    sleep 0.1
done

echo "Security validation complete"
EOF

chmod +x "$PROJECT_ROOT/scripts/docker/validate-nginx-security.sh"

echo ""
echo "✅ Nginx setup complete!"
echo ""
echo "Next steps:"
echo "1. Start the Nginx service: docker-compose up -d nginx"
echo "2. Test the configuration: ./scripts/docker/manage-nginx.sh test"
echo "3. Check service status: ./scripts/docker/manage-nginx.sh status"
echo "4. Validate security: ./scripts/docker/validate-nginx-security.sh"
echo ""
echo "Available management commands:"
echo "  ./scripts/docker/manage-nginx.sh {start|stop|restart|reload|test|logs|status|stats|ssl-info}"
echo ""
echo "SSL Certificate:"
echo "  Certificate: ssl/certs/vedfolnir.crt"
echo "  Private Key: ssl/keys/vedfolnir.key"
echo ""
echo "Access URLs:"
echo "  HTTP:  http://localhost"
echo "  HTTPS: https://localhost"
echo "  Status: http://localhost:8080/nginx_status"
echo "  Grafana: http://localhost:3000"