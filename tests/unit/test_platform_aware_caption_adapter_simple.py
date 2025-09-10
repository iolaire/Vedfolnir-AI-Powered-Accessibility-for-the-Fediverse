# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Simple unit tests for Platform-Aware Caption Generator Adapter
"""

import unittest
from unittest.mock import Mock, patch

from app.services.platform.adapters.platform_aware_caption_adapter import PlatformAwareCaptionAdapter
from models import PlatformConnection, CaptionGenerationSettings
from app.core.database.core.database_manager import DatabaseManager
from config import Config

class TestPlatformAwareCaptionAdapterSimple(unittest.TestCase):
    """Simple test cases for PlatformAwareCaptionAdapter"""
    
    @patch('platform_aware_caption_adapter.DatabaseManager')
    def setUp(self, mock_db_manager_class):
        """Set up test fixtures"""
        # Mock platform connection
        self.mock_platform_connection = Mock(spec=PlatformConnection)
        self.mock_platform_connection.id = 1
        self.mock_platform_connection.name = "Test Platform"
        self.mock_platform_connection.platform_type = "pixelfed"
        self.mock_platform_connection.instance_url = "https://test.example.com"
        self.mock_platform_connection.username = "testuser"
        self.mock_platform_connection.is_active = True
        
        # Mock config
        self.mock_config = Mock(spec=Config)
        
        # Mock DatabaseManager instance
        self.mock_db_manager = Mock(spec=DatabaseManager)
        mock_db_manager_class.return_value = self.mock_db_manager
        
        # Create adapter
        self.adapter = PlatformAwareCaptionAdapter(
            self.mock_platform_connection,
            self.mock_config
        )
    
    def test_get_platform_info(self):
        """Test getting platform information"""
        result = self.adapter.get_platform_info()
        
        expected = {
            'name': 'Test Platform',
            'platform_type': 'pixelfed',
            'instance_url': 'https://test.example.com',
            'username': 'testuser',
            'is_active': True
        }
        
        self.assertEqual(result, expected)
    
    def test_initialization(self):
        """Test adapter initialization"""
        self.assertIsNotNone(self.adapter.platform_connection)
        self.assertIsNotNone(self.adapter.config)
        self.assertIsNotNone(self.adapter.db_manager)
        self.assertEqual(self.adapter.platform_connection.name, "Test Platform")
    
    def test_stats_initialization(self):
        """Test that stats are properly initialized"""
        expected_stats = {
            'posts_processed': 0,
            'images_processed': 0,
            'captions_generated': 0,
            'errors': 0,
            'skipped_existing': 0
        }
        
        self.assertEqual(self.adapter.stats, expected_stats)

if __name__ == '__main__':
    unittest.main()