# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for session health checker responsiveness monitoring.

Tests the system responsiveness monitoring functionality added to the
SessionHealthChecker class.
"""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database import DatabaseManager
from session_health_checker import SessionHealthChecker, SessionHealthStatus, SessionComponentHealth
from unified_session_manager import UnifiedSessionManager
from models import UserSession


class TestSessionHealthResponsiveness(unittest.TestCase):
    """Test responsiveness monitoring in session health checker"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock database manager
        self.db_manager = Mock(spec=DatabaseManager)
        
        # Create mock session manager
        self.session_manager = Mock(spec=UnifiedSessionManager)
        
        # Create session health checker
        self.health_checker = SessionHealthChecker(self.db_manager, self.session_manager)
    
    @patch('session_health_checker.psutil')
    @patch('session_health_checker.SystemOptimizer')
    def test_check_system_responsiveness_health_healthy(self, mock_optimizer_class, mock_psutil):
        """Test system responsiveness health check with healthy system"""
        # Mock system metrics - healthy state
        mock_memory = Mock()
        mock_memory.percent = 60.0  # 60% memory usage
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_percent.return_value = 30.0  # 30% CPU usage
        
        # Mock database session
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.count.return_value = 10  # Low session activity
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Mock SystemOptimizer
        mock_optimizer = Mock()
        mock_optimizer.check_responsiveness.return_value = {
            'responsive': True,
            'issues': [],
            'overall_status': 'healthy'
        }
        mock_optimizer_class.return_value = mock_optimizer
        
        # Run system responsiveness health check
        result = self.health_checker.check_system_responsiveness_health()
        
        # Verify results
        self.assertIsInstance(result, SessionComponentHealth)
        self.assertEqual(result.name, "system_responsiveness")
        self.assertEqual(result.status, SessionHealthStatus.HEALTHY)
        self.assertIn("healthy", result.message.lower())
        self.assertIsNotNone(result.details)
        self.assertEqual(result.details['memory_percent'], 60.0)
        self.assertEqual(result.details['cpu_percent'], 30.0)
        self.assertTrue(result.details['system_optimizer_available'])
    
    @patch('session_health_checker.psutil')
    @patch('session_health_checker.SystemOptimizer')
    def test_check_system_responsiveness_health_degraded(self, mock_optimizer_class, mock_psutil):
        """Test system responsiveness health check with degraded system"""
        # Mock system metrics - degraded state
        mock_memory = Mock()
        mock_memory.percent = 85.0  # 85% memory usage (high)
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_percent.return_value = 85.0  # 85% CPU usage (high)
        
        # Mock database session with high activity
        mock_db_session = Mock()
        # First call for recent sessions (high activity)
        # Second call for overdue sessions (some cleanup lag)
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [150, 25]
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Mock SystemOptimizer with issues
        mock_optimizer = Mock()
        mock_optimizer.check_responsiveness.return_value = {
            'responsive': False,
            'issues': [
                {
                    'type': 'memory',
                    'severity': 'warning',
                    'message': 'High memory usage detected'
                }
            ],
            'overall_status': 'warning'
        }
        mock_optimizer_class.return_value = mock_optimizer
        
        # Run system responsiveness health check
        result = self.health_checker.check_system_responsiveness_health()
        
        # Verify results
        self.assertEqual(result.status, SessionHealthStatus.DEGRADED)
        self.assertIn("issues detected", result.message.lower())
        self.assertEqual(result.details['memory_percent'], 85.0)
        self.assertEqual(result.details['cpu_percent'], 85.0)
        self.assertEqual(result.details['recent_session_operations'], 150)
        self.assertEqual(result.details['overdue_cleanup_sessions'], 25)
        self.assertIn("High session activity", result.details['issues'][0])
        self.assertIn("Some session cleanup lag", result.details['issues'][1])
    
    @patch('session_health_checker.psutil')
    @patch('session_health_checker.SystemOptimizer')
    def test_check_system_responsiveness_health_critical(self, mock_optimizer_class, mock_psutil):
        """Test system responsiveness health check with critical system issues"""
        # Mock system metrics - critical state
        mock_memory = Mock()
        mock_memory.percent = 95.0  # 95% memory usage (critical)
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_percent.return_value = 95.0  # 95% CPU usage (critical)
        
        # Mock database session with critical issues
        mock_db_session = Mock()
        # High recent activity and critical cleanup lag
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [200, 75]
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Mock SystemOptimizer with critical issues
        mock_optimizer = Mock()
        mock_optimizer.check_responsiveness.return_value = {
            'responsive': False,
            'issues': [
                {
                    'type': 'memory',
                    'severity': 'critical',
                    'message': 'Critical memory usage detected'
                },
                {
                    'type': 'cpu',
                    'severity': 'critical',
                    'message': 'Critical CPU usage detected'
                }
            ],
            'overall_status': 'critical'
        }
        mock_optimizer_class.return_value = mock_optimizer
        
        # Run system responsiveness health check
        result = self.health_checker.check_system_responsiveness_health()
        
        # Verify results
        self.assertEqual(result.status, SessionHealthStatus.UNHEALTHY)
        self.assertIn("issues detected", result.message.lower())
        self.assertEqual(result.details['memory_percent'], 95.0)
        self.assertEqual(result.details['cpu_percent'], 95.0)
        self.assertEqual(result.details['recent_session_operations'], 200)
        self.assertEqual(result.details['overdue_cleanup_sessions'], 75)
        
        # Verify multiple issues detected
        issues = result.details['issues']
        self.assertGreater(len(issues), 3)  # System issues + session issues
        self.assertTrue(any("Session cleanup lag" in issue for issue in issues))
        self.assertTrue(any("High session activity" in issue for issue in issues))
    
    @patch('session_health_checker.psutil')
    def test_check_system_responsiveness_health_no_optimizer(self, mock_psutil):
        """Test system responsiveness health check when SystemOptimizer is not available"""
        # Mock system metrics
        mock_memory = Mock()
        mock_memory.percent = 70.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_percent.return_value = 40.0
        
        # Mock database session
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [20, 5]
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Mock SystemOptimizer import failure
        with patch('session_health_checker.SystemOptimizer', side_effect=ImportError("SystemOptimizer not available")):
            # Run system responsiveness health check
            result = self.health_checker.check_system_responsiveness_health()
        
        # Verify results
        self.assertEqual(result.status, SessionHealthStatus.HEALTHY)  # Should still work without optimizer
        self.assertFalse(result.details['system_optimizer_available'])
        self.assertIsNone(result.details['optimizer_analysis'])
    
    def test_check_system_responsiveness_health_database_error(self):
        """Test system responsiveness health check with database error"""
        # Mock database error
        self.db_manager.get_session.side_effect = Exception("Database connection failed")
        
        # Run system responsiveness health check
        result = self.health_checker.check_system_responsiveness_health()
        
        # Verify error handling
        self.assertEqual(result.status, SessionHealthStatus.UNHEALTHY)
        self.assertIn("failed", result.message.lower())
        self.assertIn("error", result.details)
    
    def test_comprehensive_session_health_includes_responsiveness(self):
        """Test that comprehensive session health check includes system responsiveness"""
        # Mock all component health checks
        with patch.object(self.health_checker, 'check_database_session_health') as mock_db, \
             patch.object(self.health_checker, 'check_session_monitoring_health') as mock_monitoring, \
             patch.object(self.health_checker, 'check_platform_switching_health') as mock_platform, \
             patch.object(self.health_checker, 'check_session_cleanup_health') as mock_cleanup, \
             patch.object(self.health_checker, 'check_session_security_health') as mock_security, \
             patch.object(self.health_checker, 'check_memory_leak_detection_health') as mock_memory, \
             patch.object(self.health_checker, 'check_system_responsiveness_health') as mock_responsiveness:
            
            # Mock return values
            mock_db.return_value = SessionComponentHealth("database_sessions", SessionHealthStatus.HEALTHY, "Healthy")
            mock_monitoring.return_value = SessionComponentHealth("session_monitoring", SessionHealthStatus.HEALTHY, "Healthy")
            mock_platform.return_value = SessionComponentHealth("platform_switching", SessionHealthStatus.HEALTHY, "Healthy")
            mock_cleanup.return_value = SessionComponentHealth("session_cleanup", SessionHealthStatus.HEALTHY, "Healthy")
            mock_security.return_value = SessionComponentHealth("session_security", SessionHealthStatus.HEALTHY, "Healthy")
            mock_memory.return_value = SessionComponentHealth("memory_leak_detection", SessionHealthStatus.HEALTHY, "Healthy")
            mock_responsiveness.return_value = SessionComponentHealth("system_responsiveness", SessionHealthStatus.HEALTHY, "Healthy")
            
            # Run comprehensive health check
            result = self.health_checker.check_comprehensive_session_health()
            
            # Verify system responsiveness is included
            self.assertIn("system_responsiveness", result.components)
            self.assertEqual(result.components["system_responsiveness"].name, "system_responsiveness")
            mock_responsiveness.assert_called_once()
    
    def test_responsiveness_thresholds_configuration(self):
        """Test that responsiveness thresholds are properly configured"""
        # Verify thresholds are set
        self.assertIn('memory_usage_warning', self.health_checker.thresholds)
        self.assertIn('memory_usage_critical', self.health_checker.thresholds)
        self.assertIn('response_time_warning', self.health_checker.thresholds)
        self.assertIn('response_time_critical', self.health_checker.thresholds)
        
        # Verify threshold values are reasonable
        self.assertGreater(self.health_checker.thresholds['memory_usage_critical'], 
                          self.health_checker.thresholds['memory_usage_warning'])
        self.assertGreater(self.health_checker.thresholds['response_time_critical'], 
                          self.health_checker.thresholds['response_time_warning'])
    
    @patch('session_health_checker.psutil')
    def test_responsiveness_metrics_collection(self, mock_psutil):
        """Test that responsiveness metrics are properly collected"""
        # Mock system metrics
        mock_memory = Mock()
        mock_memory.percent = 75.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_percent.return_value = 45.0
        
        # Mock database session
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [30, 10]
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Run system responsiveness health check
        result = self.health_checker.check_system_responsiveness_health()
        
        # Verify metrics are collected
        self.assertIsNotNone(result.metrics)
        self.assertIn('memory_percent', result.metrics)
        self.assertIn('cpu_percent', result.metrics)
        self.assertIn('issues_count', result.metrics)
        self.assertIn('recent_session_operations', result.metrics)
        self.assertIn('overdue_cleanup_sessions', result.metrics)
        
        # Verify metric values
        self.assertEqual(result.metrics['memory_percent'], 75.0)
        self.assertEqual(result.metrics['cpu_percent'], 45.0)
        self.assertEqual(result.metrics['recent_session_operations'], 30)
        self.assertEqual(result.metrics['overdue_cleanup_sessions'], 10)
    
    @patch('session_health_checker.psutil')
    def test_responsiveness_issue_prioritization(self, mock_psutil):
        """Test that responsiveness issues are properly prioritized"""
        # Mock system metrics with multiple issues
        mock_memory = Mock()
        mock_memory.percent = 95.0  # Critical memory
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_percent.return_value = 85.0  # High CPU
        
        # Mock database session with issues
        mock_db_session = Mock()
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [150, 60]  # High activity, critical cleanup lag
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Run system responsiveness health check
        result = self.health_checker.check_system_responsiveness_health()
        
        # Verify critical issues take precedence
        self.assertEqual(result.status, SessionHealthStatus.UNHEALTHY)
        
        # Verify issues are properly categorized
        issues = result.details['issues']
        critical_issues = [issue for issue in issues if 'Critical' in issue or 'critical' in issue]
        warning_issues = [issue for issue in issues if 'High' in issue and 'Critical' not in issue and 'critical' not in issue]
        
        self.assertGreater(len(critical_issues), 0)
        self.assertGreater(len(warning_issues), 0)


if __name__ == '__main__':
    unittest.main()