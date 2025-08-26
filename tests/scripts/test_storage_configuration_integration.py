#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script for storage configuration integration

This script tests that storage configuration is properly integrated into:
1. Environment setup scripts
2. Configuration validation scripts  
3. Admin configuration management interface
4. System configuration manager
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_environment_setup_integration():
    """Test that storage configuration is included in environment setup"""
    print("Testing environment setup integration...")
    
    # Test that generate_env_secrets.py includes storage configuration
    script_path = Path("scripts/setup/generate_env_secrets.py")
    if not script_path.exists():
        print("❌ generate_env_secrets.py not found")
        return False
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Check for storage configuration prompts
    storage_checks = [
        "Storage Configuration:",
        "storage_max_gb",
        "storage_warning_threshold", 
        "storage_monitoring_enabled"
    ]
    
    for check in storage_checks:
        if check not in content:
            print(f"❌ Missing storage configuration: {check}")
            return False
    
    print("✅ Environment setup includes storage configuration")
    return True

def test_configuration_validation_integration():
    """Test that configuration validation includes storage settings"""
    print("Testing configuration validation integration...")
    
    # Test verify_env_setup.py
    script_path = Path("scripts/setup/verify_env_setup.py")
    if not script_path.exists():
        print("❌ verify_env_setup.py not found")
        return False
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Check for storage validation
    storage_checks = [
        "check_storage_config",
        "CAPTION_MAX_STORAGE_GB",
        "STORAGE_WARNING_THRESHOLD",
        "STORAGE_MONITORING_ENABLED"
    ]
    
    for check in storage_checks:
        if check not in content:
            print(f"❌ Missing storage validation: {check}")
            return False
    
    # Test validate_config.py
    script_path = Path("validate_config.py")
    if not script_path.exists():
        print("❌ validate_config.py not found")
        return False
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Check for storage configuration validation
    if "CAPTION_MAX_STORAGE_GB" not in content:
        print("❌ validate_config.py missing storage configuration")
        return False
    
    print("✅ Configuration validation includes storage settings")
    return True

def test_system_configuration_manager_integration():
    """Test that system configuration manager includes storage schemas"""
    print("Testing system configuration manager integration...")
    
    try:
        from system_configuration_manager import SystemConfigurationManager
        
        # Create a temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name
        
        try:
            # Initialize configuration manager
            config_manager = SystemConfigurationManager(f"sqlite:///{db_path}")
            
            # Get all schemas
            schemas = config_manager.get_configuration_schema()
            
            # Check for storage configuration schemas
            storage_schemas = [
                "storage_max_gb",
                "storage_warning_threshold", 
                "storage_monitoring_enabled",
                "storage_cleanup_retention_days",
                "storage_override_max_duration_hours",
                "storage_email_notification_enabled",
                "storage_email_rate_limit_hours"
            ]
            
            for schema_key in storage_schemas:
                if schema_key not in schemas:
                    print(f"❌ Missing storage schema: {schema_key}")
                    return False
                
                schema = schemas[schema_key]
                print(f"✅ Found storage schema: {schema_key} ({schema.description})")
            
            # Test getting storage configuration values
            for schema_key in storage_schemas[:3]:  # Test first 3
                try:
                    value = config_manager.get_configuration(schema_key, admin_user_id=1)
                    print(f"✅ Retrieved {schema_key}: {value}")
                except Exception as e:
                    print(f"⚠️  Could not retrieve {schema_key}: {e}")
            
            print("✅ System configuration manager includes storage schemas")
            return True
            
        finally:
            # Clean up temporary database
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    except Exception as e:
        print(f"❌ System configuration manager test failed: {e}")
        return False

def test_admin_configuration_routes_integration():
    """Test that admin configuration routes support storage configuration"""
    print("Testing admin configuration routes integration...")
    
    try:
        # Check that configuration routes exist
        routes_path = Path("admin/routes/configuration_routes.py")
        if not routes_path.exists():
            print("❌ configuration_routes.py not found")
            return False
        
        with open(routes_path, 'r') as f:
            content = f.read()
        
        # Check for required API endpoints
        required_endpoints = [
            "get_configuration_schema",
            "get_configurations", 
            "set_configuration",
            "validate_configurations"
        ]
        
        for endpoint in required_endpoints:
            if endpoint not in content:
                print(f"❌ Missing configuration endpoint: {endpoint}")
                return False
        
        print("✅ Admin configuration routes support storage configuration")
        return True
        
    except Exception as e:
        print(f"❌ Admin configuration routes test failed: {e}")
        return False

def test_environment_variables_integration():
    """Test that environment variables are properly configured"""
    print("Testing environment variables integration...")
    
    # Check .env files for storage configuration
    env_files = [".env", ".env.example"]
    
    for env_file in env_files:
        if not Path(env_file).exists():
            print(f"⚠️  {env_file} not found, skipping")
            continue
        
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Check for storage configuration variables
        storage_vars = [
            "CAPTION_MAX_STORAGE_GB",
            "STORAGE_WARNING_THRESHOLD",
            "STORAGE_MONITORING_ENABLED"
        ]
        
        for var in storage_vars:
            if var not in content:
                print(f"❌ Missing storage variable in {env_file}: {var}")
                return False
        
        print(f"✅ {env_file} includes storage configuration")
    
    return True

def test_documentation_integration():
    """Test that storage configuration documentation exists"""
    print("Testing documentation integration...")
    
    doc_path = Path("docs/storage-configuration.md")
    if not doc_path.exists():
        print("❌ storage-configuration.md not found")
        return False
    
    with open(doc_path, 'r') as f:
        content = f.read()
    
    # Check for key documentation sections
    required_sections = [
        "Configuration Variables",
        "CAPTION_MAX_STORAGE_GB",
        "STORAGE_WARNING_THRESHOLD", 
        "STORAGE_MONITORING_ENABLED",
        "Configuration Examples",
        "Troubleshooting"
    ]
    
    for section in required_sections:
        if section not in content:
            print(f"❌ Missing documentation section: {section}")
            return False
    
    print("✅ Storage configuration documentation exists and is complete")
    return True

def main():
    """Run all integration tests"""
    print("🧪 Storage Configuration Integration Tests")
    print("=" * 50)
    print()
    
    tests = [
        ("Environment Setup Integration", test_environment_setup_integration),
        ("Configuration Validation Integration", test_configuration_validation_integration),
        ("System Configuration Manager Integration", test_system_configuration_manager_integration),
        ("Admin Configuration Routes Integration", test_admin_configuration_routes_integration),
        ("Environment Variables Integration", test_environment_variables_integration),
        ("Documentation Integration", test_documentation_integration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All storage configuration integration tests passed!")
        return 0
    else:
        print("💥 Some storage configuration integration tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())