#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive Security Auditor for Web Caption Generation System
"""

import os
import re
import ast
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

class SeverityLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

@dataclass
class SecurityFinding:
    category: str
    severity: SeverityLevel
    title: str
    description: str
    file_path: str
    line_number: int
    code_snippet: str
    recommendation: str
    cwe_id: str = None

class SecurityAuditor:
    """Comprehensive security auditor for the web application"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.findings: List[SecurityFinding] = []
        
    def audit_all(self) -> List[SecurityFinding]:
        """Run comprehensive security audit"""
        print("🔍 Starting comprehensive security audit...")
        
        # Web route security
        self.audit_web_routes()
        
        # Input validation
        self.audit_input_validation()
        
        # CSRF protection
        self.audit_csrf_protection()
        
        # Security headers
        self.audit_security_headers()
        
        # WebSocket security
        self.audit_websocket_security()
        
        # Database security
        self.audit_database_security()
        
        # File operations
        self.audit_file_operations()
        
        # Authentication security
        self.audit_authentication()
        
        # Session management
        self.audit_session_management()
        
        # Error handling
        self.audit_error_handling()
        
        # Logging security
        self.audit_logging_security()
        
        print(f"✅ Security audit complete. Found {len(self.findings)} issues.")
        return self.findings
    
    def audit_web_routes(self):
        """Audit web routes for authentication and authorization"""
        print("🔍 Auditing web routes...")
        
        web_app_file = self.project_root / "web_app.py"
        if not web_app_file.exists():
            return
            
        with open(web_app_file, 'r') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Check for unprotected routes
        route_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"]'
        auth_decorators = ['@require_auth', '@login_required', '@admin_required']
        
        for i, line in enumerate(lines):
            if re.search(route_pattern, line):
                route_match = re.search(route_pattern, line)
                route_path = route_match.group(1)
                
                # Check if route has authentication
                has_auth = False
                for j in range(max(0, i-5), i):
                    if any(decorator in lines[j] for decorator in auth_decorators):
                        has_auth = True
                        break
                
                # Skip public routes
                public_routes = ['/health', '/static', '/login', '/']
                if any(pub in route_path for pub in public_routes):
                    continue
                    
                if not has_auth:
                    self.findings.append(SecurityFinding(
                        category="Authentication",
                        severity=SeverityLevel.HIGH,
                        title="Unprotected Route",
                        description=f"Route {route_path} lacks authentication protection",
                        file_path=str(web_app_file),
                        line_number=i+1,
                        code_snippet=line.strip(),
                        recommendation="Add @require_auth or appropriate authentication decorator",
                        cwe_id="CWE-306"
                    ))
    
    def audit_input_validation(self):
        """Audit input validation across all endpoints"""
        print("🔍 Auditing input validation...")
        
        python_files = list(self.project_root.glob("*.py"))
        
        for file_path in python_files:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for direct request.form/request.json usage without validation
            for i, line in enumerate(lines):
                if 'request.form' in line or 'request.json' in line:
                    # Check if validation is present nearby
                    validation_keywords = ['validate', 'sanitize', 'escape', 'clean']
                    has_validation = False
                    
                    for j in range(max(0, i-3), min(len(lines), i+4)):
                        if any(keyword in lines[j].lower() for keyword in validation_keywords):
                            has_validation = True
                            break
                    
                    if not has_validation and 'request.form' in line:
                        self.findings.append(SecurityFinding(
                            category="Input Validation",
                            severity=SeverityLevel.MEDIUM,
                            title="Unvalidated User Input",
                            description="User input accessed without validation",
                            file_path=str(file_path),
                            line_number=i+1,
                            code_snippet=line.strip(),
                            recommendation="Add input validation and sanitization",
                            cwe_id="CWE-20"
                        ))
    
    def audit_csrf_protection(self):
        """Audit CSRF protection implementation"""
        print("🔍 Auditing CSRF protection...")
        
        web_app_file = self.project_root / "web_app.py"
        if not web_app_file.exists():
            return
            
        with open(web_app_file, 'r') as f:
            content = f.read()
        
        # Check if CSRF protection is enabled
        if 'CSRFProtect' not in content and 'csrf' not in content.lower():
            self.findings.append(SecurityFinding(
                category="CSRF Protection",
                severity=SeverityLevel.HIGH,
                title="Missing CSRF Protection",
                description="Application lacks CSRF protection implementation",
                file_path=str(web_app_file),
                line_number=1,
                code_snippet="# CSRF protection not found",
                recommendation="Implement Flask-WTF CSRFProtect or similar CSRF protection",
                cwe_id="CWE-352"
            ))
    
    def audit_security_headers(self):
        """Audit security headers implementation"""
        print("🔍 Auditing security headers...")
        
        web_app_file = self.project_root / "web_app.py"
        if not web_app_file.exists():
            return
            
        with open(web_app_file, 'r') as f:
            content = f.read()
        
        required_headers = {
            'X-Frame-Options': 'Clickjacking protection',
            'X-Content-Type-Options': 'MIME type sniffing protection',
            'X-XSS-Protection': 'XSS protection',
            'Strict-Transport-Security': 'HTTPS enforcement',
            'Content-Security-Policy': 'Content injection protection'
        }
        
        for header, description in required_headers.items():
            if header not in content:
                self.findings.append(SecurityFinding(
                    category="Security Headers",
                    severity=SeverityLevel.MEDIUM,
                    title=f"Missing {header} Header",
                    description=f"Missing security header for {description}",
                    file_path=str(web_app_file),
                    line_number=1,
                    code_snippet="# Security header not found",
                    recommendation=f"Add {header} security header",
                    cwe_id="CWE-693"
                ))
    
    def audit_websocket_security(self):
        """Audit WebSocket security implementation"""
        print("🔍 Auditing WebSocket security...")
        
        ws_files = list(self.project_root.glob("*websocket*.py")) + list(self.project_root.glob("*socket*.py"))
        
        for file_path in ws_files:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for authentication in WebSocket handlers
            for i, line in enumerate(lines):
                if '@socketio.on' in line:
                    # Check for authentication in the handler
                    handler_lines = lines[i:i+10]
                    has_auth = any('authenticate' in l or 'auth' in l for l in handler_lines)
                    
                    if not has_auth:
                        self.findings.append(SecurityFinding(
                            category="WebSocket Security",
                            severity=SeverityLevel.HIGH,
                            title="Unauthenticated WebSocket Handler",
                            description="WebSocket handler lacks authentication",
                            file_path=str(file_path),
                            line_number=i+1,
                            code_snippet=line.strip(),
                            recommendation="Add authentication check in WebSocket handler",
                            cwe_id="CWE-306"
                        ))
    
    def audit_database_security(self):
        """Audit database operations for SQL injection"""
        print("🔍 Auditing database security...")
        
        python_files = list(self.project_root.glob("*.py"))
        
        for file_path in python_files:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for potential SQL injection
            for i, line in enumerate(lines):
                if 'execute(' in line or 'query(' in line:
                    # Check for string formatting in SQL
                    if '%' in line or '.format(' in line or 'f"' in line:
                        self.findings.append(SecurityFinding(
                            category="Database Security",
                            severity=SeverityLevel.CRITICAL,
                            title="Potential SQL Injection",
                            description="SQL query uses string formatting instead of parameters",
                            file_path=str(file_path),
                            line_number=i+1,
                            code_snippet=line.strip(),
                            recommendation="Use parameterized queries with ? placeholders",
                            cwe_id="CWE-89"
                        ))
    
    def audit_file_operations(self):
        """Audit file upload/download operations"""
        print("🔍 Auditing file operations...")
        
        python_files = list(self.project_root.glob("*.py"))
        
        for file_path in python_files:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for file operations
            for i, line in enumerate(lines):
                if 'open(' in line and ('request' in line or 'upload' in line):
                    # Check for path validation
                    if 'secure_filename' not in content:
                        self.findings.append(SecurityFinding(
                            category="File Security",
                            severity=SeverityLevel.HIGH,
                            title="Unsafe File Operation",
                            description="File operation without path validation",
                            file_path=str(file_path),
                            line_number=i+1,
                            code_snippet=line.strip(),
                            recommendation="Use secure_filename() and validate file paths",
                            cwe_id="CWE-22"
                        ))
    
    def audit_authentication(self):
        """Audit authentication implementation"""
        print("🔍 Auditing authentication...")
        
        auth_files = list(self.project_root.glob("*auth*.py")) + [self.project_root / "web_app.py"]
        
        for file_path in auth_files:
            if not file_path.exists():
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for password hashing
            if 'password' in content.lower() and 'hash' not in content.lower():
                self.findings.append(SecurityFinding(
                    category="Authentication",
                    severity=SeverityLevel.CRITICAL,
                    title="Weak Password Storage",
                    description="Passwords may not be properly hashed",
                    file_path=str(file_path),
                    line_number=1,
                    code_snippet="# Password handling found",
                    recommendation="Use bcrypt or similar for password hashing",
                    cwe_id="CWE-256"
                ))
    
    def audit_session_management(self):
        """Audit session management security"""
        print("🔍 Auditing session management...")
        
        session_files = [self.project_root / "session_manager.py", self.project_root / "web_app.py"]
        
        for file_path in session_files:
            if not file_path.exists():
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for secure session configuration
            security_flags = ['secure=True', 'httponly=True', 'samesite']
            missing_flags = [flag for flag in security_flags if flag.lower() not in content.lower()]
            
            if missing_flags:
                self.findings.append(SecurityFinding(
                    category="Session Management",
                    severity=SeverityLevel.MEDIUM,
                    title="Insecure Session Configuration",
                    description=f"Missing session security flags: {', '.join(missing_flags)}",
                    file_path=str(file_path),
                    line_number=1,
                    code_snippet="# Session configuration",
                    recommendation="Add secure session flags (secure, httponly, samesite)",
                    cwe_id="CWE-614"
                ))
    
    def audit_error_handling(self):
        """Audit error handling for information disclosure"""
        print("🔍 Auditing error handling...")
        
        python_files = list(self.project_root.glob("*.py"))
        
        for file_path in python_files:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for debug information in error responses
            for i, line in enumerate(lines):
                if 'except' in line and ('return' in lines[i+1:i+5] or 'jsonify' in str(lines[i+1:i+5])):
                    # Check if error details are exposed
                    error_context = '\n'.join(lines[i:i+5])
                    if 'str(e)' in error_context or 'traceback' in error_context:
                        self.findings.append(SecurityFinding(
                            category="Information Disclosure",
                            severity=SeverityLevel.MEDIUM,
                            title="Error Information Disclosure",
                            description="Error details may be exposed to users",
                            file_path=str(file_path),
                            line_number=i+1,
                            code_snippet=line.strip(),
                            recommendation="Return generic error messages to users",
                            cwe_id="CWE-209"
                        ))
    
    def audit_logging_security(self):
        """Audit logging for sensitive data exposure"""
        print("🔍 Auditing logging security...")
        
        python_files = list(self.project_root.glob("*.py"))
        
        sensitive_patterns = [
            r'password',
            r'token',
            r'secret',
            r'key',
            r'credential'
        ]
        
        for file_path in python_files:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if 'log' in line.lower() and ('info' in line or 'debug' in line or 'error' in line):
                    for pattern in sensitive_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            self.findings.append(SecurityFinding(
                                category="Logging Security",
                                severity=SeverityLevel.MEDIUM,
                                title="Potential Sensitive Data in Logs",
                                description=f"Logging statement may contain sensitive data: {pattern}",
                                file_path=str(file_path),
                                line_number=i+1,
                                code_snippet=line.strip(),
                                recommendation="Avoid logging sensitive data or sanitize before logging",
                                cwe_id="CWE-532"
                            ))
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive security audit report"""
        findings_by_severity = {}
        findings_by_category = {}
        
        for finding in self.findings:
            # Group by severity
            severity = finding.severity.value
            if severity not in findings_by_severity:
                findings_by_severity[severity] = []
            findings_by_severity[severity].append(finding)
            
            # Group by category
            category = finding.category
            if category not in findings_by_category:
                findings_by_category[category] = []
            findings_by_category[category].append(finding)
        
        return {
            'total_findings': len(self.findings),
            'findings_by_severity': {k: len(v) for k, v in findings_by_severity.items()},
            'findings_by_category': {k: len(v) for k, v in findings_by_category.items()},
            'findings': [
                {
                    'category': f.category,
                    'severity': f.severity.value,
                    'title': f.title,
                    'description': f.description,
                    'file_path': f.file_path,
                    'line_number': f.line_number,
                    'code_snippet': f.code_snippet,
                    'recommendation': f.recommendation,
                    'cwe_id': f.cwe_id
                }
                for f in self.findings
            ]
        }

def main():
    """Run security audit"""
    auditor = SecurityAuditor(".")
    findings = auditor.audit_all()
    report = auditor.generate_report()
    
    # Save report
    with open("security/audit/security_audit_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n📊 Security Audit Summary:")
    print(f"Total findings: {report['total_findings']}")
    for severity, count in report['findings_by_severity'].items():
        print(f"{severity}: {count}")
    
    return len([f for f in findings if f.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]])

if __name__ == "__main__":
    exit(main())