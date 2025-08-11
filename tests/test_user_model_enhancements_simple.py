#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import User, PlatformConnection, UserSession, UserRole
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.ext.hybrid import hybrid_property


class MockPlatformConnection:
    """Simple mock platform connection that doesn't interfere with SQLAlchemy"""
    def __init__(self, id, name, platform_type, is_active=True, is_default=False):
        self.id = id
        self.name = name
        self.platform_type = platform_type
        self.instance_url = f"https://{platform_type}.example.com"
        self.username = "testuser"
        self.is_active = is_active
        self.is_default = is_default
        self.created_at = datetime.utcnow()


class TestUserModelEnhancements(unittest.TestCase):
    """Test enhanced User model with explicit relationship loading strategies"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user = User()
        self.user.id = 1
        self.user.username = "testuser"
        self.user.email = "test@example.com"
        self.user.role = UserRole.VIEWER
        self.user.is_active = True
        self.user.created_at = datetime.utcnow()
    
    def test_active_platforms_hybrid_property_exists(self):
        """Test that active_platforms is a hybrid property"""
        self.assertTrue(hasattr(User, 'active_platforms'))
        self.assertIsInstance(User.active_platforms, hybrid_property)
    
    def test_default_platform_hybrid_property_exists(self):
        """Test that default_platform is a hybrid property"""
        self.assertTrue(hasattr(User, 'default_platform'))
        self.assertIsInstance(User.default_platform, hybrid_property)
    
    def test_active_platforms_with_mock_connections(self):
        """Test active_platforms hybrid property with mock connections"""
        # Create mock connections list
        platform1 = MockPlatformConnection(1, "Platform 1", "pixelfed", is_active=True)
        platform2 = MockPlatformConnection(2, "Platform 2", "mastodon", is_active=True)
        inactive_platform = MockPlatformConnection(3, "Inactive", "pixelfed", is_active=False)
        
        # Mock the platform_connections attribute directly
        with patch.object(self.user, 'platform_connections', [platform1, platform2, inactive_platform]):
            active_platforms = self.user.active_platforms
            
            self.assertEqual(len(active_platforms), 2)
            self.assertIn(platform1, active_platforms)
            self.assertIn(platform2, active_platforms)
            self.assertNotIn(inactive_platform, active_platforms)
    
    def test_active_platforms_handles_exception(self):
        """Test active_platforms hybrid property handles exceptions gracefully"""
        # Mock platform_connections to raise an exception
        with patch.object(self.user, 'platform_connections', side_effect=RuntimeError("Test error")):
            active_platforms = self.user.active_platforms
            self.assertEqual(active_platforms, [])
    
    def test_default_platform_with_default_set(self):
        """Test default_platform hybrid property returns the default platform"""
        platform1 = MockPlatformConnection(1, "Platform 1", "pixelfed", is_active=True, is_default=True)
        platform2 = MockPlatformConnection(2, "Platform 2", "mastodon", is_active=True, is_default=False)
        
        with patch.object(self.user, 'platform_connections', [platform1, platform2]):
            default_platform = self.user.default_platform
            self.assertEqual(default_platform, platform1)
            self.assertTrue(default_platform.is_default)
    
    def test_default_platform_no_default_returns_first_active(self):
        """Test default_platform hybrid property returns first active when no default set"""
        platform1 = MockPlatformConnection(1, "Platform 1", "pixelfed", is_active=True, is_default=False)
        platform2 = MockPlatformConnection(2, "Platform 2", "mastodon", is_active=True, is_default=False)
        
        with patch.object(self.user, 'platform_connections', [platform1, platform2]):
            default_platform = self.user.default_platform
            self.assertEqual(default_platform, platform1)
    
    def test_default_platform_no_active_platforms(self):
        """Test default_platform hybrid property returns None when no active platforms"""
        inactive_platform = MockPlatformConnection(1, "Inactive", "pixelfed", is_active=False)
        
        with patch.object(self.user, 'platform_connections', [inactive_platform]):
            default_platform = self.user.default_platform
            self.assertIsNone(default_platform)
    
    def test_default_platform_handles_exception(self):
        """Test default_platform hybrid property handles exceptions gracefully"""
        with patch.object(self.user, 'platform_connections', side_effect=RuntimeError("Test error")):
            default_platform = self.user.default_platform
            self.assertIsNone(default_platform)
    
    def test_legacy_methods_use_hybrid_properties(self):
        """Test that legacy methods use the new hybrid properties"""
        platform1 = MockPlatformConnection(1, "Platform 1", "pixelfed", is_active=True, is_default=True)
        platform2 = MockPlatformConnection(2, "Platform 2", "mastodon", is_active=True, is_default=False)
        
        with patch.object(self.user, 'platform_connections', [platform1, platform2]):
            # Test get_default_platform
            default_platform = self.user.get_default_platform()
            self.assertEqual(default_platform, platform1)
            
            # Test get_active_platforms
            active_platforms = self.user.get_active_platforms()
            self.assertEqual(len(active_platforms), 2)
            self.assertIn(platform1, active_platforms)
            self.assertIn(platform2, active_platforms)
    
    def test_get_platform_by_type(self):
        """Test get_platform_by_type method"""
        platform1 = MockPlatformConnection(1, "Platform 1", "pixelfed", is_active=True)
        platform2 = MockPlatformConnection(2, "Platform 2", "mastodon", is_active=True)
        
        with patch.object(self.user, 'platform_connections', [platform1, platform2]):
            pixelfed_platform = self.user.get_platform_by_type("pixelfed")
            mastodon_platform = self.user.get_platform_by_type("mastodon")
            nonexistent_platform = self.user.get_platform_by_type("nonexistent")
            
            self.assertEqual(pixelfed_platform, platform1)
            self.assertEqual(mastodon_platform, platform2)
            self.assertIsNone(nonexistent_platform)
    
    def test_get_platform_by_name(self):
        """Test get_platform_by_name method"""
        platform1 = MockPlatformConnection(1, "Test Platform 1", "pixelfed", is_active=True)
        platform2 = MockPlatformConnection(2, "Test Platform 2", "mastodon", is_active=True)
        
        with patch.object(self.user, 'platform_connections', [platform1, platform2]):
            found_platform1 = self.user.get_platform_by_name("Test Platform 1")
            found_platform2 = self.user.get_platform_by_name("Test Platform 2")
            nonexistent = self.user.get_platform_by_name("Nonexistent Platform")
            
            self.assertEqual(found_platform1, platform1)
            self.assertEqual(found_platform2, platform2)
            self.assertIsNone(nonexistent)
    
    def test_set_default_platform(self):
        """Test set_default_platform method"""
        platform1 = MockPlatformConnection(1, "Platform 1", "pixelfed", is_active=True, is_default=True)
        platform2 = MockPlatformConnection(2, "Platform 2", "mastodon", is_active=True, is_default=False)
        
        with patch.object(self.user, 'platform_connections', [platform1, platform2]):
            # Set platform2 as default
            self.user.set_default_platform(2)
            
            self.assertFalse(platform1.is_default)
            self.assertTrue(platform2.is_default)
    
    def test_has_platform_access(self):
        """Test has_platform_access method"""
        platform1 = MockPlatformConnection(1, "Platform 1", "pixelfed", is_active=True)
        platform1.instance_url = "https://pixelfed.example.com"
        platform2 = MockPlatformConnection(2, "Platform 2", "mastodon", is_active=True)
        platform2.instance_url = "https://mastodon.example.com"
        
        with patch.object(self.user, 'platform_connections', [platform1, platform2]):
            has_pixelfed_access = self.user.has_platform_access("pixelfed", "https://pixelfed.example.com")
            has_mastodon_access = self.user.has_platform_access("mastodon", "https://mastodon.example.com")
            has_no_access = self.user.has_platform_access("pixelfed", "https://other.example.com")
            
            self.assertTrue(has_pixelfed_access)
            self.assertTrue(has_mastodon_access)
            self.assertFalse(has_no_access)
    
    def test_has_permission(self):
        """Test has_permission method"""
        # Test with VIEWER role
        self.user.role = UserRole.VIEWER
        self.assertTrue(self.user.has_permission(UserRole.VIEWER))
        self.assertFalse(self.user.has_permission(UserRole.REVIEWER))
        self.assertFalse(self.user.has_permission(UserRole.MODERATOR))
        self.assertFalse(self.user.has_permission(UserRole.ADMIN))
        
        # Test with ADMIN role
        self.user.role = UserRole.ADMIN
        self.assertTrue(self.user.has_permission(UserRole.VIEWER))
        self.assertTrue(self.user.has_permission(UserRole.REVIEWER))
        self.assertTrue(self.user.has_permission(UserRole.MODERATOR))
        self.assertTrue(self.user.has_permission(UserRole.ADMIN))
    
    def test_password_methods(self):
        """Test password setting and checking methods"""
        password = "testpassword123"
        
        self.user.set_password(password)
        self.assertIsNotNone(self.user.password_hash)
        self.assertNotEqual(self.user.password_hash, password)  # Should be hashed
        
        self.assertTrue(self.user.check_password(password))
        self.assertFalse(self.user.check_password("wrongpassword"))
    
    def test_user_repr(self):
        """Test User __repr__ method"""
        repr_str = repr(self.user)
        self.assertEqual(repr_str, "<User testuser>")


class TestPlatformConnectionEnhancements(unittest.TestCase):
    """Test enhanced PlatformConnection model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.platform = PlatformConnection()
        self.platform.id = 1
        self.platform.name = "Test Platform"
        self.platform.platform_type = "pixelfed"
        self.platform.instance_url = "https://pixelfed.example.com"
        self.platform.username = "testuser"
        self.platform.is_active = True
        self.platform.is_default = True
        self.platform.created_at = datetime.utcnow()
        self.platform.updated_at = datetime.utcnow()
        self.platform.last_used = datetime.utcnow()
    
    def test_to_dict_method(self):
        """Test to_dict method for safe serialization"""
        result = self.platform.to_dict()
        
        expected_keys = {
            'id', 'name', 'platform_type', 'instance_url', 'username',
            'is_active', 'is_default', 'created_at', 'updated_at', 'last_used'
        }
        
        self.assertEqual(set(result.keys()), expected_keys)
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['name'], "Test Platform")
        self.assertEqual(result['platform_type'], "pixelfed")
        self.assertEqual(result['instance_url'], "https://pixelfed.example.com")
        self.assertEqual(result['username'], "testuser")
        self.assertTrue(result['is_active'])
        self.assertTrue(result['is_default'])
        self.assertIsNotNone(result['created_at'])
        self.assertIsNotNone(result['updated_at'])
        self.assertIsNotNone(result['last_used'])
    
    def test_to_dict_method_with_none_dates(self):
        """Test to_dict method handles None dates gracefully"""
        self.platform.created_at = None
        self.platform.updated_at = None
        self.platform.last_used = None
        
        result = self.platform.to_dict()
        
        self.assertIsNone(result['created_at'])
        self.assertIsNone(result['updated_at'])
        self.assertIsNone(result['last_used'])
    
    def test_platform_connection_repr(self):
        """Test PlatformConnection __repr__ method"""
        repr_str = repr(self.platform)
        self.assertEqual(repr_str, "<PlatformConnection Test Platform (pixelfed)>")


class TestUserSessionEnhancements(unittest.TestCase):
    """Test enhanced UserSession model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.session = UserSession()
        self.session.id = 1
        self.session.session_id = "test-session-123"
        self.session.user_id = 1
        self.session.active_platform_id = 1
        self.session.created_at = datetime.utcnow()
        self.session.updated_at = datetime.utcnow()
        self.session.user_agent = "Test User Agent"
        self.session.ip_address = "127.0.0.1"
    
    def test_user_session_repr(self):
        """Test UserSession __repr__ method"""
        repr_str = repr(self.session)
        self.assertEqual(repr_str, "<UserSession test-session-123 - User 1>")


class TestModelRelationshipLoadingStrategies(unittest.TestCase):
    """Test that model relationships use proper loading strategies"""
    
    def test_user_relationships_use_select_loading(self):
        """Test that User model relationships use select loading strategy"""
        # Check platform_connections relationship
        platform_connections_rel = User.platform_connections.property
        self.assertEqual(platform_connections_rel.lazy, 'select')
        
        # Check sessions relationship
        sessions_rel = User.sessions.property
        self.assertEqual(sessions_rel.lazy, 'select')
    
    def test_platform_connection_relationships_use_select_loading(self):
        """Test that PlatformConnection model relationships use select loading strategy"""
        # Check user relationship
        user_rel = PlatformConnection.user.property
        self.assertEqual(user_rel.lazy, 'select')
        
        # Check posts relationship
        posts_rel = PlatformConnection.posts.property
        self.assertEqual(posts_rel.lazy, 'select')
        
        # Check images relationship
        images_rel = PlatformConnection.images.property
        self.assertEqual(images_rel.lazy, 'select')
        
        # Check processing_runs relationship
        processing_runs_rel = PlatformConnection.processing_runs.property
        self.assertEqual(processing_runs_rel.lazy, 'select')
        
        # Check user_sessions relationship
        user_sessions_rel = PlatformConnection.user_sessions.property
        self.assertEqual(user_sessions_rel.lazy, 'select')
    
    def test_user_session_relationships_use_select_loading(self):
        """Test that UserSession model relationships use select loading strategy"""
        # Check user relationship
        user_rel = UserSession.user.property
        self.assertEqual(user_rel.lazy, 'select')
        
        # Check active_platform relationship
        active_platform_rel = UserSession.active_platform.property
        self.assertEqual(active_platform_rel.lazy, 'select')


if __name__ == '__main__':
    unittest.main()