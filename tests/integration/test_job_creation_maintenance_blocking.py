# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for job creation and management blocking during maintenance mode

Tests that job-related endpoints are properly blocked during maintenance
and that existing jobs can complete gracefully.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json
import time
import asyncio
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask
from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode
from app.services.maintenance.components.maintenance_mode_middleware import MaintenanceModeMiddleware
from app.services.task.core.task_queue_manager import TaskQueueManager
from models import User, UserRole
from config import Config
from app.core.database.core.database_manager import DatabaseManager


class TestJobCreationMaintenanceBlocking(unittest.TestCase):
    """Integration tests for job creation and management blocking during maintenance mode"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create Flask app for testing
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock configuration service
        self.mock_config_service = Mock()
        
        # Create maintenance service
        self.maintenance_service = EnhancedMaintenanceModeService(self.mock_config_service)
        
        # Create middleware and integrate with app
        self.middleware = MaintenanceModeMiddleware(self.app, self.maintenance_service)
        
        # Add job management test routes
        self._add_job_management_routes()
        
        # Create test client
        self.client = self.app.test_client()
        
        # Mock users
        self.admin_user = Mock(spec=User)
        self.admin_user.role = UserRole.ADMIN
        self.admin_user.id = 1
        self.admin_user.username = "admin"
        
        self.regular_user = Mock(spec=User)
        self.regular_user.role = UserRole.REVIEWER
        self.regular_user.id = 2
        self.regular_user.username = "reviewer"
    
    def _add_job_management_routes(self):
        """Add job management test routes to the Flask app"""
        
        @self.app.route('/api/caption_generation/cancel/<task_id>', methods=['POST'])
        def cancel_caption_generation(task_id):
            return json.dumps({
                'success': True,
                'task_id': task_id,
                'message': 'Task cancelled successfully'
            }), 200, {'Content-Type': 'application/json'}
        
        @self.app.route('/api/caption_generation/retry/<task_id>', methods=['POST'])
        def retry_caption_generation(task_id):
            return json.dumps({
                'success': True,
                'task_id': task_id,
                'message': 'Task retry initiated'
            }), 200, {'Content-Type': 'application/json'}
        
        @self.app.route('/api/review/queue_regeneration', methods=['POST'])
        def queue_regeneration():
            return json.dumps({
                'success': True,
                'message': 'Queue regeneration started'
            }), 200, {'Content-Type': 'application/json'}
        
        @self.app.route('/api/caption_generation/status/<task_id>')
        def caption_generation_status(task_id):
            return json.dumps({
                'task_id': task_id,
                'status': 'running',
                'progress': 50
            }), 200, {'Content-Type': 'application/json'}
        
        @self.app.route('/api/caption_generation/results/<task_id>')
        def caption_generation_results(task_id):
            return json.dumps({
                'task_id': task_id,
                'results': ['caption1', 'caption2']
            }), 200, {'Content-Type': 'application/json'}
        
        @self.app.route('/api/jobs', methods=['POST'])
        def create_job():
            return json.dumps({
                'success': True,
                'job_id': 'job-123',
                'message': 'Job created successfully'
            }), 200, {'Content-Type': 'application/json'}
        
        @self.app.route('/background/task/create', methods=['POST'])
        def create_background_task():
            return json.dumps({
                'success': True,
                'task_id': 'bg-task-456',
                'message': 'Background task created'
            }), 200, {'Content-Type': 'application/json'}
    
    def test_job_cancel_blocked_during_maintenance(self):
        """Test that job cancellation is blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance in progress",
            duration=30,
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that job cancellation is blocked
        response = self.client.post('/api/caption_generation/cancel/test-task-123')
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['error'], 'Service Unavailable')
        self.assertTrue(data['maintenance_active'])
        self.assertEqual(data['maintenance_mode'], 'normal')
        self.assertIn('System maintenance in progress', data['message'])
        self.assertIn('/api/caption_generation/cancel/', data['operation'])
        
        # Check maintenance headers
        self.assertEqual(response.headers.get('X-Maintenance-Active'), 'true')
        self.assertEqual(response.headers.get('X-Maintenance-Mode'), 'normal')
    
    def test_job_retry_blocked_during_maintenance(self):
        """Test that job retry is blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Database maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that job retry is blocked
        response = self.client.post('/api/caption_generation/retry/test-task-456')
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['maintenance_active'])
        self.assertIn('Database maintenance', data['message'])
        self.assertIn('job creation', data['message'])  # Should include operation description
    
    def test_queue_regeneration_blocked_during_maintenance(self):
        """Test that queue regeneration is blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Queue maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that queue regeneration is blocked
        response = self.client.post('/api/review/queue_regeneration')
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['maintenance_active'])
        self.assertIn('Queue maintenance', data['message'])
    
    def test_job_creation_api_blocked_during_maintenance(self):
        """Test that generic job creation API is blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System upgrade",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that job creation API is blocked
        response = self.client.post('/api/jobs', json={'type': 'caption_generation'})
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['maintenance_active'])
        self.assertIn('System upgrade', data['message'])
    
    def test_background_task_creation_blocked_during_maintenance(self):
        """Test that background task creation is blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Background service maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that background task creation is blocked
        response = self.client.post('/background/task/create', json={'task_type': 'cleanup'})
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['maintenance_active'])
        self.assertIn('Background service maintenance', data['message'])
    
    def test_job_status_allowed_during_maintenance(self):
        """Test that job status checking is allowed during maintenance (read operation)"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that status checking is allowed (read operation)
        response = self.client.get('/api/caption_generation/status/test-task-123')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['task_id'], 'test-task-123')
        self.assertEqual(data['status'], 'running')
    
    def test_job_results_allowed_during_maintenance(self):
        """Test that job results retrieval is allowed during maintenance (read operation)"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that results retrieval is allowed (read operation)
        response = self.client.get('/api/caption_generation/results/test-task-123')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['task_id'], 'test-task-123')
        self.assertIn('results', data)
    
    def test_job_operations_allowed_when_maintenance_inactive(self):
        """Test that job operations work normally when maintenance is inactive"""
        # Ensure maintenance is inactive
        self.maintenance_service.disable_maintenance()
        
        # Test that job operations work
        response = self.client.post('/api/caption_generation/cancel/test-task-123')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
        self.assertEqual(data['task_id'], 'test-task-123')
    
    def test_admin_user_bypass_job_blocking(self):
        """Test that admin users can bypass job operation blocking"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Routine maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Mock admin user in middleware
        with patch.object(self.middleware, '_get_current_user', return_value=self.admin_user):
            response = self.client.post('/api/caption_generation/cancel/admin-task-123')
            
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.get_data(as_text=True))
            self.assertTrue(data['success'])
    
    def test_emergency_mode_blocks_job_operations(self):
        """Test that emergency mode blocks job operations"""
        # Enable emergency maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Critical system issue",
            mode=MaintenanceMode.EMERGENCY
        )
        
        # Test that job operations are blocked in emergency mode
        response = self.client.post('/api/caption_generation/retry/emergency-task-123')
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['maintenance_mode'], 'emergency')
        self.assertIn('Emergency maintenance', data['message'])
        self.assertIn('Critical system issue', data['message'])
    
    def test_test_mode_allows_job_operations(self):
        """Test that test mode allows job operations (simulation only)"""
        # Enable test maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Testing maintenance procedures",
            mode=MaintenanceMode.TEST
        )
        
        # Test that job operations are allowed in test mode
        response = self.client.post('/api/caption_generation/cancel/test-mode-task-123')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
    
    def test_multiple_job_endpoints_blocked_consistently(self):
        """Test that all job-related endpoints are blocked consistently"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test multiple job-related endpoints
        endpoints = [
            ('/api/caption_generation/cancel/test-123', 'POST'),
            ('/api/caption_generation/retry/test-456', 'POST'),
            ('/api/review/queue_regeneration', 'POST'),
            ('/api/jobs', 'POST'),
            ('/background/task/create', 'POST')
        ]
        
        for endpoint, method in endpoints:
            with self.subTest(endpoint=endpoint, method=method):
                if method == 'POST':
                    response = self.client.post(endpoint, json={'test': 'data'})
                else:
                    response = self.client.get(endpoint)
                
                self.assertEqual(response.status_code, 503, 
                               f"Endpoint {endpoint} should be blocked")
                
                data = json.loads(response.get_data(as_text=True))
                self.assertTrue(data['maintenance_active'])
                self.assertEqual(data['maintenance_mode'], 'normal')
    
    def test_job_operation_completion_tracking(self):
        """Test that job operation completion is tracked during maintenance"""
        # Mock a task queue manager with active jobs
        mock_task_queue = Mock()  # Remove spec constraint to allow any attributes
        mock_task_queue.get_queue_stats.return_value = {
            'total_tasks': 10,
            'queued_tasks': 2,
            'running_tasks': 3,
            'completed_tasks': 5
        }
        mock_task_queue.get_all_tasks.return_value = [
            Mock(task_id='job-1', status='running'),
            Mock(task_id='job-2', status='running'),
            Mock(task_id='job-3', status='running')
        ]
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Update active jobs count in maintenance service
        self.maintenance_service.update_active_jobs_count(3)
        
        # Check that maintenance status includes active jobs count
        status = self.maintenance_service.get_maintenance_status()
        self.assertEqual(status.active_jobs_count, 3)
        
        # Test that new job creation is still blocked
        response = self.client.post('/api/jobs', json={'type': 'new_job'})
        self.assertEqual(response.status_code, 503)
        
        # Test that job status checking for existing jobs is allowed
        response = self.client.get('/api/caption_generation/status/job-1')
        self.assertEqual(response.status_code, 200)
    
    def test_maintenance_statistics_track_blocked_job_attempts(self):
        """Test that maintenance statistics track blocked job operation attempts"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Make multiple blocked requests
        blocked_endpoints = [
            '/api/caption_generation/cancel/test-1',
            '/api/caption_generation/retry/test-2',
            '/api/review/queue_regeneration'
        ]
        
        for endpoint in blocked_endpoints:
            self.client.post(endpoint, json={'test': 'data'})
        
        # Check middleware statistics
        stats = self.middleware.get_middleware_stats()
        
        self.assertGreater(stats['middleware_stats']['total_requests'], 0)
        self.assertGreater(stats['middleware_stats']['blocked_requests'], 0)
        self.assertGreater(stats['middleware_stats']['maintenance_responses'], 0)
        
        # Check blocked attempts by endpoint
        blocked_attempts = stats['blocked_attempts_by_endpoint']
        self.assertGreater(len(blocked_attempts), 0)
    
    def test_job_blocking_with_operation_context(self):
        """Test that job blocking includes proper operation context in messages"""
        # Enable maintenance mode with specific reason
        self.maintenance_service.enable_maintenance(
            reason="Job queue maintenance and optimization",
            duration=60,
            mode=MaintenanceMode.NORMAL
        )
        
        # Test job operation blocking
        response = self.client.post('/api/caption_generation/cancel/context-test-123')
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        message = data['message']
        
        # Check that message includes operation context
        self.assertIn('job creation', message.lower())
        self.assertIn('Job queue maintenance and optimization', message)
        self.assertIn('/api/caption_generation/cancel/', data['operation'])
        
        # Check estimated completion time
        self.assertIsNotNone(data['estimated_completion'])
    
    def test_task_queue_rejection_during_maintenance(self):
        """Test that task queue rejects new job submissions during maintenance"""
        # This test simulates the task queue manager rejecting new submissions
        # during maintenance mode
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Task queue maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that job creation endpoints are blocked
        response = self.client.post('/api/jobs', json={
            'type': 'caption_generation',
            'priority': 'high'
        })
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['maintenance_active'])
        self.assertIn('Task queue maintenance', data['message'])
        
        # Verify that the maintenance service tracks this as a blocked operation
        stats = self.maintenance_service.get_service_stats()
        self.assertGreater(stats['statistics']['blocked_operations'], 0)


if __name__ == '__main__':
    unittest.main()