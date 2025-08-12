# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Template Security Scanner

Scans all templates for CSRF vulnerabilities and implementation issues.
Identifies forms missing CSRF protection, improper token exposure, and
inconsistent implementation patterns.
"""

import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class CSRFVulnerability:
    """Represents a CSRF security vulnerability"""
    type: str
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    description: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class TemplateSecurityAuditResult:
    """Results of CSRF security audit for a single template"""
    template_path: str
    csrf_protected: bool
    csrf_method: str  # 'hidden_tag', 'csrf_token', 'meta_only', 'none'
    vulnerabilities: List[CSRFVulnerability]
    recommendations: List[str]
    compliance_score: float
    form_count: int
    post_form_count: int
    get_form_count: int
    ajax_endpoints: List[str]
    last_audited: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['last_audited'] = self.last_audited.isoformat()
        result['vulnerabilities'] = [asdict(v) for v in self.vulnerabilities]
        return result


class CSRFTemplateScanner:
    """Scanner for CSRF security vulnerabilities in templates"""
    
    def __init__(self, templates_dir: str = "templates"):
        """Initialize the CSRF template scanner
        
        Args:
            templates_dir: Directory containing templates to scan
        """
        self.templates_dir = Path(templates_dir)
        self.scan_results: List[TemplateSecurityAuditResult] = []
        
        # Patterns for detecting CSRF implementations
        self.csrf_patterns = {
            'hidden_tag': re.compile(r'{{\s*form\.hidden_tag\(\)\s*}}', re.IGNORECASE),
            'csrf_token_direct': re.compile(r'{{\s*csrf_token\(\)\s*}}', re.IGNORECASE),
            'csrf_meta': re.compile(r'<meta[^>]*name=["\']csrf-token["\'][^>]*>', re.IGNORECASE),
            'form_post': re.compile(r'<form[^>]*method=["\']post["\'][^>]*>', re.IGNORECASE),
            'form_get': re.compile(r'<form[^>]*method=["\']get["\'][^>]*>', re.IGNORECASE),
            'form_any': re.compile(r'<form[^>]*>', re.IGNORECASE),
            'ajax_csrf': re.compile(r'X-CSRFToken["\']?\s*:', re.IGNORECASE),
            'csrf_in_js': re.compile(r'csrf[_-]?token', re.IGNORECASE)
        }
        
        # Security violation patterns
        self.vulnerability_patterns = {
            'exposed_token': re.compile(r'{{\s*csrf_token\(\)\s*}}(?![^<]*<input[^>]*type=["\']hidden["\'])', re.IGNORECASE),
            'missing_csrf_post': re.compile(r'<form[^>]*method=["\']post["\'][^>]*>(?!.*{{\s*(?:form\.hidden_tag\(\)|csrf_token\(\))\s*}})', re.IGNORECASE | re.DOTALL),
            'unnecessary_csrf_get': re.compile(r'<form[^>]*method=["\']get["\'][^>]*>.*?{{\s*(?:form\.hidden_tag\(\)|csrf_token\(\))\s*}}', re.IGNORECASE | re.DOTALL),
            'csrf_in_comment': re.compile(r'<!--.*?csrf.*?-->', re.IGNORECASE | re.DOTALL),
            'csrf_in_script_visible': re.compile(r'<script[^>]*>.*?csrf_token\(\).*?</script>', re.IGNORECASE | re.DOTALL)
        }
    
    def scan_all_templates(self) -> List[TemplateSecurityAuditResult]:
        """Scan all templates for CSRF security issues
        
        Returns:
            List of audit results for all templates
        """
        logger.info(f"Starting CSRF security scan of templates in {self.templates_dir}")
        
        self.scan_results = []
        template_files = self._find_template_files()
        
        for template_file in template_files:
            try:
                result = self.scan_template(template_file)
                self.scan_results.append(result)
                logger.debug(f"Scanned {template_file}: {result.compliance_score:.2f} compliance score")
            except Exception as e:
                logger.error(f"Error scanning template {template_file}: {e}")
                # Create error result
                error_result = TemplateSecurityAuditResult(
                    template_path=str(template_file),
                    csrf_protected=False,
                    csrf_method='error',
                    vulnerabilities=[CSRFVulnerability(
                        type='scan_error',
                        severity='HIGH',
                        description=f"Failed to scan template: {e}"
                    )],
                    recommendations=['Fix template syntax errors and rescan'],
                    compliance_score=0.0,
                    form_count=0,
                    post_form_count=0,
                    get_form_count=0,
                    ajax_endpoints=[],
                    last_audited=datetime.now()
                )
                self.scan_results.append(error_result)
        
        logger.info(f"Completed CSRF security scan: {len(self.scan_results)} templates scanned")
        return self.scan_results
    
    def scan_template(self, template_path: Path) -> TemplateSecurityAuditResult:
        """Scan a single template for CSRF security issues
        
        Args:
            template_path: Path to the template file
            
        Returns:
            Audit result for the template
        """
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Analyze template content
        csrf_method = self._detect_csrf_method(content)
        vulnerabilities = self._detect_vulnerabilities(content, template_path)
        form_counts = self._count_forms(content)
        ajax_endpoints = self._detect_ajax_endpoints(content)
        
        # Determine if template is CSRF protected
        csrf_protected = csrf_method in ['hidden_tag', 'csrf_token_direct'] or len(form_counts['post']) == 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(csrf_method, vulnerabilities, form_counts)
        
        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(csrf_method, vulnerabilities, form_counts)
        
        return TemplateSecurityAuditResult(
            template_path=str(template_path.relative_to(self.templates_dir.parent)),
            csrf_protected=csrf_protected,
            csrf_method=csrf_method,
            vulnerabilities=vulnerabilities,
            recommendations=recommendations,
            compliance_score=compliance_score,
            form_count=len(form_counts['all']),
            post_form_count=len(form_counts['post']),
            get_form_count=len(form_counts['get']),
            ajax_endpoints=ajax_endpoints,
            last_audited=datetime.now()
        )
    
    def _find_template_files(self) -> List[Path]:
        """Find all template files to scan
        
        Returns:
            List of template file paths
        """
        template_files = []
        
        for root, dirs, files in os.walk(self.templates_dir):
            for file in files:
                if file.endswith(('.html', '.htm', '.jinja', '.jinja2')):
                    template_files.append(Path(root) / file)
        
        return sorted(template_files)
    
    def _detect_csrf_method(self, content: str) -> str:
        """Detect the CSRF protection method used in template
        
        Args:
            content: Template content
            
        Returns:
            CSRF method used ('hidden_tag', 'csrf_token_direct', 'meta_only', 'none')
        """
        if self.csrf_patterns['hidden_tag'].search(content):
            return 'hidden_tag'
        elif self.csrf_patterns['csrf_token_direct'].search(content):
            return 'csrf_token_direct'
        elif self.csrf_patterns['csrf_meta'].search(content):
            return 'meta_only'
        else:
            return 'none'
    
    def _detect_vulnerabilities(self, content: str, template_path: Path) -> List[CSRFVulnerability]:
        """Detect CSRF vulnerabilities in template content
        
        Args:
            content: Template content
            template_path: Path to template file
            
        Returns:
            List of detected vulnerabilities
        """
        vulnerabilities = []
        lines = content.split('\n')
        
        # Check for exposed CSRF tokens
        for match in self.vulnerability_patterns['exposed_token'].finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            vulnerabilities.append(CSRFVulnerability(
                type='exposed_csrf_token',
                severity='HIGH',
                description='CSRF token is visible in HTML output instead of being in a hidden field',
                line_number=line_num,
                code_snippet=lines[line_num - 1].strip() if line_num <= len(lines) else None,
                recommendation='Use {{ form.hidden_tag() }} instead of {{ csrf_token() }}'
            ))
        
        # Check for POST forms missing CSRF protection
        post_forms = self.csrf_patterns['form_post'].findall(content)
        csrf_tokens = len(self.csrf_patterns['hidden_tag'].findall(content)) + len(self.csrf_patterns['csrf_token_direct'].findall(content))
        
        if len(post_forms) > csrf_tokens:
            vulnerabilities.append(CSRFVulnerability(
                type='missing_csrf_protection',
                severity='CRITICAL',
                description=f'Found {len(post_forms)} POST forms but only {csrf_tokens} CSRF tokens',
                recommendation='Add {{ form.hidden_tag() }} to all POST forms'
            ))
        
        # Check for unnecessary CSRF tokens in GET forms
        for match in self.vulnerability_patterns['unnecessary_csrf_get'].finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            vulnerabilities.append(CSRFVulnerability(
                type='unnecessary_csrf_token',
                severity='LOW',
                description='CSRF token found in GET form (unnecessary)',
                line_number=line_num,
                recommendation='Remove CSRF token from GET forms as they should be idempotent'
            ))
        
        # Check for CSRF tokens in comments
        for match in self.vulnerability_patterns['csrf_in_comment'].finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            vulnerabilities.append(CSRFVulnerability(
                type='csrf_in_comment',
                severity='MEDIUM',
                description='CSRF token or reference found in HTML comment',
                line_number=line_num,
                recommendation='Remove CSRF references from HTML comments'
            ))
        
        # Check for visible CSRF tokens in JavaScript
        for match in self.vulnerability_patterns['csrf_in_script_visible'].finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            vulnerabilities.append(CSRFVulnerability(
                type='csrf_in_visible_script',
                severity='MEDIUM',
                description='CSRF token directly embedded in visible JavaScript',
                line_number=line_num,
                recommendation='Use meta tag and document.querySelector for CSRF token access'
            ))
        
        return vulnerabilities
    
    def _count_forms(self, content: str) -> Dict[str, List[str]]:
        """Count different types of forms in template
        
        Args:
            content: Template content
            
        Returns:
            Dictionary with form counts by type
        """
        return {
            'all': self.csrf_patterns['form_any'].findall(content),
            'post': self.csrf_patterns['form_post'].findall(content),
            'get': self.csrf_patterns['form_get'].findall(content)
        }
    
    def _detect_ajax_endpoints(self, content: str) -> List[str]:
        """Detect AJAX endpoints that might need CSRF protection
        
        Args:
            content: Template content
            
        Returns:
            List of detected AJAX endpoints
        """
        ajax_endpoints = []
        
        # Look for fetch() calls
        fetch_pattern = re.compile(r'fetch\(["\']([^"\']+)["\']', re.IGNORECASE)
        for match in fetch_pattern.finditer(content):
            endpoint = match.group(1)
            if endpoint.startswith('/'):
                ajax_endpoints.append(endpoint)
        
        # Look for $.post, $.ajax calls
        jquery_patterns = [
            re.compile(r'\$\.post\(["\']([^"\']+)["\']', re.IGNORECASE),
            re.compile(r'\$\.ajax\([^{]*url:\s*["\']([^"\']+)["\']', re.IGNORECASE)
        ]
        
        for pattern in jquery_patterns:
            for match in pattern.finditer(content):
                endpoint = match.group(1)
                if endpoint.startswith('/'):
                    ajax_endpoints.append(endpoint)
        
        return list(set(ajax_endpoints))  # Remove duplicates
    
    def _generate_recommendations(self, csrf_method: str, vulnerabilities: List[CSRFVulnerability], 
                                form_counts: Dict[str, List[str]]) -> List[str]:
        """Generate security recommendations for the template
        
        Args:
            csrf_method: Detected CSRF method
            vulnerabilities: List of vulnerabilities
            form_counts: Form counts by type
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Method-specific recommendations
        if csrf_method == 'none' and len(form_counts['post']) > 0:
            recommendations.append('Add CSRF protection to POST forms using {{ form.hidden_tag() }}')
        elif csrf_method == 'csrf_token_direct':
            recommendations.append('Replace {{ csrf_token() }} with {{ form.hidden_tag() }} to hide tokens')
        elif csrf_method == 'meta_only' and len(form_counts['post']) > 0:
            recommendations.append('Add form-based CSRF protection in addition to meta tag')
        
        # Vulnerability-specific recommendations
        for vuln in vulnerabilities:
            if vuln.recommendation and vuln.recommendation not in recommendations:
                recommendations.append(vuln.recommendation)
        
        # General security recommendations
        if len(form_counts['post']) > 0:
            recommendations.append('Ensure all POST forms validate CSRF tokens on the server side')
        
        if len(form_counts['get']) > 0:
            recommendations.append('Verify GET forms are idempotent and do not change server state')
        
        return recommendations
    
    def _calculate_compliance_score(self, csrf_method: str, vulnerabilities: List[CSRFVulnerability], 
                                  form_counts: Dict[str, List[str]]) -> float:
        """Calculate security compliance score for the template
        
        Args:
            csrf_method: Detected CSRF method
            vulnerabilities: List of vulnerabilities
            form_counts: Form counts by type
            
        Returns:
            Compliance score between 0.0 and 1.0
        """
        score = 1.0
        
        # Deduct points for vulnerabilities
        for vuln in vulnerabilities:
            if vuln.severity == 'CRITICAL':
                score -= 0.4
            elif vuln.severity == 'HIGH':
                score -= 0.2
            elif vuln.severity == 'MEDIUM':
                score -= 0.1
            elif vuln.severity == 'LOW':
                score -= 0.05
        
        # Deduct points for poor CSRF method
        if csrf_method == 'none' and len(form_counts['post']) > 0:
            score -= 0.5
        elif csrf_method == 'csrf_token_direct':
            score -= 0.2
        elif csrf_method == 'meta_only' and len(form_counts['post']) > 0:
            score -= 0.3
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a summary report of all scan results
        
        Returns:
            Summary report dictionary
        """
        if not self.scan_results:
            return {'error': 'No scan results available'}
        
        total_templates = len(self.scan_results)
        protected_templates = sum(1 for r in self.scan_results if r.csrf_protected)
        
        # Vulnerability statistics
        all_vulnerabilities = []
        for result in self.scan_results:
            all_vulnerabilities.extend(result.vulnerabilities)
        
        vuln_by_severity = {}
        vuln_by_type = {}
        
        for vuln in all_vulnerabilities:
            vuln_by_severity[vuln.severity] = vuln_by_severity.get(vuln.severity, 0) + 1
            vuln_by_type[vuln.type] = vuln_by_type.get(vuln.type, 0) + 1
        
        # Compliance statistics
        avg_compliance = sum(r.compliance_score for r in self.scan_results) / total_templates
        high_compliance = sum(1 for r in self.scan_results if r.compliance_score >= 0.8)
        
        # Form statistics
        total_forms = sum(r.form_count for r in self.scan_results)
        total_post_forms = sum(r.post_form_count for r in self.scan_results)
        
        return {
            'scan_summary': {
                'total_templates': total_templates,
                'protected_templates': protected_templates,
                'protection_rate': protected_templates / total_templates if total_templates > 0 else 0,
                'average_compliance_score': avg_compliance,
                'high_compliance_templates': high_compliance,
                'scan_timestamp': datetime.now().isoformat()
            },
            'vulnerability_summary': {
                'total_vulnerabilities': len(all_vulnerabilities),
                'by_severity': vuln_by_severity,
                'by_type': vuln_by_type
            },
            'form_summary': {
                'total_forms': total_forms,
                'post_forms': total_post_forms,
                'get_forms': total_forms - total_post_forms
            },
            'csrf_methods': {
                method: sum(1 for r in self.scan_results if r.csrf_method == method)
                for method in ['hidden_tag', 'csrf_token_direct', 'meta_only', 'none', 'error']
            },
            'top_vulnerabilities': sorted(
                [(vuln_type, count) for vuln_type, count in vuln_by_type.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def save_results(self, output_file: str) -> None:
        """Save scan results to JSON file
        
        Args:
            output_file: Path to output file
        """
        results_data = {
            'scan_metadata': {
                'scan_timestamp': datetime.now().isoformat(),
                'templates_directory': str(self.templates_dir),
                'total_templates_scanned': len(self.scan_results)
            },
            'summary': self.generate_summary_report(),
            'detailed_results': [result.to_dict() for result in self.scan_results]
        }
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"CSRF security scan results saved to {output_file}")


def main():
    """Main function for running CSRF template scanner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CSRF Template Security Scanner')
    parser.add_argument('--templates-dir', default='templates', 
                       help='Directory containing templates to scan')
    parser.add_argument('--output', default='security/reports/csrf_template_audit.json',
                       help='Output file for scan results')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run the scan
    scanner = CSRFTemplateScanner(args.templates_dir)
    results = scanner.scan_all_templates()
    
    # Save results
    scanner.save_results(args.output)
    
    # Print summary
    summary = scanner.generate_summary_report()
    print(f"\nCSRF Template Security Scan Complete!")
    print(f"Templates scanned: {summary['scan_summary']['total_templates']}")
    print(f"Protected templates: {summary['scan_summary']['protected_templates']}")
    print(f"Protection rate: {summary['scan_summary']['protection_rate']:.1%}")
    print(f"Average compliance score: {summary['scan_summary']['average_compliance_score']:.2f}")
    print(f"Total vulnerabilities: {summary['vulnerability_summary']['total_vulnerabilities']}")
    
    if summary['vulnerability_summary']['total_vulnerabilities'] > 0:
        print("\nTop vulnerabilities:")
        for vuln_type, count in summary['top_vulnerabilities']:
            print(f"  {vuln_type}: {count}")


if __name__ == '__main__':
    main()