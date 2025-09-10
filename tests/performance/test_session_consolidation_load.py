# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Load testing for session consolidation validation

Tests database session performance under concurrent load to validate
that the unified session system can handle production workloads.
"""

import unittest
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

from app.core.session.manager import UnifiedSessionManager
from app.core.database.core.database_manager import DatabaseManager
from models import User, PlatformConnection, UserSession

class SessionConsolidationLoadTest(unittest.TestCase):
    """Load tests for unified session management system"""
    
    def setUp(self):
        """Set up load test environment"""
        # Mock database manager for controlled testing
        self.mock_db_manager = MagicMock(spec=DatabaseManager)
        self.mock_db_session = MagicMock()
        self.mock_db_manager.get_session.return_value.__enter__.return_value = self.mock_db_session
        self.mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        self.session_manager = UnifiedSessionManager(self.mock_db_manager)
        
        # Test parameters
        self.concurrent_users = 20
        self.operations_per_user = 10
        self.max_acceptable_response_time = 0.5  # 500ms
        self.max_acceptable_avg_time = 0.1  # 100ms
    
    def test_concurrent_session_creation_load(self):
        """Test concurrent session creation under load"""
        
        def create_session_operation(user_id):
            """Single session creation operation"""
            start_time = time.time()
            
            try:
                # Mock user and platform
                mock_user = MagicMock(spec=User)
                mock_user.id = user_id
                mock_user.is_active = True
                
                mock_platform = MagicMock(spec=PlatformConnection)
                mock_platform.id = user_id + 1000  # Unique platform ID
                mock_platform.user_id = user_id
                mock_platform.is_active = True
                
                # Mock database responses
                self.mock_db_session.get.return_value = mock_user
                self.mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_platform
                
                # Create session
                session_id = self.session_manager.create_session(user_id, mock_platform.id)
                
                end_time = time.time()
                return {
                    'success': True,
                    'duration': end_time - start_time,
                    'session_id': session_id,
                    'user_id': user_id
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    'success': False,
                    'duration': end_time - start_time,
                    'error': str(e),
                    'user_id': user_id
                }
        
        # Run concurrent session creation
        with ThreadPoolExecutor(max_workers=self.concurrent_users) as executor:
            futures = [
                executor.submit(create_session_operation, user_id)
                for user_id in range(1, self.concurrent_users + 1)
            ]
            
            results = []
            for future in as_completed(futures, timeout=30):
                result = future.result()
                results.append(result)
        
        # Analyze results
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        # Assertions
        self.assertEqual(len(results), self.concurrent_users)
        self.assertGreaterEqual(len(successful_results), self.concurrent_users * 0.95)  # 95% success rate
        
        if successful_results:
            durations = [r['duration'] for r in successful_results]
            avg_duration = statistics.mean(durations)
            max_duration = max(durations)
            
            print(f"Session creation load test results:")
            print(f"  Successful operations: {len(successful_results)}/{self.concurrent_users}")
            print(f"  Average duration: {avg_duration:.3f}s")
            print(f"  Max duration: {max_duration:.3f}s")
            print(f"  Failed operations: {len(failed_results)}")
            
            # Performance assertions
            self.assertLess(avg_duration, self.max_acceptable_avg_time)
            self.assertLess(max_duration, self.max_acceptable_response_time)
    
    def test_concurrent_session_context_retrieval_load(self):
        """Test concurrent session context retrieval under load"""
        
        def get_context_operation(session_id, user_id):
            """Single context retrieval operation"""
            start_time = time.time()
            
            try:
                # Mock session context
                mock_user_session = MagicMock(spec=UserSession)
                mock_user_session.is_expired.return_value = False
                mock_user_session.to_context_dict.return_value = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'platform_connection_id': user_id + 1000
                }
                
                self.mock_db_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_user_session
                
                # Get context
                context = self.session_manager.get_session_context(session_id)
                
                end_time = time.time()
                return {
                    'success': context is not None,
                    'duration': end_time - start_time,
                    'session_id': session_id,
                    'user_id': user_id
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    'success': False,
                    'duration': end_time - start_time,
                    'error': str(e),
                    'session_id': session_id
                }
        
        # Generate test session IDs
        test_sessions = [(f'session-{i}', i) for i in range(1, self.concurrent_users + 1)]
        
        # Run concurrent context retrieval
        with ThreadPoolExecutor(max_workers=self.concurrent_users) as executor:
            futures = [
                executor.submit(get_context_operation, session_id, user_id)
                for session_id, user_id in test_sessions
            ]
            
            results = []
            for future in as_completed(futures, timeout=30):
                result = future.result()
                results.append(result)
        
        # Analyze results
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        # Assertions
        self.assertEqual(len(results), self.concurrent_users)
        self.assertGreaterEqual(len(successful_results), self.concurrent_users * 0.95)  # 95% success rate
        
        if successful_results:
            durations = [r['duration'] for r in successful_results]
            avg_duration = statistics.mean(durations)
            max_duration = max(durations)
            
            print(f"Context retrieval load test results:")
            print(f"  Successful operations: {len(successful_results)}/{self.concurrent_users}")
            print(f"  Average duration: {avg_duration:.3f}s")
            print(f"  Max duration: {max_duration:.3f}s")
            print(f"  Failed operations: {len(failed_results)}")
            
            # Performance assertions
            self.assertLess(avg_duration, self.max_acceptable_avg_time)
            self.assertLess(max_duration, self.max_acceptable_response_time)
    
    def test_mixed_session_operations_load(self):
        """Test mixed session operations under concurrent load"""
        
        def mixed_operations_worker(worker_id):
            """Worker performing mixed session operations"""
            results = []
            
            for op_id in range(self.operations_per_user):
                operation_type = op_id % 4  # Cycle through 4 operation types
                start_time = time.time()
                
                try:
                    if operation_type == 0:  # Create session
                        mock_user = MagicMock(spec=User)
                        mock_user.id = worker_id
                        mock_user.is_active = True
                        
                        mock_platform = MagicMock(spec=PlatformConnection)
                        mock_platform.id = worker_id + 1000
                        mock_platform.user_id = worker_id
                        mock_platform.is_active = True
                        
                        self.mock_db_session.get.return_value = mock_user
                        self.mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_platform
                        
                        session_id = self.session_manager.create_session(worker_id, mock_platform.id)
                        success = session_id is not None
                        
                    elif operation_type == 1:  # Get context
                        mock_user_session = MagicMock(spec=UserSession)
                        mock_user_session.is_expired.return_value = False
                        mock_user_session.to_context_dict.return_value = {
                            'session_id': f'session-{worker_id}-{op_id}',
                            'user_id': worker_id
                        }
                        
                        self.mock_db_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_user_session
                        
                        context = self.session_manager.get_session_context(f'session-{worker_id}-{op_id}')
                        success = context is not None
                        
                    elif operation_type == 2:  # Validate session
                        mock_user_session = MagicMock(spec=UserSession)
                        mock_user_session.is_expired.return_value = False
                        mock_user_session.to_context_dict.return_value = {
                            'session_id': f'session-{worker_id}-{op_id}',
                            'user_id': worker_id
                        }
                        
                        self.mock_db_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_user_session
                        
                        is_valid = self.session_manager.validate_session(f'session-{worker_id}-{op_id}')
                        success = is_valid
                        
                    else:  # Update activity
                        mock_user_session = MagicMock(spec=UserSession)
                        mock_user_session.is_expired.return_value = False
                        
                        self.mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_user_session
                        
                        updated = self.session_manager.update_session_activity(f'session-{worker_id}-{op_id}')
                        success = updated
                    
                    end_time = time.time()
                    results.append({
                        'success': success,
                        'duration': end_time - start_time,
                        'operation_type': operation_type,
                        'worker_id': worker_id,
                        'op_id': op_id
                    })
                    
                except Exception as e:
                    end_time = time.time()
                    results.append({
                        'success': False,
                        'duration': end_time - start_time,
                        'operation_type': operation_type,
                        'worker_id': worker_id,
                        'op_id': op_id,
                        'error': str(e)
                    })
            
            return results
        
        # Run mixed operations with multiple workers
        with ThreadPoolExecutor(max_workers=self.concurrent_users) as executor:
            futures = [
                executor.submit(mixed_operations_worker, worker_id)
                for worker_id in range(1, self.concurrent_users + 1)
            ]
            
            all_results = []
            for future in as_completed(futures, timeout=60):
                worker_results = future.result()
                all_results.extend(worker_results)
        
        # Analyze results
        successful_results = [r for r in all_results if r['success']]
        failed_results = [r for r in all_results if not r['success']]
        
        total_operations = self.concurrent_users * self.operations_per_user
        
        # Assertions
        self.assertEqual(len(all_results), total_operations)
        self.assertGreaterEqual(len(successful_results), total_operations * 0.90)  # 90% success rate
        
        if successful_results:
            durations = [r['duration'] for r in successful_results]
            avg_duration = statistics.mean(durations)
            max_duration = max(durations)
            
            # Group by operation type
            by_operation = {}
            for result in successful_results:
                op_type = result['operation_type']
                if op_type not in by_operation:
                    by_operation[op_type] = []
                by_operation[op_type].append(result['duration'])
            
            print(f"Mixed operations load test results:")
            print(f"  Total operations: {len(all_results)}")
            print(f"  Successful operations: {len(successful_results)}")
            print(f"  Failed operations: {len(failed_results)}")
            print(f"  Overall average duration: {avg_duration:.3f}s")
            print(f"  Overall max duration: {max_duration:.3f}s")
            
            operation_names = ['Create', 'GetContext', 'Validate', 'UpdateActivity']
            for op_type, durations in by_operation.items():
                avg_op_duration = statistics.mean(durations)
                print(f"  {operation_names[op_type]} avg: {avg_op_duration:.3f}s ({len(durations)} ops)")
            
            # Performance assertions
            self.assertLess(avg_duration, self.max_acceptable_avg_time)
            self.assertLess(max_duration, self.max_acceptable_response_time)
    
    def test_session_cleanup_performance(self):
        """Test session cleanup performance under load"""
        
        # Mock many expired sessions
        num_expired_sessions = 100
        mock_expired_sessions = []
        
        for i in range(num_expired_sessions):
            mock_session = MagicMock(spec=UserSession)
            mock_session.id = i
            mock_expired_sessions.append(mock_session)
        
        self.mock_db_session.query.return_value.filter.return_value.all.return_value = mock_expired_sessions
        
        # Time the cleanup operation
        start_time = time.time()
        count = self.session_manager.cleanup_expired_sessions()
        end_time = time.time()
        
        cleanup_duration = end_time - start_time
        
        # Assertions
        self.assertEqual(count, num_expired_sessions)
        self.assertLess(cleanup_duration, 1.0)  # Should complete within 1 second
        
        # Verify all sessions were deleted
        self.assertEqual(self.mock_db_session.delete.call_count, num_expired_sessions)
        self.mock_db_session.commit.assert_called()
        
        print(f"Session cleanup performance:")
        print(f"  Cleaned up {count} sessions in {cleanup_duration:.3f}s")
        print(f"  Rate: {count/cleanup_duration:.1f} sessions/second")
    
    def test_database_connection_pool_stress(self):
        """Test database connection pool under stress"""
        
        def connection_stress_worker(worker_id):
            """Worker that stresses database connections"""
            results = []
            
            for i in range(5):  # 5 operations per worker
                start_time = time.time()
                
                try:
                    # This should use the connection pool
                    with self.session_manager.get_db_session() as db_session:
                        # Simulate database work
                        time.sleep(0.001)  # 1ms simulated work
                        
                        # Mock a simple query
                        db_session.execute.return_value = MagicMock()
                    
                    end_time = time.time()
                    results.append({
                        'success': True,
                        'duration': end_time - start_time,
                        'worker_id': worker_id,
                        'operation': i
                    })
                    
                except Exception as e:
                    end_time = time.time()
                    results.append({
                        'success': False,
                        'duration': end_time - start_time,
                        'worker_id': worker_id,
                        'operation': i,
                        'error': str(e)
                    })
            
            return results
        
        # Run many concurrent workers to stress connection pool
        num_workers = 50
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(connection_stress_worker, worker_id)
                for worker_id in range(num_workers)
            ]
            
            all_results = []
            for future in as_completed(futures, timeout=30):
                worker_results = future.result()
                all_results.extend(worker_results)
        
        # Analyze results
        successful_results = [r for r in all_results if r['success']]
        failed_results = [r for r in all_results if not r['success']]
        
        total_operations = num_workers * 5
        
        # Assertions
        self.assertEqual(len(all_results), total_operations)
        self.assertGreaterEqual(len(successful_results), total_operations * 0.95)  # 95% success rate
        
        if successful_results:
            durations = [r['duration'] for r in successful_results]
            avg_duration = statistics.mean(durations)
            max_duration = max(durations)
            
            print(f"Connection pool stress test results:")
            print(f"  Total operations: {len(all_results)}")
            print(f"  Successful operations: {len(successful_results)}")
            print(f"  Failed operations: {len(failed_results)}")
            print(f"  Average duration: {avg_duration:.3f}s")
            print(f"  Max duration: {max_duration:.3f}s")
            
            # Performance assertions
            self.assertLess(avg_duration, 0.05)  # Should be very fast with mocking
            self.assertLess(max_duration, 0.2)

if __name__ == '__main__':
    unittest.main()