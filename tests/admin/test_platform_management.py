# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for Admin Platform Management Routes

This module tests the platform management functionality in the admin interface,
including platform listing, filtering, status management, and security controls.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole, PlatformConnection
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

class TestAdminPlatformManagement(unittest.TestCase):
    """Test admin platform management functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create test admin user with unique username
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        
        self.admin_user, self.admin_helper = create_test_user_with_platforms(
            self.db_manager,
            username=f"test_admin_{unique_suffix}",
            role=UserRole.ADMIN
        )
        
        # Create test viewer user with platforms
        self.viewer_user, self.viewer_helper = create_test_user_with_platforms(
            self.db_manager,
            username=f"test_viewer_{unique_suffix}",
            role=UserRole.VIEWER
        )
        
        # Create test platforms
        self._create_test_platforms()
    
    def tearDown(self):
        """Clean up test environment"""
        cleanup_test_user(self.admin_helper)
        cleanup_test_user(self.viewer_helper)
    
    def _create_test_platforms(self):
        """Create test platform connections"""
        with self.db_manager.get_session() as session:
            # Platform for admin user
            self.admin_platform = PlatformConnection(
                user_id=self.admin_user.id,
                name="Admin Test Platform",
                platform_type="pixelfed",
                instance_url="https://admin.pixelfed.test",
                username="admin_test",
                access_token="test_token_admin",
                client_key="test_client_key_admin",
                client_secret="test_client_secret_admin",
                is_active=True,
                is_default=True,
                created_at=datetime.utcnow()
            )
            session.add(self.admin_platform)
            
            # Active platform for viewer user
            self.viewer_platform_1 = PlatformConnection(
                user_id=self.viewer_user.id,
                name="Viewer Test Platform 1",
                platform_type="mastodon",
                instance_url="https://viewer1.mastodon.test",
                username="viewer_test_1",
                access_token="test_token_viewer_1",
                client_key="test_client_key_viewer_1",
                client_secret="test_client_secret_viewer_1",
                is_active=True,
                is_default=True,
                created_at=datetime.utcnow()
            )
            session.add(self.viewer_platform_1)
            
            # Inactive platform for viewer user
            self.viewer_platform_2 = PlatformConnection(
                user_id=self.viewer_user.id,
                name="Viewer Test Platform 2",
                platform_type="pixelfed",
                instance_url="https://viewer2.pixelfed.test",
                username="viewer_test_2",
                access_token="test_token_viewer_2",
                client_key="test_client_key_viewer_2",
                client_secret="test_client_secret_viewer_2",
                is_active=False,
                is_default=False,
                created_at=datetime.utcnow() - timedelta(days=30)
            )
            session.add(self.viewer_platform_2)
            
            session.commit()
            
            # Store IDs for tests
            self.admin_platform_id = self.admin_platform.id
            self.viewer_platform_1_id = self.viewer_platform_1.id
            self.viewer_platform_2_id = self.viewer_platform_2.id
    
    @patch('flask_login.current_user')
    @patch('flask.current_app')
    def test_platform_management_route_admin_access(self, mock_app, mock_current_user):
        """Test that admin users can access platform management"""
        # Mock admin user
        mock_current_user.id = self.admin_user.id
        mock_current_user.role = UserRole.ADMIN
        mock_current_user.is_authenticated = True
        
        # Mock Flask app config
        mock_app.config = {
            'db_manager': self.db_manager,
            'redis_platform_manager': None
        }
        mock_app.logger = Mock()
        
        # Import and test the route function
        from app.blueprints.admin.platform_management import register_routes
        
        # Create mock blueprint
        mock_bp = Mock()
        register_routes(mock_bp)
        
        # Verify route was registered
        mock_bp.route.assert_called()
        
        # Get the platform management function
        route_calls = [call for call in mock_bp.route.call_args_list if '/platforms' in str(call)]
        self.assertTrue(len(route_calls) > 0, "Platform management route should be registered")
    
    def test_platform_statistics_calculation(self):
        """Test platform statistics calculation"""
        from app.blueprints.admin.platform_management import _get_platform_statistics
        
        with self.db_manager.get_session() as session:
            stats = _get_platform_statistics(session)
            
            # Verify basic statistics
            self.assertIsInstance(stats, dict)
            self.assertIn('total_platforms', stats)
            self.assertIn('active_platforms', stats)
            self.assertIn('inactive_platforms', stats)
            self.assertIn('platform_types', stats)
            self.assertIn('users_with_platforms', stats)
            
            # Verify counts include our test data (there may be existing data)
            self.assertGreaterEqual(stats['total_platforms'], 3)  # At least 3 test platforms
            self.assertGreaterEqual(stats['active_platforms'], 2)  # At least 2 active platforms
            self.assertGreaterEqual(stats['inactive_platforms'], 1)  # At least 1 inactive platform
            self.assertGreaterEqual(stats['users_with_platforms'], 2)  # At least 2 users with platforms
            
            # Verify platform type distribution includes our test data
            self.assertIn('pixelfed', stats['platform_types'])
            self.assertIn('mastodon', stats['platform_types'])
            self.assertGreaterEqual(stats['platform_types']['pixelfed'], 2)  # At least 2 pixelfed platforms
            self.assertGreaterEqual(stats['platform_types']['mastodon'], 1)  # At least 1 mastodon platform
    
    def test_platform_usage_statistics(self):
        """Test platform usage statistics calculation"""
        from app.blueprints.admin.platform_management import _get_platform_usage_stats
        
        with self.db_manager.get_session() as session:
            stats = _get_platform_usage_stats(session, self.admin_platform_id)
            
            # Verify statistics structure
            self.assertIsInstance(stats, dict)
            self.assertIn('total_posts', stats)
            self.assertIn('total_images', stats)
            self.assertIn('last_activity', stats)
            self.assertIn('posts_this_month', stats)
            self.assertIn('images_this_month', stats)
            
            # Verify default values (since we don't have actual post/image data)
            self.assertEqual(stats['total_posts'], 0)
            self.assertEqual(stats['total_images'], 0)
    
    @patch('flask_login.current_user')
    @patch('flask.current_app')
    @patch('flask.request')
    def test_platform_filtering(self, mock_request, mock_app, mock_current_user):
        """Test platform filtering functionality"""
        # Mock admin user
        mock_current_user.id = self.admin_user.id
        mock_current_user.role = UserRole.ADMIN
        mock_current_user.is_authenticated = True
        
        # Mock Flask app config
        mock_app.config = {
            'db_manager': self.db_manager,
            'redis_platform_manager': None
        }
        mock_app.logger = Mock()
        
        # Mock request args for filtering
        mock_request.args.get.side_effect = lambda key, default=None: {
            'platform_type': 'pixelfed',
            'status': 'active',
            'page_size': '25',
            'page': '1'
        }.get(key, default)
        
        # Test filtering logic by querying database directly
        with self.db_manager.get_session() as session:
            query = session.query(PlatformConnection).join(User)
            
            # Apply platform type filter
            query = query.filter(PlatformConnection.platform_type == 'pixelfed')
            
            # Apply status filter
            query = query.filter(PlatformConnection.is_active == True)
            
            filtered_platforms = query.all()
            
            # Should return only active pixelfed platforms
            self.assertEqual(len(filtered_platforms), 1)
            self.assertEqual(filtered_platforms[0].platform_type, 'pixelfed')
            self.assertTrue(filtered_platforms[0].is_active)
    
    @patch('flask_login.current_user')
    @patch('flask.current_app')
    def test_platform_details_retrieval(self, mock_app, mock_current_user):
        """Test platform details retrieval"""
        # Mock admin user
        mock_current_user.id = self.admin_user.id
        mock_current_user.role = UserRole.ADMIN
        mock_current_user.is_authenticated = True
        
        # Mock Flask app config
        mock_app.config = {
            'db_manager': self.db_manager
        }
        mock_app.logger = Mock()
        
        # Test platform details retrieval
        with self.db_manager.get_session() as session:
            platform = session.query(PlatformConnection).join(User).filter(
                PlatformConnection.id == self.admin_platform_id
            ).first()
            
            self.assertIsNotNone(platform)
            self.assertEqual(platform.name, "Admin Test Platform")
            self.assertEqual(platform.platform_type, "pixelfed")
            self.assertEqual(platform.instance_url, "https://admin.pixelfed.test")
            self.assertTrue(platform.is_active)
            self.assertTrue(platform.is_default)
            
            # Verify user relationship
            self.assertEqual(platform.user.id, self.admin_user.id)
            self.assertEqual(platform.user.username, "test_admin")
    
    @patch('flask_login.current_user')
    @patch('flask.current_app')
    def test_platform_status_toggle(self, mock_app, mock_current_user):
        """Test platform status toggle functionality"""
        # Mock admin user
        mock_current_user.id = self.admin_user.id
        mock_current_user.role = UserRole.ADMIN
        mock_current_user.is_authenticated = True
        mock_current_user.username = "test_admin"
        
        # Mock Flask app config
        mock_app.config = {
            'db_manager': self.db_manager,
            'redis_platform_manager': None
        }
        mock_app.logger = Mock()
        mock_app.unified_notification_manager = Mock()
        
        # Test status toggle
        with self.db_manager.get_session() as session:
            platform = session.query(PlatformConnection).filter(
                PlatformConnection.id == self.viewer_platform_2_id
            ).first()
            
            # Verify initial state (inactive)
            self.assertFalse(platform.is_active)
            
            # Toggle status (activate)
            platform.is_active = not platform.is_active
            session.commit()
            
            # Verify status changed
            updated_platform = session.query(PlatformConnection).filter(
                PlatformConnection.id == self.viewer_platform_2_id
            ).first()
            self.assertTrue(updated_platform.is_active)
    
    @patch('flask_login.current_user')
    @patch('flask.current_app')
    def test_platform_default_setting(self, mock_app, mock_current_user):
        """Test setting platform as default"""
        # Mock admin user
        mock_current_user.id = self.admin_user.id
        mock_current_user.role = UserRole.ADMIN
        mock_current_user.is_authenticated = True
        mock_current_user.username = "test_admin"
        
        # Mock Flask app config
        mock_app.config = {
            'db_manager': self.db_manager,
            'redis_platform_manager': None
        }
        mock_app.logger = Mock()
        mock_app.unified_notification_manager = Mock()
        
        # Test setting platform as default
        with self.db_manager.get_session() as session:
            # First activate the inactive platform
            inactive_platform = session.query(PlatformConnection).filter(
                PlatformConnection.id == self.viewer_platform_2_id
            ).first()
            inactive_platform.is_active = True
            
            # Clear existing default for this user
            session.query(PlatformConnection).filter(
                PlatformConnection.user_id == self.viewer_user.id,
                PlatformConnection.is_default == True
            ).update({'is_default': False})
            
            # Set new default
            inactive_platform.is_default = True
            session.commit()
            
            # Verify default was set
            updated_platform = session.query(PlatformConnection).filter(
                PlatformConnection.id == self.viewer_platform_2_id
            ).first()
            self.assertTrue(updated_platform.is_default)
            
            # Verify only one default per user
            default_count = session.query(PlatformConnection).filter(
                PlatformConnection.user_id == self.viewer_user.id,
                PlatformConnection.is_default == True
            ).count()
            self.assertEqual(default_count, 1)
    
    def test_platform_security_access_control(self):
        """Test platform access control for different user roles"""
        from app.core.security.middleware.platform_access_middleware import filter_platforms_for_user
        
        with self.db_manager.get_session() as session:
            # Test admin access (should see all platforms)
            with patch('flask_login.current_user') as mock_current_user:
                mock_current_user.role = UserRole.ADMIN
                mock_current_user.is_authenticated = True
                
                admin_query = session.query(PlatformConnection)
                admin_filtered = filter_platforms_for_user(admin_query)
                admin_platforms = admin_filtered.all()
                
                # Admin should see all platforms
                self.assertEqual(len(admin_platforms), 3)
            
            # Test viewer access (should only see own platforms)
            with patch('flask_login.current_user') as mock_current_user:
                mock_current_user.id = self.viewer_user.id
                mock_current_user.role = UserRole.VIEWER
                mock_current_user.is_authenticated = True
                
                viewer_query = session.query(PlatformConnection)
                viewer_filtered = filter_platforms_for_user(viewer_query)
                viewer_platforms = viewer_filtered.all()
                
                # Viewer should only see their own platforms
                self.assertEqual(len(viewer_platforms), 2)
                for platform in viewer_platforms:
                    self.assertEqual(platform.user_id, self.viewer_user.id)
    
    @patch('flask_login.current_user')
    def test_platform_notification_creation(self, mock_current_user):
        """Test platform management notification creation"""
        from app.blueprints.admin.platform_management import create_platform_notification
        
        # Mock admin user
        mock_current_user.id = self.admin_user.id
        mock_current_user.username = "test_admin"
        
        # Mock Flask components
        with patch('flask.current_app') as mock_app, \
             patch('flask.request') as mock_request:
            
            mock_app.unified_notification_manager = Mock()
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers.get.return_value = 'Test User Agent'
            
            # Test notification creation
            create_platform_notification(
                platform_id=self.admin_platform_id,
                platform_name="Test Platform",
                operation_type="status_changed",
                message="Platform status changed by admin"
            )
            
            # Verify notification was sent
            mock_app.unified_notification_manager.send_admin_notification.assert_called_once()
            call_args = mock_app.unified_notification_manager.send_admin_notification.call_args
            
            self.assertEqual(call_args[1]['message'], "Platform status changed by admin")
            self.assertEqual(call_args[1]['notification_type'], 'platform_management')
            self.assertIn('platform_id', call_args[1]['metadata'])
            self.assertIn('admin_user_id', call_args[1]['metadata'])

if __name__ == '__main__':
    unittest.main()