# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from session_performance_monitor import SessionPerformanceMonitor, SessionMetrics, RequestMetrics
from session_performance_monitor import get_performance_monitor, initialize_performance_monitoring

class TestSessionMetrics(unittest.TestCase):
    """Test SessionMetrics dataclass"""
    
    def test_session_metrics_initialization(self):
        """Test SessionMetrics initializes with correct defaults"""
        metrics = SessionMetrics()
        
        self.assertEqual(metrics.session_creations, 0)
        self.assertEqual(metrics.session_closures, 0)
        self.assertEqual(metrics.session_rollbacks, 0)
        self.assertEqual(metrics.session_commits, 0)
        self.assertEqual(metrics.detached_instance_recoveries, 0)
        self.assertEqual(metrics.session_reattachments, 0)
        self.assertEqual(metrics.active_sessions, 0)
        self.assertEqual(metrics.peak_active_sessions, 0)
        self.assertEqual(metrics.total_session_duration, 0.0)
        self.assertEqual(metrics.average_session_duration, 0.0)
        self.assertEqual(metrics.session_errors, 0)
        
        # Check deques are initialized
        self.assertEqual(len(metrics.session_creation_times), 0)
        self.assertEqual(len(metrics.session_cleanup_times), 0)
        self.assertEqual(len(metrics.recovery_times), 0)

class TestRequestMetrics(unittest.TestCase):
    """Test RequestMetrics dataclass"""
    
    def test_request_metrics_initialization(self):
        """Test RequestMetrics initializes correctly"""
        request_id = "test_request_123"
        endpoint = "test_endpoint"
        start_time = time.time()
        
        metrics = RequestMetrics(
            request_id=request_id,
            endpoint=endpoint,
            start_time=start_time
        )
        
        self.assertEqual(metrics.request_id, request_id)
        self.assertEqual(metrics.endpoint, endpoint)
        self.assertEqual(metrics.start_time, start_time)
        self.assertIsNone(metrics.end_time)
        self.assertEqual(len(metrics.session_operations), 0)
        self.assertEqual(metrics.detached_instance_errors, 0)
        self.assertEqual(metrics.recovery_attempts, 0)
        self.assertEqual(metrics.successful_recoveries, 0)
        self.assertEqual(metrics.database_queries, 0)
        self.assertEqual(metrics.session_duration, 0.0)

class TestSessionPerformanceMonitor(unittest.TestCase):
    """Test SessionPerformanceMonitor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = SessionPerformanceMonitor("test_monitor")
    
    def test_monitor_initialization(self):
        """Test monitor initializes correctly"""
        self.assertIsNotNone(self.monitor.logger)
        self.assertIsInstance(self.monitor.metrics, SessionMetrics)
        self.assertEqual(len(self.monitor.request_metrics), 0)
        self.assertIsNotNone(self.monitor.lock)
        self.assertEqual(self.monitor.slow_session_threshold, 1.0)
        self.assertEqual(self.monitor.high_recovery_rate_threshold, 0.1)
        self.assertEqual(self.monitor.max_active_sessions_threshold, 50)
    
    @patch('session_performance_monitor.has_request_context')
    @patch('session_performance_monitor.request')
    @patch('session_performance_monitor.g')
    def test_start_request_monitoring(self, mock_g, mock_request, mock_has_context):
        """Test starting request monitoring"""
        mock_has_context.return_value = True
        mock_request.endpoint = 'test_endpoint'
        
        request_id = self.monitor.start_request_monitoring('test_endpoint')
        
        self.assertIn(request_id, self.monitor.request_metrics)
        self.assertEqual(self.monitor.request_metrics[request_id].endpoint, 'test_endpoint')
        self.assertEqual(mock_g.performance_request_id, request_id)
    
    @patch('session_performance_monitor.has_request_context')
    def test_start_request_monitoring_no_context(self, mock_has_context):
        """Test starting request monitoring without request context"""
        mock_has_context.return_value = False
        
        request_id = self.monitor.start_request_monitoring('test_endpoint')
        
        self.assertEqual(request_id, "no-request-context")
        self.assertEqual(len(self.monitor.request_metrics), 0)
    
    def test_record_session_creation(self):
        """Test recording session creation"""
        initial_count = self.monitor.metrics.session_creations
        initial_active = self.monitor.metrics.active_sessions
        
        self.monitor.record_session_creation(0.5)
        
        self.assertEqual(self.monitor.metrics.session_creations, initial_count + 1)
        self.assertEqual(self.monitor.metrics.active_sessions, initial_active + 1)
        self.assertEqual(len(self.monitor.metrics.session_creation_times), 1)
        self.assertEqual(self.monitor.metrics.session_creation_times[0], 0.5)
    
    def test_record_session_creation_updates_peak(self):
        """Test that session creation updates peak active sessions"""
        # Create multiple sessions to test peak tracking
        for i in range(5):
            self.monitor.record_session_creation()
        
        self.assertEqual(self.monitor.metrics.active_sessions, 5)
        self.assertEqual(self.monitor.metrics.peak_active_sessions, 5)
        
        # Close some sessions
        for i in range(2):
            self.monitor.record_session_closure()
        
        self.assertEqual(self.monitor.metrics.active_sessions, 3)
        self.assertEqual(self.monitor.metrics.peak_active_sessions, 5)  # Peak should remain
    
    def test_record_session_closure(self):
        """Test recording session closure"""
        # First create a session
        self.monitor.record_session_creation()
        
        initial_closures = self.monitor.metrics.session_closures
        initial_active = self.monitor.metrics.active_sessions
        
        self.monitor.record_session_closure(0.3)
        
        self.assertEqual(self.monitor.metrics.session_closures, initial_closures + 1)
        self.assertEqual(self.monitor.metrics.active_sessions, initial_active - 1)
        self.assertEqual(len(self.monitor.metrics.session_cleanup_times), 1)
        self.assertEqual(self.monitor.metrics.session_cleanup_times[0], 0.3)
    
    def test_record_session_commit(self):
        """Test recording session commit"""
        initial_commits = self.monitor.metrics.session_commits
        
        self.monitor.record_session_commit()
        
        self.assertEqual(self.monitor.metrics.session_commits, initial_commits + 1)
    
    def test_record_session_rollback(self):
        """Test recording session rollback"""
        initial_rollbacks = self.monitor.metrics.session_rollbacks
        
        self.monitor.record_session_rollback()
        
        self.assertEqual(self.monitor.metrics.session_rollbacks, initial_rollbacks + 1)
    
    def test_record_detached_instance_recovery(self):
        """Test recording detached instance recovery"""
        initial_recoveries = self.monitor.metrics.detached_instance_recoveries
        
        self.monitor.record_detached_instance_recovery("User", 0.2, True)
        
        self.assertEqual(self.monitor.metrics.detached_instance_recoveries, initial_recoveries + 1)
        self.assertEqual(len(self.monitor.metrics.recovery_times), 1)
        self.assertEqual(self.monitor.metrics.recovery_times[0], 0.2)
    
    @patch('session_performance_monitor.g')
    def test_record_detached_instance_recovery_with_request(self, mock_g):
        """Test recording recovery with active request"""
        # Set up request metrics
        request_id = "test_request"
        mock_g.performance_request_id = request_id
        self.monitor.request_metrics[request_id] = RequestMetrics(
            request_id=request_id,
            endpoint="test",
            start_time=time.time()
        )
        
        self.monitor.record_detached_instance_recovery("User", 0.2, True)
        
        request_metric = self.monitor.request_metrics[request_id]
        self.assertEqual(request_metric.recovery_attempts, 1)
        self.assertEqual(request_metric.successful_recoveries, 1)
    
    def test_record_session_reattachment(self):
        """Test recording session reattachment"""
        initial_reattachments = self.monitor.metrics.session_reattachments
        
        self.monitor.record_session_reattachment("PlatformConnection")
        
        self.assertEqual(self.monitor.metrics.session_reattachments, initial_reattachments + 1)
    
    def test_record_session_error(self):
        """Test recording session error"""
        initial_errors = self.monitor.metrics.session_errors
        
        self.monitor.record_session_error("connection_failed", "Database connection failed")
        
        self.assertEqual(self.monitor.metrics.session_errors, initial_errors + 1)
    
    def test_update_pool_metrics(self):
        """Test updating pool metrics"""
        # Mock engine with pool
        mock_engine = Mock()
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 2
        mock_pool.checkedin.return_value = 7
        mock_engine.pool = mock_pool
        
        self.monitor.update_pool_metrics(mock_engine)
        
        self.assertEqual(self.monitor.metrics.pool_size, 10)
        self.assertEqual(self.monitor.metrics.pool_checked_out, 3)
        self.assertEqual(self.monitor.metrics.pool_overflow, 2)
        self.assertEqual(self.monitor.metrics.pool_checked_in, 7)
    
    def test_update_pool_metrics_no_pool(self):
        """Test updating pool metrics with engine that has no pool"""
        mock_engine = Mock()
        del mock_engine.pool  # Remove pool attribute
        
        # Should not raise an exception
        self.monitor.update_pool_metrics(mock_engine)
        
        # Metrics should remain at defaults
        self.assertEqual(self.monitor.metrics.pool_size, 0)
    
    def test_time_operation_context_manager(self):
        """Test timing operation context manager"""
        with self.monitor.time_operation("test_operation"):
            time.sleep(0.1)  # Small delay for timing
        
        # Should complete without error
        # Actual timing verification would require more complex mocking
    
    def test_get_current_metrics(self):
        """Test getting current metrics"""
        # Add some test data
        self.monitor.record_session_creation(0.5)
        self.monitor.record_session_commit()
        self.monitor.record_detached_instance_recovery("User", 0.2, True)
        
        metrics = self.monitor.get_current_metrics()
        
        self.assertIn('timestamp', metrics)
        self.assertIn('session_metrics', metrics)
        self.assertIn('recovery_metrics', metrics)
        self.assertIn('performance_metrics', metrics)
        self.assertIn('pool_metrics', metrics)
        self.assertIn('active_requests', metrics)
        
        # Check specific values
        self.assertEqual(metrics['session_metrics']['creations'], 1)
        self.assertEqual(metrics['session_metrics']['commits'], 1)
        self.assertEqual(metrics['recovery_metrics']['detached_instance_recoveries'], 1)
    
    def test_get_performance_summary(self):
        """Test getting performance summary"""
        # Add some test data
        self.monitor.record_session_creation(0.5)
        self.monitor.record_session_closure(0.3)
        self.monitor.record_detached_instance_recovery("User", 0.2, True)
        
        summary = self.monitor.get_performance_summary()
        
        self.assertIsInstance(summary, str)
        self.assertIn("Session Performance Summary", summary)
        self.assertIn("Recovery Metrics", summary)
        self.assertIn("Performance Timing", summary)
        self.assertIn("Database Pool", summary)
    
    def test_log_periodic_summary(self):
        """Test periodic summary logging"""
        # Mock time to control interval
        with patch('time.time') as mock_time:
            mock_time.return_value = self.monitor.last_metrics_snapshot + 400  # Past interval
            
            with patch.object(self.monitor.logger, 'info') as mock_log:
                self.monitor.log_periodic_summary(300)  # 5 minute interval
                
                mock_log.assert_called_once()
                self.assertIn("Performance Summary", mock_log.call_args[0][0])
    
    def test_thread_safety(self):
        """Test thread safety of metrics recording"""
        def record_operations():
            for i in range(100):
                self.monitor.record_session_creation()
                self.monitor.record_session_closure()
                self.monitor.record_session_commit()
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_operations)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all operations were recorded correctly
        self.assertEqual(self.monitor.metrics.session_creations, 500)
        self.assertEqual(self.monitor.metrics.session_closures, 500)
        self.assertEqual(self.monitor.metrics.session_commits, 500)

class TestGlobalMonitorFunctions(unittest.TestCase):
    """Test global monitor functions"""
    
    def test_get_performance_monitor_singleton(self):
        """Test that get_performance_monitor returns singleton"""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        self.assertIs(monitor1, monitor2)
    
    @patch('session_performance_monitor.SessionPerformanceMonitor')
    def test_initialize_performance_monitoring(self, mock_monitor_class):
        """Test initialize_performance_monitoring function"""
        mock_app = Mock()
        mock_session_manager = Mock()
        mock_engine = Mock()
        mock_monitor = Mock()
        mock_monitor_class.return_value = mock_monitor
        
        result = initialize_performance_monitoring(mock_app, mock_session_manager, mock_engine)
        
        # Check that monitor was created with correct name
        mock_monitor_class.assert_called_once_with(f"{mock_app.name}.session_performance")
        
        # Check that handlers were registered
        mock_app.before_request.assert_called_once()
        mock_app.teardown_request.assert_called_once()
        
        # Check that monitor was stored in app
        self.assertEqual(mock_app.session_performance_monitor, mock_monitor)
        
        # Check that logger was called
        mock_app.logger.info.assert_called_once_with("Session performance monitoring initialized")
        
        self.assertEqual(result, mock_monitor)

class TestPerformanceMonitoringIntegration(unittest.TestCase):
    """Integration tests for performance monitoring"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.monitor = SessionPerformanceMonitor("integration_test")
    
    def test_full_session_lifecycle_monitoring(self):
        """Test monitoring a complete session lifecycle"""
        # Simulate a complete session lifecycle
        self.monitor.record_session_creation(0.1)
        self.monitor.record_session_commit()
        self.monitor.record_session_reattachment("User")
        self.monitor.record_detached_instance_recovery("PlatformConnection", 0.05, True)
        self.monitor.record_session_closure(0.08)
        
        metrics = self.monitor.get_current_metrics()
        
        # Verify all operations were recorded
        self.assertEqual(metrics['session_metrics']['creations'], 1)
        self.assertEqual(metrics['session_metrics']['closures'], 1)
        self.assertEqual(metrics['session_metrics']['commits'], 1)
        self.assertEqual(metrics['recovery_metrics']['detached_instance_recoveries'], 1)
        self.assertEqual(metrics['recovery_metrics']['session_reattachments'], 1)
        self.assertEqual(metrics['session_metrics']['active_sessions'], 0)  # Should be 0 after closure
    
    def test_error_scenario_monitoring(self):
        """Test monitoring error scenarios"""
        # Simulate error scenarios
        self.monitor.record_session_creation(0.1)
        self.monitor.record_session_error("connection_timeout", "Connection timed out")
        self.monitor.record_detached_instance_recovery("User", 0.2, False)  # Failed recovery
        self.monitor.record_session_rollback()
        self.monitor.record_session_closure(0.05)
        
        metrics = self.monitor.get_current_metrics()
        
        # Verify error tracking
        self.assertEqual(metrics['session_metrics']['errors'], 1)
        self.assertEqual(metrics['session_metrics']['rollbacks'], 1)
        self.assertEqual(metrics['recovery_metrics']['detached_instance_recoveries'], 1)
    
    def test_performance_threshold_alerts(self):
        """Test performance threshold detection"""
        # Record slow operations
        self.monitor.record_session_creation(2.0)  # Slow creation
        self.monitor.record_session_closure(1.5)   # Slow cleanup
        self.monitor.record_detached_instance_recovery("User", 3.0, True)  # Slow recovery
        
        metrics = self.monitor.get_current_metrics()
        
        # Check that slow operations were recorded
        self.assertGreater(metrics['performance_metrics']['avg_creation_time'], 1.0)
        self.assertGreater(metrics['performance_metrics']['avg_cleanup_time'], 1.0)
        self.assertGreater(metrics['performance_metrics']['avg_recovery_time'], 1.0)

if __name__ == '__main__':
    unittest.main()