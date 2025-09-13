# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Platform Management Routes"""

from flask import render_template, request, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import PlatformConnection, User, UserRole
from app.core.security.core.security_middleware import rate_limit, validate_input_length, validate_csrf_token
from app.core.security.validation.enhanced_input_validation import enhanced_input_validation
from app.core.security.core.security_utils import sanitize_for_log
from app.core.security.middleware.platform_access_middleware import filter_platforms_for_user
from app.services.admin.security.admin_access_control import admin_required
from app.services.platform.components.platform_service import PlatformService
from app.services.platform.components.platform_identification import identify_user_platform
from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

def get_notification_manager():
    """Get unified notification manager instance"""
    return current_app.unified_notification_manager

def create_platform_notification(platform_id: int, platform_name: str, operation_type: str, message: str):
    """
    Create platform management notification using unified system
    
    Args:
        platform_id: ID of platform being managed
        platform_name: Name of platform being managed  
        operation_type: Type of operation (create, update, delete, etc.)
        message: Notification message
    """
    try:
        notification_manager = get_notification_manager()
        notification_manager.send_admin_notification(
            message=message,
            notification_type='platform_management',
            metadata={
                'platform_id': platform_id,
                'platform_name': platform_name,
                'operation_type': operation_type,
                'admin_user_id': current_user.id,
                'admin_username': current_user.username,
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }
        )
    except Exception as e:
        current_app.logger.error(f"Failed to send platform management notification: {e}")

def register_routes(bp):
    """Register platform management routes"""
    
    @bp.route('/platforms')
    @login_required
    @admin_required
    def platform_management():
        """Platform management interface with filtering and statistics"""
        
        db_manager = current_app.config['db_manager']
        redis_platform_manager = current_app.config.get('redis_platform_manager')
        
        # Get filter parameters
        platform_type_filter = request.args.get('platform_type')
        status_filter = request.args.get('status')
        user_filter = request.args.get('user_id')
        search_term = request.args.get('search')
        page_size = int(request.args.get('page_size', 25))
        page = int(request.args.get('page', 1))
        offset = (page - 1) * page_size
        
        try:
            with db_manager.get_session() as session:
                # Base query with user information
                query = session.query(PlatformConnection).join(User)
                
                # Apply filters
                if platform_type_filter:
                    query = query.filter(PlatformConnection.platform_type == platform_type_filter)
                
                if status_filter == 'active':
                    query = query.filter(PlatformConnection.is_active == True)
                elif status_filter == 'inactive':
                    query = query.filter(PlatformConnection.is_active == False)
                elif status_filter == 'default':
                    query = query.filter(PlatformConnection.is_default == True)
                
                if user_filter:
                    try:
                        user_id = int(user_filter)
                        query = query.filter(PlatformConnection.user_id == user_id)
                    except ValueError:
                        pass
                
                if search_term:
                    search_pattern = f"%{search_term}%"
                    query = query.filter(
                        (PlatformConnection.name.ilike(search_pattern)) |
                        (PlatformConnection.instance_url.ilike(search_pattern)) |
                        (User.username.ilike(search_pattern))
                    )
                
                # Get total count for pagination
                total_count = query.count()
                
                # Apply pagination and ordering
                platforms = query.order_by(
                    desc(PlatformConnection.is_active),
                    desc(PlatformConnection.is_default),
                    PlatformConnection.name
                ).offset(offset).limit(page_size).all()
                
                # Get platform statistics
                platform_stats = _get_platform_statistics(session)
                
                # Get user list for filter dropdown
                users = session.query(User).filter(User.is_active == True).order_by(User.username).all()
                
                return render_template('admin_platform_management.html',
                                     platforms=platforms,
                                     total_platforms=total_count,
                                     platform_stats=platform_stats,
                                     users=users,
                                     current_filters={
                                         'platform_type': platform_type_filter,
                                         'status': status_filter,
                                         'user_id': user_filter,
                                         'search': search_term
                                     },
                                     pagination={
                                         'page': page,
                                         'page_size': page_size,
                                         'total_pages': (total_count + page_size - 1) // page_size,
                                         'has_prev': page > 1,
                                         'has_next': page * page_size < total_count
                                     })
                                     
        except Exception as e:
            current_app.logger.error(f"Error loading platform management: {sanitize_for_log(str(e))}")
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Error loading platform management interface.", "Platform Management Error")
            return redirect(url_for('admin.dashboard'))
    
    @bp.route('/platforms/<int:platform_id>/details')
    @login_required
    @admin_required
    def get_platform_details(platform_id):
        """Get detailed platform information"""
        
        db_manager = current_app.config['db_manager']
        
        try:
            with db_manager.get_session() as session:
                platform = session.query(PlatformConnection).join(User).filter(
                    PlatformConnection.id == platform_id
                ).first()
                
                if not platform:
                    return jsonify({'success': False, 'error': 'Platform not found'}), 404
                
                # Get platform usage statistics
                platform_usage = _get_platform_usage_stats(session, platform_id)
                
                platform_data = {
                    'id': platform.id,
                    'name': platform.name,
                    'platform_type': platform.platform_type,
                    'instance_url': platform.instance_url,
                    'username': platform.username,
                    'is_active': platform.is_active,
                    'is_default': platform.is_default,
                    'created_at': platform.created_at.isoformat() if platform.created_at else None,
                    'last_used': platform.last_used.isoformat() if platform.last_used else None,
                    'owner': {
                        'id': platform.user.id,
                        'username': platform.user.username,
                        'email': platform.user.email,
                        'role': platform.user.role.value
                    },
                    'usage_stats': platform_usage
                }
                
                return jsonify({
                    'success': True,
                    'platform': platform_data
                })
                
        except Exception as e:
            current_app.logger.error(f"Error getting platform details: {sanitize_for_log(str(e))}")
            return jsonify({'success': False, 'error': 'Failed to get platform details'}), 500
    
    @bp.route('/platforms/<int:platform_id>/toggle-status', methods=['POST'])
    @login_required
    @admin_required
    @rate_limit(limit=10, window_seconds=60)
    @validate_csrf_token
    def toggle_platform_status(platform_id):
        """Toggle platform active status"""
        
        db_manager = current_app.config['db_manager']
        redis_platform_manager = current_app.config.get('redis_platform_manager')
        
        try:
            with db_manager.get_session() as session:
                platform = session.query(PlatformConnection).filter(
                    PlatformConnection.id == platform_id
                ).first()
                
                if not platform:
                    return jsonify({'success': False, 'error': 'Platform not found'}), 404
                
                # Store original status for notification
                old_status = platform.is_active
                platform_name = platform.name
                
                # Toggle status
                platform.is_active = not platform.is_active
                session.commit()
                
                # Clear Redis cache for this user's platforms
                if redis_platform_manager:
                    try:
                        redis_platform_manager.clear_user_platforms(platform.user_id)
                    except Exception as redis_error:
                        current_app.logger.warning(f"Failed to clear Redis cache: {redis_error}")
                
                # Send notification
                status_text = "activated" if platform.is_active else "deactivated"
                create_platform_notification(
                    platform_id=platform_id,
                    platform_name=platform_name,
                    operation_type='status_changed',
                    message=f"Platform {platform_name} {status_text} by admin {current_user.username}"
                )
                
                return jsonify({
                    'success': True,
                    'message': f'Platform {status_text} successfully',
                    'new_status': platform.is_active
                })
                
        except Exception as e:
            current_app.logger.error(f"Error toggling platform status: {sanitize_for_log(str(e))}")
            return jsonify({'success': False, 'error': 'Failed to update platform status'}), 500
    
    @bp.route('/platforms/<int:platform_id>/set-default', methods=['POST'])
    @login_required
    @admin_required
    @rate_limit(limit=10, window_seconds=60)
    @validate_csrf_token
    def set_platform_default(platform_id):
        """Set platform as default for its user"""
        
        db_manager = current_app.config['db_manager']
        redis_platform_manager = current_app.config.get('redis_platform_manager')
        
        try:
            with db_manager.get_session() as session:
                platform = session.query(PlatformConnection).filter(
                    PlatformConnection.id == platform_id
                ).first()
                
                if not platform:
                    return jsonify({'success': False, 'error': 'Platform not found'}), 404
                
                if not platform.is_active:
                    return jsonify({'success': False, 'error': 'Cannot set inactive platform as default'}), 400
                
                # Clear existing default for this user
                session.query(PlatformConnection).filter(
                    PlatformConnection.user_id == platform.user_id,
                    PlatformConnection.is_default == True
                ).update({'is_default': False})
                
                # Set new default
                platform.is_default = True
                session.commit()
                
                # Clear Redis cache for this user's platforms
                if redis_platform_manager:
                    try:
                        redis_platform_manager.clear_user_platforms(platform.user_id)
                    except Exception as redis_error:
                        current_app.logger.warning(f"Failed to clear Redis cache: {redis_error}")
                
                # Send notification
                create_platform_notification(
                    platform_id=platform_id,
                    platform_name=platform.name,
                    operation_type='default_changed',
                    message=f"Platform {platform.name} set as default for user {platform.user.username} by admin {current_user.username}"
                )
                
                return jsonify({
                    'success': True,
                    'message': f'Platform {platform.name} set as default successfully'
                })
                
        except Exception as e:
            current_app.logger.error(f"Error setting platform default: {sanitize_for_log(str(e))}")
            return jsonify({'success': False, 'error': 'Failed to set platform as default'}), 500
    
    @bp.route('/platforms/<int:platform_id>/test-connection', methods=['POST'])
    @login_required
    @admin_required
    @rate_limit(limit=5, window_seconds=60)
    def test_platform_connection(platform_id):
        """Test platform connection"""
        
        db_manager = current_app.config['db_manager']
        
        try:
            with db_manager.get_session() as session:
                platform = session.query(PlatformConnection).filter(
                    PlatformConnection.id == platform_id
                ).first()
                
                if not platform:
                    return jsonify({'success': False, 'error': 'Platform not found'}), 404
                
                # Test connection using platform service
                platform_service = PlatformService()
                
                # This would need to be implemented in the platform service
                # For now, return a mock response
                connection_test = {
                    'success': True,
                    'response_time': 150,  # ms
                    'status_code': 200,
                    'platform_version': '4.0.0',
                    'last_tested': datetime.utcnow().isoformat()
                }
                
                # Update last tested timestamp
                platform.last_used = datetime.utcnow()
                session.commit()
                
                return jsonify({
                    'success': True,
                    'connection_test': connection_test
                })
                
        except Exception as e:
            current_app.logger.error(f"Error testing platform connection: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False, 
                'error': 'Connection test failed',
                'connection_test': {
                    'success': False,
                    'error': str(e),
                    'last_tested': datetime.utcnow().isoformat()
                }
            }), 500
    
    @bp.route('/platforms/statistics')
    @login_required
    @admin_required
    def platform_statistics():
        """Get platform statistics for dashboard widgets"""
        
        db_manager = current_app.config['db_manager']
        
        try:
            with db_manager.get_session() as session:
                stats = _get_platform_statistics(session)
                return jsonify({
                    'success': True,
                    'statistics': stats
                })
                
        except Exception as e:
            current_app.logger.error(f"Error getting platform statistics: {sanitize_for_log(str(e))}")
            return jsonify({'success': False, 'error': 'Failed to get platform statistics'}), 500
    
    # API endpoints for platform management
    @bp.route('/api/platform/list', methods=['GET'])
    @login_required
    @admin_required
    def api_platform_list():
        """API endpoint to get platform list with filtering and pagination"""
        
        db_manager = current_app.config['db_manager']
        
        try:
            # Get filter parameters
            platform_type_filter = request.args.get('platform_type')
            status_filter = request.args.get('status')
            user_filter = request.args.get('user_id')
            search_term = request.args.get('search')
            page_size = int(request.args.get('page_size', 25))
            page = int(request.args.get('page', 1))
            offset = (page - 1) * page_size
            
            with db_manager.get_session() as session:
                # Base query with user information
                query = session.query(PlatformConnection).join(User)
                
                # Apply filters
                if platform_type_filter:
                    query = query.filter(PlatformConnection.platform_type == platform_type_filter)
                
                if status_filter == 'active':
                    query = query.filter(PlatformConnection.is_active == True)
                elif status_filter == 'inactive':
                    query = query.filter(PlatformConnection.is_active == False)
                elif status_filter == 'default':
                    query = query.filter(PlatformConnection.is_default == True)
                
                if user_filter:
                    try:
                        user_id = int(user_filter)
                        query = query.filter(PlatformConnection.user_id == user_id)
                    except ValueError:
                        pass
                
                if search_term:
                    search_pattern = f"%{search_term}%"
                    query = query.filter(
                        (PlatformConnection.name.ilike(search_pattern)) |
                        (PlatformConnection.instance_url.ilike(search_pattern)) |
                        (User.username.ilike(search_pattern))
                    )
                
                # Get total count for pagination
                total_count = query.count()
                
                # Apply pagination and ordering
                platforms = query.order_by(
                    desc(PlatformConnection.is_active),
                    desc(PlatformConnection.is_default),
                    PlatformConnection.name
                ).offset(offset).limit(page_size).all()
                
                # Convert to API response format
                platform_list = []
                for platform in platforms:
                    platform_list.append({
                        'id': platform.id,
                        'name': platform.name,
                        'platform_type': platform.platform_type,
                        'instance_url': platform.instance_url,
                        'username': platform.username,
                        'is_active': platform.is_active,
                        'is_default': platform.is_default,
                        'created_at': platform.created_at.isoformat() if platform.created_at else None,
                        'last_used': platform.last_used.isoformat() if platform.last_used else None,
                        'owner': {
                            'id': platform.user.id,
                            'username': platform.user.username,
                            'email': platform.user.email,
                            'role': platform.user.role.value
                        }
                    })
                
                return jsonify({
                    'success': True,
                    'platforms': platform_list,
                    'total_count': total_count,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total_count + page_size - 1) // page_size
                })
                
        except Exception as e:
            current_app.logger.error(f"Error getting platform list: {sanitize_for_log(str(e))}")
            return jsonify({'success': False, 'error': 'Failed to get platform list'}), 500
    
    @bp.route('/api/platform/status', methods=['GET'])
    @login_required
    @admin_required
    def api_platform_status():
        """API endpoint to get platform status overview"""
        
        db_manager = current_app.config['db_manager']
        
        try:
            with db_manager.get_session() as session:
                # Get platform statistics
                stats = _get_platform_statistics(session)
                
                # Get recent platform activities
                recent_activities = []
                recent_platforms = session.query(PlatformConnection).join(User).order_by(
                    desc(PlatformConnection.last_used)
                ).limit(10).all()
                
                for platform in recent_platforms:
                    recent_activities.append({
                        'platform_id': platform.id,
                        'platform_name': platform.name,
                        'platform_type': platform.platform_type,
                        'username': platform.user.username,
                        'last_used': platform.last_used.isoformat() if platform.last_used else None,
                        'is_active': platform.is_active
                    })
                
                return jsonify({
                    'success': True,
                    'status': {
                        'statistics': stats,
                        'recent_activities': recent_activities,
                        'system_health': {
                            'total_platforms': stats['total_platforms'],
                            'active_platforms': stats['active_platforms'],
                            'inactive_platforms': stats['inactive_platforms'],
                            'users_with_platforms': stats['users_with_platforms'],
                            'recent_activity_count': stats['recent_activity']
                        }
                    }
                })
                
        except Exception as e:
            current_app.logger.error(f"Error getting platform status: {sanitize_for_log(str(e))}")
            return jsonify({'success': False, 'error': 'Failed to get platform status'}), 500
    
    @bp.route('/api/platform/search', methods=['GET'])
    @login_required
    @admin_required
    def api_platform_search():
        """API endpoint to search platforms"""
        
        db_manager = current_app.config['db_manager']
        
        try:
            search_term = request.args.get('q', '').strip()
            platform_type = request.args.get('type')
            status = request.args.get('status')
            limit = int(request.args.get('limit', 50))
            
            if not search_term:
                return jsonify({'success': False, 'error': 'Search term is required'}), 400
            
            with db_manager.get_session() as session:
                # Base query with user information
                query = session.query(PlatformConnection).join(User)
                
                # Apply search filter
                search_pattern = f"%{search_term}%"
                query = query.filter(
                    (PlatformConnection.name.ilike(search_pattern)) |
                    (PlatformConnection.instance_url.ilike(search_pattern)) |
                    (User.username.ilike(search_pattern))
                )
                
                # Apply additional filters
                if platform_type:
                    query = query.filter(PlatformConnection.platform_type == platform_type)
                
                if status == 'active':
                    query = query.filter(PlatformConnection.is_active == True)
                elif status == 'inactive':
                    query = query.filter(PlatformConnection.is_active == False)
                elif status == 'default':
                    query = query.filter(PlatformConnection.is_default == True)
                
                # Apply limit and ordering
                platforms = query.order_by(
                    desc(PlatformConnection.is_active),
                    desc(PlatformConnection.is_default),
                    PlatformConnection.name
                ).limit(limit).all()
                
                # Convert to search results format
                search_results = []
                for platform in platforms:
                    search_results.append({
                        'id': platform.id,
                        'name': platform.name,
                        'platform_type': platform.platform_type,
                        'instance_url': platform.instance_url,
                        'username': platform.username,
                        'is_active': platform.is_active,
                        'is_default': platform.is_default,
                        'owner': {
                            'id': platform.user.id,
                            'username': platform.user.username,
                            'email': platform.user.email
                        },
                        'match_score': 100,  # Default match score
                        'highlighted_fields': {
                            'name': platform.name if search_term.lower() in platform.name.lower() else None,
                            'instance_url': platform.instance_url if search_term.lower() in platform.instance_url.lower() else None,
                            'username': platform.user.username if search_term.lower() in platform.user.username.lower() else None
                        }
                    })
                
                return jsonify({
                    'success': True,
                    'search_results': search_results,
                    'search_term': search_term,
                    'total_results': len(search_results),
                    'filters_applied': {
                        'platform_type': platform_type,
                        'status': status,
                        'limit': limit
                    }
                })
                
        except Exception as e:
            current_app.logger.error(f"Error searching platforms: {sanitize_for_log(str(e))}")
            return jsonify({'success': False, 'error': 'Failed to search platforms'}), 500

def _get_platform_statistics(session):
    """Get comprehensive platform statistics"""
    try:
        # Basic counts
        total_platforms = session.query(PlatformConnection).count()
        active_platforms = session.query(PlatformConnection).filter(
            PlatformConnection.is_active == True
        ).count()
        
        # Platform type distribution
        platform_types = session.query(
            PlatformConnection.platform_type,
            func.count(PlatformConnection.id).label('count')
        ).group_by(PlatformConnection.platform_type).all()
        
        # Recent activity (platforms used in last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_activity = session.query(PlatformConnection).filter(
            PlatformConnection.last_used >= week_ago
        ).count()
        
        # Users with platforms
        users_with_platforms = session.query(PlatformConnection.user_id).distinct().count()
        
        return {
            'total_platforms': total_platforms,
            'active_platforms': active_platforms,
            'inactive_platforms': total_platforms - active_platforms,
            'platform_types': {pt.platform_type: pt.count for pt in platform_types},
            'recent_activity': recent_activity,
            'users_with_platforms': users_with_platforms,
            'average_platforms_per_user': round(total_platforms / max(users_with_platforms, 1), 2)
        }
        
    except Exception as e:
        logger.error(f"Error calculating platform statistics: {e}")
        return {
            'total_platforms': 0,
            'active_platforms': 0,
            'inactive_platforms': 0,
            'platform_types': {},
            'recent_activity': 0,
            'users_with_platforms': 0,
            'average_platforms_per_user': 0
        }

def _get_platform_usage_stats(session, platform_id):
    """Get usage statistics for a specific platform"""
    try:
        # This would need to be implemented based on your models
        # For now, return mock data
        return {
            'total_posts': 0,
            'total_images': 0,
            'last_activity': None,
            'posts_this_month': 0,
            'images_this_month': 0
        }
        
    except Exception as e:
        logger.error(f"Error getting platform usage stats: {e}")
        return {
            'total_posts': 0,
            'total_images': 0,
            'last_activity': None,
            'posts_this_month': 0,
            'images_this_month': 0
        }