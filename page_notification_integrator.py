# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Page Notification Integrator

This module provides seamless page integration for the unified notification system,
including page-specific notification initialization, WebSocket connection management,
event handler registration, and proper cleanup on page unload.
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass
from enum import Enum
from flask import Flask, request, session, current_app

from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager
from unified_notification_manager import UnifiedNotificationManager

logger = logging.getLogger(__name__)


class PageType(Enum):
    """Types of pages that can integrate notifications"""
    USER_DASHBOARD = "user_dashboard"
    CAPTION_PROCESSING = "caption_processing"
    PLATFORM_MANAGEMENT = "platform_management"
    USER_PROFILE = "user_profile"
    ADMIN_DASHBOARD = "admin_dashboard"
    USER_MANAGEMENT = "user_management"
    SYSTEM_HEALTH = "system_health"
    MAINTENANCE = "maintenance"
    SECURITY_AUDIT = "security_audit"


@dataclass
class PageNotificationConfig:
    """Configuration for page-specific notifications"""
    page_type: PageType
    enabled_types: Set[str]
    auto_hide: bool = True
    max_notifications: int = 5
    position: str = 'top-right'
    show_progress: bool = False
    namespace: str = '/'
    required_permissions: Set[str] = None
    websocket_events: Set[str] = None
    
    def __post_init__(self):
        if self.required_permissions is None:
            self.required_permissions = set()
        if self.websocket_events is None:
            self.websocket_events = set()


class PageNotificationIntegrator:
    """
    Page integration manager for seamless notification integration
    
    Provides page-specific notification initialization, WebSocket connection management,
    event handler registration, and proper cleanup on page unload.
    """
    
    def __init__(self, websocket_factory: WebSocketFactory, 
                 auth_handler: WebSocketAuthHandler,
                 namespace_manager: WebSocketNamespaceManager,
                 notification_manager: UnifiedNotificationManager):
        """
        Initialize page notification integrator
        
        Args:
            websocket_factory: WebSocket factory instance
            auth_handler: WebSocket authentication handler
            namespace_manager: WebSocket namespace manager
            notification_manager: Unified notification manager
        """
        self.websocket_factory = websocket_factory
        self.auth_handler = auth_handler
        self.namespace_manager = namespace_manager
        self.notification_manager = notification_manager
        self.logger = logging.getLogger(__name__)
        
        # Page configurations
        self._page_configs = {}
        self._active_integrations = {}  # page_id -> integration_info
        
        # Event handlers registry
        self._page_event_handlers = {}  # page_type -> {event: handler}
        
        # Initialize default page configurations
        self._setup_default_page_configs()
    
    def register_page_integration(self, page_id: str, page_type: PageType, 
                                config: Optional[PageNotificationConfig] = None) -> Dict[str, Any]:
        """
        Register a page for notification integration
        
        Args:
            page_id: Unique page identifier
            page_type: Type of page being integrated
            config: Optional custom configuration
            
        Returns:
            Dictionary containing integration configuration for client-side
        """
        try:
            # Get or create page configuration
            if config is None:
                config = self._page_configs.get(page_type)
                if config is None:
                    raise ValueError(f"No default configuration for page type: {page_type}")
            
            # Validate user permissions for page type
            if not self._validate_page_permissions(page_type, config):
                raise PermissionError(f"User lacks permissions for page type: {page_type}")
            
            # Create integration info
            integration_info = {
                'page_id': page_id,
                'page_type': page_type.value,
                'config': config,
                'registered_at': self._get_current_timestamp(),
                'websocket_connected': False,
                'active_handlers': set()
            }
            
            self._active_integrations[page_id] = integration_info
            
            # Generate client-side configuration
            client_config = self._generate_client_config(page_id, page_type, config)
            
            self.logger.info(f"Registered page integration: {page_id} ({page_type.value})")
            return client_config
            
        except Exception as e:
            self.logger.error(f"Failed to register page integration for {page_id}: {e}")
            raise RuntimeError(f"Page integration registration failed: {e}")
    
    def initialize_page_notifications(self, page_id: str) -> Dict[str, Any]:
        """
        Initialize notifications for a registered page
        
        Args:
            page_id: Page identifier
            
        Returns:
            Dictionary containing initialization status and configuration
        """
        try:
            if page_id not in self._active_integrations:
                raise ValueError(f"Page {page_id} not registered for integration")
            
            integration_info = self._active_integrations[page_id]
            config = integration_info['config']
            page_type = PageType(integration_info['page_type'])
            
            # Setup WebSocket connection configuration
            websocket_config = self._setup_websocket_connection_config(page_id, config)
            
            # Register page-specific event handlers
            event_handlers = self._register_page_event_handlers(page_id, page_type, config)
            
            # Setup notification UI configuration
            ui_config = self._setup_notification_ui_config(page_id, config)
            
            # Mark as initialized
            integration_info['initialized'] = True
            integration_info['initialized_at'] = self._get_current_timestamp()
            
            initialization_result = {
                'page_id': page_id,
                'status': 'initialized',
                'websocket_config': websocket_config,
                'event_handlers': event_handlers,
                'ui_config': ui_config,
                'timestamp': self._get_current_timestamp()
            }
            
            self.logger.info(f"Initialized notifications for page: {page_id}")
            return initialization_result
            
        except Exception as e:
            self.logger.error(f"Failed to initialize notifications for page {page_id}: {e}")
            raise RuntimeError(f"Page notification initialization failed: {e}")
    
    def setup_websocket_connection(self, page_id: str) -> Dict[str, Any]:
        """
        Setup WebSocket connection for a page using existing CORS framework
        
        Args:
            page_id: Page identifier
            
        Returns:
            Dictionary containing WebSocket connection configuration
        """
        try:
            if page_id not in self._active_integrations:
                raise ValueError(f"Page {page_id} not registered")
            
            integration_info = self._active_integrations[page_id]
            config = integration_info['config']
            
            # Get current user session information
            user_info = self._get_current_user_info()
            if not user_info:
                raise RuntimeError("No authenticated user session found")
            
            # Determine appropriate namespace based on page type and user role
            namespace = self._determine_namespace(config, user_info)
            
            # Generate WebSocket connection configuration
            connection_config = {
                'namespace': namespace,
                'auth_data': {
                    'session_id': user_info.get('session_id'),
                    'user_id': user_info.get('user_id'),
                    'page_id': page_id
                },
                'transport_options': {
                    'transports': ['websocket', 'polling'],
                    'upgrade': True,
                    'rememberUpgrade': True
                },
                'reconnection_config': {
                    'reconnection': True,
                    'reconnectionAttempts': 5,
                    'reconnectionDelay': 1000,
                    'reconnectionDelayMax': 5000,
                    'maxReconnectionAttempts': 5
                },
                'timeout_config': {
                    'timeout': 20000,
                    'pingTimeout': 60000,
                    'pingInterval': 25000
                }
            }
            
            # Add page-specific WebSocket events
            connection_config['page_events'] = list(config.websocket_events)
            
            # Mark WebSocket as configured
            integration_info['websocket_configured'] = True
            integration_info['websocket_namespace'] = namespace
            
            self.logger.info(f"Setup WebSocket connection for page {page_id} in namespace {namespace}")
            return connection_config
            
        except Exception as e:
            self.logger.error(f"Failed to setup WebSocket connection for page {page_id}: {e}")
            raise RuntimeError(f"WebSocket connection setup failed: {e}")
    
    def register_event_handlers(self, page_id: str, custom_handlers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Register event handlers for page-specific notifications
        
        Args:
            page_id: Page identifier
            custom_handlers: Optional custom event handlers (event -> handler_function_name)
            
        Returns:
            Dictionary containing registered event handlers
        """
        try:
            if page_id not in self._active_integrations:
                raise ValueError(f"Page {page_id} not registered")
            
            integration_info = self._active_integrations[page_id]
            config = integration_info['config']
            page_type = PageType(integration_info['page_type'])
            
            # Get default handlers for page type
            default_handlers = self._get_default_event_handlers(page_type)
            
            # Merge with custom handlers
            if custom_handlers:
                default_handlers.update(custom_handlers)
            
            # Generate client-side event handler configuration
            handler_config = {
                'page_id': page_id,
                'namespace': config.namespace,
                'handlers': {},
                'middleware': []
            }
            
            # Add connection event handlers
            handler_config['handlers']['connect'] = 'handleNotificationConnect'
            handler_config['handlers']['disconnect'] = 'handleNotificationDisconnect'
            handler_config['handlers']['connect_error'] = 'handleNotificationConnectError'
            handler_config['handlers']['reconnect'] = 'handleNotificationReconnect'
            
            # Add notification event handlers
            handler_config['handlers']['notification'] = 'handleNotificationMessage'
            handler_config['handlers']['system_notification'] = 'handleSystemNotification'
            handler_config['handlers']['admin_notification'] = 'handleAdminNotification'
            
            # Add page-specific handlers
            for event, handler_name in default_handlers.items():
                handler_config['handlers'][event] = handler_name
            
            # Add error handling middleware
            handler_config['middleware'] = [
                'validateNotificationPermissions',
                'logNotificationEvents',
                'handleNotificationErrors'
            ]
            
            # Store registered handlers
            integration_info['active_handlers'] = set(handler_config['handlers'].keys())
            
            self.logger.info(f"Registered {len(handler_config['handlers'])} event handlers for page {page_id}")
            return handler_config
            
        except Exception as e:
            self.logger.error(f"Failed to register event handlers for page {page_id}: {e}")
            raise RuntimeError(f"Event handler registration failed: {e}")
    
    def cleanup_page_integration(self, page_id: str) -> bool:
        """
        Clean up page integration on page unload
        
        Args:
            page_id: Page identifier
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            if page_id not in self._active_integrations:
                self.logger.warning(f"Attempted to cleanup unregistered page: {page_id}")
                return True
            
            integration_info = self._active_integrations[page_id]
            
            # Generate cleanup configuration for client-side
            cleanup_config = {
                'page_id': page_id,
                'disconnect_websocket': True,
                'clear_event_handlers': True,
                'cleanup_ui_elements': True,
                'save_notification_state': True,
                'namespace': integration_info.get('websocket_namespace', '/'),
                'cleanup_timestamp': self._get_current_timestamp()
            }
            
            # Remove from active integrations
            del self._active_integrations[page_id]
            
            self.logger.info(f"Cleaned up page integration: {page_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup page integration {page_id}: {e}")
            return False
    
    def get_page_integration_status(self, page_id: str) -> Dict[str, Any]:
        """
        Get status of page integration
        
        Args:
            page_id: Page identifier
            
        Returns:
            Dictionary containing integration status
        """
        try:
            if page_id not in self._active_integrations:
                return {
                    'page_id': page_id,
                    'status': 'not_registered',
                    'error': 'Page not registered for integration'
                }
            
            integration_info = self._active_integrations[page_id]
            
            status = {
                'page_id': page_id,
                'page_type': integration_info['page_type'],
                'status': 'registered',
                'registered_at': integration_info['registered_at'],
                'initialized': integration_info.get('initialized', False),
                'websocket_configured': integration_info.get('websocket_configured', False),
                'websocket_connected': integration_info.get('websocket_connected', False),
                'active_handlers': list(integration_info.get('active_handlers', set())),
                'namespace': integration_info.get('websocket_namespace'),
                'config': {
                    'enabled_types': list(integration_info['config'].enabled_types),
                    'auto_hide': integration_info['config'].auto_hide,
                    'max_notifications': integration_info['config'].max_notifications,
                    'position': integration_info['config'].position,
                    'show_progress': integration_info['config'].show_progress
                }
            }
            
            if integration_info.get('initialized'):
                status['initialized_at'] = integration_info['initialized_at']
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get integration status for page {page_id}: {e}")
            return {
                'page_id': page_id,
                'status': 'error',
                'error': str(e)
            }
    
    def _setup_default_page_configs(self) -> None:
        """
        Setup default configurations for different page types
        """
        # User Dashboard Configuration
        self._page_configs[PageType.USER_DASHBOARD] = PageNotificationConfig(
            page_type=PageType.USER_DASHBOARD,
            enabled_types={'system', 'caption', 'platform', 'maintenance'},
            auto_hide=True,
            max_notifications=5,
            position='top-right',
            show_progress=False,
            namespace='/',
            websocket_events={
                'caption_progress', 'caption_status', 'platform_status',
                'notification', 'user_activity', 'system_notification'
            }
        )
        
        # Caption Processing Configuration
        self._page_configs[PageType.CAPTION_PROCESSING] = PageNotificationConfig(
            page_type=PageType.CAPTION_PROCESSING,
            enabled_types={'caption', 'system', 'maintenance'},
            auto_hide=True,
            max_notifications=3,
            position='bottom-center',
            show_progress=True,
            namespace='/',
            websocket_events={
                'caption_progress', 'caption_status', 'caption_complete',
                'caption_error', 'system_notification'
            }
        )
        
        # Platform Management Configuration
        self._page_configs[PageType.PLATFORM_MANAGEMENT] = PageNotificationConfig(
            page_type=PageType.PLATFORM_MANAGEMENT,
            enabled_types={'platform', 'system', 'maintenance'},
            auto_hide=True,
            max_notifications=4,
            position='top-center',
            show_progress=False,
            namespace='/',
            websocket_events={
                'platform_status', 'platform_connection', 'platform_error',
                'system_notification'
            }
        )
        
        # User Profile Configuration
        self._page_configs[PageType.USER_PROFILE] = PageNotificationConfig(
            page_type=PageType.USER_PROFILE,
            enabled_types={'system', 'security', 'maintenance'},
            auto_hide=True,
            max_notifications=3,
            position='top-right',
            show_progress=False,
            namespace='/',
            websocket_events={
                'profile_update', 'security_notification', 'system_notification'
            }
        )
        
        # Admin Dashboard Configuration
        self._page_configs[PageType.ADMIN_DASHBOARD] = PageNotificationConfig(
            page_type=PageType.ADMIN_DASHBOARD,
            enabled_types={'system', 'admin', 'security', 'maintenance'},
            auto_hide=False,
            max_notifications=10,
            position='top-center',
            show_progress=False,
            namespace='/admin',
            required_permissions={'system_management'},
            websocket_events={
                'system_status', 'admin_notification', 'security_alert',
                'maintenance_status', 'user_management'
            }
        )
        
        # User Management Configuration
        self._page_configs[PageType.USER_MANAGEMENT] = PageNotificationConfig(
            page_type=PageType.USER_MANAGEMENT,
            enabled_types={'admin', 'security', 'system'},
            auto_hide=False,
            max_notifications=8,
            position='top-right',
            show_progress=False,
            namespace='/admin',
            required_permissions={'user_management'},
            websocket_events={
                'user_management', 'user_status', 'security_alert',
                'admin_notification'
            }
        )
        
        # System Health Configuration
        self._page_configs[PageType.SYSTEM_HEALTH] = PageNotificationConfig(
            page_type=PageType.SYSTEM_HEALTH,
            enabled_types={'system', 'admin', 'maintenance'},
            auto_hide=False,
            max_notifications=15,
            position='bottom-left',
            show_progress=True,
            namespace='/admin',
            required_permissions={'system_management'},
            websocket_events={
                'system_status', 'health_metrics', 'performance_alert',
                'maintenance_status'
            }
        )
        
        # Maintenance Configuration
        self._page_configs[PageType.MAINTENANCE] = PageNotificationConfig(
            page_type=PageType.MAINTENANCE,
            enabled_types={'maintenance', 'system', 'admin'},
            auto_hide=False,
            max_notifications=12,
            position='full-width',
            show_progress=True,
            namespace='/admin',
            required_permissions={'maintenance_operations'},
            websocket_events={
                'maintenance_status', 'maintenance_progress', 'system_status',
                'admin_notification'
            }
        )
        
        # Security Audit Configuration
        self._page_configs[PageType.SECURITY_AUDIT] = PageNotificationConfig(
            page_type=PageType.SECURITY_AUDIT,
            enabled_types={'security', 'admin', 'system'},
            auto_hide=False,
            max_notifications=20,
            position='top-left',
            show_progress=False,
            namespace='/admin',
            required_permissions={'security_monitoring'},
            websocket_events={
                'security_alert', 'audit_event', 'security_notification',
                'admin_notification'
            }
        )
    
    def _validate_page_permissions(self, page_type: PageType, config: PageNotificationConfig) -> bool:
        """
        Validate user permissions for page type
        
        Args:
            page_type: Type of page
            config: Page configuration
            
        Returns:
            True if user has required permissions, False otherwise
        """
        try:
            user_info = self._get_current_user_info()
            if not user_info:
                return False
            
            user_role = user_info.get('role')
            if not user_role:
                return False
            
            # Check if admin namespace is required
            if config.namespace == '/admin':
                if user_role != 'admin':
                    return False
            
            # Check specific permissions if required
            if config.required_permissions:
                user_permissions = user_info.get('permissions', set())
                if not config.required_permissions.issubset(user_permissions):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating page permissions: {e}")
            return False
    
    def _generate_client_config(self, page_id: str, page_type: PageType, 
                              config: PageNotificationConfig) -> Dict[str, Any]:
        """
        Generate client-side configuration for page integration
        
        Args:
            page_id: Page identifier
            page_type: Type of page
            config: Page configuration
            
        Returns:
            Dictionary containing client-side configuration
        """
        return {
            'page_id': page_id,
            'page_type': page_type.value,
            'notification_config': {
                'enabled_types': list(config.enabled_types),
                'auto_hide': config.auto_hide,
                'max_notifications': config.max_notifications,
                'position': config.position,
                'show_progress': config.show_progress
            },
            'websocket_config': {
                'namespace': config.namespace,
                'events': list(config.websocket_events),
                'auto_connect': True,
                'reconnect_on_error': True
            },
            'ui_config': {
                'container_id': f'notifications-{page_id}',
                'theme': 'default',
                'animations': True,
                'sound_enabled': False
            },
            'security_config': {
                'validate_origin': True,
                'csrf_protection': True,
                'rate_limiting': True
            }
        }
    
    def _setup_websocket_connection_config(self, page_id: str, config: PageNotificationConfig) -> Dict[str, Any]:
        """
        Setup WebSocket connection configuration for page
        
        Args:
            page_id: Page identifier
            config: Page configuration
            
        Returns:
            Dictionary containing WebSocket configuration
        """
        return {
            'connection_url': self._get_websocket_url(),
            'namespace': config.namespace,
            'transport_options': {
                'transports': ['websocket', 'polling'],
                'upgrade': True,
                'rememberUpgrade': True,
                'forceNew': False
            },
            'auth_config': {
                'send_credentials': True,
                'include_session': True,
                'csrf_token': self._get_csrf_token()
            },
            'error_handling': {
                'retry_on_error': True,
                'max_retries': 5,
                'retry_delay': 1000,
                'exponential_backoff': True
            }
        }
    
    def _register_page_event_handlers(self, page_id: str, page_type: PageType, 
                                    config: PageNotificationConfig) -> Dict[str, Any]:
        """
        Register page-specific event handlers
        
        Args:
            page_id: Page identifier
            page_type: Type of page
            config: Page configuration
            
        Returns:
            Dictionary containing event handler configuration
        """
        handlers = self._get_default_event_handlers(page_type)
        
        return {
            'page_handlers': handlers,
            'global_handlers': {
                'notification': 'handleGlobalNotification',
                'system_notification': 'handleSystemNotification',
                'error': 'handleNotificationError'
            },
            'middleware': [
                'validateNotificationOrigin',
                'checkNotificationPermissions',
                'logNotificationActivity'
            ]
        }
    
    def _setup_notification_ui_config(self, page_id: str, config: PageNotificationConfig) -> Dict[str, Any]:
        """
        Setup notification UI configuration
        
        Args:
            page_id: Page identifier
            config: Page configuration
            
        Returns:
            Dictionary containing UI configuration
        """
        return {
            'container': {
                'id': f'notifications-{page_id}',
                'position': config.position,
                'max_notifications': config.max_notifications,
                'auto_hide': config.auto_hide,
                'show_progress': config.show_progress
            },
            'styling': {
                'theme': 'default',
                'animations': True,
                'transitions': True,
                'responsive': True
            },
            'behavior': {
                'stack_notifications': True,
                'dismiss_on_click': True,
                'pause_on_hover': True,
                'sound_notifications': False
            },
            'accessibility': {
                'screen_reader_support': True,
                'keyboard_navigation': True,
                'high_contrast_mode': False,
                'focus_management': True
            }
        }
    
    def _get_default_event_handlers(self, page_type: PageType) -> Dict[str, str]:
        """
        Get default event handlers for page type
        
        Args:
            page_type: Type of page
            
        Returns:
            Dictionary mapping events to handler function names
        """
        base_handlers = {
            'connect': 'handlePageConnect',
            'disconnect': 'handlePageDisconnect',
            'notification': 'handlePageNotification',
            'error': 'handlePageError'
        }
        
        page_specific_handlers = {
            PageType.USER_DASHBOARD: {
                'caption_progress': 'handleCaptionProgress',
                'platform_status': 'handlePlatformStatus',
                'user_activity': 'handleUserActivity'
            },
            PageType.CAPTION_PROCESSING: {
                'caption_progress': 'handleCaptionProgress',
                'caption_status': 'handleCaptionStatus',
                'caption_complete': 'handleCaptionComplete',
                'caption_error': 'handleCaptionError'
            },
            PageType.PLATFORM_MANAGEMENT: {
                'platform_status': 'handlePlatformStatus',
                'platform_connection': 'handlePlatformConnection',
                'platform_error': 'handlePlatformError'
            },
            PageType.USER_PROFILE: {
                'profile_update': 'handleProfileUpdate',
                'security_notification': 'handleSecurityNotification'
            },
            PageType.ADMIN_DASHBOARD: {
                'system_status': 'handleSystemStatus',
                'admin_notification': 'handleAdminNotification',
                'security_alert': 'handleSecurityAlert',
                'maintenance_status': 'handleMaintenanceStatus'
            },
            PageType.USER_MANAGEMENT: {
                'user_management': 'handleUserManagement',
                'user_status': 'handleUserStatus',
                'security_alert': 'handleSecurityAlert'
            },
            PageType.SYSTEM_HEALTH: {
                'system_status': 'handleSystemStatus',
                'health_metrics': 'handleHealthMetrics',
                'performance_alert': 'handlePerformanceAlert'
            },
            PageType.MAINTENANCE: {
                'maintenance_status': 'handleMaintenanceStatus',
                'maintenance_progress': 'handleMaintenanceProgress'
            },
            PageType.SECURITY_AUDIT: {
                'security_alert': 'handleSecurityAlert',
                'audit_event': 'handleAuditEvent',
                'security_notification': 'handleSecurityNotification'
            }
        }
        
        handlers = base_handlers.copy()
        handlers.update(page_specific_handlers.get(page_type, {}))
        return handlers
    
    def _determine_namespace(self, config: PageNotificationConfig, user_info: Dict[str, Any]) -> str:
        """
        Determine appropriate WebSocket namespace for page
        
        Args:
            config: Page configuration
            user_info: Current user information
            
        Returns:
            WebSocket namespace string
        """
        # Use configured namespace if available
        if config.namespace:
            # Validate user has access to admin namespace
            if config.namespace == '/admin' and user_info.get('role') != 'admin':
                return '/'  # Fall back to user namespace
            return config.namespace
        
        # Default namespace selection based on user role
        if user_info.get('role') == 'admin':
            return '/admin'
        else:
            return '/'
    
    def _get_current_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current user information from session
        
        Returns:
            Dictionary containing user information or None
        """
        try:
            if not session:
                return None
            
            return {
                'user_id': session.get('user_id'),
                'username': session.get('username'),
                'role': session.get('role'),
                'session_id': getattr(session, 'sid', None),
                'permissions': session.get('permissions', set())
            }
            
        except Exception as e:
            self.logger.error(f"Error getting current user info: {e}")
            return None
    
    def _get_websocket_url(self) -> str:
        """
        Get WebSocket connection URL
        
        Returns:
            WebSocket URL string
        """
        try:
            if request:
                scheme = 'wss' if request.is_secure else 'ws'
                host = request.host
                return f"{scheme}://{host}/socket.io/"
            else:
                # Fallback for non-request contexts
                return "/socket.io/"
                
        except Exception as e:
            self.logger.error(f"Error getting WebSocket URL: {e}")
            return "/socket.io/"
    
    def _get_csrf_token(self) -> Optional[str]:
        """
        Get CSRF token for WebSocket authentication
        
        Returns:
            CSRF token string or None
        """
        try:
            return session.get('csrf_token')
        except Exception as e:
            self.logger.error(f"Error getting CSRF token: {e}")
            return None
    
    def _get_current_timestamp(self) -> str:
        """
        Get current timestamp in ISO format
        
        Returns:
            ISO format timestamp string
        """
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active page integrations
        
        Returns:
            Dictionary containing integration statistics
        """
        try:
            stats = {
                'total_integrations': len(self._active_integrations),
                'integrations_by_type': {},
                'integrations_by_namespace': {},
                'initialized_integrations': 0,
                'websocket_configured': 0,
                'websocket_connected': 0
            }
            
            for page_id, integration_info in self._active_integrations.items():
                page_type = integration_info['page_type']
                namespace = integration_info.get('websocket_namespace', 'unknown')
                
                # Count by type
                stats['integrations_by_type'][page_type] = stats['integrations_by_type'].get(page_type, 0) + 1
                
                # Count by namespace
                stats['integrations_by_namespace'][namespace] = stats['integrations_by_namespace'].get(namespace, 0) + 1
                
                # Count status
                if integration_info.get('initialized'):
                    stats['initialized_integrations'] += 1
                if integration_info.get('websocket_configured'):
                    stats['websocket_configured'] += 1
                if integration_info.get('websocket_connected'):
                    stats['websocket_connected'] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting integration stats: {e}")
            return {'error': str(e)}