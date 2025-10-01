#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Individual Component Test Runner
Quick testing of individual Docker Compose components
"""

import os
import sys
import argparse
import subprocess
import time
import requests
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def log(message, level='INFO'):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {level}: {message}")


def test_basic_connectivity(base_url):
    """Test basic connectivity to the application"""
    log("Testing basic connectivity...")
    
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            log("✅ Basic connectivity: OK", 'SUCCESS')
            return True
        else:
            log(f"❌ Basic connectivity: HTTP {response.status_code}", 'ERROR')
            return False
    except Exception as e:
        log(f"❌ Basic connectivity: {e}", 'ERROR')
        return False


def test_docker_containers():
    """Test Docker container status"""
    log("Testing Docker container status...")
    
    try:
        result = subprocess.run(['docker-compose', 'ps'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            output = result.stdout
            if 'Up' in output:
                log("✅ Docker containers: Running", 'SUCCESS')
                return True
            else:
                log("❌ Docker containers: Not all containers running", 'ERROR')
                return False
        else:
            log("❌ Docker containers: docker-compose ps failed", 'ERROR')
            return False
    except Exception as e:
        log(f"❌ Docker containers: {e}", 'ERROR')
        return False


def test_database_connectivity():
    """Test database connectivity"""
    log("Testing database connectivity...")
    
    try:
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as session:
            result = session.execute('SELECT 1').scalar()
            if result == 1:
                log("✅ Database connectivity: OK", 'SUCCESS')
                return True
            else:
                log("❌ Database connectivity: Query failed", 'ERROR')
                return False
                
    except Exception as e:
        log(f"❌ Database connectivity: {e}", 'ERROR')
        return False


def test_redis_connectivity():
    """Test Redis connectivity"""
    log("Testing Redis connectivity...")
    
    try:
        import redis
        
        redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
        
        if redis_client.ping():
            log("✅ Redis connectivity: OK", 'SUCCESS')
            return True
        else:
            log("❌ Redis connectivity: Ping failed", 'ERROR')
            return False
            
    except Exception as e:
        log(f"❌ Redis connectivity: {e}", 'ERROR')
        return False


def test_ollama_connectivity():
    """Test Ollama API connectivity"""
    log("Testing Ollama API connectivity...")
    
    try:
        ollama_url = os.getenv('OLLAMA_URL', 'http://host.docker.internal:11434')
        response = requests.get(f"{ollama_url}/api/version", timeout=10)
        
        if response.status_code == 200:
            version_info = response.json()
            log(f"✅ Ollama API: Connected (version: {version_info.get('version', 'unknown')})", 'SUCCESS')
            return True
        else:
            log(f"❌ Ollama API: HTTP {response.status_code}", 'ERROR')
            return False
            
    except Exception as e:
        log(f"❌ Ollama API: {e}", 'ERROR')
        return False


def test_web_interface(base_url):
    """Test web interface endpoints"""
    log("Testing web interface...")
    
    endpoints = [
        ('/', 'Landing page'),
        ('/login', 'Login page'),
        ('/health', 'Health check'),
        ('/api/health', 'API health')
    ]
    
    all_passed = True
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                log(f"✅ {description}: OK", 'SUCCESS')
            else:
                log(f"❌ {description}: HTTP {response.status_code}", 'ERROR')
                all_passed = False
        except Exception as e:
            log(f"❌ {description}: {e}", 'ERROR')
            all_passed = False
    
    return all_passed


def test_volume_mounts():
    """Test volume mounts"""
    log("Testing volume mounts...")
    
    volume_paths = [
        ('./storage', 'Storage volume'),
        ('./logs', 'Logs volume'),
        ('./config', 'Configuration volume'),
        ('./data/mysql', 'MySQL data volume'),
        ('./data/redis', 'Redis data volume'),
    ]
    
    all_passed = True
    
    for path, description in volume_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                log(f"✅ {description}: {path} exists", 'SUCCESS')
            else:
                log(f"❌ {description}: {path} is not a directory", 'ERROR')
                all_passed = False
        else:
            log(f"⚠️  {description}: {path} does not exist", 'WARNING')
    
    return all_passed


def run_quick_validation(base_url):
    """Run quick validation of all components"""
    log("Starting quick component validation...")
    
    tests = [
        ("Docker Containers", test_docker_containers),
        ("Basic Connectivity", lambda: test_basic_connectivity(base_url)),
        ("Database Connectivity", test_database_connectivity),
        ("Redis Connectivity", test_redis_connectivity),
        ("Ollama Connectivity", test_ollama_connectivity),
        ("Web Interface", lambda: test_web_interface(base_url)),
        ("Volume Mounts", test_volume_mounts),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        log(f"Running {test_name} test...")
        try:
            if test_func():
                passed_tests += 1
            else:
                log(f"Test {test_name} failed", 'ERROR')
        except Exception as e:
            log(f"Test {test_name} failed with exception: {e}", 'ERROR')
    
    # Summary
    log("=== QUICK VALIDATION SUMMARY ===")
    log(f"Total tests: {total_tests}")
    log(f"Passed: {passed_tests}")
    log(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        log("🎉 All quick validation tests passed!", 'SUCCESS')
        return True
    else:
        log(f"❌ {total_tests - passed_tests} tests failed", 'ERROR')
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test individual Docker Compose components')
    parser.add_argument('--base-url', default='http://localhost:5000',
                       help='Base URL for the application')
    parser.add_argument('--component', choices=[
        'connectivity', 'containers', 'database', 'redis', 'ollama', 
        'web', 'volumes', 'all'
    ], default='all', help='Specific component to test')
    parser.add_argument('--wait', type=int, default=10,
                       help='Seconds to wait before testing')
    
    args = parser.parse_args()
    
    if args.wait > 0:
        log(f"Waiting {args.wait} seconds before testing...")
        time.sleep(args.wait)
    
    if args.component == 'all':
        success = run_quick_validation(args.base_url)
    elif args.component == 'connectivity':
        success = test_basic_connectivity(args.base_url)
    elif args.component == 'containers':
        success = test_docker_containers()
    elif args.component == 'database':
        success = test_database_connectivity()
    elif args.component == 'redis':
        success = test_redis_connectivity()
    elif args.component == 'ollama':
        success = test_ollama_connectivity()
    elif args.component == 'web':
        success = test_web_interface(args.base_url)
    elif args.component == 'volumes':
        success = test_volume_mounts()
    else:
        log(f"Unknown component: {args.component}", 'ERROR')
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()