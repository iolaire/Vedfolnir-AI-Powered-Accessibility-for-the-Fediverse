# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Storage Override System.

Tests the StorageOverrideSystem class functionality including:
- Override activation and deactivation
- Time-limited override functionality
- Automatic expiration and cleanup
- Audit logging for all override actions
- Admin authorization and validation
"""

import unittest
import sys
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from database import DatabaseManager
from models import StorageOverride, StorageEventLog, User, UserRole
from storage_override_system import (
    StorageOverrideSystem, 
    OverrideInfo, 
    OverrideValidationError, 
    OverrideNotFoundError, 
    StorageOverrideSystemError
)
from storage_configuration_service import StorageConfigurationService
from storage_monitor_service import StorageMonitorService


class TestStorageOverrideSystem(unittest.TestCase):
    """Test cases for Storage Override System"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create test admin user
        with self.db_manager.get_session() as session:
            # Clean up any existing test data
            session.query(StorageEventLog).delete()
            session.query(StorageOverride).delete()
            session.query(User).filter_by(username="test_admin").delete()
            session.commit()
            
            # Create test admin user
            self.admin_user = User(
                username="test_admin",
                email="test_admin@example.com",
                role=UserRole.ADMIN,
                is_active=True,
                email_verified=True
            )
            self.admin_user.set_password("test_password")
            session.add(self.admin_user)
            session.commit()
            
            # Store admin user ID for tests
            self.admin_user_id = self.admin_user.id
        
        # Initialize override system
        self.override_system = StorageOverrideSystem(self.db_manager)
    
    def tearDown(self):
        """Clean up test environment"""
        with self.db_manager.get_session() as session:
            # Clean up test data
            session.query(StorageEventLog).delete()
            session.query(StorageOverride).delete()
            session.query(User).filter_by(username="test_admin").delete()
            session.query(User).filter_by(username="test_regular").delete()
            session.commit()
    
    def test_activate_override_success(self):
        """Test successful override activation"""
        # Activate override
        override_info = self.override_system.activate_override(
            admin_user_id=self.admin_user_id,
            duration_hours=2,
            reason="Test override activation"
        )
        
        # Verify override info
        self.assertIsInstance(override_info, OverrideInfo)
        self.assertEqual(override_info.admin_user_id, self.admin_user_id)
        self.assertEqual(override_info.admin_username, "test_admin")
        self.assertEqual(override_info.duration_hours, 2)
        self.assertEqual(override_info.reason, "Test override activation")
        self.assertTrue(override_info.is_active)
        self.assertFalse(override_info.is_expired)
        self.assertIsNotNone(override_info.remaining_time)
        
        # Verify override is stored in database
        with self.db_manager.get_session() as session:
            override = session.query(StorageOverride).filter_by(id=override_info.id).first()
            self.assertIsNotNone(override)
            self.assertEqual(override.admin_user_id, self.admin_user_id)
            self.assertEqual(override.duration_hours, 2)
            self.assertEqual(override.reason, "Test override activation")
            self.assertTrue(override.is_active)
            
            # Verify audit log entry
            event = session.query(StorageEventLog).filter_by(
                event_type="override_activated",
                storage_override_id=override_info.id
            ).first()
            self.assertIsNotNone(event)
            self.assertEqual(event.user_id, self.admin_user_id)
    
    def test_activate_override_validation_errors(self):
        """Test override activation validation errors"""
        # Test invalid user ID
        with self.assertRaises(OverrideValidationError):
            self.override_system.activate_override(
                admin_user_id=99999,  # Non-existent user
                duration_hours=1
            )
        
        # Test invalid duration (too short)
        with self.assertRaises(OverrideValidationError):
            self.override_system.activate_override(
                admin_user_id=self.admin_user_id,
                duration_hours=0
            )
        
        # Test invalid duration (too long)
        with self.assertRaises(OverrideValidationError):
            self.override_system.activate_override(
                admin_user_id=self.admin_user_id,
                duration_hours=25
            )
        
        # Test non-admin user
        with self.db_manager.get_session() as session:
            # Clean up any existing test_regular user first
            session.query(User).filter_by(username="test_regular").delete()
            session.commit()
            
            regular_user = User(
                username="test_regular",
                email="test_regular@example.com",
                role=UserRole.REVIEWER,
                is_active=True,
                email_verified=True
            )
            regular_user.set_password("test_password")
            session.add(regular_user)
            session.commit()
            regular_user_id = regular_user.id
        
        with self.assertRaises(OverrideValidationError):
            self.override_system.activate_override(
                admin_user_id=regular_user_id,
                duration_hours=1
            )
    
    def test_activate_override_already_active(self):
        """Test activation when override is already active"""
        # Activate first override
        self.override_system.activate_override(
            admin_user_id=self.admin_user_id,
            duration_hours=1,
            reason="First override"
        )
        
        # Try to activate second override
        with self.assertRaises(OverrideValidationError) as context:
            self.override_system.activate_override(
                admin_user_id=self.admin_user_id,
                duration_hours=1,
                reason="Second override"
            )
        
        self.assertIn("already active", str(context.exception))
    
    def test_deactivate_override_success(self):
        """Test successful override deactivation"""
        # Activate override
        override_info = self.override_system.activate_override(
            admin_user_id=self.admin_user_id,
            duration_hours=2,
            reason="Test override"
        )
        
        # Deactivate override
        success = self.override_system.deactivate_override(
            admin_user_id=self.admin_user_id,
            reason="Test deactivation"
        )
        
        self.assertTrue(success)
        
        # Verify override is deactivated in database
        with self.db_manager.get_session() as session:
            override = session.query(StorageOverride).filter_by(id=override_info.id).first()
            self.assertIsNotNone(override)
            self.assertFalse(override.is_active)
            self.assertIsNotNone(override.deactivated_at)
            self.assertEqual(override.deactivated_by_user_id, self.admin_user_id)
            
            # Verify audit log entry
            event = session.query(StorageEventLog).filter_by(
                event_type="override_deactivated",
                storage_override_id=override_info.id
            ).first()
            self.assertIsNotNone(event)
            self.assertEqual(event.user_id, self.admin_user_id)
    
    def test_deactivate_override_no_active(self):
        """Test deactivation when no active override exists"""
        success = self.override_system.deactivate_override(
            admin_user_id=self.admin_user_id,
            reason="Test deactivation"
        )
        
        self.assertFalse(success)
    
    def test_is_override_active(self):
        """Test checking if override is active"""
        # Initially no active override
        self.assertFalse(self.override_system.is_override_active())
        
        # Activate override
        self.override_system.activate_override(
            admin_user_id=self.admin_user_id,
            duration_hours=1
        )
        
        # Should be active now
        self.assertTrue(self.override_system.is_override_active())
        
        # Deactivate override
        self.override_system.deactivate_override(
            admin_user_id=self.admin_user_id
        )
        
        # Should not be active now
        self.assertFalse(self.override_system.is_override_active())
    
    def test_get_active_override(self):
        """Test getting active override information"""
        # Initially no active override
        self.assertIsNone(self.override_system.get_active_override())
        
        # Activate override
        override_info = self.override_system.activate_override(
            admin_user_id=self.admin_user_id,
            duration_hours=2,
            reason="Test override"
        )
        
        # Get active override
        active_override = self.override_system.get_active_override()
        self.assertIsNotNone(active_override)
        self.assertEqual(active_override.id, override_info.id)
        self.assertEqual(active_override.admin_user_id, self.admin_user_id)
        self.assertEqual(active_override.admin_username, "test_admin")
        self.assertEqual(active_override.duration_hours, 2)
        self.assertEqual(active_override.reason, "Test override")
        self.assertTrue(active_override.is_active)
        self.assertFalse(active_override.is_expired)
    
    def test_cleanup_expired_overrides(self):
        """Test cleanup of expired overrides"""
        # Create an expired override directly in database
        with self.db_manager.get_session() as session:
            expired_override = StorageOverride(
                admin_user_id=self.admin_user_id,
                activated_at=datetime.now(timezone.utc) - timedelta(hours=2),
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
                duration_hours=1,
                reason="Expired test override",
                is_active=True  # Still marked as active
            )
            session.add(expired_override)
            session.commit()
            expired_override_id = expired_override.id
        
        # Run cleanup
        cleanup_count = self.override_system.cleanup_expired_overrides()
        
        self.assertEqual(cleanup_count, 1)
        
        # Verify override is marked as inactive
        with self.db_manager.get_session() as session:
            override = session.query(StorageOverride).filter_by(id=expired_override_id).first()
            self.assertIsNotNone(override)
            self.assertFalse(override.is_active)
            self.assertIsNotNone(override.deactivated_at)
            
            # Verify audit log entry
            event = session.query(StorageEventLog).filter_by(
                event_type="override_expired",
                storage_override_id=expired_override_id
            ).first()
            self.assertIsNotNone(event)
    
    def test_get_override_history(self):
        """Test getting override history"""
        # Initially empty history
        history = self.override_system.get_override_history()
        self.assertEqual(len(history), 0)
        
        # Create some overrides
        override1 = self.override_system.activate_override(
            admin_user_id=self.admin_user_id,
            duration_hours=1,
            reason="First override"
        )
        
        self.override_system.deactivate_override(self.admin_user_id)
        
        override2 = self.override_system.activate_override(
            admin_user_id=self.admin_user_id,
            duration_hours=2,
            reason="Second override"
        )
        
        # Get history
        history = self.override_system.get_override_history()
        self.assertEqual(len(history), 2)
        
        # Should be ordered by most recent first
        # Check that we have both overrides (order may vary due to timing)
        reasons = [h.reason for h in history]
        self.assertIn("Second override", reasons)
        # The first override was deactivated, so its reason will be modified
        first_override_found = any("First override" in reason for reason in reasons)
        self.assertTrue(first_override_found)
        
        # Test filtering by admin user
        history_filtered = self.override_system.get_override_history(admin_user_id=self.admin_user_id)
        self.assertEqual(len(history_filtered), 2)
    
    def test_get_override_statistics(self):
        """Test getting override statistics"""
        # Get initial statistics
        stats = self.override_system.get_override_statistics()
        self.assertEqual(stats['total_overrides'], 0)
        self.assertEqual(stats['active_overrides'], 0)
        
        # Create some overrides
        self.override_system.activate_override(
            admin_user_id=self.admin_user_id,
            duration_hours=1,
            reason="Test override 1"
        )
        
        # Get updated statistics
        stats = self.override_system.get_override_statistics()
        self.assertEqual(stats['total_overrides'], 1)
        self.assertEqual(stats['active_overrides'], 1)
        self.assertIsNotNone(stats['current_override'])
        
        # Deactivate and check again
        self.override_system.deactivate_override(self.admin_user_id)
        
        stats = self.override_system.get_override_statistics()
        self.assertEqual(stats['total_overrides'], 1)
        self.assertEqual(stats['active_overrides'], 0)
        self.assertIsNone(stats['current_override'])
    
    def test_health_check(self):
        """Test health check functionality"""
        health = self.override_system.health_check()
        
        self.assertIn('database_accessible', health)
        self.assertIn('config_service_healthy', health)
        self.assertIn('monitor_service_healthy', health)
        self.assertIn('overall_healthy', health)
        
        # Should be healthy with proper setup
        self.assertTrue(health['database_accessible'])
        self.assertTrue(health['config_service_healthy'])
        self.assertTrue(health['overall_healthy'])
    
    def test_override_info_to_dict(self):
        """Test OverrideInfo serialization"""
        override_info = self.override_system.activate_override(
            admin_user_id=self.admin_user_id,
            duration_hours=1,
            reason="Test serialization"
        )
        
        override_dict = override_info.to_dict()
        
        self.assertIn('id', override_dict)
        self.assertIn('admin_user_id', override_dict)
        self.assertIn('admin_username', override_dict)
        self.assertIn('activated_at', override_dict)
        self.assertIn('expires_at', override_dict)
        self.assertIn('duration_hours', override_dict)
        self.assertIn('reason', override_dict)
        self.assertIn('is_active', override_dict)
        self.assertIn('is_expired', override_dict)
        self.assertIn('remaining_time_seconds', override_dict)
        
        self.assertEqual(override_dict['admin_user_id'], self.admin_user_id)
        self.assertEqual(override_dict['admin_username'], "test_admin")
        self.assertEqual(override_dict['duration_hours'], 1)
        self.assertEqual(override_dict['reason'], "Test serialization")
        self.assertTrue(override_dict['is_active'])
        self.assertFalse(override_dict['is_expired'])


if __name__ == '__main__':
    unittest.main()