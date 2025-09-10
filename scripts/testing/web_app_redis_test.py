# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Web App Redis Session Test

Simple Flask application to test the new Redis session management system.
This is a minimal implementation to verify the session refactoring works correctly.
"""

import os
from datetime import timedelta
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Import new session components
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from redis_session_backend import RedisSessionBackend
from flask_redis_session_interface import FlaskRedisSessionInterface
from session_manager_v2 import SessionManagerV2
from session_middleware_v2 import SessionMiddleware, create_user_session, destroy_current_session, update_session_platform
from models import User, PlatformConnection

# Create Flask app
app = Flask(__name__)

# Load configuration
config = Config()
app.config['SECRET_KEY'] = config.webapp.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = config.storage.database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set Flask session configuration
app.config['SESSION_COOKIE_NAME'] = os.getenv('SESSION_COOKIE_NAME', 'vedfolnir_session')
app.config['SESSION_COOKIE_HTTPONLY'] = os.getenv('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=int(os.getenv('REDIS_SESSION_TIMEOUT', '7200')))

# Initialize database
db_manager = DatabaseManager(config)

# Initialize Redis session backend
redis_backend = RedisSessionBackend.from_env()

# Initialize session manager
session_manager = SessionManagerV2(
    db_manager=db_manager,
    redis_backend=redis_backend,
    session_timeout=int(os.getenv('REDIS_SESSION_TIMEOUT', '7200'))
)

# Set up Flask Redis session interface
redis_session_interface = FlaskRedisSessionInterface(
    redis_client=redis_backend.redis,
    key_prefix=os.getenv('REDIS_SESSION_PREFIX', 'vedfolnir:session:'),
    session_timeout=int(os.getenv('REDIS_SESSION_TIMEOUT', '7200'))
)
app.session_interface = redis_session_interface

# Store session manager in app for access
app.session_manager = session_manager

# Initialize session middleware
session_middleware = SessionMiddleware(app, session_manager)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    try:
        with db_manager.get_session() as db_session:
            user = db_session.query(User).filter_by(id=int(user_id), is_active=True).first()
            return user
    except Exception as e:
        app.logger.error(f"Error loading user {user_id}: {e}")
        return None

# Test templates
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Redis Session Test - Login</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .form-group { margin: 10px 0; }
        input[type="text"], input[type="password"] { padding: 8px; width: 200px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <h1>Redis Session Test - Login</h1>
    
    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}
    
    {% if success %}
        <div class="success">{{ success }}</div>
    {% endif %}
    
    <form method="POST">
        <div class="form-group">
            <label>Username:</label><br>
            <input type="text" name="username" required>
        </div>
        <div class="form-group">
            <label>Password:</label><br>
            <input type="password" name="password" required>
        </div>
        <div class="form-group">
            <button type="submit">Login</button>
        </div>
    </form>
    
    <h3>Test Credentials:</h3>
    <p><strong>Admin:</strong> username: admin, password: 5OIkH4M:%iaP7QbdU9wj2Sfj</p>
    <p><strong>User:</strong> username: iolaire, password: g9bDFB9JzgEaVZx</p>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Redis Session Test - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .session-info { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; }
        .platform-info { background: #e9ecef; padding: 15px; margin: 10px 0; border-radius: 5px; }
        button { padding: 10px 20px; margin: 5px; background: #007bff; color: white; border: none; cursor: pointer; }
        .danger { background: #dc3545; }
        .success { background: #28a745; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>Redis Session Test - Dashboard</h1>
    
    <div class="session-info">
        <h3>Current Session Info</h3>
        <p><strong>User:</strong> {{ session_data.username }} (ID: {{ session_data.user_id }})</p>
        <p><strong>Role:</strong> {{ session_data.role }}</p>
        <p><strong>Session ID:</strong> {{ session_data.session_id }}</p>
        <p><strong>Created:</strong> {{ session_data.created_at }}</p>
        <p><strong>Last Activity:</strong> {{ session_data.last_activity }}</p>
        
        {% if session_data.platform_connection_id %}
        <div class="platform-info">
            <h4>Current Platform</h4>
            <p><strong>Platform:</strong> {{ session_data.platform_name }} ({{ session_data.platform_type }})</p>
            <p><strong>Instance:</strong> {{ session_data.platform_instance_url }}</p>
        </div>
        {% else %}
        <p><em>No platform selected</em></p>
        {% endif %}
    </div>
    
    <div>
        <h3>Actions</h3>
        <button onclick="location.href='/test/session_info'">View Session Details</button>
        <button onclick="location.href='/test/platforms'">Manage Platforms</button>
        <button onclick="location.href='/test/stats'">Session Stats</button>
        <button onclick="extendSession()" class="success">Extend Session</button>
        <button onclick="location.href='/logout'" class="danger">Logout</button>
    </div>
    
    <div>
        <h3>Raw Session Data</h3>
        <pre>{{ session_raw | tojson(indent=2) }}</pre>
    </div>
    
    <script>
        function extendSession() {
            fetch('/test/extend_session', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Session extended successfully');
                    } else {
                        alert('Failed to extend session: ' + data.error);
                    }
                });
        }
    </script>
</body>
</html>
"""

# Routes

@app.route('/')
def index():
    """Home page - redirect to dashboard if logged in, otherwise login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template_string(LOGIN_TEMPLATE, error="Username and password required")
        
        try:
            # Authenticate user
            with db_manager.get_session() as db_session:
                user = db_session.query(User).filter_by(username=username, is_active=True).first()
                
                if user and user.check_password(password):
                    # Get user's default platform
                    default_platform = db_session.query(PlatformConnection).filter_by(
                        user_id=user.id,
                        is_default=True,
                        is_active=True
                    ).first()
                    
                    # Create session
                    session_id = create_user_session(
                        user_id=user.id,
                        platform_connection_id=default_platform.id if default_platform else None
                    )
                    
                    if session_id:
                        # Login user with Flask-Login
                        login_user(user, remember=True)
                        
                        app.logger.info(f"User {username} logged in successfully with session {session_id}")
                        return redirect(url_for('dashboard'))
                    else:
                        return render_template_string(LOGIN_TEMPLATE, error="Failed to create session")
                else:
                    return render_template_string(LOGIN_TEMPLATE, error="Invalid username or password")
                    
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            return render_template_string(LOGIN_TEMPLATE, error="Login failed")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
@login_required
def logout():
    """Logout and destroy session"""
    try:
        # Destroy current session
        destroy_current_session()
        
        # Logout from Flask-Login
        logout_user()
        
        return render_template_string(LOGIN_TEMPLATE, success="Logged out successfully")
        
    except Exception as e:
        app.logger.error(f"Logout error: {e}")
        return render_template_string(LOGIN_TEMPLATE, error="Logout failed")

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    try:
        # Get session data
        session_data = dict(session)
        session_data['session_id'] = getattr(session, 'sid', 'Unknown')
        
        return render_template_string(DASHBOARD_TEMPLATE, 
                                    session_data=session_data,
                                    session_raw=session_data)
        
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        return f"Dashboard error: {e}", 500

@app.route('/test/session_info')
@login_required
def session_info():
    """Get detailed session information"""
    try:
        from session_middleware_v2 import get_current_session_context, get_current_session_id
        
        session_id = get_current_session_id()
        context = get_current_session_context()
        
        # Get session data from Redis
        redis_data = session_manager.get_session_data(session_id) if session_id else None
        
        # Get session stats
        stats = session_manager.get_session_stats()
        
        return jsonify({
            'session_id': session_id,
            'flask_session': dict(session),
            'session_context': context,
            'redis_data': redis_data,
            'session_stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test/platforms')
@login_required
def platforms():
    """List user platforms and allow switching"""
    try:
        with db_manager.get_session() as db_session:
            platforms = db_session.query(PlatformConnection).filter_by(
                user_id=current_user.id,
                is_active=True
            ).all()
            
            platform_list = []
            for platform in platforms:
                platform_list.append({
                    'id': platform.id,
                    'name': platform.name,
                    'platform_type': platform.platform_type.value if hasattr(platform.platform_type, 'value') else str(platform.platform_type),
                    'instance_url': platform.instance_url,
                    'is_default': platform.is_default,
                    'is_current': platform.id == session.get('platform_connection_id')
                })
            
            return jsonify({
                'platforms': platform_list,
                'current_platform_id': session.get('platform_connection_id')
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test/switch_platform/<int:platform_id>', methods=['POST'])
@login_required
def switch_platform(platform_id):
    """Switch to a different platform"""
    try:
        success = update_session_platform(platform_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Switched to platform {platform_id}',
                'new_platform_id': session.get('platform_connection_id')
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to switch platform'
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test/extend_session', methods=['POST'])
@login_required
def extend_session():
    """Extend current session"""
    try:
        from session_middleware_v2 import extend_current_session
        
        success = extend_current_session()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Session extended successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to extend session'
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test/stats')
@login_required
def stats():
    """Get session statistics"""
    try:
        stats = session_manager.get_session_stats()
        
        # Get user sessions
        user_sessions = session_manager.get_user_sessions(current_user.id)
        
        return jsonify({
            'global_stats': stats,
            'user_sessions': user_sessions,
            'redis_health': redis_backend.health_check()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test/cleanup_sessions', methods=['POST'])
@login_required
def cleanup_sessions():
    """Clean up user sessions (keep current)"""
    try:
        count = session_manager.cleanup_user_sessions(current_user.id, keep_current=True)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {count} sessions',
            'cleaned_count': count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
