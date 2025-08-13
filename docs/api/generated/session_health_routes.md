# session_health_routes

Session Management Health Check Routes

Provides HTTP endpoints for session management health monitoring, alerting, and dashboard functionality.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_health_routes.py`

## Functions

### admin_required

```python
def admin_required(f)
```

Decorator to require admin role for access.

### health_status

```python
def health_status()
```

Get current session management health status.

**Decorators:**
- `@session_health_bp.route('/status')`
- `@login_required`
- `@admin_required`

### component_health

```python
def component_health(component_name)
```

Get health status for a specific session component.

**Decorators:**
- `@session_health_bp.route('/component/<component_name>')`
- `@login_required`
- `@admin_required`

### health_alerts

```python
def health_alerts()
```

Get session management health alerts.

**Decorators:**
- `@session_health_bp.route('/alerts')`
- `@login_required`
- `@admin_required`

### health_metrics

```python
def health_metrics()
```

Get session management performance metrics.

**Decorators:**
- `@session_health_bp.route('/metrics')`
- `@login_required`
- `@admin_required`

### health_dashboard

```python
def health_dashboard()
```

Render session management health dashboard.

**Decorators:**
- `@session_health_bp.route('/dashboard')`
- `@login_required`
- `@admin_required`

### admin_health

```python
def admin_health()
```

Admin-only health check endpoint for session management monitoring.

**Decorators:**
- `@session_health_bp.route('/health')`
- `@login_required`
- `@admin_required`

### health_history

```python
def health_history()
```

Get session health history (if available from monitoring).

**Decorators:**
- `@session_health_bp.route('/history')`
- `@login_required`
- `@admin_required`

### register_session_health_routes

```python
def register_session_health_routes(app)
```

Register session health routes with the Flask app.

