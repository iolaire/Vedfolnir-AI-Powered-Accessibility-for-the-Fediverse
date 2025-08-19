# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Final end-to-end tests for session consolidation validation

Tests complete session lifecycle using only Redis sessions,
verifying Flask session elimination and unified session functionality.
"""

import unittest
import json
from unittest.mock import patch, MagicMock
from flask import Flask, g
from datetime import datetime, timezone, timedelta

from unified_session_manager import UnifiedSessionManager, SessionValidationError, SessionDatabaseError
from session_cookie_manager import SessionCookieManager
from redis_session_middleware import get_current_session_context, get_current_session_id, get_current_session_context, get_current_user_id, get_current_platform_id, is_session_authenticated
from database import DatabaseManager
from models import User, PlatformConnection, UserSession

class SessionConsolidationFinalE2ETest(unittest.TestCase):
    """Final end-to-end tests for session consolidation"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock database manager
        self.mock_db_manager = MagicMock(spec=DatabaseManager)
        self.mock_db_session = MagicMock()
        self.mock_db_manager.get_session.return_value.__enter__.return_value = self.mock_db_session
        self.mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Initialize session components
        self.session_manager = UnifiedSessionManager(self.mock_db_manager)
        self.cookie_manager = SessionCookieManager()
        self.middleware = DatabaseSessionMiddleware(self.app, self.session_manager, self.cookie_manager)
        
        # Test data
        self.test_user_id = 123
        self.test_platform_id = 456
        self.test_session_id = 'test-session-123'
        
        self.client = self.app.test_client()
    
    def test_complete_session_lifecycle_database_only(self):
        """Test complete session lifecycle using only Redis sessions"""
        
        # Mock user and platform
        mock_user = MagicMock(spec=User)
        mock_user.id = self.test_user_id
        mock_user.username = 'testuser'
        mock_user.email = 'test@test.com'
        mock_user.is_active = True
        
        mock_platform = MagicMock(spec=PlatformConnection)
        mock_platform.id = self.test_platform_id
        mock_platform.name = 'Test Platform'
        mock_platform.platform_type = 'pixelfed'
        mock_platform.instance_url = 'https://test.example.com'
        mock_platform.username = 'testuser'
        mock_platform.is_default = True
        mock_platform.is_active = True
        
        # Mock database queries
        self.mock_db_session.get.return_value = mock_user
        self.mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_platform
        
        # Step 1: Create session (login)
        with patch('uuid.uuid4', return_value=MagicMock(spec=str)) as mock_uuid:
            mock_uuid.return_value = self.test_session_id
            
            session_id = self.session_manager.create_session(self.test_user_id, self.test_platform_id)
            
            self.assertEqual(session_id, self.test_session_id)
            self.mock_db_session.add.assert_called_once()
            self.mock_db_session.commit.assert_called()
        
        # Step 2: Verify session context retrieval
        mock_user_session = MagicMock(spec=UserSession)
        mock_user_session.user = mock_user
        mock_user_session.active_platform = mock_platform
        mock_user_session.session_id = self.test_session_id
        mock_user_session.user_id = self.test_user_id
        mock_user_session.active_platform_id = self.test_platform_id
        mock_user_session.created_at = datetime.now(timezone.utc)
        mock_user_session.updated_at = datetime.now(timezone.utc)
        mock_user_session.last_activity = datetime.now(timezone.utc)
        mock_user_session.is_expired.return_value = False
        mock_user_session.to_context_dict.return_value = {
            'session_id': self.test_session_id,
            'user_id': self.test_user_id,
            'user_info': {
                'username': 'testuser',
                'email': 'test@test.com',
                'is_active': True
            },
            'platform_connection_id': self.test_platform_id,
            'platform_info': {
                'name': 'Test Platform',
                'platform_type': 'pixelfed',
                'instance_url': 'https://test.example.com',
                'is_default': True
            },
            'created_at': mock_user_session.created_at.isoformat(),
            'last_activity': mock_user_session.last_activity.isoformat()
        }
        
        self.mock_db_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_user_session
        
        context = self.session_manager.get_session_context(self.test_session_id)
        
        self.assertIsNotNone(context)
        self.assertEqual(context['user_id'], self.test_user_id)
        self.assertEqual(context['platform_connection_id'], self.test_platform_id)
        self.assertIn('user_info', context)
        self.assertIn('platform_info', context)
        
        # Step 3: Validate session
        is_valid = self.session_manager.validate_session(self.test_session_id)
        self.assertTrue(is_valid)
        
        # Step 4: Update platform context
        new_platform_id = 789
        mock_new_platform = MagicMock(spec=PlatformConnection)
        mock_new_platform.id = new_platform_id
        mock_new_platform.name = 'New Platform'
        mock_new_platform.user_id = self.test_user_id
        mock_new_platform.is_active = True
        
        # Mock platform switch query
        self.mock_db_session.query.return_value.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_user_session)),  # Session lookup
            MagicMock(first=MagicMock(return_value=mock_new_platform))   # Platform lookup
        ]
        
        success = self.session_manager.update_platform_context(self.test_session_id, new_platform_id)
        self.assertTrue(success)
        
        # Step 5: Destroy session (logout)
        self.mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_user_session
        
        success = self.session_manager.destroy_session(self.test_session_id)
        self.assertTrue(success)
        self.mock_db_session.delete.assert_called_with(mock_user_session)
    
    def test_middleware_session_loading(self):
        """Test middleware loads session context correctly"""
        
        # Mock session context
        mock_context = {
            'session_id': self.test_session_id,
            'user_id': self.test_user_id,
            'platform_connection_id': self.test_platform_id,
            'user_info': {'username': 'testuser'},
            'platform_info': {'name': 'Test Platform'}
        }
        
        with patch.object(self.cookie_manager, 'get_session_id_from_cookie', return_value=self.test_session_id):
            with patch.object(self.session_manager, 'get_session_context', return_value=mock_context):
                
                @self.app.route('/test')
                def test_route():
                    # Test context access functions
                    context = get_current_session_context()
                    user_id = get_current_user_id()
                    platform_id = get_current_platform_id()
                    authenticated = is_session_authenticated()
                    
                    return json.dumps({
                        'context': context,
                        'user_id': user_id,
                        'platform_id': platform_id,
                        'authenticated': authenticated
                    })
                
                response = self.client.get('/test')
                self.assertEqual(response.status_code, 200)
                
                data = json.loads(response.data)
                self.assertEqual(data['context'], mock_context)
                self.assertEqual(data['user_id'], self.test_user_id)
                self.assertEqual(data['platform_id'], self.test_platform_id)
                self.assertTrue(data['authenticated'])
    
    def test_no_flask_session_usage(self):
        """Verify no Flask session usage in session operations"""
        
        @self.app.route('/test_no_flask_session')
        def test_route():
            # This route should NOT use Flask session at all
            # Redis session context should be available
            
            # Verify Flask session is not used
            from flask import session as flask_session
            
            # Flask session should be empty/unused
            flask_session_keys = list(flask_session.keys())
            
            # Redis session context
            context = get_current_session_context()
            
            return json.dumps({
                'flask_session_keys': flask_session_keys,
                'has_db_context': context is not None,
                'context_keys': list(context.keys()) if context else []
            })
        
        # Redis session context
        mock_context = {
            'session_id': self.test_session_id,
            'user_id': self.test_user_id,
            'platform_connection_id': self.test_platform_id
        }
        
        with patch.object(self.cookie_manager, 'get_session_id_from_cookie', return_value=self.test_session_id):
            with patch.object(self.session_manager, 'get_session_context', return_value=mock_context):
                
                response = self.client.get('/test_no_flask_session')
                self.assertEqual(response.status_code, 200)
                
                data = json.loads(response.data)
                
                # Flask session should be empty (no session data stored there)
                self.assertEqual(len(data['flask_session_keys']), 0)
                
                # Database context should be available
                self.assertTrue(data['has_db_context'])
                self.assertIn('session_id', data['context_keys'])
                self.assertIn('user_id', data['context_keys'])
    
    def test_session_expiration_handling(self):
        """Test session expiration is handled correctly"""
        
        # Mock expired session
        mock_user_session = MagicMock(spec=UserSession)
        mock_user_session.is_expired.return_value = True
        mock_user_session.is_active = True
        
        self.mock_db_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_user_session
        
        # Expired session should return None context
        context = self.session_manager.get_session_context(self.test_session_id)
        self.assertIsNone(context)
        
        # Session should be marked as inactive
        self.assertFalse(mock_user_session.is_active)
        self.mock_db_session.commit.assert_called()
    
    def test_session_security_validation(self):
        """Test session security validation"""
        
        # Test with security manager
        mock_security_manager = MagicMock()
        mock_security_manager.validate_session_comprehensive.return_value = MagicMock()
        
        session_manager_with_security = UnifiedSessionManager(
            self.mock_db_manager, 
            security_manager=mock_security_manager
        )
        
        # Valid session
        is_valid = session_manager_with_security.validate_session(self.test_session_id)
        self.assertTrue(is_valid)
        mock_security_manager.validate_session_comprehensive.assert_called_with(self.test_session_id)
        
        # Invalid session
        mock_security_manager.validate_session_comprehensive.return_value = None
        is_valid = session_manager_with_security.validate_session(self.test_session_id)
        self.assertFalse(is_valid)
    
    def test_cookie_security_attributes(self):
        """Test session cookies have proper security attributes"""
        
        from flask import make_response
        
        response = make_response('test')
        self.cookie_manager.set_session_cookie(response, self.test_session_id)
        
        # Check cookie was set
        cookies = response.headers.getlist('Set-Cookie')
        self.assertEqual(len(cookies), 1)
        
        cookie_header = cookies[0]
        
        # Verify security attributes
        self.assertIn('HttpOnly', cookie_header)
        self.assertIn('SameSite=Lax', cookie_header)
        self.assertIn('Path=/', cookie_header)
        
        # In production, should also have Secure flag
        if self.cookie_manager.secure:
            self.assertIn('Secure', cookie_header)
    
    def test_concurrent_session_operations(self):
        """Test concurrent session operations work correctly"""
        import threading
        import time
        
        results = []
        errors = []
        
        def session_operation(user_id, platform_id, operation_id):
            try:
                # Mock user and platform for this operation
                mock_user = MagicMock(spec=User)
                mock_user.id = user_id
                mock_user.is_active = True
                
                mock_platform = MagicMock(spec=PlatformConnection)
                mock_platform.id = platform_id
                mock_platform.user_id = user_id
                mock_platform.is_active = True
                
                # Create separate mock for this thread
                thread_db_manager = MagicMock(spec=DatabaseManager)
                thread_db_session = MagicMock()
                thread_db_manager.get_session.return_value.__enter__.return_value = thread_db_session
                thread_db_manager.get_session.return_value.__exit__.return_value = None
                
                thread_db_session.get.return_value = mock_user
                thread_db_session.query.return_value.filter_by.return_value.first.return_value = mock_platform
                
                thread_session_manager = UnifiedSessionManager(thread_db_manager)
                
                # Perform session operations
                session_id = thread_session_manager.create_session(user_id, platform_id)
                
                # Simulate some processing time
                time.sleep(0.01)
                
                # Mock session for context retrieval
                mock_user_session = MagicMock(spec=UserSession)
                mock_user_session.is_expired.return_value = False
                mock_user_session.to_context_dict.return_value = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'platform_connection_id': platform_id
                }
                
                thread_db_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_user_session
                
                context = thread_session_manager.get_session_context(session_id)
                
                if context and context['user_id'] == user_id:
                    results.append(f"Operation {operation_id} successful")
                else:
                    errors.append(f"Operation {operation_id} context error")
                    
            except Exception as e:
                errors.append(f"Operation {operation_id} failed: {e}")
        
        # Run concurrent operations
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=session_operation,
                args=(100 + i, 200 + i, i)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify results
        self.assertEqual(len(results), 5, f"Expected 5 successful operations, got {len(results)}. Errors: {errors}")
        self.assertEqual(len(errors), 0, f"Expected no errors, got: {errors}")
    
    def test_session_cleanup_operations(self):
        """Test session cleanup operations work correctly"""
        
        # Mock expired sessions
        mock_expired_session1 = MagicMock(spec=UserSession)
        mock_expired_session2 = MagicMock(spec=UserSession)
        
        self.mock_db_session.query.return_value.filter.return_value.all.return_value = [
            mock_expired_session1, mock_expired_session2
        ]
        
        # Test cleanup
        count = self.session_manager.cleanup_expired_sessions()
        
        self.assertEqual(count, 2)
        self.mock_db_session.delete.assert_any_call(mock_expired_session1)
        self.mock_db_session.delete.assert_any_call(mock_expired_session2)
        self.mock_db_session.commit.assert_called()

if __name__ == '__main__':
    unittest.main()