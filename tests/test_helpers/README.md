# Test Helpers

This directory contains helper utilities for testing the Alt Text Bot application.

## Mock User Helper

The `MockUserHelper` class provides standardized utilities for creating and managing mock users and platform connections in tests.

### Quick Start

```python
import unittest
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from config import Config
from database import DatabaseManager
from models import UserRole

class TestMyFeature(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create mock user with platforms
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        # Always clean up mock users
        cleanup_test_user(self.user_helper)
    
    def test_my_feature(self):
        # Use self.test_user in your tests
        self.assertEqual(self.test_user.role, UserRole.REVIEWER)
        self.assertTrue(len(self.test_user.platform_connections) > 0)
```

### Features

- **Automatic Cleanup**: Tracks created users and platforms for automatic cleanup
- **Unique Identifiers**: Auto-generates unique usernames and emails to avoid conflicts
- **Platform Support**: Creates realistic platform connections with encrypted credentials
- **Flexible Configuration**: Supports custom user roles, platform configurations, and more
- **Session Safety**: Uses proper SQLAlchemy session management to avoid DetachedInstanceError

### API Reference

#### Convenience Functions

- `create_test_user_with_platforms(db_manager, username=None, role=UserRole.REVIEWER)` - Create a user with default platforms
- `cleanup_test_user(helper)` - Clean up all users created by a helper

#### MockUserHelper Class

- `create_mock_user(...)` - Create a mock user with optional platform connections
- `create_mock_platform(...)` - Create a mock platform connection
- `get_mock_user_by_username(username)` - Retrieve a user by username
- `cleanup_mock_users()` - Clean up all created users and platforms
- `cleanup_specific_user(user_id)` - Clean up a specific user

### Default Configurations

#### User Defaults
- **Password**: `test_password_123`
- **Role**: `UserRole.REVIEWER`
- **Status**: Active
- **Username**: Auto-generated as `test_user_{uuid}`
- **Email**: Auto-generated as `test_{uuid}@example.com`

#### Platform Defaults
- **Pixelfed**: `https://test-pixelfed-{uuid}.example.com` (default platform)
- **Mastodon**: `https://test-mastodon-{uuid}.example.com` (secondary platform)

### Standalone Scripts

For manual testing or test data setup:

```bash
# Create mock user
python tests/scripts/create_mock_user.py --username test_reviewer --role reviewer

# Clean up mock users
python tests/scripts/cleanup_mock_user.py
```

### Best Practices

1. **Always Use Helpers**: Never create users manually in tests
2. **Proper Cleanup**: Always clean up in `tearDown()` methods
3. **Unique Identifiers**: Let helpers generate unique usernames/emails
4. **Appropriate Roles**: Use roles that match your test scenarios
5. **Platform Testing**: Include platforms when testing session/auth features

### Requirements

- Valid `.env` file with database configuration
- `PLATFORM_ENCRYPTION_KEY` environment variable set
- Database tables created (run migrations if needed)

### Examples

See `tests/test_mock_user_example.py` for a complete example of proper usage.

### Troubleshooting

**DetachedInstanceError**: The helpers use eager loading to prevent this. If you still encounter it, ensure you're using the returned user object from the helper.

**Unique Constraint Errors**: Let the helper auto-generate usernames instead of providing fixed ones.

**Encryption Errors**: Ensure `PLATFORM_ENCRYPTION_KEY` is set in your `.env` file.

**Database Errors**: Verify your database configuration and that tables exist.