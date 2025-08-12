# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Compliance Validator

Compliance scoring system, automated security audit reports,
and continuous integration security checks for CSRF compliance.
"""

import json
import csv
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import statistics

from security.audit.csrf_template_scanner import CSRFAuditResult, TemplateSecurityIssue

logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """CSRF compliance levels"""
    EXCELLENT = "excellent"      # 90-100%
    GOOD = "good"               # 70-89%
    NEEDS_IMPROVEMENT = "needs_improvement"  # 50-69%
    POOR = "poor"               # 0-49%


@dataclass
class ComplianceReport:
    """Comprehensive compliance report"""
    metadata: Dict[str, Any]
    summary: Dict[str, Any]
    compliance_levels: Dict[str, int]
    issues_analysis: Dict[str, Any]
    recommendations: List[str]
    templates: List[Dict[str, Any]]
    trends: Optional[Dict[str, Any]] = None


class CSRFComplianceValidator:
    """Validates CSRF compliance and generates scores"""
    
    def __init__(self):
        """Initialize compliance validator"""
        self.compliance_thresholds = {
            ComplianceLevel.EXCELLENT: 0.9,
            ComplianceLevel.GOOD: 0.7,
            ComplianceLevel.NEEDS_IMPROVEMENT: 0.5,
            ComplianceLevel.POOR: 0.0
        }
        
        self.severity_weights = {
            'CRITICAL': 0.4,
            'HIGH': 0.2,
            'MEDIUM': 0.1,
            'LOW': 0.05
        }
    
    def classify_compliance_level(self, score: float) -> ComplianceLevel:
        """Classify compliance level based on score
        
        Args:
            score: Compliance score (0.0 to 1.0)
            
        Returns:
            ComplianceLevel enum
        """
        if score >= self.compliance_thresholds[ComplianceLevel.EXCELLENT]:
            return ComplianceLevel.EXCELLENT
        elif score >= self.compliance_thresholds[ComplianceLevel.GOOD]:
            return ComplianceLevel.GOOD
        elif score >= self.compliance_thresholds[ComplianceLevel.NEEDS_IMPROVEMENT]:
            return ComplianceLevel.NEEDS_IMPROVEMENT
        else:
            return ComplianceLevel.POOR
    
    def calculate_overall_compliance(self, results: List[CSRFAuditResult]) -> float:
        """Calculate overall compliance score
        
        Args:
            results: List of CSRF audit results
            
        Returns:
            Overall compliance score (0.0 to 1.0)
        """
        if not results:
            return 1.0
        
        # Filter results with forms (templates without forms are not relevant)
        form_results = [r for r in results if r.has_forms]
        
        if not form_results:
            return 1.0
        
        # Calculate weighted average based on template importance
        total_score = 0.0
        total_weight = 0.0
        
        for result in form_results:
            # Weight templates based on criticality (admin templates are more important)
            weight = self._calculate_template_weight(result.template_path)
            total_score += result.compliance_score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_template_weight(self, template_path: str) -> float:
        """Calculate template weight based on criticality
        
        Args:
            template_path: Path to template
            
        Returns:
            Weight factor (higher = more critical)
        """
        path_lower = template_path.lower()
        
        # Critical templates (admin, login, etc.)
        if any(keyword in path_lower for keyword in ['admin', 'login', 'auth', 'user_management']):
            return 2.0
        
        # Important templates (forms, management)
        if any(keyword in path_lower for keyword in ['form', 'management', 'profile', 'settings']):
            return 1.5
        
        # Standard templates
        return 1.0
    
    def validate_compliance_thresholds(self, results: List[CSRFAuditResult], 
                                     thresholds: Dict[str, Any]) -> Dict[str, Any]:
        """Validate compliance against defined thresholds
        
        Args:
            results: List of CSRF audit results
            thresholds: Compliance thresholds configuration
            
        Returns:
            Validation result with pass/fail status
        """
        violations = []
        
        # Check minimum compliance score
        overall_score = self.calculate_overall_compliance(results)
        min_score = thresholds.get('minimum_score', 0.8)
        
        if overall_score < min_score:
            violations.append(f"Overall compliance score {overall_score:.2f} below minimum {min_score}")
        
        # Count issues by severity
        issue_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for result in results:
            for issue in result.issues:
                issue_counts[issue.severity] += 1
        
        # Check issue thresholds
        for severity, count in issue_counts.items():
            threshold_key = f'{severity.lower()}_issues'
            max_allowed = thresholds.get(threshold_key, float('inf'))
            
            if count > max_allowed:
                violations.append(f"{count} {severity} issues exceed maximum {max_allowed}")
        
        # Check protected forms percentage
        form_results = [r for r in results if r.has_forms]
        if form_results:
            protected_count = len([r for r in form_results if r.csrf_protected])
            protection_rate = protected_count / len(form_results) * 100
            min_protection = thresholds.get('protected_forms_percentage', 100)
            
            if protection_rate < min_protection:
                violations.append(f"Only {protection_rate:.1f}% of forms protected, minimum {min_protection}%")
        
        return {
            'passes': len(violations) == 0,
            'overall_score': overall_score,
            'violations': violations,
            'issue_counts': issue_counts,
            'protection_rate': protection_rate if form_results else 100.0
        }
    
    def analyze_compliance_trends(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze compliance trends over time
        
        Args:
            historical_data: List of historical compliance data points
            
        Returns:
            Trend analysis results
        """
        if len(historical_data) < 2:
            return {'trend_direction': 'insufficient_data'}
        
        # Sort by date
        sorted_data = sorted(historical_data, key=lambda x: x['date'])
        
        # Calculate trend direction
        scores = [data['score'] for data in sorted_data]
        issues = [data['issues'] for data in sorted_data]
        
        # Linear regression for trend
        n = len(scores)
        x_values = list(range(n))
        
        # Calculate slope for scores
        score_slope = self._calculate_slope(x_values, scores)
        issue_slope = self._calculate_slope(x_values, issues)
        
        # Determine trend direction
        if score_slope > 0.01:
            trend_direction = 'improving'
        elif score_slope < -0.01:
            trend_direction = 'declining'
        else:
            trend_direction = 'stable'
        
        # Calculate improvement rates
        first_score = scores[0]
        last_score = scores[-1]
        improvement_rate = (last_score - first_score) / first_score if first_score > 0 else 0
        
        first_issues = issues[0]
        last_issues = issues[-1]
        issue_reduction_rate = (first_issues - last_issues) / first_issues if first_issues > 0 else 0
        
        return {
            'trend_direction': trend_direction,
            'improvement_rate': improvement_rate,
            'issue_reduction_rate': issue_reduction_rate,
            'score_slope': score_slope,
            'issue_slope': issue_slope,
            'data_points': n,
            'time_span_days': (datetime.fromisoformat(sorted_data[-1]['date']) - 
                              datetime.fromisoformat(sorted_data[0]['date'])).days
        }
    
    def _calculate_slope(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate slope using linear regression
        
        Args:
            x_values: X coordinates
            y_values: Y coordinates
            
        Returns:
            Slope value
        """
        n = len(x_values)
        if n < 2:
            return 0.0
        
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def assess_security_risk(self, results: List[CSRFAuditResult]) -> Dict[str, Any]:
        """Assess overall security risk based on audit results
        
        Args:
            results: List of CSRF audit results
            
        Returns:
            Risk assessment results
        """
        # Calculate risk factors
        critical_templates = []
        high_risk_templates = []
        total_critical_issues = 0
        total_high_issues = 0
        
        for result in results:
            critical_issues = [i for i in result.issues if i.severity == 'CRITICAL']
            high_issues = [i for i in result.issues if i.severity == 'HIGH']
            
            total_critical_issues += len(critical_issues)
            total_high_issues += len(high_issues)
            
            if critical_issues:
                critical_templates.append({
                    'template': result.template_path,
                    'score': result.compliance_score,
                    'critical_issues': len(critical_issues)
                })
            elif result.compliance_score < 0.5:
                high_risk_templates.append({
                    'template': result.template_path,
                    'score': result.compliance_score,
                    'issues': len(result.issues)
                })
        
        # Calculate overall risk score
        overall_score = self.calculate_overall_compliance(results)
        risk_score = 1.0 - overall_score
        
        # Add penalty for critical issues
        risk_score += total_critical_issues * 0.2
        risk_score += total_high_issues * 0.1
        
        # Determine risk level
        if risk_score >= 0.7 or total_critical_issues > 0:
            risk_level = 'HIGH'
        elif risk_score >= 0.4 or total_high_issues > 2:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        # Generate immediate actions
        immediate_actions = []
        if critical_templates:
            immediate_actions.append('Fix critical CSRF vulnerabilities immediately')
        if total_high_issues > 0:
            immediate_actions.append('Address high-severity security issues')
        if overall_score < 0.7:
            immediate_actions.append('Improve overall CSRF compliance')
        
        return {
            'risk_level': risk_level,
            'risk_score': min(1.0, risk_score),
            'overall_compliance': overall_score,
            'critical_templates': critical_templates,
            'high_risk_templates': high_risk_templates,
            'total_critical_issues': total_critical_issues,
            'total_high_issues': total_high_issues,
            'immediate_actions': immediate_actions
        }
    
    def generate_dashboard_data(self, results: List[CSRFAuditResult]) -> Dict[str, Any]:
        """Generate data for compliance dashboard
        
        Args:
            results: List of CSRF audit results
            
        Returns:
            Dashboard data structure
        """
        if not results:
            return {'error': 'No data available'}
        
        # Overview statistics
        total_templates = len(results)
        templates_with_forms = len([r for r in results if r.has_forms])
        protected_templates = len([r for r in results if r.csrf_protected])
        overall_score = self.calculate_overall_compliance(results)
        
        # Compliance distribution
        compliance_distribution = {level.value: 0 for level in ComplianceLevel}
        for result in results:
            if result.has_forms:
                level = self.classify_compliance_level(result.compliance_score)
                compliance_distribution[level.value] += 1
        
        # Issue analysis
        issue_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        issue_types = {}
        
        for result in results:
            for issue in result.issues:
                issue_counts[issue.severity] += 1
                issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1
        
        # Top issues
        top_issues = sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Recommendations
        recommendations = self._generate_dashboard_recommendations(results, overall_score, issue_counts)
        
        return {
            'overview': {
                'total_templates': total_templates,
                'templates_with_forms': templates_with_forms,
                'protected_templates': protected_templates,
                'protection_rate': protected_templates / templates_with_forms * 100 if templates_with_forms > 0 else 100,
                'average_score': overall_score,
                'last_updated': datetime.now().isoformat()
            },
            'compliance_distribution': compliance_distribution,
            'issue_trends': {
                'total_issues': sum(issue_counts.values()),
                'by_severity': issue_counts,
                'by_type': dict(top_issues)
            },
            'top_issues': [{'type': issue_type, 'count': count} for issue_type, count in top_issues],
            'recommendations': recommendations
        }
    
    def _generate_dashboard_recommendations(self, results: List[CSRFAuditResult], 
                                          overall_score: float, 
                                          issue_counts: Dict[str, int]) -> List[str]:
        """Generate recommendations for dashboard
        
        Args:
            results: Audit results
            overall_score: Overall compliance score
            issue_counts: Issue counts by severity
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if issue_counts['CRITICAL'] > 0:
            recommendations.append(f"🚨 Fix {issue_counts['CRITICAL']} critical CSRF vulnerabilities immediately")
        
        if issue_counts['HIGH'] > 0:
            recommendations.append(f"⚠️ Address {issue_counts['HIGH']} high-severity security issues")
        
        if overall_score < 0.7:
            recommendations.append("📈 Improve overall CSRF compliance - consider security training")
        
        # Check for common patterns
        csrf_method_issues = sum(1 for r in results for i in r.issues if i.issue_type == 'csrf_method')
        if csrf_method_issues > 0:
            recommendations.append("🔄 Standardize CSRF implementation using form.hidden_tag()")
        
        exposure_issues = sum(1 for r in results for i in r.issues if i.issue_type == 'token_exposure')
        if exposure_issues > 0:
            recommendations.append("🔒 Review templates for CSRF token exposure in comments/JavaScript")
        
        if not recommendations:
            recommendations.append("✅ CSRF compliance looks good - maintain current security practices")
        
        return recommendations


class SecurityAuditReporter:
    """Generates automated security audit reports"""
    
    def __init__(self):
        """Initialize security audit reporter"""
        self.report_templates = {
            'html': self._get_html_template(),
            'csv_headers': ['template_path', 'has_forms', 'csrf_protected', 'csrf_method', 
                           'compliance_score', 'issue_count', 'critical_issues', 'high_issues']
        }
    
    def generate_compliance_report(self, results: List[CSRFAuditResult]) -> Dict[str, Any]:
        """Generate comprehensive compliance report
        
        Args:
            results: List of CSRF audit results
            
        Returns:
            Compliance report dictionary
        """
        validator = CSRFComplianceValidator()
        
        # Metadata
        metadata = {
            'generated_at': datetime.now().isoformat(),
            'total_templates_scanned': len(results),
            'scan_version': '1.0.0'
        }
        
        # Summary statistics
        templates_with_forms = [r for r in results if r.has_forms]
        protected_templates = [r for r in templates_with_forms if r.csrf_protected]
        
        all_issues = []
        for result in results:
            all_issues.extend(result.issues)
        
        issue_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for issue in all_issues:
            issue_counts[issue.severity] += 1
        
        summary = {
            'total_templates': len(results),
            'templates_with_forms': len(templates_with_forms),
            'csrf_protected_templates': len(protected_templates),
            'protection_rate': len(protected_templates) / len(templates_with_forms) * 100 if templates_with_forms else 100,
            'overall_compliance_score': validator.calculate_overall_compliance(results),
            'total_issues': len(all_issues),
            'critical_issues': issue_counts['CRITICAL'],
            'high_issues': issue_counts['HIGH'],
            'medium_issues': issue_counts['MEDIUM'],
            'low_issues': issue_counts['LOW']
        }
        
        # Compliance levels
        compliance_levels = {'excellent': 0, 'good': 0, 'needs_improvement': 0, 'poor': 0}
        for result in templates_with_forms:
            level = validator.classify_compliance_level(result.compliance_score)
            compliance_levels[level.value] += 1
        
        # Issues analysis
        issue_types = {}
        for issue in all_issues:
            issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1
        
        issues_analysis = {
            'by_severity': issue_counts,
            'by_type': issue_types,
            'most_common_issues': sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:5]
        }
        
        # Recommendations
        recommendations = self._generate_report_recommendations(results, summary, issues_analysis)
        
        # Template details
        templates = []
        for result in results:
            templates.append({
                'path': result.template_path,
                'has_forms': result.has_forms,
                'csrf_protected': result.csrf_protected,
                'csrf_method': result.csrf_method,
                'compliance_score': result.compliance_score,
                'issue_count': len(result.issues),
                'critical_issues': len([i for i in result.issues if i.severity == 'CRITICAL']),
                'high_issues': len([i for i in result.issues if i.severity == 'HIGH']),
                'issues': [asdict(issue) for issue in result.issues]
            })
        
        return {
            'metadata': metadata,
            'summary': summary,
            'compliance_levels': compliance_levels,
            'issues_analysis': issues_analysis,
            'recommendations': recommendations,
            'templates': templates
        }
    
    def export_report(self, report: Dict[str, Any], output_path: str, format: str = 'json'):
        """Export report in specified format
        
        Args:
            report: Report data
            output_path: Output file path
            format: Export format ('json', 'html', 'csv')
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        
        elif format == 'html':
            html_content = self._generate_html_report(report)
            with open(output_path, 'w') as f:
                f.write(html_content)
        
        elif format == 'csv':
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.report_templates['csv_headers'])
                
                for template in report['templates']:
                    writer.writerow([
                        template['path'],
                        template['has_forms'],
                        template['csrf_protected'],
                        template['csrf_method'],
                        template['compliance_score'],
                        template['issue_count'],
                        template['critical_issues'],
                        template['high_issues']
                    ])
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Report exported to {output_path} in {format} format")
    
    def schedule_automated_reports(self, frequency: str, output_dir: str, formats: List[str]):
        """Schedule automated report generation
        
        Args:
            frequency: Report frequency ('daily', 'weekly', 'monthly')
            output_dir: Output directory for reports
            formats: List of export formats
        """
        try:
            import schedule
            
            def generate_scheduled_report():
                # This would integrate with the actual scanner
                logger.info(f"Generating scheduled {frequency} report")
                # Implementation would scan templates and generate report
            
            if frequency == 'daily':
                schedule.every().day.at("02:00").do(generate_scheduled_report)
            elif frequency == 'weekly':
                schedule.every().monday.at("02:00").do(generate_scheduled_report)
            elif frequency == 'monthly':
                schedule.every().month.do(generate_scheduled_report)
            
            logger.info(f"Scheduled {frequency} reports to {output_dir}")
            
        except ImportError:
            logger.warning("Schedule library not available - automated reports not configured")
    
    def send_report_notifications(self, report: Dict[str, Any], recipients: List[str]):
        """Send report notifications
        
        Args:
            report: Report data
            recipients: List of email recipients
        """
        # Check if notification is needed
        critical_issues = report['summary']['critical_issues']
        high_issues = report['summary']['high_issues']
        compliance_score = report['summary']['overall_compliance_score']
        
        if critical_issues > 0 or high_issues > 5 or compliance_score < 0.7:
            subject = f"CSRF Security Alert - {critical_issues} Critical Issues Found"
            
            # Mock notification sending
            def send_notification(to: List[str], subject: str, body: str):
                logger.info(f"Sending notification to {to}: {subject}")
            
            body = f"""
            CSRF Security Report Summary:
            - Overall Compliance Score: {compliance_score:.2f}
            - Critical Issues: {critical_issues}
            - High Issues: {high_issues}
            - Templates Scanned: {report['summary']['total_templates']}
            
            Please review the full report for details.
            """
            
            send_notification(recipients, subject, body)
    
    def _generate_report_recommendations(self, results: List[CSRFAuditResult], 
                                       summary: Dict[str, Any], 
                                       issues_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for the report"""
        recommendations = []
        
        if summary['critical_issues'] > 0:
            recommendations.append("Immediately fix all critical CSRF vulnerabilities")
        
        if summary['protection_rate'] < 100:
            recommendations.append("Ensure all state-changing forms have CSRF protection")
        
        # Check for common issue patterns
        common_issues = issues_analysis['most_common_issues']
        for issue_type, count in common_issues:
            if issue_type == 'csrf_method' and count > 2:
                recommendations.append("Standardize CSRF implementation using form.hidden_tag()")
            elif issue_type == 'token_exposure' and count > 0:
                recommendations.append("Review and fix CSRF token exposure issues")
        
        if summary['overall_compliance_score'] < 0.8:
            recommendations.append("Improve overall CSRF compliance through security training")
        
        return recommendations
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML report"""
        template = self.report_templates['html']
        
        # Simple template substitution
        html_content = template.format(
            title="CSRF Compliance Report",
            generated_at=report['metadata']['generated_at'],
            total_templates=report['summary']['total_templates'],
            compliance_score=report['summary']['overall_compliance_score'],
            critical_issues=report['summary']['critical_issues'],
            high_issues=report['summary']['high_issues'],
            protection_rate=report['summary']['protection_rate']
        )
        
        return html_content
    
    def _get_html_template(self) -> str:
        """Get HTML report template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
                .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
                .metric {{ background: #e9ecef; padding: 15px; border-radius: 5px; flex: 1; }}
                .critical {{ background: #f8d7da; color: #721c24; }}
                .good {{ background: #d4edda; color: #155724; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Generated: {generated_at}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <h3>Templates Scanned</h3>
                    <p>{total_templates}</p>
                </div>
                <div class="metric">
                    <h3>Compliance Score</h3>
                    <p>{compliance_score:.2f}</p>
                </div>
                <div class="metric critical">
                    <h3>Critical Issues</h3>
                    <p>{critical_issues}</p>
                </div>
                <div class="metric">
                    <h3>Protection Rate</h3>
                    <p>{protection_rate:.1f}%</p>
                </div>
            </div>
        </body>
        </html>
        """


class ContinuousIntegrationValidator:
    """Validates CSRF compliance for CI/CD pipelines"""
    
    def __init__(self):
        """Initialize CI validator"""
        self.default_gate_config = {
            'minimum_compliance_score': 0.8,
            'max_critical_issues': 0,
            'max_high_issues': 2,
            'max_medium_issues': 10,
            'fail_on_regression': True
        }
    
    def validate_security_gate(self, results: List[CSRFAuditResult], 
                              gate_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate security gate for CI/CD
        
        Args:
            results: CSRF audit results
            gate_config: Gate configuration
            
        Returns:
            Gate validation result
        """
        validator = CSRFComplianceValidator()
        violations = []
        
        # Check compliance score
        overall_score = validator.calculate_overall_compliance(results)
        min_score = gate_config.get('minimum_compliance_score', 0.8)
        
        if overall_score < min_score:
            violations.append(f"Compliance score {overall_score:.2f} below minimum {min_score}")
        
        # Count issues by severity
        issue_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for result in results:
            for issue in result.issues:
                issue_counts[issue.severity] += 1
        
        # Check issue limits
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM']:
            max_key = f'max_{severity.lower()}_issues'
            max_allowed = gate_config.get(max_key, float('inf'))
            
            if issue_counts[severity] > max_allowed:
                violations.append(f"{issue_counts[severity]} {severity} issues exceed limit {max_allowed}")
        
        # Determine gate result
        passed = len(violations) == 0
        exit_code = 0 if passed else 1
        
        return {
            'passed': passed,
            'exit_code': exit_code,
            'overall_score': overall_score,
            'issue_counts': issue_counts,
            'violations': violations,
            'gate_config': gate_config
        }
    
    def detect_security_regression(self, baseline_results: List[CSRFAuditResult], 
                                  current_results: List[CSRFAuditResult]) -> Dict[str, Any]:
        """Detect security regression between baseline and current results
        
        Args:
            baseline_results: Baseline audit results
            current_results: Current audit results
            
        Returns:
            Regression detection result
        """
        validator = CSRFComplianceValidator()
        
        # Calculate scores
        baseline_score = validator.calculate_overall_compliance(baseline_results)
        current_score = validator.calculate_overall_compliance(current_results)
        
        # Create template score maps
        baseline_scores = {r.template_path: r.compliance_score for r in baseline_results}
        current_scores = {r.template_path: r.compliance_score for r in current_results}
        
        # Find regressions
        regressions = []
        for template_path in current_scores:
            if template_path in baseline_scores:
                baseline_template_score = baseline_scores[template_path]
                current_template_score = current_scores[template_path]
                
                # Significant regression threshold
                if current_template_score < baseline_template_score - 0.1:
                    regressions.append({
                        'template': template_path,
                        'baseline_score': baseline_template_score,
                        'current_score': current_template_score,
                        'regression': baseline_template_score - current_template_score
                    })
        
        # Overall regression check
        overall_regression = current_score < baseline_score - 0.05
        
        return {
            'has_regression': overall_regression or len(regressions) > 0,
            'overall_baseline_score': baseline_score,
            'overall_current_score': current_score,
            'overall_change': current_score - baseline_score,
            'template_regressions': len(regressions),
            'regressions': regressions
        }
    
    def validate_pull_request(self, results: List[CSRFAuditResult], 
                             changed_templates: List[str]) -> Dict[str, Any]:
        """Validate pull request for CSRF compliance
        
        Args:
            results: CSRF audit results
            changed_templates: List of changed template paths
            
        Returns:
            PR validation result
        """
        # Filter results for changed templates
        changed_results = [r for r in results if r.template_path in changed_templates]
        
        # Analyze changed templates
        critical_issues = 0
        high_issues = 0
        template_analysis = []
        
        for result in changed_results:
            template_critical = len([i for i in result.issues if i.severity == 'CRITICAL'])
            template_high = len([i for i in result.issues if i.severity == 'HIGH'])
            
            critical_issues += template_critical
            high_issues += template_high
            
            template_analysis.append({
                'template': result.template_path,
                'compliance_score': result.compliance_score,
                'critical_issues': template_critical,
                'high_issues': template_high,
                'total_issues': len(result.issues)
            })
        
        # Determine PR status
        if critical_issues > 0:
            status = 'BLOCKED'
            message = f"PR blocked due to {critical_issues} critical CSRF issues"
        elif high_issues > 3:
            status = 'NEEDS_REVIEW'
            message = f"PR needs security review due to {high_issues} high-severity issues"
        else:
            status = 'APPROVED'
            message = "PR approved - no critical CSRF issues found"
        
        # Generate recommendations
        recommendations = []
        if critical_issues > 0:
            recommendations.append("Fix all critical CSRF vulnerabilities before merging")
        if high_issues > 0:
            recommendations.append("Review and address high-severity security issues")
        
        return {
            'overall_status': status,
            'message': message,
            'changed_templates': len(changed_templates),
            'analyzed_templates': len(changed_results),
            'critical_issues': critical_issues,
            'high_issues': high_issues,
            'template_analysis': template_analysis,
            'recommendations': recommendations,
            'security_summary': {
                'total_issues': sum(len(r.issues) for r in changed_results),
                'avg_compliance_score': statistics.mean([r.compliance_score for r in changed_results]) if changed_results else 1.0
            }
        }
    
    def collect_security_metrics(self, results: List[CSRFAuditResult]) -> Dict[str, Any]:
        """Collect security metrics for CI reporting
        
        Args:
            results: CSRF audit results
            
        Returns:
            Security metrics
        """
        validator = CSRFComplianceValidator()
        
        # Basic metrics
        compliance_score = validator.calculate_overall_compliance(results)
        
        # Issue counts
        issue_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for result in results:
            for issue in result.issues:
                issue_counts[issue.severity.lower()] += 1
        
        # Template counts
        template_counts = {
            'total': len(results),
            'with_forms': len([r for r in results if r.has_forms]),
            'protected': len([r for r in results if r.csrf_protected]),
            'excellent': len([r for r in results if r.compliance_score >= 0.9]),
            'needs_work': len([r for r in results if r.compliance_score < 0.7])
        }
        
        return {
            'compliance_score': compliance_score,
            'issue_counts': issue_counts,
            'template_counts': template_counts,
            'trends': {
                'protection_rate': template_counts['protected'] / template_counts['with_forms'] * 100 if template_counts['with_forms'] > 0 else 100,
                'excellence_rate': template_counts['excellent'] / template_counts['total'] * 100 if template_counts['total'] > 0 else 100
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate CI configuration
        
        Args:
            config: CI configuration
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Validate score thresholds
        min_score = config.get('minimum_compliance_score')
        if min_score is not None:
            if not 0.0 <= min_score <= 1.0:
                errors.append("minimum_compliance_score must be between 0.0 and 1.0")
        
        # Validate issue limits
        for severity in ['critical', 'high', 'medium', 'low']:
            key = f'max_{severity}_issues'
            value = config.get(key)
            if value is not None:
                if not isinstance(value, int) or value < 0:
                    errors.append(f"{key} must be a non-negative integer")
        
        # Check for unknown options
        known_options = {
            'minimum_compliance_score', 'max_critical_issues', 'max_high_issues',
            'max_medium_issues', 'max_low_issues', 'fail_on_regression',
            'notification_channels'
        }
        
        for key in config:
            if key not in known_options:
                warnings.append(f"Unknown configuration option: {key}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }