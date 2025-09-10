# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for maintenance data integrity protection mechanisms.

Tests data modification attempt logging, validation, rollback mechanisms,
and data consistency checks during maintenance operations.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.maintenance.components.maintenance_data_integrity_protection import (
    MaintenanceDataIntegrityProtection,
    DataModificationAttemptType,
    DataModificationStatus,
    DataModificationAttempt,
    DataConsistencyCheck
)
from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import MaintenanceMode, MaintenanceStatus


class TestMaintenanceDataIntegrityProtection(unittest.TestCase):
    """Test cases for maintenance data integrity protection mechanisms"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock database manager
        self.mock_db_manager = Mock()
        
        # Mock maintenance service
        self.mock_maintenance_service = Mock()
        
        # Create data integrity protection service
        self.integrity_service = MaintenanceDataIntegrityProtection(
            db_manager=self.mock_db_manager,
            maintenance_service=self.mock_maintenance_service
        )
        
        # Mock maintenance status
        self.maintenance_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Test maintenance",
            estimated_duration=30,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
    
    def test_log_data_modification_attempt(self):
        """Test logging of data modification attempts during maintenance"""
        
        # Mock maintenance service to return active maintenance
        self.mock_maintenance_service.get_maintenance_status.return_value = self.maintenance_status
        
        # Log a data modification attempt
        attempt_id = self.integrity_service.log_data_modification_attempt(
            user_id=123,
            username="testuser",
            attempt_type=DataModificationAttemptType.USER_PROFILE_UPDATE,
            endpoint="/profile/update",
            method="POST",
            data_preview={"name": "New Name", "email": "new@example.com"},
            status=DataModificationStatus.BLOCKED,
            error_message="Operation blocked during maintenance"
        )
        
        # Verify attempt was logged
        self.assertIsNotNone(attempt_id)
        
        # Get the logged attempt
        attempts = self.integrity_service.get_modification_attempts(user_id=123)
        self.assertEqual(len(attempts), 1)
        
        attempt = attempts[0]
        self.assertEqual(attempt.user_id, 123)
        self.assertEqual(attempt.username, "testuser")
        self.assertEqual(attempt.attempt_type, DataModificationAttemptType.USER_PROFILE_UPDATE)
        self.assertEqual(attempt.endpoint, "/profile/update")
        self.assertEqual(attempt.method, "POST")
        self.assertEqual(attempt.status, DataModificationStatus.BLOCKED)
        self.assertEqual(attempt.error_message, "Operation blocked during maintenance")
        self.assertEqual(attempt.maintenance_mode, "normal")
        self.assertEqual(attempt.maintenance_reason, "Test maintenance")
        
        # Verify data preview was sanitized
        self.assertEqual(attempt.data_preview["name"], "New Name")
        self.assertEqual(attempt.data_preview["email"], "new@example.com")
    
    def test_data_preview_sanitization(self):
        """Test that sensitive data is sanitized in data previews"""
        
        # Mock maintenance service
        self.mock_maintenance_service.get_maintenance_status.return_value = self.maintenance_status
        
        # Log attempt with sensitive data
        attempt_id = self.integrity_service.log_data_modification_attempt(
            user_id=123,
            username="testuser",
            attempt_type=DataModificationAttemptType.PASSWORD_CHANGE,
            endpoint="/password/change",
            method="POST",
            data_preview={
                "old_password": "secret123",
                "new_password": "newsecret456",
                "token": "auth_token_12345",
                "name": "Regular Field",
                "long_text": "x" * 150  # Long text that should be truncated
            },
            status=DataModificationStatus.BLOCKED
        )
        
        # Get the logged attempt
        attempts = self.integrity_service.get_modification_attempts(user_id=123)
        attempt = attempts[0]
        
        # Verify sensitive data was redacted
        self.assertEqual(attempt.data_preview["old_password"], "[REDACTED]")
        self.assertEqual(attempt.data_preview["new_password"], "[REDACTED]")
        self.assertEqual(attempt.data_preview["token"], "[REDACTED]")
        
        # Verify regular fields were preserved
        self.assertEqual(attempt.data_preview["name"], "Regular Field")
        
        # Verify long text was truncated
        self.assertTrue(attempt.data_preview["long_text"].endswith("..."))
        self.assertEqual(len(attempt.data_preview["long_text"]), 103)  # 100 chars + "..."
    
    def test_validate_data_modification_safety_during_maintenance(self):
        """Test validation of data modification safety during maintenance"""
        
        # Mock maintenance service to return active maintenance
        self.mock_maintenance_service.get_maintenance_status.return_value = self.maintenance_status
        
        # Test various modification types
        test_cases = [
            (DataModificationAttemptType.USER_PROFILE_UPDATE, {"name": "New Name"}),
            (DataModificationAttemptType.USER_SETTINGS_CHANGE, {"setting": "value"}),
            (DataModificationAttemptType.PASSWORD_CHANGE, {"password": "new_password"}),
            (DataModificationAttemptType.CAPTION_SETTINGS_UPDATE, {"max_posts": 10}),
            (DataModificationAttemptType.IMAGE_CAPTION_UPDATE, {"caption": "New caption"}),
            (DataModificationAttemptType.IMAGE_REGENERATION, {"image_id": 123}),
            (DataModificationAttemptType.BATCH_OPERATION, {"operation": "bulk_update"}),
            (DataModificationAttemptType.PLATFORM_CREDENTIAL_UPDATE, {"token": "new_token"})
        ]
        
        for attempt_type, data in test_cases:
            with self.subTest(attempt_type=attempt_type):
                is_safe, error_message = self.integrity_service.validate_data_modification_safety(attempt_type, data)
                
                # During maintenance, all modifications should be blocked
                self.assertFalse(is_safe, f"{attempt_type.value} should not be safe during maintenance")
                self.assertIsNotNone(error_message, f"Error message should be provided for {attempt_type.value}")
                self.assertIn("not allowed during maintenance", error_message)
    
    def test_validate_data_modification_safety_no_maintenance(self):
        """Test validation when maintenance is not active"""
        
        # Mock maintenance service to return inactive maintenance
        inactive_status = MaintenanceStatus(
            is_active=False,
            mode=MaintenanceMode.NORMAL,
            reason=None,
            estimated_duration=None,
            started_at=None,
            estimated_completion=None,
            enabled_by=None,
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        self.mock_maintenance_service.get_maintenance_status.return_value = inactive_status
        
        # Test that modifications are allowed when maintenance is not active
        is_safe, error_message = self.integrity_service.validate_data_modification_safety(
            DataModificationAttemptType.USER_PROFILE_UPDATE,
            {"name": "New Name"}
        )
        
        self.assertTrue(is_safe, "Modifications should be safe when maintenance is not active")
        self.assertIsNone(error_message, "No error message should be provided when maintenance is not active")
    
    def test_validate_data_modification_safety_test_mode(self):
        """Test validation in test mode"""
        
        # Mock maintenance service to return test mode
        test_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.TEST,
            reason="Test maintenance",
            estimated_duration=30,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=True
        )
        self.mock_maintenance_service.get_maintenance_status.return_value = test_status
        
        # Test that modifications are allowed in test mode
        is_safe, error_message = self.integrity_service.validate_data_modification_safety(
            DataModificationAttemptType.USER_PROFILE_UPDATE,
            {"name": "New Name"}
        )
        
        self.assertTrue(is_safe, "Modifications should be safe in test mode")
        self.assertIsNone(error_message, "No error message should be provided in test mode")
    
    def test_rollback_checkpoint_creation_and_execution(self):
        """Test creation and execution of rollback checkpoints"""
        
        # Mock maintenance service
        self.mock_maintenance_service.get_maintenance_status.return_value = self.maintenance_status
        
        # Log a data modification attempt
        attempt_id = self.integrity_service.log_data_modification_attempt(
            user_id=123,
            username="testuser",
            attempt_type=DataModificationAttemptType.USER_PROFILE_UPDATE,
            endpoint="/profile/update",
            method="POST",
            data_preview={"name": "New Name"},
            status=DataModificationStatus.ALLOWED
        )
        
        # Create rollback checkpoint
        rollback_data = {
            "user_id": 123,
            "original_name": "Original Name",
            "table": "users",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        success = self.integrity_service.create_rollback_checkpoint(attempt_id, rollback_data)
        self.assertTrue(success, "Rollback checkpoint creation should succeed")
        
        # Verify rollback data was stored
        attempts = self.integrity_service.get_modification_attempts(user_id=123)
        attempt = attempts[0]
        self.assertEqual(attempt.rollback_info, rollback_data)
        
        # Perform rollback
        rollback_success = self.integrity_service.perform_rollback(attempt_id)
        self.assertTrue(rollback_success, "Rollback should succeed")
        
        # Verify attempt status was updated
        attempts = self.integrity_service.get_modification_attempts(user_id=123)
        attempt = attempts[0]
        self.assertEqual(attempt.status, DataModificationStatus.ROLLED_BACK)
    
    def test_rollback_without_checkpoint(self):
        """Test rollback attempt without checkpoint"""
        
        # Mock maintenance service
        self.mock_maintenance_service.get_maintenance_status.return_value = self.maintenance_status
        
        # Log a data modification attempt without rollback info
        attempt_id = self.integrity_service.log_data_modification_attempt(
            user_id=123,
            username="testuser",
            attempt_type=DataModificationAttemptType.USER_PROFILE_UPDATE,
            endpoint="/profile/update",
            method="POST",
            data_preview={"name": "New Name"},
            status=DataModificationStatus.ALLOWED
        )
        
        # Attempt rollback without checkpoint
        rollback_success = self.integrity_service.perform_rollback(attempt_id)
        self.assertFalse(rollback_success, "Rollback should fail without checkpoint")
    
    def test_rollback_nonexistent_attempt(self):
        """Test rollback of nonexistent attempt"""
        
        # Attempt rollback of nonexistent attempt
        rollback_success = self.integrity_service.perform_rollback("nonexistent_id")
        self.assertFalse(rollback_success, "Rollback should fail for nonexistent attempt")
    
    def test_data_consistency_checks(self):
        """Test data consistency check execution"""
        
        # Test different types of consistency checks
        check_types = [
            'user_data_integrity',
            'image_caption_consistency',
            'platform_connection_validity',
            'settings_consistency',
            'orphaned_records',
            'foreign_key_integrity'
        ]
        
        for check_type in check_types:
            with self.subTest(check_type=check_type):
                check_id = self.integrity_service.run_data_consistency_check(check_type)
                self.assertIsNotNone(check_id, f"Check ID should be returned for {check_type}")
                
                # Get check result
                result = self.integrity_service.get_consistency_check_result(check_id)
                self.assertIsNotNone(result, f"Check result should be available for {check_type}")
                self.assertEqual(result.check_type, check_type)
                self.assertIsInstance(result.timestamp, datetime)
    
    def test_unknown_consistency_check_type(self):
        """Test handling of unknown consistency check type"""
        
        check_id = self.integrity_service.run_data_consistency_check("unknown_check_type")
        self.assertIsNotNone(check_id, "Check ID should be returned even for unknown type")
        
        # Result should exist but with no meaningful data
        result = self.integrity_service.get_consistency_check_result(check_id)
        # The result might be None or empty depending on implementation
        # This tests that the system doesn't crash on unknown check types
    
    def test_modification_attempts_filtering(self):
        """Test filtering of modification attempts"""
        
        # Mock maintenance service
        self.mock_maintenance_service.get_maintenance_status.return_value = self.maintenance_status
        
        # Log multiple attempts with different parameters
        attempts_data = [
            (123, "user1", DataModificationAttemptType.USER_PROFILE_UPDATE, DataModificationStatus.BLOCKED),
            (123, "user1", DataModificationAttemptType.USER_SETTINGS_CHANGE, DataModificationStatus.ALLOWED),
            (456, "user2", DataModificationAttemptType.USER_PROFILE_UPDATE, DataModificationStatus.BLOCKED),
            (456, "user2", DataModificationAttemptType.PASSWORD_CHANGE, DataModificationStatus.FAILED),
        ]
        
        for user_id, username, attempt_type, status in attempts_data:
            self.integrity_service.log_data_modification_attempt(
                user_id=user_id,
                username=username,
                attempt_type=attempt_type,
                endpoint=f"/{attempt_type.value}",
                method="POST",
                data_preview={"test": "data"},
                status=status
            )
        
        # Test filtering by user_id
        user1_attempts = self.integrity_service.get_modification_attempts(user_id=123)
        self.assertEqual(len(user1_attempts), 2)
        self.assertTrue(all(a.user_id == 123 for a in user1_attempts))
        
        user2_attempts = self.integrity_service.get_modification_attempts(user_id=456)
        self.assertEqual(len(user2_attempts), 2)
        self.assertTrue(all(a.user_id == 456 for a in user2_attempts))
        
        # Test filtering by attempt_type
        profile_attempts = self.integrity_service.get_modification_attempts(
            attempt_type=DataModificationAttemptType.USER_PROFILE_UPDATE
        )
        self.assertEqual(len(profile_attempts), 2)
        self.assertTrue(all(a.attempt_type == DataModificationAttemptType.USER_PROFILE_UPDATE for a in profile_attempts))
        
        # Test filtering by status
        blocked_attempts = self.integrity_service.get_modification_attempts(status=DataModificationStatus.BLOCKED)
        self.assertEqual(len(blocked_attempts), 2)
        self.assertTrue(all(a.status == DataModificationStatus.BLOCKED for a in blocked_attempts))
        
        # Test combined filtering
        user1_blocked = self.integrity_service.get_modification_attempts(
            user_id=123,
            status=DataModificationStatus.BLOCKED
        )
        self.assertEqual(len(user1_blocked), 1)
        self.assertEqual(user1_blocked[0].user_id, 123)
        self.assertEqual(user1_blocked[0].status, DataModificationStatus.BLOCKED)
    
    def test_integrity_protection_statistics(self):
        """Test integrity protection statistics collection"""
        
        # Mock maintenance service
        self.mock_maintenance_service.get_maintenance_status.return_value = self.maintenance_status
        
        # Get initial stats
        initial_stats = self.integrity_service.get_integrity_protection_stats()
        self.assertEqual(initial_stats['total_attempts'], 0)
        self.assertEqual(initial_stats['blocked_attempts'], 0)
        
        # Log some attempts
        self.integrity_service.log_data_modification_attempt(
            user_id=123,
            username="user1",
            attempt_type=DataModificationAttemptType.USER_PROFILE_UPDATE,
            endpoint="/profile/update",
            method="POST",
            data_preview={"test": "data"},
            status=DataModificationStatus.BLOCKED
        )
        
        self.integrity_service.log_data_modification_attempt(
            user_id=456,
            username="user2",
            attempt_type=DataModificationAttemptType.USER_SETTINGS_CHANGE,
            endpoint="/settings/update",
            method="POST",
            data_preview={"test": "data"},
            status=DataModificationStatus.ALLOWED
        )
        
        # Run a consistency check
        self.integrity_service.run_data_consistency_check('user_data_integrity')
        
        # Get updated stats
        updated_stats = self.integrity_service.get_integrity_protection_stats()
        self.assertEqual(updated_stats['total_attempts'], 2)
        self.assertEqual(updated_stats['blocked_attempts'], 1)
        self.assertEqual(updated_stats['allowed_attempts'], 1)
        self.assertEqual(updated_stats['consistency_checks_run'], 1)
        self.assertEqual(updated_stats['total_attempts_in_memory'], 2)
        self.assertEqual(updated_stats['total_checks_in_memory'], 1)
    
    def test_custom_rollback_handler_registration(self):
        """Test registration of custom rollback handlers"""
        
        # Create a custom rollback handler
        def custom_rollback_handler(rollback_data: dict) -> bool:
            # Custom rollback logic
            return rollback_data.get('success', True)
        
        # Register the handler
        self.integrity_service.register_rollback_handler(
            DataModificationAttemptType.CAPTION_SETTINGS_UPDATE,
            custom_rollback_handler
        )
        
        # Mock maintenance service
        self.mock_maintenance_service.get_maintenance_status.return_value = self.maintenance_status
        
        # Log an attempt and create rollback checkpoint
        attempt_id = self.integrity_service.log_data_modification_attempt(
            user_id=123,
            username="testuser",
            attempt_type=DataModificationAttemptType.CAPTION_SETTINGS_UPDATE,
            endpoint="/caption_settings/update",
            method="POST",
            data_preview={"setting": "value"},
            status=DataModificationStatus.ALLOWED
        )
        
        # Create rollback checkpoint with success flag
        rollback_data = {"success": True, "data": "test"}
        self.integrity_service.create_rollback_checkpoint(attempt_id, rollback_data)
        
        # Perform rollback using custom handler
        rollback_success = self.integrity_service.perform_rollback(attempt_id)
        self.assertTrue(rollback_success, "Custom rollback handler should succeed")
        
        # Test with failure case
        attempt_id_2 = self.integrity_service.log_data_modification_attempt(
            user_id=123,
            username="testuser",
            attempt_type=DataModificationAttemptType.CAPTION_SETTINGS_UPDATE,
            endpoint="/caption_settings/update",
            method="POST",
            data_preview={"setting": "value"},
            status=DataModificationStatus.ALLOWED
        )
        
        rollback_data_fail = {"success": False, "data": "test"}
        self.integrity_service.create_rollback_checkpoint(attempt_id_2, rollback_data_fail)
        
        rollback_success_2 = self.integrity_service.perform_rollback(attempt_id_2)
        self.assertFalse(rollback_success_2, "Custom rollback handler should fail when success=False")


if __name__ == '__main__':
    unittest.main()