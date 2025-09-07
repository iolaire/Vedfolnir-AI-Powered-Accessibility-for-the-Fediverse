# Design Document

## Overview

The CSS Security Enhancement feature addresses Content Security Policy (CSP) violations caused by inline CSS styles in HTML templates. Based on analysis of the codebase, approximately 30+ instances of inline styles have been identified across templates, admin templates, and components. The solution involves systematically extracting these inline styles to external CSS files while maintaining visual consistency and functionality.

## Architecture

### Current State Analysis
- **Inline Styles Found**: 30+ instances across multiple template categories
- **Affected Templates**: Main templates, admin templates, components, and error pages
- **Style Types**: Progress bars, modal displays, positioning, sizing, and interactive elements
- **Existing CSS Structure**: Well-organized with separate files for different functionalities

### Target Architecture
- **Zero Inline Styles**: All `style=""` attributes removed from HTML templates
- **Organized CSS Files**: Styles grouped by functionality and template category
- **CSP Compliance**: Strict Content Security Policy without `unsafe-inline` for styles
- **Maintainable Structure**: Clear naming conventions and documentation

## Components and Interfaces

### CSS File Organization

#### Main Application CSS (`static/css/`)
- **`security-extracted.css`**: New file for extracted inline styles from main templates
- **`components.css`**: New file for component-specific styles
- **`progress-bars.css`**: New file for progress bar styling
- **`modals.css`**: New file for modal and overlay styling

#### Admin CSS (`admin/static/css/`)
- **`admin-extracted.css`**: New file for extracted admin inline styles
- **`admin-components.css`**: New file for admin component styles

### Template Categories and Affected Files

#### Progress Bar Styles
**Templates**: `caption_generation.html`, `review_single.html`, `bulk_admin_actions_modal.html`, `storage_limit_notification.html`, `caption_form_disabled.html`, `admin_job_details_modal.html`

**Inline Styles to Extract**:
```css
/* Progress bar width styling */
.progress-bar-dynamic { width: var(--progress-width); }

/* Progress bar height variations */
.progress-sm { height: 8px; }
.progress-md { height: 10px; }
.progress-lg { height: 20px; }
```

#### Modal and Display Styles
**Templates**: `batch_review.html`, `gdpr/privacy_request.html`, `viewer_dashboard.html`, `bulk_admin_actions_modal.html`, `profile.html`

**Inline Styles to Extract**:
```css
/* Hidden elements */
.hidden { display: none; }

/* Modal positioning */
.modal-overlay { display: none; }
.modal-overlay.show { display: block; }

/* Action options */
.action-option { display: none; }
.action-option.active { display: block; }
```

#### Positioning and Layout Styles
**Templates**: `batch_review.html`, `review_single.html`

**Inline Styles to Extract**:
```css
/* Absolute positioning */
.bulk-select-position {
    position: absolute;
    top: 10px;
    left: 10px;
    z-index: 10;
}

/* Checkbox scaling */
.bulk-select-checkbox {
    transform: scale(1.5);
}

/* Image zoom wrapper */
.image-zoom-wrapper {
    cursor: move;
    overflow: hidden;
}
```

#### Form and Content Styles
**Templates**: `review_single.html`, `login.html`

**Inline Styles to Extract**:
```css
/* Content containers */
.caption-container {
    min-height: 80px;
    max-height: 120px;
    overflow-y: auto;
}

/* Form fields */
.caption-field {
    min-height: 80px;
}

/* Icon styling */
.login-icon {
    font-size: 3rem;
}

/* Maintenance icon */
.maintenance-icon {
    font-size: 4rem;
}
```

## Data Models

### CSS Class Mapping
```javascript
// Template to CSS class mapping
const styleMapping = {
    'progress-bar-width': 'progress-bar-dynamic',
    'display-none': 'hidden',
    'modal-display': 'modal-overlay',
    'absolute-positioning': 'bulk-select-position',
    'checkbox-scaling': 'bulk-select-checkbox',
    'cursor-move': 'image-zoom-wrapper',
    'min-max-height': 'caption-container',
    'icon-sizing': 'login-icon'
};
```

### CSS Variable System
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
}
```

## Error Handling

### Template Validation
- **Pre-deployment Checks**: Automated scanning for remaining inline styles
- **Visual Regression Testing**: Screenshot comparison before/after changes
- **CSP Violation Monitoring**: Browser console error detection
- **Fallback Mechanisms**: Graceful degradation if CSS fails to load

### Migration Safety
- **Backup Strategy**: Git branches for each template category
- **Rollback Procedures**: Quick revert mechanisms for critical issues
- **Staged Deployment**: Template-by-template migration approach
- **Testing Checkpoints**: Validation after each template conversion

## Testing Strategy

### Automated Testing
```python
# CSS Security Test Suite
class TestCSSSecurityEnhancement(unittest.TestCase):
    def test_no_inline_styles(self):
        """Verify no inline styles remain in templates"""
        
    def test_css_files_exist(self):
        """Verify all new CSS files are created"""
        
    def test_visual_consistency(self):
        """Compare screenshots before/after changes"""
        
    def test_csp_compliance(self):
        """Verify no CSP violations in browser console"""
```

### Manual Testing Checklist
- [ ] All templates render correctly
- [ ] Interactive elements function properly
- [ ] Progress bars display accurate percentages
- [ ] Modals show/hide correctly
- [ ] Responsive behavior maintained
- [ ] No console errors or warnings

### Browser Testing
- **Chrome**: CSP violation detection
- **Firefox**: Style application verification
- **Safari**: WebKit compatibility testing
- **Edge**: Cross-browser consistency

### Performance Testing
- **CSS Load Times**: Measure external CSS loading impact
- **Render Performance**: Compare page load speeds
- **Cache Efficiency**: Verify CSS caching behavior
- **Bundle Size**: Monitor total CSS file sizes

## Implementation Phases

### Phase 1: Core Template Styles
- Extract progress bar styles
- Create base CSS files
- Update main templates

### Phase 2: Component Styles
- Extract modal and display styles
- Update component templates
- Test interactive functionality

### Phase 3: Admin Template Styles
- Extract admin-specific styles
- Update admin templates
- Verify admin functionality

### Phase 4: CSP Implementation
- Enable strict CSP headers
- Validate no violations
- Performance optimization

## Security Considerations

### Content Security Policy
```http
Content-Security-Policy: 
    default-src 'self';
    style-src 'self';
    script-src 'self';
    img-src 'self' data:;
```

### CSS Injection Prevention
- **Input Sanitization**: Prevent user-controlled CSS
- **File Integrity**: Verify CSS file checksums
- **Access Controls**: Restrict CSS file modifications
- **Audit Logging**: Track CSS-related changes