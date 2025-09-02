# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Storage Configuration Guide

## Overview

Vedfolnir includes a comprehensive storage limit management system that automatically monitors image storage usage and prevents storage overflow. This guide covers all available storage configuration options and their usage.

## Configuration Variables

### Core Storage Settings

#### `CAPTION_MAX_STORAGE_GB`
- **Description**: Maximum storage limit for image files in gigabytes
- **Type**: Float
- **Default**: 10.0
- **Range**: 0.1 - 1000.0
- **Example**: `CAPTION_MAX_STORAGE_GB=25.5`
- **Required**: Yes

Sets the maximum amount of storage space that can be used for storing images. When this limit is reached, caption generation will be automatically blocked until storage usage drops below the limit.

#### `STORAGE_WARNING_THRESHOLD`
- **Description**: Warning threshold as a percentage of the maximum storage limit
- **Type**: Float
- **Default**: 80.0
- **Range**: 1.0 - 100.0
- **Example**: `STORAGE_WARNING_THRESHOLD=85.0`
- **Required**: No

When storage usage exceeds this percentage of the maximum limit, warning notifications will be sent to administrators and warning indicators will be displayed in the admin dashboard.

#### `STORAGE_MONITORING_ENABLED`
- **Description**: Enable or disable storage monitoring
- **Type**: Boolean
- **Default**: true
- **Values**: true, false
- **Example**: `STORAGE_MONITORING_ENABLED=true`
- **Required**: No

Controls whether the storage monitoring system is active. When disabled, storage limits will not be enforced and no monitoring will occur.

### Advanced Storage Settings

#### `STORAGE_BASE_DIR`
- **Description**: Base directory for all storage operations
- **Type**: String
- **Default**: storage
- **Example**: `STORAGE_BASE_DIR=/var/lib/vedfolnir/storage`
- **Required**: No

Sets the root directory where all application data is stored.

#### `STORAGE_IMAGES_DIR`
- **Description**: Directory for storing downloaded images
- **Type**: String
- **Default**: storage/images
- **Example**: `STORAGE_IMAGES_DIR=/var/lib/vedfolnir/storage/images`
- **Required**: No

Specifies the directory where image files are stored. This is the directory that is monitored for storage usage calculations.

## Configuration Examples

### Development Environment
```bash
# Development storage configuration
CAPTION_MAX_STORAGE_GB=5.0
STORAGE_WARNING_THRESHOLD=75.0
STORAGE_MONITORING_ENABLED=true
STORAGE_BASE_DIR=storage/dev
STORAGE_IMAGES_DIR=storage/dev/images
```

### Production Environment
```bash
# Production storage configuration
CAPTION_MAX_STORAGE_GB=100.0
STORAGE_WARNING_THRESHOLD=85.0
STORAGE_MONITORING_ENABLED=true
STORAGE_BASE_DIR=/var/lib/vedfolnir/storage
STORAGE_IMAGES_DIR=/var/lib/vedfolnir/storage/images
```

### High-Volume Environment
```bash
# High-volume storage configuration
CAPTION_MAX_STORAGE_GB=500.0
STORAGE_WARNING_THRESHOLD=90.0
STORAGE_MONITORING_ENABLED=true
STORAGE_BASE_DIR=/mnt/storage/vedfolnir
STORAGE_IMAGES_DIR=/mnt/storage/vedfolnir/images
```

## Storage Monitoring Behavior

### Normal Operation
- Storage usage is calculated every time caption generation is requested
- Results are cached for 5 minutes to avoid excessive I/O operations
- Usage statistics are displayed in the admin dashboard

### Warning Threshold Exceeded
- Warning notifications are sent to administrators (rate-limited to once per 24 hours)
- Admin dashboard displays warning indicators
- Caption generation continues normally
- Warning events are logged for audit purposes

### Storage Limit Exceeded
- Caption generation is automatically blocked
- Users see a friendly notification explaining the temporary unavailability
- Email notifications are sent to administrators with cleanup links
- Blocking is automatically lifted when storage drops below the limit
- All limit events are logged for audit purposes

## Admin Dashboard Integration

The storage configuration affects several admin dashboard features:

### Storage Status Display
- Current usage vs. limit
- Usage percentage with color coding:
  - Green: < warning threshold
  - Yellow: >= warning threshold, < limit
  - Red: >= limit
- Storage trend graphs and statistics

### Storage Management Tools
- Manual override system for emergency situations
- Direct links to cleanup tools when limits are reached
- Real-time storage recalculation after cleanup operations

## Manual Override System

Administrators can temporarily override storage limits:

### Override Configuration
- Default override duration: 1 hour
- Maximum override duration: 24 hours
- All overrides are logged for audit purposes
- Overrides automatically expire and can be manually deactivated

### Override Usage
1. Access admin dashboard
2. Navigate to storage management section
3. Click "Override Storage Limit"
4. Specify duration and reason
5. Confirm override activation

## Email Notifications

### Storage Limit Reached
- **Recipients**: All administrators
- **Rate Limiting**: Once per 24 hours
- **Content**: Current usage, limit, cleanup links
- **Trigger**: When storage usage reaches or exceeds the limit

### Warning Threshold Exceeded
- **Recipients**: All administrators
- **Rate Limiting**: Once per 24 hours
- **Content**: Current usage, warning threshold, trend information
- **Trigger**: When storage usage exceeds the warning threshold

## Cleanup Integration

The storage system integrates with existing cleanup tools:

### Automatic Integration
- Storage limits are displayed on cleanup pages
- Real-time storage recalculation after cleanup operations
- Automatic limit lifting when cleanup frees sufficient space

### Cleanup Recommendations
- Email notifications include direct links to cleanup tools
- Admin dashboard shows cleanup suggestions when approaching limits
- Storage event logs track cleanup effectiveness

## Troubleshooting

### Common Issues

#### Storage Limit Not Enforced
- Check `STORAGE_MONITORING_ENABLED=true`
- Verify `CAPTION_MAX_STORAGE_GB` is set and positive
- Check application logs for configuration errors

#### Incorrect Storage Calculations
- Verify `STORAGE_IMAGES_DIR` points to the correct directory
- Check directory permissions for read access
- Review logs for I/O errors during storage calculation

#### Email Notifications Not Sent
- Verify email configuration is correct
- Check rate limiting (notifications sent once per 24 hours)
- Review email service logs for delivery issues

#### Admin Dashboard Not Showing Storage Info
- Ensure user has admin role
- Check that storage services are properly initialized
- Verify database connectivity for storage statistics

### Configuration Validation

Use the built-in validation tools to check your configuration:

```bash
# Validate all configuration including storage settings
python validate_config.py

# Verify environment setup including storage configuration
python scripts/setup/verify_env_setup.py
```

### Log Analysis

Storage-related events are logged with specific prefixes:

```bash
# View storage-related logs
grep "Storage" logs/webapp.log
grep "storage_" logs/webapp.log

# View storage limit events
grep "limit_reached\|limit_lifted" logs/webapp.log

# View storage override events
grep "override_activated\|override_deactivated" logs/webapp.log
```

## Security Considerations

### Access Control
- Only administrators can view storage statistics
- Only administrators can activate storage overrides
- All administrative actions are logged for audit purposes

### Data Protection
- Storage calculations do not expose file contents
- Storage statistics are aggregated and anonymized
- Audit logs protect against unauthorized configuration changes

### Rate Limiting
- Email notifications are rate-limited to prevent spam
- Storage calculations are cached to prevent excessive I/O
- Override activations are logged and time-limited

## Performance Impact

### Storage Calculation Performance
- Calculations are cached for 5 minutes
- Directory scanning is optimized for large file sets
- Background processing minimizes impact on user requests

### Database Impact
- Storage events are logged to database for audit purposes
- Cleanup processes remove old audit records automatically
- Indexes optimize storage-related queries

### Memory Usage
- Storage calculations use streaming for large directories
- Metric caching reduces memory overhead
- Cleanup processes manage memory usage effectively

## Migration and Upgrades

### Upgrading from Previous Versions
- Storage configuration is backward compatible
- Default values are used for missing configuration
- Existing storage data is preserved during upgrades

### Configuration Migration
- Use environment setup scripts to generate new configuration
- Validate configuration after migration
- Test storage monitoring functionality after upgrade

## Best Practices

### Configuration
- Set storage limits based on available disk space
- Use warning thresholds between 75-85% for optimal balance
- Enable monitoring in all environments except development

### Monitoring
- Regularly review storage usage trends
- Set up external monitoring for storage alerts
- Monitor cleanup effectiveness and adjust limits as needed

### Maintenance
- Regularly clean up old images to maintain optimal performance
- Review and adjust storage limits based on usage patterns
- Test override functionality periodically to ensure it works

### Security
- Restrict admin access to storage configuration
- Regularly review storage audit logs
- Monitor for unusual storage usage patterns

## API Integration

### Admin API Endpoints
- `GET /admin/api/storage/status` - Get current storage status
- `POST /admin/api/storage/override` - Activate storage override
- `DELETE /admin/api/storage/override` - Deactivate storage override
- `GET /admin/api/storage/statistics` - Get storage usage statistics

### Configuration API
- Storage settings can be managed through the admin configuration API
- Changes are validated and logged automatically
- Real-time updates to storage monitoring system

## Related Documentation

- [Admin Dashboard Guide](admin-dashboard-guide.md)
- [Cleanup Tools Documentation](cleanup-tools.md)
- [Email Configuration Guide](email-configuration.md)
- [Security Configuration](../security/security-configuration.md)
- [Troubleshooting Guide](troubleshooting.md)