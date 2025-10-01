# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Vedfolnir Resource Management and Scaling

This document describes the resource management and auto-scaling capabilities of the Vedfolnir Docker Compose deployment.

## Overview

The Vedfolnir Docker deployment includes comprehensive resource management and horizontal scaling capabilities:

- **Resource Limits**: CPU and memory limits for all containers
- **Resource Reservations**: Guaranteed resource allocation to prevent starvation
- **Horizontal Scaling**: Automatic scaling of application containers based on metrics
- **Monitoring**: Real-time resource usage monitoring and alerting
- **Auto-Scaling**: Automated scaling decisions based on performance metrics

## Resource Configuration

### Container Resource Limits

All containers have configured resource limits and reservations:

```yaml
# Application containers
vedfolnir:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
        pids: 1000
      reservations:
        cpus: '1.0'
        memory: 1G

# Database containers
mysql:
  deploy:
    resources:
      limits:
        cpus: '4.0'
        memory: 8G
        pids: 2000
      reservations:
        cpus: '2.0'
        memory: 4G
```

### Resource Allocation Strategy

| Service | CPU Limit | Memory Limit | CPU Reservation | Memory Reservation |
|---------|-----------|--------------|-----------------|-------------------|
| Vedfolnir | 2.0 cores | 2GB | 1.0 core | 1GB |
| MySQL | 4.0 cores | 8GB | 2.0 cores | 4GB |
| Redis | 2.0 cores | 2GB | 1.0 core | 1GB |
| Nginx | 1.0 core | 1GB | 0.5 cores | 512MB |
| Prometheus | 2.0 cores | 4GB | 1.0 core | 2GB |
| Grafana | 1.0 core | 2GB | 0.5 cores | 1GB |
| Loki | 2.0 cores | 2GB | 1.0 core | 1GB |

## Horizontal Scaling

### Scaling Configuration

The Vedfolnir application supports horizontal scaling with the following configuration:

```yaml
vedfolnir:
  deploy:
    replicas: 3
    update_config:
      parallelism: 1
      delay: 30s
      failure_action: rollback
      monitor: 60s
      max_failure_ratio: 0.3
      order: start-first
    placement:
      max_replicas_per_node: 2
```

### Scaling Parameters

- **Minimum Replicas**: 2
- **Maximum Replicas**: 5
- **Default Replicas**: 3
- **Scale Up Threshold**: 70% CPU or 80% memory usage
- **Scale Down Threshold**: 20% CPU and 40% memory usage
- **Scale Up Cooldown**: 5 minutes
- **Scale Down Cooldown**: 10 minutes

### Manual Scaling

Scale the application manually:

```bash
# Scale up to 4 replicas
docker-compose -f docker-compose.yml -f docker-compose.scaling.yml up -d --scale vedfolnir=4

# Scale down to 2 replicas
docker-compose -f docker-compose.yml -f docker-compose.scaling.yml up -d --scale vedfolnir=2

# Using the auto-scaling script
./scripts/docker/auto-scaling.sh scale-up 4
./scripts/docker/auto-scaling.sh scale-down 2
```

## Auto-Scaling

### Auto-Scaling Triggers

The auto-scaling system monitors multiple metrics and triggers scaling actions:

#### Scale Up Triggers
- CPU usage > 70% for 5 minutes
- Memory usage > 80% for 5 minutes
- Queue depth > 50 jobs for 5 minutes
- Response time P95 > 3 seconds for 5 minutes
- Error rate > 5% for 2 minutes

#### Scale Down Triggers
- CPU usage < 20% for 15 minutes
- Memory usage < 40% for 15 minutes
- Queue depth < 10 jobs for 15 minutes
- Response time P95 < 1 second for 15 minutes
- More than minimum replicas running

### Scaling Scores

The auto-scaling system calculates scaling scores based on multiple factors:

```prometheus
# Scale up score (0-15 points)
vedfolnir:scale_up_score = 
  (cpu_usage > 0.7) * 3 +
  (memory_usage > 0.8) * 3 +
  (queue_depth > 50) * 2 +
  (response_time_p95 > 3) * 2 +
  (error_rate > 0.05) * 4

# Scale down score (0-7 points)
vedfolnir:scale_down_score = 
  (cpu_usage < 0.2) * 2 +
  (memory_usage < 0.4) * 2 +
  (queue_depth < 10) * 1 +
  (response_time_p95 < 1) * 1 +
  (instance_count > 2) * 1
```

### Auto-Scaling Script

The auto-scaling script provides comprehensive scaling management:

```bash
# Check metrics and scale if needed
./scripts/docker/auto-scaling.sh check

# Generate scaling report
./scripts/docker/auto-scaling.sh report

# Manual scaling
./scripts/docker/auto-scaling.sh scale-up [replicas]
./scripts/docker/auto-scaling.sh scale-down [replicas]

# Health check
./scripts/docker/auto-scaling.sh health

# Reset scaling state
./scripts/docker/auto-scaling.sh reset
```

### Automated Scaling

Set up automated scaling using cron jobs:

```bash
# Install cron jobs
crontab -l > current_cron
cat config/cron/auto-scaling.cron >> current_cron
crontab current_cron

# Or use systemd service
sudo cp config/systemd/vedfolnir-autoscaler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vedfolnir-autoscaler
sudo systemctl start vedfolnir-autoscaler
```

## Monitoring and Alerting

### Resource Metrics

Key metrics monitored for scaling decisions:

- `vedfolnir:cpu_usage_avg` - Average CPU usage across replicas
- `vedfolnir:memory_usage_avg` - Average memory usage across replicas
- `vedfolnir:instance_count` - Current number of replicas
- `vedfolnir:queue_depth` - Number of jobs in queue
- `vedfolnir:response_time_p95` - 95th percentile response time
- `vedfolnir:error_rate` - Application error rate

### Alert Rules

Resource management alerts are configured in Prometheus:

```yaml
# High resource usage alerts
- alert: VedfolnirHighCPUUsage
  expr: vedfolnir:cpu_usage_avg > 0.7
  for: 5m
  labels:
    severity: warning
    scaling_action: scale_up

- alert: ContainerMemoryPressure
  expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.85
  for: 3m
  labels:
    severity: warning

# Container resource limit alerts
- alert: ContainerOOMKilled
  expr: increase(container_oom_kills_total[5m]) > 0
  for: 0m
  labels:
    severity: critical
```

### Grafana Dashboard

A comprehensive resource management dashboard is available at:
- **URL**: http://localhost:3000/d/vedfolnir-scaling
- **Panels**: Resource usage, scaling scores, replica count, performance metrics

## Testing

### Resource Management Tests

Run comprehensive resource management tests:

```bash
# Run all tests
./scripts/docker/test-resource-management.sh all

# Test specific components
./scripts/docker/test-resource-management.sh limits
./scripts/docker/test-resource-management.sh scaling
./scripts/docker/test-resource-management.sh metrics
./scripts/docker/test-resource-management.sh alerting
./scripts/docker/test-resource-management.sh auto-scaling
./scripts/docker/test-resource-management.sh performance

# Generate load for testing
./scripts/docker/test-resource-management.sh load
```

### Load Testing

Generate load to test scaling behavior:

```bash
# Medium load for 5 minutes
TEST_DURATION=300 LOAD_INTENSITY=medium ./scripts/docker/test-resource-management.sh load

# High load for 2 minutes
TEST_DURATION=120 LOAD_INTENSITY=high ./scripts/docker/test-resource-management.sh load
```

## Troubleshooting

### Common Issues

#### Scaling Not Working
1. Check if scaling configuration is loaded:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.scaling.yml config
   ```

2. Verify Prometheus metrics:
   ```bash
   curl -s "http://localhost:9090/api/v1/query?query=vedfolnir:cpu_usage_avg"
   ```

3. Check auto-scaling logs:
   ```bash
   tail -f logs/auto-scaling.log
   ```

#### High Resource Usage
1. Check container resource usage:
   ```bash
   docker stats
   ```

2. Review resource limits:
   ```bash
   docker inspect <container_name> | jq '.[0].HostConfig | {Memory, CpuQuota, CpuShares}'
   ```

3. Scale manually if needed:
   ```bash
   ./scripts/docker/auto-scaling.sh scale-up
   ```

#### Metrics Not Available
1. Check Prometheus targets:
   ```bash
   curl -s "http://localhost:9090/api/v1/targets"
   ```

2. Verify exporters are running:
   ```bash
   docker-compose ps | grep exporter
   ```

3. Check application metrics endpoint:
   ```bash
   curl -s "http://localhost:5000/metrics"
   ```

### Performance Tuning

#### CPU Optimization
- Adjust CPU limits based on actual usage patterns
- Use CPU reservations to guarantee minimum performance
- Monitor CPU throttling metrics

#### Memory Optimization
- Set appropriate memory limits to prevent OOM kills
- Use memory reservations for critical services
- Monitor memory fragmentation and swap usage

#### Scaling Optimization
- Tune scaling thresholds based on application behavior
- Adjust cooldown periods to prevent flapping
- Use queue-based scaling for batch workloads

## Best Practices

### Resource Allocation
1. **Set Conservative Limits**: Start with conservative resource limits and adjust based on monitoring
2. **Use Reservations**: Always set resource reservations for critical services
3. **Monitor Continuously**: Continuously monitor resource usage and adjust limits
4. **Plan for Peak Load**: Size resources for peak load scenarios

### Scaling Strategy
1. **Gradual Scaling**: Scale gradually (1-2 replicas at a time) to avoid resource spikes
2. **Health Checks**: Ensure proper health checks before scaling decisions
3. **Cooldown Periods**: Use appropriate cooldown periods to prevent scaling oscillation
4. **Load Testing**: Regularly test scaling behavior under load

### Monitoring
1. **Multiple Metrics**: Use multiple metrics for scaling decisions, not just CPU/memory
2. **Business Metrics**: Include business metrics (queue depth, response time) in scaling logic
3. **Alert Fatigue**: Tune alert thresholds to avoid alert fatigue
4. **Historical Analysis**: Analyze historical scaling patterns for optimization

## Configuration Files

### Key Files
- `docker-compose.scaling.yml` - Scaling configuration
- `config/prometheus/rules/resource-alerts.yml` - Resource alert rules
- `scripts/docker/auto-scaling.sh` - Auto-scaling script
- `scripts/docker/test-resource-management.sh` - Testing script
- `config/grafana/dashboards/resource-management.json` - Grafana dashboard

### Environment Variables
- `PROMETHEUS_URL` - Prometheus endpoint for metrics
- `DRY_RUN` - Set to 'true' for dry run mode
- `WEBHOOK_URL` - Webhook for scaling notifications
- `MIN_REPLICAS` - Minimum number of replicas
- `MAX_REPLICAS` - Maximum number of replicas

## Security Considerations

### Resource Limits
- Set resource limits to prevent resource exhaustion attacks
- Use PID limits to prevent fork bombs
- Monitor resource usage for anomalies

### Scaling Security
- Validate scaling requests and metrics
- Use secure communication for scaling decisions
- Log all scaling actions for audit purposes
- Implement rate limiting for scaling operations

## Future Enhancements

### Planned Features
1. **Predictive Scaling**: Machine learning-based scaling predictions
2. **Multi-Metric Scaling**: Advanced multi-metric scaling algorithms
3. **Cost Optimization**: Cost-aware scaling decisions
4. **Geographic Scaling**: Multi-region scaling support
5. **Custom Metrics**: Support for custom business metrics in scaling decisions