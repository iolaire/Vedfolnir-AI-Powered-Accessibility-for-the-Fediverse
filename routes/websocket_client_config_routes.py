# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Client Configuration Routes

Provides API endpoints for serving WebSocket client configuration based on
server environment settings, CORS configuration, and client environment detection.
"""

import logging
from flask import Blueprint, jsonify, request, current_app
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager

logger = logging.getLogger(__name__)

# Create blueprint for WebSocket client configuration routes
websocket_client_config_bp = Blueprint('websocket_client_config', __name__, url_prefix='/api/websocket')


@websocket_client_config_bp.route('/client-config', methods=['GET'])
def get_client_config():
    """
    Get WebSocket client configuration based on server settings
    
    Returns:
        JSON response with client configuration
    """
    try:
        # Get configuration managers from app context
        config_manager = getattr(current_app, 'websocket_config_manager', None)
        cors_manager = getattr(current_app, 'websocket_cors_manager', None)
        
        if not config_manager:
            logger.error("WebSocket configuration manager not available")
            return jsonify({
                'success': False,
                'error': 'WebSocket configuration not available',
                'fallback_config': _get_fallback_client_config()
            }), 500
        
        # Get client configuration from config manager
        client_config = config_manager.get_client_config()
        
        # Add CORS information if CORS manager is available
        if cors_manager:
            # Get dynamic origin for client
            try:
                dynamic_origin = cors_manager.get_dynamic_origin_for_client()
                client_config['url'] = dynamic_origin
            except Exception as e:
                logger.warning(f"Failed to get dynamic origin: {e}")
        
        # Add environment-specific adaptations
        client_config = _adapt_config_for_client_environment(client_config, request)
        
        # Add server capabilities
        client_config['server_capabilities'] = _get_server_capabilities()
        
        # Add configuration metadata
        client_config['config_version'] = '1.0.0'
        client_config['generated_at'] = _get_current_timestamp()
        
        logger.debug(f"Serving client configuration: {client_config}")
        
        return jsonify({
            'success': True,
            'config': client_config
        })
        
    except Exception as e:
        logger.error(f"Error serving client configuration: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'fallback_config': _get_fallback_client_config()
        }), 500


@websocket_client_config_bp.route('/server-info', methods=['GET'])
def get_server_info():
    """
    Get WebSocket server information and capabilities
    
    Returns:
        JSON response with server information
    """
    try:
        config_manager = getattr(current_app, 'websocket_config_manager', None)
        cors_manager = getattr(current_app, 'websocket_cors_manager', None)
        
        server_info = {
            'server_capabilities': _get_server_capabilities(),
            'supported_transports': ['websocket', 'polling'],
            'supported_namespaces': ['/', '/admin'],
            'cors_enabled': cors_manager is not None,
            'config_available': config_manager is not None
        }
        
        # Add configuration summary if available
        if config_manager:
            try:
                config_summary = config_manager.get_configuration_summary()
                server_info['configuration_summary'] = config_summary
            except Exception as e:
                logger.warning(f"Failed to get configuration summary: {e}")
        
        # Add CORS debug info if available and in development
        if cors_manager and _is_development_environment():
            try:
                cors_debug = cors_manager.get_cors_debug_info()
                server_info['cors_debug'] = cors_debug
            except Exception as e:
                logger.warning(f"Failed to get CORS debug info: {e}")
        
        return jsonify({
            'success': True,
            'server_info': server_info
        })
        
    except Exception as e:
        logger.error(f"Error serving server info: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@websocket_client_config_bp.route('/validate-origin', methods=['POST'])
def validate_origin():
    """
    Validate if an origin is allowed for WebSocket connections
    
    Returns:
        JSON response with validation result
    """
    try:
        data = request.get_json()
        if not data or 'origin' not in data:
            return jsonify({
                'success': False,
                'error': 'Origin parameter required'
            }), 400
        
        origin = data['origin']
        namespace = data.get('namespace', '/')
        
        cors_manager = getattr(current_app, 'websocket_cors_manager', None)
        if not cors_manager:
            return jsonify({
                'success': False,
                'error': 'CORS manager not available'
            }), 500
        
        # Validate origin
        is_valid, error_message = cors_manager.validate_websocket_origin(origin, namespace)
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'message': error_message,
            'origin': origin,
            'namespace': namespace
        })
        
    except Exception as e:
        logger.error(f"Error validating origin: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@websocket_client_config_bp.route('/connection-test', methods=['GET'])
def connection_test():
    """
    Test WebSocket connection availability
    
    Returns:
        JSON response with connection test results
    """
    try:
        # Basic connectivity test
        test_results = {
            'server_reachable': True,
            'timestamp': _get_current_timestamp(),
            'client_ip': _get_client_ip(request),
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'protocol': request.scheme,
            'host': request.headers.get('Host', 'Unknown')
        }
        
        # Test CORS configuration
        cors_manager = getattr(current_app, 'websocket_cors_manager', None)
        if cors_manager:
            origin = request.headers.get('Origin')
            if origin:
                is_valid, message = cors_manager.validate_websocket_origin(origin)
                test_results['cors_test'] = {
                    'origin': origin,
                    'valid': is_valid,
                    'message': message
                }
            else:
                test_results['cors_test'] = {
                    'origin': None,
                    'valid': True,
                    'message': 'No origin header (same-origin request)'
                }
        
        # Test configuration availability
        config_manager = getattr(current_app, 'websocket_config_manager', None)
        if config_manager:
            test_results['config_test'] = {
                'available': True,
                'valid': config_manager.validate_configuration()
            }
        else:
            test_results['config_test'] = {
                'available': False,
                'valid': False
            }
        
        return jsonify({
            'success': True,
            'test_results': test_results
        })
        
    except Exception as e:
        logger.error(f"Error in connection test: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _adapt_config_for_client_environment(config, request):
    """
    Adapt configuration based on client environment detection
    
    Args:
        config: Base client configuration
        request: Flask request object
        
    Returns:
        Adapted configuration
    """
    adapted_config = config.copy()
    
    # Detect mobile clients
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(mobile in user_agent for mobile in [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'
    ])
    
    if is_mobile:
        # Mobile adaptations
        adapted_config['timeout'] = max(adapted_config.get('timeout', 20000), 30000)
        adapted_config['reconnectionDelay'] = max(adapted_config.get('reconnectionDelay', 1000), 2000)
        adapted_config['pingInterval'] = 30000
        adapted_config['pingTimeout'] = 60000
    
    # Detect development environment
    if _is_development_environment():
        adapted_config['reconnectionAttempts'] = max(adapted_config.get('reconnectionAttempts', 5), 10)
        adapted_config['forceNew'] = True
    
    # Protocol-specific adaptations
    if request.scheme == 'https':
        adapted_config['secure'] = True
    
    return adapted_config


def _get_server_capabilities():
    """
    Get server capabilities information
    
    Returns:
        Dictionary of server capabilities
    """
    return {
        'namespaces': ['/', '/admin'],
        'transports': ['websocket', 'polling'],
        'features': [
            'reconnection',
            'rooms',
            'authentication',
            'cors',
            'error_handling',
            'metrics'
        ],
        'events': [
            'connect',
            'disconnect',
            'error',
            'ping',
            'pong',
            'join_room',
            'leave_room'
        ]
    }


def _get_fallback_client_config():
    """
    Get fallback client configuration when server config is unavailable
    
    Returns:
        Fallback configuration dictionary
    """
    return {
        'url': f"{request.scheme}://{request.headers.get('Host', 'localhost:5000')}",
        'transports': ['websocket', 'polling'],
        'reconnection': True,
        'reconnectionAttempts': 5,
        'reconnectionDelay': 1000,
        'reconnectionDelayMax': 5000,
        'timeout': 20000,
        'upgrade': True,
        'rememberUpgrade': True,
        'forceNew': False
    }


def _is_development_environment():
    """
    Check if running in development environment
    
    Returns:
        True if in development environment
    """
    import os
    flask_env = os.getenv('FLASK_ENV', 'production').lower()
    return flask_env in ['development', 'dev'] or request.headers.get('Host', '').startswith('localhost')


def _get_client_ip(request):
    """
    Get client IP address from request
    
    Args:
        request: Flask request object
        
    Returns:
        Client IP address string
    """
    # Check for forwarded headers first (reverse proxy)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    
    forwarded = request.headers.get('X-Forwarded')
    if forwarded:
        return forwarded.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    # Fallback to remote address
    return request.remote_addr or 'Unknown'


def _get_current_timestamp():
    """
    Get current timestamp in ISO format
    
    Returns:
        ISO format timestamp string
    """
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'


# Error handlers for the blueprint
@websocket_client_config_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors for WebSocket config routes"""
    return jsonify({
        'success': False,
        'error': 'WebSocket configuration endpoint not found'
    }), 404


@websocket_client_config_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors for WebSocket config routes"""
    logger.error(f"Internal error in WebSocket config route: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error in WebSocket configuration'
    }), 500