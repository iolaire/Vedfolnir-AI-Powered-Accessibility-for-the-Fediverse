# session_alert_routes

Session Management Alert Routes

Provides HTTP endpoints for managing session management alerts including
acknowledgment, resolution, and alert rule configuration.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_alert_routes.py`

## Functions

### admin_required

```python
def admin_required(f)
```

Decorator to require admin role for access.

### get_active_alerts

```python
def get_active_alerts()
```

Get active session management alerts.

**Decorators:**
- `@session_alert_bp.route('/active')`
- `@login_required`
- `@admin_required`

### get_alert_summary

```python
def get_alert_summary()
```

Get alert summary statistics.

**Decorators:**
- `@session_alert_bp.route('/summary')`
- `@login_required`
- `@admin_required`

### acknowledge_alert

```python
def acknowledge_alert(alert_id)
```

Acknowledge an alert.

**Decorators:**
- `@session_alert_bp.route('/<alert_id>/acknowledge', methods=['POST'])`
- `@login_required`
- `@admin_required`

### resolve_alert

```python
def resolve_alert(alert_id)
```

Manually resolve an alert.

**Decorators:**
- `@session_alert_bp.route('/<alert_id>/resolve', methods=['POST'])`
- `@login_required`
- `@admin_required`

### get_alert_rules

```python
def get_alert_rules()
```

Get alert rules configuration.

**Decorators:**
- `@session_alert_bp.route('/rules')`
- `@login_required`
- `@admin_required`

### enable_alert_rule

```python
def enable_alert_rule(rule_name)
```

Enable an alert rule.

**Decorators:**
- `@session_alert_bp.route('/rules/<rule_name>/enable', methods=['POST'])`
- `@login_required`
- `@admin_required`

### disable_alert_rule

```python
def disable_alert_rule(rule_name)
```

Disable an alert rule.

**Decorators:**
- `@session_alert_bp.route('/rules/<rule_name>/disable', methods=['POST'])`
- `@login_required`
- `@admin_required`

### update_alert_rule

```python
def update_alert_rule(rule_name)
```

Update an alert rule configuration.

**Decorators:**
- `@session_alert_bp.route('/rules/<rule_name>/update', methods=['PUT'])`
- `@login_required`
- `@admin_required`

### export_alerts

```python
def export_alerts()
```

Export alerts for external analysis.

**Decorators:**
- `@session_alert_bp.route('/export')`
- `@login_required`
- `@admin_required`

### test_alerting

```python
def test_alerting()
```

Test the alerting system by checking for alerts.

**Decorators:**
- `@session_alert_bp.route('/test')`
- `@login_required`
- `@admin_required`

### register_session_alert_routes

```python
def register_session_alert_routes(app)
```

Register session alert routes with the Flask app.

