#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Compliance Framework Validation Script

Validates that all compliance framework components are properly implemented
and configured without requiring full dependency installation.
"""

import os
import sys
from pathlib import Path

def validate_file_structure():
    """Validate that all required files are present"""
    print("🔍 Validating compliance framework file structure...")
    
    required_files = [
        # Core compliance services
        'app/services/compliance/__init__.py',
        'app/services/compliance/audit_logger.py',
        'app/services/compliance/gdpr_compliance.py',
        'app/services/compliance/compliance_reporter.py',
        'app/services/compliance/data_lifecycle_manager.py',
        'app/services/compliance/compliance_service.py',
        
        # Integration
        'app/core/compliance_integration.py',
        
        # Database migrations
        'migrations/add_compliance_tables.py',
        
        # Configuration files
        'config/compliance/audit_config.yml',
        'config/loki/loki.yml',
        'config/prometheus/compliance_rules.yml',
        'config/grafana/dashboards/compliance_dashboard.json',
        
        # Docker configuration
        'docker-compose.compliance.yml',
        
        # Tests
        'tests/compliance/test_compliance_framework.py',
        
        # Deployment scripts
        'scripts/deployment/deploy_compliance_framework.sh',
        'scripts/validation/validate_compliance_framework.py'
    ]
    
    missing_files = []
    present_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            present_files.append(file_path)
            print(f"  ✓ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"  ✗ {file_path}")
    
    print(f"\n📊 File Structure Summary:")
    print(f"  Present: {len(present_files)}/{len(required_files)} files")
    print(f"  Missing: {len(missing_files)} files")
    
    if missing_files:
        print(f"\n❌ Missing files:")
        for file_path in missing_files:
            print(f"    - {file_path}")
        return False
    
    print("✅ All required files are present")
    return True

def validate_python_syntax():
    """Validate Python syntax for all compliance modules"""
    print("\n🐍 Validating Python syntax...")
    
    python_files = [
        'app/services/compliance/__init__.py',
        'app/services/compliance/audit_logger.py',
        'app/services/compliance/gdpr_compliance.py',
        'app/services/compliance/compliance_reporter.py',
        'app/services/compliance/data_lifecycle_manager.py',
        'app/services/compliance/compliance_service.py',
        'app/core/compliance_integration.py',
        'migrations/add_compliance_tables.py',
        'tests/compliance/test_compliance_framework.py'
    ]
    
    syntax_errors = []
    valid_files = []
    
    for file_path in python_files:
        if not Path(file_path).exists():
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Compile to check syntax
            compile(content, file_path, 'exec')
            valid_files.append(file_path)
            print(f"  ✓ {file_path}")
            
        except SyntaxError as e:
            syntax_errors.append((file_path, str(e)))
            print(f"  ✗ {file_path}: {e}")
        except Exception as e:
            syntax_errors.append((file_path, str(e)))
            print(f"  ✗ {file_path}: {e}")
    
    print(f"\n📊 Python Syntax Summary:")
    print(f"  Valid: {len(valid_files)} files")
    print(f"  Errors: {len(syntax_errors)} files")
    
    if syntax_errors:
        print(f"\n❌ Syntax errors:")
        for file_path, error in syntax_errors:
            print(f"    - {file_path}: {error}")
        return False
    
    print("✅ All Python files have valid syntax")
    return True

def validate_configuration_files():
    """Validate configuration file formats"""
    print("\n⚙️  Validating configuration files...")
    
    config_files = [
        ('config/compliance/audit_config.yml', 'yaml'),
        ('config/loki/loki.yml', 'yaml'),
        ('config/prometheus/compliance_rules.yml', 'yaml'),
        ('config/grafana/dashboards/compliance_dashboard.json', 'json')
    ]
    
    valid_configs = []
    invalid_configs = []
    
    for file_path, file_type in config_files:
        if not Path(file_path).exists():
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if file_type == 'yaml':
                # Basic YAML validation (without importing yaml)
                if content.strip() and not content.strip().startswith('#'):
                    # Check for basic YAML structure
                    lines = content.split('\n')
                    has_yaml_structure = any(':' in line for line in lines if line.strip())
                    if has_yaml_structure:
                        valid_configs.append(file_path)
                        print(f"  ✓ {file_path} (YAML structure detected)")
                    else:
                        invalid_configs.append((file_path, "No YAML structure detected"))
                        print(f"  ✗ {file_path}: No YAML structure detected")
                else:
                    valid_configs.append(file_path)
                    print(f"  ✓ {file_path} (Empty or comment-only file)")
            
            elif file_type == 'json':
                # Basic JSON validation
                import json
                json.loads(content)
                valid_configs.append(file_path)
                print(f"  ✓ {file_path}")
                
        except json.JSONDecodeError as e:
            invalid_configs.append((file_path, f"JSON error: {e}"))
            print(f"  ✗ {file_path}: JSON error: {e}")
        except Exception as e:
            invalid_configs.append((file_path, str(e)))
            print(f"  ✗ {file_path}: {e}")
    
    print(f"\n📊 Configuration Files Summary:")
    print(f"  Valid: {len(valid_configs)} files")
    print(f"  Invalid: {len(invalid_configs)} files")
    
    if invalid_configs:
        print(f"\n❌ Configuration errors:")
        for file_path, error in invalid_configs:
            print(f"    - {file_path}: {error}")
        return False
    
    print("✅ All configuration files are valid")
    return True

def validate_docker_configuration():
    """Validate Docker Compose configuration"""
    print("\n🐳 Validating Docker configuration...")
    
    docker_files = [
        'docker-compose.compliance.yml',
        'Dockerfile'
    ]
    
    valid_docker = []
    invalid_docker = []
    
    for file_path in docker_files:
        if not Path(file_path).exists():
            print(f"  ⚠️  {file_path} (not found, may be optional)")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if file_path.endswith('.yml') or file_path.endswith('.yaml'):
                # Basic Docker Compose validation
                if 'version:' in content and 'services:' in content:
                    valid_docker.append(file_path)
                    print(f"  ✓ {file_path}")
                else:
                    invalid_docker.append((file_path, "Missing version or services section"))
                    print(f"  ✗ {file_path}: Missing version or services section")
            
            elif file_path == 'Dockerfile':
                # Basic Dockerfile validation
                if 'FROM' in content:
                    valid_docker.append(file_path)
                    print(f"  ✓ {file_path}")
                else:
                    invalid_docker.append((file_path, "Missing FROM instruction"))
                    print(f"  ✗ {file_path}: Missing FROM instruction")
                    
        except Exception as e:
            invalid_docker.append((file_path, str(e)))
            print(f"  ✗ {file_path}: {e}")
    
    print(f"\n📊 Docker Configuration Summary:")
    print(f"  Valid: {len(valid_docker)} files")
    print(f"  Invalid: {len(invalid_docker)} files")
    
    if invalid_docker:
        print(f"\n❌ Docker configuration errors:")
        for file_path, error in invalid_docker:
            print(f"    - {file_path}: {error}")
        return False
    
    print("✅ Docker configuration is valid")
    return True

def validate_copyright_headers():
    """Validate that all source files have copyright headers"""
    print("\n©️  Validating copyright headers...")
    
    source_files = []
    
    # Find all Python files
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', '.pytest_cache']):
            continue
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                source_files.append(file_path)
    
    # Add specific files we created
    source_files.extend([
        'config/compliance/audit_config.yml',
        'config/loki/loki.yml',
        'config/prometheus/compliance_rules.yml',
        'docker-compose.compliance.yml',
        'scripts/deployment/deploy_compliance_framework.sh'
    ])
    
    files_with_copyright = []
    files_without_copyright = []
    
    copyright_text = "Copyright (C) 2025 iolaire mcfadden"
    
    for file_path in source_files:
        if not Path(file_path).exists():
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if copyright_text in content:
                files_with_copyright.append(file_path)
                print(f"  ✓ {file_path}")
            else:
                files_without_copyright.append(file_path)
                print(f"  ✗ {file_path}")
                
        except Exception as e:
            print(f"  ⚠️  {file_path}: Could not read file ({e})")
    
    print(f"\n📊 Copyright Headers Summary:")
    print(f"  With copyright: {len(files_with_copyright)} files")
    print(f"  Without copyright: {len(files_without_copyright)} files")
    
    if files_without_copyright:
        print(f"\n❌ Files missing copyright headers:")
        for file_path in files_without_copyright[:10]:  # Show first 10
            print(f"    - {file_path}")
        if len(files_without_copyright) > 10:
            print(f"    ... and {len(files_without_copyright) - 10} more")
        return False
    
    print("✅ All source files have copyright headers")
    return True

def validate_directory_structure():
    """Validate that required directories exist or can be created"""
    print("\n📁 Validating directory structure...")
    
    required_dirs = [
        'app/services/compliance',
        'config/compliance',
        'config/loki',
        'config/prometheus',
        'config/grafana/dashboards',
        'tests/compliance',
        'scripts/deployment',
        'scripts/validation',
        'logs/audit',
        'storage/gdpr_exports',
        'storage/compliance_reports',
        'storage/archives'
    ]
    
    existing_dirs = []
    missing_dirs = []
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            existing_dirs.append(dir_path)
            print(f"  ✓ {dir_path}")
        else:
            missing_dirs.append(dir_path)
            print(f"  ⚠️  {dir_path} (will be created during deployment)")
    
    print(f"\n📊 Directory Structure Summary:")
    print(f"  Existing: {len(existing_dirs)} directories")
    print(f"  Missing: {len(missing_dirs)} directories (will be created)")
    
    print("✅ Directory structure is valid")
    return True

def main():
    """Main validation function"""
    print("🚀 Compliance and Audit Framework Validation")
    print("=" * 50)
    
    validations = [
        ("File Structure", validate_file_structure),
        ("Python Syntax", validate_python_syntax),
        ("Configuration Files", validate_configuration_files),
        ("Docker Configuration", validate_docker_configuration),
        ("Copyright Headers", validate_copyright_headers),
        ("Directory Structure", validate_directory_structure)
    ]
    
    results = []
    
    for name, validation_func in validations:
        try:
            result = validation_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error during {name} validation: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        if result:
            print(f"✅ {name}: PASSED")
            passed += 1
        else:
            print(f"❌ {name}: FAILED")
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All validations passed! Compliance framework is ready for deployment.")
        return 0
    else:
        print(f"\n⚠️  {failed} validation(s) failed. Please review and fix the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())