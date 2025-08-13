# scripts.setup.migrate_to_platform_aware

Platform-Aware Database Migration CLI

This script provides a command-line interface for migrating existing Vedfolnir
databases to support platform-aware operations with user-managed platform connections.

Usage:
    python migrate_to_platform_aware.py --up                    # Run migration
    python migrate_to_platform_aware.py --down                  # Rollback migration
    python migrate_to_platform_aware.py --status                # Check migration status
    python migrate_to_platform_aware.py --validate              # Validate migration
    python migrate_to_platform_aware.py --cleanup               # Clean up backup tables

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/setup/migrate_to_platform_aware.py`

## Functions

### setup_logging

```python
def setup_logging(level)
```

Set up logging configuration

### get_database_url_from_config

```python
def get_database_url_from_config()
```

Get database URL from configuration

### run_migration_up

```python
def run_migration_up(database_url: str, verbose: bool) -> bool
```

Run the migration to platform-aware schema.

Args:
    database_url: Database connection URL
    verbose: Enable verbose logging
    
Returns:
    True if successful, False otherwise

### run_migration_down

```python
def run_migration_down(database_url: str, verbose: bool) -> bool
```

Rollback the migration to previous state.

Args:
    database_url: Database connection URL
    verbose: Enable verbose logging
    
Returns:
    True if successful, False otherwise

### check_migration_status

```python
def check_migration_status(database_url: str, verbose: bool) -> bool
```

Check and display migration status.

Args:
    database_url: Database connection URL
    verbose: Enable verbose logging
    
Returns:
    True if successful, False otherwise

### validate_migration

```python
def validate_migration(database_url: str, verbose: bool) -> bool
```

Validate migration data integrity.

Args:
    database_url: Database connection URL
    verbose: Enable verbose logging
    
Returns:
    True if validation passes, False otherwise

### cleanup_backup_tables

```python
def cleanup_backup_tables(database_url: str, verbose: bool) -> bool
```

Clean up backup tables after successful migration.

Args:
    database_url: Database connection URL
    verbose: Enable verbose logging
    
Returns:
    True if successful, False otherwise

### main

```python
def main()
```

Main CLI entry point

