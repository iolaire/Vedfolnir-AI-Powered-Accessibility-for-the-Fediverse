# MySQL Container Quick Reference

## Quick Commands

### Container Management
```bash
# Start MySQL container
docker-compose up -d mysql

# Stop MySQL container
docker-compose stop mysql

# Restart MySQL container
docker-compose restart mysql

# View MySQL logs
docker-compose logs -f mysql

# Container status
./docker/scripts/mysql-management.sh status
```

### Database Access
```bash
# Connect to MySQL shell
docker exec -it vedfolnir_mysql mysql -u root -p

# Connect as application user
docker exec -it vedfolnir_mysql mysql -u vedfolnir -p

# Execute single query
docker exec vedfolnir_mysql mysql -u root -p -e "SHOW DATABASES;"
```

### Health Monitoring
```bash
# Basic health check
./docker/scripts/mysql-health-check.sh basic

# Comprehensive health check
./docker/scripts/mysql-health-check.sh full

# Performance report
./docker/scripts/mysql-performance-monitor.sh report

# Quick performance check (SQL)
docker exec vedfolnir_mysql mysql -u root -p -e "CALL QuickPerformanceCheck();"
```

### Backup Operations
```bash
# Full backup
./docker/scripts/mysql-backup.sh full

# Schema backup
./docker/scripts/mysql-backup.sh schema

# List backups
./docker/scripts/mysql-backup.sh list

# Verify backup
./docker/scripts/mysql-backup.sh verify /backups/20250101_120000
```

## Key Configuration

### Connection Details
- **Host**: mysql (internal Docker network)
- **Port**: 3306 (internal)
- **Database**: vedfolnir
- **User**: vedfolnir
- **Character Set**: utf8mb4
- **Collation**: utf8mb4_unicode_ci

### Resource Limits
- **CPU**: 2.0 cores (limit), 1.0 core (reservation)
- **Memory**: 4GB (limit), 2GB (reservation)
- **Buffer Pool**: 2GB
- **Max Connections**: 200

### Important Paths
- **Data**: `/var/lib/mysql` (mounted to `mysql_data` volume)
- **Config**: `/etc/mysql/conf.d` (mounted from `./config/mysql`)
- **Logs**: `/var/log/mysql` (mounted to `./logs/mysql`)
- **Backups**: `/backups` (mounted to `./storage/backups/mysql`)
- **Scripts**: `/scripts` (mounted from `./docker/scripts`)

## Performance Views

### Quick Performance Check
```sql
-- Overall performance summary
SELECT * FROM performance_summary;

-- Active connections
SELECT * FROM active_connections;

-- Database size
SELECT * FROM database_size_info;

-- Table sizes
SELECT * FROM table_size_info LIMIT 10;
```

### Health Check Procedures
```sql
-- Quick performance overview
CALL QuickPerformanceCheck();

-- Comprehensive health assessment
CALL ContainerHealthCheck();

-- Detailed health metrics
CALL CheckDatabaseHealth();
```

## Troubleshooting

### Container Issues
```bash
# Check if container is running
docker ps | grep vedfolnir_mysql

# Check container health
docker inspect vedfolnir_mysql | grep Health -A 10

# View detailed logs
docker logs vedfolnir_mysql --tail 100

# Check resource usage
docker stats vedfolnir_mysql --no-stream
```

### Connection Issues
```bash
# Test basic connectivity
docker exec vedfolnir_mysql mysqladmin ping

# Test database access
docker exec vedfolnir_mysql mysql -u vedfolnir -p -e "SELECT 1;"

# Check network
docker network inspect vedfolnir_internal
```

### Performance Issues
```bash
# Check slow queries
docker exec vedfolnir_mysql tail -f /var/log/mysql/slow.log

# Monitor performance
./docker/scripts/mysql-performance-monitor.sh report

# Check buffer pool efficiency
docker exec vedfolnir_mysql mysql -u root -p -e "
SELECT 
  ROUND((1 - (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') / 
  (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests')) * 100, 2) as buffer_hit_rate_percent;"
```

## Security

### Access Control
- Root access: Docker secrets (`mysql_root_password.txt`)
- App access: Docker secrets (`mysql_password.txt`)
- Health check: Limited privileges user
- Network: Internal Docker network only

### Credential Management
```bash
# View secret files (content hidden)
ls -la secrets/mysql_*

# Rotate passwords (requires container restart)
echo "new_password" > secrets/mysql_password.txt
docker-compose restart mysql
```

## Maintenance

### Regular Tasks
```bash
# Daily health check
./docker/scripts/mysql-health-check.sh full

# Weekly performance review
./docker/scripts/mysql-performance-monitor.sh report

# Weekly backup
./docker/scripts/mysql-backup.sh full

# Monthly cleanup
./docker/scripts/mysql-backup.sh cleanup
```

### Configuration Updates
```bash
# Edit configuration
vim config/mysql/vedfolnir.cnf

# Apply changes (restart required)
docker-compose restart mysql

# Verify changes
docker exec vedfolnir_mysql mysql -e "SHOW VARIABLES LIKE 'innodb_buffer_pool_size';"
```

## Emergency Procedures

### Container Recovery
```bash
# Stop all services
docker-compose down

# Start only MySQL
docker-compose up -d mysql

# Check logs for errors
docker-compose logs mysql

# If data corruption, restore from backup
./docker/scripts/mysql-backup.sh list
# Restore manually from backup files
```

### Data Recovery
```bash
# List available backups
./docker/scripts/mysql-backup.sh list

# Verify backup integrity
./docker/scripts/mysql-backup.sh verify /backups/YYYYMMDD_HHMMSS

# Manual restore (example)
docker exec -i vedfolnir_mysql mysql -u root -p < /backups/YYYYMMDD_HHMMSS/vedfolnir_full_backup.sql
```

This quick reference provides the most commonly used commands and procedures for managing the MySQL container in Vedfolnir's Docker Compose deployment.