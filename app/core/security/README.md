# Security Module Organization

This directory contains all security-related code for the Vedfolnir project, organized by function and responsibility.

## Directory Structure

### 📁 `core/`
Core security modules that provide fundamental security functionality:

- **`security_config.py`** - Security configuration settings and constants
- **`security_middleware.py`** - Flask security middleware (CSRF, headers, validation)
- **`security_utils.py`** - Security utility functions (sanitization, validation)
- **`security_monitoring.py`** - Security event monitoring and alerting

### 📁 `validation/`
Security validation and automated fixes:

- **`security_validation.py`** - Security validation scripts and checks
- **`security_fixes.py`** - Automated security fixes implementation

### 📁 `logging/`
Security-focused logging and error handling:

- **`secure_logging.py`** - Secure logging utilities with sanitization
- **`secure_error_handlers.py`** - Secure error handling and responses

### 📁 `features/`
Feature-specific security implementations:

- **`caption_security.py`** - Caption generation security (auth, rate limiting, validation)

### 📁 `reports/`
Security audit reports and documentation:

- **`security_audit_report.json`** - Latest security audit results (JSON format)
- **`security_audit_report.md`** - Latest security audit results (Markdown format)

### 📁 `audit/`
Security audit tools and historical reports:

- **`security_auditor.py`** - Security audit implementation
- **`security_audit_report.json`** - Historical audit report

### 📁 `tests/`
Security-specific test files:

- **`test_security_fixes.py`** - Tests for security fixes

### 📄 Root Files
- **`security_audit.py`** - Main security audit tool
- **`security_checklist.md`** - Security implementation checklist
- **`SECURITY.md`** - Security documentation and guidelines

## Import Patterns

### Core Security Utilities
```python
from security.core.security_utils import sanitize_for_log, sanitize_html_input
from security.core.security_config import security_config
from security.core.security_middleware import SecurityMiddleware, validate_csrf_token
```

### Feature-Specific Security
```python
from security.features.caption_security import CaptionSecurityManager
```

### Security Logging
```python
from security.logging.secure_error_handlers import register_secure_error_handlers
from security.logging.secure_logging import SecureLogger
```

### Security Validation
```python
from security.validation.security_validation import SecurityValidator
from security.validation.security_fixes import SecurityFixer
```

## Security Components Overview

### 🛡️ **Core Security (security.core)**
- **Configuration**: Centralized security settings
- **Middleware**: Request/response security processing
- **Utils**: Common security functions (sanitization, validation)
- **Monitoring**: Security event tracking and alerting

### ✅ **Validation (security.validation)**
- **Automated Checks**: Security validation scripts
- **Automated Fixes**: Security issue remediation
- **Compliance**: Security standard compliance checking

### 📝 **Logging (security.logging)**
- **Secure Logging**: Sanitized logging with security context
- **Error Handling**: Secure error responses without information disclosure
- **Audit Trail**: Security event logging and tracking

### 🎯 **Features (security.features)**
- **Caption Security**: Caption generation security controls
- **Future Features**: Additional feature-specific security modules

### 📊 **Audit & Reports (security.audit, security.reports)**
- **Security Auditing**: Comprehensive security assessment tools
- **Report Generation**: Security audit reports and documentation
- **Historical Tracking**: Security posture over time

## Security Standards

This security module implements:

- ✅ **OWASP Top 10 2021** compliance
- ✅ **CWE (Common Weakness Enumeration)** coverage
- ✅ **CSRF Protection** across all forms and APIs
- ✅ **Input Validation** and sanitization
- ✅ **Secure Headers** implementation
- ✅ **Rate Limiting** and abuse protection
- ✅ **Audit Logging** for security events
- ✅ **Error Handling** without information disclosure

## Usage Guidelines

1. **Import from specific modules**: Use specific imports rather than wildcard imports
2. **Follow security patterns**: Use established security utilities and patterns
3. **Validate all inputs**: Use security utilities for input validation and sanitization
4. **Log security events**: Use secure logging for security-related events
5. **Test security features**: Include security tests for new functionality

## Migration Notes

This directory structure was created by reorganizing security files from the root directory:

- **Before**: 12 security files scattered in root directory
- **After**: Organized into 6 functional subdirectories
- **Benefits**: Better organization, easier maintenance, clearer separation of concerns

All import statements have been updated to reflect the new structure. The reorganization maintains full backward compatibility while improving code organization.