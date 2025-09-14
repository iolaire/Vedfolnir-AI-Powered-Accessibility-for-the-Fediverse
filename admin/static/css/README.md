# Admin CSS Files

This directory contains CSS files specific to the admin interface.

## Files

- `admin.css` - Main admin styles (sidebar, cards, tables, etc.)
- `admin_dashboard.css` - Dashboard-specific styles
- `admin_job_management.css` - Job management interface styles
- `admin-extracted.css` - Extracted admin styles
- `configuration_management.css` - Configuration management styles
- `user_management.css` - User management interface styles (NEW)

## User Management Styles

The `user_management.css` file contains styles extracted from inline CSS in the user management template, including:

- Dropdown positioning fixes for table-responsive containers
- User statistics card hover effects
- Table enhancements for user data
- Modal styling improvements
- Filter panel styling
- Responsive adjustments for mobile devices

## Usage

All CSS files are automatically included in the base admin template (`admin/templates/base_admin.html`).