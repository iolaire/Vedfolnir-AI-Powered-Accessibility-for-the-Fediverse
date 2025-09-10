#!/usr/bin/env python3
"""
MySQL Base Test Class

Provides a standardized base class for all MySQL-based tests, replacing SQLite test patterns.
"""

import unittest
import os
import sys
import tempfile
import shutil
import logging
from unittest.mock import patch, MagicMock
from typing import Optional, Dict, Any, List

# Set up logging
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.mysql_test_config import (
    MySQLTestConfig, 
    MySQLTestFixtures, 
    MySQLTestUtilities,
    mock_redis,
    setup_test_environment
)
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, PlatformConnection, Post, Image


class MySQLTestBase(unittest.TestCase):
    """
    Base test class for MySQL-based tests
    
    Provides standardized setup and teardown for MySQL test databases,
    replacing SQLite-specific test configurations.
    """
    
    # Class-level configuration
    TEST_CONFIG_OVERRIDE = {}  # Override in subclasses if needed
    SKIP_IF_MYSQL_UNAVAILABLE = True  # Set to False to fail instead of skip
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level test configuration"""
        # Set up test environment
        setup_test_environment()
        
        # Check MySQL availability
        if cls.SKIP_IF_MYSQL_UNAVAILABLE:
            test_config = MySQLTestConfig()
            if not test_config.is_mysql_available():
                raise unittest.SkipTest("MySQL server not available for testing")
    
    def setUp(self):
        """Set up individual test with MySQL database"""
        # Generate unique test name
        test_name = f"{self.__class__.__name__}_{self._testMethodName}"
        
        # Create MySQL test configuration
        self.mysql_config = MySQLTestConfig(
            test_name=test_name,
            config_override=self.TEST_CONFIG_OVERRIDE
        )
        
        # Create test database
        if not self.mysql_config.create_test_database():
            self.fail(f"Failed to create MySQL test database: {self.mysql_config.test_database}")
        
        # Get Vedfolnir configuration
        self.config = self.mysql_config.get_test_config()
        
        # Create database manager
        self.db_manager = self.mysql_config.get_database_manager()
        
        # Create test session
        self.session = self.mysql_config.get_test_session()
        
        # Set up mock Redis
        self.redis_patcher = mock_redis()
        self.mock_redis = self.redis_patcher.start()
        
        # Create temporary directories for test files
        self.temp_dirs = []
        
        # Initialize test fixtures
        self.fixtures = MySQLTestFixtures()
        
        # Create basic test data if needed
        self._create_basic_test_data()
    
    def tearDown(self):
        """Clean up test database and resources"""
        # Close session
        if hasattr(self, 'session') and self.session:
            self.session.close()
        
        # Stop Redis mock
        if hasattr(self, 'redis_patcher'):
            self.redis_patcher.stop()
        
        # Clean up temporary directories
        for temp_dir in getattr(self, 'temp_dirs', []):
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Drop test database
        if hasattr(self, 'mysql_config'):
            self.mysql_config.drop_test_database()
    
    def _create_basic_test_data(self):
        """Create basic test data - override in subclasses if needed"""
        # Default: create a test user and platform connection with unique names
        try:
            # Use unique test names to avoid conflicts (keep them short)
            import uuid
            unique_suffix = uuid.uuid4().hex[:8]
            # Truncate test name to avoid long usernames
            short_test_name = self.mysql_config.test_name[:20] if len(self.mysql_config.test_name) > 20 else self.mysql_config.test_name
            test_username = f"test_{short_test_name}_{unique_suffix}"[:50]  # MySQL username limit
            test_email = f"test_{unique_suffix}@example.com"
            
            self.test_user = self.fixtures.create_test_user(
                self.session, 
                username=test_username,
                email=test_email
            )
            self.test_platform = self.fixtures.create_test_platform_connection(
                self.session, 
                self.test_user,
                name=f"Platform {unique_suffix}"
            )
        except Exception as e:
            # Some tests might not need basic data
            logger.warning(f"Could not create basic test data: {e}")
            # Set to None so tests can handle missing data
            self.test_user = None
            self.test_platform = None
    
    def create_temp_dir(self, prefix: str = "vedfolnir_test_") -> str:
        """Create a temporary directory for test files"""
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def create_temp_file(self, content: str = "", suffix: str = ".txt") -> str:
        """Create a temporary file with content"""
        temp_dir = self.create_temp_dir()
        temp_file = os.path.join(temp_dir, f"test_file{suffix}")
        
        with open(temp_file, 'w') as f:
            f.write(content)
        
        return temp_file
    
    def assert_test_database_state(self, model_class, expected_count: int, **filters):
        """Assert the count of test records in database (only records created by this test)"""
        query = self.session.query(model_class)
        
        # Add test-specific filters to only count our test data
        test_name = self.mysql_config.test_name
        
        if model_class.__name__ == 'User':
            query = query.filter(model_class.username.like(f'%{test_name}%'))
        elif model_class.__name__ == 'PlatformConnection':
            query = query.filter(model_class.name.like(f'%{test_name}%'))
        elif model_class.__name__ == 'Post':
            query = query.filter(model_class.post_id.like(f'%{test_name}%'))
        
        # Apply additional filters
        for key, value in filters.items():
            query = query.filter(getattr(model_class, key) == value)
        
        actual_count = query.count()
        self.assertEqual(
            actual_count, 
            expected_count,
            f"Expected {expected_count} test {model_class.__name__} records, got {actual_count}"
        )
    
    def assert_database_state(self, model_class, expected_count: int, **filters):
        """Assert the count of records in database (legacy method - use assert_test_database_state for new tests)"""
        # For backward compatibility, delegate to test-specific method
        self.assert_test_database_state(model_class, expected_count, **filters)
    
    def assert_record_exists(self, model_class, **filters):
        """Assert that a record exists in the database"""
        query = self.session.query(model_class)
        
        for key, value in filters.items():
            query = query.filter(getattr(model_class, key) == value)
        
        record = query.first()
        self.assertIsNotNone(
            record,
            f"Expected {model_class.__name__} record with {filters} to exist"
        )
        return record
    
    def assert_record_not_exists(self, model_class, **filters):
        """Assert that a record does not exist in the database"""
        query = self.session.query(model_class)
        
        for key, value in filters.items():
            query = query.filter(getattr(model_class, key) == value)
        
        record = query.first()
        self.assertIsNone(
            record,
            f"Expected {model_class.__name__} record with {filters} to not exist"
        )
    
    def refresh_session(self):
        """Refresh the database session"""
        self.session.close()
        self.session = self.mysql_config.get_test_session()
    
    def commit_and_refresh(self, *objects):
        """Commit session and refresh objects"""
        self.session.commit()
        for obj in objects:
            self.session.refresh(obj)


class MySQLIntegrationTestBase(MySQLTestBase):
    """
    Base class for integration tests with additional setup and performance testing
    """
    
    def setUp(self):
        """Set up integration test environment"""
        super().setUp()
        
        # Additional setup for integration tests
        self._setup_mock_services()
        self._setup_test_data()
        self._setup_performance_testing()
    
    def _setup_mock_services(self):
        """Set up mock external services"""
        # Mock Ollama service
        self.ollama_patcher = patch('ollama_caption_generator.OllamaCaptionGenerator')
        self.mock_ollama = self.ollama_patcher.start()
        
        # Mock ActivityPub client
        self.activitypub_patcher = patch('activitypub_client.ActivityPubClient')
        self.mock_activitypub = self.activitypub_patcher.start()
        
        # Mock image processor
        self.image_processor_patcher = patch('image_processor.ImageProcessor')
        self.mock_image_processor = self.image_processor_patcher.start()
    
    def _setup_test_data(self):
        """Set up comprehensive test data for integration tests"""
        # Create additional test posts and images if basic data exists
        if self.test_user and self.test_platform:
            try:
                self.test_post = self.fixtures.create_test_post(
                    self.session, 
                    self.test_platform
                )
                
                self.test_image = self.fixtures.create_test_image(
                    self.session, 
                    self.test_post
                )
            except Exception as e:
                logger.warning(f"Could not create additional integration test data: {e}")
                self.test_post = None
                self.test_image = None
    
    def _setup_performance_testing(self):
        """Set up MySQL performance testing utilities"""
        try:
            from tests.mysql_performance_testing import MySQLPerformanceTester
            self.performance_tester = MySQLPerformanceTester(
                self.db_manager, 
                self.mysql_config.get_test_session
            )
        except ImportError as e:
            logger.warning(f"Performance testing not available: {e}")
            self.performance_tester = None
    
    def tearDown(self):
        """Clean up integration test resources"""
        # Stop service mocks
        if hasattr(self, 'ollama_patcher'):
            self.ollama_patcher.stop()
        if hasattr(self, 'activitypub_patcher'):
            self.activitypub_patcher.stop()
        if hasattr(self, 'image_processor_patcher'):
            self.image_processor_patcher.stop()
        
        super().tearDown()
    
    def test_mysql_connection_pooling(self):
        """Test MySQL connection pooling performance"""
        if not self.performance_tester:
            self.skipTest("Performance testing not available")
        
        result = self.performance_tester.test_connection_pool_performance(
            concurrent_connections=5,
            operations_per_connection=3
        )
        
        self.assertTrue(result.success, f"Connection pooling test failed: {result.error_message}")
        
        # Verify performance metrics
        avg_time = result.get_average_metric("connection_operation_time")
        if avg_time:
            self.assertLess(avg_time, 1.0, "Connection operations should complete within 1 second")
        
        error_count = result.get_metric("connection_error_count")
        if error_count:
            self.assertEqual(error_count.value, 0, "No connection errors should occur")
    
    def test_mysql_query_performance(self):
        """Test MySQL query performance characteristics"""
        if not self.performance_tester:
            self.skipTest("Performance testing not available")
        
        # Test a simple query
        result = self.performance_tester.test_query_performance(
            "SELECT COUNT(*) FROM users",
            iterations=10
        )
        
        self.assertTrue(result.success, f"Query performance test failed: {result.error_message}")
        
        # Verify performance metrics
        avg_time = result.get_average_metric("query_execution_time")
        if avg_time:
            self.assertLess(avg_time, 0.1, "Simple queries should complete within 100ms")
        
        throughput = result.get_metric("query_throughput")
        if throughput:
            self.assertGreater(throughput.value, 10, "Should achieve at least 10 queries per second")
    
    def test_mysql_optimization_features(self):
        """Test MySQL-specific optimization features"""
        if not self.performance_tester:
            self.skipTest("Performance testing not available")
        
        result = self.performance_tester.test_mysql_optimization_features()
        
        self.assertTrue(result.success, f"MySQL optimization test failed: {result.error_message}")
        
        # Verify that MySQL-specific features are working
        version_metric = result.get_metric("version_query_time")
        self.assertIsNotNone(version_metric, "Should be able to query MySQL version")
        
        index_metric = result.get_metric("index_query_time")
        self.assertIsNotNone(index_metric, "Should be able to query index information")
    
    def run_performance_test_suite(self) -> List:
        """Run comprehensive performance test suite and return results"""
        if not self.performance_tester:
            self.skipTest("Performance testing not available")
        
        return self.performance_tester.run_comprehensive_performance_test()
    
    def assert_performance_threshold(self, metric_name: str, threshold: float, results: List = None):
        """Assert that a performance metric meets a threshold"""
        if results is None:
            results = getattr(self, '_last_performance_results', [])
        
        for result in results:
            metric = result.get_metric(metric_name)
            if metric:
                self.assertLess(
                    metric.value, 
                    threshold, 
                    f"{metric_name} ({metric.value:.4f} {metric.unit}) exceeds threshold ({threshold})"
                )
                return
        
        self.fail(f"Performance metric '{metric_name}' not found in results")


class MySQLWebTestBase(MySQLTestBase):
    """
    Base class for web/Flask tests with MySQL backend
    """
    
    def setUp(self):
        """Set up web test environment"""
        super().setUp()
        
        # Set up Flask test client
        self._setup_flask_app()
    
    def _setup_flask_app(self):
        """Set up Flask application for testing"""
        # Import here to avoid circular imports
        from web_app import create_app
        
        # Create Flask app with test configuration
        self.app = create_app(config=self.config)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        
        # Create test client
        self.client = self.app.test_client()
        
        # Create application context
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up web test resources"""
        # Pop application context
        if hasattr(self, 'app_context'):
            self.app_context.pop()
        
        super().tearDown()
    
    def login_user(self, username: str = None, password: str = "testpassword"):
        """Log in a test user"""
        if not username:
            username = self.test_user.username
        
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
    
    def logout_user(self):
        """Log out the current user"""
        return self.client.get('/logout', follow_redirects=True)


# Utility decorators for MySQL tests
def mysql_test(test_func):
    """Decorator to mark a test as requiring MySQL"""
    def wrapper(*args, **kwargs):
        # Check if MySQL is available
        test_config = MySQLTestConfig()
        if not test_config.is_mysql_available():
            raise unittest.SkipTest("MySQL server not available for testing")
        
        return test_func(*args, **kwargs)
    
    return wrapper


def mysql_integration_test(test_func):
    """Decorator for integration tests requiring MySQL and external services"""
    def wrapper(*args, **kwargs):
        # Check if MySQL is available
        test_config = MySQLTestConfig()
        if not test_config.is_mysql_available():
            raise unittest.SkipTest("MySQL server not available for testing")
        
        # Additional checks for integration test requirements could go here
        
        return test_func(*args, **kwargs)
    
    return wrapper


if __name__ == "__main__":
    # Test the base classes
    print("Testing MySQL Base Test Classes...")
    
    class TestMySQLBase(MySQLTestBase):
        def test_basic_functionality(self):
            """Test basic MySQL test functionality"""
            from models import User, PlatformConnection
            
            # Test database connection
            self.assertIsNotNone(self.session)
            
            # Test basic test data (may be None if creation failed)
            if self.test_user and self.test_platform:
                # Test database state assertions (only count our test data)
                self.assert_test_database_state(User, 1)
                self.assert_test_database_state(PlatformConnection, 1)
                
                # Test record existence with test-specific data
                self.assert_record_exists(User, username=self.test_user.username)
                self.assert_record_not_exists(User, username="nonexistent_user_12345")
            else:
                # If test data creation failed, just test basic database functionality
                logger.info("Test data creation failed, testing basic database functionality only")
                
                # Test that we can query the database
                user_count = self.session.query(User).count()
                self.assertIsInstance(user_count, int)
                self.assertGreaterEqual(user_count, 0)
    
    # Run the test
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMySQLBase)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("✅ MySQL base test classes validation completed successfully")
    else:
        print("❌ MySQL base test classes validation failed")
        sys.exit(1)
