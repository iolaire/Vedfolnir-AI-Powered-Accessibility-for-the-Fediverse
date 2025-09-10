# Enhanced Maintenance Mode - Deployment Guide

## Overview

This deployment guide provides step-by-step instructions for deploying the Enhanced Maintenance Mode system to production environments. It covers pre-deployment preparation, deployment procedures, post-deployment validation, and rollback procedures.

## Pre-Deployment Requirements

### System Requirements

#### Minimum Requirements
- **Python**: 3.8 or higher
- **Database**: MySQL 5.7+ or MariaDB 10.3+
- **Redis**: 6.0 or higher
- **Memory**: 2GB RAM minimum, 4GB recommended
- **Storage**: 10GB free space minimum
- **Network**: Stable internet connection for external dependencies

#### Recommended Production Requirements
- **CPU**: 4+ cores
- **Memory**: 8GB+ RAM
- **Storage**: 50GB+ SSD storage
- **Database**: Dedicated MySQL/MariaDB server
- **Redis**: Dedicated Redis server with persistence
- **Load Balancer**: For high availability deployments

### Software Dependencies

#### Core Dependencies
```bash
# Python packages (from requirements.txt)
Flask>=2.0.0
SQLAlchemy>=1.4.0
redis>=4.0.0
pymysql>=1.0.0
cryptography>=3.4.0
python-dotenv>=0.19.0

# System packages
mysql-client
redis-tools
nginx (optional, for reverse proxy)
supervisor (optional, for process management)
```

#### Development Dependencies (for testing)
```bash
pytest>=6.0.0
pytest-cov>=2.12.0
requests>=2.25.0
```

### Environment Preparation

#### Database Setup
```sql
-- Create database and user
CREATE DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'vedfolnir_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir_user'@'localhost';
FLUSH PRIVILEGES;

-- Verify connection
mysql -u vedfolnir_user -p vedfolnir -e "SELECT 1;"
```

#### Redis Setup
```bash
# Install Redis (Ubuntu/Debian)
sudo apt update
sudo apt install redis-server

# Configure Redis for production
sudo nano /etc/redis/redis.conf

# Key settings:
# bind 127.0.0.1
# port 6379
# requirepass your_redis_password
# maxmemory 256mb
# maxmemory-policy allkeys-lru
# save 900 1
# save 300 10
# save 60 10000

# Restart Redis
sudo systemctl restart redis
sudo systemctl enable redis
```

#### System User Setup
```bash
# Create dedicated user for the application
sudo useradd -r -s /bin/bash -d /opt/vedfolnir vedfolnir
sudo mkdir -p /opt/vedfolnir
sudo chown vedfolnir:vedfolnir /opt/vedfolnir
```

## Pre-Deployment Checklist

### Code Preparation
- [ ] **Code Review**: All maintenance mode code reviewed and approved
- [ ] **Testing**: All tests passing in staging environment
- [ ] **Documentation**: All documentation updated and reviewed
- [ ] **Configuration**: Environment-specific configuration prepared
- [ ] **Dependencies**: All dependencies verified and compatible

### Infrastructure Preparation
- [ ] **Database**: Database server configured and accessible
- [ ] **Redis**: Redis server configured and accessible
- [ ] **Storage**: Sufficient storage space available
- [ ] **Backup**: Current system backup completed
- [ ] **Monitoring**: Monitoring systems configured for new components

### Security Preparation
- [ ] **Credentials**: Secure credentials generated and stored
- [ ] **Certificates**: SSL certificates updated if needed
- [ ] **Firewall**: Firewall rules configured for new services
- [ ] **Access Control**: User access and permissions configured
- [ ] **Audit Logging**: Audit logging systems prepared

### Team Preparation
- [ ] **Deployment Team**: Deployment team identified and briefed
- [ ] **Stakeholders**: Key stakeholders notified of deployment
- [ ] **Support Team**: Support team prepared for post-deployment issues
- [ ] **Communication**: Communication channels established
- [ ] **Rollback Plan**: Rollback procedures reviewed and understood

## Deployment Procedures

### Phase 1: Pre-Deployment Backup

#### 1.1 Database Backup
```bash
# Create database backup
mysqldump -u vedfolnir_user -p vedfolnir > /backup/vedfolnir_pre_maintenance_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
mysql -u vedfolnir_user -p -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'vedfolnir';"
```

#### 1.2 Application Backup
```bash
# Create application backup
sudo tar -czf /backup/vedfolnir_app_$(date +%Y%m%d_%H%M%S).tar.gz /opt/vedfolnir/

# Create configuration backup
sudo cp /opt/vedfolnir/.env /backup/.env_$(date +%Y%m%d_%H%M%S)
```

#### 1.3 Redis Backup
```bash
# Create Redis backup
redis-cli BGSAVE
sudo cp /var/lib/redis/dump.rdb /backup/redis_$(date +%Y%m%d_%H%M%S).rdb
```

### Phase 2: Application Deployment

#### 2.1 Stop Current Application
```bash
# Stop web application (adjust for your process manager)
sudo systemctl stop vedfolnir
# OR
sudo supervisorctl stop vedfolnir
# OR
pkill -f "python web_app.py"
```

#### 2.2 Deploy New Code
```bash
# Switch to application user
sudo su - vedfolnir

# Navigate to application directory
cd /opt/vedfolnir

# Pull latest code (if using git)
git fetch origin
git checkout main
git pull origin main

# OR copy from deployment package
# sudo tar -xzf vedfolnir_enhanced_maintenance.tar.gz -C /opt/vedfolnir/
```

#### 2.3 Install Dependencies
```bash
# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Verify critical dependencies
python -c "import flask, sqlalchemy, redis; print('Dependencies OK')"
```

#### 2.4 Update Configuration
```bash
# Update environment configuration
nano .env

# Add new maintenance mode configuration
echo "# Enhanced Maintenance Mode Configuration" >> .env
echo "MAINTENANCE_MODE_ENABLED=true" >> .env
echo "MAINTENANCE_DEFAULT_TIMEOUT=7200" >> .env
echo "MAINTENANCE_CLEANUP_INTERVAL=300" >> .env
echo "EMERGENCY_MODE_JOB_GRACE_PERIOD=30" >> .env
echo "EMERGENCY_MODE_SESSION_CLEANUP=true" >> .env
echo "TEST_MODE_SIMULATION=true" >> .env
echo "MAINTENANCE_NOTIFICATIONS_ENABLED=true" >> .env

# Verify configuration
python -c "from config import Config; c = Config(); print('Config loaded successfully')"
```

### Phase 3: Database Migration

#### 3.1 Run Database Migrations
```bash
# Run any pending database migrations
python -c "
from app.core.database.core.database_manager import DatabaseManager
from config import Config
config = Config()
db_manager = DatabaseManager(config)
# Add any specific migration code here
print('Database migrations completed')
"
```

#### 3.2 Verify Database Schema
```bash
# Verify database schema
python -c "
from app.core.database.core.database_manager import DatabaseManager
from models import *
from config import Config
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    # Verify tables exist
    tables = session.execute('SHOW TABLES').fetchall()
    print(f'Database tables: {len(tables)}')
    print('Database schema verified')
"
```

### Phase 4: Service Configuration

#### 4.1 Create Systemd Service (Recommended)
```bash
# Create systemd service file
sudo nano /etc/systemd/system/vedfolnir.service
```

```ini
[Unit]
Description=Vedfolnir Enhanced Maintenance Mode Application
After=network.target mysql.service redis.service
Requires=mysql.service redis.service

[Service]
Type=simple
User=vedfolnir
Group=vedfolnir
WorkingDirectory=/opt/vedfolnir
Environment=PATH=/opt/vedfolnir/venv/bin
ExecStart=/opt/vedfolnir/venv/bin/python web_app.py
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable vedfolnir
```

#### 4.2 Configure Nginx (Optional)
```bash
# Create nginx configuration
sudo nano /etc/nginx/sites-available/vedfolnir
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/maintenance/ws {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

```bash
# Enable site and restart nginx
sudo ln -s /etc/nginx/sites-available/vedfolnir /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Phase 5: Start Services

#### 5.1 Start Application
```bash
# Start the application
sudo systemctl start vedfolnir

# Check status
sudo systemctl status vedfolnir

# Check logs
sudo journalctl -u vedfolnir -f
```

#### 5.2 Verify Service Health
```bash
# Test application health
curl -f http://localhost:5000/health || echo "Health check failed"

# Test maintenance status API
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

## Post-Deployment Validation

### Functional Testing

#### 1. Basic Functionality Tests
```bash
# Test maintenance mode activation
curl -X POST http://localhost:5000/api/maintenance/enable \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{"reason": "Deployment validation test", "duration": 300}'

# Verify maintenance mode is active
curl http://localhost:5000/api/maintenance/status

# Test operation blocking
curl -X POST http://localhost:5000/start_caption_generation \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
# Should return HTTP 503

# Disable maintenance mode
curl -X POST http://localhost:5000/api/maintenance/disable \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

#### 2. Emergency Mode Tests
```bash
# Test emergency mode activation
curl -X POST http://localhost:5000/api/maintenance/emergency \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{"reason": "Deployment validation - emergency test"}'

# Verify emergency mode blocks all operations
curl http://localhost:5000/ # Should show maintenance page

# Disable emergency mode
curl -X POST http://localhost:5000/api/maintenance/disable \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

#### 3. Session Management Tests
```bash
# Test session invalidation during maintenance
# This requires manual testing with browser sessions
echo "Manual test: Log in as non-admin user, enable maintenance, verify session invalidated"
```

### Performance Testing

#### 1. Load Testing
```bash
# Install Apache Bench for load testing
sudo apt install apache2-utils

# Test maintenance status API performance
ab -n 1000 -c 10 http://localhost:5000/api/maintenance/status

# Test blocked operation performance
ab -n 100 -c 5 http://localhost:5000/start_caption_generation
```

#### 2. Resource Monitoring
```bash
# Monitor system resources during testing
top -p $(pgrep -f "python web_app.py")
free -h
df -h

# Monitor database connections
mysql -u vedfolnir_user -p -e "SHOW PROCESSLIST;"

# Monitor Redis memory usage
redis-cli info memory
```

### Security Testing

#### 1. Authentication Tests
```bash
# Test admin-only endpoints without authentication
curl -X POST http://localhost:5000/api/maintenance/enable \
  -H "Content-Type: application/json" \
  -d '{"reason": "test"}'
# Should return HTTP 401

# Test with invalid token
curl -X POST http://localhost:5000/api/maintenance/enable \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid_token" \
  -d '{"reason": "test"}'
# Should return HTTP 401
```

#### 2. Input Validation Tests
```bash
# Test invalid maintenance mode parameters
curl -X POST http://localhost:5000/api/maintenance/enable \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{"mode": "invalid_mode"}'
# Should return HTTP 400
```

### Integration Testing

#### 1. Database Integration
```bash
# Test database operations during maintenance
python -c "
from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService
from config import Config
config = Config()
service = EnhancedMaintenanceModeService(config)

# Test maintenance activation
result = service.enable_maintenance('Integration test', 300)
print(f'Maintenance enabled: {result}')

# Test status retrieval
status = service.get_maintenance_status()
print(f'Status: {status.is_active}')

# Test deactivation
result = service.disable_maintenance()
print(f'Maintenance disabled: {result}')
"
```

#### 2. Redis Integration
```bash
# Test Redis session operations
python -c "
from redis_session_manager import RedisSessionManager
from config import Config
config = Config()
manager = RedisSessionManager(config)

# Test health check
health = manager.health_check()
print(f'Redis health: {health}')

# Test session statistics
stats = manager.get_session_statistics()
print(f'Session stats: {stats}')
"
```

## Monitoring and Alerting Setup

### Application Monitoring

#### 1. Health Check Monitoring
```bash
# Create health check script
cat > /opt/vedfolnir/scripts/health_check.sh << 'EOF'
#!/bin/bash
# Health check script for maintenance mode system

echo "=== Vedfolnir Health Check ==="
echo "Date: $(date)"

# Check application health
curl -f http://localhost:5000/health >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Application: OK"
else
    echo "❌ Application: FAILED"
    exit 1
fi

# Check maintenance API
curl -f http://localhost:5000/api/maintenance/status >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Maintenance API: OK"
else
    echo "❌ Maintenance API: FAILED"
    exit 1
fi

# Check database
python3 -c "
from app.core.database.core.database_manager import DatabaseManager
from config import Config
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    session.execute('SELECT 1')
print('✅ Database: OK')
" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Database: FAILED"
    exit 1
fi

# Check Redis
redis-cli ping >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Redis: OK"
else
    echo "❌ Redis: FAILED"
    exit 1
fi

echo "=== All Systems Operational ==="
EOF

chmod +x /opt/vedfolnir/scripts/health_check.sh
```

#### 2. Cron Job Setup
```bash
# Add health check to cron
sudo crontab -e

# Add this line to run health check every 5 minutes
*/5 * * * * /opt/vedfolnir/scripts/health_check.sh >> /var/log/vedfolnir_health.log 2>&1
```

### Log Monitoring

#### 1. Log Rotation Setup
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/vedfolnir
```

```
/opt/vedfolnir/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 vedfolnir vedfolnir
    postrotate
        systemctl reload vedfolnir
    endscript
}
```

#### 2. Log Monitoring Script
```bash
# Create log monitoring script
cat > /opt/vedfolnir/scripts/log_monitor.sh << 'EOF'
#!/bin/bash
# Monitor logs for maintenance mode events

LOG_FILE="/opt/vedfolnir/logs/webapp.log"
ALERT_EMAIL="admin@your-domain.com"

# Monitor for maintenance mode activation
tail -f "$LOG_FILE" | while read line; do
    if echo "$line" | grep -q "Maintenance mode activated"; then
        echo "ALERT: Maintenance mode activated - $line" | mail -s "Maintenance Mode Alert" "$ALERT_EMAIL"
    fi
    
    if echo "$line" | grep -q "Emergency maintenance activated"; then
        echo "CRITICAL: Emergency maintenance activated - $line" | mail -s "EMERGENCY Maintenance Alert" "$ALERT_EMAIL"
    fi
done
EOF

chmod +x /opt/vedfolnir/scripts/log_monitor.sh
```

### Performance Monitoring

#### 1. System Metrics Collection
```bash
# Install system monitoring tools
sudo apt install htop iotop nethogs

# Create performance monitoring script
cat > /opt/vedfolnir/scripts/performance_monitor.sh << 'EOF'
#!/bin/bash
# Collect performance metrics

METRICS_FILE="/var/log/vedfolnir_metrics.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# System metrics
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | cut -d'%' -f1)

# Application metrics
APP_PID=$(pgrep -f "python web_app.py")
if [ -n "$APP_PID" ]; then
    APP_CPU=$(ps -p $APP_PID -o %cpu --no-headers)
    APP_MEM=$(ps -p $APP_PID -o %mem --no-headers)
else
    APP_CPU="0"
    APP_MEM="0"
fi

# Database connections
DB_CONNECTIONS=$(mysql -u vedfolnir_user -p -e "SHOW STATUS LIKE 'Threads_connected';" | tail -1 | awk '{print $2}')

# Redis memory
REDIS_MEMORY=$(redis-cli info memory | grep used_memory_human | cut -d':' -f2 | tr -d '\r')

# Log metrics
echo "$TIMESTAMP,CPU:$CPU_USAGE%,Memory:$MEMORY_USAGE%,Disk:$DISK_USAGE%,AppCPU:$APP_CPU%,AppMem:$APP_MEM%,DBConn:$DB_CONNECTIONS,RedisMem:$REDIS_MEMORY" >> "$METRICS_FILE"
EOF

chmod +x /opt/vedfolnir/scripts/performance_monitor.sh

# Add to cron to run every minute
echo "* * * * * /opt/vedfolnir/scripts/performance_monitor.sh" | sudo crontab -
```

## Rollback Procedures

### Automatic Rollback Triggers

Rollback should be initiated if:
- Application fails to start after deployment
- Critical functionality is broken
- Performance degradation exceeds acceptable thresholds
- Security vulnerabilities are discovered
- Database corruption or data loss occurs

### Rollback Steps

#### 1. Immediate Rollback
```bash
# Stop current application
sudo systemctl stop vedfolnir

# Restore application from backup
sudo rm -rf /opt/vedfolnir_backup
sudo mv /opt/vedfolnir /opt/vedfolnir_failed
sudo tar -xzf /backup/vedfolnir_app_TIMESTAMP.tar.gz -C /

# Restore configuration
sudo cp /backup/.env_TIMESTAMP /opt/vedfolnir/.env

# Restore database
mysql -u vedfolnir_user -p vedfolnir < /backup/vedfolnir_pre_maintenance_TIMESTAMP.sql

# Restore Redis data
sudo systemctl stop redis
sudo cp /backup/redis_TIMESTAMP.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo systemctl start redis

# Start application
sudo systemctl start vedfolnir
```

#### 2. Verify Rollback
```bash
# Test application functionality
curl -f http://localhost:5000/health

# Test database connectivity
python -c "
from app.core.database.core.database_manager import DatabaseManager
from config import Config
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    result = session.execute('SELECT COUNT(*) FROM users').fetchone()
    print(f'User count: {result[0]}')
"

# Test Redis connectivity
redis-cli ping
```

#### 3. Post-Rollback Actions
```bash
# Document rollback reason
echo "$(date): Rollback completed due to: [REASON]" >> /var/log/vedfolnir_rollback.log

# Notify stakeholders
echo "Rollback completed. System restored to previous version." | mail -s "Vedfolnir Rollback Notification" admin@your-domain.com

# Schedule post-mortem
echo "Schedule post-mortem meeting to analyze deployment failure"
```

## Troubleshooting Common Deployment Issues

### Issue 1: Application Won't Start

**Symptoms**: Service fails to start, no response on port 5000

**Diagnosis**:
```bash
# Check service status
sudo systemctl status vedfolnir

# Check logs
sudo journalctl -u vedfolnir -n 50

# Check port availability
sudo netstat -tlnp | grep :5000
```

**Solutions**:
```bash
# Check configuration
python -c "from config import Config; Config()"

# Check dependencies
pip list | grep -E "flask|sqlalchemy|redis"

# Check permissions
sudo chown -R vedfolnir:vedfolnir /opt/vedfolnir
```

### Issue 2: Database Connection Failures

**Symptoms**: Database connection errors in logs

**Diagnosis**:
```bash
# Test database connection
mysql -u vedfolnir_user -p vedfolnir -e "SELECT 1;"

# Check database service
sudo systemctl status mysql
```

**Solutions**:
```bash
# Restart database service
sudo systemctl restart mysql

# Check database configuration
grep -E "^DB_|^DATABASE_" /opt/vedfolnir/.env

# Verify user permissions
mysql -u root -p -e "SHOW GRANTS FOR 'vedfolnir_user'@'localhost';"
```

### Issue 3: Redis Connection Issues

**Symptoms**: Redis connection errors, session issues

**Diagnosis**:
```bash
# Test Redis connection
redis-cli ping

# Check Redis service
sudo systemctl status redis

# Check Redis logs
sudo journalctl -u redis -n 20
```

**Solutions**:
```bash
# Restart Redis service
sudo systemctl restart redis

# Check Redis configuration
sudo nano /etc/redis/redis.conf

# Verify Redis authentication
redis-cli -a your_password ping
```

## Post-Deployment Checklist

### Immediate Post-Deployment (0-2 hours)
- [ ] **Service Status**: All services running and healthy
- [ ] **Functionality**: Core functionality working correctly
- [ ] **Performance**: Response times within acceptable limits
- [ ] **Monitoring**: All monitoring systems operational
- [ ] **Logs**: No critical errors in logs
- [ ] **Security**: Security measures functioning correctly

### Short-term Post-Deployment (2-24 hours)
- [ ] **User Feedback**: No critical user-reported issues
- [ ] **Performance Monitoring**: System performance stable
- [ ] **Error Rates**: Error rates within normal ranges
- [ ] **Resource Usage**: System resources within expected limits
- [ ] **Backup Verification**: Backup systems working correctly
- [ ] **Documentation**: Deployment documented and lessons learned recorded

### Long-term Post-Deployment (1-7 days)
- [ ] **Stability**: System stable with no recurring issues
- [ ] **Performance Optimization**: Performance optimizations applied if needed
- [ ] **User Training**: Users trained on new maintenance mode features
- [ ] **Process Improvement**: Deployment process improvements identified
- [ ] **Documentation Updates**: All documentation updated with deployment changes

## Conclusion

This deployment guide provides comprehensive procedures for deploying the Enhanced Maintenance Mode system to production environments. Following these procedures ensures a smooth deployment with minimal risk and maximum reliability.

Key success factors:
- **Thorough preparation** with comprehensive testing
- **Systematic deployment** following established procedures
- **Comprehensive validation** of all functionality
- **Robust monitoring** and alerting setup
- **Clear rollback procedures** for emergency situations

For additional support during deployment or post-deployment issues, refer to the troubleshooting guide or contact the development team.

Remember: It's better to delay deployment to address issues than to deploy with known problems. Always prioritize system stability and user experience.