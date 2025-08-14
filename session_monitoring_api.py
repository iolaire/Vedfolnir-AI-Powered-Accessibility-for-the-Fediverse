# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Monitoring API

Provides API endpoints for monitoring database session health, metrics, and performance.
"""

from logging import getLogger
from datetime import datetime, timezone
from flask import jsonify, request, current_app
from flask_login import login_required
from models import UserRole

logger = getLogger(__name__)

def create_session_monitoring_routes(app):
    """Create session monitoring API routes"""
    
    @app.route('/api/session/monitoring/health', methods=['GET'])
    @login_required
    def api_session_monitoring_health():
        """
        Get session monitoring health status
        
        Returns:
            JSON response with monitoring health information
        """
        try:
            monitor = getattr(current_app, 'session_monitor', None)
            if not monitor:
                return jsonify({
                    'success': False,
                    'error': 'Session monitor not available'
                }), 500
            
            health = monitor.get_monitoring_health()
            
            return jsonify({
                'success': True,
                'health': health,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in session monitoring health API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to get monitoring health'
            }), 500
    
    @app.route('/api/session/monitoring/metrics', methods=['GET'])
    @login_required
    def api_session_monitoring_metrics():
        """
        Get session metrics and statistics
        
        Returns:
            JSON response with session metrics
        """
        try:
            monitor = getattr(current_app, 'session_monitor', None)
            if not monitor:
                return jsonify({
                    'success': False,
                    'error': 'Session monitor not available'
                }), 500
            
            # Get database session metrics
            db_metrics = monitor.get_database_session_metrics()
            
            # Get performance stats
            performance_stats = monitor.get_session_performance_stats()
            
            return jsonify({
                'success': True,
                'database_metrics': db_metrics,
                'performance_stats': performance_stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in session monitoring metrics API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to get session metrics'
            }), 500
    
    @app.route('/api/session/monitoring/events', methods=['GET'])
    @login_required
    def api_session_monitoring_events():
        """
        Get recent session events
        
        Query parameters:
            limit: Number of events to return (default: 100, max: 500)
            event_type: Filter by event type (optional)
        
        Returns:
            JSON response with recent session events
        """
        try:
            monitor = getattr(current_app, 'session_monitor', None)
            if not monitor:
                return jsonify({
                    'success': False,
                    'error': 'Session monitor not available'
                }), 500
            
            # Get query parameters
            limit = min(int(request.args.get('limit', 100)), 500)
            event_type = request.args.get('event_type')
            
            # Get recent events
            events = monitor.get_recent_session_events(limit=limit, event_type=event_type)
            
            return jsonify({
                'success': True,
                'events': events,
                'count': len(events),
                'filters': {
                    'limit': limit,
                    'event_type': event_type
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in session monitoring events API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to get session events'
            }), 500
    
    @app.route('/api/session/monitoring/cleanup', methods=['POST'])
    @login_required
    def api_session_monitoring_cleanup():
        """
        Trigger session monitoring cleanup
        
        Requires admin role.
        
        Returns:
            JSON response with cleanup results
        """
        try:
            # Check if user is admin
            from flask_login import current_user
            if not current_user or current_user.role != UserRole.ADMIN:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            monitor = getattr(current_app, 'session_monitor', None)
            if not monitor:
                return jsonify({
                    'success': False,
                    'error': 'Session monitor not available'
                }), 500
            
            # Get cleanup parameters
            data = request.get_json() or {}
            max_age_hours = data.get('max_age_hours', 24)
            
            # Perform cleanup
            monitor.cleanup_old_metrics(max_age_hours=max_age_hours)
            
            return jsonify({
                'success': True,
                'message': f'Cleaned up metrics older than {max_age_hours} hours',
                'max_age_hours': max_age_hours,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in session monitoring cleanup API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to perform cleanup'
            }), 500
    
    @app.route('/api/session/monitoring/dashboard', methods=['GET'])
    @login_required
    def api_session_monitoring_dashboard():
        """
        Get comprehensive session monitoring dashboard data
        
        Returns:
            JSON response with dashboard data
        """
        try:
            monitor = getattr(current_app, 'session_monitor', None)
            if not monitor:
                return jsonify({
                    'success': False,
                    'error': 'Session monitor not available'
                }), 500
            
            # Get all monitoring data
            health = monitor.get_monitoring_health()
            db_metrics = monitor.get_database_session_metrics()
            performance_stats = monitor.get_session_performance_stats()
            recent_events = monitor.get_recent_session_events(limit=50)
            
            # Filter events by type for dashboard
            event_summary = {}
            for event in recent_events:
                event_type = event['event_type']
                if event_type not in event_summary:
                    event_summary[event_type] = 0
                event_summary[event_type] += 1
            
            return jsonify({
                'success': True,
                'dashboard': {
                    'health': health,
                    'database_metrics': db_metrics,
                    'performance_stats': performance_stats,
                    'recent_events_summary': event_summary,
                    'recent_events': recent_events[:10],  # Last 10 events for display
                    'session_type': 'database_only'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in session monitoring dashboard API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to get dashboard data'
            }), 500