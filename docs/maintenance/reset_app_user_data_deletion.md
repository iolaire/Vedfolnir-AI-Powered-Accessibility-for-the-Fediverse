# Reset App User Data Deletion

## Overview

The `reset_app.py` script has been enhanced to include comprehensive user data deletion functionality, similar to the single-user `delete_user_data.py` script but applied to all users in the system.

## New Features

### Complete User Data Deletion

When using `--reset-complete`, the script now performs comprehensive data deletion for all users before resetting the database structure:

- **Posts and Images**: All posts and associated images (database records and files)
- **Platform Connections**: All user platform connections and encrypted credentials
- **Sessions**: Both Redis sessions and database session records
- **Caption Data**: Caption generation tasks and user settings
- **Processing Runs**: All processing run history
- **Audit Logs**: Job audit logs and GDPR audit logs
- **Storage Data**: Storage events and overrides
- **User Directories**: User-specific storage directories
- **Redis Cache**: All session and platform cache data

### New Command Options

#### `--delete-all-user-data`
Deletes all user data but keeps the database structure intact. Useful for clearing all user content while preserving system configuration.

```bash
# Preview what would be deleted
python scripts/maintenance/reset_app.py --delete-all-user-data --dry-run

# Actually delete all user data
python scripts/maintenance/reset_app.py --delete-all-user-data
```

#### Enhanced `--reset-complete`
Now includes comprehensive user data deletion before resetting the database structure.

```bash
# Preview complete reset including user data deletion
python scripts/maintenance/reset_app.py --reset-complete --dry-run

# Perform complete reset with user data deletion
python scripts/maintenance/reset_app.py --reset-complete
```

## Data Deletion Summary

The script provides detailed summaries of what will be or was deleted:

```
============================================================
DRY RUN SUMMARY
============================================================
Users Processed: 2
Posts: 5
Images (DB): 10
Image Files: 8
Processing Runs: 3
Platform Connections: 2
Caption Tasks: 1
Caption Settings: 1
DB Sessions: 4
Redis Sessions: 2
Job Audit Logs: 15
GDPR Audit Logs: 0
Storage Events: 0
Storage Overrides: 0
User Directories: 2
........................................
Total Items: 53
============================================================
```

## Safety Features

### Dry Run Mode
All operations support `--dry-run` to preview what would be deleted without actually performing the deletion.

### Confirmation Prompts
Destructive operations require confirmation unless `--force` is used.

### Redis Integration
- Automatically clears Redis sessions and platform cache data
- Handles Redis connection failures gracefully
- Provides detailed logging of cache clearing operations

## Usage Examples

### Preview User Data Deletion
```bash
python scripts/maintenance/reset_app.py --delete-all-user-data --dry-run
```

### Delete All User Data (Keep Database Structure)
```bash
python scripts/maintenance/reset_app.py --delete-all-user-data
```

### Complete Application Reset (Including User Data)
```bash
python scripts/maintenance/reset_app.py --reset-complete --dry-run  # Preview first
python scripts/maintenance/reset_app.py --reset-complete            # Actual reset
```

### Clear Only Redis Cache
```bash
python scripts/maintenance/reset_app.py --clear-redis --dry-run
python scripts/maintenance/reset_app.py --clear-redis
```

## Implementation Details

The user data deletion functionality is implemented in the `delete_all_user_data()` method of the `AppResetManager` class. It:

1. **Iterates through all users** in the database
2. **Deletes data systematically** for each user following the same pattern as the single-user deletion script
3. **Handles foreign key constraints** by deleting in the correct order
4. **Clears Redis cache** comprehensively
5. **Removes user-specific directories** from the filesystem
6. **Provides detailed logging** and progress tracking

## Testing

The functionality includes comprehensive tests:

- **Unit tests** for individual methods
- **Integration tests** for command-line interface
- **Dry-run validation** to ensure safety

Run tests with:
```bash
python -m unittest tests.maintenance.test_reset_app_integration -v
```

## Security Considerations

- **Irreversible Operation**: User data deletion cannot be undone
- **Backup Recommended**: Always backup data before performing destructive operations
- **Confirmation Required**: Operations require explicit confirmation
- **Audit Trail**: All operations are logged for audit purposes

## Related Scripts

- `scripts/maintenance/delete_user_data.py` - Single user data deletion
- `scripts/maintenance/reset_app.py` - Application reset with user data deletion
- `scripts/setup/generate_env_secrets.py` - Environment setup after reset