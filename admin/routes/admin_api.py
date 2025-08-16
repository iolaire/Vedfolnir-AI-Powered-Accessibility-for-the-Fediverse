# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin API Routes"""

from flask import jsonify, request, session
from flask_login import current_user
from models import UserRole
from ..security.admin_access_control import admin_api_required
import logging

logger = logging.getLogger(__name__)


def register_api_routes(bp):
    """Register admin API routes"""
    
    @bp.route('/api/clear_platform_context', methods=['POST'])
    @admin_api_required
    def clear_platform_context():
        """Clear platform context for admin users"""
        try:
            # Clear platform context from session
            session.pop('platform_context', None)
            session.pop('current_platform_id', None)
            
            # Clear from database session if exists
            from database_session_middleware import clear_session_platform
            clear_session_platform()
            
            logger.info(f"Admin user {current_user.id} cleared platform context")
            
            return jsonify({
                'success': True,
                'message': 'Platform context cleared successfully'
            })
            
        except Exception as e:
            logger.error(f"Error clearing platform context for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to clear platform context'
            }), 500
    
    @bp.route('/api/system_stats', methods=['GET'])
    @admin_api_required
    def get_system_stats():
        """Get comprehensive system statistics for admin dashboard"""
        try:
            from .admin_access_control import get_admin_system_stats
            stats = get_admin_system_stats()
            
            return jsonify({
                'success': True,
                'stats': stats
            })
            
        except Exception as e:
            logger.error(f"Error getting system stats for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve system statistics'
            }), 500
    
    @bp.route('/api/user_stats', methods=['GET'])
    @admin_api_required
    def get_user_stats():
        """Get user statistics for admin dashboard"""
        try:
            from flask import current_app
            session_manager = current_app.request_session_manager
            
            with session_manager.session_scope() as db_session:
                from models import User, UserRole
                from datetime import datetime, timedelta
                
                # Basic user counts
                total_users = db_session.query(User).count()
                active_users = db_session.query(User).filter_by(is_active=True).count()
                admin_users = db_session.query(User).filter_by(role=UserRole.ADMIN).count()
                viewer_users = db_session.query(User).filter_by(role=UserRole.VIEWER).count()
                
                # Status counts
                unverified_users = db_session.query(User).filter_by(email_verified=False).count()
                locked_users = db_session.query(User).filter_by(account_locked=True).count()
                
                # Recent activity
                yesterday = datetime.utcnow() - timedelta(days=1)
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                new_users_24h = db_session.query(User).filter(User.created_at >= yesterday).count()
                new_users_7d = db_session.query(User).filter(User.created_at >= week_ago).count()
                
                recent_logins = db_session.query(User).filter(
                    User.last_login >= yesterday
                ).count()
                
                stats = {
                    'total_users': total_users,
                    'active_users': active_users,
                    'admin_users': admin_users,
                    'viewer_users': viewer_users,
                    'unverified_users': unverified_users,
                    'locked_users': locked_users,
                    'new_users_24h': new_users_24h,
                    'new_users_7d': new_users_7d,
                    'recent_logins': recent_logins
                }
                
                return jsonify({
                    'success': True,
                    'stats': stats
                })
                
        except Exception as e:
            logger.error(f"Error getting user stats for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve user statistics'
            }), 500
    
    @bp.route('/api/platform_stats', methods=['GET'])
    @admin_api_required
    def get_platform_stats():
        """Get platform statistics for admin dashboard"""
        try:
            from flask import current_app
            session_manager = current_app.request_session_manager
            
            with session_manager.session_scope() as db_session:
                from models import PlatformConnection
                from sqlalchemy import func
                
                # Platform counts
                total_platforms = db_session.query(PlatformConnection).filter_by(is_active=True).count()
                
                # Platform types
                platform_types = db_session.query(
                    PlatformConnection.platform_type,
                    func.count(PlatformConnection.id).label('count')
                ).filter_by(is_active=True).group_by(PlatformConnection.platform_type).all()
                
                # Platforms by user
                platforms_per_user = db_session.query(
                    PlatformConnection.user_id,
                    func.count(PlatformConnection.id).label('count')
                ).filter_by(is_active=True).group_by(PlatformConnection.user_id).all()
                
                avg_platforms_per_user = sum(p.count for p in platforms_per_user) / len(platforms_per_user) if platforms_per_user else 0
                
                stats = {
                    'total_platforms': total_platforms,
                    'platform_types': {pt.platform_type: pt.count for pt in platform_types},
                    'avg_platforms_per_user': round(avg_platforms_per_user, 2)
                }
                
                return jsonify({
                    'success': True,
                    'stats': stats
                })
                
        except Exception as e:
            logger.error(f"Error getting platform stats for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve platform statistics'
            }), 500