# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Connection Diagnostic Tools

Provides comprehensive diagnostic capabilities for WebSocket connections,
including connection testing, CORS validation, and performance monitoring.
"""

import time
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import socketio
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager


class WebSocketDiagnosticTools:
    """Comprehensive WebSocket diagnostic and testing tools"""
    
    def __init__(self, config_manager: WebSocketConfigManager, cors_manager: CORSManager):
        self.config_manager = config_manager
        self.cors_manager = cors_manager
        self.logger = logging.getLogger(__name__)
        self.test_results = []
        
    def run_comprehensive_diagnostics(self, server_url: str = None) -> Dict[str, Any]:
        """
        Run comprehensive WebSocket diagnostics
        
        Args:
            server_url: Optional server URL to test against
            
        Returns:
            Dict containing all diagnostic results
        """
        if not server_url:
            server_url = f"http://{self.config_manager.get_flask_host()}:{self.config_manager.get_flask_port()}"
            
        self.logger.info(f"Starting comprehensive WebSocket diagnostics for {server_url}")
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'server_url': server_url,
            'configuration_check': self.check_configuration(),
            'cors_validation': self.validate_cors_configuration(server_url),
            'connection_test': self.test_websocket_connection(server_url),
            'transport_test': self.test_transport_fallback(server_url),
            'authentication_test': self.test_authentication_flow(server_url),
            'performance_test': self.test_connection_performance(server_url),
            'error_handling_test': self.test_error_scenarios(server_url),
            'health_check': self.perform_health_check(server_url)
        }
        
        # Generate summary
        results['summary'] = self._generate_diagnostic_summary(results)
        
        self.logger.info("Comprehensive diagnostics completed")
        return results
        
    def check_configuration(self) -> Dict[str, Any]:
        """Check WebSocket configuration validity"""
        self.logger.info("Checking WebSocket configuration")
        
        config_check = {
            'status': 'pass',
            'issues': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            # Check basic configuration
            config_check['details']['flask_host'] = self.config_manager.get_flask_host()
            config_check['details']['flask_port'] = self.config_manager.get_flask_port()
            config_check['details']['cors_origins'] = self.cors_manager.get_allowed_origins()
            config_check['details']['socketio_config'] = self.config_manager.get_socketio_config()
            
            # Validate configuration
            if not self.config_manager.validate_configuration():
                config_check['status'] = 'fail'
                config_check['issues'].append('Configuration validation failed')
                
            # Check for common issues
            origins = self.cors_manager.get_allowed_origins()
            if not origins:
                config_check['status'] = 'fail'
                config_check['issues'].append('No CORS origins configured')
            elif len(origins) == 1 and origins[0] == '*':
                config_check['warnings'].append('Wildcard CORS origin detected - not recommended for production')
                
        except Exception as e:
            config_check['status'] = 'error'
            config_check['issues'].append(f'Configuration check failed: {str(e)}')
            
        return config_check
        
    def validate_cors_configuration(self, server_url: str) -> Dict[str, Any]:
        """Validate CORS configuration against server"""
        self.logger.info(f"Validating CORS configuration for {server_url}")
        
        cors_validation = {
            'status': 'pass',
            'issues': [],
            'warnings': [],
            'tests': {}
        }
        
        try:
            # Test preflight request
            cors_validation['tests']['preflight'] = self._test_cors_preflight(server_url)
            
            # Test origin validation
            cors_validation['tests']['origin_validation'] = self._test_origin_validation(server_url)
            
            # Test headers
            cors_validation['tests']['headers'] = self._test_cors_headers(server_url)
            
            # Determine overall status
            failed_tests = [test for test in cors_validation['tests'].values() if test.get('status') == 'fail']
            if failed_tests:
                cors_validation['status'] = 'fail'
                cors_validation['issues'].extend([test.get('error', 'Unknown error') for test in failed_tests])
                
        except Exception as e:
            cors_validation['status'] = 'error'
            cors_validation['issues'].append(f'CORS validation failed: {str(e)}')
            
        return cors_validation
        
    def test_websocket_connection(self, server_url: str) -> Dict[str, Any]:
        """Test basic WebSocket connection functionality"""
        self.logger.info(f"Testing WebSocket connection to {server_url}")
        
        connection_test = {
            'status': 'pass',
            'issues': [],
            'details': {},
            'timing': {}
        }
        
        try:
            start_time = time.time()
            
            # Create SocketIO client
            sio = socketio.Client(logger=False, engineio_logger=False)
            
            connection_established = False
            connection_error = None
            
            @sio.event
            def connect():
                nonlocal connection_established
                connection_established = True
                
            @sio.event
            def connect_error(data):
                nonlocal connection_error
                connection_error = data
                
            # Attempt connection
            try:
                sio.connect(server_url, wait_timeout=10)
                connection_test['timing']['connect_time'] = time.time() - start_time
                
                if connection_established:
                    connection_test['details']['connection'] = 'successful'
                    
                    # Test basic communication
                    test_message = {'test': 'diagnostic_message', 'timestamp': datetime.utcnow().isoformat()}
                    sio.emit('test_message', test_message)
                    
                    connection_test['details']['message_sent'] = True
                    
                else:
                    connection_test['status'] = 'fail'
                    connection_test['issues'].append('Connection not established')
                    
            except Exception as e:
                connection_test['status'] = 'fail'
                connection_test['issues'].append(f'Connection failed: {str(e)}')
                if connection_error:
                    connection_test['issues'].append(f'Connection error: {connection_error}')
                    
            finally:
                if sio.connected:
                    sio.disconnect()
                    
        except Exception as e:
            connection_test['status'] = 'error'
            connection_test['issues'].append(f'Connection test failed: {str(e)}')
            
        return connection_test
        
    def test_transport_fallback(self, server_url: str) -> Dict[str, Any]:
        """Test transport fallback mechanisms"""
        self.logger.info(f"Testing transport fallback for {server_url}")
        
        transport_test = {
            'status': 'pass',
            'issues': [],
            'transports_tested': {},
            'fallback_working': False
        }
        
        transports_to_test = [
            ['websocket'],
            ['polling'],
            ['websocket', 'polling']
        ]
        
        for transport_config in transports_to_test:
            transport_name = '+'.join(transport_config)
            self.logger.info(f"Testing transport: {transport_name}")
            
            try:
                sio = socketio.Client(logger=False, engineio_logger=False)
                
                connection_successful = False
                
                @sio.event
                def connect():
                    nonlocal connection_successful
                    connection_successful = True
                    
                start_time = time.time()
                sio.connect(server_url, transports=transport_config, wait_timeout=5)
                connect_time = time.time() - start_time
                
                transport_test['transports_tested'][transport_name] = {
                    'status': 'success' if connection_successful else 'failed',
                    'connect_time': connect_time,
                    'actual_transport': sio.transport() if hasattr(sio, 'transport') else 'unknown'
                }
                
                if connection_successful:
                    transport_test['fallback_working'] = True
                    
                sio.disconnect()
                
            except Exception as e:
                transport_test['transports_tested'][transport_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                
        if not transport_test['fallback_working']:
            transport_test['status'] = 'fail'
            transport_test['issues'].append('No transport methods working')
            
        return transport_test
        
    def test_authentication_flow(self, server_url: str) -> Dict[str, Any]:
        """Test authentication flow for WebSocket connections"""
        self.logger.info(f"Testing authentication flow for {server_url}")
        
        auth_test = {
            'status': 'pass',
            'issues': [],
            'tests': {}
        }
        
        try:
            # Test unauthenticated connection
            auth_test['tests']['unauthenticated'] = self._test_unauthenticated_connection(server_url)
            
            # Test authenticated connection (if possible)
            auth_test['tests']['authenticated'] = self._test_authenticated_connection(server_url)
            
            # Test admin namespace access
            auth_test['tests']['admin_access'] = self._test_admin_namespace_access(server_url)
            
        except Exception as e:
            auth_test['status'] = 'error'
            auth_test['issues'].append(f'Authentication test failed: {str(e)}')
            
        return auth_test
        
    def test_connection_performance(self, server_url: str) -> Dict[str, Any]:
        """Test WebSocket connection performance"""
        self.logger.info(f"Testing connection performance for {server_url}")
        
        performance_test = {
            'status': 'pass',
            'issues': [],
            'metrics': {}
        }
        
        try:
            # Test connection time
            connection_times = []
            for i in range(5):
                start_time = time.time()
                sio = socketio.Client(logger=False, engineio_logger=False)
                
                try:
                    sio.connect(server_url, wait_timeout=5)
                    connection_time = time.time() - start_time
                    connection_times.append(connection_time)
                    sio.disconnect()
                except Exception as e:
                    self.logger.warning(f"Performance test connection {i+1} failed: {e}")
                    
            if connection_times:
                performance_test['metrics']['avg_connection_time'] = sum(connection_times) / len(connection_times)
                performance_test['metrics']['min_connection_time'] = min(connection_times)
                performance_test['metrics']['max_connection_time'] = max(connection_times)
                
                # Check if performance is acceptable
                avg_time = performance_test['metrics']['avg_connection_time']
                if avg_time > 5.0:
                    performance_test['status'] = 'warning'
                    performance_test['issues'].append(f'Slow average connection time: {avg_time:.2f}s')
                elif avg_time > 10.0:
                    performance_test['status'] = 'fail'
                    performance_test['issues'].append(f'Very slow connection time: {avg_time:.2f}s')
            else:
                performance_test['status'] = 'fail'
                performance_test['issues'].append('No successful connections for performance testing')
                
        except Exception as e:
            performance_test['status'] = 'error'
            performance_test['issues'].append(f'Performance test failed: {str(e)}')
            
        return performance_test
        
    def test_error_scenarios(self, server_url: str) -> Dict[str, Any]:
        """Test error handling scenarios"""
        self.logger.info(f"Testing error scenarios for {server_url}")
        
        error_test = {
            'status': 'pass',
            'issues': [],
            'scenarios': {}
        }
        
        try:
            # Test invalid server URL
            error_test['scenarios']['invalid_url'] = self._test_invalid_server_connection()
            
            # Test connection timeout
            error_test['scenarios']['timeout'] = self._test_connection_timeout(server_url)
            
            # Test invalid namespace
            error_test['scenarios']['invalid_namespace'] = self._test_invalid_namespace(server_url)
            
        except Exception as e:
            error_test['status'] = 'error'
            error_test['issues'].append(f'Error scenario testing failed: {str(e)}')
            
        return error_test
        
    def perform_health_check(self, server_url: str) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        self.logger.info(f"Performing health check for {server_url}")
        
        health_check = {
            'status': 'healthy',
            'issues': [],
            'checks': {}
        }
        
        try:
            # Check server availability
            health_check['checks']['server_available'] = self._check_server_availability(server_url)
            
            # Check WebSocket endpoint
            health_check['checks']['websocket_endpoint'] = self._check_websocket_endpoint(server_url)
            
            # Check CORS configuration
            health_check['checks']['cors_config'] = self._check_cors_health(server_url)
            
            # Determine overall health
            failed_checks = [check for check in health_check['checks'].values() if check.get('status') == 'fail']
            if failed_checks:
                health_check['status'] = 'unhealthy'
                health_check['issues'].extend([check.get('error', 'Unknown error') for check in failed_checks])
                
        except Exception as e:
            health_check['status'] = 'error'
            health_check['issues'].append(f'Health check failed: {str(e)}')
            
        return health_check
        
    def _test_cors_preflight(self, server_url: str) -> Dict[str, Any]:
        """Test CORS preflight request"""
        try:
            response = requests.options(
                f"{server_url}/socket.io/",
                headers={
                    'Origin': self.cors_manager.get_allowed_origins()[0] if self.cors_manager.get_allowed_origins() else 'http://localhost:5000',
                    'Access-Control-Request-Method': 'GET',
                    'Access-Control-Request-Headers': 'Content-Type'
                },
                timeout=5
            )
            
            return {
                'status': 'pass' if response.status_code == 200 else 'fail',
                'status_code': response.status_code,
                'headers': dict(response.headers)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def _test_origin_validation(self, server_url: str) -> Dict[str, Any]:
        """Test origin validation"""
        allowed_origins = self.cors_manager.get_allowed_origins()
        
        if not allowed_origins:
            return {
                'status': 'fail',
                'error': 'No allowed origins configured'
            }
            
        # Test with allowed origin
        try:
            response = requests.get(
                f"{server_url}/socket.io/",
                headers={'Origin': allowed_origins[0]},
                timeout=5
            )
            
            return {
                'status': 'pass',
                'allowed_origin_test': response.status_code,
                'tested_origin': allowed_origins[0]
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def _test_cors_headers(self, server_url: str) -> Dict[str, Any]:
        """Test CORS headers"""
        try:
            response = requests.get(f"{server_url}/socket.io/", timeout=5)
            headers = dict(response.headers)
            
            required_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods',
                'Access-Control-Allow-Headers'
            ]
            
            missing_headers = [header for header in required_headers if header not in headers]
            
            return {
                'status': 'pass' if not missing_headers else 'fail',
                'headers_present': [header for header in required_headers if header in headers],
                'missing_headers': missing_headers,
                'all_headers': headers
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def _test_unauthenticated_connection(self, server_url: str) -> Dict[str, Any]:
        """Test unauthenticated connection"""
        try:
            sio = socketio.Client(logger=False, engineio_logger=False)
            
            connection_result = {'status': 'unknown'}
            
            @sio.event
            def connect():
                connection_result['status'] = 'connected'
                
            @sio.event
            def connect_error(data):
                connection_result['status'] = 'rejected'
                connection_result['error'] = data
                
            sio.connect(server_url, wait_timeout=5)
            sio.disconnect()
            
            return connection_result
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def _test_authenticated_connection(self, server_url: str) -> Dict[str, Any]:
        """Test authenticated connection (mock)"""
        # This would require actual authentication implementation
        return {
            'status': 'skipped',
            'reason': 'Authentication testing requires valid credentials'
        }
        
    def _test_admin_namespace_access(self, server_url: str) -> Dict[str, Any]:
        """Test admin namespace access"""
        try:
            sio = socketio.Client(logger=False, engineio_logger=False)
            
            access_result = {'status': 'unknown'}
            
            @sio.event
            def connect():
                access_result['status'] = 'connected'
                
            @sio.event
            def connect_error(data):
                access_result['status'] = 'rejected'
                access_result['error'] = data
                
            # Try to connect to admin namespace
            sio.connect(f"{server_url}/admin", wait_timeout=5)
            sio.disconnect()
            
            return access_result
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def _test_invalid_server_connection(self) -> Dict[str, Any]:
        """Test connection to invalid server"""
        try:
            sio = socketio.Client(logger=False, engineio_logger=False)
            sio.connect("http://invalid-server:9999", wait_timeout=2)
            
            return {
                'status': 'unexpected_success',
                'warning': 'Connection to invalid server succeeded unexpectedly'
            }
        except Exception as e:
            return {
                'status': 'expected_failure',
                'error': str(e)
            }
            
    def _test_connection_timeout(self, server_url: str) -> Dict[str, Any]:
        """Test connection timeout handling"""
        try:
            sio = socketio.Client(logger=False, engineio_logger=False)
            start_time = time.time()
            
            try:
                sio.connect(server_url, wait_timeout=1)  # Very short timeout
                return {
                    'status': 'connected',
                    'time': time.time() - start_time
                }
            except Exception as e:
                return {
                    'status': 'timeout_handled',
                    'time': time.time() - start_time,
                    'error': str(e)
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def _test_invalid_namespace(self, server_url: str) -> Dict[str, Any]:
        """Test connection to invalid namespace"""
        try:
            sio = socketio.Client(logger=False, engineio_logger=False)
            sio.connect(f"{server_url}/invalid_namespace", wait_timeout=5)
            
            return {
                'status': 'unexpected_success',
                'warning': 'Connection to invalid namespace succeeded'
            }
        except Exception as e:
            return {
                'status': 'expected_failure',
                'error': str(e)
            }
            
    def _check_server_availability(self, server_url: str) -> Dict[str, Any]:
        """Check if server is available"""
        try:
            response = requests.get(server_url, timeout=5)
            return {
                'status': 'pass',
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                'status': 'fail',
                'error': str(e)
            }
            
    def _check_websocket_endpoint(self, server_url: str) -> Dict[str, Any]:
        """Check WebSocket endpoint availability"""
        try:
            response = requests.get(f"{server_url}/socket.io/", timeout=5)
            return {
                'status': 'pass' if response.status_code == 200 else 'fail',
                'status_code': response.status_code
            }
        except Exception as e:
            return {
                'status': 'fail',
                'error': str(e)
            }
            
    def _check_cors_health(self, server_url: str) -> Dict[str, Any]:
        """Check CORS configuration health"""
        try:
            origins = self.cors_manager.get_allowed_origins()
            if not origins:
                return {
                    'status': 'fail',
                    'error': 'No CORS origins configured'
                }
                
            # Test with first allowed origin
            response = requests.get(
                f"{server_url}/socket.io/",
                headers={'Origin': origins[0]},
                timeout=5
            )
            
            return {
                'status': 'pass',
                'tested_origin': origins[0],
                'status_code': response.status_code
            }
        except Exception as e:
            return {
                'status': 'fail',
                'error': str(e)
            }
            
    def _generate_diagnostic_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate diagnostic summary"""
        summary = {
            'overall_status': 'healthy',
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'warnings': 0,
            'critical_issues': [],
            'recommendations': []
        }
        
        # Count test results
        for section_name, section_data in results.items():
            if section_name in ['timestamp', 'server_url', 'summary']:
                continue
                
            if isinstance(section_data, dict):
                summary['total_tests'] += 1
                
                status = section_data.get('status', 'unknown')
                if status in ['pass', 'healthy', 'success']:
                    summary['passed_tests'] += 1
                elif status in ['fail', 'unhealthy', 'error']:
                    summary['failed_tests'] += 1
                    summary['critical_issues'].extend(section_data.get('issues', []))
                elif status == 'warning':
                    summary['warnings'] += 1
                    
        # Determine overall status
        if summary['failed_tests'] > 0:
            summary['overall_status'] = 'unhealthy'
        elif summary['warnings'] > 0:
            summary['overall_status'] = 'warning'
            
        # Generate recommendations
        if summary['failed_tests'] > 0:
            summary['recommendations'].append('Review failed tests and resolve critical issues')
        if summary['warnings'] > 0:
            summary['recommendations'].append('Address warning conditions for optimal performance')
        if summary['overall_status'] == 'healthy':
            summary['recommendations'].append('WebSocket system is functioning properly')
            
        return summary
        
    def export_diagnostic_report(self, results: Dict[str, Any], filename: str = None) -> str:
        """Export diagnostic results to JSON file"""
        if not filename:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"websocket_diagnostic_report_{timestamp}.json"
            
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        self.logger.info(f"Diagnostic report exported to {filename}")
        return filename


class WebSocketTestUtilities:
    """Utility functions for WebSocket testing"""
    
    @staticmethod
    def create_test_client(server_url: str, namespace: str = None, **kwargs) -> socketio.Client:
        """Create a test SocketIO client with standard configuration"""
        sio = socketio.Client(logger=False, engineio_logger=False, **kwargs)
        
        if namespace:
            server_url = f"{server_url}/{namespace}"
            
        return sio
        
    @staticmethod
    def measure_connection_time(sio: socketio.Client, server_url: str, timeout: int = 10) -> float:
        """Measure connection establishment time"""
        start_time = time.time()
        sio.connect(server_url, wait_timeout=timeout)
        return time.time() - start_time
        
    @staticmethod
    def test_message_roundtrip(sio: socketio.Client, message: Dict[str, Any], timeout: int = 5) -> Tuple[bool, float]:
        """Test message roundtrip time"""
        response_received = False
        response_time = None
        
        @sio.event
        def test_response(data):
            nonlocal response_received, response_time
            response_received = True
            response_time = time.time()
            
        start_time = time.time()
        sio.emit('test_message', message)
        
        # Wait for response
        elapsed = 0
        while not response_received and elapsed < timeout:
            time.sleep(0.1)
            elapsed = time.time() - start_time
            
        if response_received:
            return True, response_time - start_time
        else:
            return False, elapsed
            
    @staticmethod
    def simulate_network_conditions(delay: float = 0, packet_loss: float = 0):
        """Simulate network conditions for testing (placeholder)"""
        # This would require network simulation tools
        # For now, just add artificial delay
        if delay > 0:
            time.sleep(delay)
            
    @staticmethod
    def generate_test_data(size: int = 1024) -> Dict[str, Any]:
        """Generate test data of specified size"""
        import string
        import random
        
        data_string = ''.join(random.choices(string.ascii_letters + string.digits, k=size))
        
        return {
            'test_data': data_string,
            'size': size,
            'timestamp': datetime.utcnow().isoformat()
        }