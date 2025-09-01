# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification System Performance and Load Testing Suite

This module provides comprehensive performance testing for the notification system,
including high-volume notification delivery, concurrent user handling, WebSocket
connection scaling, queue management, and graceful degradation testing.
"""

import unittest
import asyncio
import threading
import time
import json
import uuid
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
import psutil
import gc

# Test framework imports
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from config import Config
from database import DatabaseManager
from models import UserRole, NotificationType, NotificationPriority, NotificationCategory

# Notification system imports
from unified_notification_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from notification_message_router import NotificationMessageRouter
from notification_persistence_manager import NotificationPersistenceManager
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager


class PerformanceMetrics:
    """Performance metrics collection and analysis"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.operation_times = []
        self.memory_usage = []
        self.cpu_usage = []
        self.error_count = 0
        self.success_count = 0
        self.throughput_data = []
        
    def start_measurement(self):
        """Start performance measurement"""
        self.start_time = time.time()
        self.memory_usage.append(psutil.Process().memory_info().rss / 1024 / 1024)  # MB
        self.cpu_usage.append(psutil.cpu_percent())
        
    def end_measurement(self):
        """End performance measurement"""
        self.end_time = time.time()
        self.memory_usage.append(psutil.Process().memory_info().rss / 1024 / 1024)  # MB
        self.cpu_usage.append(psutil.cpu_percent())
        
    def record_operation(self, duration: float, success: bool = True):
        """Record individual operation metrics"""
        self.operation_times.append(duration)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            
    def record_throughput(self, operations_per_second: float):
        """Record throughput measurement"""
        self.throughput_data.append(operations_per_second)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        if not self.operation_times:
            return {'error': 'No operations recorded'}
            
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        return {
            'total_time': total_time,
            'total_operations': len(self.operation_times),
            'success_rate': self.success_count / (self.success_count + self.error_count) * 100,
            'average_operation_time': statistics.mean(self.operation_times),
            'median_operation_time': statistics.median(self.operation_times),
            'min_operation_time': min(self.operation_times),
            'max_operation_time': max(self.operation_times),
            'operation_time_stddev': statistics.stdev(self.operation_times) if len(self.operation_times) > 1 else 0,
            'operations_per_second': len(self.operation_times) / total_time if total_time > 0 else 0,
            'memory_usage_mb': {
                'start': self.memory_usage[0] if self.memory_usage else 0,
                'end': self.memory_usage[-1] if len(self.memory_usage) > 1 else 0,
                'peak': max(self.memory_usage) if self.memory_usage else 0,
                'average': statistics.mean(self.memory_usage) if self.memory_usage else 0
            },
            'cpu_usage_percent': {
                'average': statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
                'peak': max(self.cpu_usage) if self.cpu_usage else 0
            },
            'throughput_stats': {
                'average': statistics.mean(self.throughput_data) if self.throughput_data else 0,
                'peak': max(self.throughput_data) if self.throughput_data else 0
            }
        }


class MockWebSocketConnection:
    """Mock WebSocket connection for testing"""
    
    def __init__(self, user_id: int, namespace: str = '/'):
        self.user_id = user_id
        self.namespace = namespace
        self.session_id = str(uuid.uuid4())
        self.connected = True
        self.messages_received = []
        self.connection_time = time.time()
        
    def emit(self, event: str, data: Dict[str, Any]):
        """Mock emit function"""
        if self.connected:
            self.messages_received.append({
                'event': event,
                'data': data,
                'timestamp': time.time()
            })
            return True
        return False
        
    def disconnect(self):
        """Mock disconnect function"""
        self.connected = False


class NotificationPerformanceTestSuite(unittest.TestCase):
    """
    Comprehensive performance and load testing suite for notification system
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        
        # Create test users for performance testing
        cls.test_users = []
        cls.user_helpers = []
        
        # Create unique timestamp for test users
        import time
        timestamp = int(time.time())
        
        # Create multiple test users for concurrent testing
        for i in range(50):  # Create 50 test users
            user, helper = create_test_user_with_platforms(
                cls.db_manager,
                username=f"perf_user_{timestamp}_{i}",
                role=UserRole.REVIEWER if i % 4 != 0 else UserRole.ADMIN
            )
            cls.test_users.append(user)
            cls.user_helpers.append(helper)
        
        # Initialize notification system components
        cls._setup_notification_system()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Clean up test users
        for helper in cls.user_helpers:
            try:
                cleanup_test_user(helper)
            except Exception as e:
                print(f"Warning: Failed to cleanup test user: {e}")
    
    @classmethod
    def _setup_notification_system(cls):
        """Set up notification system components for testing"""
        try:
            # Create WebSocket components
            config_manager = WebSocketConfigManager(cls.config)
            cors_manager = CORSManager(config_manager)
            
            # Create mock session manager for auth handler (simplified for testing)
            class MockSessionManager:
                def __init__(self, db_manager):
                    self.db_manager = db_manager
                
                def get_session_data(self, session_id):
                    return {'user_id': 1, 'username': 'test_user', 'role': 'ADMIN'}
                
                def create_session(self, user_id, platform_id=None):
                    return str(uuid.uuid4())
                
                def destroy_session(self, session_id):
                    return True
            
            session_manager = MockSessionManager(cls.db_manager)
            auth_handler = WebSocketAuthHandler(cls.db_manager, session_manager)
            
            # Create mock SocketIO for testing
            from flask import Flask
            app = Flask(__name__)
            
            factory = WebSocketFactory(config_manager, cors_manager, cls.db_manager)
            socketio = factory.create_test_socketio_instance(app, {
                'async_mode': 'threading',
                'cors_allowed_origins': '*'
            })
            
            namespace_manager = WebSocketNamespaceManager(socketio, auth_handler)
            
            # Initialize notification system
            cls.notification_manager = UnifiedNotificationManager(
                factory, auth_handler, namespace_manager, cls.db_manager
            )
            
            cls.message_router = NotificationMessageRouter(namespace_manager)
            cls.persistence_manager = NotificationPersistenceManager(cls.db_manager)
            
        except Exception as e:
            raise RuntimeError(f"Failed to setup notification system: {e}")
    
    def setUp(self):
        """Set up individual test"""
        self.metrics = PerformanceMetrics()
        self.mock_connections = {}
        
        # Force garbage collection before each test
        gc.collect()
    
    def tearDown(self):
        """Clean up individual test"""
        # Disconnect all mock connections
        for connection in self.mock_connections.values():
            connection.disconnect()
        self.mock_connections.clear()
        
        # Force garbage collection after each test
        gc.collect()
    
    def test_high_volume_notification_delivery(self):
        """Test high-volume notification delivery performance"""
        print("\n=== Testing High-Volume Notification Delivery ===")
        
        # Test parameters
        notification_count = 1000
        batch_size = 50
        
        self.metrics.start_measurement()
        
        # Create notifications in batches
        notifications_sent = 0
        for batch_start in range(0, notification_count, batch_size):
            batch_end = min(batch_start + batch_size, notification_count)
            batch_notifications = []
            
            for i in range(batch_start, batch_end):
                user = self.test_users[i % len(self.test_users)]
                notification = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Performance Test Notification {i}",
                    message=f"This is test notification number {i}",
                    user_id=user.id,
                    priority=NotificationPriority.NORMAL,
                    category=NotificationCategory.SYSTEM
                )
                batch_notifications.append(notification)
            
            # Send batch
            batch_start_time = time.time()
            
            for notification in batch_notifications:
                success = self.notification_manager.send_user_notification(
                    notification.user_id, notification
                )
                self.metrics.record_operation(time.time() - batch_start_time, success)
                if success:
                    notifications_sent += 1
            
            batch_duration = time.time() - batch_start_time
            batch_throughput = len(batch_notifications) / batch_duration
            self.metrics.record_throughput(batch_throughput)
            
            # Brief pause between batches to measure sustained performance
            time.sleep(0.01)
        
        self.metrics.end_measurement()
        
        # Analyze results
        summary = self.metrics.get_summary()
        print(f"High-Volume Delivery Results:")
        print(f"  - Total notifications: {notification_count}")
        print(f"  - Successfully sent: {notifications_sent}")
        print(f"  - Success rate: {summary['success_rate']:.2f}%")
        print(f"  - Average throughput: {summary['operations_per_second']:.2f} notifications/sec")
        print(f"  - Peak throughput: {summary['throughput_stats']['peak']:.2f} notifications/sec")
        print(f"  - Average operation time: {summary['average_operation_time']*1000:.2f}ms")
        print(f"  - Memory usage: {summary['memory_usage_mb']['start']:.1f}MB -> {summary['memory_usage_mb']['end']:.1f}MB")
        
        # Performance assertions
        self.assertGreater(summary['success_rate'], 95.0, "Success rate should be > 95%")
        self.assertGreater(summary['operations_per_second'], 100, "Should handle > 100 notifications/sec")
        self.assertLess(summary['average_operation_time'], 0.1, "Average operation time should be < 100ms")
        
        # Memory usage should not grow excessively
        memory_growth = summary['memory_usage_mb']['end'] - summary['memory_usage_mb']['start']
        self.assertLess(memory_growth, 100, "Memory growth should be < 100MB for 1000 notifications")
    
    def test_concurrent_user_notification_handling(self):
        """Test concurrent user notification handling"""
        print("\n=== Testing Concurrent User Notification Handling ===")
        
        # Test parameters
        concurrent_users = 20
        notifications_per_user = 25
        
        self.metrics.start_measurement()
        
        def send_notifications_for_user(user_index: int) -> Tuple[int, int, List[float]]:
            """Send notifications for a single user"""
            user = self.test_users[user_index]
            success_count = 0
            error_count = 0
            operation_times = []
            
            for i in range(notifications_per_user):
                start_time = time.time()
                
                notification = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.SUCCESS,
                    title=f"Concurrent Test {user_index}-{i}",
                    message=f"Concurrent notification for user {user.username}",
                    user_id=user.id,
                    priority=NotificationPriority.NORMAL,
                    category=NotificationCategory.USER
                )
                
                success = self.notification_manager.send_user_notification(
                    user.id, notification
                )
                
                operation_time = time.time() - start_time
                operation_times.append(operation_time)
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
                
                # Small delay to simulate realistic usage
                time.sleep(0.001)
            
            return success_count, error_count, operation_times
        
        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [
                executor.submit(send_notifications_for_user, i)
                for i in range(concurrent_users)
            ]
            
            total_success = 0
            total_errors = 0
            all_operation_times = []
            
            for future in as_completed(futures):
                success_count, error_count, operation_times = future.result()
                total_success += success_count
                total_errors += error_count
                all_operation_times.extend(operation_times)
                
                # Record metrics for each operation
                for op_time in operation_times:
                    self.metrics.record_operation(op_time, True)
        
        self.metrics.end_measurement()
        
        # Analyze results
        summary = self.metrics.get_summary()
        total_notifications = concurrent_users * notifications_per_user
        
        print(f"Concurrent User Handling Results:")
        print(f"  - Concurrent users: {concurrent_users}")
        print(f"  - Notifications per user: {notifications_per_user}")
        print(f"  - Total notifications: {total_notifications}")
        print(f"  - Total successful: {total_success}")
        print(f"  - Success rate: {(total_success/total_notifications)*100:.2f}%")
        print(f"  - Average operation time: {statistics.mean(all_operation_times)*1000:.2f}ms")
        print(f"  - Median operation time: {statistics.median(all_operation_times)*1000:.2f}ms")
        print(f"  - 95th percentile: {sorted(all_operation_times)[int(len(all_operation_times)*0.95)]*1000:.2f}ms")
        print(f"  - Total time: {summary['total_time']:.2f}s")
        print(f"  - Throughput: {summary['operations_per_second']:.2f} notifications/sec")
        
        # Performance assertions
        success_rate = (total_success / total_notifications) * 100
        self.assertGreater(success_rate, 95.0, "Concurrent success rate should be > 95%")
        self.assertLess(statistics.mean(all_operation_times), 0.05, "Average concurrent operation time should be < 50ms")
        self.assertGreater(summary['operations_per_second'], 200, "Concurrent throughput should be > 200 notifications/sec")
    
    def test_websocket_connection_scaling(self):
        """Test WebSocket connection scaling and resource usage"""
        print("\n=== Testing WebSocket Connection Scaling ===")
        
        # Test parameters
        max_connections = 100
        connection_batch_size = 10
        
        self.metrics.start_measurement()
        
        connections_created = 0
        connection_times = []
        
        # Create connections in batches
        for batch_start in range(0, max_connections, connection_batch_size):
            batch_end = min(batch_start + connection_batch_size, max_connections)
            
            for i in range(batch_start, batch_end):
                start_time = time.time()
                
                user = self.test_users[i % len(self.test_users)]
                connection = MockWebSocketConnection(user.id, '/')
                
                # Simulate connection establishment overhead
                time.sleep(0.001)  # 1ms connection overhead
                
                self.mock_connections[connection.session_id] = connection
                
                connection_time = time.time() - start_time
                connection_times.append(connection_time)
                self.metrics.record_operation(connection_time, True)
                connections_created += 1
            
            # Measure memory usage after each batch
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            self.metrics.memory_usage.append(current_memory)
            
            # Brief pause between batches
            time.sleep(0.01)
        
        # Test message broadcasting to all connections
        broadcast_start = time.time()
        
        broadcast_message = SystemNotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Broadcast Test",
            message="Testing broadcast to all connections",
            priority=NotificationPriority.NORMAL,
            category=NotificationCategory.SYSTEM
        )
        
        # Simulate broadcasting to all connections
        broadcast_success = 0
        for connection in self.mock_connections.values():
            if connection.emit('notification', broadcast_message.to_dict()):
                broadcast_success += 1
        
        broadcast_time = time.time() - broadcast_start
        
        self.metrics.end_measurement()
        
        # Analyze results
        summary = self.metrics.get_summary()
        
        print(f"WebSocket Connection Scaling Results:")
        print(f"  - Connections created: {connections_created}")
        print(f"  - Average connection time: {statistics.mean(connection_times)*1000:.2f}ms")
        print(f"  - Memory usage growth: {summary['memory_usage_mb']['end'] - summary['memory_usage_mb']['start']:.1f}MB")
        print(f"  - Memory per connection: {(summary['memory_usage_mb']['end'] - summary['memory_usage_mb']['start'])/connections_created:.3f}MB")
        print(f"  - Broadcast success rate: {(broadcast_success/connections_created)*100:.2f}%")
        print(f"  - Broadcast time: {broadcast_time*1000:.2f}ms")
        print(f"  - Broadcast throughput: {broadcast_success/broadcast_time:.2f} messages/sec")
        
        # Performance assertions
        self.assertEqual(connections_created, max_connections, "Should create all requested connections")
        self.assertLess(statistics.mean(connection_times), 0.01, "Average connection time should be < 10ms")
        
        # Memory usage should be reasonable
        memory_per_connection = (summary['memory_usage_mb']['end'] - summary['memory_usage_mb']['start']) / connections_created
        self.assertLess(memory_per_connection, 1.0, "Memory per connection should be < 1MB")
        
        # Broadcast should be efficient
        self.assertGreater(broadcast_success / connections_created, 0.95, "Broadcast success rate should be > 95%")
        self.assertLess(broadcast_time, 1.0, "Broadcast time should be < 1 second")
    
    def test_notification_queue_management_under_load(self):
        """Test notification queue management and memory usage under load"""
        print("\n=== Testing Notification Queue Management Under Load ===")
        
        # Test parameters
        offline_users = 10
        messages_per_user = 200
        
        self.metrics.start_measurement()
        
        # Create offline users (simulate by not creating connections)
        offline_user_ids = [user.id for user in self.test_users[:offline_users]]
        
        # Queue messages for offline users
        total_queued = 0
        queue_times = []
        
        for user_id in offline_user_ids:
            for i in range(messages_per_user):
                start_time = time.time()
                
                notification = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.WARNING,
                    title=f"Offline Queue Test {i}",
                    message=f"Queued message {i} for offline user {user_id}",
                    user_id=user_id,
                    priority=NotificationPriority.NORMAL,
                    category=NotificationCategory.SYSTEM
                )
                
                self.persistence_manager.queue_for_offline_user(user_id, notification)
                
                queue_time = time.time() - start_time
                queue_times.append(queue_time)
                self.metrics.record_operation(queue_time, True)
                total_queued += 1
                
                # Measure memory periodically
                if i % 50 == 0:
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    self.metrics.memory_usage.append(current_memory)
        
        # Test queue retrieval performance
        retrieval_times = []
        total_retrieved = 0
        
        for user_id in offline_user_ids:
            start_time = time.time()
            
            pending_notifications = self.persistence_manager.get_pending_notifications(user_id)
            
            retrieval_time = time.time() - start_time
            retrieval_times.append(retrieval_time)
            total_retrieved += len(pending_notifications)
        
        # Test queue cleanup performance
        cleanup_start = time.time()
        cleaned_count = self.persistence_manager.cleanup_old_notifications(retention_days=0)  # Clean all
        cleanup_time = time.time() - cleanup_start
        
        self.metrics.end_measurement()
        
        # Analyze results
        summary = self.metrics.get_summary()
        
        print(f"Queue Management Under Load Results:")
        print(f"  - Offline users: {offline_users}")
        print(f"  - Messages per user: {messages_per_user}")
        print(f"  - Total messages queued: {total_queued}")
        print(f"  - Average queue time: {statistics.mean(queue_times)*1000:.2f}ms")
        print(f"  - Queue throughput: {total_queued/summary['total_time']:.2f} messages/sec")
        print(f"  - Total messages retrieved: {total_retrieved}")
        print(f"  - Average retrieval time: {statistics.mean(retrieval_times)*1000:.2f}ms")
        print(f"  - Messages cleaned up: {cleaned_count}")
        print(f"  - Cleanup time: {cleanup_time*1000:.2f}ms")
        print(f"  - Memory usage: {summary['memory_usage_mb']['start']:.1f}MB -> {summary['memory_usage_mb']['end']:.1f}MB")
        
        # Performance assertions
        self.assertEqual(total_queued, offline_users * messages_per_user, "Should queue all messages")
        self.assertLess(statistics.mean(queue_times), 0.01, "Average queue time should be < 10ms")
        self.assertGreater(total_queued/summary['total_time'], 500, "Queue throughput should be > 500 messages/sec")
        self.assertLess(statistics.mean(retrieval_times), 0.1, "Average retrieval time should be < 100ms")
        
        # Memory usage should be reasonable for queued messages
        memory_growth = summary['memory_usage_mb']['end'] - summary['memory_usage_mb']['start']
        self.assertLess(memory_growth, 200, f"Memory growth should be < 200MB for {total_queued} queued messages")
    
    def test_graceful_degradation_under_high_load(self):
        """Test graceful degradation under high notification volumes"""
        print("\n=== Testing Graceful Degradation Under High Load ===")
        
        # Test parameters - intentionally high to stress the system
        extreme_load_users = 30
        extreme_notifications_per_user = 100
        burst_interval = 0.001  # Very fast burst
        
        self.metrics.start_measurement()
        
        # Create extreme load scenario
        def create_notification_burst(user_index: int) -> Tuple[int, int, List[float]]:
            """Create a burst of notifications for a user"""
            user = self.test_users[user_index % len(self.test_users)]
            success_count = 0
            error_count = 0
            operation_times = []
            
            for i in range(extreme_notifications_per_user):
                start_time = time.time()
                
                notification = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.ERROR,
                    title=f"Load Test {user_index}-{i}",
                    message=f"High load test notification {i}",
                    user_id=user.id,
                    priority=NotificationPriority.HIGH,
                    category=NotificationCategory.SYSTEM
                )
                
                try:
                    success = self.notification_manager.send_user_notification(
                        user.id, notification
                    )
                    
                    operation_time = time.time() - start_time
                    operation_times.append(operation_time)
                    
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
                    operation_times.append(time.time() - start_time)
                
                # Minimal delay for burst effect
                time.sleep(burst_interval)
            
            return success_count, error_count, operation_times
        
        # Execute extreme load test
        with ThreadPoolExecutor(max_workers=extreme_load_users) as executor:
            futures = [
                executor.submit(create_notification_burst, i)
                for i in range(extreme_load_users)
            ]
            
            total_success = 0
            total_errors = 0
            all_operation_times = []
            
            for future in as_completed(futures):
                try:
                    success_count, error_count, operation_times = future.result(timeout=30)
                    total_success += success_count
                    total_errors += error_count
                    all_operation_times.extend(operation_times)
                    
                    # Record metrics
                    for op_time in operation_times:
                        self.metrics.record_operation(op_time, True)
                        
                except Exception as e:
                    print(f"Warning: Future failed with error: {e}")
                    total_errors += extreme_notifications_per_user
        
        # Test system recovery after load
        recovery_start = time.time()
        
        # Send a few normal notifications to test recovery
        recovery_notifications = 10
        recovery_success = 0
        
        for i in range(recovery_notifications):
            user = self.test_users[0]
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.SUCCESS,
                title="Recovery Test",
                message="Testing system recovery after load",
                user_id=user.id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.SYSTEM
            )
            
            if self.notification_manager.send_user_notification(user.id, notification):
                recovery_success += 1
            
            time.sleep(0.1)  # Normal interval
        
        recovery_time = time.time() - recovery_start
        
        self.metrics.end_measurement()
        
        # Analyze results
        summary = self.metrics.get_summary()
        total_attempted = extreme_load_users * extreme_notifications_per_user
        
        print(f"Graceful Degradation Results:")
        print(f"  - Extreme load users: {extreme_load_users}")
        print(f"  - Notifications per user: {extreme_notifications_per_user}")
        print(f"  - Total attempted: {total_attempted}")
        print(f"  - Total successful: {total_success}")
        print(f"  - Total errors: {total_errors}")
        print(f"  - Success rate under load: {(total_success/total_attempted)*100:.2f}%")
        print(f"  - Average operation time: {statistics.mean(all_operation_times)*1000:.2f}ms")
        print(f"  - 95th percentile time: {sorted(all_operation_times)[int(len(all_operation_times)*0.95)]*1000:.2f}ms")
        print(f"  - Recovery success rate: {(recovery_success/recovery_notifications)*100:.2f}%")
        print(f"  - Recovery time: {recovery_time:.2f}s")
        print(f"  - Peak memory usage: {summary['memory_usage_mb']['peak']:.1f}MB")
        print(f"  - Peak CPU usage: {summary['cpu_usage_percent']['peak']:.1f}%")
        
        # Graceful degradation assertions
        # Under extreme load, we expect some degradation but system should remain functional
        success_rate = (total_success / total_attempted) * 100
        self.assertGreater(success_rate, 70.0, "Even under extreme load, success rate should be > 70%")
        
        # System should recover quickly
        recovery_rate = (recovery_success / recovery_notifications) * 100
        self.assertGreater(recovery_rate, 90.0, "System should recover with > 90% success rate")
        self.assertLess(recovery_time, 5.0, "Recovery should complete within 5 seconds")
        
        # Memory and CPU should not be excessive
        self.assertLess(summary['memory_usage_mb']['peak'], 1000, "Peak memory usage should be < 1GB")
        self.assertLess(summary['cpu_usage_percent']['peak'], 90, "Peak CPU usage should be < 90%")
    
    def test_notification_system_statistics_performance(self):
        """Test performance of notification system statistics collection"""
        print("\n=== Testing Notification System Statistics Performance ===")
        
        # Create some test data first
        test_users_count = 10
        notifications_per_user = 50
        
        # Create notifications
        for i in range(test_users_count):
            user = self.test_users[i]
            for j in range(notifications_per_user):
                notification = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Stats Test {j}",
                    message=f"Statistics test notification {j}",
                    user_id=user.id,
                    priority=NotificationPriority.NORMAL,
                    category=NotificationCategory.SYSTEM
                )
                self.notification_manager.send_user_notification(user.id, notification)
        
        self.metrics.start_measurement()
        
        # Test statistics collection performance
        stats_operations = [
            ('notification_manager_stats', lambda: self.notification_manager.get_notification_stats()),
            ('message_router_stats', lambda: self.message_router.get_routing_stats()),
            ('persistence_manager_stats', lambda: self.persistence_manager.get_delivery_stats()),
        ]
        
        stats_times = {}
        
        for operation_name, operation_func in stats_operations:
            operation_times = []
            
            # Run each stats operation multiple times
            for _ in range(10):
                start_time = time.time()
                
                try:
                    stats_result = operation_func()
                    success = 'error' not in stats_result
                except Exception as e:
                    success = False
                    stats_result = {'error': str(e)}
                
                operation_time = time.time() - start_time
                operation_times.append(operation_time)
                self.metrics.record_operation(operation_time, success)
            
            stats_times[operation_name] = {
                'average': statistics.mean(operation_times),
                'min': min(operation_times),
                'max': max(operation_times)
            }
        
        self.metrics.end_measurement()
        
        # Analyze results
        summary = self.metrics.get_summary()
        
        print(f"Statistics Performance Results:")
        for operation_name, times in stats_times.items():
            print(f"  - {operation_name}:")
            print(f"    Average: {times['average']*1000:.2f}ms")
            print(f"    Min: {times['min']*1000:.2f}ms")
            print(f"    Max: {times['max']*1000:.2f}ms")
        
        print(f"  - Overall success rate: {summary['success_rate']:.2f}%")
        print(f"  - Total operations: {summary['total_operations']}")
        
        # Performance assertions for statistics
        self.assertGreater(summary['success_rate'], 95.0, "Statistics collection should have > 95% success rate")
        
        for operation_name, times in stats_times.items():
            self.assertLess(times['average'], 0.1, f"{operation_name} should complete in < 100ms on average")
            self.assertLess(times['max'], 0.5, f"{operation_name} should complete in < 500ms maximum")


if __name__ == '__main__':
    # Run performance tests with detailed output
    unittest.main(verbosity=2, buffer=True)