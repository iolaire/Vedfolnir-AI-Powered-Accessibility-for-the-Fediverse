# Docker Compose Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying Vedfolnir using Docker Compose. The containerized deployment offers improved portability, scalability, and deployment consistency compared to the previous macOS-specific setup.

## Prerequisites

### System Requirements
- Docker Engine 20.10+ 
- Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended)
- 50GB available disk space
- Linux/macOS/Windows with WSL2

### External Dependencies
- **Ollama Service**: Must be running on host system at `localhost:11434`
  - Install Ollama: https://ollama.ai/download
  - Pull LLaVA model: `ollama pull llava:7b`
  - Verify: `curl http://localhost:11434/api/version`

### Network Requirements
- Ports 80, 443 (Nginx)
- Port 3000 (Grafana dashboard)
- Internal container networking for services

## Quick Start

### 1. Clone and Setup
```bash
# Clone repository
git clone <repository-url>
cd vedfolnir

# Create required directories
mkdir -p data/{mysql,redis,prometheus,grafana,loki,vault}
mkdir -p logs/{app,nginx,mysql,vault,audit}
mkdir -p storage/{images,backups,temp}
mkdir -p secrets
```

### 2. Configure Secrets
```bash
# Generate secure secrets
openssl rand -base64 32 > secrets/flask_secret_key.txt
openssl rand -base64 32 > secrets/platform_encryption_key.txt
openssl rand -base64 32 > secrets/mysql_root_password.txt
openssl rand -base64 32 > secrets/mysql_password.txt
openssl rand -base64 32 > secrets/redis_password.txt
openssl rand -base64 32 > secrets/vault_root_token.txt
openssl rand -base64 32 > secrets/vault_token.txt

# Set proper permissions
chmod 600 secrets/*
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env.docker

# Edit configuration
nano .env.docker
```

Required environment variables:
```bash
# Database Configuration
DATABASE_URL=mysql+pymysql://vedfolnir:$(cat secrets/mysql_password.txt)@mysql:3306/vedfolnir?charset=utf8mb4
MYSQL_ROOT_PASSWORD_FILE=/run/secrets/mysql_root_password
MYSQL_PASSWORD_FILE=/run/secrets/mysql_password

# Redis Configuration
REDIS_URL=redis://:$(cat secrets/redis_password.txt)@redis:6379/0
REDIS_PASSWORD_FILE=/run/secrets/redis_password

# Application Configuration
FLASK_SECRET_KEY_FILE=/run/secrets/flask_secret_key
PLATFORM_ENCRYPTION_KEY_FILE=/run/secrets/platform_encryption_key

# External Ollama API
OLLAMA_URL=http://host.docker.internal:11434

# Security
FLASK_ENV=production
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true

# Observability
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000
LOKI_URL=http://loki:3100
```

### 4. Deploy Services
```bash
# Start all services
docker-compose up -d

# Verify deployment
docker-compose ps
docker-compose logs -f vedfolnir
```

### 5. Initial Setup
```bash
# Wait for services to be ready
./scripts/wait-for-services.sh

# Initialize database
docker-compose exec vedfolnir python scripts/setup/initialize_database.py

# Create admin user
docker-compose exec vedfolnir python scripts/setup/create_admin_user.py

# Verify deployment
curl -f http://localhost/health
```

## Detailed Configuration

### Service Architecture

The Docker Compose deployment includes:

- **vedfolnir**: Main application container (Flask + RQ workers)
- **mysql**: Database service (MySQL 8.0)
- **redis**: Session storage and queue backend (Redis 7)
- **nginx**: Reverse proxy with SSL termination
- **vault**: Secrets management (HashiCorp Vault)
- **prometheus**: Metrics collection
- **grafana**: Monitoring dashboards
- **loki**: Log aggregation

### Volume Mounts

```yaml
# Application data
./storage:/app/storage          # Images, backups, temp files
./logs:/app/logs               # Application logs
./config:/app/config           # Configuration files

# Database persistence
./data/mysql:/var/lib/mysql    # MySQL data
./data/redis:/data             # Redis data

# Monitoring data
./data/prometheus:/prometheus   # Metrics data
./data/grafana:/var/lib/grafana # Dashboards
./data/loki:/loki              # Log data

# Security
./data/vault:/vault/data       # Vault data
./secrets:/run/secrets         # Secret files
```

### Network Configuration

```yaml
networks:
  vedfolnir_internal:
    driver: bridge
    internal: true
  vedfolnir_monitoring:
    driver: bridge
    internal: true
  vedfolnir_external:
    driver: bridge
```

**Security Features:**
- Internal networks for service communication
- Only Nginx and Grafana exposed to host
- Database and Redis isolated from external access

### Resource Limits

```yaml
# Application container
vedfolnir:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '1.0'
        memory: 1G

# Database container
mysql:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
```

## Development vs Production

### Development Configuration
```bash
# Use development compose file
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Features:
# - Hot reloading enabled
# - Debug mode active
# - Direct port access for debugging
# - Development tools included
```

### Production Configuration
```bash
# Use production compose file
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Features:
# - Optimized resource limits
# - Security hardening
# - SSL/TLS termination
# - Monitoring and alerting
```

## SSL/TLS Configuration

### Self-Signed Certificates (Development)
```bash
# Generate certificates
mkdir -p ssl/{certs,keys}
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/keys/vedfolnir.key \
  -out ssl/certs/vedfolnir.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### Production Certificates
```bash
# Using Let's Encrypt with certbot
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/certs/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/keys/
```

## Backup and Recovery

### Automated Backup
```bash
# Run backup script
./scripts/backup/create_backup.sh

# Backup includes:
# - MySQL database dump
# - Redis data snapshot
# - Application storage
# - Configuration files
# - Vault secrets (encrypted)
```

### Manual Backup
```bash
# Database backup
docker-compose exec mysql mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  --all-databases | gzip > backup_$(date +%Y%m%d).sql.gz

# Redis backup
docker-compose exec redis redis-cli BGSAVE
docker cp vedfolnir_redis:/data/dump.rdb ./backup_redis_$(date +%Y%m%d).rdb

# Application data
tar -czf backup_storage_$(date +%Y%m%d).tar.gz storage/
```

### Disaster Recovery
```bash
# Restore from backup
./scripts/backup/restore_backup.sh /path/to/backup

# Manual restore process:
# 1. Stop services
docker-compose down

# 2. Restore database
gunzip < backup_20250101.sql.gz | docker-compose exec -T mysql mysql

# 3. Restore Redis
docker cp backup_redis_20250101.rdb vedfolnir_redis:/data/dump.rdb

# 4. Restore application data
tar -xzf backup_storage_20250101.tar.gz

# 5. Start services
docker-compose up -d
```

## Monitoring and Observability

### Grafana Dashboards
Access: http://localhost:3000
- Default credentials: admin/admin (change on first login)
- Pre-configured dashboards for all services
- Real-time metrics and alerting

### Prometheus Metrics
Access: http://localhost:9090 (internal)
- Application performance metrics
- Container resource usage
- Database and Redis metrics
- Custom business metrics

### Log Aggregation
- Centralized logging with Loki
- Structured JSON logs
- Real-time log streaming
- Log retention policies

### Health Checks
```bash
# Check all services
docker-compose ps

# Application health
curl -f http://localhost/health

# Database connectivity
docker-compose exec vedfolnir python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    result = session.execute('SELECT 1').scalar()
    print(f'Database OK: {result}')
"

# Redis connectivity
docker-compose exec redis redis-cli ping

# Ollama API connectivity
docker-compose exec vedfolnir curl -f http://host.docker.internal:11434/api/version
```

## Security Configuration

### Secrets Management
- HashiCorp Vault for secure secret storage
- Docker secrets for sensitive environment variables
- Automatic secret rotation capabilities
- Encrypted credential storage

### Network Security
- Multi-tier network isolation
- Internal container networking
- SSL/TLS termination at Nginx
- Rate limiting and DDoS protection

### Access Controls
- Role-based access control (RBAC)
- CSRF protection enabled
- Input validation and sanitization
- Audit logging for all actions

### Compliance Features
- GDPR compliance with data anonymization
- Immutable audit logs
- Data retention policies
- Automated compliance reporting

## Performance Optimization

### Container Optimization
- Multi-stage Docker builds
- Minimal base images (python:3.12-slim)
- Layer caching optimization
- Resource limit configuration

### Database Performance
- Connection pooling (20 connections, 30 overflow)
- MySQL performance tuning
- Optimized indexes and queries
- Regular maintenance procedures

### Caching Strategy
- Redis session caching
- Static file caching via Nginx
- Application-level caching
- CDN integration support

## Scaling Configuration

### Horizontal Scaling
```yaml
# Scale application containers
vedfolnir:
  deploy:
    replicas: 3
    update_config:
      parallelism: 1
      delay: 10s
      failure_action: rollback
```

### Load Balancing
- Nginx upstream configuration
- Session affinity with Redis
- Health check integration
- Automatic failover

### Auto-scaling
```bash
# Enable auto-scaling based on CPU usage
docker service update --replicas-max-per-node 2 vedfolnir_vedfolnir
```

## Maintenance Procedures

### Regular Maintenance
```bash
# Update containers
docker-compose pull
docker-compose up -d

# Clean up unused resources
docker system prune -f

# Rotate logs
docker-compose exec vedfolnir logrotate /etc/logrotate.conf

# Update SSL certificates
certbot renew
docker-compose restart nginx
```

### Database Maintenance
```bash
# Optimize database
docker-compose exec mysql mysqlcheck --optimize --all-databases

# Update statistics
docker-compose exec mysql mysqlcheck --analyze --all-databases

# Check for corruption
docker-compose exec mysql mysqlcheck --check --all-databases
```

### Security Updates
```bash
# Update base images
docker-compose build --pull --no-cache

# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image vedfolnir_vedfolnir

# Update secrets
./scripts/security/rotate_secrets.sh
```

## Integration Testing

### Automated Testing
```bash
# Run integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Test specific functionality
./scripts/test/test_platform_integration.sh
./scripts/test/test_ollama_integration.sh
./scripts/test/test_websocket_functionality.sh
```

### Manual Testing
```bash
# Test web interface
curl -f http://localhost/
curl -f http://localhost/login
curl -f http://localhost/health

# Test API endpoints
curl -f http://localhost/api/health
curl -f http://localhost/api/platforms

# Test WebSocket connectivity
wscat -c ws://localhost/ws/progress
```

## Migration from macOS

See the dedicated [Migration Guide](migration-from-macos-guide.md) for detailed instructions on migrating from the previous macOS deployment.

## Support and Resources

### Documentation
- [Troubleshooting Guide](docker-compose-troubleshooting-guide.md)
- [Migration Guide](migration-from-macos-guide.md)
- [Operations Guide](docker-compose-operations-guide.md)
- [Security Guide](docker-compose-security-guide.md)

### Community
- GitHub Issues: Report bugs and feature requests
- Documentation: Contribute to documentation improvements
- Testing: Help test new features and deployments

### Professional Support
For enterprise deployments and professional support, contact the development team for:
- Custom deployment configurations
- Performance optimization consulting
- Security auditing and compliance
- Training and onboarding