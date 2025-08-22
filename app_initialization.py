#!/usr/bin/env python3

"""
Web Application Initialization with Session Management

This module provides comprehensive initialization of the Flask web application
with proper session management integration to prevent DetachedInstanceError.
"""

import logging
from flask import Flask
from flask_login import LoginManager
from request_scoped_session_manager import RequestScopedSessionManager
from database_context_middleware import DatabaseContextMiddleware
from session_aware_user import SessionAwareUser
from detached_instance_handler import create_global_detached_instance_handler
from safe_template_context import create_safe_template_context_processor
from database import DatabaseManager
from models import User

logger = logging.getLogger(__name__)

class SessionManagedFlaskApp:
    """
    Flask application factory with integrated session management.
    
    This class provides a complete Flask application setup with:
    - Request-scoped session management
    - Database context middleware
    - Session-aware user loading
    - DetachedInstanceError recovery
    - Safe template context processing
    """
    
    def __init__(self, config):
        """
        Initialize the session-managed Flask application.
        
        Args:
            config: Application configuration object
        """
        self.config = config
        self.app = None
        self.db_manager = None
        self.request_session_manager = None
        self.database_context_middleware = None
        self.login_manager = None
        self.detached_instance_handler = None
        
        logger.info("SessionManagedFlaskApp initialized")
    
    def create_app(self) -> Flask:
        """
        Create and configure the Flask application with session management.
        
        Returns:
            Configured Flask application instance
        """
        # Create Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = self.config.webapp.secret_key
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.config)
        
        # Initialize session management components
        self._initialize_session_management()
        
        # Initialize Flask-Login with session-aware user loader
        self._initialize_flask_login()
        
        # Initialize error handling
        self._initialize_error_handling()
        
        # Initialize template context processing
        self._initialize_template_context()
        
        # Store components in app for access by routes
        self._register_components()
        
        logger.info("Flask application created with session management")
        return self.app
    
    def _initialize_session_management(self):
        """Initialize request-scoped session management components."""
        # Create request-scoped session manager
        self.request_session_manager = RequestScopedSessionManager(self.db_manager)
        
        # Create database context middleware
        self.database_context_middleware = DatabaseContextMiddleware(
            self.app, 
            self.request_session_manager
        )
        
        logger.info("Session management components initialized")
    
    def _initialize_flask_login(self):
        """Initialize Flask-Login with session-aware user loader."""
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'login'
        self.login_manager.login_message = 'Please log in to access this page.'
        self.login_manager.login_message_category = 'info'
        
        # Configure session-aware user loader
        @self.login_manager.user_loader
        def load_user(user_id):
            """
            Load user with proper session attachment to prevent DetachedInstanceError.
            
            Args:
                user_id: User ID to load
                
            Returns:
                SessionAwareUser instance or None
            """
            if not user_id:
                logger.warning("load_user called with empty user_id")
                return None
            
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid user_id format: {user_id}")
                return None
            
            logger.debug(f"Loading user with ID: {user_id_int}")
            
            try:
                # Use request-scoped session to prevent DetachedInstanceError
                with self.request_session_manager.session_scope() as session:
                    # Load user with explicit relationship loading
                    from sqlalchemy.orm import joinedload
                    user = session.query(User).options(
                        joinedload(User.platform_connections),
                        joinedload(User.sessions)
                    ).filter(
                        User.id == user_id_int,
                        User.is_active == True
                    ).first()
                    
                    if user:
                        logger.debug(f"User loaded successfully: {user.username} (ID: {user.id})")
                        # Return SessionAwareUser to maintain session attachment
                        return SessionAwareUser(user, self.request_session_manager)
                    else:
                        logger.info(f"User not found or inactive for ID: {user_id_int}")
                        return None
                        
            except Exception as e:
                logger.error(f"Error loading user {user_id_int}: {e}")
                return None
        
        logger.info("Flask-Login initialized with session-aware user loader")
    
    def _initialize_error_handling(self):
        """Initialize DetachedInstanceError recovery and global error handling."""
        # Create global DetachedInstanceError handler
        self.detached_instance_handler = create_global_detached_instance_handler(
            self.app, 
            self.request_session_manager
        )
        
        logger.info("Error handling initialized")
    
    def _initialize_template_context(self):
        """Initialize safe template context processing."""
        # Register safe template context processor
        create_safe_template_context_processor(self.app)
        
        logger.info("Template context processing initialized")
    
    def _register_components(self):
        """Register session management components with the Flask app."""
        # Store components in app for access by routes and other components
        self.app.request_session_manager = self.request_session_manager
        self.app.database_context_middleware = self.database_context_middleware
        self.app.detached_instance_handler = self.detached_instance_handler
        self.app.db_manager = self.db_manager
        self.app.login_manager = self.login_manager
        
        logger.info("Session management components registered with Flask app")
    
    def get_initialization_status(self) -> dict:
        """
        Get status of initialization components.
        
        Returns:
            Dictionary containing initialization status
        """
        return {
            'app_created': self.app is not None,
            'db_manager_initialized': self.db_manager is not None,
            'request_session_manager_initialized': self.request_session_manager is not None,
            'database_context_middleware_initialized': self.database_context_middleware is not None,
            'login_manager_initialized': self.login_manager is not None,
            'detached_instance_handler_initialized': self.detached_instance_handler is not None,
            'components_registered': hasattr(self.app, 'request_session_manager') if self.app else False
        }

def create_session_managed_app(config) -> Flask:
    """
    Factory function to create a Flask app with session management.
    
    Args:
        config: Application configuration object
        
    Returns:
        Configured Flask application instance
    """
    app_factory = SessionManagedFlaskApp(config)
    return app_factory.create_app()

def validate_session_management_setup(app: Flask) -> dict:
    """
    Validate that session management is properly set up in the Flask app.
    
    Args:
        app: Flask application instance to validate
        
    Returns:
        Dictionary containing validation results
    """
    validation_results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'components_found': {}
    }
    
    # Check for required components
    required_components = [
        'request_session_manager',
        'database_context_middleware', 
        'detached_instance_handler',
        'db_manager'
    ]
    
    for component in required_components:
        if hasattr(app, component):
            validation_results['components_found'][component] = True
        else:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Missing required component: {component}")
            validation_results['components_found'][component] = False
    
    # Check Flask-Login setup
    if hasattr(app, 'login_manager'):
        validation_results['components_found']['login_manager'] = True
        
        # Check if user loader is configured
        if app.login_manager.user_loader:
            validation_results['components_found']['user_loader'] = True
        else:
            validation_results['valid'] = False
            validation_results['errors'].append("Flask-Login user loader not configured")
            validation_results['components_found']['user_loader'] = False
    else:
        validation_results['valid'] = False
        validation_results['errors'].append("Flask-Login not initialized")
        validation_results['components_found']['login_manager'] = False
    
    # Check for template context processor
    context_processors = app.template_context_processors.get(None, [])
    has_safe_context_processor = any(
        'safe_template_context' in str(processor) or 'inject_safe_context' in str(processor)
        for processor in context_processors
    )
    
    if has_safe_context_processor:
        validation_results['components_found']['safe_template_context_processor'] = True
    else:
        validation_results['warnings'].append("Safe template context processor may not be registered")
        validation_results['components_found']['safe_template_context_processor'] = False
    
    # Check for error handlers
    has_detached_error_handler = any(
        'DetachedInstanceError' in str(handler) 
        for handler in app.error_handler_spec.get(None, {}).values()
    )
    
    if has_detached_error_handler:
        validation_results['components_found']['detached_instance_error_handler'] = True
    else:
        validation_results['warnings'].append("DetachedInstanceError handler may not be registered")
        validation_results['components_found']['detached_instance_error_handler'] = False
    
    logger.info(f"Session management validation completed: {'PASSED' if validation_results['valid'] else 'FAILED'}")
    
    return validation_results

def get_session_management_info(app: Flask) -> dict:
    """
    Get information about session management setup for monitoring.
    
    Args:
        app: Flask application instance
        
    Returns:
        Dictionary containing session management information
    """
    info = {
        'session_management_active': False,
        'components': {},
        'middleware_status': {},
        'session_manager_status': {}
    }
    
    try:
        # Check if session management is active
        if hasattr(app, 'request_session_manager'):
            info['session_management_active'] = True
            
            # Get session manager status
            session_manager = app.request_session_manager
            info['session_manager_status'] = session_manager.get_session_info()
            
            # Get middleware status
            if hasattr(app, 'database_context_middleware'):
                middleware = app.database_context_middleware
                info['middleware_status'] = middleware.get_middleware_status()
            
            # Get component status
            components = [
                'request_session_manager',
                'database_context_middleware',
                'detached_instance_handler',
                'db_manager'
            ]
            
            for component in components:
                info['components'][component] = {
                    'present': hasattr(app, component),
                    'type': type(getattr(app, component, None)).__name__ if hasattr(app, component) else None
                }
        
    except Exception as e:
        logger.error(f"Error getting session management info: {e}")
        info['error'] = str(e)
    
    return info