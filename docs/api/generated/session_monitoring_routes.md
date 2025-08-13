# session_monitoring_routes

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_monitoring_routes.py`

## Functions

### admin_required

```python
def admin_required(f)
```

Decorator to require admin role for access.

### monitoring_status

```python
def monitoring_status()
```

Get current session monitoring status.

**Decorators:**
- `@session_monitoring_bp.route('/status')`
- `@login_required`
- `@admin_required`

### monitoring_summary

```python
def monitoring_summary()
```

Get performance summary.

**Decorators:**
- `@session_monitoring_bp.route('/summary')`
- `@login_required`
- `@admin_required`

### monitoring_alerts

```python
def monitoring_alerts()
```

Check for performance alerts.

**Decorators:**
- `@session_monitoring_bp.route('/alerts')`
- `@login_required`
- `@admin_required`

### monitoring_dashboard

```python
def monitoring_dashboard()
```

Render session monitoring dashboard.

**Decorators:**
- `@session_monitoring_bp.route('/dashboard')`
- `@login_required`
- `@admin_required`

### monitoring_health

```python
def monitoring_health()
```

Admin-only health check endpoint for session monitoring.

**Decorators:**
- `@session_monitoring_bp.route('/health')`
- `@login_required`
- `@admin_required`

### register_session_monitoring_routes

```python
def register_session_monitoring_routes(app)
```

Register session monitoring routes with the Flask app.

