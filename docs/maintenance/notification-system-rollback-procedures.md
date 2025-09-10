# Notification System Rollback Procedures

## Overview

This document provides detailed rollback procedures for the notification system migration, including automated rollback scripts, manual rollback steps, and recovery validation procedures. These procedures ensure safe restoration to the legacy Flask flash message system when the unified notification system encounters critical issues.

## Rollback Decision Matrix

### When to Execute Rollback

#### Automatic Rollback Triggers
- **Critical System Failure**: Complete notification system failure lasting > 30 minutes
- **Security Vulnerability**: Critical security issue discovered in unified system
- **Data Corruption**: Database corruption affecting notification storage
- **Performance Degradation**: System performance below acceptable thresholds for > 1 hour

#### Manual Rollback Triggers
- **Administrator Decision**: Senior administrator determines rollback necessary
- **User Impact**: Significant user experience degradation
- **Recovery Failure**: Automated recovery attempts fail repeatedly
- **Maintenance Window**: Planned rollback during maintenance window

### Rollback Authorization

#### Authorization Levels
1. **Emergency Rollback**: Any administrator during critical failures
2. **Planned Rollback**: Senior administrator approval required
3. **Security Rollback**: Security administrator approval required
4. **Maintenance Rollback**: Change management approval required

## Pre-Rollback Procedures

### 1. Emergency Assessment
```bash
# Run comprehensive system assessment
python scripts/enhanced_notification_emergency_cli.py health-check

# Document current system state
python scripts/enhanced_notification_emergency_cli.py report

# Check system resources
df -h
free -m
ps aux | grep -E "(python|mysql|redis)"
```

### 2. Stakeholder Notification
```bash
# Notify administrators
python scripts/enhanced_notification_emergency_cli.py send-notification \
  --title "ROLLBACK INITIATED" \
  --message "Notification system rollback procedures have been initiated" \
  --target admins \
  --priority critical

# Update status page
curl -X POST http://127.0.0.1:5000/api/status \
  -H "Content-Type: application/json" \
  -d '{"status": "maintenance", "message": "System rollback in progress"}'
```

### 3. Create Emergency Backup
```bash
# Create comprehensive backup before rollback
python scripts/enhanced_notification_emergency_cli.py backup

# Verify backup creation
ls -la storage/emergency_backups/

# Test backup integrity
python scripts/verify_backup_integrity.py --latest
```

### 4. Document Rollback Reason
```bash
# Create rollback documentation
cat > storage/emergency_backups/rollback_reason_$(date +%Y%m%d_%H%M%S).md << EOF
# Rollback Reason Documentation

## Rollback Details
- **Date/Time**: $(date)
- **Initiated By**: $(whoami)
- **Reason**: [Describe the reason for rollback]
- **System Status**: [Current system status]
- **Impact**: [Description of user/system impact]

## Pre-Rollback System State
- **Notification System**: [Status]
- **WebSocket Connections**: [Status]
- **Database**: [Status]
- **User Sessions**: [Count and status]

## Expected Rollback Duration
- **Estimated Time**: [Duration estimate]
- **Critical Path**: [Key rollback steps]
- **Risk Assessment**: [Potential risks]
EOF
```

## Automated Rollback Procedures

### 1. Execute Automated Rollback
```bash
# Execute rollback with confirmation
python scripts/enhanced_notification_emergency_cli.py rollback --confirm

# Monitor rollback progress
tail -f /var/log/notification_rollback.log

# Alternative: Execute rollback script directly
bash scripts/rollback_notification_system.sh
```

### 2. Rollback Script Components

#### The automated rollback script performs:
1. **Service Shutdown**: Graceful shutdown of notification services
2. **Component Removal**: Removal of unified notification components
3. **Legacy Restoration**: Restoration of Flask flash message system
4. **Database Rollback**: Removal of unified notification tables
5. **Configuration Update**: Restoration of legacy configuration
6. **Service Restart**: Restart with legacy system
7. **Validation**: Verification of rollback success

### 3. Monitor Rollback Progress
```bash
# Monitor rollback log
tail -f /var/log/notification_rollback.log

# Check service status
systemctl status vedfolnir
ps aux | grep "python.*web_app.py"

# Monitor system resources
watch -n 5 'free -m && df -h'
```

## Manual Rollback Procedures

### 1. Stop Notification Services
```bash
# Find and stop web application
WEB_PID=$(pgrep -f "python.*web_app.py")
if [ -n "$WEB_PID" ]; then
    echo "Stopping web application (PID: $WEB_PID)"
    kill $WEB_PID
    sleep 10
    
    # Force kill if still running
    if kill -0 $WEB_PID 2>/dev/null; then
        echo "Force killing web application"
        kill -9 $WEB_PID
    fi
fi

# Stop any WebSocket services
pkill -f "websocket"

# Stop Redis if dedicated instance
sudo systemctl stop redis-server
```

### 2. Remove Unified Notification Components
```bash
# Navigate to project root
cd /path/to/vedfolnir

# Remove Python components
rm -f unified_notification_manager.py
rm -f notification_emergency_recovery.py
rm -f notification_message_router.py
rm -f notification_persistence_manager.py
rm -f page_notification_integrator.py
rm -f notification_ui_renderer.py

# Remove WebSocket notification files
rm -f websocket_notification_*.py
rm -f notification_websocket_*.py

# Remove JavaScript components
rm -f static/js/unified-notifications.js
rm -f static/js/notification-ui-renderer.js
rm -f static/js/websocket-notification-client.js
rm -f admin/static/js/admin-notifications.js
rm -f admin/static/js/unified-admin-notifications.js

# Remove CSS components
rm -f static/css/unified-notifications.css
rm -f admin/static/css/unified-notifications.css
```

### 3. Restore Legacy Components
```bash
# Restore from git if available
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Restoring from git history..."
    
    # Restore legacy templates
    git checkout HEAD~1 -- templates/base.html
    git checkout HEAD~1 -- templates/admin/base.html
    git checkout HEAD~1 -- templates/user/dashboard.html
    
    # Restore legacy JavaScript
    git checkout HEAD~1 -- static/js/notifications.js
    git checkout HEAD~1 -- admin/static/js/notifications.js
    
    # Restore legacy CSS
    git checkout HEAD~1 -- static/css/notifications.css
    git checkout HEAD~1 -- admin/static/css/notifications.css
    
    # Restore route handlers
    git checkout HEAD~1 -- routes/user_routes.py
    git checkout HEAD~1 -- routes/admin_routes.py
else
    echo "Creating minimal legacy notification system..."
    
    # Create basic flash message template
    cat > templates/flash_messages.html << 'EOF'
<!-- Legacy Flash Messages -->
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    <div class="flash-messages">
      {% for category, message in messages %}
        <div class="alert alert-{{ 'danger' if category == 'error' else category }}">
          {{ message }}
          <button type="button" class="close" data-dismiss="alert">&times;</button>
        </div>
      {% endfor %}
    </div>
  {% endif %}
{% endwith %}
EOF
fi
```

### 4. Rollback Database Schema
```bash
# Connect to MySQL and remove unified notification tables
mysql -u vedfolnir_user -p vedfolnir << 'EOF'
-- Remove unified notification tables
DROP TABLE IF EXISTS notification_storage;
DROP TABLE IF EXISTS notification_subscriptions;
DROP TABLE IF EXISTS notification_preferences;
DROP TABLE IF EXISTS notification_delivery_log;
DROP TABLE IF EXISTS notification_emergency_events;

-- Verify tables removed
SHOW TABLES LIKE 'notification_%';
EOF
```

### 5. Update Configuration
```bash
# Remove unified notification configuration from web_app.py
cp web_app.py web_app.py.rollback_backup

# Remove unified notification imports
sed -i '/unified_notification/d' web_app.py
sed -i '/UnifiedNotification/d' web_app.py
sed -i '/notification_emergency_recovery/d' web_app.py
sed -i '/NotificationEmergencyRecovery/d' web_app.py
sed -i '/websocket_notification/d' web_app.py

# Restore environment configuration if backup exists
if [ -f ".env.backup" ]; then
    echo "Restoring environment configuration..."
    cp .env.backup .env
fi

# Remove unified notification environment variables
sed -i '/UNIFIED_NOTIFICATION/d' .env
sed -i '/WEBSOCKET_NOTIFICATION/d' .env
```

### 6. Start Legacy System
```bash
# Start Redis if needed
sudo systemctl start redis-server

# Start web application
python web_app.py &
WEB_PID=$!

# Wait for startup
sleep 15

# Verify startup
if kill -0 $WEB_PID 2>/dev/null; then
    echo "✅ Legacy system started successfully (PID: $WEB_PID)"
else
    echo "❌ Failed to start legacy system"
    exit 1
fi
```

## Rollback Validation Procedures

### 1. System Functionality Validation
```bash
# Test web application accessibility
curl -I http://127.0.0.1:5000/
# Expected: HTTP/1.1 200 OK

# Test login functionality
curl -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=test_password" \
  -c cookies.txt

# Test admin dashboard
curl -b cookies.txt http://127.0.0.1:5000/admin/
# Expected: HTTP/1.1 200 OK

# Test user dashboard
curl -b cookies.txt http://127.0.0.1:5000/
# Expected: HTTP/1.1 200 OK
```

### 2. Legacy Notification System Validation
```bash
# Test Flask flash message functionality
python << 'EOF'
import requests
import re

# Create session
session = requests.Session()

# Get login page and CSRF token
login_page = session.get('http://127.0.0.1:5000/login')
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
csrf_token = csrf_match.group(1) if csrf_match else ''

# Login
login_data = {
    'username_or_email': 'admin',
    'password': 'test_password',
    'csrf_token': csrf_token
}
response = session.post('http://127.0.0.1:5000/login', data=login_data)

# Test flash message (this would be in a real route)
print("✅ Flash message system available" if response.status_code in [200, 302] else "❌ Flash message system failed")
EOF
```

### 3. Database Integrity Validation
```bash
# Check database connectivity
python << 'EOF'
from app.core.database.core.database_manager import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)

try:
    with db_manager.get_session() as session:
        session.execute("SELECT 1")
        print("✅ Database connectivity OK")
        
        # Check user table
        result = session.execute("SELECT COUNT(*) FROM users")
        user_count = result.scalar()
        print(f"✅ User table accessible ({user_count} users)")
        
        # Verify no unified notification tables exist
        result = session.execute("SHOW TABLES LIKE 'notification_%'")
        notif_tables = result.fetchall()
        if not notif_tables:
            print("✅ Unified notification tables removed")
        else:
            print(f"⚠️  Warning: {len(notif_tables)} notification tables still exist")
            
except Exception as e:
    print(f"❌ Database validation failed: {e}")
EOF
```

### 4. Performance Validation
```bash
# Check system performance
python << 'EOF'
import time
import requests

# Test response times
start_time = time.time()
response = requests.get('http://127.0.0.1:5000/')
response_time = (time.time() - start_time) * 1000

if response.status_code == 200:
    print(f"✅ Web application responding ({response_time:.2f}ms)")
    if response_time < 1000:
        print("✅ Response time acceptable")
    else:
        print("⚠️  Response time high")
else:
    print(f"❌ Web application not responding (status: {response.status_code})")
EOF

# Check system resources
echo "System Resource Usage:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
echo "Disk: $(df / | tail -1 | awk '{print $5}')"
```

### 5. User Experience Validation
```bash
# Test critical user workflows
python << 'EOF'
import requests
import re

session = requests.Session()

# Test user registration/login flow
try:
    # Get login page
    login_response = session.get('http://127.0.0.1:5000/login')
    if login_response.status_code == 200:
        print("✅ Login page accessible")
    
    # Get dashboard
    dashboard_response = session.get('http://127.0.0.1:5000/')
    if dashboard_response.status_code in [200, 302]:
        print("✅ Dashboard accessible")
    
    # Test admin pages
    admin_response = session.get('http://127.0.0.1:5000/admin/')
    if admin_response.status_code in [200, 302]:
        print("✅ Admin pages accessible")
    
    print("✅ All critical pages accessible")
    
except Exception as e:
    print(f"❌ User experience validation failed: {e}")
EOF
```

## Post-Rollback Procedures

### 1. System Monitoring
```bash
# Monitor system for 24 hours after rollback
# Set up monitoring script
cat > monitor_post_rollback.sh << 'EOF'
#!/bin/bash
LOG_FILE="/var/log/post_rollback_monitoring.log"

while true; do
    echo "$(date): Monitoring system status..." >> $LOG_FILE
    
    # Check web application
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/ | grep -q "200"; then
        echo "$(date): Web application OK" >> $LOG_FILE
    else
        echo "$(date): ❌ Web application issue detected" >> $LOG_FILE
    fi
    
    # Check system resources
    CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    MEM=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
    echo "$(date): CPU: ${CPU}%, Memory: ${MEM}%" >> $LOG_FILE
    
    sleep 300  # Check every 5 minutes
done
EOF

chmod +x monitor_post_rollback.sh
nohup ./monitor_post_rollback.sh &
```

### 2. User Communication
```bash
# Notify users of rollback completion
python << 'EOF'
from flask import Flask, flash
import smtplib
from email.mime.text import MimeText

# Send notification to administrators
def notify_rollback_completion():
    subject = "Notification System Rollback Completed"
    message = """
    The notification system rollback has been completed successfully.
    
    System Status:
    - Legacy Flask flash message system restored
    - All unified notification components removed
    - Database schema rolled back
    - System performance validated
    
    Please monitor the system closely for the next 24 hours.
    """
    
    print("Rollback completion notification sent")

notify_rollback_completion()
EOF
```

### 3. Documentation Update
```bash
# Generate rollback completion report
python scripts/enhanced_notification_emergency_cli.py report > rollback_completion_report.md

# Update system documentation
cat >> docs/system_status.md << EOF

## Rollback Event - $(date)
- **Event**: Notification system rollback executed
- **Reason**: [Rollback reason]
- **Duration**: [Rollback duration]
- **Status**: Completed successfully
- **Current System**: Legacy Flask flash messages
- **Next Review**: $(date -d "+1 week")

EOF
```

### 4. Lessons Learned Documentation
```bash
# Create lessons learned document
cat > docs/rollback_lessons_learned_$(date +%Y%m%d).md << 'EOF'
# Rollback Lessons Learned

## Event Summary
- **Date**: [Date]
- **Duration**: [Duration]
- **Reason**: [Reason for rollback]
- **Impact**: [User/system impact]

## What Went Well
- [List successful aspects]

## What Could Be Improved
- [List areas for improvement]

## Action Items
- [ ] [Improvement action 1]
- [ ] [Improvement action 2]
- [ ] [Improvement action 3]

## Process Updates
- [List any process updates needed]

## Technical Improvements
- [List technical improvements needed]
EOF
```

## Emergency Rollback Scenarios

### Scenario 1: Complete System Failure
```bash
# Immediate response for complete system failure
echo "🚨 COMPLETE SYSTEM FAILURE DETECTED"

# 1. Activate emergency mode
python scripts/enhanced_notification_emergency_cli.py backup
python scripts/enhanced_notification_emergency_cli.py rollback --confirm

# 2. Verify rollback
curl -I http://127.0.0.1:5000/

# 3. Notify stakeholders
echo "System rollback completed due to complete failure"
```

### Scenario 2: Security Vulnerability
```bash
# Response for security vulnerability
echo "🔒 SECURITY VULNERABILITY DETECTED"

# 1. Immediate isolation
iptables -A INPUT -p tcp --dport 5000 -j DROP

# 2. Emergency rollback
python scripts/enhanced_notification_emergency_cli.py rollback --confirm

# 3. Security validation
python scripts/security_validation.py

# 4. Restore access after validation
iptables -D INPUT -p tcp --dport 5000 -j DROP
```

### Scenario 3: Performance Degradation
```bash
# Response for performance issues
echo "📉 PERFORMANCE DEGRADATION DETECTED"

# 1. Performance assessment
python scripts/performance_assessment.py

# 2. Attempt optimization first
python scripts/optimize_system.py

# 3. Rollback if optimization fails
if [ $? -ne 0 ]; then
    python scripts/enhanced_notification_emergency_cli.py rollback --confirm
fi
```

## Rollback Testing and Validation

### Regular Rollback Testing
```bash
# Monthly rollback test (non-destructive)
python scripts/enhanced_notification_emergency_cli.py rollback --dry-run

# Quarterly full rollback test (test environment)
# 1. Create test environment snapshot
# 2. Execute full rollback
# 3. Validate all functionality
# 4. Document results
# 5. Restore from snapshot
```

### Rollback Automation Testing
```bash
# Test rollback script functionality
bash scripts/test_rollback_procedures.sh

# Validate rollback timing
time bash scripts/rollback_notification_system.sh --test-mode

# Test rollback under load
# 1. Generate system load
# 2. Execute rollback
# 3. Measure impact
# 4. Validate recovery time
```

## Continuous Improvement

### Rollback Metrics
- **Rollback Execution Time**: Target < 10 minutes
- **System Recovery Time**: Target < 5 minutes
- **Data Loss**: Target = 0
- **User Impact Duration**: Target < 15 minutes

### Regular Reviews
- **Monthly**: Rollback procedure review
- **Quarterly**: Full rollback testing
- **Annually**: Comprehensive procedure update
- **Post-incident**: Immediate procedure review and update

---

**Document Version**: 1.0  
**Last Updated**: August 30, 2025  
**Next Review**: September 30, 2025  
**Owner**: System Administration Team  
**Approved By**: Senior Administrator