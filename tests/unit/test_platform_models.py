# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for platform-aware models

Tests all platform-aware model functionality including:
- PlatformConnection model operations
- User model platform methods
- Model relationships and constraints
- Credential encryption/decryption
"""

import unittest
import os
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from tests.fixtures.platform_fixtures import PlatformTestCase, PlatformTestFixtures
from models import User, UserRole, PlatformConnection, UserSession, Post, Image, ProcessingStatus

class TestPlatformConnectionModel(PlatformTestCase):
    """Test PlatformConnection model functionality"""
    
    def test_platform_connection_creation(self):
        """Test creating platform connections"""
        user = self.get_test_user()
        
        platform = PlatformConnection(
            user_id=user.id,
            name='Test Platform',
            platform_type='pixelfed',
            instance_url='https://test.example.com',
            username='testuser',
            access_token='test_token',
            is_default=True
        )
        
        self.session.add(platform)
        self.session.commit()
        
        # Verify platform was created
        saved_platform = self.session.query(PlatformConnection).filter_by(name='Test Platform').first()
        self.assertIsNotNone(saved_platform)
        self.assertEqual(saved_platform.platform_type, 'pixelfed')
        self.assertEqual(saved_platform.instance_url, 'https://test.example.com')
        self.assertTrue(saved_platform.is_default)
    
    def test_credential_encryption(self):
        """Test credential encryption and decryption"""
        platform = self.get_test_platform()
        
        # Test access token encryption
        original_token = 'test_access_token_123'
        platform.access_token = original_token
        self.session.commit()
        
        # Verify token is encrypted in storage
        self.assertNotEqual(platform._access_token, original_token)
        
        # Verify token can be decrypted
        decrypted_token = platform.access_token
        self.assertEqual(decrypted_token, original_token)
    
    def test_client_credentials_encryption(self):
        """Test client key and secret encryption"""
        platform = self.get_test_platform('mastodon')
        
        # Test client key encryption
        original_key = 'test_client_key_456'
        platform.client_key = original_key
        self.session.commit()
        
        self.assertNotEqual(platform._client_key, original_key)
        self.assertEqual(platform.client_key, original_key)
        
        # Test client secret encryption
        original_secret = 'test_client_secret_789'
        platform.client_secret = original_secret
        self.session.commit()
        
        self.assertNotEqual(platform._client_secret, original_secret)
        self.assertEqual(platform.client_secret, original_secret)
    
    def test_to_activitypub_config(self):
        """Test conversion to ActivityPub config"""
        platform = self.get_test_platform()
        
        config = platform.to_activitypub_config()
        
        self.assertIsNotNone(config)
        self.assertEqual(config.instance_url, platform.instance_url)
        self.assertEqual(config.access_token, platform.access_token)
        self.assertEqual(config.api_type, platform.platform_type)
        self.assertEqual(config.username, platform.username)
    
    def test_unique_constraints(self):
        """Test unique constraints on platform connections"""
        user = self.get_test_user()
        
        # Try to create duplicate platform name for same user
        platform1 = PlatformConnection(
            user_id=user.id,
            name='Duplicate Name',
            platform_type='pixelfed',
            instance_url='https://test1.com',
            username='user1',
            access_token='token1'
        )
        self.session.add(platform1)
        self.session.commit()
        
        platform2 = PlatformConnection(
            user_id=user.id,
            name='Duplicate Name',
            platform_type='mastodon',
            instance_url='https://test2.com',
            username='user2',
            access_token='token2'
        )
        self.session.add(platform2)
        
        with self.assertRaises(IntegrityError):
            self.session.commit()
    
    def test_platform_validation(self):
        """Test platform type validation"""
        user = self.get_test_user()
        
        # Valid platform types should work
        for platform_type in ['pixelfed', 'mastodon']:
            platform = PlatformConnection(
                user_id=user.id,
                name=f'Test {platform_type}',
                platform_type=platform_type,
                instance_url=f'https://{platform_type}.test',
                username='testuser',
                access_token='test_token'
            )
            self.session.add(platform)
        
        self.session.commit()
        
        # Verify platforms were created
        platforms = self.session.query(PlatformConnection).filter(
            PlatformConnection.user_id == user.id,
            PlatformConnection.name.like('Test %')
        ).all()
        self.assertEqual(len(platforms), 2)

class TestUserModelPlatformMethods(PlatformTestCase):
    """Test User model platform-related methods"""
    
    def test_get_active_platforms(self):
        """Test getting user's active platforms"""
        user = self.get_test_user()
        
        active_platforms = user.get_active_platforms()
        
        # Should return all active platforms for user
        self.assertEqual(len(active_platforms), 3)  # From fixtures
        
        # All should be active
        for platform in active_platforms:
            self.assertTrue(platform.is_active)
            self.assertEqual(platform.user_id, user.id)
    
    def test_get_default_platform(self):
        """Test getting user's default platform"""
        user = self.get_test_user()
        
        default_platform = user.get_default_platform()
        
        self.assertIsNotNone(default_platform)
        self.assertTrue(default_platform.is_default)
        self.assertEqual(default_platform.user_id, user.id)
    
    def test_get_platform_by_type(self):
        """Test getting platform by type"""
        user = self.get_test_user()
        
        pixelfed_platform = user.get_platform_by_type('pixelfed')
        mastodon_platform = user.get_platform_by_type('mastodon')
        
        self.assertIsNotNone(pixelfed_platform)
        self.assertEqual(pixelfed_platform.platform_type, 'pixelfed')
        
        self.assertIsNotNone(mastodon_platform)
        self.assertEqual(mastodon_platform.platform_type, 'mastodon')
    
    def test_get_platform_by_name(self):
        """Test getting platform by name"""
        user = self.get_test_user()
        
        platform = user.get_platform_by_name('Test Pixelfed')
        
        self.assertIsNotNone(platform)
        self.assertEqual(platform.name, 'Test Pixelfed')
        self.assertEqual(platform.user_id, user.id)
    
    def test_set_default_platform(self):
        """Test setting default platform"""
        user = self.get_test_user()
        platforms = user.get_active_platforms()
        
        # Set second platform as default
        new_default = platforms[1]
        user.set_default_platform(new_default.id)
        self.session.commit()
        
        # Verify default was changed
        updated_default = user.get_default_platform()
        self.assertEqual(updated_default.id, new_default.id)
        
        # Verify old default is no longer default
        old_default = self.session.query(PlatformConnection).filter_by(
            user_id=user.id,
            name='Test Pixelfed'
        ).first()
        self.assertFalse(old_default.is_default)
    
    def test_has_platform_access(self):
        """Test platform access validation"""
        user = self.get_test_user()
        
        # Should have access to platforms in fixtures
        self.assertTrue(user.has_platform_access('pixelfed', 'https://pixelfed.test'))
        self.assertTrue(user.has_platform_access('mastodon', 'https://mastodon.test'))
        
        # Should not have access to non-existent platforms
        self.assertFalse(user.has_platform_access('pixelfed', 'https://other.test'))
        self.assertFalse(user.has_platform_access('other', 'https://pixelfed.test'))

class TestPlatformAwareModels(PlatformTestCase):
    """Test platform awareness in Post and Image models"""
    
    def test_post_platform_consistency(self):
        """Test post platform consistency validation"""
        post = self.posts[0]
        
        # Test platform info retrieval
        platform_info = post.get_platform_info()
        
        self.assertIsNotNone(platform_info)
        self.assertIn('platform_type', platform_info)
        self.assertIn('instance_url', platform_info)
        self.assertEqual(platform_info['platform_type'], post.platform_connection.platform_type)
    
    def test_image_platform_consistency(self):
        """Test image platform consistency validation"""
        image = self.images[0]
        
        # Test platform info retrieval
        platform_info = image.get_platform_info()
        
        self.assertIsNotNone(platform_info)
        self.assertEqual(platform_info['platform_type'], image.platform_connection.platform_type)
        self.assertEqual(platform_info['instance_url'], image.platform_connection.instance_url)
    
    def test_platform_relationships(self):
        """Test platform relationships work correctly"""
        platform = self.get_test_platform()
        
        # Test posts relationship
        platform_posts = platform.posts
        self.assertGreater(len(platform_posts), 0)
        
        for post in platform_posts:
            self.assertEqual(post.platform_connection_id, platform.id)
        
        # Test images relationship
        platform_images = platform.images
        self.assertGreater(len(platform_images), 0)
        
        for image in platform_images:
            self.assertEqual(image.platform_connection_id, platform.id)

class TestUserSessionModel(PlatformTestCase):
    """Test UserSession model functionality"""
    
    def test_user_session_creation(self):
        """Test creating user sessions"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        session = UserSession(
            user_id=user.id,
            session_id='test_session_123',
            active_platform_id=platform.id
        )
        
        self.session.add(session)
        self.session.commit()
        
        # Verify session was created
        saved_session = self.session.query(UserSession).filter_by(
            session_id='test_session_123'
        ).first()
        
        self.assertIsNotNone(saved_session)
        self.assertEqual(saved_session.user_id, user.id)
        self.assertEqual(saved_session.active_platform_id, platform.id)
    
    def test_session_relationships(self):
        """Test session relationships"""
        test_session = self.create_test_session()
        
        # Test user relationship
        self.assertIsNotNone(test_session.user)
        self.assertEqual(test_session.user.id, test_session.user_id)
        
        # Test platform relationship
        self.assertIsNotNone(test_session.active_platform)
        self.assertEqual(test_session.active_platform.id, test_session.active_platform_id)
    
    def test_session_unique_constraint(self):
        """Test session ID unique constraint"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Create first session
        session1 = UserSession(
            user_id=user.id,
            session_id='duplicate_session',
            active_platform_id=platform.id
        )
        self.session.add(session1)
        self.session.commit()
        
        # Try to create duplicate session ID
        session2 = UserSession(
            user_id=user.id,
            session_id='duplicate_session',
            active_platform_id=platform.id
        )
        self.session.add(session2)
        
        with self.assertRaises(IntegrityError):
            self.session.commit()

class TestModelValidation(PlatformTestCase):
    """Test model validation and constraints"""
    
    def test_required_fields(self):
        """Test required field validation"""
        user = self.get_test_user()
        
        # Test missing required fields
        with self.assertRaises(Exception):
            platform = PlatformConnection(
                user_id=user.id,
                # Missing name
                platform_type='pixelfed',
                instance_url='https://test.com',
                access_token='token'
            )
            self.session.add(platform)
            self.session.commit()
    
    def test_field_length_constraints(self):
        """Test field length constraints"""
        user = self.get_test_user()
        
        # Test name length constraint
        long_name = 'x' * 200  # Assuming max length is 100
        platform = PlatformConnection(
            user_id=user.id,
            name=long_name,
            platform_type='pixelfed',
            instance_url='https://test.com',
            username='user',
            access_token='token'
        )
        
        self.session.add(platform)
        # Should not raise exception for reasonable lengths
        self.session.commit()
    
    def test_boolean_defaults(self):
        """Test boolean field defaults"""
        user = self.get_test_user()
        
        platform = PlatformConnection(
            user_id=user.id,
            name='Test Defaults',
            platform_type='pixelfed',
            instance_url='https://test.com',
            username='user',
            access_token='token'
        )
        
        self.session.add(platform)
        self.session.commit()
        
        # Test defaults
        self.assertTrue(platform.is_active)  # Should default to True
        self.assertFalse(platform.is_default)  # Should default to False

if __name__ == '__main__':
    unittest.main()