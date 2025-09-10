# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Status API

Provides real-time maintenance status information for frontend applications.
Supports status queries, operation blocking information, and real-time updates.
"""

import logging
import threading
import time
import uuid
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class MaintenanceStatusResponse:
    """Comprehensive maintenance status response"""
    is_active: bool
    mode: str
    reason: Optional[str]
    estimated_duration: Optional[int]  # Duration in minutes
    started_at: Optional[str]  # ISO format datetime
    estimated_completion: Optional[str]  # ISO format datetime
    enabled_by: Optional[str]
    blocked_operations: List[str]
    active_jobs_count: int
    invalidated_sessions: int
    test_mode: bool
    message: str
    response_time_ms: float
    timestamp: str  # ISO format datetime


@dataclass
class BlockedOperation:
    """Information about a blocked operation"""
    operation_type: str
    description: str
    blocked_since: Optional[str]  # ISO format datetime
    user_message: str
    endpoints: List[str]


class MaintenanceStatusAPI:
    """
    API for real-time maintenance status information
    
    Features:
    - Real-time status queries with <100ms response time
    - Comprehensive status information
    - Operation blocking details
    - Status change subscriptions
    - Performance monitoring
    """
    
    def __init__(self, maintenance_service):
        """
        Initialize maintenance status API
        
        Args:
            maintenance_service: EnhancedMaintenanceModeService instance
        """
        self.maintenance_service = maintenance_service
        
        # Status change subscribers
        self._subscribers: Dict[str, Callable] = {}
        self._subscribers_lock = threading.RLock()
        
        # Performance tracking
        self._performance_stats = {
            'total_requests': 0,
            'average_response_time': 0.0,
            'max_response_time': 0.0,
            'min_response_time': float('inf'),
            'last_request_time': None
        }
        self._stats_lock = threading.RLock()
        
        # Subscribe to maintenance service changes
        self._maintenance_subscription_id = self.maintenance_service.subscribe_to_changes(
            self._handle_maintenance_change
        )
        
        logger.info("Maintenance Status API initialized")
    
    def get_status(self) -> MaintenanceStatusResponse:
        """
        Get comprehensive maintenance status
        
        Returns:
            MaintenanceStatusResponse with current status
        """
        start_time = time.time()
        
        try:
            # Get maintenance status from service
            status = self.maintenance_service.get_maintenance_status()
            
            # Get blocked operations
            blocked_operations = self.maintenance_service.get_blocked_operations()
            
            # Get maintenance message
            message = self.maintenance_service.get_maintenance_message()
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Create response
            response = MaintenanceStatusResponse(
                is_active=status.is_active,
                mode=status.mode.value,
                reason=status.reason,
                estimated_duration=status.estimated_duration,
                started_at=status.started_at.isoformat() if status.started_at else None,
                estimated_completion=status.estimated_completion.isoformat() if status.estimated_completion else None,
                enabled_by=status.enabled_by,
                blocked_operations=blocked_operations,
                active_jobs_count=status.active_jobs_count,
                invalidated_sessions=status.invalidated_sessions,
                test_mode=status.test_mode,
                message=message,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Update performance stats
            self._update_performance_stats(response_time_ms)
            
            logger.debug(f"Status API response generated in {response_time_ms:.2f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Error getting maintenance status: {str(e)}")
            
            # Return error response
            response_time_ms = (time.time() - start_time) * 1000
            return MaintenanceStatusResponse(
                is_active=False,
                mode="unknown",
                reason=None,
                estimated_duration=None,
                started_at=None,
                estimated_completion=None,
                enabled_by=None,
                blocked_operations=[],
                active_jobs_count=0,
                invalidated_sessions=0,
                test_mode=False,
                message="Unable to determine maintenance status",
                response_time_ms=response_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    def get_blocked_operations(self) -> List[BlockedOperation]:
        """
        Get detailed information about blocked operations
        
        Returns:
            List of BlockedOperation objects
        """
        try:
            # Get maintenance status
            status = self.maintenance_service.get_maintenance_status()
            
            if not status.is_active:
                return []
            
            # Import operation classifier
            from app.services.maintenance.components.maintenance_operation_classifier import MaintenanceOperationClassifier, OperationType
            
            classifier = MaintenanceOperationClassifier()
            blocked_operations = []
            
            # Get all operation types and check which are blocked
            for operation_type in OperationType:
                if classifier.is_blocked_operation(operation_type, status.mode):
                    # Get operation description
                    description = classifier.get_operation_description(operation_type)
                    
                    # Get user-friendly message
                    user_message = self.maintenance_service.get_maintenance_message(operation_type.value)
                    
                    # Create blocked operation info
                    blocked_op = BlockedOperation(
                        operation_type=operation_type.value,
                        description=description,
                        blocked_since=status.started_at.isoformat() if status.started_at else None,
                        user_message=user_message,
                        endpoints=self._get_endpoints_for_operation_type(operation_type)
                    )
                    
                    blocked_operations.append(blocked_op)
            
            logger.debug(f"Found {len(blocked_operations)} blocked operation types")
            return blocked_operations
            
        except Exception as e:
            logger.error(f"Error getting blocked operations: {str(e)}")
            return []
    
    def get_maintenance_message(self, operation: Optional[str] = None) -> str:
        """
        Get operation-specific maintenance message
        
        Args:
            operation: Specific operation being blocked (optional)
            
        Returns:
            User-friendly maintenance message
        """
        try:
            return self.maintenance_service.get_maintenance_message(operation)
        except Exception as e:
            logger.error(f"Error getting maintenance message: {str(e)}")
            return "System maintenance is in progress. Please try again later."
    
    def subscribe_to_status_changes(self, callback: Callable[[str, MaintenanceStatusResponse], None]) -> str:
        """
        Subscribe to real-time status changes
        
        Args:
            callback: Callback function (event_type, status_response)
            
        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        
        with self._subscribers_lock:
            self._subscribers[subscription_id] = callback
        
        logger.debug(f"Added status change subscription {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove status change subscription
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was found and removed
        """
        with self._subscribers_lock:
            if subscription_id in self._subscribers:
                del self._subscribers[subscription_id]
                logger.debug(f"Removed status change subscription {subscription_id}")
                return True
        
        return False
    
    def get_api_stats(self) -> Dict[str, Any]:
        """
        Get API performance statistics
        
        Returns:
            Dictionary with API statistics
        """
        with self._stats_lock:
            stats = self._performance_stats.copy()
        
        with self._subscribers_lock:
            subscriber_count = len(self._subscribers)
        
        return {
            'performance': stats,
            'subscribers_count': subscriber_count,
            'maintenance_subscription_active': self._maintenance_subscription_id is not None
        }
    
    def _get_endpoints_for_operation_type(self, operation_type) -> List[str]:
        """
        Get example endpoints for an operation type
        
        Args:
            operation_type: OperationType to get endpoints for
            
        Returns:
            List of example endpoint patterns
        """
        try:
            # Import operation classifier
            from app.services.maintenance.components.maintenance_operation_classifier import MaintenanceOperationClassifier, OperationType
            
            # Map operation types to example endpoints
            endpoint_examples = {
                OperationType.CAPTION_GENERATION: [
                    "/start_caption_generation",
                    "/api/caption/generate",
                    "/generate_caption"
                ],
                OperationType.JOB_CREATION: [
                    "/api/jobs",
                    "/create_job",
                    "/queue_job",
                    "/background_task"
                ],
                OperationType.PLATFORM_OPERATIONS: [
                    "/platform_management",
                    "/api/switch_platform",
                    "/api/test_platform",
                    "/api/add_platform"
                ],
                OperationType.BATCH_OPERATIONS: [
                    "/api/batch_review",
                    "/bulk_operation",
                    "/batch_process",
                    "/review/batches"
                ],
                OperationType.USER_DATA_MODIFICATION: [
                    "/profile_update",
                    "/user_settings",
                    "/password_change",
                    "/api/caption_settings"
                ],
                OperationType.IMAGE_PROCESSING: [
                    "/image_upload",
                    "/api/update_caption",
                    "/api/regenerate_caption",
                    "/image_process"
                ],
                OperationType.ADMIN_OPERATIONS: [
                    "/admin",
                    "/api/admin",
                    "/system_admin",
                    "/maintenance"
                ],
                OperationType.READ_OPERATIONS: [
                    "/api/status",
                    "/static/*",
                    "/images/*",
                    "/api/health"
                ],
                OperationType.AUTHENTICATION: [
                    "/login",
                    "/logout",
                    "/api/auth",
                    "/session"
                ]
            }
            
            return endpoint_examples.get(operation_type, [])
            
        except Exception as e:
            logger.error(f"Error getting endpoints for operation type: {str(e)}")
            return []
    
    def _handle_maintenance_change(self, event_type: str, status):
        """
        Handle maintenance service status changes
        
        Args:
            event_type: Type of change event
            status: MaintenanceStatus object
        """
        try:
            # Convert status to API response format
            status_response = MaintenanceStatusResponse(
                is_active=status.is_active,
                mode=status.mode.value,
                reason=status.reason,
                estimated_duration=status.estimated_duration,
                started_at=status.started_at.isoformat() if status.started_at else None,
                estimated_completion=status.estimated_completion.isoformat() if status.estimated_completion else None,
                enabled_by=status.enabled_by,
                blocked_operations=self.maintenance_service.get_blocked_operations(),
                active_jobs_count=status.active_jobs_count,
                invalidated_sessions=status.invalidated_sessions,
                test_mode=status.test_mode,
                message=self.maintenance_service.get_maintenance_message(),
                response_time_ms=0.0,  # Not applicable for change notifications
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Notify all subscribers
            with self._subscribers_lock:
                for subscription_id, callback in self._subscribers.items():
                    try:
                        callback(event_type, status_response)
                    except Exception as e:
                        logger.error(f"Error in status change callback {subscription_id}: {str(e)}")
            
            logger.debug(f"Notified {len(self._subscribers)} subscribers of maintenance change: {event_type}")
            
        except Exception as e:
            logger.error(f"Error handling maintenance change: {str(e)}")
    
    def _update_performance_stats(self, response_time_ms: float):
        """
        Update API performance statistics
        
        Args:
            response_time_ms: Response time in milliseconds
        """
        with self._stats_lock:
            self._performance_stats['total_requests'] += 1
            self._performance_stats['last_request_time'] = datetime.now(timezone.utc).isoformat()
            
            # Update min/max response times
            if response_time_ms > self._performance_stats['max_response_time']:
                self._performance_stats['max_response_time'] = response_time_ms
            
            if response_time_ms < self._performance_stats['min_response_time']:
                self._performance_stats['min_response_time'] = response_time_ms
            
            # Update average response time (running average)
            total_requests = self._performance_stats['total_requests']
            current_avg = self._performance_stats['average_response_time']
            new_avg = ((current_avg * (total_requests - 1)) + response_time_ms) / total_requests
            self._performance_stats['average_response_time'] = new_avg
    
    def __del__(self):
        """Cleanup subscriptions on destruction"""
        try:
            if hasattr(self, '_maintenance_subscription_id') and self._maintenance_subscription_id:
                self.maintenance_service.unsubscribe(self._maintenance_subscription_id)
        except Exception as e:
            logger.error(f"Error cleaning up maintenance status API: {str(e)}")