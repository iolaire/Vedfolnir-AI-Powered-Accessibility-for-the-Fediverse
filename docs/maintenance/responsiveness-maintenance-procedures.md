# Responsiveness Monitoring Maintenance Procedures

## Overview

This document provides comprehensive maintenance procedures for the Flask App Responsiveness Monitoring system. It covers routine maintenance tasks, optimization procedures, and long-term system health management to ensure optimal performance and reliability.

## Maintenance Schedule

### Daily Maintenance (5-10 minutes)

#### Morning Health Check (5 minutes)
```bash
#!/bin/bash
# daily_morning_check.sh

echo "=== Daily Morning Health Check - $(date) ==="

# 1. Check system status
echo "1. System Status:"
systemctl is-active vedfolnir mysql redis nginx | paste <(echo -e "Vedfolnir\nMySQL\nRedis\nNginx") -

# 2. Review overnight alerts
echo -e "\n2. Overnight Alerts:"
python -c "
from admin.services.monitoring_service import MonitoringService
service = MonitoringService()
alerts = service.get_alerts_since_hours(12)
if alerts:
    for alert in alerts[-5:]:  # Last 5 alerts
        print(f'  {alert[\"timestamp\"]} - {alert[\"severity\"]}: {alert[\"message\"]}')
else:
    print('  No alerts in the last 12 hours')
"

# 3. Check resource usage
echo -e "\n3. Resource Usage:"
python -c "
import psutil
memory = psutil.virtual_memory()
cpu = psutil.cpu_percent(interval=1)
print(f'  Memory: {memory.percent:.1f}% ({memory.used / (1024**3):.2f}GB / {memory.total / (1024**3):.2f}GB)')
print(f'  CPU: {cpu:.1f}%')
"

# 4. Database connection health
echo -e "\n4. Database Health:"
python -c "
from database import DatabaseManager
from config import Config
db = DatabaseManager(Config())
try:
    stats = db.get_mysql_performance_stats()
    print(f'  Active connections: {stats.get(\"active_connections\", \"N/A\")}')
    print(f'  Pool utilization: {stats.get(\"pool_utilization\", \"N/A\")}%')
    print(f'  Query time avg: {stats.get(\"avg_query_time\", \"N/A\")}ms')
except Exception as e:
    print(f'  Error: {e}')
"

# 5. Redis health
echo -e "\n5. Redis Health:"
redis-cli ping > /dev/null 2>&1 && echo "  Redis: Connected" || echo "  Redis: Connection failed"
redis-cli info memory | grep used_memory_human | cut -d: -f2

# 6. Background task status
echo -e "\n6. Background Tasks:"
python -c "
from background_cleanup_manager import BackgroundCleanupManager
try:
    manager = BackgroundCleanupManager()
    stats = manager.get_cleanup_stats()
    print(f'  Active tasks: {stats.get(\"active_tasks\", 0)}')
    print(f'  Success rate: {stats.get(\"success_rate\", 0):.1f}%')
    print(f'  Last cleanup: {stats.get(\"last_cleanup\", \"N/A\")}')
except Exception as e:
    print(f'  Error: {e}')
"

echo -e "\n=== Morning Check Complete ===\n"
```

#### Evening Performance Review (5 minutes)
```bash
#!/bin/bash
# daily_evening_review.sh

echo "=== Daily Evening Performance Review - $(date) ==="

# 1. Performance summary
echo "1. Daily Performance Summary:"
python -c "
from utils.performance_monitor import PerformanceMonitor
try:
    monitor = PerformanceMonitor()
    today_stats = monitor.get_daily_stats()
    print(f'  Avg response time: {today_stats.get(\"avg_response_time\", \"N/A\")}s')
    print(f'  Total requests: {today_stats.get(\"total_requests\", \"N/A\")}')
    print(f'  Error rate: {today_stats.get(\"error_rate\", \"N/A\")}%')
    print(f'  Slow requests: {today_stats.get(\"slow_requests\", \"N/A\")}')
except Exception as e:
    print(f'  Error: {e}')
"

# 2. Resource usage trends
echo -e "\n2. Resource Usage Trends:"
python -c "
import psutil
from datetime import datetime, timedelta
# Current usage
memory = psutil.virtual_memory()
cpu = psutil.cpu_percent(interval=1)
print(f'  Current Memory: {memory.percent:.1f}%')
print(f'  Current CPU: {cpu:.1f}%')
# Peak usage (would need historical data in production)
print('  Peak usage: Check monitoring dashboard for historical data')
"

# 3. Cleanup effectiveness
echo -e "\n3. Cleanup Effectiveness:"
python -c "
from background_cleanup_manager import BackgroundCleanupManager
try:
    manager = BackgroundCleanupManager()
    cleanup_stats = manager.get_daily_cleanup_stats()
    print(f'  Cleanups performed: {cleanup_stats.get(\"cleanup_count\", 0)}')
    print(f'  Memory freed: {cleanup_stats.get(\"memory_freed_mb\", 0)}MB')
    print(f'  Sessions cleaned: {cleanup_stats.get(\"sessions_cleaned\", 0)}')
except Exception as e:
    print(f'  Error: {e}')
"

# 4. Alert summary
echo -e "\n4. Daily Alert Summary:"
python -c "
from admin.services.monitoring_service import MonitoringService
try:
    service = MonitoringService()
    daily_alerts = service.get_daily_alert_summary()
    print(f'  Total alerts: {daily_alerts.get(\"total\", 0)}')
    print(f'  Critical: {daily_alerts.get(\"critical\", 0)}')
    print(f'  Warning: {daily_alerts.get(\"warning\", 0)}')
    print(f'  Resolved: {daily_alerts.get(\"resolved\", 0)}')
except Exception as e:
    print(f'  Error: {e}')
"

echo -e "\n=== Evening Review Complete ===\n"
```

### Weekly Maintenance (30-45 minutes)

#### Performance Analysis and Optimization
```bash
#!/bin/bash
# weekly_performance_analysis.sh

echo "=== Weekly Performance Analysis - $(date) ==="

# 1. Performance trend analysis
echo "1. Performance Trend Analysis:"
python -c "
from utils.performance_monitor import PerformanceMonitor
from datetime import datetime, timedelta

monitor = PerformanceMonitor()
try:
    # Get weekly trends
    weekly_stats = monitor.get_weekly_trends()
    print(f'  Avg response time trend: {weekly_stats.get(\"response_time_trend\", \"N/A\")}')
    print(f'  Memory usage trend: {weekly_stats.get(\"memory_trend\", \"N/A\")}')
    print(f'  Error rate trend: {weekly_stats.get(\"error_trend\", \"N/A\")}')
    
    # Identify performance bottlenecks
    bottlenecks = monitor.identify_bottlenecks()
    if bottlenecks:
        print('  Performance bottlenecks identified:')
        for bottleneck in bottlenecks:
            print(f'    - {bottleneck}')
    else:
        print('  No significant bottlenecks identified')
        
except Exception as e:
    print(f'  Error: {e}')
"

# 2. Database performance analysis
echo -e "\n2. Database Performance Analysis:"
mysql -u root -p -e "
SELECT 
    ROUND(AVG(query_time), 4) as avg_query_time,
    ROUND(AVG(lock_time), 4) as avg_lock_time,
    COUNT(*) as query_count
FROM mysql.slow_log 
WHERE start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY);
" 2>/dev/null || echo "  Slow query log not available"

# 3. Connection pool analysis
echo -e "\n3. Connection Pool Analysis:"
python -c "
from database import DatabaseManager
from config import Config
try:
    db = DatabaseManager(Config())
    pool_stats = db.get_weekly_pool_stats()
    print(f'  Peak utilization: {pool_stats.get(\"peak_utilization\", \"N/A\")}%')
    print(f'  Avg utilization: {pool_stats.get(\"avg_utilization\", \"N/A\")}%')
    print(f'  Connection leaks detected: {pool_stats.get(\"leak_count\", 0)}')
except Exception as e:
    print(f'  Error: {e}')
"

# 4. Memory usage analysis
echo -e "\n4. Memory Usage Analysis:"
python -c "
from utils.performance_monitor import PerformanceMonitor
try:
    monitor = PerformanceMonitor()
    memory_analysis = monitor.analyze_weekly_memory_usage()
    print(f'  Peak memory usage: {memory_analysis.get(\"peak_usage\", \"N/A\")}%')
    print(f'  Average memory usage: {memory_analysis.get(\"avg_usage\", \"N/A\")}%')
    print(f'  Memory leak indicators: {memory_analysis.get(\"leak_indicators\", \"None\")}')
except Exception as e:
    print(f'  Error: {e}')
"

echo -e "\n=== Weekly Analysis Complete ===\n"
```

#### System Optimization
```bash
#!/bin/bash
# weekly_optimization.sh

echo "=== Weekly System Optimization - $(date) ==="

# 1. Database optimization
echo "1. Database Optimization:"
mysql -u root -p -e "
OPTIMIZE TABLE users, posts, images, platform_connections, processing_runs;
ANALYZE TABLE users, posts, images, platform_connections, processing_runs;
" 2>/dev/null && echo "  Database tables optimized" || echo "  Database optimization failed"

# 2. Redis optimization
echo -e "\n2. Redis Optimization:"
redis-cli MEMORY PURGE > /dev/null 2>&1 && echo "  Redis memory purged" || echo "  Redis purge failed"

# 3. Log rotation and cleanup
echo -e "\n3. Log Cleanup:"
find /opt/vedfolnir/logs -name "*.log" -mtime +30 -delete
find /var/log -name "*vedfolnir*" -mtime +30 -delete
echo "  Old log files cleaned up"

# 4. Temporary file cleanup
echo -e "\n4. Temporary File Cleanup:"
find /tmp -name "vedfolnir_*" -mtime +1 -delete
find /opt/vedfolnir/storage/temp -type f -mtime +7 -delete
echo "  Temporary files cleaned up"

# 5. Session cleanup
echo -e "\n5. Session Cleanup:"
python -c "
from session_middleware_v2 import RedisSessionManager
try:
    manager = RedisSessionManager()
    cleaned = manager.cleanup_expired_sessions()
    print(f'  Cleaned {cleaned} expired sessions')
except Exception as e:
    print(f'  Error: {e}')
"

echo -e "\n=== Weekly Optimization Complete ===\n"
```

### Monthly Maintenance (1-2 hours)

#### Comprehensive System Review
```bash
#!/bin/bash
# monthly_system_review.sh

echo "=== Monthly System Review - $(date) ==="

# 1. Performance baseline comparison
echo "1. Performance Baseline Comparison:"
python -c "
import json
from datetime import datetime, timedelta
from utils.performance_monitor import PerformanceMonitor

try:
    # Load baseline metrics
    with open('performance_baseline.json', 'r') as f:
        baseline = json.load(f)
    
    # Get current metrics
    monitor = PerformanceMonitor()
    current = monitor.get_current_metrics()
    
    # Compare metrics
    print(f'  Response Time: Baseline {baseline.get(\"avg_response_time\", \"N/A\")}s, Current {current.get(\"avg_response_time\", \"N/A\")}s')
    print(f'  Memory Usage: Baseline {baseline.get(\"memory_usage\", \"N/A\")}%, Current {current.get(\"memory_usage\", \"N/A\")}%')
    print(f'  Error Rate: Baseline {baseline.get(\"error_rate\", \"N/A\")}%, Current {current.get(\"error_rate\", \"N/A\")}%')
    
    # Calculate performance changes
    if baseline.get('avg_response_time') and current.get('avg_response_time'):
        change = ((current['avg_response_time'] - baseline['avg_response_time']) / baseline['avg_response_time']) * 100
        print(f'  Performance change: {change:+.1f}%')
        
except Exception as e:
    print(f'  Error: {e}')
"

# 2. Capacity planning analysis
echo -e "\n2. Capacity Planning Analysis:"
python -c "
from utils.performance_monitor import PerformanceMonitor
try:
    monitor = PerformanceMonitor()
    capacity_analysis = monitor.analyze_capacity_trends()
    print(f'  Projected memory usage (3 months): {capacity_analysis.get(\"memory_projection\", \"N/A\")}%')
    print(f'  Projected storage usage (3 months): {capacity_analysis.get(\"storage_projection\", \"N/A\")}%')
    print(f'  Recommended actions: {capacity_analysis.get(\"recommendations\", \"None\")}')
except Exception as e:
    print(f'  Error: {e}')
"

# 3. Security audit
echo -e "\n3. Security Audit:"
python -c "
from security.audit.security_audit import SecurityAudit
try:
    audit = SecurityAudit()
    results = audit.run_monthly_audit()
    print(f'  Security score: {results.get(\"score\", \"N/A\")}/100')
    print(f'  Issues found: {len(results.get(\"issues\", []))}')
    if results.get('issues'):
        for issue in results['issues'][:3]:  # Show top 3 issues
            print(f'    - {issue}')
except Exception as e:
    print(f'  Error: {e}')
"

# 4. Backup verification
echo -e "\n4. Backup Verification:"
latest_db_backup=$(ls -t /opt/vedfolnir/backups/vedfolnir_*.sql.gz 2>/dev/null | head -1)
latest_redis_backup=$(ls -t /opt/vedfolnir/backups/redis_*.rdb.gz 2>/dev/null | head -1)

if [ -n "$latest_db_backup" ]; then
    echo "  Latest database backup: $(basename $latest_db_backup)"
    echo "  Backup age: $(find $latest_db_backup -mtime +1 > /dev/null && echo 'More than 1 day old' || echo 'Recent')"
else
    echo "  No database backups found"
fi

if [ -n "$latest_redis_backup" ]; then
    echo "  Latest Redis backup: $(basename $latest_redis_backup)"
else
    echo "  No Redis backups found"
fi

echo -e "\n=== Monthly Review Complete ===\n"
```

#### Configuration Optimization
```bash
#!/bin/bash
# monthly_config_optimization.sh

echo "=== Monthly Configuration Optimization - $(date) ==="

# 1. Analyze current configuration effectiveness
echo "1. Configuration Effectiveness Analysis:"
python -c "
from config import Config
from utils.performance_monitor import PerformanceMonitor

config = Config()
monitor = PerformanceMonitor()

try:
    # Analyze responsiveness configuration
    rc = config.responsiveness_config
    effectiveness = monitor.analyze_config_effectiveness()
    
    print(f'  Memory threshold effectiveness: {effectiveness.get(\"memory_threshold\", \"N/A\")}')
    print(f'  Cleanup interval effectiveness: {effectiveness.get(\"cleanup_interval\", \"N/A\")}')
    print(f'  Monitoring interval effectiveness: {effectiveness.get(\"monitoring_interval\", \"N/A\")}')
    
    # Suggest optimizations
    suggestions = monitor.suggest_config_optimizations()
    if suggestions:
        print('  Optimization suggestions:')
        for suggestion in suggestions:
            print(f'    - {suggestion}')
    else:
        print('  No configuration optimizations suggested')
        
except Exception as e:
    print(f'  Error: {e}')
"

# 2. Database configuration review
echo -e "\n2. Database Configuration Review:"
mysql -u root -p -e "
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'max_connections';
SHOW VARIABLES LIKE 'query_cache_size';
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Threads_running';
" 2>/dev/null || echo "  Database configuration review failed"

# 3. Redis configuration review
echo -e "\n3. Redis Configuration Review:"
redis-cli CONFIG GET maxmemory
redis-cli CONFIG GET maxmemory-policy
redis-cli INFO memory | grep used_memory_human

echo -e "\n=== Configuration Optimization Complete ===\n"
```

## Automated Maintenance Scripts

### Automated Daily Maintenance
```bash
#!/bin/bash
# automated_daily_maintenance.sh

LOG_FILE="/var/log/vedfolnir_maintenance.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting automated daily maintenance" >> $LOG_FILE

# 1. Health check
/opt/vedfolnir/scripts/maintenance/daily_morning_check.sh >> $LOG_FILE 2>&1

# 2. Cleanup expired sessions
python -c "
from session_middleware_v2 import RedisSessionManager
try:
    manager = RedisSessionManager()
    cleaned = manager.cleanup_expired_sessions()
    print(f'Cleaned {cleaned} expired sessions')
except Exception as e:
    print(f'Session cleanup error: {e}')
" >> $LOG_FILE 2>&1

# 3. Rotate logs
logrotate /etc/logrotate.d/vedfolnir >> $LOG_FILE 2>&1

# 4. Update performance metrics
python -c "
from utils.performance_monitor import PerformanceMonitor
try:
    monitor = PerformanceMonitor()
    monitor.update_daily_metrics()
    print('Daily metrics updated')
except Exception as e:
    print(f'Metrics update error: {e}')
" >> $LOG_FILE 2>&1

echo "[$DATE] Automated daily maintenance completed" >> $LOG_FILE
```

### Automated Weekly Maintenance
```bash
#!/bin/bash
# automated_weekly_maintenance.sh

LOG_FILE="/var/log/vedfolnir_maintenance.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting automated weekly maintenance" >> $LOG_FILE

# 1. Performance analysis
/opt/vedfolnir/scripts/maintenance/weekly_performance_analysis.sh >> $LOG_FILE 2>&1

# 2. System optimization
/opt/vedfolnir/scripts/maintenance/weekly_optimization.sh >> $LOG_FILE 2>&1

# 3. Security scan
python -c "
from security.audit.security_audit import SecurityAudit
try:
    audit = SecurityAudit()
    results = audit.run_weekly_scan()
    print(f'Security scan completed: {results.get(\"score\", \"N/A\")}/100')
except Exception as e:
    print(f'Security scan error: {e}')
" >> $LOG_FILE 2>&1

# 4. Backup verification
/opt/vedfolnir/scripts/maintenance/verify_backups.sh >> $LOG_FILE 2>&1

echo "[$DATE] Automated weekly maintenance completed" >> $LOG_FILE
```

## Performance Optimization Procedures

### Memory Optimization
```bash
#!/bin/bash
# memory_optimization.sh

echo "=== Memory Optimization Procedure ==="

# 1. Analyze current memory usage
echo "1. Current Memory Analysis:"
python -c "
import psutil
from collections import defaultdict

# Get process memory usage
processes = []
for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'memory_percent']):
    if 'python' in proc.info['name'].lower() or 'mysql' in proc.info['name'].lower() or 'redis' in proc.info['name'].lower():
        processes.append(proc.info)

# Sort by memory usage
processes.sort(key=lambda x: x['memory_percent'], reverse=True)

print('Top memory consumers:')
for proc in processes[:5]:
    memory_mb = proc['memory_info'].rss / (1024 * 1024)
    print(f'  {proc[\"name\"]} (PID {proc[\"pid\"]}): {memory_mb:.1f}MB ({proc[\"memory_percent\"]:.1f}%)')
"

# 2. Optimize Python memory usage
echo -e "\n2. Python Memory Optimization:"
python -c "
import gc
import sys

# Force garbage collection
collected = gc.collect()
print(f'Garbage collected: {collected} objects')

# Get memory usage info
memory_info = sys.getsizeof(gc.get_objects())
print(f'Python objects memory: {memory_info / (1024*1024):.1f}MB')
"

# 3. Optimize database memory
echo -e "\n3. Database Memory Optimization:"
mysql -u root -p -e "
FLUSH TABLES;
FLUSH QUERY CACHE;
SHOW STATUS LIKE 'Qcache%';
" 2>/dev/null || echo "Database optimization failed"

# 4. Optimize Redis memory
echo -e "\n4. Redis Memory Optimization:"
redis-cli MEMORY PURGE
redis-cli MEMORY USAGE vedfolnir:session:* | head -5

echo -e "\n=== Memory Optimization Complete ==="
```

### Database Optimization
```bash
#!/bin/bash
# database_optimization.sh

echo "=== Database Optimization Procedure ==="

# 1. Analyze table sizes and usage
echo "1. Table Analysis:"
mysql -u root -p -e "
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)',
    table_rows
FROM information_schema.tables 
WHERE table_schema = 'vedfolnir'
ORDER BY (data_length + index_length) DESC;
" 2>/dev/null || echo "Table analysis failed"

# 2. Identify slow queries
echo -e "\n2. Slow Query Analysis:"
mysql -u root -p -e "
SELECT 
    query_time,
    lock_time,
    rows_sent,
    rows_examined,
    LEFT(sql_text, 100) as query_preview
FROM mysql.slow_log 
ORDER BY query_time DESC 
LIMIT 5;
" 2>/dev/null || echo "Slow query analysis failed"

# 3. Check index usage
echo -e "\n3. Index Usage Analysis:"
mysql -u root -p -e "
SELECT 
    t.table_name,
    s.index_name,
    s.cardinality,
    s.seq_in_index,
    s.column_name
FROM information_schema.tables t
LEFT JOIN information_schema.statistics s ON t.table_name = s.table_name
WHERE t.table_schema = 'vedfolnir' AND s.index_name IS NOT NULL
ORDER BY t.table_name, s.index_name, s.seq_in_index;
" 2>/dev/null || echo "Index analysis failed"

# 4. Optimize tables
echo -e "\n4. Table Optimization:"
mysql -u root -p -e "
OPTIMIZE TABLE users;
OPTIMIZE TABLE posts;
OPTIMIZE TABLE images;
OPTIMIZE TABLE platform_connections;
OPTIMIZE TABLE processing_runs;
" 2>/dev/null && echo "Tables optimized" || echo "Table optimization failed"

echo -e "\n=== Database Optimization Complete ==="
```

## Monitoring and Alerting Maintenance

### Alert System Maintenance
```bash
#!/bin/bash
# alert_system_maintenance.sh

echo "=== Alert System Maintenance ==="

# 1. Review alert effectiveness
echo "1. Alert Effectiveness Review:"
python -c "
from admin.services.monitoring_service import MonitoringService
from datetime import datetime, timedelta

try:
    service = MonitoringService()
    
    # Get alert statistics for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    alert_stats = service.get_alert_statistics(start_date, end_date)
    
    print(f'  Total alerts: {alert_stats.get(\"total\", 0)}')
    print(f'  False positives: {alert_stats.get(\"false_positives\", 0)}')
    print(f'  Average resolution time: {alert_stats.get(\"avg_resolution_time\", \"N/A\")} minutes')
    print(f'  Most common alert type: {alert_stats.get(\"most_common_type\", \"N/A\")}')
    
    # Calculate alert effectiveness
    if alert_stats.get('total', 0) > 0:
        effectiveness = (1 - (alert_stats.get('false_positives', 0) / alert_stats['total'])) * 100
        print(f'  Alert effectiveness: {effectiveness:.1f}%')
    
except Exception as e:
    print(f'  Error: {e}')
"

# 2. Optimize alert thresholds
echo -e "\n2. Alert Threshold Optimization:"
python -c "
from config import Config
from utils.performance_monitor import PerformanceMonitor

try:
    config = Config()
    monitor = PerformanceMonitor()
    
    # Analyze threshold effectiveness
    threshold_analysis = monitor.analyze_alert_thresholds()
    
    print('  Current thresholds:')
    rc = config.responsiveness_config
    print(f'    Memory warning: {rc.memory_warning_threshold * 100}%')
    print(f'    Memory critical: {rc.memory_critical_threshold * 100}%')
    print(f'    CPU warning: {rc.cpu_warning_threshold * 100}%')
    print(f'    CPU critical: {rc.cpu_critical_threshold * 100}%')
    
    print('  Optimization suggestions:')
    for suggestion in threshold_analysis.get('suggestions', []):
        print(f'    - {suggestion}')
        
except Exception as e:
    print(f'  Error: {e}')
"

# 3. Clean up old alerts
echo -e "\n3. Alert Cleanup:"
python -c "
from admin.services.monitoring_service import MonitoringService
from datetime import datetime, timedelta

try:
    service = MonitoringService()
    
    # Clean up alerts older than 90 days
    cutoff_date = datetime.now() - timedelta(days=90)
    cleaned = service.cleanup_old_alerts(cutoff_date)
    
    print(f'  Cleaned up {cleaned} old alerts')
    
except Exception as e:
    print(f'  Error: {e}')
"

echo -e "\n=== Alert System Maintenance Complete ==="
```

### Monitoring Dashboard Maintenance
```bash
#!/bin/bash
# dashboard_maintenance.sh

echo "=== Monitoring Dashboard Maintenance ==="

# 1. Update dashboard metrics
echo "1. Dashboard Metrics Update:"
python -c "
from admin.services.monitoring_service import MonitoringService

try:
    service = MonitoringService()
    
    # Update dashboard cache
    service.update_dashboard_cache()
    print('  Dashboard cache updated')
    
    # Refresh performance metrics
    service.refresh_performance_metrics()
    print('  Performance metrics refreshed')
    
    # Update health status
    service.update_health_status()
    print('  Health status updated')
    
except Exception as e:
    print(f'  Error: {e}')
"

# 2. Optimize dashboard performance
echo -e "\n2. Dashboard Performance Optimization:"
python -c "
from admin.services.monitoring_service import MonitoringService

try:
    service = MonitoringService()
    
    # Analyze dashboard performance
    perf_stats = service.analyze_dashboard_performance()
    
    print(f'  Average load time: {perf_stats.get(\"avg_load_time\", \"N/A\")}ms')
    print(f'  Cache hit rate: {perf_stats.get(\"cache_hit_rate\", \"N/A\")}%')
    print(f'  Widget render time: {perf_stats.get(\"widget_render_time\", \"N/A\")}ms')
    
    # Apply optimizations
    optimizations = service.apply_dashboard_optimizations()
    print(f'  Applied {len(optimizations)} optimizations')
    
except Exception as e:
    print(f'  Error: {e}')
"

echo -e "\n=== Dashboard Maintenance Complete ==="
```

## Troubleshooting Maintenance Issues

### Common Maintenance Problems

#### Maintenance Script Failures
```bash
#!/bin/bash
# troubleshoot_maintenance.sh

echo "=== Maintenance Troubleshooting ==="

# 1. Check script permissions
echo "1. Script Permission Check:"
find /opt/vedfolnir/scripts/maintenance -name "*.sh" -not -perm -u+x -exec echo "  Missing execute permission: {}" \;

# 2. Check log file permissions
echo -e "\n2. Log File Permission Check:"
ls -la /var/log/vedfolnir* 2>/dev/null || echo "  No vedfolnir log files found"

# 3. Check disk space
echo -e "\n3. Disk Space Check:"
df -h | grep -E "(/$|/opt|/var|/tmp)"

# 4. Check service status
echo -e "\n4. Service Status Check:"
systemctl status vedfolnir mysql redis nginx --no-pager -l

# 5. Check cron jobs
echo -e "\n5. Cron Job Check:"
crontab -l | grep vedfolnir || echo "  No vedfolnir cron jobs found"

echo -e "\n=== Troubleshooting Complete ==="
```

#### Performance Degradation During Maintenance
```bash
#!/bin/bash
# maintenance_performance_check.sh

echo "=== Maintenance Performance Impact Check ==="

# 1. Monitor system resources during maintenance
echo "1. Resource Monitoring:"
python -c "
import psutil
import time

print('  Monitoring system resources for 60 seconds...')
for i in range(6):  # 6 samples over 60 seconds
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk_io = psutil.disk_io_counters()
    
    print(f'  Sample {i+1}: CPU {cpu}%, Memory {memory.percent}%, Disk I/O {disk_io.read_bytes + disk_io.write_bytes}')
    time.sleep(9)  # Wait 9 more seconds (total 10 seconds per sample)
"

# 2. Check maintenance impact on application
echo -e "\n2. Application Impact Check:"
curl -w "Response time: %{time_total}s\n" -o /dev/null -s http://localhost:5000/health

# 3. Monitor database performance during maintenance
echo -e "\n3. Database Performance Check:"
mysql -u root -p -e "SHOW PROCESSLIST;" 2>/dev/null | wc -l | xargs echo "  Active database connections:"

echo -e "\n=== Performance Impact Check Complete ==="
```

## Documentation and Reporting

### Maintenance Report Generation
```bash
#!/bin/bash
# generate_maintenance_report.sh

REPORT_DATE=$(date '+%Y-%m-%d')
REPORT_FILE="/opt/vedfolnir/reports/maintenance_report_$REPORT_DATE.md"

mkdir -p /opt/vedfolnir/reports

cat > $REPORT_FILE << EOF
# Maintenance Report - $REPORT_DATE

## Executive Summary
This report summarizes the maintenance activities and system health status for $REPORT_DATE.

## System Health Status
EOF

# Add system health information
python -c "
import psutil
from datetime import datetime

memory = psutil.virtual_memory()
cpu = psutil.cpu_percent(interval=1)
disk = psutil.disk_usage('/')

print(f'- **Memory Usage**: {memory.percent:.1f}% ({memory.used / (1024**3):.2f}GB / {memory.total / (1024**3):.2f}GB)')
print(f'- **CPU Usage**: {cpu:.1f}%')
print(f'- **Disk Usage**: {disk.percent:.1f}% ({disk.used / (1024**3):.2f}GB / {disk.total / (1024**3):.2f}GB)')
print(f'- **Report Generated**: {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}')
" >> $REPORT_FILE

cat >> $REPORT_FILE << EOF

## Performance Metrics
EOF

# Add performance metrics
python -c "
from utils.performance_monitor import PerformanceMonitor
try:
    monitor = PerformanceMonitor()
    daily_stats = monitor.get_daily_stats()
    
    print(f'- **Average Response Time**: {daily_stats.get(\"avg_response_time\", \"N/A\")}s')
    print(f'- **Total Requests**: {daily_stats.get(\"total_requests\", \"N/A\")}')
    print(f'- **Error Rate**: {daily_stats.get(\"error_rate\", \"N/A\")}%')
    print(f'- **Slow Requests**: {daily_stats.get(\"slow_requests\", \"N/A\")}')
except Exception as e:
    print(f'- **Error**: {e}')
" >> $REPORT_FILE

cat >> $REPORT_FILE << EOF

## Maintenance Activities Completed
- Daily health checks
- Performance monitoring
- Resource optimization
- Log cleanup
- Security monitoring

## Recommendations
EOF

# Add recommendations
python -c "
from utils.performance_monitor import PerformanceMonitor
try:
    monitor = PerformanceMonitor()
    recommendations = monitor.get_maintenance_recommendations()
    
    for rec in recommendations:
        print(f'- {rec}')
except Exception as e:
    print(f'- Error generating recommendations: {e}')
" >> $REPORT_FILE

echo "Maintenance report generated: $REPORT_FILE"
```

## Best Practices

### Maintenance Best Practices

1. **Schedule Maintenance Windows**
   - Plan maintenance during low-traffic periods
   - Notify users of scheduled maintenance
   - Have rollback procedures ready

2. **Monitor During Maintenance**
   - Watch system resources during maintenance
   - Monitor application performance
   - Check for errors and alerts

3. **Document Everything**
   - Keep detailed maintenance logs
   - Document any issues encountered
   - Record optimization results

4. **Test Procedures**
   - Test maintenance scripts in staging
   - Validate backup and recovery procedures
   - Verify monitoring and alerting

5. **Automate Where Possible**
   - Automate routine maintenance tasks
   - Use monitoring to trigger maintenance
   - Implement self-healing procedures

### Emergency Maintenance Procedures

#### Emergency Response Checklist
1. **Assess Situation** - Determine severity and impact
2. **Notify Stakeholders** - Alert relevant team members
3. **Implement Fix** - Apply emergency procedures
4. **Monitor Results** - Verify fix effectiveness
5. **Document Incident** - Record details for future reference

#### Emergency Contacts
- **System Administrator**: [Contact Information]
- **Database Administrator**: [Contact Information]
- **Development Team Lead**: [Contact Information]
- **Emergency Escalation**: [Contact Information]

This maintenance procedures document provides comprehensive coverage of responsiveness monitoring maintenance. For additional support or specific maintenance questions, refer to the technical documentation or contact the development team.