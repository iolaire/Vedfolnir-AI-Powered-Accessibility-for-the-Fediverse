# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Validation Framework Tests
Test that the validation framework itself is working correctly
"""

import unittest
import os
import sys
import subprocess
import importlib.util

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class ValidationFrameworkTest(unittest.TestCase):
    """Test the validation framework components"""
    
    def test_validation_scripts_exist(self):
        """Test that all validation scripts exist"""
        print("\n=== Testing Validation Scripts Existence ===")
        
        required_files = [
            'scripts/validation/validate_docker_compose_deployment.py',
            'scripts/validation/run_comprehensive_validation.sh',
            'scripts/validation/test_individual_components.py',
            'scripts/validation/README.md',
            'tests/integration/test_docker_compose_validation.py',
            'tests/integration/test_api_endpoint_validation.py',
            'tests/integration/test_backup_restore_validation.py',
            'tests/performance/test_docker_performance_benchmarks.py',
            'tests/security/test_docker_security_compliance.py'
        ]
        
        for file_path in required_files:
            with self.subTest(file=file_path):
                self.assertTrue(os.path.exists(file_path), f"Required file missing: {file_path}")
                print(f"✅ {file_path}: exists")
    
    def test_validation_scripts_executable(self):
        """Test that shell scripts are executable"""
        print("\n=== Testing Script Permissions ===")
        
        executable_scripts = [
            'scripts/validation/run_comprehensive_validation.sh'
        ]
        
        for script_path in executable_scripts:
            with self.subTest(script=script_path):
                self.assertTrue(os.path.exists(script_path), f"Script missing: {script_path}")
                self.assertTrue(os.access(script_path, os.X_OK), f"Script not executable: {script_path}")
                print(f"✅ {script_path}: executable")
    
    def test_python_validation_modules_importable(self):
        """Test that Python validation modules can be imported"""
        print("\n=== Testing Python Module Imports ===")
        
        modules = [
            ('tests.integration.test_docker_compose_validation', 'DockerComposeValidationTest'),
            ('tests.integration.test_api_endpoint_validation', 'APIEndpointValidationTest'),
            ('tests.integration.test_backup_restore_validation', 'BackupRestoreValidationTest'),
            ('tests.performance.test_docker_performance_benchmarks', 'DockerPerformanceBenchmarkTest'),
            ('tests.security.test_docker_security_compliance', 'DockerSecurityComplianceTest')
        ]
        
        for module_name, class_name in modules:
            with self.subTest(module=module_name):
                try:
                    module = importlib.import_module(module_name)
                    self.assertTrue(hasattr(module, class_name), 
                                  f"Class {class_name} not found in {module_name}")
                    print(f"✅ {module_name}: importable")
                except ImportError as e:
                    self.fail(f"Failed to import {module_name}: {e}")
    
    def test_validation_script_syntax(self):
        """Test that validation scripts have valid syntax"""
        print("\n=== Testing Script Syntax ===")
        
        python_scripts = [
            'scripts/validation/validate_docker_compose_deployment.py',
            'scripts/validation/test_individual_components.py'
        ]
        
        for script_path in python_scripts:
            with self.subTest(script=script_path):
                try:
                    # Test syntax by compiling the file
                    with open(script_path, 'r') as f:
                        source = f.read()
                    
                    compile(source, script_path, 'exec')
                    print(f"✅ {script_path}: valid syntax")
                    
                except SyntaxError as e:
                    self.fail(f"Syntax error in {script_path}: {e}")
                except Exception as e:
                    self.fail(f"Error checking {script_path}: {e}")
    
    def test_shell_script_syntax(self):
        """Test that shell scripts have valid syntax"""
        print("\n=== Testing Shell Script Syntax ===")
        
        shell_scripts = [
            'scripts/validation/run_comprehensive_validation.sh'
        ]
        
        for script_path in shell_scripts:
            with self.subTest(script=script_path):
                try:
                    # Test shell script syntax using bash -n
                    result = subprocess.run(['bash', '-n', script_path], 
                                          capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(f"✅ {script_path}: valid syntax")
                    else:
                        self.fail(f"Shell syntax error in {script_path}: {result.stderr}")
                        
                except Exception as e:
                    self.fail(f"Error checking {script_path}: {e}")
    
    def test_validation_help_commands(self):
        """Test that validation scripts provide help"""
        print("\n=== Testing Help Commands ===")
        
        help_tests = [
            ('scripts/validation/run_comprehensive_validation.sh', ['--help']),
            ('scripts/validation/test_individual_components.py', ['--help'])
        ]
        
        for script_path, help_args in help_tests:
            with self.subTest(script=script_path):
                try:
                    if script_path.endswith('.py'):
                        cmd = ['python3', script_path] + help_args
                    else:
                        cmd = [script_path] + help_args
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    # Help should exit with 0 and provide usage information
                    self.assertEqual(result.returncode, 0, f"Help command failed for {script_path}")
                    self.assertIn('usage', result.stdout.lower() + result.stderr.lower(),
                                f"No usage information in help for {script_path}")
                    
                    print(f"✅ {script_path}: provides help")
                    
                except subprocess.TimeoutExpired:
                    self.fail(f"Help command timed out for {script_path}")
                except Exception as e:
                    self.fail(f"Error testing help for {script_path}: {e}")
    
    def test_required_dependencies_documented(self):
        """Test that required dependencies are documented"""
        print("\n=== Testing Dependency Documentation ===")
        
        readme_path = 'scripts/validation/README.md'
        
        self.assertTrue(os.path.exists(readme_path), "README.md missing")
        
        with open(readme_path, 'r') as f:
            readme_content = f.read()
        
        # Check for key sections
        required_sections = [
            'Prerequisites',
            'Quick Start',
            'Usage Examples',
            'Configuration Options',
            'Troubleshooting'
        ]
        
        for section in required_sections:
            self.assertIn(section, readme_content, f"README missing section: {section}")
            print(f"✅ README contains section: {section}")
        
        # Check for dependency information
        dependencies = ['requests', 'docker', 'redis', 'mysql-connector-python']
        for dep in dependencies:
            self.assertIn(dep, readme_content, f"README missing dependency: {dep}")
            print(f"✅ README documents dependency: {dep}")
    
    def test_validation_framework_completeness(self):
        """Test that the validation framework covers all required areas"""
        print("\n=== Testing Framework Completeness ===")
        
        # Check that all major validation areas are covered
        validation_areas = {
            'Container Infrastructure': ('tests/integration', 'test_docker_compose_validation.py'),
            'API Endpoints': ('tests/integration', 'test_api_endpoint_validation.py'),
            'Backup/Restore': ('tests/integration', 'test_backup_restore_validation.py'),
            'Performance': ('tests/performance', 'test_docker_performance_benchmarks.py'),
            'Security': ('tests/security', 'test_docker_security_compliance.py')
        }
        
        for area, (test_dir, test_file) in validation_areas.items():
            test_path = os.path.join(test_dir, test_file)
            
            with self.subTest(area=area):
                self.assertTrue(os.path.exists(test_path), 
                              f"Validation area {area} missing test file: {test_path}")
                print(f"✅ {area}: covered by {test_file}")
    
    def test_copyright_headers_present(self):
        """Test that all validation scripts have copyright headers"""
        print("\n=== Testing Copyright Headers ===")
        
        script_files = [
            'scripts/validation/validate_docker_compose_deployment.py',
            'scripts/validation/test_individual_components.py',
            'scripts/validation/run_comprehensive_validation.sh',
            'tests/integration/test_docker_compose_validation.py',
            'tests/integration/test_api_endpoint_validation.py',
            'tests/integration/test_backup_restore_validation.py',
            'tests/performance/test_docker_performance_benchmarks.py',
            'tests/security/test_docker_security_compliance.py'
        ]
        
        for script_path in script_files:
            with self.subTest(script=script_path):
                with open(script_path, 'r') as f:
                    content = f.read()
                
                self.assertIn('Copyright (C) 2025 iolaire mcfadden', content,
                            f"Copyright header missing in {script_path}")
                print(f"✅ {script_path}: has copyright header")


if __name__ == '__main__':
    unittest.main(verbosity=2)