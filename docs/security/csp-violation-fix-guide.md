# CSP Violation Fix Guide

## Overview

This guide helps you fix Content Security Policy (CSP) violations in your Vedfolnir web application deployment. CSP violations occur when inline JavaScript event handlers or styles are blocked by the security policy.

## Current Issue

Your application is experiencing `script-src-attr` CSP violations due to inline event handlers like:
- `onclick="function()"`
- `onchange="this.form.submit()"`
- `onload="window.location.reload()"`

## Solution Steps

### 1. Run the Automated Fix Script

```bash
# Navigate to your project root
cd /path/to/vedfolnir

# Run the CSP violation fix script
python scripts/security/fix_csp_violations.py
```

This script will:
- Replace inline event handlers with `data-*` attributes
- Replace common inline styles with CSS classes
- Add CSP-compliant scripts to your base template

### 2. Enable Strict CSP Mode (Optional)

For maximum security, enable strict CSP mode:

```bash
# Add to your environment variables
export CSP_STRICT_MODE=1

# Or add to your .env file
echo "CSP_STRICT_MODE=1" >> .env
```

### 3. Update Your JavaScript Functions

The automated script creates placeholder functions. You need to implement them based on your existing code:

```javascript
// Edit static/js/csp-compliant-handlers.js
// Replace placeholder functions with your actual implementations

function switchPlatform(platformId, platformName) {
    // Your existing platform switching logic
}

function editPlatform(platformId) {
    // Your existing platform editing logic
}

// ... etc for other functions
```

### 4. Test the Changes

```bash
# Start your web application
python web_app.py & sleep 10

# Run CSP compliance tests
python scripts/security/test_csp_compliance.py

# Check for violations in browser console
# Open browser dev tools and look for CSP violation messages
```

### 5. Restart Your Services

```bash
# Stop services
launchctl stop com.vedfolnir.gunicorn
sudo brew services stop nginx

# Start services
launchctl start com.vedfolnir.gunicorn
sudo brew services start nginx
```

## Manual Template Updates

If the automated script doesn't catch everything, manually update templates:

### Before (CSP Violation):
```html
<button onclick="deleteItem(123)">Delete</button>
<select onchange="this.form.submit()">...</select>
<div style="font-size: 4rem;">Large Icon</div>
```

### After (CSP Compliant):
```html
<button data-action="delete-item" data-item-id="123">Delete</button>
<select data-auto-submit="true">...</select>
<div class="status-icon-large">Large Icon</div>
```

## Nginx Configuration

If you're using Nginx, ensure it's not adding conflicting CSP headers:

```nginx
# Remove any existing CSP headers in nginx config
# Let the Flask application handle CSP headers
# Comment out or remove lines like:
# add_header Content-Security-Policy "...";
```

## Testing CSP Compliance

### Browser Console Testing
1. Open browser developer tools (F12)
2. Navigate to Console tab
3. Visit your application pages
4. Look for CSP violation messages

### Automated Testing
```bash
# Run comprehensive CSP tests
python scripts/security/test_csp_compliance.py

# Monitor violations in real-time
tail -f logs/webapp.log | grep "CSP violation"
```

## Common CSP Violations and Fixes

### 1. Inline Event Handlers
**Violation**: `onclick`, `onchange`, `onload` attributes
**Fix**: Use `data-*` attributes and event listeners

### 2. Inline Scripts
**Violation**: `<script>` tags without nonce
**Fix**: Add `nonce="{{ g.csp_nonce }}"` to script tags

### 3. Inline Styles
**Violation**: `style="..."` attributes
**Fix**: Use CSS classes or add nonce to style tags

### 4. External Resources
**Violation**: Loading from unauthorized domains
**Fix**: Add domains to CSP policy or use local resources

## Environment Variables

```bash
# CSP Configuration
CSP_STRICT_MODE=1              # Enable strict CSP (blocks all inline script attributes)
CSP_PERMISSIVE=1               # Temporary: Allow more permissive CSP for testing
FLASK_ENV=development          # More permissive CSP in development
FLASK_DEBUG=1                  # Debug mode CSP settings
```

## Troubleshooting

### Issue: Functions Not Working After Fix
**Solution**: Implement the JavaScript functions in `csp-compliant-handlers.js`

### Issue: Styles Not Applied
**Solution**: Include `csp-compliant-styles.css` in your base template

### Issue: Still Getting Violations
**Solution**: 
1. Check browser console for specific violations
2. Run the test script to identify remaining issues
3. Manually fix any missed inline handlers

### Issue: Nginx Conflicts
**Solution**: Remove CSP headers from Nginx config, let Flask handle them

## Verification Checklist

- [ ] No `onclick`, `onchange`, `onload` attributes in templates
- [ ] CSP-compliant scripts included in base template
- [ ] JavaScript functions implemented in `csp-compliant-handlers.js`
- [ ] CSS classes defined in `csp-compliant-styles.css`
- [ ] CSP headers present in HTTP responses
- [ ] No CSP violations in browser console
- [ ] All application functionality working
- [ ] Services restarted after changes

## Production Deployment

1. **Test in Development**: Fix all violations in development first
2. **Gradual Rollout**: Consider using CSP report-only mode initially
3. **Monitor Logs**: Watch for CSP violation reports after deployment
4. **Performance Check**: Ensure changes don't impact performance

## Support

If you encounter issues:
1. Check the browser console for specific CSP violation details
2. Run the automated test script for comprehensive analysis
3. Review the application logs for CSP violation reports
4. Ensure all services are properly restarted after changes

## Security Benefits

After fixing CSP violations:
- ✅ Protection against XSS attacks
- ✅ Reduced attack surface
- ✅ Compliance with security best practices
- ✅ Better security audit scores
- ✅ Enhanced user trust