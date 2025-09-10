# CSRF Security Implementation Guidelines

## Overview

This document provides comprehensive guidelines for implementing CSRF (Cross-Site Request Forgery) protection in the Vedfolnir application. All developers must follow these standards to ensure consistent and secure CSRF protection across the application.

## CSRF Protection Standards

### 1. Template Implementation

#### ✅ Correct Implementation

**POST Forms:**
```html
<!-- Use form.hidden_tag() for all POST forms -->
<form method="POST" action="/submit">
    {{ form.hidden_tag() }}
    <input type="text" name="data" required>
    <button type="submit">Submit</button>
</form>
```

**AJAX Requests:**
```javascript
// Use meta tag for CSRF token
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name=csrf-token]').getAttribute('content')
    },
    body: JSON.stringify(data)
});
```

#### ❌ Incorrect Implementation

**Never expose CSRF tokens:**
```html
<!-- WRONG: Exposes token in HTML source -->
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

<!-- WRONG: Token visible in HTML -->
<div data-csrf="{{ csrf_token() }}"></div>
```

**Never use CSRF tokens in GET forms:**
```html
<!-- WRONG: GET forms should not have CSRF tokens -->
<form method="GET" action="/search">
    {{ form.hidden_tag() }}  <!-- Remove this -->
    <input type="text" name="query">
</form>
```

### 2. Backend Implementation

#### Flask Route Protection

```python
from flask import request
from flask_wtf.csrf import validate_csrf
from app.core.security.core.csrf_token_manager import get_csrf_token_manager

@app.route('/api/endpoint', methods=['POST'])
@login_required
def protected_endpoint():
    # CSRF validation is automatic with Flask-WTF
    # Additional validation if needed:
    try:
        validate_csrf(request.headers.get('X-CSRFToken'))
    except ValidationError:
        return jsonify({'error': 'CSRF token invalid'}), 403
    
    # Process request
    return jsonify({'success': True})
```

#### Custom CSRF Validation

```python
from app.core.security.core.csrf_token_manager import get_csrf_token_manager

def validate_custom_csrf(token, session_id=None):
    """Custom CSRF validation for special cases"""
    csrf_manager = get_csrf_token_manager()
    return csrf_manager.validate_token(token, session_id)
```

### 3. JavaScript Standards

#### CSRF Handler Usage

```javascript
// Use the centralized CSRF handler
import { CSRFHandler } from '/static/js/csrf-handler.js';

// Initialize CSRF handler
const csrfHandler = new CSRFHandler();

// Make CSRF-protected AJAX request
csrfHandler.makeRequest('/api/endpoint', {
    method: 'POST',
    data: { key: 'value' }
}).then(response => {
    // Handle response
}).catch(error => {
    // Handle CSRF errors automatically
});
```

#### Manual CSRF Token Handling

```javascript
// Get CSRF token from meta tag
function getCSRFToken() {
    return document.querySelector('meta[name=csrf-token]').getAttribute('content');
}

// Add CSRF token to all AJAX requests
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
        }
    }
});
```

## Security Requirements

### 1. Mandatory CSRF Protection

- **All POST, PUT, PATCH, DELETE requests** must include CSRF protection
- **All forms that modify data** must use `{{ form.hidden_tag() }}`
- **All AJAX requests that modify data** must include `X-CSRFToken` header

### 2. Token Visibility

- **CSRF tokens must never be visible** in HTML source code
- **Use hidden form fields** or secure meta tags only
- **Never log CSRF tokens** in application logs

### 3. Token Management

- **Tokens must be session-bound** and expire appropriately
- **Generate new tokens** after authentication state changes
- **Validate token entropy** and format before processing

## Implementation Checklist

### Template Security Checklist

- [ ] All POST forms use `{{ form.hidden_tag() }}`
- [ ] No direct `{{ csrf_token() }}` calls in templates
- [ ] GET forms do not include CSRF tokens
- [ ] Modal forms include proper CSRF protection
- [ ] AJAX endpoints use meta tag for token retrieval

### Backend Security Checklist

- [ ] All state-changing endpoints validate CSRF tokens
- [ ] Custom validation uses approved CSRF manager
- [ ] Error handling preserves form data when appropriate
- [ ] CSRF violations are logged for security monitoring

### JavaScript Security Checklist

- [ ] All AJAX requests include CSRF headers
- [ ] CSRF handler is used for dynamic requests
- [ ] Token refresh is implemented for long sessions
- [ ] Error handling includes CSRF failure recovery

## Code Review Standards

### Required Reviews

1. **Template Changes**: Any template modification must be reviewed for CSRF compliance
2. **Form Additions**: New forms require CSRF implementation review
3. **AJAX Endpoints**: New AJAX functionality requires CSRF validation review
4. **Security Changes**: Any security-related changes require senior developer review

### Review Checklist

```markdown
## CSRF Security Review Checklist

### Template Review
- [ ] POST forms use `{{ form.hidden_tag() }}`
- [ ] No exposed CSRF tokens in HTML
- [ ] GET forms exclude CSRF tokens
- [ ] Modal forms include CSRF protection

### Backend Review
- [ ] State-changing endpoints validate CSRF
- [ ] Error handling is secure and user-friendly
- [ ] Logging excludes sensitive token data
- [ ] Custom validation uses approved methods

### Frontend Review
- [ ] AJAX requests include CSRF headers
- [ ] Token retrieval uses secure methods
- [ ] Error handling includes retry mechanisms
- [ ] Long-session token refresh is implemented

### Security Review
- [ ] No information disclosure vulnerabilities
- [ ] Proper error messages without token exposure
- [ ] Session binding is correctly implemented
- [ ] Token entropy and format validation
```

## Testing Requirements

### Unit Tests

```python
def test_csrf_protection():
    """Test CSRF protection on protected endpoints"""
    # Test without CSRF token (should fail)
    response = client.post('/protected-endpoint', data={'test': 'data'})
    assert response.status_code == 403
    
    # Test with valid CSRF token (should succeed)
    with client.session_transaction() as sess:
        csrf_token = generate_csrf()
    
    response = client.post('/protected-endpoint', 
                          data={'test': 'data', 'csrf_token': csrf_token})
    assert response.status_code == 200
```

### Integration Tests

```python
def test_form_csrf_integration():
    """Test CSRF protection in form submissions"""
    # Get form page
    response = client.get('/form-page')
    assert 'csrf-token' in response.data.decode()
    
    # Submit form with CSRF token
    csrf_token = extract_csrf_token(response.data)
    response = client.post('/form-submit', 
                          data={'field': 'value', 'csrf_token': csrf_token})
    assert response.status_code == 200
```

## Security Monitoring

### Metrics to Track

1. **CSRF Violation Rate**: Number of CSRF failures per hour
2. **Compliance Rate**: Percentage of protected endpoints
3. **Token Exposure**: Detection of visible tokens in HTML
4. **Error Rate**: CSRF-related error frequency

### Alerting Thresholds

- **Critical**: >50 CSRF violations per hour
- **High**: >20 CSRF violations per hour
- **Medium**: >5 CSRF violations per hour
- **Low**: Any token exposure detected

## Common Pitfalls

### 1. Token Exposure
```html
<!-- WRONG: Token visible in HTML -->
<script>
    var csrfToken = "{{ csrf_token() }}";
</script>

<!-- CORRECT: Use meta tag -->
<meta name="csrf-token" content="{{ csrf_token() }}">
```

### 2. GET Form Protection
```html
<!-- WRONG: CSRF token in GET form -->
<form method="GET" action="/search">
    {{ form.hidden_tag() }}
</form>

<!-- CORRECT: No CSRF token needed -->
<form method="GET" action="/search">
    <input type="text" name="query">
</form>
```

### 3. AJAX Header Missing
```javascript
// WRONG: Missing CSRF header
fetch('/api/endpoint', {
    method: 'POST',
    body: JSON.stringify(data)
});

// CORRECT: Include CSRF header
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify(data)
});
```

## Compliance Validation

### Automated Checks

The application includes automated CSRF compliance validation:

```bash
# Run CSRF compliance scan
python scripts/security/run_csrf_audit.py

# Run template security audit
python -m security.audit.csrf_template_scanner

# Run comprehensive security tests
python scripts/testing/run_security_performance_tests.py
```

### Manual Validation

1. **Template Audit**: Review all templates for CSRF compliance
2. **Endpoint Testing**: Test all state-changing endpoints
3. **JavaScript Review**: Verify AJAX CSRF implementation
4. **Error Handling**: Test CSRF failure scenarios

## Incident Response

### CSRF Violation Response

1. **Immediate**: Check for attack patterns in logs
2. **Short-term**: Analyze violation source and frequency
3. **Long-term**: Implement additional protection if needed

### Token Exposure Response

1. **Immediate**: Identify and fix token exposure
2. **Short-term**: Regenerate affected session tokens
3. **Long-term**: Implement additional monitoring

## Training and Awareness

### Developer Training Topics

1. **CSRF Attack Vectors**: Understanding the threat
2. **Implementation Standards**: Following security guidelines
3. **Testing Procedures**: Validating CSRF protection
4. **Incident Response**: Handling security issues

### Security Awareness

- Regular security training sessions
- Code review best practices
- Security testing integration
- Incident response procedures

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Flask-WTF CSRF Protection](https://flask-wtf.readthedocs.io/en/stable/csrf.html)
- [Vedfolnir Security Documentation](../SECURITY.md)

---

**Document Version**: 1.0  
**Last Updated**: {{ current_date }}  
**Next Review**: {{ next_review_date }}