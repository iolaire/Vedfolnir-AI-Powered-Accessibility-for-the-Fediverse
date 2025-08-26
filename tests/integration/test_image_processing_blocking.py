# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for image processing blocking during maintenance mode.

Tests maintenance mode checks for image upload processing, optimization tasks, and analysis operations.
Validates maintenance messaging for image processing attempts.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode, MaintenanceStatus
from maintenance_operation_classifier import MaintenanceOperationClassifier, OperationType
from maintenance_mode_middleware import MaintenanceModeMiddleware
from maintenance_response_helper import MaintenanceResponseHelper
from models import User, UserRole


class TestImageProcessingBlocking(unittest.TestCase):
    """Test cases for image processing blocking during maintenance mode"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_config_service.get_config.return_value = False
        self.mock_config_service.subscribe_to_changes = Mock()
        
        # Mock database manager
        self.mock_db_manager = Mock()
        
        # Create maintenance service
        self.maintenance_service = EnhancedMaintenanceModeService(
            config_service=self.mock_config_service,
            db_manager=self.mock_db_manager
        )
        
        # Create operation classifier
        self.operation_classifier = MaintenanceOperationClassifier()
        
        # Create response helper
        self.response_helper = MaintenanceResponseHelper()
        
        # Create test users
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = "admin"
        self.admin_user.role = UserRole.ADMIN
        
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 2
        self.regular_user.username = "user"
        self.regular_user.role = UserRole.REVIEWER
    
    def test_image_processing_endpoints_classification(self):
        """Test that image processing endpoints are correctly classified"""
        
        # Test specific image processing endpoints found in the application
        self.assertEqual(
            self.operation_classifier.classify_operation('/api/update_caption/123', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/api/regenerate_caption/456', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/api/review/batch/image/789/caption', 'PUT'),
            OperationType.IMAGE_PROCESSING
        )
        
        # Test generic image processing patterns
        self.assertEqual(
            self.operation_classifier.classify_operation('/image/upload', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/image/process', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/image/optimize', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/image/analysis', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/upload/image', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/api/image/process', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
        
        self.assertEqual(
            self.operation_classifier.classify_operation('/media/process', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
    
    def test_image_serving_not_classified_as_processing(self):
        """Test that image serving endpoints are not classified as image processing"""
        
        # Image serving should be classified as READ_OPERATIONS, not IMAGE_PROCESSING
        self.assertEqual(
            self.operation_classifier.classify_operation('/images/some_image.jpg', 'GET'),
            OperationType.READ_OPERATIONS
        )
        
        # Review endpoints should not be classified as image processing
        # (they are for reviewing, not processing images)
        self.assertNotEqual(
            self.operation_classifier.classify_operation('/review/123', 'GET'),
            OperationType.IMAGE_PROCESSING
        )
        
        self.assertNotEqual(
            self.operation_classifier.classify_operation('/review/123', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
    
    def test_image_processing_blocking_in_normal_maintenance(self):
        """Test that image processing is blocked in normal maintenance mode"""
        
        # Enable normal maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Image processing system maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test that image processing operations are blocked for regular users
        image_processing_endpoints = [
            '/api/update_caption/123',
            '/api/regenerate_caption/456',
            '/api/review/batch/image/789/caption',
            '/image/upload',
            '/image/process',
            '/image/optimize',
            '/image/analysis',
            '/upload/image',
            '/api/image/process',
            '/media/process'
        ]
        
        for endpoint in image_processing_endpoints:
            with self.subTest(endpoint=endpoint):
                # Regular user should be blocked
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertTrue(is_blocked, f"Regular user should be blocked from {endpoint}")
                
                # Admin user should bypass
                is_blocked_admin = self.maintenance_service.is_operation_blocked(endpoint, self.admin_user)
                self.assertFalse(is_blocked_admin, f"Admin user should bypass {endpoint}")
    
    def test_image_processing_blocking_in_emergency_maintenance(self):
        """Test that image processing is blocked in emergency maintenance mode"""
        
        # Enable emergency maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Critical image processing vulnerability fix",
            mode=MaintenanceMode.EMERGENCY,
            enabled_by="admin"
        )
        
        # Test that image processing operations are blocked for regular users
        image_processing_endpoints = [
            '/api/update_caption/123',
            '/api/regenerate_caption/456',
            '/image/upload',
            '/media/process'
        ]
        
        for endpoint in image_processing_endpoints:
            with self.subTest(endpoint=endpoint):
                # Regular user should be blocked
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertTrue(is_blocked, f"Regular user should be blocked from {endpoint} in emergency mode")
                
                # Admin user should still bypass
                is_blocked_admin = self.maintenance_service.is_operation_blocked(endpoint, self.admin_user)
                self.assertFalse(is_blocked_admin, f"Admin user should bypass {endpoint} in emergency mode")
    
    def test_image_processing_not_blocked_when_maintenance_disabled(self):
        """Test that image processing is not blocked when maintenance is disabled"""
        
        # Ensure maintenance is disabled
        self.maintenance_service.disable_maintenance()
        
        # Test that image processing operations are allowed
        image_processing_endpoints = [
            '/api/update_caption/123',
            '/api/regenerate_caption/456',
            '/image/upload',
            '/media/process'
        ]
        
        for endpoint in image_processing_endpoints:
            with self.subTest(endpoint=endpoint):
                # Regular user should not be blocked
                is_blocked = self.maintenance_service.is_operation_blocked(endpoint, self.regular_user)
                self.assertFalse(is_blocked, f"Regular user should not be blocked from {endpoint} when maintenance is disabled")
                
                # Admin user should not be blocked
                is_blocked_admin = self.maintenance_service.is_operation_blocked(endpoint, self.admin_user)
                self.assertFalse(is_blocked_admin, f"Admin user should not be blocked from {endpoint} when maintenance is disabled")
    
    def test_image_serving_not_blocked_during_maintenance(self):
        """Test that image serving is not blocked during maintenance (read-only operation)"""
        
        # Enable normal maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Image processing maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Image serving should not be blocked (it's a read operation)
        is_blocked = self.maintenance_service.is_operation_blocked('/images/some_image.jpg', self.regular_user)
        self.assertFalse(is_blocked, "Image serving should not be blocked during normal maintenance")
        
        # Even in emergency mode, image serving should be allowed for normal maintenance
        # (only blocked in emergency mode)
        self.maintenance_service.enable_maintenance(
            reason="Emergency maintenance",
            mode=MaintenanceMode.EMERGENCY,
            enabled_by="admin"
        )
        
        # In emergency mode, even read operations might be blocked
        is_blocked_emergency = self.maintenance_service.is_operation_blocked('/images/some_image.jpg', self.regular_user)
        # This depends on the blocking rules - in emergency mode, READ_OPERATIONS are blocked
        self.assertTrue(is_blocked_emergency, "Image serving should be blocked during emergency maintenance")
    
    def test_image_processing_maintenance_response_creation(self):
        """Test creation of maintenance responses for image processing operations"""
        
        # Enable maintenance mode
        maintenance_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Image processing system upgrade",
            estimated_duration=60,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        # Test response creation for image processing
        response_data = self.response_helper.create_json_response(
            operation='/api/update_caption/123',
            maintenance_status=maintenance_status,
            operation_type=OperationType.IMAGE_PROCESSING
        )
        
        # Verify response structure
        self.assertEqual(response_data['error'], 'Service Unavailable')
        self.assertTrue(response_data['maintenance_active'])
        self.assertEqual(response_data['maintenance_info']['mode'], 'normal')
        self.assertEqual(response_data['maintenance_info']['reason'], 'Image processing system upgrade')
        self.assertEqual(response_data['operation_info']['operation_type'], 'image_processing')
        self.assertEqual(response_data['operation_info']['title'], 'Image Processing Unavailable')
        self.assertIn('Image upload and processing operations are temporarily disabled', response_data['operation_info']['description'])
        self.assertEqual(response_data['operation_info']['icon'], '🖼️')
        self.assertIn('Existing images can still be viewed and reviewed', response_data['operation_info']['suggestion'])
    
    def test_image_processing_operation_description(self):
        """Test operation description for image processing"""
        
        description = self.operation_classifier.get_operation_description(OperationType.IMAGE_PROCESSING)
        self.assertEqual(description, "Image upload and processing operations")
    
    def test_image_processing_blocking_rules(self):
        """Test blocking rules for image processing in different maintenance modes"""
        
        # Test normal mode blocking
        blocked_operations_normal = self.operation_classifier.get_blocked_operations_for_mode(MaintenanceMode.NORMAL)
        self.assertIn(OperationType.IMAGE_PROCESSING, blocked_operations_normal)
        
        # Test emergency mode blocking
        blocked_operations_emergency = self.operation_classifier.get_blocked_operations_for_mode(MaintenanceMode.EMERGENCY)
        self.assertIn(OperationType.IMAGE_PROCESSING, blocked_operations_emergency)
        
        # Test test mode blocking (simulated)
        blocked_operations_test = self.operation_classifier.get_blocked_operations_for_mode(MaintenanceMode.TEST)
        self.assertIn(OperationType.IMAGE_PROCESSING, blocked_operations_test)
    
    def test_image_processing_with_flask_middleware(self):
        """Test image processing blocking with Flask middleware"""
        
        # Mock Flask app
        mock_app = Mock()
        mock_app.before_request = Mock()
        
        # Create middleware
        middleware = MaintenanceModeMiddleware(mock_app, self.maintenance_service)
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Image processing maintenance",
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Test middleware operation checking directly (without Flask request context)
        # Regular user should be blocked
        is_allowed = middleware.is_allowed_operation('/api/update_caption/123', self.regular_user, 'POST')
        self.assertFalse(is_allowed, "Regular user should not be allowed to update captions during maintenance")
        
        # Admin user should be allowed
        is_allowed_admin = middleware.is_allowed_operation('/api/update_caption/123', self.admin_user, 'POST')
        self.assertTrue(is_allowed_admin, "Admin user should be allowed to update captions during maintenance")
    
    def test_image_processing_maintenance_message(self):
        """Test maintenance message generation for image processing operations"""
        
        # Enable maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Image processing infrastructure upgrade",
            duration=90,
            mode=MaintenanceMode.NORMAL,
            enabled_by="admin"
        )
        
        # Get maintenance message for image processing
        message = self.maintenance_service.get_maintenance_message('/api/regenerate_caption/456')
        
        # Verify message content
        self.assertIn("System maintenance is currently in progress", message)
        self.assertIn("Image processing infrastructure upgrade", message)
        # The message shows estimated completion time instead of duration when duration is provided
        # So we check for either the duration or completion time format
        self.assertTrue("90 minutes" in message or "Expected completion:" in message, 
                       f"Message should contain duration or completion time: {message}")
        self.assertIn("image processing", message)
        self.assertIn("Please try again later", message)
    
    def test_image_processing_test_mode_simulation(self):
        """Test that image processing blocking is simulated in test mode"""
        
        # Enable test maintenance mode
        self.maintenance_service.enable_maintenance(
            reason="Testing image processing blocking",
            mode=MaintenanceMode.TEST,
            enabled_by="admin"
        )
        
        # Test that operations are not actually blocked in test mode
        is_blocked = self.maintenance_service.is_operation_blocked('/api/update_caption/123', self.regular_user)
        self.assertFalse(is_blocked, "Operations should not be actually blocked in test mode")
        
        # Verify test mode is active
        status = self.maintenance_service.get_maintenance_status()
        self.assertTrue(status.test_mode, "Test mode should be active")
        self.assertTrue(status.is_active, "Maintenance should be active")
        self.assertEqual(status.mode, MaintenanceMode.TEST, "Mode should be TEST")
    
    def test_caption_update_vs_regeneration_classification(self):
        """Test that caption update and regeneration are properly classified as image processing"""
        
        # Caption update should be image processing (modifying image metadata)
        self.assertEqual(
            self.operation_classifier.classify_operation('/api/update_caption/123', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
        
        # Caption regeneration should be image processing (AI processing of image)
        self.assertEqual(
            self.operation_classifier.classify_operation('/api/regenerate_caption/456', 'POST'),
            OperationType.IMAGE_PROCESSING
        )
        
        # Batch image caption updates should be image processing
        self.assertEqual(
            self.operation_classifier.classify_operation('/api/review/batch/image/789/caption', 'PUT'),
            OperationType.IMAGE_PROCESSING
        )
    
    def test_image_processing_vs_other_operations(self):
        """Test that image processing is distinguished from other operation types"""
        
        # Image processing should not be confused with caption generation
        # (caption generation is the AI service, image processing is updating/regenerating captions)
        image_processing_op = self.operation_classifier.classify_operation('/api/update_caption/123', 'POST')
        caption_generation_op = self.operation_classifier.classify_operation('/start_caption_generation', 'POST')
        
        self.assertEqual(image_processing_op, OperationType.IMAGE_PROCESSING)
        self.assertEqual(caption_generation_op, OperationType.CAPTION_GENERATION)
        self.assertNotEqual(image_processing_op, caption_generation_op)
        
        # Image processing should not be confused with batch operations
        # (unless it's a batch image operation)
        image_processing_single = self.operation_classifier.classify_operation('/api/update_caption/123', 'POST')
        batch_operation = self.operation_classifier.classify_operation('/api/batch_review', 'POST')
        
        self.assertEqual(image_processing_single, OperationType.IMAGE_PROCESSING)
        self.assertEqual(batch_operation, OperationType.BATCH_OPERATIONS)
        self.assertNotEqual(image_processing_single, batch_operation)


if __name__ == '__main__':
    unittest.main()