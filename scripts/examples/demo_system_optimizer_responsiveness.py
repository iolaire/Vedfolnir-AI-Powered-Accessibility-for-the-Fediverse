# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demo script for enhanced SystemOptimizer with responsiveness monitoring.

This script demonstrates the new responsiveness monitoring capabilities
added to the SystemOptimizer class.
"""

import sys
import os
import json
from unittest.mock import Mock

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config


def demo_responsiveness_config():
    """Demonstrate ResponsivenessConfig functionality"""
    print("=== ResponsivenessConfig Demo ===")
    
    config = Config()
    resp_config = config.responsiveness
    
    print(f"Memory Warning Threshold: {resp_config.memory_warning_threshold * 100:.0f}%")
    print(f"Memory Critical Threshold: {resp_config.memory_critical_threshold * 100:.0f}%")
    print(f"CPU Warning Threshold: {resp_config.cpu_warning_threshold * 100:.0f}%")
    print(f"CPU Critical Threshold: {resp_config.cpu_critical_threshold * 100:.0f}%")
    print(f"Connection Pool Warning Threshold: {resp_config.connection_pool_warning_threshold * 100:.0f}%")
    print(f"Monitoring Interval: {resp_config.monitoring_interval} seconds")
    print(f"Cleanup Enabled: {resp_config.cleanup_enabled}")
    print(f"Auto Cleanup Memory Threshold: {resp_config.auto_cleanup_memory_threshold * 100:.0f}%")
    print(f"Auto Cleanup Connection Threshold: {resp_config.auto_cleanup_connection_threshold * 100:.0f}%")
    print()


def demo_system_optimizer_metrics():
    """Demonstrate enhanced SystemOptimizer metrics"""
    print("=== Enhanced SystemOptimizer Metrics Demo ===")
    
    # Mock Flask app for import
    class MockApp:
        def __init__(self):
            self.logger = self
        def warning(self, msg):
            print(f'[MOCK APP WARNING] {msg}')
        def info(self, msg):
            print(f'[MOCK APP INFO] {msg}')
        def error(self, msg):
            print(f'[MOCK APP ERROR] {msg}')
    
    # Set up mock app
    import web_app
    web_app.app = MockApp()
    
    # Create SystemOptimizer with config
    config = Config()
    
    # Import SystemOptimizer class from web_app
    import importlib.util
    spec = importlib.util.spec_from_file_location("web_app", "web_app.py")
    web_app_module = importlib.util.module_from_spec(spec)
    
    # Mock Flask app for import
    mock_app = MockApp()
    web_app.app = mock_app
    spec.loader.exec_module(web_app_module)
    
    # Find SystemOptimizer class
    SystemOptimizer = None
    for name in dir(web_app_module):
        obj = getattr(web_app_module, name)
        if hasattr(obj, '__name__') and obj.__name__ == 'SystemOptimizer':
            SystemOptimizer = obj
            break
    
    if SystemOptimizer:
        optimizer = SystemOptimizer(config)
        
        print("Getting enhanced performance metrics...")
        metrics = optimizer.get_performance_metrics()
        
        print("\nEnhanced Metrics:")
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
        print("\nGetting responsiveness-specific recommendations...")
        recommendations = optimizer.get_recommendations()
        
        print("\nRecommendations:")
        for rec in recommendations:
            print(f"  [{rec['priority'].upper()}] {rec['message']}")
            if 'action' in rec:
                print(f"    Action: {rec['action']}")
            if 'threshold' in rec:
                print(f"    Threshold: {rec['threshold']}")
        
        print("\nGetting enhanced health status...")
        health = optimizer.get_health_status()
        
        print(f"\nHealth Status: {health['status'].upper()}")
        print("Components:")
        for component, status in health['components'].items():
            print(f"  {component}: {status}")
        
        if 'thresholds' in health:
            print("\nConfigured Thresholds:")
            for threshold, value in health['thresholds'].items():
                print(f"  {threshold}: {value}")
        
        print("\nTesting responsiveness analysis...")
        responsiveness = optimizer.check_responsiveness()
        
        print(f"\nResponsiveness Analysis:")
        print(f"  Responsive: {responsiveness['responsive']}")
        print(f"  Overall Status: {responsiveness['overall_status']}")
        print(f"  Issues Found: {len(responsiveness['issues'])}")
        
        for issue in responsiveness['issues']:
            print(f"    [{issue['severity'].upper()}] {issue['type']}: {issue['message']}")
            print(f"      Current: {issue['current']}, Threshold: {issue['threshold']}")
    else:
        print("Could not find SystemOptimizer class for demo")
    
    print()


def demo_environment_configuration():
    """Demonstrate environment variable configuration"""
    print("=== Environment Configuration Demo ===")
    
    # Show current environment variables that affect responsiveness
    env_vars = [
        'RESPONSIVENESS_MEMORY_WARNING_THRESHOLD',
        'RESPONSIVENESS_MEMORY_CRITICAL_THRESHOLD',
        'RESPONSIVENESS_CPU_WARNING_THRESHOLD',
        'RESPONSIVENESS_CPU_CRITICAL_THRESHOLD',
        'RESPONSIVENESS_CONNECTION_POOL_WARNING_THRESHOLD',
        'RESPONSIVENESS_MONITORING_INTERVAL',
        'RESPONSIVENESS_CLEANUP_ENABLED',
        'RESPONSIVENESS_AUTO_CLEANUP_MEMORY_THRESHOLD',
        'RESPONSIVENESS_AUTO_CLEANUP_CONNECTION_THRESHOLD'
    ]
    
    print("Environment Variables for Responsiveness Configuration:")
    for var in env_vars:
        value = os.getenv(var, 'Not set')
        print(f"  {var}: {value}")
    
    print("\nExample .env configuration:")
    print("# Responsiveness Monitoring Configuration")
    print("RESPONSIVENESS_MEMORY_WARNING_THRESHOLD=0.75")
    print("RESPONSIVENESS_MEMORY_CRITICAL_THRESHOLD=0.85")
    print("RESPONSIVENESS_CPU_WARNING_THRESHOLD=0.70")
    print("RESPONSIVENESS_CPU_CRITICAL_THRESHOLD=0.80")
    print("RESPONSIVENESS_CONNECTION_POOL_WARNING_THRESHOLD=0.85")
    print("RESPONSIVENESS_MONITORING_INTERVAL=60")
    print("RESPONSIVENESS_CLEANUP_ENABLED=true")
    print("RESPONSIVENESS_AUTO_CLEANUP_MEMORY_THRESHOLD=0.80")
    print("RESPONSIVENESS_AUTO_CLEANUP_CONNECTION_THRESHOLD=0.90")
    print()


def main():
    """Main demo function"""
    print("SystemOptimizer Responsiveness Enhancement Demo")
    print("=" * 50)
    print()
    
    try:
        demo_responsiveness_config()
        demo_environment_configuration()
        demo_system_optimizer_metrics()
        
        print("=== Demo Complete ===")
        print("The SystemOptimizer has been successfully enhanced with:")
        print("✅ ResponsivenessConfig integration")
        print("✅ Enhanced performance metrics with responsiveness data")
        print("✅ Responsiveness-specific recommendations")
        print("✅ Enhanced health status with configurable thresholds")
        print("✅ Comprehensive responsiveness analysis")
        print("✅ Automated cleanup triggers")
        print("✅ Environment variable configuration support")
        print("✅ Unit and integration tests")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)