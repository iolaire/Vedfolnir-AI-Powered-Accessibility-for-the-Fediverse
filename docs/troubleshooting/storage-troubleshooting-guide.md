# Storage-Related Troubleshooting Guide

This guide provides comprehensive troubleshooting procedures for storage-related issues in Vedfolnir, including diagnosis, resolution, and prevention strategies.

## Table of Contents

1. [Common Storage Issues](#common-storage-issues)
2. [Diagnostic Procedures](#diagnostic-procedures)
3. [Storage Limit Issues](#storage-limit-issues)
4. [Storage Performance Problems](#storage-performance-problems)
5. [File System Issues](#file-system-issues)
6. [Configuration Problems](#configuration-problems)
7. [Emergency Procedures](#emergency-procedures)
8. [Prevention and Monitoring](#prevention-and-monitoring)

## Common Storage Issues

### Issue Categories

Storage-related problems in Vedfolnir typically fall into these categories:

1. **Storage Limit Issues**: Problems with storage limit detection and enforcement
2. **Performance Issues**: Slow storage operations or high I/O usage
3. **File System Issues**: Corrupted files, permission problems, or disk errors
4. **Configuration Issues**: Incorrect storage settings or paths
5. **Capacity Issues**: Running out of disk space or approaching limits

### Quick Diagnosis Checklist

Before diving into specific troubleshooting, run this quick diagnostic:

```bash
# Quick storage health check
python scripts/admin/quick_storage_diagnosis.py

# Check basic storage metrics
df -h /path/to/storage
du -sh storage/images/
ls -la storage/

# Verify storage configuration
python -c "
from system_configuration_manager import SystemConfigurationManager
config = SystemConfigurationManager()
print(f'Storage limit enabled: {config.is_storage_limit_enabled()}')
print(f'Current usage: {config.get_storage_status()}')
"
```

## Diagnostic Procedures

### Comprehensive Storage Diagnosis

#### System-Level Diagnostics

```bash
# Check disk space and usage
df -h
df -i  # Check inode usage

# Check disk health
sudo smartctl -a /dev/sda  # Replace with your disk

# Check file system errors
sudo fsck -n /dev/sda1  # Replace with your partition

# Monitor disk I/O
iostat -x 1 5
iotop -o  # Show only processes doing I/O
```

#### Application-Level Diagnostics

```bash
# Check Vedfolnir storage status
python scripts/admin/comprehensive_storage_diagnosis.py

# Verify storage paths
python -c "
import os
from config import Config
config = Config()
storage_path = config.get_storage_path()
print(f'Storage path: {storage_path}')
print(f'Path exists: {os.path.exists(storage_path)}')
print(f'Path writable: {os.access(storage_path, os.W_OK)}')
"

# Check storage permissions
ls -la storage/
find storage/ -type d -exec ls -ld {} \; | head -10
```

#### Database Diagnostics

```bash
# Check storage-related database records
mysql -u vedfolnir -p vedfolnir -e "
SELECT 
    COUNT(*) as total_images,
    SUM(CASE WHEN local_path IS NOT NULL THEN 1 ELSE 0 END) as images_with_files,
    SUM(CASE WHEN local_path IS NULL THEN 1 ELSE 0 END) as images_without_files
FROM images;
"

# Check for orphaned records
python scripts/admin/check_orphaned_storage_records.py

# Verify storage consistency
python scripts/admin/verify_storage_database_consistency.py
```

### Log Analysis

#### Storage-Related Logs

```bash
# Check storage monitoring logs
tail -f logs/storage_monitoring.log

# Look for storage errors
grep -i "storage\|disk\|space" logs/vedfolnir.log | tail -20

# Check cleanup logs
grep -i "cleanup" logs/vedfolnir.log | tail -10

# Monitor real-time storage operations
tail -f logs/vedfolnir.log | grep -i storage
```

#### Error Pattern Analysis

```bash
# Analyze storage error patterns
python scripts/admin/analyze_storage_errors.py --days 7

# Generate storage error report
python scripts/admin/storage_error_report.py --detailed
```

## Storage Limit Issues

### Storage Limits Not Working

#### Symptoms
- Caption generation continues despite reaching storage limits
- No storage limit notifications displayed
- Storage usage exceeds configured limits

#### Diagnosis

```bash
# Check if storage limits are enabled
python -c "
from system_configuration_manager import SystemConfigurationManager
config = SystemConfigurationManager()
print(f'Storage limits enabled: {config.is_storage_limit_enabled()}')
print(f'Storage limit: {config.get_storage_limit_gb()} GB')
print(f'Current usage: {config.get_storage_status()}')
"

# Verify environment configuration
grep -E "STORAGE_LIMIT" .env

# Check storage limit service status
python scripts/admin/check_storage_limit_service.py
```

#### Solutions

1. **Enable Storage Limits**:
   ```bash
   # Update .env file
   echo "STORAGE_LIMIT_ENABLED=true" >> .env
   
   # Restart application
   pkill -f "python web_app.py"
   python web_app.py & sleep 10
   ```

2. **Fix Configuration**:
   ```bash
   # Reset storage configuration
   python -c "
   from system_configuration_manager import SystemConfigurationManager
   config = SystemConfigurationManager()
   config.reset_storage_config()
   config.update_storage_limit(100)  # Set 100GB limit
   print('Storage configuration reset')
   "
   ```

3. **Restart Storage Monitoring**:
   ```bash
   # Restart storage monitoring service
   python scripts/admin/restart_storage_monitoring.py
   ```

### Incorrect Storage Usage Calculations

#### Symptoms
- Storage usage numbers don't match actual disk usage
- Inconsistent storage reporting
- Storage limits triggered incorrectly

#### Diagnosis

```bash
# Compare system calculation with actual usage
du -sh storage/images/
python -c "
from system_configuration_manager import SystemConfigurationManager
config = SystemConfigurationManager()
status = config.get_storage_status()
print(f'System reports: {status[\"used_gb\"]} GB')
"

# Check for calculation errors
python scripts/admin/verify_storage_calculations.py

# Look for symbolic links or mounted filesystems
find storage/ -type l
mount | grep storage
```

#### Solutions

1. **Recalculate Storage Usage**:
   ```bash
   # Force storage recalculation
   python -c "
   from system_configuration_manager import SystemConfigurationManager
   config = SystemConfigurationManager()
   config.recalculate_storage_usage()
   print('Storage usage recalculated')
   "
   ```

2. **Fix Path Configuration**:
   ```bash
   # Verify and fix storage paths
   python scripts/admin/fix_storage_paths.py
   ```

3. **Clear Storage Cache**:
   ```bash
   # Clear cached storage calculations
   python scripts/admin/clear_storage_cache.py
   ```

### Storage Override Issues

#### Symptoms
- Storage overrides don't bypass limits
- Override system not responding
- Overrides expire unexpectedly

#### Diagnosis

```bash
# Check active overrides
python -c "
from system_configuration_manager import SystemConfigurationManager
config = SystemConfigurationManager()
overrides = config.get_active_overrides()
print(f'Active overrides: {len(overrides)}')
for override in overrides:
    print(f'  Override {override[\"id\"]}: expires {override[\"expires_at\"]}')
"

# Verify override system configuration
grep -E "OVERRIDE" .env

# Check override logs
grep -i "override" logs/vedfolnir.log | tail -10
```

#### Solutions

1. **Enable Override System**:
   ```bash
   # Enable overrides in configuration
   echo "STORAGE_OVERRIDE_ENABLED=true" >> .env
   ```

2. **Fix Override Timing**:
   ```bash
   # Check system time
   date
   
   # Extend existing override
   python -c "
   from system_configuration_manager import SystemConfigurationManager
   config = SystemConfigurationManager()
   config.extend_storage_override('override_id', 2, 'Extended for troubleshooting')
   "
   ```

3. **Reset Override System**:
   ```bash
   # Reset override system
   python scripts/admin/reset_override_system.py
   ```

## Storage Performance Problems

### Slow Storage Operations

#### Symptoms
- Caption generation takes much longer than usual
- File uploads or downloads are slow
- High disk I/O wait times

#### Diagnosis

```bash
# Monitor disk I/O performance
iostat -x 1 10

# Check for high I/O processes
iotop -o

# Monitor storage operations
python scripts/admin/monitor_storage_performance.py --duration 60

# Check disk health
sudo smartctl -a /dev/sda
```

#### Solutions

1. **Optimize Disk I/O**:
   ```bash
   # Check and adjust I/O scheduler
   cat /sys/block/sda/queue/scheduler
   echo mq-deadline | sudo tee /sys/block/sda/queue/scheduler
   ```

2. **Reduce Concurrent Operations**:
   ```bash
   # Limit concurrent image processing
   echo "MAX_CONCURRENT_IMAGES=2" >> .env
   
   # Adjust batch sizes
   echo "STORAGE_BATCH_SIZE=50" >> .env
   ```

3. **Clean Up Storage**:
   ```bash
   # Remove unnecessary files
   python scripts/maintenance/cleanup_temp_files.py --execute
   
   # Defragment if needed (ext4)
   sudo e4defrag /path/to/storage
   ```

### High Memory Usage During Storage Operations

#### Symptoms
- Memory usage spikes during storage checks
- Out of memory errors during cleanup
- System becomes unresponsive during storage operations

#### Diagnosis

```bash
# Monitor memory usage during storage operations
python scripts/admin/monitor_storage_memory.py

# Check for memory leaks
python scripts/admin/check_storage_memory_leaks.py

# Profile memory usage
python -m memory_profiler scripts/maintenance/storage_operation.py
```

#### Solutions

1. **Optimize Memory Usage**:
   ```bash
   # Use streaming operations
   echo "STORAGE_USE_STREAMING=true" >> .env
   
   # Reduce batch sizes
   echo "STORAGE_MEMORY_BATCH_SIZE=100" >> .env
   ```

2. **Increase Available Memory**:
   ```bash
   # Increase swap space
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

3. **Process Files in Smaller Batches**:
   ```bash
   # Configure smaller processing batches
   python scripts/admin/configure_memory_efficient_processing.py
   ```

## File System Issues

### File Permission Problems

#### Symptoms
- Cannot write to storage directory
- Permission denied errors
- Files created with wrong ownership

#### Diagnosis

```bash
# Check storage directory permissions
ls -la storage/
ls -la storage/images/

# Check process ownership
ps aux | grep python | grep vedfolnir

# Verify user permissions
id vedfolnir-user
groups vedfolnir-user
```

#### Solutions

1. **Fix Directory Permissions**:
   ```bash
   # Set correct permissions
   sudo chown -R vedfolnir-user:vedfolnir-group storage/
   sudo chmod -R 755 storage/
   sudo chmod -R 644 storage/images/*
   ```

2. **Fix Process Ownership**:
   ```bash
   # Run application as correct user
   sudo -u vedfolnir-user python web_app.py
   ```

3. **Configure SELinux/AppArmor** (if applicable):
   ```bash
   # Check SELinux context
   ls -Z storage/
   
   # Set correct SELinux context
   sudo setsebool -P httpd_can_network_connect 1
   sudo semanage fcontext -a -t httpd_exec_t "/path/to/storage(/.*)?"
   sudo restorecon -R /path/to/storage
   ```

### Corrupted Files

#### Symptoms
- Cannot read image files
- Checksum mismatches
- File corruption errors

#### Diagnosis

```bash
# Check for corrupted files
python scripts/admin/check_file_integrity.py

# Verify file checksums
python scripts/admin/verify_file_checksums.py

# Check file system integrity
sudo fsck -n /dev/sda1
```

#### Solutions

1. **Identify and Remove Corrupted Files**:
   ```bash
   # Find corrupted files
   python scripts/admin/find_corrupted_files.py
   
   # Remove corrupted files
   python scripts/admin/remove_corrupted_files.py --backup-first
   ```

2. **Restore from Backup**:
   ```bash
   # Restore corrupted files from backup
   python scripts/admin/restore_from_backup.py --corrupted-only
   ```

3. **Repair File System**:
   ```bash
   # Repair file system (requires unmounting)
   sudo umount /path/to/storage
   sudo fsck -y /dev/sda1
   sudo mount /path/to/storage
   ```

### Disk Space Issues

#### Symptoms
- "No space left on device" errors
- Cannot create new files
- System becomes unresponsive

#### Diagnosis

```bash
# Check disk space
df -h
df -i  # Check inode usage

# Find largest files and directories
du -sh storage/* | sort -hr | head -10
find storage/ -type f -size +100M | head -20

# Check for hidden space usage
lsof +L1  # Files deleted but still open
```

#### Solutions

1. **Emergency Space Recovery**:
   ```bash
   # Emergency cleanup
   python scripts/emergency/emergency_space_recovery.py
   
   # Remove temporary files
   find /tmp -type f -atime +7 -delete
   find storage/temp/ -type f -delete
   ```

2. **Expand Storage**:
   ```bash
   # Add new disk or expand existing
   # (System-specific procedures)
   
   # Move storage to larger partition
   python scripts/admin/migrate_storage.py --new-path /new/storage/path
   ```

3. **Archive Old Data**:
   ```bash
   # Archive old files to external storage
   python scripts/archival/archive_old_data.py --target-free-gb 20
   ```

## Configuration Problems

### Invalid Storage Configuration

#### Symptoms
- Storage system not initializing
- Configuration validation errors
- Inconsistent behavior

#### Diagnosis

```bash
# Validate storage configuration
python scripts/admin/validate_storage_config.py

# Check environment variables
env | grep STORAGE

# Verify configuration file syntax
python -c "
from config import Config
try:
    config = Config()
    print('Configuration loaded successfully')
except Exception as e:
    print(f'Configuration error: {e}')
"
```

#### Solutions

1. **Reset Configuration**:
   ```bash
   # Reset to default configuration
   python scripts/admin/reset_storage_config.py --to-defaults
   ```

2. **Fix Environment Variables**:
   ```bash
   # Validate and fix .env file
   python scripts/admin/fix_env_config.py --storage-only
   ```

3. **Regenerate Configuration**:
   ```bash
   # Generate new configuration
   python scripts/setup/generate_storage_config.py
   ```

### Path Configuration Issues

#### Symptoms
- Cannot find storage directory
- Files saved to wrong location
- Path resolution errors

#### Diagnosis

```bash
# Check configured paths
python -c "
from config import Config
config = Config()
print(f'Storage path: {config.get_storage_path()}')
print(f'Image path: {config.get_image_path()}')
print(f'Temp path: {config.get_temp_path()}')
"

# Verify paths exist and are accessible
python scripts/admin/verify_storage_paths.py
```

#### Solutions

1. **Create Missing Directories**:
   ```bash
   # Create storage directories
   python scripts/setup/create_storage_directories.py
   ```

2. **Fix Path Configuration**:
   ```bash
   # Update path configuration
   python scripts/admin/fix_storage_paths.py --auto-detect
   ```

3. **Migrate Existing Data**:
   ```bash
   # Move data to correct paths
   python scripts/admin/migrate_storage_paths.py
   ```

## Emergency Procedures

### Critical Storage Failure

#### Immediate Response

1. **Assess Situation**:
   ```bash
   # Check system status
   df -h
   python scripts/admin/emergency_storage_assessment.py
   ```

2. **Activate Emergency Mode**:
   ```bash
   # Enable emergency storage mode
   python scripts/emergency/activate_emergency_mode.py
   ```

3. **Free Critical Space**:
   ```bash
   # Emergency space recovery
   python scripts/emergency/critical_space_recovery.py
   ```

4. **Notify Users**:
   ```bash
   # Send emergency notification
   python scripts/admin/send_emergency_notification.py \
       --message "Storage system experiencing issues. Service may be temporarily unavailable."
   ```

### Data Recovery Procedures

#### Backup Recovery

```bash
# List available backups
python scripts/admin/list_storage_backups.py

# Restore from most recent backup
python scripts/admin/restore_storage_backup.py --latest

# Verify restored data
python scripts/admin/verify_restored_data.py
```

#### Partial Recovery

```bash
# Recover specific data types
python scripts/recovery/recover_critical_images.py
python scripts/recovery/recover_user_data.py --user-id 123
python scripts/recovery/recover_recent_data.py --days 7
```

### System Recovery

#### Post-Emergency Recovery

1. **Verify System Integrity**:
   ```bash
   # Comprehensive system check
   python scripts/admin/post_emergency_system_check.py
   ```

2. **Restore Normal Operations**:
   ```bash
   # Deactivate emergency mode
   python scripts/emergency/deactivate_emergency_mode.py
   
   # Resume normal services
   python scripts/admin/resume_normal_operations.py
   ```

3. **Validate Recovery**:
   ```bash
   # Test all storage functions
   python scripts/admin/test_storage_functions.py --comprehensive
   ```

## Prevention and Monitoring

### Proactive Monitoring

#### Automated Monitoring Setup

```bash
# Set up storage monitoring
python scripts/setup/setup_storage_monitoring.py

# Configure alerts
python scripts/setup/configure_storage_alerts.py

# Set up automated cleanup
python scripts/setup/setup_automated_cleanup.py
```

#### Monitoring Scripts

```bash
# Daily storage health check
python scripts/monitoring/daily_storage_check.py

# Weekly storage analysis
python scripts/monitoring/weekly_storage_analysis.py

# Monthly capacity planning
python scripts/monitoring/monthly_capacity_planning.py
```

### Preventive Maintenance

#### Regular Maintenance Tasks

1. **Daily**:
   - Check storage usage
   - Monitor error logs
   - Verify backup status

2. **Weekly**:
   - Run storage integrity checks
   - Analyze usage trends
   - Clean up temporary files

3. **Monthly**:
   - Comprehensive storage analysis
   - Capacity planning review
   - Configuration validation

#### Maintenance Scripts

```bash
# Automated maintenance
python scripts/maintenance/automated_storage_maintenance.py

# Health check suite
python scripts/maintenance/storage_health_check_suite.py

# Performance optimization
python scripts/maintenance/optimize_storage_performance.py
```

### Best Practices

#### Storage Management

1. **Monitor Proactively**: Don't wait for problems to occur
2. **Plan Capacity**: Always plan for growth
3. **Backup Regularly**: Maintain current backups
4. **Document Changes**: Keep records of configuration changes
5. **Test Recovery**: Regularly test backup and recovery procedures

#### Troubleshooting Approach

1. **Start with Basics**: Check disk space, permissions, and configuration
2. **Use Logs**: Always check logs for error messages and patterns
3. **Test Incrementally**: Make one change at a time
4. **Document Solutions**: Record what worked for future reference
5. **Verify Fixes**: Always verify that problems are actually resolved

This comprehensive troubleshooting guide should help resolve most storage-related issues in Vedfolnir. For issues not covered here, contact system administrators or consult the detailed system logs for additional diagnostic information.