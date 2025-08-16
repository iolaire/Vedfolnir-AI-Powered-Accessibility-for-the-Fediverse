# Security Feature Toggles

This document describes the security feature toggles available in Vedfolnir for development and testing purposes.

## ⚠️ Important Warning

**These toggles are for development and testing ONLY. ALL security features MUST be enabled in production environments.**

## Available Toggles

### SECURITY_CSRF_ENABLED
- **Default**: `true`
- **Purpose**: Controls CSRF protection middleware
- **When disabled**: Allows requests without CSRF tokens (useful for API testing)
- **Production**: MUST be `true`

### SECURITY_RATE_LIMITING_ENABLED
- **Default**: `true`
- **Purpose**: Controls rate limiting on all endpoints
- **When disabled**: Removes rate limits (useful for load testing)
- **Production**: MUST be `true`

### SECURITY_INPUT_VALIDATION_ENABLED
- **Default**: `true`
- **Purpose**: Controls enhanced input validation and sanitization
- **When disabled**: Reduces input validation (basic validation still active)
- **Production**: MUST be `true`

### SECURITY_HEADERS_ENABLED
- **Default**: `true`
- **Purpose**: Controls security HTTP headers (CSP, HSTS, X-Frame-Options, etc.)
- **When disabled**: Removes security headers (useful for debugging)
- **Production**: MUST be `true`

### SECURITY_SESSION_VALIDATION_ENABLED
- **Default**: `true`
- **Purpose**: Controls additional session security checks
- **When disabled**: Reduces session validation
- **Production**: MUST be `true`

### SECURITY_ADMIN_CHECKS_ENABLED
- **Default**: `true`
- **Purpose**: Controls admin-specific security validation
- **When disabled**: Reduces admin access checks
- **Production**: MUST be `true`

## Configuration

Add these to your `.env` file:

```bash
# Security Feature Toggles (Development/Testing Only)
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_INPUT_VALIDATION_ENABLED=true
SECURITY_HEADERS_ENABLED=true
SECURITY_SESSION_VALIDATION_ENABLED=true
SECURITY_ADMIN_CHECKS_ENABLED=true
```

## Development Use Cases

### API Testing
```bash
# Disable CSRF for API testing tools
SECURITY_CSRF_ENABLED=false
```

### Load Testing
```bash
# Disable rate limiting for load tests
SECURITY_RATE_LIMITING_ENABLED=false
```

### Debugging
```bash
# Disable security headers for debugging
SECURITY_HEADERS_ENABLED=false
```

### Integration Testing
```bash
# Disable specific features for automated tests
SECURITY_RATE_LIMITING_ENABLED=false
SECURITY_CSRF_ENABLED=false
```

## Production Configuration

**ALL toggles MUST be enabled in production:**

```bash
# Production Security Configuration (REQUIRED)
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_INPUT_VALIDATION_ENABLED=true
SECURITY_HEADERS_ENABLED=true
SECURITY_SESSION_VALIDATION_ENABLED=true
SECURITY_ADMIN_CHECKS_ENABLED=true
```

## Best Practices

1. **Default to Secure**: Always start with all features enabled
2. **Minimal Disabling**: Only disable specific features needed for testing
3. **Re-enable Quickly**: Re-enable features immediately after testing
4. **Document Changes**: Document why features were disabled
5. **Never Commit**: Never commit `.env` files with disabled security
6. **Production Verification**: Always verify all features are enabled in production

## Verification

Check your current configuration:

```bash
# Verify all security features are enabled
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

toggles = [
    'SECURITY_CSRF_ENABLED',
    'SECURITY_RATE_LIMITING_ENABLED', 
    'SECURITY_INPUT_VALIDATION_ENABLED',
    'SECURITY_HEADERS_ENABLED',
    'SECURITY_SESSION_VALIDATION_ENABLED',
    'SECURITY_ADMIN_CHECKS_ENABLED'
]

for toggle in toggles:
    value = os.getenv(toggle, 'true').lower()
    status = '✅' if value == 'true' else '❌'
    print(f'{status} {toggle}: {value}')
"
```

## Related Documentation

- [Security Guide](../SECURITY.md) - Complete security documentation
- [Environment Setup](environment-setup.md) - Environment configuration guide
- [Testing Guide](../TESTING.md) - Testing procedures and guidelines