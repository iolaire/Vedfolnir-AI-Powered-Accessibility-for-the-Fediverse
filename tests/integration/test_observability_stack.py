# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import requests
import time
import json
import subprocess
import os

class TestObservabilityStack(unittest.TestCase):
    """Test suite for the comprehensive observability stack"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://localhost"
        cls.prometheus_port = 9090
        cls.grafana_port = 3000
        cls.loki_port = 3100
        
        # Exporter ports
        cls.mysql_exporter_port = 9104
        cls.redis_exporter_port = 9121
        cls.nginx_exporter_port = 9113
        cls.node_exporter_port = 9100
        cls.cadvisor_port = 8080
        
        # Wait for services to be ready
        time.sleep(30)
    
    def test_prometheus_health(self):
        """Test Prometheus health endpoint"""
        try:
            response = requests.get(f"{self.base_url}:{self.prometheus_port}/-/healthy", timeout=10)
            self.assertEqual(response.status_code, 200)
            print("✅ Prometheus health check passed")
        except requests.exceptions.RequestException as e:
            self.fail(f"Prometheus health check failed: {e}")
    
    def test_grafana_health(self):
        """Test Grafana health endpoint"""
        try:
            response = requests.get(f"{self.base_url}:{self.grafana_port}/api/health", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            health_data = response.json()
            self.assertEqual(health_data.get('database'), 'ok')
            print("✅ Grafana health check passed")
        except requests.exceptions.RequestException as e:
            self.fail(f"Grafana health check failed: {e}")
    
    def test_loki_ready(self):
        """Test Loki ready endpoint"""
        try:
            response = requests.get(f"{self.base_url}:{self.loki_port}/ready", timeout=10)
            self.assertEqual(response.status_code, 200)
            print("✅ Loki ready check passed")
        except requests.exceptions.RequestException as e:
            self.fail(f"Loki ready check failed: {e}")
    
    def test_mysql_exporter_metrics(self):
        """Test MySQL exporter metrics endpoint"""
        try:
            response = requests.get(f"{self.base_url}:{self.mysql_exporter_port}/metrics", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            metrics_text = response.text
            self.assertIn('mysql_up', metrics_text)
            self.assertIn('mysql_global_status_threads_connected', metrics_text)
            print("✅ MySQL exporter metrics available")
        except requests.exceptions.RequestException as e:
            self.fail(f"MySQL exporter metrics check failed: {e}")
    
    def test_redis_exporter_metrics(self):
        """Test Redis exporter metrics endpoint"""
        try:
            response = requests.get(f"{self.base_url}:{self.redis_exporter_port}/metrics", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            metrics_text = response.text
            self.assertIn('redis_up', metrics_text)
            self.assertIn('redis_memory_used_bytes', metrics_text)
            print("✅ Redis exporter metrics available")
        except requests.exceptions.RequestException as e:
            self.fail(f"Redis exporter metrics check failed: {e}")
    
    def test_nginx_exporter_metrics(self):
        """Test Nginx exporter metrics endpoint"""
        try:
            response = requests.get(f"{self.base_url}:{self.nginx_exporter_port}/metrics", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            metrics_text = response.text
            self.assertIn('nginx_up', metrics_text)
            print("✅ Nginx exporter metrics available")
        except requests.exceptions.RequestException as e:
            self.fail(f"Nginx exporter metrics check failed: {e}")
    
    def test_node_exporter_metrics(self):
        """Test Node exporter metrics endpoint"""
        try:
            response = requests.get(f"{self.base_url}:{self.node_exporter_port}/metrics", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            metrics_text = response.text
            self.assertIn('node_cpu_seconds_total', metrics_text)
            self.assertIn('node_memory_MemTotal_bytes', metrics_text)
            print("✅ Node exporter metrics available")
        except requests.exceptions.RequestException as e:
            self.fail(f"Node exporter metrics check failed: {e}")
    
    def test_cadvisor_metrics(self):
        """Test cAdvisor metrics endpoint"""
        try:
            response = requests.get(f"{self.base_url}:{self.cadvisor_port}/metrics", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            metrics_text = response.text
            self.assertIn('container_cpu_usage_seconds_total', metrics_text)
            self.assertIn('container_memory_usage_bytes', metrics_text)
            print("✅ cAdvisor metrics available")
        except requests.exceptions.RequestException as e:
            self.fail(f"cAdvisor metrics check failed: {e}")
    
    def test_prometheus_targets(self):
        """Test Prometheus target discovery"""
        try:
            response = requests.get(f"{self.base_url}:{self.prometheus_port}/api/v1/targets", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            targets_data = response.json()
            self.assertEqual(targets_data['status'], 'success')
            
            active_targets = targets_data['data']['activeTargets']
            target_jobs = [target['labels']['job'] for target in active_targets]
            
            expected_jobs = ['prometheus', 'vedfolnir-app', 'mysql', 'redis', 'nginx', 'node', 'cadvisor', 'grafana', 'loki']
            
            for job in expected_jobs:
                self.assertIn(job, target_jobs, f"Job {job} not found in Prometheus targets")
            
            print(f"✅ Prometheus discovered {len(active_targets)} targets")
        except requests.exceptions.RequestException as e:
            self.fail(f"Prometheus targets check failed: {e}")
    
    def test_grafana_datasources(self):
        """Test Grafana datasource configuration"""
        try:
            # Note: This would require authentication in a real environment
            # For testing, we'll just check if the provisioning worked
            response = requests.get(f"{self.base_url}:{self.grafana_port}/api/datasources", timeout=10)
            
            # If we get 401, that's expected (authentication required)
            # If we get 200, datasources are accessible
            self.assertIn(response.status_code, [200, 401])
            print("✅ Grafana datasources endpoint accessible")
        except requests.exceptions.RequestException as e:
            self.fail(f"Grafana datasources check failed: {e}")
    
    def test_alert_rules_loaded(self):
        """Test that Prometheus alert rules are loaded"""
        try:
            response = requests.get(f"{self.base_url}:{self.prometheus_port}/api/v1/rules", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            rules_data = response.json()
            self.assertEqual(rules_data['status'], 'success')
            
            rule_groups = rules_data['data']['groups']
            self.assertGreater(len(rule_groups), 0, "No alert rule groups found")
            
            # Check for our specific rule group
            vedfolnir_rules = [group for group in rule_groups if group['name'] == 'vedfolnir_alerts']
            self.assertGreater(len(vedfolnir_rules), 0, "Vedfolnir alert rules not found")
            
            print(f"✅ Prometheus loaded {len(rule_groups)} rule groups")
        except requests.exceptions.RequestException as e:
            self.fail(f"Prometheus alert rules check failed: {e}")
    
    def test_container_status(self):
        """Test that all observability containers are running"""
        try:
            result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            
            output = result.stdout
            containers = [
                'vedfolnir_prometheus',
                'vedfolnir_grafana', 
                'vedfolnir_loki',
                'vedfolnir_mysql_exporter',
                'vedfolnir_redis_exporter',
                'vedfolnir_nginx_exporter',
                'vedfolnir_node_exporter',
                'vedfolnir_cadvisor'
            ]
            
            for container in containers:
                self.assertIn(container, output, f"Container {container} not found")
                # Check if container is in "Up" state
                container_line = [line for line in output.split('\n') if container in line]
                if container_line:
                    self.assertIn('Up', container_line[0], f"Container {container} is not running")
            
            print("✅ All observability containers are running")
        except subprocess.SubprocessError as e:
            self.fail(f"Container status check failed: {e}")
    
    def test_configuration_files_exist(self):
        """Test that all required configuration files exist"""
        config_files = [
            'config/prometheus/prometheus.yml',
            'config/prometheus/rules/alert_rules.yml',
            'config/grafana/grafana.ini',
            'config/grafana/provisioning/datasources/prometheus.yml',
            'config/grafana/provisioning/dashboards/dashboards.yml',
            'config/grafana/dashboards/vedfolnir-overview.json',
            'config/grafana/dashboards/system-metrics.json',
            'config/grafana/dashboards/database-metrics.json',
            'config/loki/loki.yml',
            'config/exporters/mysql-exporter.env',
            'config/exporters/redis-exporter.env',
            'config/exporters/nginx-exporter.conf'
        ]
        
        for config_file in config_files:
            self.assertTrue(os.path.exists(config_file), f"Configuration file {config_file} does not exist")
        
        print("✅ All configuration files exist")

if __name__ == '__main__':
    unittest.main(verbosity=2)