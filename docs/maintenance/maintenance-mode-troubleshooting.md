# Enhanced Maintenance Mode - Troubleshooting Guide

## Overview

This troubleshooting guide provides comprehensive solutions for common issues encountered with the Enhanced Maintenance Mode system. It includes diagnostic procedures, common problems and solutions, and escalation procedures for complex issues.

## Quick Diagnostic Checklist

Before diving into specific issues, run through this quick diagnostic checklist:

- [ ] **System Status**: Check overall system health and status
- [ ] **Configuration**: Verify maintenance mode configuration settings
- [ ] **Services**: Confirm all required services are running
- [ ] **Connectivity**: Test database and Redis connectivity
- [ ] **Permissions**: Verify user permissions and access rights
- [ ] **Logs**: Check recent log entries for errors or warnings

## Common Issues and Solutions

### 1. Maintenance Mode Won't Activate

#### Symptoms
- Clicking "Enable Maintenance Mode" has no effect
- Maintenance status remains "inactive" after activation attempt
- No error messages displayed to user
- Operations continue to work normally

#### Possible Causes
- Configuration service unavailable or not responding
- Database connectivity issues
- Insufficient user permissions
- Middleware not properly registered
- Redis session manager issues

#### Diagnostic Steps

1. **Check Configuration Service**
```bash
# Test configuration service connectivity
python -c "
from config import Config
from app.core.configuration.core.configuration_service import ConfigurationService
config = Config()
service = ConfigurationService(config)
try:
    status = service.get('maintenance_mode')
    print(f'Configuration service working: {status}')
except Exception as e:
    print(f'Configuration service error: {e}')
"
```

2. **Verify Database Connection**
```bash
# Test database connectivity
python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
config = Config()
db_manager = DatabaseManager(config)
try:
    with db_manager.get_session() as session:
        result = session.execute('SELECT 1').fetchone()
        print('Database connection: OK')
except Exception as e:
    print(f'Database connection error: {e}')
"
```

3. **Check User Permissions**
```bash
# Verify admin user permissions
python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    user = session.query(User).filter_by(username='admin').first()
    if user:
        print(f'User role: {user.role.value}')
        print(f'Is admin: {user.role.value == \"admin\"}')
    else:
        print('Admin user not found')
"
```

4. **Verify Middleware Registration**
```bash
# Check if maintenance middleware is registered
python -c "
from web_app import app
middleware_names = [func.__name__ for func in app.before_request_funcs.get(None, [])]
print('Registered middleware:')
for name in middleware_names:
    print(f'  - {name}')
print(f'Maintenance middleware registered: {\"maintenance_check\" in str(middleware_names)}')
"
```

#### Solutions

**Solution 1: Restart Configuration Service**
```bash
# If using separate configuration service
sudo systemctl restart configuration-service

# If integrated, restart main application
sudo systemctl restart vedfolnir
```

**Solution 2: Fix Database Connection**
```bash
# Check database service status
sudo systemctl status mysql

# Restart database if needed
sudo systemctl restart mysql

# Verify connection parameters in .env file
grep -E "^DB_|^DATABASE_" .env
```

**Solution 3: Fix User Permissions**
```bash
# Update user role to admin
python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    user = session.query(User).filter_by(username='admin').first()
    if user:
        user.role = UserRole.ADMIN
        session.commit()
        print('User role updated to admin')
    else:
        print('Admin user not found')
"
```

**Solution 4: Re-register Middleware**
```bash
# Restart the web application
python web_app.py & sleep 10
```

### 2. Users Can Still Access Blocked Operations

#### Symptoms
- Maintenance mode shows as "active" but users can still perform blocked operations
- Operations that should be blocked return normal responses
- No maintenance messages displayed to users
- System appears to be in maintenance mode but doesn't block anything

#### Possible Causes
- Middleware not intercepting requests properly
- Operation classification not working correctly
- Caching issues preventing updates
- Admin bypass being applied incorrectly
- Route registration issues

#### Diagnostic Steps

1. **Test Operation Blocking**
```bash
# Test if operations are actually blocked
curl -X POST http://localhost:5000/start_caption_generation \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}' \
  -v

# Should return HTTP 503 if maintenance mode is working
```

2. **Check Operation Classification**
```bash
# Test operation classification
python -c "
from maintenance_operation_classifier import MaintenanceOperationClassifier
classifier = MaintenanceOperationClassifier()
op_type = classifier.classify_operation('/start_caption_generation', 'POST')
print(f'Operation type: {op_type}')
is_blocked = classifier.is_blocked_operation(op_type, 'normal')
print(f'Should be blocked: {is_blocked}')
"
```

3. **Verify Middleware Execution**
```bash
# Check if middleware is being called (check logs)
tail -f logs/webapp.log | grep -i maintenance
```

4. **Test Admin Bypass**
```bash
# Check if admin bypass is working correctly
python -c "
from maintenance_mode_middleware import MaintenanceModeMiddleware
from models import User, UserRole
# Test admin detection logic
middleware = MaintenanceModeMiddleware(None, None)
# This would need actual user object for testing
print('Admin bypass logic needs testing with actual user session')
"
```

#### Solutions

**Solution 1: Clear Application Cache**
```bash
# Clear Python bytecode cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Restart application
python web_app.py & sleep 10
```

**Solution 2: Fix Operation Classification**
```bash
# Verify and update operation classification rules
python -c "
from maintenance_operation_classifier import MaintenanceOperationClassifier
classifier = MaintenanceOperationClassifier()
# Add missing classification if needed
classifier.add_custom_classification(
    pattern=r'/start_caption_generation',
    operation_type='CAPTION_GENERATION'
)
"
```

**Solution 3: Debug Middleware**
```bash
# Enable debug logging for middleware
export LOG_LEVEL=DEBUG
python web_app.py & sleep 10

# Check middleware logs
tail -f logs/webapp.log | grep -i "maintenance\|middleware"
```

### 3. Session Invalidation Not Working

#### Symptoms
- Non-admin users retain access during maintenance mode
- Users can still log in during maintenance
- Session cleanup doesn't remove user sessions
- Admin users lose access (should be preserved)

#### Possible Causes
- Redis session manager connectivity issues
- Session cleanup logic errors
- User role detection problems
- Session middleware configuration issues
- Redis authentication or permission problems

#### Diagnostic Steps

1. **Test Redis Connectivity**
```bash
# Test Redis connection
python -c "
import redis
from config import Config
config = Config()
try:
    r = redis.Redis.from_url(config.REDIS_URL)
    r.ping()
    print('Redis connection: OK')
    # List current sessions
    keys = r.keys('vedfolnir:session:*')
    print(f'Active sessions: {len(keys)}')
except Exception as e:
    print(f'Redis connection error: {e}')
"
```

2. **Check Session Manager**
```bash
# Test session manager functionality
python -c "
from redis_session_manager import RedisSessionManager
from config import Config
config = Config()
manager = RedisSessionManager(config)
try:
    health = manager.health_check()
    print(f'Session manager health: {health}')
    stats = manager.get_session_statistics()
    print(f'Session statistics: {stats}')
except Exception as e:
    print(f'Session manager error: {e}')
"
```

3. **Verify User Role Detection**
```bash
# Test user role detection in sessions
python -c "
from flask import Flask
from redis_session_manager import RedisSessionManager
from config import Config
app = Flask(__name__)
config = Config()
manager = RedisSessionManager(config)
# This would need actual session testing
print('User role detection needs testing with actual sessions')
"
```

#### Solutions

**Solution 1: Fix Redis Connection**
```bash
# Check Redis service status
sudo systemctl status redis

# Restart Redis if needed
sudo systemctl restart redis

# Verify Redis configuration
redis-cli ping
```

**Solution 2: Clear All Sessions**
```bash
# Manually clear all sessions (emergency)
python -c "
import redis
from config import Config
config = Config()
r = redis.Redis.from_url(config.REDIS_URL)
keys = r.keys('vedfolnir:session:*')
if keys:
    r.delete(*keys)
    print(f'Cleared {len(keys)} sessions')
else:
    print('No sessions to clear')
"
```

**Solution 3: Restart Session Services**
```bash
# Restart web application to reinitialize session manager
pkill -f "python web_app.py"
sleep 2
python web_app.py & sleep 10
```

### 4. Emergency Mode Issues

#### Symptoms
- Emergency mode doesn't activate when triggered
- Emergency mode activates but doesn't block operations
- Jobs don't terminate during emergency mode
- Admin access is blocked during emergency mode
- Emergency mode can't be deactivated

#### Possible Causes
- Emergency handler not properly initialized
- Job termination logic failures
- Session cleanup issues during emergency
- Admin access preservation problems
- Emergency mode state persistence issues

#### Diagnostic Steps

1. **Test Emergency Handler**
```bash
# Check emergency handler initialization
python -c "
from emergency_maintenance_handler import EmergencyMaintenanceHandler
from config import Config
config = Config()
handler = EmergencyMaintenanceHandler(config)
print('Emergency handler initialized successfully')
"
```

2. **Check Running Jobs**
```bash
# List currently running jobs
python -c "
from app.services.task.core.task_queue_manager import TaskQueueManager
from config import Config
config = Config()
manager = TaskQueueManager(config)
try:
    jobs = manager.get_active_jobs()
    print(f'Active jobs: {len(jobs)}')
    for job in jobs:
        print(f'  - {job.id}: {job.status}')
except Exception as e:
    print(f'Job manager error: {e}')
"
```

3. **Verify Emergency State**
```bash
# Check emergency mode state
python -c "
from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService
from config import Config
config = Config()
service = EnhancedMaintenanceModeService(config)
status = service.get_maintenance_status()
print(f'Maintenance mode: {status.mode}')
print(f'Is emergency: {status.mode == \"emergency\"}')
"
```

#### Solutions

**Solution 1: Force Emergency Deactivation**
```bash
# Manually deactivate emergency mode
python -c "
from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService
from config import Config
config = Config()
service = EnhancedMaintenanceModeService(config)
result = service.disable_maintenance()
print(f'Emergency mode deactivated: {result}')
"
```

**Solution 2: Terminate Jobs Manually**
```bash
# Manually terminate running jobs
python -c "
from app.services.task.core.task_queue_manager import TaskQueueManager
from config import Config
config = Config()
manager = TaskQueueManager(config)
terminated = manager.terminate_all_jobs(grace_period=10)
print(f'Terminated {terminated} jobs')
"
```

**Solution 3: Reset Emergency State**
```bash
# Reset emergency state in configuration
python -c "
from app.core.configuration.core.configuration_service import ConfigurationService
from config import Config
config = Config()
service = ConfigurationService(config)
service.set('maintenance_mode', 'false')
service.set('maintenance_mode_type', 'normal')
print('Emergency state reset')
"
```

### 5. Performance Issues During Maintenance

#### Symptoms
- Slow response times during maintenance mode
- High CPU or memory usage
- Database connection timeouts
- Redis performance issues
- User interface becomes unresponsive

#### Possible Causes
- High volume of blocked operation attempts
- Inefficient middleware processing
- Database connection pool exhaustion
- Redis memory issues
- Logging system overload

#### Diagnostic Steps

1. **Check System Resources**
```bash
# Monitor system resources
top -p $(pgrep -f "python web_app.py")
free -h
df -h
```

2. **Monitor Database Connections**
```bash
# Check database connection pool
python -c "
from app.core.database.core.database_manager import DatabaseManager
from config import Config
config = Config()
db_manager = DatabaseManager(config)
pool = db_manager.engine.pool
print(f'Pool size: {pool.size()}')
print(f'Checked out: {pool.checkedout()}')
print(f'Overflow: {pool.overflow()}')
"
```

3. **Check Redis Performance**
```bash
# Monitor Redis performance
redis-cli info memory
redis-cli info stats
redis-cli slowlog get 10
```

4. **Analyze Request Patterns**
```bash
# Check for high volume of blocked requests
tail -f logs/webapp.log | grep -c "Operation blocked" | head -10
```

#### Solutions

**Solution 1: Optimize Middleware**
```bash
# Reduce middleware overhead by caching maintenance status
# This would require code changes to cache status checks
```

**Solution 2: Increase Connection Pool**
```bash
# Increase database connection pool size
export DB_POOL_SIZE=50
export DB_MAX_OVERFLOW=100
python web_app.py & sleep 10
```

**Solution 3: Optimize Redis**
```bash
# Optimize Redis memory usage
redis-cli config set maxmemory-policy allkeys-lru
redis-cli config set maxmemory 256mb
```

**Solution 4: Rate Limit Blocked Requests**
```bash
# Implement rate limiting for blocked operations
# This would require code changes to add rate limiting
```

## Advanced Troubleshooting

### Log Analysis

#### Key Log Locations
- **Application Logs**: `logs/webapp.log`
- **Maintenance Logs**: `logs/maintenance.log`
- **Security Logs**: `logs/security_events.log`
- **Session Logs**: `logs/session_debug.log`
- **System Logs**: `/var/log/syslog` (Linux) or system equivalent

#### Important Log Patterns

**Maintenance Activation**
```
[MAINTENANCE] Maintenance mode activated: reason="Database optimization" admin="admin"
```

**Operation Blocking**
```
[MAINTENANCE] Operation blocked: endpoint="/start_caption_generation" user="user123" reason="maintenance_active"
```

**Session Invalidation**
```
[MAINTENANCE] Session invalidated: session_id="abc123" user="user456" reason="maintenance_activation"
```

**Emergency Mode**
```
[EMERGENCY] Emergency maintenance activated: reason="Security incident" admin="admin"
[EMERGENCY] Job terminated: job_id="job123" reason="emergency_mode"
```

#### Log Analysis Commands

```bash
# Find maintenance-related errors
grep -i "error\|exception\|failed" logs/webapp.log | grep -i maintenance

# Count blocked operations
grep "Operation blocked" logs/webapp.log | wc -l

# Find session issues
grep -i "session.*error\|session.*failed" logs/session_debug.log

# Monitor real-time maintenance activity
tail -f logs/webapp.log | grep -i maintenance
```

### Database Troubleshooting

#### Common Database Issues

**Connection Pool Exhaustion**
```sql
-- Check current connections
SHOW PROCESSLIST;

-- Check connection limits
SHOW VARIABLES LIKE 'max_connections';
```

**Configuration Table Issues**
```sql
-- Verify configuration table
SELECT * FROM configuration WHERE key LIKE 'maintenance%';

-- Reset maintenance configuration
UPDATE configuration SET value = 'false' WHERE key = 'maintenance_mode';
```

**Session Table Issues**
```sql
-- Check user sessions
SELECT COUNT(*) FROM user_sessions WHERE is_active = 1;

-- Clean up expired sessions
DELETE FROM user_sessions WHERE expires_at < NOW();
```

### Redis Troubleshooting

#### Redis Diagnostic Commands

```bash
# Check Redis status
redis-cli ping

# Monitor Redis commands
redis-cli monitor

# Check memory usage
redis-cli info memory

# List all session keys
redis-cli keys "vedfolnir:session:*"

# Check specific session
redis-cli get "vedfolnir:session:SESSION_ID"
```

#### Redis Performance Issues

```bash
# Check slow queries
redis-cli slowlog get 10

# Monitor Redis stats
redis-cli info stats

# Check Redis configuration
redis-cli config get "*"
```

### Network and Connectivity Issues

#### Network Diagnostic Commands

```bash
# Test local connectivity
curl -I http://localhost:5000/api/maintenance/status

# Test database connectivity
telnet localhost 3306

# Test Redis connectivity
telnet localhost 6379

# Check listening ports
netstat -tlnp | grep -E ":5000|:3306|:6379"
```

## Escalation Procedures

### When to Escalate

Escalate issues when:

- **Critical System Impact**: Maintenance mode is preventing critical operations
- **Security Concerns**: Potential security implications of maintenance issues
- **Data Integrity**: Risk of data loss or corruption
- **Extended Downtime**: Issues taking longer than expected to resolve
- **Multiple System Failures**: Multiple components failing simultaneously

### Escalation Contacts

#### Level 1 - Technical Support
- **Contact**: Technical support team
- **Response Time**: 15 minutes
- **Authority**: System configuration changes, service restarts

#### Level 2 - System Administrator
- **Contact**: Senior system administrator
- **Response Time**: 30 minutes
- **Authority**: Database changes, infrastructure modifications

#### Level 3 - Emergency Response
- **Contact**: Emergency response team
- **Response Time**: Immediate
- **Authority**: Emergency procedures, system shutdown

### Escalation Information

When escalating, provide:

1. **Issue Description**: Clear description of the problem
2. **Impact Assessment**: Current and potential impact
3. **Steps Taken**: Troubleshooting steps already attempted
4. **System State**: Current system status and configuration
5. **Urgency Level**: Business impact and urgency assessment
6. **Contact Information**: Your contact information for follow-up

## Prevention and Monitoring

### Preventive Measures

#### Regular Health Checks
```bash
# Daily health check script
#!/bin/bash
echo "=== Maintenance Mode Health Check ==="
echo "Date: $(date)"

# Check configuration service
python -c "from config import Config; from app.core.configuration.core.configuration_service import ConfigurationService; print('Config service: OK')" 2>/dev/null || echo "Config service: ERROR"

# Check database
python -c "from app.core.database.core.database_manager import DatabaseManager; from config import Config; db = DatabaseManager(Config()); print('Database: OK')" 2>/dev/null || echo "Database: ERROR"

# Check Redis
redis-cli ping >/dev/null 2>&1 && echo "Redis: OK" || echo "Redis: ERROR"

# Check maintenance status
python -c "from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService; from config import Config; service = EnhancedMaintenanceModeService(Config()); status = service.get_maintenance_status(); print(f'Maintenance: {status.is_active}')" 2>/dev/null || echo "Maintenance service: ERROR"
```

#### Monitoring Setup

**System Monitoring**
- CPU, memory, and disk usage monitoring
- Database connection pool monitoring
- Redis performance monitoring
- Application response time monitoring

**Application Monitoring**
- Maintenance mode status monitoring
- Blocked operation attempt monitoring
- Session invalidation monitoring
- Error rate monitoring

**Alerting Rules**
- Alert when maintenance mode is activated
- Alert on high blocked operation rates
- Alert on session manager failures
- Alert on emergency mode activation

### Best Practices

#### Regular Maintenance
- **Weekly**: Review maintenance logs and performance metrics
- **Monthly**: Test emergency procedures and escalation contacts
- **Quarterly**: Update documentation and procedures
- **Annually**: Comprehensive system review and improvement planning

#### Documentation Maintenance
- Keep troubleshooting procedures up to date
- Document new issues and solutions as they arise
- Maintain accurate contact information
- Regular review and validation of procedures

#### Training and Preparedness
- Regular training on troubleshooting procedures
- Practice emergency scenarios
- Keep diagnostic tools and scripts updated
- Maintain knowledge base of common issues

## Conclusion

This troubleshooting guide provides comprehensive solutions for common Enhanced Maintenance Mode issues. Regular monitoring, preventive maintenance, and following these troubleshooting procedures will help ensure reliable maintenance mode operations.

For issues not covered in this guide or for complex problems requiring specialized expertise, don't hesitate to escalate to the appropriate support level. Early escalation is better than prolonged troubleshooting when system stability is at risk.

Remember to document any new issues and solutions encountered to help improve this guide for future use.