# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import asyncio
import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import sys

# Add the current directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import Vedfolnir
from config import Config
from models import ProcessingRun, Image

class TestMultiUserProcessing(unittest.TestCase):
    """Test cases for multi-user processing feature"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a mock config with the necessary structure
        self.config = MagicMock()
        self.config.max_users_per_run = 3
        self.config.user_processing_delay = 0  # No delay for tests
        self.config.max_posts_per_run = 5
        
        # Mock the storage attribute
        self.config.storage = MagicMock()
        self.config.storage.database_url = "mysql+pymysql://DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db"
        
        # Create a mock database manager
        self.db_mock = MagicMock()
        self.session_mock = MagicMock()
        self.db_mock.get_session.return_value = self.session_mock
        
        # Create the bot with mocked dependencies
        with patch('main.DatabaseManager', return_value=self.db_mock):
            self.bot = Vedfolnir(self.config)
    
    def test_create_processing_run_with_batch_id(self):
        """Test creating a processing run with a batch ID"""
        # Set up mock
        with patch('main.ProcessingRun') as mock_processing_run:
            mock_run = MagicMock()
            mock_processing_run.return_value = mock_run
            
            # Call the method with a batch ID
            user_id = "test_user"
            batch_id = "test_batch"
            self.bot._create_processing_run(user_id, batch_id)
            
            # Check that ProcessingRun was created with the correct parameters
            mock_processing_run.assert_called_once_with(user_id=user_id, batch_id=batch_id)
            
            # Check that the run was added to the session and committed
            self.session_mock.add.assert_called_once_with(mock_run)
            self.session_mock.commit.assert_called_once()

# Define async test runner
def async_test(coro):
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper

class TestMultiUserProcessingAsync(unittest.TestCase):
    """Async test cases for multi-user processing feature"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a mock config with the necessary structure
        self.config = MagicMock()
        self.config.max_users_per_run = 3
        self.config.user_processing_delay = 0  # No delay for tests
        self.config.max_posts_per_run = 5
        
        # Mock the storage attribute
        self.config.storage = MagicMock()
        self.config.storage.database_url = "mysql+pymysql://DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db"
        
        # Create a mock database manager
        self.db_mock = MagicMock()
        self.session_mock = MagicMock()
        self.db_mock.get_session.return_value = self.session_mock
        
        # Create the bot with mocked dependencies
        with patch('main.DatabaseManager', return_value=self.db_mock):
            self.bot = Vedfolnir(self.config)
    
    @async_test
    async def test_run_multi_user(self):
        """Test running the bot with multiple users"""
        # Set up mocks
        with patch('main.ActivityPubClient') as mock_ap_client, \
             patch('main.ImageProcessor') as mock_image_processor, \
             patch('main.OllamaCaptionGenerator') as mock_caption_generator:
            
            ap_client_instance = AsyncMock()
            mock_ap_client.return_value.__aenter__.return_value = ap_client_instance
            
            image_processor_instance = AsyncMock()
            mock_image_processor.return_value.__aenter__.return_value = image_processor_instance
            
            caption_generator_instance = MagicMock()
            mock_caption_generator.return_value = caption_generator_instance
            
            # Mock the _process_user method to avoid having to mock all its dependencies
            self.bot._process_user = AsyncMock()
            
            # Run the bot with multiple users
            user_ids = ["user1", "user2", "user3"]
            await self.bot.run_multi_user(user_ids)
            
            # Check that _process_user was called for each user
            self.assertEqual(self.bot._process_user.call_count, 3)
            
            # Check the calls were made with the correct arguments
            for i, user_id in enumerate(user_ids):
                call_args = self.bot._process_user.call_args_list[i][0]
                self.assertEqual(call_args[0], user_id)
                self.assertEqual(call_args[1], ap_client_instance)
                self.assertEqual(call_args[2], image_processor_instance)
                self.assertEqual(call_args[3], caption_generator_instance)
                # Check that batch_id was passed and is not None
                self.assertIsNotNone(call_args[4])
    
    @async_test
    async def test_max_users_limit(self):
        """Test that the max users per run limit is enforced"""
        # Set up mocks
        with patch('main.ActivityPubClient') as mock_ap_client, \
             patch('main.ImageProcessor') as mock_image_processor, \
             patch('main.OllamaCaptionGenerator') as mock_caption_generator:
            
            ap_client_instance = AsyncMock()
            mock_ap_client.return_value.__aenter__.return_value = ap_client_instance
            
            image_processor_instance = AsyncMock()
            mock_image_processor.return_value.__aenter__.return_value = image_processor_instance
            
            caption_generator_instance = MagicMock()
            mock_caption_generator.return_value = caption_generator_instance
            
            # Mock the _process_user method
            self.bot._process_user = AsyncMock()
            
            # Run the bot with more users than the limit
            user_ids = ["user1", "user2", "user3", "user4", "user5"]
            await self.bot.run_multi_user(user_ids)
            
            # Check that _process_user was called only for the first max_users_per_run users
            self.assertEqual(self.bot._process_user.call_count, self.config.max_users_per_run)

if __name__ == "__main__":
    unittest.main()