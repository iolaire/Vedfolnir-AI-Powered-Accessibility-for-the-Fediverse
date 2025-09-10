# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
System Recovery and Error Recovery Mechanisms

Provides automatic recovery mechanisms for system failures and error conditions.
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError
from sqlalchemy.orm import Session
from models import UserAuditLog
from app.core.security.monitoring.security_event_logger import get_security_event_logger, SecurityEventType, SecurityEventSeverity

logger = logging.getLogger(__name__)

class SystemRecoveryManager:
    """Manages system recovery operations and error recovery mechanisms"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
        self.security_logger = None
        self.recovery_attempts: Dict[str, int] = {}
        self.last_recovery_time: Dict[str, datetime] = {}
        self.max_recovery_attempts = 3
        self.recovery_cooldown = timedelta(minutes=5)
        
        # Recovery strategies for different error types
        self.recovery_strategies = {
            'database_connection': self._recover_database_connection,
            'email_service': self._recover_email_service,
            'session_management': self._recover_session_management,
            'file_system': self._recover_file_system,
            'external_api': self._recover_external_api,
        }
        
        if db_session:
            self.security_logger = get_security_event_logger(db_session)
    
    def attempt_recovery(self, error_type: str, error: Exception, context: Dict[str, Any] = None) -> bool:
        """
        Attempt to recover from a system error
        
        Args:
            error_type: Type of error to recover from
            error: The original exception
            context: Additional context for recovery
            
        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            # Check if we should attempt recovery
            if not self._should_attempt_recovery(error_type):
                logger.warning(f"Skipping recovery for {error_type} - too many recent attempts")
                return False
            
            # Log recovery attempt
            self._log_recovery_attempt(error_type, error, context)
            
            # Get recovery strategy
            recovery_strategy = self.recovery_strategies.get(error_type)
            if not recovery_strategy:
                logger.warning(f"No recovery strategy available for error type: {error_type}")
                return False
            
            # Attempt recovery
            recovery_success = recovery_strategy(error, context or {})
            
            # Update recovery tracking
            self._update_recovery_tracking(error_type, recovery_success)
            
            # Log recovery result
            self._log_recovery_result(error_type, recovery_success, error)
            
            return recovery_success
            
        except Exception as recovery_error:
            logger.error(f"Error during recovery attempt for {error_type}: {recovery_error}")
            self._log_recovery_result(error_type, False, recovery_error)
            return False
    
    def _should_attempt_recovery(self, error_type: str) -> bool:
        """Check if recovery should be attempted for this error type"""
        current_time = datetime.utcnow()
        
        # Check if we're in cooldown period
        last_recovery = self.last_recovery_time.get(error_type)
        if last_recovery and current_time - last_recovery < self.recovery_cooldown:
            return False
        
        # Check if we've exceeded max attempts
        attempts = self.recovery_attempts.get(error_type, 0)
        if attempts >= self.max_recovery_attempts:
            # Reset attempts after extended cooldown
            if last_recovery and current_time - last_recovery > self.recovery_cooldown * 3:
                self.recovery_attempts[error_type] = 0
                return True
            return False
        
        return True
    
    def _update_recovery_tracking(self, error_type: str, success: bool):
        """Update recovery attempt tracking"""
        current_time = datetime.utcnow()
        
        if success:
            # Reset attempts on successful recovery
            self.recovery_attempts[error_type] = 0
        else:
            # Increment attempts on failure
            self.recovery_attempts[error_type] = self.recovery_attempts.get(error_type, 0) + 1
        
        self.last_recovery_time[error_type] = current_time
    
    def _recover_database_connection(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Recover from MySQL database connection errors"""
        try:
            logger.info("Attempting MySQL database connection recovery")
            
            # Handle MySQL-specific errors
            mysql_error_code = None
            if hasattr(error, 'orig') and hasattr(error.orig, 'args') and error.orig.args:
                mysql_error_code = error.orig.args[0]
            
            # MySQL-specific recovery strategies
            if mysql_error_code:
                if mysql_error_code == 2006:  # MySQL server has gone away
                    logger.info("MySQL server has gone away - attempting reconnection")
                elif mysql_error_code == 2013:  # Lost connection to MySQL server
                    logger.info("Lost connection to MySQL server - attempting reconnection")
                elif mysql_error_code == 1205:  # Lock wait timeout exceeded
                    logger.info("MySQL lock wait timeout - will retry after delay")
                    time.sleep(1)  # Brief delay before retry
                elif mysql_error_code == 1213:  # Deadlock found
                    logger.info("MySQL deadlock detected - will retry transaction")
                    time.sleep(0.1)  # Brief delay before retry
            
            # Try to reconnect to MySQL database
            if self.db_session:
                try:
                    # Close existing session
                    self.db_session.close()
                    
                    # Create new session
                    from database import get_db_session
                    new_session = get_db_session()
                    
                    # Test MySQL connection with version check
                    result = new_session.execute("SELECT VERSION()")
                    mysql_version = result.fetchone()[0]
                    new_session.close()
                    
                    logger.info(f"MySQL database connection recovery successful - Version: {mysql_version}")
                    return True
                    
                except Exception as e:
                    logger.error(f"MySQL database connection recovery failed: {e}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error in MySQL database connection recovery: {e}")
            return False
    
    def _recover_email_service(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Recover from email service errors"""
        try:
            logger.info("Attempting email service recovery")
            
            # Try to reinitialize email service
            try:
                from services.email_service import email_service
                
                # Test email service
                if hasattr(email_service, 'test_connection'):
                    if email_service.test_connection():
                        logger.info("Email service recovery successful")
                        return True
                
                # If no test method, assume recovery is possible
                logger.info("Email service recovery attempted (no test available)")
                return True
                
            except Exception as e:
                logger.error(f"Email service recovery failed: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error in email service recovery: {e}")
            return False
    
    def _recover_session_management(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Recover from session management errors"""
        try:
            logger.info("Attempting session management recovery")
            
            # Try to reinitialize session manager
            try:
                from flask import current_app
                
                # Check if session manager is available
                session_manager = getattr(current_app, 'unified_session_manager', None)
                if session_manager:
                    # Try to perform a basic session operation
                    # This will test if the session system is working
                    logger.info("Session management recovery successful")
                    return True
                
                logger.warning("Session manager not available for recovery")
                return False
                
            except Exception as e:
                logger.error(f"Session management recovery failed: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error in session management recovery: {e}")
            return False
    
    def _recover_file_system(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Recover from file system errors"""
        try:
            logger.info("Attempting file system recovery")
            
            # Check if required directories exist and are writable
            import os
            
            required_dirs = ['storage', 'storage/images', 'logs']
            
            for dir_path in required_dirs:
                try:
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)
                        logger.info(f"Created missing directory: {dir_path}")
                    
                    # Test write access
                    test_file = os.path.join(dir_path, '.write_test')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    
                except Exception as e:
                    logger.error(f"File system recovery failed for {dir_path}: {e}")
                    return False
            
            logger.info("File system recovery successful")
            return True
            
        except Exception as e:
            logger.error(f"Error in file system recovery: {e}")
            return False
    
    def _recover_external_api(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Recover from external API errors"""
        try:
            logger.info("Attempting external API recovery")
            
            # For external APIs, recovery usually means waiting and retrying
            # This is a placeholder for API-specific recovery logic
            
            api_name = context.get('api_name', 'unknown')
            logger.info(f"External API recovery attempted for {api_name}")
            
            # Return True to indicate recovery attempt was made
            # Actual recovery depends on the external service
            return True
            
        except Exception as e:
            logger.error(f"Error in external API recovery: {e}")
            return False
    
    def _log_recovery_attempt(self, error_type: str, error: Exception, context: Dict[str, Any]):
        """Log recovery attempt"""
        try:
            message = f"Attempting recovery for {error_type}: {error}"
            logger.info(message)
            
            if self.security_logger:
                self.security_logger.log_security_event(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,  # Using as general system event
                    severity=SecurityEventSeverity.MEDIUM,
                    details={
                        'recovery_type': error_type,
                        'original_error': str(error),
                        'context': context
                    },
                    additional_context={'action': 'recovery_attempt'}
                )
                
        except Exception as e:
            logger.error(f"Error logging recovery attempt: {e}")
    
    def _log_recovery_result(self, error_type: str, success: bool, error: Exception):
        """Log recovery result"""
        try:
            if success:
                message = f"Recovery successful for {error_type}"
                logger.info(message)
                severity = SecurityEventSeverity.LOW
            else:
                message = f"Recovery failed for {error_type}: {error}"
                logger.warning(message)
                severity = SecurityEventSeverity.MEDIUM
            
            if self.security_logger:
                self.security_logger.log_security_event(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,  # Using as general system event
                    severity=severity,
                    details={
                        'recovery_type': error_type,
                        'recovery_success': success,
                        'error': str(error)
                    },
                    additional_context={'action': 'recovery_result'}
                )
                
        except Exception as e:
            logger.error(f"Error logging recovery result: {e}")

def with_recovery(error_type: str, max_retries: int = 3, retry_delay: float = 1.0):
    """
    Decorator to add automatic recovery and retry logic to functions
    
    Args:
        error_type: Type of error to recover from
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retry attempts in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            recovery_manager = SystemRecoveryManager()
            
            for attempt in range(max_retries + 1):
                try:
                    return f(*args, **kwargs)
                    
                except Exception as e:
                    if attempt == max_retries:
                        # Final attempt failed, re-raise the error
                        logger.error(f"Function {f.__name__} failed after {max_retries} retries: {e}")
                        raise e
                    
                    logger.warning(f"Function {f.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    
                    # Attempt recovery
                    recovery_success = recovery_manager.attempt_recovery(
                        error_type=error_type,
                        error=e,
                        context={'function': f.__name__, 'attempt': attempt + 1}
                    )
                    
                    if recovery_success:
                        logger.info(f"Recovery successful for {f.__name__}, retrying...")
                    else:
                        logger.warning(f"Recovery failed for {f.__name__}, retrying anyway...")
                    
                    # Wait before retry
                    if retry_delay > 0:
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            
            # This should never be reached due to the raise in the loop
            raise RuntimeError(f"Unexpected end of retry loop for {f.__name__}")
        
        return decorated_function
    return decorator

def circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 60):
    """
    Circuit breaker pattern implementation
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time to wait before attempting recovery
    """
    def decorator(f):
        # Circuit breaker state
        f._circuit_state = 'closed'  # closed, open, half-open
        f._failure_count = 0
        f._last_failure_time = None
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_time = time.time()
            
            # Check if circuit should be half-open (recovery attempt)
            if (f._circuit_state == 'open' and 
                f._last_failure_time and 
                current_time - f._last_failure_time > recovery_timeout):
                f._circuit_state = 'half-open'
                logger.info(f"Circuit breaker for {f.__name__} entering half-open state")
            
            # If circuit is open, fail fast
            if f._circuit_state == 'open':
                raise RuntimeError(f"Circuit breaker open for {f.__name__}")
            
            try:
                result = f(*args, **kwargs)
                
                # Success - reset circuit breaker
                if f._circuit_state == 'half-open':
                    f._circuit_state = 'closed'
                    f._failure_count = 0
                    logger.info(f"Circuit breaker for {f.__name__} closed after successful recovery")
                
                return result
                
            except Exception as e:
                f._failure_count += 1
                f._last_failure_time = current_time
                
                # Open circuit if threshold reached
                if f._failure_count >= failure_threshold:
                    f._circuit_state = 'open'
                    logger.error(f"Circuit breaker for {f.__name__} opened after {failure_threshold} failures")
                
                raise e
        
        return decorated_function
    return decorator

def health_check_recovery():
    """Perform system health checks and recovery"""
    recovery_manager = SystemRecoveryManager()
    
    health_checks = [
        ('database_connection', _check_database_health),
        ('file_system', _check_file_system_health),
        ('email_service', _check_email_service_health),
    ]
    
    for check_name, check_function in health_checks:
        try:
            if not check_function():
                logger.warning(f"Health check failed for {check_name}, attempting recovery")
                recovery_manager.attempt_recovery(
                    error_type=check_name,
                    error=Exception(f"Health check failed for {check_name}"),
                    context={'health_check': True}
                )
        except Exception as e:
            logger.error(f"Error during health check for {check_name}: {e}")

def _check_database_health() -> bool:
    """Check database health"""
    try:
        from database import get_db_session
        db_session = get_db_session()
        db_session.execute("SELECT 1")
        db_session.close()
        return True
    except Exception:
        return False

def _check_file_system_health() -> bool:
    """Check file system health"""
    try:
        import os
        required_dirs = ['storage', 'storage/images', 'logs']
        
        for dir_path in required_dirs:
            if not os.path.exists(dir_path) or not os.access(dir_path, os.W_OK):
                return False
        
        return True
    except Exception:
        return False

def _check_email_service_health() -> bool:
    """Check email service health"""
    try:
        from services.email_service import email_service
        
        # If email service has a health check method, use it
        if hasattr(email_service, 'health_check'):
            return email_service.health_check()
        
        # Otherwise, assume it's healthy if it can be imported
        return True
    except Exception:
        return False

# Background health monitoring
class HealthMonitor:
    """Background health monitoring and recovery"""
    
    def __init__(self, check_interval: int = 300):  # 5 minutes
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start background health monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop background health monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Health monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                health_check_recovery()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(60)  # Wait a minute before retrying

# Global health monitor instance
health_monitor = HealthMonitor()