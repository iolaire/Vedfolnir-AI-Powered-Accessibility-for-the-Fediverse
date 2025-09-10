# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Operation Classifier

Classifies operations into categories for granular maintenance mode blocking control.
Maps Flask endpoints to operation types and determines blocking behavior.
"""

import logging
import re
from typing import Dict, List, Pattern
from enum import Enum

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Operation types for maintenance mode blocking"""
    CAPTION_GENERATION = "caption_generation"
    JOB_CREATION = "job_creation"
    PLATFORM_OPERATIONS = "platform_operations"
    BATCH_OPERATIONS = "batch_operations"
    USER_DATA_MODIFICATION = "user_data_modification"
    IMAGE_PROCESSING = "image_processing"
    ADMIN_OPERATIONS = "admin_operations"
    READ_OPERATIONS = "read_operations"
    AUTHENTICATION = "authentication"
    UNKNOWN = "unknown"


class MaintenanceOperationClassifier:
    """
    Classifies operations into categories for granular blocking control
    
    Features:
    - Endpoint pattern matching for operation classification
    - Configurable blocking rules per maintenance mode
    - Custom classification rule support
    - Operation description and documentation
    """
    
    def __init__(self):
        """Initialize operation classifier with default patterns"""
        
        # Endpoint patterns for each operation type
        self._operation_patterns: Dict[OperationType, List[Pattern]] = {
            OperationType.CAPTION_GENERATION: [
                re.compile(r'/start_caption_generation', re.IGNORECASE),  # Specific start endpoint
                re.compile(r'/generate.*caption', re.IGNORECASE),
                # More specific patterns to avoid matching job management endpoints
                re.compile(r'/api/caption/generate', re.IGNORECASE),
                re.compile(r'/ollama', re.IGNORECASE),
            ],
            
            OperationType.JOB_CREATION: [
                re.compile(r'/job.*create', re.IGNORECASE),
                re.compile(r'/create.*job', re.IGNORECASE),
                re.compile(r'/queue.*job', re.IGNORECASE),
                re.compile(r'/api/jobs', re.IGNORECASE),
                re.compile(r'/background.*task', re.IGNORECASE),
                re.compile(r'/task.*queue', re.IGNORECASE),
                # Caption generation job management endpoints
                re.compile(r'/api/caption_generation/cancel', re.IGNORECASE),
                re.compile(r'/api/caption_generation/retry', re.IGNORECASE),
                re.compile(r'/api/review/queue_regeneration', re.IGNORECASE),
                # Job creation patterns
                re.compile(r'/start.*generation', re.IGNORECASE),
                re.compile(r'/generate.*batch', re.IGNORECASE),
            ],
            
            OperationType.PLATFORM_OPERATIONS: [
                re.compile(r'/platform.*switch', re.IGNORECASE),
                re.compile(r'/switch.*platform', re.IGNORECASE),
                re.compile(r'/platform.*connect', re.IGNORECASE),
                re.compile(r'/platform.*test', re.IGNORECASE),
                re.compile(r'/platform.*credential', re.IGNORECASE),
                re.compile(r'/api/platform', re.IGNORECASE),
                re.compile(r'/mastodon.*connect', re.IGNORECASE),
                re.compile(r'/pixelfed.*connect', re.IGNORECASE),
                # Platform management routes
                re.compile(r'/platform_management', re.IGNORECASE),
                re.compile(r'/api/add_platform', re.IGNORECASE),
                re.compile(r'/api/switch_platform', re.IGNORECASE),
                re.compile(r'/api/test_platform', re.IGNORECASE),
                re.compile(r'/api/get_platform', re.IGNORECASE),
                re.compile(r'/api/edit_platform', re.IGNORECASE),
                re.compile(r'/api/delete_platform', re.IGNORECASE),
            ],
            
            OperationType.BATCH_OPERATIONS: [
                re.compile(r'/batch.*process', re.IGNORECASE),
                re.compile(r'/bulk.*operation', re.IGNORECASE),
                re.compile(r'/bulk.*review', re.IGNORECASE),
                re.compile(r'/bulk.*caption', re.IGNORECASE),
                re.compile(r'/batch.*review', re.IGNORECASE),
                re.compile(r'/api/batch(?!.*image)', re.IGNORECASE),  # Exclude image-specific batch operations
                re.compile(r'/review.*batch', re.IGNORECASE),
                # Batch review routes (but exclude image-specific ones)
                re.compile(r'/api/batch_review', re.IGNORECASE),
                re.compile(r'/review/batches', re.IGNORECASE),
                re.compile(r'/review/batch/(?!image)', re.IGNORECASE),  # Exclude /review/batch/image/
                re.compile(r'/api/review/batch/.*/bulk_approve', re.IGNORECASE),
                re.compile(r'/api/review/batch/.*/bulk_reject', re.IGNORECASE),
                re.compile(r'/api/review/batch/.*/quality_metrics', re.IGNORECASE),
                re.compile(r'/api/review/batch/.*/statistics', re.IGNORECASE),
                # Note: /api/review/batch/image/.*/caption moved to IMAGE_PROCESSING
            ],
            
            OperationType.USER_DATA_MODIFICATION: [
                re.compile(r'/profile.*update', re.IGNORECASE),
                re.compile(r'/user.*settings', re.IGNORECASE),
                re.compile(r'/password.*change', re.IGNORECASE),
                re.compile(r'/user.*profile', re.IGNORECASE),
                re.compile(r'/settings.*save', re.IGNORECASE),
                re.compile(r'/api/user.*update', re.IGNORECASE),
                re.compile(r'/account.*settings', re.IGNORECASE),
                # Specific endpoints found in the application
                re.compile(r'/caption_settings', re.IGNORECASE),
                re.compile(r'/api/caption_settings', re.IGNORECASE),
                re.compile(r'/save_caption_settings', re.IGNORECASE),
                re.compile(r'/api/validate_caption_settings', re.IGNORECASE),
                re.compile(r'/api/update_user_settings', re.IGNORECASE),
            ],
            
            OperationType.IMAGE_PROCESSING: [
                re.compile(r'/image.*upload', re.IGNORECASE),
                re.compile(r'/image.*process', re.IGNORECASE),
                re.compile(r'/image.*optimize', re.IGNORECASE),
                re.compile(r'/image.*analysis', re.IGNORECASE),
                re.compile(r'/upload.*image', re.IGNORECASE),
                re.compile(r'/api/image', re.IGNORECASE),
                re.compile(r'/media.*process', re.IGNORECASE),
                # Specific endpoints found in the application
                re.compile(r'/api/update_caption/\d+', re.IGNORECASE),
                re.compile(r'/api/regenerate_caption/\d+', re.IGNORECASE),
                re.compile(r'/api/review/batch/image/\d+/caption', re.IGNORECASE),
                # Note: /images/<path:filename> is for serving images (read-only), not processing
                # Note: /review/<int:image_id> endpoints are for reviewing, not processing
            ],
            
            OperationType.ADMIN_OPERATIONS: [
                re.compile(r'/admin', re.IGNORECASE),
                re.compile(r'/api/admin', re.IGNORECASE),
                re.compile(r'/system.*admin', re.IGNORECASE),
                re.compile(r'/maintenance', re.IGNORECASE),
                re.compile(r'/health.*check', re.IGNORECASE),
                re.compile(r'/system.*status', re.IGNORECASE),
            ],
            
            OperationType.AUTHENTICATION: [
                re.compile(r'/login', re.IGNORECASE),
                re.compile(r'/logout', re.IGNORECASE),
                re.compile(r'/auth', re.IGNORECASE),
                re.compile(r'/api/auth', re.IGNORECASE),
                re.compile(r'/session.*create', re.IGNORECASE),
                re.compile(r'/session.*destroy', re.IGNORECASE),
            ],
            
            OperationType.READ_OPERATIONS: [
                re.compile(r'/api/status', re.IGNORECASE),
                re.compile(r'/api/health', re.IGNORECASE),
                re.compile(r'/static/', re.IGNORECASE),
                re.compile(r'/css/', re.IGNORECASE),
                re.compile(r'/js/', re.IGNORECASE),
                re.compile(r'/images/', re.IGNORECASE),
                re.compile(r'/favicon', re.IGNORECASE),
                # Job status and results (read-only operations)
                re.compile(r'/api/caption_generation/status', re.IGNORECASE),
                re.compile(r'/api/caption_generation/results', re.IGNORECASE),
                re.compile(r'/api/caption_generation/error_details', re.IGNORECASE),
                re.compile(r'/api/progress_stream', re.IGNORECASE),
            ],
        }
        
        # Custom patterns added at runtime
        self._custom_patterns: Dict[str, OperationType] = {}
        
        # Blocking rules per maintenance mode
        from enhanced_maintenance_mode_service import MaintenanceMode
        self._blocking_rules: Dict[MaintenanceMode, List[OperationType]] = {
            MaintenanceMode.NORMAL: [
                OperationType.CAPTION_GENERATION,
                OperationType.JOB_CREATION,
                OperationType.PLATFORM_OPERATIONS,
                OperationType.BATCH_OPERATIONS,
                OperationType.USER_DATA_MODIFICATION,
                OperationType.IMAGE_PROCESSING,
            ],
            
            MaintenanceMode.EMERGENCY: [
                OperationType.CAPTION_GENERATION,
                OperationType.JOB_CREATION,
                OperationType.PLATFORM_OPERATIONS,
                OperationType.BATCH_OPERATIONS,
                OperationType.USER_DATA_MODIFICATION,
                OperationType.IMAGE_PROCESSING,
                OperationType.READ_OPERATIONS,  # Block even read operations in emergency
            ],
            
            MaintenanceMode.TEST: [
                # Test mode simulates blocking but doesn't actually block
                OperationType.CAPTION_GENERATION,
                OperationType.JOB_CREATION,
                OperationType.PLATFORM_OPERATIONS,
                OperationType.BATCH_OPERATIONS,
                OperationType.USER_DATA_MODIFICATION,
                OperationType.IMAGE_PROCESSING,
            ],
        }
    
    def classify_operation(self, endpoint: str, method: str = 'GET') -> OperationType:
        """
        Classify operation based on endpoint and HTTP method
        
        Args:
            endpoint: Flask endpoint or URL path
            method: HTTP method (GET, POST, etc.)
            
        Returns:
            OperationType classification
        """
        try:
            # Check custom patterns first
            for pattern, operation_type in self._custom_patterns.items():
                if re.search(pattern, endpoint, re.IGNORECASE):
                    logger.debug(f"Classified {endpoint} as {operation_type.value} (custom pattern)")
                    return operation_type
            
            # Check built-in patterns in priority order (more specific first)
            priority_order = [
                OperationType.READ_OPERATIONS,      # Check read operations first
                OperationType.ADMIN_OPERATIONS,     # Then admin operations
                OperationType.AUTHENTICATION,       # Then authentication
                OperationType.CAPTION_GENERATION,   # Then caption generation (specific)
                OperationType.IMAGE_PROCESSING,     # Then image processing (specific)
                OperationType.JOB_CREATION,         # Then job creation (general)
                OperationType.PLATFORM_OPERATIONS,
                OperationType.USER_DATA_MODIFICATION,
                OperationType.BATCH_OPERATIONS,     # Check batch operations later (more general)
            ]
            
            # Check patterns in priority order
            for operation_type in priority_order:
                if operation_type in self._operation_patterns:
                    patterns = self._operation_patterns[operation_type]
                    for pattern in patterns:
                        if pattern.search(endpoint):
                            logger.debug(f"Classified {endpoint} as {operation_type.value}")
                            return operation_type
            
            # Check any remaining operation types not in priority order
            for operation_type, patterns in self._operation_patterns.items():
                if operation_type not in priority_order:
                    for pattern in patterns:
                        if pattern.search(endpoint):
                            logger.debug(f"Classified {endpoint} as {operation_type.value}")
                            return operation_type
            
            # Special handling for POST requests to read endpoints
            if method.upper() == 'POST':
                # POST requests are generally write operations
                if any(pattern.search(endpoint) for pattern in self._operation_patterns[OperationType.READ_OPERATIONS]):
                    # This is a POST to what looks like a read endpoint, classify as unknown
                    logger.debug(f"Classified POST {endpoint} as UNKNOWN (POST to read endpoint)")
                    return OperationType.UNKNOWN
            
            # Default classification for unmatched endpoints
            if method.upper() in ['GET', 'HEAD', 'OPTIONS']:
                logger.debug(f"Classified {endpoint} as READ_OPERATIONS (default for {method})")
                return OperationType.READ_OPERATIONS
            else:
                logger.debug(f"Classified {endpoint} as UNKNOWN (unmatched {method})")
                return OperationType.UNKNOWN
                
        except Exception as e:
            logger.error(f"Error classifying operation {endpoint}: {str(e)}")
            return OperationType.UNKNOWN
    
    def is_blocked_operation(self, operation_type: OperationType, maintenance_mode) -> bool:
        """
        Determine if operation type should be blocked in given maintenance mode
        
        Args:
            operation_type: Type of operation
            maintenance_mode: Current maintenance mode
            
        Returns:
            True if operation should be blocked, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from enhanced_maintenance_mode_service import MaintenanceMode
            
            # Admin operations are never blocked
            if operation_type == OperationType.ADMIN_OPERATIONS:
                return False
            
            # Authentication operations are never blocked (users need to login)
            if operation_type == OperationType.AUTHENTICATION:
                return False
            
            # Check blocking rules for the maintenance mode
            blocked_operations = self._blocking_rules.get(maintenance_mode, [])
            is_blocked = operation_type in blocked_operations
            
            logger.debug(f"Operation {operation_type.value} blocked in {maintenance_mode.value}: {is_blocked}")
            return is_blocked
            
        except Exception as e:
            logger.error(f"Error checking operation blocking: {str(e)}")
            # Default to not blocking on error to prevent system lockout
            return False
    
    def get_operation_description(self, operation_type: OperationType) -> str:
        """
        Get human-readable description of operation type
        
        Args:
            operation_type: Operation type to describe
            
        Returns:
            Description string
        """
        descriptions = {
            OperationType.CAPTION_GENERATION: "AI caption generation and processing",
            OperationType.JOB_CREATION: "Background job creation and queuing",
            OperationType.PLATFORM_OPERATIONS: "Platform switching and connection management",
            OperationType.BATCH_OPERATIONS: "Bulk processing and batch operations",
            OperationType.USER_DATA_MODIFICATION: "User profile and settings updates",
            OperationType.IMAGE_PROCESSING: "Image upload and processing operations",
            OperationType.ADMIN_OPERATIONS: "Administrative functions and system management",
            OperationType.READ_OPERATIONS: "Read-only operations and static content",
            OperationType.AUTHENTICATION: "User authentication and session management",
            OperationType.UNKNOWN: "Unclassified operations",
        }
        
        return descriptions.get(operation_type, "Unknown operation type")
    
    def add_custom_classification(self, pattern: str, operation_type: OperationType) -> None:
        """
        Add custom classification pattern
        
        Args:
            pattern: Regular expression pattern to match endpoints
            operation_type: Operation type to assign to matching endpoints
        """
        try:
            # Validate pattern by compiling it
            re.compile(pattern)
            
            self._custom_patterns[pattern] = operation_type
            logger.info(f"Added custom classification pattern: {pattern} -> {operation_type.value}")
            
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {str(e)}")
            raise ValueError(f"Invalid regex pattern: {str(e)}")
    
    def remove_custom_classification(self, pattern: str) -> bool:
        """
        Remove custom classification pattern
        
        Args:
            pattern: Pattern to remove
            
        Returns:
            True if pattern was found and removed, False otherwise
        """
        if pattern in self._custom_patterns:
            del self._custom_patterns[pattern]
            logger.info(f"Removed custom classification pattern: {pattern}")
            return True
        
        return False
    
    def get_all_operation_types(self) -> List[OperationType]:
        """
        Get list of all available operation types
        
        Returns:
            List of OperationType values
        """
        return list(OperationType)
    
    def get_blocked_operations_for_mode(self, maintenance_mode) -> List[OperationType]:
        """
        Get list of operations blocked in specific maintenance mode
        
        Args:
            maintenance_mode: Maintenance mode to check
            
        Returns:
            List of blocked operation types
        """
        try:
            return self._blocking_rules.get(maintenance_mode, [])
        except Exception as e:
            logger.error(f"Error getting blocked operations for mode: {str(e)}")
            return []
    
    def get_classification_stats(self) -> Dict[str, int]:
        """
        Get statistics about classification patterns
        
        Returns:
            Dictionary with classification statistics
        """
        return {
            'built_in_patterns': sum(len(patterns) for patterns in self._operation_patterns.values()),
            'custom_patterns': len(self._custom_patterns),
            'operation_types': len(OperationType),
            'maintenance_modes': len(self._blocking_rules)
        }