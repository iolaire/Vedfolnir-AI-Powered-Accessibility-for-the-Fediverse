# Enhanced Maintenance Mode - Operational Procedures

## Overview

This document outlines the operational procedures for managing the Enhanced Maintenance Mode system in production environments. It covers routine maintenance operations, emergency procedures, monitoring protocols, and best practices for system administrators and operations teams.

## Routine Maintenance Procedures

### Daily Operations

#### Morning System Health Check
**Frequency**: Every morning at 8:00 AM  
**Duration**: 10-15 minutes  
**Responsible**: Operations Team

**Procedure**:
1. **System Status Review**
   ```bash
   # Check overall system health
   /opt/vedfolnir/scripts/health_check.sh
   
   # Review overnight logs
   tail -100 /opt/vedfolnir/logs/webapp.log | grep -E "ERROR|CRITICAL|MAINTENANCE"
   
   # Check system resources
   df -h
   free -h
   top -bn1 | head -20
   ```

2. **Maintenance Mode Status**
   ```bash
   # Check if maintenance mode is active
   curl -s http://localhost:5000/api/maintenance/status | jq '.is_active'
   
   # If active, verify it's intentional
   curl -s http://localhost:5000/api/maintenance/status | jq '.reason, .started_at, .estimated_completion'
   ```

3. **Database Health**
   ```bash
   # Check database connections
   mysql -u vedfolnir_user -p -e "SHOW PROCESSLIST;" | wc -l
   
   # Check database size
   mysql -u vedfolnir_user -p -e "
   SELECT 
     table_schema AS 'Database',
     ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
   FROM information_schema.tables 
   WHERE table_schema = 'vedfolnir';"
   ```

4. **Redis Health**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Check Redis memory usage
   redis-cli info memory | grep used_memory_human
   
   # Check active sessions
   redis-cli keys "vedfolnir:session:*" | wc -l
   ```

5. **Performance Metrics Review**
   ```bash
   # Check recent performance metrics
   tail -20 /var/log/vedfolnir_metrics.log
   
   # Check for performance alerts
   grep "$(date +%Y-%m-%d)" /var/log/vedfolnir_metrics.log | awk -F',' '{print $2, $3}' | tail -10
   ```

**Documentation**: Record findings in daily operations log

#### Evening System Review
**Frequency**: Every evening at 6:00 PM  
**Duration**: 5-10 minutes  
**Responsible**: Operations Team

**Procedure**:
1. **Daily Activity Summary**
   ```bash
   # Count maintenance mode activations today
   grep "$(date +%Y-%m-%d)" /opt/vedfolnir/logs/webapp.log | grep -c "Maintenance mode activated"
   
   # Count blocked operations today
   grep "$(date +%Y-%m-%d)" /opt/vedfolnir/logs/webapp.log | grep -c "Operation blocked"
   
   # Check for any errors today
   grep "$(date +%Y-%m-%d)" /opt/vedfolnir/logs/webapp.log | grep -c "ERROR"
   ```

2. **Resource Usage Trends**
   ```bash
   # Check peak resource usage today
   grep "$(date +%Y-%m-%d)" /var/log/vedfolnir_metrics.log | sort -t',' -k2 -nr | head -1
   ```

3. **Backup Verification**
   ```bash
   # Verify daily backups completed
   ls -la /backup/ | grep "$(date +%Y%m%d)"
   ```

### Weekly Operations

#### Weekly Maintenance Review
**Frequency**: Every Monday at 9:00 AM  
**Duration**: 30-45 minutes  
**Responsible**: Senior Operations Team

**Procedure**:
1. **Weekly Statistics**
   ```bash
   # Generate weekly maintenance statistics
   cat > /tmp/weekly_stats.sh << 'EOF'
   #!/bin/bash
   WEEK_START=$(date -d "last monday" +%Y-%m-%d)
   WEEK_END=$(date +%Y-%m-%d)
   
   echo "=== Weekly Maintenance Statistics ($WEEK_START to $WEEK_END) ==="
   
   # Maintenance activations
   ACTIVATIONS=$(grep -c "Maintenance mode activated" /opt/vedfolnir/logs/webapp.log)
   echo "Maintenance activations: $ACTIVATIONS"
   
   # Emergency activations
   EMERGENCIES=$(grep -c "Emergency maintenance activated" /opt/vedfolnir/logs/webapp.log)
   echo "Emergency activations: $EMERGENCIES"
   
   # Blocked operations
   BLOCKED=$(grep -c "Operation blocked" /opt/vedfolnir/logs/webapp.log)
   echo "Blocked operations: $BLOCKED"
   
   # Average maintenance duration
   echo "Average maintenance duration: [Manual calculation needed]"
   
   # System uptime
   echo "System uptime: $(uptime -p)"
   EOF
   
   chmod +x /tmp/weekly_stats.sh
   /tmp/weekly_stats.sh
   ```

2. **Performance Analysis**
   ```bash
   # Analyze weekly performance trends
   grep "$(date -d "7 days ago" +%Y-%m-%d)" /var/log/vedfolnir_metrics.log | \
   awk -F',' '{
     cpu += substr($2, 5, length($2)-6);
     mem += substr($3, 8, length($3)-9);
     count++
   } END {
     print "Average CPU: " cpu/count "%";
     print "Average Memory: " mem/count "%"
   }'
   ```

3. **Log Rotation and Cleanup**
   ```bash
   # Force log rotation
   sudo logrotate -f /etc/logrotate.d/vedfolnir
   
   # Clean up old temporary files
   find /tmp -name "vedfolnir_*" -mtime +7 -delete
   
   # Clean up old backup files (keep 30 days)
   find /backup -name "*.sql" -mtime +30 -delete
   find /backup -name "*.tar.gz" -mtime +30 -delete
   ```

4. **Security Review**
   ```bash
   # Review security events
   grep "$(date -d "7 days ago" +%Y-%m-%d)" /opt/vedfolnir/logs/security_events.log | \
   grep -E "FAILED_LOGIN|UNAUTHORIZED|BLOCKED" | wc -l
   
   # Check for suspicious activity
   grep "$(date +%Y-%m-%d)" /opt/vedfolnir/logs/webapp.log | \
   grep -E "403|401|429" | head -10
   ```

#### Weekly System Optimization
**Frequency**: Every Sunday at 2:00 AM  
**Duration**: 1-2 hours  
**Responsible**: Automated with manual oversight

**Procedure**:
1. **Database Optimization**
   ```bash
   # Optimize database tables
   mysql -u vedfolnir_user -p vedfolnir -e "
   OPTIMIZE TABLE users, platform_connections, posts, images, processing_runs, user_sessions;
   "
   
   # Update table statistics
   mysql -u vedfolnir_user -p vedfolnir -e "
   ANALYZE TABLE users, platform_connections, posts, images, processing_runs, user_sessions;
   "
   ```

2. **Redis Optimization**
   ```bash
   # Clean up expired sessions
   redis-cli eval "
   local keys = redis.call('keys', 'vedfolnir:session:*')
   local expired = 0
   for i=1,#keys do
     if redis.call('ttl', keys[i]) == -1 then
       redis.call('del', keys[i])
       expired = expired + 1
     end
   end
   return expired
   " 0
   ```

3. **System Cleanup**
   ```bash
   # Clean package cache
   sudo apt autoremove -y
   sudo apt autoclean
   
   # Clean Python cache
   find /opt/vedfolnir -name "*.pyc" -delete
   find /opt/vedfolnir -name "__pycache__" -type d -exec rm -rf {} +
   
   # Clean temporary files
   sudo find /tmp -type f -atime +7 -delete
   ```

### Monthly Operations

#### Monthly Security Audit
**Frequency**: First Monday of each month  
**Duration**: 2-3 hours  
**Responsible**: Security Team with Operations Support

**Procedure**:
1. **Access Review**
   ```bash
   # Review admin users
   python -c "
   from app.core.database.core.database_manager import DatabaseManager
   from models import User, UserRole
   from config import Config
   config = Config()
   db_manager = DatabaseManager(config)
   with db_manager.get_session() as session:
     admins = session.query(User).filter_by(role=UserRole.ADMIN).all()
     print('Admin users:')
     for admin in admins:
       print(f'  - {admin.username} ({admin.email})')
   "
   ```

2. **Security Configuration Review**
   ```bash
   # Check security settings
   grep -E "SECURITY_|CSRF_|RATE_LIMIT" /opt/vedfolnir/.env
   
   # Review firewall rules
   sudo ufw status verbose
   
   # Check SSL certificate expiration
   echo | openssl s_client -servername your-domain.com -connect your-domain.com:443 2>/dev/null | \
   openssl x509 -noout -dates
   ```

3. **Vulnerability Assessment**
   ```bash
   # Update system packages
   sudo apt update
   sudo apt list --upgradable
   
   # Check Python package vulnerabilities
   pip list --outdated
   
   # Review security logs
   grep -E "SECURITY|BREACH|ATTACK" /opt/vedfolnir/logs/security_events.log | tail -20
   ```

#### Monthly Performance Review
**Frequency**: Second Monday of each month  
**Duration**: 1-2 hours  
**Responsible**: Operations Team

**Procedure**:
1. **Performance Trend Analysis**
   ```bash
   # Generate monthly performance report
   cat > /tmp/monthly_performance.sh << 'EOF'
   #!/bin/bash
   MONTH=$(date +%Y-%m)
   
   echo "=== Monthly Performance Report ($MONTH) ==="
   
   # Average response times (manual calculation from logs)
   echo "Average response times: [Requires log analysis]"
   
   # Peak resource usage
   grep "$MONTH" /var/log/vedfolnir_metrics.log | \
   sort -t',' -k2 -nr | head -1 | \
   awk -F',' '{print "Peak CPU usage: " $2}'
   
   # Database growth
   mysql -u vedfolnir_user -p -e "
   SELECT 
     table_name,
     table_rows,
     ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
   FROM information_schema.tables 
   WHERE table_schema = 'vedfolnir'
   ORDER BY (data_length + index_length) DESC;"
   EOF
   
   chmod +x /tmp/monthly_performance.sh
   /tmp/monthly_performance.sh
   ```

2. **Capacity Planning**
   ```bash
   # Check disk usage trends
   df -h | grep -E "/$|/opt|/var"
   
   # Check database size growth
   mysql -u vedfolnir_user -p -e "
   SELECT 
     ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Total Size (MB)'
   FROM information_schema.tables 
   WHERE table_schema = 'vedfolnir';"
   
   # Check Redis memory usage trends
   redis-cli info memory | grep -E "used_memory_human|maxmemory_human"
   ```

## Emergency Maintenance Procedures

### Emergency Response Protocol

#### Immediate Response (0-5 minutes)
**Trigger**: Critical system issues, security incidents, or data integrity threats

**Procedure**:
1. **Assess Situation**
   - Identify the nature and scope of the emergency
   - Determine immediate risk to system and data
   - Classify emergency severity (Critical/High/Medium)

2. **Activate Emergency Mode**
   ```bash
   # Activate emergency maintenance immediately
   curl -X POST http://localhost:5000/api/maintenance/emergency \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{
       "reason": "EMERGENCY: [Brief description of issue]",
       "terminate_jobs": true,
       "grace_period": 30
     }'
   ```

3. **Notify Emergency Team**
   ```bash
   # Send emergency notification
   echo "EMERGENCY MAINTENANCE ACTIVATED
   Time: $(date)
   Reason: [Emergency reason]
   System Status: Emergency mode active
   Next Update: [Time]
   
   Emergency Response Team:
   - Primary: [Contact info]
   - Secondary: [Contact info]
   - Security: [Contact info]" | \
   mail -s "EMERGENCY: Vedfolnir Maintenance Activated" emergency-team@your-domain.com
   ```

#### Extended Response (5-30 minutes)
**Focus**: Containment, assessment, and initial recovery planning

**Procedure**:
1. **System Isolation**
   ```bash
   # If security incident, consider additional isolation
   # Block external access if needed
   sudo ufw deny from any to any port 80
   sudo ufw deny from any to any port 443
   
   # Stop non-essential services
   sudo systemctl stop nginx  # If using reverse proxy
   ```

2. **Data Protection**
   ```bash
   # Create emergency backup
   mysqldump -u vedfolnir_user -p vedfolnir > /backup/emergency_$(date +%Y%m%d_%H%M%S).sql
   
   # Backup Redis data
   redis-cli BGSAVE
   cp /var/lib/redis/dump.rdb /backup/redis_emergency_$(date +%Y%m%d_%H%M%S).rdb
   
   # Backup application state
   tar -czf /backup/app_emergency_$(date +%Y%m%d_%H%M%S).tar.gz /opt/vedfolnir/
   ```

3. **Evidence Preservation**
   ```bash
   # Preserve logs for forensic analysis
   cp -r /opt/vedfolnir/logs /backup/logs_emergency_$(date +%Y%m%d_%H%M%S)
   cp /var/log/syslog /backup/syslog_emergency_$(date +%Y%m%d_%H%M%S)
   
   # Capture system state
   ps aux > /backup/processes_emergency_$(date +%Y%m%d_%H%M%S).txt
   netstat -tulpn > /backup/network_emergency_$(date +%Y%m%d_%H%M%S).txt
   ```

### Emergency Recovery Procedures

#### Security Incident Recovery
**Scenario**: Security breach or attack detected

**Procedure**:
1. **Immediate Containment**
   ```bash
   # Activate emergency mode
   curl -X POST http://localhost:5000/api/maintenance/emergency \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"reason": "Security incident - system under attack"}'
   
   # Block suspicious IPs (example)
   sudo ufw deny from SUSPICIOUS_IP
   
   # Force all user sessions to expire
   redis-cli flushdb
   ```

2. **Investigation**
   ```bash
   # Analyze access logs
   grep "$(date +%Y-%m-%d)" /opt/vedfolnir/logs/webapp.log | \
   grep -E "401|403|429|500" > /tmp/security_analysis.log
   
   # Check for unauthorized access
   grep "UNAUTHORIZED\|FAILED_LOGIN" /opt/vedfolnir/logs/security_events.log | tail -50
   
   # Review database for unauthorized changes
   mysql -u vedfolnir_user -p -e "
   SELECT * FROM user_sessions WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
   ORDER BY created_at DESC;"
   ```

3. **Recovery Actions**
   ```bash
   # Change all admin passwords
   python -c "
   from app.core.database.core.database_manager import DatabaseManager
   from models import User, UserRole
   from config import Config
   import getpass
   config = Config()
   db_manager = DatabaseManager(config)
   with db_manager.get_session() as session:
     admins = session.query(User).filter_by(role=UserRole.ADMIN).all()
     for admin in admins:
       print(f'Reset password for {admin.username}')
       # Password reset logic here
   "
   
   # Regenerate security keys
   python scripts/setup/generate_env_secrets.py --force
   
   # Update all platform credentials
   echo "Manual task: Update all platform API credentials"
   ```

#### Data Corruption Recovery
**Scenario**: Database corruption or data integrity issues

**Procedure**:
1. **Assess Damage**
   ```bash
   # Check database integrity
   mysql -u vedfolnir_user -p -e "CHECK TABLE users, platform_connections, posts, images;"
   
   # Identify corrupted data
   mysql -u vedfolnir_user -p -e "
   SELECT COUNT(*) as total_users FROM users;
   SELECT COUNT(*) as total_posts FROM posts;
   SELECT COUNT(*) as total_images FROM images;"
   ```

2. **Recovery Options**
   ```bash
   # Option 1: Repair tables
   mysql -u vedfolnir_user -p -e "REPAIR TABLE users, platform_connections, posts, images;"
   
   # Option 2: Restore from backup
   mysql -u vedfolnir_user -p vedfolnir < /backup/vedfolnir_$(date -d "yesterday" +%Y%m%d)_*.sql
   
   # Option 3: Partial recovery (manual data reconstruction)
   echo "Manual recovery required - contact development team"
   ```

3. **Validation**
   ```bash
   # Verify data integrity after recovery
   python -c "
   from app.core.database.core.database_manager import DatabaseManager
   from models import *
   from config import Config
   config = Config()
   db_manager = DatabaseManager(config)
   with db_manager.get_session() as session:
     user_count = session.query(User).count()
     post_count = session.query(Post).count()
     print(f'Users: {user_count}, Posts: {post_count}')
   "
   ```

#### System Failure Recovery
**Scenario**: Critical system component failure

**Procedure**:
1. **Component Assessment**
   ```bash
   # Check system services
   sudo systemctl status vedfolnir mysql redis nginx
   
   # Check system resources
   df -h
   free -h
   iostat -x 1 5
   ```

2. **Service Recovery**
   ```bash
   # Restart failed services
   sudo systemctl restart mysql
   sudo systemctl restart redis
   sudo systemctl restart vedfolnir
   
   # Check service logs
   sudo journalctl -u vedfolnir -n 50
   sudo journalctl -u mysql -n 50
   sudo journalctl -u redis -n 50
   ```

3. **System Recovery**
   ```bash
   # If system recovery needed
   sudo reboot
   
   # After reboot, verify all services
   /opt/vedfolnir/scripts/health_check.sh
   ```

## Monitoring and Alerting Procedures

### Monitoring Setup

#### System Monitoring
**Tools**: Built-in health checks, system monitoring scripts  
**Frequency**: Continuous with 1-minute intervals

**Key Metrics**:
- CPU usage (alert if >80% for 5 minutes)
- Memory usage (alert if >85% for 5 minutes)
- Disk usage (alert if >90%)
- Network connectivity
- Service availability

#### Application Monitoring
**Tools**: Custom monitoring scripts, log analysis  
**Frequency**: Continuous with 30-second intervals

**Key Metrics**:
- Response times (alert if >2 seconds average)
- Error rates (alert if >5% in 5 minutes)
- Maintenance mode activations
- Blocked operation attempts
- Session invalidation rates

#### Database Monitoring
**Tools**: MySQL monitoring, custom queries  
**Frequency**: Every 5 minutes

**Key Metrics**:
- Connection count (alert if >80% of max)
- Query performance (alert if slow queries >10/minute)
- Database size growth
- Replication lag (if applicable)
- Lock contention

#### Redis Monitoring
**Tools**: Redis monitoring commands, custom scripts  
**Frequency**: Every minute

**Key Metrics**:
- Memory usage (alert if >90% of maxmemory)
- Connection count
- Session count
- Command latency
- Persistence status

### Alert Configuration

#### Critical Alerts (Immediate Response)
- System down or unreachable
- Database connection failures
- Redis connection failures
- Emergency maintenance activation
- Security incidents
- Data corruption detected

#### Warning Alerts (Response within 1 hour)
- High resource usage
- Performance degradation
- Maintenance mode activation
- High error rates
- Backup failures

#### Information Alerts (Response within 24 hours)
- Routine maintenance completion
- Performance optimization opportunities
- Capacity planning warnings
- Security audit findings

### Alert Response Procedures

#### Critical Alert Response
1. **Immediate Assessment** (0-5 minutes)
   - Acknowledge alert
   - Assess system status
   - Determine if emergency procedures needed

2. **Initial Response** (5-15 minutes)
   - Implement immediate fixes if known
   - Activate emergency procedures if needed
   - Notify additional team members if required

3. **Resolution** (15+ minutes)
   - Implement comprehensive fix
   - Verify system stability
   - Document incident and resolution

#### Warning Alert Response
1. **Assessment** (0-30 minutes)
   - Review alert details
   - Check system status
   - Determine urgency level

2. **Investigation** (30-60 minutes)
   - Investigate root cause
   - Plan resolution approach
   - Implement fix if straightforward

3. **Resolution** (1+ hours)
   - Implement comprehensive solution
   - Monitor for recurrence
   - Update procedures if needed

## Best Practices and Guidelines

### Maintenance Planning

#### Scheduled Maintenance
- **Advance Notice**: Provide 48-72 hours notice for planned maintenance
- **Timing**: Schedule during low-usage periods (typically 2-6 AM local time)
- **Duration**: Estimate realistic timeframes with 25% buffer
- **Communication**: Clear communication to all stakeholders
- **Rollback Plan**: Always have a tested rollback plan ready

#### Emergency Maintenance
- **Quick Decision Making**: Don't hesitate to activate emergency mode for critical issues
- **Clear Communication**: Provide frequent updates during emergency situations
- **Documentation**: Document all actions taken during emergencies
- **Post-Incident Review**: Conduct thorough post-incident reviews
- **Process Improvement**: Update procedures based on lessons learned

### Communication Protocols

#### Internal Communication
- **Emergency Channel**: Dedicated communication channel for emergencies
- **Status Updates**: Regular status updates during maintenance
- **Escalation Path**: Clear escalation procedures for complex issues
- **Documentation**: Document all significant decisions and actions

#### External Communication
- **User Notifications**: Clear, timely notifications to users
- **Status Page**: Maintain accurate status page information
- **Social Media**: Use official channels for broader communication
- **Stakeholder Updates**: Regular updates to key stakeholders

### Documentation Standards

#### Incident Documentation
- **Incident Timeline**: Detailed timeline of events
- **Actions Taken**: All actions and decisions documented
- **Root Cause**: Thorough root cause analysis
- **Lessons Learned**: Key lessons and improvement opportunities
- **Process Updates**: Updates to procedures based on experience

#### Operational Documentation
- **Procedure Updates**: Keep procedures current and accurate
- **Contact Information**: Maintain current contact information
- **System Changes**: Document all system changes and configurations
- **Training Materials**: Keep training materials up to date

## Conclusion

These operational procedures provide comprehensive guidance for managing the Enhanced Maintenance Mode system in production environments. Regular adherence to these procedures ensures system reliability, security, and optimal performance.

Key success factors:
- **Proactive Monitoring**: Continuous monitoring prevents issues from becoming emergencies
- **Quick Response**: Rapid response to alerts minimizes impact
- **Clear Communication**: Effective communication maintains stakeholder confidence
- **Continuous Improvement**: Regular review and improvement of procedures
- **Team Preparedness**: Well-trained team ready for any situation

For questions about these procedures or suggestions for improvements, contact the operations team or system administrators.