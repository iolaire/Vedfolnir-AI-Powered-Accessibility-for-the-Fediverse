# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for Enhanced Error Recovery Manager

Tests the enhanced error handling and recovery system with multi-tenant capabilities,
error categorization, pattern detection, and administrative escalation.
"""

import unittest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

from enhanced_error_recovery_manager import (
    EnhancedErrorRecoveryManager,
    EnhancedErrorCategory,
    EscalationLevel,
    ErrorPattern,
    EnhancedErrorInfo,
    handle_enhanced_caption_error
)

class TestEnhancedErrorRecoveryManager(unittest.TestCase):
    """Test cases for Enhanced Error Recovery Manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = EnhancedErrorRecoveryManager()
        self.test_context = {
            'user_id': 1,
            'task_id': 'test-task-123',
            'platform_connection_id': 1
        }
    
    def test_enhanced_error_categorization_user_errors(self):
        """Test enhanced categorization of user errors"""
        user_errors = [
            "Invalid input provided",
            "Permission denied for user",
            "User quota exceeded",
            "Invalid user settings"
        ]
        
        for error_msg in user_errors:
            category, pattern = self.manager.enhanced_categorize_error(
                Exception(error_msg), self.test_context
            )
            self.assertEqual(category, EnhancedErrorCategory.USER)
    
    def test_enhanced_error_categorization_system_errors(self):
        """Test enhanced categorization of system errors"""
        system_errors = [
            "Database connection error",
            "Out of memory error",
            "Disk full error",
            "System overload detected"
        ]
        
        for error_msg in system_errors:
            category, pattern = self.manager.enhanced_categorize_error(
                Exception(error_msg), self.test_context
            )
            self.assertEqual(category, EnhancedErrorCategory.SYSTEM)
    
    def test_enhanced_error_categorization_platform_errors(self):
        """Test enhanced categorization of platform errors"""
        platform_errors = [
            "Rate limit exceeded",
            "Platform temporarily unavailable",
            "API deprecated warning",
            "Platform connection timeout"
        ]
        
        for error_msg in platform_errors:
            category, pattern = self.manager.enhanced_categorize_error(
                Exception(error_msg), self.test_context
            )
            self.assertEqual(category, EnhancedErrorCategory.PLATFORM)
    
    def test_enhanced_error_categorization_administrative_errors(self):
        """Test enhanced categorization of administrative errors"""
        admin_context = {**self.test_context, 'admin_action': True, 'admin_user_id': 2}
        
        admin_errors = [
            "Admin unauthorized action",
            "Configuration invalid",
            "Administrative privilege required"
        ]
        
        for error_msg in admin_errors:
            category, pattern = self.manager.enhanced_categorize_error(
                Exception(error_msg), admin_context
            )
            self.assertIn(category, [EnhancedErrorCategory.ADMINISTRATIVE, EnhancedErrorCategory.USER])
    
    def test_error_pattern_matching(self):
        """Test error pattern matching and escalation level assignment"""
        # Test critical system error
        error = Exception("Out of memory")
        category, pattern = self.manager.enhanced_categorize_error(error, self.test_context)
        
        self.assertEqual(category, EnhancedErrorCategory.SYSTEM)
        self.assertIsNotNone(pattern)
        self.assertEqual(pattern.escalation_level, EscalationLevel.CRITICAL)
        self.assertGreater(len(pattern.recovery_suggestions), 0)
    
    def test_create_enhanced_error_info(self):
        """Test creation of enhanced error information"""
        error = Exception("Rate limit exceeded")
        error_info = self.manager.create_enhanced_error_info(error, self.test_context)
        
        self.assertIsInstance(error_info, EnhancedErrorInfo)
        self.assertEqual(error_info.category, EnhancedErrorCategory.PLATFORM)
        self.assertEqual(error_info.user_id, 1)
        self.assertEqual(error_info.task_id, 'test-task-123')
        self.assertEqual(error_info.platform_connection_id, 1)
        self.assertIsNotNone(error_info.escalation_level)
        self.assertIsInstance(error_info.recovery_suggestions, list)
    
    def test_escalation_level_increase(self):
        """Test escalation level increase functionality"""
        # Test each level increase
        test_cases = [
            (EscalationLevel.NONE, EscalationLevel.LOW),
            (EscalationLevel.LOW, EscalationLevel.MEDIUM),
            (EscalationLevel.MEDIUM, EscalationLevel.HIGH),
            (EscalationLevel.HIGH, EscalationLevel.CRITICAL),
            (EscalationLevel.CRITICAL, EscalationLevel.CRITICAL)  # Should stay at critical
        ]
        
        for current, expected in test_cases:
            result = self.manager._increase_escalation_level(current)
            self.assertEqual(result, expected)
    
    def test_pattern_frequency_escalation(self):
        """Test pattern frequency-based escalation"""
        # Create a pattern with low threshold for testing
        test_pattern = ErrorPattern(
            pattern="test error",
            category=EnhancedErrorCategory.PLATFORM,
            escalation_level=EscalationLevel.LOW,
            frequency_threshold=3,
            time_window_minutes=60
        )
        
        # Add pattern to manager
        self.manager.enhanced_error_patterns.append(test_pattern)
        
        # Trigger the pattern multiple times
        for i in range(4):  # Exceed threshold
            error = Exception("Test error occurred")
            should_escalate = self.manager._should_escalate_pattern(test_pattern, error)
            
            if i >= 2:  # Should escalate on 3rd occurrence (index 2)
                self.assertTrue(should_escalate)
            else:
                self.assertFalse(should_escalate)
    
    def test_recoverable_error_determination(self):
        """Test enhanced recoverable error determination"""
        test_cases = [
            # (category, escalation_level, expected_recoverable)
            (EnhancedErrorCategory.USER, EscalationLevel.LOW, False),
            (EnhancedErrorCategory.SYSTEM, EscalationLevel.MEDIUM, True),
            (EnhancedErrorCategory.SYSTEM, EscalationLevel.CRITICAL, False),
            (EnhancedErrorCategory.PLATFORM, EscalationLevel.LOW, True),
            (EnhancedErrorCategory.AUTHENTICATION, EscalationLevel.LOW, False),
            (EnhancedErrorCategory.ADMINISTRATIVE, EscalationLevel.LOW, True),
            (EnhancedErrorCategory.ADMINISTRATIVE, EscalationLevel.HIGH, False)
        ]
        
        for category, escalation_level, expected in test_cases:
            error = Exception("Test error")
            result = self.manager._is_enhanced_recoverable(category, error, escalation_level)
            self.assertEqual(result, expected, 
                f"Failed for {category.value} with {escalation_level.value}")
    
    def test_handle_enhanced_error_fail_fast(self):
        """Test enhanced error handling with fail fast strategy"""
        async def run_test():
            error = Exception("Invalid input provided")
            
            async def mock_operation():
                return "success"
            
            with self.assertRaises(Exception) as context:
                await self.manager.handle_enhanced_error(
                    error, mock_operation, self.test_context
                )
            
            # Parse the JSON error response
            error_response = json.loads(str(context.exception))
            self.assertFalse(error_response['success'])
            self.assertEqual(error_response['error_category'], EnhancedErrorCategory.USER.value)
            self.assertIn('user_message', error_response)
            self.assertIn('recovery_suggestions', error_response)
        
        asyncio.run(run_test())
    
    def test_handle_enhanced_error_retry_strategy(self):
        """Test enhanced error handling with retry strategy"""
        async def run_test():
            error = Exception("Connection timeout")
            retry_count = 0
            
            async def mock_operation():
                nonlocal retry_count
                retry_count += 1
                if retry_count < 3:
                    raise Exception("Connection timeout")
                return "success"
            
            # Mock sleep to speed up test
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await self.manager.handle_enhanced_error(
                    error, mock_operation, self.test_context
                )
            
            self.assertEqual(result, "success")
            self.assertEqual(retry_count, 3)
        
        asyncio.run(run_test())
    
    def test_handle_enhanced_error_admin_notification(self):
        """Test enhanced error handling with admin notification"""
        async def run_test():
            error = Exception("Database connection error")
            
            async def mock_operation():
                return "success"
            
            with self.assertRaises(Exception) as context:
                await self.manager.handle_enhanced_error(
                    error, mock_operation, self.test_context
                )
            
            # Parse the JSON error response
            error_response = json.loads(str(context.exception))
            self.assertTrue(error_response['admin_notified'])
            self.assertEqual(error_response['error_category'], EnhancedErrorCategory.SYSTEM.value)
            
            # Check that admin notification was created
            self.assertGreater(len(self.manager.admin_notifications), 0)
            notification = self.manager.admin_notifications[-1]
            self.assertEqual(notification['type'], 'error_escalation')
            self.assertTrue(notification['requires_attention'])
        
        asyncio.run(run_test())
    
    def test_user_friendly_message_generation(self):
        """Test user-friendly message generation"""
        test_cases = [
            (EnhancedErrorCategory.USER, EscalationLevel.LOW, ["Check your input"]),
            (EnhancedErrorCategory.SYSTEM, EscalationLevel.CRITICAL, ["Contact support"]),
            (EnhancedErrorCategory.PLATFORM, EscalationLevel.MEDIUM, ["Try again later"]),
            (EnhancedErrorCategory.AUTHENTICATION, EscalationLevel.LOW, ["Check credentials"])
        ]
        
        for category, escalation_level, suggestions in test_cases:
            error_info = EnhancedErrorInfo(
                category=category,
                message="Test error",
                details={},
                timestamp=datetime.now(timezone.utc),
                escalation_level=escalation_level,
                recovery_suggestions=suggestions
            )
            
            message = self.manager._generate_user_friendly_message(error_info)
            
            self.assertIsInstance(message, str)
            self.assertGreater(len(message), 0)
            
            # Check that suggestions are included
            for suggestion in suggestions:
                self.assertIn(suggestion, message)
            
            # Check escalation level context
            if escalation_level == EscalationLevel.CRITICAL:
                self.assertIn("critical", message.lower())
            elif escalation_level == EscalationLevel.HIGH:
                self.assertIn("escalated", message.lower())
    
    def test_enhanced_error_statistics(self):
        """Test enhanced error statistics collection"""
        # Create some test errors
        test_errors = [
            (Exception("Invalid input"), EnhancedErrorCategory.USER, EscalationLevel.NONE),
            (Exception("Database error"), EnhancedErrorCategory.SYSTEM, EscalationLevel.HIGH),
            (Exception("Rate limit"), EnhancedErrorCategory.PLATFORM, EscalationLevel.LOW),
            (Exception("Out of memory"), EnhancedErrorCategory.SYSTEM, EscalationLevel.CRITICAL)
        ]
        
        for error, category, escalation in test_errors:
            error_info = EnhancedErrorInfo(
                category=category,
                message=str(error),
                details={},
                timestamp=datetime.now(timezone.utc),
                escalation_level=escalation
            )
            self.manager.error_history.append(error_info)
        
        stats = self.manager.get_enhanced_error_statistics()
        
        self.assertEqual(stats['total_errors'], 4)
        self.assertIn('category_breakdown', stats)
        self.assertIn('escalation_breakdown', stats)
        self.assertEqual(stats['critical_errors'], 1)
        self.assertEqual(stats['high_priority_errors'], 1)
        
        # Check category breakdown
        self.assertEqual(stats['category_breakdown']['user'], 1)
        self.assertEqual(stats['category_breakdown']['system'], 2)
        self.assertEqual(stats['category_breakdown']['platform'], 1)
    
    def test_escalation_history_tracking(self):
        """Test escalation history tracking"""
        # Create an error that should escalate
        error = Exception("Database connection error")
        error_info = self.manager.create_enhanced_error_info(error, self.test_context)
        
        # Manually trigger escalation
        asyncio.run(self.manager._handle_escalation(error_info))
        
        # Check escalation history
        history = self.manager.get_escalation_history()
        self.assertGreater(len(history), 0)
        
        escalation = history[-1]
        self.assertEqual(escalation['category'], EnhancedErrorCategory.SYSTEM.value)
        self.assertIn('timestamp', escalation)
        self.assertIn('user_id', escalation)
        self.assertIn('task_id', escalation)
    
    def test_old_error_cleanup(self):
        """Test cleanup of old error records"""
        # Add some old errors
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        
        old_error = EnhancedErrorInfo(
            category=EnhancedErrorCategory.USER,
            message="Old error",
            details={},
            timestamp=old_time,
            escalation_level=EscalationLevel.NONE
        )
        
        recent_error = EnhancedErrorInfo(
            category=EnhancedErrorCategory.PLATFORM,
            message="Recent error",
            details={},
            timestamp=recent_time,
            escalation_level=EscalationLevel.LOW
        )
        
        self.manager.error_history.extend([old_error, recent_error])
        
        # Clean up old errors (older than 24 hours)
        cleared_count = self.manager.clear_old_errors(hours=24)
        
        self.assertEqual(cleared_count, 1)
        self.assertEqual(len(self.manager.error_history), 1)
        self.assertEqual(self.manager.error_history[0].message, "Recent error")
    
    def test_decorator_functionality(self):
        """Test the enhanced error handling decorator"""
        # Patch the global manager with our test instance
        with patch('enhanced_error_recovery_manager.enhanced_error_recovery_manager', self.manager):
            @handle_enhanced_caption_error(context=self.test_context)
            async def test_function():
                raise Exception("Test error for decorator")
            
            with self.assertRaises(Exception):
                asyncio.run(test_function())
            
            # Check that error was handled by the enhanced manager
            self.assertGreater(len(self.manager.error_history), 0)
    
    def test_logging_integration(self):
        """Test logging integration with enhanced error handling"""
        async def run_test():
            error = Exception("Test error for logging")
            error_info = self.manager.create_enhanced_error_info(error, self.test_context)
            
            with patch('enhanced_error_recovery_manager.logger') as mock_logger:
                await self.manager._log_enhanced_error(error_info)
                
                # Verify appropriate logging method was called
                if error_info.escalation_level in [EscalationLevel.HIGH, EscalationLevel.CRITICAL]:
                    mock_logger.critical.assert_called_once()
                elif error_info.escalation_level == EscalationLevel.MEDIUM:
                    mock_logger.warning.assert_called_once()
                else:
                    mock_logger.error.assert_called_once()
        
        asyncio.run(run_test())

class TestErrorPatternMatching(unittest.TestCase):
    """Test cases for error pattern matching functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = EnhancedErrorRecoveryManager()
    
    def test_pattern_matching_accuracy(self):
        """Test accuracy of pattern matching"""
        test_patterns = [
            ("Rate limit exceeded", "rate limit.*exceeded"),
            ("Database connection error", "database.*error"),
            ("Invalid user input", "invalid.*input"),
            ("Authentication token expired", "token.*expired"),
            ("System out of memory", "out of memory")
        ]
        
        for error_msg, expected_pattern in test_patterns:
            category, pattern = self.manager.enhanced_categorize_error(
                Exception(error_msg), {}
            )
            
            if pattern:
                self.assertEqual(pattern.pattern, expected_pattern)
    
    def test_pattern_frequency_tracking(self):
        """Test pattern frequency tracking over time"""
        test_pattern = ErrorPattern(
            pattern="test.*error",
            category=EnhancedErrorCategory.PLATFORM,
            escalation_level=EscalationLevel.LOW,
            frequency_threshold=2,
            time_window_minutes=30
        )
        
        # Simulate errors over time
        error = Exception("Test error occurred")
        
        # First occurrence - should not escalate
        should_escalate_1 = self.manager._should_escalate_pattern(test_pattern, error)
        self.assertFalse(should_escalate_1)
        
        # Second occurrence - should escalate
        should_escalate_2 = self.manager._should_escalate_pattern(test_pattern, error)
        self.assertTrue(should_escalate_2)

if __name__ == '__main__':
    unittest.main()