# migrations.remove_user_sessions

Database Migration: Remove UserSession table

This migration removes the user_sessions table since we're moving to Flask-based
session management using secure cookies instead of database storage.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/migrations/remove_user_sessions.py`

## Functions

### upgrade

```python
def upgrade(db_session)
```

Remove the user_sessions table

### downgrade

```python
def downgrade(db_session)
```

Recreate the user_sessions table (for rollback)

