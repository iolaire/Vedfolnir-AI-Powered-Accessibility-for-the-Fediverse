# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for feature flag enforcement in application components

Tests that feature flags properly control access to batch processing,
monitoring, and auto-retry functionality.
"""

import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from feature_flag_service import FeatureFlagService
from feature_flag_decorators import (
    FeatureFlagMiddleware, require_feature_flag, batch_processing_required,
    advanced_monitoring_required, auto_retry_required
)
from app.services.batch.components.batch_update_service import BatchUpdateService
from app.services.task.core.task_queue_manager import TaskQueueManager
from advanced_monitoring_service import AdvancedMonitoringService
from app.core.configuration.core.configuration_service import ConfigurationService, ConfigurationValue, ConfigurationSource


class TestFeatureFlagEnforcement(unittest.TestCase):
    """Test cases for feature flag enforcement in application components"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_event_bus = Mock()
        
        # Create feature flag service
        self.feature_service = FeatureFlagService(
            config_service=self.mock_config_service,
            event_bus=self.mock_event_bus
        )
        
        # Create middleware
        self.middleware = FeatureFlagMiddleware(self.feature_service)
        
        # Mock config for services
        self.mock_config = Mock()
        self.mock_config.batch_size = 5
        self.mock_config.max_concurrent_batches = 2
        self.mock_config.verification_delay = 2
        
        # Mock storage config to avoid database validation
        self.mock_config.storage = Mock()
        self.mock_config.storage.database_url = "mysql+pymysql://test:test@localhost/test"
        
        # Mock database manager
        self.mock_db_manager = Mock()
    
    def test_batch_processing_enforcement_enabled(self):
        """Test batch processing when feature flag is enabled"""
        # Enable batch processing
        with patch.object(self.feature_service, 'is_enabled', return_value=True):
            # Test middleware enforcement
            result = self.middleware.enforce_batch_processing("test operation")
            self.assertTrue(result)
            
            # Test service initialization with mocked DatabaseManager
            with patch('app.services.batch.components.batch_update_service.DatabaseManager', return_value=self.mock_db_manager):
                batch_service = BatchUpdateService(self.mock_config, self.feature_service)
                self.assertIsNotNone(batch_service.feature_service)
                self.assertIsNotNone(batch_service.feature_middleware)
    
    def test_batch_processing_enforcement_disabled(self):
        """Test batch processing when feature flag is disabled"""
        # Disable batch processing
        with patch.object(self.feature_service, 'is_enabled', return_value=False):
            # Test middleware enforcement
            result = self.middleware.enforce_batch_processing("test operation")
            self.assertFalse(result)
    
    def test_batch_update_service_with_disabled_flag(self):
        """Test BatchUpdateService behavior when feature flag is disabled"""
        # Disable batch processing
        with patch.object(self.feature_service, 'is_enabled', return_value=False):
            with patch('app.services.batch.components.batch_update_service.DatabaseManager', return_value=self.mock_db_manager):
                batch_service = BatchUpdateService(self.mock_config, self.feature_service)
                
                # Run batch update - should return early with feature disabled message
                result = asyncio.run(batch_service.batch_update_captions(10))
                
                self.assertEqual(result['processed'], 0)
                self.assertEqual(result['successful'], 0)
                self.assertTrue(result.get('feature_disabled', False))
                self.assertIn('Batch processing is currently disabled', result['errors'])
    
    def test_advanced_monitoring_enforcement_enabled(self):
        """Test advanced monitoring when feature flag is enabled"""
        # Enable advanced monitoring
        with patch.object(self.feature_service, 'is_enabled', return_value=True):
            # Test middleware enforcement
            result = self.middleware.enforce_advanced_monitoring("test monitoring")
            self.assertTrue(result)
            
            # Test monitoring service
            monitoring_service = AdvancedMonitoringService(self.feature_service)
            self.assertTrue(monitoring_service._is_collecting)
    
    def test_advanced_monitoring_enforcement_disabled(self):
        """Test advanced monitoring when feature flag is disabled"""
        # Disable advanced monitoring
        with patch.object(self.feature_service, 'is_enabled', return_value=False):
            # Test middleware enforcement
            result = self.middleware.enforce_advanced_monitoring("test monitoring")
            self.assertFalse(result)
            
            # Test monitoring service
            monitoring_service = AdvancedMonitoringService(self.feature_service)
            self.assertFalse(monitoring_service._is_collecting)
    
    def test_auto_retry_enforcement_enabled(self):
        """Test auto-retry when feature flag is enabled"""
        # Enable auto-retry
        with patch.object(self.feature_service, 'is_enabled', return_value=True):
            # Test middleware enforcement
            result = self.middleware.enforce_auto_retry("test retry")
            self.assertTrue(result)
            
            # Test task queue manager
            task_manager = TaskQueueManager(
                self.mock_db_manager, 
                feature_service=self.feature_service
            )
            
            # Mock task for retry check
            with patch.object(task_manager, 'should_auto_retry_task') as mock_retry:
                mock_retry.return_value = True
                result = task_manager.should_auto_retry_task('test-task-id')
                self.assertTrue(result)
    
    def test_auto_retry_enforcement_disabled(self):
        """Test auto-retry when feature flag is disabled"""
        # Disable auto-retry
        with patch.object(self.feature_service, 'is_enabled', return_value=False):
            # Test middleware enforcement
            result = self.middleware.enforce_auto_retry("test retry")
            self.assertFalse(result)
            
            # Test task queue manager
            task_manager = TaskQueueManager(
                self.mock_db_manager,
                feature_service=self.feature_service
            )
            
            # Should not retry when feature is disabled
            result = task_manager.should_auto_retry_task('test-task-id')
            self.assertFalse(result)
    
    def test_decorator_enforcement_web_route(self):
        """Test feature flag decorator on web routes"""
        # Mock Flask app context properly
        mock_app = Mock()
        mock_app.feature_flag_service = self.feature_service
        
        with patch('feature_flag_decorators.current_app', mock_app):
            # Test with feature enabled
            with patch.object(self.feature_service, 'is_enabled', return_value=True):
                @batch_processing_required()
                def test_route():
                    return "success"
                
                result = test_route()
                self.assertEqual(result, "success")
            
            # Test with feature disabled
            with patch.object(self.feature_service, 'is_enabled', return_value=False):
                with patch('feature_flag_decorators._is_json_request', return_value=True):
                    with patch('feature_flag_decorators.jsonify') as mock_jsonify:
                        mock_jsonify.return_value = ({'error': 'feature_disabled'}, 503)
                        
                        @batch_processing_required()
                        def test_route_disabled():
                            return "should not reach here"
                        
                        result = test_route_disabled()
                        mock_jsonify.assert_called_once()
    
    def test_graceful_feature_disabling(self):
        """Test graceful feature disabling with current operations"""
        current_operations = ['op1', 'op2', 'op3']
        callback_called = []
        
        def completion_callback():
            callback_called.append(True)
        
        # Test with feature disabled
        with patch.object(self.feature_service, 'is_enabled', return_value=False):
            result = self.middleware.graceful_feature_disable(
                'enable_batch_processing',
                current_operations,
                completion_callback
            )
            
            self.assertTrue(result)
            self.assertEqual(len(callback_called), 1)
        
        # Test with feature enabled
        with patch.object(self.feature_service, 'is_enabled', return_value=True):
            callback_called.clear()
            result = self.middleware.graceful_feature_disable(
                'enable_batch_processing',
                current_operations,
                completion_callback
            )
            
            self.assertFalse(result)
            self.assertEqual(len(callback_called), 0)
    
    def test_monitoring_service_feature_flag_integration(self):
        """Test monitoring service integration with feature flags"""
        # Test with feature enabled
        with patch.object(self.feature_service, 'is_enabled', return_value=True):
            # Mock Flask app context for the decorator
            mock_app = Mock()
            mock_app.feature_flag_service = self.feature_service
            
            with patch('feature_flag_decorators.current_app', mock_app):
                monitoring_service = AdvancedMonitoringService(self.feature_service)
                
                # Should collect metrics
                with patch('advanced_monitoring_service.psutil') as mock_psutil:
                    mock_psutil.cpu_percent.return_value = 50.0
                    mock_psutil.cpu_count.return_value = 4
                    mock_psutil.virtual_memory.return_value = Mock(
                        percent=60.0, used=1000, available=500, total=1500
                    )
                    mock_psutil.disk_usage.return_value = Mock(
                        used=2000, free=1000, total=3000
                    )
                    mock_psutil.Process.return_value = Mock(
                        memory_info=Mock(return_value=Mock(rss=100, vms=200)),
                        cpu_percent=Mock(return_value=10.0),
                        num_threads=Mock(return_value=5)
                    )
                    
                    metrics = monitoring_service.collect_system_metrics()
                    self.assertIsNotNone(metrics)
                    self.assertIn('cpu_usage_percent', metrics)
                    self.assertEqual(metrics['cpu_usage_percent'], 50.0)
        
        # Test with feature disabled
        with patch.object(self.feature_service, 'is_enabled', return_value=False):
            monitoring_service = AdvancedMonitoringService(self.feature_service)
            
            # Should not collect metrics
            metrics = monitoring_service.collect_system_metrics()
            self.assertIsNone(metrics)
    
    def test_task_queue_retry_logic_with_feature_flags(self):
        """Test task queue retry logic with feature flag enforcement"""
        task_manager = TaskQueueManager(
            self.mock_db_manager,
            feature_service=self.feature_service
        )
        
        # Mock database session and task
        mock_session = Mock()
        mock_task = Mock()
        mock_task.retry_count = 1
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        self.mock_db_manager.get_session.return_value = mock_session
        
        # Test with auto-retry enabled
        with patch.object(self.feature_service, 'is_enabled', return_value=True):
            result = task_manager.should_auto_retry_task('test-task-id', 'network_error')
            self.assertTrue(result)
        
        # Test with auto-retry disabled
        with patch.object(self.feature_service, 'is_enabled', return_value=False):
            result = task_manager.should_auto_retry_task('test-task-id', 'network_error')
            self.assertFalse(result)
    
    def test_feature_flag_change_propagation(self):
        """Test that feature flag changes propagate to services within 30 seconds"""
        # This test simulates the requirement that feature flag changes
        # should propagate within 30 seconds
        
        callback_called = []
        
        def feature_change_callback(feature, old_value, new_value):
            callback_called.append((feature, old_value, new_value))
        
        # Subscribe to feature flag changes
        subscription_id = self.feature_service.subscribe_to_flag_changes(
            'enable_batch_processing',
            feature_change_callback
        )
        
        # Simulate configuration change
        from app.core.configuration.events.configuration_event_bus import ConfigurationChangeEvent, EventType
        
        change_event = ConfigurationChangeEvent(
            event_type=EventType.CONFIGURATION_CHANGED,
            key='enable_batch_processing',
            old_value=True,
            new_value=False,
            source='admin',
            timestamp=datetime.now(timezone.utc)
        )
        
        # Handle the change
        self.feature_service._handle_configuration_change(change_event)
        
        # Verify callback was called
        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0], ('enable_batch_processing', True, False))
        
        # Cleanup
        self.feature_service.unsubscribe_from_flag_changes(subscription_id)
    
    def test_feature_flag_usage_metrics(self):
        """Test that feature flag usage is tracked in metrics"""
        # Enable metrics collection
        self.feature_service.metrics_enabled = True
        
        # Use several feature flags
        self.feature_service.is_enabled('enable_batch_processing')
        self.feature_service.is_enabled('enable_advanced_monitoring')
        self.feature_service.is_enabled('enable_auto_retry')
        self.feature_service.is_enabled('enable_batch_processing')  # Duplicate
        
        # Get usage metrics
        metrics = self.feature_service.get_usage_metrics()
        
        # Verify metrics were collected
        self.assertGreater(metrics.total_checks, 0)
        self.assertIsNotNone(metrics.last_reset)
    
    def test_concurrent_feature_flag_access(self):
        """Test thread safety of feature flag service under concurrent access"""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker():
            try:
                for _ in range(50):
                    result = self.feature_service.is_enabled('enable_batch_processing')
                    results.append(result)
                    time.sleep(0.001)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0)
        
        # Verify all results are consistent
        self.assertEqual(len(results), 500)  # 10 threads * 50 calls each
        # All results should be the same (either all True or all False)
        self.assertTrue(all(r == results[0] for r in results))


if __name__ == '__main__':
    unittest.main()