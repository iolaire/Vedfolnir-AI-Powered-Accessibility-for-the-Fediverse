# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for admin user management workflows
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from config import Config
from database import DatabaseManager
from models import User, UserRole, UserAuditLog
from services.user_management_service import UserRegistrationService, UserAuthenticationService, PasswordManagementService
from admin.services.user_service import UserService
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures


class TestAdminUserManagement(MySQLIntegrationTestBase):
    """Test admin user management integration workflows"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = self.get_database_manager()
        
        # Create admin user for testing
        self.admin_user, self.admin_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_admin",
            role=UserRole.ADMIN
        )
        
        self.test_users_to_cleanup = [self.admin_helper]
    
    def tearDown(self):
        """Clean up test fixtures"""
        for user_helper in self.test_users_to_cleanup:
            try:
                cleanup_test_user(user_helper)
            except Exception:
                pass
    
    @patch('services.email_service.email_service.send_account_created_email')
    def test_admin_create_user_workflow(self, mock_send_email):
        """Test complete admin user creation workflow"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            user_service = UserService(db_session)
            
            # Admin creates new user
            success, message, new_user = asyncio.run(user_service.create_user(
                username="admin_created_user",
                email="admincreated@test.com",
                password="temppass123",
                role=UserRole.VIEWER,
                first_name="Admin",
                last_name="Created",
                admin_user_id=self.admin_user.id,
                send_email=True,
                bypass_email_verification=True,
                ip_address="127.0.0.1"
            ))
            
            self.assertTrue(success)
            self.assertIn("created successfully", message)
            self.assertIsNotNone(new_user)
            self.assertEqual(new_user.username, "admin_created_user")
            self.assertEqual(new_user.email, "admincreated@test.com")
            self.assertEqual(new_user.role, UserRole.VIEWER)
            self.assertTrue(new_user.email_verified)  # Should be verified due to bypass
            self.assertTrue(new_user.is_active)
            
            # Verify email was sent
            mock_send_email.assert_called_once()
            
            # Verify audit log was created
            audit_logs = db_session.query(UserAuditLog).filter_by(
                user_id=new_user.id,
                action="admin_user_created"
            ).all()
            self.assertEqual(len(audit_logs), 1)
            self.assertEqual(audit_logs[0].admin_user_id, self.admin_user.id)
            
            # Test that new user can login immediately
            auth_service = UserAuthenticationService(db_session)
            auth_success, auth_message, auth_user = auth_service.authenticate_user(
                username_or_email="admin_created_user",
                password="temppass123",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(auth_success)
            self.assertEqual(auth_message, "Login successful")
            self.assertIsNotNone(auth_user)
    
    def test_admin_edit_user_workflow(self):
        """Test admin user editing workflow"""
        with self.db_manager.get_session() as db_session:
            user_service = UserService(db_session)
            
            # Create a user to edit
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="user_to_edit",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Admin edits user
            update_data = {
                'first_name': 'Updated',
                'last_name': 'Name',
                'role': UserRole.ADMIN,
                'is_active': True,
                'email_verified': True
            }
            
            success, message, updated_user = user_service.update_user(
                user_id=test_user.id,
                update_data=update_data,
                admin_user_id=self.admin_user.id,
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            self.assertIn("updated successfully", message)
            self.assertIsNotNone(updated_user)
            self.assertEqual(updated_user.first_name, "Updated")
            self.assertEqual(updated_user.last_name, "Name")
            self.assertEqual(updated_user.role, UserRole.ADMIN)
            
            # Verify audit log was created
            audit_logs = db_session.query(UserAuditLog).filter_by(
                user_id=test_user.id,
                action="admin_user_updated"
            ).all()
            self.assertEqual(len(audit_logs), 1)
            self.assertEqual(audit_logs[0].admin_user_id, self.admin_user.id)
    
    @patch('services.email_service.email_service.send_notification_email')
    def test_admin_password_reset_workflow(self, mock_send_email):
        """Test admin password reset workflow"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            user_service = UserService(db_session)
            auth_service = UserAuthenticationService(db_session)
            
            # Create a user whose password will be reset
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="password_reset_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Store original password hash
            original_password_hash = test_user.password_hash
            
            # Admin resets user password
            success, message = asyncio.run(user_service.reset_user_password(
                user_id=test_user.id,
                new_password="newadminpass123",
                admin_user_id=self.admin_user.id,
                send_notification=True,
                ip_address="127.0.0.1"
            ))
            
            self.assertTrue(success)
            self.assertIn("reset successfully", message)
            
            # Verify password was changed
            db_session.refresh(test_user)
            self.assertNotEqual(test_user.password_hash, original_password_hash)
            self.assertTrue(test_user.check_password("newadminpass123"))
            
            # Verify failed login attempts were reset
            self.assertEqual(test_user.failed_login_attempts, 0)
            self.assertFalse(test_user.account_locked)
            
            # Verify notification email was sent
            mock_send_email.assert_called_once()
            
            # Verify audit log was created
            audit_logs = db_session.query(UserAuditLog).filter_by(
                user_id=test_user.id,
                action="admin_password_reset"
            ).all()
            self.assertEqual(len(audit_logs), 1)
            self.assertEqual(audit_logs[0].admin_user_id, self.admin_user.id)
            
            # Test that user can login with new password
            auth_success, auth_message, auth_user = auth_service.authenticate_user(
                username_or_email="password_reset_user",
                password="newadminpass123",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(auth_success)
            self.assertEqual(auth_message, "Login successful")
    
    def test_admin_unlock_user_account(self):
        """Test admin unlocking user account"""
        with self.db_manager.get_session() as db_session:
            user_service = UserService(db_session)
            auth_service = UserAuthenticationService(db_session)
            
            # Create a user and lock their account
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="locked_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Lock the account
            test_user.account_locked = True
            test_user.failed_login_attempts = 5
            test_user.last_failed_login = datetime.utcnow()
            db_session.commit()
            
            # Verify user cannot login
            auth_success, auth_message, auth_user = auth_service.authenticate_user(
                username_or_email="locked_user",
                password="test_password_123",
                ip_address="127.0.0.1"
            )
            self.assertFalse(auth_success)
            self.assertIn("locked", auth_message)
            
            # Admin unlocks the account
            success, message = auth_service.unlock_user_account(
                user_id=test_user.id,
                admin_user_id=self.admin_user.id,
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            self.assertIn("unlocked successfully", message)
            
            # Verify account is unlocked
            db_session.refresh(test_user)
            self.assertFalse(test_user.account_locked)
            self.assertEqual(test_user.failed_login_attempts, 0)
            self.assertIsNone(test_user.last_failed_login)
            
            # Verify user can now login
            auth_success, auth_message, auth_user = auth_service.authenticate_user(
                username_or_email="locked_user",
                password="test_password_123",
                ip_address="127.0.0.1"
            )
            self.assertTrue(auth_success)
            self.assertEqual(auth_message, "Login successful")
            
            # Verify audit log was created
            audit_logs = db_session.query(UserAuditLog).filter_by(
                user_id=test_user.id,
                action="account_unlocked"
            ).all()
            self.assertEqual(len(audit_logs), 1)
            self.assertEqual(audit_logs[0].admin_user_id, self.admin_user.id)
    
    def test_admin_delete_user_workflow(self):
        """Test admin user deletion workflow"""
        with self.db_manager.get_session() as db_session:
            user_service = UserService(db_session)
            
            # Create a user to delete
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="user_to_delete",
                role=UserRole.VIEWER
            )
            user_id = test_user.id
            
            # Admin deletes user
            success, message = asyncio.run(user_service.delete_user(
                user_id=user_id,
                admin_user_id=self.admin_user.id,
                ip_address="127.0.0.1"
            ))
            
            self.assertTrue(success)
            self.assertIn("deleted successfully", message)
            
            # Verify user was deleted from database
            deleted_user = db_session.query(User).filter_by(id=user_id).first()
            self.assertIsNone(deleted_user)
            
            # Verify audit log was created (should still exist even after user deletion)
            audit_logs = db_session.query(UserAuditLog).filter_by(
                user_id=user_id,
                action="admin_user_deleted"
            ).all()
            self.assertEqual(len(audit_logs), 1)
            self.assertEqual(audit_logs[0].admin_user_id, self.admin_user.id)
    
    def test_admin_cannot_delete_last_admin(self):
        """Test that admin cannot delete the last admin user"""
        with self.db_manager.get_session() as db_session:
            user_service = UserService(db_session)
            
            # Attempt to delete the only admin user
            success, message = asyncio.run(user_service.delete_user(
                user_id=self.admin_user.id,
                admin_user_id=self.admin_user.id,
                ip_address="127.0.0.1"
            ))
            
            self.assertFalse(success)
            self.assertIn("Cannot delete the last admin user", message)
            
            # Verify admin user still exists
            admin_still_exists = db_session.query(User).filter_by(id=self.admin_user.id).first()
            self.assertIsNotNone(admin_still_exists)
    
    def test_admin_get_user_list(self):
        """Test admin getting user list with filtering and pagination"""
        with self.db_manager.get_session() as db_session:
            user_service = UserService(db_session)
            
            # Create additional test users
            test_users = []
            for i in range(5):
                user, helper = create_test_user_with_platforms(
                    self.db_manager,
                    username=f"listtest{i}",
                    role=UserRole.VIEWER if i % 2 == 0 else UserRole.ADMIN
                )
                test_users.append((user, helper))
                self.test_users_to_cleanup.append(helper)
            
            # Get all users
            users, total_count = user_service.get_users(
                page=1,
                per_page=10,
                admin_user_id=self.admin_user.id
            )
            
            self.assertGreaterEqual(len(users), 6)  # At least our test users + admin
            self.assertGreaterEqual(total_count, 6)
            
            # Get users with role filter
            admin_users, admin_count = user_service.get_users(
                page=1,
                per_page=10,
                role_filter=UserRole.ADMIN,
                admin_user_id=self.admin_user.id
            )
            
            self.assertGreaterEqual(len(admin_users), 3)  # Original admin + 2 test admins
            for user in admin_users:
                self.assertEqual(user.role, UserRole.ADMIN)
            
            # Get users with search filter
            search_users, search_count = user_service.get_users(
                page=1,
                per_page=10,
                search_query="listtest",
                admin_user_id=self.admin_user.id
            )
            
            self.assertEqual(len(search_users), 5)  # All our test users
            for user in search_users:
                self.assertIn("listtest", user.username)
    
    def test_admin_session_preservation(self):
        """Test that admin session is preserved during user management operations"""
        with self.db_manager.get_session() as db_session:
            user_service = UserService(db_session)
            auth_service = UserAuthenticationService(db_session)
            
            # Create admin session (simulated)
            admin_login_success, admin_message, admin_user = auth_service.authenticate_user(
                username_or_email=self.admin_user.username,
                password="test_password_123",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(admin_login_success)
            
            # Perform multiple admin operations
            operations = [
                # Create user
                lambda: asyncio.run(user_service.create_user(
                    username="sessiontest1",
                    email="sessiontest1@test.com",
                    password="temppass123",
                    role=UserRole.VIEWER,
                    admin_user_id=self.admin_user.id,
                    ip_address="127.0.0.1"
                )),
                # Create another user
                lambda: asyncio.run(user_service.create_user(
                    username="sessiontest2",
                    email="sessiontest2@test.com",
                    password="temppass123",
                    role=UserRole.VIEWER,
                    admin_user_id=self.admin_user.id,
                    ip_address="127.0.0.1"
                ))
            ]
            
            # Execute operations and verify admin user remains accessible
            for operation in operations:
                success, message, created_user = operation()
                self.assertTrue(success)
                
                # Verify admin user is still accessible and hasn't been detached
                db_session.refresh(self.admin_user)
                self.assertEqual(self.admin_user.role, UserRole.ADMIN)
                self.assertTrue(self.admin_user.is_active)
    
    def test_admin_bulk_operations(self):
        """Test admin bulk operations on multiple users"""
        with self.db_manager.get_session() as db_session:
            user_service = UserService(db_session)
            
            # Create multiple test users
            test_users = []
            for i in range(3):
                user, helper = create_test_user_with_platforms(
                    self.db_manager,
                    username=f"bulktest{i}",
                    role=UserRole.VIEWER
                )
                test_users.append((user, helper))
                self.test_users_to_cleanup.append(helper)
            
            user_ids = [user.id for user, _ in test_users]
            
            # Bulk activate users
            success, message, results = user_service.bulk_update_users(
                user_ids=user_ids,
                update_data={'is_active': True},
                admin_user_id=self.admin_user.id,
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            self.assertIn("updated successfully", message)
            self.assertEqual(len(results), 3)
            
            # Verify all users were updated
            for user_id in user_ids:
                user = db_session.query(User).filter_by(id=user_id).first()
                self.assertTrue(user.is_active)
            
            # Verify audit logs were created for each user
            for user_id in user_ids:
                audit_logs = db_session.query(UserAuditLog).filter_by(
                    user_id=user_id,
                    action="admin_bulk_update"
                ).all()
                self.assertEqual(len(audit_logs), 1)
                self.assertEqual(audit_logs[0].admin_user_id, self.admin_user.id)

if __name__ == '__main__':
    unittest.main()