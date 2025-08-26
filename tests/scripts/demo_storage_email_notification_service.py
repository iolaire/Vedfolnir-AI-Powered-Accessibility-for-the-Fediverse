#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demo script for StorageEmailNotificationService functionality.

This script demonstrates the storage email notification service with various
usage scenarios and rate limiting behavior.
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage_email_notification_service import StorageEmailNotificationService
from storage_monitor_service import StorageMetrics
from services.email_service import EmailService


def create_test_metrics(usage_percentage: float, limit_gb: float = 10.0) -> StorageMetrics:
    """Create test storage metrics for demonstration"""
    total_gb = (usage_percentage / 100.0) * limit_gb
    total_bytes = int(total_gb * 1024 ** 3)
    
    return StorageMetrics(
        total_bytes=total_bytes,
        total_gb=total_gb,
        limit_gb=limit_gb,
        usage_percentage=usage_percentage,
        is_limit_exceeded=usage_percentage >= 100,
        is_warning_exceeded=usage_percentage >= 80,
        last_calculated=datetime.now()
    )


def demo_email_formatting():
    """Demonstrate email formatting for different usage levels"""
    print("=== StorageEmailNotificationService Email Formatting Demo ===\n")
    
    # Create mock components
    mock_email_service = Mock(spec=EmailService)
    mock_email_service.render_template.side_effect = Exception("Template not found")  # Force fallback
    
    mock_app = Mock()
    mock_app.config = {'BASE_URL': 'https://demo.vedfolnir.com'}
    
    # Create service
    service = StorageEmailNotificationService(
        email_service=mock_email_service,
        app=mock_app
    )
    
    # Test different usage levels
    usage_scenarios = [
        (85.0, "Medium Usage (Warning Threshold)"),
        (95.0, "High Usage (Critical)"),
        (100.0, "Limit Reached (Blocked)"),
        (105.0, "Over Limit (Blocked)")
    ]
    
    for usage_percentage, description in usage_scenarios:
        print(f"--- {description} ---")
        
        # Create metrics
        metrics = create_test_metrics(usage_percentage)
        
        # Format email
        email_content = service.format_storage_alert_email(metrics)
        
        # Display key information
        print(f"Usage: {usage_percentage}% ({metrics.total_gb:.1f}GB / {metrics.limit_gb:.1f}GB)")
        
        # Show HTML snippet
        html_content = email_content['html']
        if 'CRITICAL' in html_content:
            urgency = 'CRITICAL'
        elif 'HIGH' in html_content:
            urgency = 'HIGH'
        else:
            urgency = 'MEDIUM'
        
        print(f"Alert Level: {urgency}")
        print(f"Email Subject: [Vedfolnir] Storage Limit Alert - {usage_percentage:.1f}% Used")
        
        # Show text content snippet
        text_lines = email_content['text'].split('\n')[:5]
        print("Text Content Preview:")
        for line in text_lines:
            if line.strip():
                print(f"  {line}")
        
        print()


def demo_rate_limiting():
    """Demonstrate rate limiting functionality"""
    print("=== Rate Limiting Demo ===\n")
    
    # Create mock Redis client
    mock_redis = Mock()
    
    # Create service
    service = StorageEmailNotificationService(
        redis_client=mock_redis
    )
    
    # Test scenarios
    scenarios = [
        (None, "No previous notification"),
        (datetime.now().isoformat().encode('utf-8'), "Just sent (0 hours ago)"),
        ((datetime.now() - timedelta(hours=12)).isoformat().encode('utf-8'), "12 hours ago"),
        ((datetime.now() - timedelta(hours=25)).isoformat().encode('utf-8'), "25 hours ago (allowed)"),
    ]
    
    for redis_return, description in scenarios:
        print(f"Scenario: {description}")
        
        # Configure mock
        mock_redis.get.return_value = redis_return
        
        # Test rate limiting
        should_send = service.should_send_notification()
        
        print(f"Should send notification: {'Yes' if should_send else 'No (rate limited)'}")
        
        # Get rate limit status
        status = service.get_rate_limit_status()
        if status.get('rate_limiting_enabled'):
            if status.get('can_send_now'):
                print("Status: Ready to send")
            else:
                print(f"Status: Rate limited (last sent: {status.get('time_since_last_hours', 0):.1f} hours ago)")
        else:
            print(f"Status: Rate limiting disabled ({status.get('reason', 'Unknown')})")
        
        print()


def demo_admin_email_retrieval():
    """Demonstrate admin email retrieval"""
    print("=== Admin Email Retrieval Demo ===\n")
    
    # Create mock database components
    from models import User, UserRole
    
    mock_admin_users = [
        Mock(spec=User, email='admin1@vedfolnir.com', role=UserRole.ADMIN, is_active=True, email_verified=True),
        Mock(spec=User, email='admin2@vedfolnir.com', role=UserRole.ADMIN, is_active=True, email_verified=True),
        Mock(spec=User, email='admin3@vedfolnir.com', role=UserRole.ADMIN, is_active=True, email_verified=True)
    ]
    
    mock_session = Mock()
    mock_context_manager = Mock()
    mock_context_manager.__enter__ = Mock(return_value=mock_session)
    mock_context_manager.__exit__ = Mock(return_value=None)
    
    mock_db_manager = Mock()
    mock_db_manager.get_session.return_value = mock_context_manager
    mock_session.query.return_value.filter.return_value.all.return_value = mock_admin_users
    
    # Create service
    service = StorageEmailNotificationService(db_manager=mock_db_manager)
    
    # Get admin emails
    admin_emails = service.get_admin_email_list()
    
    print(f"Found {len(admin_emails)} admin email addresses:")
    for email in admin_emails:
        print(f"  - {email}")
    
    print()


async def demo_full_workflow():
    """Demonstrate complete email notification workflow"""
    print("=== Full Notification Workflow Demo ===\n")
    
    # Create mock components
    from models import User, UserRole
    
    mock_admin_users = [
        Mock(spec=User, email='admin@vedfolnir.com', role=UserRole.ADMIN, is_active=True, email_verified=True)
    ]
    
    mock_session = Mock()
    mock_context_manager = Mock()
    mock_context_manager.__enter__ = Mock(return_value=mock_session)
    mock_context_manager.__exit__ = Mock(return_value=None)
    
    mock_db_manager = Mock()
    mock_db_manager.get_session.return_value = mock_context_manager
    mock_session.query.return_value.filter.return_value.all.return_value = mock_admin_users
    
    mock_email_service = Mock(spec=EmailService)
    mock_email_service.is_configured.return_value = True
    mock_email_service.create_message.return_value = Mock()
    
    mock_redis = Mock()
    mock_redis.get.return_value = None  # No rate limiting
    
    # Create service
    service = StorageEmailNotificationService(
        email_service=mock_email_service,
        db_manager=mock_db_manager,
        redis_client=mock_redis
    )
    
    # Create critical usage metrics
    metrics = create_test_metrics(100.0)  # 100% usage
    
    print("Attempting to send storage limit alert...")
    print(f"Storage Usage: {metrics.usage_percentage}% ({metrics.total_gb:.1f}GB / {metrics.limit_gb:.1f}GB)")
    print(f"Admin Recipients: {len(mock_admin_users)}")
    
    # Test successful send
    mock_email_service.send_email_with_retry = Mock(return_value=True)
    
    result = await service.send_storage_limit_alert(metrics)
    
    if result:
        print("✅ Storage limit alert sent successfully!")
        print("📧 Email service called with:")
        
        # Check what was called
        call_args = mock_email_service.create_message.call_args
        if call_args:
            kwargs = call_args.kwargs
            print(f"  Subject: {kwargs.get('subject', 'N/A')}")
            print(f"  Recipients: {kwargs.get('recipients', [])}")
            print(f"  HTML Body: {'Present' if kwargs.get('html_body') else 'Missing'}")
            print(f"  Text Body: {'Present' if kwargs.get('text_body') else 'Missing'}")
        
        # Check rate limiting was recorded
        if mock_redis.setex.called:
            print("⏰ Rate limiting timestamp recorded")
    else:
        print("❌ Failed to send storage limit alert")
    
    print()


def main():
    """Main demo execution"""
    print("StorageEmailNotificationService Demonstration")
    print("=" * 50)
    print()
    
    try:
        # Run demos
        demo_email_formatting()
        demo_rate_limiting()
        demo_admin_email_retrieval()
        
        # Run async demo
        asyncio.run(demo_full_workflow())
        
        print("=== Demo Complete ===")
        print("\nKey Features Demonstrated:")
        print("✅ Email formatting for different usage levels (MEDIUM/HIGH/CRITICAL)")
        print("✅ Rate limiting to prevent duplicate notifications (24-hour window)")
        print("✅ Admin email address retrieval from database")
        print("✅ Complete notification workflow with error handling")
        print("✅ Template fallback system for robust email generation")
        print("✅ Integration with existing email infrastructure")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)