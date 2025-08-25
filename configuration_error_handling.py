# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Error Handling and Fallback Mechanisms

Provides comprehensive error handling, graceful degradation, and recovery
mechanisms for the configuration system.
"""

import logging
import time
import threading
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import traceback
import json

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FallbackSource(Enum):
    """Fallback source types"""
    ENVIRONMENT = "environment"
    DATABASE = "database"
    SCHEMA_DEFAULT = "schema_default"
    CACHED_VALUE = "cached_value"
    HARDCODED_DEFAULT = "hardcoded_default"


@dataclass
class ConfigurationError:
    """Configuration error details"""
    error_type: str
    message: str
    key: str
    severity: ErrorSeverity
    timestamp: datetime
    source: str
    traceback: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FallbackAttempt:
    """Fallback attempt details"""
    source: FallbackSource
    success: bool
    value: Any
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class RecoveryAction:
    """Recovery action details"""
    action_type: str
    description: str
    executed_at: datetime
    success: bool
    result: Optional[str] = None


class ConfigurationErrorHandler:
    """
    Comprehensive error handling and recovery for configuration system
    
    Features:
    - Error classification and severity assessment
    - Graceful degradation with fallback chain
    - Error logging and recovery mechanisms
    - Circuit breaker pattern for failing services
    - Automatic retry with exponential backoff
    - Error statistics and monitoring
    """
    
    def __init__(self, max_retries: int = 3, base_retry_delay: float = 1.0,
                 max_retry_delay: float = 60.0, circuit_breaker_threshold: int = 5):
        """
        Initialize error handler
        
        Args:
            max_retries: Maximum number of retry attempts
            base_retry_delay: Base delay between retries in seconds
            max_retry_delay: Maximum delay between retries in seconds
            circuit_breaker_threshold: Number of failures to trigger circuit breaker
        """
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        self.max_retry_delay = max_retry_delay
        self.circuit_breaker_threshold = circuit_breaker_threshold
        
        # Error tracking
        self._errors: List[ConfigurationError] = []
        self._errors_lock = threading.RLock()
        
        # Circuit breaker state
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._circuit_breaker_lock = threading.RLock()
        
        # Fallback cache for last known good values
        self._fallback_cache: Dict[str, Any] = {}
        self._fallback_cache_lock = threading.RLock()
        
        # Recovery actions
        self._recovery_actions: List[RecoveryAction] = []
        self._recovery_lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_severity': {},
            'fallback_attempts': 0,
            'successful_fallbacks': 0,
            'recovery_attempts': 0,
            'successful_recoveries': 0,
            'circuit_breaker_trips': 0
        }
        self._stats_lock = threading.RLock()
    
    def handle_error(self, error_type: str, message: str, key: str, 
                    severity: ErrorSeverity, source: str, 
                    exception: Optional[Exception] = None) -> ConfigurationError:
        """
        Handle configuration error with logging and tracking
        
        Args:
            error_type: Type of error
            message: Error message
            key: Configuration key involved
            severity: Error severity
            source: Source of the error
            exception: Optional exception object
            
        Returns:
            ConfigurationError object
        """
        error = ConfigurationError(
            error_type=error_type,
            message=message,
            key=key,
            severity=severity,
            timestamp=datetime.now(timezone.utc),
            source=source,
            traceback=traceback.format_exc() if exception else None
        )
        
        # Log error based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL configuration error: {message} (key: {key}, source: {source})")
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH severity configuration error: {message} (key: {key}, source: {source})")
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM severity configuration error: {message} (key: {key}, source: {source})")
        else:
            logger.info(f"LOW severity configuration error: {message} (key: {key}, source: {source})")
        
        # Track error
        with self._errors_lock:
            self._errors.append(error)
            # Keep only recent errors (last 1000)
            if len(self._errors) > 1000:
                self._errors = self._errors[-1000:]
        
        # Update statistics
        with self._stats_lock:
            self._stats['total_errors'] += 1
            self._stats['errors_by_type'][error_type] = self._stats['errors_by_type'].get(error_type, 0) + 1
            self._stats['errors_by_severity'][severity.value] = self._stats['errors_by_severity'].get(severity.value, 0) + 1
        
        # Update circuit breaker
        self._update_circuit_breaker(source, False)
        
        return error
    
    def execute_with_fallback(self, key: str, primary_func: Callable[[], Any],
                             fallback_chain: List[Callable[[], Any]],
                             fallback_sources: List[FallbackSource]) -> tuple[Any, List[FallbackAttempt]]:
        """
        Execute function with fallback chain
        
        Args:
            key: Configuration key
            primary_func: Primary function to execute
            fallback_chain: List of fallback functions
            fallback_sources: List of fallback source types
            
        Returns:
            Tuple of (result, fallback_attempts)
        """
        attempts = []
        
        # Try primary function first
        try:
            result = primary_func()
            return result, attempts
        except Exception as e:
            logger.debug(f"Primary function failed for key {key}: {str(e)}")
        
        # Try fallback chain
        for i, (fallback_func, source) in enumerate(zip(fallback_chain, fallback_sources)):
            attempt = FallbackAttempt(source=source, success=False, value=None)
            
            try:
                result = fallback_func()
                attempt.success = True
                attempt.value = result
                attempts.append(attempt)
                
                # Cache successful fallback value
                self._cache_fallback_value(key, result, source)
                
                with self._stats_lock:
                    self._stats['fallback_attempts'] += 1
                    self._stats['successful_fallbacks'] += 1
                
                logger.debug(f"Fallback successful for key {key} using {source.value}")
                return result, attempts
                
            except Exception as e:
                attempt.error = str(e)
                attempts.append(attempt)
                
                with self._stats_lock:
                    self._stats['fallback_attempts'] += 1
                
                logger.debug(f"Fallback failed for key {key} using {source.value}: {str(e)}")
        
        # All fallbacks failed
        raise Exception(f"All fallback attempts failed for key {key}")
    
    def execute_with_retry(self, func: Callable[[], Any], operation_name: str,
                          max_retries: Optional[int] = None) -> Any:
        """
        Execute function with retry logic and exponential backoff
        
        Args:
            func: Function to execute
            operation_name: Name of the operation for logging
            max_retries: Maximum retries (uses default if None)
            
        Returns:
            Function result
        """
        retries = max_retries if max_retries is not None else self.max_retries
        delay = self.base_retry_delay
        
        for attempt in range(retries + 1):
            try:
                result = func()
                if attempt > 0:
                    logger.info(f"Operation {operation_name} succeeded after {attempt} retries")
                return result
                
            except Exception as e:
                if attempt == retries:
                    logger.error(f"Operation {operation_name} failed after {retries} retries: {str(e)}")
                    raise
                
                logger.warning(f"Operation {operation_name} failed (attempt {attempt + 1}/{retries + 1}): {str(e)}")
                time.sleep(delay)
                delay = min(delay * 2, self.max_retry_delay)  # Exponential backoff
    
    def is_circuit_breaker_open(self, source: str) -> bool:
        """
        Check if circuit breaker is open for a source
        
        Args:
            source: Source to check
            
        Returns:
            True if circuit breaker is open
        """
        with self._circuit_breaker_lock:
            breaker = self._circuit_breakers.get(source, {})
            return breaker.get('is_open', False)
    
    def reset_circuit_breaker(self, source: str) -> bool:
        """
        Reset circuit breaker for a source
        
        Args:
            source: Source to reset
            
        Returns:
            True if reset was successful
        """
        with self._circuit_breaker_lock:
            if source in self._circuit_breakers:
                self._circuit_breakers[source] = {
                    'failure_count': 0,
                    'is_open': False,
                    'last_failure': None,
                    'opened_at': None
                }
                logger.info(f"Circuit breaker reset for source: {source}")
                return True
            return False
    
    def get_fallback_value(self, key: str) -> Optional[Any]:
        """
        Get cached fallback value for a key
        
        Args:
            key: Configuration key
            
        Returns:
            Cached fallback value or None
        """
        with self._fallback_cache_lock:
            return self._fallback_cache.get(key)
    
    def cache_fallback_value(self, key: str, value: Any, source: FallbackSource):
        """
        Cache a fallback value for future use
        
        Args:
            key: Configuration key
            value: Value to cache
            source: Source of the value
        """
        self._cache_fallback_value(key, value, source)
    
    def execute_recovery_action(self, action_type: str, description: str,
                               action_func: Callable[[], Any]) -> RecoveryAction:
        """
        Execute a recovery action
        
        Args:
            action_type: Type of recovery action
            description: Description of the action
            action_func: Function to execute
            
        Returns:
            RecoveryAction object
        """
        action = RecoveryAction(
            action_type=action_type,
            description=description,
            executed_at=datetime.now(timezone.utc),
            success=False
        )
        
        try:
            result = action_func()
            action.success = True
            action.result = str(result) if result is not None else "Success"
            
            with self._stats_lock:
                self._stats['recovery_attempts'] += 1
                self._stats['successful_recoveries'] += 1
            
            logger.info(f"Recovery action successful: {description}")
            
        except Exception as e:
            action.result = f"Failed: {str(e)}"
            
            with self._stats_lock:
                self._stats['recovery_attempts'] += 1
            
            logger.error(f"Recovery action failed: {description} - {str(e)}")
        
        with self._recovery_lock:
            self._recovery_actions.append(action)
            # Keep only recent actions (last 100)
            if len(self._recovery_actions) > 100:
                self._recovery_actions = self._recovery_actions[-100:]
        
        return action
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get error summary for the specified time period
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with error summary
        """
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        
        with self._errors_lock:
            recent_errors = [
                error for error in self._errors
                if error.timestamp.timestamp() > cutoff_time
            ]
        
        # Group errors by type and severity
        errors_by_type = {}
        errors_by_severity = {}
        errors_by_key = {}
        
        for error in recent_errors:
            errors_by_type[error.error_type] = errors_by_type.get(error.error_type, 0) + 1
            errors_by_severity[error.severity.value] = errors_by_severity.get(error.severity.value, 0) + 1
            errors_by_key[error.key] = errors_by_key.get(error.key, 0) + 1
        
        return {
            'time_period_hours': hours,
            'total_errors': len(recent_errors),
            'errors_by_type': errors_by_type,
            'errors_by_severity': errors_by_severity,
            'errors_by_key': errors_by_key,
            'most_problematic_keys': sorted(errors_by_key.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all circuit breakers
        
        Returns:
            Dictionary with circuit breaker status
        """
        with self._circuit_breaker_lock:
            return {
                source: {
                    'is_open': breaker.get('is_open', False),
                    'failure_count': breaker.get('failure_count', 0),
                    'last_failure': breaker.get('last_failure'),
                    'opened_at': breaker.get('opened_at')
                }
                for source, breaker in self._circuit_breakers.items()
            }
    
    def get_recovery_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recovery action history
        
        Args:
            limit: Maximum number of actions to return
            
        Returns:
            List of recovery action dictionaries
        """
        with self._recovery_lock:
            recent_actions = self._recovery_actions[-limit:] if self._recovery_actions else []
        
        return [
            {
                'action_type': action.action_type,
                'description': action.description,
                'executed_at': action.executed_at,
                'success': action.success,
                'result': action.result
            }
            for action in recent_actions
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive error handling statistics
        
        Returns:
            Dictionary with statistics
        """
        with self._stats_lock:
            stats = self._stats.copy()
        
        # Add additional computed statistics
        stats['fallback_success_rate'] = (
            stats['successful_fallbacks'] / stats['fallback_attempts']
            if stats['fallback_attempts'] > 0 else 0.0
        )
        
        stats['recovery_success_rate'] = (
            stats['successful_recoveries'] / stats['recovery_attempts']
            if stats['recovery_attempts'] > 0 else 0.0
        )
        
        with self._errors_lock:
            stats['recent_errors_count'] = len(self._errors)
        
        with self._circuit_breaker_lock:
            stats['active_circuit_breakers'] = len([
                cb for cb in self._circuit_breakers.values()
                if cb.get('is_open', False)
            ])
            stats['total_circuit_breakers'] = len(self._circuit_breakers)
        
        return stats
    
    def _update_circuit_breaker(self, source: str, success: bool):
        """Update circuit breaker state for a source"""
        with self._circuit_breaker_lock:
            if source not in self._circuit_breakers:
                self._circuit_breakers[source] = {
                    'failure_count': 0,
                    'is_open': False,
                    'last_failure': None,
                    'opened_at': None
                }
            
            breaker = self._circuit_breakers[source]
            
            if success:
                # Reset on success
                breaker['failure_count'] = 0
                if breaker['is_open']:
                    breaker['is_open'] = False
                    breaker['opened_at'] = None
                    logger.info(f"Circuit breaker closed for source: {source}")
            else:
                # Increment failure count
                breaker['failure_count'] += 1
                breaker['last_failure'] = datetime.now(timezone.utc)
                
                # Open circuit breaker if threshold reached
                if breaker['failure_count'] >= self.circuit_breaker_threshold and not breaker['is_open']:
                    breaker['is_open'] = True
                    breaker['opened_at'] = datetime.now(timezone.utc)
                    
                    with self._stats_lock:
                        self._stats['circuit_breaker_trips'] += 1
                    
                    logger.warning(f"Circuit breaker opened for source: {source} after {breaker['failure_count']} failures")
    
    def _cache_fallback_value(self, key: str, value: Any, source: FallbackSource):
        """Cache a fallback value"""
        with self._fallback_cache_lock:
            self._fallback_cache[key] = {
                'value': value,
                'source': source,
                'cached_at': datetime.now(timezone.utc)
            }
            
            # Keep cache size reasonable (last 500 values)
            if len(self._fallback_cache) > 500:
                # Remove oldest entries
                sorted_items = sorted(
                    self._fallback_cache.items(),
                    key=lambda x: x[1]['cached_at']
                )
                self._fallback_cache = dict(sorted_items[-500:])


# Global error handler instance
_global_error_handler: Optional[ConfigurationErrorHandler] = None
_error_handler_lock = threading.Lock()


def get_error_handler() -> ConfigurationErrorHandler:
    """Get global error handler instance"""
    global _global_error_handler
    
    with _error_handler_lock:
        if _global_error_handler is None:
            _global_error_handler = ConfigurationErrorHandler()
        return _global_error_handler


def set_error_handler(handler: ConfigurationErrorHandler):
    """Set global error handler instance"""
    global _global_error_handler
    
    with _error_handler_lock:
        _global_error_handler = handler