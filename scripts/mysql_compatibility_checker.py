#!/usr/bin/env python3
"""
MySQL Server Compatibility Checker for Vedfolnir

This script performs comprehensive MySQL server compatibility checking
to ensure the MySQL server meets all requirements for Vedfolnir operation.
It replaces any SQLite-based compatibility checking.
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mysql_connection_validator import MySQLConnectionValidator
from scripts.mysql_feature_validator import MySQLFeatureValidator
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CompatibilityIssue:
    """Represents a MySQL compatibility issue."""
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'version', 'configuration', 'feature', 'performance'
    title: str
    description: str
    current_value: Any
    recommended_value: Any
    fix_instructions: List[str]

@dataclass
class CompatibilityReport:
    """Complete MySQL compatibility report."""
    timestamp: str
    overall_compatible: bool
    compatibility_score: float
    mysql_version: str
    issues: List[CompatibilityIssue]
    recommendations: List[str]
    summary: Dict[str, Any]

class MySQLCompatibilityChecker:
    """
    Comprehensive MySQL server compatibility checker.
    
    This class performs detailed compatibility analysis including:
    - Version compatibility
    - Configuration validation
    - Feature availability
    - Performance settings
    - Security configuration
    """
    
    def __init__(self, config: Config = None):
        """Initialize the compatibility checker."""
        self.config = config or Config()
        self.connection_validator = MySQLConnectionValidator(self.config)
        self.feature_validator = MySQLFeatureValidator(self.config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Compatibility requirements
        self.requirements = {
            'mysql_version': {
                'minimum': (5, 7, 0),
                'recommended': (8, 0, 0),
                'deprecated': [(5, 6, 0), (5, 5, 0)]
            },
            'configuration': {
                'innodb_buffer_pool_size': {
                    'minimum': 134217728,  # 128MB
                    'recommended': 536870912,  # 512MB
                    'description': 'InnoDB buffer pool size for caching'
                },
                'max_connections': {
                    'minimum': 50,
                    'recommended': 200,
                    'description': 'Maximum concurrent connections'
                },
                'character_set_server': {
                    'required': 'utf8mb4',
                    'description': 'Server character set for Unicode support'
                },
                'collation_server': {
                    'required': 'utf8mb4_unicode_ci',
                    'description': 'Server collation for proper sorting'
                },
                'sql_mode': {
                    'recommended_includes': ['STRICT_TRANS_TABLES', 'ERROR_FOR_DIVISION_BY_ZERO'],
                    'deprecated_excludes': ['NO_ZERO_DATE', 'NO_ZERO_IN_DATE'],
                    'description': 'SQL mode for data integrity'
                }
            },
            'performance': {
                'slow_query_log': {
                    'recommended': 'ON',
                    'description': 'Enable slow query logging for monitoring'
                },
                'long_query_time': {
                    'recommended_max': 2.0,
                    'description': 'Threshold for slow query logging'
                }
            },
            'security': {
                'ssl_support': {
                    'recommended': True,
                    'description': 'SSL support for encrypted connections'
                }
            }
        }
    
    def check_compatibility(self) -> CompatibilityReport:
        """
        Perform comprehensive MySQL compatibility check.
        
        Returns:
            CompatibilityReport with detailed analysis
        """
        self.logger.info("🔍 Starting comprehensive MySQL compatibility check...")
        
        issues = []
        recommendations = []
        
        # Validate connection first
        connection_result = self.connection_validator.validate_connection()
        if not connection_result.success:
            critical_issue = CompatibilityIssue(
                severity='critical',
                category='connection',
                title='MySQL Connection Failed',
                description=connection_result.error_message,
                current_value=None,
                recommended_value='Working connection',
                fix_instructions=[
                    'Check MySQL server is running',
                    'Verify connection parameters',
                    'Check network connectivity',
                    'Validate credentials'
                ]
            )
            
            return CompatibilityReport(
                timestamp=datetime.now().isoformat(),
                overall_compatible=False,
                compatibility_score=0.0,
                mysql_version='Unknown',
                issues=[critical_issue],
                recommendations=['Fix MySQL connection before proceeding'],
                summary={'status': 'Connection failed'}
            )
        
        server_info = connection_result.server_info
        mysql_version = server_info.version
        
        # Check version compatibility
        version_issues = self._check_version_compatibility(server_info)
        issues.extend(version_issues)
        
        # Check configuration
        config_issues = self._check_configuration_compatibility(server_info)
        issues.extend(config_issues)
        
        # Check features
        feature_issues = self._check_feature_compatibility()
        issues.extend(feature_issues)
        
        # Check performance settings
        performance_issues = self._check_performance_compatibility(server_info)
        issues.extend(performance_issues)
        
        # Check security settings
        security_issues = self._check_security_compatibility(server_info)
        issues.extend(security_issues)
        
        # Calculate compatibility score
        compatibility_score = self._calculate_compatibility_score(issues)
        
        # Determine overall compatibility
        critical_issues = [i for i in issues if i.severity == 'critical']
        overall_compatible = len(critical_issues) == 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(issues)
        
        # Create summary
        summary = self._create_summary(issues, compatibility_score, overall_compatible)
        
        self.logger.info(f"✅ Compatibility check completed - Score: {compatibility_score:.1f}%")
        
        return CompatibilityReport(
            timestamp=datetime.now().isoformat(),
            overall_compatible=overall_compatible,
            compatibility_score=compatibility_score,
            mysql_version=mysql_version,
            issues=issues,
            recommendations=recommendations,
            summary=summary
        )
    
    def _check_version_compatibility(self, server_info) -> List[CompatibilityIssue]:
        """Check MySQL version compatibility."""
        issues = []
        current_version = (server_info.version_major, server_info.version_minor, server_info.version_patch)
        
        min_version = self.requirements['mysql_version']['minimum']
        recommended_version = self.requirements['mysql_version']['recommended']
        
        if current_version < min_version:
            issues.append(CompatibilityIssue(
                severity='critical',
                category='version',
                title='MySQL Version Too Old',
                description=f'MySQL version {server_info.version} is below minimum required version',
                current_value=server_info.version,
                recommended_value='.'.join(map(str, min_version)) + '+',
                fix_instructions=[
                    f'Upgrade MySQL to version {".".join(map(str, min_version))} or higher',
                    'Backup your data before upgrading',
                    'Test the upgrade in a development environment first'
                ]
            ))
        elif current_version < recommended_version:
            issues.append(CompatibilityIssue(
                severity='warning',
                category='version',
                title='MySQL Version Below Recommended',
                description=f'MySQL version {server_info.version} is below recommended version',
                current_value=server_info.version,
                recommended_value='.'.join(map(str, recommended_version)) + '+',
                fix_instructions=[
                    f'Consider upgrading to MySQL {".".join(map(str, recommended_version))} for optimal performance',
                    'Review new features and improvements in newer versions'
                ]
            ))
        
        # Check for deprecated versions
        for deprecated_version in self.requirements['mysql_version']['deprecated']:
            if current_version[:2] == deprecated_version[:2]:
                issues.append(CompatibilityIssue(
                    severity='warning',
                    category='version',
                    title='MySQL Version Deprecated',
                    description=f'MySQL {current_version[0]}.{current_version[1]} series is deprecated',
                    current_value=server_info.version,
                    recommended_value='8.0+',
                    fix_instructions=[
                        'Plan migration to a supported MySQL version',
                        'Check MySQL end-of-life schedules'
                    ]
                ))
        
        return issues
    
    def _check_configuration_compatibility(self, server_info) -> List[CompatibilityIssue]:
        """Check MySQL configuration compatibility."""
        issues = []
        
        # Check InnoDB buffer pool size
        buffer_pool_config = self.requirements['configuration']['innodb_buffer_pool_size']
        if server_info.innodb_buffer_pool_size < buffer_pool_config['minimum']:
            issues.append(CompatibilityIssue(
                severity='warning',
                category='configuration',
                title='InnoDB Buffer Pool Too Small',
                description=buffer_pool_config['description'],
                current_value=f"{server_info.innodb_buffer_pool_size} bytes",
                recommended_value=f"{buffer_pool_config['recommended']} bytes",
                fix_instructions=[
                    f'Set innodb_buffer_pool_size = {buffer_pool_config["recommended"]} in MySQL configuration',
                    'Restart MySQL server after configuration change',
                    'Monitor memory usage after change'
                ]
            ))
        
        # Check max connections
        connections_config = self.requirements['configuration']['max_connections']
        if server_info.max_connections < connections_config['minimum']:
            issues.append(CompatibilityIssue(
                severity='warning',
                category='configuration',
                title='Max Connections Too Low',
                description=connections_config['description'],
                current_value=server_info.max_connections,
                recommended_value=connections_config['recommended'],
                fix_instructions=[
                    f'Set max_connections = {connections_config["recommended"]} in MySQL configuration',
                    'Restart MySQL server after configuration change'
                ]
            ))
        
        # Check character set
        charset_config = self.requirements['configuration']['character_set_server']
        if server_info.character_set != charset_config['required']:
            issues.append(CompatibilityIssue(
                severity='critical',
                category='configuration',
                title='Incorrect Character Set',
                description=charset_config['description'],
                current_value=server_info.character_set,
                recommended_value=charset_config['required'],
                fix_instructions=[
                    f'Set character_set_server = {charset_config["required"]} in MySQL configuration',
                    'Restart MySQL server after configuration change',
                    'Convert existing data to UTF8MB4 if needed'
                ]
            ))
        
        # Check collation
        collation_config = self.requirements['configuration']['collation_server']
        if server_info.collation != collation_config['required']:
            issues.append(CompatibilityIssue(
                severity='warning',
                category='configuration',
                title='Non-optimal Collation',
                description=collation_config['description'],
                current_value=server_info.collation,
                recommended_value=collation_config['required'],
                fix_instructions=[
                    f'Set collation_server = {collation_config["required"]} in MySQL configuration',
                    'Restart MySQL server after configuration change'
                ]
            ))
        
        return issues
    
    def _check_feature_compatibility(self) -> List[CompatibilityIssue]:
        """Check MySQL feature compatibility."""
        issues = []
        
        # Validate features using the feature validator
        feature_results = self.feature_validator.validate_all_features()
        
        for result in feature_results:
            if result.required and not result.available:
                issues.append(CompatibilityIssue(
                    severity='critical',
                    category='feature',
                    title=f'Required Feature Missing: {result.feature_name}',
                    description=result.description,
                    current_value='Not Available',
                    recommended_value='Available',
                    fix_instructions=result.recommendations
                ))
            elif not result.required and not result.available:
                issues.append(CompatibilityIssue(
                    severity='info',
                    category='feature',
                    title=f'Optional Feature Missing: {result.feature_name}',
                    description=result.description,
                    current_value='Not Available',
                    recommended_value='Available',
                    fix_instructions=result.recommendations
                ))
        
        return issues
    
    def _check_performance_compatibility(self, server_info) -> List[CompatibilityIssue]:
        """Check MySQL performance settings compatibility."""
        issues = []
        
        # Check slow query log
        if not server_info.slow_query_log_enabled:
            issues.append(CompatibilityIssue(
                severity='info',
                category='performance',
                title='Slow Query Log Disabled',
                description='Slow query logging helps identify performance issues',
                current_value='OFF',
                recommended_value='ON',
                fix_instructions=[
                    'Set slow_query_log = ON in MySQL configuration',
                    'Set slow_query_log_file to specify log location',
                    'Set long_query_time = 2 for reasonable threshold'
                ]
            ))
        
        return issues
    
    def _check_security_compatibility(self, server_info) -> List[CompatibilityIssue]:
        """Check MySQL security settings compatibility."""
        issues = []
        
        # Check SSL support
        if not server_info.ssl_support:
            issues.append(CompatibilityIssue(
                severity='warning',
                category='security',
                title='SSL Support Not Available',
                description='SSL encryption is recommended for secure connections',
                current_value='Not Available',
                recommended_value='Available',
                fix_instructions=[
                    'Enable SSL in MySQL configuration',
                    'Generate SSL certificates',
                    'Configure SSL parameters in my.cnf'
                ]
            ))
        
        return issues
    
    def _calculate_compatibility_score(self, issues: List[CompatibilityIssue]) -> float:
        """Calculate overall compatibility score."""
        if not issues:
            return 100.0
        
        # Weight different severity levels
        severity_weights = {
            'critical': -25,
            'warning': -10,
            'info': -2
        }
        
        total_deduction = sum(severity_weights.get(issue.severity, 0) for issue in issues)
        score = max(0, 100 + total_deduction)
        
        return score
    
    def _generate_recommendations(self, issues: List[CompatibilityIssue]) -> List[str]:
        """Generate prioritized recommendations."""
        recommendations = []
        
        # Critical issues first
        critical_issues = [i for i in issues if i.severity == 'critical']
        if critical_issues:
            recommendations.append("🔴 CRITICAL: Address critical compatibility issues immediately")
            for issue in critical_issues:
                recommendations.extend(issue.fix_instructions)
        
        # Warning issues
        warning_issues = [i for i in issues if i.severity == 'warning']
        if warning_issues:
            recommendations.append("🟡 WARNING: Address configuration warnings for optimal performance")
        
        # Info issues
        info_issues = [i for i in issues if i.severity == 'info']
        if info_issues:
            recommendations.append("ℹ️ INFO: Consider addressing informational items for enhanced functionality")
        
        return recommendations
    
    def _create_summary(self, issues: List[CompatibilityIssue], score: float, compatible: bool) -> Dict[str, Any]:
        """Create compatibility summary."""
        issue_counts = {
            'critical': len([i for i in issues if i.severity == 'critical']),
            'warning': len([i for i in issues if i.severity == 'warning']),
            'info': len([i for i in issues if i.severity == 'info'])
        }
        
        return {
            'overall_status': 'Compatible' if compatible else 'Incompatible',
            'compatibility_score': f"{score:.1f}%",
            'total_issues': len(issues),
            'issue_breakdown': issue_counts,
            'ready_for_production': compatible and score >= 80
        }

def main():
    """Main function for MySQL compatibility checker."""
    parser = argparse.ArgumentParser(
        description='Check MySQL server compatibility for Vedfolnir'
    )
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress verbose output')
    parser.add_argument('--save-report', type=str,
                       help='Save detailed report to file')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    try:
        # Initialize checker
        checker = MySQLCompatibilityChecker()
        
        # Run compatibility check
        report = checker.check_compatibility()
        
        # Output results
        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            # Print human-readable report
            print("\n" + "="*80)
            print("🔍 MYSQL COMPATIBILITY REPORT")
            print("="*80)
            print(f"📅 Timestamp: {report.timestamp}")
            print(f"🗄️ MySQL Version: {report.mysql_version}")
            print(f"📊 Compatibility Score: {report.compatibility_score:.1f}%")
            print(f"✅ Overall Compatible: {'Yes' if report.overall_compatible else 'No'}")
            print(f"🚀 Production Ready: {'Yes' if report.summary['ready_for_production'] else 'No'}")
            print()
            
            # Issues breakdown
            if report.issues:
                print("📋 ISSUES FOUND:")
                for severity in ['critical', 'warning', 'info']:
                    severity_issues = [i for i in report.issues if i.severity == severity]
                    if severity_issues:
                        severity_icon = {'critical': '🔴', 'warning': '🟡', 'info': 'ℹ️'}[severity]
                        print(f"\n{severity_icon} {severity.upper()} ({len(severity_issues)}):")
                        for issue in severity_issues:
                            print(f"  • {issue.title}")
                            print(f"    {issue.description}")
                            print(f"    Current: {issue.current_value}")
                            print(f"    Recommended: {issue.recommended_value}")
                            if issue.fix_instructions:
                                print("    Fix:")
                                for instruction in issue.fix_instructions:
                                    print(f"      - {instruction}")
                            print()
            else:
                print("✅ No compatibility issues found!")
            
            # Recommendations
            if report.recommendations:
                print("💡 RECOMMENDATIONS:")
                for rec in report.recommendations:
                    print(f"  • {rec}")
                print()
            
            print("="*80)
        
        # Save report if requested
        if args.save_report:
            with open(args.save_report, 'w') as f:
                json.dump(asdict(report), f, indent=2)
            print(f"📄 Report saved to: {args.save_report}")
        
        # Exit with appropriate code
        return 0 if report.overall_compatible else 1
        
    except Exception as e:
        logger.error(f"❌ Compatibility check failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
