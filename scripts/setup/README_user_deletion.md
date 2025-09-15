# User Deletion Documentation

This document explains the user deletion functionality in Vedfolnir and how to safely remove users and their data.

## Overview

Vedfolnir provides comprehensive user deletion tools that ensure all user data is properly removed from the system. This includes database records, files, cached data, and sessions.

## Available Scripts

### 1. Interactive User Deletion Tool (Recommended)
**File**: `scripts/setup/delete_user.py`
**Wrapper**: `scripts/delete_user.py`

This is the recommended way to delete users. It provides:
- Interactive user selection
- Dry-run preview showing what will be deleted
- Safety confirmations
- Comprehensive data deletion
- Detailed summary of deleted items

**Usage**:
```bash
# Using the wrapper (recommended)
python3 scripts/delete_user.py

# Or directly
python3 scripts/setup/delete_user.py
```

### 2. Command-Line User Data Deletion
**File**: `scripts/maintenance/delete_user_data.py`

This script provides command-line access to user data deletion with advanced options.

**Usage**:
```bash
# Dry run (preview only)
python3 scripts/maintenance/delete_user_data.py --user-id 1 --dry-run

# Actual deletion
python3 scripts/maintenance/delete_user_data.py --user-id 1 --confirm

# Delete by username
python3 scripts/maintenance/delete_user_data.py --username johndoe --confirm

# Only expire sessions (useful after platform changes)
python3 scripts/maintenance/delete_user_data.py --user-id 1 --expire-sessions-only
```

### 3. User Management Tool
**File**: `scripts/setup/update_user.py`

This script includes basic user deletion but redirects to the comprehensive tool for safety.

## What Gets Deleted

When you delete a user, the following data is removed:

### Database Records
- User account record
- All posts created by the user
- All images associated with the user's posts
- Processing runs and batch operations
- Platform connections and credentials
- Caption generation tasks and settings
- User sessions (both database and Redis)
- Audit logs (job logs, GDPR logs)
- Storage events and overrides

### Files and Directories
- Downloaded image files
- User-specific storage directories
- Temporary files
- Cached data

### Session and Cache Data
- Active Redis sessions
- Platform connection cache
- User-specific cache entries

## Safety Features

### Dry-Run Mode
All deletion scripts support dry-run mode that shows what would be deleted without actually removing anything:

```bash
python3 scripts/maintenance/delete_user_data.py --user-id 1 --dry-run
```

### Multiple Confirmations
The interactive tool requires multiple confirmations:
1. Selection of the user to delete
2. Review of the dry-run results
3. Confirmation to proceed
4. Final confirmation with exact username

### Detailed Logging
All deletion operations are logged with detailed information about what was removed.

## Best Practices

### 1. Always Run Dry-Run First
Before deleting any user, run a dry-run to see what will be affected:

```bash
python3 scripts/setup/delete_user.py
# Select the user and review the dry-run results
```

### 2. Backup Before Deletion
Consider backing up user data before deletion if there's any chance you might need it:

```bash
# Backup database
python3 scripts/database/mysql_backup_recovery.py --backup

# Backup user-specific files manually if needed
```

### 3. Use the Interactive Tool
The interactive tool (`scripts/setup/delete_user.py`) is the safest option as it:
- Shows all available users
- Runs automatic dry-run preview
- Requires multiple confirmations
- Provides detailed feedback

### 4. Verify Deletion
After deletion, you can verify the user is completely removed:

```bash
# Check if user exists
python3 scripts/debug/check_users.py

# Check for orphaned data
python3 scripts/maintenance/data_cleanup.py --orphaned --dry-run
```

## Session Management

### Expiring Sessions Only
Sometimes you need to expire a user's sessions without deleting their data (e.g., after platform connection changes):

```bash
python3 scripts/maintenance/delete_user_data.py --user-id 1 --expire-sessions-only
```

This will:
- Clear Redis sessions
- Remove database sessions
- Clear platform-specific cache
- Force the user to re-login and refresh their platform context

## Error Handling

### Common Issues
1. **User not found**: Verify the user ID or username exists
2. **Permission errors**: Ensure you have write access to storage directories
3. **Database locks**: Make sure no other processes are using the database
4. **Redis connection**: Redis connection issues will be logged but won't stop the deletion

### Recovery
If deletion fails partway through:
1. Check the logs for specific error messages
2. Run the dry-run again to see what remains
3. Re-run the deletion process
4. Use `scripts/maintenance/data_cleanup.py` to clean up any orphaned data

## Examples

### Complete User Deletion Workflow
```bash
# 1. Launch interactive tool
python3 scripts/delete_user.py

# 2. Select option 3 (Delete a user)
# 3. Choose the user from the list
# 4. Review the dry-run results
# 5. Confirm deletion when prompted
# 6. Verify completion
```

### Command-Line Deletion
```bash
# 1. Preview what will be deleted
python3 scripts/maintenance/delete_user_data.py --username johndoe --dry-run

# 2. If satisfied, run actual deletion
python3 scripts/maintenance/delete_user_data.py --username johndoe --confirm
```

### Session Expiration Only
```bash
# Expire sessions after platform connection changes
python3 scripts/maintenance/delete_user_data.py --user-id 1 --expire-sessions-only
```

## Security Considerations

- User deletion is irreversible - ensure you have proper authorization
- All deletion operations are logged for audit purposes
- Sensitive data (like platform credentials) is securely removed
- Sessions are immediately expired to prevent unauthorized access
- File deletion includes secure removal of cached credentials

## Integration with Other Tools

The user deletion functionality integrates with:
- **Data cleanup tools**: Automatic orphan cleanup
- **Backup systems**: Can be run before deletion
- **Audit logging**: All deletions are logged
- **Session management**: Automatic session cleanup
- **Platform management**: Credential cleanup

For more information, see the individual script documentation and the main Vedfolnir documentation.