# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for caption generation blocking during maintenance mode

Tests that caption generation endpoints are properly blocked during maintenance
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
from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService
from models import User, UserRole, PlatformConnection
from config import Config
from app.core.database.core.database_manager import DatabaseManager


class TestCaptionGenerationMaintenanceBlocking(unittest.TestCase):
    """Integration tests for caption generation blocking during maintenance mode"""
    
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
        
        # Add caption generation test routes
        self._add_caption_generation_routes()
        
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
    
    def _add_caption_generation_routes(self):
        """Add caption generation test routes to the Flask app"""
        
        @self.app.route('/start_caption_generation', methods=['POST'])
        def start_caption_generation():
            return json.dumps({
                'success': True,
                'task_id': 'test-task-123',
                'message': 'Caption generation started successfully'
            }), 200, {'Content-Type': 'application/json'}
        
        @self.app.route('/api/caption/generate', methods=['POST'])
        def api_caption_generate():
            return json.dumps({
                'success': True,
                'caption': 'Generated caption text'
            }), 200, {'Content-Type': 'application/json'}
        
        @self.app.route('/caption/status/<task_id>')
        def caption_status(task_id):
            return json.dumps({
                'task_id': task_id,
                'status': 'running',
                'progress': 50
            }), 200, {'Content-Type': 'application/json'}
        
        @self.app.route('/generate_captions', methods=['POST'])
        def generate_captions():
            return json.dumps({
                'success': True,
                'message': 'Batch caption generation started'
            }), 200, {'Content-Type': 'application/json'}
        
        @self.app.route('/ollama/generate', methods=['POST'])
        def ollama_generate():
            return json.dumps({
                'response': 'AI generated caption'
            }), 200, {'Content-Type': 'application/json'}
    
    def test_start_caption_generation_blocked_during_maintenance(self):
        """Test that /start_caption_generation is blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System upgrade in progress",
            duration=30,
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that caption generation is blocked
        response = self.client.post('/start_caption_generation', 
                                  data={'max_posts_per_run': 10})
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['error'], 'Service Unavailable')
        self.assertTrue(data['maintenance_active'])
        self.assertEqual(data['maintenance_mode'], 'normal')
        self.assertIn('System upgrade in progress', data['message'])
        self.assertIn('start_caption_generation', data['operation'])
        
        # Check maintenance headers
        self.assertEqual(response.headers.get('X-Maintenance-Active'), 'true')
        self.assertEqual(response.headers.get('X-Maintenance-Mode'), 'normal')
        self.assertEqual(response.headers.get('Retry-After'), '1800')  # 30 minutes in seconds
    
    def test_api_caption_generate_blocked_during_maintenance(self):
        """Test that /api/caption/generate is blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Database maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that API caption generation is blocked
        response = self.client.post('/api/caption/generate',
                                  json={'image_url': 'http://example.com/image.jpg'})
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['maintenance_active'])
        self.assertIn('Database maintenance', data['message'])
    
    def test_ollama_generate_blocked_during_maintenance(self):
        """Test that /ollama/generate is blocked during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="AI service maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that Ollama generation is blocked
        response = self.client.post('/ollama/generate',
                                  json={'prompt': 'Describe this image'})
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['maintenance_active'])
        self.assertIn('AI service maintenance', data['message'])
    
    def test_caption_generation_allowed_when_maintenance_inactive(self):
        """Test that caption generation works normally when maintenance is inactive"""
        # Ensure maintenance is inactive
        self.maintenance_service.disable_maintenance()
        
        # Test that caption generation works
        response = self.client.post('/start_caption_generation',
                                  data={'max_posts_per_run': 10})
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
        self.assertEqual(data['task_id'], 'test-task-123')
    
    def test_admin_user_bypass_caption_generation_blocking(self):
        """Test that admin users can bypass caption generation blocking"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Routine maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Mock admin user in middleware
        with patch.object(self.middleware, '_get_current_user', return_value=self.admin_user):
            response = self.client.post('/start_caption_generation',
                                      data={'max_posts_per_run': 5})
            
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.get_data(as_text=True))
            self.assertTrue(data['success'])
    
    def test_caption_status_allowed_during_maintenance(self):
        """Test that caption status checking is allowed during maintenance"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test that status checking is allowed (read operation)
        response = self.client.get('/caption/status/test-task-123')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['task_id'], 'test-task-123')
        self.assertEqual(data['status'], 'running')
    
    def test_emergency_mode_blocks_caption_generation(self):
        """Test that emergency mode blocks caption generation"""
        # Enable emergency maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Critical security issue",
            mode=MaintenanceMode.EMERGENCY
        )
        
        # Test that caption generation is blocked in emergency mode
        response = self.client.post('/start_caption_generation',
                                  data={'max_posts_per_run': 10})
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['maintenance_mode'], 'emergency')
        self.assertIn('Emergency maintenance', data['message'])
        self.assertIn('Critical security issue', data['message'])
    
    def test_test_mode_allows_caption_generation(self):
        """Test that test mode allows caption generation (simulation only)"""
        # Enable test maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Testing maintenance procedures",
            mode=MaintenanceMode.TEST
        )
        
        # Test that caption generation is allowed in test mode
        response = self.client.post('/start_caption_generation',
                                  data={'max_posts_per_run': 10})
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data['success'])
    
    def test_maintenance_message_includes_operation_context(self):
        """Test that maintenance messages include operation-specific context"""
        # Enable maintenance mode with specific reason
        self.maintenance_service.enable_maintenance(
            reason="Caption AI model update in progress",
            duration=45,
            mode=MaintenanceMode.NORMAL
        )
        
        # Test caption generation blocking
        response = self.client.post('/start_caption_generation')
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        message = data['message']
        
        # Check that message includes operation context
        self.assertIn('caption generation', message.lower())
        self.assertIn('Caption AI model update in progress', message)
        self.assertIn('start_caption_generation', data['operation'])
        
        # Check estimated completion time
        self.assertIsNotNone(data['estimated_completion'])
    
    def test_multiple_caption_endpoints_blocked_consistently(self):
        """Test that all caption generation endpoints are blocked consistently"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Test multiple caption generation endpoints
        endpoints = [
            ('/start_caption_generation', 'POST'),
            ('/api/caption/generate', 'POST'),
            ('/generate_captions', 'POST'),
            ('/ollama/generate', 'POST')
        ]
        
        for endpoint, method in endpoints:
            with self.subTest(endpoint=endpoint, method=method):
                if method == 'POST':
                    response = self.client.post(endpoint, data={'test': 'data'})
                else:
                    response = self.client.get(endpoint)
                
                self.assertEqual(response.status_code, 503, 
                               f"Endpoint {endpoint} should be blocked")
                
                data = json.loads(response.get_data(as_text=True))
                self.assertTrue(data['maintenance_active'])
                self.assertEqual(data['maintenance_mode'], 'normal')
    
    def test_maintenance_statistics_track_blocked_caption_attempts(self):
        """Test that maintenance statistics track blocked caption generation attempts"""
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Make multiple blocked requests
        for _ in range(3):
            self.client.post('/start_caption_generation', data={'test': 'data'})
        
        # Check middleware statistics
        stats = self.middleware.get_middleware_stats()
        
        self.assertGreater(stats['middleware_stats']['total_requests'], 0)
        self.assertGreater(stats['middleware_stats']['blocked_requests'], 0)
        self.assertGreater(stats['middleware_stats']['maintenance_responses'], 0)
        
        # Check blocked attempts by endpoint
        blocked_attempts = stats['blocked_attempts_by_endpoint']
        self.assertIn('start_caption_generation:POST', blocked_attempts)
        self.assertEqual(blocked_attempts['start_caption_generation:POST'], 3)
    
    def test_graceful_handling_of_existing_caption_jobs(self):
        """Test graceful handling of existing caption generation jobs during maintenance"""
        # This test simulates the scenario where maintenance is enabled
        # while caption generation jobs are running
        
        # Mock an active caption generation service
        mock_caption_service = Mock(spec=WebCaptionGenerationService)
        mock_caption_service.get_all_active_jobs.return_value = [
            {'task_id': 'task-1', 'status': 'running', 'progress': 30},
            {'task_id': 'task-2', 'status': 'running', 'progress': 75}
        ]
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="System maintenance",
            mode=MaintenanceMode.NORMAL
        )
        
        # Update active jobs count in maintenance service
        self.maintenance_service.update_active_jobs_count(2)
        
        # Check that maintenance status includes active jobs count
        status = self.maintenance_service.get_maintenance_status()
        self.assertEqual(status.active_jobs_count, 2)
        
        # Test that new caption generation is still blocked
        response = self.client.post('/start_caption_generation')
        self.assertEqual(response.status_code, 503)
        
        # Test that status checking for existing jobs is allowed
        response = self.client.get('/caption/status/task-1')
        self.assertEqual(response.status_code, 200)
    
    def test_maintenance_mode_ui_message_display(self):
        """Test that maintenance messages are properly formatted for UI display"""
        # Enable maintenance mode with detailed information
        self.maintenance_service.enable_maintenance(
            reason="Upgrading caption generation AI models for improved accuracy",
            duration=60,
            mode=MaintenanceMode.NORMAL
        )
        
        # Test caption generation blocking
        response = self.client.post('/start_caption_generation')
        
        self.assertEqual(response.status_code, 503)
        
        data = json.loads(response.get_data(as_text=True))
        
        # Check that response includes all necessary information for UI display
        self.assertIn('error', data)
        self.assertIn('message', data)
        self.assertIn('maintenance_active', data)
        self.assertIn('maintenance_mode', data)
        self.assertIn('reason', data)
        self.assertIn('estimated_completion', data)
        self.assertIn('operation', data)
        self.assertIn('timestamp', data)
        
        # Check message formatting
        message = data['message']
        self.assertIn('caption generation', message.lower())
        self.assertIn('Upgrading caption generation AI models', message)
        
        # Check that estimated completion is properly formatted
        self.assertIsNotNone(data['estimated_completion'])
        
        # Check that timestamp is in ISO format
        timestamp = data['timestamp']
        self.assertRegex(timestamp, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')


if __name__ == '__main__':
    unittest.main()