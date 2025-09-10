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
from app.core.database.core.database_manager import DatabaseManager

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

## Unified Session Testing

**IMPORTANT**: All session-related tests must use the unified session manager. Legacy `SessionManager` has been deprecated.

### Using UnifiedSessionManager in Tests

```python
import unittest
from unified_session_manager import UnifiedSessionManager, get_current_platform_context
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from config import Config
from app.core.database.core.database_manager import DatabaseManager

class TestUnifiedSessions(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures with unified session manager"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create mock user with platforms for session testing
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_session_user",
            role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
    
    def test_session_creation(self):
        """Test unified session creation"""
        # Create session with user and platform
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.session_manager.create_session(
            self.test_user.id, 
            platform_id
        )
        self.assertIsNotNone(session_id)
        
        # Test session context retrieval
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['user_id'], self.test_user.id)
        self.assertEqual(context['platform_connection_id'], platform_id)
    
    def test_session_validation(self):
        """Test session validation"""
        # Create and validate session
        session_id = self.session_manager.create_session(self.test_user.id)
        self.assertTrue(self.session_manager.validate_session(session_id))
        
        # Test invalid session
        self.assertFalse(self.session_manager.validate_session("invalid_session"))
    
    def test_platform_context_functions(self):
        """Test platform context functions"""
        # Note: These functions require Flask request context
        # Use Flask test client for full integration testing
        from unified_session_manager import (
            get_current_platform_context,
            get_current_platform,
            get_current_user_from_context,
            switch_platform_context
        )
        
        # Verify functions are callable
        self.assertTrue(callable(get_current_platform_context))
        self.assertTrue(callable(get_current_platform))
        self.assertTrue(callable(get_current_user_from_context))
        self.assertTrue(callable(switch_platform_context))
```

### Session Integration Testing

For tests that require Flask request context:

```python
import unittest
from flask import Flask
from unified_session_manager import UnifiedSessionManager

class TestSessionIntegration(unittest.TestCase):
    def setUp(self):
        """Set up Flask app for integration testing"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Initialize session manager
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Store in app context
        self.app.unified_session_manager = self.session_manager
    
    def test_session_with_flask_context(self):
        """Test session operations within Flask request context"""
        with self.app.test_request_context():
            # Test session operations that require Flask context
            pass
```

### Migration Guidelines for Existing Tests

When updating existing tests to use UnifiedSessionManager:

1. **Replace Imports**:
   ```python
   # OLD
   from app.core.session.core.session_manager import SessionManager
   
   # NEW
   from unified_session_manager import UnifiedSessionManager
   ```

2. **Update Instantiation**:
   ```python
   # OLD
   self.session_manager = SessionManager(self.db_manager)
   
   # NEW
   self.session_manager = UnifiedSessionManager(self.db_manager)
   ```

3. **Update Method Calls**: Most methods remain the same, but verify signatures
4. **Add Platform Context**: Include platform_connection_id in session creation
5. **Use Mock Users**: Always use standardized mock user helpers

### Database Session Testing Patterns

**IMPORTANT**: All database operations in tests should use unified session management patterns. Direct `db_manager.get_session()` usage is deprecated.

#### Pattern 1: Testing with UnifiedSessionManager
```python
import unittest
from unified_session_manager import UnifiedSessionManager
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from config import Config
from app.core.database.core.database_manager import DatabaseManager

class TestDatabaseOperations(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures with unified session manager"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create mock user with platforms for testing
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_user",
            role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
    
    def test_database_operation(self):
        """Test database operations using unified session manager"""
        with self.session_manager.get_db_session() as session:
            # Database operations with automatic cleanup
            result = session.query(Model).filter_by(user_id=self.test_user.id).all()
            self.assertIsNotNone(result)
```

#### Pattern 2: Testing with RequestSessionManager
```python
from request_scoped_session_manager import RequestScopedSessionManager

class TestSimpleOperations(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.request_session_manager = RequestScopedSessionManager(self.db_manager)
    
    def test_simple_query(self):
        """Test simple database queries"""
        with self.request_session_manager.session_scope() as session:
            result = session.query(Model).count()
            self.assertIsInstance(result, int)
```

#### Pattern 3: Testing Service Classes
```python
class TestServiceClass(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = UnifiedSessionManager(self.db_manager)
        self.service = SomeService(self.db_manager, self.session_manager)
    
    def test_service_operation(self):
        """Test service operations with proper session management"""
        result = self.service.get_data()
        self.assertIsNotNone(result)
```

### Migration Guidelines for Tests

When updating existing tests that use direct database sessions:

1. **Replace Direct Usage**:
   ```python
   # OLD - Don't use
   session = self.db_manager.get_session()
   try:
       result = session.query(Model).all()
   finally:
       session.close()
   
   # NEW - Use unified patterns
   with self.session_manager.get_db_session() as session:
       result = session.query(Model).all()
   ```

2. **Add Session Manager to setUp**:
   ```python
   def setUp(self):
       self.config = Config()
       self.db_manager = DatabaseManager(self.config)
       self.session_manager = UnifiedSessionManager(self.db_manager)  # Add this
   ```

3. **Use Appropriate Pattern**: Choose between UnifiedSessionManager and RequestSessionManager based on test requirements

### Required Test Dependencies for Database Sessions

```python
# Core testing imports for database sessions
from unified_session_manager import UnifiedSessionManager
from request_scoped_session_manager import RequestScopedSessionManager
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import UserRole
```