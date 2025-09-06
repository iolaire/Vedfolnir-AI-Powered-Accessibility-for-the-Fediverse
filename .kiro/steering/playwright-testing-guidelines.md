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

## Landing Page Tests (NEW)

### Running Landing Page Tests
```bash
# Navigate to correct directory first
cd tests/playwright

# Start web application first
python web_app.py & sleep 10

# Run accessibility tests (REQUIRED timeout prefix)
timeout 120 npx playwright test tests/0905_14_50_test_landing_page_accessibility.js --config=0830_17_52_playwright.config.js

# Run UI tests
timeout 120 npx playwright test tests/0905_14_50_test_landing_page_ui.js --config=0830_17_52_playwright.config.js

# Debug mode
timeout 120 npx playwright test tests/0905_14_50_test_landing_page_accessibility.js --config=0830_17_52_playwright.config.js --debug

# Use convenience script
./0905_14_50_run_landing_page_tests.sh --accessibility
./0905_14_50_run_landing_page_tests.sh --ui
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

## Generic Test Running Instructions (For Any Playwright Test)

### Standard Test Execution Pattern
```bash
# 1. ALWAYS navigate to correct directory first
cd tests/playwright

# 2. Start web application if needed (most tests require this)
python web_app.py & sleep 10

# 3. Verify app is running
curl -s http://127.0.0.1:5000 | head -5

# 4. Run test with MANDATORY timeout prefix and working config
timeout 120 npx playwright test tests/[TIMESTAMP]_test_[NAME].js --config=0830_17_52_playwright.config.js

# 5. For debugging, add --debug flag
timeout 120 npx playwright test tests/[TIMESTAMP]_test_[NAME].js --config=0830_17_52_playwright.config.js --debug
```

### Test File Pattern Recognition
- All test files follow: `tests/MMdd_HH_mm_test_[description].js`
- Always use existing working config: `0830_17_52_playwright.config.js`
- Always use timeout prefix: `timeout 120`
- Always run from `tests/playwright/` directory

### Universal Prerequisites Checklist
1. ✅ Navigate to `tests/playwright/` directory
2. ✅ Start web application: `python web_app.py & sleep 10`
3. ✅ Verify app responds: `curl http://127.0.0.1:5000`
4. ✅ Use timeout prefix: `timeout 120`
5. ✅ Use working config: `--config=0830_17_52_playwright.config.js`
6. ✅ For debugging: add `--debug` flag

### Common Error Prevention
- **"No tests found"**: Check file path and use correct config
- **Timeout errors**: Ensure web app is running first
- **Navigation errors**: Use `domcontentloaded` not `networkidle`
- **Security errors**: Avoid `page.evaluate()` for storage operations
- **Browser errors**: Ensure browsers installed: `npx playwright install`

## Troubleshooting
1. Verify web app running on `http://127.0.0.1:5000`
2. Confirm admin/user accounts exist
3. Check browser console for errors
4. Use debug mode for step-by-step execution

## AJAX Form Testing (Lessons Learned)

### JavaScript Event Handling
**Problem**: JavaScript event listeners may not be properly attached or executed in Playwright.

**Solution**: Use direct element interaction and verify JavaScript execution:
```javascript
// CORRECT - Direct button click with proper waiting
await page.click('button[type="submit"]');
await page.wait_for_timeout(5000); // Wait for AJAX completion

// ALSO CORRECT - Verify JavaScript is executing
const js_event_listener = await page.evaluate('''
    () => {
        const form = document.querySelector('#edit-mode form');
        if (form) {
            return form.onsubmit !== null;
        }
        return false;
    }
''');
console.log(`JavaScript event listener attached: ${js_event_listener}`);
```

### Console Message Monitoring
**Problem**: JavaScript errors and AJAX responses may not be visible in test output.

**Solution**: Set up real-time console message capture:
```javascript
// CORRECT - Real-time console monitoring
console_messages = [];
def console_handler(msg):
    message = f"Console {msg.type}: {msg.text}"
    console_messages.append(message);
    print(f"   {message}");
page.on("console", console_handler);
```

### AJAX Form Submission Testing
**Problem**: Forms using AJAX may not trigger traditional form submission events.

**Solution**: Test both direct interaction and verify AJAX responses:
```javascript
// CORRECT - Test AJAX form submission
await page.fill('#first_name', 'TestValue');
await page.click('button[type="submit"]');

// Wait for AJAX completion
await page.wait_for_timeout(5000);

// Verify success through console logs
if any('Response data: {success: true}' in msg for msg in console_messages):
    console.log("✅ AJAX submission successful");
```

### Page Reload Handling
**Problem**: AJAX forms that reload pages may cause timeout issues.

**Solution**: Use appropriate timeouts and verify page state:
```javascript
// CORRECT - Handle page reloads after AJAX
await page.wait_for_timeout(5000); // Wait for reload
await page.wait_for_selector('#view-mode', state='visible', timeout=30000);

// Alternative - Check URL if page reloads
current_url = page.url;
if current_url.includes('/profile'):
    console.log("✅ Page reload successful");
```

### Form Validation Testing
**Problem**: CSRF protection and form validation may fail silently.

**Solution**: Verify form data and CSRF tokens:
```javascript
// CORRECT - Check form structure and CSRF
form_html = await page.inner_html('#edit-mode form');
console.log(`Form contains CSRF token: ${'csrf_token' in form_html}`);

// Verify form data submission
console.log("Form data being submitted:");
for (let [key, value] of formData.entries()) {
    console.log(`${key}: ${value}`);
}
```

### Browser-Specific Behavior
**Problem**: Different browsers may handle JavaScript and AJAX differently.

**Solution**: Test across browsers and use appropriate waits:
```javascript
// CORRECT - Browser-agnostic testing
const browsers = ['webkit', 'chromium', 'firefox'];
for (const browser of browsers) {
    const context = await browser.newContext();
    const page = await context.newPage();
    // Test implementation
    await browser.close();
}
```

### Debug Mode Best Practices
**Problem**: Headless mode may hide JavaScript and AJAX issues.

**Solution**: Always use headless mode for debugging:
```javascript
// CORRECT - Debug configuration
const browser = await p.webkit.launch(headless=false); // MANDATORY
const context = await browser.newContext();
const page = await context.newPage();

// Add screenshots for debugging
await page.screenshot(path='debug_result.png');
```

### Test Organization for AJAX Features
**Problem**: AJAX functionality requires comprehensive testing of both client and server sides.

**Solution**: Create dedicated test files for AJAX features:
```
tests/playwright/
├── test_profile_editing_functionality.py  # AJAX form tests
├── debug_profile_submission.py            # Debug scripts
└── utils/
    └── ajax_helpers.py                    # AJAX test utilities
```
