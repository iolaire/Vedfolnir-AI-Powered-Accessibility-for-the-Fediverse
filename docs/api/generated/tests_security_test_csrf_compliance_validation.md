# tests.security.test_csrf_compliance_validation

CSRF Security Compliance Validation Tests

Tests for compliance scoring system, automated security audit reports,
and continuous integration security checks for CSRF compliance.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/security/test_csrf_compliance_validation.py`

## Classes

### TestCSRFComplianceScoring

```python
class TestCSRFComplianceScoring(unittest.TestCase)
```

Test CSRF compliance scoring system

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_compliance_level_classification

```python
def test_compliance_level_classification(self)
```

Test compliance level classification

**Type:** Instance method

#### test_overall_compliance_calculation

```python
def test_overall_compliance_calculation(self)
```

Test overall compliance score calculation

**Type:** Instance method

#### test_compliance_trends_tracking

```python
def test_compliance_trends_tracking(self)
```

Test compliance trends tracking over time

**Type:** Instance method

#### test_compliance_thresholds

```python
def test_compliance_thresholds(self)
```

Test compliance threshold validation

**Type:** Instance method

#### test_risk_assessment

```python
def test_risk_assessment(self)
```

Test security risk assessment

**Type:** Instance method

#### _create_mock_result

```python
def _create_mock_result(self, template_path: str, score: float, issues: list) -> CSRFAuditResult
```

Create mock CSRF audit result for testing

**Type:** Instance method

### TestSecurityAuditReporting

```python
class TestSecurityAuditReporting(unittest.TestCase)
```

Test automated security audit reporting

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test environment

**Type:** Instance method

#### test_generate_compliance_report

```python
def test_generate_compliance_report(self)
```

Test compliance report generation

**Type:** Instance method

#### test_export_report_formats

```python
def test_export_report_formats(self)
```

Test report export in different formats

**Type:** Instance method

#### test_report_scheduling

```python
def test_report_scheduling(self)
```

Test automated report scheduling

**Type:** Instance method

#### test_report_notifications

```python
def test_report_notifications(self)
```

Test report notification system

**Type:** Instance method

#### _create_mock_result

```python
def _create_mock_result(self, template_path: str, score: float, issues: list) -> CSRFAuditResult
```

Create mock CSRF audit result for testing

**Type:** Instance method

### TestContinuousIntegrationValidation

```python
class TestContinuousIntegrationValidation(unittest.TestCase)
```

Test continuous integration security checks

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test environment

**Type:** Instance method

#### test_ci_security_gate

```python
def test_ci_security_gate(self)
```

Test CI security gate validation

**Type:** Instance method

#### test_regression_detection

```python
def test_regression_detection(self)
```

Test security regression detection

**Type:** Instance method

#### test_pull_request_validation

```python
def test_pull_request_validation(self)
```

Test pull request security validation

**Type:** Instance method

#### test_security_metrics_collection

```python
def test_security_metrics_collection(self)
```

Test security metrics collection for CI

**Type:** Instance method

#### test_ci_configuration_validation

```python
def test_ci_configuration_validation(self)
```

Test CI configuration validation

**Type:** Instance method

#### _create_mock_result

```python
def _create_mock_result(self, template_path: str, score: float, issues: list) -> CSRFAuditResult
```

Create mock CSRF audit result for testing

**Type:** Instance method

### TestComplianceIntegration

```python
class TestComplianceIntegration(unittest.TestCase)
```

Integration tests for compliance validation system

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test environment

**Type:** Instance method

#### test_end_to_end_compliance_workflow

```python
def test_end_to_end_compliance_workflow(self)
```

Test complete compliance validation workflow

**Type:** Instance method

#### test_compliance_dashboard_data

```python
def test_compliance_dashboard_data(self)
```

Test compliance dashboard data generation

**Type:** Instance method

#### _create_mock_result

```python
def _create_mock_result(self, template_path: str, score: float, issues: list) -> CSRFAuditResult
```

Create mock CSRF audit result for testing

**Type:** Instance method

