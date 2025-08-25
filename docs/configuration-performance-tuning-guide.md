# Configuration System Performance Tuning Guide

## Overview

This guide provides comprehensive performance tuning recommendations for the Configuration Integration System. Follow these guidelines to optimize configuration access performance, reduce latency, and minimize resource usage.

## Table of Contents

1. [Performance Metrics](#performance-metrics)
2. [Cache Optimization](#cache-optimization)
3. [Database Performance](#database-performance)
4. [Event System Performance](#event-system-performance)
5. [Memory Optimization](#memory-optimization)
6. [Network Optimization](#network-optimization)
7. [Monitoring and Alerting](#monitoring-and-alerting)
8. [Performance Testing](#performance-testing)

## Performance Metrics

### Key Performance Indicators (KPIs)

Monitor these metrics to assess configuration system performance:

#### Response Time Metrics
- **Configuration Access Latency**: Target < 10ms for cached values
- **Database Query Time**: Target < 50ms for uncached values
- **Cache Hit Rate**: Target > 90%
- **Event Propagation Time**: Target < 30 seconds

#### Throughput Metrics
- **Requests per Second**: Monitor configuration access rate
- **Cache Operations per Second**: Monitor cache performance
- **Database Connections**: Monitor connection pool usage

#### Resource Metrics
- **Memory Usage**: Monitor cache and service memory consumption
- **CPU Usage**: Monitor configuration processing overhead
- **Database Connection Pool**: Monitor connection utilization

### Performance Monitoring Setup

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Performance Monitor

Monitors and reports configuration system performance metrics.
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = None


class ConfigurationPerformanceMonitor:
    """
    Monitor configuration system performance metrics
    """
    
    def __init__(self, config_service, retention_hours: int = 24):
        """
        Initialize performance monitor
        
        Args:
            config_service: ConfigurationService instance
            retention_hours: How long to retain metrics
        """
        self.config_service = config_service
        self.retention_hours = retention_hours
        self.metrics: Dict[str, deque] = {}
        self._lock = threading.RLock()
        self._monitoring = False
        self._monitor_thread = None
    
    def start_monitoring(self, interval_seconds: int = 60):
        """Start performance monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Configuration performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Configuration performance monitoring stopped")
    
    def _monitor_loop(self, interval_seconds: int):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                self._collect_metrics()
                self._cleanup_old_metrics()
                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                time.sleep(interval_seconds)
    
    def _collect_metrics(self):
        """Collect current performance metrics"""
        timestamp = datetime.utcnow()
        
        # Cache metrics
        cache_stats = self.config_service.get_cache_stats()
        self._record_metric("cache_hit_rate", cache_stats['hit_rate'], timestamp)
        self._record_metric("cache_size", cache_stats['cache']['size'], timestamp)
        self._record_metric("total_requests", cache_stats['total_requests'], timestamp)
        
        # Response time metrics (measure actual access time)
        start_time = time.time()
        self.config_service.get_config('session_timeout_minutes', 120)
        access_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        self._record_metric("config_access_time_ms", access_time, timestamp)
        
        # Memory metrics
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self._record_metric("memory_usage_mb", memory_mb, timestamp)
        
        # Database connection metrics
        try:
            with self.config_service.db_manager.get_session() as session:
                # This is a simple way to test database responsiveness
                start_time = time.time()
                session.execute("SELECT 1")
                db_time = (time.time() - start_time) * 1000
                self._record_metric("database_response_time_ms", db_time, timestamp)
        except Exception as e:
            logger.error(f"Error measuring database response time: {e}")
    
    def _record_metric(self, metric_name: str, value: float, timestamp: datetime):
        """Record a performance metric"""
        with self._lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = deque()
            
            metric = PerformanceMetric(
                timestamp=timestamp,
                metric_name=metric_name,
                value=value
            )
            self.metrics[metric_name].append(metric)
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        with self._lock:
            for metric_name, metric_deque in self.metrics.items():
                while metric_deque and metric_deque[0].timestamp < cutoff_time:
                    metric_deque.popleft()
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Dict[str, float]]:
        """Get performance summary for specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        summary = {}
        
        with self._lock:
            for metric_name, metric_deque in self.metrics.items():
                recent_metrics = [
                    m for m in metric_deque 
                    if m.timestamp >= cutoff_time
                ]
                
                if recent_metrics:
                    values = [m.value for m in recent_metrics]
                    summary[metric_name] = {
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }
        
        return summary
    
    def get_performance_alerts(self) -> List[str]:
        """Get performance alerts based on thresholds"""
        alerts = []
        summary = self.get_performance_summary(hours=1)
        
        # Check cache hit rate
        if 'cache_hit_rate' in summary:
            hit_rate = summary['cache_hit_rate']['avg']
            if hit_rate < 0.8:  # 80% threshold
                alerts.append(f"Low cache hit rate: {hit_rate:.2%}")
        
        # Check response time
        if 'config_access_time_ms' in summary:
            avg_time = summary['config_access_time_ms']['avg']
            if avg_time > 50:  # 50ms threshold
                alerts.append(f"High configuration access time: {avg_time:.1f}ms")
        
        # Check database response time
        if 'database_response_time_ms' in summary:
            db_time = summary['database_response_time_ms']['avg']
            if db_time > 100:  # 100ms threshold
                alerts.append(f"High database response time: {db_time:.1f}ms")
        
        # Check memory usage
        if 'memory_usage_mb' in summary:
            memory_mb = summary['memory_usage_mb']['avg']
            if memory_mb > 500:  # 500MB threshold
                alerts.append(f"High memory usage: {memory_mb:.1f}MB")
        
        return alerts
```

## Cache Optimization

### Cache Size Tuning

Optimize cache size based on your configuration usage patterns:

```python
def optimize_cache_size(config_service, target_hit_rate: float = 0.95):
    """
    Optimize cache size to achieve target hit rate
    """
    current_stats = config_service.get_cache_stats()
    current_hit_rate = current_stats['hit_rate']
    current_size = current_stats['cache']['maxsize']
    
    print(f"Current cache size: {current_size}")
    print(f"Current hit rate: {current_hit_rate:.2%}")
    
    if current_hit_rate < target_hit_rate:
        # Increase cache size
        recommended_size = int(current_size * (target_hit_rate / current_hit_rate))
        print(f"Recommended cache size: {recommended_size}")
        
        # Apply new cache size (requires service restart)
        return recommended_size
    else:
        print("Cache size is optimal")
        return current_size

# Usage
recommended_size = optimize_cache_size(config_service)

# Apply in configuration service initialization
config_service = ConfigurationService(
    db_manager, 
    cache_size=recommended_size
)
```

### TTL Optimization

Optimize Time-To-Live (TTL) values based on configuration change frequency:

```python
def optimize_cache_ttl(config_service, config_key: str, change_frequency_hours: float):
    """
    Optimize TTL based on configuration change frequency
    
    Args:
        config_service: ConfigurationService instance
        config_key: Configuration key to optimize
        change_frequency_hours: How often this config changes (in hours)
    """
    # Rule of thumb: TTL should be 1/4 of change frequency
    optimal_ttl = int(change_frequency_hours * 3600 / 4)  # Convert to seconds
    
    # Minimum TTL of 60 seconds, maximum of 1 hour
    optimal_ttl = max(60, min(3600, optimal_ttl))
    
    print(f"Optimal TTL for {config_key}: {optimal_ttl} seconds")
    return optimal_ttl

# Configuration-specific TTL recommendations
ttl_recommendations = {
    'session_timeout_minutes': optimize_cache_ttl(config_service, 'session_timeout_minutes', 24),  # Changes daily
    'max_concurrent_jobs': optimize_cache_ttl(config_service, 'max_concurrent_jobs', 4),  # Changes every 4 hours
    'maintenance_mode': optimize_cache_ttl(config_service, 'maintenance_mode', 0.5),  # Changes every 30 minutes
}
```

### Cache Warming

Implement cache warming for frequently accessed configurations:

```python
def warm_configuration_cache(config_service, critical_keys: List[str]):
    """
    Warm cache with critical configuration keys
    """
    print("Warming configuration cache...")
    
    for key in critical_keys:
        try:
            value = config_service.get_config(key)
            print(f"Warmed cache for {key}: {value}")
        except Exception as e:
            print(f"Failed to warm cache for {key}: {e}")
    
    # Verify cache warming
    stats = config_service.get_cache_stats()
    print(f"Cache size after warming: {stats['cache']['size']}")

# Critical configurations to warm
critical_configurations = [
    'session_timeout_minutes',
    'max_concurrent_jobs',
    'default_job_timeout',
    'rate_limit_per_user_per_hour',
    'maintenance_mode',
    'enable_batch_processing'
]

warm_configuration_cache(config_service, critical_configurations)
```

## Database Performance

### Query Optimization

Optimize database queries for configuration access:

```sql
-- Ensure proper indexing on configuration table
CREATE INDEX idx_system_configurations_key ON system_configurations(key);
CREATE INDEX idx_system_configurations_updated_at ON system_configurations(updated_at);
CREATE INDEX idx_system_configurations_category ON system_configurations(category);

-- Analyze query performance
EXPLAIN SELECT * FROM system_configurations WHERE key = 'session_timeout_minutes';

-- Check for slow queries
SELECT * FROM information_schema.processlist WHERE time > 1;
```

### Connection Pool Optimization

Optimize database connection pool settings:

```python
def optimize_database_connection_pool(db_manager):
    """
    Optimize database connection pool for configuration access patterns
    """
    # Configuration access is typically read-heavy with occasional writes
    # Optimize for read performance
    
    optimal_settings = {
        'pool_size': 20,  # Base connection pool size
        'max_overflow': 30,  # Additional connections during peak
        'pool_timeout': 30,  # Timeout for getting connection
        'pool_recycle': 3600,  # Recycle connections every hour
        'pool_pre_ping': True,  # Verify connections before use
    }
    
    print("Recommended database connection pool settings:")
    for setting, value in optimal_settings.items():
        print(f"  {setting}: {value}")
    
    return optimal_settings

# Apply in database manager initialization
optimal_settings = optimize_database_connection_pool(db_manager)
```

### Database Maintenance

Regular database maintenance for optimal performance:

```sql
-- Analyze table statistics
ANALYZE TABLE system_configurations;

-- Optimize table structure
OPTIMIZE TABLE system_configurations;

-- Check table fragmentation
SELECT 
    table_name,
    data_length,
    index_length,
    data_free,
    (data_free / (data_length + index_length)) * 100 AS fragmentation_percent
FROM information_schema.tables 
WHERE table_name = 'system_configurations';

-- Rebuild indexes if fragmentation > 10%
ALTER TABLE system_configurations ENGINE=InnoDB;
```

## Event System Performance

### Event Processing Optimization

Optimize event processing for better performance:

```python
class OptimizedConfigurationEventBus:
    """
    Optimized event bus with batching and async processing
    """
    
    def __init__(self, batch_size: int = 10, batch_timeout: float = 1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.event_queue = []
        self.subscribers = {}
        self._lock = threading.RLock()
        self._processing = False
        self._process_thread = None
    
    def start_processing(self):
        """Start async event processing"""
        if self._processing:
            return
        
        self._processing = True
        self._process_thread = threading.Thread(
            target=self._process_events,
            daemon=True
        )
        self._process_thread.start()
    
    def _process_events(self):
        """Process events in batches"""
        while self._processing:
            try:
                events_to_process = []
                
                with self._lock:
                    if len(self.event_queue) >= self.batch_size:
                        events_to_process = self.event_queue[:self.batch_size]
                        self.event_queue = self.event_queue[self.batch_size:]
                
                if events_to_process:
                    self._process_event_batch(events_to_process)
                else:
                    time.sleep(self.batch_timeout)
                    
            except Exception as e:
                logger.error(f"Error processing events: {e}")
                time.sleep(1)
    
    def _process_event_batch(self, events):
        """Process a batch of events"""
        # Group events by key for efficient processing
        events_by_key = {}
        for event in events:
            key = event.key
            if key not in events_by_key:
                events_by_key[key] = []
            events_by_key[key].append(event)
        
        # Process events for each key
        for key, key_events in events_by_key.items():
            subscribers = self.subscribers.get(key, {})
            
            # Only process the latest event for each key
            latest_event = key_events[-1]
            
            for subscription_id, callback in subscribers.items():
                try:
                    callback(latest_event.key, latest_event.old_value, latest_event.new_value)
                except Exception as e:
                    logger.error(f"Error in event callback {subscription_id}: {e}")
```

### Subscription Management Optimization

Optimize subscription management for better performance:

```python
def optimize_subscription_management(service_adapters):
    """
    Optimize subscription management across service adapters
    """
    # Consolidate subscriptions to reduce overhead
    subscription_map = {}
    
    for adapter in service_adapters:
        for key in adapter.get_configuration_keys():
            if key not in subscription_map:
                subscription_map[key] = []
            subscription_map[key].append(adapter)
    
    # Create single subscription per key with multiplexed callbacks
    for key, adapters in subscription_map.items():
        def create_multiplexed_callback(adapter_list):
            def multiplexed_callback(key, old_value, new_value):
                for adapter in adapter_list:
                    try:
                        adapter.handle_configuration_change(key, old_value, new_value)
                    except Exception as e:
                        logger.error(f"Error in adapter {adapter.__class__.__name__}: {e}")
            return multiplexed_callback
        
        # Single subscription for multiple adapters
        callback = create_multiplexed_callback(adapters)
        subscription_id = config_service.subscribe_to_changes(key, callback)
        
        print(f"Optimized subscription for {key}: {len(adapters)} adapters")
```

## Memory Optimization

### Memory Usage Monitoring

Monitor and optimize memory usage:

```python
import psutil
import gc
from pympler import tracker

def monitor_memory_usage(config_service):
    """
    Monitor memory usage of configuration system
    """
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"Memory Usage Analysis:")
    print(f"  RSS: {memory_info.rss / 1024 / 1024:.1f} MB")
    print(f"  VMS: {memory_info.vms / 1024 / 1024:.1f} MB")
    
    # Cache memory usage
    cache_stats = config_service.get_cache_stats()
    estimated_cache_memory = cache_stats['cache']['size'] * 1024  # Rough estimate
    print(f"  Estimated cache memory: {estimated_cache_memory / 1024:.1f} KB")
    
    # Python object tracking
    gc.collect()
    objects = gc.get_objects()
    print(f"  Python objects: {len(objects)}")
    
    # Memory growth tracking
    tr = tracker.SummaryTracker()
    
    # Perform operations
    for i in range(100):
        config_service.get_config(f'test_key_{i}', 'default')
    
    tr.print_diff()

def optimize_memory_usage(config_service):
    """
    Optimize memory usage of configuration system
    """
    # Force garbage collection
    gc.collect()
    
    # Clear unnecessary cache entries
    config_service.refresh_config()
    
    # Optimize cache size based on memory constraints
    available_memory = psutil.virtual_memory().available
    max_cache_memory = available_memory * 0.01  # Use 1% of available memory
    max_cache_size = int(max_cache_memory / 1024)  # Rough estimate
    
    print(f"Recommended max cache size: {max_cache_size}")
    
    return max_cache_size
```

### Memory Leak Prevention

Prevent memory leaks in configuration system:

```python
def prevent_memory_leaks():
    """
    Best practices for preventing memory leaks
    """
    
    # 1. Always clean up subscriptions
    class ConfigurationAdapter:
        def __init__(self, config_service):
            self.config_service = config_service
            self.subscriptions = []
        
        def subscribe_to_config(self, key, callback):
            subscription_id = self.config_service.subscribe_to_changes(key, callback)
            self.subscriptions.append(subscription_id)
            return subscription_id
        
        def cleanup(self):
            """Clean up all subscriptions"""
            for subscription_id in self.subscriptions:
                self.config_service.unsubscribe(subscription_id)
            self.subscriptions.clear()
    
    # 2. Use weak references for callbacks when appropriate
    import weakref
    
    class WeakCallbackManager:
        def __init__(self):
            self.callbacks = {}
        
        def add_callback(self, key, obj, method_name):
            """Add callback using weak reference"""
            weak_ref = weakref.ref(obj)
            self.callbacks[key] = (weak_ref, method_name)
        
        def call_callback(self, key, *args):
            """Call callback if object still exists"""
            if key in self.callbacks:
                weak_ref, method_name = self.callbacks[key]
                obj = weak_ref()
                if obj is not None:
                    method = getattr(obj, method_name)
                    method(*args)
                else:
                    # Object was garbage collected, remove callback
                    del self.callbacks[key]
    
    # 3. Periodic cleanup
    def periodic_cleanup(config_service):
        """Perform periodic cleanup"""
        # Force garbage collection
        gc.collect()
        
        # Clean up expired cache entries
        config_service.refresh_config()
        
        # Log memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"Memory usage after cleanup: {memory_mb:.1f} MB")
```

## Network Optimization

### Connection Optimization

Optimize network connections for distributed deployments:

```python
def optimize_network_connections(config_service):
    """
    Optimize network connections for configuration system
    """
    # Connection pooling for database
    connection_settings = {
        'pool_size': 20,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Connection keep-alive settings
    keepalive_settings = {
        'tcp_keepalive': True,
        'tcp_keepalive_idle': 600,  # 10 minutes
        'tcp_keepalive_interval': 30,  # 30 seconds
        'tcp_keepalive_count': 3
    }
    
    print("Network optimization settings:")
    print("Connection pool:", connection_settings)
    print("Keep-alive:", keepalive_settings)
    
    return connection_settings, keepalive_settings
```

### Compression and Serialization

Optimize data serialization for better network performance:

```python
import json
import pickle
import gzip
from typing import Any

class OptimizedConfigurationSerializer:
    """
    Optimized serialization for configuration data
    """
    
    @staticmethod
    def serialize(data: Any, compress: bool = True) -> bytes:
        """
        Serialize configuration data with optional compression
        """
        # Use pickle for Python objects (faster than JSON)
        serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        
        if compress and len(serialized) > 1024:  # Compress if > 1KB
            serialized = gzip.compress(serialized)
        
        return serialized
    
    @staticmethod
    def deserialize(data: bytes, compressed: bool = None) -> Any:
        """
        Deserialize configuration data with automatic compression detection
        """
        # Auto-detect compression
        if compressed is None:
            compressed = data[:2] == b'\x1f\x8b'  # gzip magic number
        
        if compressed:
            data = gzip.decompress(data)
        
        return pickle.loads(data)
    
    @staticmethod
    def benchmark_serialization(data: Any):
        """
        Benchmark different serialization methods
        """
        import time
        
        # JSON serialization
        start_time = time.time()
        json_data = json.dumps(data).encode('utf-8')
        json_time = time.time() - start_time
        
        # Pickle serialization
        start_time = time.time()
        pickle_data = pickle.dumps(data)
        pickle_time = time.time() - start_time
        
        # Compressed pickle
        start_time = time.time()
        compressed_data = gzip.compress(pickle_data)
        compress_time = time.time() - start_time
        
        print(f"Serialization benchmark:")
        print(f"  JSON: {len(json_data)} bytes, {json_time*1000:.2f}ms")
        print(f"  Pickle: {len(pickle_data)} bytes, {pickle_time*1000:.2f}ms")
        print(f"  Compressed: {len(compressed_data)} bytes, {compress_time*1000:.2f}ms")
        
        return {
            'json': (len(json_data), json_time),
            'pickle': (len(pickle_data), pickle_time),
            'compressed': (len(compressed_data), compress_time)
        }
```

## Monitoring and Alerting

### Performance Dashboard

Create a performance monitoring dashboard:

```python
def create_performance_dashboard(config_service):
    """
    Create performance monitoring dashboard
    """
    dashboard_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'cache_performance': {},
        'database_performance': {},
        'memory_usage': {},
        'system_health': {}
    }
    
    # Cache performance
    cache_stats = config_service.get_cache_stats()
    dashboard_data['cache_performance'] = {
        'hit_rate': cache_stats['hit_rate'],
        'size': cache_stats['cache']['size'],
        'max_size': cache_stats['cache']['maxsize'],
        'total_requests': cache_stats['total_requests']
    }
    
    # Database performance
    start_time = time.time()
    try:
        with config_service.db_manager.get_session() as session:
            session.execute("SELECT 1")
        db_response_time = (time.time() - start_time) * 1000
        dashboard_data['database_performance'] = {
            'response_time_ms': db_response_time,
            'status': 'healthy' if db_response_time < 100 else 'slow'
        }
    except Exception as e:
        dashboard_data['database_performance'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # Memory usage
    process = psutil.Process()
    memory_info = process.memory_info()
    dashboard_data['memory_usage'] = {
        'rss_mb': memory_info.rss / 1024 / 1024,
        'vms_mb': memory_info.vms / 1024 / 1024,
        'cpu_percent': process.cpu_percent()
    }
    
    # System health
    dashboard_data['system_health'] = {
        'configuration_service': 'healthy',
        'cache_system': 'healthy' if cache_stats['hit_rate'] > 0.8 else 'degraded',
        'database': dashboard_data['database_performance']['status']
    }
    
    return dashboard_data

def setup_performance_alerts(config_service, alert_thresholds):
    """
    Set up performance alerting
    """
    def check_performance_alerts():
        alerts = []
        
        # Check cache hit rate
        cache_stats = config_service.get_cache_stats()
        if cache_stats['hit_rate'] < alert_thresholds.get('min_hit_rate', 0.8):
            alerts.append({
                'severity': 'warning',
                'message': f"Low cache hit rate: {cache_stats['hit_rate']:.2%}",
                'metric': 'cache_hit_rate',
                'value': cache_stats['hit_rate']
            })
        
        # Check memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        if memory_mb > alert_thresholds.get('max_memory_mb', 500):
            alerts.append({
                'severity': 'critical',
                'message': f"High memory usage: {memory_mb:.1f}MB",
                'metric': 'memory_usage',
                'value': memory_mb
            })
        
        return alerts
    
    return check_performance_alerts
```

## Performance Testing

### Load Testing

Implement load testing for configuration system:

```python
import concurrent.futures
import random
import statistics

def load_test_configuration_access(config_service, num_threads=10, requests_per_thread=100):
    """
    Load test configuration access performance
    """
    print(f"Starting load test: {num_threads} threads, {requests_per_thread} requests each")
    
    # Test configuration keys
    test_keys = [
        'session_timeout_minutes',
        'max_concurrent_jobs',
        'default_job_timeout',
        'rate_limit_per_user_per_hour',
        'maintenance_mode'
    ]
    
    def worker_thread(thread_id):
        """Worker thread for load testing"""
        response_times = []
        errors = 0
        
        for i in range(requests_per_thread):
            try:
                key = random.choice(test_keys)
                start_time = time.time()
                value = config_service.get_config(key)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to ms
                response_times.append(response_time)
                
            except Exception as e:
                errors += 1
                logger.error(f"Error in thread {thread_id}: {e}")
        
        return {
            'thread_id': thread_id,
            'response_times': response_times,
            'errors': errors
        }
    
    # Execute load test
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    end_time = time.time()
    
    # Analyze results
    all_response_times = []
    total_errors = 0
    
    for result in results:
        all_response_times.extend(result['response_times'])
        total_errors += result['errors']
    
    total_requests = num_threads * requests_per_thread
    total_time = end_time - start_time
    requests_per_second = total_requests / total_time
    
    print(f"\nLoad Test Results:")
    print(f"  Total requests: {total_requests}")
    print(f"  Total time: {total_time:.2f} seconds")
    print(f"  Requests per second: {requests_per_second:.2f}")
    print(f"  Total errors: {total_errors}")
    print(f"  Error rate: {total_errors/total_requests:.2%}")
    
    if all_response_times:
        print(f"  Average response time: {statistics.mean(all_response_times):.2f}ms")
        print(f"  Median response time: {statistics.median(all_response_times):.2f}ms")
        print(f"  95th percentile: {sorted(all_response_times)[int(len(all_response_times)*0.95)]:.2f}ms")
        print(f"  Max response time: {max(all_response_times):.2f}ms")
    
    # Check cache performance after load test
    cache_stats = config_service.get_cache_stats()
    print(f"  Final cache hit rate: {cache_stats['hit_rate']:.2%}")
    
    return {
        'requests_per_second': requests_per_second,
        'error_rate': total_errors/total_requests,
        'avg_response_time': statistics.mean(all_response_times) if all_response_times else 0,
        'cache_hit_rate': cache_stats['hit_rate']
    }

# Run load test
load_test_results = load_test_configuration_access(config_service)
```

### Stress Testing

Implement stress testing to find system limits:

```python
def stress_test_configuration_system(config_service, max_threads=50, duration_seconds=300):
    """
    Stress test configuration system to find limits
    """
    print(f"Starting stress test: up to {max_threads} threads for {duration_seconds} seconds")
    
    results = []
    current_threads = 1
    
    while current_threads <= max_threads:
        print(f"\nTesting with {current_threads} threads...")
        
        # Run load test with current thread count
        test_result = load_test_configuration_access(
            config_service, 
            num_threads=current_threads, 
            requests_per_thread=50
        )
        
        test_result['thread_count'] = current_threads
        results.append(test_result)
        
        # Check if system is still performing well
        if test_result['error_rate'] > 0.05 or test_result['avg_response_time'] > 100:
            print(f"⚠️  Performance degradation detected at {current_threads} threads")
            break
        
        current_threads += 5
    
    # Find optimal thread count
    optimal_threads = 1
    best_rps = 0
    
    for result in results:
        if result['error_rate'] < 0.01 and result['requests_per_second'] > best_rps:
            best_rps = result['requests_per_second']
            optimal_threads = result['thread_count']
    
    print(f"\nStress Test Summary:")
    print(f"  Optimal thread count: {optimal_threads}")
    print(f"  Best requests per second: {best_rps:.2f}")
    print(f"  System limit reached at: {current_threads} threads")
    
    return {
        'optimal_threads': optimal_threads,
        'max_rps': best_rps,
        'system_limit': current_threads,
        'detailed_results': results
    }
```

This performance tuning guide provides comprehensive optimization strategies for the configuration system. Regular monitoring and tuning based on these guidelines will ensure optimal performance.