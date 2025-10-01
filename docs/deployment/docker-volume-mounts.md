# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Docker Volume Mounts Configuration

## Overview

This document describes the comprehensive volume mount configuration for the Vedfolnir Docker Compose deployment. All persistent data is stored using bind mounts to provide external access from the host system for backup, monitoring, and management purposes.

## Volume Mount Strategy

### Bind Mounts vs Named Volumes

The configuration uses **bind mounts** instead of named Docker volumes to ensure:
- Direct host system access to all data
- Easy backup and restore procedures
- External monitoring and management capabilities
- Simplified data migration and maintenance

## Directory Structure

```
vedfolnir/
├── storage/                    # Application data storage
│   ├── images/                # Downloaded images
│   ├── backups/               # Backup storage
│   │   ├── mysql/            # MySQL backups
│   │   ├── redis/            # Redis backups
│   │   └── app/              # Application backups
│   └── temp/                  # Temporary files
├── logs/                      # Service logs
│   ├── app/                   # Application logs
│   ├── mysql/                 # MySQL logs
│   ├── redis/                 # Redis logs
│   ├── nginx/                 # Nginx logs
│   ├── vault/                 # Vault logs
│   └── audit/                 # Audit logs
├── config/                    # Configuration files
│   ├── app/                   # Application config
│   ├── mysql/                 # MySQL config
│   ├── redis/                 # Redis config
│   ├── nginx/                 # Nginx config
│   ├── prometheus/            # Prometheus config
│   ├── grafana/               # Grafana config
│   ├── loki/                  # Loki config
│   └── vault/                 # Vault config
├── data/                      # Persistent data
│   ├── mysql/                 # MySQL database files
│   ├── redis/                 # Redis data files
│   ├── prometheus/            # Prometheus metrics data
│   ├── grafana/               # Grafana dashboards and settings
│   ├── loki/                  # Loki log data
│   └── vault/                 # Vault secrets data
├── secrets/                   # Docker secrets
└── ssl/                       # SSL certificates
```

## Service Volume Mounts

### Vedfolnir Application
```yaml
volumes:
  - ./storage:/app/storage              # Application storage
  - ./config/app:/app/config:ro         # Configuration (read-only)
  - ./logs/app:/app/logs                # Application logs
  - ./storage/backups/app:/app/backups  # Application backups
```

### MySQL Database
```yaml
volumes:
  - ./data/mysql:/var/lib/mysql                        # Database data
  - ./config/mysql:/etc/mysql/conf.d:ro                # Configuration
  - ./docker/mysql/init:/docker-entrypoint-initdb.d:ro # Init scripts
  - ./docker/scripts:/scripts:ro                       # Management scripts
  - ./storage/backups/mysql:/backups                   # Backups
  - ./logs/mysql:/var/log/mysql                        # Logs
```

### Redis Cache
```yaml
volumes:
  - ./data/redis:/data:rw,Z                                        # Redis data
  - ./config/redis/redis.conf:/usr/local/etc/redis/redis.conf:ro,Z # Configuration
  - ./storage/backups/redis:/backups:rw,Z                          # Backups
  - ./logs/redis:/var/log/redis:rw,Z                               # Logs
```

### HashiCorp Vault
```yaml
volumes:
  - ./data/vault:/vault/data        # Vault data
  - ./config/vault:/vault/config:ro # Configuration
  - ./logs/vault:/vault/logs        # Logs
  - ./secrets:/vault/secrets        # Secrets access
```

### Nginx Reverse Proxy
```yaml
volumes:
  - ./config/nginx:/etc/nginx/conf.d:ro # Configuration
  - ./ssl:/etc/nginx/ssl:ro             # SSL certificates
  - ./static:/var/www/static:ro         # Static files
  - ./logs/nginx:/var/log/nginx         # Access logs
```

### Prometheus Metrics
```yaml
volumes:
  - ./config/prometheus:/etc/prometheus:ro           # Configuration
  - ./data/prometheus:/prometheus                    # Metrics data
  - ./config/prometheus/rules:/etc/prometheus/rules:ro # Alert rules
```

### Grafana Dashboard
```yaml
volumes:
  - ./data/grafana:/var/lib/grafana                              # Dashboard data
  - ./config/grafana/grafana.ini:/etc/grafana/grafana.ini:ro    # Configuration
  - ./config/grafana/provisioning:/etc/grafana/provisioning:ro  # Provisioning
  - ./config/grafana/dashboards:/etc/grafana/dashboards:ro      # Dashboards
```

### Loki Log Aggregation
```yaml
volumes:
  - ./config/loki/loki.yml:/etc/loki/local-config.yaml:ro # Configuration
  - ./data/loki:/loki                                     # Log data
```

## External Access Benefits

### Backup and Recovery
- **Direct Access**: All data accessible from host for backup scripts
- **Incremental Backups**: Easy to implement with standard backup tools
- **Point-in-Time Recovery**: Database and Redis data directly accessible
- **Cross-Platform**: Backup data portable across different environments

### Monitoring and Management
- **Log Analysis**: Direct access to all service logs
- **Configuration Management**: Easy to update configurations without rebuilding containers
- **Data Inspection**: Direct access to database and cache data for troubleshooting
- **Performance Monitoring**: File system metrics available to host monitoring tools

### Development and Debugging
- **Live Configuration**: Update configurations without container restarts
- **Log Streaming**: Real-time log access for debugging
- **Data Inspection**: Direct database and cache access for development
- **File Sharing**: Easy file transfer between host and containers

## Security Considerations

### File Permissions
- **Container Users**: Services run as non-root users where possible
- **Host Access**: Bind mounts maintain appropriate file permissions
- **Read-Only Mounts**: Configuration files mounted read-only for security
- **SELinux Labels**: Z flag used for SELinux compatibility where needed

### Access Control
- **Directory Permissions**: Proper permissions set on host directories
- **Secret Management**: Sensitive files in dedicated secrets directory
- **Configuration Security**: Read-only access to configuration files
- **Log Security**: Appropriate permissions on log directories

## Testing and Validation

### Volume Mount Test Script
Use the provided test script to verify all volume mounts:

```bash
./scripts/docker/test_volume_mounts.sh
```

This script tests:
- Directory existence
- Write access from host
- Docker Compose configuration
- File permissions

### Manual Verification
1. **Start Services**: `docker-compose up -d`
2. **Check Mounts**: `docker-compose exec vedfolnir ls -la /app/storage`
3. **Test Write Access**: Create test files in mounted directories
4. **Verify Persistence**: Restart containers and check data persistence

## Troubleshooting

### Common Issues

#### Permission Denied
```bash
# Fix directory permissions
sudo chown -R $USER:$USER ./data ./logs ./storage
chmod -R 755 ./data ./logs ./storage
```

#### SELinux Issues (RHEL/CentOS)
```bash
# Set SELinux context
sudo setsebool -P container_manage_cgroup on
sudo chcon -Rt svirt_sandbox_file_t ./data ./logs ./storage
```

#### Container User Conflicts
```bash
# Check container user ID
docker-compose exec vedfolnir id

# Adjust host directory ownership
sudo chown -R 1000:1000 ./data/grafana  # Example for Grafana
```

### Verification Commands

```bash
# Check volume mounts
docker-compose config --volumes

# Inspect container mounts
docker inspect vedfolnir_app | grep -A 20 "Mounts"

# Test file creation
echo "test" > ./storage/test.txt
docker-compose exec vedfolnir cat /app/storage/test.txt
```

## Maintenance Procedures

### Backup Procedures
```bash
# Stop services
docker-compose down

# Backup all data
tar -czf vedfolnir-backup-$(date +%Y%m%d).tar.gz data/ storage/ config/ secrets/

# Restart services
docker-compose up -d
```

### Data Migration
```bash
# Export from old system
docker-compose exec mysql mysqldump --all-databases > ./storage/backups/mysql/full-backup.sql

# Import to new system
docker-compose exec mysql mysql < ./storage/backups/mysql/full-backup.sql
```

### Configuration Updates
```bash
# Update configuration files in ./config/
# Restart specific service
docker-compose restart prometheus

# Or reload configuration (if supported)
docker-compose exec prometheus kill -HUP 1
```

## Performance Considerations

### I/O Performance
- **SSD Storage**: Use SSD storage for data directories for better performance
- **Separate Volumes**: Consider separate volumes for high-I/O services
- **Mount Options**: Use appropriate mount options for performance

### Monitoring
- **Disk Usage**: Monitor disk usage of data directories
- **I/O Metrics**: Track I/O performance of mounted volumes
- **Backup Performance**: Monitor backup and restore performance

## Compliance and Audit

### Data Retention
- **Log Rotation**: Implement log rotation for log directories
- **Data Archival**: Archive old data from data directories
- **Compliance**: Maintain audit trails for data access

### Security Auditing
- **File Access**: Monitor file access to mounted directories
- **Permission Changes**: Audit permission changes on data directories
- **Configuration Changes**: Track configuration file modifications