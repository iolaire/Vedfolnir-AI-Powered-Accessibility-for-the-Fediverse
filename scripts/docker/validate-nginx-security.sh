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
