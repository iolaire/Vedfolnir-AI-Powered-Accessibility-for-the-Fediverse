#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demonstration script for StorageConfigurationService.

This script shows how to use the StorageConfigurationService both standalone
and integrated with the main configuration system.
"""

import os
import sys
import json

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage_configuration_service import StorageConfigurationService
from config import Config


def demo_standalone_service():
    """Demonstrate standalone StorageConfigurationService usage"""
    print("=" * 60)
    print("STANDALONE STORAGE CONFIGURATION SERVICE DEMO")
    print("=" * 60)
    
    # Create standalone service
    print("Creating standalone StorageConfigurationService...")
    service = StorageConfigurationService()
    
    # Show current configuration
    print("\nCurrent Configuration:")
    print(f"  Max Storage: {service.get_max_storage_gb():.1f} GB")
    print(f"  Warning Threshold: {service.get_warning_threshold_gb():.1f} GB")
    print(f"  Monitoring Enabled: {service.is_storage_monitoring_enabled()}")
    print(f"  Configuration Valid: {service.validate_storage_config()}")
    
    # Show configuration summary
    print("\nConfiguration Summary:")
    summary = service.get_configuration_summary()
    print(json.dumps(summary, indent=2))
    
    return service


def demo_integrated_service():
    """Demonstrate integrated StorageConfigurationService usage through Config"""
    print("\n" + "=" * 60)
    print("INTEGRATED STORAGE CONFIGURATION SERVICE DEMO")
    print("=" * 60)
    
    # Create main config
    print("Creating main Config with integrated storage configuration...")
    config = Config()
    
    # Access storage limit service through config
    if config.storage.limit_service is not None:
        service = config.storage.limit_service
        
        print("\nAccessing storage configuration through main Config:")
        print(f"  Max Storage: {service.get_max_storage_gb():.1f} GB")
        print(f"  Warning Threshold: {service.get_warning_threshold_gb():.1f} GB")
        print(f"  Monitoring Enabled: {service.is_storage_monitoring_enabled()}")
        
        # Show that we can access other storage config too
        print(f"\nOther storage configuration:")
        print(f"  Base Directory: {config.storage.base_dir}")
        print(f"  Images Directory: {config.storage.images_dir}")
        print(f"  Logs Directory: {config.storage.logs_dir}")
        
        return service
    else:
        print("❌ Storage limit service not available in integrated config")
        return None


def demo_environment_variables():
    """Demonstrate how environment variables affect the service"""
    print("\n" + "=" * 60)
    print("ENVIRONMENT VARIABLES DEMO")
    print("=" * 60)
    
    # Show current environment variables
    print("Current environment variables:")
    env_vars = ['CAPTION_MAX_STORAGE_GB', 'STORAGE_WARNING_THRESHOLD', 'STORAGE_MONITORING_ENABLED']
    for var in env_vars:
        value = os.environ.get(var, "Not set")
        print(f"  {var}: {value}")
    
    # Set some test environment variables
    print("\nSetting test environment variables...")
    os.environ['CAPTION_MAX_STORAGE_GB'] = '50.0'
    os.environ['STORAGE_WARNING_THRESHOLD'] = '90.0'
    os.environ['STORAGE_MONITORING_ENABLED'] = 'true'
    
    # Create service with new environment
    print("Creating service with new environment variables...")
    service = StorageConfigurationService()
    
    print(f"\nNew configuration:")
    print(f"  Max Storage: {service.get_max_storage_gb():.1f} GB")
    print(f"  Warning Threshold: {service.get_warning_threshold_gb():.1f} GB")
    print(f"  Monitoring Enabled: {service.is_storage_monitoring_enabled()}")
    
    # Test reload functionality
    print("\nChanging environment and reloading...")
    os.environ['CAPTION_MAX_STORAGE_GB'] = '75.0'
    service.reload_configuration()
    
    print(f"After reload:")
    print(f"  Max Storage: {service.get_max_storage_gb():.1f} GB")
    print(f"  Warning Threshold: {service.get_warning_threshold_gb():.1f} GB")
    
    # Clean up environment variables
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]
    
    return service


def demo_validation_and_error_handling():
    """Demonstrate validation and error handling"""
    print("\n" + "=" * 60)
    print("VALIDATION AND ERROR HANDLING DEMO")
    print("=" * 60)
    
    # Test with invalid values
    test_cases = [
        ("Valid configuration", "20.0", "80.0", "true"),
        ("Negative storage", "-5.0", "80.0", "true"),
        ("Zero storage", "0", "80.0", "true"),
        ("Invalid storage format", "not_a_number", "80.0", "true"),
        ("Invalid threshold too high", "20.0", "150.0", "true"),
        ("Invalid threshold zero", "20.0", "0", "true"),
        ("Invalid threshold format", "20.0", "invalid", "true"),
        ("Monitoring disabled", "20.0", "80.0", "false"),
    ]
    
    for description, max_storage, threshold, monitoring in test_cases:
        print(f"\nTesting: {description}")
        
        # Clear environment
        env_vars = ['CAPTION_MAX_STORAGE_GB', 'STORAGE_WARNING_THRESHOLD', 'STORAGE_MONITORING_ENABLED']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
        
        # Set test values
        os.environ['CAPTION_MAX_STORAGE_GB'] = max_storage
        os.environ['STORAGE_WARNING_THRESHOLD'] = threshold
        os.environ['STORAGE_MONITORING_ENABLED'] = monitoring
        
        # Create service and test
        service = StorageConfigurationService()
        is_valid = service.validate_storage_config()
        
        print(f"  Max Storage: {service.get_max_storage_gb():.1f} GB")
        print(f"  Warning Threshold: {service.get_warning_threshold_gb():.1f} GB")
        print(f"  Monitoring: {service.is_storage_monitoring_enabled()}")
        print(f"  Valid: {is_valid}")
    
    # Clean up
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]


def main():
    """Main demonstration function"""
    print("StorageConfigurationService Demonstration")
    print("This script demonstrates the storage configuration service functionality.")
    
    try:
        # Run demonstrations
        demo_standalone_service()
        demo_integrated_service()
        demo_environment_variables()
        demo_validation_and_error_handling()
        
        print("\n" + "=" * 60)
        print("DEMONSTRATION COMPLETE")
        print("=" * 60)
        print("✅ All demonstrations completed successfully!")
        print("\nKey features demonstrated:")
        print("  • Standalone service usage")
        print("  • Integration with main Config class")
        print("  • Environment variable handling")
        print("  • Configuration validation")
        print("  • Error handling and defaults")
        print("  • Configuration reloading")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())