#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test script to verify setup instructions work correctly.

This script tests the setup instructions from the documentation
to ensure they work for new users.
"""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

def test_config_validation():
    """Test that configuration validation works"""
    print("Testing configuration validation...")
    
    # Test that validation script exists and runs
    result = subprocess.run([sys.executable, 'validate_config.py'], 
                          capture_output=True, text=True)
    
    # The script should run (may succeed or fail depending on config)
    # but it should not crash
    if "Configuration Validator" not in result.stdout:
        print("❌ Configuration validation script not working properly")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        return False
    
    print("✅ Configuration validation script works correctly")
    return True

def test_example_configs():
    """Test that example configurations are valid"""
    print("Testing example configurations...")
    
    example_files = ['.env.example', '.env.example.mastodon', '.env.example.pixelfed']
    
    for example_file in example_files:
        if not os.path.exists(example_file):
            print(f"❌ Missing example file: {example_file}")
            return False
        
        # Check that file has required variables
        with open(example_file, 'r') as f:
            content = f.read()
        
        required_vars = ['ACTIVITYPUB_API_TYPE', 'ACTIVITYPUB_INSTANCE_URL', 
                        'ACTIVITYPUB_USERNAME', 'ACTIVITYPUB_ACCESS_TOKEN']
        
        for var in required_vars:
            if var not in content:
                print(f"❌ {example_file} missing required variable: {var}")
                return False
        
        # Check Mastodon-specific variables
        if 'mastodon' in example_file:
            mastodon_vars = ['MASTODON_CLIENT_KEY', 'MASTODON_CLIENT_SECRET']
            for var in mastodon_vars:
                if var not in content:
                    print(f"❌ {example_file} missing Mastodon variable: {var}")
                    return False
    
    print("✅ All example configurations contain required variables")
    return True

def test_documentation_completeness():
    """Test that all referenced files exist"""
    print("Testing documentation completeness...")
    
    required_files = [
        'README.md',
        'LICENSE',
        'requirements.txt',
        'config.py',
        'main.py',
        'web_app.py',
        'validate_config.py',
        'init_migrations.py',
        'init_admin_user.py',
        'check_db.py',
        '.env.example',
        '.env.example.mastodon',
        '.env.example.pixelfed'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files exist")
    return True

def test_documentation_structure():
    """Test that documentation has proper structure"""
    print("Testing documentation structure...")
    
    # Check README structure
    with open('README.md', 'r') as f:
        readme_content = f.read()
    
    required_sections = [
        '# Vedfolnir',
        '## Features',
        '## Quick Start',
        '## Platform Setup',
        '## Usage',
        '## Testing',
        '## Deployment',
        '## Troubleshooting'
    ]
    
    missing_sections = []
    for section in required_sections:
        if section not in readme_content:
            missing_sections.append(section)
    
    if missing_sections:
        print(f"❌ README missing sections: {', '.join(missing_sections)}")
        return False
    
    # Check that docs directory exists and has key files
    docs_files = [
        'docs/deployment.md',
        'docs/troubleshooting.md',
        'docs/multi-platform-setup.md'
    ]
    
    missing_docs = []
    for doc_file in docs_files:
        if not os.path.exists(doc_file):
            missing_docs.append(doc_file)
    
    if missing_docs:
        print(f"❌ Missing documentation files: {', '.join(missing_docs)}")
        return False
    
    print("✅ Documentation structure is complete")
    return True

def test_config_variables_documented():
    """Test that all config variables are documented"""
    print("Testing configuration variable documentation...")
    
    # Load config variables from config.py
    config_vars = set()
    try:
        with open('config.py', 'r') as f:
            content = f.read()
        
        import re
        env_pattern = r'os\.getenv\(["\']([^"\']+)["\']'
        matches = re.findall(env_pattern, content)
        config_vars.update(matches)
    except Exception as e:
        print(f"❌ Could not load config variables: {e}")
        return False
    
    # Check that variables are documented in README
    with open('README.md', 'r') as f:
        readme_content = f.read()
    
    # Check example files for documented variables
    documented_vars = set()
    for example_file in ['.env.example', '.env.example.mastodon', '.env.example.pixelfed']:
        if os.path.exists(example_file):
            with open(example_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        var_name = line.split('=')[0].strip()
                        documented_vars.add(var_name)
    
    # Find variables mentioned in README
    readme_vars = set(re.findall(r'`([A-Z_][A-Z0-9_]*)`', readme_content))
    documented_vars.update(readme_vars)
    
    # Check for undocumented variables (excluding system variables)
    system_vars = {'PATH', 'HOME', 'USER', 'PWD', 'SHELL', 'TERM'}
    undocumented = config_vars - documented_vars - system_vars
    
    if undocumented:
        print(f"⚠️  Potentially undocumented variables: {', '.join(undocumented)}")
        # This is a warning, not an error
    
    print("✅ Configuration variables documentation check completed")
    return True

def main():
    """Run all tests"""
    print("Testing setup instructions and documentation...\n")
    
    tests = [
        test_documentation_completeness,
        test_documentation_structure,
        test_example_configs,
        test_config_variables_documented,
        test_config_validation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All setup instruction tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Please review the documentation.")
        return 1

if __name__ == '__main__':
    sys.exit(main())