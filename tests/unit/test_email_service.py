# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Email Service
"""

import unittest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from flask import Flask
from flask_mailing import Message

from services.email_service import EmailService, email_service

class TestEmailService(unittest.TestCase):
    """Test EmailService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Set up email configuration
        self.app.config['MAIL_SERVER'] = 'smtp.example.com'
        self.app.config['MAIL_PORT'] = 587
        self.app.config['MAIL_USE_TLS'] = True
        self.app.config['MAIL_USERNAME'] = 'test@test.com'
        self.app.config['MAIL_PASSWORD'] = 'testpassword'
        self.app.config['MAIL_DEFAULT_SENDER'] = 'noreply@test.com'
        
        self.email_service = EmailService()
        self.email_service.init_app(self.app)
    
    def test_email_service_initialization(self):
        """Test email service initialization"""
        self.assertIsNotNone(self.email_service.mail)
        self.assertIsNotNone(self.email_service.app)
        self.assertEqual(self.email_service.app, self.app)
    
    def test_is_configured_true(self):
        """Test is_configured returns True for properly configured service"""
        self.assertTrue(self.email_service.is_configured())
    
    def test_is_configured_false(self):
        """Test is_configured returns False for improperly configured service"""
        # Test with localhost server
        self.app.config['MAIL_SERVER'] = 'localhost'
        self.assertFalse(self.email_service.is_configured())
        
        # Test with missing username
        self.app.config['MAIL_SERVER'] = 'smtp.example.com'
        self.app.config['MAIL_USERNAME'] = ''
        self.assertFalse(self.email_service.is_configured())
        
        # Test with missing password
        self.app.config['MAIL_USERNAME'] = 'test@test.com'
        self.app.config['MAIL_PASSWORD'] = ''
        self.assertFalse(self.email_service.is_configured())
    
    def test_create_message(self):
        """Test email message creation"""
        with self.app.app_context():
            message = self.email_service.create_message(
                subject="Test Subject",
                recipients=["test@test.com"],
                html_body="<h1>Test HTML</h1>",
                text_body="Test Text"
            )
            
            self.assertIsInstance(message, Message)
            self.assertEqual(message.subject, "Test Subject")
            self.assertEqual(message.recipients, ["test@test.com"])
            self.assertEqual(message.html, "<h1>Test HTML</h1>")
            self.assertEqual(message.body, "Test Text")
            self.assertEqual(message.sender, "noreply@test.com")
    
    def test_create_message_custom_sender(self):
        """Test email message creation with custom sender"""
        with self.app.app_context():
            message = self.email_service.create_message(
                subject="Test Subject",
                recipients=["test@test.com"],
                html_body="<h1>Test HTML</h1>",
                sender="custom@test.com"
            )
            
            self.assertEqual(message.sender, "custom@test.com")
    
    @patch('services.email_service.render_template')
    def test_render_template_success(self, mock_render_template):
        """Test successful template rendering"""
        mock_render_template.return_value = "<h1>Rendered Template</h1>"
        
        with self.app.app_context():
            result = self.email_service.render_template(
                'email_verification.html',
                username='testuser',
                verification_url='http://example.com/verify'
            )
            
            self.assertEqual(result, "<h1>Rendered Template</h1>")
            mock_render_template.assert_called_once_with(
                'emails/email_verification.html',
                username='testuser',
                verification_url='http://example.com/verify'
            )
    
    @patch('services.email_service.render_template')
    def test_render_template_fallback(self, mock_render_template):
        """Test template rendering with fallback"""
        mock_render_template.side_effect = Exception("Template not found")
        
        with self.app.app_context():
            result = self.email_service.render_template(
                'email_verification.html',
                username='testuser',
                verification_url='http://example.com/verify'
            )
            
            # Should return fallback template
            self.assertIn("Email Verification", result)
            self.assertIn("http://example.com/verify", result)
    
    def test_get_fallback_template_verification(self):
        """Test fallback template for email verification"""
        result = self.email_service._get_fallback_template(
            'email_verification.html',
            verification_url='http://example.com/verify'
        )
        
        self.assertIn("Email Verification", result)
        self.assertIn("http://example.com/verify", result)
        self.assertIn("<html>", result)
    
    def test_get_fallback_template_password_reset(self):
        """Test fallback template for password reset"""
        result = self.email_service._get_fallback_template(
            'password_reset.html',
            reset_url='http://example.com/reset'
        )
        
        self.assertIn("Password Reset", result)
        self.assertIn("http://example.com/reset", result)
        self.assertIn("1 hour", result)
    
    def test_get_fallback_template_account_created(self):
        """Test fallback template for account created"""
        result = self.email_service._get_fallback_template(
            'account_created.html',
            username='testuser',
            temporary_password='temp123'
        )
        
        self.assertIn("Account Created", result)
        self.assertIn("testuser", result)
        self.assertIn("temp123", result)
    
    @patch.object(EmailService, 'send_email_with_retry')
    @patch.object(EmailService, 'render_template')
    async def test_send_verification_email(self, mock_render_template, mock_send_email):
        """Test sending verification email"""
        mock_render_template.return_value = "<h1>Verification Email</h1>"
        mock_send_email.return_value = True
        
        result = await self.email_service.send_verification_email(
            user_email="test@test.com",
            username="testuser",
            verification_token="abc123",
            base_url="http://localhost:5000"
        )
        
        self.assertTrue(result)
        mock_render_template.assert_called_once()
        mock_send_email.assert_called_once()
    
    @patch.object(EmailService, 'send_email_with_retry')
    @patch.object(EmailService, 'render_template')
    async def test_send_password_reset_email(self, mock_render_template, mock_send_email):
        """Test sending password reset email"""
        mock_render_template.return_value = "<h1>Password Reset</h1>"
        mock_send_email.return_value = True
        
        result = await self.email_service.send_password_reset_email(
            user_email="test@test.com",
            username="testuser",
            reset_token="xyz789",
            base_url="http://localhost:5000"
        )
        
        self.assertTrue(result)
        mock_render_template.assert_called_once()
        mock_send_email.assert_called_once()
    
    @patch.object(EmailService, 'send_email_with_retry')
    @patch.object(EmailService, 'render_template')
    async def test_send_account_created_email(self, mock_render_template, mock_send_email):
        """Test sending account created email"""
        mock_render_template.return_value = "<h1>Account Created</h1>"
        mock_send_email.return_value = True
        
        result = await self.email_service.send_account_created_email(
            user_email="test@test.com",
            username="testuser",
            temporary_password="temp123",
            base_url="http://localhost:5000"
        )
        
        self.assertTrue(result)
        mock_render_template.assert_called_once()
        mock_send_email.assert_called_once()
    
    @patch.object(EmailService, 'send_email_with_retry')
    @patch.object(EmailService, 'render_template')
    async def test_send_profile_deleted_confirmation(self, mock_render_template, mock_send_email):
        """Test sending profile deleted confirmation email"""
        mock_render_template.return_value = "<h1>Profile Deleted</h1>"
        mock_send_email.return_value = True
        
        result = await self.email_service.send_profile_deleted_confirmation(
            user_email="test@test.com",
            username="testuser"
        )
        
        self.assertTrue(result)
        mock_render_template.assert_called_once()
        mock_send_email.assert_called_once()
    
    @patch.object(EmailService, 'send_email_with_retry')
    @patch.object(EmailService, 'render_template')
    async def test_send_notification_email(self, mock_render_template, mock_send_email):
        """Test sending generic notification email"""
        mock_render_template.return_value = "<h1>Notification</h1>"
        mock_send_email.return_value = True
        
        result = await self.email_service.send_notification_email(
            user_email="test@test.com",
            username="testuser",
            subject="Test Notification",
            message_body="This is a test notification"
        )
        
        self.assertTrue(result)
        mock_render_template.assert_called_once()
        mock_send_email.assert_called_once()
    
    @patch.object(EmailService, 'send_email_with_retry')
    @patch.object(EmailService, 'render_template')
    async def test_send_data_export_notification(self, mock_render_template, mock_send_email):
        """Test sending GDPR data export notification"""
        mock_render_template.return_value = "<h1>Data Export Ready</h1>"
        mock_send_email.return_value = True
        
        result = await self.email_service.send_data_export_notification(
            user_email="test@test.com",
            username="testuser",
            export_timestamp="2025-01-16 10:00:00",
            base_url="http://localhost:5000"
        )
        
        self.assertTrue(result)
        mock_render_template.assert_called_once()
        mock_send_email.assert_called_once()
    
    @patch.object(EmailService, 'send_email_with_retry')
    @patch.object(EmailService, 'render_template')
    async def test_send_data_deletion_confirmation(self, mock_render_template, mock_send_email):
        """Test sending GDPR data deletion confirmation"""
        mock_render_template.return_value = "<h1>Data Deleted</h1>"
        mock_send_email.return_value = True
        
        result = await self.email_service.send_data_deletion_confirmation(
            user_email="test@test.com",
            username="testuser",
            deletion_type="complete"
        )
        
        self.assertTrue(result)
        mock_render_template.assert_called_once()
        mock_send_email.assert_called_once()
    
    @patch.object(EmailService, 'send_email_with_retry')
    @patch.object(EmailService, 'render_template')
    async def test_send_consent_withdrawal_confirmation(self, mock_render_template, mock_send_email):
        """Test sending consent withdrawal confirmation"""
        mock_render_template.return_value = "<h1>Consent Withdrawn</h1>"
        mock_send_email.return_value = True
        
        result = await self.email_service.send_consent_withdrawal_confirmation(
            user_email="test@test.com",
            username="testuser",
            base_url="http://localhost:5000"
        )
        
        self.assertTrue(result)
        mock_render_template.assert_called_once()
        mock_send_email.assert_called_once()
    
    async def test_send_email_with_retry_not_configured(self):
        """Test email sending when service is not configured"""
        # Make service appear not configured
        self.app.config['MAIL_SERVER'] = 'localhost'
        
        message = Mock()
        message.recipients = ["test@test.com"]
        
        result = await self.email_service.send_email_with_retry(message)
        
        self.assertFalse(result)
    
    @patch('services.email_service.time.sleep')
    async def test_send_email_with_retry_failure(self, mock_sleep):
        """Test email sending with retry on failure"""
        # Mock the mail.send_message to always fail
        self.email_service.mail = Mock()
        self.email_service.mail.send_message = AsyncMock(side_effect=Exception("SMTP Error"))
        
        message = Mock()
        message.recipients = ["test@test.com"]
        
        result = await self.email_service.send_email_with_retry(message)
        
        self.assertFalse(result)
        # Should have tried 3 times (max_retries)
        self.assertEqual(self.email_service.mail.send_message.call_count, 3)
        # Should have slept between retries
        self.assertEqual(mock_sleep.call_count, 2)
    
    async def test_send_email_with_retry_success_after_failure(self):
        """Test email sending success after initial failure"""
        # Mock the mail.send_message to fail once then succeed
        self.email_service.mail = Mock()
        self.email_service.mail.send_message = AsyncMock(side_effect=[Exception("SMTP Error"), None])
        
        message = Mock()
        message.recipients = ["test@test.com"]
        
        with patch('services.email_service.time.sleep'):
            result = await self.email_service.send_email_with_retry(message)
        
        self.assertTrue(result)
        # Should have tried twice
        self.assertEqual(self.email_service.mail.send_message.call_count, 2)
    
    async def test_send_email_with_retry_immediate_success(self):
        """Test email sending with immediate success"""
        # Mock the mail.send_message to succeed immediately
        self.email_service.mail = Mock()
        self.email_service.mail.send_message = AsyncMock(return_value=None)
        
        message = Mock()
        message.recipients = ["test@test.com"]
        
        result = await self.email_service.send_email_with_retry(message)
        
        self.assertTrue(result)
        # Should have tried only once
        self.assertEqual(self.email_service.mail.send_message.call_count, 1)

class TestEmailServiceIntegration(unittest.TestCase):
    """Test EmailService integration functionality"""
    
    def test_global_email_service_instance(self):
        """Test global email service instance"""
        self.assertIsInstance(email_service, EmailService)
    
    def test_init_email_service_function(self):
        """Test init_email_service function"""
        from services.email_service import init_email_service
        
        app = Flask(__name__)
        app.config['MAIL_SERVER'] = 'smtp.example.com'
        app.config['MAIL_USERNAME'] = 'test@test.com'
        app.config['MAIL_PASSWORD'] = 'testpass'
        
        service = init_email_service(app)
        
        self.assertIsInstance(service, EmailService)
        self.assertEqual(service.app, app)
        self.assertIsNotNone(service.mail)

if __name__ == '__main__':
    unittest.main()