# Design Document

## Overview

The Flask landing page design implements a dual-route system that serves different content based on user authentication status. Anonymous users receive a compelling marketing-focused landing page, while authenticated users continue to access the existing dashboard. The design leverages the existing Flask blueprint architecture, template inheritance system, and styling conventions to ensure seamless integration.

## Architecture

### Route Logic Design

The core architectural decision centers on modifying the existing main blueprint's index route to implement conditional rendering with session awareness:

```python
@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        # Existing dashboard logic for authenticated users
        return render_dashboard()
    elif has_previous_session():
        # User was previously logged in, redirect to login
        return redirect(url_for('user_management.login'))
    else:
        # Completely new user, show landing page
        return render_template('landing.html')
```

This approach maintains backward compatibility while providing an optimal user experience for returning users and new visitors.

### Template Inheritance Structure

The landing page will extend the existing `base.html` template but with modifications to handle the anonymous user state:

- **Base Template Modifications**: The base template's navigation will be conditionally rendered to show appropriate links for anonymous users
- **Landing Template**: A new `templates/landing.html` that extends base.html and provides landing-specific content
- **CSS Integration**: Utilizes existing Bootstrap classes and custom CSS from the current styling system

### Authentication Integration

The design integrates with Flask-Login's authentication system and session management:

- Uses `current_user.is_authenticated` to determine authenticated state
- Checks for previous session indicators to detect returning users
- Maintains existing login/logout functionality
- Preserves all existing authentication middleware and security measures

### Session Detection Logic

To determine if a user has previously logged in, the system will check for:

1. **Flask Session Data**: Presence of session data indicating previous authentication
2. **Remember Me Cookies**: Flask-Login remember me tokens
3. **Session History**: Custom session tracking cookies (if implemented)

**Implementation**:
```python
def has_previous_session():
    """
    Detect if user has previously logged in based on session indicators
    Returns: Boolean indicating if user has previous session
    """
    # Check for Flask-Login remember token
    if request.cookies.get('remember_token'):
        return True
    
    # Check for session data indicating previous login
    if session.get('_user_id') or session.get('user_id'):
        return True
    
    # Check for custom session tracking
    if request.cookies.get('vedfolnir_returning_user'):
        return True
    
    return False
```

## Components and Interfaces

### 1. Route Handler Component

**File**: `app/blueprints/main/routes.py`

**Responsibilities**:
- Detect user authentication status
- Check for previous session indicators (cookies, session data)
- Route to appropriate template/redirect based on user state
- Maintain existing dashboard functionality for authenticated users
- Redirect returning users to login page
- Serve landing page content for completely new users

**Interface**:
```python
@main_bp.route('/')
def index():
    """
    Serves dashboard for authenticated users, redirects returning users to login,
    and shows landing page for new visitors
    Returns: Flask Response object with appropriate template or redirect
    """
```

### 2. Landing Page Template Component

**File**: `templates/landing.html`

**Responsibilities**:
- Extend base.html template
- Render hero section with value proposition
- Display feature highlights and benefits
- Provide clear calls-to-action
- Ensure responsive design and accessibility

**Key Sections**:
- Hero section with main headline and CTA
- Features section with three key benefits
- Target audience section
- Final call-to-action section

### 3. Navigation Component Enhancement

**File**: `templates/base.html` (modifications)

**Responsibilities**:
- Conditionally render navigation based on authentication status
- Show "Login" link for anonymous users
- Maintain existing navigation for authenticated users
- Ensure consistent styling across both states

### 4. CSS Styling Component

**Approach**: Extend existing CSS rather than create new files

**Responsibilities**:
- Landing page specific styles integrated into existing CSS files
- Responsive design using existing Bootstrap framework
- Consistent color scheme and typography
- Accessibility-compliant styling

## Data Models

### No New Data Models Required

The landing page is purely presentational and doesn't require new database models. It leverages:

- Existing User model for authentication checks
- Existing template context processors for CSRF tokens
- Existing Flask-Login user session management

### Template Context Data

The landing page template receives minimal context data:

```python
{
    'csrf_token': 'generated_csrf_token',
    'current_user': AnonymousUserMixin(),  # Flask-Login anonymous user
    'page_title': 'Vedfolnir - AI-Powered Accessibility for the Fediverse'
}
```

## Error Handling

### Authentication State Errors

**Scenario**: Flask-Login authentication system failures
**Handling**: Graceful fallback to landing page with error logging

**Implementation**:
```python
try:
    if current_user.is_authenticated:
        return render_dashboard()
except Exception as e:
    current_app.logger.error(f"Authentication check failed: {e}")
    # Fallback to landing page
    return render_template('landing.html')
```

### Template Rendering Errors

**Scenario**: Template file missing or rendering failures
**Handling**: Fallback to basic HTML response with error logging

**Implementation**:
```python
try:
    return render_template('landing.html')
except TemplateNotFound:
    current_app.logger.error("Landing page template not found")
    return render_template_string(FALLBACK_LANDING_HTML)
```

### Static Asset Loading Errors

**Scenario**: CSS or JavaScript files fail to load
**Handling**: Graceful degradation with inline fallback styles

**Implementation**: Include critical CSS inline in the template head section as fallback

## Testing Strategy

### Unit Tests

**File**: `tests/unit/test_landing_page.py`

**Test Cases**:
1. **test_new_anonymous_user_gets_landing_page**: Verify completely new users receive landing page
2. **test_authenticated_user_gets_dashboard**: Verify authenticated users receive dashboard
3. **test_returning_user_redirected_to_login**: Verify users with previous session cookies are redirected to login
4. **test_landing_page_template_renders**: Verify template renders without errors
5. **test_landing_page_contains_required_elements**: Verify all required content is present
6. **test_cta_buttons_have_correct_urls**: Verify call-to-action buttons link correctly

### Integration Tests

**File**: `tests/integration/test_landing_page_integration.py`

**Test Cases**:
1. **test_landing_to_registration_flow**: Test complete user journey from landing to registration
2. **test_landing_to_login_flow**: Test user journey from landing to login
3. **test_authenticated_user_bypass**: Test that logged-in users skip landing page
4. **test_logout_returns_to_landing**: Test that logout redirects to landing page

### Frontend Tests

**File**: `tests/frontend/test_landing_page_ui.py`

**Test Cases**:
1. **test_responsive_design**: Verify layout works on different screen sizes
2. **test_accessibility_compliance**: Verify WCAG compliance
3. **test_cta_button_interactions**: Verify button hover states and clicks
4. **test_navigation_functionality**: Verify all links work correctly

### Performance Tests

**Considerations**:
- Page load time should be under 2 seconds
- Template rendering should be under 100ms
- No additional database queries for anonymous users
- Minimal impact on existing dashboard performance

## Security Considerations

### CSRF Protection

The landing page doesn't include forms, but maintains CSRF token generation for consistency with the existing template system.

### Content Security Policy

Landing page content is static and doesn't introduce new security vectors. Existing CSP policies remain effective.

### Input Validation

No user input is processed on the landing page itself. All input validation occurs on the registration and login pages that users navigate to.

### Session Security

Anonymous users don't receive sessions, reducing attack surface. Existing session security measures remain unchanged for authenticated users.

## SEO and Accessibility Design

### SEO Optimization

**Meta Tags**:
```html
<title>Vedfolnir - AI-Powered Accessibility for the Fediverse</title>
<meta name="description" content="Automated alt text generation for ActivityPub platforms. Make your social media content accessible with AI-powered image descriptions.">
<meta name="keywords" content="accessibility, alt text, ActivityPub, Mastodon, Pixelfed, AI, image descriptions">
```

**Structured Data**:
```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Vedfolnir",
  "description": "AI-powered accessibility tool for the Fediverse",
  "applicationCategory": "AccessibilityApplication"
}
```

### Accessibility Features

**Semantic HTML Structure**:
- Proper heading hierarchy (h1 → h2 → h3)
- Semantic elements (header, main, section, footer)
- ARIA labels for interactive elements

**Keyboard Navigation**:
- All interactive elements accessible via Tab key
- Skip-to-content link for screen readers
- Focus indicators for all focusable elements

**Screen Reader Optimization**:
- Descriptive alt text for all images
- Proper form labels and descriptions
- Logical reading order

## Performance Optimization

### Template Caching

Implement template caching for the landing page since content is static:

```python
@main_bp.route('/')
@cache.cached(timeout=3600)  # Cache for 1 hour
def index():
    # Implementation
```

### Asset Optimization

- Reuse existing CSS and JavaScript files
- Minimize additional HTTP requests
- Leverage existing CDN resources (Bootstrap, fonts)

### Database Query Optimization

The landing page requires zero database queries for anonymous users, ensuring optimal performance.

## Deployment Considerations

### Backward Compatibility

The design maintains 100% backward compatibility:
- Existing authenticated user workflows unchanged
- All existing routes and functionality preserved
- No breaking changes to API or template structure

### Rollback Strategy

If issues arise, the landing page can be disabled by modifying the route logic:

```python
@main_bp.route('/')
@login_required  # Re-add login requirement
def index():
    # Return to original dashboard-only logic
```

### Monitoring and Analytics

Consider adding analytics tracking to measure landing page effectiveness:
- Page view tracking
- Conversion rate from landing to registration
- User engagement metrics

This design provides a comprehensive solution that enhances the user experience for new visitors while maintaining the robust functionality that existing users depend on.