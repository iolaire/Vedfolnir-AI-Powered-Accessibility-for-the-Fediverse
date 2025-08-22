#!/usr/bin/env python3
"""
MySQL Test Configuration Module

Provides standardized MySQL test database configuration and utilities for all test suites.
Replaces SQLite-specific test configurations with MySQL-optimized test environments.
"""

import os
import sys
import logging
import tempfile
import uuid
from typing import Optional, Dict, Any
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DatabaseConfig, StorageConfig
from database import DatabaseManager
from models import Base
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MySQLTestConfig:
    """MySQL test database configuration and management"""
    
    # Default MySQL test configuration
    DEFAULT_TEST_CONFIG = {
        'host': 'localhost',
        'port': 3306,
        'user': 'database_user_1d7b0d0696a20',
        'password': 'EQA&bok7',
        'database': 'vedfolnir',  # Use existing database
        'charset': 'utf8mb4',
        'driver': 'pymysql'
    }
    
    def __init__(self, test_name: str = None, config_override: Dict[str, Any] = None):
        """
        Initialize MySQL test configuration
        
        Args:
            test_name: Name of the test (used for table prefixes)
            config_override: Override default configuration values
        """
        self.test_name = test_name or f"test_{uuid.uuid4().hex[:8]}"
        self.config = {**self.DEFAULT_TEST_CONFIG}
        
        if config_override:
            self.config.update(config_override)
        
        # Load from environment if available
        self._load_from_environment()
        
        # Use table prefix instead of separate database
        self.table_prefix = f"test_{self.test_name}_"
        
        # Build connection URL for existing database
        self.test_url = self._build_connection_url(self.config['database'])
        
        # Initialize engines
        self.test_engine = None
        self.test_session_factory = None
        
        logger.info(f"MySQL test config initialized for: {self.test_name}")
        logger.info(f"Using database: {self.config['database']} with table prefix: {self.table_prefix}")
    
    def _load_from_environment(self):
        """Load MySQL test configuration from environment variables"""
        env_mapping = {
            'host': 'MYSQL_TEST_HOST',
            'port': 'MYSQL_TEST_PORT',
            'user': 'MYSQL_TEST_USER',
            'password': 'MYSQL_TEST_PASSWORD',
            'database': 'MYSQL_TEST_DATABASE',
        }
        
        for key, env_var in env_mapping.items():
            if os.getenv(env_var):
                if key == 'port':
                    self.config[key] = int(os.getenv(env_var))
                else:
                    self.config[key] = os.getenv(env_var)
    
    def _build_connection_url(self, database: str) -> str:
        """Build MySQL connection URL"""
        return (
            f"mysql+{self.config['driver']}://"
            f"{self.config['user']}:{self.config['password']}@"
            f"{self.config['host']}:{self.config['port']}/"
            f"{database}?charset={self.config['charset']}"
        )
    
    def create_test_database(self) -> bool:
        """Set up test environment with table prefixes"""
        try:
            # Connect to existing database
            self.test_engine = create_engine(self.test_url, echo=False)
            self.test_session_factory = sessionmaker(bind=self.test_engine)
            
            # Test connection
            with self.test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Create tables with prefixes (we'll modify Base metadata for this)
            # For now, we'll use the existing tables and clean them for testing
            self._cleanup_test_tables()
            
            logger.info(f"✅ Test environment ready with table prefix: {self.table_prefix}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to set up test environment: {e}")
            return False
    
    def _cleanup_test_tables(self):
        """Clean up any existing test data"""
        try:
            with self.test_engine.connect() as conn:
                # Clean up test data by deleting records that match our test patterns
                # This is safer than dropping/creating tables
                test_patterns = [
                    f"test_{self.test_name}%",
                    f"%{self.test_name}%"
                ]
                
                # Clean up in reverse dependency order
                tables_to_clean = [
                    'images', 'posts', 'user_sessions', 'platform_connections', 
                    'processing_runs', 'caption_generation_tasks', 
                    'caption_generation_user_settings', 'users'
                ]
                
                for table in tables_to_clean:
                    try:
                        # Delete test records (be very careful with patterns)
                        for pattern in test_patterns:
                            if table == 'users':
                                conn.execute(text(f"DELETE FROM {table} WHERE username LIKE :pattern"), {"pattern": pattern})
                            elif table == 'posts':
                                conn.execute(text(f"DELETE FROM {table} WHERE post_id LIKE :pattern"), {"pattern": pattern})
                            elif table == 'platform_connections':
                                conn.execute(text(f"DELETE FROM {table} WHERE name LIKE :pattern"), {"pattern": pattern})
                    except Exception as e:
                        # Ignore cleanup errors for non-existent tables
                        pass
                
                conn.commit()
                
        except Exception as e:
            logger.warning(f"Test table cleanup warning: {e}")
    
    def drop_test_database(self) -> bool:
        """Clean up test environment"""
        try:
            # Clean up test data instead of dropping database
            self._cleanup_test_tables()
            
            # Clean up engines
            if self.test_engine:
                self.test_engine.dispose()
            
            logger.info(f"✅ Test environment cleaned up: {self.table_prefix}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clean up test environment: {e}")
            return False
    
    def get_test_config(self) -> Config:
        """Get Vedfolnir Config object configured for MySQL testing"""
        config = Config()
        
        # Override storage configuration for testing
        config.storage = StorageConfig(
            base_dir=tempfile.mkdtemp(prefix="vedfolnir_test_"),
            images_dir=tempfile.mkdtemp(prefix="vedfolnir_test_images_"),
            logs_dir=tempfile.mkdtemp(prefix="vedfolnir_test_logs_"),
            database_url=self.test_url,
            db_config=DatabaseConfig(
                pool_size=5,  # Smaller pool for testing
                max_overflow=10,
                pool_timeout=10,
                pool_recycle=300,  # Shorter recycle for tests
                query_logging=False
            )
        )
        
        return config
    
    def get_database_manager(self) -> DatabaseManager:
        """Get DatabaseManager configured for MySQL testing"""
        config = self.get_test_config()
        db_manager = DatabaseManager(config)
        return db_manager
    
    def get_test_session(self):
        """Get SQLAlchemy session for testing"""
        if not self.test_session_factory:
            raise RuntimeError("Test database not initialized. Call create_test_database() first.")
        
        return self.test_session_factory()
    
    def is_mysql_available(self) -> bool:
        """Check if MySQL server is available for testing"""
        try:
            engine = create_engine(self.test_url, echo=False)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            engine.dispose()
            return True
            
        except Exception as e:
            logger.warning(f"MySQL not available for testing: {e}")
            return False
    
    @contextmanager
    def test_database_context(self):
        """Context manager for test database lifecycle"""
        try:
            if not self.create_test_database():
                raise RuntimeError(f"Failed to set up test environment with prefix: {self.table_prefix}")
            
            yield self
            
        finally:
            self.drop_test_database()


class MySQLTestFixtures:
    """MySQL-compatible test fixtures and data"""
    
    @staticmethod
    def create_test_user(session, username: str = None, email: str = None):
        """Create a test user with MySQL-compatible data"""
        from models import User, UserRole
        import uuid
        
        # Generate unique identifiers if not provided
        unique_id = uuid.uuid4().hex[:8]
        username = username or f"testuser_{unique_id}"
        email = email or f"test_{unique_id}@example.com"
        
        user = User(
            username=username,
            email=email,
            role=UserRole.REVIEWER,
            is_active=True,
            email_verified=True
        )
        user.set_password("testpassword")
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return user
    
    @staticmethod
    def create_test_platform_connection(session, user, name: str = None):
        """Create a test platform connection with MySQL-compatible data"""
        from models import PlatformConnection
        import uuid
        
        # Generate unique name if not provided
        unique_id = uuid.uuid4().hex[:8]
        name = name or f"Test Platform {unique_id}"
        
        platform = PlatformConnection(
            user_id=user.id,
            name=name,
            platform_type="pixelfed",
            instance_url="https://test.pixelfed.social",
            username=f"testuser_{unique_id}",
            is_active=True,
            is_default=True
        )
        
        # Set encrypted credentials
        platform.access_token = f"test_access_token_{unique_id}"
        platform.client_key = f"test_client_key_{unique_id}"
        platform.client_secret = f"test_client_secret_{unique_id}"
        
        session.add(platform)
        session.commit()
        session.refresh(platform)
        
        return platform
    
    @staticmethod
    def create_test_post(session, platform_connection, post_id: str = None):
        """Create a test post with MySQL-compatible data"""
        from models import Post
        import uuid
        
        # Generate unique post ID if not provided
        unique_id = uuid.uuid4().hex[:8]
        post_id = post_id or f"test_post_{unique_id}"
        
        post = Post(
            post_id=post_id,
            user_id=f"test_user_{unique_id}",
            post_url=f"https://test.pixelfed.social/p/{post_id}",
            post_content="Test post content",
            platform_connection_id=platform_connection.id
        )
        
        session.add(post)
        session.commit()
        session.refresh(post)
        
        return post
    
    @staticmethod
    def create_test_image(session, post, attachment_index: int = 0):
        """Create a test image with MySQL-compatible data"""
        from models import Image, ProcessingStatus
        import uuid
        
        # Generate unique identifiers
        unique_id = uuid.uuid4().hex[:8]
        
        image = Image(
            post_id=post.id,
            image_url=f"https://test.pixelfed.social/storage/media/test_image_{unique_id}.jpg",
            local_path=f"/tmp/test_image_{unique_id}.jpg",
            original_filename=f"test_image_{unique_id}.jpg",
            media_type="image/jpeg",
            image_post_id=f"img_{post.post_id}_{attachment_index}_{unique_id}",
            attachment_index=attachment_index,
            platform_connection_id=post.platform_connection_id,
            status=ProcessingStatus.PENDING
        )
        
        session.add(image)
        session.commit()
        session.refresh(image)
        
        return image


class MySQLTestUtilities:
    """Utilities for MySQL testing"""
    
    @staticmethod
    def skip_if_mysql_unavailable():
        """Decorator to skip tests if MySQL is not available"""
        import unittest
        
        def decorator(test_func):
            def wrapper(*args, **kwargs):
                test_config = MySQLTestConfig()
                if not test_config.is_mysql_available():
                    raise unittest.SkipTest("MySQL server not available for testing")
                return test_func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def clean_test_databases():
        """Clean up any leftover test data"""
        try:
            test_config = MySQLTestConfig()
            if not test_config.is_mysql_available():
                return
            
            engine = create_engine(test_config.test_url, echo=False)
            
            with engine.connect() as conn:
                # Clean up test data by pattern matching
                test_patterns = ['test_%', '%_test_%']
                
                # Clean up in reverse dependency order
                tables_to_clean = [
                    'images', 'posts', 'user_sessions', 'platform_connections', 
                    'processing_runs', 'caption_generation_tasks', 
                    'caption_generation_user_settings', 'users'
                ]
                
                for table in tables_to_clean:
                    try:
                        for pattern in test_patterns:
                            if table == 'users':
                                result = conn.execute(text(f"DELETE FROM {table} WHERE username LIKE :pattern"), {"pattern": pattern})
                                if result.rowcount > 0:
                                    logger.info(f"Cleaned up {result.rowcount} test records from {table}")
                            elif table == 'posts':
                                result = conn.execute(text(f"DELETE FROM {table} WHERE post_id LIKE :pattern"), {"pattern": pattern})
                                if result.rowcount > 0:
                                    logger.info(f"Cleaned up {result.rowcount} test records from {table}")
                            elif table == 'platform_connections':
                                result = conn.execute(text(f"DELETE FROM {table} WHERE name LIKE :pattern"), {"pattern": pattern})
                                if result.rowcount > 0:
                                    logger.info(f"Cleaned up {result.rowcount} test records from {table}")
                    except Exception as e:
                        # Ignore cleanup errors for non-existent tables or columns
                        pass
                
                conn.commit()
            
            engine.dispose()
            
        except Exception as e:
            logger.warning(f"Failed to clean test data: {e}")


# Convenience functions for backward compatibility
def get_mysql_test_config(test_name: str = None) -> MySQLTestConfig:
    """Get MySQL test configuration"""
    return MySQLTestConfig(test_name)

def create_mysql_test_database(test_name: str = None) -> MySQLTestConfig:
    """Create MySQL test database and return config"""
    config = MySQLTestConfig(test_name)
    if config.create_test_database():
        return config
    else:
        raise RuntimeError(f"Failed to create MySQL test database for: {test_name}")

# Mock Redis for testing
def mock_redis():
    """Create mock Redis for testing"""
    return patch('redis.Redis', MagicMock())

# Environment setup for testing
def setup_test_environment():
    """Set up test environment variables"""
    test_env = {
        'FLASK_SECRET_KEY': 'test_secret_key_for_testing_only',
        'PLATFORM_ENCRYPTION_KEY': 'test_encryption_key_for_testing_only_32_chars',
        'REDIS_URL': 'redis://localhost:6379/15',  # Use test Redis DB
        'OLLAMA_URL': 'http://localhost:11434',
        'OLLAMA_MODEL': 'llava:7b',
        'SECURITY_CSRF_ENABLED': 'false',  # Disable for testing
        'SECURITY_RATE_LIMITING_ENABLED': 'false',  # Disable for testing
        'SECURITY_INPUT_VALIDATION_ENABLED': 'true',
        'SECURITY_HEADERS_ENABLED': 'false',  # Disable for testing
        'SECURITY_SESSION_VALIDATION_ENABLED': 'false',  # Disable for testing
        'SECURITY_ADMIN_CHECKS_ENABLED': 'false',  # Disable for testing
    }
    
    for key, value in test_env.items():
        os.environ.setdefault(key, value)

if __name__ == "__main__":
    # Test the MySQL configuration
    print("Testing MySQL Test Configuration...")
    
    # Clean up any existing test data first
    MySQLTestUtilities.clean_test_databases()
    
    # Test database creation and cleanup
    with MySQLTestConfig("config_test").test_database_context() as test_config:
        print(f"✅ Test environment ready with prefix: {test_config.table_prefix}")
        
        # Test database manager
        db_manager = test_config.get_database_manager()
        print(f"✅ Database manager created")
        
        # Test session
        session = test_config.get_test_session()
        print(f"✅ Test session created")
        session.close()
    
    print("✅ MySQL test configuration validation completed")
