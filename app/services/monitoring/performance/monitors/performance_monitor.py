# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance Monitoring Utilities

This module provides utilities for monitoring page load performance,
database query counts, and other performance metrics.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from functools import wraps
from flask import request, g, current_app
from flask_login import current_user
from datetime import datetime, timezone
from cachetools import TTLCache
import threading

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Container for performance metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.end_time = None
        self.database_queries = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.template_render_time = 0
        self.route_name = None
        self.user_type = 'anonymous'
        self.response_size = 0
        self.status_code = None
    
    def finish(self, status_code: int = 200, response_size: int = 0):
        """Mark the request as finished and calculate final metrics."""
        self.end_time = time.time()
        self.status_code = status_code
        self.response_size = response_size
    
    @property
    def total_time(self) -> float:
        """Get total request time in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def total_time_ms(self) -> float:
        """Get total request time in milliseconds."""
        return self.total_time * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'total_time_ms': round(self.total_time_ms, 2),
            'database_queries': self.database_queries,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'template_render_time_ms': round(self.template_render_time * 1000, 2),
            'route_name': self.route_name,
            'user_type': self.user_type,
            'response_size_bytes': self.response_size,
            'status_code': self.status_code,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

class PerformanceMonitor:
    """
    Performance monitoring manager.
    
    Tracks performance metrics for requests, database queries,
    and caching operations.
    """
    
    def __init__(self, max_metrics: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize performance monitor.
        
        Args:
            max_metrics: Maximum number of metrics to store
            ttl_seconds: Time to live for metrics in seconds
        """
        self.metrics_cache = TTLCache(maxsize=max_metrics, ttl=ttl_seconds)
        self.aggregated_stats = {
            'total_requests': 0,
            'anonymous_requests': 0,
            'authenticated_requests': 0,
            'landing_page_requests': 0,
            'dashboard_requests': 0,
            'avg_response_time_ms': 0,
            'database_queries_saved': 0,
            'cache_hit_rate': 0
        }
        self._lock = threading.Lock()
    
    def start_request_monitoring(self) -> PerformanceMetrics:
        """
        Start monitoring a request.
        
        Returns:
            PerformanceMetrics instance
        """
        metrics = PerformanceMetrics()
        
        # Set route information
        if request:
            metrics.route_name = request.endpoint
            
            # Determine user type
            if current_user and current_user.is_authenticated:
                metrics.user_type = 'authenticated'
            else:
                metrics.user_type = 'anonymous'
        
        # Store in Flask g for request-scoped access
        g.performance_metrics = metrics
        
        return metrics
    
    def finish_request_monitoring(self, status_code: int = 200, response_size: int = 0):
        """
        Finish monitoring a request and store metrics.
        
        Args:
            status_code: HTTP status code
            response_size: Response size in bytes
        """
        if not hasattr(g, 'performance_metrics'):
            return
        
        metrics = g.performance_metrics
        metrics.finish(status_code, response_size)
        
        # Store metrics
        self._store_metrics(metrics)
        
        # Update aggregated stats
        self._update_aggregated_stats(metrics)
        
        # Log performance if slow
        if metrics.total_time_ms > 1000:  # Log requests over 1 second
            logger.warning(f"Slow request: {metrics.route_name} took {metrics.total_time_ms:.2f}ms")
    
    def record_database_query(self):
        """Record a database query."""
        if hasattr(g, 'performance_metrics'):
            g.performance_metrics.database_queries += 1
    
    def record_cache_hit(self):
        """Record a cache hit."""
        if hasattr(g, 'performance_metrics'):
            g.performance_metrics.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss."""
        if hasattr(g, 'performance_metrics'):
            g.performance_metrics.cache_misses += 1
    
    def record_template_render_time(self, render_time: float):
        """
        Record template rendering time.
        
        Args:
            render_time: Template rendering time in seconds
        """
        if hasattr(g, 'performance_metrics'):
            g.performance_metrics.template_render_time += render_time
    
    def _store_metrics(self, metrics: PerformanceMetrics):
        """Store metrics in cache."""
        try:
            with self._lock:
                key = f"metrics:{int(time.time())}:{id(metrics)}"
                self.metrics_cache[key] = metrics.to_dict()
        except Exception as e:
            logger.error(f"Error storing performance metrics: {e}")
    
    def _update_aggregated_stats(self, metrics: PerformanceMetrics):
        """Update aggregated statistics."""
        try:
            with self._lock:
                self.aggregated_stats['total_requests'] += 1
                
                if metrics.user_type == 'anonymous':
                    self.aggregated_stats['anonymous_requests'] += 1
                    
                    # Track zero database queries for anonymous users
                    if metrics.database_queries == 0:
                        self.aggregated_stats['database_queries_saved'] += 1
                else:
                    self.aggregated_stats['authenticated_requests'] += 1
                
                # Track specific routes
                if metrics.route_name == 'main.index':
                    if metrics.user_type == 'anonymous':
                        self.aggregated_stats['landing_page_requests'] += 1
                    else:
                        self.aggregated_stats['dashboard_requests'] += 1
                
                # Update average response time
                total_requests = self.aggregated_stats['total_requests']
                current_avg = self.aggregated_stats['avg_response_time_ms']
                new_avg = ((current_avg * (total_requests - 1)) + metrics.total_time_ms) / total_requests
                self.aggregated_stats['avg_response_time_ms'] = round(new_avg, 2)
                
                # Update cache hit rate
                total_cache_ops = metrics.cache_hits + metrics.cache_misses
                if total_cache_ops > 0:
                    hit_rate = (metrics.cache_hits / total_cache_ops) * 100
                    current_hit_rate = self.aggregated_stats['cache_hit_rate']
                    # Simple moving average
                    self.aggregated_stats['cache_hit_rate'] = round((current_hit_rate + hit_rate) / 2, 2)
                
        except Exception as e:
            logger.error(f"Error updating aggregated stats: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary.
        
        Returns:
            Dictionary with performance summary
        """
        try:
            with self._lock:
                summary = self.aggregated_stats.copy()
                
                # Add additional calculated metrics
                total_requests = summary['total_requests']
                if total_requests > 0:
                    summary['anonymous_percentage'] = round(
                        (summary['anonymous_requests'] / total_requests) * 100, 2
                    )
                    summary['landing_page_percentage'] = round(
                        (summary['landing_page_requests'] / total_requests) * 100, 2
                    )
                    summary['zero_db_query_percentage'] = round(
                        (summary['database_queries_saved'] / summary['anonymous_requests']) * 100, 2
                    ) if summary['anonymous_requests'] > 0 else 0
                else:
                    summary['anonymous_percentage'] = 0
                    summary['landing_page_percentage'] = 0
                    summary['zero_db_query_percentage'] = 0
                
                summary['metrics_cache_size'] = len(self.metrics_cache)
                summary['timestamp'] = datetime.now(timezone.utc).isoformat()
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {'error': str(e)}
    
    def get_recent_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent performance metrics.
        
        Args:
            limit: Maximum number of metrics to return
        
        Returns:
            List of recent metrics
        """
        try:
            with self._lock:
                metrics = list(self.metrics_cache.values())
                # Sort by timestamp (most recent first)
                metrics.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                return metrics[:limit]
        except Exception as e:
            logger.error(f"Error getting recent metrics: {e}")
            return []

# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """
    Get the global performance monitor instance.
    
    Returns:
        PerformanceMonitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        logger.info("Initialized performance monitor")
    
    return _performance_monitor

def monitor_performance(func):
    """
    Decorator to monitor route performance.
    
    Args:
        func: Route function to monitor
    
    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        monitor = get_performance_monitor()
        
        # Start monitoring
        metrics = monitor.start_request_monitoring()
        
        try:
            # Execute the route function
            result = func(*args, **kwargs)
            
            # Finish monitoring with success
            monitor.finish_request_monitoring(200, len(str(result)) if isinstance(result, str) else 0)
            
            return result
            
        except Exception as e:
            # Finish monitoring with error
            monitor.finish_request_monitoring(500, 0)
            raise
    
    return wrapper

def record_database_query():
    """Record a database query for performance tracking."""
    monitor = get_performance_monitor()
    monitor.record_database_query()

def record_cache_operation(hit: bool):
    """
    Record a cache operation.
    
    Args:
        hit: True for cache hit, False for cache miss
    """
    monitor = get_performance_monitor()
    if hit:
        monitor.record_cache_hit()
    else:
        monitor.record_cache_miss()

def get_performance_summary() -> Dict[str, Any]:
    """
    Get performance summary.
    
    Returns:
        Dictionary with performance summary
    """
    monitor = get_performance_monitor()
    return monitor.get_performance_summary()