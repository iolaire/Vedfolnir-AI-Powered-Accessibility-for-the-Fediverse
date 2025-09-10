# Enhanced Maintenance Mode - Rollback and Recovery Procedures

## Overview

This document outlines comprehensive rollback and recovery procedures for the Enhanced Maintenance Mode system. It covers scenarios where rollback is necessary, step-by-step rollback procedures, recovery validation, and post-rollback actions.

## When to Initiate Rollback

### Automatic Rollback Triggers

Rollback should be automatically initiated when:

- **Application Startup Failure**: Application fails to start after deployment
- **Critical Functionality Broken**: Core maintenance mode features not working
- **Database Corruption**: Data integrity issues detected
- **Security Vulnerabilities**: New security issues introduced
- **Performance Degradation**: Unacceptable performance impact (>50% degradation)

### Manual Rollback Triggers

Consider manual rollback when:

- **User Impact**: Significant negative impact on user experience
- **Operational Issues**: Maintenance procedures not working as expected
- **Integration Failures**: External system integrations broken
- **Monitoring Failures**: Monitoring and alerting systems compromised
- **Stakeholder Decision**: Business decision to rollback

### Rollback Decision Matrix

| Issue Severity | User Impact | System Stability | Decision |
|---------------|-------------|------------------|----------|
| Critical | High | Unstable | Immediate Rollback |
| High | Medium | Stable | Consider Rollback |
| Medium | Low | Stable | Fix Forward |
| Low | None | Stable | Fix Forward |

## Pre-Rollback Assessment

### Impact Assessment

Before initiating rollback, assess:

1. **Current System State**
   - What is currently broken or degraded?
   - How many users are affected?
   - What functionality is impacted?

2. **Rollback Feasibility**
   - Are complete backups available?
   - How long will rollback take?
   - What data might be lost?

3. **Alternative Solutions**
   - Can the issue be fixed quickly without rollback?
   - Are there workarounds available?
   - Is partial rollback sufficient?

### Rollback Readiness Checklist

- [ ] **Backups Available**: Verified backups of application, database, and configuration
- [ ] **Rollback Team**: Key personnel available and notified
- [ ] **Communication Plan**: Stakeholders and users informed
- [ ] **Rollback Window**: Maintenance window scheduled if needed
- [ ] **Recovery Plan**: Post-rollback recovery procedures ready

## Rollback Procedures

### Phase 1: Immediate System Protection

#### 1.1 Activate Emergency Maintenance Mode
```bash
# Immediately protect the system
curl -X POST http://localhost:5000/api/maintenance/emergency \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "reason": "ROLLBACK: Critical issues detected - initiating rollback procedures",
    "terminate_jobs": true,
    "grace_period": 30
  }'
```

#### 1.2 Stop Current Application
```bash
# Stop the application service
sudo systemctl stop vedfolnir

# Verify application is stopped
sudo systemctl status vedfolnir

# Kill any remaining processes
pkill -f "python web_app.py"
```

#### 1.3 Create Emergency Backup
```bash
# Create emergency backup of current state
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /backup/rollback_$TIMESTAMP

# Backup current application
sudo tar -czf /backup/rollback_$TIMESTAMP/app_current.tar.gz /opt/vedfolnir/

# Backup current database
mysqldump -u vedfolnir_user -p vedfolnir > /backup/rollback_$TIMESTAMP/db_current.sql

# Backup current Redis data
redis-cli BGSAVE
sudo cp /var/lib/redis/dump.rdb /backup/rollback_$TIMESTAMP/redis_current.rdb

# Backup current configuration
sudo cp /opt/vedfolnir/.env /backup/rollback_$TIMESTAMP/.env_current
```

### Phase 2: Application Rollback

#### 2.1 Restore Application Code
```bash
# Find the most recent stable backup
BACKUP_FILE=$(ls -t /backup/vedfolnir_app_*.tar.gz | head -1)
echo "Restoring from: $BACKUP_FILE"

# Remove current application
sudo rm -rf /opt/vedfolnir_failed
sudo mv /opt/vedfolnir /opt/vedfolnir_failed

# Restore application from backup
sudo tar -xzf $BACKUP_FILE -C /

# Verify restoration
ls -la /opt/vedfolnir/
```

#### 2.2 Restore Configuration
```bash
# Find the most recent stable configuration
CONFIG_BACKUP=$(ls -t /backup/.env_* | head -1)
echo "Restoring configuration from: $CONFIG_BACKUP"

# Restore configuration
sudo cp $CONFIG_BACKUP /opt/vedfolnir/.env

# Verify configuration
grep -E "^[A-Z]" /opt/vedfolnir/.env | head -10
```

#### 2.3 Restore Dependencies
```bash
# Switch to application user
sudo su - vedfolnir

# Navigate to application directory
cd /opt/vedfolnir

# Activate virtual environment
source venv/bin/activate

# Restore dependencies from requirements.txt
pip install -r requirements.txt

# Verify critical dependencies
python -c "import flask, sqlalchemy, redis; print('Dependencies OK')"
```

### Phase 3: Database Rollback

#### 3.1 Assess Database State
```bash
# Check current database state
mysql -u vedfolnir_user -p -e "
SELECT 
  table_name,
  table_rows,
  ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.tables 
WHERE table_schema = 'vedfolnir'
ORDER BY table_rows DESC;"

# Check for any corruption
mysql -u vedfolnir_user -p -e "CHECK TABLE users, platform_connections, posts, images;"
```

#### 3.2 Database Rollback Decision

**Option A: Full Database Restore (Recommended for major issues)**
```bash
# Find the most recent stable database backup
DB_BACKUP=$(ls -t /backup/vedfolnir_*.sql | head -1)
echo "Restoring database from: $DB_BACKUP"

# Create backup of current database state
mysqldump -u vedfolnir_user -p vedfolnir > /backup/rollback_$TIMESTAMP/db_before_restore.sql

# Drop and recreate database
mysql -u root -p -e "
DROP DATABASE vedfolnir;
CREATE DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir_user'@'localhost';
FLUSH PRIVILEGES;"

# Restore database from backup
mysql -u vedfolnir_user -p vedfolnir < $DB_BACKUP

# Verify restoration
mysql -u vedfolnir_user -p -e "
SELECT COUNT(*) as user_count FROM vedfolnir.users;
SELECT COUNT(*) as post_count FROM vedfolnir.posts;"
```

**Option B: Selective Table Restore (For specific table issues)**
```bash
# Restore specific tables only
mysql -u vedfolnir_user -p -e "
DROP TABLE IF EXISTS configuration;
"

# Extract and restore specific table
sed -n '/CREATE TABLE.*configuration/,/UNLOCK TABLES/p' $DB_BACKUP | \
mysql -u vedfolnir_user -p vedfolnir
```

#### 3.3 Database Integrity Verification
```bash
# Run integrity checks
mysql -u vedfolnir_user -p -e "
CHECK TABLE users, platform_connections, posts, images, processing_runs, user_sessions;
"

# Verify data consistency
python -c "
from app.core.database.core.database_manager import DatabaseManager
from models import *
from config import Config
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    user_count = session.query(User).count()
    post_count = session.query(Post).count()
    print(f'Users: {user_count}, Posts: {post_count}')
    print('Database integrity check passed')
"
```

### Phase 4: Redis Rollback

#### 4.1 Redis State Assessment
```bash
# Check current Redis state
redis-cli info memory
redis-cli info stats
redis-cli keys "vedfolnir:session:*" | wc -l
```

#### 4.2 Redis Data Restore
```bash
# Stop Redis service
sudo systemctl stop redis

# Backup current Redis data
sudo cp /var/lib/redis/dump.rdb /backup/rollback_$TIMESTAMP/redis_before_restore.rdb

# Find most recent stable Redis backup
REDIS_BACKUP=$(ls -t /backup/redis_*.rdb | head -1)
echo "Restoring Redis from: $REDIS_BACKUP"

# Restore Redis data
sudo cp $REDIS_BACKUP /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb

# Start Redis service
sudo systemctl start redis

# Verify Redis restoration
redis-cli ping
redis-cli keys "vedfolnir:session:*" | wc -l
```

### Phase 5: Service Restoration

#### 5.1 Start Services
```bash
# Start database service (if stopped)
sudo systemctl start mysql
sudo systemctl status mysql

# Start Redis service (if not already started)
sudo systemctl start redis
sudo systemctl status redis

# Start application service
sudo systemctl start vedfolnir
sudo systemctl status vedfolnir
```

#### 5.2 Service Health Verification
```bash
# Wait for services to fully start
sleep 30

# Test application health
curl -f http://localhost:5000/health || echo "Health check failed"

# Test maintenance API
curl -f http://localhost:5000/api/maintenance/status || echo "Maintenance API failed"

# Test database connectivity
python -c "
from app.core.database.core.database_manager import DatabaseManager
from config import Config
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    result = session.execute('SELECT 1').fetchone()
    print('Database connectivity: OK')
"

# Test Redis connectivity
redis-cli ping
```

## Post-Rollback Validation

### Functional Testing

#### 1. Core Functionality Tests
```bash
# Test basic application functionality
curl -I http://localhost:5000/

# Test login functionality (manual test required)
echo "Manual test: Verify admin login works"

# Test maintenance mode functionality
curl -X POST http://localhost:5000/api/maintenance/enable \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"reason": "Rollback validation test", "duration": 300}'

# Verify maintenance mode is active
curl http://localhost:5000/api/maintenance/status

# Disable maintenance mode
curl -X POST http://localhost:5000/api/maintenance/disable \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### 2. Data Integrity Tests
```bash
# Verify user data integrity
python -c "
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole
from config import Config
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    admin_count = session.query(User).filter_by(role=UserRole.ADMIN).count()
    total_users = session.query(User).count()
    print(f'Admin users: {admin_count}, Total users: {total_users}')
    if admin_count > 0:
        print('User data integrity: OK')
    else:
        print('WARNING: No admin users found')
"

# Verify platform connections
python -c "
from app.core.database.core.database_manager import DatabaseManager
from models import PlatformConnection
from config import Config
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    platform_count = session.query(PlatformConnection).count()
    print(f'Platform connections: {platform_count}')
"
```

#### 3. Session Management Tests
```bash
# Test session creation and management
python -c "
from app.core.session.redis.redis_session_manager import RedisSessionManager
from config import Config
config = Config()
manager = RedisSessionManager(config)
health = manager.health_check()
print(f'Session manager health: {health}')
stats = manager.get_session_statistics()
print(f'Session statistics: {stats}')
"
```

### Performance Testing

#### 1. Response Time Testing
```bash
# Test response times
time curl -s http://localhost:5000/api/maintenance/status > /dev/null
time curl -s http://localhost:5000/health > /dev/null

# Load testing (if ab is available)
if command -v ab &> /dev/null; then
    ab -n 100 -c 5 http://localhost:5000/api/maintenance/status
fi
```

#### 2. Resource Usage Monitoring
```bash
# Monitor system resources
echo "Monitoring system resources for 60 seconds..."
for i in {1..12}; do
    echo "$(date): CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}'), Memory: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
    sleep 5
done
```

### Security Validation

#### 1. Authentication Tests
```bash
# Test authentication endpoints
curl -X POST http://localhost:5000/api/maintenance/enable \
  -H "Content-Type: application/json" \
  -d '{"reason": "test"}'
# Should return 401 Unauthorized

# Test with invalid token
curl -X POST http://localhost:5000/api/maintenance/enable \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid_token" \
  -d '{"reason": "test"}'
# Should return 401 Unauthorized
```

#### 2. Security Configuration Verification
```bash
# Check security settings
grep -E "SECURITY_|CSRF_|RATE_LIMIT" /opt/vedfolnir/.env

# Verify SSL/TLS configuration (if applicable)
if command -v openssl &> /dev/null; then
    echo | openssl s_client -servername localhost -connect localhost:443 2>/dev/null | \
    openssl x509 -noout -dates 2>/dev/null || echo "SSL not configured or not accessible"
fi
```

## Post-Rollback Actions

### Immediate Actions (0-2 hours)

#### 1. System Monitoring
```bash
# Enable intensive monitoring
echo "Starting intensive monitoring period..."

# Monitor application logs
tail -f /opt/vedfolnir/logs/webapp.log &
WEBAPP_LOG_PID=$!

# Monitor system resources
watch -n 30 'echo "$(date): CPU: $(top -bn1 | grep "Cpu(s)" | awk "{print \$2}"), Memory: $(free | grep Mem | awk "{printf \"%.1f%%\", \$3/\$2 * 100.0}")"' &
MONITOR_PID=$!

echo "Monitoring started. PIDs: webapp_log=$WEBAPP_LOG_PID, monitor=$MONITOR_PID"
echo "Stop monitoring with: kill $WEBAPP_LOG_PID $MONITOR_PID"
```

#### 2. User Communication
```bash
# Notify users of rollback completion
cat > /tmp/rollback_notification.txt << 'EOF'
System Rollback Completed

The Vedfolnir system has been successfully rolled back to a previous stable version due to issues with the recent deployment.

Status: All services restored and operational
Impact: Previous functionality restored
Action Required: None - normal operations have resumed

We apologize for any inconvenience caused during the rollback period.

If you experience any issues, please contact support.
EOF

# Send notification (adjust email addresses as needed)
mail -s "Vedfolnir System Rollback Completed" admin@your-domain.com < /tmp/rollback_notification.txt
```

#### 3. Stakeholder Notification
```bash
# Create rollback summary report
cat > /tmp/rollback_summary.txt << EOF
ROLLBACK SUMMARY REPORT

Date: $(date)
Rollback Initiated: [Time rollback started]
Rollback Completed: $(date)
Duration: [Calculate duration]

Reason for Rollback:
[Describe the issues that triggered rollback]

Actions Taken:
- Emergency maintenance mode activated
- Application rolled back to previous version
- Database restored from backup
- Redis data restored
- All services restarted and verified

Current Status:
- System: Operational
- Database: Restored and verified
- Sessions: Restored and functional
- Monitoring: Active and normal

Next Steps:
- Continue intensive monitoring for 24 hours
- Investigate root cause of original issues
- Plan corrective actions for next deployment
- Update rollback procedures based on lessons learned

Contact: [Your contact information]
EOF

# Send to stakeholders
mail -s "URGENT: Vedfolnir Rollback Summary" stakeholders@your-domain.com < /tmp/rollback_summary.txt
```

### Short-term Actions (2-24 hours)

#### 1. Root Cause Analysis
```bash
# Collect data for root cause analysis
mkdir -p /tmp/rollback_analysis

# Copy relevant logs
cp /opt/vedfolnir/logs/webapp.log /tmp/rollback_analysis/webapp_rollback.log
cp /var/log/syslog /tmp/rollback_analysis/syslog_rollback.log
cp /backup/rollback_$TIMESTAMP/db_current.sql /tmp/rollback_analysis/

# Create analysis report template
cat > /tmp/rollback_analysis/root_cause_analysis.md << 'EOF'
# Root Cause Analysis - Rollback Event

## Timeline
- Deployment Time: [Time]
- Issue Detection: [Time]
- Rollback Decision: [Time]
- Rollback Completion: [Time]

## Issues Identified
1. [Issue 1 description]
2. [Issue 2 description]

## Root Causes
1. [Root cause 1]
2. [Root cause 2]

## Contributing Factors
- [Factor 1]
- [Factor 2]

## Lessons Learned
- [Lesson 1]
- [Lesson 2]

## Preventive Actions
- [Action 1]
- [Action 2]

## Process Improvements
- [Improvement 1]
- [Improvement 2]
EOF

echo "Root cause analysis template created at /tmp/rollback_analysis/root_cause_analysis.md"
```

#### 2. System Hardening
```bash
# Review and strengthen monitoring
echo "Reviewing monitoring configuration..."

# Check all monitoring scripts are working
/opt/vedfolnir/monitoring/health_check.py
/opt/vedfolnir/monitoring/system_monitor.py

# Verify alerting is working
python -c "
from app.services.alerts.components.alert_manager import AlertManager
am = AlertManager()
am.send_alert('rollback_test', 'Rollback Recovery Test', 'Testing alert system after rollback', 'info')
print('Test alert sent')
"

# Update monitoring thresholds if needed
echo "Review and update monitoring thresholds based on rollback experience"
```

#### 3. Documentation Updates
```bash
# Update rollback procedures based on experience
echo "Updating rollback procedures with lessons learned..."

# Create improvement notes
cat > /tmp/rollback_improvements.md << 'EOF'
# Rollback Procedure Improvements

## What Worked Well
- [List successful aspects]

## What Could Be Improved
- [List areas for improvement]

## Recommended Changes
- [List specific changes to procedures]

## Additional Tools Needed
- [List tools that would help]

## Training Needs
- [List training requirements]
EOF

echo "Rollback improvements documented at /tmp/rollback_improvements.md"
```

### Long-term Actions (1-7 days)

#### 1. Process Review and Improvement
- Conduct post-rollback review meeting
- Update deployment procedures
- Enhance testing procedures
- Improve monitoring and alerting
- Update documentation

#### 2. Team Training
- Review rollback procedures with team
- Conduct rollback simulation exercises
- Update emergency contact procedures
- Enhance communication protocols

#### 3. System Improvements
- Implement additional safeguards
- Enhance automated testing
- Improve backup and recovery procedures
- Strengthen monitoring and alerting

## Rollback Prevention Strategies

### Pre-Deployment
- Comprehensive testing in staging environment
- Automated testing pipelines
- Code review processes
- Deployment checklists
- Rollback plan preparation

### During Deployment
- Gradual rollout procedures
- Real-time monitoring
- Immediate rollback triggers
- Communication protocols
- Stakeholder notifications

### Post-Deployment
- Intensive monitoring period
- User feedback collection
- Performance validation
- Security verification
- Documentation updates

## Emergency Contacts

### Rollback Team
- **Primary Administrator**: [Contact information]
- **Database Administrator**: [Contact information]
- **Security Officer**: [Contact information]
- **Operations Manager**: [Contact information]

### Escalation Contacts
- **Technical Director**: [Contact information]
- **Emergency Hotline**: [Contact information]
- **External Support**: [Contact information]

## Conclusion

These rollback and recovery procedures provide comprehensive guidance for safely rolling back the Enhanced Maintenance Mode system when issues arise. The key to successful rollback is:

1. **Quick Decision Making**: Don't hesitate to rollback when criteria are met
2. **Systematic Approach**: Follow procedures step-by-step
3. **Thorough Validation**: Verify all functionality after rollback
4. **Continuous Improvement**: Learn from each rollback experience
5. **Clear Communication**: Keep all stakeholders informed

Regular practice and refinement of these procedures ensures that rollback operations can be performed quickly and safely when needed, minimizing system downtime and user impact.