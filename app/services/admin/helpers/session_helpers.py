# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from flask import Blueprint, request, current_app
from sqlalchemy import text, func, and_, or_, desc
from sqlalchemy.exc import SQLAlchemyError

from models import User, UserSession
from app.core.database.core.database_manager import DatabaseManager

# Configure logging
logger = logging.getLogger(__name__)


class SessionHelper:
    """Helper class for session monitoring operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_session_statistics(self, time_range: str = '24h') -> Dict[str, Any]:
        """Get session statistics for the specified time range"""
        try:
            # Calculate time range
            now = datetime.utcnow()
            if time_range == '1h':
                start_time = now - timedelta(hours=1)
            elif time_range == '24h':
                start_time = now - timedelta(hours=24)
            elif time_range == '7d':
                start_time = now - timedelta(days=7)
            elif time_range == '30d':
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(hours=24)
            
            # Get database session counts
            db_sessions = UserSession.query.filter(UserSession.created_at >= start_time).count()
            
            # Get active sessions (last 30 minutes)
            active_threshold = now - timedelta(minutes=30)
            active_db_sessions = UserSession.query.filter(UserSession.last_activity >= active_threshold).count()
            
            # Get unique users
            unique_users = UserSession.query.filter(UserSession.created_at >= start_time).distinct(UserSession.user_id).count()
            
            # Get error sessions (those with error status or expired)
            error_sessions = UserSession.query.filter(
                and_(UserSession.created_at >= start_time, 
                     or_(UserSession.status == 'error', 
                         UserSession.expires_at < now))
            ).count()
            
            # Calculate expired sessions
            expired_sessions = UserSession.query.filter(
                UserSession.expires_at < now
            ).count()
            
            return {
                'total_sessions': db_sessions,
                'active_sessions': active_db_sessions,
                'expired_sessions': expired_sessions,
                'database_sessions': db_sessions,
                'platform_sessions': 0,  # No platform sessions in current model
                'unique_users': unique_users,
                'error_sessions': error_sessions,
                'session_manager_type': 'database',  # Using database session manager
                'time_range': time_range,
                'timestamp': now.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error calculating session statistics: {str(e)}")
            return {
                'total_sessions': 0,
                'active_sessions': 0,
                'expired_sessions': 0,
                'database_sessions': 0,
                'platform_sessions': 0,
                'unique_users': 0,
                'error_sessions': 0,
                'session_manager_type': 'database',
                'time_range': time_range,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_filtered_sessions(self, page: int = 1, per_page: int = 20, 
                             status: str = 'all', user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get filtered sessions with pagination"""
        try:
            # Build query
            query = UserSession.query
            
            # Apply filters
            if status != 'all':
                query = query.filter(UserSession.status == status)
            
            if user_id:
                query = query.filter(UserSession.user_id == int(user_id))
            
            # Get total count
            total = query.count()
            
            # Get paginated results
            sessions = query.order_by(desc(UserSession.last_activity)).offset((page - 1) * per_page).limit(per_page).all()
            
            # Format results
            sessions_data = []
            for sess in sessions:
                user = User.query.get(sess.user_id) if sess.user_id else None
                sessions_data.append({
                    'id': sess.id,
                    'user_id': sess.user_id,
                    'username': user.username if user else 'Unknown',
                    'email': user.email if user else 'Unknown',
                    'session_data': sess.session_data,
                    'status': sess.status,
                    'created_at': sess.created_at.isoformat(),
                    'last_activity': sess.last_activity.isoformat(),
                    'expires_at': sess.expires_at.isoformat() if sess.expires_at else None,
                    'ip_address': sess.ip_address,
                    'user_agent': sess.user_agent
                })
            
            return {
                'sessions': sessions_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting filtered sessions: {str(e)}")
            return {
                'sessions': [],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': 0,
                    'pages': 0
                }
            }
    
    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed session information"""
        try:
            session_data = UserSession.query.filter(UserSession.id == session_id).first()
            
            if not session_data:
                return None
            
            user = User.query.get(session_data.user_id) if session_data.user_id else None
            
            return {
                'id': session_data.id,
                'user_id': session_data.user_id,
                'username': user.username if user else 'Unknown',
                'email': user.email if user else 'Unknown',
                'session_data': session_data.session_data,
                'status': session_data.status,
                'created_at': session_data.created_at.isoformat(),
                'last_activity': session_data.last_activity.isoformat(),
                'expires_at': session_data.expires_at.isoformat() if session_data.expires_at else None,
                'ip_address': session_data.ip_address,
                'user_agent': session_data.user_agent,
                'platform_sessions': []  # No platform sessions in current model
            }
        except Exception as e:
            self.logger.error(f"Error getting session details: {str(e)}")
            return None
    
    def terminate_session(self, session_id: str, reason: str, admin_id: int) -> bool:
        """Terminate a session"""
        try:
            session_data = UserSession.query.filter(UserSession.id == session_id).first()
            
            if not session_data:
                return False
            
            # Update session status
            session_data.status = 'terminated'
            session_data.session_data = session_data.session_data or {}
            session_data.session_data['termination_reason'] = reason
            session_data.session_data['terminated_by'] = admin_id
            session_data.session_data['terminated_at'] = datetime.utcnow().isoformat()
            
            DatabaseManager.get_instance().session.commit()
            
            # Log security event using logger
            self.logger.info(f'Session {session_id} terminated by admin {admin_id}: {reason}')
            
            return True
        except Exception as e:
            self.logger.error(f"Error terminating session: {str(e)}")
            DatabaseManager.get_instance().session.rollback()
            return False
    
    def get_session_analytics(self, start_date: Optional[str] = None, end_date: Optional[str] = None, 
                           metric_type: str = 'all') -> Dict[str, Any]:
        """Get session analytics data"""
        try:
            # Parse dates
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime.utcnow() - timedelta(days=7)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
            
            analytics = {}
            
            if metric_type in ['all', 'timeline']:
                # Get session timeline data
                timeline_data = db.session.query(
                    func.date(UserSession.created_at).label('date'),
                    func.count(UserSession.id).label('count')
                ).filter(
                    UserSession.created_at.between(start_dt, end_dt)
                ).group_by(func.date(UserSession.created_at)).all()
                
                analytics['timeline'] = [
                    {'date': str(item.date), 'count': item.count}
                    for item in timeline_data
                ]
            
            if metric_type in ['all', 'users']:
                # Get user activity data
                user_activity = db.session.query(
                    User.username,
                    func.count(UserSession.id).label('session_count')
                ).join(
                    UserSession, User.id == UserSession.user_id
                ).filter(
                    UserSession.created_at.between(start_dt, end_dt)
                ).group_by(User.username).order_by(desc('session_count')).limit(10).all()
                
                analytics['users'] = [
                    {'username': item.username, 'sessions': item.session_count}
                    for item in user_activity
                ]
            
            if metric_type in ['all', 'platforms']:
                # No platform sessions in current model
                analytics['platforms'] = []
            
            return analytics
        except Exception as e:
            self.logger.error(f"Error getting session analytics: {str(e)}")
            return {}
    
    def get_session_export_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None, 
                               session_type: str = 'all') -> List[Dict[str, Any]]:
        """Get session data for export"""
        try:
            # Parse dates
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime.utcnow() - timedelta(days=30)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
            
            # Build query
            query = UserSession.query.filter(UserSession.created_at.between(start_dt, end_dt))
            
            if session_type != 'all':
                query = query.filter(UserSession.status == session_type)
            
            sessions = query.all()
            
            export_data = []
            for sess in sessions:
                user = User.query.get(sess.user_id) if sess.user_id else None
                export_data.append({
                    'session_id': sess.id,
                    'user_id': sess.user_id,
                    'username': user.username if user else 'Unknown',
                    'email': user.email if user else 'Unknown',
                    'status': sess.status,
                    'created_at': sess.created_at.isoformat(),
                    'last_activity': sess.last_activity.isoformat(),
                    'expires_at': sess.expires_at.isoformat() if sess.expires_at else None,
                    'ip_address': sess.ip_address,
                    'user_agent': sess.user_agent
                })
            
            return export_data
        except Exception as e:
            self.logger.error(f"Error getting session export data: {str(e)}")
            return []
    
    def get_session_alerts(self) -> List[Dict[str, Any]]:
        """Get session alerts and warnings"""
        try:
            alerts = []
            now = datetime.utcnow()
            
            # Check for sessions with no activity for more than 24 hours
            inactive_threshold = now - timedelta(hours=24)
            inactive_sessions = UserSession.query.filter(
                UserSession.last_activity < inactive_threshold
            ).count()
            
            if inactive_sessions > 0:
                alerts.append({
                    'type': 'warning',
                    'message': f'{inactive_sessions} sessions inactive for more than 24 hours',
                    'severity': 'medium',
                    'timestamp': now.isoformat()
                })
            
            # Check for sessions with errors
            error_sessions = UserSession.query.filter(UserSession.status == 'error').count()
            if error_sessions > 0:
                alerts.append({
                    'type': 'error',
                    'message': f'{error_sessions} sessions with errors',
                    'severity': 'high',
                    'timestamp': now.isoformat()
                })
            
            # Check for high session count
            recent_sessions = UserSession.query.filter(
                UserSession.created_at >= now - timedelta(hours=1)
            ).count()
            
            if recent_sessions > 100:
                alerts.append({
                    'type': 'warning',
                    'message': f'High session activity: {recent_sessions} sessions in the last hour',
                    'severity': 'medium',
                    'timestamp': now.isoformat()
                })
            
            return alerts
        except Exception as e:
            self.logger.error(f"Error getting session alerts: {str(e)}")
            return []