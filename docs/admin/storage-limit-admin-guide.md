# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Storage Limit Management - Administrator Guide

This comprehensive guide covers all aspects of managing storage limits in Vedfolnir, including configuration, monitoring, override systems, and maintenance procedures.

## Table of Contents

1. [Overview](#overview)
2. [Storage Limit Configuration](#storage-limit-configuration)
3. [Monitoring Storage Usage](#monitoring-storage-usage)
4. [Override System Management](#override-system-management)
5. [Alert Management](#alert-management)
6. [Maintenance Procedures](#maintenance-procedures)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)
9. [Emergency Procedures](#emergency-procedures)

## Overview

### Storage Limit System Purpose

The storage limit system protects Vedfolnir from running out of disk space by:

- **Proactive Monitoring**: Continuously tracking image storage usage
- **Automatic Protection**: Blocking caption generation when limits are reached
- **Administrator Alerts**: Notifying administrators when action is needed
- **Override Capabilities**: Allowing temporary bypasses for critical operations
- **Automatic Recovery**: Resuming normal operation when space is available

### Key Components

- **SystemConfigurationManager**: Core configuration and limit checking
- **StorageLimitService**: Business logic for storage management
- **Admin Dashboard**: Web interface for monitoring and management
- **Alert System**: Notifications and warnings for administrators
- **Override System**: Temporary bypass capabilities

### Administrator Responsibilities

- Monitor storage usage and trends
- Configure appropriate storage limits
- Respond to storage alerts promptly
- Manage override system when needed
- Perform regular storage cleanup
- Plan for storage capacity expansion

## Storage Limit Configuration

### Environment Variables

Configure storage limits through environment variables in `.env`:

```bash
# Storage Limit Configuration
STORAGE_LIMIT_ENABLED=true                    # Enable/disable storage limits
STORAGE_LIMIT_GB=100                         # Storage limit in GB
STORAGE_WARNING_THRESHOLD_PERCENT=80         # Warning threshold (80%)
STORAGE_CHECK_INTERVAL_MINUTES=15            # How often to check storage

# Override System Configuration
STORAGE_OVERRIDE_ENABLED=true                # Enable override system
STORAGE_OVERRIDE_DURATION_HOURS=2            # Default override duration
STORAGE_OVERRIDE_MAX_DURATION_HOURS=24       # Maximum override duration

# Alert Configuration
STORAGE_ALERT_EMAIL_ENABLED=true             # Enable email alerts
STORAGE_ALERT_EMAIL_RECIPIENTS=admin@example.com,ops@example.com
STORAGE_ALERT_COOLDOWN_MINUTES=60            # Minimum time between alerts
```

### Configuration Management

#### Using the Admin Web Interface (Recommended)

1. **Access Storage Configuration**:
   ```
   Navigate to: /admin/configuration
   Click: "Storage" category button in Configuration Categories
   ```

2. **Available Storage Settings**:
   - **CAPTION_MAX_STORAGE_GB** - Maximum storage limit (0.1 - 1000 GB)
   - **STORAGE_WARNING_THRESHOLD** - Warning threshold percentage (1-100%)
   - **STORAGE_MONITORING_ENABLED** - Enable/disable monitoring
   - **storage_cleanup_retention_days** - Storage event log retention (1-365 days)
   - **storage_override_max_duration_hours** - Maximum override duration (1-168 hours)
   - **storage_email_notification_enabled** - Enable email notifications
   - **storage_email_rate_limit_hours** - Email notification rate limit (1-168 hours)

3. **Making Changes**:
   - Click on any configuration to edit
   - Changes take effect immediately (no restart required)
   - Configuration history is automatically tracked
   - Rollback to previous values is available

4. **Configuration Features**:
   - Real-time validation of configuration values
   - Impact assessment for configuration changes
   - Export/import configuration sets
   - Configuration documentation and help

#### Using the Command Line

```bash
# Update storage limit
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
config_manager.update_storage_limit(150)  # Set to 150GB
print('Storage limit updated to 150GB')
"

# Configure warning threshold
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
config_manager.update_warning_threshold(75)  # Set to 75%
print('Warning threshold updated to 75%')
"

# Enable/disable storage limits
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
config_manager.toggle_storage_limits(True)  # Enable
print('Storage limits enabled')
"
```

### Configuration Validation

The system validates all configuration changes:

- **Storage Limit**: Must be positive number, reasonable size
- **Warning Threshold**: Must be between 50% and 95%
- **Check Interval**: Must be between 5 and 60 minutes
- **Override Duration**: Must be between 1 and 48 hours

## Monitoring Storage Usage

### Admin Dashboard

#### Storage Status Overview

The admin dashboard displays comprehensive storage information:

- **Current Usage**: Total storage used and percentage of limit
- **Available Space**: Remaining storage capacity
- **Usage Trend**: Historical storage usage patterns
- **Status Indicator**: Visual status (Normal, Warning, Limit Reached)
- **Last Check**: When storage was last monitored

#### Storage Metrics

Key metrics displayed in the dashboard:

```
Storage Usage: 85.2 GB / 100 GB (85.2%)
Status: ⚠️ Warning - Approaching Limit
Available Space: 14.8 GB
Files Stored: 12,847 images
Average File Size: 6.8 MB
Last Check: 2025-01-15 14:30:25
```

#### Usage Trends

- **Daily Usage**: Storage consumption over the past 30 days
- **Growth Rate**: Average daily storage growth
- **Projection**: Estimated time until limit is reached
- **Peak Usage**: Highest usage periods and patterns

### Command Line Monitoring

#### Check Current Storage Status

```bash
# Get current storage status
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
status = config_manager.get_storage_status()
print(f'Storage Usage: {status[\"used_gb\"]:.1f} GB / {status[\"limit_gb\"]} GB ({status[\"usage_percent\"]:.1f}%)')
print(f'Status: {status[\"status\"]}')
print(f'Available: {status[\"available_gb\"]:.1f} GB')
"

# Check if limits are active
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
if config_manager.is_storage_limit_reached():
    print('🚫 Storage limit reached - Caption generation blocked')
else:
    print('✅ Storage within limits - Caption generation available')
"
```

#### Storage Usage Analysis

```bash
# Analyze storage usage patterns
python scripts/admin/analyze_storage_usage.py

# Generate storage usage report
python scripts/admin/generate_storage_report.py --days 30

# Check storage growth trends
python scripts/admin/storage_trend_analysis.py
```

### Automated Monitoring

#### Health Checks

The system performs automatic health checks:

- **Storage Usage Check**: Every 15 minutes (configurable)
- **Trend Analysis**: Daily analysis of usage patterns
- **Capacity Planning**: Weekly projections of storage needs
- **Alert Generation**: Immediate alerts when thresholds are exceeded

#### Monitoring Logs

Storage monitoring activities are logged:

```bash
# View storage monitoring logs
tail -f logs/storage_monitoring.log

# Search for storage alerts
grep "STORAGE_ALERT" logs/vedfolnir.log

# Check storage check history
grep "storage_check" logs/system.log | tail -20
```

## Override System Management

### Understanding the Override System

The override system allows temporary bypassing of storage limits for critical operations:

- **Temporary Bypass**: Allows caption generation despite storage limits
- **Time-Limited**: Overrides automatically expire
- **Audit Trail**: All override activities are logged
- **Admin Control**: Only administrators can activate overrides

### Activating Storage Overrides

#### Using the Admin Interface

1. **Access Override Management**:
   ```
   Navigate to: /admin/storage-limits
   Click: "Override Management" tab
   ```

2. **Create New Override**:
   - Select override duration (1-24 hours)
   - Provide justification/reason
   - Confirm override activation
   - Monitor override status

3. **Override Confirmation**:
   ```
   Override Active
   Duration: 2 hours
   Expires: 2025-01-15 16:30:00
   Reason: Critical content processing for marketing campaign
   Status: ✅ Caption generation enabled despite storage limits
   ```

#### Using the Command Line

```bash
# Activate 2-hour override
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
override_id = config_manager.activate_storage_override(
    duration_hours=2,
    reason='Emergency content processing',
    admin_user='admin'
)
print(f'Override activated: {override_id}')
"

# Check active overrides
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
overrides = config_manager.get_active_overrides()
for override in overrides:
    print(f'Override {override[\"id\"]}: Expires {override[\"expires_at\"]}')
"
```

### Managing Active Overrides

#### Monitoring Override Status

- **Dashboard Display**: Active overrides shown prominently in admin dashboard
- **Expiration Warnings**: Alerts when overrides are about to expire
- **Usage Tracking**: Monitor storage usage during override periods
- **Impact Assessment**: Track caption generation activity during overrides

#### Extending Overrides

```bash
# Extend existing override
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
config_manager.extend_storage_override(
    override_id='override_123',
    additional_hours=2,
    reason='Processing taking longer than expected'
)
print('Override extended by 2 hours')
"
```

#### Deactivating Overrides

```bash
# Manually deactivate override
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
config_manager.deactivate_storage_override(
    override_id='override_123',
    reason='Storage space freed up'
)
print('Override deactivated')
"
```

### Override Best Practices

#### When to Use Overrides

- **Critical Content**: Time-sensitive content that must be processed
- **Emergency Situations**: Urgent caption generation needs
- **Maintenance Windows**: During planned storage cleanup operations
- **Business Requirements**: Important business deadlines

#### When NOT to Use Overrides

- **Routine Processing**: Regular, non-urgent caption generation
- **Testing**: Development or testing activities
- **Convenience**: Simply to avoid waiting for storage cleanup
- **Long-term Solutions**: Overrides are temporary fixes, not permanent solutions

#### Override Documentation

Always document override usage:

- **Reason**: Clear justification for the override
- **Duration**: Appropriate time limit for the need
- **Impact**: Expected storage usage during override
- **Follow-up**: Plans for addressing underlying storage issues

## Alert Management

### Alert Types

#### Storage Warning Alerts

Triggered when storage usage exceeds warning threshold (default 80%):

```
Subject: Storage Warning - Vedfolnir Approaching Limit
Priority: Medium

Storage usage has exceeded the warning threshold:
- Current Usage: 82.5 GB / 100 GB (82.5%)
- Available Space: 17.5 GB
- Estimated Time to Limit: 3.2 days
- Recommended Action: Plan storage cleanup or expansion
```

#### Storage Limit Alerts

Triggered when storage limit is reached:

```
Subject: URGENT: Storage Limit Reached - Caption Generation Blocked
Priority: High

Storage limit has been reached:
- Current Usage: 100.2 GB / 100 GB (100.2%)
- Status: Caption generation BLOCKED
- User Impact: All users affected
- Required Action: Immediate storage cleanup or limit increase
```

#### Override Alerts

Triggered when storage overrides are activated:

```
Subject: Storage Override Activated - Vedfolnir
Priority: Medium

Storage override has been activated:
- Override ID: override_20250115_143000
- Duration: 2 hours
- Expires: 2025-01-15 16:30:00
- Reason: Critical content processing
- Activated By: admin
```

### Alert Configuration

#### Email Alert Settings

Configure email alerts in the admin interface:

1. **Recipients**: Add administrator email addresses
2. **Alert Types**: Select which alerts to send
3. **Frequency**: Set minimum time between alerts
4. **Templates**: Customize alert message templates

#### Alert Thresholds

Customize when alerts are triggered:

- **Warning Threshold**: Percentage that triggers warnings (default 80%)
- **Critical Threshold**: Percentage that triggers urgent alerts (default 95%)
- **Cooldown Period**: Minimum time between repeat alerts (default 60 minutes)

### Managing Alert Fatigue

#### Alert Suppression

- **Cooldown Periods**: Prevent duplicate alerts within specified timeframes
- **Escalation Rules**: Send different alerts to different recipients based on severity
- **Acknowledgment System**: Allow administrators to acknowledge alerts

#### Alert Prioritization

- **High Priority**: Storage limit reached, system impact
- **Medium Priority**: Warning thresholds, override activities
- **Low Priority**: Routine monitoring, trend notifications

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Tasks

1. **Check Storage Status**: Review current usage and trends
2. **Monitor Alerts**: Respond to any storage-related alerts
3. **Review Override Usage**: Check for active or recent overrides
4. **Validate Configuration**: Ensure settings are appropriate

#### Weekly Tasks

1. **Storage Trend Analysis**: Review usage patterns and growth
2. **Capacity Planning**: Project future storage needs
3. **Cleanup Assessment**: Identify opportunities for storage cleanup
4. **Performance Review**: Assess impact of storage limits on system performance

#### Monthly Tasks

1. **Configuration Review**: Evaluate storage limit settings
2. **Alert Effectiveness**: Review alert frequency and response times
3. **Override Analysis**: Analyze override usage patterns
4. **Capacity Planning**: Plan for storage expansion if needed

### Storage Cleanup Procedures

#### Automated Cleanup

The system provides automated cleanup capabilities:

```bash
# Run automated storage cleanup
python scripts/maintenance/storage_cleanup.py --dry-run

# Execute cleanup (removes old files)
python scripts/maintenance/storage_cleanup.py --execute

# Cleanup with specific parameters
python scripts/maintenance/storage_cleanup.py \
    --older-than-days 30 \
    --min-free-space-gb 20 \
    --execute
```

#### Manual Cleanup

For more control over cleanup operations:

```bash
# Identify large files for cleanup
python scripts/admin/identify_cleanup_candidates.py

# Remove specific file categories
python scripts/admin/cleanup_by_category.py --category "failed_processing"

# Archive old images to external storage
python scripts/admin/archive_old_images.py --archive-path /backup/images
```

### Configuration Backup and Recovery

#### Backup Configuration

```bash
# Backup current storage configuration
python scripts/admin/backup_storage_config.py

# Export configuration to file
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
config = config_manager.export_storage_config()
with open('storage_config_backup.json', 'w') as f:
    import json
    json.dump(config, f, indent=2)
print('Configuration backed up to storage_config_backup.json')
"
```

#### Restore Configuration

```bash
# Restore configuration from backup
python scripts/admin/restore_storage_config.py --file storage_config_backup.json

# Import configuration
python -c "
from system_configuration_manager import SystemConfigurationManager
import json
config_manager = SystemConfigurationManager()
with open('storage_config_backup.json', 'r') as f:
    config = json.load(f)
config_manager.import_storage_config(config)
print('Configuration restored from backup')
"
```

## Troubleshooting

### Common Issues

#### Storage Limits Not Working

**Symptoms**: Caption generation continues despite reaching storage limits

**Diagnosis**:
```bash
# Check if storage limits are enabled
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
print(f'Storage limits enabled: {config_manager.is_storage_limit_enabled()}')
print(f'Current status: {config_manager.get_storage_status()}')
"
```

**Solutions**:
1. Verify `STORAGE_LIMIT_ENABLED=true` in `.env`
2. Check storage limit configuration
3. Restart the application to reload configuration
4. Verify storage monitoring service is running

#### Incorrect Storage Usage Calculations

**Symptoms**: Storage usage numbers seem incorrect or inconsistent

**Diagnosis**:
```bash
# Manual storage calculation
du -sh storage/images/
df -h /path/to/storage

# Compare with system calculation
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
status = config_manager.get_storage_status()
print(f'System calculation: {status[\"used_gb\"]} GB')
"
```

**Solutions**:
1. Clear storage cache and recalculate
2. Check for symbolic links or mounted filesystems
3. Verify storage path configuration
4. Run storage integrity check

#### Override System Not Working

**Symptoms**: Overrides don't bypass storage limits

**Diagnosis**:
```bash
# Check active overrides
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()
overrides = config_manager.get_active_overrides()
print(f'Active overrides: {len(overrides)}')
for override in overrides:
    print(f'  {override}')
"
```

**Solutions**:
1. Verify override system is enabled
2. Check override expiration times
3. Confirm override is properly activated
4. Restart application if needed

### Performance Issues

#### Slow Storage Checks

**Symptoms**: Storage monitoring causes system slowdowns

**Solutions**:
1. Increase check interval in configuration
2. Optimize storage calculation methods
3. Use cached storage values when appropriate
4. Consider asynchronous storage monitoring

#### High Memory Usage During Storage Checks

**Symptoms**: Memory usage spikes during storage monitoring

**Solutions**:
1. Implement streaming file size calculation
2. Process files in smaller batches
3. Clear file system caches after checks
4. Monitor and limit concurrent storage operations

### Alert Issues

#### Missing Storage Alerts

**Symptoms**: No alerts received when storage limits are reached

**Diagnosis**:
```bash
# Check alert configuration
grep -E "(ALERT|EMAIL)" .env

# Test alert system
python scripts/admin/test_storage_alerts.py
```

**Solutions**:
1. Verify email configuration
2. Check spam/junk folders
3. Test SMTP connectivity
4. Review alert cooldown settings

#### Too Many Alerts

**Symptoms**: Excessive storage alert emails

**Solutions**:
1. Increase alert cooldown period
2. Adjust warning thresholds
3. Implement alert acknowledgment system
4. Review alert escalation rules

## Best Practices

### Configuration Management

#### Setting Appropriate Limits

- **Conservative Approach**: Set limits with 20-30% buffer for system operations
- **Growth Planning**: Consider historical growth rates when setting limits
- **Regular Review**: Adjust limits based on actual usage patterns
- **Documentation**: Document rationale for limit settings

#### Monitoring Configuration

- **Appropriate Intervals**: Balance monitoring frequency with system performance
- **Threshold Settings**: Set warning thresholds early enough for proactive response
- **Alert Recipients**: Ensure appropriate administrators receive alerts
- **Escalation Procedures**: Define clear escalation paths for storage issues

### Operational Procedures

#### Proactive Management

- **Trend Monitoring**: Watch for unusual growth patterns
- **Capacity Planning**: Plan storage expansion before limits are reached
- **Regular Cleanup**: Schedule routine storage cleanup operations
- **Performance Monitoring**: Track impact of storage limits on system performance

#### Incident Response

- **Response Procedures**: Define clear procedures for storage limit incidents
- **Communication Plans**: Keep users informed during storage issues
- **Recovery Procedures**: Document steps for quick recovery
- **Post-Incident Review**: Analyze incidents to improve procedures

### Security Considerations

#### Access Control

- **Admin-Only Access**: Restrict storage management to administrators
- **Audit Logging**: Log all storage configuration changes
- **Override Controls**: Implement approval processes for overrides
- **Configuration Protection**: Secure storage configuration files

#### Data Protection

- **Backup Procedures**: Regular backups of storage configuration
- **Recovery Planning**: Procedures for configuration recovery
- **Change Management**: Controlled process for configuration changes
- **Validation**: Verify configuration changes before implementation

## Emergency Procedures

### Critical Storage Situations

#### Immediate Actions for Storage Emergencies

1. **Assess Situation**:
   - Determine severity and impact
   - Check available disk space
   - Identify immediate risks

2. **Activate Override** (if appropriate):
   ```bash
   # Emergency override activation
   python -c "
   from system_configuration_manager import SystemConfigurationManager
   config_manager = SystemConfigurationManager()
   override_id = config_manager.activate_storage_override(
       duration_hours=4,
       reason='EMERGENCY: Critical storage situation',
       admin_user='emergency_admin'
   )
   print(f'Emergency override activated: {override_id}')
   "
   ```

3. **Free Up Space**:
   - Run emergency cleanup procedures
   - Archive or move non-critical files
   - Identify and remove unnecessary data

4. **Communicate**:
   - Notify users of the situation
   - Provide estimated resolution time
   - Keep stakeholders informed

#### Emergency Cleanup Procedures

```bash
# Emergency storage cleanup
python scripts/emergency/emergency_storage_cleanup.py

# Remove temporary files
find storage/temp/ -type f -mtime +1 -delete

# Archive old processed images
python scripts/emergency/archive_old_images.py --emergency

# Clear processing caches
python scripts/emergency/clear_processing_caches.py
```

### Recovery Procedures

#### Post-Emergency Recovery

1. **Verify System Stability**:
   - Check storage usage levels
   - Verify caption generation is working
   - Monitor system performance

2. **Deactivate Emergency Overrides**:
   ```bash
   # Deactivate emergency overrides
   python -c "
   from system_configuration_manager import SystemConfigurationManager
   config_manager = SystemConfigurationManager()
   overrides = config_manager.get_active_overrides()
   for override in overrides:
       if 'EMERGENCY' in override['reason']:
           config_manager.deactivate_storage_override(
               override_id=override['id'],
               reason='Emergency resolved'
           )
   print('Emergency overrides deactivated')
   "
   ```

3. **Review and Adjust**:
   - Analyze what caused the emergency
   - Adjust storage limits if necessary
   - Update procedures based on lessons learned

4. **Document Incident**:
   - Record timeline of events
   - Document actions taken
   - Identify improvements for future incidents

### Contact Information

#### Emergency Contacts

- **Primary Administrator**: [Contact Information]
- **Secondary Administrator**: [Contact Information]
- **System Operations**: [Contact Information]
- **Infrastructure Team**: [Contact Information]

#### Escalation Procedures

1. **Level 1**: Primary administrator response (within 1 hour)
2. **Level 2**: Secondary administrator involvement (within 2 hours)
3. **Level 3**: System operations escalation (within 4 hours)
4. **Level 4**: Infrastructure team involvement (critical situations)

This comprehensive guide provides administrators with all the tools and knowledge needed to effectively manage storage limits in Vedfolnir. Regular review and practice of these procedures will ensure smooth operation and quick resolution of storage-related issues.