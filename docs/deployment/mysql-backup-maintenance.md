# MySQL Backup and Maintenance Procedures

This document provides comprehensive backup and maintenance procedures for Vedfolnir's MySQL deployment, replacing all SQLite-based backup and maintenance instructions.

## Table of Contents

1. [Backup Strategies](#backup-strategies)
2. [Automated Backup Scripts](#automated-backup-scripts)
3. [Recovery Procedures](#recovery-procedures)
4. [Database Maintenance](#database-maintenance)
5. [Performance Monitoring](#performance-monitoring)
6. [Security Maintenance](#security-maintenance)
7. [Disaster Recovery](#disaster-recovery)

## Backup Strategies

### Backup Types

#### 1. Full Database Backup
Complete backup of all data, schema, and metadata.

```bash
#!/bin/bash
# Full backup with mysqldump
mysqldump \
    --user=vedfolnir \
    --password="$MYSQL_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --hex-blob \
    --opt \
    --compress \
    vedfolnir | gzip > "vedfolnir_full_$(date +%Y%m%d_%H%M%S).sql.gz"
```

#### 2. Incremental Backup
Binary log-based incremental backups.

```bash
#!/bin/bash
# Enable binary logging in MySQL configuration
# Add to /etc/mysql/conf.d/vedfolnir.cnf:
# log-bin = mysql-bin
# binlog_format = ROW
# expire_logs_days = 7

# Flush binary logs
mysql -u vedfolnir -p"$MYSQL_PASSWORD" -e "FLUSH BINARY LOGS;"

# Backup binary logs
cp /var/lib/mysql/mysql-bin.* /backup/vedfolnir/binlogs/
```

#### 3. Schema-Only Backup
Structure backup without data.

```bash
#!/bin/bash
# Schema backup
mysqldump \
    --user=vedfolnir \
    --password="$MYSQL_PASSWORD" \
    --no-data \
    --routines \
    --triggers \
    --events \
    vedfolnir > "vedfolnir_schema_$(date +%Y%m%d_%H%M%S).sql"
```

#### 4. Selective Table Backup
Backup specific tables.

```bash
#!/bin/bash
# Backup critical tables only
mysqldump \
    --user=vedfolnir \
    --password="$MYSQL_PASSWORD" \
    --single-transaction \
    vedfolnir users platforms posts captions > "vedfolnir_critical_$(date +%Y%m%d_%H%M%S).sql"
```

### Backup Schedule Recommendations

| Backup Type | Frequency | Retention | Purpose |
|-------------|-----------|-----------|---------|
| Full Backup | Daily | 30 days | Complete recovery |
| Incremental | Hourly | 7 days | Point-in-time recovery |
| Schema | Weekly | 90 days | Structure recovery |
| Critical Tables | Every 4 hours | 14 days | Fast critical data recovery |

## Automated Backup Scripts

### Comprehensive Backup Script

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-backup-complete.sh

set -euo pipefail

# Configuration
BACKUP_BASE_DIR="/backup/vedfolnir"
MYSQL_USER="vedfolnir"
MYSQL_PASSWORD="${MYSQL_PASSWORD}"
MYSQL_DATABASE="vedfolnir"
REDIS_HOST="localhost"
REDIS_PORT="6379"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directories
mkdir -p "$BACKUP_BASE_DIR"/{mysql,redis,storage,logs}

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$BACKUP_BASE_DIR/backup.log"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Backup verification function
verify_backup() {
    local backup_file="$1"
    if [[ "$backup_file" == *.gz ]]; then
        if gunzip -t "$backup_file" 2>/dev/null; then
            log "Backup verification successful: $backup_file"
            return 0
        else
            error_exit "Backup verification failed: $backup_file"
        fi
    else
        if mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "source $backup_file" --dry-run 2>/dev/null; then
            log "Backup verification successful: $backup_file"
            return 0
        else
            error_exit "Backup verification failed: $backup_file"
        fi
    fi
}

log "Starting comprehensive backup process"

# 1. MySQL Full Backup
log "Creating MySQL full backup"
MYSQL_BACKUP="$BACKUP_BASE_DIR/mysql/vedfolnir_full_$DATE.sql.gz"
mysqldump \
    --user="$MYSQL_USER" \
    --password="$MYSQL_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --hex-blob \
    --opt \
    --compress \
    "$MYSQL_DATABASE" | gzip > "$MYSQL_BACKUP"

verify_backup "$MYSQL_BACKUP"

# 2. MySQL Schema Backup
log "Creating MySQL schema backup"
SCHEMA_BACKUP="$BACKUP_BASE_DIR/mysql/vedfolnir_schema_$DATE.sql"
mysqldump \
    --user="$MYSQL_USER" \
    --password="$MYSQL_PASSWORD" \
    --no-data \
    --routines \
    --triggers \
    --events \
    "$MYSQL_DATABASE" > "$SCHEMA_BACKUP"

# 3. Binary Log Backup (if enabled)
if mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SHOW VARIABLES LIKE 'log_bin'" | grep -q ON; then
    log "Creating binary log backup"
    mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "FLUSH BINARY LOGS;"
    cp /var/lib/mysql/mysql-bin.* "$BACKUP_BASE_DIR/mysql/" 2>/dev/null || true
fi

# 4. Redis Backup
log "Creating Redis backup"
if command -v redis-cli >/dev/null 2>&1; then
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" BGSAVE
    sleep 5  # Wait for background save to complete
    cp /var/lib/redis/dump.rdb "$BACKUP_BASE_DIR/redis/redis_$DATE.rdb" 2>/dev/null || true
fi

# 5. Application Storage Backup
log "Creating storage backup"
if [ -d "/app/storage" ]; then
    tar -czf "$BACKUP_BASE_DIR/storage/storage_$DATE.tar.gz" -C /app storage/
elif [ -d "./storage" ]; then
    tar -czf "$BACKUP_BASE_DIR/storage/storage_$DATE.tar.gz" storage/
fi

# 6. Configuration Backup
log "Creating configuration backup"
if [ -f ".env" ]; then
    cp .env "$BACKUP_BASE_DIR/config_$DATE.env"
fi

# 7. Log Backup
log "Creating log backup"
if [ -d "/app/logs" ]; then
    tar -czf "$BACKUP_BASE_DIR/logs/logs_$DATE.tar.gz" -C /app logs/
elif [ -d "./logs" ]; then
    tar -czf "$BACKUP_BASE_DIR/logs/logs_$DATE.tar.gz" logs/
fi

# 8. Cleanup old backups
log "Cleaning up old backups"
find "$BACKUP_BASE_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_BASE_DIR" -name "*.sql" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_BASE_DIR" -name "*.rdb" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_BASE_DIR" -name "*.env" -mtime +$RETENTION_DAYS -delete

# 9. Backup size and summary
BACKUP_SIZE=$(du -sh "$BACKUP_BASE_DIR" | cut -f1)
log "Backup completed successfully. Total backup size: $BACKUP_SIZE"

# 10. Send notification (optional)
if command -v mail >/dev/null 2>&1; then
    echo "Vedfolnir backup completed successfully at $(date)" | \
    mail -s "Vedfolnir Backup Success" admin@example.com
fi

log "Backup process completed"
```

### Quick Backup Script

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-quick-backup.sh

set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/vedfolnir/quick"
mkdir -p "$BACKUP_DIR"

# Quick MySQL backup
mysqldump -u vedfolnir -p"$MYSQL_PASSWORD" --single-transaction vedfolnir | \
gzip > "$BACKUP_DIR/quick_backup_$DATE.sql.gz"

# Quick Redis backup
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis_quick_$DATE.rdb"

echo "Quick backup completed: $DATE"
```

### Backup Automation

```bash
# Add to crontab (crontab -e)

# Full backup daily at 2 AM
0 2 * * * /usr/local/bin/vedfolnir-backup-complete.sh

# Quick backup every 4 hours
0 */4 * * * /usr/local/bin/vedfolnir-quick-backup.sh

# Schema backup weekly on Sunday at 3 AM
0 3 * * 0 mysqldump -u vedfolnir -p"$MYSQL_PASSWORD" --no-data vedfolnir > /backup/vedfolnir/schema_$(date +\%Y\%m\%d).sql

# Binary log flush every hour
0 * * * * mysql -u vedfolnir -p"$MYSQL_PASSWORD" -e "FLUSH BINARY LOGS;"
```

## Recovery Procedures

### Full Database Recovery

```bash
#!/bin/bash
# Full database recovery procedure

BACKUP_FILE="$1"
MYSQL_USER="vedfolnir"
MYSQL_PASSWORD="$MYSQL_PASSWORD"
MYSQL_DATABASE="vedfolnir"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

echo "Starting database recovery from: $BACKUP_FILE"

# 1. Stop application
systemctl stop vedfolnir || docker-compose stop vedfolnir

# 2. Create backup of current database
mysqldump -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" | \
gzip > "pre_recovery_backup_$(date +%Y%m%d_%H%M%S).sql.gz"

# 3. Drop and recreate database
mysql -u root -p -e "
DROP DATABASE IF EXISTS $MYSQL_DATABASE;
CREATE DATABASE $MYSQL_DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON $MYSQL_DATABASE.* TO '$MYSQL_USER'@'localhost';
FLUSH PRIVILEGES;
"

# 4. Restore from backup
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"
else
    mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < "$BACKUP_FILE"
fi

# 5. Verify restoration
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT 
    table_name,
    table_rows
FROM information_schema.tables 
WHERE table_schema = '$MYSQL_DATABASE'
ORDER BY table_name;
"

# 6. Start application
systemctl start vedfolnir || docker-compose start vedfolnir

echo "Database recovery completed successfully"
```

### Point-in-Time Recovery

```bash
#!/bin/bash
# Point-in-time recovery using binary logs

FULL_BACKUP="$1"
RECOVERY_TIME="$2"  # Format: 'YYYY-MM-DD HH:MM:SS'

if [ -z "$FULL_BACKUP" ] || [ -z "$RECOVERY_TIME" ]; then
    echo "Usage: $0 <full_backup.sql.gz> 'YYYY-MM-DD HH:MM:SS'"
    exit 1
fi

echo "Starting point-in-time recovery to: $RECOVERY_TIME"

# 1. Restore full backup
gunzip -c "$FULL_BACKUP" | mysql -u vedfolnir -p"$MYSQL_PASSWORD" vedfolnir

# 2. Apply binary logs up to recovery time
for binlog in /var/lib/mysql/mysql-bin.*; do
    if [[ "$binlog" == *.index ]]; then
        continue
    fi
    
    mysqlbinlog --stop-datetime="$RECOVERY_TIME" "$binlog" | \
    mysql -u vedfolnir -p"$MYSQL_PASSWORD" vedfolnir
done

echo "Point-in-time recovery completed"
```

### Selective Table Recovery

```bash
#!/bin/bash
# Recover specific tables

BACKUP_FILE="$1"
shift
TABLES="$@"

if [ -z "$BACKUP_FILE" ] || [ -z "$TABLES" ]; then
    echo "Usage: $0 <backup_file.sql.gz> table1 table2 ..."
    exit 1
fi

echo "Recovering tables: $TABLES"

# Extract and restore specific tables
gunzip -c "$BACKUP_FILE" | \
mysql -u vedfolnir -p"$MYSQL_PASSWORD" vedfolnir --one-database \
--tables $TABLES

echo "Table recovery completed"
```

## Database Maintenance

### Daily Maintenance Script

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-daily-maintenance.sh

set -e

MYSQL_USER="vedfolnir"
MYSQL_PASSWORD="$MYSQL_PASSWORD"
MYSQL_DATABASE="vedfolnir"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Starting daily maintenance"

# 1. Optimize tables
log "Optimizing tables"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
OPTIMIZE TABLE users, platforms, posts, captions, sessions;
"

# 2. Analyze tables
log "Analyzing tables"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
ANALYZE TABLE users, platforms, posts, captions, sessions;
"

# 3. Check table integrity
log "Checking table integrity"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
CHECK TABLE users, platforms, posts, captions, sessions;
"

# 4. Update table statistics
log "Updating table statistics"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
FLUSH TABLES;
"

# 5. Clean up old sessions (older than 7 days)
log "Cleaning up old sessions"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
DELETE FROM sessions WHERE created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);
"

# 6. Clean up old logs (older than 30 days)
log "Cleaning up old logs"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
DELETE FROM audit_logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
"

# 7. Update index statistics
log "Updating index statistics"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT 
    table_name,
    index_name,
    cardinality
FROM information_schema.statistics 
WHERE table_schema = '$MYSQL_DATABASE'
ORDER BY table_name, seq_in_index;
"

log "Daily maintenance completed"
```

### Weekly Maintenance Script

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-weekly-maintenance.sh

set -e

MYSQL_USER="vedfolnir"
MYSQL_PASSWORD="$MYSQL_PASSWORD"
MYSQL_DATABASE="vedfolnir"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Starting weekly maintenance"

# 1. Rebuild indexes
log "Rebuilding indexes"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
ALTER TABLE users ENGINE=InnoDB;
ALTER TABLE platforms ENGINE=InnoDB;
ALTER TABLE posts ENGINE=InnoDB;
ALTER TABLE captions ENGINE=InnoDB;
"

# 2. Defragment tables
log "Defragmenting tables"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
OPTIMIZE TABLE users, platforms, posts, captions;
"

# 3. Update MySQL statistics
log "Updating MySQL statistics"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
FLUSH TABLES WITH READ LOCK;
UNLOCK TABLES;
"

# 4. Check for unused indexes
log "Checking for unused indexes"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT 
    s.table_name,
    s.index_name,
    s.cardinality,
    CASE 
        WHEN s.cardinality = 0 THEN 'Consider dropping'
        WHEN s.cardinality < 100 THEN 'Low cardinality'
        ELSE 'OK'
    END as recommendation
FROM information_schema.statistics s
WHERE s.table_schema = '$MYSQL_DATABASE'
  AND s.index_name != 'PRIMARY'
ORDER BY s.cardinality;
"

log "Weekly maintenance completed"
```

## Performance Monitoring

### Performance Monitoring Script

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-performance-monitor.sh

MYSQL_USER="vedfolnir_readonly"
MYSQL_PASSWORD="$MYSQL_READONLY_PASSWORD"

# Connection statistics
echo "=== Connection Statistics ==="
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
SELECT 
    VARIABLE_NAME,
    VARIABLE_VALUE
FROM performance_schema.global_status 
WHERE VARIABLE_NAME IN (
    'Connections',
    'Max_used_connections',
    'Threads_connected',
    'Threads_running',
    'Aborted_connects',
    'Aborted_clients'
);
"

# Query performance
echo "=== Top 10 Slowest Queries ==="
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
SELECT 
    schema_name,
    LEFT(digest_text, 100) as query_sample,
    count_star as executions,
    ROUND(avg_timer_wait/1000000000, 2) as avg_time_seconds,
    ROUND(sum_timer_wait/1000000000, 2) as total_time_seconds
FROM performance_schema.events_statements_summary_by_digest 
WHERE schema_name = 'vedfolnir'
ORDER BY sum_timer_wait DESC 
LIMIT 10;
"

# Table statistics
echo "=== Table Statistics ==="
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" vedfolnir -e "
SELECT 
    table_name,
    table_rows,
    ROUND(data_length/1024/1024, 2) as data_mb,
    ROUND(index_length/1024/1024, 2) as index_mb,
    ROUND((data_length + index_length)/1024/1024, 2) as total_mb
FROM information_schema.tables 
WHERE table_schema = 'vedfolnir'
ORDER BY (data_length + index_length) DESC;
"

# InnoDB status
echo "=== InnoDB Buffer Pool Status ==="
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
SELECT 
    VARIABLE_NAME,
    VARIABLE_VALUE
FROM performance_schema.global_status 
WHERE VARIABLE_NAME LIKE 'Innodb_buffer_pool%'
ORDER BY VARIABLE_NAME;
"
```

### Automated Performance Alerts

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-performance-alerts.sh

MYSQL_USER="vedfolnir_readonly"
MYSQL_PASSWORD="$MYSQL_READONLY_PASSWORD"
ALERT_EMAIL="admin@example.com"

# Check connection usage
CONNECTION_USAGE=$(mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -N -e "
SELECT ROUND(
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Threads_connected') /
    (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections') * 100
);
")

if [ "$CONNECTION_USAGE" -gt 80 ]; then
    echo "ALERT: High connection usage: ${CONNECTION_USAGE}%" | \
    mail -s "Vedfolnir MySQL Alert: High Connection Usage" "$ALERT_EMAIL"
fi

# Check slow queries
SLOW_QUERIES=$(mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -N -e "
SELECT COUNT(*) FROM performance_schema.events_statements_summary_by_digest 
WHERE schema_name = 'vedfolnir' AND avg_timer_wait/1000000000 > 5;
")

if [ "$SLOW_QUERIES" -gt 10 ]; then
    echo "ALERT: ${SLOW_QUERIES} slow queries detected" | \
    mail -s "Vedfolnir MySQL Alert: Slow Queries" "$ALERT_EMAIL"
fi

# Check disk space
DISK_USAGE=$(df /var/lib/mysql | awk 'NR==2 {print $5}' | sed 's/%//')

if [ "$DISK_USAGE" -gt 85 ]; then
    echo "ALERT: MySQL disk usage: ${DISK_USAGE}%" | \
    mail -s "Vedfolnir MySQL Alert: High Disk Usage" "$ALERT_EMAIL"
fi
```

## Security Maintenance

### Security Audit Script

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-security-audit.sh

MYSQL_USER="root"
MYSQL_PASSWORD="$MYSQL_ROOT_PASSWORD"

echo "=== MySQL Security Audit ==="

# Check for users without passwords
echo "Users without passwords:"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
SELECT user, host FROM mysql.user WHERE authentication_string = '';
"

# Check for users with weak passwords
echo "Users with potential weak passwords:"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
SELECT user, host FROM mysql.user 
WHERE LENGTH(authentication_string) < 40 AND authentication_string != '';
"

# Check for unnecessary privileges
echo "Users with excessive privileges:"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
SELECT user, host, 
       CASE WHEN Super_priv = 'Y' THEN 'SUPER' ELSE '' END as super_priv,
       CASE WHEN File_priv = 'Y' THEN 'FILE' ELSE '' END as file_priv,
       CASE WHEN Process_priv = 'Y' THEN 'PROCESS' ELSE '' END as process_priv
FROM mysql.user 
WHERE Super_priv = 'Y' OR File_priv = 'Y' OR Process_priv = 'Y';
"

# Check SSL configuration
echo "SSL Configuration:"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
SHOW VARIABLES LIKE 'have_ssl';
SHOW VARIABLES LIKE 'ssl_%';
"
```

### Password Rotation Script

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-rotate-passwords.sh

set -e

NEW_PASSWORD=$(openssl rand -base64 32)
MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD"

echo "Rotating MySQL password for vedfolnir user"

# Update password in MySQL
mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "
ALTER USER 'vedfolnir'@'localhost' IDENTIFIED BY '$NEW_PASSWORD';
ALTER USER 'vedfolnir'@'%' IDENTIFIED BY '$NEW_PASSWORD';
FLUSH PRIVILEGES;
"

# Update environment file
sed -i.bak "s/MYSQL_PASSWORD=.*/MYSQL_PASSWORD=$NEW_PASSWORD/" .env

# Restart application
systemctl restart vedfolnir || docker-compose restart vedfolnir

echo "Password rotation completed. New password stored in .env file."
echo "Please update any external systems that use this password."
```

## Disaster Recovery

### Disaster Recovery Plan

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-disaster-recovery.sh

set -e

RECOVERY_SITE="$1"
BACKUP_LOCATION="$2"

if [ -z "$RECOVERY_SITE" ] || [ -z "$BACKUP_LOCATION" ]; then
    echo "Usage: $0 <recovery_site> <backup_location>"
    echo "Example: $0 dr-server.example.com /backup/vedfolnir/latest"
    exit 1
fi

echo "Starting disaster recovery to: $RECOVERY_SITE"

# 1. Prepare recovery site
ssh "$RECOVERY_SITE" "
    # Install MySQL and Redis
    apt update && apt install -y mysql-server redis-server
    
    # Create database and user
    mysql -u root -e \"
        CREATE DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        CREATE USER 'vedfolnir'@'localhost' IDENTIFIED BY '$MYSQL_PASSWORD';
        GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir'@'localhost';
        FLUSH PRIVILEGES;
    \"
"

# 2. Transfer backups
echo "Transferring backups to recovery site"
rsync -avz "$BACKUP_LOCATION/" "$RECOVERY_SITE:/tmp/vedfolnir-recovery/"

# 3. Restore database
ssh "$RECOVERY_SITE" "
    cd /tmp/vedfolnir-recovery
    gunzip -c mysql/vedfolnir_full_*.sql.gz | mysql -u vedfolnir -p'$MYSQL_PASSWORD' vedfolnir
"

# 4. Restore Redis data
ssh "$RECOVERY_SITE" "
    systemctl stop redis-server
    cp /tmp/vedfolnir-recovery/redis/redis_*.rdb /var/lib/redis/dump.rdb
    chown redis:redis /var/lib/redis/dump.rdb
    systemctl start redis-server
"

# 5. Deploy application
ssh "$RECOVERY_SITE" "
    # Clone application
    git clone <repository-url> /opt/vedfolnir
    cd /opt/vedfolnir
    
    # Setup environment
    cp /tmp/vedfolnir-recovery/config_*.env .env
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Start application
    systemctl enable vedfolnir
    systemctl start vedfolnir
"

echo "Disaster recovery completed on: $RECOVERY_SITE"
echo "Please verify application functionality and update DNS records."
```

This comprehensive backup and maintenance guide ensures robust data protection and optimal performance for Vedfolnir's MySQL deployment.
