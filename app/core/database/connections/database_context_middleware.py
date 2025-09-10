# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
from typing import Optional, Dict, Any
from flask import Flask, g, current_app
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import DetachedInstanceError
from app.core.session.core.session_manager import SessionManager
from models import PlatformConnection, User
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class DatabaseContextMiddleware:
    """
    Middleware to ensure proper database session lifecycle management for Flask requests.
    
    This middleware handles:
    - Initializing request-scoped database sessions
    - Proper session cleanup and rollback on errors
    - Injecting session-aware objects into template context
    - Preventing DetachedInstanceError throughout the request lifecycle
    """
    
    def __init__(self, app: Flask, session_manager: SessionManager):
        """
        Initialize the database context middleware.
        
        Args:
            app: Flask application instance
            session_manager: SessionManager for handling database sessions
        """
        self.app = app
        self.session_manager = session_manager
        logger.info("DatabaseContextMiddleware initialized")
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup Flask request handlers for database session management"""
        
        @self.app.before_request
        def before_request():
            """Initialize database session for request"""
            # Skip database session creation for static files
            from flask import request
            if request.endpoint == 'static':
                return
                
            try:
                # Ensure we have a request-scoped session
                session = self.session_manager.get_request_session()
                logger.debug("Initialized request-scoped database session")
                
                # Store session info in g for debugging
                g.db_session_info = self.session_manager.get_session_info()
                
            except Exception as e:
                logger.error(f"Error initializing request session: {sanitize_for_log(str(e))}")
                # Don't fail the request, but log the error
        
        @self.app.teardown_request
        def teardown_request(exception=None):
            """Clean up database session after request"""
            # Skip database session cleanup for static files
            from flask import request
            if request.endpoint == 'static':
                return
                
            try:
                if exception:
                    logger.warning(f"Request ended with exception: {sanitize_for_log(str(exception))}")
                    # Rollback on exception
                    if hasattr(g, 'db_session'):
                        try:
                            g.db_session.rollback()
                            logger.debug("Rolled back database session due to exception")
                        except Exception as rollback_error:
                            logger.error(f"Error rolling back session: {sanitize_for_log(str(rollback_error))}")
                
                # Always clean up the session
                self.session_manager.close_request_session()
                
            except Exception as e:
                logger.error(f"Error in teardown_request: {sanitize_for_log(str(e))}")
        
        @self.app.context_processor
        def inject_session_aware_objects():
            """Inject session-aware objects into template context"""
            # Skip template context injection for static files
            from flask import request
            if request.endpoint == 'static':
                return {}
            return self._create_safe_template_context()
    
    def _create_safe_template_context(self) -> Dict[str, Any]:
        """
        Create safe template context with error handling for database objects.
        
        Returns:
            Dictionary containing safe template context variables
        """
        context = {
            'current_user_safe': None,
            'user_platforms': [],
            'active_platform': None,
            'platform_count': 0,
            'template_error': False,
            'session_context': None
        }
        
        if not current_user.is_authenticated:
            return context
        
        try:
            # Safely access current user properties
            context['current_user_safe'] = self._get_safe_user_dict(current_user)
            
            # Safely get user platforms
            platforms_result = self._get_safe_user_platforms(current_user)
            context.update(platforms_result)
            
            # Get session context for debugging
            context['session_context'] = self._get_session_context_info()
            
        except Exception as e:
            logger.error(f"Error creating template context: {sanitize_for_log(str(e))}")
            context['template_error'] = True
        
        return context
    
    def _get_safe_user_dict(self, user) -> Optional[Dict[str, Any]]:
        """
        Safely extract user information into a dictionary.
        
        Args:
            user: Current user object
            
        Returns:
            Dictionary with safe user information or None if error
        """
        try:
            # Try to access attributes directly first
            user_dict = {}
            try:
                user_dict['id'] = user.id
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                user_dict['id'] = getattr(user, '_user_id', None) if hasattr(user, '_user_id') else None
            
            try:
                user_dict['username'] = user.username
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                user_dict['username'] = 'Unknown'
            
            try:
                user_dict['email'] = user.email
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                user_dict['email'] = 'Unknown'
            
            try:
                user_dict['role'] = user.role
                # Ensure we have the role value for template comparison
                if hasattr(user_dict['role'], 'value'):
                    user_dict['role_value'] = user_dict['role'].value
                else:
                    user_dict['role_value'] = str(user_dict['role']) if user_dict['role'] else None
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                user_dict['role'] = None
                user_dict['role_value'] = None
            
            try:
                user_dict['is_active'] = user.is_active
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                user_dict['is_active'] = True
            
            try:
                user_dict['last_login'] = user.last_login
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                user_dict['last_login'] = None
            
            return user_dict
            
        except Exception as e:
            logger.warning(f"Error accessing user properties: {sanitize_for_log(str(e))}")
            return {
                'id': getattr(user, '_user_id', None) if hasattr(user, '_user_id') else None,
                'username': 'Unknown',
                'email': 'Unknown',
                'role': None,
                'role_value': None,
                'is_active': True,
                'last_login': None
            }
        except Exception as e:
            logger.error(f"Unexpected error accessing user properties: {sanitize_for_log(str(e))}")
            return None
    
    def _get_safe_user_platforms(self, user) -> Dict[str, Any]:
        """
        Safely get user platforms with error handling and recovery.
        
        Args:
            user: Current user object
            
        Returns:
            Dictionary containing platform information
        """
        result = {
            'user_platforms': [],
            'active_platform': None,
            'platform_count': 0
        }
        
        try:
            # Always load from database to ensure fresh data
            user_id = getattr(user, 'id', None) or getattr(user, '_user_id', None)
            if user_id:
                result.update(self._load_platforms_from_database(user_id))
                return result
            
            # Fallback: Try to get platforms from SessionAwareUser
            if hasattr(user, 'platforms'):
                platforms = user.platforms
                result['user_platforms'] = [self._platform_to_dict(p) for p in platforms if p]
                result['platform_count'] = len(result['user_platforms'])
                
                # Get active platform - check session context first
                active_platform_id = None
                try:
                    from redis_session_backend import get_platform_id
                    active_platform_id = get_platform_id()
                except Exception:
                    pass
                
                # If we have an active platform ID from session, use that
                if active_platform_id:
                    for platform_dict in result['user_platforms']:
                        if platform_dict.get('id') == active_platform_id:
                            result['active_platform'] = platform_dict
                            break
                
                # Fallback to SessionAwareUser method
                if not result['active_platform'] and hasattr(user, 'get_active_platform'):
                    active_platform = user.get_active_platform()
                    if active_platform:
                        result['active_platform'] = self._platform_to_dict(active_platform)
                
                # Fallback: find default platform
                if not result['active_platform']:
                    for platform_dict in result['user_platforms']:
                        if platform_dict.get('is_default'):
                            result['active_platform'] = platform_dict
                            break
                    
                    # If no default, use first platform
                    if not result['active_platform'] and result['user_platforms']:
                        result['active_platform'] = result['user_platforms'][0]
                
                return result
                
        except (DetachedInstanceError, SQLAlchemyError) as e:
            logger.warning(f"DetachedInstanceError accessing platforms, attempting database recovery: {sanitize_for_log(str(e))}")
            # Recovery: Load platforms directly from database
            try:
                user_id = getattr(user, 'id', None) or getattr(user, '_user_id', None)
                if user_id:
                    result.update(self._load_platforms_from_database(user_id))
            except Exception as recovery_error:
                logger.error(f"Failed to recover platforms from database: {sanitize_for_log(str(recovery_error))}")
        except Exception as e:
            logger.error(f"Unexpected error accessing platforms: {sanitize_for_log(str(e))}")
            # Recovery: Load platforms directly from database
            try:
                user_id = getattr(user, 'id', None) or getattr(user, '_user_id', None)
                if user_id:
                    result.update(self._load_platforms_from_database(user_id))
            except Exception as recovery_error:
                logger.error(f"Failed to recover platforms from database: {sanitize_for_log(str(recovery_error))}")
        
        return result
    
    def _load_platforms_from_database(self, user_id: int) -> Dict[str, Any]:
        """
        Load user platforms directly from database as recovery mechanism.
        
        Args:
            user_id: User ID to load platforms for
            
        Returns:
            Dictionary containing platform information
        """
        result = {
            'user_platforms': [],
            'active_platform': None,
            'platform_count': 0
        }
        
        try:
            session = self.session_manager.get_request_session()
            platforms = session.query(PlatformConnection).filter_by(
                user_id=user_id,
                is_active=True
            ).order_by(PlatformConnection.is_default.desc(), PlatformConnection.name).all()
            
            result['user_platforms'] = [self._platform_to_dict(p) for p in platforms]
            result['platform_count'] = len(platforms)
            
            # Find active platform - check session context first
            active_platform_id = None
            try:
                from redis_session_backend import get_platform_id
                active_platform_id = get_platform_id()
            except Exception:
                pass
            
            # If we have an active platform ID from session, use that
            if active_platform_id:
                for platform in platforms:
                    if platform.id == active_platform_id:
                        result['active_platform'] = self._platform_to_dict(platform)
                        break
            
            # Fallback to default platform
            if not result['active_platform']:
                for platform in platforms:
                    if platform.is_default:
                        result['active_platform'] = self._platform_to_dict(platform)
                        break
            
            # If no default, use first platform
            if not result['active_platform'] and platforms:
                result['active_platform'] = self._platform_to_dict(platforms[0])
            
            logger.debug(f"Recovered {len(platforms)} platforms from database for user {user_id}, active: {result['active_platform']['name'] if result['active_platform'] else 'None'}")
            
        except Exception as e:
            logger.error(f"Error loading platforms from database: {sanitize_for_log(str(e))}")
        
        return result
    
    def _platform_to_dict(self, platform: PlatformConnection) -> Dict[str, Any]:
        """
        Convert PlatformConnection to safe dictionary representation.
        
        Args:
            platform: PlatformConnection object
            
        Returns:
            Dictionary representation of platform
        """
        try:
            # Try to access attributes directly first
            platform_dict = {}
            
            try:
                platform_dict['id'] = platform.id
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                platform_dict['id'] = None
            
            try:
                platform_dict['name'] = platform.name
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                platform_dict['name'] = 'Unknown'
            
            try:
                platform_dict['platform_type'] = platform.platform_type
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                platform_dict['platform_type'] = 'unknown'
            
            try:
                platform_dict['instance_url'] = platform.instance_url
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                platform_dict['instance_url'] = ''
            
            try:
                platform_dict['username'] = platform.username
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                platform_dict['username'] = ''
            
            try:
                platform_dict['is_default'] = platform.is_default
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                platform_dict['is_default'] = False
            
            try:
                platform_dict['is_active'] = platform.is_active
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                platform_dict['is_active'] = True
            
            try:
                platform_dict['created_at'] = platform.created_at
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                platform_dict['created_at'] = None
            
            try:
                platform_dict['last_used'] = platform.last_used
            except (DetachedInstanceError, SQLAlchemyError, AttributeError):
                platform_dict['last_used'] = None
            
            return platform_dict
            
        except Exception as e:
            logger.warning(f"Error converting platform to dict: {sanitize_for_log(str(e))}")
            # Return minimal safe representation
            return {
                'id': None,
                'name': 'Unknown',
                'platform_type': 'unknown',
                'instance_url': '',
                'username': '',
                'is_default': False,
                'is_active': True,
                'created_at': None,
                'last_used': None
            }
        except Exception as e:
            logger.error(f"Unexpected error converting platform to dict: {sanitize_for_log(str(e))}")
            return {
                'id': None,
                'name': 'Error',
                'platform_type': 'unknown',
                'instance_url': '',
                'username': '',
                'is_default': False,
                'is_active': False,
                'created_at': None,
                'last_used': None
            }
    
    def _get_session_context_info(self) -> Optional[Dict[str, Any]]:
        """
        Get session context information for debugging.
        
        Returns:
            Dictionary with session context information or None
        """
        try:
            context_info = {
                'session_id': getattr(g, 'session_id', None),
                'has_db_session': hasattr(g, 'db_session'),
                'db_session_active': False,
                'user_authenticated': current_user.is_authenticated
            }
            
            if hasattr(g, 'db_session'):
                context_info['db_session_active'] = g.db_session.is_active
            
            # Add session manager info
            context_info.update(self.session_manager.get_session_info())
            
            return context_info
            
        except Exception as e:
            logger.error(f"Error getting session context info: {sanitize_for_log(str(e))}")
            return None
    
    def handle_detached_instance_error(self, error: DetachedInstanceError, context: str = "unknown"):
        """
        Handle DetachedInstanceError by logging and attempting recovery.
        
        Args:
            error: The DetachedInstanceError that occurred
            context: Context where the error occurred for logging
        """
        logger.warning(f"DetachedInstanceError in {context}: {sanitize_for_log(str(error))}")
        
        # Log session state for debugging
        session_info = self.session_manager.get_session_info()
        logger.debug(f"Session state during DetachedInstanceError: {session_info}")
        
        # If we have a current user, try to refresh their session attachment
        if current_user.is_authenticated and hasattr(current_user, 'refresh_platforms'):
            try:
                current_user.refresh_platforms()
                logger.debug("Refreshed current_user platforms after DetachedInstanceError")
            except Exception as refresh_error:
                logger.error(f"Failed to refresh user platforms: {sanitize_for_log(str(refresh_error))}")
    
    def get_middleware_status(self) -> Dict[str, Any]:
        """
        Get status information about the middleware for monitoring.
        
        Returns:
            Dictionary containing middleware status information
        """
        return {
            'middleware_active': True,
            'session_manager_active': self.session_manager.is_session_active(),
            'session_info': self.session_manager.get_session_info(),
            'app_name': self.app.name,
            'handlers_registered': True
        }