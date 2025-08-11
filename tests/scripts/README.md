# Test Scripts

This directory contains standalone scripts for creating and managing mock users for testing purposes.

## Scripts

### Create Mock User (`create_mock_user.py`)

Creates a mock user with platform connections for testing.

```bash
# Create user with default settings
python tests/scripts/create_mock_user.py

# Create user with specific username and role
python tests/scripts/create_mock_user.py --username test_reviewer --role reviewer

# Create admin user without platforms
python tests/scripts/create_mock_user.py --username test_admin --role admin --no-platforms

# Enable verbose logging
python tests/scripts/create_mock_user.py --username test_user --verbose
```

**Options:**
- `--username`: Username for the mock user (auto-generated if not provided)
- `--role`: User role (admin, moderator, reviewer, viewer) - default: reviewer
- `--no-platforms`: Do not create platform connections
- `--verbose, -v`: Enable verbose logging

### Cleanup Mock User (`cleanup_mock_user.py`)

Cleans up mock users and their associated data.

```bash
# Clean up last created user
python tests/scripts/cleanup_mock_user.py

# Clean up specific user by ID
python tests/scripts/cleanup_mock_user.py --user-id 123

# Clean up all test users (with confirmation)
python tests/scripts/cleanup_mock_user.py --all

# Enable verbose logging
python tests/scripts/cleanup_mock_user.py --verbose
```

**Options:**
- `--user-id`: ID of specific user to clean up
- `--all`: Clean up all test users (requires confirmation)
- `--last`: Clean up last created user (default behavior)
- `--verbose, -v`: Enable verbose logging

## Usage Examples

### Manual Testing Setup

```bash
# Create a test user for manual testing
python tests/scripts/create_mock_user.py --username manual_test_user --role reviewer

# ... perform manual testing ...

# Clean up when done
python tests/scripts/cleanup_mock_user.py
```

### Development Environment Setup

```bash
# Create admin user for development
python tests/scripts/create_mock_user.py --username dev_admin --role admin

# Create reviewer user for testing review features
python tests/scripts/create_mock_user.py --username dev_reviewer --role reviewer

# Clean up all test users when done
python tests/scripts/cleanup_mock_user.py --all
```

### Automated Testing

```bash
# In a test script or CI/CD pipeline
python tests/scripts/create_mock_user.py --username ci_test_user --role reviewer
# ... run tests ...
python tests/scripts/cleanup_mock_user.py --user-id $(cat tests/scripts/.last_created_user.txt | head -1)
```

## Features

- **Automatic Tracking**: Saves information about created users for easy cleanup
- **Flexible Configuration**: Support for different roles and platform setups
- **Safe Cleanup**: Confirmation prompts for bulk operations
- **Verbose Logging**: Detailed output for debugging
- **Error Handling**: Graceful handling of database and configuration errors

## Requirements

- Valid `.env` file with database configuration
- `PLATFORM_ENCRYPTION_KEY` environment variable set
- Database tables created (run migrations if needed)
- Python dependencies installed (`pip install -r requirements.txt`)

## Files Created

- `.last_created_user.txt`: Tracks the last created user for cleanup (automatically managed)

## Integration with Test Framework

These scripts use the same `MockUserHelper` class as the test framework, ensuring consistency between manual and automated testing.

For programmatic usage in tests, use the helper classes directly:

```python
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
```

See `tests/test_helpers/README.md` for the full API documentation.