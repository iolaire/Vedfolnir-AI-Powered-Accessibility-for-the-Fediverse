# scripts.setup.init_admin_user

Initialize the first admin user for the Vedfolnir web interface.
This script should be run once after setting up the database.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/setup/init_admin_user.py`

## Functions

### create_or_update_admin_user

```python
def create_or_update_admin_user(db_manager, username, email, password)
```

Create an admin user if one doesn't exist, or update existing one

### main

```python
def main()
```

Main function

