# tests.test_helpers.mock_user_helper

Mock User Helper for Testing

This module provides utilities for creating and managing mock users and platform connections
for testing purposes. It ensures consistent test data setup and cleanup across all tests
that involve user sessions and platforms.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_helpers/mock_user_helper.py`

## Constants

- `TEST_USER_DEFAULTS`
- `TEST_PLATFORM_DEFAULTS`

## Classes

### MockUserHelper

```python
class MockUserHelper
```

Helper class for creating and managing mock users in tests

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager)
```

Initialize the mock user helper.

Args:
    db_manager: DatabaseManager instance for database operations

**Type:** Instance method

#### create_mock_user

```python
def create_mock_user(self, username: Optional[str], email: Optional[str], password: str, role: UserRole, is_active: bool, with_platforms: bool, platform_configs: Optional[List[Dict[str, Any]]]) -> User
```

Create a mock user for testing.

Args:
    username: Username (auto-generated if None)
    email: Email address (auto-generated if None)
    password: Password for the user
    role: User role
    is_active: Whether user is active
    with_platforms: Whether to create platform connections
    platform_configs: List of platform configuration dicts
    
Returns:
    Created User object

**Type:** Instance method

#### create_mock_platform

```python
def create_mock_platform(self, user_id: int, name: str, platform_type: str, instance_url: str, username: str, access_token: str, client_key: Optional[str], client_secret: Optional[str], is_default: bool, is_active: bool, session: Optional[Session]) -> PlatformConnection
```

Create a mock platform connection for testing.

Args:
    user_id: ID of the user to associate with
    name: Platform connection name
    platform_type: Type of platform (pixelfed, mastodon)
    instance_url: URL of the platform instance
    username: Username on the platform
    access_token: Access token for API access
    client_key: Optional client key
    client_secret: Optional client secret
    is_default: Whether this is the default platform
    is_active: Whether platform is active
    session: Optional existing session to use
    
Returns:
    Created PlatformConnection object

**Type:** Instance method

#### get_mock_user_by_username

```python
def get_mock_user_by_username(self, username: str) -> Optional[User]
```

Get a mock user by username.

Args:
    username: Username to search for
    
Returns:
    User object if found, None otherwise

**Type:** Instance method

#### cleanup_mock_users

```python
def cleanup_mock_users(self)
```

Clean up all created mock users and their associated data

**Type:** Instance method

#### cleanup_specific_user

```python
def cleanup_specific_user(self, user_id: int)
```

Clean up a specific user and their associated data.

Args:
    user_id: ID of the user to clean up

**Type:** Instance method

#### get_created_user_count

```python
def get_created_user_count(self) -> int
```

Get the number of users created by this helper

**Type:** Instance method

#### get_created_platform_count

```python
def get_created_platform_count(self) -> int
```

Get the number of platforms created by this helper

**Type:** Instance method

## Functions

### create_test_user_with_platforms

```python
def create_test_user_with_platforms(db_manager: DatabaseManager, username: Optional[str], role: UserRole) -> tuple[User, MockUserHelper]
```

Convenience function to create a test user with default platforms.

Args:
    db_manager: DatabaseManager instance
    username: Optional username (auto-generated if None)
    role: User role
    
Returns:
    Tuple of (User object, MockUserHelper instance for cleanup)

### cleanup_test_user

```python
def cleanup_test_user(helper: MockUserHelper)
```

Convenience function to clean up test users.

Args:
    helper: MockUserHelper instance to clean up

