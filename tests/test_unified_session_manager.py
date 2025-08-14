# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for UnifiedSessionManager

Tests the unified session management system that replaces both Flask and database sessions
with a single database-backed session management approach.
"""

import unittest
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from config import Config
from database import DatabaseManager
from models import User, UserSession, PlatformConnection, UserRole
from unified_session_manager import (
    UnifiedSessionManager, 
    SessionValidationError, 
    SessionExpiredError, 
    SessionNotFoundError,
    SessionDatabaseError
)
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user


class TestUnifiedSessionManager(unittest.TestCase):
    """Test cases for UnifiedSessionManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Set up test configuration
        self.config = Config()
        self.config.database.url = f'sqlite:///{self.temp_db.name}'
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.config)
        
        # Create tables
        from models import Base
        Base.metadata.create_all(self.db_manager.engine)
        
        # Create test user with platforms
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_session_user",
            role=UserRole.REVIEWER
        )
        
        # Initialize session manager
        self.session_manager = UnifiedSessionManager(self.db_manager)
    
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
        
        # Clean up temporary database
        try:
            os.unlink(self.temp_db.name)
        except OSError:
            pass
    
    def test_create_session_success(self):
        """Test successful session creation"""
        # Get platform ID
        platform_id = self.test_user.platform_connections[0].id
        
        # Create session
        session_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Verify session was created
        self.assertIsNotNone(session_id)
        self.assertIsInstance(session_id, str)
        
        # Verify session exists in database
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNotNone(user_session)
            self.assertEqual(user_session.user_id, self.test_user.id)
            self.assertEqual(user_session.active_platform_id, platform_id)
            self.assertTrue(user_session.is_active)
    
    def test_create_session_invalid_user(self):
        """Test session creation with invalid user"""
        with self.assertRaises(SessionValidationError):
            self.session_manager.create_session(99999)  # Non-existent user
    
    def test_create_session_invalid_platform(self):
        """Test session creation with invalid platform"""
        with self.assertRaises(SessionValidationError):
            self.session_manager.create_session(self.test_user.id, 99999)  # Non-existent platform
    
    def test_create_session_without_platform(self):
        """Test session creation without specifying platform"""
        # Create session without platform
        session_id = self.session_manager.create_session(self.test_user.id)
        
        # Verify session was created with default platform
        self.assertIsNotNone(session_id)
        
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNotNone(user_session)
            # Should use default platform
            default_platform = next((p for p in self.test_user.platform_connections if p.is_default), None)
            if default_platform:
                self.assertEqual(user_session.active_platform_id, default_platform.id)
    
    def test_get_session_context_valid(self):
        """Test getting session context for valid session"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Get session context
        context = self.session_manager.get_session_context(session_id)
        
        # Verify context
        self.assertIsNotNone(context)
        self.assertEqual(context['session_id'], session_id)
        self.assertEqual(context['user_id'], self.test_user.id)
        self.assertEqual(context['platform_connection_id'], platform_id)
        self.assertIsNotNone(context['user_info'])
        self.assertIsNotNone(context['platform_info'])
    
    def test_get_session_context_invalid(self):
        """Test getting session context for invalid session"""
        context = self.session_manager.get_session_context('invalid_session_id')
        self.assertIsNone(context)
    
    def test_get_session_context_expired(self):
        """Test getting session context for expired session"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Manually expire the session
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            user_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db_session.commit()
        
        # Try to get context
        context = self.session_manager.get_session_context(session_id)
        self.assertIsNone(context)
        
        # Verify session was marked as inactive
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertFalse(user_session.is_active)
    
    def test_validate_session_valid(self):
        """Test validating a valid session"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Validate session
        is_valid = self.session_manager.validate_session(session_id)
        self.assertTrue(is_valid)
    
    def test_validate_session_invalid(self):
        """Test validating an invalid session"""
        is_valid = self.session_manager.validate_session('invalid_session_id')
        self.assertFalse(is_valid)
    
    def test_validate_session_expired(self):
        """Test validating an expired session"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Manually expire the session
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            user_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db_session.commit()
        
        # Validate session
        is_valid = self.session_manager.validate_session(session_id)
        self.assertFalse(is_valid)
    
    def test_update_session_activity(self):
        """Test updating session activity"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Get initial activity time
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            initial_activity = user_session.last_activity
        
        # Wait a moment and update activity
        import time
        time.sleep(0.1)
        
        success = self.session_manager.update_session_activity(session_id)
        self.assertTrue(success)
        
        # Verify activity was updated
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertGreater(user_session.last_activity, initial_activity)
    
    def test_update_platform_context(self):
        """Test updating platform context"""
        # Create session with first platform
        platform1_id = self.test_user.platform_connections[0].id
        platform2_id = self.test_user.platform_connections[1].id if len(self.test_user.platform_connections) > 1 else platform1_id
        
        session_id = self.session_manager.create_session(self.test_user.id, platform1_id)
        
        # Update to second platform
        success = self.session_manager.update_platform_context(session_id, platform2_id)
        self.assertTrue(success)
        
        # Verify platform was updated
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertEqual(user_session.active_platform_id, platform2_id)
    
    def test_update_platform_context_invalid_session(self):
        """Test updating platform context for invalid session"""
        platform_id = self.test_user.platform_connections[0].id
        success = self.session_manager.update_platform_context('invalid_session_id', platform_id)
        self.assertFalse(success)
    
    def test_update_platform_context_invalid_platform(self):
        """Test updating platform context with invalid platform"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Try to update to invalid platform
        success = self.session_manager.update_platform_context(session_id, 99999)
        self.assertFalse(success)
    
    def test_destroy_session(self):
        """Test destroying a session"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Verify session exists
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNotNone(user_session)
        
        # Destroy session
        success = self.session_manager.destroy_session(session_id)
        self.assertTrue(success)
        
        # Verify session was deleted
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNone(user_session)
    
    def test_destroy_session_invalid(self):
        """Test destroying an invalid session"""
        success = self.session_manager.destroy_session('invalid_session_id')
        self.assertFalse(success)
    
    def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions"""
        # Create multiple sessions
        platform_id = self.test_user.platform_connections[0].id
        session1_id = self.session_manager.create_session(self.test_user.id, platform_id)
        session2_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Manually expire one session
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session1_id).first()
            user_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db_session.commit()
        
        # Clean up expired sessions
        cleaned_count = self.session_manager.cleanup_expired_sessions()
        self.assertEqual(cleaned_count, 1)
        
        # Verify expired session was deleted
        with self.db_manager.get_session() as db_session:
            expired_session = db_session.query(UserSession).filter_by(session_id=session1_id).first()
            active_session = db_session.query(UserSession).filter_by(session_id=session2_id).first()
            
            self.assertIsNone(expired_session)
            self.assertIsNotNone(active_session)
    
    def test_cleanup_user_sessions(self):
        """Test cleaning up all sessions for a user"""
        # Create multiple sessions
        platform_id = self.test_user.platform_connections[0].id
        session1_id = self.session_manager.create_session(self.test_user.id, platform_id)
        session2_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Clean up user sessions
        cleaned_count = self.session_manager.cleanup_user_sessions(self.test_user.id)
        self.assertEqual(cleaned_count, 2)
        
        # Verify all sessions were deleted
        with self.db_manager.get_session() as db_session:
            sessions = db_session.query(UserSession).filter_by(user_id=self.test_user.id).all()
            self.assertEqual(len(sessions), 0)
    
    def test_cleanup_user_sessions_keep_current(self):
        """Test cleaning up user sessions while keeping current one"""
        # Create multiple sessions
        platform_id = self.test_user.platform_connections[0].id
        session1_id = self.session_manager.create_session(self.test_user.id, platform_id)
        session2_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Clean up user sessions but keep session2
        cleaned_count = self.session_manager.cleanup_user_sessions(self.test_user.id, keep_current=session2_id)
        self.assertEqual(cleaned_count, 1)
        
        # Verify only session1 was deleted
        with self.db_manager.get_session() as db_session:
            session1 = db_session.query(UserSession).filter_by(session_id=session1_id).first()
            session2 = db_session.query(UserSession).filter_by(session_id=session2_id).first()
            
            self.assertIsNone(session1)
            self.assertIsNotNone(session2)
    
    @patch('unified_session_manager.logger')
    def test_database_error_handling(self, mock_logger):
        """Test handling of database errors"""
        # Mock database manager to raise an error
        with patch.object(self.session_manager.db_manager, 'get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")
            
            # Try to create session
            session_id = self.session_manager.create_session(self.test_user.id)
            
            # Should return None and log error
            self.assertIsNone(session_id)
            mock_logger.error.assert_called()
    
    def test_session_fingerprinting(self):
        """Test session fingerprinting functionality"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.create_session_fingerprint.return_value = "test_fingerprint"
        
        session_manager = UnifiedSessionManager(self.db_manager, security_manager=mock_security_manager)
        
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = session_manager.create_session(self.test_user.id, platform_id)
        
        # Verify fingerprint was created
        mock_security_manager.create_session_fingerprint.assert_called()
        
        # Verify fingerprint was stored
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertEqual(user_session.session_fingerprint, "test_fingerprint")
    
    def test_security_audit_events(self):
        """Test security audit event creation"""
        # Mock security manager
        mock_security_manager = Mock()
        session_manager = UnifiedSessionManager(self.db_manager, security_manager=mock_security_manager)
        
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = session_manager.create_session(self.test_user.id, platform_id)
        
        # Verify audit event was created
        mock_security_manager.create_security_audit_event.assert_called_with(
            'session_created',
            session_id,
            self.test_user.id,
            unittest.mock.ANY
        )
    
    def test_concurrent_session_creation(self):
        """Test handling of concurrent session creation"""
        import threading
        import time
        
        platform_id = self.test_user.platform_connections[0].id
        session_ids = []
        errors = []
        
        def create_session_thread():
            try:
                session_id = self.session_manager.create_session(self.test_user.id, platform_id)
                if session_id:
                    session_ids.append(session_id)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_session_thread)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have created sessions (cleanup happens automatically)
        self.assertGreater(len(session_ids), 0)
        # Should not have any errors
        self.assertEqual(len(errors), 0)
    
    def test_session_context_dict_format(self):
        """Test session context dictionary format"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Get context
        context = self.session_manager.get_session_context(session_id)
        
        # Verify required fields
        required_fields = [
            'session_id', 'user_id', 'platform_connection_id',
            'created_at', 'last_activity', 'user_info', 'platform_info'
        ]
        
        for field in required_fields:
            self.assertIn(field, context)
        
        # Verify user_info structure
        user_info = context['user_info']
        self.assertIn('id', user_info)
        self.assertIn('username', user_info)
        self.assertIn('email', user_info)
        self.assertIn('role', user_info)
        
        # Verify platform_info structure
        platform_info = context['platform_info']
        self.assertIn('id', platform_info)
        self.assertIn('name', platform_info)
        self.assertIn('platform_type', platform_info)
        self.assertIn('instance_url', platform_info)
        self.assertIn('is_default', platform_info)
    
    def test_session_cleanup_on_create(self):
        """Test that creating a session cleans up existing sessions"""
        platform_id = self.test_user.platform_connections[0].id
        
        # Create first session
        session1_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Verify first session exists
        with self.db_manager.get_session() as db_session:
            sessions = db_session.query(UserSession).filter_by(user_id=self.test_user.id).all()
            self.assertEqual(len(sessions), 1)
        
        # Create second session (should clean up first)
        session2_id = self.session_manager.create_session(self.test_user.id, platform_id)
        
        # Verify only second session exists
        with self.db_manager.get_session() as db_session:
            sessions = db_session.query(UserSession).filter_by(user_id=self.test_user.id).all()
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].session_id, session2_id)
    
    def test_empty_session_id_handling(self):
        """Test handling of empty or None session IDs"""
        # Test with None
        context = self.session_manager.get_session_context(None)
        self.assertIsNone(context)
        
        # Test with empty string
        context = self.session_manager.get_session_context('')
        self.assertIsNone(context)
        
        # Test validation with None
        is_valid = self.session_manager.validate_session(None)
        self.assertFalse(is_valid)
        
        # Test validation with empty string
        is_valid = self.session_manager.validate_session('')
        self.assertFalse(is_valid)


if __name__ == '__main__':
    unittest.main()