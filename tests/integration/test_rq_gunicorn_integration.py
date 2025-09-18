# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH the SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for RQ Gunicorn Integration and Worker Coordination

Tests RQ worker integration with Gunicorn processes, worker coordination
across multiple processes, and proper resource management.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import threading
import time
import signal
import os
import subprocess
from datetime import datetime, timezone
import redis
from flask import Flask

from app.core.database.core.database_manager import DatabaseManager
from app.services.task.rq.rq_worker_manager import RQWorkerManager
from app.services.task.rq.integrated_rq_worker import IntegratedRQWorker
from app.services.task.rq.gunicorn_integration import GunicornRQIntegration
from app.services.task.rq.flask_rq_integration import FlaskRQIntegration
from app.services.task.rq.rq_config import RQConfig


class TestGunicornRQIntegration(unittest.TestCase):
    """Test RQ integration with Gunicorn application server"""
    
    def setUp(self):
        """Set up Gunicorn integration test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_redis.ping.return_value = True
        
        # Create test configuration
        self.config = RQConfig()
        
        # Mock Flask app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Initialize integration components
        self.gunicorn_integration = GunicornRQIntegration(
            self.mock_db_manager,
            self.mock_redis,
            self.config
        )
        
        self.flask_integration = FlaskRQIntegration(
            self.app,
            self.mock_db_manager,
            self.mock_redis,
            self.config
        )
    
    def test_gunicorn_worker_initialization(self):
        """Test RQ worker initialization when Gunicorn starts"""
        # Mock Gunicorn worker process
        mock_worker_process = Mock()
        mock_worker_process.pid = 12345
        
        # Test worker initialization
        with patch('app.services.task.rq.rq_worker_manager.RQWorkerManager') as mock_worker_manager_class:
            mock_worker_manager = Mock()
            mock_worker_manager_class.return_value = mock_worker_manager
            
            # Initialize RQ workers for Gunicorn process
            self.gunicorn_integration.initialize_workers_for_process(mock_worker_process)
            
            # Verify worker manager was created
            mock_worker_manager_class.assert_called_once()
            
            # Verify workers were started
            mock_worker_manager.start_integrated_workers.assert_called_once()
            
            # Verify process tracking
            self.assertIn(12345, self.gunicorn_integration.process_workers)
    
    def test_flask_app_startup_integration(self):
        """Test Flask app startup integration with RQ workers"""
        # Mock Flask startup hooks
        startup_functions = []
        
        def mock_before_first_request(func):
            startup_functions.append(func)
            return func
        
        # Test Flask integration setup
        with patch.object(self.app, 'before_first_request', mock_before_first_request):
            self.flask_integration.setup_app_integration()
            
            # Verify startup function was registered
            self.assertEqual(len(startup_functions), 1)
            
            # Test startup function execution
            with patch('app.services.task.rq.rq_worker_manager.RQWorkerManager') as mock_worker_manager_class:
                mock_worker_manager = Mock()
                mock_worker_manager_class.return_value = mock_worker_manager
                
                # Execute startup function
                startup_functions[0]()
                
                # Verify worker manager was initialized
                mock_worker_manager_class.assert_called_once()
                mock_worker_manager.start_integrated_workers.assert_called_once()
    
    def test_worker_coordination_across_processes(self):
        """Test worker coordination across multiple Gunicorn processes"""
        # Simulate multiple Gunicorn worker processes
        process_pids = [12345, 12346, 12347]
        worker_managers = []
        
        for pid in process_pids:
            mock_process = Mock()
            mock_process.pid = pid
            
            with patch('app.services.task.rq.rq_worker_manager.RQWorkerManager') as mock_worker_manager_class:
                mock_worker_manager = Mock()
                mock_worker_manager.worker_id = f"worker-{pid}"
                mock_worker_manager_class.return_value = mock_worker_manager
                
                # Initialize workers for each process
                self.gunicorn_integration.initialize_workers_for_process(mock_process)
                worker_managers.append(mock_worker_manager)
        
        # Verify each process registered its workers
        for worker_manager in worker_managers:
            worker_manager.register_worker_coordination.assert_called_once()
        
        # Test coordination key uniqueness
        coordination_keys = []
        for worker_manager in worker_managers:
            key = f"rq:workers:{worker_manager.worker_id}"
            coordination_keys.append(key)
        
        # Verify all coordination keys are unique
        self.assertEqual(len(coordination_keys), len(set(coordination_keys)))
    
    def test_graceful_shutdown_on_gunicorn_signal(self):
        """Test graceful RQ worker shutdown when Gunicorn receives shutdown signal"""
        # Mock active worker manager
        mock_worker_manager = Mock()
        self.gunicorn_integration.process_workers[12345] = mock_worker_manager
        
        # Mock signal handler registration
        original_signal = signal.signal
        signal_handlers = {}
        
        def mock_signal(sig, handler):
            signal_handlers[sig] = handler
            return original_signal
        
        with patch('signal.signal', mock_signal):
            # Register shutdown handlers
            self.gunicorn_integration.register_shutdown_handlers()
            
            # Verify SIGTERM handler was registered
            self.assertIn(signal.SIGTERM, signal_handlers)
            
            # Simulate SIGTERM signal
            sigterm_handler = signal_handlers[signal.SIGTERM]
            sigterm_handler(signal.SIGTERM, None)
            
            # Verify graceful shutdown was called
            mock_worker_manager.stop_workers.assert_called_with(graceful=True, timeout=30)
    
    def test_worker_health_monitoring_across_processes(self):
        """Test worker health monitoring across Gunicorn processes"""
        # Mock multiple processes with workers
        process_data = [
            {'pid': 12345, 'healthy': True},
            {'pid': 12346, 'healthy': False},
            {'pid': 12347, 'healthy': True}
        ]
        
        for data in process_data:
            mock_worker_manager = Mock()
            mock_worker_manager.check_worker_health.return_value = {
                'healthy_workers': 2 if data['healthy'] else 0,
                'unhealthy_workers': 0 if data['healthy'] else 2,
                'total_workers': 2
            }
            self.gunicorn_integration.process_workers[data['pid']] = mock_worker_manager
        
        # Get overall health status
        overall_health = self.gunicorn_integration.get_overall_health_status()
        
        # Verify health aggregation
        self.assertIn('total_processes', overall_health)
        self.assertIn('healthy_processes', overall_health)
        self.assertIn('total_workers', overall_health)
        self.assertIn('healthy_workers', overall_health)
        
        self.assertEqual(overall_health['total_processes'], 3)
        self.assertEqual(overall_health['healthy_processes'], 2)  # 2 healthy processes
        self.assertEqual(overall_health['total_workers'], 6)      # 2 workers per process
        self.assertEqual(overall_health['healthy_workers'], 4)    # 4 healthy workers total
    
    def test_dynamic_worker_scaling_across_processes(self):
        """Test dynamic worker scaling across Gunicorn processes"""
        # Mock multiple processes
        process_pids = [12345, 12346]
        
        for pid in process_pids:
            mock_worker_manager = Mock()
            mock_worker_manager.scale_workers.return_value = True
            self.gunicorn_integration.process_workers[pid] = mock_worker_manager
        
        # Test scaling workers across all processes
        queue_name = 'normal'
        target_workers_per_process = 3
        
        result = self.gunicorn_integration.scale_workers_across_processes(
            queue_name, 
            target_workers_per_process
        )
        
        # Verify scaling was applied to all processes
        self.assertTrue(result)
        for pid in process_pids:
            worker_manager = self.gunicorn_integration.process_workers[pid]
            worker_manager.scale_workers.assert_called_with(queue_name, target_workers_per_process)
    
    def test_resource_cleanup_on_process_termination(self):
        """Test resource cleanup when Gunicorn process terminates"""
        pid = 12345
        mock_worker_manager = Mock()
        self.gunicorn_integration.process_workers[pid] = mock_worker_manager
        
        # Mock Redis coordination cleanup
        mock_worker_manager.cleanup_worker_coordination.return_value = None
        
        # Test process termination cleanup
        self.gunicorn_integration.cleanup_process_resources(pid)
        
        # Verify cleanup was performed
        mock_worker_manager.stop_workers.assert_called_with(graceful=True, timeout=10)
        mock_worker_manager.cleanup_worker_coordination.assert_called_once()
        
        # Verify process was removed from tracking
        self.assertNotIn(pid, self.gunicorn_integration.process_workers)
    
    def test_configuration_hot_reload(self):
        """Test hot reloading of RQ configuration across processes"""
        # Mock processes with workers
        process_pids = [12345, 12346]
        
        for pid in process_pids:
            mock_worker_manager = Mock()
            mock_worker_manager.reload_configuration.return_value = True
            self.gunicorn_integration.process_workers[pid] = mock_worker_manager
        
        # Create new configuration
        new_config = RQConfig()
        new_config.max_workers_per_queue = 5
        
        # Test configuration reload
        result = self.gunicorn_integration.reload_configuration(new_config)
        
        # Verify configuration was reloaded in all processes
        self.assertTrue(result)
        for pid in process_pids:
            worker_manager = self.gunicorn_integration.process_workers[pid]
            worker_manager.reload_configuration.assert_called_with(new_config)


class TestIntegratedRQWorkerLifecycle(unittest.TestCase):
    """Test integrated RQ worker lifecycle management"""
    
    def setUp(self):
        """Set up worker lifecycle test fixtures"""
        # Mock dependencies
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_app_context = Mock()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Mock Flask app context
        self.mock_app_context.__enter__ = Mock(return_value=self.mock_app_context)
        self.mock_app_context.__exit__ = Mock(return_value=None)
        
        self.queues = ['normal', 'low']
        self.worker_id = 'test-lifecycle-worker'
    
    @patch('app.services.task.rq.integrated_rq_worker.Worker')
    @patch('threading.Thread')
    def test_worker_startup_sequence(self, mock_thread_class, mock_worker_class):
        """Test complete worker startup sequence"""
        # Mock RQ Worker
        mock_rq_worker = Mock()
        mock_worker_class.return_value = mock_rq_worker
        
        # Mock thread
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Initialize integrated worker
        integrated_worker = IntegratedRQWorker(
            self.queues,
            self.mock_redis,
            self.mock_app_context,
            self.mock_db_manager,
            self.worker_id
        )
        
        # Test startup sequence
        integrated_worker.start()
        
        # Verify worker initialization
        mock_worker_class.assert_called_once_with(
            self.queues,
            connection=self.mock_redis,
            name=f"worker-{self.worker_id}"
        )
        
        # Verify thread creation and startup
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()
        
        # Verify worker state
        self.assertTrue(integrated_worker.running)
        self.assertEqual(integrated_worker.thread, mock_thread)
    
    @patch('app.services.task.rq.integrated_rq_worker.Worker')
    def test_worker_shutdown_sequence(self, mock_worker_class):
        """Test complete worker shutdown sequence"""
        # Mock RQ Worker
        mock_rq_worker = Mock()
        mock_worker_class.return_value = mock_rq_worker
        
        # Mock running thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        
        # Initialize and start worker
        integrated_worker = IntegratedRQWorker(
            self.queues,
            self.mock_redis,
            self.mock_app_context,
            self.mock_db_manager,
            self.worker_id
        )
        
        integrated_worker.thread = mock_thread
        integrated_worker.running = True
        
        # Test shutdown sequence
        result = integrated_worker.stop(timeout=30)
        
        # Verify graceful shutdown request
        mock_rq_worker.request_stop.assert_called_once()
        
        # Verify thread join with timeout
        mock_thread.join.assert_called_with(timeout=30)
        
        # Verify worker state
        self.assertFalse(integrated_worker.running)
        self.assertTrue(result)  # Successful shutdown
    
    @patch('app.services.task.rq.integrated_rq_worker.Worker')
    def test_worker_health_monitoring(self, mock_worker_class):
        """Test worker health monitoring and reporting"""
        # Mock RQ Worker
        mock_rq_worker = Mock()
        mock_rq_worker.get_current_job.return_value = None  # No current job
        mock_worker_class.return_value = mock_rq_worker
        
        # Mock thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        
        # Initialize worker
        integrated_worker = IntegratedRQWorker(
            self.queues,
            self.mock_redis,
            self.mock_app_context,
            self.mock_db_manager,
            self.worker_id
        )
        
        integrated_worker.thread = mock_thread
        integrated_worker.running = True
        
        # Test health check
        is_healthy = integrated_worker.is_healthy()
        
        # Verify health status
        self.assertTrue(is_healthy)
        
        # Test health status details
        health_status = integrated_worker.get_health_status()
        
        # Verify health status structure
        self.assertIn('is_running', health_status)
        self.assertIn('thread_alive', health_status)
        self.assertIn('current_job', health_status)
        self.assertIn('last_heartbeat', health_status)
        
        self.assertTrue(health_status['is_running'])
        self.assertTrue(health_status['thread_alive'])
        self.assertIsNone(health_status['current_job'])
    
    @patch('app.services.task.rq.integrated_rq_worker.Worker')
    def test_worker_memory_monitoring(self, mock_worker_class):
        """Test worker memory usage monitoring"""
        # Mock RQ Worker
        mock_rq_worker = Mock()
        mock_worker_class.return_value = mock_rq_worker
        
        # Initialize worker
        integrated_worker = IntegratedRQWorker(
            self.queues,
            self.mock_redis,
            self.mock_app_context,
            self.mock_db_manager,
            self.worker_id
        )
        
        # Mock memory usage
        with patch('psutil.Process') as mock_process_class:
            mock_process = Mock()
            mock_process.memory_info.return_value.rss = 1024 * 1024 * 256  # 256 MB
            mock_process_class.return_value = mock_process
            
            # Test memory monitoring
            memory_usage = integrated_worker.get_memory_usage()
            
            # Verify memory usage reporting
            self.assertEqual(memory_usage, 256.0)  # MB
    
    @patch('app.services.task.rq.integrated_rq_worker.Worker')
    def test_worker_error_handling(self, mock_worker_class):
        """Test worker error handling and recovery"""
        # Mock RQ Worker that raises exception
        mock_rq_worker = Mock()
        mock_rq_worker.work.side_effect = Exception("Worker crashed")
        mock_worker_class.return_value = mock_rq_worker
        
        # Initialize worker
        integrated_worker = IntegratedRQWorker(
            self.queues,
            self.mock_redis,
            self.mock_app_context,
            self.mock_db_manager,
            self.worker_id
        )
        
        # Mock session manager for cleanup
        mock_session_manager = Mock()
        integrated_worker.session_manager = mock_session_manager
        
        # Test error handling in worker loop
        with patch('threading.Thread') as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread
            
            # Capture the worker loop function
            worker_loop_func = None
            
            def capture_thread_target(*args, **kwargs):
                nonlocal worker_loop_func
                worker_loop_func = kwargs.get('target')
                return mock_thread
            
            mock_thread_class.side_effect = capture_thread_target
            
            # Start worker
            integrated_worker.start()
            
            # Execute worker loop (which should handle the exception)
            if worker_loop_func:
                try:
                    worker_loop_func()
                except Exception:
                    pass  # Expected to handle gracefully
            
            # Verify session cleanup was called even after error
            mock_session_manager.close_session.assert_called()


class TestWorkerCoordinationMechanisms(unittest.TestCase):
    """Test worker coordination mechanisms across processes"""
    
    def setUp(self):
        """Set up worker coordination test fixtures"""
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.config = RQConfig()
    
    def test_worker_registration_and_discovery(self):
        """Test worker registration and discovery across processes"""
        # Create multiple worker managers (simulating different processes)
        worker_managers = []
        
        for i in range(3):
            worker_manager = RQWorkerManager(
                self.mock_db_manager,
                self.mock_redis,
                self.config,
                {}
            )
            worker_manager.worker_id = f"worker-process-{i}"
            worker_managers.append(worker_manager)
        
        # Register all workers
        for worker_manager in worker_managers:
            worker_manager.register_worker_coordination()
        
        # Verify Redis registration calls
        expected_calls = len(worker_managers)
        self.assertEqual(self.mock_redis.setex.call_count, expected_calls)
        
        # Test worker discovery
        # Mock Redis scan to return all registered workers
        registered_keys = [f"rq:workers:worker-process-{i}".encode() for i in range(3)]
        self.mock_redis.scan_iter.return_value = registered_keys
        
        # Get active workers
        active_workers = worker_managers[0].get_active_workers()
        
        # Verify all workers are discovered
        self.assertEqual(len(active_workers), 3)
    
    def test_task_distribution_coordination(self):
        """Test task distribution coordination to prevent duplicate processing"""
        # Mock Redis lock operations
        self.mock_redis.set.return_value = True  # Lock acquired
        self.mock_redis.delete.return_value = 1  # Lock released
        
        # Create worker manager
        worker_manager = RQWorkerManager(
            self.mock_db_manager,
            self.mock_redis,
            self.config,
            {}
        )
        
        task_id = "coordination-task-123"
        
        # Test acquiring task lock
        lock_acquired = worker_manager.acquire_task_lock(task_id)
        
        # Verify lock acquisition
        self.assertTrue(lock_acquired)
        expected_lock_key = f"rq:task_lock:{task_id}"
        self.mock_redis.set.assert_called_with(
            expected_lock_key,
            worker_manager.worker_id,
            nx=True,
            ex=300  # 5 minute expiration
        )
        
        # Test releasing task lock
        lock_released = worker_manager.release_task_lock(task_id)
        
        # Verify lock release
        self.assertTrue(lock_released)
        self.mock_redis.delete.assert_called_with(expected_lock_key)
    
    def test_worker_heartbeat_mechanism(self):
        """Test worker heartbeat mechanism for health monitoring"""
        # Create worker manager
        worker_manager = RQWorkerManager(
            self.mock_db_manager,
            self.mock_redis,
            self.config,
            {}
        )
        
        # Mock Redis operations for heartbeat
        self.mock_redis.hset.return_value = True
        self.mock_redis.expire.return_value = True
        
        # Test sending heartbeat
        worker_manager.send_heartbeat()
        
        # Verify heartbeat was sent
        expected_key = f"rq:workers:{worker_manager.worker_id}"
        self.mock_redis.hset.assert_called()
        self.mock_redis.expire.assert_called_with(expected_key, 300)  # 5 minute TTL
        
        # Test checking worker heartbeats
        # Mock Redis scan for worker keys
        worker_keys = [
            b"rq:workers:worker-1",
            b"rq:workers:worker-2",
            b"rq:workers:worker-3"
        ]
        self.mock_redis.scan_iter.return_value = worker_keys
        
        # Mock heartbeat data
        self.mock_redis.hgetall.side_effect = [
            {b'last_heartbeat': str(time.time()).encode(), b'status': b'active'},
            {b'last_heartbeat': str(time.time() - 400).encode(), b'status': b'active'},  # Stale
            {b'last_heartbeat': str(time.time()).encode(), b'status': b'active'}
        ]
        
        # Check worker health
        health_report = worker_manager.check_all_worker_health()
        
        # Verify health report
        self.assertIn('healthy_workers', health_report)
        self.assertIn('stale_workers', health_report)
        self.assertEqual(len(health_report['healthy_workers']), 2)
        self.assertEqual(len(health_report['stale_workers']), 1)
    
    def test_load_balancing_coordination(self):
        """Test load balancing coordination across workers"""
        # Create multiple worker managers
        worker_managers = []
        
        for i in range(3):
            worker_manager = RQWorkerManager(
                self.mock_db_manager,
                self.mock_redis,
                self.config,
                {}
            )
            worker_manager.worker_id = f"load-balance-worker-{i}"
            worker_managers.append(worker_manager)
        
        # Mock Redis operations for load reporting
        self.mock_redis.hset.return_value = True
        self.mock_redis.hgetall.side_effect = [
            {b'active_jobs': b'2', b'queue_size': b'5'},
            {b'active_jobs': b'1', b'queue_size': b'3'},
            {b'active_jobs': b'3', b'queue_size': b'7'}
        ]
        
        # Report load for each worker
        loads = [2, 1, 3]
        for i, (worker_manager, load) in enumerate(zip(worker_managers, loads)):
            worker_manager.report_worker_load(active_jobs=load, queue_size=load + 3)
        
        # Test load balancing decision
        # Mock Redis scan for worker load data
        load_keys = [f"rq:worker_load:load-balance-worker-{i}".encode() for i in range(3)]
        self.mock_redis.scan_iter.return_value = load_keys
        
        # Get optimal worker for new task
        optimal_worker = worker_managers[0].get_optimal_worker_for_task()
        
        # Verify load balancing logic
        self.assertIsNotNone(optimal_worker)
        # Should select worker with lowest load (worker-1 with load=1)
        self.assertEqual(optimal_worker, 'load-balance-worker-1')


if __name__ == '__main__':
    unittest.main()