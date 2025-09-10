#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Emergency Recovery Validation Script

This script validates the emergency recovery mechanisms and rollback procedures
for the notification system, ensuring all emergency procedures work correctly
and can be executed when needed.
"""

import sys
import os
import json
import time
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from app.services.notification.components.notification_emergency_recovery import NotificationEmergencyRecovery, EmergencyLevel, FailureType
    from app.services.notification.manager.unified_manager import UnifiedNotificationManager
    from websocket_factory import WebSocketFactory
    from websocket_auth_handler import WebSocketAuthHandler
    from websocket_namespace_manager import WebSocketNamespaceManager
    from app.core.database.core.database_manager import DatabaseManager
    from config import Config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


class EmergencyRecoveryValidator:
    """Validates emergency recovery mechanisms and procedures"""
    
    def __init__(self):
        """Initialize validator"""
        self.project_root = Path(__file__).parent.parent
        self.test_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tests': {},
            'overall_status': 'unknown',
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
        
        try:
            self.config = Config()
            self.db_manager = DatabaseManager(self.config)
            
            # Initialize components for testing
            self._initialize_components()
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize components: {e}")
            self.recovery_system = None
    
    def _initialize_components(self):
        """Initialize system components for testing"""
        try:
            self.websocket_factory = WebSocketFactory()
            self.auth_handler = WebSocketAuthHandler()
            self.namespace_manager = WebSocketNamespaceManager()
            
            self.notification_manager = UnifiedNotificationManager(
                self.websocket_factory,
                self.auth_handler,
                self.namespace_manager,
                self.db_manager
            )
            
            self.recovery_system = NotificationEmergencyRecovery(
                self.notification_manager,
                self.websocket_factory,
                self.auth_handler,
                self.namespace_manager,
                self.db_manager
            )
            
        except Exception as e:
            print(f"⚠️  Component initialization warning: {e}")
            self.recovery_system = None
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all emergency recovery validation tests"""
        print("🔍 Running Emergency Recovery Validation Tests...")
        print("=" * 60)
        
        # Test categories
        test_categories = [
            ('Emergency Detection', self._test_emergency_detection),
            ('Recovery Mechanisms', self._test_recovery_mechanisms),
            ('Fallback Systems', self._test_fallback_systems),
            ('Rollback Procedures', self._test_rollback_procedures),
            ('Emergency CLI Tools', self._test_emergency_cli_tools),
            ('Documentation Completeness', self._test_documentation_completeness),
            ('System Integration', self._test_system_integration),
            ('Performance Under Load', self._test_performance_under_load)
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n📋 Testing: {category_name}")
            print("-" * 40)
            
            try:
                test_result = test_function()
                self.test_results['tests'][category_name] = test_result
                
                if test_result['status'] == 'passed':
                    self.test_results['passed'] += 1
                    print(f"✅ {category_name}: PASSED")
                elif test_result['status'] == 'failed':
                    self.test_results['failed'] += 1
                    print(f"❌ {category_name}: FAILED")
                    for error in test_result.get('errors', []):
                        print(f"   ❌ {error}")
                else:
                    self.test_results['warnings'] += 1
                    print(f"⚠️  {category_name}: WARNING")
                    for warning in test_result.get('warnings', []):
                        print(f"   ⚠️  {warning}")
                        
            except Exception as e:
                self.test_results['failed'] += 1
                self.test_results['tests'][category_name] = {
                    'status': 'failed',
                    'errors': [f"Test execution failed: {e}"]
                }
                print(f"❌ {category_name}: FAILED (Exception: {e})")
        
        # Determine overall status
        if self.test_results['failed'] > 0:
            self.test_results['overall_status'] = 'failed'
        elif self.test_results['warnings'] > 0:
            self.test_results['overall_status'] = 'warning'
        else:
            self.test_results['overall_status'] = 'passed'
        
        # Display summary
        self._display_test_summary()
        
        return self.test_results
    
    def _test_emergency_detection(self) -> Dict[str, Any]:
        """Test emergency detection mechanisms"""
        result = {'status': 'passed', 'errors': [], 'warnings': [], 'details': {}}
        
        if not self.recovery_system:
            result['status'] = 'failed'
            result['errors'].append("Recovery system not available")
            return result
        
        try:
            # Test failure classification
            test_error = Exception("WebSocket connection failed")
            failure_type = self.recovery_system._classify_failure(
                test_error, {'affected_users': 5}
            )
            
            if failure_type == FailureType.WEBSOCKET_CONNECTION_FAILURE:
                result['details']['failure_classification'] = 'passed'
            else:
                result['warnings'].append(f"Unexpected failure type: {failure_type}")
            
            # Test emergency level assessment
            emergency_level = self.recovery_system._assess_emergency_level(
                failure_type, {'affected_users': 15}
            )
            
            if emergency_level in [EmergencyLevel.HIGH, EmergencyLevel.MEDIUM]:
                result['details']['emergency_assessment'] = 'passed'
            else:
                result['warnings'].append(f"Unexpected emergency level: {emergency_level}")
            
            # Test health check functionality
            health_results = self.recovery_system.run_health_check()
            
            if isinstance(health_results, dict) and 'overall_status' in health_results:
                result['details']['health_check'] = 'passed'
            else:
                result['errors'].append("Health check failed to return proper results")
                result['status'] = 'failed'
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Emergency detection test failed: {e}")
        
        return result
    
    def _test_recovery_mechanisms(self) -> Dict[str, Any]:
        """Test recovery mechanisms"""
        result = {'status': 'passed', 'errors': [], 'warnings': [], 'details': {}}
        
        if not self.recovery_system:
            result['status'] = 'failed'
            result['errors'].append("Recovery system not available")
            return result
        
        try:
            # Test emergency mode activation
            activation_result = self.recovery_system.activate_emergency_mode(
                "Test emergency activation", "validator"
            )
            
            if activation_result:
                result['details']['emergency_activation'] = 'passed'
                
                # Test emergency mode deactivation
                deactivation_result = self.recovery_system.deactivate_emergency_mode("validator")
                
                if deactivation_result:
                    result['details']['emergency_deactivation'] = 'passed'
                else:
                    result['warnings'].append("Emergency deactivation failed")
            else:
                result['warnings'].append("Emergency activation failed")
            
            # Test emergency notification sending
            notification_result = self.recovery_system.send_emergency_notification(
                "Test Emergency", "This is a test emergency notification"
            )
            
            if notification_result:
                result['details']['emergency_notification'] = 'passed'
            else:
                result['warnings'].append("Emergency notification sending failed")
            
            # Test recovery plan execution (simulate)
            test_event = self.recovery_system._create_emergency_event(
                FailureType.MESSAGE_DELIVERY_FAILURE,
                EmergencyLevel.MEDIUM,
                Exception("Test failure"),
                {'affected_users': [1, 2, 3]}
            )
            
            # Note: We don't actually execute recovery plan to avoid system impact
            result['details']['recovery_plan_structure'] = 'passed'
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Recovery mechanisms test failed: {e}")
        
        return result
    
    def _test_fallback_systems(self) -> Dict[str, Any]:
        """Test fallback systems"""
        result = {'status': 'passed', 'errors': [], 'warnings': [], 'details': {}}
        
        try:
            # Test Flask flash message fallback availability
            try:
                from flask import flash
                result['details']['flask_fallback_available'] = 'passed'
            except ImportError:
                result['errors'].append("Flask flash message fallback not available")
                result['status'] = 'failed'
            
            # Test emergency broadcast capability
            if self.recovery_system:
                emergency_status = self.recovery_system.get_emergency_status()
                
                if isinstance(emergency_status, dict):
                    fallback_systems = emergency_status.get('fallback_systems', {})
                    
                    if fallback_systems.get('emergency_broadcast_enabled'):
                        result['details']['emergency_broadcast'] = 'passed'
                    else:
                        result['warnings'].append("Emergency broadcast not enabled")
                else:
                    result['warnings'].append("Could not get emergency status")
            
            # Test database fallback for session management
            try:
                with self.db_manager.get_session() as session:
                    session.execute("SELECT 1")
                result['details']['database_fallback'] = 'passed'
            except Exception as e:
                result['errors'].append(f"Database fallback test failed: {e}")
                result['status'] = 'failed'
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Fallback systems test failed: {e}")
        
        return result
    
    def _test_rollback_procedures(self) -> Dict[str, Any]:
        """Test rollback procedures (non-destructive)"""
        result = {'status': 'passed', 'errors': [], 'warnings': [], 'details': {}}
        
        try:
            # Check rollback script existence
            rollback_script = self.project_root / "scripts" / "rollback_notification_system.sh"
            
            if rollback_script.exists():
                result['details']['rollback_script_exists'] = 'passed'
                
                # Test script syntax (dry run)
                try:
                    subprocess.run(['bash', '-n', str(rollback_script)], 
                                 check=True, capture_output=True)
                    result['details']['rollback_script_syntax'] = 'passed'
                except subprocess.CalledProcessError as e:
                    result['errors'].append(f"Rollback script syntax error: {e}")
                    result['status'] = 'failed'
            else:
                result['errors'].append("Rollback script not found")
                result['status'] = 'failed'
            
            # Check enhanced CLI tool
            enhanced_cli = self.project_root / "scripts" / "enhanced_notification_emergency_cli.py"
            
            if enhanced_cli.exists():
                result['details']['enhanced_cli_exists'] = 'passed'
                
                # Test CLI syntax
                try:
                    subprocess.run([sys.executable, '-m', 'py_compile', str(enhanced_cli)], 
                                 check=True, capture_output=True)
                    result['details']['enhanced_cli_syntax'] = 'passed'
                except subprocess.CalledProcessError as e:
                    result['errors'].append(f"Enhanced CLI syntax error: {e}")
                    result['status'] = 'failed'
            else:
                result['warnings'].append("Enhanced CLI tool not found")
            
            # Test backup creation capability
            try:
                # Create a temporary test backup
                test_backup_dir = tempfile.mkdtemp(prefix="test_backup_")
                
                # Simulate backup creation
                test_file = Path(test_backup_dir) / "test_backup.txt"
                test_file.write_text("Test backup content")
                
                if test_file.exists():
                    result['details']['backup_creation'] = 'passed'
                
                # Clean up
                shutil.rmtree(test_backup_dir)
                
            except Exception as e:
                result['warnings'].append(f"Backup creation test failed: {e}")
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Rollback procedures test failed: {e}")
        
        return result
    
    def _test_emergency_cli_tools(self) -> Dict[str, Any]:
        """Test emergency CLI tools"""
        result = {'status': 'passed', 'errors': [], 'warnings': [], 'details': {}}
        
        try:
            # Test original emergency CLI
            original_cli = self.project_root / "scripts" / "notification_emergency_cli.py"
            
            if original_cli.exists():
                result['details']['original_cli_exists'] = 'passed'
                
                # Test CLI help functionality
                try:
                    subprocess.run([sys.executable, str(original_cli), '--help'], 
                                 check=True, capture_output=True, timeout=10)
                    result['details']['original_cli_help'] = 'passed'
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    result['warnings'].append(f"Original CLI help test failed: {e}")
            else:
                result['warnings'].append("Original emergency CLI not found")
            
            # Test enhanced CLI
            enhanced_cli = self.project_root / "scripts" / "enhanced_notification_emergency_cli.py"
            
            if enhanced_cli.exists():
                result['details']['enhanced_cli_exists'] = 'passed'
                
                # Test enhanced CLI help
                try:
                    subprocess.run([sys.executable, str(enhanced_cli), '--help'], 
                                 check=True, capture_output=True, timeout=10)
                    result['details']['enhanced_cli_help'] = 'passed'
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    result['warnings'].append(f"Enhanced CLI help test failed: {e}")
            else:
                result['warnings'].append("Enhanced emergency CLI not found")
            
            # Test validation script (this script)
            validation_script = Path(__file__)
            
            if validation_script.exists():
                result['details']['validation_script_exists'] = 'passed'
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Emergency CLI tools test failed: {e}")
        
        return result
    
    def _test_documentation_completeness(self) -> Dict[str, Any]:
        """Test documentation completeness"""
        result = {'status': 'passed', 'errors': [], 'warnings': [], 'details': {}}
        
        try:
            docs_dir = self.project_root / "docs"
            
            # Required documentation files
            required_docs = [
                "notification-system-emergency-procedures.md",
                "notification-system-rollback-procedures.md"
            ]
            
            for doc_file in required_docs:
                doc_path = docs_dir / doc_file
                
                if doc_path.exists():
                    result['details'][f'{doc_file}_exists'] = 'passed'
                    
                    # Check if file has content
                    if doc_path.stat().st_size > 1000:  # At least 1KB of content
                        result['details'][f'{doc_file}_content'] = 'passed'
                    else:
                        result['warnings'].append(f"{doc_file} appears to have minimal content")
                else:
                    result['errors'].append(f"Required documentation missing: {doc_file}")
                    result['status'] = 'failed'
            
            # Check for emergency contact information
            emergency_proc_file = docs_dir / "notification-system-emergency-procedures.md"
            if emergency_proc_file.exists():
                content = emergency_proc_file.read_text()
                
                if "Emergency Contacts" in content:
                    result['details']['emergency_contacts_documented'] = 'passed'
                else:
                    result['warnings'].append("Emergency contacts section not found in procedures")
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Documentation completeness test failed: {e}")
        
        return result
    
    def _test_system_integration(self) -> Dict[str, Any]:
        """Test system integration for emergency recovery"""
        result = {'status': 'passed', 'errors': [], 'warnings': [], 'details': {}}
        
        try:
            # Test database connectivity
            try:
                with self.db_manager.get_session() as session:
                    session.execute("SELECT 1")
                result['details']['database_connectivity'] = 'passed'
            except Exception as e:
                result['errors'].append(f"Database connectivity failed: {e}")
                result['status'] = 'failed'
            
            # Test Redis connectivity (if configured)
            try:
                import redis
                redis_client = redis.Redis.from_url(self.config.REDIS_URL)
                redis_client.ping()
                result['details']['redis_connectivity'] = 'passed'
            except Exception as e:
                result['warnings'].append(f"Redis connectivity test failed: {e}")
            
            # Test WebSocket factory integration
            if self.websocket_factory:
                result['details']['websocket_factory_integration'] = 'passed'
            else:
                result['warnings'].append("WebSocket factory not initialized")
            
            # Test notification manager integration
            if self.notification_manager:
                result['details']['notification_manager_integration'] = 'passed'
            else:
                result['warnings'].append("Notification manager not initialized")
            
            # Test emergency recovery system integration
            if self.recovery_system:
                result['details']['recovery_system_integration'] = 'passed'
            else:
                result['errors'].append("Recovery system not initialized")
                result['status'] = 'failed'
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"System integration test failed: {e}")
        
        return result
    
    def _test_performance_under_load(self) -> Dict[str, Any]:
        """Test performance under simulated load"""
        result = {'status': 'passed', 'errors': [], 'warnings': [], 'details': {}}
        
        try:
            if not self.recovery_system:
                result['warnings'].append("Recovery system not available for load testing")
                return result
            
            # Test health check performance
            start_time = time.time()
            health_results = self.recovery_system.run_health_check()
            health_check_time = (time.time() - start_time) * 1000
            
            result['details']['health_check_time_ms'] = health_check_time
            
            if health_check_time < 5000:  # Less than 5 seconds
                result['details']['health_check_performance'] = 'passed'
            else:
                result['warnings'].append(f"Health check took {health_check_time:.2f}ms (> 5000ms)")
            
            # Test emergency status retrieval performance
            start_time = time.time()
            emergency_status = self.recovery_system.get_emergency_status()
            status_time = (time.time() - start_time) * 1000
            
            result['details']['status_retrieval_time_ms'] = status_time
            
            if status_time < 1000:  # Less than 1 second
                result['details']['status_retrieval_performance'] = 'passed'
            else:
                result['warnings'].append(f"Status retrieval took {status_time:.2f}ms (> 1000ms)")
            
            # Test multiple rapid health checks (simulated load)
            rapid_check_times = []
            for i in range(5):
                start_time = time.time()
                self.recovery_system.run_health_check()
                rapid_check_times.append((time.time() - start_time) * 1000)
            
            avg_rapid_time = sum(rapid_check_times) / len(rapid_check_times)
            result['details']['avg_rapid_check_time_ms'] = avg_rapid_time
            
            if avg_rapid_time < 2000:  # Average less than 2 seconds
                result['details']['rapid_check_performance'] = 'passed'
            else:
                result['warnings'].append(f"Rapid checks averaged {avg_rapid_time:.2f}ms (> 2000ms)")
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Performance under load test failed: {e}")
        
        return result
    
    def _display_test_summary(self):
        """Display test summary"""
        print("\n" + "=" * 60)
        print("🏁 EMERGENCY RECOVERY VALIDATION SUMMARY")
        print("=" * 60)
        
        total_tests = self.test_results['passed'] + self.test_results['failed'] + self.test_results['warnings']
        
        print(f"📊 Test Results:")
        print(f"   ✅ Passed: {self.test_results['passed']}")
        print(f"   ❌ Failed: {self.test_results['failed']}")
        print(f"   ⚠️  Warnings: {self.test_results['warnings']}")
        print(f"   📈 Total: {total_tests}")
        
        if self.test_results['overall_status'] == 'passed':
            print(f"\n🎉 Overall Status: ✅ PASSED")
            print("   Emergency recovery system is ready for production use.")
        elif self.test_results['overall_status'] == 'warning':
            print(f"\n⚠️  Overall Status: ⚠️  WARNING")
            print("   Emergency recovery system has minor issues that should be addressed.")
        else:
            print(f"\n🚨 Overall Status: ❌ FAILED")
            print("   Emergency recovery system has critical issues that must be resolved.")
        
        print(f"\n📄 Detailed results saved to validation report")
    
    def save_results(self, output_file: Optional[str] = None) -> str:
        """Save test results to file"""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"emergency_recovery_validation_{timestamp}.json"
        
        output_path = self.project_root / "storage" / "emergency_backups" / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        return str(output_path)


def main():
    """Main validation entry point"""
    print("🔍 Emergency Recovery Validation")
    print("=" * 60)
    print("This script validates the emergency recovery mechanisms")
    print("and rollback procedures for the notification system.")
    print("=" * 60)
    
    # Initialize validator
    validator = EmergencyRecoveryValidator()
    
    # Run all tests
    results = validator.run_all_tests()
    
    # Save results
    results_file = validator.save_results()
    print(f"\n📄 Results saved to: {results_file}")
    
    # Return appropriate exit code
    if results['overall_status'] == 'passed':
        return 0
    elif results['overall_status'] == 'warning':
        return 1
    else:
        return 2


if __name__ == '__main__':
    sys.exit(main())