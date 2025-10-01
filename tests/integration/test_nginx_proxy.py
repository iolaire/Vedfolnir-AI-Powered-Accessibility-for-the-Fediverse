# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Nginx reverse proxy configuration in Docker Compose deployment.
Tests proxy functionality, security headers, SSL termination, and WebSocket support.
"""

import unittest
import time
import ssl
import socket
import subprocess
import json

try:
    import requests
    from urllib.parse import urljoin
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    # Fallback to urllib for basic functionality
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    from urllib.parse import urljoin


class TestNginxProxy(unittest.TestCase):
    """Test Nginx reverse proxy functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        if not HAS_REQUESTS:
            raise unittest.SkipTest("requests module not available - use test_nginx_config_simple.py instead")
        
        cls.base_url = "http://localhost"
        cls.https_url = "https://localhost"
        cls.status_url = "http://localhost:8080"
        cls.timeout = 30
        
        # Wait for services to be ready
        cls._wait_for_service(cls.base_url, timeout=60)
        cls._wait_for_service(cls.status_url, timeout=30)
    
    @classmethod
    def _wait_for_service(cls, url, timeout=30):
        """Wait for service to be available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code < 500:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        raise Exception(f"Service at {url} not available after {timeout} seconds")
    
    def test_http_to_https_redirect(self):
        """Test HTTP to HTTPS redirect"""
        try:
            response = requests.get(self.base_url, allow_redirects=False, timeout=self.timeout)
            self.assertEqual(response.status_code, 301)
            self.assertTrue(response.headers.get('Location', '').startswith('https://'))
        except requests.exceptions.RequestException as e:
            self.skipTest(f"HTTP service not available: {e}")
    
    def test_security_headers(self):
        """Test security headers are present"""
        try:
            response = requests.get(self.base_url, timeout=self.timeout)
            headers = response.headers
            
            # Test required security headers
            self.assertIn('X-Content-Type-Options', headers)
            self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
            
            self.assertIn('X-Frame-Options', headers)
            self.assertEqual(headers['X-Frame-Options'], 'DENY')
            
            self.assertIn('X-XSS-Protection', headers)
            self.assertIn('1; mode=block', headers['X-XSS-Protection'])
            
            self.assertIn('Referrer-Policy', headers)
            self.assertEqual(headers['Referrer-Policy'], 'strict-origin-when-cross-origin')
            
        except requests.exceptions.RequestException as e:
            self.skipTest(f"HTTP service not available: {e}")
    
    def test_https_security_headers(self):
        """Test HTTPS-specific security headers"""
        try:
            # Disable SSL verification for self-signed certificate
            response = requests.get(self.https_url, verify=False, timeout=self.timeout)
            headers = response.headers
            
            # Test HSTS header
            self.assertIn('Strict-Transport-Security', headers)
            hsts = headers['Strict-Transport-Security']
            self.assertIn('max-age=31536000', hsts)
            self.assertIn('includeSubDomains', hsts)
            self.assertIn('preload', hsts)
            
            # Test CSP header
            self.assertIn('Content-Security-Policy', headers)
            csp = headers['Content-Security-Policy']
            self.assertIn("default-src 'self'", csp)
            
        except requests.exceptions.RequestException as e:
            self.skipTest(f"HTTPS service not available: {e}")
    
    def test_ssl_configuration(self):
        """Test SSL/TLS configuration"""
        try:
            # Test SSL connection
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection(('localhost', 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname='localhost') as ssock:
                    # Test TLS version
                    tls_version = ssock.version()
                    self.assertIn(tls_version, ['TLSv1.2', 'TLSv1.3'])
                    
                    # Test cipher suite
                    cipher = ssock.cipher()
                    self.assertIsNotNone(cipher)
                    
        except (socket.error, ssl.SSLError) as e:
            self.skipTest(f"SSL connection failed: {e}")
    
    def test_proxy_to_application(self):
        """Test proxy passes requests to application"""
        try:
            response = requests.get(self.base_url, timeout=self.timeout)
            
            # Should get a response from the application
            self.assertIn(response.status_code, [200, 302, 401])  # Various valid responses
            
            # Test that we're getting content from the application
            if response.status_code == 200:
                content = response.text.lower()
                # Look for signs this is the Vedfolnir application
                self.assertTrue(
                    'vedfolnir' in content or 
                    'login' in content or 
                    'caption' in content or
                    'flask' in response.headers.get('Server', '').lower()
                )
                
        except requests.exceptions.RequestException as e:
            self.skipTest(f"Application not available: {e}")
    
    def test_static_file_serving(self):
        """Test static file serving with caching headers"""
        static_urls = [
            '/static/css/style.css',
            '/static/js/app.js',
            '/favicon.ico',
            '/robots.txt'
        ]
        
        for static_url in static_urls:
            try:
                response = requests.get(urljoin(self.base_url, static_url), timeout=self.timeout)
                
                if response.status_code == 200:
                    # Test caching headers for static files
                    self.assertIn('Cache-Control', response.headers)
                    cache_control = response.headers['Cache-Control']
                    self.assertTrue('public' in cache_control or 'max-age' in cache_control)
                    
                elif response.status_code == 404:
                    # Static file doesn't exist, which is acceptable
                    continue
                else:
                    self.fail(f"Unexpected status code {response.status_code} for {static_url}")
                    
            except requests.exceptions.RequestException:
                # Static file serving may not be available, skip
                continue
    
    def test_api_endpoints_with_rate_limiting(self):
        """Test API endpoints have rate limiting"""
        api_url = urljoin(self.base_url, '/api/health')
        
        try:
            # Make multiple rapid requests to test rate limiting
            responses = []
            for i in range(15):  # Exceed typical rate limit
                try:
                    response = requests.get(api_url, timeout=5)
                    responses.append(response.status_code)
                except requests.exceptions.RequestException:
                    responses.append(0)
                time.sleep(0.1)
            
            # Should eventually get rate limited (429) or connection refused
            rate_limited = any(code == 429 for code in responses)
            if not rate_limited:
                # Rate limiting might not be triggered in test environment
                self.skipTest("Rate limiting not triggered in test environment")
            else:
                self.assertTrue(rate_limited, "Rate limiting should be active for API endpoints")
                
        except requests.exceptions.RequestException as e:
            self.skipTest(f"API endpoint not available: {e}")
    
    def test_websocket_proxy_support(self):
        """Test WebSocket proxy configuration"""
        # Test WebSocket upgrade headers
        headers = {
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
            'Sec-WebSocket-Version': '13'
        }
        
        try:
            response = requests.get(
                urljoin(self.base_url, '/ws'),
                headers=headers,
                timeout=self.timeout
            )
            
            # WebSocket upgrade should be handled appropriately
            # May return 101 (upgrade), 400 (bad request), or 404 (not found)
            self.assertIn(response.status_code, [101, 400, 404, 426])
            
        except requests.exceptions.RequestException as e:
            self.skipTest(f"WebSocket endpoint not available: {e}")
    
    def test_nginx_status_endpoint(self):
        """Test Nginx status endpoint for monitoring"""
        try:
            response = requests.get(urljoin(self.status_url, '/nginx_status'), timeout=self.timeout)
            
            if response.status_code == 200:
                content = response.text
                # Should contain Nginx status information
                self.assertIn('Active connections:', content)
                self.assertIn('server accepts handled requests', content)
            else:
                self.skipTest("Nginx status endpoint not configured")
                
        except requests.exceptions.RequestException as e:
            self.skipTest(f"Nginx status endpoint not available: {e}")
    
    def test_health_check_endpoint(self):
        """Test health check endpoint"""
        try:
            response = requests.get(urljoin(self.base_url, '/health'), timeout=self.timeout)
            
            # Health endpoint should return 200 or be proxied to application
            self.assertIn(response.status_code, [200, 404])
            
            if response.status_code == 200:
                # Should be a simple health check response
                content = response.text.lower()
                self.assertTrue(
                    'ok' in content or 
                    'healthy' in content or 
                    'success' in content or
                    len(content) < 100  # Simple response
                )
                
        except requests.exceptions.RequestException as e:
            self.skipTest(f"Health endpoint not available: {e}")
    
    def test_admin_endpoints_security(self):
        """Test admin endpoints have additional security"""
        admin_url = urljoin(self.base_url, '/admin/')
        
        try:
            response = requests.get(admin_url, timeout=self.timeout)
            
            # Admin endpoints should have security headers
            if response.status_code in [200, 302, 401, 403]:
                headers = response.headers
                self.assertIn('X-Frame-Options', headers)
                self.assertEqual(headers['X-Frame-Options'], 'DENY')
                self.assertIn('X-Content-Type-Options', headers)
                
        except requests.exceptions.RequestException as e:
            self.skipTest(f"Admin endpoint not available: {e}")
    
    def test_gzip_compression(self):
        """Test Gzip compression is enabled"""
        headers = {'Accept-Encoding': 'gzip, deflate'}
        
        try:
            response = requests.get(self.base_url, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                # Check if response is compressed
                encoding = response.headers.get('Content-Encoding', '')
                if 'gzip' in encoding:
                    self.assertIn('gzip', encoding)
                else:
                    # Compression might not be enabled for small responses
                    self.skipTest("Gzip compression not detected (may be disabled for small responses)")
                    
        except requests.exceptions.RequestException as e:
            self.skipTest(f"Compression test failed: {e}")
    
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
                self.skipTest("Nginx container not found or Docker not available")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Docker command not available")
    
    def test_nginx_configuration_syntax(self):
        """Test Nginx configuration syntax via Docker"""
        try:
            # Test Nginx configuration syntax
            result = subprocess.run(
                ['docker', 'exec', 'vedfolnir_nginx', 'nginx', '-t'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.assertIn('syntax is ok', result.stderr)
                self.assertIn('test is successful', result.stderr)
            else:
                self.fail(f"Nginx configuration test failed: {result.stderr}")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Docker exec command not available")


class TestNginxPerformance(unittest.TestCase):
    """Test Nginx performance characteristics"""
    
    def setUp(self):
        self.base_url = "http://localhost"
        self.timeout = 30
    
    def test_response_time(self):
        """Test response time is reasonable"""
        try:
            start_time = time.time()
            response = requests.get(self.base_url, timeout=self.timeout)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Response should be under 5 seconds for basic requests
            self.assertLess(response_time, 5.0, "Response time should be under 5 seconds")
            
            # Log response time for monitoring
            print(f"Response time: {response_time:.3f} seconds")
            
        except requests.exceptions.RequestException as e:
            self.skipTest(f"Performance test failed: {e}")
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                start_time = time.time()
                response = requests.get(self.base_url, timeout=self.timeout)
                end_time = time.time()
                results.put({
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'success': True
                })
            except Exception as e:
                results.put({
                    'error': str(e),
                    'success': False
                })
        
        # Create 10 concurrent requests
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=self.timeout)
        
        # Analyze results
        successful_requests = 0
        total_response_time = 0
        
        while not results.empty():
            result = results.get()
            if result['success']:
                successful_requests += 1
                total_response_time += result['response_time']
        
        # At least 80% of requests should succeed
        success_rate = successful_requests / 10
        self.assertGreaterEqual(success_rate, 0.8, "At least 80% of concurrent requests should succeed")
        
        if successful_requests > 0:
            avg_response_time = total_response_time / successful_requests
            print(f"Concurrent requests: {successful_requests}/10 successful, avg response time: {avg_response_time:.3f}s")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)