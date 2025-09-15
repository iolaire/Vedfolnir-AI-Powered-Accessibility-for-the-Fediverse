#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Deploy Nginx Configuration for Vedfolnir

set -e  # Exit on any error

echo "=== Vedfolnir Nginx Configuration Deployment ==="
echo

# Configuration paths
LOCAL_CONFIG="/Users/administrator/app/Vedfolnir-AI-Powered-Accessibility-for-the-Fediverse/config/vedfolnir.org.conf"
NGINX_CONFIG="/opt/homebrew/etc/nginx/servers/vedfolnir.org.conf"
BACKUP_CONFIG="config/backup/vedfolnir.org.conf.backup.$(date +%Y%m%d_%H%M%S)"

# Check if local config exists
if [ ! -f "$LOCAL_CONFIG" ]; then
    echo "❌ Error: Local config file not found: $LOCAL_CONFIG"
    exit 1
fi

echo "📁 Local config: $LOCAL_CONFIG"
echo "📁 Nginx config: $NGINX_CONFIG"
echo "📁 Backup will be: $BACKUP_CONFIG"
echo

# Test local configuration syntax
echo "🔍 Testing local configuration syntax..."
if nginx -t -c /dev/stdin < "$LOCAL_CONFIG" 2>/dev/null; then
    echo "✅ Local configuration syntax is valid"
else
    echo "❌ Local configuration has syntax errors"
    echo "Please fix the configuration before deploying"
    exit 1
fi

# Backup existing configuration
if [ -f "$NGINX_CONFIG" ]; then
    echo "💾 Backing up existing configuration..."
    cp "$NGINX_CONFIG" "$BACKUP_CONFIG"
    echo "✅ Backup created: $BACKUP_CONFIG"
else
    echo "ℹ️  No existing configuration found"
fi

# Copy new configuration
echo "📋 Copying new configuration..."
cp "$LOCAL_CONFIG" "$NGINX_CONFIG"
echo "✅ Configuration copied"

# Test new configuration
echo "🔍 Testing new Nginx configuration..."
if nginx -t; then
    echo "✅ New configuration is valid"
else
    echo "❌ New configuration has errors"
    echo "🔄 Restoring backup..."
    if [ -f "$BACKUP_CONFIG" ]; then
        cp "$BACKUP_CONFIG" "$NGINX_CONFIG"
        echo "✅ Backup restored"
    fi
    exit 1
fi

# Reload Nginx
echo "🔄 Reloading Nginx..."
if sudo brew services restart nginx; then
    echo "✅ Nginx reloaded successfully"
else
    echo "❌ Failed to reload Nginx"
    echo "🔄 Restoring backup..."
    if [ -f "$BACKUP_CONFIG" ]; then
        cp "$BACKUP_CONFIG" "$NGINX_CONFIG"
        sudo brew services restart nginx
        echo "✅ Backup restored and Nginx restarted"
    fi
    exit 1
fi

echo
echo "=== Deployment Summary ==="
echo "✅ Configuration deployed successfully"
echo "✅ Nginx reloaded"
echo "📁 Backup available at: $BACKUP_CONFIG"
echo
echo "Next steps:"
echo "1. Restart Gunicorn: launchctl restart com.vedfolnir.gunicorn"
echo "2. Test the application: curl -I https://vedfolnir.org"
echo "3. Monitor logs: tail -f logs/webapp.log"
echo "4. Check for CSP violations: python3 scripts/debug/debug_csp_violations.py"
echo
echo "🎉 Deployment complete!"