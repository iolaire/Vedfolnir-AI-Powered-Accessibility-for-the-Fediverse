# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for StorageEmailNotificationService.

Tests email formatting, rate limiting logic, admin email retrieval,
and integration with the existing email infrastructure.
"""

import unittest
import asyncio
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.storage.components.storage_email_notification_service import StorageEmailNotificationService
from app.services.storage.components.storage_monitor_service import StorageMetrics
from models import User, UserRole
from services.email_service import EmailService


class TestStorageEmailNotificationService(unittest.TestCase):
    """Test StorageEmailNotificationService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock components
        self.mock_email_service = Mock(spec=EmailService)
        self.mock_db_manager = Mock()
        self.mock_redis_client = Mock()
        self.mock_app = Mock()
        
        # Configure mock app
        self.mock_app.config = {'BASE_URL': 'https://test.example.com'}
        
        # Create service instance
        self.service = StorageEmailNotificationService(
            email_service=self.mock_email_service,
            db_manager=self.mock_db_manager,
            redis_client=self.mock_redis_client,
            app=self.mock_app
        )
        
        # Create test storage metrics
        self.test_metrics = StorageMetrics(
            total_bytes=8589934592,  # 8GB in bytes
            total_gb=8.0,
            limit_gb=10.0,
            usage_percentage=80.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime(2025, 1, 15, 12, 30, 45)
        )
        
        # Create test admin users
        self.test_admin_users = [
            Mock(spec=User, email='admin1@example.com', role=UserRole.ADMIN, is_active=True, email_verified=True),
            Mock(spec=User, email='admin2@example.com', role=UserRole.ADMIN, is_active=True, email_verified=True),
            Mock(spec=User, email='admin3@example.com', role=UserRole.ADMIN, is_active=True, email_verified=True)
        ]
    
    def test_initialization_with_all_components(self):
        """Test service initialization with all components provided"""
        service = StorageEmailNotificationService(
            email_service=self.mock_email_service,
            db_manager=self.mock_db_manager,
            redis_client=self.mock_redis_client,
            app=self.mock_app
        )
        
        self.assertEqual(service.email_service, self.mock_email_service)
        self.assertEqual(service.db_manager, self.mock_db_manager)
        self.assertEqual(service.redis_client, self.mock_redis_client)
        self.assertEqual(service.app, self.mock_app)
    
    def test_initialization_without_components(self):
        """Test service initialization without components (auto-initialization)"""
        # Test that service can be created without explicit components
        # (auto-initialization will be tested in integration tests)
        service = StorageEmailNotificationService()
        
        # Verify service was created
        self.assertIsNotNone(service)
        
        # Components may or may not be initialized depending on environment
        # This is acceptable for unit tests
    
    def test_get_admin_email_list_success(self):
        """Test successful retrieval of admin email addresses"""
        # Configure mock database session context manager
        mock_session = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context_manager
        mock_session.query.return_value.filter.return_value.all.return_value = self.test_admin_users
        
        # Test method
        admin_emails = self.service.get_admin_email_list()
        
        # Verify results
        expected_emails = ['admin1@example.com', 'admin2@example.com', 'admin3@example.com']
        self.assertEqual(admin_emails, expected_emails)
        
        # Verify database query
        mock_session.query.assert_called_once_with(User)
        self.assertTrue(mock_session.query.return_value.filter.called)
    
    def test_get_admin_email_list_no_admins(self):
        """Test admin email retrieval when no admin users exist"""
        # Configure mock database session context manager
        mock_session = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context_manager
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        # Test method
        admin_emails = self.service.get_admin_email_list()
        
        # Verify empty result
        self.assertEqual(admin_emails, [])
    
    def test_get_admin_email_list_database_error(self):
        """Test admin email retrieval with database error"""
        # Configure mock to raise exception
        self.mock_db_manager.get_session.side_effect = Exception("Database connection failed")
        
        # Test method
        admin_emails = self.service.get_admin_email_list()
        
        # Verify empty result on error
        self.assertEqual(admin_emails, [])
    
    @patch('config.Config')
    @patch('database.DatabaseManager')
    def test_get_admin_email_list_no_database_manager(self, mock_db_class, mock_config_class):
        """Test admin email retrieval without database manager"""
        # Mock the auto-initialization to fail for database manager
        mock_config_class.side_effect = Exception("Config failed")
        
        # Create service without database manager
        service = StorageEmailNotificationService(
            email_service=self.mock_email_service,
            db_manager=None,
            redis_client=self.mock_redis_client,
            app=self.mock_app
        )
        
        # Test method
        admin_emails = service.get_admin_email_list()
        
        # Verify empty result
        self.assertEqual(admin_emails, [])
    
    def test_should_send_notification_no_previous_notification(self):
        """Test rate limiting when no previous notification exists"""
        # Configure Redis to return None (no previous notification)
        self.mock_redis_client.get.return_value = None
        
        # Test method
        should_send = self.service.should_send_notification()
        
        # Verify result
        self.assertTrue(should_send)
        
        # Verify Redis call
        expected_key = f"{self.service.REDIS_KEY_PREFIX}last_sent"
        self.mock_redis_client.get.assert_called_once_with(expected_key)
    
    def test_should_send_notification_within_rate_limit_window(self):
        """Test rate limiting when within the 24-hour window"""
        # Configure Redis to return recent timestamp
        recent_time = datetime.now() - timedelta(hours=12)  # 12 hours ago
        self.mock_redis_client.get.return_value = recent_time.isoformat().encode('utf-8')
        
        # Test method
        should_send = self.service.should_send_notification()
        
        # Verify result (should be rate limited)
        self.assertFalse(should_send)
    
    def test_should_send_notification_outside_rate_limit_window(self):
        """Test rate limiting when outside the 24-hour window"""
        # Configure Redis to return old timestamp
        old_time = datetime.now() - timedelta(hours=25)  # 25 hours ago
        self.mock_redis_client.get.return_value = old_time.isoformat().encode('utf-8')
        
        # Test method
        should_send = self.service.should_send_notification()
        
        # Verify result (should be allowed)
        self.assertTrue(should_send)
    
    @patch('redis.from_url')
    def test_should_send_notification_redis_unavailable(self, mock_redis_from_url):
        """Test rate limiting when Redis is unavailable"""
        # Mock Redis initialization to fail
        mock_redis_from_url.side_effect = Exception("Redis connection failed")
        
        # Create service without Redis
        service = StorageEmailNotificationService(
            email_service=self.mock_email_service,
            db_manager=self.mock_db_manager,
            redis_client=None,
            app=self.mock_app
        )
        
        # Test method
        should_send = service.should_send_notification()
        
        # Verify result (should fail open and allow sending)
        self.assertTrue(should_send)
    
    def test_should_send_notification_redis_error(self):
        """Test rate limiting when Redis raises an error"""
        # Configure Redis to raise exception
        self.mock_redis_client.get.side_effect = Exception("Redis connection failed")
        
        # Test method
        should_send = self.service.should_send_notification()
        
        # Verify result (should fail open and allow sending)
        self.assertTrue(should_send)
    
    def test_record_notification_sent(self):
        """Test recording notification sent timestamp"""
        # Test method
        self.service._record_notification_sent()
        
        # Verify Redis call
        expected_key = f"{self.service.REDIS_KEY_PREFIX}last_sent"
        self.mock_redis_client.setex.assert_called_once()
        
        # Verify call arguments
        call_args = self.mock_redis_client.setex.call_args
        self.assertEqual(call_args[0][0], expected_key)  # Key
        self.assertEqual(call_args[0][1], 25 * 3600)     # Expiration (25 hours)
        # Timestamp should be recent ISO format
        timestamp_arg = call_args[0][2]
        self.assertIsInstance(timestamp_arg, str)
        # Should be able to parse as ISO format
        datetime.fromisoformat(timestamp_arg)
    
    def test_record_notification_sent_redis_unavailable(self):
        """Test recording notification when Redis is unavailable"""
        # Create service without Redis
        service = StorageEmailNotificationService(
            email_service=self.mock_email_service,
            db_manager=self.mock_db_manager,
            redis_client=None,
            app=self.mock_app
        )
        
        # Test method (should not raise exception)
        service._record_notification_sent()
        
        # No assertions needed - just verify no exception is raised
    
    def test_format_storage_alert_email_critical_usage(self):
        """Test email formatting for critical storage usage (100%+)"""
        # Configure email service to use fallback (since template will fail)
        self.mock_email_service.render_template.side_effect = Exception("Template not found")
        
        # Create critical usage metrics
        critical_metrics = StorageMetrics(
            total_bytes=10737418240,  # 10GB in bytes
            total_gb=10.0,
            limit_gb=10.0,
            usage_percentage=100.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime(2025, 1, 15, 12, 30, 45)
        )
        
        # Test method
        email_content = self.service.format_storage_alert_email(critical_metrics)
        
        # Verify structure
        self.assertIn('html', email_content)
        self.assertIn('text', email_content)
        
        # Verify HTML content
        html_content = email_content['html']
        self.assertIn('CRITICAL', html_content)
        self.assertIn('10.0GB', html_content)
        self.assertIn('100.0%', html_content)
        self.assertIn('blocked', html_content)
        self.assertIn('https://test.example.com/admin/cleanup', html_content)
        
        # Verify text content
        text_content = email_content['text']
        self.assertIn('CRITICAL', text_content)
        self.assertIn('10.0GB', text_content)
        self.assertIn('100.0%', text_content)
        self.assertIn('blocked', text_content)
    
    def test_format_storage_alert_email_high_usage(self):
        """Test email formatting for high storage usage (95-99%)"""
        # Configure email service to use fallback
        self.mock_email_service.render_template.side_effect = Exception("Template not found")
        
        # Create high usage metrics
        high_metrics = StorageMetrics(
            total_bytes=10200547328,  # 9.5GB in bytes
            total_gb=9.5,
            limit_gb=10.0,
            usage_percentage=95.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime(2025, 1, 15, 12, 30, 45)
        )
        
        # Test method
        email_content = self.service.format_storage_alert_email(high_metrics)
        
        # Verify HTML content
        html_content = email_content['html']
        self.assertIn('HIGH', html_content)
        self.assertIn('9.5GB', html_content)
        self.assertIn('95.0%', html_content)
        self.assertIn('at risk', html_content)
        
        # Verify text content
        text_content = email_content['text']
        self.assertIn('HIGH', text_content)
        self.assertIn('at risk', text_content)
    
    def test_format_storage_alert_email_medium_usage(self):
        """Test email formatting for medium storage usage (80-94%)"""
        # Configure email service to use fallback
        self.mock_email_service.render_template.side_effect = Exception("Template not found")
        
        # Test method with default test metrics (80%)
        email_content = self.service.format_storage_alert_email(self.test_metrics)
        
        # Verify HTML content
        html_content = email_content['html']
        self.assertIn('MEDIUM', html_content)
        self.assertIn('8.0GB', html_content)
        self.assertIn('80.0%', html_content)
        self.assertIn('at risk', html_content)
        
        # Verify text content
        text_content = email_content['text']
        self.assertIn('MEDIUM', text_content)
        self.assertIn('at risk', text_content)
    
    def test_format_storage_alert_email_custom_base_url(self):
        """Test email formatting with custom base URL"""
        # Configure email service to use fallback
        self.mock_email_service.render_template.side_effect = Exception("Template not found")
        
        custom_base_url = 'https://custom.example.com'
        
        # Test method
        email_content = self.service.format_storage_alert_email(self.test_metrics, custom_base_url)
        
        # Verify custom URLs in content
        html_content = email_content['html']
        self.assertIn('https://custom.example.com/admin/cleanup', html_content)
        self.assertIn('https://custom.example.com/admin', html_content)
        
        text_content = email_content['text']
        self.assertIn('https://custom.example.com/admin/cleanup', text_content)
        self.assertIn('https://custom.example.com/admin', text_content)
    
    def test_format_storage_alert_email_template_fallback(self):
        """Test email formatting with template rendering failure"""
        # Configure email service to fail template rendering
        self.mock_email_service.render_template.side_effect = Exception("Template not found")
        
        # Test method
        email_content = self.service.format_storage_alert_email(self.test_metrics)
        
        # Verify fallback HTML is used
        html_content = email_content['html']
        self.assertIn('Storage Limit Alert', html_content)
        self.assertIn('8.0GB', html_content)
        self.assertIn('MEDIUM ALERT', html_content)
        
        # Verify text content is still generated
        text_content = email_content['text']
        self.assertIn('STORAGE LIMIT ALERT', text_content)
    
    def test_send_storage_limit_alert_success(self):
        """Test successful storage limit alert sending"""
        async def run_test():
            # Configure mock database session context manager
            mock_session = Mock()
            mock_context_manager = Mock()
            mock_context_manager.__enter__ = Mock(return_value=mock_session)
            mock_context_manager.__exit__ = Mock(return_value=None)
            self.mock_db_manager.get_session.return_value = mock_context_manager
            mock_session.query.return_value.filter.return_value.all.return_value = self.test_admin_users
            
            self.mock_redis_client.get.return_value = None  # No rate limiting
            self.mock_email_service.is_configured.return_value = True
            self.mock_email_service.create_message.return_value = Mock()
            self.mock_email_service.send_email_with_retry = AsyncMock(return_value=True)
            
            # Test method
            result = await self.service.send_storage_limit_alert(self.test_metrics)
            
            # Verify success
            self.assertTrue(result)
            
            # Verify email service calls
            self.mock_email_service.create_message.assert_called_once()
            self.mock_email_service.send_email_with_retry.assert_called_once()
            
            # Verify rate limiting was recorded
            self.mock_redis_client.setex.assert_called_once()
        
        # Run async test
        asyncio.run(run_test())
    
    def test_send_storage_limit_alert_rate_limited(self):
        """Test storage limit alert sending when rate limited"""
        async def run_test():
            # Configure rate limiting
            recent_time = datetime.now() - timedelta(hours=12)
            self.mock_redis_client.get.return_value = recent_time.isoformat().encode('utf-8')
            
            # Test method
            result = await self.service.send_storage_limit_alert(self.test_metrics)
            
            # Verify rate limited
            self.assertFalse(result)
            
            # Verify no email was sent
            self.mock_email_service.send_email_with_retry.assert_not_called()
        
        # Run async test
        asyncio.run(run_test())
    
    def test_send_storage_limit_alert_no_admin_emails(self):
        """Test storage limit alert sending when no admin emails exist"""
        async def run_test():
            # Configure mock database session context manager with no admin users
            mock_session = Mock()
            mock_context_manager = Mock()
            mock_context_manager.__enter__ = Mock(return_value=mock_session)
            mock_context_manager.__exit__ = Mock(return_value=None)
            self.mock_db_manager.get_session.return_value = mock_context_manager
            mock_session.query.return_value.filter.return_value.all.return_value = []
            
            self.mock_redis_client.get.return_value = None  # No rate limiting
            
            # Test method
            result = await self.service.send_storage_limit_alert(self.test_metrics)
            
            # Verify failure
            self.assertFalse(result)
            
            # Verify no email was sent
            self.mock_email_service.send_email_with_retry.assert_not_called()
        
        # Run async test
        asyncio.run(run_test())
    
    def test_send_storage_limit_alert_email_service_not_configured(self):
        """Test storage limit alert sending when email service is not configured"""
        async def run_test():
            # Configure mock database session context manager
            mock_session = Mock()
            mock_context_manager = Mock()
            mock_context_manager.__enter__ = Mock(return_value=mock_session)
            mock_context_manager.__exit__ = Mock(return_value=None)
            self.mock_db_manager.get_session.return_value = mock_context_manager
            mock_session.query.return_value.filter.return_value.all.return_value = self.test_admin_users
            
            self.mock_redis_client.get.return_value = None  # No rate limiting
            self.mock_email_service.is_configured.return_value = False  # Not configured
            
            # Test method
            result = await self.service.send_storage_limit_alert(self.test_metrics)
            
            # Verify failure
            self.assertFalse(result)
            
            # Verify no email was sent
            self.mock_email_service.send_email_with_retry.assert_not_called()
        
        # Run async test
        asyncio.run(run_test())
    
    def test_send_storage_limit_alert_email_send_failure(self):
        """Test storage limit alert sending when email sending fails"""
        async def run_test():
            # Configure mock database session context manager
            mock_session = Mock()
            mock_context_manager = Mock()
            mock_context_manager.__enter__ = Mock(return_value=mock_session)
            mock_context_manager.__exit__ = Mock(return_value=None)
            self.mock_db_manager.get_session.return_value = mock_context_manager
            mock_session.query.return_value.filter.return_value.all.return_value = self.test_admin_users
            
            self.mock_redis_client.get.return_value = None  # No rate limiting
            self.mock_email_service.is_configured.return_value = True
            self.mock_email_service.create_message.return_value = Mock()
            self.mock_email_service.send_email_with_retry = AsyncMock(return_value=False)  # Send fails
            
            # Test method
            result = await self.service.send_storage_limit_alert(self.test_metrics)
            
            # Verify failure
            self.assertFalse(result)
            
            # Verify email send was attempted
            self.mock_email_service.send_email_with_retry.assert_called_once()
            
            # Verify rate limiting was NOT recorded (since send failed)
            self.mock_redis_client.setex.assert_not_called()
        
        # Run async test
        asyncio.run(run_test())
    
    def test_get_rate_limit_status_no_previous_notification(self):
        """Test rate limit status when no previous notification exists"""
        # Configure Redis to return None
        self.mock_redis_client.get.return_value = None
        
        # Test method
        status = self.service.get_rate_limit_status()
        
        # Verify status
        expected_status = {
            'rate_limiting_enabled': True,
            'last_sent': None,
            'can_send_now': True,
            'next_allowed_time': None,
            'window_hours': 24
        }
        self.assertEqual(status, expected_status)
    
    def test_get_rate_limit_status_within_window(self):
        """Test rate limit status when within rate limit window"""
        # Configure Redis with recent timestamp
        recent_time = datetime.now() - timedelta(hours=12)
        self.mock_redis_client.get.return_value = recent_time.isoformat().encode('utf-8')
        
        # Test method
        status = self.service.get_rate_limit_status()
        
        # Verify status
        self.assertTrue(status['rate_limiting_enabled'])
        self.assertEqual(status['last_sent'], recent_time.isoformat())
        self.assertFalse(status['can_send_now'])
        self.assertIsNotNone(status['next_allowed_time'])
        self.assertEqual(status['window_hours'], 24)
        self.assertAlmostEqual(status['time_since_last_hours'], 12, delta=0.1)
    
    def test_get_rate_limit_status_outside_window(self):
        """Test rate limit status when outside rate limit window"""
        # Configure Redis with old timestamp
        old_time = datetime.now() - timedelta(hours=25)
        self.mock_redis_client.get.return_value = old_time.isoformat().encode('utf-8')
        
        # Test method
        status = self.service.get_rate_limit_status()
        
        # Verify status
        self.assertTrue(status['rate_limiting_enabled'])
        self.assertEqual(status['last_sent'], old_time.isoformat())
        self.assertTrue(status['can_send_now'])
        self.assertIsNone(status['next_allowed_time'])
        self.assertAlmostEqual(status['time_since_last_hours'], 25, delta=0.1)
    
    @patch('redis.from_url')
    def test_get_rate_limit_status_redis_unavailable(self, mock_redis_from_url):
        """Test rate limit status when Redis is unavailable"""
        # Mock Redis initialization to fail
        mock_redis_from_url.side_effect = Exception("Redis connection failed")
        
        # Create service without Redis
        service = StorageEmailNotificationService(
            email_service=self.mock_email_service,
            db_manager=self.mock_db_manager,
            redis_client=None,
            app=self.mock_app
        )
        
        # Test method
        status = service.get_rate_limit_status()
        
        # Verify status
        expected_status = {
            'rate_limiting_enabled': False,
            'reason': 'Redis not available'
        }
        self.assertEqual(status, expected_status)
    
    def test_get_rate_limit_status_redis_error(self):
        """Test rate limit status when Redis raises an error"""
        # Configure Redis to raise exception
        self.mock_redis_client.get.side_effect = Exception("Redis connection failed")
        
        # Test method
        status = self.service.get_rate_limit_status()
        
        # Verify status
        self.assertFalse(status['rate_limiting_enabled'])
        self.assertIn('Error:', status['reason'])
    
    def test_reset_rate_limit_success(self):
        """Test successful rate limit reset"""
        # Configure Redis to return success
        self.mock_redis_client.delete.return_value = 1  # Key was deleted
        
        # Test method
        result = self.service.reset_rate_limit()
        
        # Verify success
        self.assertTrue(result)
        
        # Verify Redis call
        expected_key = f"{self.service.REDIS_KEY_PREFIX}last_sent"
        self.mock_redis_client.delete.assert_called_once_with(expected_key)
    
    def test_reset_rate_limit_no_key_to_delete(self):
        """Test rate limit reset when no key exists"""
        # Configure Redis to return 0 (no key deleted)
        self.mock_redis_client.delete.return_value = 0
        
        # Test method
        result = self.service.reset_rate_limit()
        
        # Verify success (no key to delete is still success)
        self.assertTrue(result)
    
    @patch('redis.from_url')
    def test_reset_rate_limit_redis_unavailable(self, mock_redis_from_url):
        """Test rate limit reset when Redis is unavailable"""
        # Mock Redis initialization to fail
        mock_redis_from_url.side_effect = Exception("Redis connection failed")
        
        # Create service without Redis
        service = StorageEmailNotificationService(
            email_service=self.mock_email_service,
            db_manager=self.mock_db_manager,
            redis_client=None,
            app=self.mock_app
        )
        
        # Test method
        result = service.reset_rate_limit()
        
        # Verify failure
        self.assertFalse(result)
    
    def test_reset_rate_limit_redis_error(self):
        """Test rate limit reset when Redis raises an error"""
        # Configure Redis to raise exception
        self.mock_redis_client.delete.side_effect = Exception("Redis connection failed")
        
        # Test method
        result = self.service.reset_rate_limit()
        
        # Verify failure
        self.assertFalse(result)


class TestStorageEmailNotificationServiceIntegration(unittest.TestCase):
    """Integration tests for StorageEmailNotificationService"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Create mock Flask app with proper configuration
        self.mock_app = Mock()
        self.mock_app.config = {
            'BASE_URL': 'https://integration-test.example.com',
            'MAIL_SERVER': 'localhost',
            'MAIL_PORT': 587,
            'MAIL_USE_TLS': True,
            'MAIL_USERNAME': 'test@example.com',
            'MAIL_PASSWORD': 'testpass',
            'MAIL_DEFAULT_SENDER': 'noreply@example.com'
        }
        
        # Create test storage metrics
        self.test_metrics = StorageMetrics(
            total_bytes=9663676416,  # 9GB in bytes
            total_gb=9.0,
            limit_gb=10.0,
            usage_percentage=90.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime(2025, 1, 15, 14, 30, 0)
        )
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_service_initialization(self):
        """Test full service initialization with auto-created components"""
        # Test that service can be created with app context
        service = StorageEmailNotificationService(app=self.mock_app)
        
        # Verify service was created with app
        self.assertIsNotNone(service)
        self.assertEqual(service.app, self.mock_app)
        
        # Auto-initialization behavior will vary based on environment
        # This is acceptable for integration testing
    
    def test_email_content_formatting_consistency(self):
        """Test that email content formatting is consistent across different usage levels"""
        # Create service with mocks
        mock_email_service = Mock(spec=EmailService)
        mock_email_service.render_template.side_effect = Exception("Template not found")  # Force fallback
        
        service = StorageEmailNotificationService(
            email_service=mock_email_service,
            app=self.mock_app
        )
        
        # Test different usage levels
        usage_levels = [
            (85.0, "MEDIUM"),
            (95.0, "HIGH"),
            (100.0, "CRITICAL"),
            (105.0, "CRITICAL")
        ]
        
        for usage_percentage, expected_urgency in usage_levels:
            with self.subTest(usage_percentage=usage_percentage):
                # Create metrics for this usage level
                metrics = StorageMetrics(
                    total_bytes=int(usage_percentage * 1073741824 / 10),  # Convert to bytes
                    total_gb=usage_percentage / 10,
                    limit_gb=10.0,
                    usage_percentage=usage_percentage,
                    is_limit_exceeded=usage_percentage >= 100,
                    is_warning_exceeded=usage_percentage >= 80,
                    last_calculated=datetime.now()
                )
                
                # Format email
                email_content = service.format_storage_alert_email(metrics)
                
                # Verify consistency
                self.assertIn('html', email_content)
                self.assertIn('text', email_content)
                
                # Verify urgency level
                html_content = email_content['html']
                text_content = email_content['text']
                
                self.assertIn(expected_urgency, html_content)
                self.assertIn(expected_urgency, text_content)
                
                # Verify usage information
                self.assertIn(f"{usage_percentage:.1f}%", html_content)
                self.assertIn(f"{usage_percentage:.1f}%", text_content)
                
                # Verify URLs
                self.assertIn('https://integration-test.example.com/admin/cleanup', html_content)
                self.assertIn('https://integration-test.example.com/admin', html_content)
    
    def test_rate_limiting_behavior_over_time(self):
        """Test rate limiting behavior over multiple time periods"""
        # Create service with real Redis mock
        mock_redis = Mock()
        service = StorageEmailNotificationService(
            email_service=Mock(spec=EmailService),
            redis_client=mock_redis,
            app=self.mock_app
        )
        
        # Simulate rate limiting behavior
        test_scenarios = [
            # (redis_get_return, expected_should_send, description)
            (None, True, "No previous notification"),
            (datetime.now().isoformat().encode('utf-8'), False, "Just sent"),
            ((datetime.now() - timedelta(hours=12)).isoformat().encode('utf-8'), False, "12 hours ago"),
            ((datetime.now() - timedelta(hours=23)).isoformat().encode('utf-8'), False, "23 hours ago"),
            ((datetime.now() - timedelta(hours=25)).isoformat().encode('utf-8'), True, "25 hours ago"),
        ]
        
        for redis_return, expected_result, description in test_scenarios:
            with self.subTest(description=description):
                # Configure Redis mock
                mock_redis.get.return_value = redis_return
                
                # Test rate limiting
                result = service.should_send_notification()
                
                # Verify result
                self.assertEqual(result, expected_result, f"Failed for scenario: {description}")


if __name__ == '__main__':
    unittest.main()