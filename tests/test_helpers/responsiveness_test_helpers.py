# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Responsiveness Testing Helpers

Utilities and helpers for testing responsiveness monitoring features,
including mock configurations, test data factories, and performance testing utilities.
"""

import time
import threading
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass


@dataclass
class ResponsivenessTestConfig:
    """Configuration for responsiveness testing"""
    memory_warning_threshold: float = 0.8
    memory_critical_threshold: float = 0.9
    cpu_warning_threshold: float = 0.8
    cpu_critical_threshold: float = 0.9
    connection_pool_warning_threshold: float = 0.9
    monitoring_interval: int = 30
    cleanup_enabled: bool = True
    test_duration_seconds: int = 60
    concurrent_users: int = 10


class ResponsivenessTestDataFactory:
    """Factory for creating test data for responsiveness testing"""
    
    @staticmethod
    def create_healthy_system_metrics() -> Dict[str, Any]:
        """Create healthy system metrics for testing"""
        return {
            'memory_usage_percent': 45.2,
            'memory_usage_mb': 512.5,
            'cpu_usage_percent': 25.8,
            'connection_pool_utilization': 0.65,
            'active_connections': 13,
            'max_connections': 20,
            'background_tasks_count': 8,
            'blocked_requests': 0,
            'avg_request_time': 0.85,
            'slow_request_count': 2,
            'total_requests': 1250,
            'requests_per_second': 12.5,
            'responsiveness_status': 'healthy',
            'cleanup_triggered': False,
            'last_cleanup_time': time.time() - 300,
            'recent_slow_requests': []
        }
    
    @staticmethod
    def create_warning_system_metrics() -> Dict[str, Any]:
        """Create warning-level system metrics for testing"""
        return {
            'memory_usage_percent': 82.5,
            'memory_usage_mb': 1638.4,
            'cpu_usage_percent': 75.2,
            'connection_pool_utilization': 0.88,
            'active_connections': 18,
            'max_connections': 20,
            'background_tasks_count': 15,
            'blocked_requests': 3,
            'avg_request_time': 2.1,
            'slow_request_count': 8,
            'total_requests': 2100,
            'requests_per_second': 8.3,
            'responsiveness_status': 'warning',
            'cleanup_triggered': False,
            'last_cleanup_time': time.time() - 600,
            'recent_slow_requests': [
                {
                    'endpoint': '/admin/dashboard',
                    'method': 'GET',
                    'time': 3.2,
                    'timestamp': time.time() - 60,
                    'status_code': 200
                }
            ]
        }
    
    @staticmethod
    def create_critical_system_metrics() -> Dict[str, Any]:
        """Create critical-level system metrics for testing"""
        return {
            'memory_usage_percent': 94.8,
            'memory_usage_mb': 1945.6,
            'cpu_usage_percent': 92.1,
            'connection_pool_utilization': 0.98,
            'active_connections': 20,
            'max_connections': 20,
            'background_tasks_count': 25,
            'blocked_requests': 12,
            'avg_request_time': 8.5,
            'slow_request_count': 25,
            'total_requests': 1800,
            'requests_per_second': 3.2,
            'responsiveness_status': 'critical',
            'cleanup_triggered': True,
            'last_cleanup_time': time.time() - 60,
            'recent_slow_requests': [
                {
                    'endpoint': '/admin/performance',
                    'method': 'GET',
                    'time': 12.8,
                    'timestamp': time.time() - 30,
                    'status_code': 200
                },
                {
                    'endpoint': '/api/responsiveness/check',
                    'method': 'GET',
                    'time': 15.2,
                    'timestamp': time.time() - 45,
                    'status_code': 200
                }
            ]
        }
    
    @staticmethod
    def create_responsiveness_check_result(status: str = 'healthy') -> Dict[str, Any]:
        """Create responsiveness check result for testing"""
        base_result = {
            'responsive': status == 'healthy',
            'overall_status': status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'performance_score': 85.5 if status == 'healthy' else 45.2 if status == 'warning' else 15.8,
            'issues': [],
            'recommendations': []
        }
        
        if status == 'warning':
            base_result['issues'] = [
                {
                    'type': 'memory',
                    'severity': 'warning',
                    'current': '82.5%',
                    'threshold': '80.0%',
                    'message': 'Memory usage elevated - monitor closely'
                }
            ]
            base_result['recommendations'] = [
                'Consider running memory cleanup',
                'Monitor memory usage trends'
            ]
        elif status == 'critical':
            base_result['issues'] = [
                {
                    'type': 'memory',
                    'severity': 'critical',
                    'current': '94.8%',
                    'threshold': '90.0%',
                    'message': 'Memory usage critical - immediate action required'
                },
                {
                    'type': 'connection_pool',
                    'severity': 'critical',
                    'current': '98.0%',
                    'threshold': '90.0%',
                    'message': 'Connection pool utilization critical'
                }
            ]
            base_result['recommendations'] = [
                'Execute emergency memory cleanup immediately',
                'Optimize database connection usage',
                'Consider enabling maintenance mode'
            ]
        
        return base_result
    
    @staticmethod
    def create_cleanup_stats(operations_count: int = 10) -> Dict[str, Any]:
        """Create cleanup statistics for testing"""
        return {
            'summary': {
                'total_operations': operations_count,
                'successful_operations': max(1, operations_count - 2),
                'failed_operations': min(2, operations_count),
                'total_items_cleaned': operations_count * 50,
                'avg_cleanup_time': 2.5,
                'last_cleanup_time': datetime.now(timezone.utc).isoformat()
            },
            'recent_operations': [
                {
                    'type': 'audit_logs',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'items_cleaned': 100,
                    'duration': 2.5,
                    'success': True
                },
                {
                    'type': 'expired_sessions',
                    'timestamp': (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
                    'items_cleaned': 25,
                    'duration': 1.2,
                    'success': True
                }
            ],
            'responsiveness_metrics': {
                'avg_cleanup_duration': 2.1,
                'cleanup_success_rate': 0.8,
                'cleanup_frequency': 0.5,  # per hour
                'system_impact_score': 0.3,  # low impact
                'blocking_operations': 0
            }
        }
    
    @staticmethod
    def create_session_metrics(active_sessions: int = 45) -> Dict[str, Any]:
        """Create session metrics for testing"""
        return {
            'active_sessions': active_sessions,
            'total_sessions_today': active_sessions * 4,
            'avg_session_duration': 1800,  # 30 minutes
            'memory_per_session_mb': 2.8,
            'session_creation_rate': 0.5,  # per second
            'expired_sessions_cleaned': max(1, active_sessions // 10),
            'memory_leak_indicators': [],
            'session_health_score': 85.0,
            'cleanup_recommendations': []
        }


class ResponsivenessMockFactory:
    """Factory for creating mocks for responsiveness testing"""
    
    @staticmethod
    def create_system_optimizer_mock(status: str = 'healthy') -> Mock:
        """Create SystemOptimizer mock for testing"""
        mock_optimizer = Mock()
        
        # Configure performance metrics
        if status == 'healthy':
            mock_optimizer.get_performance_metrics.return_value = ResponsivenessTestDataFactory.create_healthy_system_metrics()
        elif status == 'warning':
            mock_optimizer.get_performance_metrics.return_value = ResponsivenessTestDataFactory.create_warning_system_metrics()
        else:  # critical
            mock_optimizer.get_performance_metrics.return_value = ResponsivenessTestDataFactory.create_critical_system_metrics()
        
        # Configure responsiveness check
        mock_optimizer.check_responsiveness.return_value = ResponsivenessTestDataFactory.create_responsiveness_check_result(status)
        
        # Configure cleanup trigger
        mock_optimizer.trigger_cleanup_if_needed.return_value = status != 'healthy'
        
        # Configure additional methods
        mock_optimizer.get_recommendations.return_value = [
            {'id': 1, 'message': 'System running normally', 'priority': 'low'}
        ] if status == 'healthy' else [
            {'id': 2, 'message': 'Consider memory cleanup', 'priority': 'high'}
        ]
        
        mock_optimizer.get_health_status.return_value = {
            'status': status,
            'components': {
                'memory': status,
                'cpu': status,
                'connection_pool': status,
                'background_tasks': status
            },
            'responsiveness_monitoring': True,
            'thresholds': {
                'memory_warning': 0.8,
                'memory_critical': 0.9,
                'cpu_warning': 0.8,
                'cpu_critical': 0.9
            }
        }
        
        return mock_optimizer
    
    @staticmethod
    def create_cleanup_manager_mock(operations_count: int = 10) -> Mock:
        """Create BackgroundCleanupManager mock for testing"""
        mock_cleanup = Mock()
        
        # Configure cleanup stats
        mock_cleanup.get_cleanup_stats.return_value = ResponsivenessTestDataFactory.create_cleanup_stats(operations_count)
        
        # Configure cleanup operations
        mock_cleanup.run_manual_cleanup.return_value = {
            'success': True,
            'cleanup_type': 'audit_logs',
            'items_cleaned': 50,
            'execution_time_seconds': 2.5,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Configure task coordination
        mock_cleanup.coordinate_cleanup_tasks.return_value = {
            'tasks_coordinated': 4,
            'execution_order': ['audit_logs', 'expired_sessions', 'cache_cleanup', 'temp_files'],
            'estimated_total_duration': 120,
            'parallel_execution_possible': True,
            'coordination_time': 0.5
        }
        
        # Configure health monitoring
        mock_cleanup.monitor_task_health.return_value = {
            'overall_health': 'healthy',
            'active_threads': 3,
            'failed_threads': 0,
            'cleanup_performance': {
                'avg_duration': 2.1,
                'success_rate': 0.9
            },
            'recommendations': []
        }
        
        return mock_cleanup
    
    @staticmethod
    def create_session_monitor_mock(active_sessions: int = 45) -> Mock:
        """Create SessionMonitor mock for testing"""
        mock_session = Mock()
        
        # Configure session metrics
        mock_session.get_session_metrics.return_value = ResponsivenessTestDataFactory.create_session_metrics(active_sessions)
        
        # Configure memory leak detection
        mock_session.detect_memory_leaks.return_value = {
            'leaks_detected': [],
            'total_sessions_analyzed': active_sessions,
            'memory_usage_analysis': {
                'avg_memory_per_session': 2.8,
                'high_memory_sessions': 0,
                'memory_trend': 'stable'
            },
            'cleanup_recommendations': []
        }
        
        # Configure cleanup operations
        mock_session.cleanup_expired_sessions.return_value = {
            'sessions_cleaned': max(1, active_sessions // 10),
            'memory_freed_mb': 15.5,
            'cleanup_duration': 1.2,
            'success': True
        }
        
        # Configure performance integration
        mock_session.get_integrated_performance_metrics.return_value = {
            'session_performance': {
                'avg_session_creation_time': 0.15,
                'avg_session_lookup_time': 0.05,
                'session_cache_hit_rate': 0.85
            },
            'memory_monitoring': {
                'memory_per_session_mb': 2.8,
                'total_session_memory_mb': active_sessions * 2.8,
                'memory_efficiency_score': 85.0
            },
            'responsiveness_indicators': {
                'session_responsiveness_score': 88.5,
                'memory_efficiency_score': 85.0,
                'overall_health_status': 'healthy'
            }
        }
        
        return mock_session
    
    @staticmethod
    def create_database_manager_mock() -> Mock:
        """Create DatabaseManager mock for responsiveness testing"""
        mock_db = Mock()
        
        # Configure MySQL performance stats with responsiveness metrics
        mock_db.get_mysql_performance_stats.return_value = {
            'connection_stats': {
                'active_connections': 15,
                'max_connections': 100,
                'connection_utilization': 0.15
            },
            'query_stats': {
                'slow_queries': 3,
                'total_queries': 5000,
                'queries_per_second': 25.5
            },
            'responsiveness_metrics': {
                'connection_pool_utilization': 0.75,
                'connection_pool_health': {
                    'status': 'healthy',
                    'utilization_level': 'normal',
                    'issues': []
                },
                'long_running_queries': [],
                'idle_connections': [],
                'connection_errors': 0,
                'response_time_ms': 15.5,
                'connection_leak_risk': 'low'
            }
        }
        
        # Configure connection health monitoring
        mock_db.monitor_connection_health.return_value = {
            'overall_health': 'healthy',
            'connection_pool': {
                'status': 'healthy',
                'utilization': 0.75,
                'size': 20,
                'checked_out': 15,
                'overflow': 0,
                'invalid': 0
            },
            'utilization': 0.75,
            'issues': [],
            'recommendations': []
        }
        
        # Configure connection leak detection
        mock_db.detect_and_cleanup_connection_leaks.return_value = {
            'total_sessions': 20,
            'leaked_sessions': 0,
            'cleaned_sessions': 0,
            'leak_threshold_hours': 1,
            'cleanup_successful': True
        }
        
        return mock_db


class ResponsivenessPerformanceTester:
    """Utility for performance testing responsiveness features"""
    
    def __init__(self, config: ResponsivenessTestConfig = None):
        self.config = config or ResponsivenessTestConfig()
        self.results = []
    
    def run_performance_test(self, test_function: Callable, iterations: int = 100) -> Dict[str, Any]:
        """Run performance test for a function"""
        execution_times = []
        errors = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                result = test_function()
                execution_time = time.time() - start_time
                execution_times.append(execution_time)
            except Exception as e:
                errors.append(str(e))
        
        if execution_times:
            performance_result = {
                'iterations': iterations,
                'successful_iterations': len(execution_times),
                'failed_iterations': len(errors),
                'avg_execution_time': sum(execution_times) / len(execution_times),
                'min_execution_time': min(execution_times),
                'max_execution_time': max(execution_times),
                'total_execution_time': sum(execution_times),
                'errors': errors
            }
        else:
            performance_result = {
                'iterations': iterations,
                'successful_iterations': 0,
                'failed_iterations': len(errors),
                'errors': errors
            }
        
        self.results.append(performance_result)
        return performance_result
    
    def run_concurrent_test(self, test_function: Callable, concurrent_users: int = None) -> Dict[str, Any]:
        """Run concurrent performance test"""
        concurrent_users = concurrent_users or self.config.concurrent_users
        results = []
        errors = []
        
        def worker_thread(worker_id):
            """Worker thread for concurrent testing"""
            try:
                start_time = time.time()
                result = test_function()
                execution_time = time.time() - start_time
                
                results.append({
                    'worker_id': worker_id,
                    'execution_time': execution_time,
                    'result': result
                })
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
        
        # Start concurrent workers
        threads = []
        for i in range(concurrent_users):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze concurrent results
        if results:
            execution_times = [r['execution_time'] for r in results]
            concurrent_result = {
                'concurrent_users': concurrent_users,
                'successful_operations': len(results),
                'failed_operations': len(errors),
                'avg_execution_time': sum(execution_times) / len(execution_times),
                'min_execution_time': min(execution_times),
                'max_execution_time': max(execution_times),
                'total_execution_time': sum(execution_times),
                'throughput_ops_per_second': len(results) / max(execution_times) if execution_times else 0,
                'errors': errors
            }
        else:
            concurrent_result = {
                'concurrent_users': concurrent_users,
                'successful_operations': 0,
                'failed_operations': len(errors),
                'errors': errors
            }
        
        self.results.append(concurrent_result)
        return concurrent_result
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all performance test results"""
        if not self.results:
            return {'message': 'No performance tests run'}
        
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r.get('successful_iterations', 0) > 0 or r.get('successful_operations', 0) > 0])
        
        avg_execution_times = []
        for result in self.results:
            if 'avg_execution_time' in result:
                avg_execution_times.append(result['avg_execution_time'])
        
        summary = {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'test_success_rate': successful_tests / total_tests if total_tests > 0 else 0,
            'overall_avg_execution_time': sum(avg_execution_times) / len(avg_execution_times) if avg_execution_times else 0,
            'test_results': self.results
        }
        
        return summary


class ResponsivenessTestValidator:
    """Validator for responsiveness test results"""
    
    @staticmethod
    def validate_system_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Validate system metrics structure and values"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Required fields
        required_fields = [
            'memory_usage_percent',
            'cpu_usage_percent',
            'connection_pool_utilization',
            'responsiveness_status'
        ]
        
        for field in required_fields:
            if field not in metrics:
                validation_result['errors'].append(f"Missing required field: {field}")
                validation_result['valid'] = False
        
        # Value range validation
        if 'memory_usage_percent' in metrics:
            memory_percent = metrics['memory_usage_percent']
            if not (0 <= memory_percent <= 100):
                validation_result['errors'].append(f"Invalid memory_usage_percent: {memory_percent}")
                validation_result['valid'] = False
            elif memory_percent > 90:
                validation_result['warnings'].append(f"High memory usage: {memory_percent}%")
        
        if 'cpu_usage_percent' in metrics:
            cpu_percent = metrics['cpu_usage_percent']
            if not (0 <= cpu_percent <= 100):
                validation_result['errors'].append(f"Invalid cpu_usage_percent: {cpu_percent}")
                validation_result['valid'] = False
            elif cpu_percent > 90:
                validation_result['warnings'].append(f"High CPU usage: {cpu_percent}%")
        
        if 'connection_pool_utilization' in metrics:
            pool_util = metrics['connection_pool_utilization']
            if not (0 <= pool_util <= 1):
                validation_result['errors'].append(f"Invalid connection_pool_utilization: {pool_util}")
                validation_result['valid'] = False
            elif pool_util > 0.9:
                validation_result['warnings'].append(f"High connection pool utilization: {pool_util:.1%}")
        
        # Status validation
        if 'responsiveness_status' in metrics:
            status = metrics['responsiveness_status']
            valid_statuses = ['healthy', 'warning', 'critical']
            if status not in valid_statuses:
                validation_result['errors'].append(f"Invalid responsiveness_status: {status}")
                validation_result['valid'] = False
        
        return validation_result
    
    @staticmethod
    def validate_responsiveness_check(check_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate responsiveness check result structure"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Required fields
        required_fields = ['responsive', 'overall_status', 'timestamp', 'issues']
        
        for field in required_fields:
            if field not in check_result:
                validation_result['errors'].append(f"Missing required field: {field}")
                validation_result['valid'] = False
        
        # Type validation
        if 'responsive' in check_result and not isinstance(check_result['responsive'], bool):
            validation_result['errors'].append("Field 'responsive' must be boolean")
            validation_result['valid'] = False
        
        if 'issues' in check_result and not isinstance(check_result['issues'], list):
            validation_result['errors'].append("Field 'issues' must be list")
            validation_result['valid'] = False
        
        # Consistency validation
        if 'responsive' in check_result and 'overall_status' in check_result:
            responsive = check_result['responsive']
            status = check_result['overall_status']
            
            if responsive and status != 'healthy':
                validation_result['warnings'].append(f"Inconsistent: responsive=True but status='{status}'")
            elif not responsive and status == 'healthy':
                validation_result['warnings'].append(f"Inconsistent: responsive=False but status='healthy'")
        
        return validation_result
    
    @staticmethod
    def validate_performance_result(performance_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate performance test result"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Required fields
        required_fields = ['iterations', 'successful_iterations', 'avg_execution_time']
        
        for field in required_fields:
            if field not in performance_result:
                validation_result['errors'].append(f"Missing required field: {field}")
                validation_result['valid'] = False
        
        # Performance thresholds
        if 'avg_execution_time' in performance_result:
            avg_time = performance_result['avg_execution_time']
            if avg_time > 1.0:  # 1 second threshold
                validation_result['warnings'].append(f"Slow average execution time: {avg_time:.3f}s")
            elif avg_time > 5.0:  # 5 second critical threshold
                validation_result['errors'].append(f"Critical execution time: {avg_time:.3f}s")
                validation_result['valid'] = False
        
        # Success rate validation
        if 'successful_iterations' in performance_result and 'iterations' in performance_result:
            success_rate = performance_result['successful_iterations'] / performance_result['iterations']
            if success_rate < 0.9:  # 90% success rate threshold
                validation_result['warnings'].append(f"Low success rate: {success_rate:.1%}")
            elif success_rate < 0.5:  # 50% critical threshold
                validation_result['errors'].append(f"Critical success rate: {success_rate:.1%}")
                validation_result['valid'] = False
        
        return validation_result


# Convenience functions for common test scenarios
def create_responsiveness_test_suite(status: str = 'healthy') -> Dict[str, Mock]:
    """Create complete responsiveness test suite with mocks"""
    return {
        'system_optimizer': ResponsivenessMockFactory.create_system_optimizer_mock(status),
        'cleanup_manager': ResponsivenessMockFactory.create_cleanup_manager_mock(),
        'session_monitor': ResponsivenessMockFactory.create_session_monitor_mock(),
        'database_manager': ResponsivenessMockFactory.create_database_manager_mock()
    }


def patch_responsiveness_components(status: str = 'healthy'):
    """Context manager for patching responsiveness components"""
    test_suite = create_responsiveness_test_suite(status)
    
    return patch.multiple(
        'web_app',
        system_optimizer=test_suite['system_optimizer'],
        cleanup_manager=test_suite['cleanup_manager'],
        session_monitor=test_suite['session_monitor'],
        db_manager=test_suite['database_manager']
    )


def run_responsiveness_performance_test(test_function: Callable, config: ResponsivenessTestConfig = None) -> Dict[str, Any]:
    """Run a complete responsiveness performance test"""
    tester = ResponsivenessPerformanceTester(config)
    
    # Run sequential performance test
    sequential_result = tester.run_performance_test(test_function, iterations=50)
    
    # Run concurrent performance test
    concurrent_result = tester.run_concurrent_test(test_function, concurrent_users=10)
    
    # Get performance summary
    summary = tester.get_performance_summary()
    
    return {
        'sequential_performance': sequential_result,
        'concurrent_performance': concurrent_result,
        'performance_summary': summary
    }