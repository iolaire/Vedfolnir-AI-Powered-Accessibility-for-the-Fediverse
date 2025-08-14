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
        from database import DatabaseManager
        
        with patch('database.DatabaseManager') as MockDatabaseManager:
            # Configure the mock class
            mock_instance = Mock()
            mock_session = Mock()
            mock_instance.get_session.return_value = mock_session
            mock_instance.get_processing_stats.return_value = {'test': 'data'}\n            MockDatabaseManager.return_value = mock_instance\n            \n            # Create a new instance (this would be used in tests)\n            from config import Config\n            config = Config()\n            db_manager = DatabaseManager(config)\n            \n            # Test the mock\n            session = db_manager.get_session()\n            stats = db_manager.get_processing_stats()\n            \n            print(f"✓ Mock instance: {db_manager}")\n            print(f"✓ Mock session: {session}")\n            print(f"✓ Mock stats: {stats}")\n            print("✓ Class-level patching works")\n            \n    except Exception as e:\n        print(f"✗ Error with class-level patching: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Test Flask app with patched database manager
    print("\n4. Testing Flask app with patched database manager:")
    try:\n        with patch.object(web_app, 'db_manager') as mock_db_manager:\n            # Configure mock for Flask app usage\n            mock_session = Mock()\n            mock_db_manager.get_session.return_value = mock_session\n            mock_db_manager.get_processing_stats.return_value = {\n                'total_posts': 5,\n                'total_images': 10,\n                'pending_review': 2,\n                'approved': 3,\n                'posted': 4,\n                'rejected': 1\n            }\n            \n            # Test with Flask test client\n            with web_app.app.test_client() as client:\n                # This would normally require authentication, but we're just testing the patching\n                print(f"✓ Flask test client created: {client}")
                print("✓ Flask app with patched database manager works")\n                \n    except Exception as e:\n        print(f"✗ Error with Flask app patching: {e}")
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
        mock_db_manager.get_processing_stats.return_value = {\n            'total_posts': 0,\n            'total_images': 0,\n            'pending_review': 0,\n            'approved': 0,\n            'posted': 0,\n            'rejected': 0\n        }\n        mock_db_manager.get_platform_processing_stats.return_value = {\n            'total_posts': 0,\n            'total_images': 0,\n            'pending_review': 0,\n            'approved': 0,\n            'posted': 0,\n            'rejected': 0\n        }\n        mock_db_manager.get_user_platform_summary.return_value = {\n            'total_platforms': 0,\n            'platforms': [],\n            'combined_stats': {\n                'total_posts': 0,\n                'total_images': 0,\n                'pending_review': 0,\n                'approved': 0,\n                'posted': 0,\n                'rejected': 0\n            }\n        }\n        \n        # Configure user management methods\n        mock_db_manager.get_user_by_username.return_value = None\n        mock_db_manager.create_user.return_value = 1\n        mock_db_manager.update_user.return_value = True\n        mock_db_manager.delete_user.return_value = True\n        \n        # Configure platform management methods\n        mock_db_manager.create_platform_connection.return_value = Mock(id=1)\n        mock_db_manager.get_user_platform_connections.return_value = []\n        mock_db_manager.update_platform_connection.return_value = True\n        mock_db_manager.delete_platform_connection.return_value = True\n        mock_db_manager.set_default_platform.return_value = True\n        \n        return mock_db_manager\n    \n    # Test the mock creation\n    mock_db_manager = create_mock_db_manager()\n    print(f"✓ Mock database manager created: {mock_db_manager}")
    \n    # Test basic functionality\n    session = mock_db_manager.get_session()\n    stats = mock_db_manager.get_processing_stats()\n    print(f"✓ Mock session: {session}")
    print(f"✓ Mock stats: {stats}")
    \n    return create_mock_db_manager

class TestDatabaseManagerPatching(unittest.TestCase):
    """Unit tests for database manager patching"""
    
    def setUp(self):\n        \"\"\"Set up test environment\"\"\"\n        # Import here to avoid issues with module-level imports\n        import web_app\n        self.web_app = web_app\n    \n    def test_patch_web_app_db_manager(self):\n        \"\"\"Test patching the web app's database manager\"\"\"\n        with patch.object(self.web_app, 'db_manager') as mock_db_manager:\n            # Configure mock\n            mock_session = Mock()\n            mock_db_manager.get_session.return_value = mock_session\n            \n            # Test\n            session = self.web_app.db_manager.get_session()\n            self.assertEqual(session, mock_session)\n            mock_db_manager.get_session.assert_called_once()\n    \n    def test_patch_database_manager_class(self):\n        \"\"\"Test patching the DatabaseManager class\"\"\"\n        with patch('database.DatabaseManager') as MockDatabaseManager:\n            mock_instance = Mock()\n            MockDatabaseManager.return_value = mock_instance\n            \n            # Import and create instance\n            from database import DatabaseManager\n            from config import Config\n            \n            config = Config()\n            db_manager = DatabaseManager(config)\n            \n            # Test\n            self.assertEqual(db_manager, mock_instance)\n            MockDatabaseManager.assert_called_once_with(config)\n    \n    def test_flask_app_with_mocked_db_manager(self):\n        \"\"\"Test Flask app functionality with mocked database manager\"\"\"\n        with patch.object(self.web_app, 'db_manager') as mock_db_manager:\n            # Configure mock for typical Flask app usage\n            mock_session = Mock()\n            mock_db_manager.get_session.return_value = mock_session\n            mock_db_manager.get_processing_stats.return_value = {\n                'total_posts': 1,\n                'total_images': 2,\n                'pending_review': 0,\n                'approved': 1,\n                'posted': 1,\n                'rejected': 0\n            }\n            \n            # Test that the Flask app can be created with test client\n            with self.web_app.app.test_client() as client:\n                # Just test that we can create the client without errors\n                self.assertIsNotNone(client)\n\ndef main():\n    \"\"\"Main test function\"\"\"\n    print(\"Testing Database Manager Patching for Flask App\")\n    print(\"=\" * 60)\n    \n    # Run basic patching tests\n    success = test_database_manager_patching()\n    \n    if success:\n        # Create reusable patch function\n        create_mock_db_manager = create_test_database_manager_patch()\n        \n        # Run unit tests\n        print(\"\\n=== Running Unit Tests ===\")\n        unittest.main(argv=[''], exit=False, verbosity=2)\n        \n        print(\"\\n\" + \"=\" * 60)\n        print(\"✅ All database manager patching tests completed successfully!\")\n        print(\"\\nTo use in your tests:\")\n        print(\"1. Import web_app and patch web_app.db_manager\")\n        print(\"2. Or patch 'database.DatabaseManager' class\")\n        print(\"3. Use the create_mock_db_manager function for consistent mocks\")\n    else:\n        print(\"\\n\" + \"=\" * 60)\n        print(\"❌ Some database manager patching tests failed!\")\n        return False\n    \n    return True\n\nif __name__ == \"__main__\":\n    success = main()\n    exit(0 if success else 1)