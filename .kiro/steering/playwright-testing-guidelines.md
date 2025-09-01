# Playwright Testing Guidelines

## Overview
This document establishes mandatory guidelines for Playwright browser testing in Vedfolnir. All Playwright tests must follow these standards to ensure reliability, consistency, and proper resource management.

## Timeout Requirements

### Command-Level Timeouts (MANDATORY)
All Playwright test commands MUST be prefixed with `timeout 120` to prevent infinite hangs:

```bash
# CORRECT - Always use timeout prefix
timeout 120 npx playwright test --config=0830_17_52_playwright.config.js

# WRONG - Missing timeout prefix
npx playwright test --config=0830_17_52_playwright.config.js
```

### Playwright Configuration Timeouts
The following timeout values are mandatory in all Playwright configurations:

```javascript
module.exports = defineConfig({
  // Global test timeout (120 seconds = 120000ms)
  timeout: 120000,
  
  // Expect timeout for assertions (30 seconds = 30000ms)
  expect: {
    timeout: 30000
  },
  
  use: {
    // Action timeout (30 seconds = 30000ms)
    actionTimeout: 30000,
    
    // Navigation timeout (60 seconds = 60000ms)
    navigationTimeout: 60000
  },
  
  webServer: {
    timeout: 120000, // 120 seconds = 120000ms for server startup
  }
});
```

### NPM Script Timeouts
All NPM scripts must include timeout parameters:

```json
{
  "scripts": {
    "test": "playwright test --config=0830_17_52_playwright.config.js --timeout=120000",
    "test:webkit": "playwright test --config=0830_17_52_playwright.config.js --project=webkit-all-tests --timeout=120000",
    "test:debug": "playwright test --config=0830_17_52_playwright.config.js --debug --timeout=120000"
  }
}
```

## Authentication Requirements

### Clean State Initialization (MANDATORY)
All tests MUST start with a clean authentication state:

```javascript
const { ensureLoggedOut } = require('../utils/0830_17_52_auth_utils');

test.describe('Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    // MANDATORY - Ensure user is logged out before starting test
    await ensureLoggedOut(page);
  });

  test.afterEach(async ({ page }) => {
    // MANDATORY - Ensure clean logout after each test
    await ensureLoggedOut(page);
  });
});
```

### Authentication Functions
Use standardized authentication functions:

```javascript
// Login functions
await loginAsAdmin(page);     // For admin tests
await loginAsUser(page);      // For user tests

// Logout functions
await logout(page);           // Standard logout
await ensureLoggedOut(page);  // Comprehensive cleanup (preferred)
await clearAuthState(page);   // Clear cookies and storage
```

## File Organization

### Test File Placement
All Playwright tests MUST be placed in `tests/playwright/tests/` directory:

```
tests/playwright/
├── tests/                           # All test files here
│   ├── 0830_17_52_test_admin_authentication.js
│   ├── 0830_17_52_test_user_authentication.js
│   └── 0830_17_52_test_websocket_validation.js
├── utils/                           # Utility functions
│   ├── 0830_17_52_auth_utils.js
│   └── 0830_17_52_websocket_utils.js
├── 0830_17_52_playwright.config.js  # Configuration
├── 0830_17_52_package.json          # Dependencies
└── 0830_17_52_README.md             # Documentation
```

### File Naming Convention
All Playwright files MUST use timestamp prefix: `MMdd_HH_mm_filename.js`

```javascript
// CORRECT
0830_17_52_test_admin_authentication.js
0830_17_52_playwright.config.js
0830_17_52_auth_utils.js

// WRONG
test_admin_authentication.js
playwright.config.js
auth_utils.js
```

## Browser Configuration

### Headless Mode (MANDATORY)
All tests MUST run with `headless: false` for debugging and development:

```javascript
use: {
  headless: false,  // MANDATORY for visual debugging
  // other configuration...
}
```

### Browser Support
- **Primary**: WebKit (Safari) - main testing target
- **Secondary**: Chromium, Firefox - compatibility testing
- **All browsers**: Must support WebSocket connections and notifications

## Test Structure Requirements

### Test Organization
```javascript
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await ensureLoggedOut(page);
    // Additional setup...
  });

  test.afterEach(async ({ page }) => {
    await ensureLoggedOut(page);
    // Additional cleanup...
  });

  test('Specific behavior description', async ({ page }) => {
    // Test implementation
  });
});
```

### Error Monitoring
All tests should include console error monitoring:

```javascript
test.beforeEach(async ({ page }) => {
  // Set up console error monitoring
  const errors = await checkConsoleErrors(page);
  page.consoleErrors = errors;
});

test.afterEach(async ({ page }) => {
  // Check for console errors after each test
  if (page.consoleErrors && page.consoleErrors.length > 0) {
    console.warn('⚠️ Console errors detected:', page.consoleErrors);
  }
});
```

## Command Examples

### Individual Test Execution
```bash
# Run specific test file
timeout 120 npx playwright test --config=0830_17_52_playwright.config.js tests/0830_17_52_test_admin_authentication.js --timeout=120

# Run with debug mode
timeout 120 npx playwright test --config=0830_17_52_playwright.config.js tests/0830_17_52_test_admin_authentication.js --debug --timeout=120

# Run with verbose output
timeout 120 npx playwright test --config=0830_17_52_playwright.config.js --reporter=list --timeout=120
```

### Test Suite Execution
```bash
# Run all tests
timeout 120 npm test

# Run browser-specific tests
timeout 120 npm run test:webkit
timeout 120 npm run test:chromium
timeout 120 npm run test:firefox

# Run in debug mode
timeout 120 npm run test:debug
```

## Error Handling

### Timeout Failures
When tests fail due to timeouts:

1. **Check Web Application**: Ensure Vedfolnir is running on `http://127.0.0.1:5000`
2. **Verify Credentials**: Confirm admin and user accounts exist with correct passwords
3. **Review Logs**: Check browser console and network logs for errors
4. **Increase Timeouts**: Only as last resort, prefer fixing root cause

### Authentication Failures
When authentication tests fail:

1. **Verify Accounts**: Ensure test accounts exist in database
2. **Check Passwords**: Verify credentials match test configuration
3. **Clear State**: Run `ensureLoggedOut()` manually if needed
4. **Review Session**: Check session management and cookies

### Common Authentication Issues and Fixes

#### Null Page Object Errors
**Problem**: `Cannot read properties of null (reading 'goto')` errors in authentication utilities.

**Root Cause**: Authentication utility functions (`ensureLoggedOut`, `logout`, `clearAuthState`) not validating page object before use.

**Solution**: Always validate page object before using it:

```javascript
// CORRECT - Always validate page object
async function ensureLoggedOut(page) {
  // Check if page object is valid
  if (!page) {
    console.error('❌ Page object is null or undefined');
    throw new Error('Page object is required for ensureLoggedOut');
  }
  
  // Additional safety checks before using page methods
  if (page && typeof page.goto === 'function') {
    try {
      await page.goto('/login');
    } catch (fallbackError) {
      console.error('❌ Final fallback also failed:', fallbackError.message);
      throw fallbackError;
    }
  } else {
    console.error('❌ Page object is invalid, cannot perform fallback');
    throw new Error('Page object is invalid');
  }
}

// WRONG - No validation
async function ensureLoggedOut(page) {
  await page.goto('/login'); // This can fail if page is null
}
```

**Prevention**: 
- Always validate page object at the start of utility functions
- Use defensive programming with null checks
- Provide meaningful error messages for debugging
- Test utility functions independently before using in test suites

## CI/CD Integration

### Environment Variables
```bash
# Set base URL for different environments
export TEST_BASE_URL=http://127.0.0.1:5000

# Set credentials (if different from defaults)
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD="akdr)X&XCN>fe0<RT5$RP^ik"
export USER_EMAIL="iolaire@usa.net"
export USER_PASSWORD="g9bDFB9JzgEaVZx"
```

### GitHub Actions Example
```yaml
- name: Run Playwright Tests
  run: |
    cd tests/playwright
    npm install
    npx playwright install webkit
    timeout 120 npm test
```

## Quality Standards

### Test Requirements
- All tests must pass consistently
- No console errors related to WebSocket, CORS, or notifications
- Proper cleanup after each test
- Clear, descriptive test names and logging

### Performance Standards
- Tests should complete within timeout limits
- WebSocket connections established within 15 seconds
- Page navigation completed within 60 seconds
- Authentication completed within 30 seconds

## Maintenance

### Regular Updates
1. Update timeout values if application performance changes
2. Maintain test credentials and accounts
3. Update browser versions regularly
4. Review and update test expectations

### Troubleshooting
1. Run tests individually to isolate issues
2. Use debug mode for step-by-step execution
3. Check HTML reports for detailed failure information
4. Verify web application is running and accessible

---

**Compliance**: All Playwright tests MUST follow these guidelines  
**Enforcement**: Tests not following these standards will be rejected  
**Updates**: This document should be updated when testing requirements change