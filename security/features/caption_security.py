# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security controls for caption generation functionality

Implements authorization, validation, and security checks specific to caption generation.
"""

import re
import uuid
import secrets
import logging
from functools import wraps
from typing import Optional, Dict, Any
from flask import request, jsonify, current_app, g
from flask_login import current_user
from datetime import datetime, timedelta

from database import DatabaseManager
from models import CaptionGenerationTask, PlatformConnection, User
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class CaptionSecurityManager:
    """Security manager for caption generation operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._rate_limits = {}  # In production, use Redis
    
    def generate_secure_task_id(self) -> str:
        """Generate cryptographically secure task ID"""
        return str(uuid.uuid4())
    
    def validate_task_id(self, task_id: str) -> bool:
        """Validate task ID format"""
        try:
            uuid.UUID(task_id)
            return True
        except ValueError:
            return False
    
    def check_user_platform_access(self, user_id: int, platform_connection_id: int) -> bool:
        """Check if user has access to platform connection"""
        session = self.db_manager.get_session()
        try:
            platform = session.query(PlatformConnection).filter_by(
                id=platform_connection_id,
                user_id=user_id,
                is_active=True
            ).first()
            return platform is not None
        finally:
            session.close()
    
    def check_task_ownership(self, task_id: str, user_id: int) -> bool:
        """Check if user owns the task"""
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(
                id=task_id,
                user_id=user_id
            ).first()
            return task is not None
        finally:
            session.close()
    
    def check_generation_rate_limit(self, user_id: int, limit: int = 5, window_minutes: int = 60) -> bool:
        """Check if user is within generation rate limits"""
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(minutes=window_minutes)
        
        # Clean old entries
        if user_id in self._rate_limits:
            self._rate_limits[user_id] = [
                timestamp for timestamp in self._rate_limits[user_id]
                if timestamp > cutoff_time
            ]
        else:
            self._rate_limits[user_id] = []
        
        # Check limit
        if len(self._rate_limits[user_id]) >= limit:
            return False
        
        # Add current request
        self._rate_limits[user_id].append(current_time)
        return True
    
    def validate_generation_settings(self, settings: Dict[str, Any]) -> tuple[bool, list]:
        """Validate caption generation settings"""
        errors = []
        
        # Max posts per run
        max_posts = settings.get('max_posts_per_run')
        if max_posts is not None:
            if not isinstance(max_posts, int) or max_posts < 1 or max_posts > 100:
                errors.append('Max posts per run must be between 1 and 100')
        
        # Processing delay
        delay = settings.get('processing_delay')
        if delay is not None:
            if not isinstance(delay, (int, float)) or delay < 0 or delay > 10:
                errors.append('Processing delay must be between 0 and 10 seconds')
        
        # Caption lengths
        max_length = settings.get('max_caption_length')
        if max_length is not None:
            if not isinstance(max_length, int) or max_length < 50 or max_length > 1000:
                errors.append('Max caption length must be between 50 and 1000 characters')
        
        min_length = settings.get('optimal_min_length')
        if min_length is not None:
            if not isinstance(min_length, int) or min_length < 20 or min_length > 200:
                errors.append('Optimal min length must be between 20 and 200 characters')
        
        opt_max_length = settings.get('optimal_max_length')
        if opt_max_length is not None:
            if not isinstance(opt_max_length, int) or opt_max_length < 100 or opt_max_length > 500:
                errors.append('Optimal max length must be between 100 and 500 characters')
        
        # Cross-field validation
        if min_length and opt_max_length and min_length >= opt_max_length:
            errors.append('Optimal min length must be less than optimal max length')
        
        if opt_max_length and max_length and opt_max_length > max_length:
            errors.append('Optimal max length cannot exceed maximum caption length')
        
        return len(errors) == 0, errors
    
    def sanitize_task_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize task input data"""
        sanitized = {}
        
        # Only allow specific fields
        allowed_fields = {
            'max_posts_per_run', 'max_caption_length', 'optimal_min_length',
            'optimal_max_length', 'reprocess_existing', 'processing_delay'
        }
        
        for key, value in data.items():
            if key in allowed_fields:
                # Sanitize based on field type
                if key in ['max_posts_per_run', 'max_caption_length', 'optimal_min_length', 'optimal_max_length']:
                    try:
                        sanitized[key] = int(value)
                    except (ValueError, TypeError):
                        continue
                elif key == 'processing_delay':
                    try:
                        sanitized[key] = float(value)
                    except (ValueError, TypeError):
                        continue
                elif key == 'reprocess_existing':
                    sanitized[key] = bool(value)
                else:
                    sanitized[key] = value
        
        return sanitized

# Security decorators for caption generation

def caption_generation_auth_required(f):
    """Decorator to require authentication and platform access for caption generation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Check if user has active platform
        from session_manager import get_current_platform_context
        context = get_current_platform_context()
        if not context or not context.get('platform_connection_id'):
            return jsonify({'success': False, 'error': 'No active platform connection'}), 403
        
        # Store platform context for use in the endpoint
        g.platform_connection_id = context['platform_connection_id']
        
        return f(*args, **kwargs)
    return decorated_function

def validate_task_access(f):
    """Decorator to validate task access for task-specific endpoints"""
    @wraps(f)
    def decorated_function(task_id, *args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Validate task ID format
        security_manager = CaptionSecurityManager(current_app.config.get('db_manager'))
        if not security_manager.validate_task_id(task_id):
            logger.warning(f"Invalid task ID format from user {sanitize_for_log(str(current_user.id))}: {sanitize_for_log(task_id)}")
            return jsonify({'success': False, 'error': 'Invalid task ID'}), 400
        
        # Check task ownership
        if not security_manager.check_task_ownership(task_id, current_user.id):
            logger.warning(f"User {sanitize_for_log(str(current_user.id))} attempted to access task {sanitize_for_log(task_id)} without permission")
            return jsonify({'success': False, 'error': 'Task not found or access denied'}), 404
        
        return f(task_id, *args, **kwargs)
    return decorated_function

def caption_generation_rate_limit(limit: int = 5, window_minutes: int = 60):
    """Decorator to rate limit caption generation requests"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            security_manager = CaptionSecurityManager(current_app.config.get('db_manager'))
            if not security_manager.check_generation_rate_limit(current_user.id, limit, window_minutes):
                logger.warning(f"Rate limit exceeded for caption generation by user {sanitize_for_log(str(current_user.id))}")
                return jsonify({
                    'success': False, 
                    'error': f'Rate limit exceeded. Maximum {limit} generation requests per {window_minutes} minutes.'
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_caption_settings_input(f):
    """Decorator to validate caption settings input"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            # Get data from form or JSON
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = request.form.to_dict()
            
            security_manager = CaptionSecurityManager(current_app.config.get('db_manager'))
            
            # Sanitize input
            sanitized_data = security_manager.sanitize_task_input(data)
            
            # Validate settings
            is_valid, errors = security_manager.validate_generation_settings(sanitized_data)
            if not is_valid:
                logger.warning(f"Invalid caption settings from user {sanitize_for_log(str(current_user.id))}: {errors}")
                return jsonify({'success': False, 'errors': errors}), 400
            
            # Store sanitized data for use in endpoint
            g.sanitized_settings = sanitized_data
        
        return f(*args, **kwargs)
    return decorated_function

def log_caption_security_event(event_type: str, details: Dict[str, Any] = None):
    """Log security events for caption generation"""
    event_data = {
        'event_type': event_type,
        'user_id': current_user.id if current_user.is_authenticated else None,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'timestamp': datetime.utcnow().isoformat(),
        'endpoint': request.endpoint,
        'method': request.method
    }
    
    if details:
        event_data.update(details)
    
    logger.info(f"Caption security event: {sanitize_for_log(str(event_data))}")