# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Page Notification Routes

Flask routes for managing page notification integration, including registration,
initialization, configuration, and status endpoints.
"""

import logging
from flask import Blueprint, request, jsonify, session, current_app
from typing import Dict, Any, Optional

from app.services.notification.integration.page_notification_integrator import PageNotificationIntegrator, PageType, PageNotificationConfig
# Import security components if available, otherwise use mocks
try:
    from app.core.security.validation.input_validator import InputValidator
    from app.core.security.core.security_decorators import require_csrf_token, rate_limit
except ImportError:
    # Mock security components for testing
    class InputValidator:
        def validate_identifier(self, value):
            return isinstance(value, str) and len(value) > 0 and len(value) < 100
    
    def require_csrf_token(func):
        return func
    
    def rate_limit(limit=None, window=None):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)

# Create blueprint
page_notification_bp = Blueprint('page_notifications', __name__, url_prefix='/api/notifications/page')

# Input validator
input_validator = InputValidator()


@page_notification_bp.route('/register', methods=['POST'])
@require_csrf_token
@rate_limit(limit=10, window=60)  # 10 requests per minute
def register_page_integration():
    """
    Register a page for notification integration
    
    Expected JSON payload:
    {
        "page_id": "unique-page-identifier",
        "page_type": "user_dashboard|caption_processing|admin_dashboard|...",
        "config": {  // Optional custom configuration
            "enabled_types": ["system", "caption", "platform"],
            "auto_hide": true,
            "max_notifications": 5,
            "position": "top-right",
            "show_progress": false
        }
    }
    
    Returns:
        JSON response with integration configuration
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        page_id = data.get('page_id')
        page_type_str = data.get('page_type')
        
        if not page_id or not page_type_str:
            return jsonify({'error': 'page_id and page_type are required'}), 400
        
        # Validate page_id format
        if not input_validator.validate_identifier(page_id):
            return jsonify({'error': 'Invalid page_id format'}), 400
        
        # Validate page_type
        try:
            page_type = PageType(page_type_str)
        except ValueError:
            valid_types = [pt.value for pt in PageType]
            return jsonify({
                'error': f'Invalid page_type. Valid types: {valid_types}'
            }), 400
        
        # Get page integrator from app context
        page_integrator = current_app.page_notification_integrator
        if not page_integrator:
            return jsonify({'error': 'Page notification system not available'}), 503
        
        # Parse custom configuration if provided
        custom_config = None
        if 'config' in data:
            custom_config = _parse_page_config(data['config'], page_type)
        
        # Register page integration
        client_config = page_integrator.register_page_integration(
            page_id, page_type, custom_config
        )
        
        logger.info(f"Registered page integration: {page_id} ({page_type.value})")
        
        return jsonify({
            'success': True,
            'page_id': page_id,
            'page_type': page_type.value,
            'config': client_config
        })
        
    except PermissionError as e:
        logger.warning(f"Permission denied for page integration: {e}")
        return jsonify({'error': 'Insufficient permissions for page type'}), 403
        
    except Exception as e:
        logger.error(f"Failed to register page integration: {e}")
        return jsonify({'error': 'Failed to register page integration'}), 500


@page_notification_bp.route('/initialize', methods=['POST'])
@require_csrf_token
@rate_limit(limit=20, window=60)  # 20 requests per minute
def initialize_page_notifications():
    """
    Initialize notifications for a registered page
    
    Expected JSON payload:
    {
        "page_id": "unique-page-identifier"
    }
    
    Returns:
        JSON response with initialization configuration
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        page_id = data.get('page_id')
        if not page_id:
            return jsonify({'error': 'page_id is required'}), 400
        
        # Validate page_id format
        if not input_validator.validate_identifier(page_id):
            return jsonify({'error': 'Invalid page_id format'}), 400
        
        # Get page integrator from app context
        page_integrator = current_app.page_notification_integrator
        if not page_integrator:
            return jsonify({'error': 'Page notification system not available'}), 503
        
        # Initialize page notifications
        initialization_result = page_integrator.initialize_page_notifications(page_id)
        
        logger.info(f"Initialized page notifications: {page_id}")
        
        return jsonify({
            'success': True,
            **initialization_result
        })
        
    except ValueError as e:
        logger.warning(f"Invalid page initialization request: {e}")
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        logger.error(f"Failed to initialize page notifications: {e}")
        return jsonify({'error': 'Failed to initialize page notifications'}), 500


@page_notification_bp.route('/websocket-config', methods=['POST'])
@require_csrf_token
@rate_limit(limit=15, window=60)  # 15 requests per minute
def get_websocket_config():
    """
    Get WebSocket connection configuration for a page
    
    Expected JSON payload:
    {
        "page_id": "unique-page-identifier"
    }
    
    Returns:
        JSON response with WebSocket configuration
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        page_id = data.get('page_id')
        if not page_id:
            return jsonify({'error': 'page_id is required'}), 400
        
        # Validate page_id format
        if not input_validator.validate_identifier(page_id):
            return jsonify({'error': 'Invalid page_id format'}), 400
        
        # Get page integrator from app context
        page_integrator = current_app.page_notification_integrator
        if not page_integrator:
            return jsonify({'error': 'Page notification system not available'}), 503
        
        # Setup WebSocket connection configuration
        websocket_config = page_integrator.setup_websocket_connection(page_id)
        
        logger.debug(f"Generated WebSocket config for page: {page_id}")
        
        return jsonify({
            'success': True,
            'page_id': page_id,
            'websocket_config': websocket_config
        })
        
    except ValueError as e:
        logger.warning(f"Invalid WebSocket config request: {e}")
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        logger.error(f"Failed to get WebSocket config: {e}")
        return jsonify({'error': 'Failed to get WebSocket configuration'}), 500


@page_notification_bp.route('/event-handlers', methods=['POST'])
@require_csrf_token
@rate_limit(limit=15, window=60)  # 15 requests per minute
def get_event_handlers():
    """
    Get event handler configuration for a page
    
    Expected JSON payload:
    {
        "page_id": "unique-page-identifier",
        "custom_handlers": {  // Optional custom handlers
            "event_name": "handler_function_name"
        }
    }
    
    Returns:
        JSON response with event handler configuration
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        page_id = data.get('page_id')
        if not page_id:
            return jsonify({'error': 'page_id is required'}), 400
        
        # Validate page_id format
        if not input_validator.validate_identifier(page_id):
            return jsonify({'error': 'Invalid page_id format'}), 400
        
        # Get custom handlers if provided
        custom_handlers = data.get('custom_handlers')
        if custom_handlers and not isinstance(custom_handlers, dict):
            return jsonify({'error': 'custom_handlers must be a dictionary'}), 400
        
        # Get page integrator from app context
        page_integrator = current_app.page_notification_integrator
        if not page_integrator:
            return jsonify({'error': 'Page notification system not available'}), 503
        
        # Register event handlers
        handler_config = page_integrator.register_event_handlers(page_id, custom_handlers)
        
        logger.debug(f"Generated event handler config for page: {page_id}")
        
        return jsonify({
            'success': True,
            'page_id': page_id,
            'handler_config': handler_config
        })
        
    except ValueError as e:
        logger.warning(f"Invalid event handler request: {e}")
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        logger.error(f"Failed to get event handlers: {e}")
        return jsonify({'error': 'Failed to get event handler configuration'}), 500


@page_notification_bp.route('/status/<page_id>', methods=['GET'])
@rate_limit(limit=30, window=60)  # 30 requests per minute
def get_page_status(page_id: str):
    """
    Get status of page integration
    
    Args:
        page_id: Page identifier
        
    Returns:
        JSON response with integration status
    """
    try:
        # Validate page_id format
        if not input_validator.validate_identifier(page_id):
            return jsonify({'error': 'Invalid page_id format'}), 400
        
        # Get page integrator from app context
        page_integrator = current_app.page_notification_integrator
        if not page_integrator:
            return jsonify({'error': 'Page notification system not available'}), 503
        
        # Get integration status
        status = page_integrator.get_page_integration_status(page_id)
        
        return jsonify({
            'success': True,
            **status
        })
        
    except Exception as e:
        logger.error(f"Failed to get page status: {e}")
        return jsonify({'error': 'Failed to get page status'}), 500


@page_notification_bp.route('/cleanup', methods=['POST'])
@require_csrf_token
@rate_limit(limit=10, window=60)  # 10 requests per minute
def cleanup_page_integration():
    """
    Clean up page integration
    
    Expected JSON payload:
    {
        "page_id": "unique-page-identifier"
    }
    
    Returns:
        JSON response with cleanup status
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        page_id = data.get('page_id')
        if not page_id:
            return jsonify({'error': 'page_id is required'}), 400
        
        # Validate page_id format
        if not input_validator.validate_identifier(page_id):
            return jsonify({'error': 'Invalid page_id format'}), 400
        
        # Get page integrator from app context
        page_integrator = current_app.page_notification_integrator
        if not page_integrator:
            return jsonify({'error': 'Page notification system not available'}), 503
        
        # Cleanup page integration
        success = page_integrator.cleanup_page_integration(page_id)
        
        if success:
            logger.info(f"Cleaned up page integration: {page_id}")
            return jsonify({
                'success': True,
                'page_id': page_id,
                'message': 'Page integration cleaned up successfully'
            })
        else:
            return jsonify({
                'success': False,
                'page_id': page_id,
                'error': 'Failed to cleanup page integration'
            }), 500
        
    except Exception as e:
        logger.error(f"Failed to cleanup page integration: {e}")
        return jsonify({'error': 'Failed to cleanup page integration'}), 500


@page_notification_bp.route('/stats', methods=['GET'])
@rate_limit(limit=20, window=60)  # 20 requests per minute
def get_integration_stats():
    """
    Get statistics about active page integrations
    
    Returns:
        JSON response with integration statistics
    """
    try:
        # Get page integrator from app context
        page_integrator = current_app.page_notification_integrator
        if not page_integrator:
            return jsonify({'error': 'Page notification system not available'}), 503
        
        # Get integration statistics
        stats = page_integrator.get_integration_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Failed to get integration stats: {e}")
        return jsonify({'error': 'Failed to get integration statistics'}), 500


def _parse_page_config(config_data: Dict[str, Any], page_type: PageType) -> PageNotificationConfig:
    """
    Parse custom page configuration from request data
    
    Args:
        config_data: Configuration data from request
        page_type: Type of page
        
    Returns:
        PageNotificationConfig object
    """
    # Extract configuration values with defaults
    enabled_types = set(config_data.get('enabled_types', []))
    auto_hide = config_data.get('auto_hide', True)
    max_notifications = config_data.get('max_notifications', 5)
    position = config_data.get('position', 'top-right')
    show_progress = config_data.get('show_progress', False)
    
    # Validate values
    if not isinstance(auto_hide, bool):
        raise ValueError('auto_hide must be a boolean')
    
    if not isinstance(max_notifications, int) or max_notifications < 1 or max_notifications > 50:
        raise ValueError('max_notifications must be an integer between 1 and 50')
    
    valid_positions = [
        'top-right', 'top-left', 'top-center',
        'bottom-right', 'bottom-left', 'bottom-center',
        'full-width'
    ]
    if position not in valid_positions:
        raise ValueError(f'position must be one of: {valid_positions}')
    
    if not isinstance(show_progress, bool):
        raise ValueError('show_progress must be a boolean')
    
    # Determine namespace based on page type
    admin_page_types = {
        PageType.ADMIN_DASHBOARD, PageType.USER_MANAGEMENT,
        PageType.SYSTEM_HEALTH, PageType.MAINTENANCE, PageType.SECURITY_AUDIT
    }
    namespace = '/admin' if page_type in admin_page_types else '/'
    
    # Create configuration
    return PageNotificationConfig(
        page_type=page_type,
        enabled_types=enabled_types,
        auto_hide=auto_hide,
        max_notifications=max_notifications,
        position=position,
        show_progress=show_progress,
        namespace=namespace
    )


def register_page_notification_routes(app):
    """
    Register page notification routes with Flask app
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(page_notification_bp)
    logger.info("Page notification routes registered")