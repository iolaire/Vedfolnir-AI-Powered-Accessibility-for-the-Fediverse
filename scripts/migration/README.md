# Migration Scripts

This directory contains comprehensive scripts for migrating Vedfolnir from macOS hosting to Docker Compose deployment.

## Quick Start

### Automated Migration (Recommended)
```bash
# Interactive migration wizard
python scripts/migration/manage_migration.py --interactive

# Or full automated migration
python scripts/migration/manage_migration.py --action full
```

### Manual Migration Steps
```bash
# 1. Export data from macOS
python scripts/migration/export_macos_mysql_data.py
python scripts/migration/export_macos_redis_data.py
python scripts/migration/migrate_configuration.py

# 2. Start Docker environment
docker-compose up -d

# 3. Import data to Docker
python scripts/migration/import_docker_mysql_data.py ./migration_exports/mysql_export_*
python scripts/migration/import_docker_redis_data.py ./migration_exports/redis_export_*

# 4. Test migration
python scripts/migration/test_complete_migration.py
```

## Scripts Overview

### Data Export Scripts

#### `export_macos_mysql_data.py`
Exports MySQL database from macOS deployment.

**Features:**
- Complete schema and data export using mysqldump
- Table statistics for validation
- Migration manifest generation
- Export validation and integrity checks

**Usage:**
```bash
python scripts/migration/export_macos_mysql_data.py [--export-dir DIR] [--verbose]
```

**Output:**
- `mysql_export_YYYYMMDD_HHMMSS/schema/vedfolnir_schema.sql`
- `mysql_export_YYYYMMDD_HHMMSS/data/vedfolnir_data.sql`
- `mysql_export_YYYYMMDD_HHMMSS/validation/table_statistics.json`
- `mysql_export_YYYYMMDD_HHMMSS/migration_manifest.json`

#### `export_macos_redis_data.py`
Exports Redis data from macOS deployment.

**Features:**
- Redis dump.rdb export via BGSAVE
- JSON key export for validation
- Redis configuration backup
- Server information capture

**Usage:**
```bash
python scripts/migration/export_macos_redis_data.py [--export-dir DIR] [--verbose]
```

**Output:**
- `redis_export_YYYYMMDD_HHMMSS/data/dump.rdb`
- `redis_export_YYYYMMDD_HHMMSS/data/redis_keys.json`
- `redis_export_YYYYMMDD_HHMMSS/config/redis_config.json`
- `redis_export_YYYYMMDD_HHMMSS/validation/redis_info.json`

### Configuration Migration

#### `migrate_configuration.py`
Migrates environment configuration from macOS to Docker.

**Features:**
- Automatic URL conversion for container networking
- Docker secrets file generation
- Docker Compose environment template
- Configuration validation

**Usage:**
```bash
python scripts/migration/migrate_configuration.py [--source .env] [--target .env.docker] [--verbose]
```

**Key Conversions:**
- `localhost` → `mysql`/`redis` for database connections
- `localhost` → `host.docker.internal` for Ollama API
- File paths → container mount points
- Sensitive values → Docker secret file references

### Data Import Scripts

#### `import_docker_mysql_data.py`
Imports MySQL data into Docker container.

**Features:**
- Pre-import backup creation
- Schema and data import with validation
- Table statistics comparison
- Import integrity verification

**Usage:**
```bash
python scripts/migration/import_docker_mysql_data.py EXPORT_PATH [--container CONTAINER_NAME] [--verbose]
```

#### `import_docker_redis_data.py`
Imports Redis data into Docker container.

**Features:**
- Redis service management (stop/start)
- Dump file replacement
- Key validation and fallback import
- Data integrity verification

**Usage:**
```bash
python scripts/migration/import_docker_redis_data.py EXPORT_PATH [--container CONTAINER_NAME] [--verbose]
```

### Testing and Validation

#### `test_complete_migration.py`
Comprehensive migration testing and validation.

**Features:**
- End-to-end migration testing
- Application functionality validation
- Database connectivity testing
- External service verification
- Performance benchmarking

**Usage:**
```bash
python scripts/migration/test_complete_migration.py [--export-dir DIR] [--skip-export] [--verbose]
```

**Tests Performed:**
- Docker container health
- Database connectivity and data integrity
- Redis connectivity and key validation
- Application endpoint testing
- Ollama API connectivity
- WebSocket functionality

### Rollback Procedures

#### `rollback_to_macos.py`
Rollback from Docker to macOS deployment.

**Features:**
- Docker environment cleanup
- macOS services restoration
- Configuration file restoration
- Data restoration (optional)
- Deployment validation

**Usage:**
```bash
python scripts/migration/rollback_to_macos.py [--mysql-backup PATH] [--redis-backup PATH] [--confirm] [--verbose]
```

**Rollback Steps:**
1. Create rollback backup of Docker data
2. Stop and remove Docker containers
3. Restore original .env configuration
4. Start macOS services (MySQL, Redis, etc.)
5. Optionally restore data from backups
6. Validate macOS deployment

### Migration Management

#### `manage_migration.py`
Unified migration management interface.

**Features:**
- Interactive migration wizard
- Automated full migration
- Individual phase execution
- Migration status monitoring
- Prerequisites checking

**Usage:**
```bash
# Interactive mode
python scripts/migration/manage_migration.py --interactive

# Specific actions
python scripts/migration/manage_migration.py --action [export|import|test|rollback|status|full]
```

## Migration Phases

### Phase 1: Export
- Export MySQL database (schema + data)
- Export Redis data (dump + keys)
- Migrate configuration files
- Generate migration manifests

### Phase 2: Docker Setup
- Start Docker Compose environment
- Wait for services to initialize
- Verify container health

### Phase 3: Import
- Import MySQL data with validation
- Import Redis data with verification
- Apply configuration changes

### Phase 4: Validation
- Test application functionality
- Verify data integrity
- Check external service connectivity
- Performance validation

## Directory Structure

```
scripts/migration/
├── README.md                           # This file
├── manage_migration.py                 # Migration manager
├── export_macos_mysql_data.py         # MySQL export
├── export_macos_redis_data.py         # Redis export
├── migrate_configuration.py           # Config migration
├── import_docker_mysql_data.py        # MySQL import
├── import_docker_redis_data.py        # Redis import
├── test_complete_migration.py         # Migration testing
└── rollback_to_macos.py               # Rollback procedures
```

## Export Directory Structure

```
migration_exports/
├── mysql_export_YYYYMMDD_HHMMSS/
│   ├── schema/
│   │   └── vedfolnir_schema.sql
│   ├── data/
│   │   └── vedfolnir_data.sql
│   ├── validation/
│   │   ├── table_statistics.json
│   │   └── export_validation.json
│   └── migration_manifest.json
├── redis_export_YYYYMMDD_HHMMSS/
│   ├── data/
│   │   ├── dump.rdb
│   │   └── redis_keys.json
│   ├── config/
│   │   └── redis_config.json
│   ├── validation/
│   │   ├── redis_info.json
│   │   └── export_validation.json
│   └── migration_manifest.json
└── config_conversion_log_YYYYMMDD_HHMMSS.json
```

## Configuration Files Generated

- `.env.docker` - Docker environment configuration
- `.env.docker-compose` - Docker Compose variables
- `secrets/` - Docker secret files
- `config_conversion_log_*.json` - Configuration changes log
- `config_validation_*.json` - Validation results

## Log Files

All scripts generate detailed log files:
- `mysql_export_*.log`
- `redis_export_*.log`
- `config_migration_*.log`
- `mysql_import_*.log`
- `redis_import_*.log`
- `migration_test_*.log`
- `rollback_*.log`
- `migration_manager_*.log`

## Error Handling

### Common Issues

1. **MySQL Connection Failed**
   - Check MySQL service is running
   - Verify credentials in configuration
   - Ensure database exists

2. **Redis Connection Failed**
   - Check Redis service is running
   - Verify Redis configuration
   - Check for password authentication

3. **Docker Container Not Running**
   - Check Docker Desktop is running
   - Verify docker-compose.yml exists
   - Check container logs: `docker-compose logs`

4. **Import Validation Failed**
   - Check export data integrity
   - Verify container has sufficient resources
   - Review import logs for specific errors

### Troubleshooting Commands

```bash
# Check migration status
python scripts/migration/manage_migration.py --action status

# Verbose logging
python scripts/migration/[script].py --verbose

# Check Docker containers
docker-compose ps
docker-compose logs [service]

# Check macOS services
brew services list

# Test connectivity
mysql -u vedfolnir -p -e "SELECT 1;"
redis-cli ping
curl http://localhost:5000/health
```

## Best Practices

1. **Always backup data** before migration
2. **Test migration** in development environment first
3. **Monitor logs** during migration process
4. **Validate data integrity** after import
5. **Keep rollback procedures** ready
6. **Document custom configurations**

## Security Considerations

- Sensitive data is handled via Docker secrets
- Database passwords are not logged
- Export files contain sensitive data - secure appropriately
- Use proper file permissions on secret files (600)
- Clean up temporary files after migration

## Performance Tips

- Allocate sufficient resources to Docker Desktop
- Use SSD storage for Docker volumes
- Monitor container resource usage during migration
- Consider migration during low-traffic periods
- Test performance after migration completion

## Support

For migration issues:
1. Check the detailed log files
2. Use `--verbose` flag for additional debugging
3. Review the migration guide: `docs/migration/docker-migration-guide.md`
4. Check Docker container logs: `docker-compose logs`
5. Verify prerequisites are met