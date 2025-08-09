# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for platform credential encryption

Tests encryption/decryption functionality for platform credentials including:
- Access token encryption/decryption
- Client key/secret encryption/decryption
- Encryption key management
- Security validation
"""

import unittest
import os
from unittest.mock import patch, Mock
from cryptography.fernet import Fernet, InvalidToken

from tests.fixtures.platform_fixtures import PlatformTestCase
from models import PlatformConnection


class TestCredentialEncryption(PlatformTestCase):
    """Test credential encryption and decryption"""
    
    def test_access_token_encryption(self):
        """Test access token encryption and decryption"""
        platform = self.get_test_platform()
        
        # Set access token
        original_token = 'test_access_token_12345'
        platform.access_token = original_token
        self.session.commit()
        
        # Verify token is encrypted in storage
        self.assertNotEqual(platform._access_token, original_token)
        self.assertIsNotNone(platform._access_token)
        
        # Verify token can be decrypted correctly
        decrypted_token = platform.access_token
        self.assertEqual(decrypted_token, original_token)
    
    def test_client_key_encryption(self):
        """Test client key encryption and decryption"""
        platform = self.get_test_platform('mastodon')
        
        # Set client key
        original_key = 'test_client_key_67890'
        platform.client_key = original_key
        self.session.commit()
        
        # Verify key is encrypted in storage
        self.assertNotEqual(platform._client_key, original_key)
        self.assertIsNotNone(platform._client_key)
        
        # Verify key can be decrypted correctly
        decrypted_key = platform.client_key
        self.assertEqual(decrypted_key, original_key)
    
    def test_client_secret_encryption(self):
        """Test client secret encryption and decryption"""
        platform = self.get_test_platform('mastodon')
        
        # Set client secret
        original_secret = 'test_client_secret_abcdef'
        platform.client_secret = original_secret
        self.session.commit()
        
        # Verify secret is encrypted in storage
        self.assertNotEqual(platform._client_secret, original_secret)
        self.assertIsNotNone(platform._client_secret)
        
        # Verify secret can be decrypted correctly
        decrypted_secret = platform.client_secret
        self.assertEqual(decrypted_secret, original_secret)
    
    def test_empty_credential_handling(self):
        """Test handling of empty/None credentials"""
        platform = self.get_test_platform()
        
        # Set empty credentials
        platform.access_token = None
        platform.client_key = None
        platform.client_secret = None
        self.session.commit()
        
        # Should handle None values gracefully
        self.assertIsNone(platform.access_token)
        self.assertIsNone(platform.client_key)
        self.assertIsNone(platform.client_secret)
        
        # Storage should also be None
        self.assertIsNone(platform._access_token)
        self.assertIsNone(platform._client_key)
        self.assertIsNone(platform._client_secret)
    
    def test_credential_update(self):
        """Test updating encrypted credentials"""
        platform = self.get_test_platform()
        
        # Set initial token
        initial_token = 'initial_token_123'
        platform.access_token = initial_token
        self.session.commit()
        
        # Update token
        updated_token = 'updated_token_456'
        platform.access_token = updated_token
        self.session.commit()
        
        # Verify update worked
        self.assertEqual(platform.access_token, updated_token)
        self.assertNotEqual(platform.access_token, initial_token)
    
    def test_multiple_platforms_encryption(self):
        """Test encryption works independently for multiple platforms"""
        user = self.get_test_user()
        
        # Create two platforms with different tokens
        platform1 = PlatformConnection(
            user_id=user.id,
            name='Platform 1',
            platform_type='pixelfed',
            instance_url='https://platform1.test',
            username='user1',
            access_token='token_platform_1'
        )
        
        platform2 = PlatformConnection(
            user_id=user.id,
            name='Platform 2',
            platform_type='mastodon',
            instance_url='https://platform2.test',
            username='user2',
            access_token='token_platform_2'
        )
        
        self.session.add(platform1)
        self.session.add(platform2)
        self.session.commit()
        
        # Verify both are encrypted differently
        self.assertNotEqual(platform1._access_token, platform2._access_token)
        self.assertNotEqual(platform1._access_token, 'token_platform_1')
        self.assertNotEqual(platform2._access_token, 'token_platform_2')
        
        # Verify both decrypt correctly
        self.assertEqual(platform1.access_token, 'token_platform_1')
        self.assertEqual(platform2.access_token, 'token_platform_2')


class TestEncryptionKeyManagement(unittest.TestCase):
    """Test encryption key management"""
    
    def setUp(self):
        """Set up test environment"""
        # Store original environment
        self.original_key = os.environ.get('PLATFORM_ENCRYPTION_KEY')
    
    def tearDown(self):
        """Restore original environment"""
        if self.original_key:
            os.environ['PLATFORM_ENCRYPTION_KEY'] = self.original_key
        elif 'PLATFORM_ENCRYPTION_KEY' in os.environ:
            del os.environ['PLATFORM_ENCRYPTION_KEY']
    
    def test_encryption_key_from_environment(self):
        """Test getting encryption key from environment"""
        test_key = Fernet.generate_key().decode()
        os.environ['PLATFORM_ENCRYPTION_KEY'] = test_key
        
        key = PlatformConnection._get_encryption_key()
        
        self.assertEqual(key.decode(), test_key)
    
    def test_encryption_key_generation(self):
        """Test encryption key generation when not in environment"""
        # Remove key from environment
        if 'PLATFORM_ENCRYPTION_KEY' in os.environ:
            del os.environ['PLATFORM_ENCRYPTION_KEY']
        
        key = PlatformConnection._get_encryption_key()
        
        # Should generate a valid key
        self.assertIsInstance(key, bytes)
        
        # Should be able to create cipher
        cipher = Fernet(key)
        self.assertIsInstance(cipher, Fernet)
    
    def test_cipher_creation(self):
        """Test cipher creation"""
        cipher = PlatformConnection._get_cipher()
        
        self.assertIsInstance(cipher, Fernet)
        
        # Should be able to encrypt/decrypt
        test_data = b'test_data_123'
        encrypted = cipher.encrypt(test_data)
        decrypted = cipher.decrypt(encrypted)
        
        self.assertEqual(decrypted, test_data)
    
    @patch('models.logging')
    def test_encryption_key_warning(self, mock_logging):
        """Test warning when generating encryption key"""
        # Remove key from environment
        if 'PLATFORM_ENCRYPTION_KEY' in os.environ:
            del os.environ['PLATFORM_ENCRYPTION_KEY']
        
        PlatformConnection._get_encryption_key()
        
        # Should log warning
        mock_logging.warning.assert_called_once()
        warning_call = mock_logging.warning.call_args[0][0]
        self.assertIn('PLATFORM_ENCRYPTION_KEY', warning_call)


class TestEncryptionSecurity(PlatformTestCase):
    """Test encryption security aspects"""
    
    def test_encrypted_data_not_readable(self):
        """Test that encrypted data is not human-readable"""
        platform = self.get_test_platform()
        
        # Set a recognizable token
        recognizable_token = 'VERY_RECOGNIZABLE_TOKEN_123'
        platform.access_token = recognizable_token
        self.session.commit()
        
        # Encrypted data should not contain the original token
        encrypted_data = platform._access_token
        self.assertNotIn('VERY_RECOGNIZABLE', encrypted_data)
        self.assertNotIn('TOKEN', encrypted_data)
        self.assertNotIn('123', encrypted_data)
    
    def test_encryption_deterministic(self):
        """Test that encryption produces different results each time"""
        platform = self.get_test_platform()
        
        # Set same token multiple times
        test_token = 'same_token_every_time'
        
        platform.access_token = test_token
        self.session.commit()
        first_encrypted = platform._access_token
        
        platform.access_token = test_token
        self.session.commit()
        second_encrypted = platform._access_token
        
        # Encrypted values should be different (due to random IV)
        self.assertNotEqual(first_encrypted, second_encrypted)
        
        # But both should decrypt to same value
        self.assertEqual(platform.access_token, test_token)
    
    def test_decryption_with_wrong_key(self):
        """Test that decryption fails with wrong key"""
        platform = self.get_test_platform()
        
        # Set token with current key
        platform.access_token = 'test_token_123'
        self.session.commit()
        encrypted_data = platform._access_token
        
        # Try to decrypt with different key
        wrong_key = Fernet.generate_key()
        wrong_cipher = Fernet(wrong_key)
        
        with self.assertRaises(InvalidToken):
            wrong_cipher.decrypt(encrypted_data.encode())
    
    def test_credential_length_handling(self):
        """Test handling of various credential lengths"""
        platform = self.get_test_platform()
        
        # Test very short credential
        short_token = 'x'
        platform.access_token = short_token
        self.session.commit()
        self.assertEqual(platform.access_token, short_token)
        
        # Test very long credential
        long_token = 'x' * 1000
        platform.access_token = long_token
        self.session.commit()
        self.assertEqual(platform.access_token, long_token)
        
        # Test credential with special characters
        special_token = 'token!@#$%^&*()_+-=[]{}|;:,.<>?'
        platform.access_token = special_token
        self.session.commit()
        self.assertEqual(platform.access_token, special_token)
    
    def test_unicode_credential_handling(self):
        """Test handling of Unicode characters in credentials"""
        platform = self.get_test_platform()
        
        # Test Unicode token
        unicode_token = 'token_with_unicode_🔐🗝️🔑'
        platform.access_token = unicode_token
        self.session.commit()
        
        # Should handle Unicode correctly
        self.assertEqual(platform.access_token, unicode_token)


class TestEncryptionErrorHandling(PlatformTestCase):
    """Test encryption error handling"""
    
    @patch('models.PlatformConnection._get_cipher')
    def test_encryption_failure_handling(self, mock_get_cipher):
        """Test handling of encryption failures"""
        # Mock cipher to raise exception
        mock_cipher = Mock()
        mock_cipher.encrypt.side_effect = Exception("Encryption failed")
        mock_get_cipher.return_value = mock_cipher
        
        platform = self.get_test_platform()
        
        # Should raise exception when encryption fails
        with self.assertRaises(Exception):
            platform.access_token = 'test_token'
    
    @patch('models.PlatformConnection._get_cipher')
    def test_decryption_failure_handling(self, mock_get_cipher):
        """Test handling of decryption failures"""
        platform = self.get_test_platform()
        
        # Set token normally first
        platform.access_token = 'test_token'
        self.session.commit()
        
        # Mock cipher to raise exception on decrypt
        mock_cipher = Mock()
        mock_cipher.decrypt.side_effect = Exception("Decryption failed")
        mock_get_cipher.return_value = mock_cipher
        
        # Should return None when decryption fails
        decrypted_token = platform.access_token
        self.assertIsNone(decrypted_token)
    
    @patch('models.logging')
    def test_encryption_error_logging(self, mock_logging):
        """Test that encryption errors are logged"""
        platform = self.get_test_platform()
        
        # Force encryption error by corrupting cipher
        with patch('models.PlatformConnection._get_cipher') as mock_get_cipher:
            mock_cipher = Mock()
            mock_cipher.encrypt.side_effect = Exception("Test encryption error")
            mock_get_cipher.return_value = mock_cipher
            
            with self.assertRaises(Exception):
                platform.access_token = 'test_token'
            
            # Should log error
            mock_logging.error.assert_called()
    
    @patch('models.logging')
    def test_decryption_error_logging(self, mock_logging):
        """Test that decryption errors are logged"""
        platform = self.get_test_platform()
        
        # Set encrypted data manually to invalid value
        platform._access_token = 'invalid_encrypted_data'
        
        # Try to decrypt
        decrypted = platform.access_token
        
        # Should log error and return None
        mock_logging.error.assert_called()
        self.assertIsNone(decrypted)


class TestEncryptionPerformance(PlatformTestCase):
    """Test encryption performance characteristics"""
    
    def test_encryption_performance(self):
        """Test encryption performance with multiple operations"""
        platform = self.get_test_platform()
        
        # Perform multiple encryption operations
        tokens = [f'test_token_{i}' for i in range(100)]
        
        for token in tokens:
            platform.access_token = token
            self.session.commit()
            
            # Verify each encryption/decryption works
            self.assertEqual(platform.access_token, token)
    
    def test_concurrent_encryption(self):
        """Test encryption with multiple platforms"""
        user = self.get_test_user()
        platforms = []
        
        # Create multiple platforms
        for i in range(10):
            platform = PlatformConnection(
                user_id=user.id,
                name=f'Platform {i}',
                platform_type='pixelfed',
                instance_url=f'https://platform{i}.test',
                username=f'user{i}',
                access_token=f'token_{i}'
            )
            platforms.append(platform)
            self.session.add(platform)
        
        self.session.commit()
        
        # Verify all platforms have correct tokens
        for i, platform in enumerate(platforms):
            self.assertEqual(platform.access_token, f'token_{i}')


if __name__ == '__main__':
    unittest.main()