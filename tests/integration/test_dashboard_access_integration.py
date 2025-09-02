# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# NOTE: Flash messages in this test file have been replaced with comments
# as part of the notification system migration. The actual application now
# uses the unified WebSocket-based notification system.

"""
Integration tests for dashboard access without DetachedInstanceError.

This test suite validates Task 16 requirements:
- Write test for successful dashboard access after login without DetachedInstanceError
- Create test for platform switching without session detachment
- Add test for template rendering with proper session context
- Test error recovery scenarios and fallback mechanisms
- Requirements: 1.1, 1.2, 1.3, 1.4
"""

import unittest
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
# TODO: Refactor this test to not use flask_session - from flask import Flask
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import SQLAlchemyError

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserRole, Post, Image, ProcessingStatus
from request_scoped_session_manager import RequestScopedSessionManager
from redis_session_manager import RedisSessionManager as SessionManager
from database_context_middleware import DatabaseContextMiddleware
from session_aware_user import SessionAwareUser
from tests.test_helpers.mock_user_helper import MockUserHelper

class TestDashboardAccessIntegration(unittest.TestCase):
    """Integration tests for dashboard access without DetachedInstanceError"""
    
    def setUp(self):
        """Set up test environment with Flask app and database"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.config)
        self.db_manager.create_tables()
        
        # Initialize session managers
        self.request_session_manager = RequestScopedSessionManager(self.db_manager)
        with patch('redis.Redis', MagicMock()):
            self.session_manager = SessionManager(self.db_manager)
        
        # Create Flask app for testing
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test_secret_key'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        # Add session managers to app
        self.app.request_session_manager = self.request_session_manager
        self.app.session_manager = self.session_manager
        
        # Initialize database context middleware
        self.database_context_middleware = DatabaseContextMiddleware(self.app, self.request_session_manager)
        
        # Create mock user helper
        self.mock_user_helper = MockUserHelper(self.db_manager)
        
        # Create test users and data
        self._create_test_data()
        
        # Set up Flask-Login and routes
        self._setup_flask_login()
        self._setup_test_routes()
        
        # Create test client
        self.client = self.app.test_client()
    
    def tearDown(self):
        """Clean up test environment"""
        self.mock_user_helper.cleanup_mock_users()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def _create_test_data(self):
        """Create test users and platform data"""
        # Create user with multiple platforms
        self.test_user = self.mock_user_helper.create_mock_user(
            username='integration_test_user',
            email='integration@test.com',
            password='test_password_123',
            role=UserRole.REVIEWER,
            with_platforms=True,
            platform_configs=[
                {
                    'name': 'Primary Pixelfed',
                    'platform_type': 'pixelfed',
                    'instance_url': 'https://primary.pixelfed.social',
                    'username': 'testuser_primary',
                    'access_token': 'token_primary',
                    'is_default': True
                },
                {
                    'name': 'Secondary Mastodon',
                    'platform_type': 'mastodon',
                    'instance_url': 'https://secondary.mastodon.social',
                    'username': 'testuser_secondary',
                    'access_token': 'token_secondary',
                    'is_default': False
                }
            ]
        )
        
        # Create user without platforms for testing
        self.test_user_no_platforms = self.mock_user_helper.create_mock_user(
            username='no_platforms_user',
            email='no_platforms@test.com',
            password='test_password_123',
            role=UserRole.REVIEWER,
            with_platforms=False
        )
        
        # Create some test posts and images for statistics
        self._create_test_posts_and_images()
    
    def _create_test_posts_and_images(self):
        """Create test posts and images for dashboard statistics"""
        session = self.db_manager.get_session()
        try:
            # Get the primary platform
            primary_platform = session.query(PlatformConnection).filter_by(
                user_id=self.test_user.id,
                is_default=True
            ).first()
            
            if primary_platform:
                # Create test posts
                for i in range(3):
                    post = Post(
                        platform_connection_id=primary_platform.id,
                        post_id=f'test_post_{i}',
                        user_id=f'test_user_{i}',
                        post_url=f'https://example.com/posts/{i}',
                        post_content=f'Test post {i}'
                    )
                    session.add(post)
                    session.flush()
                    
                    # Create test images for each post
                    for j in range(2):
                        image = Image(
                            platform_connection_id=primary_platform.id,
                            post_id=post.id,
                            image_post_id=f'test_image_{i}_{j}',
                            image_url=f'https://example.com/images/{i}_{j}.jpg',
                            local_path=f'/tmp/test_{i}_{j}.jpg',
                            attachment_index=j,
                            status=ProcessingStatus.PENDING if j == 0 else ProcessingStatus.APPROVED,
                            original_filename=f'test_{i}_{j}.jpg'
                        )
                        session.add(image)
                
                session.commit()
        finally:
            session.close()
    
    def _setup_flask_login(self):
        """Set up Flask-Login for testing"""
        from flask_login import LoginManager
        
        login_manager = LoginManager()
        login_manager.init_app(self.app)
        login_manager.login_view = 'login'
        
        @login_manager.user_loader
        def load_user(user_id):
            """Load user with proper session attachment"""
            if not user_id:
                return None
            
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                return None
            
            try:
                with self.request_session_manager.session_scope() as session:
                    from sqlalchemy.orm import joinedload
                    user = session.query(User).options(
                        joinedload(User.platform_connections),
                        joinedload(User.sessions)
                    ).filter(
                        User.id == user_id_int,
                        User.is_active == True
                    ).first()
                    
                    if user:
                        return SessionAwareUser(user, self.request_session_manager)
                    return None
            except Exception as e:
                print(f"Error loading user: {e}")
                return None
    
    def _setup_test_routes(self):
        """Set up test routes that mirror the actual web app"""
        from flask import render_template_string, redirect, url_for, flash, request
        from flask_login import login_user, logout_user, login_required, current_user
        from session_aware_decorators import with_db_session, require_platform_context
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            """Login route for testing"""
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                # Find user
                with self.request_session_manager.session_scope() as session:
                    from sqlalchemy.orm import joinedload
                    user = session.query(User).options(
                        joinedload(User.platform_connections),
                        joinedload(User.sessions)
                    ).filter_by(username=username).first()
                    
                    if user and user.check_password(password) and user.is_active:
                        # Create SessionAwareUser and log in
                        session_aware_user = SessionAwareUser(user, self.request_session_manager)
                        login_user(session_aware_user)
                        
                        # Create platform session if user has platforms
                        user_platforms = session.query(PlatformConnection).filter_by(
                            user_id=user.id,
                            is_active=True
                        ).all()
                        
                        if user_platforms:
                            default_platform = next((p for p in user_platforms if p.is_default), user_platforms[0])
                            session_id = self.session_manager.create_session(user.id, default_platform.id)
                            response = redirect(url_for('dashboard'))
                            self.app.session_cookie_manager.set_session_cookie(response, session_id)
                            return response
                    else:
                        # Unified notification: Invalid credentials (error)
            
            return render_template_string('''
                <form method="post">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Login</button>
                </form>
                {% with messages = get_flashed_messages() %}
                    {% if messages %}
                        {% for message in messages %}
                            <div class="flash">{{ message }}</div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
            ''')
        
        @self.app.route('/logout')
        @login_required
        def logout():
            """Logout route"""
            session_id = self.app.session_cookie_manager.get_session_id_from_cookie()
            if session_id:
                self.session_manager._cleanup_session(session_id)
            
            logout_user()
            response = make_response(redirect(url_for('login')))
            self.app.session_cookie_manager.clear_session_cookie(response)
            return response
        
        @self.app.route('/')
        @self.app.route('/dashboard')
        @login_required
        @with_db_session
        @require_platform_context
        def dashboard():
            """Dashboard route with session-aware decorators"""
            try:
                # Use request-scoped session for all database queries
                with self.request_session_manager.session_scope() as db_session:
                    # Get current platform context
                    session_id = self.app.session_cookie_manager.get_session_id_from_cookie()
                    context = None
                    current_platform = None
                    
                    if session_id:
                        context = self.session_manager.get_session_context(session_id)
                        if context and context.get('platform_connection_id'):
                            current_platform = db_session.query(PlatformConnection).filter_by(
                                id=context['platform_connection_id'],
                                user_id=current_user.id,
                                is_active=True
                            ).first()
                    
                    # Get statistics
                    stats = {}
                    if current_platform:
                        stats = {
                            'total_posts': db_session.query(Post).filter_by(
                                platform_connection_id=current_platform.id
                            ).count(),
                            'total_images': db_session.query(Image).filter_by(
                                platform_connection_id=current_platform.id
                            ).count(),
                            'pending_images': db_session.query(Image).filter_by(
                                platform_connection_id=current_platform.id,
                                status=ProcessingStatus.PENDING
                            ).count(),
                            'approved_images': db_session.query(Image).filter_by(
                                platform_connection_id=current_platform.id,
                                status=ProcessingStatus.APPROVED
                            ).count()
                        }
                    else:
                        stats = {
                            'total_posts': 0,
                            'total_images': 0,
                            'pending_images': 0,
                            'approved_images': 0
                        }
                    
                    # Test accessing user properties to ensure no DetachedInstanceError
                    user_info = {
                        'id': current_user.id,
                        'username': current_user.username,
                        'email': current_user.email,
                        'role': current_user.role.value if current_user.role else 'unknown'
                    }
                    
                    # Test accessing platforms property
                    user_platforms = current_user.platforms
                    platform_count = len(user_platforms)
                    
                    return render_template_string('''
                        <h1>Dashboard</h1>
                        <div class="user-info">
                            <p>User: {{ user_info.username }} ({{ user_info.email }})</p>
                            <p>Role: {{ user_info.role }}</p>
                            <p>Platforms: {{ platform_count }}</p>
                        </div>
                        <div class="stats">
                            <p>Posts: {{ stats.total_posts }}</p>
                            <p>Images: {{ stats.total_images }}</p>
                            <p>Pending: {{ stats.pending_images }}</p>
                            <p>Approved: {{ stats.approved_images }}</p>
                        </div>
                        {% if current_platform %}
                        <div class="platform-info">
                            <p>Current Platform: {{ current_platform.name }} ({{ current_platform.platform_type }})</p>
                            <p>Instance: {{ current_platform.instance_url }}</p>
                        </div>
                        {% endif %}
                        <div class="actions">
                            <a href="{{ url_for('switch_platform') }}">Switch Platform</a>
                            <a href="{{ url_for('logout') }}">Logout</a>
                        </div>
                    ''', 
                    user_info=user_info,
                    platform_count=platform_count,
                    stats=stats,
                    current_platform=current_platform
                    )
                    
            except DetachedInstanceError as e:
                # Unified notification: Session error occurred. Please log in again. (error)
                return redirect(url_for('login'))
            except Exception as e:
                # Unified notification: An error occurred loading the dashboard. (error)
                return redirect(url_for('login'))
        
        @self.app.route('/switch_platform')
        @login_required
        @with_db_session
        def switch_platform():
            """Platform switching route"""
            try:
                # Get user's platforms
                user_platforms = current_user.platforms
                
                if len(user_platforms) < 2:
                    # Unified notification: You need at least 2 platforms to switch. (warning)
                    return redirect(url_for('dashboard'))
                
                # Get current platform
                session_id = self.app.session_cookie_manager.get_session_id_from_cookie()
                current_platform_id = None
                if session_id:
                    context = self.session_manager.get_session_context(session_id)
                    if context:
                        current_platform_id = context.get('platform_connection_id')
                
                # Find next platform to switch to
                next_platform = None
                for platform in user_platforms:
                    if platform.id != current_platform_id:
                        next_platform = platform
                        break
                
                if next_platform:
                    # Update session with new platform
                    if session_id:
                        success = self.session_manager.update_platform_context(session_id, next_platform.id)
                        if success:
                            flash(f'Switched to {next_platform.name}', 'success')
                        else:
                            # Unified notification: Failed to switch platform (error)
                    else:
                        # Create new session with the platform
                        new_session_id = self.session_manager.create_session(current_user.id, next_platform.id)
# TODO: Refactor this test to not use flask_session -                         flask_session['_id'] = new_session_id
                        flash(f'Switched to {next_platform.name}', 'success')
                
                return redirect(url_for('dashboard'))
                
            except DetachedInstanceError as e:
                # Unified notification: Session error during platform switch. Please log in again. (error)
                return redirect(url_for('login'))
            except Exception as e:
                # Unified notification: Error switching platform. (error)
                return redirect(url_for('dashboard'))
        
        @self.app.route('/first_time_setup')
        @login_required
        def first_time_setup():
            """First time setup route"""
            return render_template_string('''
                <h1>First Time Setup</h1>
                <p>Please set up your first platform connection.</p>
                <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
            ''')
        
        @self.app.route('/platform_management')
        @login_required
        def platform_management():
            """Platform management route"""
            return render_template_string('''
                <h1>Platform Management</h1>
                <p>Manage your platform connections here.</p>
                <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
            ''')
    
    def _login_user(self, username, password):
        """Helper to log in a user via the login form"""
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=False)
    
    def test_successful_dashboard_access_after_login_without_detached_instance_error(self):
        """Test successful dashboard access after login without DetachedInstanceError (Requirement 1.1)"""
        # Login user
        response = self._login_user('integration_test_user', 'test_password_123')
        self.assertEqual(response.status_code, 302)  # Redirect after login
        
        # Access dashboard
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        
        # Verify dashboard content is rendered properly
        self.assertIn(b'Dashboard', response.data)
        self.assertIn(b'integration_test_user', response.data)
        self.assertIn(b'Posts:', response.data)
        self.assertIn(b'Images:', response.data)
        self.assertIn(b'Primary Pixelfed', response.data)
        
        # Verify no DetachedInstanceError occurred (would result in redirect or error)
        self.assertNotIn(b'Session error', response.data)
        self.assertNotIn(b'Please log in again', response.data)
    
    def test_platform_switching_without_session_detachment(self):
        """Test platform switching without session detachment (Requirement 3.1, 3.2)"""
        # Login user
        self._login_user('integration_test_user', 'test_password_123')
        
        # Access dashboard to verify initial state
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Primary Pixelfed', response.data)
        
        # Switch platform
        response = self.client.get('/switch_platform', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify platform was switched and dashboard still accessible
        self.assertIn(b'Dashboard', response.data)
        self.assertIn(b'Secondary Mastodon', response.data)
        
        # Verify no session detachment errors
        self.assertNotIn(b'Session error', response.data)
        self.assertNotIn(b'DetachedInstanceError', response.data)
        
        # Switch back to verify bidirectional switching works
        response = self.client.get('/switch_platform', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Primary Pixelfed', response.data)
    
    def test_template_rendering_with_proper_session_context(self):
        """Test template rendering with proper session context (Requirement 5.1, 5.2, 5.3, 5.4)"""
        # Login user
        self._login_user('integration_test_user', 'test_password_123')
        
        # Access dashboard
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        
        # Verify all template context variables are properly rendered
        response_text = response.data.decode('utf-8')
        
        # User information should be accessible
        self.assertIn('integration_test_user', response_text)
        self.assertIn('integration@test.com', response_text)
        self.assertIn('reviewer', response_text.lower())
        
        # Platform count should be rendered
        self.assertIn('Platforms: 2', response_text)
        
        # Statistics should be rendered
        self.assertIn('Posts: 3', response_text)  # From test data
        self.assertIn('Images: 6', response_text)  # From test data
        
        # Current platform information should be rendered
        self.assertIn('Primary Pixelfed', response_text)
        self.assertIn('https://primary.pixelfed.social', response_text)
        
        # Navigation links should be rendered
        self.assertIn('Switch Platform', response_text)
        self.assertIn('Logout', response_text)
    
    def test_error_recovery_scenarios_and_fallback_mechanisms(self):
        """Test error recovery scenarios and fallback mechanisms (Requirement 7.1, 7.2, 7.3, 7.4)"""
        # Test 1: User with no platforms should redirect to setup
        self._login_user('no_platforms_user', 'test_password_123')
        
        response = self.client.get('/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'First Time Setup', response.data)
        
        # Test 2: Invalid session context recovery
        self._login_user('integration_test_user', 'test_password_123')
        
        # Corrupt the session
        self.client.set_cookie('localhost', 'session_id', 'invalid_session_id')
        
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        # Should still work with fallback mechanisms
        self.assertIn(b'Dashboard', response.data)
        
        # Test 3: Database error during dashboard access (test separately to avoid login interference)
        self._login_user('integration_test_user', 'test_password_123')
        
        # Patch only the dashboard's session scope, not the login
        original_session_scope = self.request_session_manager.session_scope
        
        def mock_session_scope_for_dashboard():
            # Check if we're in dashboard context by looking at the call stack
            import inspect
            frame = inspect.currentframe()
            try:
                # Look for dashboard function in the call stack
                while frame:
                    if frame.f_code.co_name == 'dashboard':
                        raise SQLAlchemyError("Database connection failed")
                    frame = frame.f_back
                # If not in dashboard, use original
                return original_session_scope()
            finally:
                del frame
        
        with patch.object(self.request_session_manager, 'session_scope', side_effect=mock_session_scope_for_dashboard):
            response = self.client.get('/dashboard', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            # Should redirect to login with error message
            self.assertIn(b'Login', response.data)
    
    def test_dashboard_access_with_detached_instance_simulation(self):
        """Test dashboard access when DetachedInstanceError is simulated (Requirement 1.2, 1.3)"""
        # Login user
        self._login_user('integration_test_user', 'test_password_123')
        
        # Simulate DetachedInstanceError by patching current_user property access
        with patch('session_aware_user.SessionAwareUser.__getattr__') as mock_getattr:
            # First call succeeds (for authentication check), second raises DetachedInstanceError
            mock_getattr.side_effect = [1, DetachedInstanceError("Object is detached")]
            
            response = self.client.get('/dashboard', follow_redirects=True)
            
            # Should handle the error gracefully and redirect to login
            self.assertEqual(response.status_code, 200)
            # Should either show login page or handle error gracefully
            self.assertTrue(b'Login' in response.data or b'Dashboard' in response.data)
    
    def test_multiple_dashboard_accesses_maintain_session_integrity(self):
        """Test multiple dashboard accesses maintain session integrity (Requirement 1.4)"""
        # Login user
        self._login_user('integration_test_user', 'test_password_123')
        
        # Access dashboard multiple times
        for i in range(5):
            response = self.client.get('/dashboard')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Dashboard', response.data)
            self.assertIn(b'integration_test_user', response.data)
            
            # Verify session context is maintained
            self.assertIn(b'Primary Pixelfed', response.data)
            self.assertNotIn(b'Session error', response.data)
    
    def test_concurrent_platform_operations_without_detachment(self):
        """Test concurrent platform operations without session detachment (Requirement 3.3, 3.4)"""
        # Login user
        self._login_user('integration_test_user', 'test_password_123')
        
        # Perform multiple operations in sequence
        operations = [
            ('/dashboard', b'Dashboard'),
            ('/switch_platform', b'Dashboard'),  # Switch redirects to dashboard
            ('/dashboard', b'Secondary Mastodon'),
            ('/switch_platform', b'Dashboard'),  # Switch redirects to dashboard
            ('/dashboard', b'Primary Pixelfed')
        ]
        
        for url, expected_content in operations:
            response = self.client.get(url, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(expected_content, response.data)
            self.assertNotIn(b'Session error', response.data)
            self.assertNotIn(b'DetachedInstanceError', response.data)
    
    def test_session_cleanup_after_logout(self):
        """Test proper session cleanup after logout (Requirement 4.3, 4.4)"""
        # Login user
        self._login_user('integration_test_user', 'test_password_123')
        
        # Verify dashboard access works
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        
        # Logout
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
        
        # Verify dashboard is no longer accessible
        response = self.client.get('/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)  # Should redirect to login
    
    def test_template_context_error_handling(self):
        """Test template context error handling (Requirement 5.4)"""
        # Login user
        self._login_user('integration_test_user', 'test_password_123')
        
        # Simulate error in template context by patching platform access
        with patch.object(SessionAwareUser, 'platforms', new_callable=lambda: property(lambda self: (_ for _ in ()).throw(DetachedInstanceError("Platforms detached")))):
            response = self.client.get('/dashboard', follow_redirects=True)
            
            # Should handle error gracefully
            self.assertEqual(response.status_code, 200)
            # Should either redirect to login or show dashboard with error handling
            # The dashboard should still render but may have fallback content
            self.assertTrue(b'Login' in response.data or b'Dashboard' in response.data)

if __name__ == '__main__':
    unittest.main()