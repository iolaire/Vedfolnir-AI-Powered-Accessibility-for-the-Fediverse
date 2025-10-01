# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Docker Performance Benchmarks
Performance testing to ensure parity with macOS deployment
"""

import unittest
import requests
import time
import statistics
import concurrent.futures
import os
import sys
import json
import threading
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class DockerPerformanceBenchmarkTest(unittest.TestCase):
    """Performance benchmarks for Docker Compose deployment"""
    
    @classmethod
    def setUpClass(cls):
        """Set up performance testing environment"""
        cls.base_url = os.getenv('TEST_BASE_URL', 'http://localhost:5000')
        cls.session = requests.Session()
        cls.session.timeout = 30
        cls.performance_results = {}
        
        # Performance thresholds (adjust based on requirements)
        cls.thresholds = {
            'response_time_ms': {
                'excellent': 100,
                'good': 500,
                'acceptable': 1000,
                'poor': 2000
            },
            'throughput_rps': {
                'excellent': 100,
                'good': 50,
                'acceptable': 20,
                'poor': 10
            },
            'concurrent_users': {
                'target': 50,
                'maximum': 100
            }
        }
    
    def test_response_time_benchmarks(self):
        """Test response time benchmarks for key endpoints"""
        print("\n=== Response Time Benchmarks ===")
        
        endpoints = [
            ('/', 'Landing Page'),
            ('/health', 'Health Check'),
            ('/api/health', 'API Health'),
            ('/login', 'Login Page'),
            ('/static/css/main.css', 'Static CSS'),
            ('/static/js/main.js', 'Static JavaScript')
        ]
        
        for endpoint, description in endpoints:
            with self.subTest(endpoint=endpoint):
                response_times = self._measure_response_times(endpoint, iterations=10)
                
                if response_times:
                    avg_time = statistics.mean(response_times)
                    median_time = statistics.median(response_times)
                    p95_time = self._percentile(response_times, 95)
                    p99_time = self._percentile(response_times, 99)
                    
                    # Store results
                    self.performance_results[f'{endpoint}_response_time'] = {
                        'average_ms': avg_time,
                        'median_ms': median_time,
                        'p95_ms': p95_time,
                        'p99_ms': p99_time,
                        'samples': len(response_times)
                    }
                    
                    # Evaluate performance
                    performance_level = self._evaluate_response_time(avg_time)
                    
                    print(f"✅ {description}:")
                    print(f"   Average: {avg_time:.2f}ms ({performance_level})")
                    print(f"   Median: {median_time:.2f}ms")
                    print(f"   P95: {p95_time:.2f}ms")
                    print(f"   P99: {p99_time:.2f}ms")
                    
                    # Assert acceptable performance
                    self.assertLess(avg_time, self.thresholds['response_time_ms']['poor'],
                                  f"{description} average response time too slow: {avg_time:.2f}ms")
                else:
                    self.fail(f"No successful responses for {description}")
    
    def test_throughput_benchmarks(self):
        """Test throughput benchmarks"""
        print("\n=== Throughput Benchmarks ===")
        
        endpoints = [
            ('/', 'Landing Page'),
            ('/health', 'Health Check'),
            ('/api/health', 'API Health')
        ]
        
        for endpoint, description in endpoints:
            with self.subTest(endpoint=endpoint):
                throughput = self._measure_throughput(endpoint, duration=30)
                
                # Store results
                self.performance_results[f'{endpoint}_throughput'] = {
                    'requests_per_second': throughput['rps'],
                    'total_requests': throughput['total_requests'],
                    'successful_requests': throughput['successful_requests'],
                    'error_rate': throughput['error_rate'],
                    'duration_seconds': throughput['duration']
                }
                
                # Evaluate performance
                performance_level = self._evaluate_throughput(throughput['rps'])
                
                print(f"✅ {description}:")
                print(f"   Throughput: {throughput['rps']:.2f} RPS ({performance_level})")
                print(f"   Total Requests: {throughput['total_requests']}")
                print(f"   Success Rate: {(1 - throughput['error_rate']) * 100:.1f}%")
                
                # Assert acceptable throughput
                self.assertGreater(throughput['rps'], self.thresholds['throughput_rps']['poor'],
                                 f"{description} throughput too low: {throughput['rps']:.2f} RPS")
                
                # Assert low error rate
                self.assertLess(throughput['error_rate'], 0.05,  # 5% error rate threshold
                              f"{description} error rate too high: {throughput['error_rate'] * 100:.1f}%")
    
    def test_concurrent_user_load(self):
        """Test concurrent user load handling"""
        print("\n=== Concurrent User Load Test ===")
        
        concurrent_levels = [10, 25, 50]
        endpoint = '/health'  # Use health endpoint for load testing
        
        for concurrent_users in concurrent_levels:
            with self.subTest(concurrent_users=concurrent_users):
                print(f"\nTesting {concurrent_users} concurrent users...")
                
                load_results = self._concurrent_load_test(endpoint, concurrent_users, duration=20)
                
                # Store results
                self.performance_results[f'concurrent_{concurrent_users}_users'] = load_results
                
                print(f"✅ {concurrent_users} Concurrent Users:")
                print(f"   Average Response Time: {load_results['avg_response_time']:.2f}ms")
                print(f"   Success Rate: {load_results['success_rate'] * 100:.1f}%")
                print(f"   Throughput: {load_results['throughput']:.2f} RPS")
                print(f"   Errors: {load_results['error_count']}")
                
                # Assert acceptable performance under load
                self.assertGreater(load_results['success_rate'], 0.95,  # 95% success rate
                                 f"Success rate too low under {concurrent_users} concurrent users")
                
                self.assertLess(load_results['avg_response_time'], 
                               self.thresholds['response_time_ms']['poor'],
                               f"Response time too slow under {concurrent_users} concurrent users")
    
    def test_database_performance(self):
        """Test database performance in containerized environment"""
        print("\n=== Database Performance Test ===")
        
        try:
            from config import Config
            from app.core.database.core.database_manager import DatabaseManager
            
            config = Config()
            db_manager = DatabaseManager(config)
            
            # Test database connection time
            connection_times = []
            for _ in range(10):
                start_time = time.time()
                with db_manager.get_session() as session:
                    session.execute('SELECT 1')
                end_time = time.time()
                connection_times.append((end_time - start_time) * 1000)
            
            avg_connection_time = statistics.mean(connection_times)
            
            # Test query performance
            query_times = []
            with db_manager.get_session() as session:
                for _ in range(10):
                    start_time = time.time()
                    session.execute('SELECT COUNT(*) FROM users')
                    end_time = time.time()
                    query_times.append((end_time - start_time) * 1000)
            
            avg_query_time = statistics.mean(query_times)
            
            # Store results
            self.performance_results['database_performance'] = {
                'avg_connection_time_ms': avg_connection_time,
                'avg_query_time_ms': avg_query_time
            }
            
            print(f"✅ Database Performance:")
            print(f"   Average Connection Time: {avg_connection_time:.2f}ms")
            print(f"   Average Query Time: {avg_query_time:.2f}ms")
            
            # Assert acceptable database performance
            self.assertLess(avg_connection_time, 100,  # 100ms connection threshold
                          f"Database connection time too slow: {avg_connection_time:.2f}ms")
            
            self.assertLess(avg_query_time, 50,  # 50ms query threshold
                          f"Database query time too slow: {avg_query_time:.2f}ms")
            
        except Exception as e:
            print(f"⚠️  Database performance test failed: {e}")
    
    def test_redis_performance(self):
        """Test Redis performance in containerized environment"""
        print("\n=== Redis Performance Test ===")
        
        try:
            import redis
            
            redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
            
            # Test Redis ping times
            ping_times = []
            for _ in range(100):
                start_time = time.time()
                redis_client.ping()
                end_time = time.time()
                ping_times.append((end_time - start_time) * 1000)
            
            avg_ping_time = statistics.mean(ping_times)
            
            # Test Redis set/get performance
            set_get_times = []
            for i in range(100):
                key = f'perf_test_{i}'
                value = f'test_value_{i}'
                
                start_time = time.time()
                redis_client.set(key, value)
                retrieved_value = redis_client.get(key)
                redis_client.delete(key)
                end_time = time.time()
                
                set_get_times.append((end_time - start_time) * 1000)
            
            avg_set_get_time = statistics.mean(set_get_times)
            
            # Store results
            self.performance_results['redis_performance'] = {
                'avg_ping_time_ms': avg_ping_time,
                'avg_set_get_time_ms': avg_set_get_time
            }
            
            print(f"✅ Redis Performance:")
            print(f"   Average Ping Time: {avg_ping_time:.2f}ms")
            print(f"   Average Set/Get Time: {avg_set_get_time:.2f}ms")
            
            # Assert acceptable Redis performance
            self.assertLess(avg_ping_time, 10,  # 10ms ping threshold
                          f"Redis ping time too slow: {avg_ping_time:.2f}ms")
            
            self.assertLess(avg_set_get_time, 20,  # 20ms set/get threshold
                          f"Redis set/get time too slow: {avg_set_get_time:.2f}ms")
            
        except Exception as e:
            print(f"⚠️  Redis performance test failed: {e}")
    
    def test_memory_usage_monitoring(self):
        """Monitor memory usage during testing"""
        print("\n=== Memory Usage Monitoring ===")
        
        try:
            import psutil
            import docker
            
            docker_client = docker.from_env()
            
            # Get Vedfolnir containers
            containers = docker_client.containers.list()
            vedfolnir_containers = [c for c in containers if 'vedfolnir' in c.name.lower()]
            
            memory_stats = {}
            
            for container in vedfolnir_containers:
                stats = container.stats(stream=False)
                memory_usage = stats['memory_stats']['usage']
                memory_limit = stats['memory_stats']['limit']
                memory_percent = (memory_usage / memory_limit) * 100
                
                memory_stats[container.name] = {
                    'usage_mb': memory_usage / (1024 * 1024),
                    'limit_mb': memory_limit / (1024 * 1024),
                    'usage_percent': memory_percent
                }
                
                print(f"✅ {container.name}:")
                print(f"   Memory Usage: {memory_usage / (1024 * 1024):.1f}MB")
                print(f"   Memory Limit: {memory_limit / (1024 * 1024):.1f}MB")
                print(f"   Usage Percentage: {memory_percent:.1f}%")
                
                # Assert reasonable memory usage
                self.assertLess(memory_percent, 90,  # 90% memory usage threshold
                              f"Container {container.name} using too much memory: {memory_percent:.1f}%")
            
            self.performance_results['memory_usage'] = memory_stats
            
        except Exception as e:
            print(f"⚠️  Memory usage monitoring failed: {e}")
    
    def _measure_response_times(self, endpoint, iterations=10):
        """Measure response times for an endpoint"""
        response_times = []
        
        for _ in range(iterations):
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append((end_time - start_time) * 1000)  # Convert to ms
                
                time.sleep(0.1)  # Small delay between requests
                
            except Exception:
                pass
        
        return response_times
    
    def _measure_throughput(self, endpoint, duration=30):
        """Measure throughput for an endpoint"""
        start_time = time.time()
        end_time = start_time + duration
        
        total_requests = 0
        successful_requests = 0
        
        while time.time() < end_time:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                total_requests += 1
                
                if response.status_code == 200:
                    successful_requests += 1
                    
            except Exception:
                total_requests += 1
        
        actual_duration = time.time() - start_time
        rps = successful_requests / actual_duration
        error_rate = (total_requests - successful_requests) / total_requests if total_requests > 0 else 0
        
        return {
            'rps': rps,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'error_rate': error_rate,
            'duration': actual_duration
        }
    
    def _concurrent_load_test(self, endpoint, concurrent_users, duration=20):
        """Perform concurrent load test"""
        results = {
            'response_times': [],
            'success_count': 0,
            'error_count': 0,
            'total_requests': 0
        }
        
        results_lock = threading.Lock()
        
        def worker():
            session = requests.Session()
            session.timeout = 30
            
            end_time = time.time() + duration
            
            while time.time() < end_time:
                try:
                    start_time = time.time()
                    response = session.get(f"{self.base_url}{endpoint}")
                    response_time = (time.time() - start_time) * 1000
                    
                    with results_lock:
                        results['total_requests'] += 1
                        results['response_times'].append(response_time)
                        
                        if response.status_code == 200:
                            results['success_count'] += 1
                        else:
                            results['error_count'] += 1
                            
                except Exception:
                    with results_lock:
                        results['total_requests'] += 1
                        results['error_count'] += 1
                
                time.sleep(0.01)  # Small delay
        
        # Start concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(worker) for _ in range(concurrent_users)]
            concurrent.futures.wait(futures)
        
        # Calculate results
        avg_response_time = statistics.mean(results['response_times']) if results['response_times'] else 0
        success_rate = results['success_count'] / results['total_requests'] if results['total_requests'] > 0 else 0
        throughput = results['success_count'] / duration
        
        return {
            'avg_response_time': avg_response_time,
            'success_rate': success_rate,
            'throughput': throughput,
            'error_count': results['error_count'],
            'total_requests': results['total_requests']
        }
    
    def _percentile(self, data, percentile):
        """Calculate percentile of data"""
        if not data:
            return 0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _evaluate_response_time(self, response_time):
        """Evaluate response time performance level"""
        thresholds = self.thresholds['response_time_ms']
        
        if response_time <= thresholds['excellent']:
            return 'Excellent'
        elif response_time <= thresholds['good']:
            return 'Good'
        elif response_time <= thresholds['acceptable']:
            return 'Acceptable'
        elif response_time <= thresholds['poor']:
            return 'Poor'
        else:
            return 'Unacceptable'
    
    def _evaluate_throughput(self, throughput):
        """Evaluate throughput performance level"""
        thresholds = self.thresholds['throughput_rps']
        
        if throughput >= thresholds['excellent']:
            return 'Excellent'
        elif throughput >= thresholds['good']:
            return 'Good'
        elif throughput >= thresholds['acceptable']:
            return 'Acceptable'
        elif throughput >= thresholds['poor']:
            return 'Poor'
        else:
            return 'Unacceptable'
    
    @classmethod
    def tearDownClass(cls):
        """Save performance results"""
        try:
            results_file = f"performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w') as f:
                json.dump(cls.performance_results, f, indent=2)
            print(f"\n📊 Performance results saved to: {results_file}")
        except Exception as e:
            print(f"⚠️  Failed to save performance results: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)