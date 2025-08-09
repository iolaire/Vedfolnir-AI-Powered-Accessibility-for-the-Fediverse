# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
End-to-end tests for web interface functionality
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import json
import uuid
from datetime import datetime, timezone

from web_app import app
from models import (
    User, UserRole, PlatformConnection, CaptionGenerationTask, 
    TaskStatus, CaptionGenerationSettings
)

class TestWebInterfaceEndToEnd(unittest.TestCase):
    """End-to-end tests for web interface functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        # Test data
        self.test_user_id = 1
        self.test_platform_id = 1
        self.test_task_id = str(uuid.uuid4())
        
        # Mock user session
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user_id
            sess['current_platform_id'] = self.test_platform_id
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_caption_generation_page_load(self, mock_service, mock_session_manager):
        """Test caption generation page loads correctly"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser',
            'role': UserRole.USER.value
        }
        
        mock_session_manager.get_current_platform.return_value = {
            'id': self.test_platform_id,
            'name': 'Test Platform',
            'platform_type': 'mastodon'
        }
        
        # Mock user settings
        mock_service.get_user_settings.return_value = CaptionGenerationSettings()
        
        response = self.client.get('/caption-generation')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Caption Generation', response.data)
        self.assertIn(b'Start Generation', response.data)
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_start_caption_generation_success(self, mock_service, mock_session_manager):
        """Test successful caption generation start via web interface"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser'
        }
        
        mock_session_manager.get_current_platform.return_value = {
            'id': self.test_platform_id,
            'name': 'Test Platform'
        }
        
        # Mock service response
        mock_service.start_caption_generation = AsyncMock(return_value=self.test_task_id)
        
        response = self.client.post('/api/caption-generation/start', 
                                  data={'max_posts_per_run': '25'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['task_id'], self.test_task_id)
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_start_caption_generation_validation_error(self, mock_service, mock_session_manager):
        """Test caption generation start with validation error"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser'
        }
        
        mock_session_manager.get_current_platform.return_value = {
            'id': self.test_platform_id,
            'name': 'Test Platform'
        }
        
        # Mock service error
        mock_service.start_caption_generation = AsyncMock(
            side_effect=ValueError("User has active task")
        )
        
        response = self.client.post('/api/caption-generation/start', 
                                  data={'max_posts_per_run': '25'})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('User has active task', data['error'])
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_get_generation_status(self, mock_service, mock_session_manager):
        """Test getting generation status via API"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser'
        }
        
        # Mock service response
        mock_status = {
            'task_id': self.test_task_id,
            'status': TaskStatus.RUNNING.value,
            'progress_percent': 50,
            'current_step': 'Processing images',
            'progress_details': {'images_processed': 10, 'total_images': 20}
        }
        mock_service.get_generation_status.return_value = mock_status
        
        response = self.client.get(f'/api/caption-generation/status/{self.test_task_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['status']['task_id'], self.test_task_id)
        self.assertEqual(data['status']['progress_percent'], 50)
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_cancel_generation(self, mock_service, mock_session_manager):
        """Test cancelling generation via API"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser'
        }
        
        # Mock service response
        mock_service.cancel_generation.return_value = True
        
        response = self.client.post(f'/api/caption-generation/cancel/{self.test_task_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertTrue(data['cancelled'])
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_get_generation_results(self, mock_service, mock_session_manager):
        """Test getting generation results via API"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser'
        }
        
        # Mock service response
        from models import GenerationResults
        mock_results = GenerationResults(
            total_posts_processed=10,
            captions_generated=8,
            captions_updated=6,
            errors=[]
        )
        mock_service.get_generation_results = AsyncMock(return_value=mock_results)
        
        response = self.client.get(f'/api/caption-generation/results/{self.test_task_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['results']['total_posts_processed'], 10)
        self.assertEqual(data['results']['captions_generated'], 8)
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_save_user_settings(self, mock_service, mock_session_manager):
        """Test saving user settings via API"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser'
        }
        
        mock_session_manager.get_current_platform.return_value = {
            'id': self.test_platform_id,
            'name': 'Test Platform'
        }
        
        # Mock service response
        mock_service.save_user_settings = AsyncMock(return_value=True)
        
        settings_data = {
            'max_posts_per_run': 30,
            'caption_max_length': 400,
            'include_hashtags': True
        }
        
        response = self.client.post('/api/caption-generation/settings', 
                                  data=json.dumps(settings_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
    
    @patch('web_app.session_manager')
    def test_unauthorized_access(self, mock_session_manager):
        """Test unauthorized access to caption generation endpoints"""
        # Mock no user session
        mock_session_manager.get_current_user.return_value = None
        
        # Test various endpoints
        endpoints = [
            '/caption-generation',
            '/api/caption-generation/start',
            f'/api/caption-generation/status/{self.test_task_id}',
            f'/api/caption-generation/cancel/{self.test_task_id}',
            f'/api/caption-generation/results/{self.test_task_id}',
            '/api/caption-generation/settings'
        ]
        
        for endpoint in endpoints:
            if endpoint.startswith('/api/'):
                response = self.client.post(endpoint) if 'start' in endpoint or 'cancel' in endpoint or 'settings' in endpoint else self.client.get(endpoint)
                self.assertIn(response.status_code, [401, 403], f"Endpoint {endpoint} should require authentication")
            else:
                response = self.client.get(endpoint)
                self.assertIn(response.status_code, [302, 401, 403], f"Endpoint {endpoint} should redirect or deny access")
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_websocket_connection(self, mock_service, mock_session_manager):
        """Test WebSocket connection for progress updates"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser'
        }
        
        # Note: This is a simplified test as full WebSocket testing requires more setup
        # In a real scenario, you'd use a WebSocket testing library
        
        with patch('web_app.socketio') as mock_socketio:
            # Mock WebSocket client connection
            mock_socketio.test_client.return_value = Mock()
            
            # Test that WebSocket routes are accessible
            response = self.client.get('/caption-generation')
            self.assertEqual(response.status_code, 200)
            
            # Verify WebSocket JavaScript is included
            self.assertIn(b'socket.io', response.data)
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_settings_page_functionality(self, mock_service, mock_session_manager):
        """Test caption settings page functionality"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser'
        }
        
        mock_session_manager.get_current_platform.return_value = {
            'id': self.test_platform_id,
            'name': 'Test Platform'
        }
        
        # Mock current settings
        mock_service.get_user_settings.return_value = CaptionGenerationSettings(
            max_posts_per_run=25,
            caption_max_length=400
        )
        
        response = self.client.get('/caption-settings')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Caption Settings', response.data)
        self.assertIn(b'max_posts_per_run', response.data)
        self.assertIn(b'caption_max_length', response.data)
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_task_history_display(self, mock_service, mock_session_manager):
        """Test task history display functionality"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser'
        }
        
        # Mock task history
        mock_history = [
            {
                'task_id': str(uuid.uuid4()),
                'status': TaskStatus.COMPLETED.value,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'progress_percent': 100
            },
            {
                'task_id': str(uuid.uuid4()),
                'status': TaskStatus.FAILED.value,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'error_message': 'Test error',
                'progress_percent': 30
            }
        ]
        mock_service.get_user_task_history = AsyncMock(return_value=mock_history)
        
        response = self.client.get('/api/caption-generation/history')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['history']), 2)
        self.assertEqual(data['history'][0]['status'], TaskStatus.COMPLETED.value)
        self.assertEqual(data['history'][1]['status'], TaskStatus.FAILED.value)
    
    @patch('web_app.session_manager')
    @patch('web_app.web_caption_service')
    def test_error_handling_in_web_interface(self, mock_service, mock_session_manager):
        """Test error handling in web interface"""
        # Mock session data
        mock_session_manager.get_current_user.return_value = {
            'id': self.test_user_id,
            'username': 'testuser'
        }
        
        # Test various error scenarios
        
        # 1. Service unavailable
        mock_service.start_caption_generation = AsyncMock(
            side_effect=Exception("Service unavailable")
        )
        
        response = self.client.post('/api/caption-generation/start', 
                                  data={'max_posts_per_run': '25'})
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        
        # 2. Invalid task ID format
        response = self.client.get('/api/caption-generation/status/invalid-id')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        
        # 3. Task not found
        mock_service.get_generation_status.return_value = None
        
        response = self.client.get(f'/api/caption-generation/status/{str(uuid.uuid4())}')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['success'])

if __name__ == '__main__':
    unittest.main()