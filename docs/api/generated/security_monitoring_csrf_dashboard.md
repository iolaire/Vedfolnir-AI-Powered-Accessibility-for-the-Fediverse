# security.monitoring.csrf_dashboard

CSRF Security Dashboard

Web interface for monitoring CSRF security metrics, violations, and compliance.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/monitoring/csrf_dashboard.py`

## Functions

### csrf_dashboard

```python
def csrf_dashboard()
```

CSRF security dashboard page

**Decorators:**
- `@csrf_dashboard_bp.route('/dashboard')`
- `@login_required`
- `@admin_required`

### csrf_metrics_api

```python
def csrf_metrics_api()
```

API endpoint for CSRF metrics data

**Decorators:**
- `@csrf_dashboard_bp.route('/api/metrics')`
- `@login_required`
- `@admin_required`

### csrf_violations_api

```python
def csrf_violations_api()
```

API endpoint for recent CSRF violations

**Decorators:**
- `@csrf_dashboard_bp.route('/api/violations')`
- `@login_required`
- `@admin_required`

### csrf_alerts_api

```python
def csrf_alerts_api()
```

API endpoint for CSRF security alerts

**Decorators:**
- `@csrf_dashboard_bp.route('/api/alerts')`
- `@login_required`
- `@admin_required`

### register_csrf_dashboard

```python
def register_csrf_dashboard(app)
```

Register CSRF dashboard with Flask app

Args:
    app: Flask application instance

