# Session Maintenance Utilities

This document describes the session cleanup and maintenance utilities implemented for Task 14 of the Session Management System.

## Overview

The session maintenance utilities provide automated cleanup of expired sessions, comprehensive analytics and health monitoring, and database maintenance capabilities for optimal performance.

## Utilities

### 1. Session Cleanup Service (`session_cleanup.py`)

Automated session cleanup with configurable intervals and comprehensive logging.

**Features:**
- Automated expired session cleanup
- Orphaned session detection and removal
- Configurable cleanup intervals
- Batch processing for performance
- Daemon mode for continuous operation
- Force cleanup with custom age limits

**Usage:**
```bash
# Run cleanup once
python scripts/maintenance/session_cleanup.py --once

# Run as daemon
python scripts/maintenance/session_cleanup.py --daemon

# Force cleanup with custom age
python scripts/maintenance/session_cleanup.py --force --max-age 24

# Show statistics
python scripts/maintenance/session_cleanup.py --stats
```

**Configuration:**
- `SESSION_CLEANUP_INTERVAL`: Cleanup interval in seconds (default: 3600)
- `SESSION_CLEANUP_BATCH_SIZE`: Batch size for processing (default: 100)
- `SESSION_MAX_AGE`: Maximum session age in seconds (default: 172800)

### 2. Session Analytics (`session_analytics.py`)

Comprehensive analytics and health monitoring for the session management system.

**Features:**
- Health report generation
- Session trends analysis
- Performance metrics collection
- Security analysis
- Detailed analytics with recommendations
- Report export functionality

**Usage:**
```bash
# Generate health report
python scripts/maintenance/session_analytics.py --health-report

# Show session trends
python scripts/maintenance/session_analytics.py --trends 7

# Export report to file
python scripts/maintenance/session_analytics.py --health-report --export report.json

# JSON output
python scripts/maintenance/session_analytics.py --health-report --json
```

### 3. Database Maintenance (`session_db_maintenance.py`)

Database maintenance scripts for session table optimization and performance tuning.

**Features:**
- Session table analysis
- Recommended index creation
- Database optimization
- Integrity checking
- Performance statistics
- Maintenance recommendations

**Usage:**
```bash
# Analyze session tables
python scripts/maintenance/session_db_maintenance.py --analyze

# Create recommended indexes
python scripts/maintenance/session_db_maintenance.py --create-indexes

# Optimize tables
python scripts/maintenance/session_db_maintenance.py --optimize

# Check database integrity
python scripts/maintenance/session_db_maintenance.py --integrity-check

# Show database statistics
python scripts/maintenance/session_db_maintenance.py --stats
```

### 4. Unified Session Maintenance CLI (`session_maintenance.py`)

Unified interface combining all session maintenance utilities.

**Features:**
- Complete maintenance cycle
- Individual utility access
- Comprehensive status reporting
- Dry-run mode for safe testing
- JSON output for automation

**Usage:**
```bash
# Run complete maintenance
python scripts/maintenance/session_maintenance.py --full-maintenance

# Show system status
python scripts/maintenance/session_maintenance.py --status

# Cleanup operations
python scripts/maintenance/session_maintenance.py --cleanup --once

# Analytics operations
python scripts/maintenance/session_maintenance.py --analytics --health

# Database operations
python scripts/maintenance/session_maintenance.py --database --analyze

# Dry run mode
python scripts/maintenance/session_maintenance.py --full-maintenance --dry-run
```

## Automation

### Cron Job Setup

For automated maintenance, set up a cron job:

```bash
# Run cleanup every hour
0 * * * * /path/to/vedfolnir/scripts/maintenance/session_cleanup.py --once

# Run full maintenance daily at 2 AM
0 2 * * * /path/to/vedfolnir/scripts/maintenance/session_maintenance.py --full-maintenance
```

### Systemd Service

Create a systemd service for continuous cleanup:

```ini
[Unit]
Description=Vedfolnir Session Cleanup Service
After=network.target

[Service]
Type=simple
User=vedfolnir
WorkingDirectory=/path/to/vedfolnir
ExecStart=/path/to/vedfolnir/scripts/maintenance/session_cleanup.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Monitoring

### Health Checks

The utilities provide comprehensive health monitoring:

- **Overall Health Status**: Good/Warning/Critical
- **Session Statistics**: Active sessions, user counts, age distribution
- **Performance Metrics**: Response times, success rates, connection pool status
- **Security Analysis**: Suspicious activity detection, security scoring
- **Database Health**: Integrity checks, optimization status

### Alerts

The system generates alerts for:
- High session creation rates
- Elevated error rates
- Security issues
- Database problems
- Performance degradation

### Metrics Collection

Key metrics collected:
- Session creation/expiration rates
- Platform switch performance
- Database operation times
- Connection pool utilization
- Error frequencies

## Configuration

### Environment Variables

```bash
# Cleanup configuration
SESSION_CLEANUP_INTERVAL=3600        # 1 hour
SESSION_CLEANUP_BATCH_SIZE=100       # Process 100 sessions at a time
SESSION_MAX_AGE=172800               # 48 hours

# Monitoring configuration
SESSION_MONITORING_ENABLED=true
SESSION_METRICS_RETENTION_DAYS=7
SESSION_ALERT_THRESHOLDS_FILE=/path/to/thresholds.json
```

### Alert Thresholds

Customize alert thresholds in the monitoring configuration:

```python
alert_thresholds = {
    'session_creation_rate': 100,    # per minute
    'session_failure_rate': 10,      # per minute
    'avg_session_duration': 3600,    # seconds
    'concurrent_sessions': 1000,     # total
    'suspicious_activity_rate': 5    # per minute
}
```

## Troubleshooting

### Common Issues

1. **Database Lock Errors**
   - Ensure only one maintenance process runs at a time
   - Use the unified CLI to avoid conflicts

2. **High Memory Usage**
   - Reduce batch sizes for large datasets
   - Run cleanup more frequently

3. **Performance Issues**
   - Create recommended database indexes
   - Optimize connection pool settings

### Logging

All utilities provide comprehensive logging:
- INFO level: Normal operations
- WARNING level: Issues that need attention
- ERROR level: Failures requiring intervention
- DEBUG level: Detailed diagnostic information

### Diagnostics

Use the status command for quick diagnostics:

```bash
python scripts/maintenance/session_maintenance.py --status --json
```

This provides:
- Current session counts
- Health status
- Database statistics
- Recent issues

## Requirements Fulfilled

This implementation fulfills the following requirements from Task 14:

- **Requirement 1.4**: Automated expired session cleanup with configurable intervals
- **Requirement 8.1**: Session analytics and health monitoring utilities  
- **Requirement 8.2**: Comprehensive logging for session operations and errors
- **Requirement 8.3**: Diagnostic information for troubleshooting session issues

The utilities provide a complete maintenance solution for the session management system with automation capabilities, comprehensive monitoring, and performance optimization features.