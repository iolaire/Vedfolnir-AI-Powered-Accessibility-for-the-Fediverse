#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Emergency CSS Security Enhancement Rollback Script
# This script provides quick rollback capability for CSS security deployment issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== EMERGENCY CSS SECURITY ROLLBACK ===${NC}"
echo "This script will rollback CSS security enhancements to the previous state."
echo ""

# Find latest backup
LATEST_BACKUP=$(ls -1t backups/css-security-* 2>/dev/null | head -1)

if [[ -z "$LATEST_BACKUP" ]]; then
    echo -e "${RED}❌ No CSS security backup found!${NC}"
    echo "Available backups:"
    ls -la backups/ 2>/dev/null || echo "No backups directory found"
    exit 1
fi

echo -e "Latest backup found: ${GREEN}$LATEST_BACKUP${NC}"
echo ""

# Confirm rollback
read -p "Are you sure you want to rollback? (yes/no): " confirm
if [[ "$confirm" != "yes" ]]; then
    echo "Rollback cancelled"
    exit 0
fi

echo -e "${YELLOW}Starting emergency rollback...${NC}"

# Stop application
echo "Stopping application..."
pkill -f "python web_app.py" || true
sleep 2

# Restore files
echo "Restoring templates..."
cp -r "$LATEST_BACKUP/templates" . || {
    echo -e "${RED}❌ Failed to restore templates${NC}"
    exit 1
}

echo "Restoring admin templates..."
cp -r "$LATEST_BACKUP/admin_templates" admin/templates || {
    echo -e "${RED}❌ Failed to restore admin templates${NC}"
    exit 1
}

echo "Restoring CSS files..."
cp -r "$LATEST_BACKUP/static_css" static/css || {
    echo -e "${RED}❌ Failed to restore static CSS${NC}"
    exit 1
}

cp -r "$LATEST_BACKUP/admin_static_css" admin/static/css || {
    echo -e "${RED}❌ Failed to restore admin CSS${NC}"
    exit 1
}

echo "Restoring configuration files..."
cp "$LATEST_BACKUP/config.py" . || {
    echo -e "${RED}❌ Failed to restore config.py${NC}"
    exit 1
}

cp "$LATEST_BACKUP/web_app.py" . || {
    echo -e "${RED}❌ Failed to restore web_app.py${NC}"
    exit 1
}

# Restart application
echo "Restarting application..."
python web_app.py & sleep 10

# Verify rollback
echo "Verifying rollback..."
status=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/ || echo "000")

if [[ "$status" == "200" ]]; then
    echo -e "${GREEN}✅ Emergency rollback completed successfully${NC}"
    echo "Application is responding normally"
    
    # Log rollback
    echo "$(date): Emergency CSS security rollback completed" >> logs/rollback.log
    echo "Backup used: $LATEST_BACKUP" >> logs/rollback.log
    
    echo ""
    echo "Next steps:"
    echo "1. Investigate the cause of the rollback"
    echo "2. Fix any issues with the CSS security deployment"
    echo "3. Test the fixes thoroughly before redeploying"
    echo "4. Update deployment procedures if needed"
    
else
    echo -e "${RED}❌ Rollback failed - application not responding (HTTP $status)${NC}"
    echo "Manual intervention required"
    exit 1
fi