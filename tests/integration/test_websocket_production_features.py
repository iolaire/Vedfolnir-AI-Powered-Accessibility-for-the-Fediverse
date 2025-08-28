# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Production Features Integration Tests

This module provides comprehensive integration tests for WebSocket production
readiness features including SSL/TLS support, production logging, monitoring,
backup/recovery, and load balancer compatibility.
"""

import os
import ssl
import json
import time
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from websocket_production_config import (
    ProductionWebSocketConfigManager,
    SSLConfig,
    LoadBalancerConfig,
    ProductionLoggingConfig,
    ProductionMonitoringConfig,
    BackupRecoveryConfig
)
from websocket_production_logging import (
    ProductionWebSocketLogger,
    WebSocketProductionErrorHandler,
    WebSocketLogLevel
)
from websocket_production_monitoring import WebSocketProductionMonitor
from websocket_backup_recovery import WebSocketBackupManager, BackupType
from websocket_load_balancer_support import WebSocketLoadBalancerSupport
from websocket_production_factory import ProductionWebSocketFactory


class TestProductionWebSocketConfig(unittest.TestCase):
    """Test production WebSocket configuration"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.temp_dir = tempfile.mkdtemp()
        
        # Set test environment variables
        os.environ.update({
            'WEBSOCKET_PRODUCTION_MODE': 'true',
            'WEBSOCKET_SSL_CERT_FILE': os.path.join(self.temp_dir, 'cert.pem'),
            'WEBSOCKET_SSL_KEY_FILE': os.path.join(self.temp_dir, 'key.pem'),
            'WEBSOCKET_BACKUP_LOCATION': os.path.join(self.temp_dir, 'backups'),
            'WEBSOCKET_LOG_FILE': os.path.join(self.temp_dir, 'websocket.log'),
            'WEBSOCKET_METRICS_ENABLED': 'true',
            'WEBSOCKET_SESSION_AFFINITY': 'true'
        })
    
    def tearDown(self):
        """Clean up test environment"""
        # Clean up environment variables
        test_vars = [
            'WEBSOCKET_PRODUCTION_MODE', 'WEBSOCKET_SSL_CERT_FILE',
            'WEBSOCKET_SSL_KEY_FILE', 'WEBSOCKET_BACKUP_LOCATION',
            'WEBSOCKET_LOG_FILE', 'WEBSOCKET_METRICS_ENABLED',
            'WEBSOCKET_SESSION_AFFINITY'
        ]
        for var in test_vars:
            os.environ.pop(var, None)
    
    def test_production_config_loading(self):
        """Test production configuration loading"""
        config_manager = ProductionWebSocketConfigManager(self.config)
        
        self.assertIsNotNone(config_manager)
        self.assertTrue(config_manager.is_production_mode())
        
        production_config = config_manager.get_production_config()
        self.assertIsNotNone(production_config)
        self.assertTrue(production_config.production_mode)
        self.assertFalse(production_config.debug_mode)
    
    def test_ssl_config_creation(self):
        """Test SSL configuration creation"""
        config_manager = ProductionWebSocketConfigManager(self.config)
        production_config = config_manager.get_production_config()
        
        self.assertIsNotNone(production_config.ssl_config)
        self.assertEqual(production_config.ssl_config.cert_file, 
                        os.path.join(self.temp_dir, 'cert.pem'))
        self.assertEqual(production_config.ssl_config.key_file, 
                        os.path.join(self.temp_dir, 'key.pem'))
        self.assertTrue(production_config.ssl_config.force_https)
    
    def test_load_balancer_config_creation(self):
        """Test load balancer configuration creation"""
        config_manager = ProductionWebSocketConfigManager(self.config)
        production_config = config_manager.get_production_config()
        
        self.assertIsNotNone(production_config.load_balancer_config)
        self.assertTrue(production_config.load_balancer_config.session_affinity_enabled)
        self.assertTrue(production_config.load_balancer_config.trust_proxy_headers)
    
    def test_logging_config_creation(self):
        """Test logging configuration creation"""
        config_manager = ProductionWebSocketConfigManager(self.config)
        production_config = config_manager.get_production_config()
        
        self.assertIsNotNone(production_config.logging_config)
        self.assertEqual(production_config.logging_config.websocket_log_file,
                        os.path.join(self.temp_dir, 'websocket.log'))
        self.assertTrue(production_config.logging_config.json_logging)
    
    def test_monitoring_config_creation(self):
        """Test monitoring configuration creation"""
        config_manager = ProductionWebSocketConfigManager(self.config)
        production_config = config_manager.get_production_config()
        
        self.assertIsNotNone(production_config.monitoring_config)
        self.assertTrue(production_config.monitoring_config.metrics_enabled)
        self.assertTrue(production_config.monitoring_config.performance_monitoring)
    
    def test_backup_config_creation(self):
        """Test backup configuration creation"""
        config_manager = ProductionWebSocketConfigManager(self.config)
        production_config = config_manager.get_production_config()
        
        self.assertIsNotNone(production_config.backup_config)
        self.assertTrue(production_config.backup_config.state_backup_enabled)
        self.assertEqual(production_config.backup_config.backup_location,
                        os.path.join(self.temp_dir, 'backups'))


class TestProductionWebSocketLogging(unittest.TestCase):
    """Test production WebSocket logging"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        self.logging_config = ProductionLoggingConfig(
            websocket_log_file=os.path.join(self.temp_dir, 'websocket.log'),
            json_logging=True,
            structured_logging=True,
            log_rotation_enabled=False  # Disable for testing
        )
        
        self.logger = ProductionWebSocketLogger(self.logging_config)
    
    def test_logger_initialization(self):
        """Test logger initialization"""
        self.assertIsNotNone(self.logger)
        self.assertEqual(self.logger.config, self.logging_config)
    
    def test_connection_event_logging(self):
        """Test connection event logging"""
        self.logger.log_connection_event(
            event_type="test_connection",
            message="Test connection event",
            session_id="test_session",
            user_id=1,
            connection_id="test_conn",
            client_ip="127.0.0.1"
        )
        
        # Verify log file was created
        log_file = Path(self.logging_config.websocket_log_file)
        self.assertTrue(log_file.exists())
    
    def test_security_event_logging(self):
        """Test security event logging"""
        self.logger.log_security_event(
            event_type="test_security",
            message="Test security event",
            session_id="test_session",
            user_id=1,
            connection_id="test_conn",
            client_ip="127.0.0.1",
            error_code="TEST_ERROR",
            level=WebSocketLogLevel.CRITICAL
        )
        
        # Verify log file was created
        log_file = Path(self.logging_config.websocket_log_file)
        self.assertTrue(log_file.exists())
    
    def test_performance_context_logging(self):
        """Test performance context logging"""
        with self.logger.log_performance_context(
            event_type="test_operation",
            message="Test operation",
            session_id="test_session"
        ):
            time.sleep(0.01)  # Simulate work
        
        # Verify log file was created
        log_file = Path(self.logging_config.websocket_log_file)
        self.assertTrue(log_file.exists())
    
    def test_error_handler_initialization(self):
        """Test error handler initialization"""
        error_handler = WebSocketProductionErrorHandler(self.logger)
        self.assertIsNotNone(error_handler)
        self.assertEqual(error_handler.logger, self.logger)
    
    def test_error_handler_connection_error(self):
        """Test error handler connection error handling"""
        error_handler = WebSocketProductionErrorHandler(self.logger)
        
        test_error = Exception("Test connection error")
        error_handler.handle_connection_error(
            error=test_error,
            session_id="test_session",
            user_id=1,
            connection_id="test_conn",
            client_ip="127.0.0.1"
        )
        
        # Verify error was tracked
        error_stats = error_handler.get_error_statistics()
        self.assertIn("Exception", error_stats)
        self.assertEqual(error_stats["Exception"], 1)


class TestProductionWebSocketMonitoring(unittest.TestCase):
    """Test production WebSocket monitoring"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        self.logging_config = ProductionLoggingConfig()
        self.logger = ProductionWebSocketLogger(self.logging_config)
        
        self.monitoring_config = ProductionMonitoringConfig(
            metrics_enabled=True,
            performance_monitoring=True,
            health_checks_enabled=True
        )
        
        self.monitor = WebSocketProductionMonitor(
            self.monitoring_config,
            self.logger
        )
    
    def test_monitor_initialization(self):
        """Test monitor initialization"""
        self.assertIsNotNone(self.monitor)
        self.assertEqual(self.monitor.config, self.monitoring_config)
        self.assertEqual(self.monitor.logger, self.logger)
    
    def test_connection_event_recording(self):
        """Test connection event recording"""
        self.monitor.record_connection_event(
            event_type="connect",
            session_id="test_session",
            user_id=1,
            namespace="/user",
            success=True
        )
        
        metrics = self.monitor.get_connection_metrics()
        self.assertEqual(metrics.total_connections, 1)
        self.assertEqual(metrics.active_connections, 1)
        self.assertEqual(metrics.failed_connections, 0)
    
    def test_message_event_recording(self):
        """Test message event recording"""
        self.monitor.record_message_event(
            event_name="test_event",
            namespace="/user",
            message_size=100,
            processing_time_ms=50.0,
            success=True
        )
        
        metrics = self.monitor.get_message_metrics()
        self.assertEqual(metrics.total_messages, 1)
        self.assertEqual(metrics.failed_messages, 0)
        self.assertIn("test_event", metrics.messages_by_event)
    
    def test_security_event_recording(self):
        """Test security event recording"""
        self.monitor.record_security_event(
            event_type="blocked_connection",
            session_id="test_session",
            user_id=1,
            severity="critical"
        )
        
        metrics = self.monitor.get_security_metrics()
        self.assertEqual(metrics.blocked_connections, 1)
        self.assertIn("blocked_connection", metrics.security_events_by_type)
    
    def test_health_check(self):
        """Test health check functionality"""
        health_result = self.monitor.perform_health_check()
        
        self.assertIsNotNone(health_result)
        self.assertIsNotNone(health_result.status)
        self.assertIsNotNone(health_result.message)
        self.assertIsNotNone(health_result.timestamp)
    
    def test_monitor_operation_context(self):
        """Test monitor operation context"""
        with self.monitor.monitor_operation(
            operation_name="test_operation",
            session_id="test_session",
            user_id=1
        ):
            time.sleep(0.01)  # Simulate work
        
        # Operation should complete without error
        self.assertTrue(True)


class TestWebSocketBackupRecovery(unittest.TestCase):
    """Test WebSocket backup and recovery"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        self.logging_config = ProductionLoggingConfig()
        self.logger = ProductionWebSocketLogger(self.logging_config)
        
        self.backup_config = BackupRecoveryConfig(
            state_backup_enabled=True,
            backup_location=os.path.join(self.temp_dir, 'backups'),
            backup_interval=60,  # 1 minute for testing
            max_backup_files=5
        )
        
        self.backup_manager = WebSocketBackupManager(
            self.backup_config,
            self.logger
        )
    
    def test_backup_manager_initialization(self):
        """Test backup manager initialization"""
        self.assertIsNotNone(self.backup_manager)
        self.assertEqual(self.backup_manager.config, self.backup_config)
        self.assertTrue(Path(self.backup_config.backup_location).exists())
    
    def test_connection_tracking(self):
        """Test connection tracking"""
        self.backup_manager.track_connection(
            session_id="test_session",
            user_id=1,
            connection_id="test_conn",
            namespace="/user",
            client_info={"ip": "127.0.0.1"}
        )
        
        self.assertIn("test_conn", self.backup_manager.active_connections)
        connection_state = self.backup_manager.active_connections["test_conn"]
        self.assertEqual(connection_state.session_id, "test_session")
        self.assertEqual(connection_state.user_id, 1)
    
    def test_connection_untracking(self):
        """Test connection untracking"""
        # First track a connection
        self.backup_manager.track_connection(
            session_id="test_session",
            user_id=1,
            connection_id="test_conn",
            namespace="/user"
        )
        
        # Then untrack it
        self.backup_manager.untrack_connection("test_conn")
        
        self.assertNotIn("test_conn", self.backup_manager.active_connections)
    
    def test_backup_creation(self):
        """Test backup creation"""
        # Track some connections
        self.backup_manager.track_connection(
            session_id="test_session_1",
            user_id=1,
            connection_id="test_conn_1",
            namespace="/user"
        )
        
        self.backup_manager.track_connection(
            session_id="test_session_2",
            user_id=2,
            connection_id="test_conn_2",
            namespace="/admin"
        )
        
        # Create backup
        metadata = self.backup_manager.create_backup(BackupType.FULL)
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.backup_type, BackupType.FULL)
        self.assertEqual(metadata.connection_count, 2)
        self.assertTrue(Path(metadata.file_path).exists())
    
    def test_backup_verification(self):
        """Test backup verification"""
        # Create a backup first
        self.backup_manager.track_connection(
            session_id="test_session",
            user_id=1,
            connection_id="test_conn",
            namespace="/user"
        )
        
        metadata = self.backup_manager.create_backup(BackupType.FULL)
        self.assertIsNotNone(metadata)
        
        # Verify the backup
        is_valid = self.backup_manager.verify_backup(metadata.backup_id)
        self.assertTrue(is_valid)
    
    def test_backup_listing(self):
        """Test backup listing"""
        # Create multiple backups
        self.backup_manager.track_connection(
            session_id="test_session",
            user_id=1,
            connection_id="test_conn",
            namespace="/user"
        )
        
        backup1 = self.backup_manager.create_backup(BackupType.FULL)
        backup2 = self.backup_manager.create_backup(BackupType.INCREMENTAL)
        
        # List backups
        backups = self.backup_manager.list_backups()
        
        self.assertEqual(len(backups), 2)
        backup_ids = [b.backup_id for b in backups]
        self.assertIn(backup1.backup_id, backup_ids)
        self.assertIn(backup2.backup_id, backup_ids)


class TestWebSocketLoadBalancerSupport(unittest.TestCase):
    """Test WebSocket load balancer support"""
    
    def setUp(self):
        """Set up test environment"""
        self.logging_config = ProductionLoggingConfig()
        self.logger = ProductionWebSocketLogger(self.logging_config)
        
        self.load_balancer_config = LoadBalancerConfig(
            session_affinity_enabled=True,
            health_check_path="/websocket/health",
            trust_proxy_headers=True
        )
        
        self.load_balancer_support = WebSocketLoadBalancerSupport(
            self.load_balancer_config,
            self.logger
        )
    
    def test_load_balancer_support_initialization(self):
        """Test load balancer support initialization"""
        self.assertIsNotNone(self.load_balancer_support)
        self.assertEqual(self.load_balancer_support.config, self.load_balancer_config)
        self.assertIsNotNone(self.load_balancer_support.server_id)
    
    def test_connection_registration(self):
        """Test WebSocket connection registration"""
        self.load_balancer_support.register_websocket_connection(
            session_id="test_session",
            connection_id="test_conn",
            user_id=1,
            namespace="/user"
        )
        
        self.assertEqual(self.load_balancer_support.server_instance.connection_count, 1)
    
    def test_connection_unregistration(self):
        """Test WebSocket connection unregistration"""
        # First register a connection
        self.load_balancer_support.register_websocket_connection(
            session_id="test_session",
            connection_id="test_conn",
            user_id=1,
            namespace="/user"
        )
        
        # Then unregister it
        self.load_balancer_support.unregister_websocket_connection(
            session_id="test_session",
            connection_id="test_conn"
        )
        
        self.assertEqual(self.load_balancer_support.server_instance.connection_count, 0)
    
    def test_server_metrics_update(self):
        """Test server metrics update"""
        self.load_balancer_support.update_server_metrics(
            cpu_usage=50.0,
            memory_usage=256.0,
            response_time_ms=100.0,
            error_rate=0.1
        )
        
        self.assertEqual(self.load_balancer_support.server_instance.cpu_usage, 50.0)
        self.assertEqual(self.load_balancer_support.server_instance.memory_usage, 256.0)
        self.assertEqual(self.load_balancer_support.server_instance.response_time_ms, 100.0)
        self.assertEqual(self.load_balancer_support.server_instance.error_rate, 0.1)
    
    def test_health_status(self):
        """Test health status reporting"""
        health_status = self.load_balancer_support.get_health_status()
        
        self.assertIsNotNone(health_status)
        self.assertIn('status', health_status)
        self.assertIn('server_id', health_status)
        self.assertIn('connection_count', health_status)
    
    def test_maintenance_mode(self):
        """Test maintenance mode setting"""
        # Enable maintenance mode
        self.load_balancer_support.set_maintenance_mode(True)
        health_status = self.load_balancer_support.get_health_status()
        self.assertEqual(health_status['status'], 'maintenance')
        
        # Disable maintenance mode
        self.load_balancer_support.set_maintenance_mode(False)
        health_status = self.load_balancer_support.get_health_status()
        self.assertNotEqual(health_status['status'], 'maintenance')


class TestProductionWebSocketFactory(unittest.TestCase):
    """Test production WebSocket factory"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.temp_dir = tempfile.mkdtemp()
        
        # Set test environment variables
        os.environ.update({
            'WEBSOCKET_PRODUCTION_MODE': 'true',
            'WEBSOCKET_BACKUP_LOCATION': os.path.join(self.temp_dir, 'backups'),
            'WEBSOCKET_LOG_FILE': os.path.join(self.temp_dir, 'websocket.log'),
            'WEBSOCKET_METRICS_ENABLED': 'true'
        })
        
        # Mock database and session managers
        self.db_manager = Mock()
        self.session_manager = Mock()
    
    def tearDown(self):
        """Clean up test environment"""
        # Clean up environment variables
        test_vars = [
            'WEBSOCKET_PRODUCTION_MODE', 'WEBSOCKET_BACKUP_LOCATION',
            'WEBSOCKET_LOG_FILE', 'WEBSOCKET_METRICS_ENABLED'
        ]
        for var in test_vars:
            os.environ.pop(var, None)
    
    def test_production_factory_initialization(self):
        """Test production factory initialization"""
        factory = ProductionWebSocketFactory(
            self.config,
            self.db_manager,
            self.session_manager
        )
        
        self.assertIsNotNone(factory)
        self.assertIsNotNone(factory.production_config_manager)
        self.assertTrue(factory.production_config_manager.is_production_mode())
    
    @patch('websocket_production_factory.Flask')
    @patch('websocket_production_factory.SocketIO')
    def test_production_socketio_creation(self, mock_socketio, mock_flask):
        """Test production SocketIO instance creation"""
        # Setup mocks
        mock_app = Mock()
        mock_flask.return_value = mock_app
        mock_socketio_instance = Mock()
        mock_socketio.return_value = mock_socketio_instance
        
        factory = ProductionWebSocketFactory(
            self.config,
            self.db_manager,
            self.session_manager
        )
        
        # Create production SocketIO instance
        socketio = factory.create_production_socketio_instance(mock_app)
        
        self.assertIsNotNone(socketio)
        mock_socketio.assert_called_once()
    
    def test_production_status(self):
        """Test production status reporting"""
        factory = ProductionWebSocketFactory(
            self.config,
            self.db_manager,
            self.session_manager
        )
        
        status = factory.get_production_status()
        
        self.assertIsNotNone(status)
        self.assertIn('timestamp', status)
        self.assertIn('production_mode', status)
        self.assertIn('components', status)
        self.assertTrue(status['production_mode'])


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestProductionWebSocketConfig))
    test_suite.addTest(unittest.makeSuite(TestProductionWebSocketLogging))
    test_suite.addTest(unittest.makeSuite(TestProductionWebSocketMonitoring))
    test_suite.addTest(unittest.makeSuite(TestWebSocketBackupRecovery))
    test_suite.addTest(unittest.makeSuite(TestWebSocketLoadBalancerSupport))
    test_suite.addTest(unittest.makeSuite(TestProductionWebSocketFactory))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)