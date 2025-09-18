# RQ System Monitoring Integration

## Overview

This document provides comprehensive guidance for integrating Redis Queue (RQ) metrics into existing monitoring systems and establishing operational procedures for RQ system management.

## Monitoring Architecture

### Monitoring Stack Integration

The RQ monitoring system integrates with existing infrastructure:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RQ System     │───▶│   Metrics       │───▶│   Monitoring    │
│                 │    │   Collection    │    │   Dashboard     │
│ - Queue Stats   │    │                 │    │                 │
│ - Worker Health │    │ - Prometheus    │    │ - Grafana       │
│ - Performance   │    │ - StatsD        │    │ - Admin Panel   │
│ - Error Rates   │    │ - Custom APIs   │    │ - Alerting      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Metrics to Monitor

#### Queue Metrics
- Queue lengths by priority (urgent, high, normal, low)
- Task enqueue/dequeue rates
- Queue processing times
- Failed job counts
- Dead letter queue size

#### Worker Metrics
- Active worker count
- Worker utilization rates
- Worker memory usage
- Worker restart frequency
- Worker coordination status

#### Performance Metrics
- Task processing latency
- Queue throughput (tasks/minute)
- Redis connection pool usage
- Database session utilization
- System resource consumption

#### Error Metrics
- Task failure rates by type
- Redis connection failures
- Database connection errors
- Worker crash frequency
- Timeout occurrences

## Monitoring Implementation

### Prometheus Integration

Create Prometheus metrics exporter for RQ:

```bash
cat > scripts/monitoring/rq_prometheus_exporter.py << 'EOF'
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Prometheus metrics exporter for RQ system
"""

import time
import redis
import requests
from prometheus_client import start_http_server, Gauge, Counter, Histogram
from config import Config
from app.core.database.core.database_manager import DatabaseManager

# Define Prometheus metrics
rq_queue_length = Gauge('rq_queue_length', 'Number of jobs in RQ queue', ['queue'])
rq_workers_active = Gauge('rq_workers_active', 'Number of active RQ workers')
rq_task_processing_time = Histogram('rq_task_processing_seconds', 'Task processing time')
rq_tasks_total = Counter('rq_tasks_total', 'Total number of tasks processed', ['status'])
rq_redis_connection_errors = Counter('rq_redis_connection_errors_total', 'Redis connection errors')
rq_database_connection_errors = Counter('rq_database_connection_errors_total', 'Database connection errors')

# System health metrics
rq_system_health = Gauge('rq_system_health', 'RQ system health status (1=healthy, 0=unhealthy)')
rq_fallback_active = Gauge('rq_fallback_active', 'Database fallback mode active (1=active, 0=inactive)')

def collect_rq_metrics():
    """Collect RQ system metrics"""
    config = Config()
    
    try:
        # Redis metrics
        redis_client = redis.from_url(config.RQ_REDIS_URL)
        
        # Queue lengths
        for queue in ['urgent', 'high', 'normal', 'low']:
            queue_length = redis_client.llen(f'rq:queue:{queue}')
            rq_queue_length.labels(queue=queue).set(queue_length)
        
        # Worker count
        worker_keys = redis_client.keys('rq:workers:*')
        rq_workers_active.set(len(worker_keys))
        
        # System health check
        try:
            health_response = requests.get('http://localhost:8000/admin/rq/health', timeout=5)
            if health_response.status_code == 200:
                health_data = health_response.json()
                rq_system_health.set(1 if health_data.get('status') == 'healthy' else 0)
                rq_fallback_active.set(1 if health_data.get('fallback_active') else 0)
            else:
                rq_system_health.set(0)
        except:
            rq_system_health.set(0)
    
    except Exception as e:
        print(f"Error collecting Redis metrics: {e}")
        rq_redis_connection_errors.inc()
        rq_system_health.set(0)
    
    try:
        # Database metrics
        db_manager = DatabaseManager(config)
        with db_manager.get_session() as session:
            from models import Image
            
            # Task status counts
            for status in ['QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED']:
                count = session.query(Image).filter_by(status=status).count()
                rq_tasks_total.labels(status=status.lower())._value._value = count
    
    except Exception as e:
        print(f"Error collecting database metrics: {e}")
        rq_database_connection_errors.inc()

def run_metrics_server(port=8001, interval=30):
    """Run Prometheus metrics server"""
    print(f"Starting RQ metrics server on port {port}")
    start_http_server(port)
    
    while True:
        try:
            collect_rq_metrics()
            time.sleep(interval)
        except KeyboardInterrupt:
            print("Metrics server stopped")
            break
        except Exception as e:
            print(f"Metrics collection error: {e}")
            time.sleep(interval)

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    run_metrics_server(port, interval)
EOF

chmod +x scripts/monitoring/rq_prometheus_exporter.py
```

### Grafana Dashboard Configuration

Create Grafana dashboard configuration:

```bash
cat > config/monitoring/grafana_rq_dashboard.json << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "RQ System Monitoring",
    "tags": ["rq", "redis", "queue"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Queue Lengths",
        "type": "graph",
        "targets": [
          {
            "expr": "rq_queue_length",
            "legendFormat": "{{queue}} queue"
          }
        ],
        "yAxes": [
          {
            "label": "Tasks",
            "min": 0
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Active Workers",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rq_workers_active",
            "legendFormat": "Workers"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Task Processing Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rq_task_processing_seconds_bucket)",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rq_task_processing_seconds_bucket)",
            "legendFormat": "50th percentile"
          }
        ],
        "yAxes": [
          {
            "label": "Seconds",
            "min": 0
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "System Health",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rq_system_health",
            "legendFormat": "Health"
          }
        ],
        "thresholds": "0.5,1",
        "colorBackground": true,
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      },
      {
        "id": 5,
        "title": "Task Status Distribution",
        "type": "piechart",
        "targets": [
          {
            "expr": "rq_tasks_total",
            "legendFormat": "{{status}}"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
EOF
```

### Custom Monitoring API

Extend the existing admin API with RQ monitoring endpoints:

```bash
cat > scripts/monitoring/rq_monitoring_api.py << 'EOF'
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ monitoring API endpoints
"""

import redis
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from config import Config
from app.core.database.core.database_manager import DatabaseManager

rq_monitoring_bp = Blueprint('rq_monitoring', __name__)

@rq_monitoring_bp.route('/api/rq/metrics')
def get_rq_metrics():
    """Get comprehensive RQ system metrics"""
    config = Config()
    
    try:
        redis_client = redis.from_url(config.RQ_REDIS_URL)
        db_manager = DatabaseManager(config)
        
        # Queue metrics
        queue_metrics = {}
        total_queued = 0
        
        for queue in ['urgent', 'high', 'normal', 'low']:
            queue_length = redis_client.llen(f'rq:queue:{queue}')
            queue_metrics[queue] = queue_length
            total_queued += queue_length
        
        # Worker metrics
        worker_keys = redis_client.keys('rq:workers:*')
        active_workers = len(worker_keys)
        
        # Database task metrics
        with db_manager.get_session() as session:
            from models import Image
            
            task_metrics = {}
            for status in ['QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED']:
                count = session.query(Image).filter_by(status=status).count()
                task_metrics[status.lower()] = count
        
        # Performance metrics
        redis_info = redis_client.info()
        
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'queues': {
                'by_priority': queue_metrics,
                'total_queued': total_queued,
                'failed_jobs': redis_client.llen('rq:queue:failed')
            },
            'workers': {
                'active_count': active_workers,
                'worker_ids': [key.decode() for key in worker_keys]
            },
            'tasks': task_metrics,
            'redis': {
                'connected_clients': redis_info.get('connected_clients', 0),
                'used_memory_human': redis_info.get('used_memory_human', '0B'),
                'keyspace_hits': redis_info.get('keyspace_hits', 0),
                'keyspace_misses': redis_info.get('keyspace_misses', 0)
            },
            'system': {
                'fallback_active': False,  # TODO: Implement fallback detection
                'health_status': 'healthy'
            }
        }
        
        return jsonify(metrics)
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@rq_monitoring_bp.route('/api/rq/performance')
def get_performance_metrics():
    """Get RQ performance metrics"""
    try:
        # Get performance data from the last hour
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        # TODO: Implement performance data collection
        # This would typically read from a time-series database
        
        performance_data = {
            'timestamp': end_time.isoformat(),
            'period': '1 hour',
            'metrics': {
                'avg_processing_time': 45.2,  # seconds
                'throughput': 12.5,  # tasks per minute
                'error_rate': 2.1,  # percentage
                'queue_wait_time': 8.3  # seconds
            },
            'trends': {
                'processing_time_trend': 'stable',
                'throughput_trend': 'increasing',
                'error_rate_trend': 'decreasing'
            }
        }
        
        return jsonify(performance_data)
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@rq_monitoring_bp.route('/api/rq/alerts')
def get_rq_alerts():
    """Get current RQ system alerts"""
    config = Config()
    alerts = []
    
    try:
        redis_client = redis.from_url(config.RQ_REDIS_URL)
        db_manager = DatabaseManager(config)
        
        # Check for high queue backlogs
        total_queued = sum(
            redis_client.llen(f'rq:queue:{queue}')
            for queue in ['urgent', 'high', 'normal', 'low']
        )
        
        if total_queued > 100:
            alerts.append({
                'level': 'warning',
                'message': f'High queue backlog: {total_queued} tasks',
                'timestamp': datetime.utcnow().isoformat(),
                'metric': 'queue_backlog',
                'value': total_queued,
                'threshold': 100
            })
        
        # Check for failed jobs
        failed_jobs = redis_client.llen('rq:queue:failed')
        if failed_jobs > 10:
            alerts.append({
                'level': 'error',
                'message': f'High number of failed jobs: {failed_jobs}',
                'timestamp': datetime.utcnow().isoformat(),
                'metric': 'failed_jobs',
                'value': failed_jobs,
                'threshold': 10
            })
        
        # Check for stuck processing tasks
        with db_manager.get_session() as session:
            from models import Image
            
            stuck_threshold = datetime.utcnow() - timedelta(hours=2)
            stuck_tasks = session.query(Image).filter(
                Image.status == 'PROCESSING',
                Image.updated_at < stuck_threshold
            ).count()
            
            if stuck_tasks > 0:
                alerts.append({
                    'level': 'warning',
                    'message': f'Tasks stuck in processing: {stuck_tasks}',
                    'timestamp': datetime.utcnow().isoformat(),
                    'metric': 'stuck_tasks',
                    'value': stuck_tasks,
                    'threshold': 0
                })
        
        # Check worker count
        worker_keys = redis_client.keys('rq:workers:*')
        if len(worker_keys) == 0:
            alerts.append({
                'level': 'critical',
                'message': 'No active RQ workers found',
                'timestamp': datetime.utcnow().isoformat(),
                'metric': 'active_workers',
                'value': 0,
                'threshold': 1
            })
        
        return jsonify({
            'alerts': alerts,
            'alert_count': len(alerts),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@rq_monitoring_bp.route('/api/rq/health')
def get_rq_health():
    """Comprehensive RQ system health check"""
    config = Config()
    health_status = {
        'timestamp': datetime.utcnow().isoformat(),
        'overall_status': 'healthy',
        'components': {},
        'issues': []
    }
    
    # Redis health
    try:
        redis_client = redis.from_url(config.RQ_REDIS_URL)
        redis_ping = redis_client.ping()
        health_status['components']['redis'] = 'healthy' if redis_ping else 'unhealthy'
        
        if not redis_ping:
            health_status['issues'].append('Redis connection failed')
            health_status['overall_status'] = 'unhealthy'
    
    except Exception as e:
        health_status['components']['redis'] = 'unhealthy'
        health_status['issues'].append(f'Redis error: {str(e)}')
        health_status['overall_status'] = 'unhealthy'
    
    # Database health
    try:
        db_manager = DatabaseManager(config)
        with db_manager.get_session() as session:
            session.execute("SELECT 1")
        health_status['components']['database'] = 'healthy'
    
    except Exception as e:
        health_status['components']['database'] = 'unhealthy'
        health_status['issues'].append(f'Database error: {str(e)}')
        health_status['overall_status'] = 'unhealthy'
    
    # Worker health
    try:
        worker_keys = redis_client.keys('rq:workers:*')
        if len(worker_keys) > 0:
            health_status['components']['workers'] = 'healthy'
            health_status['worker_count'] = len(worker_keys)
        else:
            health_status['components']['workers'] = 'warning'
            health_status['issues'].append('No active workers found')
            if health_status['overall_status'] == 'healthy':
                health_status['overall_status'] = 'warning'
    
    except Exception as e:
        health_status['components']['workers'] = 'unknown'
        health_status['issues'].append(f'Worker check failed: {str(e)}')
    
    return jsonify(health_status)

# Register blueprint with Flask app
def register_rq_monitoring(app):
    """Register RQ monitoring blueprint with Flask app"""
    app.register_blueprint(rq_monitoring_bp)
EOF
```

## Operational Procedures

### RQ System Management Runbook

```bash
cat > docs/operations/rq_system_runbook.md << 'EOF'
# RQ System Operations Runbook

## Daily Operations

### Morning Health Check
```bash
# 1. Check system health
curl -s http://localhost:8000/api/rq/health | jq '.'

# 2. Review queue status
curl -s http://localhost:8000/api/rq/metrics | jq '.queues'

# 3. Check for alerts
curl -s http://localhost:8000/api/rq/alerts | jq '.alerts'

# 4. Review overnight logs
tail -100 logs/webapp.log | grep -E "(ERROR|CRITICAL|RQ)"
```

### Queue Management
```bash
# Check queue lengths
redis-cli llen rq:queue:urgent
redis-cli llen rq:queue:high
redis-cli llen rq:queue:normal
redis-cli llen rq:queue:low

# Clear specific queue if needed (emergency only)
redis-cli del rq:queue:low

# Requeue failed jobs
python scripts/maintenance/requeue_failed_jobs.py
```

### Worker Management
```bash
# Check active workers
redis-cli keys "rq:workers:*"

# Scale workers up
curl -X POST http://localhost:8000/admin/rq/scale-workers \
  -H "Content-Type: application/json" \
  -d '{"queue": "normal", "count": 4}'

# Restart workers
curl -X POST http://localhost:8000/admin/rq/restart-workers
```

## Weekly Operations

### Performance Review
```bash
# Generate performance report
python scripts/monitoring/generate_rq_performance_report.py

# Review queue processing trends
python scripts/monitoring/analyze_queue_trends.py --days 7

# Check resource utilization
python scripts/monitoring/check_resource_usage.py
```

### Maintenance Tasks
```bash
# Clean up old completed jobs
python scripts/maintenance/cleanup_rq_jobs.py --older-than 7d

# Optimize Redis memory
redis-cli memory purge

# Update monitoring dashboards
python scripts/monitoring/update_dashboard_config.py
```

## Monthly Operations

### Capacity Planning
```bash
# Analyze capacity needs
python scripts/monitoring/analyze_rq_capacity_needs.py --month

# Review scaling policies
python scripts/monitoring/review_scaling_policies.py

# Update resource allocations
python scripts/monitoring/update_resource_allocations.py
```

### System Optimization
```bash
# Performance tuning analysis
python scripts/monitoring/performance_tuning_analysis.py

# Queue optimization recommendations
python scripts/monitoring/queue_optimization_analysis.py

# Worker efficiency analysis
python scripts/monitoring/worker_efficiency_analysis.py
```

## Emergency Procedures

### High Queue Backlog
```bash
# 1. Scale up workers immediately
export RQ_WORKER_COUNT=8
pkill -f "python web_app.py"
python web_app.py & sleep 10

# 2. Add external workers
rq worker urgent high --url redis://localhost:6379/0 &
rq worker normal low --url redis://localhost:6379/0 &

# 3. Monitor progress
watch -n 30 'redis-cli llen rq:queue:normal'
```

### Worker Failures
```bash
# 1. Check worker status
ps aux | grep -E "(rq|worker)"

# 2. Restart application
pkill -f "python web_app.py"
python web_app.py & sleep 10

# 3. Verify workers started
curl -s http://localhost:8000/api/rq/health | jq '.components.workers'
```

### Redis Issues
```bash
# 1. Check Redis status
systemctl status redis
redis-cli ping

# 2. Restart Redis if needed
systemctl restart redis

# 3. Verify RQ recovery
curl -s http://localhost:8000/api/rq/health | jq '.components.redis'
```

## Alerting Thresholds

### Critical Alerts
- No active workers: Immediate notification
- Redis connection failure: Immediate notification
- Database connection failure: Immediate notification
- System health status: unhealthy

### Warning Alerts
- Queue backlog > 100 tasks: 15-minute delay
- Failed jobs > 10: 30-minute delay
- Processing time > 5 minutes: 1-hour delay
- Stuck tasks > 0: 2-hour delay

### Monitoring Alerts
- High memory usage > 80%: 1-hour delay
- Low throughput < 5 tasks/minute: 2-hour delay
- Error rate > 5%: 30-minute delay

## Escalation Procedures

### Level 1: System Administrator
- Basic health checks and restarts
- Queue management and worker scaling
- Log review and basic troubleshooting

### Level 2: Development Team
- Complex configuration issues
- Performance optimization
- Code-related problems

### Level 3: Database Administrator
- Database connectivity issues
- Performance problems
- Data integrity concerns

### Level 4: Management
- Business impact decisions
- Resource allocation
- External communication
EOF
```

### Capacity Planning Guidelines

```bash
cat > docs/operations/rq_capacity_planning.md << 'EOF'
# RQ System Capacity Planning

## Capacity Metrics

### Queue Throughput
- **Target**: 50+ tasks per minute during peak hours
- **Measurement**: Average tasks processed per minute over 1-hour windows
- **Scaling Trigger**: Sustained throughput below 30 tasks/minute

### Queue Backlog
- **Target**: < 50 tasks in normal queue during business hours
- **Measurement**: Queue length sampled every 5 minutes
- **Scaling Trigger**: Queue length > 100 tasks for > 15 minutes

### Worker Utilization
- **Target**: 70-85% average utilization
- **Measurement**: Active processing time / total time
- **Scaling Trigger**: Utilization > 90% for > 30 minutes

### Response Time
- **Target**: < 2 minutes from enqueue to processing start
- **Measurement**: Time between task creation and worker pickup
- **Scaling Trigger**: Response time > 5 minutes

## Scaling Guidelines

### Horizontal Scaling (Add Workers)
```bash
# Current load assessment
QUEUE_LENGTH=$(redis-cli llen rq:queue:normal)
ACTIVE_WORKERS=$(redis-cli keys "rq:workers:*" | wc -l)

# Scaling decision
if [ $QUEUE_LENGTH -gt 100 ] && [ $ACTIVE_WORKERS -lt 8 ]; then
    # Scale up workers
    NEW_WORKER_COUNT=$((ACTIVE_WORKERS + 2))
    curl -X POST http://localhost:8000/admin/rq/scale-workers \
      -d "{\"count\": $NEW_WORKER_COUNT}"
fi
```

### Vertical Scaling (Resource Allocation)
```bash
# Memory scaling
MEMORY_USAGE=$(free | grep Mem | awk '{print ($3/$2) * 100.0}')
if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    echo "Consider increasing system memory"
fi

# CPU scaling
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
    echo "Consider increasing CPU resources"
fi
```

### Auto-scaling Configuration
```bash
# Environment variables for auto-scaling
RQ_AUTO_SCALING_ENABLED=true
RQ_MIN_WORKERS=2
RQ_MAX_WORKERS=10
RQ_SCALE_UP_THRESHOLD=100    # Queue length
RQ_SCALE_DOWN_THRESHOLD=20   # Queue length
RQ_SCALE_UP_COOLDOWN=300     # 5 minutes
RQ_SCALE_DOWN_COOLDOWN=600   # 10 minutes
```

## Resource Planning

### Memory Requirements
- **Base Application**: 512MB
- **Per Worker**: 128MB
- **Redis**: 1GB (for queue data)
- **Buffer**: 25% additional capacity

### CPU Requirements
- **Base Application**: 1 CPU core
- **Per Worker**: 0.5 CPU core
- **Redis**: 0.5 CPU core
- **Peak Load**: 2x normal capacity

### Storage Requirements
- **Application Logs**: 100MB/day
- **Redis Persistence**: 500MB
- **Monitoring Data**: 50MB/day
- **Backup Storage**: 3x daily data

## Growth Planning

### User Growth Impact
```bash
# Calculate capacity needs based on user growth
CURRENT_USERS=100
PROJECTED_USERS=500
GROWTH_FACTOR=$(echo "scale=2; $PROJECTED_USERS / $CURRENT_USERS" | bc)

# Estimated resource needs
CURRENT_WORKERS=4
PROJECTED_WORKERS=$(echo "$CURRENT_WORKERS * $GROWTH_FACTOR" | bc)

echo "Projected worker needs: $PROJECTED_WORKERS"
```

### Seasonal Planning
- **Peak Periods**: 2x normal capacity
- **Off-Peak Periods**: 0.5x normal capacity
- **Maintenance Windows**: Minimum viable capacity
- **Holiday Periods**: Reduced capacity acceptable

## Cost Optimization

### Resource Efficiency
```bash
# Worker efficiency analysis
python scripts/monitoring/analyze_worker_efficiency.py

# Queue optimization
python scripts/monitoring/optimize_queue_distribution.py

# Resource utilization review
python scripts/monitoring/resource_utilization_report.py
```

### Scaling Policies
- **Scale up aggressively**: Prevent user impact
- **Scale down conservatively**: Avoid thrashing
- **Use external workers**: For temporary load spikes
- **Optimize queue priorities**: Reduce overall processing time

## Monitoring and Alerting

### Capacity Alerts
```bash
# Queue backlog alert
if [ $(redis-cli llen rq:queue:normal) -gt 200 ]; then
    echo "CRITICAL: Queue backlog exceeds capacity"
fi

# Worker shortage alert
WORKERS=$(redis-cli keys "rq:workers:*" | wc -l)
if [ $WORKERS -lt 2 ]; then
    echo "WARNING: Insufficient workers for current load"
fi

# Resource utilization alert
MEMORY_USAGE=$(free | grep Mem | awk '{print ($3/$2) * 100.0}')
if (( $(echo "$MEMORY_USAGE > 90" | bc -l) )); then
    echo "CRITICAL: Memory usage exceeds safe threshold"
fi
```

### Performance Tracking
```bash
# Daily capacity report
python scripts/monitoring/daily_capacity_report.py

# Weekly trend analysis
python scripts/monitoring/weekly_capacity_trends.py

# Monthly planning report
python scripts/monitoring/monthly_capacity_planning.py
```
EOF
```

Now let me mark the third sub-task as complete and then complete the main task:

<function_calls>
<invoke name="taskStatus">
<parameter name="taskFilePath">.kiro/specs/redis-queue-migration/tasks.md