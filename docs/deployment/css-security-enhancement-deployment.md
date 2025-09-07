# CSS Security Enhancement Deployment Guide

## Overview

This document provides comprehensive deployment and rollback procedures for the CSS Security Enhancement feature. This enhancement removes all inline CSS styles from HTML templates and moves them to external CSS files to improve Content Security Policy (CSP) compliance and security posture.

## Pre-Deployment Requirements

### System Requirements
- Web server with CSS file serving capability
- Browser cache clearing capability
- Access to application logs and monitoring
- Backup and rollback capabilities

### Dependencies
- All new CSS files must be created and tested
- Templates must be updated to use CSS classes
- JavaScript must be updated for dynamic styling
- CSP headers must be configured

## Deployment Procedures

### Phase 1: Pre-Deployment Validation

#### 1.1 Verify CSS Files Exist
```bash
# Check that all required CSS files are present
ls -la static/css/security-extracted.css
ls -la static/css/components.css
ls -la admin/static/css/admin-extracted.css

# Verify CSS files are not empty
wc -l static/css/security-extracted.css
wc -l static/css/components.css
wc -l admin/static/css/admin-extracted.css
```

#### 1.2 Run Inline Style Detection
```bash
# Run the CSS extraction helper to verify no inline styles remain
cd tests/scripts
python css_extraction_helper.py

# Expected output: "No inline styles found" or specific count
```

#### 1.3 Validate Template Syntax
```bash
# Check for template syntax errors
python -c "
import os
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

def validate_templates():
    template_dirs = ['templates', 'admin/templates']
    errors = []
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            env = Environment(loader=FileSystemLoader(template_dir))
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.html'):
                        template_path = os.path.relpath(os.path.join(root, file), template_dir)
                        try:
                            env.get_template(template_path)
                            print(f'✅ {template_path}')
                        except TemplateSyntaxError as e:
                            errors.append(f'❌ {template_path}: {e}')
                            print(f'❌ {template_path}: {e}')
    
    if errors:
        print(f'\nFound {len(errors)} template errors')
        return False
    else:
        print(f'\nAll templates validated successfully')
        return True

validate_templates()
"
```

### Phase 2: Backup Procedures

#### 2.1 Create Application Backup
```bash
# Create timestamped backup directory
BACKUP_DIR="backups/css-security-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup templates
cp -r templates "$BACKUP_DIR/"
cp -r admin/templates "$BACKUP_DIR/admin_templates"

# Backup existing CSS files
cp -r static/css "$BACKUP_DIR/static_css"
cp -r admin/static/css "$BACKUP_DIR/admin_static_css"

# Backup configuration files
cp config.py "$BACKUP_DIR/"
cp web_app.py "$BACKUP_DIR/"

# Create backup manifest
echo "CSS Security Enhancement Backup - $(date)" > "$BACKUP_DIR/MANIFEST.txt"
echo "Templates: $(find templates -name '*.html' | wc -l) files" >> "$BACKUP_DIR/MANIFEST.txt"
echo "Admin Templates: $(find admin/templates -name '*.html' | wc -l) files" >> "$BACKUP_DIR/MANIFEST.txt"
echo "CSS Files: $(find static/css -name '*.css' | wc -l) files" >> "$BACKUP_DIR/MANIFEST.txt"
echo "Admin CSS Files: $(find admin/static/css -name '*.css' | wc -l) files" >> "$BACKUP_DIR/MANIFEST.txt"

echo "Backup created in: $BACKUP_DIR"
```

#### 2.2 Database Backup (if needed)
```bash
# If any database changes are involved
python scripts/database/backup_database.py --output="$BACKUP_DIR/database_backup.sql"
```

### Phase 3: Deployment Execution

#### 3.1 Deploy CSS Files
```bash
# Ensure CSS files are in correct locations with proper permissions
chmod 644 static/css/*.css
chmod 644 admin/static/css/*.css

# Verify CSS file integrity
for css_file in static/css/*.css admin/static/css/*.css; do
    if [ -f "$css_file" ]; then
        echo "✅ $css_file exists ($(wc -l < "$css_file") lines)"
    else
        echo "❌ $css_file missing"
    fi
done
```

#### 3.2 Deploy Template Updates
```bash
# Templates should already be updated, verify key templates
key_templates=(
    "templates/base.html"
    "templates/index.html"
    "templates/caption_generation.html"
    "templates/review_single.html"
    "templates/batch_review.html"
    "admin/templates/base_admin.html"
)

for template in "${key_templates[@]}"; do
    if [ -f "$template" ]; then
        # Check that template includes new CSS files
        if grep -q "security-extracted.css\|components.css\|admin-extracted.css" "$template"; then
            echo "✅ $template includes new CSS files"
        else
            echo "⚠️  $template may not include new CSS files"
        fi
    else
        echo "❌ $template missing"
    fi
done
```

#### 3.3 Clear Application Caches
```bash
# Clear any application-level template caches
python -c "
import os
import shutil

# Clear Python cache
cache_dirs = ['__pycache__', 'templates/__pycache__', 'admin/__pycache__']
for cache_dir in cache_dirs:
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        print(f'Cleared {cache_dir}')

# Clear any Flask template cache
if os.path.exists('flask_cache'):
    shutil.rmtree('flask_cache')
    print('Cleared Flask cache')
"
```

#### 3.4 Restart Application Services
```bash
# Restart web application (adjust for your deployment method)
# For systemd:
# sudo systemctl restart vedfolnir

# For Docker:
# docker-compose restart

# For development:
# Kill existing process and restart
pkill -f "python web_app.py"
sleep 2
python web_app.py & sleep 10
```

### Phase 4: Post-Deployment Verification

#### 4.1 Application Health Check
```bash
# Verify application starts successfully
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/
# Expected: 200

# Check for any startup errors
tail -n 50 logs/webapp.log | grep -i error
```

#### 4.2 CSS Loading Verification
```bash
# Test CSS file accessibility
css_files=(
    "http://127.0.0.1:5000/static/css/security-extracted.css"
    "http://127.0.0.1:5000/static/css/components.css"
    "http://127.0.0.1:5000/admin/static/css/admin-extracted.css"
)

for css_url in "${css_files[@]}"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "$css_url")
    if [ "$status" = "200" ]; then
        echo "✅ $css_url accessible"
    else
        echo "❌ $css_url returned $status"
    fi
done
```

#### 4.3 Visual Regression Testing
```bash
# Run visual consistency tests if available
cd tests/playwright
timeout 120 npx playwright test tests/*_test_visual_consistency.js --config=0830_17_52_playwright.config.js
```

## Rollback Procedures

### Emergency Rollback (< 5 minutes)

#### 1. Quick Template Rollback
```bash
# Find the most recent backup
LATEST_BACKUP=$(ls -1t backups/css-security-* | head -1)
echo "Rolling back to: $LATEST_BACKUP"

# Stop application
pkill -f "python web_app.py"

# Restore templates
cp -r "$LATEST_BACKUP/templates" .
cp -r "$LATEST_BACKUP/admin_templates" admin/templates

# Restore CSS files
cp -r "$LATEST_BACKUP/static_css" static/css
cp -r "$LATEST_BACKUP/admin_static_css" admin/static/css

# Restore configuration if needed
cp "$LATEST_BACKUP/config.py" .
cp "$LATEST_BACKUP/web_app.py" .

# Restart application
python web_app.py & sleep 10

echo "Emergency rollback completed"
```

#### 2. Verify Rollback Success
```bash
# Test application accessibility
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/
# Expected: 200

# Check for inline styles (should be present after rollback)
python tests/scripts/css_extraction_helper.py
# Expected: Some inline styles found (pre-enhancement state)
```

### Planned Rollback (Full Procedure)

#### 1. Pre-Rollback Assessment
```bash
# Document current state
echo "=== Pre-Rollback State ===" > rollback_log.txt
echo "Date: $(date)" >> rollback_log.txt
echo "Reason: [SPECIFY REASON]" >> rollback_log.txt
echo "Application Status: $(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/)" >> rollback_log.txt

# Check current CSS files
echo "Current CSS Files:" >> rollback_log.txt
ls -la static/css/*.css >> rollback_log.txt
ls -la admin/static/css/*.css >> rollback_log.txt
```

#### 2. Execute Rollback
```bash
# Use the emergency rollback procedure above
# Then perform additional verification
```

#### 3. Post-Rollback Verification
```bash
# Run comprehensive tests
python -m unittest discover tests -v

# Verify all functionality works
echo "=== Post-Rollback Verification ===" >> rollback_log.txt
echo "Application Status: $(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/)" >> rollback_log.txt
echo "Template Count: $(find templates -name '*.html' | wc -l)" >> rollback_log.txt
echo "CSS File Count: $(find static/css -name '*.css' | wc -l)" >> rollback_log.txt
```

## Testing Checklist

### Pre-Deployment Testing
- [ ] All CSS files exist and are not empty
- [ ] No inline styles detected in templates (except email templates)
- [ ] Template syntax validation passes
- [ ] CSS file accessibility tests pass
- [ ] Visual consistency tests pass
- [ ] JavaScript functionality tests pass
- [ ] Cross-browser compatibility verified
- [ ] Mobile responsiveness maintained

### Post-Deployment Testing
- [ ] Application starts without errors
- [ ] All pages load correctly
- [ ] CSS files are accessible via HTTP
- [ ] No console errors in browser
- [ ] Interactive elements function properly
- [ ] Progress bars display correctly
- [ ] Modals show/hide properly
- [ ] Forms submit successfully
- [ ] Admin interface works correctly
- [ ] User interface maintains visual consistency

### CSP Compliance Testing
- [ ] Enable strict CSP headers
- [ ] No CSP violations in browser console
- [ ] All pages load without style-src violations
- [ ] JavaScript functionality unaffected by CSP
- [ ] External CSS loading works with CSP

### Performance Testing
- [ ] Page load times within acceptable range
- [ ] CSS file sizes optimized
- [ ] Browser caching working correctly
- [ ] No significant performance degradation
- [ ] Memory usage stable

## Monitoring Procedures

### Real-Time Monitoring

#### 1. Application Health Monitoring
```bash
# Monitor application logs for CSS-related errors
tail -f logs/webapp.log | grep -i "css\|style\|template"

# Monitor HTTP status codes
while true; do
    status=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/)
    echo "$(date): HTTP Status $status"
    sleep 30
done
```

#### 2. CSS File Monitoring
```bash
# Monitor CSS file accessibility
css_files=(
    "http://127.0.0.1:5000/static/css/security-extracted.css"
    "http://127.0.0.1:5000/static/css/components.css"
    "http://127.0.0.1:5000/admin/static/css/admin-extracted.css"
)

while true; do
    for css_url in "${css_files[@]}"; do
        status=$(curl -s -o /dev/null -w "%{http_code}" "$css_url")
        if [ "$status" != "200" ]; then
            echo "ALERT: $css_url returned $status at $(date)"
        fi
    done
    sleep 60
done
```

#### 3. Browser Console Monitoring
```bash
# Use Playwright for automated console monitoring
cd tests/playwright
timeout 120 npx playwright test tests/*_test_console_monitoring.js --config=0830_17_52_playwright.config.js
```

### Performance Monitoring

#### 1. Page Load Time Monitoring
```bash
# Monitor page load times
pages=(
    "http://127.0.0.1:5000/"
    "http://127.0.0.1:5000/login"
    "http://127.0.0.1:5000/caption_generation"
    "http://127.0.0.1:5000/admin"
)

for page in "${pages[@]}"; do
    load_time=$(curl -s -o /dev/null -w "%{time_total}" "$page")
    echo "$(date): $page loaded in ${load_time}s"
done
```

#### 2. CSS File Size Monitoring
```bash
# Monitor CSS file sizes
for css_file in static/css/*.css admin/static/css/*.css; do
    if [ -f "$css_file" ]; then
        size=$(stat -f%z "$css_file" 2>/dev/null || stat -c%s "$css_file" 2>/dev/null)
        echo "$(date): $css_file is ${size} bytes"
    fi
done
```

### Alert Conditions

#### Critical Alerts (Immediate Action Required)
- Application returns 500 errors
- CSS files return 404 errors
- CSP violations detected in browser console
- Page load times exceed 10 seconds
- Template rendering errors

#### Warning Alerts (Monitor Closely)
- Page load times exceed 5 seconds
- CSS file sizes increase significantly
- Browser console warnings
- Memory usage increases
- Unusual error patterns in logs

### Monitoring Scripts

#### 1. Comprehensive Health Check Script
```bash
#!/bin/bash
# css_health_check.sh

echo "=== CSS Security Enhancement Health Check ==="
echo "Date: $(date)"

# Check application status
app_status=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/)
echo "Application Status: $app_status"

# Check CSS files
css_files=(
    "static/css/security-extracted.css"
    "static/css/components.css"
    "admin/static/css/admin-extracted.css"
)

for css_file in "${css_files[@]}"; do
    if [ -f "$css_file" ]; then
        size=$(stat -f%z "$css_file" 2>/dev/null || stat -c%s "$css_file" 2>/dev/null)
        echo "✅ $css_file exists (${size} bytes)"
    else
        echo "❌ $css_file missing"
    fi
done

# Check for inline styles
echo "Checking for inline styles..."
python tests/scripts/css_extraction_helper.py

# Check recent errors
echo "Recent errors in logs:"
tail -n 100 logs/webapp.log | grep -i error | tail -5

echo "=== Health Check Complete ==="
```

#### 2. Performance Monitoring Script
```bash
#!/bin/bash
# css_performance_monitor.sh

echo "=== CSS Performance Monitor ==="
echo "Date: $(date)"

# Test page load times
pages=(
    "http://127.0.0.1:5000/"
    "http://127.0.0.1:5000/login"
    "http://127.0.0.1:5000/caption_generation"
)

for page in "${pages[@]}"; do
    load_time=$(curl -s -o /dev/null -w "%{time_total}" "$page")
    echo "$page: ${load_time}s"
done

# Check CSS file accessibility and response times
css_urls=(
    "http://127.0.0.1:5000/static/css/security-extracted.css"
    "http://127.0.0.1:5000/static/css/components.css"
    "http://127.0.0.1:5000/admin/static/css/admin-extracted.css"
)

for css_url in "${css_urls[@]}"; do
    response_time=$(curl -s -o /dev/null -w "%{time_total}" "$css_url")
    status=$(curl -s -o /dev/null -w "%{http_code}" "$css_url")
    echo "$css_url: ${status} (${response_time}s)"
done

echo "=== Performance Monitor Complete ==="
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: CSS Files Not Loading
**Symptoms**: Pages display without styling, 404 errors for CSS files
**Solution**:
```bash
# Check file permissions
chmod 644 static/css/*.css admin/static/css/*.css

# Verify file paths in templates
grep -r "security-extracted.css\|components.css" templates/
```

#### Issue: Visual Layout Broken
**Symptoms**: Elements misaligned, missing styles
**Solution**:
```bash
# Check for missing CSS classes
python tests/scripts/css_extraction_helper.py --verbose

# Compare with backup
diff -r templates/ "$LATEST_BACKUP/templates/"
```

#### Issue: CSP Violations
**Symptoms**: Console errors about Content Security Policy
**Solution**:
```bash
# Check for remaining inline styles
grep -r 'style=' templates/ admin/templates/

# Verify CSP headers configuration
curl -I http://127.0.0.1:5000/ | grep -i content-security-policy
```

#### Issue: JavaScript Functionality Broken
**Symptoms**: Interactive elements not working
**Solution**:
```bash
# Check JavaScript console for errors
# Update JavaScript to use CSS classes instead of inline styles
# Verify event handlers are properly attached
```

### Recovery Procedures

#### 1. Partial Recovery (Specific Component)
```bash
# If only specific templates are affected
cp "$LATEST_BACKUP/templates/specific_template.html" templates/
# Restart application
pkill -f "python web_app.py" && python web_app.py & sleep 10
```

#### 2. Full Recovery
```bash
# Use the emergency rollback procedure
# Then investigate root cause
# Plan re-deployment with fixes
```

## Documentation Updates

After successful deployment, update the following documentation:
- [ ] Update deployment status in project README
- [ ] Update CSS organization guide with new file structure
- [ ] Update developer guidelines with new CSS practices
- [ ] Update security documentation with CSP improvements
- [ ] Create post-deployment report with lessons learned

## Conclusion

This deployment guide provides comprehensive procedures for safely deploying the CSS Security Enhancement feature. Follow all steps carefully and maintain backups throughout the process. Monitor the application closely after deployment and be prepared to execute rollback procedures if issues arise.

For questions or issues during deployment, refer to the troubleshooting section or contact the development team.