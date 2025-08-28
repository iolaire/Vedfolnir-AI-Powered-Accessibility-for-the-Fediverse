# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Backup and Recovery System

This module provides comprehensive backup and recovery capabilities for WebSocket state,
including connection state persistence, session data backup, subscription management,
and automatic recovery procedures for production environments.
"""

import os
import json
import gzip
import shutil
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import pickle
import hashlib
from contextlib import contextmanager

from flask_socketio import SocketIO

from websocket_production_config import BackupRecoveryConfig
from websocket_production_logging import ProductionWebSocketLogger, WebSocketLogLevel

# Try to import optional dependencies
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class BackupType(Enum):
    """Types of WebSocket backups"""
    FULL = "full"
    INCREMENTAL = "incremental"
    EMERGENCY = "emergency"


class RecoveryStatus(Enum):
    """Recovery operation status"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"


@dataclass
class ConnectionState:
    """WebSocket connection state"""
    session_id: str
    user_id: Optional[int]
    connection_id: str
    namespace: str
    rooms: Set[str]
    connected_at: str
    last_activity: str
    client_info: Dict[str, Any]
    subscription_data: Dict[str, Any]


@dataclass
class BackupMetadata:
    """Backup metadata information"""
    backup_id: str
    backup_type: BackupType
    timestamp: str
    file_path: str
    file_size: int
    checksum: str
    connection_count: int
    session_count: int
    compressed: bool
    recovery_tested: bool = False


@dataclass
class RecoveryResult:
    """Recovery operation result"""
    status: RecoveryStatus
    message: str
    recovered_connections: int
    recovered_sessions: int
    failed_recoveries: int
    recovery_time_seconds: float
    errors: List[str]


class WebSocketBackupManager:
    """
    WebSocket backup manager for state persistence
    
    Provides comprehensive backup capabilities for WebSocket connections,
    sessions, subscriptions, and related state data.
    """
    
    def __init__(self, config: BackupRecoveryConfig, 
                 logger: ProductionWebSocketLogger,
                 socketio: Optional[SocketIO] = None,
                 redis_client: Optional[Any] = None):
        """
        Initialize WebSocket backup manager
        
        Args:
            config: Backup and recovery configuration
            logger: Production WebSocket logger
            socketio: SocketIO instance (optional)
            redis_client: Redis client for session data (optional)
        """
        self.config = config
        self.logger = logger
        self.socketio = socketio
        self.redis_client = redis_client
        
        # Backup state
        self.backup_lock = threading.Lock()
        self.backup_thread = None
        self.backup_running = False
        
        # Connection and session tracking
        self.active_connections: Dict[str, ConnectionState] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self.subscription_data: Dict[str, Dict[str, Any]] = {}
        
        # Backup storage
        self.backup_directory = Path(self.config.backup_location)
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        
        # Recovery state
        self.recovery_in_progress = False
        self.recovery_lock = threading.Lock()
        
        # Start automatic backup if enabled
        if self.config.state_backup_enabled:
            self.start_automatic_backup()
    
    def start_automatic_backup(self) -> None:
        """Start automatic backup process"""
        if self.backup_running:
            return
        
        self.backup_running = True
        
        def backup_loop():
            while self.backup_running:
                try:
                    self.create_backup(BackupType.INCREMENTAL)
                    time.sleep(self.config.backup_interval)
                except Exception as e:
                    self.logger.log_error_event(
                        event_type="backup_error",
                        message=f"Automatic backup failed: {str(e)}",
                        exception=e
                    )
                    time.sleep(60)  # Wait longer on error
        
        self.backup_thread = threading.Thread(target=backup_loop, daemon=True)
        self.backup_thread.start()
        
        self.logger.log_system_event(
            event_type="backup_started",
            message="Automatic WebSocket backup started",
            metadata={'interval': self.config.backup_interval}
        )
    
    def stop_automatic_backup(self) -> None:
        """Stop automatic backup process"""
        self.backup_running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=30)
        
        self.logger.log_system_event(
            event_type="backup_stopped",
            message="Automatic WebSocket backup stopped"
        )
    
    def track_connection(self, session_id: str, user_id: Optional[int],
                        connection_id: str, namespace: str,
                        client_info: Optional[Dict[str, Any]] = None) -> None:
        """Track active WebSocket connection"""
        
        if not self.config.persist_connections:
            return
        
        connection_state = ConnectionState(
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            namespace=namespace,
            rooms=set(),
            connected_at=datetime.now(timezone.utc).isoformat(),
            last_activity=datetime.now(timezone.utc).isoformat(),
            client_info=client_info or {},
            subscription_data={}
        )
        
        with self.backup_lock:
            self.active_connections[connection_id] = connection_state
        
        self.logger.log_connection_event(
            event_type="connection_tracked",
            message=f"Connection tracked for backup: {connection_id}",
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id
        )
    
    def untrack_connection(self, connection_id: str) -> None:
        """Remove connection from tracking"""
        
        with self.backup_lock:
            if connection_id in self.active_connections:
                connection_state = self.active_connections.pop(connection_id)
                
                self.logger.log_connection_event(
                    event_type="connection_untracked",
                    message=f"Connection removed from tracking: {connection_id}",
                    session_id=connection_state.session_id,
                    user_id=connection_state.user_id,
                    connection_id=connection_id
                )
    
    def update_connection_activity(self, connection_id: str,
                                 rooms: Optional[Set[str]] = None,
                                 subscription_data: Optional[Dict[str, Any]] = None) -> None:
        """Update connection activity and state"""
        
        with self.backup_lock:
            if connection_id in self.active_connections:
                connection_state = self.active_connections[connection_id]
                connection_state.last_activity = datetime.now(timezone.utc).isoformat()
                
                if rooms is not None:
                    connection_state.rooms = rooms
                
                if subscription_data is not None and self.config.persist_subscriptions:
                    connection_state.subscription_data.update(subscription_data)
    
    def store_session_data(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Store session data for backup"""
        
        if not self.config.persist_session_data:
            return
        
        with self.backup_lock:
            self.session_data[session_id] = {
                'data': session_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def create_backup(self, backup_type: BackupType = BackupType.FULL) -> Optional[BackupMetadata]:
        """Create WebSocket state backup"""
        
        try:
            backup_id = self._generate_backup_id(backup_type)
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Collect backup data
            backup_data = self._collect_backup_data(backup_type)
            
            # Create backup file
            backup_filename = f"websocket_backup_{backup_id}.json"
            if self.config.compress_backups:
                backup_filename += ".gz"
            
            backup_path = self.backup_directory / backup_filename
            
            # Write backup data
            if self.config.compress_backups:
                with gzip.open(backup_path, 'wt', encoding='utf-8', 
                             compresslevel=self.config.compression_level) as f:
                    json.dump(backup_data, f, indent=2, default=str)
            else:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, default=str)
            
            # Calculate file size and checksum
            file_size = backup_path.stat().st_size
            checksum = self._calculate_checksum(backup_path)
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=backup_type,
                timestamp=timestamp,
                file_path=str(backup_path),
                file_size=file_size,
                checksum=checksum,
                connection_count=len(backup_data.get('connections', {})),
                session_count=len(backup_data.get('sessions', {})),
                compressed=self.config.compress_backups
            )
            
            # Save metadata
            self._save_backup_metadata(metadata)
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            self.logger.log_system_event(
                event_type="backup_created",
                message=f"WebSocket backup created: {backup_id}",
                metadata={
                    'backup_type': backup_type.value,
                    'file_size': file_size,
                    'connection_count': metadata.connection_count,
                    'session_count': metadata.session_count
                }
            )
            
            return metadata
            
        except Exception as e:
            self.logger.log_error_event(
                event_type="backup_creation_failed",
                message=f"Failed to create WebSocket backup: {str(e)}",
                exception=e
            )
            return None
    
    def restore_from_backup(self, backup_id: Optional[str] = None,
                          backup_path: Optional[str] = None) -> RecoveryResult:
        """Restore WebSocket state from backup"""
        
        if self.recovery_in_progress:
            return RecoveryResult(
                status=RecoveryStatus.FAILED,
                message="Recovery already in progress",
                recovered_connections=0,
                recovered_sessions=0,
                failed_recoveries=0,
                recovery_time_seconds=0.0,
                errors=["Recovery already in progress"]
            )
        
        with self.recovery_lock:
            self.recovery_in_progress = True
            start_time = time.time()
            
            try:
                # Find backup file
                if backup_path:
                    backup_file = Path(backup_path)
                elif backup_id:
                    backup_file = self._find_backup_file(backup_id)
                else:
                    backup_file = self._find_latest_backup()
                
                if not backup_file or not backup_file.exists():
                    return RecoveryResult(
                        status=RecoveryStatus.FAILED,
                        message="Backup file not found",
                        recovered_connections=0,
                        recovered_sessions=0,
                        failed_recoveries=0,
                        recovery_time_seconds=time.time() - start_time,
                        errors=["Backup file not found"]
                    )
                
                # Load backup data
                backup_data = self._load_backup_data(backup_file)
                
                # Perform recovery
                recovery_result = self._perform_recovery(backup_data)
                recovery_result.recovery_time_seconds = time.time() - start_time
                
                self.logger.log_system_event(
                    event_type="backup_restored",
                    message=f"WebSocket backup restored: {backup_file.name}",
                    metadata={
                        'recovered_connections': recovery_result.recovered_connections,
                        'recovered_sessions': recovery_result.recovered_sessions,
                        'failed_recoveries': recovery_result.failed_recoveries,
                        'recovery_time': recovery_result.recovery_time_seconds
                    }
                )
                
                return recovery_result
                
            except Exception as e:
                self.logger.log_error_event(
                    event_type="backup_restore_failed",
                    message=f"Failed to restore WebSocket backup: {str(e)}",
                    exception=e
                )
                
                return RecoveryResult(
                    status=RecoveryStatus.FAILED,
                    message=f"Recovery failed: {str(e)}",
                    recovered_connections=0,
                    recovered_sessions=0,
                    failed_recoveries=0,
                    recovery_time_seconds=time.time() - start_time,
                    errors=[str(e)]
                )
            
            finally:
                self.recovery_in_progress = False
    
    def list_backups(self) -> List[BackupMetadata]:
        """List available backups"""
        
        backups = []
        metadata_files = self.backup_directory.glob("*.metadata.json")
        
        for metadata_file in metadata_files:
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_data = json.load(f)
                    metadata = BackupMetadata(**metadata_data)
                    backups.append(metadata)
            except Exception as e:
                self.logger.log_error_event(
                    event_type="backup_metadata_read_error",
                    message=f"Failed to read backup metadata: {metadata_file}",
                    exception=e
                )
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.timestamp, reverse=True)
        return backups
    
    def verify_backup(self, backup_id: str) -> bool:
        """Verify backup integrity"""
        
        try:
            backup_file = self._find_backup_file(backup_id)
            if not backup_file or not backup_file.exists():
                return False
            
            # Load metadata
            metadata = self._load_backup_metadata(backup_id)
            if not metadata:
                return False
            
            # Verify checksum
            current_checksum = self._calculate_checksum(backup_file)
            if current_checksum != metadata.checksum:
                self.logger.log_error_event(
                    event_type="backup_verification_failed",
                    message=f"Backup checksum mismatch: {backup_id}",
                    metadata={
                        'expected': metadata.checksum,
                        'actual': current_checksum
                    }
                )
                return False
            
            # Try to load backup data
            backup_data = self._load_backup_data(backup_file)
            if not backup_data:
                return False
            
            self.logger.log_system_event(
                event_type="backup_verified",
                message=f"Backup verification successful: {backup_id}"
            )
            
            return True
            
        except Exception as e:
            self.logger.log_error_event(
                event_type="backup_verification_error",
                message=f"Error verifying backup {backup_id}: {str(e)}",
                exception=e
            )
            return False
    
    def _collect_backup_data(self, backup_type: BackupType) -> Dict[str, Any]:
        """Collect data for backup"""
        
        backup_data = {
            'metadata': {
                'backup_type': backup_type.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': '1.0'
            }
        }
        
        with self.backup_lock:
            # Collect connection data
            if self.config.persist_connections:
                connections_data = {}
                for conn_id, conn_state in self.active_connections.items():
                    connections_data[conn_id] = {
                        'session_id': conn_state.session_id,
                        'user_id': conn_state.user_id,
                        'connection_id': conn_state.connection_id,
                        'namespace': conn_state.namespace,
                        'rooms': list(conn_state.rooms),
                        'connected_at': conn_state.connected_at,
                        'last_activity': conn_state.last_activity,
                        'client_info': conn_state.client_info,
                        'subscription_data': conn_state.subscription_data
                    }
                backup_data['connections'] = connections_data
            
            # Collect session data
            if self.config.persist_session_data:
                backup_data['sessions'] = self.session_data.copy()
            
            # Collect subscription data
            if self.config.persist_subscriptions:
                backup_data['subscriptions'] = self.subscription_data.copy()
        
        # Collect Redis session data if available
        if self.redis_client and REDIS_AVAILABLE:
            try:
                redis_sessions = {}
                session_keys = self.redis_client.keys("vedfolnir:session:*")
                for key in session_keys:
                    session_data = self.redis_client.get(key)
                    if session_data:
                        redis_sessions[key.decode()] = json.loads(session_data)
                backup_data['redis_sessions'] = redis_sessions
            except Exception as e:
                self.logger.log_error_event(
                    event_type="redis_backup_error",
                    message=f"Failed to backup Redis sessions: {str(e)}",
                    exception=e
                )
        
        return backup_data
    
    def _perform_recovery(self, backup_data: Dict[str, Any]) -> RecoveryResult:
        """Perform recovery from backup data"""
        
        recovered_connections = 0
        recovered_sessions = 0
        failed_recoveries = 0
        errors = []
        
        try:
            # Recover connections
            if 'connections' in backup_data and self.config.persist_connections:
                for conn_id, conn_data in backup_data['connections'].items():
                    try:
                        connection_state = ConnectionState(
                            session_id=conn_data['session_id'],
                            user_id=conn_data.get('user_id'),
                            connection_id=conn_data['connection_id'],
                            namespace=conn_data['namespace'],
                            rooms=set(conn_data.get('rooms', [])),
                            connected_at=conn_data['connected_at'],
                            last_activity=conn_data['last_activity'],
                            client_info=conn_data.get('client_info', {}),
                            subscription_data=conn_data.get('subscription_data', {})
                        )
                        
                        with self.backup_lock:
                            self.active_connections[conn_id] = connection_state
                        
                        recovered_connections += 1
                        
                    except Exception as e:
                        failed_recoveries += 1
                        errors.append(f"Failed to recover connection {conn_id}: {str(e)}")
            
            # Recover sessions
            if 'sessions' in backup_data and self.config.persist_session_data:
                for session_id, session_info in backup_data['sessions'].items():
                    try:
                        with self.backup_lock:
                            self.session_data[session_id] = session_info
                        recovered_sessions += 1
                        
                    except Exception as e:
                        failed_recoveries += 1
                        errors.append(f"Failed to recover session {session_id}: {str(e)}")
            
            # Recover Redis sessions
            if ('redis_sessions' in backup_data and 
                self.redis_client and REDIS_AVAILABLE):
                for key, session_data in backup_data['redis_sessions'].items():
                    try:
                        self.redis_client.set(key, json.dumps(session_data))
                        recovered_sessions += 1
                        
                    except Exception as e:
                        failed_recoveries += 1
                        errors.append(f"Failed to recover Redis session {key}: {str(e)}")
            
            # Determine overall status
            if failed_recoveries == 0:
                status = RecoveryStatus.SUCCESS
                message = "Recovery completed successfully"
            elif recovered_connections > 0 or recovered_sessions > 0:
                status = RecoveryStatus.PARTIAL
                message = f"Partial recovery completed with {failed_recoveries} failures"
            else:
                status = RecoveryStatus.FAILED
                message = "Recovery failed completely"
            
            return RecoveryResult(
                status=status,
                message=message,
                recovered_connections=recovered_connections,
                recovered_sessions=recovered_sessions,
                failed_recoveries=failed_recoveries,
                recovery_time_seconds=0.0,  # Will be set by caller
                errors=errors
            )
            
        except Exception as e:
            return RecoveryResult(
                status=RecoveryStatus.FAILED,
                message=f"Recovery failed: {str(e)}",
                recovered_connections=recovered_connections,
                recovered_sessions=recovered_sessions,
                failed_recoveries=failed_recoveries + 1,
                recovery_time_seconds=0.0,  # Will be set by caller
                errors=errors + [str(e)]
            )
    
    def _generate_backup_id(self, backup_type: BackupType) -> str:
        """Generate unique backup ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{backup_type.value}_{timestamp}"
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate file checksum"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _save_backup_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata"""
        metadata_file = self.backup_directory / f"{metadata.backup_id}.metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(metadata), f, indent=2, default=str)
    
    def _load_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Load backup metadata"""
        metadata_file = self.backup_directory / f"{backup_id}.metadata.json"
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_data = json.load(f)
                return BackupMetadata(**metadata_data)
        except Exception:
            return None
    
    def _find_backup_file(self, backup_id: str) -> Optional[Path]:
        """Find backup file by ID"""
        # Try compressed first
        backup_file = self.backup_directory / f"websocket_backup_{backup_id}.json.gz"
        if backup_file.exists():
            return backup_file
        
        # Try uncompressed
        backup_file = self.backup_directory / f"websocket_backup_{backup_id}.json"
        if backup_file.exists():
            return backup_file
        
        return None
    
    def _find_latest_backup(self) -> Optional[Path]:
        """Find the latest backup file"""
        backups = self.list_backups()
        if not backups:
            return None
        
        latest_backup = backups[0]  # Already sorted by timestamp
        return Path(latest_backup.file_path)
    
    def _load_backup_data(self, backup_file: Path) -> Optional[Dict[str, Any]]:
        """Load backup data from file"""
        try:
            if backup_file.name.endswith('.gz'):
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.log_error_event(
                event_type="backup_load_error",
                message=f"Failed to load backup data: {backup_file}",
                exception=e
            )
            return None
    
    def _cleanup_old_backups(self) -> None:
        """Clean up old backup files"""
        try:
            backups = self.list_backups()
            if len(backups) <= self.config.max_backup_files:
                return
            
            # Remove oldest backups
            backups_to_remove = backups[self.config.max_backup_files:]
            
            for backup in backups_to_remove:
                try:
                    # Remove backup file
                    backup_path = Path(backup.file_path)
                    if backup_path.exists():
                        backup_path.unlink()
                    
                    # Remove metadata file
                    metadata_path = self.backup_directory / f"{backup.backup_id}.metadata.json"
                    if metadata_path.exists():
                        metadata_path.unlink()
                    
                    self.logger.log_system_event(
                        event_type="backup_cleaned",
                        message=f"Old backup removed: {backup.backup_id}"
                    )
                    
                except Exception as e:
                    self.logger.log_error_event(
                        event_type="backup_cleanup_error",
                        message=f"Failed to remove old backup: {backup.backup_id}",
                        exception=e
                    )
                    
        except Exception as e:
            self.logger.log_error_event(
                event_type="backup_cleanup_failed",
                message=f"Backup cleanup failed: {str(e)}",
                exception=e
            )


def create_backup_manager(config: BackupRecoveryConfig,
                        logger: ProductionWebSocketLogger,
                        socketio: Optional[SocketIO] = None,
                        redis_client: Optional[Any] = None) -> WebSocketBackupManager:
    """
    Factory function to create WebSocket backup manager
    
    Args:
        config: Backup and recovery configuration
        logger: Production WebSocket logger
        socketio: SocketIO instance (optional)
        redis_client: Redis client (optional)
    
    Returns:
        Configured WebSocket backup manager
    """
    return WebSocketBackupManager(config, logger, socketio, redis_client)