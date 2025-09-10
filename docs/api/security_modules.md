# Security Modules API Documentation

This document provides comprehensive API documentation for Vedfolnir's security modules, including function signatures, parameters, return types, and usage examples.

## Table of Contents

- [Security Utils (security/core/security_utils.py)](#security-utils)
- [Security Middleware (security/core/security_middleware.py)](#security-middleware)
- [Session Security (security/features/session_security.py)](#session-security)
- [Security Configuration](#security-configuration)
- [Security Best Practices](#security-best-practices)

---

## Security Utils

### Core Functions

#### sanitize_for_log

```python
def sanitize_for_log(value: Any) -> str
```

Sanitize a value for safe logging to prevent log injection attacks.

**Parameters:**
- `value` (Any): The value to sanitize (will be converted to string)

**Returns:**
- `str`: Sanitized string safe for logging

**Features:**
- Removes newlines and carriage returns
- Replaces control characters with spaces
- Limits length to prevent log flooding (200 chars max)
- Handles None values gracefully

**Example:**
```python
from app.core.security.core.security_utils import sanitize_for_log

# Safe logging of user input
user_input = "malicious\nlog\rinjection\x00attempt"
logger.info(f"User input: {sanitize_for_log(user_input)}")
# Output: "User input: malicious log injection attempt"

# Handle None values
logger.info(f"Value: {sanitize_for_log(None)}")
# Output: "Value: None"
```

#### sanitize_filename

```python
def sanitize_filename(filename: str) -> str
```

Sanitize a filename to prevent directory traversal and file system attacks.

**Parameters:**
- `filename` (str): The filename to sanitize

**Returns:**
- `str`: Sanitized filename safe for file system operations

**Features:**
- Removes directory traversal attempts (`..`, `/`, `\`)
- Removes dangerous characters (`<>:"|?*`)
- Prevents hidden files (starting with `.`)
- Limits length to 255 characters
- Preserves file extensions when truncating

**Example:**
```python
from app.core.security.core.security_utils import sanitize_filename

# Prevent directory traversal
dangerous_name = "../../../etc/passwd"
safe_name = sanitize_filename(dangerous_name)
# Output: "___etc_passwd"

# Handle long filenames
long_name = "a" * 300 + ".txt"
safe_name = sanitize_filename(long_name)
# Output: "aaa...aaa.txt" (truncated to 255 chars)
```

#### validate_url

```python
def validate_url(url: str) -> bool
```

Validate that a URL is safe and well-formed.

**Parameters:**
- `url` (str): The URL to validate

**Returns:**
- `bool`: True if URL is valid and safe, False otherwise

**Features:**
- Validates URL format
- Checks for allowed schemes (http, https)
- Prevents local network access
- Validates domain format

**Example:**
```python
from app.core.security.core.security_utils import validate_url

# Valid URLs
assert validate_url("https://example.com/path") == True
assert validate_url("http://api.service.com/endpoint") == True

# Invalid URLs
assert validate_url("javascript:alert('xss')") == False
assert validate_url("file:///etc/passwd") == False
assert validate_url("http://localhost/admin") == False
```

#### sanitize_html_input

```python
def sanitize_html_input(html_input: str, allowed_tags: List[str] = None) -> str
```

Sanitize HTML input to prevent XSS attacks.

**Parameters:**
- `html_input` (str): HTML content to sanitize
- `allowed_tags` (List[str], optional): List of allowed HTML tags

**Returns:**
- `str`: Sanitized HTML content

**Example:**
```python
from app.core.security.core.security_utils import sanitize_html_input

# Remove dangerous scripts
dangerous_html = '<script>alert("xss")</script><p>Safe content</p>'
safe_html = sanitize_html_input(dangerous_html, allowed_tags=['p'])
# Output: '<p>Safe content</p>'
```

#### generate_secure_token

```python
def generate_secure_token(length: int = 32) -> str
```

Generate a cryptographically secure random token.

**Parameters:**
- `length` (int, optional): Token length in bytes. Defaults to 32.

**Returns:**
- `str`: URL-safe base64 encoded token

**Example:**
```python
from app.core.security.core.security_utils import generate_secure_token

# Generate session token
session_token = generate_secure_token(32)
# Output: "dGhpcyBpcyBhIHNlY3VyZSB0b2tlbg"

# Generate CSRF token
csrf_token = generate_secure_token(16)
```

---

## Security Middleware

### Class: SecurityMiddleware

Comprehensive security middleware for Flask applications implementing multiple protection layers.

#### Constructor

```python
def __init__(self, app=None)
```

**Parameters:**
- `app` (Flask, optional): Flask application instance

#### Core Methods

##### init_app

```python
def init_app(self, app: Flask) -> None
```

Initialize security middleware with Flask app.

**Parameters:**
- `app` (Flask): Flask application instance

**Features:**
- Registers before_request and after_request handlers
- Generates CSP nonces for each request
- Sets up security event logging

##### before_request

```python
def before_request(self) -> Optional[Response]
```

Security checks performed before each request.

**Returns:**
- `Optional[Response]`: Error response if security check fails, None otherwise

**Security Checks:**
- Rate limiting per IP address
- Input validation for request data
- Suspicious pattern detection
- CSRF token validation
- Request size limits

##### after_request

```python
def after_request(self, response: Response) -> Response
```

Add security headers and logging after each request.

**Parameters:**
- `response` (Response): Flask response object

**Returns:**
- `Response`: Modified response with security headers

**Security Headers Added:**
- Content Security Policy (CSP)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Strict-Transport-Security
- Referrer-Policy

#### Security Features

##### Rate Limiting

```python
def _check_rate_limit(self) -> bool
```

Check rate limiting for the current request.

**Returns:**
- `bool`: True if request is allowed, False if rate limited

**Configuration:**
- Default: 60 requests per minute per IP
- Configurable via environment variables
- Automatic cleanup of old entries

##### Input Validation

```python
def _validate_request_data(self) -> None
```

Validate request data for security threats.

**Raises:**
- `BadRequest`: If validation fails

**Validations:**
- Request size limits
- Content type validation
- Parameter sanitization
- File upload validation

##### Suspicious Pattern Detection

```python
def _check_suspicious_patterns(self) -> None
```

Check for suspicious patterns in requests.

**Raises:**
- `BadRequest`: If suspicious patterns detected

**Patterns Detected:**
- SQL injection attempts
- XSS attack patterns
- Directory traversal attempts
- Command injection patterns

#### Usage Example

```python
from flask import Flask
from app.core.security.core.security_middleware import SecurityMiddleware

app = Flask(__name__)
security = SecurityMiddleware(app)

# Or initialize later
app = Flask(__name__)
security = SecurityMiddleware()
security.init_app(app)

@app.route('/api/data')
def get_data():
    # Request automatically protected by middleware
    return {'data': 'secure'}
```

### Decorators

#### require_https

```python
def require_https(f: Callable) -> Callable
```

Decorator to require HTTPS for specific routes.

**Parameters:**
- `f` (Callable): Function to decorate

**Returns:**
- `Callable`: Decorated function

**Example:**
```python
from app.core.security.core.security_middleware import require_https

@app.route('/admin')
@require_https
def admin_panel():
    return render_template('admin.html')
```

#### validate_csrf_token

```python
def validate_csrf_token(f: Callable) -> Callable
```

Decorator to validate CSRF tokens for specific routes.

**Parameters:**
- `f` (Callable): Function to decorate

**Returns:**
- `Callable`: Decorated function

**Example:**
```python
from app.core.security.core.security_middleware import validate_csrf_token

@app.route('/api/update', methods=['POST'])
@validate_csrf_token
def update_data():
    # CSRF token automatically validated
    return {'status': 'updated'}
```

#### rate_limit

```python
def rate_limit(requests_per_minute: int = 60, 
               per_user: bool = False) -> Callable
```

Decorator to apply rate limiting to specific routes.

**Parameters:**
- `requests_per_minute` (int): Rate limit threshold. Defaults to 60.
- `per_user` (bool): Apply limit per user instead of per IP. Defaults to False.

**Returns:**
- `Callable`: Decorated function

**Example:**
```python
from app.core.security.core.security_middleware import rate_limit

@app.route('/api/expensive-operation')
@rate_limit(requests_per_minute=10, per_user=True)
def expensive_operation():
    # Limited to 10 requests per minute per user
    return perform_expensive_operation()
```

---

## Session Security

### Class: SessionFingerprint

Data class for session fingerprinting to detect session hijacking attempts.

#### Constructor

```python
@dataclass
class SessionFingerprint:
    user_agent_hash: str
    ip_address_hash: str
    accept_language: str
    accept_encoding: str
    timezone_offset: Optional[int]
    screen_resolution: Optional[str]
    created_at: datetime
```

**Attributes:**
- `user_agent_hash` (str): Hashed user agent string
- `ip_address_hash` (str): Hashed IP address
- `accept_language` (str): Browser language preferences
- `accept_encoding` (str): Browser encoding preferences
- `timezone_offset` (int, optional): Client timezone offset
- `screen_resolution` (str, optional): Client screen resolution
- `created_at` (datetime): Fingerprint creation time

#### Methods

##### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

Convert fingerprint to dictionary for storage.

**Returns:**
- `Dict[str, Any]`: Dictionary representation

##### from_dict

```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> SessionFingerprint
```

Create fingerprint from dictionary.

**Parameters:**
- `data` (Dict[str, Any]): Dictionary data

**Returns:**
- `SessionFingerprint`: Fingerprint instance

### Class: SecurityAuditEvent

Data class for security audit events.

#### Constructor

```python
@dataclass
class SecurityAuditEvent:
    event_id: str
    session_id: str
    user_id: int
    event_type: str
    severity: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    details: Dict[str, Any]
```

### Class: SessionSecurityHardening

Enhanced session security with fingerprinting and suspicious activity detection.

#### Constructor

```python
def __init__(self, db_manager: DatabaseManager, config: SessionConfig = None)
```

**Parameters:**
- `db_manager` (DatabaseManager): Database manager instance
- `config` (SessionConfig, optional): Session configuration

#### Core Methods

##### create_session_fingerprint

```python
def create_session_fingerprint(self, request: Request) -> SessionFingerprint
```

Create a session fingerprint from request data.

**Parameters:**
- `request` (Request): Flask request object

**Returns:**
- `SessionFingerprint`: Generated fingerprint

##### validate_session_fingerprint

```python
def validate_session_fingerprint(self, session_id: str, 
                                current_fingerprint: SessionFingerprint) -> Tuple[bool, List[str]]
```

Validate session fingerprint against stored fingerprint.

**Parameters:**
- `session_id` (str): Session identifier
- `current_fingerprint` (SessionFingerprint): Current request fingerprint

**Returns:**
- `Tuple[bool, List[str]]`: (is_valid, list_of_mismatches)

##### detect_suspicious_activity

```python
def detect_suspicious_activity(self, user_id: int, 
                              session_data: Dict[str, Any]) -> List[SuspiciousActivityType]
```

Detect suspicious session activities.

**Parameters:**
- `user_id` (int): User identifier
- `session_data` (Dict[str, Any]): Session data to analyze

**Returns:**
- `List[SuspiciousActivityType]`: List of detected suspicious activities

##### log_security_audit_event

```python
def log_security_audit_event(self, event: SecurityAuditEvent) -> None
```

Log a security audit event.

**Parameters:**
- `event` (SecurityAuditEvent): Security event to log

#### Usage Example

```python
from app.core.security.features.session_security import SessionSecurityHardening, SessionFingerprint
from app.core.database.core.database_manager import DatabaseManager
from flask import request

db_manager = DatabaseManager(config)
security_hardening = SessionSecurityHardening(db_manager)

# Create fingerprint for new session
fingerprint = security_hardening.create_session_fingerprint(request)

# Validate existing session
is_valid, mismatches = security_hardening.validate_session_fingerprint(
    session_id='session_123',
    current_fingerprint=fingerprint
)

if not is_valid:
    logger.warning(f"Session fingerprint mismatch: {mismatches}")
    # Handle suspicious activity

# Detect suspicious activities
suspicious_activities = security_hardening.detect_suspicious_activity(
    user_id=123,
    session_data={'platform_switches': 5, 'login_locations': ['US', 'RU']}
)

if suspicious_activities:
    logger.warning(f"Suspicious activities detected: {suspicious_activities}")
```

---

## Security Configuration

### Environment Variables

Configure security features via environment variables:

```bash
# Rate Limiting
SECURITY_RATE_LIMIT_ENABLED=true
SECURITY_RATE_LIMIT_REQUESTS_PER_MINUTE=60
SECURITY_RATE_LIMIT_BURST_SIZE=10

# CSRF Protection
SECURITY_CSRF_ENABLED=true
SECURITY_CSRF_TIME_LIMIT=3600

# Session Security
SECURITY_SESSION_FINGERPRINTING=true
SECURITY_SESSION_TIMEOUT=7200
SECURITY_SESSION_REGENERATE_ON_LOGIN=true

# Content Security Policy
SECURITY_CSP_ENABLED=true
SECURITY_CSP_REPORT_URI=/security/csp-report

# HTTPS Enforcement
SECURITY_FORCE_HTTPS=true
SECURITY_HSTS_MAX_AGE=31536000

# Input Validation
SECURITY_MAX_REQUEST_SIZE=16777216  # 16MB
SECURITY_MAX_FORM_FIELDS=100
SECURITY_MAX_FORM_FIELD_SIZE=1048576  # 1MB
```

### Security Headers Configuration

```python
SECURITY_HEADERS = {
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'nonce-{nonce}'; style-src 'self' 'unsafe-inline'",
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Referrer-Policy': 'strict-origin-when-cross-origin'
}
```

---

## Security Best Practices

### Input Validation

Always validate and sanitize user input:

```python
from app.core.security.core.security_utils import sanitize_html_input, sanitize_for_log

@app.route('/api/comment', methods=['POST'])
def create_comment():
    content = request.json.get('content', '')
    
    # Sanitize HTML content
    safe_content = sanitize_html_input(content, allowed_tags=['p', 'br', 'strong', 'em'])
    
    # Log safely
    logger.info(f"Comment created: {sanitize_for_log(safe_content[:50])}")
    
    return {'status': 'created'}
```

### Session Management

Implement secure session handling:

```python
from app.core.security.features.session_security import SessionSecurityHardening

@app.before_request
def check_session_security():
    if 'user_id' in session:
        # Validate session fingerprint
        fingerprint = security_hardening.create_session_fingerprint(request)
        is_valid, mismatches = security_hardening.validate_session_fingerprint(
            session['session_id'], fingerprint
        )
        
        if not is_valid:
            session.clear()
            abort(401)
```

### Error Handling

Handle security errors gracefully:

```python
@app.errorhandler(429)
def rate_limit_exceeded(error):
    logger.warning(f"Rate limit exceeded for IP: {request.remote_addr}")
    return jsonify({'error': 'Rate limit exceeded'}), 429

@app.errorhandler(400)
def bad_request(error):
    logger.warning(f"Bad request from IP: {request.remote_addr}")
    return jsonify({'error': 'Invalid request'}), 400
```

### Logging Security Events

Log security events for monitoring:

```python
from app.core.security.monitoring.security_monitoring import log_security_event, SecurityEventType

def log_login_attempt(user_id: int, success: bool):
    log_security_event(
        event_type=SecurityEventType.LOGIN_ATTEMPT,
        user_id=user_id,
        details={
            'success': success,
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string
        }
    )
```

---

## Testing Security Features

### Unit Tests

```python
import unittest
from app.core.security.core.security_utils import sanitize_for_log, sanitize_filename

class TestSecurityUtils(unittest.TestCase):
    def test_sanitize_for_log(self):
        # Test log injection prevention
        malicious_input = "user\nINFO: Fake log entry"
        sanitized = sanitize_for_log(malicious_input)
        self.assertNotIn('\n', sanitized)
        
    def test_sanitize_filename(self):
        # Test directory traversal prevention
        malicious_filename = "../../../etc/passwd"
        sanitized = sanitize_filename(malicious_filename)
        self.assertNotIn('..', sanitized)
        self.assertNotIn('/', sanitized)
```

### Integration Tests

```python
def test_security_middleware():
    with app.test_client() as client:
        # Test rate limiting
        for _ in range(70):  # Exceed rate limit
            response = client.get('/api/test')
        
        assert response.status_code == 429
        
        # Test CSRF protection
        response = client.post('/api/update', json={'data': 'test'})
        assert response.status_code == 400  # Missing CSRF token
```

---

This documentation provides a comprehensive reference for Vedfolnir's security modules. The security system implements defense-in-depth with multiple layers of protection including input validation, rate limiting, session security, and comprehensive audit logging.