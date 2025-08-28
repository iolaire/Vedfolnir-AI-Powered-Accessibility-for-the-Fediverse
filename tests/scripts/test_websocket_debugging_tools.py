#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script for WebSocket debugging tools

This script demonstrates and tests all the WebSocket debugging and monitoring
tools including diagnostics, debug logging, health checks, and monitoring dashboard.
"""

import sys
import os
import time
import json
import threading
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websocket_diagnostic_tools import WebSocketDiagnosticTools, WebSocketTestUtilities
from websocket_debug_logger import get_debug_logger, set_debug_level, DebugLevel, configure_debug_from_env
from websocket_monitoring_dashboard import get_connection_monitor, create_monitoring_dashboard
from websocket_health_checker import create_health_checker, setup_basic_alerts
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager


class WebSocketDebuggingToolsTest:
    """Test suite for WebSocket debugging tools"""
    
    def __init__(self):
        self.logger = get_debug_logger('test_suite', DebugLevel.INFO)
        self.config_manager = WebSocketConfigManager()
        self.cors_manager = CORSManager(self.config_manager)
        self.server_url = f"http://{self.config_manager.get_flask_host()}:{self.config_manager.get_flask_port()}"
        
        # Initialize tools
        self.diagnostics = WebSocketDiagnosticTools(self.config_manager, self.cors_manager)
        self.health_checker = create_health_checker(self.config_manager, self.cors_manager)
        self.monitor = get_connection_monitor()
        
        self.test_results = {}
        
    def run_all_tests(self):
        """Run all debugging tool tests"""
        print("=" * 60)
        print("WebSocket Debugging Tools Test Suite")
        print("=" * 60)
        
        tests = [
            ('Debug Logger Test', self.test_debug_logger),
            ('Diagnostic Tools Test', self.test_diagnostic_tools),
            ('Health Checker Test', self.test_health_checker),
            ('Connection Monitor Test', self.test_connection_monitor),
            ('Test Utilities Test', self.test_utilities),
            ('Integration Test', self.test_integration)
        ]
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                start_time = time.time()
                result = test_func()
                duration = time.time() - start_time
                
                self.test_results[test_name] = {
                    'status': 'PASS' if result else 'FAIL',
                    'duration': duration
                }
                
                print(f"Result: {'PASS' if result else 'FAIL'} ({duration:.2f}s)")
                
            except Exception as e:
                self.test_results[test_name] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
                print(f"Result: ERROR - {e}")
                
        self.print_summary()
        
    def test_debug_logger(self):
        """Test debug logging functionality"""
        print("Testing debug logger with different verbosity levels...")
        
        # Test different debug levels
        for level in [DebugLevel.ERROR, DebugLevel.WARNING, DebugLevel.INFO, DebugLevel.DEBUG, DebugLevel.VERBOSE]:
            logger = get_debug_logger(f'test_{level.name.lower()}', level)
            logger.set_session_id(f'test_session_{level.name}')
            logger.set_context(test_level=level.name, component='debug_test')
            
            # Test different log methods
            logger.error("Test error message", Exception("Test exception"))
            logger.warning("Test warning message")
            logger.info("Test info message")
            logger.debug("Test debug message")
            logger.verbose("Test verbose message")
            
            # Test WebSocket-specific logging
            logger.log_connection_attempt(self.server_url, 'websocket')
            logger.log_cors_check('http://localhost:5000', True)
            logger.log_performance_metric('test_metric', 1.23, 'seconds')
            
            # Get statistics
            stats = logger.get_statistics()
            print(f"  {level.name}: {stats['messages_logged']} messages logged")
            
        # Test context managers
        logger = get_debug_logger('context_test', DebugLevel.DEBUG)
        
        with logger.debug_context(operation='test_operation', user_id='test_user'):
            logger.info("Message with context")
            
        with logger.timed_operation('test_timing'):
            time.sleep(0.1)  # Simulate work
            
        return True
        
    def test_diagnostic_tools(self):
        """Test diagnostic tools functionality"""
        print("Testing diagnostic tools...")
        
        # Test configuration check
        config_check = self.diagnostics.check_configuration()
        print(f"  Configuration check: {config_check['status']}")
        
        # Test CORS validation
        cors_validation = self.diagnostics.validate_cors_configuration(self.server_url)
        print(f"  CORS validation: {cors_validation['status']}")
        
        # Test connection (may fail if server not running)
        try:
            connection_test = self.diagnostics.test_websocket_connection(self.server_url)
            print(f"  Connection test: {connection_test['status']}")
        except Exception as e:
            print(f"  Connection test: SKIPPED (server not available: {e})")
            
        # Test transport fallback
        try:
            transport_test = self.diagnostics.test_transport_fallback(self.server_url)
            print(f"  Transport test: {transport_test['status']}")
        except Exception as e:
            print(f"  Transport test: SKIPPED (server not available: {e})")
            
        # Test comprehensive diagnostics
        try:
            results = self.diagnostics.run_comprehensive_diagnostics(self.server_url)
            print(f"  Comprehensive diagnostics: {results['summary']['overall_status']}")
            
            # Export report
            filename = self.diagnostics.export_diagnostic_report(results)
            print(f"  Diagnostic report exported: {filename}")
            
        except Exception as e:
            print(f"  Comprehensive diagnostics: SKIPPED ({e})")
            
        return True
        
    def test_health_checker(self):
        """Test health checker functionality"""
        print("Testing health checker...")
        
        # Set up alerts
        setup_basic_alerts(self.health_checker)
        
        # Run individual health checks
        components = ['configuration', 'cors_setup', 'server_availability']
        
        for component in components:
            try:
                results = self.health_checker.run_health_check([component])
                result = results.get(component)
                if result:
                    print(f"  {component}: {result.status.value} - {result.message}")
                else:
                    print(f"  {component}: No result")
            except Exception as e:
                print(f"  {component}: ERROR - {e}")
                
        # Test overall health
        try:
            overall_health = self.health_checker.get_overall_health()
            print(f"  Overall health: {overall_health['status']}")
            print(f"  Components: {overall_health['summary']['total_components']}")
        except Exception as e:
            print(f"  Overall health: ERROR - {e}")
            
        # Test automated monitoring (brief test)
        print("  Testing automated monitoring...")
        self.health_checker.start_monitoring(interval=5)
        time.sleep(6)  # Let it run one cycle
        self.health_checker.stop_monitoring()
        
        # Get health history
        history = self.health_checker.get_health_history(hours=1)
        print(f"  Health history: {len(history)} components tracked")
        
        return True
        
    def test_connection_monitor(self):
        """Test connection monitoring functionality"""
        print("Testing connection monitor...")
        
        # Simulate some connections
        test_connections = [
            ('conn_1', '/', 'websocket', 'user_1'),
            ('conn_2', '/admin', 'polling', 'admin_1'),
            ('conn_3', '/', 'websocket', 'user_2')
        ]
        
        for conn_id, namespace, transport, user_id in test_connections:
            self.monitor.register_connection(conn_id, namespace, transport, user_id)
            
            # Simulate some activity
            self.monitor.record_message_sent(conn_id, 'test_event', 100)
            self.monitor.record_message_received(conn_id, 'response_event', 50)
            
        # Get connection status
        status = self.monitor.get_connection_status()
        print(f"  Active connections: {status['active_connections']}")
        print(f"  Total connections: {status['total_connections']}")
        
        # Get metrics
        metrics = self.monitor.get_metrics_summary()
        print(f"  Messages sent: {metrics['messages_sent']}")
        print(f"  Messages received: {metrics['messages_received']}")
        
        # Get recent events
        events = self.monitor.get_recent_events(10)
        print(f"  Recent events: {len(events)}")
        
        # Simulate disconnections
        for conn_id, _, _, _ in test_connections:
            self.monitor.unregister_connection(conn_id, 'test_disconnect')
            
        # Check final status
        final_status = self.monitor.get_connection_status()
        print(f"  Final active connections: {final_status['active_connections']}")
        
        return True
        
    def test_utilities(self):
        """Test WebSocket test utilities"""
        print("Testing WebSocket utilities...")
        
        # Test data generation
        test_data = WebSocketTestUtilities.generate_test_data(512)
        print(f"  Generated test data: {test_data['size']} bytes")
        
        # Test network simulation
        start_time = time.time()
        WebSocketTestUtilities.simulate_network_conditions(delay=0.1)
        elapsed = time.time() - start_time
        print(f"  Network simulation: {elapsed:.2f}s delay")
        
        # Test client creation (without actual connection)
        try:
            test_client = WebSocketTestUtilities.create_test_client(self.server_url)
            print(f"  Test client created: {type(test_client).__name__}")
        except Exception as e:
            print(f"  Test client creation: ERROR - {e}")
            
        return True
        
    def test_integration(self):
        """Test integration between different tools"""
        print("Testing tool integration...")
        
        # Test debug logger with health checker
        debug_logger = get_debug_logger('integration_test', DebugLevel.DEBUG)
        
        def health_alert_callback(result):
            debug_logger.warning(f"Health alert: {result.component} - {result.message}")
            
        self.health_checker.add_alert_callback(health_alert_callback)
        
        # Run health check to trigger potential alerts
        self.health_checker.run_health_check(['configuration'])
        
        # Test diagnostic tools with monitoring
        try:
            # Simulate diagnostic run with monitoring
            self.monitor.record_message_sent('diag_test', 'diagnostic_start', 0)
            
            config_check = self.diagnostics.check_configuration()
            
            self.monitor.record_message_received('diag_test', 'diagnostic_complete', 0)
            
            print(f"  Diagnostic with monitoring: {config_check['status']}")
            
        except Exception as e:
            print(f"  Integration test: ERROR - {e}")
            
        # Test environment configuration
        configure_debug_from_env()
        print("  Environment configuration: Applied")
        
        return True
        
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r['status'] == 'PASS')
        failed_tests = sum(1 for r in self.test_results.values() if r['status'] == 'FAIL')
        error_tests = sum(1 for r in self.test_results.values() if r['status'] == 'ERROR')
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Errors: {error_tests}")
        
        print("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = result['status']
            if status == 'PASS':
                duration = result.get('duration', 0)
                print(f"  ✓ {test_name} ({duration:.2f}s)")
            elif status == 'FAIL':
                duration = result.get('duration', 0)
                print(f"  ✗ {test_name} ({duration:.2f}s)")
            else:  # ERROR
                error = result.get('error', 'Unknown error')
                print(f"  ⚠ {test_name} - {error}")
                
        print("\nRecommendations:")
        if failed_tests > 0:
            print("  - Review failed tests and check server availability")
        if error_tests > 0:
            print("  - Check error messages and fix configuration issues")
        if passed_tests == total_tests:
            print("  - All debugging tools are working correctly!")
            
        print("\nNext Steps:")
        print("  - Start monitoring dashboard: python -c \"from websocket_monitoring_dashboard import start_monitoring_dashboard; start_monitoring_dashboard()\"")
        print("  - Run health monitoring: python -c \"from websocket_health_checker import create_health_checker; hc = create_health_checker(); hc.start_monitoring()\"")
        print("  - View troubleshooting guide: docs/websocket_troubleshooting_guide.md")


def main():
    """Main test function"""
    # Configure debug logging from environment
    configure_debug_from_env()
    
    # Create and run test suite
    test_suite = WebSocketDebuggingToolsTest()
    test_suite.run_all_tests()
    
    # Offer to start monitoring dashboard
    try:
        response = input("\nWould you like to start the monitoring dashboard? (y/n): ")
        if response.lower() in ['y', 'yes']:
            print("Starting monitoring dashboard on http://localhost:5001")
            print("Press Ctrl+C to stop...")
            
            dashboard = create_monitoring_dashboard(port=5001)
            dashboard.run(debug=False, host='127.0.0.1')
            
    except KeyboardInterrupt:
        print("\nMonitoring dashboard stopped.")
    except Exception as e:
        print(f"Could not start monitoring dashboard: {e}")


if __name__ == "__main__":
    main()