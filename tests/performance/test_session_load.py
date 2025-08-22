# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance and load tests for session management system.

Tests concurrent session operations, database connection pool efficiency,
and cross-tab synchronization performance metrics.
Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import unittest
import tempfile
import os
import time
import threading
import concurrent.futures
from datetime import datetime, timezone
from statistics import mean, median

from config import Config
from database import DatabaseManager
from models import User, PlatformConnection, UserSession, UserRole
from unified_session_manager import UnifiedSessionManager as SessionManager
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

class TestConcurrentSessionOperations(unittest.TestCase):
    """Test concurrent session operations under load (Requirements 7.1, 7.2)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        self.db_manager = DatabaseManager(self.config)
        self.db_manager.create_tables()
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_load_user",
            role=UserRole.REVIEWER
        )
        
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_concurrent_session_creation(self):
        """Test concurrent session creation performance"""
        num_threads = 10
        sessions_per_thread = 5
        results = []
        
        def create_sessions():
            thread_results = []
            for _ in range(sessions_per_thread):
                start_time = time.time()
                session_id = self.session_manager.create_session(self.test_user.id)
                end_time = time.time()
                
                thread_results.append({
                    'session_id': session_id,
                    'duration': end_time - start_time,
                    'success': session_id is not None
                })
                time.sleep(0.1)  # Avoid suspicious activity detection
            return thread_results
        
        # Run concurrent session creation
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_sessions) for _ in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())
        
        # Analyze results
        successful_operations = [r for r in results if r['success']]
        durations = [r['duration'] for r in successful_operations]
        
        self.assertGreater(len(successful_operations), 0)
        self.assertLess(mean(durations), 1.0)  # Average under 1 second
        self.assertLess(max(durations), 5.0)   # Max under 5 seconds
    
    def test_concurrent_session_validation(self):
        """Test concurrent session validation performance"""
        # Create sessions first
        session_ids = []
        for i in range(20):
            session_id = self.session_manager.create_session(self.test_user.id)
            session_ids.append(session_id)
            time.sleep(0.05)
        
        def validate_sessions(session_batch):
            results = []
            for session_id in session_batch:
                start_time = time.time()
                is_valid = self.session_manager.validate_session(session_id, self.test_user.id)
                end_time = time.time()
                
                results.append({
                    'session_id': session_id,
                    'duration': end_time - start_time,
                    'valid': is_valid
                })
            return results
        
        # Split sessions into batches for concurrent validation
        batch_size = 5
        batches = [session_ids[i:i+batch_size] for i in range(0, len(session_ids), batch_size)]
        
        all_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(validate_sessions, batch) for batch in batches]
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        
        # Analyze performance
        durations = [r['duration'] for r in all_results]
        valid_count = sum(1 for r in all_results if r['valid'])
        
        self.assertGreater(valid_count, 0)
        self.assertLess(mean(durations), 0.5)  # Average under 500ms
        self.assertLess(max(durations), 2.0)   # Max under 2 seconds
    
    def test_concurrent_platform_switching(self):
        """Test concurrent platform switching performance"""
        if len(self.test_user.platform_connections) < 2:
            self.skipTest("Need at least 2 platforms for switching test")
        
        # Create sessions
        session_ids = []
        for i in range(10):
            session_id = self.session_manager.create_session(self.test_user.id)
            session_ids.append(session_id)
            time.sleep(0.1)
        
        def switch_platforms(session_batch):
            results = []
            platforms = self.test_user.platform_connections
            
            for i, session_id in enumerate(session_batch):
                platform = platforms[i % len(platforms)]
                start_time = time.time()
                success = self.session_manager.update_platform_context(session_id, platform.id)
                end_time = time.time()
                
                results.append({
                    'session_id': session_id,
                    'platform_id': platform.id,
                    'duration': end_time - start_time,
                    'success': success
                })
            return results
        
        # Split into batches for concurrent switching
        batch_size = 3
        batches = [session_ids[i:i+batch_size] for i in range(0, len(session_ids), batch_size)]
        
        all_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(switch_platforms, batch) for batch in batches]
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        
        # Analyze performance
        successful_switches = [r for r in all_results if r['success']]
        durations = [r['duration'] for r in successful_switches]
        
        self.assertGreater(len(successful_switches), 0)
        self.assertLess(mean(durations), 0.1)  # Sub-100ms requirement
        self.assertLess(max(durations), 0.5)   # Max under 500ms

class TestDatabaseConnectionPoolEfficiency(unittest.TestCase):
    """Test database connection pool efficiency (Requirements 7.3, 7.4)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        self.db_manager = DatabaseManager(self.config)
        self.db_manager.create_tables()
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_pool_user",
            role=UserRole.REVIEWER
        )
        
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_connection_pool_under_load(self):
        """Test connection pool performance under concurrent load"""
        num_operations = 50
        results = []
        
        def database_operation():
            start_time = time.time()
            try:
                with self.session_manager.get_db_session() as db_session:
                    # Simulate database work
                    user_count = db_session.query(User).count()
                    session_count = db_session.query(UserSession).count()
                    
                end_time = time.time()
                return {
                    'duration': end_time - start_time,
                    'success': True,
                    'user_count': user_count,
                    'session_count': session_count
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'duration': end_time - start_time,
                    'success': False,
                    'error': str(e)
                }
        
        # Run concurrent database operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(database_operation) for _ in range(num_operations)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        # Analyze connection pool efficiency
        successful_ops = [r for r in results if r['success']]
        durations = [r['duration'] for r in successful_ops]
        
        self.assertGreater(len(successful_ops), num_operations * 0.9)  # 90% success rate
        self.assertLess(mean(durations), 0.5)  # Average under 500ms
        self.assertLess(max(durations), 2.0)   # Max under 2 seconds
    
    def test_session_context_manager_efficiency(self):
        """Test session context manager efficiency under load"""
        num_contexts = 30
        results = []
        
        def context_operation():
            start_time = time.time()
            try:
                with self.session_manager.get_db_session() as db_session:
                    # Multiple operations in same context
                    users = db_session.query(User).limit(5).all()
                    sessions = db_session.query(UserSession).limit(10).all()
                    platforms = db_session.query(PlatformConnection).limit(5).all()
                    
                end_time = time.time()
                return {
                    'duration': end_time - start_time,
                    'success': True,
                    'operations': 3
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'duration': end_time - start_time,
                    'success': False,
                    'error': str(e)
                }
        
        # Run concurrent context operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(context_operation) for _ in range(num_contexts)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        # Analyze context manager efficiency
        successful_ops = [r for r in results if r['success']]
        durations = [r['duration'] for r in successful_ops]
        
        self.assertGreater(len(successful_ops), num_contexts * 0.95)  # 95% success rate
        self.assertLess(mean(durations), 0.3)  # Average under 300ms
        self.assertLess(median(durations), 0.2)  # Median under 200ms

class TestCrossTabSynchronizationPerformance(unittest.TestCase):
    """Test cross-tab synchronization performance metrics (Requirements 7.1, 7.2, 7.5)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        self.db_manager = DatabaseManager(self.config)
        self.db_manager.create_tables()
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_sync_user",
            role=UserRole.REVIEWER
        )
        
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_session_state_api_performance(self):
        """Test session state API performance under load"""
        # Create sessions
        session_ids = []
        for i in range(15):
            session_id = self.session_manager.create_session(self.test_user.id)
            session_ids.append(session_id)
            time.sleep(0.05)
        
        def api_call_simulation():
            """Simulate session state API call"""
            start_time = time.time()
            try:
                # Simulate what the API does
                context = self.session_manager.get_session_context(session_ids[0])
                if context:
                    # Simulate JSON serialization time
                    import json
                    data = {
                        'user': {'id': context['user_id']},
                        'platform': {'id': context.get('platform_connection_id')},
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    json.dumps(data)
                
                end_time = time.time()
                return {
                    'duration': end_time - start_time,
                    'success': context is not None
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'duration': end_time - start_time,
                    'success': False,
                    'error': str(e)
                }
        
        # Run concurrent API calls
        num_calls = 25
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(api_call_simulation) for _ in range(num_calls)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        # Analyze API performance
        successful_calls = [r for r in results if r['success']]
        durations = [r['duration'] for r in successful_calls]
        
        self.assertGreater(len(successful_calls), num_calls * 0.9)  # 90% success rate
        self.assertLess(mean(durations), 0.2)  # Average under 200ms
        self.assertLess(max(durations), 1.0)   # Max under 1 second
    
    def test_concurrent_session_cleanup_performance(self):
        """Test session cleanup performance under concurrent operations"""
        # Create many sessions
        session_ids = []
        for i in range(30):
            session_id = self.session_manager.create_session(self.test_user.id)
            session_ids.append(session_id)
            time.sleep(0.03)
        
        def cleanup_operation():
            start_time = time.time()
            try:
                # Cleanup some sessions (keeping one active)
                cleaned = self.session_manager.cleanup_user_sessions(
                    self.test_user.id, 
                    keep_current=session_ids[0]
                )
                end_time = time.time()
                return {
                    'duration': end_time - start_time,
                    'success': True,
                    'cleaned_count': cleaned
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'duration': end_time - start_time,
                    'success': False,
                    'error': str(e)
                }
        
        # Run concurrent cleanup operations
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(cleanup_operation) for _ in range(3)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        # Analyze cleanup performance
        successful_cleanups = [r for r in results if r['success']]
        durations = [r['duration'] for r in successful_cleanups]
        
        self.assertGreater(len(successful_cleanups), 0)
        if durations:  # Only check if we have successful operations
            self.assertLess(mean(durations), 2.0)  # Average under 2 seconds
            self.assertLess(max(durations), 5.0)   # Max under 5 seconds
    
    def test_memory_usage_under_load(self):
        """Test memory usage during high session load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many sessions
        session_ids = []
        for i in range(50):
            session_id = self.session_manager.create_session(self.test_user.id)
            session_ids.append(session_id)
            time.sleep(0.02)
        
        # Perform operations
        for session_id in session_ids[:20]:
            context = self.session_manager.get_session_context(session_id)
            if context and len(self.test_user.platform_connections) > 0:
                self.session_manager.update_platform_context(
                    session_id, 
                    self.test_user.platform_connections[0].id
                )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (under 50MB for this test)
        self.assertLess(memory_increase, 50)
        
        # Cleanup
        self.session_manager.cleanup_all_user_sessions(self.test_user.id)

class TestPerformanceMetrics(unittest.TestCase):
    """Test performance metrics collection (Requirements 7.5)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        self.db_manager = DatabaseManager(self.config)
        self.db_manager.create_tables()
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_metrics_user",
            role=UserRole.REVIEWER
        )
        
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_operation_timing_metrics(self):
        """Test collection of operation timing metrics"""
        operations = []
        
        # Perform various operations and collect timing
        for i in range(10):
            # Session creation
            start_time = time.time()
            session_id = self.session_manager.create_session(self.test_user.id)
            create_duration = time.time() - start_time
            
            # Session validation
            start_time = time.time()
            is_valid = self.session_manager.validate_session(session_id, self.test_user.id)
            validate_duration = time.time() - start_time
            
            # Context retrieval
            start_time = time.time()
            context = self.session_manager.get_session_context(session_id)
            context_duration = time.time() - start_time
            
            operations.append({
                'create_duration': create_duration,
                'validate_duration': validate_duration,
                'context_duration': context_duration,
                'session_id': session_id
            })
            
            time.sleep(0.1)
        
        # Analyze metrics
        create_times = [op['create_duration'] for op in operations]
        validate_times = [op['validate_duration'] for op in operations]
        context_times = [op['context_duration'] for op in operations]
        
        # Performance assertions
        self.assertLess(mean(create_times), 0.5)    # Average creation under 500ms
        self.assertLess(mean(validate_times), 0.1)  # Average validation under 100ms
        self.assertLess(mean(context_times), 0.1)   # Average context under 100ms
        
        # Consistency checks
        self.assertLess(max(create_times) - min(create_times), 1.0)  # Consistent performance
    
    def test_throughput_metrics(self):
        """Test throughput metrics under sustained load"""
        start_time = time.time()
        operations_completed = 0
        test_duration = 2.0  # 2 seconds
        
        while time.time() - start_time < test_duration:
            session_id = self.session_manager.create_session(self.test_user.id)
            if session_id:
                operations_completed += 1
            time.sleep(0.05)  # Small delay to avoid overwhelming
        
        actual_duration = time.time() - start_time
        throughput = operations_completed / actual_duration
        
        # Should handle at least 10 operations per second
        self.assertGreater(throughput, 10)
        self.assertGreater(operations_completed, 15)

if __name__ == '__main__':
    unittest.main()