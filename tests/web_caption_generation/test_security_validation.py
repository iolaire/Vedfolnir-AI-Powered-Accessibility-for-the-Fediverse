# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security tests for caption generation system
"""

import unittest
from unittest.mock import Mock, patch
import uuid

from caption_security import CaptionSecurityManager
from models import User, UserRole, PlatformConnection
from app.core.database.core.database_manager import DatabaseManager

class TestCaptionGenerationSecurity(unittest.TestCase):
    """Security tests for caption generation system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.security_manager = CaptionSecurityManager(self.mock_db_manager)
        
        # Test data
        self.test_user_id = 1
        self.test_platform_id = 1
        self.test_task_id = str(uuid.uuid4())
        
        # Mock user
        self.mock_user = Mock(spec=User)
        self.mock_user.id = self.test_user_id
        self.mock_user.role = UserRole.USER
        self.mock_user.is_active = True
        
        # Mock platform
        self.mock_platform = Mock(spec=PlatformConnection)
        self.mock_platform.id = self.test_platform_id
        self.mock_platform.user_id = self.test_user_id
        self.mock_platform.is_active = True
    
    def test_secure_task_id_generation(self):
        """Test secure task ID generation"""
        task_id = self.security_manager.generate_secure_task_id()
        
        # Verify format
        self.assertIsInstance(task_id, str)
        self.assertEqual(len(task_id), 36)  # UUID4 format
        
        # Verify uniqueness
        task_id2 = self.security_manager.generate_secure_task_id()
        self.assertNotEqual(task_id, task_id2)
    
    def test_validate_task_id_format(self):
        """Test task ID format validation"""
        # Valid UUID
        valid_id = str(uuid.uuid4())
        self.assertTrue(self.security_manager.validate_task_id_format(valid_id))
        
        # Invalid formats
        self.assertFalse(self.security_manager.validate_task_id_format("invalid"))
        self.assertFalse(self.security_manager.validate_task_id_format(""))
        self.assertFalse(self.security_manager.validate_task_id_format(None))
        self.assertFalse(self.security_manager.validate_task_id_format("123"))
    
    def test_user_authorization_success(self):
        """Test successful user authorization"""
        # Mock user found and active
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_user
        
        result = self.security_manager.authorize_user(self.test_user_id)
        
        self.assertTrue(result)
    
    def test_user_authorization_user_not_found(self):
        """Test user authorization when user not found"""
        # Mock user not found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.security_manager.authorize_user(self.test_user_id)
        
        self.assertFalse(result)
    
    def test_user_authorization_inactive_user(self):
        """Test user authorization for inactive user"""
        # Mock inactive user
        self.mock_user.is_active = False
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_user
        
        result = self.security_manager.authorize_user(self.test_user_id)
        
        self.assertFalse(result)
    
    def test_platform_access_validation_success(self):
        """Test successful platform access validation"""
        # Mock platform found and accessible
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_platform
        
        result = self.security_manager.validate_platform_access(
            self.test_user_id, 
            self.test_platform_id
        )
        
        self.assertTrue(result)
    
    def test_platform_access_validation_platform_not_found(self):
        """Test platform access validation when platform not found"""
        # Mock platform not found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.security_manager.validate_platform_access(
            self.test_user_id, 
            self.test_platform_id
        )
        
        self.assertFalse(result)
    
    def test_platform_access_validation_wrong_user(self):
        """Test platform access validation for wrong user"""
        # Mock platform belonging to different user
        self.mock_platform.user_id = 999
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_platform
        
        result = self.security_manager.validate_platform_access(
            self.test_user_id, 
            self.test_platform_id
        )
        
        self.assertFalse(result)
    
    def test_platform_access_validation_inactive_platform(self):
        """Test platform access validation for inactive platform"""
        # Mock inactive platform
        self.mock_platform.is_active = False
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_platform
        
        result = self.security_manager.validate_platform_access(
            self.test_user_id, 
            self.test_platform_id
        )
        
        self.assertFalse(result)
    
    def test_input_sanitization(self):
        """Test input sanitization"""
        # Test various inputs
        test_cases = [
            ("normal text", "normal text"),
            ("<script>alert('xss')</script>", "&lt;script&gt;alert('xss')&lt;/script&gt;"),
            ("text with & ampersand", "text with &amp; ampersand"),
            ("", ""),
            (None, "")
        ]
        
        for input_text, expected in test_cases:
            result = self.security_manager.sanitize_input(input_text)
            self.assertEqual(result, expected)
    
    def test_rate_limiting_check(self):
        """Test rate limiting functionality"""
        # Mock rate limiter
        with patch('caption_security.RateLimiter') as mock_rate_limiter_class:
            mock_rate_limiter = Mock()
            mock_rate_limiter_class.return_value = mock_rate_limiter
            
            # Test allowed request
            mock_rate_limiter.is_allowed.return_value = True
            result = self.security_manager.check_rate_limit(self.test_user_id, "caption_generation")
            self.assertTrue(result)
            
            # Test rate limited request
            mock_rate_limiter.is_allowed.return_value = False
            result = self.security_manager.check_rate_limit(self.test_user_id, "caption_generation")
            self.assertFalse(result)
    
    def test_admin_authorization(self):
        """Test admin authorization"""
        # Mock admin user
        self.mock_user.role = UserRole.ADMIN
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_user
        
        result = self.security_manager.authorize_admin(self.test_user_id)
        
        self.assertTrue(result)
    
    def test_admin_authorization_non_admin(self):
        """Test admin authorization for non-admin user"""
        # Mock regular user
        self.mock_user.role = UserRole.USER
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_user
        
        result = self.security_manager.authorize_admin(self.test_user_id)
        
        self.assertFalse(result)
    
    def test_task_ownership_validation(self):
        """Test task ownership validation"""
        # Mock task
        mock_task = Mock()
        mock_task.user_id = self.test_user_id
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        result = self.security_manager.validate_task_ownership(
            self.test_task_id, 
            self.test_user_id
        )
        
        self.assertTrue(result)
    
    def test_task_ownership_validation_wrong_user(self):
        """Test task ownership validation for wrong user"""
        # Mock task belonging to different user
        mock_task = Mock()
        mock_task.user_id = 999
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        result = self.security_manager.validate_task_ownership(
            self.test_task_id, 
            self.test_user_id
        )
        
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()