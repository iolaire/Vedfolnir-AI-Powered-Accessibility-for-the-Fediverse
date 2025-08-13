# security.reporting.audit_dashboard

Security Audit Dashboard

Web interface for security audit reporting, vulnerability tracking,
and compliance monitoring.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/reporting/audit_dashboard.py`

## Functions

### audit_dashboard

```python
def audit_dashboard()
```

Security audit dashboard page

**Decorators:**
- `@audit_dashboard_bp.route('/dashboard')`
- `@login_required`
- `@admin_required`

### generate_audit_report

```python
def generate_audit_report()
```

Generate new comprehensive audit report

**Decorators:**
- `@audit_dashboard_bp.route('/api/generate-report')`
- `@login_required`
- `@admin_required`

### get_vulnerabilities

```python
def get_vulnerabilities()
```

Get vulnerability data

**Decorators:**
- `@audit_dashboard_bp.route('/api/vulnerabilities')`
- `@login_required`
- `@admin_required`

### get_compliance_data

```python
def get_compliance_data()
```

Get compliance data

**Decorators:**
- `@audit_dashboard_bp.route('/api/compliance')`
- `@login_required`
- `@admin_required`

### get_remediation_data

```python
def get_remediation_data()
```

Get remediation progress data

**Decorators:**
- `@audit_dashboard_bp.route('/api/remediation')`
- `@login_required`
- `@admin_required`

### update_vulnerability

```python
def update_vulnerability(vulnerability_id)
```

Update vulnerability status

**Decorators:**
- `@audit_dashboard_bp.route('/api/vulnerability/<vulnerability_id>/update', methods=['POST'])`
- `@login_required`
- `@admin_required`

### track_new_vulnerability

```python
def track_new_vulnerability()
```

Track a new vulnerability

**Decorators:**
- `@audit_dashboard_bp.route('/api/vulnerability/track', methods=['POST'])`
- `@login_required`
- `@admin_required`

### register_audit_dashboard

```python
def register_audit_dashboard(app)
```

Register audit dashboard with Flask app

