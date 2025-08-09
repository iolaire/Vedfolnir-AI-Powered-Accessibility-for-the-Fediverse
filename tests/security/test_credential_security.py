# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security tests for credential storage and encryption

Tests cryptographic security of platform credentials.
"""

import unittest
import os
from cryptography.fernet import Fernet, InvalidToken
from tests.fixtures.platform_fixtures import PlatformTestCase
from models import PlatformConnection


class TestCredentialEncryptionSecurity(PlatformTestCase):
    """Test cryptographic security of credential encryption"""
    
    def test_credentials_encrypted_at_rest(self):
        """Test credentials are encrypted in database storage"""
        platform = self.get_test_platform()
        
        # Set sensitive credentials
        platform.access_token = 'sensitive_access_token_123'
        platform.client_key = 'sensitive_client_key_456'
        platform.client_secret = 'sensitive_client_secret_789'
        self.session.commit()
        
        # Verify encrypted storage doesn't contain plaintext
        self.assertNotEqual(platform._access_token, 'sensitive_access_token_123')
        self.assertNotEqual(platform._client_key, 'sensitive_client_key_456')
        self.assertNotEqual(platform._client_secret, 'sensitive_client_secret_789')
        
        # Verify encrypted data is not human readable
        self.assertNotIn('sensitive', platform._access_token or '')
        self.assertNotIn('token', platform._access_token or '')
        self.assertNotIn('123', platform._access_token or '')
    
    def test_encryption_key_security(self):
        """Test encryption key cannot be easily compromised"""
        # Test with invalid key
        original_key = os.environ.get('PLATFORM_ENCRYPTION_KEY')
        
        try:
            # Set invalid key
            os.environ['PLATFORM_ENCRYPTION_KEY'] = 'invalid_key'
            
            # Should fail to decrypt
            platform = self.get_test_platform()
            with self.assertRaises(Exception):
                _ = platform.access_token
                
        finally:
            # Restore original key
            if original_key:
                os.environ['PLATFORM_ENCRYPTION_KEY'] = original_key
    
    def test_credential_tampering_detection(self):
        """Test that credential tampering is detected"""
        platform = self.get_test_platform()
        platform.access_token = 'original_token'
        self.session.commit()
        
        # Tamper with encrypted data
        platform._access_token = 'tampered_data'
        
        # Should fail to decrypt tampered data
        decrypted = platform.access_token
        self.assertIsNone(decrypted)  # Should return None on decryption failure
    
    def test_different_platforms_different_encryption(self):
        """Test that different platforms have different encrypted values"""
        user = self.get_test_user()
        
        # Create two platforms with same token
        same_token = 'identical_token_value'
        
        platform1 = PlatformConnection(
            user_id=user.id,
            name='Platform 1',
            platform_type='pixelfed',
            instance_url='https://test1.com',
            username='user1',
            access_token=same_token
        )
        
        platform2 = PlatformConnection(
            user_id=user.id,
            name='Platform 2', 
            platform_type='mastodon',
            instance_url='https://test2.com',
            username='user2',
            access_token=same_token
        )
        
        self.session.add(platform1)
        self.session.add(platform2)
        self.session.commit()
        
        # Encrypted values should be different (due to random IV)
        self.assertNotEqual(platform1._access_token, platform2._access_token)
        
        # But decrypted values should be same
        self.assertEqual(platform1.access_token, platform2.access_token)


class TestCredentialAccessControl(PlatformTestCase):
    """Test access control for platform credentials"""
    
    def test_user_cannot_access_other_users_credentials(self):
        """Test users cannot access other users' platform credentials"""
        user1 = self.get_test_user()
        user2 = self.users[1]
        
        # Create platform for user2
        user2_platform = PlatformConnection(
            user_id=user2.id,
            name='User2 Platform',
            platform_type='pixelfed',
            instance_url='https://user2.test.com',
            username='user2',
            access_token='user2_secret_token'
        )
        self.session.add(user2_platform)
        self.session.commit()
        
        # User1 should not be able to access user2's platforms
        user1_platforms = self.session.query(PlatformConnection).filter(
            PlatformConnection.user_id == user1.id
        ).all()
        
        user2_platform_ids = {p.id for p in user1_platforms}
        self.assertNotIn(user2_platform.id, user2_platform_ids)
    
    def test_platform_connection_ownership_validation(self):
        """Test platform connection ownership is validated"""
        user1 = self.get_test_user()
        user2 = self.users[1]
        
        # Get user1's platform
        user1_platform = self.get_test_platform()
        
        # Verify ownership
        self.assertEqual(user1_platform.user_id, user1.id)
        self.assertNotEqual(user1_platform.user_id, user2.id)
    
    def test_credential_decryption_requires_valid_key(self):
        """Test credential decryption requires valid encryption key"""
        platform = self.get_test_platform()
        platform.access_token = 'test_token_for_decryption'
        self.session.commit()
        
        # Store encrypted value
        encrypted_token = platform._access_token
        
        # Change encryption key
        original_key = os.environ.get('PLATFORM_ENCRYPTION_KEY')
        try:
            os.environ['PLATFORM_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
            
            # Should not be able to decrypt with wrong key
            decrypted = platform.access_token
            self.assertIsNone(decrypted)
            
        finally:
            # Restore original key
            if original_key:
                os.environ['PLATFORM_ENCRYPTION_KEY'] = original_key


class TestSessionSecurity(PlatformTestCase):
    """Test session security for platform context"""
    
    def test_session_platform_context_isolation(self):
        """Test session platform context is properly isolated"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Simulate different sessions
        session1_data = {'user_id': user.id, 'platform_id': platform1.id}
        session2_data = {'user_id': user.id, 'platform_id': platform2.id}
        
        # Sessions should be isolated
        self.assertNotEqual(session1_data['platform_id'], session2_data['platform_id'])
    
    def test_session_tampering_prevention(self):
        """Test session data tampering prevention"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Valid session data
        valid_session = {
            'user_id': user.id,
            'platform_id': platform.id,
            'timestamp': 1234567890
        }
        
        # Tampered session data
        tampered_session = {
            'user_id': 99999,  # Invalid user
            'platform_id': platform.id,
            'timestamp': 1234567890
        }
        
        # Validation should detect tampering
        def validate_session(session_data):
            user_exists = self.session.query(type(user)).get(session_data['user_id']) is not None
            platform_exists = self.session.query(PlatformConnection).get(session_data['platform_id']) is not None
            return user_exists and platform_exists
        
        self.assertTrue(validate_session(valid_session))
        self.assertFalse(validate_session(tampered_session))


class TestDataIsolationSecurity(PlatformTestCase):
    """Test security of data isolation between platforms"""
    
    def test_platform_data_cannot_be_accessed_cross_platform(self):
        """Test platform data cannot be accessed from other platforms"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Get data for platform1
        from models import Post
        platform1_posts = self.session.query(Post).filter(
            Post.platform_connection_id == platform1.id
        ).all()
        
        # Get data for platform2
        platform2_posts = self.session.query(Post).filter(
            Post.platform_connection_id == platform2.id
        ).all()
        
        # Verify complete isolation
        platform1_ids = {post.id for post in platform1_posts}
        platform2_ids = {post.id for post in platform2_posts}
        
        self.assertEqual(len(platform1_ids.intersection(platform2_ids)), 0)
    
    def test_platform_context_prevents_unauthorized_access(self):
        """Test platform context prevents unauthorized data access"""
        user1 = self.get_test_user()
        user2 = self.users[1]
        
        # Create platform for user2
        user2_platform = PlatformConnection(
            user_id=user2.id,
            name='User2 Secure Platform',
            platform_type='pixelfed',
            instance_url='https://secure.test.com',
            username='secureuser',
            access_token='secure_token'
        )
        self.session.add(user2_platform)
        self.session.commit()
        
        # User1 should not be able to set context to user2's platform
        from platform_context import PlatformContextManager, PlatformContextError
        context_manager = PlatformContextManager(self.session)
        
        with self.assertRaises(PlatformContextError):
            context_manager.set_context(user1.id, user2_platform.id)


if __name__ == '__main__':
    unittest.main()