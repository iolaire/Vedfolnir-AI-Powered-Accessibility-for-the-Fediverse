#!/usr/bin/env python3
"""
Database Configuration Cleanup Validation Script

Validates that all SQLite-specific configuration options have been removed
and that the system is configured for MySQL-only operation.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConfigValidator:
    """Validates database configuration cleanup"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.violations = []
        
        # Patterns that should not exist after cleanup
        self.forbidden_patterns = [
            ('database_dir', 'SQLite database directory references'),
            ('db_path', 'SQLite database path references'),
            ('\.db["\']', 'SQLite database file references'),
            ('MySQL:///', 'Deprecated MySQL URL format'),
            ('sqlite3\.', 'SQLite module usage'),
            ('PRAGMA ', 'SQLite PRAGMA statements'),
            ('sqlite_master', 'SQLite system table references'),
        ]
    
    def test_config_class_structure(self) -> bool:
        """Test that Config classes have proper MySQL-only structure"""
        logger.info("Testing Config class structure...")
        
        try:
            sys.path.append(str(self.project_root))
            from config import Config, StorageConfig, DatabaseConfig
            
            # Test StorageConfig
            storage_config = StorageConfig()
            
            # Should not have database_dir attribute
            if hasattr(storage_config, 'database_dir'):
                self.violations.append("StorageConfig still has database_dir attribute")
                return False
            
            # Should have MySQL database_url
            if not storage_config.database_url.startswith('mysql+pymysql://'):
                self.violations.append(f"StorageConfig database_url is not MySQL: {storage_config.database_url}")
                return False
            
            # Test DatabaseConfig
            db_config = DatabaseConfig()
            
            # Should have MySQL-specific settings
            required_attrs = ['pool_size', 'max_overflow', 'pool_timeout', 'pool_recycle']
            for attr in required_attrs:
                if not hasattr(db_config, attr):
                    self.violations.append(f"DatabaseConfig missing MySQL attribute: {attr}")
                    return False
            
            # Test main Config
            config = Config()
            
            # Should have proper storage config
            if hasattr(config.storage, 'database_dir'):
                self.violations.append("Config.storage still has database_dir")
                return False
            
            logger.info("✅ Config class structure is MySQL-only")
            return True
            
        except Exception as e:
            self.violations.append(f"Config class test failed: {e}")
            return False
    
    def test_database_url_validation(self) -> bool:
        """Test that database URL validation is MySQL-only"""
        logger.info("Testing database URL validation...")
        
        try:
            sys.path.append(str(self.project_root))
            from config import Config
            
            config = Config()
            
            # Test validation method
            validation_errors = config.validate_configuration()
            
            # Should validate MySQL URLs properly
            original_url = os.environ.get('DATABASE_URL')
            
            # Test with invalid URL
            os.environ['DATABASE_URL'] = 'sqlite:///test.db'
            try:
                test_config = Config()
                test_errors = test_config.validate_configuration()
                
                # Should have MySQL validation error
                mysql_error_found = any('mysql+pymysql://' in error.lower() for error in test_errors)
                if not mysql_error_found:
                    self.violations.append("Database URL validation doesn't properly reject non-MySQL URLs")
                    return False
                
            finally:
                # Restore original URL
                if original_url:
                    os.environ['DATABASE_URL'] = original_url
                elif 'DATABASE_URL' in os.environ:
                    del os.environ['DATABASE_URL']
            
            logger.info("✅ Database URL validation is MySQL-only")
            return True
            
        except Exception as e:
            self.violations.append(f"Database URL validation test failed: {e}")
            return False
    
    def test_database_manager_integration(self) -> bool:
        """Test that DatabaseManager works with cleaned config"""
        logger.info("Testing DatabaseManager integration...")
        
        try:
            sys.path.append(str(self.project_root))
            from config import Config
            from database import DatabaseManager
            
            config = Config()
            db_manager = DatabaseManager(config)
            
            # Should have MySQL-specific methods
            mysql_methods = [
                'handle_mysql_error',
                'test_mysql_connection', 
                'get_mysql_performance_stats',
                'generate_mysql_troubleshooting_guide'
            ]
            
            for method in mysql_methods:
                if not hasattr(db_manager, method):
                    self.violations.append(f"DatabaseManager missing MySQL method: {method}")
                    return False
            
            # Should not have SQLite-specific methods
            sqlite_methods = ['handle_sqlite_error', 'test_sqlite_connection']
            for method in sqlite_methods:
                if hasattr(db_manager, method):
                    self.violations.append(f"DatabaseManager still has SQLite method: {method}")
                    return False
            
            logger.info("✅ DatabaseManager integration is MySQL-only")
            return True
            
        except Exception as e:
            self.violations.append(f"DatabaseManager integration test failed: {e}")
            return False
    
    def test_file_patterns(self) -> bool:
        """Test that forbidden patterns don't exist in code files"""
        logger.info("Testing for forbidden patterns in code files...")
        
        violations_found = False
        
        for file_path in self.project_root.rglob('*.py'):
            # Skip test files and migration scripts
            if any(skip in str(file_path) for skip in ['test_', 'migration', '__pycache__', '.git']):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    # Skip comments
                    if line.strip().startswith('#'):
                        continue
                    
                    for pattern, description in self.forbidden_patterns:
                        import re
                        if re.search(pattern, line, re.IGNORECASE):
                            self.violations.append(
                                f"{file_path}:{line_num} - {description}: {line.strip()}"
                            )
                            violations_found = True
                            
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
        
        if not violations_found:
            logger.info("✅ No forbidden patterns found in code files")
            return True
        else:
            logger.error(f"❌ Found {len([v for v in self.violations if 'forbidden pattern' in v.lower()])} forbidden patterns")
            return False
    
    def test_environment_variables(self) -> bool:
        """Test that environment variables are MySQL-focused"""
        logger.info("Testing environment variable configuration...")
        
        # Check .env.example if it exists
        env_example = self.project_root / '.env.example'
        if env_example.exists():
            try:
                with open(env_example, 'r') as f:
                    content = f.read()
                
                # Should have MySQL DATABASE_URL example
                if 'mysql+pymysql://' not in content:
                    self.violations.append(".env.example missing MySQL DATABASE_URL example")
                    return False
                
                # Should not have SQLite examples
                if 'sqlite:///' in content:
                    self.violations.append(".env.example still contains SQLite URL examples")
                    return False
                
                logger.info("✅ Environment variable examples are MySQL-only")
                return True
                
            except Exception as e:
                self.violations.append(f"Environment variable test failed: {e}")
                return False
        else:
            logger.warning("⚠️  .env.example not found - skipping environment variable test")
            return True
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all validation tests"""
        logger.info("=== Database Configuration Cleanup Validation ===")
        
        tests = {
            'config_class_structure': self.test_config_class_structure(),
            'database_url_validation': self.test_database_url_validation(),
            'database_manager_integration': self.test_database_manager_integration(),
            'file_patterns': self.test_file_patterns(),
            'environment_variables': self.test_environment_variables(),
        }
        
        return tests
    
    def generate_report(self, test_results: Dict[str, bool]) -> str:
        """Generate validation report"""
        passed = sum(test_results.values())
        total = len(test_results)
        
        report = [
            "=== Database Configuration Cleanup Validation Report ===",
            f"Tests passed: {passed}/{total}",
            f"Violations found: {len(self.violations)}",
            ""
        ]
        
        # Test results
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            report.append(f"{status}: {test_name.replace('_', ' ').title()}")
        
        report.append("")
        
        # Violations
        if self.violations:
            report.extend([
                "🚨 VIOLATIONS FOUND:",
                ""
            ])
            for violation in self.violations:
                report.append(f"  - {violation}")
        else:
            report.extend([
                "✅ SUCCESS: No violations found!",
                "Database configuration has been successfully cleaned up for MySQL-only operation.",
            ])
        
        return "\n".join(report)


def main():
    """Main validation function"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info(f"Validating database configuration cleanup in: {project_root}")
    
    validator = DatabaseConfigValidator(project_root)
    test_results = validator.run_all_tests()
    
    # Generate report
    report = validator.generate_report(test_results)
    
    # Save report
    report_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'database_config_validation_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    
    # Print summary
    passed = sum(test_results.values())
    total = len(test_results)
    
    logger.info(f"Validation completed: {passed}/{total} tests passed")
    logger.info(f"Violations found: {len(validator.violations)}")
    logger.info(f"Report saved to: {report_path}")
    
    if passed == total and len(validator.violations) == 0:
        logger.info("✅ SUCCESS: Database configuration cleanup validation passed!")
        return True
    else:
        logger.error("❌ FAILURE: Database configuration cleanup validation failed!")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
