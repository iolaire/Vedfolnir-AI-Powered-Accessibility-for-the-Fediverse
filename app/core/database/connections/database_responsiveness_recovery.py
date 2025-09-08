# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Database Responsiveness Recovery Extensions

This module extends the existing DatabaseManager with enhanced error handling
and responsiveness recovery mechanisms, including connection recovery, 
exponential backoff, and automated cleanup procedures.
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, TimeoutError as SQLTimeoutError
from sqlalchemy import text

from database import DatabaseManager, DatabaseOperationError
from responsiveness_error_recovery import ResponsivenessErrorRecoveryManager, ResponsivenessIssueType
from notification_helpers import send_admin_notification
from models import NotificationType, NotificationPriority

logger = logging.getLogger(__name__)

class DatabaseResponsivenessRecoveryMixin:
    """Mixin to add responsiveness recovery capabilities to DatabaseManager"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Connection recovery configuration
        self.connection_recovery_config = {
            'max_retries': 3,
            'base_delay': 1.0,
            'max_delay': 30.0,
            'backoff_multiplier': 2.0,
            'connection_timeout': 30.0,
            'query_timeout': 60.0
        }
        
        # Recovery statistics
        self.recovery_stats = {
            'connection_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'total_recovery_time': 0.0,
            'last_recovery': None
        }
        
        # Connection health monitoring
        self.connection_health_history = []
        self.max_health_history = 100
        
        # Recovery manager integration
        self._recovery_manager = None
    
    def get_recovery_manager(self) -> ResponsivenessErrorRecoveryManager:
        """Get or create recovery manager instance"""
        if self._recovery_manager is None:
            from responsiveness_error_recovery import get_responsiveness_recovery_manager
            self._recovery_manager = get_responsiveness_recovery_manager(db_manager=self)
        return self._recovery_manager
    
    async def handle_mysql_error_with_recovery(self, error: Exception, operation: str = None, context: Dict[str, Any] = None) -> str:
        """Enhanced MySQL error handling with automatic recovery mechanisms"""
        start_time = time.time()
        recovery_attempted = False
        
        try:
            # Get basic error information
            error_message = self.handle_mysql_error(error)
            
            # Determine if this error is recoverable
            if self._is_connection_recoverable_error(error):
                logger.info(f"Attempting connection recovery for error: {type(error).__name__}")
                recovery_attempted = True
                
                # Attempt connection recovery
                recovery_result = await self._attempt_connection_recovery(error, operation, context)
                
                if recovery_result['success']:
                    self.recovery_stats['successful_recoveries'] += 1
                    self.recovery_stats['total_recovery_time'] += recovery_result['recovery_time']
                    self.recovery_stats['last_recovery'] = datetime.now(timezone.utc)
                    
                    # Send success notification
                    await send_admin_notification(
                        message=f"Database connection recovery successful for {operation or 'unknown operation'}",
                        notification_type=NotificationType.SUCCESS,
                        title="Database Recovery Success",
                        priority=NotificationPriority.NORMAL,
                        system_health_data={
                            'recovery_type': 'database_connection',
                            'operation': operation,
                            'recovery_time': recovery_result['recovery_time'],
                            'actions_taken': recovery_result.get('actions_taken', [])
                        }
                    )
                    
                    return f"Connection recovered successfully. Original error: {error_message}"
                else:
                    self.recovery_stats['failed_recoveries'] += 1
                    
                    # Send failure notification
                    await send_admin_notification(
                        message=f"Database connection recovery failed for {operation or 'unknown operation'}: {error_message}",
                        notification_type=NotificationType.ERROR,
                        title="Database Recovery Failed",
                        priority=NotificationPriority.HIGH,
                        system_health_data={
                            'recovery_type': 'database_connection',
                            'operation': operation,
                            'recovery_time': recovery_result['recovery_time'],
                            'error_details': str(error),
                            'actions_attempted': recovery_result.get('actions_taken', [])
                        },
                        requires_admin_action=True
                    )
            
            # Add recovery information to error message
            if recovery_attempted:
                recovery_time = time.time() - start_time
                self.recovery_stats['connection_recoveries'] += 1
                
                enhanced_message = f"{error_message}\n\nRecovery attempted: {'Success' if recovery_result.get('success') else 'Failed'}"
                enhanced_message += f"\nRecovery time: {recovery_time:.2f} seconds"
                
                if not recovery_result.get('success'):
                    enhanced_message += f"\nRecovery actions attempted: {len(recovery_result.get('actions_taken', []))}"
                
                return enhanced_message
            
            return error_message
            
        except Exception as recovery_error:
            logger.error(f"Error during database recovery process: {recovery_error}")
            return f"{error_message}\n\nRecovery process failed: {str(recovery_error)}"
    
    async def _attempt_connection_recovery(self, error: Exception, operation: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Attempt to recover from database connection errors"""
        recovery_result = {
            'success': False,
            'actions_taken': [],
            'recovery_time': 0,
            'error_resolved': False
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Wait for potential temporary issues to resolve
            await asyncio.sleep(self.connection_recovery_config['base_delay'])
            recovery_result['actions_taken'].append({
                'action': 'initial_delay',
                'duration': self.connection_recovery_config['base_delay'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Step 2: Test basic connectivity
            connection_test_passed = await self._test_connection_with_timeout()
            recovery_result['actions_taken'].append({
                'action': 'connection_test',
                'result': connection_test_passed,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            if not connection_test_passed:
                # Step 3: Attempt to recreate engine connection
                engine_recreation_success = await self._recreate_engine_connection()
                recovery_result['actions_taken'].append({
                    'action': 'engine_recreation',
                    'result': engine_recreation_success,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                if engine_recreation_success:
                    # Test connection again after engine recreation
                    connection_test_passed = await self._test_connection_with_timeout()
                    recovery_result['actions_taken'].append({
                        'action': 'post_recreation_test',
                        'result': connection_test_passed,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            # Step 4: Clean up any leaked connections
            if connection_test_passed:
                cleanup_result = self.detect_and_cleanup_connection_leaks()
                recovery_result['actions_taken'].append({
                    'action': 'connection_cleanup',
                    'result': cleanup_result,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            # Step 5: Final connection health check
            if connection_test_passed:
                health_report = self.monitor_connection_health()
                recovery_result['actions_taken'].append({
                    'action': 'health_check',
                    'result': health_report,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                # Consider recovery successful if health is not critical
                recovery_result['success'] = health_report.get('overall_health') != 'CRITICAL'
                recovery_result['error_resolved'] = recovery_result['success']
            
        except Exception as recovery_error:
            logger.error(f"Connection recovery process failed: {recovery_error}")
            recovery_result['actions_taken'].append({
                'action': 'recovery_error',
                'error': str(recovery_error),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        finally:
            recovery_result['recovery_time'] = time.time() - start_time
        
        return recovery_result
    
    async def _test_connection_with_timeout(self) -> bool:
        """Test database connection with timeout"""
        try:
            # Use asyncio timeout to prevent hanging
            async def test_connection():
                session = self.get_session()
                try:
                    session.execute(text("SELECT 1"))
                    return True
                finally:
                    self.close_session(session)
            
            # Test with timeout
            result = await asyncio.wait_for(
                test_connection(),
                timeout=self.connection_recovery_config['connection_timeout']
            )
            return result
            
        except asyncio.TimeoutError:
            logger.warning("Database connection test timed out")
            return False
        except Exception as e:
            logger.warning(f"Database connection test failed: {e}")
            return False
    
    async def _recreate_engine_connection(self) -> bool:
        """Attempt to recreate the database engine connection"""
        try:
            # Dispose of current engine connections
            self.engine.dispose()
            
            # Wait a moment for cleanup
            await asyncio.sleep(2)
            
            # Test if engine can create new connections
            connection = self.engine.connect()
            connection.execute(text("SELECT 1"))
            connection.close()
            
            logger.info("Database engine connection recreated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to recreate database engine connection: {e}")
            return False
    
    def _is_connection_recoverable_error(self, error: Exception) -> bool:
        """Determine if a database error is recoverable through connection recovery"""
        recoverable_error_types = (
            DisconnectionError,
            SQLTimeoutError,
            ConnectionError
        )
        
        if isinstance(error, recoverable_error_types):
            return True
        
        # Check error message for recoverable patterns
        error_message = str(error).lower()
        recoverable_patterns = [
            'connection refused',
            'connection lost',
            'server has gone away',
            'lost connection',
            'connection timeout',
            'connection reset',
            'connection aborted',
            'connection closed',
            'connection broken'
        ]
        
        return any(pattern in error_message for pattern in recoverable_patterns)
    
    @contextmanager
    def get_session_with_recovery(self, max_retries: int = None, operation: str = None):
        """Get database session with automatic recovery on connection errors"""
        max_retries = max_retries or self.connection_recovery_config['max_retries']
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                session = self.get_session()
                try:
                    yield session
                    break  # Success, exit retry loop
                except Exception as e:
                    self.close_session(session)
                    
                    # Check if this is a recoverable error
                    if self._is_connection_recoverable_error(e) and retry_count < max_retries:
                        retry_count += 1
                        delay = min(
                            self.connection_recovery_config['base_delay'] * 
                            (self.connection_recovery_config['backoff_multiplier'] ** (retry_count - 1)),
                            self.connection_recovery_config['max_delay']
                        )
                        
                        logger.warning(f"Database operation failed, retrying in {delay}s (attempt {retry_count}/{max_retries}): {e}")
                        time.sleep(delay)
                        
                        # Attempt recovery before retry
                        asyncio.create_task(self._attempt_connection_recovery(e, operation))
                        continue
                    else:
                        # Non-recoverable error or max retries exceeded
                        raise
                        
            except Exception as e:
                if retry_count >= max_retries:
                    logger.error(f"Database operation failed after {max_retries} retries: {e}")
                    raise DatabaseOperationError(f"Database operation failed after {max_retries} retries: {e}")
                else:
                    # This shouldn't happen in normal flow, but handle it
                    raise
    
    def get_enhanced_mysql_performance_stats(self) -> Dict[str, Any]:
        """Get enhanced MySQL performance statistics with recovery information"""
        # Get base performance stats
        base_stats = self.get_mysql_performance_stats()
        
        # Add recovery statistics
        recovery_stats = {
            'connection_recoveries': self.recovery_stats['connection_recoveries'],
            'successful_recoveries': self.recovery_stats['successful_recoveries'],
            'failed_recoveries': self.recovery_stats['failed_recoveries'],
            'recovery_success_rate': 0.0,
            'average_recovery_time': 0.0,
            'last_recovery': self.recovery_stats['last_recovery'].isoformat() if self.recovery_stats['last_recovery'] else None
        }
        
        # Calculate recovery success rate
        if self.recovery_stats['connection_recoveries'] > 0:
            recovery_stats['recovery_success_rate'] = (
                self.recovery_stats['successful_recoveries'] / 
                self.recovery_stats['connection_recoveries']
            )
        
        # Calculate average recovery time
        if self.recovery_stats['successful_recoveries'] > 0:
            recovery_stats['average_recovery_time'] = (
                self.recovery_stats['total_recovery_time'] / 
                self.recovery_stats['successful_recoveries']
            )
        
        # Add recovery stats to base stats
        base_stats['recovery_statistics'] = recovery_stats
        
        # Add connection health history summary
        if self.connection_health_history:
            recent_health = self.connection_health_history[-10:]  # Last 10 health checks
            health_summary = {
                'recent_health_checks': len(recent_health),
                'healthy_checks': sum(1 for h in recent_health if h.get('overall_health') == 'HEALTHY'),
                'warning_checks': sum(1 for h in recent_health if h.get('overall_health') == 'WARNING'),
                'critical_checks': sum(1 for h in recent_health if h.get('overall_health') == 'CRITICAL'),
                'last_health_check': recent_health[-1].get('timestamp') if recent_health else None
            }
            base_stats['connection_health_summary'] = health_summary
        
        return base_stats
    
    def monitor_connection_health_with_recovery(self) -> Dict[str, Any]:
        """Enhanced connection health monitoring with recovery status"""
        # Get base health report
        health_report = self.monitor_connection_health()
        
        # Add recovery system status
        recovery_manager = self.get_recovery_manager()
        health_report = asyncio.create_task(
            recovery_manager.extend_health_check_error_handling(health_report)
        )
        
        # Store health check in history
        self.connection_health_history.append({
            'timestamp': health_report['timestamp'],
            'overall_health': health_report['overall_health'],
            'issues_count': len(health_report.get('issues', [])),
            'recommendations_count': len(health_report.get('recommendations', []))
        })
        
        # Trim health history if it gets too large
        if len(self.connection_health_history) > self.max_health_history:
            self.connection_health_history = self.connection_health_history[-self.max_health_history:]
        
        return health_report

class EnhancedDatabaseManager(DatabaseResponsivenessRecoveryMixin, DatabaseManager):
    """Enhanced DatabaseManager with responsiveness recovery capabilities"""
    
    def __init__(self, config):
        super().__init__(config)
        logger.info("Enhanced DatabaseManager initialized with responsiveness recovery capabilities")

# Decorator for database operations with recovery
def with_database_recovery(operation_name: str = None, max_retries: int = None):
    """Decorator to add database recovery to operations"""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'get_session_with_recovery'):
                # Fallback to normal operation if recovery not available
                return await func(self, *args, **kwargs)
            
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                if hasattr(self, '_is_connection_recoverable_error') and self._is_connection_recoverable_error(e):
                    logger.info(f"Attempting database recovery for operation: {operation_name or func.__name__}")
                    
                    # Attempt recovery
                    recovery_result = await self._attempt_connection_recovery(e, operation_name or func.__name__)
                    
                    if recovery_result.get('success', False):
                        logger.info(f"Database recovery successful, retrying operation: {operation_name or func.__name__}")
                        return await func(self, *args, **kwargs)
                
                # Recovery failed or not applicable, re-raise original error
                raise
                
        return wrapper
    return decorator