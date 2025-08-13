# tests.scripts.create_mock_user

Test Create Mock User Script

This script creates a mock user with platform connections for testing purposes.
It can be used standalone or imported into test files.

Usage:
    python tests/scripts/create_mock_user.py [--username USERNAME] [--role ROLE] [--no-platforms]
    
Examples:
    python tests/scripts/create_mock_user.py
    python tests/scripts/create_mock_user.py --username test_reviewer --role reviewer
    python tests/scripts/create_mock_user.py --username test_admin --role admin --no-platforms

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/scripts/create_mock_user.py`

## Functions

### create_mock_user

```python
def create_mock_user(username, role, with_platforms)
```

Create a mock user for testing.

Args:
    username: Username for the user (auto-generated if None)
    role: User role
    with_platforms: Whether to create platform connections
    
Returns:
    Tuple of (user, helper) for cleanup

### main

```python
def main()
```

Main function for command line usage

