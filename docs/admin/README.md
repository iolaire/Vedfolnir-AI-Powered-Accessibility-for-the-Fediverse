# Admin Module Documentation

The admin module provides centralized administrative functionality for Vedfolnir, including user management, system health monitoring, data cleanup, and administrative oversight.

## Architecture

The admin module follows a modular architecture with clear separation of concerns:

```
admin/
├── __init__.py              # Module initialization and blueprint registration
├── routes/                  # Route handlers
│   ├── dashboard.py         # Main admin dashboard
│   ├── user_management.py   # User CRUD operations
│   ├── system_health.py     # Health monitoring routes
│   ├── cleanup.py          # Data cleanup routes
│   └── monitoring.py       # System monitoring routes
├── services/               # Business logic services
│   ├── user_service.py     # User management operations
│   ├── cleanup_service.py  # Data cleanup operations
│   └── monitoring_service.py # System monitoring
├── templates/              # Admin-specific templates
│   ├── base_admin.html     # Base admin template
│   ├── dashboard.html      # Admin dashboard
│   └── ...                 # Other admin templates
├── static/                 # Admin-specific assets
│   ├── css/admin.css       # Admin styles
│   └── js/admin.js         # Admin JavaScript
└── forms/                  # Form definitions
    └── user_forms.py       # User management forms
```

## Features

### User Management
- Create, edit, and delete users
- Role-based access control
- User activity monitoring
- Bulk user operations

### System Health Monitoring
- Real-time system health checks
- Component status monitoring
- Performance metrics
- Alert management

### Data Cleanup
- Archive old processing runs
- Clean up orphaned data
- User data management
- Bulk cleanup operations

### System Monitoring
- Active task monitoring
- Performance metrics
- Resource usage tracking
- Administrative controls

## Security

The admin module implements comprehensive security measures:

- **Role-based Access Control**: All admin routes require ADMIN role
- **CSRF Protection**: All forms include CSRF tokens
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: Protection against abuse
- **Audit Logging**: All admin actions are logged

## Usage

### Accessing Admin Interface

1. Log in with an admin account
2. Navigate to `/admin/` or use the admin navigation
3. Access various admin functions through the sidebar

### Adding New Admin Features

1. Create route handler in appropriate `routes/` module
2. Implement business logic in `services/` module
3. Create templates in `templates/` directory
4. Add forms if needed in `forms/` module
5. Register routes in the blueprint

## Migration from Main App

When moving admin functionality from the main app:

1. Move route handlers to appropriate admin route modules
2. Extract business logic to admin services
3. Move templates to admin templates directory
4. Update template references and URL generation
5. Update tests to use admin blueprint routes
6. Remove old admin routes from main app