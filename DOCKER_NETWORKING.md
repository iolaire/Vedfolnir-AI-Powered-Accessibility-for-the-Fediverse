# Docker Networking Configuration for Vedfolnir

This document describes the Docker Compose networking configuration for Vedfolnir, including service networking, environment variables, and security isolation.

## Overview

Vedfolnir uses Docker Compose with multi-tier networking for security isolation and proper service communication. All services communicate via internal Docker networks using container hostnames instead of localhost.

## Network Architecture

### Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    External Network                          │
│  ┌─────────────┐                                            │
│  │   Internet  │ ──────► Nginx (80/443)                     │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  Internal Network                           │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────┐  │
│  │  MySQL  │   │  Redis  │   │ Ollama  │   │ Vedfolnir   │  │
│  │ :3306   │   │ :6379   │   │ :11434  │   │ App :5000   │  │
│  └─────────┘   └─────────┘   └─────────┘   └─────────────┘  │
│                                                             │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                   │
│  │  Vault  │   │Prometheus│   │  Loki   │                   │
│  │ :8200   │   │ :9090   │   │ :3100   │                   │
│  └─────────┘   └─────────┘   └─────────┘                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                Monitoring Network                           │
│  ┌─────────────┐                                           │
│  │   Grafana   │ ──────► External Access (3000)            │
│  │   :3000     │                                           │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

### Network Definitions

1. **vedfolnir_internal** (172.20.0.0/16)
   - Internal communication between core services
   - MySQL, Redis, Ollama, Vedfolnir App, Vault
   - No external access

2. **vedfolnir_monitoring** (172.21.0.0/16)
   - Monitoring services communication
   - Prometheus, Grafana, Loki
   - Isolated from core services

3. **vedfolnir_external** (172.22.0.0/16)
   - External-facing services
   - Nginx reverse proxy
   - Public internet access

## Service Networking Configuration

### Database Connections

**MySQL (mysql:3306)**
```bash
# Container networking
DATABASE_URL=mysql+pymysql://vedfolnir:${MYSQL_PASSWORD}@mysql:3306/vedfolnir?charset=utf8mb4

# Traditional localhost (not used in containers)
# DATABASE_URL=mysql+pymysql://vedfolnir:password@localhost:3306/vedfolnir?charset=utf8mb4
```

**Redis (redis:6379)**
```bash
# Container networking
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Traditional localhost (not used in containers)
# REDIS_URL=redis://localhost:6379/0
```

**Ollama AI Service (ollama:11434)**
```bash
# Container networking
OLLAMA_URL=http://ollama:11434

# Traditional localhost (not used in containers)
# OLLAMA_URL=http://localhost:11434
```

### Observability Services

**Prometheus (prometheus:9090)**
```bash
PROMETHEUS_URL=http://prometheus:9090
```

**Grafana (grafana:3000)**
```bash
GRAFANA_URL=http://grafana:3000
```

**Loki (loki:3100)**
```bash
LOKI_URL=http://loki:3100
```

**Vault (vault:8200)**
```bash
VAULT_ADDR=http://vault:8200
```

## Port Exposure Strategy

### Security-First Approach

By default, **NO internal service ports are exposed** to the host system for maximum security:

- ❌ MySQL port 3306 - Not exposed
- ❌ Redis port 6379 - Not exposed  
- ❌ Ollama port 11434 - Not exposed
- ❌ Vault port 8200 - Not exposed
- ❌ Prometheus port 9090 - Not exposed
- ❌ Loki port 3100 - Not exposed
- ❌ Application port 5000 - Not exposed (accessed via Nginx)

### Exposed Ports (Production)

Only essential ports are exposed:

- ✅ **Nginx HTTP**: 80 → External access
- ✅ **Nginx HTTPS**: 443 → External access  
- ✅ **Grafana**: 3000 → Monitoring dashboard access

### Development Port Exposure

For development and debugging, use `docker-compose.dev.yml`:

```bash
# Start with development overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Development mode exposes additional ports:
- MySQL: 127.0.0.1:3306
- Redis: 127.0.0.1:6379
- Ollama: 127.0.0.1:11434
- Vault: 127.0.0.1:8200
- Application: 127.0.0.1:5000
- Prometheus: 127.0.0.1:9090
- Loki: 127.0.0.1:3100

## Environment Configuration

### Container-Specific Variables

The `.env.docker` template provides container-optimized configuration:

```bash
# Docker deployment flag
DOCKER_DEPLOYMENT=true

# Container networking URLs
DATABASE_URL=mysql+pymysql://vedfolnir:${MYSQL_PASSWORD}@mysql:3306/vedfolnir?charset=utf8mb4
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
OLLAMA_URL=http://ollama:11434

# Observability URLs
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000
LOKI_URL=http://loki:3100
VAULT_ADDR=http://vault:8200
```

### Automatic Configuration Detection

The application automatically detects Docker deployment and adjusts URLs:

```python
# config.py automatically handles container networking
if os.getenv("DOCKER_DEPLOYMENT", "false").lower() == "true":
    default_database_url = f"mysql+pymysql://vedfolnir:{mysql_password}@mysql:3306/vedfolnir?charset=utf8mb4"
    default_redis_url = f"redis://:{redis_password}@redis:6379/0"
    default_ollama_url = "http://ollama:11434"
```

## Nginx Reverse Proxy Configuration

### Security Features

- **SSL/TLS Termination**: Modern TLS 1.2/1.3 configuration
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **Rate Limiting**: API, login, and general endpoint protection
- **WebSocket Support**: Real-time features proxy
- **Static File Serving**: Optimized static asset delivery

### Proxy Configuration

```nginx
# Backend upstream
upstream vedfolnir_backend {
    server vedfolnir:5000;
    keepalive 32;
}

# Proxy settings
location / {
    proxy_pass http://vedfolnir_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Secrets Management

### Docker Secrets Integration

Sensitive data is managed via Docker secrets:

```yaml
secrets:
  flask_secret_key:
    file: ./secrets/flask_secret_key.txt
  mysql_password:
    file: ./secrets/mysql_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
```

### Vault Integration

HashiCorp Vault provides additional secrets management:

- Database credential rotation
- API token storage
- Encryption key management
- Audit logging

## Health Checks and Dependencies

### Service Dependencies

```yaml
vedfolnir:
  depends_on:
    mysql:
      condition: service_healthy
    redis:
      condition: service_healthy
    vault:
      condition: service_started
    ollama:
      condition: service_started
```

### Health Check Endpoints

- **MySQL**: `mysqladmin ping`
- **Redis**: `redis-cli ping`
- **Ollama**: `GET /api/version`
- **Vault**: `GET /v1/sys/health`
- **Application**: `GET /health`
- **Nginx**: `GET /health`

## Management Commands

### Quick Start

```bash
# Generate secrets
./scripts/docker/manage_compose.sh generate-secrets

# Start services
./scripts/docker/manage_compose.sh start

# Check status
./scripts/docker/manage_compose.sh status

# Validate networking
./scripts/docker/manage_compose.sh validate
```

### Development Mode

```bash
# Start in development mode (exposes ports)
./scripts/docker/manage_compose.sh start dev

# View logs
./scripts/docker/manage_compose.sh logs vedfolnir -f
```

### Maintenance

```bash
# Backup data
./scripts/docker/manage_compose.sh backup

# Update containers
./scripts/docker/manage_compose.sh update

# Clean up resources
./scripts/docker/manage_compose.sh cleanup
```

## Validation and Troubleshooting

### Network Validation

Run the network validation script to test all connections:

```bash
python3 scripts/setup/validate_docker_networking.py
```

This tests:
- ✅ MySQL connection (mysql:3306)
- ✅ Redis connection (redis:6379)
- ✅ Ollama API (ollama:11434)
- ✅ Vault API (vault:8200)
- ✅ Prometheus API (prometheus:9090)
- ✅ Grafana API (grafana:3000)
- ✅ Loki API (loki:3100)

### Common Issues

**Service Not Accessible**
```bash
# Check if service is running
docker-compose ps

# Check service logs
docker-compose logs <service_name>

# Test network connectivity
docker-compose exec vedfolnir ping mysql
```

**Database Connection Failed**
```bash
# Verify MySQL password
cat secrets/mysql_password.txt

# Check MySQL logs
docker-compose logs mysql

# Test MySQL connection
docker-compose exec mysql mysql -u vedfolnir -p vedfolnir
```

**Redis Connection Failed**
```bash
# Verify Redis password
cat secrets/redis_password.txt

# Test Redis connection
docker-compose exec redis redis-cli -a $(cat secrets/redis_password.txt) ping
```

## Security Considerations

### Network Isolation

- Internal services cannot be accessed directly from the host
- Services communicate only via defined Docker networks
- Monitoring services are isolated from core application services

### Credential Security

- All passwords stored in Docker secrets with restricted permissions
- Vault provides additional encryption and rotation capabilities
- No credentials stored in environment variables or logs

### SSL/TLS Configuration

- Modern TLS protocols (1.2/1.3) only
- Strong cipher suites
- HSTS and security headers enabled
- OCSP stapling for certificate validation

## Performance Optimization

### Connection Pooling

- MySQL: Optimized connection pool settings
- Redis: Connection pooling and keepalive
- Nginx: Upstream keepalive connections

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
```

### Caching Strategy

- Nginx static file caching
- Redis session and queue caching
- Application-level caching where appropriate

## Migration from localhost

### Configuration Changes Required

1. **Update .env file**:
   ```bash
   cp .env.docker .env
   # Edit .env with your specific values
   ```

2. **Generate secrets**:
   ```bash
   python3 scripts/setup/generate_docker_secrets.py
   ```

3. **Update application code** (if needed):
   - Set `DOCKER_DEPLOYMENT=true`
   - Application automatically detects and uses container networking

4. **Start services**:
   ```bash
   docker-compose up -d
   ```

5. **Validate configuration**:
   ```bash
   python3 scripts/setup/validate_docker_networking.py
   ```

## Monitoring and Observability

### Metrics Collection

- **Prometheus**: Collects metrics from all services
- **Grafana**: Visualizes metrics and provides dashboards
- **Custom Metrics**: Application performance and business metrics

### Log Aggregation

- **Loki**: Centralized log collection and indexing
- **Structured Logging**: JSON format for better parsing
- **Log Retention**: Configurable retention policies

### Alerting

- **Grafana Alerts**: Threshold-based alerting
- **Prometheus Rules**: Custom alert rules
- **Notification Channels**: Email, Slack, webhook integration

This networking configuration provides a secure, scalable, and maintainable foundation for Vedfolnir's Docker Compose deployment.