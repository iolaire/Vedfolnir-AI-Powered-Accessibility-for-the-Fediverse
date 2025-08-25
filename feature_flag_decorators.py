# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Feature Flag Decorators

Provides decorators for enforcing feature flags in application components,
including Flask routes, service methods, and background tasks.
"""

import logging
from functools import wraps
from typing import Callable, Any, Optional, Union
from flask import jsonify, render_template, request, current_app, abort
import asyncio

from feature_flag_service import FeatureFlagService

logger = logging.getLogger(__name__)


def require_feature_flag(feature_key: str, 
                        disabled_message: str = None,
                        disabled_template: str = None,
                        disabled_json_response: dict = None,
                        graceful_degradation: bool = False):
    """
    Decorator to require a feature flag to be enabled
    
    Args:
        feature_key: Feature flag key to check
        disabled_message: Message to show when feature is disabled
        disabled_template: Template to render when feature is disabled (for web routes)
        disabled_json_response: JSON response when feature is disabled (for API routes)
        graceful_degradation: If True, return None instead of error response
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get feature flag service from current app
            feature_service = None
            try:
                feature_service = getattr(current_app, 'feature_flag_service', None)
            except RuntimeError:
                # Not in Flask context, try to get from args/kwargs
                pass
            
            # Try to get from function arguments if not in Flask context
            if not feature_service:
                for arg in args:
                    if isinstance(arg, FeatureFlagService):
                        feature_service = arg
                        break
                
                if not feature_service:
                    for value in kwargs.values():
                        if isinstance(value, FeatureFlagService):
                            feature_service = value
                            break
            
            if not feature_service:
                logger.error("FeatureFlagService not available")
                if graceful_degradation:
                    return None
                return _create_error_response("Feature flag service unavailable", 500)
            
            # Check if feature is enabled
            if not feature_service.is_enabled(feature_key):
                logger.info(f"Feature {feature_key} is disabled, blocking access to {func.__name__}")
                
                if graceful_degradation:
                    return None
                
                # Determine response type based on request
                if disabled_json_response and _is_json_request():
                    return jsonify(disabled_json_response), 503
                elif disabled_template and _is_web_request():
                    return render_template(disabled_template, 
                                         feature=feature_key,
                                         message=disabled_message or f"Feature '{feature_key}' is currently disabled")
                else:
                    message = disabled_message or f"Feature '{feature_key}' is currently disabled"
                    return _create_error_response(message, 503)
            
            # Feature is enabled, proceed with function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_feature_flag_async(feature_key: str,
                              disabled_message: str = None,
                              graceful_degradation: bool = False):
    """
    Async decorator to require a feature flag to be enabled
    
    Args:
        feature_key: Feature flag key to check
        disabled_message: Message to log when feature is disabled
        graceful_degradation: If True, return None instead of raising exception
    
    Returns:
        Async decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # For async functions, we need to get the feature service differently
            # This assumes the service is passed as a parameter or available globally
            feature_service = None
            
            # Try to get from current_app if available
            try:
                from flask import current_app
                feature_service = getattr(current_app, 'feature_flag_service', None)
            except RuntimeError:
                # Not in Flask context, try to get from args/kwargs
                pass
            
            # Try to get from function arguments
            if not feature_service:
                for arg in args:
                    if isinstance(arg, FeatureFlagService):
                        feature_service = arg
                        break
                
                if not feature_service:
                    for value in kwargs.values():
                        if isinstance(value, FeatureFlagService):
                            feature_service = value
                            break
            
            if not feature_service:
                logger.error("FeatureFlagService not available for async function")
                if graceful_degradation:
                    return None
                raise RuntimeError("Feature flag service unavailable")
            
            # Check if feature is enabled
            if not feature_service.is_enabled(feature_key):
                message = disabled_message or f"Feature '{feature_key}' is currently disabled"
                logger.info(f"Feature {feature_key} is disabled, blocking async function {func.__name__}")
                
                if graceful_degradation:
                    return None
                
                raise RuntimeError(message)
            
            # Feature is enabled, proceed with function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def batch_processing_required(disabled_message: str = "Batch processing is currently disabled"):
    """
    Decorator specifically for batch processing endpoints
    
    Args:
        disabled_message: Message when batch processing is disabled
    
    Returns:
        Decorator function
    """
    return require_feature_flag(
        'enable_batch_processing',
        disabled_message=disabled_message,
        disabled_template='errors/feature_disabled.html',
        disabled_json_response={
            'error': 'batch_processing_disabled',
            'message': disabled_message,
            'feature': 'enable_batch_processing'
        }
    )


def advanced_monitoring_required(graceful_degradation: bool = True):
    """
    Decorator for advanced monitoring features
    
    Args:
        graceful_degradation: If True, return None when disabled instead of error
    
    Returns:
        Decorator function
    """
    return require_feature_flag(
        'enable_advanced_monitoring',
        disabled_message="Advanced monitoring is currently disabled",
        graceful_degradation=graceful_degradation
    )


def auto_retry_required(graceful_degradation: bool = True):
    """
    Decorator for auto-retry functionality
    
    Args:
        graceful_degradation: If True, return None when disabled instead of error
    
    Returns:
        Decorator function
    """
    return require_feature_flag_async(
        'enable_auto_retry',
        disabled_message="Auto-retry is currently disabled",
        graceful_degradation=graceful_degradation
    )


class FeatureFlagMiddleware:
    """
    Middleware for feature flag enforcement in services and background tasks
    """
    
    def __init__(self, feature_service: FeatureFlagService):
        """
        Initialize middleware
        
        Args:
            feature_service: FeatureFlagService instance
        """
        self.feature_service = feature_service
    
    def check_feature_enabled(self, feature_key: str, operation_name: str = None) -> bool:
        """
        Check if a feature is enabled and log appropriately
        
        Args:
            feature_key: Feature flag key to check
            operation_name: Optional operation name for logging
        
        Returns:
            True if feature is enabled, False otherwise
        """
        enabled = self.feature_service.is_enabled(feature_key)
        
        if not enabled:
            op_name = operation_name or "operation"
            logger.info(f"Feature {feature_key} is disabled, skipping {op_name}")
        
        return enabled
    
    def enforce_batch_processing(self, operation_name: str = "batch operation") -> bool:
        """
        Enforce batch processing feature flag
        
        Args:
            operation_name: Name of the operation for logging
        
        Returns:
            True if batch processing is enabled
        """
        return self.check_feature_enabled('enable_batch_processing', operation_name)
    
    def enforce_advanced_monitoring(self, operation_name: str = "monitoring operation") -> bool:
        """
        Enforce advanced monitoring feature flag
        
        Args:
            operation_name: Name of the operation for logging
        
        Returns:
            True if advanced monitoring is enabled
        """
        return self.check_feature_enabled('enable_advanced_monitoring', operation_name)
    
    def enforce_auto_retry(self, operation_name: str = "retry operation") -> bool:
        """
        Enforce auto-retry feature flag
        
        Args:
            operation_name: Name of the operation for logging
        
        Returns:
            True if auto-retry is enabled
        """
        return self.check_feature_enabled('enable_auto_retry', operation_name)
    
    def graceful_feature_disable(self, feature_key: str, 
                                current_operations: list = None,
                                completion_callback: Callable = None) -> bool:
        """
        Handle graceful feature disabling
        
        Args:
            feature_key: Feature flag key
            current_operations: List of current operations to complete
            completion_callback: Callback to execute when operations complete
        
        Returns:
            True if feature should be disabled gracefully
        """
        if not self.feature_service.is_enabled(feature_key):
            logger.info(f"Feature {feature_key} disabled, initiating graceful shutdown")
            
            if current_operations:
                logger.info(f"Allowing {len(current_operations)} current operations to complete")
                # In a real implementation, you might wait for operations to complete
                # or set flags to prevent new operations
            
            if completion_callback:
                try:
                    completion_callback()
                except Exception as e:
                    logger.error(f"Error in completion callback for {feature_key}: {e}")
            
            return True
        
        return False


def _is_json_request() -> bool:
    """Check if the current request expects JSON response"""
    try:
        return (request.is_json or 
                'application/json' in request.headers.get('Accept', '') or
                request.path.startswith('/api/'))
    except RuntimeError:
        # Not in request context
        return False


def _is_web_request() -> bool:
    """Check if the current request is a web request (not API)"""
    try:
        return (not _is_json_request() and
                'text/html' in request.headers.get('Accept', ''))
    except RuntimeError:
        # Not in request context
        return True  # Default to web request


def _create_error_response(message: str, status_code: int = 503):
    """Create appropriate error response based on request type"""
    try:
        if _is_json_request():
            return jsonify({'error': 'feature_disabled', 'message': message}), status_code
        else:
            # For web requests, you might want to render a template
            return render_template('errors/feature_disabled.html', 
                                 message=message), status_code
    except Exception:
        # Fallback to simple response
        return message, status_code