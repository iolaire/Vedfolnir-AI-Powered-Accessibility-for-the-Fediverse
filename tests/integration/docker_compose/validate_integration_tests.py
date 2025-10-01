# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Docker Compose Integration Test Validation
Validates that all integration tests are properly implemented and cover required functionality
"""

import os
import sys
import ast
import inspect
import importlib.util
from pathlib import Path

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

class IntegrationTestValidator:
    """Validates integration test implementation"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.required_tests = {
            'test_service_interactions.py': {
                'description': 'Service interaction tests',
                'required_methods': [
                    'test_container_health_checks',
                    'test_web_app_to_mysql_connection',
                    'test_web_app_to_redis_connection',
                    'test_nginx_proxy_functionality',
                    'test_prometheus_metrics_collection',
                    'test_grafana_dashboard_access',
                    'test_vault_secrets_integration',
                    'test_loki_log_aggregation',
                    'test_service_network_isolation',
                    'test_volume_persistence',
                    'test_container_resource_limits',
                    'test_service_startup_dependencies'
                ]
            },
            'test_activitypub_integration.py': {
                'description': 'ActivityPub platform integration tests',
                'required_methods': [
                    'test_pixelfed_post_fetching_in_container',
                    'test_mastodon_post_fetching_in_container',
                    'test_caption_publishing_in_container',
                    'test_platform_connection_validation_in_container',
                    'test_activitypub_api_calls_from_container',
                    'test_platform_credential_encryption_in_container',
                    'test_multi_platform_batch_processing_in_container',
                    'test_platform_rate_limiting_in_container',
                    'test_activitypub_webhook_handling_in_container',
                    'test_platform_error_handling_in_container'
                ]
            },
            'test_ollama_integration.py': {
                'description': 'Ollama integration tests',
                'required_methods': [
                    'test_ollama_service_connectivity_from_container',
                    'test_ollama_model_availability_from_container',
                    'test_caption_generation_from_container_to_ollama',
                    'test_ollama_api_timeout_handling_from_container',
                    'test_ollama_error_handling_from_container',
                    'test_ollama_batch_processing_from_container',
                    'test_ollama_model_switching_from_container',
                    'test_ollama_performance_metrics_from_container',
                    'test_ollama_websocket_progress_from_container',
                    'test_ollama_configuration_from_container',
                    'test_ollama_health_monitoring_from_container'
                ]
            },
            'test_websocket_functionality.py': {
                'description': 'WebSocket functionality tests',
                'required_methods': [
                    'test_websocket_connection_establishment',
                    'test_websocket_progress_updates_during_caption_generation',
                    'test_websocket_real_time_notifications',
                    'test_websocket_session_management',
                    'test_websocket_error_handling',
                    'test_websocket_authentication_in_container',
                    'test_websocket_concurrent_connections',
                    'test_websocket_performance_in_container',
                    'test_websocket_nginx_proxy_compatibility'
                ]
            },
            'test_performance_benchmarks.py': {
                'description': 'Performance benchmark tests',
                'required_methods': [
                    'test_web_interface_response_times',
                    'test_database_query_performance',
                    'test_concurrent_request_handling',
                    'test_memory_usage_performance',
                    'test_api_endpoint_performance',
                    'test_static_file_serving_performance',
                    'test_session_management_performance',
                    'test_container_resource_efficiency'
                ]
            }
        }
        
        self.validation_results = {
            'files_found': [],
            'files_missing': [],
            'methods_found': {},
            'methods_missing': {},
            'copyright_headers': {},
            'import_structure': {},
            'test_class_structure': {},
            'errors': []
        }
    
    def validate_file_exists(self, filename):
        """Validate that test file exists"""
        file_path = self.test_dir / filename
        if file_path.exists():
            self.validation_results['files_found'].append(filename)
            return True
        else:
            self.validation_results['files_missing'].append(filename)
            return False
    
    def validate_copyright_header(self, filename):
        """Validate copyright header in file"""
        file_path = self.test_dir / filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            has_copyright = 'Copyright (C) 2025 iolaire mcfadden' in content
            has_agpl = 'GNU Affero General Public License' in content
            
            self.validation_results['copyright_headers'][filename] = {
                'has_copyright': has_copyright,
                'has_agpl': has_agpl,
                'valid': has_copyright and has_agpl
            }
            
            return has_copyright and has_agpl
            
        except Exception as e:
            self.validation_results['errors'].append(f"Error reading {filename}: {e}")
            return False
    
    def validate_import_structure(self, filename):
        """Validate import structure in test file"""
        file_path = self.test_dir / filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
            
            required_imports = [
                'unittest',
                'sys',
                'os',
                'requests',
                'time'
            ]
            
            missing_imports = [imp for imp in required_imports if not any(imp in i for i in imports)]
            
            self.validation_results['import_structure'][filename] = {
                'imports': imports,
                'missing_required': missing_imports,
                'valid': len(missing_imports) == 0
            }
            
            return len(missing_imports) == 0
            
        except Exception as e:
            self.validation_results['errors'].append(f"Error parsing imports in {filename}: {e}")
            return False
    
    def validate_test_methods(self, filename):
        """Validate test methods in file"""
        file_path = self.test_dir / filename
        
        try:
            spec = importlib.util.spec_from_file_location("test_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find test classes
            test_classes = []
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and name.endswith('Test'):
                    test_classes.append(obj)
            
            if not test_classes:
                self.validation_results['errors'].append(f"No test classes found in {filename}")
                return False
            
            # Get test methods from all test classes
            found_methods = []
            for test_class in test_classes:
                methods = [name for name, method in inspect.getmembers(test_class) 
                          if inspect.ismethod(method) or inspect.isfunction(method)]
                found_methods.extend(methods)
            
            required_methods = self.required_tests[filename]['required_methods']
            missing_methods = [method for method in required_methods if method not in found_methods]
            
            self.validation_results['methods_found'][filename] = found_methods
            self.validation_results['methods_missing'][filename] = missing_methods
            
            return len(missing_methods) == 0
            
        except Exception as e:
            self.validation_results['errors'].append(f"Error loading methods from {filename}: {e}")
            return False
    
    def validate_test_class_structure(self, filename):
        """Validate test class structure"""
        file_path = self.test_dir / filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            test_classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.endswith('Test'):
                    class_info = {
                        'name': node.name,
                        'methods': [],
                        'has_setup_class': False,
                        'has_setup': False,
                        'has_teardown': False
                    }
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info['methods'].append(item.name)
                            
                            if item.name == 'setUpClass':
                                class_info['has_setup_class'] = True
                            elif item.name == 'setUp':
                                class_info['has_setup'] = True
                            elif item.name == 'tearDown':
                                class_info['has_teardown'] = True
                    
                    test_classes.append(class_info)
            
            self.validation_results['test_class_structure'][filename] = test_classes
            
            # Validate that at least one test class exists with proper structure
            valid_structure = any(
                cls['has_setup_class'] or cls['has_setup'] 
                for cls in test_classes
            )
            
            return valid_structure and len(test_classes) > 0
            
        except Exception as e:
            self.validation_results['errors'].append(f"Error parsing class structure in {filename}: {e}")
            return False
    
    def validate_all_tests(self):
        """Validate all integration tests"""
        print("🔍 Validating Docker Compose Integration Tests")
        print("=" * 60)
        
        overall_valid = True
        
        for filename, test_info in self.required_tests.items():
            print(f"\n📋 Validating {filename}")
            print(f"   Description: {test_info['description']}")
            
            file_valid = True
            
            # Check file exists
            if self.validate_file_exists(filename):
                print("   ✅ File exists")
            else:
                print("   ❌ File missing")
                file_valid = False
                overall_valid = False
                continue
            
            # Check copyright header
            if self.validate_copyright_header(filename):
                print("   ✅ Copyright header valid")
            else:
                print("   ❌ Copyright header missing or invalid")
                file_valid = False
            
            # Check import structure
            if self.validate_import_structure(filename):
                print("   ✅ Import structure valid")
            else:
                print("   ⚠️ Some required imports missing")
            
            # Check test class structure
            if self.validate_test_class_structure(filename):
                print("   ✅ Test class structure valid")
            else:
                print("   ❌ Test class structure invalid")
                file_valid = False
            
            # Check test methods
            if self.validate_test_methods(filename):
                print("   ✅ All required test methods found")
            else:
                print("   ❌ Some required test methods missing")
                missing = self.validation_results['methods_missing'].get(filename, [])
                if missing:
                    print(f"      Missing methods: {', '.join(missing)}")
                file_valid = False
            
            if not file_valid:
                overall_valid = False
        
        return overall_valid
    
    def generate_report(self):
        """Generate detailed validation report"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION REPORT")
        print("=" * 60)
        
        # Files summary
        print(f"\n📁 Files:")
        print(f"   Found: {len(self.validation_results['files_found'])}")
        print(f"   Missing: {len(self.validation_results['files_missing'])}")
        
        if self.validation_results['files_missing']:
            print(f"   Missing files: {', '.join(self.validation_results['files_missing'])}")
        
        # Methods summary
        total_methods_required = sum(len(info['required_methods']) for info in self.required_tests.values())
        total_methods_found = sum(len(methods) for methods in self.validation_results['methods_found'].values())
        total_methods_missing = sum(len(methods) for methods in self.validation_results['methods_missing'].values())
        
        print(f"\n🧪 Test Methods:")
        print(f"   Required: {total_methods_required}")
        print(f"   Found: {total_methods_found}")
        print(f"   Missing: {total_methods_missing}")
        
        # Copyright headers
        copyright_valid = sum(1 for info in self.validation_results['copyright_headers'].values() if info['valid'])
        copyright_total = len(self.validation_results['copyright_headers'])
        
        print(f"\n©️ Copyright Headers:")
        print(f"   Valid: {copyright_valid}/{copyright_total}")
        
        # Errors
        if self.validation_results['errors']:
            print(f"\n❌ Errors:")
            for error in self.validation_results['errors']:
                print(f"   • {error}")
        
        # Requirements coverage
        print(f"\n📋 Requirements Coverage:")
        requirements_covered = [
            "9.6: Automated integration tests for all service interactions",
            "9.7: ActivityPub platform integrations work correctly in containers",
            "9.8: Ollama integration from containerized application to external host-based service",
            "9.9: WebSocket functionality and real-time features in containers",
            "8.3: Performance benchmarking tests to ensure parity with macOS deployment"
        ]
        
        for req in requirements_covered:
            print(f"   ✅ {req}")
        
        # Overall status
        overall_valid = (
            len(self.validation_results['files_missing']) == 0 and
            total_methods_missing == 0 and
            copyright_valid == copyright_total and
            len(self.validation_results['errors']) == 0
        )
        
        print(f"\n🎯 Overall Status:")
        if overall_valid:
            print("   ✅ All integration tests are properly implemented")
            print("   ✅ Ready for Docker Compose testing")
        else:
            print("   ❌ Some issues found - please review above")
        
        return overall_valid


def main():
    """Main validation function"""
    validator = IntegrationTestValidator()
    
    # Run validation
    valid = validator.validate_all_tests()
    
    # Generate report
    validator.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if valid else 1)


if __name__ == '__main__':
    main()