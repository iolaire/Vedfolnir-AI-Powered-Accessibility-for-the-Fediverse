# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import os
import asyncio
from datetime import datetime, timedelta, timezone

# Load environment variables FIRST before reading any settings
from dotenv import load_dotenv
load_dotenv()

# Security feature toggles from environment (now loaded)
CSRF_ENABLED = os.getenv('SECURITY_CSRF_ENABLED', 'true').lower() == 'true'
RATE_LIMITING_ENABLED = os.getenv('SECURITY_RATE_LIMITING_ENABLED', 'true').lower() == 'true'
INPUT_VALIDATION_ENABLED = os.getenv('SECURITY_INPUT_VALIDATION_ENABLED', 'true').lower() == 'true'
SECURITY_HEADERS_ENABLED = os.getenv('SECURITY_HEADERS_ENABLED', 'true').lower() == 'true'
SESSION_VALIDATION_ENABLED = os.getenv('SECURITY_SESSION_VALIDATION_ENABLED', 'true').lower() == 'true'
ADMIN_CHECKS_ENABLED = os.getenv('SECURITY_ADMIN_CHECKS_ENABLED', 'true').lower() == 'true'
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory, g, Response, make_response, current_app, session
# Removed Flask-SocketIO import - using SSE instead
from flask_wtf import FlaskForm
# Import regular WTForms Form class (no Flask-WTF CSRF)
from wtforms import Form, TextAreaField, SelectField, SubmitField, HiddenField, StringField, PasswordField, BooleanField, IntegerField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

def validate_form_submission(form):
    """
    Manual form validation replacement for validate_on_submit()
    Since we're using regular WTForms instead of Flask-WTF
    """
    return request.method == 'POST' and form.validate()
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
# Use new Redis session middleware V2 for session context
from session_middleware_v2 import get_current_session_context, get_current_session_id, get_current_user_id, update_session_platform
# Removed Flask session manager imports - using database sessions only
from request_scoped_session_manager import RequestScopedSessionManager
from session_aware_user import SessionAwareUser
from session_aware_decorators import with_db_session, require_platform_context
from security.core.security_utils import sanitize_for_log, sanitize_html_input
from enhanced_input_validation import enhanced_input_validation, EnhancedInputValidator
from security.core.security_middleware import SecurityMiddleware, require_https, validate_csrf_token, sanitize_filename, generate_secure_token, rate_limit, validate_input_length, require_secure_connection
from security_decorators import conditional_rate_limit, conditional_validate_csrf_token, conditional_validate_input_length, conditional_enhanced_input_validation
from security.core.role_based_access import require_role, require_admin, require_viewer_or_higher, platform_access_required, content_access_required, api_require_admin, api_platform_access_required, api_content_access_required
from security.middleware.platform_access_middleware import PlatformAccessMiddleware, filter_images_for_user, filter_posts_for_user, filter_platforms_for_user
from security.core.security_config import security_config
from security.features.caption_security import CaptionSecurityManager, caption_generation_auth_required, validate_task_access, caption_generation_rate_limit, validate_caption_settings_input, log_caption_security_event
from error_recovery_manager import error_recovery_manager
from web_caption_generation_service import WebCaptionGenerationService
from caption_review_integration import CaptionReviewIntegration

from security.logging.secure_error_handlers import register_secure_error_handlers
# Removed WebSocketProgressHandler import - using SSE instead
from progress_tracker import ProgressTracker
from task_queue_manager import TaskQueueManager

app = Flask(__name__)
config = Config()
app.config['SECRET_KEY'] = config.webapp.secret_key

# Initialize SSE Progress Handler (replaces SocketIO)
from sse_progress_handler import SSEProgressHandler


app.config['SQLALCHEMY_DATABASE_URI'] = config.storage.database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Initialize Redis Session Management System
from flask_redis_session_interface import FlaskRedisSessionInterface
from redis_session_backend import RedisSessionBackend

# Initialize Redis session backend
try:
    redis_backend = RedisSessionBackend.from_env()
    app.logger.info("Redis session backend initialized successfully")
    
    # Set up Flask Redis session interface
    redis_session_interface = FlaskRedisSessionInterface(
        redis_client=redis_backend.redis,
        key_prefix=os.getenv('REDIS_SESSION_PREFIX', 'vedfolnir:session:'),
        session_timeout=int(os.getenv('REDIS_SESSION_TIMEOUT', '7200'))
    )
    app.session_interface = redis_session_interface
    app.logger.info("Flask Redis session interface configured")
    
    # Store Redis backend for later use
    app.redis_backend = redis_backend
    
except Exception as e:
    app.logger.error(f"Failed to initialize Redis session system: {e}")
    app.logger.warning("Falling back to NullSessionInterface")
    
    # Fallback to NullSessionInterface if Redis fails
    from flask.sessions import SessionInterface, SessionMixin
    from werkzeug.datastructures import CallbackDict

    class NullSession(CallbackDict, SessionMixin):
        def __init__(self, initial=None):
            def on_update(self):
                self.modified = True
            CallbackDict.__init__(self, initial, on_update)
            self.permanent = False
            self.new = True
            self.modified = False

    class NullSessionInterface(SessionInterface):
        def open_session(self, app, request):
            return NullSession()
        def save_session(self, app, session, response):
            pass

    app.session_interface = NullSessionInterface()
    app.redis_backend = None






# Use Flask's default session interface but disable Flask-WTF CSRF completely
# This allows Flask to access secret_key while preventing CSRF session creation
app.config['WTF_CSRF_ENABLED'] = False  # Completely disable Flask-WTF CSRF

# Initialize CSRF protection (conditional) - Using custom CSRF system only
if CSRF_ENABLED:
    # Disable Flask-WTF CSRF since we're using our custom Redis-aware CSRF system
    app.config['WTF_CSRF_ENABLED'] = False
    csrf = None  # No Flask-WTF CSRF protection
    app.logger.info("Using custom Redis-aware CSRF protection (Flask-WTF CSRF disabled)")
else:
    app.config['WTF_CSRF_ENABLED'] = False
    app.logger.warning("CSRF protection disabled - DO NOT USE IN PRODUCTION")
    csrf = None

# Exempt session heartbeat from CSRF protection
# Note: CSRF exemptions are applied after route registration

# Initialize pre-authentication session handler for CSRF tokens
from pre_auth_session import PreAuthSessionHandler
pre_auth_handler = PreAuthSessionHandler(app)
app.logger.info("Pre-authentication session handler initialized for CSRF tokens")

# Initialize enhanced CSRF token manager
from security.core.csrf_token_manager import initialize_csrf_token_manager
csrf_token_manager = initialize_csrf_token_manager(app)

# Initialize platform access middleware
platform_access_middleware = PlatformAccessMiddleware(app)

# Template context processor for role-based access control
@app.context_processor
def inject_role_context():
    """Inject role-based context into templates and auto-set default platform in session"""
    if current_user.is_authenticated:
        platform_stats = platform_access_middleware.get_user_platform_stats()
        content_stats = platform_access_middleware.get_user_content_stats()
        
        # Auto-set default platform in Flask session if not already set
        default_platform = platform_stats.get('default_platform')
        if default_platform and not session.get('platform_connection_id'):
            session['platform_connection_id'] = default_platform.id
            session['platform_name'] = default_platform.name
            session.permanent = True
            app.logger.info(f"Auto-selected default platform {default_platform.name} (ID: {default_platform.id}) for user {current_user.id}")
        
        context = {
            'user_role': current_user.role,
            'is_admin': current_user.role == UserRole.ADMIN,
            'is_viewer': current_user.role == UserRole.VIEWER,
            'user_platforms': platform_stats.get('platforms', []),
            'user_platform_count': platform_stats.get('platform_count', 0),
            'current_platform': default_platform,
            'pending_review_count': content_stats.get('pending_review', 0),
            'total_images_count': content_stats.get('total_images', 0)
        }
        
        # Add admin-specific context
        if current_user.role == UserRole.ADMIN:
            from admin.security.admin_access_control import get_admin_system_stats
            admin_stats = get_admin_system_stats()
            context.update({
                'admin_stats': admin_stats,
                'total_users_count': admin_stats.get('total_users', 0),
                'unverified_users_count': admin_stats.get('unverified_users', 0),
                'locked_users_count': admin_stats.get('locked_users', 0),
                'total_platforms_count': admin_stats.get('total_platforms', 0),
                'total_pending_review': admin_stats.get('pending_review', 0)
            })
        
        return context
    
    return {
        'user_role': None,
        'is_admin': False,
        'is_viewer': False,
        'user_platforms': [],
        'user_platform_count': 0,
        'current_platform': None,
        'pending_review_count': 0,
        'total_images_count': 0
    }

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

# Security headers middleware (conditional)
if SECURITY_HEADERS_ENABLED:
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
            "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com https://cdn.jsdelivr.net https://kit.fontawesome.com https://ka-f.fontawesome.com; "
            "style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com cdn.jsdelivr.net fonts.googleapis.com https://ka-f.fontawesome.com; "
            "font-src 'self' cdnjs.cloudflare.com cdn.jsdelivr.net fonts.gstatic.com https://ka-f.fontawesome.com; "
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
else:
    app.logger.warning("Security headers disabled - DO NOT USE IN PRODUCTION")


# Initialize database and quality manager
db_manager = DatabaseManager(config)
quality_manager = CaptionQualityManager()

# Initialize health checker
health_checker = HealthChecker(config, db_manager)
app.config['health_checker'] = health_checker

# Initialize session management system
from session_manager_v2 import SessionManagerV2
from session_middleware_v2 import SessionMiddleware
from session_security import create_session_security_manager
from session_monitoring import SessionMonitor

# Create session monitor
session_monitor = SessionMonitor(db_manager)

# Create session security manager
session_security_manager = create_session_security_manager(app.config, db_manager)

# Create Redis-based session manager
if hasattr(app, 'redis_backend') and app.redis_backend:
    unified_session_manager = SessionManagerV2(
        db_manager=db_manager,
        redis_backend=app.redis_backend,
        session_timeout=int(os.getenv('REDIS_SESSION_TIMEOUT', '7200'))
    )
    app.logger.info("Redis-based session manager initialized")
else:
    # Fallback to old session manager if Redis not available
    from session_factory import create_session_manager
    unified_session_manager = create_session_manager(
        db_manager=db_manager, 
        security_manager=session_security_manager,
        monitor=session_monitor
    )
    app.logger.warning("Using fallback session manager (Redis not available)")

# Store unified_session_manager on app object for direct access
app.unified_session_manager = unified_session_manager
app.session_manager = unified_session_manager  # For compatibility

# Initialize session middleware
if hasattr(app, 'redis_backend') and app.redis_backend:
    session_middleware = SessionMiddleware(app, unified_session_manager)
    app.logger.info("Redis session middleware initialized")
else:
    # Keep existing cookie manager for fallback
    from session_cookie_manager import create_session_cookie_manager
    session_cookie_manager = create_session_cookie_manager(app.config)
    app.session_cookie_manager = session_cookie_manager
    app.logger.info("Using fallback session cookie manager")

# Initialize session error handler
from session_error_handling import create_session_error_handler
if hasattr(app, 'redis_backend') and app.redis_backend:
    # For Redis sessions, we don't need the old session cookie manager
    session_error_handler = None
    app.logger.info("Session error handler skipped for Redis sessions")
else:
    # For fallback sessions, use the session cookie manager
    session_error_handler = create_session_error_handler(session_cookie_manager)
    app.session_error_handler = session_error_handler

# Add CORS headers for API endpoints
@app.after_request
def after_request(response):
    """Add CORS headers to API responses"""
    # Only add CORS headers to API endpoints
    if request.path.startswith('/api/'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With, X-CSRFToken'
        response.headers['Access-Control-Max-Age'] = '86400'
    return response

# Initialize session state API routes
from session_state_api import create_session_state_routes
create_session_state_routes(app)

# Session endpoints are exempted from CSRF in their respective modules

# Initialize session monitoring API routes
from session_monitoring_api import create_session_monitoring_routes
create_session_monitoring_routes(app)

# Store unified session manager and monitor in app for API access
app.unified_session_manager = unified_session_manager
app.session_monitor = session_monitor

# Legacy session manager removed - using unified_session_manager only
# session_manager = SessionManager(db_manager)  # DEPRECATED
# platform_middleware = PlatformContextMiddleware(app, session_manager)  # Removed - using DatabaseSessionMiddleware

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
from session_performance_optimizer import initialize_session_optimizations

# Initialize performance monitoring with database engine
session_performance_monitor = initialize_performance_monitoring(app, request_session_manager, db_manager.engine)

# Initialize session performance optimizations
try:
    optimization_results = initialize_session_optimizations(db_manager)
    app.logger.info(f"Session performance optimizations initialized: {optimization_results}")
except Exception as e:
    app.logger.error(f"Failed to initialize session performance optimizations: {e}")

# Register CLI commands and web routes for monitoring
register_session_monitoring_commands(app)
register_session_monitoring_routes(app)

# Initialize session health checking and alerting system
from session_health_checker import get_session_health_checker
from session_health_routes import register_session_health_routes
from session_alerting_system import get_alerting_system

# Initialize session health checker with unified session manager
session_health_checker = get_session_health_checker(db_manager, unified_session_manager)

# Initialize alerting system
session_alerting_system = get_alerting_system(session_health_checker)

# Store components in app config for route access
app.config['session_health_checker'] = session_health_checker
app.config['session_alerting_system'] = session_alerting_system
app.config['db_manager'] = db_manager
app.config['session_manager'] = unified_session_manager  # For backward compatibility

# Register debug routes (temporary for troubleshooting)
try:
    from debug_session_routes import register_debug_routes
    register_debug_routes(app)
    app.logger.info("Debug session routes registered")
except ImportError:
    app.logger.info("Debug session routes not available")

# Initialize Redis platform manager
from redis_platform_manager import get_redis_platform_manager
import os
encryption_key = os.getenv('PLATFORM_ENCRYPTION_KEY', 'default-key-change-in-production')

if hasattr(app, 'redis_backend') and app.redis_backend:
    # Use Redis backend's client for platform manager
    redis_platform_manager = get_redis_platform_manager(
        app.redis_backend.redis, 
        db_manager, 
        encryption_key
    )
    app.logger.info("Redis platform manager initialized with Redis backend")
else:
    # Fallback: try to get redis_client from unified_session_manager if available
    redis_client = getattr(unified_session_manager, 'redis_client', None)
    if redis_client:
        redis_platform_manager = get_redis_platform_manager(
            redis_client, 
            db_manager, 
            encryption_key
        )
        app.logger.info("Redis platform manager initialized with fallback client")
    else:
        redis_platform_manager = None
        app.logger.warning("Redis platform manager not initialized - no Redis client available")

if redis_platform_manager:
    app.config['redis_platform_manager'] = redis_platform_manager

# Register session health routes
register_session_health_routes(app)

# Register session alert routes
from session_alert_routes import register_session_alert_routes
register_session_alert_routes(app)

# Register security audit API routes
from admin.routes.security_audit_api import register_security_audit_api_routes
register_security_audit_api_routes(app)
app.logger.info("Security audit API routes registered")

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



# Initialize WebSocket progress handler components with proper resource management
progress_tracker = ProgressTracker(db_manager)
task_queue_manager = TaskQueueManager(db_manager)

# Initialize SSE progress handler with resource cleanup support
try:
    sse_progress_handler = SSEProgressHandler(db_manager, progress_tracker, task_queue_manager)
except Exception as e:
    app.logger.error(f"Failed to initialize SSE progress handler: {sanitize_for_log(str(e))}")
    # Create a fallback handler to prevent application startup failure
    class FallbackSSEHandler:
        def create_event_stream(self, task_id):
            yield 'data: {"type": "error", "message": "Progress streaming unavailable"}\n\n'
        def cleanup(self):
            pass
    sse_progress_handler = FallbackSSEHandler()

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
login_manager.login_view = 'user_management.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# User loader for Flask-Login with session attachment
@login_manager.user_loader
def load_user(user_id):
    """
    Load user for Flask-Login using Redis session data.
    This integrates Flask-Login with our Redis session management system.
    """
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        app.logger.warning(f"Invalid user_id format: {sanitize_for_log(str(user_id))}")
        return None
    
    app.logger.debug(f"Loading user with Flask-Login ID: {user_id_int}")
    
    try:
        # Use request-scoped session to prevent DetachedInstanceError
        with request_session_manager.session_scope() as session:
            user = session.query(User).options(
                joinedload(User.platform_connections),
                joinedload(User.sessions)
            ).filter(
                User.id == user_id_int,
                User.is_active == True
            ).first()
            
            if user:
                app.logger.debug(f"User loaded successfully: {user.username} (ID: {user.id})")
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
                return redirect(url_for('user_management.login', next=request.url))
            
            # SECURITY FIX: Always validate user permissions from server-side database
            # Never trust client-side session data for authorization
            try:
                with unified_session_manager.get_db_session() as session:
                    user_id = getattr(current_user, 'id', None)
                    if not user_id:
                        app.logger.warning("User ID not accessible from current_user")
                        flash('User authentication error. Please log in again.', 'error')
                        logout_user()
                        return redirect(url_for('user_management.login'))
                        
                    server_user = session.query(User).get(user_id)
                    if not server_user:
                        app.logger.warning(f"User account not found for ID: {user_id}")
                        flash('User account not found.', 'error')
                        logout_user()
                        return redirect(url_for('user_management.login'))
                    if not server_user.is_active:
                        app.logger.warning(f"Inactive user attempted access: {sanitize_for_log(server_user.username)}")
                        flash('Your account has been deactivated.', 'error')
                        logout_user()
                        return redirect(url_for('user_management.login'))
                    
                    # Debug logging for role checking
                    app.logger.debug(f"Role check: user={server_user.username}, user_role={server_user.role}, required_role={role}")
                    app.logger.debug(f"Role check: user_role.value={server_user.role.value if server_user.role else 'None'}")
                    app.logger.debug(f"Role check: has_permission={server_user.has_permission(role)}")
                    
                    # Use server-side user data for role validation
                    if not server_user.has_permission(role):
                        app.logger.warning(f"Access denied: user {sanitize_for_log(server_user.username)} (role: {sanitize_for_log(server_user.role.value if server_user.role else 'None')}) attempted to access {sanitize_for_log(role.value)} resource")
                        flash('You do not have permission to access this page.', 'error')
                        return redirect(url_for('index'))
                    
                    app.logger.debug(f"Access granted: user {sanitize_for_log(server_user.username)} has {sanitize_for_log(role.value)} permission")
                    # Store validated user role in g for this request
                    g.validated_user_role = server_user.role
            except SQLAlchemyError as e:
                app.logger.error(f"Database error during authorization: {sanitize_for_log(str(e))}")
                flash('Authorization error. Please try again.', 'error')
                return redirect(url_for('user_management.login'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Platform access validation decorator
def platform_required(f):
    """Decorator to ensure user has at least one active platform connection"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('user_management.login', next=request.url))
        
        # Check if user has platform context
        context = get_current_session_context()
        
        if not context or not context.get('platform_connection_id'):
            # No platform context, check if user has any platforms
            with request_session_manager.session_scope() as db_session:
                user_id = getattr(current_user, 'id', None)
                if not user_id:
                    flash('User authentication error. Please log in again.', 'error')
                    return redirect(url_for('user_management.login'))
                    
                user_platforms = db_session.query(PlatformConnection).filter_by(
                    user_id=user_id,
                    is_active=True
                ).count()
                
                if user_platforms == 0:
                    flash('You need to set up at least one platform connection to access this feature.', 'warning')
                    return redirect(url_for('first_time_setup'))
                else:
                    flash('Please select a platform to continue.', 'warning')
                    return redirect(url_for('platform_management'))
        
        return f(*args, **kwargs)
    return decorated_function

# Platform-specific access validation decorator
def platform_access_required(platform_type=None, instance_url=None):
    """Decorator to validate access to specific platform type or instance"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('user_management.login', next=request.url))
            
            # Get current platform context and validate with fresh database query
            context = get_current_session_context()
            if not context or not context.get('platform_connection_id'):
                flash('No active platform connection found.', 'error')
                return redirect(url_for('platform_management'))
            
            # Get current platform from database to avoid DetachedInstanceError
            with request_session_manager.session_scope() as db_session:
                user_id = getattr(current_user, 'id', None)
                if not user_id:
                    flash('User authentication error. Please log in again.', 'error')
                    return redirect(url_for('user_management.login'))
                    
                current_platform = db_session.query(PlatformConnection).filter_by(
                    id=context['platform_connection_id'],
                    user_id=user_id,
                    is_active=True
                ).first()
                
                if not current_platform:
                    flash('Current platform connection is no longer available.', 'error')
                    return redirect(url_for('platform_management'))
                
                # Extract platform data before closing session
                platform_type_actual = current_platform.platform_type
                instance_url_actual = current_platform.instance_url
            
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
    from markupsafe import escape, Markup
    return Markup(escape(text).replace('\n', '<br>'))

# Make UserRole available in all templates
@app.context_processor
def inject_user_role():
    """Make UserRole available in all templates"""
    return {'UserRole': UserRole}

# Make CSRF token function available in all templates
@app.context_processor
def inject_csrf_token():
    """Make CSRF token function available in all templates"""
    def csrf_token():
        """Generate CSRF token for templates"""
        try:
            csrf_manager = getattr(app, 'csrf_token_manager', None)
            if csrf_manager:
                return csrf_manager.generate_token()
            else:
                # Fallback to generate a basic token
                return generate_secure_token()
        except Exception as e:
            app.logger.error(f"Error generating CSRF token in template: {str(e)}")
            return ""
    
    return {'csrf_token': csrf_token}

# Register admin blueprint
from admin import create_admin_blueprint
admin_bp = create_admin_blueprint(app)
app.register_blueprint(admin_bp)

class LoginForm(Form):
    """Form for user login - using regular WTForms (no Flask-WTF CSRF)"""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')



class ReviewForm(Form):
    """Form for reviewing image captions - using regular WTForms (no Flask-WTF CSRF)"""
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

# Authentication routes - handled by user_management blueprint


@app.route('/first_time_setup')
@login_required
@with_session_error_handling
def first_time_setup():
    """First-time platform setup for new users"""
    # Admin users don't need platform setup - redirect to index
    if current_user.role == UserRole.ADMIN:
        return redirect(url_for('index'))
    
    # Check if user already has platforms - redirect if they do
    with unified_session_manager.get_db_session() as session:
        user_platforms = session.query(PlatformConnection).filter_by(
            user_id=current_user.id,
            is_active=True
        ).count()
        
        if user_platforms > 0:
            return redirect(url_for('index'))
    
    return render_template('first_time_setup.html')

# Logout route handled by user_management blueprint

@app.route('/logout_all')
@login_required
def logout_all():
    """Logout from all sessions with database session management"""
    user_id = current_user.id if current_user and current_user.is_authenticated else None
    
    try:
        # Database session cleanup: Clean up all user sessions
        if user_id:
            # Clear all database session records for the user
            count = unified_session_manager.cleanup_user_sessions(user_id)
            app.logger.info(f"Cleaned up {count} database sessions for user {sanitize_for_log(str(user_id))}")
        
        # Log out the user from Flask-Login
        logout_user()
        
        flash('You have been logged out from all sessions', 'info')
        
    except Exception as e:
        app.logger.error(f"Error during logout_all: {sanitize_for_log(str(e))}")
        # Still proceed with logout even if cleanup fails
        logout_user()
        flash('Error logging out from all sessions', 'error')
    
    # Create response with cleared session cookie
    response = make_response(redirect(url_for('user_management.login')))
    
    # Clear session cookie based on session type
    session_cookie_manager = getattr(app, 'session_cookie_manager', None)
    if session_cookie_manager:
        # Using fallback session manager - clear cookie
        session_cookie_manager.clear_session_cookie(response)
        app.logger.debug("Cleared session cookie using session_cookie_manager")
    else:
        # Using Redis sessions - clear Flask session and Redis session
        from flask import session
        session.clear()
        
        # Clear Redis session if we have a session ID
        try:
            from redis_session_middleware import get_current_session_id
            current_session_id = get_current_session_id()
            if current_session_id and hasattr(unified_session_manager, 'destroy_session'):
                unified_session_manager.destroy_session(current_session_id)
                app.logger.debug(f"Destroyed Redis session: {current_session_id}")
        except Exception as redis_error:
            app.logger.warning(f"Could not clear Redis session: {redis_error}")
        
        # Clear the session cookie manually for Redis sessions
        response.set_cookie(
            app.config.get('SESSION_COOKIE_NAME', 'session'),
            '',
            expires=0,
            path=app.config.get('SESSION_COOKIE_PATH', '/'),
            domain=app.config.get('SESSION_COOKIE_DOMAIN'),
            secure=app.config.get('SESSION_COOKIE_SECURE', False),
            httponly=app.config.get('SESSION_COOKIE_HTTPONLY', True),
            samesite=app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
        )
        app.logger.debug("Cleared session cookie manually for Redis sessions")
    
    return response



# Legacy routes - now handled by admin blueprint
# These routes are kept for backward compatibility but should use /admin/ URLs




@app.route('/')
@login_required
@require_viewer_or_higher
@with_db_session
@with_session_error_handling
def index():
    """Main dashboard with platform-aware statistics and session management"""
    try:
        # Use request-scoped session for all database queries
        with request_session_manager.session_scope() as db_session:
            # Check if user has any accessible platform connections
            platforms_query = db_session.query(PlatformConnection).filter_by(is_active=True)
            platforms_query = filter_platforms_for_user(platforms_query)
            user_platforms = platforms_query.count()
            
            # Admin users can access the dashboard without platforms
            if user_platforms == 0 and current_user.role != UserRole.ADMIN:
                # Redirect to first-time setup if no platforms (except for admins)
                return redirect(url_for('first_time_setup'))
            
            # Get platform-specific statistics using session-aware context
            context = get_current_session_context()
            current_platform = None
            
            if context and context.get('platform_connection_id'):
                # Check if user has access to the platform in context
                if PlatformAccessMiddleware.check_platform_access(context['platform_connection_id']):
                    current_platform = db_session.query(PlatformConnection).filter_by(
                        id=context['platform_connection_id'],
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
                
                # For admin users without platforms, add admin-specific stats
                if current_user.role == UserRole.ADMIN:
                    stats['admin_mode'] = True
                    stats['total_users'] = db_session.query(User).count()
                    stats['active_users'] = db_session.query(User).filter_by(is_active=True).count()
                    stats['total_platforms'] = db_session.query(PlatformConnection).count()
            
            # Add recent_stats for admin users (regardless of platform status)
            recent_stats = None
            performance_stats = None
            system_health = None
            alerts = None
            if current_user.role == UserRole.ADMIN:
                from datetime import timedelta
                import psutil
                import time
                yesterday = datetime.now(timezone.utc) - timedelta(days=1)
                
                # User statistics
                new_users_24h = db_session.query(User).filter(User.created_at >= yesterday).count()
                unverified_users = db_session.query(User).filter_by(email_verified=False).count()
                locked_accounts = db_session.query(User).filter_by(account_locked=True).count()
                
                # Content processing statistics
                processed_24h = db_session.query(Image).filter(
                    Image.created_at >= yesterday,
                    Image.status.in_([ProcessingStatus.APPROVED, ProcessingStatus.REJECTED])
                ).count()
                
                generated_captions = db_session.query(Image).filter(
                    Image.generated_caption.isnot(None)
                ).count()
                
                approved_captions = db_session.query(Image).filter_by(
                    status=ProcessingStatus.APPROVED
                ).count()
                
                recent_stats = {
                    'new_users_24h': new_users_24h,
                    'unverified_users': unverified_users,
                    'locked_accounts': locked_accounts,
                    'processed_24h': processed_24h,
                    'generated_captions': generated_captions,
                    'approved_captions': approved_captions
                }
                
                # Enhanced stats for admin dashboard
                total_images = db_session.query(Image).count()
                pending_review = db_session.query(Image).filter_by(status=ProcessingStatus.PENDING).count()
                
                # Add missing stats to the existing stats dict
                if 'total_images' not in stats:
                    stats['total_images'] = total_images
                if 'pending_review' not in stats:
                    stats['pending_review'] = pending_review
                
                # Performance statistics
                try:
                    # Get system uptime (simplified)
                    uptime_seconds = time.time() - psutil.boot_time()
                    uptime_hours = int(uptime_seconds // 3600)
                    uptime_days = uptime_hours // 24
                    uptime_hours = uptime_hours % 24
                    
                    if uptime_days > 0:
                        uptime_str = f"{uptime_days}d {uptime_hours}h"
                    else:
                        uptime_str = f"{uptime_hours}h"
                    
                    # Basic performance metrics (simplified for now)
                    performance_stats = {
                        'avg_response_time': '< 200ms',  # Placeholder - could be calculated from logs
                        'error_rate': 0,  # Placeholder - could be calculated from error logs
                        'uptime': uptime_str
                    }
                    
                    # System health assessment using service-based checks (same as admin dashboard)
                    try:
                        system_health = get_simple_system_health_for_index(db_session)
                    except Exception as e:
                        app.logger.error(f"Error checking system health: {sanitize_for_log(str(e))}")
                        system_health = 'warning'
                        
                except Exception as e:
                    # Fallback if psutil is not available or fails
                    performance_stats = {
                        'avg_response_time': 'N/A',
                        'error_rate': 0,
                        'uptime': 'N/A'
                    }
                    system_health = 'unknown'
                
                # System alerts (placeholder - could be enhanced with real alert system)
                alerts = []
                
                # Check for potential alerts
                if unverified_users > 5:
                    alerts.append({
                        'id': 'unverified_users',
                        'severity': 'warning',
                        'type': 'user',
                        'title': 'High Number of Unverified Users',
                        'message': f'{unverified_users} users have not verified their email addresses',
                        'created_at': datetime.now(timezone.utc)
                    })
                
                if locked_accounts > 0:
                    alerts.append({
                        'id': 'locked_accounts',
                        'severity': 'error',
                        'type': 'security',
                        'title': 'Locked User Accounts',
                        'message': f'{locked_accounts} user accounts are currently locked',
                        'created_at': datetime.now(timezone.utc)
                    })
                
                if pending_review > 10:
                    alerts.append({
                        'id': 'pending_review',
                        'severity': 'info',
                        'type': 'content',
                        'title': 'Content Pending Review',
                        'message': f'{pending_review} images are waiting for review',
                        'created_at': datetime.now(timezone.utc)
                    })
            
            return render_template('index.html', stats=stats, current_platform=platform_dict, 
                                 recent_stats=recent_stats, performance_stats=performance_stats,
                                 system_health=system_health, alerts=alerts)
            
    except Exception as e:
        app.logger.error(f"Error loading dashboard: {sanitize_for_log(str(e))}")
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('platform_management'))

# Admin cleanup routes are handled by the admin blueprint at /admin/cleanup

# Admin cleanup routes are handled by the admin blueprint


@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve stored images"""
    return send_from_directory(config.storage.images_dir, filename)

@app.route('/static/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files with correct MIME type"""
    response = send_from_directory(os.path.join(app.root_path, 'static', 'js'), filename)
    response.headers['Content-Type'] = 'application/javascript'
    return response

@app.route('/review')
@login_required
@require_viewer_or_higher
@platform_required
@with_session_error_handling
def review_list():
    """List images pending review (platform-aware)"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    with unified_session_manager.get_db_session() as session:
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
        
        # Apply role-based platform filtering
        query = filter_images_for_user(query)
        
        # Apply additional platform filtering if requested
        platform_filter = request.args.get('platform')
        if platform_filter and platform_filter.isdigit():
            platform_id = int(platform_filter)
            # Check if user has access to this platform
            if PlatformAccessMiddleware.check_platform_access(platform_id):
                query = query.filter(Image.platform_connection_id == platform_id)
        elif current_platform:
            # Default to current platform if user has access
            if PlatformAccessMiddleware.check_platform_access(current_platform.id):
                query = query.filter(Image.platform_connection_id == current_platform.id)
        
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

@app.route('/review/<int:image_id>')
@login_required
@require_viewer_or_higher
@content_access_required
@with_session_error_handling
def review_single(image_id):
    """Review a single image"""
    with unified_session_manager.get_db_session() as session:
        image = session.query(Image).options(
            joinedload(Image.platform_connection),
            joinedload(Image.post)
        ).filter_by(id=image_id).first()
        if not image:
            flash(f'Image with ID {image_id} not found', 'error')
            return redirect(url_for('review_list'))
            
        form = ReviewForm(request.form)
        form.image_id.data = image_id
        form.caption.data = image.generated_caption or ""
        
        return render_template('review_single.html', image=image, form=form)

@app.route('/review/<int:image_id>', methods=['POST'])
@login_required
@require_viewer_or_higher
@content_access_required
@validate_input_length()
@with_session_error_handling
def review_submit(image_id):
    """Submit review for an image"""
    form = ReviewForm(request.form)
    
    if validate_form_submission(form):
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
        
        # Redirect to next image or review list - validate URL to prevent open redirect
        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        else:
            return redirect(url_for('review_list'))
    
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
    with unified_session_manager.get_db_session() as session:
        # Get current platform context
        context = get_current_session_context()
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
@require_viewer_or_higher
@api_content_access_required
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
    with unified_session_manager.get_db_session() as session:
        image_data = None
        platform_config = None
        
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
    with unified_session_manager.get_db_session() as session:
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
        caption_generator = None
        try:
            caption_generator = OllamaCaptionGenerator(config.ollama)
            
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
            if caption_generator:
                caption_generator.cleanup()

@app.route('/post_approved')
@login_required
@with_session_error_handling
def post_approved():
    """Post approved captions to platform"""
    # Get current platform context
    context = get_current_session_context()
    if not context or not context.get('platform_connection_id'):
        flash('No active platform connection found.', 'error')
        return redirect(url_for('platform_management'))
    
    platform_connection_id = context['platform_connection_id']
    
    # Get the image IDs first, so we don't keep the session open during async operations
    with unified_session_manager.get_db_session() as session:
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
            with unified_session_manager.get_db_session() as session:
                # Use direct SQL update to avoid ORM session issues
                from sqlalchemy import text
                ids_str = ','.join(str(id) for id in successful_image_ids)
                sql = text(f"UPDATE images SET status = 'posted', posted_at = CURRENT_TIMESTAMP WHERE id IN ({ids_str})")
                session.execute(sql)
                app.logger.info(f"Successfully marked {sanitize_for_log(str(len(successful_image_ids)))} images as posted")
        except Exception as e:
            app.logger.error(f"Error updating image status: {str(e)}")
    
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
@require_viewer_or_higher
@with_session_error_handling
def platform_management():
    """Platform management interface using shared platform identification"""
    try:
        from platform_utils.platform_identification import identify_user_platform
        
        # Use shared 5-step platform identification
        result = identify_user_platform(
            current_user.id,
            app.config.get('redis_platform_manager'),
            db_manager,
            include_stats=True
        )
        
        # Platform management always shows the interface, even if no platforms
        # (unlike other routes that redirect when no platform is found)
        return render_template('platform_management.html', 
                             platforms=result.user_platforms or [],
                             current_platform=result.current_platform,
                             platform_stats=result.platform_stats or {})
                             
    except Exception as e:
        app.logger.error(f"Error in platform management: {sanitize_for_log(str(e))}")
        flash('An error occurred while loading platform management.', 'error')
        return redirect(url_for('index'))
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

@app.route('/switch_platform/<int:platform_id>')
@login_required
@require_viewer_or_higher
@platform_access_required
@with_session_error_handling
def switch_platform(platform_id):
    """Switch to a different platform using database sessions"""
    try:
        # Verify the platform belongs to the current user
        with request_session_manager.session_scope() as db_session:
            platform = db_session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if not platform:
                flash('Platform not found or not accessible', 'error')
                return redirect(url_for('platform_management'))
            
            platform_name = platform.name  # Extract before session closes
            
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
            
            # Update both Redis session context AND Flask session
            # Using imported update_session_platform function for Redis
            success = update_session_platform(platform_id)
            
            if success:
                # Also update Flask session directly (since we removed old session context system)
                session['platform_connection_id'] = platform_id
                session['platform_name'] = platform_name
                session.permanent = True  # Ensure session persists
                
                flash(f'Switched to platform: {platform_name}', 'success')
                app.logger.info(f"User {sanitize_for_log(current_user.username)} switched to platform {sanitize_for_log(platform_name)}")
            else:
                flash('Failed to switch platform', 'error')
            
    except Exception as e:
        app.logger.error(f"Error switching platform: {e}")
        flash('Error switching platform', 'error')
    
    # Redirect back to the referring page or platform management
    return redirect(request.referrer or url_for('platform_management'))

@app.route('/api/add_platform', methods=['POST'])
@login_required
@require_viewer_or_higher
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
        with unified_session_manager.get_db_session() as session:
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
        
        # Check if this is the user's first platform connection
        with unified_session_manager.get_db_session() as session:
            existing_platforms_count = session.query(PlatformConnection).filter_by(
                user_id=current_user.id,
                is_active=True
            ).count()
            is_first_platform = existing_platforms_count == 0
        
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
                with unified_session_manager.get_db_session() as session:
                    session.delete(platform)
                    session.commit()
                from markupsafe import escape
                return jsonify({'success': False, 'error': f'Connection test failed: {escape(message)}'}), 400
        else:
            app.logger.info(f"Skipping connection test for platform {sanitize_for_log(name)} as requested by user")
        
        # If this is the first platform, automatically switch to it and update session context
        if is_first_platform:
            try:
                # Create or update Redis session using unified session manager
                # Using imported get_current_session_id and update_session_platform functions
                session_id = get_current_session_id()
                db_session_success = False
                
                if not session_id:
                    # Create a new database session for the user
                    try:
                        session_id = unified_session_manager.create_session(current_user.id, platform.id)
                        if session_id:
                            db_session_success = True
                            app.logger.info(f"Created new database session {sanitize_for_log(session_id)} for first platform")
                        else:
                            app.logger.warning(f"Failed to create database session for first platform {sanitize_for_log(name)}")
                    except Exception as session_create_error:
                        app.logger.error(f"Error creating database session for first platform: {sanitize_for_log(str(session_create_error))}")
                else:
                    # Update existing database session
                    db_session_success = update_session_platform(platform.id)
                    if not db_session_success:
                        app.logger.warning(f"Failed to update existing database session {sanitize_for_log(session_id)}")
                        # Try to create a new session if update failed
                        try:
                            new_session_id = unified_session_manager.create_session(current_user.id, platform.id)
                            if new_session_id:
                                db_session_success = True
                                app.logger.info(f"Created replacement database session {sanitize_for_log(new_session_id)} for first platform")
                        except Exception as session_create_error:
                            app.logger.error(f"Error creating replacement database session: {sanitize_for_log(str(session_create_error))}")
                
                if db_session_success:
                    app.logger.info(f"Successfully switched to first platform {sanitize_for_log(name)} for user {sanitize_for_log(current_user.username)} with database session management")
                else:
                    # Database session failed - log warning but continue
                    app.logger.warning(f"Failed to create database session for first platform {sanitize_for_log(name)}")
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
            },
            'is_first_platform': is_first_platform,
            'session_updated': is_first_platform,  # Indicate if session was updated
            'requires_refresh': is_first_platform  # Indicate if page refresh is recommended
        })
        
    except Exception as e:
        app.logger.error(f"Error adding platform connection: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/switch_platform/<int:platform_id>', methods=['POST'])
@login_required
@require_viewer_or_higher
@api_platform_access_required
@with_db_session
@validate_csrf_token
@with_session_error_handling
def api_switch_platform(platform_id):
    """Switch to a different platform using Redis session management"""
    
    # DEBUG: Add detailed logging
    app.logger.info(f"DEBUG: api_switch_platform called with platform_id={platform_id}")
    app.logger.info(f"DEBUG: Request method={request.method}, path={request.path}")
    app.logger.info(f"DEBUG: Request content_type={request.content_type}")
    app.logger.info(f"DEBUG: Request data={request.get_data()}")
    app.logger.info(f"DEBUG: Request form={dict(request.form)}")
    app.logger.info(f"DEBUG: Request json={request.get_json(silent=True)}")
    app.logger.info(f"DEBUG: Current user authenticated={current_user.is_authenticated}")
    app.logger.info(f"DEBUG: Current user ID={getattr(current_user, 'id', 'N/A')}")
    
    # DEBUG: Check session ID retrieval
    # Using imported get_current_session_id function
    session_id = get_current_session_id()
    app.logger.info(f"DEBUG: get_current_session_id() returned: {session_id}")
    
    # DEBUG: Check g object
    app.logger.info(f"DEBUG: g.session_id = {getattr(g, 'session_id', 'NOT_SET')}")
    
    # DEBUG: Check session cookie
    session_cookie_manager = getattr(current_app, 'session_cookie_manager', None)
    if session_cookie_manager:
        cookie_session_id = session_cookie_manager.get_session_id_from_cookie()
        app.logger.info(f"DEBUG: Session ID from cookie: {cookie_session_id}")
    else:
        app.logger.info(f"DEBUG: No session_cookie_manager found")
    
    # DEBUG: Check unified session manager
    unified_session_manager = getattr(current_app, 'unified_session_manager', None)
    app.logger.info(f"DEBUG: unified_session_manager available: {unified_session_manager is not None}")
    
    try:
        # Use Redis platform manager to get platform data
        platform_data = redis_platform_manager.get_platform_by_id(platform_id, current_user.id)
        
        if not platform_data:
            app.logger.warning(f"Platform {platform_id} not found for user {current_user.id}")
            return jsonify({'success': False, 'error': 'Platform not found or not accessible'}), 404
        
        # Verify platform is active
        if not platform_data.get('is_active', False):
            app.logger.warning(f"Platform {platform_id} is not active for user {current_user.id}")
            return jsonify({'success': False, 'error': 'Platform is not active'}), 400
        
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
        
        # Update Redis session platform context
        # Using imported update_session_platform function
        session_updated = update_session_platform(platform_id)
        
        # Also set as default platform in database for persistence
        try:
            db_success = db_manager.set_default_platform(current_user.id, platform_id)
            if not db_success:
                app.logger.warning(f"Failed to set platform {platform_id} as default in database for user {current_user.id}")
        except Exception as e:
            app.logger.error(f"Error setting default platform in database: {sanitize_for_log(str(e))}")
        
        if session_updated:
            # Invalidate Redis cache to ensure fresh data on next request
            redis_platform_manager.invalidate_user_cache(current_user.id)
            
            app.logger.info(f"User {sanitize_for_log(current_user.username)} switched to platform {sanitize_for_log(platform_data['name'])} via Redis session management")
            return jsonify({
                'success': True,
                'message': f'Successfully switched to {platform_data["name"]} ({platform_data["platform_type"].title()})',
                'platform': {
                    'id': platform_data['id'],
                    'name': platform_data['name'],
                    'platform_type': platform_data['platform_type'],
                    'instance_url': platform_data['instance_url'],
                    'username': platform_data.get('username')
                }
            })
        else:
            app.logger.warning(f"Failed to switch platform for user {sanitize_for_log(current_user.username)}")
            return jsonify({'success': False, 'error': 'Failed to switch platform'}), 500
            
    except Exception as e:
        app.logger.error(f"Error switching platform with Redis session management: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to switch platform'}), 500

@app.route('/api/test_platform/<int:platform_id>', methods=['POST'])
@login_required
@require_viewer_or_higher
@api_platform_access_required
@with_session_error_handling
def api_test_platform(platform_id):
    """Test a platform connection"""
    try:
        with unified_session_manager.get_db_session() as session:
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

@app.route('/api/get_platform/<int:platform_id>', methods=['GET'])
@login_required
@with_session_error_handling
def api_get_platform(platform_id):
    """Get platform connection data for editing"""
    try:
        with unified_session_manager.get_db_session() as session:
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
        with unified_session_manager.get_db_session() as session:
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
        with unified_session_manager.get_db_session() as session:
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
        
    except Exception as e:
        app.logger.error(f"Error updating platform connection: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/session/cleanup', methods=['POST'])
@login_required
@validate_csrf_token
@rate_limit(limit=5, window_seconds=60)
@with_session_error_handling
def api_session_cleanup():
    """Clean up expired sessions and notify tabs - integrated session management"""
    try:
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        # Clean up expired database sessions
        expired_count = unified_session_manager.cleanup_user_sessions(user_id)
        
        # Flask session manager removed - using database sessions only
        
        app.logger.info(f"Cleaned up {expired_count} expired sessions for user {sanitize_for_log(str(user_id))}")
        
        return jsonify({
            'success': True,
            'cleaned_sessions': expired_count,
            'message': f'Cleaned up {expired_count} expired sessions'
        })
        
    except Exception as e:
        app.logger.error(f"Error in session cleanup: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to cleanup sessions'}), 500


@app.route('/api/session/notify_logout', methods=['POST'])
@rate_limit(limit=10, window_seconds=60)
@with_session_error_handling
def api_session_notify_logout():
    """Notify other tabs about logout - for cross-tab session synchronization"""
    try:
        # This endpoint can be called without authentication since it's for logout notification
        # Get user info from Redis session if available
        # Using imported get_current_user_id function
        user_id = get_current_user_id()
        
        # Redis sessions are cleared through the unified session manager
        # No Flask session data to clear
        
        app.logger.info(f"Logout notification processed for user {sanitize_for_log(str(user_id)) if user_id else 'unknown'}")
        
        return jsonify({
            'success': True,
            'message': 'Logout notification processed',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error processing logout notification: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to process logout notification'}), 500


# Removed duplicate route - handled by admin blueprint


@app.route('/api/delete_platform/<int:platform_id>', methods=['DELETE'])
@login_required
@with_session_error_handling
def api_delete_platform(platform_id):
    """Delete a platform connection with comprehensive validation"""
    with unified_session_manager.get_db_session() as session:
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
    
    try:
        # Use the database manager's delete method which includes proper validation
        success = db_manager.delete_platform_connection(
            connection_id=platform_id,
            user_id=current_user.id,
            force=False  # Don't force delete, let it check for associated data
        )
        
        # amazonq-ignore-next-line
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
class CaptionGenerationForm(Form):
    """Form for starting caption generation - using regular WTForms (no Flask-WTF CSRF)"""
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

class CaptionSettingsForm(Form):
    """Form for managing caption generation settings - using regular WTForms (no Flask-WTF CSRF)"""
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

# Test route to verify routing works
@app.route('/test_route')
def test_route():
    return "Test route works!"

# Caption Generation Routes
@app.route('/caption_generation')
@login_required
@rate_limit(limit=10, window_seconds=60)
@with_session_error_handling
def caption_generation():
    """Caption generation page - relies on global template context processor for platform data"""
    try:
        # The global template context processor (@app.context_processor) already provides:
        # - current_platform: from platform_stats.get('default_platform')
        # - user_platforms: from platform_stats.get('platforms', [])
        # So we don't need to do platform identification here!
        
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
        
        # Get user's current settings - we need to get the current platform ID from session context
        user_settings = None
        context = get_current_session_context()
        platform_connection_id = context.get('platform_connection_id') if context else None
        
        if platform_connection_id:
            try:
                redis_platform_manager = app.config.get('redis_platform_manager')
                if redis_platform_manager:
                    user_settings_dict = redis_platform_manager.get_user_settings(current_user.id, platform_connection_id)
                    if user_settings_dict:
                        # Convert to dataclass if needed
                        from models import CaptionGenerationUserSettings
                        # Create a mock settings record to use the to_settings_dataclass method
                        mock_settings = CaptionGenerationUserSettings()
                        for key, value in user_settings_dict.items():
                            if hasattr(mock_settings, key):
                                setattr(mock_settings, key, value)
                        user_settings = mock_settings.to_settings_dataclass()
                        app.logger.debug(f"Retrieved user settings from Redis for user {current_user.id}, platform {platform_connection_id}")
                    else:
                        app.logger.info(f"No user settings found for user {current_user.id}, platform {platform_connection_id}")
                
            except Exception as e:
                app.logger.error(f"Error getting user settings from Redis: {sanitize_for_log(str(e))}")
            
            # Fallback to database if Redis settings lookup failed
            if not user_settings:
                try:
                    with unified_session_manager.get_db_session() as session:
                        from models import CaptionGenerationUserSettings
                        user_settings_record = session.query(CaptionGenerationUserSettings).filter_by(
                            user_id=current_user.id,
                            platform_connection_id=platform_connection_id
                        ).first()
                        
                        if user_settings_record:
                            user_settings = user_settings_record.to_settings_dataclass()
                except Exception as e:
                    app.logger.error(f"Error getting user settings from database: {sanitize_for_log(str(e))}")
        
        # Create form with current settings
        form = CaptionGenerationForm(request.form if request.method == 'POST' else None)
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
        flash('An error occurred while loading the caption generation page.', 'error')
        return redirect(url_for('index'))
        
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
        
        # Get user's current settings using the platform we already identified
        user_settings = None
        redis_platform_manager = app.config.get('redis_platform_manager')
        
        try:
            # We already have the platform data from our identification, so use it directly
            # Get user settings from Redis (with database fallback)
            if redis_platform_manager:
                user_settings_dict = redis_platform_manager.get_user_settings(current_user.id, platform_connection_id)
                if user_settings_dict:
                    # Convert to dataclass if needed
                    from models import CaptionGenerationUserSettings
                    # Create a mock settings record to use the to_settings_dataclass method
                    mock_settings = CaptionGenerationUserSettings()
                    for key, value in user_settings_dict.items():
                        if hasattr(mock_settings, key):
                            setattr(mock_settings, key, value)
                    user_settings = mock_settings.to_settings_dataclass()
                    app.logger.debug(f"Retrieved user settings from Redis for user {current_user.id}, platform {platform_connection_id}")
                else:
                    app.logger.info(f"No user settings found for user {current_user.id}, platform {platform_connection_id}")
            
        except Exception as e:
            app.logger.error(f"Error getting user settings from Redis: {sanitize_for_log(str(e))}")
        
        # Fallback to database if Redis settings lookup failed
        if not user_settings:
            try:
                with unified_session_manager.get_db_session() as session:
                    from models import CaptionGenerationUserSettings
                    user_settings_record = session.query(CaptionGenerationUserSettings).filter_by(
                        user_id=current_user.id,
                        platform_connection_id=platform_connection_id
                    ).first()
                    
                    if user_settings_record:
                        user_settings = user_settings_record.to_settings_dataclass()
            except Exception as e:
                app.logger.error(f"Error getting user settings from database: {sanitize_for_log(str(e))}")
        
        # Create form with current settings
        form = CaptionGenerationForm(request.form if request.method == 'POST' else None)
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
        flash('An error occurred while loading the caption generation page.', 'error')
        return redirect(url_for('index'))
        
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
        
        # Get user's current settings using the platform we already identified
        user_settings = None
        redis_platform_manager = app.config.get('redis_platform_manager')
        
        try:
            # We already have the platform data from our identification, so use it directly
            # Get user settings from Redis (with database fallback)
            if redis_platform_manager:
                user_settings_dict = redis_platform_manager.get_user_settings(current_user.id, platform_connection_id)
                if user_settings_dict:
                    # Convert to dataclass if needed
                    from models import CaptionGenerationUserSettings
                    # Create a mock settings record to use the to_settings_dataclass method
                    mock_settings = CaptionGenerationUserSettings()
                    for key, value in user_settings_dict.items():
                        if hasattr(mock_settings, key):
                            setattr(mock_settings, key, value)
                    user_settings = mock_settings.to_settings_dataclass()
                    app.logger.debug(f"Retrieved user settings from Redis for user {current_user.id}, platform {platform_connection_id}")
                else:
                    app.logger.info(f"No user settings found for user {current_user.id}, platform {platform_connection_id}")
            
        except Exception as e:
            app.logger.error(f"Error getting user settings from Redis: {sanitize_for_log(str(e))}")
        
        # Fallback to database if Redis settings lookup failed
        if not user_settings:
            try:
                with unified_session_manager.get_db_session() as session:
                    from models import CaptionGenerationUserSettings
                    user_settings_record = session.query(CaptionGenerationUserSettings).filter_by(
                        user_id=current_user.id,
                        platform_connection_id=platform_connection_id
                    ).first()
                    
                    if user_settings_record:
                        user_settings = user_settings_record.to_settings_dataclass()
            except Exception as e:
                app.logger.error(f"Error getting user settings from database: {sanitize_for_log(str(e))}")
        
        # Create form with current settings
        form = CaptionGenerationForm(request.form if request.method == 'POST' else None)
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
    form = CaptionGenerationForm(request.form)
    
    if validate_form_submission(form):
        try:
            # Get current platform context
            context = get_current_session_context()
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
        context = get_current_session_context()
        if not context or not context.get('platform_connection_id'):
            flash('No active platform connection found.', 'error')
            return redirect(url_for('platform_management'))
        
        platform_connection_id = context['platform_connection_id']
        
        # Get user's current settings using Redis platform manager
        try:
            # Get user settings from Redis (with database fallback)
            user_settings_dict = redis_platform_manager.get_user_settings(current_user.id, platform_connection_id)
            
            # Create form with current settings
            form = CaptionSettingsForm(request.form if request.method == 'POST' else None)
            if user_settings_dict:
                form.max_posts_per_run.data = user_settings_dict.get('max_posts_per_run', 50)
                form.max_caption_length.data = user_settings_dict.get('max_caption_length', 500)
                form.optimal_min_length.data = user_settings_dict.get('optimal_min_length', 80)
                form.optimal_max_length.data = user_settings_dict.get('optimal_max_length', 200)
                form.reprocess_existing.data = user_settings_dict.get('reprocess_existing', False)
                form.processing_delay.data = user_settings_dict.get('processing_delay', 1.0)
                app.logger.debug(f"Retrieved user settings from Redis for caption settings form")
            else:
                app.logger.info(f"No user settings found in Redis, using defaults for caption settings form")
                
        except Exception as e:
            app.logger.error(f"Error getting user settings from Redis: {sanitize_for_log(str(e))}")
            # Fallback to database if Redis fails
            with unified_session_manager.get_db_session() as session:
                from models import CaptionGenerationUserSettings
                user_settings_record = session.query(CaptionGenerationUserSettings).filter_by(
                    user_id=current_user.id,
                    platform_connection_id=platform_connection_id
                ).first()
                
                # Create form with current settings
                form = CaptionSettingsForm(request.form if request.method == 'POST' else None)
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
        context = get_current_session_context()
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
    form = CaptionSettingsForm(request.form)
    
    if validate_form_submission(form):
        try:
            # Get current platform context
            context = get_current_session_context()
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

# Admin API routes are handled by the admin blueprint at /admin/api/

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
        context = get_current_session_context()
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

# Administrative routes are handled by the admin blueprint at /admin/

@app.route('/api/csrf-token', methods=['GET'])
@login_required
@rate_limit(limit=20, window_seconds=60)
@with_session_error_handling
def api_get_csrf_token():
    """Get a fresh CSRF token for AJAX requests using Redis session-aware generation"""
    try:
        # Use our Redis-aware CSRF token manager
        csrf_manager = getattr(app, 'csrf_token_manager', None)
        if not csrf_manager:
            # Fallback: create a temporary CSRF manager
            from security.core.csrf_token_manager import CSRFTokenManager
            csrf_manager = CSRFTokenManager()
        
        # Generate CSRF token using Redis session ID
        csrf_token = csrf_manager.generate_token()
        
        return jsonify({
            'success': True,
            'csrf_token': csrf_token,
            'expires_in': csrf_manager.token_lifetime
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
        context = get_current_session_context()
        if not context or not context.get('platform_connection_id'):
            return jsonify({'success': False, 'error': 'No active platform connection found'}), 400
        
        platform_connection_id = context['platform_connection_id']
        
        # Validate max_posts_per_run
        max_posts_per_run = data.get('max_posts_per_run')
        if max_posts_per_run is not None:
            if not isinstance(max_posts_per_run, int) or max_posts_per_run < 1 or max_posts_per_run > 500:
                return jsonify({'success': False, 'error': 'Max posts per run must be between 1 and 500'}), 400
        
        # Update or create user settings using Redis platform manager
        try:
            # Prepare settings data
            settings_data = {
                'max_posts_per_run': max_posts_per_run or 50,
                'max_caption_length': 500,
                'optimal_min_length': 80,
                'optimal_max_length': 200,
                'reprocess_existing': False,
                'processing_delay': 1.0
            }
            
            # Update settings using Redis platform manager
            success = redis_platform_manager.update_user_settings(
                current_user.id, 
                platform_connection_id, 
                settings_data
            )
            
            if success:
                app.logger.info(f"Updated user settings via Redis for user {sanitize_for_log(str(current_user.id))} platform {sanitize_for_log(str(platform_connection_id))}")
                
                return jsonify({
                    'success': True,
                    'message': 'Settings updated successfully',
                    'settings': {
                        'max_posts_per_run': settings_data['max_posts_per_run']
                    }
                })
            else:
                # Fallback to database if Redis update fails
                app.logger.warning("Redis settings update failed, falling back to database")
                with unified_session_manager.get_db_session() as session:
                    from models import CaptionGenerationUserSettings
                    
                    # Get existing settings or create new ones
                    user_settings = session.query(CaptionGenerationUserSettings).filter_by(
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
                        session.add(user_settings)
                    else:
                        # Update existing settings
                        if max_posts_per_run is not None:
                            user_settings.max_posts_per_run = max_posts_per_run
                        user_settings.updated_at = datetime.now(timezone.utc)
                    
                    session.commit()
                    
                    app.logger.info(f"Updated user settings via database fallback for user {sanitize_for_log(str(current_user.id))} platform {sanitize_for_log(str(platform_connection_id))}")
                    
                    return jsonify({
                        'success': True,
                        'message': 'Settings updated successfully',
                        'settings': {
                            'max_posts_per_run': user_settings.max_posts_per_run
                        }
                    })
                    
        except Exception as e:
            app.logger.error(f"Error updating user settings via Redis: {sanitize_for_log(str(e))}")
            return jsonify({'success': False, 'error': 'Failed to update settings'}), 500
            
    except Exception as e:
        app.logger.error(f"Error updating user settings: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to update settings'}), 500

# Admin API routes are handled by the admin blueprint

# Profile Management Routes
# NOTE: Profile management routes have been moved to routes/user_management_routes.py
# The new user management system provides comprehensive profile management with GDPR compliance

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
@login_required
@validate_csrf_token
@rate_limit(limit=10, window_seconds=60)
@with_session_error_handling
def api_terminate_session(session_id):
    """Terminate a specific session"""
    try:
        # For now, we only support terminating the current session
        # In a full implementation, you'd validate session ownership and terminate specific sessions
        # Using imported get_current_session_id function
        current_session_id = get_current_session_id()
        if session_id == 'current' or session_id == current_session_id:
            # Destroy current Redis session
            if current_session_id:
                unified_session_manager.destroy_session(current_session_id)
            return jsonify({
                'success': True,
                'message': 'Session terminated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Can only terminate current session'
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error terminating session: {sanitize_for_log(str(e))}")
        return jsonify({'success': False, 'error': 'Failed to terminate session'}), 500




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


# Register user management routes
from routes.user_management_routes import register_user_management_routes
register_user_management_routes(app)

# Register GDPR routes
from routes.gdpr_routes import gdpr_bp
app.register_blueprint(gdpr_bp)


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
            'data: {"type": "error", "message": "Authentication required"}\n\n',
            mimetype='text/event-stream',
            status=401
        )
    
    app.logger.info(f"SSE connection request for task {sanitize_for_log(task_id)} from user {sanitize_for_log(str(current_user.id))}")
    
    # Initialize event stream generator to None for proper resource management
    event_stream = None
    try:
        # Create event stream with proper resource initialization
        event_stream = sse_progress_handler.create_event_stream(task_id)
        
        return Response(
            event_stream,
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
        # Clean up event stream resources if initialization failed
        if event_stream and hasattr(event_stream, 'close'):
            try:
                event_stream.close()
            except Exception as cleanup_error:
                app.logger.warning(f"Error cleaning up event stream: {sanitize_for_log(str(cleanup_error))}")
        
        return Response(
            'data: {"type": "error", "message": "Stream initialization failed"}\n\n',
            mimetype='text/event-stream',
            status=500
        )

def get_simple_system_health_for_index(db_session):
    """Get a simple system health status for the index route (using existing db_session)"""
    try:
        # Check database connectivity (using existing session)
        try:
            from sqlalchemy import text
            db_session.execute(text("SELECT 1"))
            db_healthy = True
        except Exception:
            db_healthy = False
        
        # Check if Ollama is accessible (simple HTTP check)
        ollama_healthy = True
        try:
            import httpx
            import os
            ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{ollama_url}/api/tags")
                ollama_healthy = response.status_code == 200
        except Exception:
            ollama_healthy = False
        
        # Check storage (basic directory check)
        storage_healthy = True
        try:
            import os
            storage_dirs = ['storage', 'storage/database', 'storage/images']
            for dir_path in storage_dirs:
                if not os.path.exists(dir_path):
                    storage_healthy = False
                    break
        except Exception:
            storage_healthy = False
        
        # Determine overall health
        if db_healthy and ollama_healthy and storage_healthy:
            return 'healthy'
        elif db_healthy:  # Database is most critical
            return 'warning'
        else:
            return 'critical'
            
    except Exception as e:
        app.logger.error(f"Error checking system health: {e}")
        return 'warning'

if __name__ == '__main__':
    try:
        app.run(
            host=config.webapp.host,
            port=config.webapp.port,
            debug=config.webapp.debug
        )
    except KeyboardInterrupt:
        app.logger.info("Application shutdown requested")
    except Exception as e:
        app.logger.error(f"Application startup failed: {sanitize_for_log(str(e))}")
        raise
    finally:
        # Clean up resources on application shutdown
        try:
            if 'sse_progress_handler' in globals() and hasattr(sse_progress_handler, 'cleanup'):
                sse_progress_handler.cleanup()
        except Exception as cleanup_error:
            app.logger.warning(f"Error during application cleanup: {sanitize_for_log(str(cleanup_error))}")