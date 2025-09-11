# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from flask import Blueprint, render_template, redirect, url_for, current_app, request, jsonify, abort
from flask_login import login_required, current_user
from models import UserRole, PlatformConnection, User
from app.utils.session.session_detection import has_previous_session, SessionDetectionResult
from app.utils.web.request_helpers import sanitize_user_input
from app.utils.web.error_responses import handle_security_error
from app.utils.templates.template_cache import cached_render_template, get_template_cache_stats
from app.services.monitoring.performance.monitors.performance_monitor import monitor_performance, record_database_query
from app.utils.landing.landing_page_fallback import (
    ensure_system_stability, 
    handle_template_rendering_error,
    handle_session_detection_error,
    handle_authentication_error,
    log_authentication_failure,
    create_fallback_landing_html,
    AuthenticationFailureError,
    TemplateRenderingError,
    SessionDetectionError
)
from app.core.security.core.decorators import conditional_rate_limit, conditional_enhanced_input_validation
import logging
import traceback

main_bp = Blueprint('main', __name__)

@main_bp.route('/landing')
@conditional_rate_limit(requests_per_minute=60)
@conditional_enhanced_input_validation
@monitor_performance
def landing():
    """
    Direct landing page route that bypasses session detection.
    Always shows the landing page regardless of session state.
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Direct landing page access")
        return cached_render_template('landing.html')
        
    except Exception as e:
        logger.error(f"Error rendering landing page: {e}")
        return handle_template_rendering_error(
            TemplateRenderingError(
                template_name='landing.html',
                message=str(e),
                template_context={},
                original_exception=e
            )
        )

@main_bp.route('/')
@conditional_rate_limit(requests_per_minute=60)  # Allow 60 requests per minute for landing page
@conditional_enhanced_input_validation
@monitor_performance
@ensure_system_stability
def index():
    """
    Main route with three-way logic:
    - Authenticated users: Show dashboard
    - Returning users (with previous session): Redirect to login
    - New users: Show landing page
    
    Security is handled by decorators and middleware:
    - Rate limiting via @conditional_rate_limit
    - Input validation via @conditional_enhanced_input_validation
    - Security headers via SecurityMiddleware
    - System stability via @ensure_system_stability
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Check if user is authenticated with enhanced error handling
        try:
            if current_user.is_authenticated:
                logger.info(f"Authenticated user {current_user.username} accessing dashboard")
                return render_dashboard()
        except Exception as auth_error:
            # Log authentication failure and continue with anonymous flow
            log_authentication_failure(auth_error, {
                'route': 'index',
                'user_authenticated': 'unknown',
                'error_context': 'current_user.is_authenticated check failed'
            })
            logger.warning(f"Authentication check failed, treating as anonymous user: {auth_error}")
        
        # Check if user has previous session indicators with error handling
        try:
            has_previous = has_previous_session()
            if has_previous:
                logger.info("Anonymous user with previous session detected, redirecting to login")
                return redirect(url_for('auth.user_management.login', _external=False))
        except Exception as session_error:
            # Handle session detection error - default to new user
            has_previous = handle_session_detection_error(session_error, {
                'route': 'index',
                'error_context': 'session detection failed'
            })
            if has_previous:
                logger.info("Session detection recovered, redirecting to login")
                return redirect(url_for('auth.user_management.login', _external=False))
            else:
                logger.info("Session detection failed, treating as new user")
        
        # Completely new user - show landing page with enhanced error handling
        logger.info("New anonymous user detected, showing landing page")
        
        try:
            # Use cached template rendering for performance
            return cached_render_template('landing.html')
        except Exception as template_error:
            # Handle template rendering error
            logger.error(f"Landing page template rendering failed: {template_error}")
            raise TemplateRenderingError(
                template_name='landing.html',
                message=str(template_error),
                template_context={},
                original_exception=template_error
            )
            
    except (TemplateRenderingError, AuthenticationFailureError, SessionDetectionError):
        # These are handled by the @ensure_system_stability decorator
        raise
        
    except Exception as e:
        # Enhanced error logging with sanitization
        error_msg = sanitize_user_input(str(e))
        logger.error(f"Unexpected error in index route: {error_msg}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
        # Handle potential security-related errors
        if "security" in str(e).lower() or "csrf" in str(e).lower():
            logger.warning(f"Security-related error detected: {error_msg}")
            return handle_security_error("Access denied", 403)
        
        # For any other unexpected error, let the decorator handle it
        raise


def render_dashboard():
    """Render the main dashboard for authenticated users with enhanced error handling"""
    logger = logging.getLogger(__name__)
    
    try:
        # Get unified session manager from app with error handling
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        db_manager = getattr(current_app, 'config', {}).get('db_manager')
        
        if not unified_session_manager or not db_manager:
            logger.warning("Missing unified_session_manager or db_manager, using minimal dashboard")
            try:
                return render_template('index.html', stats={}, current_platform=None)
            except Exception as template_error:
                logger.error(f"Dashboard template rendering failed: {template_error}")
                raise TemplateRenderingError(
                    template_name='index.html',
                    message=str(template_error),
                    template_context={'stats': {}, 'current_platform': None},
                    original_exception=template_error
                )
        
        # Use unified session manager for database queries with error handling
        try:
            with unified_session_manager.get_db_session() as db_session:
                # Check if user has accessible platform connections
                try:
                    record_database_query()  # Track database query for performance monitoring
                    platforms_query = db_session.query(PlatformConnection).filter_by(is_active=True)
                    user_platforms = platforms_query.count()
                except Exception as db_error:
                    logger.error(f"Database query for platform connections failed: {db_error}")
                    user_platforms = 0
                
                # Admin users can access dashboard without platforms
                if user_platforms == 0 and current_user.role != UserRole.ADMIN:
                    logger.info(f"User {current_user.username} has no platforms, redirecting to setup")
                    return redirect(url_for('auth.first_time_setup'))
                
                # Get basic statistics with error handling
                try:
                    stats = db_manager.get_processing_stats()
                except Exception as stats_error:
                    logger.error(f"Failed to get processing stats: {stats_error}")
                    stats = {
                        'total_posts': 0,
                        'processed_posts': 0,
                        'pending_posts': 0,
                        'error_posts': 0
                    }
                
                # Platform context will be provided by the context processor
                # No need to manually get it here
                
                # Admin-specific statistics with error handling
                if current_user.role == UserRole.ADMIN:
                    stats['admin_mode'] = True
                    
                    try:
                        # Optimized: Single query with aggregation instead of 3 separate queries
                        from sqlalchemy import func, case
                        record_database_query()  # Track database query for performance monitoring
                        admin_stats = db_session.query(
                            func.count(User.id).label('total_users'),
                            func.sum(case((User.is_active == True, 1), else_=0)).label('active_users'),
                            func.count(PlatformConnection.id).label('total_platforms')
                        ).outerjoin(PlatformConnection).first()
                        
                        stats['total_users'] = admin_stats.total_users or 0
                        stats['active_users'] = admin_stats.active_users or 0
                        stats['total_platforms'] = admin_stats.total_platforms or 0
                    except Exception as admin_stats_error:
                        logger.error(f"Failed to get admin statistics: {admin_stats_error}")
                        stats['total_users'] = 0
                        stats['active_users'] = 0
                        stats['total_platforms'] = 0
                
                # Notification config
                notification_config = {
                    'page_type': 'user_dashboard',
                    'enabled_types': ['system', 'caption', 'platform', 'maintenance'],
                    'auto_hide': True,
                    'max_notifications': 5,
                    'position': 'top-right',
                    'show_progress': False
                }
                
                # Render dashboard template with error handling
                try:
                    return render_template('index.html', stats=stats, notification_config=notification_config)
                except Exception as template_error:
                    logger.error(f"Dashboard template rendering failed: {template_error}")
                    raise TemplateRenderingError(
                        template_name='index.html',
                        message=str(template_error),
                        template_context={'stats': stats, 'notification_config': notification_config},
                        original_exception=template_error
                    )
                    
        except Exception as session_error:
            logger.error(f"Database session error in dashboard: {session_error}")
            # Try to render minimal dashboard
            try:
                return render_template('index.html', stats={})
            except Exception as template_error:
                logger.error(f"Minimal dashboard template rendering failed: {template_error}")
                raise TemplateRenderingError(
                    template_name='index.html',
                    message=str(template_error),
                    template_context={'stats': {}},
                    original_exception=template_error
                )
            
    except TemplateRenderingError:
        # Re-raise template errors to be handled by decorator
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error loading dashboard: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
        # Try one more time with absolute minimal context
        try:
            return render_template('index.html', stats={})
        except Exception as final_error:
            logger.error(f"Final dashboard fallback failed: {final_error}")
            raise TemplateRenderingError(
                template_name='index.html',
                message=str(final_error),
                template_context={'stats': {}},
                original_exception=final_error
            )




@main_bp.route('/index')
@conditional_rate_limit(requests_per_minute=60)
def index_redirect():
    """Redirect /index to main dashboard"""
    return redirect(url_for('main.index', _external=False))


@main_bp.route('/dashboard')
@conditional_rate_limit(requests_per_minute=60)
def dashboard_redirect():
    """Redirect /dashboard to main index"""
    return redirect(url_for('main.index', _external=False))

@main_bp.route('/cache-stats')
@conditional_rate_limit(requests_per_minute=30)
def cache_stats():
    """
    Get template cache statistics for performance monitoring.
    
    This endpoint provides cache performance metrics for monitoring
    and optimization purposes.
    """
    try:
        stats = get_template_cache_stats()
        return jsonify({
            'success': True,
            'cache_stats': stats,
            'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                name='', level=0, pathname='', lineno=0, msg='', args=(), exc_info=None
            ))
        })
    except Exception as e:
        logger.error(f"Error retrieving cache stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve cache statistics'
        }), 500

@main_bp.route('/profile')
@login_required
def profile():
    """Redirect to user management profile"""
    return redirect(url_for('auth.user_management.profile'))
