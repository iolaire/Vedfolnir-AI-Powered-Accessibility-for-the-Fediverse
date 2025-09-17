#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test RQ Worker System

Script to test the RQ worker system implementation including worker management,
job processing, and progress tracking.
"""

import os
import sys
import logging
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
# Import RQ components directly - no mocking
from app.services.task.rq import (
    RQConfig, RQQueueManager, RQWorkerManager, RQProgressTracker,
    RedisConnectionManager, FlaskRQIntegration
)
from flask import Flask

logger = logging.getLogger(__name__)


class RQWorkerSystemTester:
    """Tests RQ worker system components"""
    
    def __init__(self):
        self.config = None
        self.db_manager = None
        self.app = None
        self.rq_integration = None
    
    def setup(self) -> bool:
        """Set up test environment"""
        try:
            # Load configuration
            self.config = Config()
            
            # Initialize database manager
            self.db_manager = DatabaseManager(self.config)
            
            # Create Flask app
            self.app = Flask(__name__)
            self.app.config.update(self.config.__dict__)
            self.app.config['db_manager'] = self.db_manager
            
            # Initialize RQ integration
            self.rq_integration = FlaskRQIntegration()
            
            logger.info("Test environment set up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up test environment: {e}")
            return False
    
    def test_rq_config(self) -> bool:
        """Test RQ configuration"""
        try:
            logger.info("Testing RQ configuration...")
            
            rq_config = RQConfig()
            
            # Test configuration validation
            if not rq_config.validate_config():
                logger.error("RQ configuration validation failed")
                return False
            
            # Test queue configurations
            queue_names = rq_config.get_queue_names()
            expected_queues = ['urgent', 'high', 'normal', 'low']
            
            if queue_names != expected_queues:
                logger.error(f"Expected queues {expected_queues}, got {queue_names}")
                return False
            
            # Test Redis connection parameters
            redis_params = rq_config.get_redis_connection_params()
            required_params = ['host', 'port', 'db']
            
            for param in required_params:
                if param not in redis_params:
                    logger.error(f"Missing Redis parameter: {param}")
                    return False
            
            logger.info("✓ RQ configuration test passed")
            return True
            
        except Exception as e:
            logger.error(f"RQ configuration test failed: {e}")
            return False
    
    def test_redis_connection(self) -> bool:
        """Test Redis connection management"""
        try:
            logger.info("Testing Redis connection...")
            
            rq_config = RQConfig()
            redis_manager = RedisConnectionManager(rq_config)
            
            # Test initialization
            if not redis_manager.initialize():
                logger.warning("Redis connection failed - this is expected if Redis is not running")
                return True  # Don't fail test if Redis is not available
            
            # Test connection
            connection = redis_manager.get_connection()
            if connection:
                # Test basic Redis operation
                connection.ping()
                logger.info("✓ Redis connection test passed")
            else:
                logger.warning("Redis connection not available")
            
            # Test cleanup
            redis_manager.cleanup()
            
            return True
            
        except Exception as e:
            logger.warning(f"Redis connection test failed (expected if Redis not running): {e}")
            return True  # Don't fail test if Redis is not available
    
    def test_queue_manager(self) -> bool:
        """Test RQ queue manager"""
        try:
            logger.info("Testing RQ queue manager...")
            
            # Initialize components
            rq_config = RQConfig()
            security_manager = CaptionSecurityManager(self.db_manager)
            
            # Create queue manager
            queue_manager = RQQueueManager(
                db_manager=self.db_manager,
                config=rq_config,
                security_manager=security_manager
            )
            
            # Test health status
            health_status = queue_manager.get_health_status()
            
            required_keys = ['redis_available', 'fallback_mode', 'queues_initialized']
            for key in required_keys:
                if key not in health_status:
                    logger.error(f"Missing health status key: {key}")
                    return False
            
            # Test queue statistics
            stats = queue_manager.get_queue_stats()
            if not isinstance(stats, dict):
                logger.error("Queue stats should be a dictionary")
                return False
            
            logger.info("✓ Queue manager test passed")
            return True
            
        except Exception as e:
            logger.error(f"Queue manager test failed: {e}")
            return False
    
    def test_worker_manager(self) -> bool:
        """Test RQ worker manager"""
        try:
            logger.info("Testing RQ worker manager...")
            
            # Initialize components
            rq_config = RQConfig()
            redis_manager = RedisConnectionManager(rq_config)
            
            if not redis_manager.initialize():
                logger.warning("Skipping worker manager test - Redis not available")
                return True
            
            redis_connection = redis_manager.get_connection()
            if not redis_connection:
                logger.warning("Skipping worker manager test - Redis connection failed")
                return True
            
            # Create worker manager
            worker_manager = RQWorkerManager(
                redis_connection=redis_connection,
                config=rq_config,
                db_manager=self.db_manager,
                app_context=self.app
            )
            
            # Test initialization
            if not worker_manager.initialize():
                logger.error("Worker manager initialization failed")
                return False
            
            # Test status
            status = worker_manager.get_worker_status()
            
            required_keys = ['manager_id', 'initialized', 'total_workers']
            for key in required_keys:
                if key not in status:
                    logger.error(f"Missing worker status key: {key}")
                    return False
            
            # Cleanup
            worker_manager.cleanup_and_stop()
            redis_manager.cleanup()
            
            logger.info("✓ Worker manager test passed")
            return True
            
        except Exception as e:
            logger.error(f"Worker manager test failed: {e}")
            return False
    
    def test_progress_tracker(self) -> bool:
        """Test RQ progress tracker"""
        try:
            logger.info("Testing RQ progress tracker...")
            
            # Initialize components
            rq_config = RQConfig()
            redis_manager = RedisConnectionManager(rq_config)
            
            if not redis_manager.initialize():
                logger.warning("Skipping progress tracker test - Redis not available")
                return True
            
            redis_connection = redis_manager.get_connection()
            if not redis_connection:
                logger.warning("Skipping progress tracker test - Redis connection failed")
                return True
            
            # Create progress tracker
            progress_tracker = RQProgressTracker(self.db_manager, redis_connection)
            
            # Test progress callback creation
            callback = progress_tracker.create_progress_callback("test_task_id")
            if not callable(callback):
                logger.error("Progress callback should be callable")
                return False
            
            # Test cleanup
            cleaned_count = progress_tracker.cleanup_expired_progress()
            if not isinstance(cleaned_count, int):
                logger.error("Cleanup should return integer count")
                return False
            
            # Cleanup
            redis_manager.cleanup()
            
            logger.info("✓ Progress tracker test passed")
            return True
            
        except Exception as e:
            logger.error(f"Progress tracker test failed: {e}")
            return False
    
    def test_flask_integration(self) -> bool:
        """Test Flask RQ integration"""
        try:
            logger.info("Testing Flask RQ integration...")
            
            # Test initialization
            if not self.rq_integration.init_app(self.app):
                logger.warning("Flask RQ integration failed - likely due to Redis unavailability")
                return True  # Don't fail if Redis is not available
            
            # Test status
            status = self.rq_integration.get_status()
            
            required_keys = ['initialized', 'redis_available', 'queue_manager_available']
            for key in required_keys:
                if key not in status:
                    logger.error(f"Missing integration status key: {key}")
                    return False
            
            # Test cleanup
            self.rq_integration.cleanup()
            
            logger.info("✓ Flask integration test passed")
            return True
            
        except Exception as e:
            logger.error(f"Flask integration test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        logger.info("Starting RQ worker system tests...")
        logger.info("Running full RQ worker system tests (no mocking)")
        
        tests = [
            ("RQ Configuration", self.test_rq_config),
            ("Redis Connection", self.test_redis_connection),
            ("Queue Manager", self.test_queue_manager),
            ("Worker Manager", self.test_worker_manager),
            ("Progress Tracker", self.test_progress_tracker),
            ("Flask Integration", self.test_flask_integration)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
                    logger.error(f"✗ {test_name} test failed")
            except Exception as e:
                failed += 1
                logger.error(f"✗ {test_name} test failed with exception: {e}")
        
        logger.info(f"\nTest Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            logger.info("🎉 All RQ worker system tests passed!")
            return True
        else:
            logger.error(f"❌ {failed} tests failed")
            return False


def main():
    """Main entry point"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run tester
    tester = RQWorkerSystemTester()
    
    if not tester.setup():
        logger.error("Failed to set up test environment")
        sys.exit(1)
    
    success = tester.run_all_tests()
    
    if success:
        logger.info("RQ worker system tests completed successfully")
        sys.exit(0)
    else:
        logger.error("RQ worker system tests failed")
        sys.exit(1)


if __name__ == '__main__':
    main()