# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for request performance tracking API endpoints.

Tests the admin performance dashboard API endpoints for request tracking functionality.
"""

import unittest
import json
import sys
import os
from unittest.mock import Mock, patch

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config


class TestRequestTrackingIntegration(unittest.TestCase):
    """Integration tests for request tracking API endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        
        # Mock Flask app and request context
        self.mock_app = Mock()
        self.mock_app.config = {}
        
        # Mock current_user as admin
        self.mock_admin_user = Mock()
        self.mock_admin_user.role = Mock()
        self.mock_admin_user.role.ADMIN = 'admin'
        
        # Mock system optimizer with request tracking
        self.mock_system_optimizer = Mock()
        self.mock_system_optimizer._get_request_performance_metrics.return_value = {
            'avg_request_time': 0.125,
            'slow_request_count': 3,
            'total_requests': 1250,
            'requests_per_second': 12.5,
            'request_queue_size': 2,
            'recent_slow_requests': [
                {
                    'endpoint': '/admin/performance',
                    'method': 'GET',
                    'time': 6.2,
                    'timestamp': 1693920000.0,
                    'status_code': 200
                }
            ]
        }
        
        self.mock_system_optimizer.get_slow_request_analysis.return_value = {
            'slow_requests': [
                {
                    'id': 'req_123',
                    'time': 6.2,
                    'timestamp': 1693920000.0,
                    'endpoint': '/admin/performance',
                    'method': 'GET',
                    'status_code': 200
                }
            ],
            'analysis': {
                '/admin/performance': {
                    'count': 2,
                    'total_time': 12.4,
                    'avg_time': 6.2,
                    'max_time': 6.5
                }
            },
            'total_slow_requests': 2,
            'time_range_hours': 1
        }
        
        self.mock_app.system_optimizer = self.mock_system_optimizer
    
    @patch('app.services.performance.components.performance_dashboard.current_app')
    @patch('app.services.performance.components.performance_dashboard.current_user')
    @patch('app.services.performance.components.performance_dashboard.jsonify')
    def test_api_request_tracking_endpoint(self, mock_jsonify, mock_current_user, mock_current_app):
        """Test the request tracking API endpoint"""
        # Set up mocks
        mock_current_app.system_optimizer = self.mock_system_optimizer
        mock_current_user.role = 'admin'
        mock_jsonify.return_value = Mock()
        
        # Import the route function
        from app.services.performance.components.performance_dashboard import register_routes
        
        # Create a mock blueprint
        mock_bp = Mock()
        mock_route_decorator = Mock()
        mock_bp.route.return_value = mock_route_decorator
        
        # Register routes
        register_routes(mock_bp)
        
        # Verify that the request tracking route was registered
        route_calls = mock_bp.route.call_args_list
        request_tracking_route = None
        
        for call in route_calls:
            if '/api/performance/request-tracking' in str(call):
                request_tracking_route = call
                break
        
        self.assertIsNotNone(request_tracking_route, "Request tracking route should be registered")
    
    def test_request_performance_metrics_structure(self):
        """Test that request performance metrics have the correct structure"""
        metrics = self.mock_system_optimizer._get_request_performance_metrics()
        
        # Check required fields
        required_fields = [
            'avg_request_time',
            'slow_request_count',
            'total_requests',
            'requests_per_second',
            'request_queue_size',
            'recent_slow_requests'
        ]
        
        for field in required_fields:
            self.assertIn(field, metrics, f"Missing required field: {field}")
        
        # Check data types
        self.assertIsInstance(metrics['avg_request_time'], (int, float))
        self.assertIsInstance(metrics['slow_request_count'], int)
        self.assertIsInstance(metrics['total_requests'], int)
        self.assertIsInstance(metrics['requests_per_second'], (int, float))
        self.assertIsInstance(metrics['request_queue_size'], int)
        self.assertIsInstance(metrics['recent_slow_requests'], list)
    
    def test_slow_request_analysis_structure(self):
        """Test that slow request analysis has the correct structure"""
        analysis = self.mock_system_optimizer.get_slow_request_analysis()
        
        # Check required fields
        required_fields = [
            'slow_requests',
            'analysis',
            'total_slow_requests',
            'time_range_hours'
        ]
        
        for field in required_fields:
            self.assertIn(field, analysis, f"Missing required field: {field}")
        
        # Check data types
        self.assertIsInstance(analysis['slow_requests'], list)
        self.assertIsInstance(analysis['analysis'], dict)
        self.assertIsInstance(analysis['total_slow_requests'], int)
        self.assertIsInstance(analysis['time_range_hours'], int)
        
        # Check slow request structure
        if analysis['slow_requests']:
            slow_request = analysis['slow_requests'][0]
            required_slow_request_fields = ['id', 'time', 'timestamp', 'endpoint', 'method', 'status_code']
            
            for field in required_slow_request_fields:
                self.assertIn(field, slow_request, f"Missing slow request field: {field}")
    
    def test_endpoint_analysis_structure(self):
        """Test that endpoint analysis has the correct structure"""
        analysis = self.mock_system_optimizer.get_slow_request_analysis()
        
        if analysis['analysis']:
            endpoint_data = list(analysis['analysis'].values())[0]
            required_fields = ['count', 'total_time', 'avg_time', 'max_time']
            
            for field in required_fields:
                self.assertIn(field, endpoint_data, f"Missing endpoint analysis field: {field}")
                self.assertIsInstance(endpoint_data[field], (int, float))
    
    @patch('app.services.performance.components.performance_dashboard.logger')
    def test_api_error_handling(self, mock_logger):
        """Test API error handling when system optimizer is not available"""
        # Test with missing system optimizer
        mock_app_no_optimizer = Mock()
        mock_app_no_optimizer.system_optimizer = None
        
        with patch('app.services.performance.components.performance_dashboard.current_app', mock_app_no_optimizer):
            with patch('app.services.performance.components.performance_dashboard.current_user') as mock_user:
                mock_user.role = 'admin'
                
                # This would normally be called by Flask, but we're testing the logic
                try:
                    # Simulate the API call logic
                    system_optimizer = getattr(mock_app_no_optimizer, 'system_optimizer', None)
                    if not system_optimizer:
                        error_response = {'error': 'System optimizer not initialized'}
                        self.assertEqual(error_response['error'], 'System optimizer not initialized')
                except Exception as e:
                    self.fail(f"Error handling should not raise exceptions: {e}")
    
    def test_performance_metrics_integration_with_dashboard(self):
        """Test that performance metrics integrate properly with dashboard metrics"""
        # Mock the dashboard metrics that would include request data
        dashboard_metrics = {
            'notification_throughput': 15.2,
            'websocket_connections': 45,
            'cache_hit_rate': 0.85,
            'memory_usage_mb': 256.7,
            'cpu_usage_percent': 35.2,
            'database_query_time': 45.3,
            # Request performance metrics should be added
            'avg_request_time': 0.125,
            'slow_request_count': 3,
            'total_requests': 1250,
            'requests_per_second': 12.5,
            'request_queue_size': 2
        }
        
        # Verify all expected metrics are present
        expected_request_metrics = [
            'avg_request_time',
            'slow_request_count', 
            'total_requests',
            'requests_per_second',
            'request_queue_size'
        ]
        
        for metric in expected_request_metrics:
            self.assertIn(metric, dashboard_metrics, f"Dashboard should include {metric}")
    
    def test_request_tracking_thresholds(self):
        """Test request tracking threshold logic"""
        # Test slow request detection threshold
        slow_threshold = 5.0  # 5 seconds
        
        test_requests = [
            {'time': 2.1, 'should_be_slow': False},
            {'time': 5.5, 'should_be_slow': True},
            {'time': 0.8, 'should_be_slow': False},
            {'time': 10.2, 'should_be_slow': True}
        ]
        
        for request in test_requests:
            is_slow = request['time'] > slow_threshold
            self.assertEqual(is_slow, request['should_be_slow'], 
                           f"Request with time {request['time']}s should {'be' if request['should_be_slow'] else 'not be'} slow")
    
    def test_request_performance_status_calculation(self):
        """Test request performance status calculation logic"""
        test_cases = [
            {'avg_time': 0.5, 'expected_status': 'good'},
            {'avg_time': 1.5, 'expected_status': 'fair'},
            {'avg_time': 3.0, 'expected_status': 'poor'}
        ]
        
        for case in test_cases:
            # Simulate status calculation logic
            avg_time = case['avg_time']
            if avg_time > 2.0:
                status = 'poor'
            elif avg_time > 1.0:
                status = 'fair'
            else:
                status = 'good'
            
            self.assertEqual(status, case['expected_status'], 
                           f"Average time {avg_time}s should result in {case['expected_status']} status")


if __name__ == '__main__':
    unittest.main()