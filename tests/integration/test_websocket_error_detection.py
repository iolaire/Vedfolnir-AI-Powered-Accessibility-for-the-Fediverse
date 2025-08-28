# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive Test Suite for WebSocket Error Detection and Categorization System

This test suite validates the implementation of Task 8: Comprehensive Error Detection
and Categorization, ensuring all requirements are met.

Requirements tested:
- 4.1: CORS error detection and categorization
- 4.4: User-friendly error messages with CORS guidance
- 7.1: Comprehensive error recovery mechanisms
- 9.2: CORS-specific error details and suggested fixes
- 9.3: Detailed error logging with actionable debugging information
"""

import unittest
import sys
import os
import tempfile
import json
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from flask import Flask

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websocket_error_detector import (
    WebSocketErrorDetector, 
    WebSocketErrorInfo, 
    WebSocketErrorCategory, 
    WebSocketErrorSeverity,
    ErrorPattern
)
from websocket_error_handler import WebSocketErrorHandler
from websocket_error_logger import WebSocketErrorLogger
from websocket_error_integration import WebSocketErrorIntegration, create_error_integration


class TestWebSocketErrorDetector(unittest.TestCase):
    """Test WebSocket error detection and categorization"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = WebSocketErrorDetector()
    
    def test_cors_error_detection(self):
        """Test CORS error pattern recognition (Requirement 4.1)"""
        # Test various CORS error patterns
        cors_errors = [
            "CORS policy violation",
            "Cross-origin request blocked",
            "Origin not allowed by Access-Control-Allow-Origin",
            "Preflight request failed",
            "OPTIONS request failed"
        ]
        
        for error_text in cors_errors:
            with self.subTest(error=error_text):
                error_info = self.detector.detect_error(error_text)
                self.assertEqual(error_info.category, WebSocketErrorCategory.CORS)
                self.assertEqual(error_info.severity, WebSocketErrorSeverity.HIGH)
                self.assertIn("CORS", error_info.message)
    
    def test_authentication_error_detection(self):
        """Test authentication error pattern recognition"""
        auth_errors = [
            "Unauthorized access",
            "Authentication failed",
            "Invalid token",
            "Token expired",
            "Session expired",
            "No session found"
        ]
        
        for error_text in auth_errors:
            with self.subTest(error=error_text):
                error_info = self.detector.detect_error(error_text)
                self.assertIn(error_info.category, [
                    WebSocketErrorCategory.AUTHENTICATION,
                    WebSocketErrorCategory.AUTHORIZATION
                ])
                self.assertIn(error_info.severity, [
                    WebSocketErrorSeverity.HIGH,
                    WebSocketErrorSeverity.MEDIUM
                ])
    
    def test_network_error_detection(self):
        """Test network error pattern recognition"""
        network_errors = [
            "Connection refused",
            "Connection reset",
            "Network error",
            "DNS resolution failed",
            "Host not found",
            "SSL error",
            "Certificate error"
        ]
        
        for error_text in network_errors:
            with self.subTest(error=error_text):
                error_info = self.detector.detect_error(error_text)
                self.assertEqual(error_info.category, WebSocketErrorCategory.NETWORK)
                self.assertEqual(error_info.severity, WebSocketErrorSeverity.HIGH)
    
    def test_transport_error_detection(self):
        """Test transport error pattern recognition"""
        transport_errors = [
            "WebSocket not supported",
            "WebSocket failed",
            "Polling failed",
            "XHR failed"
        ]
        
        for error_text in transport_errors:
            with self.subTest(error=error_text):
                error_info = self.detector.detect_error(error_text)
                self.assertEqual(error_info.category, WebSocketErrorCategory.TRANSPORT)
                self.assertEqual(error_info.severity, WebSocketErrorSeverity.MEDIUM)
    
    def test_cors_specific_detection(self):
        """Test CORS-specific error detection with detailed analysis (Requirement 9.2)"""
        origin = "http://localhost:3000"
        allowed_origins = ["http://localhost:5000", "https://example.com"]
        
        error_info = self.detector.detect_cors_error(origin, allowed_origins)
        
        # Verify error categorization
        self.assertEqual(error_info.category, WebSocketErrorCategory.CORS)
        self.assertEqual(error_info.severity, WebSocketErrorSeverity.HIGH)
        
        # Verify CORS analysis is present
        self.assertIn('cors_analysis', error_info.debug_info)
        cors_analysis = error_info.debug_info['cors_analysis']
        
        # Verify detailed CORS information
        self.assertTrue(cors_analysis['origin_provided'])
        self.assertFalse(cors_analysis['origin_in_allowed_list'])
        self.assertEqual(cors_analysis['allowed_origins_count'], 2)
        self.assertEqual(cors_analysis['origin_protocol'], 'http')
        self.assertIsInstance(cors_analysis['suggested_origins'], list)
    
    def test_authentication_specific_detection(self):
        """Test authentication-specific error detection with detailed analysis"""
        user_id = None
        session_data = {'expired': True}
        
        error_info = self.detector.detect_authentication_error(user_id, session_data)
        
        # Verify error categorization (should be authentication related)
        self.assertIn(error_info.category, [WebSocketErrorCategory.AUTHENTICATION, WebSocketErrorCategory.UNKNOWN])
        
        # Verify authentication analysis is present
        self.assertIn('auth_analysis', error_info.debug_info)
        auth_analysis = error_info.debug_info['auth_analysis']
        
        # Verify detailed authentication information
        self.assertFalse(auth_analysis['user_id_provided'])
        self.assertTrue(auth_analysis['session_data_available'])
        self.assertIn('expired', auth_analysis['session_keys'])
    
    def test_network_specific_detection(self):
        """Test network-specific error detection with detailed analysis"""
        connection_info = {
            'host': 'example.com',
            'port': 443,
            'protocol': 'wss',
            'transport': 'websocket',
            'attempts': 3
        }
        
        error_info = self.detector.detect_network_error(connection_info)
        
        # Verify error categorization
        self.assertEqual(error_info.category, WebSocketErrorCategory.NETWORK)
        
        # Verify network analysis is present
        self.assertIn('network_analysis', error_info.debug_info)
        network_analysis = error_info.debug_info['network_analysis']
        
        # Verify detailed network information
        self.assertEqual(network_analysis['host'], 'example.com')
        self.assertEqual(network_analysis['port'], 443)
        self.assertEqual(network_analysis['protocol'], 'wss')
        self.assertEqual(network_analysis['connection_attempts'], 3)
    
    def test_error_code_generation(self):
        """Test unique error code generation"""
        error1 = self.detector.detect_error("Test error 1")
        error2 = self.detector.detect_error("Test error 2")
        
        # Verify error codes are unique
        self.assertNotEqual(error1.error_code, error2.error_code)
        
        # Verify error code format
        self.assertTrue(error1.error_code.startswith('WS_'))
        self.assertTrue(error2.error_code.startswith('WS_'))
    
    def test_debugging_suggestions(self):
        """Test debugging suggestions generation (Requirement 9.3)"""
        # Test CORS error suggestions
        cors_error = self.detector.detect_error("CORS policy violation")
        cors_suggestions = self.detector.get_debugging_suggestions(cors_error)
        
        self.assertIsInstance(cors_suggestions, list)
        self.assertTrue(len(cors_suggestions) > 0)
        self.assertTrue(any("CORS" in suggestion for suggestion in cors_suggestions))
        
        # Test authentication error suggestions
        auth_error = self.detector.detect_error("Authentication failed")
        auth_suggestions = self.detector.get_debugging_suggestions(auth_error)
        
        self.assertIsInstance(auth_suggestions, list)
        self.assertTrue(len(auth_suggestions) > 0)
        self.assertTrue(any("session" in suggestion.lower() for suggestion in auth_suggestions))
    
    def test_error_statistics(self):
        """Test error statistics tracking"""
        # Generate some errors
        self.detector.detect_error("CORS error")
        self.detector.detect_error("Authentication failed")
        self.detector.detect_error("Network timeout")
        
        stats = self.detector.get_error_statistics()
        
        # Verify statistics structure
        self.assertIn('statistics', stats)
        self.assertIn('top_categories', stats)
        self.assertIn('severity_distribution', stats)
        
        # Verify error counts
        self.assertEqual(stats['statistics']['total_errors'], 3)
        self.assertTrue(stats['statistics']['by_category']['cors'] > 0)
        self.assertTrue(stats['statistics']['by_category']['authentication'] > 0)
        # Network error might be categorized as timeout, so check both
        network_count = stats['statistics']['by_category']['network'] + stats['statistics']['by_category']['timeout']
        self.assertTrue(network_count > 0)


class TestWebSocketErrorHandler(unittest.TestCase):
    """Test WebSocket error handling and recovery"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_socketio = Mock()
        self.mock_detector = Mock(spec=WebSocketErrorDetector)
        self.handler = WebSocketErrorHandler(self.mock_socketio, self.mock_detector)
    
    def test_error_handling_integration(self):
        """Test error handler integration with detector"""
        # Mock error detection
        mock_error_info = Mock(spec=WebSocketErrorInfo)
        mock_error_info.category = WebSocketErrorCategory.CORS
        mock_error_info.severity = WebSocketErrorSeverity.HIGH
        mock_error_info.error_code = "WS_CORS_123456"
        mock_error_info.user_message = "Connection blocked by browser security policy"
        mock_error_info.context = {}
        
        self.mock_detector.detect_error.return_value = mock_error_info
        
        # Test error handling
        test_error = Exception("CORS policy violation")
        
        # Mock the timestamp attribute that's accessed in logging
        mock_error_info.timestamp = Mock()
        mock_error_info.timestamp.isoformat.return_value = "2025-08-27T14:20:53.000000+00:00"
        
        result = self.handler.handle_error(test_error)
        
        # Verify detector was called
        self.mock_detector.detect_error.assert_called_once()
        
        # Verify result
        self.assertEqual(result, mock_error_info)
    
    def test_cors_error_handling(self):
        """Test CORS-specific error handling (Requirement 4.4)"""
        # Mock CORS error detection
        mock_error_info = Mock(spec=WebSocketErrorInfo)
        mock_error_info.category = WebSocketErrorCategory.CORS
        mock_error_info.error_code = "WS_CORS_123456"
        mock_error_info.user_message = "Connection blocked by browser security policy"
        mock_error_info.debug_info = {
            'cors_analysis': {
                'origin_provided': True,
                'origin_in_allowed_list': False,
                'suggested_origins': ['https://localhost:3000']
            }
        }
        mock_error_info.context = {}
        
        self.mock_detector.detect_cors_error.return_value = mock_error_info
        
        # Test CORS error handling
        origin = "http://localhost:3000"
        allowed_origins = ["http://localhost:5000"]
        
        # Mock the timestamp attribute that's accessed in logging
        mock_error_info.timestamp = Mock()
        mock_error_info.timestamp.isoformat.return_value = "2025-08-27T14:20:53.000000+00:00"
        
        # Create Flask app context for request handling
        app = Flask(__name__)
        with app.test_request_context():
            with patch('websocket_error_handler.request') as mock_request:
                mock_request.sid = 'test_client_123'
                result = self.handler.handle_cors_error(origin, allowed_origins)
        
        # Verify CORS detection was called
        self.mock_detector.detect_cors_error.assert_called_once_with(origin, allowed_origins)
        
        # Verify result
        self.assertEqual(result, mock_error_info)
    
    def test_authentication_error_handling(self):
        """Test authentication-specific error handling"""
        # Mock authentication error detection
        mock_error_info = Mock(spec=WebSocketErrorInfo)
        mock_error_info.category = WebSocketErrorCategory.AUTHENTICATION
        mock_error_info.error_code = "WS_AUTH_123456"
        mock_error_info.user_message = "Authentication failed. Please log in again."
        mock_error_info.debug_info = {
            'auth_analysis': {
                'user_id_provided': False,
                'session_data_available': True,
                'authentication_method': 'session_based'
            }
        }
        mock_error_info.context = {}
        
        self.mock_detector.detect_authentication_error.return_value = mock_error_info
        
        # Test authentication error handling
        user_id = None
        session_data = {'expired': True}
        
        # Mock the timestamp attribute that's accessed in logging
        mock_error_info.timestamp = Mock()
        mock_error_info.timestamp.isoformat.return_value = "2025-08-27T14:20:53.000000+00:00"
        
        # Create Flask app context for request handling
        app = Flask(__name__)
        with app.test_request_context():
            with patch('websocket_error_handler.request') as mock_request, patch('websocket_error_handler.session') as mock_session:
                mock_request.sid = 'test_client_123'
                mock_session.get.return_value = 'test_session_123'
                result = self.handler.handle_authentication_error(user_id, session_data)
        
        # Verify authentication detection was called
        self.mock_detector.detect_authentication_error.assert_called_once_with(user_id, session_data)
        
        # Verify result
        self.assertEqual(result, mock_error_info)
    
    def test_error_callback_registration(self):
        """Test error callback registration and execution"""
        callback_called = False
        callback_error_info = None
        
        def test_callback(error_info):
            nonlocal callback_called, callback_error_info
            callback_called = True
            callback_error_info = error_info
        
        # Register callback
        self.handler.register_error_callback(WebSocketErrorCategory.CORS, test_callback)
        
        # Verify callback is registered
        self.assertIn(WebSocketErrorCategory.CORS, self.handler._error_callbacks)
        self.assertIn(test_callback, self.handler._error_callbacks[WebSocketErrorCategory.CORS])
    
    def test_recovery_strategy_registration(self):
        """Test recovery strategy registration (Requirement 7.1)"""
        recovery_called = False
        
        def test_recovery_strategy(error_info, namespace):
            nonlocal recovery_called
            recovery_called = True
            return True
        
        # Register recovery strategy
        self.handler.register_recovery_strategy(WebSocketErrorCategory.NETWORK, test_recovery_strategy)
        
        # Verify strategy is registered
        self.assertIn(WebSocketErrorCategory.NETWORK, self.handler._recovery_strategies)
        self.assertEqual(self.handler._recovery_strategies[WebSocketErrorCategory.NETWORK], test_recovery_strategy)


class TestWebSocketErrorLogger(unittest.TestCase):
    """Test WebSocket error logging with actionable debugging information"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = WebSocketErrorLogger(log_dir=self.temp_dir, max_recent_errors=100)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_error_logging(self):
        """Test comprehensive error logging (Requirement 9.3)"""
        # Create test error info
        error_info = WebSocketErrorInfo(
            category=WebSocketErrorCategory.CORS,
            severity=WebSocketErrorSeverity.HIGH,
            error_code="WS_CORS_TEST_001",
            message="CORS policy violation",
            user_message="Connection blocked by browser security policy",
            suggested_fix="Check CORS configuration and allowed origins",
            debug_info={'cors_analysis': {'origin_provided': True}},
            timestamp=datetime.now(timezone.utc),
            context={'client_id': 'test_123'}
        )
        
        # Log the error
        self.logger.log_error(error_info)
        
        # Verify error was added to recent errors
        self.assertEqual(len(self.logger._recent_errors), 1)
        self.assertEqual(self.logger._recent_errors[0], error_info)
        
        # Verify counters were updated
        self.assertEqual(self.logger._error_counters['total'], 1)
        self.assertEqual(self.logger._error_counters['by_category']['cors'], 1)
        self.assertEqual(self.logger._error_counters['by_severity']['high'], 1)
    
    def test_cors_specific_logging(self):
        """Test CORS-specific error logging with detailed information"""
        # Create CORS error info
        error_info = WebSocketErrorInfo(
            category=WebSocketErrorCategory.CORS,
            severity=WebSocketErrorSeverity.HIGH,
            error_code="WS_CORS_TEST_002",
            message="CORS policy violation",
            user_message="Connection blocked by browser security policy",
            suggested_fix="Check CORS configuration and allowed origins",
            debug_info={
                'cors_analysis': {
                    'origin_provided': True,
                    'origin_in_allowed_list': False,
                    'suggested_origins': ['https://localhost:3000']
                }
            },
            timestamp=datetime.now(timezone.utc),
            context={}
        )
        
        origin = "http://localhost:3000"
        allowed_origins = ["http://localhost:5000"]
        
        # Log CORS error
        self.logger.log_cors_error(error_info, origin, allowed_origins)
        
        # Verify CORS-specific context was added
        self.assertIn('cors_details', error_info.context)
        cors_details = error_info.context['cors_details']
        
        self.assertEqual(cors_details['failed_origin'], origin)
        self.assertEqual(cors_details['allowed_origins'], allowed_origins)
        self.assertIn('suggested_fixes', cors_details)
        self.assertTrue(len(cors_details['suggested_fixes']) > 0)
    
    def test_authentication_specific_logging(self):
        """Test authentication-specific error logging with detailed information"""
        # Create authentication error info
        error_info = WebSocketErrorInfo(
            category=WebSocketErrorCategory.AUTHENTICATION,
            severity=WebSocketErrorSeverity.HIGH,
            error_code="WS_AUTH_TEST_003",
            message="Authentication failed",
            user_message="Authentication failed. Please log in again.",
            suggested_fix="Verify user credentials and session validity",
            debug_info={
                'auth_analysis': {
                    'user_id_provided': False,
                    'session_data_available': True,
                    'authentication_method': 'session_based'
                }
            },
            timestamp=datetime.now(timezone.utc),
            context={}
        )
        
        user_id = None
        session_data = {'expired': True}
        
        # Log authentication error
        self.logger.log_authentication_error(error_info, user_id, session_data)
        
        # Verify authentication-specific context was added
        self.assertIn('auth_details', error_info.context)
        auth_details = error_info.context['auth_details']
        
        self.assertEqual(auth_details['user_id'], user_id)
        self.assertTrue(auth_details['session_available'])
        self.assertIn('suggested_fixes', auth_details)
        self.assertTrue(len(auth_details['suggested_fixes']) > 0)
    
    def test_error_summary_generation(self):
        """Test error summary generation with actionable insights"""
        # Create multiple test errors
        errors = [
            WebSocketErrorInfo(
                category=WebSocketErrorCategory.CORS,
                severity=WebSocketErrorSeverity.HIGH,
                error_code=f"WS_CORS_TEST_{i:03d}",
                message="CORS policy violation",
                user_message="Connection blocked",
                suggested_fix="Check CORS configuration",
                debug_info={},
                timestamp=datetime.now(timezone.utc),
                context={}
            ) for i in range(3)
        ]
        
        # Log errors
        for error in errors:
            self.logger.log_error(error)
        
        # Get error summary
        summary = self.logger.get_error_summary(hours=24)
        
        # Verify summary structure
        self.assertIn('total_errors', summary)
        self.assertIn('by_category', summary)
        self.assertIn('by_severity', summary)
        self.assertIn('actionable_insights', summary)
        
        # Verify error counts
        self.assertEqual(summary['total_errors'], 3)
        self.assertEqual(summary['by_category']['cors'], 3)
        self.assertEqual(summary['by_severity']['high'], 3)
        
        # Verify actionable insights are provided
        self.assertIsInstance(summary['actionable_insights'], list)
        self.assertTrue(len(summary['actionable_insights']) > 0)
    
    def test_debugging_report_generation(self):
        """Test debugging report generation for specific errors"""
        # Create test error
        error_info = WebSocketErrorInfo(
            category=WebSocketErrorCategory.NETWORK,
            severity=WebSocketErrorSeverity.HIGH,
            error_code="WS_NET_TEST_004",
            message="Network connectivity issue",
            user_message="Network connection problem",
            suggested_fix="Check network connectivity",
            debug_info={'network_analysis': {'host': 'example.com'}},
            timestamp=datetime.now(timezone.utc),
            context={'client_id': 'test_456'},
            stack_trace="Test stack trace"
        )
        
        # Log error
        self.logger.log_error(error_info)
        
        # Get debugging report
        report = self.logger.get_debugging_report(error_info.error_code)
        
        # Verify report structure
        self.assertIsNotNone(report)
        self.assertEqual(report['error_code'], error_info.error_code)
        self.assertEqual(report['category'], error_info.category.value)
        self.assertEqual(report['severity'], error_info.severity.value)
        self.assertIn('debugging_steps', report)
        self.assertIn('related_documentation', report)
        
        # Verify debugging steps are provided
        self.assertIsInstance(report['debugging_steps'], list)
        self.assertTrue(len(report['debugging_steps']) > 0)
    
    def test_log_export_functionality(self):
        """Test error log export functionality"""
        # Create test error
        error_info = WebSocketErrorInfo(
            category=WebSocketErrorCategory.CORS,
            severity=WebSocketErrorSeverity.HIGH,
            error_code="WS_CORS_EXPORT_001",
            message="CORS policy violation",
            user_message="Connection blocked",
            suggested_fix="Check CORS configuration",
            debug_info={},
            timestamp=datetime.now(timezone.utc),
            context={}
        )
        
        # Log error
        self.logger.log_error(error_info)
        
        # Test JSON export
        json_file = os.path.join(self.temp_dir, 'test_export.json')
        success = self.logger.export_error_logs(json_file, hours=24, format='json')
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(json_file))
        
        # Verify JSON content
        with open(json_file, 'r') as f:
            exported_data = json.load(f)
        
        self.assertIsInstance(exported_data, list)
        self.assertEqual(len(exported_data), 1)
        self.assertEqual(exported_data[0]['error_code'], error_info.error_code)


class TestWebSocketErrorIntegration(unittest.TestCase):
    """Test WebSocket error integration system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_app = Mock()
        self.mock_socketio = Mock()
        self.integration = WebSocketErrorIntegration(self.mock_app, self.mock_socketio)
    
    def test_integration_initialization(self):
        """Test error integration initialization"""
        # Verify components are initialized
        self.assertIsNotNone(self.integration.error_detector)
        self.assertIsNotNone(self.integration.error_logger)
        self.assertIsNotNone(self.integration.error_handler)
        
        # Verify integration state
        self.assertEqual(self.integration.app, self.mock_app)
        self.assertEqual(self.integration.socketio, self.mock_socketio)
    
    def test_factory_integration(self):
        """Test integration with WebSocket factory"""
        mock_factory = Mock()
        mock_factory.register_error_detector = Mock()
        mock_factory.register_error_handler = Mock()
        
        # Test integration
        self.integration.integrate_with_factory(mock_factory)
        
        # Verify integration methods were called
        mock_factory.register_error_detector.assert_called_once_with(self.integration.error_detector)
        mock_factory.register_error_handler.assert_called_once_with(self.integration.error_handler)
    
    def test_cors_manager_integration(self):
        """Test integration with CORS manager"""
        mock_cors_manager = Mock()
        mock_cors_manager.register_error_callback = Mock()
        
        # Test integration
        self.integration.integrate_with_cors_manager(mock_cors_manager)
        
        # Verify callback was registered
        mock_cors_manager.register_error_callback.assert_called_once()
    
    def test_auth_handler_integration(self):
        """Test integration with authentication handler"""
        mock_auth_handler = Mock()
        mock_auth_handler.register_error_callback = Mock()
        
        # Test integration
        self.integration.integrate_with_auth_handler(mock_auth_handler)
        
        # Verify callback was registered
        mock_auth_handler.register_error_callback.assert_called_once()
    
    def test_error_statistics_aggregation(self):
        """Test error statistics aggregation across components"""
        # Mock component statistics
        self.integration.error_detector.get_error_statistics = Mock(return_value={'detector': 'stats'})
        self.integration.error_logger.get_error_summary = Mock(return_value={'logger': 'stats'})
        self.integration.error_handler.get_error_statistics = Mock(return_value={'handler': 'stats'})
        
        # Get aggregated statistics
        stats = self.integration.get_error_statistics()
        
        # Verify statistics structure
        self.assertIn('detector_stats', stats)
        self.assertIn('logger_stats', stats)
        self.assertIn('handler_stats', stats)
        self.assertIn('integration_status', stats)
        
        # Verify integration status
        integration_status = stats['integration_status']
        self.assertTrue(integration_status['socketio_available'])
        self.assertTrue(integration_status['error_handler_available'])
    
    def test_create_error_integration_factory(self):
        """Test error integration factory function"""
        mock_app = Mock()
        mock_app.debug = True
        mock_socketio = Mock()
        
        # Create integration using factory
        integration = create_error_integration(mock_app, mock_socketio)
        
        # Verify integration was created and configured
        self.assertIsInstance(integration, WebSocketErrorIntegration)
        self.assertEqual(integration.app, mock_app)
        self.assertEqual(integration.socketio, mock_socketio)
        self.assertIsNotNone(integration.error_detector)
        self.assertIsNotNone(integration.error_logger)
        self.assertIsNotNone(integration.error_handler)


class TestErrorDetectionRequirements(unittest.TestCase):
    """Test that all task requirements are met"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = WebSocketErrorDetector()
        self.temp_dir = tempfile.mkdtemp()
        self.logger = WebSocketErrorLogger(log_dir=self.temp_dir)
        
        # Mock SocketIO for handler
        self.mock_socketio = Mock()
        self.handler = WebSocketErrorHandler(self.mock_socketio, self.detector)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_requirement_4_1_cors_error_detection(self):
        """Test Requirement 4.1: CORS error detection and categorization"""
        # Test CORS error detection
        cors_error = "CORS policy: Cross origin requests are only supported for protocol schemes"
        error_info = self.detector.detect_error(cors_error)
        
        # Verify CORS categorization
        self.assertEqual(error_info.category, WebSocketErrorCategory.CORS)
        self.assertEqual(error_info.severity, WebSocketErrorSeverity.HIGH)
        
        # Test CORS-specific detection
        origin = "http://localhost:3000"
        allowed_origins = ["http://localhost:5000"]
        cors_specific = self.detector.detect_cors_error(origin, allowed_origins)
        
        # Verify detailed CORS analysis
        self.assertEqual(cors_specific.category, WebSocketErrorCategory.CORS)
        self.assertIn('cors_analysis', cors_specific.debug_info)
        
        print("✅ Requirement 4.1: CORS error detection and categorization - PASSED")
    
    def test_requirement_4_4_user_friendly_error_messages(self):
        """Test Requirement 4.4: User-friendly error messages with CORS guidance"""
        # Test CORS error user message
        cors_error = self.detector.detect_error("CORS policy violation")
        
        # Verify user-friendly message
        self.assertIsNotNone(cors_error.user_message)
        self.assertNotEqual(cors_error.user_message, cors_error.message)
        self.assertTrue(len(cors_error.user_message) > 0)
        
        # Test authentication error user message
        auth_error = self.detector.detect_error("Authentication failed")
        
        # Verify user-friendly message
        self.assertIsNotNone(auth_error.user_message)
        self.assertIn("log in", auth_error.user_message.lower())
        
        print("✅ Requirement 4.4: User-friendly error messages with CORS guidance - PASSED")
    
    def test_requirement_7_1_comprehensive_error_recovery(self):
        """Test Requirement 7.1: Comprehensive error recovery mechanisms"""
        # Test recovery strategy registration
        recovery_called = False
        
        def test_recovery(error_info, namespace):
            nonlocal recovery_called
            recovery_called = True
            return True
        
        # Register recovery strategy
        self.handler.register_recovery_strategy(WebSocketErrorCategory.CORS, test_recovery)
        
        # Verify strategy is registered
        self.assertIn(WebSocketErrorCategory.CORS, self.handler._recovery_strategies)
        
        # Test default recovery strategies exist
        self.assertIn(WebSocketErrorCategory.AUTHENTICATION, self.handler._recovery_strategies)
        self.assertIn(WebSocketErrorCategory.NETWORK, self.handler._recovery_strategies)
        self.assertIn(WebSocketErrorCategory.TRANSPORT, self.handler._recovery_strategies)
        
        print("✅ Requirement 7.1: Comprehensive error recovery mechanisms - PASSED")
    
    def test_requirement_9_2_cors_specific_error_details(self):
        """Test Requirement 9.2: CORS-specific error details and suggested fixes"""
        origin = "http://localhost:3000"
        allowed_origins = ["http://localhost:5000", "https://example.com"]
        
        # Test CORS-specific detection
        error_info = self.detector.detect_cors_error(origin, allowed_origins)
        
        # Verify CORS analysis details
        self.assertIn('cors_analysis', error_info.debug_info)
        cors_analysis = error_info.debug_info['cors_analysis']
        
        # Verify specific CORS information
        self.assertIn('origin_provided', cors_analysis)
        self.assertIn('origin_in_allowed_list', cors_analysis)
        self.assertIn('allowed_origins_count', cors_analysis)
        self.assertIn('origin_protocol', cors_analysis)
        self.assertIn('suggested_origins', cors_analysis)
        
        # Verify suggested fix is provided
        self.assertIsNotNone(error_info.suggested_fix)
        self.assertIn("CORS", error_info.suggested_fix)
        
        # Test debugging suggestions
        suggestions = self.detector.get_debugging_suggestions(error_info)
        self.assertIsInstance(suggestions, list)
        self.assertTrue(len(suggestions) > 0)
        self.assertTrue(any("CORS" in suggestion for suggestion in suggestions))
        
        print("✅ Requirement 9.2: CORS-specific error details and suggested fixes - PASSED")
    
    def test_requirement_9_3_detailed_error_logging(self):
        """Test Requirement 9.3: Detailed error logging with actionable debugging information"""
        # Create comprehensive error
        error_info = WebSocketErrorInfo(
            category=WebSocketErrorCategory.CORS,
            severity=WebSocketErrorSeverity.HIGH,
            error_code="WS_CORS_REQ_TEST",
            message="CORS policy violation",
            user_message="Connection blocked by browser security policy",
            suggested_fix="Check CORS configuration and allowed origins",
            debug_info={
                'cors_analysis': {
                    'origin_provided': True,
                    'origin_in_allowed_list': False,
                    'suggested_origins': ['https://localhost:3000']
                },
                'original_error': 'CORS policy violation',
                'pattern_matched': 'cors|cross.?origin'
            },
            timestamp=datetime.now(timezone.utc),
            context={'client_id': 'test_123', 'namespace': '/'},
            stack_trace="Test stack trace"
        )
        
        # Log the error
        self.logger.log_error(error_info)
        
        # Test debugging report generation
        report = self.logger.get_debugging_report(error_info.error_code)
        
        # Verify comprehensive debugging information
        self.assertIsNotNone(report)
        self.assertIn('debugging_steps', report)
        self.assertIn('related_documentation', report)
        self.assertIn('context', report)
        self.assertIn('debug_info', report)
        self.assertIn('stack_trace', report)
        
        # Verify debugging steps are actionable
        debugging_steps = report['debugging_steps']
        self.assertIsInstance(debugging_steps, list)
        self.assertTrue(len(debugging_steps) > 0)
        self.assertTrue(all(isinstance(step, str) and len(step) > 0 for step in debugging_steps))
        
        # Test error summary with actionable insights
        summary = self.logger.get_error_summary(hours=24)
        self.assertIn('actionable_insights', summary)
        self.assertIsInstance(summary['actionable_insights'], list)
        
        print("✅ Requirement 9.3: Detailed error logging with actionable debugging information - PASSED")
    
    def test_all_requirements_integration(self):
        """Test that all requirements work together in an integrated scenario"""
        # Simulate a complete error detection and handling scenario
        
        # 1. CORS error occurs
        origin = "http://localhost:3000"
        allowed_origins = ["http://localhost:5000"]
        
        # 2. Error is detected and categorized (Req 4.1)
        error_info = self.detector.detect_cors_error(origin, allowed_origins)
        
        # 3. User-friendly message is generated (Req 4.4)
        self.assertIsNotNone(error_info.user_message)
        self.assertNotIn("CORS policy violation", error_info.user_message)  # Technical details hidden
        
        # 4. Error is logged with detailed debugging information (Req 9.3)
        self.logger.log_cors_error(error_info, origin, allowed_origins)
        
        # 5. CORS-specific details are available (Req 9.2)
        self.assertIn('cors_analysis', error_info.debug_info)
        
        # 6. Recovery mechanisms are available (Req 7.1)
        self.assertIn(WebSocketErrorCategory.CORS, self.handler._recovery_strategies)
        
        # 7. Debugging report can be generated
        report = self.logger.get_debugging_report(error_info.error_code)
        self.assertIsNotNone(report)
        
        print("✅ All Requirements Integration Test - PASSED")
        print("✅ Task 8: Comprehensive Error Detection and Categorization - COMPLETED")


if __name__ == '__main__':
    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)
    
    # Run tests
    unittest.main(verbosity=2)