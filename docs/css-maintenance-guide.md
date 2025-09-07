# CSS Maintenance Guide

## Overview

This guide provides step-by-step procedures for maintaining the CSS codebase in Vedfolnir, ensuring continued security compliance and code quality.

## Daily Maintenance Tasks

### 1. Inline Style Detection

**Automated Scan:**
```bash
# Run the CSS extraction helper to detect any new inline styles
python tests/scripts/css_extraction_helper.py

# Check for specific inline style patterns
grep -r 'style="' templates/ --exclude-dir=emails
grep -r 'style="' admin/templates/
```

**Expected Output:**
- Zero inline styles found (excluding email templates)
- Clean scan report with no violations

### 2. CSS File Validation

**Check CSS Syntax:**
```bash
# Validate CSS files for syntax errors
find static/css -name "*.css" -exec echo "Checking {}" \; -exec css-validator {} \;
find admin/static/css -name "*.css" -exec echo "Checking {}" \; -exec css-validator {} \;
```

**Manual Review:**
- Check for duplicate CSS rules
- Verify proper copyright headers
- Ensure consistent formatting

### 3. Performance Monitoring

**CSS Load Time Check:**
```bash
# Test CSS loading performance
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:5000/static/css/style.css"
```

**File Size Monitoring:**
```bash
# Monitor CSS file sizes
du -h static/css/*.css
du -h admin/static/css/*.css
```

## Weekly Maintenance Tasks

### 1. Comprehensive Template Scan

**Full Template Review:**
```bash
# Comprehensive scan of all templates
find templates -name "*.html" -exec grep -l 'style="' {} \;
find admin/templates -name "*.html" -exec grep -l 'style="' {} \;

# Check for JavaScript style manipulation
grep -r '\.style\.' static/js/
grep -r '\.style\.' admin/static/js/
```

### 2. CSS Class Usage Analysis

**Unused Class Detection:**
```bash
# Find potentially unused CSS classes
python scripts/css_usage_analyzer.py

# Check for orphaned CSS rules
python scripts/css_orphan_detector.py
```

### 3. Browser Compatibility Testing

**Cross-Browser CSS Testing:**
- Test in Chrome, Firefox, Safari, Edge
- Verify CSS Grid and Flexbox compatibility
- Check CSS custom property support

## Monthly Maintenance Tasks

### 1. CSS Architecture Review

**File Organization Audit:**
- Review CSS file structure
- Check for proper separation of concerns
- Verify logical file grouping

**Documentation Updates:**
- Update CSS organization guide
- Review and update class naming conventions
- Update maintenance procedures

### 2. Performance Optimization

**CSS Bundle Analysis:**
```bash
# Analyze CSS bundle size and composition
python scripts/css_bundle_analyzer.py

# Check for optimization opportunities
python scripts/css_optimizer.py --analyze
```

**Optimization Actions:**
- Remove duplicate CSS rules
- Consolidate similar classes
- Optimize CSS custom properties

### 3. Security Compliance Audit

**CSP Compliance Check:**
```bash
# Test strict CSP compliance
python scripts/csp_compliance_tester.py

# Browser console error check
python scripts/browser_console_checker.py
```

## Emergency Procedures

### 1. CSS Rollback Procedure

**When CSS changes break functionality:**

```bash
# 1. Identify the problematic commit
git log --oneline --grep="css" -n 10

# 2. Create emergency branch
git checkout -b emergency-css-rollback

# 3. Revert specific CSS changes
git revert [commit-hash]

# 4. Test the rollback
python web_app.py & sleep 10
# Test affected pages manually

# 5. Deploy emergency fix
git push origin emergency-css-rollback
```

### 2. Inline Style Emergency Addition

**When emergency inline styles are needed:**

1. **Document the emergency:**
   ```html
   <!-- EMERGENCY INLINE STYLE - Remove after fix -->
   <!-- Issue: [Issue description] -->
   <!-- Date: [Current date] -->
   <!-- TODO: Extract to CSS file -->
   <div style="display: none;">Emergency hidden content</div>
   ```

2. **Create tracking issue:**
   - Document the inline style addition
   - Set priority for CSS extraction
   - Assign to CSS maintenance team

3. **Schedule extraction:**
   - Plan CSS extraction within 24 hours
   - Test extraction thoroughly
   - Remove emergency inline style

### 3. CSP Violation Response

**When CSP violations are detected:**

1. **Immediate Assessment:**
   ```bash
   # Check browser console for violations
   # Identify the source template/component
   # Assess security impact
   ```

2. **Quick Fix:**
   ```bash
   # Extract the violating inline style
   # Add appropriate CSS class
   # Test the fix
   ```

3. **Verification:**
   ```bash
   # Verify CSP compliance restored
   # Test affected functionality
   # Monitor for additional violations
   ```

## CSS Change Procedures

### 1. Adding New CSS Classes

**Step-by-Step Process:**

1. **Determine Appropriate File:**
   - Utility class → `utilities.css`
   - Component-specific → `components.css`
   - Admin-specific → `admin-extracted.css`
   - Page-specific → Create/update page CSS file

2. **Follow Naming Convention:**
   ```css
   /* Good naming examples */
   .modal-overlay          /* Component-based */
   .hidden                 /* Utility-based */
   .progress-bar-dynamic   /* Descriptive */
   .bulk-select-position   /* Context-specific */
   ```

3. **Add Documentation:**
   ```css
   /* Modal overlay for dialog boxes
    * Replaces: style="display: none;" in modal templates
    * Used in: user_modal.html, admin_modal.html
    * Toggle with: .show class
    */
   .modal-overlay {
       display: none;
       position: fixed;
       top: 0;
       left: 0;
       width: 100%;
       height: 100%;
       background-color: rgba(0, 0, 0, 0.5);
       z-index: 1000;
   }
   ```

4. **Test Implementation:**
   - Test in all affected templates
   - Verify responsive behavior
   - Check browser compatibility
   - Validate CSP compliance

### 2. Modifying Existing CSS Classes

**Change Process:**

1. **Impact Assessment:**
   ```bash
   # Find all usages of the class
   grep -r "class-name" templates/
   grep -r "class-name" admin/templates/
   grep -r "class-name" static/js/
   ```

2. **Backward Compatibility:**
   - Consider deprecation period
   - Provide migration path
   - Update documentation

3. **Testing Protocol:**
   - Test all affected templates
   - Verify no visual regressions
   - Check interactive functionality
   - Validate across browsers

### 3. Removing CSS Classes

**Deprecation Process:**

1. **Mark as Deprecated:**
   ```css
   /* @deprecated - Use .new-class-name instead
    * Will be removed in version X.X.X
    * Migration: Replace .old-class with .new-class
    */
   .old-class {
       /* existing styles */
   }
   ```

2. **Update Usage:**
   - Replace all instances
   - Update documentation
   - Test thoroughly

3. **Remove After Grace Period:**
   - Remove deprecated class
   - Update version notes
   - Clean up documentation

## Quality Assurance Procedures

### 1. Pre-Commit Checks

**Automated Checks:**
```bash
# CSS syntax validation
css-validator static/css/*.css

# Inline style detection
python tests/scripts/css_extraction_helper.py --strict

# Copyright header verification
python scripts/copyright_checker.py --css
```

### 2. Code Review Checklist

**CSS Changes Review:**
- [ ] No inline styles introduced
- [ ] Proper file organization
- [ ] Consistent naming conventions
- [ ] Adequate documentation
- [ ] Browser compatibility considered
- [ ] Performance impact assessed
- [ ] Security implications reviewed

### 3. Testing Requirements

**Required Tests:**
- Visual regression testing
- Cross-browser compatibility
- CSP compliance verification
- Performance impact assessment
- Accessibility compliance

## Monitoring and Alerting

### 1. Automated Monitoring

**Daily Checks:**
```bash
# Cron job for daily CSS monitoring
0 9 * * * /path/to/css_monitor.sh
```

**Monitor Script (`css_monitor.sh`):**
```bash
#!/bin/bash
# Daily CSS monitoring script

# Check for inline styles
INLINE_STYLES=$(grep -r 'style="' templates/ --exclude-dir=emails | wc -l)
if [ $INLINE_STYLES -gt 0 ]; then
    echo "WARNING: $INLINE_STYLES inline styles detected"
    # Send alert
fi

# Check CSS file sizes
CSS_SIZE=$(du -s static/css | cut -f1)
if [ $CSS_SIZE -gt 1000 ]; then
    echo "WARNING: CSS bundle size exceeding threshold"
    # Send alert
fi

# Check for CSS errors
CSS_ERRORS=$(css-validator static/css/*.css 2>&1 | grep -i error | wc -l)
if [ $CSS_ERRORS -gt 0 ]; then
    echo "ERROR: CSS validation errors detected"
    # Send alert
fi
```

### 2. Performance Monitoring

**Key Metrics:**
- CSS file load times
- Total CSS bundle size
- CSS parsing time
- Render-blocking CSS

**Monitoring Tools:**
- Browser DevTools
- Lighthouse audits
- WebPageTest
- Custom performance scripts

### 3. Security Monitoring

**CSP Violation Tracking:**
```javascript
// CSP violation reporting
document.addEventListener('securitypolicyviolation', (e) => {
    if (e.violatedDirective === 'style-src') {
        // Log CSS-related CSP violation
        console.error('CSS CSP Violation:', e);
        // Send to monitoring system
    }
});
```

## Documentation Maintenance

### 1. Documentation Updates

**When to Update:**
- New CSS files added
- Class naming conventions change
- File organization changes
- New maintenance procedures

**Update Process:**
1. Update CSS organization guide
2. Update maintenance guide
3. Update component documentation
4. Update deployment guides

### 2. Version Control

**Documentation Versioning:**
- Tag documentation versions
- Maintain changelog
- Track breaking changes
- Provide migration guides

## Training and Knowledge Transfer

### 1. Team Training

**CSS Guidelines Training:**
- CSS organization principles
- Security compliance requirements
- Maintenance procedures
- Emergency response protocols

### 2. Knowledge Documentation

**Maintain Knowledge Base:**
- Common issues and solutions
- Best practices documentation
- Troubleshooting guides
- Performance optimization tips

## Conclusion

Regular maintenance of the CSS codebase ensures:
- Continued security compliance
- Optimal performance
- Code quality and maintainability
- Team productivity and knowledge sharing

Follow these procedures to maintain a healthy, secure, and performant CSS architecture.