# CSS Form and Content Classes Documentation

## Overview

This document describes the form and content CSS classes created as part of the CSS Security Enhancement project. These classes replace inline styles to improve Content Security Policy (CSP) compliance.

## Min/Max Height Container Classes

### Basic Container Classes
- `.min-height-sm` - Minimum height: 60px
- `.min-height-md` - Minimum height: 80px (default caption height)
- `.min-height-lg` - Minimum height: 120px
- `.min-height-xl` - Minimum height: 160px

- `.max-height-sm` - Maximum height: 80px with auto scroll
- `.max-height-md` - Maximum height: 120px with auto scroll (default caption height)
- `.max-height-lg` - Maximum height: 200px with auto scroll
- `.max-height-xl` - Maximum height: 300px with auto scroll

### Combined Container Classes
- `.container-sm` - Min: 60px, Max: 80px with scroll
- `.container-md` - Min: 80px, Max: 120px with scroll (default caption container)
- `.container-lg` - Min: 120px, Max: 200px with scroll
- `.container-xl` - Min: 160px, Max: 300px with scroll

## Icon Sizing Classes

### Standard Icon Sizes
- `.icon-xs` - 0.5rem
- `.icon-sm` - 1.5rem
- `.icon-md` - 3rem (login icon size)
- `.icon-lg` - 4rem (maintenance icon size)
- `.icon-xl` - 5rem
- `.icon-2xl` - 6rem
- `.icon-3xl` - 7rem
- `.icon-4xl` - 8rem

### Specific Use Case Icons
- `.icon-button` - 1.25rem (for button icons)
- `.icon-nav` - 1.5rem (for navigation icons)
- `.icon-header` - 2rem (for header icons)
- `.icon-hero` - 3rem (for hero section icons)
- `.icon-display` - 4rem (for large display icons)

### Template-Specific Icons
- `.login-icon` - 3rem (for login page icon)
- `.maintenance-icon` - 4rem (for maintenance page icon)

## Form Field Height Classes

### Form Field Classes
- `.form-field-sm` - Minimum height: 60px
- `.form-field-md` - Minimum height: 80px
- `.form-field-lg` - Minimum height: 120px
- `.form-field-xl` - Minimum height: 160px

### Textarea Classes
- `.textarea-sm` - Min height: 60px, vertical resize
- `.textarea-md` - Min height: 80px, vertical resize
- `.textarea-lg` - Min height: 120px, vertical resize
- `.textarea-xl` - Min height: 160px, vertical resize

### Input Field Classes
- `.input-sm` - Height: 32px, padding: 4px 8px
- `.input-md` - Height: 38px, padding: 6px 12px
- `.input-lg` - Height: 46px, padding: 8px 16px
- `.input-xl` - Height: 54px, padding: 10px 20px

## Special Purpose Classes

### Caption-Specific Classes
- `.caption-container` - Min: 80px, Max: 120px with scroll, bordered
- `.caption-field` - Min height: 80px, vertical resize

### Profile Avatar Classes
- `.profile-avatar` - 60x60px
- `.profile-avatar-sm` - 40x40px
- `.profile-avatar-lg` - 80x80px
- `.profile-avatar-xl` - 120x120px

## Form Utility Classes

### Styling Utilities
- `.form-field-bordered` - Adds border and padding
- `.form-field-rounded` - Rounded corners
- `.form-field-shadow` - Drop shadow
- `.form-field-focus` - Focus state styling

### Validation States
- `.form-field-valid` - Green border for valid fields
- `.form-field-invalid` - Red border for invalid fields
- `.form-field-warning` - Yellow border for warnings

### Layout Utilities
- `.form-group-compact` - Reduced margin (0.5rem)
- `.form-group-spaced` - Increased margin (1.5rem)
- `.form-group-inline` - Inline flex layout with gap

### Content Areas
- `.content-area` - Basic content area with padding
- `.content-area-bordered` - With border
- `.content-area-shadow` - With shadow
- `.scrollable-content` - Max height 300px with scroll
- `.scrollable-content-sm` - Max height 150px with scroll
- `.scrollable-content-lg` - Max height 500px with scroll

## CSS Variables

The following CSS variables control the dimensions:

```css
:root {
    /* Container dimensions */
    --caption-min-height: 80px;
    --caption-max-height: 120px;
    
    /* Icon sizes */
    --icon-size-sm: 1.5rem;
    --icon-size-md: 3rem;
    --icon-size-lg: 4rem;
    
    /* Form field dimensions */
    --form-field-height-sm: 32px;
    --form-field-height-md: 38px;
    --form-field-height-lg: 46px;
    
    /* Colors */
    --form-border-color: #dee2e6;
    --form-bg-color: #f8f9fa;
    --form-focus-color: #007bff;
}
```

## Usage Examples

### Replace Inline Styles

**Before:**
```html
<div style="min-height: 80px; max-height: 120px; overflow-y: auto;">
    Caption content
</div>
```

**After:**
```html
<div class="caption-container">
    Caption content
</div>
```

**Before:**
```html
<i class="fas fa-user" style="font-size: 3rem;"></i>
```

**After:**
```html
<i class="fas fa-user login-icon"></i>
```

**Before:**
```html
<textarea style="min-height: 80px;"></textarea>
```

**After:**
```html
<textarea class="caption-field"></textarea>
```

## Files Modified

- `static/css/security-extracted.css` - Main form and content classes
- `static/css/components.css` - Additional form utility classes
- `tests/security/test_css_form_content_classes.py` - Test coverage

## Requirements Satisfied

- **Requirement 1.1**: CSS classes enable extraction of inline styles
- **Requirement 2.2**: Follows existing naming conventions and includes copyright headers