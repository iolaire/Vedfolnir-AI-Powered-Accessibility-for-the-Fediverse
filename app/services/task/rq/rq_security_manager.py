# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Security Manager

Provides security controls and data protection for Redis Queue operations.
Integrates with existing security mechanisms and adds RQ-specific protections.
"""

import logging
import json
import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
import redis

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
from app.core.security.core.security_utils import sanitize_for_log, mask_sensitive_data
from models import CaptionGenerationTask, User, UserRole

logger = logging.getLogger(__name__)


class RQSecurityManager:
    """Security manager for RQ operations with encryption and access control"""
    
    def __init__(self, db_manager: DatabaseManager, redis_connection: redis.Redis, 
                 caption_security_manager: CaptionSecurityManager):
        """
        Initialize RQ Security Manager
        
        Args:
            db_manager: Database manager instance
            redis_connection: Redis connection for secure operations
            caption_security_manager: Existing caption security manager
        """
        self.db_manager = db_manager
        self.redis_connection = redis_connection
        self.caption_security_manager = caption_security_manager
        
        # Initialize encryption
        self._cipher = self._initialize_encryption()
        
        # Security configuration
        self.sensitive_fields = {
            'access_token', 'client_key', 'client_secret', 'password',
            'api_key', 'bearer_token', 'oauth_token'
        }
        
        # Redis key prefixes for security
        self.security_prefix = "rq:security:"
        self.task_auth_prefix = f"{self.security_prefix}task_auth:"
        self.worker_auth_prefix = f"{self.security_prefix}worker_auth:"
        
        logger.info("RQ Security Manager initialized")
    
    def _initialize_encryption(self) -> Fernet:
        """Initialize encryption using existing platform encryption key"""
        try:
            import os
            key = os.getenv('PLATFORM_ENCRYPTION_KEY')
            if not key:
                raise ValueError("PLATFORM_ENCRYPTION_KEY not found in environment")
            
            if isinstance(key, str):
                key = key.encode()
            
            return Fernet(key)
            
        except Exception as e:
            logger.error(f"Failed to initialize RQ encryption: {sanitize_for_log(str(e))}")
            raise
    
    def generate_secure_task_id(self) -> str:
        """Generate cryptographically secure task ID using existing security manager"""
        return self.caption_security_manager.generate_secure_task_id()
    
    def validate_task_id(self, task_id: str) -> bool:
        """Validate task ID format using existing security manager"""
        return self.caption_security_manager.validate_task_id(task_id)
    
    def encrypt_task_data(self, task_data: Dict[str, Any]) -> bytes:
        """
        Encrypt sensitive task data for Redis storage
        
        Args:
            task_data: Task data dictionary to encrypt
            
        Returns:
            Encrypted task data as bytes
        """
        try:
            # Create a copy to avoid modifying original
            data_copy = task_data.copy()
            
            # Encrypt sensitive fields
            for field in self.sensitive_fields:
                if field in data_copy and data_copy[field]:
                    # Mark field as encrypted and encrypt value
                    encrypted_value = self._cipher.encrypt(str(data_copy[field]).encode()).decode()
                    data_copy[field] = {
                        'encrypted': True,
                        'value': encrypted_value
                    }
            
            # Add encryption metadata
            data_copy['_encryption_metadata'] = {
                'encrypted_at': datetime.now(timezone.utc).isoformat(),
                'version': '1.0',
                'fields_encrypted': list(self.sensitive_fields.intersection(task_data.keys()))
            }
            
            # Serialize and encrypt entire payload
            json_data = json.dumps(data_copy, default=str)
            encrypted_data = self._cipher.encrypt(json_data.encode())
            
            logger.debug(f"Encrypted task data with {len(data_copy.get('_encryption_metadata', {}).get('fields_encrypted', []))} sensitive fields")
            return encrypted_data
            
        except Exception as e:
            logger.error(f"Failed to encrypt task data: {sanitize_for_log(str(e))}")
            raise
    
    def decrypt_task_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """
        Decrypt task data from Redis storage
        
        Args:
            encrypted_data: Encrypted task data bytes
            
        Returns:
            Decrypted task data dictionary
        """
        try:
            # Decrypt entire payload
            decrypted_json = self._cipher.decrypt(encrypted_data).decode()
            data = json.loads(decrypted_json)
            
            # Decrypt individual sensitive fields
            for field in self.sensitive_fields:
                if field in data and isinstance(data[field], dict) and data[field].get('encrypted'):
                    encrypted_value = data[field]['value']
                    decrypted_value = self._cipher.decrypt(encrypted_value.encode()).decode()
                    data[field] = decrypted_value
            
            # Remove encryption metadata
            data.pop('_encryption_metadata', None)
            
            logger.debug("Successfully decrypted task data")
            return data
            
        except Exception as e:
            logger.error(f"Failed to decrypt task data: {sanitize_for_log(str(e))}")
            raise
    
    def validate_worker_authentication(self, worker_id: str, worker_token: str) -> bool:
        """
        Validate RQ worker authentication and authorization
        
        Args:
            worker_id: Unique worker identifier
            worker_token: Worker authentication token
            
        Returns:
            True if worker is authenticated and authorized
        """
        try:
            # Check worker authentication in Redis
            auth_key = f"{self.worker_auth_prefix}{worker_id}"
            stored_token_hash = self.redis_connection.get(auth_key)
            
            if not stored_token_hash:
                logger.warning(f"Worker authentication failed - no token found for worker {sanitize_for_log(worker_id)}")
                return False
            
            # Verify token hash
            token_hash = hashlib.sha256(worker_token.encode()).hexdigest()
            if token_hash != stored_token_hash.decode():
                logger.warning(f"Worker authentication failed - invalid token for worker {sanitize_for_log(worker_id)}")
                return False
            
            # Update last seen timestamp
            self.redis_connection.hset(
                f"{self.worker_auth_prefix}metadata:{worker_id}",
                "last_seen",
                datetime.now(timezone.utc).isoformat()
            )
            
            logger.debug(f"Worker {sanitize_for_log(worker_id)} authenticated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Worker authentication error: {sanitize_for_log(str(e))}")
            return False
    
    def register_worker_authentication(self, worker_id: str, worker_token: str, ttl: int = 3600) -> None:
        """
        Register worker authentication credentials
        
        Args:
            worker_id: Unique worker identifier
            worker_token: Worker authentication token
            ttl: Token time-to-live in seconds
        """
        try:
            # Hash the token for storage
            token_hash = hashlib.sha256(worker_token.encode()).hexdigest()
            
            # Store authentication
            auth_key = f"{self.worker_auth_prefix}{worker_id}"
            self.redis_connection.setex(auth_key, ttl, token_hash)
            
            # Store metadata
            metadata_key = f"{self.worker_auth_prefix}metadata:{worker_id}"
            self.redis_connection.hset(metadata_key, mapping={
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "ttl": ttl,
                "status": "active"
            })
            self.redis_connection.expire(metadata_key, ttl)
            
            logger.info(f"Registered authentication for worker {sanitize_for_log(worker_id)}")
            
        except Exception as e:
            logger.error(f"Failed to register worker authentication: {sanitize_for_log(str(e))}")
            raise
    
    def validate_task_access(self, task_id: str, user_id: int) -> bool:
        """
        Validate user access to a specific task
        
        Args:
            task_id: Task identifier
            user_id: User identifier
            
        Returns:
            True if user has access to the task
        """
        try:
            # Use existing caption security manager for task ownership validation
            if not self.caption_security_manager.check_task_ownership(task_id, user_id):
                logger.warning(f"Task access denied - user {sanitize_for_log(str(user_id))} does not own task {sanitize_for_log(task_id)}")
                return False
            
            # Additional RQ-specific access checks
            return self._validate_rq_task_access(task_id, user_id)
            
        except Exception as e:
            logger.error(f"Task access validation error: {sanitize_for_log(str(e))}")
            return False
    
    def _validate_rq_task_access(self, task_id: str, user_id: int) -> bool:
        """RQ-specific task access validation"""
        try:
            # Check if task is in RQ system
            task_auth_key = f"{self.task_auth_prefix}{task_id}"
            task_auth_data = self.redis_connection.hgetall(task_auth_key)
            
            if task_auth_data:
                stored_user_id = task_auth_data.get(b'user_id', b'').decode()
                if stored_user_id and int(stored_user_id) != user_id:
                    logger.warning(f"RQ task access mismatch - stored user {stored_user_id} vs requesting user {user_id}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"RQ task access validation error: {sanitize_for_log(str(e))}")
            return False
    
    def store_task_authorization(self, task_id: str, user_id: int, platform_connection_id: int, ttl: int = 7200) -> None:
        """
        Store task authorization information in Redis
        
        Args:
            task_id: Task identifier
            user_id: User identifier
            platform_connection_id: Platform connection identifier
            ttl: Authorization time-to-live in seconds
        """
        try:
            task_auth_key = f"{self.task_auth_prefix}{task_id}"
            
            auth_data = {
                "user_id": str(user_id),
                "platform_connection_id": str(platform_connection_id),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "ttl": str(ttl)
            }
            
            self.redis_connection.hset(task_auth_key, mapping=auth_data)
            self.redis_connection.expire(task_auth_key, ttl)
            
            logger.debug(f"Stored authorization for task {sanitize_for_log(task_id)}")
            
        except Exception as e:
            logger.error(f"Failed to store task authorization: {sanitize_for_log(str(e))}")
            raise
    
    def validate_user_permissions(self, user_id: int, required_permissions: List[str]) -> bool:
        """
        Validate user permissions for RQ operations
        
        Args:
            user_id: User identifier
            required_permissions: List of required permissions
            
        Returns:
            True if user has all required permissions
        """
        try:
            session = self.db_manager.get_session()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    logger.warning(f"User not found for permission validation: {sanitize_for_log(str(user_id))}")
                    return False
                
                # Check user role permissions
                user_permissions = self._get_user_permissions(user.role)
                
                # Validate all required permissions
                for permission in required_permissions:
                    if permission not in user_permissions:
                        logger.warning(f"User {sanitize_for_log(str(user_id))} lacks permission: {sanitize_for_log(permission)}")
                        return False
                
                return True
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"User permission validation error: {sanitize_for_log(str(e))}")
            return False
    
    def _get_user_permissions(self, role: UserRole) -> List[str]:
        """Get permissions for user role"""
        permissions_map = {
            UserRole.ADMIN: [
                'rq:task:create', 'rq:task:view', 'rq:task:cancel', 'rq:task:retry',
                'rq:queue:manage', 'rq:worker:manage', 'rq:system:monitor'
            ],
            UserRole.REVIEWER: [
                'rq:task:create', 'rq:task:view', 'rq:task:cancel'
            ]
        }
        
        # Handle USER role which might not exist in some versions
        try:
            permissions_map[UserRole.USER] = ['rq:task:create', 'rq:task:view']
        except AttributeError:
            # USER role doesn't exist, use a default mapping
            pass
        
        return permissions_map.get(role, [])
    
    def sanitize_error_message(self, error_message: str, task_id: str = None) -> str:
        """
        Sanitize error messages to prevent information leakage
        
        Args:
            error_message: Original error message
            task_id: Optional task ID for context
            
        Returns:
            Sanitized error message safe for logging and user display
        """
        try:
            # Use existing sanitization
            sanitized = sanitize_for_log(error_message)
            
            # Remove sensitive patterns
            sensitive_patterns = [
                r'password[=:]\s*\S+',
                r'token[=:]\s*\S+',
                r'key[=:]\s*\S+',
                r'secret[=:]\s*\S+',
                r'api[_-]?key[=:]\s*\S+',
                r'access[_-]?token[=:]\s*\S+',
                r'bearer\s+\S+',
                r'authorization:\s*\S+',
                r'/[a-zA-Z0-9+/]{20,}={0,2}',  # Base64 patterns
                r'[a-f0-9]{32,}',  # Hex patterns (potential tokens)
            ]
            
            for pattern in sensitive_patterns:
                sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
            
            # Mask file paths
            sanitized = re.sub(r'/[a-zA-Z0-9_/.-]+', '[PATH]', sanitized)
            
            # Add task context if provided
            if task_id:
                sanitized = f"Task {mask_sensitive_data(task_id, visible_chars=8)}: {sanitized}"
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Error sanitizing error message: {str(e)}")
            return "[ERROR MESSAGE SANITIZATION FAILED]"
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], 
                          severity: str = "INFO", user_id: int = None) -> None:
        """
        Log security events for RQ operations
        
        Args:
            event_type: Type of security event
            details: Event details dictionary
            severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
            user_id: Optional user ID associated with event
        """
        try:
            # Sanitize all details
            sanitized_details = {}
            for key, value in details.items():
                if key in self.sensitive_fields:
                    sanitized_details[key] = mask_sensitive_data(str(value))
                else:
                    sanitized_details[key] = sanitize_for_log(str(value))
            
            # Create security event record
            event_record = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                'severity': severity,
                'user_id': user_id,
                'details': sanitized_details,
                'component': 'RQ_SECURITY'
            }
            
            # Log based on severity
            log_message = f"RQ Security Event [{event_type}]: {sanitized_details}"
            
            if severity == "CRITICAL":
                logger.critical(log_message)
            elif severity == "ERROR":
                logger.error(log_message)
            elif severity == "WARNING":
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            # Store in Redis for security monitoring (optional)
            try:
                security_log_key = f"{self.security_prefix}events:{datetime.now().strftime('%Y%m%d')}"
                self.redis_connection.lpush(security_log_key, json.dumps(event_record))
                self.redis_connection.expire(security_log_key, 86400 * 7)  # 7 days retention
            except Exception as redis_error:
                logger.warning(f"Failed to store security event in Redis: {sanitize_for_log(str(redis_error))}")
            
        except Exception as e:
            logger.error(f"Failed to log security event: {sanitize_for_log(str(e))}")
    
    def cleanup_expired_auth_data(self) -> int:
        """
        Clean up expired authentication and authorization data
        
        Returns:
            Number of expired entries cleaned up
        """
        try:
            cleaned_count = 0
            
            # Clean up expired worker auth
            worker_pattern = f"{self.worker_auth_prefix}*"
            for key in self.redis_connection.scan_iter(match=worker_pattern):
                if self.redis_connection.ttl(key) == -1:  # No TTL set
                    self.redis_connection.delete(key)
                    cleaned_count += 1
            
            # Clean up expired task auth
            task_pattern = f"{self.task_auth_prefix}*"
            for key in self.redis_connection.scan_iter(match=task_pattern):
                if self.redis_connection.ttl(key) == -1:  # No TTL set
                    self.redis_connection.delete(key)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired authentication entries")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired auth data: {sanitize_for_log(str(e))}")
            return 0
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """
        Get security metrics for monitoring
        
        Returns:
            Dictionary containing security metrics
        """
        try:
            metrics = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'active_workers': 0,
                'active_task_auths': 0,
                'security_events_today': 0,
                'encryption_status': 'active'
            }
            
            # Count active workers
            worker_pattern = f"{self.worker_auth_prefix}*"
            metrics['active_workers'] = len(list(self.redis_connection.scan_iter(match=worker_pattern)))
            
            # Count active task authorizations
            task_pattern = f"{self.task_auth_prefix}*"
            metrics['active_task_auths'] = len(list(self.redis_connection.scan_iter(match=task_pattern)))
            
            # Count security events today
            today_key = f"{self.security_prefix}events:{datetime.now().strftime('%Y%m%d')}"
            metrics['security_events_today'] = self.redis_connection.llen(today_key)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get security metrics: {sanitize_for_log(str(e))}")
            return {'error': 'Failed to retrieve security metrics'}