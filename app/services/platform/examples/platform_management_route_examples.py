# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Platform Management Route Examples

This module demonstrates how to update existing platform management routes
to use the unified WebSocket notification system instead of legacy flash messages.

These are example implementations showing the migration pattern.
"""

import logging
from flask import jsonify, request, current_app
from flask_login import current_user, login_required

from platform_management_route_integration import get_platform_route_integrator
from platform_management_notification_integration import get_platform_notification_service

logger = logging.getLogger(__name__)


def example_api_add_platform_updated():
    """
    Example of updated add platform route with WebSocket notifications
    
    This shows how to modify the existing route to use the unified notification system
    instead of returning plain JSON responses that rely on JavaScript alerts.
    """
    try:
        # Get route integrator
        integrator = get_platform_route_integrator()
        
        # ... existing validation and platform creation logic ...
        
        # Example successful platform creation
        success = True  # Result from platform creation
        platform_data = {
            'id': 123,
            'name': 'My Platform',
            'platform_type': 'pixelfed',
            'instance_url': 'https://pixelfed.social',
            'username': 'myuser'
        }
        is_first_platform = True  # Check if this is user's first platform
        
        if success:
            # Use integrator to handle response with WebSocket notifications
            response_data, status_code = integrator.handle_add_platform_response(
                success=True,
                message='Platform connection added successfully',
                platform_data=platform_data,
                is_first_platform=is_first_platform
            )
        else:
            # Handle error case
            response_data, status_code = integrator.handle_add_platform_response(
                success=False,
                message='Failed to add platform connection',
                error_details='Connection test failed: Invalid credentials'
            )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Error in add platform route: {e}")
        integrator = get_platform_route_integrator()
        response_data, status_code = integrator.handle_add_platform_response(
            success=False,
            message='Internal server error',
            error_details=str(e)
        )
        return jsonify(response_data), status_code


def example_api_switch_platform_updated(platform_id):
    """
    Example of updated switch platform route with WebSocket notifications
    
    Args:
        platform_id: ID of platform to switch to
    """
    try:
        # Get route integrator
        integrator = get_platform_route_integrator()
        
        # ... existing platform switching logic ...
        
        # Example successful platform switch
        success = True  # Result from platform switch
        from_platform = 'Old Platform'  # Previous platform name
        new_platform_data = {
            'id': platform_id,
            'name': 'New Platform',
            'platform_type': 'mastodon',
            'instance_url': 'https://mastodon.social',
            'username': 'newuser'
        }
        
        if success:
            # Use integrator to handle response with WebSocket notifications
            response_data, status_code = integrator.handle_switch_platform_response(
                success=True,
                message=f'Successfully switched to {new_platform_data["name"]}',
                platform_data=new_platform_data,
                from_platform=from_platform
            )
        else:
            # Handle error case
            response_data, status_code = integrator.handle_switch_platform_response(
                success=False,
                message='Failed to switch platform',
                error_message='Platform not found or not accessible'
            )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Error in switch platform route: {e}")
        integrator = get_platform_route_integrator()
        response_data, status_code = integrator.handle_switch_platform_response(
            success=False,
            message='Internal server error',
            error_message=str(e)
        )
        return jsonify(response_data), status_code


def example_api_test_platform_updated(platform_id):
    """
    Example of updated test platform route with WebSocket notifications
    
    Args:
        platform_id: ID of platform to test
    """
    try:
        # Get route integrator
        integrator = get_platform_route_integrator()
        
        # ... existing platform testing logic ...
        
        # Example successful connection test
        success = True  # Result from connection test
        platform_name = 'Test Platform'
        test_message = 'Connection successful! Verified access to platform.'
        platform_info = {
            'name': platform_name,
            'type': 'pixelfed',
            'instance': 'https://pixelfed.social'
        }
        
        # Use integrator to handle response with WebSocket notifications
        response_data, status_code = integrator.handle_test_platform_response(
            success=success,
            message=test_message,
            platform_name=platform_name,
            platform_info=platform_info
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Error in test platform route: {e}")
        integrator = get_platform_route_integrator()
        response_data, status_code = integrator.handle_test_platform_response(
            success=False,
            message='Connection test failed',
            platform_name='Unknown Platform'
        )
        return jsonify(response_data), status_code


def example_api_edit_platform_updated(platform_id):
    """
    Example of updated edit platform route with WebSocket notifications
    
    Args:
        platform_id: ID of platform to edit
    """
    try:
        # Get route integrator
        integrator = get_platform_route_integrator()
        
        # ... existing platform editing logic ...
        
        # Example successful platform edit
        success = True  # Result from platform edit
        platform_name = 'Updated Platform'
        change_details = 'Updated access token and instance URL'
        
        if success:
            # Use integrator to handle response with WebSocket notifications
            response_data, status_code = integrator.handle_edit_platform_response(
                success=True,
                message='Platform connection updated successfully',
                platform_name=platform_name,
                change_details=change_details
            )
        else:
            # Handle error case
            response_data, status_code = integrator.handle_edit_platform_response(
                success=False,
                message='Failed to update platform connection',
                platform_name=platform_name,
                error_details='Invalid access token provided'
            )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Error in edit platform route: {e}")
        integrator = get_platform_route_integrator()
        response_data, status_code = integrator.handle_edit_platform_response(
            success=False,
            message='Internal server error',
            platform_name='Unknown Platform',
            error_details=str(e)
        )
        return jsonify(response_data), status_code


def example_api_delete_platform_updated(platform_id):
    """
    Example of updated delete platform route with WebSocket notifications
    
    Args:
        platform_id: ID of platform to delete
    """
    try:
        # Get route integrator
        integrator = get_platform_route_integrator()
        
        # ... existing platform deletion logic ...
        
        # Example successful platform deletion
        success = True  # Result from platform deletion
        platform_name = 'Deleted Platform'
        
        if success:
            # Use integrator to handle response with WebSocket notifications
            response_data, status_code = integrator.handle_delete_platform_response(
                success=True,
                message=f'Platform connection "{platform_name}" deleted successfully',
                platform_name=platform_name
            )
        else:
            # Handle error case
            response_data, status_code = integrator.handle_delete_platform_response(
                success=False,
                message='Failed to delete platform connection',
                platform_name=platform_name,
                error_details='Platform not found or access denied'
            )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Error in delete platform route: {e}")
        integrator = get_platform_route_integrator()
        response_data, status_code = integrator.handle_delete_platform_response(
            success=False,
            message='Internal server error',
            platform_name='Unknown Platform',
            error_details=str(e)
        )
        return jsonify(response_data), status_code


def example_handle_authentication_error():
    """
    Example of handling platform authentication errors with WebSocket notifications
    """
    try:
        # Get route integrator
        integrator = get_platform_route_integrator()
        
        # Example authentication error
        platform_name = 'My Platform'
        error_type = 'invalid_token'
        error_details = 'Access token has expired or been revoked'
        
        # Use integrator to handle authentication error with WebSocket notifications
        response_data, status_code = integrator.handle_authentication_error(
            platform_name=platform_name,
            error_type=error_type,
            error_details=error_details
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Error handling authentication error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


def example_handle_maintenance_mode():
    """
    Example of handling maintenance mode responses with WebSocket notifications
    """
    try:
        # Get route integrator
        integrator = get_platform_route_integrator()
        
        # Example maintenance mode information
        operation_type = 'platform_switching'
        maintenance_info = {
            'reason': 'Scheduled system maintenance',
            'estimated_duration': 30,  # minutes
            'estimated_completion': '2025-01-15T10:30:00Z'
        }
        
        # Use integrator to handle maintenance mode response with WebSocket notifications
        response_data, status_code = integrator.handle_maintenance_mode_response(
            operation_type=operation_type,
            maintenance_info=maintenance_info
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Error handling maintenance mode response: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# Example of how to integrate with existing route decorators
def example_route_with_notifications():
    """
    Example showing how to integrate notifications with existing Flask route patterns
    """
    
    # This would be added to existing routes like:
    # @app.route('/api/add_platform', methods=['POST'])
    # @login_required
    # @require_viewer_or_higher
    # @validate_csrf_token
    # @enhanced_input_validation
    # @with_session_error_handling
    # def api_add_platform():
    #     return example_api_add_platform_updated()
    
    pass


# Example of direct notification service usage
def example_direct_notification_usage():
    """
    Example of using the notification service directly for custom notifications
    """
    try:
        # Get notification service
        notification_service = get_platform_notification_service()
        
        if notification_service and hasattr(current_user, 'id'):
            # Send custom platform status notification
            success = notification_service.send_platform_status_notification(
                user_id=current_user.id,
                platform_name='My Platform',
                status='active',
                details='Connection restored after temporary outage'
            )
            
            if success:
                logger.info("Custom platform notification sent successfully")
            else:
                logger.warning("Failed to send custom platform notification")
        
    except Exception as e:
        logger.error(f"Error sending direct notification: {e}")


# Migration checklist for existing routes:
"""
MIGRATION CHECKLIST FOR PLATFORM MANAGEMENT ROUTES:

1. Import the integration modules:
   from platform_management_route_integration import get_platform_route_integrator

2. Replace direct jsonify() returns with integrator methods:
   - For add_platform: use integrator.handle_add_platform_response()
   - For switch_platform: use integrator.handle_switch_platform_response()
   - For test_platform: use integrator.handle_test_platform_response()
   - For edit_platform: use integrator.handle_edit_platform_response()
   - For delete_platform: use integrator.handle_delete_platform_response()

3. Remove flash() calls - notifications are now sent via WebSocket

4. Update error handling to use integrator methods:
   - For auth errors: use integrator.handle_authentication_error()
   - For maintenance mode: use integrator.handle_maintenance_mode_response()

5. Update JavaScript to remove showAlert() calls - notifications come via WebSocket

6. Test WebSocket connectivity and fallback to legacy notifications

7. Verify notification delivery across different browsers and network conditions

8. Update any custom notification logic to use the unified system

BACKWARD COMPATIBILITY:
- JSON responses remain the same structure for API compatibility
- Legacy JavaScript alert system works as fallback
- Existing error handling patterns are preserved
- No breaking changes to existing functionality
"""