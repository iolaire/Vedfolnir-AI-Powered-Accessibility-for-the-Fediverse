# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
from functools import wraps
from datetime import datetime, timezone
from flask import current_app, redirect, url_for, flash, request
from flask_login import current_user
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def with_db_session(f):
    """
    Decorator to ensure view functions have proper database session and current_user attachment.
    
    This decorator:
    - Ensures a request-scoped database session exists
    - Reattaches current_user object if it becomes detached
    - Handles DetachedInstanceError gracefully
    
    Requirements: 1.1, 1.2, 6.1, 6.2
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get the request-scoped session manager
            if not hasattr(current_app, 'request_session_manager'):
                logger.error("RequestScopedSessionManager not found in current_app")
                flash('Database configuration error. Please contact support.', 'error')
                return redirect(url_for('login'))
            
            session_manager = current_app.request_session_manager
            
            # Ensure we have a request session
            session = session_manager.get_request_session()
            
            # If current_user is authenticated, ensure proper session attachment
            if current_user.is_authenticated:
                try:
                    # Check if current_user is a SessionAwareUser and needs reattachment
                    if hasattr(current_user, '_user_id') and hasattr(current_user, '_session_manager'):
                        # This is a SessionAwareUser - ensure it's using the current session
                        if hasattr(current_user, '_user') and hasattr(session, '__contains__') and current_user._user not in session:
                            # Reattach user object to current session
                            current_user._user = session_manager.ensure_session_attachment(current_user._user)
                            # Invalidate cached platforms to force reload
                            if hasattr(current_user, '_invalidate_cache'):
                                current_user._invalidate_cache()
                            logger.debug(f"Reattached current_user {current_user._user_id} to request session")
                    
                    # Test access to user properties to ensure attachment is working
                    _ = getattr(current_user, 'id', None)
                    
                except DetachedInstanceError as e:
                    logger.warning(f"DetachedInstanceError for current_user in {f.__name__}: {e}")
                    flash('Your session has expired. Please log in again.', 'warning')
                    return redirect(url_for('login'))
                except Exception as e:
                    logger.error(f"Error ensuring current_user attachment in {f.__name__}: {e}")
                    flash('Authentication error. Please log in again.', 'error')
                    return redirect(url_for('login'))
            
            # Call the original function
            return f(*args, **kwargs)
            
        except DetachedInstanceError as e:
            logger.error(f"DetachedInstanceError in view {f.__name__}: {e}")
            flash('Database session error. Please try again.', 'error')
            return redirect(url_for('index'))
        except SQLAlchemyError as e:
            logger.error(f"Database error in view {f.__name__}: {e}")
            flash('Database error occurred. Please try again.', 'error')
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Unexpected error in view {f.__name__}: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('index'))
    
    return decorated_function


def require_platform_context(f):
    """
    Decorator to ensure platform context is available for platform-dependent views.
    
    This decorator:
    - Ensures user is authenticated
    - Verifies user has at least one active platform
    - Ensures current platform context is available
    - Handles missing platform context gracefully
    
    Requirements: 3.1, 3.2
    """
    @wraps(f)
    @with_db_session  # Ensure database session is available first
    def decorated_function(*args, **kwargs):
        try:
            # Check authentication
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'info')
                return redirect(url_for('login', next=request.url))
            
            # Use direct database query instead of current_user.platforms to avoid session issues
            from flask import current_app
            from models import PlatformConnection
            
            try:
                # Get request-scoped session manager
                session_manager = current_app.request_session_manager
                with session_manager.session_scope() as db_session:
                    # Check if user has any platforms
                    user_id = getattr(current_user, 'id', None)
                    if not user_id:
                        flash('User authentication error. Please log in again.', 'error')
                        return redirect(url_for('user_management.login'))
                    
                    user_platforms = db_session.query(PlatformConnection).filter_by(
                        user_id=user_id,
                        is_active=True
                    ).all()
                    
                    if not user_platforms:
                        flash('You need to set up at least one platform connection to access this feature.', 'warning')
                        return redirect(url_for('first_time_setup'))
                    
                    # Check for active platform context
                    from database_session_middleware import get_current_session_context
                    context = get_current_session_context()
                    
                    if not context or not context.get('platform_connection_id'):
                        # No platform context, try to set default platform
                        default_platform = None
                        for platform in user_platforms:
                            if platform.is_default:
                                default_platform = platform
                                break
                        
                        if not default_platform:
                            default_platform = user_platforms[0]  # Use first platform as fallback
                        
                        # Try to set platform context using database session
                        from database_session_middleware import update_session_platform
                        success = update_session_platform(default_platform.id)
                        
                        if success:
                            logger.info(f"Set platform context to {default_platform.name} for user {user_id}")
                        else:
                            logger.warning(f"Failed to set platform context to {default_platform.name} for user {user_id}")
                    
            except Exception as e:
                logger.error(f"Error checking platform context in {f.__name__}: {e}")
                flash('Error loading platform information. Please try again.', 'error')
                return redirect(url_for('platform_management'))
            
            # Call the original function
            return f(*args, **kwargs)
            
        except DetachedInstanceError as e:
            logger.error(f"DetachedInstanceError in platform-dependent view {f.__name__}: {e}")
            flash('Database session error. Please log in again.', 'warning')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Unexpected error in platform-dependent view {f.__name__}: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('index'))
    
    return decorated_function


def handle_detached_instance_error(f):
    """
    Decorator to handle DetachedInstanceError specifically.
    
    This decorator provides a fallback mechanism for views that might encounter
    DetachedInstanceError and need graceful recovery.
    
    Requirements: 6.1, 6.2
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except DetachedInstanceError as e:
            logger.warning(f"DetachedInstanceError in {f.__name__}: {e}")
            
            # Attempt to recover by clearing any cached data and redirecting
            try:
                if current_user.is_authenticated and hasattr(current_user, '_invalidate_cache'):
                    current_user._invalidate_cache()
            except Exception as cache_error:
                logger.error(f"Error invalidating user cache: {cache_error}")
            
            # Provide user-friendly error message based on the view
            if f.__name__ in ['index', 'dashboard']:
                flash('Your session has expired. Please refresh the page or log in again.', 'warning')
                return redirect(url_for('login'))
            elif 'platform' in f.__name__.lower():
                flash('Platform session error. Please select your platform again.', 'warning')
                return redirect(url_for('platform_management'))
            else:
                flash('Session error occurred. Please try again.', 'error')
                return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('index'))
    
    return decorated_function


def ensure_user_session_attachment(f):
    """
    Lightweight decorator to ensure current_user session attachment without full platform checks.
    
    This decorator is useful for views that need current_user but don't require platform context.
    
    Requirements: 1.1, 1.2
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            try:
                # Ensure current_user is properly attached
                if hasattr(current_user, '_session_manager') and hasattr(current_app, 'request_session_manager'):
                    session_manager = current_app.request_session_manager
                    session = session_manager.get_request_session()
                    
                    # Check if user object needs reattachment
                    if hasattr(current_user, '_user') and hasattr(session, '__contains__') and current_user._user not in session:
                        current_user._user = session_manager.ensure_session_attachment(current_user._user)
                        if hasattr(current_user, '_invalidate_cache'):
                            current_user._invalidate_cache()
                
                # Test access to ensure attachment is working
                _ = getattr(current_user, 'id', None)
                
            except DetachedInstanceError:
                logger.warning(f"DetachedInstanceError for current_user in {f.__name__}")
                flash('Your session has expired. Please log in again.', 'warning')
                return redirect(url_for('login'))
            except Exception as e:
                logger.error(f"Error ensuring user session attachment in {f.__name__}: {e}")
        
        return f(*args, **kwargs)
    
    return decorated_function