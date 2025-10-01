# Docker Compose Management Scripts

This directory contains comprehensive automation and management scripts for the Vedfolnir Docker Compose deployment.

## Overview

The Docker Compose management system provides automated deployment, maintenance, backup, and security management for the containerized Vedfolnir application.

## Scripts

### 1. `docker-compose-manager.sh` - Master Management Script

The main entry point for all Docker Compose operations. Provides a unified interface to all other scripts.

**Usage:**
```bash
./docker-compose-manager.sh COMMAND [OPTIONS]
```

**Key Commands:**
- `deploy` - Initial Docker Compose deployment
- `start/stop/restart` - Service management
- `status/logs/health` - Monitoring
- `backup/restore` - Data management
- `rotate-secrets` - Security management
- `interactive` - Interactive menu mode

### 2. `deploy.sh` - Deployment Automation

Automated setup script for initial Docker Compose deployment.

**Features:**
- Prerequisites checking
- Directory structure creation
- Secret generation
- Environment file creation
- Service initialization
- Deployment verification

**Usage:**
```bash
./deploy.sh [--dry-run] [--force]
```

### 3. `manage.sh` - Service Management

Management scripts for common operations (start, stop, restart, logs, backup).

**Commands:**
- `start [--build]` - Start services
- `stop [--remove]` - Stop services
- `restart [SERVICE]` - Restart services
- `status` - Show service status
- `logs [SERVICE] [--follow]` - Show logs
- `health` - Health check
- `update` - Update services
- `backup` - Create backup
- `restore BACKUP_DIR` - Restore data
- `cleanup` - Clean resources

### 4. `backup.sh` - Backup and Restore

Comprehensive backup and restore procedures for containerized data.

**Backup Types:**
- `full` - Complete system backup
- `database` - MySQL database only
- `redis` - Redis data only
- `application` - Application data
- `config` - Configuration files
- `vault` - Vault secrets

**Features:**
- Automated backup creation
- Backup verification
- Compressed backups
- Point-in-time recovery
- Backup retention management

**Usage:**
```bash
./backup.sh backup [TYPE] [NAME]
./backup.sh restore BACKUP_PATH [TYPE]
./backup.sh list
./backup.sh cleanup
```

### 5. `maintenance.sh` - System Maintenance

Update and maintenance scripts for container management.

**Operations:**
- `update` - Update all services
- `maintenance` - System maintenance
- `security` - Security updates
- `performance` - Performance tuning
- `health` - Health monitoring
- `recovery` - Emergency recovery

**Features:**
- Rolling updates
- Resource cleanup
- Log rotation
- Database optimization
- Performance tuning
- Health monitoring

### 6. `secrets.sh` - Secret Management

Secret rotation automation and container update procedures.

**Secret Types:**
- Flask secret key
- Platform encryption key
- MySQL passwords
- Redis password
- Vault tokens

**Features:**
- Automated secret rotation
- Secret backup
- Service updates
- Rotation verification
- Emergency reset

**Usage:**
```bash
./secrets.sh rotate [TYPE]
./secrets.sh check
./secrets.sh verify
./secrets.sh emergency
```

## Quick Start

### Initial Deployment

```bash
# Make scripts executable
chmod +x scripts/docker/*.sh

# Run initial deployment
./scripts/docker/deploy.sh

# Or use the master script
./scripts/docker/docker-compose-manager.sh deploy
```

### Daily Operations

```bash
# Check system status
./scripts/docker/docker-compose-manager.sh status

# View logs
./scripts/docker/docker-compose-manager.sh logs vedfolnir --follow

# Create backup
./scripts/docker/docker-compose-manager.sh backup full

# Update system
./scripts/docker/docker-compose-manager.sh update
```

### Interactive Mode

```bash
# Launch interactive menu
./scripts/docker/docker-compose-manager.sh interactive
```

## Directory Structure

After deployment, the following directory structure will be created:

```
vedfolnir/
├── data/                    # Persistent data
│   ├── mysql/              # MySQL data
│   ├── redis/              # Redis data
│   ├── prometheus/         # Prometheus data
│   ├── grafana/            # Grafana data
│   ├── loki/               # Loki data
│   └── vault/              # Vault data
├── config/                 # Configuration files
│   ├── mysql/              # MySQL config
│   ├── redis/              # Redis config
│   ├── nginx/              # Nginx config
│   ├── prometheus/         # Prometheus config
│   ├── grafana/            # Grafana config
│   ├── loki/               # Loki config
│   ├── vault/              # Vault config
│   └── app/                # Application config
├── storage/                # Application storage
│   ├── images/             # Image files
│   ├── backups/            # Backup files
│   └── temp/               # Temporary files
├── logs/                   # Log files
│   ├── app/                # Application logs
│   ├── nginx/              # Nginx logs
│   ├── mysql/              # MySQL logs
│   ├── redis/              # Redis logs
│   ├── vault/              # Vault logs
│   └── audit/              # Audit logs
├── secrets/                # Secret files
│   ├── database/           # Database secrets
│   ├── redis/              # Redis secrets
│   └── app/                # Application secrets
└── ssl/                    # SSL certificates
    ├── certs/              # Certificate files
    └── keys/               # Private keys
```

## Environment Configuration

The deployment creates a `.env.docker` file with all necessary environment variables:

```bash
# Application Configuration
FLASK_ENV=production
FLASK_DEBUG=false

# Database Configuration
DATABASE_URL=mysql+pymysql://vedfolnir:${MYSQL_PASSWORD}@mysql:3306/vedfolnir?charset=utf8mb4

# Redis Configuration
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Ollama Configuration (External Service)
OLLAMA_URL=http://host.docker.internal:11434

# Security Configuration
FLASK_SECRET_KEY_FILE=/run/secrets/flask_secret_key
PLATFORM_ENCRYPTION_KEY_FILE=/run/secrets/platform_encryption_key

# Observability Configuration
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000
LOKI_URL=http://loki:3100
```

## Security Features

### Secret Management
- Automated secret generation
- Secure file permissions (600)
- Regular rotation schedules
- Backup and recovery
- Emergency reset procedures

### Container Security
- Non-root user execution
- Read-only root filesystems
- Security context constraints
- Network isolation
- Resource limits

### Data Protection
- Encryption at rest
- Secure inter-service communication
- Audit logging
- Access controls
- Backup encryption

## Monitoring and Observability

### Services
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **Loki**: Log aggregation
- **Health Checks**: Service monitoring

### Endpoints
- Application: http://localhost:80
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

### Metrics
- Application performance
- Container resources
- Database performance
- Queue processing
- Business metrics

## Backup Strategy

### Automated Backups
- Full system backups
- Incremental backups
- Point-in-time recovery
- Backup verification
- Retention management

### Backup Types
- **Full**: Complete system backup
- **Database**: MySQL data only
- **Redis**: Session and queue data
- **Application**: Storage and configuration
- **Vault**: Secrets and policies

### Recovery Procedures
- Automated restore scripts
- Data integrity verification
- Service health validation
- Rollback procedures

## Maintenance Procedures

### Regular Maintenance
- System updates
- Security patches
- Resource cleanup
- Log rotation
- Performance optimization

### Health Monitoring
- Service health checks
- Resource usage monitoring
- Performance metrics
- Alert management
- Issue detection

### Emergency Procedures
- Emergency recovery
- Secret reset
- Service restoration
- Data recovery
- Incident response

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   ./docker-compose-manager.sh health
   ./docker-compose-manager.sh logs [SERVICE]
   ```

2. **Database connection issues**
   ```bash
   ./docker-compose-manager.sh check-secrets
   ./docker-compose-manager.sh restart mysql
   ```

3. **Storage issues**
   ```bash
   df -h
   ./docker-compose-manager.sh cleanup
   ```

4. **Performance issues**
   ```bash
   ./docker-compose-manager.sh performance
   docker stats
   ```

### Log Locations
- Application logs: `logs/app/`
- Service logs: `docker-compose logs [SERVICE]`
- System logs: `logs/audit/`
- Rotation logs: `logs/secret_rotation.log`

### Support Commands
```bash
# System status
./docker-compose-manager.sh status

# Health check
./docker-compose-manager.sh health

# View recent logs
./docker-compose-manager.sh logs --follow

# Emergency recovery
./docker-compose-manager.sh recovery
```

## Requirements Compliance

This implementation satisfies the following requirements:

- **10.1**: Automated setup script for initial Docker Compose deployment
- **10.2**: Management scripts for common operations
- **10.3**: Backup and restore procedures for containerized data
- **10.5**: Update and maintenance scripts for container management
- **5.9**: Secret rotation automation and container update procedures

## License

Copyright (C) 2025 iolaire mcfadden.
This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.