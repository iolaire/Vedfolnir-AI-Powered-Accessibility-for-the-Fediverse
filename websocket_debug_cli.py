#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Debug CLI

Command-line interface for WebSocket debugging tools, diagnostics,
health checks, and monitoring capabilities.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from websocket_diagnostic_tools import WebSocketDiagnosticTools
from websocket_debug_logger import get_debug_logger, set_debug_level, DebugLevel
from websocket_monitoring_dashboard import start_monitoring_dashboard
from websocket_health_checker import create_health_checker, setup_basic_alerts
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager


def setup_tools():
    """Set up WebSocket debugging tools"""
    config_manager = WebSocketConfigManager()
    cors_manager = CORSManager(config_manager)
    diagnostics = WebSocketDiagnosticTools(config_manager, cors_manager)
    health_checker = create_health_checker(config_manager, cors_manager)
    
    return config_manager, cors_manager, diagnostics, health_checker


def cmd_diagnose(args):
    """Run WebSocket diagnostics"""
    config_manager, cors_manager, diagnostics, health_checker = setup_tools()
    
    server_url = args.url or f"http://{config_manager.get_flask_host()}:{config_manager.get_flask_port()}"
    
    print(f"Running WebSocket diagnostics for {server_url}...")
    print("=" * 60)
    
    try:
        if args.component:
            # Run specific component diagnostics
            if args.component == 'config':
                result = diagnostics.check_configuration()
            elif args.component == 'cors':
                result = diagnostics.validate_cors_configuration(server_url)
            elif args.component == 'connection':
                result = diagnostics.test_websocket_connection(server_url)
            elif args.component == 'transport':
                result = diagnostics.test_transport_fallback(server_url)
            elif args.component == 'auth':
                result = diagnostics.test_authentication_flow(server_url)
            elif args.component == 'performance':
                result = diagnostics.test_connection_performance(server_url)
            else:
                print(f"Unknown component: {args.component}")
                return
                
            print(f"Component: {args.component}")
            print(f"Status: {result['status']}")
            print(f"Details: {json.dumps(result, indent=2, default=str)}")
            
        else:
            # Run comprehensive diagnostics
            results = diagnostics.run_comprehensive_diagnostics(server_url)
            
            # Print summary
            summary = results['summary']
            print(f"Overall Status: {summary['overall_status']}")
            print(f"Tests: {summary['passed_tests']}/{summary['total_tests']} passed")
            
            if summary['failed_tests'] > 0:
                print(f"Failed Tests: {summary['failed_tests']}")
                print("Critical Issues:")
                for issue in summary['critical_issues']:
                    print(f"  - {issue}")
                    
            if summary['warnings'] > 0:
                print(f"Warnings: {summary['warnings']}")
                
            print("\nRecommendations:")
            for rec in summary['recommendations']:
                print(f"  - {rec}")
                
            # Export report if requested
            if args.export:
                filename = diagnostics.export_diagnostic_report(results, args.export)
                print(f"\nDiagnostic report exported to: {filename}")
                
    except Exception as e:
        print(f"Diagnostic failed: {e}")
        sys.exit(1)


def cmd_health(args):
    """Run health checks"""
    config_manager, cors_manager, diagnostics, health_checker = setup_tools()
    
    print("Running WebSocket health checks...")
    print("=" * 60)
    
    try:
        if args.monitor:
            # Start continuous monitoring
            setup_basic_alerts(health_checker)
            
            print(f"Starting health monitoring (interval: {args.interval}s)")
            print("Press Ctrl+C to stop...")
            
            health_checker.start_monitoring(args.interval)
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping health monitoring...")
                health_checker.stop_monitoring()
                
        else:
            # Run one-time health check
            if args.component:
                results = health_checker.run_health_check([args.component])
                result = results.get(args.component)
                
                if result:
                    print(f"Component: {args.component}")
                    print(f"Status: {result.status.value}")
                    print(f"Message: {result.message}")
                    print(f"Response Time: {result.response_time:.3f}s")
                    
                    if result.details:
                        print("Details:")
                        print(json.dumps(result.details, indent=2, default=str))
                        
                    if result.error:
                        print(f"Error: {result.error}")
                else:
                    print(f"No results for component: {args.component}")
                    
            else:
                # Run all health checks
                overall_health = health_checker.get_overall_health()
                
                print(f"Overall Health: {overall_health['status']}")
                print(f"Message: {overall_health['message']}")
                
                summary = overall_health['summary']
                print(f"\nSummary:")
                print(f"  Total Components: {summary['total_components']}")
                print(f"  Healthy: {summary['healthy_components']}")
                print(f"  Warning: {summary['warning_components']}")
                print(f"  Critical: {summary['critical_components']}")
                print(f"  Average Response Time: {summary['avg_response_time']:.3f}s")
                
                if args.verbose:
                    print("\nComponent Details:")
                    for name, component in overall_health['components'].items():
                        status_icon = {
                            'healthy': '✓',
                            'warning': '⚠',
                            'critical': '✗',
                            'unknown': '?'
                        }.get(component['status'], '?')
                        
                        print(f"  {status_icon} {name}: {component['message']}")
                        
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)


def cmd_monitor(args):
    """Start monitoring dashboard"""
    print(f"Starting WebSocket monitoring dashboard on port {args.port}...")
    print(f"Access at: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop...")
    
    try:
        start_monitoring_dashboard(port=args.port, host=args.host)
    except KeyboardInterrupt:
        print("\nMonitoring dashboard stopped.")
    except Exception as e:
        print(f"Failed to start monitoring dashboard: {e}")
        sys.exit(1)


def cmd_config(args):
    """Show WebSocket configuration"""
    config_manager, cors_manager, diagnostics, health_checker = setup_tools()
    
    print("WebSocket Configuration")
    print("=" * 60)
    
    try:
        # Basic configuration
        print("Basic Configuration:")
        print(f"  Flask Host: {config_manager.get_flask_host()}")
        print(f"  Flask Port: {config_manager.get_flask_port()}")
        
        # CORS configuration
        print("\nCORS Configuration:")
        origins = cors_manager.get_allowed_origins()
        if origins:
            for i, origin in enumerate(origins, 1):
                print(f"  {i}. {origin}")
        else:
            print("  No CORS origins configured")
            
        # SocketIO configuration
        print("\nSocketIO Configuration:")
        socketio_config = config_manager.get_socketio_config()
        for key, value in socketio_config.items():
            print(f"  {key}: {value}")
            
        # Validation
        print("\nConfiguration Validation:")
        is_valid = config_manager.validate_configuration()
        print(f"  Status: {'✓ Valid' if is_valid else '✗ Invalid'}")
        
        if args.export:
            config_data = {
                'flask_host': config_manager.get_flask_host(),
                'flask_port': config_manager.get_flask_port(),
                'cors_origins': origins,
                'socketio_config': socketio_config,
                'validation_status': is_valid,
                'export_timestamp': datetime.utcnow().isoformat()
            }
            
            with open(args.export, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
                
            print(f"\nConfiguration exported to: {args.export}")
            
    except Exception as e:
        print(f"Configuration check failed: {e}")
        sys.exit(1)


def cmd_test(args):
    """Run connection tests"""
    config_manager, cors_manager, diagnostics, health_checker = setup_tools()
    
    server_url = args.url or f"http://{config_manager.get_flask_host()}:{config_manager.get_flask_port()}"
    
    print(f"Testing WebSocket connection to {server_url}...")
    print("=" * 60)
    
    try:
        if args.type == 'connection':
            result = diagnostics.test_websocket_connection(server_url)
        elif args.type == 'transport':
            result = diagnostics.test_transport_fallback(server_url)
        elif args.type == 'performance':
            result = diagnostics.test_connection_performance(server_url)
        elif args.type == 'auth':
            result = diagnostics.test_authentication_flow(server_url)
        else:
            print(f"Unknown test type: {args.type}")
            return
            
        print(f"Test Type: {args.type}")
        print(f"Status: {result['status']}")
        
        if 'timing' in result:
            for key, value in result['timing'].items():
                print(f"{key}: {value:.3f}s")
                
        if 'details' in result:
            print("Details:")
            print(json.dumps(result['details'], indent=2, default=str))
            
        if result['status'] != 'pass' and 'issues' in result:
            print("Issues:")
            for issue in result['issues']:
                print(f"  - {issue}")
                
    except Exception as e:
        print(f"Connection test failed: {e}")
        sys.exit(1)


def cmd_debug(args):
    """Configure debug logging"""
    level_map = {
        'silent': DebugLevel.SILENT,
        'error': DebugLevel.ERROR,
        'warning': DebugLevel.WARNING,
        'info': DebugLevel.INFO,
        'debug': DebugLevel.DEBUG,
        'verbose': DebugLevel.VERBOSE
    }
    
    if args.level:
        level = level_map.get(args.level.lower())
        if level:
            set_debug_level(level)
            print(f"Debug level set to: {level.name}")
        else:
            print(f"Invalid debug level: {args.level}")
            print(f"Available levels: {', '.join(level_map.keys())}")
            return
            
    # Create test logger
    logger = get_debug_logger('cli_test', level or DebugLevel.INFO)
    logger.set_session_id('cli_debug_session')
    
    print("Testing debug logging...")
    logger.error("Test error message")
    logger.warning("Test warning message")
    logger.info("Test info message")
    logger.debug("Test debug message")
    logger.verbose("Test verbose message")
    
    # Show statistics
    stats = logger.get_statistics()
    print(f"\nLogging Statistics:")
    print(f"  Messages logged: {stats['messages_logged']}")
    print(f"  Errors logged: {stats['errors_logged']}")
    print(f"  Warnings logged: {stats['warnings_logged']}")
    
    if args.export:
        filename = logger.export_debug_log(args.export)
        print(f"Debug log exported to: {filename}")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="WebSocket Debug CLI - Comprehensive debugging tools for WebSocket connections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s diagnose                    # Run comprehensive diagnostics
  %(prog)s diagnose --component cors   # Check CORS configuration only
  %(prog)s health --monitor            # Start continuous health monitoring
  %(prog)s monitor --port 5001         # Start monitoring dashboard
  %(prog)s test --type connection      # Test WebSocket connection
  %(prog)s config --export config.json # Export configuration to file
  %(prog)s debug --level verbose       # Set verbose debug logging
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Diagnose command
    diagnose_parser = subparsers.add_parser('diagnose', help='Run WebSocket diagnostics')
    diagnose_parser.add_argument('--url', help='Server URL to test (default: from config)')
    diagnose_parser.add_argument('--component', choices=['config', 'cors', 'connection', 'transport', 'auth', 'performance'],
                                help='Run diagnostics for specific component only')
    diagnose_parser.add_argument('--export', help='Export diagnostic report to file')
    diagnose_parser.set_defaults(func=cmd_diagnose)
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Run health checks')
    health_parser.add_argument('--component', help='Check specific component only')
    health_parser.add_argument('--monitor', action='store_true', help='Start continuous monitoring')
    health_parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds')
    health_parser.add_argument('--verbose', action='store_true', help='Show detailed component information')
    health_parser.set_defaults(func=cmd_health)
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Start monitoring dashboard')
    monitor_parser.add_argument('--port', type=int, default=5001, help='Dashboard port')
    monitor_parser.add_argument('--host', default='127.0.0.1', help='Dashboard host')
    monitor_parser.set_defaults(func=cmd_monitor)
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Show WebSocket configuration')
    config_parser.add_argument('--export', help='Export configuration to file')
    config_parser.set_defaults(func=cmd_config)
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run connection tests')
    test_parser.add_argument('--type', choices=['connection', 'transport', 'performance', 'auth'],
                            default='connection', help='Type of test to run')
    test_parser.add_argument('--url', help='Server URL to test (default: from config)')
    test_parser.set_defaults(func=cmd_test)
    
    # Debug command
    debug_parser = subparsers.add_parser('debug', help='Configure debug logging')
    debug_parser.add_argument('--level', choices=['silent', 'error', 'warning', 'info', 'debug', 'verbose'],
                             help='Set debug logging level')
    debug_parser.add_argument('--export', help='Export debug log to file')
    debug_parser.set_defaults(func=cmd_debug)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    # Execute command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()