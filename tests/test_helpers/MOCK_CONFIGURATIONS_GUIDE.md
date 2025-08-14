# Standardized Mock Configurations Guide

This guide explains how to use the standardized mock configurations to address common testing issues including async operations, tuple unpacking, database query chains, and platform behavior simulation.

## Overview

The standardized mock configurations solve several common testing problems:

1. **Async Mock Issues**: Proper configuration of AsyncMock for async operations
2. **Tuple Unpacking**: Mock objects that support tuple/list unpacking operations
3. **Database Query Chains**: Proper mock configuration for SQLAlchemy query method chaining
4. **Platform Behavior**: Accurate simulation of platform-specific API behavior

## Quick Start

```python
import unittest
from tests.test_helpers import (
    StandardizedMockFactory,
    AsyncMockHelper,
    DatabaseMockHelper,
    PlatformMockHelper,
    create_pixelfed_test_setup
)

class TestMyFeature(unittest.TestCase):
    def test_with_standardized_mocks(self):
        # Create database session mock
        session_mock = StandardizedMockFactory.create_session_mock()
        
        # Create async HTTP client mock
        client_mock = AsyncMockHelper.create_async_http_client()
        
        # Create platform test setup
        user_mock, connection_mock, api_mock = create_pixelfed_test_setup()
        
        # Your test code here...
```

## Async Mock Configurations

### Basic Async Mock

```python
from tests.test_helpers import StandardizedMockFactory

# Create async mock with return value
async_mock = StandardizedMockFactory.create_async_mock(
    return_value={'success': True}
)

# Create async mock with side effect
async_mock_with_error = StandardizedMockFactory.create_async_mock(
    side_effect=Exception("Connection failed")
)
```

### HTTP Response Mocks

```python
from tests.test_helpers import AsyncMockHelper

# Successful HTTP response
response_mock = AsyncMockHelper.create_async_http_response(
    status_code=200,
    json_data={'data': 'test'}
)

# Failed HTTP response
error_response = AsyncMockHelper.create_async_http_response(
    status_code=500,
    json_data={'error': 'Server error'}
)
```

### HTTP Client Mocks

```python
from tests.test_helpers import AsyncMockHelper

# HTTP client with successful responses
client_mock = AsyncMockHelper.create_async_http_client(
    responses=[response_mock]
)

# HTTP client with connection errors
client_mock = AsyncMockHelper.create_async_http_client(
    side_effects=[httpx.ConnectError("Connection refused")]
)
```

## Database Mock Configurations

### Query Chain Mocks

```python
from tests.test_helpers import DatabaseMockHelper

# Query mock with single result
query_mock = DatabaseMockHelper.create_query_chain_mock(
    final_result={'id': 1, 'name': 'test'}
)

# Query mock with list results
query_mock = DatabaseMockHelper.create_query_chain_mock(
    final_result=[{'id': 1}, {'id': 2}]
)

# Usage in tests
result = query_mock.filter().filter_by().order_by().first()
results = query_mock.filter().all()
count = query_mock.count()
```

### Session Mocks

```python
from tests.test_helpers import DatabaseMockHelper

# Basic session mock
session_mock = DatabaseMockHelper.create_session_mock()

# Session mock with query results
session_mock = DatabaseMockHelper.create_session_mock(
    query_results={
        'User': [{'id': 1, 'username': 'test'}],
        'PlatformConnection': [{'id': 1, 'platform_type': 'pixelfed'}]
    }
)

# Usage
with session_mock as session:
    user = session.query(User).first()
    session.add(user)
    session.commit()
```

### Query Builder Pattern

```python
from tests.test_helpers import QueryMockBuilder

# Build complex query mock
query_mock = (QueryMockBuilder()
             .filter({'id': 1})
             .filter_by()
             .order_by()
             .first({'id': 1, 'name': 'test'}))

# Use the built query
result = query_mock.filter().filter_by().order_by().first()
```

## Platform Mock Configurations

### Platform Connection Mocks

```python
from tests.test_helpers import PlatformMockHelper

# Pixelfed connection
pixelfed_mock = PlatformMockHelper.create_pixelfed_connection_mock(
    connection_id=1,
    user_id=1,
    is_default=True
)

# Mastodon connection
mastodon_mock = PlatformMockHelper.create_mastodon_connection_mock(
    connection_id=2,
    user_id=1,
    is_default=False
)
```

### Platform API Mocks

```python
from tests.test_helpers import PlatformMockHelper

# Pixelfed API mock
pixelfed_api = PlatformMockHelper.create_activitypub_client_mock(
    platform_type='pixelfed',
    success=True
)

# Mastodon API mock
mastodon_api = PlatformMockHelper.create_activitypub_client_mock(
    platform_type='mastodon',
    success=True
)
```

### Complete Platform Test Setup

```python
from tests.test_helpers import create_pixelfed_test_setup, create_mastodon_test_setup

# Pixelfed test setup
user_mock, connection_mock, client_mock = create_pixelfed_test_setup(
    user_id=1,
    success=True
)

# Mastodon test setup
user_mock, connection_mock, client_mock = create_mastodon_test_setup(
    user_id=1,
    success=True
)
```

## Tuple Unpacking Support

### Mock with Unpacking

```python
from tests.test_helpers import create_mock_with_unpacking

# Create mock that supports unpacking
items = ['item1', 'item2', 'item3']
mock = create_mock_with_unpacking(items)

# Use unpacking
for item in mock:
    print(item)  # Works correctly

# Use indexing
first_item = mock[0]  # Works correctly

# Use length
count = len(mock)  # Works correctly
```

### Database Query with Unpacking

```python
from tests.test_helpers import DatabaseMockHelper

# Query mock with unpacking support
query_mock = DatabaseMockHelper.create_query_chain_mock(
    final_result=['item1', 'item2', 'item3'],
    supports_unpacking=True
)

# Use unpacking
items = list(query_mock.all())
first_item = query_mock.all()[0]
```

## Model Mock Configurations

### User Mocks

```python
from tests.test_helpers import StandardizedMockFactory
from models import UserRole

# User mock with platforms
user_mock = StandardizedMockFactory.create_user_mock(
    user_id=1,
    username='testuser',
    role=UserRole.ADMIN,
    with_platforms=True
)

# Access platforms
platforms = user_mock.platform_connections
default_platform = user_mock.get_default_platform()
```

### Task Mocks

```python
from tests.test_helpers import StandardizedMockFactory
from models import TaskStatus

# Task mock
task_mock = StandardizedMockFactory.create_task_mock(
    task_id='test-task-123',
    user_id=1,
    status=TaskStatus.RUNNING,
    can_be_cancelled=True
)

# Check task properties
can_cancel = task_mock.can_be_cancelled()
status = task_mock.status
```

## Patching with Standardized Mocks

### Database Patching

```python
from tests.test_helpers import patch_database_session, patch_database_manager

class TestWithDatabaseMocks(unittest.TestCase):
    @patch_database_session()
    def test_with_session_patch(self, session_mock):
        # Your test code here
        pass
    
    @patch_database_manager()
    def test_with_db_manager_patch(self, db_manager_mock):
        # Your test code here
        pass
```

### HTTP Client Patching

```python
from tests.test_helpers import patch_httpx_client, patch_ollama_client

class TestWithHTTPMocks(unittest.TestCase):
    @patch_httpx_client()
    def test_with_http_client(self, client_mock):
        # Your test code here
        pass
    
    @patch_ollama_client(success=True, response_text='Test caption')
    def test_with_ollama_client(self, client_mock):
        # Your test code here
        pass
```

### Platform Patching

```python
from tests.test_helpers import patch_platform_context_manager, patch_activitypub_client

class TestWithPlatformMocks(unittest.TestCase):
    @patch_platform_context_manager()
    def test_with_platform_context(self, context_manager_mock):
        # Your test code here
        pass
    
    @patch_activitypub_client(platform_type='pixelfed', success=True)
    def test_with_activitypub_client(self, client_mock):
        # Your test code here
        pass
```

## Common Patterns

### Task Queue Manager Testing

```python
from tests.test_helpers import DatabaseMockHelper, StandardizedMockFactory
from unittest.mock import patch

class TestTaskQueueManager(unittest.TestCase):
    @patch('database.DatabaseManager')
    def test_enqueue_task(self, mock_db_manager_class):
        # Create standardized mocks
        session_mock = DatabaseMockHelper.create_session_mock()
        db_manager_mock = DatabaseMockHelper.create_database_manager_mock(session_mock)
        mock_db_manager_class.return_value = db_manager_mock
        
        # Create task mock
        task_mock = StandardizedMockFactory.create_task_mock()
        
        # Configure query to return no existing tasks
        query_mock = DatabaseMockHelper.create_query_chain_mock(final_result=None)
        session_mock.query.return_value = query_mock
        
        # Your test logic here
```

### Platform Integration Testing

```python
from tests.test_helpers import create_pixelfed_test_setup, AsyncMockHelper

class TestPlatformIntegration(unittest.TestCase):
    def test_pixelfed_integration(self):
        # Create complete test setup
        user_mock, connection_mock, client_mock = create_pixelfed_test_setup(
            user_id=1,
            success=True
        )
        
        # Configure additional responses if needed
        posts_response = AsyncMockHelper.create_async_http_response(
            status_code=200,
            json_data={'data': [{'id': '123', 'content': 'test'}]}
        )
        client_mock.get.return_value = posts_response
        
        # Your test logic here
```

### Async Operation Testing

```python
from tests.test_helpers import AsyncMockHelper, AsyncTestHelper

class TestAsyncOperations(unittest.TestCase):
    def test_async_operation(self):
        # Create async mocks
        client_mock = AsyncMockHelper.create_ollama_api_mock(
            success=True,
            response_text='Generated caption'
        )
        
        # Define async test function
        async def async_test():
            # Your async test logic here
            result = await client_mock.post('/api/generate')
            return result
        
        # Run async test
        result = AsyncTestHelper.run_async_test(async_test)
        
        # Assertions
        self.assertIsNotNone(result)
```

## Best Practices

1. **Use Appropriate Mock Types**: Choose the right mock type for your use case (sync vs async, with/without unpacking)

2. **Configure Realistic Behavior**: Set up mocks to behave like the real objects they're replacing

3. **Handle Error Cases**: Test both success and failure scenarios with appropriate mock configurations

4. **Use Builders for Complex Queries**: Use QueryMockBuilder for complex database query chains

5. **Leverage Test Setup Helpers**: Use convenience functions like `create_pixelfed_test_setup()` for common scenarios

6. **Patch at the Right Level**: Patch at the appropriate level (class, method, or module) for your test

7. **Clean Up Properly**: Ensure mocks are properly cleaned up after tests

## Troubleshooting

### Common Issues and Solutions

**Issue**: Mock doesn't support tuple unpacking
**Solution**: Use `create_mock_with_unpacking()` or set `supports_unpacking=True`

**Issue**: Async mock not working correctly
**Solution**: Use `StandardizedMockFactory.create_async_mock()` or `AsyncMockHelper` methods

**Issue**: Database query chain not working
**Solution**: Use `DatabaseMockHelper.create_query_chain_mock()` with proper chaining support

**Issue**: Platform API mock missing methods
**Solution**: Use platform-specific mock helpers like `PlatformMockHelper.create_activitypub_client_mock()`

**Issue**: Session mock not behaving like real session
**Solution**: Use `StandardizedMockFactory.create_session_mock()` with context manager support

## Migration from Existing Mocks

To migrate existing tests to use standardized mocks:

1. **Identify Mock Types**: Determine what type of mocks you're currently using
2. **Replace with Standardized**: Replace manual mock creation with standardized factory methods
3. **Update Configurations**: Use the standardized configuration options
4. **Test Thoroughly**: Ensure the new mocks work correctly with your existing test logic
5. **Simplify Code**: Remove redundant mock configuration code

Example migration:

```python
# Before (manual mock configuration)
mock_session = Mock()
mock_query = Mock()
mock_filter = Mock()
mock_session.query.return_value = mock_query
mock_query.filter.return_value = mock_filter
mock_filter.first.return_value = test_result

# After (standardized mock)
mock_session = DatabaseMockHelper.create_session_mock(
    query_results={'User': test_result}
)
```

This standardized approach reduces boilerplate code, improves test reliability, and ensures consistent mock behavior across all tests.