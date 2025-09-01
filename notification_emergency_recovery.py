# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification System Emergency Recovery

This module provides emergency recovery mechanisms for critical notification system failures,
including automatic fallback systems, emergency notification delivery, and system restoration
procedures.
"""

import logging
import json
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from flask import flash, current_app
from flask_socketio import emit

from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager
from database import DatabaseManager
from models import NotificationType, NotificationPriority, NotificationCategory

logger = logging.getLogger(__name__)


class EmergencyLevel(Enum):
    """Emergency severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Available recovery actions"""
    RESTART_WEBSOCKET = "restart_websocket"
    FALLBACK_TO_FLASH = "fallback_to_flash"
    EMERGENCY_BROADCAST = "emergency_broadcast"
    DISABLE_NOTIFICATIONS = "disable_notifications"
    RESTORE_FROM_BACKUP = "restore_from_backup"
    MANUAL_INTERVENTION = "manual_intervention"


class FailureType(Enum):
    """Types of notification system failures"""
    WEBSOCKET_CONNECTION_FAILURE = "websocket_connection_failure"
    MESSAGE_DELIVERY_FAILURE = "message_delivery_failure"
    DATABASE_PERSISTENCE_FAILURE = "database_persistence_failure"
    AUTHENTICATION_FAILURE = "authentication_failure"
    NAMESPACE_ROUTING_FAILURE = "namespace_routing_failure"
    MEMORY_OVERFLOW = "memory_overflow"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SYSTEM_OVERLOAD = "system_overload"


@dataclass
class EmergencyEvent:
    """Emergency event record"""
    event_id: str
    timestamp: datetime
    failure_type: FailureType
    emergency_level: EmergencyLevel
    affected_users: List[int]
    error_message: str
    stack_trace: Optional[str]
    recovery_actions: List[RecoveryAction]
    recovery_success: bool
    resolution_time: Optional[datetime]
    manual_intervention_required: bool


@dataclass
class RecoveryPlan:
    """Recovery plan for specific failure types"""
    failure_type: FailureType
    emergency_level: EmergencyLevel
    automatic_actions: List[RecoveryAction]
    manual_actions: List[str]
    escalation_threshold: int  # seconds before escalation
    fallback_enabled: bool


class NotificationEmergencyRecovery:
    """
    Emergency recovery system for notification failures
    
    Provides automatic detection, recovery, and fallback mechanisms for critical
    notification system failures, ensuring users continue to receive important
    notifications even during system issues.
    """
    
    def __init__(self, 
                 notification_manager: UnifiedNotificationManager,
                 websocket_factory: WebSocketFactory,
                 auth_handler: WebSocketAuthHandler,
                 namespace_manager: WebSocketNamespaceManager,
                 db_manager: DatabaseManager,
                 emergency_config: Optional[Dict[str, Any]] = None):
        """
        Initialize emergency recovery system
        
        Args:
            notification_manager: Unified notification manager
            websocket_factory: WebSocket factory instance
            auth_handler: WebSocket authentication handler
            namespace_manager: WebSocket namespace manager
            db_manager: Database manager
            emergency_config: Emergency configuration settings
        """
        self.notification_manager = notification_manager
        self.websocket_factory = websocket_factory
        self.auth_handler = auth_handler
        self.namespace_manager = namespace_manager
        self.db_manager = db_manager
        
        # Emergency configuration
        self.config = emergency_config or self._get_default_config()
        
        # Emergency state tracking
        self._emergency_active = False
        self._emergency_events: List[EmergencyEvent] = []
        self._recovery_plans = self._initialize_recovery_plans()
        
        # Fallback systems
        self._fallback_enabled = True
        self._flash_fallback_enabled = True
        self._emergency_broadcast_enabled = True
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'emergency_events': 0,
            'automatic_recoveries': 0,
            'manual_interventions': 0,
            'fallback_activations': 0,
            'recovery_success_rate': 0.0
        }
        
        # Health monitoring
        self._health_check_interval = 30  # seconds
        self._last_health_check = datetime.now(timezone.utc)
        self._health_status = "healthy"
        
        logger.info("Notification Emergency Recovery system initialized")
    
    def detect_and_recover(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Detect failure and execute recovery procedures
        
        Args:
            error: Exception that occurred
            context: Context information about the failure
            
        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            with self._lock:
                # Classify the failure
                failure_type = self._classify_failure(error, context)
                emergency_level = self._assess_emergency_level(failure_type, context)
                
                # Create emergency event
                event = self._create_emergency_event(
                    failure_type, emergency_level, error, context
                )
                
                self._emergency_events.append(event)
                self._stats['emergency_events'] += 1
                
                logger.error(f"Emergency detected: {failure_type.value} (Level: {emergency_level.value})")
                
                # Execute recovery plan
                recovery_success = self._execute_recovery_plan(event)
                
                # Update event with recovery result
                event.recovery_success = recovery_success
                event.resolution_time = datetime.now(timezone.utc)
                
                if recovery_success:
                    self._stats['automatic_recoveries'] += 1
                    logger.info(f"Emergency recovery successful for event {event.event_id}")
                else:
                    self._stats['manual_interventions'] += 1
                    logger.error(f"Emergency recovery failed for event {event.event_id}")
                    
                    # Escalate if necessary
                    self._escalate_emergency(event)
                
                # Update success rate
                self._update_success_rate()
                
                return recovery_success
                
        except Exception as e:
            logger.error(f"Failed to execute emergency recovery: {e}")
            return False
    
    def activate_emergency_mode(self, reason: str, triggered_by: str) -> bool:
        """
        Activate emergency mode with fallback systems
        
        Args:
            reason: Reason for emergency activation
            triggered_by: Who/what triggered the emergency
            
        Returns:
            True if activated successfully, False otherwise
        """
        try:
            with self._lock:
                if self._emergency_active:
                    logger.warning("Emergency mode already active")
                    return True
                
                self._emergency_active = True
                
                logger.critical(f"EMERGENCY MODE ACTIVATED: {reason} (by {triggered_by})")
                
                # Activate all fallback systems
                self._activate_fallback_systems()
                
                # Send emergency notification to all admins
                self._send_emergency_notification(
                    "Emergency Mode Activated",
                    f"Notification system emergency mode has been activated. Reason: {reason}",
                    {"reason": reason, "triggered_by": triggered_by}
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to activate emergency mode: {e}")
            return False
    
    def deactivate_emergency_mode(self, resolved_by: str) -> bool:
        """
        Deactivate emergency mode and restore normal operations
        
        Args:
            resolved_by: Who resolved the emergency
            
        Returns:
            True if deactivated successfully, False otherwise
        """
        try:
            with self._lock:
                if not self._emergency_active:
                    logger.warning("Emergency mode not active")
                    return True
                
                # Attempt to restore normal operations
                restoration_success = self._restore_normal_operations()
                
                if restoration_success:
                    self._emergency_active = False
                    
                    logger.info(f"Emergency mode deactivated by {resolved_by}")
                    
                    # Send recovery notification to admins
                    self._send_emergency_notification(
                        "Emergency Mode Deactivated",
                        f"Notification system has been restored to normal operations by {resolved_by}",
                        {"resolved_by": resolved_by, "restoration_success": True}
                    )
                    
                    return True
                else:
                    logger.error("Failed to restore normal operations")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to deactivate emergency mode: {e}")
            return False
    
    def send_emergency_notification(self, title: str, message: str, 
                                  target_users: Optional[List[int]] = None) -> bool:
        """
        Send emergency notification using all available channels
        
        Args:
            title: Notification title
            message: Notification message
            target_users: Specific users to notify (None for all admins)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            success = False
            
            # Try WebSocket delivery first
            try:
                emergency_msg = AdminNotificationMessage(
                    id=f"emergency_{int(time.time())}",
                    type=NotificationType.ERROR,
                    title=title,
                    message=message,
                    priority=NotificationPriority.CRITICAL,
                    category=NotificationCategory.ADMIN,
                    requires_admin_action=True
                )
                
                if target_users:
                    for user_id in target_users:
                        if self.notification_manager.send_user_notification(user_id, emergency_msg):
                            success = True
                else:
                    if self.notification_manager.send_admin_notification(emergency_msg):
                        success = True
                        
            except Exception as e:
                logger.error(f"WebSocket emergency notification failed: {e}")
            
            # Fallback to Flask flash messages
            if not success and self._flash_fallback_enabled:
                try:
                    flash(f"EMERGENCY: {title} - {message}", "error")
                    success = True
                    logger.info("Emergency notification sent via Flask flash fallback")
                except Exception as e:
                    logger.error(f"Flash fallback failed: {e}")
            
            # Log emergency notification attempt
            if success:
                logger.info(f"Emergency notification sent: {title}")
            else:
                logger.error(f"All emergency notification channels failed: {title}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send emergency notification: {e}")
            return False
    
    def get_emergency_status(self) -> Dict[str, Any]:
        """
        Get current emergency system status
        
        Returns:
            Dictionary containing emergency system status
        """
        try:
            with self._lock:
                recent_events = [
                    {
                        'event_id': event.event_id,
                        'timestamp': event.timestamp.isoformat(),
                        'failure_type': event.failure_type.value,
                        'emergency_level': event.emergency_level.value,
                        'recovery_success': event.recovery_success,
                        'manual_intervention_required': event.manual_intervention_required
                    }
                    for event in self._emergency_events[-10:]  # Last 10 events
                ]
                
                return {
                    'emergency_active': self._emergency_active,
                    'health_status': self._health_status,
                    'last_health_check': self._last_health_check.isoformat(),
                    'fallback_systems': {
                        'fallback_enabled': self._fallback_enabled,
                        'flash_fallback_enabled': self._flash_fallback_enabled,
                        'emergency_broadcast_enabled': self._emergency_broadcast_enabled
                    },
                    'statistics': self._stats,
                    'recent_events': recent_events,
                    'recovery_plans_count': len(self._recovery_plans)
                }
                
        except Exception as e:
            logger.error(f"Failed to get emergency status: {e}")
            return {'error': str(e)}
    
    def run_health_check(self) -> Dict[str, Any]:
        """
        Run comprehensive health check of notification system
        
        Returns:
            Health check results
        """
        try:
            health_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_status': 'healthy',
                'components': {},
                'issues': [],
                'recommendations': []
            }
            
            # Check WebSocket factory
            try:
                if self.websocket_factory and hasattr(self.websocket_factory, 'health_check'):
                    ws_health = self.websocket_factory.health_check()
                    health_results['components']['websocket_factory'] = ws_health
                else:
                    health_results['components']['websocket_factory'] = {'status': 'unknown'}
            except Exception as e:
                health_results['components']['websocket_factory'] = {'status': 'error', 'error': str(e)}
                health_results['issues'].append(f"WebSocket factory health check failed: {e}")
            
            # Check notification manager
            try:
                if hasattr(self.notification_manager, 'get_notification_stats'):
                    notif_stats = self.notification_manager.get_notification_stats()
                    health_results['components']['notification_manager'] = {
                        'status': 'healthy',
                        'stats': notif_stats
                    }
                else:
                    health_results['components']['notification_manager'] = {'status': 'unknown'}
            except Exception as e:
                health_results['components']['notification_manager'] = {'status': 'error', 'error': str(e)}
                health_results['issues'].append(f"Notification manager health check failed: {e}")
            
            # Check database connectivity
            try:
                with self.db_manager.get_session() as session:
                    session.execute("SELECT 1")
                    health_results['components']['database'] = {'status': 'healthy'}
            except Exception as e:
                health_results['components']['database'] = {'status': 'error', 'error': str(e)}
                health_results['issues'].append(f"Database connectivity failed: {e}")
            
            # Determine overall status
            if health_results['issues']:
                if len(health_results['issues']) >= 2:
                    health_results['overall_status'] = 'critical'
                else:
                    health_results['overall_status'] = 'degraded'
            
            # Update internal health status
            self._health_status = health_results['overall_status']
            self._last_health_check = datetime.now(timezone.utc)
            
            return health_results
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_status': 'error',
                'error': str(e)
            }
    
    def _classify_failure(self, error: Exception, context: Dict[str, Any]) -> FailureType:
        """Classify the type of failure based on error and context"""
        error_str = str(error).lower()
        
        if 'websocket' in error_str or 'connection' in error_str:
            return FailureType.WEBSOCKET_CONNECTION_FAILURE
        elif 'delivery' in error_str or 'emit' in error_str:
            return FailureType.MESSAGE_DELIVERY_FAILURE
        elif 'database' in error_str or 'sql' in error_str:
            return FailureType.DATABASE_PERSISTENCE_FAILURE
        elif 'auth' in error_str or 'permission' in error_str:
            return FailureType.AUTHENTICATION_FAILURE
        elif 'namespace' in error_str or 'routing' in error_str:
            return FailureType.NAMESPACE_ROUTING_FAILURE
        elif 'memory' in error_str or 'overflow' in error_str:
            return FailureType.MEMORY_OVERFLOW
        elif 'rate limit' in error_str or 'throttle' in error_str:
            return FailureType.RATE_LIMIT_EXCEEDED
        else:
            return FailureType.SYSTEM_OVERLOAD
    
    def _assess_emergency_level(self, failure_type: FailureType, context: Dict[str, Any]) -> EmergencyLevel:
        """Assess the emergency level based on failure type and context"""
        affected_users_raw = context.get('affected_users', 0)
        
        # Handle both integer count and list of user IDs
        if isinstance(affected_users_raw, list):
            affected_users_count = len(affected_users_raw)
        else:
            affected_users_count = affected_users_raw
        
        # Critical failures
        if failure_type in [FailureType.SYSTEM_OVERLOAD, FailureType.MEMORY_OVERFLOW]:
            return EmergencyLevel.CRITICAL
        
        # High priority failures
        if failure_type in [FailureType.WEBSOCKET_CONNECTION_FAILURE, FailureType.DATABASE_PERSISTENCE_FAILURE]:
            if affected_users_count > 10:
                return EmergencyLevel.HIGH
            else:
                return EmergencyLevel.MEDIUM
        
        # Medium priority failures
        if failure_type in [FailureType.MESSAGE_DELIVERY_FAILURE, FailureType.NAMESPACE_ROUTING_FAILURE]:
            return EmergencyLevel.MEDIUM
        
        # Low priority failures
        return EmergencyLevel.LOW
    
    def _create_emergency_event(self, failure_type: FailureType, emergency_level: EmergencyLevel,
                              error: Exception, context: Dict[str, Any]) -> EmergencyEvent:
        """Create an emergency event record"""
        import traceback
        
        return EmergencyEvent(
            event_id=f"emergency_{int(time.time())}_{len(self._emergency_events)}",
            timestamp=datetime.now(timezone.utc),
            failure_type=failure_type,
            emergency_level=emergency_level,
            affected_users=context.get('affected_users', []),
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            recovery_actions=[],
            recovery_success=False,
            resolution_time=None,
            manual_intervention_required=False
        )
    
    def _execute_recovery_plan(self, event: EmergencyEvent) -> bool:
        """Execute recovery plan for the emergency event"""
        try:
            recovery_plan = self._recovery_plans.get(event.failure_type)
            if not recovery_plan:
                logger.error(f"No recovery plan found for {event.failure_type.value}")
                return False
            
            success = True
            
            # Execute automatic recovery actions
            for action in recovery_plan.automatic_actions:
                try:
                    action_success = self._execute_recovery_action(action, event)
                    event.recovery_actions.append(action)
                    
                    if not action_success:
                        success = False
                        logger.error(f"Recovery action {action.value} failed")
                    else:
                        logger.info(f"Recovery action {action.value} succeeded")
                        
                except Exception as e:
                    logger.error(f"Recovery action {action.value} threw exception: {e}")
                    success = False
            
            # Check if manual intervention is required
            if not success or event.emergency_level == EmergencyLevel.CRITICAL:
                event.manual_intervention_required = True
                logger.warning(f"Manual intervention required for event {event.event_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to execute recovery plan: {e}")
            return False
    
    def _execute_recovery_action(self, action: RecoveryAction, event: EmergencyEvent) -> bool:
        """Execute a specific recovery action"""
        try:
            if action == RecoveryAction.RESTART_WEBSOCKET:
                return self._restart_websocket_connections()
            elif action == RecoveryAction.FALLBACK_TO_FLASH:
                return self._activate_flash_fallback()
            elif action == RecoveryAction.EMERGENCY_BROADCAST:
                return self._send_emergency_broadcast(event)
            elif action == RecoveryAction.DISABLE_NOTIFICATIONS:
                return self._disable_notifications_temporarily()
            elif action == RecoveryAction.RESTORE_FROM_BACKUP:
                return self._restore_from_backup()
            elif action == RecoveryAction.MANUAL_INTERVENTION:
                return self._request_manual_intervention(event)
            else:
                logger.error(f"Unknown recovery action: {action.value}")
                return False
                
        except Exception as e:
            logger.error(f"Recovery action {action.value} failed: {e}")
            return False
    
    def _restart_websocket_connections(self) -> bool:
        """Restart WebSocket connections"""
        try:
            # This would restart the WebSocket factory if supported
            if hasattr(self.websocket_factory, 'restart'):
                return self.websocket_factory.restart()
            else:
                logger.warning("WebSocket factory does not support restart")
                return False
        except Exception as e:
            logger.error(f"Failed to restart WebSocket connections: {e}")
            return False
    
    def _activate_flash_fallback(self) -> bool:
        """Activate Flask flash message fallback"""
        try:
            self._flash_fallback_enabled = True
            self._stats['fallback_activations'] += 1
            logger.info("Flask flash fallback activated")
            return True
        except Exception as e:
            logger.error(f"Failed to activate flash fallback: {e}")
            return False
    
    def _send_emergency_broadcast(self, event: EmergencyEvent) -> bool:
        """Send emergency broadcast to all users"""
        try:
            return self.send_emergency_notification(
                "System Alert",
                f"Notification system is experiencing issues. Emergency level: {event.emergency_level.value}",
                None
            )
        except Exception as e:
            logger.error(f"Failed to send emergency broadcast: {e}")
            return False
    
    def _disable_notifications_temporarily(self) -> bool:
        """Temporarily disable notifications to prevent further issues"""
        try:
            # This would disable the notification manager if supported
            if hasattr(self.notification_manager, 'disable'):
                return self.notification_manager.disable()
            else:
                logger.warning("Notification manager does not support disable")
                return False
        except Exception as e:
            logger.error(f"Failed to disable notifications: {e}")
            return False
    
    def _restore_from_backup(self) -> bool:
        """Restore notification system from backup"""
        try:
            # This would restore from backup if supported
            logger.warning("Backup restoration not implemented")
            return False
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False
    
    def _request_manual_intervention(self, event: EmergencyEvent) -> bool:
        """Request manual intervention for the emergency"""
        try:
            # Send alert to administrators
            return self.send_emergency_notification(
                "Manual Intervention Required",
                f"Emergency event {event.event_id} requires manual intervention. "
                f"Failure type: {event.failure_type.value}",
                None
            )
        except Exception as e:
            logger.error(f"Failed to request manual intervention: {e}")
            return False
    
    def _activate_fallback_systems(self) -> None:
        """Activate all fallback systems"""
        self._fallback_enabled = True
        self._flash_fallback_enabled = True
        self._emergency_broadcast_enabled = True
        logger.info("All fallback systems activated")
    
    def _restore_normal_operations(self) -> bool:
        """Restore normal notification operations"""
        try:
            # Run health check to verify system status
            health_results = self.run_health_check()
            
            if health_results['overall_status'] == 'healthy':
                # Deactivate fallback systems
                self._fallback_enabled = False
                self._flash_fallback_enabled = False
                
                logger.info("Normal operations restored")
                return True
            else:
                logger.error("System not healthy enough to restore normal operations")
                return False
                
        except Exception as e:
            logger.error(f"Failed to restore normal operations: {e}")
            return False
    
    def _send_emergency_notification(self, title: str, message: str, data: Dict[str, Any]) -> None:
        """Send emergency notification to administrators"""
        try:
            self.send_emergency_notification(title, message, None)
        except Exception as e:
            logger.error(f"Failed to send emergency notification: {e}")
    
    def _escalate_emergency(self, event: EmergencyEvent) -> None:
        """Escalate emergency to higher level support"""
        try:
            self.send_emergency_notification(
                "Emergency Escalation Required",
                f"Emergency event {event.event_id} could not be automatically resolved. "
                f"Failure type: {event.failure_type.value}, Level: {event.emergency_level.value}",
                None
            )
            logger.critical(f"Emergency escalated: {event.event_id}")
        except Exception as e:
            logger.error(f"Failed to escalate emergency: {e}")
    
    def _update_success_rate(self) -> None:
        """Update recovery success rate statistics"""
        if self._emergency_events:
            successful_recoveries = sum(1 for event in self._emergency_events if event.recovery_success)
            self._stats['recovery_success_rate'] = successful_recoveries / len(self._emergency_events)
    
    def _initialize_recovery_plans(self) -> Dict[FailureType, RecoveryPlan]:
        """Initialize recovery plans for different failure types"""
        return {
            FailureType.WEBSOCKET_CONNECTION_FAILURE: RecoveryPlan(
                failure_type=FailureType.WEBSOCKET_CONNECTION_FAILURE,
                emergency_level=EmergencyLevel.HIGH,
                automatic_actions=[RecoveryAction.RESTART_WEBSOCKET, RecoveryAction.FALLBACK_TO_FLASH],
                manual_actions=["Check network connectivity", "Restart application server"],
                escalation_threshold=300,  # 5 minutes
                fallback_enabled=True
            ),
            FailureType.MESSAGE_DELIVERY_FAILURE: RecoveryPlan(
                failure_type=FailureType.MESSAGE_DELIVERY_FAILURE,
                emergency_level=EmergencyLevel.MEDIUM,
                automatic_actions=[RecoveryAction.FALLBACK_TO_FLASH, RecoveryAction.EMERGENCY_BROADCAST],
                manual_actions=["Check WebSocket namespace configuration", "Verify user permissions"],
                escalation_threshold=180,  # 3 minutes
                fallback_enabled=True
            ),
            FailureType.DATABASE_PERSISTENCE_FAILURE: RecoveryPlan(
                failure_type=FailureType.DATABASE_PERSISTENCE_FAILURE,
                emergency_level=EmergencyLevel.HIGH,
                automatic_actions=[RecoveryAction.FALLBACK_TO_FLASH],
                manual_actions=["Check database connectivity", "Verify database permissions"],
                escalation_threshold=120,  # 2 minutes
                fallback_enabled=True
            ),
            FailureType.SYSTEM_OVERLOAD: RecoveryPlan(
                failure_type=FailureType.SYSTEM_OVERLOAD,
                emergency_level=EmergencyLevel.CRITICAL,
                automatic_actions=[RecoveryAction.DISABLE_NOTIFICATIONS, RecoveryAction.MANUAL_INTERVENTION],
                manual_actions=["Scale up resources", "Investigate system load"],
                escalation_threshold=60,  # 1 minute
                fallback_enabled=True
            )
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default emergency configuration"""
        return {
            'health_check_interval': 30,
            'max_emergency_events': 100,
            'auto_recovery_enabled': True,
            'fallback_systems_enabled': True,
            'emergency_broadcast_enabled': True,
            'escalation_enabled': True
        }