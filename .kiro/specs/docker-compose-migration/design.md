# Design Document

## Overview

This design document outlines the architecture and implementation approach for migrating Vedfolnir from macOS hosting to Docker Compose deployment with Debian Linux optimizations. The migration will transform the current macOS-specific setup into a containerized multi-service architecture while maintaining all existing functionality and improving portability, scalability, and deployment consistency.

## Architecture

### Container Architecture

The new Docker Compose architecture will consist of the following services with comprehensive logging, monitoring, and security:

```mermaid
graph TB
    subgraph "Docker Compose Environment"
        subgraph "Application Layer"
            APP[Vedfolnir App Container<br/>python:3.12-slim]
            WORKER[RQ Workers<br/>Integrated in App]
        end
        
        subgraph "Data Layer"
            MYSQL[(MySQL 8.0<br/>Database)]
            REDIS[(Redis 7<br/>Session & Queue)]
        end
        
        subgraph "External AI Layer"
            OLLAMA[Ollama Service<br/>Host System<br/>LLaVA Model]
        end
        
        subgraph "Proxy Layer"
            NGINX[Nginx<br/>Reverse Proxy + SSL]
        end
        
        subgraph "Observability Layer"
            PROMETHEUS[Prometheus<br/>Metrics Collection]
            GRAFANA[Grafana<br/>Monitoring Dashboard]
            LOKI[Loki<br/>Log Aggregation]
        end
        
        subgraph "Security Layer"
            VAULT[HashiCorp Vault<br/>Secrets Management]
            AUDIT[Audit Logger<br/>Compliance Logging]
        end
        
        subgraph "Host Volumes"
            CONFIG[Configuration<br/>./config:/app/config]
            STORAGE[Storage<br/>./storage:/app/storage]
            LOGS[Logs<br/>./logs:/app/logs]
            MYSQL_DATA[MySQL Data<br/>./data/mysql:/var/lib/mysql]
            REDIS_DATA[Redis Data<br/>./data/redis:/data]
            SECRETS[Secrets<br/>./secrets:/vault/secrets]
            BACKUPS[Backups<br/>./backups:/app/backups]
        end
    end
    
    NGINX --> APP
    APP --> MYSQL
    APP --> REDIS
    APP -.-> OLLAMA
    APP --> VAULT
    WORKER --> REDIS
    
    PROMETHEUS --> APP
    PROMETHEUS --> MYSQL
    PROMETHEUS --> REDIS
    GRAFANA --> PROMETHEUS
    LOKI --> APP
    LOKI --> NGINX
    AUDIT --> APP
    
    CONFIG -.-> APP
    STORAGE -.-> APP
    LOGS -.-> LOKI
    MYSQL_DATA -.-> MYSQL
    REDIS_DATA -.-> REDIS
    SECRETS -.-> VAULT
    BACKUPS -.-> APP
```

### Service Dependencies and Networking

```mermaid
graph TD
    subgraph "Internal Network (vedfolnir_internal)"
        A[MySQL Container] --> B[Redis Container]
        B --> D[Vedfolnir App Container]
        D --> E[Nginx Container]
        
        F[Vault Container] --> D
        G[Prometheus Container] --> D
        G --> A
        G --> B
        H[Loki Container] --> D
        H --> E
        I[Grafana Container] --> G
    end
    
    subgraph "External Network"
        J[Internet] --> E
        K[Admin Access] --> I
        L[Monitoring] --> G
    end
    
    subgraph "Host System (External)"
        O[Ollama API Service<br/>Pre-configured<br/>Not managed by project]
    end
    
    D -.-> O
    
    subgraph "Health Monitoring"
        M[Health Checks] --> A
        M --> B
        M --> D
        M --> E
        M --> F
        M --> G
        M --> H
        M --> I
        M -.-> O
    end
```

### Network Security Design

**Internal Networks:**
- `vedfolnir_internal`: Isolated network for service-to-service communication
- `vedfolnir_monitoring`: Separate network for monitoring services
- `vedfolnir_external`: DMZ network for external-facing services

**Port Exposure Strategy:**
- Only Nginx (80/443) and Grafana (3000) exposed to host
- All other services communicate via internal networks
- Database and Redis accessible only from application containers

## Components and Interfaces

### 1. Vedfolnir Application Container

**Base Image:** `python:3.12-slim`

**Key Components:**
- Flask web application
- Integrated RQ workers (maintaining current pattern)
- WebSocket support via eventlet
- Session management with Redis
- Platform integrations (ActivityPub)

**Optimizations for Debian:**
- Remove macOS-specific dependencies (pyenv, Homebrew packages)
- Use apt-get for system dependencies
- Optimize for container size and startup time
- Multi-stage build for production

**Container Configuration:**
```dockerfile
FROM python:3.12-slim as base

# System dependencies for Debian
RUN apt-get update && apt-get install -y \
    curl \
    default-mysql-client \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Application setup
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r vedfolnir && useradd -r -g vedfolnir vedfolnir
RUN chown -R vedfolnir:vedfolnir /app

USER vedfolnir
EXPOSE 5000

CMD ["gunicorn", "--config", "gunicorn.conf.py", "web_app:app"]
```

### 2. MySQL Database Container

**Image:** `mysql:8.0`

**Configuration:**
- UTF8MB4 character set for proper Unicode support
- Optimized for containerized environment
- Performance tuning for typical workloads
- Persistent data storage via host volumes

**Volume Mounts:**
- `./data/mysql:/var/lib/mysql` - Database data persistence
- `./config/mysql:/etc/mysql/conf.d` - Custom configuration
- `./backups/mysql:/backups` - Backup storage

### 3. Redis Container

**Image:** `redis:7-alpine`

**Configuration:**
- Session storage optimization
- RQ queue management
- Memory management policies
- Persistent data storage

**Volume Mounts:**
- `./data/redis:/data` - Redis data persistence
- `./config/redis/redis.conf:/usr/local/etc/redis/redis.conf` - Configuration

### 4. Ollama API Integration (External Service)

**Deployment:** External service (not managed by this project)

**Integration Requirements:**
- External Ollama service assumed to be running on host system at localhost:11434
- Application connects via host.docker.internal:11434 from containers
- API endpoint must be accessible for LLaVA model image captioning
- No configuration or management of Ollama service by this project

**Benefits of External Integration:**
- Separation of concerns - AI service managed independently
- No container orchestration complexity for GPU-intensive workloads
- Ollama service can be shared across multiple applications
- Simplified Docker Compose architecture

### 5. Nginx Reverse Proxy Container

**Image:** `nginx:alpine`

**Configuration:**
- SSL/TLS termination
- Rate limiting
- Static file serving
- WebSocket proxy support
- Security headers

**Volume Mounts:**
- `./config/nginx:/etc/nginx/conf.d` - Nginx configuration
- `./ssl:/etc/nginx/ssl` - SSL certificates
- `./logs/nginx:/var/log/nginx` - Access logs

### 6. HashiCorp Vault Container (Secrets Management)

**Image:** `vault:latest`

**Configuration:**
- Secure secrets storage and rotation
- Database credential management
- Encryption key management
- API token storage
- Integration with application containers

**Volume Mounts:**
- `./data/vault:/vault/data` - Vault data persistence
- `./config/vault:/vault/config` - Vault configuration
- `./logs/vault:/vault/logs` - Vault audit logs

### 7. Prometheus Container (Metrics Collection)

**Image:** `prom/prometheus:latest`

**Configuration:**
- Application metrics collection
- Container resource monitoring
- Database performance metrics
- Custom business metrics
- Alert rule management

**Volume Mounts:**
- `./config/prometheus:/etc/prometheus` - Prometheus configuration
- `./data/prometheus:/prometheus` - Metrics data storage

### 8. Grafana Container (Monitoring Dashboard)

**Image:** `grafana/grafana:latest`

**Configuration:**
- Real-time monitoring dashboards
- Alert visualization
- Performance analytics
- Resource usage tracking
- Custom dashboard creation

**Volume Mounts:**
- `./data/grafana:/var/lib/grafana` - Dashboard and data persistence
- `./config/grafana:/etc/grafana` - Grafana configuration

### 9. Loki Container (Log Aggregation)

**Image:** `grafana/loki:latest`

**Configuration:**
- Centralized log collection
- Log parsing and indexing
- Log retention policies
- Integration with Grafana
- Structured logging support

**Volume Mounts:**
- `./data/loki:/loki` - Log data storage
- `./config/loki:/etc/loki` - Loki configuration

## Data Models

### Volume Mount Strategy

```yaml
# Host directory structure
vedfolnir-docker/
├── config/
│   ├── mysql/
│   │   └── vedfolnir.cnf
│   ├── redis/
│   │   └── redis.conf
│   ├── nginx/
│   │   └── default.conf
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── rules/
│   ├── grafana/
│   │   ├── grafana.ini
│   │   └── dashboards/
│   ├── loki/
│   │   └── loki.yml
│   ├── vault/
│   │   └── vault.hcl
│   └── app/
│       └── .env
├── data/
│   ├── mysql/
│   ├── redis/
│   ├── prometheus/
│   ├── grafana/
│   ├── loki/
│   └── vault/
├── storage/
│   ├── images/
│   ├── backups/
│   │   ├── mysql/
│   │   ├── redis/
│   │   └── app/
│   └── temp/
├── logs/
│   ├── app/
│   ├── nginx/
│   ├── mysql/
│   ├── vault/
│   └── audit/
├── ssl/
│   ├── certs/
│   └── keys/
└── secrets/
    ├── database/
    ├── redis/
    └── app/
```

### Environment Configuration and Secrets Management

**Docker Compose Environment Variables:**
```yaml
environment:
  # Database connections use container networking
  - DATABASE_URL=mysql+pymysql://vedfolnir:${MYSQL_PASSWORD}@mysql:3306/vedfolnir?charset=utf8mb4
  - REDIS_URL=redis://redis:6379/0
  # Ollama runs on host system, accessed via host.docker.internal
  - OLLAMA_URL=http://host.docker.internal:11434
  
  # Application configuration
  - FLASK_ENV=${FLASK_ENV:-production}
  - FLASK_SECRET_KEY_FILE=/run/secrets/flask_secret_key
  - PLATFORM_ENCRYPTION_KEY_FILE=/run/secrets/platform_encryption_key
  
  # RQ Configuration
  - RQ_ENABLE_INTEGRATED_WORKERS=true
  - RQ_ENABLE_EXTERNAL_WORKERS=false
  
  # Observability configuration
  - PROMETHEUS_URL=http://prometheus:9090
  - LOKI_URL=http://loki:3100
  - GRAFANA_URL=http://grafana:3000
  
  # Vault configuration
  - VAULT_ADDR=http://vault:8200
  - VAULT_TOKEN_FILE=/run/secrets/vault_token
  
  # Resource limits
  - MEMORY_LIMIT=2g
  - CPU_LIMIT=2
```

**Docker Secrets Configuration:**
```yaml
secrets:
  flask_secret_key:
    file: ./secrets/flask_secret_key.txt
  platform_encryption_key:
    file: ./secrets/platform_encryption_key.txt
  mysql_root_password:
    file: ./secrets/mysql_root_password.txt
  mysql_password:
    file: ./secrets/mysql_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
  vault_token:
    file: ./secrets/vault_token.txt
```

### Requirements.txt Optimization

**Removed macOS Dependencies:**
- Remove any Homebrew-specific packages
- Remove pyenv-related dependencies
- Remove macOS-specific system library bindings

**Added Container Optimizations:**
```txt
# Core dependencies (unchanged)
requests>=2.31.0
Pillow>=10.0.0
flask>=2.3.0
sqlalchemy>=2.0.0
redis>=5.0.0
rq>=1.16.0
pymysql>=1.1.0

# Container-optimized additions
gunicorn>=23.0.0
eventlet>=0.33.0

# Remove macOS-specific packages
# (Any packages that were macOS-specific will be identified and removed)
```

## Error Handling

### Container Health Checks

**Application Health Check:**
```bash
#!/bin/bash
# Health check script
curl -f http://localhost:5000/health || exit 1
python -c "
from app.core.database.core.database_manager import DatabaseManager
from config import Config
try:
    config = Config()
    db_manager = DatabaseManager(config)
    with db_manager.get_session() as session:
        session.execute('SELECT 1')
    print('Database OK')
except Exception as e:
    print(f'Database error: {e}')
    exit(1)
"
```

**Service Dependencies:**
```yaml
depends_on:
  mysql:
    condition: service_healthy
  redis:
    condition: service_healthy
  ollama:
    condition: service_started
```

### Graceful Shutdown

**Application Container:**
- Implement proper signal handling for SIGTERM
- Complete current RQ jobs before shutdown
- Close database connections gracefully
- Save session data to Redis

**Database Containers:**
- Ensure data consistency on shutdown
- Proper transaction completion
- Clean connection termination

## Development Workflow and Testing Strategy

### Development Environment Configuration

**Docker Compose Override for Development:**
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  vedfolnir:
    build:
      target: development
    volumes:
      - .:/app  # Mount source code for hot reloading
      - /app/node_modules  # Exclude node_modules
    environment:
      - FLASK_DEBUG=true
      - LOG_LEVEL=DEBUG
      - FLASK_ENV=development
    ports:
      - "5000:5000"  # Direct access for debugging
      - "5678:5678"  # Python debugger port
    command: ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "web_app.py"]
  
  # Development-specific services
  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI
    networks:
      - vedfolnir_internal
```

### Multi-Stage Dockerfile for Development
```dockerfile
# Multi-stage build for development and production
FROM python:3.12-slim as base
# ... base configuration ...

FROM base as development
# Development-specific packages
RUN pip install debugpy pytest pytest-cov black flake8 mypy
# Enable hot reloading
ENV FLASK_DEBUG=1
ENV PYTHONPATH=/app
EXPOSE 5678
CMD ["python", "web_app.py"]

FROM base as production
# Production optimizations
RUN pip install --no-cache-dir gunicorn
USER vedfolnir
CMD ["gunicorn", "--config", "gunicorn.conf.py", "web_app:app"]
```

### Comprehensive Testing Framework

**1. Unit Testing in Containers:**
```yaml
# docker-compose.test.yml
version: '3.8'
services:
  test-runner:
    build:
      context: .
      target: development
    volumes:
      - .:/app
      - ./test-results:/app/test-results
    environment:
      - TESTING=true
      - DATABASE_URL=mysql+pymysql://test:test@mysql-test:3306/vedfolnir_test
    depends_on:
      - mysql-test
      - redis-test
    command: ["python", "-m", "pytest", "-v", "--cov=app", "--cov-report=html:/app/test-results/coverage"]
  
  mysql-test:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: testroot
      MYSQL_DATABASE: vedfolnir_test
      MYSQL_USER: test
      MYSQL_PASSWORD: test
    tmpfs:
      - /var/lib/mysql  # In-memory database for faster tests
  
  redis-test:
    image: redis:7-alpine
    tmpfs:
      - /data  # In-memory Redis for tests
```

**2. Integration Testing:**
```bash
#!/bin/bash
# integration_test.sh
set -e

echo "Starting integration test suite..."

# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be ready
./scripts/wait-for-services.sh

# Run integration tests
docker-compose -f docker-compose.test.yml exec test-runner python -m pytest tests/integration/ -v

# Test container-to-container communication
docker-compose -f docker-compose.test.yml exec test-runner python tests/integration/test_service_communication.py

# Test ActivityPub platform integration
docker-compose -f docker-compose.test.yml exec test-runner python tests/integration/test_platform_integration.py

# Test Ollama AI integration
docker-compose -f docker-compose.test.yml exec test-runner python tests/integration/test_ollama_integration.py

# Test WebSocket functionality
docker-compose -f docker-compose.test.yml exec test-runner python tests/integration/test_websocket_functionality.py

# Cleanup
docker-compose -f docker-compose.test.yml down -v

echo "Integration tests completed successfully"
```

**3. Migration Validation Testing:**
```python
# tests/migration/test_migration_validation.py
import unittest
import docker
import mysql.connector
import redis
import requests

class MigrationValidationTest(unittest.TestCase):
    def setUp(self):
        self.client = docker.from_env()
        self.base_url = "http://localhost:5000"
    
    def test_database_migration(self):
        """Test MySQL data migration from macOS"""
        # Verify database schema
        # Verify data integrity
        # Test performance benchmarks
        pass
    
    def test_redis_session_migration(self):
        """Test Redis session data migration"""
        # Verify session data structure
        # Test session functionality
        pass
    
    def test_application_functionality_parity(self):
        """Test that all features work identically to macOS deployment"""
        # Test web interface
        # Test API endpoints
        # Test WebSocket connections
        # Test caption generation
        pass
    
    def test_performance_parity(self):
        """Ensure performance matches macOS deployment"""
        # Load testing
        # Response time validation
        # Resource usage comparison
        pass
```

### CI/CD Pipeline Integration
```yaml
# .github/workflows/docker-compose-ci.yml
name: Docker Compose CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build test environment
        run: docker-compose -f docker-compose.test.yml build
      
      - name: Run unit tests
        run: docker-compose -f docker-compose.test.yml run --rm test-runner
      
      - name: Run integration tests
        run: ./scripts/integration_test.sh
      
      - name: Run security scans
        run: |
          docker run --rm -v $(pwd):/app clair-scanner
          docker run --rm -v $(pwd):/app anchore/grype
      
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./test-results/coverage/coverage.xml
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to staging
        run: ./scripts/deploy-staging.sh
      
      - name: Run smoke tests
        run: ./scripts/smoke-tests.sh
      
      - name: Deploy to production
        run: ./scripts/deploy-production.sh
```

### Validation Scripts

**Migration Validation:**
```bash
#!/bin/bash
# validate_migration.sh

echo "Validating Docker Compose migration..."

# Check container health
docker-compose ps
docker-compose exec vedfolnir curl -f http://localhost:5000/health

# Test database connectivity
docker-compose exec vedfolnir python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    result = session.execute('SELECT COUNT(*) FROM users').scalar()
    print(f'Users in database: {result}')
"

# Test Redis connectivity
docker-compose exec redis redis-cli ping

# Test external Ollama API connectivity from container
docker-compose exec vedfolnir curl -f http://host.docker.internal:11434/api/version

echo "Migration validation complete"
```

## Migration Strategy

### Phase 1: Container Preparation
1. Create Dockerfile optimized for python:3.12-slim
2. Update requirements.txt for Debian compatibility
3. Create Docker Compose configuration files
4. Set up volume mount structure

### Phase 2: Service Migration
1. Migrate MySQL data to containerized MySQL
2. Migrate Redis data to containerized Redis
3. Update application configuration for container networking
4. Test integrated RQ workers in container environment

### Phase 3: Deployment Automation
1. Create deployment scripts
2. Implement health checks and monitoring
3. Set up backup procedures for containerized data
4. Create management scripts for common operations

### Phase 4: Validation and Documentation
1. Comprehensive testing of all functionality
2. Performance validation against macOS deployment
3. Create deployment documentation
4. Provide migration procedures and rollback plans

## Security Architecture

### Container Security
- Run all applications as non-root users
- Use minimal base images (alpine/slim variants)
- Regular security updates via automated scanning
- Read-only root filesystems where possible
- Security context constraints and capabilities dropping

### Secrets Management with HashiCorp Vault
```yaml
# Vault integration pattern
vault:
  image: vault:latest
  environment:
    VAULT_DEV_ROOT_TOKEN_ID: ${VAULT_ROOT_TOKEN}
    VAULT_DEV_LISTEN_ADDRESS: 0.0.0.0:8200
  volumes:
    - vault_data:/vault/data
    - ./config/vault:/vault/config
  networks:
    - vedfolnir_internal
  healthcheck:
    test: ["CMD", "vault", "status"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Secret Rotation Strategy:**
- Automated secret rotation every 90 days
- Zero-downtime secret updates
- Audit trail for all secret access
- Integration with application startup

### Network Security
- Multi-tier network isolation
- Internal container networking with custom bridge networks
- Nginx SSL termination with modern TLS protocols
- Rate limiting and DDoS protection
- Security headers (HSTS, CSP, X-Frame-Options)
- Firewall rules for container-to-container communication

### Data Security and Compliance
- Encryption at rest for all persistent volumes
- Encrypted inter-service communication
- Database access controls with least privilege
- Redis authentication and ACLs
- GDPR compliance with data anonymization
- Audit logging for all data access

### Security Monitoring
```yaml
# Security event monitoring
security_monitoring:
  - Container runtime security (Falco integration)
  - Network traffic analysis
  - Failed authentication tracking
  - Privilege escalation detection
  - File integrity monitoring
  - Vulnerability scanning automation
```

## Observability and Monitoring Architecture

### Comprehensive Logging with Loki
```yaml
# Centralized logging configuration
logging:
  driver: loki
  options:
    loki-url: "http://loki:3100/loki/api/v1/push"
    loki-batch-size: "400"
    loki-retries: "3"
    loki-timeout: "1s"
    loki-pipeline-stages: |
      - json:
          expressions:
            level: level
            timestamp: timestamp
            message: message
            service: service
```

**Log Aggregation Strategy:**
- Structured JSON logging across all services
- Log correlation with trace IDs
- Automated log parsing and indexing
- Real-time log streaming to Grafana
- Log retention policies (30 days operational, 1 year audit)

### Metrics Collection with Prometheus
```yaml
# Prometheus scraping configuration
prometheus_config:
  scrape_configs:
    - job_name: 'vedfolnir-app'
      static_configs:
        - targets: ['vedfolnir:5000']
      metrics_path: '/metrics'
      scrape_interval: 15s
    
    - job_name: 'mysql-exporter'
      static_configs:
        - targets: ['mysql-exporter:9104']
    
    - job_name: 'redis-exporter'
      static_configs:
        - targets: ['redis-exporter:9121']
    
    - job_name: 'nginx-exporter'
      static_configs:
        - targets: ['nginx-exporter:9113']
```

**Key Metrics:**
- Application performance (response times, error rates)
- Container resource usage (CPU, memory, disk, network)
- Database performance (query times, connection pools)
- Queue processing metrics (job completion rates, queue depth)
- Business metrics (user activity, caption generation rates)

### Monitoring Dashboards with Grafana
- Real-time system health dashboard
- Application performance monitoring
- Resource utilization tracking
- Alert management and notification
- Custom business intelligence dashboards

### Alerting Strategy
```yaml
# Alert rules configuration
alert_rules:
  - name: "High CPU Usage"
    condition: "cpu_usage > 80%"
    duration: "5m"
    severity: "warning"
    
  - name: "Database Connection Pool Exhausted"
    condition: "mysql_connections_active / mysql_connections_max > 0.9"
    duration: "2m"
    severity: "critical"
    
  - name: "Application Error Rate High"
    condition: "error_rate > 5%"
    duration: "1m"
    severity: "critical"
```

## Resource Management and Scaling

### Container Resource Limits
```yaml
# Resource allocation per service
resources:
  vedfolnir:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
  
  mysql:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
  
  redis:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Horizontal Scaling Strategy
```yaml
# Docker Compose scaling configuration
scaling:
  vedfolnir:
    replicas: 3
    update_config:
      parallelism: 1
      delay: 10s
      failure_action: rollback
    restart_policy:
      condition: on-failure
      delay: 5s
      max_attempts: 3
```

### Performance Optimizations
- Multi-stage Docker builds for minimal image sizes
- Layer caching optimization for faster builds
- Connection pooling optimization for containerized databases
- Redis session optimization with clustering support
- Static file serving via Nginx with caching
- Application-level caching strategies

## Backup and Disaster Recovery

### Automated Backup Strategy
```bash
#!/bin/bash
# Comprehensive backup script
BACKUP_DIR="/app/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# MySQL backup with point-in-time recovery
docker-compose exec mysql mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  --all-databases | gzip > "$BACKUP_DIR/mysql_full.sql.gz"

# Redis backup
docker-compose exec redis redis-cli BGSAVE
docker cp vedfolnir_redis:/data/dump.rdb "$BACKUP_DIR/redis.rdb"

# Application data backup
tar -czf "$BACKUP_DIR/storage.tar.gz" storage/
tar -czf "$BACKUP_DIR/config.tar.gz" config/

# Vault secrets backup (encrypted)
docker-compose exec vault vault operator raft snapshot save /vault/backups/vault_snapshot
docker cp vedfolnir_vault:/vault/backups/vault_snapshot "$BACKUP_DIR/"

# Verify backup integrity
./scripts/verify_backup.sh "$BACKUP_DIR"
```

### Disaster Recovery Procedures
- Automated backup verification
- Cross-region backup replication
- Recovery time objective (RTO): 4 hours
- Recovery point objective (RPO): 1 hour
- Automated failover procedures
- Data consistency validation

## Compliance and Audit Framework

### Audit Logging
```yaml
# Audit logging configuration
audit_config:
  enabled: true
  log_level: "INFO"
  destinations:
    - type: "file"
      path: "/app/logs/audit/audit.log"
    - type: "syslog"
      facility: "local0"
    - type: "elasticsearch"
      endpoint: "http://elasticsearch:9200"
  
  events:
    - user_authentication
    - data_access
    - configuration_changes
    - privilege_escalation
    - data_export
    - system_administration
```

### GDPR Compliance Features
- Data anonymization procedures
- Right to be forgotten implementation
- Data export capabilities
- Consent management tracking
- Data retention policy enforcement
- Privacy impact assessment logging

### Compliance Reporting
- Automated compliance report generation
- Security event correlation
- Access pattern analysis
- Data lineage tracking
- Regulatory requirement mapping