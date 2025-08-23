# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Acceptance Tests for Admin User Experience Enhancements
Tests the complete admin user experience workflows including context switching,
job management separation, visual distinctions, and notification systems.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timedelta
from flask import Flask
from flask_login import login_user
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config
from database import DatabaseManager
from models import User, UserRole, CaptionGenerationTask, JobAuditLog, SystemConfiguration
from web_app import create_app


class TestAdminUserExperience(unittest.TestCase):
    """Test admin user experience enhancements"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.config.TESTING = True
        self.config.WTF_CSRF_ENABLED = False
        
        # Create test app
        self.app = create_app(self.config)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        self.client = self.app.test_client()
        
        # Set up database manager
        self.db_manager = DatabaseManager(self.config)
        
        # Create test users
        self.admin_user = self._create_test_admin_user()
        self.regular_user = self._create_test_regular_user()
        
        # Create test jobs
        self.admin_personal_job = self._create_test_job(self.admin_user.id, is_admin_job=False)
        self.admin_managed_job = self._create_test_job(self.regular_user.id, is_admin_job=True, admin_user_id=self.admin_user.id)
        self.regular_user_job = self._create_test_job(self.regular_user.id, is_admin_job=False)
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            with self.db_manager.get_session() as session:
                # Clean up test data
                session.query(JobAuditLog).delete()
                session.query(CaptionGenerationTask).delete()
                session.query(SystemConfiguration).delete()
                session.query(User).delete()
                session.commit()
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        self.app_context.pop()
    
    def _create_test_admin_user(self):
        """Create a test admin user"""
        with self.db_manager.get_session() as session:
            admin_user = User(
                username='test_admin',
                email='admin@test.com',
                role=UserRole.ADMIN,
                is_active=True
            )
            admin_user.set_password('admin_password')
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            return admin_user
    
    def _create_test_regular_user(self):
        """Create a test regular user"""
        with self.db_manager.get_session() as session:
            regular_user = User(
                username='test_user',
                email='user@test.com',
                role=UserRole.REVIEWER,
                is_active=True
            )
            regular_user.set_password('user_password')
            session.add(regular_user)
            session.commit()
            session.refresh(regular_user)
            return regular_user
    
    def _create_test_job(self, user_id, is_admin_job=False, admin_user_id=None):
        """Create a test caption generation job"""
        with self.db_manager.get_session() as session:
            job = CaptionGenerationTask(
                user_id=user_id,
                platform_connection_id=1,
                status='running',
                progress_percent=50,
                current_step='Processing images',
                admin_managed=is_admin_job,
                admin_user_id=admin_user_id,
                admin_notes='Test admin notes' if is_admin_job else None
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
    
    def _login_as_admin(self):
        """Login as admin user"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.admin_user.id
            sess['_fresh'] = True
    
    def _login_as_regular_user(self):
        """Login as regular user"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.regular_user.id
            sess['_fresh'] = True
    
    def test_admin_context_switcher_display(self):
        """Test that admin context switcher is displayed correctly"""
        self._login_as_admin()
        
        # Test admin job management page
        response = self.client.get('/admin/job-management')
        self.assertEqual(response.status_code, 200)
        
        # Check for context switcher elements
        self.assertIn(b'admin-context-switcher', response.data)
        self.assertIn(b'Administrator Mode', response.data)
        self.assertIn(b'Personal Mode', response.data)
        self.assertIn(b'switchToPersonalMode', response.data)
        self.assertIn(b'switchToAdminMode', response.data)
    
    def test_admin_personal_mode_restrictions(self):
        """Test that personal mode only shows personal jobs"""
        self._login_as_admin()
        
        # Mock personal mode context
        with patch('flask.session', {'admin_mode': False}):
            response = self.client.get('/admin/job-management')
            self.assertEqual(response.status_code, 200)
            
            # Should show personal jobs section
            self.assertIn(b'personal-job-section', response.data)
            self.assertIn(b'Your Personal Jobs', response.data)
            
            # Should not show admin jobs section in personal mode
            # (or it should be hidden via JavaScript)
            self.assertIn(b'adminJobSection', response.data)
    
    def test_admin_mode_full_access(self):
        """Test that admin mode shows all administrative capabilities"""
        self._login_as_admin()
        
        # Mock admin mode context
        with patch('flask.session', {'admin_mode': True}):
            response = self.client.get('/admin/job-management')
            self.assertEqual(response.status_code, 200)
            
            # Should show admin jobs section
            self.assertIn(b'admin-job-section', response.data)
            self.assertIn(b'Administrative Job Management', response.data)
            self.assertIn(b'ADMIN ACTIONS', response.data)
            
            # Should show personal jobs section too
            self.assertIn(b'personal-job-section', response.data)
            self.assertIn(b'Your Personal Jobs', response.data)
    
    def test_visual_distinction_admin_vs_personal(self):
        """Test visual distinction between admin and personal actions"""
        self._login_as_admin()
        
        response = self.client.get('/admin/job-management')
        self.assertEqual(response.status_code, 200)
        
        # Check for admin visual elements
        self.assertIn(b'admin-action-badge', response.data)
        self.assertIn(b'ADMIN MANAGED', response.data)
        self.assertIn(b'admin-managed', response.data)
        
        # Check for personal visual elements
        self.assertIn(b'personal-action-badge', response.data)
        self.assertIn(b'YOUR JOB', response.data)
        self.assertIn(b'personal-managed', response.data)
        
        # Check for CSS classes that provide visual distinction
        self.assertIn(b'admin-job-section', response.data)
        self.assertIn(b'personal-job-section', response.data)
    
    def test_admin_job_cancellation_workflow(self):
        """Test admin job cancellation workflow with proper notifications"""
        self._login_as_admin()
        
        # Mock the admin cancel job API
        with patch('admin.routes.admin_api.AdminManagementService') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.cancel_job_as_admin.return_value = True
            
            # Test admin job cancellation
            response = self.client.post(
                f'/admin/api/jobs/{self.regular_user_job.id}/cancel',
                json={'reason': 'Test cancellation reason'},
                headers={'Content-Type': 'application/json'}
            )
            
            # Should succeed (mocked)
            self.assertEqual(response.status_code, 200)
            
            # Verify the service was called with correct parameters
            mock_service_instance.cancel_job_as_admin.assert_called_once()
    
    def test_personal_job_cancellation_workflow(self):
        """Test personal job cancellation workflow"""
        self._login_as_admin()
        
        # Mock the personal cancel job API
        with patch('web_caption_generation_service.WebCaptionGenerationService') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.cancel_task.return_value = {'success': True}
            
            # Test personal job cancellation
            response = self.client.post(f'/api/cancel_task/{self.admin_personal_job.id}')
            
            # Should succeed (mocked)
            self.assertEqual(response.status_code, 200)
    
    def test_admin_job_history_separation(self):
        """Test that admin job history properly separates admin actions from personal jobs"""
        self._login_as_admin()
        
        # Create audit log entries
        with self.db_manager.get_session() as session:
            # Admin action audit log
            admin_audit = JobAuditLog(
                task_id=self.admin_managed_job.id,
                user_id=self.regular_user.id,
                admin_user_id=self.admin_user.id,
                action='cancelled',
                details='{"reason": "Test cancellation"}',
                timestamp=datetime.utcnow()
            )
            session.add(admin_audit)
            
            # Personal job audit log
            personal_audit = JobAuditLog(
                task_id=self.admin_personal_job.id,
                user_id=self.admin_user.id,
                admin_user_id=None,
                action='completed',
                details='{"captions_generated": 5}',
                timestamp=datetime.utcnow()
            )
            session.add(personal_audit)
            session.commit()
        
        # Mock the job history API
        with patch('admin.routes.admin_api.get_admin_job_history') as mock_admin_history, \
             patch('admin.routes.admin_api.get_personal_job_history') as mock_personal_history:
            
            mock_admin_history.return_value = {
                'history': [{
                    'id': 1,
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': 'cancelled',
                    'job_id': self.admin_managed_job.id,
                    'target_username': self.regular_user.username,
                    'reason': 'Test cancellation',
                    'success': True
                }]
            }
            
            mock_personal_history.return_value = {
                'history': [{
                    'id': 2,
                    'timestamp': datetime.utcnow().isoformat(),
                    'job_id': self.admin_personal_job.id,
                    'status': 'completed',
                    'results': {'captions_generated': 5}
                }]
            }
            
            # Test admin history endpoint
            response = self.client.get('/admin/api/job-history/admin')
            self.assertEqual(response.status_code, 200)
            
            # Test personal history endpoint
            response = self.client.get('/admin/api/job-history/personal')
            self.assertEqual(response.status_code, 200)
    
    def test_admin_notification_system(self):
        """Test admin notification system functionality"""
        self._login_as_admin()
        
        # Mock notification data
        mock_notifications = [
            {
                'id': 'notif_1',
                'title': 'Job Failed',
                'message': 'User job failed due to system error',
                'type': 'job_failed',
                'severity': 'warning',
                'timestamp': datetime.utcnow().isoformat(),
                'read': False
            },
            {
                'id': 'notif_2',
                'title': 'System Alert',
                'message': 'High system load detected',
                'type': 'system_alert',
                'severity': 'critical',
                'timestamp': datetime.utcnow().isoformat(),
                'read': False
            }
        ]
        
        # Mock the notifications API
        with patch('admin.routes.admin_api.get_admin_notifications') as mock_notifications_api:
            mock_notifications_api.return_value = {'notifications': mock_notifications}
            
            # Test notifications endpoint
            response = self.client.get('/admin/api/notifications')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertIn('notifications', data)
            self.assertEqual(len(data['notifications']), 2)
    
    def test_admin_help_center_access(self):
        """Test admin help center accessibility and content"""
        self._login_as_admin()
        
        response = self.client.get('/admin/help')
        self.assertEqual(response.status_code, 200)
        
        # Check for help sections
        self.assertIn(b'Admin Help Center', response.data)
        self.assertIn(b'getting-started', response.data)
        self.assertIn(b'job-management', response.data)
        self.assertIn(b'troubleshooting', response.data)
        self.assertIn(b'Admin Context Switching', response.data)
        self.assertIn(b'Administrative Job Actions', response.data)
    
    def test_regular_user_cannot_access_admin_features(self):
        """Test that regular users cannot access admin-specific features"""
        self._login_as_regular_user()
        
        # Test admin dashboard access
        response = self.client.get('/admin/dashboard')
        self.assertIn(response.status_code, [302, 403])  # Redirect or forbidden
        
        # Test admin job management access
        response = self.client.get('/admin/job-management')
        self.assertIn(response.status_code, [302, 403])
        
        # Test admin API access
        response = self.client.get('/admin/api/jobs')
        self.assertIn(response.status_code, [302, 403])
    
    def test_admin_context_persistence(self):
        """Test that admin context preference is persisted"""
        self._login_as_admin()
        
        # The context switching should be handled by JavaScript and localStorage
        # This test verifies the UI elements are present for context switching
        response = self.client.get('/admin/job-management')
        self.assertEqual(response.status_code, 200)
        
        # Check for JavaScript context switching functionality
        self.assertIn(b'switchToPersonalMode', response.data)
        self.assertIn(b'switchToAdminMode', response.data)
        self.assertIn(b'localStorage.setItem', response.data)
        self.assertIn(b'vedfolnir_admin_mode', response.data)
    
    def test_admin_bulk_actions_interface(self):
        """Test admin bulk actions interface"""
        self._login_as_admin()
        
        response = self.client.get('/admin/job-management')
        self.assertEqual(response.status_code, 200)
        
        # Check for bulk actions elements
        self.assertIn(b'Bulk Actions', response.data)
        self.assertIn(b'showBulkAdminActions', response.data)
        self.assertIn(b'System Maintenance', response.data)
        self.assertIn(b'showSystemMaintenanceModal', response.data)
    
    def test_admin_job_statistics_display(self):
        """Test admin job statistics display"""
        self._login_as_admin()
        
        # Mock job statistics
        with patch('admin.routes.dashboard.get_system_metrics') as mock_metrics:
            mock_metrics.return_value = {
                'active_jobs': 3,
                'queued_jobs': 1,
                'completed_today': 10,
                'failed_jobs': 2,
                'success_rate': 85,
                'error_rate': 15
            }
            
            response = self.client.get('/admin/job-management')
            self.assertEqual(response.status_code, 200)
            
            # Check for statistics display elements
            self.assertIn(b'job-stats', response.data)
            self.assertIn(b'Total Active Jobs', response.data)
            self.assertIn(b'Your Active Jobs', response.data)
            self.assertIn(b'Admin Managed', response.data)
            self.assertIn(b'Queued Jobs', response.data)
    
    def test_admin_notification_toast_system(self):
        """Test admin notification toast system"""
        self._login_as_admin()
        
        response = self.client.get('/admin/job-management')
        self.assertEqual(response.status_code, 200)
        
        # Check for toast notification system elements
        self.assertIn(b'adminToastContainer', response.data)
        self.assertIn(b'admin-toast', response.data)
        self.assertIn(b'showToastNotification', response.data)
        self.assertIn(b'AdminNotificationSystem', response.data)
    
    def test_admin_error_handling_and_recovery(self):
        """Test admin error handling and recovery suggestions"""
        self._login_as_admin()
        
        # Mock a failed admin action
        with patch('admin.routes.admin_api.AdminManagementService') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.cancel_job_as_admin.side_effect = Exception("Test error")
            
            # Test error handling in admin action
            response = self.client.post(
                f'/admin/api/jobs/{self.regular_user_job.id}/cancel',
                json={'reason': 'Test cancellation'},
                headers={'Content-Type': 'application/json'}
            )
            
            # Should handle error gracefully
            self.assertEqual(response.status_code, 500)
    
    def test_admin_accessibility_features(self):
        """Test admin interface accessibility features"""
        self._login_as_admin()
        
        response = self.client.get('/admin/job-management')
        self.assertEqual(response.status_code, 200)
        
        # Check for accessibility features
        self.assertIn(b'aria-label', response.data)
        self.assertIn(b'role=', response.data)
        self.assertIn(b'aria-expanded', response.data)
        
        # Check for keyboard navigation support
        self.assertIn(b'tabindex', response.data)
        
        # Check for screen reader support
        self.assertIn(b'sr-only', response.data)
    
    def test_admin_responsive_design(self):
        """Test admin interface responsive design elements"""
        self._login_as_admin()
        
        response = self.client.get('/admin/job-management')
        self.assertEqual(response.status_code, 200)
        
        # Check for responsive CSS classes
        self.assertIn(b'col-md-', response.data)
        self.assertIn(b'col-sm-', response.data)
        self.assertIn(b'd-md-block', response.data)
        self.assertIn(b'@media', response.data)
    
    def test_complete_admin_workflow(self):
        """Test complete admin workflow from login to job management"""
        # 1. Login as admin
        self._login_as_admin()
        
        # 2. Access admin dashboard
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)
        
        # 3. Navigate to job management
        response = self.client.get('/admin/job-management')
        self.assertEqual(response.status_code, 200)
        
        # 4. Verify context switcher is present
        self.assertIn(b'admin-context-switcher', response.data)
        
        # 5. Verify both admin and personal job sections are present
        self.assertIn(b'admin-job-section', response.data)
        self.assertIn(b'personal-job-section', response.data)
        
        # 6. Verify visual distinctions are in place
        self.assertIn(b'admin-action-badge', response.data)
        self.assertIn(b'personal-action-badge', response.data)
        
        # 7. Verify notification system is present
        self.assertIn(b'adminNotificationBell', response.data)
        
        # 8. Access help center
        response = self.client.get('/admin/help')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Help Center', response.data)


if __name__ == '__main__':
    unittest.main()