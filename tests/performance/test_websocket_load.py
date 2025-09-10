# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Load Testing Suite

This module provides comprehensive load testing for WebSocket connections,
including connection scaling, message throughput, concurrent user handling,
and resource usage monitoring under various load conditions.
"""

import unittest
import asyncio
import threading
import time
import json
import uuid
import statistics
import websocket
import ssl
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
import psutil
import gc
import queue

# Test framework imports
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import UserRole

# WebSocket imports
from websocket_factory import WebSocketFactory
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager


class WebSocketLoadClient:
    """WebSocket client for load testing"""
    
    def __init__(self, user_id: int, username: str, base_url: str = "ws://127.0.0.1:5000"):
        self.user_id = user_id
        self.username = username
        self.base_url = base_url
        self.ws = None
        self.connected = False
        self.messages_received = []
        self.messages_sent = []
        self.connection_time = None
        self.disconnect_time = None
        self.errors = []
        self.message_queue = queue.Queue()
        
    def connect(self, namespace: str = "/") -> bool:
        """Connect to WebSocket server"""
        try:
            start_time = time.time()
            
            # Create WebSocket URL
            ws_url = f"{self.base_url}/socket.io/?transport=websocket&EIO=4&t={int(time.time())}"
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start connection in separate thread
            self.connection_thread = threading.Thread(
                target=self.ws.run_forever,
                kwargs={'sslopt': {"cert_reqs": ssl.CERT_NONE}}
            )
            self.connection_thread.daemon = True
            self.connection_thread.start()
            
            # Wait for connection with timeout
            timeout = 10  # 10 seconds
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.01)
            
            if self.connected:
                self.connection_time = time.time() - start_time
                return True
            else:
                self.errors.append("Connection timeout")
                return False
                
        except Exception as e:
            self.errors.append(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from WebSocket server"""
        try:
            if self.ws and self.connected:
                start_time = time.time()
                self.ws.close()
                self.disconnect_time = time.time() - start_time
                self.connected = False
        except Exception as e:
            self.errors.append(f"Disconnect error: {e}")
    
    def send_message(self, event: str, data: Dict[str, Any], namespace: str = "/") -> bool:
        """Send message to server"""
        try:
            if not self.connected:
                return False
            
            # Format Socket.IO message
            message = f'42{namespace}["{event}",{json.dumps(data)}]'
            
            self.ws.send(message)
            self.messages_sent.append({
                'event': event,
                'data': data,
                'timestamp': time.time(),
                'namespace': namespace
            })
            return True
            
        except Exception as e:
            self.errors.append(f"Send error: {e}")
            return False
    
    def _on_open(self, ws):
        """Handle WebSocket open"""
        self.connected = True
        
        # Send Socket.IO handshake
        ws.send("40")  # Connect to default namespace
    
    def _on_message(self, ws, message):
        """Handle WebSocket message"""
        try:
            self.messages_received.append({
                'message': message,
                'timestamp': time.time()
            })
            
            # Parse Socket.IO message
            if message.startswith('42'):
                # Extract JSON payload
                json_start = message.find('[')
                if json_start != -1:
                    payload = json.loads(message[json_start:])
                    if len(payload) >= 2:
                        event = payload[0]
                        data = payload[1] if len(payload) > 1 else {}
                        
                        self.message_queue.put({
                            'event': event,
                            'data': data,
                            'timestamp': time.time()
                        })
                        
        except Exception as e:
            self.errors.append(f"Message parse error: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        self.errors.append(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        self.connected = False
    
    def get_received_messages(self) -> List[Dict[str, Any]]:
        """Get all received messages from queue"""
        messages = []
        while not self.message_queue.empty():
            try:
                messages.append(self.message_queue.get_nowait())
            except queue.Empty:
                break
        return messages
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'connected': self.connected,
            'connection_time': self.connection_time,
            'disconnect_time': self.disconnect_time,
            'messages_sent': len(self.messages_sent),
            'messages_received': len(self.messages_received),
            'errors': len(self.errors),
            'error_messages': self.errors[-5:]  # Last 5 errors
        }


class WebSocketLoadTestSuite(unittest.TestCase):
    """
    Comprehensive WebSocket load testing suite
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        
        # Create test users for load testing
        cls.test_users = []
        cls.user_helpers = []
        
        # Create unique timestamp for test users
        import time
        timestamp = int(time.time())
        
        # Create test users
        for i in range(25):  # Create 25 test users for WebSocket testing
            user, helper = create_test_user_with_platforms(
                cls.db_manager,
                username=f"ws_load_user_{timestamp}_{i}",
                role=UserRole.REVIEWER if i % 3 != 0 else UserRole.ADMIN
            )
            cls.test_users.append(user)
            cls.user_helpers.append(helper)
        
        # Start web application for WebSocket testing
        cls._start_web_application()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Clean up test users
        for helper in cls.user_helpers:
            try:
                cleanup_test_user(helper)
            except Exception as e:
                print(f"Warning: Failed to cleanup test user: {e}")
        
        # Stop web application
        cls._stop_web_application()
    
    @classmethod
    def _start_web_application(cls):
        """Start web application for testing"""
        try:
            # This would start the actual web application
            # For testing purposes, we'll assume it's running
            cls.web_app_running = True
            print("Note: Assuming web application is running on http://127.0.0.1:5000")
        except Exception as e:
            print(f"Warning: Could not start web application: {e}")
            cls.web_app_running = False
    
    @classmethod
    def _stop_web_application(cls):
        """Stop web application"""
        cls.web_app_running = False
    
    def setUp(self):
        """Set up individual test"""
        self.clients = []
        self.start_time = None
        self.end_time = None
        
        # Force garbage collection before each test
        gc.collect()
    
    def tearDown(self):
        """Clean up individual test"""
        # Disconnect all clients
        for client in self.clients:
            try:
                client.disconnect()
            except Exception:
                pass
        self.clients.clear()
        
        # Force garbage collection after each test
        gc.collect()
    
    def test_websocket_connection_scaling(self):
        """Test WebSocket connection scaling performance"""
        print("\n=== Testing WebSocket Connection Scaling ===")
        
        if not self.web_app_running:
            self.skipTest("Web application not running")
        
        # Test parameters
        max_connections = 50
        connection_batch_size = 5
        
        self.start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        connection_times = []
        successful_connections = 0
        failed_connections = 0
        
        # Create connections in batches
        for batch_start in range(0, max_connections, connection_batch_size):
            batch_end = min(batch_start + connection_batch_size, max_connections)
            batch_clients = []
            
            # Create batch of clients
            for i in range(batch_start, batch_end):
                user = self.test_users[i % len(self.test_users)]
                client = WebSocketLoadClient(user.id, user.username)
                batch_clients.append(client)
            
            # Connect batch concurrently
            with ThreadPoolExecutor(max_workers=connection_batch_size) as executor:
                futures = [executor.submit(client.connect) for client in batch_clients]
                
                for future, client in zip(futures, batch_clients):
                    try:
                        success = future.result(timeout=15)
                        if success:
                            successful_connections += 1
                            connection_times.append(client.connection_time)
                            self.clients.append(client)
                        else:
                            failed_connections += 1
                    except Exception as e:
                        failed_connections += 1
                        print(f"Connection failed: {e}")
            
            # Brief pause between batches
            time.sleep(0.1)
            
            # Monitor memory usage
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            print(f"Batch {batch_start//connection_batch_size + 1}: {len(self.clients)} connections, {current_memory:.1f}MB")
        
        self.end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Test message broadcasting to all connections
        if self.clients:
            broadcast_start = time.time()
            broadcast_success = 0
            
            test_message = {
                'type': 'load_test',
                'message': 'Broadcasting to all connections',
                'timestamp': time.time()
            }
            
            for client in self.clients:
                if client.send_message('test_broadcast', test_message):
                    broadcast_success += 1
            
            broadcast_time = time.time() - broadcast_start
        else:
            broadcast_time = 0
            broadcast_success = 0
        
        # Analyze results
        total_time = self.end_time - self.start_time
        memory_usage = end_memory - start_memory
        
        print(f"WebSocket Connection Scaling Results:")
        print(f"  - Target connections: {max_connections}")
        print(f"  - Successful connections: {successful_connections}")
        print(f"  - Failed connections: {failed_connections}")
        print(f"  - Success rate: {(successful_connections/max_connections)*100:.2f}%")
        print(f"  - Total time: {total_time:.2f}s")
        print(f"  - Average connection time: {statistics.mean(connection_times)*1000:.2f}ms" if connection_times else "N/A")
        print(f"  - Memory usage: {start_memory:.1f}MB -> {end_memory:.1f}MB (+{memory_usage:.1f}MB)")
        print(f"  - Memory per connection: {memory_usage/successful_connections:.3f}MB" if successful_connections > 0 else "N/A")
        print(f"  - Broadcast success: {broadcast_success}/{successful_connections}")
        print(f"  - Broadcast time: {broadcast_time*1000:.2f}ms")
        
        # Performance assertions
        self.assertGreater(successful_connections, max_connections * 0.8, "Should achieve > 80% connection success rate")
        if connection_times:
            self.assertLess(statistics.mean(connection_times), 2.0, "Average connection time should be < 2 seconds")
        self.assertLess(memory_usage, 100, "Memory usage should be < 100MB for 50 connections")
    
    def test_websocket_message_throughput(self):
        """Test WebSocket message throughput performance"""
        print("\n=== Testing WebSocket Message Throughput ===")
        
        if not self.web_app_running:
            self.skipTest("Web application not running")
        
        # Test parameters
        num_clients = 10
        messages_per_client = 50
        
        # Create and connect clients
        print(f"Creating {num_clients} WebSocket clients...")
        
        for i in range(num_clients):
            user = self.test_users[i % len(self.test_users)]
            client = WebSocketLoadClient(user.id, user.username)
            
            if client.connect():
                self.clients.append(client)
            else:
                print(f"Failed to connect client {i}")
        
        connected_clients = len(self.clients)
        print(f"Successfully connected {connected_clients} clients")
        
        if connected_clients == 0:
            self.skipTest("No WebSocket clients connected")
        
        # Test message sending throughput
        self.start_time = time.time()
        
        def send_messages_for_client(client: WebSocketLoadClient) -> Tuple[int, int, List[float]]:
            """Send messages for a single client"""
            success_count = 0
            error_count = 0
            send_times = []
            
            for i in range(messages_per_client):
                start_time = time.time()
                
                message_data = {
                    'message_id': str(uuid.uuid4()),
                    'sequence': i,
                    'user_id': client.user_id,
                    'timestamp': time.time(),
                    'payload': f"Load test message {i} from {client.username}"
                }
                
                success = client.send_message('load_test_message', message_data)
                
                send_time = time.time() - start_time
                send_times.append(send_time)
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
                
                # Small delay to prevent overwhelming
                time.sleep(0.01)
            
            return success_count, error_count, send_times
        
        # Send messages concurrently from all clients
        with ThreadPoolExecutor(max_workers=connected_clients) as executor:
            futures = [
                executor.submit(send_messages_for_client, client)
                for client in self.clients
            ]
            
            total_success = 0
            total_errors = 0
            all_send_times = []
            
            for future in as_completed(futures):
                try:
                    success_count, error_count, send_times = future.result(timeout=30)
                    total_success += success_count
                    total_errors += error_count
                    all_send_times.extend(send_times)
                except Exception as e:
                    print(f"Client message sending failed: {e}")
                    total_errors += messages_per_client
        
        self.end_time = time.time()
        
        # Wait for message reception
        time.sleep(2)
        
        # Collect received messages
        total_received = 0
        for client in self.clients:
            received_messages = client.get_received_messages()
            total_received += len(received_messages)
        
        # Analyze results
        total_time = self.end_time - self.start_time
        total_messages = connected_clients * messages_per_client
        
        print(f"WebSocket Message Throughput Results:")
        print(f"  - Connected clients: {connected_clients}")
        print(f"  - Messages per client: {messages_per_client}")
        print(f"  - Total messages sent: {total_success}")
        print(f"  - Total messages failed: {total_errors}")
        print(f"  - Send success rate: {(total_success/total_messages)*100:.2f}%")
        print(f"  - Total time: {total_time:.2f}s")
        print(f"  - Send throughput: {total_success/total_time:.2f} messages/sec")
        print(f"  - Average send time: {statistics.mean(all_send_times)*1000:.2f}ms" if all_send_times else "N/A")
        print(f"  - Messages received: {total_received}")
        print(f"  - Reception rate: {(total_received/total_success)*100:.2f}%" if total_success > 0 else "N/A")
        
        # Performance assertions
        self.assertGreater(total_success / total_messages, 0.9, "Should achieve > 90% message send success rate")
        self.assertGreater(total_success / total_time, 100, "Should achieve > 100 messages/sec throughput")
        if all_send_times:
            self.assertLess(statistics.mean(all_send_times), 0.1, "Average send time should be < 100ms")
    
    def test_websocket_concurrent_user_simulation(self):
        """Test WebSocket performance with concurrent user simulation"""
        print("\n=== Testing WebSocket Concurrent User Simulation ===")
        
        if not self.web_app_running:
            self.skipTest("Web application not running")
        
        # Test parameters
        concurrent_users = 15
        session_duration = 10  # seconds
        activity_interval = 1  # seconds between activities
        
        # Create clients
        print(f"Simulating {concurrent_users} concurrent users...")
        
        for i in range(concurrent_users):
            user = self.test_users[i % len(self.test_users)]
            client = WebSocketLoadClient(user.id, user.username)
            
            if client.connect():
                self.clients.append(client)
        
        connected_clients = len(self.clients)
        print(f"Connected {connected_clients} concurrent users")
        
        if connected_clients == 0:
            self.skipTest("No WebSocket clients connected")
        
        def simulate_user_activity(client: WebSocketLoadClient) -> Dict[str, Any]:
            """Simulate realistic user activity"""
            activities = 0
            messages_sent = 0
            messages_received = 0
            errors = 0
            
            start_time = time.time()
            
            while time.time() - start_time < session_duration:
                try:
                    # Simulate different types of user activities
                    activity_type = ['status_update', 'notification_ack', 'heartbeat'][activities % 3]
                    
                    activity_data = {
                        'activity_type': activity_type,
                        'user_id': client.user_id,
                        'timestamp': time.time(),
                        'session_time': time.time() - start_time
                    }
                    
                    if client.send_message('user_activity', activity_data):
                        messages_sent += 1
                    else:
                        errors += 1
                    
                    activities += 1
                    
                    # Check for received messages
                    received = client.get_received_messages()
                    messages_received += len(received)
                    
                    # Wait for next activity
                    time.sleep(activity_interval)
                    
                except Exception as e:
                    errors += 1
            
            return {
                'client_id': client.user_id,
                'activities': activities,
                'messages_sent': messages_sent,
                'messages_received': messages_received,
                'errors': errors,
                'session_duration': time.time() - start_time
            }
        
        # Run concurrent user simulation
        self.start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=connected_clients) as executor:
            futures = [
                executor.submit(simulate_user_activity, client)
                for client in self.clients
            ]
            
            user_results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=session_duration + 5)
                    user_results.append(result)
                except Exception as e:
                    print(f"User simulation failed: {e}")
        
        self.end_time = time.time()
        
        # Analyze results
        total_time = self.end_time - self.start_time
        
        if user_results:
            total_activities = sum(r['activities'] for r in user_results)
            total_messages_sent = sum(r['messages_sent'] for r in user_results)
            total_messages_received = sum(r['messages_received'] for r in user_results)
            total_errors = sum(r['errors'] for r in user_results)
            
            avg_activities = statistics.mean([r['activities'] for r in user_results])
            avg_messages_sent = statistics.mean([r['messages_sent'] for r in user_results])
            avg_session_duration = statistics.mean([r['session_duration'] for r in user_results])
        else:
            total_activities = total_messages_sent = total_messages_received = total_errors = 0
            avg_activities = avg_messages_sent = avg_session_duration = 0
        
        print(f"Concurrent User Simulation Results:")
        print(f"  - Concurrent users: {connected_clients}")
        print(f"  - Session duration: {session_duration}s")
        print(f"  - Total simulation time: {total_time:.2f}s")
        print(f"  - Total activities: {total_activities}")
        print(f"  - Total messages sent: {total_messages_sent}")
        print(f"  - Total messages received: {total_messages_received}")
        print(f"  - Total errors: {total_errors}")
        print(f"  - Average activities per user: {avg_activities:.1f}")
        print(f"  - Average messages per user: {avg_messages_sent:.1f}")
        print(f"  - Average session duration: {avg_session_duration:.2f}s")
        print(f"  - Activity throughput: {total_activities/total_time:.2f} activities/sec")
        print(f"  - Message throughput: {total_messages_sent/total_time:.2f} messages/sec")
        print(f"  - Error rate: {(total_errors/(total_messages_sent+total_errors))*100:.2f}%" if total_messages_sent + total_errors > 0 else "0%")
        
        # Performance assertions
        if user_results:
            self.assertGreater(avg_activities, session_duration * 0.8, "Users should maintain reasonable activity levels")
            self.assertLess(total_errors / (total_messages_sent + total_errors), 0.05, "Error rate should be < 5%")
            self.assertGreater(total_activities / total_time, 10, "Should maintain > 10 activities/sec across all users")
    
    def test_websocket_resource_usage_monitoring(self):
        """Test WebSocket resource usage under load"""
        print("\n=== Testing WebSocket Resource Usage Monitoring ===")
        
        if not self.web_app_running:
            self.skipTest("Web application not running")
        
        # Test parameters
        monitoring_duration = 15  # seconds
        num_clients = 20
        message_frequency = 2  # messages per second per client
        
        # Monitor initial resource usage
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        initial_cpu = psutil.cpu_percent()
        
        memory_samples = [initial_memory]
        cpu_samples = [initial_cpu]
        
        # Create and connect clients
        print(f"Creating {num_clients} clients for resource monitoring...")
        
        for i in range(num_clients):
            user = self.test_users[i % len(self.test_users)]
            client = WebSocketLoadClient(user.id, user.username)
            
            if client.connect():
                self.clients.append(client)
        
        connected_clients = len(self.clients)
        print(f"Connected {connected_clients} clients")
        
        if connected_clients == 0:
            self.skipTest("No WebSocket clients connected")
        
        def monitor_resources():
            """Monitor system resources during test"""
            start_time = time.time()
            
            while time.time() - start_time < monitoring_duration:
                memory_samples.append(psutil.Process().memory_info().rss / 1024 / 1024)
                cpu_samples.append(psutil.cpu_percent())
                time.sleep(0.5)  # Sample every 500ms
        
        def generate_load_for_client(client: WebSocketLoadClient) -> Dict[str, Any]:
            """Generate continuous load for a client"""
            messages_sent = 0
            errors = 0
            start_time = time.time()
            
            while time.time() - start_time < monitoring_duration:
                try:
                    message_data = {
                        'load_test': True,
                        'timestamp': time.time(),
                        'client_id': client.user_id
                    }
                    
                    if client.send_message('resource_test', message_data):
                        messages_sent += 1
                    else:
                        errors += 1
                    
                    # Wait based on message frequency
                    time.sleep(1.0 / message_frequency)
                    
                except Exception as e:
                    errors += 1
            
            return {
                'client_id': client.user_id,
                'messages_sent': messages_sent,
                'errors': errors,
                'duration': time.time() - start_time
            }
        
        # Start resource monitoring
        monitor_thread = threading.Thread(target=monitor_resources)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Start load generation
        self.start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=connected_clients + 1) as executor:
            # Submit load generation tasks
            load_futures = [
                executor.submit(generate_load_for_client, client)
                for client in self.clients
            ]
            
            # Collect results
            load_results = []
            for future in as_completed(load_futures):
                try:
                    result = future.result(timeout=monitoring_duration + 5)
                    load_results.append(result)
                except Exception as e:
                    print(f"Load generation failed: {e}")
        
        self.end_time = time.time()
        
        # Wait for monitoring to complete
        monitor_thread.join(timeout=2)
        
        # Analyze resource usage
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        if load_results:
            total_messages = sum(r['messages_sent'] for r in load_results)
            total_errors = sum(r['errors'] for r in load_results)
        else:
            total_messages = total_errors = 0
        
        memory_usage = {
            'initial': initial_memory,
            'final': final_memory,
            'peak': max(memory_samples),
            'average': statistics.mean(memory_samples),
            'growth': final_memory - initial_memory
        }
        
        cpu_usage = {
            'initial': initial_cpu,
            'peak': max(cpu_samples),
            'average': statistics.mean(cpu_samples)
        }
        
        total_time = self.end_time - self.start_time
        
        print(f"WebSocket Resource Usage Results:")
        print(f"  - Monitoring duration: {monitoring_duration}s")
        print(f"  - Connected clients: {connected_clients}")
        print(f"  - Message frequency: {message_frequency} msg/sec/client")
        print(f"  - Total messages sent: {total_messages}")
        print(f"  - Total errors: {total_errors}")
        print(f"  - Message throughput: {total_messages/total_time:.2f} msg/sec")
        print(f"  - Memory usage:")
        print(f"    Initial: {memory_usage['initial']:.1f}MB")
        print(f"    Final: {memory_usage['final']:.1f}MB")
        print(f"    Peak: {memory_usage['peak']:.1f}MB")
        print(f"    Average: {memory_usage['average']:.1f}MB")
        print(f"    Growth: {memory_usage['growth']:.1f}MB")
        print(f"  - CPU usage:")
        print(f"    Peak: {cpu_usage['peak']:.1f}%")
        print(f"    Average: {cpu_usage['average']:.1f}%")
        
        # Resource usage assertions
        self.assertLess(memory_usage['growth'], 50, "Memory growth should be < 50MB during test")
        self.assertLess(cpu_usage['peak'], 80, "Peak CPU usage should be < 80%")
        self.assertLess(cpu_usage['average'], 50, "Average CPU usage should be < 50%")
        
        if total_messages + total_errors > 0:
            error_rate = total_errors / (total_messages + total_errors)
            self.assertLess(error_rate, 0.05, "Error rate should be < 5%")


if __name__ == '__main__':
    # Run WebSocket load tests with detailed output
    unittest.main(verbosity=2, buffer=True)