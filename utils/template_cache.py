# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Template Caching Utilities

This module provides caching utilities specifically for Flask templates,
with a focus on optimizing the landing page performance.
"""

import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from cachetools import TTLCache
from flask import render_template, request, current_app
from datetime import datetime, timezone
import hashlib
import json

logger = logging.getLogger(__name__)

class TemplateCacheManager:
    """
    Template cache manager for Flask templates.
    
    Provides caching functionality for rendered templates with support for
    cache invalidation, TTL, and conditional caching based on user state.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        Initialize template cache manager.
        
        Args:
            max_size: Maximum number of cached templates
            ttl_seconds: Time to live for cached templates in seconds
        """
        self.cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'created_at': datetime.now(timezone.utc)
        }
    
    def _generate_cache_key(self, template_name: str, **kwargs) -> str:
        """
        Generate a cache key for a template with its context.
        
        Args:
            template_name: Name of the template
            **kwargs: Template context variables
        
        Returns:
            String cache key
        """
        # Create a deterministic key based on template name and context
        context_str = json.dumps(kwargs, sort_keys=True, default=str)
        context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]
        
        # Include user agent and language for responsive/i18n caching
        user_agent_hash = ""
        if request:
            user_agent = request.headers.get('User-Agent', '')
            accept_language = request.headers.get('Accept-Language', '')
            combined = f"{user_agent}:{accept_language}"
            user_agent_hash = hashlib.md5(combined.encode()).hexdigest()[:6]
        
        return f"template:{template_name}:{context_hash}:{user_agent_hash}"
    
    def get_cached_template(self, template_name: str, **kwargs) -> Optional[str]:
        """
        Get cached rendered template.
        
        Args:
            template_name: Name of the template
            **kwargs: Template context variables
        
        Returns:
            Cached rendered template HTML or None if not cached
        """
        try:
            cache_key = self._generate_cache_key(template_name, **kwargs)
            cached_html = self.cache.get(cache_key)
            
            if cached_html is not None:
                self._cache_stats['hits'] += 1
                logger.debug(f"Template cache hit for {template_name}")
                return cached_html
            else:
                self._cache_stats['misses'] += 1
                logger.debug(f"Template cache miss for {template_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached template {template_name}: {e}")
            self._cache_stats['misses'] += 1
            return None
    
    def cache_template(self, template_name: str, rendered_html: str, **kwargs) -> None:
        """
        Cache a rendered template.
        
        Args:
            template_name: Name of the template
            rendered_html: Rendered HTML content
            **kwargs: Template context variables used for cache key
        """
        try:
            cache_key = self._generate_cache_key(template_name, **kwargs)
            self.cache[cache_key] = rendered_html
            logger.debug(f"Cached template {template_name} with key {cache_key[:20]}...")
            
        except Exception as e:
            logger.error(f"Error caching template {template_name}: {e}")
    
    def invalidate_template(self, template_name: str, **kwargs) -> bool:
        """
        Invalidate a specific cached template.
        
        Args:
            template_name: Name of the template
            **kwargs: Template context variables
        
        Returns:
            True if template was invalidated, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(template_name, **kwargs)
            if cache_key in self.cache:
                del self.cache[cache_key]
                self._cache_stats['invalidations'] += 1
                logger.debug(f"Invalidated cached template {template_name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error invalidating cached template {template_name}: {e}")
            return False
    
    def clear_cache(self) -> None:
        """Clear all cached templates."""
        try:
            cache_size = len(self.cache)
            self.cache.clear()
            self._cache_stats['invalidations'] += cache_size
            logger.info(f"Cleared {cache_size} cached templates")
            
        except Exception as e:
            logger.error(f"Error clearing template cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = (self._cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self._cache_stats['hits'],
            'misses': self._cache_stats['misses'],
            'invalidations': self._cache_stats['invalidations'],
            'hit_rate_percent': round(hit_rate, 2),
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds,
            'created_at': self._cache_stats['created_at'].isoformat()
        }

# Global template cache manager instance
_template_cache_manager = None

def get_template_cache_manager() -> TemplateCacheManager:
    """
    Get the global template cache manager instance.
    
    Returns:
        TemplateCacheManager instance
    """
    global _template_cache_manager
    if _template_cache_manager is None:
        # Configure cache based on app config if available
        max_size = 100
        ttl_seconds = 3600  # 1 hour default
        
        if current_app:
            config = current_app.config
            max_size = config.get('TEMPLATE_CACHE_MAX_SIZE', 100)
            ttl_seconds = config.get('TEMPLATE_CACHE_TTL_SECONDS', 3600)
        
        _template_cache_manager = TemplateCacheManager(max_size, ttl_seconds)
        logger.info(f"Initialized template cache manager (max_size={max_size}, ttl={ttl_seconds}s)")
    
    return _template_cache_manager

def cached_render_template(template_name: str, cache_timeout: Optional[int] = None, **kwargs) -> str:
    """
    Render template with caching support.
    
    This function provides a drop-in replacement for Flask's render_template
    with automatic caching capabilities.
    
    Args:
        template_name: Name of the template to render
        cache_timeout: Optional cache timeout override
        **kwargs: Template context variables
    
    Returns:
        Rendered HTML content
    """
    cache_manager = get_template_cache_manager()
    
    # Check if template should be cached (exclude user-specific content)
    should_cache = _should_cache_template(template_name, **kwargs)
    
    if should_cache:
        # Try to get from cache first
        cached_html = cache_manager.get_cached_template(template_name, **kwargs)
        if cached_html is not None:
            return cached_html
    
    # Render template
    try:
        rendered_html = render_template(template_name, **kwargs)
        
        # Cache the rendered template if appropriate
        if should_cache:
            cache_manager.cache_template(template_name, rendered_html, **kwargs)
        
        return rendered_html
        
    except Exception as e:
        logger.error(f"Error rendering template {template_name}: {e}")
        raise

def _should_cache_template(template_name: str, **kwargs) -> bool:
    """
    Determine if a template should be cached.
    
    Args:
        template_name: Name of the template
        **kwargs: Template context variables
    
    Returns:
        True if template should be cached, False otherwise
    """
    # Cache landing page and other static templates
    cacheable_templates = {
        'landing.html',
        '404.html',
        '500.html',
        'base.html'  # Base template can be cached with specific contexts
    }
    
    if template_name in cacheable_templates:
        # Don't cache if user-specific data is present
        user_specific_keys = {'current_user', 'user', 'profile_data', 'stats'}
        if any(key in kwargs for key in user_specific_keys):
            return False
        
        # Don't cache if CSRF token is present (user-specific)
        if 'csrf_token' in kwargs:
            return False
        
        return True
    
    return False

def cache_template(cache_timeout: Optional[int] = None):
    """
    Decorator for caching template rendering in Flask routes.
    
    Args:
        cache_timeout: Cache timeout in seconds
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the original function
            result = func(*args, **kwargs)
            
            # If result is a template response, it's already handled by cached_render_template
            return result
        
        return wrapper
    return decorator

def invalidate_template_cache(template_name: str, **kwargs) -> bool:
    """
    Invalidate cached template.
    
    Args:
        template_name: Name of the template to invalidate
        **kwargs: Template context variables
    
    Returns:
        True if template was invalidated, False otherwise
    """
    cache_manager = get_template_cache_manager()
    return cache_manager.invalidate_template(template_name, **kwargs)

def clear_template_cache() -> None:
    """Clear all cached templates."""
    cache_manager = get_template_cache_manager()
    cache_manager.clear_cache()

def get_template_cache_stats() -> Dict[str, Any]:
    """
    Get template cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    cache_manager = get_template_cache_manager()
    return cache_manager.get_cache_stats()