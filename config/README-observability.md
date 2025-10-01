# Vedfolnir Observability Stack Configuration

This directory contains configuration files for the comprehensive observability stack including Prometheus, Grafana, Loki, and various metrics exporters.

## Directory Structure

```
config/
├── prometheus/
│   ├── prometheus.yml          # Main Prometheus configuration
│   └── rules/
│       └── alert_rules.yml     # Alert rules for critical events
├── grafana/
│   ├── grafana.ini            # Grafana server configuration
│   ├── provisioning/
│   │   ├── datasources/       # Auto-provisioned datasources
│   │   └── dashboards/        # Dashboard provisioning config
│   └── dashboards/            # Pre-built monitoring dashboards
├── loki/
│   └── loki.yml              # Loki log aggregation configuration
└── exporters/
    ├── mysql-exporter.env    # MySQL metrics exporter config
    ├── redis-exporter.env    # Redis metrics exporter config
    └── nginx-exporter.conf   # Nginx metrics exporter config
```

## Quick Start

1. **Setup**: Run `./scripts/monitoring/setup_observability.sh`
2. **Configure**: Copy `.env.observability.example` to `.env.observability` and set passwords
3. **Deploy**: `docker-compose up -d prometheus grafana loki mysql-exporter redis-exporter nginx-exporter node-exporter cadvisor`
4. **Validate**: Run `./scripts/monitoring/validate_observability.sh`
5. **Access**: Open Grafana at http://localhost:3000

## Key Features

### Metrics Collection
- **Application Metrics**: Request rates, response times, error rates
- **System Metrics**: CPU, memory, disk, network usage
- **Database Metrics**: MySQL connections, query performance, slow queries
- **Cache Metrics**: Redis memory usage, connections, command rates
- **Container Metrics**: Resource usage per container

### Dashboards
- **Vedfolnir Overview**: High-level application and system status
- **System Metrics**: Detailed system resource monitoring
- **Database Metrics**: MySQL and Redis performance monitoring

### Alerting
- **Critical Alerts**: Service outages, high error rates, resource exhaustion
- **Warning Alerts**: Performance degradation, resource pressure
- **Configurable Thresholds**: Customizable alert conditions

### Log Aggregation
- **Centralized Logging**: All container logs in one place
- **Structured Logs**: JSON-formatted logs with metadata
- **Log Retention**: Configurable retention policies
- **Search and Filter**: Powerful log query capabilities

## Configuration Details

### Prometheus
- **Scrape Interval**: 15 seconds for most targets, 30 seconds for exporters
- **Retention**: 200 hours of metrics data
- **Storage**: Persistent volume with automatic cleanup
- **Targets**: Auto-discovery of all services and exporters

### Grafana
- **Authentication**: Admin user with generated password
- **Datasources**: Auto-provisioned Prometheus and Loki
- **Dashboards**: Pre-configured monitoring dashboards
- **Plugins**: Essential visualization plugins included

### Loki
- **Storage**: Local filesystem with configurable retention
- **Ingestion**: JSON log parsing with automatic labeling
- **Retention**: 168 hours (7 days) default
- **Compression**: Efficient log storage and retrieval

## Security

### Network Isolation
- Monitoring services use dedicated internal network
- Only Grafana exposed to external access
- Inter-service communication secured

### Authentication
- Grafana requires login (admin user)
- Internal services use network-level security
- Database exporters use dedicated users with minimal privileges

### Data Protection
- Secrets managed via Docker secrets
- Configuration files mounted read-only
- Proper file permissions and ownership

## Maintenance

### Regular Tasks
- Monitor disk usage for metrics and logs
- Update alert thresholds based on usage patterns
- Review and rotate access credentials
- Update container images for security patches

### Backup Procedures
- Export Grafana dashboards and configuration
- Backup Prometheus data for long-term retention
- Document custom alert rules and thresholds

### Performance Tuning
- Adjust scrape intervals based on requirements
- Configure retention periods for storage optimization
- Optimize query performance with recording rules
- Scale resources based on monitoring load

## Troubleshooting

### Common Issues
1. **Permission Errors**: Check data directory ownership
2. **Connection Failures**: Verify network configuration and service health
3. **Missing Metrics**: Check exporter configuration and Prometheus targets
4. **Dashboard Issues**: Verify datasource configuration and queries

### Diagnostic Commands
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs prometheus
docker-compose logs grafana
docker-compose logs loki

# Test metrics endpoints
curl http://localhost:9090/-/healthy    # Prometheus
curl http://localhost:3000/api/health   # Grafana
curl http://localhost:3100/ready        # Loki

# Validate configuration
./scripts/monitoring/validate_observability.sh
```

For detailed setup and usage instructions, see `docs/monitoring/observability-stack-guide.md`.