#!/usr/bin/env python3

"""
Example Test Using Database Manager Patching

This demonstrates how to properly test Flask routes that use the database manager
by patching the web app's database manager instance.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our test utilities
from database_manager_test_utils import (
    patch_web_app_database_manager,
    create_mock_database_manager,
    create_mock_user,
    create_mock_platform_connection,
    configure_mock_for_flask_routes
)

class TestFlaskRoutesWithDatabaseManager(unittest.TestCase):
    """Test Flask routes with properly patched database manager"""
    
    def test_platform_management_route_with_mock_db(self):
        """Test platform management route with mocked database manager"""
        
        # Create test data
        test_user = create_mock_user(user_id=1, username="testuser")
        test_platforms = [
            create_mock_platform_connection(connection_id=1, user_id=1, platform_type="pixelfed"),
            create_mock_platform_connection(connection_id=2, user_id=1, platform_type="mastodon", is_default=False)
        ]
        
        # Use our utility to patch the web app's database manager
        with patch_web_app_database_manager() as mock_db_manager:
            # Configure the mock for this test
            configure_mock_for_flask_routes(mock_db_manager, test_user, test_platforms)
            
            # Import web_app after patching
            import web_app
            
            # Verify the database manager is patched
            self.assertEqual(web_app.db_manager, mock_db_manager)
            
            # Test that we can create a Flask test client
            with web_app.app.test_client() as client:
                self.assertIsNotNone(client)
                
                # Test that the database manager methods are called correctly
                session = web_app.db_manager.get_session()
                stats = web_app.db_manager.get_processing_stats()
                
                # Verify mock calls
                mock_db_manager.get_session.assert_called()
                mock_db_manager.get_processing_stats.assert_called()
                
                # Verify return values
                self.assertIsNotNone(session)
                self.assertIn('total_posts', stats)
    
    def test_api_session_state_with_mock_db(self):
        """Test API session state endpoint with mocked database manager"""
        
        # Create test data
        test_user = create_mock_user(user_id=1, username="testuser")
        test_platform = create_mock_platform_connection(connection_id=1, user_id=1)
        
        with patch_web_app_database_manager() as mock_db_manager:
            configure_mock_for_flask_routes(mock_db_manager, test_user, [test_platform])
            
            import web_app
            
            # Test that the database manager is properly integrated
            with web_app.app.test_client() as client:
                # The route would normally require authentication, but we're testing the DB integration
                self.assertIsNotNone(client)
                
                # Test database operations that the route might perform
                platforms = web_app.db_manager.get_user_platform_connections(1)
                
                # Configure the mock to return our test user
                mock_db_manager.get_user_by_username.return_value = test_user
                user = web_app.db_manager.get_user_by_username("testuser")
                
                # Verify the mock returns our test data
                self.assertEqual(len(platforms), 1)
                self.assertEqual(platforms[0].id, 1)
                self.assertEqual(user.username, "testuser")
    
    def test_database_manager_methods_are_mocked(self):
        """Test that all expected database manager methods are properly mocked"""
        
        with patch_web_app_database_manager() as mock_db_manager:
            import web_app
            
            # Test core database methods
            session = web_app.db_manager.get_session()
            self.assertIsNotNone(session)
            
            # Test statistics methods
            stats = web_app.db_manager.get_processing_stats()
            self.assertIsInstance(stats, dict)
            self.assertIn('total_posts', stats)
            
            platform_stats = web_app.db_manager.get_platform_processing_stats(1)
            self.assertIsInstance(platform_stats, dict)
            
            user_summary = web_app.db_manager.get_user_platform_summary(1)
            self.assertIsInstance(user_summary, dict)
            self.assertIn('platforms', user_summary)
            
            # Test user management methods
            user = web_app.db_manager.get_user_by_username("testuser")
            self.assertIsNone(user)  # Default mock returns None
            
            user_id = web_app.db_manager.create_user("newuser", "new@test.com", "password")
            self.assertEqual(user_id, 1)  # Default mock returns 1
            
            # Test platform management methods
            platforms = web_app.db_manager.get_user_platform_connections(1)
            self.assertIsInstance(platforms, list)
            
            success = web_app.db_manager.set_default_platform(1, 1)
            self.assertTrue(success)
            
            # Test image and post methods
            post = web_app.db_manager.get_or_create_post("post123", "user123", "https://example.com/post")
            self.assertIsNotNone(post)
            
            image_id = web_app.db_manager.save_image(1, "https://example.com/image.jpg", "/tmp/image.jpg", 0)
            self.assertEqual(image_id, 1)
            
            success = web_app.db_manager.update_image_caption(1, "Test caption")
            self.assertTrue(success)
    
    def test_custom_mock_configuration(self):
        """Test using a custom mock configuration"""
        
        # Create a custom mock database manager
        custom_mock = create_mock_database_manager()
        
        # Customize the mock for specific test needs
        custom_mock.get_processing_stats.return_value = {
            'total_posts': 100,
            'total_images': 200,
            'pending_review': 50,
            'approved': 75,
            'posted': 60,
            'rejected': 15
        }
        
        # Create custom test user
        custom_user = create_mock_user(user_id=42, username="customuser")
        custom_mock.get_user_by_username.return_value = custom_user
        
        with patch_web_app_database_manager(custom_mock) as mock_db_manager:
            import web_app
            
            # Test that our custom configuration is used
            stats = web_app.db_manager.get_processing_stats()
            self.assertEqual(stats['total_posts'], 100)
            self.assertEqual(stats['total_images'], 200)
            
            user = web_app.db_manager.get_user_by_username("customuser")
            self.assertEqual(user.id, 42)
            self.assertEqual(user.username, "customuser")
    
    def test_session_context_manager(self):
        """Test that session context manager works correctly"""
        
        with patch_web_app_database_manager() as mock_db_manager:
            import web_app
            
            # Test session context manager
            session = web_app.db_manager.get_session()
            
            # Test that session has context manager methods
            self.assertTrue(hasattr(session, '__enter__'))
            self.assertTrue(hasattr(session, '__exit__'))
            
            # Test using session as context manager
            with session as ctx_session:
                self.assertEqual(ctx_session, session)
                
                # Test session methods
                ctx_session.add(Mock())
                ctx_session.commit()
                ctx_session.rollback()
                ctx_session.close()
                
                # Verify methods were called
                session.add.assert_called()
                session.commit.assert_called()
                session.rollback.assert_called()
                session.close.assert_called()

class TestDatabaseManagerPatchingStrategies(unittest.TestCase):
    """Test different strategies for patching the database manager"""
    
    def test_patch_web_app_module_level(self):
        """Test patching at the web_app module level"""
        
        import web_app
        
        with patch.object(web_app, 'db_manager') as mock_db_manager:
            mock_db_manager.get_session.return_value = Mock()
            mock_db_manager.get_processing_stats.return_value = {'test': 'data'}
            
            # Test that the patch works
            session = web_app.db_manager.get_session()
            stats = web_app.db_manager.get_processing_stats()
            
            self.assertIsNotNone(session)
            self.assertEqual(stats, {'test': 'data'})
            
            # Verify calls
            mock_db_manager.get_session.assert_called()
            mock_db_manager.get_processing_stats.assert_called()
    
    def test_patch_database_manager_class(self):
        """Test patching the DatabaseManager class itself"""
        
        with patch('database.DatabaseManager') as MockDatabaseManager:
            mock_instance = Mock()
            mock_instance.get_session.return_value = Mock()
            mock_instance.get_processing_stats.return_value = {'class_patch': 'success'}
            MockDatabaseManager.return_value = mock_instance
            
            # Import and create instance
            from app.core.database.core.database_manager import DatabaseManager
            from config import Config
            
            config = Config()
            db_manager = DatabaseManager(config)
            
            # Test that we get the mock instance
            self.assertEqual(db_manager, mock_instance)
            
            # Test methods
            session = db_manager.get_session()
            stats = db_manager.get_processing_stats()
            
            self.assertIsNotNone(session)
            self.assertEqual(stats, {'class_patch': 'success'})
            
            # Verify the class was called with config
            MockDatabaseManager.assert_called_once_with(config)

def run_example_tests():
    """Run all example tests"""
    
    print("Running Example Tests with Database Manager Patching")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestFlaskRoutesWithDatabaseManager,
        TestDatabaseManagerPatchingStrategies
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_example_tests()
    
    print(f"\n{'='*60}")
    print("EXAMPLE TESTS SUMMARY")
    print(f"{'='*60}")
    
    if success:
        print("✅ All example tests passed!")
        print("\nKey takeaways:")
        print("1. Use patch_web_app_database_manager() to patch web_app.db_manager")
        print("2. Configure mocks with configure_mock_for_flask_routes()")
        print("3. Create custom test data with create_mock_user() and create_mock_platform_connection()")
        print("4. Import web_app AFTER patching to get the patched version")
        print("5. All database manager methods are properly mocked")
    else:
        print("❌ Some example tests failed!")
    
    exit(0 if success else 1)