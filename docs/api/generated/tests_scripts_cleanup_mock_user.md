# tests.scripts.cleanup_mock_user

Test Cleanup Mock User Script

This script cleans up mock users and their associated data created for testing purposes.
It can clean up the last created user or specific users by ID.

Usage:
    python tests/scripts/cleanup_mock_user.py [--user-id USER_ID] [--all] [--last]
    
Examples:
    python tests/scripts/cleanup_mock_user.py                    # Clean up last created user
    python tests/scripts/cleanup_mock_user.py --user-id 123     # Clean up specific user
    python tests/scripts/cleanup_mock_user.py --all             # Clean up all test users

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/scripts/cleanup_mock_user.py`

## Functions

### cleanup_last_created_user

```python
def cleanup_last_created_user()
```

Clean up the last created user based on saved info

### cleanup_specific_user

```python
def cleanup_specific_user(user_id)
```

Clean up a specific user by ID

### cleanup_all_test_users

```python
def cleanup_all_test_users()
```

Clean up all users that appear to be test users

### main

```python
def main()
```

Main function for command line usage

