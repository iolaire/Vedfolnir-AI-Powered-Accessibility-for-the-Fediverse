# Testing Guidelines

## Test File Organization

All test files must be organized in appropriate subdirectories within `/tests`. Never place test files in the root directory.

### Test Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
├── integration/             # Integration tests for workflows
├── frontend/                # Web interface and UI tests
├── security/                # Security-focused tests
├── performance/             # Performance and load tests
├── scripts/                 # Test utilities and helper scripts
└── test_helpers.py          # Shared test helper functions
```

### Test File Placement Guidelines

#### Unit Tests (`tests/unit/`)
- Individual module/class testing
- Database model tests
- Configuration validation tests
- Utility function tests
- Examples: `test_config_validation.py`, `test_database_models.py`

#### Integration Tests (`tests/integration/`)
- End-to-end workflow testing
- Session management tests
- Platform integration tests
- Multi-component interaction tests
- Examples: `test_session_management.py`, `test_platform_workflows.py`

#### Frontend Tests (`tests/frontend/`)
- Web interface tests
- Form validation tests
- JavaScript functionality tests
- UI component tests
- Examples: `test_web_interface.py`, `test_form_validation.py`

#### Security Tests (`tests/security/`)
- Authentication tests
- Authorization tests
- CSRF protection tests
- Input validation tests
- Examples: `test_auth_security.py`, `test_csrf_protection.py`

#### Performance Tests (`tests/performance/`)
- Load testing
- Stress testing
- Performance benchmarks
- Resource usage tests
- Examples: `test_performance_benchmarks.py`, `test_load_testing.py`

#### Test Scripts (`tests/scripts/`)
- Test data setup scripts
- Mock user management scripts
- Test environment utilities
- Examples: `create_mock_user.py`, `cleanup_mock_user.py`

### Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*` (e.g., `TestUserAuthentication`)
- Test methods: `test_*` (e.g., `test_user_login_success`)
- Helper scripts: Descriptive names without `test_` prefix

## Mock User Management for Tests

When writing tests that involve user sessions, authentication, or platform connections, always use the standardized mock user helpers to ensure consistent test data and proper cleanup.

### Using Mock User Helpers

#### In Test Files

```python
import unittest
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from config import Config
from database import DatabaseManager

class TestUserSessions(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create mock user with platforms
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_session_user",
            role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Always clean up mock users
        cleanup_test_user(self.user_helper)
    
    def test_user_session_functionality(self):
        """Test user session functionality"""
        # Use self.test_user in your tests
        self.assertEqual(self.test_user.username, "test_session_user")
        self.assertTrue(len(self.test_user.platform_connections) > 0)
```

#### Advanced Usage

```python
from tests.test_helpers import MockUserHelper
from models import UserRole

class TestAdvancedUserScenarios(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.user_helper = MockUserHelper(self.db_manager)
    
    def tearDown(self):
        # Clean up all created users
        self.user_helper.cleanup_mock_users()
    
    def test_multiple_users(self):
        """Test scenarios with multiple users"""
        # Create admin user
        admin_user = self.user_helper.create_mock_user(
            username="test_admin",
            role=UserRole.ADMIN,
            with_platforms=True
        )
        
        # Create reviewer user with custom platforms
        platform_configs = [{
            'name': 'Custom Pixelfed',
            'platform_type': 'pixelfed',
            'instance_url': 'https://custom.pixelfed.social',
            'username': 'custom_user',
            'access_token': 'custom_token',
            'is_default': True
        }]
        
        reviewer_user = self.user_helper.create_mock_user(
            username="test_reviewer",
            role=UserRole.REVIEWER,
            platform_configs=platform_configs
        )
        
        # Test functionality with both users
        self.assertEqual(admin_user.role, UserRole.ADMIN)
        self.assertEqual(reviewer_user.role, UserRole.REVIEWER)
```

### Standalone Scripts

For manual testing or test data setup, use the standalone scripts:

#### Create Mock User
```bash
# Create user with default settings
python tests/scripts/create_mock_user.py

# Create user with specific username and role
python tests/scripts/create_mock_user.py --username test_reviewer --role reviewer

# Create admin user without platforms
python tests/scripts/create_mock_user.py --username test_admin --role admin --no-platforms
```

#### Cleanup Mock User
```bash
# Clean up last created user
python tests/scripts/cleanup_mock_user.py

# Clean up specific user by ID
python tests/scripts/cleanup_mock_user.py --user-id 123

# Clean up all test users (with confirmation)
python tests/scripts/cleanup_mock_user.py --all
```

### Test Data Standards

#### Default Test User Configuration
- **Username**: Auto-generated as `test_user_{uuid}`
- **Email**: Auto-generated as `test_{uuid}@example.com`
- **Password**: `test_password_123`
- **Role**: `UserRole.REVIEWER`
- **Status**: Active

#### Default Platform Configurations
- **Pixelfed**: `https://test-pixelfed-{uuid}.example.com` (default platform)
- **Mastodon**: `https://test-mastodon-{uuid}.example.com` (secondary platform)

### Best Practices

1. **Always Use Helpers**: Never create users manually in tests - always use the mock user helpers
2. **Proper Cleanup**: Always clean up mock users in `tearDown()` methods
3. **Unique Identifiers**: Let the helper generate unique usernames/emails to avoid conflicts
4. **Consistent Roles**: Use appropriate roles for your test scenarios
5. **Platform Testing**: Include platform connections when testing session/authentication features

### Required Imports

```python
# For basic user creation
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

# For advanced scenarios
from tests.test_helpers import MockUserHelper, TEST_USER_DEFAULTS, TEST_PLATFORM_DEFAULTS

# For user roles
from models import UserRole
```

### Environment Requirements

Mock user helpers require:
- Valid database configuration in `.env` file
- `PLATFORM_ENCRYPTION_KEY` set for platform credential encryption
- Database tables created (run migrations if needed)

### Error Handling

The mock user helpers include comprehensive error handling and logging. If user creation fails:
1. Check database connectivity
2. Verify encryption key is set
3. Ensure database tables exist
4. Check for unique constraint violations

### Integration with Existing Tests

When updating existing tests to use mock user helpers:
1. Replace manual user creation with helper calls
2. Add proper cleanup in `tearDown()`
3. Update assertions to use helper-created users
4. Ensure test isolation by using unique usernames

This standardized approach ensures consistent test data, proper cleanup, and reliable test execution across all test suites involving user sessions and platforms.