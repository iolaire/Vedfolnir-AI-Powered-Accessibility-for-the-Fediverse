#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Mode Test Validation

Quick validation script to check if all maintenance mode tests can be imported
and basic functionality is working.
"""

import sys
import os
import unittest
from io import StringIO

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def validate_test_imports():
    """Validate that all test modules can be imported"""
    print("🔍 Validating test imports...")
    
    test_modules = [
        'tests.integration.test_maintenance_mode_end_to_end',
        'tests.performance.test_maintenance_mode_load',
        'tests.integration.test_maintenance_mode_failure_scenarios'
    ]
    
    import_results = {}
    
    for module_name in test_modules:
        try:
            __import__(module_name)
            import_results[module_name] = 'SUCCESS'
            print(f"  ✓ {module_name}")
        except ImportError as e:
            import_results[module_name] = f'IMPORT_ERROR: {e}'
            print(f"  ❌ {module_name}: {e}")
        except Exception as e:
            import_results[module_name] = f'ERROR: {e}'
            print(f"  ⚠️  {module_name}: {e}")
    
    successful_imports = sum(1 for result in import_results.values() if result == 'SUCCESS')
    total_imports = len(import_results)
    
    print(f"\nImport Results: {successful_imports}/{total_imports} successful")
    
    return successful_imports == total_imports, import_results


def validate_test_discovery():
    """Validate that tests can be discovered"""
    print("\n🔍 Validating test discovery...")
    
    test_directories = [
        'tests/integration',
        'tests/performance'
    ]
    
    discovery_results = {}
    
    for test_dir in test_directories:
        try:
            if os.path.exists(test_dir):
                loader = unittest.TestLoader()
                suite = loader.discover(test_dir, pattern='test_maintenance_mode_*.py')
                test_count = suite.countTestCases()
                discovery_results[test_dir] = f'SUCCESS: {test_count} tests'
                print(f"  ✓ {test_dir}: {test_count} tests discovered")
            else:
                discovery_results[test_dir] = 'DIRECTORY_NOT_FOUND'
                print(f"  ❌ {test_dir}: Directory not found")
        except Exception as e:
            discovery_results[test_dir] = f'ERROR: {e}'
            print(f"  ⚠️  {test_dir}: {e}")
    
    successful_discoveries = sum(1 for result in discovery_results.values() if result.startswith('SUCCESS'))
    total_discoveries = len(discovery_results)
    
    print(f"\nDiscovery Results: {successful_discoveries}/{total_discoveries} successful")
    
    return successful_discoveries == total_discoveries, discovery_results


def validate_basic_functionality():
    """Validate basic maintenance mode functionality"""
    print("\n🔍 Validating basic functionality...")
    
    try:
        # Test basic imports
        from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode
        from tests.test_helpers.mock_configurations import MockConfigurationService
        
        # Create basic service
        config_service = MockConfigurationService()
        maintenance_service = EnhancedMaintenanceModeService(config_service=config_service)
        
        # Test basic operations
        tests = {
            'get_status': False,
            'enable_maintenance': False,
            'disable_maintenance': False,
            'check_operation': False
        }
        
        # Test get status
        status = maintenance_service.get_maintenance_status()
        tests['get_status'] = status is not None
        
        # Test enable maintenance
        result = maintenance_service.enable_maintenance(
            reason="Validation test",
            mode=MaintenanceMode.TEST,
            enabled_by="validation"
        )
        tests['enable_maintenance'] = result
        
        # Test operation checking
        blocked = maintenance_service.is_operation_blocked('/test', None)
        tests['check_operation'] = isinstance(blocked, bool)
        
        # Test disable maintenance
        result = maintenance_service.disable_maintenance()
        tests['disable_maintenance'] = result
        
        successful_tests = sum(tests.values())
        total_tests = len(tests)
        
        print(f"  Basic functionality: {successful_tests}/{total_tests} tests passed")
        
        for test_name, passed in tests.items():
            status = "✓" if passed else "❌"
            print(f"    {status} {test_name}")
        
        return successful_tests == total_tests, tests
        
    except Exception as e:
        print(f"  ❌ Basic functionality test failed: {e}")
        return False, {'error': str(e)}


def validate_test_runner():
    """Validate that the test runner script works"""
    print("\n🔍 Validating test runner...")
    
    try:
        from tests.scripts.run_maintenance_mode_comprehensive_tests import MaintenanceModeTestRunner
        
        runner = MaintenanceModeTestRunner()
        
        # Check that test suites are defined
        suite_count = len(runner.test_suites)
        print(f"  ✓ Test runner loaded with {suite_count} test suites")
        
        # Check suite definitions
        for suite_name, suite_info in runner.test_suites.items():
            class_count = len(suite_info['test_classes'])
            print(f"    - {suite_name}: {class_count} test classes")
        
        return True, {'suites': suite_count}
        
    except Exception as e:
        print(f"  ❌ Test runner validation failed: {e}")
        return False, {'error': str(e)}


def main():
    """Main validation function"""
    print("🧪 Maintenance Mode Test Validation")
    print("=" * 50)
    
    validation_results = {}
    overall_success = True
    
    # Run validations
    validations = [
        ('imports', validate_test_imports),
        ('discovery', validate_test_discovery),
        ('functionality', validate_basic_functionality),
        ('test_runner', validate_test_runner)
    ]
    
    for validation_name, validation_func in validations:
        success, details = validation_func()
        validation_results[validation_name] = {'success': success, 'details': details}
        if not success:
            overall_success = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    for validation_name, result in validation_results.items():
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{validation_name.upper()}: {status}")
    
    if overall_success:
        print(f"\n🎉 All validations passed! Maintenance mode tests are ready to run.")
        print(f"\nTo run the comprehensive test suite:")
        print(f"  python tests/scripts/run_maintenance_mode_comprehensive_tests.py")
        print(f"\nTo run quick validation:")
        print(f"  python tests/scripts/run_maintenance_mode_comprehensive_tests.py --quick")
    else:
        print(f"\n⚠️  Some validations failed. Check the issues above before running tests.")
    
    return 0 if overall_success else 1


if __name__ == '__main__':
    sys.exit(main())