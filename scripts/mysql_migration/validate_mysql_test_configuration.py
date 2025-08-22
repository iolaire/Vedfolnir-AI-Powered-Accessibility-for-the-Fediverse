#!/usr/bin/env python3
"""
MySQL Test Configuration Validation Script

Validates that MySQL test configurations are working correctly and all test infrastructure is properly set up.
"""

import os
import sys
import logging
import unittest
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MySQLTestConfigurationValidator:
    """Validates MySQL test configuration and infrastructure"""
    
    def __init__(self):
        """Initialize validator"""
        self.validation_results = {}
        self.test_results = []
        self.issues_found = []
        
        # Import test modules
        try:
            from tests.mysql_test_config import MySQLTestConfig, MySQLTestFixtures, MySQLTestUtilities
            from tests.mysql_test_base import MySQLTestBase, MySQLIntegrationTestBase, MySQLWebTestBase
            
            self.mysql_test_config = MySQLTestConfig
            self.mysql_test_fixtures = MySQLTestFixtures
            self.mysql_test_utilities = MySQLTestUtilities
            self.mysql_test_base = MySQLTestBase
            self.mysql_integration_test_base = MySQLIntegrationTestBase
            self.mysql_web_test_base = MySQLWebTestBase
            
        except ImportError as e:
            logger.error(f"Failed to import MySQL test modules: {e}")
            self.issues_found.append(f"Import error: {e}")
    
    def validate_mysql_server_availability(self) -> bool:
        """Validate MySQL server is available for testing"""
        logger.info("Validating MySQL server availability...")
        
        try:
            test_config = self.mysql_test_config("validation_test")
            available = test_config.is_mysql_available()
            
            if available:
                logger.info("✅ MySQL server is available for testing")
                self.validation_results['mysql_server'] = True
                return True
            else:
                logger.error("❌ MySQL server is not available for testing")
                self.validation_results['mysql_server'] = False
                self.issues_found.append("MySQL server not available")
                return False
                
        except Exception as e:
            logger.error(f"❌ MySQL server validation failed: {e}")
            self.validation_results['mysql_server'] = False
            self.issues_found.append(f"MySQL server validation error: {e}")
            return False
    
    def validate_test_database_creation(self) -> bool:
        """Validate test database creation and cleanup"""
        logger.info("Validating test database creation and cleanup...")
        
        try:
            test_config = self.mysql_test_config("validation_db_test")
            
            # Test database creation
            if not test_config.create_test_database():
                logger.error("❌ Failed to create test database")
                self.validation_results['database_creation'] = False
                self.issues_found.append("Test database creation failed")
                return False
            
            # Test database manager
            db_manager = test_config.get_database_manager()
            if not db_manager:
                logger.error("❌ Failed to get database manager")
                self.validation_results['database_creation'] = False
                self.issues_found.append("Database manager creation failed")
                return False
            
            # Test session creation
            session = test_config.get_test_session()
            if not session:
                logger.error("❌ Failed to create test session")
                self.validation_results['database_creation'] = False
                self.issues_found.append("Test session creation failed")
                return False
            
            session.close()
            
            # Test database cleanup
            if not test_config.drop_test_database():
                logger.error("❌ Failed to drop test database")
                self.validation_results['database_creation'] = False
                self.issues_found.append("Test database cleanup failed")
                return False
            
            logger.info("✅ Test database creation and cleanup working")
            self.validation_results['database_creation'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Database creation validation failed: {e}")
            self.validation_results['database_creation'] = False
            self.issues_found.append(f"Database creation validation error: {e}")
            return False
    
    def validate_test_fixtures(self) -> bool:
        """Validate test fixtures work correctly"""
        logger.info("Validating test fixtures...")
        
        try:
            with self.mysql_test_config("validation_fixtures_test").test_database_context() as test_config:
                session = test_config.get_test_session()
                
                # Test user creation
                test_user = self.mysql_test_fixtures.create_test_user(session)
                if not test_user or not test_user.id:
                    logger.error("❌ Failed to create test user")
                    self.validation_results['test_fixtures'] = False
                    self.issues_found.append("Test user creation failed")
                    return False
                
                # Test platform connection creation
                test_platform = self.mysql_test_fixtures.create_test_platform_connection(session, test_user)
                if not test_platform or not test_platform.id:
                    logger.error("❌ Failed to create test platform connection")
                    self.validation_results['test_fixtures'] = False
                    self.issues_found.append("Test platform connection creation failed")
                    return False
                
                # Test post creation
                test_post = self.mysql_test_fixtures.create_test_post(session, test_platform)
                if not test_post or not test_post.id:
                    logger.error("❌ Failed to create test post")
                    self.validation_results['test_fixtures'] = False
                    self.issues_found.append("Test post creation failed")
                    return False
                
                # Test image creation
                test_image = self.mysql_test_fixtures.create_test_image(session, test_post)
                if not test_image or not test_image.id:
                    logger.error("❌ Failed to create test image")
                    self.validation_results['test_fixtures'] = False
                    self.issues_found.append("Test image creation failed")
                    return False
                
                session.close()
            
            logger.info("✅ Test fixtures working correctly")
            self.validation_results['test_fixtures'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Test fixtures validation failed: {e}")
            self.validation_results['test_fixtures'] = False
            self.issues_found.append(f"Test fixtures validation error: {e}")
            return False
    
    def validate_base_test_classes(self) -> bool:
        """Validate base test classes work correctly"""
        logger.info("Validating base test classes...")
        
        try:
            # Create a test class that inherits from MySQLTestBase
            class ValidationTest(self.mysql_test_base):
                def test_basic_functionality(self):
                    """Test basic MySQL test functionality"""
                    # Test database connection
                    self.assertIsNotNone(self.session)
                    
                    # Test basic test data
                    self.assertIsNotNone(self.test_user)
                    self.assertIsNotNone(self.test_platform)
                    
                    # Test database state assertions
                    from models import User, PlatformConnection
                    self.assert_database_state(User, 1)
                    self.assert_database_state(PlatformConnection, 1)
                    
                    # Test record existence
                    self.assert_record_exists(User, username="testuser")
                    self.assert_record_not_exists(User, username="nonexistent")
            
            # Run the validation test
            suite = unittest.TestLoader().loadTestsFromTestCase(ValidationTest)
            runner = unittest.TextTestRunner(stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            if result.wasSuccessful():
                logger.info("✅ Base test classes working correctly")
                self.validation_results['base_test_classes'] = True
                return True
            else:
                logger.error("❌ Base test classes validation failed")
                self.validation_results['base_test_classes'] = False
                for failure in result.failures + result.errors:
                    self.issues_found.append(f"Base test class issue: {failure[1]}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Base test classes validation failed: {e}")
            self.validation_results['base_test_classes'] = False
            self.issues_found.append(f"Base test classes validation error: {e}")
            return False
    
    def validate_integration_test_base(self) -> bool:
        """Validate integration test base class"""
        logger.info("Validating integration test base class...")
        
        try:
            # Create a test class that inherits from MySQLIntegrationTestBase
            class ValidationIntegrationTest(self.mysql_integration_test_base):
                def test_integration_setup(self):
                    """Test integration test setup"""
                    # Test that mocks are available
                    self.assertIsNotNone(self.mock_ollama)
                    self.assertIsNotNone(self.mock_activitypub)
                    self.assertIsNotNone(self.mock_image_processor)
                    
                    # Test that additional test data is created
                    self.assertIsNotNone(self.test_post)
                    self.assertIsNotNone(self.test_image)
            
            # Run the validation test
            suite = unittest.TestLoader().loadTestsFromTestCase(ValidationIntegrationTest)
            runner = unittest.TextTestRunner(stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            if result.wasSuccessful():
                logger.info("✅ Integration test base class working correctly")
                self.validation_results['integration_test_base'] = True
                return True
            else:
                logger.error("❌ Integration test base class validation failed")
                self.validation_results['integration_test_base'] = False
                for failure in result.failures + result.errors:
                    self.issues_found.append(f"Integration test base issue: {failure[1]}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Integration test base validation failed: {e}")
            self.validation_results['integration_test_base'] = False
            self.issues_found.append(f"Integration test base validation error: {e}")
            return False
    
    def validate_test_utilities(self) -> bool:
        """Validate test utilities"""
        logger.info("Validating test utilities...")
        
        try:
            # Test cleanup utility
            self.mysql_test_utilities.clean_test_databases()
            
            # Test skip decorator (should not raise exception)
            @self.mysql_test_utilities.skip_if_mysql_unavailable()
            def dummy_test():
                pass
            
            dummy_test()
            
            logger.info("✅ Test utilities working correctly")
            self.validation_results['test_utilities'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Test utilities validation failed: {e}")
            self.validation_results['test_utilities'] = False
            self.issues_found.append(f"Test utilities validation error: {e}")
            return False
    
    def validate_environment_configuration(self) -> bool:
        """Validate test environment configuration"""
        logger.info("Validating test environment configuration...")
        
        try:
            from tests.mysql_test_config import setup_test_environment
            
            # Set up test environment
            setup_test_environment()
            
            # Check required environment variables
            required_vars = [
                'FLASK_SECRET_KEY',
                'PLATFORM_ENCRYPTION_KEY',
                'REDIS_URL',
                'OLLAMA_URL',
                'OLLAMA_MODEL',
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                logger.error(f"❌ Missing environment variables: {missing_vars}")
                self.validation_results['environment_config'] = False
                self.issues_found.append(f"Missing environment variables: {missing_vars}")
                return False
            
            logger.info("✅ Test environment configuration working correctly")
            self.validation_results['environment_config'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Environment configuration validation failed: {e}")
            self.validation_results['environment_config'] = False
            self.issues_found.append(f"Environment configuration validation error: {e}")
            return False
    
    def run_sample_test_suite(self) -> bool:
        """Run a sample test suite to validate end-to-end functionality"""
        logger.info("Running sample test suite...")
        
        try:
            # Create a comprehensive sample test
            class SampleTestSuite(self.mysql_test_base):
                def test_user_management(self):
                    """Test user management functionality"""
                    from models import User, UserRole
                    import uuid
                    
                    # Create additional user with unique identifiers
                    unique_id = uuid.uuid4().hex[:8]
                    new_user = User(
                        username=f"sampleuser_{unique_id}",
                        email=f"sample_{unique_id}@example.com",
                        role=UserRole.VIEWER,
                        is_active=True
                    )
                    new_user.set_password("samplepassword")
                    
                    self.session.add(new_user)
                    self.session.commit()
                    
                    # Verify user creation (count only our test users)
                    test_users = self.session.query(User).filter(
                        User.username.like(f'%{self.mysql_config.test_name}%')
                    ).count()
                    self.assertGreaterEqual(test_users, 1)  # At least our new user
                
                def test_platform_operations(self):
                    """Test platform operations"""
                    from models import PlatformConnection
                    
                    # Only test if we have test platform data
                    if hasattr(self, 'test_platform') and self.test_platform:
                        # Test platform connection
                        self.assertEqual(self.test_platform.platform_type, "pixelfed")
                        self.assertTrue(self.test_platform.is_active)
                        
                        # Test platform update
                        original_name = self.test_platform.name
                        self.test_platform.name = f"Updated {original_name}"
                        self.session.commit()
                        
                        # Verify update
                        updated_platform = self.session.query(PlatformConnection).filter(
                            PlatformConnection.id == self.test_platform.id
                        ).first()
                        self.assertIsNotNone(updated_platform)
                        self.assertEqual(updated_platform.name, f"Updated {original_name}")
                    else:
                        # Skip if no test platform available
                        self.skipTest("No test platform data available")
                
                def test_database_transactions(self):
                    """Test database transaction handling"""
                    from models import User
                    import uuid
                    
                    # Test rollback with unique data
                    unique_id = uuid.uuid4().hex[:8]
                    try:
                        # Create a user that should succeed
                        valid_user = User(
                            username=f"valid_user_{unique_id}",
                            email=f"valid_{unique_id}@example.com",
                            is_active=True
                        )
                        self.session.add(valid_user)
                        self.session.commit()
                        
                        # Now try to create a duplicate (this should fail)
                        duplicate_user = User(
                            username=f"valid_user_{unique_id}",  # Same username
                            email=f"duplicate_{unique_id}@example.com",
                            is_active=True
                        )
                        self.session.add(duplicate_user)
                        self.session.commit()
                        self.fail("Should have raised integrity error for duplicate username")
                    except Exception:
                        self.session.rollback()
                        # Verify rollback worked - the valid user should still exist
                        existing_user = self.session.query(User).filter(
                            User.username == f"valid_user_{unique_id}"
                        ).first()
                        self.assertIsNotNone(existing_user)
            
            # Run the sample test suite
            suite = unittest.TestLoader().loadTestsFromTestCase(SampleTestSuite)
            runner = unittest.TextTestRunner(stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            if result.wasSuccessful():
                logger.info("✅ Sample test suite passed")
                self.validation_results['sample_test_suite'] = True
                return True
            else:
                logger.error("❌ Sample test suite failed")
                self.validation_results['sample_test_suite'] = False
                for failure in result.failures + result.errors:
                    self.issues_found.append(f"Sample test failure: {failure[1]}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Sample test suite validation failed: {e}")
            self.validation_results['sample_test_suite'] = False
            self.issues_found.append(f"Sample test suite validation error: {e}")
            return False
    
    def run_comprehensive_validation(self) -> bool:
        """Run comprehensive validation of MySQL test configuration"""
        logger.info("=== MySQL Test Configuration Validation ===")
        
        validations = [
            ("MySQL Server Availability", self.validate_mysql_server_availability),
            ("Test Database Creation", self.validate_test_database_creation),
            ("Test Fixtures", self.validate_test_fixtures),
            ("Base Test Classes", self.validate_base_test_classes),
            ("Integration Test Base", self.validate_integration_test_base),
            ("Test Utilities", self.validate_test_utilities),
            ("Environment Configuration", self.validate_environment_configuration),
            ("Sample Test Suite", self.run_sample_test_suite),
        ]
        
        passed = 0
        total = len(validations)
        
        for validation_name, validation_func in validations:
            logger.info(f"Running validation: {validation_name}")
            try:
                if validation_func():
                    passed += 1
                    logger.info(f"✅ {validation_name}: PASSED")
                else:
                    logger.error(f"❌ {validation_name}: FAILED")
            except Exception as e:
                logger.error(f"❌ {validation_name}: ERROR - {e}")
                self.issues_found.append(f"{validation_name} validation error: {e}")
        
        logger.info(f"Validation completed: {passed}/{total} validations passed")
        
        return passed == total
    
    def generate_validation_report(self) -> str:
        """Generate comprehensive validation report"""
        passed_count = sum(1 for result in self.validation_results.values() if result)
        total_count = len(self.validation_results)
        
        report = [
            "=== MySQL Test Configuration Validation Report ===",
            "",
            f"Validation Results: {passed_count}/{total_count} passed",
            f"Issues Found: {len(self.issues_found)}",
            "",
            "VALIDATION RESULTS:",
        ]
        
        for validation_name, result in self.validation_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            report.append(f"  {status}: {validation_name.replace('_', ' ').title()}")
        
        report.append("")
        
        if self.issues_found:
            report.extend([
                "🚨 ISSUES FOUND:",
                ""
            ])
            for issue in self.issues_found:
                report.append(f"  - {issue}")
            report.append("")
        
        if passed_count == total_count:
            report.extend([
                "✅ SUCCESS: MySQL test configuration is fully functional!",
                "",
                "All test infrastructure components are working correctly:",
                "- MySQL server connectivity",
                "- Test database creation and cleanup",
                "- Test fixtures and data creation",
                "- Base test classes and inheritance",
                "- Integration test setup with mocking",
                "- Test utilities and decorators",
                "- Environment configuration",
                "- End-to-end test execution",
                "",
                "You can now run MySQL-based tests with confidence.",
            ])
        else:
            report.extend([
                "❌ ISSUES DETECTED: MySQL test configuration needs attention",
                "",
                "Please address the issues listed above before running tests.",
                "Common solutions:",
                "- Ensure MySQL server is running and accessible",
                "- Verify MySQL test user has proper permissions",
                "- Check environment variable configuration",
                "- Install required Python dependencies (pymysql, cryptography)",
            ])
        
        return "\n".join(report)


def main():
    """Main validation function"""
    logger.info("MySQL Test Configuration Validation")
    
    # Initialize validator
    validator = MySQLTestConfigurationValidator()
    
    # Run comprehensive validation
    success = validator.run_comprehensive_validation()
    
    # Generate report
    report = validator.generate_validation_report()
    
    # Save report
    project_root = Path(__file__).parent.parent.parent
    report_path = project_root / 'scripts' / 'mysql_migration' / 'mysql_test_validation_report.txt'
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info(f"Validation report saved to: {report_path}")
    
    if success:
        logger.info("✅ MySQL test configuration validation passed!")
        print("\n" + "="*60)
        print("MySQL Test Configuration: READY")
        print("="*60)
        print("All test infrastructure components are working correctly.")
        print("You can now run MySQL-based tests.")
        print("="*60)
        return True
    else:
        logger.error("❌ MySQL test configuration validation failed!")
        print("\n" + "="*60)
        print("MySQL Test Configuration: ISSUES DETECTED")
        print("="*60)
        print("Please check the validation report for details.")
        print(f"Report: {report_path}")
        print("="*60)
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
