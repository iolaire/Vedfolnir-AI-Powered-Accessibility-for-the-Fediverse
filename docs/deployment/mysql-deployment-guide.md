# MySQL Deployment Guide for Vedfolnir

This guide provides comprehensive MySQL deployment procedures and best practices for Vedfolnir, replacing all SQLite-based deployment instructions.

## Table of Contents

1. [MySQL Server Setup](#mysql-server-setup)
2. [Database Configuration](#database-configuration)
3. [Performance Optimization](#performance-optimization)
4. [Security Configuration](#security-configuration)
5. [Backup and Maintenance](#backup-and-maintenance)
6. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
7. [Migration from SQLite](#migration-from-sqlite)

## MySQL Server Setup

### Production MySQL Installation

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install MySQL Server 8.0
sudo apt install mysql-server-8.0

# Start and enable MySQL
sudo systemctl start mysql
sudo systemctl enable mysql

# Secure MySQL installation
sudo mysql_secure_installation
```

#### CentOS/RHEL
```bash
# Install MySQL repository
sudo dnf install mysql80-community-release-el8-1.noarch.rpm

# Install MySQL Server
sudo dnf install mysql-community-server

# Start and enable MySQL
sudo systemctl start mysqld
sudo systemctl enable mysqld

# Get temporary root password
sudo grep 'temporary password' /var/log/mysqld.log

# Secure installation
sudo mysql_secure_installation
```

#### Docker MySQL Setup
```yaml
# docker-compose.yml MySQL service
mysql:
  image: mysql:8.0
  environment:
    MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    MYSQL_DATABASE: vedfolnir
    MYSQL_USER: vedfolnir
    MYSQL_PASSWORD: ${MYSQL_PASSWORD}
  ports:
    - "3306:3306"
  volumes:
    - mysql_data:/var/lib/mysql
    - ./mysql/conf.d:/etc/mysql/conf.d
    - ./mysql/init:/docker-entrypoint-initdb.d
  command: >
    --character-set-server=utf8mb4
    --collation-server=utf8mb4_unicode_ci
    --innodb-buffer-pool-size=1G
    --innodb-log-file-size=256M
    --max-connections=200
    --query-cache-size=0
    --query-cache-type=0
  restart: unless-stopped
```

## Database Configuration

### Database and User Creation

```sql
-- Connect as root
mysql -u root -p

-- Create database with proper character set
CREATE DATABASE vedfolnir 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

-- Create application user
CREATE USER 'vedfolnir'@'localhost' IDENTIFIED BY 'secure_password_here';
CREATE USER 'vedfolnir'@'%' IDENTIFIED BY 'secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir'@'localhost';
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir'@'%';

-- Create read-only user for monitoring
CREATE USER 'vedfolnir_readonly'@'localhost' IDENTIFIED BY 'readonly_password';
GRANT SELECT ON vedfolnir.* TO 'vedfolnir_readonly'@'localhost';

FLUSH PRIVILEGES;
```

### MySQL Configuration File

Create `/etc/mysql/conf.d/vedfolnir.cnf`:

```ini
[mysqld]
# Character set configuration
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# InnoDB Configuration
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_log_buffer_size = 16M
innodb_flush_log_at_trx_commit = 2
innodb_file_per_table = 1

# Connection settings
max_connections = 200
max_connect_errors = 1000
connect_timeout = 60
wait_timeout = 28800
interactive_timeout = 28800

# Query cache (disabled for MySQL 8.0+)
query_cache_size = 0
query_cache_type = 0

# Logging
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
log_queries_not_using_indexes = 1

# Binary logging for replication
log-bin = mysql-bin
binlog_format = ROW
expire_logs_days = 7

# Security
local_infile = 0
```

### Environment Configuration

Update `.env` file:

```bash
# MySQL Database Configuration
DATABASE_URL=mysql+pymysql://vedfolnir:secure_password_here@localhost:3306/vedfolnir?charset=utf8mb4

# Connection pool settings
DATABASE_POOL_SIZE=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
DATABASE_POOL_PRE_PING=true

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_SESSION_PREFIX=vedfolnir:session:
REDIS_SESSION_TIMEOUT=7200

# MySQL-specific settings
MYSQL_CHARSET=utf8mb4
MYSQL_COLLATION=utf8mb4_unicode_ci
MYSQL_ENGINE=InnoDB
```

## Performance Optimization

### MySQL Performance Tuning

```sql
-- Check current configuration
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'max_connections';

-- Monitor performance
SHOW ENGINE INNODB STATUS\G
SHOW PROCESSLIST;
SELECT * FROM performance_schema.events_waits_summary_global_by_event_name 
WHERE event_name LIKE 'wait/io%' ORDER BY sum_timer_wait DESC LIMIT 10;
```

### Index Optimization

```sql
-- Check for missing indexes
SELECT DISTINCT
    CONCAT('ALTER TABLE ', table_schema, '.', table_name, 
           ' ADD INDEX idx_', column_name, ' (', column_name, ');') AS add_index
FROM information_schema.columns 
WHERE table_schema = 'vedfolnir' 
  AND column_name IN ('user_id', 'platform_id', 'created_at', 'updated_at');

-- Analyze table usage
ANALYZE TABLE users, platforms, posts, captions;

-- Check index usage
SELECT 
    table_name,
    index_name,
    cardinality,
    sub_part,
    packed,
    nullable,
    index_type
FROM information_schema.statistics 
WHERE table_schema = 'vedfolnir'
ORDER BY table_name, seq_in_index;
```

### Connection Pool Configuration

```python
# In config.py - MySQL connection pool settings
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'pool_timeout': 30,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 30,
    'echo': False,  # Set to True for SQL debugging
    'connect_args': {
        'charset': 'utf8mb4',
        'connect_timeout': 60,
        'read_timeout': 30,
        'write_timeout': 30,
    }
}
```

## Security Configuration

### MySQL Security Hardening

```sql
-- Remove anonymous users
DELETE FROM mysql.user WHERE User='';

-- Remove remote root access
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');

-- Remove test database
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';

-- Update root password policy
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'very_secure_root_password';

-- Set password validation
INSTALL COMPONENT 'file://component_validate_password';
SET GLOBAL validate_password.policy = STRONG;
SET GLOBAL validate_password.length = 12;

FLUSH PRIVILEGES;
```

### SSL/TLS Configuration

```bash
# Generate SSL certificates for MySQL
sudo mysql_ssl_rsa_setup --uid=mysql

# Update MySQL configuration
echo "
[mysqld]
ssl-ca=/var/lib/mysql/ca.pem
ssl-cert=/var/lib/mysql/server-cert.pem
ssl-key=/var/lib/mysql/server-key.pem
require_secure_transport=ON
" | sudo tee -a /etc/mysql/conf.d/ssl.cnf

# Restart MySQL
sudo systemctl restart mysql

# Update user to require SSL
ALTER USER 'vedfolnir'@'%' REQUIRE SSL;
FLUSH PRIVILEGES;
```

### Firewall Configuration

```bash
# UFW firewall rules
sudo ufw allow from 10.0.0.0/8 to any port 3306  # Internal network only
sudo ufw deny 3306  # Deny external access

# iptables rules
sudo iptables -A INPUT -p tcp --dport 3306 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 3306 -j DROP
```

## Backup and Maintenance

### Automated Backup Script

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-mysql-backup.sh

set -euo pipefail

# Configuration
BACKUP_DIR="/backup/vedfolnir/mysql"
RETENTION_DAYS=30
DB_NAME="vedfolnir"
DB_USER="vedfolnir"
DB_PASSWORD="${MYSQL_PASSWORD}"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Full database backup
mysqldump \
    --user="$DB_USER" \
    --password="$DB_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --hex-blob \
    --opt \
    --compress \
    "$DB_NAME" | gzip > "$BACKUP_DIR/vedfolnir_full_$DATE.sql.gz"

# Schema-only backup
mysqldump \
    --user="$DB_USER" \
    --password="$DB_PASSWORD" \
    --no-data \
    --routines \
    --triggers \
    --events \
    "$DB_NAME" > "$BACKUP_DIR/vedfolnir_schema_$DATE.sql"

# Binary log backup (if enabled)
if [ -f /var/lib/mysql/mysql-bin.index ]; then
    cp /var/lib/mysql/mysql-bin.* "$BACKUP_DIR/" 2>/dev/null || true
fi

# Cleanup old backups
find "$BACKUP_DIR" -name "vedfolnir_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "vedfolnir_*.sql" -mtime +$RETENTION_DAYS -delete

# Log backup completion
echo "$(date): MySQL backup completed successfully" >> "$BACKUP_DIR/backup.log"

# Verify backup integrity
if gunzip -t "$BACKUP_DIR/vedfolnir_full_$DATE.sql.gz"; then
    echo "$(date): Backup integrity verified" >> "$BACKUP_DIR/backup.log"
else
    echo "$(date): ERROR - Backup integrity check failed" >> "$BACKUP_DIR/backup.log"
    exit 1
fi
```

### Backup Automation

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /usr/local/bin/vedfolnir-mysql-backup.sh

# Weekly full backup with verification
0 3 * * 0 /usr/local/bin/vedfolnir-mysql-backup.sh && /usr/local/bin/verify-backup.sh
```

### Database Maintenance

```sql
-- Weekly maintenance queries
-- Optimize tables
OPTIMIZE TABLE users, platforms, posts, captions, sessions;

-- Analyze tables for query optimization
ANALYZE TABLE users, platforms, posts, captions, sessions;

-- Check table integrity
CHECK TABLE users, platforms, posts, captions, sessions;

-- Update table statistics
FLUSH TABLES;
```

## Monitoring and Troubleshooting

### Performance Monitoring

```bash
#!/bin/bash
# MySQL performance monitoring script

# Connection monitoring
mysql -u vedfolnir_readonly -p -e "
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
mysql -u vedfolnir_readonly -p -e "
SELECT 
    schema_name,
    digest_text,
    count_star,
    avg_timer_wait/1000000000 as avg_time_ms,
    sum_timer_wait/1000000000 as total_time_ms
FROM performance_schema.events_statements_summary_by_digest 
WHERE schema_name = 'vedfolnir'
ORDER BY sum_timer_wait DESC 
LIMIT 10;
"

# InnoDB status
mysql -u vedfolnir_readonly -p -e "SHOW ENGINE INNODB STATUS\G" | grep -A 20 "BUFFER POOL AND MEMORY"
```

### Health Check Script

```python
#!/usr/bin/env python3
# mysql_health_check.py

import pymysql
import sys
import os
from datetime import datetime

def check_mysql_health():
    try:
        # Connection parameters
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'vedfolnir'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE', 'vedfolnir'),
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Basic connectivity test
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result[0] != 1:
                raise Exception("Basic connectivity test failed")
            
            # Check table existence
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            required_tables = ['users', 'platforms', 'posts', 'captions']
            existing_tables = [table[0] for table in tables]
            
            for table in required_tables:
                if table not in existing_tables:
                    raise Exception(f"Required table '{table}' not found")
            
            # Check connection pool
            cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
            connections = cursor.fetchone()
            
            cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
            max_connections = cursor.fetchone()
            
            connection_usage = int(connections[1]) / int(max_connections[1]) * 100
            
            if connection_usage > 80:
                print(f"WARNING: High connection usage: {connection_usage:.1f}%")
            
            print(f"MySQL Health Check - {datetime.now()}")
            print(f"✓ Database connectivity: OK")
            print(f"✓ Required tables: OK")
            print(f"✓ Connection usage: {connection_usage:.1f}%")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"MySQL Health Check FAILED: {e}")
        return False

if __name__ == "__main__":
    if not check_mysql_health():
        sys.exit(1)
```

### Common Troubleshooting

```bash
# Check MySQL error logs
sudo tail -f /var/log/mysql/error.log

# Check slow query log
sudo tail -f /var/log/mysql/slow.log

# Monitor real-time connections
watch -n 1 'mysql -u vedfolnir_readonly -p -e "SHOW PROCESSLIST"'

# Check disk space
df -h /var/lib/mysql

# Check MySQL service status
systemctl status mysql

# Test connection from application server
telnet mysql_server_ip 3306

# Check for locked tables
mysql -u vedfolnir_readonly -p -e "SHOW OPEN TABLES WHERE In_use > 0;"

# Monitor InnoDB deadlocks
mysql -u vedfolnir_readonly -p -e "SHOW ENGINE INNODB STATUS\G" | grep -A 10 "LATEST DETECTED DEADLOCK"
```

## Migration from SQLite

### Pre-Migration Checklist

```bash
# 1. Backup existing SQLite database
cp storage/database/vedfolnir.db storage/database/vedfolnir_backup_$(date +%Y%m%d).db

# 2. Verify MySQL setup
python scripts/mysql_migration/verify_mysql_setup.py

# 3. Test MySQL connection
python -c "
from database import get_db_connection
conn = get_db_connection()
print('MySQL connection successful')
conn.close()
"
```

### Migration Execution

```bash
# Run comprehensive migration
python scripts/mysql_migration/migrate_to_mysql.py --backup --verify

# Verify migration results
python scripts/mysql_migration/verify_migration.py

# Update configuration
sed -i 's/sqlite:\/\/\/.*$/mysql+pymysql:\/\/vedfolnir:password@localhost\/vedfolnir?charset=utf8mb4/' .env

# Test application functionality
python scripts/testing/run_comprehensive_tests.py --suite integration
```

### Post-Migration Validation

```bash
# Compare record counts
python -c "
import sqlite3
import pymysql

# SQLite counts
sqlite_conn = sqlite3.connect('storage/database/vedfolnir.db')
sqlite_cursor = sqlite_conn.cursor()

# MySQL counts  
mysql_conn = pymysql.connect(host='localhost', user='vedfolnir', password='password', database='vedfolnir')
mysql_cursor = mysql_conn.cursor()

tables = ['users', 'platforms', 'posts', 'captions']
for table in tables:
    sqlite_cursor.execute(f'SELECT COUNT(*) FROM {table}')
    sqlite_count = sqlite_cursor.fetchone()[0]
    
    mysql_cursor.execute(f'SELECT COUNT(*) FROM {table}')
    mysql_count = mysql_cursor.fetchone()[0]
    
    print(f'{table}: SQLite={sqlite_count}, MySQL={mysql_count}')
    
sqlite_conn.close()
mysql_conn.close()
"
```

This comprehensive MySQL deployment guide ensures a robust, secure, and performant MySQL deployment for Vedfolnir, completely replacing SQLite-based deployment procedures.
