# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Status API Routes

Flask routes for maintenance status API endpoints providing real-time
maintenance status information and Server-Sent Events streaming.
"""

import logging
from flask import Blueprint, jsonify, request, current_app
from dataclasses import asdict
from typing import Optional, List

from maintenance_status_api import MaintenanceStatusAPI
from maintenance_status_sse import MaintenanceStatusSSE, create_flask_sse_response

logger = logging.getLogger(__name__)

# Create blueprint for maintenance status routes
maintenance_status_bp = Blueprint('maintenance_status', __name__, url_prefix='/api/maintenance')


def get_maintenance_status_api() -> MaintenanceStatusAPI:
    """Get MaintenanceStatusAPI instance from Flask app context"""
    if not hasattr(current_app, 'maintenance_status_api'):
        raise RuntimeError("MaintenanceStatusAPI not initialized in Flask app")
    return current_app.maintenance_status_api


def get_maintenance_status_sse() -> MaintenanceStatusSSE:
    """Get MaintenanceStatusSSE instance from Flask app context"""
    if not hasattr(current_app, 'maintenance_status_sse'):
        raise RuntimeError("MaintenanceStatusSSE not initialized in Flask app")
    return current_app.maintenance_status_sse


@maintenance_status_bp.route('/status', methods=['GET'])
def get_maintenance_status():
    """
    Get comprehensive maintenance status
    
    Returns:
        JSON response with maintenance status information
    """
    try:
        status_api = get_maintenance_status_api()
        status_response = status_api.get_status()
        
        # Convert to dict for JSON response
        status_dict = asdict(status_response)
        
        logger.debug(f"Maintenance status API request completed in {status_response.response_time_ms:.2f}ms")
        
        return jsonify({
            'success': True,
            'data': status_dict
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting maintenance status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to retrieve maintenance status',
            'message': str(e)
        }), 500


@maintenance_status_bp.route('/blocked-operations', methods=['GET'])
def get_blocked_operations():
    """
    Get detailed information about blocked operations
    
    Returns:
        JSON response with blocked operations list
    """
    try:
        status_api = get_maintenance_status_api()
        blocked_operations = status_api.get_blocked_operations()
        
        # Convert blocked operations to dict format
        blocked_ops_data = [asdict(op) for op in blocked_operations]
        
        return jsonify({
            'success': True,
            'data': {
                'blocked_operations': blocked_ops_data,
                'count': len(blocked_ops_data)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting blocked operations: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to retrieve blocked operations',
            'message': str(e)
        }), 500


@maintenance_status_bp.route('/message', methods=['GET'])
def get_maintenance_message():
    """
    Get operation-specific maintenance message
    
    Query Parameters:
        operation (optional): Specific operation being blocked
    
    Returns:
        JSON response with maintenance message
    """
    try:
        status_api = get_maintenance_status_api()
        operation = request.args.get('operation')
        
        message = status_api.get_maintenance_message(operation)
        
        return jsonify({
            'success': True,
            'data': {
                'message': message,
                'operation': operation
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting maintenance message: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to retrieve maintenance message',
            'message': str(e)
        }), 500


@maintenance_status_bp.route('/stream', methods=['GET'])
def maintenance_status_stream():
    """
    Server-Sent Events stream for real-time maintenance status updates
    
    Query Parameters:
        client_id (optional): Unique client identifier
        events (optional): Comma-separated list of event types to subscribe to
    
    Returns:
        SSE stream response
    """
    try:
        sse_service = get_maintenance_status_sse()
        
        # Get query parameters
        client_id = request.args.get('client_id')
        events_param = request.args.get('events')
        
        # Parse event types
        event_types = None
        if events_param:
            event_types = [event.strip() for event in events_param.split(',') if event.strip()]
        
        # Create SSE response
        response = create_flask_sse_response(sse_service, client_id, event_types)
        
        logger.info(f"Started SSE stream for client {client_id or 'anonymous'} with events {event_types or 'all'}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating SSE stream: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to create status stream',
            'message': str(e)
        }), 500


@maintenance_status_bp.route('/stream/stats', methods=['GET'])
def get_stream_stats():
    """
    Get SSE stream statistics
    
    Returns:
        JSON response with SSE statistics
    """
    try:
        sse_service = get_maintenance_status_sse()
        stats = sse_service.get_sse_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting SSE stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to retrieve stream statistics',
            'message': str(e)
        }), 500


@maintenance_status_bp.route('/stream/clients/<client_id>', methods=['GET'])
def get_client_info(client_id: str):
    """
    Get information about a specific SSE client
    
    Args:
        client_id: Client identifier
    
    Returns:
        JSON response with client information
    """
    try:
        sse_service = get_maintenance_status_sse()
        client_info = sse_service.get_client_info(client_id)
        
        if client_info is None:
            return jsonify({
                'success': False,
                'error': 'Client not found',
                'message': f'No client found with ID: {client_id}'
            }), 404
        
        # Convert datetime objects to ISO format for JSON serialization
        if 'connected_at' in client_info:
            client_info['connected_at'] = client_info['connected_at'].isoformat()
        if 'last_activity' in client_info:
            client_info['last_activity'] = client_info['last_activity'].isoformat()
        
        return jsonify({
            'success': True,
            'data': client_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting client info for {client_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to retrieve client information',
            'message': str(e)
        }), 500


@maintenance_status_bp.route('/stream/clients/<client_id>', methods=['DELETE'])
def disconnect_client(client_id: str):
    """
    Disconnect a specific SSE client
    
    Args:
        client_id: Client identifier
    
    Returns:
        JSON response confirming disconnection
    """
    try:
        sse_service = get_maintenance_status_sse()
        result = sse_service.disconnect_client(client_id)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Client not found',
                'message': f'No active client found with ID: {client_id}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'message': f'Client {client_id} disconnected successfully',
                'client_id': client_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error disconnecting client {client_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to disconnect client',
            'message': str(e)
        }), 500


@maintenance_status_bp.route('/api-stats', methods=['GET'])
def get_api_stats():
    """
    Get maintenance status API statistics
    
    Returns:
        JSON response with API performance statistics
    """
    try:
        status_api = get_maintenance_status_api()
        stats = status_api.get_api_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting API stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to retrieve API statistics',
            'message': str(e)
        }), 500


@maintenance_status_bp.route('/health', methods=['GET'])
def maintenance_api_health():
    """
    Health check endpoint for maintenance status API
    
    Returns:
        JSON response with health status
    """
    try:
        status_api = get_maintenance_status_api()
        sse_service = get_maintenance_status_sse()
        
        # Test API functionality
        status_response = status_api.get_status()
        api_healthy = status_response.response_time_ms < 1000  # Under 1 second
        
        # Test SSE functionality
        sse_stats = sse_service.get_sse_stats()
        sse_healthy = sse_stats['service_stats']['connection_errors'] < 10  # Less than 10 errors
        
        overall_healthy = api_healthy and sse_healthy
        
        return jsonify({
            'success': True,
            'data': {
                'healthy': overall_healthy,
                'components': {
                    'status_api': {
                        'healthy': api_healthy,
                        'response_time_ms': status_response.response_time_ms
                    },
                    'sse_service': {
                        'healthy': sse_healthy,
                        'active_connections': sse_stats['client_stats']['active_clients'],
                        'connection_errors': sse_stats['service_stats']['connection_errors']
                    }
                },
                'timestamp': status_response.timestamp
            }
        }), 200 if overall_healthy else 503
        
    except Exception as e:
        logger.error(f"Error in maintenance API health check: {str(e)}")
        return jsonify({
            'success': False,
            'healthy': False,
            'error': 'Health check failed',
            'message': str(e)
        }), 503


# Error handlers for the blueprint
@maintenance_status_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': 'The requested maintenance status API endpoint was not found'
    }), 404


@maintenance_status_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        'success': False,
        'error': 'Method not allowed',
        'message': 'The HTTP method is not allowed for this endpoint'
    }), 405


@maintenance_status_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error in maintenance status API: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred in the maintenance status API'
    }), 500


def init_maintenance_status_api(app, maintenance_service):
    """
    Initialize maintenance status API and SSE service in Flask app
    
    Args:
        app: Flask application instance
        maintenance_service: EnhancedMaintenanceModeService instance
    """
    try:
        # Create API and SSE services
        status_api = MaintenanceStatusAPI(maintenance_service)
        sse_service = MaintenanceStatusSSE(status_api)
        
        # Store in app context
        app.maintenance_status_api = status_api
        app.maintenance_status_sse = sse_service
        
        # Register blueprint
        app.register_blueprint(maintenance_status_bp)
        
        logger.info("Maintenance status API and SSE service initialized")
        
        # Register cleanup on app teardown
        @app.teardown_appcontext
        def cleanup_maintenance_services(error):
            if hasattr(app, 'maintenance_status_sse'):
                try:
                    app.maintenance_status_sse.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down SSE service: {str(e)}")
        
        return status_api, sse_service
        
    except Exception as e:
        logger.error(f"Error initializing maintenance status API: {str(e)}")
        raise