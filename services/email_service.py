# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Email Service for User Management

This service handles all email communications for user management including
email verification, password reset, and user notifications using flask-mailing.
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from flask import Flask, render_template
from flask_mailing import Mail, Message
from jinja2 import Template

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails using flask-mailing"""
    
    def __init__(self, app: Optional[Flask] = None):
        """Initialize email service"""
        self.mail = None
        self.app = app
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize email service with Flask app"""
        self.app = app
        
        # Configure flask-mailing
        app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'localhost')
        app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
        app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
        app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
        app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
        app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
        app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@localhost')
        
        # Initialize Mail instance
        self.mail = Mail(app)
        
        logger.info(f"Email service initialized with server: {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        if not self.mail or not self.app:
            return False
        
        server = self.app.config.get('MAIL_SERVER')
        username = self.app.config.get('MAIL_USERNAME')
        password = self.app.config.get('MAIL_PASSWORD')
        
        return bool(server and server != 'localhost' and username and password)
    
    async def send_email_with_retry(self, message: Message) -> bool:
        """Send email with retry mechanism"""
        if not self.is_configured():
            logger.warning("Email service not configured - email not sent")
            return False
        
        for attempt in range(self.max_retries):
            try:
                await self.mail.send_message(message)
                logger.info(f"Email sent successfully to {message.recipients}")
                return True
                
            except Exception as e:
                logger.warning(f"Email send attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to send email after {self.max_retries} attempts: {e}")
                    return False
        
        return False
    
    def create_message(self, subject: str, recipients: list, html_body: str, 
                      text_body: Optional[str] = None, sender: Optional[str] = None) -> Message:
        """Create email message"""
        if not sender:
            sender = self.app.config.get('MAIL_DEFAULT_SENDER', 'noreply@localhost')
        
        message = Message(
            subject=subject,
            recipients=recipients,
            html=html_body,
            body=text_body,
            sender=sender
        )
        
        return message
    
    def render_template(self, template_name: str, **context) -> str:
        """Render email template with context"""
        try:
            with self.app.app_context():
                return render_template(f'emails/{template_name}', **context)
        except Exception as e:
            logger.error(f"Failed to render email template {template_name}: {e}")
            # Return a basic fallback template
            return self._get_fallback_template(template_name, **context)
    
    def _get_fallback_template(self, template_name: str, **context) -> str:
        """Get fallback template if main template fails"""
        if 'verification' in template_name:
            return f"""
            <html>
            <body>
                <h2>Email Verification</h2>
                <p>Please verify your email address by clicking the link below:</p>
                <p><a href="{context.get('verification_url', '#')}">Verify Email</a></p>
                <p>If you didn't request this, please ignore this email.</p>
            </body>
            </html>
            """
        elif 'password_reset' in template_name:
            return f"""
            <html>
            <body>
                <h2>Password Reset</h2>
                <p>You requested a password reset. Click the link below to reset your password:</p>
                <p><a href="{context.get('reset_url', '#')}">Reset Password</a></p>
                <p>This link will expire in 1 hour.</p>
                <p>If you didn't request this, please ignore this email.</p>
            </body>
            </html>
            """
        elif 'account_created' in template_name:
            return f"""
            <html>
            <body>
                <h2>Account Created</h2>
                <p>Your account has been created by an administrator.</p>
                <p>Username: {context.get('username', 'N/A')}</p>
                <p>Temporary Password: {context.get('temporary_password', 'N/A')}</p>
                <p>Please log in and change your password immediately.</p>
            </body>
            </html>
            """
        else:
            return f"""
            <html>
            <body>
                <h2>Notification</h2>
                <p>You have received a notification from Vedfolnir.</p>
                <p>Please log in to your account for more details.</p>
            </body>
            </html>
            """
    
    async def send_verification_email(self, user_email: str, username: str, 
                                    verification_token: str, base_url: str) -> bool:
        """Send email verification email"""
        verification_url = f"{base_url}/verify-email/{verification_token}"
        
        html_body = self.render_template('email_verification.html', 
                                       username=username,
                                       verification_url=verification_url,
                                       base_url=base_url)
        
        text_body = f"""
        Hi {username},
        
        Please verify your email address by visiting this link:
        {verification_url}
        
        If you didn't create an account, please ignore this email.
        
        Thanks,
        Vedfolnir Team
        """
        
        message = self.create_message(
            subject="Verify your email address",
            recipients=[user_email],
            html_body=html_body,
            text_body=text_body
        )
        
        return await self.send_email_with_retry(message)
    
    async def send_password_reset_email(self, user_email: str, username: str, 
                                      reset_token: str, base_url: str) -> bool:
        """Send password reset email"""
        reset_url = f"{base_url}/reset-password/{reset_token}"
        
        html_body = self.render_template('password_reset.html',
                                       username=username,
                                       reset_url=reset_url,
                                       base_url=base_url)
        
        text_body = f"""
        Hi {username},
        
        You requested a password reset. Click the link below to reset your password:
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you didn't request this, please ignore this email.
        
        Thanks,
        Vedfolnir Team
        """
        
        message = self.create_message(
            subject="Reset your password",
            recipients=[user_email],
            html_body=html_body,
            text_body=text_body
        )
        
        return await self.send_email_with_retry(message)
    
    async def send_account_created_email(self, user_email: str, username: str, 
                                       temporary_password: str, base_url: str) -> bool:
        """Send account created notification email"""
        login_url = f"{base_url}/login"
        
        html_body = self.render_template('account_created.html',
                                       username=username,
                                       temporary_password=temporary_password,
                                       login_url=login_url,
                                       base_url=base_url)
        
        text_body = f"""
        Hi {username},
        
        Your account has been created by an administrator.
        
        Username: {username}
        Temporary Password: {temporary_password}
        
        Please log in at {login_url} and change your password immediately.
        
        Thanks,
        Vedfolnir Team
        """
        
        message = self.create_message(
            subject="Your account has been created",
            recipients=[user_email],
            html_body=html_body,
            text_body=text_body
        )
        
        return await self.send_email_with_retry(message)
    
    async def send_profile_deleted_confirmation(self, user_email: str, username: str) -> bool:
        """Send profile deletion confirmation email"""
        html_body = self.render_template('profile_deleted.html',
                                       username=username)
        
        text_body = f"""
        Hi {username},
        
        Your profile and all associated data have been successfully deleted from Vedfolnir.
        
        If you didn't request this deletion, please contact support immediately.
        
        Thanks,
        Vedfolnir Team
        """
        
        message = self.create_message(
            subject="Profile deleted successfully",
            recipients=[user_email],
            html_body=html_body,
            text_body=text_body
        )
        
        return await self.send_email_with_retry(message)
    
    async def send_notification_email(self, user_email: str, username: str, 
                                    subject: str, message_body: str, 
                                    template_context: Optional[Dict[str, Any]] = None) -> bool:
        """Send generic notification email"""
        context = template_context or {}
        context.update({
            'username': username,
            'message_body': message_body
        })
        
        html_body = self.render_template('notification.html', **context)
        
        text_body = f"""
        Hi {username},
        
        {message_body}
        
        Thanks,
        Vedfolnir Team
        """
        
        message = self.create_message(
            subject=subject,
            recipients=[user_email],
            html_body=html_body,
            text_body=text_body
        )
        
        return await self.send_email_with_retry(message)
    
    async def send_data_export_notification(self, user_email: str, username: str, 
                                          export_timestamp: str, base_url: str) -> bool:
        """Send GDPR data export notification email"""
        profile_url = f"{base_url}/profile"
        
        html_body = self.render_template('gdpr_data_export.html',
                                       username=username,
                                       export_timestamp=export_timestamp,
                                       profile_url=profile_url,
                                       base_url=base_url)
        
        text_body = f"""
        Hi {username},
        
        Your personal data export has been completed as requested under GDPR Article 20.
        
        Export completed: {export_timestamp}
        
        For security reasons, your data export is available through your profile page at:
        {profile_url}
        
        This export includes all personal data we have about you in a machine-readable format.
        
        If you didn't request this export, please contact support immediately.
        
        Thanks,
        Vedfolnir Team
        """
        
        message = self.create_message(
            subject="Your data export is ready",
            recipients=[user_email],
            html_body=html_body,
            text_body=text_body
        )
        
        return await self.send_email_with_retry(message)
    
    async def send_data_deletion_confirmation(self, user_email: str, username: str, 
                                            deletion_type: str = "complete") -> bool:
        """Send GDPR data deletion confirmation email"""
        html_body = self.render_template('gdpr_data_deletion.html',
                                       username=username,
                                       deletion_type=deletion_type)
        
        text_body = f"""
        Hi {username},
        
        Your personal data has been {'completely deleted' if deletion_type == 'complete' else 'anonymized'} from Vedfolnir as requested under GDPR Article 17.
        
        Deletion completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        
        All your personal information, platform connections, and associated content have been removed from our systems.
        
        If you didn't request this deletion, please contact support immediately.
        
        Thanks,
        Vedfolnir Team
        """
        
        message = self.create_message(
            subject="Your data has been deleted",
            recipients=[user_email],
            html_body=html_body,
            text_body=text_body
        )
        
        return await self.send_email_with_retry(message)
    
    async def send_consent_withdrawal_confirmation(self, user_email: str, username: str, 
                                                 base_url: str) -> bool:
        """Send consent withdrawal confirmation email"""
        contact_url = f"{base_url}/contact"
        
        html_body = self.render_template('gdpr_consent_withdrawal.html',
                                       username=username,
                                       contact_url=contact_url,
                                       base_url=base_url)
        
        text_body = f"""
        Hi {username},
        
        Your consent for data processing has been withdrawn as requested under GDPR Article 7(3).
        
        Withdrawal processed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        
        Please note that withdrawing consent may affect the functionality of your account. 
        You can re-give consent at any time through your profile settings.
        
        If you have any questions, please contact us at: {contact_url}
        
        Thanks,
        Vedfolnir Team
        """
        
        message = self.create_message(
            subject="Consent withdrawal confirmed",
            recipients=[user_email],
            html_body=html_body,
            text_body=text_body
        )
        
        return await self.send_email_with_retry(message)


# Global email service instance
email_service = EmailService()


def init_email_service(app: Flask) -> EmailService:
    """Initialize and return email service"""
    email_service.init_app(app)
    return email_service