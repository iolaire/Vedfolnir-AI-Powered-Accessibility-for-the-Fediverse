# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test for reset_app.py user data deletion functionality

This test verifies that the --reset-complete and --delete-all-user-data options
properly delete all user data including sessions, images, platforms, etc.
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the reset manager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'maintenance'))
from reset_app import AppResetManager


class TestResetAppUserDataDeletion(unittest.TestCase):
    """Test reset_app.py user data deletion functionality"""
    
    def setUp(self):
        """Set up test environment with mocked dependencies"""
        # Mock the config and database manager
        self.mock_config = MagicMock()
        self.mock_db_manager = MagicMock()
        self.mock_cleanup_manager = MagicMock()
        
        # Mock Redis client
        self.mock_redis = MagicMock()
        self.mock_redis.ping.return_value = True
        self.mock_redis.keys.return_value = [b'vedfolnir:session:test123']
        self.mock_redis.delete.return_value = 1
        
        # Create reset manager with mocked dependencies
        with patch('scripts.maintenance.reset_app.Config', return_value=self.mock_config), \
             patch('scripts.maintenance.reset_app.DatabaseManager', return_value=self.mock_db_manager), \
             patch('scripts.maintenance.reset_app.DataCleanupManager', return_value=self.mock_cleanup_manager), \
             patch('redis.Redis', return_value=self.mock_redis):
            
            self.reset_manager = AppResetManager()
    
    def test_delete_all_user_data_dry_run_with_mocked_data(self):
        """Test that dry run correctly identifies data to delete with mocked data"""
        # Mock session and query results
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        
        # Mock query results
        mock_session.query.return_value.all.return_value = [MagicMock(id=1, username='test_user')]
        mock_session.query.return_value.count.return_value = 5
        
        self.mock_db_manager.get_session.return_value = mock_session
        
        # Mock Redis keys
        self.mock_redis.keys.return_value = [b'vedfolnir:session:test1', b'vedfolnir:session:test2']
        
        # Run dry run
        success = self.reset_manager.delete_all_user_data(dry_run=True)
        
        # Verify dry run succeeded
        self.assertTrue(success)
        
        # Verify session was accessed
        self.mock_db_manager.get_session.assert_called()
        
        # Verify Redis was queried
        self.mock_redis.keys.assert_called_with("vedfolnir:session:*")
    
    def test_delete_all_user_data_handles_no_config(self):
        """Test that method handles missing configuration gracefully"""
        # Create reset manager with no config
        reset_manager = AppResetManager()
        reset_manager.config = None
        
        # Run deletion
        success = reset_manager.delete_all_user_data(dry_run=True)
        
        # Should fail gracefully
        self.assertFalse(success)
    
    def test_print_deletion_summary(self):
        """Test that deletion summary prints correctly"""
        test_results = {
            'users_processed': 2,
            'posts': 5,
            'images': 10,
            'image_files': 8,
            'processing_runs': 3,
            'platform_connections': 2,
            'caption_tasks': 1,
            'caption_settings': 1,
            'user_sessions_db': 4,
            'user_sessions_redis': 2,
            'job_audit_logs': 15,
            'gdpr_audit_logs': 0,
            'storage_events': 0,
            'storage_overrides': 0,
            'directories_removed': 2
        }
        
        # Capture log output
        with patch('scripts.maintenance.reset_app.logger') as mock_logger:
            self.reset_manager._print_deletion_summary(test_results, dry_run=True)
            
            # Verify summary was logged
            mock_logger.info.assert_called()
            
            # Check that key information was included in the calls
            call_args_list = [call[0][0] for call in mock_logger.info.call_args_list]
            summary_text = ' '.join(call_args_list)
            
            self.assertIn('Users Processed: 2', summary_text)
            self.assertIn('Posts: 5', summary_text)
            self.assertIn('Images (DB): 10', summary_text)
            self.assertIn('Total Items:', summary_text)
    
    def test_reset_complete_includes_user_data_deletion(self):
        """Test that reset_complete includes comprehensive user data deletion"""
        # Mock all the methods to avoid actual operations
        with patch.object(self.reset_manager, 'delete_all_user_data', return_value=True) as mock_delete_data, \
             patch.object(self.reset_manager, 'reset_database_only', return_value=True) as mock_db_reset, \
             patch.object(self.reset_manager, 'reset_storage_only', return_value=True) as mock_storage_reset, \
             patch('os.path.exists', return_value=False):
            
            # Run reset complete in dry run mode
            success = self.reset_manager.reset_complete(dry_run=True)
            
            # Verify it succeeded
            self.assertTrue(success)
            
            # Verify that user data deletion was called
            mock_delete_data.assert_called_once_with(dry_run=True)
            
            # Verify other methods were called
            mock_db_reset.assert_called_once_with(dry_run=True)
            mock_storage_reset.assert_called_once_with(dry_run=True)
    
    def test_clear_redis_cache_dry_run(self):
        """Test Redis cache clearing in dry run mode"""
        # Mock Redis keys
        self.mock_redis.keys.side_effect = [
            [b'session:1', b'session:2'],  # session keys
            [b'user_platforms:1'],         # user platform keys
            [b'platform:1'],               # individual platform keys
            [b'platform_stats:1']          # platform stats keys
        ]
        
        # Run dry run
        success = self.reset_manager.clear_redis_cache(dry_run=True)
        
        # Verify success
        self.assertTrue(success)
        
        # Verify Redis keys were queried but not deleted
        self.assertEqual(self.mock_redis.keys.call_count, 4)
        self.mock_redis.delete.assert_not_called()
    
    def test_clear_redis_cache_actual_deletion(self):
        """Test Redis cache clearing with actual deletion"""
        # Mock Redis keys
        self.mock_redis.keys.side_effect = [
            [b'session:1', b'session:2'],  # session keys
            [b'user_platforms:1'],         # user platform keys
            [b'platform:1'],               # individual platform keys
            [b'platform_stats:1'],         # platform stats keys
            [b'vedfolnir:other']            # other keys
        ]
        self.mock_redis.delete.return_value = 2
        
        # Run actual deletion
        success = self.reset_manager.clear_redis_cache(dry_run=False)
        
        # Verify success
        self.assertTrue(success)
        
        # Verify Redis keys were queried and deleted
        self.assertEqual(self.mock_redis.keys.call_count, 5)
        self.assertEqual(self.mock_redis.delete.call_count, 5)


if __name__ == '__main__':
    unittest.main()