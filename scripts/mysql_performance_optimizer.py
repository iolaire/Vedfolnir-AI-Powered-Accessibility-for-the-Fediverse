#!/usr/bin/env python3
"""
MySQL Performance Optimizer for Vedfolnir

This module provides comprehensive MySQL performance optimization capabilities including:
- Connection pool optimization
- Query performance monitoring and analysis
- Caching strategy implementation
- Performance metrics collection and analysis
- Automated performance tuning recommendations
- Real-time performance monitoring

Integrates with existing MySQL health monitoring and validation systems.
"""

import logging
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pymysql
    from sqlalchemy import create_engine, text, pool
    from sqlalchemy.engine import Engine
    from sqlalchemy.pool import QueuePool, StaticPool
    import redis
    from config import Config
    from mysql_connection_validator import MySQLConnectionValidator
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required packages are installed")
    sys.exit(1)

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Container for MySQL performance metrics."""
    timestamp: datetime
    connection_pool_size: int
    active_connections: int
    idle_connections: int
    connection_usage_percent: float
    avg_query_time_ms: float
    slow_queries_count: int
    slow_query_ratio_percent: float
    cache_hit_ratio_percent: float
    memory_usage_mb: float
    cpu_usage_percent: float
    disk_io_ops_per_sec: float
    network_io_bytes_per_sec: float
    innodb_buffer_pool_hit_ratio: float
    table_locks_waited: int
    thread_cache_hit_ratio: float

@dataclass
class QueryPerformanceData:
    """Container for individual query performance data."""
    query_hash: str
    query_template: str
    execution_count: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    last_execution: datetime
    slow_query_threshold_ms: float = 1000.0

@dataclass
class OptimizationRecommendation:
    """Container for performance optimization recommendations."""
    category: str  # 'connection_pool', 'query', 'cache', 'configuration'
    priority: str  # 'critical', 'high', 'medium', 'low'
    title: str
    description: str
    current_value: Any
    recommended_value: Any
    expected_improvement: str
    implementation_steps: List[str]
    risk_level: str  # 'low', 'medium', 'high'

class MySQLPerformanceOptimizer:
    """
    Comprehensive MySQL performance optimization system.
    
    Provides connection pool optimization, query monitoring, caching strategies,
    and automated performance tuning recommendations.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the MySQL Performance Optimizer.
        
        Args:
            config: Optional Config instance, will create default if not provided
        """
        self.config = config or Config()
        self.validator = MySQLConnectionValidator()
        
        # Performance monitoring state
        self.query_performance_data: Dict[str, QueryPerformanceData] = {}
        self.performance_history: deque = deque(maxlen=1000)  # Keep last 1000 metrics
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Connection pool optimization
        self.optimized_engines: Dict[str, Engine] = {}
        
        # Caching
        self.redis_client: Optional[redis.Redis] = None
        self._initialize_redis()
        
        # Query monitoring
        self.slow_query_threshold_ms = float(os.getenv('MYSQL_SLOW_QUERY_THRESHOLD_MS', '1000'))
        self.query_cache_size = int(os.getenv('MYSQL_QUERY_CACHE_SIZE', '100'))
        
        logger.info("MySQL Performance Optimizer initialized")
    
    def _initialize_redis(self):
        """Initialize Redis connection for caching if available."""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/1')  # Use DB 1 for performance cache
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established for performance caching")
        except Exception as e:
            logger.warning(f"Redis not available for performance caching: {e}")
            self.redis_client = None
    
    def optimize_connection_pool(self, database_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Optimize MySQL connection pool configuration based on current usage patterns.
        
        Args:
            database_url: Optional database URL, uses config default if not provided
            
        Returns:
            Dictionary containing optimization results and recommendations
        """
        try:
            db_url = database_url or self.config.DATABASE_URL
            
            # Analyze current connection usage
            current_metrics = self._collect_connection_metrics(db_url)
            
            # Determine optimal pool settings
            optimal_settings = self._calculate_optimal_pool_settings(current_metrics)
            
            # Create optimized engine
            optimized_engine = self._create_optimized_engine(db_url, optimal_settings)
            
            # Store optimized engine
            engine_key = self._get_engine_key(db_url)
            self.optimized_engines[engine_key] = optimized_engine
            
            result = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'current_metrics': asdict(current_metrics),
                'optimal_settings': optimal_settings,
                'improvements': self._calculate_pool_improvements(current_metrics, optimal_settings),
                'engine_key': engine_key
            }
            
            logger.info(f"Connection pool optimized: {optimal_settings}")
            return result
            
        except Exception as e:
            logger.error(f"Connection pool optimization failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _collect_connection_metrics(self, database_url: str) -> PerformanceMetrics:
        """Collect current connection and performance metrics."""
        try:
            # Create temporary engine for metrics collection
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as conn:
                # Get connection pool information
                pool_info = self._get_pool_information(conn)
                
                # Get performance schema data
                performance_data = self._get_performance_schema_data(conn)
                
                # Get InnoDB metrics
                innodb_metrics = self._get_innodb_metrics(conn)
                
                # Calculate derived metrics
                connection_usage = (pool_info['active_connections'] / max(pool_info['max_connections'], 1)) * 100
                slow_query_ratio = (performance_data['slow_queries'] / max(performance_data['total_queries'], 1)) * 100
                
                metrics = PerformanceMetrics(
                    timestamp=datetime.now(),
                    connection_pool_size=pool_info['max_connections'],
                    active_connections=pool_info['active_connections'],
                    idle_connections=pool_info['idle_connections'],
                    connection_usage_percent=connection_usage,
                    avg_query_time_ms=performance_data['avg_query_time_ms'],
                    slow_queries_count=performance_data['slow_queries'],
                    slow_query_ratio_percent=slow_query_ratio,
                    cache_hit_ratio_percent=performance_data['query_cache_hit_ratio'],
                    memory_usage_mb=innodb_metrics['buffer_pool_size_mb'],
                    cpu_usage_percent=0.0,  # Would need system-level monitoring
                    disk_io_ops_per_sec=innodb_metrics['disk_io_ops_per_sec'],
                    network_io_bytes_per_sec=0.0,  # Would need system-level monitoring
                    innodb_buffer_pool_hit_ratio=innodb_metrics['buffer_pool_hit_ratio'],
                    table_locks_waited=performance_data['table_locks_waited'],
                    thread_cache_hit_ratio=performance_data['thread_cache_hit_ratio']
                )
                
            engine.dispose()
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect connection metrics: {e}")
            # Return default metrics
            return PerformanceMetrics(
                timestamp=datetime.now(),
                connection_pool_size=10,
                active_connections=0,
                idle_connections=0,
                connection_usage_percent=0.0,
                avg_query_time_ms=0.0,
                slow_queries_count=0,
                slow_query_ratio_percent=0.0,
                cache_hit_ratio_percent=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                disk_io_ops_per_sec=0.0,
                network_io_bytes_per_sec=0.0,
                innodb_buffer_pool_hit_ratio=0.0,
                table_locks_waited=0,
                thread_cache_hit_ratio=0.0
            )
    
    def _get_pool_information(self, conn) -> Dict[str, int]:
        """Get connection pool information from MySQL."""
        try:
            # Get connection statistics
            result = conn.execute(text("SHOW STATUS LIKE 'Threads_%'")).fetchall()
            status_dict = {row[0]: int(row[1]) for row in result}
            
            # Get max connections
            max_conn_result = conn.execute(text("SHOW VARIABLES LIKE 'max_connections'")).fetchone()
            max_connections = int(max_conn_result[1]) if max_conn_result else 151
            
            return {
                'max_connections': max_connections,
                'active_connections': status_dict.get('Threads_running', 0),
                'idle_connections': status_dict.get('Threads_connected', 0) - status_dict.get('Threads_running', 0),
                'total_connections': status_dict.get('Threads_connected', 0)
            }
        except Exception as e:
            logger.warning(f"Could not get pool information: {e}")
            return {
                'max_connections': 151,
                'active_connections': 0,
                'idle_connections': 0,
                'total_connections': 0
            }
    
    def _get_performance_schema_data(self, conn) -> Dict[str, float]:
        """Get performance data from MySQL performance schema."""
        try:
            performance_data = {}
            
            # Get slow query information
            try:
                slow_query_result = conn.execute(text("SHOW STATUS LIKE 'Slow_queries'")).fetchone()
                performance_data['slow_queries'] = int(slow_query_result[1]) if slow_query_result else 0
            except:
                performance_data['slow_queries'] = 0
            
            # Get total queries
            try:
                queries_result = conn.execute(text("SHOW STATUS LIKE 'Questions'")).fetchone()
                performance_data['total_queries'] = int(queries_result[1]) if queries_result else 1
            except:
                performance_data['total_queries'] = 1
            
            # Calculate average query time (approximation)
            try:
                uptime_result = conn.execute(text("SHOW STATUS LIKE 'Uptime'")).fetchone()
                uptime = int(uptime_result[1]) if uptime_result else 1
                performance_data['avg_query_time_ms'] = (uptime * 1000) / max(performance_data['total_queries'], 1)
            except:
                performance_data['avg_query_time_ms'] = 0.0
            
            # Get query cache hit ratio
            try:
                cache_hits_result = conn.execute(text("SHOW STATUS LIKE 'Qcache_hits'")).fetchone()
                cache_inserts_result = conn.execute(text("SHOW STATUS LIKE 'Qcache_inserts'")).fetchone()
                
                cache_hits = int(cache_hits_result[1]) if cache_hits_result else 0
                cache_inserts = int(cache_inserts_result[1]) if cache_inserts_result else 0
                
                total_cache_ops = cache_hits + cache_inserts
                performance_data['query_cache_hit_ratio'] = (cache_hits / max(total_cache_ops, 1)) * 100
            except:
                performance_data['query_cache_hit_ratio'] = 0.0
            
            # Get table lock information
            try:
                locks_waited_result = conn.execute(text("SHOW STATUS LIKE 'Table_locks_waited'")).fetchone()
                performance_data['table_locks_waited'] = int(locks_waited_result[1]) if locks_waited_result else 0
            except:
                performance_data['table_locks_waited'] = 0
            
            # Get thread cache hit ratio
            try:
                thread_cache_misses_result = conn.execute(text("SHOW STATUS LIKE 'Thread_cache_misses'")).fetchone()
                connections_result = conn.execute(text("SHOW STATUS LIKE 'Connections'")).fetchone()
                
                cache_misses = int(thread_cache_misses_result[1]) if thread_cache_misses_result else 0
                total_connections = int(connections_result[1]) if connections_result else 1
                
                performance_data['thread_cache_hit_ratio'] = ((total_connections - cache_misses) / max(total_connections, 1)) * 100
            except:
                performance_data['thread_cache_hit_ratio'] = 0.0
            
            return performance_data
            
        except Exception as e:
            logger.warning(f"Could not get performance schema data: {e}")
            return {
                'slow_queries': 0,
                'total_queries': 1,
                'avg_query_time_ms': 0.0,
                'query_cache_hit_ratio': 0.0,
                'table_locks_waited': 0,
                'thread_cache_hit_ratio': 0.0
            }
    
    def _get_innodb_metrics(self, conn) -> Dict[str, float]:
        """Get InnoDB-specific performance metrics."""
        try:
            innodb_data = {}
            
            # Get InnoDB buffer pool information
            try:
                buffer_pool_size_result = conn.execute(text("SHOW STATUS LIKE 'Innodb_buffer_pool_pages_total'")).fetchone()
                buffer_pool_free_result = conn.execute(text("SHOW STATUS LIKE 'Innodb_buffer_pool_pages_free'")).fetchone()
                
                total_pages = int(buffer_pool_size_result[1]) if buffer_pool_size_result else 0
                free_pages = int(buffer_pool_free_result[1]) if buffer_pool_free_result else 0
                
                # Assume 16KB page size
                innodb_data['buffer_pool_size_mb'] = (total_pages * 16) / 1024
                innodb_data['buffer_pool_used_mb'] = ((total_pages - free_pages) * 16) / 1024
            except:
                innodb_data['buffer_pool_size_mb'] = 0.0
                innodb_data['buffer_pool_used_mb'] = 0.0
            
            # Get buffer pool hit ratio
            try:
                buffer_pool_reads_result = conn.execute(text("SHOW STATUS LIKE 'Innodb_buffer_pool_reads'")).fetchone()
                buffer_pool_read_requests_result = conn.execute(text("SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests'")).fetchone()
                
                reads = int(buffer_pool_reads_result[1]) if buffer_pool_reads_result else 0
                read_requests = int(buffer_pool_read_requests_result[1]) if buffer_pool_read_requests_result else 1
                
                innodb_data['buffer_pool_hit_ratio'] = ((read_requests - reads) / max(read_requests, 1)) * 100
            except:
                innodb_data['buffer_pool_hit_ratio'] = 0.0
            
            # Get disk I/O operations
            try:
                data_reads_result = conn.execute(text("SHOW STATUS LIKE 'Innodb_data_reads'")).fetchone()
                data_writes_result = conn.execute(text("SHOW STATUS LIKE 'Innodb_data_writes'")).fetchone()
                
                reads = int(data_reads_result[1]) if data_reads_result else 0
                writes = int(data_writes_result[1]) if data_writes_result else 0
                
                # Approximate ops per second (would need time-based calculation for accuracy)
                innodb_data['disk_io_ops_per_sec'] = reads + writes
            except:
                innodb_data['disk_io_ops_per_sec'] = 0.0
            
            return innodb_data
            
        except Exception as e:
            logger.warning(f"Could not get InnoDB metrics: {e}")
            return {
                'buffer_pool_size_mb': 0.0,
                'buffer_pool_used_mb': 0.0,
                'buffer_pool_hit_ratio': 0.0,
                'disk_io_ops_per_sec': 0.0
            }
    
    def _calculate_optimal_pool_settings(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Calculate optimal connection pool settings based on current metrics."""
        try:
            # Base settings
            optimal_settings = {
                'pool_size': 20,
                'max_overflow': 10,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'pool_pre_ping': True
            }
            
            # Adjust based on connection usage
            if metrics.connection_usage_percent > 80:
                # High usage - increase pool size
                optimal_settings['pool_size'] = min(50, int(metrics.connection_pool_size * 1.5))
                optimal_settings['max_overflow'] = min(20, optimal_settings['pool_size'] // 2)
            elif metrics.connection_usage_percent < 20:
                # Low usage - decrease pool size
                optimal_settings['pool_size'] = max(5, int(metrics.connection_pool_size * 0.7))
                optimal_settings['max_overflow'] = max(5, optimal_settings['pool_size'] // 4)
            
            # Adjust based on query performance
            if metrics.avg_query_time_ms > 1000:
                # Slow queries - increase timeout and recycle time
                optimal_settings['pool_timeout'] = 60
                optimal_settings['pool_recycle'] = 1800  # 30 minutes
            
            # Adjust based on environment
            environment = os.getenv('FLASK_ENV', 'production')
            if environment == 'development':
                optimal_settings['pool_size'] = min(optimal_settings['pool_size'], 10)
                optimal_settings['max_overflow'] = min(optimal_settings['max_overflow'], 5)
            elif environment == 'testing':
                optimal_settings['pool_size'] = min(optimal_settings['pool_size'], 5)
                optimal_settings['max_overflow'] = min(optimal_settings['max_overflow'], 2)
            
            return optimal_settings
            
        except Exception as e:
            logger.error(f"Failed to calculate optimal pool settings: {e}")
            return {
                'pool_size': 20,
                'max_overflow': 10,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'pool_pre_ping': True
            }
    
    def _create_optimized_engine(self, database_url: str, settings: Dict[str, Any]) -> Engine:
        """Create an optimized SQLAlchemy engine with the given settings."""
        try:
            # Create engine with optimized settings
            engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=settings['pool_size'],
                max_overflow=settings['max_overflow'],
                pool_timeout=settings['pool_timeout'],
                pool_recycle=settings['pool_recycle'],
                pool_pre_ping=settings['pool_pre_ping'],
                echo=False,
                # Additional MySQL-specific optimizations
                connect_args={
                    'charset': 'utf8mb4',
                    'autocommit': False,
                    'connect_timeout': 10,
                    'read_timeout': 30,
                    'write_timeout': 30
                }
            )
            
            logger.info(f"Created optimized engine with settings: {settings}")
            return engine
            
        except Exception as e:
            logger.error(f"Failed to create optimized engine: {e}")
            raise
    
    def _calculate_pool_improvements(self, current_metrics: PerformanceMetrics, 
                                   optimal_settings: Dict[str, Any]) -> Dict[str, str]:
        """Calculate expected improvements from pool optimization."""
        improvements = {}
        
        # Connection efficiency improvement
        current_efficiency = 100 - current_metrics.connection_usage_percent
        if current_metrics.connection_usage_percent > 80:
            improvements['connection_efficiency'] = "Expected 20-30% improvement in connection availability"
        elif current_metrics.connection_usage_percent < 20:
            improvements['resource_efficiency'] = "Expected 15-25% reduction in resource usage"
        
        # Query performance improvement
        if current_metrics.avg_query_time_ms > 1000:
            improvements['query_performance'] = "Expected 10-20% improvement in query response time"
        
        # Memory usage improvement
        if optimal_settings['pool_size'] < current_metrics.connection_pool_size:
            improvements['memory_usage'] = "Expected 10-15% reduction in memory usage"
        
        return improvements
    
    def _get_engine_key(self, database_url: str) -> str:
        """Generate a unique key for storing optimized engines."""
        import hashlib
        return hashlib.md5(database_url.encode()).hexdigest()[:8]
    
    def start_query_monitoring(self, monitoring_interval: int = 60) -> Dict[str, Any]:
        """
        Start continuous query performance monitoring.
        
        Args:
            monitoring_interval: Interval in seconds between monitoring cycles
            
        Returns:
            Dictionary containing monitoring startup status
        """
        try:
            if self.monitoring_active:
                return {
                    'success': False,
                    'message': 'Query monitoring is already active',
                    'timestamp': datetime.now().isoformat()
                }
            
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                args=(monitoring_interval,),
                daemon=True
            )
            self.monitoring_thread.start()
            
            logger.info(f"Query monitoring started with {monitoring_interval}s interval")
            return {
                'success': True,
                'message': f'Query monitoring started with {monitoring_interval}s interval',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to start query monitoring: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def stop_query_monitoring(self) -> Dict[str, Any]:
        """
        Stop continuous query performance monitoring.
        
        Returns:
            Dictionary containing monitoring stop status
        """
        try:
            if not self.monitoring_active:
                return {
                    'success': False,
                    'message': 'Query monitoring is not active',
                    'timestamp': datetime.now().isoformat()
                }
            
            self.monitoring_active = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            logger.info("Query monitoring stopped")
            return {
                'success': True,
                'message': 'Query monitoring stopped',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to stop query monitoring: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _monitoring_loop(self, interval: int):
        """Main monitoring loop that runs in a separate thread."""
        while self.monitoring_active:
            try:
                # Collect current performance metrics
                metrics = self._collect_connection_metrics(self.config.DATABASE_URL)
                self.performance_history.append(metrics)
                
                # Analyze slow queries if performance schema is available
                self._analyze_slow_queries()
                
                # Cache metrics in Redis if available
                if self.redis_client:
                    self._cache_performance_metrics(metrics)
                
                # Sleep for the specified interval
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)  # Continue monitoring even if there's an error
    
    def _analyze_slow_queries(self):
        """Analyze slow queries from performance schema."""
        try:
            engine = create_engine(self.config.DATABASE_URL, echo=False)
            
            with engine.connect() as conn:
                # Check if performance schema is available
                try:
                    conn.execute(text("SELECT 1 FROM performance_schema.events_statements_summary_by_digest LIMIT 1"))
                except:
                    logger.debug("Performance schema not available for slow query analysis")
                    return
                
                # Get slow queries from performance schema
                slow_query_sql = text("""
                    SELECT 
                        DIGEST_TEXT as query_template,
                        COUNT_STAR as execution_count,
                        SUM_TIMER_WAIT/1000000000 as total_time_ms,
                        AVG_TIMER_WAIT/1000000000 as avg_time_ms,
                        MIN_TIMER_WAIT/1000000000 as min_time_ms,
                        MAX_TIMER_WAIT/1000000000 as max_time_ms,
                        FIRST_SEEN,
                        LAST_SEEN
                    FROM performance_schema.events_statements_summary_by_digest 
                    WHERE AVG_TIMER_WAIT/1000000000 > :threshold
                    ORDER BY AVG_TIMER_WAIT DESC 
                    LIMIT 50
                """)
                
                result = conn.execute(slow_query_sql, {'threshold': self.slow_query_threshold_ms})
                
                for row in result:
                    query_hash = self._generate_query_hash(row[0] or "unknown")
                    
                    query_data = QueryPerformanceData(
                        query_hash=query_hash,
                        query_template=row[0] or "unknown",
                        execution_count=int(row[1] or 0),
                        total_time_ms=float(row[2] or 0),
                        avg_time_ms=float(row[3] or 0),
                        min_time_ms=float(row[4] or 0),
                        max_time_ms=float(row[5] or 0),
                        last_execution=row[7] or datetime.now(),
                        slow_query_threshold_ms=self.slow_query_threshold_ms
                    )
                    
                    self.query_performance_data[query_hash] = query_data
            
            engine.dispose()
            
        except Exception as e:
            logger.debug(f"Could not analyze slow queries: {e}")
    
    def _generate_query_hash(self, query_template: str) -> str:
        """Generate a hash for a query template."""
        import hashlib
        return hashlib.md5(query_template.encode()).hexdigest()[:12]
    
    def _cache_performance_metrics(self, metrics: PerformanceMetrics):
        """Cache performance metrics in Redis."""
        try:
            if not self.redis_client:
                return
            
            # Cache current metrics
            metrics_key = f"mysql_performance:current"
            self.redis_client.setex(
                metrics_key,
                300,  # 5 minutes TTL
                json.dumps(asdict(metrics), default=str)
            )
            
            # Cache historical metrics (keep last 24 hours)
            history_key = f"mysql_performance:history:{int(time.time())}"
            self.redis_client.setex(
                history_key,
                86400,  # 24 hours TTL
                json.dumps(asdict(metrics), default=str)
            )
            
        except Exception as e:
            logger.debug(f"Could not cache performance metrics: {e}")
    
    def get_query_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive query performance report.
        
        Returns:
            Dictionary containing query performance analysis
        """
        try:
            if not self.query_performance_data:
                return {
                    'success': False,
                    'message': 'No query performance data available. Start monitoring first.',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Sort queries by average execution time
            sorted_queries = sorted(
                self.query_performance_data.values(),
                key=lambda x: x.avg_time_ms,
                reverse=True
            )
            
            # Calculate summary statistics
            total_queries = len(sorted_queries)
            slow_queries = [q for q in sorted_queries if q.avg_time_ms > self.slow_query_threshold_ms]
            
            avg_execution_time = statistics.mean([q.avg_time_ms for q in sorted_queries]) if sorted_queries else 0
            median_execution_time = statistics.median([q.avg_time_ms for q in sorted_queries]) if sorted_queries else 0
            
            report = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_unique_queries': total_queries,
                    'slow_queries_count': len(slow_queries),
                    'slow_query_percentage': (len(slow_queries) / max(total_queries, 1)) * 100,
                    'avg_execution_time_ms': avg_execution_time,
                    'median_execution_time_ms': median_execution_time,
                    'slow_query_threshold_ms': self.slow_query_threshold_ms
                },
                'top_slow_queries': [
                    {
                        'query_hash': q.query_hash,
                        'query_template': q.query_template[:200] + '...' if len(q.query_template) > 200 else q.query_template,
                        'execution_count': q.execution_count,
                        'avg_time_ms': q.avg_time_ms,
                        'total_time_ms': q.total_time_ms,
                        'last_execution': q.last_execution.isoformat() if isinstance(q.last_execution, datetime) else str(q.last_execution)
                    }
                    for q in slow_queries[:10]  # Top 10 slow queries
                ],
                'recommendations': self._generate_query_recommendations(slow_queries)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate query performance report: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_query_recommendations(self, slow_queries: List[QueryPerformanceData]) -> List[Dict[str, str]]:
        """Generate recommendations for slow queries."""
        recommendations = []
        
        for query in slow_queries[:5]:  # Top 5 slow queries
            # Analyze query pattern and generate recommendations
            query_lower = query.query_template.lower()
            
            if 'select' in query_lower and 'where' not in query_lower:
                recommendations.append({
                    'query_hash': query.query_hash,
                    'type': 'missing_where_clause',
                    'description': 'Query lacks WHERE clause, potentially scanning entire table',
                    'suggestion': 'Add appropriate WHERE conditions to limit result set'
                })
            
            if 'order by' in query_lower and 'limit' not in query_lower:
                recommendations.append({
                    'query_hash': query.query_hash,
                    'type': 'missing_limit',
                    'description': 'ORDER BY without LIMIT may sort large result sets',
                    'suggestion': 'Consider adding LIMIT clause to reduce sorting overhead'
                })
            
            if query.avg_time_ms > 5000:  # Very slow queries (>5 seconds)
                recommendations.append({
                    'query_hash': query.query_hash,
                    'type': 'very_slow_query',
                    'description': f'Query takes {query.avg_time_ms:.0f}ms on average',
                    'suggestion': 'Consider query optimization, indexing, or result caching'
                })
        
        return recommendations
    
    def implement_caching_strategy(self, strategy_type: str = 'adaptive') -> Dict[str, Any]:
        """
        Implement intelligent caching strategy for MySQL queries.
        
        Args:
            strategy_type: Type of caching strategy ('adaptive', 'aggressive', 'conservative')
            
        Returns:
            Dictionary containing caching implementation results
        """
        try:
            if not self.redis_client:
                return {
                    'success': False,
                    'message': 'Redis not available for caching',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Configure caching parameters based on strategy
            cache_config = self._get_cache_configuration(strategy_type)
            
            # Implement query result caching
            caching_results = {
                'strategy_type': strategy_type,
                'cache_config': cache_config,
                'implementation_status': {}
            }
            
            # Set up query result caching
            caching_results['implementation_status']['query_caching'] = self._setup_query_caching(cache_config)
            
            # Set up connection pool caching
            caching_results['implementation_status']['connection_caching'] = self._setup_connection_caching(cache_config)
            
            # Set up metadata caching
            caching_results['implementation_status']['metadata_caching'] = self._setup_metadata_caching(cache_config)
            
            logger.info(f"Caching strategy '{strategy_type}' implemented successfully")
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'results': caching_results
            }
            
        except Exception as e:
            logger.error(f"Failed to implement caching strategy: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_cache_configuration(self, strategy_type: str) -> Dict[str, Any]:
        """Get caching configuration based on strategy type."""
        base_config = {
            'query_cache_ttl': 300,  # 5 minutes
            'metadata_cache_ttl': 1800,  # 30 minutes
            'connection_cache_ttl': 60,  # 1 minute
            'max_cache_size': 1000,
            'cache_key_prefix': 'vedfolnir:mysql:'
        }
        
        if strategy_type == 'aggressive':
            base_config.update({
                'query_cache_ttl': 1800,  # 30 minutes
                'metadata_cache_ttl': 3600,  # 1 hour
                'max_cache_size': 5000
            })
        elif strategy_type == 'conservative':
            base_config.update({
                'query_cache_ttl': 60,  # 1 minute
                'metadata_cache_ttl': 300,  # 5 minutes
                'max_cache_size': 500
            })
        # 'adaptive' uses base_config as-is
        
        return base_config
    
    def _setup_query_caching(self, cache_config: Dict[str, Any]) -> Dict[str, Any]:
        """Set up query result caching."""
        try:
            # Create cache namespace for query results
            cache_key = f"{cache_config['cache_key_prefix']}queries"
            
            # Set cache configuration in Redis
            config_key = f"{cache_key}:config"
            self.redis_client.setex(
                config_key,
                cache_config['metadata_cache_ttl'],
                json.dumps(cache_config)
            )
            
            return {
                'success': True,
                'cache_namespace': cache_key,
                'ttl': cache_config['query_cache_ttl']
            }
            
        except Exception as e:
            logger.error(f"Failed to setup query caching: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _setup_connection_caching(self, cache_config: Dict[str, Any]) -> Dict[str, Any]:
        """Set up connection pool metrics caching."""
        try:
            # Cache connection pool metrics for monitoring
            cache_key = f"{cache_config['cache_key_prefix']}connections"
            
            # Store current connection metrics
            if self.performance_history:
                latest_metrics = self.performance_history[-1]
                self.redis_client.setex(
                    cache_key,
                    cache_config['connection_cache_ttl'],
                    json.dumps(asdict(latest_metrics), default=str)
                )
            
            return {
                'success': True,
                'cache_namespace': cache_key,
                'ttl': cache_config['connection_cache_ttl']
            }
            
        except Exception as e:
            logger.error(f"Failed to setup connection caching: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _setup_metadata_caching(self, cache_config: Dict[str, Any]) -> Dict[str, Any]:
        """Set up database metadata caching."""
        try:
            # Cache database schema information
            cache_key = f"{cache_config['cache_key_prefix']}metadata"
            
            # Get and cache table information
            metadata_info = self._collect_database_metadata()
            self.redis_client.setex(
                cache_key,
                cache_config['metadata_cache_ttl'],
                json.dumps(metadata_info, default=str)
            )
            
            return {
                'success': True,
                'cache_namespace': cache_key,
                'ttl': cache_config['metadata_cache_ttl'],
                'cached_tables': len(metadata_info.get('tables', []))
            }
            
        except Exception as e:
            logger.error(f"Failed to setup metadata caching: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _collect_database_metadata(self) -> Dict[str, Any]:
        """Collect database metadata for caching."""
        try:
            engine = create_engine(self.config.DATABASE_URL, echo=False)
            metadata_info = {
                'timestamp': datetime.now().isoformat(),
                'tables': [],
                'indexes': [],
                'constraints': []
            }
            
            with engine.connect() as conn:
                # Get table information
                tables_result = conn.execute(text("SHOW TABLES")).fetchall()
                for table_row in tables_result:
                    table_name = table_row[0]
                    
                    # Get table status
                    table_status = conn.execute(text(f"SHOW TABLE STATUS LIKE '{table_name}'")).fetchone()
                    if table_status:
                        metadata_info['tables'].append({
                            'name': table_name,
                            'engine': table_status[1],
                            'rows': table_status[4],
                            'data_length': table_status[6],
                            'index_length': table_status[8]
                        })
                    
                    # Get indexes for this table
                    indexes_result = conn.execute(text(f"SHOW INDEX FROM {table_name}")).fetchall()
                    for index_row in indexes_result:
                        metadata_info['indexes'].append({
                            'table': table_name,
                            'name': index_row[2],
                            'column': index_row[4],
                            'unique': index_row[1] == 0
                        })
            
            engine.dispose()
            return metadata_info
            
        except Exception as e:
            logger.error(f"Failed to collect database metadata: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'tables': [],
                'indexes': [],
                'constraints': [],
                'error': str(e)
            }
    
    def generate_optimization_recommendations(self) -> Dict[str, Any]:
        """
        Generate comprehensive MySQL optimization recommendations.
        
        Returns:
            Dictionary containing detailed optimization recommendations
        """
        try:
            recommendations = []
            
            # Analyze current performance metrics
            if self.performance_history:
                latest_metrics = self.performance_history[-1]
                
                # Connection pool recommendations
                recommendations.extend(self._analyze_connection_pool_performance(latest_metrics))
                
                # Query performance recommendations
                recommendations.extend(self._analyze_query_performance(latest_metrics))
                
                # Memory usage recommendations
                recommendations.extend(self._analyze_memory_usage(latest_metrics))
                
                # I/O performance recommendations
                recommendations.extend(self._analyze_io_performance(latest_metrics))
            
            # Configuration recommendations
            recommendations.extend(self._analyze_mysql_configuration())
            
            # Sort recommendations by priority
            priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            recommendations.sort(key=lambda x: priority_order.get(x.priority, 3))
            
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'total_recommendations': len(recommendations),
                'recommendations': [asdict(rec) for rec in recommendations],
                'summary': self._generate_recommendations_summary(recommendations)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate optimization recommendations: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _analyze_connection_pool_performance(self, metrics: PerformanceMetrics) -> List[OptimizationRecommendation]:
        """Analyze connection pool performance and generate recommendations."""
        recommendations = []
        
        if metrics.connection_usage_percent > 90:
            recommendations.append(OptimizationRecommendation(
                category='connection_pool',
                priority='critical',
                title='Connection Pool Exhaustion Risk',
                description=f'Connection usage is at {metrics.connection_usage_percent:.1f}%, indicating potential pool exhaustion',
                current_value=f'{metrics.active_connections}/{metrics.connection_pool_size}',
                recommended_value=f'{int(metrics.connection_pool_size * 1.5)}/pool_size',
                expected_improvement='Prevent connection timeouts and improve application stability',
                implementation_steps=[
                    'Increase connection pool size in database configuration',
                    'Monitor connection usage patterns',
                    'Consider connection pooling optimization',
                    'Review application connection management'
                ],
                risk_level='low'
            ))
        
        elif metrics.connection_usage_percent < 10:
            recommendations.append(OptimizationRecommendation(
                category='connection_pool',
                priority='medium',
                title='Over-provisioned Connection Pool',
                description=f'Connection usage is only {metrics.connection_usage_percent:.1f}%, indicating over-provisioning',
                current_value=f'{metrics.connection_pool_size}',
                recommended_value=f'{max(5, int(metrics.connection_pool_size * 0.6))}',
                expected_improvement='Reduce memory usage and improve resource efficiency',
                implementation_steps=[
                    'Reduce connection pool size gradually',
                    'Monitor for any performance degradation',
                    'Adjust based on peak usage patterns'
                ],
                risk_level='low'
            ))
        
        return recommendations
    
    def _analyze_query_performance(self, metrics: PerformanceMetrics) -> List[OptimizationRecommendation]:
        """Analyze query performance and generate recommendations."""
        recommendations = []
        
        if metrics.slow_query_ratio_percent > 10:
            recommendations.append(OptimizationRecommendation(
                category='query',
                priority='high',
                title='High Slow Query Ratio',
                description=f'{metrics.slow_query_ratio_percent:.1f}% of queries are slow (>{self.slow_query_threshold_ms}ms)',
                current_value=f'{metrics.slow_query_ratio_percent:.1f}%',
                recommended_value='<5%',
                expected_improvement='Significant improvement in application response time',
                implementation_steps=[
                    'Enable slow query log analysis',
                    'Review and optimize slow queries',
                    'Add appropriate database indexes',
                    'Consider query result caching'
                ],
                risk_level='low'
            ))
        
        if metrics.avg_query_time_ms > 500:
            recommendations.append(OptimizationRecommendation(
                category='query',
                priority='medium',
                title='High Average Query Time',
                description=f'Average query time is {metrics.avg_query_time_ms:.1f}ms',
                current_value=f'{metrics.avg_query_time_ms:.1f}ms',
                recommended_value='<200ms',
                expected_improvement='Improved application responsiveness',
                implementation_steps=[
                    'Analyze query execution plans',
                    'Optimize database schema and indexes',
                    'Consider query optimization',
                    'Implement query result caching'
                ],
                risk_level='low'
            ))
        
        return recommendations
    
    def _analyze_memory_usage(self, metrics: PerformanceMetrics) -> List[OptimizationRecommendation]:
        """Analyze memory usage and generate recommendations."""
        recommendations = []
        
        if metrics.innodb_buffer_pool_hit_ratio < 95:
            recommendations.append(OptimizationRecommendation(
                category='configuration',
                priority='high',
                title='Low InnoDB Buffer Pool Hit Ratio',
                description=f'Buffer pool hit ratio is {metrics.innodb_buffer_pool_hit_ratio:.1f}%, indicating insufficient memory allocation',
                current_value=f'{metrics.innodb_buffer_pool_hit_ratio:.1f}%',
                recommended_value='>95%',
                expected_improvement='Reduced disk I/O and improved query performance',
                implementation_steps=[
                    'Increase innodb_buffer_pool_size',
                    'Monitor memory usage after changes',
                    'Consider server memory upgrade if needed'
                ],
                risk_level='medium'
            ))
        
        return recommendations
    
    def _analyze_io_performance(self, metrics: PerformanceMetrics) -> List[OptimizationRecommendation]:
        """Analyze I/O performance and generate recommendations."""
        recommendations = []
        
        if metrics.disk_io_ops_per_sec > 1000:
            recommendations.append(OptimizationRecommendation(
                category='configuration',
                priority='medium',
                title='High Disk I/O Operations',
                description=f'Disk I/O operations are at {metrics.disk_io_ops_per_sec:.0f} ops/sec',
                current_value=f'{metrics.disk_io_ops_per_sec:.0f} ops/sec',
                recommended_value='<500 ops/sec',
                expected_improvement='Reduced disk bottlenecks and improved performance',
                implementation_steps=[
                    'Increase InnoDB buffer pool size',
                    'Optimize queries to reduce disk access',
                    'Consider SSD storage upgrade',
                    'Implement query result caching'
                ],
                risk_level='low'
            ))
        
        return recommendations
    
    def _analyze_mysql_configuration(self) -> List[OptimizationRecommendation]:
        """Analyze MySQL configuration and generate recommendations."""
        recommendations = []
        
        try:
            engine = create_engine(self.config.DATABASE_URL, echo=False)
            
            with engine.connect() as conn:
                # Check query cache configuration
                try:
                    query_cache_size_result = conn.execute(text("SHOW VARIABLES LIKE 'query_cache_size'")).fetchone()
                    if query_cache_size_result and int(query_cache_size_result[1]) == 0:
                        recommendations.append(OptimizationRecommendation(
                            category='configuration',
                            priority='medium',
                            title='Query Cache Disabled',
                            description='MySQL query cache is disabled, missing potential performance benefits',
                            current_value='0',
                            recommended_value='64M-256M',
                            expected_improvement='Improved performance for repeated queries',
                            implementation_steps=[
                                'Enable query cache in MySQL configuration',
                                'Set appropriate query_cache_size',
                                'Monitor query cache hit ratio'
                            ],
                            risk_level='low'
                        ))
                except:
                    pass  # Query cache might not be available in newer MySQL versions
                
                # Check thread cache configuration
                try:
                    thread_cache_size_result = conn.execute(text("SHOW VARIABLES LIKE 'thread_cache_size'")).fetchone()
                    if thread_cache_size_result and int(thread_cache_size_result[1]) < 8:
                        recommendations.append(OptimizationRecommendation(
                            category='configuration',
                            priority='low',
                            title='Small Thread Cache Size',
                            description=f'Thread cache size is {thread_cache_size_result[1]}, may cause thread creation overhead',
                            current_value=thread_cache_size_result[1],
                            recommended_value='8-16',
                            expected_improvement='Reduced thread creation overhead',
                            implementation_steps=[
                                'Increase thread_cache_size in MySQL configuration',
                                'Monitor thread cache hit ratio'
                            ],
                            risk_level='low'
                        ))
                except:
                    pass
            
            engine.dispose()
            
        except Exception as e:
            logger.debug(f"Could not analyze MySQL configuration: {e}")
        
        return recommendations
    
    def _generate_recommendations_summary(self, recommendations: List[OptimizationRecommendation]) -> Dict[str, Any]:
        """Generate a summary of optimization recommendations."""
        summary = {
            'total_recommendations': len(recommendations),
            'by_priority': {
                'critical': len([r for r in recommendations if r.priority == 'critical']),
                'high': len([r for r in recommendations if r.priority == 'high']),
                'medium': len([r for r in recommendations if r.priority == 'medium']),
                'low': len([r for r in recommendations if r.priority == 'low'])
            },
            'by_category': {
                'connection_pool': len([r for r in recommendations if r.category == 'connection_pool']),
                'query': len([r for r in recommendations if r.category == 'query']),
                'configuration': len([r for r in recommendations if r.category == 'configuration']),
                'cache': len([r for r in recommendations if r.category == 'cache'])
            },
            'implementation_priority': []
        }
        
        # Add implementation priority suggestions
        critical_recs = [r for r in recommendations if r.priority == 'critical']
        if critical_recs:
            summary['implementation_priority'].append('Address critical issues immediately')
        
        high_recs = [r for r in recommendations if r.priority == 'high']
        if high_recs:
            summary['implementation_priority'].append('Implement high priority optimizations within 1 week')
        
        medium_recs = [r for r in recommendations if r.priority == 'medium']
        if medium_recs:
            summary['implementation_priority'].append('Plan medium priority optimizations for next maintenance window')
        
        return summary
    
    def get_performance_metrics_history(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get historical performance metrics.
        
        Args:
            hours: Number of hours of history to retrieve
            
        Returns:
            Dictionary containing historical performance data
        """
        try:
            # Get metrics from memory (recent data)
            memory_metrics = list(self.performance_history)
            
            # Get metrics from Redis cache (if available)
            redis_metrics = []
            if self.redis_client:
                redis_metrics = self._get_cached_metrics_history(hours)
            
            # Combine and sort metrics
            all_metrics = memory_metrics + redis_metrics
            all_metrics.sort(key=lambda x: x.timestamp)
            
            # Filter by time range
            cutoff_time = datetime.now() - timedelta(hours=hours)
            filtered_metrics = [m for m in all_metrics if m.timestamp >= cutoff_time]
            
            # Calculate trends
            trends = self._calculate_performance_trends(filtered_metrics)
            
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'time_range_hours': hours,
                'metrics_count': len(filtered_metrics),
                'metrics': [asdict(m) for m in filtered_metrics],
                'trends': trends
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics history: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_cached_metrics_history(self, hours: int) -> List[PerformanceMetrics]:
        """Get cached metrics from Redis."""
        try:
            cached_metrics = []
            
            # Get all cached metrics keys
            pattern = "mysql_performance:history:*"
            keys = self.redis_client.keys(pattern)
            
            for key in keys:
                try:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        metrics_dict = json.loads(cached_data)
                        # Convert back to PerformanceMetrics object
                        metrics_dict['timestamp'] = datetime.fromisoformat(metrics_dict['timestamp'])
                        metrics = PerformanceMetrics(**metrics_dict)
                        cached_metrics.append(metrics)
                except Exception as e:
                    logger.debug(f"Could not parse cached metrics from {key}: {e}")
            
            return cached_metrics
            
        except Exception as e:
            logger.debug(f"Could not get cached metrics history: {e}")
            return []
    
    def _calculate_performance_trends(self, metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Calculate performance trends from historical data."""
        if len(metrics) < 2:
            return {'insufficient_data': True}
        
        try:
            # Calculate trends for key metrics
            connection_usage_trend = self._calculate_trend([m.connection_usage_percent for m in metrics])
            query_time_trend = self._calculate_trend([m.avg_query_time_ms for m in metrics])
            slow_query_trend = self._calculate_trend([m.slow_query_ratio_percent for m in metrics])
            buffer_pool_trend = self._calculate_trend([m.innodb_buffer_pool_hit_ratio for m in metrics])
            
            return {
                'connection_usage': connection_usage_trend,
                'avg_query_time': query_time_trend,
                'slow_query_ratio': slow_query_trend,
                'buffer_pool_hit_ratio': buffer_pool_trend,
                'overall_trend': self._determine_overall_trend([
                    connection_usage_trend, query_time_trend, slow_query_trend, buffer_pool_trend
                ])
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate performance trends: {e}")
            return {'error': str(e)}
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend for a series of values."""
        if len(values) < 2:
            return {'trend': 'insufficient_data'}
        
        # Simple linear trend calculation
        x = list(range(len(values)))
        n = len(values)
        
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        # Calculate slope (trend)
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # Determine trend direction
        if abs(slope) < 0.01:
            trend_direction = 'stable'
        elif slope > 0:
            trend_direction = 'increasing'
        else:
            trend_direction = 'decreasing'
        
        return {
            'trend': trend_direction,
            'slope': slope,
            'current_value': values[-1],
            'change_from_start': values[-1] - values[0],
            'percent_change': ((values[-1] - values[0]) / max(abs(values[0]), 0.01)) * 100
        }
    
    def _determine_overall_trend(self, trends: List[Dict[str, Any]]) -> str:
        """Determine overall performance trend from individual trends."""
        improving_count = 0
        degrading_count = 0
        
        for trend in trends:
            if trend.get('trend') == 'improving':
                improving_count += 1
            elif trend.get('trend') == 'degrading':
                degrading_count += 1
        
        if improving_count > degrading_count:
            return 'improving'
        elif degrading_count > improving_count:
            return 'degrading'
        else:
            return 'stable'
    
    def get_optimized_engine(self, database_url: Optional[str] = None) -> Optional[Engine]:
        """
        Get an optimized SQLAlchemy engine for the given database URL.
        
        Args:
            database_url: Optional database URL, uses config default if not provided
            
        Returns:
            Optimized SQLAlchemy engine or None if not available
        """
        try:
            db_url = database_url or self.config.DATABASE_URL
            engine_key = self._get_engine_key(db_url)
            
            return self.optimized_engines.get(engine_key)
            
        except Exception as e:
            logger.error(f"Failed to get optimized engine: {e}")
            return None
    
    def cleanup_resources(self):
        """Clean up resources and stop monitoring."""
        try:
            # Stop monitoring
            self.stop_query_monitoring()
            
            # Close optimized engines
            for engine in self.optimized_engines.values():
                try:
                    engine.dispose()
                except:
                    pass
            
            self.optimized_engines.clear()
            
            # Close Redis connection
            if self.redis_client:
                try:
                    self.redis_client.close()
                except:
                    pass
            
            logger.info("MySQL Performance Optimizer resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")


def main():
    """Command-line interface for MySQL Performance Optimizer."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MySQL Performance Optimizer for Vedfolnir')
    parser.add_argument('--action', choices=[
        'optimize-pool', 'start-monitoring', 'stop-monitoring', 
        'query-report', 'implement-caching', 'recommendations', 
        'metrics-history', 'status'
    ], required=True, help='Action to perform')
    
    parser.add_argument('--database-url', help='Database URL (optional, uses config default)')
    parser.add_argument('--monitoring-interval', type=int, default=60, 
                       help='Monitoring interval in seconds (default: 60)')
    parser.add_argument('--caching-strategy', choices=['adaptive', 'aggressive', 'conservative'], 
                       default='adaptive', help='Caching strategy type')
    parser.add_argument('--history-hours', type=int, default=24, 
                       help='Hours of history to retrieve (default: 24)')
    parser.add_argument('--output-format', choices=['json', 'table'], default='table',
                       help='Output format (default: table)')
    
    args = parser.parse_args()
    
    # Initialize optimizer
    try:
        optimizer = MySQLPerformanceOptimizer()
        
        if args.action == 'optimize-pool':
            result = optimizer.optimize_connection_pool(args.database_url)
            print_result(result, args.output_format)
            
        elif args.action == 'start-monitoring':
            result = optimizer.start_query_monitoring(args.monitoring_interval)
            print_result(result, args.output_format)
            
        elif args.action == 'stop-monitoring':
            result = optimizer.stop_query_monitoring()
            print_result(result, args.output_format)
            
        elif args.action == 'query-report':
            result = optimizer.get_query_performance_report()
            print_result(result, args.output_format)
            
        elif args.action == 'implement-caching':
            result = optimizer.implement_caching_strategy(args.caching_strategy)
            print_result(result, args.output_format)
            
        elif args.action == 'recommendations':
            result = optimizer.generate_optimization_recommendations()
            print_result(result, args.output_format)
            
        elif args.action == 'metrics-history':
            result = optimizer.get_performance_metrics_history(args.history_hours)
            print_result(result, args.output_format)
            
        elif args.action == 'status':
            # Show current status
            status = {
                'monitoring_active': optimizer.monitoring_active,
                'cached_queries': len(optimizer.query_performance_data),
                'performance_history_count': len(optimizer.performance_history),
                'optimized_engines': len(optimizer.optimized_engines),
                'redis_available': optimizer.redis_client is not None
            }
            print_result({'success': True, 'status': status}, args.output_format)
        
        # Cleanup
        optimizer.cleanup_resources()
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        print_result(error_result, args.output_format)
        sys.exit(1)


def print_result(result: Dict[str, Any], output_format: str):
    """Print result in the specified format."""
    if output_format == 'json':
        print(json.dumps(result, indent=2, default=str))
    else:
        # Table format
        print(f"\n{'='*60}")
        print(f"MySQL Performance Optimizer - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if result.get('success'):
            print("✅ Operation completed successfully")
            
            # Print key information based on result content
            if 'optimal_settings' in result:
                print(f"\n🔧 Optimal Settings:")
                for key, value in result['optimal_settings'].items():
                    print(f"  {key}: {value}")
            
            if 'recommendations' in result:
                recommendations = result['recommendations']
                if recommendations:
                    print(f"\n💡 Recommendations ({len(recommendations)}):")
                    for i, rec in enumerate(recommendations[:5], 1):  # Show top 5
                        priority_emoji = {'critical': '🚨', 'high': '⚠️', 'medium': '📋', 'low': '💭'}
                        emoji = priority_emoji.get(rec.get('priority', 'low'), '📋')
                        print(f"  {i}. {emoji} {rec.get('title', 'Unknown')}")
                        print(f"     {rec.get('description', '')}")
                else:
                    print("\n✅ No optimization recommendations - system is performing well!")
            
            if 'summary' in result:
                summary = result['summary']
                print(f"\n📊 Summary:")
                for key, value in summary.items():
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for sub_key, sub_value in value.items():
                            print(f"    {sub_key}: {sub_value}")
                    else:
                        print(f"  {key}: {value}")
        
        else:
            print("❌ Operation failed")
            if 'error' in result:
                print(f"Error: {result['error']}")
        
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
