# Multi-Tenant Caption Management Deployment Guide

## Overview

This guide covers the deployment of the multi-tenant caption management system with comprehensive admin oversight capabilities. The deployment includes database migrations, new admin services, monitoring systems, and enhanced user interfaces.

## Prerequisites

### System Requirements
- **Database**: MySQL/MariaDB 5.7+ with admin privileges
- **Redis**: Redis 6.0+ for session management and caching
- **Python**: Python 3.8+ with all dependencies installed
- **Disk Space**: Minimum 2GB free space for backups and logs
- **Memory**: Minimum 4GB RAM for optimal performance

### Pre-Deployment Checklist
- [ ] Current system backup completed
- [ ] Database admin credentials available
- [ ] Redis server running and accessible
- [ ] All existing caption generation jobs completed or safely paused
- [ ] Admin user accounts identified and ready
- [ ] Monitoring infrastructure prepared

## Deployment Process

### Phase 1: Pre-Deployment Preparation

#### 1.1 System Health Check
```bash
# Verify current system status
python scripts/deployment/pre_deployment_check.py --comprehensive

# Check database connectivity
python -c "from app.core.database.core.database_manager import DatabaseManager; from config import Config; 
           db = DatabaseManager(Config()); 
           with db.get_session() as s: print('Database OK')"

# Verify Redis connectivity
python -c "import redis; r = redis.from_url('redis://localhost:6379'); 
           r.ping(); print('Redis OK')"
```

#### 1.2 Create System Backup
```bash
# Full system backup (recommended)
python scripts/deployment/create_deployment_backup.py --full

# Database-only backup (minimum)
python scripts/deployment/run_multi_tenant_migration.py --action verify
```

#### 1.3 Pause Active Operations
```bash
# Gracefully pause caption generation
python scripts/maintenance/pause_caption_generation.py --graceful

# Wait for active jobs to complete (optional)
python scripts/maintenance/wait_for_job_completion.py --timeout 300
```

### Phase 2: Database Migration

#### 2.1 Execute Migration
```bash
# Run migration with backup (recommended)
python scripts/deployment/run_multi_tenant_migration.py --action migrate

# Run migration without backup (not recommended)
python scripts/deployment/run_multi_tenant_migration.py --action migrate --no-backup
```

#### 2.2 Verify Migration
```bash
# Verify all tables and columns created
python scripts/deployment/run_multi_tenant_migration.py --action verify

# Test database functionality
python scripts/deployment/test_migration_functionality.py
```

### Phase 3: Service Deployment

#### 3.1 Deploy Admin Services
```bash
# Deploy admin management service
python scripts/deployment/deploy_admin_services.py --service admin_management

# Deploy monitoring services
python scripts/deployment/deploy_admin_services.py --service monitoring

# Deploy alert management
python scripts/deployment/deploy_admin_services.py --service alerts
```

#### 3.2 Update Web Application
```bash
# Deploy new admin routes and templates
python scripts/deployment/deploy_web_components.py --component admin_interface

# Update existing user interface
python scripts/deployment/deploy_web_components.py --component user_interface

# Deploy API endpoints
python scripts/deployment/deploy_web_components.py --component api_endpoints
```

### Phase 4: Configuration and Testing

#### 4.1 Initialize System Configuration
```bash
# Set up default system configuration
python scripts/deployment/initialize_system_config.py

# Configure alert thresholds
python scripts/deployment/configure_alert_system.py --defaults

# Set up performance monitoring
python scripts/deployment/configure_monitoring.py --enable-all
```

#### 4.2 Create Admin Users
```bash
# Promote existing users to admin (if needed)
python scripts/setup/promote_user_to_admin.py --username existing_user

# Create new admin user
python scripts/setup/create_admin_user.py --username admin --email admin@example.com
```

#### 4.3 Run Integration Tests
```bash
# Test admin functionality
python -m unittest tests.test_multi_tenant_comprehensive -v

# Test user interface integration
python -m unittest tests.test_admin_user_experience -v

# Test monitoring and alerts
python -m unittest tests.test_monitoring_dashboard_service -v
```

### Phase 5: Service Restart and Validation

#### 5.1 Restart Application Services
```bash
# Stop current application
ps aux | grep "python.*web_app.py" | grep -v grep
kill <process_id>

# Wait for graceful shutdown
sleep 5

# Start application with new features
python web_app.py & sleep 10
```

#### 5.2 Validate Deployment
```bash
# Run comprehensive deployment validation
python scripts/deployment/validate_deployment.py --comprehensive

# Test admin dashboard access
curl -f http://localhost:5000/admin/dashboard || echo "Admin dashboard check failed"

# Test user interface
curl -f http://localhost:5000/ || echo "User interface check failed"
```

## Feature Flags Configuration

### Environment Variables
```bash
# Feature flags for gradual rollout
MULTI_TENANT_ADMIN_ENABLED=true
ADMIN_DASHBOARD_ENABLED=true
ENHANCED_MONITORING_ENABLED=true
ALERT_SYSTEM_ENABLED=true
PERFORMANCE_METRICS_ENABLED=true

# Admin interface features
ADMIN_JOB_MANAGEMENT_ENABLED=true
ADMIN_USER_MANAGEMENT_ENABLED=true
ADMIN_SYSTEM_CONFIG_ENABLED=true

# Monitoring and alerting
REAL_TIME_MONITORING_ENABLED=true
EMAIL_ALERTS_ENABLED=false  # Configure email settings first
WEBHOOK_ALERTS_ENABLED=false  # Configure webhook URLs first
```

### Gradual Rollout Strategy
1. **Phase 1**: Enable basic admin dashboard (read-only)
2. **Phase 2**: Enable job management capabilities
3. **Phase 3**: Enable user management features
4. **Phase 4**: Enable monitoring and alerting
5. **Phase 5**: Enable all advanced features

## Post-Deployment Configuration

### Admin Dashboard Setup
```bash
# Configure dashboard widgets
python scripts/deployment/configure_admin_dashboard.py --default-widgets

# Set up real-time updates
python scripts/deployment/configure_websocket_updates.py --enable

# Configure dashboard permissions
python scripts/deployment/configure_admin_permissions.py --role-based
```

### Monitoring Configuration
```bash
# Set up performance metrics collection
python scripts/deployment/configure_performance_monitoring.py --interval 60

# Configure alert thresholds
python scripts/deployment/configure_alert_thresholds.py --load-defaults

# Set up notification channels
python scripts/deployment/configure_notification_channels.py --email --webhook
```

### Security Configuration
```bash
# Enable admin audit logging
python scripts/deployment/configure_audit_logging.py --comprehensive

# Set up admin session security
python scripts/deployment/configure_admin_security.py --enhanced

# Configure rate limiting for admin actions
python scripts/deployment/configure_admin_rate_limiting.py --strict
```

## Rollback Procedures

### Emergency Rollback
```bash
# Immediate rollback using backup
python scripts/deployment/emergency_rollback.py --backup-file <backup_file>

# Disable new features via feature flags
export MULTI_TENANT_ADMIN_ENABLED=false
export ADMIN_DASHBOARD_ENABLED=false

# Restart application
python scripts/deployment/restart_application.py --safe-mode
```

### Planned Rollback
```bash
# Graceful rollback with data preservation
python scripts/deployment/planned_rollback.py --preserve-data

# Database rollback
python scripts/deployment/run_multi_tenant_migration.py --action rollback

# Verify rollback
python scripts/deployment/verify_rollback.py --comprehensive
```

## Health Checks and Monitoring

### Automated Health Checks
```bash
# Database health
python scripts/monitoring/check_database_health.py --multi-tenant

# Admin services health
python scripts/monitoring/check_admin_services_health.py --all

# Monitoring system health
python scripts/monitoring/check_monitoring_health.py --comprehensive
```

### Performance Monitoring
```bash
# Monitor admin dashboard performance
python scripts/monitoring/monitor_admin_performance.py --continuous

# Monitor database performance impact
python scripts/monitoring/monitor_database_performance.py --admin-queries

# Monitor system resource usage
python scripts/monitoring/monitor_system_resources.py --admin-services
```

## Troubleshooting

### Common Issues

#### Migration Failures
```bash
# Check migration logs
tail -f logs/migration_*.log

# Verify database state
python scripts/deployment/verify_database_state.py --detailed

# Manual migration repair
python scripts/deployment/repair_migration.py --interactive
```

#### Admin Dashboard Issues
```bash
# Check admin service logs
tail -f logs/admin_services.log

# Verify admin permissions
python scripts/deployment/verify_admin_permissions.py --user <username>

# Reset admin dashboard
python scripts/deployment/reset_admin_dashboard.py --safe
```

#### Performance Issues
```bash
# Check system performance
python scripts/monitoring/diagnose_performance.py --admin-impact

# Optimize database queries
python scripts/deployment/optimize_admin_queries.py --analyze

# Clear performance caches
python scripts/deployment/clear_performance_caches.py --admin-only
```

## Maintenance Procedures

### Regular Maintenance
```bash
# Weekly admin system maintenance
python scripts/maintenance/admin_system_maintenance.py --weekly

# Monthly performance optimization
python scripts/maintenance/optimize_admin_performance.py --monthly

# Quarterly security audit
python scripts/maintenance/admin_security_audit.py --quarterly
```

### Data Cleanup
```bash
# Clean old audit logs
python scripts/maintenance/cleanup_audit_logs.py --older-than 90d

# Clean performance metrics
python scripts/maintenance/cleanup_performance_metrics.py --older-than 30d

# Clean system alerts
python scripts/maintenance/cleanup_system_alerts.py --resolved --older-than 7d
```

## Support and Documentation

### Administrator Training
- **Admin Dashboard Guide**: `docs/admin/dashboard_guide.md`
- **Job Management Guide**: `docs/admin/job_management_guide.md`
- **System Configuration Guide**: `docs/admin/system_config_guide.md`
- **Troubleshooting Guide**: `docs/admin/troubleshooting_guide.md`

### API Documentation
- **Admin API Reference**: `docs/api/admin_api_reference.md`
- **Monitoring API Reference**: `docs/api/monitoring_api_reference.md`
- **Configuration API Reference**: `docs/api/config_api_reference.md`

### Contact Information
- **Technical Support**: Create issue in project repository
- **Emergency Contact**: Check project documentation for emergency procedures
- **Documentation Updates**: Submit pull requests for documentation improvements