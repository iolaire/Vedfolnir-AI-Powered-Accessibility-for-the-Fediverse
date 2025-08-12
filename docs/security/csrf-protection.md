# CSRF Protection Implementation

## Overview

Vedfolnir implements comprehensive Cross-Site Request Forgery (CSRF) protection using multiple layers of security to prevent unauthorized actions on behalf of authenticated users.

## Implementation Details

### 1. Flask-WTF CSRF Protection

All forms use Flask-WTF's built-in CSRF protection:

```html
<form method="POST" action="{{ url_for('some_endpoint') }}">
    {{ form.hidden_tag() }}
    <!-- form fields -->
</form>
```

### 2. JavaScript CSRF Handler

For AJAX requests, we use a centralized CSRF handler (`static/js/csrf-handler.js`):

```javascript
// Automatic CSRF token injection for all AJAX requests
window.csrfHandler.secureFetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
});
```

### 3. Meta Tag Token

CSRF tokens are available in the page head for JavaScript access:

```html
<meta name="csrf-token" content="{{ csrf_token() }}">
```

## Security Features

### Token Management
- **Automatic Refresh**: Tokens are refreshed before expiry
- **Retry Logic**: Failed requests are automatically retried with fresh tokens
- **Fallback Handling**: Multiple token sources for reliability

### Request Protection
- **State-Changing Requests**: All POST, PUT, PATCH, DELETE requests require CSRF tokens
- **AJAX Integration**: Automatic token injection for fetch() and jQuery requests
- **Form Validation**: Server-side token validation for all form submissions

### Error Handling
- **Graceful Degradation**: Fallback to meta tag tokens if API refresh fails
- **User Feedback**: Clear error messages for CSRF validation failures
- **Automatic Recovery**: Transparent token refresh and request retry

## Best Practices

### Template Usage

✅ **Correct**: Use form.hidden_tag() for WTForms
```html
<form method="POST">
    {{ form.hidden_tag() }}
    <!-- fields -->
</form>
```

❌ **Incorrect**: Manual CSRF token insertion
```html
<form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <!-- fields -->
</form>
```

### JavaScript Usage

✅ **Correct**: Use csrfHandler.secureFetch()
```javascript
window.csrfHandler.secureFetch('/api/endpoint', {
    method: 'POST',
    body: formData
});
```

❌ **Incorrect**: Manual token handling
```javascript
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
    },
    body: formData
});
```

## Configuration

### Flask Configuration
```python
# CSRF settings in web_app.py
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
app.config['WTF_CSRF_SSL_STRICT'] = False  # Allow HTTP in development
app.config['WTF_CSRF_CHECK_DEFAULT'] = True
```

### JavaScript Configuration
```javascript
// CSRF handler settings
const csrfHandler = new CSRFHandler({
    retryAttempts: 3,
    retryDelay: 1000,
    tokenExpiry: 3600000  // 1 hour
});
```

## Security Audit Results

Current CSRF protection status:
- **Compliance Score**: 74%
- **Critical Issues**: 0
- **High Priority Issues**: Resolved
- **Forms Protected**: 100%
- **AJAX Requests Protected**: 100%

## Troubleshooting

### Common Issues

1. **Token Expired Errors**
   - Solution: Tokens are automatically refreshed
   - Check: Browser console for refresh failures

2. **AJAX Requests Failing**
   - Solution: Use `window.csrfHandler.secureFetch()`
   - Check: Network tab for missing X-CSRFToken header

3. **Form Submission Errors**
   - Solution: Ensure `{{ form.hidden_tag() }}` is present
   - Check: Form HTML for CSRF token field

### Debug Mode

Enable CSRF debugging in development:
```python
import logging
logging.getLogger('flask_wtf.csrf').setLevel(logging.DEBUG)
```

## Testing

### Manual Testing
1. Submit forms without CSRF tokens (should fail)
2. Submit forms with invalid tokens (should fail)
3. Submit forms with valid tokens (should succeed)
4. Test AJAX requests with automatic token handling

### Automated Testing
```python
def test_csrf_protection(client):
    # Test form submission without CSRF token
    response = client.post('/api/endpoint', data={})
    assert response.status_code == 403
    
    # Test with valid CSRF token
    with client.session_transaction() as sess:
        sess['csrf_token'] = 'valid_token'
    response = client.post('/api/endpoint', data={'csrf_token': 'valid_token'})
    assert response.status_code == 200
```

## Monitoring

CSRF protection is monitored through:
- Security audit scripts
- Error logging and reporting
- Performance metrics for token refresh
- User experience metrics for failed requests

## Updates and Maintenance

1. **Regular Audits**: Run `python scripts/security/run_csrf_audit.py`
2. **Token Rotation**: Tokens are automatically rotated
3. **Security Updates**: Keep Flask-WTF updated
4. **Code Reviews**: All new forms and AJAX requests reviewed for CSRF protection