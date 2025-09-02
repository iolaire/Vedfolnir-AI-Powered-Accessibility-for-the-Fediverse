# Playwright Testing Guidelines

## Mandatory Requirements

### Timeouts (REQUIRED)
```bash
# Always prefix with timeout (run from tests/playwright/)
timeout 120 npx playwright test --config=0830_17_52_playwright.config.js
```

### Configuration Timeouts
```javascript
module.exports = defineConfig({
  timeout: 120000,                    // 120 seconds
  expect: { timeout: 30000 },         // 30 seconds
  use: {
    headless: false,                  // MANDATORY for debugging
    actionTimeout: 30000,
    navigationTimeout: 60000
  },
  webServer: { timeout: 120000 }
});
```

### Authentication (MANDATORY)
```javascript
const { ensureLoggedOut } = require('../utils/0830_17_52_auth_utils');

test.describe('Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    await ensureLoggedOut(page);      // MANDATORY cleanup
  });
  
  test.afterEach(async ({ page }) => {
    await ensureLoggedOut(page);      // MANDATORY cleanup
  });
});
```

## File Organization

### Directory Structure
```
tests/playwright/
├── tests/                           # All test files
├── utils/                           # Utility functions
├── 0830_17_52_playwright.config.js  # Configuration
├── 0830_17_52_package.json          # Dependencies
└── 0830_17_52_README.md             # Documentation
```

### File Naming (MANDATORY)
All files MUST use timestamp prefix: `MMdd_HH_mm_filename.js`

## Browser Configuration
- **Headless**: `false` (MANDATORY for debugging)
- **Primary**: WebKit (Safari)
- **Secondary**: Chromium, Firefox

## Command Examples
```bash
# Navigate to correct directory first
cd tests/playwright

# Run tests
timeout 120 npx playwright test --config=0830_17_52_playwright.config.js

# Debug mode
timeout 120 npx playwright test --config=0830_17_52_playwright.config.js --debug

# Specific test
timeout 120 npx playwright test tests/0830_17_52_test_admin.js --timeout=120
```

## Critical Security Issues

### Page.evaluate() Security Error
**Problem**: `SecurityError: The operation is insecure` in WebKit

**Solution**: Avoid `page.evaluate()` for storage cleanup
```javascript
// CORRECT - Safe cleanup
test.beforeEach(async ({ page }) => {
  await page.context().clearCookies();
});

// WRONG - Causes SecurityError
test.beforeEach(async ({ page }) => {
  await page.evaluate(() => {
    localStorage.clear();    // SecurityError!
  });
});
```

### Navigation Timeout Prevention
**Problem**: `networkidle` timeouts with WebSockets

**Solution**: Use `domcontentloaded`
```javascript
// CORRECT
await page.goto('/login', { 
  waitUntil: 'domcontentloaded',
  timeout: 30000 
});

// WRONG - Times out
await page.goto('/login', { 
  waitUntil: 'networkidle'
});
```

## Quality Standards
- All tests must pass consistently
- No console errors (WebSocket, CORS, notifications)
- Proper cleanup after each test
- Clear, descriptive test names

## Troubleshooting
1. Verify web app running on `http://127.0.0.1:5000`
2. Confirm admin/user accounts exist
3. Check browser console for errors
4. Use debug mode for step-by-step execution
