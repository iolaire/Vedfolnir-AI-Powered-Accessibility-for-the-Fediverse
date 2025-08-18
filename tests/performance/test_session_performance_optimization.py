#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test session performance optimizations
"""

import unittest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from config import Config
from database import DatabaseManager
from session_performance_optimizer import SessionPerformanceOptimizer, SessionCache, get_session_optimizer
from models import User, UserSession, PlatformConnection, UserRole
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user


class TestSessionCache(unittest.TestCase):
    """Test session caching functionality"""
    
    def setUp(self):
        self.cache = SessionCache()
    
    def test_cache_basic_operations(self):
        """Test basic cache operations"""
        session_id = "test_session_123"
        context = {
            'user_id': 1,
            'platform_id': 1,
            'session_id': session_id
        }
        
        # Test cache miss
        self.assertIsNone(self.cache.get(session_id))
        
        # Test cache set and hit
        self.cache.set(session_id, context)
        cached_context = self.cache.get(session_id)
        self.assertEqual(cached_context, context)
        
        # Test cache size
        self.assertEqual(self.cache.size(), 1)
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        self.cache._cache_ttl = 0.1  # 100ms TTL for testing
        
        session_id = "test_session_ttl"
        context = {'user_id': 1}
        
        self.cache.set(session_id, context)
        self.assertIsNotNone(self.cache.get(session_id))
        
        # Wait for TTL to expire
        time.sleep(0.2)
        self.assertIsNone(self.cache.get(session_id))
    
    def test_cache_invalidation(self):
        """Test cache invalidation"""
        session_id = "test_session_invalidate"
        context = {'user_id': 1}
        
        self.cache.set(session_id, context)
        self.assertIsNotNone(self.cache.get(session_id))
        
        self.cache.invalidate(session_id)
        self.assertIsNone(self.cache.get(session_id))
    
    def test_cache_clear(self):
        """Test cache clear"""
        self.cache.set("session1", {'user_id': 1})
        self.cache.set("session2", {'user_id': 2})
        self.assertEqual(self.cache.size(), 2)
        
        self.cache.clear()
        self.assertEqual(self.cache.size(), 0)


class TestSessionPerformanceOptimizer(unittest.TestCase):
    """Test session performance optimizer"""
    
    def setUp(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.optimizer = SessionPerformanceOptimizer(self.db_manager)
        
        # Create test user with platforms
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_perf_user",
            role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        cleanup_test_user(self.user_helper)
    
    def test_apply_database_optimizations(self):
        """Test database optimization application"""
        results = self.optimizer.apply_database_optimizations()
        
        self.assertEqual(results['status'], 'success')
        self.assertIsInstance(results['indexes_created'], int)
        self.assertIsInstance(results['indexes_checked'], int)
        self.assertIsInstance(results['errors'], list)
    
    def test_cached_session_context(self):
        """Test cached session context retrieval"""
        # Create a test session
        from unified_session_manager import UnifiedSessionManager as SessionManager
        session_manager = UnifiedSessionManager(self.db_manager)
        
        session_id = session_manager.create_user_session(
            self.test_user.id,
            self.test_user.platform_connections[0].id
        )
        
        # First call should fetch from database
        context1 = self.optimizer.get_cached_session_context(session_id)
        self.assertIsNotNone(context1)
        self.assertEqual(context1['user_id'], self.test_user.id)
        
        # Second call should use cache
        context2 = self.optimizer.get_cached_session_context(session_id)
        self.assertEqual(context1, context2)
        
        # Verify cache was used
        self.assertGreater(self.optimizer.request_cache.size(), 0)
    
    def test_optimized_session_validation(self):
        """Test optimized session validation"""
        from unified_session_manager import UnifiedSessionManager as SessionManager
        session_manager = UnifiedSessionManager(self.db_manager)
        
        session_id = session_manager.create_user_session(
            self.test_user.id,
            self.test_user.platform_connections[0].id
        )
        
        # Valid session should pass
        self.assertTrue(
            self.optimizer.validate_session_optimized(session_id, self.test_user.id)
        )
        
        # Invalid user ID should fail
        self.assertFalse(
            self.optimizer.validate_session_optimized(session_id, 99999)
        )
        
        # Invalid session ID should fail
        self.assertFalse(
            self.optimizer.validate_session_optimized("invalid_session", self.test_user.id)
        )
    
    def test_optimized_session_cleanup(self):
        """Test optimized session cleanup"""
        from unified_session_manager import UnifiedSessionManager as SessionManager
        session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create test sessions
        session_ids = []
        for i in range(3):
            session_id = session_manager.create_user_session(
                self.test_user.id,
                self.test_user.platform_connections[0].id
            )
            session_ids.append(session_id)
        
        # Manually expire sessions by updating expires_at
        with self.db_manager.get_session() as db_session:
            expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
            db_session.query(UserSession).filter(
                UserSession.session_id.in_(session_ids)
            ).update({
                'expires_at': expired_time
            }, synchronize_session=False)
            db_session.commit()
        
        # Run cleanup
        cleaned_count = self.optimizer.cleanup_expired_sessions_optimized(batch_size=10)
        self.assertEqual(cleaned_count, 3)
        
        # Verify sessions were removed
        with self.db_manager.get_session() as db_session:
            remaining_sessions = db_session.query(UserSession).filter(
                UserSession.session_id.in_(session_ids)
            ).count()
            self.assertEqual(remaining_sessions, 0)
    
    def test_optimized_user_sessions(self):
        """Test optimized user session retrieval"""
        from unified_session_manager import UnifiedSessionManager as SessionManager
        session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create multiple sessions
        session_ids = []
        for i in range(2):
            session_id = session_manager.create_user_session(
                self.test_user.id,
                self.test_user.platform_connections[0].id
            )
            session_ids.append(session_id)
        
        # Get user sessions
        sessions = self.optimizer.get_user_sessions_optimized(self.test_user.id)
        
        self.assertEqual(len(sessions), 2)
        for session_info in sessions:
            self.assertIn('session_id', session_info)
            self.assertIn('platform_id', session_info)
            self.assertIn('created_at', session_info)
            self.assertIn('is_expired', session_info)
    
    def test_session_activity_update_throttling(self):
        """Test session activity update throttling"""
        from unified_session_manager import UnifiedSessionManager as SessionManager
        session_manager = UnifiedSessionManager(self.db_manager)
        
        session_id = session_manager.create_user_session(
            self.test_user.id,
            self.test_user.platform_connections[0].id
        )
        
        # First update should succeed
        result1 = self.optimizer.update_session_activity_optimized(session_id)
        self.assertTrue(result1)
        
        # Immediate second update should be throttled (return True but not update DB)
        with patch('flask.g') as mock_g:
            # Simulate Flask g context
            mock_g.configure_mock(**{f'activity_update_{session_id}': datetime.now(timezone.utc)})
            result2 = self.optimizer.update_session_activity_optimized(session_id)
            self.assertTrue(result2)
    
    def test_performance_metrics(self):
        """Test performance metrics collection"""
        metrics = self.optimizer.get_performance_metrics()
        
        self.assertIn('session_stats', metrics)
        self.assertIn('cache_stats', metrics)
        self.assertIn('database_stats', metrics)
        self.assertIn('timestamp', metrics)
        
        # Check session stats structure
        session_stats = metrics['session_stats']
        self.assertIn('total_sessions', session_stats)
        self.assertIn('active_sessions', session_stats)
        self.assertIn('expired_sessions', session_stats)
        self.assertIn('expiration_rate', session_stats)
    
    def test_query_plan_optimization(self):
        """Test query plan optimization"""
        results = self.optimizer.optimize_query_plan()
        
        self.assertIn('analyzed_queries', results)
        self.assertIn('optimizations', results)
        self.assertIn('recommendations', results)
        self.assertIsInstance(results['analyzed_queries'], int)
    
    def test_cache_invalidation_on_cleanup(self):
        """Test that cache is invalidated when sessions are cleaned up"""
        from unified_session_manager import UnifiedSessionManager as SessionManager
        session_manager = UnifiedSessionManager(self.db_manager)
        
        session_id = session_manager.create_user_session(
            self.test_user.id,
            self.test_user.platform_connections[0].id
        )
        
        # Cache the session
        context = self.optimizer.get_cached_session_context(session_id)
        self.assertIsNotNone(context)
        self.assertGreater(self.optimizer.request_cache.size(), 0)
        
        # Expire and cleanup the session
        with self.db_manager.get_session() as db_session:
            expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
            db_session.query(UserSession).filter_by(session_id=session_id).update({
                'expires_at': expired_time
            })
            db_session.commit()
        
        # Run cleanup (should invalidate cache)
        self.optimizer.cleanup_expired_sessions_optimized(batch_size=10)
        
        # Cache should be cleared for this session
        cached_after_cleanup = self.optimizer.request_cache.get(session_id)
        self.assertIsNone(cached_after_cleanup)


class TestGlobalOptimizer(unittest.TestCase):
    """Test global optimizer instance"""
    
    def test_get_session_optimizer(self):
        """Test global optimizer instance"""
        optimizer1 = get_session_optimizer()
        optimizer2 = get_session_optimizer()
        
        # Should return the same instance
        self.assertIs(optimizer1, optimizer2)
        self.assertIsInstance(optimizer1, SessionPerformanceOptimizer)
    
    def test_optimizer_with_custom_db_manager(self):
        """Test optimizer with custom database manager"""
        config = Config()
        db_manager = DatabaseManager(config)
        
        optimizer = get_session_optimizer(db_manager)
        self.assertIsInstance(optimizer, SessionPerformanceOptimizer)
        self.assertEqual(optimizer.db_manager, db_manager)


class TestPerformanceImprovements(unittest.TestCase):
    """Test actual performance improvements"""
    
    def setUp(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.optimizer = SessionPerformanceOptimizer(self.db_manager)
        
        # Apply optimizations
        self.optimizer.apply_database_optimizations()
        
        # Create test user
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_perf_user",
            role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        cleanup_test_user(self.user_helper)
    
    def test_session_lookup_performance(self):
        """Test that session lookup is faster with optimizations"""
        from unified_session_manager import UnifiedSessionManager as SessionManager
        session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create test session
        session_id = session_manager.create_user_session(
            self.test_user.id,
            self.test_user.platform_connections[0].id
        )
        
        # Time optimized lookup
        start_time = time.time()
        for _ in range(10):
            context = self.optimizer.get_cached_session_context(session_id)
            self.assertIsNotNone(context)
        optimized_time = time.time() - start_time
        
        # Clear cache and time non-optimized lookup
        self.optimizer.clear_request_cache()
        start_time = time.time()
        for _ in range(10):
            context = self.optimizer._fetch_session_context_optimized(session_id)
            self.assertIsNotNone(context)
        non_cached_time = time.time() - start_time
        
        # Cached lookups should be significantly faster
        # (allowing for some variance in test environment)
        self.assertLess(optimized_time, non_cached_time * 0.8)
    
    def test_batch_cleanup_performance(self):
        """Test batch cleanup performance"""
        from unified_session_manager import UnifiedSessionManager as SessionManager
        session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create many test sessions
        session_ids = []
        for i in range(20):
            session_id = session_manager.create_user_session(
                self.test_user.id,
                self.test_user.platform_connections[0].id
            )
            session_ids.append(session_id)
        
        # Expire all sessions
        with self.db_manager.get_session() as db_session:
            expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
            db_session.query(UserSession).filter(
                UserSession.session_id.in_(session_ids)
            ).update({
                'expires_at': expired_time
            }, synchronize_session=False)
            db_session.commit()
        
        # Time batch cleanup
        start_time = time.time()
        cleaned_count = self.optimizer.cleanup_expired_sessions_optimized(batch_size=5)
        cleanup_time = time.time() - start_time
        
        self.assertEqual(cleaned_count, 20)
        # Cleanup should complete in reasonable time
        self.assertLess(cleanup_time, 2.0)  # Should complete within 2 seconds


if __name__ == '__main__':
    unittest.main()