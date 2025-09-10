# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MIGRATION NOTE: Flash messages in this file have been commented out as part of
# the notification system migration. The application now uses the unified
# WebSocket-based notification system. These comments should be replaced with
# appropriate unified notification calls in a future update.


from user_profile_notification_helper import send_profile_notification
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
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, g, Response, make_response, current_app, session
from flask_socketio import SocketIO
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
from app.core.database.core.database_manager import DatabaseManager
from models import ProcessingStatus, Image, Post, User, UserRole, ProcessingRun, PlatformConnection
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from app.services.activitypub.components.activitypub_client import ActivityPubClient
from app.utils.processing.ollama_caption_generator import OllamaCaptionGenerator
from app.utils.processing.caption_quality_assessment import CaptionQualityManager
from app.services.monitoring.health.health_check import HealthChecker
# Use new Redis session middleware V2 for session context
from app.core.session.middleware.session_middleware import get_current_session_context, get_current_session_id, get_current_user_id, update_session_platform
# Removed Flask session manager imports - using database sessions only
from app.core.session.managers.request_scoped_session_manager import RequestScopedSessionManager
from app.core.session.components.session_aware_user import SessionAwareUser
from app.core.session.decorators.session_aware_decorators import with_db_session, require_platform_context
from app.core.security.core.security_utils import sanitize_for_log, sanitize_html_input
from app.core.security.validation.enhanced_input_validation import enhanced_input_validation, EnhancedInputValidator
from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import EnhancedMaintenanceModeService
from app.services.maintenance.components.maintenance_mode_middleware import MaintenanceModeMiddleware
from app.core.security.core.security_middleware import SecurityMiddleware, require_https, validate_csrf_token, sanitize_filename, generate_secure_token, rate_limit, validate_input_length, require_secure_connection
from app.core.security.decorators.security_decorators import conditional_rate_limit, conditional_validate_csrf_token, conditional_validate_input_length, conditional_enhanced_input_validation
from app.core.security.core.role_based_access import require_role, require_admin, require_viewer_or_higher, platform_access_required, content_access_required, api_require_admin, api_platform_access_required, api_content_access_required
from app.core.security.middleware.platform_access_middleware import PlatformAccessMiddleware, filter_images_for_user, filter_posts_for_user, filter_platforms_for_user
from app.core.security.core.security_config import security_config
from app.core.security.features.caption_security import CaptionSecurityManager, caption_generation_auth_required, validate_task_access, caption_generation_rate_limit, validate_caption_settings_input, log_caption_security_event
from error_recovery_manager import error_recovery_manager
from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService
from app.utils.processing.caption_review_integration import CaptionReviewIntegration

from app.core.security.logging.secure_error_handlers import register_secure_error_handlers
# Removed WebSocketProgressHandler import - using SSE instead
from app.services.monitoring.progress.progress_tracker import ProgressTracker
from app.services.task.core.task_queue_manager import TaskQueueManager

app = Flask(__name__)
config = Config()
app.config['SECRET_KEY'] = config.webapp.secret_key

# Initialize WebSocket system using consolidated components
from app.websocket.core.config_manager import ConsolidatedWebSocketConfigManager
from app.websocket.core.factory import WebSocketFactory
from app.websocket.core.auth_handler import WebSocketAuthHandler
from app.websocket.core.namespace_manager import WebSocketNamespaceManager
from app.websocket.middleware.security_manager import ConsolidatedWebSocketSecurityManager
from app.websocket.services.error_handler import ConsolidatedWebSocketErrorHandler

# Initialize WebSocket configuration manager
websocket_config_manager = ConsolidatedWebSocketConfigManager(config)
websocket_config = websocket_config_manager.get_websocket_config()
app.logger.debug("WebSocket configuration manager initialized")

# Initialize WebSocket security manager
websocket_security_manager = ConsolidatedWebSocketSecurityManager()
app.logger.debug("WebSocket security manager initialized")

# Initialize WebSocket error handler
websocket_error_handler = ConsolidatedWebSocketErrorHandler()
app.logger.debug("WebSocket error handler initialized")

# Initialize WebSocket factory
websocket_factory = WebSocketFactory(websocket_config_manager)
app.logger.debug("WebSocket factory initialized")

# WebSocket authentication handler will be initialized after session manager
# WebSocket namespace manager and SocketIO will be initialized after session manager

# Initialize legacy CORS support for backward compatibility
from flask_cors import CORS
CORS(app, origins=["http://localhost:5000"], supports_credentials=True) 

# Progress handler now integrated into consolidated WebSocket system

app.config['SQLALCHEMY_DATABASE_URI'] = config.storage.database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Redis Session Management System (restored after WebSocket analysis)
from flask_redis_session_interface import FlaskRedisSessionInterface
from redis_session_backend import RedisSessionBackend

# Initialize Redis session backend
try:
    
    # Set up Flask Redis session interface
    redis_session_interface = FlaskRedisSessionInterface(
        redis_client=redis_backend.redis,
        key_prefix=os.getenv('REDIS_SESSION_PREFIX', 'vedfolnir:session:'),
        session_timeout=int(os.getenv('REDIS_SESSION_TIMEOUT', '7200'))
    )
    app.session_interface = redis_session_interface
    app.logger.debug("Flask Redis session interface configured")
    
    # Store Redis backend for later use
    app.redis_backend = redis_backend
    
except Exception as e:
    
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
else:

# Exempt session heartbeat from CSRF protection
# Note: CSRF exemptions are applied after route registration

# Initialize pre-authentication session handler for CSRF tokens
from pre_auth_session import PreAuthSessionHandler
pre_auth_handler = PreAuthSessionHandler(app)
app.logger.debug("Pre-authentication session handler initialized for CSRF tokens")

# Initialize enhanced CSRF token manager
from app.core.security.core.csrf_token_manager import initialize_csrf_token_manager
csrf_token_manager = initialize_csrf_token_manager(app)

# Initialize platform access middleware
platform_access_middleware = PlatformAccessMiddleware(app)

# Template context processor for role-based access control
@app.context_processor
def inject_role_context():
    """Inject role-based context into templates using current session context"""
    if current_user.is_authenticated:
        # Use session context for platform information instead of manual detection
        session_context = get_current_session_context()
        
        # Get platform stats using session-aware methods
        platform_stats = platform_access_middleware.get_user_platform_stats()
        content_stats = platform_access_middleware.get_user_content_stats()
        
        # Get current platform from session context
        current_platform = None
        if session_context and session_context.get('platform_connection_id'):
            # Build current platform info from session context
            current_platform = {
                'id': session_context.get('platform_connection_id'),
                'name': session_context.get('platform_name'),
                'type': session_context.get('platform_type'),
                'instance_url': session_context.get('platform_instance_url')
            }
        
        context = {
            'user_role': current_user.role,
            'is_admin': current_user.role == UserRole.ADMIN,
            'is_viewer': current_user.role == UserRole.VIEWER,
            'user_platforms': platform_stats.get('platforms', []),
            'user_platform_count': platform_stats.get('platform_count', 0),
            'current_platform': current_platform,
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
from app.core.security.core.csrf_error_handler import register_csrf_error_handlers
csrf_error_handler = register_csrf_error_handlers(app)

# Initialize CSRF middleware
from app.core.security.core.csrf_middleware import initialize_csrf_middleware
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

# Security headers middleware (conditional)
if SECURITY_HEADERS_ENABLED:
    @app.after_request
    def add_security_headers(response):
        """Add comprehensive security headers to all responses"""
        # Skip WebSocket requests to prevent WSGI protocol violations
        if (request.headers.get('Upgrade', '').lower() == 'websocket' or
            'websocket' in request.headers.get('Connection', '').lower() or
            request.path.startswith('/socket.io/') or
            request.args.get('transport') in ['websocket', 'polling']):
            return response
        
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
            "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com https://cdn.jsdelivr.net https://cdn.socket.io https://kit.fontawesome.com https://ka-f.fontawesome.com; "
            "style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com cdn.jsdelivr.net fonts.googleapis.com https://ka-f.fontawesome.com; "
            "font-src 'self' data: https:; "
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

# Initialize database and quality manager
db_manager = DatabaseManager(config)
quality_manager = CaptionQualityManager()

# Initialize health checker
health_checker = HealthChecker(config, db_manager)
app.config['health_checker'] = health_checker

# Initialize session management system
from app.core.session.manager import SessionManagerV2
from app.core.session.middleware.session_middleware import SessionMiddleware
from app.core.session.security.session_security import create_session_security_manager
from app.services.monitoring.session.session_monitoring import SessionMonitor

# Create session monitor
session_monitor = SessionMonitor(db_manager)

# Create session security manager
session_security_manager = create_session_security_manager(app.config, db_manager)

# Create Redis-based session manager
if hasattr(app, 'redis_backend') and app.redis_backend:
else:

from app.websocket.core.auth_handler import WebSocketAuthHandler
from app.websocket.core.namespace_manager import WebSocketNamespaceManager

# Store unified_session_manager on app object for direct access
app.unified_session_manager = unified_session_manager
app.session_manager = unified_session_manager  # For compatibility

# Now initialize WebSocket components that require session manager
# Initialize WebSocket authentication handler
websocket_auth_handler = WebSocketAuthHandler(
)
app.logger.debug("WebSocket authentication handler initialized")

# Create SocketIO instance using factory first
socketio = websocket_factory.create_socketio_instance(app)
app.logger.debug("SocketIO instance created using WebSocket factory")

# Initialize WebSocket namespace manager with SocketIO instance
websocket_namespace_manager = WebSocketNamespaceManager(socketio, websocket_auth_handler)
app.logger.debug("WebSocket namespace manager initialized")

# Store WebSocket components for later use
app.websocket_config_manager = websocket_config_manager
app.websocket_security_manager = websocket_security_manager
app.websocket_error_handler = websocket_error_handler
app.websocket_factory = websocket_factory
app.websocket_auth_handler = websocket_auth_handler
app.websocket_namespace_manager = websocket_namespace_manager

# Initialize unified notification system components
from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from notification_message_router import NotificationMessageRouter
from app.services.notification.components.notification_persistence_manager import NotificationPersistenceManager
from dashboard_notification_handlers import register_dashboard_notification_handlers

# Initialize unified notification system
try:
    
    # Initialize notification message router
    notification_message_router = NotificationMessageRouter(websocket_namespace_manager)
    app.logger.debug("Notification message router initialized")
    
    # Initialize unified notification manager
    unified_notification_manager = UnifiedNotificationManager(
        websocket_factory=websocket_factory,
        auth_handler=websocket_auth_handler,
        namespace_manager=websocket_namespace_manager,
        db_manager=db_manager
    )
    app.logger.debug("Unified notification manager initialized")
    
    # Register dashboard notification handlers
    dashboard_handlers = register_dashboard_notification_handlers(socketio, unified_notification_manager)
    app.logger.debug("Dashboard notification handlers registered")
    
    # Register admin health WebSocket handlers
    # Temporarily disabled to fix WebSocket disconnect handler conflicts
    # from admin_health_websocket_handlers import register_admin_health_websocket_handlers
    # register_admin_health_websocket_handlers(socketio)
    # app.logger.info("Admin health WebSocket handlers registered")
    
    # Initialize page notification integrator
    from page_notification_integrator import PageNotificationIntegrator
    page_notification_integrator = PageNotificationIntegrator(
        websocket_factory=websocket_factory,
        auth_handler=websocket_auth_handler,
        namespace_manager=websocket_namespace_manager,
        notification_manager=unified_notification_manager
    )
    app.logger.debug("Page notification integrator initialized")
    
    # Store notification components for later use
    app.notification_persistence_manager = notification_persistence_manager
    app.notification_message_router = notification_message_router
    app.unified_notification_manager = unified_notification_manager
    app.notification_manager = unified_notification_manager  # Alias for progress tracker
    app.dashboard_handlers = dashboard_handlers
    app.page_notification_integrator = page_notification_integrator
    
except Exception as e:

# Initialize session middleware
if hasattr(app, 'redis_backend') and app.redis_backend:
else:

# Initialize session error handler
from session_error_handling import create_session_error_handler
if hasattr(app, 'redis_backend') and app.redis_backend:
else:

# Add CORS headers for API and Socket.IO endpoints
# Add CORS headers for API and Socket.IO endpoints
@app.after_request
def after_request(response):
    """Add CORS headers to API and Socket.IO responses"""
    # Skip WebSocket requests to prevent WSGI protocol violations
    if (request.headers.get('Upgrade', '').lower() == 'websocket' or
        'websocket' in request.headers.get('Connection', '').lower() or
        request.args.get('transport') == 'websocket'):
        return response
    
    # Add CORS headers to API endpoints and Socket.IO
    if request.path.startswith('/api/') or request.path.startswith('/socket.io/'):
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = '*' # Fallback for non-browser requests

        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-CSRF-Token'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Type, X-CSRF-Token'
        
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response.headers['Access-Control-Max-Age'] = '86400'
    
    return response

# Add explicit OPTIONS handler for Socket.IO
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
from app.services.monitoring.performance.monitors.session_performance_monitor import initialize_performance_monitoring
from session_monitoring_cli import register_session_monitoring_commands
from session_monitoring_routes import register_session_monitoring_routes
from session_performance_optimizer import initialize_session_optimizations

# Initialize performance monitoring with database engine
session_performance_monitor = initialize_performance_monitoring(app, request_session_manager, db_manager.engine)

# Initialize session performance optimizations
try:
except Exception as e:

# Register CLI commands and web routes for monitoring
register_session_monitoring_commands(app)
register_session_monitoring_routes(app)

# Initialize session health checking and alerting system
from app.services.monitoring.health.checkers.session_health_checker import get_session_health_checker
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
except ImportError:

# Initialize Redis platform manager
from redis_platform_manager import get_redis_platform_manager
import os
encryption_key = os.getenv('PLATFORM_ENCRYPTION_KEY', 'default-key-change-in-production')

if hasattr(app, 'redis_backend') and app.redis_backend:
else:

if redis_platform_manager:

# Register session health routes
register_session_health_routes(app)

# Register session alert routes
from session_alert_routes import register_session_alert_routes
register_session_alert_routes(app)

# Register security audit API routes
from app.blueprints.admin.security_audit_api import register_security_audit_api_routes
register_security_audit_api_routes(app)
app.logger.debug("Security audit API routes registered")

# Initialize security middleware
security_middleware = SecurityMiddleware(app)

# Initialize caption security manager
caption_security_manager = CaptionSecurityManager(db_manager)
app.config['db_manager'] = db_manager
app.config['caption_security_manager'] = caption_security_manager

# Initialize system configuration manager
from app.core.configuration.core.system_configuration_manager import SystemConfigurationManager
system_configuration_manager = SystemConfigurationManager(db_manager)
app.config['system_configuration_manager'] = system_configuration_manager

# Initialize configuration service
from app.core.configuration.core.configuration_service import ConfigurationService
configuration_service = ConfigurationService(db_manager)
app.config['configuration_service'] = configuration_service

# Initialize enhanced maintenance mode service
maintenance_service = EnhancedMaintenanceModeService(configuration_service)
app.config['maintenance_service'] = maintenance_service

# Initialize maintenance mode middleware
maintenance_middleware = MaintenanceModeMiddleware(app, maintenance_service)
app.config['maintenance_middleware'] = maintenance_middleware

# Initialize maintenance mode service
from app.services.maintenance.components.maintenance_mode_service import MaintenanceModeService
maintenance_service = MaintenanceModeService(configuration_service)
app.maintenance_service = maintenance_service

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

# Initialize WebSocket authentication handler
try:
    
    # Initialize WebSocket namespace manager
    websocket_namespace_manager = WebSocketNamespaceManager(socketio, websocket_auth_handler)
    app.logger.debug("WebSocket namespace manager initialized")
    
    # Store WebSocket components for access by other modules
    app.websocket_auth_handler = websocket_auth_handler
    app.websocket_namespace_manager = websocket_namespace_manager
    
    # Initialize WebSocket progress handler with new namespace system
    from app.websocket.progress.progress_handler import WebSocketProgressHandler
    websocket_progress_handler = WebSocketProgressHandler()
    
    # Update progress handler to use new namespace system
    if hasattr(websocket_progress_handler, 'set_namespace_manager'):
        websocket_progress_handler.set_namespace_manager(websocket_namespace_manager)
    
    app.logger.debug("WebSocket progress handlers initialized with namespace system")
    
except Exception as e:
    
    # Fallback handlers that do nothing
    class FallbackWebSocketHandler:
        def broadcast_progress_update(self, task_id, progress_data):
            pass
        def broadcast_task_completion(self, task_id, results):
            pass
        def broadcast_task_error(self, task_id, error_message):
            pass
        def cleanup_task_connections(self, task_id):
            pass
        def cleanup(self):
            pass
        def set_namespace_manager(self, manager):
            pass
    
    class FallbackAdminWebSocketHandler:
        def broadcast_system_metrics(self, metrics):
            pass
        def broadcast_job_update(self, job_data):
            pass
        def broadcast_alert(self, alert_data):
            pass
        def set_namespace_manager(self, manager):
            pass
    
    class FallbackAuthHandler:
        def authenticate_connection(self, auth_data=None, namespace='/'):
            from app.websocket.core.auth_handler import AuthenticationResult
            return AuthenticationResult.SYSTEM_ERROR, None
        def get_authentication_stats(self):
            return {'error': 'Authentication handler not available'}
    
    class FallbackNamespaceManager:
        def get_namespace_stats(self, namespace):
            return {'error': 'Namespace manager not available'}
        def broadcast_to_namespace(self, namespace, event, data, role_filter=None):
            return False
    
    websocket_progress_handler = FallbackWebSocketHandler()
    websocket_auth_handler = FallbackAuthHandler()
    websocket_namespace_manager = FallbackNamespaceManager()
    
    # Store fallback components
    app.websocket_auth_handler = websocket_auth_handler
    app.websocket_namespace_manager = websocket_namespace_manager

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
        app.logger.debug("All required favicon and logo assets are present")
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
                app.logger.debug(f"User not found or inactive for ID: {user_id_int}")
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
                        # Send error notification
                        from app.services.notification.helpers.notification_helpers import send_error_notification
                        send_error_notification("User authentication error. Please log in again.", "Error")
                        logout_user()
                        return redirect(url_for('user_management.login'))
                        
                    server_user = session.query(User).get(user_id)
                    if not server_user:
                        app.logger.warning(f"User account not found for ID: {user_id}")
                        # Send error notification
                        from app.services.notification.helpers.notification_helpers import send_error_notification
                        send_error_notification("User account not found.", "Error")
                        logout_user()
                        return redirect(url_for('user_management.login'))
                    if not server_user.is_active:
                        app.logger.warning(f"Inactive user attempted access: {sanitize_for_log(server_user.username)}")
                        # Send error notification
                        from app.services.notification.helpers.notification_helpers import send_error_notification
                        send_error_notification("Your account has been deactivated.", "Error")
                        logout_user()
                        return redirect(url_for('user_management.login'))
                    
                    # Debug logging for role checking
                    app.logger.debug(f"Role check: user={server_user.username}, user_role={server_user.role}, required_role={role}")
                    app.logger.debug(f"Role check: user_role.value={server_user.role.value if server_user.role else 'None'}")
                    app.logger.debug(f"Role check: has_permission={server_user.has_permission(role)}")
                    
                    # Use server-side user data for role validation
                    if not server_user.has_permission(role):
                        app.logger.warning(f"Access denied: user {sanitize_for_log(server_user.username)} (role: {sanitize_for_log(server_user.role.value if server_user.role else 'None')}) attempted to access {sanitize_for_log(role.value)} resource")
                        # Send error notification
                        from app.services.notification.helpers.notification_helpers import send_error_notification
                        send_error_notification("You do not have permission to access this page.", "Error")
                        return redirect(url_for('main.index'))
                    
                    app.logger.debug(f"Access granted: user {sanitize_for_log(server_user.username)} has {sanitize_for_log(role.value)} permission")
                    # Store validated user role in g for this request
                    g.validated_user_role = server_user.role
            except SQLAlchemyError as e:
                app.logger.error(f"Database error during authorization: {sanitize_for_log(str(e))}")
                # Send error notification
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification("Authorization error. Please try again.", "Error")
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
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification("User authentication error. Please log in again.", "Error")
                    return redirect(url_for('user_management.login'))
                    
                user_platforms = db_session.query(PlatformConnection).filter_by(
                    user_id=user_id,
                    is_active=True
                ).count()
                
                if user_platforms == 0:
                    # Send warning notification
                    from app.services.notification.helpers.notification_helpers import send_warning_notification
                    send_warning_notification("You need to set up at least one platform connection to access this feature.", "Warning")
                    return redirect(url_for('first_time_setup'))
                else:
                    # Send warning notification
                    from app.services.notification.helpers.notification_helpers import send_warning_notification
                    send_warning_notification("Please select a platform to continue.", "Warning")
                    return redirect(url_for('platform.management'))
        
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
                # Send error notification
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification("No active platform connection found.", "Error")
                return redirect(url_for('platform.management'))
            
            # Get current platform from database to avoid DetachedInstanceError
            with request_session_manager.session_scope() as db_session:
                user_id = getattr(current_user, 'id', None)
                if not user_id:
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification("User authentication error. Please log in again.", "Error")
                    return redirect(url_for('user_management.login'))
                    
                current_platform = db_session.query(PlatformConnection).filter_by(
                    id=context['platform_connection_id'],
                    user_id=user_id,
                    is_active=True
                ).first()
                
                if not current_platform:
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification("Current platform connection is no longer available.", "Error")
                    return redirect(url_for('platform.management'))
                
                # Extract platform data before closing session
                platform_type_actual = current_platform.platform_type
                instance_url_actual = current_platform.instance_url
            
            # Validate platform type if specified
            if platform_type and platform_type_actual != platform_type:
                # Send error notification
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification(f'This feature requires a {platform_type.title()} connection. Current platform: {platform_type_actual.title()}', "Platform Mismatch")
                return redirect(url_for('platform.management'))
            
            # Validate instance URL if specified
            if instance_url and instance_url_actual != instance_url:
                # Send error notification
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification("f'This feature requires access to {instance_url}. Current instance: {instance_url_actual}'", "Error")
                return redirect(url_for('platform.management'))
            
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

# Register all blueprints
from app.core.blueprints import register_blueprints
register_blueprints(app)

# Register admin blueprint
from app.services.admin import create_admin_blueprint
admin_bp = create_admin_blueprint(app)
app.register_blueprint(admin_bp)

# Register debug routes (for development only)
from debug_routes import register_debug_routes
register_debug_routes(app)

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

# Logout route handled by user_management blueprint

# Legacy routes - now handled by admin blueprint
# These routes are kept for backward compatibility but should use /admin/ URLs

# Main dashboard route moved to main blueprint

# Admin cleanup routes are handled by the admin blueprint at /admin/cleanup

# Admin cleanup routes are handled by the admin blueprint

# Platform Management Routes moved to platform blueprint
        
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

# Removed duplicate route - handled by admin blueprint

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
# Caption Generation Routes moved to caption blueprint
# Caption Review Integration Routes# Review routes moved to review blueprint

# Administrative routes are handled by the admin blueprint at /admin/

# Admin API routes are handled by the admin blueprint

# Profile Management Routes
# NOTE: Profile management routes have been moved to routes/user_management_routes.py
# The new user management system provides comprehensive profile management with GDPR compliance

# Favicon and static asset routes
# Register user management routes
from routes.user_management_routes import register_user_management_routes
register_user_management_routes(app)

# Register GDPR routes
from routes.gdpr_routes import gdpr_bp
app.register_blueprint(gdpr_bp)

# Register WebSocket client configuration routes
from routes.websocket_client_config_routes import websocket_client_config_bp
app.register_blueprint(websocket_client_config_bp)

# WebSocket configuration API endpoint with explicit CORS handling
# Page Notification API endpoints
# WebSocket test routes (development only)
# WebSocket endpoints are handled by the WebSocketProgressHandler class
# No HTTP endpoint needed for WebSocket communication

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
