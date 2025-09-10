# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Email Notification Service for sending storage limit alerts.

This service extends the existing email infrastructure to send notifications
to administrators when storage limits are reached, with rate limiting to
prevent duplicate notifications within a 24-hour window.
"""

import os
import logging
import redis
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from flask import Flask, current_app

from services.email_service import EmailService
from app.services.storage.components.storage_monitor_service import StorageMetrics
from models import User, UserRole
from app.core.database.core.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class StorageEmailNotificationService:
    """
    Service for sending storage limit email notifications to administrators.
    
    This service extends the existing email infrastructure to provide:
    - Storage limit alert emails to all administrators
    - Rate limiting to prevent duplicate notifications (24-hour window)
    - Email templates with cleanup links and storage information
    - Integration with existing email service infrastructure
    """
    
    # Rate limiting configuration
    RATE_LIMIT_WINDOW_HOURS = 24
    REDIS_KEY_PREFIX = "storage_email_notification:"
    
    def __init__(self, 
                 email_service: Optional[EmailService] = None,
                 db_manager: Optional[DatabaseManager] = None,
                 redis_client: Optional[redis.Redis] = None,
                 app: Optional[Flask] = None):
        """
        Initialize the storage email notification service.
        
        Args:
            email_service: Email service instance (optional, will create if not provided)
            db_manager: Database manager instance (optional, will create if not provided)
            redis_client: Redis client for rate limiting (optional, will create if not provided)
            app: Flask app instance (optional, will use current_app if not provided)
        """
        self.email_service = email_service
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.app = app
        
        # Initialize components if not provided
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize service components if not provided"""
        try:
            # Initialize email service if not provided
            if self.email_service is None:
                if self.app:
                    self.email_service = EmailService(self.app)
                elif current_app:
                    self.email_service = EmailService(current_app)
                else:
                    logger.warning("No Flask app available for email service initialization")
                    self.email_service = EmailService()
            
            # Initialize database manager if not provided
            if self.db_manager is None:
                try:
                    from config import Config
                    config = Config()
                    self.db_manager = DatabaseManager(config)
                except Exception as e:
                    logger.error(f"Failed to initialize database manager: {e}")
                    self.db_manager = None
            
            # Initialize Redis client if not provided
            if self.redis_client is None:
                try:
                    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
                    self.redis_client = redis.from_url(redis_url)
                    # Test connection
                    self.redis_client.ping()
                    logger.debug("Redis client initialized for storage email notifications")
                except Exception as e:
                    logger.warning(f"Failed to initialize Redis client: {e}")
                    logger.warning("Rate limiting will be disabled")
                    self.redis_client = None
                    
        except Exception as e:
            logger.error(f"Failed to initialize storage email notification service components: {e}")
    
    def get_admin_email_list(self) -> List[str]:
        """
        Get list of email addresses for all active admin users.
        
        Returns:
            List[str]: List of admin email addresses
        """
        if not self.db_manager:
            logger.error("Database manager not available, cannot get admin emails")
            return []
        
        try:
            with self.db_manager.get_session() as session:
                admin_users = session.query(User).filter(
                    User.role == UserRole.ADMIN,
                    User.is_active == True,
                    User.email_verified == True
                ).all()
                
                admin_emails = [user.email for user in admin_users if user.email]
                logger.debug(f"Found {len(admin_emails)} admin email addresses")
                return admin_emails
                
        except Exception as e:
            logger.error(f"Failed to get admin email list: {e}")
            return []
    
    def _get_rate_limit_key(self) -> str:
        """
        Get Redis key for rate limiting storage notifications.
        
        Returns:
            str: Redis key for rate limiting
        """
        return f"{self.REDIS_KEY_PREFIX}last_sent"
    
    def should_send_notification(self) -> bool:
        """
        Check if a storage limit notification should be sent based on rate limiting.
        
        Implements 24-hour rate limiting to prevent duplicate notifications.
        
        Returns:
            bool: True if notification should be sent, False if rate limited
        """
        if not self.redis_client:
            # If Redis is not available, allow sending (fail open)
            logger.warning("Redis not available for rate limiting, allowing notification")
            return True
        
        try:
            rate_limit_key = self._get_rate_limit_key()
            last_sent_str = self.redis_client.get(rate_limit_key)
            
            if last_sent_str is None:
                # No previous notification sent
                logger.debug("No previous storage notification found, allowing send")
                return True
            
            # Parse last sent timestamp
            last_sent = datetime.fromisoformat(last_sent_str.decode('utf-8'))
            time_since_last = datetime.now() - last_sent
            
            # Check if enough time has passed
            if time_since_last.total_seconds() >= (self.RATE_LIMIT_WINDOW_HOURS * 3600):
                logger.debug(f"Rate limit window passed ({time_since_last}), allowing send")
                return True
            else:
                remaining_time = timedelta(hours=self.RATE_LIMIT_WINDOW_HOURS) - time_since_last
                logger.info(f"Storage notification rate limited, {remaining_time} remaining")
                return False
                
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Fail open - allow sending if rate limit check fails
            return True
    
    def _record_notification_sent(self) -> None:
        """Record that a notification was sent for rate limiting purposes"""
        if not self.redis_client:
            return
        
        try:
            rate_limit_key = self._get_rate_limit_key()
            current_time = datetime.now().isoformat()
            
            # Store with expiration slightly longer than rate limit window
            expiration_seconds = (self.RATE_LIMIT_WINDOW_HOURS + 1) * 3600
            self.redis_client.setex(rate_limit_key, expiration_seconds, current_time)
            
            logger.debug("Recorded storage notification sent timestamp")
            
        except Exception as e:
            logger.error(f"Failed to record notification sent: {e}")
    
    def format_storage_alert_email(self, metrics: StorageMetrics, base_url: str = None) -> Dict[str, str]:
        """
        Format storage limit alert email content using templates.
        
        Args:
            metrics: Storage metrics containing usage information
            base_url: Base URL for cleanup links (optional)
            
        Returns:
            Dict[str, str]: Dictionary with 'html' and 'text' email content
        """
        # Get base URL from app config if not provided
        if base_url is None:
            try:
                if self.app:
                    base_url = self.app.config.get('BASE_URL', 'http://localhost:5000')
                elif current_app:
                    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
                else:
                    base_url = 'http://localhost:5000'
            except Exception:
                base_url = 'http://localhost:5000'
        
        # Create cleanup URL
        cleanup_url = f"{base_url}/admin/cleanup"
        admin_dashboard_url = f"{base_url}/admin"
        
        # Format usage information
        usage_percentage = metrics.usage_percentage
        usage_gb = metrics.total_gb
        limit_gb = metrics.limit_gb
        
        # Determine urgency level
        if usage_percentage >= 100:
            urgency = "CRITICAL"
            urgency_color = "#dc3545"  # Red
            status_message = "Storage limit has been reached and caption generation is now blocked."
        elif usage_percentage >= 95:
            urgency = "HIGH"
            urgency_color = "#fd7e14"  # Orange
            status_message = "Storage is critically full and will reach the limit very soon."
        else:
            urgency = "MEDIUM"
            urgency_color = "#ffc107"  # Yellow
            status_message = "Storage usage has exceeded the warning threshold."
        
        # Template context
        template_context = {
            'urgency': urgency,
            'urgency_color': urgency_color,
            'status_message': status_message,
            'usage_gb': f"{usage_gb:.1f}",
            'limit_gb': f"{limit_gb:.1f}",
            'usage_percentage': f"{usage_percentage:.1f}",
            'usage_percentage_capped': min(usage_percentage, 100),
            'last_calculated': metrics.last_calculated.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'cleanup_url': cleanup_url,
            'admin_dashboard_url': admin_dashboard_url,
            'is_blocked': usage_percentage >= 100
        }
        
        # Try to render template, fall back to inline HTML if template fails
        try:
            if self.email_service:
                html_content = self.email_service.render_template('storage_limit_alert.html', **template_context)
            else:
                raise Exception("Email service not available")
        except Exception as e:
            logger.warning(f"Failed to render email template, using fallback: {e}")
            html_content = self._get_fallback_html_template(template_context)
        
        # Plain text email content
        text_content = f"""
STORAGE LIMIT ALERT - {urgency} - ACTION REQUIRED

{status_message}

CURRENT STORAGE USAGE:
- Used: {usage_gb:.1f}GB
- Limit: {limit_gb:.1f}GB  
- Usage: {usage_percentage:.1f}%
- Last Calculated: {metrics.last_calculated.strftime('%Y-%m-%d %H:%M:%S UTC')}

RECOMMENDED ACTIONS:
1. Review and delete old or unnecessary images
2. Use the cleanup tools to remove processed images  
3. Consider increasing the storage limit if needed
4. Monitor storage usage regularly to prevent future issues

QUICK ACTIONS:
- Clean Up Storage: {cleanup_url}
- Admin Dashboard: {admin_dashboard_url}

IMPORTANT: Caption generation is currently {'blocked' if usage_percentage >= 100 else 'at risk'} due to storage limits. Please take action as soon as possible to restore normal operation.

---
This alert was sent from Vedfolnir Storage Management System.
You are receiving this because you are an administrator.
This notification is rate-limited to once per 24 hours.
        """
        
        return {
            'html': html_content.strip(),
            'text': text_content.strip()
        }
    
    def _get_fallback_html_template(self, context: Dict[str, Any]) -> str:
        """
        Get fallback HTML template if main template rendering fails.
        
        Args:
            context: Template context variables
            
        Returns:
            str: Fallback HTML content
        """
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h1 style="color: {context['urgency_color']}; text-align: center;">Storage Limit Alert</h1>
                <div style="background-color: {context['urgency_color']}; color: white; padding: 8px 16px; border-radius: 20px; text-align: center; font-weight: bold; margin-bottom: 20px;">
                    {context['urgency']} ALERT
                </div>
                
                <p><strong>Action Required:</strong> {context['status_message']}</p>
                
                <div style="background-color: #f8f9fa; border-left: 4px solid {context['urgency_color']}; padding: 20px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: {context['urgency_color']};">Current Storage Usage</h3>
                    <p><strong>Used:</strong> {context['usage_gb']}GB</p>
                    <p><strong>Limit:</strong> {context['limit_gb']}GB</p>
                    <p><strong>Usage:</strong> {context['usage_percentage']}%</p>
                    <p><strong>Last Calculated:</strong> {context['last_calculated']}</p>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; margin: 20px 0;">
                    <h4 style="margin-top: 0; color: #856404;">Recommended Actions:</h4>
                    <ul>
                        <li>Review and delete old or unnecessary images</li>
                        <li>Use the cleanup tools to remove processed images</li>
                        <li>Consider increasing the storage limit if needed</li>
                        <li>Monitor storage usage regularly to prevent future issues</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{context['cleanup_url']}" style="background-color: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 5px;">Clean Up Storage</a>
                    <a href="{context['admin_dashboard_url']}" style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 5px;">Admin Dashboard</a>
                </div>
                
                <p><strong>Important:</strong> Caption generation is currently {'blocked' if context['is_blocked'] else 'at risk'} due to storage limits.</p>
                
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 14px; color: #666; text-align: center;">
                    <p>This alert was sent from Vedfolnir Storage Management System.</p>
                    <p>You are receiving this because you are an administrator.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    async def send_storage_limit_alert(self, metrics: StorageMetrics, base_url: str = None) -> bool:
        """
        Send storage limit alert email to all administrators.
        
        Args:
            metrics: Storage metrics containing usage information
            base_url: Base URL for cleanup links (optional)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Check rate limiting
            if not self.should_send_notification():
                logger.info("Storage notification rate limited, skipping send")
                return False
            
            # Get admin email addresses
            admin_emails = self.get_admin_email_list()
            if not admin_emails:
                logger.warning("No admin email addresses found, cannot send storage alert")
                return False
            
            # Check if email service is configured
            if not self.email_service or not self.email_service.is_configured():
                logger.warning("Email service not configured, cannot send storage alert")
                return False
            
            # Format email content
            email_content = self.format_storage_alert_email(metrics, base_url)
            
            # Create email message
            subject = f"[Vedfolnir] Storage Limit Alert - {metrics.usage_percentage:.1f}% Used"
            
            message = self.email_service.create_message(
                subject=subject,
                recipients=admin_emails,
                html_body=email_content['html'],
                text_body=email_content['text']
            )
            
            # Send email with retry
            success = await self.email_service.send_email_with_retry(message)
            
            if success:
                # Record that notification was sent for rate limiting
                self._record_notification_sent()
                logger.info(f"Storage limit alert sent to {len(admin_emails)} administrators")
                return True
            else:
                logger.error("Failed to send storage limit alert email")
                return False
                
        except Exception as e:
            logger.error(f"Error sending storage limit alert: {e}")
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limiting status for storage notifications.
        
        Returns:
            Dict[str, Any]: Rate limiting status information
        """
        if not self.redis_client:
            return {
                'rate_limiting_enabled': False,
                'reason': 'Redis not available'
            }
        
        try:
            rate_limit_key = self._get_rate_limit_key()
            last_sent_str = self.redis_client.get(rate_limit_key)
            
            if last_sent_str is None:
                return {
                    'rate_limiting_enabled': True,
                    'last_sent': None,
                    'can_send_now': True,
                    'next_allowed_time': None,
                    'window_hours': self.RATE_LIMIT_WINDOW_HOURS
                }
            
            last_sent = datetime.fromisoformat(last_sent_str.decode('utf-8'))
            time_since_last = datetime.now() - last_sent
            can_send_now = time_since_last.total_seconds() >= (self.RATE_LIMIT_WINDOW_HOURS * 3600)
            
            next_allowed_time = None
            if not can_send_now:
                next_allowed_time = last_sent + timedelta(hours=self.RATE_LIMIT_WINDOW_HOURS)
            
            return {
                'rate_limiting_enabled': True,
                'last_sent': last_sent.isoformat(),
                'time_since_last_hours': time_since_last.total_seconds() / 3600,
                'can_send_now': can_send_now,
                'next_allowed_time': next_allowed_time.isoformat() if next_allowed_time else None,
                'window_hours': self.RATE_LIMIT_WINDOW_HOURS
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {
                'rate_limiting_enabled': False,
                'reason': f'Error: {str(e)}'
            }
    
    def reset_rate_limit(self) -> bool:
        """
        Reset rate limiting to allow immediate notification sending.
        
        This should only be used for testing or emergency situations.
        
        Returns:
            bool: True if rate limit was reset, False otherwise
        """
        if not self.redis_client:
            logger.warning("Redis not available, cannot reset rate limit")
            return False
        
        try:
            rate_limit_key = self._get_rate_limit_key()
            result = self.redis_client.delete(rate_limit_key)
            
            if result:
                logger.info("Storage notification rate limit reset")
                return True
            else:
                logger.info("No rate limit to reset")
                return True
                
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False