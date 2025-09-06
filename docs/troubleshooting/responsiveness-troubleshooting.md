# Responsiveness Monitoring Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting procedures for the Flask App Responsiveness Monitoring system. It covers common issues, diagnostic procedures, and resolution steps for maintaining optimal application performance.

## Quick Diagnostic Checklist

### Immediate Response (2 minutes)
1. **Check System Status** - Visit `/admin/health` for overall system health
2. **Review Active Alerts** - Check dashboard for critical alerts
3. **Verify Basic Connectivity** - Ensure database and Redis connections
4. **Check Resource Usage** - Review memory and CPU utilization

### Detailed Assessment (5 minutes)
1. **Analyze Performance Metrics** - Review response times and error rates
2. **Check Background Tasks** - Verify task coordination and completion
3. **Review Recent Logs** - Check for error patterns and warnings
4. **Validate Configuration** - Ensure monitoring settings are correct

## Common Issues and Solutions

### 1. High Memory Usage

#### Symptoms
- Memory usage consistently above 80%
- Gradual memory increase over time
- Out of memory errors in logs
- Application becoming unresponsive

#### Diagnostic Steps
```bash
# Check current memory usage
python -c "
import psutil
print(f'Memory usage: {psutil.virtual_memory().percent}%')
print(f'Available: {psutil.virtual_memory().available / (1024**3):.2f} GB')
"

# Check for memory leaks in sessions
python -c "
from session_middleware_v2 import RedisSessionManager
manager = RedisSessionManager()
stats = manager.get_session_stats()
print(f'Active sessions: {stats.get(\"active_sessions\", 0)}')
print(f'Memory usage: {stats.get(\"memory_usage_mb\", 0)} MB')
"

# Monitor memory usage over time
watch -n 5 'python -c "import psutil; print(f\"Memory: {psutil.virtual_memory().percent}%\")"'
```

#### Resolution Steps
1. **Immediate Actions**
   - Trigger manual cleanup via admin dashboard
   - Restart background cleanup processes
   - Clear expired sessions manually

2. **Configuration Adjustments**
   ```bash
   # Increase cleanup frequency
   RESPONSIVENESS_CLEANUP_INTERVAL=180  # Reduce from 300 to 180 seconds
   
   # Lower memory thresholds for earlier intervention
   RESPONSIVENESS_MEMORY_WARNING_THRESHOLD=0.7  # Reduce from 0.8
   RESPONSIVENESS_MEMORY_CRITICAL_THRESHOLD=0.8  # Reduce from 0.9
   ```

3. **Long-term Solutions**
   - Implement more aggressive session cleanup
   - Review code for memory leak patterns
   - Consider increasing system memory

#### Prevention
- Monitor memory trends daily
- Set up proactive alerts at 70% usage
- Implement automated cleanup triggers
- Regular memory usage pattern analysis

### 2. Database Connection Issues

#### Symptoms
- Connection pool exhaustion warnings
- Database query timeouts
- "Too many connections" errors
- Slow database response times

#### Diagnostic Steps
```bash
# Check database connection status
python -c "
from database import DatabaseManager
from config import Config
db = DatabaseManager(Config())
stats = db.get_mysql_performance_stats()
print(f'Active connections: {stats.get(\"active_connections\", 0)}')
print(f'Pool utilization: {stats.get(\"pool_utilization\", 0)}%')
"

# Monitor database connections
mysql -u root -p -e "SHOW PROCESSLIST;" | wc -l

# Check for connection leaks
python -c "
from database import DatabaseManager
from config import Config
db = DatabaseManager(Config())
leak_info = db.detect_connection_leaks()
if leak_info:
    print(f'Potential leaks detected: {len(leak_info)}')
    for leak in leak_info:
        print(f'  - {leak}')
else:
    print('No connection leaks detected')
"
```

#### Resolution Steps
1. **Immediate Actions**
   - Restart database connection pool
   - Kill long-running database queries
   - Clear connection pool and reconnect

2. **Configuration Adjustments**
   ```bash
   # Increase connection pool size
   DB_POOL_SIZE=30  # Increase from 20
   DB_MAX_OVERFLOW=50  # Increase from 30
   
   # Reduce connection timeout
   DB_POOL_TIMEOUT=10  # Reduce connection wait time
   DB_POOL_RECYCLE=1800  # Recycle connections every 30 minutes
   ```

3. **Code Review**
   - Audit database session usage patterns
   - Ensure proper session cleanup in all routes
   - Implement connection leak detection

#### Prevention
- Monitor connection pool utilization
- Implement connection lifecycle logging
- Regular database performance analysis
- Automated connection leak detection

### 3. Slow Request Performance

#### Symptoms
- Response times above 5 seconds
- Request timeout errors
- High request queue buildup
- User complaints about slow interface

#### Diagnostic Steps
```bash
# Check current response times
tail -f logs/webapp.log | grep "response_time" | tail -20

# Identify slow endpoints
python -c "
from utils.performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()
slow_requests = monitor.get_slow_requests(limit=10)
for request in slow_requests:
    print(f'{request[\"endpoint\"]}: {request[\"response_time\"]}s')
"

# Monitor request queue
python -c "
from web_app import app
with app.app_context():
    queue_size = app.config.get('REQUEST_QUEUE_SIZE', 0)
    print(f'Request queue size: {queue_size}')
"
```

#### Resolution Steps
1. **Immediate Actions**
   - Identify and optimize slowest endpoints
   - Implement request throttling if needed
   - Clear request queue if backed up

2. **Database Optimization**
   ```bash
   # Identify slow queries
   mysql -u root -p -e "
   SELECT query_time, lock_time, rows_sent, rows_examined, sql_text 
   FROM mysql.slow_log 
   ORDER BY query_time DESC 
   LIMIT 10;"
   
   # Check for missing indexes
   python scripts/database/analyze_query_performance.py
   ```

3. **Code Optimization**
   - Profile slow endpoints using performance monitoring
   - Implement caching for frequently accessed data
   - Optimize database queries and add indexes

#### Prevention
- Set up automated slow request alerts
- Regular performance profiling
- Implement request performance budgets
- Monitor and optimize database queries

### 4. Background Task Problems

#### Symptoms
- Background tasks not completing
- High task error rates
- Task coordination failures
- Resource contention issues

#### Diagnostic Steps
```bash
# Check background task status
python -c "
from background_cleanup_manager import BackgroundCleanupManager
manager = BackgroundCleanupManager()
stats = manager.get_cleanup_stats()
print(f'Active tasks: {stats.get(\"active_tasks\", 0)}')
print(f'Success rate: {stats.get(\"success_rate\", 0)}%')
print(f'Error count: {stats.get(\"error_count\", 0)}')
"

# Monitor task coordination
python -c "
from background_cleanup_manager import BackgroundCleanupManager
manager = BackgroundCleanupManager()
coordination_status = manager.get_coordination_status()
print(f'Coordination health: {coordination_status}')
"

# Check task resource usage
ps aux | grep python | grep -E "(cleanup|background)" | awk '{print $3, $4, $11}'
```

#### Resolution Steps
1. **Immediate Actions**
   - Restart failed background tasks
   - Clear task queue if backed up
   - Check for resource conflicts

2. **Configuration Adjustments**
   ```bash
   # Adjust task coordination settings
   RESPONSIVENESS_TASK_HEALTH_CHECK_INTERVAL=30  # Reduce from 60
   RESPONSIVENESS_TASK_MONITORING_ENABLED=true
   
   # Increase task timeout limits
   BACKGROUND_TASK_TIMEOUT=300  # 5 minutes
   TASK_RETRY_ATTEMPTS=3
   ```

3. **Task Optimization**
   - Review task resource requirements
   - Implement better error handling
   - Add task progress monitoring

#### Prevention
- Monitor task success rates
- Implement task health checks
- Regular task performance analysis
- Automated task recovery procedures

### 5. Session Management Issues

#### Symptoms
- Session data loss or corruption
- Authentication failures
- Cross-tab synchronization problems
- Session-related memory leaks

#### Diagnostic Steps
```bash
# Check Redis session health
python -c "
from session_middleware_v2 import RedisSessionManager
manager = RedisSessionManager()
health = manager.health_check()
print(f'Redis health: {health}')
"

# Monitor session statistics
python -c "
from session_middleware_v2 import RedisSessionManager
manager = RedisSessionManager()
stats = manager.get_session_stats()
for key, value in stats.items():
    print(f'{key}: {value}')
"

# Check for session leaks
redis-cli --scan --pattern "vedfolnir:session:*" | wc -l
```

#### Resolution Steps
1. **Immediate Actions**
   - Clear expired sessions manually
   - Restart Redis session service
   - Verify Redis connectivity

2. **Configuration Review**
   ```bash
   # Adjust session settings
   REDIS_SESSION_TIMEOUT=3600  # Reduce from 7200 if needed
   SESSION_CLEANUP_INTERVAL=300  # 5 minutes
   
   # Enable session debugging
   SESSION_DEBUG_ENABLED=true
   SESSION_AUDIT_ENABLED=true
   ```

3. **Session Cleanup**
   ```bash
   # Manual session cleanup
   python -c "
   from session_middleware_v2 import RedisSessionManager
   manager = RedisSessionManager()
   cleaned = manager.cleanup_expired_sessions()
   print(f'Cleaned {cleaned} expired sessions')
   "
   ```

#### Prevention
- Regular session cleanup monitoring
- Implement session lifecycle logging
- Monitor session memory usage
- Automated session health checks

## Advanced Troubleshooting

### Performance Profiling

#### CPU Profiling
```bash
# Profile application CPU usage
python -m cProfile -o profile_output.prof web_app.py &
sleep 60
kill %1

# Analyze profile results
python -c "
import pstats
stats = pstats.Stats('profile_output.prof')
stats.sort_stats('cumulative').print_stats(20)
"
```

#### Memory Profiling
```bash
# Install memory profiler if needed
pip install memory-profiler

# Profile memory usage
python -m memory_profiler web_app.py

# Monitor memory over time
mprof run python web_app.py &
sleep 300
mprof plot
```

#### Database Profiling
```bash
# Enable MySQL slow query log
mysql -u root -p -e "
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;
SET GLOBAL log_queries_not_using_indexes = 'ON';
"

# Analyze slow queries
mysqldumpslow /var/log/mysql/mysql-slow.log | head -20
```

### Log Analysis

#### Error Pattern Analysis
```bash
# Find common error patterns
grep -E "(ERROR|CRITICAL)" logs/webapp.log | \
awk '{print $4}' | sort | uniq -c | sort -nr | head -10

# Analyze response time patterns
grep "response_time" logs/webapp.log | \
awk '{print $NF}' | sort -n | tail -20

# Check for memory warnings
grep -i "memory" logs/webapp.log | tail -20
```

#### Performance Trend Analysis
```bash
# Analyze hourly performance trends
grep "$(date '+%Y-%m-%d')" logs/webapp.log | \
grep "response_time" | \
awk '{print substr($2,1,2), $NF}' | \
awk '{sum[$1]+=$2; count[$1]++} END {for(h in sum) print h":00", sum[h]/count[h]}' | \
sort
```

### System Resource Analysis

#### Comprehensive System Check
```bash
# Create system diagnostic script
cat > system_diagnostic.py << 'EOF'
#!/usr/bin/env python3
import psutil
import time
from datetime import datetime

def system_diagnostic():
    print(f"=== System Diagnostic Report - {datetime.now()} ===")
    
    # CPU Information
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    print(f"CPU Usage: {cpu_percent}% ({cpu_count} cores)")
    
    # Memory Information
    memory = psutil.virtual_memory()
    print(f"Memory Usage: {memory.percent}% ({memory.used / (1024**3):.2f}GB / {memory.total / (1024**3):.2f}GB)")
    
    # Disk Information
    disk = psutil.disk_usage('/')
    print(f"Disk Usage: {disk.percent}% ({disk.used / (1024**3):.2f}GB / {disk.total / (1024**3):.2f}GB)")
    
    # Network Information
    network = psutil.net_io_counters()
    print(f"Network - Sent: {network.bytes_sent / (1024**2):.2f}MB, Received: {network.bytes_recv / (1024**2):.2f}MB")
    
    # Process Information
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        if 'python' in proc.info['name'].lower():
            processes.append(proc.info)
    
    print("\nPython Processes:")
    for proc in sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:5]:
        print(f"  PID {proc['pid']}: {proc['name']} - CPU: {proc['cpu_percent']}%, Memory: {proc['memory_percent']:.2f}%")

if __name__ == "__main__":
    system_diagnostic()
EOF

python system_diagnostic.py
```

## Emergency Procedures

### Critical System Recovery

#### Complete System Restart
```bash
# Graceful application shutdown
pkill -TERM -f "python web_app.py"
sleep 10

# Force kill if needed
pkill -KILL -f "python web_app.py"

# Clear temporary files
rm -rf /tmp/vedfolnir_*

# Restart services
systemctl restart redis
systemctl restart mysql

# Restart application
python web_app.py & sleep 10
```

#### Database Recovery
```bash
# Check database integrity
mysql -u root -p vedfolnir -e "CHECK TABLE users, posts, images;"

# Repair tables if needed
mysql -u root -p vedfolnir -e "REPAIR TABLE users, posts, images;"

# Optimize database
mysql -u root -p vedfolnir -e "OPTIMIZE TABLE users, posts, images;"
```

#### Redis Recovery
```bash
# Check Redis status
redis-cli ping

# Clear Redis cache if corrupted
redis-cli FLUSHDB

# Restart Redis service
systemctl restart redis
```

### Escalation Procedures

#### Level 1: Automated Recovery
- Automated cleanup triggers activate
- System attempts self-recovery
- Alerts generated for monitoring

#### Level 2: Administrative Intervention
- Admin dashboard alerts require attention
- Manual optimization procedures needed
- Configuration adjustments required

#### Level 3: Technical Support
- System-wide performance degradation
- Multiple component failures
- Expert technical intervention required

#### Level 4: Emergency Response
- Complete system failure
- Data integrity concerns
- Immediate expert response required

## Monitoring and Prevention

### Proactive Monitoring Setup

#### Alert Configuration
```bash
# Set up comprehensive alerting
cat > alert_config.py << 'EOF'
ALERT_THRESHOLDS = {
    'memory_warning': 70,
    'memory_critical': 85,
    'cpu_warning': 75,
    'cpu_critical': 90,
    'response_time_warning': 3.0,
    'response_time_critical': 8.0,
    'error_rate_warning': 2.0,
    'error_rate_critical': 5.0
}
EOF
```

#### Automated Health Checks
```bash
# Create health check script
cat > health_check.sh << 'EOF'
#!/bin/bash
# Automated health check script

echo "=== Health Check - $(date) ==="

# Check application response
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health | grep -q "200"; then
    echo "✓ Application responding"
else
    echo "✗ Application not responding"
fi

# Check database connectivity
if python -c "from database import DatabaseManager; from config import Config; DatabaseManager(Config()).test_mysql_connection()" 2>/dev/null; then
    echo "✓ Database connected"
else
    echo "✗ Database connection failed"
fi

# Check Redis connectivity
if redis-cli ping | grep -q "PONG"; then
    echo "✓ Redis connected"
else
    echo "✗ Redis connection failed"
fi

# Check system resources
MEMORY_USAGE=$(python -c "import psutil; print(int(psutil.virtual_memory().percent))")
if [ $MEMORY_USAGE -lt 80 ]; then
    echo "✓ Memory usage: ${MEMORY_USAGE}%"
else
    echo "⚠ Memory usage high: ${MEMORY_USAGE}%"
fi

echo "=== Health Check Complete ==="
EOF

chmod +x health_check.sh

# Schedule regular health checks
echo "*/5 * * * * /path/to/health_check.sh >> /var/log/vedfolnir_health.log 2>&1" | crontab -
```

### Performance Baseline Establishment

#### Baseline Metrics Collection
```bash
# Collect baseline performance metrics
python -c "
import json
from datetime import datetime
from utils.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor()
baseline = {
    'timestamp': datetime.now().isoformat(),
    'avg_response_time': monitor.get_average_response_time(),
    'memory_usage': monitor.get_memory_usage(),
    'cpu_usage': monitor.get_cpu_usage(),
    'error_rate': monitor.get_error_rate(),
    'throughput': monitor.get_throughput()
}

with open('performance_baseline.json', 'w') as f:
    json.dump(baseline, f, indent=2)

print('Baseline metrics saved to performance_baseline.json')
"
```

## Support Resources

### Documentation References
- [Performance Monitoring Guide](../performance/responsiveness-monitoring.md)
- [Admin Dashboard Guide](../admin/responsiveness-dashboard-guide.md)
- [Configuration Guide](../deployment/responsiveness-configuration.md)
- [API Documentation](../api/responsiveness-api.md)

### Diagnostic Tools
- **System Diagnostic Script**: `system_diagnostic.py`
- **Health Check Script**: `health_check.sh`
- **Performance Profiler**: Built-in profiling tools
- **Log Analysis Tools**: Automated log analysis scripts

### Contact Information
- **Technical Support**: Contact development team for complex issues
- **Emergency Response**: Use escalation procedures for critical issues
- **Community Support**: Check project documentation and forums
- **Bug Reports**: Submit issues through project issue tracker

This troubleshooting guide provides comprehensive coverage of common responsiveness monitoring issues. For additional support or complex problems, refer to the technical documentation or contact the development team.