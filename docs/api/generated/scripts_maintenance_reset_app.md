# scripts.maintenance.reset_app

Complete Application Reset Script for Vedfolnir

This script provides various levels of application reset, from cleaning up old data
to completely resetting the application to a fresh state.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/maintenance/reset_app.py`

## Classes

### AppResetManager

```python
class AppResetManager
```

Manages different levels of application reset

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### reset_database_only

```python
def reset_database_only(self, dry_run)
```

Reset only the database, keeping files

**Type:** Instance method

#### reset_storage_only

```python
def reset_storage_only(self, dry_run)
```

Reset only storage files, keeping database

**Type:** Instance method

#### reset_complete

```python
def reset_complete(self, dry_run)
```

Complete application reset - database and storage

**Type:** Instance method

#### cleanup_old_data

```python
def cleanup_old_data(self, dry_run)
```

Clean up old data using retention policies (non-destructive)

**Type:** Instance method

#### reset_user_data

```python
def reset_user_data(self, user_id, dry_run)
```

Reset data for a specific user

**Type:** Instance method

#### show_status

```python
def show_status(self)
```

Show current application status

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main entry point

