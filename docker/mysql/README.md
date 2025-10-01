# MySQL Container Configuration for Vedfolnir

## Overview

This directory contains the MySQL container configuration for Vedfolnir's Docker Compose deployment. The configuration is optimized for containerized deployment with UTF8MB4 charset, performance optimizations, comprehensive health monitoring, and enterprise-grade security.

## Directory Structure

```
docker/mysql/
├── README.md                    # This documentation
├── conf.d/                      # Additional MySQL configuration files
├── init/                        # Database initialization scripts
│   ├── 01-init-vedfolnir.sql   # Basic database setup
│   ├── 02-health-check-setup.sql # Health monitoring setup
│   └── 03-performance-optimization.sql # Performance tuning
└── dev-init/                    # Development-specific initialization
```

## Configuration Features

### Character Set and Collation
- **UTF8MB4**: Full Unicode support including emojis and special characters
- **utf8mb4_unicode_ci**: Case-insensitive Unicode collation
- Proper character set configuration for all connections

### Performance Optimizations
- **InnoDB Buffer Pool**: 2GB optimized for containerized deployment
- **Connection Pooling**: Up to 200 concurrent connections
- **Query Optimization**: Optimized for typical web application workloads
- **Binary Logging**: Enabled for point-in-time recovery
- **Slow Query Logging**: Enabled for performance monitoring

### Security Features
- **Network Isolation**: Internal Docker network only
- **Credential Management**: Docker secrets integration
- **Access Control**: Minimal privilege principles
- **SSL Support**: Ready for SSL/TLS encryption
- **Audit Logging**: Comprehensive security event logging

### Health Monitoring
- **Health Check User**: Dedicated monitoring user with minimal privileges
- **Performance Views**: Pre-built views for performance monitoring
- **Stored Procedures**: Automated health and performance checks
- **Comprehensive Metrics**: Buffer pool, connections, queries, disk usage

## Container Configuration

### Docker Compose Service
```yaml
mysql:
  image: mysql:8.0
  container_name: vedfolnir_mysql
  restart: unless-stopped
  environment:
    MYSQL_ROOT_PASSWORD_FILE: /run/secrets/mysql_root_password
    MYSQL_DATABASE: vedfolnir
    MYSQL_USER: vedfolnir
    MYSQL_PASSWORD_FILE: /run/secrets/mysql_password
    MYSQL_CHARSET: utf8mb4
    MYSQL_COLLATION: utf8mb4_unicode_ci
  secrets:
    - mysql_root_password
    - mysql_password
  volumes:
    - mysql_data:/var/lib/mysql
    - ./config/mysql:/etc/mysql/conf.d:ro
    - ./docker/mysql/init:/docker-entrypoint-initdb.d:ro
    - ./docker/scripts:/scripts:ro
    - ./storage/backups/mysql:/backups
    - ./logs/mysql:/var/log/mysql
  networks:
    - vedfolnir_internal
  healthcheck:
    test: ["CMD", "sh", "-c", "mysqladmin ping -h localhost --silent && mysql -h localhost -e 'SELECT 1' >/dev/null 2>&1"]
    interval: 30s
    timeout: 15s
    retries: 5
    start_period: 60s
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
```

### Resource Limits
- **CPU**: 2.0 cores limit, 1.0 core reservation
- **Memory**: 4GB limit, 2GB reservation
- **Buffer Pool**: 2GB (50% of memory limit)
- **Connections**: 200 maximum concurrent connections

## Management Scripts

### Health Check Script
```bash
# Basic health check (used by Docker)
./docker/scripts/mysql-health-check.sh basic

# Comprehensive health check
./docker/scripts/mysql-health-check.sh full
```

### Performance Monitoring
```bash
# Full performance report
./docker/scripts/mysql-performance-monitor.sh report

# Specific checks
./docker/scripts/mysql-performance-monitor.sh buffer
./docker/scripts/mysql-performance-monitor.sh connections
./docker/scripts/mysql-performance-monitor.sh queries
```

### Backup Management
```bash
# Full database backup
./docker/scripts/mysql-backup.sh full

# Schema-only backup
./docker/scripts/mysql-backup.sh schema

# Specific tables backup
./docker/scripts/mysql-backup.sh tables "users posts images"

# List available backups
./docker/scripts/mysql-backup.sh list

# Verify backup integrity
./docker/scripts/mysql-backup.sh verify /backups/20250101_120000
```

### Container Management
```bash
# Container status and MySQL accessibility
./docker/scripts/mysql-management.sh status

# View logs
./docker/scripts/mysql-management.sh logs 100

# Connect to MySQL shell
./docker/scripts/mysql-management.sh connect

# Database information
./docker/scripts/mysql-management.sh database-info

# Restart container
./docker/scripts/mysql-management.sh restart
```

## Database Initialization

### Automatic Setup
The container automatically runs initialization scripts in order:

1. **01-init-vedfolnir.sql**: Basic database setup with UTF8MB4
2. **02-health-check-setup.sql**: Health monitoring components
3. **03-performance-optimization.sql**: Performance views and procedures

### Manual Verification
After container startup, verify the setup:

```sql
-- Check character set
SHOW VARIABLES LIKE 'character_set%';

-- Check collation
SHOW VARIABLES LIKE 'collation%';

-- Check performance views
SELECT * FROM performance_summary;

-- Run health check
CALL ContainerHealthCheck();
```

## Performance Monitoring

### Built-in Views
- **performance_summary**: Key performance metrics with status
- **active_connections**: Current active database connections
- **database_size_info**: Database size and table count
- **table_size_info**: Individual table sizes and index ratios

### Stored Procedures
- **QuickPerformanceCheck()**: Quick performance overview
- **ContainerHealthCheck()**: Comprehensive health assessment
- **CheckDatabaseHealth()**: Detailed health metrics

### Key Metrics to Monitor
- **Buffer Pool Hit Rate**: Should be >99% for optimal performance
- **Connection Usage**: Should be <85% of max_connections
- **Slow Query Rate**: Should be <1% of total queries
- **Disk Usage**: Should be <90% of available space

## Security Configuration

### Network Security
- Container runs on internal Docker network only
- No direct host port exposure (except for debugging)
- Secure inter-service communication

### Credential Management
- Root password stored in Docker secrets
- Application user password in Docker secrets
- Health check user with minimal privileges
- No passwords in environment variables or logs

### Access Control
```sql
-- Application user (created automatically)
CREATE USER 'vedfolnir'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir'@'%';

-- Health check user (created by init script)
CREATE USER 'healthcheck'@'localhost' IDENTIFIED BY 'healthcheck_password';
GRANT PROCESS ON *.* TO 'healthcheck'@'localhost';
GRANT SELECT ON performance_schema.* TO 'healthcheck'@'localhost';
```

## Backup and Recovery

### Automated Backups
- Full database backups with compression
- Schema-only backups for structure
- Table-specific backups for targeted recovery
- Backup verification and integrity checking
- Configurable retention policies (default: 7 days)

### Point-in-Time Recovery
- Binary logging enabled for transaction-level recovery
- Log rotation every 7 days or 1GB
- Complete transaction consistency with single-transaction dumps

### Backup Storage
- Backups stored in `./storage/backups/mysql/`
- Organized by timestamp directories
- Metadata files for backup information
- Compressed storage for space efficiency

## Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check container logs
docker logs vedfolnir_mysql

# Check Docker Compose logs
docker-compose logs mysql

# Verify secrets files exist
ls -la secrets/mysql_*
```

#### Connection Issues
```bash
# Test basic connectivity
docker exec vedfolnir_mysql mysqladmin ping

# Test database access
docker exec vedfolnir_mysql mysql -u vedfolnir -p -e "SELECT 1;"

# Check network connectivity
docker network ls
docker network inspect vedfolnir_internal
```

#### Performance Issues
```bash
# Run performance check
docker exec vedfolnir_mysql /scripts/mysql-performance-monitor.sh report

# Check resource usage
docker stats vedfolnir_mysql

# Review slow query log
docker exec vedfolnir_mysql tail -f /var/log/mysql/slow.log
```

### Health Check Failures
```bash
# Manual health check
docker exec vedfolnir_mysql /scripts/mysql-health-check.sh full

# Check MySQL error log
docker exec vedfolnir_mysql tail -f /var/log/mysql/error.log

# Verify configuration
docker exec vedfolnir_mysql mysql -e "SHOW VARIABLES LIKE 'innodb%';"
```

## Development and Testing

### Development Configuration
For development, you can expose the MySQL port:

```yaml
# Uncomment in docker-compose.yml for development
ports:
  - "127.0.0.1:3306:3306"
```

### Testing Database Setup
```bash
# Create test database
docker exec vedfolnir_mysql mysql -u root -p -e "CREATE DATABASE vedfolnir_test;"

# Run application tests
python -m pytest tests/ -v
```

### Performance Testing
```bash
# Load testing with mysqlslap
docker exec vedfolnir_mysql mysqlslap --user=vedfolnir --password --host=localhost --concurrency=50 --iterations=100 --create-schema=vedfolnir_test

# Monitor during load
docker exec vedfolnir_mysql /scripts/mysql-performance-monitor.sh report
```

## Maintenance

### Regular Maintenance Tasks
1. **Daily**: Monitor health checks and performance metrics
2. **Weekly**: Review slow query logs and optimize queries
3. **Monthly**: Analyze table sizes and optimize indexes
4. **Quarterly**: Review and update configuration parameters

### Configuration Updates
```bash
# Update MySQL configuration
vim config/mysql/vedfolnir.cnf

# Restart container to apply changes
docker-compose restart mysql

# Verify configuration
docker exec vedfolnir_mysql mysql -e "SHOW VARIABLES LIKE 'innodb_buffer_pool_size';"
```

### Log Management
```bash
# Rotate logs manually
docker exec vedfolnir_mysql mysqladmin flush-logs

# Clean old binary logs
docker exec vedfolnir_mysql mysql -e "PURGE BINARY LOGS BEFORE DATE(NOW() - INTERVAL 7 DAY);"
```

## Integration with Vedfolnir Application

### Connection Configuration
The application connects using:
```bash
DATABASE_URL=mysql+pymysql://vedfolnir:${MYSQL_PASSWORD}@mysql:3306/vedfolnir?charset=utf8mb4
```

### SQLAlchemy Configuration
```python
# Optimized for containerized MySQL
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'max_overflow': 30,
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'connect_args': {
        'charset': 'utf8mb4',
        'connect_timeout': 60,
        'read_timeout': 30,
        'write_timeout': 30
    }
}
```

### Migration Support
```bash
# Run database migrations in container
docker exec vedfolnir_app python -m alembic upgrade head

# Create new migration
docker exec vedfolnir_app python -m alembic revision --autogenerate -m "Description"
```

This MySQL container configuration provides enterprise-grade database services for Vedfolnir with comprehensive monitoring, security, and performance optimization specifically designed for containerized deployment.