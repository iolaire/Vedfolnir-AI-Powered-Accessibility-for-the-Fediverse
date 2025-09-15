#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Update Requirements and Restart Services

set -e

echo "=== Updating Requirements and Restarting Services ==="
echo

# Navigate to project directory
cd /Users/administrator/app/Vedfolnir-AI-Powered-Accessibility-for-the-Fediverse

# Set up environment
export PATH="/opt/homebrew/bin:$PATH"

# Initialize pyenv
if command -v pyenv 1>/dev/null 2>&1; then
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
pyenv activate gunicorn-host

# Install updated requirements
echo "📦 Installing updated requirements (including eventlet)..."
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

# Start Gunicorn
echo "🚀 Starting Gunicorn with WebSocket support..."
launchctl start com.vedfolnir.gunicorn

# Wait for startup
echo "⏳ Waiting for services to start..."
sleep 5

# Test services
echo "🔍 Testing services..."

# Test Gunicorn
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 | grep -q "200\|302"; then
    echo "✅ Gunicorn is responding"
else
    echo "❌ Gunicorn is not responding"
fi

# Test WebSocket endpoint
SOCKET_TEST=$(curl -s -w "%{http_code}" -o /dev/null http://127.0.0.1:8000/socket.io/?EIO=4&transport=polling)
if [ "$SOCKET_TEST" = "200" ]; then
    echo "✅ WebSocket endpoint is working"
else
    echo "⚠️  WebSocket endpoint returned: $SOCKET_TEST"
fi

echo
echo "=== Update Complete ==="
echo
echo "Next steps:"
echo "1. Test your application: https://vedfolnir.org"
echo "2. Check browser console for WebSocket connections"
echo "3. Monitor logs: tail -f logs/webapp.log"
echo
echo "If WebSocket issues persist:"
echo "- Check logs: tail -f logs/error.log"
echo "- Verify eventlet: python3 -c 'import eventlet; print(eventlet.__version__)'"