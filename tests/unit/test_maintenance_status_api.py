# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for MaintenanceStatusAPI

Tests the maintenance status API functionality including status queries,
operation blocking information, and real-time updates.
"""

import unittest
import sys
import os
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.maintenance.components.maintenance_status_api import MaintenanceStatusAPI, MaintenanceStatusResponse, BlockedOperation
from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import MaintenanceStatus, MaintenanceMode


class TestMaintenanceStatusAPI(unittest.TestCase):
    """Test cases for MaintenanceStatusAPI"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock maintenance service
        self.mock_maintenance_service = Mock()
        
        # Create API instance
        self.api = MaintenanceStatusAPI(self.mock_maintenance_service)
        
        # Sample maintenance status
        self.sample_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Scheduled maintenance",
            estimated_duration=30,
            started_at=datetime.now(timezone.utc),
            estimated_completion=datetime.now(timezone.utc) + timedelta(minutes=30),
            enabled_by="admin",
            blocked_operations=["caption_generation", "job_creation"],
            active_jobs_count=5,
            invalidated_sessions=10,
            test_mode=False
        )
    
    def test_get_status_success(self):
        """Test successful status retrieval"""
        # Setup mock
        self.mock_maintenance_service.get_maintenance_status.return_value = self.sample_status
        self.mock_maintenance_service.get_blocked_operations.return_value = ["caption_generation", "job_creation"]
        self.mock_maintenance_service.get_maintenance_message.return_value = "System maintenance in progress"
        
        # Get status
        response = self.api.get_status()
        
        # Verify response
        self.assertIsInstance(response, MaintenanceStatusResponse)
        self.assertTrue(response.is_active)
        self.assertEqual(response.mode, "normal")
        self.assertEqual(response.reason, "Scheduled maintenance")
        self.assertEqual(response.estimated_duration, 30)
        self.assertEqual(response.enabled_by, "admin")
        self.assertEqual(response.blocked_operations, ["caption_generation", "job_creation"])
        self.assertEqual(response.active_jobs_count, 5)
        self.assertEqual(response.invalidated_sessions, 10)
        self.assertFalse(response.test_mode)
        self.assertEqual(response.message, "System maintenance in progress")
        self.assertIsNotNone(response.started_at)
        self.assertIsNotNone(response.estimated_completion)
        self.assertIsNotNone(response.timestamp)
        self.assertGreater(response.response_time_ms, 0)
        self.assertLess(response.response_time_ms, 100)  # Should be under 100ms
    
    def test_get_status_inactive_maintenance(self):
        """Test status retrieval when maintenance is inactive"""
        # Setup mock for inactive maintenance
        inactive_status = MaintenanceStatus(
            is_active=False,
            mode=MaintenanceMode.NORMAL,
            reason=None,
            estimated_duration=None,
            started_at=None,
            estimated_completion=None,
            enabled_by=None,
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        self.mock_maintenance_service.get_maintenance_status.return_value = inactive_status
        self.mock_maintenance_service.get_blocked_operations.return_value = []
        self.mock_maintenance_service.get_maintenance_message.return_value = "System is operating normally."
        
        # Get status
        response = self.api.get_status()
        
        # Verify response
        self.assertFalse(response.is_active)
        self.assertEqual(response.mode, "normal")
        self.assertIsNone(response.reason)
        self.assertIsNone(response.estimated_duration)
        self.assertIsNone(response.enabled_by)
        self.assertEqual(response.blocked_operations, [])
        self.assertEqual(response.active_jobs_count, 0)
        self.assertEqual(response.invalidated_sessions, 0)
        self.assertFalse(response.test_mode)
        self.assertEqual(response.message, "System is operating normally.")
        self.assertIsNone(response.started_at)
        self.assertIsNone(response.estimated_completion)
    
    def test_get_status_error_handling(self):
        """Test status retrieval error handling"""
        # Setup mock to raise exception
        self.mock_maintenance_service.get_maintenance_status.side_effect = Exception("Service error")
        
        # Get status
        response = self.api.get_status()
        
        # Verify error response
        self.assertFalse(response.is_active)
        self.assertEqual(response.mode, "unknown")
        self.assertIsNone(response.reason)
        self.assertEqual(response.blocked_operations, [])
        self.assertEqual(response.message, "Unable to determine maintenance status")
        self.assertGreater(response.response_time_ms, 0)
    
    def test_get_status_performance_requirement(self):
        """Test that status retrieval meets <100ms performance requirement"""
        # Setup mock
        self.mock_maintenance_service.get_maintenance_status.return_value = self.sample_status
        self.mock_maintenance_service.get_blocked_operations.return_value = []
        self.mock_maintenance_service.get_maintenance_message.return_value = "Test message"
        
        # Measure response time
        start_time = time.time()
        response = self.api.get_status()
        end_time = time.time()
        
        actual_response_time = (end_time - start_time) * 1000
        
        # Verify performance requirement
        self.assertLess(actual_response_time, 100, "Status API should respond in under 100ms")
        self.assertLess(response.response_time_ms, 100, "Reported response time should be under 100ms")
    
    @patch('maintenance_operation_classifier.MaintenanceOperationClassifier')
    def test_get_blocked_operations_success(self, mock_classifier_class):
        """Test successful blocked operations retrieval"""
        # Setup mock classifier
        mock_classifier = Mock()
        mock_classifier_class.return_value = mock_classifier
        
        # Import OperationType for mocking
        from app.services.maintenance.components.maintenance_operation_classifier import OperationType
        
        # Setup mock responses
        mock_classifier.is_blocked_operation.side_effect = lambda op_type, mode: op_type in [
            OperationType.CAPTION_GENERATION, OperationType.JOB_CREATION
        ]
        mock_classifier.get_operation_description.side_effect = lambda op_type: {
            OperationType.CAPTION_GENERATION: "AI caption generation",
            OperationType.JOB_CREATION: "Background job creation"
        }.get(op_type, "Unknown operation")
        
        self.mock_maintenance_service.get_maintenance_status.return_value = self.sample_status
        self.mock_maintenance_service.get_maintenance_message.side_effect = lambda op: f"Operation {op} is blocked"
        
        # Get blocked operations
        blocked_ops = self.api.get_blocked_operations()
        
        # Verify response
        self.assertEqual(len(blocked_ops), 2)
        
        # Check first blocked operation
        caption_op = next((op for op in blocked_ops if op.operation_type == "caption_generation"), None)
        self.assertIsNotNone(caption_op)
        self.assertEqual(caption_op.description, "AI caption generation")
        self.assertIsNotNone(caption_op.blocked_since)
        self.assertIn("caption_generation", caption_op.user_message)
        self.assertIsInstance(caption_op.endpoints, list)
        
        # Check second blocked operation
        job_op = next((op for op in blocked_ops if op.operation_type == "job_creation"), None)
        self.assertIsNotNone(job_op)
        self.assertEqual(job_op.description, "Background job creation")
    
    def test_get_blocked_operations_inactive_maintenance(self):
        """Test blocked operations when maintenance is inactive"""
        # Setup inactive maintenance
        inactive_status = MaintenanceStatus(
            is_active=False,
            mode=MaintenanceMode.NORMAL,
            reason=None,
            estimated_duration=None,
            started_at=None,
            estimated_completion=None,
            enabled_by=None,
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        self.mock_maintenance_service.get_maintenance_status.return_value = inactive_status
        
        # Get blocked operations
        blocked_ops = self.api.get_blocked_operations()
        
        # Verify no operations are blocked
        self.assertEqual(len(blocked_ops), 0)
    
    def test_get_maintenance_message_success(self):
        """Test maintenance message retrieval"""
        # Setup mock
        self.mock_maintenance_service.get_maintenance_message.return_value = "Custom maintenance message"
        
        # Get message
        message = self.api.get_maintenance_message("test_operation")
        
        # Verify message
        self.assertEqual(message, "Custom maintenance message")
        self.mock_maintenance_service.get_maintenance_message.assert_called_once_with("test_operation")
    
    def test_get_maintenance_message_error_handling(self):
        """Test maintenance message error handling"""
        # Setup mock to raise exception
        self.mock_maintenance_service.get_maintenance_message.side_effect = Exception("Service error")
        
        # Get message
        message = self.api.get_maintenance_message("test_operation")
        
        # Verify fallback message
        self.assertEqual(message, "System maintenance is in progress. Please try again later.")
    
    def test_subscribe_to_status_changes(self):
        """Test status change subscription"""
        # Create callback
        callback_called = threading.Event()
        received_events = []
        
        def test_callback(event_type, status_response):
            received_events.append((event_type, status_response))
            callback_called.set()
        
        # Subscribe
        subscription_id = self.api.subscribe_to_status_changes(test_callback)
        
        # Verify subscription
        self.assertIsInstance(subscription_id, str)
        self.assertIn(subscription_id, self.api._subscribers)
        
        # Simulate maintenance change
        self.api._handle_maintenance_change("maintenance_enabled", self.sample_status)
        
        # Wait for callback
        callback_called.wait(timeout=1.0)
        
        # Verify callback was called
        self.assertEqual(len(received_events), 1)
        event_type, status_response = received_events[0]
        self.assertEqual(event_type, "maintenance_enabled")
        self.assertIsInstance(status_response, MaintenanceStatusResponse)
        self.assertTrue(status_response.is_active)
    
    def test_unsubscribe_success(self):
        """Test successful unsubscription"""
        # Subscribe first
        callback = Mock()
        subscription_id = self.api.subscribe_to_status_changes(callback)
        
        # Verify subscription exists
        self.assertIn(subscription_id, self.api._subscribers)
        
        # Unsubscribe
        result = self.api.unsubscribe(subscription_id)
        
        # Verify unsubscription
        self.assertTrue(result)
        self.assertNotIn(subscription_id, self.api._subscribers)
    
    def test_unsubscribe_nonexistent(self):
        """Test unsubscription of nonexistent subscription"""
        # Try to unsubscribe nonexistent subscription
        result = self.api.unsubscribe("nonexistent-id")
        
        # Verify failure
        self.assertFalse(result)
    
    def test_get_api_stats(self):
        """Test API statistics retrieval"""
        # Add some subscribers
        callback1 = Mock()
        callback2 = Mock()
        self.api.subscribe_to_status_changes(callback1)
        self.api.subscribe_to_status_changes(callback2)
        
        # Make some status requests to generate stats
        self.mock_maintenance_service.get_maintenance_status.return_value = self.sample_status
        self.mock_maintenance_service.get_blocked_operations.return_value = []
        self.mock_maintenance_service.get_maintenance_message.return_value = "Test"
        
        self.api.get_status()
        self.api.get_status()
        
        # Get stats
        stats = self.api.get_api_stats()
        
        # Verify stats
        self.assertIn('performance', stats)
        self.assertIn('subscribers_count', stats)
        self.assertIn('maintenance_subscription_active', stats)
        
        # Check performance stats
        perf_stats = stats['performance']
        self.assertEqual(perf_stats['total_requests'], 2)
        self.assertGreater(perf_stats['average_response_time'], 0)
        self.assertGreater(perf_stats['max_response_time'], 0)
        self.assertLess(perf_stats['min_response_time'], float('inf'))
        self.assertIsNotNone(perf_stats['last_request_time'])
        
        # Check subscriber count
        self.assertEqual(stats['subscribers_count'], 2)
        
        # Check maintenance subscription
        self.assertTrue(stats['maintenance_subscription_active'])
    
    def test_performance_stats_tracking(self):
        """Test performance statistics tracking"""
        # Setup mock
        self.mock_maintenance_service.get_maintenance_status.return_value = self.sample_status
        self.mock_maintenance_service.get_blocked_operations.return_value = []
        self.mock_maintenance_service.get_maintenance_message.return_value = "Test"
        
        # Make multiple requests
        for _ in range(5):
            self.api.get_status()
        
        # Check performance stats
        stats = self.api.get_api_stats()
        perf_stats = stats['performance']
        
        self.assertEqual(perf_stats['total_requests'], 5)
        self.assertGreater(perf_stats['average_response_time'], 0)
        self.assertGreaterEqual(perf_stats['max_response_time'], perf_stats['min_response_time'])
        self.assertLessEqual(perf_stats['min_response_time'], perf_stats['average_response_time'])
        self.assertLessEqual(perf_stats['average_response_time'], perf_stats['max_response_time'])
    
    def test_subscription_error_handling(self):
        """Test subscription callback error handling"""
        # Create callback that raises exception
        def error_callback(event_type, status_response):
            raise Exception("Callback error")
        
        # Create normal callback
        normal_callback_called = threading.Event()
        def normal_callback(event_type, status_response):
            normal_callback_called.set()
        
        # Subscribe both callbacks
        self.api.subscribe_to_status_changes(error_callback)
        self.api.subscribe_to_status_changes(normal_callback)
        
        # Simulate maintenance change
        self.api._handle_maintenance_change("test_event", self.sample_status)
        
        # Wait for normal callback
        normal_callback_called.wait(timeout=1.0)
        
        # Verify normal callback was called despite error in other callback
        self.assertTrue(normal_callback_called.is_set())
    
    def test_endpoints_for_operation_type(self):
        """Test endpoint examples for operation types"""
        from app.services.maintenance.components.maintenance_operation_classifier import OperationType
        
        # Test caption generation endpoints
        endpoints = self.api._get_endpoints_for_operation_type(OperationType.CAPTION_GENERATION)
        self.assertIsInstance(endpoints, list)
        self.assertIn("/start_caption_generation", endpoints)
        self.assertIn("/api/caption/generate", endpoints)
        
        # Test job creation endpoints
        endpoints = self.api._get_endpoints_for_operation_type(OperationType.JOB_CREATION)
        self.assertIn("/api/jobs", endpoints)
        self.assertIn("/create_job", endpoints)
        
        # Test platform operations endpoints
        endpoints = self.api._get_endpoints_for_operation_type(OperationType.PLATFORM_OPERATIONS)
        self.assertIn("/platform_management", endpoints)
        self.assertIn("/api/switch_platform", endpoints)
    
    def test_maintenance_service_subscription(self):
        """Test subscription to maintenance service changes"""
        # Verify that API subscribed to maintenance service
        self.mock_maintenance_service.subscribe_to_changes.assert_called_once()
        
        # Get the callback that was registered
        callback = self.mock_maintenance_service.subscribe_to_changes.call_args[0][0]
        
        # Verify it's the correct method
        self.assertEqual(callback, self.api._handle_maintenance_change)
    
    def test_response_format_consistency(self):
        """Test that response format is consistent"""
        # Setup mock
        self.mock_maintenance_service.get_maintenance_status.return_value = self.sample_status
        self.mock_maintenance_service.get_blocked_operations.return_value = ["test_op"]
        self.mock_maintenance_service.get_maintenance_message.return_value = "Test message"
        
        # Get multiple responses
        response1 = self.api.get_status()
        response2 = self.api.get_status()
        
        # Verify consistent structure
        self.assertEqual(type(response1), type(response2))
        self.assertEqual(response1.is_active, response2.is_active)
        self.assertEqual(response1.mode, response2.mode)
        self.assertEqual(response1.reason, response2.reason)
        
        # Verify timestamps are different (showing real-time updates)
        self.assertNotEqual(response1.timestamp, response2.timestamp)


if __name__ == '__main__':
    unittest.main()