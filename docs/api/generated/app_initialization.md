# app_initialization

Web Application Initialization with Session Management

This module provides comprehensive initialization of the Flask web application
with proper session management integration to prevent DetachedInstanceError.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/app_initialization.py`

## Classes

### SessionManagedFlaskApp

```python
class SessionManagedFlaskApp
```

Flask application factory with integrated session management.

This class provides a complete Flask application setup with:
- Request-scoped session management
- Database context middleware
- Session-aware user loading
- DetachedInstanceError recovery
- Safe template context processing

**Methods:**

#### __init__

```python
def __init__(self, config)
```

Initialize the session-managed Flask application.

Args:
    config: Application configuration object

**Type:** Instance method

#### create_app

```python
def create_app(self) -> Flask
```

Create and configure the Flask application with session management.

Returns:
    Configured Flask application instance

**Type:** Instance method

#### _initialize_session_management

```python
def _initialize_session_management(self)
```

Initialize request-scoped session management components.

**Type:** Instance method

#### _initialize_flask_login

```python
def _initialize_flask_login(self)
```

Initialize Flask-Login with session-aware user loader.

**Type:** Instance method

#### _initialize_error_handling

```python
def _initialize_error_handling(self)
```

Initialize DetachedInstanceError recovery and global error handling.

**Type:** Instance method

#### _initialize_template_context

```python
def _initialize_template_context(self)
```

Initialize safe template context processing.

**Type:** Instance method

#### _register_components

```python
def _register_components(self)
```

Register session management components with the Flask app.

**Type:** Instance method

#### get_initialization_status

```python
def get_initialization_status(self) -> dict
```

Get status of initialization components.

Returns:
    Dictionary containing initialization status

**Type:** Instance method

## Functions

### create_session_managed_app

```python
def create_session_managed_app(config) -> Flask
```

Factory function to create a Flask app with session management.

Args:
    config: Application configuration object
    
Returns:
    Configured Flask application instance

### validate_session_management_setup

```python
def validate_session_management_setup(app: Flask) -> dict
```

Validate that session management is properly set up in the Flask app.

Args:
    app: Flask application instance to validate
    
Returns:
    Dictionary containing validation results

### get_session_management_info

```python
def get_session_management_info(app: Flask) -> dict
```

Get information about session management setup for monitoring.

Args:
    app: Flask application instance
    
Returns:
    Dictionary containing session management information

