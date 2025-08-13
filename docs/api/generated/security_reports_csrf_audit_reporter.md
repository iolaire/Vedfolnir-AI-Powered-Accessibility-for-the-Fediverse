# security.reports.csrf_audit_reporter

CSRF Security Audit Reporter

Generates comprehensive reports for CSRF security audits, including
compliance tracking, vulnerability analysis, and remediation guidance.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/reports/csrf_audit_reporter.py`

## Classes

### ComplianceReport

```python
class ComplianceReport
```

CSRF compliance report data

**Decorators:**
- `@dataclass`

### CSRFAuditReporter

```python
class CSRFAuditReporter
```

Generates comprehensive CSRF security audit reports

**Methods:**

#### __init__

```python
def __init__(self, reports_dir: str)
```

Initialize the CSRF audit reporter

Args:
    reports_dir: Directory to store generated reports

**Type:** Instance method

#### generate_comprehensive_report

```python
def generate_comprehensive_report(self, scan_results_file: str) -> Dict[str, Any]
```

Generate a comprehensive CSRF security audit report

Args:
    scan_results_file: Path to scan results JSON file
    
Returns:
    Comprehensive report dictionary

**Type:** Instance method

#### _generate_executive_summary

```python
def _generate_executive_summary(self, summary: Dict[str, Any], detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Generate executive summary section

**Type:** Instance method

#### _generate_compliance_analysis

```python
def _generate_compliance_analysis(self, summary: Dict[str, Any], detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Generate compliance analysis section

**Type:** Instance method

#### _generate_vulnerability_analysis

```python
def _generate_vulnerability_analysis(self, summary: Dict[str, Any], detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Generate vulnerability analysis section

**Type:** Instance method

#### _generate_template_analysis

```python
def _generate_template_analysis(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Generate template-specific analysis

**Type:** Instance method

#### _generate_remediation_plan

```python
def _generate_remediation_plan(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Generate remediation plan

**Type:** Instance method

#### _generate_security_metrics

```python
def _generate_security_metrics(self, summary: Dict[str, Any], detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Generate security metrics

**Type:** Instance method

#### _generate_recommendations

```python
def _generate_recommendations(self, summary: Dict[str, Any], detailed_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]
```

Generate security recommendations

**Type:** Instance method

#### _generate_appendix

```python
def _generate_appendix(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Generate appendix with detailed data

**Type:** Instance method

#### _generate_markdown_report

```python
def _generate_markdown_report(self, report: Dict[str, Any], output_file: Path) -> None
```

Generate markdown version of the report

**Type:** Instance method

#### _format_report_as_markdown

```python
def _format_report_as_markdown(self, report: Dict[str, Any]) -> str
```

Format report as markdown

**Type:** Instance method

#### _identify_compliance_gaps

```python
def _identify_compliance_gaps(self, detailed_results: List[Dict[str, Any]]) -> List[str]
```

Identify compliance gaps

**Type:** Instance method

#### _analyze_vulnerability_trends

```python
def _analyze_vulnerability_trends(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Analyze vulnerability trends

**Type:** Instance method

#### _prioritize_vulnerabilities

```python
def _prioritize_vulnerabilities(self, vuln_details: Dict[str, Any]) -> List[Dict[str, str]]
```

Prioritize vulnerabilities for remediation

**Type:** Instance method

#### _analyze_forms

```python
def _analyze_forms(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Analyze form usage across templates

**Type:** Instance method

#### _analyze_ajax_usage

```python
def _analyze_ajax_usage(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Analyze AJAX usage across templates

**Type:** Instance method

#### _calculate_priority

```python
def _calculate_priority(self, impact_level: str, effort_level: str) -> int
```

Calculate priority score for remediation tasks

**Type:** Instance method

#### _estimate_total_effort

```python
def _estimate_total_effort(self, remediation_tasks: List[Dict[str, Any]]) -> Dict[str, Any]
```

Estimate total effort for remediation

**Type:** Instance method

#### _generate_implementation_timeline

```python
def _generate_implementation_timeline(self, phases: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]
```

Generate implementation timeline

**Type:** Instance method

#### _generate_vulnerability_reference

```python
def _generate_vulnerability_reference(self) -> Dict[str, Dict[str, str]]
```

Generate vulnerability reference guide

**Type:** Instance method

#### _generate_implementation_guide

```python
def _generate_implementation_guide(self) -> Dict[str, str]
```

Generate CSRF implementation guide

**Type:** Instance method

#### _generate_testing_recommendations

```python
def _generate_testing_recommendations(self) -> List[str]
```

Generate testing recommendations

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main function for generating CSRF audit reports

