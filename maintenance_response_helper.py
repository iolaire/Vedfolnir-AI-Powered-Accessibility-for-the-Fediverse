# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Response Helper

Provides standardized maintenance response formatting with reason and duration.
Creates user-friendly maintenance status display and consistent messaging.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from flask import jsonify, render_template_string

from enhanced_maintenance_mode_service import MaintenanceStatus, MaintenanceMode
from maintenance_operation_classifier import OperationType

logger = logging.getLogger(__name__)


class MaintenanceResponseHelper:
    """
    Helper class for creating consistent maintenance responses
    
    Features:
    - Standardized maintenance response format with reason and duration
    - Operation-specific maintenance message templates
    - User-friendly maintenance status display
    - Consistent messaging across different operation types
    - Support for both JSON API responses and HTML templates
    """
    
    def __init__(self):
        """Initialize maintenance response helper"""
        
        # Operation-specific message templates
        self._operation_templates = {
            OperationType.PLATFORM_OPERATIONS: {
                'title': 'Platform Operations Unavailable',
                'description': 'Platform switching, connection testing, and credential updates are temporarily disabled during maintenance.',
                'icon': '🔗',
                'suggestion': 'You can continue using your current platform connection.'
            },
            
            OperationType.BATCH_OPERATIONS: {
                'title': 'Batch Operations Unavailable', 
                'description': 'Bulk processing, batch reviews, and bulk caption updates are temporarily disabled during maintenance.',
                'icon': '📦',
                'suggestion': 'You can still review individual items.'
            },
            
            OperationType.CAPTION_GENERATION: {
                'title': 'Caption Generation Unavailable',
                'description': 'AI caption generation is temporarily disabled during maintenance.',
                'icon': '🤖',
                'suggestion': 'Existing captions can still be reviewed and edited.'
            },
            
            OperationType.JOB_CREATION: {
                'title': 'Job Creation Unavailable',
                'description': 'New background jobs cannot be created during maintenance.',
                'icon': '⚙️',
                'suggestion': 'Running jobs will complete normally.'
            },
            
            OperationType.USER_DATA_MODIFICATION: {
                'title': 'Profile Updates Unavailable',
                'description': 'User profile and settings updates are temporarily disabled during maintenance.',
                'icon': '👤',
                'suggestion': 'You can still browse and review content.'
            },
            
            OperationType.IMAGE_PROCESSING: {
                'title': 'Image Processing Unavailable',
                'description': 'Image upload and processing operations are temporarily disabled during maintenance.',
                'icon': '🖼️',
                'suggestion': 'Existing images can still be viewed and reviewed.'
            }
        }
        
        # Default template for unknown operations
        self._default_template = {
            'title': 'Service Temporarily Unavailable',
            'description': 'This operation is temporarily disabled during maintenance.',
            'icon': '🔧',
            'suggestion': 'Please try again after maintenance is complete.'
        }
        
        # Maintenance mode specific messages
        self._mode_messages = {
            MaintenanceMode.NORMAL: {
                'prefix': '🔧 System Maintenance',
                'description': 'Routine maintenance is in progress to improve system performance and reliability.'
            },
            MaintenanceMode.EMERGENCY: {
                'prefix': '🚨 Emergency Maintenance',
                'description': 'Emergency maintenance is in progress to address critical system issues.'
            },
            MaintenanceMode.TEST: {
                'prefix': '🧪 Test Maintenance',
                'description': 'Test maintenance mode is active for system validation.'
            }
        }
    
    def create_json_response(self, operation: str, maintenance_status: MaintenanceStatus, 
                           operation_type: Optional[OperationType] = None) -> Dict[str, Any]:
        """
        Create standardized JSON maintenance response
        
        Args:
            operation: Operation that was blocked
            maintenance_status: Current maintenance status
            operation_type: Classified operation type (optional)
            
        Returns:
            Dictionary with standardized maintenance response data
        """
        try:
            # Get operation template
            template = self._get_operation_template(operation_type)
            
            # Get mode-specific message
            mode_info = self._mode_messages.get(maintenance_status.mode, self._mode_messages[MaintenanceMode.NORMAL])
            
            # Build comprehensive response
            response_data = {
                'error': 'Service Unavailable',
                'maintenance_active': True,
                'maintenance_info': {
                    'mode': maintenance_status.mode.value,
                    'reason': maintenance_status.reason,
                    'started_at': maintenance_status.started_at.isoformat() if maintenance_status.started_at else None,
                    'estimated_completion': maintenance_status.estimated_completion.isoformat() if maintenance_status.estimated_completion else None,
                    'estimated_duration': maintenance_status.estimated_duration,
                    'enabled_by': maintenance_status.enabled_by,
                    'test_mode': maintenance_status.test_mode
                },
                'operation_info': {
                    'operation': operation,
                    'operation_type': operation_type.value if operation_type else 'unknown',
                    'title': template['title'],
                    'description': template['description'],
                    'icon': template['icon'],
                    'suggestion': template['suggestion']
                },
                'message': self._build_user_message(maintenance_status, template, mode_info),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Add retry information if available
            if maintenance_status.estimated_completion:
                response_data['retry_after'] = self._calculate_retry_after(maintenance_status)
            elif maintenance_status.estimated_duration:
                response_data['retry_after'] = maintenance_status.estimated_duration * 60  # Convert to seconds
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error creating JSON maintenance response: {str(e)}")
            
            # Return fallback response
            return {
                'error': 'Service Unavailable',
                'message': 'System maintenance is in progress. Please try again later.',
                'maintenance_active': True,
                'operation': operation,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def create_flask_response(self, operation: str, maintenance_status: MaintenanceStatus,
                            operation_type: Optional[OperationType] = None):
        """
        Create Flask JSON response for maintenance
        
        Args:
            operation: Operation that was blocked
            maintenance_status: Current maintenance status
            operation_type: Classified operation type (optional)
            
        Returns:
            Flask Response object with 503 status
        """
        try:
            response_data = self.create_json_response(operation, maintenance_status, operation_type)
            
            # Create Flask response
            response = jsonify(response_data)
            response.status_code = 503
            
            # Add standard maintenance headers
            response.headers['X-Maintenance-Active'] = 'true'
            response.headers['X-Maintenance-Mode'] = maintenance_status.mode.value
            
            # Add Retry-After header if available
            if 'retry_after' in response_data:
                response.headers['Retry-After'] = str(response_data['retry_after'])
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating Flask maintenance response: {str(e)}")
            
            # Return fallback response
            fallback_response = jsonify({
                'error': 'Service Unavailable',
                'message': 'System maintenance is in progress. Please try again later.',
                'maintenance_active': True,
                'operation': operation,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            fallback_response.status_code = 503
            return fallback_response
    
    def create_html_maintenance_banner(self, maintenance_status: MaintenanceStatus) -> str:
        """
        Create HTML maintenance banner for web pages
        
        Args:
            maintenance_status: Current maintenance status
            
        Returns:
            HTML string for maintenance banner
        """
        try:
            if not maintenance_status.is_active:
                return ""
            
            # Get mode-specific styling and message
            mode_info = self._mode_messages.get(maintenance_status.mode, self._mode_messages[MaintenanceMode.NORMAL])
            
            # Determine banner style based on maintenance mode
            if maintenance_status.mode == MaintenanceMode.EMERGENCY:
                banner_class = "alert alert-danger"
                icon = "🚨"
            elif maintenance_status.mode == MaintenanceMode.TEST:
                banner_class = "alert alert-info"
                icon = "🧪"
            else:
                banner_class = "alert alert-warning"
                icon = "🔧"
            
            # Build maintenance message
            message = f"{icon} {mode_info['prefix']}"
            if maintenance_status.reason:
                message += f": {maintenance_status.reason}"
            
            # Add duration information
            duration_info = ""
            if maintenance_status.estimated_completion:
                completion_str = maintenance_status.estimated_completion.strftime("%Y-%m-%d %H:%M UTC")
                duration_info = f"Expected completion: {completion_str}"
            elif maintenance_status.estimated_duration:
                duration_info = f"Estimated duration: {maintenance_status.estimated_duration} minutes"
            
            # Create HTML template
            html_template = """
            <div class="{{ banner_class }}" role="alert" id="maintenance-banner">
                <div class="d-flex align-items-center">
                    <div class="flex-grow-1">
                        <strong>{{ message }}</strong>
                        {% if duration_info %}
                        <br><small>{{ duration_info }}</small>
                        {% endif %}
                        <br><small>{{ mode_description }}</small>
                    </div>
                    {% if not test_mode %}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    {% endif %}
                </div>
            </div>
            """
            
            # Render template
            return render_template_string(html_template,
                banner_class=banner_class,
                message=message,
                duration_info=duration_info,
                mode_description=mode_info['description'],
                test_mode=maintenance_status.test_mode
            )
            
        except Exception as e:
            logger.error(f"Error creating HTML maintenance banner: {str(e)}")
            return f'<div class="alert alert-warning">🔧 System maintenance is in progress.</div>'
    
    def get_operation_message_template(self, operation_type: OperationType) -> Dict[str, str]:
        """
        Get message template for specific operation type
        
        Args:
            operation_type: Type of operation
            
        Returns:
            Dictionary with message template
        """
        return self._operation_templates.get(operation_type, self._default_template).copy()
    
    def _get_operation_template(self, operation_type: Optional[OperationType]) -> Dict[str, str]:
        """
        Get operation-specific template
        
        Args:
            operation_type: Type of operation (optional)
            
        Returns:
            Template dictionary
        """
        if operation_type and operation_type in self._operation_templates:
            return self._operation_templates[operation_type]
        return self._default_template
    
    def _build_user_message(self, maintenance_status: MaintenanceStatus, 
                          template: Dict[str, str], mode_info: Dict[str, str]) -> str:
        """
        Build comprehensive user-facing message
        
        Args:
            maintenance_status: Current maintenance status
            template: Operation template
            mode_info: Mode-specific information
            
        Returns:
            Complete user message
        """
        try:
            # Start with mode prefix and reason
            message = mode_info['prefix']
            if maintenance_status.reason:
                message += f": {maintenance_status.reason}"
            
            # Add operation-specific information
            message += f"\n\n{template['description']}"
            
            # Add duration information
            if maintenance_status.estimated_completion:
                completion_str = maintenance_status.estimated_completion.strftime("%Y-%m-%d %H:%M UTC")
                message += f"\n\nExpected completion: {completion_str}"
            elif maintenance_status.estimated_duration:
                message += f"\n\nEstimated duration: {maintenance_status.estimated_duration} minutes"
            
            # Add suggestion
            message += f"\n\n{template['suggestion']}"
            
            # Add general advice
            message += "\n\nPlease try again after maintenance is complete."
            
            return message
            
        except Exception as e:
            logger.error(f"Error building user message: {str(e)}")
            return "System maintenance is in progress. Please try again later."
    
    def _calculate_retry_after(self, maintenance_status: MaintenanceStatus) -> int:
        """
        Calculate retry-after seconds from maintenance status
        
        Args:
            maintenance_status: Current maintenance status
            
        Returns:
            Seconds until estimated completion
        """
        try:
            if maintenance_status.estimated_completion:
                now = datetime.now(timezone.utc)
                delta = maintenance_status.estimated_completion - now
                return max(60, int(delta.total_seconds()))  # Minimum 1 minute
            return 3600  # Default 1 hour
            
        except Exception as e:
            logger.error(f"Error calculating retry-after: {str(e)}")
            return 3600  # Default 1 hour
    
    def create_maintenance_status_dict(self, maintenance_status: MaintenanceStatus) -> Dict[str, Any]:
        """
        Create dictionary representation of maintenance status for templates
        
        Args:
            maintenance_status: Current maintenance status
            
        Returns:
            Dictionary with maintenance status information
        """
        try:
            mode_info = self._mode_messages.get(maintenance_status.mode, self._mode_messages[MaintenanceMode.NORMAL])
            
            return {
                'is_active': maintenance_status.is_active,
                'mode': maintenance_status.mode.value,
                'mode_display': mode_info['prefix'],
                'mode_description': mode_info['description'],
                'reason': maintenance_status.reason,
                'estimated_duration': maintenance_status.estimated_duration,
                'started_at': maintenance_status.started_at.isoformat() if maintenance_status.started_at else None,
                'estimated_completion': maintenance_status.estimated_completion.isoformat() if maintenance_status.estimated_completion else None,
                'enabled_by': maintenance_status.enabled_by,
                'blocked_operations': maintenance_status.blocked_operations,
                'active_jobs_count': maintenance_status.active_jobs_count,
                'invalidated_sessions': maintenance_status.invalidated_sessions,
                'test_mode': maintenance_status.test_mode,
                'banner_html': self.create_html_maintenance_banner(maintenance_status)
            }
            
        except Exception as e:
            logger.error(f"Error creating maintenance status dict: {str(e)}")
            return {
                'is_active': False,
                'mode': 'normal',
                'mode_display': 'Normal Operation',
                'mode_description': 'System is operating normally',
                'banner_html': ''
            }