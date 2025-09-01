# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simplified Web Application with Clean Redis Session Management

This is a simplified version of the web application that implements the clean
Redis session architecture: Redis stores all session data, Flask manages session cookies.
"""

import os
import redis
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g
from flask_login import LoginManager, UserMixin, login_user as flask_login_user, logout_user as flask_logout_user, login_required, current_user
from functools import wraps
# from notification_flash_replacement import send_notification  # Removed - using unified notification system

# Import our simplified session management
from flask_redis_session import init_redis_session
from simple_session_manager import get_session_manager, login_user, logout_user, is_logged_in, get_current_user_id, set_platform_context, get_platform_context

# Import existing modules
from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserRole

# Create Flask app with custom template directory
template_dir = os.path.join(os.path.dirname(__file__), 'templates_simple')
os.makedirs(template_dir, exist_ok=True)

app = Flask(__name__, template_folder='templates_simple')

# Load configuration
config = Config()
app.config['SECRET_KEY'] = config.webapp.secret_key

# Initialize database
db_manager = DatabaseManager(config)

# Initialize Redis client
redis_client = redis.from_url(config.redis.url)
app.redis_client = redis_client

# Initialize Redis session management
session_interface = init_redis_session(
    app, 
    redis_client=redis_client,
    prefix=config.redis.session_prefix,
    timeout=config.redis.session_timeout
)

# Initialize Flask-Login for compatibility
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

class SimpleUser(UserMixin):
    """Simple user class for Flask-Login compatibility"""
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role
    
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    try:
        session = db_manager.get_session()
        try:
            user = session.query(User).filter(
                User.id == int(user_id),
                User.is_active == True
            ).first()
            
            if user:
                return SimpleUser(user.id, user.username, user.role)
            
        finally:
            db_manager.close_session(session)
            
    except Exception as e:
        app.logger.error(f"Error loading user: {e}")
    
    return None

# Authentication decorators
def require_login(f):
    """Require user to be logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Please log in to access this page.", "Authentication Required")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def require_platform(f):
    """Require platform context"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_platform_context():
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Please select a platform first.", "Platform Required")
            return redirect(url_for('platform_management'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
@require_login
def index():
    """Main dashboard"""
    user_id = get_current_user_id()
    platform_id = get_platform_context()
    
    # Get user info
    session = db_manager.get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        platform = None
        if platform_id:
            platform = session.query(PlatformConnection).filter(
                PlatformConnection.id == platform_id,
                PlatformConnection.user_id == user_id
            ).first()
        
        return render_template('index_simple.html', 
                             user=user, 
                             platform=platform,
                             session_info=get_session_manager().get_session_info())
    finally:
        db_manager.close_session(session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Username and password are required.", "Missing Credentials")
            return render_template('login_simple.html')
        
        # Authenticate user
        session = db_manager.get_session()
        try:
            user = session.query(User).filter(
                User.username == username,
                User.is_active == True
            ).first()
            
            if user and user.check_password(password):
                # Login with our session manager
                login_user(user.id)
                
                # Also login with Flask-Login for compatibility
                flask_user = SimpleUser(user.id, user.username, user.role)
                flask_login_user(flask_user)
                
                # Check if user has platforms
                platforms = session.query(PlatformConnection).filter(
                    PlatformConnection.user_id == user.id,
                    PlatformConnection.is_active == True
                ).all()
                
                if platforms:
                    # Set default platform if available
                    default_platform = next((p for p in platforms if p.is_default), platforms[0])
                    set_platform_context(default_platform.id)
                
                # Send success notification
                from notification_helpers import send_success_notification
                send_success_notification(f'Welcome back, {user.username}!', 'Login Successful')
                return redirect(url_for('index'))
            else:
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification("Invalid username or password.", "Login Failed")
                
        finally:
            db_manager.close_session(session)
    
    return render_template('login_simple.html')

@app.route('/logout')
def logout():
    """User logout"""
    # Logout with our session manager
    logout_user()
    
    # Also logout with Flask-Login
    flask_logout_user()
    
    # Send info notification
    from notification_helpers import send_info_notification
    send_info_notification("You have been logged out.", "Logged Out")
    return redirect(url_for('login'))

@app.route('/platform_management')
@require_login
def platform_management():
    """Platform management"""
    user_id = get_current_user_id()
    
    session = db_manager.get_session()
    try:
        platforms = session.query(PlatformConnection).filter(
            PlatformConnection.user_id == user_id,
            PlatformConnection.is_active == True
        ).all()
        
        current_platform_id = get_platform_context()
        
        return render_template('platform_management_simple.html', 
                             platforms=platforms,
                             current_platform_id=current_platform_id)
    finally:
        db_manager.close_session(session)

@app.route('/switch_platform/<int:platform_id>')
@require_login
def switch_platform(platform_id):
    """Switch to a different platform"""
    user_id = get_current_user_id()
    
    # Verify platform belongs to user
    session = db_manager.get_session()
    try:
        platform = session.query(PlatformConnection).filter(
            PlatformConnection.id == platform_id,
            PlatformConnection.user_id == user_id,
            PlatformConnection.is_active == True
        ).first()
        
        if platform:
            set_platform_context(platform_id)
            # Send success notification
            from notification_helpers import send_success_notification
            send_success_notification(f'Switched to platform: {platform.name}', 'Platform Switched')
        else:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Platform not found or access denied.", "Platform Switch Failed")
            
    finally:
        db_manager.close_session(session)
    
    return redirect(url_for('platform_management'))

@app.route('/session_info')
@require_login
def session_info():
    """Display session information for debugging"""
    return jsonify(get_session_manager().get_session_info())

@app.route('/redis_info')
@require_login
def redis_info():
    """Display Redis session information"""
    try:
        from flask_redis_session import get_session_info
        session_id = session.get('_id') if hasattr(session, '_id') else 'unknown'
        info = get_session_info(redis_client, session_id, config.redis.session_prefix)
        return jsonify(info or {'error': 'Session not found'})
    except Exception as e:
        return jsonify({'error': str(e)})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error_simple.html', 
                         error_code=404, 
                         error_message='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error_simple.html', 
                         error_code=500, 
                         error_message='Internal server error'), 500

if __name__ == '__main__':
    app.logger.info("Starting simplified web application with Redis session management")
    app.logger.info(f"Redis URL: {config.redis.url}")
    app.logger.info(f"Session prefix: {config.redis.session_prefix}")
    app.logger.info(f"Session timeout: {config.redis.session_timeout}s")
    
    app.run(
        host=config.webapp.host,
        port=5000,  # Use port 5000 to avoid conflict with AirPlay on macOS
        debug=config.webapp.debug
    )
