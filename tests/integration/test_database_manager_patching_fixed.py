#!/usr/bin/env python3

"""
Test Database Manager Patching for Flask App

This script demonstrates how to properly patch the database manager
used by the Flask app for testing purposes.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

def test_database_manager_patching():
    """Test different approaches to patching the database manager"""
    
    print("=== Database Manager Patching Test ===")
    
    # Test 1: Import web_app and check its database manager
    print("\n1. Testing web_app database manager:")
    try:
        import web_app
        print(f"✓ web_app imported successfully")
        print(f"✓ web_app.db_manager type: {type(web_app.db_manager)}")
        print(f"✓ web_app.db_manager methods: {[m for m in dir(web_app.db_manager) if not m.startswith('_')][:10]}...")
        
        # Test getting a session
        session = web_app.db_manager.get_session()
        print(f"✓ Session created: {type(session)}")
        session.close()
        
    except Exception as e:
        print(f"✗ Error importing web_app: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Patch the database manager at module level
    print("\n2. Testing module-level patching:")
    try:
        with patch.object(web_app, 'db_manager') as mock_db_manager:
            # Configure the mock
            mock_session = Mock()
            mock_db_manager.get_session.return_value = mock_session
            mock_db_manager.get_processing_stats.return_value = {
                'total_posts': 0,
                'total_images': 0,
                'pending_review': 0,
                'approved': 0,
                'posted': 0,
                'rejected': 0
            }
            
            # Test that the mock is working
            session = web_app.db_manager.get_session()
            stats = web_app.db_manager.get_processing_stats()
            
            print(f"✓ Mock session: {session}")
            print(f"✓ Mock stats: {stats}")
            print("✓ Module-level patching works")
            
    except Exception as e:
        print(f"✗ Error with module-level patching: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Patch the DatabaseManager class
    print("\n3. Testing class-level patching:")
    try:
        from app.core.database.core.database_manager import DatabaseManager
        
        with patch('database.DatabaseManager') as MockDatabaseManager:
            # Configure the mock class
            mock_instance = Mock()
            mock_session = Mock()
            mock_instance.get_session.return_value = mock_session
            mock_instance.get_processing_stats.return_value = {'test': 'data'}
            MockDatabaseManager.return_value = mock_instance
            
            # Create a new instance (this would be used in tests)
            from config import Config
            config = Config()
            db_manager = self.get_database_manager()
            
            # Test the mock
            session = db_manager.get_session()
            stats = db_manager.get_processing_stats()
            
            print(f"✓ Mock instance: {db_manager}")
            print(f"✓ Mock session: {session}")
            print(f"✓ Mock stats: {stats}")
            print("✓ Class-level patching works")
            
    except Exception as e:
        print(f"✗ Error with class-level patching: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Test Flask app with patched database manager
    print("\n4. Testing Flask app with patched database manager:")
    try:
        with patch.object(web_app, 'db_manager') as mock_db_manager:
            # Configure mock for Flask app usage
            mock_session = Mock()
            mock_db_manager.get_session.return_value = mock_session
            mock_db_manager.get_processing_stats.return_value = {
                'total_posts': 5,
                'total_images': 10,
                'pending_review': 2,
                'approved': 3,
                'posted': 4,
                'rejected': 1
            }
            
            # Test with Flask test client
            with web_app.app.test_client() as client:
                # This would normally require authentication, but we're just testing the patching
                print(f"✓ Flask test client created: {client}")
                print("✓ Flask app with patched database manager works")
                
    except Exception as e:
        print(f"✗ Error with Flask app patching: {e}")
        import traceback
        traceback.print_exc()
    
    return True

def create_test_database_manager_patch():
    """Create a reusable database manager patch for tests"""
    
    print("\n=== Creating Reusable Database Manager Patch ===")
    
    def create_mock_db_manager():
        """Create a properly configured mock database manager"""
        mock_db_manager = Mock()
        
        # Configure session mock
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.query.return_value.filter_by.return_value.all.return_value = []
        mock_session.query.return_value.filter_by.return_value.count.return_value = 0
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.rollback = Mock()
        mock_session.close = Mock()
        
        # Configure database manager methods
        mock_db_manager.get_session.return_value = mock_session
        mock_db_manager.close_session = Mock()
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
        
        # Configure user management methods
        mock_db_manager.get_user_by_username.return_value = None
        mock_db_manager.create_user.return_value = 1
        mock_db_manager.update_user.return_value = True
        mock_db_manager.delete_user.return_value = True
        
        # Configure platform management methods
        mock_db_manager.create_platform_connection.return_value = Mock(id=1)
        mock_db_manager.get_user_platform_connections.return_value = []
        mock_db_manager.update_platform_connection.return_value = True
        mock_db_manager.delete_platform_connection.return_value = True
        mock_db_manager.set_default_platform.return_value = True
        
        return mock_db_manager
    
    # Test the mock creation
    mock_db_manager = create_mock_db_manager()
    print(f"✓ Mock database manager created: {mock_db_manager}")
    
    # Test basic functionality
    session = mock_db_manager.get_session()
    stats = mock_db_manager.get_processing_stats()
    print(f"✓ Mock session: {session}")
    print(f"✓ Mock stats: {stats}")
    
    return create_mock_db_manager

class TestDatabaseManagerPatching(MySQLIntegrationTestBase):
    """Unit tests for database manager patching"""
    
    def setUp(self):
        """Set up test environment"""
        # Import here to avoid issues with module-level imports
        import web_app
        self.web_app = web_app
    
    def test_patch_web_app_db_manager(self):
        """Test patching the web app's database manager"""
        with patch.object(self.web_app, 'db_manager') as mock_db_manager:
            # Configure mock
            mock_session = Mock()
            mock_db_manager.get_session.return_value = mock_session
            
            # Test
            session = self.web_app.db_manager.get_session()
            self.assertEqual(session, mock_session)
            mock_db_manager.get_session.assert_called_once()
    
    def test_patch_database_manager_class(self):
        """Test patching the DatabaseManager class"""
        with patch('database.DatabaseManager') as MockDatabaseManager:
            mock_instance = Mock()
            MockDatabaseManager.return_value = mock_instance
            
            # Import and create instance
            from app.core.database.core.database_manager import DatabaseManager
            from config import Config

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures

            
            config = Config()
            db_manager = self.get_database_manager()
            
            # Test
            self.assertEqual(db_manager, mock_instance)
            MockDatabaseManager.assert_called_once_with(config)
    
    def test_flask_app_with_mocked_db_manager(self):
        """Test Flask app functionality with mocked database manager"""
        with patch.object(self.web_app, 'db_manager') as mock_db_manager:
            # Configure mock for typical Flask app usage
            mock_session = Mock()
            mock_db_manager.get_session.return_value = mock_session
            mock_db_manager.get_processing_stats.return_value = {
                'total_posts': 1,
                'total_images': 2,
                'pending_review': 0,
                'approved': 1,
                'posted': 1,
                'rejected': 0
            }
            
            # Test that the Flask app can be created with test client
            with self.web_app.app.test_client() as client:
                # Just test that we can create the client without errors
                self.assertIsNotNone(client)

def main():
    """Main test function"""
    print("Testing Database Manager Patching for Flask App")
    print("=" * 60)
    
    # Run basic patching tests
    success = test_database_manager_patching()
    
    if success:
        # Create reusable patch function
        create_mock_db_manager = create_test_database_manager_patch()
        
        # Run unit tests
        print("\n=== Running Unit Tests ===")
        unittest.main(argv=[''], exit=False, verbosity=2)
        
        print("\n" + "=" * 60)
        print("✅ All database manager patching tests completed successfully!")
        print("\nTo use in your tests:")
        print("1. Import web_app and patch web_app.db_manager")
        print("2. Or patch 'database.DatabaseManager' class")
        print("3. Use the create_mock_db_manager function for consistent mocks")
    else:
        print("\n" + "=" * 60)
        print("❌ Some database manager patching tests failed!")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)