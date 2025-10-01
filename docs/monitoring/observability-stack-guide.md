# Vedfolnir Observability Stack Guide

## Overview

The Vedfolnir observability stack provides comprehensive monitoring, logging, and alerting capabilities for the containerized deployment. It includes:

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboarding
- **Loki**: Centralized log aggregation
- **Exporters**: Custom metrics collection for MySQL, Redis, Nginx, and system resources
- **Alerting**: Proactive monitoring with configurable alert rules

## Components

### Prometheus (Metrics Collection)
- **Port**: 9090 (internal)
- **Configuration**: `config/prometheus/prometheus.yml`
- **Data Storage**: `data/prometheus/`
- **Retention**: 200 hours
- **Scrape Interval**: 15 seconds

### Grafana (Visualization)
- **Port**: 3000 (exposed)
- **Default Login**: admin / [generated password]
- **Configuration**: `config/grafana/grafana.ini`
- **Dashboards**: `config/grafana/dashboards/`
- **Data Storage**: `data/grafana/`

### Loki (Log Aggregation)
- **Port**: 3100 (internal)
- **Configuration**: `config/loki/loki.yml`
- **Data Storage**: `data/loki/`
- **Retention**: 168 hours (7 days)

### Metrics Exporters

#### MySQL Exporter
- **Port**: 9104 (internal)
- **Metrics**: Database performance, connections, queries
- **User**: `exporter` (created automatically)

#### Redis Exporter
- **Port**: 9121 (internal)
- **Metrics**: Memory usage, connections, commands
- **Keys Monitored**: `vedfolnir:*`

#### Nginx Exporter
- **Port**: 9113 (internal)
- **Metrics**: Request rates, response codes, connections
- **Status Endpoint**: `/nginx_status`

#### Node Exporter
- **Port**: 9100 (internal)
- **Metrics**: System resources (CPU, memory, disk, network)

#### cAdvisor
- **Port**: 8080 (internal)
- **Metrics**: Container resource usage and performance

## Setup Instructions

### 1. Initial Setup
```bash
# Run the setup script
./scripts/monitoring/setup_observability.sh

# Copy and configure environment file
cp .env.observability.example .env.observability
# Edit .env.observability with your passwords
```

### 2. Start Observability Stack
```bash
# Start all monitoring services
docker-compose up -d prometheus grafana loki mysql-exporter redis-exporter nginx-exporter node-exporter cadvisor

# Validate deployment
./scripts/monitoring/validate_observability.sh
```

### 3. Access Dashboards
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090 (if exposed)

## Pre-configured Dashboards

### Vedfolnir Overview
- Application request rate and status
- System CPU and memory usage
- Database connections and Redis memory
- **UID**: `vedfolnir-overview`

### System Metrics
- Detailed CPU, memory, disk, and network metrics
- **UID**: `system-metrics`

### Database Metrics
- MySQL connection pools and query performance
- Redis memory usage and activity
- **UID**: `database-metrics`

## Alert Rules

### Critical Alerts
- Application down (1 minute)
- Database down (1 minute)
- Redis down (1 minute)
- High error rate (>5% for 2 minutes)
- Low disk space (>90% for 5 minutes)

### Warning Alerts
- High CPU usage (>80% for 5 minutes)
- High memory usage (>85% for 5 minutes)
- High database connections (>80% for 5 minutes)
- High Redis memory usage (>90% for 5 minutes)
- Slow MySQL queries (>0.1/sec for 5 minutes)

## Configuration Files

### Prometheus Configuration
- **Main Config**: `config/prometheus/prometheus.yml`
- **Alert Rules**: `config/prometheus/rules/alert_rules.yml`

### Grafana Configuration
- **Main Config**: `config/grafana/grafana.ini`
- **Datasources**: `config/grafana/provisioning/datasources/`
- **Dashboards**: `config/grafana/provisioning/dashboards/`

### Loki Configuration
- **Main Config**: `config/loki/loki.yml`

## Troubleshooting

### Common Issues

#### Grafana Permission Errors
```bash
sudo chown -R 472:472 data/grafana
```

#### Prometheus Permission Errors
```bash
sudo chown -R 65534:65534 data/prometheus
```

#### MySQL Exporter Connection Issues
1. Verify MySQL exporter user exists
2. Check password in secrets file
3. Ensure MySQL is accessible from exporter container

#### Missing Metrics
1. Check exporter health endpoints
2. Verify Prometheus scrape configuration
3. Check container networking

### Validation Commands
```bash
# Check all containers
docker-compose ps

# Check specific service logs
docker-compose logs prometheus
docker-compose logs grafana
docker-compose logs loki

# Test metrics endpoints
curl http://localhost:9104/metrics  # MySQL
curl http://localhost:9121/metrics  # Redis
curl http://localhost:9113/metrics  # Nginx
curl http://localhost:9100/metrics  # Node
curl http://localhost:8080/metrics  # cAdvisor

# Validate Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana health
curl http://localhost:3000/api/health
```

## Security Considerations

### Network Isolation
- Monitoring services use dedicated `vedfolnir_monitoring` network
- Only Grafana is exposed to external network
- All other services communicate internally

### Authentication
- Grafana requires authentication (admin user)
- Prometheus and other services are internal-only
- MySQL exporter uses dedicated database user with minimal privileges

### Data Protection
- Secrets stored in Docker secrets
- Configuration files mounted read-only
- Data volumes use proper ownership and permissions

## Performance Tuning

### Resource Limits
- Prometheus: 2GB memory, 2 CPU cores
- Grafana: 1GB memory, 1 CPU core
- Loki: 1GB memory, 1 CPU core
- Exporters: 256MB memory, 0.5 CPU cores each

### Storage Optimization
- Prometheus retention: 200 hours
- Loki retention: 168 hours
- Regular cleanup of old data
- Compressed storage for logs

### Query Optimization
- Use appropriate time ranges in dashboards
- Limit concurrent queries
- Use recording rules for complex metrics

## Maintenance

### Regular Tasks
1. Monitor disk usage for data volumes
2. Review and update alert thresholds
3. Update dashboard configurations
4. Rotate secrets periodically
5. Update container images

### Backup Procedures
```bash
# Backup Grafana dashboards and configuration
docker-compose exec grafana grafana-cli admin export-dashboard

# Backup Prometheus data
docker-compose stop prometheus
tar -czf prometheus-backup-$(date +%Y%m%d).tar.gz data/prometheus/
docker-compose start prometheus
```

## Integration with CI/CD

### Automated Monitoring
- Health checks in deployment pipelines
- Performance regression detection
- Automated alert testing
- Dashboard validation

### Metrics in Development
- Local development monitoring
- Performance profiling
- Resource usage tracking
- Integration test metrics