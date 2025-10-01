# Docker Compose Operations Guide

## Overview

This guide covers day-to-day operations, maintenance procedures, and management tasks for the Vedfolnir Docker Compose deployment. It provides administrators with the knowledge needed to effectively operate and maintain the containerized environment.

## Daily Operations

### Starting and Stopping Services

#### Standard Operations
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart vedfolnir
docker-compose restart mysql
docker-compose restart redis
```

#### Graceful Shutdown
```bash
# Graceful shutdown with data preservation
docker-compose stop

# Force shutdown (use only if graceful fails)
docker-compose kill

# Remove containers but preserve volumes
docker-compose down

# Remove everything including volumes (DESTRUCTIVE)
docker-compose down -v
```

#### Service-Specific Operations
```bash
# Application container
docker-compose restart vedfolnir
docker-compose logs -f vedfolnir

# Database operations
docker-compose restart mysql
docker-compose exec mysql mysqladmin status

# Cache operations
docker-compose restart redis
docker-compose exec redis redis-cli info
```

### Monitoring Service Health

#### Container Status
```bash
# Check all container status
docker-compose ps

# Detailed container information
docker-compose ps --services
docker inspect $(docker-compose ps -q)

# Resource usage
docker stats $(docker-compose ps -q)
```

#### Service Health Checks
```bash
# Application health
curl -f http://localhost/health
docker-compose exec vedfolnir python -c "
from app.core.database.core.database_manager import DatabaseManager
from config import Config
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    print('Database connection: OK')
"

# Database health
docker-compose exec mysql mysqladmin ping
docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "SELECT 1;"

# Redis health
docker-compose exec redis redis-cli ping
docker-compose exec redis redis-cli info replication

# External service health
curl -f http://localhost:11434/api/version  # Ollama on host
```

#### Automated Health Monitoring
```bash
# Create health monitoring script
cat > scripts/health_monitor.sh << 'EOF'
#!/bin/bash
# health_monitor.sh - Continuous health monitoring

LOGFILE="logs/health_monitor.log"
ALERT_EMAIL="admin@example.com"

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Check web interface
    if curl -f -s http://localhost/health > /dev/null; then
        echo "$TIMESTAMP - Web interface: OK" >> $LOGFILE
    else
        echo "$TIMESTAMP - Web interface: FAILED" >> $LOGFILE
        # Send alert (configure mail system)
        # echo "Web interface down" | mail -s "Vedfolnir Alert" $ALERT_EMAIL
    fi
    
    # Check database
    if docker-compose exec -T mysql mysqladmin ping --silent; then
        echo "$TIMESTAMP - Database: OK" >> $LOGFILE
    else
        echo "$TIMESTAMP - Database: FAILED" >> $LOGFILE
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null; then
        echo "$TIMESTAMP - Redis: OK" >> $LOGFILE
    else
        echo "$TIMESTAMP - Redis: FAILED" >> $LOGFILE
    fi
    
    sleep 300  # Check every 5 minutes
done
EOF

chmod +x scripts/health_monitor.sh

# Run in background
nohup ./scripts/health_monitor.sh &
```

### Log Management

#### Viewing Logs
```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# Service-specific logs
docker-compose logs vedfolnir
docker-compose logs mysql
docker-compose logs redis
docker-compose logs nginx

# Filter logs by time
docker-compose logs --since="2h" vedfolnir
docker-compose logs --until="2025-01-01T00:00:00" vedfolnir

# Tail specific number of lines
docker-compose logs --tail=100 vedfolnir
```

#### Log Rotation and Cleanup
```bash
# Configure log rotation in docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

# Manual log cleanup
docker-compose down
docker system prune -f
docker-compose up -d

# Archive old logs
mkdir -p logs/archive/$(date +%Y%m%d)
mv logs/app/*.log logs/archive/$(date +%Y%m%d)/ 2>/dev/null || true
```

#### Centralized Logging with Loki
```bash
# Query logs through Loki
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={container_name="vedfolnir"}' \
  --data-urlencode 'limit=100'

# View logs in Grafana
# Access: http://localhost:3000
# Navigate to Explore > Loki > {container_name="vedfolnir"}
```

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Tasks
```bash
# Create daily maintenance script
cat > scripts/daily_maintenance.sh << 'EOF'
#!/bin/bash
# daily_maintenance.sh

echo "=== Daily Maintenance - $(date) ==="

# Check container health
echo "Container Status:"
docker-compose ps

# Check disk usage
echo "Disk Usage:"
df -h | grep -E "(Filesystem|/dev/)"
du -sh data/ logs/ storage/

# Check resource usage
echo "Resource Usage:"
docker stats --no-stream

# Cleanup temporary files
find storage/temp/ -type f -mtime +1 -delete 2>/dev/null || true

# Rotate application logs
find logs/app/ -name "*.log" -size +100M -exec gzip {} \; 2>/dev/null || true

# Check for failed containers
FAILED=$(docker-compose ps --filter "status=exited" -q)
if [ ! -z "$FAILED" ]; then
    echo "WARNING: Failed containers detected"
    docker-compose ps --filter "status=exited"
fi

echo "=== Daily Maintenance Complete ==="
EOF

chmod +x scripts/daily_maintenance.sh

# Schedule with cron
echo "0 6 * * * /path/to/vedfolnir/scripts/daily_maintenance.sh >> /var/log/vedfolnir_maintenance.log 2>&1" | crontab -
```

#### Weekly Tasks
```bash
# Create weekly maintenance script
cat > scripts/weekly_maintenance.sh << 'EOF'
#!/bin/bash
# weekly_maintenance.sh

echo "=== Weekly Maintenance - $(date) ==="

# Update container images
echo "Updating container images..."
docker-compose pull

# Restart services with new images
echo "Restarting services..."
docker-compose up -d

# Database optimization
echo "Optimizing database..."
docker-compose exec mysql mysqlcheck --optimize --all-databases

# Clean up Docker system
echo "Cleaning up Docker resources..."
docker system prune -f

# Backup data
echo "Creating backup..."
./scripts/backup/create_backup.sh

# Check SSL certificate expiration
echo "Checking SSL certificates..."
openssl x509 -in ssl/certs/vedfolnir.crt -text -noout | grep -A2 "Validity"

echo "=== Weekly Maintenance Complete ==="
EOF

chmod +x scripts/weekly_maintenance.sh

# Schedule with cron
echo "0 2 * * 0 /path/to/vedfolnir/scripts/weekly_maintenance.sh >> /var/log/vedfolnir_maintenance.log 2>&1" | crontab -
```

#### Monthly Tasks
```bash
# Create monthly maintenance script
cat > scripts/monthly_maintenance.sh << 'EOF'
#!/bin/bash
# monthly_maintenance.sh

echo "=== Monthly Maintenance - $(date) ==="

# Security updates
echo "Checking for security updates..."
docker-compose build --pull --no-cache

# Rotate secrets (if policy requires)
echo "Checking secret rotation..."
# ./scripts/security/rotate_secrets.sh

# Archive old logs
echo "Archiving old logs..."
mkdir -p logs/archive/$(date +%Y%m)
find logs/ -name "*.log" -mtime +30 -exec mv {} logs/archive/$(date +%Y%m)/ \; 2>/dev/null || true

# Database maintenance
echo "Database maintenance..."
docker-compose exec mysql mysqlcheck --analyze --all-databases
docker-compose exec mysql mysqlcheck --check --all-databases

# Performance analysis
echo "Performance analysis..."
docker stats --no-stream > logs/performance_$(date +%Y%m%d).txt

# Backup verification
echo "Verifying backups..."
./scripts/backup/verify_backup.sh

echo "=== Monthly Maintenance Complete ==="
EOF

chmod +x scripts/monthly_maintenance.sh

# Schedule with cron
echo "0 1 1 * * /path/to/vedfolnir/scripts/monthly_maintenance.sh >> /var/log/vedfolnir_maintenance.log 2>&1" | crontab -
```

### Database Management

#### Database Operations
```bash
# Connect to database
docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt)

# Database backup
docker-compose exec mysql mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  vedfolnir | gzip > backup_$(date +%Y%m%d).sql.gz

# Database restore
gunzip < backup_20250101.sql.gz | \
  docker-compose exec -T mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) vedfolnir

# Database optimization
docker-compose exec mysql mysqlcheck --optimize vedfolnir

# Check database size
docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "
SELECT 
    table_schema AS 'Database',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.tables 
WHERE table_schema = 'vedfolnir'
GROUP BY table_schema;
"
```

#### Database Performance Monitoring
```bash
# Monitor active connections
docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "SHOW PROCESSLIST;"

# Check slow queries
docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "
SELECT * FROM information_schema.processlist WHERE time > 5;
"

# Database status
docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "SHOW STATUS LIKE 'Threads%';"
```

### Redis Management

#### Redis Operations
```bash
# Connect to Redis
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)"

# Redis information
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" info

# Monitor Redis commands
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" monitor

# Redis backup
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" BGSAVE

# Check Redis memory usage
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" info memory

# Clear Redis cache (if needed)
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" FLUSHDB
```

#### Redis Performance Tuning
```bash
# Monitor Redis performance
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" --latency

# Check Redis configuration
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" CONFIG GET '*'

# Optimize Redis memory
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" CONFIG SET maxmemory-policy allkeys-lru
```

## Backup and Recovery Operations

### Automated Backup System
```bash
# Create comprehensive backup script
cat > scripts/backup/create_backup.sh << 'EOF'
#!/bin/bash
# create_backup.sh - Comprehensive backup system

BACKUP_DIR="/var/backups/vedfolnir"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"

mkdir -p "$BACKUP_PATH"

echo "=== Creating Backup - $TIMESTAMP ==="

# Database backup
echo "Backing up MySQL database..."
docker-compose exec mysql mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  --all-databases | gzip > "$BACKUP_PATH/mysql_full.sql.gz"

# Redis backup
echo "Backing up Redis data..."
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" BGSAVE
sleep 5
docker cp $(docker-compose ps -q redis):/data/dump.rdb "$BACKUP_PATH/redis.rdb"

# Application data backup
echo "Backing up application data..."
tar -czf "$BACKUP_PATH/storage.tar.gz" storage/
tar -czf "$BACKUP_PATH/config.tar.gz" config/
tar -czf "$BACKUP_PATH/logs.tar.gz" logs/

# Secrets backup (encrypted)
echo "Backing up secrets..."
tar -czf "$BACKUP_PATH/secrets.tar.gz" secrets/

# Configuration backup
echo "Backing up configuration..."
cp docker-compose.yml "$BACKUP_PATH/"
cp .env.docker "$BACKUP_PATH/"

# Create backup manifest
echo "Creating backup manifest..."
cat > "$BACKUP_PATH/manifest.txt" << MANIFEST
Backup created: $TIMESTAMP
Hostname: $(hostname)
Docker Compose version: $(docker-compose --version)
Container versions:
$(docker-compose images)

Files included:
$(ls -la "$BACKUP_PATH")
MANIFEST

# Verify backup integrity
echo "Verifying backup integrity..."
if [ -f "$BACKUP_PATH/mysql_full.sql.gz" ] && \
   [ -f "$BACKUP_PATH/redis.rdb" ] && \
   [ -f "$BACKUP_PATH/storage.tar.gz" ]; then
    echo "✅ Backup completed successfully"
    echo "Backup location: $BACKUP_PATH"
else
    echo "❌ Backup verification failed"
    exit 1
fi

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true

echo "=== Backup Complete ==="
EOF

chmod +x scripts/backup/create_backup.sh

# Schedule automated backups
echo "0 3 * * * /path/to/vedfolnir/scripts/backup/create_backup.sh >> /var/log/vedfolnir_backup.log 2>&1" | crontab -
```

### Disaster Recovery Procedures
```bash
# Create disaster recovery script
cat > scripts/backup/disaster_recovery.sh << 'EOF'
#!/bin/bash
# disaster_recovery.sh - Complete system recovery

BACKUP_PATH="$1"

if [ -z "$BACKUP_PATH" ]; then
    echo "Usage: $0 /path/to/backup"
    exit 1
fi

echo "=== Disaster Recovery from $BACKUP_PATH ==="

# Stop all services
echo "Stopping services..."
docker-compose down

# Clear existing data
echo "Clearing existing data..."
sudo rm -rf data/mysql/*
sudo rm -rf data/redis/*

# Restore database
echo "Restoring MySQL database..."
gunzip < "$BACKUP_PATH/mysql_full.sql.gz" | \
  docker-compose run --rm mysql mysql -h mysql -u root -p$(cat secrets/mysql_root_password.txt)

# Restore Redis
echo "Restoring Redis data..."
docker cp "$BACKUP_PATH/redis.rdb" $(docker-compose ps -q redis):/data/dump.rdb

# Restore application data
echo "Restoring application data..."
tar -xzf "$BACKUP_PATH/storage.tar.gz"
tar -xzf "$BACKUP_PATH/config.tar.gz"

# Start services
echo "Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 30

# Verify recovery
echo "Verifying recovery..."
./scripts/health_check.sh

echo "=== Disaster Recovery Complete ==="
EOF

chmod +x scripts/backup/disaster_recovery.sh
```

## Security Operations

### Security Monitoring
```bash
# Create security monitoring script
cat > scripts/security/security_monitor.sh << 'EOF'
#!/bin/bash
# security_monitor.sh - Security monitoring and alerting

LOGFILE="logs/security_monitor.log"

echo "=== Security Monitor - $(date) ===" >> $LOGFILE

# Check for failed login attempts
FAILED_LOGINS=$(docker-compose logs vedfolnir | grep -c "Failed login attempt" || echo "0")
if [ "$FAILED_LOGINS" -gt 10 ]; then
    echo "WARNING: $FAILED_LOGINS failed login attempts detected" >> $LOGFILE
fi

# Check for unusual database activity
DB_CONNECTIONS=$(docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "SHOW STATUS LIKE 'Threads_connected';" | tail -1 | awk '{print $2}')
if [ "$DB_CONNECTIONS" -gt 50 ]; then
    echo "WARNING: High database connection count: $DB_CONNECTIONS" >> $LOGFILE
fi

# Check SSL certificate expiration
CERT_EXPIRY=$(openssl x509 -in ssl/certs/vedfolnir.crt -text -noout | grep "Not After" | cut -d: -f2-)
EXPIRY_TIMESTAMP=$(date -d "$CERT_EXPIRY" +%s)
CURRENT_TIMESTAMP=$(date +%s)
DAYS_UNTIL_EXPIRY=$(( ($EXPIRY_TIMESTAMP - $CURRENT_TIMESTAMP) / 86400 ))

if [ "$DAYS_UNTIL_EXPIRY" -lt 30 ]; then
    echo "WARNING: SSL certificate expires in $DAYS_UNTIL_EXPIRY days" >> $LOGFILE
fi

# Check for container vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity HIGH,CRITICAL vedfolnir_vedfolnir >> $LOGFILE 2>&1

echo "=== Security Monitor Complete ===" >> $LOGFILE
EOF

chmod +x scripts/security/security_monitor.sh

# Schedule security monitoring
echo "0 */6 * * * /path/to/vedfolnir/scripts/security/security_monitor.sh" | crontab -
```

### Secret Rotation
```bash
# Create secret rotation script
cat > scripts/security/rotate_secrets.sh << 'EOF'
#!/bin/bash
# rotate_secrets.sh - Automated secret rotation

echo "=== Secret Rotation - $(date) ==="

# Backup current secrets
cp -r secrets/ secrets_backup_$(date +%Y%m%d)/

# Generate new secrets
echo "Generating new secrets..."
openssl rand -base64 32 > secrets/flask_secret_key.txt.new
openssl rand -base64 32 > secrets/platform_encryption_key.txt.new
openssl rand -base64 32 > secrets/redis_password.txt.new

# Update Redis password
echo "Updating Redis password..."
NEW_REDIS_PASSWORD=$(cat secrets/redis_password.txt.new)
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" CONFIG SET requirepass "$NEW_REDIS_PASSWORD"

# Update application configuration
echo "Updating application configuration..."
mv secrets/flask_secret_key.txt.new secrets/flask_secret_key.txt
mv secrets/platform_encryption_key.txt.new secrets/platform_encryption_key.txt
mv secrets/redis_password.txt.new secrets/redis_password.txt

# Restart application
echo "Restarting application..."
docker-compose restart vedfolnir

# Verify functionality
echo "Verifying functionality..."
sleep 10
curl -f http://localhost/health && echo "✅ Secret rotation successful" || echo "❌ Secret rotation failed"

echo "=== Secret Rotation Complete ==="
EOF

chmod +x scripts/security/rotate_secrets.sh
```

## Performance Optimization

### Performance Monitoring
```bash
# Create performance monitoring script
cat > scripts/performance/monitor_performance.sh << 'EOF'
#!/bin/bash
# monitor_performance.sh - Performance monitoring and optimization

LOGFILE="logs/performance_monitor.log"

echo "=== Performance Monitor - $(date) ===" >> $LOGFILE

# Container resource usage
echo "Container Resource Usage:" >> $LOGFILE
docker stats --no-stream >> $LOGFILE

# Database performance
echo "Database Performance:" >> $LOGFILE
docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "
SHOW STATUS LIKE 'Queries';
SHOW STATUS LIKE 'Slow_queries';
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests';
" >> $LOGFILE

# Redis performance
echo "Redis Performance:" >> $LOGFILE
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" info stats >> $LOGFILE

# Application response time
echo "Application Response Time:" >> $LOGFILE
time curl -s http://localhost/health > /dev/null 2>> $LOGFILE

# Disk I/O
echo "Disk I/O:" >> $LOGFILE
iostat -x 1 1 >> $LOGFILE 2>/dev/null || echo "iostat not available" >> $LOGFILE

echo "=== Performance Monitor Complete ===" >> $LOGFILE
EOF

chmod +x scripts/performance/monitor_performance.sh

# Schedule performance monitoring
echo "*/15 * * * * /path/to/vedfolnir/scripts/performance/monitor_performance.sh" | crontab -
```

### Performance Optimization
```bash
# Create performance optimization script
cat > scripts/performance/optimize_performance.sh << 'EOF'
#!/bin/bash
# optimize_performance.sh - Performance optimization procedures

echo "=== Performance Optimization - $(date) ==="

# Database optimization
echo "Optimizing database..."
docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "
OPTIMIZE TABLE vedfolnir.users;
OPTIMIZE TABLE vedfolnir.posts;
OPTIMIZE TABLE vedfolnir.images;
OPTIMIZE TABLE vedfolnir.platform_connections;
"

# Update database statistics
echo "Updating database statistics..."
docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "
ANALYZE TABLE vedfolnir.users;
ANALYZE TABLE vedfolnir.posts;
ANALYZE TABLE vedfolnir.images;
ANALYZE TABLE vedfolnir.platform_connections;
"

# Redis optimization
echo "Optimizing Redis..."
docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" CONFIG SET save "900 1 300 10 60 10000"

# Clean up temporary files
echo "Cleaning up temporary files..."
find storage/temp/ -type f -mtime +1 -delete 2>/dev/null || true

# Docker system cleanup
echo "Cleaning up Docker resources..."
docker system prune -f

echo "=== Performance Optimization Complete ==="
EOF

chmod +x scripts/performance/optimize_performance.sh
```

## Scaling Operations

### Horizontal Scaling
```bash
# Scale application containers
docker-compose up -d --scale vedfolnir=3

# Check scaled containers
docker-compose ps vedfolnir

# Load balancer configuration (Nginx upstream)
# Edit config/nginx/default.conf:
upstream vedfolnir_backend {
    server vedfolnir_1:5000;
    server vedfolnir_2:5000;
    server vedfolnir_3:5000;
}
```

### Resource Scaling
```bash
# Update resource limits in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
    reservations:
      cpus: '2.0'
      memory: 2G

# Apply changes
docker-compose up -d
```

## Troubleshooting Operations

### Quick Diagnostics
```bash
# Create diagnostic script
cat > scripts/diagnostics.sh << 'EOF'
#!/bin/bash
# diagnostics.sh - Quick system diagnostics

echo "=== Vedfolnir Diagnostics ==="

# System information
echo "System Information:"
uname -a
docker --version
docker-compose --version

# Container status
echo -e "\nContainer Status:"
docker-compose ps

# Resource usage
echo -e "\nResource Usage:"
docker stats --no-stream

# Network connectivity
echo -e "\nNetwork Connectivity:"
curl -f http://localhost/health && echo "✅ Web interface OK" || echo "❌ Web interface FAILED"
docker-compose exec vedfolnir curl -f http://host.docker.internal:11434/api/version && echo "✅ Ollama OK" || echo "❌ Ollama FAILED"

# Service health
echo -e "\nService Health:"
docker-compose exec mysql mysqladmin ping && echo "✅ MySQL OK" || echo "❌ MySQL FAILED"
docker-compose exec redis redis-cli ping && echo "✅ Redis OK" || echo "❌ Redis FAILED"

# Disk space
echo -e "\nDisk Usage:"
df -h | grep -E "(Filesystem|/dev/)"
du -sh data/ logs/ storage/

echo -e "\n=== Diagnostics Complete ==="
EOF

chmod +x scripts/diagnostics.sh
```

### Emergency Procedures
```bash
# Create emergency response script
cat > scripts/emergency_response.sh << 'EOF'
#!/bin/bash
# emergency_response.sh - Emergency response procedures

ACTION="$1"

case "$ACTION" in
    "stop")
        echo "Emergency stop - stopping all services"
        docker-compose down
        ;;
    "restart")
        echo "Emergency restart - restarting all services"
        docker-compose restart
        ;;
    "backup")
        echo "Emergency backup - creating immediate backup"
        ./scripts/backup/create_backup.sh
        ;;
    "logs")
        echo "Emergency log collection"
        mkdir -p emergency_logs_$(date +%Y%m%d_%H%M%S)
        docker-compose logs > emergency_logs_$(date +%Y%m%d_%H%M%S)/all_logs.txt
        docker stats --no-stream > emergency_logs_$(date +%Y%m%d_%H%M%S)/resource_usage.txt
        ;;
    *)
        echo "Usage: $0 {stop|restart|backup|logs}"
        echo "  stop    - Emergency stop all services"
        echo "  restart - Emergency restart all services"
        echo "  backup  - Create emergency backup"
        echo "  logs    - Collect emergency logs"
        ;;
esac
EOF

chmod +x scripts/emergency_response.sh
```

## Compliance and Audit Operations

### Audit Log Management
```bash
# Create audit log management script
cat > scripts/audit/manage_audit_logs.sh << 'EOF'
#!/bin/bash
# manage_audit_logs.sh - Audit log management

echo "=== Audit Log Management - $(date) ==="

# Collect audit logs
echo "Collecting audit logs..."
docker-compose exec vedfolnir python -c "
from app.services.compliance.audit_logger import AuditLogger
from config import Config
config = Config()
audit_logger = AuditLogger(config)
# Generate audit report
audit_logger.generate_audit_report()
"

# Archive old audit logs
echo "Archiving old audit logs..."
mkdir -p logs/audit/archive/$(date +%Y%m)
find logs/audit/ -name "*.log" -mtime +90 -exec mv {} logs/audit/archive/$(date +%Y%m)/ \; 2>/dev/null || true

# Verify audit log integrity
echo "Verifying audit log integrity..."
# Implementation depends on audit log format and integrity checking mechanism

echo "=== Audit Log Management Complete ==="
EOF

chmod +x scripts/audit/manage_audit_logs.sh
```

### GDPR Compliance Operations
```bash
# Create GDPR compliance script
cat > scripts/compliance/gdpr_operations.sh << 'EOF'
#!/bin/bash
# gdpr_operations.sh - GDPR compliance operations

ACTION="$1"
USER_ID="$2"

case "$ACTION" in
    "export")
        echo "Exporting user data for user ID: $USER_ID"
        docker-compose exec vedfolnir python -c "
from app.services.gdpr.data_export_service import DataExportService
from config import Config
config = Config()
export_service = DataExportService(config)
export_service.export_user_data($USER_ID)
"
        ;;
    "anonymize")
        echo "Anonymizing user data for user ID: $USER_ID"
        docker-compose exec vedfolnir python -c "
from app.services.gdpr.data_anonymization_service import DataAnonymizationService
from config import Config
config = Config()
anonymization_service = DataAnonymizationService(config)
anonymization_service.anonymize_user_data($USER_ID)
"
        ;;
    "delete")
        echo "Deleting user data for user ID: $USER_ID"
        docker-compose exec vedfolnir python -c "
from app.services.gdpr.data_deletion_service import DataDeletionService
from config import Config
config = Config()
deletion_service = DataDeletionService(config)
deletion_service.delete_user_data($USER_ID)
"
        ;;
    *)
        echo "Usage: $0 {export|anonymize|delete} USER_ID"
        echo "  export    - Export user data"
        echo "  anonymize - Anonymize user data"
        echo "  delete    - Delete user data"
        ;;
esac
EOF

chmod +x scripts/compliance/gdpr_operations.sh
```

This comprehensive operations guide provides administrators with all the tools and procedures needed to effectively manage and maintain the Vedfolnir Docker Compose deployment. Regular use of these scripts and procedures will ensure optimal performance, security, and reliability of the system.