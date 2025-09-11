# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance Context Processor

This module provides template context processors for injecting performance
optimization data into Flask templates.
"""

import logging
from typing import Dict, Any
from flask import request, current_app
from flask_login import current_user
from utils.asset_optimizer import get_resource_hints, get_critical_css

logger = logging.getLogger(__name__)

def performance_context_processor() -> Dict[str, Any]:
    """
    Template context processor for performance optimization data.
    
    Injects performance-related data into all templates including:
    - Resource hints (preload, dns-prefetch, preconnect)
    - Critical CSS
    - Performance flags
    
    Returns:
        Dictionary with performance context data
    """
    try:
        # Determine page type based on current route
        page_type = _determine_page_type()
        
        # Get resource hints for the page type
        resource_hints = get_resource_hints(page_type)
        
        # Get critical CSS for above-the-fold content
        critical_css = get_critical_css(page_type)
        
        # Performance flags
        performance_flags = {
            'enable_template_caching': _should_enable_template_caching(),
            'enable_asset_optimization': True,
            'enable_critical_css': page_type == 'landing',
            'enable_resource_hints': True,
            'is_anonymous_user': not (current_user and current_user.is_authenticated)
        }
        
        return {
            'performance': {
                'page_type': page_type,
                'resource_hints': resource_hints,
                'critical_css': critical_css,
                'flags': performance_flags
            }
        }
        
    except Exception as e:
        logger.error(f"Error in performance context processor: {e}")
        # Return safe defaults
        return {
            'performance': {
                'page_type': 'default',
                'resource_hints': {'preload': [], 'dns_prefetch': [], 'preconnect': []},
                'critical_css': '',
                'flags': {
                    'enable_template_caching': False,
                    'enable_asset_optimization': False,
                    'enable_critical_css': False,
                    'enable_resource_hints': False,
                    'is_anonymous_user': True
                }
            }
        }

def _determine_page_type() -> str:
    """
    Determine the page type based on the current request.
    
    Returns:
        String indicating the page type
    """
    try:
        if not request or not request.endpoint:
            return 'default'
        
        endpoint = request.endpoint
        
        # Map endpoints to page types
        page_type_mapping = {
            'main.index': 'landing' if not (current_user and current_user.is_authenticated) else 'dashboard',
            'auth.user_management.login': 'auth',
            'user_management.register': 'auth',
            'admin.dashboard': 'admin',
            'main.profile': 'profile'
        }
        
        return page_type_mapping.get(endpoint, 'default')
        
    except Exception as e:
        logger.debug(f"Error determining page type: {e}")
        return 'default'

def _should_enable_template_caching() -> bool:
    """
    Determine if template caching should be enabled for the current request.
    
    Returns:
        True if template caching should be enabled, False otherwise
    """
    try:
        # Enable caching for anonymous users
        if not current_user or not current_user.is_authenticated:
            return True
        
        # Disable caching for authenticated users to ensure fresh data
        return False
        
    except Exception as e:
        logger.debug(f"Error determining template caching flag: {e}")
        return False

def register_performance_context_processor(app):
    """
    Register the performance context processor with a Flask app.
    
    Args:
        app: Flask application instance
    """
    try:
        app.context_processor(performance_context_processor)
        logger.info("Registered performance context processor")
    except Exception as e:
        logger.error(f"Error registering performance context processor: {e}")

def get_performance_metrics() -> Dict[str, Any]:
    """
    Get current performance metrics for monitoring.
    
    Returns:
        Dictionary with performance metrics
    """
    try:
        from utils.template_cache import get_template_cache_stats
        
        cache_stats = get_template_cache_stats()
        
        return {
            'template_cache': cache_stats,
            'page_type': _determine_page_type(),
            'caching_enabled': _should_enable_template_caching(),
            'anonymous_user': not (current_user and current_user.is_authenticated)
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {
            'error': str(e),
            'template_cache': {'hits': 0, 'misses': 0, 'hit_rate_percent': 0}
        }