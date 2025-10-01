# Docker Migration Guide

## Overview

This guide provides comprehensive instructions for migrating Vedfolnir from macOS hosting to Docker Compose deployment. The migration process includes data export, containerized deployment setup, data import, and validation procedures.

## Prerequisites

### System Requirements
- Docker Desktop for Mac (latest version)
- Docker Compose v2.0+
- Python 3.8+
- MySQL client tools
- Redis client tools
- Homebrew (for macOS services management)

### Python Dependencies
```bash
pip install pymysql redis requests
```

### Verification
```bash
# Check prerequisites
python scripts/migration/manage_migration.py --action status
```

## Migration Process

### Phase 1: Data Export

Export data from current macOS deployment:

```bash
# Export MySQL data
python scripts/migration/export_macos_mysql_data.py --export-dir ./migration_exports

# Export Redis data
python scripts/migration/export_macos_redis_data.py --export-dir ./migration_exports

# Migrate configuration
python scripts/migration/migrate_configuration.py --source .env --target .env.docker
```

### Phase 2: Docker Environment Setup

1. **Start Docker Compose Environment**:
```bash
# Start all services
docker-compose up -d

# Verify containers are running
docker-compose ps
```

2. **Wait for Services to Initialize**:
```bash
# Check MySQL readiness
docker exec vedfolnir_mysql mysqladmin ping

# Check Redis readiness
docker exec vedfolnir_redis redis-cli ping
```

### Phase 3: Data Import

Import exported data into Docker containers:

```bash
# Import MySQL data
python scripts/migration/import_docker_mysql_data.py ./migration_exports/mysql_export_YYYYMMDD_HHMMSS

# Import Redis data
python scripts/migration/import_docker_redis_data.py ./migration_exports/redis_export_YYYYMMDD_HHMMSS
```

### Phase 4: Validation

Test the migrated deployment:

```bash
# Run complete migration test
python scripts/migration/test_complete_migration.py --export-dir ./migration_exports

# Manual verification
curl http://localhost:5000/health
```

## Automated Migration

Use the migration manager for automated process:

```bash
# Interactive wizard
python scripts/migration/manage_migration.py --interactive

# Full automated migration
python scripts/migration/manage_migration.py --action full
```

## Configuration Changes

### Database Connections
- **Before**: `mysql://user:pass@localhost:3306/vedfolnir`
- **After**: `mysql://user:pass@mysql:3306/vedfolnir`

### Redis Connections
- **Before**: `redis://localhost:6379/0`
- **After**: `redis://redis:6379/0`

### Ollama API
- **Before**: `http://localhost:11434`
- **After**: `http://host.docker.internal:11434`

### File Paths
- **Storage**: `/app/storage` (mounted from `./storage`)
- **Logs**: `/app/logs` (mounted from `./logs`)
- **Config**: `/app/config` (mounted from `./config`)

## Docker Compose Services

### Core Services
- **vedfolnir**: Main application container
- **mysql**: MySQL 8.0 database
- **redis**: Redis 7 session storage
- **nginx**: Reverse proxy and SSL termination

### Observability Stack
- **prometheus**: Metrics collection
- **grafana**: Monitoring dashboards
- **loki**: Log aggregation

### Security
- **vault**: HashiCorp Vault for secrets management

## Volume Mounts

```yaml
volumes:
  - ./data/mysql:/var/lib/mysql          # MySQL data
  - ./data/redis:/data                   # Redis data
  - ./storage:/app/storage               # Application storage
  - ./logs:/app/logs                     # Application logs
  - ./config:/app/config                 # Configuration files
  - ./secrets:/run/secrets               # Docker secrets
```

## Secrets Management

Docker secrets are used for sensitive configuration:

```bash
# Secret files location
./secrets/
├── flask_secret_key.txt
├── platform_encryption_key.txt
├── mysql_password.txt
└── redis_password.txt
```

## Troubleshooting

### Common Issues

1. **Container Won't Start**:
```bash
# Check logs
docker-compose logs vedfolnir
docker-compose logs mysql
docker-compose logs redis
```

2. **Database Connection Failed**:
```bash
# Verify MySQL is ready
docker exec vedfolnir_mysql mysqladmin ping -h localhost

# Check database exists
docker exec vedfolnir_mysql mysql -u vedfolnir -p -e "SHOW DATABASES;"
```

3. **Redis Connection Failed**:
```bash
# Test Redis connectivity
docker exec vedfolnir_redis redis-cli ping

# Check Redis data
docker exec vedfolnir_redis redis-cli dbsize
```

4. **Application Not Accessible**:
```bash
# Check port mapping
docker-compose ps

# Test internal connectivity
docker exec vedfolnir_app curl http://localhost:5000/health
```

### Log Locations

- **Application**: `./logs/app/`
- **MySQL**: `./logs/mysql/`
- **Nginx**: `./logs/nginx/`
- **Migration**: `migration_*.log`

## Rollback Procedures

If migration issues occur, rollback to macOS deployment:

```bash
# Automated rollback
python scripts/migration/rollback_to_macos.py --confirm

# Manual rollback steps:
# 1. Stop Docker containers
docker-compose down -v

# 2. Restore .env file
cp .env.backup_YYYYMMDD_HHMMSS .env

# 3. Start macOS services
brew services start mysql
brew services start redis

# 4. Test macOS deployment
python web_app.py & sleep 10
curl http://localhost:5000/health
```

## Performance Considerations

### Resource Allocation
```yaml
# Recommended container limits
vedfolnir:
  cpus: '2.0'
  memory: 2G

mysql:
  cpus: '2.0'
  memory: 4G

redis:
  cpus: '1.0'
  memory: 1G
```

### Optimization Tips
- Use SSD storage for Docker volumes
- Allocate sufficient memory to Docker Desktop
- Monitor container resource usage with `docker stats`
- Use connection pooling for database connections

## Security Best Practices

1. **Use Docker Secrets** for sensitive data
2. **Network Isolation** with internal Docker networks
3. **Regular Updates** of container images
4. **Backup Encryption** for sensitive data
5. **Access Controls** on mounted volumes

## Monitoring and Maintenance

### Health Checks
```bash
# Application health
curl http://localhost:5000/health

# Database health
docker exec vedfolnir_mysql mysqladmin ping

# Redis health
docker exec vedfolnir_redis redis-cli ping
```

### Backup Procedures
```bash
# Automated backup
docker exec vedfolnir_mysql mysqldump --all-databases > backup.sql
docker exec vedfolnir_redis redis-cli bgsave
```

### Updates
```bash
# Update containers
docker-compose pull
docker-compose up -d

# Update application code
git pull
docker-compose build vedfolnir
docker-compose up -d vedfolnir
```

## Support and Resources

### Documentation
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [MySQL Container Guide](https://hub.docker.com/_/mysql)
- [Redis Container Guide](https://hub.docker.com/_/redis)

### Migration Scripts
- `scripts/migration/manage_migration.py` - Main migration manager
- `scripts/migration/export_macos_*.py` - Data export scripts
- `scripts/migration/import_docker_*.py` - Data import scripts
- `scripts/migration/test_complete_migration.py` - Migration validation
- `scripts/migration/rollback_to_macos.py` - Rollback procedures

### Getting Help
1. Check migration logs for detailed error information
2. Use `--verbose` flag for detailed output
3. Run migration status check: `python scripts/migration/manage_migration.py --action status`
4. Review Docker container logs: `docker-compose logs [service]`