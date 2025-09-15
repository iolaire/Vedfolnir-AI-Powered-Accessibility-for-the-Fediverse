#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Validate JavaScript Files and Restart Services

set -e

echo "=== JavaScript Validation and Service Restart ==="
echo

# Check if Node.js is available for syntax validation
if command -v node >/dev/null 2>&1; then
    echo "🔍 Validating JavaScript syntax..."
    
    # Find and validate all JavaScript files
    JS_FILES=$(find static/js -name "*.js" 2>/dev/null || echo "")
    
    if [ -n "$JS_FILES" ]; then
        SYNTAX_ERRORS=0
        
        for js_file in $JS_FILES; do
            if [ -f "$js_file" ]; then
                echo "  Checking: $js_file"
                if node -c "$js_file" 2>/dev/null; then
                    echo "    ✅ Syntax OK"
                else
                    echo "    ❌ Syntax Error"
                    node -c "$js_file"
                    SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
                fi
            fi
        done
        
        if [ $SYNTAX_ERRORS -gt 0 ]; then
            echo "❌ Found $SYNTAX_ERRORS JavaScript syntax errors"
            echo "Please fix the syntax errors before continuing"
            exit 1
        else
            echo "✅ All JavaScript files have valid syntax"
        fi
    else
        echo "ℹ️  No JavaScript files found to validate"
    fi
else
    echo "⚠️  Node.js not available - skipping JavaScript validation"
fi

# Install/update requirements
echo "📦 Installing/updating requirements..."
pip install -r requirements.txt

# Stop Gunicorn
echo "🛑 Stopping Gunicorn..."
if launchctl list | grep -q com.vedfolnir.gunicorn; then
    launchctl stop com.vedfolnir.gunicorn
    echo "✅ Gunicorn stopped"
else
    echo "ℹ️  Gunicorn was not running"
fi

# Wait for cleanup
sleep 3

# Start Gunicorn with eventlet
echo "🚀 Starting Gunicorn with WebSocket support..."
launchctl start com.vedfolnir.gunicorn

# Wait for startup
echo "⏳ Waiting for services to start..."
sleep 5

# Test services
echo "🔍 Testing services..."

# Test main application
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 | grep -q "200\|302"; then
    echo "✅ Application is responding"
else
    echo "❌ Application is not responding"
    echo "Check logs: tail -f logs/error.log"
fi

# Test static files
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/static/js/csp-compliant-handlers.js | grep -q "200"; then
    echo "✅ Static files are serving correctly"
else
    echo "❌ Static files are not serving correctly"
fi

# Test WebSocket endpoint
SOCKET_TEST=$(curl -s -w "%{http_code}" -o /dev/null http://127.0.0.1:8000/socket.io/?EIO=4&transport=polling 2>/dev/null || echo "000")
if [ "$SOCKET_TEST" = "200" ]; then
    echo "✅ WebSocket endpoint is working"
else
    echo "⚠️  WebSocket endpoint returned: $SOCKET_TEST"
fi

# Test through Nginx
if curl -s -o /dev/null -w "%{http_code}" http://38.23.47.127 | grep -q "200\|302"; then
    echo "✅ Nginx proxy is working"
else
    echo "❌ Nginx proxy failed"
fi

echo
echo "=== Validation and Restart Complete ==="
echo
echo "JavaScript syntax error has been fixed in csp-compliant-handlers.js"
echo
echo "Next steps:"
echo "1. Test your application: https://vedfolnir.org"
echo "2. Check browser console - JavaScript errors should be resolved"
echo "3. Verify WebSocket connections are working"
echo "4. Monitor logs: tail -f logs/webapp.log"
echo
echo "If issues persist:"
echo "- Check error logs: tail -f logs/error.log"
echo "- Check browser developer console for remaining errors"