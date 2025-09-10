# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Admin Cleanup Service Integration

Tests the integration between admin cleanup service and storage monitoring,
including storage warnings and cleanup operations with real-time updates.
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.admin.components.cleanup_service import CleanupService
from models import ProcessingStatus


class TestAdminCleanupIntegration(unittest.TestCase):
    """Test admin cleanup service integration with storage monitoring"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_db_manager = Mock()
        self.mock_config = Mock()
        
        # Create cleanup service
        self.cleanup_service = CleanupService(self.mock_db_manager, self.mock_config)
    
    def test_cleanup_service_initialization(self):
        """Test cleanup service initializes correctly"""
        self.assertIsNotNone(self.cleanup_service.db_manager)
        self.assertIsNotNone(self.cleanup_service.config)
        # Storage integration may or may not be available depending on imports
    
    def test_get_cleanup_statistics_basic(self):
        """Test getting basic cleanup statistics"""
        # Mock database session
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        
        # Mock query results
        mock_session.query.return_value.count.return_value = 10
        mock_session.query.return_value.filter_by.return_value.count.return_value = 5
        mock_session.query.return_value.distinct.return_value.all.return_value = [('user1',), ('user2',)]
        mock_session.query.return_value.filter.return_value.count.return_value = 3
        mock_session.query.return_value.join.return_value.filter.return_value.count.return_value = 8
        
        self.mock_db_manager.get_session.return_value = mock_session
        
        stats = self.cleanup_service.get_cleanup_statistics()
        
        # Verify basic statistics are returned
        self.assertIn('processing_runs', stats)
        self.assertIn('total_posts', stats)
        self.assertIn('total_images', stats)
        self.assertIn('rejected_images', stats)
        self.assertIn('posted_images', stats)
        self.assertIn('error_images', stats)
        self.assertIn('pending_review', stats)
        self.assertIn('approved', stats)
        self.assertIn('users', stats)
        self.assertIn('storage_available', stats)
    
    @patch('scripts.maintenance.data_cleanup.DataCleanupManager')
    def test_cleanup_old_processing_runs(self, mock_cleanup_manager_class):
        """Test cleanup old processing runs"""
        # Mock cleanup manager
        mock_cleanup_manager = Mock()
        mock_cleanup_manager.archive_old_processing_runs.return_value = 5
        mock_cleanup_manager_class.return_value = mock_cleanup_manager
        
        result = self.cleanup_service.cleanup_old_processing_runs(days=30, dry_run=True)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 5)
        self.assertTrue(result['dry_run'])
        self.assertIn('message', result)
    
    @patch('scripts.maintenance.data_cleanup.DataCleanupManager')
    def test_cleanup_old_images(self, mock_cleanup_manager_class):
        """Test cleanup old images"""
        # Mock cleanup manager
        mock_cleanup_manager = Mock()
        mock_cleanup_manager.cleanup_old_images.return_value = 15
        mock_cleanup_manager_class.return_value = mock_cleanup_manager
        
        result = self.cleanup_service.cleanup_old_images(
            status=ProcessingStatus.REJECTED, 
            days=7, 
            dry_run=True
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 15)
        self.assertTrue(result['dry_run'])
        self.assertIn('message', result)
    
    def test_cleanup_with_storage_integration_available(self):
        """Test cleanup when storage integration is available"""
        # Mock storage integration
        mock_storage_integration = Mock()
        mock_cleanup_result = Mock()
        mock_cleanup_result.success = True
        mock_cleanup_result.items_cleaned = 20
        mock_cleanup_result.storage_freed_gb = 0.5
        mock_cleanup_result.error_message = None
        
        mock_storage_integration.cleanup_old_images_with_monitoring.return_value = mock_cleanup_result
        mock_storage_integration.recalculate_storage_after_cleanup.return_value = Mock()
        mock_storage_integration.check_and_lift_storage_limits.return_value = True
        
        # Inject storage integration
        self.cleanup_service.storage_integration = mock_storage_integration
        
        result = self.cleanup_service.cleanup_old_images_with_storage_monitoring(
            status=ProcessingStatus.REJECTED,
            days=7,
            dry_run=False
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 20)
        self.assertEqual(result['storage_freed_gb'], 0.5)
        self.assertFalse(result['dry_run'])
        self.assertIn('message', result)
        
        # Verify storage integration was called
        mock_storage_integration.cleanup_old_images_with_monitoring.assert_called_once()
    
    def test_cleanup_without_storage_integration(self):
        """Test cleanup when storage integration is not available"""
        # Ensure no storage integration
        self.cleanup_service.storage_integration = None
        
        with patch('scripts.maintenance.data_cleanup.DataCleanupManager') as mock_cleanup_manager_class:
            mock_cleanup_manager = Mock()
            mock_cleanup_manager.cleanup_old_images.return_value = 10
            mock_cleanup_manager_class.return_value = mock_cleanup_manager
            
            result = self.cleanup_service.cleanup_old_images_with_storage_monitoring(
                status=ProcessingStatus.REJECTED,
                days=7,
                dry_run=True
            )
            
            # Should fall back to basic cleanup
            self.assertTrue(result['success'])
            self.assertEqual(result['count'], 10)
    
    def test_run_full_cleanup_with_storage_monitoring(self):
        """Test full cleanup with storage monitoring"""
        # Mock storage integration
        mock_storage_integration = Mock()
        mock_summary = Mock()
        mock_summary.total_items_cleaned = 100
        mock_summary.total_storage_freed_gb = 2.5
        mock_summary.limit_lifted = True
        mock_summary.to_dict.return_value = {
            'total_items_cleaned': 100,
            'total_storage_freed_gb': 2.5,
            'limit_lifted': True
        }
        
        mock_storage_integration.run_full_cleanup_with_monitoring.return_value = mock_summary
        
        # Inject storage integration
        self.cleanup_service.storage_integration = mock_storage_integration
        
        result = self.cleanup_service.run_full_cleanup(dry_run=False)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_items'], 100)
        self.assertEqual(result['storage_freed_gb'], 2.5)
        self.assertTrue(result['limit_lifted'])
        self.assertFalse(result['dry_run'])
        self.assertIn('message', result)
        
        # Verify storage integration was called
        mock_storage_integration.run_full_cleanup_with_monitoring.assert_called_once_with(dry_run=False)
    
    def test_error_handling_in_cleanup_operations(self):
        """Test error handling in cleanup operations"""
        # Mock storage integration to raise an exception
        mock_storage_integration = Mock()
        mock_storage_integration.cleanup_old_images_with_monitoring.side_effect = Exception("Test error")
        
        # Inject storage integration
        self.cleanup_service.storage_integration = mock_storage_integration
        
        result = self.cleanup_service.cleanup_old_images_with_storage_monitoring(
            status=ProcessingStatus.REJECTED,
            days=7,
            dry_run=False
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Test error')


if __name__ == '__main__':
    unittest.main()