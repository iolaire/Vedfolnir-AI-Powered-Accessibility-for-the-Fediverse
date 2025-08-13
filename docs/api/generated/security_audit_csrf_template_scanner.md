# security.audit.csrf_template_scanner

CSRF Template Scanner

Automated scanner to identify CSRF vulnerabilities across all templates,
detect token exposure, and validate CSRF implementation compliance.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/audit/csrf_template_scanner.py`

## Classes

### TemplateSecurityIssue

```python
class TemplateSecurityIssue
```

Represents a security issue found in a template

**Decorators:**
- `@dataclass`

### CSRFAuditResult

```python
class CSRFAuditResult
```

Results of CSRF template audit

**Decorators:**
- `@dataclass`

### CSRFTemplateScanner

```python
class CSRFTemplateScanner
```

Scanner for CSRF vulnerabilities in templates

**Methods:**

#### __init__

```python
def __init__(self)
```

Initialize CSRF template scanner

**Type:** Instance method

#### scan_template

```python
def scan_template(self, template_path: str) -> CSRFAuditResult
```

Scan a single template for CSRF vulnerabilities

Args:
    template_path: Path to template file
    
Returns:
    CSRFAuditResult with scan results

**Type:** Instance method

#### _analyze_forms

```python
def _analyze_forms(self, content: str, result: CSRFAuditResult)
```

Analyze forms in template content

**Type:** Instance method

#### _analyze_csrf_protection

```python
def _analyze_csrf_protection(self, content: str, result: CSRFAuditResult)
```

Analyze CSRF protection in template

**Type:** Instance method

#### _analyze_token_exposure

```python
def _analyze_token_exposure(self, content: str, result: CSRFAuditResult)
```

Analyze potential CSRF token exposure

**Type:** Instance method

#### _analyze_ajax_requests

```python
def _analyze_ajax_requests(self, content: str, result: CSRFAuditResult)
```

Analyze AJAX requests for CSRF protection

**Type:** Instance method

#### _get_line_number

```python
def _get_line_number(self, content: str, position: int) -> int
```

Get line number for a position in content

**Type:** Instance method

#### _extract_form_content

```python
def _extract_form_content(self, content: str, form_match) -> str
```

Extract the content of a form element

Args:
    content: Full template content
    form_match: Regex match object for form opening tag
    
Returns:
    Content between form opening and closing tags

**Type:** Instance method

#### _form_has_csrf_protection

```python
def _form_has_csrf_protection(self, form_content: str) -> bool
```

Check if a form has CSRF protection

Args:
    form_content: Content within form tags
    
Returns:
    True if form has CSRF protection, False otherwise

**Type:** Instance method

#### _is_secure_csrf_meta_tag

```python
def _is_secure_csrf_meta_tag(self, content: str) -> bool
```

Check if content is a secure CSRF meta tag

Args:
    content: Content to check
    
Returns:
    True if this is a secure CSRF meta tag, False otherwise

**Type:** Instance method

#### calculate_compliance_score

```python
def calculate_compliance_score(self, result: CSRFAuditResult) -> float
```

Calculate CSRF compliance score

Args:
    result: CSRF audit result
    
Returns:
    Compliance score between 0.0 and 1.0

**Type:** Instance method

#### generate_recommendations

```python
def generate_recommendations(self, result: CSRFAuditResult) -> List[str]
```

Generate security recommendations

Args:
    result: CSRF audit result
    
Returns:
    List of recommendations

**Type:** Instance method

#### scan_all_templates

```python
def scan_all_templates(self, templates_dir: str) -> List[CSRFAuditResult]
```

Scan all templates in a directory

Args:
    templates_dir: Path to templates directory
    
Returns:
    List of CSRF audit results

**Type:** Instance method

#### generate_compliance_report

```python
def generate_compliance_report(self, results: List[CSRFAuditResult]) -> Dict
```

Generate comprehensive compliance report

Args:
    results: List of CSRF audit results
    
Returns:
    Compliance report dictionary

**Type:** Instance method

