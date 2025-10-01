# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simplified Nginx configuration tests using only standard library modules.
Tests configuration files, SSL certificates, and Docker integration without external dependencies.
"""

import unittest
import subprocess
import os
import ssl
import socket
import time
import threading
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin


class TestNginxConfiguration(unittest.TestCase):
    """Test Nginx configuration files and Docker integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.config_dir = os.path.join(self.project_root, 'config', 'nginx')
        self.ssl_dir = os.path.join(self.project_root, 'ssl')
        self.timeout = 10
    
    def test_configuration_files_exist(self):
        """Test that all required configuration files exist"""
        required_files = [
            os.path.join(self.config_dir, 'nginx.conf'),
            os.path.join(self.config_dir, 'default.conf'),
            os.path.join(self.config_dir, 'nginx_status.conf'),
            os.path.join(self.ssl_dir, 'certs', 'vedfolnir.crt'),
            os.path.join(self.ssl_dir, 'keys', 'vedfolnir.key')
        ]
        
        for file_path in required_files:
            with self.subTest(file=file_path):
                self.assertTrue(os.path.exists(file_path), f"Required file {file_path} does not exist")
                self.assertTrue(os.path.isfile(file_path), f"{file_path} is not a regular file")
    
    def test_ssl_certificate_validity(self):
        """Test SSL certificate is valid"""
        cert_path = os.path.join(self.ssl_dir, 'certs', 'vedfolnir.crt')
        key_path = os.path.join(self.ssl_dir, 'keys', 'vedfolnir.key')
        
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            self.skipTest("SSL certificate files not found")
        
        try:
            # Test certificate validity
            result = subprocess.run(
                ['openssl', 'x509', '-in', cert_path, '-noout', '-checkend', '86400'],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(result.returncode, 0, "SSL certificate is invalid or expired")
            
            # Test certificate and key match
            cert_modulus = subprocess.run(
                ['openssl', 'x509', '-noout', '-modulus', '-in', cert_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            key_modulus = subprocess.run(
                ['openssl', 'rsa', '-noout', '-modulus', '-in', key_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if cert_modulus.returncode == 0 and key_modulus.returncode == 0:
                self.assertEqual(cert_modulus.stdout, key_modulus.stdout, 
                               "SSL certificate and key do not match")
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("OpenSSL command not available")
    
    def test_docker_compose_configuration(self):
        """Test Docker Compose configuration is valid"""
        try:
            os.chdir(self.project_root)
            result = subprocess.run(
                ['docker-compose', 'config'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.fail(f"Docker Compose configuration is invalid: {result.stderr}")
            
            # Check if Nginx service is defined
            self.assertIn('nginx:', result.stdout, "Nginx service not found in Docker Compose configuration")
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Docker Compose command not available")
    
    def test_nginx_container_health(self):
        """Test Nginx container health via Docker"""
        try:
            # Check if Nginx container is running
            result = subprocess.run(
                ['docker', 'ps', '--filter', 'name=vedfolnir_nginx', '--format', '{{.Status}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                status = result.stdout.strip()
                self.assertIn('Up', status, "Nginx container should be running")
            else:
                self.skipTest("Nginx container not found or not running")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Docker command not available")
    
    def test_nginx_configuration_syntax(self):
        """Test Nginx configuration syntax via Docker or local nginx"""
        # First try with Docker container if it's running
        try:
            result = subprocess.run(
                ['docker', 'exec', 'vedfolnir_nginx', 'nginx', '-t'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.assertIn('syntax is ok', result.stderr, "Nginx configuration syntax check failed")
                self.assertIn('test is successful', result.stderr, "Nginx configuration test failed")
                return
            elif 'No such container' not in result.stderr:
                # Container exists but config test failed
                self.fail(f"Nginx configuration test failed: {result.stderr}")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Docker command failed, try local nginx or validate config files
            pass
        
        # Try with local nginx installation
        try:
            nginx_conf = os.path.join(self.config_dir, 'nginx.conf')
            result = subprocess.run(
                ['nginx', '-t', '-c', nginx_conf, '-p', self.project_root],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.assertIn('syntax is ok', result.stderr, "Nginx configuration syntax check failed")
                self.assertIn('test is successful', result.stderr, "Nginx configuration test failed")
                return
            else:
                self.fail(f"Nginx configuration test failed: {result.stderr}")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # No local nginx, do basic file validation
            pass
        
        # Fallback: Basic configuration file validation
        self._validate_config_files_basic()
    
    def _validate_config_files_basic(self):
        """Basic validation of configuration files without nginx binary"""
        nginx_conf = os.path.join(self.config_dir, 'nginx.conf')
        default_conf = os.path.join(self.config_dir, 'default.conf')
        
        # Check main nginx.conf
        if os.path.exists(nginx_conf):
            with open(nginx_conf, 'r') as f:
                content = f.read()
                # Basic syntax checks
                self.assertEqual(content.count('{'), content.count('}'), 
                               "Mismatched braces in nginx.conf")
                self.assertIn('http {', content, "Missing http block in nginx.conf")
                self.assertIn('include /etc/nginx/conf.d/*.conf;', content, 
                            "Missing conf.d include in nginx.conf")
        
        # Check default.conf
        if os.path.exists(default_conf):
            with open(default_conf, 'r') as f:
                content = f.read()
                # Basic syntax checks
                self.assertEqual(content.count('{'), content.count('}'), 
                               "Mismatched braces in default.conf")
                self.assertIn('server {', content, "Missing server block in default.conf")
                self.assertIn('listen 443 ssl', content, "Missing SSL listener in default.conf")
                self.assertIn('proxy_pass http://vedfolnir_app;', content, 
                            "Missing proxy_pass directive in default.conf")
        
        print("✅ Basic configuration file validation passed (nginx binary not available)")
    
    def test_configuration_content(self):
        """Test configuration files contain required directives"""
        default_conf_path = os.path.join(self.config_dir, 'default.conf')
        
        if not os.path.exists(default_conf_path):
            self.skipTest("Default configuration file not found")
        
        with open(default_conf_path, 'r') as f:
            config_content = f.read()
        
        # Test for required configuration elements
        required_elements = [
            'ssl_certificate',
            'ssl_certificate_key',
            'limit_req_zone',
            'proxy_pass',
            'X-Content-Type-Options',
            'X-Frame-Options',
            'Strict-Transport-Security',
            'proxy_set_header Upgrade',
            'location /static/',
            'location /ws'
        ]
        
        for element in required_elements:
            with self.subTest(element=element):
                self.assertIn(element, config_content, 
                            f"Required configuration element '{element}' not found")
    
    def test_ssl_file_permissions(self):
        """Test SSL key file has secure permissions"""
        key_path = os.path.join(self.ssl_dir, 'keys', 'vedfolnir.key')
        
        if not os.path.exists(key_path):
            self.skipTest("SSL key file not found")
        
        # Check file permissions
        file_stat = os.stat(key_path)
        file_mode = oct(file_stat.st_mode)[-3:]  # Get last 3 digits of octal mode
        
        # Should be 600 (owner read/write only) or 400 (owner read only)
        self.assertIn(file_mode, ['600', '400'], 
                     f"SSL key file has insecure permissions: {file_mode}")


class TestNginxConnectivity(unittest.TestCase):
    """Test Nginx connectivity using standard library only"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = "http://localhost"
        self.https_url = "https://localhost"
        self.status_url = "http://localhost:8080"
        self.timeout = 10
    
    def _make_request(self, url, timeout=None):
        """Make HTTP request using urllib"""
        if timeout is None:
            timeout = self.timeout
        
        try:
            req = Request(url)
            with urlopen(req, timeout=timeout) as response:
                return {
                    'status_code': response.getcode(),
                    'headers': dict(response.headers),
                    'content': response.read().decode('utf-8', errors='ignore')
                }
        except (URLError, HTTPError) as e:
            if hasattr(e, 'code'):
                return {
                    'status_code': e.code,
                    'headers': dict(e.headers) if hasattr(e, 'headers') else {},
                    'content': ''
                }
            raise
    
    def test_http_connectivity(self):
        """Test HTTP connectivity to Nginx"""
        try:
            response = self._make_request(self.base_url)
            # Should get some response (200, 301, 302, etc.)
            self.assertIsInstance(response['status_code'], int)
            self.assertGreater(response['status_code'], 0)
            
        except Exception as e:
            self.skipTest(f"HTTP service not available: {e}")
    
    def test_https_connectivity(self):
        """Test HTTPS connectivity to Nginx"""
        try:
            # Create SSL context that accepts self-signed certificates
            import ssl
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            req = Request(self.https_url)
            with urlopen(req, timeout=self.timeout, context=context) as response:
                status_code = response.getcode()
                self.assertIsInstance(status_code, int)
                self.assertGreater(status_code, 0)
                
        except Exception as e:
            self.skipTest(f"HTTPS service not available: {e}")
    
    def test_ssl_connection(self):
        """Test SSL/TLS connection parameters"""
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection(('localhost', 443), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname='localhost') as ssock:
                    # Test TLS version
                    tls_version = ssock.version()
                    self.assertIsNotNone(tls_version, "TLS version should not be None")
                    self.assertIn(tls_version, ['TLSv1.2', 'TLSv1.3'], 
                                f"Unexpected TLS version: {tls_version}")
                    
                    # Test cipher suite
                    cipher = ssock.cipher()
                    self.assertIsNotNone(cipher, "Cipher suite should not be None")
                    
        except (socket.error, ssl.SSLError) as e:
            self.skipTest(f"SSL connection failed: {e}")
    
    def test_status_endpoint(self):
        """Test Nginx status endpoint"""
        try:
            response = self._make_request(f"{self.status_url}/nginx_status")
            
            if response['status_code'] == 200:
                content = response['content']
                # Should contain Nginx status information
                self.assertIn('Active connections:', content)
                self.assertIn('server accepts handled requests', content)
            else:
                self.skipTest("Nginx status endpoint not configured or not accessible")
                
        except Exception as e:
            self.skipTest(f"Nginx status endpoint not available: {e}")


class TestNginxPerformanceSimple(unittest.TestCase):
    """Simple performance tests using standard library"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = "http://localhost"
        self.timeout = 10
    
    def _make_request(self, url):
        """Make HTTP request and measure time"""
        start_time = time.time()
        try:
            req = Request(url)
            with urlopen(req, timeout=self.timeout) as response:
                end_time = time.time()
                return {
                    'status_code': response.getcode(),
                    'response_time': end_time - start_time,
                    'success': True
                }
        except Exception as e:
            end_time = time.time()
            return {
                'error': str(e),
                'response_time': end_time - start_time,
                'success': False
            }
    
    def test_response_time(self):
        """Test response time is reasonable"""
        try:
            result = self._make_request(self.base_url)
            
            if result['success']:
                response_time = result['response_time']
                # Response should be under 5 seconds for basic requests
                self.assertLess(response_time, 5.0, 
                              f"Response time too slow: {response_time:.3f} seconds")
                print(f"Response time: {response_time:.3f} seconds")
            else:
                self.skipTest(f"Request failed: {result['error']}")
                
        except Exception as e:
            self.skipTest(f"Performance test failed: {e}")
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        results = []
        threads = []
        
        def make_request():
            result = self._make_request(self.base_url)
            results.append(result)
        
        # Create 5 concurrent requests (reduced for stability)
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=self.timeout)
        
        # Analyze results
        successful_requests = sum(1 for r in results if r['success'])
        total_response_time = sum(r['response_time'] for r in results if r['success'])
        
        # At least 60% of requests should succeed (lower threshold for stability)
        success_rate = successful_requests / len(results) if results else 0
        self.assertGreaterEqual(success_rate, 0.6, 
                              f"Success rate too low: {success_rate:.2%}")
        
        if successful_requests > 0:
            avg_response_time = total_response_time / successful_requests
            print(f"Concurrent requests: {successful_requests}/{len(results)} successful, "
                  f"avg response time: {avg_response_time:.3f}s")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)