# Enhanced Maintenance Mode - Administrator Guide

## Overview

This guide provides comprehensive instructions for system administrators on configuring, managing, and monitoring the Enhanced Maintenance Mode system. It covers all aspects of maintenance mode operations from initial setup to emergency procedures.

## System Architecture

### Core Components

1. **EnhancedMaintenanceModeService**: Central service managing all maintenance operations
2. **MaintenanceModeMiddleware**: Automatic request interception and blocking
3. **MaintenanceOperationClassifier**: Granular operation categorization and blocking rules
4. **MaintenanceSessionManager**: User session management during maintenance
5. **MaintenanceStatusAPI**: Real-time status information for frontend applications
6. **EmergencyMaintenanceHandler**: Emergency maintenance scenarios and immediate protection

### Integration Points

- **Configuration Service**: Maintenance settings and state persistence
- **Redis Session Manager**: Session invalidation and user management
- **Flask Application**: Middleware integration and route protection
- **Admin Interface**: Web-based maintenance controls and monitoring
- **Logging System**: Comprehensive audit trails and monitoring

## Configuration

### Environment Variables

```bash
# Maintenance Mode Configuration
MAINTENANCE_MODE_ENABLED=true
MAINTENANCE_DEFAULT_TIMEOUT=7200  # 2 hours default
MAINTENANCE_CLEANUP_INTERVAL=300  # 5 minutes

# Emergency Mode Settings
EMERGENCY_MODE_JOB_GRACE_PERIOD=30  # 30 seconds
EMERGENCY_MODE_SESSION_CLEANUP=true

# Test Mode Configuration
TEST_MODE_SIMULATION=true
TEST_MODE_LOGGING_LEVEL=DEBUG

# Notification Settings
MAINTENANCE_NOTIFICATIONS_ENABLED=true
MAINTENANCE_EMAIL_ALERTS=true
MAINTENANCE_WEBHOOK_URL=https://your-webhook-endpoint.com
```

### Database Configuration

The maintenance mode system uses the existing configuration service for state persistence:

```sql
-- Configuration entries for maintenance mode
INSERT INTO configuration (key, value, description) VALUES
('maintenance_mode', 'false', 'Current maintenance mode status'),
('maintenance_reason', '', 'Current maintenance reason'),
('maintenance_duration', '0', 'Estimated maintenance duration in seconds'),
('maintenance_started_at', '', 'Maintenance start timestamp'),
('maintenance_mode_type', 'normal', 'Maintenance mode type: normal, emergency, test');
```

## Admin Interface Usage

### Accessing Maintenance Controls

1. **Login**: Access the admin interface with administrator credentials
2. **Navigate**: Go to Admin Dashboard → System Maintenance
3. **Status**: View current maintenance status and system health
4. **Controls**: Use maintenance mode controls for activation/deactivation

### Maintenance Mode Activation

#### Normal Maintenance Mode

1. **Access Control Panel**: Navigate to the maintenance mode section
2. **Set Parameters**:
   - **Reason**: Provide clear explanation for maintenance
   - **Duration**: Estimate maintenance duration (optional)
   - **Notification**: Choose whether to notify users
3. **Confirm Activation**: Review settings and confirm activation
4. **Monitor Status**: Watch real-time status updates and user impact

#### Emergency Maintenance Mode

1. **Emergency Access**: Use emergency maintenance button (red button)
2. **Immediate Activation**: Emergency mode activates immediately
3. **Reason Required**: Provide emergency reason for audit trail
4. **Monitor Impact**: Track session cleanup and job termination
5. **Recovery Planning**: Plan recovery procedures while in emergency mode

#### Test Maintenance Mode

1. **Test Mode Selection**: Choose test mode from dropdown
2. **Simulation Settings**: Configure test parameters
3. **Validation**: Run through maintenance procedures without impact
4. **Report Generation**: Review test results and validation reports
5. **Documentation**: Document test results for future reference

### Monitoring and Status

#### Real-Time Dashboard

The admin dashboard provides:

- **Current Status**: Active maintenance mode and type
- **Affected Operations**: List of currently blocked operations
- **User Impact**: Number of affected users and sessions
- **System Health**: Overall system status during maintenance
- **Progress Tracking**: Maintenance progress and estimated completion

#### Status Metrics

Key metrics to monitor:

- **Blocked Operation Attempts**: Number of blocked requests per minute
- **Active Sessions**: Current user sessions and admin sessions
- **Running Jobs**: Background jobs still completing
- **System Performance**: Response times and resource usage
- **Error Rates**: Any errors or issues during maintenance

### Session Management

#### User Session Handling

During maintenance activation:

1. **Session Invalidation**: Non-admin sessions are automatically invalidated
2. **Login Prevention**: Non-admin users cannot log in during maintenance
3. **Admin Preservation**: Administrator sessions remain active
4. **Graceful Notification**: Users receive maintenance notifications

#### Session Recovery

After maintenance completion:

1. **Login Restoration**: Users can log in normally
2. **Session Cleanup**: Expired maintenance sessions are cleaned up
3. **State Recovery**: User preferences and settings are preserved
4. **Platform Connections**: Platform connections remain intact

## Operation Classification and Blocking

### Default Operation Types

The system classifies operations into these categories:

#### CAPTION_GENERATION
- **Endpoints**: `/start_caption_generation`, `/api/caption/*`
- **Blocking**: Blocked in normal and emergency modes
- **Reason**: Prevents resource-intensive AI operations during maintenance

#### JOB_CREATION
- **Endpoints**: `/api/jobs/*`, job-related routes
- **Blocking**: Blocked in normal and emergency modes
- **Reason**: Prevents new background processing during maintenance

#### PLATFORM_OPERATIONS
- **Endpoints**: `/switch_platform`, `/test_connection`, platform management
- **Blocking**: Blocked in normal and emergency modes
- **Reason**: Prevents external API calls during maintenance

#### BATCH_OPERATIONS
- **Endpoints**: `/batch/*`, bulk processing routes
- **Blocking**: Blocked in normal and emergency modes
- **Reason**: Prevents large-scale operations during maintenance

#### USER_DATA_MODIFICATION
- **Endpoints**: Profile updates, settings changes, password changes
- **Blocking**: Blocked in normal and emergency modes
- **Reason**: Protects data integrity during maintenance

#### IMAGE_PROCESSING
- **Endpoints**: Image upload, optimization, analysis
- **Blocking**: Blocked in normal and emergency modes
- **Reason**: Prevents resource-intensive processing during maintenance

#### ADMIN_OPERATIONS
- **Endpoints**: Admin routes and functions
- **Blocking**: Never blocked (admin bypass)
- **Reason**: Administrators need access to manage maintenance

#### READ_OPERATIONS
- **Endpoints**: View routes, status pages, documentation
- **Blocking**: Allowed in normal mode, blocked in emergency mode
- **Reason**: Users can still browse content during normal maintenance

### Custom Operation Rules

You can add custom operation classifications:

```python
# Add custom classification rule
classifier = MaintenanceOperationClassifier()
classifier.add_custom_classification(
    pattern=r'/api/custom/.*',
    operation_type=OperationType.CUSTOM_OPERATION
)
```

## Emergency Procedures

### Emergency Maintenance Activation

#### When to Use Emergency Mode

Activate emergency maintenance for:

- **Security Incidents**: Active security threats or breaches
- **Data Corruption**: Risk of data loss or corruption
- **System Instability**: Critical system failures or instability
- **External Threats**: DDoS attacks or other external threats
- **Compliance Issues**: Regulatory compliance requirements

#### Emergency Activation Steps

1. **Immediate Access**: Click emergency maintenance button in admin interface
2. **Reason Documentation**: Provide detailed emergency reason
3. **Stakeholder Notification**: Notify relevant stakeholders immediately
4. **System Assessment**: Assess system status and impact
5. **Recovery Planning**: Develop recovery plan while in emergency mode

#### Emergency Mode Behavior

- **Immediate Blocking**: All non-admin operations blocked instantly
- **Job Termination**: Running jobs terminated with grace period
- **Session Cleanup**: All non-admin sessions invalidated immediately
- **Critical Access Only**: Only essential admin functions available
- **Enhanced Logging**: All actions logged with emergency context

### Recovery Procedures

#### Normal Recovery

1. **Issue Resolution**: Complete maintenance tasks
2. **System Validation**: Verify system stability and functionality
3. **Gradual Restoration**: Disable maintenance mode
4. **User Notification**: Inform users that services have resumed
5. **Post-Maintenance Monitoring**: Monitor system for any issues

#### Emergency Recovery

1. **Threat Assessment**: Ensure emergency situation is resolved
2. **Security Validation**: Verify system security and integrity
3. **Data Verification**: Check data consistency and integrity
4. **Staged Recovery**: Consider staged recovery for critical systems
5. **Incident Documentation**: Document emergency and recovery actions

### Rollback Procedures

If issues occur during maintenance:

1. **Immediate Assessment**: Evaluate the severity of issues
2. **Rollback Decision**: Decide whether to rollback or continue
3. **System Restoration**: Restore system to pre-maintenance state
4. **User Communication**: Inform users of rollback and status
5. **Issue Investigation**: Investigate and document issues for future prevention

## Monitoring and Alerting

### Health Checks

The system provides comprehensive health monitoring:

```bash
# Check maintenance mode status
curl http://localhost:5000/api/maintenance/status

# Check system health during maintenance
curl http://localhost:5000/api/health/maintenance

# Monitor blocked operations
curl http://localhost:5000/api/maintenance/blocked-operations
```

### Alerting Configuration

Set up alerts for:

- **Maintenance Activation**: Alert when maintenance mode is enabled
- **Emergency Mode**: Immediate alerts for emergency maintenance
- **High Block Rates**: Alert when many operations are being blocked
- **System Issues**: Alert for any system problems during maintenance
- **Recovery Completion**: Notification when maintenance is complete

### Log Monitoring

Key log entries to monitor:

```
[MAINTENANCE] Maintenance mode activated: reason="Database optimization"
[MAINTENANCE] Operation blocked: endpoint="/start_caption_generation" user="user123"
[MAINTENANCE] Emergency mode activated: reason="Security incident" admin="admin"
[MAINTENANCE] Session invalidated: user="user456" reason="maintenance_activation"
[MAINTENANCE] Maintenance mode deactivated: duration="45 minutes"
```

## Troubleshooting

### Common Issues

#### Maintenance Mode Won't Activate

**Symptoms**: Maintenance mode activation fails or doesn't take effect

**Possible Causes**:
- Configuration service unavailable
- Database connection issues
- Permission problems
- Middleware not properly registered

**Solutions**:
1. Check configuration service status
2. Verify database connectivity
3. Confirm admin user permissions
4. Restart application if necessary

#### Users Still Accessing Blocked Operations

**Symptoms**: Users can access operations that should be blocked

**Possible Causes**:
- Middleware not intercepting requests
- Operation classification issues
- Caching problems
- Admin bypass incorrectly applied

**Solutions**:
1. Verify middleware registration
2. Check operation classification rules
3. Clear application caches
4. Review admin user detection logic

#### Session Invalidation Not Working

**Symptoms**: Non-admin users retain access during maintenance

**Possible Causes**:
- Redis session manager issues
- Session cleanup failures
- User role detection problems
- Session middleware problems

**Solutions**:
1. Check Redis connectivity
2. Verify session manager configuration
3. Review user role assignments
4. Restart session services

#### Emergency Mode Issues

**Symptoms**: Emergency mode doesn't activate or doesn't block operations

**Possible Causes**:
- Emergency handler not initialized
- Job termination failures
- Session cleanup issues
- Critical admin access problems

**Solutions**:
1. Verify emergency handler setup
2. Check job termination logic
3. Review session cleanup procedures
4. Ensure admin access preservation

### Diagnostic Commands

```bash
# Check maintenance mode configuration
python -c "
from config import Config
from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService
config = Config()
service = EnhancedMaintenanceModeService(config)
print(f'Maintenance Status: {service.get_maintenance_status()}')
"

# Verify middleware registration
python -c "
from web_app import app
print('Registered middleware:')
for middleware in app.before_request_funcs[None]:
    print(f'  - {middleware.__name__}')
"

# Check session manager status
python -c "
from redis_session_manager import RedisSessionManager
from config import Config
config = Config()
manager = RedisSessionManager(config)
print(f'Session Manager Health: {manager.health_check()}')
"
```

## Best Practices

### Planning Maintenance

1. **Advance Notice**: Provide users with advance notice when possible
2. **Off-Peak Hours**: Schedule maintenance during low-usage periods
3. **Duration Estimation**: Provide realistic time estimates
4. **Rollback Planning**: Always have a rollback plan ready
5. **Communication**: Keep users informed throughout the process

### During Maintenance

1. **Monitor Continuously**: Watch system status and user impact
2. **Document Actions**: Log all maintenance actions and decisions
3. **Stay Available**: Ensure administrators are available for issues
4. **Communicate Updates**: Provide regular status updates
5. **Be Prepared**: Have emergency procedures ready if needed

### After Maintenance

1. **Verify Functionality**: Test all systems thoroughly
2. **Monitor Performance**: Watch for any performance issues
3. **User Feedback**: Collect and address user feedback
4. **Document Lessons**: Record lessons learned for future maintenance
5. **Update Procedures**: Improve procedures based on experience

## Security Considerations

### Access Control

- **Admin-Only Activation**: Only administrators can enable maintenance mode
- **Emergency Authentication**: Additional verification for emergency mode
- **Audit Logging**: Complete audit trail of all maintenance actions
- **Session Security**: Secure session handling during maintenance transitions

### Data Protection

- **Session Data Security**: Secure cleanup of invalidated sessions
- **Configuration Encryption**: Encrypt sensitive maintenance configuration
- **Audit Trail Integrity**: Protect maintenance logs from tampering
- **Recovery Security**: Secure recovery procedures and access

## API Reference

### Maintenance Status API

#### GET /api/maintenance/status
Returns current maintenance status information.

**Response**:
```json
{
  "is_active": boolean,
  "mode": "normal|emergency|test",
  "reason": string,
  "estimated_duration": number,
  "started_at": string,
  "estimated_completion": string,
  "blocked_operations": [string],
  "active_jobs_count": number,
  "message": string
}
```

#### GET /api/maintenance/blocked-operations
Returns list of currently blocked operations.

**Response**:
```json
{
  "blocked_operations": [
    {
      "operation_type": string,
      "description": string,
      "blocked_since": string,
      "attempt_count": number
    }
  ]
}
```

#### POST /api/maintenance/enable
Enables maintenance mode (admin only).

**Request**:
```json
{
  "reason": string,
  "duration": number,
  "mode": "normal|emergency|test"
}
```

#### POST /api/maintenance/disable
Disables maintenance mode (admin only).

## Conclusion

The Enhanced Maintenance Mode system provides comprehensive protection and management capabilities for system maintenance operations. By following this guide, administrators can effectively manage maintenance procedures while minimizing user impact and ensuring system integrity.

For additional support or advanced configuration needs, refer to the troubleshooting guide or contact the development team.