#!/usr/bin/env python3
"""
MySQL Performance Monitoring Integration for Vedfolnir

This script integrates the MySQL Performance Optimizer with the existing
health monitoring system to provide comprehensive performance monitoring,
automated optimization, and alerting capabilities.
"""

import logging
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.mysql_performance_optimizer import MySQLPerformanceOptimizer, OptimizationRecommendation
    from mysql_connection_validator import MySQLConnectionValidator
    from config import Config
    import redis
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required packages are installed")
    sys.exit(1)

logger = logging.getLogger(__name__)

class MySQLPerformanceMonitor:
    """
    Integrated MySQL performance monitoring system that combines
    health checking, performance optimization, and automated alerting.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the performance monitor."""
        self.config = config or Config()
        self.optimizer = MySQLPerformanceOptimizer(config)
        self.validator = MySQLConnectionValidator()
        
        # Monitoring configuration
        self.monitoring_enabled = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_interval = int(os.getenv('MYSQL_MONITORING_INTERVAL', '300'))  # 5 minutes
        
        # Performance thresholds for alerting
        self.thresholds = {
            'connection_usage_critical': float(os.getenv('MYSQL_CONNECTION_USAGE_CRITICAL', '90')),
            'connection_usage_warning': float(os.getenv('MYSQL_CONNECTION_USAGE_WARNING', '75')),
            'slow_query_ratio_critical': float(os.getenv('MYSQL_SLOW_QUERY_RATIO_CRITICAL', '20')),
            'slow_query_ratio_warning': float(os.getenv('MYSQL_SLOW_QUERY_RATIO_WARNING', '10')),
            'avg_query_time_critical': float(os.getenv('MYSQL_AVG_QUERY_TIME_CRITICAL', '2000')),
            'avg_query_time_warning': float(os.getenv('MYSQL_AVG_QUERY_TIME_WARNING', '1000')),
            'buffer_pool_hit_ratio_critical': float(os.getenv('MYSQL_BUFFER_POOL_HIT_RATIO_CRITICAL', '90')),
            'buffer_pool_hit_ratio_warning': float(os.getenv('MYSQL_BUFFER_POOL_HIT_RATIO_WARNING', '95'))
        }
        
        # Auto-optimization settings
        self.auto_optimize_enabled = os.getenv('MYSQL_AUTO_OPTIMIZE_ENABLED', 'false').lower() == 'true'
        self.auto_optimize_interval = int(os.getenv('MYSQL_AUTO_OPTIMIZE_INTERVAL', '3600'))  # 1 hour
        self.last_optimization = datetime.min
        
        # Redis for caching and alerting
        self.redis_client: Optional[redis.Redis] = None
        self._initialize_redis()
        
        logger.info("MySQL Performance Monitor initialized")
    
    def _initialize_redis(self):
        """Initialize Redis connection for caching and alerting."""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/2')  # Use DB 2 for monitoring
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established for performance monitoring")
        except Exception as e:
            logger.warning(f"Redis not available for performance monitoring: {e}")
            self.redis_client = None
    
    def start_monitoring(self) -> Dict[str, Any]:
        """Start comprehensive performance monitoring."""
        try:
            if self.monitoring_enabled:
                return {
                    'success': False,
                    'message': 'Performance monitoring is already active',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Start the optimizer's query monitoring
            optimizer_result = self.optimizer.start_query_monitoring(60)  # 1 minute intervals
            if not optimizer_result.get('success'):
                return optimizer_result
            
            # Start our integrated monitoring
            self.monitoring_enabled = True
            self.monitoring_thread = threading.Thread(
                target=self._integrated_monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            
            logger.info(f"Integrated MySQL performance monitoring started (interval: {self.monitoring_interval}s)")
            return {
                'success': True,
                'message': f'Integrated performance monitoring started with {self.monitoring_interval}s interval',
                'auto_optimize_enabled': self.auto_optimize_enabled,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to start performance monitoring: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop comprehensive performance monitoring."""
        try:
            if not self.monitoring_enabled:
                return {
                    'success': False,
                    'message': 'Performance monitoring is not active',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Stop integrated monitoring
            self.monitoring_enabled = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=10)
            
            # Stop optimizer monitoring
            optimizer_result = self.optimizer.stop_query_monitoring()
            
            logger.info("Integrated MySQL performance monitoring stopped")
            return {
                'success': True,
                'message': 'Integrated performance monitoring stopped',
                'optimizer_result': optimizer_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to stop performance monitoring: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _integrated_monitoring_loop(self):
        """Main integrated monitoring loop."""
        while self.monitoring_enabled:
            try:
                # Collect comprehensive performance data
                monitoring_data = self._collect_monitoring_data()
                
                # Analyze performance and generate alerts
                alerts = self._analyze_performance_and_generate_alerts(monitoring_data)
                
                # Handle auto-optimization if enabled
                if self.auto_optimize_enabled:
                    self._handle_auto_optimization(monitoring_data)
                
                # Cache monitoring data
                if self.redis_client:
                    self._cache_monitoring_data(monitoring_data, alerts)
                
                # Log performance summary
                self._log_performance_summary(monitoring_data, alerts)
                
                # Sleep until next monitoring cycle
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in integrated monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_monitoring_data(self) -> Dict[str, Any]:
        """Collect comprehensive monitoring data."""
        monitoring_data = {
            'timestamp': datetime.now().isoformat(),
            'health_check': None,
            'performance_metrics': None,
            'query_performance': None,
            'optimization_recommendations': None
        }
        
        try:
            # Health check
            health_result = self.validator.perform_health_check()
            monitoring_data['health_check'] = {
                'healthy': health_result.healthy,
                'status': health_result.status,
                'metrics': health_result.metrics,
                'details': health_result.details
            }
            
            # Performance metrics from optimizer
            if self.optimizer.performance_history:
                latest_metrics = self.optimizer.performance_history[-1]
                monitoring_data['performance_metrics'] = {
                    'connection_usage_percent': latest_metrics.connection_usage_percent,
                    'avg_query_time_ms': latest_metrics.avg_query_time_ms,
                    'slow_query_ratio_percent': latest_metrics.slow_query_ratio_percent,
                    'innodb_buffer_pool_hit_ratio': latest_metrics.innodb_buffer_pool_hit_ratio,
                    'active_connections': latest_metrics.active_connections,
                    'connection_pool_size': latest_metrics.connection_pool_size
                }
            
            # Query performance report
            query_report = self.optimizer.get_query_performance_report()
            if query_report.get('success'):
                monitoring_data['query_performance'] = query_report.get('summary', {})
            
            # Optimization recommendations
            recommendations_result = self.optimizer.generate_optimization_recommendations()
            if recommendations_result.get('success'):
                monitoring_data['optimization_recommendations'] = {
                    'total_recommendations': recommendations_result.get('total_recommendations', 0),
                    'critical_count': len([r for r in recommendations_result.get('recommendations', []) 
                                         if r.get('priority') == 'critical']),
                    'high_count': len([r for r in recommendations_result.get('recommendations', []) 
                                     if r.get('priority') == 'high'])
                }
            
        except Exception as e:
            logger.error(f"Error collecting monitoring data: {e}")
            monitoring_data['error'] = str(e)
        
        return monitoring_data
    
    def _analyze_performance_and_generate_alerts(self, monitoring_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze performance data and generate alerts."""
        alerts = []
        
        try:
            performance_metrics = monitoring_data.get('performance_metrics', {})
            
            # Connection usage alerts
            connection_usage = performance_metrics.get('connection_usage_percent', 0)
            if connection_usage >= self.thresholds['connection_usage_critical']:
                alerts.append({
                    'level': 'critical',
                    'category': 'connection_pool',
                    'title': 'Critical Connection Pool Usage',
                    'message': f'Connection usage at {connection_usage:.1f}% (threshold: {self.thresholds["connection_usage_critical"]}%)',
                    'current_value': connection_usage,
                    'threshold': self.thresholds['connection_usage_critical'],
                    'timestamp': datetime.now().isoformat()
                })
            elif connection_usage >= self.thresholds['connection_usage_warning']:
                alerts.append({
                    'level': 'warning',
                    'category': 'connection_pool',
                    'title': 'High Connection Pool Usage',
                    'message': f'Connection usage at {connection_usage:.1f}% (threshold: {self.thresholds["connection_usage_warning"]}%)',
                    'current_value': connection_usage,
                    'threshold': self.thresholds['connection_usage_warning'],
                    'timestamp': datetime.now().isoformat()
                })
            
            # Slow query ratio alerts
            slow_query_ratio = performance_metrics.get('slow_query_ratio_percent', 0)
            if slow_query_ratio >= self.thresholds['slow_query_ratio_critical']:
                alerts.append({
                    'level': 'critical',
                    'category': 'query_performance',
                    'title': 'Critical Slow Query Ratio',
                    'message': f'Slow query ratio at {slow_query_ratio:.1f}% (threshold: {self.thresholds["slow_query_ratio_critical"]}%)',
                    'current_value': slow_query_ratio,
                    'threshold': self.thresholds['slow_query_ratio_critical'],
                    'timestamp': datetime.now().isoformat()
                })
            elif slow_query_ratio >= self.thresholds['slow_query_ratio_warning']:
                alerts.append({
                    'level': 'warning',
                    'category': 'query_performance',
                    'title': 'High Slow Query Ratio',
                    'message': f'Slow query ratio at {slow_query_ratio:.1f}% (threshold: {self.thresholds["slow_query_ratio_warning"]}%)',
                    'current_value': slow_query_ratio,
                    'threshold': self.thresholds['slow_query_ratio_warning'],
                    'timestamp': datetime.now().isoformat()
                })
            
            # Average query time alerts
            avg_query_time = performance_metrics.get('avg_query_time_ms', 0)
            if avg_query_time >= self.thresholds['avg_query_time_critical']:
                alerts.append({
                    'level': 'critical',
                    'category': 'query_performance',
                    'title': 'Critical Average Query Time',
                    'message': f'Average query time at {avg_query_time:.1f}ms (threshold: {self.thresholds["avg_query_time_critical"]}ms)',
                    'current_value': avg_query_time,
                    'threshold': self.thresholds['avg_query_time_critical'],
                    'timestamp': datetime.now().isoformat()
                })
            elif avg_query_time >= self.thresholds['avg_query_time_warning']:
                alerts.append({
                    'level': 'warning',
                    'category': 'query_performance',
                    'title': 'High Average Query Time',
                    'message': f'Average query time at {avg_query_time:.1f}ms (threshold: {self.thresholds["avg_query_time_warning"]}ms)',
                    'current_value': avg_query_time,
                    'threshold': self.thresholds['avg_query_time_warning'],
                    'timestamp': datetime.now().isoformat()
                })
            
            # Buffer pool hit ratio alerts
            buffer_pool_ratio = performance_metrics.get('innodb_buffer_pool_hit_ratio', 100)
            if buffer_pool_ratio <= self.thresholds['buffer_pool_hit_ratio_critical']:
                alerts.append({
                    'level': 'critical',
                    'category': 'memory_performance',
                    'title': 'Critical Buffer Pool Hit Ratio',
                    'message': f'Buffer pool hit ratio at {buffer_pool_ratio:.1f}% (threshold: {self.thresholds["buffer_pool_hit_ratio_critical"]}%)',
                    'current_value': buffer_pool_ratio,
                    'threshold': self.thresholds['buffer_pool_hit_ratio_critical'],
                    'timestamp': datetime.now().isoformat()
                })
            elif buffer_pool_ratio <= self.thresholds['buffer_pool_hit_ratio_warning']:
                alerts.append({
                    'level': 'warning',
                    'category': 'memory_performance',
                    'title': 'Low Buffer Pool Hit Ratio',
                    'message': f'Buffer pool hit ratio at {buffer_pool_ratio:.1f}% (threshold: {self.thresholds["buffer_pool_hit_ratio_warning"]}%)',
                    'current_value': buffer_pool_ratio,
                    'threshold': self.thresholds['buffer_pool_hit_ratio_warning'],
                    'timestamp': datetime.now().isoformat()
                })
            
            # Health check alerts
            health_check = monitoring_data.get('health_check', {})
            if not health_check.get('healthy', True):
                alerts.append({
                    'level': 'critical',
                    'category': 'health',
                    'title': 'MySQL Health Check Failed',
                    'message': f'MySQL health check failed: {health_check.get("status", "unknown")}',
                    'timestamp': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error analyzing performance and generating alerts: {e}")
            alerts.append({
                'level': 'error',
                'category': 'monitoring',
                'title': 'Monitoring Error',
                'message': f'Error in performance analysis: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    def _handle_auto_optimization(self, monitoring_data: Dict[str, Any]):
        """Handle automatic optimization if enabled."""
        try:
            # Check if it's time for auto-optimization
            time_since_last = datetime.now() - self.last_optimization
            if time_since_last.total_seconds() < self.auto_optimize_interval:
                return
            
            # Check if optimization is needed based on performance metrics
            performance_metrics = monitoring_data.get('performance_metrics', {})
            optimization_needed = False
            
            # Check connection usage
            connection_usage = performance_metrics.get('connection_usage_percent', 0)
            if connection_usage >= self.thresholds['connection_usage_warning']:
                optimization_needed = True
            
            # Check slow query ratio
            slow_query_ratio = performance_metrics.get('slow_query_ratio_percent', 0)
            if slow_query_ratio >= self.thresholds['slow_query_ratio_warning']:
                optimization_needed = True
            
            if optimization_needed:
                logger.info("Auto-optimization triggered based on performance metrics")
                
                # Optimize connection pool
                pool_result = self.optimizer.optimize_connection_pool()
                if pool_result.get('success'):
                    logger.info("Connection pool auto-optimization completed")
                
                # Implement adaptive caching strategy
                cache_result = self.optimizer.implement_caching_strategy('adaptive')
                if cache_result.get('success'):
                    logger.info("Caching strategy auto-optimization completed")
                
                self.last_optimization = datetime.now()
            
        except Exception as e:
            logger.error(f"Error in auto-optimization: {e}")
    
    def _cache_monitoring_data(self, monitoring_data: Dict[str, Any], alerts: List[Dict[str, Any]]):
        """Cache monitoring data and alerts in Redis."""
        try:
            if not self.redis_client:
                return
            
            # Cache current monitoring data
            current_key = "mysql_monitoring:current"
            self.redis_client.setex(
                current_key,
                600,  # 10 minutes TTL
                json.dumps(monitoring_data, default=str)
            )
            
            # Cache alerts
            if alerts:
                alerts_key = f"mysql_monitoring:alerts:{int(time.time())}"
                self.redis_client.setex(
                    alerts_key,
                    3600,  # 1 hour TTL
                    json.dumps(alerts, default=str)
                )
            
            # Cache historical data
            history_key = f"mysql_monitoring:history:{int(time.time())}"
            self.redis_client.setex(
                history_key,
                86400,  # 24 hours TTL
                json.dumps(monitoring_data, default=str)
            )
            
        except Exception as e:
            logger.debug(f"Could not cache monitoring data: {e}")
    
    def _log_performance_summary(self, monitoring_data: Dict[str, Any], alerts: List[Dict[str, Any]]):
        """Log performance summary."""
        try:
            performance_metrics = monitoring_data.get('performance_metrics', {})
            health_check = monitoring_data.get('health_check', {})
            
            # Create summary message
            summary_parts = []
            
            if health_check.get('healthy'):
                summary_parts.append("✅ Healthy")
            else:
                summary_parts.append("❌ Unhealthy")
            
            if performance_metrics:
                conn_usage = performance_metrics.get('connection_usage_percent', 0)
                avg_query_time = performance_metrics.get('avg_query_time_ms', 0)
                slow_query_ratio = performance_metrics.get('slow_query_ratio_percent', 0)
                
                summary_parts.append(f"Conn: {conn_usage:.1f}%")
                summary_parts.append(f"AvgQuery: {avg_query_time:.1f}ms")
                summary_parts.append(f"SlowQueries: {slow_query_ratio:.1f}%")
            
            if alerts:
                critical_alerts = [a for a in alerts if a.get('level') == 'critical']
                warning_alerts = [a for a in alerts if a.get('level') == 'warning']
                
                if critical_alerts:
                    summary_parts.append(f"🚨 {len(critical_alerts)} critical")
                if warning_alerts:
                    summary_parts.append(f"⚠️ {len(warning_alerts)} warnings")
            
            summary = " | ".join(summary_parts)
            logger.info(f"MySQL Performance Summary: {summary}")
            
            # Log individual alerts
            for alert in alerts:
                level_emoji = {'critical': '🚨', 'warning': '⚠️', 'error': '❌'}
                emoji = level_emoji.get(alert.get('level', 'info'), 'ℹ️')
                logger.warning(f"{emoji} {alert.get('title', 'Alert')}: {alert.get('message', 'No message')}")
            
        except Exception as e:
            logger.error(f"Error logging performance summary: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        try:
            status = {
                'monitoring_enabled': self.monitoring_enabled,
                'monitoring_interval': self.monitoring_interval,
                'auto_optimize_enabled': self.auto_optimize_enabled,
                'auto_optimize_interval': self.auto_optimize_interval,
                'last_optimization': self.last_optimization.isoformat() if self.last_optimization != datetime.min else None,
                'thresholds': self.thresholds,
                'optimizer_status': {
                    'monitoring_active': self.optimizer.monitoring_active,
                    'cached_queries': len(self.optimizer.query_performance_data),
                    'performance_history_count': len(self.optimizer.performance_history),
                    'optimized_engines': len(self.optimizer.optimized_engines)
                },
                'redis_available': self.redis_client is not None,
                'timestamp': datetime.now().isoformat()
            }
            
            return {
                'success': True,
                'status': status
            }
            
        except Exception as e:
            logger.error(f"Failed to get monitoring status: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_recent_alerts(self, hours: int = 24) -> Dict[str, Any]:
        """Get recent alerts from Redis cache."""
        try:
            if not self.redis_client:
                return {
                    'success': False,
                    'message': 'Redis not available for alert retrieval',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Get alert keys from the last N hours
            cutoff_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())
            pattern = "mysql_monitoring:alerts:*"
            keys = self.redis_client.keys(pattern)
            
            # Filter keys by timestamp
            recent_keys = [key for key in keys if int(key.split(':')[-1]) >= cutoff_timestamp]
            
            # Retrieve alerts
            all_alerts = []
            for key in recent_keys:
                try:
                    alerts_data = self.redis_client.get(key)
                    if alerts_data:
                        alerts = json.loads(alerts_data)
                        all_alerts.extend(alerts)
                except Exception as e:
                    logger.debug(f"Could not parse alerts from {key}: {e}")
            
            # Sort alerts by timestamp
            all_alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Categorize alerts
            alert_summary = {
                'critical': [a for a in all_alerts if a.get('level') == 'critical'],
                'warning': [a for a in all_alerts if a.get('level') == 'warning'],
                'error': [a for a in all_alerts if a.get('level') == 'error']
            }
            
            return {
                'success': True,
                'time_range_hours': hours,
                'total_alerts': len(all_alerts),
                'alert_counts': {
                    'critical': len(alert_summary['critical']),
                    'warning': len(alert_summary['warning']),
                    'error': len(alert_summary['error'])
                },
                'alerts': all_alerts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def cleanup_resources(self):
        """Clean up resources."""
        try:
            # Stop monitoring
            self.stop_monitoring()
            
            # Clean up optimizer
            self.optimizer.cleanup_resources()
            
            # Close Redis connection
            if self.redis_client:
                try:
                    self.redis_client.close()
                except:
                    pass
            
            logger.info("MySQL Performance Monitor resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")


def main():
    """Command-line interface for MySQL Performance Monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MySQL Performance Monitor for Vedfolnir')
    parser.add_argument('--action', choices=[
        'start', 'stop', 'status', 'alerts', 'optimize-now'
    ], required=True, help='Action to perform')
    
    parser.add_argument('--monitoring-interval', type=int, default=300,
                       help='Monitoring interval in seconds (default: 300)')
    parser.add_argument('--auto-optimize', action='store_true',
                       help='Enable auto-optimization')
    parser.add_argument('--alert-hours', type=int, default=24,
                       help='Hours of alerts to retrieve (default: 24)')
    parser.add_argument('--output-format', choices=['json', 'table'], default='table',
                       help='Output format (default: table)')
    
    args = parser.parse_args()
    
    # Initialize monitor
    try:
        monitor = MySQLPerformanceMonitor()
        
        if args.action == 'start':
            # Set monitoring interval
            monitor.monitoring_interval = args.monitoring_interval
            monitor.auto_optimize_enabled = args.auto_optimize
            
            result = monitor.start_monitoring()
            print_result(result, args.output_format)
            
            if result.get('success'):
                print("Monitoring started. Press Ctrl+C to stop...")
                try:
                    while monitor.monitoring_enabled:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nStopping monitoring...")
                    monitor.stop_monitoring()
            
        elif args.action == 'stop':
            result = monitor.stop_monitoring()
            print_result(result, args.output_format)
            
        elif args.action == 'status':
            result = monitor.get_monitoring_status()
            print_result(result, args.output_format)
            
        elif args.action == 'alerts':
            result = monitor.get_recent_alerts(args.alert_hours)
            print_result(result, args.output_format)
            
        elif args.action == 'optimize-now':
            # Force immediate optimization
            print("Running immediate optimization...")
            
            # Connection pool optimization
            pool_result = monitor.optimizer.optimize_connection_pool()
            print_result(pool_result, args.output_format)
            
            # Caching strategy
            cache_result = monitor.optimizer.implement_caching_strategy('adaptive')
            print_result(cache_result, args.output_format)
        
        # Cleanup
        monitor.cleanup_resources()
        
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
        print(f"MySQL Performance Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if result.get('success'):
            print("✅ Operation completed successfully")
            
            # Print status information
            if 'status' in result:
                status = result['status']
                print(f"\n📊 Monitoring Status:")
                print(f"  Enabled: {'✅' if status.get('monitoring_enabled') else '❌'}")
                print(f"  Interval: {status.get('monitoring_interval')}s")
                print(f"  Auto-optimize: {'✅' if status.get('auto_optimize_enabled') else '❌'}")
                print(f"  Redis: {'✅' if status.get('redis_available') else '❌'}")
            
            # Print alerts
            if 'alerts' in result:
                alerts = result['alerts']
                alert_counts = result.get('alert_counts', {})
                
                print(f"\n🚨 Recent Alerts ({result.get('total_alerts', 0)} total):")
                print(f"  Critical: {alert_counts.get('critical', 0)}")
                print(f"  Warning: {alert_counts.get('warning', 0)}")
                print(f"  Error: {alert_counts.get('error', 0)}")
                
                # Show recent alerts
                recent_alerts = alerts[:5]  # Show last 5 alerts
                for alert in recent_alerts:
                    level_emoji = {'critical': '🚨', 'warning': '⚠️', 'error': '❌'}
                    emoji = level_emoji.get(alert.get('level', 'info'), 'ℹ️')
                    print(f"  {emoji} {alert.get('title', 'Alert')}: {alert.get('message', 'No message')}")
        
        else:
            print("❌ Operation failed")
            if 'error' in result:
                print(f"Error: {result['error']}")
        
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
