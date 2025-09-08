# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Responsiveness Error Recovery System

This module enhances existing error handling components with responsiveness recovery
mechanisms, including connection recovery, memory cleanup, and automated recovery procedures.
"""

import logging
import time
import asyncio
import gc
from typing import Dict, Any, Optional, Callable, List, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from enhanced_error_recovery_manager import EnhancedErrorRecoveryManager, EnhancedErrorCategory, EscalationLevel
from notification_helpers import send_admin_notification, send_system_notification
from models import NotificationType, NotificationPriority

logger = logging.getLogger(__name__)

class ResponsivenessIssueType(Enum):
    """Types of responsiveness issues"""
    CONNECTION_LEAK = "connection_leak"
    MEMORY_LEAK = "memory_leak"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    SLOW_RESPONSE = "slow_response"
    BLOCKING_OPERATION = "blocking_operation"
    SYSTEM_OVERLOAD = "system_overload"

@dataclass
class ResponsivenessRecoveryAction:
    """Recovery action for responsiveness issues"""
    action_type: str
    description: str
    priority: int
    estimated_duration: int  # seconds
    requires_admin: bool = False
    automatic: bool = True

class ResponsivenessErrorRecoveryManager(EnhancedErrorRecoveryManager):
    """Enhanced error recovery manager with responsiveness recovery capabilities"""
    
    def __init__(self, db_manager=None, system_optimizer=None):
        super().__init__()
        self.db_manager = db_manager
        self.system_optimizer = system_optimizer
        
        # Responsiveness recovery configuration
        self.recovery_actions = self._initialize_recovery_actions()
        self.recovery_history = []
        self.active_recoveries = {}
        
        # Performance thresholds for recovery triggers
        self.performance_thresholds = {
            'memory_critical': 0.9,  # 90%
            'cpu_critical': 0.9,     # 90%
            'connection_pool_critical': 0.9,  # 90%
            'response_time_critical': 10.0,   # 10 seconds
            'request_queue_critical': 100     # 100 queued requests
        }
        
        # Recovery statistics
        self.recovery_stats = {
            'total_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'automatic_recoveries': 0,
            'manual_recoveries': 0
        }
    
    def _initialize_recovery_actions(self) -> Dict[ResponsivenessIssueType, List[ResponsivenessRecoveryAction]]:
        """Initialize recovery actions for different responsiveness issues"""
        return {
            ResponsivenessIssueType.CONNECTION_LEAK: [
                ResponsivenessRecoveryAction(
                    action_type="detect_connection_leaks",
                    description="Detect and cleanup connection leaks",
                    priority=1,
                    estimated_duration=30,
                    automatic=True
                ),
                ResponsivenessRecoveryAction(
                    action_type="force_connection_cleanup",
                    description="Force cleanup of long-lived connections",
                    priority=2,
                    estimated_duration=60,
                    automatic=True
                ),
                ResponsivenessRecoveryAction(
                    action_type="restart_connection_pool",
                    description="Restart database connection pool",
                    priority=3,
                    estimated_duration=120,
                    requires_admin=True,
                    automatic=False
                )
            ],
            ResponsivenessIssueType.MEMORY_LEAK: [
                ResponsivenessRecoveryAction(
                    action_type="force_garbage_collection",
                    description="Force Python garbage collection",
                    priority=1,
                    estimated_duration=10,
                    automatic=True
                ),
                ResponsivenessRecoveryAction(
                    action_type="cleanup_session_cache",
                    description="Clear session and cache data",
                    priority=2,
                    estimated_duration=30,
                    automatic=True
                ),
                ResponsivenessRecoveryAction(
                    action_type="restart_background_tasks",
                    description="Restart background cleanup tasks",
                    priority=3,
                    estimated_duration=60,
                    automatic=True
                )
            ],
            ResponsivenessIssueType.RESOURCE_EXHAUSTION: [
                ResponsivenessRecoveryAction(
                    action_type="emergency_cleanup",
                    description="Emergency system resource cleanup",
                    priority=1,
                    estimated_duration=60,
                    automatic=True
                ),
                ResponsivenessRecoveryAction(
                    action_type="throttle_requests",
                    description="Temporarily throttle incoming requests",
                    priority=2,
                    estimated_duration=300,
                    automatic=True
                ),
                ResponsivenessRecoveryAction(
                    action_type="enable_maintenance_mode",
                    description="Enable maintenance mode to reduce load",
                    priority=3,
                    estimated_duration=600,
                    requires_admin=True,
                    automatic=False
                )
            ],
            ResponsivenessIssueType.SLOW_RESPONSE: [
                ResponsivenessRecoveryAction(
                    action_type="optimize_database_queries",
                    description="Optimize slow database queries",
                    priority=1,
                    estimated_duration=30,
                    automatic=True
                ),
                ResponsivenessRecoveryAction(
                    action_type="clear_request_queue",
                    description="Clear backed up request queue",
                    priority=2,
                    estimated_duration=60,
                    automatic=True
                )
            ],
            ResponsivenessIssueType.BLOCKING_OPERATION: [
                ResponsivenessRecoveryAction(
                    action_type="identify_blocking_operations",
                    description="Identify and terminate blocking operations",
                    priority=1,
                    estimated_duration=30,
                    automatic=True
                ),
                ResponsivenessRecoveryAction(
                    action_type="restart_background_threads",
                    description="Restart blocked background threads",
                    priority=2,
                    estimated_duration=60,
                    automatic=True
                )
            ],
            ResponsivenessIssueType.SYSTEM_OVERLOAD: [
                ResponsivenessRecoveryAction(
                    action_type="reduce_system_load",
                    description="Reduce system load through optimization",
                    priority=1,
                    estimated_duration=120,
                    automatic=True
                ),
                ResponsivenessRecoveryAction(
                    action_type="emergency_shutdown_non_critical",
                    description="Shutdown non-critical services",
                    priority=2,
                    estimated_duration=180,
                    requires_admin=True,
                    automatic=False
                )
            ]
        }
    
    async def handle_database_connection_recovery(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle database connection errors with recovery mechanisms"""
        recovery_result = {
            'success': False,
            'actions_taken': [],
            'recovery_time': 0,
            'error_resolved': False,
            'admin_notification_sent': False
        }
        
        start_time = time.time()
        
        try:
            logger.info("Starting database connection recovery")
            
            # Step 1: Detect connection leaks
            if self.db_manager:
                leak_cleanup_result = self.db_manager.detect_and_cleanup_connection_leaks()
                recovery_result['actions_taken'].append({
                    'action': 'connection_leak_cleanup',
                    'result': leak_cleanup_result,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                if leak_cleanup_result.get('cleaned_sessions', 0) > 0:
                    logger.info(f"Cleaned up {leak_cleanup_result['cleaned_sessions']} leaked connections")
            
            # Step 2: Check connection pool health
            if self.db_manager:
                health_report = self.db_manager.monitor_connection_health()
                recovery_result['actions_taken'].append({
                    'action': 'connection_health_check',
                    'result': health_report,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                # If connection pool is critical, attempt recovery
                if health_report.get('overall_health') == 'CRITICAL':
                    await self._attempt_connection_pool_recovery()
                    recovery_result['actions_taken'].append({
                        'action': 'connection_pool_recovery',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            # Step 3: Test connection after recovery
            connection_test_passed = await self._test_database_connection()
            recovery_result['error_resolved'] = connection_test_passed
            
            if connection_test_passed:
                recovery_result['success'] = True
                logger.info("Database connection recovery successful")
                
                # Send success notification to admins
                await send_admin_notification(
                    message="Database connection recovery completed successfully",
                    notification_type=NotificationType.SUCCESS,
                    title="Connection Recovery Success",
                    priority=NotificationPriority.NORMAL
                )
            else:
                # Recovery failed, escalate to admin
                await self._escalate_connection_recovery_failure(error, recovery_result)
                recovery_result['admin_notification_sent'] = True
            
        except Exception as recovery_error:
            logger.error(f"Database connection recovery failed: {recovery_error}")
            recovery_result['actions_taken'].append({
                'action': 'recovery_error',
                'error': str(recovery_error),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Escalate recovery failure
            await self._escalate_connection_recovery_failure(recovery_error, recovery_result)
            recovery_result['admin_notification_sent'] = True
        
        finally:
            recovery_result['recovery_time'] = time.time() - start_time
            self.recovery_history.append({
                'type': 'database_connection_recovery',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'result': recovery_result
            })
            
            # Update recovery statistics
            self.recovery_stats['total_recoveries'] += 1
            if recovery_result['success']:
                self.recovery_stats['successful_recoveries'] += 1
            else:
                self.recovery_stats['failed_recoveries'] += 1
            self.recovery_stats['automatic_recoveries'] += 1
        
        return recovery_result
    
    async def handle_session_memory_cleanup_recovery(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle session memory errors with cleanup recovery"""
        recovery_result = {
            'success': False,
            'actions_taken': [],
            'recovery_time': 0,
            'memory_freed_mb': 0,
            'sessions_cleaned': 0
        }
        
        start_time = time.time()
        
        try:
            logger.info("Starting session memory cleanup recovery")
            
            # Step 1: Force garbage collection
            initial_memory = self._get_memory_usage_mb()
            gc.collect()
            post_gc_memory = self._get_memory_usage_mb()
            memory_freed_gc = initial_memory - post_gc_memory
            
            recovery_result['actions_taken'].append({
                'action': 'garbage_collection',
                'memory_freed_mb': memory_freed_gc,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Step 2: Clean up expired sessions
            sessions_cleaned = await self._cleanup_expired_sessions()
            recovery_result['sessions_cleaned'] = sessions_cleaned
            recovery_result['actions_taken'].append({
                'action': 'session_cleanup',
                'sessions_cleaned': sessions_cleaned,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Step 3: Clear application caches
            cache_cleanup_result = await self._clear_application_caches()
            recovery_result['actions_taken'].append({
                'action': 'cache_cleanup',
                'result': cache_cleanup_result,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Step 4: Check memory usage after cleanup
            final_memory = self._get_memory_usage_mb()
            total_memory_freed = initial_memory - final_memory
            recovery_result['memory_freed_mb'] = total_memory_freed
            
            # Determine if recovery was successful
            memory_usage_percent = self._get_memory_usage_percent()
            if memory_usage_percent < self.performance_thresholds['memory_critical']:
                recovery_result['success'] = True
                logger.info(f"Session memory cleanup recovery successful - freed {total_memory_freed:.1f}MB")
                
                # Send success notification
                await send_admin_notification(
                    message=f"Memory cleanup recovery completed - freed {total_memory_freed:.1f}MB, cleaned {sessions_cleaned} sessions",
                    notification_type=NotificationType.SUCCESS,
                    title="Memory Recovery Success",
                    priority=NotificationPriority.NORMAL
                )
            else:
                logger.warning(f"Session memory cleanup recovery insufficient - memory still at {memory_usage_percent:.1f}%")
                await self._escalate_memory_recovery_failure(error, recovery_result)
        
        except Exception as recovery_error:
            logger.error(f"Session memory cleanup recovery failed: {recovery_error}")
            recovery_result['actions_taken'].append({
                'action': 'recovery_error',
                'error': str(recovery_error),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            await self._escalate_memory_recovery_failure(recovery_error, recovery_result)
        
        finally:
            recovery_result['recovery_time'] = time.time() - start_time
            self.recovery_history.append({
                'type': 'session_memory_cleanup_recovery',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'result': recovery_result
            })
            
            # Update recovery statistics
            self.recovery_stats['total_recoveries'] += 1
            if recovery_result['success']:
                self.recovery_stats['successful_recoveries'] += 1
            else:
                self.recovery_stats['failed_recoveries'] += 1
            self.recovery_stats['automatic_recoveries'] += 1
        
        return recovery_result
    
    async def integrate_with_admin_alerts(self, recovery_result: Dict[str, Any], issue_type: ResponsivenessIssueType) -> bool:
        """Integrate responsiveness recovery with existing admin alert systems"""
        try:
            # Determine notification type and priority based on recovery success
            if recovery_result['success']:
                notification_type = NotificationType.SUCCESS
                priority = NotificationPriority.NORMAL
                title = f"Responsiveness Recovery Success - {issue_type.value.replace('_', ' ').title()}"
                message = f"Automatic recovery completed successfully for {issue_type.value.replace('_', ' ')} issue"
            else:
                notification_type = NotificationType.ERROR
                priority = NotificationPriority.HIGH
                title = f"Responsiveness Recovery Failed - {issue_type.value.replace('_', ' ').title()}"
                message = f"Automatic recovery failed for {issue_type.value.replace('_', ' ')} issue - manual intervention required"
            
            # Add recovery details to message
            actions_summary = []
            for action in recovery_result.get('actions_taken', []):
                actions_summary.append(f"• {action.get('action', 'unknown').replace('_', ' ').title()}")
            
            if actions_summary:
                message += f"\n\nActions taken:\n" + "\n".join(actions_summary)
            
            # Add recovery time and statistics
            recovery_time = recovery_result.get('recovery_time', 0)
            message += f"\n\nRecovery time: {recovery_time:.1f} seconds"
            
            if 'memory_freed_mb' in recovery_result:
                message += f"\nMemory freed: {recovery_result['memory_freed_mb']:.1f}MB"
            
            if 'sessions_cleaned' in recovery_result:
                message += f"\nSessions cleaned: {recovery_result['sessions_cleaned']}"
            
            # Send admin notification
            success = await send_admin_notification(
                message=message,
                notification_type=notification_type,
                title=title,
                priority=priority,
                system_health_data={
                    'recovery_type': issue_type.value,
                    'recovery_success': recovery_result['success'],
                    'recovery_time': recovery_time,
                    'actions_taken': len(recovery_result.get('actions_taken', [])),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                requires_admin_action=not recovery_result['success']
            )
            
            if success:
                logger.info(f"Admin notification sent for {issue_type.value} recovery")
            else:
                logger.warning(f"Failed to send admin notification for {issue_type.value} recovery")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to integrate with admin alerts: {e}")
            return False
    
    async def extend_health_check_error_handling(self, health_check_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extend existing health check error handling with responsiveness recovery status"""
        try:
            # Add responsiveness recovery status to health check
            recovery_status = {
                'recovery_system_active': True,
                'total_recoveries': self.recovery_stats['total_recoveries'],
                'successful_recoveries': self.recovery_stats['successful_recoveries'],
                'recovery_success_rate': 0.0,
                'active_recoveries': len(self.active_recoveries),
                'recent_recovery_history': []
            }
            
            # Calculate success rate
            if self.recovery_stats['total_recoveries'] > 0:
                recovery_status['recovery_success_rate'] = (
                    self.recovery_stats['successful_recoveries'] / 
                    self.recovery_stats['total_recoveries']
                )
            
            # Add recent recovery history (last 10)
            recent_recoveries = self.recovery_history[-10:] if self.recovery_history else []
            for recovery in recent_recoveries:
                recovery_status['recent_recovery_history'].append({
                    'type': recovery['type'],
                    'timestamp': recovery['timestamp'],
                    'success': recovery['result'].get('success', False),
                    'recovery_time': recovery['result'].get('recovery_time', 0)
                })
            
            # Determine overall responsiveness health status
            responsiveness_health = 'healthy'
            responsiveness_issues = []
            
            # Check for active recovery operations
            if self.active_recoveries:
                responsiveness_health = 'recovering'
                responsiveness_issues.append(f"{len(self.active_recoveries)} active recovery operations")
            
            # Check recovery success rate
            if recovery_status['recovery_success_rate'] < 0.8 and self.recovery_stats['total_recoveries'] >= 5:
                responsiveness_health = 'degraded'
                responsiveness_issues.append(f"Low recovery success rate: {recovery_status['recovery_success_rate']:.1f}")
            
            # Check for recent recovery failures
            recent_failures = [r for r in recent_recoveries if not r['result'].get('success', False)]
            if len(recent_failures) >= 3:
                responsiveness_health = 'degraded'
                responsiveness_issues.append(f"{len(recent_failures)} recent recovery failures")
            
            # Add responsiveness status to health check result
            health_check_result['responsiveness_recovery'] = {
                'status': responsiveness_health,
                'issues': responsiveness_issues,
                'recovery_stats': recovery_status,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            # Update overall health status if responsiveness is degraded
            if responsiveness_health == 'degraded' and health_check_result.get('overall_health') == 'HEALTHY':
                health_check_result['overall_health'] = 'WARNING'
                health_check_result['issues'].extend(responsiveness_issues)
                health_check_result['recommendations'].append(
                    "Monitor responsiveness recovery system - multiple recovery failures detected"
                )
            elif responsiveness_health == 'recovering':
                health_check_result['recommendations'].append(
                    f"Responsiveness recovery in progress - {len(self.active_recoveries)} active operations"
                )
            
            return health_check_result
            
        except Exception as e:
            logger.error(f"Failed to extend health check with responsiveness recovery status: {e}")
            # Return original health check result if extension fails
            return health_check_result
    
    async def _attempt_connection_pool_recovery(self) -> bool:
        """Attempt to recover connection pool issues"""
        try:
            if not self.db_manager:
                return False
            
            # Force cleanup of connection leaks
            cleanup_result = self.db_manager.detect_and_cleanup_connection_leaks()
            
            # Wait a moment for cleanup to take effect
            await asyncio.sleep(2)
            
            # Test connection pool health
            health_report = self.db_manager.monitor_connection_health()
            
            return health_report.get('overall_health') != 'CRITICAL'
            
        except Exception as e:
            logger.error(f"Connection pool recovery failed: {e}")
            return False
    
    async def _test_database_connection(self) -> bool:
        """Test database connection after recovery"""
        try:
            if not self.db_manager:
                return False
            
            session = self.db_manager.get_session()
            try:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
                return True
            finally:
                self.db_manager.close_session(session)
                
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def _cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count of cleaned sessions"""
        try:
            # This would integrate with the session management system
            # For now, return a simulated count
            cleaned_count = 0
            
            # If we have access to session manager, clean up expired sessions
            # This would be implemented based on the actual session management system
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
            return 0
    
    async def _clear_application_caches(self) -> Dict[str, Any]:
        """Clear application caches to free memory"""
        try:
            cache_result = {
                'caches_cleared': [],
                'memory_freed_estimate': 0
            }
            
            # Clear various application caches
            # This would be implemented based on the actual caching system
            
            return cache_result
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return {'error': str(e)}
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            return psutil.virtual_memory().used / (1024 * 1024)
        except ImportError:
            return 0.0
    
    def _get_memory_usage_percent(self) -> float:
        """Get current memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
    
    async def _escalate_connection_recovery_failure(self, error: Exception, recovery_result: Dict[str, Any]) -> None:
        """Escalate connection recovery failure to administrators"""
        await send_admin_notification(
            message=f"Database connection recovery failed: {str(error)}",
            notification_type=NotificationType.ERROR,
            title="Critical: Connection Recovery Failed",
            priority=NotificationPriority.CRITICAL,
            system_health_data={
                'error_type': 'connection_recovery_failure',
                'original_error': str(error),
                'recovery_actions': recovery_result.get('actions_taken', []),
                'recovery_time': recovery_result.get('recovery_time', 0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            requires_admin_action=True
        )
    
    async def _escalate_memory_recovery_failure(self, error: Exception, recovery_result: Dict[str, Any]) -> None:
        """Escalate memory recovery failure to administrators"""
        await send_admin_notification(
            message=f"Memory cleanup recovery failed: {str(error)}",
            notification_type=NotificationType.ERROR,
            title="Critical: Memory Recovery Failed",
            priority=NotificationPriority.CRITICAL,
            system_health_data={
                'error_type': 'memory_recovery_failure',
                'original_error': str(error),
                'recovery_actions': recovery_result.get('actions_taken', []),
                'memory_freed_mb': recovery_result.get('memory_freed_mb', 0),
                'sessions_cleaned': recovery_result.get('sessions_cleaned', 0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            requires_admin_action=True
        )

# Global responsiveness error recovery manager instance
responsiveness_recovery_manager = None

def get_responsiveness_recovery_manager(db_manager=None, system_optimizer=None) -> ResponsivenessErrorRecoveryManager:
    """Get or create the global responsiveness recovery manager"""
    global responsiveness_recovery_manager
    if responsiveness_recovery_manager is None:
        responsiveness_recovery_manager = ResponsivenessErrorRecoveryManager(db_manager, system_optimizer)
    return responsiveness_recovery_manager

def with_responsiveness_recovery(issue_type: ResponsivenessIssueType):
    """Decorator to add responsiveness recovery to functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                recovery_manager = get_responsiveness_recovery_manager()
                
                # Attempt appropriate recovery based on issue type
                if issue_type == ResponsivenessIssueType.CONNECTION_LEAK:
                    recovery_result = await recovery_manager.handle_database_connection_recovery(e)
                elif issue_type == ResponsivenessIssueType.MEMORY_LEAK:
                    recovery_result = await recovery_manager.handle_session_memory_cleanup_recovery(e)
                else:
                    # For other issue types, use the enhanced error handling
                    return await recovery_manager.handle_enhanced_error(e, func, {'issue_type': issue_type.value}, *args, **kwargs)
                
                # Integrate with admin alerts
                await recovery_manager.integrate_with_admin_alerts(recovery_result, issue_type)
                
                # If recovery was successful, retry the operation
                if recovery_result.get('success', False):
                    logger.info(f"Recovery successful for {issue_type.value}, retrying operation")
                    return await func(*args, **kwargs)
                else:
                    # Recovery failed, raise the original error
                    raise e
                    
        return wrapper
    return decorator