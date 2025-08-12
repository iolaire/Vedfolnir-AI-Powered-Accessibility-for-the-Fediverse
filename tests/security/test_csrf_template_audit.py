# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Template Security Audit Tests

Automated tests to scan templates for CSRF compliance, detect token exposure,
and implement security regression tests to prevent future vulnerabilities.
"""

import unittest
import os
import re
import json
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
from bs4 import BeautifulSoup, Comment
from flask import Flask, render_template_string
from jinja2 import Environment, FileSystemLoader, meta

# Import CSRF components for testing
from security.audit.csrf_template_scanner import CSRFTemplateScanner
from security.audit.security_auditor import SecurityAuditor


@dataclass
class TemplateSecurityIssue:
    """Represents a security issue found in a template"""
    template_path: str
    issue_type: str
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    description: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class CSRFAuditResult:
    """Results of CSRF template audit"""
    template_path: str
    has_forms: bool
    csrf_protected: bool
    csrf_method: str  # 'hidden_tag', 'csrf_token', 'none', 'mixed'
    issues: List[TemplateSecurityIssue]
    compliance_score: float
    recommendations: List[str]


class TestCSRFTemplateScanner(unittest.TestCase):
    """Test CSRF template scanning functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.templates_dir = Path('templates')
        self.scanner = CSRFTemplateScanner()
        
        # Create test templates directory if it doesn't exist
        self.test_templates_dir = Path('test_templates')
        self.test_templates_dir.mkdir(exist_ok=True)
        
        # Sample template content for testing
        self.sample_templates = {
            'good_form.html': '''
                <form method="POST" action="/submit">
                    {{ form.hidden_tag() }}
                    <input type="text" name="username">
                    <button type="submit">Submit</button>
                </form>
            ''',
            'bad_form_visible_token.html': '''
                <form method="POST" action="/submit">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <input type="text" name="username">
                    <button type="submit">Submit</button>
                </form>
            ''',
            'bad_form_no_csrf.html': '''
                <form method="POST" action="/submit">
                    <input type="text" name="username">
                    <button type="submit">Submit</button>
                </form>
            ''',
            'get_form_with_csrf.html': '''
                <form method="GET" action="/search">
                    {{ form.hidden_tag() }}
                    <input type="text" name="query">
                    <button type="submit">Search</button>
                </form>
            ''',
            'mixed_csrf_methods.html': '''
                <form method="POST" action="/form1">
                    {{ form.hidden_tag() }}
                    <input type="text" name="field1">
                    <button type="submit">Submit 1</button>
                </form>
                <form method="POST" action="/form2">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <input type="text" name="field2">
                    <button type="submit">Submit 2</button>
                </form>
            ''',
            'ajax_form.html': '''
                <form id="ajaxForm" method="POST" action="/api/submit">
                    {{ form.hidden_tag() }}
                    <input type="text" name="data">
                    <button type="submit">Submit</button>
                </form>
                <script>
                    document.getElementById('ajaxForm').addEventListener('submit', function(e) {
                        e.preventDefault();
                        fetch('/api/submit', {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                            },
                            body: new FormData(this)
                        });
                    });
                </script>
            ''',
            'exposed_token_in_comment.html': '''
                <!-- CSRF Token: {{ csrf_token() }} -->
                <form method="POST" action="/submit">
                    {{ form.hidden_tag() }}
                    <input type="text" name="username">
                    <button type="submit">Submit</button>
                </form>
            ''',
            'exposed_token_in_script.html': '''
                <form method="POST" action="/submit">
                    {{ form.hidden_tag() }}
                    <input type="text" name="username">
                    <button type="submit">Submit</button>
                </form>
                <script>
                    var csrfToken = "{{ csrf_token() }}";
                    console.log("CSRF Token:", csrfToken);
                </script>
            '''
        }
        
        # Write test templates
        for filename, content in self.sample_templates.items():
            (self.test_templates_dir / filename).write_text(content.strip())
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove test templates
        for filename in self.sample_templates.keys():
            template_path = self.test_templates_dir / filename
            if template_path.exists():
                template_path.unlink()
        
        if self.test_templates_dir.exists():
            self.test_templates_dir.rmdir()
    
    def test_scan_template_with_good_csrf(self):
        """Test scanning template with proper CSRF protection"""
        template_path = self.test_templates_dir / 'good_form.html'
        result = self.scanner.scan_template(str(template_path))
        
        self.assertIsInstance(result, CSRFAuditResult)
        self.assertTrue(result.has_forms)
        self.assertTrue(result.csrf_protected)
        self.assertEqual(result.csrf_method, 'hidden_tag')
        self.assertEqual(len(result.issues), 0)
        self.assertGreaterEqual(result.compliance_score, 0.9)
    
    def test_scan_template_with_visible_token(self):
        """Test scanning template with visible CSRF token"""
        template_path = self.test_templates_dir / 'bad_form_visible_token.html'
        result = self.scanner.scan_template(str(template_path))
        
        self.assertTrue(result.has_forms)
        self.assertTrue(result.csrf_protected)
        self.assertEqual(result.csrf_method, 'csrf_token')
        self.assertGreater(len(result.issues), 0)
        
        # Should have issue about visible token
        visible_token_issues = [
            issue for issue in result.issues 
            if 'visible' in issue.description.lower() or 'exposed' in issue.description.lower()
        ]
        self.assertGreater(len(visible_token_issues), 0)
    
    def test_scan_template_without_csrf(self):
        """Test scanning template without CSRF protection"""
        template_path = self.test_templates_dir / 'bad_form_no_csrf.html'
        result = self.scanner.scan_template(str(template_path))
        
        self.assertTrue(result.has_forms)
        self.assertFalse(result.csrf_protected)
        self.assertEqual(result.csrf_method, 'none')
        self.assertGreater(len(result.issues), 0)
        
        # Should have critical issue about missing CSRF
        critical_issues = [
            issue for issue in result.issues 
            if issue.severity == 'CRITICAL'
        ]
        self.assertGreater(len(critical_issues), 0)
    
    def test_scan_get_form_with_csrf(self):
        """Test scanning GET form with unnecessary CSRF token"""
        template_path = self.test_templates_dir / 'get_form_with_csrf.html'
        result = self.scanner.scan_template(str(template_path))
        
        self.assertTrue(result.has_forms)
        self.assertTrue(result.csrf_protected)
        
        # Should have issue about unnecessary CSRF on GET form
        unnecessary_csrf_issues = [
            issue for issue in result.issues 
            if 'get' in issue.description.lower() and 'unnecessary' in issue.description.lower()
        ]
        self.assertGreater(len(unnecessary_csrf_issues), 0)
    
    def test_scan_mixed_csrf_methods(self):
        """Test scanning template with mixed CSRF methods"""
        template_path = self.test_templates_dir / 'mixed_csrf_methods.html'
        result = self.scanner.scan_template(str(template_path))
        
        self.assertTrue(result.has_forms)
        self.assertTrue(result.csrf_protected)
        self.assertEqual(result.csrf_method, 'mixed')
        
        # Should have issue about inconsistent CSRF methods
        consistency_issues = [
            issue for issue in result.issues 
            if 'inconsistent' in issue.description.lower() or 'mixed' in issue.description.lower()
        ]
        self.assertGreater(len(consistency_issues), 0)
    
    def test_scan_ajax_form(self):
        """Test scanning AJAX form with proper CSRF handling"""
        template_path = self.test_templates_dir / 'ajax_form.html'
        result = self.scanner.scan_template(str(template_path))
        
        self.assertTrue(result.has_forms)
        self.assertTrue(result.csrf_protected)
        
        # Should detect AJAX CSRF handling
        ajax_issues = [
            issue for issue in result.issues 
            if 'ajax' in issue.description.lower()
        ]
        # AJAX form with proper CSRF should have minimal issues
        self.assertLessEqual(len(ajax_issues), 1)
    
    def test_detect_exposed_token_in_comment(self):
        """Test detection of CSRF token exposed in HTML comments"""
        template_path = self.test_templates_dir / 'exposed_token_in_comment.html'
        result = self.scanner.scan_template(str(template_path))
        
        # Should detect token exposure in comments
        exposure_issues = [
            issue for issue in result.issues 
            if 'comment' in issue.description.lower() and 'exposed' in issue.description.lower()
        ]
        self.assertGreater(len(exposure_issues), 0)
        
        # Should be high severity
        high_severity_issues = [
            issue for issue in exposure_issues 
            if issue.severity == 'HIGH'
        ]
        self.assertGreater(len(high_severity_issues), 0)
    
    def test_detect_exposed_token_in_script(self):
        """Test detection of CSRF token exposed in JavaScript"""
        template_path = self.test_templates_dir / 'exposed_token_in_script.html'
        result = self.scanner.scan_template(str(template_path))
        
        # Should detect token exposure in JavaScript
        exposure_issues = [
            issue for issue in result.issues 
            if 'javascript' in issue.description.lower() and 'exposed' in issue.description.lower()
        ]
        self.assertGreater(len(exposure_issues), 0)


class TestRealTemplateAudit(unittest.TestCase):
    """Test CSRF audit on real application templates"""
    
    def setUp(self):
        """Set up test environment"""
        self.templates_dir = Path('templates')
        self.scanner = CSRFTemplateScanner()
        
        # Skip if templates directory doesn't exist
        if not self.templates_dir.exists():
            self.skipTest("Templates directory not found")
    
    def test_audit_all_templates(self):
        """Test CSRF audit on all application templates"""
        results = []
        
        # Scan all HTML templates
        for template_path in self.templates_dir.rglob('*.html'):
            if template_path.is_file():
                try:
                    result = self.scanner.scan_template(str(template_path))
                    results.append(result)
                except Exception as e:
                    self.fail(f"Failed to scan template {template_path}: {e}")
        
        # Ensure we found some templates
        self.assertGreater(len(results), 0, "No templates found to audit")
        
        # Check for critical issues
        critical_issues = []
        for result in results:
            critical_issues.extend([
                issue for issue in result.issues 
                if issue.severity == 'CRITICAL'
            ])
        
        # Report critical issues
        if critical_issues:
            issue_summary = "\n".join([
                f"  - {issue.template_path}: {issue.description}"
                for issue in critical_issues
            ])
            self.fail(f"Found {len(critical_issues)} critical CSRF issues:\n{issue_summary}")
    
    def test_base_template_csrf_meta_tag(self):
        """Test that base template has proper CSRF meta tag"""
        base_template = self.templates_dir / 'base.html'
        
        if not base_template.exists():
            self.skipTest("base.html template not found")
        
        content = base_template.read_text()
        
        # Should have CSRF meta tag
        self.assertIn('name="csrf-token"', content)
        self.assertIn('csrf_token()', content)
        
        # Meta tag should be in head section
        soup = BeautifulSoup(content, 'html.parser')
        head = soup.find('head')
        self.assertIsNotNone(head)
        
        csrf_meta = head.find('meta', {'name': 'csrf-token'})
        self.assertIsNotNone(csrf_meta, "CSRF meta tag not found in head section")
    
    def test_form_templates_csrf_protection(self):
        """Test that templates with forms have proper CSRF protection"""
        form_templates = []
        
        # Find templates that likely contain forms
        form_template_patterns = [
            'login.html',
            'platform_management.html',
            'user_management.html',
            'profile.html',
            'admin_*.html'
        ]
        
        for pattern in form_template_patterns:
            for template_path in self.templates_dir.rglob(pattern):
                if template_path.is_file():
                    form_templates.append(template_path)
        
        # Test each form template
        for template_path in form_templates:
            with self.subTest(template=template_path.name):
                result = self.scanner.scan_template(str(template_path))
                
                if result.has_forms:
                    # Forms should have CSRF protection
                    self.assertTrue(
                        result.csrf_protected,
                        f"Template {template_path.name} has forms but no CSRF protection"
                    )
                    
                    # Should prefer hidden_tag method
                    if result.csrf_method == 'csrf_token':
                        print(f"Warning: {template_path.name} uses csrf_token() instead of form.hidden_tag()")
    
    def test_modal_forms_csrf_protection(self):
        """Test that modal forms have proper CSRF protection"""
        modal_templates = []
        
        # Find templates with modals
        for template_path in self.templates_dir.rglob('*.html'):
            if template_path.is_file():
                content = template_path.read_text()
                if 'modal' in content.lower() and 'form' in content.lower():
                    modal_templates.append(template_path)
        
        # Test each modal template
        for template_path in modal_templates:
            with self.subTest(template=template_path.name):
                content = template_path.read_text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find forms within modals
                modals = soup.find_all(class_=re.compile(r'modal'))
                for modal in modals:
                    forms = modal.find_all('form')
                    for form in forms:
                        method = form.get('method', 'GET').upper()
                        if method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                            # Should have CSRF protection
                            has_hidden_tag = '{{ form.hidden_tag() }}' in str(form) or 'form.hidden_tag()' in str(form)
                            has_csrf_token = 'csrf_token' in str(form)
                            
                            self.assertTrue(
                                has_hidden_tag or has_csrf_token,
                                f"Modal form in {template_path.name} missing CSRF protection"
                            )


class TestCSRFSecurityRegression(unittest.TestCase):
    """Security regression tests to prevent future CSRF vulnerabilities"""
    
    def setUp(self):
        """Set up test environment"""
        self.templates_dir = Path('templates')
        self.scanner = CSRFTemplateScanner()
    
    def test_no_csrf_token_in_get_forms(self):
        """Test that GET forms don't have unnecessary CSRF tokens"""
        if not self.templates_dir.exists():
            self.skipTest("Templates directory not found")
        
        violations = []
        
        for template_path in self.templates_dir.rglob('*.html'):
            if template_path.is_file():
                content = template_path.read_text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find GET forms
                get_forms = soup.find_all('form', method=re.compile(r'^get$', re.I))
                for form in get_forms:
                    # Check for CSRF tokens
                    if ('csrf_token' in str(form) or 
                        'hidden_tag' in str(form)):
                        violations.append(f"{template_path.name}: GET form has CSRF token")
        
        if violations:
            self.fail(f"Found GET forms with unnecessary CSRF tokens:\n" + 
                     "\n".join(f"  - {v}" for v in violations))
    
    def test_no_exposed_csrf_tokens(self):
        """Test that CSRF tokens are not exposed in HTML output"""
        if not self.templates_dir.exists():
            self.skipTest("Templates directory not found")
        
        violations = []
        
        for template_path in self.templates_dir.rglob('*.html'):
            if template_path.is_file():
                content = template_path.read_text()
                
                # Check for exposed tokens in various contexts
                exposure_patterns = [
                    (r'<!--.*?csrf_token\(\).*?-->', 'HTML comment'),
                    (r'<script[^>]*>.*?csrf_token\(\).*?</script>', 'JavaScript code'),
                    (r'console\.log.*?csrf_token\(\)', 'Console log'),
                    (r'alert.*?csrf_token\(\)', 'Alert dialog'),
                    (r'<div[^>]*>.*?csrf_token\(\).*?</div>', 'Visible div'),
                    (r'<span[^>]*>.*?csrf_token\(\).*?</span>', 'Visible span'),
                ]
                
                for pattern, context in exposure_patterns:
                    if re.search(pattern, content, re.DOTALL | re.IGNORECASE):
                        violations.append(f"{template_path.name}: CSRF token exposed in {context}")
        
        if violations:
            self.fail(f"Found exposed CSRF tokens:\n" + 
                     "\n".join(f"  - {v}" for v in violations))
    
    def test_consistent_csrf_implementation(self):
        """Test that CSRF implementation is consistent across templates"""
        if not self.templates_dir.exists():
            self.skipTest("Templates directory not found")
        
        csrf_methods = {}
        
        for template_path in self.templates_dir.rglob('*.html'):
            if template_path.is_file():
                content = template_path.read_text()
                
                # Detect CSRF method used
                if 'form.hidden_tag()' in content:
                    csrf_methods[template_path.name] = 'hidden_tag'
                elif 'csrf_token()' in content:
                    csrf_methods[template_path.name] = 'csrf_token'
        
        # Check for mixed usage
        hidden_tag_templates = [t for t, m in csrf_methods.items() if m == 'hidden_tag']
        csrf_token_templates = [t for t, m in csrf_methods.items() if m == 'csrf_token']
        
        if hidden_tag_templates and csrf_token_templates:
            print(f"Warning: Mixed CSRF methods detected:")
            print(f"  hidden_tag(): {', '.join(hidden_tag_templates)}")
            print(f"  csrf_token(): {', '.join(csrf_token_templates)}")
            print(f"  Recommendation: Use form.hidden_tag() consistently")
    
    def test_ajax_csrf_header_usage(self):
        """Test that AJAX requests use proper CSRF headers"""
        if not self.templates_dir.exists():
            self.skipTest("Templates directory not found")
        
        violations = []
        
        for template_path in self.templates_dir.rglob('*.html'):
            if template_path.is_file():
                content = template_path.read_text()
                
                # Find AJAX requests
                ajax_patterns = [
                    r'fetch\s*\([^)]*method\s*:\s*["\'](?:POST|PUT|PATCH|DELETE)["\']',
                    r'\.ajax\s*\([^)]*type\s*:\s*["\'](?:POST|PUT|PATCH|DELETE)["\']',
                    r'XMLHttpRequest.*?open\s*\([^)]*["\'](?:POST|PUT|PATCH|DELETE)["\']'
                ]
                
                for pattern in ajax_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
                    for match in matches:
                        # Check if CSRF header is included nearby
                        context = content[max(0, match.start()-500):match.end()+500]
                        if not re.search(r'X-CSRFToken|csrf.token', context, re.IGNORECASE):
                            violations.append(f"{template_path.name}: AJAX request missing CSRF header")
        
        if violations:
            print(f"Warning: Found AJAX requests without CSRF headers:\n" + 
                 "\n".join(f"  - {v}" for v in violations))


class TestCSRFComplianceScoring(unittest.TestCase):
    """Test CSRF compliance scoring system"""
    
    def setUp(self):
        """Set up test environment"""
        self.scanner = CSRFTemplateScanner()
    
    def test_compliance_score_calculation(self):
        """Test CSRF compliance score calculation"""
        # Test perfect compliance
        perfect_result = CSRFAuditResult(
            template_path='perfect.html',
            has_forms=True,
            csrf_protected=True,
            csrf_method='hidden_tag',
            issues=[],
            compliance_score=0.0,  # Will be calculated
            recommendations=[]
        )
        
        score = self.scanner.calculate_compliance_score(perfect_result)
        self.assertEqual(score, 1.0)
        
        # Test with minor issues
        minor_issues_result = CSRFAuditResult(
            template_path='minor.html',
            has_forms=True,
            csrf_protected=True,
            csrf_method='csrf_token',
            issues=[
                TemplateSecurityIssue(
                    template_path='minor.html',
                    issue_type='csrf_method',
                    severity='LOW',
                    description='Using csrf_token() instead of form.hidden_tag()'
                )
            ],
            compliance_score=0.0,
            recommendations=[]
        )
        
        score = self.scanner.calculate_compliance_score(minor_issues_result)
        self.assertGreater(score, 0.8)
        self.assertLess(score, 1.0)
        
        # Test with critical issues
        critical_issues_result = CSRFAuditResult(
            template_path='critical.html',
            has_forms=True,
            csrf_protected=False,
            csrf_method='none',
            issues=[
                TemplateSecurityIssue(
                    template_path='critical.html',
                    issue_type='missing_csrf',
                    severity='CRITICAL',
                    description='POST form missing CSRF protection'
                )
            ],
            compliance_score=0.0,
            recommendations=[]
        )
        
        score = self.scanner.calculate_compliance_score(critical_issues_result)
        self.assertLess(score, 0.5)
    
    def test_generate_recommendations(self):
        """Test generation of security recommendations"""
        result = CSRFAuditResult(
            template_path='test.html',
            has_forms=True,
            csrf_protected=True,
            csrf_method='csrf_token',
            issues=[
                TemplateSecurityIssue(
                    template_path='test.html',
                    issue_type='csrf_method',
                    severity='LOW',
                    description='Using csrf_token() instead of form.hidden_tag()'
                )
            ],
            compliance_score=0.85,
            recommendations=[]
        )
        
        recommendations = self.scanner.generate_recommendations(result)
        
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # Should recommend using hidden_tag
        hidden_tag_rec = any('hidden_tag' in rec.lower() for rec in recommendations)
        self.assertTrue(hidden_tag_rec)


if __name__ == '__main__':
    unittest.main(verbosity=2)