# Docker Health Checks and Service Dependencies

## Overview

This document describes the comprehensive health check system and service dependency management implemented for the Vedfolnir Docker Compose deployment. The system ensures reliable service startup, proper dependency handling, and comprehensive monitoring capabilities.

## Health Check System

### Application Health Endpoints

The Vedfolnir application provides multiple health check endpoints for different monitoring needs:

#### Main Health Endpoint
- **URL**: `http://localhost:5000/health`
- **Purpose**: Comprehensive health status of all application components
- **Response**: JSON with detailed component status
- **Usage**: Docker health checks, monitoring systems

#### Readiness Endpoint
- **URL**: `http://localhost:5000/health/ready`
- **Purpose**: Kubernetes/Docker orchestration readiness check
- **Response**: JSON indicating if service is ready to serve traffic
- **Usage**: Load balancer health checks

#### Liveness Endpoint
- **URL**: `http://localhost:5000/health/live`
- **Purpose**: Simple liveness check for container orchestration
- **Response**: JSON with uptime information
- **Usage**: Container restart decisions

#### Metrics Endpoint
- **URL**: `http://localhost:5000/metrics`
- **Purpose**: Prometheus-compatible metrics
- **Response**: Prometheus format metrics
- **Usage**: Monitoring and alerting systems

### Health Check Scripts

#### Vedfolnir Application Health Check
- **Script**: `docker/scripts/vedfolnir-health-check.sh`
- **Purpose**: Comprehensive application container health validation
- **Checks**:
  - Application endpoint responsiveness
  - Gunicorn process status
  - Database connectivity
  - Redis connectivity
  - RQ workers status
  - System resources (CPU, memory, disk)
  - File permissions

**Usage Examples**:
```bash
# Default comprehensive check
./docker/scripts/vedfolnir-health-check.sh

# Verbose output
./docker/scripts/vedfolnir-health-check.sh verbose

# Quick endpoint check only
./docker/scripts/vedfolnir-health-check.sh quick
```

#### MySQL Health Check
- **Script**: `docker/scripts/mysql-health-check.sh`
- **Purpose**: Enhanced MySQL container health validation
- **Checks**:
  - Basic connectivity (ping)
  - Database access
  - Connection count monitoring
  - InnoDB engine status
  - Disk space usage

**Usage Examples**:
```bash
# Basic check (used by Docker health check)
./docker/scripts/mysql-health-check.sh basic

# Full comprehensive check
./docker/scripts/mysql-health-check.sh full
```

#### Redis Health Check
- **Script**: `docker/scripts/redis-health-check.sh`
- **Purpose**: Redis container health validation
- **Checks**:
  - Ping test
  - Basic operations (SET/GET)
  - Memory usage monitoring
  - Replication status
  - Persistence status (RDB/AOF)

#### Ollama Health Check
- **Script**: `docker/scripts/docker_ollama_health.sh`
- **Purpose**: External Ollama API connectivity validation
- **Checks**:
  - Host connectivity
  - API version endpoint
  - Tags endpoint
  - LLaVA model availability

**Usage Examples**:
```bash
# Comprehensive check
./docker/scripts/docker_ollama_health.sh

# Quick version check only
./docker/scripts/docker_ollama_health.sh quick

# Connectivity test only
./docker/scripts/docker_ollama_health.sh connectivity
```

#### Monitoring Services Health Checks
- **Prometheus**: `docker/scripts/prometheus-health-check.sh`
- **Grafana**: `docker/scripts/grafana-health-check.sh`
- **Loki**: `docker/scripts/loki-health-check.sh`

Each monitoring service health check validates:
- Service-specific health endpoints
- Configuration validity
- Storage status
- Process status

## Service Dependencies

### Dependency Hierarchy

```
External Services
├── Ollama API (host.docker.internal:11434)

Infrastructure Layer
├── MySQL Database (critical)
├── Redis Cache (critical)
└── Vault Secrets (important)

Application Layer
├── Vedfolnir Application (depends: MySQL, Redis)
└── Nginx Reverse Proxy (depends: Vedfolnir)

Monitoring Layer
├── Prometheus (depends: application services)
├── Loki (independent)
└── Grafana (depends: Prometheus)

Metrics Exporters
├── MySQL Exporter (depends: MySQL)
├── Redis Exporter (depends: Redis)
├── Nginx Exporter (depends: Nginx)
├── Node Exporter (independent)
└── cAdvisor (independent)
```

### Service Startup Order

1. **Infrastructure Services** (Stage 1)
   - MySQL Database
   - Redis Cache
   - Vault Secrets Manager

2. **Database Initialization** (Stage 2)
   - Schema creation
   - Migrations
   - Initial admin user

3. **Application Services** (Stage 3)
   - Vedfolnir Application
   - Nginx Reverse Proxy

4. **Monitoring Services** (Stage 4)
   - Prometheus
   - Loki
   - Grafana

5. **Metrics Exporters** (Stage 5)
   - All metrics exporters

6. **External Validation** (Stage 6)
   - Ollama API connectivity

### Docker Compose Dependencies

The Docker Compose configuration uses proper `depends_on` with health conditions:

```yaml
vedfolnir:
  depends_on:
    mysql:
      condition: service_healthy
    redis:
      condition: service_healthy
    vault:
      condition: service_started

nginx:
  depends_on:
    - vedfolnir

grafana:
  depends_on:
    - prometheus
```

## Service Management Scripts

### Service Startup Coordinator
- **Script**: `docker/scripts/service-startup-coordinator.sh`
- **Purpose**: Orchestrates proper service startup with dependencies
- **Features**:
  - Stage-based startup
  - Dependency validation
  - Health check integration
  - Timeout handling
  - Dry-run capability

**Usage Examples**:
```bash
# Full startup (all services)
./docker/scripts/service-startup-coordinator.sh full

# Critical services only
./docker/scripts/service-startup-coordinator.sh quick

# Infrastructure services only
./docker/scripts/service-startup-coordinator.sh infrastructure

# Show what would be done
./docker/scripts/service-startup-coordinator.sh dry-run
```

### Service Restart Manager
- **Script**: `docker/scripts/service-restart-manager.sh`
- **Purpose**: Handles service failures and restart policies
- **Features**:
  - Automatic failure detection
  - Configurable restart attempts
  - Dependent service handling
  - Failure alerting

**Usage Examples**:
```bash
# Monitor all services
./docker/scripts/service-restart-manager.sh monitor

# Restart specific service
./docker/scripts/service-restart-manager.sh restart vedfolnir

# Emergency restart all
./docker/scripts/service-restart-manager.sh emergency
```

### Wait for Services
- **Script**: `docker/scripts/wait-for-services.sh`
- **Purpose**: Waits for service dependencies to be ready
- **Features**:
  - Configurable timeouts
  - Health check integration
  - Database initialization
  - Comprehensive logging

### Database Initialization
- **Script**: `docker/scripts/database-init-migration.sh`
- **Purpose**: Handles database setup and migrations
- **Features**:
  - Schema creation
  - Migration execution
  - Initial admin user creation
  - Backup and restore
  - Integrity validation

**Usage Examples**:
```bash
# Full initialization
./docker/scripts/database-init-migration.sh init

# Run migrations only
./docker/scripts/database-init-migration.sh migrate

# Create backup
./docker/scripts/database-init-migration.sh backup

# Validate database
./docker/scripts/database-init-migration.sh validate
```

## Monitoring and Alerting

### Monitoring Endpoints
- **Script**: `docker/scripts/monitoring-endpoints.sh`
- **Purpose**: Provides monitoring endpoint information for external tools
- **Features**:
  - Endpoint testing
  - Configuration generation
  - Multiple output formats

**Usage Examples**:
```bash
# Test all endpoints
./docker/scripts/monitoring-endpoints.sh test

# Generate JSON config
./docker/scripts/monitoring-endpoints.sh config json

# Generate Prometheus config
./docker/scripts/monitoring-endpoints.sh config prometheus
```

### Available Monitoring Endpoints

#### Application Endpoints
- Health: `http://localhost:5000/health`
- Ready: `http://localhost:5000/health/ready`
- Live: `http://localhost:5000/health/live`
- Metrics: `http://localhost:5000/metrics`

#### Infrastructure Endpoints
- Prometheus: `http://localhost:9090/-/healthy`
- Grafana: `http://localhost:3000/api/health`
- Loki: `http://localhost:3100/ready`

#### Metrics Exporters
- MySQL: `http://localhost:9104/metrics`
- Redis: `http://localhost:9121/metrics`
- Nginx: `http://localhost:9113/metrics`
- Node: `http://localhost:9100/metrics`
- cAdvisor: `http://localhost:8080/metrics`

## Configuration

### Environment Variables

#### Health Check Configuration
```bash
# Health check timeouts
HEALTH_CHECK_TIMEOUT=15
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_VERBOSE=true

# Service startup configuration
SERVICE_STARTUP_TIMEOUT=600
SERVICE_CHECK_INTERVAL=5
SERVICE_STARTUP_VERBOSE=true

# Database initialization
DB_INIT_TIMEOUT=120
DB_MIGRATION_TIMEOUT=300
DB_BACKUP_DIR=/app/storage/backups/mysql

# Restart policies
SERVICE_RESTART_ATTEMPTS=3
SERVICE_RESTART_DELAY=10
SERVICE_HEALTH_TIMEOUT=30
```

#### Ollama Configuration
```bash
# External Ollama API
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_HEALTH_TIMEOUT=10
OLLAMA_HEALTH_VERBOSE=false
```

### Docker Compose Health Check Configuration

Each service in Docker Compose has optimized health check settings:

```yaml
healthcheck:
  test: ["CMD", "/scripts/service-health-check.sh"]
  interval: 30s      # Check every 30 seconds
  timeout: 15s       # 15 second timeout
  retries: 5         # 5 retries before unhealthy
  start_period: 60s  # Grace period for startup
```

## Troubleshooting

### Common Issues

#### Service Won't Start
1. Check dependencies are healthy
2. Review service logs: `docker-compose logs service_name`
3. Run health check manually: `./docker/scripts/service-health-check.sh`
4. Check resource usage: `docker stats`

#### Health Check Failures
1. Increase timeout values
2. Check network connectivity
3. Verify service configuration
4. Review application logs

#### Database Issues
1. Run database validation: `./docker/scripts/database-init-migration.sh validate`
2. Check MySQL logs: `docker-compose logs mysql`
3. Verify database connectivity from application

#### External Service Issues
1. Test Ollama connectivity: `./docker/scripts/docker_ollama_health.sh`
2. Verify host networking configuration
3. Check firewall settings

### Debugging Commands

```bash
# Check all service status
docker-compose ps

# View service logs
docker-compose logs -f service_name

# Run comprehensive health checks
./docker/scripts/service-restart-manager.sh monitor

# Test monitoring endpoints
./docker/scripts/monitoring-endpoints.sh test

# Generate service report
./docker/scripts/service-startup-coordinator.sh report
```

## Best Practices

### Health Check Design
1. Use appropriate timeouts for each service
2. Implement both shallow and deep health checks
3. Include dependency checks in health validation
4. Provide verbose output for debugging

### Service Dependencies
1. Start services in proper dependency order
2. Wait for health confirmation before starting dependents
3. Handle partial failures gracefully
4. Implement proper restart policies

### Monitoring Integration
1. Expose comprehensive metrics
2. Use standard monitoring endpoints
3. Implement proper alerting thresholds
4. Provide configuration for external tools

### Failure Handling
1. Implement exponential backoff for retries
2. Log all failure events with context
3. Provide manual recovery procedures
4. Alert on critical service failures

This comprehensive health check and service dependency system ensures reliable operation of the Vedfolnir Docker Compose deployment with proper monitoring, failure handling, and recovery capabilities.