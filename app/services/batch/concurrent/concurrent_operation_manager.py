# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Concurrent Operation Manager

Handles concurrent operation coordination to prevent job conflicts
and data corruption. Provides distributed locking, operation tracking,
and conflict resolution mechanisms.
"""

import logging
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Set, List, Callable
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class OperationType(Enum):
    TASK_CREATION = "task_creation"
    TASK_EXECUTION = "task_execution"
    TASK_CANCELLATION = "task_cancellation"
    USER_MANAGEMENT = "user_management"
    PLATFORM_MANAGEMENT = "platform_management"
    SYSTEM_MAINTENANCE = "system_maintenance"
    DATABASE_MIGRATION = "database_migration"
    PROGRESS_UPDATE = "progress_update"

class LockScope(Enum):
    GLOBAL = "global"
    USER = "user"
    PLATFORM = "platform"
    TASK = "task"
    RESOURCE = "resource"

@dataclass
class OperationLock:
    """Represents an active operation lock"""
    lock_id: str
    operation_type: OperationType
    scope: LockScope
    resource_id: str
    owner_thread: str
    created_at: datetime
    expires_at: Optional[datetime]
    metadata: Dict[str, Any]

class ConcurrentOperationManager:
    """Manages concurrent operations and prevents conflicts"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
        # In-memory lock tracking
        self._active_locks: Dict[str, OperationLock] = {}
        self._lock_registry = threading.Lock()
        
        # Operation tracking
        self._operation_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000
        
        # Configuration
        self._default_lock_timeout = 300  # 5 minutes
        self._cleanup_interval = 60  # 1 minute
        self._max_concurrent_operations = 100
        
        # Cleanup thread
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        
        # Conflict resolution callbacks
        self._conflict_callbacks: Dict[OperationType, List[Callable]] = {}
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        logger.info("Concurrent operation manager initialized")
    
    def register_conflict_callback(self, operation_type: OperationType, 
                                 callback: Callable[[str, Dict[str, Any]], None]):
        """Register callback for conflict resolution"""
        if operation_type not in self._conflict_callbacks:
            self._conflict_callbacks[operation_type] = []
        self._conflict_callbacks[operation_type].append(callback)
    
    @contextmanager
    def acquire_lock(self, operation_type: OperationType, scope: LockScope, 
                    resource_id: str, timeout: Optional[int] = None,
                    metadata: Optional[Dict[str, Any]] = None):
        """
        Acquire an operation lock with automatic cleanup
        
        Args:
            operation_type: Type of operation
            scope: Scope of the lock
            resource_id: ID of the resource being locked
            timeout: Lock timeout in seconds
            metadata: Additional metadata for the lock
        """
        lock_key = self._generate_lock_key(scope, resource_id, operation_type)
        lock_id = str(uuid.uuid4())
        timeout = timeout or self._default_lock_timeout
        
        try:
            # Acquire the lock
            lock = self._acquire_lock_internal(
                lock_id, operation_type, scope, resource_id, timeout, metadata or {}
            )
            
            logger.debug(f"Acquired lock {sanitize_for_log(lock_key)} for operation {operation_type.value}")
            
            yield lock
            
        except Exception as e:
            logger.error(f"Error in locked operation {sanitize_for_log(lock_key)}: {sanitize_for_log(str(e))}")
            raise
        finally:
            # Release the lock
            self._release_lock_internal(lock_id)
            logger.debug(f"Released lock {sanitize_for_log(lock_key)}")
    
    def _acquire_lock_internal(self, lock_id: str, operation_type: OperationType,
                             scope: LockScope, resource_id: str, timeout: int,
                             metadata: Dict[str, Any]) -> OperationLock:
        """Internal method to acquire a lock"""
        lock_key = self._generate_lock_key(scope, resource_id, operation_type)
        current_thread = threading.current_thread().name
        
        with self._lock_registry:
            # Check if we're at max concurrent operations
            if len(self._active_locks) >= self._max_concurrent_operations:
                raise RuntimeError(f"Maximum concurrent operations limit reached ({self._max_concurrent_operations})")
            
            # Check for existing lock
            existing_lock = self._active_locks.get(lock_key)
            if existing_lock:
                # Check if lock is expired
                if existing_lock.expires_at and datetime.now(timezone.utc) > existing_lock.expires_at:
                    logger.warning(f"Removing expired lock {sanitize_for_log(lock_key)}")
                    del self._active_locks[lock_key]
                else:
                    # Check for same thread (reentrant lock)
                    if existing_lock.owner_thread == current_thread:
                        logger.debug(f"Reentrant lock detected for {sanitize_for_log(lock_key)}")
                        return existing_lock
                    else:
                        # Conflict detected
                        self._handle_lock_conflict(lock_key, existing_lock, operation_type, metadata)
                        raise RuntimeError(f"Resource {resource_id} is locked by another operation")
            
            # Create new lock
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(seconds=timeout) if timeout > 0 else None
            
            lock = OperationLock(
                lock_id=lock_id,
                operation_type=operation_type,
                scope=scope,
                resource_id=resource_id,
                owner_thread=current_thread,
                created_at=now,
                expires_at=expires_at,
                metadata=metadata
            )
            
            self._active_locks[lock_key] = lock
            
            # Record operation
            self._record_operation("lock_acquired", {
                "lock_key": lock_key,
                "operation_type": operation_type.value,
                "scope": scope.value,
                "resource_id": resource_id,
                "thread": current_thread,
                "timeout": timeout
            })
            
            return lock
    
    def _release_lock_internal(self, lock_id: str):
        """Internal method to release a lock"""
        with self._lock_registry:
            # Find and remove the lock
            lock_key_to_remove = None
            for lock_key, lock in self._active_locks.items():
                if lock.lock_id == lock_id:
                    lock_key_to_remove = lock_key
                    break
            
            if lock_key_to_remove:
                lock = self._active_locks[lock_key_to_remove]
                del self._active_locks[lock_key_to_remove]
                
                # Record operation
                self._record_operation("lock_released", {
                    "lock_key": lock_key_to_remove,
                    "operation_type": lock.operation_type.value,
                    "resource_id": lock.resource_id,
                    "duration_seconds": (datetime.now(timezone.utc) - lock.created_at).total_seconds()
                })
    
    def _generate_lock_key(self, scope: LockScope, resource_id: str, 
                          operation_type: OperationType) -> str:
        """Generate a unique lock key"""
        return f"{scope.value}:{resource_id}:{operation_type.value}"
    
    def _handle_lock_conflict(self, lock_key: str, existing_lock: OperationLock,
                            requested_operation: OperationType, metadata: Dict[str, Any]):
        """Handle lock conflicts"""
        logger.warning(f"Lock conflict detected for {sanitize_for_log(lock_key)}")
        
        conflict_data = {
            "lock_key": lock_key,
            "existing_operation": existing_lock.operation_type.value,
            "existing_thread": existing_lock.owner_thread,
            "existing_created_at": existing_lock.created_at.isoformat(),
            "requested_operation": requested_operation.value,
            "requesting_thread": threading.current_thread().name,
            "metadata": metadata
        }
        
        # Record conflict
        self._record_operation("lock_conflict", conflict_data)
        
        # Call conflict callbacks
        callbacks = self._conflict_callbacks.get(requested_operation, [])
        for callback in callbacks:
            try:
                callback(lock_key, conflict_data)
            except Exception as e:
                logger.error(f"Conflict callback failed: {sanitize_for_log(str(e))}")
    
    def _record_operation(self, operation: str, data: Dict[str, Any]):
        """Record operation in history"""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "data": data
        }
        
        self._operation_history.append(record)
        
        # Trim history if too large
        if len(self._operation_history) > self._max_history_size:
            self._operation_history = self._operation_history[-self._max_history_size:]
    
    def _start_cleanup_thread(self):
        """Start the cleanup thread for expired locks"""
        def cleanup_loop():
            while not self._stop_cleanup.is_set():
                try:
                    self._cleanup_expired_locks()
                except Exception as e:
                    logger.error(f"Error in lock cleanup: {sanitize_for_log(str(e))}")
                
                self._stop_cleanup.wait(self._cleanup_interval)
        
        self._cleanup_thread = threading.Thread(
            target=cleanup_loop,
            name="LockCleanup",
            daemon=True
        )
        self._cleanup_thread.start()
        logger.info("Lock cleanup thread started")
    
    def _cleanup_expired_locks(self):
        """Clean up expired locks"""
        now = datetime.now(timezone.utc)
        expired_locks = []
        
        with self._lock_registry:
            for lock_key, lock in list(self._active_locks.items()):
                if lock.expires_at and now > lock.expires_at:
                    expired_locks.append((lock_key, lock))
                    del self._active_locks[lock_key]
        
        if expired_locks:
            logger.info(f"Cleaned up {len(expired_locks)} expired locks")
            
            for lock_key, lock in expired_locks:
                self._record_operation("lock_expired", {
                    "lock_key": lock_key,
                    "operation_type": lock.operation_type.value,
                    "resource_id": lock.resource_id,
                    "duration_seconds": (now - lock.created_at).total_seconds()
                })
    
    def get_active_locks(self) -> List[Dict[str, Any]]:
        """Get list of currently active locks"""
        with self._lock_registry:
            return [
                {
                    "lock_id": lock.lock_id,
                    "operation_type": lock.operation_type.value,
                    "scope": lock.scope.value,
                    "resource_id": lock.resource_id,
                    "owner_thread": lock.owner_thread,
                    "created_at": lock.created_at.isoformat(),
                    "expires_at": lock.expires_at.isoformat() if lock.expires_at else None,
                    "metadata": lock.metadata
                }
                for lock in self._active_locks.values()
            ]
    
    def get_operation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent operation history"""
        return self._operation_history[-limit:] if limit > 0 else self._operation_history
    
    def get_lock_statistics(self) -> Dict[str, Any]:
        """Get lock usage statistics"""
        with self._lock_registry:
            active_count = len(self._active_locks)
            
            # Count by operation type
            operation_counts = {}
            for lock in self._active_locks.values():
                op_type = lock.operation_type.value
                operation_counts[op_type] = operation_counts.get(op_type, 0) + 1
            
            # Count by scope
            scope_counts = {}
            for lock in self._active_locks.values():
                scope = lock.scope.value
                scope_counts[scope] = scope_counts.get(scope, 0) + 1
        
        return {
            "active_locks": active_count,
            "max_concurrent_operations": self._max_concurrent_operations,
            "operation_counts": operation_counts,
            "scope_counts": scope_counts,
            "total_operations": len(self._operation_history)
        }
    
    def force_release_lock(self, resource_id: str, scope: LockScope, 
                          operation_type: OperationType) -> bool:
        """Force release a lock (admin operation)"""
        lock_key = self._generate_lock_key(scope, resource_id, operation_type)
        
        with self._lock_registry:
            if lock_key in self._active_locks:
                lock = self._active_locks[lock_key]
                del self._active_locks[lock_key]
                
                logger.warning(f"Force released lock {sanitize_for_log(lock_key)}")
                
                self._record_operation("lock_force_released", {
                    "lock_key": lock_key,
                    "operation_type": lock.operation_type.value,
                    "resource_id": lock.resource_id,
                    "original_thread": lock.owner_thread,
                    "duration_seconds": (datetime.now(timezone.utc) - lock.created_at).total_seconds()
                })
                
                return True
        
        return False
    
    def is_resource_locked(self, resource_id: str, scope: LockScope, 
                          operation_type: OperationType) -> bool:
        """Check if a resource is currently locked"""
        lock_key = self._generate_lock_key(scope, resource_id, operation_type)
        
        with self._lock_registry:
            lock = self._active_locks.get(lock_key)
            if lock:
                # Check if lock is expired
                if lock.expires_at and datetime.now(timezone.utc) > lock.expires_at:
                    del self._active_locks[lock_key]
                    return False
                return True
        
        return False
    
    def shutdown(self):
        """Shutdown the concurrent operation manager"""
        logger.info("Shutting down concurrent operation manager")
        
        # Stop cleanup thread
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        # Release all locks
        with self._lock_registry:
            active_count = len(self._active_locks)
            if active_count > 0:
                logger.warning(f"Releasing {active_count} active locks during shutdown")
                self._active_locks.clear()
        
        logger.info("Concurrent operation manager shutdown complete")

# Convenience decorators and context managers

def with_operation_lock(operation_type: OperationType, scope: LockScope, 
                       resource_id_func: Callable = None, timeout: int = None):
    """
    Decorator for functions that need operation locking
    
    Args:
        operation_type: Type of operation
        scope: Scope of the lock
        resource_id_func: Function to extract resource ID from function args
        timeout: Lock timeout in seconds
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get concurrent operation manager from app context or global
            manager = _get_operation_manager()
            if not manager:
                logger.warning("No concurrent operation manager available, proceeding without lock")
                return func(*args, **kwargs)
            
            # Determine resource ID
            if resource_id_func:
                resource_id = resource_id_func(*args, **kwargs)
            else:
                # Default: use first argument as resource ID
                resource_id = str(args[0]) if args else "default"
            
            # Acquire lock and execute function
            with manager.acquire_lock(operation_type, scope, resource_id, timeout):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def _get_operation_manager() -> Optional[ConcurrentOperationManager]:
    """Get the concurrent operation manager from Flask app context or global"""
    try:
        from flask import current_app
        return getattr(current_app, 'concurrent_operation_manager', None)
    except:
        return _global_operation_manager

# Global instance
_global_operation_manager = None

def initialize_concurrent_operation_manager(db_manager: DatabaseManager) -> ConcurrentOperationManager:
    """Initialize the global concurrent operation manager"""
    global _global_operation_manager
    _global_operation_manager = ConcurrentOperationManager(db_manager)
    return _global_operation_manager

def get_concurrent_operation_manager() -> Optional[ConcurrentOperationManager]:
    """Get the global concurrent operation manager"""
    return _global_operation_manager