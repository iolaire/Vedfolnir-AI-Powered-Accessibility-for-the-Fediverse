# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for maintenance mode transitions

Tests graceful maintenance mode transitions including job completion
waiting and immediate resumption of operations.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timezone
import threading
import time

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from maintenance_mode_transition_manager import (
    MaintenanceModeTransitionManager, TransitionState, TransitionStatus,
    RunningJobInfo
)
from maintenance_mode_service import MaintenanceModeService, MaintenanceChangeEvent


class TestMaintenanceModeTransitions(unittest.TestCase):
    """Test cases for maintenance mode transitions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_maintenance_service = Mock(spec=MaintenanceModeService)
        self.mock_db_manager = Mock()
        
        # Create transition manager with short timeout for testing
        self.transition_manager = MaintenanceModeTransitionManager(
            maintenance_service=self.mock_maintenance_service,
            db_manager=self.mock_db_manager,
            job_completion_timeout=5  # 5 seconds for testing
        )
    
    def tearDown(self):
        """Clean up after tests"""
        self.transition_manager.shutdown()
    
    def test_initialization(self):
        """Test transition manager initialization"""
        self.assertEqual(self.transition_manager._current_state, TransitionState.NORMAL)
        self.assertIsNone(self.transition_manager._transition_started_at)
        self.assertTrue(self.transition_manager._monitoring_active)
    
    def test_get_transition_status_normal(self):
        """Test getting transition status in normal state"""
        # Mock maintenance service
        self.mock_maintenance_service.is_maintenance_mode.return_value = False
        
        # Get status
        status = self.transition_manager.get_transition_status()
        
        self.assertEqual(status.state, TransitionState.NORMAL)
        self.assertFalse(status.maintenance_enabled)
        self.assertEqual(status.running_jobs_count, 0)
        self.assertTrue(status.can_complete_transition)
        self.assertEqual(len(status.blocking_jobs), 0)
    
    def test_entering_maintenance_with_no_jobs(self):
        """Test entering maintenance mode when no jobs are running"""
        # Mock no running jobs
        with patch.object(self.transition_manager, '_get_running_jobs', return_value=[]):
            # Create maintenance change event
            change_event = MaintenanceChangeEvent(
                enabled=True,
                reason="Test maintenance",
                changed_at=datetime.now(timezone.utc)
            )
            
            # Handle the change
            self.transition_manager._handle_maintenance_change(change_event)
            
            # Should immediately enter maintenance mode
            self.assertEqual(self.transition_manager._current_state, TransitionState.IN_MAINTENANCE)
    
    def test_entering_maintenance_with_running_jobs(self):
        """Test entering maintenance mode when jobs are running"""
        # Mock running jobs
        running_jobs = [
            RunningJobInfo(
                job_id="job1",
                user_id=1,
                started_at=datetime.now(timezone.utc),
                estimated_completion=None,
                job_type="caption_generation",
                status="running"
            )
        ]
        
        with patch.object(self.transition_manager, '_get_running_jobs', return_value=running_jobs):
            # Create maintenance change event
            change_event = MaintenanceChangeEvent(
                enabled=True,
                reason="Test maintenance with jobs",
                changed_at=datetime.now(timezone.utc)
            )
            
            # Handle the change
            self.transition_manager._handle_maintenance_change(change_event)
            
            # Should be in entering maintenance state
            self.assertEqual(self.transition_manager._current_state, TransitionState.ENTERING_MAINTENANCE)
            self.assertIsNotNone(self.transition_manager._transition_started_at)
    
    def test_exiting_maintenance_immediate(self):
        """Test exiting maintenance mode happens immediately"""
        # Set initial state to maintenance
        with self.transition_manager._state_lock:
            self.transition_manager._current_state = TransitionState.IN_MAINTENANCE
        
        # Create maintenance change event (disabled)
        change_event = MaintenanceChangeEvent(
            enabled=False,
            reason=None,
            changed_at=datetime.now(timezone.utc)
        )
        
        # Handle the change
        self.transition_manager._handle_maintenance_change(change_event)
        
        # Should immediately return to normal
        self.assertEqual(self.transition_manager._current_state, TransitionState.NORMAL)
        self.assertIsNone(self.transition_manager._transition_started_at)
    
    def test_force_transition_completion_entering(self):
        """Test forcing completion when entering maintenance"""
        # Set state to entering maintenance
        with self.transition_manager._state_lock:
            self.transition_manager._current_state = TransitionState.ENTERING_MAINTENANCE
        
        # Force completion
        result = self.transition_manager.force_transition_completion("Test force")
        
        self.assertTrue(result)
        self.assertEqual(self.transition_manager._current_state, TransitionState.IN_MAINTENANCE)
    
    def test_force_transition_completion_exiting(self):
        """Test forcing completion when exiting maintenance"""
        # Set state to exiting maintenance
        with self.transition_manager._state_lock:
            self.transition_manager._current_state = TransitionState.EXITING_MAINTENANCE
        
        # Force completion
        result = self.transition_manager.force_transition_completion("Test force")
        
        self.assertTrue(result)
        self.assertEqual(self.transition_manager._current_state, TransitionState.NORMAL)
    
    def test_force_transition_completion_no_transition(self):
        """Test forcing completion when no transition is active"""
        # State is already normal
        result = self.transition_manager.force_transition_completion("Test force")
        
        self.assertFalse(result)
        self.assertEqual(self.transition_manager._current_state, TransitionState.NORMAL)
    
    def test_subscribe_to_transitions(self):
        """Test subscribing to transition events"""
        callback_results = []
        
        def test_callback(event_type, event_data):
            callback_results.append((event_type, event_data))
        
        # Subscribe
        subscription_id = self.transition_manager.subscribe_to_transitions(test_callback)
        
        self.assertIsNotNone(subscription_id)
        self.assertIn(subscription_id, self.transition_manager._transition_callbacks)
    
    def test_unsubscribe_from_transitions(self):
        """Test unsubscribing from transition events"""
        def test_callback(event_type, event_data):
            pass
        
        # Subscribe first
        subscription_id = self.transition_manager.subscribe_to_transitions(test_callback)
        
        # Then unsubscribe
        result = self.transition_manager.unsubscribe_from_transitions(subscription_id)
        
        self.assertTrue(result)
        self.assertNotIn(subscription_id, self.transition_manager._transition_callbacks)
    
    def test_unsubscribe_nonexistent(self):
        """Test unsubscribing from non-existent subscription"""
        result = self.transition_manager.unsubscribe_from_transitions("nonexistent-id")
        
        self.assertFalse(result)
    
    def test_transition_callbacks_notification(self):
        """Test transition callback notifications"""
        callback_results = []
        callback_lock = threading.Lock()
        
        def test_callback(event_type, event_data):
            with callback_lock:
                callback_results.append((event_type, event_data))
        
        # Subscribe
        subscription_id = self.transition_manager.subscribe_to_transitions(test_callback)
        
        # Trigger notification
        self.transition_manager._notify_transition_callbacks('test_event', {'test': 'data'})
        
        # Give time for callback to execute
        time.sleep(0.1)
        
        # Check results
        with callback_lock:
            self.assertEqual(len(callback_results), 1)
            self.assertEqual(callback_results[0][0], 'test_event')
            self.assertEqual(callback_results[0][1]['test'], 'data')
    
    def test_transition_callback_error_handling(self):
        """Test transition callback error handling"""
        def failing_callback(event_type, event_data):
            raise Exception("Callback error")
        
        # Subscribe with failing callback
        subscription_id = self.transition_manager.subscribe_to_transitions(failing_callback)
        
        # This should not raise an exception
        try:
            self.transition_manager._notify_transition_callbacks('test_event', {})
        except Exception as e:
            self.fail(f"Callback error should be handled gracefully: {e}")
    
    def test_get_transition_status_with_running_jobs(self):
        """Test getting transition status with running jobs"""
        # Mock running jobs
        running_jobs = [
            RunningJobInfo(
                job_id="job1",
                user_id=1,
                started_at=datetime.now(timezone.utc),
                estimated_completion=datetime.now(timezone.utc),
                job_type="caption_generation",
                status="running"
            ),
            RunningJobInfo(
                job_id="job2",
                user_id=2,
                started_at=datetime.now(timezone.utc),
                estimated_completion=None,
                job_type="batch_processing",
                status="processing"
            )
        ]
        
        # Set state to entering maintenance
        with self.transition_manager._state_lock:
            self.transition_manager._current_state = TransitionState.ENTERING_MAINTENANCE
            self.transition_manager._transition_started_at = datetime.now(timezone.utc)
        
        # Mock maintenance service and running jobs
        self.mock_maintenance_service.is_maintenance_mode.return_value = True
        
        with patch.object(self.transition_manager, '_get_running_jobs', return_value=running_jobs):
            # Get status
            status = self.transition_manager.get_transition_status()
            
            self.assertEqual(status.state, TransitionState.ENTERING_MAINTENANCE)
            self.assertTrue(status.maintenance_enabled)
            self.assertEqual(status.running_jobs_count, 2)
            self.assertEqual(len(status.running_jobs), 2)
            self.assertFalse(status.can_complete_transition)
            self.assertEqual(len(status.blocking_jobs), 2)
            self.assertIn("job1", status.blocking_jobs)
            self.assertIn("job2", status.blocking_jobs)
    
    def test_get_transition_status_error_handling(self):
        """Test transition status error handling"""
        # Mock maintenance service to raise exception
        self.mock_maintenance_service.is_maintenance_mode.side_effect = Exception("Service error")
        
        # Get status
        status = self.transition_manager.get_transition_status()
        
        # Should return safe default status
        self.assertEqual(status.state, TransitionState.NORMAL)
        self.assertFalse(status.maintenance_enabled)
        self.assertEqual(status.running_jobs_count, 0)
        self.assertTrue(status.can_complete_transition)
    
    def test_can_complete_transition_logic(self):
        """Test transition completion logic"""
        # Test entering maintenance with no jobs
        can_complete = self.transition_manager._can_complete_transition(
            TransitionState.ENTERING_MAINTENANCE, []
        )
        self.assertTrue(can_complete)
        
        # Test entering maintenance with jobs
        running_jobs = [RunningJobInfo("job1", 1, datetime.now(timezone.utc), None, "test", "running")]
        can_complete = self.transition_manager._can_complete_transition(
            TransitionState.ENTERING_MAINTENANCE, running_jobs
        )
        self.assertFalse(can_complete)
        
        # Test exiting maintenance (always can complete)
        can_complete = self.transition_manager._can_complete_transition(
            TransitionState.EXITING_MAINTENANCE, running_jobs
        )
        self.assertTrue(can_complete)
        
        # Test normal state (always can complete)
        can_complete = self.transition_manager._can_complete_transition(
            TransitionState.NORMAL, running_jobs
        )
        self.assertTrue(can_complete)
    
    def test_monitoring_thread_job_completion(self):
        """Test monitoring thread detects job completion"""
        # Set state to entering maintenance
        with self.transition_manager._state_lock:
            self.transition_manager._current_state = TransitionState.ENTERING_MAINTENANCE
            self.transition_manager._transition_started_at = datetime.now(timezone.utc)
        
        # Mock running jobs initially, then empty
        call_count = 0
        def mock_get_running_jobs():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [RunningJobInfo("job1", 1, datetime.now(timezone.utc), None, "test", "running")]
            else:
                return []  # Jobs completed
        
        with patch.object(self.transition_manager, '_get_running_jobs', side_effect=mock_get_running_jobs):
            # Wait for monitoring thread to detect completion
            max_wait = 15  # seconds
            start_time = time.time()
            
            while (self.transition_manager._current_state != TransitionState.IN_MAINTENANCE and 
                   time.time() - start_time < max_wait):
                time.sleep(0.5)
            
            # Should have transitioned to maintenance mode
            self.assertEqual(self.transition_manager._current_state, TransitionState.IN_MAINTENANCE)
    
    def test_monitoring_thread_timeout(self):
        """Test monitoring thread handles timeout"""
        # Set state to entering maintenance
        with self.transition_manager._state_lock:
            self.transition_manager._current_state = TransitionState.ENTERING_MAINTENANCE
            from datetime import timedelta
            self.transition_manager._transition_started_at = datetime.now(timezone.utc) - \
                                                           timedelta(seconds=self.transition_manager.job_completion_timeout * 2)
        
        # Mock running jobs that never complete
        running_jobs = [RunningJobInfo("job1", 1, datetime.now(timezone.utc), None, "test", "running")]
        
        with patch.object(self.transition_manager, '_get_running_jobs', return_value=running_jobs):
            # Wait for monitoring thread to detect timeout
            max_wait = 15  # seconds
            start_time = time.time()
            
            while (self.transition_manager._current_state != TransitionState.IN_MAINTENANCE and 
                   time.time() - start_time < max_wait):
                time.sleep(0.5)
            
            # Should have been forced into maintenance mode due to timeout
            self.assertEqual(self.transition_manager._current_state, TransitionState.IN_MAINTENANCE)


if __name__ == '__main__':
    unittest.main()