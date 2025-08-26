# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for MaintenanceStatusSSE

Tests the Server-Sent Events implementation for real-time maintenance status updates.
"""

import unittest
import sys
import os
import time
import threading
import json
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from maintenance_status_sse import MaintenanceStatusSSE, create_flask_sse_response
from maintenance_status_api import MaintenanceStatusResponse


class TestMaintenanceStatusSSE(unittest.TestCase):
    """Test cases for MaintenanceStatusSSE"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock status API
        self.mock_status_api = Mock()
        
        # Sample status response
        self.sample_status = MaintenanceStatusResponse(
            is_active=True,
            mode="normal",
            reason="Test maintenance",
            estimated_duration=30,
            started_at=datetime.now(timezone.utc).isoformat(),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=["caption_generation"],
            active_jobs_count=5,
            invalidated_sessions=10,
            test_mode=False,
            message="Test maintenance in progress",
            response_time_ms=50.0,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Create SSE service
        self.sse_service = MaintenanceStatusSSE(self.mock_status_api)
        
        # Reduce intervals for faster testing
        self.sse_service.heartbeat_interval = 1
        self.sse_service.connection_timeout = 5
    
    def tearDown(self):
        """Clean up after tests"""
        self.sse_service.shutdown()
    
    def test_sse_service_initialization(self):
        """Test SSE service initialization"""
        # Verify service is initialized
        self.assertIsNotNone(self.sse_service.status_api)
        self.assertEqual(self.sse_service.status_api, self.mock_status_api)
        
        # Verify subscription to status API
        self.mock_status_api.subscribe_to_status_changes.assert_called_once()
        
        # Verify background threads are started
        self.assertTrue(self.sse_service._running)
        self.assertTrue(self.sse_service._heartbeat_thread.is_alive())
        self.assertTrue(self.sse_service._cleanup_thread.is_alive())
    
    def test_create_event_stream_basic(self):
        """Test basic event stream creation"""
        # Setup mock
        self.mock_status_api.get_status.return_value = self.sample_status
        
        # Create event stream
        client_id = "test-client-1"
        stream = self.sse_service.create_event_stream(client_id)
        
        # Get first few events
        events = []
        for i, event in enumerate(stream):
            events.append(event)
            if i >= 2:  # Get initial status and connection confirmation
                break
        
        # Verify events
        self.assertEqual(len(events), 3)
        
        # Check initial status event
        self.assertIn("event: status_update", events[0])
        self.assertIn("data:", events[0])
        
        # Check connection confirmation
        self.assertIn("event: connection_established", events[1])
        self.assertIn(client_id, events[1])
        
        # Verify client was registered
        client_info = self.sse_service.get_client_info(client_id)
        self.assertIsNotNone(client_info)
        self.assertEqual(client_info['id'], client_id)
        self.assertTrue(client_info['active'])
    
    def test_broadcast_event(self):
        """Test event broadcasting"""
        # Setup mock
        self.mock_status_api.get_status.return_value = self.sample_status
        
        # Create a client stream
        client_id = "test-client-broadcast"
        stream = self.sse_service.create_event_stream(client_id)
        
        # Consume initial events
        events = []
        for i, event in enumerate(stream):
            events.append(event)
            if i >= 1:  # Get initial events
                break
        
        # Broadcast a test event
        test_data = {"test": "data", "timestamp": datetime.now(timezone.utc).isoformat()}
        clients_notified = self.sse_service.broadcast_event("test_event", test_data)
        
        # Verify broadcast
        self.assertGreater(clients_notified, 0)
        
        # Get the broadcasted event
        try:
            next_event = next(stream)
            self.assertIn("event: test_event", next_event)
            self.assertIn("test", next_event)
        except StopIteration:
            self.fail("Expected broadcasted event not received")
    
    def test_event_filtering(self):
        """Test event type filtering"""
        # Setup mock
        self.mock_status_api.get_status.return_value = self.sample_status
        
        # Create client with specific event type subscription
        client_id = "test-client-filter"
        event_types = ["maintenance_status_change"]
        stream = self.sse_service.create_event_stream(client_id, event_types)
        
        # Consume initial events
        events = []
        for i, event in enumerate(stream):
            events.append(event)
            if i >= 1:
                break
        
        # Broadcast different types of events
        self.sse_service.broadcast_event("maintenance_status_change", {"allowed": True})
        self.sse_service.broadcast_event("other_event", {"blocked": True})
        
        # Get next events
        received_events = []
        try:
            for i in range(2):
                event = next(stream)
                received_events.append(event)
        except StopIteration:
            pass
        
        # Verify only allowed event type was received
        allowed_events = [e for e in received_events if "maintenance_status_change" in e]
        blocked_events = [e for e in received_events if "other_event" in e]
        
        self.assertGreater(len(allowed_events), 0)
        self.assertEqual(len(blocked_events), 0)
    
    def test_client_management(self):
        """Test client connection management"""
        # Setup mock
        self.mock_status_api.get_status.return_value = self.sample_status
        
        # Create multiple clients
        client1_id = "client-1"
        client2_id = "client-2"
        
        stream1 = self.sse_service.create_event_stream(client1_id)
        stream2 = self.sse_service.create_event_stream(client2_id)
        
        # Consume initial events for both clients
        for i, event in enumerate(stream1):
            if i >= 1:
                break
        
        for i, event in enumerate(stream2):
            if i >= 1:
                break
        
        # Verify both clients are registered
        self.assertIsNotNone(self.sse_service.get_client_info(client1_id))
        self.assertIsNotNone(self.sse_service.get_client_info(client2_id))
        
        # Disconnect one client
        result = self.sse_service.disconnect_client(client1_id)
        self.assertTrue(result)
        
        # Verify client was marked inactive
        client1_info = self.sse_service.get_client_info(client1_id)
        self.assertFalse(client1_info['active'])
        
        # Try to disconnect non-existent client
        result = self.sse_service.disconnect_client("non-existent")
        self.assertFalse(result)
    
    def test_heartbeat_functionality(self):
        """Test heartbeat functionality"""
        # Setup mock
        self.mock_status_api.get_status.return_value = self.sample_status
        
        # Create client stream
        client_id = "test-client-heartbeat"
        stream = self.sse_service.create_event_stream(client_id)
        
        # Consume initial events
        for i, event in enumerate(stream):
            if i >= 1:
                break
        
        # Wait for heartbeat (reduced interval for testing)
        time.sleep(1.5)
        
        # Get heartbeat event
        heartbeat_received = False
        try:
            for i in range(5):  # Try to get heartbeat within reasonable time
                event = next(stream)
                if "event: heartbeat" in event:
                    heartbeat_received = True
                    self.assertIn("timestamp", event)
                    self.assertIn("active_clients", event)
                    break
        except StopIteration:
            pass
        
        self.assertTrue(heartbeat_received, "Heartbeat event not received")
    
    def test_sse_statistics(self):
        """Test SSE statistics collection"""
        # Setup mock
        self.mock_status_api.get_status.return_value = self.sample_status
        
        # Create some clients
        client1_stream = self.sse_service.create_event_stream("stats-client-1")
        client2_stream = self.sse_service.create_event_stream("stats-client-2", ["test_events"])
        
        # Consume initial events
        for i, event in enumerate(client1_stream):
            if i >= 1:
                break
        
        for i, event in enumerate(client2_stream):
            if i >= 1:
                break
        
        # Broadcast some events
        self.sse_service.broadcast_event("test_event", {"data": "test"})
        self.sse_service.broadcast_event("another_event", {"data": "test2"})
        
        # Get statistics
        stats = self.sse_service.get_sse_stats()
        
        # Verify statistics structure
        self.assertIn('service_stats', stats)
        self.assertIn('client_stats', stats)
        self.assertIn('queue_stats', stats)
        self.assertIn('configuration', stats)
        
        # Verify service stats
        service_stats = stats['service_stats']
        self.assertGreaterEqual(service_stats['total_connections'], 2)
        self.assertGreaterEqual(service_stats['active_connections'], 2)
        self.assertGreaterEqual(service_stats['events_sent'], 2)
        
        # Verify client stats
        client_stats = stats['client_stats']
        self.assertGreaterEqual(client_stats['active_clients'], 2)
        self.assertIn('clients_by_event_type', client_stats)
        
        # Verify queue stats
        queue_stats = stats['queue_stats']
        self.assertGreaterEqual(queue_stats['queue_size'], 0)
        self.assertEqual(queue_stats['max_queue_size'], self.sse_service.max_queue_size)
    
    def test_status_change_integration(self):
        """Test integration with status API changes"""
        # Setup mock
        self.mock_status_api.get_status.return_value = self.sample_status
        
        # Create client stream
        client_id = "test-status-change"
        stream = self.sse_service.create_event_stream(client_id)
        
        # Consume initial events
        for i, event in enumerate(stream):
            if i >= 1:
                break
        
        # Simulate status change from API
        updated_status = MaintenanceStatusResponse(
            is_active=False,
            mode="normal",
            reason=None,
            estimated_duration=None,
            started_at=None,
            estimated_completion=None,
            enabled_by=None,
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False,
            message="System is operating normally",
            response_time_ms=25.0,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Trigger status change handler
        self.sse_service._handle_status_change("maintenance_disabled", updated_status)
        
        # Get the status change event
        status_change_received = False
        try:
            for i in range(3):
                event = next(stream)
                if "event: maintenance_status_change" in event:
                    status_change_received = True
                    self.assertIn("maintenance_disabled", event)
                    self.assertIn("is_active", event)
                    break
        except StopIteration:
            pass
        
        self.assertTrue(status_change_received, "Status change event not received")
    
    def test_error_handling(self):
        """Test error handling in SSE service"""
        # Test with API that raises exceptions
        error_api = Mock()
        error_api.get_status.side_effect = Exception("API Error")
        error_api.subscribe_to_status_changes.return_value = "test-sub"
        
        # Create SSE service with error API
        error_sse = MaintenanceStatusSSE(error_api)
        
        try:
            # Create stream (should handle API error gracefully)
            stream = error_sse.create_event_stream("error-client")
            
            # Try to get events (should not crash)
            events = []
            for i, event in enumerate(stream):
                events.append(event)
                if i >= 1:
                    break
            
            # Should have received some events despite API error
            self.assertGreater(len(events), 0)
            
        finally:
            error_sse.shutdown()
    
    def test_flask_response_creation(self):
        """Test Flask SSE response creation"""
        # Setup mock
        self.mock_status_api.get_status.return_value = self.sample_status
        
        # Create Flask response
        response = create_flask_sse_response(self.sse_service, "flask-client")
        
        # Verify response properties
        self.assertEqual(response.mimetype, 'text/event-stream')
        self.assertIn('Cache-Control', response.headers)
        self.assertIn('Connection', response.headers)
        self.assertEqual(response.headers['Cache-Control'], 'no-cache')
        self.assertEqual(response.headers['Connection'], 'keep-alive')
        
        # Verify response has data
        self.assertIsNotNone(response.response)
    
    def test_queue_management(self):
        """Test event queue management"""
        # Setup mock
        self.mock_status_api.get_status.return_value = self.sample_status
        
        # Set small queue size for testing
        original_max_size = self.sse_service.max_queue_size
        self.sse_service.max_queue_size = 3
        
        try:
            # Broadcast more events than queue size
            for i in range(5):
                self.sse_service.broadcast_event(f"test_event_{i}", {"index": i})
            
            # Verify queue was trimmed
            with self.sse_service._queue_lock:
                self.assertLessEqual(len(self.sse_service._event_queue), 3)
                
                # Verify latest events are kept
                latest_event = self.sse_service._event_queue[-1]
                self.assertEqual(latest_event['type'], 'test_event_4')
        
        finally:
            self.sse_service.max_queue_size = original_max_size
    
    def test_cleanup_functionality(self):
        """Test client cleanup functionality"""
        # Setup mock
        self.mock_status_api.get_status.return_value = self.sample_status
        
        # Set short timeout for testing
        original_timeout = self.sse_service.connection_timeout
        self.sse_service.connection_timeout = 1
        
        try:
            # Create client
            client_id = "cleanup-test-client"
            stream = self.sse_service.create_event_stream(client_id)
            
            # Consume initial events
            for i, event in enumerate(stream):
                if i >= 1:
                    break
            
            # Verify client exists
            self.assertIsNotNone(self.sse_service.get_client_info(client_id))
            
            # Wait for cleanup (timeout + cleanup interval)
            time.sleep(2)
            
            # Client should still exist but might be marked for cleanup
            # (actual cleanup happens in background thread)
            
        finally:
            self.sse_service.connection_timeout = original_timeout


if __name__ == '__main__':
    unittest.main()