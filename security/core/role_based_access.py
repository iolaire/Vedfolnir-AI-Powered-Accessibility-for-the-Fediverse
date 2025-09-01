# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MIGRATION NOTE: Flash messages in this file have been commented out as part of
# the notification system migration. The application now uses the unified
# WebSocket-based notification system. These comments should be replaced with
# appropriate unified notification calls in a future update.


from unified_notification_manager import UnifiedNotificationManager
"""
Role-Based Access Control System

This module provides comprehensive role-based access control decorators and utilities
for the user management system. It implements viewer user permissions and admin role
enhancements as specified in the requirements.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 1.2, 1.3, 1.4, 1.5
"""

import logging
from functools import wraps
from flask import current_app, redirect, url_for, request, abort, jsonify
from flask_login import current_user
from models import UserRole, PlatformConnection, Image, Post
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def require_role(required_role):
    """
    Decorator to require a specific user role or higher.
    
    Args:
        required_role (UserRole): The minimum required role
        
    Requirements: 1.2, 1.3, 1.4, 1.5
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                # Send info notification
                from notification_helpers import send_info_notification
                send_info_notification("Please log in to access this page.", "Information")
                return redirect(url_for('user_management.login', next=request.url))
            
            if not current_user.has_permission(required_role):
                logger.warning(f"Access denied for user {current_user.id} to {f.__name__}. Required: {required_role.value}, User: {current_user.role.value}")
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification("Access denied. Insufficient permissions.", "Error")
                
                # Log security event
                from models import UserAuditLog
                try:
                    session_manager = current_app.request_session_manager
                    with session_manager.session_scope() as db_session:
                        UserAuditLog.log_action(
                            db_session,
                            action='ACCESS_DENIED',
                            user_id=current_user.id,
                            details=f"Attempted to access {f.__name__} requiring {required_role.value}",
                            ip_address=request.remote_addr,
                            user_agent=request.headers.get('User-Agent')
                        )
                        db_session.commit()
                except Exception as e:
                    logger.error(f"Failed to log access denied event: {e}")
                
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin(f):
    """
    Decorator to require admin role.
    
    Requirements: 1.2, 1.3, 1.4, 1.5
    """
    return require_role(UserRole.ADMIN)(f)

def require_viewer_or_higher(f):
    """
    Decorator to require viewer role or higher.
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    return require_role(UserRole.VIEWER)(f)

def platform_access_required(f):
    """
    Decorator to ensure user has access to the requested platform.
    For viewer users, restricts access to only their own platforms.
    For admin users, allows access to all platforms.
    
    Requirements: 8.2, 8.3
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Send info notification
            from notification_helpers import send_info_notification
            send_info_notification("Please log in to access this page.", "Information")
            return redirect(url_for('user_management.login', next=request.url))
        
        # Admin users have access to all platforms
        if current_user.role == UserRole.ADMIN:
            return f(*args, **kwargs)
        
        # For viewer users, check platform ownership
        platform_id = kwargs.get('platform_id') or request.args.get('platform_id')
        if platform_id:
            try:
                session_manager = current_app.request_session_manager
                with session_manager.session_scope() as db_session:
                    platform = db_session.query(PlatformConnection).filter_by(
                        id=platform_id,
                        user_id=current_user.id,
                        is_active=True
                    ).first()
                    
                    if not platform:
                        logger.warning(f"User {current_user.id} attempted to access platform {platform_id} without permission")
                        # Send error notification
                        from notification_helpers import send_error_notification
                        send_error_notification("Access denied. You can only access your own platforms.", "Error")
                        return redirect(url_for('platform_management'))
                        
            except Exception as e:
                logger.error(f"Error checking platform access: {e}")
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification("Error checking platform access.", "Error")
                return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def content_access_required(f):
    """
    Decorator to ensure user has access to the requested content (images/posts).
    For viewer users, restricts access to only content from their platforms.
    For admin users, allows access to all content.
    
    Requirements: 8.4, 8.5
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Send info notification
            from notification_helpers import send_info_notification
            send_info_notification("Please log in to access this page.", "Information")
            return redirect(url_for('user_management.login', next=request.url))
        
        # Admin users have access to all content
        if current_user.role == UserRole.ADMIN:
            return f(*args, **kwargs)
        
        # For viewer users, check content ownership
        image_id = kwargs.get('image_id') or request.args.get('image_id')
        post_id = kwargs.get('post_id') or request.args.get('post_id')
        
        try:
            session_manager = current_app.request_session_manager
            with session_manager.session_scope() as db_session:
                # Check image access
                if image_id:
                    image = db_session.query(Image).filter_by(id=image_id).first()
                    if image and image.platform_connection_id:
                        platform = db_session.query(PlatformConnection).filter_by(
                            id=image.platform_connection_id,
                            user_id=current_user.id,
                            is_active=True
                        ).first()
                        
                        if not platform:
                            logger.warning(f"User {current_user.id} attempted to access image {image_id} without permission")
                            # Send error notification
                            from notification_helpers import send_error_notification
                            send_error_notification("Access denied. You can only access content from your own platforms.", "Error")
                            return redirect(url_for('review_list'))
                
                # Check post access
                if post_id:
                    post = db_session.query(Post).filter_by(id=post_id).first()
                    if post and post.platform_connection_id:
                        platform = db_session.query(PlatformConnection).filter_by(
                            id=post.platform_connection_id,
                            user_id=current_user.id,
                            is_active=True
                        ).first()
                        
                        if not platform:
                            logger.warning(f"User {current_user.id} attempted to access post {post_id} without permission")
                            # Send error notification
                            from notification_helpers import send_error_notification
                            send_error_notification("Access denied. You can only access content from your own platforms.", "Error")
                            return redirect(url_for('index'))
                            
        except Exception as e:
            logger.error(f"Error checking content access: {e}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Error checking content access.", "Error")
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def filter_user_platforms(user_id=None):
    """
    Filter platforms based on user role and permissions.
    
    Args:
        user_id (int, optional): User ID to filter platforms for. If None, uses current_user.
        
    Returns:
        list: List of platform connections the user can access
        
    Requirements: 8.2, 8.3
    """
    if not current_user.is_authenticated:
        return []
    
    target_user_id = user_id or current_user.id
    
    try:
        # Try unified session manager first
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if unified_session_manager:
            with unified_session_manager.get_db_session() as db_session:
                # Admin users can access all platforms if user_id is specified
                if current_user.role == UserRole.ADMIN and user_id:
                    platforms = db_session.query(PlatformConnection).filter_by(
                        user_id=target_user_id,
                        is_active=True
                    ).all()
                else:
                    # Viewer users can only access their own platforms
                    platforms = db_session.query(PlatformConnection).filter_by(
                        user_id=current_user.id,
                        is_active=True
                    ).all()
                
                return platforms
        else:
            # Fallback to request session manager
            session_manager = current_app.request_session_manager
            with session_manager.session_scope() as db_session:
                # Admin users can access all platforms if user_id is specified
                if current_user.role == UserRole.ADMIN and user_id:
                    platforms = db_session.query(PlatformConnection).filter_by(
                        user_id=target_user_id,
                        is_active=True
                    ).all()
                else:
                    # Viewer users can only access their own platforms
                    platforms = db_session.query(PlatformConnection).filter_by(
                        user_id=current_user.id,
                        is_active=True
                    ).all()
                
                return platforms
            
    except Exception as e:
        logger.error(f"Error filtering user platforms: {e}")
        return []

def filter_user_content(content_type='images', platform_id=None):
    """
    Filter content (images/posts) based on user role and permissions.
    
    Args:
        content_type (str): Type of content to filter ('images' or 'posts')
        platform_id (int, optional): Specific platform to filter by
        
    Returns:
        query: SQLAlchemy query object filtered by user permissions
        
    Requirements: 8.4, 8.5
    """
    if not current_user.is_authenticated:
        return None
    
    try:
        session_manager = current_app.request_session_manager
        with session_manager.session_scope() as db_session:
            if content_type == 'images':
                query = db_session.query(Image)
            elif content_type == 'posts':
                query = db_session.query(Post)
            else:
                raise ValueError(f"Invalid content_type: {content_type}")
            
            # Admin users can access all content
            if current_user.role == UserRole.ADMIN:
                if platform_id:
                    query = query.filter_by(platform_connection_id=platform_id)
                return query
            
            # Viewer users can only access content from their platforms
            user_platform_ids = [p.id for p in filter_user_platforms()]
            if not user_platform_ids:
                # User has no platforms, return empty query
                return query.filter(False)
            
            query = query.filter(
                getattr(query.column_descriptions[0]['type'], 'platform_connection_id').in_(user_platform_ids)
            )
            
            if platform_id and platform_id in user_platform_ids:
                query = query.filter_by(platform_connection_id=platform_id)
            
            return query
            
    except Exception as e:
        logger.error(f"Error filtering user content: {e}")
        return None

def get_accessible_platform_ids():
    """
    Get list of platform IDs that the current user can access.
    
    Returns:
        list: List of platform IDs
        
    Requirements: 8.2, 8.3
    """
    if not current_user.is_authenticated:
        return []
    
    # Admin users can access all platforms
    if current_user.role == UserRole.ADMIN:
        try:
            # Try unified session manager first
            unified_session_manager = getattr(current_app, 'unified_session_manager', None)
            if unified_session_manager:
                with unified_session_manager.get_db_session() as db_session:
                    platforms = db_session.query(PlatformConnection).filter_by(is_active=True).all()
                    return [p.id for p in platforms]
            else:
                # Fallback to request session manager
                session_manager = current_app.request_session_manager
                with session_manager.session_scope() as db_session:
                    platforms = db_session.query(PlatformConnection).filter_by(is_active=True).all()
                    return [p.id for p in platforms]
        except Exception as e:
            logger.error(f"Error getting all platform IDs for admin: {e}")
            return []
    
    # Viewer users can only access their own platforms
    platforms = filter_user_platforms()
    return [p.id for p in platforms]

def check_platform_ownership(platform_id):
    """
    Check if the current user owns or has access to a specific platform.
    
    Args:
        platform_id (int): Platform ID to check
        
    Returns:
        bool: True if user has access, False otherwise
        
    Requirements: 8.2, 8.3
    """
    if not current_user.is_authenticated:
        return False
    
    # Admin users have access to all platforms
    if current_user.role == UserRole.ADMIN:
        return True
    
    # Check if platform belongs to current user
    accessible_platform_ids = get_accessible_platform_ids()
    return platform_id in accessible_platform_ids

def check_content_ownership(content_id, content_type='image'):
    """
    Check if the current user owns or has access to specific content.
    
    Args:
        content_id (int): Content ID to check
        content_type (str): Type of content ('image' or 'post')
        
    Returns:
        bool: True if user has access, False otherwise
        
    Requirements: 8.4, 8.5
    """
    if not current_user.is_authenticated:
        return False
    
    # Admin users have access to all content
    if current_user.role == UserRole.ADMIN:
        return True
    
    try:
        session_manager = current_app.request_session_manager
        with session_manager.session_scope() as db_session:
            if content_type == 'image':
                content = db_session.query(Image).filter_by(id=content_id).first()
            elif content_type == 'post':
                content = db_session.query(Post).filter_by(id=content_id).first()
            else:
                return False
            
            if not content or not content.platform_connection_id:
                return False
            
            return check_platform_ownership(content.platform_connection_id)
            
    except Exception as e:
        logger.error(f"Error checking content ownership: {e}")
        return False

def api_require_role(required_role):
    """
    API version of role requirement decorator that returns JSON responses.
    
    Args:
        required_role (UserRole): The minimum required role
        
    Requirements: 1.2, 1.3, 1.4, 1.5
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            if not current_user.has_permission(required_role):
                logger.warning(f"API access denied for user {current_user.id} to {f.__name__}. Required: {required_role.value}, User: {current_user.role.value}")
                
                # Log security event
                from models import UserAuditLog
                try:
                    session_manager = current_app.request_session_manager
                    with session_manager.session_scope() as db_session:
                        UserAuditLog.log_action(
                            db_session,
                            action='API_ACCESS_DENIED',
                            user_id=current_user.id,
                            details=f"Attempted to access API {f.__name__} requiring {required_role.value}",
                            ip_address=request.remote_addr,
                            user_agent=request.headers.get('User-Agent')
                        )
                        db_session.commit()
                except Exception as e:
                    logger.error(f"Failed to log API access denied event: {e}")
                
                return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_require_admin(f):
    """
    API version of admin requirement decorator.
    
    Requirements: 1.2, 1.3, 1.4, 1.5
    """
    return api_require_role(UserRole.ADMIN)(f)

def api_platform_access_required(f):
    """
    API version of platform access requirement decorator.
    
    Requirements: 8.2, 8.3
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Admin users have access to all platforms
        if current_user.role == UserRole.ADMIN:
            return f(*args, **kwargs)
        
        # For viewer users, check platform ownership
        platform_id = kwargs.get('platform_id') or request.json.get('platform_id') if request.json else None
        if platform_id and not check_platform_ownership(platform_id):
            logger.warning(f"User {current_user.id} attempted API access to platform {platform_id} without permission")
            return jsonify({'success': False, 'error': 'Access denied. You can only access your own platforms.'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def api_content_access_required(f):
    """
    API version of content access requirement decorator.
    
    Requirements: 8.4, 8.5
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Admin users have access to all content
        if current_user.role == UserRole.ADMIN:
            return f(*args, **kwargs)
        
        # For viewer users, check content ownership
        image_id = kwargs.get('image_id') or (request.json.get('image_id') if request.json else None)
        post_id = kwargs.get('post_id') or (request.json.get('post_id') if request.json else None)
        
        if image_id and not check_content_ownership(image_id, 'image'):
            logger.warning(f"User {current_user.id} attempted API access to image {image_id} without permission")
            return jsonify({'success': False, 'error': 'Access denied. You can only access content from your own platforms.'}), 403
        
        if post_id and not check_content_ownership(post_id, 'post'):
            logger.warning(f"User {current_user.id} attempted API access to post {post_id} without permission")
            return jsonify({'success': False, 'error': 'Access denied. You can only access content from your own platforms.'}), 403
        
        return f(*args, **kwargs)
    return decorated_function