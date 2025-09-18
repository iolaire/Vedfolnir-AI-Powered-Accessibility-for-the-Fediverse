# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for RQ Worker Manager

Tests worker lifecycle management, coordination, graceful shutdown,
and integration with Gunicorn processes.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import threading
import time
import redis
from rq import Worker, Queue
from datetime import datetime, timezone

from app.core.database.core.database_manager import DatabaseManager
from app.services.task.rq.rq_worker_manager import RQWorkerManager
from app.services.task.rq.integrated_rq_worker import IntegratedRQWorker
from app.services.task.rq.worker_session_manager import WorkerSessionManager
from app.services.task.rq.rq_config import RQConfig, WorkerConfig


class TestRQWorkerManager(unittest.TestCase):
    """Test RQ Worker Manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_redis.ping.return_value = True
        
        # Create test configuration
        self.config = RQConfig()
        self.worker_config = WorkerConfig(
            worker_id='test-worker-1',
            queues=['urgent', 'high', 'normal'],
            concurrency=2,
            memory_limit=512,
            timeout=300,
            health_check_interval=30
        )
        
        # Mock queues
        self.mock_queues = {}
        for priority in ['urgent', 'high', 'normal', 'low']:
            mock_queue = Mock(spec=Queue)
            mock_queue.name = priority
            self.mock_queues[priority] = mock_queue
        
        # Initialize worker manager
        self.worker_manager = RQWorkerManager(
            self.mock_db_manager,
            self.mock_redis,
            self.config,
            self.mock_queues
        )
    
    def test_initialization(self):
        """Test RQWorkerManager initialization"""
        # Verify initialization
        self.assertEqual(self.worker_manager.db_manager, self.mock_db_manager)
        self.assertEqual(self.worker_manager.redis_connection, self.mock_redis)
        self.assertEqual(self.worker_manager.config, self.config)
        self.assertEqual(self.worker_manager.queues, self.mock_queues)
        
        # Verify worker tracking structures
        self.assertIsInstance(self.worker_manager.integrated_workers, list)
        self.assertIsInstance(self.worker_manager.external_workers, list)
        self.assertIsInstance(self.worker_manager.workers, dict)
        
        # Verify unique worker ID generation
        self.assertIsNotNone(self.worker_manager.worker_id)
        self.assertTrue(self.worker_manager.worker_id.startswith('worker-'))
    
    def test_generate_unique_worker_id(self):
        """Test unique worker ID generation"""
        worker_id = self.worker_manager._generate_unique_worker_id()
        
        # Verify format
        self.assertTrue(worker_id.startswith('worker-'))
        self.assertGreater(len(worker_id), 10)  # Should include timestamp/random component
        
        # Verify uniqueness
        worker_id2 = self.worker_manager._generate_unique_worker_id()
        self.assertNotEqual(worker_id, worker_id2)
    
    @patch('app.services.task.rq.rq_worker_manager.IntegratedRQWorker')
    def test_start_integrated_workers(self, mock_integrated_worker_class):
        """Test starting integrated workers"""
        # Mock integrated worker instances
        mock_worker1 = Mock(spec=IntegratedRQWorker)
        mock_worker2 = Mock(spec=IntegratedRQWorker)
        mock_integrated_worker_class.side_effect = [mock_worker1, mock_worker2]
        
        # Configure worker settings
        self.worker_manager.config.integrated_workers = [
            {'queues': ['urgent', 'high'], 'count': 1},
            {'queues': ['normal', 'low'], 'count': 1}
        ]
        
        # Start integrated workers
        self.worker_manager.start_integrated_workers()
        
        # Verify workers were created and started
        self.assertEqual(len(self.worker_manager.integrated_workers), 2)
        mock_worker1.start.assert_called_once()
        mock_worker2.start.assert_called_once()
        
        # Verify worker coordination was registered
        self.mock_redis.setex.assert_called()
    
    @patch('subprocess.Popen')
    def test_start_external_workers(self, mock_popen):
        """Test starting external workers"""
        # Mock subprocess for external workers
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Configure external worker settings
        self.worker_manager.config.external_workers = [
            {'queues': ['low'], 'count': 2, 'separate_process': True}
        ]
        
        # Start external workers
        self.worker_manager.start_external_workers()
        
        # Verify external processes were started
        self.assertEqual(len(self.worker_manager.external_workers), 2)
        self.assertEqual(mock_popen.call_count, 2)
        
        # Verify process tracking
        for worker_info in self.worker_manager.external_workers:
            self.assertIn('process', worker_info)
            self.assertIn('pid', worker_info)
            self.assertEqual(worker_info['pid'], 12345)
    
    def test_register_worker_coordination(self):
        """Test worker coordination registration"""
        # Test coordination registration
        self.worker_manager.register_worker_coordination()
        
        # Verify Redis operations
        expected_key = f"rq:workers:{self.worker_manager.worker_id}"
        self.mock_redis.setex.assert_called_with(expected_key, 300, "active")
        
        # Verify worker metadata
        self.mock_redis.hset.assert_called()
    
    def test_cleanup_worker_coordination(self):
        """Test worker coordination cleanup"""
        # Test coordination cleanup
        self.worker_manager.cleanup_worker_coordination()
        
        # Verify Redis cleanup
        expected_key = f"rq:workers:{self.worker_manager.worker_id}"
        self.mock_redis.delete.assert_called_with(expected_key)
    
    @patch('app.services.task.rq.rq_worker_manager.IntegratedRQWorker')
    def test_stop_workers_graceful(self, mock_integrated_worker_class):
        """Test graceful worker shutdown"""
        # Set up integrated workers
        mock_worker1 = Mock(spec=IntegratedRQWorker)
        mock_worker2 = Mock(spec=IntegratedRQWorker)
        mock_integrated_worker_class.side_effect = [mock_worker1, mock_worker2]
        
        self.worker_manager.integrated_workers = [
            {'worker': mock_worker1, 'worker_id': 'worker-1'},
            {'worker': mock_worker2, 'worker_id': 'worker-2'}
        ]
        
        # Mock external workers
        mock_process1 = Mock()
        mock_process1.poll.return_value = None  # Still running
        mock_process1.terminate.return_value = None
        mock_process1.wait.return_value = 0
        
        self.worker_manager.external_workers = [
            {'process': mock_process1, 'pid': 12345, 'worker_id': 'external-1'}
        ]
        
        # Test graceful shutdown
        self.worker_manager.stop_workers(graceful=True, timeout=30)
        
        # Verify integrated workers were stopped gracefully
        mock_worker1.stop.assert_called_with(timeout=30)
        mock_worker2.stop.assert_called_with(timeout=30)
        
        # Verify external workers were terminated gracefully
        mock_process1.terminate.assert_called_once()
        mock_process1.wait.assert_called_with(timeout=30)
        
        # Verify coordination cleanup
        self.mock_redis.delete.assert_called()
    
    @patch('app.services.task.rq.rq_worker_manager.IntegratedRQWorker')
    def test_stop_workers_force_kill(self, mock_integrated_worker_class):
        """Test force killing workers when graceful shutdown fails"""
        # Set up integrated worker that doesn't stop gracefully
        mock_worker = Mock(spec=IntegratedRQWorker)
        mock_worker.stop.return_value = False  # Graceful stop failed
        mock_integrated_worker_class.return_value = mock_worker
        
        self.worker_manager.integrated_workers = [
            {'worker': mock_worker, 'worker_id': 'stubborn-worker'}
        ]
        
        # Mock external process that doesn't terminate gracefully
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running
        mock_process.terminate.return_value = None
        mock_process.wait.side_effect = TimeoutError("Process didn't terminate")
        mock_process.kill.return_value = None
        
        self.worker_manager.external_workers = [
            {'process': mock_process, 'pid': 12345, 'worker_id': 'stubborn-external'}
        ]
        
        # Test force shutdown
        self.worker_manager.stop_workers(graceful=False, timeout=5)
        
        # Verify force kill was attempted
        mock_process.kill.assert_called_once()
    
    def test_restart_worker(self):
        """Test restarting a specific worker"""
        # Mock existing worker
        mock_worker = Mock(spec=IntegratedRQWorker)
        worker_id = 'worker-to-restart'
        
        self.worker_manager.workers[worker_id] = {
            'worker': mock_worker,
            'type': 'integrated',
            'queues': ['normal'],
            'config': self.worker_config
        }
        
        with patch('app.services.task.rq.rq_worker_manager.IntegratedRQWorker') as mock_worker_class:
            mock_new_worker = Mock(spec=IntegratedRQWorker)
            mock_worker_class.return_value = mock_new_worker
            
            # Test worker restart
            result = self.worker_manager.restart_worker(worker_id)
            
            # Verify old worker was stopped
            mock_worker.stop.assert_called_once()
            
            # Verify new worker was created and started
            mock_new_worker.start.assert_called_once()
            
            # Verify result
            self.assertTrue(result)
    
    def test_restart_nonexistent_worker(self):
        """Test restarting a worker that doesn't exist"""
        # Test restarting non-existent worker
        result = self.worker_manager.restart_worker('nonexistent-worker')
        
        # Should return False
        self.assertFalse(result)
    
    def test_scale_workers_up(self):
        """Test scaling workers up"""
        queue_name = 'normal'
        target_count = 3
        
        with patch('app.services.task.rq.rq_worker_manager.IntegratedRQWorker') as mock_worker_class:
            mock_workers = [Mock(spec=IntegratedRQWorker) for _ in range(3)]
            mock_worker_class.side_effect = mock_workers
            
            # Test scaling up
            result = self.worker_manager.scale_workers(queue_name, target_count)
            
            # Verify workers were created
            self.assertEqual(mock_worker_class.call_count, 3)
            for mock_worker in mock_workers:
                mock_worker.start.assert_called_once()
            
            # Verify result
            self.assertTrue(result)
    
    def test_scale_workers_down(self):
        """Test scaling workers down"""
        queue_name = 'normal'
        
        # Set up existing workers
        mock_workers = [Mock(spec=IntegratedRQWorker) for _ in range(3)]
        for i, worker in enumerate(mock_workers):
            worker_id = f'worker-{i}'
            self.worker_manager.workers[worker_id] = {
                'worker': worker,
                'type': 'integrated',
                'queues': [queue_name],
                'config': self.worker_config
            }
        
        # Test scaling down to 1 worker
        result = self.worker_manager.scale_workers(queue_name, 1)
        
        # Verify 2 workers were stopped (keeping 1)
        stopped_count = sum(1 for worker in mock_workers if worker.stop.called)
        self.assertEqual(stopped_count, 2)
        
        # Verify result
        self.assertTrue(result)
    
    def test_get_worker_status(self):
        """Test getting worker status information"""
        # Set up mock workers
        mock_integrated_worker = Mock(spec=IntegratedRQWorker)
        mock_integrated_worker.is_running.return_value = True
        mock_integrated_worker.get_stats.return_value = {
            'jobs_processed': 10,
            'memory_usage': 256,
            'uptime': 3600
        }
        
        self.worker_manager.integrated_workers = [
            {
                'worker': mock_integrated_worker,
                'worker_id': 'integrated-1',
                'queues': ['normal'],
                'started_at': datetime.now(timezone.utc)
            }
        ]
        
        # Mock external worker
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running
        mock_process.pid = 12345
        
        self.worker_manager.external_workers = [
            {
                'process': mock_process,
                'worker_id': 'external-1',
                'pid': 12345,
                'queues': ['low'],
                'started_at': datetime.now(timezone.utc)
            }
        ]
        
        # Get worker status
        status = self.worker_manager.get_worker_status()
        
        # Verify status structure
        self.assertIn('integrated_workers', status)
        self.assertIn('external_workers', status)
        self.assertIn('total_workers', status)
        self.assertIn('active_workers', status)
        
        # Verify integrated worker status
        self.assertEqual(len(status['integrated_workers']), 1)
        integrated_status = status['integrated_workers'][0]
        self.assertEqual(integrated_status['worker_id'], 'integrated-1')
        self.assertTrue(integrated_status['is_running'])
        self.assertIn('stats', integrated_status)
        
        # Verify external worker status
        self.assertEqual(len(status['external_workers']), 1)
        external_status = status['external_workers'][0]
        self.assertEqual(external_status['worker_id'], 'external-1')
        self.assertEqual(external_status['pid'], 12345)
        self.assertTrue(external_status['is_running'])
    
    def test_health_check_monitoring(self):
        """Test worker health check monitoring"""
        # Mock unhealthy worker
        mock_worker = Mock(spec=IntegratedRQWorker)
        mock_worker.is_healthy.return_value = False
        mock_worker.get_health_status.return_value = {
            'status': 'unhealthy',
            'last_heartbeat': datetime.now(timezone.utc),
            'error': 'Memory limit exceeded'
        }
        
        self.worker_manager.integrated_workers = [
            {
                'worker': mock_worker,
                'worker_id': 'unhealthy-worker',
                'health_check_enabled': True
            }
        ]
        
        # Run health check
        health_report = self.worker_manager.check_worker_health()
        
        # Verify health report
        self.assertIn('healthy_workers', health_report)
        self.assertIn('unhealthy_workers', health_report)
        self.assertIn('total_workers', health_report)
        
        # Verify unhealthy worker is detected
        self.assertEqual(len(health_report['unhealthy_workers']), 1)
        unhealthy_worker = health_report['unhealthy_workers'][0]
        self.assertEqual(unhealthy_worker['worker_id'], 'unhealthy-worker')
        self.assertEqual(unhealthy_worker['status'], 'unhealthy')
    
    def test_automatic_worker_restart_on_failure(self):
        """Test automatic worker restart when worker fails"""
        # Mock failed worker
        mock_worker = Mock(spec=IntegratedRQWorker)
        mock_worker.is_running.return_value = False
        mock_worker.is_healthy.return_value = False
        
        worker_id = 'failed-worker'
        self.worker_manager.workers[worker_id] = {
            'worker': mock_worker,
            'type': 'integrated',
            'queues': ['normal'],
            'config': self.worker_config,
            'auto_restart': True
        }
        
        with patch('app.services.task.rq.rq_worker_manager.IntegratedRQWorker') as mock_worker_class:
            mock_new_worker = Mock(spec=IntegratedRQWorker)
            mock_worker_class.return_value = mock_new_worker
            
            # Run health check with auto-restart
            self.worker_manager.check_and_restart_failed_workers()
            
            # Verify worker was restarted
            mock_new_worker.start.assert_called_once()
    
    def test_worker_memory_monitoring(self):
        """Test worker memory usage monitoring"""
        # Mock worker with high memory usage
        mock_worker = Mock(spec=IntegratedRQWorker)
        mock_worker.get_memory_usage.return_value = 800  # MB, exceeds limit of 512
        
        self.worker_manager.integrated_workers = [
            {
                'worker': mock_worker,
                'worker_id': 'memory-heavy-worker',
                'memory_limit': 512
            }
        ]
        
        # Check memory usage
        memory_report = self.worker_manager.check_worker_memory_usage()
        
        # Verify memory report
        self.assertIn('workers_over_limit', memory_report)
        self.assertIn('total_memory_usage', memory_report)
        
        # Verify worker over limit is detected
        self.assertEqual(len(memory_report['workers_over_limit']), 1)
        over_limit_worker = memory_report['workers_over_limit'][0]
        self.assertEqual(over_limit_worker['worker_id'], 'memory-heavy-worker')
        self.assertEqual(over_limit_worker['memory_usage'], 800)
        self.assertEqual(over_limit_worker['memory_limit'], 512)
    
    def test_concurrent_worker_operations(self):
        """Test concurrent worker management operations"""
        # This test verifies thread safety of worker operations
        results = []
        errors = []
        
        def start_worker_operation():
            try:
                with patch('app.services.task.rq.rq_worker_manager.IntegratedRQWorker'):
                    result = self.worker_manager.scale_workers('test-queue', 1)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        def stop_worker_operation():
            try:
                result = self.worker_manager.stop_workers(graceful=True, timeout=1)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple concurrent operations
        threads = []
        for _ in range(3):
            thread1 = threading.Thread(target=start_worker_operation)
            thread2 = threading.Thread(target=stop_worker_operation)
            threads.extend([thread1, thread2])
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Concurrent operations failed: {errors}")


class TestIntegratedRQWorker(unittest.TestCase):
    """Test Integrated RQ Worker functionality"""
    
def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_app_context = Mock()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        # Mock Flask app context
        self.mock_app_context.__enter__ = Mock(return_value=self.mock_app_context)
        self.mock_app_context.__exit__ = Mock(return_value=None)
        
        # Mock queues
        self.queues = ['normal', 'low']
        self.worker_id = 'test-integrated-worker'
        
        # Initialize integrated worker
        with patch('app.services.task.rq.integrated_rq_worker.Worker') as mock_worker_class:
            self.mock_rq_worker = Mock(spec=Worker)
            mock_worker_class.return_value = self.mock_rq_worker
            
            self.integrated_worker = IntegratedRQWorker(
                self.queues,
                self.mock_redis,
                self.mock_app_context,
                self.mock_db_manager,
                self.worker_id
            )
    
    def test_integrated_worker_initialization(self):
        """Test IntegratedRQWorker initialization"""
        # Verify initialization
        self.assertEqual(self.integrated_worker.worker_id, self.worker_id)
        self.assertEqual(self.integrated_worker.app_context, self.mock_app_context)
        self.assertEqual(self.integrated_worker.db_manager, self.mock_db_manager)
        self.assertFalse(self.integrated_worker.running)
        self.assertIsNone(self.integrated_worker.thread)
    
    @patch('threading.Thread')
    def test_integrated_worker_start(self, mock_thread_class):
        """Test starting integrated worker"""
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Start worker
        self.integrated_worker.start()
        
        # Verify thread was created and started
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()
        self.assertTrue(self.integrated_worker.running)
        self.assertEqual(self.integrated_worker.thread, mock_thread)
    
    def test_integrated_worker_stop_graceful(self):
        """Test graceful stop of integrated worker"""
        # Mock running thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        self.integrated_worker.thread = mock_thread
        self.integrated_worker.running = True
        
        # Mock RQ worker
        self.mock_rq_worker.request_stop.return_value = None
        
        # Test graceful stop
        result = self.integrated_worker.stop(timeout=30)
        
        # Verify graceful stop was attempted
        self.mock_rq_worker.request_stop.assert_called_once()
        mock_thread.join.assert_called_with(timeout=30)
        self.assertFalse(self.integrated_worker.running)
    
    def test_integrated_worker_session_cleanup(self):
        """Test database session cleanup in worker"""
        # Mock session manager
        mock_session_manager = Mock(spec=WorkerSessionManager)
        self.integrated_worker.session_manager = mock_session_manager
        
        # Test session cleanup
        self.integrated_worker._cleanup_session()
        
        # Verify session cleanup was called
        mock_session_manager.close_session.assert_called_once()


if __name__ == '__main__':
    unittest.main()