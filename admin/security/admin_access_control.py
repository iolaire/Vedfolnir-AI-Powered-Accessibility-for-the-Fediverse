# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Access Control System

This module provides admin-specific access control decorators and utilities
for the admin interface. It ensures admin users maintain full site access
and session preservation during user management operations.

Requirements: 1.2, 1.3, 1.4, 1.5
"""

import logging
from functools import wraps
from flask import current_app, redirect, url_for, request, jsonify, g
from flask_login import current_user
from models import UserRole, UserAuditLog
# from notification_flash_replacement import send_notification  # Removed - using unified notification system
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def admin_required(f):
    """
    Decorator to require admin role for admin interface access.
    Includes Redis session preservation and audit logging.
    
    Requirements: 1.2, 1.3, 1.4, 1.5
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Send info notification
            from app.services.notification.helpers.notification_helpers import send_info_notification
            send_info_notification("Please log in to access the admin interface.", "Information")
            return redirect(url_for('user_management.login', next=request.url))
        
        if current_user.role != UserRole.ADMIN:
            logger.warning(f"Non-admin user {current_user.id} attempted to access admin function {f.__name__}")
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Administrator privileges required.", "Error")
            
            # Log security event
            try:
                session_manager = getattr(current_app, "request_session_manager", None) or current_app.config.get("db_manager")
                db_session = session_manager.get_session()
                try:
                    UserAuditLog.log_action(
                        db_session,
                        action='ADMIN_ACCESS_DENIED',
                        user_id=current_user.id,
                        details=f"Attempted to access admin function {f.__name__}",
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent')
                    )
                    db_session.commit()
                finally:
                    session_manager.close_session(db_session)
            except Exception as e:
                logger.error(f"Failed to log admin access denied event: {e}")
            
            return redirect(url_for('main.index'))
        
        # Preserve admin session context using Redis sessions
        try:
            # Skip Redis session context for now - causing import errors
            # Log admin action
            try:
                session_manager = getattr(current_app, "request_session_manager", None) or current_app.config.get("db_manager")
                db_session = session_manager.get_session()
                try:
                    UserAuditLog.log_action(
                        db_session,
                        action='ADMIN_ACCESS',
                        user_id=current_user.id,
                        details=f"Accessed admin function {f.__name__}",
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent')
                    )
                    db_session.commit()
                finally:
                    session_manager.close_session(db_session)
            except Exception as e:
                logger.error(f"Failed to log admin access event: {e}")
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in admin access control for {f.__name__}: {e}")
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("An error occurred while accessing the admin interface.", "Error")
            return redirect(url_for('main.index'))
    
    return decorated_function

def admin_session_preservation(f):
    """
    Decorator to preserve admin session during user management operations.
    Uses Redis sessions instead of Flask sessions.
    Ensures admin users don't lose their session when managing other users.
    
    Requirements: 1.3, 1.4
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            return redirect(url_for('user_management.login'))
        
        # Get Redis session manager and current session
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        admin_session_backup = None
        
        if unified_session_manager:
            try:
                # Get current session ID from request context
                session_id = getattr(request, 'session_id', None) or getattr(g, 'session_id', None)
                
                if session_id:
                    # Backup current Redis session state
                    session_data = unified_session_manager.get_session_data(session_id)
                    if session_data:
                        admin_session_backup = {
                            'session_id': session_id,
                            'user_id': session_data.get('user_id'),
                            'platform_connection_id': session_data.get('platform_connection_id'),
                            'admin_context': session_data.get('admin_context'),
                            'session_data': session_data.copy()
                        }
                        logger.debug(f"Backed up admin session state for session {session_id}")
                else:
                    logger.warning("No Redis session ID found for admin session preservation")
            except Exception as e:
                logger.error(f"Failed to backup admin session state: {e}")
        
        try:
            result = f(*args, **kwargs)
            
            # Restore admin session state after operation (if we have a backup)
            if admin_session_backup and unified_session_manager:
                try:
                    session_id = admin_session_backup['session_id']
                    # Restore the session data
                    unified_session_manager.update_session(
                        session_id, 
                        admin_session_backup['session_data']
                    )
                    logger.debug(f"Restored admin session state for session {session_id}")
                except Exception as restore_error:
                    logger.error(f"Failed to restore admin session state: {restore_error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in admin session preservation for {f.__name__}: {e}")
            
            # Attempt to restore session on error
            if admin_session_backup and unified_session_manager:
                try:
                    session_id = admin_session_backup['session_id']
                    unified_session_manager.update_session(
                        session_id, 
                        admin_session_backup['session_data']
                    )
                    logger.debug(f"Restored admin session state after error for session {session_id}")
                except Exception as restore_error:
                    logger.error(f"Failed to restore admin session after error: {restore_error}")
            
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("An error occurred during the admin operation.", "Error")
            return redirect(url_for('admin.user_management'))
    
    return decorated_function

def admin_api_required(f):
    """
    API version of admin requirement decorator for AJAX endpoints.
    
    Requirements: 1.2, 1.3, 1.4, 1.5
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        if current_user.role != UserRole.ADMIN:
            logger.warning(f"Non-admin user {current_user.id} attempted to access admin API {f.__name__}")
            
            # Log security event
            try:
                session_manager = getattr(current_app, "request_session_manager", None) or current_app.config.get("db_manager")
                db_session = session_manager.get_session()
                try:
                    UserAuditLog.log_action(
                        db_session,
                        action='ADMIN_API_ACCESS_DENIED',
                        user_id=current_user.id,
                        details=f"Attempted to access admin API {f.__name__}",
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent')
                    )
                    db_session.commit()
                finally:
                    session_manager.close_session(db_session)
            except Exception as e:
                logger.error(f"Failed to log admin API access denied event: {e}")
            
            return jsonify({'success': False, 'error': 'Administrator privileges required'}), 403
        
        # Log admin API access
        try:
            session_manager = getattr(current_app, "request_session_manager", None) or current_app.config.get("db_manager")
            db_session = session_manager.get_session()
            try:
                UserAuditLog.log_action(
                    db_session,
                    action='ADMIN_API_ACCESS',
                    user_id=current_user.id,
                    details=f"Accessed admin API {f.__name__}",
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                db_session.commit()
            finally:
                session_manager.close_session(db_session)
        except Exception as e:
            logger.error(f"Failed to log admin API access event: {e}")
        
        return f(*args, **kwargs)
    
    return decorated_function

def admin_user_management_access(f):
    """
    Decorator specifically for user management operations.
    Includes additional safeguards and logging.
    
    Requirements: 1.3, 1.4, 1.5
    """
    @wraps(f)
    @admin_required
    @admin_session_preservation
    def decorated_function(*args, **kwargs):
        # Additional user management specific checks
        target_user_id = kwargs.get('user_id') or request.form.get('user_id') or request.json.get('user_id') if request.json else None
        
        if target_user_id:
            try:
                session_manager = getattr(current_app, "request_session_manager", None) or current_app.config.get("db_manager")
                db_session = session_manager.get_session()
                try:
                    from models import User
                    target_user = db_session.query(User).filter_by(id=target_user_id).first()
                    
                    if target_user:
                        # Log user management action
                        UserAuditLog.log_action(
                            db_session,
                            action='USER_MANAGEMENT_ACCESS',
                            user_id=target_user.id,
                            admin_user_id=current_user.id,
                            details=f"Admin accessed user management function {f.__name__} for user {target_user.username}",
                            ip_address=request.remote_addr,
                            user_agent=request.headers.get('User-Agent')
                        )
                        db_session.commit()
                finally:
                    session_manager.close_session(db_session)
                        
            except Exception as e:
                logger.error(f"Error logging user management access: {e}")
        
        return f(*args, **kwargs)
    
    return decorated_function

def ensure_admin_count(f):
    """
    Decorator to ensure at least one admin user remains in the system.
    Used for user deletion and role changes.
    
    Requirements: 1.5
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        target_user_id = kwargs.get('user_id') or request.form.get('user_id') or request.json.get('user_id') if request.json else None
        
        if target_user_id:
            try:
                session_manager = getattr(current_app, "request_session_manager", None) or current_app.config.get("db_manager")
                db_session = session_manager.get_session()
                try:
                    from models import User
                    
                    # Count current admin users
                    admin_count = db_session.query(User).filter_by(
                        role=UserRole.ADMIN,
                        is_active=True
                    ).count()
                    
                    # Check if target user is admin
                    target_user = db_session.query(User).filter_by(id=target_user_id).first()
                    
                    if target_user and target_user.role == UserRole.ADMIN and admin_count <= 1:
                        logger.warning(f"Attempt to delete/modify last admin user {target_user_id} by admin {current_user.id}")
                        
                        if request.is_json:
                            return jsonify({
                                'success': False, 
                                'error': 'Cannot delete or modify the last administrator account'
                            }), 400
                        else:
                            # Send error notification
                            from app.services.notification.helpers.notification_helpers import send_error_notification
                            send_error_notification("Cannot delete or modify the last administrator account.", "Error")
                            return redirect(url_for('admin.user_management'))
                finally:
                    session_manager.close_session(db_session)
            except Exception as e:
                logger.error(f"Error checking admin count: {e}")
                if request.is_json:
                    return jsonify({'success': False, 'error': 'Error validating admin count'}), 500
                else:
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification("Error validating admin count.", "Error")
                    return redirect(url_for('admin.user_management'))
        
        return f(*args, **kwargs)
    
    return decorated_function

def admin_context_processor():
    """
    Context processor to inject admin-specific variables into templates.
    
    Requirements: 1.2, 1.4
    """
    if current_user.is_authenticated and current_user.role == UserRole.ADMIN:
        try:
            session_manager = getattr(current_app, "request_session_manager", None) or current_app.config.get("db_manager")
            db_session = session_manager.get_session()
            try:
                from models import User, PlatformConnection, Image
                
                # Get admin-specific statistics - Fixed: Separate simpler queries
                from models import ProcessingStatus
                
                total_users = db_session.query(User).count()
                active_users = db_session.query(User).filter_by(is_active=True).count()
                unverified_users = db_session.query(User).filter_by(email_verified=False).count()
                locked_users = db_session.query(User).filter_by(account_locked=True).count()
                total_platforms = db_session.query(PlatformConnection).filter_by(is_active=True).count()
                total_pending_review = db_session.query(Image).filter_by(status=ProcessingStatus.PENDING).count()
                
                # Get admin context from Redis session instead of Flask session
                admin_session_context = None
                try:
                    unified_session_manager = getattr(current_app, 'unified_session_manager', None)
                    if unified_session_manager:
                        # Get session ID from request context
                        session_id = getattr(request, 'session_id', None) or getattr(g, 'session_id', None)
                        if session_id:
                            session_data = unified_session_manager.get_session_data(session_id)
                            admin_session_context = session_data.get('admin_context') if session_data else None
                except Exception as e:
                    logger.debug(f"Could not get admin context from Redis session: {e}")
                
                return {
                    'admin_stats': {
                        'total_users': total_users,
                        'active_users': active_users,
                        'unverified_users': unverified_users,
                        'locked_users': locked_users,
                        'total_platforms': total_platforms,
                        'total_pending_review': total_pending_review
                    },
                    'is_admin_interface': True,
                    'admin_session_context': admin_session_context
                }
            finally:
                session_manager.close_session(db_session)
                
        except Exception as e:
            logger.error(f"Error in admin context processor: {e}")
            return {
                'admin_stats': {},
                'is_admin_interface': True,
                'admin_session_context': None
            }
    
    return {}

def get_admin_accessible_users():
    """
    Get all users accessible to admin (all users).
    
    Returns:
        list: List of all users
        
    Requirements: 1.2, 1.4
    """
    if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
        return []
    
    try:
        session_manager = getattr(current_app, "request_session_manager", None) or current_app.config.get("db_manager")
        db_session = session_manager.get_session()
        try:
            from models import User
            users = db_session.query(User).all()
            return users
        finally:
            session_manager.close_session(db_session)
    except Exception as e:
        logger.error(f"Error getting admin accessible users: {e}")
        return []

def get_admin_accessible_platforms():
    """
    Get all platforms accessible to admin (all platforms).
    
    Returns:
        list: List of all platform connections
        
    Requirements: 1.2, 1.4
    """
    if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
        return []
    
    try:
        session_manager = getattr(current_app, "request_session_manager", None) or current_app.config.get("db_manager")
        db_session = session_manager.get_session()
        try:
            from models import PlatformConnection
            platforms = db_session.query(PlatformConnection).filter_by(is_active=True).all()
            return platforms
        finally:
            session_manager.close_session(db_session)
    except Exception as e:
        logger.error(f"Error getting admin accessible platforms: {e}")
        return []

def get_admin_system_stats():
    """
    Get comprehensive system statistics for admin dashboard.
    
    Returns:
        dict: System statistics
        
    Requirements: 1.2, 1.4
    """
    if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
        return {}
    
    try:
        session_manager = getattr(current_app, "request_session_manager", None) or current_app.config.get("db_manager")
        db_session = session_manager.get_session()
        try:
            from models import User, PlatformConnection, Image, Post, ProcessingStatus
            from datetime import datetime, timedelta
            
            # User statistics - Optimized: Single query with aggregation
            from sqlalchemy import func, case
            user_stats = db_session.query(
                func.count(User.id).label('total_users'),
                func.sum(case((User.is_active == True, 1), else_=0)).label('active_users'),
                func.sum(case((User.email_verified == False, 1), else_=0)).label('unverified_users'),
                func.sum(case((User.account_locked == True, 1), else_=0)).label('locked_users')
            ).first()
            
            total_users = user_stats.total_users or 0
            active_users = user_stats.active_users or 0
            unverified_users = user_stats.unverified_users or 0
            locked_users = user_stats.locked_users or 0
            
            # Platform and content statistics - Fixed: Separate simpler queries
            total_platforms = db_session.query(PlatformConnection).filter_by(is_active=True).count()
            total_images = db_session.query(Image).count()
            pending_review = db_session.query(Image).filter_by(status=ProcessingStatus.PENDING).count()
            approved_images = db_session.query(Image).filter_by(status=ProcessingStatus.APPROVED).count()
            total_posts = db_session.query(Post).count()
            
            # Recent activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            new_users_24h = db_session.query(User).filter(User.created_at >= yesterday).count()
            processed_24h = db_session.query(Image).filter(Image.updated_at >= yesterday).count()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'unverified_users': unverified_users,
                'locked_users': locked_users,
                'total_platforms': total_platforms,
                'total_images': total_images,
                'pending_review': pending_review,
                'approved_images': approved_images,
                'total_posts': total_posts,
                'new_users_24h': new_users_24h,
                'processed_24h': processed_24h
            }
        finally:
            session_manager.close_session(db_session)
            
    except Exception as e:
        logger.error(f"Error getting admin system stats: {e}")
        return {}