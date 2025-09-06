# Landing Page Integration Tests

## Overview

This document describes the comprehensive integration tests implemented for the Flask landing page functionality. These tests verify the complete user journey flows and session state transitions as specified in the requirements.

## Test File

**Location**: `tests/integration/test_landing_page_integration.py`

## Test Coverage

### Requirements Tested

The integration tests cover the following requirements:

- **Requirement 1.1**: Anonymous visitor sees landing page
- **Requirement 1.2**: Authenticated user sees dashboard  
- **Requirement 1.3**: Anonymous user with previous session redirects to login
- **Requirement 6.1**: CTA buttons navigate to registration
- **Requirement 6.2**: Login link navigates to login page

### Test Cases Implemented

#### 1. `test_new_anonymous_user_gets_landing_page`
- **Purpose**: Verify completely new anonymous users see the landing page
- **Verification**: 
  - Landing page content is displayed
  - Contains key elements (Vedfolnir, AI-Powered Accessibility, Fediverse)
  - Contains call-to-action elements
  - Contains features and accessibility content

#### 2. `test_authenticated_user_bypasses_landing_page`
- **Purpose**: Verify authenticated users bypass landing page and see dashboard
- **Process**: Creates test user, logs in, visits root URL
- **Verification**:
  - Dashboard content is displayed
  - Landing page content is NOT displayed
  - Contains authenticated user elements (Logout)

#### 3. `test_returning_user_redirected_to_login`
- **Purpose**: Verify users with previous session cookies are redirected to login
- **Process**: Sets session cookies to simulate returning user
- **Verification**:
  - Receives 302 redirect response
  - Redirected to login page
  - Login page is properly displayed

#### 4. `test_landing_to_registration_flow`
- **Purpose**: Test complete user journey from landing page to registration
- **Process**: Visits landing page, follows registration links
- **Verification**:
  - Landing page contains registration links
  - Registration page is accessible
  - Registration form is properly displayed

#### 5. `test_landing_to_login_flow`
- **Purpose**: Test user journey from landing page to login
- **Process**: Visits landing page, follows login links
- **Verification**:
  - Landing page contains login links
  - Login page is accessible
  - Login form is properly displayed

#### 6. `test_logout_returns_to_appropriate_page`
- **Purpose**: Test that logout behavior returns user to appropriate page
- **Process**: Creates user, logs in, verifies dashboard, logs out
- **Verification**:
  - User can successfully log in and see dashboard
  - Logout process completes successfully
  - After logout, user sees landing page (not dashboard)

#### 7. `test_session_state_transitions`
- **Purpose**: Test various session state transitions comprehensively
- **Process**: Tests all state transitions in sequence
- **Verification**:
  - New user → Landing page
  - Returning user → Redirect to login
  - Authenticated user → Dashboard
  - Logout → Appropriate page

#### 8. `test_landing_page_accessibility_elements`
- **Purpose**: Test that landing page contains required accessibility elements
- **Verification**:
  - Semantic HTML elements (main, h1, h2)
  - Skip-to-content links
  - Proper meta tags
  - Structured data (JSON-LD)

#### 9. `test_landing_page_cta_buttons_functionality`
- **Purpose**: Test that CTA buttons have correct URLs and functionality
- **Verification**:
  - Registration CTA is present and functional
  - Login link is present and functional
  - Both target pages are accessible

#### 10. `test_landing_page_performance`
- **Purpose**: Test landing page performance characteristics
- **Verification**:
  - Response time under 2 seconds
  - Reasonable content length
  - Successful HTTP response

#### 11. `test_error_handling_and_fallbacks`
- **Purpose**: Test error handling and fallback behavior
- **Process**: Tests with malformed session data
- **Verification**:
  - System handles invalid session data gracefully
  - Falls back to landing page display

## Test Infrastructure

### Helper Methods

- **`_get_csrf_token(url)`**: Extracts CSRF tokens from pages for form submissions
- **`_create_test_user(...)`**: Creates test users with proper credentials and verification
- **`_login_user(username, password)`**: Performs user login via HTTP requests
- **`_logout_user()`**: Performs user logout via HTTP requests
- **`_clear_session_cookies()`**: Clears session cookies to simulate new users
- **`_set_previous_session_cookie()`**: Sets cookies to simulate returning users

### Test Configuration

- **Base URL**: `http://127.0.0.1:5000`
- **Test Framework**: Python `unittest`
- **HTTP Client**: `requests` library
- **Database**: Uses existing test database with cleanup
- **User Management**: Integrates with `tests.test_helpers` for user creation/cleanup

## Running the Tests

### Prerequisites

1. Web application must be running on `http://127.0.0.1:5000`
2. Database must be accessible and configured
3. Redis session backend must be available

### Start Web Application

```bash
# For testing (non-blocking)
python web_app.py & sleep 10
```

### Run Tests

```bash
# Run all landing page integration tests
python -m unittest tests.integration.test_landing_page_integration.TestLandingPageIntegration -v

# Run specific test
python -m unittest tests.integration.test_landing_page_integration.TestLandingPageIntegration.test_new_anonymous_user_gets_landing_page -v
```

## Test Results

All tests pass successfully and verify:

✅ **New anonymous users** see the landing page  
✅ **Authenticated users** bypass landing page and see dashboard  
✅ **Returning users** are redirected to login page  
✅ **Landing to registration flow** works correctly  
✅ **Landing to login flow** works correctly  
✅ **Logout behavior** returns to appropriate page  
✅ **Session state transitions** work correctly  
✅ **Accessibility elements** are present  
✅ **CTA buttons** function correctly  
✅ **Performance** meets requirements  
✅ **Error handling** works gracefully  

## Integration with CI/CD

These tests can be integrated into continuous integration pipelines:

```bash
# Example CI script
#!/bin/bash
# Start web application in background
python web_app.py & 
WEB_PID=$!
sleep 10

# Run integration tests
python -m unittest tests.integration.test_landing_page_integration.TestLandingPageIntegration -v

# Cleanup
kill $WEB_PID
```

## Maintenance Notes

- Tests use mock users that are automatically cleaned up
- Session cookies are managed per test to ensure isolation
- CSRF tokens are properly extracted and used for form submissions
- Tests handle redirect loops and timeout scenarios gracefully
- All HTTP requests include proper error handling and logging

## Future Enhancements

Potential improvements for the test suite:

1. **Browser Testing**: Add Playwright tests for full browser automation
2. **Performance Monitoring**: Add detailed performance metrics collection
3. **Accessibility Validation**: Integrate automated accessibility testing tools
4. **Load Testing**: Add concurrent user simulation tests
5. **Mobile Testing**: Add mobile-specific user journey tests