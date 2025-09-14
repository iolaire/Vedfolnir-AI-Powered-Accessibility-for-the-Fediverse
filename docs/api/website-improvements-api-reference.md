# Website Improvements - API Reference

## Overview

This document provides comprehensive API reference for the Website Improvements implementation, covering all consolidated frameworks, admin interfaces, and enhanced functionality.

## Framework APIs

### Core Security Framework (`app/core/security/`)

#### CSP Middleware API

```python
from app.core.security.csp.middleware import CSPMiddleware

class CSPMiddleware:
    """Content Security Policy middleware for enhanced security."""
    
    def __init__(self, app=None):
        """Initialize CSP middleware.
        
        Args:
            app (Flask, optional): Flask application instance
        """
        
    def generate_nonce(self) -> str:
        """Generate secure nonce for CSP.
        
        Returns:
            str: Base64-encoded nonce string
            
        Example:
            >>> middleware = CSPMiddleware()
            >>> nonce = middleware.generate_nonce()
            >>> print(f"Nonce: {nonce}")
        """
        
    def validate_inline_content(self, content: str) -> bool:
        """Validate inline content against CSP policy.
        
        Args:
            content (str): Inline content to validate
            
        Returns:
            bool: True if content is CSP-compliant
            
        Example:
            >>> middleware = CSPMiddleware()
            >>> is_valid = middleware.validate_inline_content("<script>alert('test')</script>")
            >>> print(f"Content valid: {is_valid}")
        """
        
    def get_csp_header(self, nonce: str = None) -> str:
        """Generate CSP header string.
        
        Args:
            nonce (str, optional): Nonce to include in policy
            
        Returns:
            str: Complete CSP header value
            
        Example:
            >>> middleware = CSPMiddleware()
            >>> nonce = middleware.generate_nonce()
            >>> header = middleware.get_csp_header(nonce)
            >>> print(f"CSP Header: {header}")
        """
```

#### Security Access Control API

```python
from app.core.security.access_control import require_admin_access, SecurityAccessControl

def require_admin_access(f):
    """Decorator requiring admin access for route.
    
    Args:
        f (function): Route function to protect
        
    Returns:
        function: Decorated function with admin access check
        
    Example:
        >>> @app.route('/admin/dashboard')
        >>> @require_admin_access
        >>> def admin_dashboard():
        >>>     return render_template('admin/dashboard.html')
    """

class SecurityAccessControl:
    """Security access control management."""
    
    def __init__(self, db_manager):
        """Initialize access control.
        
        Args:
            db_manager: Database manager instance
        """
        
    def check_admin_access(self, user_id: int) -> bool:
        """Check if user has admin access.
        
        Args:
            user_id (int): User ID to check
            
        Returns:
            bool: True if user has admin access
            
        Example:
            >>> access_control = SecurityAccessControl(db_manager)
            >>> has_access = access_control.check_admin_access(1)
            >>> print(f"Admin access: {has_access}")
        """
        
    def log_access_attempt(self, user_id: int, route: str, success: bool):
        """Log access attempt for audit.
        
        Args:
            user_id (int): User attempting access
            route (str): Route being accessed
            success (bool): Whether access was granted
            
        Example:
            >>> access_control = SecurityAccessControl(db_manager)
            >>> access_control.log_access_attempt(1, '/admin/dashboard', True)
        """
```

### Core Session Framework (`app/core/session/`)

#### Session Manager API

```python
from app.core.session.manager import SessionManager

class SessionManager:
    """Unified session management with Redis primary and database fallback."""
    
    def __init__(self, redis_client, db_manager):
        """Initialize session manager.
        
        Args:
            redis_client: Redis client instance
            db_manager: Database manager instance
        """
        
    def create_session(self, user_id: int, platform_id: int = None) -> str:
        """Create new user session.
        
        Args:
            user_id (int): User ID for session
            platform_id (int, optional): Platform connection ID
            
        Returns:
            str: Session ID
            
        Example:
            >>> session_manager = SessionManager(redis_client, db_manager)
            >>> session_id = session_manager.create_session(1, 123)
            >>> print(f"Session created: {session_id}")
        """
        
    def get_session_data(self, session_id: str) -> dict:
        """Retrieve session data.
        
        Args:
            session_id (str): Session ID to retrieve
            
        Returns:
            dict: Session data or None if not found
            
        Example:
            >>> session_manager = SessionManager(redis_client, db_manager)
            >>> data = session_manager.get_session_data(session_id)
            >>> print(f"User ID: {data.get('user_id')}")
        """
        
    def update_session(self, session_id: str, data: dict):
        """Update session data.
        
        Args:
            session_id (str): Session ID to update
            data (dict): Data to update in session
            
        Example:
            >>> session_manager = SessionManager(redis_client, db_manager)
            >>> session_manager.update_session(session_id, {'last_activity': datetime.utcnow()})
        """
        
    def destroy_session(self, session_id: str):
        """Destroy user session.
        
        Args:
            session_id (str): Session ID to destroy
            
        Example:
            >>> session_manager = SessionManager(redis_client, db_manager)
            >>> session_manager.destroy_session(session_id)
        """
```

#### Session Middleware API

```python
from app.core.session.middleware.session_middleware import create_user_session, destroy_current_session

def create_user_session(user_id: int, platform_id: int = None) -> str:
    """Create user session with Flask integration.
    
    Args:
        user_id (int): User ID for session
        platform_id (int, optional): Platform connection ID
        
    Returns:
        str: Session ID
        
    Example:
        >>> from flask import request
        >>> session_id = create_user_session(1, 123)
        >>> # Session automatically set in Flask session
    """

def destroy_current_session():
    """Destroy current Flask session.
    
    Example:
        >>> destroy_current_session()
        >>> # Current session destroyed and cleared
    """
```

### Core Database Framework (`app/core/database/`)

#### Database Manager API

```python
from app.core.database.manager import DatabaseManager

class DatabaseManager:
    """Unified database management with MySQL support."""
    
    def __init__(self, config):
        """Initialize database manager.
        
        Args:
            config: Configuration object with database settings
        """
        
    def get_session(self):
        """Get database session context manager.
        
        Returns:
            contextmanager: Database session context
            
        Example:
            >>> db_manager = DatabaseManager(config)
            >>> with db_manager.get_session() as session:
            >>>     users = session.query(User).all()
        """
        
    def execute_query(self, query: str, params: dict = None):
        """Execute raw SQL query.
        
        Args:
            query (str): SQL query to execute
            params (dict, optional): Query parameters
            
        Returns:
            Result set from query execution
            
        Example:
            >>> db_manager = DatabaseManager(config)
            >>> result = db_manager.execute_query(
            >>>     "SELECT * FROM users WHERE id = :user_id",
            >>>     {"user_id": 1}
            >>> )
        """
        
    def get_connection_info(self) -> dict:
        """Get database connection information.
        
        Returns:
            dict: Connection status and metrics
            
        Example:
            >>> db_manager = DatabaseManager(config)
            >>> info = db_manager.get_connection_info()
            >>> print(f"Pool size: {info['pool_size']}")
        """
```

### Service Frameworks

#### Notification Manager API (`app/services/notification/`)

```python
from app.services.notification.manager.unified_manager import UnifiedNotificationManager

class UnifiedNotificationManager:
    """Unified notification management system."""
    
    def __init__(self, db_manager, websocket_manager=None):
        """Initialize notification manager.
        
        Args:
            db_manager: Database manager instance
            websocket_manager: WebSocket manager for real-time notifications
        """
        
    def send_admin_alert(self, message: str, severity: str = 'info'):
        """Send alert to administrators.
        
        Args:
            message (str): Alert message
            severity (str): Alert severity (info, warning, error, critical)
            
        Example:
            >>> notification_manager = UnifiedNotificationManager(db_manager)
            >>> notification_manager.send_admin_alert(
            >>>     "System maintenance scheduled", 
            >>>     severity='warning'
            >>> )
        """
        
    def send_user_notification(self, user_id: int, message: str, notification_type: str = 'info'):
        """Send notification to specific user.
        
        Args:
            user_id (int): Target user ID
            message (str): Notification message
            notification_type (str): Type of notification
            
        Example:
            >>> notification_manager = UnifiedNotificationManager(db_manager)
            >>> notification_manager.send_user_notification(
            >>>     1, 
            >>>     "Caption generation completed", 
            >>>     'success'
            >>> )
        """
        
    def get_user_notifications(self, user_id: int, limit: int = 50) -> list:
        """Get notifications for user.
        
        Args:
            user_id (int): User ID to get notifications for
            limit (int): Maximum number of notifications to return
            
        Returns:
            list: List of notification dictionaries
            
        Example:
            >>> notification_manager = UnifiedNotificationManager(db_manager)
            >>> notifications = notification_manager.get_user_notifications(1)
            >>> for notif in notifications:
            >>>     print(f"{notif['message']} - {notif['created_at']}")
        """
```

#### Monitoring System API (`app/services/monitoring/`)

```python
from app.services.monitoring.system.system_monitor import SystemMonitor

class SystemMonitor:
    """System monitoring and health tracking."""
    
    def __init__(self, db_manager):
        """Initialize system monitor.
        
        Args:
            db_manager: Database manager instance
        """
        
    def log_admin_access(self, user_id: int, route_path: str, ip_address: str = None):
        """Log admin route access.
        
        Args:
            user_id (int): User accessing admin route
            route_path (str): Admin route path
            ip_address (str, optional): User IP address
            
        Example:
            >>> monitor = SystemMonitor(db_manager)
            >>> monitor.log_admin_access(1, '/admin/dashboard', '192.168.1.1')
        """
        
    def get_system_health(self) -> dict:
        """Get current system health status.
        
        Returns:
            dict: System health metrics
            
        Example:
            >>> monitor = SystemMonitor(db_manager)
            >>> health = monitor.get_system_health()
            >>> print(f"CPU Usage: {health['cpu_usage']}%")
        """
        
    def log_performance_metric(self, metric_name: str, value: float, unit: str = 'ms'):
        """Log performance metric.
        
        Args:
            metric_name (str): Name of the metric
            value (float): Metric value
            unit (str): Unit of measurement
            
        Example:
            >>> monitor = SystemMonitor(db_manager)
            >>> monitor.log_performance_metric('admin_dashboard_load_time', 450.2, 'ms')
        """
```

## Admin Route APIs

### Platform Management Routes

```python
from app.blueprints.admin.platform_management import PlatformManagementRoutes

class PlatformManagementRoutes:
    """Admin routes for platform management."""
    
    def __init__(self, security_framework, session_manager, notification_manager):
        """Initialize platform management routes.
        
        Args:
            security_framework: Security framework instance
            session_manager: Session manager instance
            notification_manager: Notification manager instance
        """
        
    @require_admin_access
    def platform_list(self):
        """Display list of platform connections.
        
        Returns:
            Response: Rendered platform list template
            
        Route: GET /admin/platforms
        """
        
    @require_admin_access
    def platform_create(self):
        """Create new platform connection.
        
        Returns:
            Response: Redirect to platform list or form with errors
            
        Route: POST /admin/platforms/create
        """
        
    @require_admin_access
    def platform_edit(self, platform_id: int):
        """Edit existing platform connection.
        
        Args:
            platform_id (int): Platform connection ID to edit
            
        Returns:
            Response: Rendered edit form or redirect
            
        Route: GET/POST /admin/platforms/<int:platform_id>/edit
        """
```

### System Administration Routes

```python
from app.blueprints.admin.system_administration import SystemAdministrationRoutes

class SystemAdministrationRoutes:
    """Admin routes for system administration."""
    
    @require_admin_access
    def system_dashboard(self):
        """Display system administration dashboard.
        
        Returns:
            Response: Rendered system dashboard template
            
        Route: GET /admin/system
        """
        
    @require_admin_access
    def system_maintenance(self):
        """System maintenance operations.
        
        Returns:
            Response: Rendered maintenance interface
            
        Route: GET/POST /admin/system/maintenance
        """
        
    @require_admin_access
    def system_configuration(self):
        """System configuration management.
        
        Returns:
            Response: Rendered configuration interface
            
        Route: GET/POST /admin/system/configuration
        """
```

### Security Management Routes

```python
from app.blueprints.admin.security_management import SecurityManagementRoutes

class SecurityManagementRoutes:
    """Admin routes for security management."""
    
    @require_admin_access
    def security_dashboard(self):
        """Display security management dashboard.
        
        Returns:
            Response: Rendered security dashboard template
            
        Route: GET /admin/security
        """
        
    @require_admin_access
    def security_audit(self):
        """Display security audit logs.
        
        Returns:
            Response: Rendered audit log interface
            
        Route: GET /admin/security/audit
        """
        
    @require_admin_access
    def security_policies(self):
        """Manage security policies.
        
        Returns:
            Response: Rendered security policy interface
            
        Route: GET/POST /admin/security/policies
        """
```

## Admin API Endpoints

### System Status API

```python
@app.route('/admin/api/system-status')
@require_admin_access
def get_system_status():
    """Get current system status.
    
    Returns:
        JSON response with system status information
        
    Response Format:
        {
            "status": "healthy|warning|critical",
            "uptime": 86400,
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "disk_usage": 23.1,
            "active_sessions": 15,
            "database_status": "connected",
            "redis_status": "connected",
            "last_updated": "2025-01-15T10:30:00Z"
        }
        
    Example:
        >>> import requests
        >>> response = requests.get('/admin/api/system-status', 
        >>>                        headers={'Authorization': 'Bearer <token>'})
        >>> data = response.json()
        >>> print(f"System status: {data['status']}")
    """
```

### Performance Metrics API

```python
@app.route('/admin/api/performance-metrics')
@require_admin_access
def get_performance_metrics():
    """Get performance metrics.
    
    Returns:
        JSON response with performance data
        
    Response Format:
        {
            "response_times": {
                "admin_dashboard": 450.2,
                "user_dashboard": 320.1,
                "api_endpoints": 125.5
            },
            "throughput": {
                "requests_per_second": 45.2,
                "captions_per_hour": 120
            },
            "error_rates": {
                "4xx_errors": 2.1,
                "5xx_errors": 0.3
            },
            "database_performance": {
                "query_time_avg": 15.2,
                "connection_pool_usage": 65.4
            }
        }
        
    Example:
        >>> import requests
        >>> response = requests.get('/admin/api/performance-metrics')
        >>> metrics = response.json()
        >>> print(f"Dashboard load time: {metrics['response_times']['admin_dashboard']}ms")
    """
```

### Storage Status API

```python
@app.route('/admin/api/storage-status')
@require_admin_access
def get_storage_status():
    """Get storage status information.
    
    Returns:
        JSON response with storage data
        
    Response Format:
        {
            "total_storage": 1073741824,
            "used_storage": 536870912,
            "available_storage": 536870912,
            "usage_percentage": 50.0,
            "storage_breakdown": {
                "images": 402653184,
                "database": 104857600,
                "logs": 20971520,
                "temp": 8388608
            },
            "cleanup_recommendations": [
                {
                    "type": "temp_files",
                    "size": 8388608,
                    "description": "Temporary files older than 7 days"
                }
            ]
        }
        
    Example:
        >>> import requests
        >>> response = requests.get('/admin/api/storage-status')
        >>> storage = response.json()
        >>> print(f"Storage usage: {storage['usage_percentage']}%")
    """
```

## Error Handling APIs

### Security Error Handler

```python
from app.core.security.error_handling.handler import SecurityErrorHandler

class SecurityErrorHandler:
    """Handle security-related errors."""
    
    def handle_csp_violation(self, violation_data: dict):
        """Handle CSP violation.
        
        Args:
            violation_data (dict): CSP violation details
            
        Example:
            >>> handler = SecurityErrorHandler()
            >>> handler.handle_csp_violation({
            >>>     'blocked_uri': 'inline',
            >>>     'document_uri': '/admin/dashboard',
            >>>     'violated_directive': 'script-src'
            >>> })
        """
        
    def handle_access_denied(self, user_id: int, route: str):
        """Handle access denied error.
        
        Args:
            user_id (int): User attempting access
            route (str): Route being accessed
            
        Example:
            >>> handler = SecurityErrorHandler()
            >>> handler.handle_access_denied(1, '/admin/security')
        """
```

### Session Error Handler

```python
from app.core.session.error_handling.handler import SessionErrorHandler

class SessionErrorHandler:
    """Handle session-related errors."""
    
    def handle_session_expired(self, session_id: str):
        """Handle expired session.
        
        Args:
            session_id (str): Expired session ID
            
        Example:
            >>> handler = SessionErrorHandler()
            >>> handler.handle_session_expired('session_123')
        """
        
    def handle_redis_connection_error(self):
        """Handle Redis connection failure.
        
        Example:
            >>> handler = SessionErrorHandler()
            >>> handler.handle_redis_connection_error()
            >>> # Automatically falls back to database sessions
        """
```

## Testing APIs

### Test Utilities

```python
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

def create_test_user_with_platforms(db_manager, username="test_user", role=UserRole.REVIEWER):
    """Create test user with platform connections.
    
    Args:
        db_manager: Database manager instance
        username (str): Username for test user
        role (UserRole): User role
        
    Returns:
        tuple: (test_user, user_helper) for cleanup
        
    Example:
        >>> test_user, user_helper = create_test_user_with_platforms(
        >>>     db_manager, 
        >>>     username="test_admin", 
        >>>     role=UserRole.ADMIN
        >>> )
    """

def cleanup_test_user(user_helper):
    """Clean up test user and associated data.
    
    Args:
        user_helper: User helper from create_test_user_with_platforms
        
    Example:
        >>> cleanup_test_user(user_helper)
    """
```

### Admin Route Testing

```python
import unittest
from tests.admin.test_admin_routes import AdminRouteTestCase

class AdminRouteTestCase(unittest.TestCase):
    """Base test case for admin routes."""
    
    def setUp(self):
        """Set up test environment."""
        
    def test_admin_dashboard_access(self):
        """Test admin dashboard access.
        
        Example:
            >>> test_case = AdminRouteTestCase()
            >>> test_case.setUp()
            >>> test_case.test_admin_dashboard_access()
        """
        
    def test_platform_management_crud(self):
        """Test platform management CRUD operations.
        
        Example:
            >>> test_case = AdminRouteTestCase()
            >>> test_case.test_platform_management_crud()
        """
```

## Configuration APIs

### Framework Configuration

```python
from app.core.configuration.manager import ConfigurationManager

class ConfigurationManager:
    """Manage application configuration."""
    
    def get_security_config(self) -> dict:
        """Get security configuration.
        
        Returns:
            dict: Security configuration settings
            
        Example:
            >>> config_manager = ConfigurationManager()
            >>> security_config = config_manager.get_security_config()
            >>> print(f"CSP enabled: {security_config['csp_enabled']}")
        """
        
    def get_session_config(self) -> dict:
        """Get session configuration.
        
        Returns:
            dict: Session configuration settings
            
        Example:
            >>> config_manager = ConfigurationManager()
            >>> session_config = config_manager.get_session_config()
            >>> print(f"Redis URL: {session_config['redis_url']}")
        """
        
    def update_config(self, section: str, key: str, value):
        """Update configuration value.
        
        Args:
            section (str): Configuration section
            key (str): Configuration key
            value: New value
            
        Example:
            >>> config_manager = ConfigurationManager()
            >>> config_manager.update_config('security', 'csp_enabled', True)
        """
```

## Usage Examples

### Complete Admin Route Implementation

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

from flask import Blueprint, render_template, request, jsonify
from app.core.security.access_control import require_admin_access
from app.core.session.manager import SessionManager
from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from app.services.monitoring.system.system_monitor import SystemMonitor

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Initialize services
session_manager = SessionManager(redis_client, db_manager)
notification_manager = UnifiedNotificationManager(db_manager)
system_monitor = SystemMonitor(db_manager)

@admin_bp.route('/platforms')
@require_admin_access
def platform_management():
    """Platform management interface."""
    try:
        # Log admin access
        system_monitor.log_admin_access(
            current_user.id, 
            '/admin/platforms',
            request.remote_addr
        )
        
        # Get platform connections
        with db_manager.get_session() as session:
            platforms = session.query(PlatformConnection).all()
        
        return render_template('admin/platform_management.html', 
                             platforms=platforms)
    except Exception as e:
        # Send error notification
        notification_manager.send_admin_alert(
            f"Error in platform management: {str(e)}", 
            severity='error'
        )
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/api/system-status')
@require_admin_access
def api_system_status():
    """System status API endpoint."""
    try:
        health_data = system_monitor.get_system_health()
        return jsonify(health_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Complete Security Implementation

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

from app.core.security.csp.middleware import CSPMiddleware
from app.core.security.access_control import SecurityAccessControl
from app.core.security.error_handling.handler import SecurityErrorHandler

# Initialize security components
csp_middleware = CSPMiddleware(app)
access_control = SecurityAccessControl(db_manager)
error_handler = SecurityErrorHandler()

@app.before_request
def apply_security():
    """Apply security measures to all requests."""
    # Generate CSP nonce
    nonce = csp_middleware.generate_nonce()
    g.csp_nonce = nonce
    
    # Set CSP header
    csp_header = csp_middleware.get_csp_header(nonce)
    response.headers['Content-Security-Policy'] = csp_header

@app.errorhandler(403)
def handle_access_denied(error):
    """Handle access denied errors."""
    if current_user.is_authenticated:
        error_handler.handle_access_denied(current_user.id, request.path)
    return render_template('errors/403.html'), 403
```

This comprehensive API reference provides detailed documentation for all framework components, admin interfaces, and enhanced functionality in the Website Improvements implementation. Each API includes parameter documentation, return types, usage examples, and integration patterns for effective development and maintenance.