# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Tests for admin user service"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from admin.services.user_service import UserService
from models import UserRole

class TestUserService(unittest.TestCase):
    """Test admin user service functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        self.user_service = UserService(self.mock_db_manager)
    
    def test_get_all_users(self):
        """Test getting all users"""
        # Mock users
        mock_users = [Mock(), Mock()]
        self.mock_session.query.return_value.all.return_value = mock_users
        
        users = self.user_service.get_all_users()
        
        self.assertEqual(users, mock_users)
        self.mock_session.close.assert_called_once()
    
    def test_get_admin_count(self):
        """Test getting admin user count"""
        self.mock_session.query.return_value.filter_by.return_value.count.return_value = 2
        
        count = self.user_service.get_admin_count()
        
        self.assertEqual(count, 2)
        self.mock_session.close.assert_called_once()
    
    def test_create_user_success(self):
        """Test successful user creation"""
        # Mock no existing user
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock user creation
        mock_user = Mock()
        mock_user.id = 1
        
        with patch('admin.services.user_service.User', return_value=mock_user):
            user = self.user_service.create_user(
                username="testuser",
                email="test@test.com",
                password="password123",
                role=UserRole.REVIEWER
            )
            
            self.assertEqual(user, mock_user)
            self.mock_session.add.assert_called_once_with(mock_user)
            self.mock_session.commit.assert_called_once()
    
    def test_create_user_duplicate_username(self):
        """Test user creation with duplicate username"""
        # Mock existing user
        existing_user = Mock()
        existing_user.username = "testuser"
        self.mock_session.query.return_value.filter.return_value.first.return_value = existing_user
        
        with self.assertRaises(ValueError) as context:
            self.user_service.create_user(
                username="testuser",
                email="test@test.com",
                password="password123",
                role=UserRole.REVIEWER
            )
        
        self.assertIn("Username testuser already exists", str(context.exception))
    
    def test_update_user_success(self):
        """Test successful user update"""
        # Mock existing user
        mock_user = Mock()
        mock_user.id = 1
        self.mock_session.query.return_value.get.return_value = mock_user
        
        # Mock no conflicts
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        success = self.user_service.update_user(
            user_id=1,
            username="newusername",
            email="new@test.com",
            role=UserRole.ADMIN,
            is_active=True
        )
        
        self.assertTrue(success)
        self.assertEqual(mock_user.username, "newusername")
        self.assertEqual(mock_user.email, "new@test.com")
        self.assertEqual(mock_user.role, UserRole.ADMIN)
        self.assertTrue(mock_user.is_active)
        self.mock_session.commit.assert_called_once()
    
    def test_update_user_not_found(self):
        """Test user update when user not found"""
        self.mock_session.query.return_value.get.return_value = None
        
        success = self.user_service.update_user(
            user_id=999,
            username="newusername",
            email="new@test.com",
            role=UserRole.ADMIN,
            is_active=True
        )
        
        self.assertFalse(success)
    
    def test_delete_user_success(self):
        """Test successful user deletion"""
        mock_user = Mock()
        self.mock_session.query.return_value.get.return_value = mock_user
        
        success = self.user_service.delete_user(1)
        
        self.assertTrue(success)
        self.mock_session.delete.assert_called_once_with(mock_user)
        self.mock_session.commit.assert_called_once()
    
    def test_delete_user_not_found(self):
        """Test user deletion when user not found"""
        self.mock_session.query.return_value.get.return_value = None
        
        success = self.user_service.delete_user(999)
        
        self.assertFalse(success)
        self.mock_session.delete.assert_not_called()

if __name__ == '__main__':
    unittest.main()