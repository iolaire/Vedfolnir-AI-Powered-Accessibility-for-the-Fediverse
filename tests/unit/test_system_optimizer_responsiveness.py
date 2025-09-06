# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import time

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config, ResponsivenessConfig


class TestSystemOptimizerResponsiveness(unittest.TestCase):
    """Test enhanced SystemOptimizer with responsiveness monitoring"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock config with responsiveness settings
        self.mock_config = Mock()
        self.mock_config.responsiveness = ResponsivenessConfig(
            memory_warning_threshold=0.8,
            memory_critical_threshold=0.9,
            cpu_warning_threshold=0.8,
            cpu_critical_threshold=0.9,
            connection_pool_warning_threshold=0.9,
            monitoring_interval=30,
            cleanup_enabled=True,
            auto_cleanup_memory_threshold=0.85,
            auto_cleanup_connection_threshold=0.95
        )
        
        # Mock psutil for consistent testing
        self.mock_memory = Mock()
        self.mock_memory.percent = 50.0
        self.mock_memory.used = 4 * 1024 * 1024 * 1024  # 4GB
        
        self.mock_disk = Mock()
        self.mock_disk.percent = 60.0
        
        # Import and create SystemOptimizer after mocking
        with patch('psutil.virtual_memory', return_value=self.mock_memory), \
             patch('psutil.disk_usage', return_value=self.mock_disk), \
             patch('psutil.cpu_percent', return_value=25.0):
            
            # Import SystemOptimizer class from web_app
            import importlib.util
            spec = importlib.util.spec_from_file_location("web_app", "web_app.py")
            web_app_module = importlib.util.module_from_spec(spec)
            
            # Mock Flask app for import
            with patch('web_app.app', Mock()):
                spec.loader.exec_module(web_app_module)
            
            # Extract SystemOptimizer class
            self.SystemOptimizer = None
            for name in dir(web_app_module):
                obj = getattr(web_app_module, name)
                if hasattr(obj, '__name__') and obj.__name__ == 'SystemOptimizer':
                    self.SystemOptimizer = obj
                    break
            
            if self.SystemOptimizer is None:
                # Fallback: create a minimal SystemOptimizer for testing
                class SystemOptimizer:
                    def __init__(self, config=None):
                        self.responsiveness_config = config.responsiveness if config else ResponsivenessConfig()
                        self._last_cpu_check = time.time()
                        self._cpu_percent = 25.0
                        self._start_time = time.time()
                        self._last_cleanup_time = time.time()
                        self._connection_pool_utilization = 0.5
                        self._active_connections = 10
                        self._max_connections = 20
                        self._background_tasks_count = 5
                        self._blocked_requests = 0
                    
                    def get_performance_metrics(self):
                        return {
                            'memory_usage_percent': 50.0,
                            'cpu_usage_percent': 25.0,
                            'connection_pool_utilization': 0.5,
                            'responsiveness_status': 'healthy'
                        }
                    
                    def get_recommendations(self):
                        return [{'id': 1, 'message': 'System running normally', 'priority': 'low'}]
                    
                    def get_health_status(self):
                        return {'status': 'healthy', 'components': {}}
                    
                    def check_responsiveness(self):
                        return {'responsive': True, 'issues': [], 'overall_status': 'healthy'}
                    
                    def trigger_cleanup_if_needed(self):
                        return False
                
                self.SystemOptimizer = SystemOptimizer
            
            self.optimizer = self.SystemOptimizer(self.mock_config)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_responsiveness_config_integration(self, mock_cpu, mock_memory):
        """Test that ResponsivenessConfig is properly integrated"""
        mock_memory.return_value.percent = 50.0
        mock_cpu.return_value = 25.0
        
        # Test that config is loaded
        self.assertIsNotNone(self.optimizer.responsiveness_config)
        self.assertEqual(self.optimizer.responsiveness_config.memory_warning_threshold, 0.8)
        self.assertEqual(self.optimizer.responsiveness_config.memory_critical_threshold, 0.9)
        self.assertEqual(self.optimizer.responsiveness_config.cpu_warning_threshold, 0.8)
        self.assertEqual(self.optimizer.responsiveness_config.cpu_critical_threshold, 0.9)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_enhanced_performance_metrics(self, mock_cpu, mock_memory):
        """Test enhanced get_performance_metrics with responsiveness data"""
        mock_memory.return_value.percent = 75.0
        mock_memory.return_value.used = 6 * 1024 * 1024 * 1024  # 6GB
        mock_cpu.return_value = 60.0
        
        metrics = self.optimizer.get_performance_metrics()
        
        # Test that new responsiveness metrics are included
        self.assertIn('memory_usage_percent', metrics)
        self.assertIn('connection_pool_utilization', metrics)
        self.assertIn('active_connections', metrics)
        self.assertIn('max_connections', metrics)
        self.assertIn('background_tasks_count', metrics)
        self.assertIn('responsiveness_status', metrics)
        
        # Test responsiveness status calculation
        self.assertIn(metrics['responsiveness_status'], ['healthy', 'warning', 'critical'])
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_responsiveness_specific_recommendations(self, mock_cpu, mock_memory):
        """Test get_recommendations with responsiveness-specific logic"""
        # Test high memory scenario
        mock_memory.return_value.percent = 85.0  # Above warning threshold
        mock_cpu.return_value = 30.0
        
        recommendations = self.optimizer.get_recommendations()
        
        # Should have memory warning recommendation
        memory_recommendations = [r for r in recommendations if 'memory' in r.get('message', '').lower()]
        self.assertTrue(len(memory_recommendations) > 0)
        
        # Test critical memory scenario
        mock_memory.return_value.percent = 95.0  # Above critical threshold
        recommendations = self.optimizer.get_recommendations()
        
        # Should have critical memory recommendation
        critical_recommendations = [r for r in recommendations if r.get('priority') == 'critical']
        self.assertTrue(len(critical_recommendations) > 0)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_enhanced_health_status(self, mock_cpu, mock_memory):
        """Test get_health_status with responsiveness thresholds"""
        mock_memory.return_value.percent = 70.0
        mock_cpu.return_value = 40.0
        
        health_status = self.optimizer.get_health_status()
        
        # Test that responsiveness monitoring is indicated
        self.assertIn('responsiveness_monitoring', health_status)
        self.assertTrue(health_status['responsiveness_monitoring'])
        
        # Test that thresholds are included
        self.assertIn('thresholds', health_status)
        thresholds = health_status['thresholds']
        self.assertIn('memory_warning', thresholds)
        self.assertIn('memory_critical', thresholds)
        self.assertIn('cpu_warning', thresholds)
        self.assertIn('cpu_critical', thresholds)
        
        # Test component health with responsiveness thresholds
        components = health_status['components']
        self.assertIn('memory', components)
        self.assertIn('cpu', components)
        self.assertIn('connection_pool', components)
        self.assertIn('background_tasks', components)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_check_responsiveness_method(self, mock_cpu, mock_memory):
        """Test new check_responsiveness method"""
        mock_memory.return_value.percent = 60.0
        mock_cpu.return_value = 30.0
        
        responsiveness = self.optimizer.check_responsiveness()
        
        # Test return structure
        self.assertIn('responsive', responsiveness)
        self.assertIn('issues', responsiveness)
        self.assertIn('overall_status', responsiveness)
        self.assertIn('timestamp', responsiveness)
        
        # Test healthy scenario
        self.assertTrue(responsiveness['responsive'])
        self.assertEqual(len(responsiveness['issues']), 0)
        self.assertEqual(responsiveness['overall_status'], 'healthy')
        
        # Test warning scenario
        mock_memory.return_value.percent = 85.0  # Above warning threshold
        responsiveness = self.optimizer.check_responsiveness()
        
        self.assertFalse(responsiveness['responsive'])
        self.assertTrue(len(responsiveness['issues']) > 0)
        self.assertEqual(responsiveness['overall_status'], 'warning')
    
    def test_automated_cleanup_triggers(self):
        """Test trigger_cleanup_if_needed method"""
        # Test normal conditions - no cleanup needed
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 70.0
            cleanup_triggered = self.optimizer.trigger_cleanup_if_needed()
            self.assertFalse(cleanup_triggered)
        
        # Test high memory - should trigger cleanup
        # Set last cleanup time to old enough to allow new cleanup
        self.optimizer._last_cleanup_time = time.time() - 120  # 2 minutes ago
        
        with patch('psutil.virtual_memory') as mock_memory, \
             patch.object(self.optimizer, '_trigger_memory_cleanup') as mock_memory_cleanup:
            mock_memory.return_value.percent = 90.0  # Above auto cleanup threshold (85%)
            
            cleanup_triggered = self.optimizer.trigger_cleanup_if_needed()
            
            if self.optimizer.responsiveness_config.cleanup_enabled:
                self.assertTrue(cleanup_triggered)
                mock_memory_cleanup.assert_called_once()
            else:
                self.assertFalse(cleanup_triggered)
    
    def test_responsiveness_config_from_env(self):
        """Test ResponsivenessConfig.from_env() method"""
        with patch.dict(os.environ, {
            'RESPONSIVENESS_MEMORY_WARNING_THRESHOLD': '0.75',
            'RESPONSIVENESS_MEMORY_CRITICAL_THRESHOLD': '0.85',
            'RESPONSIVENESS_CPU_WARNING_THRESHOLD': '0.70',
            'RESPONSIVENESS_CPU_CRITICAL_THRESHOLD': '0.80',
            'RESPONSIVENESS_CLEANUP_ENABLED': 'false'
        }):
            config = ResponsivenessConfig.from_env()
            
            self.assertEqual(config.memory_warning_threshold, 0.75)
            self.assertEqual(config.memory_critical_threshold, 0.85)
            self.assertEqual(config.cpu_warning_threshold, 0.70)
            self.assertEqual(config.cpu_critical_threshold, 0.80)
            self.assertFalse(config.cleanup_enabled)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_connection_pool_monitoring(self, mock_cpu, mock_memory):
        """Test connection pool utilization monitoring"""
        mock_memory.return_value.percent = 50.0
        mock_cpu.return_value = 25.0
        
        metrics = self.optimizer.get_performance_metrics()
        
        # Test connection pool metrics are present
        self.assertIn('connection_pool_utilization', metrics)
        self.assertIn('active_connections', metrics)
        self.assertIn('max_connections', metrics)
        
        # Test connection pool utilization is reasonable
        utilization = metrics['connection_pool_utilization']
        self.assertGreaterEqual(utilization, 0.0)
        self.assertLessEqual(utilization, 1.0)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_background_task_monitoring(self, mock_cpu, mock_memory):
        """Test background task count monitoring"""
        mock_memory.return_value.percent = 50.0
        mock_cpu.return_value = 25.0
        
        metrics = self.optimizer.get_performance_metrics()
        
        # Test background task metrics are present
        self.assertIn('background_tasks_count', metrics)
        self.assertIn('blocked_requests', metrics)
        
        # Test values are reasonable
        self.assertGreaterEqual(metrics['background_tasks_count'], 0)
        self.assertGreaterEqual(metrics['blocked_requests'], 0)
    
    def test_cleanup_frequency_limiting(self):
        """Test that cleanup operations are rate-limited"""
        # Set last cleanup time to recent
        self.optimizer._last_cleanup_time = time.time() - 30  # 30 seconds ago
        
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 95.0  # Above cleanup threshold
            
            # Should not trigger cleanup due to rate limiting
            cleanup_triggered = self.optimizer.trigger_cleanup_if_needed()
            self.assertFalse(cleanup_triggered)
        
        # Set last cleanup time to old enough
        self.optimizer._last_cleanup_time = time.time() - 120  # 2 minutes ago
        
        with patch('psutil.virtual_memory') as mock_memory, \
             patch.object(self.optimizer, '_trigger_memory_cleanup'):
            mock_memory.return_value.percent = 95.0  # Above cleanup threshold
            
            # Should trigger cleanup now
            cleanup_triggered = self.optimizer.trigger_cleanup_if_needed()
            if self.optimizer.responsiveness_config.cleanup_enabled:
                self.assertTrue(cleanup_triggered)


if __name__ == '__main__':
    unittest.main()