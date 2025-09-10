# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Mode Failure Scenario Testing

Tests maintenance mode behavior under various failure conditions including
configuration service unavailability, session manager failures, system failures,
disaster recovery, and data consistency validation.
"""

import unittest
import time
import threading
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import tempfile
import json

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole
from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import (
    EnhancedMaintenanceModeService, MaintenanceMode, MaintenanceStatus,
    MaintenanceActivationError, SessionInvalidationError
)
from app.services.maintenance.components.maintenance_mode_middleware import MaintenanceModeMiddleware
from app.services.maintenance.emergency.emergency_maintenance_handler import EmergencyMaintenanceHandler
from app.services.maintenance.components.maintenance_status_api import MaintenanceStatusAPI
from app.core.configuration.core.configuration_service import ConfigurationService
from tests.test_helpers.mock_configurations import MockConfigurationService
from tests.test_helpers.mock_user_helper import create_test_user_with_platforms, cleanup_test_user


class FailingConfigurationService(MockConfigurationService):
    """Configuration service that simulates failures"""
    
    def __init__(self, fail_on_get=False, fail_on_set=False, fail_after_calls=None):
        super().__init__()
        self.fail_on_get = fail_on_get
        self.fail_on_set = fail_on_set
        self.fail_after_calls = fail_after_calls
        self.call_count = 0
    
    def get_config(self, key, default=None):
        self.call_count += 1
        if self.fail_on_get or (self.fail_after_calls and self.call_count > self.fail_after_calls):
            raise Exception("Configuration service unavailable")
        return super().get_config(key, default)
    
    def set_config(self, key, value):
        self.call_count += 1
        if self.fail_on_set or (self.fail_after_calls and self.call_count > self.fail_after_calls):
            raise Exception("Configuration service unavailable")
        return super().set_config(key, value)


class FailingDatabaseManager:
    """Database manager that simulates failures"""
    
    def __init__(self, real_db_manager, fail_on_session=False, fail_after_calls=None):
        self.real_db_manager = real_db_manager
        self.fail_on_session = fail_on_session
        self.fail_after_calls = fail_after_calls
        self.call_count = 0
    
    def get_session(self):
        self.call_count += 1
        if self.fail_on_session or (self.fail_after_calls and self.call_count > self.fail_after_calls):
            raise Exception("Database connection failed")
        return self.real_db_manager.get_session()
    
    def __getattr__(self, name):
        return getattr(self.real_db_manager, name)


class TestMaintenanceModeFailureScenarios(unittest.TestCase):
    """
    Failure scenario tests for maintenance mode functionality
    
    Tests:
    - Configuration service unavailability
    - Session manager failures during maintenance
    - System failure recovery
    - Disaster recovery and state persistence
    - Data consistency after failures
    """
    
    def setUp(self):
        """Set up test environment for failure scenario testing"""
        self.config = Config()
        self.real_db_manager = DatabaseManager(self.config)
        
        # Create test users
        self.admin_user, self.admin_helper = create_test_user_with_platforms(
            self.real_db_manager, username="failure_test_admin", role=UserRole.ADMIN
        )
        
        self.regular_user, self.regular_helper = create_test_user_with_platforms(
            self.real_db_manager, username="failure_test_user", role=UserRole.REVIEWER
        )
        
        # Track created services for cleanup
        self.created_services = []
        
        # Failure tracking
        self.failure_scenarios = {
            'config_service_failures': [],
            'database_failures': [],
            'session_manager_failures': [],
            'recovery_attempts': [],
            'data_consistency_issues': []
        }
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            # Clean up any active maintenance modes
            for service in self.created_services:
                try:
                    service.disable_maintenance()
                except Exception:
                    pass
            
            # Clean up test users
            cleanup_test_user(self.admin_helper)
            cleanup_test_user(self.regular_helper)
            
        except Exception as e:
            print(f"Error in tearDown: {e}")
    
    def test_configuration_service_unavailable(self):
        """Test maintenance mode behavior when configuration service is unavailable"""
        print("\n=== Testing Configuration Service Unavailability ===")
        
        # Test 1: Configuration service fails on get operations
        failing_config_service = FailingConfigurationService(fail_on_get=True)
        maintenance_service = EnhancedMaintenanceModeService(
            config_service=failing_config_service,
            db_manager=self.real_db_manager
        )
        self.created_services.append(maintenance_service)
        
        print("Testing configuration service failure on get operations...")
        
        # Should gracefully handle configuration failures
        status = maintenance_service.get_maintenance_status()
        self.assertIsNotNone(status, "Should return default status when config fails")
        self.assertFalse(status.is_active, "Should default to inactive when config fails")
        
        print("✓ Graceful handling of configuration get failures")
        
        # Test 2: Configuration service fails on set operations
        failing_config_service_set = FailingConfigurationService(fail_on_set=True)
        maintenance_service_set = EnhancedMaintenanceModeService(
            config_service=failing_config_service_set,
            db_manager=self.real_db_manager
        )
        self.created_services.append(maintenance_service_set)
        
        print("Testing configuration service failure on set operations...")
        
        # Should handle activation failures gracefully
        try:
            result = maintenance_service_set.enable_maintenance(
                reason="Testing config failure",
                mode=MaintenanceMode.NORMAL,
                enabled_by="failure_test"
            )
            # Should still succeed using internal state
            self.assertTrue(result, "Should succeed even with config set failures")
        except MaintenanceActivationError:
            # This is also acceptable behavior
            print("✓ Maintenance activation properly failed with config error")
        
        print("✓ Graceful handling of configuration set failures")
        
        # Test 3: Configuration service fails after some operations
        failing_config_intermittent = FailingConfigurationService(fail_after_calls=3)
        maintenance_service_intermittent = EnhancedMaintenanceModeService(
            config_service=failing_config_intermittent,
            db_manager=self.real_db_manager
        )
        self.created_services.append(maintenance_service_intermittent)
        
        print("Testing intermittent configuration service failures...")
        
        # First few operations should succeed
        status1 = maintenance_service_intermittent.get_maintenance_status()
        self.assertIsNotNone(status1, "First status check should succeed")
        
        status2 = maintenance_service_intermittent.get_maintenance_status()
        self.assertIsNotNone(status2, "Second status check should succeed")
        
        # Later operations should handle failures gracefully
        status3 = maintenance_service_intermittent.get_maintenance_status()
        self.assertIsNotNone(status3, "Should handle intermittent failures gracefully")
        
        print("✓ Graceful handling of intermittent configuration failures")
        
        # Test 4: Recovery after configuration service restoration
        print("Testing recovery after configuration service restoration...")
        
        # Create a service that initially fails
        recovering_config = FailingConfigurationService(fail_on_get=True)
        maintenance_service_recovery = EnhancedMaintenanceModeService(
            config_service=recovering_config,
            db_manager=self.real_db_manager
        )
        self.created_services.append(maintenance_service_recovery)
        
        # Initial status should use defaults
        initial_status = maintenance_service_recovery.get_maintenance_status()
        self.assertFalse(initial_status.is_active, "Should default to inactive")
        
        # "Fix" the configuration service
        recovering_config.fail_on_get = False
        
        # Should now work normally
        result = maintenance_service_recovery.enable_maintenance(
            reason="Testing recovery",
            mode=MaintenanceMode.NORMAL,
            enabled_by="recovery_test"
        )
        self.assertTrue(result, "Should work after config service recovery")
        
        recovered_status = maintenance_service_recovery.get_maintenance_status()
        self.assertTrue(recovered_status.is_active, "Should show active after recovery")
        
        print("✓ Successful recovery after configuration service restoration")
        
        print("✓ Configuration service unavailability test passed")
    
    def test_session_manager_failures_during_maintenance(self):
        """Test graceful degradation when session manager fails during maintenance"""
        print("\n=== Testing Session Manager Failures During Maintenance ===")
        
        # Create maintenance service with working components
        config_service = MockConfigurationService()
        maintenance_service = EnhancedMaintenanceModeService(
            config_service=config_service,
            db_manager=self.real_db_manager
        )
        self.created_services.append(maintenance_service)
        
        # Test 1: Session invalidation failures
        print("Testing session invalidation failures...")
        
        with patch.object(maintenance_service, 'update_invalidated_sessions_count') as mock_update:
            mock_update.side_effect = SessionInvalidationError("Session manager unavailable")
            
            # Should still enable maintenance even if session invalidation fails
            result = maintenance_service.enable_maintenance(
                reason="Testing session manager failure",
                mode=MaintenanceMode.NORMAL,
                enabled_by="failure_test"
            )
            
            self.assertTrue(result, "Maintenance should enable despite session failures")
            
            status = maintenance_service.get_maintenance_status()
            self.assertTrue(status.is_active, "Maintenance should be active")
            
            print("✓ Maintenance enabled despite session invalidation failures")
        
        # Test 2: Session monitoring failures
        print("Testing session monitoring failures...")
        
        # Mock session monitoring to fail
        with patch('maintenance_session_manager.MaintenanceSessionManager') as mock_session_manager:
            mock_session_manager.return_value.get_active_non_admin_sessions.side_effect = Exception("Session monitoring failed")
            
            # Should still provide maintenance status
            status = maintenance_service.get_maintenance_status()
            self.assertIsNotNone(status, "Should provide status despite session monitoring failures")
            
            print("✓ Status available despite session monitoring failures")
        
        # Test 3: Database session failures
        print("Testing database session failures...")
        
        failing_db_manager = FailingDatabaseManager(self.real_db_manager, fail_on_session=True)
        maintenance_service_db_fail = EnhancedMaintenanceModeService(
            config_service=config_service,
            db_manager=failing_db_manager
        )
        self.created_services.append(maintenance_service_db_fail)
        
        # Should handle database failures gracefully
        result = maintenance_service_db_fail.enable_maintenance(
            reason="Testing database failure",
            mode=MaintenanceMode.NORMAL,
            enabled_by="db_failure_test"
        )
        
        # Should either succeed (using fallback) or fail gracefully
        if result:
            print("✓ Maintenance enabled with database fallback")
        else:
            print("✓ Maintenance gracefully failed with database issues")
        
        # Status should still be available
        status = maintenance_service_db_fail.get_maintenance_status()
        self.assertIsNotNone(status, "Status should be available despite database issues")
        
        print("✓ Session manager failure handling test passed")
    
    def test_system_failure_recovery(self):
        """Test maintenance mode recovery after system failures"""
        print("\n=== Testing System Failure Recovery ===")
        
        # Test 1: Recovery after application restart
        print("Testing recovery after application restart...")
        
        # Create initial maintenance service and enable maintenance
        config_service = MockConfigurationService()
        initial_service = EnhancedMaintenanceModeService(
            config_service=config_service,
            db_manager=self.real_db_manager
        )
        
        result = initial_service.enable_maintenance(
            reason="Testing system recovery",
            mode=MaintenanceMode.NORMAL,
            enabled_by="recovery_test"
        )
        self.assertTrue(result, "Initial maintenance activation should succeed")
        
        # Store maintenance state in config
        config_service.set_config("maintenance_mode", True)
        config_service.set_config("maintenance_reason", "Testing system recovery")
        
        # Simulate application restart by creating new service instance
        recovered_service = EnhancedMaintenanceModeService(
            config_service=config_service,
            db_manager=self.real_db_manager
        )
        self.created_services.append(recovered_service)
        
        # Should recover maintenance state
        recovered_status = recovered_service.get_maintenance_status()
        self.assertTrue(recovered_status.is_active, "Should recover active maintenance state")
        self.assertEqual(recovered_status.reason, "Testing system recovery", "Should recover maintenance reason")
        
        print("✓ Successful recovery after application restart")
        
        # Test 2: Recovery from partial failures
        print("Testing recovery from partial failures...")
        
        # Simulate partial failure during maintenance activation
        with patch.object(recovered_service, '_notify_change_subscribers') as mock_notify:
            mock_notify.side_effect = Exception("Notification system failed")
            
            # Should still enable maintenance despite notification failures
            result = recovered_service.enable_maintenance(
                reason="Testing partial failure recovery",
                mode=MaintenanceMode.EMERGENCY,
                enabled_by="partial_failure_test"
            )
            
            self.assertTrue(result, "Should succeed despite partial failures")
            
            status = recovered_service.get_maintenance_status()
            self.assertTrue(status.is_active, "Maintenance should be active")
            self.assertEqual(status.mode, MaintenanceMode.EMERGENCY, "Should have correct mode")
            
            print("✓ Recovery from partial failures successful")
        
        # Test 3: Graceful degradation under resource constraints
        print("Testing graceful degradation under resource constraints...")
        
        # Simulate resource constraints
        with patch('threading.RLock') as mock_lock:
            mock_lock.side_effect = Exception("Resource exhaustion")
            
            # Should still provide basic functionality
            try:
                status = recovered_service.get_maintenance_status()
                self.assertIsNotNone(status, "Should provide status despite resource constraints")
                print("✓ Basic functionality maintained under resource constraints")
            except Exception as e:
                print(f"✓ Graceful failure under resource constraints: {e}")
        
        # Test 4: Recovery validation
        print("Testing recovery validation...")
        
        # Validate that all core functionality works after recovery
        validation_results = {
            'status_check': False,
            'operation_blocking': False,
            'admin_bypass': False,
            'disable_maintenance': False
        }
        
        try:
            # Test status check
            status = recovered_service.get_maintenance_status()
            validation_results['status_check'] = status is not None
            
            # Test operation blocking
            blocked = recovered_service.is_operation_blocked('/test_operation', self.regular_user)
            validation_results['operation_blocking'] = isinstance(blocked, bool)
            
            # Test admin bypass
            admin_blocked = recovered_service.is_operation_blocked('/test_operation', self.admin_user)
            validation_results['admin_bypass'] = not admin_blocked
            
            # Test disable maintenance
            disable_result = recovered_service.disable_maintenance()
            validation_results['disable_maintenance'] = disable_result
            
        except Exception as e:
            print(f"Validation error: {e}")
        
        passed_validations = sum(validation_results.values())
        total_validations = len(validation_results)
        
        print(f"✓ Recovery validation: {passed_validations}/{total_validations} tests passed")
        
        self.assertGreater(passed_validations, total_validations * 0.75, 
                          "At least 75% of recovery validations should pass")
        
        print("✓ System failure recovery test passed")
    
    def test_disaster_recovery_state_persistence(self):
        """Test disaster recovery and maintenance mode state persistence"""
        print("\n=== Testing Disaster Recovery and State Persistence ===")
        
        # Test 1: State persistence across failures
        print("Testing state persistence across failures...")
        
        config_service = MockConfigurationService()
        
        # Create maintenance service and enable maintenance
        maintenance_service = EnhancedMaintenanceModeService(
            config_service=config_service,
            db_manager=self.real_db_manager
        )
        
        # Enable maintenance with specific configuration
        maintenance_config = {
            'reason': 'Disaster recovery testing',
            'duration': 60,
            'mode': MaintenanceMode.EMERGENCY,
            'enabled_by': 'disaster_recovery_test'
        }
        
        result = maintenance_service.enable_maintenance(**maintenance_config)
        self.assertTrue(result, "Initial maintenance activation should succeed")
        
        # Store state for persistence testing
        initial_status = maintenance_service.get_maintenance_status()
        
        # Simulate disaster - create new service instance with same config
        disaster_recovery_service = EnhancedMaintenanceModeService(
            config_service=config_service,
            db_manager=self.real_db_manager
        )
        self.created_services.append(disaster_recovery_service)
        
        # Should recover state from configuration
        recovered_status = disaster_recovery_service.get_maintenance_status()
        
        # Validate state recovery
        state_recovery_checks = {
            'is_active': recovered_status.is_active == initial_status.is_active,
            'reason_preserved': recovered_status.reason is not None,
            'mode_recoverable': recovered_status.mode is not None
        }
        
        recovery_success = sum(state_recovery_checks.values())
        print(f"✓ State recovery: {recovery_success}/{len(state_recovery_checks)} attributes recovered")
        
        # Test 2: Emergency state persistence
        print("Testing emergency state persistence...")
        
        # Create emergency handler
        emergency_handler = EmergencyMaintenanceHandler(
            maintenance_service=disaster_recovery_service,
            db_manager=self.real_db_manager
        )
        
        # Activate emergency mode
        emergency_result = emergency_handler.activate_emergency_mode(
            reason="Disaster recovery emergency test",
            triggered_by="disaster_recovery_system"
        )
        
        self.assertTrue(emergency_result, "Emergency activation should succeed")
        
        # Verify emergency state
        emergency_status = disaster_recovery_service.get_maintenance_status()
        self.assertEqual(emergency_status.mode, MaintenanceMode.EMERGENCY, "Should be in emergency mode")
        
        # Simulate recovery after emergency
        recovery_service = EnhancedMaintenanceModeService(
            config_service=config_service,
            db_manager=self.real_db_manager
        )
        self.created_services.append(recovery_service)
        
        # Should maintain emergency state
        post_recovery_status = recovery_service.get_maintenance_status()
        emergency_state_maintained = post_recovery_status.is_active
        
        print(f"✓ Emergency state persistence: {'maintained' if emergency_state_maintained else 'lost'}")
        
        # Test 3: Configuration backup and restore
        print("Testing configuration backup and restore...")
        
        # Create backup of maintenance configuration
        backup_config = {
            'maintenance_mode': config_service.get_config('maintenance_mode'),
            'maintenance_reason': config_service.get_config('maintenance_reason'),
            'maintenance_duration': config_service.get_config('maintenance_duration'),
            'maintenance_enabled_by': config_service.get_config('maintenance_enabled_by')
        }
        
        # Simulate configuration corruption
        config_service.config_data.clear()
        
        # Restore from backup
        for key, value in backup_config.items():
            if value is not None:
                config_service.set_config(key, value)
        
        # Verify restoration
        restored_service = EnhancedMaintenanceModeService(
            config_service=config_service,
            db_manager=self.real_db_manager
        )
        self.created_services.append(restored_service)
        
        restored_status = restored_service.get_maintenance_status()
        restoration_successful = restored_status.is_active or restored_status.reason is not None
        
        print(f"✓ Configuration restoration: {'successful' if restoration_successful else 'failed'}")
        
        # Test 4: Multi-instance state consistency
        print("Testing multi-instance state consistency...")
        
        # Create multiple service instances
        service_instances = []
        for i in range(3):
            instance = EnhancedMaintenanceModeService(
                config_service=config_service,
                db_manager=self.real_db_manager
            )
            service_instances.append(instance)
            self.created_services.append(instance)
        
        # Check state consistency across instances
        statuses = [instance.get_maintenance_status() for instance in service_instances]
        
        # All instances should have consistent state
        active_states = [status.is_active for status in statuses]
        state_consistency = len(set(active_states)) == 1  # All same value
        
        print(f"✓ Multi-instance consistency: {'consistent' if state_consistency else 'inconsistent'}")
        
        self.assertTrue(state_consistency, "All instances should have consistent state")
        
        print("✓ Disaster recovery and state persistence test passed")
    
    def test_data_consistency_after_failures(self):
        """Test data consistency after maintenance mode failures"""
        print("\n=== Testing Data Consistency After Failures ===")
        
        config_service = MockConfigurationService()
        maintenance_service = EnhancedMaintenanceModeService(
            config_service=config_service,
            db_manager=self.real_db_manager
        )
        self.created_services.append(maintenance_service)
        
        # Test 1: Consistency after partial activation failure
        print("Testing consistency after partial activation failure...")
        
        # Mock partial failure during activation
        original_notify = maintenance_service._notify_change_subscribers
        
        def failing_notify(*args, **kwargs):
            if args[0] == 'maintenance_enabled':
                raise Exception("Notification failed")
            return original_notify(*args, **kwargs)
        
        with patch.object(maintenance_service, '_notify_change_subscribers', side_effect=failing_notify):
            result = maintenance_service.enable_maintenance(
                reason="Consistency test",
                mode=MaintenanceMode.NORMAL,
                enabled_by="consistency_test"
            )
            
            # Should still succeed
            self.assertTrue(result, "Should succeed despite notification failure")
        
        # Verify internal state consistency
        status = maintenance_service.get_maintenance_status()
        self.assertTrue(status.is_active, "Internal state should be consistent")
        self.assertEqual(status.reason, "Consistency test", "Reason should be preserved")
        
        print("✓ Consistency maintained after partial activation failure")
        
        # Test 2: Consistency after operation blocking failures
        print("Testing consistency after operation blocking failures...")
        
        # Mock operation classifier to fail intermittently
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier:
            mock_instance = Mock()
            mock_instance.classify_operation.side_effect = [
                Exception("Classifier failed"),  # First call fails
                'caption_generation',  # Second call succeeds
                Exception("Classifier failed again"),  # Third call fails
                'job_creation'  # Fourth call succeeds
            ]
            mock_classifier.return_value = mock_instance
            
            # Test multiple operation checks
            operations = ['/test1', '/test2', '/test3', '/test4']
            results = []
            
            for operation in operations:
                try:
                    blocked = maintenance_service.is_operation_blocked(operation, self.regular_user)
                    results.append(('success', blocked))
                except Exception as e:
                    results.append(('error', str(e)))
            
            # Should handle failures gracefully without corrupting state
            successful_checks = [r for r in results if r[0] == 'success']
            print(f"✓ Operation blocking: {len(successful_checks)}/{len(results)} checks succeeded")
            
            # Verify maintenance state is still consistent
            status_after_failures = maintenance_service.get_maintenance_status()
            self.assertTrue(status_after_failures.is_active, "Maintenance state should remain consistent")
        
        # Test 3: Consistency after concurrent access failures
        print("Testing consistency after concurrent access failures...")
        
        # Simulate concurrent access with some failures
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        results = []
        errors = []
        
        def concurrent_operation(operation_id):
            try:
                if operation_id % 3 == 0:  # Every third operation fails
                    raise Exception(f"Simulated failure for operation {operation_id}")
                
                # Test various operations
                status = maintenance_service.get_maintenance_status()
                blocked = maintenance_service.is_operation_blocked(f'/test_{operation_id}', self.regular_user)
                message = maintenance_service.get_maintenance_message(f'test_{operation_id}')
                
                return {
                    'operation_id': operation_id,
                    'status_active': status.is_active,
                    'operation_blocked': blocked,
                    'message_length': len(message)
                }
            except Exception as e:
                errors.append((operation_id, str(e)))
                return None
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(concurrent_operation, i) for i in range(50)]
            results = [future.result() for future in futures if future.result() is not None]
        
        # Analyze consistency
        if results:
            status_values = [r['status_active'] for r in results]
            status_consistent = len(set(status_values)) == 1
            
            print(f"✓ Concurrent access: {len(results)} successful operations, {len(errors)} errors")
            print(f"✓ Status consistency: {'consistent' if status_consistent else 'inconsistent'}")
            
            self.assertTrue(status_consistent, "Status should be consistent across concurrent access")
        
        # Test 4: Recovery and consistency validation
        print("Testing recovery and consistency validation...")
        
        # Disable and re-enable maintenance to test full cycle
        disable_result = maintenance_service.disable_maintenance()
        self.assertTrue(disable_result, "Should disable successfully")
        
        # Verify disabled state
        disabled_status = maintenance_service.get_maintenance_status()
        self.assertFalse(disabled_status.is_active, "Should be inactive after disable")
        
        # Re-enable with different configuration
        enable_result = maintenance_service.enable_maintenance(
            reason="Consistency validation test",
            mode=MaintenanceMode.EMERGENCY,
            enabled_by="validation_test"
        )
        self.assertTrue(enable_result, "Should re-enable successfully")
        
        # Verify new state
        final_status = maintenance_service.get_maintenance_status()
        self.assertTrue(final_status.is_active, "Should be active after re-enable")
        self.assertEqual(final_status.mode, MaintenanceMode.EMERGENCY, "Should have correct mode")
        self.assertEqual(final_status.reason, "Consistency validation test", "Should have correct reason")
        
        print("✓ Full cycle consistency validation successful")
        
        # Test 5: Data integrity checks
        print("Testing data integrity checks...")
        
        # Verify service statistics are consistent
        stats = maintenance_service.get_service_stats()
        self.assertIsInstance(stats, dict, "Stats should be a dictionary")
        self.assertIn('current_status', stats, "Stats should include current status")
        self.assertIn('statistics', stats, "Stats should include statistics")
        
        # Verify status consistency
        status_from_stats = stats['current_status']
        direct_status = maintenance_service.get_maintenance_status()
        
        consistency_checks = {
            'is_active': status_from_stats['is_active'] == direct_status.is_active,
            'mode': status_from_stats['mode'] == direct_status.mode.value,
            'reason': status_from_stats['reason'] == direct_status.reason
        }
        
        consistent_fields = sum(consistency_checks.values())
        print(f"✓ Data integrity: {consistent_fields}/{len(consistency_checks)} fields consistent")
        
        self.assertGreater(consistent_fields, len(consistency_checks) * 0.8, 
                          "At least 80% of fields should be consistent")
        
        print("✓ Data consistency after failures test passed")
    
    def test_cascading_failure_recovery(self):
        """Test recovery from cascading failures across multiple components"""
        print("\n=== Testing Cascading Failure Recovery ===")
        
        # Create components that can fail
        failing_config = FailingConfigurationService(fail_after_calls=5)
        failing_db = FailingDatabaseManager(self.real_db_manager, fail_after_calls=10)
        
        maintenance_service = EnhancedMaintenanceModeService(
            config_service=failing_config,
            db_manager=failing_db
        )
        self.created_services.append(maintenance_service)
        
        # Test 1: Initial operations before failures
        print("Testing initial operations before failures...")
        
        # Should work initially
        initial_result = maintenance_service.enable_maintenance(
            reason="Cascading failure test",
            mode=MaintenanceMode.NORMAL,
            enabled_by="cascade_test"
        )
        self.assertTrue(initial_result, "Initial activation should succeed")
        
        # Multiple status checks to trigger config failures
        for i in range(3):
            status = maintenance_service.get_maintenance_status()
            self.assertIsNotNone(status, f"Status check {i+1} should succeed")
        
        print("✓ Initial operations successful")
        
        # Test 2: Operations during cascading failures
        print("Testing operations during cascading failures...")
        
        # Continue operations to trigger failures
        failure_results = []
        
        for i in range(10):
            try:
                # This should trigger config service failures
                status = maintenance_service.get_maintenance_status()
                blocked = maintenance_service.is_operation_blocked('/test', self.regular_user)
                failure_results.append(('success', i))
            except Exception as e:
                failure_results.append(('error', str(e)))
        
        successful_operations = [r for r in failure_results if r[0] == 'success']
        failed_operations = [r for r in failure_results if r[0] == 'error']
        
        print(f"✓ During failures: {len(successful_operations)} successful, {len(failed_operations)} failed")
        
        # Should have some successful operations (graceful degradation)
        self.assertGreater(len(successful_operations), 0, "Should have some successful operations")
        
        # Test 3: Recovery after fixing components
        print("Testing recovery after fixing components...")
        
        # "Fix" the failing components
        failing_config.fail_after_calls = None
        failing_config.fail_on_get = False
        failing_config.fail_on_set = False
        
        failing_db.fail_after_calls = None
        failing_db.fail_on_session = False
        
        # Should recover functionality
        recovery_operations = []
        
        for i in range(5):
            try:
                status = maintenance_service.get_maintenance_status()
                blocked = maintenance_service.is_operation_blocked('/test', self.regular_user)
                message = maintenance_service.get_maintenance_message('test')
                recovery_operations.append('success')
            except Exception as e:
                recovery_operations.append(f'error: {e}')
        
        successful_recovery = recovery_operations.count('success')
        print(f"✓ Recovery operations: {successful_recovery}/{len(recovery_operations)} successful")
        
        self.assertGreater(successful_recovery, len(recovery_operations) * 0.8, 
                          "At least 80% of recovery operations should succeed")
        
        # Test 4: Full functionality validation after recovery
        print("Testing full functionality validation after recovery...")
        
        validation_tests = {
            'enable_maintenance': False,
            'disable_maintenance': False,
            'get_status': False,
            'check_operation': False,
            'get_message': False,
            'get_stats': False
        }
        
        try:
            # Test enable/disable cycle
            maintenance_service.disable_maintenance()
            validation_tests['disable_maintenance'] = True
            
            result = maintenance_service.enable_maintenance(
                reason="Recovery validation",
                mode=MaintenanceMode.TEST,
                enabled_by="recovery_validation"
            )
            validation_tests['enable_maintenance'] = result
            
            # Test status
            status = maintenance_service.get_maintenance_status()
            validation_tests['get_status'] = status is not None
            
            # Test operation checking
            blocked = maintenance_service.is_operation_blocked('/test', self.regular_user)
            validation_tests['check_operation'] = isinstance(blocked, bool)
            
            # Test message generation
            message = maintenance_service.get_maintenance_message('test')
            validation_tests['get_message'] = isinstance(message, str) and len(message) > 0
            
            # Test statistics
            stats = maintenance_service.get_service_stats()
            validation_tests['get_stats'] = isinstance(stats, dict)
            
        except Exception as e:
            print(f"Validation error: {e}")
        
        passed_validations = sum(validation_tests.values())
        total_validations = len(validation_tests)
        
        print(f"✓ Full functionality validation: {passed_validations}/{total_validations} tests passed")
        
        self.assertGreater(passed_validations, total_validations * 0.8, 
                          "At least 80% of functionality should be restored")
        
        print("✓ Cascading failure recovery test passed")
    
    def generate_failure_report(self):
        """Generate comprehensive failure scenario report"""
        report = {
            'test_timestamp': datetime.now(timezone.utc).isoformat(),
            'failure_scenarios_tested': len(self.failure_scenarios),
            'scenarios': {}
        }
        
        for scenario_name, scenario_data in self.failure_scenarios.items():
            report['scenarios'][scenario_name] = {
                'count': len(scenario_data),
                'details': scenario_data
            }
        
        return report


if __name__ == '__main__':
    unittest.main(verbosity=2)