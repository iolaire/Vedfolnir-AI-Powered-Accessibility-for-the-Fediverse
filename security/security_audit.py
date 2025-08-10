#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive Security Audit for Web-Integrated Caption Generation

This script performs a thorough security audit of the web-integrated caption generation system,
identifying vulnerabilities and providing detailed remediation recommendations.
"""

import os
import re
import ast
import sys
import json
import logging
from datetime import datetime as dt
from typing import Dict, List, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SeverityLevel(Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"

@dataclass
class SecurityVulnerability:
    """Represents a security vulnerability"""
    id: str
    title: str
    severity: SeverityLevel
    category: str
    description: str
    file_path: str
    line_number: int
    code_snippet: str
    impact: str
    remediation: str
    cwe_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['severity'] = self.severity.value
        return result

class SecurityAuditor:
    """Main security auditor class"""
    
    def __init__(self):
        self.vulnerabilities: List[SecurityVulnerability] = []
        self.files_to_audit = [
            'web_app.py',
            'security_middleware.py',
            'caption_security.py',
            'websocket_progress_handler.py',
            'web_caption_generation_service.py',
            'task_queue_manager.py',
            'progress_tracker.py',
            'platform_aware_caption_adapter.py',
            'error_recovery_manager.py',
            'caption_review_integration.py',
            'admin_monitoring.py',
            'models.py'
        ]
    
    def run_audit(self) -> Dict[str, Any]:
        """Run comprehensive security audit"""
        logger.info("Starting comprehensive security audit...")
        
        # 1. Authentication and Authorization Audit
        self._audit_authentication()
        
        # 2. Input Validation Audit
        self._audit_input_validation()
        
        # 3. CSRF Protection Audit
        self._audit_csrf_protection()
        
        # 4. Security Headers Audit
        self._audit_security_headers()
        
        # 5. WebSocket Security Audit
        self._audit_websocket_security()
        
        # 6. Database Security Audit
        self._audit_database_security()
        
        # 7. File Operations Security Audit
        self._audit_file_operations()
        
        # 8. Session Management Audit
        self._audit_session_management()
        
        # 9. Error Handling Audit
        self._audit_error_handling()
        
        # 10. Logging Security Audit
        self._audit_logging_security()
        
        # Generate report
        return self._generate_report()
    
    def _audit_authentication(self):
        """Audit authentication and authorization mechanisms"""
        logger.info("Auditing authentication and authorization...")
        
        # Check for missing authentication decorators
        self._check_missing_auth_decorators()
        
        # Check for weak password policies
        self._check_password_policies()
        
        # Check for session fixation vulnerabilities
        self._check_session_fixation()
        
        # Check for privilege escalation vulnerabilities
        self._check_privilege_escalation()
    
    def _audit_input_validation(self):
        """Audit input validation across all endpoints"""
        logger.info("Auditing input validation...")
        
        # Check for SQL injection vulnerabilities
        self._check_sql_injection()
        
        # Check for XSS vulnerabilities
        self._check_xss_vulnerabilities()
        
        # Check for path traversal vulnerabilities
        self._check_path_traversal()
        
        # Check for command injection vulnerabilities
        self._check_command_injection()
        
        # Check for deserialization vulnerabilities
        self._check_deserialization()
    
    def _audit_csrf_protection(self):
        """Audit CSRF protection implementation"""
        logger.info("Auditing CSRF protection...")
        
        # Check for missing CSRF tokens
        self._check_missing_csrf_tokens()
        
        # Check for weak CSRF token generation
        self._check_csrf_token_strength()
        
        # Check for CSRF token validation
        self._check_csrf_validation()
    
    def _audit_security_headers(self):
        """Audit security headers implementation"""
        logger.info("Auditing security headers...")
        
        # Check for missing security headers
        self._check_security_headers()
        
        # Check Content Security Policy
        self._check_csp_policy()
        
        # Check HSTS implementation
        self._check_hsts()
    
    def _audit_websocket_security(self):
        """Audit WebSocket security implementation"""
        logger.info("Auditing WebSocket security...")
        
        # Check WebSocket authentication
        self._check_websocket_auth()
        
        # Check WebSocket message validation
        self._check_websocket_validation()
        
        # Check WebSocket rate limiting
        self._check_websocket_rate_limiting()
    
    def _audit_database_security(self):
        """Audit database security"""
        logger.info("Auditing database security...")
        
        # Check for SQL injection in ORM queries
        self._check_orm_sql_injection()
        
        # Check for sensitive data exposure
        self._check_sensitive_data_exposure()
        
        # Check for database connection security
        self._check_database_connections()
    
    def _audit_file_operations(self):
        """Audit file operations security"""
        logger.info("Auditing file operations...")
        
        # Check file upload security
        self._check_file_upload_security()
        
        # Check file download security
        self._check_file_download_security()
        
        # Check file path validation
        self._check_file_path_validation()
    
    def _audit_session_management(self):
        """Audit session management security"""
        logger.info("Auditing session management...")
        
        # Check session configuration
        self._check_session_config()
        
        # Check session timeout
        self._check_session_timeout()
        
        # Check session invalidation
        self._check_session_invalidation()
    
    def _audit_error_handling(self):
        """Audit error handling for information disclosure"""
        logger.info("Auditing error handling...")
        
        # Check for information disclosure in errors
        self._check_error_disclosure()
        
        # Check for debug mode in production
        self._check_debug_mode()
        
        # Check for stack trace exposure
        self._check_stack_trace_exposure()
    
    def _audit_logging_security(self):
        """Audit logging for security issues"""
        logger.info("Auditing logging security...")
        
        # Check for sensitive data in logs
        self._check_sensitive_logging()
        
        # Check for log injection
        self._check_log_injection()
        
        # Check for insufficient logging
        self._check_insufficient_logging()
    
    def _check_missing_auth_decorators(self):
        """Check for routes missing authentication decorators"""
        web_app_path = Path('web_app.py')
        if not web_app_path.exists():
            return
        
        with open(web_app_path, 'r') as f:
            content = f.read()
        
        # Find all route definitions
        route_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"](?:,\s*methods=\[([^\]]+)\])?\)\s*\n(?:@[^\n]+\n)*def\s+(\w+)'
        routes = re.findall(route_pattern, content, re.MULTILINE)
        
        lines = content.split('\n')
        
        for route_path, methods, func_name in routes:
            # Skip static routes and public endpoints
            if route_path.startswith('/static') or func_name in ['login', 'health', 'index']:
                continue
            
            # Find the function definition
            func_pattern = rf'def\s+{func_name}\s*\('
            for i, line in enumerate(lines):
                if re.search(func_pattern, line):
                    # Check preceding lines for auth decorators
                    auth_decorators = ['@login_required', '@role_required', '@platform_required']
                    has_auth = False
                    
                    for j in range(max(0, i-10), i):
                        if any(decorator in lines[j] for decorator in auth_decorators):
                            has_auth = True
                            break
                    
                    if not has_auth and 'POST' in methods:
                        self.vulnerabilities.append(SecurityVulnerability(
                            id=f"AUTH-001-{func_name}",
                            title=f"Missing Authentication on {func_name}",
                            severity=SeverityLevel.HIGH,
                            category="Authentication",
                            description=f"Route {route_path} ({func_name}) accepts POST requests but lacks authentication decorators",
                            file_path="web_app.py",
                            line_number=i+1,
                            code_snippet=line.strip(),
                            impact="Unauthorized users could access protected functionality",
                            remediation="Add @login_required or appropriate authentication decorator",
                            cwe_id="CWE-306"
                        ))
                    break
    
    def _check_password_policies(self):
        """Check for weak password policies"""
        # Check User model for password validation
        models_path = Path('models.py')
        if models_path.exists():
            with open(models_path, 'r') as f:
                content = f.read()
            
            # Look for password validation
            if 'password' in content.lower() and 'length' not in content.lower():
                self.vulnerabilities.append(SecurityVulnerability(
                    id="PWD-001",
                    title="Weak Password Policy",
                    severity=SeverityLevel.MEDIUM,
                    category="Authentication",
                    description="No password length validation found",
                    file_path="models.py",
                    line_number=1,
                    code_snippet="",
                    impact="Users could set weak passwords",
                    remediation="Implement password complexity requirements",
                    cwe_id="CWE-521"
                ))
    
    def _check_session_fixation(self):
        """Check for session fixation vulnerabilities"""
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            # Check if session is regenerated on login
            if 'login_user' in content and 'session.regenerate' not in content:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="SESS-001",
                    title="Potential Session Fixation",
                    severity=SeverityLevel.MEDIUM,
                    category="Session Management",
                    description="Session ID may not be regenerated on login",
                    file_path="web_app.py",
                    line_number=1,
                    code_snippet="",
                    impact="Attackers could hijack user sessions",
                    remediation="Regenerate session ID on successful login",
                    cwe_id="CWE-384"
                ))
    
    def _check_privilege_escalation(self):
        """Check for privilege escalation vulnerabilities"""
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for role assignments without proper validation
            for i, line in enumerate(lines):
                if 'role' in line.lower() and ('=' in line or 'update' in line.lower()):
                    if 'current_user' not in line and 'admin' not in line.lower():
                        self.vulnerabilities.append(SecurityVulnerability(
                            id=f"PRIV-001-{i}",
                            title="Potential Privilege Escalation",
                            severity=SeverityLevel.HIGH,
                            category="Authorization",
                            description="Role assignment without proper authorization check",
                            file_path="web_app.py",
                            line_number=i+1,
                            code_snippet=line.strip(),
                            impact="Users could escalate their privileges",
                            remediation="Add proper authorization checks before role changes",
                            cwe_id="CWE-269"
                        ))
    
    def _check_path_traversal(self):
        """Check for path traversal vulnerabilities"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for file operations with user input
            for i, line in enumerate(lines):
                if any(func in line for func in ['open(', 'send_file(', 'send_from_directory(']):
                    if any(var in line for var in ['request.', 'form.', 'args.', 'json.']):
                        self.vulnerabilities.append(SecurityVulnerability(
                            id=f"PATH-001-{file_path}-{i}",
                            title="Potential Path Traversal",
                            severity=SeverityLevel.HIGH,
                            category="Path Traversal",
                            description="File operation with user input without validation",
                            file_path=file_path,
                            line_number=i+1,
                            code_snippet=line.strip(),
                            impact="Attackers could access arbitrary files",
                            remediation="Validate and sanitize file paths",
                            cwe_id="CWE-22"
                        ))
    
    def _check_command_injection(self):
        """Check for command injection vulnerabilities"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for command execution with user input
            dangerous_functions = ['os.system', 'subprocess.call', 'subprocess.run', 'os.popen']
            
            for i, line in enumerate(lines):
                for func in dangerous_functions:
                    if func in line and any(var in line for var in ['request.', 'form.', 'args.']):
                        self.vulnerabilities.append(SecurityVulnerability(
                            id=f"CMD-001-{file_path}-{i}",
                            title="Potential Command Injection",
                            severity=SeverityLevel.CRITICAL,
                            category="Injection",
                            description="Command execution with user input",
                            file_path=file_path,
                            line_number=i+1,
                            code_snippet=line.strip(),
                            impact="Attackers could execute arbitrary commands",
                            remediation="Use safe alternatives or validate input",
                            cwe_id="CWE-78"
                        ))
    
    def _check_deserialization(self):
        """Check for unsafe deserialization"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for pickle or eval usage
            dangerous_functions = ['pickle.loads', 'pickle.load', 'eval(', 'exec(']
            
            for i, line in enumerate(lines):
                for func in dangerous_functions:
                    if func in line:
                        self.vulnerabilities.append(SecurityVulnerability(
                            id=f"DESER-001-{file_path}-{i}",
                            title="Unsafe Deserialization",
                            severity=SeverityLevel.HIGH,
                            category="Deserialization",
                            description="Unsafe deserialization function detected",
                            file_path=file_path,
                            line_number=i+1,
                            code_snippet=line.strip(),
                            impact="Code execution through malicious payloads",
                            remediation="Use safe serialization formats like JSON",
                            cwe_id="CWE-502"
                        ))
    
    def _check_csrf_token_strength(self):
        """Check CSRF token generation strength"""
        security_middleware_path = Path('security_middleware.py')
        if security_middleware_path.exists():
            with open(security_middleware_path, 'r') as f:
                content = f.read()
            
            # Check for weak token generation
            if 'csrf' in content.lower() and 'secrets.' not in content:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="CSRF-002",
                    title="Weak CSRF Token Generation",
                    severity=SeverityLevel.MEDIUM,
                    category="CSRF",
                    description="CSRF tokens may not use cryptographically secure generation",
                    file_path="security_middleware.py",
                    line_number=1,
                    code_snippet="",
                    impact="CSRF tokens could be predictable",
                    remediation="Use secrets module for token generation",
                    cwe_id="CWE-330"
                ))
    
    def _check_csrf_validation(self):
        """Check CSRF token validation implementation"""
        security_middleware_path = Path('security_middleware.py')
        if security_middleware_path.exists():
            with open(security_middleware_path, 'r') as f:
                content = f.read()
            
            # Check for proper CSRF validation
            if 'validate_csrf_token' in content and 'session' not in content:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="CSRF-003",
                    title="Incomplete CSRF Validation",
                    severity=SeverityLevel.HIGH,
                    category="CSRF",
                    description="CSRF validation may not check against session token",
                    file_path="security_middleware.py",
                    line_number=1,
                    code_snippet="",
                    impact="CSRF protection could be bypassed",
                    remediation="Implement proper session-based CSRF validation",
                    cwe_id="CWE-352"
                ))
    
    def _check_csp_policy(self):
        """Check Content Security Policy implementation"""
        security_middleware_path = Path('security_middleware.py')
        if security_middleware_path.exists():
            with open(security_middleware_path, 'r') as f:
                content = f.read()
            
            # Check for unsafe CSP directives
            if "'unsafe-inline'" in content or "'unsafe-eval'" in content:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="CSP-001",
                    title="Unsafe CSP Directives",
                    severity=SeverityLevel.MEDIUM,
                    category="Security Headers",
                    description="CSP contains unsafe-inline or unsafe-eval directives",
                    file_path="security_middleware.py",
                    line_number=1,
                    code_snippet="",
                    impact="Reduced XSS protection",
                    remediation="Remove unsafe CSP directives and use nonces",
                    cwe_id="CWE-79"
                ))
    
    def _check_hsts(self):
        """Check HSTS implementation"""
        security_middleware_path = Path('security_middleware.py')
        if security_middleware_path.exists():
            with open(security_middleware_path, 'r') as f:
                content = f.read()
            
            # Check for HSTS header
            if 'Strict-Transport-Security' not in content:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="HSTS-001",
                    title="Missing HSTS Header",
                    severity=SeverityLevel.MEDIUM,
                    category="Security Headers",
                    description="HSTS header not implemented",
                    file_path="security_middleware.py",
                    line_number=1,
                    code_snippet="",
                    impact="Vulnerable to protocol downgrade attacks",
                    remediation="Implement HSTS header for HTTPS connections",
                    cwe_id="CWE-319"
                ))
    
    def _check_websocket_validation(self):
        """Check WebSocket message validation"""
        websocket_path = Path('websocket_progress_handler.py')
        if websocket_path.exists():
            with open(websocket_path, 'r') as f:
                content = f.read()
            
            # Check for input validation in WebSocket handlers
            if '@socketio.on(' in content and 'validate' not in content:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="WS-002",
                    title="Missing WebSocket Input Validation",
                    severity=SeverityLevel.MEDIUM,
                    category="WebSocket Security",
                    description="WebSocket message handlers may lack input validation",
                    file_path="websocket_progress_handler.py",
                    line_number=1,
                    code_snippet="",
                    impact="Malicious WebSocket messages could cause issues",
                    remediation="Add input validation to WebSocket handlers",
                    cwe_id="CWE-20"
                ))
    
    def _check_websocket_rate_limiting(self):
        """Check WebSocket rate limiting"""
        websocket_path = Path('websocket_progress_handler.py')
        if websocket_path.exists():
            with open(websocket_path, 'r') as f:
                content = f.read()
            
            # Check for rate limiting
            if 'rate_limit' not in content and 'throttle' not in content:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="WS-003",
                    title="Missing WebSocket Rate Limiting",
                    severity=SeverityLevel.LOW,
                    category="WebSocket Security",
                    description="WebSocket connections may lack rate limiting",
                    file_path="websocket_progress_handler.py",
                    line_number=1,
                    code_snippet="",
                    impact="WebSocket flooding attacks possible",
                    remediation="Implement rate limiting for WebSocket messages",
                    cwe_id="CWE-770"
                ))
    
    def _check_orm_sql_injection(self):
        """Check for SQL injection in ORM queries"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for raw SQL in ORM
            for i, line in enumerate(lines):
                if 'text(' in line and any(var in line for var in ['%', '.format', 'f"']):
                    self.vulnerabilities.append(SecurityVulnerability(
                        id=f"ORM-001-{file_path}-{i}",
                        title="SQL Injection in ORM",
                        severity=SeverityLevel.HIGH,
                        category="Injection",
                        description="Raw SQL with string formatting in ORM",
                        file_path=file_path,
                        line_number=i+1,
                        code_snippet=line.strip(),
                        impact="SQL injection through ORM queries",
                        remediation="Use parameterized queries",
                        cwe_id="CWE-89"
                    ))
    
    def _check_database_connections(self):
        """Check database connection security"""
        config_files = ['config.py', 'database.py']
        for file_path in config_files:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for hardcoded credentials
            if any(pattern in content for pattern in ['password=', 'pwd=']):
                if 'os.environ' not in content and 'getenv' not in content:
                    self.vulnerabilities.append(SecurityVulnerability(
                        id=f"DB-001-{file_path}",
                        title="Hardcoded Database Credentials",
                        severity=SeverityLevel.HIGH,
                        category="Configuration",
                        description="Database credentials may be hardcoded",
                        file_path=file_path,
                        line_number=1,
                        code_snippet="",
                        impact="Credentials exposed in source code",
                        remediation="Use environment variables for credentials",
                        cwe_id="CWE-798"
                    ))
    
    def _check_file_upload_security(self):
        """Check file upload security"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for file upload handling
            for i, line in enumerate(lines):
                if 'request.files' in line:
                    # Check for file type validation
                    context_lines = lines[max(0, i-5):i+5]
                    context = '\n'.join(context_lines)
                    
                    if 'allowed_extensions' not in context and 'content_type' not in context:
                        self.vulnerabilities.append(SecurityVulnerability(
                            id=f"FILE-001-{file_path}-{i}",
                            title="Unrestricted File Upload",
                            severity=SeverityLevel.HIGH,
                            category="File Upload",
                            description="File upload without type validation",
                            file_path=file_path,
                            line_number=i+1,
                            code_snippet=line.strip(),
                            impact="Malicious files could be uploaded",
                            remediation="Implement file type and size validation",
                            cwe_id="CWE-434"
                        ))
    
    def _check_file_download_security(self):
        """Check file download security"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for file download endpoints
            for i, line in enumerate(lines):
                if 'send_file' in line or 'send_from_directory' in line:
                    if any(var in line for var in ['request.', 'args.', 'form.']):
                        self.vulnerabilities.append(SecurityVulnerability(
                            id=f"FILE-002-{file_path}-{i}",
                            title="Insecure File Download",
                            severity=SeverityLevel.MEDIUM,
                            category="File Download",
                            description="File download with user input",
                            file_path=file_path,
                            line_number=i+1,
                            code_snippet=line.strip(),
                            impact="Unauthorized file access possible",
                            remediation="Validate file paths and implement access controls",
                            cwe_id="CWE-22"
                        ))
    
    def _check_file_path_validation(self):
        """Check file path validation"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for path operations without validation
            for i, line in enumerate(lines):
                if any(func in line for func in ['os.path.join', 'Path(']):
                    if any(var in line for var in ['request.', 'form.', 'args.']):
                        if 'sanitize' not in line and 'validate' not in line:
                            self.vulnerabilities.append(SecurityVulnerability(
                                id=f"PATH-002-{file_path}-{i}",
                                title="Unvalidated Path Construction",
                                severity=SeverityLevel.MEDIUM,
                                category="Path Validation",
                                description="Path construction with user input without validation",
                                file_path=file_path,
                                line_number=i+1,
                                code_snippet=line.strip(),
                                impact="Path traversal attacks possible",
                                remediation="Validate and sanitize path components",
                                cwe_id="CWE-22"
                            ))
    
    def _check_session_config(self):
        """Check session configuration"""
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            # Check for secure session configuration
            session_issues = []
            
            if 'SESSION_COOKIE_SECURE' not in content:
                session_issues.append("SESSION_COOKIE_SECURE not set")
            
            if 'SESSION_COOKIE_HTTPONLY' not in content:
                session_issues.append("SESSION_COOKIE_HTTPONLY not set")
            
            if 'SESSION_COOKIE_SAMESITE' not in content:
                session_issues.append("SESSION_COOKIE_SAMESITE not set")
            
            if session_issues:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="SESS-002",
                    title="Insecure Session Configuration",
                    severity=SeverityLevel.MEDIUM,
                    category="Session Management",
                    description=f"Session security issues: {', '.join(session_issues)}",
                    file_path="web_app.py",
                    line_number=1,
                    code_snippet="",
                    impact="Session cookies vulnerable to attacks",
                    remediation="Configure secure session cookie settings",
                    cwe_id="CWE-614"
                ))
    
    def _check_session_timeout(self):
        """Check session timeout configuration"""
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            # Check for session timeout
            if 'PERMANENT_SESSION_LIFETIME' not in content:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="SESS-003",
                    title="Missing Session Timeout",
                    severity=SeverityLevel.LOW,
                    category="Session Management",
                    description="Session timeout not configured",
                    file_path="web_app.py",
                    line_number=1,
                    code_snippet="",
                    impact="Sessions could remain active indefinitely",
                    remediation="Configure appropriate session timeout",
                    cwe_id="CWE-613"
                ))
    
    def _check_session_invalidation(self):
        """Check session invalidation on logout"""
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            # Check for proper session cleanup on logout
            if 'logout' in content and 'session.clear' not in content:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="SESS-004",
                    title="Incomplete Session Invalidation",
                    severity=SeverityLevel.MEDIUM,
                    category="Session Management",
                    description="Session may not be properly cleared on logout",
                    file_path="web_app.py",
                    line_number=1,
                    code_snippet="",
                    impact="Session data could persist after logout",
                    remediation="Clear session data on logout",
                    cwe_id="CWE-613"
                ))
    
    def _check_error_disclosure(self):
        """Check for information disclosure in error messages"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for detailed error messages
            for i, line in enumerate(lines):
                if any(pattern in line for pattern in ['str(e)', 'exception', 'traceback']):
                    if 'flash(' in line or 'return' in line:
                        self.vulnerabilities.append(SecurityVulnerability(
                            id=f"ERR-001-{file_path}-{i}",
                            title="Information Disclosure in Errors",
                            severity=SeverityLevel.LOW,
                            category="Information Disclosure",
                            description="Detailed error information may be exposed",
                            file_path=file_path,
                            line_number=i+1,
                            code_snippet=line.strip(),
                            impact="System information could be leaked",
                            remediation="Use generic error messages for users",
                            cwe_id="CWE-209"
                        ))
    
    def _check_stack_trace_exposure(self):
        """Check for stack trace exposure"""
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            # Check for debug mode or stack trace exposure
            if 'traceback' in content and 'debug' in content:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="ERR-002",
                    title="Stack Trace Exposure Risk",
                    severity=SeverityLevel.MEDIUM,
                    category="Information Disclosure",
                    description="Stack traces may be exposed in debug mode",
                    file_path="web_app.py",
                    line_number=1,
                    code_snippet="",
                    impact="Internal application structure exposed",
                    remediation="Disable debug mode and handle exceptions properly",
                    cwe_id="CWE-209"
                ))
    
    def _check_sensitive_logging(self):
        """Check for sensitive data in logs"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for logging of sensitive data
            for i, line in enumerate(lines):
                if any(log_func in line for log_func in ['logger.', 'logging.', 'print(']):
                    if any(sensitive in line.lower() for sensitive in ['password', 'token', 'secret', 'key']):
                        if 'sanitize' not in line:
                            self.vulnerabilities.append(SecurityVulnerability(
                                id=f"LOG-001-{file_path}-{i}",
                                title="Sensitive Data in Logs",
                                severity=SeverityLevel.MEDIUM,
                                category="Logging",
                                description="Sensitive data may be logged",
                                file_path=file_path,
                                line_number=i+1,
                                code_snippet=line.strip(),
                                impact="Sensitive information exposed in logs",
                                remediation="Sanitize sensitive data before logging",
                                cwe_id="CWE-532"
                            ))
    
    def _check_log_injection(self):
        """Check for log injection vulnerabilities"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for user input in log messages
            for i, line in enumerate(lines):
                if any(log_func in line for log_func in ['logger.', 'logging.']):
                    if any(user_input in line for user_input in ['request.', 'form.', 'args.']):
                        if 'sanitize' not in line:
                            self.vulnerabilities.append(SecurityVulnerability(
                                id=f"LOG-002-{file_path}-{i}",
                                title="Log Injection Vulnerability",
                                severity=SeverityLevel.LOW,
                                category="Logging",
                                description="User input logged without sanitization",
                                file_path=file_path,
                                line_number=i+1,
                                code_snippet=line.strip(),
                                impact="Log files could be manipulated",
                                remediation="Sanitize user input before logging",
                                cwe_id="CWE-117"
                            ))
    
    def _check_insufficient_logging(self):
        """Check for insufficient security logging"""
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            # Check for security event logging
            security_events = ['login', 'logout', 'failed', 'unauthorized', 'admin']
            logged_events = []
            
            for event in security_events:
                if event in content and 'logger' in content:
                    logged_events.append(event)
            
            if len(logged_events) < 3:
                self.vulnerabilities.append(SecurityVulnerability(
                    id="LOG-003",
                    title="Insufficient Security Logging",
                    severity=SeverityLevel.LOW,
                    category="Logging",
                    description="Insufficient logging of security events",
                    file_path="web_app.py",
                    line_number=1,
                    code_snippet="",
                    impact="Security incidents may go undetected",
                    remediation="Implement comprehensive security event logging",
                    cwe_id="CWE-778"
                ))
    
    def _check_missing_csrf_tokens(self):
        """Check for POST routes missing CSRF protection"""
        web_app_path = Path('web_app.py')
        if not web_app_path.exists():
            return
        
        with open(web_app_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Find POST routes
        for i, line in enumerate(lines):
            if '@app.route(' in line and 'POST' in line:
                # Check for CSRF protection in following decorators
                has_csrf = False
                func_start = i
                
                # Look for function definition and check decorators
                for j in range(i, min(len(lines), i+10)):
                    if 'def ' in lines[j]:
                        func_start = j
                        break
                    if '@validate_csrf_token' in lines[j] or 'csrf_token' in lines[j]:
                        has_csrf = True
                        break
                
                if not has_csrf:
                    func_name = ""
                    if func_start < len(lines):
                        func_match = re.search(r'def\s+(\w+)', lines[func_start])
                        if func_match:
                            func_name = func_match.group(1)
                    
                    self.vulnerabilities.append(SecurityVulnerability(
                        id=f"CSRF-001-{func_name}",
                        title=f"Missing CSRF Protection on {func_name}",
                        severity=SeverityLevel.HIGH,
                        category="CSRF",
                        description=f"POST route lacks CSRF protection",
                        file_path="web_app.py",
                        line_number=i+1,
                        code_snippet=line.strip(),
                        impact="Application vulnerable to Cross-Site Request Forgery attacks",
                        remediation="Add @validate_csrf_token decorator and implement proper CSRF token validation",
                        cwe_id="CWE-352"
                    ))
    
    def _check_sql_injection(self):
        """Check for potential SQL injection vulnerabilities"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for string formatting in SQL-like contexts
            sql_patterns = [
                r'\.query\([^)]*%[^)]*\)',  # SQLAlchemy query with % formatting
                r'\.execute\([^)]*%[^)]*\)',  # Direct execute with % formatting
                r'\.filter\([^)]*%[^)]*\)',  # Filter with % formatting
                r'f["\'][^"\']*SELECT[^"\']*["\']',  # f-string with SELECT
                r'["\'][^"\']*SELECT[^"\']*["\']\.format\(',  # .format() with SELECT
            ]
            
            for i, line in enumerate(lines):
                for pattern in sql_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        self.vulnerabilities.append(SecurityVulnerability(
                            id=f"SQL-001-{file_path}-{i}",
                            title="Potential SQL Injection",
                            severity=SeverityLevel.CRITICAL,
                            category="Injection",
                            description="Potential SQL injection vulnerability detected",
                            file_path=file_path,
                            line_number=i+1,
                            code_snippet=line.strip(),
                            impact="Attackers could execute arbitrary SQL queries",
                            remediation="Use parameterized queries or ORM methods instead of string formatting",
                            cwe_id="CWE-89"
                        ))
    
    def _check_xss_vulnerabilities(self):
        """Check for XSS vulnerabilities"""
        # Check templates for unsafe rendering
        template_dir = Path('templates')
        if template_dir.exists():
            for template_file in template_dir.glob('*.html'):
                with open(template_file, 'r') as f:
                    content = f.read()
                
                lines = content.split('\n')
                
                # Look for unsafe template rendering
                unsafe_patterns = [
                    r'\{\{\s*[^}|]*\|safe\s*\}\}',  # |safe filter
                    r'\{\{\s*[^}]*\|raw\s*\}\}',   # |raw filter
                    r'innerHTML\s*=',               # Direct innerHTML assignment
                ]
                
                for i, line in enumerate(lines):
                    for pattern in unsafe_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            self.vulnerabilities.append(SecurityVulnerability(
                                id=f"XSS-001-{template_file.name}-{i}",
                                title="Potential XSS Vulnerability",
                                severity=SeverityLevel.HIGH,
                                category="XSS",
                                description="Unsafe template rendering detected",
                                file_path=str(template_file),
                                line_number=i+1,
                                code_snippet=line.strip(),
                                impact="Attackers could inject malicious scripts",
                                remediation="Remove |safe filter or properly sanitize input",
                                cwe_id="CWE-79"
                            ))
    
    def _check_security_headers(self):
        """Check for proper security headers implementation"""
        security_middleware_path = Path('security_middleware.py')
        if not security_middleware_path.exists():
            return
        
        with open(security_middleware_path, 'r') as f:
            content = f.read()
        
        required_headers = [
            'Content-Security-Policy',
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security',
            'Referrer-Policy'
        ]
        
        missing_headers = []
        for header in required_headers:
            if header not in content:
                missing_headers.append(header)
        
        if missing_headers:
            self.vulnerabilities.append(SecurityVulnerability(
                id="HEADERS-001",
                title="Missing Security Headers",
                severity=SeverityLevel.MEDIUM,
                category="Security Headers",
                description=f"Missing security headers: {', '.join(missing_headers)}",
                file_path="security_middleware.py",
                line_number=1,
                code_snippet="",
                impact="Reduced protection against various attacks",
                remediation=f"Implement missing headers: {', '.join(missing_headers)}",
                cwe_id="CWE-693"
            ))
    
    def _check_websocket_auth(self):
        """Check WebSocket authentication implementation"""
        websocket_path = Path('websocket_progress_handler.py')
        if not websocket_path.exists():
            return
        
        with open(websocket_path, 'r') as f:
            content = f.read()
        
        # Check for authentication in connect handler
        if 'current_user.is_authenticated' not in content:
            self.vulnerabilities.append(SecurityVulnerability(
                id="WS-001",
                title="Missing WebSocket Authentication",
                severity=SeverityLevel.HIGH,
                category="WebSocket Security",
                description="WebSocket connections may lack proper authentication",
                file_path="websocket_progress_handler.py",
                line_number=1,
                code_snippet="",
                impact="Unauthorized users could access WebSocket functionality",
                remediation="Implement authentication check in WebSocket connect handler",
                cwe_id="CWE-306"
            ))
    
    def _check_sensitive_data_exposure(self):
        """Check for sensitive data exposure"""
        for file_path in self.files_to_audit:
            if not Path(file_path).exists():
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for potential sensitive data exposure
            sensitive_patterns = [
                r'password[^=]*=.*[^*]',  # Password assignments (not masked)
                r'secret[^=]*=.*[^*]',   # Secret assignments
                r'token[^=]*=.*[^*]',    # Token assignments
                r'api_key[^=]*=.*[^*]',  # API key assignments
            ]
            
            for i, line in enumerate(lines):
                for pattern in sensitive_patterns:
                    if re.search(pattern, line, re.IGNORECASE) and 'hash' not in line.lower():
                        self.vulnerabilities.append(SecurityVulnerability(
                            id=f"DATA-001-{file_path}-{i}",
                            title="Potential Sensitive Data Exposure",
                            severity=SeverityLevel.MEDIUM,
                            category="Data Exposure",
                            description="Potential sensitive data exposure detected",
                            file_path=file_path,
                            line_number=i+1,
                            code_snippet=line.strip(),
                            impact="Sensitive information could be exposed",
                            remediation="Ensure sensitive data is properly encrypted or masked",
                            cwe_id="CWE-200"
                        ))
    
    def _check_debug_mode(self):
        """Check for debug mode enabled"""
        web_app_path = Path('web_app.py')
        if not web_app_path.exists():
            return
        
        with open(web_app_path, 'r') as f:
            content = f.read()
        
        if 'debug=True' in content or 'DEBUG = True' in content:
            self.vulnerabilities.append(SecurityVulnerability(
                id="DEBUG-001",
                title="Debug Mode Enabled",
                severity=SeverityLevel.HIGH,
                category="Configuration",
                description="Debug mode appears to be enabled",
                file_path="web_app.py",
                line_number=1,
                code_snippet="debug=True",
                impact="Sensitive information could be exposed in error messages",
                remediation="Disable debug mode in production",
                cwe_id="CWE-489"
            ))
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive security audit report"""
        # Sort vulnerabilities by severity
        severity_order = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 4
        }
        
        self.vulnerabilities.sort(key=lambda v: severity_order[v.severity])
        
        # Generate statistics
        stats = {
            'total_vulnerabilities': len(self.vulnerabilities),
            'by_severity': {},
            'by_category': {}
        }
        
        for vuln in self.vulnerabilities:
            # Count by severity
            severity = vuln.severity.value
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
            
            # Count by category
            category = vuln.category
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
        
        report = {
            'audit_timestamp': dt.now().isoformat(),
            'statistics': stats,
            'vulnerabilities': [vuln.to_dict() for vuln in self.vulnerabilities],
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate high-level security recommendations"""
        recommendations = []
        
        if any(v.severity == SeverityLevel.CRITICAL for v in self.vulnerabilities):
            recommendations.append("URGENT: Address all Critical severity vulnerabilities immediately")
        
        if any(v.category == "CSRF" for v in self.vulnerabilities):
            recommendations.append("Implement comprehensive CSRF protection across all forms")
        
        if any(v.category == "Authentication" for v in self.vulnerabilities):
            recommendations.append("Review and strengthen authentication mechanisms")
        
        if any(v.category == "XSS" for v in self.vulnerabilities):
            recommendations.append("Implement proper input sanitization and output encoding")
        
        if any(v.category == "Injection" for v in self.vulnerabilities):
            recommendations.append("Use parameterized queries and input validation")
        
        recommendations.extend([
            "Implement automated security testing in CI/CD pipeline",
            "Conduct regular security code reviews",
            "Set up security monitoring and alerting",
            "Create incident response procedures",
            "Provide security training for development team"
        ])
        
        return recommendations

def main():
    """Main function to run security audit"""
    auditor = SecurityAuditor()
    report = auditor.run_audit()
    
    # Save report to file
    report_file = 'security_audit_report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Print summary
    print(f"\n{'='*60}")
    print("SECURITY AUDIT SUMMARY")
    print(f"{'='*60}")
    print(f"Total Vulnerabilities Found: {report['statistics']['total_vulnerabilities']}")
    print("\nBy Severity:")
    for severity, count in report['statistics']['by_severity'].items():
        print(f"  {severity}: {count}")
    
    print("\nBy Category:")
    for category, count in report['statistics']['by_category'].items():
        print(f"  {category}: {count}")
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Print critical vulnerabilities
    critical_vulns = [v for v in auditor.vulnerabilities if v.severity == SeverityLevel.CRITICAL]
    if critical_vulns:
        print(f"\n{'='*60}")
        print("CRITICAL VULNERABILITIES (IMMEDIATE ACTION REQUIRED)")
        print(f"{'='*60}")
        for vuln in critical_vulns:
            print(f"\n{vuln.id}: {vuln.title}")
            print(f"File: {vuln.file_path}:{vuln.line_number}")
            print(f"Description: {vuln.description}")
            print(f"Remediation: {vuln.remediation}")
    
    return len(critical_vulns)

if __name__ == '__main__':
    import datetime
    critical_count = main()
    sys.exit(critical_count)  # Exit with number of critical vulnerabilities