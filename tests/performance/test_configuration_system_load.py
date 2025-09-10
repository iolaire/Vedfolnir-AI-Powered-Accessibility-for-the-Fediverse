# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration System Load Testing

Tests configuration system performance under high load including:
- High-frequency configuration access patterns
- Cache performance and memory usage under sustained load
- Event bus performance with multiple simultaneous changes
- Configuration service scalability and resource usage
- Stress tests for configuration change propagation
"""

import unittest
import time
import threading
import psutil
import os
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import SystemConfiguration
from app.core.configuration.core.configuration_service import ConfigurationService, ConfigurationSource
from app.core.configuration.cache.configuration_cache import ConfigurationCache
from app.core.configuration.events.configuration_event_bus import ConfigurationEventBus


class TestConfigurationSystemLoad(unittest.TestCase):
    """Load testing for configuration system components"""
    
    def setUp(self):
        """Set up test environment for load testing"""
        self.config = Config()
        
        # Mock database manager
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_mock = Mock()
        
        # Mock the context manager properly
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=self.session_mock)
        context_manager.__exit__ = Mock(return_value=None)
        self.db_manager.get_session.return_value = context_manager
        
        # Create configuration service with larger cache for load testing
        self.config_service = ConfigurationService(
            self.db_manager,
            cache_size=10000,  # Large cache for load testing
            default_ttl=300
        )
        
        # Create event bus for testing
        self.event_bus = ConfigurationEventBus()
        
        # Set up test configurations
        self._setup_test_configurations()
        
        # Performance tracking
        self.performance_metrics = {
            'access_times': [],
            'cache_hit_rates': [],
            'memory_usage': [],
            'event_propagation_times': []
        }
    
    def _setup_test_configurations(self):
        """Set up test configurations for load testing"""
        self.test_configs = {}
        
        # Create 1000 test configurations
        for i in range(1000):
            key = f"test_config_{i:04d}"
            mock_config = Mock(spec=SystemConfiguration)
            mock_config.key = key
            mock_config.value = f"value_{i}"
            mock_config.data_type = "string"
            mock_config.get_typed_value.return_value = f"value_{i}"
            mock_config.updated_at = datetime.now(timezone.utc)
            
            self.test_configs[key] = mock_config
        
        # Mock database queries
        def mock_query_filter_by(key):
            mock_query = Mock()
            mock_query.first.return_value = self.test_configs.get(key)
            return mock_query
        
        self.session_mock.query.return_value.filter_by = mock_query_filter_by
    
    def test_high_frequency_configuration_access(self):
        """Test high-frequency configuration access patterns"""
        num_requests = 10000
        num_threads = 10
        requests_per_thread = num_requests // num_threads
        
        results = []
        errors = []
        
        def worker_thread(thread_id: int):
            """Worker thread for high-frequency access"""
            thread_results = []
            thread_errors = []
            
            for i in range(requests_per_thread):
                try:
                    start_time = time.time()
                    
                    # Access random configuration
                    config_key = f"test_config_{(thread_id * requests_per_thread + i) % 100:04d}"
                    value = self.config_service.get_config(config_key)
                    
                    end_time = time.time()
                    access_time = end_time - start_time
                    
                    thread_results.append({
                        'thread_id': thread_id,
                        'request_id': i,
                        'config_key': config_key,
                        'value': value,
                        'access_time': access_time
                    })
                    
                except Exception as e:
                    thread_errors.append({
                        'thread_id': thread_id,
                        'request_id': i,
                        'error': str(e)
                    })
            
            return thread_results, thread_errors
        
        # Execute load test
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(worker_thread, i) 
                for i in range(num_threads)
            ]
            
            for future in as_completed(futures):
                thread_results, thread_errors = future.result()
                results.extend(thread_results)
                errors.extend(thread_errors)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        self.assertEqual(len(errors), 0, f"Errors during load test: {errors[:5]}")
        self.assertEqual(len(results), num_requests)
        
        # Performance assertions
        avg_access_time = sum(r['access_time'] for r in results) / len(results)
        max_access_time = max(r['access_time'] for r in results)
        
        print(f"High-frequency access test results:")
        print(f"  Total requests: {num_requests}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Requests per second: {num_requests / total_time:.2f}")
        print(f"  Average access time: {avg_access_time * 1000:.2f}ms")
        print(f"  Max access time: {max_access_time * 1000:.2f}ms")
        
        # Performance requirements
        self.assertLess(avg_access_time, 0.01)  # Average < 10ms
        self.assertLess(max_access_time, 0.1)   # Max < 100ms
        self.assertGreater(num_requests / total_time, 100)  # > 100 RPS
    
    def test_cache_performance_under_sustained_load(self):
        """Test cache performance and memory usage under sustained load"""
        duration_seconds = 30
        access_interval = 0.001  # 1ms between accesses
        
        results = []
        memory_samples = []
        
        def memory_monitor():
            """Monitor memory usage during test"""
            process = psutil.Process(os.getpid())
            
            while not stop_monitoring.is_set():
                memory_info = process.memory_info()
                memory_samples.append({
                    'timestamp': time.time(),
                    'rss': memory_info.rss,
                    'vms': memory_info.vms
                })
                time.sleep(0.1)  # Sample every 100ms
        
        stop_monitoring = threading.Event()
        
        # Start memory monitoring
        monitor_thread = threading.Thread(target=memory_monitor)
        monitor_thread.start()
        
        try:
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < duration_seconds:
                # Access configuration with varying patterns
                config_key = f"test_config_{request_count % 100:04d}"
                
                access_start = time.time()
                value = self.config_service.get_config(config_key)
                access_end = time.time()
                
                results.append({
                    'request_id': request_count,
                    'config_key': config_key,
                    'access_time': access_end - access_start,
                    'timestamp': access_end
                })
                
                request_count += 1
                time.sleep(access_interval)
            
        finally:
            stop_monitoring.set()
            monitor_thread.join(timeout=5.0)
        
        # Analyze cache performance
        cache_stats = self.config_service.get_cache_stats()
        
        print(f"Sustained load test results:")
        print(f"  Duration: {duration_seconds}s")
        print(f"  Total requests: {request_count}")
        print(f"  Cache hit rate: {cache_stats['hit_rate']:.2%}")
        print(f"  Cache size: {cache_stats['cache']['size']}")
        print(f"  Memory samples: {len(memory_samples)}")
        
        if memory_samples:
            initial_memory = memory_samples[0]['rss']
            final_memory = memory_samples[-1]['rss']
            max_memory = max(sample['rss'] for sample in memory_samples)
            
            print(f"  Initial memory: {initial_memory / 1024 / 1024:.2f}MB")
            print(f"  Final memory: {final_memory / 1024 / 1024:.2f}MB")
            print(f"  Max memory: {max_memory / 1024 / 1024:.2f}MB")
            print(f"  Memory growth: {(final_memory - initial_memory) / 1024 / 1024:.2f}MB")
        
        # Performance assertions
        self.assertGreater(cache_stats['hit_rate'], 0.8)  # >80% hit rate
        self.assertLess(cache_stats['cache']['size'], 1000)  # Cache size reasonable
        
        # Memory growth should be reasonable
        if memory_samples:
            memory_growth = final_memory - initial_memory
            self.assertLess(memory_growth, 50 * 1024 * 1024)  # <50MB growth
    
    def test_event_bus_performance_multiple_changes(self):
        """Test event bus performance with multiple simultaneous changes"""
        num_events = 1000
        num_subscribers = 50
        
        events_received = []
        event_times = []
        
        def create_subscriber(subscriber_id: int):
            """Create a subscriber function"""
            def subscriber(key: str, old_value: Any, new_value: Any):
                receive_time = time.time()
                events_received.append({
                    'subscriber_id': subscriber_id,
                    'key': key,
                    'old_value': old_value,
                    'new_value': new_value,
                    'receive_time': receive_time
                })
            return subscriber
        
        # Set up subscribers
        subscription_ids = []
        for i in range(num_subscribers):
            subscriber = create_subscriber(i)
            subscription_id = self.event_bus.subscribe("test_key", subscriber)
            subscription_ids.append(subscription_id)
        
        try:
            # Publish events rapidly
            start_time = time.time()
            
            for i in range(num_events):
                publish_start = time.time()
                self.event_bus.publish_change("test_key", f"old_{i}", f"new_{i}")
                publish_end = time.time()
                
                event_times.append({
                    'event_id': i,
                    'publish_time': publish_end - publish_start,
                    'timestamp': publish_end
                })
            
            # Wait for all events to be processed
            time.sleep(1.0)
            
            end_time = time.time()
            total_time = end_time - start_time
            
        finally:
            # Clean up subscriptions
            for subscription_id in subscription_ids:
                self.event_bus.unsubscribe(subscription_id)
        
        # Analyze results
        expected_total_events = num_events * num_subscribers
        
        print(f"Event bus performance test results:")
        print(f"  Events published: {num_events}")
        print(f"  Subscribers: {num_subscribers}")
        print(f"  Expected total events: {expected_total_events}")
        print(f"  Actual events received: {len(events_received)}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Events per second: {num_events / total_time:.2f}")
        
        if event_times:
            avg_publish_time = sum(e['publish_time'] for e in event_times) / len(event_times)
            max_publish_time = max(e['publish_time'] for e in event_times)
            
            print(f"  Average publish time: {avg_publish_time * 1000:.2f}ms")
            print(f"  Max publish time: {max_publish_time * 1000:.2f}ms")
        
        # Performance assertions
        self.assertEqual(len(events_received), expected_total_events)
        self.assertLess(total_time, 10.0)  # Should complete in under 10 seconds
        
        if event_times:
            avg_publish_time = sum(e['publish_time'] for e in event_times) / len(event_times)
            self.assertLess(avg_publish_time, 0.01)  # Average publish time < 10ms
    
    def test_configuration_service_scalability(self):
        """Test configuration service scalability with increasing load"""
        load_levels = [10, 50, 100, 500, 1000]
        scalability_results = []
        
        for load_level in load_levels:
            print(f"Testing scalability at load level: {load_level}")
            
            # Reset cache for each test
            self.config_service.refresh_config()
            gc.collect()  # Force garbage collection
            
            results = []
            errors = []
            
            def worker(worker_id: int):
                """Worker function for scalability test"""
                worker_results = []
                worker_errors = []
                
                for i in range(10):  # 10 requests per worker
                    try:
                        start_time = time.time()
                        config_key = f"test_config_{(worker_id * 10 + i) % 100:04d}"
                        value = self.config_service.get_config(config_key)
                        end_time = time.time()
                        
                        worker_results.append({
                            'worker_id': worker_id,
                            'request_id': i,
                            'access_time': end_time - start_time
                        })
                        
                    except Exception as e:
                        worker_errors.append({
                            'worker_id': worker_id,
                            'request_id': i,
                            'error': str(e)
                        })
                
                return worker_results, worker_errors
            
            # Execute test at current load level
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=load_level) as executor:
                futures = [executor.submit(worker, i) for i in range(load_level)]
                
                for future in as_completed(futures):
                    worker_results, worker_errors = future.result()
                    results.extend(worker_results)
                    errors.extend(worker_errors)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate metrics
            total_requests = len(results)
            avg_access_time = sum(r['access_time'] for r in results) / total_requests if results else 0
            throughput = total_requests / total_time if total_time > 0 else 0
            error_rate = len(errors) / (len(results) + len(errors)) if (results or errors) else 0
            
            cache_stats = self.config_service.get_cache_stats()
            
            scalability_results.append({
                'load_level': load_level,
                'total_requests': total_requests,
                'total_time': total_time,
                'avg_access_time': avg_access_time,
                'throughput': throughput,
                'error_rate': error_rate,
                'cache_hit_rate': cache_stats['hit_rate']
            })
            
            print(f"  Requests: {total_requests}, Time: {total_time:.2f}s")
            print(f"  Throughput: {throughput:.2f} RPS")
            print(f"  Avg access time: {avg_access_time * 1000:.2f}ms")
            print(f"  Error rate: {error_rate:.2%}")
            print(f"  Cache hit rate: {cache_stats['hit_rate']:.2%}")
        
        # Analyze scalability
        print(f"\\nScalability analysis:")
        for result in scalability_results:
            print(f"  Load {result['load_level']:4d}: "
                  f"{result['throughput']:8.2f} RPS, "
                  f"{result['avg_access_time'] * 1000:6.2f}ms avg, "
                  f"{result['error_rate']:6.2%} errors")
        
        # Performance assertions
        for result in scalability_results:
            self.assertEqual(result['error_rate'], 0.0)  # No errors
            self.assertLess(result['avg_access_time'], 0.1)  # <100ms average
            self.assertGreater(result['throughput'], 10)  # >10 RPS minimum
    
    def test_stress_configuration_change_propagation(self):
        """Test stress conditions for configuration change propagation"""
        num_changes = 500
        num_subscribers_per_key = 20
        num_keys = 10
        
        all_events_received = []
        propagation_times = []
        
        def create_subscriber(key: str, subscriber_id: int):
            """Create a subscriber for stress testing"""
            def subscriber(changed_key: str, old_value: Any, new_value: Any):
                receive_time = time.time()
                all_events_received.append({
                    'key': key,
                    'subscriber_id': subscriber_id,
                    'changed_key': changed_key,
                    'old_value': old_value,
                    'new_value': new_value,
                    'receive_time': receive_time
                })
            return subscriber
        
        # Set up subscribers for multiple keys
        subscription_ids = []
        for key_id in range(num_keys):
            key = f"stress_test_key_{key_id}"
            for sub_id in range(num_subscribers_per_key):
                subscriber = create_subscriber(key, sub_id)
                subscription_id = self.config_service.subscribe_to_changes(key, subscriber)
                subscription_ids.append(subscription_id)
        
        try:
            # Generate rapid configuration changes
            start_time = time.time()
            
            for change_id in range(num_changes):
                key = f"stress_test_key_{change_id % num_keys}"
                old_value = f"old_value_{change_id}"
                new_value = f"new_value_{change_id}"
                
                change_start = time.time()
                self.config_service.notify_change(key, old_value, new_value)
                change_end = time.time()
                
                propagation_times.append({
                    'change_id': change_id,
                    'key': key,
                    'propagation_time': change_end - change_start,
                    'timestamp': change_end
                })
                
                # Small delay to prevent overwhelming the system
                if change_id % 50 == 0:
                    time.sleep(0.01)
            
            # Wait for all events to propagate
            time.sleep(2.0)
            
            end_time = time.time()
            total_time = end_time - start_time
            
        finally:
            # Clean up subscriptions
            for subscription_id in subscription_ids:
                self.config_service.unsubscribe(subscription_id)
        
        # Analyze stress test results
        expected_events = num_changes * num_subscribers_per_key
        
        print(f"Stress test results:")
        print(f"  Configuration changes: {num_changes}")
        print(f"  Keys: {num_keys}")
        print(f"  Subscribers per key: {num_subscribers_per_key}")
        print(f"  Expected events: {expected_events}")
        print(f"  Actual events received: {len(all_events_received)}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Changes per second: {num_changes / total_time:.2f}")
        
        if propagation_times:
            avg_propagation = sum(p['propagation_time'] for p in propagation_times) / len(propagation_times)
            max_propagation = max(p['propagation_time'] for p in propagation_times)
            
            print(f"  Average propagation time: {avg_propagation * 1000:.2f}ms")
            print(f"  Max propagation time: {max_propagation * 1000:.2f}ms")
        
        # Performance assertions
        self.assertEqual(len(all_events_received), expected_events)
        self.assertLess(total_time, 30.0)  # Should complete in under 30 seconds
        
        if propagation_times:
            avg_propagation = sum(p['propagation_time'] for p in propagation_times) / len(propagation_times)
            self.assertLess(avg_propagation, 0.05)  # Average propagation < 50ms
    
    def test_memory_usage_under_load(self):
        """Test memory usage patterns under sustained load"""
        duration_seconds = 60
        access_rate = 100  # requests per second
        
        memory_samples = []
        cache_stats_samples = []
        
        def memory_monitor():
            """Monitor memory usage and cache statistics"""
            process = psutil.Process(os.getpid())
            
            while not stop_monitoring.is_set():
                memory_info = process.memory_info()
                cache_stats = self.config_service.get_cache_stats()
                
                memory_samples.append({
                    'timestamp': time.time(),
                    'rss': memory_info.rss,
                    'vms': memory_info.vms
                })
                
                cache_stats_samples.append({
                    'timestamp': time.time(),
                    'cache_size': cache_stats['cache']['size'],
                    'hit_rate': cache_stats['hit_rate'],
                    'total_requests': cache_stats['total_requests']
                })
                
                time.sleep(1.0)  # Sample every second
        
        stop_monitoring = threading.Event()
        
        # Start monitoring
        monitor_thread = threading.Thread(target=memory_monitor)
        monitor_thread.start()
        
        try:
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < duration_seconds:
                # Access configurations at specified rate
                config_key = f"test_config_{request_count % 100:04d}"
                self.config_service.get_config(config_key)
                
                request_count += 1
                
                # Control access rate
                elapsed = time.time() - start_time
                expected_requests = int(elapsed * access_rate)
                if request_count > expected_requests:
                    time.sleep(0.001)
            
        finally:
            stop_monitoring.set()
            monitor_thread.join(timeout=5.0)
        
        # Analyze memory usage
        if memory_samples:
            initial_memory = memory_samples[0]['rss']
            final_memory = memory_samples[-1]['rss']
            max_memory = max(sample['rss'] for sample in memory_samples)
            min_memory = min(sample['rss'] for sample in memory_samples)
            
            memory_growth = final_memory - initial_memory
            memory_variance = max_memory - min_memory
            
            print(f"Memory usage analysis:")
            print(f"  Duration: {duration_seconds}s")
            print(f"  Total requests: {request_count}")
            print(f"  Initial memory: {initial_memory / 1024 / 1024:.2f}MB")
            print(f"  Final memory: {final_memory / 1024 / 1024:.2f}MB")
            print(f"  Max memory: {max_memory / 1024 / 1024:.2f}MB")
            print(f"  Memory growth: {memory_growth / 1024 / 1024:.2f}MB")
            print(f"  Memory variance: {memory_variance / 1024 / 1024:.2f}MB")
        
        if cache_stats_samples:
            final_cache_size = cache_stats_samples[-1]['cache_size']
            final_hit_rate = cache_stats_samples[-1]['hit_rate']
            
            print(f"  Final cache size: {final_cache_size}")
            print(f"  Final hit rate: {final_hit_rate:.2%}")
        
        # Memory usage assertions
        if memory_samples:
            # Memory growth should be reasonable
            self.assertLess(memory_growth, 100 * 1024 * 1024)  # <100MB growth
            
            # Memory usage should be stable (not constantly growing)
            memory_trend = final_memory - initial_memory
            self.assertLess(abs(memory_trend), 50 * 1024 * 1024)  # <50MB trend


if __name__ == '__main__':
    unittest.main()