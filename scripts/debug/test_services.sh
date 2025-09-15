#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Test Vedfolnir Services

echo "=== Vedfolnir Service Status Check ==="
echo

# Test Gunicorn on port 8000
echo "🔍 Testing Gunicorn (port 8000)..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 | grep -q "200\|302"; then
    echo "✅ Gunicorn is responding on port 8000"
else
    echo "❌ Gunicorn is not responding on port 8000"
    echo "   Check: launchctl list | grep vedfolnir"
fi

# Test Nginx
echo
echo "🔍 Testing Nginx..."
if brew services list | grep nginx | grep -q started; then
    echo "✅ Nginx service is running"
else
    echo "❌ Nginx service is not running"
    echo "   Start with: sudo brew services start nginx"
fi

# Test Nginx configuration
echo
echo "🔍 Testing Nginx configuration..."
if nginx -t 2>/dev/null; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration has errors"
    nginx -t
fi

# Test local HTTP access
echo
echo "🔍 Testing local HTTP access..."
if curl -s -o /dev/null -w "%{http_code}" http://38.23.47.127 | grep -q "200\|302"; then
    echo "✅ Local HTTP access is working"
else
    echo "❌ Local HTTP access failed"
    echo "   Check Nginx logs: tail -f /opt/homebrew/var/log/nginx/error.log"
fi

# Test CSP headers
echo
echo "🔍 Testing CSP headers..."
CSP_HEADER=$(curl -s -I http://127.0.0.1:8000 | grep -i "content-security-policy" | head -1)
if [ -n "$CSP_HEADER" ]; then
    echo "✅ CSP header is present"
    echo "   ${CSP_HEADER:0:100}..."
else
    echo "❌ No CSP header found"
    echo "   Check Flask security middleware initialization"
fi

# Check for recent CSP violations
echo
echo "🔍 Checking recent CSP violations..."
RECENT_VIOLATIONS=$(tail -n 100 logs/webapp.log 2>/dev/null | grep -c "CSP violation detected" || echo "0")
if [ "$RECENT_VIOLATIONS" -eq 0 ]; then
    echo "✅ No recent CSP violations found"
else
    echo "⚠️  Found $RECENT_VIOLATIONS recent CSP violations"
    echo "   Run: python3 scripts/debug/debug_csp_violations.py"
fi

echo
echo "=== Service Status Summary ==="
echo "Run this script after making changes to verify everything is working."
echo
echo "Useful commands:"
echo "  Restart Gunicorn: launchctl restart com.vedfolnir.gunicorn"
echo "  Restart Nginx: sudo brew services restart nginx"
echo "  View logs: tail -f logs/webapp.log"
echo "  Test CSP: python3 scripts/debug/debug_csp_violations.py"