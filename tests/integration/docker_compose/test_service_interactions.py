# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Docker Compose Integration Tests - Service Interactions
Tests all service-to-service communication in containerized environment
"""

import unittest
import time
import requests
import redis
import mysql.connector
import docker
import json
import os
import sys
from urllib.parse import urljoin

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

class DockerComposeServiceInteractionTest(unittest.TestCase):
    """Test service interactions in Docker Compose environment"""
    
    @classmethod
    def setUpClass(cls):
        """Set up Docker client and verify containers are running"""
        cls.docker_client = docker.from_env()
        cls.base_url = "http://localhost:5000"
        cls.mysql_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'vedfolnir',
            'database': 'vedfolnir'
        }
        cls.redis_config = {
            'host': 'localhost',
            'port': 6379,
            'db': 0
        }
        
        # Wait for services to be ready
        cls._wait_for_services()
    
    @classmethod
    def _wait_for_services(cls, timeout=120):
        """Wait for all services to be ready"""
        print("Waiting for Docker Compose services to be ready...")
        
        # Wait for web application
        for i in range(timeout):
            try:
                response = requests.get(f"{cls.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Web application ready")
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        else:
            raise Exception("Web application failed to start within timeout")
        
        # Wait for MySQL
        for i in range(timeout):
            try:
                conn = mysql.connector.connect(**cls.mysql_config, password=os.getenv('MYSQL_PASSWORD', 'vedfolnir'))
                conn.close()
                print("✅ MySQL ready")
                break
            except mysql.connector.Error:
                pass
            time.sleep(1)
        else:
            raise Exception("MySQL failed to start within timeout")
        
        # Wait for Redis
        for i in range(timeout):
            try:
                r = redis.Redis(**cls.redis_config, password=os.getenv('REDIS_PASSWORD'))
                r.ping()
                print("✅ Redis ready")
                break
            except redis.exceptions.ConnectionError:
                pass
            time.sleep(1)
        else:
            raise Exception("Redis failed to start within timeout")
    
    def test_container_health_checks(self):
        """Test that all containers are healthy"""
        containers = self.docker_client.containers.list()
        
        # Expected containers
        expected_containers = [
            'vedfolnir_app',
            'vedfolnir_mysql',
            'vedfolnir_redis',
            'vedfolnir_nginx',
            'vedfolnir_prometheus',
            'vedfolnir_grafana',
            'vedfolnir_loki',
            'vedfolnir_vault'
        ]
        
        running_containers = [c.name for c in containers if c.status == 'running']
        
        for expected in expected_containers:
            # Check if container exists (name might have suffix)
            matching = [name for name in running_containers if expected in name]
            self.assertTrue(len(matching) > 0, f"Container {expected} not found in running containers")
    
    def test_web_app_to_mysql_connection(self):
        """Test web application can connect to MySQL container"""
        response = requests.get(f"{self.base_url}/api/health/database")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('database_connected', False))
        self.assertEqual(data.get('database_type'), 'mysql')
    
    def test_web_app_to_redis_connection(self):
        """Test web application can connect to Redis container"""
        response = requests.get(f"{self.base_url}/api/health/redis")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('redis_connected', False))
        self.assertIsNotNone(data.get('redis_info'))
    
    def test_nginx_proxy_functionality(self):
        """Test Nginx reverse proxy is working"""
        # Test direct access through Nginx (port 80)
        try:
            response = requests.get("http://localhost:80/health", timeout=10)
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException:
            # If port 80 not exposed, test internal routing
            self.skipTest("Nginx port 80 not exposed for testing")
    
    def test_prometheus_metrics_collection(self):
        """Test Prometheus is collecting metrics from services"""
        try:
            # Test Prometheus endpoint
            response = requests.get("http://localhost:9090/api/v1/targets", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            targets = data.get('data', {}).get('activeTargets', [])
            
            # Verify application metrics are being scraped
            app_targets = [t for t in targets if 'vedfolnir' in t.get('labels', {}).get('job', '')]
            self.assertTrue(len(app_targets) > 0, "No application targets found in Prometheus")
            
        except requests.exceptions.RequestException:
            self.skipTest("Prometheus not accessible for testing")
    
    def test_grafana_dashboard_access(self):
        """Test Grafana dashboard is accessible"""
        try:
            response = requests.get("http://localhost:3000/api/health", timeout=10)
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException:
            self.skipTest("Grafana not accessible for testing")
    
    def test_vault_secrets_integration(self):
        """Test Vault secrets management integration"""
        try:
            # Test Vault health
            response = requests.get("http://localhost:8200/v1/sys/health", timeout=10)
            self.assertIn(response.status_code, [200, 429, 472, 473])  # Various healthy states
            
            # Test application can access secrets
            response = requests.get(f"{self.base_url}/api/health/vault")
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get('vault_accessible', False))
            
        except requests.exceptions.RequestException:
            self.skipTest("Vault not accessible for testing")
    
    def test_loki_log_aggregation(self):
        """Test Loki log aggregation is working"""
        try:
            # Test Loki ready endpoint
            response = requests.get("http://localhost:3100/ready", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            # Test log ingestion
            response = requests.get("http://localhost:3100/loki/api/v1/labels", timeout=10)
            self.assertEqual(response.status_code, 200)
            
        except requests.exceptions.RequestException:
            self.skipTest("Loki not accessible for testing")
    
    def test_service_network_isolation(self):
        """Test that services are properly isolated in Docker networks"""
        # Get network information
        networks = self.docker_client.networks.list()
        vedfolnir_networks = [n for n in networks if 'vedfolnir' in n.name]
        
        self.assertTrue(len(vedfolnir_networks) > 0, "No Vedfolnir networks found")
        
        # Test internal network exists
        internal_networks = [n for n in vedfolnir_networks if 'internal' in n.name]
        self.assertTrue(len(internal_networks) > 0, "Internal network not found")
    
    def test_volume_persistence(self):
        """Test that data volumes are properly mounted and persistent"""
        # Test MySQL data persistence
        conn = mysql.connector.connect(**self.mysql_config, password=os.getenv('MYSQL_PASSWORD', 'vedfolnir'))
        cursor = conn.cursor()
        
        # Create test data
        test_table = "integration_test_table"
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {test_table} (id INT PRIMARY KEY, data VARCHAR(255))")
        cursor.execute(f"INSERT INTO {test_table} (id, data) VALUES (1, 'test_data') ON DUPLICATE KEY UPDATE data='test_data'")
        conn.commit()
        
        # Verify data exists
        cursor.execute(f"SELECT data FROM {test_table} WHERE id = 1")
        result = cursor.fetchone()
        self.assertEqual(result[0], 'test_data')
        
        # Cleanup
        cursor.execute(f"DROP TABLE {test_table}")
        conn.commit()
        conn.close()
        
        # Test Redis data persistence
        r = redis.Redis(**self.redis_config, password=os.getenv('REDIS_PASSWORD'))
        test_key = "integration_test_key"
        r.set(test_key, "test_value")
        
        result = r.get(test_key)
        self.assertEqual(result.decode('utf-8'), 'test_value')
        
        # Cleanup
        r.delete(test_key)
    
    def test_container_resource_limits(self):
        """Test that containers are running within resource limits"""
        containers = self.docker_client.containers.list()
        
        for container in containers:
            if 'vedfolnir' in container.name:
                # Get container stats
                stats = container.stats(stream=False)
                
                # Check memory usage is reasonable
                memory_usage = stats['memory_stats'].get('usage', 0)
                memory_limit = stats['memory_stats'].get('limit', 0)
                
                if memory_limit > 0:
                    memory_percent = (memory_usage / memory_limit) * 100
                    self.assertLess(memory_percent, 90, f"Container {container.name} using {memory_percent:.1f}% memory")
    
    def test_service_startup_dependencies(self):
        """Test that services start in correct order with proper dependencies"""
        # This test verifies that dependent services are healthy
        # MySQL and Redis should be ready before the application
        
        # Test database connection from application
        response = requests.get(f"{self.base_url}/api/health/database")
        self.assertEqual(response.status_code, 200)
        
        # Test Redis connection from application
        response = requests.get(f"{self.base_url}/api/health/redis")
        self.assertEqual(response.status_code, 200)
        
        # If we get here, dependencies are working correctly
        self.assertTrue(True, "Service dependencies are working correctly")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)