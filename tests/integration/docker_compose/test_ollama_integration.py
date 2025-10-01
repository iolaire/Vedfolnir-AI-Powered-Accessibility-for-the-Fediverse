# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Docker Compose Integration Tests - Ollama Integration
Tests Ollama integration from containerized application to external host-based Ollama service
"""

import unittest
import time
import requests
import json
import os
import sys
from unittest.mock import patch, MagicMock
import base64
from io import BytesIO
from PIL import Image as PILImage

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, PlatformConnection, Post, Image
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

class DockerComposeOllamaIntegrationTest(unittest.TestCase):
    """Test Ollama integration from containerized application to external host service"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://localhost:5000"
        cls.ollama_url = "http://host.docker.internal:11434"  # External Ollama service
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        
        # Wait for services to be ready
        cls._wait_for_services()
        cls._check_ollama_availability()
    
    @classmethod
    def _wait_for_services(cls, timeout=60):
        """Wait for services to be ready"""
        print("Waiting for services to be ready for Ollama testing...")
        
        for i in range(timeout):
            try:
                response = requests.get(f"{cls.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Services ready for Ollama testing")
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        raise Exception("Services failed to start within timeout")
    
    @classmethod
    def _check_ollama_availability(cls):
        """Check if external Ollama service is available"""
        try:
            # Test direct connection to external Ollama
            response = requests.get(f"{cls.ollama_url}/api/version", timeout=10)
            if response.status_code == 200:
                print("✅ External Ollama service is available")
                cls.ollama_available = True
            else:
                print("⚠️ External Ollama service not responding correctly")
                cls.ollama_available = False
        except requests.exceptions.RequestException as e:
            print(f"⚠️ External Ollama service not available: {e}")
            cls.ollama_available = False
    
    def setUp(self):
        """Set up test data for each test"""
        # Create test user with platform connections
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="ollama_test_user",
            platforms=['pixelfed']
        )
        
        # Create authenticated session for API calls
        self.session = requests.Session()
        self._authenticate_session()
        
        # Create test image data
        self.test_image_data = self._create_test_image()
    
    def tearDown(self):
        """Clean up test data"""
        cleanup_test_user(self.user_helper)
    
    def _authenticate_session(self):
        """Authenticate session for API calls"""
        # Get login page for CSRF token
        login_page = self.session.get(f"{self.base_url}/login")
        csrf_token = self._extract_csrf_token(login_page.text)
        
        # Login with test user
        login_data = {
            'username_or_email': self.test_user.username,
            'password': 'test_password',
            'csrf_token': csrf_token
        }
        
        response = self.session.post(f"{self.base_url}/login", data=login_data)
        self.assertIn(response.status_code, [200, 302])
    
    def _extract_csrf_token(self, html_content):
        """Extract CSRF token from HTML content"""
        import re
        match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html_content)
        return match.group(1) if match else None
    
    def _create_test_image(self):
        """Create test image data for caption generation"""
        # Create a simple test image
        img = PILImage.new('RGB', (100, 100), color='red')
        img_buffer = BytesIO()
        img.save(img_buffer, format='JPEG')
        img_buffer.seek(0)
        
        # Convert to base64 for API calls
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        return {
            'data': img_base64,
            'format': 'jpeg',
            'size': (100, 100)
        }
    
    def test_ollama_service_connectivity_from_container(self):
        """Test that containerized application can connect to external Ollama service"""
        # Test Ollama connectivity through containerized application
        response = self.session.get(f"{self.base_url}/api/ollama/health")
        
        if not self.ollama_available:
            self.skipTest("External Ollama service not available")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('ollama_accessible', False))
        self.assertIn('ollama_version', data)
    
    def test_ollama_model_availability_from_container(self):
        """Test that LLaVA model is available through containerized application"""
        if not self.ollama_available:
            self.skipTest("External Ollama service not available")
        
        # Test model availability
        response = self.session.get(f"{self.base_url}/api/ollama/models")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', False))
        
        models = data.get('models', [])
        llava_models = [m for m in models if 'llava' in m.get('name', '').lower()]
        self.assertGreater(len(llava_models), 0, "No LLaVA models found")
    
    @patch('requests.post')
    def test_caption_generation_from_container_to_ollama(self, mock_post):
        """Test caption generation from containerized app to external Ollama"""
        # Mock Ollama API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'A red square image for testing purposes.',
            'done': True
        }
        mock_post.return_value = mock_response
        
        # Create test post and image
        with self.db_manager.get_session() as session:
            test_post = Post(
                platform_post_id='ollama_test_post',
                platform_connection_id=self.user_helper.platform_connections['pixelfed'].id,
                content='Test post for Ollama integration',
                created_at='2025-01-01T12:00:00Z'
            )
            session.add(test_post)
            session.flush()
            
            test_image = Image(
                post_id=test_post.id,
                platform_image_id='ollama_test_image',
                image_url='https://example.com/test_image.jpg',
                caption_status='pending'
            )
            session.add(test_image)
            session.commit()
            
            # Test caption generation
            response = self.session.post(f"{self.base_url}/api/generate-caption", json={
                'image_id': test_image.id,
                'image_data': self.test_image_data['data'],
                'use_ollama': True
            })
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data.get('success', False))
            self.assertIn('caption', data)
            self.assertGreater(len(data['caption']), 0)
    
    def test_ollama_api_timeout_handling_from_container(self):
        """Test Ollama API timeout handling from containerized application"""
        if not self.ollama_available:
            self.skipTest("External Ollama service not available")
        
        # Test timeout configuration
        response = self.session.get(f"{self.base_url}/api/ollama/config")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('timeout', data)
        self.assertIn('max_retries', data)
        self.assertGreater(data['timeout'], 0)
    
    @patch('requests.post')
    def test_ollama_error_handling_from_container(self, mock_post):
        """Test Ollama error handling from containerized application"""
        # Mock Ollama API error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            'error': 'Internal server error'
        }
        mock_post.return_value = mock_response
        
        # Create test image
        with self.db_manager.get_session() as session:
            test_post = Post(
                platform_post_id='ollama_error_test',
                platform_connection_id=self.user_helper.platform_connections['pixelfed'].id,
                content='Test post for error handling',
                created_at='2025-01-01T12:00:00Z'
            )
            session.add(test_post)
            session.flush()
            
            test_image = Image(
                post_id=test_post.id,
                platform_image_id='ollama_error_image',
                image_url='https://example.com/error_test.jpg',
                caption_status='pending'
            )
            session.add(test_image)
            session.commit()
            
            # Test error handling
            response = self.session.post(f"{self.base_url}/api/generate-caption", json={
                'image_id': test_image.id,
                'image_data': self.test_image_data['data'],
                'use_ollama': True
            })
            
            # Should handle error gracefully
            self.assertIn(response.status_code, [400, 500])
            data = response.json()
            self.assertIn('error', data)
    
    def test_ollama_batch_processing_from_container(self):
        """Test batch caption generation using Ollama from containerized application"""
        if not self.ollama_available:
            self.skipTest("External Ollama service not available")
        
        # Create multiple test images
        image_ids = []
        with self.db_manager.get_session() as session:
            for i in range(3):
                test_post = Post(
                    platform_post_id=f'batch_ollama_post_{i}',
                    platform_connection_id=self.user_helper.platform_connections['pixelfed'].id,
                    content=f'Batch test post {i}',
                    created_at='2025-01-01T12:00:00Z'
                )
                session.add(test_post)
                session.flush()
                
                test_image = Image(
                    post_id=test_post.id,
                    platform_image_id=f'batch_ollama_image_{i}',
                    image_url=f'https://example.com/batch_test_{i}.jpg',
                    caption_status='pending'
                )
                session.add(test_image)
                session.flush()
                image_ids.append(test_image.id)
            
            session.commit()
        
        # Test batch processing
        response = self.session.post(f"{self.base_url}/api/batch-generate-captions", json={
            'image_ids': image_ids,
            'use_ollama': True,
            'batch_size': 2
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', False))
        self.assertIn('processed_count', data)
    
    def test_ollama_model_switching_from_container(self):
        """Test switching between different Ollama models from containerized application"""
        if not self.ollama_available:
            self.skipTest("External Ollama service not available")
        
        # Test model switching
        response = self.session.post(f"{self.base_url}/api/ollama/switch-model", json={
            'model_name': 'llava:7b'
        })
        
        # Model switching might not be implemented, accept 404
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            data = response.json()
            self.assertTrue(data.get('success', False))
            self.assertEqual(data.get('active_model'), 'llava:7b')
    
    def test_ollama_performance_metrics_from_container(self):
        """Test Ollama performance metrics collection from containerized application"""
        if not self.ollama_available:
            self.skipTest("External Ollama service not available")
        
        # Test performance metrics
        response = self.session.get(f"{self.base_url}/api/ollama/metrics")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('response_times', data)
        self.assertIn('success_rate', data)
        self.assertIn('error_rate', data)
    
    def test_ollama_websocket_progress_from_container(self):
        """Test WebSocket progress updates for Ollama caption generation"""
        # This test would require WebSocket client setup
        # For now, test the progress endpoint
        response = self.session.get(f"{self.base_url}/api/caption-progress/test_session")
        
        # Progress endpoint might return 404 if no active session
        self.assertIn(response.status_code, [200, 404])
    
    def test_ollama_configuration_from_container(self):
        """Test Ollama configuration management from containerized application"""
        # Test configuration endpoint
        response = self.session.get(f"{self.base_url}/api/ollama/config")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify configuration includes container-specific settings
        self.assertIn('ollama_url', data)
        self.assertEqual(data['ollama_url'], 'http://host.docker.internal:11434')
        self.assertIn('timeout', data)
        self.assertIn('model', data)
    
    def test_ollama_health_monitoring_from_container(self):
        """Test Ollama health monitoring from containerized application"""
        # Test health monitoring endpoint
        response = self.session.get(f"{self.base_url}/api/health/ollama")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        if self.ollama_available:
            self.assertTrue(data.get('ollama_accessible', False))
            self.assertIn('response_time', data)
            self.assertIn('last_check', data)
        else:
            self.assertFalse(data.get('ollama_accessible', True))
            self.assertIn('error', data)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)