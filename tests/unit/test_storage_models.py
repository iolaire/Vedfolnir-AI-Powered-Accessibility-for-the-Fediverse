#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for storage management models.
Tests StorageOverride and StorageEventLog models functionality.
"""

import unittest
import sys
import os
from datetime import datetime, timedelta
import json

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from database import DatabaseManager
from models import StorageOverride, StorageEventLog, User, UserRole

class TestStorageModels(unittest.TestCase):
    """Test cases for storage management models"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database connection"""
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
    
    def setUp(self):
        """Set up test data for each test"""
        self.session = self.db_manager.get_session()
        
        # Create a test admin user
        self.admin_user = User(
            username="test_admin",
            email="admin@test.com",
            role=UserRole.ADMIN,
            is_active=True,
            email_verified=True
        )
        self.admin_user.set_password("test_password")
        self.session.add(self.admin_user)
        self.session.commit()
    
    def tearDown(self):
        """Clean up test data after each test"""
        # Clean up test data
        self.session.query(StorageEventLog).delete()
        self.session.query(StorageOverride).delete()
        self.session.query(User).filter_by(username="test_admin").delete()
        self.session.commit()
        self.session.close()
    
    def test_storage_override_creation(self):
        """Test creating a storage override"""
        expires_at = datetime.utcnow() + timedelta(hours=2)
        
        override = StorageOverride(
            admin_user_id=self.admin_user.id,
            expires_at=expires_at,
            duration_hours=2,
            reason="Testing storage override",
            storage_gb_at_activation=8.5,
            limit_gb_at_activation=10.0
        )
        
        self.session.add(override)
        self.session.commit()
        
        # Verify the override was created
        self.assertIsNotNone(override.id)
        self.assertEqual(override.admin_user_id, self.admin_user.id)
        self.assertEqual(override.duration_hours, 2)
        self.assertEqual(override.reason, "Testing storage override")
        self.assertTrue(override.is_active)
        self.assertIsNone(override.deactivated_at)
    
    def test_storage_override_expiration(self):
        """Test storage override expiration logic"""
        # Create an expired override
        expired_override = StorageOverride(
            admin_user_id=self.admin_user.id,
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            duration_hours=1,
            reason="Expired override test"
        )
        
        # Create an active override
        active_override = StorageOverride(
            admin_user_id=self.admin_user.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),  # Expires in 1 hour
            duration_hours=1,
            reason="Active override test"
        )
        
        self.session.add_all([expired_override, active_override])
        self.session.commit()
        
        # Test expiration logic
        self.assertTrue(expired_override.is_expired())
        self.assertFalse(expired_override.is_currently_active())
        
        self.assertFalse(active_override.is_expired())
        self.assertTrue(active_override.is_currently_active())
        
        # Test remaining time
        self.assertIsNone(expired_override.get_remaining_time())
        remaining = active_override.get_remaining_time()
        self.assertIsNotNone(remaining)
        self.assertGreater(remaining.total_seconds(), 0)
    
    def test_storage_override_deactivation(self):
        """Test manual deactivation of storage override"""
        override = StorageOverride(
            admin_user_id=self.admin_user.id,
            expires_at=datetime.utcnow() + timedelta(hours=2),
            duration_hours=2,
            reason="Test deactivation"
        )
        
        self.session.add(override)
        self.session.commit()
        
        # Initially active
        self.assertTrue(override.is_currently_active())
        
        # Deactivate
        override.deactivate(self.admin_user.id, "Manual deactivation test")
        self.session.commit()
        
        # Should now be inactive
        self.assertFalse(override.is_active)
        self.assertFalse(override.is_currently_active())
        self.assertIsNotNone(override.deactivated_at)
        self.assertEqual(override.deactivated_by_user_id, self.admin_user.id)
        self.assertIn("Manual deactivation test", override.reason)
    
    def test_storage_event_log_creation(self):
        """Test creating storage event log entries"""
        event = StorageEventLog.log_event(
            session=self.session,
            event_type='test_event',
            storage_gb=7.5,
            limit_gb=10.0,
            user_id=self.admin_user.id,
            details={'test': True, 'action': 'unit_test'}
        )
        
        self.session.commit()
        
        # Verify the event was created
        self.assertIsNotNone(event.id)
        self.assertEqual(event.event_type, 'test_event')
        self.assertEqual(event.storage_gb, 7.5)
        self.assertEqual(event.limit_gb, 10.0)
        self.assertEqual(event.user_id, self.admin_user.id)
        self.assertEqual(event.usage_percentage, 75.0)  # 7.5/10.0 * 100
        
        # Test details handling
        details = event.get_details()
        self.assertEqual(details['test'], True)
        self.assertEqual(details['action'], 'unit_test')
    
    def test_storage_event_log_helper_methods(self):
        """Test storage event log helper methods"""
        # Test limit reached logging
        limit_event = StorageEventLog.log_limit_reached(
            session=self.session,
            storage_gb=10.5,
            limit_gb=10.0,
            details={'reason': 'caption_generation_blocked'}
        )
        
        self.assertEqual(limit_event.event_type, 'limit_reached')
        self.assertEqual(limit_event.storage_gb, 10.5)
        self.assertEqual(limit_event.limit_gb, 10.0)
        self.assertEqual(limit_event.usage_percentage, 105.0)
        
        # Test cleanup logging
        cleanup_event = StorageEventLog.log_cleanup_performed(
            session=self.session,
            storage_gb_before=10.5,
            storage_gb_after=8.0,
            limit_gb=10.0,
            user_id=self.admin_user.id,
            cleanup_details={'files_deleted': 50}
        )
        
        self.assertEqual(cleanup_event.event_type, 'cleanup_performed')
        self.assertEqual(cleanup_event.storage_gb, 8.0)  # After cleanup
        details = cleanup_event.get_details()
        self.assertEqual(details['storage_gb_before'], 10.5)
        self.assertEqual(details['space_freed_gb'], 2.5)
        self.assertEqual(details['cleanup_details']['files_deleted'], 50)
        
        # Test warning threshold logging
        warning_event = StorageEventLog.log_warning_threshold_exceeded(
            session=self.session,
            storage_gb=8.5,
            limit_gb=10.0,
            threshold_percentage=80
        )
        
        self.assertEqual(warning_event.event_type, 'warning_threshold_exceeded')
        self.assertEqual(warning_event.usage_percentage, 85.0)
        details = warning_event.get_details()
        self.assertEqual(details['threshold_percentage'], 80)
        
        self.session.commit()
    
    def test_storage_override_with_event_logging(self):
        """Test storage override with related event logging"""
        # Create an override
        override = StorageOverride(
            admin_user_id=self.admin_user.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            duration_hours=1,
            reason="Integration test",
            storage_gb_at_activation=9.5,
            limit_gb_at_activation=10.0
        )
        
        self.session.add(override)
        self.session.commit()
        
        # Log override activation
        activation_event = StorageEventLog.log_override_activated(
            session=self.session,
            storage_gb=9.5,
            limit_gb=10.0,
            user_id=self.admin_user.id,
            storage_override_id=override.id,
            duration_hours=1,
            reason="Integration test"
        )
        
        self.session.commit()
        
        # Verify the relationship
        self.assertEqual(activation_event.storage_override_id, override.id)
        self.assertEqual(activation_event.event_type, 'override_activated')
        
        # Test the relationship works
        self.assertIn(activation_event, override.related_events)
        
        # Log override deactivation
        override.deactivate(self.admin_user.id, "Test completed")
        
        deactivation_event = StorageEventLog.log_override_deactivated(
            session=self.session,
            storage_gb=9.5,
            limit_gb=10.0,
            user_id=self.admin_user.id,
            storage_override_id=override.id,
            reason="Test completed"
        )
        
        self.session.commit()
        
        # Verify both events are linked to the override
        self.assertEqual(len(override.related_events), 2)
        event_types = [event.event_type for event in override.related_events]
        self.assertIn('override_activated', event_types)
        self.assertIn('override_deactivated', event_types)
    
    def test_storage_event_log_details_handling(self):
        """Test JSON details handling in storage event log"""
        complex_details = {
            'action': 'complex_test',
            'metadata': {
                'files_processed': 100,
                'errors': ['file1.jpg', 'file2.png'],
                'success_rate': 98.5
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        event = StorageEventLog(
            event_type='complex_test',
            storage_gb=5.0,
            limit_gb=10.0,
            user_id=self.admin_user.id
        )
        
        # Test setting complex details
        event.set_details(complex_details)
        self.session.add(event)
        self.session.commit()
        
        # Test retrieving complex details
        retrieved_details = event.get_details()
        self.assertEqual(retrieved_details['action'], 'complex_test')
        self.assertEqual(retrieved_details['metadata']['files_processed'], 100)
        self.assertEqual(len(retrieved_details['metadata']['errors']), 2)
        self.assertEqual(retrieved_details['metadata']['success_rate'], 98.5)
        
        # Test empty details
        empty_event = StorageEventLog(
            event_type='empty_test',
            storage_gb=1.0,
            limit_gb=10.0
        )
        self.assertEqual(empty_event.get_details(), {})
        
        # Test invalid JSON handling
        empty_event.details = "invalid json {"
        self.assertEqual(empty_event.get_details(), {})

if __name__ == '__main__':
    unittest.main()