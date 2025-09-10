# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.database.core.database_manager import DatabaseManager
from config import Config


class TestDatabaseConnectionMonitoringIntegration(unittest.TestCase):
    """Integration tests for enhanced DatabaseManager connection monitoring"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock config that mimics real config
        self.mock_config = Mock(spec=Config)
        self.mock_config.storage = Mock()
        self.mock_config.storage.database_url = "mysql+pymysql://test:test@localhost/test?charset=utf8mb4"
        self.mock_config.storage.db_config = Mock()
        self.mock_config.storage.db_config.pool_size = 10
        self.mock_config.storage.db_config.max_overflow = 20
        self.mock_config.storage.db_config.pool_timeout = 30
        self.mock_config.storage.db_config.pool_recycle = 3600
        self.mock_config.storage.db_config.query_logging = False
    
    @patch.object(DatabaseManager, '_validate_mysql_connection_params')
    @patch('database.create_engine')
    @patch.object(DatabaseManager, 'create_tables')
    def test_database_manager_initialization_with_monitoring(self, mock_create_tables, mock_create_engine, mock_validate):
        """Test that DatabaseManager initializes with connection monitoring features"""
        # Mock engine and pool
        mock_engine = Mock()
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool
        mock_create_engine.return_value = mock_engine
        
        # Create DatabaseManager
        db_manager = DatabaseManager(self.mock_config)
        
        # Verify session tracking is initialized
        self.assertIn('active_sessions', db_manager._session_tracking)
        self.assertIn('session_count', db_manager._session_tracking)
        self.assertIn('total_created', db_manager._session_tracking)
        self.assertIn('total_closed', db_manager._session_tracking)
        self.assertIn('leaked_sessions', db_manager._session_tracking)
        self.assertIn('max_concurrent', db_manager._session_tracking)
        
        # Verify initial values
        self.assertEqual(db_manager._session_tracking['session_count'], 0)
        self.assertEqual(db_manager._session_tracking['total_created'], 0)
        self.assertEqual(db_manager._session_tracking['total_closed'], 0)
        self.assertEqual(db_manager._session_tracking['leaked_sessions'], 0)
        self.assertEqual(db_manager._session_tracking['max_concurrent'], 0)
    
    @patch.object(DatabaseManager, '_validate_mysql_connection_params')
    @patch('database.create_engine')
    @patch.object(DatabaseManager, 'create_tables')
    def test_enhanced_methods_exist(self, mock_create_tables, mock_create_engine, mock_validate):
        """Test that all enhanced methods exist and are callable"""
        # Mock engine
        mock_engine = Mock()
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_engine.pool = mock_pool
        mock_create_engine.return_value = mock_engine
        
        # Create DatabaseManager
        db_manager = DatabaseManager(self.mock_config)
        
        # Verify enhanced methods exist
        self.assertTrue(hasattr(db_manager, 'get_session_lifecycle_stats'))
        self.assertTrue(callable(db_manager.get_session_lifecycle_stats))
        
        self.assertTrue(hasattr(db_manager, 'detect_and_cleanup_connection_leaks'))
        self.assertTrue(callable(db_manager.detect_and_cleanup_connection_leaks))
        
        self.assertTrue(hasattr(db_manager, 'monitor_connection_health'))
        self.assertTrue(callable(db_manager.monitor_connection_health))
        
        # Verify enhanced existing methods still exist
        self.assertTrue(hasattr(db_manager, 'get_mysql_performance_stats'))
        self.assertTrue(callable(db_manager.get_mysql_performance_stats))
        
        self.assertTrue(hasattr(db_manager, 'test_mysql_connection'))
        self.assertTrue(callable(db_manager.test_mysql_connection))
        
        self.assertTrue(hasattr(db_manager, 'handle_mysql_error'))
        self.assertTrue(callable(db_manager.handle_mysql_error))
    
    @patch.object(DatabaseManager, '_validate_mysql_connection_params')
    @patch('database.create_engine')
    @patch.object(DatabaseManager, 'create_tables')
    def test_session_lifecycle_integration(self, mock_create_tables, mock_create_engine, mock_validate):
        """Test session lifecycle tracking integration"""
        # Mock engine and SessionFactory
        mock_engine = Mock()
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_engine.pool = mock_pool
        mock_create_engine.return_value = mock_engine
        
        # Create DatabaseManager
        db_manager = DatabaseManager(self.mock_config)
        
        # Mock SessionFactory
        mock_session = Mock()
        db_manager.SessionFactory = Mock(return_value=mock_session)
        
        # Test session creation and tracking
        session = db_manager.get_session()
        self.assertEqual(db_manager._session_tracking['session_count'], 1)
        self.assertEqual(db_manager._session_tracking['total_created'], 1)
        
        # Test session closing and tracking
        db_manager.close_session(session)
        self.assertEqual(db_manager._session_tracking['session_count'], 0)
        self.assertEqual(db_manager._session_tracking['total_closed'], 1)
        
        # Test lifecycle stats
        stats = db_manager.get_session_lifecycle_stats()
        self.assertIn('active_sessions', stats)
        self.assertIn('total_created', stats)
        self.assertIn('total_closed', stats)
        self.assertIn('timestamp', stats)
    
    @patch.object(DatabaseManager, '_validate_mysql_connection_params')
    @patch('database.create_engine')
    @patch.object(DatabaseManager, 'create_tables')
    def test_connection_health_monitoring_integration(self, mock_create_tables, mock_create_engine, mock_validate):
        """Test connection health monitoring integration"""
        # Mock engine
        mock_engine = Mock()
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_engine.pool = mock_pool
        mock_create_engine.return_value = mock_engine
        
        # Create DatabaseManager
        db_manager = DatabaseManager(self.mock_config)
        
        # Mock the performance stats and session stats methods
        mock_perf_stats = {
            'connection_pool': {'total_utilization_percent': 50.0},
            'connection_abort_rate': 2.0,
            'current_connections': 5
        }
        
        mock_session_stats = {
            'leaked_sessions': 0,
            'long_lived_sessions': 0
        }
        
        with patch.object(db_manager, 'get_mysql_performance_stats', return_value=mock_perf_stats), \
             patch.object(db_manager, 'get_session_lifecycle_stats', return_value=mock_session_stats):
            
            health_report = db_manager.monitor_connection_health()
            
            # Verify health report structure
            self.assertIn('timestamp', health_report)
            self.assertIn('overall_health', health_report)
            self.assertIn('issues', health_report)
            self.assertIn('recommendations', health_report)
            self.assertIn('metrics', health_report)
            
            # Verify healthy status
            self.assertEqual(health_report['overall_health'], 'HEALTHY')
            self.assertEqual(len(health_report['issues']), 0)
    
    @patch.object(DatabaseManager, '_validate_mysql_connection_params')
    @patch('database.create_engine')
    @patch.object(DatabaseManager, 'create_tables')
    def test_connection_leak_cleanup_integration(self, mock_create_tables, mock_create_engine, mock_validate):
        """Test connection leak cleanup integration"""
        # Mock engine
        mock_engine = Mock()
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_engine.pool = mock_pool
        mock_create_engine.return_value = mock_engine
        
        # Create DatabaseManager
        db_manager = DatabaseManager(self.mock_config)
        
        # Test cleanup with no leaks
        cleanup_result = db_manager.detect_and_cleanup_connection_leaks()
        
        # Verify cleanup result structure
        self.assertIn('cleaned_sessions', cleanup_result)
        self.assertIn('long_lived_sessions_found', cleanup_result)
        self.assertIn('leaked_sessions_found', cleanup_result)
        self.assertIn('cleanup_actions', cleanup_result)
        self.assertIn('timestamp', cleanup_result)
        
        # Verify no cleanup needed initially
        self.assertEqual(cleanup_result['cleaned_sessions'], 0)
        self.assertEqual(cleanup_result['long_lived_sessions_found'], 0)


if __name__ == '__main__':
    unittest.main()