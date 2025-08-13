# migrations.add_caption_generation_tables

Database migration script to add caption generation tables.

This script adds the following tables:
- caption_generation_tasks: Tracks caption generation tasks
- caption_generation_user_settings: Stores user-specific settings per platform

Usage:
    python migrations/add_caption_generation_tables.py

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/migrations/add_caption_generation_tables.py`

## Functions

### run_migration

```python
def run_migration()
```

Run the migration to add caption generation tables

### verify_migration

```python
def verify_migration()
```

Verify that the migration was successful

