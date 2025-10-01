#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Container Configuration Validation Script
Validates that all container components are properly configured
"""

import os
import sys
import json
import subprocess
from typing import Dict, Any, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class ContainerConfigValidator:
    """Validates container configuration and components"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed_checks = []
    
    def validate_all(self) -> bool:
        """Run all validation checks"""
        print("=== Container Configuration Validation ===\n")
        
        # Core configuration checks
        self.check_dockerfile()
        self.check_gunicorn_config()
        self.check_startup_scripts()
        self.check_health_scripts()
        
        # Application component checks
        self.check_rq_integration()
        self.check_container_metrics()
        self.check_resource_config()
        self.check_logging_config()
        
        # Environment checks
        self.check_environment_variables()
        self.check_file_permissions()
        
        # Print results
        self.print_results()
        
        return len(self.errors) == 0
    
    def check_dockerfile(self) -> None:
        """Validate Dockerfile configuration"""
        print("Checking Dockerfile...")
        
        dockerfile_path = "Dockerfile"
        if not os.path.exists(dockerfile_path):
            self.errors.append("Dockerfile not found")
            return
        
        with open(dockerfile_path, 'r') as f:
            content = f.read()
        
        # Check for required stages
        if 'FROM python:3.12-slim as base' not in content:
            self.errors.append("Dockerfile missing base stage with python:3.12-slim")
        else:
            self.passed_checks.append("Dockerfile has correct base image")
        
        if 'FROM base as development' not in content:
            self.errors.append("Dockerfile missing development stage")
        else:
            self.passed_checks.append("Dockerfile has development stage")
        
        if 'FROM base as production' not in content:
            self.errors.append("Dockerfile missing production stage")
        else:
            self.passed_checks.append("Dockerfile has production stage")
        
        # Check for container-specific configurations
        required_packages = ['gunicorn', 'eventlet', 'netcat-openbsd']
        for package in required_packages:
            if package not in content:
                self.warnings.append(f"Dockerfile may be missing {package} package")
        
        # Check for health checks
        if 'HEALTHCHECK' not in content:
            self.errors.append("Dockerfile missing health check configuration")
        else:
            self.passed_checks.append("Dockerfile has health check configuration")
    
    def check_gunicorn_config(self) -> None:
        """Validate Gunicorn configuration"""
        print("Checking Gunicorn configuration...")
        
        config_path = "gunicorn.conf.py"
        if not os.path.exists(config_path):
            self.errors.append("gunicorn.conf.py not found")
            return
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Check for container-specific settings
        required_settings = [
            'IS_CONTAINER',
            'worker_class = "eventlet"',
            'RQ_ENABLE_INTEGRATED_WORKERS',
            'when_ready',
            'post_fork'
        ]
        
        for setting in required_settings:
            if setting not in content:
                self.errors.append(f"Gunicorn config missing: {setting}")
            else:
                self.passed_checks.append(f"Gunicorn config has: {setting}")
    
    def check_startup_scripts(self) -> None:
        """Validate startup scripts"""
        print("Checking startup scripts...")
        
        scripts = [
            "docker/scripts/init-app.sh",
            "docker/scripts/init-app-dev.sh"
        ]
        
        for script_path in scripts:
            if not os.path.exists(script_path):
                self.errors.append(f"Startup script not found: {script_path}")
                continue
            
            if not os.access(script_path, os.X_OK):
                self.errors.append(f"Startup script not executable: {script_path}")
                continue
            
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Check for required functions
            required_functions = [
                'wait_for_dependencies',
                'initialize_database',
                'main'
            ]
            
            for func in required_functions:
                if func not in content:
                    self.warnings.append(f"Script {script_path} missing function: {func}")
                else:
                    self.passed_checks.append(f"Script {script_path} has function: {func}")
    
    def check_health_scripts(self) -> None:
        """Validate health check scripts"""
        print("Checking health check scripts...")
        
        scripts = [
            "docker/scripts/health-check.sh",
            "docker/scripts/health-check-dev.sh"
        ]
        
        for script_path in scripts:
            if not os.path.exists(script_path):
                self.errors.append(f"Health check script not found: {script_path}")
                continue
            
            if not os.access(script_path, os.X_OK):
                self.errors.append(f"Health check script not executable: {script_path}")
                continue
            
            self.passed_checks.append(f"Health check script exists and is executable: {script_path}")
    
    def check_rq_integration(self) -> None:
        """Validate RQ integration for containers"""
        print("Checking RQ integration...")
        
        try:
            from app.services.task.rq.gunicorn_integration import GunicornRQIntegration
            self.passed_checks.append("RQ Gunicorn integration module imports successfully")
            
            # Check for container-specific methods
            integration_class = GunicornRQIntegration
            required_methods = [
                '_adjust_config_for_container',
                '_wait_for_container_dependencies'
            ]
            
            for method in required_methods:
                if hasattr(integration_class, method):
                    self.passed_checks.append(f"RQ integration has method: {method}")
                else:
                    self.errors.append(f"RQ integration missing method: {method}")
                    
        except ImportError as e:
            self.errors.append(f"Failed to import RQ integration: {e}")
    
    def check_container_metrics(self) -> None:
        """Validate container metrics module"""
        print("Checking container metrics...")
        
        try:
            from app.services.monitoring.container.container_metrics import ContainerMetricsCollector
            self.passed_checks.append("Container metrics module imports successfully")
            
            # Test metrics collection
            collector = ContainerMetricsCollector()
            if collector.is_container or os.getenv('CONTAINER_ENV') == 'true':
                self.passed_checks.append("Container environment detected correctly")
            else:
                self.warnings.append("Container environment not detected (expected in non-container environment)")
                
        except ImportError as e:
            self.errors.append(f"Failed to import container metrics: {e}")
        except Exception as e:
            self.warnings.append(f"Container metrics initialization issue: {e}")
    
    def check_resource_config(self) -> None:
        """Validate resource configuration"""
        print("Checking resource configuration...")
        
        try:
            from app.core.configuration.container.resource_config import ContainerResourceConfig
            self.passed_checks.append("Resource configuration module imports successfully")
            
            # Test configuration
            config = ContainerResourceConfig()
            summary = config.get_resource_summary()
            
            if 'resource_tier' in summary:
                self.passed_checks.append(f"Resource tier detected: {summary['resource_tier']}")
            else:
                self.errors.append("Resource tier not detected")
                
        except ImportError as e:
            self.errors.append(f"Failed to import resource config: {e}")
        except Exception as e:
            self.warnings.append(f"Resource config initialization issue: {e}")
    
    def check_logging_config(self) -> None:
        """Validate container logging configuration"""
        print("Checking logging configuration...")
        
        try:
            from app.utils.logging.container_logger import ContainerLoggerConfig
            self.passed_checks.append("Container logging module imports successfully")
            
            # Test logging configuration
            config = ContainerLoggerConfig()
            logger = config.setup_logging('test_logger')
            
            if logger:
                self.passed_checks.append("Container logging setup successful")
            else:
                self.errors.append("Container logging setup failed")
                
        except ImportError as e:
            self.errors.append(f"Failed to import container logging: {e}")
        except Exception as e:
            self.warnings.append(f"Container logging initialization issue: {e}")
    
    def check_environment_variables(self) -> None:
        """Check for required environment variables"""
        print("Checking environment variables...")
        
        # Required for production
        required_vars = [
            'DATABASE_URL',
            'FLASK_SECRET_KEY'
        ]
        
        # Optional but recommended
        recommended_vars = [
            'REDIS_URL',
            'MEMORY_LIMIT',
            'CPU_LIMIT',
            'RQ_ENABLE_INTEGRATED_WORKERS'
        ]
        
        for var in required_vars:
            if os.getenv(var):
                self.passed_checks.append(f"Required environment variable set: {var}")
            else:
                self.warnings.append(f"Required environment variable not set: {var}")
        
        for var in recommended_vars:
            if os.getenv(var):
                self.passed_checks.append(f"Recommended environment variable set: {var}")
            else:
                self.warnings.append(f"Recommended environment variable not set: {var}")
    
    def check_file_permissions(self) -> None:
        """Check file permissions for container environment"""
        print("Checking file permissions...")
        
        # Directories that need to be writable
        writable_dirs = [
            'logs',
            'storage',
            'storage/images',
            'storage/backups',
            'storage/temp'
        ]
        
        for dir_path in writable_dirs:
            if os.path.exists(dir_path):
                if os.access(dir_path, os.W_OK):
                    self.passed_checks.append(f"Directory is writable: {dir_path}")
                else:
                    self.errors.append(f"Directory is not writable: {dir_path}")
            else:
                self.warnings.append(f"Directory does not exist: {dir_path}")
        
        # Scripts that need to be executable
        executable_scripts = [
            'docker/scripts/init-app.sh',
            'docker/scripts/init-app-dev.sh',
            'docker/scripts/health-check.sh',
            'docker/scripts/health-check-dev.sh'
        ]
        
        for script_path in executable_scripts:
            if os.path.exists(script_path):
                if os.access(script_path, os.X_OK):
                    self.passed_checks.append(f"Script is executable: {script_path}")
                else:
                    self.errors.append(f"Script is not executable: {script_path}")
    
    def print_results(self) -> None:
        """Print validation results"""
        print("\n" + "="*50)
        print("VALIDATION RESULTS")
        print("="*50)
        
        if self.passed_checks:
            print(f"\n✅ PASSED ({len(self.passed_checks)}):")
            for check in self.passed_checks:
                print(f"  • {check}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        
        print("\n" + "="*50)
        
        if self.errors:
            print("❌ VALIDATION FAILED - Please fix the errors above")
            return False
        elif self.warnings:
            print("⚠️  VALIDATION PASSED WITH WARNINGS - Consider addressing warnings")
            return True
        else:
            print("✅ VALIDATION PASSED - Container configuration is ready")
            return True


def main():
    """Main validation function"""
    validator = ContainerConfigValidator()
    success = validator.validate_all()
    
    if success:
        print("\n🎉 Container configuration validation completed successfully!")
        print("The application is ready for containerized deployment.")
        sys.exit(0)
    else:
        print("\n💥 Container configuration validation failed!")
        print("Please fix the errors before deploying to containers.")
        sys.exit(1)


if __name__ == "__main__":
    main()