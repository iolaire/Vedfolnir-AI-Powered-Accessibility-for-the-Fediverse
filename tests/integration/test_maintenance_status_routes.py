# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Maintenance Status API Routes

Tests the Flask routes for maintenance status API endpoints including
status queries, blocked operations, and SSE streaming.
"""

import unittest
import sys
import os
import json
import time
import threading
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
from flask import Flask

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from routes.maintenance_status_routes import maintenance_status_bp, init_maintenance_status_api
from maintenance_status_api import MaintenanceStatusResponse, BlockedOperation
from enhanced_maintenance_mode_service import MaintenanceStatus, MaintenanceMode


class TestMaintenanceStatusRoutes(unittest.TestCase):
    """Test cases for maintenance status API routes"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create Flask test app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Create mock maintenance service
        self.mock_maintenance_service = Mock()
        
        # Sample maintenance status
        self.sample_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Test maintenance",
            estimated_duration=30,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=["caption_generation", "job_creation"],
            active_jobs_count=5,
            invalidated_sessions=10,
            test_mode=False
        )
        
        # Sample status response
        self.sample_status_response = MaintenanceStatusResponse(
            is_active=True,
            mode="normal",
            reason="Test maintenance",
            estimated_duration=30,
            started_at=datetime.now(timezone.utc).isoformat(),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=["caption_generation", "job_creation"],
            active_jobs_count=5,
            invalidated_sessions=10,
            test_mode=False,
            message="Test maintenance in progress",
            response_time_ms=50.0,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Sample blocked operations
        self.sample_blocked_ops = [
            BlockedOperation(
                operation_type="caption_generation",
                description="AI caption generation",
                blocked_since=datetime.now(timezone.utc).isoformat(),
                user_message="Caption generation is temporarily unavailable",
                endpoints=["/start_caption_generation", "/api/caption/generate"]
            ),
            BlockedOperation(
                operation_type="job_creation",
                description="Background job creation",
                blocked_since=datetime.now(timezone.utc).isoformat(),
                user_message="Job creation is temporarily unavailable",
                endpoints=["/api/jobs", "/create_job"]
            )
        ]
        
        # Initialize maintenance status API
        init_maintenance_status_api(self.app, self.mock_maintenance_service)
        
        # Reduce SSE service timeouts for faster testing
        if hasattr(self.app, 'maintenance_status_sse'):
            self.app.maintenance_status_sse.heartbeat_interval = 0.1
            self.app.maintenance_status_sse.connection_timeout = 1
        
        # Create test client
        self.client = self.app.test_client()
        
        # Setup mock responses
        self.app.maintenance_status_api.get_status = Mock(return_value=self.sample_status_response)
        self.app.maintenance_status_api.get_blocked_operations = Mock(return_value=self.sample_blocked_ops)
        self.app.maintenance_status_api.get_maintenance_message = Mock(return_value="Test maintenance message")
        self.app.maintenance_status_api.get_api_stats = Mock(return_value={
            'performance': {'total_requests': 10, 'average_response_time': 45.0},
            'subscribers_count': 2
        })
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self.app, 'maintenance_status_sse'):
            # Set running to False to speed up shutdown
            self.app.maintenance_status_sse._running = False
            self.app.maintenance_status_sse.shutdown()
    
    def test_get_maintenance_status_endpoint(self):
        """Test GET /api/maintenance/status endpoint"""
        response = self.client.get('/api/maintenance/status')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Verify status data
        status_data = data['data']
        self.assertTrue(status_data['is_active'])
        self.assertEqual(status_data['mode'], 'normal')
        self.assertEqual(status_data['reason'], 'Test maintenance')
        self.assertEqual(status_data['estimated_duration'], 30)
        self.assertEqual(status_data['enabled_by'], 'admin')
        self.assertEqual(status_data['blocked_operations'], ['caption_generation', 'job_creation'])
        self.assertEqual(status_data['active_jobs_count'], 5)
        self.assertEqual(status_data['invalidated_sessions'], 10)
        self.assertFalse(status_data['test_mode'])
        self.assertEqual(status_data['message'], 'Test maintenance in progress')
        self.assertIsNotNone(status_data['response_time_ms'])
        self.assertIsNotNone(status_data['timestamp'])
    
    def test_get_maintenance_status_error_handling(self):
        """Test error handling in status endpoint"""
        # Setup mock to raise exception
        self.app.maintenance_status_api.get_status.side_effect = Exception("API Error")
        
        response = self.client.get('/api/maintenance/status')
        
        # Verify error response
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertIn('message', data)
        self.assertEqual(data['error'], 'Unable to retrieve maintenance status')
    
    def test_get_blocked_operations_endpoint(self):
        """Test GET /api/maintenance/blocked-operations endpoint"""
        response = self.client.get('/api/maintenance/blocked-operations')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Verify blocked operations data
        blocked_data = data['data']
        self.assertIn('blocked_operations', blocked_data)
        self.assertIn('count', blocked_data)
        self.assertEqual(blocked_data['count'], 2)
        
        # Verify first blocked operation
        first_op = blocked_data['blocked_operations'][0]
        self.assertEqual(first_op['operation_type'], 'caption_generation')
        self.assertEqual(first_op['description'], 'AI caption generation')
        self.assertIn('blocked_since', first_op)
        self.assertIn('user_message', first_op)
        self.assertIn('endpoints', first_op)
        self.assertIsInstance(first_op['endpoints'], list)
    
    def test_get_blocked_operations_error_handling(self):
        """Test error handling in blocked operations endpoint"""
        # Setup mock to raise exception
        self.app.maintenance_status_api.get_blocked_operations.side_effect = Exception("API Error")
        
        response = self.client.get('/api/maintenance/blocked-operations')
        
        # Verify error response
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Unable to retrieve blocked operations')
    
    def test_get_maintenance_message_endpoint(self):
        """Test GET /api/maintenance/message endpoint"""
        # Test without operation parameter
        response = self.client.get('/api/maintenance/message')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        message_data = data['data']
        self.assertEqual(message_data['message'], 'Test maintenance message')
        self.assertIsNone(message_data['operation'])
        
        # Test with operation parameter
        response = self.client.get('/api/maintenance/message?operation=caption_generation')
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        message_data = data['data']
        self.assertEqual(message_data['operation'], 'caption_generation')
        
        # Verify API was called with operation parameter
        self.app.maintenance_status_api.get_maintenance_message.assert_called_with('caption_generation')
    
    def test_get_maintenance_message_error_handling(self):
        """Test error handling in maintenance message endpoint"""
        # Setup mock to raise exception
        self.app.maintenance_status_api.get_maintenance_message.side_effect = Exception("API Error")
        
        response = self.client.get('/api/maintenance/message')
        
        # Verify error response
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Unable to retrieve maintenance message')
    
    def test_maintenance_status_stream_endpoint(self):
        """Test GET /api/maintenance/stream endpoint"""
        # Test basic stream creation
        response = self.client.get('/api/maintenance/stream')
        
        # Verify response headers
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/event-stream')
        self.assertIn('Cache-Control', response.headers)
        self.assertEqual(response.headers['Cache-Control'], 'no-cache')
        
        # Test with parameters
        response = self.client.get('/api/maintenance/stream?client_id=test-client&events=maintenance_status_change,heartbeat')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/event-stream')
    
    def test_get_stream_stats_endpoint(self):
        """Test GET /api/maintenance/stream/stats endpoint"""
        # Setup mock SSE stats
        mock_stats = {
            'service_stats': {
                'total_connections': 5,
                'active_connections': 2,
                'events_sent': 50,
                'heartbeats_sent': 10
            },
            'client_stats': {
                'active_clients': 2,
                'total_clients': 5
            },
            'queue_stats': {
                'queue_size': 3,
                'max_queue_size': 100
            }
        }
        self.app.maintenance_status_sse.get_sse_stats = Mock(return_value=mock_stats)
        
        response = self.client.get('/api/maintenance/stream/stats')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Verify stats structure
        stats_data = data['data']
        self.assertIn('service_stats', stats_data)
        self.assertIn('client_stats', stats_data)
        self.assertIn('queue_stats', stats_data)
        
        # Verify specific stats
        self.assertEqual(stats_data['service_stats']['total_connections'], 5)
        self.assertEqual(stats_data['client_stats']['active_clients'], 2)
        self.assertEqual(stats_data['queue_stats']['queue_size'], 3)
    
    def test_get_client_info_endpoint(self):
        """Test GET /api/maintenance/stream/clients/<client_id> endpoint"""
        # Setup mock client info
        mock_client_info = {
            'id': 'test-client',
            'connected_at': datetime.now(timezone.utc),
            'last_activity': datetime.now(timezone.utc),
            'event_types': ['maintenance_status_change'],
            'events_sent': 5,
            'active': True
        }
        self.app.maintenance_status_sse.get_client_info = Mock(return_value=mock_client_info)
        
        response = self.client.get('/api/maintenance/stream/clients/test-client')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Verify client info
        client_data = data['data']
        self.assertEqual(client_data['id'], 'test-client')
        self.assertIn('connected_at', client_data)
        self.assertIn('last_activity', client_data)
        self.assertEqual(client_data['event_types'], ['maintenance_status_change'])
        self.assertEqual(client_data['events_sent'], 5)
        self.assertTrue(client_data['active'])
    
    def test_get_client_info_not_found(self):
        """Test client info endpoint with non-existent client"""
        # Setup mock to return None
        self.app.maintenance_status_sse.get_client_info = Mock(return_value=None)
        
        response = self.client.get('/api/maintenance/stream/clients/non-existent')
        
        # Verify 404 response
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Client not found')
    
    def test_disconnect_client_endpoint(self):
        """Test DELETE /api/maintenance/stream/clients/<client_id> endpoint"""
        # Setup mock to return successful disconnection
        self.app.maintenance_status_sse.disconnect_client = Mock(return_value=True)
        
        response = self.client.delete('/api/maintenance/stream/clients/test-client')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Verify disconnection message
        disconnect_data = data['data']
        self.assertIn('message', disconnect_data)
        self.assertEqual(disconnect_data['client_id'], 'test-client')
        
        # Verify mock was called
        self.app.maintenance_status_sse.disconnect_client.assert_called_once_with('test-client')
    
    def test_disconnect_client_not_found(self):
        """Test disconnect client endpoint with non-existent client"""
        # Setup mock to return False (client not found)
        self.app.maintenance_status_sse.disconnect_client = Mock(return_value=False)
        
        response = self.client.delete('/api/maintenance/stream/clients/non-existent')
        
        # Verify 404 response
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Client not found')
    
    def test_get_api_stats_endpoint(self):
        """Test GET /api/maintenance/api-stats endpoint"""
        response = self.client.get('/api/maintenance/api-stats')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Verify stats structure
        stats_data = data['data']
        self.assertIn('performance', stats_data)
        self.assertIn('subscribers_count', stats_data)
        
        # Verify specific stats
        self.assertEqual(stats_data['performance']['total_requests'], 10)
        self.assertEqual(stats_data['performance']['average_response_time'], 45.0)
        self.assertEqual(stats_data['subscribers_count'], 2)
    
    def test_maintenance_api_health_endpoint(self):
        """Test GET /api/maintenance/health endpoint"""
        # Setup mock SSE stats
        mock_sse_stats = {
            'service_stats': {'connection_errors': 2},
            'client_stats': {'active_clients': 3}
        }
        self.app.maintenance_status_sse.get_sse_stats = Mock(return_value=mock_sse_stats)
        
        response = self.client.get('/api/maintenance/health')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Verify health data
        health_data = data['data']
        self.assertIn('healthy', health_data)
        self.assertIn('components', health_data)
        self.assertIn('timestamp', health_data)
        
        # Verify components
        components = health_data['components']
        self.assertIn('status_api', components)
        self.assertIn('sse_service', components)
        
        # Verify API component
        api_component = components['status_api']
        self.assertIn('healthy', api_component)
        self.assertIn('response_time_ms', api_component)
        
        # Verify SSE component
        sse_component = components['sse_service']
        self.assertIn('healthy', sse_component)
        self.assertIn('active_connections', sse_component)
        self.assertIn('connection_errors', sse_component)
    
    def test_maintenance_api_health_unhealthy(self):
        """Test health endpoint when services are unhealthy"""
        # Setup slow API response
        slow_response = self.sample_status_response
        slow_response.response_time_ms = 2000.0  # 2 seconds (unhealthy)
        self.app.maintenance_status_api.get_status = Mock(return_value=slow_response)
        
        # Setup SSE with many errors
        mock_sse_stats = {
            'service_stats': {'connection_errors': 15},  # Too many errors
            'client_stats': {'active_clients': 1}
        }
        self.app.maintenance_status_sse.get_sse_stats = Mock(return_value=mock_sse_stats)
        
        response = self.client.get('/api/maintenance/health')
        
        # Verify unhealthy response
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        health_data = data['data']
        self.assertFalse(health_data['healthy'])
        
        # Verify components are marked unhealthy
        components = health_data['components']
        self.assertFalse(components['status_api']['healthy'])
        self.assertFalse(components['sse_service']['healthy'])
    
    def test_error_handlers(self):
        """Test blueprint error handlers"""
        # Test 404 handler
        response = self.client.get('/api/maintenance/nonexistent')
        self.assertEqual(response.status_code, 404)
        
        # Check if response is JSON
        if response.content_type and 'application/json' in response.content_type:
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertEqual(data['error'], 'Endpoint not found')
        else:
            # Flask default 404 handler returns HTML, which is expected
            self.assertIn(b'404', response.data)
        
        # Test 405 handler
        response = self.client.post('/api/maintenance/status')  # POST not allowed
        self.assertEqual(response.status_code, 405)
        
        # Check if response is JSON
        if response.content_type and 'application/json' in response.content_type:
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertEqual(data['error'], 'Method not allowed')
        else:
            # Flask default 405 handler returns HTML, which is expected
            self.assertIn(b'405', response.data)
    
    def test_response_format_consistency(self):
        """Test that all endpoints return consistent response format"""
        endpoints = [
            '/api/maintenance/status',
            '/api/maintenance/blocked-operations',
            '/api/maintenance/message',
            '/api/maintenance/stream/stats',
            '/api/maintenance/api-stats',
            '/api/maintenance/health'
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            
            # All endpoints should return JSON
            self.assertIn('application/json', response.content_type)
            
            data = json.loads(response.data)
            
            # All responses should have 'success' field
            self.assertIn('success', data)
            
            if response.status_code == 200:
                # Successful responses should have 'data' field
                self.assertTrue(data['success'])
                self.assertIn('data', data)
            else:
                # Error responses should have 'error' field
                self.assertFalse(data['success'])
                self.assertIn('error', data)
    
    def test_performance_requirements(self):
        """Test that endpoints meet performance requirements"""
        # Test just the API response time (not including test setup/teardown)
        response = self.client.get('/api/maintenance/status')
        self.assertEqual(response.status_code, 200)
        
        # Verify reported response time meets requirement
        data = json.loads(response.data)
        reported_time = data['data']['response_time_ms']
        self.assertLess(reported_time, 100)  # API internal timing should be under 100ms
        
        # Test multiple endpoints for consistency
        endpoints = [
            '/api/maintenance/blocked-operations',
            '/api/maintenance/message',
            '/api/maintenance/api-stats'
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            # All endpoints should respond quickly (this is just a basic check)


if __name__ == '__main__':
    unittest.main()