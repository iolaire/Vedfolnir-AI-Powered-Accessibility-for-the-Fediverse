# Configuration System Monitoring and Maintenance

## Overview

This document provides comprehensive procedures for monitoring and maintaining the Configuration Integration System to ensure optimal performance, reliability, and security.

## Table of Contents

1. [Monitoring Setup](#monitoring-setup)
2. [Health Checks](#health-checks)
3. [Performance Monitoring](#performance-monitoring)
4. [Alerting Configuration](#alerting-configuration)
5. [Maintenance Procedures](#maintenance-procedures)
6. [Troubleshooting](#troubleshooting)
7. [Capacity Planning](#capacity-planning)

## Monitoring Setup

### System Monitoring Components

```python
#!/usr/bin/env python3
"""
Configuration System Monitoring Setup
"""

import json
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class ConfigurationSystemMonitor:
    """
    Comprehensive monitoring for configuration system
    """
    
    def __init__(self, config_service, monitoring_config: Dict):
        self.config_service = config_service
        self.monitoring_config = monitoring_config
        self.metrics_history = []
        self.alerts = []
        self.monitoring_active = False
        
    def start_monitoring(self):
        """Start all monitoring components"""
        self.monitoring_active = True
        
        # Start monitoring threads
        threads = [
            threading.Thread(target=self._monitor_performance, daemon=True),
            threading.Thread(target=self._monitor_health, daemon=True),
            threading.Thread(target=self._monitor_cache, daemon=True),
            threading.Thread(target=self._monitor_database, daemon=True),
            threading.Thread(target=self._cleanup_old_data, daemon=True)
        ]
        
        for thread in threads:
            thread.start()
        
        logging.info("Configuration system monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        logging.info("Configuration system monitoring stopped")
    
    def _monitor_performance(self):
        """Monitor configuration access performance"""
        while self.monitoring_active:
            try:
                # Measure configuration access time
                start_time = time.time()
                self.config_service.get_config('session_timeout_minutes', 120)
                access_time = (time.time() - start_time) * 1000  # ms
                
                # Record metric
                self._record_metric('config_access_time_ms', access_time)
                
                # Check threshold
                threshold = self.monitoring_config.get('access_time_threshold_ms', 50)
                if access_time > threshold:
                    self._create_alert(
                        'performance',
                        f'Slow configuration access: {access_time:.2f}ms',
                        'warning'
                    )
                
                time.sleep(self.monitoring_config.get('performance_check_interval', 60))
                
            except Exception as e:
                logging.error(f"Performance monitoring error: {e}")
                time.sleep(60)
    
    def _monitor_health(self):
        """Monitor system health"""
        while self.monitoring_active:
            try:
                health_status = self._check_system_health()
                self._record_metric('system_health', health_status)
                
                # Check for health issues
                if not health_status.get('overall_healthy', True):
                    self._create_alert(
                        'health',
                        f'System health degraded: {health_status}',
                        'critical'
                    )
                
                time.sleep(self.monitoring_config.get('health_check_interval', 30))
                
            except Exception as e:
                logging.error(f"Health monitoring error: {e}")
                time.sleep(30)
    
    def _monitor_cache(self):
        """Monitor cache performance"""
        while self.monitoring_active:
            try:
                cache_stats = self.config_service.get_cache_stats()
                
                # Record cache metrics
                self._record_metric('cache_hit_rate', cache_stats['hit_rate'])
                self._record_metric('cache_size', cache_stats['cache']['size'])
                
                # Check cache hit rate
                min_hit_rate = self.monitoring_config.get('min_cache_hit_rate', 0.8)
                if cache_stats['hit_rate'] < min_hit_rate:
                    self._create_alert(
                        'cache',
                        f'Low cache hit rate: {cache_stats["hit_rate"]:.2%}',
                        'warning'
                    )
                
                # Check cache size
                max_cache_usage = self.monitoring_config.get('max_cache_usage', 0.9)
                cache_usage = cache_stats['cache']['size'] / cache_stats['cache']['maxsize']
                if cache_usage > max_cache_usage:
                    self._create_alert(
                        'cache',
                        f'High cache usage: {cache_usage:.2%}',
                        'warning'
                    )
                
                time.sleep(self.monitoring_config.get('cache_check_interval', 120))
                
            except Exception as e:
                logging.error(f"Cache monitoring error: {e}")
                time.sleep(120)
    
    def _monitor_database(self):
        """Monitor database performance"""
        while self.monitoring_active:
            try:
                # Measure database response time
                start_time = time.time()
                with self.config_service.db_manager.get_session() as session:
                    session.execute("SELECT 1")
                db_time = (time.time() - start_time) * 1000  # ms
                
                self._record_metric('database_response_time_ms', db_time)
                
                # Check database response time
                threshold = self.monitoring_config.get('db_response_threshold_ms', 100)
                if db_time > threshold:
                    self._create_alert(
                        'database',
                        f'Slow database response: {db_time:.2f}ms',
                        'warning'
                    )
                
                time.sleep(self.monitoring_config.get('database_check_interval', 60))
                
            except Exception as e:
                logging.error(f"Database monitoring error: {e}")
                self._create_alert(
                    'database',
                    f'Database connection error: {e}',
                    'critical'
                )
                time.sleep(60)
    
    def _check_system_health(self) -> Dict:
        """Check overall system health"""
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'configuration_service': True,
            'database': True,
            'cache': True,
            'memory_usage': 0.0,
            'overall_healthy': True
        }
        
        try:
            # Check configuration service
            self.config_service.get_config('test_key', 'default')
        except Exception:
            health_status['configuration_service'] = False
            health_status['overall_healthy'] = False
        
        try:
            # Check database
            with self.config_service.db_manager.get_session() as session:
                session.execute("SELECT 1")
        except Exception:
            health_status['database'] = False
            health_status['overall_healthy'] = False
        
        try:
            # Check cache
            stats = self.config_service.get_cache_stats()
            if stats['hit_rate'] < 0.5:  # Very low hit rate indicates issues
                health_status['cache'] = False
        except Exception:
            health_status['cache'] = False
        
        try:
            # Check memory usage
            import psutil
            memory = psutil.virtual_memory()
            health_status['memory_usage'] = memory.percent / 100.0
            
            if memory.percent > 90:
                health_status['overall_healthy'] = False
        except Exception:
            pass
        
        return health_status
    
    def _record_metric(self, metric_name: str, value):
        """Record a metric value"""
        metric = {
            'timestamp': datetime.utcnow(),
            'metric': metric_name,
            'value': value
        }
        
        self.metrics_history.append(metric)
    
    def _create_alert(self, category: str, message: str, severity: str):
        """Create an alert"""
        alert = {
            'timestamp': datetime.utcnow(),
            'category': category,
            'message': message,
            'severity': severity,
            'acknowledged': False
        }
        
        self.alerts.append(alert)
        logging.warning(f"ALERT [{severity.upper()}] {category}: {message}")
        
        # Send notification if configured
        self._send_alert_notification(alert)
    
    def _send_alert_notification(self, alert: Dict):
        """Send alert notification"""
        # Implementation depends on notification system
        # Could be email, webhook, Slack, etc.
        pass
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        while self.monitoring_active:
            try:
                cutoff_time = datetime.utcnow() - timedelta(
                    hours=self.monitoring_config.get('retention_hours', 24)
                )
                
                # Clean up old metrics
                self.metrics_history = [
                    m for m in self.metrics_history 
                    if m['timestamp'] > cutoff_time
                ]
                
                # Clean up old alerts (keep acknowledged ones longer)
                alert_cutoff = datetime.utcnow() - timedelta(
                    hours=self.monitoring_config.get('alert_retention_hours', 72)
                )
                
                self.alerts = [
                    a for a in self.alerts 
                    if a['timestamp'] > alert_cutoff or not a['acknowledged']
                ]
                
                time.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                logging.error(f"Cleanup error: {e}")
                time.sleep(3600)
    
    def get_metrics_summary(self, hours: int = 1) -> Dict:
        """Get metrics summary for specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_metrics = [
            m for m in self.metrics_history 
            if m['timestamp'] > cutoff_time
        ]
        
        # Group metrics by name
        metrics_by_name = {}
        for metric in recent_metrics:
            name = metric['metric']
            if name not in metrics_by_name:
                metrics_by_name[name] = []
            metrics_by_name[name].append(metric['value'])
        
        # Calculate summary statistics
        summary = {}
        for name, values in metrics_by_name.items():
            if values:
                summary[name] = {
                    'count': len(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values)
                }
        
        return summary
    
    def get_active_alerts(self) -> List[Dict]:
        """Get active (unacknowledged) alerts"""
        return [a for a in self.alerts if not a['acknowledged']]
    
    def acknowledge_alert(self, alert_index: int):
        """Acknowledge an alert"""
        if 0 <= alert_index < len(self.alerts):
            self.alerts[alert_index]['acknowledged'] = True
            self.alerts[alert_index]['acknowledged_at'] = datetime.utcnow()
```

## Health Checks

### Automated Health Check System

```python
#!/usr/bin/env python3
"""
Configuration System Health Checks
"""

class ConfigurationHealthChecker:
    """
    Comprehensive health checking for configuration system
    """
    
    def __init__(self, config_service):
        self.config_service = config_service
        self.health_checks = [
            self._check_configuration_service,
            self._check_database_connectivity,
            self._check_cache_performance,
            self._check_event_system,
            self._check_service_adapters,
            self._check_memory_usage,
            self._check_disk_space
        ]
    
    def run_all_health_checks(self) -> Dict:
        """Run all health checks and return results"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        for check in self.health_checks:
            try:
                check_name = check.__name__.replace('_check_', '')
                check_result = check()
                results['checks'][check_name] = check_result
                
                if not check_result.get('healthy', True):
                    results['overall_status'] = 'unhealthy'
                    
            except Exception as e:
                results['checks'][check.__name__] = {
                    'healthy': False,
                    'error': str(e)
                }
                results['overall_status'] = 'unhealthy'
        
        return results
    
    def _check_configuration_service(self) -> Dict:
        """Check configuration service health"""
        try:
            # Test basic configuration access
            start_time = time.time()
            value = self.config_service.get_config('test_key', 'default')
            response_time = (time.time() - start_time) * 1000
            
            # Test configuration with metadata
            config_value = self.config_service.get_config_with_metadata('session_timeout_minutes')
            
            # Test cache statistics
            stats = self.config_service.get_cache_stats()
            
            return {
                'healthy': True,
                'response_time_ms': response_time,
                'cache_hit_rate': stats['hit_rate'],
                'cache_size': stats['cache']['size']
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_database_connectivity(self) -> Dict:
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            
            with self.config_service.db_manager.get_session() as session:
                # Test basic connectivity
                session.execute("SELECT 1")
                
                # Test configuration table access
                result = session.execute(
                    "SELECT COUNT(*) FROM system_configurations"
                ).scalar()
                
            response_time = (time.time() - start_time) * 1000
            
            return {
                'healthy': True,
                'response_time_ms': response_time,
                'configuration_count': result
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_cache_performance(self) -> Dict:
        """Check cache performance and health"""
        try:
            stats = self.config_service.get_cache_stats()
            
            # Check hit rate
            hit_rate_healthy = stats['hit_rate'] >= 0.7  # 70% minimum
            
            # Check cache size utilization
            cache_usage = stats['cache']['size'] / stats['cache']['maxsize']
            cache_size_healthy = cache_usage < 0.95  # Less than 95% full
            
            return {
                'healthy': hit_rate_healthy and cache_size_healthy,
                'hit_rate': stats['hit_rate'],
                'cache_usage': cache_usage,
                'total_requests': stats['total_requests']
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_event_system(self) -> Dict:
        """Check event system functionality"""
        try:
            # Test event subscription and notification
            test_events = []
            
            def test_callback(key, old_value, new_value):
                test_events.append((key, old_value, new_value))
            
            # Subscribe to test event
            subscription_id = self.config_service.subscribe_to_changes(
                'health_check_test_key', 
                test_callback
            )
            
            # Trigger test event
            self.config_service.notify_change(
                'health_check_test_key', 
                'old_test_value', 
                'new_test_value'
            )
            
            # Wait for event processing
            time.sleep(0.1)
            
            # Clean up
            self.config_service.unsubscribe(subscription_id)
            
            return {
                'healthy': len(test_events) > 0,
                'events_received': len(test_events)
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_service_adapters(self) -> Dict:
        """Check service adapter health"""
        # This would check if service adapters are functioning
        # Implementation depends on how adapters are managed
        return {
            'healthy': True,
            'note': 'Service adapter health check not implemented'
        }
    
    def _check_memory_usage(self) -> Dict:
        """Check memory usage"""
        try:
            import psutil
            
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()
            
            memory_mb = memory_info.rss / 1024 / 1024
            memory_healthy = memory_mb < 500  # Less than 500MB
            
            return {
                'healthy': memory_healthy,
                'process_memory_mb': memory_mb,
                'system_memory_percent': system_memory.percent
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_disk_space(self) -> Dict:
        """Check disk space"""
        try:
            import psutil
            
            disk_usage = psutil.disk_usage('.')
            free_percent = (disk_usage.free / disk_usage.total) * 100
            
            disk_healthy = free_percent > 10  # More than 10% free
            
            return {
                'healthy': disk_healthy,
                'free_percent': free_percent,
                'free_gb': disk_usage.free / (1024**3)
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
```

This monitoring and maintenance document provides comprehensive procedures for keeping the configuration system healthy and performing optimally.