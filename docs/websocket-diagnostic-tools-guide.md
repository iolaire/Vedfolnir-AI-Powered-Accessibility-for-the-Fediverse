# WebSocket Diagnostic Tools and Debugging Guide

## Overview

This guide provides comprehensive diagnostic tools and debugging procedures specifically for WebSocket connection issues in the unified notification system. It includes automated diagnostic scripts, manual testing procedures, and advanced debugging techniques.

## Automated Diagnostic Tools

### 1. WebSocket Connection Validator

Create: `tests/scripts/websocket_connection_validator.py`

```python
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Connection Validator
Comprehensive testing tool for WebSocket connectivity and functionality
"""

import socketio
import requests
import time
import sys
import json
import threading
from urllib.parse import urljoin

class WebSocketValidator:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
    def log_result(self, test_name, success, message="", details=None):
        """Log test result"""
        self.results['tests_run'] += 1
        
        if success:
            self.results['tests_passed'] += 1
            print(f"✅ {test_name}: {message}")
        else:
            self.results['tests_failed'] += 1
            self.results['errors'].append(f"{test_name}: {message}")
            print(f"❌ {test_name}: {message}")
        
        if details:
            self.results['details'][test_name] = details
    
    def test_basic_connectivity(self):
        """Test basic HTTP connectivity to the server"""
        try:
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                self.log_result("Basic Connectivity", True, "Server is reachable")
                return True
            else:
                self.log_result("Basic Connectivity", False, 
                              f"Server returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_result("Basic Connectivity", False, f"Connection failed: {e}")
            return False
    
    def test_socketio_endpoint(self):
        """Test Socket.IO endpoint availability"""
        try:
            response = requests.get(urljoin(self.base_url, "/socket.io/"), timeout=10)
            if response.status_code in [200, 400]:  # 400 is expected for GET request
                self.log_result("Socket.IO Endpoint", True, "Endpoint is available")
                return True
            else:
                self.log_result("Socket.IO Endpoint", False, 
                              f"Unexpected status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_result("Socket.IO Endpoint", False, f"Endpoint test failed: {e}")
            return False
    
    def test_websocket_connection(self):
        """Test WebSocket connection establishment"""
        connection_successful = threading.Event()
        connection_error = None
        
        sio = socketio.Client(logger=False, engineio_logger=False)
        
        @sio.event
        def connect():
            connection_successful.set()
        
        @sio.event
        def connect_error(data):
            nonlocal connection_error
            connection_error = data
            connection_successful.set()
        
        try:
            sio.connect(self.base_url, wait_timeout=15)
            
            if connection_successful.wait(timeout=15):
                if sio.connected:
                    self.log_result("WebSocket Connection", True, 
                                  f"Connected successfully (ID: {sio.sid})")
                    sio.disconnect()
                    return True
                else:
                    self.log_result("WebSocket Connection", False, 
                                  f"Connection failed: {connection_error}")
                    return False
            else:
                self.log_result("WebSocket Connection", False, "Connection timeout")
                return False
                
        except Exception as e:
            self.log_result("WebSocket Connection", False, f"Connection error: {e}")
            return False
    
    def test_namespace_connections(self):
        """Test connections to different namespaces"""
        namespaces = ['/user', '/admin', '/system']
        results = {}
        
        for namespace in namespaces:
            try:
                sio = socketio.Client(logger=False, engineio_logger=False)
                
                connection_successful = threading.Event()
                
                @sio.event
                def connect():
                    connection_successful.set()
                
                sio.connect(self.base_url, namespaces=[namespace], wait_timeout=10)
                
                if connection_successful.wait(timeout=10) and sio.connected:
                    results[namespace] = True
                    self.log_result(f"Namespace {namespace}", True, "Connected successfully")
                    sio.disconnect()
                else:
                    results[namespace] = False
                    self.log_result(f"Namespace {namespace}", False, "Connection failed")
                    
            except Exception as e:
                results[namespace] = False
                self.log_result(f"Namespace {namespace}", False, f"Error: {e}")
        
        return results
    
    def test_message_echo(self):
        """Test bidirectional message communication"""
        message_received = threading.Event()
        received_data = None
        
        sio = socketio.Client(logger=False, engineio_logger=False)
        
        @sio.event
        def connect():
            # Send test message after connection
            test_data = {'test': 'echo', 'timestamp': time.time()}
            sio.emit('test_echo', test_data)
        
        @sio.event
        def test_echo_response(data):
            nonlocal received_data
            received_data = data
            message_received.set()
        
        try:
            sio.connect(self.base_url, wait_timeout=10)
            
            if message_received.wait(timeout=10):
                self.log_result("Message Echo", True, 
                              f"Echo successful: {received_data}")
                sio.disconnect()
                return True
            else:
                self.log_result("Message Echo", False, "No echo response received")
                sio.disconnect()
                return False
                
        except Exception as e:
            self.log_result("Message Echo", False, f"Echo test failed: {e}")
            return False
    
    def test_cors_configuration(self):
        """Test CORS configuration for WebSocket"""
        try:
            # Test preflight request
            headers = {
                'Origin': 'http://127.0.0.1:5000',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = requests.options(
                urljoin(self.base_url, "/socket.io/"),
                headers=headers,
                timeout=10
            )
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }
            
            if cors_headers['Access-Control-Allow-Origin']:
                self.log_result("CORS Configuration", True, 
                              "CORS headers present", cors_headers)
                return True
            else:
                self.log_result("CORS Configuration", False, 
                              "Missing CORS headers", cors_headers)
                return False
                
        except Exception as e:
            self.log_result("CORS Configuration", False, f"CORS test failed: {e}")
            return False
    
    def test_performance_metrics(self):
        """Test WebSocket performance metrics"""
        connection_times = []
        
        for i in range(3):
            start_time = time.time()
            
            try:
                sio = socketio.Client(logger=False, engineio_logger=False)
                sio.connect(self.base_url, wait_timeout=10)
                
                if sio.connected:
                    connection_time = (time.time() - start_time) * 1000  # ms
                    connection_times.append(connection_time)
                    sio.disconnect()
                else:
                    self.log_result("Performance Test", False, 
                                  f"Connection {i+1} failed")
                    return False
                    
            except Exception as e:
                self.log_result("Performance Test", False, 
                              f"Performance test {i+1} failed: {e}")
                return False
        
        avg_time = sum(connection_times) / len(connection_times)
        
        if avg_time < 5000:  # 5 seconds
            self.log_result("Performance Test", True, 
                          f"Average connection time: {avg_time:.2f}ms")
            return True
        else:
            self.log_result("Performance Test", False, 
                          f"Slow connection time: {avg_time:.2f}ms")
            return False
    
    def run_all_tests(self):
        """Run comprehensive WebSocket validation"""
        print("🔍 Starting WebSocket Connection Validation...")
        print(f"🌐 Target URL: {self.base_url}")
        print("-" * 60)
        
        # Run tests in order
        tests = [
            self.test_basic_connectivity,
            self.test_socketio_endpoint,
            self.test_websocket_connection,
            self.test_namespace_connections,
            self.test_cors_configuration,
            self.test_performance_metrics,
            # Note: test_message_echo requires server-side echo handler
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_result(test.__name__, False, f"Test exception: {e}")
        
        # Print summary
        print("-" * 60)
        print(f"📊 Test Summary:")
        print(f"   Tests Run: {self.results['tests_run']}")
        print(f"   Passed: {self.results['tests_passed']}")
        print(f"   Failed: {self.results['tests_failed']}")
        
        if self.results['errors']:
            print(f"\n❌ Errors:")
            for error in self.results['errors']:
                print(f"   - {error}")
        
        success_rate = (self.results['tests_passed'] / self.results['tests_run']) * 100
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        return success_rate >= 80  # 80% success rate threshold

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WebSocket Connection Validator')
    parser.add_argument('--url', default='http://127.0.0.1:5000',
                       help='Base URL for testing (default: http://127.0.0.1:5000)')
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    
    args = parser.parse_args()
    
    validator = WebSocketValidator(args.url)
    success = validator.run_all_tests()
    
    if args.json:
        print(json.dumps(validator.results, indent=2))
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
```

### 2. Real-Time Connection Monitor

Create: `tests/scripts/websocket_connection_monitor.py`

```python
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Real-Time WebSocket Connection Monitor
Monitors WebSocket connections and provides live statistics
"""

import socketio
import time
import threading
import json
import signal
import sys
from datetime import datetime, timedelta

class WebSocketMonitor:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.running = False
        self.connections = {}
        self.stats = {
            'total_connections': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'disconnections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'start_time': None,
            'connection_times': [],
            'errors': []
        }
        
    def create_monitored_connection(self, connection_id):
        """Create a monitored WebSocket connection"""
        sio = socketio.Client(logger=False, engineio_logger=False)
        
        connection_info = {
            'id': connection_id,
            'client': sio,
            'connected_at': None,
            'disconnected_at': None,
            'messages_sent': 0,
            'messages_received': 0,
            'last_activity': None
        }
        
        @sio.event
        def connect():
            connection_info['connected_at'] = datetime.now()
            connection_info['last_activity'] = datetime.now()
            self.stats['successful_connections'] += 1
            print(f"🔗 Connection {connection_id} established")
        
        @sio.event
        def disconnect():
            connection_info['disconnected_at'] = datetime.now()
            self.stats['disconnections'] += 1
            print(f"🔌 Connection {connection_id} disconnected")
        
        @sio.event
        def connect_error(data):
            self.stats['failed_connections'] += 1
            self.stats['errors'].append({
                'connection_id': connection_id,
                'error': str(data),
                'timestamp': datetime.now().isoformat()
            })
            print(f"❌ Connection {connection_id} failed: {data}")
        
        @sio.event
        def notification(data):
            connection_info['messages_received'] += 1
            connection_info['last_activity'] = datetime.now()
            self.stats['messages_received'] += 1
            print(f"📨 Connection {connection_id} received notification")
        
        self.connections[connection_id] = connection_info
        return sio
    
    def start_monitoring(self, num_connections=1, duration=60):
        """Start monitoring with specified number of connections"""
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        print(f"🚀 Starting WebSocket monitoring...")
        print(f"   Connections: {num_connections}")
        print(f"   Duration: {duration} seconds")
        print(f"   Target: {self.base_url}")
        print("-" * 50)
        
        # Create connections
        for i in range(num_connections):
            try:
                connection_id = f"monitor_{i+1}"
                sio = self.create_monitored_connection(connection_id)
                
                start_time = time.time()
                sio.connect(self.base_url, wait_timeout=10)
                connection_time = (time.time() - start_time) * 1000
                
                self.stats['total_connections'] += 1
                self.stats['connection_times'].append(connection_time)
                
                time.sleep(0.1)  # Small delay between connections
                
            except Exception as e:
                self.stats['failed_connections'] += 1
                self.stats['errors'].append({
                    'connection_id': connection_id,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                print(f"❌ Failed to create connection {connection_id}: {e}")
        
        # Monitor for specified duration
        start_time = time.time()
        while self.running and (time.time() - start_time) < duration:
            self.print_live_stats()
            time.sleep(5)  # Update every 5 seconds
        
        # Cleanup connections
        self.cleanup_connections()
        self.print_final_report()
    
    def print_live_stats(self):
        """Print live statistics"""
        now = datetime.now()
        uptime = now - self.stats['start_time']
        
        active_connections = sum(1 for conn in self.connections.values() 
                               if conn['connected_at'] and not conn['disconnected_at'])
        
        print(f"\n📊 Live Stats ({now.strftime('%H:%M:%S')}) - Uptime: {uptime}")
        print(f"   Active Connections: {active_connections}")
        print(f"   Total Connections: {self.stats['total_connections']}")
        print(f"   Successful: {self.stats['successful_connections']}")
        print(f"   Failed: {self.stats['failed_connections']}")
        print(f"   Messages Received: {self.stats['messages_received']}")
        
        if self.stats['connection_times']:
            avg_connection_time = sum(self.stats['connection_times']) / len(self.stats['connection_times'])
            print(f"   Avg Connection Time: {avg_connection_time:.2f}ms")
    
    def cleanup_connections(self):
        """Clean up all connections"""
        print("\n🧹 Cleaning up connections...")
        
        for connection_info in self.connections.values():
            try:
                if connection_info['client'].connected:
                    connection_info['client'].disconnect()
            except Exception as e:
                print(f"⚠️ Error disconnecting {connection_info['id']}: {e}")
    
    def print_final_report(self):
        """Print final monitoring report"""
        print("\n" + "=" * 60)
        print("📋 FINAL MONITORING REPORT")
        print("=" * 60)
        
        total_time = datetime.now() - self.stats['start_time']
        
        print(f"Monitoring Duration: {total_time}")
        print(f"Total Connections Attempted: {self.stats['total_connections']}")
        print(f"Successful Connections: {self.stats['successful_connections']}")
        print(f"Failed Connections: {self.stats['failed_connections']}")
        print(f"Disconnections: {self.stats['disconnections']}")
        print(f"Messages Received: {self.stats['messages_received']}")
        
        if self.stats['total_connections'] > 0:
            success_rate = (self.stats['successful_connections'] / self.stats['total_connections']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        if self.stats['connection_times']:
            avg_time = sum(self.stats['connection_times']) / len(self.stats['connection_times'])
            min_time = min(self.stats['connection_times'])
            max_time = max(self.stats['connection_times'])
            
            print(f"\nConnection Time Statistics:")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  Minimum: {min_time:.2f}ms")
            print(f"  Maximum: {max_time:.2f}ms")
        
        if self.stats['errors']:
            print(f"\nErrors Encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][-5:]:  # Show last 5 errors
                print(f"  - {error['connection_id']}: {error['error']}")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
    
    def export_stats(self, filename=None):
        """Export statistics to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"websocket_monitor_{timestamp}.json"
        
        # Convert datetime objects to strings for JSON serialization
        export_data = self.stats.copy()
        export_data['start_time'] = export_data['start_time'].isoformat()
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📄 Statistics exported to {filename}")

def signal_handler(signum, frame):
    """Handle interrupt signal"""
    print("\n🛑 Monitoring interrupted by user")
    sys.exit(0)

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WebSocket Connection Monitor')
    parser.add_argument('--url', default='http://127.0.0.1:5000',
                       help='Base URL for monitoring (default: http://127.0.0.1:5000)')
    parser.add_argument('--connections', type=int, default=1,
                       help='Number of concurrent connections (default: 1)')
    parser.add_argument('--duration', type=int, default=60,
                       help='Monitoring duration in seconds (default: 60)')
    parser.add_argument('--export', type=str,
                       help='Export statistics to JSON file')
    
    args = parser.parse_args()
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    monitor = WebSocketMonitor(args.url)
    
    try:
        monitor.start_monitoring(args.connections, args.duration)
        
        if args.export:
            monitor.export_stats(args.export)
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
        monitor.stop_monitoring()
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### 3. Browser-Based Diagnostic Tool

Create: `static/js/websocket-diagnostics.js`

```javascript
// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * WebSocket Diagnostics Tool
 * Browser-based diagnostic and testing tool for WebSocket connections
 */

class WebSocketDiagnostics {
    constructor() {
        this.testResults = [];
        this.isRunning = false;
        this.socket = null;
        this.startTime = null;
        
        this.initializeUI();
    }
    
    initializeUI() {
        // Create diagnostic UI if it doesn't exist
        if (!document.getElementById('websocket-diagnostics')) {
            this.createDiagnosticUI();
        }
        
        // Bind event handlers
        this.bindEventHandlers();
    }
    
    createDiagnosticUI() {
        const diagnosticHTML = `
            <div id="websocket-diagnostics" style="
                position: fixed;
                top: 10px;
                left: 10px;
                width: 400px;
                background: white;
                border: 2px solid #007bff;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                z-index: 10000;
                font-family: monospace;
                font-size: 12px;
                display: none;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h3 style="margin: 0; color: #007bff;">WebSocket Diagnostics</h3>
                    <button id="close-diagnostics" style="background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">×</button>
                </div>
                
                <div style="margin-bottom: 10px;">
                    <button id="run-diagnostics" style="background: #28a745; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; margin-right: 5px;">Run Tests</button>
                    <button id="clear-results" style="background: #6c757d; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; margin-right: 5px;">Clear</button>
                    <button id="export-results" style="background: #17a2b8; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer;">Export</button>
                </div>
                
                <div id="diagnostic-status" style="margin-bottom: 10px; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                    Ready to run diagnostics
                </div>
                
                <div id="diagnostic-results" style="max-height: 300px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 4px;">
                    <div style="color: #6c757d; text-align: center;">No tests run yet</div>
                </div>
                
                <div style="margin-top: 10px; font-size: 10px; color: #6c757d;">
                    Press F12 → Console for detailed logs
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', diagnosticHTML);
    }
    
    bindEventHandlers() {
        document.getElementById('run-diagnostics').addEventListener('click', () => {
            this.runDiagnostics();
        });
        
        document.getElementById('clear-results').addEventListener('click', () => {
            this.clearResults();
        });
        
        document.getElementById('export-results').addEventListener('click', () => {
            this.exportResults();
        });
        
        document.getElementById('close-diagnostics').addEventListener('click', () => {
            this.hide();
        });
    }
    
    show() {
        document.getElementById('websocket-diagnostics').style.display = 'block';
    }
    
    hide() {
        document.getElementById('websocket-diagnostics').style.display = 'none';
    }
    
    toggle() {
        const diagnostics = document.getElementById('websocket-diagnostics');
        diagnostics.style.display = diagnostics.style.display === 'none' ? 'block' : 'none';
    }
    
    updateStatus(message, type = 'info') {
        const statusElement = document.getElementById('diagnostic-status');
        const colors = {
            info: '#17a2b8',
            success: '#28a745',
            warning: '#ffc107',
            error: '#dc3545'
        };
        
        statusElement.textContent = message;
        statusElement.style.background = colors[type] || colors.info;
        statusElement.style.color = type === 'warning' ? '#000' : '#fff';
    }
    
    addResult(testName, success, message, details = null) {
        const result = {
            testName,
            success,
            message,
            details,
            timestamp: new Date().toISOString()
        };
        
        this.testResults.push(result);
        
        const resultsContainer = document.getElementById('diagnostic-results');
        const resultElement = document.createElement('div');
        resultElement.style.marginBottom = '5px';
        resultElement.style.padding = '5px';
        resultElement.style.borderRadius = '3px';
        resultElement.style.background = success ? '#d4edda' : '#f8d7da';
        resultElement.style.color = success ? '#155724' : '#721c24';
        
        const icon = success ? '✅' : '❌';
        resultElement.innerHTML = `
            <strong>${icon} ${testName}</strong><br>
            <small>${message}</small>
            ${details ? `<br><small style="color: #6c757d;">${JSON.stringify(details)}</small>` : ''}
        `;
        
        resultsContainer.appendChild(resultElement);
        resultsContainer.scrollTop = resultsContainer.scrollHeight;
        
        console.log(`[WebSocket Diagnostics] ${testName}: ${message}`, details);
    }
    
    clearResults() {
        this.testResults = [];
        const resultsContainer = document.getElementById('diagnostic-results');
        resultsContainer.innerHTML = '<div style="color: #6c757d; text-align: center;">No tests run yet</div>';
        this.updateStatus('Results cleared');
    }
    
    async runDiagnostics() {
        if (this.isRunning) {
            this.updateStatus('Tests already running...', 'warning');
            return;
        }
        
        this.isRunning = true;
        this.startTime = Date.now();
        this.clearResults();
        this.updateStatus('Running diagnostics...', 'info');
        
        try {
            await this.testBrowserSupport();
            await this.testNetworkConnectivity();
            await this.testWebSocketConnection();
            await this.testNamespaceConnections();
            await this.testMessageEcho();
            await this.testPerformanceMetrics();
            
            const duration = Date.now() - this.startTime;
            const passed = this.testResults.filter(r => r.success).length;
            const total = this.testResults.length;
            
            this.updateStatus(`Tests completed in ${duration}ms (${passed}/${total} passed)`, 
                            passed === total ? 'success' : 'warning');
            
        } catch (error) {
            this.updateStatus(`Tests failed: ${error.message}`, 'error');
            this.addResult('Diagnostic Error', false, error.message);
        } finally {
            this.isRunning = false;
        }
    }
    
    async testBrowserSupport() {
        const features = {
            WebSocket: typeof WebSocket !== 'undefined',
            SocketIO: typeof io !== 'undefined',
            EventSource: typeof EventSource !== 'undefined',
            Fetch: typeof fetch !== 'undefined',
            Promise: typeof Promise !== 'undefined'
        };
        
        const allSupported = Object.values(features).every(Boolean);
        
        this.addResult('Browser Support', allSupported, 
                      allSupported ? 'All required features supported' : 'Missing required features',
                      features);
    }
    
    async testNetworkConnectivity() {
        try {
            const response = await fetch(window.location.origin, { 
                method: 'HEAD',
                cache: 'no-cache'
            });
            
            this.addResult('Network Connectivity', response.ok, 
                          `Server reachable (${response.status})`,
                          { status: response.status, statusText: response.statusText });
        } catch (error) {
            this.addResult('Network Connectivity', false, 
                          `Network error: ${error.message}`);
        }
    }
    
    async testWebSocketConnection() {
        return new Promise((resolve) => {
            const startTime = Date.now();
            let connectionTimeout;
            
            try {
                this.socket = io({
                    transports: ['websocket'],
                    timeout: 10000,
                    forceNew: true
                });
                
                connectionTimeout = setTimeout(() => {
                    this.addResult('WebSocket Connection', false, 'Connection timeout (10s)');
                    resolve();
                }, 10000);
                
                this.socket.on('connect', () => {
                    clearTimeout(connectionTimeout);
                    const connectionTime = Date.now() - startTime;
                    
                    this.addResult('WebSocket Connection', true, 
                                  `Connected successfully in ${connectionTime}ms`,
                                  { 
                                      socketId: this.socket.id,
                                      transport: this.socket.io.engine.transport.name,
                                      connectionTime
                                  });
                    resolve();
                });
                
                this.socket.on('connect_error', (error) => {
                    clearTimeout(connectionTimeout);
                    this.addResult('WebSocket Connection', false, 
                                  `Connection failed: ${error.message || error}`);
                    resolve();
                });
                
            } catch (error) {
                clearTimeout(connectionTimeout);
                this.addResult('WebSocket Connection', false, 
                              `Connection error: ${error.message}`);
                resolve();
            }
        });
    }
    
    async testNamespaceConnections() {
        const namespaces = ['/user', '/admin', '/system'];
        
        for (const namespace of namespaces) {
            await new Promise((resolve) => {
                try {
                    const nsSocket = io(namespace, {
                        transports: ['websocket'],
                        timeout: 5000,
                        forceNew: true
                    });
                    
                    const timeout = setTimeout(() => {
                        this.addResult(`Namespace ${namespace}`, false, 'Connection timeout');
                        nsSocket.disconnect();
                        resolve();
                    }, 5000);
                    
                    nsSocket.on('connect', () => {
                        clearTimeout(timeout);
                        this.addResult(`Namespace ${namespace}`, true, 'Connected successfully');
                        nsSocket.disconnect();
                        resolve();
                    });
                    
                    nsSocket.on('connect_error', (error) => {
                        clearTimeout(timeout);
                        this.addResult(`Namespace ${namespace}`, false, 
                                      `Connection failed: ${error.message || error}`);
                        resolve();
                    });
                    
                } catch (error) {
                    this.addResult(`Namespace ${namespace}`, false, 
                                  `Error: ${error.message}`);
                    resolve();
                }
            });
        }
    }
    
    async testMessageEcho() {
        if (!this.socket || !this.socket.connected) {
            this.addResult('Message Echo', false, 'No active WebSocket connection');
            return;
        }
        
        return new Promise((resolve) => {
            const testMessage = {
                test: 'echo',
                timestamp: Date.now(),
                random: Math.random()
            };
            
            const timeout = setTimeout(() => {
                this.addResult('Message Echo', false, 'Echo timeout (5s)');
                resolve();
            }, 5000);
            
            this.socket.once('test_echo_response', (response) => {
                clearTimeout(timeout);
                
                if (response && response.timestamp === testMessage.timestamp) {
                    this.addResult('Message Echo', true, 'Echo successful', response);
                } else {
                    this.addResult('Message Echo', false, 'Echo data mismatch', response);
                }
                resolve();
            });
            
            this.socket.emit('test_echo', testMessage);
        });
    }
    
    async testPerformanceMetrics() {
        const metrics = {
            connectionTime: null,
            messageLatency: null,
            memoryUsage: null
        };
        
        // Test connection time (if we have a fresh connection)
        if (this.socket && this.socket.connected) {
            const startTime = Date.now();
            
            // Test message round-trip time
            await new Promise((resolve) => {
                const timeout = setTimeout(resolve, 2000);
                
                this.socket.once('ping_response', () => {
                    clearTimeout(timeout);
                    metrics.messageLatency = Date.now() - startTime;
                    resolve();
                });
                
                this.socket.emit('ping', { timestamp: startTime });
            });
        }
        
        // Get memory usage if available
        if (performance.memory) {
            metrics.memoryUsage = {
                used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
                total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
                limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024)
            };
        }
        
        const hasMetrics = Object.values(metrics).some(v => v !== null);
        
        this.addResult('Performance Metrics', hasMetrics, 
                      hasMetrics ? 'Performance data collected' : 'No performance data available',
                      metrics);
    }
    
    exportResults() {
        const exportData = {
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href,
            testDuration: this.startTime ? Date.now() - this.startTime : null,
            results: this.testResults
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `websocket-diagnostics-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.updateStatus('Results exported successfully', 'success');
    }
}

// Initialize diagnostics tool
window.webSocketDiagnostics = new WebSocketDiagnostics();

// Console commands
console.log('🔧 WebSocket Diagnostics Tool Loaded');
console.log('Commands:');
console.log('  webSocketDiagnostics.show() - Show diagnostic panel');
console.log('  webSocketDiagnostics.hide() - Hide diagnostic panel');
console.log('  webSocketDiagnostics.toggle() - Toggle diagnostic panel');
console.log('  webSocketDiagnostics.runDiagnostics() - Run all tests');

// Keyboard shortcut (Ctrl+Shift+D)
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        window.webSocketDiagnostics.toggle();
    }
});
```

Now I'll create configuration documentation for the notification system.

<function_calls>
<invoke name="fsWrite">
<parameter name="path">docs/notification-system-configuration-guide.md