# CSS Organization Guide

## Overview

This document provides comprehensive guidelines for CSS organization in Vedfolnir, following the CSS Security Enhancement implementation that removed all inline styles from HTML templates to achieve Content Security Policy (CSP) compliance.

## CSS File Structure

### Main Application CSS (`static/css/`)

```
static/css/
├── style.css                           # Main application styles
├── security-extracted.css              # Extracted inline styles (CSP compliance)
├── utilities.css                       # Utility classes (display, spacing, etc.)
├── components.css                      # Component-specific styles
├── css-variables.css                   # CSS custom properties and variables
├── caption_generation.css              # Caption generation page styles
├── platform_styles.css                # Platform-specific styling
├── notification-ui.css                 # Notification system styles
├── unified-notifications.css           # Unified notification components
├── email.css                          # Email template styles
├── admin.css                          # Admin interface base styles
├── bootstrap-fallback.css             # Bootstrap compatibility
├── fixes.css                          # Bug fixes and patches
└── legacy-notification-fallback.css   # Legacy notification support
```

### Admin CSS (`admin/static/css/`)

```
admin/static/css/
├── admin.css                          # Base admin styles
├── admin-extracted.css                # Extracted admin inline styles
├── admin_dashboard.css                # Dashboard-specific styles
├── admin_job_management.css           # Job management interface
└── configuration_management.css       # Configuration interface
```

## CSS Class Naming Conventions

### Utility Classes

#### Display Utilities
- `.hidden` - Primary utility for `display: none`
- `.visible` - Primary utility for `display: block`
- `.d-none` - Bootstrap-compatible `display: none`
- `.d-block` - Bootstrap-compatible `display: block`
- `.d-flex` - Bootstrap-compatible `display: flex`
- `.d-inline` - Bootstrap-compatible `display: inline`

#### Width Utilities
- `.w-0` - Width 0%
- `.w-60` - Width 60%
- `.w-75` - Width 75%
- `.w-85` - Width 85%
- `.w-90` - Width 90%
- `.w-100` - Width 100%

#### Icon Sizing
- `.icon-sm` - Small icons (1.5rem)
- `.icon-md` - Medium icons (3rem)
- `.icon-lg` - Large icons (4rem)

#### Scrollable Containers
- `.scrollable-sm` - Small scrollable container (max-height: 80px)
- `.scrollable-md` - Medium scrollable container (max-height: 120px)
- `.scrollable-lg` - Large scrollable container (max-height: 200px)

### Component Classes

#### Progress Bars
- `.progress-bar-dynamic` - Dynamic width progress bar using CSS variables
- `.progress-sm` - Small progress bar (height: 8px)
- `.progress-md` - Medium progress bar (height: 10px)
- `.progress-lg` - Large progress bar (height: 20px)

#### Modal Components
- `.modal-overlay` - Base modal overlay
- `.modal-overlay.show` - Visible modal state
- `.action-option` - Hidden action option
- `.action-option.active` - Visible action option

#### Form Components
- `.edit-mode` - Edit mode container
- `.edit-mode.active` - Active edit mode
- `.view-mode` - View mode container
- `.conditional-field` - Conditionally shown field
- `.conditional-field.show` - Visible conditional field

#### Layout Components
- `.bulk-select-position` - Absolute positioning for bulk select
- `.bulk-select-checkbox` - Scaled checkbox (transform: scale(1.5))
- `.image-zoom-wrapper` - Image zoom container (cursor: move)
- `.caption-container` - Caption text container with scroll

## CSS Organization Principles

### 1. Separation of Concerns

**Utility Classes** (`utilities.css`)
- Single-purpose classes
- Reusable across components
- No component-specific logic

**Component Classes** (`components.css`)
- Component-specific styling
- Encapsulated functionality
- Clear component boundaries

**Extracted Styles** (`security-extracted.css`)
- Previously inline styles
- Documented original template source
- CSP compliance focused

### 2. File Organization

**By Functionality**
- Group related styles in dedicated files
- Clear file naming conventions
- Logical import order

**By Scope**
- Application-wide styles in main directory
- Admin-specific styles in admin directory
- Component-specific styles clearly labeled

### 3. CSS Variable Usage

All CSS variables are centralized in `css-variables.css`:

```css
:root {
    /* Progress bar variables */
    --progress-height-sm: 8px;
    --progress-height-md: 10px;
    --progress-height-lg: 20px;
    
    /* Icon sizes */
    --icon-size-sm: 1.5rem;
    --icon-size-md: 3rem;
    --icon-size-lg: 4rem;
    
    /* Container dimensions */
    --caption-min-height: 80px;
    --caption-max-height: 120px;
    
    /* Color scheme */
    --primary-color: #007bff;
    --secondary-color: #6c757d;
    --success-color: #28a745;
    --warning-color: #ffc107;
    --danger-color: #dc3545;
}
```

## Guidelines for Preventing Inline CSS

### 1. Template Development Rules

**NEVER use inline styles in templates:**
```html
<!-- ❌ WRONG - Inline styles -->
<div style="display: none;">Content</div>
<div style="width: 75%;">Content</div>

<!-- ✅ CORRECT - CSS classes -->
<div class="hidden">Content</div>
<div class="w-75">Content</div>
```

### 2. Dynamic Styling Patterns

**Use CSS variables for dynamic values:**
```html
<!-- ❌ WRONG - Inline dynamic styles -->
<div class="progress-bar" style="width: {{ progress }}%;">

<!-- ✅ CORRECT - CSS variables -->
<div class="progress-bar-dynamic" style="--progress-width: {{ progress }}%;">
```

**Use CSS classes for state management:**
```javascript
// ❌ WRONG - Direct style manipulation
element.style.display = 'none';

// ✅ CORRECT - Class-based state management
element.classList.add('hidden');
element.classList.toggle('show');
```

### 3. New Component Development

When creating new components:

1. **Check existing utilities first** - Use existing utility classes when possible
2. **Create component-specific classes** - Add to `components.css` if component-specific
3. **Document the purpose** - Include comments explaining the class usage
4. **Test CSP compliance** - Verify no inline styles are needed

### 4. Template Review Checklist

Before committing templates:
- [ ] No `style=""` attributes present
- [ ] All styling uses CSS classes
- [ ] Dynamic styles use CSS variables
- [ ] State changes use class toggles
- [ ] CSP compliance verified

## CSS Class Usage Patterns

### Display State Management

```html
<!-- Modal visibility -->
<div class="modal-overlay" id="myModal">
    <div class="modal-content">...</div>
</div>

<script>
// Show modal
document.getElementById('myModal').classList.add('show');

// Hide modal
document.getElementById('myModal').classList.remove('show');
</script>
```

### Progress Bar Implementation

```html
<!-- Static progress bar -->
<div class="progress progress-md">
    <div class="progress-bar w-75"></div>
</div>

<!-- Dynamic progress bar -->
<div class="progress progress-md">
    <div class="progress-bar-dynamic" style="--progress-width: 75%;"></div>
</div>
```

### Form State Management

```html
<!-- Edit/View mode toggle -->
<div class="profile-section">
    <div class="view-mode" id="viewMode">
        <span>Current Value</span>
        <button onclick="toggleEditMode()">Edit</button>
    </div>
    <div class="edit-mode" id="editMode">
        <input type="text" value="Current Value">
        <button onclick="saveChanges()">Save</button>
    </div>
</div>

<script>
function toggleEditMode() {
    document.getElementById('viewMode').classList.add('hidden');
    document.getElementById('editMode').classList.add('active');
}
</script>
```

## Maintenance Guidelines

### 1. Adding New Styles

**Step 1: Determine Category**
- Utility class → Add to `utilities.css`
- Component-specific → Add to `components.css`
- Admin-specific → Add to `admin/static/css/admin-extracted.css`

**Step 2: Follow Naming Convention**
- Use semantic names (`.caption-container` not `.cc`)
- Use consistent prefixes (`.progress-`, `.modal-`, `.form-`)
- Use state suffixes (`.active`, `.show`, `.hidden`)

**Step 3: Document Usage**
```css
/* Caption container with scrolling
 * Replaces: style="min-height: 80px; max-height: 120px; overflow-y: auto;"
 * Used in: review_single.html, caption_generation.html
 */
.caption-container {
    min-height: var(--caption-min-height);
    max-height: var(--caption-max-height);
    overflow-y: auto;
}
```

### 2. Modifying Existing Styles

**Before making changes:**
1. Check all usage locations
2. Consider backward compatibility
3. Test across all affected templates
4. Update documentation

**Change process:**
1. Make changes in appropriate CSS file
2. Test all affected templates
3. Update this documentation if needed
4. Commit with descriptive message

### 3. Removing Deprecated Styles

**Deprecation process:**
1. Mark as deprecated in comments
2. Add deprecation notice in next release
3. Remove after one version cycle
4. Update all references

### 4. Performance Considerations

**CSS File Loading Order:**
1. `css-variables.css` (variables first)
2. `utilities.css` (base utilities)
3. `style.css` (main styles)
4. `components.css` (component styles)
5. `security-extracted.css` (extracted styles)
6. Page-specific CSS files

**Optimization guidelines:**
- Minimize CSS file size
- Avoid duplicate rules
- Use CSS variables for repeated values
- Group related selectors

## Email Template Exception

**Important Note:** Email templates (`templates/emails/`) are intentionally excluded from this CSS organization and retain inline styles. This is required for email client compatibility.

**Email template guidelines:**
- Inline styles are required and acceptable
- Use table-based layouts
- Include fallback styles
- Test across email clients

## Version Control and Security Tracking

### Commit Message Format

When making CSS changes related to security:
```
feat(css): extract inline styles from [template_name]

- Remove style="display: none;" from modal elements
- Add .hidden utility class usage
- Improve CSP compliance
- Refs: CSS Security Enhancement spec

Security: Removes inline styles for CSP compliance
```

### Security Improvement Tracking

Track security improvements in commit messages:
- `Security: Removes inline styles for CSP compliance`
- `Security: Adds CSP-compliant modal styling`
- `Security: Extracts dynamic progress bar styles`

### Documentation Updates

When CSS structure changes:
1. Update this documentation
2. Update component documentation
3. Update deployment guides
4. Update testing procedures

## Testing CSS Changes

### 1. Visual Regression Testing

Before and after screenshots for:
- All affected templates
- Different screen sizes
- Different browsers

### 2. CSP Compliance Testing

```bash
# Enable strict CSP headers
# Test all pages for violations
# Check browser console for errors
```

### 3. Functionality Testing

- Interactive elements work correctly
- State changes function properly
- Dynamic styles update correctly
- Cross-browser compatibility

### 4. Performance Testing

- CSS load times
- Render performance
- Cache efficiency
- Bundle size impact

## Troubleshooting Common Issues

### 1. Styles Not Applying

**Check CSS file inclusion:**
```html
<!-- Verify CSS files are included in correct order -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/css-variables.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/utilities.css') }}">
```

**Check class names:**
```html
<!-- Verify correct class names are used -->
<div class="hidden">  <!-- Not "hide" or "d-hidden" -->
```

### 2. Dynamic Styles Not Working

**Check CSS variable syntax:**
```css
/* Correct CSS variable usage */
.progress-bar-dynamic {
    width: var(--progress-width, 0%);
}
```

**Check JavaScript class manipulation:**
```javascript
// Correct class toggle
element.classList.toggle('hidden');
// Not: element.style.display = 'none';
```

### 3. CSP Violations

**Check for remaining inline styles:**
```bash
# Scan templates for inline styles
grep -r 'style="' templates/
```

**Verify CSP headers:**
```http
Content-Security-Policy: style-src 'self';
```

## Future Considerations

### 1. CSS Framework Integration

Consider integrating with CSS frameworks:
- Tailwind CSS for utility classes
- Bootstrap for component styles
- Custom framework for specific needs

### 2. CSS-in-JS Migration

For dynamic components, consider:
- Styled components
- CSS modules
- CSS-in-JS libraries

### 3. Build Process Integration

Consider adding:
- CSS minification
- Autoprefixer
- CSS linting
- Unused CSS removal

## Conclusion

This CSS organization system provides:
- **Security**: CSP compliance through external stylesheets
- **Maintainability**: Clear organization and naming conventions
- **Performance**: Optimized loading and caching
- **Scalability**: Structured approach for future growth

Follow these guidelines to maintain a secure, organized, and maintainable CSS codebase.