# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import os
import asyncio
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory, session, g, Response
# Removed Flask-SocketIO import - using SSE instead
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from wtforms import TextAreaField, SelectField, SubmitField, HiddenField, StringField, PasswordField, BooleanField, IntegerField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange
from functools import wraps
from config import Config
from database import DatabaseManager
from models import ProcessingStatus, Image, Post, User, UserRole, ProcessingRun, PlatformConnection
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from activitypub_client import ActivityPubClient
from ollama_caption_generator import OllamaCaptionGenerator
from caption_quality_assessment import CaptionQualityManager
from health_check import HealthChecker
from session_manager import SessionManager, PlatformContextMiddleware
from flask_session_manager import FlaskSessionManager, FlaskPlatformContextMiddleware, get_current_platform_context, get_current_platform
from request_scoped_session_manager import RequestScopedSessionManager
from session_aware_user import SessionAwareUser
from session_aware_decorators import with_db_session, require_platform_context
from security.core.security_utils import sanitize_for_log, sanitize_html_input
from enhanced_input_validation import enhanced_input_validation, EnhancedInputValidator
from security.core.security_middleware import SecurityMiddleware, require_https, validate_csrf_token, sanitize_filename, generate_secure_token, rate_limit, validate_input_length, require_secure_connection
from security.core.security_config import security_config
from security.features.caption_security import CaptionSecurityManager, caption_generation_auth_required, validate_task_access, caption_generation_rate_limit, validate_caption_settings_input, log_caption_security_event
from error_recovery_manager import error_recovery_manager
from web_caption_generation_service import WebCaptionGenerationService
from caption_review_integration import CaptionReviewIntegration
from admin_monitoring import AdminMonitoringService
from security.logging.secure_error_handlers import register_secure_error_handlers
# Removed WebSocketProgressHandler import - using SSE instead
from progress_tracker import ProgressTracker
from task_queue_manager import TaskQueueManager

app = Flask(__name__)
config = Config()
app.config['SECRET_KEY'] = config.webapp.secret_key

# Initialize SSE Progress Handler (replaces SocketIO)
from sse_progress_handler import SSEProgressHandler
# Secure session configuration
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Allow HTTP in development
    SESSION_COOKIE_HTTPONLY=True,         # Prevent XSS access
    SESSION_COOKIE_SAMESITE='Lax',        # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=48)  # Extended session timeout
)

app.config['SQLALCHEMY_DATABASE_URI'] = config.storage.database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=config.auth.session_lifetime)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(seconds=config.auth.remember_cookie_duration)

# Secure session configuration - disable HTTPS requirements for development
app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP in development
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['SESSION_COOKIE_NAME'] = 'session'  # Standard name for development
app.config['REMEMBER_COOKIE_SECURE'] = False  # Allow HTTP in development
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'


# Initialize CSRF protection
csrf = CSRFProtect()
csrf.init_app(app)

# Initialize enhanced CSRF token manager
from security.core.csrf_token_manager import initialize_csrf_token_manager
csrf_token_manager = initialize_csrf_token_manager(app)

# Initialize CSRF error handler
from security.core.csrf_error_handler import register_csrf_error_handlers
csrf_error_handler = register_csrf_error_handlers(app)

# Initialize CSRF middleware
from security.core.csrf_middleware import initialize_csrf_middleware
csrf_middleware = initialize_csrf_middleware(app)

# Configure CSRF settings
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
app.config['WTF_CSRF_SSL_STRICT'] = False  # Allow HTTP in development
app.config['WTF_CSRF_CHECK_DEFAULT'] = True

# Enhanced CSRF configuration
app.config['CSRF_TOKEN_LIFETIME'] = 3600  # 1 hour for our token manager
app.config['WTF_CSRF_ENABLED'] = True  # Always enable CSRF protection

# Only disable CSRF for specific testing scenarios
if os.getenv('DISABLE_CSRF_FOR_TESTING', 'false').lower() == 'true':
    app.config['WTF_CSRF_ENABLED'] = False
    app.logger.warning("CSRF protection disabled for testing - DO NOT USE IN PRODUCTION")

# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add comprehensive security headers to all responses"""
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # HTTPS enforcement (only in production)
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com https://cdn.jsdelivr.net https://cdn.socket.io; "
        "style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com cdn.jsdelivr.net fonts.googleapis.com; "
        "font-src 'self' cdnjs.cloudflare.com cdn.jsdelivr.net fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'"
    )
    response.headers['Content-Security-Policy'] = csp
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions policy
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    return response


# Initialize database and quality manager
db_manager = DatabaseManager(config)
quality_manager = CaptionQualityManager()

# Initialize health checker
health_checker = HealthChecker(config, db_manager)

# Initialize database-based session manager and middleware
session_manager = SessionManager(db_manager)
platform_middleware = PlatformContextMiddleware(app, session_manager)

# Keep Flask session manager for backward compatibility
flask_session_manager = FlaskSessionManager(db_manager)

# Initialize request-scoped session manager for preventing DetachedInstanceError
request_session_manager = RequestScopedSessionManager(db_manager)
app.request_session_manager = request_session_manager  # Store in app for decorator access

# Initialize database context middleware for request lifecycle management
from database_context_middleware import DatabaseContextMiddleware
database_context_middleware = DatabaseContextMiddleware(app, request_session_manager)

# Initialize session performance monitoring
from session_performance_monitor import initialize_performance_monitoring
from session_monitoring_cli import register_session_monitoring_commands
from session_monitoring_routes import register_session_monitoring_routes

# Initialize performance monitoring with database engine
session_performance_monitor = initialize_performance_monitoring(app, request_session_manager, db_manager.engine)

# Register CLI commands and web routes for monitoring
register_session_monitoring_commands(app)
register_session_monitoring_routes(app)

# Initialize security middleware
security_middleware = SecurityMiddleware(app)

# Initialize caption security manager
caption_security_manager = CaptionSecurityManager(db_manager)
app.config['db_manager'] = db_manager
app.config['caption_security_manager'] = caption_security_manager

# Initialize caption review integration
caption_review_integration = CaptionReviewIntegration(db_manager)

# Register secure error handlers
register_secure_error_handlers(app)

# Initialize session error logging
from session_error_logger import initialize_session_error_logging
session_error_logger = initialize_session_error_logging(app)

# Initialize and register session error handlers for DetachedInstanceError prevention
from session_error_handlers import register_session_error_handlers, with_session_error_handling
from detached_instance_handler import create_global_detached_instance_handler

# Create detached instance handler
detached_instance_handler = create_global_detached_instance_handler(app, request_session_manager)

# Register comprehensive session error handlers
register_session_error_handlers(app, request_session_manager, detached_instance_handler)

# Initialize admin monitoring service
admin_monitoring_service = AdminMonitoringService(db_manager)

# Initialize WebSocket progress handler components
progress_tracker = ProgressTracker(db_manager)
task_queue_manager = TaskQueueManager(db_manager)
sse_progress_handler = SSEProgressHandler(db_manager, progress_tracker, task_queue_manager)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


def validate_favicon_assets():
    """Validate that required favicon and logo assets exist"""
    required_assets = [
        'static/favicons/favicon.ico',
        'static/favicons/favicon-32x32.png',
        'static/favicons/favicon-16x16.png',
        'static/favicons/apple-icon-180x180.png',
        'static/favicons/android-icon-192x192.png',
        'static/images/Logo.png'
    ]
    
    missing_assets = []
    for asset in required_assets:
        asset_path = os.path.join(app.root_path, asset)
        if not os.path.exists(asset_path):
            missing_assets.append(asset)
    
    if missing_assets:
        app.logger.warning(f"Missing favicon/logo assets: {missing_assets}")
        return False
    else:
        app.logger.info("All required favicon and logo assets are present")
        return True


# Validate assets on startup
validate_favicon_assets()

# Template context processor to make config available to templates
@app.context_processor
def inject_config():
    return {
        'caption_max_length': config.caption.max_length,
        'caption_optimal_min_length': config.caption.optimal_min_length,
        'caption_optimal_max_length': config.caption.optimal_max_length
    }

# Template context processor to provide platform information is now handled by DatabaseContextMiddleware
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# User loader for Flask-Login with session attachment
@login_manager.user_loader
def load_user(user_id):
    """
    Load user for Flask-Login with proper session attachment to prevent DetachedInstanceError.
    Returns SessionAwareUser instance that maintains session context throughout request.
    Only returns active users as required by Flask-Login security best practices.
    """
    if not user_id:
        app.logger.warning("load_user called with empty user_id")
        return None
    
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        app.logger.warning(f"Invalid user_id format: {sanitize_for_log(str(user_id))}")
        return None
    
    app.logger.debug(f"Loading user with ID: {user_id_int}")
    
    try:
        # Use request-scoped session to prevent DetachedInstanceError
        with request_session_manager.session_scope() as session:
            # Use explicit joinedload for relationships to prevent lazy loading issues
            user = session.query(User).options(
                joinedload(User.platform_connections),
                joinedload(User.sessions)
            ).filter(
                User.id == user_id_int,
                User.is_active == True  # Only load active users
            ).first()
            
            if user:
                app.logger.debug(f"User loaded successfully: {user.username} (ID: {user.id})")
                # Return SessionAwareUser to maintain session attachment
                return SessionAwareUser(user, request_session_manager)
            else:
                app.logger.info(f"User not found or inactive for ID: {user_id_int}")
                return None
                
    except SQLAlchemyError as e:
        app.logger.error(f"Database error loading user {user_id_int}: {sanitize_for_log(str(e))}")
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error loading user {user_id_int}: {sanitize_for_log(str(e))}")
        return None

# Note: UserMixin functionality is now provided by SessionAwareUser class
# which is returned by the load_user function above

# Request teardown handler for session cleanup is now handled by DatabaseContextMiddleware

# Role-based access control decorator
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login', next=request.url))
            
            # SECURITY FIX: Always validate user permissions from server-side database
            # Never trust client-side session data for authorization
            db_session = db_manager.get_session()
            try:
                server_user = db_session.query(User).get(current_user.id)
                if not server_user:
                    flash('User account not found.', 'error')
                    logout_user()
                    return redirect(url_for('login'))
                if not server_user.is_active:
                    flash('Your account has been deactivated.', 'error')
                    logout_user()
                    return redirect(url_for('login'))
                # Use server-side user data for role validation
                if not server_user.has_permission(role):
                    flash('You do not have permission to access this page.', 'error')
                    return redirect(url_for('index'))
                # Store validated user role in g for this request
                g.validated_user_role = server_user.role
            except SQLAlchemyError as e:
                app.logger.error(f"Database error during authorization: {sanitize_for_log(str(e))}")
                flash('Authorization error. Please try again.', 'error')
                return redirect(url_for('login'))
            finally:
                db_session.close()
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Platform access validation decorator
def platform_required(f):
    """Decorator to ensure user has at least one active platform connection"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
        
        # Check if user has platform context
        context = get_current_platform_context()
        
        if not context or not context.get('platform_connection_id'):
            # No platform context, check if user has any platforms
            db_session = db_manager.get_session()
            try:
                user_platforms = db_session.query(PlatformConnection).filter_by(
                    user_id=current_user.id,
                    is_active=True
                ).count()
                
                if user_platforms == 0:
                    flash('You need to set up at least one platform connection to access this feature.', 'warning')
                    return redirect(url_for('first_time_setup'))
                else:
                    flash('Please select a platform to continue.', 'warning')
                    return redirect(url_for('platform_management'))
            finally:
                db_session.close()
        
        return f(*args, **kwargs)
    return decorated_function

# Platform-specific access validation decorator
def platform_access_required(platform_type=None, instance_url=None):
    """Decorator to validate access to specific platform type or instance"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login', next=request.url))
            
            # Get current platform context and validate with fresh database query
            context = get_current_platform_context()
            if not context or not context.get('platform_connection_id'):
                flash('No active platform connection found.', 'error')
                return redirect(url_for('platform_management'))
            
            # Get current platform from database to avoid DetachedInstanceError
            db_session = db_manager.get_session()
            try:
                current_platform = db_session.query(PlatformConnection).filter_by(
                    id=context['platform_connection_id'],
                    user_id=current_user.id,
                    is_active=True
                ).first()
                
                if not current_platform:
                    flash('Current platform connection is no longer available.', 'error')
                    return redirect(url_for('platform_management'))
                
                # Extract platform data before closing session
                platform_type_actual = current_platform.platform_type
                instance_url_actual = current_platform.instance_url
            finally:
                db_session.close()
            
            # Validate platform type if specified
            if platform_type and platform_type_actual != platform_type:
                flash(f'This feature requires a {platform_type.title()} connection. Current platform: {platform_type_actual.title()}', 'error')
                return redirect(url_for('platform_management'))
            
            # Validate instance URL if specified
            if instance_url and instance_url_actual != instance_url:
                flash(f'This feature requires access to {instance_url}. Current instance: {instance_url_actual}', 'error')
                return redirect(url_for('platform_management'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Custom Jinja2 filters
@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to <br> tags"""
    if not text:
        return ""
    return text.replace('\n', '<br>')

# Make UserRole available in all templates
@app.context_processor
def inject_user_role():
    """Make UserRole available in all templates"""
    return {'UserRole': UserRole}

class LoginForm(FlaskForm):
    """Form for user login"""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UserForm(FlaskForm):
    """Base form for user management"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password')
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[EqualTo('password', message='Passwords must match')])
    role = SelectField('Role', choices=[(role.value, role.value.capitalize()) for role in UserRole])

class AddUserForm(UserForm):
    """Form for adding a new user"""
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Add User')

class EditUserForm(UserForm):
    """Form for editing an existing user"""
    user_id = HiddenField('User ID')
    is_active = BooleanField('Active')
    submit = SubmitField('Save Changes')

class DeleteUserForm(FlaskForm):
    """Form for deleting a user"""
    user_id = HiddenField('User ID', validators=[DataRequired()])
    submit = SubmitField('Delete User')

class ReviewForm(FlaskForm):
    """Form for reviewing image captions"""
    image_id = HiddenField('Image ID', validators=[DataRequired()])
    caption = TextAreaField('Caption', validators=[DataRequired(), Length(max=security_config.MAX_CAPTION_LENGTH)], 
                          render_kw={"rows": 3, "placeholder": "Enter alt text description..."})
    action = SelectField('Action', choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('edit', 'Save for Later')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Length(max=1000)], render_kw={"rows": 2, "placeholder": "Optional notes..."})
    submit = SubmitField('Submit')

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
@rate_limit(limit=10, window_seconds=300)  # 10 attempts per 5 minutes
@validate_input_length()
@with_session_error_handling
def login():
    """User login with proper session management to prevent DetachedInstanceError"""
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        # Use request-scoped session manager for all database operations
        try:
            with request_session_manager.session_scope() as db_session:
                # Find user with explicit relationship loading to prevent lazy loading issues
                user = db_session.query(User).options(
                    joinedload(User.platform_connections),
                    joinedload(User.sessions)
                ).filter_by(username=form.username.data).first()
                
                if user and user.check_password(form.password.data) and user.is_active:
                    # Store user info before login_user() call to avoid DetachedInstanceError
                    user_id = user.id
                    username = user.username
                    
                    # Update last login time within the session scope
                    user.last_login = datetime.now(timezone.utc)
                    db_session.commit()
                    
                    # Get user's platform connections with proper session attachment
                    user_platforms = db_session.query(PlatformConnection).filter_by(
                        user_id=user_id,
                        is_active=True
                    ).order_by(PlatformConnection.is_default.desc(), PlatformConnection.name).all()
                    
                    # Extract platform data before session closes to avoid DetachedInstanceError
                    platform_data = []
                    for p in user_platforms:
                        platform_data.append({
                            'id': p.id,
                            'name': p.name,
                            'platform_type': p.platform_type,
                            'is_default': p.is_default
                        })
                    
                    # Log in the user with Flask-Login (creates SessionAwareUser via load_user)
                    login_user(user, remember=form.remember.data)
                    
                    if not platform_data:
                        # First-time user - redirect to platform setup
                        flash('Welcome! Please set up your first platform connection to get started.', 'info')
                        return redirect(url_for('first_time_setup'))
                    
                    # Create Flask-based session with default platform using extracted data
                    try:
                        default_platform = next((p for p in platform_data if p['is_default']), None)
                        if not default_platform:
                            # Set first platform as default if none is set
                            default_platform = platform_data[0]
                            # Update default platform in database within session scope
                            for p in user_platforms:
                                p.is_default = (p.id == default_platform['id'])
                            db_session.commit()
                        
                        # Create database session with platform context
                        session_id = session_manager.create_user_session(user_id, default_platform['id'])
                        
                        # Store session ID in Flask session
                        session['_id'] = session_id
                        session.permanent = True
                        
                        if session_id:
                            # Welcome message with platform info
                            flash(f'Welcome back! Connected to {default_platform["name"]} ({default_platform["platform_type"].title()})', 'success')
                            app.logger.info(f"Created Flask session for user {sanitize_for_log(username)} with platform {sanitize_for_log(default_platform['name'])}")
                        else:
                            app.logger.error(f"Failed to create Flask session for user {sanitize_for_log(username)}")
                            flash('Login successful, but there was an issue setting up your platform context', 'warning')
                        
                    except Exception as e:
                        app.logger.error(f"Error creating platform session: {sanitize_for_log(str(e))}")
                        flash('Login successful, but there was an issue setting up your platform context', 'warning')
                    
                    # Redirect to the requested page or default to index with session context maintained
                    next_page = request.args.get('next')
                    if next_page and next_page.startswith('/'):  # Ensure the next page is relative
                        return redirect(next_page)
                    return redirect(url_for('index'))
                else:
                    flash('Invalid username or password', 'error')
                    
        except SQLAlchemyError as e:
            app.logger.error(f"Database error during login: {sanitize_for_log(str(e))}")
            flash('Database error occurred during login. Please try again.', 'error')
        except Exception as e:
            app.logger.error(f"Unexpected error during login: {sanitize_for_log(str(e))}")
            flash('An unexpected error occurred during login. Please try again.', 'error')
            
    return render_template('login.html', form=form)

@app.route('/first_time_setup')
@login_required
@with_session_error_handling
def first_time_setup():
    """First-time platform setup for new users"""
    # Check if user already has platforms - redirect if they do
    db_session = db_manager.get_session()
    try:
        user_platforms = db_session.query(PlatformConnection).filter_by(
            user_id=current_user.id,
            is_active=True
        ).count()
        
        if user_platforms > 0:
            return redirect(url_for('index'))
    finally:
        db_session.close()
    
    return render_template('first_time_setup.html')

@app.route('/logout')
@login_required
def logout():
    """User logout - clears platform context and current session"""
    # Get current platform info for logging
    current_platform = None
    try:
        context = get_current_platform_context()
        if context and context.get('platform_info'):
            current_platform = context['platform_info']
    except Exception:
        pass
    
    # Clear database session
    flask_session_id = session.get('_id')
    if flask_session_id:
        # Clean up database session
        session_manager._cleanup_session(flask_session_id)
    
    # Clear Flask session
    session.clear()
    
    # Log out the user
    logout_user()
    
    # Provide contextual logout message
    if current_platform:
        flash(f'You have been logged out from {current_platform["name"]}', 'info')
    else:
        flash('You have been logged out', 'info')
    
    return redirect(url_for('login'))

@app.route('/logout_all')
@login_required
def logout_all():
    """Logout from current session (Flask sessions are per-browser)"""
    try:
        # Clear all database sessions for the user
        session_manager.cleanup_all_user_sessions(current_user.id)
        
        # Clear Flask session
        session.clear()
        
        # Log out the user
        logout_user()
        flash('You have been logged out', 'info')
        
    except Exception as e:
        app.logger.error(f"Error during logout: {sanitize_for_log(str(e))}")
        flash('Error logging out', 'error')
    
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
@with_session_error_handling
def profile():
    """User profile with platform preferences"""
    db_session = db_manager.get_session()
    try:
        # Get user's platform connections
        user_platforms = db_session.query(PlatformConnection).filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(PlatformConnection.is_default.desc(), PlatformConnection.name).all()
        
        # Get current platform from context
        current_platform = None
        context = get_current_platform_context()
        if context and context.get('platform_info'):
            # Convert platform info dict to a simple object for template compatibility
            platform_info = context['platform_info']
            current_platform = type('Platform', (), platform_info)()
        
        # Get user statistics per platform
        platform_stats = {}
        for platform in user_platforms:
            stats = {
                'posts': db_session.query(Post).filter_by(platform_connection_id=platform.id).count(),
                'images': db_session.query(Image).filter_by(platform_connection_id=platform.id).count(),
                'pending': db_session.query(Image).filter_by(
                    platform_connection_id=platform.id,
                    status=ProcessingStatus.PENDING
                ).count(),
                'approved': db_session.query(Image).filter_by(
                    platform_connection_id=platform.id,
                    status=ProcessingStatus.APPROVED
                ).count(),
                'posted': db_session.query(Image).filter_by(
                    platform_connection_id=platform.id,
                    status=ProcessingStatus.POSTED
                ).count()
            }
            platform_stats[platform.id] = stats
        
        # Get current session info (Flask sessions are per-browser)
        active_sessions = []
        context = get_current_platform_context()
        if context:
            active_sessions = [{
                'platform_id': context.get('platform_connection_id'),
                'platform_name': context.get('platform_info', {}).get('name', 'Unknown') if context.get('platform_info') else 'Unknown',
                'created_at': context.get('created_at'),
                'last_activity': context.get('last_activity'),
                'is_current': True
            }]
        
        # Get user settings for current platform
        user_settings = None
        if current_platform:
            from models import CaptionGenerationUserSettings
            user_settings = db_session.query(CaptionGenerationUserSettings).filter_by(
                user_id=current_user.id,
                platform_connection_id=current_platform.id
            ).first()
        
        # Convert platforms to dicts to avoid DetachedInstanceError
        user_platforms_dict = [{
            'id': p.id,
            'name': p.name,
            'platform_type': p.platform_type,
            'instance_url': p.instance_url,
            'username': p.username,
            'is_default': p.is_default,
            'is_active': p.is_active
        } for p in user_platforms]
        
        current_platform_dict = None
        if current_platform:
            current_platform_dict = {
                'id': current_platform.id,
                'name': current_platform.name,
                'platform_type': current_platform.platform_type,
                'instance_url': current_platform.instance_url,
                'username': current_platform.username,
                'is_default': current_platform.is_default,
                'is_active': current_platform.is_active
            }
        
        return render_template('profile.html',
                             user_platforms=user_platforms_dict,
                             current_platform=current_platform_dict,
                             platform_stats=platform_stats,
                             active_sessions=active_sessions,
                             user_settings=user_settings)
    finally:
        db_session.close()

@app.route('/user_management')
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def user_management():
    """User management interface"""
    session = db_manager.get_session()
    try:
        users = session.query(User).all()
        
        # Create forms for user management
        add_form = AddUserForm()
        edit_form = EditUserForm()
        delete_form = DeleteUserForm()
        
        return render_template('user_management.html', 
                              users=users, 
                              add_form=add_form, 
                              edit_form=edit_form, 
                              delete_form=delete_form)
    finally:
        session.close()

@app.route('/add_user', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@require_secure_connection
@validate_input_length()
@enhanced_input_validation
@with_session_error_handling
def add_user():
    """Add a new user"""
    form = AddUserForm()
    if form.validate_on_submit():
        session = db_manager.get_session()
        try:
            # Check if username or email already exists
            existing_user = session.query(User).filter(
                (User.username == form.username.data) | 
                (User.email == form.email.data)
            ).first()
            
            if existing_user:
                if existing_user.username == form.username.data:
                    flash(f'Username {form.username.data} is already taken', 'error')
                else:
                    flash(f'Email {form.email.data} is already registered', 'error')
                return redirect(url_for('user_management'))
            
            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=UserRole(form.role.data),
                is_active=True
            )
            user.set_password(form.password.data)
            
            session.add(user)
            session.commit()
            flash(f'User {form.username.data} created successfully', 'success')
        except SQLAlchemyError as e:
            session.rollback()
            app.logger.error(f'Database error creating user: {sanitize_for_log(str(e))}')
            flash('Database error occurred while creating the user', 'error')
        except (ValueError, TypeError, AttributeError) as e:
            session.rollback()
            flash(f'Validation error: {sanitize_for_log(str(e))}', 'error')
        except Exception as e:
            session.rollback()
            app.logger.exception(f'Unexpected error creating user: {sanitize_for_log(str(e))}')
            flash('An unexpected error occurred while creating the user', 'error')
        finally:
            session.close()
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')
    
    return redirect(url_for('user_management'))

@app.route('/edit_user', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@require_secure_connection
@validate_input_length()
@enhanced_input_validation
@with_session_error_handling
def edit_user():
    """Edit an existing user"""
    form = EditUserForm()
    if form.validate_on_submit():
        session = db_manager.get_session()
        try:
            user = session.query(User).get(form.user_id.data)
            if not user:
                flash('User not found', 'error')
                return redirect(url_for('user_management'))
            
            # Check if username or email already exists for another user
            existing_user = session.query(User).filter(
                ((User.username == form.username.data) | (User.email == form.email.data)) &
                (User.id != user.id)
            ).first()
            
            if existing_user:
                if existing_user.username == form.username.data:
                    flash(f'Username {form.username.data} is already taken', 'error')
                else:
                    flash(f'Email {form.email.data} is already registered', 'error')
                return redirect(url_for('user_management'))
            
            # Update user
            user.username = form.username.data
            user.email = form.email.data
            user.role = UserRole(form.role.data)
            user.is_active = form.is_active.data
            
            # Update password if provided
            if form.password.data:
                user.set_password(form.password.data)
            
            session.commit()
            flash(f'User {form.username.data} updated successfully', 'success')
        except SQLAlchemyError as e:
            session.rollback()
            app.logger.error(f"Database error updating user: {sanitize_for_log(str(e))}")
            flash('Database error updating user', 'error')
        except (ValueError, TypeError) as e:
            session.rollback()
            flash(f'Validation error: {sanitize_for_log(str(e))}', 'error')
        except Exception as e:
            session.rollback()
            app.logger.error(f"Unexpected error updating user: {sanitize_for_log(str(e))}")
            flash('An unexpected error occurred while updating the user', 'error')
        finally:
            session.close()
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')
    
    return redirect(url_for('user_management'))

@app.route('/delete_user', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@require_secure_connection
@with_session_error_handling
def delete_user():
    """Delete a user"""
    form = DeleteUserForm()
    if form.validate_on_submit():
        # Prevent deleting yourself
        if int(form.user_id.data) == current_user.id:
            flash('You cannot delete your own account', 'error')
            return redirect(url_for('user_management'))
        
        session = db_manager.get_session()
        try:
            user = session.query(User).get(form.user_id.data)
            if user:
                username = user.username
                session.delete(user)
                session.commit()
                flash(f'User {username} deleted successfully', 'success')
            else:
                flash('User not found', 'error')
        except SQLAlchemyError as e:
            session.rollback()
            app.logger.error(f"Database error deleting user: {sanitize_for_log(str(e))}")
            flash('Database error deleting user', 'error')
        except Exception as e:
            session.rollback()
            app.logger.error(f"Unexpected error deleting user: {sanitize_for_log(str(e))}")
            flash('An unexpected error occurred while deleting the user', 'error')
        finally:
            session.close()
    
    return redirect(url_for('user_management'))

# Health check endpoints
@app.route('/health')
@login_required
def health_check():
    """Basic health check endpoint"""
    try:
        # Simple health check - just verify we can connect to database
        session = db_manager.get_session()
        try:
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'vedfolnir'
            }), 200
        finally:
            session.close()
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': 'vedfolnir',
            'error': str(e)
        }), 503

@app.route('/health/detailed')
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def health_check_detailed():
    """Detailed health check endpoint"""
    try:
        # Run comprehensive health check with proper resource management
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            system_health = loop.run_until_complete(health_checker.check_system_health())
        except Exception as e:
            app.logger.error(f"Health check failed: {sanitize_for_log(str(e))}")
            raise
        finally:
            try:
                loop.close()
            except Exception as e:
                app.logger.warning(f"Error closing event loop: {sanitize_for_log(str(e))}")
        
        # Convert to dictionary for JSON response
        health_dict = health_checker.to_dict(system_health)
        
        # Return appropriate HTTP status code based on health
        status_code = 200
        if system_health.status.value == 'unhealthy':
            status_code = 503
        elif system_health.status.value == 'degraded':
            status_code = 200  # Still operational, but with issues
        
        return jsonify(health_dict), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': 'vedfolnir',
            'error': f'Health check failed: {str(e)}'
        }), 503

@app.route('/health/dashboard')
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def health_dashboard():
    """Health dashboard for system administrators"""
    try:
        # Run comprehensive health check with proper resource management
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            system_health = loop.run_until_complete(health_checker.check_system_health())
        except Exception as e:
            app.logger.error(f"Health dashboard check failed: {sanitize_for_log(str(e))}")
            raise
        finally:
            try:
                loop.close()
            except Exception as e:
                app.logger.warning(f"Error closing event loop: {sanitize_for_log(str(e))}")
        
        # Get error statistics for admin dashboard
        try:
            error_stats = error_recovery_manager.get_error_statistics()
            admin_notifications = error_recovery_manager.get_admin_notifications(unread_only=True)
        except Exception as e:
            app.logger.error(f"Error getting error statistics for dashboard: {sanitize_for_log(str(e))}")
            error_stats = {'total_errors': 0}
            admin_notifications = []
        
        return render_template('health_dashboard.html', 
                             health=system_health,
                             error_stats=error_stats,
                             admin_notifications=admin_notifications)
        
    except Exception as e:
        flash(f'Error loading health dashboard: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/health/components/<component_name>')
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def health_check_component(component_name):
    """Health check for a specific component"""
    try:
        # Map component names to health check methods
        component_checks = {
            'database': health_checker.check_database_health,
            'ollama': health_checker.check_ollama_health,
            'activitypub': health_checker.check_activitypub_health,
            'storage': health_checker.check_storage_health
        }
        
        if component_name not in component_checks:
            return jsonify({
                'error': f'Unknown component: {component_name}',
                'available_components': list(component_checks.keys())
            }), 404
        
        # Run specific component health check with proper resource management
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            component_health = loop.run_until_complete(component_checks[component_name]())
        except Exception as e:
            app.logger.error(f"Component health check failed for {component_name}: {sanitize_for_log(str(e))}")
            raise
        finally:
            try:
                loop.close()
            except Exception as e:
                app.logger.warning(f"Error closing event loop: {sanitize_for_log(str(e))}")
        
        # Convert to dictionary
        health_dict = {
            'name': component_health.name,
            'status': component_health.status.value,
            'message': component_health.message,
            'response_time_ms': component_health.response_time_ms,
            'last_check': component_health.last_check.isoformat() if component_health.last_check else None,
            'details': component_health.details
        }
        
        # Return appropriate HTTP status code
        status_code = 200
        if component_health.status.value == 'unhealthy':
            status_code = 503
        elif component_health.status.value == 'degraded':
            status_code = 200
        
        return jsonify(health_dict), status_code
        
    except Exception as e:
        return jsonify({
            'component': component_name,
            'status': 'unhealthy',
            'error': f'Component health check failed: {str(e)}',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 503




@app.route('/')
@login_required
@with_db_session
@require_platform_context
@with_session_error_handling
def index():
    """Main dashboard with platform-aware statistics and session management"""
    try:
        # Use request-scoped session for all database queries
        with request_session_manager.session_scope() as db_session:
            # Check if user has any platform connections first
            user_platforms = db_session.query(PlatformConnection).filter_by(
                user_id=current_user.id,
                is_active=True
            ).count()
            
            if user_platforms == 0:
                # Redirect to first-time setup if no platforms
                return redirect(url_for('first_time_setup'))
            
            # Get platform-specific statistics using session-aware context
            context = get_current_platform_context()
            current_platform = None
            
            if context and context.get('platform_connection_id'):
                current_platform = db_session.query(PlatformConnection).filter_by(
                    id=context['platform_connection_id'],
                    user_id=current_user.id,
                    is_active=True
                ).first()
            
            if current_platform:
                # Get platform-specific stats
                stats = db_manager.get_platform_processing_stats(current_platform.id)
                stats['platform_name'] = current_platform.name
                stats['platform_type'] = current_platform.platform_type
                # Convert to dict to avoid DetachedInstanceError
                platform_dict = {
                    'id': current_platform.id,
                    'name': current_platform.name,
                    'platform_type': current_platform.platform_type,
                    'instance_url': current_platform.instance_url,
                    'username': current_platform.username,
                    'is_default': current_platform.is_default
                }
            else:
                # Fallback to general stats
                stats = db_manager.get_processing_stats()
                platform_dict = None
            
            return render_template('index.html', stats=stats, current_platform=platform_dict)
            
    except Exception as e:
        app.logger.error(f"Error loading dashboard: {sanitize_for_log(str(e))}")
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('platform_management'))

@app.route('/admin/cleanup')
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def admin_cleanup():
    """Admin interface for data cleanup"""
    from scripts.maintenance.data_cleanup import DataCleanupManager
    
    # Get database statistics
    stats = db_manager.get_processing_stats()
    
    # Add processing runs count
    session = db_manager.get_session()
    try:
        stats['processing_runs'] = session.query(ProcessingRun).count()
        
        # Get list of unique user IDs from posts
        users = session.query(Post.user_id).distinct().all()
        user_ids = [user[0] for user in users if user[0]]
        
        # Get post counts for each user
        user_stats = []
        for user_id in user_ids:
            post_count = session.query(Post).filter(Post.user_id == user_id).count()
            image_count = session.query(Image).join(Post).filter(Post.user_id == user_id).count()
            user_stats.append({
                'user_id': user_id,
                'post_count': post_count,
                'image_count': image_count
            })
    finally:
        session.close()
    
    # Get retention configuration
    cleanup_manager = DataCleanupManager(db_manager, config)
    retention = cleanup_manager.default_retention
    
    return render_template('admin_cleanup.html', stats=stats, retention=retention, users=user_stats)

@app.route('/admin/cleanup/runs', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def admin_cleanup_runs():
    """Archive old processing runs"""
    from scripts.maintenance.data_cleanup import DataCleanupManager
    
    days = request.form.get('days', type=int)
    dry_run = 'dry_run' in request.form
    
    if not days or days < 1:
        flash('Invalid number of days', 'danger')
        return redirect(url_for('admin_cleanup'))
    
    cleanup_manager = DataCleanupManager(db_manager, config)
    try:
        count = cleanup_manager.archive_old_processing_runs(days=days, dry_run=dry_run)
        
        if dry_run:
            flash(f'Dry run: Would archive {count} processing runs older than {days} days', 'info')
        else:
            flash(f'Successfully archived {count} processing runs older than {days} days', 'success')
    except Exception as e:
        flash(f'Error archiving processing runs: {str(e)}', 'danger')
    
    return redirect(url_for('admin_cleanup'))

@app.route('/admin/cleanup/images', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def admin_cleanup_images():
    """Clean up old images"""
    from scripts.maintenance.data_cleanup import DataCleanupManager
    
    status_str = request.form.get('status')
    days = request.form.get('days', type=int)
    dry_run = 'dry_run' in request.form
    
    if not days or days < 1:
        flash('Invalid number of days', 'danger')
        return redirect(url_for('admin_cleanup'))
    
    # Map status string to ProcessingStatus enum
    status_map = {
        'rejected': ProcessingStatus.REJECTED,
        'posted': ProcessingStatus.POSTED,
        'error': ProcessingStatus.ERROR
    }
    
    status = status_map.get(status_str)
    if not status:
        flash('Invalid status', 'danger')
        return redirect(url_for('admin_cleanup'))
    
    cleanup_manager = DataCleanupManager(db_manager, config)
    try:
        count = cleanup_manager.cleanup_old_images(status=status, days=days, dry_run=dry_run)
        
        if dry_run:
            flash(f'Dry run: Would clean up {count} {status.value} images older than {days} days', 'info')
        else:
            flash(f'Successfully cleaned up {count} {status.value} images older than {days} days', 'success')
    except ValueError as e:
        flash(f'Invalid parameters: {sanitize_for_log(str(e))}', 'danger')
    except Exception as e:
        logger.error(f"Unexpected error cleaning up images: {sanitize_for_log(str(e))}")
        flash('An unexpected error occurred during cleanup', 'danger')
    
    return redirect(url_for('admin_cleanup'))

@app.route('/admin/cleanup/posts', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def admin_cleanup_posts():
    """Clean up orphaned posts"""
    from scripts.maintenance.data_cleanup import DataCleanupManager
    
    dry_run = 'dry_run' in request.form
    
    cleanup_manager = DataCleanupManager(db_manager, config)
    try:
        count = cleanup_manager.cleanup_orphaned_posts(dry_run=dry_run)
        
        if dry_run:
            flash(f'Dry run: Would clean up {count} orphaned posts', 'info')
        else:
            flash(f'Successfully cleaned up {count} orphaned posts', 'success')
    except Exception as e:
        logger.error(f"Unexpected error cleaning up posts: {sanitize_for_log(str(e))}")
        flash('An unexpected error occurred during post cleanup', 'danger')
    
    return redirect(url_for('admin_cleanup'))

@app.route('/admin/cleanup/orphan_runs', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def admin_cleanup_orphan_runs():
    """Clean up orphan processing runs"""
    from scripts.maintenance.data_cleanup import DataCleanupManager
    
    hours = request.form.get('hours', type=float)
    dry_run = request.form.get('dry_run') == 'true'
    
    if not hours or hours <= 0:
        flash('Invalid number of hours (must be greater than 0)', 'danger')
        return redirect(url_for('admin_cleanup'))
    
    cleanup_manager = DataCleanupManager(db_manager, config)
    
    try:
        result = cleanup_manager.cleanup_orphan_processing_runs(hours=hours, dry_run=dry_run)
        
        if dry_run:
            flash(f'Dry run completed: Would delete {result["deleted"]} orphan processing runs', 'info')
        else:
            flash(f'Successfully deleted {result["deleted"]} orphan processing runs', 'success')
            
        if result['errors'] > 0:
            flash(f'Encountered {result["errors"]} errors during cleanup', 'warning')
            
    except Exception as e:
        logger.error(f"Error during orphan processing runs cleanup: {e}")
        flash('An unexpected error occurred during orphan processing runs cleanup', 'danger')
    
    return redirect(url_for('admin_cleanup'))

@app.route('/admin/cleanup/user', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def admin_cleanup_user():
    """Clean up all data for a specific user"""
    from scripts.maintenance.data_cleanup import DataCleanupManager
    
    user_id = request.form.get('user_id')
    dry_run = 'dry_run' in request.form
    
    if not user_id:
        flash('Please select a user', 'danger')
        return redirect(url_for('admin_cleanup'))
    
    cleanup_manager = DataCleanupManager(db_manager, config)
    try:
        results = cleanup_manager.cleanup_user_data(user_id=user_id, dry_run=dry_run)
        
        if dry_run:
            flash(f'Dry run: Would delete {results["posts"]} posts, {results["images"]} images, and {results["runs"]} processing runs for user {user_id}', 'info')
        else:
            flash(f'Successfully deleted {results["posts"]} posts, {results["images"]} images, and {results["runs"]} processing runs for user {user_id}', 'success')
    except ValueError as e:
        flash(f'Invalid user ID: {sanitize_for_log(str(e))}', 'danger')
    except Exception as e:
        logger.error(f"Unexpected error cleaning up user data: {sanitize_for_log(str(e))}")
        flash('An unexpected error occurred during user data cleanup', 'danger')
    
    return redirect(url_for('admin_cleanup'))

@app.route('/admin/cleanup/all', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def admin_cleanup_all():
    """Run full cleanup"""
    from scripts.maintenance.data_cleanup import DataCleanupManager
    
    dry_run = 'dry_run' in request.form
    
    cleanup_manager = DataCleanupManager(db_manager, config)
    try:
        results = cleanup_manager.run_full_cleanup(dry_run=dry_run)
        
        total_items = sum(results.values())
        
        if dry_run:
            flash(f'Dry run: Would clean up {total_items} items (database: {results["archived_runs"] + results["cleaned_rejected"] + results["cleaned_posted"] + results["cleaned_error"] + results["cleaned_posts"]}, storage: {results["deleted_images"]}, logs: {results["deleted_logs"]})', 'info')
        else:
            flash(f'Successfully cleaned up {total_items} items (database: {results["archived_runs"] + results["cleaned_rejected"] + results["cleaned_posted"] + results["cleaned_error"] + results["cleaned_posts"]}, storage: {results["deleted_images"]}, logs: {results["deleted_logs"]})', 'success')
    except Exception as e:
        logger.error(f"Unexpected error during full cleanup: {sanitize_for_log(str(e))}")
        flash('An unexpected error occurred during full cleanup', 'danger')
    
    return redirect(url_for('admin_cleanup'))


@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve stored images"""
    return send_from_directory(config.storage.images_dir, filename)

@app.route('/review')
@login_required
@platform_required
@with_session_error_handling
def review_list():
    """List images pending review (platform-aware)"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    session = db_manager.get_session()
    try:
        # Get current user's platform context
        current_platform = None
        user_platforms = session.query(PlatformConnection).filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(PlatformConnection.is_default.desc(), PlatformConnection.name).all()
        
        for platform in user_platforms:
            if platform.is_default:
                current_platform = platform
                break
        if not current_platform and user_platforms:
            current_platform = user_platforms[0]
        
        # Build platform-aware query with eager loading to avoid DetachedInstanceError
        query = session.query(Image).options(
            joinedload(Image.platform_connection),
            joinedload(Image.post)
        ).filter_by(status=ProcessingStatus.PENDING)
        
        # Apply platform filtering
        platform_filter = request.args.get('platform')
        if platform_filter == 'all':
            # Show all platforms for this user
            if user_platforms:
                platform_ids = [p.id for p in user_platforms]
                query = query.filter(
                    (Image.platform_connection_id.in_(platform_ids)) |
                    (Image.platform_connection_id.is_(None))  # Include legacy data
                )
        elif platform_filter and platform_filter.isdigit():
            # Filter by specific platform
            platform_id = int(platform_filter)
            if any(p.id == platform_id for p in user_platforms):
                query = query.filter(Image.platform_connection_id == platform_id)
        elif current_platform:
            # Default to current platform
            query = query.filter(
                (Image.platform_connection_id == current_platform.id) |
                (Image.platform_connection_id.is_(None))  # Include legacy data
            )
        
        # Apply other filters
        post_id = request.args.get('post_id')
        if post_id:
            query = query.filter(Image.post_id == post_id)
        
        # Sort by most recent first (original post date descending, fallback to updated_at)
        query = query.order_by(Image.original_post_date.desc().nullslast(), Image.updated_at.desc())
        
        total = query.count()
        images = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Calculate pagination
        has_prev = page > 1
        has_next = (page * per_page) < total
        
        # Convert platforms to dicts to avoid DetachedInstanceError
        user_platforms_dict = [{
            'id': p.id,
            'name': p.name,
            'platform_type': p.platform_type,
            'instance_url': p.instance_url,
            'username': p.username,
            'is_default': p.is_default,
            'is_active': p.is_active
        } for p in user_platforms]
        
        current_platform_dict = None
        if current_platform:
            current_platform_dict = {
                'id': current_platform.id,
                'name': current_platform.name,
                'platform_type': current_platform.platform_type,
                'instance_url': current_platform.instance_url,
                'username': current_platform.username,
                'is_default': current_platform.is_default,
                'is_active': current_platform.is_active
            }
        
        return render_template('review.html', 
                             images=images,
                             page=page,
                             per_page=per_page,
                             total=total,
                             has_prev=has_prev,
                             has_next=has_next,
                             current_platform=current_platform_dict,
                             user_platforms=user_platforms_dict,
                             selected_platform=platform_filter)
    finally:
        session.close()

@app.route('/review/<int:image_id>')
@login_required
@with_session_error_handling
def review_single(image_id):
    """Review a single image"""
    session = db_manager.get_session()
    try:
        image = session.query(Image).options(
            joinedload(Image.platform_connection),
            joinedload(Image.post)
        ).filter_by(id=image_id).first()
        if not image:
            flash(f'Image with ID {image_id} not found', 'error')
            return redirect(url_for('review_list'))
            
        form = ReviewForm()
        form.image_id.data = image_id
        form.caption.data = image.generated_caption or ""
        
        return render_template('review_single.html', image=image, form=form)
    finally:
        session.close()

@app.route('/review/<int:image_id>', methods=['POST'])
@login_required
@validate_input_length()
@with_session_error_handling
def review_submit(image_id):
    """Submit review for an image"""
    form = ReviewForm()
    
    if form.validate_on_submit():
        # Determine status based on action
        status_map = {
            'approve': ProcessingStatus.APPROVED,
            'reject': ProcessingStatus.REJECTED,
            'edit': ProcessingStatus.PENDING
        }
        
        status = status_map.get(form.action.data, ProcessingStatus.PENDING)
        
        # Sanitize input data before database update
        sanitized_caption = sanitize_html_input(form.caption.data) if form.caption.data else ""
        sanitized_notes = sanitize_html_input(form.notes.data) if form.notes.data else ""
        
        # Update image in database
        success = db_manager.review_image(
            image_id=image_id,
            reviewed_caption=sanitized_caption,
            status=status,
            reviewer_notes=sanitized_notes
        )
        
        if success:
            from markupsafe import escape
            flash(f'Image review submitted successfully! Status: {escape(status.value)}', 'success')
        else:
            flash('Error submitting review. Image may not exist.', 'error')
        
        # Redirect to next image or review list
        next_url = request.args.get('next', url_for('review_list'))
        return redirect(next_url)
    
    # If form validation failed, show errors
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{field}: {error}', 'error')
    
    return redirect(url_for('review_single', image_id=image_id))

@app.route('/batch_review')
@login_required
@platform_required
@with_session_error_handling
def batch_review():
    """Batch review interface with filtering, sorting, and pagination"""
    session = db_manager.get_session()
    try:
        # Get current platform context
        context = get_current_platform_context()
        if not context or not context.get('platform_connection_id'):
            flash('No active platform connection found.', 'error')
            return redirect(url_for('platform_management'))
        
        platform_connection_id = context['platform_connection_id']
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        sort_by = request.args.get('sort_by', 'original_post_date')
        sort_order = request.args.get('sort_order', 'desc')
        category = request.args.get('category')
        quality_score = request.args.get('quality_score')
        needs_review = request.args.get('needs_review')
        post_id = request.args.get('post_id')
        
        # Build the query with eager loading to avoid DetachedInstanceError
        query = session.query(Image).options(
            joinedload(Image.platform_connection),
            joinedload(Image.post)
        ).filter_by(status=ProcessingStatus.PENDING)
        
        # Apply platform filtering - only show images for current platform
        query = query.filter(
            (Image.platform_connection_id == platform_connection_id) |
            (Image.platform_connection_id.is_(None))  # Include legacy data
        )
        
        # Apply filters
        # Category filtering removed as part of simplification
        
        if quality_score:
            try:
                quality_threshold = int(quality_score)
                if quality_threshold > 0:
                    query = query.filter(Image.caption_quality_score <= quality_threshold)
            except (ValueError, TypeError):
                pass
        
        if needs_review == 'yes':
            query = query.filter(Image.needs_special_review == True)
        
        if post_id:
            query = query.filter(Image.post_id == post_id)
        
        # Categories removed as part of simplification
        categories = []
        
        # Apply sorting
        if sort_by == 'quality_score':
            if sort_order == 'asc':
                query = query.order_by(Image.caption_quality_score.asc())
            else:
                query = query.order_by(Image.caption_quality_score.desc())
        elif sort_by == 'created_at':
            if sort_order == 'asc':
                query = query.order_by(Image.created_at.asc())
            else:
                query = query.order_by(Image.created_at.desc())
        elif sort_by == 'updated_at':
            if sort_order == 'asc':
                query = query.order_by(Image.updated_at.asc())
            else:
                query = query.order_by(Image.updated_at.desc())
        else:  # Default to original_post_date (original post creation date)
            if sort_order == 'asc':
                query = query.order_by(Image.original_post_date.asc().nullslast(), Image.updated_at.asc())
            else:
                query = query.order_by(Image.original_post_date.desc().nullslast(), Image.updated_at.desc())
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        images = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Calculate pagination values
        total_pages = (total_count + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        # Prepare pagination data for template
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next
        }
        
        # Prepare filter data for template
        filters = {
            'category': category,
            'quality_score': quality_score,
            'needs_review': needs_review,
            'post_id': post_id,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'available_categories': categories
        }
        
        return render_template('batch_review.html', 
                              images=images, 
                              pagination=pagination,
                              filters=filters)
    finally:
        session.close()

@app.route('/api/batch_review', methods=['POST'])
@login_required
@with_session_error_handling
def api_batch_review():
    """API endpoint for batch review"""
    data = request.get_json()
    
    if not data or 'reviews' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    
    results = []
    for review in data['reviews']:
        image_id = review.get('image_id')
        caption = review.get('caption')
        action = review.get('action')
        notes = review.get('notes', '')
        
        status_map = {
            'approve': ProcessingStatus.APPROVED,
            'reject': ProcessingStatus.REJECTED,
            'edit': ProcessingStatus.PENDING
        }
        
        status = status_map.get(action, ProcessingStatus.PENDING)
        
        success = db_manager.review_image(
            image_id=image_id,
            reviewed_caption=caption,
            status=status,
            reviewer_notes=notes
        )
        
        results.append({
            'image_id': image_id,
            'success': success,
            'status': status.value
        })
    
    return jsonify({'results': results})

@app.route('/api/update_caption/<int:image_id>', methods=['POST'])
@login_required
@enhanced_input_validation
@with_session_error_handling
def api_update_caption(image_id):
    """API endpoint for updating and optionally posting a caption"""
    data = request.get_json()
    
    if not data or 'caption' not in data or 'action' not in data:
        return jsonify({'success': False, 'error': 'Invalid data'}), 400
    
    caption = data['caption']
    action = data['action']
    
    # Map action to status
    status_map = {
        'approve': ProcessingStatus.APPROVED,
        'reject': ProcessingStatus.REJECTED,
        'edit': ProcessingStatus.PENDING
    }
    
    if action not in status_map:
        return jsonify({'success': False, 'error': f'Invalid action: {action}'}), 400
    
    status = status_map[action]
    
    # First, get the image data we need
    session = db_manager.get_session()
    image_data = None
    platform_config = None
    try:
        image = session.query(Image).options(
            joinedload(Image.platform_connection),
            joinedload(Image.post)
        ).filter_by(id=image_id).first()
        if not image:
            return jsonify({'success': False, 'error': 'Image not found'}), 404
        
        # Get platform connection for authentication
        platform_connection = image.platform_connection
        if not platform_connection:
            return jsonify({'success': False, 'error': 'No platform connection found for image'}), 400
        
        # Extract platform config before session closes
        platform_config = platform_connection.to_activitypub_config()
        if not platform_config:
            return jsonify({'success': False, 'error': 'Failed to create platform config'}), 400
        
        # Update image
        image.reviewed_caption = caption
        image.final_caption = caption
        image.status = status
        image.reviewed_at = datetime.now(timezone.utc)
        
        # Extract necessary data before committing and potentially closing the session
        if status == ProcessingStatus.APPROVED and image.image_post_id:
            image_data = {
                'id': image.id,
                'image_post_id': image.image_post_id,
                'final_caption': caption,  # Use the new caption
                'reviewed_caption': caption,
                'image_url': image.image_url,
                'post_url': image.post.post_url if image.post else None
            }
        
        # Commit the changes
        session.commit()
    except Exception as e:
        session.rollback()
        app.logger.error(f"Error updating caption: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()
    
    # If approved and we have image data, post to platform
    posted = False
    if status == ProcessingStatus.APPROVED and image_data and image_data['image_post_id'] and platform_config:
        try:
            # Post to platform using platform-aware client
            async def post_caption():
                try:
                    async with ActivityPubClient(platform_config) as ap_client:
                        caption = image_data['final_caption'] or image_data['reviewed_caption']
                        
                        # Check if this is Mastodon and we need to use status edit API
                        if platform_config.api_type == 'mastodon':
                            # For Mastodon, we need the status ID from the post URL
                            if image_data.get('post_url'):
                                try:
                                    status_id = image_data['post_url'].split('/')[-1]
                                    if status_id.isdigit():
                                        # Use Mastodon's status edit API
                                        return await ap_client.platform.update_status_media_caption(
                                            ap_client, status_id, image_data['image_post_id'], caption
                                        )
                                    else:
                                        app.logger.warning(f"Could not extract numeric status ID from URL: {image_data['post_url']}")
                                        return False
                                except Exception as e:
                                    app.logger.error(f"Error extracting status ID from URL {image_data.get('post_url', 'None')}: {e}")
                                    return False
                            else:
                                app.logger.warning(f"No post URL available for Mastodon media update: {image_data['image_post_id']}")
                                return False
                        else:
                            # For other platforms (Pixelfed), use direct media update
                            return await ap_client.update_media_caption(
                                image_data['image_post_id'], caption
                            )
                except Exception as e:
                    app.logger.error(f"Error posting caption to platform: {str(e)}")
                    return False
            
            # Run async function with proper resource management
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(post_caption())
            except Exception as e:
                app.logger.error(f"Async caption posting failed: {sanitize_for_log(str(e))}")
                success = False
            finally:
                try:
                    loop.close()
                except Exception as e:
                    app.logger.warning(f"Error closing event loop: {sanitize_for_log(str(e))}")
            
            # If successful, mark as posted using the DatabaseManager method
            if success:
                posted = True
                try:
                    # Use the proper method to mark the image as posted
                    db_manager.mark_image_posted(image_id)
                    app.logger.info(f"Image {sanitize_for_log(str(image_id))} marked as posted successfully")
                except Exception as e:
                    app.logger.error(f"Error marking image as posted: {str(e)}")
            else:
                # Log the failure but don't treat expired media as an error
                app.logger.warning(f"Failed to update media caption for image {sanitize_for_log(str(image_id))} - media may be expired")
                posted = False
        except Exception as e:
            app.logger.error(f"Error in async operation: {str(e)}")
    
    return jsonify({
        'success': True,
        'status': status.value,
        'posted': posted
    })

@app.route('/api/regenerate_caption/<int:image_id>', methods=['POST'])
@login_required
@with_session_error_handling
def api_regenerate_caption(image_id):
    """API endpoint to regenerate caption for an image"""
    session = db_manager.get_session()
    try:
        image = session.query(Image).options(
            joinedload(Image.platform_connection),
            joinedload(Image.post)
        ).filter_by(id=image_id).first()
        if not image:
            return jsonify({
                'success': False,
                'error': f'Image with ID {image_id} not found'
            }), 404
        
        # Verify user has access to this image's platform
        if image.platform_connection and image.platform_connection.user_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Access denied to this image'
            }), 403
        
        # Initialize caption generator
        caption_generator = OllamaCaptionGenerator(config.ollama)
        
        try:
            # Log model information
            model_info = caption_generator.get_model_info()
            if model_info:
                app.logger.info(f"Using Ollama model: {sanitize_for_log(config.ollama.model_name)}")
                app.logger.info(f"Model size: {model_info.get('size', 'unknown')}")
                app.logger.info(f"Model last modified: {model_info.get('modified_at', 'unknown')}")
            else:
                app.logger.warning(f"Model information not available for {config.ollama.model_name}")
                
            app.logger.info(f"Ollama endpoint: {sanitize_for_log(config.ollama.url)}")
            app.logger.info(f"Ollama timeout: {sanitize_for_log(str(config.ollama.timeout))}s")
            # Create a new event loop for async operations with proper resource management
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                # Generate new caption with general prompt (classification removed)
                result = loop.run_until_complete(caption_generator.generate_caption(image.local_path))
            except Exception as e:
                app.logger.error(f"Caption generation failed: {sanitize_for_log(str(e))}")
                raise
            finally:
                try:
                    loop.close()
                except Exception as e:
                    app.logger.warning(f"Error closing event loop: {sanitize_for_log(str(e))}")
            
            # Handle the result which can be either just a caption (old format) or a tuple of (caption, quality_metrics)
            if isinstance(result, tuple) and len(result) == 2:
                new_caption, quality_metrics = result
                app.logger.info(f"Caption quality score: {sanitize_for_log(str(quality_metrics['overall_score']))}/100 ({sanitize_for_log(quality_metrics['quality_level'])})")
                if quality_metrics['needs_review']:
                    app.logger.warning(f"Caption flagged for special review: {sanitize_for_log(quality_metrics['feedback'])}")
            else:
                new_caption = result
                # Use our quality manager to assess the caption if no metrics were provided
                quality_metrics = quality_manager.assess_caption_quality(
                    caption=new_caption,
                    prompt_used="general"
                )
                app.logger.info(f"Caption quality assessed: {sanitize_for_log(str(quality_metrics['overall_score']))}/100 ({sanitize_for_log(quality_metrics['quality_level'])})")
            
            if new_caption:
                # Update image in database
                image.generated_caption = new_caption
                image.prompt_used = "general"
                image.updated_at = datetime.now(timezone.utc)
                
                # Update quality metrics if available
                if quality_metrics:
                    image.caption_quality_score = quality_metrics.get('overall_score', 0)
                    image.needs_special_review = quality_metrics.get('needs_review', False)
                    image.reviewer_notes = quality_metrics.get('feedback', '')
                
                session.commit()
                
                # Prepare response with quality metrics if available
                response_data = {
                    'success': True,
                    'image_id': image_id,
                    'caption': new_caption,
                    'category': 'general'
                }
                
                # Add quality metrics to the response if available
                if quality_metrics:
                    response_data['quality'] = {
                        'score': quality_metrics['overall_score'],
                        'level': quality_metrics['quality_level'],
                        'needs_review': quality_metrics['needs_review'],
                        'feedback': quality_metrics['feedback']
                    }
                
                return jsonify(response_data)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to generate caption'
                }), 500
        finally:
            # Clean up model resources
            caption_generator.cleanup()
            
    except Exception as e:
        session.rollback()
        app.logger.error(f"Error regenerating caption: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()

@app.route('/post_approved')
@login_required
@with_session_error_handling
def post_approved():
    """Post approved captions to platform"""
    # Get current platform context
    context = get_current_platform_context()
    if not context or not context.get('platform_connection_id'):
        flash('No active platform connection found.', 'error')
        return redirect(url_for('platform_management'))
    
    platform_connection_id = context['platform_connection_id']
    
    # Get the image IDs first, so we don't keep the session open during async operations
    session = db_manager.get_session()
    try:
        # Only get approved images for the current platform
        approved_images = session.query(Image).options(
            joinedload(Image.platform_connection),
            joinedload(Image.post)
        ).filter_by(
            status=ProcessingStatus.APPROVED,
            platform_connection_id=platform_connection_id
        ).order_by(Image.original_post_date.desc().nullslast(), Image.updated_at.desc()).limit(10).all()
        
        if not approved_images:
            flash('No approved images to post for current platform', 'info')
            return redirect(url_for('index'))
        
        # Get platform connection for authentication
        platform_connection = approved_images[0].platform_connection
        if not platform_connection:
            flash('Platform connection not found', 'error')
            return redirect(url_for('platform_management'))
        
        # Extract platform config before session closes
        platform_config = platform_connection.to_activitypub_config()
        if not platform_config:
            flash('Failed to create platform config', 'error')
            return redirect(url_for('platform_management'))
            
        # Extract the necessary data from images before closing the session
        image_data = []
        for image in approved_images:
            image_data.append({
                'id': image.id,
                'image_post_id': image.image_post_id,
                'final_caption': image.final_caption,
                'reviewed_caption': image.reviewed_caption,
                'image_url': image.image_url,
                'post_url': image.post.post_url if image.post else None
            })
    finally:
        session.close()
    
    # Post captions to platform
    posted_count = 0
    successful_image_ids = []
    
    # Create an async function to handle the posting
    async def post_captions():
        nonlocal posted_count, successful_image_ids
        try:
            async with ActivityPubClient(platform_config) as ap_client:
                for img_data in image_data:
                    try:
                        if img_data['image_post_id']:
                            caption = img_data['final_caption'] or img_data['reviewed_caption']
                            
                            # Check if this is Mastodon and we need to use status edit API
                            if platform_config.api_type == 'mastodon':
                                # For Mastodon, we need the status ID from the post URL
                                # Extract status ID from post URL (e.g., https://mastodon.social/@user/123456)
                                status_id = None
                                if 'post_url' in img_data and img_data['post_url']:
                                    try:
                                        status_id = img_data['post_url'].split('/')[-1]
                                        if status_id.isdigit():
                                            # Use Mastodon's status edit API
                                            success = await ap_client.platform.update_status_media_caption(
                                                ap_client, status_id, img_data['image_post_id'], caption
                                            )
                                        else:
                                            logger.warning(f"Could not extract numeric status ID from URL: {img_data['post_url']}")
                                            success = False
                                    except Exception as e:
                                        logger.error(f"Error extracting status ID from URL {img_data.get('post_url', 'None')}: {e}")
                                        success = False
                                else:
                                    logger.warning(f"No post URL available for Mastodon media update: {img_data['image_post_id']}")
                                    success = False
                            else:
                                # For other platforms (Pixelfed), use direct media update
                                success = await ap_client.update_media_caption(img_data['image_post_id'], caption)
                        else:
                            # Fallback to the old method
                            success = update_platform_media_description(img_data, platform_config)
                            
                        # Track successful updates
                        if success:
                            successful_image_ids.append(img_data['id'])
                            posted_count += 1
                        else:
                            # Log but don't count failed updates
                            app.logger.warning(f"Media update failed for image {img_data['id']} - likely expired media")
                            # Don't add to successful_image_ids if update failed
                    except Exception as e:
                        app.logger.error(f"Error updating caption for image {img_data['id']}: {str(e)}")
                        continue
        except Exception as e:
            app.logger.error(f"Error initializing ActivityPubClient: {str(e)}")
    
    # Run the async function with proper resource management
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(post_captions())
    except Exception as e:
        app.logger.error(f"Async caption posting failed: {sanitize_for_log(str(e))}")
    finally:
        try:
            loop.close()
        except Exception as e:
            app.logger.warning(f"Error closing event loop: {sanitize_for_log(str(e))}")
    
    # Update the database with successful posts - use direct SQL update instead of ORM
    if successful_image_ids:
        try:
            session = db_manager.get_session()
            try:
                # Use direct SQL update to avoid ORM session issues
                from sqlalchemy import text
                ids_str = ','.join(str(id) for id in successful_image_ids)
                sql = text(f"UPDATE images SET status = 'posted', posted_at = CURRENT_TIMESTAMP WHERE id IN ({ids_str})")
                session.execute(sql)
                session.commit()
                app.logger.info(f"Successfully marked {sanitize_for_log(str(len(successful_image_ids)))} images as posted")
            except Exception as e:
                session.rollback()
                app.logger.error(f"Error updating image status: {str(e)}")
            finally:
                session.close()
        except Exception as e:
            app.logger.error(f"Error getting database session: {str(e)}")
    
    flash(f'Successfully posted {posted_count} of {len(image_data)} approved captions', 'success')
    return redirect(url_for('index'))

def update_platform_media_description(image_data, platform_config):
    """Update media description on platform using platform config"""
    try:
        import httpx
        import logging
        logger = logging.getLogger(__name__)
        
        headers = {
            'Authorization': f'Bearer {platform_config.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Use the stored image_post_id from the database
        if not image_data['image_post_id']:
            logger.error(f"No image_post_id available for image: {image_data['image_url']}")
            return False
        
        # Update media description using platform API
        url = f"{platform_config.instance_url}/api/v1/media/{image_data['image_post_id']}"
        caption = image_data['final_caption'] or image_data['reviewed_caption']
        data = {'description': caption}
        
        logger.info(f"Updating media {sanitize_for_log(str(image_data['image_post_id']))} with caption: {sanitize_for_log(str(caption)[:50])}...")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.put(url, headers=headers, json=data)
            response.raise_for_status()
            
        logger.info(f"Successfully updated media description for {image_data['image_url']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update media description for {image_data['image_url']}: {e}")
        return False

# Platform Management Routes
@app.route('/platform_management')
@login_required
@with_session_error_handling
def platform_management():
    """Platform management interface"""
    session = db_manager.get_session()
    try:
        # Get user's platform connections
        user_platforms = session.query(PlatformConnection).filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(PlatformConnection.is_default.desc(), PlatformConnection.name).all()
        
        # Get current platform (default or first available)
        current_platform = None
        for platform in user_platforms:
            if platform.is_default:
                current_platform = platform
                break
        if not current_platform and user_platforms:
            current_platform = user_platforms[0]
        
        # Get platform statistics if we have a current platform
        platform_stats = {}
        if current_platform:
            user_summary = db_manager.get_user_platform_summary(current_user.id)
            for platform_info in user_summary['platforms']:
                if platform_info['id'] == current_platform.id:
                    platform_stats = platform_info['stats']
                    break
        
        # Convert platforms to dicts to avoid DetachedInstanceError
        user_platforms_dict = [{
            'id': p.id,
            'name': p.name,
            'platform_type': p.platform_type,
            'instance_url': p.instance_url,
            'username': p.username,
            'is_default': p.is_default,
            'is_active': p.is_active
        } for p in user_platforms]
        
        current_platform_dict = None
        if current_platform:
            current_platform_dict = {
                'id': current_platform.id,
                'name': current_platform.name,
                'platform_type': current_platform.platform_type,
                'instance_url': current_platform.instance_url,
                'username': current_platform.username,
                'is_default': current_platform.is_default,
                'is_active': current_platform.is_active
            }
        
        return render_template('platform_management.html', 
                             user_platforms=user_platforms_dict,
                             current_platform=current_platform_dict,
                             platform_stats=platform_stats)
    finally:
        session.close()

@app.route('/switch_platform/<int:platform_id>')
@login_required
@with_session_error_handling
def switch_platform(platform_id):
    """Switch to a different platform"""
    try:
        # Verify the platform belongs to the current user
        db_session = db_manager.get_session()
        try:
            platform = db_session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if not platform:
                flash('Platform not found or not accessible', 'error')
                return redirect(url_for('platform_management'))
            
            # Check for active caption generation tasks and cancel them
            try:
                caption_service = WebCaptionGenerationService(db_manager)
                active_task = caption_service.task_queue_manager.get_user_active_task(current_user.id)
                
                if active_task:
                    # Cancel the active task
                    cancelled = caption_service.cancel_generation(active_task.id, current_user.id)
                    if cancelled:
                        flash('Active caption generation task was cancelled due to platform switch.', 'warning')
                        app.logger.info(f"Cancelled active caption generation task {sanitize_for_log(active_task.id)} due to platform switch")
                    else:
                        app.logger.warning(f"Failed to cancel active caption generation task {sanitize_for_log(active_task.id)} during platform switch")
            except Exception as e:
                app.logger.error(f"Error handling active caption generation task during platform switch: {sanitize_for_log(str(e))}")
            
            # Update database session platform context
            flask_session_id = session.get('_id')
            success = False
            if flask_session_id:
                success = session_manager.update_platform_context(flask_session_id, platform_id)
            if success:
                flash(f'Switched to platform: {platform.name}', 'success')
                app.logger.info(f"User {sanitize_for_log(current_user.username)} switched to platform {sanitize_for_log(platform.name)}")
            else:
                flash('Failed to switch platform', 'error')
            
        finally:
            db_session.close()
            
    except Exception as e:
        app.logger.error(f"Error switching platform: {e}")
        flash('Error switching platform', 'error')
    
    # Redirect back to the referring page or platform management
    return redirect(request.referrer or url_for('platform_management'))

@app.route('/api/add_platform', methods=['POST'])
@login_required
@validate_csrf_token
@enhanced_input_validation
@with_session_error_handling
def api_add_platform():
    """Add a new platform connection"""
    try:
        # Handle JSON parsing with better error handling
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            app.logger.error(f"JSON parsing error: {str(json_error)}")
            return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
        
        # Validate JSON data exists
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['name', 'platform_type', 'instance_url', 'access_token']
        for field in required_fields:
            if not data.get(field) or not str(data.get(field)).strip():
                return jsonify({'success': False, 'error': f'Missing or empty required field: {field}'}), 400
        
        # Validate field formats and constraints
        validation_errors = []
        
        # Validate name
        name = str(data['name']).strip()
        if len(name) < 1 or len(name) > 100:
            validation_errors.append('Platform name must be between 1 and 100 characters')
        
        # Validate platform type
        platform_type = str(data['platform_type']).strip().lower()
        valid_platforms = ['pixelfed', 'mastodon']
        if platform_type not in valid_platforms:
            validation_errors.append(f'Platform type must be one of: {", ".join(valid_platforms)}')
        
        # Validate instance URL
        instance_url = str(data['instance_url']).strip()
        if not instance_url.startswith(('http://', 'https://')):
            validation_errors.append('Instance URL must start with http:// or https://')
        if len(instance_url) > 500:
            validation_errors.append('Instance URL must be less than 500 characters')
        
        # Validate access token
        access_token = str(data['access_token']).strip()
        if len(access_token) < 10:
            validation_errors.append('Access token appears to be too short (minimum 10 characters)')
        
        # Validate username if provided
        username = data.get('username')
        if username:
            username = str(username).strip()
            if len(username) > 200:
                validation_errors.append('Username must be less than 200 characters')
        
        # Mastodon no longer requires client credentials - only access token needed
        
        # Return validation errors if any
        if validation_errors:
            return jsonify({
                'success': False, 
                'error': 'Validation failed: ' + '; '.join(validation_errors)
            }), 400
        
        # Check for duplicate platform connections
        session = db_manager.get_session()
        try:
            existing_platform = session.query(PlatformConnection).filter_by(
                user_id=current_user.id,
                name=name
            ).first()
            
            if existing_platform:
                return jsonify({
                    'success': False, 
                    'error': f'A platform connection with the name "{name}" already exists'
                }), 400
            
            # Check for duplicate instance/username combination
            existing_instance = session.query(PlatformConnection).filter_by(
                user_id=current_user.id,
                instance_url=instance_url,
                username=username
            ).first()
            
            if existing_instance:
                return jsonify({
                    'success': False, 
                    'error': f'A connection to this instance with this username already exists'
                }), 400
        finally:
            session.close()
        
        # Check if this is the user's first platform connection
        session = db_manager.get_session()
        try:
            existing_platforms_count = session.query(PlatformConnection).filter_by(
                user_id=current_user.id,
                is_active=True
            ).count()
            is_first_platform = existing_platforms_count == 0
        finally:
            session.close()
        
        # Create platform connection (set as default if it's the first one)
        platform = db_manager.create_platform_connection(
            user_id=current_user.id,
            name=name,
            platform_type=platform_type,
            instance_url=instance_url,
            username=username,
            access_token=access_token,
            client_key=data.get('client_key'),
            client_secret=data.get('client_secret'),
            is_default=is_first_platform  # Set as default if it's the first platform
        )
        
        if not platform:
            return jsonify({
                'success': False, 
                'error': 'Failed to create platform connection. Please check your input and try again.'
            }), 500
        
        # Test connection if requested
        test_connection = data.get('test_connection', True)
        app.logger.info(f"Test connection requested: {sanitize_for_log(str(test_connection))}")
        
        if test_connection:
            app.logger.info(f"Testing connection for platform {sanitize_for_log(name)} ({sanitize_for_log(platform_type)})")
            success, message = platform.test_connection()
            app.logger.info(f"Connection test result: success={sanitize_for_log(str(success))}, message={sanitize_for_log(message)}")
            
            if not success:
                # Delete the platform if connection test fails
                session = db_manager.get_session()
                try:
                    session.delete(platform)
                    session.commit()
                finally:
                    session.close()
                from markupsafe import escape
                return jsonify({'success': False, 'error': f'Connection test failed: {escape(message)}'}), 400
        else:
            app.logger.info(f"Skipping connection test for platform {sanitize_for_log(name)} as requested by user")
        
        # If this is the first platform, automatically switch to it
        if is_first_platform:
            try:
                from flask import session as flask_session
                flask_session_id = flask_session.get('_id')
                success = False
                if flask_session_id:
                    success = session_manager.update_platform_context(flask_session_id, platform.id)
                if success:
                    app.logger.info(f"Automatically switched to first platform {sanitize_for_log(name)} for user {sanitize_for_log(current_user.username)}")
                else:
                    app.logger.error(f"Failed to switch to first platform {sanitize_for_log(name)}")
            except Exception as e:
                app.logger.error(f"Error switching to first platform: {e}")
                # Don't fail the platform creation, just log the error
        
        return jsonify({
            'success': True, 
            'message': 'Platform connection added successfully',
            'platform': {
                'id': platform.id,
                'name': platform.name,
                'platform_type': platform.platform_type,
                'instance_url': platform.instance_url,
                'username': platform.username,
                'is_default': platform.is_default
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error adding platform connection: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/switch_platform/<int:platform_id>', methods=['POST'])
@login_required
@with_db_session
@validate_csrf_token
@with_session_error_handling
def api_switch_platform(platform_id):
    """Switch to a different platform with session management"""
    try:
        # Use request-scoped session for all database operations
        with request_session_manager.session_scope() as db_session:
            # Verify platform belongs to current user and validate ownership
            platform = db_session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if not platform:
                return jsonify({'success': False, 'error': 'Platform not found or not accessible'}), 404
            
            # Extract platform data before session operations to avoid DetachedInstanceError
            platform_data = {
                'id': platform.id,
                'name': platform.name,
                'platform_type': platform.platform_type,
                'instance_url': platform.instance_url,
                'username': platform.username
            }
            
            # Check for active caption generation tasks and cancel them
            try:
                caption_service = WebCaptionGenerationService(db_manager)
                active_task = caption_service.task_queue_manager.get_user_active_task(current_user.id)
                
                if active_task:
                    # Cancel the active task
                    cancelled = caption_service.cancel_generation(active_task.id, current_user.id)
                    if cancelled:
                        app.logger.info(f"Cancelled active caption generation task {sanitize_for_log(active_task.id)} due to platform switch")
                    else:
                        app.logger.warning(f"Failed to cancel active caption generation task {sanitize_for_log(active_task.id)} during platform switch")
            except Exception as e:
                app.logger.error(f"Error handling active caption generation task during platform switch: {sanitize_for_log(str(e))}")
            
            # Update database session platform context using session manager
            from flask import session as flask_session
            flask_session_id = flask_session.get('_id')
            session_updated = False
            if flask_session_id:
                session_updated = session_manager.update_platform_context(flask_session_id, platform_id)
            
            # Also set as default platform in database for persistence
            db_success = db_manager.set_default_platform(current_user.id, platform_id)
            
            if session_updated:
                app.logger.info(f"User {sanitize_for_log(current_user.username)} switched to platform {sanitize_for_log(platform_data['name'])}")
                return jsonify({
                    'success': True,
                    'message': f'Successfully switched to {platform_data["name"]} ({platform_data["platform_type"].title()})',
                    'platform': platform_data
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to switch platform'}), 500
                
    except Exception as e:
        app.logger.error(f"Error switching platform: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to switch platform'}), 500

@app.route('/api/test_platform/<int:platform_id>', methods=['POST'])
@login_required
@with_session_error_handling
def api_test_platform(platform_id):
    """Test a platform connection"""
    session = db_manager.get_session()
    try:
        # Verify platform belongs to current user
        platform = session.query(PlatformConnection).filter_by(
            id=platform_id,
            user_id=current_user.id
        ).first()
        
        if not platform:
            return jsonify({'success': False, 'error': 'Platform not found or not accessible'}), 404
        
        # Test the connection
        success, message = platform.test_connection()
        
        # Provide more detailed feedback
        if success:
            detailed_message = f"Connection successful! Verified access to {platform.instance_url}"
            if platform.username:
                detailed_message += f" as @{platform.username}"
        else:
            detailed_message = f"Connection failed: {message}"
        
        return jsonify({
            'success': success,
            'message': detailed_message,
            'platform_info': {
                'name': platform.name,
                'type': platform.platform_type,
                'instance': platform.instance_url
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error testing platform connection: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()

@app.route('/api/get_platform/<int:platform_id>', methods=['GET'])
@login_required
@with_session_error_handling
def api_get_platform(platform_id):
    """Get platform connection data for editing"""
    session = db_manager.get_session()
    try:
        # Verify platform belongs to current user
        platform = session.query(PlatformConnection).filter_by(
            id=platform_id,
            user_id=current_user.id
        ).first()
        
        if not platform:
            return jsonify({'success': False, 'error': 'Platform not found or not accessible'}), 404
        
        return jsonify({
            'success': True,
            'platform': {
                'id': platform.id,
                'name': platform.name,
                'platform_type': platform.platform_type,
                'instance_url': platform.instance_url,
                'username': platform.username,
                'access_token': platform.access_token,  # Note: This will be decrypted
                'client_key': platform.client_key,
                'client_secret': platform.client_secret,
                'is_default': platform.is_default,
                'is_active': platform.is_active
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error getting platform connection: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()

@app.route('/api/edit_platform/<int:platform_id>', methods=['PUT'])
@login_required
@with_session_error_handling
def api_edit_platform(platform_id):
    """Edit an existing platform connection"""
    try:
        data = request.get_json()
        
        # Validate JSON data exists
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['name', 'platform_type', 'instance_url', 'access_token']
        for field in required_fields:
            if not data.get(field) or not str(data.get(field)).strip():
                return jsonify({'success': False, 'error': f'Missing or empty required field: {field}'}), 400
        
        # Validate field formats and constraints (same as add platform)
        validation_errors = []
        
        # Validate name
        name = str(data['name']).strip()
        if len(name) < 1 or len(name) > 100:
            validation_errors.append('Platform name must be between 1 and 100 characters')
        
        # Validate platform type
        platform_type = str(data['platform_type']).strip().lower()
        valid_platforms = ['pixelfed', 'mastodon']
        if platform_type not in valid_platforms:
            validation_errors.append(f'Platform type must be one of: {", ".join(valid_platforms)}')
        
        # Validate instance URL
        instance_url = str(data['instance_url']).strip()
        if not instance_url.startswith(('http://', 'https://')):
            validation_errors.append('Instance URL must start with http:// or https://')
        if len(instance_url) > 500:
            validation_errors.append('Instance URL must be less than 500 characters')
        
        # Validate access token
        access_token = str(data['access_token']).strip()
        if len(access_token) < 10:
            validation_errors.append('Access token appears to be too short (minimum 10 characters)')
        
        # Validate username if provided
        username = data.get('username')
        if username:
            username = str(username).strip()
            if len(username) > 200:
                validation_errors.append('Username must be less than 200 characters')
        
        # Mastodon no longer requires client credentials - only access token needed
        
        # Return validation errors if any
        if validation_errors:
            return jsonify({
                'success': False, 
                'error': 'Validation failed: ' + '; '.join(validation_errors)
            }), 400
        
        # Check for duplicate platform connections (excluding current platform)
        session = db_manager.get_session()
        try:
            existing_platform = session.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.name == name,
                PlatformConnection.id != platform_id
            ).first()
            
            if existing_platform:
                return jsonify({
                    'success': False, 
                    'error': f'A platform connection with the name "{name}" already exists'
                }), 400
            
            # Check for duplicate instance/username combination (excluding current platform)
            existing_instance = session.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.instance_url == instance_url,
                PlatformConnection.username == username,
                PlatformConnection.id != platform_id
            ).first()
            
            if existing_instance:
                return jsonify({
                    'success': False, 
                    'error': f'A connection to this instance with this username already exists'
                }), 400
        finally:
            session.close()
        
        # Update platform connection using database manager
        update_data = {
            'name': name,
            'platform_type': platform_type,
            'instance_url': instance_url,
            'username': username,
            'access_token': access_token,
            'client_key': data.get('client_key'),
            'client_secret': data.get('client_secret')
        }
        
        success = db_manager.update_platform_connection(
            connection_id=platform_id,
            user_id=current_user.id,
            **update_data
        )
        
        if not success:
            return jsonify({
                'success': False, 
                'error': 'Failed to update platform connection. Platform may not exist or not be accessible.'
            }), 400
        
        # Get updated platform for response
        session = db_manager.get_session()
        try:
            updated_platform = session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id
            ).first()
            
            if not updated_platform:
                return jsonify({
                    'success': False, 
                    'error': 'Platform connection not found after update'
                }), 404
            
            # Test connection if requested
            if data.get('test_connection', False):
                test_success, message = updated_platform.test_connection()
                if not test_success:
                    return jsonify({
                        'success': False, 
                        'error': f'Platform updated but connection test failed: {message}'
                    }), 400
            
            return jsonify({
                'success': True, 
                'message': 'Platform connection updated successfully',
                'platform': {
                    'id': updated_platform.id,
                    'name': updated_platform.name,
                    'platform_type': updated_platform.platform_type,
                    'instance_url': updated_platform.instance_url,
                    'username': updated_platform.username,
                    'is_default': updated_platform.is_default
                }
            })
        finally:
            session.close()
        
    except Exception as e:
        app.logger.error(f"Error updating platform connection: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session_state', methods=['GET'])
@login_required
@with_session_error_handling
def api_session_state():
    """Get current session state for cross-tab synchronization"""
    try:
        # Get current platform context with fallback
        context = get_current_platform_context()
        current_platform = None
        
        # Get platform info from Flask session context
        if context and context.get('platform_info'):
            current_platform = {
                'id': context['platform_info']['id'],
                'name': context['platform_info']['name'],
                'type': context['platform_info']['platform_type'],
                'instance_url': context['platform_info']['instance_url'],
                'is_default': context['platform_info']['is_default']
            }
        else:
            # Fallback to default platform if no current platform
            db_session = db_manager.get_session()
            try:
                default_platform = db_session.query(PlatformConnection).filter_by(
                    user_id=current_user.id,
                    is_default=True,
                    is_active=True
                ).first()
                
                if not default_platform:
                    default_platform = db_session.query(PlatformConnection).filter_by(
                        user_id=current_user.id,
                        is_active=True
                    ).first()
                
                if default_platform:
                    # Extract platform data before session closes to avoid DetachedInstanceError
                    platform_id = default_platform.id
                    platform_name = default_platform.name
                    
                    current_platform = {
                        'id': platform_id,
                        'name': platform_name,
                        'type': default_platform.platform_type,
                        'instance_url': default_platform.instance_url,
                        'is_default': default_platform.is_default
                    }
                    
                    # Update database session context
                    from flask import session as flask_session
                    flask_session_id = flask_session.get('_id')
                    if flask_session_id:
                        session_manager.update_platform_context(flask_session_id, platform_id)
                    app.logger.info(f"Updated session context to default platform {platform_name}")
            finally:
                db_session.close()
        
        return jsonify({
            'success': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email
            },
            'platform': current_platform,
            'session_type': 'flask',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context_source': 'session' if context else 'fallback'
        })
        
    except Exception as e:
        app.logger.error(f"Error getting session state: {e}")
        return jsonify({'success': False, 'error': 'Failed to get session state'}), 500

# Flask sessions are per-browser, so no need for multi-session management endpoints

@app.route('/api/delete_platform/<int:platform_id>', methods=['DELETE'])
@login_required
@with_session_error_handling
def api_delete_platform(platform_id):
    """Delete a platform connection with comprehensive validation"""
    session = db_manager.get_session()
    try:
        # First, verify the platform exists and belongs to the user
        platform = session.query(PlatformConnection).filter_by(
            id=platform_id,
            user_id=current_user.id
        ).first()
        
        if not platform:
            return jsonify({
                'success': False,
                'error': 'Platform connection not found or not accessible'
            }), 404
        
        platform_name = platform.name
        was_default = platform.is_default
        
        # Check if this is the only platform connection
        user_platform_count = session.query(PlatformConnection).filter_by(
            user_id=current_user.id,
            is_active=True
        ).count()
        
        if user_platform_count <= 1:
            return jsonify({
                'success': False,
                'error': 'Cannot delete the last platform connection. You must have at least one active platform.'
            }), 400
        
        # Check for associated data that might be affected
        associated_posts = session.query(Post).filter_by(platform_connection_id=platform_id).count()
        associated_images = session.query(Image).filter_by(platform_connection_id=platform_id).count()
        
        # Provide information about associated data
        data_info = []
        if associated_posts > 0:
            data_info.append(f"{associated_posts} posts")
        if associated_images > 0:
            data_info.append(f"{associated_images} images")
        
        # Log the deletion attempt
        app.logger.info(f"User {sanitize_for_log(current_user.username)} attempting to delete platform '{sanitize_for_log(platform_name)}' "
                       f"(ID: {sanitize_for_log(str(platform_id))}) with {sanitize_for_log(', '.join(data_info)) if data_info else 'no associated data'}")
        
    except Exception as e:
        session.rollback()
        app.logger.error(f"Error during platform deletion validation: {str(e)}")
        return jsonify({'success': False, 'error': 'Database error during validation'}), 500
    finally:
        session.close()
    
    try:
        # Use the database manager's delete method which includes proper validation
        success = db_manager.delete_platform_connection(
            connection_id=platform_id,
            user_id=current_user.id,
            force=False  # Don't force delete, let it check for associated data
        )
        
        if success:
            message = f'Platform connection "{platform_name}" deleted successfully'
            if data_info:
                message += f'. Associated data ({", ".join(data_info)}) has been preserved.'
            if was_default:
                message += ' Another platform has been set as default.'
            
            app.logger.info(f"Successfully deleted platform '{sanitize_for_log(platform_name)}' for user {sanitize_for_log(current_user.username)}")
            
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete platform connection. It may have associated data that prevents deletion.'
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error deleting platform connection: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Caption Generation Forms
class CaptionGenerationForm(FlaskForm):
    """Form for starting caption generation"""
    max_posts_per_run = IntegerField('Max Posts Per Run', 
                                   validators=[DataRequired(), NumberRange(min=1, max=500)], 
                                   default=50)
    max_caption_length = IntegerField('Max Caption Length', 
                                    validators=[DataRequired(), NumberRange(min=50, max=1000)], 
                                    default=500)
    optimal_min_length = IntegerField('Optimal Min Length', 
                                    validators=[DataRequired(), NumberRange(min=20, max=200)], 
                                    default=80)
    optimal_max_length = IntegerField('Optimal Max Length', 
                                    validators=[DataRequired(), NumberRange(min=100, max=500)], 
                                    default=200)
    reprocess_existing = BooleanField('Reprocess Existing Captions', default=False)
    processing_delay = FloatField('Processing Delay (seconds)', 
                                validators=[DataRequired(), NumberRange(min=0.0, max=10.0)], 
                                default=1.0)
    submit = SubmitField('Start Caption Generation')

class CaptionSettingsForm(FlaskForm):
    """Form for managing caption generation settings"""
    max_posts_per_run = IntegerField('Max Posts Per Run', 
                                   validators=[DataRequired(), NumberRange(min=1, max=500)], 
                                   default=50)
    max_caption_length = IntegerField('Max Caption Length', 
                                    validators=[DataRequired(), NumberRange(min=50, max=1000)], 
                                    default=500)
    optimal_min_length = IntegerField('Optimal Min Length', 
                                    validators=[DataRequired(), NumberRange(min=20, max=200)], 
                                    default=80)
    optimal_max_length = IntegerField('Optimal Max Length', 
                                    validators=[DataRequired(), NumberRange(min=100, max=500)], 
                                    default=200)
    reprocess_existing = BooleanField('Reprocess Existing Captions', default=False)
    processing_delay = FloatField('Processing Delay (seconds)', 
                                validators=[DataRequired(), NumberRange(min=0.0, max=10.0)], 
                                default=1.0)
    submit = SubmitField('Save Settings')

# Caption Generation Routes
@app.route('/caption_generation')
@login_required
@platform_required
@rate_limit(limit=10, window_seconds=60)
@with_session_error_handling
def caption_generation():
    """Caption generation page"""
    try:
        # Get current platform context
        context = get_current_platform_context()
        if not context or not context.get('platform_connection_id'):
            flash('No active platform connection found.', 'error')
            return redirect(url_for('platform_management'))
        
        platform_connection_id = context['platform_connection_id']
        
        # Initialize caption generation service
        caption_service = WebCaptionGenerationService(db_manager)
        
        # Check if user has an active task
        active_task = caption_service.task_queue_manager.get_user_active_task(current_user.id)
        
        # Get user's task history
        task_history = []
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            task_history = loop.run_until_complete(
                caption_service.get_user_task_history(current_user.id, limit=5)
            )
            loop.close()
        except Exception as e:
            app.logger.error(f"Error getting task history: {sanitize_for_log(str(e))}")
        
        # Get user's current settings
        user_settings = None
        db_session = db_manager.get_session()
        try:
            from models import CaptionGenerationUserSettings
            user_settings_record = db_session.query(CaptionGenerationUserSettings).filter_by(
                user_id=current_user.id,
                platform_connection_id=platform_connection_id
            ).first()
            
            if user_settings_record:
                user_settings = user_settings_record.to_settings_dataclass()
        finally:
            db_session.close()
        
        # Create form with current settings
        form = CaptionGenerationForm()
        if user_settings:
            form.max_posts_per_run.data = user_settings.max_posts_per_run
            form.max_caption_length.data = user_settings.max_caption_length
            form.optimal_min_length.data = user_settings.optimal_min_length
            form.optimal_max_length.data = user_settings.optimal_max_length
            form.reprocess_existing.data = user_settings.reprocess_existing
            form.processing_delay.data = user_settings.processing_delay
        
        return render_template('caption_generation.html',
                             form=form,
                             active_task=active_task,
                             task_history=task_history,
                             user_settings=user_settings)
                             
    except Exception as e:
        app.logger.error(f"Error loading caption generation page: {sanitize_for_log(str(e))}")
        flash('Error loading caption generation page.', 'error')
        return redirect(url_for('index'))

@app.route('/start_caption_generation', methods=['POST'])
@login_required
@platform_required
@caption_generation_rate_limit(limit=3, window_minutes=60)
@require_secure_connection
@validate_csrf_token
@rate_limit(limit=3, window_seconds=300)  # Max 3 attempts per 5 minutes
@validate_input_length()
@with_session_error_handling
def start_caption_generation():
    """Start caption generation process"""
    form = CaptionGenerationForm()
    
    if form.validate_on_submit():
        try:
            # Get current platform context
            context = get_current_platform_context()
            if not context or not context.get('platform_connection_id'):
                return jsonify({
                    'success': False,
                    'error': 'No active platform connection found.'
                }), 400
            
            platform_connection_id = context['platform_connection_id']
            
            # Create settings from form
            from models import CaptionGenerationSettings
            settings = CaptionGenerationSettings(
                max_posts_per_run=form.max_posts_per_run.data,
                max_caption_length=form.max_caption_length.data,
                optimal_min_length=form.optimal_min_length.data,
                optimal_max_length=form.optimal_max_length.data,
                reprocess_existing=form.reprocess_existing.data,
                processing_delay=form.processing_delay.data
            )
            
            # Initialize caption generation service
            caption_service = WebCaptionGenerationService(db_manager)
            
            # Start caption generation
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                task_id = loop.run_until_complete(
                    caption_service.start_caption_generation(
                        current_user.id,
                        platform_connection_id,
                        settings
                    )
                )
                
                app.logger.info(f"Started caption generation task {sanitize_for_log(task_id)} for user {sanitize_for_log(str(current_user.id))}")
                
                # Log security event
                log_caption_security_event('generation_started', {
                    'task_id': task_id,
                    'platform_connection_id': platform_connection_id,
                    'settings': settings.to_dict()
                })
                
                return jsonify({
                    'success': True,
                    'task_id': task_id,
                    'message': 'Caption generation started successfully',
                    'redirect_url': url_for('review_batches')  # Redirect to batch review after completion
                })
                
            finally:
                loop.close()
                
        except ValueError as e:
            app.logger.warning(f"Validation error starting caption generation: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
            
        except Exception as e:
            app.logger.error(f"Error starting caption generation: {sanitize_for_log(str(e))}")
            
            # Create error info for better user messaging
            try:
                error_info = error_recovery_manager.create_error_info(e, {
                    'operation': 'start_generation',
                    'user_id': current_user.id,
                    'platform_id': platform_connection_id
                })
                user_message = error_recovery_manager._get_user_friendly_message(error_info)
            except Exception:
                user_message = 'Failed to start caption generation. Please try again.'
            
            return jsonify({
                'success': False,
                'error': user_message
            }), 500
    else:
        # Form validation failed
        errors = []
        for field, field_errors in form.errors.items():
            for error in field_errors:
                errors.append(f"{field}: {error}")
        
        return jsonify({
            'success': False,
            'error': 'Form validation failed',
            'details': errors
        }), 400

@app.route('/api/caption_generation/status/<task_id>')
@login_required
@platform_required
@validate_task_access
@rate_limit(limit=30, window_seconds=60)
@with_session_error_handling
def get_caption_generation_status(task_id):
    """Get caption generation task status"""
    try:
        # Validate task_id format (UUID)
        import uuid
        try:
            uuid.UUID(task_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid task ID format'
            }), 400
        
        # Initialize caption generation service
        caption_service = WebCaptionGenerationService(db_manager)
        
        # Get task status
        status = caption_service.get_generation_status(task_id, current_user.id)
        
        if status:
            return jsonify({
                'success': True,
                'status': status
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Task not found or access denied'
            }), 404
            
    except Exception as e:
        app.logger.error(f"Error getting caption generation status: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': 'Failed to get task status'
        }), 500

@app.route('/api/caption_generation/cancel/<task_id>', methods=['POST'])
@login_required
@platform_required
@validate_task_access
@require_secure_connection
@validate_csrf_token
@rate_limit(limit=10, window_seconds=60)
@with_session_error_handling
def cancel_caption_generation(task_id):
    """Cancel caption generation task"""
    try:
        # Validate task_id format (UUID)
        import uuid
        try:
            uuid.UUID(task_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid task ID format'
            }), 400
        
        # Initialize caption generation service
        caption_service = WebCaptionGenerationService(db_manager)
        
        # Cancel the task
        success = caption_service.cancel_generation(task_id, current_user.id)
        
        if success:
            app.logger.info(f"Cancelled caption generation task {sanitize_for_log(task_id)} for user {sanitize_for_log(str(current_user.id))}")
            return jsonify({
                'success': True,
                'message': 'Task cancelled successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to cancel task. Task may not exist or cannot be cancelled.'
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error cancelling caption generation: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': 'Failed to cancel task'
        }), 500

@app.route('/api/caption_generation/results/<task_id>')
@login_required
@platform_required
@validate_task_access
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def get_caption_generation_results(task_id):
    """Get caption generation results"""
    try:
        # Validate task_id format (UUID)
        import uuid
        try:
            uuid.UUID(task_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid task ID format'
            }), 400
        
        # Initialize caption generation service
        caption_service = WebCaptionGenerationService(db_manager)
        
        # Get results
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                caption_service.get_generation_results(task_id, current_user.id)
            )
            
            if results:
                return jsonify({
                    'success': True,
                    'results': results.to_dict()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Results not found or task not completed'
                }), 404
                
        finally:
            loop.close()
            
    except Exception as e:
        app.logger.error(f"Error getting caption generation results: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': 'Failed to get results'
        }), 500

@app.route('/caption_settings')
@login_required
@platform_required
@rate_limit(limit=10, window_seconds=60)
@with_session_error_handling
def caption_settings():
    """Caption generation settings page"""
    try:
        # Get current platform context
        context = get_current_platform_context()
        if not context or not context.get('platform_connection_id'):
            flash('No active platform connection found.', 'error')
            return redirect(url_for('platform_management'))
        
        platform_connection_id = context['platform_connection_id']
        
        # Get user's current settings
        db_session = db_manager.get_session()
        try:
            from models import CaptionGenerationUserSettings
            user_settings_record = db_session.query(CaptionGenerationUserSettings).filter_by(
                user_id=current_user.id,
                platform_connection_id=platform_connection_id
            ).first()
            
            # Create form with current settings
            form = CaptionSettingsForm()
            if user_settings_record:
                form.max_posts_per_run.data = user_settings_record.max_posts_per_run
                form.max_caption_length.data = user_settings_record.max_caption_length
                form.optimal_min_length.data = user_settings_record.optimal_min_length
                form.optimal_max_length.data = user_settings_record.optimal_max_length
                form.reprocess_existing.data = user_settings_record.reprocess_existing
                form.processing_delay.data = user_settings_record.processing_delay
            
            return render_template('caption_settings.html',
                                 form=form,
                                 user_settings=user_settings_record)
                                 
        finally:
            db_session.close()
            
    except Exception as e:
        app.logger.error(f"Error loading caption settings page: {sanitize_for_log(str(e))}")
        flash('Error loading caption settings page.', 'error')
        return redirect(url_for('index'))

@app.route('/api/caption_settings', methods=['GET'])
@login_required
@platform_required
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def api_get_caption_settings():
    """API endpoint to get caption generation settings"""
    try:
        # Get current platform context
        context = get_current_platform_context()
        if not context or not context.get('platform_connection_id'):
            return jsonify({'success': False, 'error': 'No active platform connection found'}), 400
        
        platform_connection_id = context['platform_connection_id']
        
        # Initialize caption generation service
        caption_service = WebCaptionGenerationService(db_manager)
        
        # Get settings
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            settings = loop.run_until_complete(
                caption_service.get_user_settings(
                    current_user.id,
                    platform_connection_id
                )
            )
            
            return jsonify({
                'success': True,
                'settings': settings.to_dict()
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        app.logger.error(f"Error getting caption settings: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to retrieve settings'}), 500

@app.route('/save_caption_settings', methods=['POST'])
@login_required
@platform_required
@validate_caption_settings_input
@require_secure_connection
@validate_csrf_token
@rate_limit(limit=10, window_seconds=60)
@validate_input_length()
@enhanced_input_validation
@with_session_error_handling
def save_caption_settings():
    """Save caption generation settings"""
    form = CaptionSettingsForm()
    
    if form.validate_on_submit():
        try:
            # Get current platform context
            context = get_current_platform_context()
            if not context or not context.get('platform_connection_id'):
                flash('No active platform connection found.', 'error')
                return redirect(url_for('platform_management'))
            
            platform_connection_id = context['platform_connection_id']
            
            # Create settings from form
            from models import CaptionGenerationSettings
            settings = CaptionGenerationSettings(
                max_posts_per_run=form.max_posts_per_run.data,
                max_caption_length=form.max_caption_length.data,
                optimal_min_length=form.optimal_min_length.data,
                optimal_max_length=form.optimal_max_length.data,
                reprocess_existing=form.reprocess_existing.data,
                processing_delay=form.processing_delay.data
            )
            
            # Initialize caption generation service
            caption_service = WebCaptionGenerationService(db_manager)
            
            # Save settings
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(
                    caption_service.save_user_settings(
                        current_user.id,
                        platform_connection_id,
                        settings
                    )
                )
                
                if success:
                    flash('Caption generation settings saved successfully.', 'success')
                    app.logger.info(f"Saved caption settings for user {sanitize_for_log(str(current_user.id))} platform {sanitize_for_log(str(platform_connection_id))}")
                else:
                    flash('Failed to save caption generation settings.', 'error')
                    
            finally:
                loop.close()
                
        except Exception as e:
            app.logger.error(f"Error saving caption settings: {sanitize_for_log(str(e))}")
            flash('Error saving caption generation settings.', 'error')
    else:
        # Form validation failed
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')
    
    return redirect(url_for('caption_settings'))

@app.route('/api/validate_caption_settings', methods=['POST'])
@login_required
@platform_required
@validate_caption_settings_input
@rate_limit(limit=30, window_seconds=60)
@validate_input_length()
@with_session_error_handling
def api_validate_caption_settings():
    """API endpoint to validate caption generation settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate individual fields
        validation_errors = []
        
        # Max posts per run
        max_posts = data.get('max_posts_per_run')
        if max_posts is not None:
            if not isinstance(max_posts, int) or max_posts < 1 or max_posts > 500:
                validation_errors.append('Max posts per run must be between 1 and 500')
        
        # Processing delay
        delay = data.get('processing_delay')
        if delay is not None:
            if not isinstance(delay, (int, float)) or delay < 0 or delay > 10:
                validation_errors.append('Processing delay must be between 0 and 10 seconds')
        
        # Max caption length
        max_length = data.get('max_caption_length')
        if max_length is not None:
            if not isinstance(max_length, int) or max_length < 50 or max_length > 1000:
                validation_errors.append('Max caption length must be between 50 and 1000 characters')
        
        # Optimal lengths
        min_length = data.get('optimal_min_length')
        if min_length is not None:
            if not isinstance(min_length, int) or min_length < 20 or min_length > 200:
                validation_errors.append('Optimal min length must be between 20 and 200 characters')
        
        opt_max_length = data.get('optimal_max_length')
        if opt_max_length is not None:
            if not isinstance(opt_max_length, int) or opt_max_length < 100 or opt_max_length > 500:
                validation_errors.append('Optimal max length must be between 100 and 500 characters')
        
        # Cross-field validation
        if min_length is not None and opt_max_length is not None:
            if min_length >= opt_max_length:
                validation_errors.append('Optimal min length must be less than optimal max length')
        
        if opt_max_length is not None and max_length is not None:
            if opt_max_length > max_length:
                validation_errors.append('Optimal max length cannot exceed maximum caption length')
        
        # Return validation results
        if validation_errors:
            return jsonify({
                'success': False,
                'valid': False,
                'errors': validation_errors
            })
        else:
            return jsonify({
                'success': True,
                'valid': True,
                'message': 'All settings are valid'
            })
            
    except Exception as e:
        app.logger.error(f"Error validating caption settings: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Validation failed'}), 500

@app.route('/api/admin/error_statistics')
@login_required
@role_required(UserRole.ADMIN)
@rate_limit(limit=10, window_seconds=60)
@with_session_error_handling
def api_get_error_statistics():
    """Get error statistics for admin monitoring"""
    try:
        stats = error_recovery_manager.get_error_statistics()
        notifications = error_recovery_manager.get_admin_notifications(unread_only=True)
        
        return jsonify({
            'success': True,
            'statistics': stats,
            'unread_notifications': len(notifications),
            'notifications': notifications[:10]  # Latest 10 notifications
        })
        
    except Exception as e:
        app.logger.error(f"Error getting error statistics: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to get error statistics'}), 500

@app.route('/api/admin/session_error_statistics')
@login_required
@role_required(UserRole.ADMIN)
@with_session_error_handling
def api_get_session_error_statistics():
    """Get session error statistics for monitoring"""
    try:
        # Get session error handler statistics
        session_error_handler = getattr(app, 'session_error_handler', None)
        if session_error_handler:
            error_stats = session_error_handler.get_error_statistics()
        else:
            error_stats = {}
        
        # Get detached instance handler statistics if available
        detached_handler = getattr(app, 'detached_instance_handler', None)
        recovery_stats = {}
        if detached_handler and hasattr(detached_handler, '_record_recovery_metrics'):
            # This would require extending the detached instance handler to track metrics
            recovery_stats = {'recovery_attempts': 'Not implemented yet'}
        
        return jsonify({
            'success': True,
            'session_errors': error_stats,
            'recovery_stats': recovery_stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error getting session error statistics: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to get session error statistics'}), 500

@app.route('/api/admin/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def api_mark_notification_read(notification_id):
    """Mark admin notification as read"""
    try:
        success = error_recovery_manager.mark_notification_read(notification_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Notification marked as read'})
        else:
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Error marking notification as read: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to mark notification as read'}), 500

# Caption Review Integration Routes
@app.route('/review/batches')
@login_required
@platform_required
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def review_batches():
    """List recent caption generation batches for review"""
    try:
        # Get current platform context
        context = get_current_platform_context()
        if not context or not context.get('platform_connection_id'):
            flash('No active platform connection found.', 'error')
            return redirect(url_for('platform_management'))
        
        platform_connection_id = context['platform_connection_id']
        
        # Get query parameters
        days_back = request.args.get('days_back', 7, type=int)
        
        # Get recent batches
        batches = caption_review_integration.get_review_batches(
            user_id=current_user.id,
            platform_connection_id=platform_connection_id,
            days_back=days_back,
            limit=20
        )
        
        return render_template('review_batches.html', 
                             batches=batches,
                             days_back=days_back)
                             
    except Exception as e:
        app.logger.error(f"Error loading review batches: {sanitize_for_log(str(e))}")
        flash('Error loading review batches.', 'error')
        return redirect(url_for('index'))

@app.route('/review/batch/<batch_id>')
@login_required
@platform_required
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def review_batch(batch_id):
    """Review images in a specific batch"""
    try:
        # Get query parameters
        status_filter = request.args.get('status')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Convert status filter
        status_enum = None
        if status_filter:
            try:
                status_enum = ProcessingStatus(status_filter)
            except ValueError:
                status_enum = None
        
        # Get batch images
        batch_data = caption_review_integration.get_batch_images(
            batch_id=batch_id,
            user_id=current_user.id,
            status_filter=status_enum,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )
        
        # Get batch statistics
        batch_stats = caption_review_integration.get_batch_statistics(batch_id, current_user.id)
        
        return render_template('review_batch.html',
                             batch_data=batch_data,
                             batch_stats=batch_stats,
                             status_filter=status_filter,
                             sort_by=sort_by,
                             sort_order=sort_order,
                             processing_statuses=ProcessingStatus)
                             
    except Exception as e:
        app.logger.error(f"Error loading batch review: {sanitize_for_log(str(e))}")
        flash('Error loading batch for review.', 'error')
        return redirect(url_for('review_batches'))

@app.route('/api/review/batch/<batch_id>/bulk_approve', methods=['POST'])
@login_required
@platform_required
@require_secure_connection
@validate_csrf_token
@rate_limit(limit=10, window_seconds=60)
@validate_input_length()
@with_session_error_handling
def api_bulk_approve_batch(batch_id):
    """Bulk approve images in a batch"""
    try:
        data = request.get_json() or {}
        image_ids = data.get('image_ids')  # None means approve all
        reviewer_notes = data.get('reviewer_notes', '').strip()
        
        # Validate image_ids if provided
        if image_ids is not None:
            if not isinstance(image_ids, list) or not all(isinstance(id, int) for id in image_ids):
                return jsonify({'success': False, 'error': 'Invalid image_ids format'}), 400
        
        # Perform bulk approval
        result = caption_review_integration.bulk_approve_batch(
            batch_id=batch_id,
            user_id=current_user.id,
            image_ids=image_ids,
            reviewer_notes=reviewer_notes if reviewer_notes else None
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        app.logger.error(f"Error in bulk approve: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to approve images'}), 500

@app.route('/api/review/batch/<batch_id>/bulk_reject', methods=['POST'])
@login_required
@platform_required
@require_secure_connection
@validate_csrf_token
@rate_limit(limit=10, window_seconds=60)
@validate_input_length()
@with_session_error_handling
def api_bulk_reject_batch(batch_id):
    """Bulk reject images in a batch"""
    try:
        data = request.get_json() or {}
        image_ids = data.get('image_ids')  # None means reject all
        reviewer_notes = data.get('reviewer_notes', '').strip()
        
        # Validate image_ids if provided
        if image_ids is not None:
            if not isinstance(image_ids, list) or not all(isinstance(id, int) for id in image_ids):
                return jsonify({'success': False, 'error': 'Invalid image_ids format'}), 400
        
        # Perform bulk rejection
        result = caption_review_integration.bulk_reject_batch(
            batch_id=batch_id,
            user_id=current_user.id,
            image_ids=image_ids,
            reviewer_notes=reviewer_notes if reviewer_notes else None
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        app.logger.error(f"Error in bulk reject: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to reject images'}), 500

@app.route('/api/review/batch/image/<int:image_id>/caption', methods=['PUT'])
@login_required
@platform_required
@require_secure_connection
@validate_csrf_token
@rate_limit(limit=30, window_seconds=60)
@validate_input_length()
@with_session_error_handling
def api_update_batch_image_caption(image_id):
    """Update caption for an image in batch review context"""
    try:
        data = request.get_json()
        if not data or 'caption' not in data:
            return jsonify({'success': False, 'error': 'Caption is required'}), 400
        
        new_caption = data['caption'].strip()
        batch_id = data.get('batch_id')
        
        if not new_caption:
            return jsonify({'success': False, 'error': 'Caption cannot be empty'}), 400
        
        if len(new_caption) > 1000:
            return jsonify({'success': False, 'error': 'Caption too long (max 1000 characters)'}), 400
        
        # Update the caption
        result = caption_review_integration.update_batch_image_caption(
            image_id=image_id,
            user_id=current_user.id,
            new_caption=new_caption,
            batch_id=batch_id
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        app.logger.error(f"Error updating batch image caption: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to update caption'}), 500

@app.route('/api/review/batch/<batch_id>/statistics')
@login_required
@platform_required
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def api_get_batch_statistics(batch_id):
    """Get statistics for a review batch"""
    try:
        stats = caption_review_integration.get_batch_statistics(batch_id, current_user.id)
        
        if stats:
            return jsonify({'success': True, 'statistics': stats})
        else:
            return jsonify({'success': False, 'error': 'Batch not found or access denied'}), 404
            
    except Exception as e:
        app.logger.error(f"Error getting batch statistics: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to get statistics'}), 500

# Administrative Monitoring Routes
@app.route('/admin/monitoring')
@login_required
@role_required(UserRole.ADMIN)
@rate_limit(limit=10, window_seconds=60)
@with_session_error_handling
def admin_monitoring_dashboard():
    """Administrative monitoring dashboard"""
    try:
        # Get system overview
        system_overview = admin_monitoring_service.get_system_overview()
        
        # Get active tasks
        active_tasks = admin_monitoring_service.get_active_tasks(limit=20)
        
        # Get recent performance metrics
        performance_metrics = admin_monitoring_service.get_performance_metrics(days=7)
        
        # Get system limits
        system_limits = admin_monitoring_service.get_system_limits()
        
        return render_template('admin_monitoring.html',
                             system_overview=system_overview,
                             active_tasks=active_tasks,
                             performance_metrics=performance_metrics,
                             system_limits=system_limits)
                             
    except Exception as e:
        app.logger.error(f"Error loading admin monitoring dashboard: {sanitize_for_log(str(e))}")
        flash('Error loading monitoring dashboard.', 'error')
        return redirect(url_for('index'))

@app.route('/api/admin/system_overview')
@login_required
@role_required(UserRole.ADMIN)
@rate_limit(limit=30, window_seconds=60)
@with_session_error_handling
def api_admin_system_overview():
    """Get real-time system overview"""
    try:
        overview = admin_monitoring_service.get_system_overview()
        return jsonify({'success': True, 'overview': overview})
        
    except Exception as e:
        app.logger.error(f"Error getting system overview: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to get system overview'}), 500

@app.route('/api/admin/active_tasks')
@login_required
@role_required(UserRole.ADMIN)
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def api_admin_active_tasks():
    """Get active caption generation tasks"""
    try:
        limit = request.args.get('limit', 50, type=int)
        tasks = admin_monitoring_service.get_active_tasks(limit=limit)
        
        return jsonify({'success': True, 'tasks': tasks})
        
    except Exception as e:
        app.logger.error(f"Error getting active tasks: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to get active tasks'}), 500

@app.route('/api/admin/task_history')
@login_required
@role_required(UserRole.ADMIN)
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def api_admin_task_history():
    """Get task history"""
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        tasks = admin_monitoring_service.get_task_history(hours=hours, limit=limit)
        
        return jsonify({'success': True, 'tasks': tasks})
        
    except Exception as e:
        app.logger.error(f"Error getting task history: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to get task history'}), 500

@app.route('/api/admin/performance_metrics')
@login_required
@role_required(UserRole.ADMIN)
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def api_admin_performance_metrics():
    """Get performance metrics"""
    try:
        days = request.args.get('days', 7, type=int)
        metrics = admin_monitoring_service.get_performance_metrics(days=days)
        
        return jsonify({'success': True, 'metrics': metrics})
        
    except Exception as e:
        app.logger.error(f"Error getting performance metrics: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to get performance metrics'}), 500

@app.route('/api/admin/cancel_task/<task_id>', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@require_secure_connection
@validate_csrf_token
@rate_limit(limit=10, window_seconds=60)
@with_session_error_handling
def api_admin_cancel_task(task_id):
    """Cancel a task as administrator"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', '').strip()
        
        result = admin_monitoring_service.cancel_task(
            task_id=task_id,
            admin_user_id=current_user.id,
            reason=reason
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        app.logger.error(f"Error cancelling task: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to cancel task'}), 500

@app.route('/api/admin/cleanup_tasks', methods=['POST'])
@login_required
@role_required(UserRole.ADMIN)
@require_secure_connection
@validate_csrf_token
@rate_limit(limit=5, window_seconds=300)
@with_session_error_handling
def api_admin_cleanup_tasks():
    """Clean up old tasks"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 7)
        dry_run = data.get('dry_run', True)
        
        if not isinstance(days, int) or days < 1 or days > 365:
            return jsonify({'success': False, 'error': 'Invalid days parameter (1-365)'}), 400
        
        result = admin_monitoring_service.cleanup_old_tasks(days=days, dry_run=dry_run)
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error cleaning up tasks: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to cleanup tasks'}), 500

@app.route('/api/csrf-token', methods=['GET'])
@login_required
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def api_get_csrf_token():
    """Get a fresh CSRF token for AJAX requests"""
    try:
        from flask_wtf.csrf import generate_csrf
        
        # Generate new CSRF token
        csrf_token = generate_csrf()
        
        return jsonify({
            'success': True,
            'csrf_token': csrf_token,
            'expires_in': 3600  # 1 hour
        })
        
    except Exception as e:
        app.logger.error(f"Error generating CSRF token: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate CSRF token'
        }), 500

@app.route('/api/update_user_settings', methods=['POST'])
@login_required
@require_secure_connection
@validate_csrf_token
@rate_limit(limit=10, window_seconds=60)
@validate_input_length()
@with_session_error_handling
def api_update_user_settings():
    """Update user settings for the current platform"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Get current platform context
        context = get_current_platform_context()
        if not context or not context.get('platform_connection_id'):
            return jsonify({'success': False, 'error': 'No active platform connection found'}), 400
        
        platform_connection_id = context['platform_connection_id']
        
        # Validate max_posts_per_run
        max_posts_per_run = data.get('max_posts_per_run')
        if max_posts_per_run is not None:
            if not isinstance(max_posts_per_run, int) or max_posts_per_run < 1 or max_posts_per_run > 500:
                return jsonify({'success': False, 'error': 'Max posts per run must be between 1 and 500'}), 400
        
        # Update or create user settings
        db_session = db_manager.get_session()
        try:
            from models import CaptionGenerationUserSettings
            
            # Get existing settings or create new ones
            user_settings = db_session.query(CaptionGenerationUserSettings).filter_by(
                user_id=current_user.id,
                platform_connection_id=platform_connection_id
            ).first()
            
            if not user_settings:
                # Create new settings with defaults
                user_settings = CaptionGenerationUserSettings(
                    user_id=current_user.id,
                    platform_connection_id=platform_connection_id,
                    max_posts_per_run=max_posts_per_run or 50,
                    max_caption_length=500,
                    optimal_min_length=80,
                    optimal_max_length=200,
                    reprocess_existing=False,
                    processing_delay=1.0
                )
                db_session.add(user_settings)
            else:
                # Update existing settings
                if max_posts_per_run is not None:
                    user_settings.max_posts_per_run = max_posts_per_run
                user_settings.updated_at = datetime.now(timezone.utc)
            
            db_session.commit()
            
            app.logger.info(f"Updated user settings for user {sanitize_for_log(str(current_user.id))} platform {sanitize_for_log(str(platform_connection_id))}")
            
            return jsonify({
                'success': True,
                'message': 'Settings updated successfully',
                'settings': {
                    'max_posts_per_run': user_settings.max_posts_per_run
                }
            })
            
        finally:
            db_session.close()
            
    except Exception as e:
        app.logger.error(f"Error updating user settings: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to update settings'}), 500

@app.route('/api/admin/user_activity')
@login_required
@role_required(UserRole.ADMIN)
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def api_admin_user_activity():
    """Get user activity statistics"""
    try:
        days = request.args.get('days', 7, type=int)
        activity = admin_monitoring_service.get_user_activity(days=days)
        
        return jsonify({'success': True, 'activity': activity})
        
    except Exception as e:
        app.logger.error(f"Error getting user activity: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to get user activity'}), 500

@app.route('/api/admin/system_limits', methods=['GET', 'POST'])
@login_required
@role_required(UserRole.ADMIN)
@rate_limit(limit=10, window_seconds=60)
@with_session_error_handling
def api_admin_system_limits():
    """Get or update system limits"""
    try:
        if request.method == 'GET':
            limits = admin_monitoring_service.get_system_limits()
            return jsonify({'success': True, 'limits': limits})
        
        else:  # POST
            data = request.get_json() or {}
            result = admin_monitoring_service.update_system_limits(data)
            
            return jsonify(result)
            
    except Exception as e:
        app.logger.error(f"Error with system limits: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to handle system limits'}), 500


# Favicon and static asset routes
@app.route('/favicon.ico')
@with_session_error_handling
def favicon():
    """Serve favicon.ico with proper caching"""
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'favicons'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


@app.after_request
def add_favicon_cache_headers(response):
    """Add cache headers for favicon assets"""
    if request.path.startswith('/static/favicons/'):
        # Cache favicons for 1 week
        response.cache_control.max_age = 604800
        response.cache_control.public = True
    elif request.path == '/favicon.ico':
        # Cache main favicon for 1 week
        response.cache_control.max_age = 604800
        response.cache_control.public = True
    return response


if __name__ == '__main__':
    # Set up logging for web app
    import logging
    from logger import setup_logging
    
    # Create logs directory
    os.makedirs(config.storage.logs_dir, exist_ok=True)
    
    # Set up structured logging for web app
    setup_logging(
        log_level=config.log_level,
        log_file=os.path.join(config.storage.logs_dir, 'webapp.log'),
        use_json=False,
        include_traceback=True
    )

@app.route('/api/progress_stream/<task_id>')
@login_required
@with_session_error_handling
def progress_stream(task_id):
    """Server-Sent Events endpoint for real-time progress updates"""
    # Verify authentication before starting stream
    if not current_user or not current_user.is_authenticated:
        app.logger.warning(f"Unauthenticated SSE connection attempt for task {sanitize_for_log(task_id)}")
        return Response(
            f"data: {{\"type\": \"error\", \"message\": \"Authentication required\"}}\n\n",
            mimetype='text/event-stream',
            status=401
        )
    
    app.logger.info(f"SSE connection request for task {sanitize_for_log(task_id)} from user {sanitize_for_log(str(current_user.id))}")
    try:
        return Response(
            sse_progress_handler.create_event_stream(task_id),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )
    except Exception as e:
        app.logger.error(f"Error in progress_stream: {sanitize_for_log(str(e))}")
        return Response(
            f"data: {{\"type\": \"error\", \"message\": \"Stream initialization failed\"}}\n\n",
            mimetype='text/event-stream',
            status=500
        )

if __name__ == '__main__':
    app.run(
        host=config.webapp.host,
        port=config.webapp.port,
        debug=config.webapp.debug
    )