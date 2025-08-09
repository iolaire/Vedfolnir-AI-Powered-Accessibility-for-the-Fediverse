# Troubleshooting Guide - Web Caption Generation

## Overview
This guide provides solutions for common issues encountered with the web-based caption generation system.

## Quick Diagnostics

### System Health Check
```bash
# Check application status
curl -s http://localhost:5000/health | jq

# Check detailed system status
curl -s http://localhost:5000/health/detailed | jq

# Check database connectivity
python -c "
from database import DatabaseManager
from config import Config
try:
    db = DatabaseManager(Config())
    session = db.get_session()
    print('✓ Database connection successful')
    session.close()
except Exception as e:
    print(f'✗ Database error: {e}')
"
```

### Service Status
```bash
# Check running processes
ps aux | grep -E "(web_app|background_worker)" | grep -v grep

# Check system services
systemctl status vedfolnir
systemctl status vedfolnir-worker

# Check ports
netstat -tlnp | grep :5000
```

## Common Issues and Solutions

### 1. Caption Generation Not Starting

#### Symptoms
- "Start Generation" button doesn't respond
- Error: "User already has an active task"
- Tasks stuck in "Queued" status

#### Diagnosis
```bash
# Check for active tasks
python -c "
from web_caption_generation_service import WebCaptionGenerationService
from database import DatabaseManager
from config import Config
service = WebCaptionGenerationService(DatabaseManager(Config()))
stats = service.get_service_stats()
print(f'Queue stats: {stats[\"queue_stats\"]}')
print(f'Active sessions: {stats[\"active_progress_sessions\"]}')
"

# Check task queue
python -c "
from task_queue_manager import TaskQueueManager
from database import DatabaseManager
from config import Config
manager = TaskQueueManager(DatabaseManager(Config()))
print('Queue statistics:', manager.get_queue_stats())
"
```

#### Solutions

**Clear Stuck Tasks:**
```bash
# Cancel all active tasks for a user
python -c "
from task_queue_manager import TaskQueueManager
from database import DatabaseManager
from config import Config
manager = TaskQueueManager(DatabaseManager(Config()))
# Replace USER_ID with actual user ID
active_task = manager.get_user_active_task(USER_ID)
if active_task:
    manager.cancel_task(active_task.id, USER_ID)
    print(f'Cancelled task: {active_task.id}')
else:
    print('No active task found')
"
```

**Restart Background Worker:**
```bash
# If using systemd
sudo systemctl restart vedfolnir-worker

# If using supervisor
sudo supervisorctl restart background-worker

# If running manually
pkill -f background_worker.py
python background_worker.py &
```

**Clear Task Queue:**
```bash
# Emergency: Clear all queued tasks
python -c "
from database import DatabaseManager
from config import Config
from models import CaptionGenerationTask, TaskStatus
db = DatabaseManager(Config())
session = db.get_session()
queued_tasks = session.query(CaptionGenerationTask).filter_by(status=TaskStatus.QUEUED).all()
for task in queued_tasks:
    task.status = TaskStatus.CANCELLED
session.commit()
print(f'Cancelled {len(queued_tasks)} queued tasks')
session.close()
"
```

### 2. WebSocket Connection Issues

#### Symptoms
- Progress updates not showing
- "Connection lost" messages
- Real-time features not working

#### Diagnosis
```bash
# Test WebSocket connection
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" \
     http://localhost:5000/socket.io/

# Check WebSocket logs
grep "WebSocket" logs/webapp.log | tail -20

# Check for proxy issues
nginx -t
```

#### Solutions

**Fix Nginx WebSocket Configuration:**
```nginx
# Add to nginx configuration
location /socket.io/ {
    proxy_pass http://127.0.0.1:5000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
```

**Restart WebSocket Service:**
```bash
# Restart main application
sudo systemctl restart vedfolnir

# Or if using Docker
docker-compose restart vedfolnir
```

**Check Firewall:**
```bash
# Ensure WebSocket ports are open
sudo ufw status
sudo ufw allow 5000  # If needed for testing
```

### 3. Platform Connection Failures

#### Symptoms
- "Platform connection failed" errors
- Authentication errors during generation
- "Invalid access token" messages

#### Diagnosis
```bash
# Test platform connections
python -c "
from database import DatabaseManager
from config import Config
from models import PlatformConnection
db = DatabaseManager(Config())
session = db.get_session()
platforms = session.query(PlatformConnection).filter_by(is_active=True).all()
for platform in platforms:
    try:
        success, message = platform.test_connection()
        status = '✓' if success else '✗'
        print(f'{status} {platform.name}: {message}')
    except Exception as e:
        print(f'✗ {platform.name}: Error - {e}')
session.close()
"
```

#### Solutions

**Update Platform Credentials:**
1. Go to **Platform Management** in web interface
2. Click **"Edit"** on the failing platform
3. Update access token/credentials
4. Click **"Test Connection"** to verify
5. Save changes

**Re-authorize Platform Access:**
```bash
# For Mastodon platforms
# 1. Go to platform's Developer settings
# 2. Revoke old application access
# 3. Create new application
# 4. Update credentials in Vedfolnir

# For Pixelfed platforms
# 1. Go to Settings > Applications
# 2. Delete old application
# 3. Create new application
# 4. Update access token
```

**Check Platform Status:**
```bash
# Test platform API directly
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-mastodon-instance.com/api/v1/accounts/verify_credentials
```

### 4. AI Service (Ollama) Issues

#### Symptoms
- "AI service unavailable" errors
- Caption generation fails at processing step
- Long delays in caption generation

#### Diagnosis
```bash
# Check Ollama service
curl -s http://localhost:11434/api/version

# Check available models
curl -s http://localhost:11434/api/tags | jq

# Test model inference
curl -X POST http://localhost:11434/api/generate \
     -H "Content-Type: application/json" \
     -d '{"model": "llava:7b", "prompt": "Describe this image", "stream": false}'
```

#### Solutions

**Restart Ollama Service:**
```bash
# If using systemd
sudo systemctl restart ollama

# If using Docker
docker-compose restart ollama

# If running manually
pkill ollama
ollama serve &
```

**Reinstall Model:**
```bash
# Remove and reinstall model
ollama rm llava:7b
ollama pull llava:7b

# Verify model installation
ollama list
```

**Check Resource Usage:**
```bash
# Monitor Ollama resource usage
top -p $(pgrep ollama)

# Check available memory
free -h

# Check GPU usage (if applicable)
nvidia-smi
```

### 5. Database Issues

#### Symptoms
- "Database connection failed" errors
- Slow query performance
- Data corruption warnings

#### Diagnosis
```bash
# Check database file
ls -la storage/database/vedfolnir.db

# Check database integrity
sqlite3 storage/database/vedfolnir.db "PRAGMA integrity_check;"

# Check database size
du -sh storage/database/

# Analyze slow queries
sqlite3 storage/database/vedfolnir.db ".timer on" \
    "SELECT COUNT(*) FROM caption_generation_tasks;"
```

#### Solutions

**Database Maintenance:**
```bash
# Vacuum database
sqlite3 storage/database/vedfolnir.db "VACUUM;"

# Analyze and optimize
sqlite3 storage/database/vedfolnir.db "ANALYZE;"

# Reindex database
sqlite3 storage/database/vedfolnir.db "REINDEX;"
```

**Clean Old Data:**
```bash
# Clean up old completed tasks
python -c "
from task_queue_manager import TaskQueueManager
from database import DatabaseManager
from config import Config
manager = TaskQueueManager(DatabaseManager(Config()))
cleaned = manager.cleanup_completed_tasks(older_than_hours=168)  # 1 week
print(f'Cleaned up {cleaned} old tasks')
"
```

**Backup and Restore:**
```bash
# Create backup
cp storage/database/vedfolnir.db storage/database/vedfolnir.db.backup

# Restore from backup (if needed)
cp storage/database/vedfolnir.db.backup storage/database/vedfolnir.db
```

### 6. Performance Issues

#### Symptoms
- Slow web interface response
- High CPU/memory usage
- Tasks taking too long to complete

#### Diagnosis
```bash
# Monitor system resources
top -p $(pgrep -f "python.*web_app")
htop

# Check memory usage
ps aux --sort=-%mem | head -10

# Monitor disk I/O
iotop -p $(pgrep -f "python.*web_app")

# Check network connections
netstat -an | grep :5000
```

#### Solutions

**Optimize Configuration:**
```bash
# Reduce concurrent tasks
export MAX_CONCURRENT_TASKS=3

# Increase worker processes
export BACKGROUND_TASK_WORKERS=2

# Tune database connections
export DATABASE_POOL_SIZE=10
```

**Clear Caches:**
```bash
# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Clear logs (if too large)
truncate -s 0 logs/vedfolnir.log
truncate -s 0 logs/webapp.log
```

**Restart Services:**
```bash
# Restart all services
sudo systemctl restart vedfolnir
sudo systemctl restart vedfolnir-worker
sudo systemctl restart nginx
```

### 7. Authentication and Session Issues

#### Symptoms
- Users getting logged out frequently
- "Session expired" errors
- Login page redirects

#### Diagnosis
```bash
# Check session configuration
python -c "
import os
print('Session timeout:', os.getenv('SESSION_TIMEOUT', '3600'))
print('Flask secret key set:', bool(os.getenv('FLASK_SECRET_KEY')))
"

# Check active sessions
python -c "
from session_manager import SessionManager
from database import DatabaseManager
from config import Config
sm = SessionManager(DatabaseManager(Config()))
# This would require implementing session listing
print('Session manager initialized')
"
```

#### Solutions

**Fix Session Configuration:**
```bash
# Set proper session timeout
export SESSION_TIMEOUT=7200  # 2 hours

# Ensure Flask secret key is set
export FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

**Clear Sessions:**
```bash
# Clear all sessions (users will need to re-login)
python -c "
from database import DatabaseManager
from config import Config
from models import UserSession
db = DatabaseManager(Config())
session = db.get_session()
session.query(UserSession).delete()
session.commit()
print('All sessions cleared')
session.close()
"
```

## Error Code Reference

### Task Management Errors
- **ACTIVE_TASK_EXISTS**: Cancel existing task or wait for completion
- **TASK_NOT_FOUND**: Check task ID and user permissions
- **TASK_CANNOT_BE_CANCELLED**: Task is in final state (completed/failed)

### Platform Errors
- **PLATFORM_CONNECTION_FAILED**: Update platform credentials
- **PLATFORM_AUTH_FAILED**: Re-authorize platform access
- **PLATFORM_RATE_LIMITED**: Wait and retry later

### System Errors
- **SYSTEM_OVERLOADED**: Reduce concurrent tasks or scale up
- **DATABASE_ERROR**: Check database integrity and connections
- **AI_SERVICE_UNAVAILABLE**: Restart Ollama service

## Emergency Procedures

### System Recovery
```bash
#!/bin/bash
# Emergency system recovery script

echo "Starting emergency recovery..."

# Stop all services
sudo systemctl stop vedfolnir
sudo systemctl stop vedfolnir-worker

# Clear stuck tasks
python -c "
from database import DatabaseManager
from config import Config
from models import CaptionGenerationTask, TaskStatus
db = DatabaseManager(Config())
session = db.get_session()
stuck_tasks = session.query(CaptionGenerationTask).filter(
    CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
).all()
for task in stuck_tasks:
    task.status = TaskStatus.CANCELLED
session.commit()
print(f'Cancelled {len(stuck_tasks)} stuck tasks')
session.close()
"

# Restart services
sudo systemctl start vedfolnir
sudo systemctl start vedfolnir-worker

echo "Recovery complete"
```

### Data Recovery
```bash
#!/bin/bash
# Data recovery from backup

BACKUP_DATE=${1:-$(date -d "1 day ago" +%Y%m%d)}
BACKUP_FILE="backups/vedfolnir_${BACKUP_DATE}.db"

if [ -f "$BACKUP_FILE" ]; then
    echo "Restoring from backup: $BACKUP_FILE"
    sudo systemctl stop vedfolnir
    cp "$BACKUP_FILE" storage/database/vedfolnir.db
    sudo systemctl start vedfolnir
    echo "Restore complete"
else
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi
```

## Getting Help

### Log Collection
```bash
#!/bin/bash
# Collect logs for support

LOG_DIR="support_logs_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

# Application logs
cp logs/*.log "$LOG_DIR/"

# System logs
journalctl -u vedfolnir --since "1 hour ago" > "$LOG_DIR/systemd.log"

# System info
uname -a > "$LOG_DIR/system_info.txt"
df -h >> "$LOG_DIR/system_info.txt"
free -h >> "$LOG_DIR/system_info.txt"

# Configuration (sanitized)
env | grep -E "(FLASK|OLLAMA|MAX_|LOG_)" > "$LOG_DIR/config.txt"

tar -czf "${LOG_DIR}.tar.gz" "$LOG_DIR"
echo "Support logs collected: ${LOG_DIR}.tar.gz"
```

### Contact Information
- **GitHub Issues**: Create issue with logs and error details
- **Documentation**: Check README.md and docs/ directory
- **Community**: Join discussion forums or chat channels

### Before Contacting Support
1. **Check this troubleshooting guide**
2. **Review application logs**
3. **Test with minimal configuration**
4. **Document steps to reproduce issue**
5. **Collect system information and logs**