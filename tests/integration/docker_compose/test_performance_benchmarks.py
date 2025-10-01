# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Docker Compose Integration Tests - Performance Benchmarks
Performance benchmarking tests to ensure parity with macOS deployment
"""

import unittest
import time
import requests
import json
import os
import sys
import statistics
import concurrent.futures
import threading
from datetime import datetime, timedelta

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, PlatformConnection, Post, Image
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

class DockerComposePerformanceBenchmarkTest(unittest.TestCase):
    """Performance benchmarking tests for Docker Compose deployment"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://localhost:5000"
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        
        # Performance thresholds (based on macOS deployment expectations)
        cls.performance_thresholds = {
            'response_time_p95': 2.0,  # 95th percentile response time (seconds)
            'response_time_avg': 0.5,  # Average response time (seconds)
            'throughput_min': 10,      # Minimum requests per second
            'database_query_max': 0.1, # Maximum database query time (seconds)
            'memory_usage_max': 2048,  # Maximum memory usage (MB)
            'cpu_usage_max': 80,       # Maximum CPU usage (%)
        }
        
        # Wait for services to be ready
        cls._wait_for_services()
    
    @classmethod
    def _wait_for_services(cls, timeout=60):
        """Wait for services to be ready"""
        print("Waiting for services to be ready for performance testing...")
        
        for i in range(timeout):
            try:
                response = requests.get(f"{cls.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Services ready for performance testing")
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        raise Exception("Services failed to start within timeout")
    
    def setUp(self):
        """Set up test data for each test"""
        # Create test user with platform connections
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="perf_test_user",
            platforms=['pixelfed']
        )
        
        # Create authenticated session for API calls
        self.session = requests.Session()
        self._authenticate_session()
        
        # Performance metrics storage
        self.metrics = {
            'response_times': [],
            'database_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'error_count': 0,
            'success_count': 0
        }
    
    def tearDown(self):
        """Clean up test data and report metrics"""
        cleanup_test_user(self.user_helper)
        self._report_performance_metrics()
    
    def _authenticate_session(self):
        """Authenticate session for API calls"""
        # Get login page for CSRF token
        login_page = self.session.get(f"{self.base_url}/login")
        csrf_token = self._extract_csrf_token(login_page.text)
        
        # Login with test user
        login_data = {
            'username_or_email': self.test_user.username,
            'password': 'test_password',
            'csrf_token': csrf_token
        }
        
        response = self.session.post(f"{self.base_url}/login", data=login_data)
        self.assertIn(response.status_code, [200, 302])
    
    def _extract_csrf_token(self, html_content):
        """Extract CSRF token from HTML content"""
        import re
        match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html_content)
        return match.group(1) if match else None
    
    def _measure_response_time(self, url, method='GET', data=None, json_data=None):
        """Measure response time for a request"""
        start_time = time.time()
        
        try:
            if method == 'GET':
                response = self.session.get(url, timeout=10)
            elif method == 'POST':
                if json_data:
                    response = self.session.post(url, json=json_data, timeout=10)
                else:
                    response = self.session.post(url, data=data, timeout=10)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            self.metrics['response_times'].append(response_time)
            
            if response.status_code < 400:
                self.metrics['success_count'] += 1
            else:
                self.metrics['error_count'] += 1
            
            return response, response_time
            
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            response_time = end_time - start_time
            self.metrics['response_times'].append(response_time)
            self.metrics['error_count'] += 1
            raise e
    
    def _get_system_metrics(self):
        """Get system performance metrics"""
        try:
            response = self.session.get(f"{self.base_url}/api/system/metrics")
            if response.status_code == 200:
                data = response.json()
                return {
                    'memory_usage': data.get('memory_usage_mb', 0),
                    'cpu_usage': data.get('cpu_usage_percent', 0),
                    'database_connections': data.get('database_connections', 0),
                    'redis_memory': data.get('redis_memory_mb', 0)
                }
        except:
            pass
        
        return {
            'memory_usage': 0,
            'cpu_usage': 0,
            'database_connections': 0,
            'redis_memory': 0
        }
    
    def _report_performance_metrics(self):
        """Report performance metrics"""
        if not self.metrics['response_times']:
            return
        
        response_times = self.metrics['response_times']
        
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        
        total_requests = self.metrics['success_count'] + self.metrics['error_count']
        success_rate = (self.metrics['success_count'] / total_requests * 100) if total_requests > 0 else 0
        
        print(f"\n📊 Performance Metrics:")
        print(f"   Average Response Time: {avg_response_time:.3f}s")
        print(f"   95th Percentile: {p95_response_time:.3f}s")
        print(f"   Min Response Time: {min_response_time:.3f}s")
        print(f"   Max Response Time: {max_response_time:.3f}s")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Total Requests: {total_requests}")
    
    def test_web_interface_response_times(self):
        """Test web interface response times meet performance thresholds"""
        endpoints = [
            '/',
            '/login',
            '/dashboard',
            '/platform-management',
            '/review',
            '/api/health'
        ]
        
        print("Testing web interface response times...")
        
        for endpoint in endpoints:
            url = f"{self.base_url}{endpoint}"
            
            # Test multiple requests to get average
            for i in range(5):
                try:
                    response, response_time = self._measure_response_time(url)
                    print(f"   {endpoint}: {response_time:.3f}s")
                except requests.exceptions.RequestException:
                    print(f"   {endpoint}: ERROR")
        
        # Check performance thresholds
        if self.metrics['response_times']:
            avg_time = statistics.mean(self.metrics['response_times'])
            p95_time = statistics.quantiles(self.metrics['response_times'], n=20)[18] if len(self.metrics['response_times']) > 1 else avg_time
            
            self.assertLess(avg_time, self.performance_thresholds['response_time_avg'],
                          f"Average response time {avg_time:.3f}s exceeds threshold {self.performance_thresholds['response_time_avg']}s")
            
            self.assertLess(p95_time, self.performance_thresholds['response_time_p95'],
                          f"95th percentile response time {p95_time:.3f}s exceeds threshold {self.performance_thresholds['response_time_p95']}s")
    
    def test_database_query_performance(self):
        """Test database query performance in containerized environment"""
        print("Testing database query performance...")
        
        # Test various database operations
        database_operations = [
            ('User query', f"{self.base_url}/api/users"),
            ('Platform connections', f"{self.base_url}/api/platform-connections"),
            ('Posts query', f"{self.base_url}/api/posts?limit=10"),
            ('Images query', f"{self.base_url}/api/images?limit=10"),
            ('Dashboard stats', f"{self.base_url}/api/dashboard/stats")
        ]
        
        for operation_name, url in database_operations:
            try:
                response, response_time = self._measure_response_time(url)
                self.metrics['database_times'].append(response_time)
                print(f"   {operation_name}: {response_time:.3f}s")
                
                # Check individual query performance
                self.assertLess(response_time, self.performance_thresholds['database_query_max'],
                              f"{operation_name} query time {response_time:.3f}s exceeds threshold")
                
            except requests.exceptions.RequestException as e:
                print(f"   {operation_name}: ERROR - {e}")
    
    def test_concurrent_request_handling(self):
        """Test concurrent request handling performance"""
        print("Testing concurrent request handling...")
        
        def make_request(url):
            try:
                start_time = time.time()
                response = self.session.get(url, timeout=10)
                end_time = time.time()
                return {
                    'success': response.status_code < 400,
                    'response_time': end_time - start_time,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'response_time': 10.0,  # Timeout
                    'error': str(e)
                }
        
        # Test concurrent requests
        urls = [f"{self.base_url}/api/health" for _ in range(20)]
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(make_request, urls))
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_requests = sum(1 for r in results if r['success'])
        total_requests = len(results)
        success_rate = (successful_requests / total_requests) * 100
        
        response_times = [r['response_time'] for r in results if r['success']]
        if response_times:
            avg_response_time = statistics.mean(response_times)
            throughput = successful_requests / total_time
            
            print(f"   Concurrent requests: {total_requests}")
            print(f"   Successful requests: {successful_requests}")
            print(f"   Success rate: {success_rate:.1f}%")
            print(f"   Average response time: {avg_response_time:.3f}s")
            print(f"   Throughput: {throughput:.1f} req/s")
            
            # Check performance thresholds
            self.assertGreater(throughput, self.performance_thresholds['throughput_min'],
                             f"Throughput {throughput:.1f} req/s below threshold {self.performance_thresholds['throughput_min']} req/s")
            
            self.assertGreater(success_rate, 95.0, f"Success rate {success_rate:.1f}% below 95%")
    
    def test_memory_usage_performance(self):
        """Test memory usage in containerized environment"""
        print("Testing memory usage performance...")
        
        # Get initial memory usage
        initial_metrics = self._get_system_metrics()
        initial_memory = initial_metrics['memory_usage']
        
        # Perform memory-intensive operations
        operations = [
            ('Load dashboard', f"{self.base_url}/dashboard"),
            ('Load platform management', f"{self.base_url}/platform-management"),
            ('Load review interface', f"{self.base_url}/review"),
            ('API health check', f"{self.base_url}/api/health"),
            ('System metrics', f"{self.base_url}/api/system/metrics")
        ]
        
        for operation_name, url in operations:
            try:
                response, response_time = self._measure_response_time(url)
                
                # Get memory usage after operation
                metrics = self._get_system_metrics()
                memory_usage = metrics['memory_usage']
                
                if memory_usage > 0:
                    self.metrics['memory_usage'].append(memory_usage)
                    print(f"   {operation_name}: {memory_usage}MB")
                
            except requests.exceptions.RequestException:
                print(f"   {operation_name}: ERROR")
        
        # Check memory usage threshold
        if self.metrics['memory_usage']:
            max_memory = max(self.metrics['memory_usage'])
            avg_memory = statistics.mean(self.metrics['memory_usage'])
            
            print(f"   Initial memory: {initial_memory}MB")
            print(f"   Average memory: {avg_memory:.1f}MB")
            print(f"   Peak memory: {max_memory}MB")
            
            self.assertLess(max_memory, self.performance_thresholds['memory_usage_max'],
                          f"Peak memory usage {max_memory}MB exceeds threshold {self.performance_thresholds['memory_usage_max']}MB")
    
    def test_api_endpoint_performance(self):
        """Test API endpoint performance"""
        print("Testing API endpoint performance...")
        
        api_endpoints = [
            ('Health check', 'GET', '/api/health', None),
            ('System metrics', 'GET', '/api/system/metrics', None),
            ('Platform connections', 'GET', '/api/platform-connections', None),
            ('Dashboard stats', 'GET', '/api/dashboard/stats', None),
            ('User profile', 'GET', '/api/user/profile', None)
        ]
        
        for endpoint_name, method, path, data in api_endpoints:
            url = f"{self.base_url}{path}"
            
            # Test multiple requests for each endpoint
            endpoint_times = []
            for i in range(3):
                try:
                    response, response_time = self._measure_response_time(url, method, data)
                    endpoint_times.append(response_time)
                except requests.exceptions.RequestException:
                    pass
            
            if endpoint_times:
                avg_time = statistics.mean(endpoint_times)
                print(f"   {endpoint_name}: {avg_time:.3f}s")
                
                # API endpoints should be fast
                self.assertLess(avg_time, 1.0, f"{endpoint_name} response time {avg_time:.3f}s too slow")
    
    def test_static_file_serving_performance(self):
        """Test static file serving performance"""
        print("Testing static file serving performance...")
        
        static_files = [
            '/static/css/style.css',
            '/static/js/main.js',
            '/static/images/logo.png',
            '/admin/static/css/admin.css',
            '/admin/static/js/admin.js'
        ]
        
        for static_file in static_files:
            url = f"{self.base_url}{static_file}"
            
            try:
                response, response_time = self._measure_response_time(url)
                print(f"   {static_file}: {response_time:.3f}s")
                
                # Static files should be served quickly
                if response.status_code == 200:
                    self.assertLess(response_time, 0.5, f"Static file {static_file} served too slowly")
                
            except requests.exceptions.RequestException:
                print(f"   {static_file}: Not found (acceptable)")
    
    def test_session_management_performance(self):
        """Test session management performance with Redis"""
        print("Testing session management performance...")
        
        # Test session operations
        session_operations = []
        
        for i in range(10):
            start_time = time.time()
            
            # Make authenticated request (uses session)
            response = self.session.get(f"{self.base_url}/dashboard")
            
            end_time = time.time()
            operation_time = end_time - start_time
            session_operations.append(operation_time)
            
            print(f"   Session operation {i+1}: {operation_time:.3f}s")
        
        # Analyze session performance
        avg_session_time = statistics.mean(session_operations)
        max_session_time = max(session_operations)
        
        print(f"   Average session operation: {avg_session_time:.3f}s")
        print(f"   Max session operation: {max_session_time:.3f}s")
        
        # Session operations should be fast with Redis
        self.assertLess(avg_session_time, 0.5, f"Average session operation {avg_session_time:.3f}s too slow")
        self.assertLess(max_session_time, 1.0, f"Max session operation {max_session_time:.3f}s too slow")
    
    def test_container_resource_efficiency(self):
        """Test container resource efficiency"""
        print("Testing container resource efficiency...")
        
        # Get system metrics over time
        metrics_samples = []
        
        for i in range(5):
            metrics = self._get_system_metrics()
            metrics_samples.append(metrics)
            
            print(f"   Sample {i+1}: Memory={metrics['memory_usage']}MB, CPU={metrics['cpu_usage']}%")
            
            # Make some requests to generate load
            self._measure_response_time(f"{self.base_url}/api/health")
            time.sleep(1)
        
        # Analyze resource usage
        if metrics_samples:
            avg_memory = statistics.mean([m['memory_usage'] for m in metrics_samples if m['memory_usage'] > 0])
            avg_cpu = statistics.mean([m['cpu_usage'] for m in metrics_samples if m['cpu_usage'] > 0])
            
            if avg_memory > 0:
                print(f"   Average memory usage: {avg_memory:.1f}MB")
                self.assertLess(avg_memory, self.performance_thresholds['memory_usage_max'],
                              f"Average memory usage {avg_memory:.1f}MB exceeds threshold")
            
            if avg_cpu > 0:
                print(f"   Average CPU usage: {avg_cpu:.1f}%")
                self.assertLess(avg_cpu, self.performance_thresholds['cpu_usage_max'],
                              f"Average CPU usage {avg_cpu:.1f}% exceeds threshold")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)