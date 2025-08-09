# Administrator Guide - Web Caption Generation

## Overview
This guide covers administrative monitoring, management, and troubleshooting of the web-based caption generation system.

## Admin Dashboard

### Accessing Admin Features
1. Log in with admin credentials
2. Navigate to **Admin** → **Monitoring Dashboard**
3. Access admin-only features from the dropdown menu

### System Overview
Monitor key system metrics:
- **Active Users**: Currently logged in users
- **Running Tasks**: Caption generation tasks in progress
- **System Health**: Overall system status
- **Resource Usage**: CPU, memory, and disk utilization

## Task Management

### Active Task Monitoring
View and manage all active caption generation tasks:

```
Task ID: abc123...
User: john_doe
Platform: Mastodon
Status: Running (45% complete)
Started: 2024-01-15 14:30:00
Current Step: Processing images (15/33)
Actions: [Cancel] [View Details]
```

### Task Actions
- **Cancel Task**: Stop any running task
- **View Details**: See complete task information
- **Task History**: Review completed and failed tasks
- **Bulk Operations**: Cancel multiple tasks at once

### Task Statistics
- **Completion Rate**: Percentage of successful tasks
- **Average Duration**: Typical task completion time
- **Error Rate**: Failed task percentage
- **Peak Usage**: Busiest times and user counts

## Resource Monitoring

### System Resources
Monitor server performance:
- **CPU Usage**: Current processor utilization
- **Memory Usage**: RAM consumption and availability
- **Disk Space**: Storage usage and free space
- **Database Size**: Database growth and optimization needs

### Performance Metrics
- **Response Times**: API endpoint performance
- **WebSocket Connections**: Real-time connection count
- **Queue Depth**: Pending task backlog
- **Throughput**: Tasks processed per hour

### Alerts and Thresholds
Configure monitoring alerts:
- **High CPU**: Alert when CPU > 80%
- **Low Memory**: Alert when RAM < 20% free
- **Queue Backlog**: Alert when > 10 tasks queued
- **Error Rate**: Alert when error rate > 5%

## User Management

### User Activity Monitoring
Track user behavior and usage:
- **Login Activity**: Recent user logins
- **Task History**: Per-user generation history
- **Resource Usage**: Individual user resource consumption
- **Error Patterns**: Users experiencing frequent issues

### User Support
- **Active Sessions**: See who's currently online
- **Task Assistance**: Help users with stuck tasks
- **Account Issues**: Resolve login and access problems
- **Usage Guidance**: Provide optimization recommendations

## System Configuration

### Global Settings
Configure system-wide parameters:

```python
# Maximum concurrent tasks
MAX_CONCURRENT_TASKS = 5

# Task timeout (minutes)
TASK_TIMEOUT_MINUTES = 60

# Default user limits
DEFAULT_MAX_POSTS_PER_RUN = 50
DEFAULT_CAPTION_MAX_LENGTH = 500

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = 10
RATE_LIMIT_TASKS_PER_HOUR = 5
```

### Platform Limits
Set platform-specific restrictions:
- **Mastodon**: 100 posts/hour, 5 concurrent users
- **Pixelfed**: 50 posts/hour, 3 concurrent users
- **Custom Limits**: Per-instance configuration

### Security Settings
- **Session Timeout**: User session duration
- **Failed Login Attempts**: Account lockout thresholds
- **API Rate Limits**: Request throttling
- **Admin Access**: IP restrictions and 2FA requirements

## Error Management

### Error Categories
Monitor different error types:

#### Authentication Errors
- **Invalid Tokens**: Expired or revoked platform tokens
- **Permission Denied**: Insufficient platform permissions
- **Account Suspended**: Platform account issues

#### Platform Errors
- **Rate Limits**: Platform API rate limiting
- **Service Unavailable**: Platform downtime
- **Connection Timeouts**: Network connectivity issues

#### System Errors
- **Out of Memory**: Resource exhaustion
- **Database Errors**: Database connectivity or corruption
- **AI Service Errors**: Ollama/LLaVA processing failures

### Error Recovery
Automated recovery strategies:
- **Retry with Backoff**: Temporary platform issues
- **Fail Fast**: Authentication and validation errors
- **Admin Notification**: Critical system errors

### Error Resolution
1. **Identify Pattern**: Group similar errors
2. **Root Cause Analysis**: Investigate underlying issues
3. **Apply Fix**: Implement solution
4. **Monitor Results**: Verify resolution effectiveness

## Maintenance Tasks

### Daily Tasks
- **Review Error Logs**: Check for new issues
- **Monitor Resource Usage**: Ensure adequate capacity
- **Check Active Tasks**: Verify normal operation
- **User Support**: Respond to user issues

### Weekly Tasks
- **Database Cleanup**: Remove old completed tasks
- **Performance Review**: Analyze system metrics
- **User Activity Analysis**: Identify usage patterns
- **Security Audit**: Review access logs

### Monthly Tasks
- **Capacity Planning**: Assess growth needs
- **Performance Optimization**: Tune system parameters
- **Security Updates**: Apply patches and updates
- **Backup Verification**: Test backup and recovery

## Troubleshooting

### Common Issues

#### High CPU Usage
```bash
# Check active processes
top -p $(pgrep -f "python.*web_app.py")

# Monitor task queue
python -c "from admin_monitoring import AdminMonitoringService; 
           service = AdminMonitoringService(); 
           print(service.get_active_tasks())"
```

#### Memory Leaks
```bash
# Monitor memory usage
ps aux | grep python | grep web_app

# Check for stuck tasks
python -c "from task_queue_manager import TaskQueueManager;
           manager = TaskQueueManager();
           print(manager.get_queue_stats())"
```

#### Database Issues
```bash
# Check database size
du -sh storage/database/

# Analyze slow queries
sqlite3 storage/database/vedfolnir.db ".timer on" ".explain query plan SELECT * FROM caption_generation_tasks WHERE status = 'running'"
```

### Emergency Procedures

#### System Overload
1. **Cancel Non-Critical Tasks**: Stop low-priority operations
2. **Increase Resources**: Scale up server capacity
3. **Enable Rate Limiting**: Reduce incoming requests
4. **Notify Users**: Communicate service degradation

#### Data Corruption
1. **Stop All Services**: Prevent further damage
2. **Restore from Backup**: Use latest clean backup
3. **Verify Integrity**: Check data consistency
4. **Resume Operations**: Restart services gradually

#### Security Incident
1. **Isolate System**: Disconnect from network if needed
2. **Preserve Evidence**: Capture logs and system state
3. **Assess Damage**: Determine scope of compromise
4. **Implement Fixes**: Apply security patches
5. **Monitor Activity**: Watch for continued threats

## Performance Optimization

### Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX idx_tasks_user_status ON caption_generation_tasks(user_id, status);
CREATE INDEX idx_tasks_created_at ON caption_generation_tasks(created_at);

-- Analyze query performance
EXPLAIN QUERY PLAN SELECT * FROM caption_generation_tasks 
WHERE user_id = ? AND status IN ('queued', 'running');
```

### Memory Management
- **Task Cleanup**: Remove completed tasks after 24 hours
- **Session Management**: Clean up expired user sessions
- **Cache Optimization**: Tune Redis cache settings
- **Garbage Collection**: Monitor Python memory usage

### Network Optimization
- **WebSocket Tuning**: Optimize connection pooling
- **HTTP Compression**: Enable gzip compression
- **CDN Usage**: Serve static assets from CDN
- **Connection Limits**: Tune concurrent connection limits

## Monitoring and Alerting

### Key Metrics to Monitor
- **Task Success Rate**: > 95%
- **Average Task Duration**: < 10 minutes
- **System Response Time**: < 2 seconds
- **Error Rate**: < 1%
- **Resource Utilization**: < 80%

### Alert Configuration
```python
ALERTS = {
    'high_error_rate': {
        'threshold': 0.05,  # 5%
        'window': '5m',
        'action': 'email_admin'
    },
    'long_running_tasks': {
        'threshold': 1800,  # 30 minutes
        'action': 'cancel_and_notify'
    },
    'resource_exhaustion': {
        'cpu_threshold': 0.9,
        'memory_threshold': 0.9,
        'action': 'scale_up'
    }
}
```

### Log Analysis
```bash
# Monitor error patterns
grep "ERROR" logs/vedfolnir.log | tail -50

# Track task completion rates
grep "Task completed" logs/vedfolnir.log | wc -l

# Analyze performance trends
awk '/Task.*completed/ {print $1, $2, $NF}' logs/vedfolnir.log
```