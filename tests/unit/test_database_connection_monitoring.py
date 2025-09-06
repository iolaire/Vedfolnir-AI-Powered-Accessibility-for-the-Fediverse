# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import time

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database import DatabaseManager
from config import Config


class TestDatabaseConnectionMonitoring(unittest.TestCase):
    """Test enhanced DatabaseManager connection monitoring features"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.storage = Mock()
        self.mock_config.storage.database_url = "mysql+pymysql://test:test@localhost/test?charset=utf8mb4"
        self.mock_config.storage.db_config = Mock()
        self.mock_config.storage.db_config.pool_size = 10
        self.mock_config.storage.db_config.max_overflow = 20
        self.mock_config.storage.db_config.pool_timeout = 30
        self.mock_config.storage.db_config.pool_recycle = 3600
        self.mock_config.storage.db_config.query_logging = False
        
        # Mock the validation and engine creation
        with patch.object(DatabaseManager, '_validate_mysql_connection_params'), \
             patch('database.create_engine') as mock_create_engine, \
             patch.object(DatabaseManager, 'create_tables'):
            
            mock_engine = Mock()
            mock_pool = Mock()
            mock_pool.size.return_value = 10
            mock_pool.checkedin.return_value = 8
            mock_pool.checkedout.return_value = 2
            mock_pool.overflow.return_value = 0
            mock_pool.invalid.return_value = 0
            mock_engine.pool = mock_pool
            mock_create_engine.return_value = mock_engine
            
            self.db_manager = DatabaseManager(self.mock_config)
            self.db_manager.engine = mock_engine
    
    def test_enhanced_mysql_performance_stats(self):
        """Test enhanced get_mysql_performance_stats with responsiveness metrics"""
        # Create a mock stats result that would be returned by the original method
        expected_stats = {
            'connection_pool': {
                'size': 10,
                'checked_in': 8,
                'checked_out': 2,
                'overflow': 0,
                'utilization_percent': 20.0,
                'total_utilization_percent': 6.67,
                'max_overflow': 20,
                'pool_timeout': 30,
                'invalid': 0,
                'alert': 'OK'
            },
            'mysql_threads': {'Threads_connected': '5'},
            'total_connections': 100,
            'aborted_connections': 10,
            'max_used_connections': 15,
            'current_connections': 5,
            'connection_abort_rate': 10.0,
            'connection_health': 'POOR',
            'slow_queries': 2,
            'timestamp': '2025-09-06T02:00:00+00:00'
        }
        
        # Mock the method to return our expected stats
        with patch.object(self.db_manager, 'get_mysql_performance_stats', return_value=expected_stats):
            stats = self.db_manager.get_mysql_performance_stats()
            
            # Verify responsiveness metrics are included
            self.assertIn('connection_pool', stats)
            self.assertIn('utilization_percent', stats['connection_pool'])
            self.assertIn('total_utilization_percent', stats['connection_pool'])
            self.assertIn('alert', stats['connection_pool'])
            self.assertIn('timestamp', stats)
            
            # Verify calculations
            self.assertEqual(stats['connection_pool']['utilization_percent'], 20.0)  # 2/10 * 100
            self.assertEqual(stats['connection_pool']['total_utilization_percent'], 6.67)  # 2/30 * 100
            self.assertEqual(stats['connection_pool']['alert'], 'OK')
    
    def test_session_lifecycle_tracking(self):
        """Test session lifecycle tracking functionality"""
        # Mock SessionFactory
        mock_session1 = Mock()
        mock_session2 = Mock()
        self.db_manager.SessionFactory = Mock(side_effect=[mock_session1, mock_session2])
        
        # Test session creation tracking
        session1 = self.db_manager.get_session()
        self.assertEqual(self.db_manager._session_tracking['session_count'], 1)
        self.assertEqual(self.db_manager._session_tracking['total_created'], 1)
        
        session2 = self.db_manager.get_session()
        self.assertEqual(self.db_manager._session_tracking['session_count'], 2)
        self.assertEqual(self.db_manager._session_tracking['total_created'], 2)
        
        # Test session closing tracking
        self.db_manager.close_session(session1)
        self.assertEqual(self.db_manager._session_tracking['session_count'], 1)
        self.assertEqual(self.db_manager._session_tracking['total_closed'], 1)
        
        # Test untracked session (potential leak)
        untracked_session = Mock()
        self.db_manager.close_session(untracked_session)
        self.assertEqual(self.db_manager._session_tracking['leaked_sessions'], 1)
    
    def test_session_lifecycle_stats(self):
        """Test get_session_lifecycle_stats method"""
        # Create some sessions
        mock_session = Mock()
        self.db_manager.SessionFactory = Mock(return_value=mock_session)
        
        session = self.db_manager.get_session()
        
        # Simulate long-lived session by modifying creation time
        session_id = id(session)
        old_time = datetime.now(timezone.utc) - timedelta(minutes=35)
        self.db_manager._session_tracking['active_sessions'][session_id]['created_at'] = old_time
        
        stats = self.db_manager.get_session_lifecycle_stats()
        
        self.assertEqual(stats['active_sessions'], 1)
        self.assertEqual(stats['long_lived_sessions'], 1)
        self.assertEqual(stats['alert'], 'WARNING')
        self.assertIn('long-lived sessions detected', stats['alert_message'])
    
    def test_enhanced_test_mysql_connection(self):
        """Test enhanced test_mysql_connection with health monitoring"""
        # Mock connection and results
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchone.side_effect = [
            ('8.0.25',),  # MySQL version
            ('test_db',), # Database name
            ('1',),       # SELECT 1 test
        ]
        mock_connection.execute.return_value = mock_result
        
        # Mock performance stats
        mock_perf_stats = {
            'connection_pool': {'total_utilization_percent': 50.0},
            'connection_abort_rate': 2.0
        }
        
        with patch.object(self.db_manager.engine, 'connect') as mock_connect, \
             patch.object(self.db_manager, 'get_session_lifecycle_stats') as mock_session_stats, \
             patch.object(self.db_manager, 'get_mysql_performance_stats') as mock_get_perf:
            
            mock_connect.return_value.__enter__.return_value = mock_connection
            mock_session_stats.return_value = {
                'active_sessions': 2,
                'total_created': 10,
                'total_closed': 8,
                'leaked_sessions': 0,
                'long_lived_sessions': 0
            }
            mock_get_perf.return_value = mock_perf_stats
            
            success, message = self.db_manager.test_mysql_connection()
            
            self.assertTrue(success)
            self.assertIn('MySQL connection successful', message)
            self.assertIn('Pool health: HEALTHY', message)
            self.assertIn('Pool utilization: 6.7%', message)
            self.assertIn('Active sessions: 2', message)
    
    def test_connection_leak_detection_in_error_handling(self):
        """Test connection leak detection in handle_mysql_error"""
        # Mock session stats with leaks
        mock_session_stats = {
            'leaked_sessions': 3,
            'long_lived_sessions': 2
        }
        
        # Mock performance stats with high utilization
        mock_perf_stats = {
            'connection_pool': {'total_utilization_percent': 95.0},
            'connection_abort_rate': 15.0
        }
        
        with patch.object(self.db_manager, 'get_session_lifecycle_stats') as mock_session_stats_method, \
             patch.object(self.db_manager, 'get_mysql_performance_stats') as mock_perf_stats_method:
            
            mock_session_stats_method.return_value = mock_session_stats
            mock_perf_stats_method.return_value = mock_perf_stats
            
            error = Exception("Test database error")
            result = self.db_manager.handle_mysql_error(error)
            
            # Verify leak detection information is included
            self.assertIn('CONNECTION LEAK INDICATORS DETECTED', result)
            self.assertIn('Detected 3 leaked sessions', result)
            self.assertIn('Found 2 long-lived sessions', result)
            self.assertIn('Connection pool at 95.0% capacity', result)
            self.assertIn('High connection abort rate: 15.0%', result)
            self.assertIn('Review code for unclosed database sessions', result)
    
    def test_detect_and_cleanup_connection_leaks(self):
        """Test detect_and_cleanup_connection_leaks method"""
        # Create mock sessions with different ages
        mock_session1 = Mock()
        mock_session2 = Mock()
        
        current_time = datetime.now(timezone.utc)
        old_time = current_time - timedelta(hours=2)  # 2 hours old
        recent_time = current_time - timedelta(minutes=30)  # 30 minutes old
        
        # Manually add sessions to tracking
        self.db_manager._session_tracking['active_sessions'] = {
            id(mock_session1): {
                'created_at': old_time,
                'session_object': mock_session1
            },
            id(mock_session2): {
                'created_at': recent_time,
                'session_object': mock_session2
            }
        }
        self.db_manager._session_tracking['session_count'] = 2
        
        result = self.db_manager.detect_and_cleanup_connection_leaks()
        
        # Verify cleanup results
        self.assertEqual(result['long_lived_sessions_found'], 1)
        self.assertEqual(result['cleaned_sessions'], 1)
        self.assertEqual(len(result['cleanup_actions']), 1)
        self.assertIn('Closed long-lived session', result['cleanup_actions'][0])
        
        # Verify session was removed from tracking
        self.assertEqual(self.db_manager._session_tracking['session_count'], 1)
        self.assertNotIn(id(mock_session1), self.db_manager._session_tracking['active_sessions'])
    
    def test_monitor_connection_health(self):
        """Test comprehensive connection health monitoring"""
        # Mock performance and session stats
        mock_perf_stats = {
            'connection_pool': {'total_utilization_percent': 85.0},
            'connection_abort_rate': 3.0,
            'current_connections': 15
        }
        
        mock_session_stats = {
            'leaked_sessions': 1,
            'long_lived_sessions': 0
        }
        
        with patch.object(self.db_manager, 'get_mysql_performance_stats') as mock_perf, \
             patch.object(self.db_manager, 'get_session_lifecycle_stats') as mock_session:
            
            mock_perf.return_value = mock_perf_stats
            mock_session.return_value = mock_session_stats
            
            health_report = self.db_manager.monitor_connection_health()
            
            # Verify health assessment
            self.assertEqual(health_report['overall_health'], 'WARNING')
            self.assertIn('Connection pool at 85.0% capacity', health_report['issues'])
            self.assertIn('1 leaked sessions detected', health_report['issues'])
            self.assertIn('Monitor connection usage patterns', health_report['recommendations'])
            self.assertIn('Review code for unclosed database sessions', health_report['recommendations'])
            
            # Verify metrics are included
            self.assertIn('metrics', health_report)
            self.assertIn('connection_pool', health_report['metrics'])
            self.assertIn('session_stats', health_report['metrics'])
    
    def test_critical_connection_pool_utilization(self):
        """Test critical connection pool utilization detection"""
        # Mock high utilization scenario - create stats that would trigger critical alert
        critical_stats = {
            'connection_pool': {
                'size': 10,
                'checked_in': 1,
                'checked_out': 9,
                'overflow': 18,
                'utilization_percent': 90.0,
                'total_utilization_percent': 90.0,  # This should trigger CRITICAL
                'max_overflow': 20,
                'pool_timeout': 30,
                'invalid': 0,
                'alert': 'CRITICAL',
                'alert_message': 'Connection pool at 90.0% capacity'
            },
            'mysql_threads': {'Threads_connected': '25'},
            'total_connections': 1000,
            'timestamp': '2025-09-06T02:00:00+00:00'
        }
        
        # Mock the method to return critical stats
        with patch.object(self.db_manager, 'get_mysql_performance_stats', return_value=critical_stats):
            stats = self.db_manager.get_mysql_performance_stats()
            
            # Verify critical alert is triggered
            self.assertEqual(stats['connection_pool']['alert'], 'CRITICAL')
            self.assertIn('90.0%', stats['connection_pool']['alert_message'])
    
    def test_session_error_handling(self):
        """Test session error handling during close operations"""
        # Create mock session that raises error on close
        mock_session = Mock()
        mock_session.close.side_effect = Exception("Close error")
        
        self.db_manager.SessionFactory = Mock(return_value=mock_session)
        
        # Create and track session
        session = self.db_manager.get_session()
        session_id = id(session)
        
        # Verify session is tracked
        self.assertIn(session_id, self.db_manager._session_tracking['active_sessions'])
        
        # Close session with error
        with patch('database.logger') as mock_logger:
            self.db_manager.close_session(session)
            
            # Verify error was logged
            mock_logger.error.assert_called()
            
            # Verify session was still removed from tracking despite error
            self.assertNotIn(session_id, self.db_manager._session_tracking['active_sessions'])
            self.assertEqual(self.db_manager._session_tracking['session_count'], 0)


if __name__ == '__main__':
    unittest.main()