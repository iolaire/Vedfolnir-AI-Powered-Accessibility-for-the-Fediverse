# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for health check responsiveness monitoring integration.

Tests the integration of responsiveness monitoring with existing health check systems,
including HealthChecker enhancements and alert integration.
"""

import unittest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config, ResponsivenessConfig
from database import DatabaseManager
from health_check import HealthChecker, HealthStatus, ComponentHealth
from models import UserRole


class TestHealthCheckResponsiveness(unittest.TestCase):
    """Test responsiveness monitoring integration with health checks"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock config with responsiveness settings
        self.config = Mock(spec=Config)
        self.config.responsiveness = ResponsivenessConfig(
            memory_warning_threshold=0.8,
            memory_critical_threshold=0.9,
            cpu_warning_threshold=0.8,
            cpu_critical_threshold=0.9,
            connection_pool_warning_threshold=0.9,
            monitoring_interval=30,
            cleanup_enabled=True
        )
        
        # Create mock database manager
        self.db_manager = Mock(spec=DatabaseManager)
        
        # Create health checker instance
        self.health_checker = HealthChecker(self.config, self.db_manager)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_check_responsiveness_health_healthy(self, mock_cpu_percent, mock_virtual_memory):
        """Test responsiveness health check with healthy system"""
        # Mock system metrics - healthy state
        mock_memory = Mock()
        mock_memory.percent = 60.0  # 60% memory usage
        mock_virtual_memory.return_value = mock_memory
        mock_cpu_percent.return_value = 30.0  # 30% CPU usage
        
        # Mock SystemOptimizer
        mock_optimizer = Mock()
        mock_optimizer.check_responsiveness.return_value = {
            'responsive': True,
            'issues': [],
            'overall_status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }
        mock_optimizer.get_performance_metrics.return_value = {
            'cleanup_triggered': False,
            'connection_pool_utilization': 0.5,
            'background_tasks_count': 3,
            'avg_request_time': 0.2,
            'slow_request_count': 0
        }
        self.health_checker.system_optimizer = mock_optimizer
        
        # Run responsiveness health check
        result = asyncio.run(self.health_checker.check_responsiveness_health())
        
        # Verify results
        self.assertIsInstance(result, ComponentHealth)
        self.assertEqual(result.name, "responsiveness")
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertIn("healthy", result.message.lower())
        self.assertIsNotNone(result.details)
        self.assertTrue(result.details['responsive'])
        self.assertEqual(result.details['issues_count'], 0)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_check_responsiveness_health_degraded(self, mock_cpu_percent, mock_virtual_memory):
        """Test responsiveness health check with degraded system"""
        # Mock system metrics - degraded state
        mock_memory = Mock()
        mock_memory.percent = 85.0  # 85% memory usage (above warning threshold)
        mock_virtual_memory.return_value = mock_memory
        mock_cpu_percent.return_value = 85.0  # 85% CPU usage (above warning threshold)
        
        # Mock SystemOptimizer with issues
        mock_optimizer = Mock()
        mock_optimizer.check_responsiveness.return_value = {
            'responsive': False,
            'issues': [
                {
                    'type': 'memory',
                    'severity': 'warning',
                    'current': '85.0%',
                    'threshold': '80.0%',
                    'message': 'Memory usage elevated - monitor closely'
                },
                {
                    'type': 'cpu',
                    'severity': 'warning',
                    'current': '85.0%',
                    'threshold': '80.0%',
                    'message': 'CPU usage elevated - potential performance impact'
                }
            ],
            'overall_status': 'warning',
            'timestamp': datetime.now().isoformat()
        }
        mock_optimizer.get_performance_metrics.return_value = {
            'cleanup_triggered': True,
            'connection_pool_utilization': 0.8,
            'background_tasks_count': 12,
            'avg_request_time': 1.5,
            'slow_request_count': 5
        }
        self.health_checker.system_optimizer = mock_optimizer
        
        # Run responsiveness health check
        result = asyncio.run(self.health_checker.check_responsiveness_health())
        
        # Verify results
        self.assertEqual(result.status, HealthStatus.DEGRADED)
        self.assertIn("issues detected", result.message.lower())
        self.assertFalse(result.details['responsive'])
        self.assertEqual(result.details['issues_count'], 2)
        self.assertEqual(result.details['warning_issues'], 2)
        self.assertEqual(result.details['critical_issues'], 0)
        self.assertTrue(result.details['cleanup_triggered'])
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_check_responsiveness_health_critical(self, mock_cpu_percent, mock_virtual_memory):
        """Test responsiveness health check with critical system issues"""
        # Mock system metrics - critical state
        mock_memory = Mock()
        mock_memory.percent = 95.0  # 95% memory usage (above critical threshold)
        mock_virtual_memory.return_value = mock_memory
        mock_cpu_percent.return_value = 95.0  # 95% CPU usage (above critical threshold)
        
        # Mock SystemOptimizer with critical issues
        mock_optimizer = Mock()
        mock_optimizer.check_responsiveness.return_value = {
            'responsive': False,
            'issues': [
                {
                    'type': 'memory',
                    'severity': 'critical',
                    'current': '95.0%',
                    'threshold': '90.0%',
                    'message': 'Memory usage critical - immediate cleanup required'
                },
                {
                    'type': 'cpu',
                    'severity': 'critical',
                    'current': '95.0%',
                    'threshold': '90.0%',
                    'message': 'CPU usage critical - performance severely impacted'
                }
            ],
            'overall_status': 'critical',
            'timestamp': datetime.now().isoformat()
        }
        mock_optimizer.get_performance_metrics.return_value = {
            'cleanup_triggered': True,
            'connection_pool_utilization': 0.95,
            'background_tasks_count': 25,
            'avg_request_time': 8.0,
            'slow_request_count': 20
        }
        self.health_checker.system_optimizer = mock_optimizer
        
        # Run responsiveness health check
        result = asyncio.run(self.health_checker.check_responsiveness_health())
        
        # Verify results
        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
        self.assertIn("critical", result.message.lower())
        self.assertFalse(result.details['responsive'])
        self.assertEqual(result.details['issues_count'], 2)
        self.assertEqual(result.details['critical_issues'], 2)
        self.assertTrue(result.details['cleanup_triggered'])
    
    def test_check_responsiveness_health_no_optimizer(self):
        """Test responsiveness health check when SystemOptimizer is not available"""
        # Set system_optimizer to None
        self.health_checker.system_optimizer = None
        
        # Run responsiveness health check
        result = asyncio.run(self.health_checker.check_responsiveness_health())
        
        # Verify results
        self.assertEqual(result.status, HealthStatus.DEGRADED)
        self.assertIn("not available", result.message.lower())
        self.assertFalse(result.details['system_optimizer_available'])
    
    def test_check_system_health_includes_responsiveness(self):
        """Test that system health check includes responsiveness monitoring"""
        # Mock the individual health check methods to return ComponentHealth objects directly
        async def mock_database_health():
            return ComponentHealth("database", HealthStatus.HEALTHY, "Database healthy")
        
        async def mock_ollama_health():
            return ComponentHealth("ollama", HealthStatus.HEALTHY, "Ollama healthy")
        
        async def mock_storage_health():
            return ComponentHealth("storage", HealthStatus.HEALTHY, "Storage healthy")
        
        async def mock_session_health():
            return ComponentHealth("sessions", HealthStatus.HEALTHY, "Sessions healthy")
        
        async def mock_responsiveness_health():
            return ComponentHealth("responsiveness", HealthStatus.HEALTHY, "Responsiveness healthy")
        
        with patch.object(self.health_checker, 'check_database_health', side_effect=mock_database_health), \
             patch.object(self.health_checker, 'check_ollama_health', side_effect=mock_ollama_health), \
             patch.object(self.health_checker, 'check_storage_health', side_effect=mock_storage_health), \
             patch.object(self.health_checker, 'check_session_health', side_effect=mock_session_health), \
             patch.object(self.health_checker, 'check_responsiveness_health', side_effect=mock_responsiveness_health):
            
            # Run system health check
            result = asyncio.run(self.health_checker.check_system_health())
            
            # Verify responsiveness is included
            self.assertIn("responsiveness", result.components)
            self.assertEqual(result.components["responsiveness"].name, "responsiveness")
    
    @patch('notification_helpers.send_admin_notification')
    def test_send_responsiveness_alerts_healthy(self, mock_send_notification):
        """Test sending responsiveness alerts for healthy status"""
        # Create healthy responsiveness health
        responsiveness_health = ComponentHealth(
            name="responsiveness",
            status=HealthStatus.HEALTHY,
            message="System responsiveness healthy",
            last_check=datetime.now(timezone.utc)
        )
        
        # Send alerts
        result = self.health_checker.send_responsiveness_alerts(responsiveness_health)
        
        # Verify no alert sent for healthy status
        self.assertTrue(result)
        mock_send_notification.assert_not_called()
    
    @patch('notification_helpers.send_admin_notification')
    def test_send_responsiveness_alerts_degraded(self, mock_send_notification):
        """Test sending responsiveness alerts for degraded status"""
        mock_send_notification.return_value = True
        
        # Create degraded responsiveness health
        responsiveness_health = ComponentHealth(
            name="responsiveness",
            status=HealthStatus.DEGRADED,
            message="Responsiveness issues detected: 2 issues",
            last_check=datetime.now(timezone.utc),
            details={
                'issues': [
                    {'type': 'memory', 'severity': 'warning', 'message': 'High memory usage'},
                    {'type': 'cpu', 'severity': 'warning', 'message': 'High CPU usage'}
                ],
                'current_metrics': {
                    'memory_percent': 85.0,
                    'cpu_percent': 85.0,
                    'connection_pool_utilization': 0.8
                },
                'cleanup_triggered': True
            }
        )
        
        # Send alerts
        result = self.health_checker.send_responsiveness_alerts(responsiveness_health)
        
        # Verify alert sent
        self.assertTrue(result)
        mock_send_notification.assert_called_once()
        
        # Verify alert content
        call_args = mock_send_notification.call_args
        self.assertIn("Responsiveness Warning", call_args[1]['title'])
        self.assertIn("Memory: 85.0%", call_args[1]['message'])
        self.assertIn("CPU: 85.0%", call_args[1]['message'])
        self.assertIn("cleanup has been triggered", call_args[1]['message'])
    
    @patch('notification_helpers.send_admin_notification')
    def test_send_responsiveness_alerts_critical(self, mock_send_notification):
        """Test sending responsiveness alerts for critical status"""
        mock_send_notification.return_value = True
        
        # Create critical responsiveness health
        responsiveness_health = ComponentHealth(
            name="responsiveness",
            status=HealthStatus.UNHEALTHY,
            message="Critical responsiveness issues detected: 2 critical, 2 total",
            last_check=datetime.now(timezone.utc),
            details={
                'issues': [
                    {'type': 'memory', 'severity': 'critical', 'message': 'Critical memory usage'},
                    {'type': 'cpu', 'severity': 'critical', 'message': 'Critical CPU usage'}
                ],
                'current_metrics': {
                    'memory_percent': 95.0,
                    'cpu_percent': 95.0,
                    'connection_pool_utilization': 0.95
                },
                'cleanup_triggered': True
            }
        )
        
        # Send alerts
        result = self.health_checker.send_responsiveness_alerts(responsiveness_health)
        
        # Verify alert sent
        self.assertTrue(result)
        mock_send_notification.assert_called_once()
        
        # Verify alert content
        call_args = mock_send_notification.call_args
        self.assertIn("Critical Responsiveness Issue", call_args[1]['title'])
        self.assertIn("Immediate attention required", call_args[1]['message'])
        
        # Verify notification type and priority
        from models import NotificationType, NotificationPriority
        self.assertEqual(call_args[1]['notification_type'], NotificationType.ERROR)
        self.assertEqual(call_args[1]['priority'], NotificationPriority.HIGH)
    
    @patch('notification_helpers.send_admin_notification')
    def test_send_responsiveness_alerts_error_handling(self, mock_send_notification):
        """Test error handling in responsiveness alert sending"""
        mock_send_notification.side_effect = Exception("Notification system error")
        
        # Create responsiveness health
        responsiveness_health = ComponentHealth(
            name="responsiveness",
            status=HealthStatus.DEGRADED,
            message="Test message",
            last_check=datetime.now(timezone.utc)
        )
        
        # Send alerts (should handle exception gracefully)
        result = self.health_checker.send_responsiveness_alerts(responsiveness_health)
        
        # Verify error handled gracefully
        self.assertFalse(result)
    
    def test_responsiveness_config_integration(self):
        """Test that responsiveness configuration is properly integrated"""
        # Verify config is loaded
        self.assertIsNotNone(self.health_checker.responsiveness_config)
        self.assertEqual(self.health_checker.responsiveness_config.memory_warning_threshold, 0.8)
        self.assertEqual(self.health_checker.responsiveness_config.memory_critical_threshold, 0.9)
        self.assertEqual(self.health_checker.responsiveness_config.cpu_warning_threshold, 0.8)
        self.assertEqual(self.health_checker.responsiveness_config.cpu_critical_threshold, 0.9)
        self.assertTrue(self.health_checker.responsiveness_config.cleanup_enabled)
    
    def test_responsiveness_metrics_tracking(self):
        """Test that responsiveness metrics are properly tracked"""
        # Initially no metrics
        self.assertEqual(self.health_checker._last_responsiveness_check, 0)
        self.assertEqual(self.health_checker._responsiveness_metrics, {})
        
        # After running a check, metrics should be updated
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.cpu_percent') as mock_cpu:
            
            # Mock system metrics
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 70.0
            mock_memory.return_value = mock_memory_obj
            mock_cpu.return_value = 40.0
            
            # Mock SystemOptimizer
            mock_optimizer = Mock()
            mock_optimizer.check_responsiveness.return_value = {
                'responsive': True,
                'issues': [],
                'overall_status': 'healthy'
            }
            mock_optimizer.get_performance_metrics.return_value = {'cleanup_triggered': False}
            self.health_checker.system_optimizer = mock_optimizer
            
            # Run check
            asyncio.run(self.health_checker.check_responsiveness_health())
            
            # Verify metrics updated
            self.assertGreater(self.health_checker._last_responsiveness_check, 0)
            self.assertIn('timestamp', self.health_checker._responsiveness_metrics)
            self.assertIn('responsive', self.health_checker._responsiveness_metrics)


if __name__ == '__main__':
    unittest.main()