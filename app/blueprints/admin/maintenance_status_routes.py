# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Status API Routes

Flask routes for maintenance status API endpoints providing real-time
maintenance status information via WebSocket connections.
"""

import logging
from flask import Blueprint, jsonify, request, current_app
from dataclasses import asdict
from typing import Optional, List

from app.services.maintenance.components.maintenance_status_api import MaintenanceStatusAPI
# SSE imports removed - using WebSocket instead

logger = logging.getLogger(__name__)

# Create blueprint for maintenance status routes
maintenance_status_bp = Blueprint('maintenance_status', __name__, url_prefix='/api/maintenance')


def get_maintenance_status_api() -> MaintenanceStatusAPI:
    """Get MaintenanceStatusAPI instance from Flask app context"""
    if not hasattr(current_app, 'maintenance_status_api'):
        raise RuntimeError("MaintenanceStatusAPI not initialized in Flask app")
    return current_app.maintenance_status_api


# SSE service functions removed - using WebSocket instead


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


# SSE stream endpoints removed - using WebSocket instead
# Real-time updates now handled by WebSocket connections


# SSE-related endpoints removed - using WebSocket instead


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
        
        # Test API functionality
        status_response = status_api.get_status()
        api_healthy = status_response.response_time_ms < 1000  # Under 1 second
        
        # WebSocket health is checked separately
        overall_healthy = api_healthy
        
        return jsonify({
            'success': True,
            'data': {
                'healthy': overall_healthy,
                'components': {
                    'status_api': {
                        'healthy': api_healthy,
                        'response_time_ms': status_response.response_time_ms
                    },
                    'websocket_service': {
                        'healthy': True,  # WebSocket health checked separately
                        'note': 'WebSocket connections managed by Flask-SocketIO'
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
    Initialize maintenance status API in Flask app
    
    Args:
        app: Flask application instance
        maintenance_service: EnhancedMaintenanceModeService instance
    """
    try:
        # Create API service
        status_api = MaintenanceStatusAPI(maintenance_service)
        
        # Store in app context
        app.maintenance_status_api = status_api
        
        # Register blueprint
        app.register_blueprint(maintenance_status_bp)
        
        logger.info("Maintenance status API initialized (WebSocket replaces SSE)")
        
        return status_api
        
    except Exception as e:
        logger.error(f"Error initializing maintenance status API: {str(e)}")
        raise