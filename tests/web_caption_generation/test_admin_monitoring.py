# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for administrative monitoring and controls
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import uuid
from datetime import datetime, timezone, timedelta

from admin_monitoring import AdminMonitoringService
from models import (
    User, UserRole, CaptionGenerationTask, TaskStatus, 
    PlatformConnection, CaptionGenerationUserSettings
)
from app.core.database.core.database_manager import DatabaseManager

class TestAdminMonitoring(unittest.TestCase):
    """Tests for administrative monitoring and controls"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.admin_service = AdminMonitoringService(self.mock_db_manager)
        
        # Test data
        self.test_admin_id = 1
        self.test_user_id = 2
        self.test_task_id = str(uuid.uuid4())
        
        # Mock admin user
        self.mock_admin = Mock(spec=User)
        self.mock_admin.id = self.test_admin_id
        self.mock_admin.role = UserRole.ADMIN
        self.mock_admin.is_active = True
    
    def test_get_system_overview(self):
        """Test system overview retrieval"""
        # Mock database queries
        self.mock_session.query.return_value.count.side_effect = [
            5,   # total_users
            3,   # active_users
            10,  # total_platforms
            8,   # active_platforms
            25,  # total_tasks
            2,   # active_tasks
            20,  # completed_tasks
            3    # failed_tasks
        ]
        
        overview = self.admin_service.get_system_overview()
        
        # Verify overview structure
        self.assertIn('users', overview)
        self.assertIn('platforms', overview)
        self.assertIn('tasks', overview)
        self.assertIn('system_health', overview)
        
        # Verify user stats
        self.assertEqual(overview['users']['total'], 5)
        self.assertEqual(overview['users']['active'], 3)
        
        # Verify platform stats
        self.assertEqual(overview['platforms']['total'], 10)
        self.assertEqual(overview['platforms']['active'], 8)
        
        # Verify task stats
        self.assertEqual(overview['tasks']['total'], 25)
        self.assertEqual(overview['tasks']['active'], 2)
        self.assertEqual(overview['tasks']['completed'], 20)
        self.assertEqual(overview['tasks']['failed'], 3)
    
    @patch('admin_monitoring.psutil')
    def test_get_resource_monitoring(self, mock_psutil):
        """Test resource monitoring data retrieval"""
        # Mock system resource data
        mock_psutil.cpu_percent.return_value = 45.2
        mock_psutil.virtual_memory.return_value.percent = 67.8
        mock_psutil.disk_usage.return_value.percent = 23.4
        
        # Mock database size
        with patch('os.path.getsize', return_value=1024*1024*50):  # 50MB
            resources = self.admin_service.get_resource_monitoring()
        
        # Verify resource data
        self.assertIn('cpu_usage', resources)
        self.assertIn('memory_usage', resources)
        self.assertIn('disk_usage', resources)
        self.assertIn('database_size', resources)
        
        self.assertEqual(resources['cpu_usage'], 45.2)
        self.assertEqual(resources['memory_usage'], 67.8)
        self.assertEqual(resources['disk_usage'], 23.4)
        self.assertGreater(resources['database_size'], 0)
    
    def test_get_active_tasks(self):
        """Test active tasks retrieval"""
        # Mock active tasks
        mock_tasks = []
        for i in range(3):
            mock_task = Mock(spec=CaptionGenerationTask)
            mock_task.id = f"task-{i}"
            mock_task.user_id = i + 1
            mock_task.status = TaskStatus.RUNNING
            mock_task.created_at = datetime.now(timezone.utc)
            mock_task.progress_percent = 50 + i * 10
            mock_task.current_step = f"Step {i}"
            
            # Mock user relationship
            mock_user = Mock(spec=User)
            mock_user.username = f"user{i}"
            mock_task.user = mock_user
            
            # Mock platform relationship
            mock_platform = Mock(spec=PlatformConnection)
            mock_platform.name = f"Platform {i}"
            mock_task.platform_connection = mock_platform
            
            mock_tasks.append(mock_task)
        
        query_mock = self.mock_session.query.return_value
        query_mock.filter.return_value.options.return_value.all.return_value = mock_tasks
        
        active_tasks = self.admin_service.get_active_tasks()
        
        # Verify active tasks structure
        self.assertEqual(len(active_tasks), 3)
        for i, task in enumerate(active_tasks):
            self.assertEqual(task['task_id'], f"task-{i}")
            self.assertEqual(task['username'], f"user{i}")
            self.assertEqual(task['platform_name'], f"Platform {i}")
            self.assertEqual(task['status'], TaskStatus.RUNNING.value)
            self.assertEqual(task['progress_percent'], 50 + i * 10)
    
    def test_cancel_task_as_admin(self):
        """Test admin task cancellation"""
        # Mock task
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = self.test_task_id
        mock_task.status = TaskStatus.RUNNING
        mock_task.can_be_cancelled.return_value = True
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        result = self.admin_service.cancel_task(self.test_task_id, self.test_admin_id)
        
        # Verify cancellation
        self.assertTrue(result)
        self.assertEqual(mock_task.status, TaskStatus.CANCELLED)
        self.assertIsNotNone(mock_task.completed_at)
        self.mock_session.commit.assert_called_once()
    
    def test_cancel_task_unauthorized(self):
        """Test task cancellation by non-admin user"""
        # Mock non-admin user
        mock_user = Mock(spec=User)
        mock_user.role = UserRole.USER
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        result = self.admin_service.cancel_task(self.test_task_id, self.test_user_id)
        
        # Verify cancellation was denied
        self.assertFalse(result)
    
    def test_get_performance_metrics(self):
        """Test performance metrics retrieval"""
        # Mock task completion times
        now = datetime.now(timezone.utc)
        mock_tasks = []
        for i in range(5):
            mock_task = Mock(spec=CaptionGenerationTask)
            mock_task.created_at = now - timedelta(minutes=30)
            mock_task.completed_at = now - timedelta(minutes=10)
            mock_task.status = TaskStatus.COMPLETED
            mock_tasks.append(mock_task)
        
        # Mock database queries
        query_mock = self.mock_session.query.return_value
        query_mock.filter.return_value.all.return_value = mock_tasks
        
        # Mock count queries
        self.mock_session.query.return_value.filter.return_value.count.side_effect = [
            10,  # tasks_last_24h
            50,  # tasks_last_week
            5,   # failed_tasks_last_24h
            2    # cancelled_tasks_last_24h
        ]
        
        metrics = self.admin_service.get_performance_metrics()
        
        # Verify metrics structure
        self.assertIn('tasks_last_24h', metrics)
        self.assertIn('tasks_last_week', metrics)
        self.assertIn('average_completion_time', metrics)
        self.assertIn('success_rate_24h', metrics)
        self.assertIn('failed_tasks_last_24h', metrics)
        
        # Verify calculated values
        self.assertEqual(metrics['tasks_last_24h'], 10)
        self.assertEqual(metrics['tasks_last_week'], 50)
        self.assertGreater(metrics['average_completion_time'], 0)
    
    def test_get_user_activity(self):
        """Test user activity tracking"""
        # Mock user activity data
        mock_users = []
        for i in range(3):
            mock_user = Mock(spec=User)
            mock_user.id = i + 1
            mock_user.username = f"user{i}"
            mock_user.last_login = datetime.now(timezone.utc) - timedelta(hours=i)
            mock_users.append(mock_user)
        
        self.mock_session.query.return_value.all.return_value = mock_users
        
        # Mock task counts per user
        self.mock_session.query.return_value.filter.return_value.count.side_effect = [
            5, 3, 1  # Task counts for each user
        ]
        
        activity = self.admin_service.get_user_activity()
        
        # Verify activity structure
        self.assertEqual(len(activity), 3)
        for i, user_activity in enumerate(activity):
            self.assertEqual(user_activity['user_id'], i + 1)
            self.assertEqual(user_activity['username'], f"user{i}")
            self.assertIn('last_login', user_activity)
            self.assertIn('tasks_last_24h', user_activity)
    
    def test_cleanup_old_tasks(self):
        """Test cleanup of old tasks"""
        # Mock old tasks
        old_tasks = [Mock(), Mock(), Mock()]
        query_mock = self.mock_session.query.return_value
        query_mock.filter.return_value.all.return_value = old_tasks
        
        result = self.admin_service.cleanup_old_tasks(days_old=30)
        
        # Verify cleanup
        self.assertEqual(result, 3)
        for task in old_tasks:
            self.mock_session.delete.assert_any_call(task)
        self.mock_session.commit.assert_called_once()
    
    def test_get_system_configuration(self):
        """Test system configuration retrieval"""
        # Mock configuration settings
        mock_settings = []
        for i in range(3):
            mock_setting = Mock(spec=CaptionGenerationUserSettings)
            mock_setting.user_id = i + 1
            mock_setting.max_posts_per_run = 25 + i * 5
            mock_setting.caption_max_length = 400 + i * 50
            mock_settings.append(mock_setting)
        
        self.mock_session.query.return_value.all.return_value = mock_settings
        
        config = self.admin_service.get_system_configuration()
        
        # Verify configuration structure
        self.assertIn('user_settings_count', config)
        self.assertIn('default_settings', config)
        self.assertIn('system_limits', config)
        
        self.assertEqual(config['user_settings_count'], 3)
        self.assertIn('max_posts_per_run', config['default_settings'])
    
    def test_update_system_limits(self):
        """Test system limits update"""
        new_limits = {
            'max_concurrent_tasks': 5,
            'max_posts_per_run': 100,
            'task_timeout_minutes': 60
        }
        
        result = self.admin_service.update_system_limits(new_limits, self.test_admin_id)
        
        # Verify update was successful
        self.assertTrue(result)
    
    def test_get_error_statistics(self):
        """Test error statistics retrieval"""
        # Mock failed tasks with error messages
        mock_failed_tasks = []
        error_types = ["Authentication failed", "Rate limit exceeded", "Connection timeout"]
        
        for i, error_type in enumerate(error_types):
            mock_task = Mock(spec=CaptionGenerationTask)
            mock_task.error_message = error_type
            mock_task.completed_at = datetime.now(timezone.utc) - timedelta(hours=i)
            mock_failed_tasks.append(mock_task)
        
        query_mock = self.mock_session.query.return_value
        query_mock.filter.return_value.all.return_value = mock_failed_tasks
        
        error_stats = self.admin_service.get_error_statistics()
        
        # Verify error statistics structure
        self.assertIn('total_errors', error_stats)
        self.assertIn('error_categories', error_stats)
        self.assertIn('recent_errors', error_stats)
        
        self.assertEqual(error_stats['total_errors'], 3)
        self.assertGreater(len(error_stats['error_categories']), 0)
    
    def test_generate_admin_report(self):
        """Test comprehensive admin report generation"""
        # Mock all required data
        self.mock_session.query.return_value.count.side_effect = [
            10, 8, 20, 15, 50, 5, 40, 5  # Various counts for overview
        ]
        
        with patch.object(self.admin_service, 'get_resource_monitoring') as mock_resources:
            mock_resources.return_value = {
                'cpu_usage': 45.0,
                'memory_usage': 60.0,
                'disk_usage': 30.0,
                'database_size': 1024*1024*100
            }
            
            with patch.object(self.admin_service, 'get_performance_metrics') as mock_metrics:
                mock_metrics.return_value = {
                    'tasks_last_24h': 15,
                    'average_completion_time': 300,
                    'success_rate_24h': 85.0
                }
                
                report = self.admin_service.generate_admin_report()
        
        # Verify report structure
        self.assertIn('generated_at', report)
        self.assertIn('system_overview', report)
        self.assertIn('resource_monitoring', report)
        self.assertIn('performance_metrics', report)
        self.assertIn('recommendations', report)
        
        # Verify recommendations are generated
        self.assertIsInstance(report['recommendations'], list)
    
    def test_authorization_check(self):
        """Test admin authorization checking"""
        # Test admin user
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_admin
        
        result = self.admin_service._is_admin(self.test_admin_id)
        self.assertTrue(result)
        
        # Test non-admin user
        mock_user = Mock(spec=User)
        mock_user.role = UserRole.USER
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        result = self.admin_service._is_admin(self.test_user_id)
        self.assertFalse(result)
        
        # Test non-existent user
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.admin_service._is_admin(999)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()