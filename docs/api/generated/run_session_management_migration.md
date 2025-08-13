# run_session_management_migration

Session Management Migration Runner

This script applies the session management optimization migration to improve
database performance for user authentication, platform context loading, and
session management operations.

Usage:
    python run_session_management_migration.py [--dry-run] [--rollback]

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/run_session_management_migration.py`

## Classes

### SessionManagementMigration

```python
class SessionManagementMigration
```

Handles the session management optimization migration

**Methods:**

#### __init__

```python
def __init__(self, config: Config)
```

**Type:** Instance method

#### check_database_exists

```python
def check_database_exists(self)
```

Check if the database file exists

**Type:** Instance method

#### backup_database

```python
def backup_database(self)
```

Create a backup of the database before migration

**Type:** Instance method

#### get_existing_indexes

```python
def get_existing_indexes(self)
```

Get list of existing indexes

**Type:** Instance method

#### check_migration_needed

```python
def check_migration_needed(self)
```

Check if the migration is needed by looking for key indexes

**Type:** Instance method

#### apply_migration

```python
def apply_migration(self, dry_run)
```

Apply the session management optimization migration

**Type:** Instance method

#### rollback_migration

```python
def rollback_migration(self, dry_run)
```

Rollback the session management optimization migration

**Type:** Instance method

#### verify_migration

```python
def verify_migration(self)
```

Verify that the migration was applied correctly

**Type:** Instance method

#### show_migration_plan

```python
def show_migration_plan(self)
```

Show what the migration would do

**Type:** Instance method

#### show_rollback_plan

```python
def show_rollback_plan(self)
```

Show what the rollback would do

**Type:** Instance method

#### _get_upgrade_sql

```python
def _get_upgrade_sql(self)
```

Get the SQL statements for the upgrade

**Type:** Instance method

#### _get_downgrade_sql

```python
def _get_downgrade_sql(self)
```

Get the SQL statements for the downgrade

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main function to run the migration

