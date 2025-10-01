#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Validate Docker networking configuration for Vedfolnir.
This script checks that all services can communicate properly via container networking.
"""

import os
import sys
import time
import requests
import mysql.connector
import redis
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def check_environment():
    """Check if running in Docker environment."""
    docker_deployment = os.getenv("DOCKER_DEPLOYMENT", "false").lower() == "true"
    
    if not docker_deployment:
        print("❌ DOCKER_DEPLOYMENT not set to true")
        print("   Set DOCKER_DEPLOYMENT=true in your .env file")
        return False
    
    print("✅ Docker deployment environment detected")
    return True

def check_mysql_connection():
    """Test MySQL connection using container networking."""
    try:
        mysql_password = os.getenv("MYSQL_PASSWORD")
        if not mysql_password:
            print("❌ MYSQL_PASSWORD not set in environment")
            return False
        
        # Try to connect to MySQL using container hostname
        connection = mysql.connector.connect(
            host='mysql',
            port=3306,
            user='vedfolnir',
            password=mysql_password,
            database='vedfolnir',
            charset='utf8mb4',
            connect_timeout=10
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if result and result[0] == 1:
            print("✅ MySQL connection successful (mysql:3306)")
            return True
        else:
            print("❌ MySQL connection failed - unexpected result")
            return False
            
    except mysql.connector.Error as e:
        print(f"❌ MySQL connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ MySQL connection error: {e}")
        return False

def check_redis_connection():
    """Test Redis connection using container networking."""
    try:
        redis_password = os.getenv("REDIS_PASSWORD")
        
        # Connect to Redis using container hostname
        if redis_password:
            redis_client = redis.Redis(
                host='redis',
                port=6379,
                db=0,
                password=redis_password,
                socket_connect_timeout=10
            )
        else:
            redis_client = redis.Redis(
                host='redis',
                port=6379,
                db=0,
                socket_connect_timeout=10
            )
        
        # Test connection
        response = redis_client.ping()
        
        if response:
            print("✅ Redis connection successful (redis:6379)")
            return True
        else:
            print("❌ Redis connection failed - no ping response")
            return False
            
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Redis connection error: {e}")
        return False

def check_ollama_connection():
    """Test Ollama connection using container networking."""
    try:
        # Test Ollama API endpoint
        response = requests.get(
            "http://ollama:11434/api/version",
            timeout=10
        )
        
        if response.status_code == 200:
            version_data = response.json()
            print(f"✅ Ollama connection successful (ollama:11434) - Version: {version_data.get('version', 'unknown')}")
            return True
        else:
            print(f"❌ Ollama connection failed - HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Ollama connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Ollama connection error: {e}")
        return False

def check_vault_connection():
    """Test Vault connection using container networking."""
    try:
        # Test Vault health endpoint
        response = requests.get(
            "http://vault:8200/v1/sys/health",
            timeout=10
        )
        
        # Vault returns 200 for initialized and unsealed, 429 for standby, 501 for not initialized
        if response.status_code in [200, 429, 501]:
            print("✅ Vault connection successful (vault:8200)")
            return True
        else:
            print(f"❌ Vault connection failed - HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Vault connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Vault connection error: {e}")
        return False

def check_prometheus_connection():
    """Test Prometheus connection using container networking."""
    try:
        # Test Prometheus API endpoint
        response = requests.get(
            "http://prometheus:9090/api/v1/status/config",
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Prometheus connection successful (prometheus:9090)")
            return True
        else:
            print(f"❌ Prometheus connection failed - HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Prometheus connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Prometheus connection error: {e}")
        return False

def check_grafana_connection():
    """Test Grafana connection using container networking."""
    try:
        # Test Grafana health endpoint
        response = requests.get(
            "http://grafana:3000/api/health",
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Grafana connection successful (grafana:3000)")
            return True
        else:
            print(f"❌ Grafana connection failed - HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Grafana connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Grafana connection error: {e}")
        return False

def check_loki_connection():
    """Test Loki connection using container networking."""
    try:
        # Test Loki ready endpoint
        response = requests.get(
            "http://loki:3100/ready",
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Loki connection successful (loki:3100)")
            return True
        else:
            print(f"❌ Loki connection failed - HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Loki connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Loki connection error: {e}")
        return False

def check_configuration():
    """Check configuration for container networking."""
    print("🔍 Checking configuration...")
    
    # Load environment from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check key configuration values
    database_url = os.getenv("DATABASE_URL", "")
    redis_url = os.getenv("REDIS_URL", "")
    ollama_url = os.getenv("OLLAMA_URL", "")
    
    config_ok = True
    
    if "mysql:3306" not in database_url:
        print("❌ DATABASE_URL should use 'mysql:3306' for container networking")
        config_ok = False
    else:
        print("✅ DATABASE_URL configured for container networking")
    
    if "redis:6379" not in redis_url:
        print("❌ REDIS_URL should use 'redis:6379' for container networking")
        config_ok = False
    else:
        print("✅ REDIS_URL configured for container networking")
    
    if "ollama:11434" not in ollama_url:
        print("❌ OLLAMA_URL should use 'ollama:11434' for container networking")
        config_ok = False
    else:
        print("✅ OLLAMA_URL configured for container networking")
    
    return config_ok

def main():
    """Main validation function."""
    print("🐳 Validating Docker networking configuration for Vedfolnir...")
    print("=" * 60)
    
    # Check if we're in Docker environment
    if not check_environment():
        sys.exit(1)
    
    print()
    
    # Check configuration
    config_ok = check_configuration()
    
    print()
    print("🔗 Testing service connections...")
    
    # Test all service connections
    tests = [
        ("MySQL Database", check_mysql_connection),
        ("Redis Cache", check_redis_connection),
        ("Ollama AI Service", check_ollama_connection),
        ("Vault Secrets", check_vault_connection),
        ("Prometheus Metrics", check_prometheus_connection),
        ("Grafana Dashboard", check_grafana_connection),
        ("Loki Logs", check_loki_connection),
    ]
    
    results = []
    for service_name, test_func in tests:
        print(f"\nTesting {service_name}...")
        try:
            result = test_func()
            results.append((service_name, result))
        except Exception as e:
            print(f"❌ {service_name} test failed with exception: {e}")
            results.append((service_name, False))
    
    print()
    print("=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    # Configuration summary
    if config_ok:
        print("✅ Configuration: PASSED")
    else:
        print("❌ Configuration: FAILED")
    
    # Service connection summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"🔗 Service Connections: {passed}/{total} PASSED")
    
    for service_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {service_name}: {status}")
    
    print()
    
    # Overall result
    overall_success = config_ok and all(result for _, result in results)
    
    if overall_success:
        print("🎉 ALL TESTS PASSED!")
        print("   Docker networking is configured correctly.")
        print("   All services can communicate via container networking.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("   Please check the failed services and configuration.")
        print("   Ensure all containers are running: docker-compose ps")
        print("   Check container logs: docker-compose logs <service_name>")
    
    print()
    print("💡 Troubleshooting tips:")
    print("   - Ensure all services are running: docker-compose up -d")
    print("   - Check service health: docker-compose ps")
    print("   - View logs: docker-compose logs -f")
    print("   - Restart services: docker-compose restart")
    print("   - Rebuild containers: docker-compose up -d --build")
    
    sys.exit(0 if overall_success else 1)

if __name__ == "__main__":
    main()