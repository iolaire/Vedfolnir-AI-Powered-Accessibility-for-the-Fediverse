# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session State API

This module provides API endpoints for cross-tab session synchronization
using database sessions as the single source of truth.
"""

from logging import getLogger
from datetime import datetime, timezone
from flask import jsonify, request, g, make_response
# Removed Flask-WTF CSRF import - using custom CSRF system
from redis_session_middleware import get_current_session_id, validate_current_session as is_session_authenticated

logger = getLogger(__name__)

def create_session_state_routes(app):
    """Create session state API routes"""
    # Note: Session endpoints are exempt from custom CSRF protection in middleware
    
    @app.route('/api/session/state', methods=['GET', 'OPTIONS'])
    def api_session_state():
        """
        Get current session state for cross-tab synchronization
        
        Returns:
            JSON response with session state information
        """
        # Handle CORS preflight request
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With'
            response.headers['Access-Control-Max-Age'] = '86400'
            return response
            
        try:
            # Get current session information using direct session access
            from flask import session
            session_id = get_current_session_id()
            
            if not session or not is_session_authenticated():
                response = jsonify({
                    'success': True,
                    'authenticated': False,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                # Add CORS headers
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With'
                return response
            
            # Return session state for cross-tab sync using direct session access
            response_data = {
                'success': True,
                'authenticated': True,
                'session_id': session_id,
                'user': {
                    'id': session.get('user_id'),
                    'username': session.get('username')
                },
                'platform': {
                    'id': session.get('platform_connection_id'),
                    'name': session.get('platform_name')
                },
                'created_at': session.get('created_at'),
                'last_activity': session.get('last_activity'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Session state API called for user {session.get('user_id')}")
            response = jsonify(response_data)
            # Add CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With'
            return response
            
        except Exception as e:
            logger.error(f"Error in session state API: {e}")
            response = jsonify({
                'success': False,
                'error': 'Failed to get session state',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            # Add CORS headers even for error responses
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With'
            return response, 500
    
    @app.route('/api/session/validate', methods=['POST'])
    def api_session_validate():
        """
        Validate current session
        
        Returns:
            JSON response with validation result
        """
        try:
            session_id = get_current_session_id()
            
            if not session_id:
                return jsonify({
                    'success': True,
                    'valid': False,
                    'reason': 'no_session',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            # Validate session using unified session manager
            unified_session_manager = getattr(g, 'session_manager', None)
            if not unified_session_manager:
                # Get from app context
                from flask import current_app
                unified_session_manager = getattr(current_app, 'unified_session_manager', None)
            
            if unified_session_manager:
                is_valid = unified_session_manager.validate_session(session_id)
                return jsonify({
                    'success': True,
                    'valid': is_valid,
                    'session_id': session_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Session manager not available',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }), 500
                
        except Exception as e:
            logger.error(f"Error in session validation API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to validate session',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }), 500
    
    @app.route('/api/session/heartbeat', methods=['POST'])
    def api_session_heartbeat():
        """
        Session heartbeat to keep session active
        
        Returns:
            JSON response with heartbeat result
        """
        try:
            from flask import session
            session_id = get_current_session_id()
            
            if not session or not session_id:
                return jsonify({
                    'success': True,
                    'active': False,
                    'reason': 'no_session',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            # Session activity is automatically updated by middleware
            # Just return current state
            return jsonify({
                'success': True,
                'active': True,
                'session_id': session_id,
                'user_id': session.get('user_id'),
                'platform_id': session.get('platform_connection_id'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in session heartbeat API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to process heartbeat',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }), 500
    
    # Session endpoints are exempt from CSRF protection in custom middleware
    # No Flask-WTF CSRF exemptions needed since we disabled Flask-WTF CSRF
  
    @app.route('/api/session/state/metrics', methods=['GET'])
    def api_session_state_metrics():
        """
        Get session monitoring metrics
        
        Returns:
            JSON response with session metrics
        """
        try:
            # Get session monitor from app
            session_monitor = getattr(app, 'session_monitor', None)
            if not session_monitor:
                # Try to get from unified session manager
                unified_session_manager = getattr(app, 'unified_session_manager', None)
                if unified_session_manager:
                    session_monitor = getattr(unified_session_manager, 'monitor', None)
            
            if not session_monitor:
                return jsonify({
                    'success': False,
                    'error': 'Session monitoring not available',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }), 503
            
            # Get metrics
            metrics = session_monitor.get_database_session_metrics()
            health_status = session_monitor.get_database_session_health_status()
            
            return jsonify({
                'success': True,
                'metrics': metrics,
                'health_status': health_status,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in session monitoring metrics API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to get session metrics',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }), 500
    
    @app.route('/api/session/monitoring/report', methods=['GET'])
    def api_session_monitoring_report():
        """
        Get session monitoring report
        
        Returns:
            JSON response with session report
        """
        try:
            # Get hours parameter
            hours = request.args.get('hours', 24, type=int)
            hours = max(1, min(hours, 168))  # Limit to 1-168 hours (1 week)
            
            # Get session monitor
            session_monitor = getattr(app, 'session_monitor', None)
            if not session_monitor:
                unified_session_manager = getattr(app, 'unified_session_manager', None)
                if unified_session_manager:
                    session_monitor = getattr(unified_session_manager, 'monitor', None)
            
            if not session_monitor:
                return jsonify({
                    'success': False,
                    'error': 'Session monitoring not available',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }), 503
            
            # Generate report
            report = session_monitor.generate_database_session_report(hours)
            
            return jsonify({
                'success': True,
                'report': report,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in session monitoring report API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to generate session report',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }), 500
    
    @app.route('/api/maintenance/status', methods=['GET', 'OPTIONS'])
    def api_maintenance_status():
        """
        Get current maintenance mode status
        
        Returns:
            JSON response with maintenance status information
        """
        # Handle CORS preflight request
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With'
            response.headers['Access-Control-Max-Age'] = '86400'
            return response
            
        try:
            # Import maintenance status function
            from maintenance_mode_decorators import maintenance_status_info
            
            # Get maintenance status
            status_info = maintenance_status_info()
            
            response_data = {
                'success': True,
                'maintenance_mode': status_info.get('maintenance_mode', False),
                'maintenance_reason': status_info.get('maintenance_reason'),
                'maintenance_status': status_info.get('maintenance_status', 'inactive'),
                'last_updated': status_info.get('last_updated'),
                'service_available': status_info.get('service_available', False),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Maintenance status API called: {status_info.get('maintenance_mode', False)}")
            response = jsonify(response_data)
            
            # Add CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With'
            return response
            
        except Exception as e:
            logger.error(f"Error in maintenance status API: {e}")
            response = jsonify({
                'success': False,
                'error': 'Failed to get maintenance status',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            # Add CORS headers even for error responses
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With'
            return response, 500
    
    @app.route('/api/maintenance/refresh', methods=['GET'])
    def api_maintenance_refresh():
        """
        Manually refresh maintenance service cache (for testing)
        
        Returns:
            JSON response with refresh result
        """
        try:
            maintenance_service = getattr(app, 'maintenance_service', None)
            if not maintenance_service:
                return jsonify({
                    'success': False,
                    'error': 'Maintenance service not available',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }), 503
            
            # Refresh the cache
            refresh_success = maintenance_service.refresh_status()
            
            # Get updated status
            from maintenance_mode_decorators import maintenance_status_info
            status_info = maintenance_status_info()
            
            return jsonify({
                'success': True,
                'refresh_successful': refresh_success,
                'updated_status': {
                    'maintenance_mode': status_info.get('maintenance_mode', False),
                    'maintenance_reason': status_info.get('maintenance_reason'),
                    'maintenance_status': status_info.get('maintenance_status', 'inactive'),
                    'last_updated': status_info.get('last_updated'),
                    'service_available': status_info.get('service_available', False)
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in maintenance refresh API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to refresh maintenance status',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }), 500