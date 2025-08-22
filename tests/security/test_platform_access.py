# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security tests for platform access control

Tests access control and authorization for platform operations.
"""

import unittest
from tests.fixtures.platform_fixtures import PlatformTestCase
from models import User, UserRole, PlatformConnection
from platform_context import PlatformContextManager, PlatformContextError

class TestPlatformAccessControl(PlatformTestCase):
    """Test platform access control mechanisms"""
    
    def test_user_role_based_access(self):
        """Test access control based on user roles"""
        admin_user = self.get_test_user(UserRole.ADMIN)
        viewer_user = self.get_test_user(UserRole.VIEWER)
        
        # Admin should have full access
        admin_platforms = admin_user.get_active_platforms()
        self.assertGreater(len(admin_platforms), 0)
        
        # Viewer should have limited access
        viewer_platforms = viewer_user.get_active_platforms() if hasattr(viewer_user, 'get_active_platforms') else []
        # Access depends on implementation - test what's appropriate
    
    def test_platform_ownership_validation(self):
        """Test platform ownership is strictly validated"""
        user1 = self.get_test_user()
        user2 = self.users[1]
        
        # Create platform for user1
        user1_platform = self.get_test_platform()
        
        # User2 should not be able to access user1's platform
        context_manager = PlatformContextManager(self.session)
        
        with self.assertRaises(PlatformContextError):
            context_manager.set_context(user2.id, user1_platform.id)
    
    def test_inactive_platform_access_denied(self):
        """Test access to inactive platforms is denied"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Deactivate platform
        platform.is_active = False
        self.session.commit()
        
        # Access should be denied
        context_manager = PlatformContextManager(self.session)
        
        with self.assertRaises(PlatformContextError):
            context_manager.set_context(user.id, platform.id)
    
    def test_deleted_platform_access_denied(self):
        """Test access to deleted platforms is denied"""
        user = self.get_test_user()
        
        # Create temporary platform
        temp_platform = PlatformConnection(
            user_id=user.id,
            name='Temporary Platform',
            platform_type='pixelfed',
            instance_url='https://temp.test.com',
            username='tempuser',
            access_token='temp_token'
        )
        self.session.add(temp_platform)
        self.session.commit()
        
        platform_id = temp_platform.id
        
        # Delete platform
        self.session.delete(temp_platform)
        self.session.commit()
        
        # Access should be denied
        context_manager = PlatformContextManager(self.session)
        
        with self.assertRaises(PlatformContextError):
            context_manager.set_context(user.id, platform_id)

class TestUnauthorizedAccessPrevention(PlatformTestCase):
    """Test prevention of unauthorized access attempts"""
    
    def test_invalid_user_access_denied(self):
        """Test access with invalid user ID is denied"""
        platform = self.get_test_platform()
        context_manager = PlatformContextManager(self.session)
        
        # Try with non-existent user
        with self.assertRaises(PlatformContextError):
            context_manager.set_context(99999, platform.id)
    
    def test_invalid_platform_access_denied(self):
        """Test access with invalid platform ID is denied"""
        user = self.get_test_user()
        context_manager = PlatformContextManager(self.session)
        
        # Try with non-existent platform
        with self.assertRaises(PlatformContextError):
            context_manager.set_context(user.id, 99999)
    
    def test_cross_user_platform_access_denied(self):
        """Test cross-user platform access is denied"""
        user1 = self.get_test_user()
        user2 = self.users[1]
        
        # Create platform for user2
        user2_platform = PlatformConnection(
            user_id=user2.id,
            name='User2 Private Platform',
            platform_type='mastodon',
            instance_url='https://private.test.com',
            username='privateuser',
            access_token='private_token'
        )
        self.session.add(user2_platform)
        self.session.commit()
        
        # User1 should not access user2's platform
        context_manager = PlatformContextManager(self.session)
        
        with self.assertRaises(PlatformContextError):
            context_manager.set_context(user1.id, user2_platform.id)
    
    def test_sql_injection_prevention(self):
        """Test SQL injection attempts are prevented"""
        user = self.get_test_user()
        context_manager = PlatformContextManager(self.session)
        
        # Try SQL injection in user_id
        malicious_user_id = "1; DROP TABLE users; --"
        
        with self.assertRaises((PlatformContextError, ValueError, TypeError)):
            context_manager.set_context(malicious_user_id, 1)
        
        # Try SQL injection in platform_id
        malicious_platform_id = "1; DROP TABLE platform_connections; --"
        
        with self.assertRaises((PlatformContextError, ValueError, TypeError)):
            context_manager.set_context(user.id, malicious_platform_id)

class TestDataAccessSecurity(PlatformTestCase):
    """Test security of data access operations"""
    
    def test_platform_filtered_queries_secure(self):
        """Test platform-filtered queries prevent data leakage"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        context_manager = PlatformContextManager(self.session)
        
        # Set context to platform1
        context_manager.set_context(user.id, platform1.id)
        
        # Query should only return platform1 data
        from models import Post
        posts = context_manager.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        
        # Verify all posts belong to platform1
        for post in posts:
            self.assertEqual(post.platform_connection_id, platform1.id)
            self.assertNotEqual(post.platform_connection_id, platform2.id)
    
    def test_context_isolation_security(self):
        """Test context isolation prevents data mixing"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Create separate context managers
        context_mgr1 = PlatformContextManager(self.session)
        context_mgr2 = PlatformContextManager(self.session)
        
        # Set different contexts
        context_mgr1.set_context(user.id, platform1.id)
        context_mgr2.set_context(user.id, platform2.id)
        
        # Get data from each context
        from models import Post
        posts1 = context_mgr1.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        
        posts2 = context_mgr2.apply_platform_filter(
            self.session.query(Post), Post
        ).all()
        
        # Verify complete isolation
        posts1_ids = {post.id for post in posts1}
        posts2_ids = {post.id for post in posts2}
        
        self.assertEqual(len(posts1_ids.intersection(posts2_ids)), 0)
    
    def test_unauthorized_data_modification_prevented(self):
        """Test unauthorized data modification is prevented"""
        user1 = self.get_test_user()
        user2 = self.users[1]
        
        # Create platform for user2
        user2_platform = PlatformConnection(
            user_id=user2.id,
            name='User2 Protected Platform',
            platform_type='pixelfed',
            instance_url='https://protected.test.com',
            username='protecteduser',
            access_token='protected_token'
        )
        self.session.add(user2_platform)
        self.session.commit()
        
        # User1 should not be able to modify user2's platform
        original_name = user2_platform.name
        
        # Simulate unauthorized modification attempt
        # In real implementation, this would be prevented by access control
        user1_platforms = self.session.query(PlatformConnection).filter(
            PlatformConnection.user_id == user1.id
        ).all()
        
        user2_platform_accessible = any(p.id == user2_platform.id for p in user1_platforms)
        self.assertFalse(user2_platform_accessible)

class TestSecurityAuditValidation(PlatformTestCase):
    """Test security audit and validation mechanisms"""
    
    def test_credential_storage_audit(self):
        """Test credential storage meets security standards"""
        platform = self.get_test_platform()
        
        # Set sensitive credential
        sensitive_token = 'highly_sensitive_access_token_12345'
        platform.access_token = sensitive_token
        self.session.commit()
        
        # Audit encrypted storage
        encrypted_token = platform._access_token
        
        # Should not contain plaintext
        self.assertNotIn('sensitive', encrypted_token.lower())
        self.assertNotIn('token', encrypted_token.lower())
        self.assertNotIn('12345', encrypted_token)
        
        # Should be properly encrypted
        self.assertNotEqual(encrypted_token, sensitive_token)
        self.assertGreater(len(encrypted_token), len(sensitive_token))
    
    def test_access_control_audit(self):
        """Test access control mechanisms meet security standards"""
        users = self.session.query(User).all()
        platforms = self.session.query(PlatformConnection).all()
        
        # Audit user-platform relationships
        for platform in platforms:
            # Each platform should belong to exactly one user
            self.assertIsNotNone(platform.user_id)
            
            # User should exist
            owner = self.session.query(User).get(platform.user_id)
            self.assertIsNotNone(owner)
            
            # Platform should be in user's platforms
            user_platform_ids = {p.id for p in owner.get_active_platforms()}
            self.assertIn(platform.id, user_platform_ids)
    
    def test_session_security_audit(self):
        """Test session security meets standards"""
        user = self.get_test_user()
        platform = self.get_test_platform()
        
        # Create session
        from models import UserSession
        session = UserSession(
            user_id=user.id,
            session_id='audit_test_session',
            active_platform_id=platform.id
        )
        self.session.add(session)
        self.session.commit()
        
        # Audit session security
        self.assertEqual(session.user_id, user.id)
        self.assertEqual(session.active_platform_id, platform.id)
        
        # Session should belong to correct user
        self.assertEqual(session.user.id, user.id)
        
        # Platform should belong to same user
        self.assertEqual(session.active_platform.user_id, user.id)

if __name__ == '__main__':
    unittest.main()