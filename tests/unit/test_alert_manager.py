# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for the AlertManager system

Tests alert generation, notification delivery, acknowledgment, escalation,
and configuration management for the multi-tenant caption management system.
"""

import unittest
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole, AlertConfiguration, SystemAlert, AlertType, AlertSeverity
from app.services.alerts.components.alert_manager import (
    AlertManager, Alert, AlertThresholds, NotificationChannel, NotificationConfig,
    AlertStatus, alert_job_failure, alert_repeated_failures, alert_resource_low,
    alert_ai_service_down, alert_queue_backup
)

class TestAlertManager(unittest.TestCase):
    """Test AlertManager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create test admin user
        with self.db_manager.get_session() as session:
            # Clean up any existing test users
            session.query(User).filter(User.username.like('test_admin_%')).delete()
            session.commit()
            
            self.admin_user = User(
                username='test_admin_alerts',
                email='admin@test.com',
                role=UserRole.ADMIN
            )
            self.admin_user.set_password('test_password')
            session.add(self.admin_user)
            session.commit()
            self.admin_user_id = self.admin_user.id
        
        # Create AlertManager instance
        self.alert_manager = AlertManager(self.db_manager, self.config)
        
        # Mock notification handlers to avoid actual email/webhook sending
        self.mock_email_handler = Mock()
        self.mock_webhook_handler = Mock()
        
    def tearDown(self):
        """Clean up test environment"""
        with self.db_manager.get_session() as session:
            # Clean up test data
            session.query(User).filter(User.username.like('test_admin_%')).delete()
            session.commit()
    
    def test_alert_manager_initialization(self):
        """Test AlertManager initialization"""
        self.assertIsInstance(self.alert_manager, AlertManager)
        self.assertIsInstance(self.alert_manager.thresholds, AlertThresholds)
        self.assertEqual(len(self.alert_manager.notification_configs), 4)  # email, in_app, webhook, log
        self.assertIn(NotificationChannel.EMAIL, self.alert_manager.notification_configs)
        self.assertIn(NotificationChannel.IN_APP, self.alert_manager.notification_configs)
        self.assertIn(NotificationChannel.WEBHOOK, self.alert_manager.notification_configs)
        self.assertIn(NotificationChannel.LOG, self.alert_manager.notification_configs)
    
    def test_send_alert_basic(self):
        """Test basic alert sending"""
        alert_id = self.alert_manager.send_alert(
            AlertType.JOB_FAILURE,
            "Test job failed",
            AlertSeverity.HIGH,
            {'job_id': 'test_123', 'user_id': 1}
        )
        
        self.assertIsNotNone(alert_id)
        self.assertIn(alert_id, self.alert_manager.active_alerts)
        
        alert = self.alert_manager.active_alerts[alert_id]
        self.assertEqual(alert.alert_type, AlertType.JOB_FAILURE)
        self.assertEqual(alert.severity, AlertSeverity.HIGH)
        self.assertEqual(alert.status, AlertStatus.ACTIVE)
        self.assertEqual(alert.message, "Test job failed")
        self.assertEqual(alert.context['job_id'], 'test_123')
    
    def test_alert_deduplication(self):
        """Test alert deduplication within cooldown period"""
        # Send first alert
        alert_id1 = self.alert_manager.send_alert(
            AlertType.JOB_FAILURE,
            "Duplicate test message",
            AlertSeverity.HIGH
        )
        
        # Send duplicate alert immediately (should update count, not create new)
        alert_id2 = self.alert_manager.send_alert(
            AlertType.JOB_FAILURE,
            "Duplicate test message",
            AlertSeverity.HIGH
        )
        
        self.assertEqual(alert_id1, alert_id2)
        alert = self.alert_manager.active_alerts[alert_id1]
        self.assertEqual(alert.count, 2)
    
    def test_get_active_alerts(self):
        """Test getting active alerts with filtering"""
        # Send alerts of different severities
        self.alert_manager.send_alert(AlertType.JOB_FAILURE, "High alert", AlertSeverity.HIGH)
        self.alert_manager.send_alert(AlertType.AI_SERVICE_DOWN, "Critical alert", AlertSeverity.CRITICAL)
        self.alert_manager.send_alert(AlertType.SYSTEM_ERROR, "Low alert", AlertSeverity.LOW)
        
        # Get all active alerts
        all_alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(all_alerts), 3)
        
        # Get only critical alerts
        critical_alerts = self.alert_manager.get_active_alerts(AlertSeverity.CRITICAL)
        self.assertEqual(len(critical_alerts), 1)
        self.assertEqual(critical_alerts[0].severity, AlertSeverity.CRITICAL)
        
        # Verify sorting (critical first)
        self.assertEqual(all_alerts[0].severity, AlertSeverity.CRITICAL)
    
    def test_acknowledge_alert(self):
        """Test alert acknowledgment"""
        alert_id = self.alert_manager.send_alert(
            AlertType.QUEUE_BACKUP,
            "Queue backed up",
            AlertSeverity.HIGH
        )
        
        # Acknowledge the alert
        success = self.alert_manager.acknowledge_alert(self.admin_user_id, alert_id)
        self.assertTrue(success)
        
        alert = self.alert_manager.active_alerts[alert_id]
        self.assertEqual(alert.status, AlertStatus.ACKNOWLEDGED)
        self.assertEqual(alert.acknowledged_by, self.admin_user_id)
        self.assertIsNotNone(alert.acknowledged_at)
        
        # Try to acknowledge non-existent alert
        success = self.alert_manager.acknowledge_alert(self.admin_user_id, "non_existent")
        self.assertFalse(success)
    
    def test_resolve_alert(self):
        """Test alert resolution"""
        alert_id = self.alert_manager.send_alert(
            AlertType.RESOURCE_LOW,
            "Memory usage high",
            AlertSeverity.CRITICAL
        )
        
        # Resolve the alert
        success = self.alert_manager.resolve_alert(self.admin_user_id, alert_id)
        self.assertTrue(success)
        
        alert = self.alert_manager.active_alerts[alert_id]
        self.assertEqual(alert.status, AlertStatus.RESOLVED)
        self.assertIsNotNone(alert.resolved_at)
    
    def test_configure_alert_thresholds(self):
        """Test alert threshold configuration"""
        new_thresholds = AlertThresholds(
            job_failure_rate=0.2,
            repeated_failure_count=5,
            resource_usage_threshold=0.85,
            queue_backup_threshold=200
        )
        
        success = self.alert_manager.configure_alert_thresholds(self.admin_user_id, new_thresholds)
        self.assertTrue(success)
        
        self.assertEqual(self.alert_manager.thresholds.job_failure_rate, 0.2)
        self.assertEqual(self.alert_manager.thresholds.repeated_failure_count, 5)
        self.assertEqual(self.alert_manager.thresholds.resource_usage_threshold, 0.85)
        self.assertEqual(self.alert_manager.thresholds.queue_backup_threshold, 200)
        
        # Test invalid thresholds
        invalid_thresholds = AlertThresholds(job_failure_rate=1.5)  # > 1.0
        success = self.alert_manager.configure_alert_thresholds(self.admin_user_id, invalid_thresholds)
        self.assertFalse(success)
    
    def test_alert_history(self):
        """Test alert history functionality"""
        # Send multiple alerts
        alert_ids = []
        for i in range(5):
            alert_id = self.alert_manager.send_alert(
                AlertType.JOB_FAILURE,
                f"Test alert {i}",
                AlertSeverity.HIGH
            )
            alert_ids.append(alert_id)
        
        # Get history
        history = self.alert_manager.get_alert_history(limit=3)
        self.assertEqual(len(history), 3)
        
        # Test filtering by type
        history_filtered = self.alert_manager.get_alert_history(
            alert_type=AlertType.JOB_FAILURE,
            limit=10
        )
        self.assertEqual(len(history_filtered), 5)
        
        # Test date filtering
        start_date = datetime.now(timezone.utc) - timedelta(minutes=1)
        history_recent = self.alert_manager.get_alert_history(start_date=start_date)
        self.assertEqual(len(history_recent), 5)
    
    def test_alert_statistics(self):
        """Test alert statistics generation"""
        # Send alerts of different types and severities
        self.alert_manager.send_alert(AlertType.JOB_FAILURE, "Test 1", AlertSeverity.HIGH)
        self.alert_manager.send_alert(AlertType.AI_SERVICE_DOWN, "Test 2", AlertSeverity.CRITICAL)
        self.alert_manager.send_alert(AlertType.QUEUE_BACKUP, "Test 3", AlertSeverity.LOW)
        
        # Acknowledge one alert
        alerts = self.alert_manager.get_active_alerts()
        self.alert_manager.acknowledge_alert(self.admin_user_id, alerts[0].id)
        
        stats = self.alert_manager.get_alert_statistics()
        
        self.assertEqual(stats['total_active'], 3)
        self.assertEqual(stats['active_alerts'], 2)  # One acknowledged
        self.assertEqual(stats['acknowledged_alerts'], 1)
        self.assertEqual(stats['by_severity']['critical'], 1)
        self.assertEqual(stats['by_severity']['high'], 1)
        self.assertEqual(stats['by_severity']['low'], 1)
        self.assertIn('job_failure', stats['by_type'])
        self.assertIn('ai_service_down', stats['by_type'])
    
    @patch('smtplib.SMTP')
    def test_email_notification(self, mock_smtp):
        """Test email notification sending"""
        from app.services.alerts.components.alert_manager import EMAIL_AVAILABLE
        
        if not EMAIL_AVAILABLE:
            self.skipTest("Email functionality not available")
        
        # Configure email notifications
        self.alert_manager.notification_configs[NotificationChannel.EMAIL].config['admin_emails'] = ['admin@test.com']
        
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Send alert that should trigger email
        alert_id = self.alert_manager.send_alert(
            AlertType.AI_SERVICE_DOWN,
            "AI service is down",
            AlertSeverity.CRITICAL
        )
        
        # Verify SMTP was called
        mock_smtp.assert_called_once()
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()
    
    @patch('requests.post')
    def test_webhook_notification(self, mock_post):
        """Test webhook notification sending"""
        # Configure webhook notifications
        webhook_config = self.alert_manager.notification_configs[NotificationChannel.WEBHOOK]
        webhook_config.enabled = True
        webhook_config.config = {
            'webhook_url': 'https://example.com/webhook',
            'webhook_secret': 'test_secret'
        }
        
        # Mock successful webhook response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Send alert that should trigger webhook
        alert_id = self.alert_manager.send_alert(
            AlertType.RESOURCE_LOW,
            "Memory usage critical",
            AlertSeverity.CRITICAL
        )
        
        # Verify webhook was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json']['alert_type'], 'resource_low')
        self.assertEqual(call_args[1]['headers']['X-Webhook-Secret'], 'test_secret')
    
    def test_alert_handler_registration(self):
        """Test alert handler registration and execution"""
        handler_called = False
        test_alert = None
        
        def test_handler(alert):
            nonlocal handler_called, test_alert
            handler_called = True
            test_alert = alert
        
        # Register handler
        self.alert_manager.register_alert_handler(AlertType.JOB_FAILURE, test_handler)
        
        # Send alert
        alert_id = self.alert_manager.send_alert(
            AlertType.JOB_FAILURE,
            "Test handler execution",
            AlertSeverity.HIGH
        )
        
        # Verify handler was called
        self.assertTrue(handler_called)
        self.assertIsNotNone(test_alert)
        self.assertEqual(test_alert.alert_type, AlertType.JOB_FAILURE)
    
    def test_cleanup_old_alerts(self):
        """Test cleanup of old resolved alerts"""
        # Send and resolve an alert
        alert_id = self.alert_manager.send_alert(
            AlertType.JOB_FAILURE,
            "Old alert",
            AlertSeverity.HIGH
        )
        
        # Resolve it
        self.alert_manager.resolve_alert(self.admin_user_id, alert_id)
        
        # Manually set resolved time to be old
        alert = self.alert_manager.active_alerts[alert_id]
        alert.resolved_at = datetime.now(timezone.utc) - timedelta(days=31)
        
        # Run cleanup
        self.alert_manager.cleanup_old_alerts(days_to_keep=30)
        
        # Alert should be removed from active alerts
        self.assertNotIn(alert_id, self.alert_manager.active_alerts)
    
    def test_export_alerts(self):
        """Test alert export functionality"""
        # Send some alerts
        self.alert_manager.send_alert(AlertType.JOB_FAILURE, "Export test 1", AlertSeverity.HIGH)
        self.alert_manager.send_alert(AlertType.AI_SERVICE_DOWN, "Export test 2", AlertSeverity.CRITICAL)
        
        # Export as JSON
        json_export = self.alert_manager.export_alerts(format='json')
        self.assertIsInstance(json_export, str)
        
        # Parse and verify
        alerts_data = json.loads(json_export)
        self.assertEqual(len(alerts_data), 2)
        self.assertIn('alert_type', alerts_data[0])
        self.assertIn('severity', alerts_data[0])
        
        # Export as list
        list_export = self.alert_manager.export_alerts(format='list')
        self.assertIsInstance(list_export, list)
        self.assertEqual(len(list_export), 2)

class TestAlertConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for common alert scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.alert_manager = AlertManager(self.db_manager, self.config)
    
    def test_alert_job_failure(self):
        """Test job failure alert convenience function"""
        alert_job_failure(self.alert_manager, 'job_123', 456, 'Connection timeout')
        
        alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(alerts), 1)
        
        alert = alerts[0]
        self.assertEqual(alert.alert_type, AlertType.JOB_FAILURE)
        self.assertEqual(alert.severity, AlertSeverity.HIGH)
        self.assertIn('job_123', alert.message)
        self.assertEqual(alert.context['job_id'], 'job_123')
        self.assertEqual(alert.context['user_id'], 456)
    
    def test_alert_repeated_failures(self):
        """Test repeated failures alert convenience function"""
        alert_repeated_failures(self.alert_manager, 789, 5)
        
        alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(alerts), 1)
        
        alert = alerts[0]
        self.assertEqual(alert.alert_type, AlertType.REPEATED_FAILURES)
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
        self.assertIn('5 consecutive', alert.message)
        self.assertEqual(alert.context['failure_count'], 5)
    
    def test_alert_resource_low(self):
        """Test resource low alert convenience function"""
        # Test warning level
        alert_resource_low(self.alert_manager, 'memory', 92.5)
        
        alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(alerts), 1)
        
        alert = alerts[0]
        self.assertEqual(alert.alert_type, AlertType.RESOURCE_LOW)
        self.assertEqual(alert.severity, AlertSeverity.HIGH)
        
        # Test critical level
        alert_resource_low(self.alert_manager, 'disk', 97.8)
        
        alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        self.assertEqual(len(critical_alerts), 1)
    
    def test_alert_ai_service_down(self):
        """Test AI service down alert convenience function"""
        alert_ai_service_down(self.alert_manager, 'ollama', 'Connection refused')
        
        alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(alerts), 1)
        
        alert = alerts[0]
        self.assertEqual(alert.alert_type, AlertType.AI_SERVICE_DOWN)
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
        self.assertIn('ollama', alert.message)
        self.assertEqual(alert.context['service_name'], 'ollama')
    
    def test_alert_queue_backup(self):
        """Test queue backup alert convenience function"""
        # Test warning level
        alert_queue_backup(self.alert_manager, 150, 30)
        
        alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(alerts), 1)
        
        alert = alerts[0]
        self.assertEqual(alert.alert_type, AlertType.QUEUE_BACKUP)
        self.assertEqual(alert.severity, AlertSeverity.HIGH)
        
        # Test critical level
        alert_queue_backup(self.alert_manager, 600, 120)
        
        alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        self.assertEqual(len(critical_alerts), 1)

class TestAlertIntegration(unittest.TestCase):
    """Integration tests for alert system with database models"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.alert_manager = AlertManager(self.db_manager, self.config)
        
        # Create test admin user
        with self.db_manager.get_session() as session:
            session.query(User).filter(User.username.like('test_admin_integration_%')).delete()
            session.commit()
            
            import time
            self.admin_user = User(
                username=f'test_admin_integration_{int(time.time())}',
                email='admin@integration.test',
                role=UserRole.ADMIN
            )
            self.admin_user.set_password('test_password')
            session.add(self.admin_user)
            session.commit()
            self.admin_user_id = self.admin_user.id
    
    def tearDown(self):
        """Clean up test environment"""
        with self.db_manager.get_session() as session:
            # Clean up test data
            session.query(AlertConfiguration).filter(
                AlertConfiguration.created_by == self.admin_user_id
            ).delete()
            session.query(SystemAlert).delete()
            session.query(User).filter(User.username.like('test_admin_integration_%')).delete()
            session.commit()
    
    def test_alert_configuration_integration(self):
        """Test integration with AlertConfiguration database model"""
        with self.db_manager.get_session() as session:
            # Create alert configuration
            config = AlertConfiguration(
                alert_type=AlertType.JOB_FAILURE,
                metric_name='failure_rate',
                threshold_value=0.1,
                threshold_operator='>',
                severity=AlertSeverity.CRITICAL,
                created_by=self.admin_user_id
            )
            config.set_notification_channels(['email', 'webhook'])
            session.add(config)
            session.commit()
            
            # Verify configuration
            self.assertEqual(config.get_notification_channels(), ['email', 'webhook'])
            self.assertTrue(config.should_trigger(0.15))
            self.assertFalse(config.should_trigger(0.05))
            self.assertFalse(config.is_in_cooldown())
    
    def test_system_alert_integration(self):
        """Test integration with SystemAlert database model"""
        with self.db_manager.get_session() as session:
            # Create alert configuration first
            config = AlertConfiguration(
                alert_type=AlertType.RESOURCE_LOW,
                metric_name='memory_usage',
                threshold_value=90.0,
                created_by=self.admin_user_id
            )
            session.add(config)
            session.commit()
            
            # Create system alert
            alert = SystemAlert(
                alert_configuration_id=config.id,
                alert_type=AlertType.RESOURCE_LOW,
                severity=AlertSeverity.CRITICAL,
                title='Memory Usage Critical',
                message='Memory usage at 95%',
                metric_value=95.0,
                context_data=json.dumps({'server': 'web-01'})
            )
            session.add(alert)
            session.commit()
            
            # Verify alert
            self.assertEqual(alert.alert_type, AlertType.RESOURCE_LOW)
            self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
            self.assertEqual(alert.status, 'active')
            self.assertIsNotNone(alert.created_at)

if __name__ == '__main__':
    unittest.main()