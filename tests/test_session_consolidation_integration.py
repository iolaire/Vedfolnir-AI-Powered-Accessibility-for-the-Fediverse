# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Session Consolidation

Tests the complete session management consolidation system including
login, logout, platform switching, and cross-tab synchronization.
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock

from config import Config
from database import DatabaseManager
from models import User, UserSession, PlatformConnection, UserRole, Base
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user


class TestSessionConsolidationIntegration(unittest.TestCase):
    """Integration tests for session consolidation"""
    
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
        Base.metadata.create_all(self.db_manager.engine)
        
        # Create test user with platforms
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="integration_test_user",
            role=UserRole.REVIEWER
        )
        
        # Set up Flask app for testing
        self.setup_test_app()
    
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
        
        # Clean up temporary database
        try:
            os.unlink(self.temp_db.name)
        except OSError:
            pass
    
    def setup_test_app(self):
        """Set up Flask test app with session consolidation"""
        from flask import Flask
        from unified_session_manager import UnifiedSessionManager
        from session_cookie_manager import create_session_cookie_manager
        from redis_session_middleware import get_current_session_context, get_current_session_id
        from session_security import create_session_security_manager
        from session_state_api import create_session_state_routes
        
        # Create Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        # Initialize session management components
        session_security_manager = create_session_security_manager(self.app.config, self.db_manager)
        unified_session_manager = UnifiedSessionManager(self.db_manager, security_manager=session_security_manager)
        session_cookie_manager = create_session_cookie_manager(self.app.config)
        
        # Initialize middleware
        database_session_middleware = DatabaseSessionMiddleware(self.app, unified_session_manager, session_cookie_manager)
        
        # Create session state API routes
        create_session_state_routes(self.app)
        
        # Store components for testing
        self.app.unified_session_manager = unified_session_manager
        self.app.session_cookie_manager = session_cookie_manager
        self.app.database_session_middleware = database_session_middleware
        
        # Create test client
        self.client = self.app.test_client()
    
    def test_login_creates_database_session_only(self):
        """Test that login creates only Redis session, no Flask session"""
        with self.app.test_request_context():
            # Create session directly (simulating login)
            platform_id = self.test_user.platform_connections[0].id
            session_id = self.app.unified_session_manager.create_session(
                self.test_user.id, 
                platform_id
            )
            
            # Verify session was created in database
            self.assertIsNotNone(session_id)
            
            with self.db_manager.get_session() as db_session:
                user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
                self.assertIsNotNone(user_session)
                self.assertEqual(user_session.user_id, self.test_user.id)
                self.assertEqual(user_session.active_platform_id, platform_id)
                self.assertTrue(user_session.is_active)
    
    def test_session_context_available_across_requests(self):
        """Test that session context persists across requests"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.app.unified_session_manager.create_session(
            self.test_user.id, 
            platform_id
        )
        
        # Simulate multiple requests with session cookie
        with self.client as c:
            # Set session cookie
            c.set_cookie('localhost', 'session_id', session_id)
            
            # Make first request to session state API
            response1 = c.get('/api/session/state')
            self.assertEqual(response1.status_code, 200)
            
            data1 = json.loads(response1.data)
            self.assertTrue(data1['success'])
            self.assertTrue(data1['authenticated'])
            self.assertEqual(data1['user']['id'], self.test_user.id)
            
            # Make second request
            response2 = c.get('/api/session/state')
            self.assertEqual(response2.status_code, 200)
            
            data2 = json.loads(response2.data)
            self.assertTrue(data2['success'])
            self.assertTrue(data2['authenticated'])
            self.assertEqual(data2['session_id'], session_id)
    
    def test_platform_switching_updates_database(self):
        """Test that platform switching updates Redis session"""
        # Create session with first platform
        platform1_id = self.test_user.platform_connections[0].id
        platform2_id = self.test_user.platform_connections[1].id if len(self.test_user.platform_connections) > 1 else platform1_id
        
        session_id = self.app.unified_session_manager.create_session(
            self.test_user.id, 
            platform1_id
        )
        
        # Switch platform
        success = self.app.unified_session_manager.update_platform_context(session_id, platform2_id)
        self.assertTrue(success)
        
        # Verify platform was updated in database
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertEqual(user_session.active_platform_id, platform2_id)
        
        # Verify session context reflects the change
        context = self.app.unified_session_manager.get_session_context(session_id)
        self.assertEqual(context['platform_connection_id'], platform2_id)
    
    def test_logout_clears_database_session(self):
        """Test that logout removes Redis session"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.app.unified_session_manager.create_session(
            self.test_user.id, 
            platform_id
        )
        
        # Verify session exists
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNotNone(user_session)
        
        # Logout (destroy session)
        success = self.app.unified_session_manager.destroy_session(session_id)
        self.assertTrue(success)
        
        # Verify session was removed from database
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNone(user_session)
    
    def test_session_state_api_unauthenticated(self):
        """Test session state API with no authentication"""
        with self.client as c:
            response = c.get('/api/session/state')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertFalse(data['authenticated'])
    
    def test_session_state_api_authenticated(self):
        """Test session state API with valid authentication"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.app.unified_session_manager.create_session(
            self.test_user.id, 
            platform_id
        )
        
        with self.client as c:
            # Set session cookie
            c.set_cookie('localhost', 'session_id', session_id)
            
            response = c.get('/api/session/state')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertTrue(data['authenticated'])
            self.assertEqual(data['session_id'], session_id)
            self.assertEqual(data['user']['id'], self.test_user.id)
            self.assertEqual(data['platform']['id'], platform_id)
    
    def test_session_validation_api(self):
        """Test session validation API"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.app.unified_session_manager.create_session(
            self.test_user.id, 
            platform_id
        )
        
        with self.client as c:
            # Test with valid session
            c.set_cookie('localhost', 'session_id', session_id)
            
            response = c.post('/api/session/validate')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertTrue(data['valid'])
            self.assertEqual(data['session_id'], session_id)
            
            # Test with no session
            c.set_cookie('localhost', 'session_id', '', expires=0)
            
            response = c.post('/api/session/validate')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertFalse(data['valid'])
            self.assertEqual(data['reason'], 'no_session')
    
    def test_session_heartbeat_api(self):
        """Test session heartbeat API"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.app.unified_session_manager.create_session(
            self.test_user.id, 
            platform_id
        )
        
        with self.client as c:
            # Test with valid session
            c.set_cookie('localhost', 'session_id', session_id)
            
            response = c.post('/api/session/heartbeat')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertTrue(data['active'])
            self.assertEqual(data['session_id'], session_id)
            self.assertEqual(data['user_id'], self.test_user.id)
            self.assertEqual(data['platform_id'], platform_id)
    
    def test_expired_session_handling(self):
        """Test handling of expired sessions"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.app.unified_session_manager.create_session(
            self.test_user.id, 
            platform_id
        )
        
        # Manually expire the session
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            user_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db_session.commit()
        
        with self.client as c:
            # Set expired session cookie
            c.set_cookie('localhost', 'session_id', session_id)
            
            # Try to access session state
            response = c.get('/api/session/state')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertFalse(data['authenticated'])  # Should be unauthenticated
    
    def test_session_cleanup_functionality(self):
        """Test session cleanup functionality"""
        # Create multiple sessions
        platform_id = self.test_user.platform_connections[0].id
        session1_id = self.app.unified_session_manager.create_session(self.test_user.id, platform_id)
        session2_id = self.app.unified_session_manager.create_session(self.test_user.id, platform_id)
        
        # Verify sessions exist
        with self.db_manager.get_session() as db_session:
            sessions = db_session.query(UserSession).filter_by(user_id=self.test_user.id).all()
            # Should only have one session due to cleanup on create
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].session_id, session2_id)
        
        # Test expired session cleanup
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session2_id).first()
            user_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db_session.commit()
        
        # Run cleanup
        cleaned_count = self.app.unified_session_manager.cleanup_expired_sessions()
        self.assertEqual(cleaned_count, 1)
        
        # Verify session was cleaned up
        with self.db_manager.get_session() as db_session:
            sessions = db_session.query(UserSession).filter_by(user_id=self.test_user.id).all()
            self.assertEqual(len(sessions), 0)
    
    def test_concurrent_session_operations(self):
        """Test concurrent session operations"""
        import threading
        import time
        
        platform_id = self.test_user.platform_connections[0].id
        session_ids = []
        errors = []
        
        def create_and_validate_session():
            try:
                # Create session
                session_id = self.app.unified_session_manager.create_session(self.test_user.id, platform_id)
                if session_id:
                    session_ids.append(session_id)
                    
                    # Validate session
                    is_valid = self.app.unified_session_manager.validate_session(session_id)
                    if not is_valid:
                        errors.append(f"Session {session_id} validation failed")
                    
                    # Get context
                    context = self.app.unified_session_manager.get_session_context(session_id)
                    if not context:
                        errors.append(f"Session {session_id} context retrieval failed")
                        
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=create_and_validate_session)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have created at least one session
        self.assertGreater(len(session_ids), 0)
        # Should not have any errors
        if errors:
            self.fail(f"Concurrent operations failed: {errors}")
    
    def test_session_security_features(self):
        """Test session security features"""
        # Create session with security manager
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.app.unified_session_manager.create_session(
            self.test_user.id, 
            platform_id
        )
        
        # Verify session has security features
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            
            # Should have fingerprint (if security manager is working)
            # Note: In test environment, fingerprinting might not work due to no request context
            # but we can verify the structure is there
            self.assertIsNotNone(user_session.session_fingerprint)
            
            # Should have proper timestamps
            self.assertIsNotNone(user_session.created_at)
            self.assertIsNotNone(user_session.last_activity)
            self.assertIsNotNone(user_session.expires_at)
            
            # Should be active
            self.assertTrue(user_session.is_active)
    
    def test_session_model_enhancements(self):
        """Test UserSession model enhancements"""
        # Create session
        platform_id = self.test_user.platform_connections[0].id
        session_id = self.app.unified_session_manager.create_session(
            self.test_user.id, 
            platform_id
        )
        
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            
            # Test model methods
            self.assertFalse(user_session.is_expired())
            self.assertGreater(user_session.time_until_expiry(), 0)
            self.assertGreater(user_session.get_session_duration(), 0)
            self.assertTrue(user_session.is_recently_active())
            
            # Test context dictionary
            context_dict = user_session.to_context_dict()
            self.assertIn('session_id', context_dict)
            self.assertIn('user_id', context_dict)
            self.assertIn('platform_connection_id', context_dict)
            self.assertIn('user_info', context_dict)
            self.assertIn('platform_info', context_dict)
            
            # Test activity update
            old_activity = user_session.last_activity
            user_session.update_activity()
            self.assertGreaterEqual(user_session.last_activity, old_activity)


if __name__ == '__main__':
    unittest.main()# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Session Consolidation

Tests the complete session management system integration including login,
platform switching, logout, and cross-tab synchronization using Redis sessions only.
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, timezone, timedelta
from flask import url_for

from config import Config
from database import DatabaseManager
from models import User, UserSession, PlatformConnection, UserRole
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user


class TestSessionConsolidationIntegration(unittest.TestCase):
    """Integration tests for session consolidation"""
    
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
            username="integration_test_user",
            role=UserRole.REVIEWER
        )
        
        # Set up Flask app for testing
        self.setup_test_app()
    
    def setup_test_app(self):
        """Set up Flask test app with session consolidation"""
        from flask import Flask
        from unified_session_manager import UnifiedSessionManager
        from session_cookie_manager import create_session_cookie_manager
        from redis_session_middleware import get_current_session_context, get_current_session_id
        from session_security import create_session_security_manager
        from session_state_api import create_session_state_routes
        
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        
        # Initialize session management components
        session_security_manager = create_session_security_manager(self.app.config, self.db_manager)
        unified_session_manager = UnifiedSessionManager(self.db_manager, security_manager=session_security_manager)
        session_cookie_manager = create_session_cookie_manager(self.app.config)
        database_session_middleware = DatabaseSessionMiddleware(self.app, unified_session_manager, session_cookie_manager)
        
        # Store components in app for access
        self.app.unified_session_manager = unified_session_manager
        self.app.session_cookie_manager = session_cookie_manager
        
        # Create session state API routes
        create_session_state_routes(self.app)
        
        # Add basic routes for testing
        self.add_test_routes()
        
        self.client = self.app.test_client()
    
    def add_test_routes(self):
        """Add basic routes for testing"""
        from flask import jsonify, request, make_response
        from redis_session_middleware import get_current_session_context, get_current_session_id
        
        @self.app.route('/test_login', methods=['POST'])
        def test_login():
            """Test login route that creates Redis session only"""
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            # Simple authentication check
            if username == self.test_user.username and password == 'test_password':
                # Create session using unified session manager
                platform_id = self.test_user.platform_connections[0].id if self.test_user.platform_connections else None
                session_id = self.app.unified_session_manager.create_session(self.test_user.id, platform_id)
                
                if session_id:
                    response = make_response(jsonify({'success': True, 'session_id': session_id}))
                    self.app.session_cookie_manager.set_session_cookie(response, session_id)
                    return response
                else:
                    return jsonify({'success': False, 'error': 'Failed to create session'}), 500
            else:
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        @self.app.route('/test_logout', methods=['POST'])
        def test_logout():
            """Test logout route that destroys Redis session"""
            session_id = get_current_session_id()
            if session_id:
                success = self.app.unified_session_manager.destroy_session(session_id)
                response = make_response(jsonify({'success': success}))
                self.app.session_cookie_manager.clear_session_cookie(response)
                return response
            else:
                return jsonify({'success': False, 'error': 'No session found'}), 400
        
        @self.app.route('/test_session_info')
        def test_session_info():
            """Test route to get current session info"""
            context = get_current_session_context()
            session_id = get_current_session_id()
            
            return jsonify({
                'session_id': session_id,
                'context': context,
                'authenticated': context is not None
            })
        
        @self.app.route('/test_switch_platform', methods=['POST'])
        def test_switch_platform():
            """Test platform switching route"""
            from redis_session_middleware import update_session_platform
            
            data = request.get_json()
            platform_id = data.get('platform_id')
            
            success = update_session_platform(platform_id)
            return jsonify({'success': success})
    
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
        
        # Clean up temporary database
        try:
            os.unlink(self.temp_db.name)
        except OSError:
            pass
    
    def test_login_creates_database_session_only(self):
        """Test that login creates only Redis session, no Flask session"""
        # Perform login
        response = self.client.post('/test_login', 
                                  json={'username': self.test_user.username, 'password': 'test_password'})
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('session_id', data)
        
        # Verify session cookie was set
        cookies = response.headers.getlist('Set-Cookie')
        self.assertTrue(any('session_id=' in cookie for cookie in cookies))
        
        # Redis session was created
        session_id = data['session_id']
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNotNone(user_session)
            self.assertEqual(user_session.user_id, self.test_user.id)
            self.assertTrue(user_session.is_active)
    
    def test_session_context_persists_across_requests(self):
        """Test that session context persists across requests"""
        # Login first
        login_response = self.client.post('/test_login', 
                                        json={'username': self.test_user.username, 'password': 'test_password'})
        self.assertEqual(login_response.status_code, 200)
        
        # Make subsequent request to check session info
        info_response = self.client.get('/test_session_info')
        self.assertEqual(info_response.status_code, 200)
        
        data = info_response.get_json()
        self.assertIsNotNone(data['session_id'])
        self.assertIsNotNone(data['context'])
        self.assertTrue(data['authenticated'])
        
        # Verify context contains expected data
        context = data['context']
        self.assertEqual(context['user_id'], self.test_user.id)
        self.assertIsNotNone(context['user_info'])
        self.assertEqual(context['user_info']['username'], self.test_user.username)
    
    def test_platform_switching_updates_database_session(self):
        """Test that platform switching updates Redis session"""
        # Login first
        login_response = self.client.post('/test_login', 
                                        json={'username': self.test_user.username, 'password': 'test_password'})
        self.assertEqual(login_response.status_code, 200)
        session_id = login_response.get_json()['session_id']
        
        # Get initial platform
        info_response = self.client.get('/test_session_info')
        initial_context = info_response.get_json()['context']
        initial_platform_id = initial_context['platform_connection_id']
        
        # Switch to different platform (if available)
        if len(self.test_user.platform_connections) > 1:
            new_platform_id = next(p.id for p in self.test_user.platform_connections 
                                 if p.id != initial_platform_id)
            
            switch_response = self.client.post('/test_switch_platform', 
                                             json={'platform_id': new_platform_id})
            self.assertEqual(switch_response.status_code, 200)
            self.assertTrue(switch_response.get_json()['success'])
            
            # Verify platform was updated in database
            with self.db_manager.get_session() as db_session:
                user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
                self.assertEqual(user_session.active_platform_id, new_platform_id)
            
            # Verify context reflects the change
            updated_info_response = self.client.get('/test_session_info')
            updated_context = updated_info_response.get_json()['context']
            self.assertEqual(updated_context['platform_connection_id'], new_platform_id)
    
    def test_logout_destroys_database_session(self):
        """Test that logout destroys Redis session"""
        # Login first
        login_response = self.client.post('/test_login', 
                                        json={'username': self.test_user.username, 'password': 'test_password'})
        self.assertEqual(login_response.status_code, 200)
        session_id = login_response.get_json()['session_id']
        
        # Verify session exists
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNotNone(user_session)
        
        # Logout
        logout_response = self.client.post('/test_logout')
        self.assertEqual(logout_response.status_code, 200)
        self.assertTrue(logout_response.get_json()['success'])
        
        # Verify session was destroyed in database
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNone(user_session)
        
        # Verify session cookie was cleared
        cookies = logout_response.headers.getlist('Set-Cookie')
        self.assertTrue(any('session_id=' in cookie and 'expires=' in cookie for cookie in cookies))
        
        # Verify subsequent requests show no authentication
        info_response = self.client.get('/test_session_info')
        data = info_response.get_json()
        self.assertFalse(data['authenticated'])
        self.assertIsNone(data['session_id'])
    
    def test_session_state_api_works_with_database_sessions(self):
        """Test that session state API works with Redis sessions"""
        # Login first
        login_response = self.client.post('/test_login', 
                                        json={'username': self.test_user.username, 'password': 'test_password'})
        self.assertEqual(login_response.status_code, 200)
        
        # Call session state API
        state_response = self.client.get('/api/session/state')
        self.assertEqual(state_response.status_code, 200)
        
        data = state_response.get_json()
        self.assertTrue(data['success'])
        self.assertTrue(data['authenticated'])
        self.assertIsNotNone(data['session_id'])
        self.assertIsNotNone(data['user'])
        self.assertEqual(data['user']['username'], self.test_user.username)
        
        if self.test_user.platform_connections:
            self.assertIsNotNone(data['platform'])
    
    def test_session_validation_api_works(self):
        """Test that session validation API works"""
        # Login first
        login_response = self.client.post('/test_login', 
                                        json={'username': self.test_user.username, 'password': 'test_password'})
        self.assertEqual(login_response.status_code, 200)
        
        # Call session validation API
        validate_response = self.client.post('/api/session/validate')
        self.assertEqual(validate_response.status_code, 200)
        
        data = validate_response.get_json()
        self.assertTrue(data['success'])
        self.assertTrue(data['valid'])
        self.assertIsNotNone(data['session_id'])
    
    def test_session_validation_api_invalid_session(self):
        """Test session validation API with invalid session"""
        # Call validation API without login
        validate_response = self.client.post('/api/session/validate')
        self.assertEqual(validate_response.status_code, 200)
        
        data = validate_response.get_json()
        self.assertTrue(data['success'])
        self.assertFalse(data['valid'])
        self.assertEqual(data['reason'], 'no_session')
    
    def test_session_heartbeat_api_works(self):
        """Test that session heartbeat API works"""
        # Login first
        login_response = self.client.post('/test_login', 
                                        json={'username': self.test_user.username, 'password': 'test_password'})
        self.assertEqual(login_response.status_code, 200)
        
        # Call heartbeat API
        heartbeat_response = self.client.post('/api/session/heartbeat')
        self.assertEqual(heartbeat_response.status_code, 200)
        
        data = heartbeat_response.get_json()
        self.assertTrue(data['success'])
        self.assertTrue(data['active'])
        self.assertIsNotNone(data['session_id'])
        self.assertEqual(data['user_id'], self.test_user.id)
    
    def test_session_heartbeat_api_no_session(self):
        """Test heartbeat API without session"""
        # Call heartbeat API without login
        heartbeat_response = self.client.post('/api/session/heartbeat')
        self.assertEqual(heartbeat_response.status_code, 200)
        
        data = heartbeat_response.get_json()
        self.assertTrue(data['success'])
        self.assertFalse(data['active'])
        self.assertEqual(data['reason'], 'no_session')
    
    def test_expired_session_handling(self):
        """Test handling of expired sessions"""
        # Login first
        login_response = self.client.post('/test_login', 
                                        json={'username': self.test_user.username, 'password': 'test_password'})
        self.assertEqual(login_response.status_code, 200)
        session_id = login_response.get_json()['session_id']
        
        # Manually expire the session
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            user_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db_session.commit()
        
        # Try to access session info
        info_response = self.client.get('/test_session_info')
        data = info_response.get_json()
        
        # Should show as not authenticated
        self.assertFalse(data['authenticated'])
        self.assertIsNone(data['session_id'])
        
        # Session should be marked as inactive in database
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            if user_session:  # Might be deleted depending on implementation
                self.assertFalse(user_session.is_active)
    
    def test_session_activity_updates(self):
        """Test that session activity is updated on requests"""
        # Login first
        login_response = self.client.post('/test_login', 
                                        json={'username': self.test_user.username, 'password': 'test_password'})
        self.assertEqual(login_response.status_code, 200)
        session_id = login_response.get_json()['session_id']
        
        # Get initial activity time
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            initial_activity = user_session.last_activity
        
        # Wait a moment and make another request
        import time
        time.sleep(0.1)
        
        info_response = self.client.get('/test_session_info')
        self.assertEqual(info_response.status_code, 200)
        
        # Verify activity was updated
        with self.db_manager.get_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertGreater(user_session.last_activity, initial_activity)
    
    def test_multiple_sessions_for_user(self):
        """Test handling multiple sessions for the same user"""
        # Create first session
        login1_response = self.client.post('/test_login', 
                                         json={'username': self.test_user.username, 'password': 'test_password'})
        self.assertEqual(login1_response.status_code, 200)
        session1_id = login1_response.get_json()['session_id']
        
        # Create second session (should clean up first one due to cleanup_user_sessions)
        login2_response = self.client.post('/test_login', 
                                         json={'username': self.test_user.username, 'password': 'test_password'})
        self.assertEqual(login2_response.status_code, 200)
        session2_id = login2_response.get_json()['session_id']
        
        # Verify sessions are different
        self.assertNotEqual(session1_id, session2_id)
        
        # Verify only the latest session exists (due to cleanup in create_session)
        with self.db_manager.get_session() as db_session:
            session1 = db_session.query(UserSession).filter_by(session_id=session1_id).first()
            session2 = db_session.query(UserSession).filter_by(session_id=session2_id).first()
            
            # First session should be cleaned up
            self.assertIsNone(session1)
            self.assertIsNotNone(session2)


if __name__ == '__main__':
    unittest.main()