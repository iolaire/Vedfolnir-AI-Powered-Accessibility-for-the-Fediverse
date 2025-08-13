# security.reporting.security_audit_system

Security Audit Reporting System

Comprehensive security audit reporting with vulnerability tracking,
remediation status monitoring, and compliance dashboard.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/reporting/security_audit_system.py`

## Classes

### VulnerabilityStatus

```python
class VulnerabilityStatus(Enum)
```

Vulnerability remediation status

**Class Variables:**
- `OPEN`
- `IN_PROGRESS`
- `RESOLVED`
- `ACCEPTED_RISK`
- `FALSE_POSITIVE`

### AuditType

```python
class AuditType(Enum)
```

Types of security audits

**Class Variables:**
- `CSRF_COMPLIANCE`
- `TEMPLATE_SECURITY`
- `COMPREHENSIVE`
- `VULNERABILITY_SCAN`

### VulnerabilityRecord

```python
class VulnerabilityRecord
```

Vulnerability tracking record

**Decorators:**
- `@dataclass`

### AuditReport

```python
class AuditReport
```

Security audit report

**Decorators:**
- `@dataclass`

### SecurityAuditSystem

```python
class SecurityAuditSystem
```

Comprehensive security audit reporting system

**Methods:**

#### __init__

```python
def __init__(self, reports_dir: str)
```

Initialize security audit system

**Type:** Instance method

#### generate_comprehensive_audit_report

```python
def generate_comprehensive_audit_report(self, scope: str) -> AuditReport
```

Generate comprehensive security audit report

**Type:** Instance method

#### track_vulnerability

```python
def track_vulnerability(self, vulnerability_type: str, severity: str, description: str, affected_component: str, assigned_to: str) -> str
```

Track a new vulnerability

**Type:** Instance method

#### update_vulnerability_status

```python
def update_vulnerability_status(self, vulnerability_id: str, status: VulnerabilityStatus, resolution_notes: str, assigned_to: str) -> bool
```

Update vulnerability status

**Type:** Instance method

#### get_vulnerability_dashboard_data

```python
def get_vulnerability_dashboard_data(self) -> Dict[str, Any]
```

Get vulnerability dashboard data

**Type:** Instance method

#### get_compliance_dashboard_data

```python
def get_compliance_dashboard_data(self) -> Dict[str, Any]
```

Get compliance dashboard data

**Type:** Instance method

#### generate_remediation_report

```python
def generate_remediation_report(self) -> Dict[str, Any]
```

Generate remediation progress report

**Type:** Instance method

#### _collect_csrf_metrics

```python
def _collect_csrf_metrics(self) -> Dict[str, Any]
```

Collect CSRF security metrics

**Type:** Instance method

#### _collect_template_security_data

```python
def _collect_template_security_data(self) -> Dict[str, Any]
```

Collect template security data

**Type:** Instance method

#### _collect_vulnerability_status

```python
def _collect_vulnerability_status(self) -> Dict[str, Any]
```

Collect vulnerability status data

**Type:** Instance method

#### _collect_compliance_metrics

```python
def _collect_compliance_metrics(self) -> Dict[str, Any]
```

Collect compliance metrics

**Type:** Instance method

#### _collect_remediation_progress

```python
def _collect_remediation_progress(self) -> Dict[str, Any]
```

Collect remediation progress data

**Type:** Instance method

#### _calculate_overall_security_score

```python
def _calculate_overall_security_score(self, audit_data: Dict[str, Any]) -> float
```

Calculate overall security score

**Type:** Instance method

#### _determine_risk_level

```python
def _determine_risk_level(self, audit_data: Dict[str, Any]) -> str
```

Determine overall risk level

**Type:** Instance method

#### _calculate_compliance_rate

```python
def _calculate_compliance_rate(self, audit_data: Dict[str, Any]) -> float
```

Calculate overall compliance rate

**Type:** Instance method

#### _generate_security_recommendations

```python
def _generate_security_recommendations(self, audit_data: Dict[str, Any]) -> List[str]
```

Generate security recommendations

**Type:** Instance method

#### _calculate_due_date

```python
def _calculate_due_date(self, severity: str) -> datetime
```

Calculate due date based on severity

**Type:** Instance method

#### _save_audit_report

```python
def _save_audit_report(self, report: AuditReport)
```

Save audit report to file

**Type:** Instance method

#### _load_vulnerability_database

```python
def _load_vulnerability_database(self)
```

Load vulnerability database from file

**Type:** Instance method

#### _save_vulnerability_database

```python
def _save_vulnerability_database(self)
```

Save vulnerability database to file

**Type:** Instance method

#### _load_audit_history

```python
def _load_audit_history(self)
```

Load audit history from files

**Type:** Instance method

## Functions

### get_security_audit_system

```python
def get_security_audit_system() -> SecurityAuditSystem
```

Get the global security audit system instance

