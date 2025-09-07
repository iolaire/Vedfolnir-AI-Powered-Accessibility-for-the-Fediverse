# CSS Naming Conventions

## Overview

This document defines the CSS class naming conventions used in Vedfolnir to ensure consistency, maintainability, and clarity across the codebase.

## General Principles

### 1. Semantic Naming
- Use descriptive names that indicate purpose or function
- Avoid presentational names that describe appearance
- Choose names that remain valid if styling changes

**✅ Good Examples:**
```css
.modal-overlay          /* Describes function */
.navigation-menu        /* Describes purpose */
.error-message          /* Describes content type */
.user-profile-card      /* Describes component */
```

**❌ Bad Examples:**
```css
.red-text              /* Presentational */
.big-box               /* Appearance-based */
.left-thing            /* Vague and positional */
.div-1                 /* Non-semantic */
```

### 2. Consistency
- Use consistent patterns across similar components
- Follow established conventions within the codebase
- Maintain consistent word order and structure

### 3. Clarity
- Use clear, unambiguous names
- Avoid abbreviations unless widely understood
- Include context when necessary

## Naming Patterns

### 1. Component-Based Naming

**Pattern:** `component-element-modifier`

```css
/* Base component */
.modal-overlay { }

/* Component elements */
.modal-header { }
.modal-content { }
.modal-footer { }

/* Component modifiers */
.modal-overlay--large { }
.modal-overlay--centered { }
```

**Examples in Vedfolnir:**
```css
.progress-bar { }
.progress-bar-dynamic { }
.progress-bar--small { }

.caption-container { }
.caption-field { }
.caption-preview { }
```

### 2. Utility Class Naming

**Pattern:** `property-value` or `abbreviation-value`

```css
/* Display utilities */
.hidden { }
.visible { }
.d-none { }
.d-block { }
.d-flex { }

/* Width utilities */
.w-25 { }
.w-50 { }
.w-75 { }
.w-100 { }

/* Spacing utilities */
.m-0 { }    /* margin: 0 */
.p-2 { }    /* padding: 0.5rem */
.mt-3 { }   /* margin-top: 1rem */
```

### 3. State-Based Naming

**Pattern:** `base-class` + `state-modifier`

```css
/* Base states */
.modal-overlay { display: none; }
.action-option { display: none; }
.edit-mode { display: none; }

/* Active states */
.modal-overlay.show { display: block; }
.action-option.active { display: block; }
.edit-mode.active { display: block; }
```

**State Modifiers:**
- `.active` - Active/enabled state
- `.show` - Visible state
- `.hidden` - Hidden state
- `.disabled` - Disabled state
- `.selected` - Selected state
- `.expanded` - Expanded state
- `.collapsed` - Collapsed state

### 4. Size and Variant Naming

**Pattern:** `base-class-size` or `base-class--variant`

```css
/* Size variants */
.icon-sm { font-size: 1.5rem; }
.icon-md { font-size: 3rem; }
.icon-lg { font-size: 4rem; }

.progress-sm { height: 8px; }
.progress-md { height: 10px; }
.progress-lg { height: 20px; }

/* Style variants */
.button--primary { }
.button--secondary { }
.button--danger { }
```

## Category-Specific Conventions

### 1. Layout Classes

**Container Classes:**
```css
.container { }
.container-fluid { }
.wrapper { }
.section { }
```

**Grid Classes:**
```css
.row { }
.col { }
.col-md-6 { }
.grid { }
.grid-item { }
```

**Positioning Classes:**
```css
.position-relative { }
.position-absolute { }
.position-fixed { }
.position-sticky { }

.bulk-select-position { }    /* Specific positioning */
.image-zoom-wrapper { }      /* Functional positioning */
```

### 2. Component Classes

**Modal Components:**
```css
.modal-overlay { }
.modal-dialog { }
.modal-content { }
.modal-header { }
.modal-body { }
.modal-footer { }
.modal-backdrop { }
```

**Form Components:**
```css
.form-group { }
.form-control { }
.form-label { }
.form-text { }
.form-check { }
.form-switch { }

.edit-mode { }
.view-mode { }
.conditional-field { }
.urgency-field { }
```

**Navigation Components:**
```css
.navbar { }
.nav-link { }
.nav-item { }
.breadcrumb { }
.pagination { }
.tab-content { }
```

### 3. Utility Classes

**Display Utilities:**
```css
.hidden { }
.visible { }
.invisible { }
.d-none { }
.d-block { }
.d-inline { }
.d-inline-block { }
.d-flex { }
.d-grid { }
```

**Spacing Utilities:**
```css
/* Margin utilities */
.m-0, .m-1, .m-2, .m-3, .m-4, .m-5 { }
.mt-0, .mt-1, .mt-2, .mt-3, .mt-4, .mt-5 { }
.mr-0, .mr-1, .mr-2, .mr-3, .mr-4, .mr-5 { }
.mb-0, .mb-1, .mb-2, .mb-3, .mb-4, .mb-5 { }
.ml-0, .ml-1, .ml-2, .ml-3, .ml-4, .ml-5 { }

/* Padding utilities */
.p-0, .p-1, .p-2, .p-3, .p-4, .p-5 { }
.pt-0, .pt-1, .pt-2, .pt-3, .pt-4, .pt-5 { }
.pr-0, .pr-1, .pr-2, .pr-3, .pr-4, .pr-5 { }
.pb-0, .pb-1, .pb-2, .pb-3, .pb-4, .pb-5 { }
.pl-0, .pl-1, .pl-2, .pl-3, .pl-4, .pl-5 { }
```

**Width/Height Utilities:**
```css
.w-25 { width: 25%; }
.w-50 { width: 50%; }
.w-75 { width: 75%; }
.w-100 { width: 100%; }

.h-25 { height: 25%; }
.h-50 { height: 50%; }
.h-75 { height: 75%; }
.h-100 { height: 100%; }
```

**Text Utilities:**
```css
.text-left { }
.text-center { }
.text-right { }
.text-justify { }

.text-primary { }
.text-secondary { }
.text-success { }
.text-danger { }
.text-warning { }
.text-info { }
.text-muted { }
```

### 4. Functional Classes

**Interactive Classes:**
```css
.clickable { cursor: pointer; }
.draggable { cursor: move; }
.resizable { cursor: nw-resize; }
.disabled { cursor: not-allowed; }
```

**Scrollable Classes:**
```css
.scrollable { overflow: auto; }
.scrollable-x { overflow-x: auto; }
.scrollable-y { overflow-y: auto; }

.scrollable-sm { max-height: 80px; overflow-y: auto; }
.scrollable-md { max-height: 120px; overflow-y: auto; }
.scrollable-lg { max-height: 200px; overflow-y: auto; }
```

**Animation Classes:**
```css
.fade-in { }
.fade-out { }
.slide-up { }
.slide-down { }
.bounce { }
.pulse { }
```

## Vedfolnir-Specific Conventions

### 1. Application Components

**Caption Generation:**
```css
.caption-container { }
.caption-field { }
.caption-preview { }
.caption-quality-score { }
.caption-generation-progress { }
```

**Platform Management:**
```css
.platform-card { }
.platform-status { }
.platform-connection { }
.platform-switcher { }
```

**Admin Interface:**
```css
.admin-dashboard { }
.admin-sidebar { }
.admin-content { }
.admin-widget { }
.admin-action { }
```

**Review Interface:**
```css
.review-container { }
.review-image { }
.review-controls { }
.review-batch { }
.review-single { }
```

### 2. Security-Related Classes

**Extracted from Inline Styles:**
```css
/* Progress bars */
.progress-bar-dynamic { }
.progress-sm { }
.progress-md { }
.progress-lg { }

/* Modal states */
.modal-overlay { }
.modal-overlay.show { }
.action-option { }
.action-option.active { }

/* Form states */
.edit-mode { }
.edit-mode.active { }
.view-mode { }
.conditional-field { }
.conditional-field.show { }

/* Layout positioning */
.bulk-select-position { }
.bulk-select-checkbox { }
.image-zoom-wrapper { }
```

## BEM Methodology Integration

### Block-Element-Modifier (BEM) Pattern

**Structure:** `.block__element--modifier`

```css
/* Block */
.card { }

/* Elements */
.card__header { }
.card__body { }
.card__footer { }

/* Modifiers */
.card--large { }
.card--featured { }
.card__header--centered { }
```

**Vedfolnir BEM Examples:**
```css
/* Modal component */
.modal { }
.modal__overlay { }
.modal__dialog { }
.modal__content { }
.modal__header { }
.modal__body { }
.modal__footer { }
.modal--large { }
.modal--centered { }

/* Progress component */
.progress { }
.progress__bar { }
.progress__label { }
.progress--small { }
.progress--animated { }
```

## Naming Anti-Patterns

### 1. Avoid These Patterns

**❌ Presentational Names:**
```css
.red-button { }
.big-text { }
.left-sidebar { }
.blue-link { }
```

**❌ Non-Semantic Names:**
```css
.div1 { }
.content2 { }
.box-a { }
.thing { }
```

**❌ Overly Specific Names:**
```css
.homepage-header-navigation-menu-item-link { }
.user-profile-edit-form-submit-button { }
```

**❌ Inconsistent Patterns:**
```css
.btn-primary { }
.button-secondary { }
.primaryBtn { }
.BUTTON_DANGER { }
```

### 2. Better Alternatives

**✅ Semantic Alternatives:**
```css
.button--primary { }      /* Instead of .red-button */
.heading--large { }       /* Instead of .big-text */
.sidebar--navigation { }  /* Instead of .left-sidebar */
.link--external { }       /* Instead of .blue-link */
```

**✅ Meaningful Names:**
```css
.user-card { }           /* Instead of .div1 */
.article-content { }     /* Instead of .content2 */
.feature-box { }         /* Instead of .box-a */
.notification { }        /* Instead of .thing */
```

## Documentation Standards

### 1. CSS Comments

**File Headers:**
```css
/* Copyright (C) 2025 iolaire mcfadden. */
/* ... license text ... */

/**
 * Component Name CSS
 * 
 * Description of the component and its purpose.
 * 
 * Usage:
 * - .component-name for base styling
 * - .component-name--modifier for variations
 * - .component-name.state for state changes
 */
```

**Section Headers:**
```css
/* ==========================================================================
   Component Section Name
   ========================================================================== */
```

**Class Documentation:**
```css
/* Modal overlay for dialog boxes
 * Replaces: style="display: none;" in modal templates
 * Used in: user_modal.html, admin_modal.html, confirmation_modal.html
 * Toggle with: .show class
 * 
 * Example:
 * <div class="modal-overlay" id="myModal">
 *   <div class="modal-content">...</div>
 * </div>
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

### 2. Usage Examples

**Template Usage Documentation:**
```html
<!-- Modal with proper CSS classes -->
<div class="modal-overlay" id="confirmModal">
    <div class="modal-dialog modal-dialog--centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Confirm Action</h5>
            </div>
            <div class="modal-body">
                <p>Are you sure you want to proceed?</p>
            </div>
            <div class="modal-footer">
                <button class="button button--secondary" data-dismiss="modal">Cancel</button>
                <button class="button button--primary" id="confirmBtn">Confirm</button>
            </div>
        </div>
    </div>
</div>
```

**JavaScript Usage Documentation:**
```javascript
// Show modal using CSS classes
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.add('show');
}

// Hide modal using CSS classes
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('show');
}
```

## Validation and Enforcement

### 1. Automated Validation

**CSS Class Naming Linter:**
```javascript
// .stylelintrc.js
module.exports = {
    rules: {
        'selector-class-pattern': [
            '^[a-z]([a-z0-9-]+)?(__([a-z0-9]+-?)+)?(--([a-z0-9]+-?)+){0,2}$',
            {
                message: 'Expected class selector to be kebab-case BEM format'
            }
        ],
        'selector-max-class': 4,
        'selector-max-compound-selectors': 3
    }
};
```

### 2. Code Review Checklist

**CSS Naming Review:**
- [ ] Class names are semantic and descriptive
- [ ] Consistent naming patterns used
- [ ] No presentational names
- [ ] Appropriate BEM structure when applicable
- [ ] Consistent with existing codebase
- [ ] Properly documented with comments

## Migration Guidelines

### 1. Updating Existing Classes

**When renaming classes:**
1. Create new class with proper name
2. Add both old and new classes temporarily
3. Update all template usage
4. Remove old class after verification
5. Update documentation

**Example Migration:**
```css
/* Step 1: Add new class */
.modal-overlay { /* new semantic name */ }
.popup { /* old presentational name - deprecated */ }

/* Step 2: Update templates to use .modal-overlay */

/* Step 3: Remove deprecated class */
/* .popup { } - REMOVED */
```

### 2. Gradual Adoption

**For large codebases:**
- Adopt conventions for new components first
- Gradually refactor existing components
- Maintain consistency within component boundaries
- Document migration progress

## Conclusion

Consistent CSS naming conventions provide:
- **Maintainability**: Easy to understand and modify
- **Scalability**: Patterns that work as the codebase grows
- **Team Collaboration**: Clear communication through naming
- **Code Quality**: Professional and organized codebase

Follow these conventions to maintain a high-quality, maintainable CSS architecture in Vedfolnir.