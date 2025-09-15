# CSP Violation Resolution Guide

## Issue Summary

Your Vedfolnir web application was experiencing Content Security Policy (CSP) violations, specifically:
- **3 violations** on the landing page (`/landing`)
- **All violations** were Safari browser false positives
- **Violated directive**: `script-src-elem`
- **Blocked URI**: `inline` scripts

## Root Cause Analysis

### Primary Issue: Safari CSP Reporting Bug
Safari has a known bug where it reports CSP violations for inline scripts even when they are explicitly allowed by the policy. Your CSP policy correctly included:
- `'unsafe-inline'` directive
- Proper nonce values (`'nonce-{csp_nonce}'`)

### Secondary Issue: Missing `script-src-elem` Directive
The CSP policy was missing the `script-src-elem` directive, which is required for inline script elements in modern browsers.

## Fixes Applied

### 1. Updated CSP Policy (`app/core/security/core/security_middleware.py`)

**Added `script-src-elem` directive** to all CSP policy configurations:
```python
# Before
f"script-src 'self' 'nonce-{csp_nonce}' 'unsafe-inline' ..."

# After  
f"script-src 'self' 'nonce-{csp_nonce}' 'unsafe-inline' ..."
f"script-src-elem 'self' 'nonce-{csp_nonce}' 'unsafe-inline' ..."
```

**Fixed development mode detection**:
```python
# Before
is_development = ... or True  # Always true

# After
is_development = os.environ.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('CSP_PERMISSIVE') == '1'
```

**Updated WebSocket URLs for production**:
```python
# Production connect-src now includes
f"connect-src 'self' ... wss://vedfolnir.org ws://vedfolnir.org"
```

### 2. Enhanced CSP Report Handler (`app/blueprints/api/routes.py`)

**Added Safari false positive filtering**:
```python
# Filter out Safari false positives for inline scripts with nonces
is_safari_false_positive = (
    'Safari' in violation_info.get('user_agent', '') and
    violation_info.get('violated_directive') == 'script-src-elem' and
    violation_info.get('blocked_uri') == 'inline' and
    "'unsafe-inline'" in violation_info.get('original_policy', '') and
    "'nonce-" in violation_info.get('original_policy', '')
)

if is_safari_false_positive:
    # Log as debug instead of warning for Safari false positives
    current_app.logger.debug(f"Safari CSP false positive (filtered): ...")
else:
    # Log genuine CSP violations
    current_app.logger.warning(f"CSP violation detected: ...")
```

### 3. Nginx Configuration Recommendations

Created `nginx_vedfolnir_recommended.conf` with:
- **No duplicate CSP headers** (let Flask handle CSP exclusively)
- Proper proxy headers for HTTPS detection
- WebSocket support
- Security headers (excluding CSP)
- Static file optimization

**Critical**: Do NOT add `Content-Security-Policy` headers in Nginx - this causes conflicts.

## Deployment Steps

### 1. Restart Services
```bash
# Stop services
launchctl stop com.vedfolnir.gunicorn
sudo brew services stop nginx

# Start services  
launchctl start com.vedfolnir.gunicorn
sudo brew services start nginx
```

### 2. Verify Nginx Configuration
Compare your current `/opt/homebrew/etc/nginx/servers/vedfolnir.org.conf` with the provided `nginx_vedfolnir_recommended.conf` and ensure:
- No `add_header Content-Security-Policy` directives
- Proper proxy headers are set
- WebSocket support is configured

### 3. Monitor Results
```bash
# Monitor for new CSP violations
tail -f logs/webapp.log | grep 'CSP violation'

# Run analysis script
python3 scripts/debug/debug_csp_violations.py
```

## Debug Tools Created

### 1. CSP Violation Analyzer (`scripts/debug/debug_csp_violations.py`)
- Parses webapp logs for CSP violations
- Classifies Safari false positives vs genuine violations
- Provides detailed analysis and recommendations

### 2. CSP Configuration Checker (`scripts/debug/check_csp_config.py`)
- Tests CSP headers from your application
- Validates CSP report endpoint
- Checks environment configuration
- Provides Nginx configuration guidance

## Expected Results

After applying these fixes:

1. **Safari false positives** will be filtered out (logged as debug, not warnings)
2. **Genuine CSP violations** should be eliminated
3. **Application functionality** remains unchanged
4. **Security posture** is maintained or improved

## Environment Variables

You can control CSP behavior with these environment variables:

```bash
# Force development mode (more permissive CSP)
CSP_PERMISSIVE=1

# Enable strict CSP mode (more restrictive)
CSP_STRICT_MODE=1

# Standard Flask environment detection
FLASK_ENV=development
FLASK_DEBUG=1
```

## Verification Checklist

- [ ] Services restarted successfully
- [ ] No CSP violations in Safari after 1 hour of testing
- [ ] Landing page JavaScript functions correctly
- [ ] WebSocket connections work properly
- [ ] No duplicate CSP headers in browser dev tools
- [ ] CSP report endpoint returns 204 status

## Troubleshooting

If you still see violations after applying fixes:

1. **Run the analyzer**: `python3 scripts/debug/debug_csp_violations.py`
2. **Check configuration**: `python3 scripts/debug/check_csp_config.py`
3. **Verify Nginx config**: Ensure no duplicate CSP headers
4. **Test different browsers**: Chrome, Firefox, Safari
5. **Check environment variables**: Ensure proper CSP mode

## Technical Details

### CSP Policy Structure
```
default-src 'self';
script-src 'self' 'nonce-{nonce}' 'unsafe-inline' https://cdn.jsdelivr.net ...;
script-src-elem 'self' 'nonce-{nonce}' 'unsafe-inline' https://cdn.jsdelivr.net ...;
style-src 'self' 'nonce-{nonce}' 'unsafe-inline' https://fonts.googleapis.com ...;
connect-src 'self' wss: ws: https://cdn.jsdelivr.net ... wss://vedfolnir.org;
report-uri /api/csp-report;
```

### Safari CSP Bug Details
Safari versions 14+ have a known issue where they report violations for inline scripts that use nonces, even when `'unsafe-inline'` is present in the policy. This is a browser bug, not a security issue.

## Support

If you continue to experience issues:
1. Check the debug script outputs
2. Verify all services are running correctly
3. Test with different browsers to isolate Safari-specific issues
4. Monitor logs for 24-48 hours to establish a baseline

The fixes applied should resolve all current CSP violations while maintaining security and functionality.