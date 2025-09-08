#!/usr/bin/env python3
"""
MySQL Performance Optimization System for Vedfolnir

This module provides comprehensive MySQL performance optimization including
connection pooling optimization, query performance monitoring, caching strategies,
and performance metrics collection. This replaces any SQLite-based performance
optimization and provides MySQL-specific performance enhancements.
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager
from collections import defaultdict, deque
import json

import pymysql
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from config import Config
from database import get_db_connection

logger = logging.getLogger(__name__)

@dataclass
class QueryPerformanceMetrics:
    """Query performance metrics."""
    query_hash: str
    query_template: str
    execution_count: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    last_executed: datetime
    slow_query_count: int = 0
    error_count: int = 0

@dataclass
class ConnectionPoolMetrics:
    """Connection pool performance metrics."""
    pool_size: int
    checked_out: int
    overflow: int
    invalid: int
    total_connections_created: int
    total_connections_closed: int
    connection_errors: int
    avg_checkout_time_ms: float
    max_checkout_time_ms: float
    pool_utilization_percent: float

@dataclass
class MySQLPerformanceSnapshot:
    """Snapshot of MySQL performance metrics."""
    timestamp: datetime
    connection_pool: ConnectionPoolMetrics
    query_metrics: List[QueryPerformanceMetrics]
    mysql_status: Dict[str, Any]
    performance_recommendations: List[str]

class MySQLConnectionPoolOptimizer:
    """
    MySQL connection pool optimizer with advanced configuration.
    
    This class provides optimal connection pool configuration for different
    deployment scenarios and workload patterns.
    """
    
    def __init__(self, config: Config):
        """Initialize the connection pool optimizer."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Connection pool configurations for different scenarios
        self.pool_configurations = {
            'development': {
                'pool_size': 5,
                'max_overflow': 10,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'pool_pre_ping': True,
                'pool_reset_on_return': 'commit'
            },
            'testing': {
                'pool_size': 2,
                'max_overflow': 5,
                'pool_timeout': 10,
                'pool_recycle': 300,
                'pool_pre_ping': True,
                'pool_reset_on_return': 'rollback'
            },
            'production': {
                'pool_size': 20,
                'max_overflow': 50,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'pool_pre_ping': True,
                'pool_reset_on_return': 'commit'
            },
            'high_load': {
                'pool_size': 50,
                'max_overflow': 100,
                'pool_timeout': 60,
                'pool_recycle': 7200,
                'pool_pre_ping': True,
                'pool_reset_on_return': 'commit'
            }
        }
    
    def get_optimal_pool_config(self, environment: str = 'production') -> Dict[str, Any]:
        """
        Get optimal connection pool configuration for the environment.
        
        Args:
            environment: Target environment (development, testing, production, high_load)
            
        Returns:
            Dictionary with optimal pool configuration
        """
        base_config = self.pool_configurations.get(environment, self.pool_configurations['production'])
        
        # Add MySQL-specific connection arguments
        mysql_connect_args = {
            'charset': 'utf8mb4',
            'connect_timeout': 60,
            'read_timeout': 30,
            'write_timeout': 30,
            'autocommit': False,
            'use_unicode': True,
            'sql_mode': 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION'
        }
        
        # Add SSL configuration if enabled
        if getattr(self.config, 'mysql_ssl_enabled', False):
            mysql_connect_args.update({
                'ssl_disabled': False,
                'ssl_verify_cert': getattr(self.config, 'mysql_ssl_verify_cert', True),
                'ssl_verify_identity': getattr(self.config, 'mysql_ssl_verify_identity', True)
            })
            
            # Add SSL certificate paths if configured
            ssl_ca = getattr(self.config, 'mysql_ssl_ca', None)
            ssl_cert = getattr(self.config, 'mysql_ssl_cert', None)
            ssl_key = getattr(self.config, 'mysql_ssl_key', None)
            
            if ssl_ca:
                mysql_connect_args['ssl_ca'] = ssl_ca
            if ssl_cert:
                mysql_connect_args['ssl_cert'] = ssl_cert
            if ssl_key:
                mysql_connect_args['ssl_key'] = ssl_key
        
        # Combine configuration
        optimal_config = {
            **base_config,
            'connect_args': mysql_connect_args,
            'poolclass': QueuePool,
            'echo': getattr(self.config, 'mysql_log_queries', False),
            'echo_pool': getattr(self.config, 'mysql_log_pool_events', False)
        }
        
        self.logger.info(f"Generated optimal pool config for {environment} environment")
        return optimal_config
    
    def create_optimized_engine(self, environment: str = 'production') -> Engine:
        """
        Create an optimized SQLAlchemy engine with MySQL-specific optimizations.
        
        Args:
            environment: Target environment
            
        Returns:
            Optimized SQLAlchemy Engine instance
        """
        pool_config = self.get_optimal_pool_config(environment)
        database_url = self.config.database.database_url
        
        # Create engine with optimized configuration
        engine = create_engine(database_url, **pool_config)
        
        # Add performance monitoring event listeners
        self._add_performance_listeners(engine)
        
        self.logger.info(f"Created optimized MySQL engine for {environment}")
        return engine
    
    def _add_performance_listeners(self, engine: Engine):
        """Add performance monitoring event listeners to the engine."""
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time."""
            context._query_start_time = time.time()
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query execution time and log slow queries."""
            if hasattr(context, '_query_start_time'):
                execution_time = time.time() - context._query_start_time
                
                # Log slow queries (configurable threshold)
                slow_query_threshold = getattr(self.config, 'mysql_slow_query_threshold', 2.0)
                if execution_time > slow_query_threshold:
                    self.logger.warning(
                        f"Slow query detected: {execution_time:.3f}s - {statement[:100]}..."
                    )
                
                # Store metrics for monitoring (if performance monitoring is enabled)
                if hasattr(self, 'performance_monitor'):
                    self.performance_monitor.record_query_execution(
                        statement, execution_time, parameters
                    )

class MySQLQueryOptimizer:
    """
    MySQL query optimization and monitoring system.
    
    This class provides query performance analysis, optimization recommendations,
    and index usage monitoring specifically for MySQL.
    """
    
    def __init__(self, config: Config):
        """Initialize the query optimizer."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.query_metrics = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'errors': 0
        })
        self.slow_queries = deque(maxlen=100)  # Keep last 100 slow queries
        
    def analyze_query_performance(self) -> Dict[str, Any]:
        """
        Analyze MySQL query performance using Performance Schema.
        
        Returns:
            Dictionary with query performance analysis
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get top slow queries from Performance Schema
                cursor.execute("""
                    SELECT 
                        DIGEST_TEXT as query_template,
                        COUNT_STAR as execution_count,
                        SUM_TIMER_WAIT/1000000000 as total_time_seconds,
                        AVG_TIMER_WAIT/1000000000 as avg_time_seconds,
                        MIN_TIMER_WAIT/1000000000 as min_time_seconds,
                        MAX_TIMER_WAIT/1000000000 as max_time_seconds
                    FROM performance_schema.events_statements_summary_by_digest 
                    WHERE SCHEMA_NAME = %s
                    ORDER BY SUM_TIMER_WAIT DESC 
                    LIMIT 20
                """, (self.config.database.database_name,))
                
                slow_queries = []
                for row in cursor.fetchall():
                    slow_queries.append({
                        'query_template': row[0][:200] if row[0] else 'Unknown',
                        'execution_count': row[1],
                        'total_time_seconds': float(row[2]) if row[2] else 0,
                        'avg_time_seconds': float(row[3]) if row[3] else 0,
                        'min_time_seconds': float(row[4]) if row[4] else 0,
                        'max_time_seconds': float(row[5]) if row[5] else 0
                    })
                
                # Get index usage statistics
                cursor.execute("""
                    SELECT 
                        object_schema,
                        object_name,
                        index_name,
                        count_star as usage_count,
                        sum_timer_wait/1000000000 as total_time_seconds
                    FROM performance_schema.table_io_waits_summary_by_index_usage 
                    WHERE object_schema = %s
                    AND count_star > 0
                    ORDER BY count_star DESC
                    LIMIT 20
                """, (self.config.database.database_name,))
                
                index_usage = []
                for row in cursor.fetchall():
                    index_usage.append({
                        'table': row[1],
                        'index': row[2],
                        'usage_count': row[3],
                        'total_time_seconds': float(row[4]) if row[4] else 0
                    })
                
                # Get unused indexes
                cursor.execute("""
                    SELECT 
                        table_schema,
                        table_name,
                        index_name,
                        cardinality
                    FROM information_schema.statistics 
                    WHERE table_schema = %s
                    AND index_name NOT IN (
                        SELECT DISTINCT index_name 
                        FROM performance_schema.table_io_waits_summary_by_index_usage 
                        WHERE object_schema = %s AND count_star > 0
                    )
                    AND index_name != 'PRIMARY'
                """, (self.config.database.database_name, self.config.database.database_name))
                
                unused_indexes = []
                for row in cursor.fetchall():
                    unused_indexes.append({
                        'table': row[1],
                        'index': row[2],
                        'cardinality': row[3]
                    })
                
                cursor.close()
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'slow_queries': slow_queries,
                    'index_usage': index_usage,
                    'unused_indexes': unused_indexes,
                    'analysis_summary': {
                        'total_slow_queries': len(slow_queries),
                        'total_indexes_used': len(index_usage),
                        'total_unused_indexes': len(unused_indexes)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Query performance analysis failed: {e}")
            return {'error': str(e)}
    
    def get_optimization_recommendations(self) -> List[str]:
        """
        Generate MySQL query optimization recommendations.
        
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        try:
            performance_analysis = self.analyze_query_performance()
            
            if 'error' in performance_analysis:
                return ['Fix database connection issues before optimization']
            
            # Analyze slow queries
            slow_queries = performance_analysis.get('slow_queries', [])
            if slow_queries:
                recommendations.append(f"Found {len(slow_queries)} slow query patterns")
                
                # Check for common issues
                for query in slow_queries[:5]:  # Top 5 slowest
                    if query['avg_time_seconds'] > 5:
                        recommendations.append(
                            f"Critical: Query taking {query['avg_time_seconds']:.2f}s on average - "
                            f"consider optimization or indexing"
                        )
            
            # Analyze unused indexes
            unused_indexes = performance_analysis.get('unused_indexes', [])
            if unused_indexes:
                recommendations.append(f"Found {len(unused_indexes)} unused indexes")
                if len(unused_indexes) > 5:
                    recommendations.append("Consider removing unused indexes to improve write performance")
            
            # Check index usage patterns
            index_usage = performance_analysis.get('index_usage', [])
            if index_usage:
                # Look for heavily used indexes that might need optimization
                for idx in index_usage[:3]:
                    if idx['usage_count'] > 10000:
                        recommendations.append(
                            f"High usage index: {idx['table']}.{idx['index']} - "
                            f"monitor for optimization opportunities"
                        )
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate optimization recommendations: {e}")
            return ['Error generating recommendations - check logs']
    
    @contextmanager
    def _get_connection(self):
        """Get a MySQL connection with proper cleanup."""
        conn = None
        try:
            conn = get_db_connection()
            yield conn
        finally:
            if conn:
                conn.close()

class MySQLCachingStrategy:
    """
    MySQL-specific caching strategies and implementation.
    
    This class provides intelligent caching for MySQL queries and results
    to improve application performance.
    """
    
    def __init__(self, config: Config):
        """Initialize the caching strategy."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Cache configuration
        self.cache_config = {
            'query_cache_enabled': getattr(config, 'mysql_query_cache_enabled', True),
            'query_cache_size': getattr(config, 'mysql_query_cache_size', 1000),
            'query_cache_ttl': getattr(config, 'mysql_query_cache_ttl', 300),
            'result_cache_enabled': getattr(config, 'mysql_result_cache_enabled', True),
            'result_cache_size': getattr(config, 'mysql_result_cache_size', 500),
            'result_cache_ttl': getattr(config, 'mysql_result_cache_ttl', 600)
        }
        
        # In-memory caches
        self.query_cache = {}
        self.result_cache = {}
        self.cache_stats = {
            'query_cache_hits': 0,
            'query_cache_misses': 0,
            'result_cache_hits': 0,
            'result_cache_misses': 0
        }
        
        # Cache cleanup thread
        self._start_cache_cleanup_thread()
    
    def cache_query_result(self, query: str, params: tuple, result: Any, ttl: Optional[int] = None):
        """
        Cache a query result.
        
        Args:
            query: SQL query string
            params: Query parameters
            result: Query result to cache
            ttl: Time to live in seconds
        """
        if not self.cache_config['result_cache_enabled']:
            return
        
        cache_key = self._generate_cache_key(query, params)
        ttl = ttl or self.cache_config['result_cache_ttl']
        expiry_time = datetime.now() + timedelta(seconds=ttl)
        
        # Store in cache with expiry
        self.result_cache[cache_key] = {
            'result': result,
            'expiry': expiry_time,
            'created': datetime.now()
        }
        
        # Maintain cache size limit
        if len(self.result_cache) > self.cache_config['result_cache_size']:
            self._evict_oldest_cache_entries()
    
    def get_cached_result(self, query: str, params: tuple) -> Optional[Any]:
        """
        Get cached query result if available and not expired.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Cached result or None if not found/expired
        """
        if not self.cache_config['result_cache_enabled']:
            return None
        
        cache_key = self._generate_cache_key(query, params)
        cached_entry = self.result_cache.get(cache_key)
        
        if cached_entry:
            if datetime.now() < cached_entry['expiry']:
                self.cache_stats['result_cache_hits'] += 1
                return cached_entry['result']
            else:
                # Remove expired entry
                del self.result_cache[cache_key]
        
        self.cache_stats['result_cache_misses'] += 1
        return None
    
    def _generate_cache_key(self, query: str, params: tuple) -> str:
        """Generate a cache key for query and parameters."""
        import hashlib
        
        # Normalize query (remove extra whitespace)
        normalized_query = ' '.join(query.split())
        
        # Create hash of query and parameters
        cache_data = f"{normalized_query}:{str(params)}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _evict_oldest_cache_entries(self):
        """Evict oldest cache entries to maintain size limit."""
        if not self.result_cache:
            return
        
        # Sort by creation time and remove oldest 10%
        sorted_entries = sorted(
            self.result_cache.items(),
            key=lambda x: x[1]['created']
        )
        
        entries_to_remove = len(sorted_entries) // 10
        for i in range(entries_to_remove):
            del self.result_cache[sorted_entries[i][0]]
    
    def _start_cache_cleanup_thread(self):
        """Start background thread for cache cleanup."""
        def cleanup_expired_entries():
            while True:
                try:
                    current_time = datetime.now()
                    expired_keys = [
                        key for key, entry in self.result_cache.items()
                        if current_time >= entry['expiry']
                    ]
                    
                    for key in expired_keys:
                        del self.result_cache[key]
                    
                    if expired_keys:
                        self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
                    time.sleep(60)  # Cleanup every minute
                    
                except Exception as e:
                    self.logger.error(f"Cache cleanup error: {e}")
                    time.sleep(60)
        
        cleanup_thread = threading.Thread(target=cleanup_expired_entries, daemon=True)
        cleanup_thread.start()
        self.logger.info("Cache cleanup thread started")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = (
            self.cache_stats['result_cache_hits'] + 
            self.cache_stats['result_cache_misses']
        )
        
        hit_rate = (
            (self.cache_stats['result_cache_hits'] / total_requests * 100)
            if total_requests > 0 else 0
        )
        
        return {
            'cache_enabled': self.cache_config['result_cache_enabled'],
            'cache_size': len(self.result_cache),
            'max_cache_size': self.cache_config['result_cache_size'],
            'cache_utilization_percent': (len(self.result_cache) / self.cache_config['result_cache_size'] * 100),
            'hit_rate_percent': hit_rate,
            'total_hits': self.cache_stats['result_cache_hits'],
            'total_misses': self.cache_stats['result_cache_misses'],
            'total_requests': total_requests
        }
