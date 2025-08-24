# Testing Authentication and Session Management

## Overview
This document provides standardized approaches for testing authenticated functionality in Vedfolnir. It covers login procedures, session creation, and best practices for testing admin and user features.

## Authentication Testing Patterns

### 1. Web Request Testing (Recommended)
Use this pattern for testing web routes that require authentication.

```python
#!/usr/bin/env python3
import requests
import sys
import re
from urllib.parse import urljoin

def create_authenticated_session(base_url="http://127.0.0.1:5000", username="admin"):
    """
    Create an authenticated session for testing
    
    Args:
        base_url: The base URL of the web application
        username: Username to login with (default: admin)
    
    Returns:
        tuple: (session, success) where session is requests.Session and success is bool
    """
    session = requests.Session()
    
    # Step 1: Get login page and CSRF token
    print(f"Getting login page for user: {username}")
    login_page = session.get(urljoin(base_url, "/login"))
    if login_page.status_code != 200:
        print(f"❌ Failed to get login page: {login_page.status_code}")
        return session, False
    
    # Extract CSRF token from meta tag
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token in login page")
        return session, False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Got CSRF token: {csrf_token[:20]}...")
    
    # Step 2: Prompt for password
    import getpass
    password = getpass.getpass(f"Enter password for {username}: ")
    
    # Step 3: Login
    print(f"Logging in as {username}...")
    login_data = {
        'username_or_email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    
    # Check if login was successful
    if login_response.status_code == 302:
        print("✅ Successfully logged in (redirected)")
        return session, True
    elif login_response.status_code == 200:
        if 'login' in login_response.url.lower():
            print("❌ Login failed: Still on login page")
            return session, False
        else:
            print("✅ Successfully logged in")
            return session, True
    else:
        print(f"❌ Login failed: {login_response.status_code}")
        return session, False

def test_authenticated_route(route_path, method="GET", data=None, expected_status=200):
    """
    Test an authenticated route
    
    Args:
        route_path: The route to test (e.g., "/admin/maintenance/pause-system")
        method: HTTP method (GET, POST, etc.)
        data: Form data for POST requests
        expected_status: Expected HTTP status code
    
    Returns:
        bool: True if test passed, False otherwise
    """
    session, login_success = create_authenticated_session()
    if not login_success:
        return False
    
    # Test the route
    print(f"Testing {method} {route_path}...")
    if method.upper() == "GET":
        response = session.get(urljoin("http://127.0.0.1:5000", route_path))
    elif method.upper() == "POST":
        response = session.post(urljoin("http://127.0.0.1:5000", route_path), data=data)
    else:
        print(f"❌ Unsupported method: {method}")
        return False
    
    if response.status_code == expected_status:
        print(f"✅ Route test passed: {response.status_code}")
        return True
    else:
        print(f"❌ Route test failed: {response.status_code} (expected {expected_status})")
        return False
```

### 2. Direct Database Testing
Use this pattern for testing business logic that requires user context.

```python
from dotenv import load_dotenv
from config import Config
from database import DatabaseManager
from models import User, UserRole
import getpass

def get_test_user(username="admin"):
    """
    Get a user from the database for testing
    
    Args:
        username: Username to retrieve
    
    Returns:
        User: User object or None if not found
    """
    load_dotenv()
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user:
            print(f"✅ Found user: {user.username} ({user.role.value})")
            return user
        else:
            print(f"❌ User not found: {username}")
            return None

def verify_user_credentials(username="admin"):
    """
    Verify user credentials interactively
    
    Args:
        username: Username to verify
    
    Returns:
        bool: True if credentials are valid
    """
    from services.user_management_service import UserManagementService
    
    load_dotenv()
    config = Config()
    db_manager = DatabaseManager(config)
    user_service = UserManagementService(db_manager)
    
    password = getpass.getpass(f"Enter password for {username}: ")
    
    try:
        user = user_service.authenticate_user(username, password)
        if user:
            print(f"✅ Credentials verified for {username}")
            return True
        else:
            print(f"❌ Invalid credentials for {username}")
            return False
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False
```

### 3. Mock User Testing (For Unit Tests)
Use this pattern for unit tests that need user context without real authentication.

```python
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from models import UserRole

def create_mock_admin_user():
    """
    Create a mock admin user for testing
    
    Returns:
        tuple: (user, helper) for cleanup
    """
    from config import Config
    from database import DatabaseManager
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    test_user, user_helper = create_test_user_with_platforms(
        db_manager, 
        username="test_admin", 
        role=UserRole.ADMIN
    )
    
    print(f"✅ Created mock admin user: {test_user.username}")
    return test_user, user_helper

def cleanup_mock_user(user_helper):
    """
    Clean up mock user after testing
    
    Args:
        user_helper: Helper object from create_test_user_with_platforms
    """
    cleanup_test_user(user_helper)
    print("✅ Mock user cleaned up")
```

## Testing Specific Features

### Admin Routes Testing
```python
def test_admin_functionality():
    """Test admin-specific functionality"""
    
    # Create authenticated session
    session, success = create_authenticated_session(username="admin")
    if not success:
        return False
    
    # Test admin dashboard access
    dashboard = session.get("http://127.0.0.1:5000/admin")
    if dashboard.status_code != 200:
        print("❌ Cannot access admin dashboard")
        return False
    
    print("✅ Admin dashboard accessible")
    return True

def test_system_maintenance():
    """Test system maintenance functionality"""
    
    session, success = create_authenticated_session(username="admin")
    if not success:
        return False
    
    # Get maintenance page and CSRF token
    maintenance_page = session.get("http://127.0.0.1:5000/admin/maintenance/pause-system")
    if maintenance_page.status_code != 200:
        print("❌ Cannot access maintenance page")
        return False
    
    # Extract CSRF token
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', maintenance_page.text)
    if not csrf_match:
        print("❌ No CSRF token found")
        return False
    
    csrf_token = csrf_match.group(1)
    
    # Test pause system
    pause_data = {
        'action': 'pause_system',
        'reason': 'Testing system pause functionality',
        'duration': '15 minutes',
        'notifyUsers': 'on',
        'confirmPause': 'on',
        'csrf_token': csrf_token
    }
    
    response = session.post(
        "http://127.0.0.1:5000/admin/api/system-maintenance/execute",
        data=pause_data
    )
    
    if response.status_code in [200, 302]:
        print("✅ System pause test successful")
        return True
    else:
        print(f"❌ System pause test failed: {response.status_code}")
        return False
```

### User Routes Testing
```python
def test_user_functionality():
    """Test regular user functionality"""
    
    # Test with regular user account
    session, success = create_authenticated_session(username="iolaire")  # or other non-admin user
    if not success:
        return False
    
    # Test user dashboard
    dashboard = session.get("http://127.0.0.1:5000/")
    if dashboard.status_code != 200:
        print("❌ Cannot access user dashboard")
        return False
    
    print("✅ User dashboard accessible")
    return True
```

## Security Considerations

### CSRF Token Handling
- Always extract CSRF tokens from the `<meta name="csrf-token">` tag
- Include CSRF tokens in all POST requests
- Use the session-specific token, not a hardcoded one

### Password Security
- Never hardcode passwords in test files
- Always prompt for passwords using `getpass.getpass()`
- Consider using environment variables for CI/CD testing

### Session Management
- Use `requests.Session()` to maintain cookies across requests
- Clean up sessions after testing
- Test session expiration and renewal

## Best Practices

### 1. Interactive Password Prompts
```python
import getpass

# Always prompt for passwords
password = getpass.getpass("Enter admin password: ")
```

### 2. Environment-Specific Testing
```python
import os

# Allow override of base URL for different environments
base_url = os.getenv('TEST_BASE_URL', 'http://127.0.0.1:5000')
```

### 3. Comprehensive Error Handling
```python
def safe_test_execution(test_func):
    """Wrapper for safe test execution with cleanup"""
    try:
        return test_func()
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    finally:
        # Cleanup code here
        pass
```

### 4. Logging Integration
```python
import logging

# Set up test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_test_result(test_name, success):
    """Log test results consistently"""
    if success:
        logger.info(f"✅ {test_name} - PASSED")
    else:
        logger.error(f"❌ {test_name} - FAILED")
```

## Example Test Script Template

```python
#!/usr/bin/env python3
"""
Template for authenticated testing scripts
"""

import sys
import requests
import getpass
from urllib.parse import urljoin

def main():
    """Main test execution"""
    print("=== Vedfolnir Authentication Test ===")
    
    # Get admin password
    admin_password = getpass.getpass("Enter admin password: ")
    
    # Create session and login
    session = requests.Session()
    
    # Your test logic here...
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

## Integration with Kiro

When Kiro needs to test authenticated functionality:

1. **Always prompt for admin password**: Use `getpass.getpass()` to securely get the password
2. **Use the patterns above**: Follow the established authentication patterns
3. **Handle errors gracefully**: Provide clear feedback on authentication failures
4. **Clean up after testing**: Ensure sessions are properly closed
5. **Log test results**: Use consistent logging for test outcomes

## Common Issues and Solutions

### Issue: CSRF Token Missing
**Solution**: Always extract CSRF token from the login page meta tag

### Issue: Wrong Form Field Names
**Solution**: Use `username_or_email` field name, not `username`

### Issue: Session Not Persisting
**Solution**: Use `requests.Session()` to maintain cookies

### Issue: Authentication Failing
**Solution**: Verify credentials manually first, check for typos in username

### Issue: Route Not Found
**Solution**: Verify the web application is running and routes are registered

This document should be referenced for all future authentication testing in Vedfolnir.