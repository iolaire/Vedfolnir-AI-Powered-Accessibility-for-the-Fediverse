# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance tests for user management operations
"""

import unittest
import time
import asyncio
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from database import DatabaseManager
from models import User, UserRole, UserAuditLog
from services.user_management_service import (
    UserRegistrationService, UserAuthenticationService, 
    PasswordManagementService, UserProfileService
)
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user


class TestUserManagementPerformance(unittest.TestCase):
    """Test performance aspects of user management operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        self.test_users_to_cleanup = []
    
    def tearDown(self):
        """Clean up test fixtures"""
        for user_helper in self.test_users_to_cleanup:
            try:
                cleanup_test_user(user_helper)
            except Exception:
                pass
    
    @patch('services.email_service.email_service.send_verification_email')
    def test_bulk_user_registration_performance(self, mock_send_email):
        """Test performance of bulk user registration"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Test registering multiple users
            num_users = 50
            start_time = time.time()
            
            successful_registrations = 0
            for i in range(num_users):
                success, message, user = registration_service.register_user(
                    username=f"perftest_user_{i}",
                    email=f"perftest{i}@test.com",
                    password="testpass123",
                    role=UserRole.VIEWER,
                    require_email_verification=False  # Skip email for performance
                )
                
                if success:
                    successful_registrations += 1
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Performance assertions
            self.assertEqual(successful_registrations, num_users)
            self.assertLess(total_time, 10.0)  # Should complete within 10 seconds
            
            # Calculate average time per registration
            avg_time_per_registration = total_time / num_users
            self.assertLess(avg_time_per_registration, 0.2)  # Less than 200ms per registration
            
            print(f"Registered {num_users} users in {total_time:.2f} seconds")
            print(f"Average time per registration: {avg_time_per_registration:.3f} seconds")
    
    def test_concurrent_authentication_performance(self):
        """Test performance of concurrent authentication requests"""
        with self.db_manager.get_session() as db_session:
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Create test users for concurrent authentication
            test_users = []
            for i in range(10):
                user, helper = create_test_user_with_platforms(
                    self.db_manager,
                    username=f"concurrent_user_{i}",
                    role=UserRole.VIEWER
                )
                test_users.append((user, helper))
                self.test_users_to_cleanup.append(helper)
            
            def authenticate_user(user_data):
                """Helper function for concurrent authentication"""
                user, _ = user_data
                with self.db_manager.get_session() as session:
                    auth_svc = UserAuthenticationService(session)
                    start = time.time()
                    success, message, auth_user = auth_svc.authenticate_user(
                        username_or_email=user.username,
                        password="test_password_123",
                        ip_address="127.0.0.1"
                    )
                    end = time.time()
                    return success, end - start
            
            # Test concurrent authentication
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(authenticate_user, user_data) for user_data in test_users]
                results = [future.result() for future in as_completed(futures)]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Performance assertions
            successful_auths = sum(1 for success, _ in results if success)
            self.assertEqual(successful_auths, len(test_users))
            
            # All authentications should complete quickly
            auth_times = [auth_time for _, auth_time in results]
            max_auth_time = max(auth_times)
            avg_auth_time = sum(auth_times) / len(auth_times)
            
            self.assertLess(max_auth_time, 1.0)  # No single auth should take more than 1 second
            self.assertLess(avg_auth_time, 0.5)  # Average should be under 500ms
            self.assertLess(total_time, 5.0)     # Total concurrent time should be under 5 seconds
            
            print(f"Concurrent authentication of {len(test_users)} users completed in {total_time:.2f} seconds")
            print(f"Average authentication time: {avg_auth_time:.3f} seconds")
            print(f"Maximum authentication time: {max_auth_time:.3f} seconds")
    
    def test_password_hashing_performance(self):
        """Test performance of password hashing operations"""
        with self.db_manager.get_session() as db_session:
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="hash_perf_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Test password hashing performance
            passwords = [f"testpassword{i}" for i in range(100)]
            
            start_time = time.time()
            for password in passwords:
                test_user.set_password(password)
            end_time = time.time()
            
            hashing_time = end_time - start_time
            avg_hash_time = hashing_time / len(passwords)
            
            # Performance assertions
            self.assertLess(avg_hash_time, 0.1)  # Less than 100ms per hash on average
            self.assertLess(hashing_time, 10.0)  # Total time under 10 seconds
            
            # Test password verification performance
            start_time = time.time()
            for password in passwords[-10:]:  # Test last 10 passwords
                test_user.check_password(password)
            end_time = time.time()
            
            verification_time = end_time - start_time
            avg_verification_time = verification_time / 10
            
            self.assertLess(avg_verification_time, 0.05)  # Less than 50ms per verification
            
            print(f"Password hashing: {avg_hash_time:.4f} seconds per hash")
            print(f"Password verification: {avg_verification_time:.4f} seconds per verification")
    
    def test_database_query_performance(self):
        """Test performance of database queries for user operations"""
        with self.db_manager.get_session() as db_session:
            # Create multiple test users
            test_users = []
            for i in range(100):
                user, helper = create_test_user_with_platforms(
                    self.db_manager,
                    username=f"query_perf_user_{i}",
                    role=UserRole.VIEWER if i % 2 == 0 else UserRole.ADMIN
                )
                test_users.append((user, helper))
                self.test_users_to_cleanup.append(helper)
                
                # Create some audit log entries
                UserAuditLog.log_action(
                    db_session,
                    action="test_action",
                    user_id=user.id,
                    details=f"Test action for user {i}"
                )
            
            # Test user lookup by username performance
            start_time = time.time()
            for i in range(50):  # Test 50 lookups
                user = db_session.query(User).filter_by(username=f"query_perf_user_{i}").first()
                self.assertIsNotNone(user)
            end_time = time.time()
            
            lookup_time = end_time - start_time
            avg_lookup_time = lookup_time / 50
            
            self.assertLess(avg_lookup_time, 0.01)  # Less than 10ms per lookup
            
            # Test user lookup by email performance
            start_time = time.time()
            for i in range(50):
                user = db_session.query(User).filter_by(email=f"query_perf_user_{i}@test.com").first()
                self.assertIsNotNone(user)
            end_time = time.time()
            
            email_lookup_time = end_time - start_time
            avg_email_lookup_time = email_lookup_time / 50
            
            self.assertLess(avg_email_lookup_time, 0.01)  # Less than 10ms per email lookup
            
            # Test bulk user queries
            start_time = time.time()
            all_users = db_session.query(User).all()
            end_time = time.time()
            
            bulk_query_time = end_time - start_time
            self.assertGreaterEqual(len(all_users), 100)
            self.assertLess(bulk_query_time, 1.0)  # Less than 1 second for bulk query
            
            # Test audit log queries
            start_time = time.time()
            for user, _ in test_users[:10]:  # Test 10 audit queries
                audit_logs = db_session.query(UserAuditLog).filter_by(user_id=user.id).all()
                self.assertGreater(len(audit_logs), 0)
            end_time = time.time()
            
            audit_query_time = end_time - start_time
            avg_audit_query_time = audit_query_time / 10
            
            self.assertLess(avg_audit_query_time, 0.05)  # Less than 50ms per audit query
            
            print(f"Username lookup: {avg_lookup_time:.4f} seconds per query")
            print(f"Email lookup: {avg_email_lookup_time:.4f} seconds per query")
            print(f"Bulk user query: {bulk_query_time:.4f} seconds for {len(all_users)} users")
            print(f"Audit log query: {avg_audit_query_time:.4f} seconds per query")
    
    @patch('services.email_service.email_service.send_password_reset_email')
    def test_password_reset_performance(self, mock_send_email):
        """Test performance of password reset operations"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test users
            test_users = []
            for i in range(20):
                user, helper = create_test_user_with_platforms(
                    self.db_manager,
                    username=f"reset_perf_user_{i}",
                    role=UserRole.VIEWER
                )
                test_users.append((user, helper))
                self.test_users_to_cleanup.append(helper)
            
            # Test password reset initiation performance
            start_time = time.time()
            for user, _ in test_users:
                success, message = asyncio.run(password_service.initiate_password_reset(
                    email=user.email,
                    ip_address="127.0.0.1"
                ))
                self.assertTrue(success)
            end_time = time.time()
            
            reset_initiation_time = end_time - start_time
            avg_reset_time = reset_initiation_time / len(test_users)
            
            self.assertLess(avg_reset_time, 0.1)  # Less than 100ms per reset initiation
            
            # Test token verification performance
            start_time = time.time()
            for user, _ in test_users:
                db_session.refresh(user)
                if user.password_reset_token:
                    success, message, verified_user = password_service.verify_reset_token(
                        user.password_reset_token
                    )
                    self.assertTrue(success)
            end_time = time.time()
            
            verification_time = end_time - start_time
            avg_verification_time = verification_time / len(test_users)
            
            self.assertLess(avg_verification_time, 0.05)  # Less than 50ms per verification
            
            print(f"Password reset initiation: {avg_reset_time:.4f} seconds per request")
            print(f"Token verification: {avg_verification_time:.4f} seconds per verification")
    
    def test_profile_update_performance(self):
        """Test performance of profile update operations"""
        with self.db_manager.get_session() as db_session:
            profile_service = UserProfileService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test users
            test_users = []
            for i in range(50):
                user, helper = create_test_user_with_platforms(
                    self.db_manager,
                    username=f"profile_perf_user_{i}",
                    role=UserRole.VIEWER
                )
                test_users.append((user, helper))
                self.test_users_to_cleanup.append(helper)
            
            # Test profile updates
            start_time = time.time()
            for i, (user, _) in enumerate(test_users):
                profile_data = {
                    'first_name': f'Updated{i}',
                    'last_name': f'User{i}'
                }
                
                success, message, updated_user = profile_service.update_profile(
                    user_id=user.id,
                    profile_data=profile_data,
                    ip_address="127.0.0.1"
                )
                self.assertTrue(success)
            end_time = time.time()
            
            update_time = end_time - start_time
            avg_update_time = update_time / len(test_users)
            
            self.assertLess(avg_update_time, 0.1)  # Less than 100ms per update
            self.assertLess(update_time, 5.0)     # Total time under 5 seconds
            
            print(f"Profile update: {avg_update_time:.4f} seconds per update")
    
    def test_audit_log_performance(self):
        """Test performance of audit logging operations"""
        with self.db_manager.get_session() as db_session:
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="audit_perf_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Test bulk audit log creation
            num_logs = 1000
            start_time = time.time()
            
            for i in range(num_logs):
                UserAuditLog.log_action(
                    db_session,
                    action=f"test_action_{i % 10}",  # Vary actions
                    user_id=test_user.id,
                    details=f"Performance test action {i}",
                    ip_address="127.0.0.1"
                )
            
            db_session.commit()
            end_time = time.time()
            
            logging_time = end_time - start_time
            avg_log_time = logging_time / num_logs
            
            self.assertLess(avg_log_time, 0.01)  # Less than 10ms per log entry
            self.assertLess(logging_time, 10.0)  # Total time under 10 seconds
            
            # Test audit log retrieval performance
            start_time = time.time()
            audit_logs = db_session.query(UserAuditLog).filter_by(user_id=test_user.id).all()
            end_time = time.time()
            
            retrieval_time = end_time - start_time
            
            self.assertEqual(len(audit_logs), num_logs)
            self.assertLess(retrieval_time, 1.0)  # Less than 1 second to retrieve all logs
            
            print(f"Audit log creation: {avg_log_time:.5f} seconds per log")
            print(f"Audit log retrieval: {retrieval_time:.4f} seconds for {num_logs} logs")


if __name__ == '__main__':
    unittest.main()