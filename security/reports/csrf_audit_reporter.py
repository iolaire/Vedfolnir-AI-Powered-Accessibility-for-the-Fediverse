# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Security Audit Reporter

Generates comprehensive reports for CSRF security audits, including
compliance tracking, vulnerability analysis, and remediation guidance.
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class ComplianceReport:
    """CSRF compliance report data"""
    overall_score: float
    total_templates: int
    compliant_templates: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    recommendations: List[str]
    generated_at: datetime

class CSRFAuditReporter:
    """Generates comprehensive CSRF security audit reports"""
    
    def __init__(self, reports_dir: str = "security/reports"):
        """Initialize the CSRF audit reporter
        
        Args:
            reports_dir: Directory to store generated reports
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_comprehensive_report(self, scan_results_file: str) -> Dict[str, Any]:
        """Generate a comprehensive CSRF security audit report
        
        Args:
            scan_results_file: Path to scan results JSON file
            
        Returns:
            Comprehensive report dictionary
        """
        logger.info(f"Generating comprehensive CSRF audit report from {scan_results_file}")
        
        # Load scan results
        with open(scan_results_file, 'r', encoding='utf-8') as f:
            scan_data = json.load(f)
        
        # Extract data
        summary = scan_data.get('summary', {})
        detailed_results = scan_data.get('detailed_results', [])
        
        # Generate report sections
        report = {
            'report_metadata': {
                'report_type': 'CSRF Security Audit',
                'generated_at': datetime.now().isoformat(),
                'scan_timestamp': scan_data.get('scan_metadata', {}).get('scan_timestamp'),
                'templates_scanned': len(detailed_results),
                'report_version': '1.0'
            },
            'executive_summary': self._generate_executive_summary(summary, detailed_results),
            'compliance_analysis': self._generate_compliance_analysis(summary, detailed_results),
            'vulnerability_analysis': self._generate_vulnerability_analysis(summary, detailed_results),
            'template_analysis': self._generate_template_analysis(detailed_results),
            'remediation_plan': self._generate_remediation_plan(detailed_results),
            'security_metrics': self._generate_security_metrics(summary, detailed_results),
            'recommendations': self._generate_recommendations(summary, detailed_results),
            'appendix': self._generate_appendix(detailed_results)
        }
        
        # Save comprehensive report
        report_file = self.reports_dir / f"csrf_comprehensive_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Generate markdown report
        self._generate_markdown_report(report, report_file.with_suffix('.md'))
        
        logger.info(f"Comprehensive CSRF audit report generated: {report_file}")
        return report
    
    def _generate_executive_summary(self, summary: Dict[str, Any], detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate executive summary section"""
        scan_summary = summary.get('scan_summary', {})
        vuln_summary = summary.get('vulnerability_summary', {})
        
        # Calculate risk level
        critical_vulns = vuln_summary.get('by_severity', {}).get('CRITICAL', 0)
        high_vulns = vuln_summary.get('by_severity', {}).get('HIGH', 0)
        
        if critical_vulns > 0:
            risk_level = 'CRITICAL'
        elif high_vulns > 0:
            risk_level = 'HIGH'
        elif vuln_summary.get('total_vulnerabilities', 0) > 0:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        # Key findings
        key_findings = []
        
        protection_rate = scan_summary.get('protection_rate', 0)
        if protection_rate < 0.8:
            key_findings.append(f"Only {protection_rate:.1%} of templates have CSRF protection")
        
        avg_compliance = scan_summary.get('average_compliance_score', 0)
        if avg_compliance < 0.7:
            key_findings.append(f"Average compliance score is low: {avg_compliance:.2f}")
        
        if critical_vulns > 0:
            key_findings.append(f"{critical_vulns} critical CSRF vulnerabilities found")
        
        if high_vulns > 0:
            key_findings.append(f"{high_vulns} high-severity CSRF vulnerabilities found")
        
        return {
            'overall_risk_level': risk_level,
            'protection_rate': protection_rate,
            'average_compliance_score': avg_compliance,
            'total_vulnerabilities': vuln_summary.get('total_vulnerabilities', 0),
            'key_findings': key_findings,
            'immediate_actions_required': critical_vulns > 0 or high_vulns > 0,
            'templates_requiring_attention': sum(1 for r in detailed_results if r.get('compliance_score', 1) < 0.7)
        }
    
    def _generate_compliance_analysis(self, summary: Dict[str, Any], detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate compliance analysis section"""
        scan_summary = summary.get('scan_summary', {})
        
        # Compliance score distribution
        score_ranges = {
            'excellent': (0.9, 1.0),
            'good': (0.7, 0.9),
            'fair': (0.5, 0.7),
            'poor': (0.0, 0.5)
        }
        
        score_distribution = {}
        for range_name, (min_score, max_score) in score_ranges.items():
            count = sum(1 for r in detailed_results 
                       if min_score <= r.get('compliance_score', 0) < max_score)
            score_distribution[range_name] = count
        
        # CSRF method distribution
        csrf_methods = summary.get('csrf_methods', {})
        
        # Compliance trends (if historical data available)
        compliance_trends = {
            'current_score': scan_summary.get('average_compliance_score', 0),
            'target_score': 0.9,
            'improvement_needed': max(0, 0.9 - scan_summary.get('average_compliance_score', 0))
        }
        
        return {
            'overall_compliance_score': scan_summary.get('average_compliance_score', 0),
            'compliance_target': 0.9,
            'templates_meeting_target': scan_summary.get('high_compliance_templates', 0),
            'score_distribution': score_distribution,
            'csrf_method_distribution': csrf_methods,
            'compliance_trends': compliance_trends,
            'compliance_gaps': self._identify_compliance_gaps(detailed_results)
        }
    
    def _generate_vulnerability_analysis(self, summary: Dict[str, Any], detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate vulnerability analysis section"""
        vuln_summary = summary.get('vulnerability_summary', {})
        
        # Vulnerability details by type
        vuln_details = {}
        for result in detailed_results:
            for vuln in result.get('vulnerabilities', []):
                vuln_type = vuln.get('type', 'unknown')
                if vuln_type not in vuln_details:
                    vuln_details[vuln_type] = {
                        'count': 0,
                        'severity_distribution': {},
                        'affected_templates': [],
                        'description': vuln.get('description', ''),
                        'recommendation': vuln.get('recommendation', '')
                    }
                
                vuln_details[vuln_type]['count'] += 1
                severity = vuln.get('severity', 'UNKNOWN')
                vuln_details[vuln_type]['severity_distribution'][severity] = \
                    vuln_details[vuln_type]['severity_distribution'].get(severity, 0) + 1
                
                template_path = result.get('template_path', 'unknown')
                if template_path not in vuln_details[vuln_type]['affected_templates']:
                    vuln_details[vuln_type]['affected_templates'].append(template_path)
        
        # Risk assessment
        total_vulns = vuln_summary.get('total_vulnerabilities', 0)
        critical_vulns = vuln_summary.get('by_severity', {}).get('CRITICAL', 0)
        high_vulns = vuln_summary.get('by_severity', {}).get('HIGH', 0)
        
        risk_score = (critical_vulns * 4 + high_vulns * 2 + 
                     vuln_summary.get('by_severity', {}).get('MEDIUM', 0) * 1 +
                     vuln_summary.get('by_severity', {}).get('LOW', 0) * 0.5)
        
        return {
            'total_vulnerabilities': total_vulns,
            'severity_distribution': vuln_summary.get('by_severity', {}),
            'vulnerability_types': vuln_details,
            'risk_score': risk_score,
            'most_common_vulnerabilities': summary.get('top_vulnerabilities', []),
            'vulnerability_trends': self._analyze_vulnerability_trends(detailed_results),
            'remediation_priority': self._prioritize_vulnerabilities(vuln_details)
        }
    
    def _generate_template_analysis(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate template-specific analysis"""
        # Templates by compliance score
        templates_by_score = sorted(detailed_results, key=lambda x: x.get('compliance_score', 0))
        
        # Most problematic templates
        problematic_templates = [
            {
                'template_path': r.get('template_path', 'unknown'),
                'compliance_score': r.get('compliance_score', 0),
                'vulnerability_count': len(r.get('vulnerabilities', [])),
                'csrf_method': r.get('csrf_method', 'none'),
                'form_count': r.get('form_count', 0),
                'post_form_count': r.get('post_form_count', 0)
            }
            for r in templates_by_score[:10]  # Top 10 most problematic
        ]
        
        # Best practice examples
        best_practice_templates = [
            {
                'template_path': r.get('template_path', 'unknown'),
                'compliance_score': r.get('compliance_score', 0),
                'csrf_method': r.get('csrf_method', 'none')
            }
            for r in sorted(detailed_results, key=lambda x: x.get('compliance_score', 0), reverse=True)[:5]
            if r.get('compliance_score', 0) >= 0.9
        ]
        
        # Template categories
        template_categories = {
            'admin_templates': [r for r in detailed_results if 'admin' in r.get('template_path', '').lower()],
            'form_templates': [r for r in detailed_results if r.get('post_form_count', 0) > 0],
            'ajax_templates': [r for r in detailed_results if len(r.get('ajax_endpoints', [])) > 0],
            'public_templates': [r for r in detailed_results if 'login' in r.get('template_path', '').lower() or 'public' in r.get('template_path', '').lower()]
        }
        
        return {
            'total_templates_analyzed': len(detailed_results),
            'problematic_templates': problematic_templates,
            'best_practice_templates': best_practice_templates,
            'template_categories': {
                category: {
                    'count': len(templates),
                    'average_compliance': sum(t.get('compliance_score', 0) for t in templates) / len(templates) if templates else 0,
                    'vulnerability_count': sum(len(t.get('vulnerabilities', [])) for t in templates)
                }
                for category, templates in template_categories.items()
            },
            'form_analysis': self._analyze_forms(detailed_results),
            'ajax_analysis': self._analyze_ajax_usage(detailed_results)
        }
    
    def _generate_remediation_plan(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate remediation plan"""
        # Prioritize fixes by impact and effort
        remediation_tasks = []
        
        for result in detailed_results:
            template_path = result.get('template_path', 'unknown')
            compliance_score = result.get('compliance_score', 0)
            vulnerabilities = result.get('vulnerabilities', [])
            
            if compliance_score < 0.7 or vulnerabilities:
                # Determine effort level
                effort_level = 'LOW'
                if len(vulnerabilities) > 3:
                    effort_level = 'HIGH'
                elif len(vulnerabilities) > 1:
                    effort_level = 'MEDIUM'
                
                # Determine impact
                impact_level = 'LOW'
                for vuln in vulnerabilities:
                    if vuln.get('severity') == 'CRITICAL':
                        impact_level = 'CRITICAL'
                        break
                    elif vuln.get('severity') == 'HIGH':
                        impact_level = 'HIGH'
                
                remediation_tasks.append({
                    'template_path': template_path,
                    'priority': self._calculate_priority(impact_level, effort_level),
                    'impact_level': impact_level,
                    'effort_level': effort_level,
                    'vulnerabilities': len(vulnerabilities),
                    'current_score': compliance_score,
                    'target_score': 0.9,
                    'specific_actions': result.get('recommendations', [])
                })
        
        # Sort by priority
        remediation_tasks.sort(key=lambda x: x['priority'], reverse=True)
        
        # Group by phases
        phases = {
            'immediate': [t for t in remediation_tasks if t['impact_level'] in ['CRITICAL', 'HIGH']],
            'short_term': [t for t in remediation_tasks if t['impact_level'] == 'MEDIUM'],
            'long_term': [t for t in remediation_tasks if t['impact_level'] == 'LOW']
        }
        
        return {
            'total_remediation_tasks': len(remediation_tasks),
            'remediation_phases': phases,
            'estimated_effort': self._estimate_total_effort(remediation_tasks),
            'quick_wins': [t for t in remediation_tasks if t['effort_level'] == 'LOW' and t['impact_level'] in ['HIGH', 'MEDIUM']],
            'implementation_timeline': self._generate_implementation_timeline(phases)
        }
    
    def _generate_security_metrics(self, summary: Dict[str, Any], detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate security metrics"""
        scan_summary = summary.get('scan_summary', {})
        vuln_summary = summary.get('vulnerability_summary', {})
        
        return {
            'protection_coverage': {
                'total_templates': scan_summary.get('total_templates', 0),
                'protected_templates': scan_summary.get('protected_templates', 0),
                'protection_rate': scan_summary.get('protection_rate', 0),
                'unprotected_templates': scan_summary.get('total_templates', 0) - scan_summary.get('protected_templates', 0)
            },
            'vulnerability_metrics': {
                'total_vulnerabilities': vuln_summary.get('total_vulnerabilities', 0),
                'vulnerabilities_per_template': vuln_summary.get('total_vulnerabilities', 0) / max(1, scan_summary.get('total_templates', 1)),
                'critical_vulnerability_rate': vuln_summary.get('by_severity', {}).get('CRITICAL', 0) / max(1, scan_summary.get('total_templates', 1)),
                'high_vulnerability_rate': vuln_summary.get('by_severity', {}).get('HIGH', 0) / max(1, scan_summary.get('total_templates', 1))
            },
            'compliance_metrics': {
                'average_compliance_score': scan_summary.get('average_compliance_score', 0),
                'high_compliance_templates': scan_summary.get('high_compliance_templates', 0),
                'compliance_rate': scan_summary.get('high_compliance_templates', 0) / max(1, scan_summary.get('total_templates', 1)),
                'compliance_gap': max(0, 0.9 - scan_summary.get('average_compliance_score', 0))
            },
            'form_security_metrics': {
                'total_forms': summary.get('form_summary', {}).get('total_forms', 0),
                'post_forms': summary.get('form_summary', {}).get('post_forms', 0),
                'get_forms': summary.get('form_summary', {}).get('get_forms', 0),
                'forms_per_template': summary.get('form_summary', {}).get('total_forms', 0) / max(1, scan_summary.get('total_templates', 1))
            }
        }
    
    def _generate_recommendations(self, summary: Dict[str, Any], detailed_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate security recommendations"""
        recommendations = []
        
        scan_summary = summary.get('scan_summary', {})
        vuln_summary = summary.get('vulnerability_summary', {})
        
        # High-level recommendations
        if scan_summary.get('protection_rate', 0) < 0.8:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'CSRF Protection',
                'title': 'Implement CSRF Protection for All POST Forms',
                'description': f"Only {scan_summary.get('protection_rate', 0):.1%} of templates have CSRF protection. All POST forms should include CSRF tokens.",
                'implementation': 'Add {{ form.hidden_tag() }} to all POST forms',
                'impact': 'Prevents CSRF attacks on state-changing operations'
            })
        
        if vuln_summary.get('by_severity', {}).get('CRITICAL', 0) > 0:
            recommendations.append({
                'priority': 'CRITICAL',
                'category': 'Vulnerability Remediation',
                'title': 'Fix Critical CSRF Vulnerabilities',
                'description': f"Found {vuln_summary.get('by_severity', {}).get('CRITICAL', 0)} critical CSRF vulnerabilities that need immediate attention.",
                'implementation': 'Review and fix all critical vulnerabilities listed in the detailed analysis',
                'impact': 'Eliminates high-risk security vulnerabilities'
            })
        
        # Method-specific recommendations
        csrf_methods = summary.get('csrf_methods', {})
        if csrf_methods.get('csrf_token_direct', 0) > 0:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Implementation Standards',
                'title': 'Standardize CSRF Token Implementation',
                'description': f"Found {csrf_methods.get('csrf_token_direct', 0)} templates using {{ csrf_token() }} directly, which exposes tokens in HTML.",
                'implementation': 'Replace {{ csrf_token() }} with {{ form.hidden_tag() }}',
                'impact': 'Improves security by hiding CSRF tokens from HTML source'
            })
        
        if csrf_methods.get('none', 0) > 0:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'CSRF Protection',
                'title': 'Add CSRF Protection to Unprotected Templates',
                'description': f"Found {csrf_methods.get('none', 0)} templates with no CSRF protection.",
                'implementation': 'Add appropriate CSRF protection based on template functionality',
                'impact': 'Provides comprehensive CSRF protection across the application'
            })
        
        # Compliance recommendations
        if scan_summary.get('average_compliance_score', 0) < 0.8:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Compliance',
                'title': 'Improve Overall Security Compliance',
                'description': f"Average compliance score is {scan_summary.get('average_compliance_score', 0):.2f}, below the target of 0.9.",
                'implementation': 'Follow the remediation plan to address identified issues',
                'impact': 'Achieves security compliance standards'
            })
        
        return recommendations
    
    def _generate_appendix(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate appendix with detailed data"""
        return {
            'detailed_template_results': detailed_results,
            'vulnerability_reference': self._generate_vulnerability_reference(),
            'csrf_implementation_guide': self._generate_implementation_guide(),
            'testing_recommendations': self._generate_testing_recommendations()
        }
    
    def _generate_markdown_report(self, report: Dict[str, Any], output_file: Path) -> None:
        """Generate markdown version of the report"""
        md_content = self._format_report_as_markdown(report)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Markdown report generated: {output_file}")
    
    def _format_report_as_markdown(self, report: Dict[str, Any]) -> str:
        """Format report as markdown"""
        md = []
        
        # Title and metadata
        metadata = report.get('report_metadata', {})
        md.append(f"# {metadata.get('report_type', 'CSRF Security Audit Report')}")
        md.append(f"**Generated:** {metadata.get('generated_at', 'Unknown')}")
        md.append(f"**Templates Scanned:** {metadata.get('templates_scanned', 0)}")
        md.append("")
        
        # Executive Summary
        exec_summary = report.get('executive_summary', {})
        md.append("## Executive Summary")
        md.append(f"**Overall Risk Level:** {exec_summary.get('overall_risk_level', 'Unknown')}")
        md.append(f"**Protection Rate:** {exec_summary.get('protection_rate', 0):.1%}")
        md.append(f"**Average Compliance Score:** {exec_summary.get('average_compliance_score', 0):.2f}")
        md.append(f"**Total Vulnerabilities:** {exec_summary.get('total_vulnerabilities', 0)}")
        md.append("")
        
        if exec_summary.get('key_findings'):
            md.append("### Key Findings")
            for finding in exec_summary.get('key_findings', []):
                md.append(f"- {finding}")
            md.append("")
        
        # Vulnerability Analysis
        vuln_analysis = report.get('vulnerability_analysis', {})
        md.append("## Vulnerability Analysis")
        
        severity_dist = vuln_analysis.get('severity_distribution', {})
        if severity_dist:
            md.append("### Vulnerabilities by Severity")
            for severity, count in severity_dist.items():
                md.append(f"- **{severity}:** {count}")
            md.append("")
        
        # Most Common Vulnerabilities
        common_vulns = vuln_analysis.get('most_common_vulnerabilities', [])
        if common_vulns:
            md.append("### Most Common Vulnerabilities")
            for vuln_type, count in common_vulns:
                md.append(f"- {vuln_type}: {count}")
            md.append("")
        
        # Recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            md.append("## Recommendations")
            for rec in recommendations:
                md.append(f"### {rec.get('title', 'Recommendation')}")
                md.append(f"**Priority:** {rec.get('priority', 'Unknown')}")
                md.append(f"**Category:** {rec.get('category', 'Unknown')}")
                md.append(f"{rec.get('description', '')}")
                md.append(f"**Implementation:** {rec.get('implementation', '')}")
                md.append("")
        
        # Remediation Plan
        remediation = report.get('remediation_plan', {})
        phases = remediation.get('remediation_phases', {})
        if phases:
            md.append("## Remediation Plan")
            for phase_name, tasks in phases.items():
                if tasks:
                    md.append(f"### {phase_name.replace('_', ' ').title()} ({len(tasks)} tasks)")
                    for task in tasks[:5]:  # Show top 5 tasks per phase
                        md.append(f"- {task.get('template_path', 'Unknown')} (Score: {task.get('current_score', 0):.2f})")
                    md.append("")
        
        return "\n".join(md)
    
    # Helper methods for analysis
    def _identify_compliance_gaps(self, detailed_results: List[Dict[str, Any]]) -> List[str]:
        """Identify compliance gaps"""
        gaps = []
        
        low_compliance = [r for r in detailed_results if r.get('compliance_score', 0) < 0.7]
        if low_compliance:
            gaps.append(f"{len(low_compliance)} templates below compliance threshold")
        
        no_csrf = [r for r in detailed_results if r.get('csrf_method') == 'none' and r.get('post_form_count', 0) > 0]
        if no_csrf:
            gaps.append(f"{len(no_csrf)} POST forms without CSRF protection")
        
        return gaps
    
    def _analyze_vulnerability_trends(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze vulnerability trends"""
        # This would be more meaningful with historical data
        return {
            'trend_analysis': 'Historical data needed for trend analysis',
            'current_snapshot': {
                'templates_with_vulnerabilities': sum(1 for r in detailed_results if r.get('vulnerabilities')),
                'average_vulnerabilities_per_template': sum(len(r.get('vulnerabilities', [])) for r in detailed_results) / len(detailed_results) if detailed_results else 0
            }
        }
    
    def _prioritize_vulnerabilities(self, vuln_details: Dict[str, Any]) -> List[Dict[str, str]]:
        """Prioritize vulnerabilities for remediation"""
        priority_list = []
        
        for vuln_type, details in vuln_details.items():
            severity_dist = details.get('severity_distribution', {})
            critical_count = severity_dist.get('CRITICAL', 0)
            high_count = severity_dist.get('HIGH', 0)
            
            if critical_count > 0:
                priority = 'CRITICAL'
            elif high_count > 0:
                priority = 'HIGH'
            else:
                priority = 'MEDIUM'
            
            priority_list.append({
                'vulnerability_type': vuln_type,
                'priority': priority,
                'count': details.get('count', 0),
                'affected_templates': len(details.get('affected_templates', []))
            })
        
        return sorted(priority_list, key=lambda x: (x['priority'] == 'CRITICAL', x['priority'] == 'HIGH', x['count']), reverse=True)
    
    def _analyze_forms(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze form usage across templates"""
        total_forms = sum(r.get('form_count', 0) for r in detailed_results)
        total_post_forms = sum(r.get('post_form_count', 0) for r in detailed_results)
        
        return {
            'total_forms': total_forms,
            'post_forms': total_post_forms,
            'get_forms': total_forms - total_post_forms,
            'templates_with_forms': sum(1 for r in detailed_results if r.get('form_count', 0) > 0),
            'templates_with_post_forms': sum(1 for r in detailed_results if r.get('post_form_count', 0) > 0),
            'average_forms_per_template': total_forms / len(detailed_results) if detailed_results else 0
        }
    
    def _analyze_ajax_usage(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze AJAX usage across templates"""
        templates_with_ajax = [r for r in detailed_results if r.get('ajax_endpoints')]
        total_ajax_endpoints = sum(len(r.get('ajax_endpoints', [])) for r in detailed_results)
        
        return {
            'templates_with_ajax': len(templates_with_ajax),
            'total_ajax_endpoints': total_ajax_endpoints,
            'average_ajax_per_template': total_ajax_endpoints / len(detailed_results) if detailed_results else 0,
            'ajax_usage_rate': len(templates_with_ajax) / len(detailed_results) if detailed_results else 0
        }
    
    def _calculate_priority(self, impact_level: str, effort_level: str) -> int:
        """Calculate priority score for remediation tasks"""
        impact_scores = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        effort_scores = {'LOW': 3, 'MEDIUM': 2, 'HIGH': 1}  # Lower effort = higher priority
        
        return impact_scores.get(impact_level, 1) * effort_scores.get(effort_level, 1)
    
    def _estimate_total_effort(self, remediation_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate total effort for remediation"""
        effort_mapping = {'LOW': 1, 'MEDIUM': 3, 'HIGH': 8}  # Story points
        
        total_effort = sum(effort_mapping.get(task.get('effort_level', 'MEDIUM'), 3) for task in remediation_tasks)
        
        return {
            'total_story_points': total_effort,
            'estimated_days': total_effort * 0.5,  # Assuming 2 story points per day
            'effort_by_level': {
                level: sum(1 for task in remediation_tasks if task.get('effort_level') == level)
                for level in ['LOW', 'MEDIUM', 'HIGH']
            }
        }
    
    def _generate_implementation_timeline(self, phases: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
        """Generate implementation timeline"""
        return {
            'immediate': 'Week 1-2: Address critical and high-severity vulnerabilities',
            'short_term': 'Week 3-6: Implement medium-priority fixes and improvements',
            'long_term': 'Month 2-3: Complete remaining improvements and establish monitoring'
        }
    
    def _generate_vulnerability_reference(self) -> Dict[str, Dict[str, str]]:
        """Generate vulnerability reference guide"""
        return {
            'exposed_csrf_token': {
                'description': 'CSRF token visible in HTML source code',
                'risk': 'HIGH - Token can be extracted by malicious scripts',
                'fix': 'Use {{ form.hidden_tag() }} instead of {{ csrf_token() }}'
            },
            'missing_csrf_protection': {
                'description': 'POST form without CSRF token',
                'risk': 'CRITICAL - Form vulnerable to CSRF attacks',
                'fix': 'Add {{ form.hidden_tag() }} to all POST forms'
            },
            'unnecessary_csrf_token': {
                'description': 'CSRF token in GET form',
                'risk': 'LOW - Unnecessary complexity, GET should be idempotent',
                'fix': 'Remove CSRF token from GET forms'
            },
            'csrf_in_comment': {
                'description': 'CSRF token reference in HTML comment',
                'risk': 'MEDIUM - Information disclosure',
                'fix': 'Remove CSRF references from HTML comments'
            }
        }
    
    def _generate_implementation_guide(self) -> Dict[str, str]:
        """Generate CSRF implementation guide"""
        return {
            'best_practices': 'Always use {{ form.hidden_tag() }} for POST forms',
            'ajax_implementation': 'Use meta tag and X-CSRFToken header for AJAX requests',
            'validation': 'Ensure server-side CSRF validation is enabled',
            'testing': 'Test CSRF protection with automated security tests'
        }
    
    def _generate_testing_recommendations(self) -> List[str]:
        """Generate testing recommendations"""
        return [
            'Implement automated CSRF protection tests',
            'Test form submissions without CSRF tokens (should fail)',
            'Test AJAX requests with and without CSRF tokens',
            'Verify CSRF tokens are not visible in HTML source',
            'Test CSRF token expiration and refresh functionality'
        ]

def main():
    """Main function for generating CSRF audit reports"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CSRF Security Audit Reporter')
    parser.add_argument('--scan-results', required=True,
                       help='Path to scan results JSON file')
    parser.add_argument('--output-dir', default='security/reports',
                       help='Output directory for reports')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Generate report
    reporter = CSRFAuditReporter(args.output_dir)
    report = reporter.generate_comprehensive_report(args.scan_results)
    
    print(f"\nCSRF Security Audit Report Generated!")
    print(f"Overall Risk Level: {report['executive_summary']['overall_risk_level']}")
    print(f"Protection Rate: {report['executive_summary']['protection_rate']:.1%}")
    print(f"Total Vulnerabilities: {report['executive_summary']['total_vulnerabilities']}")

if __name__ == '__main__':
    main()