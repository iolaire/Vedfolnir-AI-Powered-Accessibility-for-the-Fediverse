# MySQL Installation and Setup Guide

This comprehensive guide covers installing, configuring, and optimizing MySQL for Vedfolnir. This replaces all previous SQLite-based setup instructions.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [MySQL Server Installation](#mysql-server-installation)
3. [Database Setup](#database-setup)
4. [Vedfolnir Configuration](#vedfolnir-configuration)
5. [Performance Optimization](#performance-optimization)
6. [Security Configuration](#security-configuration)
7. [Troubleshooting](#troubleshooting)
8. [Migration from SQLite](#migration-from-sqlite)

## Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 2GB RAM (4GB+ recommended for production)
- **Storage**: 10GB+ available space
- **Python**: 3.8 or higher
- **Network**: Internet access for package installation

### Required Software
- MySQL Server 8.0+ (recommended) or MariaDB 10.5+
- Python 3.8+
- pip package manager
- Redis server (for session management)

## MySQL Server Installation

### Ubuntu/Debian

```bash
# Update package index
sudo apt update

# Install MySQL Server
sudo apt install mysql-server mysql-client

# Secure MySQL installation
sudo mysql_secure_installation

# Start and enable MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Verify installation
sudo systemctl status mysql
```

### CentOS/RHEL/Rocky Linux

```bash
# Install MySQL repository
sudo dnf install mysql-server mysql

# Start and enable MySQL service
sudo systemctl start mysqld
sudo systemctl enable mysqld

# Get temporary root password
sudo grep 'temporary password' /var/log/mysqld.log

# Secure MySQL installation
sudo mysql_secure_installation
```

### macOS

**Using Homebrew (Recommended):**
```bash
# Install MySQL
brew install mysql

# Start MySQL service
brew services start mysql

# Secure MySQL installation
mysql_secure_installation
```

**Using MySQL Installer:**
1. Download MySQL Community Server from [mysql.com](https://dev.mysql.com/downloads/mysql/)
2. Run the installer and follow the setup wizard
3. Configure MySQL to start automatically

### Windows

1. **Download MySQL Installer** from [mysql.com](https://dev.mysql.com/downloads/installer/)
2. **Run the installer** and select "Developer Default" setup type
3. **Configure MySQL Server**:
   - Set root password
   - Configure as Windows Service
   - Enable automatic startup
4. **Complete installation** and verify service is running

### Docker (Development/Testing)

```bash
# Run MySQL in Docker container
docker run --name vedfolnir-mysql \
  -e MYSQL_ROOT_PASSWORD=your_secure_password \
  -e MYSQL_DATABASE=vedfolnir \
  -e MYSQL_USER=vedfolnir_user \
  -e MYSQL_PASSWORD=vedfolnir_password \
  -p 3306:3306 \
  -v vedfolnir_mysql_data:/var/lib/mysql \
  -d mysql:8.0

# Verify container is running
docker ps | grep vedfolnir-mysql
```

## Database Setup

### 1. Create Database and User

Connect to MySQL as root and create the Vedfolnir database:

```sql
-- Connect to MySQL
mysql -u root -p

-- Create database
CREATE DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (replace with your preferred credentials)
CREATE USER 'vedfolnir_user'@'localhost' IDENTIFIED BY 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir_user'@'localhost';

-- For remote connections (if needed)
CREATE USER 'vedfolnir_user'@'%' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir_user'@'%';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify database creation
SHOW DATABASES;
USE vedfolnir;
SHOW TABLES;

-- Exit MySQL
EXIT;
```

### 2. Test Database Connection

```bash
# Test connection with new user
mysql -u vedfolnir_user -p vedfolnir

# Test from command line
mysql -u vedfolnir_user -p -e "SELECT 'Connection successful' as status;"
```

### 3. Configure MySQL for Vedfolnir

Create or edit MySQL configuration file:

**Linux/macOS**: `/etc/mysql/mysql.conf.d/vedfolnir.cnf`
**Windows**: Add to `my.ini` in MySQL installation directory

```ini
[mysqld]
# Basic Configuration
default-storage-engine = InnoDB
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# Performance Optimization
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# Connection Settings
max_connections = 200
max_connect_errors = 1000
connect_timeout = 60
wait_timeout = 28800
interactive_timeout = 28800

# Query Cache (MySQL 5.7 and earlier)
# query_cache_type = 1
# query_cache_size = 64M

# Logging
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2

# Binary Logging (for replication/backup)
log-bin = mysql-bin
binlog_format = ROW
expire_logs_days = 7

[mysql]
default-character-set = utf8mb4

[client]
default-character-set = utf8mb4
```

**Restart MySQL after configuration changes:**
```bash
# Linux/macOS
sudo systemctl restart mysql

# macOS with Homebrew
brew services restart mysql

# Windows
net stop mysql80
net start mysql80
```

## Vedfolnir Configuration

### 1. Install Python Dependencies

```bash
# Install MySQL Python connector
pip install pymysql>=1.1.0 cryptography>=3.4.8

# Or install all dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create or update your `.env` file:

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your MySQL configuration
nano .env
```

**Required MySQL Configuration in `.env`:**

```bash
# Database Configuration - MySQL
DATABASE_URL=mysql+pymysql://vedfolnir_user:your_secure_password@localhost/vedfolnir?charset=utf8mb4

# MySQL Connection Pool Settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=50
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_QUERY_LOGGING=false

# Application Configuration
FLASK_SECRET_KEY=your_flask_secret_key_here
PLATFORM_ENCRYPTION_KEY=your_platform_encryption_key_here

# Redis Configuration (for sessions)
REDIS_URL=redis://localhost:6379/0
REDIS_SESSION_PREFIX=vedfolnir:session:
REDIS_SESSION_TIMEOUT=7200

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava:7b

# Security Configuration
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_INPUT_VALIDATION_ENABLED=true
SECURITY_HEADERS_ENABLED=true
SECURITY_SESSION_VALIDATION_ENABLED=true
SECURITY_ADMIN_CHECKS_ENABLED=true

# Caption Generation
CAPTION_MAX_LENGTH=500
CAPTION_OPTIMAL_MIN_LENGTH=150
CAPTION_OPTIMAL_MAX_LENGTH=450
```

### 3. Generate Secure Keys

```bash
# Generate Flask secret key
python3 -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate platform encryption key
python3 -c "from cryptography.fernet import Fernet; print('PLATFORM_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

### 4. Initialize Database Schema

```bash
# Run the application to create tables automatically
python web_app.py

# Or use the database initialization script
python scripts/setup/init_database.py

# Verify tables were created
mysql -u vedfolnir_user -p vedfolnir -e "SHOW TABLES;"
```

### 5. Create Admin User

```bash
# Use the automated setup script (recommended)
python scripts/setup/generate_env_secrets.py

# Or create admin user manually
python scripts/setup/init_admin_user.py
```

### 6. Verify Installation

```bash
# Verify environment setup
python scripts/setup/verify_env_setup.py

# Verify MySQL connection
python scripts/setup/verify_mysql_connection.py

# Run basic tests
python -m pytest tests/test_mysql_connection.py -v
```

## Performance Optimization

### MySQL Server Optimization

#### 1. InnoDB Configuration

```sql
-- Check current InnoDB settings
SHOW VARIABLES LIKE 'innodb%';

-- Optimize buffer pool size (75% of available RAM)
SET GLOBAL innodb_buffer_pool_size = 2147483648; -- 2GB

-- Optimize log file size
-- Note: Requires server restart
-- innodb_log_file_size = 256M (in my.cnf)

-- Check buffer pool usage
SELECT 
  ROUND(A.num * 100.0 / B.num, 2) AS buffer_pool_utilization
FROM 
  (SELECT variable_value AS num FROM information_schema.global_status WHERE variable_name = 'Innodb_buffer_pool_pages_data') A,
  (SELECT variable_value AS num FROM information_schema.global_status WHERE variable_name = 'Innodb_buffer_pool_pages_total') B;
```

#### 2. Query Optimization

```sql
-- Enable slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;

-- Check for queries that need optimization
SELECT 
  query_time,
  lock_time,
  rows_sent,
  rows_examined,
  sql_text
FROM mysql.slow_log
ORDER BY query_time DESC
LIMIT 10;
```

#### 3. Index Optimization

```sql
-- Check index usage
SELECT 
  TABLE_SCHEMA,
  TABLE_NAME,
  INDEX_NAME,
  CARDINALITY
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'vedfolnir'
ORDER BY CARDINALITY DESC;

-- Analyze table statistics
ANALYZE TABLE users, platform_connections, posts, images;

-- Optimize tables
OPTIMIZE TABLE users, platform_connections, posts, images;
```

### Application-Level Optimization

#### 1. Connection Pool Tuning

```python
# In your application configuration
DB_POOL_SIZE = 20          # Number of connections to maintain
DB_MAX_OVERFLOW = 50       # Additional connections when needed
DB_POOL_TIMEOUT = 30       # Timeout for getting connection
DB_POOL_RECYCLE = 3600     # Recycle connections every hour
```

#### 2. Query Optimization

```python
# Use connection pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=50,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True  # Validate connections
)
```

## Security Configuration

### 1. MySQL Security Hardening

```sql
-- Remove anonymous users
DELETE FROM mysql.user WHERE User='';

-- Remove remote root access
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');

-- Remove test database
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';

-- Reload privilege tables
FLUSH PRIVILEGES;
```

### 2. SSL/TLS Configuration

```bash
# Generate SSL certificates (if not using managed MySQL)
sudo mysql_ssl_rsa_setup --uid=mysql

# Verify SSL is enabled
mysql -u root -p -e "SHOW VARIABLES LIKE 'have_ssl';"
```

**Update connection string for SSL:**
```bash
DATABASE_URL=mysql+pymysql://vedfolnir_user:password@localhost/vedfolnir?charset=utf8mb4&ssl_disabled=false
```

### 3. Firewall Configuration

```bash
# Ubuntu/Debian - Allow MySQL port
sudo ufw allow 3306/tcp

# CentOS/RHEL - Allow MySQL port
sudo firewall-cmd --permanent --add-port=3306/tcp
sudo firewall-cmd --reload
```

### 4. User Privilege Management

```sql
-- Create read-only user for monitoring
CREATE USER 'vedfolnir_readonly'@'localhost' IDENTIFIED BY 'readonly_password';
GRANT SELECT ON vedfolnir.* TO 'vedfolnir_readonly'@'localhost';

-- Create backup user
CREATE USER 'vedfolnir_backup'@'localhost' IDENTIFIED BY 'backup_password';
GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER ON vedfolnir.* TO 'vedfolnir_backup'@'localhost';

FLUSH PRIVILEGES;
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused

```bash
# Check if MySQL is running
sudo systemctl status mysql

# Check MySQL port
netstat -tlnp | grep :3306

# Check MySQL error log
sudo tail -f /var/log/mysql/error.log
```

#### 2. Authentication Issues

```sql
-- Check user exists and has correct privileges
SELECT User, Host FROM mysql.user WHERE User = 'vedfolnir_user';
SHOW GRANTS FOR 'vedfolnir_user'@'localhost';

-- Reset user password
ALTER USER 'vedfolnir_user'@'localhost' IDENTIFIED BY 'new_password';
FLUSH PRIVILEGES;
```

#### 3. Character Set Issues

```sql
-- Check database character set
SELECT 
  SCHEMA_NAME,
  DEFAULT_CHARACTER_SET_NAME,
  DEFAULT_COLLATION_NAME
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME = 'vedfolnir';

-- Fix character set if needed
ALTER DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 4. Performance Issues

```sql
-- Check current connections
SHOW PROCESSLIST;

-- Check InnoDB status
SHOW ENGINE INNODB STATUS;

-- Check table sizes
SELECT 
  TABLE_NAME,
  ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'vedfolnir'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
```

### Diagnostic Commands

```bash
# Test MySQL connection
mysql -u vedfolnir_user -p vedfolnir -e "SELECT 'MySQL connection successful' as status;"

# Test Python MySQL connection
python3 -c "
import pymysql
try:
    conn = pymysql.connect(host='localhost', user='vedfolnir_user', password='your_password', database='vedfolnir')
    print('✅ Python MySQL connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
"

# Check Vedfolnir configuration
python scripts/setup/verify_mysql_connection.py

# Run MySQL performance tests
python tests/integration/test_mysql_performance_integration.py
```

## Migration from SQLite

If you're migrating from an existing SQLite installation:

### 1. Backup SQLite Data

```bash
# Backup SQLite database
cp storage/database/vedfolnir.db storage/database/vedfolnir.db.backup

# Export SQLite data
sqlite3 storage/database/vedfolnir.db .dump > vedfolnir_sqlite_export.sql
```

### 2. Data Migration Script

```bash
# Use the automated migration script
python scripts/mysql_migration/migrate_sqlite_to_mysql.py

# Or follow the manual migration guide
# See: docs/mysql_migration_guide.md
```

### 3. Verify Migration

```bash
# Compare record counts
python scripts/mysql_migration/verify_migration.py

# Run comprehensive tests
python -m pytest tests/integration/ -v
```

### 4. Cleanup SQLite Files

```bash
# Remove SQLite files after successful migration
python scripts/mysql_migration/cleanup_sqlite_files.py

# Or manually remove
rm -rf storage/database/
```

## Next Steps

After completing the MySQL installation and setup:

1. **📖 [Platform Setup Guide](platform_setup.md)** - Configure your social media platforms
2. **📖 [User Guide](user_guide.md)** - Learn how to use the web interface
3. **📖 [MySQL Optimization Guide](mysql-optimization-guide.md)** - Advanced performance tuning
4. **📖 [Backup and Maintenance](mysql-backup-maintenance.md)** - Database maintenance procedures
5. **📖 [Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

## Support

If you encounter issues during installation:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review the [MySQL Optimization Guide](mysql-optimization-guide.md)
3. Run the diagnostic commands provided above
4. Check the application logs in `logs/webapp.log`

---

**✅ MySQL Installation Complete!** Your Vedfolnir installation is now ready with a robust, scalable MySQL backend.
