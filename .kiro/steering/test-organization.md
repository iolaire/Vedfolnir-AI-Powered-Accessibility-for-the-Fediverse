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
# ✅ CORRECT - Python-based frontend tests
tests/frontend/test_web_interface.py
tests/frontend/test_session_sync.py

# ✅ CORRECT - All Playwright tests (JavaScript/TypeScript)
tests/playwright/test_admin_ui.js
tests/playwright/test_login_flow.js
tests/playwright/test_platform_switching.js

# ❌ WRONG
ui_test.py
frontend_test.py
playwright_test.js  # Should be in tests/playwright/
```

### 7. Playwright Tests → `tests/playwright/`
```javascript
// ✅ CORRECT - All Playwright tests and files with timestamp prefix
tests/playwright/0824_14_30_test_admin_ui.js
tests/playwright/0824_14_30_test_login_flow.js
tests/playwright/0824_14_30_test_platform_switching.js
tests/playwright/0824_14_30_playwright.config.js
tests/playwright/0824_14_30_README.md
tests/playwright/fixtures/0824_14_30_test_data.json
tests/playwright/page_objects/0824_14_30_LoginPage.js
tests/playwright/utils/0824_14_30_test_helpers.js

// ❌ WRONG - Missing timestamp prefix
tests/playwright/test_admin_ui.js        # Missing timestamp prefix
tests/playwright/playwright.config.js   # Missing timestamp prefix
tests/playwright/README.md              # Missing timestamp prefix

// ❌ WRONG - Playwright files outside tests/playwright/
playwright.config.js                    # Should be in tests/playwright/
e2e/test_admin.js                       # Should be in tests/playwright/
browser_tests/login_test.js             # Should be in tests/playwright/
```

### 8. Security Tests → `tests/security/`
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

### Playwright File Naming
**IMPORTANT**: All Playwright test and documentation files must be prefixed with timestamp in format `MMdd_HH_mm_`

- **Test Files**: `MMdd_HH_mm_test_<functionality>.js` or `MMdd_HH_mm_<functionality>.spec.js`
- **Configuration**: `MMdd_HH_mm_playwright.config.js`
- **Page Objects**: `MMdd_HH_mm_<PageName>Page.js`
- **Utilities**: `MMdd_HH_mm_<utility_name>.js`
- **Documentation**: `MMdd_HH_mm_README.md`, `MMdd_HH_mm_<doc_name>.md`
- **Examples**:
  - `0824_14_30_test_admin_login.js`
  - `0824_14_30_admin_dashboard.spec.js`
  - `0824_14_30_LoginPage.js`
  - `0824_14_30_test_helpers.js`
  - `0824_14_30_README.md`
  - `0824_14_30_playwright.config.js`

**Timestamp Format**: `MMdd_HH_mm_` where:
- `MM` = Month (01-12)
- `dd` = Day (01-31)  
- `HH` = Hour in 24-hour format (00-23)
- `mm` = Minute (00-59)

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
- **Python-based web interface tests only**
- Server-side rendered template tests
- Flask route testing with web interface
- Session synchronization tests
- CSRF token validation tests
- **Note**: All Playwright/browser automation tests go in `tests/playwright/`

### `tests/playwright/`
- **ALL Playwright tests and documentation**
- Browser automation tests (JavaScript/TypeScript)
- End-to-end user workflows
- Cross-browser compatibility tests
- UI regression tests
- Playwright configuration files (`playwright.config.js`) with `headless: false`
- Playwright test utilities and helpers
- Playwright test documentation and README files
- Page object models and test fixtures
- Visual regression test screenshots and baselines
- **Configuration Requirement**: All tests must run with `headless: false` for visual debugging

### `tests/scripts/`
- Manual testing scripts
- Debugging utilities
- Data generation scripts
- Test environment setup scripts
- Temporary test files

## Playwright Test Organization

### Mandatory Playwright Directory Structure
**ALL Playwright-related files MUST be placed in `tests/playwright/`**

```
tests/playwright/
├── MMdd_HH_mm_test_*.js          # Playwright test files with timestamp
├── MMdd_HH_mm_*.spec.js          # Alternative test file naming with timestamp
├── MMdd_HH_mm_playwright.config.js # Playwright configuration with timestamp
├── MMdd_HH_mm_README.md          # Playwright documentation with timestamp
├── MMdd_HH_mm_package.json       # Node.js dependencies with timestamp
├── fixtures/                     # Test data and fixtures
│   ├── MMdd_HH_mm_test_data.json
│   └── MMdd_HH_mm_mock_responses.json
├── page_objects/                 # Page Object Model files
│   ├── MMdd_HH_mm_LoginPage.js
│   ├── MMdd_HH_mm_AdminDashboardPage.js
│   └── MMdd_HH_mm_PlatformManagementPage.js
├── utils/                        # Playwright utilities and helpers
│   ├── MMdd_HH_mm_test_helpers.js
│   ├── MMdd_HH_mm_auth_utils.js
│   └── MMdd_HH_mm_screenshot_utils.js
├── docs/                         # Documentation files
│   ├── MMdd_HH_mm_setup_guide.md
│   └── MMdd_HH_mm_troubleshooting.md
├── screenshots/                  # Visual regression baselines
│   ├── baseline/
│   └── actual/
└── reports/                      # Test reports and artifacts
    ├── html-report/
    └── test-results/
```

### Playwright File Types and Placement

#### Test Files
- **Location**: `tests/playwright/`
- **Naming**: `MMdd_HH_mm_test_<functionality>.js` or `MMdd_HH_mm_<functionality>.spec.js`
- **Examples**: `0824_14_30_test_admin_login.js`, `0824_14_30_admin_dashboard.spec.js`

#### Configuration Files
- **Location**: `tests/playwright/`
- **Files**: `MMdd_HH_mm_playwright.config.js`, `MMdd_HH_mm_package.json`
- **Purpose**: Playwright configuration and Node.js dependencies
- **Examples**: `0824_14_30_playwright.config.js`, `0824_14_30_package.json`
- **Required Setting**: `headless: false` must be configured in playwright.config.js

#### Page Object Models
- **Location**: `tests/playwright/page_objects/`
- **Naming**: `MMdd_HH_mm_<PageName>Page.js`
- **Examples**: `0824_14_30_LoginPage.js`, `0824_14_30_AdminDashboardPage.js`

#### Test Utilities
- **Location**: `tests/playwright/utils/`
- **Naming**: `MMdd_HH_mm_<utility_name>.js`
- **Examples**: `0824_14_30_test_helpers.js`, `0824_14_30_auth_utils.js`

#### Test Data and Fixtures
- **Location**: `tests/playwright/fixtures/`
- **Files**: JSON, CSV, or other data files with timestamp prefix
- **Examples**: `0824_14_30_test_data.json`, `0824_14_30_mock_responses.json`

#### Documentation
- **Location**: `tests/playwright/` or `tests/playwright/docs/`
- **Files**: `MMdd_HH_mm_README.md`, setup guides, troubleshooting docs
- **Purpose**: Playwright-specific documentation and guides
- **Examples**: `0824_14_30_README.md`, `0824_14_30_setup_guide.md`, `0824_14_30_troubleshooting.md`

### Playwright Test Categories

#### End-to-End Workflow Tests
```javascript
// tests/playwright/0824_14_30_test_complete_workflow.js
// Full user journey from login to task completion
```

#### Admin Interface Tests
```javascript
// tests/playwright/0824_14_30_test_admin_dashboard.js
// Admin-specific UI functionality
```

#### Cross-Browser Compatibility Tests
```javascript
// tests/playwright/0824_14_30_test_browser_compatibility.js
// Testing across different browsers
```

#### Visual Regression Tests
```javascript
// tests/playwright/0824_14_30_test_visual_regression.js
// Screenshot comparison tests
```

#### Performance Tests
```javascript
// tests/playwright/0824_14_30_test_performance.js
// Page load times and performance metrics
```

### Playwright Security Considerations

#### Page.evaluate() Security Restrictions
**CRITICAL**: WebKit browsers have strict security restrictions on `page.evaluate()` operations.

**Issue**: Using `page.evaluate()` to clear localStorage/sessionStorage causes `SecurityError: The operation is insecure`.

**Solution**: Use safer cleanup methods:
```javascript
// CORRECT - Safe cleanup
test.beforeEach(async ({ page }) => {
  await page.context().clearCookies();
});

// WRONG - Causes SecurityError in WebKit
test.beforeEach(async ({ page }) => {
  await page.evaluate(() => {
    localStorage.clear();    // SecurityError!
    sessionStorage.clear();  // SecurityError!
  });
});
```

#### Navigation Timeout Prevention
**Issue**: `networkidle` wait conditions timeout with WebSocket connections.

**Solution**: Use `domcontentloaded` for reliable navigation:
```javascript
// CORRECT - Reliable navigation
await page.goto('/login', { 
  waitUntil: 'domcontentloaded',
  timeout: 30000 
});

// WRONG - Times out with WebSockets
await page.goto('/login', { 
  waitUntil: 'networkidle'  // Problematic
});
```

### Playwright Configuration Requirements

#### Headless Mode Setting
**MANDATORY**: All Playwright tests must be configured to run with `headless: false`

```javascript
// 0824_14_30_playwright.config.js
module.exports = {
  use: {
    headless: false,  // REQUIRED: Always run with visible browser
    // other configuration options...
  },
  // other configuration...
};
```

#### Reasons for headless=false
- **Visual Debugging**: Allows developers to see test execution in real-time
- **Test Development**: Easier to develop and debug tests when browser is visible
- **Issue Identification**: Faster identification of UI issues and test failures
- **Interactive Development**: Enables step-by-step test development and validation

#### Configuration Examples
```javascript
// Example 1: Basic configuration with headless=false
// 0824_14_30_playwright.config.js
module.exports = {
  testDir: './tests',
  use: {
    headless: false,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
  },
};

// Example 2: Advanced configuration with headless=false
// 0824_14_30_playwright.config.js
module.exports = {
  testDir: './tests',
  timeout: 30000,
  use: {
    headless: false,
    baseURL: 'http://127.0.0.1:5000',
    viewport: { width: 1280, height: 720 },
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], headless: false },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'], headless: false },
    },
  ],
};
```

### Timestamp Prefix Rules

#### When to Apply Timestamp Prefix
- **ALL Playwright test files** (`.js`, `.ts`, `.spec.js`, `.spec.ts`)
- **ALL Playwright configuration files** (`playwright.config.js`, `package.json`)
- **ALL Playwright documentation files** (`.md` files)
- **ALL Playwright utility files** (helper functions, page objects)
- **ALL Playwright data files** (fixtures, test data)

#### How to Generate Timestamp
Use the current date and time when creating the file:
- **Format**: `MMdd_HH_mm_`
- **Example**: For August 24th at 2:30 PM → `0824_14_30_`

#### Timestamp Examples by File Type
```javascript
// Test files
0824_14_30_test_login.js
0824_14_30_admin_dashboard.spec.js

// Configuration files  
0824_14_30_playwright.config.js
0824_14_30_package.json

// Page objects
0824_14_30_LoginPage.js
0824_14_30_AdminDashboardPage.js

// Utilities
0824_14_30_test_helpers.js
0824_14_30_auth_utils.js

// Documentation
0824_14_30_README.md
0824_14_30_setup_guide.md
0824_14_30_troubleshooting.md

// Test data
0824_14_30_test_data.json
0824_14_30_mock_responses.json
```

## Enforcement Rules

### Kiro Guidelines
When Kiro creates test files:

1. **Always ask**: "What type of test is this?" (admin, security, integration, unit, playwright, etc.)
2. **Always place** test files in the appropriate `tests/` subdirectory
3. **Never create** test files in the project root directory
4. **Always use** proper naming conventions
5. **Always include** proper copyright headers (for Python files)
6. **Always add** proper import path management for subdirectories
7. **For Playwright tests**: Always place ALL Playwright-related files in `tests/playwright/`
8. **For browser automation**: Use `tests/playwright/` for all browser-based end-to-end tests
9. **For Playwright configuration**: Always set `headless: false` in playwright.config.js
10. **For Playwright execution**: Ensure tests run with visible browser for debugging and development

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
├── playwright/
│   ├── 0824_14_30_test_admin_ui.js
│   ├── 0824_14_30_test_login_flow.js
│   ├── 0824_14_30_playwright.config.js
│   ├── 0824_14_30_README.md
│   ├── fixtures/
│   │   └── 0824_14_30_test_data.json
│   ├── page_objects/
│   │   ├── 0824_14_30_LoginPage.js
│   │   └── 0824_14_30_AdminDashboardPage.js
│   └── utils/
│       └── 0824_14_30_test_helpers.js
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
├── manual_test.py                # Should be in tests/scripts/
├── playwright.config.js          # Should be in tests/playwright/
├── e2e/
│   └── admin_test.js             # Should be in tests/playwright/
└── browser_tests/
    └── login_test.js             # Should be in tests/playwright/
```

This organization ensures a clean, maintainable, and professional project structure that scales well as the project grows.