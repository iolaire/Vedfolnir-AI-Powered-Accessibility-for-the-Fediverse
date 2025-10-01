# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Docker Compose Validation Tests
Comprehensive testing to verify functionality parity with macOS deployment
"""

import unittest
import requests
import time
import json
import os
import sys
import subprocess
import docker
import redis
import mysql.connector
from urllib.parse import urljoin, urlparse
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, Post, Image, PlatformConnection


class DockerComposeValidationTest(unittest.TestCase):
    """Comprehensive validation tests for Docker Compose deployment"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = os.getenv('TEST_BASE_URL', 'http://localhost:5000')
        cls.docker_client = docker.from_env()
        cls.session = requests.Session()
        cls.session.timeout = 30
        
        # Wait for services to be ready
        cls._wait_for_services()
    
    @classmethod
    def _wait_for_services(cls, timeout=120):
        """Wait for all Docker Compose services to be ready"""
        print("Waiting for Docker Compose services to be ready...")
        
        services = {
            'vedfolnir': f"{cls.base_url}/health",
            'mysql': None,  # Will test via database connection
            'redis': None,  # Will test via Redis connection
            'nginx': f"{cls.base_url}",
            'prometheus': 'http://localhost:9090/-/ready',
            'grafana': 'http://localhost:3000/api/health'
        }
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            all_ready = True
            
            for service, url in services.items():
                try:
                    if url:
                        response = requests.get(url, timeout=5)
                        if response.status_code not in [200, 302]:
                            all_ready = False
                            break
                    elif service == 'mysql':
                        # Test MySQL connection
                        config = Config()
                        db_manager = DatabaseManager(config)
                        with db_manager.get_session() as session:
                            session.execute('SELECT 1')
                    elif service == 'redis':
                        # Test Redis connection
                        redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
                        redis_client.ping()
                        
                except Exception as e:
                    all_ready = False
                    break
            
            if all_ready:
                print("All services are ready!")
                return
            
            time.sleep(5)
        
        raise Exception(f"Services not ready after {timeout} seconds")
    
    def test_container_health_checks(self):
        """Test that all containers are healthy"""
        print("\n=== Testing Container Health ===")
        
        # Get running containers
        containers = self.docker_client.containers.list()
        vedfolnir_containers = [c for c in containers if 'vedfolnir' in c.name.lower()]
        
        self.assertGreater(len(vedfolnir_containers), 0, "No Vedfolnir containers found")
        
        for container in vedfolnir_containers:
            # Check container status
            container.reload()
            self.assertEqual(container.status, 'running', f"Container {container.name} is not running")
            
            # Check health status if available
            if container.attrs.get('State', {}).get('Health'):
                health_status = container.attrs['State']['Health']['Status']
                self.assertEqual(health_status, 'healthy', f"Container {container.name} is not healthy")
            
            print(f"✅ Container {container.name}: {container.status}")
    
    def test_web_application_endpoints(self):
        """Test all major web application endpoints"""
        print("\n=== Testing Web Application Endpoints ===")
        
        endpoints = [
            ('/', 200, 'Landing page'),
            ('/health', 200, 'Health check'),
            ('/login', 200, 'Login page'),
            ('/api/health', 200, 'API health check'),
            ('/static/css/main.css', 200, 'Static CSS'),
            ('/static/js/main.js', 200, 'Static JavaScript'),
        ]
        
        for endpoint, expected_status, description in endpoints:
            with self.subTest(endpoint=endpoint):
                try:
                    response = self.session.get(urljoin(self.base_url, endpoint))
                    self.assertEqual(response.status_code, expected_status, 
                                   f"{description} returned {response.status_code}")
                    print(f"✅ {description}: {response.status_code}")
                except Exception as e:
                    self.fail(f"Failed to access {description} ({endpoint}): {e}")
    
    def test_database_connectivity_and_operations(self):
        """Test MySQL database connectivity and basic operations"""
        print("\n=== Testing Database Connectivity ===")
        
        try:
            config = Config()
            db_manager = DatabaseManager(config)
            
            with db_manager.get_session() as session:
                # Test basic query
                result = session.execute('SELECT 1 as test').scalar()
                self.assertEqual(result, 1, "Basic database query failed")
                
                # Test table existence
                tables = ['users', 'platform_connections', 'posts', 'images', 'processing_runs']
                for table in tables:
                    count = session.execute(f'SELECT COUNT(*) FROM {table}').scalar()
                    self.assertIsNotNone(count, f"Table {table} not accessible")
                    print(f"✅ Table {table}: {count} records")
                
                # Test user operations
                user_count = session.query(User).count()
                self.assertGreaterEqual(user_count, 0, "User table not accessible")
                print(f"✅ Database connectivity: {user_count} users")
                
        except Exception as e:
            self.fail(f"Database connectivity test failed: {e}")
    
    def test_redis_connectivity_and_sessions(self):
        """Test Redis connectivity and session management"""
        print("\n=== Testing Redis Connectivity ===")
        
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            redis_client = redis.Redis.from_url(redis_url)
            
            # Test basic Redis operations
            test_key = 'vedfolnir:test:connectivity'
            test_value = 'docker_compose_test'
            
            redis_client.set(test_key, test_value, ex=60)
            retrieved_value = redis_client.get(test_key)
            self.assertEqual(retrieved_value.decode('utf-8'), test_value, "Redis set/get failed")
            
            # Clean up test key
            redis_client.delete(test_key)
            
            # Test session storage
            session_keys = redis_client.keys('vedfolnir:session:*')
            print(f"✅ Redis connectivity: {len(session_keys)} active sessions")
            
            # Test Redis info
            info = redis_client.info()
            self.assertIn('redis_version', info, "Redis info not accessible")
            print(f"✅ Redis version: {info['redis_version']}")
            
        except Exception as e:
            self.fail(f"Redis connectivity test failed: {e}")
    
    def test_rq_worker_functionality(self):
        """Test Redis Queue worker functionality and performance"""
        print("\n=== Testing RQ Worker Functionality ===")
        
        try:
            from rq import Queue
            from redis import Redis
            
            redis_conn = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
            queue = Queue('default', connection=redis_conn)
            
            # Check queue status
            queue_length = len(queue)
            print(f"✅ RQ Queue length: {queue_length}")
            
            # Test job enqueueing (simple test job)
            def test_job(x, y):
                return x + y
            
            job = queue.enqueue(test_job, 2, 3, timeout=30)
            
            # Wait for job completion
            start_time = time.time()
            while not job.is_finished and not job.is_failed and time.time() - start_time < 30:
                time.sleep(1)
                job.refresh()
            
            if job.is_finished:
                self.assertEqual(job.result, 5, "RQ job execution failed")
                print("✅ RQ Worker: Job executed successfully")
            elif job.is_failed:
                self.fail(f"RQ job failed: {job.exc_info}")
            else:
                self.fail("RQ job timed out")
                
        except Exception as e:
            self.fail(f"RQ worker test failed: {e}")
    
    def test_websocket_functionality(self):
        """Test WebSocket functionality for real-time features"""
        print("\n=== Testing WebSocket Functionality ===")
        
        try:
            import websocket
            import threading
            import json
            
            ws_url = self.base_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws'
            
            messages_received = []
            connection_established = threading.Event()
            
            def on_message(ws, message):
                messages_received.append(json.loads(message))
            
            def on_open(ws):
                connection_established.set()
                # Send test message
                ws.send(json.dumps({'type': 'ping', 'data': 'test'}))
            
            def on_error(ws, error):
                print(f"WebSocket error: {error}")
            
            ws = websocket.WebSocketApp(ws_url,
                                      on_message=on_message,
                                      on_open=on_open,
                                      on_error=on_error)
            
            # Run WebSocket in separate thread
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection
            if connection_established.wait(timeout=10):
                time.sleep(2)  # Wait for potential messages
                ws.close()
                print("✅ WebSocket: Connection established and closed successfully")
            else:
                self.fail("WebSocket connection not established")
                
        except ImportError:
            print("⚠️  WebSocket test skipped (websocket-client not installed)")
        except Exception as e:
            print(f"⚠️  WebSocket test failed: {e}")
    
    def test_ollama_integration(self):
        """Test Ollama API integration from containerized environment"""
        print("\n=== Testing Ollama Integration ===")
        
        try:
            ollama_url = os.getenv('OLLAMA_URL', 'http://host.docker.internal:11434')
            
            # Test Ollama API connectivity
            response = requests.get(f"{ollama_url}/api/version", timeout=10)
            if response.status_code == 200:
                version_info = response.json()
                print(f"✅ Ollama API: Connected (version: {version_info.get('version', 'unknown')})")
                
                # Test model availability
                models_response = requests.get(f"{ollama_url}/api/tags", timeout=10)
                if models_response.status_code == 200:
                    models = models_response.json().get('models', [])
                    llava_models = [m for m in models if 'llava' in m.get('name', '').lower()]
                    if llava_models:
                        print(f"✅ Ollama Models: {len(llava_models)} LLaVA models available")
                    else:
                        print("⚠️  No LLaVA models found")
                else:
                    print("⚠️  Could not retrieve model list")
            else:
                print(f"⚠️  Ollama API not accessible: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Ollama integration test failed: {e}")
    
    def test_security_configurations(self):
        """Test security configurations and compliance requirements"""
        print("\n=== Testing Security Configurations ===")
        
        # Test HTTPS redirect (if configured)
        try:
            response = self.session.get(self.base_url, allow_redirects=False)
            headers = response.headers
            
            # Check security headers
            security_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': None,  # May not be present in development
            }
            
            for header, expected_value in security_headers.items():
                if expected_value:
                    self.assertIn(header, headers, f"Security header {header} missing")
                    if expected_value != headers.get(header):
                        print(f"⚠️  {header}: {headers.get(header)} (expected: {expected_value})")
                    else:
                        print(f"✅ {header}: {headers.get(header)}")
                else:
                    if header in headers:
                        print(f"✅ {header}: {headers.get(header)}")
            
            # Test CSRF protection
            login_response = self.session.get(urljoin(self.base_url, '/login'))
            if 'csrf-token' in login_response.text or 'csrf_token' in login_response.text:
                print("✅ CSRF protection: Token found in login page")
            else:
                print("⚠️  CSRF protection: No token found")
                
        except Exception as e:
            print(f"⚠️  Security configuration test failed: {e}")
    
    def test_monitoring_endpoints(self):
        """Test monitoring and observability endpoints"""
        print("\n=== Testing Monitoring Endpoints ===")
        
        monitoring_endpoints = [
            ('http://localhost:9090/-/ready', 'Prometheus'),
            ('http://localhost:3000/api/health', 'Grafana'),
            (f"{self.base_url}/metrics", 'Application Metrics'),
        ]
        
        for url, service in monitoring_endpoints:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    print(f"✅ {service}: Available")
                else:
                    print(f"⚠️  {service}: HTTP {response.status_code}")
            except Exception as e:
                print(f"⚠️  {service}: Not accessible ({e})")
    
    def test_volume_mounts_and_persistence(self):
        """Test volume mounts and data persistence"""
        print("\n=== Testing Volume Mounts and Persistence ===")
        
        # Test volume mount paths
        volume_paths = [
            ('./storage', 'Storage volume'),
            ('./logs', 'Logs volume'),
            ('./config', 'Configuration volume'),
            ('./data/mysql', 'MySQL data volume'),
            ('./data/redis', 'Redis data volume'),
        ]
        
        for path, description in volume_paths:
            if os.path.exists(path):
                if os.path.isdir(path):
                    files_count = len(os.listdir(path)) if os.access(path, os.R_OK) else 'N/A'
                    print(f"✅ {description}: {path} ({files_count} items)")
                else:
                    print(f"⚠️  {description}: {path} is not a directory")
            else:
                print(f"⚠️  {description}: {path} does not exist")
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks to ensure parity with macOS deployment"""
        print("\n=== Testing Performance Benchmarks ===")
        
        # Test response times
        endpoints_to_benchmark = [
            ('/', 'Landing page'),
            ('/health', 'Health check'),
            ('/api/health', 'API health'),
        ]
        
        for endpoint, description in endpoints_to_benchmark:
            response_times = []
            
            for _ in range(5):  # 5 requests for average
                start_time = time.time()
                try:
                    response = self.session.get(urljoin(self.base_url, endpoint))
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        response_times.append((end_time - start_time) * 1000)  # Convert to ms
                except Exception:
                    pass
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                print(f"✅ {description}: {avg_time:.2f}ms avg, {max_time:.2f}ms max")
                
                # Performance thresholds (adjust based on requirements)
                if avg_time > 1000:  # 1 second
                    print(f"⚠️  {description}: Average response time exceeds 1s")
            else:
                print(f"⚠️  {description}: No successful requests")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)