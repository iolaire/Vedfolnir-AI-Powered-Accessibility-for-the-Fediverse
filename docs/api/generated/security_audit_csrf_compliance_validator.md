# security.audit.csrf_compliance_validator

CSRF Compliance Validator

Compliance scoring system, automated security audit reports,
and continuous integration security checks for CSRF compliance.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/audit/csrf_compliance_validator.py`

## Classes

### ComplianceLevel

```python
class ComplianceLevel(Enum)
```

CSRF compliance levels

**Class Variables:**
- `EXCELLENT`
- `GOOD`
- `NEEDS_IMPROVEMENT`
- `POOR`

### ComplianceReport

```python
class ComplianceReport
```

Comprehensive compliance report

**Decorators:**
- `@dataclass`

### CSRFComplianceValidator

```python
class CSRFComplianceValidator
```

Validates CSRF compliance and generates scores

**Methods:**

#### __init__

```python
def __init__(self)
```

Initialize compliance validator

**Type:** Instance method

#### classify_compliance_level

```python
def classify_compliance_level(self, score: float) -> ComplianceLevel
```

Classify compliance level based on score

Args:
    score: Compliance score (0.0 to 1.0)
    
Returns:
    ComplianceLevel enum

**Type:** Instance method

#### calculate_overall_compliance

```python
def calculate_overall_compliance(self, results: List[CSRFAuditResult]) -> float
```

Calculate overall compliance score

Args:
    results: List of CSRF audit results
    
Returns:
    Overall compliance score (0.0 to 1.0)

**Type:** Instance method

#### _calculate_template_weight

```python
def _calculate_template_weight(self, template_path: str) -> float
```

Calculate template weight based on criticality

Args:
    template_path: Path to template
    
Returns:
    Weight factor (higher = more critical)

**Type:** Instance method

#### validate_compliance_thresholds

```python
def validate_compliance_thresholds(self, results: List[CSRFAuditResult], thresholds: Dict[str, Any]) -> Dict[str, Any]
```

Validate compliance against defined thresholds

Args:
    results: List of CSRF audit results
    thresholds: Compliance thresholds configuration
    
Returns:
    Validation result with pass/fail status

**Type:** Instance method

#### analyze_compliance_trends

```python
def analyze_compliance_trends(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]
```

Analyze compliance trends over time

Args:
    historical_data: List of historical compliance data points
    
Returns:
    Trend analysis results

**Type:** Instance method

#### _calculate_slope

```python
def _calculate_slope(self, x_values: List[float], y_values: List[float]) -> float
```

Calculate slope using linear regression

Args:
    x_values: X coordinates
    y_values: Y coordinates
    
Returns:
    Slope value

**Type:** Instance method

#### assess_security_risk

```python
def assess_security_risk(self, results: List[CSRFAuditResult]) -> Dict[str, Any]
```

Assess overall security risk based on audit results

Args:
    results: List of CSRF audit results
    
Returns:
    Risk assessment results

**Type:** Instance method

#### generate_dashboard_data

```python
def generate_dashboard_data(self, results: List[CSRFAuditResult]) -> Dict[str, Any]
```

Generate data for compliance dashboard

Args:
    results: List of CSRF audit results
    
Returns:
    Dashboard data structure

**Type:** Instance method

#### _generate_dashboard_recommendations

```python
def _generate_dashboard_recommendations(self, results: List[CSRFAuditResult], overall_score: float, issue_counts: Dict[str, int]) -> List[str]
```

Generate recommendations for dashboard

Args:
    results: Audit results
    overall_score: Overall compliance score
    issue_counts: Issue counts by severity
    
Returns:
    List of recommendations

**Type:** Instance method

### SecurityAuditReporter

```python
class SecurityAuditReporter
```

Generates automated security audit reports

**Methods:**

#### __init__

```python
def __init__(self)
```

Initialize security audit reporter

**Type:** Instance method

#### generate_compliance_report

```python
def generate_compliance_report(self, results: List[CSRFAuditResult]) -> Dict[str, Any]
```

Generate comprehensive compliance report

Args:
    results: List of CSRF audit results
    
Returns:
    Compliance report dictionary

**Type:** Instance method

#### export_report

```python
def export_report(self, report: Dict[str, Any], output_path: str, format: str)
```

Export report in specified format

Args:
    report: Report data
    output_path: Output file path
    format: Export format ('json', 'html', 'csv')

**Type:** Instance method

#### schedule_automated_reports

```python
def schedule_automated_reports(self, frequency: str, output_dir: str, formats: List[str])
```

Schedule automated report generation

Args:
    frequency: Report frequency ('daily', 'weekly', 'monthly')
    output_dir: Output directory for reports
    formats: List of export formats

**Type:** Instance method

#### send_report_notifications

```python
def send_report_notifications(self, report: Dict[str, Any], recipients: List[str])
```

Send report notifications

Args:
    report: Report data
    recipients: List of email recipients

**Type:** Instance method

#### _generate_report_recommendations

```python
def _generate_report_recommendations(self, results: List[CSRFAuditResult], summary: Dict[str, Any], issues_analysis: Dict[str, Any]) -> List[str]
```

Generate recommendations for the report

**Type:** Instance method

#### _generate_html_report

```python
def _generate_html_report(self, report: Dict[str, Any]) -> str
```

Generate HTML report

**Type:** Instance method

#### _get_html_template

```python
def _get_html_template(self) -> str
```

Get HTML report template

**Type:** Instance method

### ContinuousIntegrationValidator

```python
class ContinuousIntegrationValidator
```

Validates CSRF compliance for CI/CD pipelines

**Methods:**

#### __init__

```python
def __init__(self)
```

Initialize CI validator

**Type:** Instance method

#### validate_security_gate

```python
def validate_security_gate(self, results: List[CSRFAuditResult], gate_config: Dict[str, Any]) -> Dict[str, Any]
```

Validate security gate for CI/CD

Args:
    results: CSRF audit results
    gate_config: Gate configuration
    
Returns:
    Gate validation result

**Type:** Instance method

#### detect_security_regression

```python
def detect_security_regression(self, baseline_results: List[CSRFAuditResult], current_results: List[CSRFAuditResult]) -> Dict[str, Any]
```

Detect security regression between baseline and current results

Args:
    baseline_results: Baseline audit results
    current_results: Current audit results
    
Returns:
    Regression detection result

**Type:** Instance method

#### validate_pull_request

```python
def validate_pull_request(self, results: List[CSRFAuditResult], changed_templates: List[str]) -> Dict[str, Any]
```

Validate pull request for CSRF compliance

Args:
    results: CSRF audit results
    changed_templates: List of changed template paths
    
Returns:
    PR validation result

**Type:** Instance method

#### collect_security_metrics

```python
def collect_security_metrics(self, results: List[CSRFAuditResult]) -> Dict[str, Any]
```

Collect security metrics for CI reporting

Args:
    results: CSRF audit results
    
Returns:
    Security metrics

**Type:** Instance method

#### validate_configuration

```python
def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]
```

Validate CI configuration

Args:
    config: CI configuration
    
Returns:
    Validation result

**Type:** Instance method

