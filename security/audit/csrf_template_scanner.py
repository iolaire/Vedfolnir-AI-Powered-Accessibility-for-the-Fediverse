# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Template Scanner

Automated scanner to identify CSRF vulnerabilities across all templates,
detect token exposure, and validate CSRF implementation compliance.
"""

import re
import logging
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from bs4 import BeautifulSoup, Comment
from jinja2 import Environment, meta

logger = logging.getLogger(__name__)


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


class CSRFTemplateScanner:
    """Scanner for CSRF vulnerabilities in templates"""
    
    def __init__(self):
        """Initialize CSRF template scanner"""
        self.csrf_patterns = {
            'hidden_tag': re.compile(r'\{\{\s*\w*_?form\.hidden_tag\(\)\s*\}\}'),
            'csrf_token': re.compile(r'\{\{\s*csrf_token\(\)\s*\}\}'),
            'csrf_meta': re.compile(r'name=["\']csrf-token["\']'),
            'csrf_header': re.compile(r'X-CSRFToken|X-CSRF-Token'),
        }
        
        self.exposure_patterns = {
            'comment': re.compile(r'<!--.*?csrf_token\(\).*?-->', re.DOTALL | re.IGNORECASE),
            'script': re.compile(r'<script[^>]*>.*?csrf_token\(\).*?</script>', re.DOTALL | re.IGNORECASE),
            'console': re.compile(r'console\.log.*?csrf_token\(\)', re.IGNORECASE),
            'alert': re.compile(r'alert.*?csrf_token\(\)', re.IGNORECASE),
            'visible_div': re.compile(r'<div[^>]*>.*?csrf_token\(\).*?</div>', re.DOTALL | re.IGNORECASE),
            'visible_span': re.compile(r'<span[^>]*>.*?csrf_token\(\).*?</span>', re.DOTALL | re.IGNORECASE),
        }
        
        self.form_patterns = {
            'post_form': re.compile(r'<form[^>]*method\s*=\s*["\']post["\'][^>]*>', re.IGNORECASE),
            'put_form': re.compile(r'<form[^>]*method\s*=\s*["\']put["\'][^>]*>', re.IGNORECASE),
            'patch_form': re.compile(r'<form[^>]*method\s*=\s*["\']patch["\'][^>]*>', re.IGNORECASE),
            'delete_form': re.compile(r'<form[^>]*method\s*=\s*["\']delete["\'][^>]*>', re.IGNORECASE),
            'get_form': re.compile(r'<form[^>]*method\s*=\s*["\']get["\'][^>]*>', re.IGNORECASE),
            'no_method_form': re.compile(r'<form(?![^>]*method\s*=)[^>]*>', re.IGNORECASE),
        }
        
        self.ajax_patterns = {
            'fetch_post': re.compile(r'fetch\s*\([^)]*method\s*:\s*["\'](?:POST|PUT|PATCH|DELETE)["\']', re.IGNORECASE),
            'jquery_ajax': re.compile(r'\.ajax\s*\([^)]*type\s*:\s*["\'](?:POST|PUT|PATCH|DELETE)["\']', re.IGNORECASE),
            'xhr_post': re.compile(r'XMLHttpRequest.*?open\s*\([^)]*["\'](?:POST|PUT|PATCH|DELETE)["\']', re.IGNORECASE),
        }
    
    def scan_template(self, template_path: str) -> CSRFAuditResult:
        """Scan a single template for CSRF vulnerabilities
        
        Args:
            template_path: Path to template file
            
        Returns:
            CSRFAuditResult with scan results
        """
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Initialize result
            result = CSRFAuditResult(
                template_path=template_path,
                has_forms=False,
                csrf_protected=False,
                csrf_method='none',
                issues=[],
                compliance_score=0.0,
                recommendations=[]
            )
            
            # Analyze template content
            self._analyze_forms(content, result)
            self._analyze_csrf_protection(content, result)
            self._analyze_token_exposure(content, result)
            self._analyze_ajax_requests(content, result)
            
            # Calculate compliance score
            result.compliance_score = self.calculate_compliance_score(result)
            
            # Generate recommendations
            result.recommendations = self.generate_recommendations(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to scan template {template_path}: {e}")
            return CSRFAuditResult(
                template_path=template_path,
                has_forms=False,
                csrf_protected=False,
                csrf_method='none',
                issues=[TemplateSecurityIssue(
                    template_path=template_path,
                    issue_type='scan_error',
                    severity='HIGH',
                    description=f'Failed to scan template: {e}'
                )],
                compliance_score=0.0,
                recommendations=['Fix template syntax errors']
            )
    
    def _analyze_forms(self, content: str, result: CSRFAuditResult):
        """Analyze forms in template content"""
        # Check for various form types
        state_changing_forms = []
        get_forms = []
        
        for pattern_name, pattern in self.form_patterns.items():
            matches = pattern.finditer(content)
            for match in matches:
                result.has_forms = True
                
                if pattern_name in ['post_form', 'put_form', 'patch_form', 'delete_form']:
                    state_changing_forms.append((match, pattern_name))
                elif pattern_name == 'get_form':
                    get_forms.append((match, pattern_name))
                elif pattern_name == 'no_method_form':
                    # Forms without method default to GET
                    get_forms.append((match, 'default_get_form'))
        
        # Store form information for later analysis
        result._state_changing_forms = state_changing_forms
        result._get_forms = get_forms
    
    def _analyze_csrf_protection(self, content: str, result: CSRFAuditResult):
        """Analyze CSRF protection in template"""
        if not result.has_forms:
            return
        
        # Check for CSRF protection methods globally
        has_hidden_tag = bool(self.csrf_patterns['hidden_tag'].search(content))
        has_csrf_token = bool(self.csrf_patterns['csrf_token'].search(content))
        has_csrf_meta = bool(self.csrf_patterns['csrf_meta'].search(content))
        
        # Determine overall CSRF method
        if has_hidden_tag and has_csrf_token:
            result.csrf_method = 'mixed'
            result.csrf_protected = True
            result.issues.append(TemplateSecurityIssue(
                template_path=result.template_path,
                issue_type='inconsistent_csrf',
                severity='MEDIUM',
                description='Template uses both form.hidden_tag() and csrf_token() - inconsistent implementation',
                recommendation='Use form.hidden_tag() consistently for all forms'
            ))
        elif has_hidden_tag:
            result.csrf_method = 'hidden_tag'
            result.csrf_protected = True
        elif has_csrf_token:
            result.csrf_method = 'csrf_token'
            result.csrf_protected = True
            result.issues.append(TemplateSecurityIssue(
                template_path=result.template_path,
                issue_type='csrf_method',
                severity='LOW',
                description='Template uses csrf_token() instead of recommended form.hidden_tag()',
                recommendation='Replace csrf_token() with form.hidden_tag() for better security'
            ))
        else:
            result.csrf_method = 'none'
            result.csrf_protected = False
        
        # Analyze each form individually for CSRF protection
        if hasattr(result, '_state_changing_forms'):
            for form_match, form_type in result._state_changing_forms:
                form_content = self._extract_form_content(content, form_match)
                form_has_csrf = self._form_has_csrf_protection(form_content)
                
                if not form_has_csrf:
                    result.issues.append(TemplateSecurityIssue(
                        template_path=result.template_path,
                        issue_type='missing_csrf',
                        severity='CRITICAL',
                        description=f'{form_type.replace("_", " ").title()} form missing CSRF protection',
                        line_number=self._get_line_number(content, form_match.start()),
                        code_snippet=form_match.group(0),
                        recommendation='Add {{ form.hidden_tag() }} inside the form'
                    ))
        
        # Check GET forms for unnecessary CSRF tokens
        if hasattr(result, '_get_forms'):
            for form_match, form_type in result._get_forms:
                form_content = self._extract_form_content(content, form_match)
                form_has_csrf = self._form_has_csrf_protection(form_content)
                
                if form_has_csrf:
                    result.issues.append(TemplateSecurityIssue(
                        template_path=result.template_path,
                        issue_type='unnecessary_csrf',
                        severity='LOW',
                        description='GET form has unnecessary CSRF token (GET requests should be idempotent)',
                        line_number=self._get_line_number(content, form_match.start()),
                        code_snippet=form_match.group(0),
                        recommendation='Remove CSRF token from GET forms or change to POST if state-changing'
                    ))
    
    def _analyze_token_exposure(self, content: str, result: CSRFAuditResult):
        """Analyze potential CSRF token exposure"""
        for exposure_type, pattern in self.exposure_patterns.items():
            matches = pattern.finditer(content)
            for match in matches:
                # Skip if this is the proper CSRF meta tag (which is secure)
                if self._is_secure_csrf_meta_tag(match.group(0)):
                    continue
                
                severity = 'HIGH' if exposure_type in ['comment', 'script', 'console'] else 'MEDIUM'
                
                result.issues.append(TemplateSecurityIssue(
                    template_path=result.template_path,
                    issue_type='token_exposure',
                    severity=severity,
                    description=f'CSRF token potentially exposed in {exposure_type.replace("_", " ")}',
                    line_number=self._get_line_number(content, match.start()),
                    code_snippet=match.group(0)[:100] + '...' if len(match.group(0)) > 100 else match.group(0),
                    recommendation='Use meta tag for JavaScript access: <meta name="csrf-token" content="{{ csrf_token() }}">'
                ))
    
    def _analyze_ajax_requests(self, content: str, result: CSRFAuditResult):
        """Analyze AJAX requests for CSRF protection"""
        ajax_requests = []
        
        for ajax_type, pattern in self.ajax_patterns.items():
            matches = pattern.finditer(content)
            for match in matches:
                ajax_requests.append((match, ajax_type))
        
        # Check if AJAX requests have CSRF headers
        for ajax_match, ajax_type in ajax_requests:
            # Check context around AJAX request for CSRF header or secure patterns
            context_start = max(0, ajax_match.start() - 500)
            context_end = min(len(content), ajax_match.end() + 500)
            context = content[context_start:context_end]
            
            # Check for CSRF protection patterns
            has_csrf_header = bool(self.csrf_patterns['csrf_header'].search(context))
            has_secure_fetch = bool(re.search(r'csrfHandler\.secureFetch', context, re.IGNORECASE))
            has_csrf_token_meta = bool(re.search(r'csrf-token.*getAttribute', context, re.IGNORECASE))
            
            # Consider request protected if it has any CSRF protection
            is_protected = has_csrf_header or has_secure_fetch or has_csrf_token_meta
            
            if not is_protected:
                result.issues.append(TemplateSecurityIssue(
                    template_path=result.template_path,
                    issue_type='ajax_csrf_missing',
                    severity='HIGH',
                    description=f'AJAX {ajax_type.replace("_", " ")} request missing CSRF header',
                    line_number=self._get_line_number(content, ajax_match.start()),
                    code_snippet=ajax_match.group(0),
                    recommendation='Add X-CSRFToken header with token from meta tag or use window.csrfHandler.secureFetch()'
                ))
    
    def _get_line_number(self, content: str, position: int) -> int:
        """Get line number for a position in content"""
        return content[:position].count('\n') + 1
    
    def _extract_form_content(self, content: str, form_match) -> str:
        """Extract the content of a form element
        
        Args:
            content: Full template content
            form_match: Regex match object for form opening tag
            
        Returns:
            Content between form opening and closing tags
        """
        form_start = form_match.end()
        
        # Find the matching closing </form> tag
        # This is a simplified approach - in practice, you might want more robust HTML parsing
        form_depth = 1
        pos = form_start
        
        while pos < len(content) and form_depth > 0:
            # Look for form tags
            next_open = content.find('<form', pos)
            next_close = content.find('</form>', pos)
            
            if next_close == -1:
                # No closing tag found, return rest of content
                return content[form_start:]
            
            if next_open != -1 and next_open < next_close:
                # Found nested form opening tag
                form_depth += 1
                pos = next_open + 5
            else:
                # Found closing tag
                form_depth -= 1
                if form_depth == 0:
                    return content[form_start:next_close]
                pos = next_close + 7
        
        # Fallback: return content from form start to end
        return content[form_start:]
    
    def _form_has_csrf_protection(self, form_content: str) -> bool:
        """Check if a form has CSRF protection
        
        Args:
            form_content: Content within form tags
            
        Returns:
            True if form has CSRF protection, False otherwise
        """
        # Check for various CSRF protection patterns within the form
        has_hidden_tag = bool(self.csrf_patterns['hidden_tag'].search(form_content))
        has_csrf_token = bool(self.csrf_patterns['csrf_token'].search(form_content))
        
        # Also check for manual CSRF input fields
        csrf_input_pattern = re.compile(r'<input[^>]*name=["\']csrf_token["\'][^>]*>', re.IGNORECASE)
        has_csrf_input = bool(csrf_input_pattern.search(form_content))
        
        return has_hidden_tag or has_csrf_token or has_csrf_input
    
    def _is_secure_csrf_meta_tag(self, content: str) -> bool:
        """Check if content is a secure CSRF meta tag
        
        Args:
            content: Content to check
            
        Returns:
            True if this is a secure CSRF meta tag, False otherwise
        """
        # Check if this is the standard CSRF meta tag pattern
        meta_tag_pattern = re.compile(
            r'<meta\s+name=["\']csrf-token["\']\s+content=["\'].*?csrf_token\(\).*?["\']',
            re.IGNORECASE | re.DOTALL
        )
        return bool(meta_tag_pattern.search(content))
    
    def calculate_compliance_score(self, result: CSRFAuditResult) -> float:
        """Calculate CSRF compliance score
        
        Args:
            result: CSRF audit result
            
        Returns:
            Compliance score between 0.0 and 1.0
        """
        if not result.has_forms:
            return 1.0  # No forms = no CSRF issues
        
        base_score = 1.0
        
        # Deduct points for issues
        for issue in result.issues:
            if issue.severity == 'CRITICAL':
                base_score -= 0.4
            elif issue.severity == 'HIGH':
                base_score -= 0.2
            elif issue.severity == 'MEDIUM':
                base_score -= 0.1
            elif issue.severity == 'LOW':
                base_score -= 0.05
        
        # Bonus for good practices
        if result.csrf_protected and result.csrf_method == 'hidden_tag':
            base_score += 0.1
        
        return max(0.0, min(1.0, base_score))
    
    def generate_recommendations(self, result: CSRFAuditResult) -> List[str]:
        """Generate security recommendations
        
        Args:
            result: CSRF audit result
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if not result.has_forms:
            return recommendations
        
        # General recommendations based on issues
        issue_types = {issue.issue_type for issue in result.issues}
        
        if 'missing_csrf' in issue_types:
            recommendations.append('Add CSRF protection to all state-changing forms using {{ form.hidden_tag() }}')
        
        if 'csrf_method' in issue_types:
            recommendations.append('Replace csrf_token() with form.hidden_tag() for consistent implementation')
        
        if 'inconsistent_csrf' in issue_types:
            recommendations.append('Use form.hidden_tag() consistently across all forms')
        
        if 'token_exposure' in issue_types:
            recommendations.append('Avoid exposing CSRF tokens in HTML comments or JavaScript console logs')
            recommendations.append('Use meta tag for JavaScript access: <meta name="csrf-token" content="{{ csrf_token() }}">')
        
        if 'ajax_csrf_missing' in issue_types:
            recommendations.append('Add X-CSRFToken header to all AJAX requests that modify state')
            recommendations.append('Retrieve CSRF token from meta tag for AJAX requests')
        
        if 'unnecessary_csrf' in issue_types:
            recommendations.append('Remove CSRF tokens from GET forms (GET requests should be idempotent)')
        
        # Best practices
        if result.csrf_protected and not recommendations:
            recommendations.append('CSRF implementation looks good - maintain current security practices')
        
        return recommendations
    
    def scan_all_templates(self, templates_dir: str) -> List[CSRFAuditResult]:
        """Scan all templates in a directory
        
        Args:
            templates_dir: Path to templates directory
            
        Returns:
            List of CSRF audit results
        """
        results = []
        templates_path = Path(templates_dir)
        
        if not templates_path.exists():
            logger.error(f"Templates directory not found: {templates_dir}")
            return results
        
        # Scan all HTML templates
        for template_path in templates_path.rglob('*.html'):
            if template_path.is_file():
                try:
                    result = self.scan_template(str(template_path))
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to scan template {template_path}: {e}")
        
        return results
    
    def generate_compliance_report(self, results: List[CSRFAuditResult]) -> Dict:
        """Generate comprehensive compliance report
        
        Args:
            results: List of CSRF audit results
            
        Returns:
            Compliance report dictionary
        """
        if not results:
            return {'error': 'No templates scanned'}
        
        # Calculate overall statistics
        total_templates = len(results)
        templates_with_forms = len([r for r in results if r.has_forms])
        protected_templates = len([r for r in results if r.csrf_protected])
        
        # Issue statistics
        all_issues = []
        for result in results:
            all_issues.extend(result.issues)
        
        issue_counts = {}
        severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        
        for issue in all_issues:
            issue_counts[issue.issue_type] = issue_counts.get(issue.issue_type, 0) + 1
            severity_counts[issue.severity] += 1
        
        # Compliance scores
        scores = [r.compliance_score for r in results if r.has_forms]
        avg_score = sum(scores) / len(scores) if scores else 1.0
        
        # Templates by compliance level
        excellent = len([r for r in results if r.compliance_score >= 0.9])
        good = len([r for r in results if 0.7 <= r.compliance_score < 0.9])
        needs_improvement = len([r for r in results if 0.5 <= r.compliance_score < 0.7])
        poor = len([r for r in results if r.compliance_score < 0.5])
        
        return {
            'summary': {
                'total_templates': total_templates,
                'templates_with_forms': templates_with_forms,
                'csrf_protected_templates': protected_templates,
                'protection_rate': protected_templates / templates_with_forms if templates_with_forms > 0 else 1.0,
                'average_compliance_score': avg_score
            },
            'issues': {
                'total_issues': len(all_issues),
                'by_severity': severity_counts,
                'by_type': issue_counts
            },
            'compliance_levels': {
                'excellent': excellent,
                'good': good,
                'needs_improvement': needs_improvement,
                'poor': poor
            },
            'templates': [
                {
                    'path': r.template_path,
                    'has_forms': r.has_forms,
                    'csrf_protected': r.csrf_protected,
                    'csrf_method': r.csrf_method,
                    'compliance_score': r.compliance_score,
                    'issue_count': len(r.issues),
                    'critical_issues': len([i for i in r.issues if i.severity == 'CRITICAL'])
                }
                for r in results
            ]
        }