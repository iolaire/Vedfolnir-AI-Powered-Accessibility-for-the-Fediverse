#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Health check script for external Ollama API connectivity from containers.
This script can be used in Docker health checks or monitoring systems.
"""

import sys
import os
import json
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from config import Config
except ImportError:
    # Fallback configuration if config module is not available
    class FallbackConfig:
        def __init__(self):
            self.ollama_url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
            self.ollama_model = os.getenv("OLLAMA_MODEL", "llava:7b")
            self.timeout = float(os.getenv("OLLAMA_TIMEOUT", "10.0"))


def check_ollama_health(config=None, verbose=False):
    """
    Check Ollama API health and return status information.
    
    Args:
        config: Configuration object (optional)
        verbose: Whether to print detailed output
        
    Returns:
        dict: Health check results
    """
    if config is None:
        try:
            config = Config()
            ollama_url = config.ollama.url
            model_name = config.ollama.model_name
            timeout = config.ollama.timeout
        except:
            config = FallbackConfig()
            ollama_url = config.ollama_url
            model_name = config.ollama_model
            timeout = config.timeout
    else:
        ollama_url = config.ollama.url
        model_name = config.ollama.model_name
        timeout = config.ollama.timeout
    
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "ollama_url": ollama_url,
        "model_name": model_name,
        "api_accessible": False,
        "version": None,
        "models_available": False,
        "required_model_available": False,
        "response_time_ms": None,
        "error": None
    }
    
    try:
        # Test API version endpoint
        start_time = time.time()
        
        if verbose:
            print(f"Checking Ollama API at: {ollama_url}")
        
        version_url = f"{ollama_url}/api/version"
        request = Request(version_url)
        request.add_header('User-Agent', 'Vedfolnir-Health-Check/1.0')
        
        with urlopen(request, timeout=timeout) as response:
            response_time = (time.time() - start_time) * 1000
            health_status["response_time_ms"] = round(response_time, 2)
            
            if response.getcode() == 200:
                health_status["api_accessible"] = True
                version_data = json.loads(response.read().decode('utf-8'))
                health_status["version"] = version_data.get("version", "unknown")
                
                if verbose:
                    print(f"✅ API accessible - Version: {health_status['version']}")
                    print(f"   Response time: {health_status['response_time_ms']}ms")
            else:
                health_status["error"] = f"API returned status {response.getcode()}"
                if verbose:
                    print(f"❌ API returned status {response.getcode()}")
                return health_status
        
        # Test models endpoint
        tags_url = f"{ollama_url}/api/tags"
        request = Request(tags_url)
        request.add_header('User-Agent', 'Vedfolnir-Health-Check/1.0')
        
        with urlopen(request, timeout=timeout) as response:
            if response.getcode() == 200:
                health_status["models_available"] = True
                tags_data = json.loads(response.read().decode('utf-8'))
                models = tags_data.get("models", [])
                model_names = [model.get("name", "") for model in models]
                
                if verbose:
                    print(f"✅ Models endpoint accessible - {len(models)} models found")
                
                # Check if required model is available
                if model_name in model_names:
                    health_status["required_model_available"] = True
                    if verbose:
                        print(f"✅ Required model '{model_name}' is available")
                else:
                    if verbose:
                        print(f"⚠️  Required model '{model_name}' not found")
                        print(f"   Available models: {model_names[:5]}")  # Show first 5
            else:
                health_status["error"] = f"Models endpoint returned status {response.getcode()}"
                if verbose:
                    print(f"❌ Models endpoint returned status {response.getcode()}")
    
    except HTTPError as e:
        health_status["error"] = f"HTTP error {e.code}: {e.reason}"
        if verbose:
            print(f"❌ HTTP error {e.code}: {e.reason}")
    
    except URLError as e:
        health_status["error"] = f"Connection error: {str(e.reason)}"
        if verbose:
            print(f"❌ Connection error: {str(e.reason)}")
    
    except Exception as e:
        health_status["error"] = f"Unexpected error: {str(e)}"
        if verbose:
            print(f"❌ Unexpected error: {str(e)}")
    
    return health_status


def main():
    """Main health check function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check external Ollama API health")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")
    parser.add_argument("--timeout", "-t", type=float, default=10.0, help="Request timeout in seconds")
    parser.add_argument("--url", "-u", help="Override Ollama URL")
    parser.add_argument("--model", "-m", help="Override model name to check")
    
    args = parser.parse_args()
    
    # Override configuration if specified
    config = None
    if args.url or args.model:
        class OverrideConfig:
            def __init__(self):
                try:
                    base_config = Config()
                    self.ollama_url = args.url or base_config.ollama.url
                    self.ollama_model = args.model or base_config.ollama.model_name
                    self.timeout = args.timeout
                except:
                    self.ollama_url = args.url or "http://host.docker.internal:11434"
                    self.ollama_model = args.model or "llava:7b"
                    self.timeout = args.timeout
        
        class ConfigWrapper:
            def __init__(self):
                override = OverrideConfig()
                self.ollama = type('obj', (object,), {
                    'url': override.ollama_url,
                    'model_name': override.ollama_model,
                    'timeout': override.timeout
                })
        
        config = ConfigWrapper()
    
    # Run health check
    health_status = check_ollama_health(config, verbose=args.verbose)
    
    # Output results
    if args.json:
        print(json.dumps(health_status, indent=2))
    else:
        if not args.verbose:
            # Summary output
            if health_status["api_accessible"]:
                print("✅ Ollama API is accessible")
                if health_status["required_model_available"]:
                    print("✅ Required model is available")
                else:
                    print("⚠️  Required model not available")
            else:
                print("❌ Ollama API is not accessible")
                if health_status["error"]:
                    print(f"   Error: {health_status['error']}")
    
    # Exit with appropriate code
    if health_status["api_accessible"]:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == "__main__":
    main()