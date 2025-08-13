# scripts.maintenance.data_cleanup

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/maintenance/data_cleanup.py`

## Classes

### DataCleanupManager

```python
class DataCleanupManager
```

Manages data cleanup operations for the Vedfolnir database

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager, config: Config)
```

**Type:** Instance method

#### _load_retention_config

```python
def _load_retention_config(self)
```

Load retention configuration from environment variables

**Type:** Instance method

#### archive_old_processing_runs

```python
def archive_old_processing_runs(self, days, dry_run)
```

Archive processing runs older than the specified number of days

**Type:** Instance method

#### cleanup_old_images

```python
def cleanup_old_images(self, status, days, dry_run)
```

Clean up old images with the specified status

**Type:** Instance method

#### cleanup_orphaned_posts

```python
def cleanup_orphaned_posts(self, dry_run)
```

Clean up posts that have no associated images

**Type:** Instance method

#### cleanup_user_data

```python
def cleanup_user_data(self, user_id, dry_run)
```

Clean up all data for a specific user

**Type:** Instance method

#### cleanup_orphan_processing_runs

```python
def cleanup_orphan_processing_runs(self, hours, dry_run)
```

Clean up orphan processing runs that are stuck or abandoned

**Type:** Instance method

#### cleanup_storage_images

```python
def cleanup_storage_images(self, dry_run)
```

Clean up all stored images from the storage directory

**Type:** Instance method

#### cleanup_log_files

```python
def cleanup_log_files(self, dry_run)
```

Clean up log files

**Type:** Instance method

#### run_full_cleanup

```python
def run_full_cleanup(self, dry_run)
```

Run all cleanup operations including database, storage, and logs

**Type:** Instance method

## Functions

### parse_args

```python
def parse_args()
```

Parse command line arguments

### main

```python
def main()
```

Main entry point

