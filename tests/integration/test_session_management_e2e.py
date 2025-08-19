#!/usr/bin/env python3
"""
End-to-End Session Management Integration Tests

Comprehensive tests for complete session lifecycle including:
- User authentication and session creation
- Platform switching and cross-tab synchronization
- Session expiration and cleanup
- Error handling and recovery
"""

import unittest
import asyncio
import time
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_login import login_user, logout_user

from database import DatabaseManager
from models import User, PlatformConnection, UserRole
from unified_session_manager import UnifiedSessionManager as SessionManager
from request_scoped_session_manager import RequestScopedSessionManager
from config import Config


class SessionManagementE2ETest(unittest.TestCase):
    """End-to-end tests for session management system"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = UnifiedSessionManager(self.db_manager)
        self.request_session_manager = RequestScopedSessionManager(self.db_manager)
        
        # Create test Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        
        # Create test user and platform
        with self.db_manager.get_session() as session:
            self.test_user = User(
                username='testuser',
                email='test@test.com',
                role=UserRole.USER,
                is_active=True
            )
            self.test_user.set_password('testpass')
            session.add(self.test_user)
            session.commit()
            
            self.test_platform = PlatformConnection(
                user_id=self.test_user.id,
                name='Test Platform',
                platform_type='mastodon',
                instance_url='https://test.social',
                username='testuser',
                access_token='test-token',
                is_default=True,
                is_active=True
            )
            session.add(self.test_platform)
            session.commit()
    
    def tearDown(self):
        """Clean up test environment"""
        with self.db_manager.get_session() as session:
            session.query(PlatformConnection).delete()
            session.query(User).delete()
            session.commit()
    
    def test_complete_session_lifecycle(self):
        """Test complete session lifecycle from login to logout"""
        with self.app.test_client() as client:
            with self.app.app_context():
                # 1. User login creates session
                session_id = self.session_manager.create_session(
                    self.test_user.id, 
                    self.test_platform.id
                )
                self.assertIsNotNone(session_id)
                
                # 2. Validate session exists and is active
                session_valid = self.session_manager.validate_session(
                    session_id, 
                    self.test_user.id
                )
                self.assertTrue(session_valid)
                
                # 3. Update platform context
                update_success = self.session_manager.update_platform_context(
                    session_id, 
                    self.test_platform.id
                )
                self.assertTrue(update_success)
                
                # 4. Session cleanup on logout
                cleanup_success = self.session_manager._cleanup_session(session_id)
                self.assertTrue(cleanup_success)
                
                # 5. Verify session is no longer valid
                session_valid_after = self.session_manager.validate_session(
                    session_id, 
                    self.test_user.id
                )
                self.assertFalse(session_valid_after)
    
    def test_cross_tab_synchronization_simulation(self):
        """Simulate cross-tab session synchronization"""
        # Create multiple sessions for same user (simulating multiple tabs)
        session_ids = []
        for i in range(3):
            session_id = self.session_manager.create_session(
                self.test_user.id, 
                self.test_platform.id
            )
            session_ids.append(session_id)
        
        # Verify all sessions are valid
        for session_id in session_ids:
            self.assertTrue(
                self.session_manager.validate_session(session_id, self.test_user.id)
            )
        
        # Simulate platform switch in one tab
        new_platform = PlatformConnection(
            user_id=self.test_user.id,
            name='New Platform',
            platform_type='pixelfed',
            instance_url='https://new.social',
            username='testuser2',
            access_token='new-token',
            is_default=False,
            is_active=True
        )
        
        with self.db_manager.get_session() as session:
            session.add(new_platform)
            session.commit()
            new_platform_id = new_platform.id
        
        # Update one session's platform context
        update_success = self.session_manager.update_platform_context(
            session_ids[0], 
            new_platform_id
        )
        self.assertTrue(update_success)
        
        # Verify other sessions remain valid but with original platform
        for session_id in session_ids[1:]:
            self.assertTrue(
                self.session_manager.validate_session(session_id, self.test_user.id)
            )
        
        # Cleanup
        for session_id in session_ids:
            self.session_manager._cleanup_session(session_id)
    
    def test_session_expiration_handling(self):
        """Test session expiration and cleanup"""
        # Create session with short expiration
        session_id = self.session_manager.create_session(
            self.test_user.id, 
            self.test_platform.id
        )
        
        # Manually expire session in database
        with self.db_manager.get_session() as session:
            from models import UserSession
            user_session = session.query(UserSession).filter_by(
                session_id=session_id
            ).first()
            if user_session:
                user_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
                session.commit()
        
        # Verify session is no longer valid
        session_valid = self.session_manager.validate_session(
            session_id, 
            self.test_user.id
        )
        self.assertFalse(session_valid)
        
        # Run cleanup and verify expired session is removed
        cleanup_count = self.session_manager.cleanup_expired_sessions()
        self.assertGreaterEqual(cleanup_count, 1)
    
    def test_error_recovery_scenarios(self):
        """Test error handling and recovery scenarios"""
        # Test invalid session ID
        invalid_session_valid = self.session_manager.validate_session(
            'invalid-session-id', 
            self.test_user.id
        )
        self.assertFalse(invalid_session_valid)
        
        # Test invalid user ID
        session_id = self.session_manager.create_session(
            self.test_user.id, 
            self.test_platform.id
        )
        
        invalid_user_valid = self.session_manager.validate_session(
            session_id, 
            99999  # Non-existent user ID
        )
        self.assertFalse(invalid_user_valid)
        
        # Test database connection failure simulation
        with patch.object(self.db_manager, 'get_session') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            # Should handle gracefully without crashing
            try:
                result = self.session_manager.validate_session(session_id, self.test_user.id)
                self.assertFalse(result)  # Should return False on error
            except Exception:
                self.fail("Session manager should handle database errors gracefully")
        
        # Cleanup
        self.session_manager._cleanup_session(session_id)
    
    def test_concurrent_session_operations(self):
        """Test concurrent session operations"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def create_session_worker():
            try:
                session_id = self.session_manager.create_session(
                    self.test_user.id, 
                    self.test_platform.id
                )
                results.put(('create', session_id is not None, session_id))
            except Exception as e:
                results.put(('create', False, str(e)))
        
        def validate_session_worker(session_id):
            try:
                valid = self.session_manager.validate_session(
                    session_id, 
                    self.test_user.id
                )
                results.put(('validate', valid, session_id))
            except Exception as e:
                results.put(('validate', False, str(e)))
        
        # Create session first
        main_session_id = self.session_manager.create_session(
            self.test_user.id, 
            self.test_platform.id
        )
        
        # Start concurrent operations
        threads = []
        
        # Multiple session creation threads
        for _ in range(5):
            thread = threading.Thread(target=create_session_worker)
            threads.append(thread)
            thread.start()
        
        # Multiple validation threads
        for _ in range(5):
            thread = threading.Thread(target=validate_session_worker, args=(main_session_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Collect results
        create_successes = 0
        validate_successes = 0
        session_ids_to_cleanup = [main_session_id]
        
        while not results.empty():
            operation, success, data = results.get()
            if operation == 'create' and success:
                create_successes += 1
                if isinstance(data, str) and data != main_session_id:
                    session_ids_to_cleanup.append(data)
            elif operation == 'validate' and success:
                validate_successes += 1
        
        # Verify concurrent operations succeeded
        self.assertGreaterEqual(create_successes, 3)  # At least 3 out of 5
        self.assertGreaterEqual(validate_successes, 3)  # At least 3 out of 5
        
        # Cleanup all created sessions
        for session_id in session_ids_to_cleanup:
            if session_id:
                self.session_manager._cleanup_session(session_id)
    



class SessionManagementLoadTest(unittest.TestCase):
    """Load testing for session management system"""
    
    def setUp(self):
        """Set up load test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create test users and platforms
        self.test_users = []
        self.test_platforms = []
        
        with self.db_manager.get_session() as session:
            for i in range(10):  # Create 10 test users
                user = User(
                    username=f'loadtest_user_{i}',
                    email=f'loadtest_{i}@test.com',
                    role=UserRole.USER,
                    is_active=True
                )
                user.set_password('testpass')
                session.add(user)
                session.commit()
                self.test_users.append(user)
                
                platform = PlatformConnection(
                    user_id=user.id,
                    name=f'Load Test Platform {i}',
                    platform_type='mastodon',
                    instance_url=f'https://test{i}.social',
                    username=f'loaduser{i}',
                    access_token=f'token-{i}',
                    is_default=True,
                    is_active=True
                )
                session.add(platform)
                session.commit()
                self.test_platforms.append(platform)
    
    def tearDown(self):
        """Clean up load test environment"""
        with self.db_manager.get_session() as session:
            session.query(PlatformConnection).filter(
                PlatformConnection.name.like('Load Test Platform%')
            ).delete(synchronize_session=False)
            session.query(User).filter(
                User.username.like('loadtest_user_%')
            ).delete(synchronize_session=False)
            session.commit()
    
    def test_concurrent_session_creation_load(self):
        """Test concurrent session creation under load"""
        import threading
        import time
        
        results = []
        start_time = time.time()
        
        def create_sessions_worker(user_index):
            user = self.test_users[user_index]
            platform = self.test_platforms[user_index]
            
            session_ids = []
            worker_start = time.time()
            
            # Create 10 sessions per user
            for _ in range(10):
                try:
                    session_id = self.session_manager.create_session(
                        user.id, platform.id
                    )
                    if session_id:
                        session_ids.append(session_id)
                except Exception as e:
                    pass  # Count failures
            
            worker_end = time.time()
            results.append({
                'user_index': user_index,
                'sessions_created': len(session_ids),
                'duration': worker_end - worker_start,
                'session_ids': session_ids
            })
        
        # Start concurrent workers
        threads = []
        for i in range(len(self.test_users)):
            thread = threading.Thread(target=create_sessions_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        total_sessions = sum(r['sessions_created'] for r in results)
        avg_sessions_per_user = total_sessions / len(self.test_users)
        sessions_per_second = total_sessions / total_duration
        
        # Cleanup created sessions
        for result in results:
            for session_id in result['session_ids']:
                try:
                    self.session_manager._cleanup_session(session_id)
                except:
                    pass
        
        # Performance assertions
        self.assertGreaterEqual(avg_sessions_per_user, 8)  # At least 8/10 success rate
        self.assertGreaterEqual(sessions_per_second, 10)   # At least 10 sessions/sec
        self.assertLessEqual(total_duration, 15)           # Complete within 15 seconds
    
    def test_session_validation_performance(self):
        """Test session validation performance under load"""
        # Create sessions for all test users
        session_ids = []
        for i, (user, platform) in enumerate(zip(self.test_users, self.test_platforms)):
            session_id = self.session_manager.create_session(user.id, platform.id)
            if session_id:
                session_ids.append((session_id, user.id))
        
        # Perform validation load test
        import threading
        import time
        
        validation_results = []
        start_time = time.time()
        
        def validation_worker():
            worker_start = time.time()
            validations = 0
            
            # Perform 100 validations
            for _ in range(100):
                for session_id, user_id in session_ids[:5]:  # Test first 5 sessions
                    try:
                        valid = self.session_manager.validate_session(session_id, user_id)
                        validations += 1
                    except:
                        pass
            
            worker_end = time.time()
            validation_results.append({
                'validations': validations,
                'duration': worker_end - worker_start
            })
        
        # Start validation workers
        threads = []
        for _ in range(5):  # 5 concurrent validation workers
            thread = threading.Thread(target=validation_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=20)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze performance
        total_validations = sum(r['validations'] for r in validation_results)
        validations_per_second = total_validations / total_duration
        
        # Cleanup
        for session_id, user_id in session_ids:
            try:
                self.session_manager._cleanup_session(session_id)
            except:
                pass
        
        # Performance assertions
        self.assertGreaterEqual(validations_per_second, 100)  # At least 100 validations/sec
        self.assertLessEqual(total_duration, 15)              # Complete within 15 seconds


if __name__ == '__main__':
    # Run end-to-end tests
    e2e_suite = unittest.TestLoader().loadTestsFromTestCase(SessionManagementE2ETest)
    e2e_runner = unittest.TextTestRunner(verbosity=2)
    e2e_result = e2e_runner.run(e2e_suite)
    
    # Run load tests
    load_suite = unittest.TestLoader().loadTestsFromTestCase(SessionManagementLoadTest)
    load_runner = unittest.TextTestRunner(verbosity=2)
    load_result = load_runner.run(load_suite)
    
    # Summary
    total_tests = e2e_result.testsRun + load_result.testsRun
    total_failures = len(e2e_result.failures) + len(load_result.failures)
    total_errors = len(e2e_result.errors) + len(load_result.errors)
    
    print(f"\n{'='*60}")
    print(f"SESSION MANAGEMENT TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_tests - total_failures - total_errors}")
    print(f"Failed: {total_failures}")
    print(f"Errors: {total_errors}")
    print(f"Success Rate: {((total_tests - total_failures - total_errors) / total_tests * 100):.1f}%")