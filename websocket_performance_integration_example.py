# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Performance Integration Example

Demonstrates how to integrate all performance monitoring and optimization
components into a complete WebSocket system with monitoring, optimization,
and scalability testing capabilities.
"""

import time
import logging
import threading
from flask import Flask
from flask_socketio import SocketIO
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_factory import WebSocketFactory
from websocket_performance_monitor import WebSocketPerformanceMonitor, setup_performance_monitoring
from websocket_performance_optimizer import WebSocketPerformanceOptimizer, OptimizationStrategy
from websocket_performance_dashboard import WebSocketPerformanceDashboard
from websocket_scalability_tester import WebSocketScalabilityTester
from config import Config


class IntegratedWebSocketSystem:
    """Complete WebSocket system with performance monitoring and optimization"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize core WebSocket components
        self.websocket_config_manager = WebSocketConfigManager(config)
        self.cors_manager = CORSManager(self.websocket_config_manager)
        self.websocket_factory = WebSocketFactory(self.websocket_config_manager, self.cors_manager)
        
        # Initialize performance components
        self.performance_monitor = WebSocketPerformanceMonitor(monitoring_interval=30)
        self.performance_optimizer = WebSocketPerformanceOptimizer(
            self.performance_monitor, 
            OptimizationStrategy.BALANCED
        )
        self.scalability_tester = WebSocketScalabilityTester()
        
        # Initialize dashboard
        self.performance_dashboard = WebSocketPerformanceDashboard(
            self.performance_monitor,
            self.performance_optimizer,
            self.scalability_tester,
            port=5002
        )
        
        # Flask app and SocketIO
        self.app = None
        self.socketio = None
        
    def create_app(self) -> Flask:
        """Create Flask application with integrated WebSocket system"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'websocket_performance_demo'
        
        # Create SocketIO instance using factory
        self.socketio = self.websocket_factory.create_socketio_instance(self.app)
        
        # Set up performance monitoring for SocketIO
        setup_performance_monitoring(self.socketio, self.performance_monitor)
        
        # Set up optimization callbacks
        self._setup_optimization_callbacks()
        
        # Add demo routes
        self._setup_demo_routes()
        
        return self.app
        
    def start_monitoring(self):
        """Start all monitoring and optimization services"""
        self.logger.info("Starting performance monitoring services")
        
        # Start performance monitoring
        self.performance_monitor.start_monitoring()
        
        # Start auto-optimization
        self.performance_optimizer.start_auto_optimization()
        
        # Start dashboard in separate thread
        dashboard_thread = threading.Thread(
            target=self.performance_dashboard.run,
            kwargs={'debug': False, 'host': '127.0.0.1'},
            daemon=True
        )
        dashboard_thread.start()
        
        self.logger.info("All performance services started")
        
    def stop_monitoring(self):
        """Stop all monitoring and optimization services"""
        self.logger.info("Stopping performance monitoring services")
        
        self.performance_monitor.stop_monitoring()
        self.performance_optimizer.stop_auto_optimization()
        
        self.logger.info("All performance services stopped")
        
    def _setup_optimization_callbacks(self):
        """Set up callbacks for optimization events"""
        
        def optimization_callback(result):
            self.logger.info(f"Optimization applied: {result.rule_name} - {result.expected_impact}")
            
        def threshold_callback(threshold_name, current_value, threshold_value):
            self.logger.warning(f"Threshold exceeded: {threshold_name} = {current_value} (threshold: {threshold_value})")
            
        self.performance_optimizer.add_optimization_callback(optimization_callback)
        self.performance_monitor.add_threshold_callback(threshold_callback)   
     
    def _setup_demo_routes(self):
        """Set up demo routes for testing"""
        
        @self.app.route('/')
        def index():
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>WebSocket Performance Demo</title>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            </head>
            <body>
                <h1>WebSocket Performance Demo</h1>
                <div id="status">Connecting...</div>
                <div id="messages"></div>
                <button onclick="sendTestMessage()">Send Test Message</button>
                <button onclick="startLoadTest()">Start Load Test</button>
                <br><br>
                <a href="http://localhost:5002" target="_blank">Open Performance Dashboard</a>
                
                <script>
                    const socket = io();
                    let messageCount = 0;
                    
                    socket.on('connect', function() {
                        document.getElementById('status').innerHTML = 'Connected';
                    });
                    
                    socket.on('disconnect', function() {
                        document.getElementById('status').innerHTML = 'Disconnected';
                    });
                    
                    socket.on('test_response', function(data) {
                        const messages = document.getElementById('messages');
                        messages.innerHTML += '<div>Received: ' + JSON.stringify(data) + '</div>';
                    });
                    
                    function sendTestMessage() {
                        messageCount++;
                        socket.emit('test_message', {
                            id: messageCount,
                            timestamp: new Date().toISOString(),
                            data: 'Test message ' + messageCount
                        });
                    }
                    
                    function startLoadTest() {
                        for (let i = 0; i < 10; i++) {
                            setTimeout(() => sendTestMessage(), i * 100);
                        }
                    }
                </script>
            </body>
            </html>
            '''
            
        @self.socketio.on('test_message')
        def handle_test_message(data):
            """Handle test messages and echo back"""
            # Simulate some processing time
            time.sleep(0.01)
            
            response = {
                'original': data,
                'processed_at': time.time(),
                'echo': f"Echo: {data.get('data', 'No data')}"
            }
            
            self.socketio.emit('test_response', response)
            
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info(f"Client connected: {request.sid}")
            
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info(f"Client disconnected: {request.sid}")
            
    def run_demo(self, host='127.0.0.1', port=5000):
        """Run the complete demo system"""
        self.logger.info("Starting WebSocket Performance Demo")
        
        # Create Flask app
        app = self.create_app()
        
        # Start monitoring services
        self.start_monitoring()
        
        try:
            self.logger.info(f"Demo server starting on {host}:{port}")
            self.logger.info(f"Performance dashboard available at http://{host}:5002")
            
            # Run the Flask-SocketIO server
            self.socketio.run(app, host=host, port=port, debug=False)
            
        except KeyboardInterrupt:
            self.logger.info("Shutting down demo")
        finally:
            self.stop_monitoring()


def run_performance_demo():
    """Run the complete performance monitoring demo"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create config (you may need to adjust this based on your Config class)
    config = Config()
    
    # Create and run the integrated system
    system = IntegratedWebSocketSystem(config)
    system.run_demo()


def run_scalability_test_example():
    """Example of running scalability tests"""
    import asyncio
    from websocket_scalability_tester import create_load_test_config
    
    async def test_scalability():
        tester = WebSocketScalabilityTester()
        
        # Quick test
        print("Running quick scalability test...")
        config = create_load_test_config('http://localhost:5000', 50, 30)
        result = await tester.run_load_test(config)
        
        print(f"Quick test result: {result.result.value}")
        print(f"Performance level: {result.performance_summary.get('performance_level')}")
        print(f"Connection success rate: {result.aggregate_metrics.get('connection_success_rate', 0):.2%}")
        
        # Stress test
        print("\nRunning stress test...")
        base_config = create_load_test_config('http://localhost:5000', 100, 60)
        stress_results = await tester.run_stress_test(base_config, [25, 50, 100, 200])
        
        print(f"Stress test completed with {len(stress_results)} phases")
        for i, result in enumerate(stress_results):
            print(f"Phase {i+1} ({result.config.max_connections} connections): {result.result.value}")
            
    asyncio.run(test_scalability())


def run_optimization_example():
    """Example of using the performance optimizer"""
    from websocket_performance_monitor import create_performance_monitor
    from websocket_performance_optimizer import create_performance_optimizer, OptimizationStrategy
    
    # Create performance monitor
    monitor = create_performance_monitor(monitoring_interval=10)
    monitor.start_monitoring()
    
    # Create optimizer
    optimizer = create_performance_optimizer(monitor, OptimizationStrategy.BALANCED)
    
    # Set custom performance baselines
    optimizer.set_performance_baselines({
        'connection_success_rate': 0.98,
        'message_success_rate': 0.99,
        'avg_latency_ms': 50,
        'error_rate': 0.01,
        'cpu_usage': 60,
        'memory_usage': 70
    })
    
    # Start auto-optimization
    optimizer.start_auto_optimization()
    
    try:
        print("Performance optimizer running...")
        print("Monitor performance and optimization at http://localhost:5002")
        
        # Simulate some load for demonstration
        for i in range(100):
            monitor.register_connection(f"demo_conn_{i}", {
                'namespace': '/',
                'transport': 'websocket',
                'user_agent': 'demo_client'
            })
            
            # Simulate some message activity
            monitor.record_message_sent(f"demo_conn_{i}", 1024, 50.0)
            monitor.record_message_received(f"demo_conn_{i}", 512)
            
            time.sleep(0.1)
            
        # Let it run for a while
        time.sleep(60)
        
    except KeyboardInterrupt:
        print("Stopping optimization example")
    finally:
        optimizer.stop_auto_optimization()
        monitor.stop_monitoring()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            run_performance_demo()
        elif sys.argv[1] == "scalability":
            run_scalability_test_example()
        elif sys.argv[1] == "optimization":
            run_optimization_example()
        else:
            print("Usage: python websocket_performance_integration_example.py [demo|scalability|optimization]")
    else:
        print("Available examples:")
        print("  demo         - Run complete performance monitoring demo")
        print("  scalability  - Run scalability testing example")
        print("  optimization - Run performance optimization example")
        print("")
        print("Usage: python websocket_performance_integration_example.py <example_name>")