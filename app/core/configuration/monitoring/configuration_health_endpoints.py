# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Health Check Endpoints

Health check functions for configuration service components,
providing detailed health status and metrics for monitoring.
"""

import time
import psutil
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import text
import redis

logger = logging.getLogger(__name__)


class ConfigurationHealthChecks:
    """
    Health check implementations for configuration service components
    """
    
    def __init__(self, configuration_service=None, configuration_cache=None, 
                 db_manager=None, event_bus=None, metrics_collector=None):
        """
        Initialize health checks with component references
        
        Args:
            configuration_service: ConfigurationService instance
            configuration_cache: ConfigurationCache instance
            db_manager: DatabaseManager instance
            event_bus: ConfigurationEventBus instance
            metrics_collector: ConfigurationMetricsCollector instance
        """
        self.configuration_service = configuration_service
        self.configuration_cache = configuration_cache
        self.db_manager = db_manager
        self.event_bus = event_bus
        self.metrics_collector = metrics_collector
    
    def check_configuration_service_health(self) -> Dict[str, Any]:
        """
        Check health of the main configuration service
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            start_time = time.time()
            
            if not self.configuration_service:
                return {
                    'status': 'critical',
                    'error': 'Configuration service not available',
                    'response_time_ms': 0.0
                }
            
            # Test basic functionality
            test_key = '_health_check_test'
            test_value = f'health_check_{int(time.time())}'
            
            # Try to get a configuration (should work even if key doesn't exist)
            try:
                result = self.configuration_service.get_config(test_key, test_value)
                config_access_working = True
            except Exception as e:
                config_access_working = False
                logger.warning(f"Configuration access test failed: {str(e)}")
            
            # Get cache statistics
            cache_stats = {}
            try:
                cache_stats = self.configuration_service.get_cache_stats()
            except Exception as e:
                logger.warning(f"Failed to get cache stats: {str(e)}")
            
            # Check restart requirements
            restart_required = False
            pending_configs = []
            try:
                restart_required = self.configuration_service.is_restart_required()
                pending_configs = self.configuration_service.get_pending_restart_configs()
            except Exception as e:
                logger.warning(f"Failed to check restart requirements: {str(e)}")
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status
            if not config_access_working:
                status = 'critical'
            elif cache_stats.get('hit_rate', 0) < 0.5:  # Low cache hit rate
                status = 'warning'
            else:
                status = 'healthy'
            
            return {
                'status': status,
                'response_time_ms': response_time,
                'config_access_working': config_access_working,
                'cache_stats': cache_stats,
                'restart_required': restart_required,
                'pending_restart_configs': pending_configs,
                'subscriber_count': len(getattr(self.configuration_service, '_subscribers', {})),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Configuration service health check failed: {str(e)}")
            return {
                'status': 'critical',
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000 if 'start_time' in locals() else 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def check_configuration_cache_health(self) -> Dict[str, Any]:
        """
        Check health of the configuration cache
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            start_time = time.time()
            
            if not self.configuration_cache:
                return {
                    'status': 'critical',
                    'error': 'Configuration cache not available',
                    'response_time_ms': 0.0
                }
            
            # Get cache statistics
            cache_stats = self.configuration_cache.get_stats()
            cache_info = self.configuration_cache.get_cache_info()
            
            # Test cache operations
            test_key = '_cache_health_test'
            test_value_obj = type('TestValue', (), {
                'key': test_key,
                'value': f'test_{int(time.time())}',
                'data_type': 'string',
                'source': 'test',
                'requires_restart': False,
                'last_updated': datetime.now(timezone.utc),
                'cached_at': datetime.now(timezone.utc),
                'ttl': 60
            })()
            
            cache_operations_working = True
            try:
                # Test set operation
                self.configuration_cache.set(test_key, test_value_obj, ttl=60)
                
                # Test get operation
                retrieved = self.configuration_cache.get(test_key)
                
                # Test invalidate operation
                self.configuration_cache.invalidate(test_key)
                
                if retrieved is None:
                    cache_operations_working = False
                    
            except Exception as e:
                cache_operations_working = False
                logger.warning(f"Cache operations test failed: {str(e)}")
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on metrics
            hit_rate = cache_stats.hit_rate
            memory_usage_mb = cache_stats.memory_usage_bytes / (1024 * 1024)
            cache_efficiency = cache_stats.cache_efficiency
            
            if not cache_operations_working:
                status = 'critical'
            elif hit_rate < 0.3 or cache_efficiency < 0.5:
                status = 'warning'
            elif memory_usage_mb > 100:  # Over 100MB
                status = 'warning'
            else:
                status = 'healthy'
            
            return {
                'status': status,
                'response_time_ms': response_time,
                'cache_operations_working': cache_operations_working,
                'hit_rate': hit_rate,
                'cache_efficiency': cache_efficiency,
                'memory_usage_mb': memory_usage_mb,
                'total_keys': cache_stats.total_keys,
                'hits': cache_stats.hits,
                'misses': cache_stats.misses,
                'evictions': cache_stats.evictions,
                'average_access_time_ms': cache_stats.average_access_time_ms,
                'maxsize': cache_info['maxsize'],
                'current_size': cache_info['current_size'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Configuration cache health check failed: {str(e)}")
            return {
                'status': 'critical',
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000 if 'start_time' in locals() else 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def check_database_connection_health(self) -> Dict[str, Any]:
        """
        Check health of database connection
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            start_time = time.time()
            
            if not self.db_manager:
                return {
                    'status': 'critical',
                    'error': 'Database manager not available',
                    'response_time_ms': 0.0
                }
            
            # Test database connectivity
            connection_working = True
            query_working = True
            
            try:
                with self.db_manager.get_session() as session:
                    # Test basic connectivity
                    result = session.execute(text("SELECT 1")).fetchone()
                    if not result or result[0] != 1:
                        connection_working = False
                    
                    # Test configuration table access
                    config_count = session.execute(
                        text("SELECT COUNT(*) FROM system_configurations")
                    ).fetchone()
                    
                    if config_count is None:
                        query_working = False
                        
            except Exception as e:
                connection_working = False
                query_working = False
                logger.warning(f"Database connectivity test failed: {str(e)}")
            
            # Get connection pool information
            pool_info = {}
            try:
                engine = self.db_manager.engine
                pool = engine.pool
                pool_info = {
                    'pool_size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid()
                }
            except Exception as e:
                logger.warning(f"Failed to get pool info: {str(e)}")
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status
            if not connection_working:
                status = 'critical'
            elif not query_working:
                status = 'critical'
            elif response_time > 1000:  # Over 1 second
                status = 'warning'
            else:
                status = 'healthy'
            
            return {
                'status': status,
                'response_time_ms': response_time,
                'connection_working': connection_working,
                'query_working': query_working,
                'pool_info': pool_info,
                'database_url': self.db_manager.config.DATABASE_URL.split('@')[0] + '@***' if hasattr(self.db_manager, 'config') else 'unknown',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database connection health check failed: {str(e)}")
            return {
                'status': 'critical',
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000 if 'start_time' in locals() else 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def check_event_bus_health(self) -> Dict[str, Any]:
        """
        Check health of configuration event bus
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            start_time = time.time()
            
            if not self.event_bus:
                return {
                    'status': 'critical',
                    'error': 'Event bus not available',
                    'response_time_ms': 0.0
                }
            
            # Test event bus functionality
            event_publishing_working = True
            subscription_working = True
            
            test_key = '_event_bus_health_test'
            test_callback_called = False
            
            def test_callback(key, old_value, new_value):
                nonlocal test_callback_called
                test_callback_called = True
            
            try:
                # Test subscription
                subscription_id = self.event_bus.subscribe(test_key, test_callback)
                
                # Test event publishing
                # Create a simple test event object
                test_event = type('ConfigurationChangeEvent', (), {
                    'key': test_key,
                    'old_value': 'old',
                    'new_value': 'new',
                    'source': 'health_check',
                    'timestamp': datetime.now(timezone.utc),
                    'requires_restart': False,
                    'admin_user_id': None
                })()
                
                self.event_bus.publish(test_event)
                
                # Give a moment for async processing
                time.sleep(0.1)
                
                # Clean up subscription
                self.event_bus.unsubscribe(subscription_id)
                
                if not test_callback_called:
                    event_publishing_working = False
                    
            except Exception as e:
                event_publishing_working = False
                subscription_working = False
                logger.warning(f"Event bus functionality test failed: {str(e)}")
            
            # Get subscriber statistics
            subscriber_stats = {}
            try:
                if hasattr(self.event_bus, '_subscribers'):
                    total_subscriptions = sum(len(subs) for subs in self.event_bus._subscribers.values())
                    subscriber_stats = {
                        'total_keys_with_subscribers': len(self.event_bus._subscribers),
                        'total_subscriptions': total_subscriptions,
                        'keys_with_subscribers': list(self.event_bus._subscribers.keys())
                    }
            except Exception as e:
                logger.warning(f"Failed to get subscriber stats: {str(e)}")
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status
            if not event_publishing_working or not subscription_working:
                status = 'critical'
            elif response_time > 500:  # Over 500ms
                status = 'warning'
            else:
                status = 'healthy'
            
            return {
                'status': status,
                'response_time_ms': response_time,
                'event_publishing_working': event_publishing_working,
                'subscription_working': subscription_working,
                'test_callback_called': test_callback_called,
                'subscriber_stats': subscriber_stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Event bus health check failed: {str(e)}")
            return {
                'status': 'critical',
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000 if 'start_time' in locals() else 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def check_metrics_collector_health(self) -> Dict[str, Any]:
        """
        Check health of metrics collector
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            start_time = time.time()
            
            if not self.metrics_collector:
                return {
                    'status': 'critical',
                    'error': 'Metrics collector not available',
                    'response_time_ms': 0.0
                }
            
            # Test metrics collection functionality
            metrics_recording_working = True
            metrics_analysis_working = True
            
            try:
                # Test recording metrics
                self.metrics_collector.record_access(
                    key='_health_check_test',
                    source='health_check',
                    access_time_ms=1.0,
                    success=True
                )
                
                # Test metrics analysis
                summary = self.metrics_collector.get_comprehensive_summary(hours=1)
                if not summary:
                    metrics_analysis_working = False
                    
            except Exception as e:
                metrics_recording_working = False
                metrics_analysis_working = False
                logger.warning(f"Metrics collector functionality test failed: {str(e)}")
            
            # Get metrics statistics
            metrics_stats = {}
            try:
                access_patterns = self.metrics_collector.get_access_patterns(hours=1)
                cache_performance = self.metrics_collector.get_cache_performance(hours=1)
                change_frequency = self.metrics_collector.get_change_frequency(hours=24)
                
                metrics_stats = {
                    'total_accesses': access_patterns.get('total_accesses', 0),
                    'cache_hit_rate': cache_performance.get('hit_rate', 0.0),
                    'total_changes': change_frequency.get('total_changes', 0),
                    'error_rate': access_patterns.get('error_rate', 0.0)
                }
            except Exception as e:
                logger.warning(f"Failed to get metrics stats: {str(e)}")
            
            # Check memory usage
            memory_usage_mb = 0
            try:
                process = psutil.Process()
                memory_usage_mb = process.memory_info().rss / (1024 * 1024)
            except Exception as e:
                logger.warning(f"Failed to get memory usage: {str(e)}")
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status
            if not metrics_recording_working or not metrics_analysis_working:
                status = 'critical'
            elif memory_usage_mb > 500:  # Over 500MB
                status = 'warning'
            elif response_time > 200:  # Over 200ms
                status = 'warning'
            else:
                status = 'healthy'
            
            return {
                'status': status,
                'response_time_ms': response_time,
                'metrics_recording_working': metrics_recording_working,
                'metrics_analysis_working': metrics_analysis_working,
                'metrics_stats': metrics_stats,
                'memory_usage_mb': memory_usage_mb,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Metrics collector health check failed: {str(e)}")
            return {
                'status': 'critical',
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000 if 'start_time' in locals() else 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def check_system_resources_health(self) -> Dict[str, Any]:
        """
        Check system resource health (CPU, memory, disk)
        
        Returns:
            Dictionary with system resource status
        """
        try:
            start_time = time.time()
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get process-specific metrics
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024 * 1024)
            process_cpu_percent = process.cpu_percent()
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on resource usage
            status = 'healthy'
            
            if cpu_percent > 90 or memory.percent > 95 or disk.percent > 95:
                status = 'critical'
            elif cpu_percent > 70 or memory.percent > 80 or disk.percent > 80:
                status = 'warning'
            elif process_memory_mb > 1000:  # Process using over 1GB
                status = 'warning'
            
            return {
                'status': status,
                'response_time_ms': response_time,
                'system_cpu_percent': cpu_percent,
                'system_memory_percent': memory.percent,
                'system_memory_available_mb': memory.available / (1024 * 1024),
                'system_disk_percent': disk.percent,
                'system_disk_free_gb': disk.free / (1024 * 1024 * 1024),
                'process_memory_mb': process_memory_mb,
                'process_cpu_percent': process_cpu_percent,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"System resources health check failed: {str(e)}")
            return {
                'status': 'critical',
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000 if 'start_time' in locals() else 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_all_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all health checks and return comprehensive results
        
        Returns:
            Dictionary with all health check results
        """
        return {
            'configuration_service': self.check_configuration_service_health(),
            'configuration_cache': self.check_configuration_cache_health(),
            'database_connection': self.check_database_connection_health(),
            'event_bus': self.check_event_bus_health(),
            'metrics_collector': self.check_metrics_collector_health(),
            'system_resources': self.check_system_resources_health()
        }