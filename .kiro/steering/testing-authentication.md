# Testing Authentication and Session Management

## Authentication Testing Patterns

### 1. Web Request Testing (Recommended)
```python
import requests
import getpass
import re
from urllib.parse import urljoin

def create_authenticated_session(base_url="http://127.0.0.1:5000", username="admin"):
    """Create authenticated session for testing"""
    session = requests.Session()
    
    # Get login page and CSRF token
    login_page = session.get(urljoin(base_url, "/login"))
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    csrf_token = csrf_match.group(1)
    
    # Prompt for password
    password = getpass.getpass(f"Enter password for {username}: ")
    
    # Login
    login_data = {
        'username_or_email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    response = session.post(urljoin(base_url, "/login"), data=login_data)
    success = response.status_code in [200, 302] and 'login' not in response.url.lower()
    
    return session, success
```

### 2. Direct Database Testing
```python
from config import Config
from database import DatabaseManager
from models import User
import getpass

def get_test_user(username="admin"):
    """Get user from database for testing"""
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        return session.query(User).filter_by(username=username).first()

def verify_user_credentials(username="admin"):
    """Verify user credentials interactively"""
    from services.user_management_service import UserManagementService
    
    config = Config()
    db_manager = DatabaseManager(config)
    user_service = UserManagementService(db_manager)
    
    password = getpass.getpass(f"Enter password for {username}: ")
    return user_service.authenticate_user(username, password) is not None
```

### 3. Mock User Testing (Unit Tests)
```python
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from models import UserRole

def create_mock_admin_user():
    """Create mock admin for testing"""
    config = Config()
    db_manager = DatabaseManager(config)
    
    test_user, user_helper = create_test_user_with_platforms(
        db_manager, 
        username="test_admin", 
        role=UserRole.ADMIN
    )
    return test_user, user_helper
```

## Testing Specific Features

### Admin Routes
```python
def test_admin_functionality():
    """Test admin-specific functionality"""
    session, success = create_authenticated_session(username="admin")
    if not success:
        return False
    
    # Test admin dashboard
    dashboard = session.get("http://127.0.0.1:5000/admin")
    return dashboard.status_code == 200

def test_system_maintenance():
    """Test system maintenance functionality"""
    session, success = create_authenticated_session(username="admin")
    if not success:
        return False
    
    # Get CSRF token from maintenance page
    maintenance_page = session.get("http://127.0.0.1:5000/admin/maintenance/pause-system")
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', maintenance_page.text)
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
    
    return response.status_code in [200, 302]
```

## Security Considerations

### CSRF Token Handling
- Extract from `<meta name="csrf-token">` tag
- Include in all POST requests
- Use session-specific tokens

### Password Security
- Always use `getpass.getpass()` for password prompts
- Never hardcode passwords
- Consider environment variables for CI/CD

### Session Management
- Use `requests.Session()` for cookie persistence
- Clean up sessions after testing
- Test session expiration

## Best Practices

### Interactive Password Prompts
```python
import getpass
password = getpass.getpass("Enter admin password: ")
```

### Environment-Specific Testing
```python
import os
base_url = os.getenv('TEST_BASE_URL', 'http://127.0.0.1:5000')
```

### Error Handling
```python
def safe_test_execution(test_func):
    """Wrapper for safe test execution"""
    try:
        return test_func()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
```

## Example Test Script Template
```python
#!/usr/bin/env python3
import sys
import requests
import getpass
from urllib.parse import urljoin

def main():
    """Main test execution"""
    print("=== Vedfolnir Authentication Test ===")
    
    # Create session and test functionality
    session, success = create_authenticated_session()
    if success:
        # Your test logic here
        print("✅ Authentication successful")
    else:
        print("❌ Authentication failed")
        return False
    
    print("=== Test Complete ===")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

## Common Issues & Solutions
- **CSRF Token Missing**: Extract from login page meta tag
- **Wrong Form Fields**: Use `username_or_email`, not `username`
- **Session Not Persisting**: Use `requests.Session()`
- **Authentication Failing**: Verify credentials manually first
