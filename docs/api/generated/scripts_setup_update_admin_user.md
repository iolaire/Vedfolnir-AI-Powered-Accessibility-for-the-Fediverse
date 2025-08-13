# scripts.setup.update_admin_user

Admin user management tool.

This script allows you to create, update, or manage admin users in the database.
Admin credentials are stored in the database, not in environment variables.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/setup/update_admin_user.py`

## Functions

### generate_secure_password

```python
def generate_secure_password(length)
```

Generate a secure password

### list_admin_users

```python
def list_admin_users(db_manager)
```

List all admin users

### create_admin_user

```python
def create_admin_user(db_manager)
```

Create a new admin user interactively

### update_admin_user

```python
def update_admin_user(db_manager, admin_users)
```

Update an existing admin user

### main

```python
def main()
```

