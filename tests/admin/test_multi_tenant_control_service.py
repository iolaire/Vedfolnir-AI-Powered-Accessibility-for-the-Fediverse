# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole, CaptionGenerationTask, TaskStatus, JobPriority, SystemConfiguration, JobAuditLog
from app.services.batch.components.multi_tenant_control_service import MultiTenantControlService, UserJobLimits, RateLimits
from app.services.monitoring.system.system_monitor import ResourceUsage

class TestMultiTenantControlService(unittest.TestCase):
    """Test cases for MultiTenantControlService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = Mock(spec=DatabaseManager)
        self.service = MultiTenantControlService(self.db_manager)
        
        # Mock session context manager
        self.mock_session = Mock()
        self.mock_context_manager = MagicMock()
        self.mock_context_manager.__enter__.return_value = self.mock_session
        self.mock_context_manager.__exit__.return_value = None
        self.db_manager.get_session.return_value = self.mock_context_manager
        
        # Mock admin user
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = "admin"
        self.admin_user.role = UserRole.ADMIN
        
        # Mock regular user
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 2
        self.regular_user.username = "user"
        self.regular_user.role = UserRole.REVIEWER
        
        # Mock target user
        self.target_user = Mock(spec=User)
        self.target_user.id = 3
        self.target_user.username = "target"
        self.target_user.role = UserRole.VIEWER
    
    def test_verify_admin_authorization_success(self):
        """Test successful admin authorization"""
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        result = self.service._verify_admin_authorization(self.mock_session, 1)
        
        self.assertEqual(result, self.admin_user)
        self.mock_session.query.assert_called_with(User)
    
    def test_verify_admin_authorization_user_not_found(self):
        """Test admin authorization with non-existent user"""
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        with self.assertRaises(ValueError) as context:
            self.service._verify_admin_authorization(self.mock_session, 999)
        
        self.assertIn("User 999 not found", str(context.exception))
    
    def test_verify_admin_authorization_not_admin(self):
        """Test admin authorization with non-admin user"""
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        with self.assertRaises(ValueError) as context:
            self.service._verify_admin_authorization(self.mock_session, 2)
        
        self.assertIn("User 2 is not authorized for admin operations", str(context.exception))
    
    def test_log_admin_action(self):
        """Test admin action logging"""
        details = {"action": "test", "value": 123}
        
        self.service._log_admin_action(
            self.mock_session, 1, "test_action", details, 
            target_user_id=2, task_id="task-123"
        )
        
        self.mock_session.add.assert_called_once()
        added_log = self.mock_session.add.call_args[0][0]
        self.assertIsInstance(added_log, JobAuditLog)
        self.assertEqual(added_log.admin_user_id, 1)
        self.assertEqual(added_log.action, "test_action")
        self.assertEqual(added_log.user_id, 2)
        self.assertEqual(added_log.task_id, "task-123")
    
    def test_set_user_job_limits_success(self):
        """Test successful user job limits setting"""
        # Mock admin and target user queries
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            self.target_user,  # Target user verification
            None  # No existing config
        ]
        
        limits = UserJobLimits(max_concurrent_jobs=2, max_jobs_per_hour=20)
        
        result = self.service.set_user_job_limits(1, 3, limits)
        
        self.assertTrue(result)
        self.mock_session.add.assert_called()
        self.mock_session.commit.assert_called_once()
        
        # Verify config entry was added
        added_config = None
        for call in self.mock_session.add.call_args_list:
            if isinstance(call[0][0], SystemConfiguration):
                added_config = call[0][0]
                break
        
        self.assertIsNotNone(added_config)
        self.assertEqual(added_config.key, "user_job_limits_3")
        self.assertEqual(added_config.updated_by, 1)
    
    def test_set_user_job_limits_update_existing(self):
        """Test updating existing user job limits"""
        # Mock existing config
        existing_config = Mock(spec=SystemConfiguration)
        existing_config.key = "user_job_limits_3"
        existing_config.value = UserJobLimits().to_json()
        
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            self.target_user,  # Target user verification
            existing_config  # Existing config
        ]
        
        limits = UserJobLimits(max_concurrent_jobs=3, max_jobs_per_hour=30)
        
        result = self.service.set_user_job_limits(1, 3, limits)
        
        self.assertTrue(result)
        self.assertEqual(existing_config.value, limits.to_json())
        self.assertEqual(existing_config.updated_by, 1)
        self.mock_session.commit.assert_called_once()
    
    def test_set_user_job_limits_target_user_not_found(self):
        """Test setting limits for non-existent target user"""
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            None  # Target user not found
        ]
        
        limits = UserJobLimits()
        
        result = self.service.set_user_job_limits(1, 999, limits)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    def test_set_user_job_limits_unauthorized(self):
        """Test setting limits with unauthorized user"""
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        limits = UserJobLimits()
        
        result = self.service.set_user_job_limits(2, 3, limits)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    def test_pause_system_jobs_success(self):
        """Test successful system jobs pause"""
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            None,  # No existing maintenance config
            None   # No existing reason config
        ]
        
        result = self.service.pause_system_jobs(1, "Scheduled maintenance")
        
        self.assertTrue(result)
        self.mock_session.commit.assert_called_once()
        
        # Verify two config entries were added (maintenance_mode and maintenance_reason)
        self.assertEqual(self.mock_session.add.call_count, 3)  # 2 configs + 1 audit log
    
    def test_pause_system_jobs_update_existing(self):
        """Test pausing jobs with existing maintenance config"""
        existing_maintenance = Mock(spec=SystemConfiguration)
        existing_maintenance.key = "maintenance_mode"
        existing_maintenance.value = "false"
        
        existing_reason = Mock(spec=SystemConfiguration)
        existing_reason.key = "maintenance_reason"
        existing_reason.value = ""
        
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            existing_maintenance,  # Existing maintenance config
            existing_reason  # Existing reason config
        ]
        
        result = self.service.pause_system_jobs(1, "Emergency maintenance")
        
        self.assertTrue(result)
        self.assertEqual(existing_maintenance.value, "true")
        self.assertEqual(existing_reason.value, "Emergency maintenance")
        self.mock_session.commit.assert_called_once()
    
    def test_resume_system_jobs_success(self):
        """Test successful system jobs resume"""
        existing_maintenance = Mock(spec=SystemConfiguration)
        existing_maintenance.key = "maintenance_mode"
        existing_maintenance.value = "true"
        
        existing_reason = Mock(spec=SystemConfiguration)
        existing_reason.key = "maintenance_reason"
        existing_reason.value = "Maintenance in progress"
        
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            existing_maintenance,  # Existing maintenance config
            existing_reason  # Existing reason config
        ]
        
        result = self.service.resume_system_jobs(1)
        
        self.assertTrue(result)
        self.assertEqual(existing_maintenance.value, "false")
        self.assertEqual(existing_reason.value, "")
        self.mock_session.commit.assert_called_once()
    
    def test_set_job_priority_success(self):
        """Test successful job priority setting"""
        # Mock task
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = "task-123"
        mock_task.user_id = 2
        mock_task.priority = JobPriority.NORMAL
        mock_task.admin_notes = None
        
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            mock_task  # Task lookup
        ]
        
        result = self.service.set_job_priority(1, "task-123", JobPriority.HIGH)
        
        self.assertTrue(result)
        self.assertEqual(mock_task.priority, JobPriority.HIGH)
        self.assertIsNotNone(mock_task.admin_notes)
        self.assertIn("Priority changed from normal to high", mock_task.admin_notes)
        self.mock_session.commit.assert_called_once()
    
    def test_set_job_priority_task_not_found(self):
        """Test setting priority for non-existent task"""
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            None  # Task not found
        ]
        
        result = self.service.set_job_priority(1, "nonexistent", JobPriority.HIGH)
        
        self.assertFalse(result)
        self.mock_session.commit.assert_not_called()
    
    @patch('system_monitor.SystemMonitor')
    def test_get_resource_usage_success(self, mock_system_monitor_class):
        """Test successful resource usage retrieval"""
        mock_monitor = Mock()
        mock_system_monitor_class.return_value = mock_monitor
        
        expected_usage = ResourceUsage(
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            memory_total_mb=2048.0,
            disk_percent=30.0,
            disk_used_gb=100.0,
            disk_total_gb=500.0,
            network_io={"bytes_sent": 1000, "bytes_recv": 2000},
            database_connections=5,
            redis_memory_mb=128.0,
            timestamp=datetime.utcnow()
        )
        
        mock_monitor.check_resource_usage.return_value = expected_usage
        
        result = self.service.get_resource_usage()
        
        self.assertEqual(result, expected_usage)
        mock_system_monitor_class.assert_called_once_with(self.db_manager)
        mock_monitor.check_resource_usage.assert_called_once()
    
    @patch('system_monitor.SystemMonitor')
    def test_get_resource_usage_error(self, mock_system_monitor_class):
        """Test resource usage retrieval with error"""
        mock_system_monitor_class.side_effect = Exception("Monitor error")
        
        result = self.service.get_resource_usage()
        
        # Should return default ResourceUsage on error
        self.assertIsInstance(result, ResourceUsage)
        self.assertEqual(result.cpu_percent, 0.0)
        self.assertEqual(result.memory_percent, 0.0)
    
    def test_configure_rate_limits_success(self):
        """Test successful rate limits configuration"""
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin verification
            None  # No existing config
        ]
        
        limits = RateLimits(
            global_max_concurrent_jobs=20,
            max_jobs_per_minute=10,
            max_jobs_per_hour=200
        )
        
        result = self.service.configure_rate_limits(1, limits)
        
        self.assertTrue(result)
        self.mock_session.add.assert_called()
        self.mock_session.commit.assert_called_once()
        
        # Verify config entry was added
        added_config = None
        for call in self.mock_session.add.call_args_list:
            if isinstance(call[0][0], SystemConfiguration):
                added_config = call[0][0]
                break
        
        self.assertIsNotNone(added_config)
        self.assertEqual(added_config.key, "system_rate_limits")
        self.assertEqual(added_config.updated_by, 1)
    
    def test_get_user_job_limits_existing(self):
        """Test getting existing user job limits"""
        limits = UserJobLimits(max_concurrent_jobs=5, max_jobs_per_hour=50)
        
        mock_config = Mock(spec=SystemConfiguration)
        mock_config.key = "user_job_limits_2"
        mock_config.value = limits.to_json()
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_config
        
        result = self.service.get_user_job_limits(2)
        
        self.assertEqual(result.max_concurrent_jobs, 5)
        self.assertEqual(result.max_jobs_per_hour, 50)
    
    def test_get_user_job_limits_default(self):
        """Test getting default user job limits when none exist"""
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.service.get_user_job_limits(2)
        
        # Should return default limits
        self.assertEqual(result.max_concurrent_jobs, 1)
        self.assertEqual(result.max_jobs_per_hour, 10)
    
    def test_get_system_rate_limits_existing(self):
        """Test getting existing system rate limits"""
        limits = RateLimits(global_max_concurrent_jobs=15, max_jobs_per_minute=8)
        
        mock_config = Mock(spec=SystemConfiguration)
        mock_config.key = "system_rate_limits"
        mock_config.value = limits.to_json()
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_config
        
        result = self.service.get_system_rate_limits()
        
        self.assertEqual(result.global_max_concurrent_jobs, 15)
        self.assertEqual(result.max_jobs_per_minute, 8)
    
    def test_get_system_rate_limits_default(self):
        """Test getting default system rate limits when none exist"""
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.service.get_system_rate_limits()
        
        # Should return default limits
        self.assertEqual(result.global_max_concurrent_jobs, 10)
        self.assertEqual(result.max_jobs_per_minute, 5)
    
    def test_is_maintenance_mode_true(self):
        """Test maintenance mode check when enabled"""
        mock_config = Mock(spec=SystemConfiguration)
        mock_config.key = "maintenance_mode"
        mock_config.value = "true"
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_config
        
        result = self.service.is_maintenance_mode()
        
        self.assertTrue(result)
    
    def test_is_maintenance_mode_false(self):
        """Test maintenance mode check when disabled"""
        mock_config = Mock(spec=SystemConfiguration)
        mock_config.key = "maintenance_mode"
        mock_config.value = "false"
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_config
        
        result = self.service.is_maintenance_mode()
        
        self.assertFalse(result)
    
    def test_is_maintenance_mode_no_config(self):
        """Test maintenance mode check when no config exists"""
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.service.is_maintenance_mode()
        
        self.assertFalse(result)
    
    def test_get_maintenance_reason_exists(self):
        """Test getting maintenance reason when it exists"""
        mock_config = Mock(spec=SystemConfiguration)
        mock_config.key = "maintenance_reason"
        mock_config.value = "Database upgrade in progress"
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_config
        
        result = self.service.get_maintenance_reason()
        
        self.assertEqual(result, "Database upgrade in progress")
    
    def test_get_maintenance_reason_none(self):
        """Test getting maintenance reason when none exists"""
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.service.get_maintenance_reason()
        
        self.assertIsNone(result)

class TestUserJobLimits(unittest.TestCase):
    """Test cases for UserJobLimits data class"""
    
    def test_to_dict(self):
        """Test UserJobLimits to_dict conversion"""
        limits = UserJobLimits(
            max_concurrent_jobs=2,
            max_jobs_per_hour=20,
            priority_override=JobPriority.HIGH
        )
        
        result = limits.to_dict()
        
        self.assertEqual(result['max_concurrent_jobs'], 2)
        self.assertEqual(result['max_jobs_per_hour'], 20)
        self.assertEqual(result['priority_override'], 'high')
    
    def test_from_dict(self):
        """Test UserJobLimits from_dict creation"""
        data = {
            'max_concurrent_jobs': 3,
            'max_jobs_per_hour': 30,
            'priority_override': 'urgent'
        }
        
        limits = UserJobLimits.from_dict(data)
        
        self.assertEqual(limits.max_concurrent_jobs, 3)
        self.assertEqual(limits.max_jobs_per_hour, 30)
        self.assertEqual(limits.priority_override, JobPriority.URGENT)
    
    def test_json_serialization(self):
        """Test UserJobLimits JSON serialization and deserialization"""
        original = UserJobLimits(
            max_concurrent_jobs=4,
            max_jobs_per_day=100,
            enabled=False
        )
        
        json_str = original.to_json()
        restored = UserJobLimits.from_json(json_str)
        
        self.assertEqual(restored.max_concurrent_jobs, 4)
        self.assertEqual(restored.max_jobs_per_day, 100)
        self.assertEqual(restored.enabled, False)

class TestRateLimits(unittest.TestCase):
    """Test cases for RateLimits data class"""
    
    def test_to_dict_with_user_limits(self):
        """Test RateLimits to_dict conversion with user limits"""
        user_limits = UserJobLimits(max_concurrent_jobs=2)
        limits = RateLimits(
            global_max_concurrent_jobs=15,
            user_rate_limits={1: user_limits}
        )
        
        result = limits.to_dict()
        
        self.assertEqual(result['global_max_concurrent_jobs'], 15)
        self.assertIn('user_rate_limits', result)
        self.assertIn('1', result['user_rate_limits'])
        self.assertEqual(result['user_rate_limits']['1']['max_concurrent_jobs'], 2)
    
    def test_from_dict_with_user_limits(self):
        """Test RateLimits from_dict creation with user limits"""
        data = {
            'global_max_concurrent_jobs': 20,
            'user_rate_limits': {
                '2': {'max_concurrent_jobs': 3, 'max_jobs_per_hour': 30}
            }
        }
        
        limits = RateLimits.from_dict(data)
        
        self.assertEqual(limits.global_max_concurrent_jobs, 20)
        self.assertIn(2, limits.user_rate_limits)
        self.assertEqual(limits.user_rate_limits[2].max_concurrent_jobs, 3)
    
    def test_json_serialization(self):
        """Test RateLimits JSON serialization and deserialization"""
        user_limits = UserJobLimits(max_concurrent_jobs=5)
        original = RateLimits(
            max_jobs_per_minute=8,
            user_rate_limits={3: user_limits}
        )
        
        json_str = original.to_json()
        restored = RateLimits.from_json(json_str)
        
        self.assertEqual(restored.max_jobs_per_minute, 8)
        self.assertIn(3, restored.user_rate_limits)
        self.assertEqual(restored.user_rate_limits[3].max_concurrent_jobs, 5)

if __name__ == '__main__':
    unittest.main()