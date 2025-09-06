# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for request performance tracking functionality.

Tests the SystemOptimizer's request tracking capabilities and the request performance middleware.
"""

import unittest
import time
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config


class TestRequestTracking(unittest.TestCase):
    """Test request performance tracking functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        
        # Mock psutil for SystemOptimizer
        self.psutil_mock = Mock()
        self.psutil_mock.virtual_memory.return_value = Mock(
            used=1024*1024*100,  # 100MB
            percent=50.0
        )
        self.psutil_mock.cpu_percent.return_value = 25.0
        
        # Create SystemOptimizer with mocked dependencies
        with patch('psutil.virtual_memory', self.psutil_mock.virtual_memory), \
             patch('psutil.cpu_percent', self.psutil_mock.cpu_percent):
            
            # Import and create SystemOptimizer (simulating web_app.py implementation)
            from web_app import SystemOptimizer
            self.system_optimizer = SystemOptimizer(self.config)
    
    def test_request_tracking_initialization(self):
        """Test that request tracking is properly initialized"""
        self.assertIsNotNone(self.system_optimizer._request_times)
        self.assertIsNotNone(self.system_optimizer._slow_requests)
        self.assertEqual(self.system_optimizer._request_count, 0)
        self.assertEqual(self.system_optimizer._total_request_time, 0.0)
        self.assertEqual(self.system_optimizer._max_request_history, 1000)
        self.assertEqual(self.system_optimizer._slow_request_threshold, 5.0)
    
    def test_track_request_start(self):
        """Test request start tracking"""
        request_data = self.system_optimizer.track_request_start()
        
        if request_data:  # Only test if threading is available
            self.assertIsNotNone(request_data)
            self.assertIn('id', request_data)
            self.assertIn('start_time', request_data)
            self.assertIsInstance(request_data['start_time'], float)
    
    def test_track_request_end(self):
        """Test request end tracking"""
        # Start a request
        request_data = self.system_optimizer.track_request_start()
        
        if request_data:  # Only test if threading is available
            # Simulate some processing time
            time.sleep(0.1)
            
            # End the request
            self.system_optimizer.track_request_end(
                request_data,
                endpoint='/test',
                method='GET',
                status_code=200
            )
            
            # Check that metrics were updated
            self.assertEqual(self.system_optimizer._request_count, 1)
            self.assertGreater(self.system_optimizer._total_request_time, 0)
            self.assertEqual(len(self.system_optimizer._request_times), 1)
    
    def test_slow_request_detection(self):
        """Test slow request detection"""
        # Mock a slow request by setting a low threshold
        original_threshold = self.system_optimizer._slow_request_threshold
        self.system_optimizer._slow_request_threshold = 0.05  # 50ms threshold
        
        try:
            request_data = self.system_optimizer.track_request_start()
            
            if request_data:  # Only test if threading is available
                # Simulate slow processing
                time.sleep(0.1)  # 100ms - should be detected as slow
                
                self.system_optimizer.track_request_end(
                    request_data,
                    endpoint='/slow-endpoint',
                    method='POST',
                    status_code=200
                )
                
                # Check that slow request was detected
                self.assertEqual(len(self.system_optimizer._slow_requests), 1)
                slow_request = self.system_optimizer._slow_requests[0]
                self.assertEqual(slow_request['endpoint'], '/slow-endpoint')
                self.assertEqual(slow_request['method'], 'POST')
                self.assertGreater(slow_request['time'], 0.05)
        finally:
            # Restore original threshold
            self.system_optimizer._slow_request_threshold = original_threshold
    
    def test_get_request_performance_metrics(self):
        """Test getting request performance metrics"""
        metrics = self.system_optimizer._get_request_performance_metrics()
        
        # Check that all expected metrics are present
        expected_keys = [
            'avg_request_time',
            'slow_request_count',
            'total_requests',
            'requests_per_second',
            'request_queue_size',
            'recent_slow_requests'
        ]
        
        for key in expected_keys:
            self.assertIn(key, metrics)
        
        # Check initial values
        self.assertEqual(metrics['avg_request_time'], 0.0)
        self.assertEqual(metrics['slow_request_count'], 0)
        self.assertEqual(metrics['total_requests'], 0)
        self.assertIsInstance(metrics['requests_per_second'], float)
        self.assertIsInstance(metrics['request_queue_size'], int)
        self.assertIsInstance(metrics['recent_slow_requests'], list)
    
    def test_get_slow_request_analysis(self):
        """Test slow request analysis"""
        analysis = self.system_optimizer.get_slow_request_analysis()
        
        # Check that analysis structure is correct
        expected_keys = ['slow_requests', 'analysis']
        for key in expected_keys:
            self.assertIn(key, analysis)
        
        self.assertIsInstance(analysis['slow_requests'], list)
        self.assertIsInstance(analysis['analysis'], dict)
    
    def test_performance_metrics_include_request_data(self):
        """Test that performance metrics include request tracking data"""
        metrics = self.system_optimizer.get_performance_metrics()
        
        # Check that request performance metrics are included
        request_metrics_keys = [
            'avg_request_time',
            'slow_request_count',
            'total_requests',
            'requests_per_second',
            'request_queue_size',
            'recent_slow_requests'
        ]
        
        for key in request_metrics_keys:
            self.assertIn(key, metrics, f"Missing request metric: {key}")
    
    def test_request_history_trimming(self):
        """Test that request history is properly trimmed"""
        if not self.system_optimizer._request_lock:
            self.skipTest("Threading not available")
        
        # Set a small history limit for testing
        original_limit = self.system_optimizer._max_request_history
        self.system_optimizer._max_request_history = 5
        
        try:
            # Add more requests than the limit
            for i in range(10):
                request_data = self.system_optimizer.track_request_start()
                if request_data:
                    self.system_optimizer.track_request_end(
                        request_data,
                        endpoint=f'/test-{i}',
                        method='GET',
                        status_code=200
                    )
            
            # Check that history was trimmed
            self.assertLessEqual(len(self.system_optimizer._request_times), 5)
            
        finally:
            # Restore original limit
            self.system_optimizer._max_request_history = original_limit
    
    def test_request_tracking_without_threading(self):
        """Test request tracking gracefully handles missing threading"""
        # Create SystemOptimizer without threading support
        with patch('threading.Lock', side_effect=ImportError("No threading")):
            optimizer = self.system_optimizer.__class__(self.config)
            
            # Should not crash and should return None for request data
            request_data = optimizer.track_request_start()
            self.assertIsNone(request_data)
            
            # Should not crash when tracking end with None data
            optimizer.track_request_end(None)
            
            # Metrics should still work with default values
            metrics = optimizer._get_request_performance_metrics()
            self.assertEqual(metrics['total_requests'], 0)


class TestRequestPerformanceMiddleware(unittest.TestCase):
    """Test request performance middleware"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Import the middleware
        from request_performance_middleware import RequestPerformanceMiddleware
        self.middleware_class = RequestPerformanceMiddleware
    
    def test_middleware_initialization(self):
        """Test middleware initialization"""
        middleware = self.middleware_class()
        self.assertIsNotNone(middleware)
    
    def test_middleware_app_initialization(self):
        """Test middleware initialization with Flask app"""
        # Mock Flask app
        mock_app = Mock()
        mock_app.before_request = Mock()
        mock_app.after_request = Mock()
        mock_app.teardown_appcontext = Mock()
        
        middleware = self.middleware_class(mock_app)
        
        # Check that Flask hooks were registered
        mock_app.before_request.assert_called_once()
        mock_app.after_request.assert_called_once()
        mock_app.teardown_appcontext.assert_called_once()
    
    @patch('request_performance_middleware.current_app')
    @patch('request_performance_middleware.g')
    def test_before_request_tracking(self, mock_g, mock_current_app):
        """Test before_request tracking"""
        # Mock system optimizer
        mock_optimizer = Mock()
        mock_optimizer.track_request_start.return_value = {'id': 'test', 'start_time': time.time()}
        mock_current_app.system_optimizer = mock_optimizer
        
        # Mock request
        mock_request = Mock()
        mock_request.method = 'GET'
        mock_request.endpoint = '/test'
        
        with patch('request_performance_middleware.request', mock_request):
            middleware = self.middleware_class()
            middleware.before_request()
            
            # Check that tracking was called
            mock_optimizer.track_request_start.assert_called_once()
    
    @patch('request_performance_middleware.current_app')
    @patch('request_performance_middleware.g')
    def test_after_request_tracking(self, mock_g, mock_current_app):
        """Test after_request tracking"""
        # Mock system optimizer
        mock_optimizer = Mock()
        mock_current_app.system_optimizer = mock_optimizer
        
        # Mock request data
        mock_g.request_performance_data = {'id': 'test', 'start_time': time.time()}
        
        # Mock request and response
        mock_request = Mock()
        mock_request.endpoint = '/test'
        mock_request.method = 'GET'
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch('request_performance_middleware.request', mock_request):
            middleware = self.middleware_class()
            result = middleware.after_request(mock_response)
            
            # Check that tracking was called
            mock_optimizer.track_request_end.assert_called_once()
            # Check that response was returned unchanged
            self.assertEqual(result, mock_response)


if __name__ == '__main__':
    unittest.main()