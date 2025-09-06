# Landing Page Frontend Accessibility and UI Tests

This directory contains comprehensive frontend tests for the Flask landing page using Playwright, focusing on accessibility compliance, responsive design, and user interface functionality.

## Overview

The test suite validates that the landing page meets all specified requirements:

### Accessibility Requirements (3.1-3.6)
- **3.1**: Semantic HTML elements for proper screen reader navigation
- **3.2**: Appropriate alt text for all images
- **3.3**: Proper color contrast ratios for text readability
- **3.4**: Fully navigable using keyboard-only input
- **3.5**: Proper heading hierarchy (h1, h2, h3) for content structure
- **3.6**: Skip-to-content links for screen reader users

### Responsive Design Requirements (4.1-4.3)
- **4.1**: Display all content in readable format on mobile devices
- **4.2**: Maintain proper layout and functionality on tablets
- **4.3**: Utilize full screen width effectively on desktop

### Interactive Elements Requirements (6.4-6.6)
- **6.4**: Visual feedback for interactive elements
- **6.5**: Button functionality and navigation
- **6.6**: Hover states and visual feedback

## Test Files

### `test_landing_page_accessibility.py`
Comprehensive accessibility testing using Playwright including:
- WCAG compliance validation using axe-core (injected via CDN)
- Keyboard navigation testing
- Screen reader compatibility
- Semantic HTML structure validation
- Color contrast ratio testing
- Cross-browser accessibility testing (Chromium, Firefox, WebKit)

### `test_landing_page_ui.py`
User interface and visual testing using Playwright including:
- Responsive design across multiple screen sizes
- Visual layout validation
- Interactive element functionality
- Hover effects and visual feedback
- Performance testing
- JavaScript functionality testing

### `run_landing_page_tests.py`
Test runner with comprehensive reporting:
- Run all tests or specific test suites
- Detailed test reports with requirements coverage
- Performance metrics and recommendations
- Multiple verbosity levels

## Prerequisites

### System Requirements
- Python 3.8+
- Node.js (for Playwright browser management)

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r tests/frontend/requirements-test.txt
   ```

2. **Install Playwright browsers:**
   ```bash
   # This downloads Chromium, Firefox, and WebKit browsers
   playwright install
   ```

3. **Verify installation:**
   ```bash
   # Test Playwright installation
   playwright --version
   
   # List installed browsers
   playwright install --dry-run
   ```

## Running Tests

### Quick Start
```bash
# Run all tests with detailed report
python tests/frontend/run_landing_page_tests.py --all --report

# Run quick test suite (critical tests only)
python tests/frontend/run_landing_page_tests.py --quick
```

### Specific Test Suites
```bash
# Accessibility tests only
python tests/frontend/run_landing_page_tests.py --accessibility

# UI tests only
python tests/frontend/run_landing_page_tests.py --ui

# Generate detailed report
python tests/frontend/run_landing_page_tests.py --report
```

### Individual Test Files
```bash
# Run accessibility tests directly
python -m unittest tests.frontend.test_landing_page_accessibility -v

# Run UI tests directly
python -m unittest tests.frontend.test_landing_page_ui -v
```

### Verbosity Levels
```bash
# Minimal output
python tests/frontend/run_landing_page_tests.py --all -v

# Standard output (default)
python tests/frontend/run_landing_page_tests.py --all -vv

# Verbose output
python tests/frontend/run_landing_page_tests.py --all -vvv
```

## Test Categories

### Responsive Design Testing
Tests across multiple screen sizes:
- **Mobile**: 375x667, 414x896, 360x640, 320x568
- **Tablet**: 768x1024, 834x1112, 1024x1366, 800x1280
- **Desktop**: 1920x1080, 1366x768, 1440x900, 2560x1440

### Accessibility Testing
- **WCAG Compliance**: Automated testing with axe-core
- **Keyboard Navigation**: Full keyboard accessibility
- **Screen Reader Support**: Semantic HTML and ARIA
- **Color Contrast**: Text readability validation
- **Focus Management**: Visual focus indicators

### Cross-Browser Testing
- **Chromium**: Primary testing browser (Google Chrome engine)
- **Firefox**: Secondary testing browser
- **WebKit**: Safari engine testing (cross-platform)

### Performance Testing
- Page load time validation
- JavaScript functionality testing
- Image loading optimization
- Critical rendering path

## Test Reports

The test runner generates comprehensive reports including:

### Summary Statistics
- Total tests run
- Pass/fail/skip counts
- Success rate percentage
- Test duration

### Requirements Coverage
- Detailed mapping to specification requirements
- Compliance status for each requirement
- Accessibility standards coverage

### Failure Analysis
- Detailed failure descriptions
- Error stack traces
- Recommendations for fixes

### Performance Metrics
- Page load times
- Rendering performance
- JavaScript execution time

## Troubleshooting

### Common Issues

**Playwright browsers not installed:**
```bash
# Install all browsers
playwright install

# Install specific browser
playwright install chromium
```

**Web application not starting:**
```bash
# Ensure web app is not already running
pkill -f "python web_app.py"

# Check if port 5000 is available
lsof -i :5000
```

**Browser not opening:**
```bash
# For headless testing, set headless=True in test configuration
# For visible testing, ensure display is available
# Check browser installation: playwright install --dry-run
```

**Playwright timeouts:**
```bash
# Increase timeout values in test configuration
# Check network connectivity
# Verify application is responding
# Use page.wait_for_load_state() for better synchronization
```

### Debug Mode

For debugging test failures:

1. **Disable headless mode** in test configuration (set `headless=False`)
2. **Add breakpoints** in test code
3. **Use browser developer tools** during test execution
4. **Enable verbose logging** with `-vvv` flag
5. **Use Playwright's debug mode**: `PWDEBUG=1 python test_file.py`

### Manual Verification

After automated tests pass, perform manual verification:

1. **Screen Reader Testing**: Test with actual screen readers (NVDA, JAWS, VoiceOver)
2. **Real Device Testing**: Test on actual mobile devices and tablets
3. **Network Conditions**: Test with slow network connections
4. **User Scenarios**: Test complete user workflows

## Continuous Integration

For CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Install Playwright
  run: |
    pip install playwright
    playwright install --with-deps

- name: Run Landing Page Tests
  run: |
    python tests/frontend/run_landing_page_tests.py --all --report
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*` for test methods
2. **Add docstrings**: Document what each test validates
3. **Include requirement references**: Map tests to specification requirements
4. **Use subTests**: For testing multiple scenarios
5. **Add cleanup**: Ensure proper test cleanup with `tearDown`
6. **Update documentation**: Update this README for new test categories

## Best Practices

### Test Design
- **Atomic tests**: Each test should validate one specific behavior
- **Independent tests**: Tests should not depend on each other
- **Descriptive names**: Test names should clearly indicate what is being tested
- **Comprehensive coverage**: Test both positive and negative scenarios

### Accessibility Testing
- **Multiple methods**: Combine automated and manual testing
- **Real assistive technology**: Test with actual screen readers when possible
- **Keyboard-only navigation**: Test complete workflows with keyboard only
- **Color blindness**: Test with color blindness simulators

### Performance Testing
- **Realistic conditions**: Test under realistic network and device conditions
- **Multiple runs**: Average results across multiple test runs
- **Baseline comparison**: Compare against performance baselines
- **Resource monitoring**: Monitor CPU, memory, and network usage

## Playwright Advantages

### Why Playwright over Selenium
- **Faster execution**: Native browser automation
- **Better reliability**: Auto-wait for elements
- **Modern browsers**: Latest Chromium, Firefox, WebKit
- **Network interception**: Mock APIs and test offline scenarios
- **Screenshots/videos**: Built-in visual debugging
- **Mobile testing**: Device emulation built-in

### Playwright Features Used
- **Auto-waiting**: Automatically waits for elements to be ready
- **Cross-browser**: Tests run on Chromium, Firefox, and WebKit
- **Mobile emulation**: Test responsive design with device emulation
- **Network control**: Intercept and modify network requests
- **Screenshots**: Capture screenshots for debugging
- **Trace viewer**: Record and replay test execution

## Resources

### Accessibility Guidelines
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Screen Reader Testing](https://webaim.org/articles/screenreader_testing/)
- [axe-core Documentation](https://github.com/dequelabs/axe-core)

### Testing Tools
- [Playwright Documentation](https://playwright.dev/python/)
- [Playwright Best Practices](https://playwright.dev/python/best-practices)
- [Color Contrast Analyzers](https://www.tpgi.com/color-contrast-checker/)

### Browser Developer Tools
- [Chrome DevTools Accessibility](https://developers.google.com/web/tools/chrome-devtools/accessibility)
- [Firefox Accessibility Inspector](https://developer.mozilla.org/en-US/docs/Tools/Accessibility_inspector)
- [Safari Web Inspector](https://webkit.org/web-inspector/)

## Support

For issues with the test suite:

1. **Check prerequisites**: Ensure all dependencies are installed
2. **Review logs**: Check test output for specific error messages
3. **Verify environment**: Ensure web application is running correctly
4. **Update dependencies**: Ensure all packages are up to date
5. **Consult documentation**: Review Playwright documentation