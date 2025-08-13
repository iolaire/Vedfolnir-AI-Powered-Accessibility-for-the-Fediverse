# scripts.setup.add_original_post_date_column

Database migration script to add original_post_date column to images table.

This script adds a new column to store the original Pixelfed post creation date,
which will be used for proper chronological sorting in the review interfaces.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/setup/add_original_post_date_column.py`

## Functions

### migrate_database

```python
def migrate_database()
```

Add original_post_date column to images table

### verify_migration

```python
def verify_migration()
```

Verify that the migration was successful

