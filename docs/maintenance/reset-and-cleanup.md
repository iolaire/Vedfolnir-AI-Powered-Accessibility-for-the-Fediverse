# Reset and Cleanup Guide

This guide covers all the available options for resetting and cleaning up your Vedfolnir installation.

## Quick Reference

### 🔍 Check Status
```bash
# Show current application status
python scripts/maintenance/reset_app.py --status
```

### 🧹 Safe Cleanup (Recommended)
```bash
# Preview what would be cleaned up
python scripts/maintenance/reset_app.py --cleanup --dry-run

# Clean up old data using retention policies (safe)
python scripts/maintenance/reset_app.py --cleanup
```

### 🔄 Complete Reset (Nuclear Option)
```bash
# Preview complete reset
python scripts/maintenance/reset_app.py --reset-complete --dry-run

# Complete reset (database + storage)
python scripts/maintenance/reset_app.py --reset-complete
```

## Available Reset Options

### 1. Application Status
Shows the current state of your Vedfolnir installation:

```bash
python scripts/maintenance/reset_app.py --status
```

**What it shows:**
- Configuration validity
- Database size and record counts
- Storage directory sizes
- Environment variable status

### 2. Data Cleanup (Safe)
Cleans up old data according to retention policies without destroying current data:

```bash
# Preview cleanup
python scripts/maintenance/reset_app.py --cleanup --dry-run

# Perform cleanup
python scripts/maintenance/reset_app.py --cleanup
```

**What it cleans:**
- Old processing runs (90+ days)
- Old rejected images (30+ days)
- Old posted images (180+ days)
- Old error images (60+ days)
- Orphaned posts
- Old log files

### 3. Database Reset
Resets only the database, keeping all image files:

```bash
# Preview database reset
python scripts/maintenance/reset_app.py --reset-db --dry-run

# Reset database
python scripts/maintenance/reset_app.py --reset-db
```

**What it does:**
- Drops all database tables
- Recreates empty tables
- Keeps all image files in storage/images

### 4. Storage Reset
Resets only storage files, keeping the database:

```bash
# Preview storage reset
python scripts/maintenance/reset_app.py --reset-storage --dry-run

# Reset storage
python scripts/maintenance/reset_app.py --reset-storage
```

**What it does:**
- Deletes all files in storage/images
- Clears all log files
- Keeps database intact

### 5. Complete Reset
Nuclear option - resets everything to a fresh state:

```bash
# Preview complete reset
python scripts/maintenance/reset_app.py --reset-complete --dry-run

# Complete reset (requires confirmation)
python scripts/maintenance/reset_app.py --reset-complete

# Skip confirmation (use with caution)
python scripts/maintenance/reset_app.py --reset-complete --force
```

**What it does:**
- Resets database (all tables dropped and recreated)
- Deletes all storage files
- Clears all logs
- Returns app to fresh installation state

### 6. User-Specific Reset
Reset data for a specific user:

```bash
# Preview user data reset
python scripts/maintenance/reset_app.py --reset-user username123 --dry-run

# Reset user data
python scripts/maintenance/reset_app.py --reset-user username123
```

**What it does:**
- Deletes all posts for the user
- Deletes all images for the user
- Deletes all processing runs for the user
- Removes associated image files

## Advanced Cleanup Options

### Granular Data Cleanup
For more specific cleanup operations, use the data cleanup script directly:

```bash
# Clean up specific types of data
python scripts/maintenance/data_cleanup.py --help

# Examples:
python scripts/maintenance/data_cleanup.py --rejected 7 --dry-run    # Clean rejected images older than 7 days
python scripts/maintenance/data_cleanup.py --storage --dry-run       # Clean all storage images
python scripts/maintenance/data_cleanup.py --logs --dry-run          # Clean log files
python scripts/maintenance/data_cleanup.py --all --dry-run           # Full cleanup
```

### Database-Only Operations
```bash
# Empty database completely
python scripts/maintenance/empty_db.py

# Check database contents
python scripts/maintenance/check_db.py
```

## Safety Features

### Dry Run Mode
All reset operations support `--dry-run` mode to preview changes:

```bash
# Always test first with --dry-run
python scripts/maintenance/reset_app.py --reset-complete --dry-run
```

### Confirmation Prompts
Destructive operations require confirmation unless `--force` is used:

```bash
# Will prompt for confirmation
python scripts/maintenance/reset_app.py --reset-complete

# Skips confirmation (dangerous)
python scripts/maintenance/reset_app.py --reset-complete --force
```

### Backup Recommendations
Before performing destructive operations:

1. **Backup Database:**
   ```bash
   cp storage/database/vedfolnir.db storage/database/vedfolnir.db.backup
   ```

2. **Backup Images:**
   ```bash
   tar -czf storage_backup.tar.gz storage/images/
   ```

3. **Backup Configuration:**
   ```bash
   # Environment variables are managed by the system
   # No configuration files to backup
   ```

## Common Use Cases

### 1. Fresh Development Environment
```bash
# Complete reset for clean development
python scripts/maintenance/reset_app.py --reset-complete
```

### 2. Clean Up Old Data
```bash
# Regular maintenance cleanup
python scripts/maintenance/reset_app.py --cleanup
```

### 3. Fix Database Issues
```bash
# Reset database but keep images
python scripts/maintenance/reset_app.py --reset-db
```

### 4. Free Up Storage Space
```bash
# Clean up old images and logs
python scripts/maintenance/reset_app.py --reset-storage
```

### 5. Remove Test User Data
```bash
# Clean up specific user's data
python scripts/maintenance/reset_app.py --reset-user testuser123
```

## After Reset

After performing a reset, you may need to:

1. **Ensure Environment Variables:**
   ```bash
   python scripts/setup/verify_env_setup.py
   ```

2. **Start the Application:**
   ```bash
   python web_app.py
   ```

3. **Set Up Platform Connections:**
   - Log in to the web interface
   - Go to Platform Management
   - Add your platform connections

4. **Verify Everything Works:**
   ```bash
   python scripts/maintenance/reset_app.py --status
   ```

## Troubleshooting

### "Configuration Invalid" Error
If you see configuration errors:

1. Check environment variables:
   ```bash
   python scripts/setup/verify_env_setup.py
   ```

2. Generate missing variables:
   ```bash
   python scripts/setup/generate_env_secrets.py
   ```

### Permission Errors
If you get permission errors:

```bash
# Fix file permissions
chmod -R 755 storage/
chmod -R 755 logs/
```

### Database Locked Errors
If database is locked:

1. Stop the web application
2. Wait a few seconds
3. Try the reset operation again

## Automation

### Scheduled Cleanup
Add to crontab for regular cleanup:

```bash
# Clean up old data weekly (Sundays at 2 AM)
0 2 * * 0 /path/to/vedfolnir/scripts/maintenance/reset_app.py --cleanup

# Check status daily
0 8 * * * /path/to/vedfolnir/scripts/maintenance/reset_app.py --status
```

### CI/CD Integration
For automated testing environments:

```bash
# Reset for each test run
python scripts/maintenance/reset_app.py --reset-complete --force
```

## Security Considerations

- Reset operations don't affect environment variables or configuration
- Platform credentials in the database are encrypted and will be lost on database reset
- Always verify environment variables are set after reset operations
- Consider the security implications of force-skipping confirmations in scripts