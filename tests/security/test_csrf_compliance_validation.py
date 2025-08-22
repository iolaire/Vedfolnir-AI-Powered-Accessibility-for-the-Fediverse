# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Security Compliance Validation Tests

Tests for compliance scoring system, automated security audit reports,
and continuous integration security checks for CSRF compliance.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import compliance validation components
from security.audit.csrf_compliance_validator import (
    CSRFComplianceValidator, ComplianceReport, ComplianceLevel,
    SecurityAuditReporter, ContinuousIntegrationValidator
)
from security.audit.csrf_template_scanner import CSRFTemplateScanner, CSRFAuditResult, TemplateSecurityIssue

class TestCSRFComplianceScoring(unittest.TestCase):
    """Test CSRF compliance scoring system"""
    
    def setUp(self):
        """Set up test environment"""
        self.validator = CSRFComplianceValidator()
        self.scanner = CSRFTemplateScanner()
    
    def test_compliance_level_classification(self):
        """Test compliance level classification"""
        test_cases = [
            (1.0, ComplianceLevel.EXCELLENT),
            (0.95, ComplianceLevel.EXCELLENT),
            (0.89, ComplianceLevel.GOOD),
            (0.75, ComplianceLevel.GOOD),
            (0.69, ComplianceLevel.NEEDS_IMPROVEMENT),
            (0.50, ComplianceLevel.NEEDS_IMPROVEMENT),
            (0.49, ComplianceLevel.POOR),
            (0.0, ComplianceLevel.POOR)
        ]
        
        for score, expected_level in test_cases:
            with self.subTest(score=score):
                level = self.validator.classify_compliance_level(score)
                self.assertEqual(level, expected_level)
    
    def test_overall_compliance_calculation(self):
        """Test overall compliance score calculation"""
        # Create mock audit results
        results = [
            self._create_mock_result('template1.html', 1.0, []),
            self._create_mock_result('template2.html', 0.8, [
                TemplateSecurityIssue('template2.html', 'csrf_method', 'LOW', 'Minor issue')
            ]),
            self._create_mock_result('template3.html', 0.5, [
                TemplateSecurityIssue('template3.html', 'missing_csrf', 'CRITICAL', 'Critical issue')
            ])
        ]
        
        overall_score = self.validator.calculate_overall_compliance(results)
        
        # Should be weighted average
        expected_score = (1.0 + 0.8 + 0.5) / 3
        self.assertAlmostEqual(overall_score, expected_score, places=2)
    
    def test_compliance_trends_tracking(self):
        """Test compliance trends tracking over time"""
        # Create historical compliance data
        historical_data = [
            {'date': '2025-01-01', 'score': 0.6, 'issues': 10},
            {'date': '2025-01-08', 'score': 0.7, 'issues': 8},
            {'date': '2025-01-15', 'score': 0.8, 'issues': 5},
            {'date': '2025-01-22', 'score': 0.85, 'issues': 3}
        ]
        
        trends = self.validator.analyze_compliance_trends(historical_data)
        
        self.assertIn('trend_direction', trends)
        self.assertIn('improvement_rate', trends)
        self.assertIn('issue_reduction_rate', trends)
        
        # Should detect positive trend
        self.assertEqual(trends['trend_direction'], 'improving')
        self.assertGreater(trends['improvement_rate'], 0)
    
    def test_compliance_thresholds(self):
        """Test compliance threshold validation"""
        thresholds = {
            'minimum_score': 0.8,
            'critical_issues': 0,
            'high_issues': 2,
            'protected_forms_percentage': 100
        }
        
        # Test passing compliance
        passing_results = [
            self._create_mock_result('template1.html', 0.9, []),
            self._create_mock_result('template2.html', 0.85, [
                TemplateSecurityIssue('template2.html', 'csrf_method', 'LOW', 'Minor issue')
            ])
        ]
        
        compliance_check = self.validator.validate_compliance_thresholds(passing_results, thresholds)
        self.assertTrue(compliance_check['passes'])
        
        # Test failing compliance
        failing_results = [
            self._create_mock_result('template1.html', 0.5, [
                TemplateSecurityIssue('template1.html', 'missing_csrf', 'CRITICAL', 'Critical issue')
            ])
        ]
        
        compliance_check = self.validator.validate_compliance_thresholds(failing_results, thresholds)
        self.assertFalse(compliance_check['passes'])
        self.assertIn('violations', compliance_check)
    
    def test_risk_assessment(self):
        """Test security risk assessment"""
        # High-risk scenario
        high_risk_results = [
            self._create_mock_result('admin.html', 0.3, [
                TemplateSecurityIssue('admin.html', 'missing_csrf', 'CRITICAL', 'Admin form without CSRF'),
                TemplateSecurityIssue('admin.html', 'token_exposure', 'HIGH', 'Token exposed in JavaScript')
            ]),
            self._create_mock_result('login.html', 0.4, [
                TemplateSecurityIssue('login.html', 'missing_csrf', 'CRITICAL', 'Login form without CSRF')
            ])
        ]
        
        risk_assessment = self.validator.assess_security_risk(high_risk_results)
        
        self.assertEqual(risk_assessment['risk_level'], 'HIGH')
        self.assertGreater(risk_assessment['risk_score'], 0.7)
        self.assertIn('critical_templates', risk_assessment)
        self.assertIn('immediate_actions', risk_assessment)
        
        # Low-risk scenario
        low_risk_results = [
            self._create_mock_result('template1.html', 0.95, []),
            self._create_mock_result('template2.html', 0.9, [
                TemplateSecurityIssue('template2.html', 'csrf_method', 'LOW', 'Minor styling issue')
            ])
        ]
        
        risk_assessment = self.validator.assess_security_risk(low_risk_results)
        self.assertEqual(risk_assessment['risk_level'], 'LOW')
    
    def _create_mock_result(self, template_path: str, score: float, issues: list) -> CSRFAuditResult:
        """Create mock CSRF audit result for testing"""
        return CSRFAuditResult(
            template_path=template_path,
            has_forms=True,
            csrf_protected=score > 0.5,
            csrf_method='hidden_tag' if score > 0.8 else 'csrf_token' if score > 0.5 else 'none',
            issues=issues,
            compliance_score=score,
            recommendations=[]
        )

class TestSecurityAuditReporting(unittest.TestCase):
    """Test automated security audit reporting"""
    
    def setUp(self):
        """Set up test environment"""
        self.reporter = SecurityAuditReporter()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_generate_compliance_report(self):
        """Test compliance report generation"""
        # Create mock audit results
        results = [
            self._create_mock_result('template1.html', 1.0, []),
            self._create_mock_result('template2.html', 0.7, [
                TemplateSecurityIssue('template2.html', 'csrf_method', 'MEDIUM', 'Inconsistent method')
            ]),
            self._create_mock_result('template3.html', 0.3, [
                TemplateSecurityIssue('template3.html', 'missing_csrf', 'CRITICAL', 'No CSRF protection')
            ])
        ]
        
        report = self.reporter.generate_compliance_report(results)
        
        # Validate report structure
        self.assertIn('metadata', report)
        self.assertIn('summary', report)
        self.assertIn('compliance_levels', report)
        self.assertIn('issues_analysis', report)
        self.assertIn('recommendations', report)
        self.assertIn('templates', report)
        
        # Validate summary data
        summary = report['summary']
        self.assertEqual(summary['total_templates'], 3)
        self.assertEqual(summary['templates_with_forms'], 3)
        self.assertEqual(summary['critical_issues'], 1)
        
        # Validate compliance levels
        levels = report['compliance_levels']
        self.assertEqual(levels['excellent'], 1)
        self.assertEqual(levels['poor'], 1)
    
    def test_export_report_formats(self):
        """Test report export in different formats"""
        results = [self._create_mock_result('test.html', 0.8, [])]
        report = self.reporter.generate_compliance_report(results)
        
        # Test JSON export
        json_path = Path(self.temp_dir) / 'report.json'
        self.reporter.export_report(report, str(json_path), format='json')
        
        self.assertTrue(json_path.exists())
        with open(json_path) as f:
            loaded_report = json.load(f)
        self.assertEqual(loaded_report['summary']['total_templates'], 1)
        
        # Test HTML export
        html_path = Path(self.temp_dir) / 'report.html'
        self.reporter.export_report(report, str(html_path), format='html')
        
        self.assertTrue(html_path.exists())
        html_content = html_path.read_text()
        self.assertIn('<html>', html_content)
        self.assertIn('CSRF Compliance Report', html_content)
        
        # Test CSV export
        csv_path = Path(self.temp_dir) / 'report.csv'
        self.reporter.export_report(report, str(csv_path), format='csv')
        
        self.assertTrue(csv_path.exists())
        csv_content = csv_path.read_text()
        self.assertIn('template_path', csv_content)
        self.assertIn('compliance_score', csv_content)
    
    def test_report_scheduling(self):
        """Test automated report scheduling"""
        # Mock scheduler
        with patch('security.audit.csrf_compliance_validator.schedule') as mock_schedule:
            self.reporter.schedule_automated_reports(
                frequency='daily',
                output_dir=self.temp_dir,
                formats=['json', 'html']
            )
            
            # Should schedule daily job
            mock_schedule.every.return_value.day.at.assert_called_once()
    
    def test_report_notifications(self):
        """Test report notification system"""
        # High-risk report should trigger notifications
        high_risk_results = [
            self._create_mock_result('critical.html', 0.2, [
                TemplateSecurityIssue('critical.html', 'missing_csrf', 'CRITICAL', 'Critical issue')
            ])
        ]
        
        with patch('security.audit.csrf_compliance_validator.send_notification') as mock_notify:
            report = self.reporter.generate_compliance_report(high_risk_results)
            self.reporter.send_report_notifications(report, ['admin@test.com'])
            
            # Should send notification for critical issues
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args[1]
            self.assertIn('CRITICAL', call_args['subject'])
    
    def _create_mock_result(self, template_path: str, score: float, issues: list) -> CSRFAuditResult:
        """Create mock CSRF audit result for testing"""
        return CSRFAuditResult(
            template_path=template_path,
            has_forms=True,
            csrf_protected=score > 0.5,
            csrf_method='hidden_tag' if score > 0.8 else 'csrf_token' if score > 0.5 else 'none',
            issues=issues,
            compliance_score=score,
            recommendations=[]
        )

class TestContinuousIntegrationValidation(unittest.TestCase):
    """Test continuous integration security checks"""
    
    def setUp(self):
        """Set up test environment"""
        self.ci_validator = ContinuousIntegrationValidator()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_ci_security_gate(self):
        """Test CI security gate validation"""
        # Configure security gate
        gate_config = {
            'minimum_compliance_score': 0.8,
            'max_critical_issues': 0,
            'max_high_issues': 2,
            'fail_on_regression': True
        }
        
        # Test passing gate
        passing_results = [
            self._create_mock_result('template1.html', 0.9, []),
            self._create_mock_result('template2.html', 0.85, [
                TemplateSecurityIssue('template2.html', 'csrf_method', 'LOW', 'Minor issue')
            ])
        ]
        
        gate_result = self.ci_validator.validate_security_gate(passing_results, gate_config)
        self.assertTrue(gate_result['passed'])
        self.assertEqual(gate_result['exit_code'], 0)
        
        # Test failing gate
        failing_results = [
            self._create_mock_result('template1.html', 0.3, [
                TemplateSecurityIssue('template1.html', 'missing_csrf', 'CRITICAL', 'Critical issue')
            ])
        ]
        
        gate_result = self.ci_validator.validate_security_gate(failing_results, gate_config)
        self.assertFalse(gate_result['passed'])
        self.assertNotEqual(gate_result['exit_code'], 0)
        self.assertIn('violations', gate_result)
    
    def test_regression_detection(self):
        """Test security regression detection"""
        # Previous baseline
        baseline_results = [
            self._create_mock_result('template1.html', 0.9, []),
            self._create_mock_result('template2.html', 0.8, [])
        ]
        
        # Current results with regression
        current_results = [
            self._create_mock_result('template1.html', 0.9, []),
            self._create_mock_result('template2.html', 0.5, [
                TemplateSecurityIssue('template2.html', 'missing_csrf', 'CRITICAL', 'New critical issue')
            ])
        ]
        
        regression_check = self.ci_validator.detect_security_regression(
            baseline_results, current_results
        )
        
        self.assertTrue(regression_check['has_regression'])
        self.assertIn('regressions', regression_check)
        self.assertGreater(len(regression_check['regressions']), 0)
        
        # Test no regression
        no_regression_results = [
            self._create_mock_result('template1.html', 0.95, []),
            self._create_mock_result('template2.html', 0.85, [])
        ]
        
        regression_check = self.ci_validator.detect_security_regression(
            baseline_results, no_regression_results
        )
        
        self.assertFalse(regression_check['has_regression'])
    
    def test_pull_request_validation(self):
        """Test pull request security validation"""
        # Mock changed templates
        changed_templates = ['template1.html', 'template2.html']
        
        # Mock audit results for changed templates
        pr_results = [
            self._create_mock_result('template1.html', 0.9, []),
            self._create_mock_result('template2.html', 0.7, [
                TemplateSecurityIssue('template2.html', 'csrf_method', 'MEDIUM', 'Style issue')
            ])
        ]
        
        pr_validation = self.ci_validator.validate_pull_request(pr_results, changed_templates)
        
        self.assertIn('overall_status', pr_validation)
        self.assertIn('changed_templates', pr_validation)
        self.assertIn('security_summary', pr_validation)
        self.assertIn('recommendations', pr_validation)
        
        # Should pass for medium/low issues
        self.assertEqual(pr_validation['overall_status'], 'APPROVED')
        
        # Test PR with critical issues
        critical_pr_results = [
            self._create_mock_result('template1.html', 0.2, [
                TemplateSecurityIssue('template1.html', 'missing_csrf', 'CRITICAL', 'Critical issue')
            ])
        ]
        
        pr_validation = self.ci_validator.validate_pull_request(critical_pr_results, ['template1.html'])
        self.assertEqual(pr_validation['overall_status'], 'BLOCKED')
    
    def test_security_metrics_collection(self):
        """Test security metrics collection for CI"""
        results = [
            self._create_mock_result('template1.html', 0.9, []),
            self._create_mock_result('template2.html', 0.7, [
                TemplateSecurityIssue('template2.html', 'csrf_method', 'MEDIUM', 'Issue')
            ]),
            self._create_mock_result('template3.html', 0.3, [
                TemplateSecurityIssue('template3.html', 'missing_csrf', 'CRITICAL', 'Critical')
            ])
        ]
        
        metrics = self.ci_validator.collect_security_metrics(results)
        
        # Validate metrics structure
        self.assertIn('compliance_score', metrics)
        self.assertIn('issue_counts', metrics)
        self.assertIn('template_counts', metrics)
        self.assertIn('trends', metrics)
        
        # Validate metric values
        self.assertAlmostEqual(metrics['compliance_score'], (0.9 + 0.7 + 0.3) / 3, places=2)
        self.assertEqual(metrics['issue_counts']['critical'], 1)
        self.assertEqual(metrics['issue_counts']['medium'], 1)
        self.assertEqual(metrics['template_counts']['total'], 3)
    
    def test_ci_configuration_validation(self):
        """Test CI configuration validation"""
        # Valid configuration
        valid_config = {
            'minimum_compliance_score': 0.8,
            'max_critical_issues': 0,
            'max_high_issues': 2,
            'max_medium_issues': 5,
            'fail_on_regression': True,
            'notification_channels': ['email', 'slack']
        }
        
        validation = self.ci_validator.validate_configuration(valid_config)
        self.assertTrue(validation['valid'])
        
        # Invalid configuration
        invalid_config = {
            'minimum_compliance_score': 1.5,  # Invalid score
            'max_critical_issues': -1,  # Invalid count
            'unknown_option': True  # Unknown option
        }
        
        validation = self.ci_validator.validate_configuration(invalid_config)
        self.assertFalse(validation['valid'])
        self.assertIn('errors', validation)
    
    def _create_mock_result(self, template_path: str, score: float, issues: list) -> CSRFAuditResult:
        """Create mock CSRF audit result for testing"""
        return CSRFAuditResult(
            template_path=template_path,
            has_forms=True,
            csrf_protected=score > 0.5,
            csrf_method='hidden_tag' if score > 0.8 else 'csrf_token' if score > 0.5 else 'none',
            issues=issues,
            compliance_score=score,
            recommendations=[]
        )

class TestComplianceIntegration(unittest.TestCase):
    """Integration tests for compliance validation system"""
    
    def setUp(self):
        """Set up test environment"""
        self.validator = CSRFComplianceValidator()
        self.reporter = SecurityAuditReporter()
        self.ci_validator = ContinuousIntegrationValidator()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_compliance_workflow(self):
        """Test complete compliance validation workflow"""
        # 1. Scan templates (mocked)
        scanner = CSRFTemplateScanner()
        
        # 2. Create mock results
        results = [
            self._create_mock_result('good.html', 0.95, []),
            self._create_mock_result('needs_work.html', 0.6, [
                TemplateSecurityIssue('needs_work.html', 'csrf_method', 'MEDIUM', 'Needs improvement')
            ]),
            self._create_mock_result('critical.html', 0.2, [
                TemplateSecurityIssue('critical.html', 'missing_csrf', 'CRITICAL', 'Critical issue')
            ])
        ]
        
        # 3. Validate compliance
        overall_compliance = self.validator.calculate_overall_compliance(results)
        self.assertGreater(overall_compliance, 0.5)
        
        # 4. Generate report
        report = self.reporter.generate_compliance_report(results)
        self.assertIsInstance(report, dict)
        
        # 5. Export report
        report_path = Path(self.temp_dir) / 'compliance_report.json'
        self.reporter.export_report(report, str(report_path), format='json')
        self.assertTrue(report_path.exists())
        
        # 6. CI validation
        gate_config = {'minimum_compliance_score': 0.7, 'max_critical_issues': 0}
        gate_result = self.ci_validator.validate_security_gate(results, gate_config)
        
        # Should fail due to critical issue
        self.assertFalse(gate_result['passed'])
    
    def test_compliance_dashboard_data(self):
        """Test compliance dashboard data generation"""
        results = [
            self._create_mock_result('template1.html', 0.9, []),
            self._create_mock_result('template2.html', 0.8, []),
            self._create_mock_result('template3.html', 0.6, [
                TemplateSecurityIssue('template3.html', 'csrf_method', 'MEDIUM', 'Issue')
            ])
        ]
        
        dashboard_data = self.validator.generate_dashboard_data(results)
        
        # Validate dashboard structure
        self.assertIn('overview', dashboard_data)
        self.assertIn('compliance_distribution', dashboard_data)
        self.assertIn('issue_trends', dashboard_data)
        self.assertIn('top_issues', dashboard_data)
        self.assertIn('recommendations', dashboard_data)
        
        # Validate overview data
        overview = dashboard_data['overview']
        self.assertEqual(overview['total_templates'], 3)
        self.assertGreater(overview['average_score'], 0.7)
    
    def _create_mock_result(self, template_path: str, score: float, issues: list) -> CSRFAuditResult:
        """Create mock CSRF audit result for testing"""
        return CSRFAuditResult(
            template_path=template_path,
            has_forms=True,
            csrf_protected=score > 0.5,
            csrf_method='hidden_tag' if score > 0.8 else 'csrf_token' if score > 0.5 else 'none',
            issues=issues,
            compliance_score=score,
            recommendations=[]
        )

if __name__ == '__main__':
    unittest.main(verbosity=2)