#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Security and Data Retention Demo

Demonstrates the security and data retention features of the RQ system,
including encryption, access control, retention policies, and cleanup.
"""

import os
import sys
import logging
from unittest.mock import Mock
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
from app.services.task.rq.rq_security_manager import RQSecurityManager
from app.services.task.rq.rq_data_retention_manager import RQDataRetentionManager
from app.services.task.rq.rq_retention_config import (
    get_retention_config_manager, 
    create_retention_policy
)
from app.services.task.rq.rq_config import RQConfig

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_demo_environment():
    """Set up demo environment with proper encryption key"""
    from cryptography.fernet import Fernet
    
    # Generate a proper Fernet key for demo
    if 'PLATFORM_ENCRYPTION_KEY' not in os.environ:
        demo_key = Fernet.generate_key().decode()
        os.environ['PLATFORM_ENCRYPTION_KEY'] = demo_key
        logger.info("Generated demo encryption key")
    
    # Set demo retention policy
    os.environ['RQ_RETENTION_POLICY'] = 'development'
    os.environ['RQ_COMPLETED_TASKS_TTL'] = '1800'  # 30 minutes for demo
    os.environ['RQ_MEMORY_WARNING_THRESHOLD_MB'] = '100'
    os.environ['RQ_MEMORY_CRITICAL_THRESHOLD_MB'] = '128'


def demo_security_features():
    """Demonstrate RQ security features"""
    logger.info("=== RQ Security Features Demo ===")
    
    try:
        # Mock dependencies for demo
        mock_db_manager = Mock(spec=DatabaseManager)
        mock_redis = Mock()
        mock_caption_security = Mock(spec=CaptionSecurityManager)
        mock_caption_security.generate_secure_task_id.return_value = "demo-task-12345"
        mock_caption_security.validate_task_id.return_value = True
        mock_caption_security.check_task_ownership.return_value = True
        
        # Initialize security manager
        security_manager = RQSecurityManager(
            mock_db_manager,
            mock_redis,
            mock_caption_security
        )
        
        logger.info("✅ RQ Security Manager initialized successfully")
        
        # Demo 1: Secure task ID generation
        task_id = security_manager.generate_secure_task_id()
        logger.info(f"Generated secure task ID: {task_id}")
        
        # Demo 2: Task data encryption
        sensitive_data = {
            'task_id': task_id,
            'user_id': 1,
            'access_token': 'sensitive_demo_token_12345',
            'normal_field': 'public_data'
        }
        
        encrypted_data = security_manager.encrypt_task_data(sensitive_data)
        logger.info(f"Encrypted task data: {len(encrypted_data)} bytes")
        
        decrypted_data = security_manager.decrypt_task_data(encrypted_data)
        logger.info(f"Decrypted task data: {len(decrypted_data)} fields")
        
        # Demo 3: Error message sanitization
        error_with_sensitive_info = "Database error: password=secret123 token=abc123 at /path/to/file"
        sanitized_error = security_manager.sanitize_error_message(error_with_sensitive_info, task_id)
        logger.info(f"Original error: {error_with_sensitive_info}")
        logger.info(f"Sanitized error: {sanitized_error}")
        
        # Demo 4: Security event logging
        security_manager.log_security_event(
            'demo_security_test',
            {
                'task_id': task_id,
                'demo_field': 'demo_value',
                'access_token': 'should_be_masked'
            },
            user_id=1
        )
        logger.info("Security event logged successfully")
        
        # Demo 5: Security metrics
        metrics = security_manager.get_security_metrics()
        logger.info(f"Security metrics: {metrics}")
        
        logger.info("✅ Security features demo completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Security demo failed: {e}")
        raise


def demo_retention_features():
    """Demonstrate RQ data retention features"""
    logger.info("=== RQ Data Retention Features Demo ===")
    
    try:
        # Get retention configuration manager
        config_manager = get_retention_config_manager()
        logger.info("✅ Retention configuration manager initialized")
        
        # Demo 1: Show available policies
        available_policies = config_manager.get_available_policies()
        logger.info(f"Available retention policies: {list(available_policies.keys())}")
        
        # Demo 2: Create retention policy
        dev_policy = create_retention_policy('development')
        logger.info(f"Development policy: {dev_policy.name}")
        logger.info(f"  - Completed tasks TTL: {dev_policy.completed_tasks_ttl}s")
        logger.info(f"  - Failed tasks TTL: {dev_policy.failed_tasks_ttl}s")
        logger.info(f"  - Max memory: {dev_policy.max_memory_usage_mb}MB")
        logger.info(f"  - Cleanup threshold: {dev_policy.cleanup_threshold_mb}MB")
        
        # Demo 3: Create custom policy
        custom_result = config_manager.update_policy(
            'demo_policy',
            description='Demo policy for testing',
            completed_tasks_ttl=900,  # 15 minutes
            failed_tasks_ttl=1800,    # 30 minutes
            max_memory_usage_mb=64,   # 64 MB
            cleanup_threshold_mb=48   # 48 MB
        )
        logger.info(f"Custom policy created: {custom_result}")
        
        # Demo 4: Create policy from custom definition
        custom_policy = config_manager.create_retention_policy('demo_policy')
        logger.info(f"Custom policy: {custom_policy.name}")
        logger.info(f"  - Description: {custom_policy.description}")
        logger.info(f"  - Completed tasks TTL: {custom_policy.completed_tasks_ttl}s")
        
        # Demo 5: Configuration export/import
        exported_config = config_manager.export_configuration()
        logger.info(f"Exported configuration keys: {list(exported_config.keys())}")
        
        # Demo 6: Mock data retention manager
        mock_db_manager = Mock(spec=DatabaseManager)
        mock_redis = Mock()
        mock_rq_config = Mock(spec=RQConfig)
        mock_queues = {}
        
        retention_manager = RQDataRetentionManager(
            mock_db_manager,
            mock_redis,
            mock_rq_config,
            mock_queues
        )
        logger.info("✅ Data retention manager initialized")
        
        # Demo 7: Retention status
        # Mock Redis operations for demo
        mock_redis.info.return_value = {'used_memory': 1024 * 1024 * 50}  # 50 MB
        mock_redis.scan_iter.return_value = [b'demo-key-1', b'demo-key-2']
        
        status = retention_manager.get_retention_status()
        logger.info(f"Retention status: {status['active_policy']['name']}")
        logger.info(f"Memory usage: {status['memory_usage']['current_mb']:.2f}MB")
        logger.info(f"Monitoring active: {status['monitoring']['active']}")
        
        logger.info("✅ Data retention features demo completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Retention demo failed: {e}")
        raise


def demo_integration_features():
    """Demonstrate integration between security and retention"""
    logger.info("=== Integration Features Demo ===")
    
    try:
        # Demo 1: Policy-based TTL management
        config_manager = get_retention_config_manager()
        
        # Show how different policies affect TTLs
        policies_to_test = ['development', 'default', 'high_volume', 'conservative']
        
        for policy_name in policies_to_test:
            policy = config_manager.create_retention_policy(policy_name)
            logger.info(f"{policy_name} policy TTLs:")
            logger.info(f"  - Completed: {policy.completed_tasks_ttl}s ({policy.completed_tasks_ttl/3600:.1f}h)")
            logger.info(f"  - Failed: {policy.failed_tasks_ttl}s ({policy.failed_tasks_ttl/3600:.1f}h)")
            logger.info(f"  - Security logs: {policy.security_logs_ttl}s ({policy.security_logs_ttl/86400:.1f}d)")
        
        # Demo 2: Configuration overrides
        logger.info("Configuration overrides in effect:")
        config = config_manager.get_config()
        if config.completed_tasks_ttl_override:
            logger.info(f"  - Completed tasks TTL override: {config.completed_tasks_ttl_override}s")
        if config.memory_warning_threshold_mb:
            logger.info(f"  - Memory warning threshold: {config.memory_warning_threshold_mb}MB")
        if config.memory_critical_threshold_mb:
            logger.info(f"  - Memory critical threshold: {config.memory_critical_threshold_mb}MB")
        
        logger.info("✅ Integration features demo completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Integration demo failed: {e}")
        raise


def main():
    """Main demo function"""
    logger.info("Starting RQ Security and Data Retention Demo")
    
    try:
        # Setup demo environment
        setup_demo_environment()
        logger.info("Demo environment set up")
        
        # Run demos
        demo_security_features()
        print()  # Add spacing
        
        demo_retention_features()
        print()  # Add spacing
        
        demo_integration_features()
        
        logger.info("🎉 All demos completed successfully!")
        
        # Show summary
        print("\n" + "="*60)
        print("DEMO SUMMARY")
        print("="*60)
        print("✅ Security Features:")
        print("   - Secure task ID generation")
        print("   - Task data encryption/decryption")
        print("   - Error message sanitization")
        print("   - Security event logging")
        print("   - Security metrics collection")
        print()
        print("✅ Data Retention Features:")
        print("   - Configurable retention policies")
        print("   - Environment-based configuration")
        print("   - Custom policy management")
        print("   - Memory usage monitoring")
        print("   - Automatic cleanup scheduling")
        print()
        print("✅ Integration Features:")
        print("   - Policy-based TTL management")
        print("   - Configuration overrides")
        print("   - Unified security and retention")
        print("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)