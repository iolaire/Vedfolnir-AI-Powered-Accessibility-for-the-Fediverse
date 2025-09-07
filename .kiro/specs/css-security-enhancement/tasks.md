# Implementation Plan

- [x] 1. Create base CSS files for extracted styles
  - Create `static/css/security-extracted.css` with copyright header and base structure
  - Create `static/css/components.css` for component-specific styles
  - Create `admin/static/css/admin-extracted.css` for admin template styles
  - _Requirements: 2.2, 2.4_

- [x] 2. Extract progress bar inline styles
  - [x] 2.1 Create progress bar CSS classes in security-extracted.css
    - Write CSS classes for dynamic width progress bars using CSS variables
    - Create height variation classes (sm, md, lg) for different progress bar sizes
    - Add responsive progress bar styling
    - _Requirements: 1.1, 1.2, 3.1_

  - [x] 2.2 Update caption_generation.html progress bar
    - Remove inline `style="width: {{ active_task.progress_percent or 0 }}%"` from progress bar
    - Replace with CSS class and data attribute for dynamic width
    - Test progress bar functionality with JavaScript updates
    - _Requirements: 1.3, 3.3_

  - [x] 2.3 Update review_single.html progress bars
    - Remove inline `style="width: {{ image.caption_quality_score }}%"` from quality score progress bar
    - Replace with CSS class and data attribute system
    - Verify quality score visualization remains accurate
    - _Requirements: 1.3, 3.1_

  - [x] 2.4 Update admin and component progress bars
    - Remove inline styles from `bulk_admin_actions_modal.html` progress bars
    - Remove inline styles from `storage_limit_notification.html` progress bars
    - Remove inline styles from `caption_form_disabled.html` progress bars
    - Remove inline styles from `admin_job_details_modal.html` progress bars
    - _Requirements: 1.1, 1.2, 3.1_

- [x] 3. Extract modal and display inline styles
  - [x] 3.1 Create modal and display CSS classes
    - Write CSS classes for hidden elements (display: none)
    - Create modal overlay and visibility toggle classes
    - Add action option display/hide classes
    - _Requirements: 1.1, 2.2_

  - [x] 3.2 Update batch_review.html modal styles
    - Remove inline `style="display: none;"` from filter panel
    - Replace with CSS class for hidden state
    - Update JavaScript to toggle visibility classes
    - _Requirements: 1.2, 3.3_

  - [x] 3.3 Update component modal templates
    - Remove inline styles from `viewer_dashboard.html` platform switcher modal
    - Remove inline styles from `bulk_admin_actions_modal.html` action options
    - Remove inline styles from `gdpr/privacy_request.html` urgency field
    - Remove inline styles from `profile.html` edit mode
    - _Requirements: 1.1, 1.2, 3.1_

- [x] 4. Extract positioning and layout inline styles
  - [x] 4.1 Create positioning CSS classes in components.css
    - Write CSS classes for absolute positioning (bulk select checkboxes)
    - Create transform scale classes for checkbox sizing
    - Add cursor and overflow classes for image zoom functionality
    - _Requirements: 1.1, 2.2_

  - [x] 4.2 Update batch_review.html positioning styles
    - Remove inline `style="top: 10px; left: 10px; z-index: 10;"` from bulk select positioning
    - Remove inline `style="transform: scale(1.5);"` from checkbox scaling
    - Remove inline `style="cursor: move;"` from image zoom wrapper
    - Replace with semantic CSS classes
    - _Requirements: 1.2, 3.1_

  - [x] 4.3 Update review_single.html positioning styles
    - Remove inline `style="cursor: move;"` from image zoom wrapper
    - Replace with CSS class for consistent cursor behavior
    - Test image zoom functionality remains intact
    - _Requirements: 1.2, 3.3_

- [x] 5. Extract form and content inline styles
  - [x] 5.1 Create form and content CSS classes
    - Write CSS classes for min/max height containers
    - Create icon sizing classes for different icon sizes
    - Add form field height classes
    - _Requirements: 1.1, 2.2_

  - [x] 5.2 Update review_single.html content styles
    - Remove inline `style="min-height: 80px; max-height: 120px; overflow-y: auto;"` from caption container
    - Remove inline `style="min-height: 80px;"` from caption field
    - Replace with semantic CSS classes
    - _Requirements: 1.2, 3.1_

  - [x] 5.3 Update login.html and error template styles
    - Remove inline `style="font-size: 3rem;"` from login icon
    - Remove inline `style="font-size: 4rem;"` from maintenance icon
    - Replace with icon sizing CSS classes
    - _Requirements: 1.1, 1.2_

- [x] 6. Update template CSS includes
  - [x] 6.1 Add new CSS files to base templates
    - Update `templates/base.html` to include new CSS files
    - Update `admin/templates/base_admin.html` to include admin CSS files
    - Ensure proper loading order for CSS dependencies
    - _Requirements: 2.2, 3.1_

  - [x] 6.2 Update component template includes
    - Add CSS includes to component templates that don't inherit from base
    - Verify all templates have access to required CSS classes
    - Test CSS loading in different template contexts
    - _Requirements: 2.2, 3.3_

- [x] 7. Implement JavaScript updates for dynamic styles
  - [x] 7.1 Update progress bar JavaScript
    - Modify JavaScript code to update CSS custom properties instead of inline styles
    - Create utility functions for progress bar updates
    - Test dynamic progress updates in caption generation
    - _Requirements: 3.3, 1.3_

  - [x] 7.2 Update modal visibility JavaScript
    - Modify JavaScript to toggle CSS classes instead of inline display styles
    - Update modal show/hide functions to use CSS classes
    - Test modal functionality across all affected templates
    - _Requirements: 3.3, 1.3_

- [x] 8. Apply CSS security enhancements to landing page
  - [x] 8.1 Extract landing page inline styles
    - Remove inline styles from `templates/landing.html` hero section
    - Remove inline styles from feature cards and layout elements
    - Remove inline styles from call-to-action buttons and forms
    - _Requirements: 1.1, 1.2, 2.2_

  - [x] 8.2 Create landing page specific CSS classes
    - Add landing page styles to `static/css/security-extracted.css`
    - Create responsive layout classes for landing page sections
    - Add hero section styling classes with proper spacing
    - _Requirements: 2.2, 3.1_

  - [x] 8.3 Update landing page template structure
    - Replace inline styles with semantic CSS classes
    - Ensure landing page includes new CSS files
    - Test landing page functionality and visual consistency
    - _Requirements: 1.3, 3.3_

- [-] 9. Create comprehensive test suite
  - [x] 9.1 Write automated CSS security tests
    - Create test to scan all HTML templates for remaining inline styles
    - Write test to verify all new CSS files exist and are accessible
    - Create test to check CSS class usage in templates
    - _Requirements: 4.1, 4.2_

  - [n] 9.2 Write visual consistency tests
    - Create screenshot comparison tests for key templates
    - Write tests to verify interactive element functionality
    - Create tests for responsive behavior preservation
    - _Requirements: 4.1, 3.1, 3.2_

  - [n] 9.3 Write CSP compliance tests
    - Create test to verify no CSP violations in browser console
    - Write test to check strict CSP header compatibility
    - Create test for CSS loading without security errors
    - _Requirements: 4.3, 1.4_

- [x] 10. Update CSS extraction helper to exclude email templates
  - [x] 10.1 Modify CSS extraction helper script
    - Update `tests/scripts/css_extraction_helper.py` to exclude `templates/emails/` directory
    - Add documentation explaining why email templates retain inline CSS
    - Update extraction report to show email templates as intentionally excluded
    - _Requirements: 4.1, 5.1_

  - [x] 10.2 Document email template CSS policy
    - Create documentation explaining email template inline CSS policy
    - Document that email templates require inline CSS for email client compatibility
    - Add guidelines for maintaining email template styles
    - _Requirements: 5.1, 5.3_

- [ ] 11. Extract admin template remaining inline styles
  - [x] 11.1 Extract admin dashboard inline styles
    - Remove inline styles from `admin/templates/performance_dashboard.html`
    - Remove inline styles from `admin/templates/admin_system_logs.html`
    - Remove inline styles from `admin/templates/websocket_diagnostic.html`
    - Remove inline styles from `admin/templates/admin_job_management.html`
    - _Requirements: 1.1, 1.2_

  - [x] 11.2 Extract admin component inline styles
    - Remove inline styles from `admin/templates/components/admin_context_switcher.html`
    - Remove inline styles from `admin/templates/components/user_limits_modal.html`
    - Remove inline styles from `admin/templates/components/admin_job_history_modal.html`
    - Remove inline styles from `admin/templates/components/job_details_modal.html`
    - Remove inline styles from `admin/templates/components/system_maintenance_modal.html`
    - _Requirements: 1.1, 1.2_

  - [x] 11.3 Extract admin monitoring inline styles
    - Remove inline styles from `admin/templates/admin_monitoring.html`
    - Remove inline styles from `admin/templates/enhanced_monitoring_dashboard.html`
    - Remove inline styles from `admin/templates/maintenance_monitoring_dashboard.html`
    - Remove inline styles from `admin/templates/maintenance_mode_dashboard.html`
    - Remove inline styles from `admin/templates/admin_system_maintenance.html`
    - _Requirements: 1.1, 1.2_

- [x] 12. Extract main template remaining inline styles
  - [x] 12.1 Extract index page inline styles
    - Remove gradient background inline styles from `templates/index.html`
    - Remove progress bar width inline styles from `templates/index.html`
    - Remove icon sizing inline styles from `templates/index.html`
    - Create index-specific CSS classes for hero section and features
    - _Requirements: 1.1, 1.2, 2.2_

  - [x] 12.2 Extract review template inline styles
    - Remove inline styles from `templates/review.html`
    - Remove inline styles from `templates/review_batch.html`
    - Remove inline styles from `templates/review_batches.html`
    - Create review-specific CSS classes for image previews and layouts
    - _Requirements: 1.1, 1.2_

  - [x] 12.3 Extract user management template inline styles
    - Remove inline styles from `templates/user_management/reset_password.html`
    - Remove inline styles from `templates/user_management/change_password.html`
    - Remove inline styles from `templates/first_time_setup.html`
    - Create user management CSS classes for forms and progress indicators
    - _Requirements: 1.1, 1.2_

- [x] 13. Create comprehensive CSS class system
  - [x] 13.1 Create utility CSS classes
    - Add `.hidden` class for `display: none` (used in 47 files)
    - Add icon sizing classes `.icon-sm`, `.icon-md`, `.icon-lg` for font-size variations
    - Add width percentage classes `.w-0`, `.w-60`, `.w-75`, `.w-85`, `.w-90`
    - Add dimension classes for common width/height combinations
    - _Requirements: 2.2, 2.3_

  - [x] 13.2 Create layout CSS classes
    - Add scrollable container classes `.scrollable-sm`, `.scrollable-md`, `.scrollable-lg`
    - Add image preview classes for consistent image sizing
    - Add progress bar classes for different heights and dynamic widths
    - Add margin and padding utility classes
    - _Requirements: 2.2, 2.3_

  - [x] 13.3 Create color and background CSS classes
    - Add color utility classes for common text colors
    - Add background utility classes for alerts and notifications
    - Add gradient classes for hero sections and buttons
    - Add theme-consistent color variables
    - _Requirements: 2.2, 2.3_

- [x] 14. Update CSS file includes and organization
  - [x] 14.1 Update base template CSS includes
    - Add email CSS file to email templates
    - Add utility CSS file to all base templates
    - Ensure proper CSS loading order for dependencies
    - Test CSS loading performance impact
    - _Requirements: 2.2, 3.1_

  - [x] 14.2 Optimize CSS file structure
    - Consolidate similar CSS classes across files
    - Remove duplicate CSS rules
    - Optimize CSS file sizes and loading
    - Create CSS documentation for maintainability
    - _Requirements: 2.2, 5.1_

- [x] 15. Final validation and testing
  - [x] 15.1 Run comprehensive inline style scan
    - Execute CSS extraction helper to verify zero remaining inline styles
    - Test all templates for visual consistency
    - Verify all interactive elements function correctly
    - Check browser console for CSS-related errors
    - _Requirements: 4.1, 4.2, 1.3_

  - [x] 15.2 Extract remaining 35 inline styles from 23 template files
    - Remove `display: none;` inline styles from 25 locations (most common pattern)
    - Extract font-size inline styles (1.5rem, 2rem, 3rem) to icon sizing classes
    - Remove dynamic width inline styles from progress bars and containers
    - Extract max-height inline styles from scrollable containers
    - Update templates: index.html, caption_generation.html, admin_monitoring.html, dashboard.html, and 19 others
    - _Requirements: 1.1, 1.2, 2.2_

  - [x] 15.3 Perform CSP compliance testing
    - Enable strict Content Security Policy headers
    - Test all pages for CSP violations
    - Verify no `unsafe-inline` style-src needed
    - Document CSP configuration for deployment
    - _Requirements: 4.3, 1.4_

- [ ] 16. Documentation and deployment preparation
  - [-] 16.1 Create CSS organization documentation
    - Document the complete CSS file structure and organization
    - Create guidelines for preventing future inline CSS usage
    - Document CSS class naming conventions and usage patterns
    - Create maintenance guide for CSS updates
    - _Requirements: 5.1, 5.3_

  - [ ] 16.2 Create deployment and rollback procedures
    - Document step-by-step deployment process for CSS changes
    - Create rollback procedures for quick reversion if needed
    - Document testing checklist for post-deployment verification
    - Create monitoring procedures for CSS-related issues
    - _Requirements: 4.4, 5.4_