# Test Organization Guidelines

## Overview
All test code in Vedfolnir must be organized within the `tests/` directory structure. **No test files should be placed in the project root directory (`/`)**. This ensures clean project organization, better maintainability, and clear separation of concerns.

## Directory Structure

### Required Test Organization
```
tests/
├── admin/                    # Admin functionality tests
├── deployment/               # Deployment and infrastructure tests
├── documentation/            # Documentation validation tests
├── fixtures/                 # Test fixtures and data
├── frontend/                 # Frontend and UI tests
├── integration/              # Integration tests
├── performance/              # Performance and load tests
├── playwright/               # End-to-end browser tests
├── scripts/                  # Test utility scripts
├── security/                 # Security and vulnerability tests
├── templates/                # Template testing utilities
├── test_helpers/             # Test helper functions and utilities
├── unit/                     # Unit tests
└── web_caption_generation/   # Web caption generation specific tests
```

## Test File Placement Rules

### 1. Admin Functionality Tests → `tests/admin/`
```python
# ✅ CORRECT
tests/admin/test_pause_system.py
tests/admin/test_user_management.py
tests/admin/test_system_maintenance.py

# ❌ WRONG
test_pause_system.py
admin_test.py
```

### 2. Authentication Tests → `tests/security/` or `tests/integration/`
```python
# ✅ CORRECT
tests/security/test_authentication.py
tests/integration/test_login_flow.py
tests/security/test_session_security.py

# ❌ WRONG
test_authentication.py
login_test.py
```

### 3. Unit Tests → `tests/unit/`
```python
# ✅ CORRECT
tests/unit/test_user_model.py
tests/unit/test_database_manager.py
tests/unit/test_config_validation.py

# ❌ WRONG
test_user_model.py
unit_test_config.py
```

### 4. Integration Tests → `tests/integration/`
```python
# ✅ CORRECT
tests/integration/test_end_to_end_workflow.py
tests/integration/test_platform_switching.py
tests/integration/test_session_management.py

# ❌ WRONG
test_integration.py
e2e_test.py
```

### 5. Performance Tests → `tests/performance/`
```python
# ✅ CORRECT
tests/performance/test_database_performance.py
tests/performance/test_session_load.py
tests/performance/test_api_benchmarks.py

# ❌ WRONG
performance_test.py
load_test.py
```

### 6. Frontend/UI Tests → `tests/frontend/` or `tests/playwright/`
```python
# ✅ CORRECT
tests/frontend/test_web_interface.py
tests/playwright/test_admin_ui.py
tests/frontend/test_session_sync.py

# ❌ WRONG
ui_test.py
frontend_test.py
```

### 7. Security Tests → `tests/security/`
```python
# ✅ CORRECT
tests/security/test_csrf_protection.py
tests/security/test_authentication_security.py
tests/security/test_input_validation.py

# ❌ WRONG
security_test.py
test_csrf.py
```

## Naming Conventions

### Test File Naming
- **Pattern**: `test_<functionality>.py`
- **Examples**:
  - `test_pause_system.py`
  - `test_user_authentication.py`
  - `test_platform_switching.py`
  - `test_session_management.py`

### Test Class Naming
- **Pattern**: `Test<Functionality>`
- **Examples**:
  - `TestPauseSystem`
  - `TestUserAuthentication`
  - `TestPlatformSwitching`

### Test Method Naming
- **Pattern**: `test_<specific_behavior>`
- **Examples**:
  - `test_pause_system_with_valid_credentials`
  - `test_login_with_invalid_password`
  - `test_session_creation_success`

## Test Script Organization

### Temporary Test Scripts
For temporary testing or debugging, use the `tests/scripts/` directory:

```python
# ✅ CORRECT
tests/scripts/debug_pause_system.py
tests/scripts/manual_authentication_test.py
tests/scripts/verify_database_connection.py

# ❌ WRONG
debug_test.py
manual_test.py
verify_connection.py
```

### Test Utilities and Helpers
Place reusable test utilities in `tests/test_helpers/`:

```python
# ✅ CORRECT
tests/test_helpers/authentication_helpers.py
tests/test_helpers/mock_user_helpers.py
tests/test_helpers/database_test_utils.py

# ❌ WRONG
auth_utils.py
test_utils.py
helpers.py
```

## Implementation Guidelines

### 1. Creating New Tests
When creating any new test, always place it in the appropriate subdirectory:

```python
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test for admin pause system functionality
Location: tests/admin/test_pause_system.py
"""

import unittest
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestPauseSystem(unittest.TestCase):
    """Test cases for admin pause system functionality"""
    
    def test_pause_system_with_authentication(self):
        """Test pause system with proper admin authentication"""
        # Test implementation here
        pass

if __name__ == '__main__':
    unittest.main()
```

### 2. Import Path Management
For tests in subdirectories, ensure proper import paths:

```python
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Now you can import project modules
from config import Config
from database import DatabaseManager
```

### 3. Test Discovery
Ensure tests can be discovered by the test runner:

```bash
# Run all tests
python -m unittest discover tests

# Run specific test category
python -m unittest discover tests/admin
python -m unittest discover tests/security
python -m unittest discover tests/integration
```

## Directory-Specific Guidelines

### `tests/admin/`
- Admin dashboard tests
- User management tests
- System maintenance tests
- Admin API tests
- Admin security tests

### `tests/integration/`
- End-to-end workflow tests
- Cross-component integration tests
- Database integration tests
- Session management integration tests
- Platform switching tests

### `tests/unit/`
- Individual component tests
- Model tests
- Service layer tests
- Utility function tests
- Configuration tests

### `tests/security/`
- Authentication tests
- Authorization tests
- CSRF protection tests
- Input validation tests
- Security vulnerability tests

### `tests/performance/`
- Load testing
- Stress testing
- Performance benchmarks
- Memory usage tests
- Database performance tests

### `tests/frontend/`
- Web interface tests
- JavaScript functionality tests
- CSS/styling tests
- User interaction tests
- Accessibility tests

### `tests/playwright/`
- Browser automation tests
- End-to-end user workflows
- Cross-browser compatibility tests
- UI regression tests

### `tests/scripts/`
- Manual testing scripts
- Debugging utilities
- Data generation scripts
- Test environment setup scripts
- Temporary test files

## Enforcement Rules

### Kiro Guidelines
When Kiro creates test files:

1. **Always ask**: "What type of test is this?" (admin, security, integration, unit, etc.)
2. **Always place** test files in the appropriate `tests/` subdirectory
3. **Never create** test files in the project root directory
4. **Always use** proper naming conventions
5. **Always include** proper copyright headers
6. **Always add** proper import path management for subdirectories

### Code Review Checklist
- [ ] Test file is in appropriate `tests/` subdirectory
- [ ] Test file follows naming convention `test_<functionality>.py`
- [ ] Test class follows naming convention `Test<Functionality>`
- [ ] Test methods follow naming convention `test_<specific_behavior>`
- [ ] Copyright header is present
- [ ] Import paths are properly configured
- [ ] Test can be discovered by test runner

### Migration of Existing Tests
If any test files exist in the project root, they should be moved:

```bash
# Example migration
mv test_pause_system.py tests/admin/test_pause_system.py
mv auth_test.py tests/security/test_authentication.py
mv integration_test.py tests/integration/test_workflow.py
```

## Benefits of Proper Organization

### 1. Clean Project Structure
- Clear separation between source code and tests
- Easy navigation and file discovery
- Professional project appearance

### 2. Better Maintainability
- Related tests grouped together
- Easier to find and update tests
- Clear test categorization

### 3. Improved Test Discovery
- Test runners can easily find all tests
- Category-specific test execution
- Better CI/CD integration

### 4. Team Collaboration
- Clear conventions for all developers
- Consistent project structure
- Easier onboarding for new team members

### 5. Scalability
- Structure supports project growth
- Easy to add new test categories
- Maintains organization as codebase expands

## Examples

### ✅ CORRECT Test Organization
```
tests/
├── admin/
│   ├── test_pause_system.py
│   ├── test_user_management.py
│   └── test_system_maintenance.py
├── security/
│   ├── test_authentication.py
│   ├── test_csrf_protection.py
│   └── test_session_security.py
├── integration/
│   ├── test_login_workflow.py
│   ├── test_platform_switching.py
│   └── test_end_to_end.py
└── scripts/
    ├── debug_authentication.py
    └── manual_system_test.py
```

### ❌ WRONG Test Organization
```
/
├── test_pause_system.py          # Should be in tests/admin/
├── auth_test.py                  # Should be in tests/security/
├── integration_test.py           # Should be in tests/integration/
├── debug_test.py                 # Should be in tests/scripts/
└── manual_test.py                # Should be in tests/scripts/
```

This organization ensures a clean, maintainable, and professional project structure that scales well as the project grows.