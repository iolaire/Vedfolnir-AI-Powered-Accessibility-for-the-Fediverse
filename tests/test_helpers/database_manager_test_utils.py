#!/usr/bin/env python3

"""
Database Manager Test Utilities

This module provides utilities for properly mocking and patching the database manager
in tests, addressing the issue where the Flask app uses a different database manager
instance than what tests might expect.
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_mock_database_manager():
    """
    Create a comprehensive mock database manager that mimics the real DatabaseManager.
    
    This mock includes all the methods that the Flask app expects to use.
    
    Returns:
        Mock: Configured mock database manager
    """
    mock_db_manager = Mock()
    
    # Configure session mock with context manager support
    mock_session = Mock()
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=None)
    
    # Configure SQLAlchemy query chain methods
    query_mock = Mock()
    query_mock.filter.return_value = query_mock
    query_mock.filter_by.return_value = query_mock
    query_mock.join.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.offset.return_value = query_mock
    query_mock.first.return_value = None
    query_mock.all.return_value = []
    query_mock.count.return_value = 0
    query_mock.get.return_value = None
    
    mock_session.query.return_value = query_mock
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.rollback = Mock()
    mock_session.flush = Mock()
    mock_session.refresh = Mock()
    mock_session.close = Mock()
    mock_session.execute = Mock()
    
    # Configure database manager methods
    mock_db_manager.get_session.return_value = mock_session
    mock_db_manager.close_session = Mock()
    
    # Configure statistics methods
    mock_db_manager.get_processing_stats.return_value = {
        'total_posts': 0,
        'total_images': 0,
        'pending_review': 0,
        'approved': 0,
        'posted': 0,
        'rejected': 0
    }
    
    mock_db_manager.get_platform_processing_stats.return_value = {
        'total_posts': 0,
        'total_images': 0,
        'pending_review': 0,
        'approved': 0,
        'posted': 0,
        'rejected': 0
    }
    
    mock_db_manager.get_user_platform_summary.return_value = {
        'total_platforms': 0,
        'platforms': [],
        'combined_stats': {
            'total_posts': 0,
            'total_images': 0,
            'pending_review': 0,
            'approved': 0,
            'posted': 0,
            'rejected': 0
        }
    }
    
    mock_db_manager.get_platform_statistics.return_value = {}
    
    # Configure user management methods
    mock_db_manager.get_user_by_username.return_value = None
    mock_db_manager.get_user_by_email.return_value = None
    mock_db_manager.create_user.return_value = 1
    mock_db_manager.update_user.return_value = True
    mock_db_manager.delete_user.return_value = True
    mock_db_manager.get_all_users.return_value = []
    
    # Configure platform connection methods
    mock_platform = Mock()
    mock_platform.id = 1
    mock_platform.name = "Test Platform"
    mock_platform.platform_type = "pixelfed"
    mock_platform.instance_url = "https://test.example.com"
    mock_platform.username = "testuser"
    mock_platform.is_active = True
    mock_platform.is_default = True
    
    mock_db_manager.create_platform_connection.return_value = mock_platform
    mock_db_manager.get_platform_connection.return_value = mock_platform
    mock_db_manager.get_user_platform_connections.return_value = [mock_platform]
    mock_db_manager.update_platform_connection.return_value = True
    mock_db_manager.delete_platform_connection.return_value = True
    mock_db_manager.set_default_platform.return_value = True
    mock_db_manager.test_platform_connection.return_value = (True, "Connection successful")
    mock_db_manager.switch_platform_context.return_value = True
    
    # Configure image and post methods
    mock_post = Mock()
    mock_post.id = 1
    mock_post.post_id = "test_post_id"
    mock_post.user_id = "test_user"
    mock_post.post_url = "https://test.example.com/posts/1"
    
    mock_image = Mock()
    mock_image.id = 1
    mock_image.post_id = 1
    mock_image.image_url = "https://test.example.com/image.jpg"
    mock_image.local_path = "/tmp/test_image.jpg"
    
    mock_db_manager.get_or_create_post.return_value = mock_post
    mock_db_manager.save_image.return_value = 1
    mock_db_manager.update_image_caption.return_value = True
    mock_db_manager.get_pending_images.return_value = [mock_image]
    mock_db_manager.get_approved_images.return_value = [mock_image]
    mock_db_manager.review_image.return_value = True
    mock_db_manager.mark_image_posted.return_value = True
    mock_db_manager.is_image_processed.return_value = False
    
    # Configure platform context methods
    mock_db_manager.set_platform_context.return_value = True
    mock_db_manager.clear_platform_context = Mock()
    mock_db_manager.require_platform_context = Mock()
    
    # Configure validation methods
    mock_db_manager.validate_data_isolation.return_value = {
        'user_id': 1,
        'platforms_tested': 1,
        'isolation_issues': [],
        'cross_platform_data': [],
        'validation_passed': True
    }
    
    return mock_db_manager

@contextmanager
def patch_web_app_database_manager(mock_db_manager: Optional[Mock] = None):
    """
    Context manager to patch the web app's database manager.
    
    Args:
        mock_db_manager: Optional pre-configured mock database manager
        
    Yields:
        Mock: The mock database manager being used
    """
    if mock_db_manager is None:
        mock_db_manager = create_mock_database_manager()
    
    # Import web_app here to avoid circular imports
    import web_app
    
    with patch.object(web_app, 'db_manager', mock_db_manager) as patched_db_manager:
        yield patched_db_manager

@contextmanager
def patch_database_manager_class(mock_db_manager: Optional[Mock] = None):
    """
    Context manager to patch the DatabaseManager class itself.
    
    Args:
        mock_db_manager: Optional pre-configured mock database manager
        
    Yields:
        Mock: The mock DatabaseManager class
    """
    if mock_db_manager is None:
        mock_db_manager = create_mock_database_manager()
    
    with patch('database.DatabaseManager', return_value=mock_db_manager) as MockDatabaseManager:
        yield MockDatabaseManager

def create_mock_user(user_id: int = 1, username: str = "testuser", 
                    email: str = "test@test.com", is_active: bool = True):
    """
    Create a mock user object for testing.
    
    Args:
        user_id: User ID
        username: Username
        email: Email address
        is_active: Whether user is active
        
    Returns:
        Mock: Configured mock user
    """
    from models import UserRole
    
    mock_user = Mock()
    mock_user.id = user_id
    mock_user.username = username
    mock_user.email = email
    mock_user.is_active = is_active
    mock_user.role = UserRole.REVIEWER
    mock_user.created_at = datetime.now(timezone.utc)
    mock_user.last_login = datetime.now(timezone.utc)
    mock_user.platform_connections = []
    mock_user.sessions = []
    
    # Configure user methods
    mock_user.check_password.return_value = True
    mock_user.set_password = Mock()
    mock_user.has_permission.return_value = True
    
    return mock_user

def create_mock_platform_connection(connection_id: int = 1, user_id: int = 1,
                                   platform_type: str = "pixelfed", 
                                   is_active: bool = True, is_default: bool = True):
    """
    Create a mock platform connection object for testing.
    
    Args:
        connection_id: Platform connection ID
        user_id: User ID who owns the connection
        platform_type: Type of platform
        is_active: Whether connection is active
        is_default: Whether this is the default connection
        
    Returns:
        Mock: Configured mock platform connection
    """
    mock_platform = Mock()
    mock_platform.id = connection_id
    mock_platform.user_id = user_id
    mock_platform.name = f"Test {platform_type.title()}"
    mock_platform.platform_type = platform_type
    mock_platform.instance_url = f"https://test-{platform_type}.example.com"
    mock_platform.username = "testuser"
    mock_platform.is_active = is_active
    mock_platform.is_default = is_default
    mock_platform.created_at = datetime.now(timezone.utc)
    mock_platform.updated_at = datetime.now(timezone.utc)
    mock_platform.last_used = datetime.now(timezone.utc)
    
    # Configure encrypted credential access
    mock_platform.access_token = "test_access_token"
    mock_platform.client_key = "test_client_key"
    mock_platform.client_secret = "test_client_secret"
    
    # Configure platform methods
    mock_platform.test_connection.return_value = (True, "Connection successful")
    mock_platform.to_activitypub_config.return_value = Mock()
    
    return mock_platform

def configure_mock_for_flask_routes(mock_db_manager: Mock, 
                                   user: Optional[Mock] = None,
                                   platforms: Optional[List[Mock]] = None):
    """
    Configure a mock database manager for typical Flask route usage.
    
    Args:
        mock_db_manager: Mock database manager to configure
        user: Optional mock user to return from queries
        platforms: Optional list of mock platforms to return from queries
    """
    if user is None:
        user = create_mock_user()
    
    if platforms is None:
        platforms = [create_mock_platform_connection()]
    
    # Configure session queries to return the test data
    mock_session = mock_db_manager.get_session.return_value
    
    # Configure user queries
    mock_session.query.return_value.filter_by.return_value.first.return_value = user
    mock_session.query.return_value.get.return_value = user
    
    # Configure platform queries
    mock_session.query.return_value.filter_by.return_value.all.return_value = platforms
    mock_session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = platforms
    
    # Configure statistics
    mock_db_manager.get_processing_stats.return_value = {
        'total_posts': 5,
        'total_images': 10,
        'pending_review': 2,
        'approved': 3,
        'posted': 4,
        'rejected': 1
    }

# Example usage functions
def example_test_with_patched_web_app():
    """Example of how to test Flask routes with patched database manager"""
    
    print("=== Example: Testing Flask Routes with Patched Database Manager ===")
    
    # Create test data
    test_user = create_mock_user(user_id=1, username="testuser")
    test_platforms = [create_mock_platform_connection(connection_id=1, user_id=1)]
    
    # Use the context manager to patch the web app's database manager
    with patch_web_app_database_manager() as mock_db_manager:
        # Configure the mock for Flask route usage
        configure_mock_for_flask_routes(mock_db_manager, test_user, test_platforms)
        
        # Import web_app after patching to get the patched version
        import web_app
        
        # Test with Flask test client
        with web_app.app.test_client() as client:
            print("✓ Flask test client created successfully")
            print("✓ Database manager is properly mocked")
            print(f"✓ Mock database manager: {web_app.db_manager}")
            
            # You can now make requests to routes that use the database
            # For example (these would normally require authentication):
            # response = client.get('/platform_management')
            # response = client.get('/api/session_state')
            
    print("✓ Example completed successfully")

def example_test_with_patched_class():
    """Example of how to test with patched DatabaseManager class"""
    
    print("=== Example: Testing with Patched DatabaseManager Class ===")
    
    with patch_database_manager_class() as MockDatabaseManager:
        # Import and create a new database manager instance
        from app.core.database.core.database_manager import DatabaseManager
        from config import Config
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        print(f"✓ DatabaseManager class patched: {MockDatabaseManager}")
        print(f"✓ Database manager instance: {db_manager}")
        print("✓ All DatabaseManager instances will use the mock")
        
        # Test database operations
        session = db_manager.get_session()
        stats = db_manager.get_processing_stats()
        
        print(f"✓ Mock session: {session}")
        print(f"✓ Mock stats: {stats}")
    
    print("✓ Example completed successfully")

if __name__ == "__main__":
    print("Database Manager Test Utilities")
    print("=" * 50)
    
    # Run examples
    example_test_with_patched_web_app()
    print()
    example_test_with_patched_class()
    
    print("\n" + "=" * 50)
    print("✅ All examples completed successfully!")
    print("\nUsage in your tests:")
    print("1. Use patch_web_app_database_manager() to patch web_app.db_manager")
    print("2. Use patch_database_manager_class() to patch the DatabaseManager class")
    print("3. Use create_mock_database_manager() for custom mock configurations")
    print("4. Use configure_mock_for_flask_routes() to set up typical Flask route data")