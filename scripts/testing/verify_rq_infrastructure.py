#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Infrastructure Verification Script

Verifies that the RQ infrastructure components are properly set up and configured.
This script tests the basic functionality without requiring a Redis server.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.task.rq import (
    RQConfig, 
    WorkerMode, 
    TaskPriority, 
    RedisHealthMonitor, 
    RedisConnectionManager,
    rq_config
)


def main():
    """Main verification function"""
    print("=== RQ Infrastructure Verification ===")
    print()
    
    # Test 1: Configuration Loading
    print("1. Testing RQ Configuration...")
    try:
        config = RQConfig()
        print(f"   ✓ Redis URL: {config.redis_url}")
        print(f"   ✓ Worker Mode: {config.worker_mode.value}")
        print(f"   ✓ Worker Count: {config.worker_count}")
        print(f"   ✓ Queue Prefix: {config.queue_prefix}")
        print(f"   ✓ Health Check Interval: {config.health_check_interval}s")
        print("   ✓ Configuration loaded successfully")
    except Exception as e:
        print(f"   ✗ Configuration failed: {e}")
        return False
    
    # Test 2: Configuration Validation
    print("\n2. Testing Configuration Validation...")
    try:
        is_valid = config.validate_config()
        if is_valid:
            print("   ✓ Configuration validation passed")
        else:
            print("   ✗ Configuration validation failed")
            return False
    except Exception as e:
        print(f"   ✗ Validation error: {e}")
        return False
    
    # Test 3: Queue Configurations
    print("\n3. Testing Queue Configurations...")
    try:
        queue_configs = config.queue_configs
        queue_names = config.get_queue_names()
        
        print(f"   ✓ Priority queues: {', '.join(queue_names)}")
        
        for priority in [TaskPriority.URGENT, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
            queue_config = queue_configs[priority.value]
            print(f"   ✓ {priority.value}: {queue_config.max_workers} workers, {queue_config.timeout}s timeout")
        
        print("   ✓ Queue configurations verified")
    except Exception as e:
        print(f"   ✗ Queue configuration error: {e}")
        return False
    
    # Test 4: Worker Configurations
    print("\n4. Testing Worker Configurations...")
    try:
        worker_configs = config.worker_configs
        
        for worker_id, worker_config in worker_configs.items():
            print(f"   ✓ {worker_id}: queues={worker_config.queues}, concurrency={worker_config.concurrency}")
        
        print("   ✓ Worker configurations verified")
    except Exception as e:
        print(f"   ✗ Worker configuration error: {e}")
        return False
    
    # Test 5: Redis Connection Parameters
    print("\n5. Testing Redis Connection Parameters...")
    try:
        params = config.get_redis_connection_params()
        
        print(f"   ✓ Host: {params['host']}")
        print(f"   ✓ Port: {params['port']}")
        print(f"   ✓ Database: {params['db']}")
        print(f"   ✓ Decode Responses: {params['decode_responses']}")
        print(f"   ✓ Connection Timeout: {params['socket_connect_timeout']}s")
        print("   ✓ Redis connection parameters verified")
    except Exception as e:
        print(f"   ✗ Redis parameter error: {e}")
        return False
    
    # Test 6: Enums and Constants
    print("\n6. Testing Enums and Constants...")
    try:
        # Test WorkerMode enum
        modes = [WorkerMode.INTEGRATED, WorkerMode.EXTERNAL, WorkerMode.HYBRID]
        print(f"   ✓ Worker modes: {[mode.value for mode in modes]}")
        
        # Test TaskPriority enum
        priorities = [TaskPriority.URGENT, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]
        print(f"   ✓ Task priorities: {[priority.value for priority in priorities]}")
        
        print("   ✓ Enums and constants verified")
    except Exception as e:
        print(f"   ✗ Enum error: {e}")
        return False
    
    # Test 7: Global Configuration Instance
    print("\n7. Testing Global Configuration Instance...")
    try:
        global_config = rq_config
        print(f"   ✓ Global config worker mode: {global_config.worker_mode.value}")
        print(f"   ✓ Global config validation: {global_config.validate_config()}")
        print("   ✓ Global configuration instance verified")
    except Exception as e:
        print(f"   ✗ Global config error: {e}")
        return False
    
    # Test 8: Configuration Serialization
    print("\n8. Testing Configuration Serialization...")
    try:
        config_dict = config.to_dict()
        
        required_keys = [
            'redis_url', 'worker_mode', 'worker_count', 'queue_configs', 'worker_configs'
        ]
        
        for key in required_keys:
            if key not in config_dict:
                print(f"   ✗ Missing key in serialization: {key}")
                return False
        
        print(f"   ✓ Serialized {len(config_dict)} configuration keys")
        print("   ✓ Configuration serialization verified")
    except Exception as e:
        print(f"   ✗ Serialization error: {e}")
        return False
    
    print("\n=== Verification Complete ===")
    print("✅ All RQ infrastructure components verified successfully!")
    print()
    print("Next steps:")
    print("1. Install Redis server if not already installed")
    print("2. Configure Redis connection in .env file")
    print("3. Run integration tests: python -m unittest tests.integration.test_rq_infrastructure")
    print("4. Proceed to implement RQ Queue Manager (Task 2)")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)