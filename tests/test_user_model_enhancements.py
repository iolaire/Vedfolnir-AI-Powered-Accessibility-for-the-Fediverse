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
from sqlalchemy.exc import InvalidRequestError


class TestUserModelEnhancements(unittest.TestCase):
    """Test enhanced User model with explicit relationship loading strategies"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user = User()
        self.user.id = 1
        self.user.username = "testuser"
        self.user.email = "test@test.com"
        self.user.role = UserRole.VIEWER
        self.user.is_active = True
        self.user.created_at = datetime.utcnow()
        
        # Create mock platform connections
        self.platform1 = Mock(spec=PlatformConnection)
        self.platform1.id = 1
        self.platform1.name = "Test Platform 1"
        self.platform1.platform_type = "pixelfed"
        self.platform1.is_active = True
        self.platform1.is_default = True
        self.platform1.created_at = datetime.utcnow()
        
        self.platform2 = Mock(spec=PlatformConnection)
        self.platform2.id = 2
        self.platform2.name = "Test Platform 2"
        self.platform2.platform_type = "mastodon"
        self.platform2.is_active = True
        self.platform2.is_default = False
        self.platform2.created_at = datetime.utcnow()
        
        self.inactive_platform = Mock(spec=PlatformConnection)
        self.inactive_platform.id = 3
        self.inactive_platform.name = "Inactive Platform"
        self.inactive_platform.platform_type = "pixelfed"
        self.inactive_platform.is_active = False
        self.inactive_platform.is_default = False
        self.inactive_platform.created_at = datetime.utcnow()
    
    def test_active_platforms_hybrid_property_success(self):
        """Test active_platforms hybrid property returns only active platforms"""
        # Mock platform_connections relationship
        self.user.platform_connections = [self.platform1, self.platform2, self.inactive_platform]
        
        active_platforms = self.user.active_platforms
        
        self.assertEqual(len(active_platforms), 2)
        self.assertIn(self.platform1, active_platforms)
        self.assertIn(self.platform2, active_platforms)
        self.assertNotIn(self.inactive_platform, active_platforms)
    
    def test_active_platforms_hybrid_property_detached_instance_error(self):
        """Test active_platforms hybrid property handles DetachedInstanceError gracefully"""
        # Mock platform_connections to raise DetachedInstanceError
        mock_connections = Mock()
        mock_connections.__iter__ = Mock(side_effect=DetachedInstanceError("Test detached instance"))
        self.user.platform_connections = mock_connections
        
        active_platforms = self.user.active_platforms
        
        # Should return empty list instead of raising exception
        self.assertEqual(active_platforms, [])
    
    def test_active_platforms_hybrid_property_general_exception(self):
        """Test active_platforms hybrid property handles general exceptions gracefully"""
        # Mock platform_connections to raise general exception
        mock_connections = Mock()
        mock_connections.__iter__ = Mock(side_effect=RuntimeError("Test error"))
        self.user.platform_connections = mock_connections
        
        active_platforms = self.user.active_platforms
        
        # Should return empty list instead of raising exception
        self.assertEqual(active_platforms, [])
    
    def test_default_platform_hybrid_property_with_default(self):
        """Test default_platform hybrid property returns the default platform"""
        self.user.platform_connections = [self.platform1, self.platform2]
        
        default_platform = self.user.default_platform
        
        self.assertEqual(default_platform, self.platform1)
        self.assertTrue(default_platform.is_default)
    
    def test_default_platform_hybrid_property_no_default_returns_first_active(self):
        """Test default_platform hybrid property returns first active when no default set"""
        # Set no platform as default
        self.platform1.is_default = False
        self.platform2.is_default = False
        self.user.platform_connections = [self.platform1, self.platform2]
        
        default_platform = self.user.default_platform
        
        self.assertEqual(default_platform, self.platform1)
    
    def test_default_platform_hybrid_property_no_active_platforms(self):
        """Test default_platform hybrid property returns None when no active platforms"""
        self.user.platform_connections = [self.inactive_platform]
        
        default_platform = self.user.default_platform
        
        self.assertIsNone(default_platform)
    
    def test_default_platform_hybrid_property_detached_instance_error(self):
        """Test default_platform hybrid property handles DetachedInstanceError gracefully"""
        # Mock platform_connections to raise DetachedInstanceError
        mock_connections = Mock()
        mock_connections.__iter__ = Mock(side_effect=DetachedInstanceError("Test detached instance"))
        self.user.platform_connections = mock_connections
        
        default_platform = self.user.default_platform
        
        # Should return None instead of raising exception
        self.assertIsNone(default_platform)
    
    def test_default_platform_hybrid_property_general_exception(self):
        """Test default_platform hybrid property handles general exceptions gracefully"""
        # Mock platform_connections to raise general exception
        mock_connections = Mock()
        mock_connections.__iter__ = Mock(side_effect=RuntimeError("Test error"))
        self.user.platform_connections = mock_connections
        
        default_platform = self.user.default_platform
        
        # Should return None instead of raising exception
        self.assertIsNone(default_platform)
    
    def test_get_default_platform_legacy_method(self):
        """Test get_default_platform legacy method uses hybrid property"""
        self.user.platform_connections = [self.platform1, self.platform2]
        
        default_platform = self.user.get_default_platform()
        
        self.assertEqual(default_platform, self.platform1)
        self.assertTrue(default_platform.is_default)
    
    def test_get_active_platforms_legacy_method(self):
        """Test get_active_platforms legacy method uses hybrid property"""
        self.user.platform_connections = [self.platform1, self.platform2, self.inactive_platform]
        
        active_platforms = self.user.get_active_platforms()
        
        self.assertEqual(len(active_platforms), 2)
        self.assertIn(self.platform1, active_platforms)
        self.assertIn(self.platform2, active_platforms)
        self.assertNotIn(self.inactive_platform, active_platforms)
    
    def test_get_platform_by_type(self):
        """Test get_platform_by_type method"""
        self.user.platform_connections = [self.platform1, self.platform2]
        
        pixelfed_platform = self.user.get_platform_by_type("pixelfed")
        mastodon_platform = self.user.get_platform_by_type("mastodon")
        nonexistent_platform = self.user.get_platform_by_type("nonexistent")
        
        self.assertEqual(pixelfed_platform, self.platform1)
        self.assertEqual(mastodon_platform, self.platform2)
        self.assertIsNone(nonexistent_platform)
    
    def test_get_platform_by_name(self):
        """Test get_platform_by_name method"""
        self.user.platform_connections = [self.platform1, self.platform2]
        
        platform1 = self.user.get_platform_by_name("Test Platform 1")
        platform2 = self.user.get_platform_by_name("Test Platform 2")
        nonexistent = self.user.get_platform_by_name("Nonexistent Platform")
        
        self.assertEqual(platform1, self.platform1)
        self.assertEqual(platform2, self.platform2)
        self.assertIsNone(nonexistent)
    
    def test_set_default_platform(self):
        """Test set_default_platform method"""
        self.user.platform_connections = [self.platform1, self.platform2]
        
        # Set platform2 as default
        self.user.set_default_platform(2)
        
        self.assertFalse(self.platform1.is_default)
        self.assertTrue(self.platform2.is_default)
    
    def test_has_platform_access(self):
        """Test has_platform_access method"""
        self.platform1.instance_url = "https://pixelfed.example.com"
        self.platform2.instance_url = "https://mastodon.example.com"
        self.user.platform_connections = [self.platform1, self.platform2]
        
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