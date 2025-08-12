# Frontend JavaScript Tests

This directory contains frontend JavaScript tests for the session synchronization functionality.

## Test Files

### test_session_sync.html
Browser-based test runner that can be opened directly in a web browser to test the SessionSync class functionality. This provides a visual interface for running tests and viewing results.

**Usage:**
1. Open `test_session_sync.html` in a web browser
2. Tests will run automatically after page load
3. View results in the browser interface
4. Use "Run All Tests" button to re-run tests
5. Use "Clear Results" button to clear the display

### test_session_sync.js
Node.js compatible test file that can be run from the command line for automated testing and CI/CD integration.

**Usage:**
```bash
# Run from the project root
node tests/frontend/test_session_sync.js

# Or run from the tests/frontend directory
cd tests/frontend
node test_session_sync.js
```

## Test Coverage

The tests cover the following requirements from the session management system specification:

### Requirements 2.1, 2.2 - SessionSync Class Initialization and Tab Identification
- ✅ SessionSync class initialization
- ✅ Tab ID generation uniqueness
- ✅ Session initialization conditions

### Requirements 2.2, 2.3 - Cross-tab Storage Event Handling and Synchronization
- ✅ Storage event handling setup
- ✅ Cross-tab session state synchronization
- ✅ Platform switch event handling

### Requirements 2.4, 2.5 - Session Validation and Expiration Handling
- ✅ Session validation with server
- ✅ Session expiration handling
- ✅ Session state change detection
- ✅ Performance metrics tracking
- ✅ Debounced sync functionality

## Test Features

### Mock Framework
The tests include a comprehensive mocking framework that simulates:
- Browser DOM environment
- LocalStorage with event simulation
- Fetch API for server communication
- Navigator online/offline states
- Window and document event handling

### Test Utilities
- Asynchronous test execution
- Performance timing
- Error handling and reporting
- Requirement traceability
- Visual test results (HTML version)

### Browser Compatibility
The HTML test runner works in modern browsers and includes:
- Visual test results with pass/fail indicators
- Error details and stack traces
- Performance metrics
- Requirement mapping
- Interactive controls

### CI/CD Integration
The Node.js test file provides:
- Command-line execution
- Exit codes for CI/CD integration
- Structured test output
- Automated test discovery
- Mock environment setup

## Running Tests

### Browser Testing
1. Start the web application: `python web_app.py`
2. Navigate to: `http://localhost:5000/tests/frontend/test_session_sync.html`
3. View test results in the browser

### Command Line Testing
```bash
# From project root
node tests/frontend/test_session_sync.js

# Expected output:
# Running SessionSync Frontend Tests...
# 
# ✓ SessionSync class initialization (2ms) [2.1, 2.2]
# ✓ Tab ID generation uniqueness (1ms) [2.1]
# ✓ Storage event handling setup (5ms) [2.2, 2.3]
# ✓ Cross-tab session state synchronization (52ms) [2.2, 2.3]
# ✓ Session validation with server (3ms) [2.4, 2.5]
# ✓ Session expiration handling (2ms) [2.5]
# ✓ Platform switch event handling (51ms) [2.3, 2.4]
# ✓ Session state change detection (1ms) [2.4]
# ✓ Performance metrics tracking (1ms) [2.5]
# ✓ Debounced sync functionality (151ms) [2.5]
# 
# Tests: 10 | Passed: 10 | Failed: 0 | Success Rate: 100%
```

## Integration with Existing Test Suite

These frontend tests complement the existing backend session management tests and can be integrated into the project's testing workflow:

1. **Manual Testing**: Use the HTML test runner during development
2. **Automated Testing**: Include the Node.js test in CI/CD pipelines
3. **Integration Testing**: Combine with backend tests for full coverage
4. **Performance Testing**: Monitor test execution times and metrics

## Test Maintenance

When updating the SessionSync class:
1. Update corresponding test cases
2. Add new tests for new functionality
3. Update requirement mappings
4. Verify both HTML and Node.js versions work
5. Update this README with any changes

## Troubleshooting

### Common Issues
- **Tests fail in browser**: Check console for JavaScript errors
- **Node.js tests fail**: Ensure Node.js version compatibility
- **Mock issues**: Verify mock setup matches actual browser APIs
- **Timing issues**: Adjust sleep delays for slower environments

### Debug Mode
Add `console.log` statements to tests or use browser developer tools for debugging the HTML version.