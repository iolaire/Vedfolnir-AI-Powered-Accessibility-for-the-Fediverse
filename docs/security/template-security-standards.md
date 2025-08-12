# Template Security Standards

## Overview

This document defines security standards for HTML templates in the Vedfolnir application. These standards ensure consistent security implementation across all user interfaces and prevent common web vulnerabilities.

## CSRF Protection Standards

### Form Security Requirements

#### POST Forms
All POST forms must include CSRF protection:

```html
<!-- REQUIRED: Use form.hidden_tag() -->
<form method="POST" action="/submit">
    {{ form.hidden_tag() }}
    <!-- Form fields -->
</form>
```

#### GET Forms
GET forms must NOT include CSRF tokens:

```html
<!-- CORRECT: No CSRF token for GET -->
<form method="GET" action="/search">
    <input type="text" name="query">
    <button type="submit">Search</button>
</form>
```

#### Modal Forms
Modal forms require CSRF protection:

```html
<!-- Modal with CSRF protection -->
<div class="modal" id="editModal">
    <form method="POST" action="/edit">
        {{ form.hidden_tag() }}
        <!-- Modal form fields -->
    </form>
</div>
```

### AJAX Integration

#### Meta Tag Implementation
Include CSRF token in page head:

```html
<head>
    <meta name="csrf-token" content="{{ csrf_token() }}">
</head>
```

#### JavaScript Access
Access CSRF token securely:

```javascript
// CORRECT: Get token from meta tag
const csrfToken = document.querySelector('meta[name=csrf-token]').getAttribute('content');

// WRONG: Never expose token in JavaScript variables
// var csrfToken = "{{ csrf_token() }}";
```

## Input Validation Standards

### XSS Prevention

#### Output Encoding
Always encode user input:

```html
<!-- CORRECT: Automatic escaping -->
<p>Welcome, {{ user.name }}!</p>

<!-- CORRECT: Explicit escaping for untrusted content -->
<p>{{ user_content | e }}</p>

<!-- WRONG: Raw output without escaping -->
<p>{{ user_content | safe }}</p>
```

#### Safe HTML Rendering
For trusted HTML content:

```html
<!-- Only for admin-controlled content -->
{% if current_user.is_admin %}
    {{ admin_content | safe }}
{% endif %}
```

### SQL Injection Prevention

#### Parameterized Queries
Always use parameterized queries in templates that interact with data:

```html
<!-- Template should receive sanitized data -->
{% for item in items %}
    <tr>
        <td>{{ item.name }}</td>
        <td>{{ item.value }}</td>
    </tr>
{% endfor %}
```

## Content Security Standards

### Information Disclosure Prevention

#### Error Messages
Never expose sensitive information:

```html
<!-- CORRECT: Generic error message -->
{% if error %}
    <div class="alert alert-danger">
        An error occurred. Please try again.
    </div>
{% endif %}

<!-- WRONG: Detailed error exposure -->
<!-- <div>Database error: {{ error_details }}</div> -->
```

#### Debug Information
Remove debug information from production templates:

```html
<!-- WRONG: Debug information in production -->
<!-- Debug: {{ debug_info }} -->
<!-- User ID: {{ current_user.id }} -->
```

### Session Security

#### Session Token Protection
Never expose session tokens:

```html
<!-- WRONG: Session token exposure -->
<!-- <input type="hidden" name="session_id" value="{{ session.id }}"> -->

<!-- CORRECT: Use Flask-Login's built-in session management -->
{% if current_user.is_authenticated %}
    <!-- User-specific content -->
{% endif %}
```

## Template Structure Standards

### Security Headers

#### Content Security Policy
Include CSP-friendly implementations:

```html
<!-- CORRECT: Inline styles with nonce -->
<style nonce="{{ csp_nonce }}">
    .secure-style { color: blue; }
</style>

<!-- AVOID: Inline styles without nonce -->
<div style="color: red;">Content</div>
```

#### X-Frame-Options
Prevent clickjacking:

```html
<!-- Handled by Flask security headers -->
<!-- Templates should not include frameable content -->
```

### Access Control

#### Authentication Checks
Verify user authentication:

```html
{% if current_user.is_authenticated %}
    <div class="user-content">
        <!-- Authenticated user content -->
    </div>
{% else %}
    <div class="guest-content">
        <!-- Public content only -->
    </div>
{% endif %}
```

#### Authorization Checks
Verify user permissions:

```html
{% if current_user.has_permission('admin') %}
    <div class="admin-panel">
        <!-- Admin-only content -->
    </div>
{% endif %}
```

## Form Validation Standards

### Client-Side Validation

#### Input Constraints
Implement proper input validation:

```html
<form method="POST" action="/submit">
    {{ form.hidden_tag() }}
    
    <!-- Required field validation -->
    <input type="email" name="email" required 
           pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$">
    
    <!-- Length constraints -->
    <input type="text" name="username" required 
           minlength="3" maxlength="50">
    
    <!-- Numeric constraints -->
    <input type="number" name="age" min="1" max="120">
</form>
```

#### File Upload Security
Secure file upload forms:

```html
<form method="POST" enctype="multipart/form-data" action="/upload">
    {{ form.hidden_tag() }}
    
    <!-- Restrict file types -->
    <input type="file" name="file" 
           accept=".jpg,.jpeg,.png,.gif" 
           required>
</form>
```

### Server-Side Integration
Templates must work with server-side validation:

```html
<!-- Display validation errors -->
{% if form.errors %}
    <div class="alert alert-danger">
        {% for field, errors in form.errors.items() %}
            {% for error in errors %}
                <p>{{ field }}: {{ error }}</p>
            {% endfor %}
        {% endfor %}
    </div>
{% endif %}
```

## JavaScript Security Standards

### Event Handling

#### Secure Event Binding
Use secure event handling:

```html
<!-- CORRECT: Use data attributes for configuration -->
<button type="button" 
        class="btn btn-primary" 
        data-action="submit"
        data-endpoint="/api/submit">
    Submit
</button>

<!-- WRONG: Inline JavaScript -->
<button onclick="submitForm()">Submit</button>
```

#### CSRF-Protected AJAX
Ensure AJAX requests include CSRF protection:

```html
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name=csrf-token]').getAttribute('content');
    
    // Configure AJAX requests
    fetch('/api/endpoint', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(data)
    });
});
</script>
```

## Template Security Checklist

### Pre-Deployment Checklist

#### CSRF Protection
- [ ] All POST forms use `{{ form.hidden_tag() }}`
- [ ] No direct `{{ csrf_token() }}` calls in templates
- [ ] GET forms exclude CSRF tokens
- [ ] Modal forms include CSRF protection
- [ ] Meta tag includes CSRF token for AJAX

#### Input/Output Security
- [ ] All user input is properly escaped
- [ ] No raw HTML output without validation
- [ ] Error messages don't expose sensitive data
- [ ] Debug information removed from production

#### Access Control
- [ ] Authentication checks implemented
- [ ] Authorization checks for sensitive content
- [ ] Session tokens not exposed
- [ ] Admin-only content properly protected

#### JavaScript Security
- [ ] No inline JavaScript without nonce
- [ ] Event handlers use secure binding
- [ ] AJAX requests include CSRF protection
- [ ] No sensitive data in JavaScript variables

### Code Review Checklist

#### Security Review Points
1. **CSRF Implementation**: Verify all forms have proper CSRF protection
2. **XSS Prevention**: Check all user input is escaped
3. **Access Control**: Verify authentication/authorization checks
4. **Information Disclosure**: Ensure no sensitive data exposure
5. **JavaScript Security**: Review client-side security implementation

#### Common Vulnerabilities to Check
- Exposed CSRF tokens
- Unescaped user input
- Missing authentication checks
- Sensitive information in HTML comments
- Inline JavaScript without CSP compliance

## Testing Standards

### Security Testing

#### Template Security Tests
```python
def test_template_csrf_protection():
    """Test CSRF protection in templates"""
    response = client.get('/form-page')
    assert 'csrf-token' in response.data.decode()
    assert 'csrf_token()' not in response.data.decode()

def test_template_xss_protection():
    """Test XSS protection in templates"""
    malicious_input = '<script>alert("xss")</script>'
    response = client.post('/submit', data={'input': malicious_input})
    assert '<script>' not in response.data.decode()
```

#### Manual Testing
1. **View Source**: Check for exposed tokens or sensitive data
2. **Form Testing**: Verify CSRF protection on all forms
3. **XSS Testing**: Test input fields with malicious scripts
4. **Access Control**: Test unauthorized access attempts

## Compliance Validation

### Automated Scanning
```bash
# Run template security scan
python -m security.audit.csrf_template_scanner

# Check for security violations
python scripts/security/run_csrf_audit.py --templates-only
```

### Manual Audit Process
1. **Template Review**: Examine all template files
2. **Form Analysis**: Check all form implementations
3. **JavaScript Review**: Verify client-side security
4. **Access Control Audit**: Test permission checks

## Security Incident Response

### Template Security Issues

#### Immediate Response
1. **Identify Scope**: Determine affected templates
2. **Assess Impact**: Evaluate security implications
3. **Implement Fix**: Apply security patches
4. **Verify Fix**: Test security implementation

#### Prevention Measures
1. **Code Review**: Mandatory security review
2. **Automated Testing**: Include security tests
3. **Developer Training**: Security awareness
4. **Monitoring**: Continuous security monitoring

## Best Practices Summary

### Do's
- ✅ Use `{{ form.hidden_tag() }}` for all POST forms
- ✅ Escape all user input with automatic templating
- ✅ Implement proper authentication/authorization checks
- ✅ Use meta tags for CSRF tokens in AJAX
- ✅ Include comprehensive input validation
- ✅ Test all security implementations

### Don'ts
- ❌ Never expose CSRF tokens directly in HTML
- ❌ Don't use raw HTML output without validation
- ❌ Don't include CSRF tokens in GET forms
- ❌ Don't expose sensitive data in templates
- ❌ Don't use inline JavaScript without CSP compliance
- ❌ Don't skip security testing

---

**Document Version**: 1.0  
**Last Updated**: {{ current_date }}  
**Next Review**: {{ next_review_date }}