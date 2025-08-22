#!/usr/bin/env python3
"""
MySQL Feature Availability Validation Script for Vedfolnir

This script validates MySQL server features and capabilities required
for Vedfolnir operation. It replaces any SQLite-based feature checking
and provides comprehensive MySQL-specific feature validation.
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mysql_connection_validator import MySQLConnectionValidator
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class FeatureValidationResult:
    """Result of MySQL feature validation."""
    feature_name: str
    available: bool
    required: bool
    description: str
    validation_details: Dict[str, Any]
    recommendations: List[str]

class MySQLFeatureValidator:
    """
    Comprehensive MySQL feature availability validator.
    
    This class validates MySQL server features and capabilities
    required for optimal Vedfolnir operation.
    """
    
    def __init__(self, config: Config = None):
        """Initialize the feature validator."""
        self.config = config or Config()
        self.validator = MySQLConnectionValidator(self.config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Define required and optional features
        self.feature_definitions = {
            'mysql_version': {
                'required': True,
                'description': 'MySQL server version compatibility',
                'minimum_version': (5, 7, 0),
                'recommended_version': (8, 0, 0)
            },
            'innodb_engine': {
                'required': True,
                'description': 'InnoDB storage engine for ACID compliance',
                'validation_query': "SELECT SUPPORT FROM INFORMATION_SCHEMA.ENGINES WHERE ENGINE = 'InnoDB'"
            },
            'utf8mb4_charset': {
                'required': True,
                'description': 'UTF8MB4 character set for full Unicode support',
                'validation_query': "SHOW CHARACTER SET LIKE 'utf8mb4'"
            },
            'json_datatype': {
                'required': True,
                'description': 'JSON data type support for flexible data storage',
                'validation_query': "SELECT JSON_VALID('{\"test\": true}') AS json_support"
            },
            'performance_schema': {
                'required': True,
                'description': 'Performance Schema for monitoring and diagnostics',
                'validation_query': "SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = 'performance_schema'"
            },
            'information_schema': {
                'required': True,
                'description': 'Information Schema for metadata access',
                'validation_query': "SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = 'information_schema'"
            },
            'ssl_support': {
                'required': False,
                'description': 'SSL/TLS support for encrypted connections',
                'validation_query': "SHOW VARIABLES LIKE 'have_ssl'"
            },
            'partitioning': {
                'required': False,
                'description': 'Table partitioning for large dataset management',
                'validation_query': "SHOW VARIABLES LIKE 'have_partitioning'"
            },
            'event_scheduler': {
                'required': False,
                'description': 'Event scheduler for automated maintenance tasks',
                'validation_query': "SHOW VARIABLES LIKE 'event_scheduler'"
            },
            'full_text_search': {
                'required': False,
                'description': 'Full-text search capabilities',
                'validation_query': "SELECT COUNT(*) FROM INFORMATION_SCHEMA.PLUGINS WHERE PLUGIN_NAME = 'FULLTEXT'"
            },
            'replication': {
                'required': False,
                'description': 'MySQL replication capabilities',
                'validation_query': "SHOW VARIABLES LIKE 'log_bin'"
            },
            'stored_procedures': {
                'required': False,
                'description': 'Stored procedure support',
                'validation_query': "SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'PROCEDURE' LIMIT 1"
            },
            'triggers': {
                'required': False,
                'description': 'Database trigger support',
                'validation_query': "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TRIGGERS LIMIT 1"
            },
            'views': {
                'required': False,
                'description': 'Database view support',
                'validation_query': "SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS LIMIT 1"
            }
        }
    
    def validate_all_features(self) -> List[FeatureValidationResult]:
        """
        Validate all MySQL features.
        
        Returns:
            List of FeatureValidationResult objects
        """
        results = []
        
        self.logger.info("🔍 Starting comprehensive MySQL feature validation...")
        
        # First, validate basic connection
        connection_result = self.validator.validate_connection()
        if not connection_result.success:
            self.logger.error(f"❌ Cannot validate features: {connection_result.error_message}")
            return []
        
        server_info = connection_result.server_info
        
        for feature_name, feature_def in self.feature_definitions.items():
            try:
                result = self._validate_feature(feature_name, feature_def, server_info)
                results.append(result)
                
                status_icon = "✅" if result.available else "❌" if result.required else "⚠️"
                self.logger.info(f"{status_icon} {feature_name}: {'Available' if result.available else 'Not Available'}")
                
            except Exception as e:
                self.logger.error(f"❌ Failed to validate feature {feature_name}: {e}")
                results.append(FeatureValidationResult(
                    feature_name=feature_name,
                    available=False,
                    required=feature_def['required'],
                    description=feature_def['description'],
                    validation_details={'error': str(e)},
                    recommendations=[f"Fix validation error for {feature_name}"]
                ))
        
        return results
    
    def _validate_feature(self, feature_name: str, feature_def: Dict[str, Any], server_info) -> FeatureValidationResult:
        """
        Validate a specific MySQL feature.
        
        Args:
            feature_name: Name of the feature to validate
            feature_def: Feature definition dictionary
            server_info: MySQL server information
            
        Returns:
            FeatureValidationResult object
        """
        validation_details = {}
        recommendations = []
        available = False
        
        if feature_name == 'mysql_version':
            # Special handling for version validation
            current_version = (server_info.version_major, server_info.version_minor, server_info.version_patch)
            min_version = feature_def['minimum_version']
            recommended_version = feature_def['recommended_version']
            
            available = current_version >= min_version
            validation_details = {
                'current_version': server_info.version,
                'minimum_required': '.'.join(map(str, min_version)),
                'recommended': '.'.join(map(str, recommended_version)),
                'meets_minimum': available,
                'meets_recommended': current_version >= recommended_version
            }
            
            if not available:
                recommendations.append(f"Upgrade MySQL to version {'.'.join(map(str, min_version))} or higher")
            elif current_version < recommended_version:
                recommendations.append(f"Consider upgrading to MySQL {'.'.join(map(str, recommended_version))} for optimal performance")
                
        elif 'validation_query' in feature_def:
            # Query-based validation
            try:
                with self.validator._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(feature_def['validation_query'])
                    result = cursor.fetchone()
                    cursor.close()
                    
                    if feature_name == 'innodb_engine':
                        available = result and result[0] in ('YES', 'DEFAULT')
                        validation_details['engine_support'] = result[0] if result else 'NOT_FOUND'
                        
                    elif feature_name == 'utf8mb4_charset':
                        available = result is not None
                        validation_details['charset_available'] = available
                        
                    elif feature_name == 'json_datatype':
                        available = result and result[0] == 1
                        validation_details['json_support'] = available
                        
                    elif feature_name in ['performance_schema', 'information_schema']:
                        available = result and result[0] > 0
                        validation_details['schema_exists'] = available
                        
                    elif feature_name == 'ssl_support':
                        available = result and result[1] == 'YES'
                        validation_details['ssl_available'] = available
                        if not available and not feature_def['required']:
                            recommendations.append("Consider enabling SSL for secure connections")
                            
                    elif feature_name == 'partitioning':
                        available = result and result[1] == 'YES'
                        validation_details['partitioning_available'] = available
                        
                    elif feature_name == 'event_scheduler':
                        available = result and result[1] in ('ON', 'YES')
                        validation_details['event_scheduler_status'] = result[1] if result else 'OFF'
                        
                    elif feature_name == 'replication':
                        available = result and result[1] == 'ON'
                        validation_details['binary_logging'] = available
                        
                    else:
                        # Generic validation for other features
                        available = result is not None and (
                            (isinstance(result[0], int) and result[0] > 0) or
                            (isinstance(result[0], str) and result[0] not in ('', 'NO', 'OFF'))
                        )
                        validation_details['query_result'] = result[0] if result else None
                        
            except Exception as e:
                available = False
                validation_details['validation_error'] = str(e)
                recommendations.append(f"Check MySQL configuration for {feature_name}")
        
        # Add feature-specific recommendations
        if not available and feature_def['required']:
            recommendations.append(f"Enable {feature_name} - this feature is required for Vedfolnir")
        elif not available and not feature_def['required']:
            recommendations.append(f"Consider enabling {feature_name} for enhanced functionality")
        
        return FeatureValidationResult(
            feature_name=feature_name,
            available=available,
            required=feature_def['required'],
            description=feature_def['description'],
            validation_details=validation_details,
            recommendations=recommendations
        )
    
    def generate_feature_report(self, results: List[FeatureValidationResult]) -> Dict[str, Any]:
        """
        Generate a comprehensive feature validation report.
        
        Args:
            results: List of feature validation results
            
        Returns:
            Dictionary containing the feature report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_features_checked': len(results),
            'required_features': [],
            'optional_features': [],
            'missing_required_features': [],
            'missing_optional_features': [],
            'all_recommendations': [],
            'overall_compatibility': True,
            'compatibility_score': 0
        }
        
        required_count = 0
        required_available = 0
        optional_count = 0
        optional_available = 0
        
        for result in results:
            feature_info = {
                'name': result.feature_name,
                'available': result.available,
                'description': result.description,
                'validation_details': result.validation_details,
                'recommendations': result.recommendations
            }
            
            if result.required:
                required_count += 1
                report['required_features'].append(feature_info)
                if result.available:
                    required_available += 1
                else:
                    report['missing_required_features'].append(result.feature_name)
                    report['overall_compatibility'] = False
            else:
                optional_count += 1
                report['optional_features'].append(feature_info)
                if result.available:
                    optional_available += 1
                else:
                    report['missing_optional_features'].append(result.feature_name)
            
            # Collect all recommendations
            report['all_recommendations'].extend(result.recommendations)
        
        # Calculate compatibility score
        total_features = required_count + optional_count
        available_features = required_available + optional_available
        report['compatibility_score'] = (available_features / total_features * 100) if total_features > 0 else 0
        
        # Add summary statistics
        report['summary'] = {
            'required_features_available': f"{required_available}/{required_count}",
            'optional_features_available': f"{optional_available}/{optional_count}",
            'overall_score': f"{report['compatibility_score']:.1f}%"
        }
        
        return report
    
    def print_feature_report(self, results: List[FeatureValidationResult]):
        """
        Print a human-readable feature validation report.
        
        Args:
            results: List of feature validation results
        """
        report = self.generate_feature_report(results)
        
        print("\n" + "="*80)
        print("🔍 MYSQL FEATURE VALIDATION REPORT")
        print("="*80)
        print(f"📅 Timestamp: {report['timestamp']}")
        print(f"📊 Compatibility Score: {report['compatibility_score']:.1f}%")
        print(f"✅ Overall Compatible: {'Yes' if report['overall_compatibility'] else 'No'}")
        print()
        
        # Required features
        print("🔴 REQUIRED FEATURES:")
        for feature in report['required_features']:
            status = "✅ Available" if feature['available'] else "❌ Missing"
            print(f"  • {feature['name']}: {status}")
            print(f"    {feature['description']}")
            if feature['recommendations']:
                for rec in feature['recommendations']:
                    print(f"    💡 {rec}")
            print()
        
        # Optional features
        print("🟡 OPTIONAL FEATURES:")
        for feature in report['optional_features']:
            status = "✅ Available" if feature['available'] else "⚠️ Not Available"
            print(f"  • {feature['name']}: {status}")
            print(f"    {feature['description']}")
            if feature['recommendations']:
                for rec in feature['recommendations']:
                    print(f"    💡 {rec}")
            print()
        
        # Summary
        print("📋 SUMMARY:")
        print(f"  • Required Features: {report['summary']['required_features_available']}")
        print(f"  • Optional Features: {report['summary']['optional_features_available']}")
        print(f"  • Overall Score: {report['summary']['overall_score']}")
        
        if report['missing_required_features']:
            print(f"\n❌ CRITICAL: Missing required features: {', '.join(report['missing_required_features'])}")
            print("   Vedfolnir may not function properly without these features.")
        
        if report['missing_optional_features']:
            print(f"\n⚠️ INFO: Missing optional features: {', '.join(report['missing_optional_features'])}")
            print("   These features would enhance Vedfolnir functionality.")
        
        print("\n" + "="*80)

def main():
    """Main function for the MySQL feature validator."""
    parser = argparse.ArgumentParser(
        description='Validate MySQL server features for Vedfolnir compatibility'
    )
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress verbose output')
    parser.add_argument('--required-only', action='store_true',
                       help='Check only required features')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    try:
        # Initialize validator
        validator = MySQLFeatureValidator()
        
        # Validate features
        results = validator.validate_all_features()
        
        if not results:
            print("❌ Failed to validate MySQL features - check connection")
            return 1
        
        # Filter results if requested
        if args.required_only:
            results = [r for r in results if r.required]
        
        # Output results
        if args.json:
            report = validator.generate_feature_report(results)
            print(json.dumps(report, indent=2))
        else:
            validator.print_feature_report(results)
        
        # Check if all required features are available
        missing_required = [r for r in results if r.required and not r.available]
        if missing_required:
            if not args.quiet:
                print(f"\n❌ {len(missing_required)} required features are missing")
            return 1
        
        if not args.quiet:
            print("\n✅ All required MySQL features are available")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Feature validation failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
