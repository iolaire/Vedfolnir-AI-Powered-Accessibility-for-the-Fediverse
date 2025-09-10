# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Memory Usage and Resource Monitoring Test Suite

This module provides comprehensive memory usage testing for the notification system,
including memory leak detection, queue management memory efficiency, garbage collection
monitoring, and resource usage under various load conditions.
"""

import unittest
import gc
import time
import threading
import uuid
import statistics
import tracemalloc
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import psutil
import sys

# Test framework imports
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import UserRole, NotificationType, NotificationPriority, NotificationCategory

# Notification system imports
from app.services.notification.manager.unified_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from notification_message_router import NotificationMessageRouter
from app.services.notification.components.notification_persistence_manager import NotificationPersistenceManager
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager


class MemoryProfiler:
    """Memory profiling and monitoring utility"""
    
    def __init__(self):
        self.snapshots = []
        self.start_memory = None
        self.peak_memory = 0
        self.gc_stats = []
        self.tracemalloc_enabled = False
        
    def start_profiling(self):
        """Start memory profiling"""
        # Start tracemalloc for detailed memory tracking
        tracemalloc.start()
        self.tracemalloc_enabled = True
        
        # Record initial memory state
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        
        # Record initial GC stats
        self.gc_stats.append({
            'timestamp': time.time(),
            'collections': gc.get_stats(),
            'objects': len(gc.get_objects())
        })
        
    def take_snapshot(self, label: str = None):
        """Take a memory snapshot"""
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = max(self.peak_memory, current_memory)
        
        snapshot = {
            'timestamp': time.time(),
            'label': label or f"snapshot_{len(self.snapshots)}",
            'memory_mb': current_memory,
            'objects': len(gc.get_objects()),
        }
        
        if self.tracemalloc_enabled:
            snapshot['tracemalloc'] = tracemalloc.take_snapshot()
            
        self.snapshots.append(snapshot)
        
        # Record GC stats
        self.gc_stats.append({
            'timestamp': time.time(),
            'collections': gc.get_stats(),
            'objects': len(gc.get_objects())
        })
        
    def stop_profiling(self):
        """Stop memory profiling"""
        if self.tracemalloc_enabled:
            tracemalloc.stop()
            self.tracemalloc_enabled = False
            
    def get_memory_growth(self) -> float:
        """Get total memory growth in MB"""
        if not self.snapshots:
            return 0.0
        return self.snapshots[-1]['memory_mb'] - self.start_memory
        
    def get_peak_memory_usage(self) -> float:
        """Get peak memory usage in MB"""
        return self.peak_memory
        
    def detect_memory_leaks(self) -> Dict[str, Any]:
        """Detect potential memory leaks"""
        if len(self.snapshots) < 2:
            return {'error': 'Insufficient snapshots for leak detection'}
            
        # Analyze memory growth pattern
        memory_values = [s['memory_mb'] for s in self.snapshots]
        object_counts = [s['objects'] for s in self.snapshots]
        
        # Calculate growth rates
        memory_growth_rate = (memory_values[-1] - memory_values[0]) / len(memory_values)
        object_growth_rate = (object_counts[-1] - object_counts[0]) / len(object_counts)
        
        # Analyze tracemalloc data if available
        leak_analysis = {}
        if self.tracemalloc_enabled and len(self.snapshots) >= 2:
            first_snapshot = self.snapshots[0].get('tracemalloc')
            last_snapshot = self.snapshots[-1].get('tracemalloc')
            
            if first_snapshot and last_snapshot:
                top_stats = last_snapshot.compare_to(first_snapshot, 'lineno')
                leak_analysis['top_memory_growth'] = [
                    {
                        'filename': stat.traceback.format()[0] if stat.traceback else 'unknown',
                        'size_diff_mb': stat.size_diff / 1024 / 1024,
                        'count_diff': stat.count_diff
                    }
                    for stat in top_stats[:10]  # Top 10 memory growth sources
                ]
        
        return {
            'memory_growth_rate_mb_per_snapshot': memory_growth_rate,
            'object_growth_rate_per_snapshot': object_growth_rate,
            'total_memory_growth_mb': memory_values[-1] - memory_values[0],
            'total_object_growth': object_counts[-1] - object_counts[0],
            'potential_leak': memory_growth_rate > 1.0 or object_growth_rate > 100,
            'leak_analysis': leak_analysis
        }
        
    def get_gc_analysis(self) -> Dict[str, Any]:
        """Analyze garbage collection statistics"""
        if len(self.gc_stats) < 2:
            return {'error': 'Insufficient GC data'}
            
        first_stats = self.gc_stats[0]
        last_stats = self.gc_stats[-1]
        
        # Calculate GC activity
        gc_activity = {}
        for i, (first_gen, last_gen) in enumerate(zip(first_stats['collections'], last_stats['collections'])):
            gc_activity[f'generation_{i}'] = {
                'collections_increase': last_gen['collections'] - first_gen['collections'],
                'collected_increase': last_gen['collected'] - first_gen['collected'],
                'uncollectable_increase': last_gen['uncollectable'] - first_gen['uncollectable']
            }
            
        return {
            'gc_activity': gc_activity,
            'object_count_change': last_stats['objects'] - first_stats['objects'],
            'monitoring_duration': last_stats['timestamp'] - first_stats['timestamp']
        }
        
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive memory profiling summary"""
        return {
            'start_memory_mb': self.start_memory,
            'peak_memory_mb': self.peak_memory,
            'final_memory_mb': self.snapshots[-1]['memory_mb'] if self.snapshots else self.start_memory,
            'total_growth_mb': self.get_memory_growth(),
            'snapshots_taken': len(self.snapshots),
            'leak_detection': self.detect_memory_leaks(),
            'gc_analysis': self.get_gc_analysis()
        }


class MemoryUsageTestSuite(unittest.TestCase):
    """
    Comprehensive memory usage and resource monitoring test suite
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        
        # Create test users for memory testing
        cls.test_users = []
        cls.user_helpers = []
        
        # Create unique timestamp for test users
        import time
        timestamp = int(time.time())
        
        # Create test users
        for i in range(20):  # Create 20 test users for memory testing
            user, helper = create_test_user_with_platforms(
                cls.db_manager,
                username=f"mem_test_user_{timestamp}_{i}",
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
        self.profiler = MemoryProfiler()
        
        # Force garbage collection before each test
        gc.collect()
        
    def tearDown(self):
        """Clean up individual test"""
        self.profiler.stop_profiling()
        
        # Force garbage collection after each test
        gc.collect()
    
    def test_notification_creation_memory_usage(self):
        """Test memory usage during notification creation and processing"""
        print("\n=== Testing Notification Creation Memory Usage ===")
        
        self.profiler.start_profiling()
        self.profiler.take_snapshot("initial")
        
        # Test parameters
        notification_batches = 10
        notifications_per_batch = 100
        
        for batch in range(notification_batches):
            batch_start_time = time.time()
            
            # Create batch of notifications
            notifications = []
            for i in range(notifications_per_batch):
                user = self.test_users[i % len(self.test_users)]
                notification = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Memory Test Batch {batch} Notification {i}",
                    message=f"Testing memory usage for notification {i} in batch {batch}",
                    user_id=user.id,
                    priority=NotificationPriority.NORMAL,
                    category=NotificationCategory.SYSTEM,
                    data={'batch': batch, 'index': i, 'test_data': 'x' * 100}  # Add some data
                )
                notifications.append(notification)
            
            # Process notifications
            for notification in notifications:
                self.notification_manager.send_user_notification(
                    notification.user_id, notification
                )
            
            # Take memory snapshot after each batch
            self.profiler.take_snapshot(f"batch_{batch}")
            
            # Force garbage collection periodically
            if batch % 3 == 0:
                gc.collect()
                self.profiler.take_snapshot(f"batch_{batch}_after_gc")
            
            batch_time = time.time() - batch_start_time
            print(f"Batch {batch}: {notifications_per_batch} notifications in {batch_time:.2f}s")
        
        # Final cleanup and measurement
        gc.collect()
        self.profiler.take_snapshot("final")
        
        # Analyze results
        summary = self.profiler.get_summary()
        leak_detection = summary['leak_detection']
        
        total_notifications = notification_batches * notifications_per_batch
        
        print(f"Notification Creation Memory Results:")
        print(f"  - Total notifications created: {total_notifications}")
        print(f"  - Start memory: {summary['start_memory_mb']:.1f}MB")
        print(f"  - Peak memory: {summary['peak_memory_mb']:.1f}MB")
        print(f"  - Final memory: {summary['final_memory_mb']:.1f}MB")
        print(f"  - Total growth: {summary['total_growth_mb']:.1f}MB")
        print(f"  - Memory per notification: {summary['total_growth_mb']/total_notifications*1024:.2f}KB")
        print(f"  - Memory growth rate: {leak_detection['memory_growth_rate_mb_per_snapshot']:.3f}MB/snapshot")
        print(f"  - Object growth rate: {leak_detection['object_growth_rate_per_snapshot']:.1f} objects/snapshot")
        print(f"  - Potential leak detected: {leak_detection['potential_leak']}")
        
        # Memory usage assertions
        memory_per_notification = summary['total_growth_mb'] / total_notifications * 1024  # KB
        self.assertLess(memory_per_notification, 10, "Memory per notification should be < 10KB")
        self.assertLess(summary['total_growth_mb'], 50, f"Total memory growth should be < 50MB for {total_notifications} notifications")
        self.assertFalse(leak_detection['potential_leak'], "No significant memory leak should be detected")
    
    def test_offline_queue_memory_efficiency(self):
        """Test memory efficiency of offline notification queues"""
        print("\n=== Testing Offline Queue Memory Efficiency ===")
        
        self.profiler.start_profiling()
        self.profiler.take_snapshot("initial")
        
        # Test parameters
        offline_users = 10
        messages_per_user_batch = 50
        batches = 5
        
        offline_user_ids = [user.id for user in self.test_users[:offline_users]]
        
        for batch in range(batches):
            batch_start_time = time.time()
            
            # Queue messages for offline users
            for user_id in offline_user_ids:
                for i in range(messages_per_user_batch):
                    notification = NotificationMessage(
                        id=str(uuid.uuid4()),
                        type=NotificationType.WARNING,
                        title=f"Offline Queue Test Batch {batch} Message {i}",
                        message=f"Queued message {i} for offline user {user_id} in batch {batch}",
                        user_id=user_id,
                        priority=NotificationPriority.NORMAL,
                        category=NotificationCategory.SYSTEM,
                        data={'batch': batch, 'message_index': i, 'payload': 'y' * 200}
                    )
                    
                    self.persistence_manager.queue_for_offline_user(user_id, notification)
            
            # Take snapshot after each batch
            self.profiler.take_snapshot(f"queue_batch_{batch}")
            
            batch_time = time.time() - batch_start_time
            messages_in_batch = offline_users * messages_per_user_batch
            print(f"Queue Batch {batch}: {messages_in_batch} messages queued in {batch_time:.2f}s")
        
        # Test queue retrieval memory impact
        retrieval_start_time = time.time()
        
        for user_id in offline_user_ids:
            pending_notifications = self.persistence_manager.get_pending_notifications(user_id)
            print(f"User {user_id}: {len(pending_notifications)} pending notifications")
        
        retrieval_time = time.time() - retrieval_start_time
        self.profiler.take_snapshot("after_retrieval")
        
        # Test queue cleanup memory impact
        cleanup_start_time = time.time()
        cleaned_count = self.persistence_manager.cleanup_old_notifications(retention_days=0)
        cleanup_time = time.time() - cleanup_start_time
        
        gc.collect()
        self.profiler.take_snapshot("after_cleanup")
        
        # Analyze results
        summary = self.profiler.get_summary()
        leak_detection = summary['leak_detection']
        
        total_messages = offline_users * messages_per_user_batch * batches
        
        print(f"Offline Queue Memory Efficiency Results:")
        print(f"  - Offline users: {offline_users}")
        print(f"  - Total messages queued: {total_messages}")
        print(f"  - Messages cleaned up: {cleaned_count}")
        print(f"  - Start memory: {summary['start_memory_mb']:.1f}MB")
        print(f"  - Peak memory: {summary['peak_memory_mb']:.1f}MB")
        print(f"  - Final memory: {summary['final_memory_mb']:.1f}MB")
        print(f"  - Total growth: {summary['total_growth_mb']:.1f}MB")
        print(f"  - Memory per queued message: {summary['total_growth_mb']/total_messages*1024:.2f}KB")
        print(f"  - Retrieval time: {retrieval_time:.2f}s")
        print(f"  - Cleanup time: {cleanup_time:.2f}s")
        print(f"  - Potential leak detected: {leak_detection['potential_leak']}")
        
        # Memory efficiency assertions
        memory_per_message = summary['total_growth_mb'] / total_messages * 1024  # KB
        self.assertLess(memory_per_message, 15, "Memory per queued message should be < 15KB")
        self.assertLess(summary['total_growth_mb'], 100, f"Total memory growth should be < 100MB for {total_messages} queued messages")
        self.assertFalse(leak_detection['potential_leak'], "No significant memory leak should be detected in queue operations")
    
    def test_concurrent_operations_memory_impact(self):
        """Test memory impact of concurrent notification operations"""
        print("\n=== Testing Concurrent Operations Memory Impact ===")
        
        self.profiler.start_profiling()
        self.profiler.take_snapshot("initial")
        
        # Test parameters
        concurrent_threads = 8
        operations_per_thread = 50
        
        def concurrent_notification_operations(thread_id: int) -> Dict[str, Any]:
            """Perform concurrent notification operations"""
            operations_completed = 0
            errors = 0
            
            for i in range(operations_per_thread):
                try:
                    user = self.test_users[i % len(self.test_users)]
                    
                    # Create notification
                    notification = NotificationMessage(
                        id=str(uuid.uuid4()),
                        type=NotificationType.SUCCESS,
                        title=f"Concurrent Test Thread {thread_id} Op {i}",
                        message=f"Concurrent operation {i} from thread {thread_id}",
                        user_id=user.id,
                        priority=NotificationPriority.NORMAL,
                        category=NotificationCategory.USER,
                        data={'thread_id': thread_id, 'operation': i}
                    )
                    
                    # Send notification
                    success = self.notification_manager.send_user_notification(
                        user.id, notification
                    )
                    
                    if success:
                        operations_completed += 1
                    else:
                        errors += 1
                    
                    # Simulate some processing time
                    time.sleep(0.01)
                    
                except Exception as e:
                    errors += 1
            
            return {
                'thread_id': thread_id,
                'operations_completed': operations_completed,
                'errors': errors
            }
        
        # Execute concurrent operations
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
            futures = [
                executor.submit(concurrent_notification_operations, i)
                for i in range(concurrent_threads)
            ]
            
            # Take snapshots during execution
            for i, future in enumerate(futures):
                if i % 2 == 0:  # Take snapshot every 2 threads
                    self.profiler.take_snapshot(f"concurrent_progress_{i}")
            
            # Collect results
            results = [future.result() for future in futures]
        
        execution_time = time.time() - start_time
        
        # Take final snapshots
        self.profiler.take_snapshot("concurrent_complete")
        gc.collect()
        self.profiler.take_snapshot("concurrent_after_gc")
        
        # Analyze results
        summary = self.profiler.get_summary()
        leak_detection = summary['leak_detection']
        gc_analysis = summary['gc_analysis']
        
        total_operations = sum(r['operations_completed'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        
        print(f"Concurrent Operations Memory Impact Results:")
        print(f"  - Concurrent threads: {concurrent_threads}")
        print(f"  - Operations per thread: {operations_per_thread}")
        print(f"  - Total operations completed: {total_operations}")
        print(f"  - Total errors: {total_errors}")
        print(f"  - Execution time: {execution_time:.2f}s")
        print(f"  - Operations per second: {total_operations/execution_time:.2f}")
        print(f"  - Start memory: {summary['start_memory_mb']:.1f}MB")
        print(f"  - Peak memory: {summary['peak_memory_mb']:.1f}MB")
        print(f"  - Final memory: {summary['final_memory_mb']:.1f}MB")
        print(f"  - Total growth: {summary['total_growth_mb']:.1f}MB")
        print(f"  - Memory per operation: {summary['total_growth_mb']/total_operations*1024:.2f}KB" if total_operations > 0 else "N/A")
        print(f"  - GC object count change: {gc_analysis.get('object_count_change', 'N/A')}")
        print(f"  - Potential leak detected: {leak_detection['potential_leak']}")
        
        # Concurrent operations assertions
        success_rate = total_operations / (total_operations + total_errors) if total_operations + total_errors > 0 else 0
        self.assertGreater(success_rate, 0.95, "Concurrent operations should have > 95% success rate")
        self.assertLess(summary['total_growth_mb'], 30, "Memory growth should be < 30MB for concurrent operations")
        self.assertFalse(leak_detection['potential_leak'], "No memory leak should be detected during concurrent operations")
    
    def test_long_running_memory_stability(self):
        """Test memory stability during long-running operations"""
        print("\n=== Testing Long-Running Memory Stability ===")
        
        self.profiler.start_profiling()
        self.profiler.take_snapshot("initial")
        
        # Test parameters
        test_duration = 30  # seconds
        operation_interval = 0.1  # seconds between operations
        
        start_time = time.time()
        operations_completed = 0
        
        while time.time() - start_time < test_duration:
            try:
                # Perform various notification operations
                user = self.test_users[operations_completed % len(self.test_users)]
                
                # Create and send notification
                notification = NotificationMessage(
                    id=str(uuid.uuid4()),
                    type=NotificationType.INFO,
                    title=f"Long Running Test {operations_completed}",
                    message=f"Long running stability test notification {operations_completed}",
                    user_id=user.id,
                    priority=NotificationPriority.NORMAL,
                    category=NotificationCategory.SYSTEM
                )
                
                self.notification_manager.send_user_notification(user.id, notification)
                operations_completed += 1
                
                # Take periodic snapshots
                if operations_completed % 50 == 0:
                    self.profiler.take_snapshot(f"long_running_{operations_completed}")
                    
                    # Periodic cleanup
                    if operations_completed % 100 == 0:
                        gc.collect()
                        self.profiler.take_snapshot(f"long_running_{operations_completed}_gc")
                
                time.sleep(operation_interval)
                
            except Exception as e:
                print(f"Error in long-running test: {e}")
        
        # Final measurements
        total_time = time.time() - start_time
        gc.collect()
        self.profiler.take_snapshot("long_running_final")
        
        # Analyze results
        summary = self.profiler.get_summary()
        leak_detection = summary['leak_detection']
        
        print(f"Long-Running Memory Stability Results:")
        print(f"  - Test duration: {total_time:.2f}s")
        print(f"  - Operations completed: {operations_completed}")
        print(f"  - Operations per second: {operations_completed/total_time:.2f}")
        print(f"  - Start memory: {summary['start_memory_mb']:.1f}MB")
        print(f"  - Peak memory: {summary['peak_memory_mb']:.1f}MB")
        print(f"  - Final memory: {summary['final_memory_mb']:.1f}MB")
        print(f"  - Total growth: {summary['total_growth_mb']:.1f}MB")
        print(f"  - Growth rate: {summary['total_growth_mb']/total_time:.3f}MB/sec")
        print(f"  - Memory growth rate per snapshot: {leak_detection['memory_growth_rate_mb_per_snapshot']:.3f}MB")
        print(f"  - Potential leak detected: {leak_detection['potential_leak']}")
        
        # Long-running stability assertions
        growth_rate_per_second = summary['total_growth_mb'] / total_time
        self.assertLess(growth_rate_per_second, 0.5, "Memory growth rate should be < 0.5MB/sec for long-running operations")
        self.assertLess(summary['total_growth_mb'], 20, "Total memory growth should be < 20MB for 30-second test")
        self.assertFalse(leak_detection['potential_leak'], "No memory leak should be detected in long-running operations")
    
    def test_garbage_collection_effectiveness(self):
        """Test garbage collection effectiveness with notification system"""
        print("\n=== Testing Garbage Collection Effectiveness ===")
        
        self.profiler.start_profiling()
        self.profiler.take_snapshot("initial")
        
        # Create a large number of notifications to stress GC
        stress_notifications = 500
        
        # Phase 1: Create many notifications without GC
        print("Phase 1: Creating notifications without GC...")
        for i in range(stress_notifications):
            user = self.test_users[i % len(self.test_users)]
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.WARNING,
                title=f"GC Test Notification {i}",
                message=f"Testing garbage collection with notification {i}",
                user_id=user.id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.SYSTEM,
                data={'large_data': 'x' * 1000}  # Add large data to stress memory
            )
            
            self.notification_manager.send_user_notification(user.id, notification)
            
            if i % 100 == 0:
                self.profiler.take_snapshot(f"stress_phase1_{i}")
        
        self.profiler.take_snapshot("before_gc")
        
        # Phase 2: Force garbage collection
        print("Phase 2: Forcing garbage collection...")
        gc_start_time = time.time()
        
        # Collect all generations
        collected_counts = []
        for generation in range(3):
            collected = gc.collect(generation)
            collected_counts.append(collected)
        
        gc_time = time.time() - gc_start_time
        self.profiler.take_snapshot("after_gc")
        
        # Phase 3: Create more notifications after GC
        print("Phase 3: Creating notifications after GC...")
        for i in range(100):  # Smaller number after GC
            user = self.test_users[i % len(self.test_users)]
            notification = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.SUCCESS,
                title=f"Post-GC Test Notification {i}",
                message=f"Testing after garbage collection with notification {i}",
                user_id=user.id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.SYSTEM
            )
            
            self.notification_manager.send_user_notification(user.id, notification)
        
        self.profiler.take_snapshot("final")
        
        # Analyze results
        summary = self.profiler.get_summary()
        gc_analysis = summary['gc_analysis']
        
        # Calculate GC effectiveness
        memory_before_gc = None
        memory_after_gc = None
        
        for snapshot in self.profiler.snapshots:
            if snapshot['label'] == 'before_gc':
                memory_before_gc = snapshot['memory_mb']
            elif snapshot['label'] == 'after_gc':
                memory_after_gc = snapshot['memory_mb']
        
        gc_effectiveness = 0
        if memory_before_gc and memory_after_gc:
            gc_effectiveness = ((memory_before_gc - memory_after_gc) / memory_before_gc) * 100
        
        print(f"Garbage Collection Effectiveness Results:")
        print(f"  - Stress notifications created: {stress_notifications}")
        print(f"  - GC time: {gc_time*1000:.2f}ms")
        print(f"  - Objects collected by generation: {collected_counts}")
        print(f"  - Memory before GC: {memory_before_gc:.1f}MB" if memory_before_gc else "N/A")
        print(f"  - Memory after GC: {memory_after_gc:.1f}MB" if memory_after_gc else "N/A")
        print(f"  - GC effectiveness: {gc_effectiveness:.2f}%" if gc_effectiveness else "N/A")
        print(f"  - Start memory: {summary['start_memory_mb']:.1f}MB")
        print(f"  - Peak memory: {summary['peak_memory_mb']:.1f}MB")
        print(f"  - Final memory: {summary['final_memory_mb']:.1f}MB")
        print(f"  - Total growth: {summary['total_growth_mb']:.1f}MB")
        
        # GC effectiveness assertions
        self.assertGreater(sum(collected_counts), 0, "Garbage collection should collect some objects")
        self.assertLess(gc_time, 1.0, "Garbage collection should complete in < 1 second")
        
        if gc_effectiveness:
            self.assertGreater(gc_effectiveness, 5, "Garbage collection should free > 5% of memory")


if __name__ == '__main__':
    # Run memory usage tests with detailed output
    unittest.main(verbosity=2, buffer=True)