# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for MaintenanceOperationClassifier
"""

import unittest
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.maintenance.components.maintenance_operation_classifier import MaintenanceOperationClassifier, OperationType
from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import MaintenanceMode


class TestMaintenanceOperationClassifier(unittest.TestCase):
    """Test cases for MaintenanceOperationClassifier"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.classifier = MaintenanceOperationClassifier()
    
    def test_classify_caption_generation_operations(self):
        """Test classification of caption generation operations"""
        test_cases = [
            "/caption/generation",
            "/generate/caption",
            "/start/caption",
            "/api/caption",
            "/ollama/generate"
        ]
        
        for endpoint in test_cases:
            with self.subTest(endpoint=endpoint):
                result = self.classifier.classify_operation(endpoint)
                self.assertEqual(result, OperationType.CAPTION_GENERATION)
    
    def test_classify_job_creation_operations(self):
        """Test classification of job creation operations"""
        test_cases = [
            "/job/create",
            "/create/job",
            "/queue/job",
            "/api/jobs",
            "/background/task",
            "/task/queue"
        ]
        
        for endpoint in test_cases:
            with self.subTest(endpoint=endpoint):
                result = self.classifier.classify_operation(endpoint)
                self.assertEqual(result, OperationType.JOB_CREATION)
    
    def test_classify_platform_operations(self):
        """Test classification of platform operations"""
        test_cases = [
            "/platform/switch",
            "/switch/platform",
            "/platform/connect",
            "/platform/test",
            "/platform/credential",
            "/api/platform",
            "/mastodon/connect",
            "/pixelfed/connect"
        ]
        
        for endpoint in test_cases:
            with self.subTest(endpoint=endpoint):
                result = self.classifier.classify_operation(endpoint)
                self.assertEqual(result, OperationType.PLATFORM_OPERATIONS)
    
    def test_classify_batch_operations(self):
        """Test classification of batch operations"""
        test_cases = [
            "/batch/process",
            "/bulk/operation",
            "/bulk/review",
            "/bulk/caption",
            "/batch/review",
            "/api/batch",
            "/review/batch"
        ]
        
        for endpoint in test_cases:
            with self.subTest(endpoint=endpoint):
                result = self.classifier.classify_operation(endpoint)
                self.assertEqual(result, OperationType.BATCH_OPERATIONS)
    
    def test_classify_user_data_modification_operations(self):
        """Test classification of user data modification operations"""
        test_cases = [
            "/profile/update",
            "/user/settings",
            "/password/change",
            "/user/profile",
            "/settings/save",
            "/api/user/update",
            "/account/settings"
        ]
        
        for endpoint in test_cases:
            with self.subTest(endpoint=endpoint):
                result = self.classifier.classify_operation(endpoint)
                self.assertEqual(result, OperationType.USER_DATA_MODIFICATION)
    
    def test_classify_image_processing_operations(self):
        """Test classification of image processing operations"""
        test_cases = [
            "/image/upload",
            "/image/process",
            "/image/optimize",
            "/image/analysis",
            "/upload/image",
            "/api/image",
            "/media/process"
        ]
        
        for endpoint in test_cases:
            with self.subTest(endpoint=endpoint):
                result = self.classifier.classify_operation(endpoint)
                self.assertEqual(result, OperationType.IMAGE_PROCESSING)
    
    def test_classify_admin_operations(self):
        """Test classification of admin operations"""
        test_cases = [
            "/admin",
            "/admin/dashboard",
            "/api/admin",
            "/system/admin",
            "/maintenance",
            "/health/check",
            "/system/status"
        ]
        
        for endpoint in test_cases:
            with self.subTest(endpoint=endpoint):
                result = self.classifier.classify_operation(endpoint)
                self.assertEqual(result, OperationType.ADMIN_OPERATIONS)
    
    def test_classify_authentication_operations(self):
        """Test classification of authentication operations"""
        test_cases = [
            "/login",
            "/logout",
            "/auth",
            "/api/auth",
            "/session/create",
            "/session/destroy"
        ]
        
        for endpoint in test_cases:
            with self.subTest(endpoint=endpoint):
                result = self.classifier.classify_operation(endpoint)
                self.assertEqual(result, OperationType.AUTHENTICATION)
    
    def test_classify_read_operations(self):
        """Test classification of read operations"""
        test_cases = [
            "/api/status",
            "/api/health",
            "/static/css/style.css",
            "/css/main.css",
            "/js/app.js",
            "/images/logo.png",
            "/favicon.ico"
        ]
        
        for endpoint in test_cases:
            with self.subTest(endpoint=endpoint):
                result = self.classifier.classify_operation(endpoint)
                self.assertEqual(result, OperationType.READ_OPERATIONS)
    
    def test_classify_unknown_get_operations(self):
        """Test classification of unknown GET operations defaults to READ_OPERATIONS"""
        result = self.classifier.classify_operation("/unknown/endpoint", "GET")
        self.assertEqual(result, OperationType.READ_OPERATIONS)
    
    def test_classify_unknown_post_operations(self):
        """Test classification of unknown POST operations defaults to UNKNOWN"""
        result = self.classifier.classify_operation("/unknown/endpoint", "POST")
        self.assertEqual(result, OperationType.UNKNOWN)
    
    def test_classify_case_insensitive(self):
        """Test that classification is case insensitive"""
        test_cases = [
            ("/CAPTION/GENERATION", OperationType.CAPTION_GENERATION),
            ("/Admin/Dashboard", OperationType.ADMIN_OPERATIONS),
            ("/API/JOBS", OperationType.JOB_CREATION)
        ]
        
        for endpoint, expected_type in test_cases:
            with self.subTest(endpoint=endpoint):
                result = self.classifier.classify_operation(endpoint)
                self.assertEqual(result, expected_type)
    
    def test_is_blocked_operation_normal_mode(self):
        """Test operation blocking in normal maintenance mode"""
        blocked_operations = [
            OperationType.CAPTION_GENERATION,
            OperationType.JOB_CREATION,
            OperationType.PLATFORM_OPERATIONS,
            OperationType.BATCH_OPERATIONS,
            OperationType.USER_DATA_MODIFICATION,
            OperationType.IMAGE_PROCESSING
        ]
        
        allowed_operations = [
            OperationType.ADMIN_OPERATIONS,
            OperationType.AUTHENTICATION,
            OperationType.READ_OPERATIONS
        ]
        
        for operation_type in blocked_operations:
            with self.subTest(operation_type=operation_type):
                result = self.classifier.is_blocked_operation(operation_type, MaintenanceMode.NORMAL)
                self.assertTrue(result)
        
        for operation_type in allowed_operations:
            with self.subTest(operation_type=operation_type):
                result = self.classifier.is_blocked_operation(operation_type, MaintenanceMode.NORMAL)
                self.assertFalse(result)
    
    def test_is_blocked_operation_emergency_mode(self):
        """Test operation blocking in emergency maintenance mode"""
        blocked_operations = [
            OperationType.CAPTION_GENERATION,
            OperationType.JOB_CREATION,
            OperationType.PLATFORM_OPERATIONS,
            OperationType.BATCH_OPERATIONS,
            OperationType.USER_DATA_MODIFICATION,
            OperationType.IMAGE_PROCESSING,
            OperationType.READ_OPERATIONS  # Also blocked in emergency mode
        ]
        
        allowed_operations = [
            OperationType.ADMIN_OPERATIONS,
            OperationType.AUTHENTICATION
        ]
        
        for operation_type in blocked_operations:
            with self.subTest(operation_type=operation_type):
                result = self.classifier.is_blocked_operation(operation_type, MaintenanceMode.EMERGENCY)
                self.assertTrue(result)
        
        for operation_type in allowed_operations:
            with self.subTest(operation_type=operation_type):
                result = self.classifier.is_blocked_operation(operation_type, MaintenanceMode.EMERGENCY)
                self.assertFalse(result)
    
    def test_is_blocked_operation_test_mode(self):
        """Test operation blocking in test maintenance mode"""
        # Test mode has same blocking rules as normal mode
        blocked_operations = [
            OperationType.CAPTION_GENERATION,
            OperationType.JOB_CREATION,
            OperationType.PLATFORM_OPERATIONS,
            OperationType.BATCH_OPERATIONS,
            OperationType.USER_DATA_MODIFICATION,
            OperationType.IMAGE_PROCESSING
        ]
        
        for operation_type in blocked_operations:
            with self.subTest(operation_type=operation_type):
                result = self.classifier.is_blocked_operation(operation_type, MaintenanceMode.TEST)
                self.assertTrue(result)
    
    def test_admin_operations_never_blocked(self):
        """Test that admin operations are never blocked in any mode"""
        modes = [MaintenanceMode.NORMAL, MaintenanceMode.EMERGENCY, MaintenanceMode.TEST]
        
        for mode in modes:
            with self.subTest(mode=mode):
                result = self.classifier.is_blocked_operation(OperationType.ADMIN_OPERATIONS, mode)
                self.assertFalse(result)
    
    def test_authentication_operations_never_blocked(self):
        """Test that authentication operations are never blocked in any mode"""
        modes = [MaintenanceMode.NORMAL, MaintenanceMode.EMERGENCY, MaintenanceMode.TEST]
        
        for mode in modes:
            with self.subTest(mode=mode):
                result = self.classifier.is_blocked_operation(OperationType.AUTHENTICATION, mode)
                self.assertFalse(result)
    
    def test_get_operation_description(self):
        """Test getting operation descriptions"""
        descriptions = {
            OperationType.CAPTION_GENERATION: "AI caption generation and processing",
            OperationType.JOB_CREATION: "Background job creation and queuing",
            OperationType.ADMIN_OPERATIONS: "Administrative functions and system management",
            OperationType.UNKNOWN: "Unclassified operations"
        }
        
        for operation_type, expected_description in descriptions.items():
            with self.subTest(operation_type=operation_type):
                result = self.classifier.get_operation_description(operation_type)
                self.assertEqual(result, expected_description)
    
    def test_add_custom_classification(self):
        """Test adding custom classification patterns"""
        # Add custom pattern
        self.classifier.add_custom_classification(r'/custom/endpoint', OperationType.BATCH_OPERATIONS)
        
        # Test classification with custom pattern
        result = self.classifier.classify_operation("/custom/endpoint")
        self.assertEqual(result, OperationType.BATCH_OPERATIONS)
    
    def test_add_invalid_custom_classification(self):
        """Test adding invalid regex pattern raises ValueError"""
        with self.assertRaises(ValueError):
            self.classifier.add_custom_classification(r'[invalid regex', OperationType.BATCH_OPERATIONS)
    
    def test_remove_custom_classification(self):
        """Test removing custom classification patterns"""
        # Add custom pattern
        pattern = r'/custom/endpoint'
        self.classifier.add_custom_classification(pattern, OperationType.BATCH_OPERATIONS)
        
        # Remove pattern
        result = self.classifier.remove_custom_classification(pattern)
        self.assertTrue(result)
        
        # Test that pattern is no longer used
        classification = self.classifier.classify_operation("/custom/endpoint", "POST")
        self.assertEqual(classification, OperationType.UNKNOWN)  # Should default to UNKNOWN for POST
    
    def test_remove_nonexistent_custom_classification(self):
        """Test removing non-existent custom pattern returns False"""
        result = self.classifier.remove_custom_classification(r'/nonexistent')
        self.assertFalse(result)
    
    def test_get_all_operation_types(self):
        """Test getting all operation types"""
        result = self.classifier.get_all_operation_types()
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), len(OperationType))
        self.assertIn(OperationType.CAPTION_GENERATION, result)
        self.assertIn(OperationType.ADMIN_OPERATIONS, result)
    
    def test_get_blocked_operations_for_mode(self):
        """Test getting blocked operations for specific mode"""
        normal_blocked = self.classifier.get_blocked_operations_for_mode(MaintenanceMode.NORMAL)
        emergency_blocked = self.classifier.get_blocked_operations_for_mode(MaintenanceMode.EMERGENCY)
        
        self.assertIsInstance(normal_blocked, list)
        self.assertIsInstance(emergency_blocked, list)
        
        # Emergency mode should block more operations than normal mode
        self.assertGreater(len(emergency_blocked), len(normal_blocked))
        
        # Both should block caption generation
        self.assertIn(OperationType.CAPTION_GENERATION, normal_blocked)
        self.assertIn(OperationType.CAPTION_GENERATION, emergency_blocked)
        
        # Only emergency should block read operations
        self.assertNotIn(OperationType.READ_OPERATIONS, normal_blocked)
        self.assertIn(OperationType.READ_OPERATIONS, emergency_blocked)
    
    def test_get_classification_stats(self):
        """Test getting classification statistics"""
        stats = self.classifier.get_classification_stats()
        
        self.assertIn('built_in_patterns', stats)
        self.assertIn('custom_patterns', stats)
        self.assertIn('operation_types', stats)
        self.assertIn('maintenance_modes', stats)
        
        self.assertGreater(stats['built_in_patterns'], 0)
        self.assertEqual(stats['custom_patterns'], 0)  # No custom patterns added yet
        self.assertEqual(stats['operation_types'], len(OperationType))
        self.assertEqual(stats['maintenance_modes'], 3)  # NORMAL, EMERGENCY, TEST
    
    def test_custom_patterns_take_precedence(self):
        """Test that custom patterns take precedence over built-in patterns"""
        # Add custom pattern that would normally be classified as CAPTION_GENERATION
        self.classifier.add_custom_classification(r'/caption/generation', OperationType.BATCH_OPERATIONS)
        
        result = self.classifier.classify_operation("/caption/generation")
        self.assertEqual(result, OperationType.BATCH_OPERATIONS)


if __name__ == '__main__':
    unittest.main()