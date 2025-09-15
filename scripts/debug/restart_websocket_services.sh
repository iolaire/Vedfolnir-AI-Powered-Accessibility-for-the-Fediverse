#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Restart Services with WebSocket Support

set -e

echo "=== Restarting Vedfolnir Services with WebSocket Support ==="
echo

# Stop Gunicorn
echo "🛑 Stopping Gunicorn..."
if launchctl list | grep -q com.vedfolnir.gunicorn; then
    launchctl stop com.vedfolnir.gunicorn
    echo "✅ Gunicorn stopped"
else
    echo "ℹ️  Gunicorn was not running"
fi

# Wait a moment for cleanup
sleep 2

# Install eventlet if not already installed
echo "📦 Ensuring eventlet is installed..."
if ! python3 -c "import eventlet" 2>/dev/null; then
    echo "Installing eventlet..."
    pip install eventlet
    echo "✅ eventlet installed"
else
    echo "✅ eventlet already installed"
fi

# Start Gunicorn with new configuration
echo "🚀 Starting Gunicorn with WebSocket support..."
launchctl start com.vedfolnir.gunicorn
echo "✅ Gunicorn started with eventlet worker"

# Wait for service to start
echo "⏳ Waiting for services to start..."
sleep 5

# Test Gunicorn
echo "🔍 Testing Gunicorn..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 | grep -q "200\|302"; then
    echo "✅ Gunicorn is responding"
else
    echo "❌ Gunicorn is not responding"
    echo "Check logs: tail -f logs/error.log"
fi

# Test WebSocket endpoint
echo "🔍 Testing WebSocket endpoint..."
SOCKET_RESPONSE=$(curl -s -w "%{http_code}" http://127.0.0.1:8000/socket.io/?EIO=4&transport=polling)
if echo "$SOCKET_RESPONSE" | grep -q "200"; then
    echo "✅ WebSocket endpoint is responding"
else
    echo "❌ WebSocket endpoint failed"
    echo "Response: $SOCKET_RESPONSE"
fi

# Test through Nginx
echo "🔍 Testing through Nginx..."
if curl -s -o /dev/null -w "%{http_code}" http://38.23.47.127 | grep -q "200\|302"; then
    echo "✅ Nginx proxy is working"
else
    echo "❌ Nginx proxy failed"
    echo "Check Nginx logs: tail -f /opt/homebrew/var/log/nginx/error.log"
fi

echo
echo "=== Service Restart Complete ==="
echo
echo "Next steps:"
echo "1. Test the application in your browser"
echo "2. Check browser console for WebSocket connection success"
echo "3. Monitor logs: tail -f logs/webapp.log"
echo "4. If issues persist, check: tail -f logs/error.log"
echo
echo "WebSocket test URL: https://vedfolnir.org"
echo "Direct test URL: http://127.0.0.1:8000"