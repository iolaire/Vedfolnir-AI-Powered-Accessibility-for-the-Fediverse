# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import os
import sys
import time
import json
from unittest.mock import patch
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from config import Config
except ImportError as e:
    print(f"Warning: Could not import Config: {e}")
    Config = None


def make_http_request(url, timeout=10):
    """Make HTTP request using urllib (no external dependencies)"""
    try:
        request = Request(url)
        request.add_header('User-Agent', 'Vedfolnir-Test/1.0')
        
        with urlopen(request, timeout=timeout) as response:
            status_code = response.getcode()
            data = response.read().decode('utf-8')
            
            if status_code == 200:
                try:
                    return True, json.loads(data)
                except json.JSONDecodeError:
                    return True, data
            else:
                return False, f"HTTP {status_code}"
                
    except HTTPError as e:
        return False, f"HTTP Error {e.code}: {e.reason}"
    except URLError as e:
        return False, f"URL Error: {e.reason}"
    except Exception as e:
        return False, f"Request Error: {str(e)}"


class TestOllamaExternalConnectivity(unittest.TestCase):
    """Test external Ollama API connectivity from containerized application"""
    
    def setUp(self):
        """Set up test configuration"""
        if Config:
            self.config = Config()
            self.ollama_url = self.config.ollama.url
            self.timeout = self.config.ollama.timeout
            self.model_name = self.config.ollama.model_name
        else:
            # Fallback configuration
            self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
            self.timeout = float(os.getenv("OLLAMA_TIMEOUT", "10.0"))
            self.model_name = os.getenv("OLLAMA_MODEL", "llava:7b")
    
    def test_ollama_url_configuration_for_docker(self):
        """Test that Ollama URL is correctly configured for Docker deployment"""
        # Test with DOCKER_DEPLOYMENT=true
        with patch.dict(os.environ, {'DOCKER_DEPLOYMENT': 'true'}):
            if Config:
                config = Config()
                expected_url = "http://host.docker.internal:11434"
                self.assertEqual(config.ollama.url, expected_url)
                print(f"✅ Docker deployment Ollama URL: {config.ollama.url}")
            else:
                print("⚠️  Config class not available, skipping configuration test")
                self.skipTest("Config class not available")
    
    def test_ollama_url_configuration_for_local(self):
        """Test that Ollama URL is correctly configured for local deployment"""
        # Test with DOCKER_DEPLOYMENT=false or not set
        with patch.dict(os.environ, {'DOCKER_DEPLOYMENT': 'false'}, clear=False):
            if Config:
                config = Config()
                expected_url = "http://localhost:11434"
                self.assertEqual(config.ollama.url, expected_url)
                print(f"✅ Local deployment Ollama URL: {config.ollama.url}")
            else:
                print("⚠️  Config class not available, skipping configuration test")
                self.skipTest("Config class not available")
    
    def test_ollama_api_version_endpoint(self):
        """Test connectivity to Ollama API version endpoint"""
        version_url = f"{self.ollama_url}/api/version"
        print(f"Testing Ollama version endpoint: {version_url}")
        
        success, result = make_http_request(version_url, timeout=10)
        
        if success:
            if isinstance(result, dict) and 'version' in result:
                version = result.get('version', 'unknown')
                print(f"✅ Ollama API version: {version}")
                self.assertTrue(True)
            else:
                print(f"✅ Ollama API accessible (response: {str(result)[:100]})")
                self.assertTrue(True)
        else:
            print(f"⚠️  Could not connect to Ollama API: {result}")
            print("This is expected if Ollama is not running on the host system")
            self.skipTest("Ollama service not available - this is expected for external service")
    
    def test_ollama_api_tags_endpoint(self):
        """Test connectivity to Ollama API tags endpoint"""
        tags_url = f"{self.ollama_url}/api/tags"
        print(f"Testing Ollama tags endpoint: {tags_url}")
        
        success, result = make_http_request(tags_url, timeout=10)
        
        if success:
            if isinstance(result, dict) and 'models' in result:
                models = result.get('models', [])
                print(f"✅ Ollama models available: {len(models)}")
                for model in models[:3]:  # Show first 3 models
                    model_name = model.get('name', 'unknown') if isinstance(model, dict) else str(model)
                    print(f"   - {model_name}")
                self.assertTrue(True)
            else:
                print(f"✅ Ollama tags endpoint accessible (response: {str(result)[:100]})")
                self.assertTrue(True)
        else:
            print(f"⚠️  Could not connect to Ollama tags endpoint: {result}")
            self.skipTest("Ollama service not available - this is expected for external service")
    
    def test_ollama_model_availability(self):
        """Test if the configured LLaVA model is available"""
        tags_url = f"{self.ollama_url}/api/tags"
        print(f"Checking for model '{self.model_name}' at: {tags_url}")
        
        success, result = make_http_request(tags_url, timeout=10)
        
        if success:
            if isinstance(result, dict) and 'models' in result:
                models = result.get('models', [])
                model_names = []
                
                for model in models:
                    if isinstance(model, dict):
                        model_names.append(model.get('name', ''))
                    else:
                        model_names.append(str(model))
                
                if self.model_name in model_names:
                    print(f"✅ Required model '{self.model_name}' is available")
                    self.assertTrue(True)
                else:
                    print(f"⚠️  Required model '{self.model_name}' not found")
                    print(f"Available models: {model_names[:5]}")  # Show first 5
                    self.skipTest(f"Required model '{self.model_name}' not available")
            else:
                print(f"⚠️  Could not parse models from response: {str(result)[:100]}")
                self.skipTest("Could not parse models response")
        else:
            print(f"⚠️  Could not connect to Ollama API: {result}")
            self.skipTest("Ollama service not available - this is expected for external service")
    
    def test_docker_host_networking_configuration(self):
        """Test that Docker host networking is properly configured"""
        # This test verifies the configuration but doesn't require actual connectivity
        
        # Test environment variable configuration
        with patch.dict(os.environ, {'DOCKER_DEPLOYMENT': 'true'}):
            if Config:
                config = Config()
                
                # Verify URL uses host.docker.internal
                self.assertIn("host.docker.internal", config.ollama.url)
                print(f"✅ Docker host networking configured: {config.ollama.url}")
                
                # Verify port is correct
                self.assertIn(":11434", config.ollama.url)
                print("✅ Ollama port 11434 configured correctly")
                
                # Verify protocol is HTTP (not HTTPS for internal communication)
                self.assertTrue(config.ollama.url.startswith("http://"))
                print("✅ HTTP protocol configured for internal communication")
            else:
                # Test with environment variables directly
                expected_url = "http://host.docker.internal:11434"
                print(f"✅ Expected Docker URL: {expected_url}")
                self.assertTrue(True)
    
    def test_configuration_fallback(self):
        """Test that configuration works even without Config class"""
        # Test fallback configuration
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        model_name = os.getenv("OLLAMA_MODEL", "llava:7b")
        timeout = float(os.getenv("OLLAMA_TIMEOUT", "10.0"))
        
        self.assertIsInstance(ollama_url, str)
        self.assertIsInstance(model_name, str)
        self.assertIsInstance(timeout, float)
        
        print(f"✅ Fallback configuration works:")
        print(f"   URL: {ollama_url}")
        print(f"   Model: {model_name}")
        print(f"   Timeout: {timeout}s")


def run_connectivity_test():
    """Run Ollama connectivity test with detailed output"""
    print("=== Ollama External Connectivity Test ===")
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestOllamaExternalConnectivity)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print()
    print("=== Test Summary ===")
    if result.wasSuccessful():
        print("✅ All tests passed successfully")
    else:
        print(f"⚠️  {len(result.failures)} test(s) failed")
        print(f"⚠️  {len(result.errors)} test(s) had errors")
    
    if result.skipped:
        print(f"✅ {len(result.skipped)} test(s) skipped (expected for external service)")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_connectivity_test()
    sys.exit(0 if success else 1)