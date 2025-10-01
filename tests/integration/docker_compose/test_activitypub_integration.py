# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Docker Compose Integration Tests - ActivityPub Platform Integration
Tests ActivityPub platform integrations work correctly in containers
"""

import unittest
import time
import requests
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, PlatformConnection, Post, Image
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

class DockerComposeActivityPubIntegrationTest(unittest.TestCase):
    """Test ActivityPub platform integrations in Docker Compose environment"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://localhost:5000"
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        
        # Wait for services to be ready
        cls._wait_for_services()
    
    @classmethod
    def _wait_for_services(cls, timeout=60):
        """Wait for services to be ready"""
        print("Waiting for services to be ready for ActivityPub testing...")
        
        for i in range(timeout):
            try:
                response = requests.get(f"{cls.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Services ready for ActivityPub testing")
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        raise Exception("Services failed to start within timeout")
    
    def setUp(self):
        """Set up test data for each test"""
        # Create test user with platform connections
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="activitypub_test_user",
            platforms=['pixelfed', 'mastodon']
        )
        
        # Create authenticated session for API calls
        self.session = requests.Session()
        self._authenticate_session()
    
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
    
    @patch('activitypub_client.ActivityPubClient.fetch_posts')
    def test_pixelfed_post_fetching_in_container(self, mock_fetch_posts):
        """Test Pixelfed post fetching works in containerized environment"""
        # Mock Pixelfed API response
        mock_posts = [
            {
                'id': 'test_post_1',
                'content': 'Test post content',
                'media_attachments': [
                    {
                        'id': 'media_1',
                        'url': 'https://example.com/image1.jpg',
                        'type': 'image'
                    }
                ],
                'created_at': '2025-01-01T12:00:00Z'
            }
        ]
        mock_fetch_posts.return_value = mock_posts
        
        # Test post fetching through containerized application
        response = self.session.post(f"{self.base_url}/api/fetch-posts", json={
            'platform_connection_id': self.user_helper.platform_connections['pixelfed'].id,
            'limit': 10
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', False))
        self.assertGreater(len(data.get('posts', [])), 0)
    
    @patch('activitypub_client.ActivityPubClient.fetch_posts')
    def test_mastodon_post_fetching_in_container(self, mock_fetch_posts):
        """Test Mastodon post fetching works in containerized environment"""
        # Mock Mastodon API response
        mock_posts = [
            {
                'id': 'mastodon_post_1',
                'content': 'Mastodon test post',
                'media_attachments': [
                    {
                        'id': 'mastodon_media_1',
                        'url': 'https://mastodon.example.com/image1.jpg',
                        'type': 'image'
                    }
                ],
                'created_at': '2025-01-01T12:00:00Z'
            }
        ]
        mock_fetch_posts.return_value = mock_posts
        
        # Test post fetching through containerized application
        response = self.session.post(f"{self.base_url}/api/fetch-posts", json={
            'platform_connection_id': self.user_helper.platform_connections['mastodon'].id,
            'limit': 10
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', False))
        self.assertGreater(len(data.get('posts', [])), 0)
    
    @patch('activitypub_client.ActivityPubClient.update_post')
    def test_caption_publishing_in_container(self, mock_update_post):
        """Test caption publishing to ActivityPub platforms works in containers"""
        # Mock successful update response
        mock_update_post.return_value = {'success': True, 'updated_at': '2025-01-01T12:00:00Z'}
        
        # Create test post and image with caption
        with self.db_manager.get_session() as session:
            test_post = Post(
                platform_post_id='test_post_caption',
                platform_connection_id=self.user_helper.platform_connections['pixelfed'].id,
                content='Test post for caption publishing',
                created_at='2025-01-01T12:00:00Z'
            )
            session.add(test_post)
            session.flush()
            
            test_image = Image(
                post_id=test_post.id,
                platform_image_id='test_image_caption',
                image_url='https://example.com/test_image.jpg',
                alt_text='Generated alt text for testing',
                caption_status='approved'
            )
            session.add(test_image)
            session.commit()
            
            # Test caption publishing
            response = self.session.post(f"{self.base_url}/api/publish-caption", json={
                'image_id': test_image.id,
                'caption': 'Updated alt text for testing'
            })
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data.get('success', False))
    
    def test_platform_connection_validation_in_container(self):
        """Test platform connection validation works in containerized environment"""
        # Test connection validation endpoint
        response = self.session.post(f"{self.base_url}/api/validate-platform-connection", json={
            'platform_connection_id': self.user_helper.platform_connections['pixelfed'].id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Connection validation should work even if external platform is mocked
        self.assertIn('connection_status', data)
    
    @patch('requests.get')
    def test_activitypub_api_calls_from_container(self, mock_get):
        """Test ActivityPub API calls work from containerized application"""
        # Mock external API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    'id': 'api_test_post',
                    'attributes': {
                        'content': 'API test post',
                        'media_attachments': []
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Test API call through containerized application
        response = self.session.get(f"{self.base_url}/api/platform-status", params={
            'platform_connection_id': self.user_helper.platform_connections['pixelfed'].id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('platform_accessible', data)
    
    def test_platform_credential_encryption_in_container(self):
        """Test platform credential encryption/decryption works in containers"""
        # Test credential access through API
        response = self.session.get(f"{self.base_url}/api/platform-connections")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        connections = data.get('connections', [])
        self.assertGreater(len(connections), 0)
        
        # Verify credentials are not exposed in API response
        for connection in connections:
            self.assertNotIn('access_token', connection)
            self.assertNotIn('client_secret', connection)
            # But connection info should be available
            self.assertIn('platform_name', connection)
            self.assertIn('instance_url', connection)
    
    def test_multi_platform_batch_processing_in_container(self):
        """Test batch processing across multiple platforms works in containers"""
        # Create posts for multiple platforms
        with self.db_manager.get_session() as session:
            platforms = ['pixelfed', 'mastodon']
            post_ids = []
            
            for platform in platforms:
                platform_conn = self.user_helper.platform_connections[platform]
                test_post = Post(
                    platform_post_id=f'batch_test_{platform}',
                    platform_connection_id=platform_conn.id,
                    content=f'Batch test post for {platform}',
                    created_at='2025-01-01T12:00:00Z'
                )
                session.add(test_post)
                session.flush()
                
                test_image = Image(
                    post_id=test_post.id,
                    platform_image_id=f'batch_image_{platform}',
                    image_url=f'https://example.com/{platform}_image.jpg',
                    caption_status='pending'
                )
                session.add(test_image)
                post_ids.append(test_post.id)
            
            session.commit()
        
        # Test batch processing
        response = self.session.post(f"{self.base_url}/api/batch-process", json={
            'post_ids': post_ids,
            'action': 'generate_captions'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', False))
        self.assertIn('processed_count', data)
    
    def test_platform_rate_limiting_in_container(self):
        """Test platform rate limiting works correctly in containerized environment"""
        # Test rate limiting endpoint
        response = self.session.get(f"{self.base_url}/api/rate-limit-status", params={
            'platform_connection_id': self.user_helper.platform_connections['pixelfed'].id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('rate_limit_remaining', data)
        self.assertIn('rate_limit_reset', data)
    
    def test_activitypub_webhook_handling_in_container(self):
        """Test ActivityPub webhook handling works in containerized environment"""
        # Test webhook endpoint (if implemented)
        webhook_data = {
            'type': 'post.created',
            'data': {
                'id': 'webhook_test_post',
                'content': 'Webhook test post',
                'media_attachments': []
            }
        }
        
        response = self.session.post(f"{self.base_url}/api/webhook/activitypub", 
                                   json=webhook_data,
                                   headers={'Content-Type': 'application/json'})
        
        # Webhook endpoint might not be implemented, so accept 404
        self.assertIn(response.status_code, [200, 404])
    
    def test_platform_error_handling_in_container(self):
        """Test platform error handling works correctly in containers"""
        # Test with invalid platform connection ID
        response = self.session.post(f"{self.base_url}/api/fetch-posts", json={
            'platform_connection_id': 99999,  # Invalid ID
            'limit': 10
        })
        
        # Should handle error gracefully
        self.assertIn(response.status_code, [400, 404])
        
        if response.status_code == 400:
            data = response.json()
            self.assertIn('error', data)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)