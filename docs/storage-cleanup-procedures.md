# Storage Cleanup Procedures

This document provides comprehensive procedures for managing storage when limits are reached, including automated cleanup, manual procedures, and emergency protocols.

## Table of Contents

1. [Overview](#overview)
2. [Automated Cleanup Procedures](#automated-cleanup-procedures)
3. [Manual Cleanup Procedures](#manual-cleanup-procedures)
4. [Emergency Cleanup Protocols](#emergency-cleanup-protocols)
5. [Storage Analysis and Planning](#storage-analysis-and-planning)
6. [Data Archival Procedures](#data-archival-procedures)
7. [Cleanup Verification](#cleanup-verification)
8. [Best Practices](#best-practices)

## Overview

### Storage Cleanup Strategy

Vedfolnir uses a multi-tiered approach to storage cleanup:

1. **Automated Cleanup**: Routine removal of temporary and expired files
2. **Scheduled Cleanup**: Regular cleanup of old processed images
3. **Manual Cleanup**: Administrator-initiated cleanup of specific data
4. **Emergency Cleanup**: Rapid space recovery during critical situations
5. **Archival**: Long-term storage of important historical data

### Cleanup Priorities

When storage limits are reached, cleanup follows this priority order:

1. **Temporary Files**: Processing temporary files and caches
2. **Failed Processing**: Images from failed processing attempts
3. **Duplicate Images**: Identical images stored multiple times
4. **Old Processed Images**: Successfully processed images older than retention period
5. **Archived Data**: Data that can be moved to external storage

### Safety Measures

All cleanup procedures include safety measures:

- **Dry Run Mode**: Preview what will be deleted before execution
- **Backup Verification**: Ensure backups exist before deletion
- **Rollback Capability**: Ability to restore accidentally deleted data
- **Audit Logging**: Complete logging of all cleanup activities

## Automated Cleanup Procedures

### Daily Automated Cleanup

The system runs automated cleanup daily to maintain storage health:

```bash
# Daily cleanup script (runs automatically via cron)
python scripts/maintenance/daily_storage_cleanup.py
```

#### What Gets Cleaned Daily

1. **Temporary Processing Files**:
   - Files in `storage/temp/` older than 24 hours
   - Incomplete download files
   - Processing lock files

2. **Failed Processing Data**:
   - Images from failed processing attempts older than 7 days
   - Error logs older than 30 days
   - Temporary files from crashed processes

3. **Cache Files**:
   - Thumbnail caches older than 30 days
   - Processing result caches older than 7 days
   - Session temporary files

### Weekly Automated Cleanup

More comprehensive cleanup runs weekly:

```bash
# Weekly cleanup script (runs automatically via cron)
python scripts/maintenance/weekly_storage_cleanup.py
```

#### What Gets Cleaned Weekly

1. **Old Processed Images**:
   - Successfully processed images older than 90 days (configurable)
   - Images with approved captions older than retention period
   - Duplicate images identified by hash comparison

2. **Log Files**:
   - Application logs older than 60 days
   - Processing logs older than 30 days
   - Debug logs older than 14 days

3. **Database Cleanup**:
   - Orphaned image records without files
   - Expired session data
   - Old processing run records

### Configuring Automated Cleanup

#### Environment Variables

```bash
# Automated Cleanup Configuration
AUTO_CLEANUP_ENABLED=true                    # Enable automated cleanup
AUTO_CLEANUP_TEMP_FILES_HOURS=24            # Clean temp files after 24 hours
AUTO_CLEANUP_FAILED_PROCESSING_DAYS=7       # Clean failed processing after 7 days
AUTO_CLEANUP_PROCESSED_IMAGES_DAYS=90       # Clean processed images after 90 days
AUTO_CLEANUP_LOG_FILES_DAYS=60              # Clean log files after 60 days

# Safety Settings
AUTO_CLEANUP_DRY_RUN=false                  # Set to true for testing
AUTO_CLEANUP_BACKUP_BEFORE_DELETE=true     # Backup before deletion
AUTO_CLEANUP_MAX_DELETE_PER_RUN=1000       # Limit deletions per run
```

#### Customizing Cleanup Rules

```bash
# Update cleanup configuration
python -c "
from system_configuration_manager import SystemConfigurationManager
config_manager = SystemConfigurationManager()

# Set custom retention periods
config_manager.update_cleanup_config({
    'temp_files_hours': 12,
    'failed_processing_days': 3,
    'processed_images_days': 60,
    'log_files_days': 30
})
print('Cleanup configuration updated')
"
```

### Monitoring Automated Cleanup

#### Cleanup Logs

```bash
# View cleanup activity logs
tail -f logs/storage_cleanup.log

# Check cleanup statistics
grep "CLEANUP_SUMMARY" logs/storage_cleanup.log | tail -5

# View cleanup errors
grep "CLEANUP_ERROR" logs/storage_cleanup.log
```

#### Cleanup Reports

```bash
# Generate cleanup report
python scripts/admin/generate_cleanup_report.py --days 7

# View cleanup statistics
python scripts/admin/cleanup_statistics.py --summary
```

## Manual Cleanup Procedures

### Interactive Cleanup Tool

Use the interactive cleanup tool for manual cleanup:

```bash
# Start interactive cleanup
python scripts/admin/interactive_cleanup.py
```

The interactive tool provides:
- Storage usage analysis
- Cleanup recommendations
- Safe deletion with confirmation
- Real-time progress monitoring

### Targeted Cleanup Commands

#### Clean Specific File Types

```bash
# Clean temporary files
python scripts/maintenance/cleanup_temp_files.py --older-than-hours 6

# Clean failed processing files
python scripts/maintenance/cleanup_failed_processing.py --older-than-days 3

# Clean duplicate images
python scripts/maintenance/cleanup_duplicates.py --dry-run
python scripts/maintenance/cleanup_duplicates.py --execute

# Clean old processed images
python scripts/maintenance/cleanup_old_images.py \
    --older-than-days 60 \
    --keep-approved-captions \
    --dry-run
```

#### Clean by Storage Usage

```bash
# Free up specific amount of space
python scripts/maintenance/cleanup_by_size.py \
    --target-free-gb 20 \
    --dry-run

# Clean until usage is below threshold
python scripts/maintenance/cleanup_to_threshold.py \
    --target-usage-percent 75 \
    --dry-run
```

#### Clean by Date Range

```bash
# Clean files from specific date range
python scripts/maintenance/cleanup_date_range.py \
    --start-date 2024-01-01 \
    --end-date 2024-06-30 \
    --file-types "temp,failed" \
    --dry-run
```

### Advanced Cleanup Options

#### Selective Cleanup

```bash
# Clean specific user's data
python scripts/maintenance/cleanup_user_data.py \
    --user-id 123 \
    --older-than-days 30 \
    --dry-run

# Clean specific platform data
python scripts/maintenance/cleanup_platform_data.py \
    --platform-type pixelfed \
    --older-than-days 45 \
    --dry-run

# Clean by file size
python scripts/maintenance/cleanup_large_files.py \
    --min-size-mb 50 \
    --older-than-days 14 \
    --dry-run
```

#### Cleanup with Conditions

```bash
# Clean only if backups exist
python scripts/maintenance/conditional_cleanup.py \
    --require-backup \
    --older-than-days 30 \
    --dry-run

# Clean only successful processing
python scripts/maintenance/cleanup_successful_only.py \
    --older-than-days 60 \
    --keep-recent-approved \
    --dry-run
```

### Manual Cleanup Verification

Before executing manual cleanup:

1. **Run in Dry-Run Mode**:
   ```bash
   # Always test first
   python scripts/maintenance/cleanup_command.py --dry-run
   ```

2. **Review What Will Be Deleted**:
   ```bash
   # Generate deletion preview
   python scripts/admin/preview_cleanup.py --older-than-days 30
   ```

3. **Verify Backups**:
   ```bash
   # Check backup status
   python scripts/admin/verify_backups.py --check-recent
   ```

4. **Execute with Confirmation**:
   ```bash
   # Execute with confirmation prompts
   python scripts/maintenance/cleanup_command.py --interactive
   ```

## Emergency Cleanup Protocols

### Critical Storage Situations

When storage is critically low (>98% full), use emergency procedures:

#### Immediate Emergency Cleanup

```bash
# Emergency cleanup - removes most aggressive targets
python scripts/emergency/emergency_cleanup.py --critical

# Quick space recovery
python scripts/emergency/quick_space_recovery.py --target-gb 10
```

#### Emergency Cleanup Steps

1. **Assess Critical Situation**:
   ```bash
   # Check available space
   df -h /path/to/storage
   
   # Identify largest files
   find storage/ -type f -size +100M | head -20
   ```

2. **Emergency File Removal**:
   ```bash
   # Remove all temporary files immediately
   find storage/temp/ -type f -delete
   
   # Remove failed processing files
   find storage/images/ -name "*_failed_*" -delete
   
   # Clear processing caches
   rm -rf storage/cache/*
   ```

3. **Database Cleanup**:
   ```bash
   # Remove orphaned database records
   python scripts/emergency/cleanup_orphaned_records.py
   
   # Clean expired sessions
   python scripts/emergency/cleanup_expired_sessions.py
   ```

4. **Verify Space Recovery**:
   ```bash
   # Check recovered space
   df -h /path/to/storage
   
   # Verify system functionality
   python scripts/admin/verify_system_health.py
   ```

### Emergency Cleanup Safety

Even in emergencies, maintain safety:

- **Log All Actions**: Record what was deleted
- **Verify Critical Data**: Ensure important data isn't deleted
- **Test System**: Verify system works after cleanup
- **Document Incident**: Record emergency procedures used

## Storage Analysis and Planning

### Storage Usage Analysis

#### Comprehensive Storage Analysis

```bash
# Analyze storage usage patterns
python scripts/admin/analyze_storage_usage.py --detailed

# Generate storage breakdown report
python scripts/admin/storage_breakdown.py --by-category --by-date

# Identify cleanup opportunities
python scripts/admin/identify_cleanup_targets.py --recommendations
```

#### Usage Pattern Analysis

```bash
# Analyze growth patterns
python scripts/admin/storage_growth_analysis.py --days 90

# Identify unusual usage
python scripts/admin/detect_storage_anomalies.py --threshold 2.0

# Project future needs
python scripts/admin/storage_capacity_planning.py --months 6
```

### Cleanup Planning

#### Develop Cleanup Strategy

1. **Assess Current Usage**:
   - Total storage used
   - File type breakdown
   - Age distribution of files
   - User/platform distribution

2. **Identify Cleanup Targets**:
   - Temporary files
   - Failed processing data
   - Old processed images
   - Duplicate files

3. **Plan Cleanup Phases**:
   - Phase 1: Safe, immediate cleanup
   - Phase 2: Older processed data
   - Phase 3: Archival of historical data

4. **Set Cleanup Goals**:
   - Target storage usage percentage
   - Minimum free space required
   - Timeline for cleanup completion

#### Cleanup Impact Assessment

```bash
# Estimate cleanup impact
python scripts/admin/estimate_cleanup_impact.py \
    --older-than-days 60 \
    --file-types "processed,temp"

# Analyze user impact
python scripts/admin/analyze_cleanup_user_impact.py \
    --cleanup-plan cleanup_plan.json
```

## Data Archival Procedures

### Archival Strategy

Before deleting data, consider archival:

1. **Identify Archival Candidates**:
   - Successfully processed images older than 6 months
   - Approved captions with historical value
   - Complete processing runs for audit purposes

2. **Archival Destinations**:
   - External storage systems
   - Cloud storage services
   - Backup tape systems
   - Network attached storage

### Archival Procedures

#### Automated Archival

```bash
# Archive old processed images
python scripts/archival/archive_old_images.py \
    --older-than-days 180 \
    --destination /backup/archive/ \
    --verify-integrity

# Archive processing logs
python scripts/archival/archive_processing_logs.py \
    --older-than-days 90 \
    --compress \
    --destination /backup/logs/
```

#### Manual Archival

```bash
# Interactive archival tool
python scripts/admin/interactive_archival.py

# Archive specific data sets
python scripts/archival/archive_dataset.py \
    --dataset-id dataset_123 \
    --destination s3://backup-bucket/vedfolnir/ \
    --encrypt
```

### Archival Verification

```bash
# Verify archived data integrity
python scripts/archival/verify_archive_integrity.py \
    --archive-path /backup/archive/ \
    --check-checksums

# Test archive restoration
python scripts/archival/test_archive_restore.py \
    --archive-file archive_20250115.tar.gz \
    --test-restore-path /tmp/restore_test/
```

## Cleanup Verification

### Post-Cleanup Verification

After any cleanup operation:

#### System Health Checks

```bash
# Verify system functionality
python scripts/admin/post_cleanup_health_check.py

# Check database integrity
python scripts/admin/verify_database_integrity.py

# Test caption generation
python scripts/admin/test_caption_generation.py --quick-test
```

#### Storage Verification

```bash
# Verify storage usage reduction
python scripts/admin/verify_storage_cleanup.py \
    --before-usage 95.2 \
    --target-usage 80.0

# Check for orphaned files
python scripts/admin/find_orphaned_files.py

# Verify file system integrity
python scripts/admin/verify_filesystem_integrity.py
```

#### Data Integrity Checks

```bash
# Verify no critical data was deleted
python scripts/admin/verify_critical_data.py

# Check database consistency
python scripts/admin/check_database_consistency.py

# Verify user data integrity
python scripts/admin/verify_user_data_integrity.py
```

### Cleanup Reporting

#### Generate Cleanup Reports

```bash
# Generate comprehensive cleanup report
python scripts/admin/generate_cleanup_report.py \
    --cleanup-session session_20250115 \
    --include-details \
    --output-format html

# Create cleanup summary
python scripts/admin/cleanup_summary.py \
    --date 2025-01-15 \
    --email-report admin@example.com
```

#### Cleanup Metrics

Track cleanup effectiveness:

- **Space Recovered**: Amount of storage freed
- **Files Processed**: Number of files cleaned
- **Time Taken**: Duration of cleanup operations
- **Error Rate**: Percentage of cleanup operations that failed
- **User Impact**: Effect on system users during cleanup

## Best Practices

### Cleanup Planning

#### Regular Cleanup Schedule

- **Daily**: Temporary files and caches
- **Weekly**: Failed processing data and old logs
- **Monthly**: Old processed images and comprehensive cleanup
- **Quarterly**: Full system cleanup and archival

#### Cleanup Preparation

1. **Backup Critical Data**: Ensure backups are current
2. **Notify Users**: Inform users of planned cleanup activities
3. **Schedule Downtime**: Plan cleanup during low-usage periods
4. **Prepare Rollback**: Have procedures ready to restore data if needed

### Safety Measures

#### Always Use Dry-Run First

```bash
# Never skip dry-run for significant cleanup
python cleanup_script.py --dry-run
# Review output carefully
python cleanup_script.py --execute
```

#### Verify Backups Before Cleanup

```bash
# Check backup status before cleanup
python scripts/admin/verify_backup_status.py --critical-data-only
```

#### Monitor Cleanup Progress

```bash
# Monitor cleanup in real-time
python scripts/admin/monitor_cleanup.py --session session_id
```

### Performance Considerations

#### Cleanup During Off-Peak Hours

- Schedule intensive cleanup during low-usage periods
- Monitor system performance during cleanup
- Pause cleanup if system performance degrades

#### Batch Processing

- Process files in small batches to avoid system overload
- Use rate limiting for I/O intensive operations
- Monitor disk I/O and adjust batch sizes accordingly

### Documentation and Auditing

#### Document All Cleanup Activities

- Record what was cleaned and when
- Document reasons for cleanup decisions
- Maintain cleanup logs for audit purposes
- Track cleanup effectiveness over time

#### Audit Trail

```bash
# Generate audit report
python scripts/admin/generate_cleanup_audit.py \
    --start-date 2025-01-01 \
    --end-date 2025-01-31 \
    --include-details
```

This comprehensive guide provides all the procedures and tools needed to effectively manage storage cleanup in Vedfolnir. Regular application of these procedures will ensure optimal storage utilization and system performance.