#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Start Integrated RQ Workers

Script to start RQ workers as integrated daemon threads within the current process.
This is useful for development and testing scenarios.
"""

import os
import sys
import logging
import signal
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
from app.services.task.rq.rq_config import RQConfig
from app.services.task.rq.redis_connection_manager import RedisConnectionManager
from app.services.task.rq.rq_queue_manager import RQQueueManager
from app.services.task.rq.rq_worker_manager import RQWorkerManager
from flask import Flask

logger = logging.getLogger(__name__)


class IntegratedWorkerRunner:
    """Runs integrated RQ workers in standalone mode"""
    
    def __init__(self):
        self.config = None
        self.db_manager = None
        self.worker_manager = None
        self.running = False
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def initialize(self) -> bool:
        """Initialize worker runner"""
        try:
            # Load configuration
            self.config = Config()
            
            # Initialize database manager
            self.db_manager = DatabaseManager(self.config)
            
            # Create minimal Flask app for context
            app = Flask(__name__)
            app.config.update(self.config.__dict__)
            app.config['db_manager'] = self.db_manager
            
            # Initialize RQ components
            rq_config = RQConfig()
            redis_manager = RedisConnectionManager(rq_config)
            
            if not redis_manager.initialize():
                logger.error("Failed to initialize Redis connection")
                return False
            
            redis_connection = redis_manager.get_connection()
            if not redis_connection:
                logger.error("Redis connection not available")
                return False
            
            # Initialize security manager
            security_manager = CaptionSecurityManager(self.db_manager)
            
            # Initialize queue manager
            queue_manager = RQQueueManager(
                db_manager=self.db_manager,
                config=rq_config,
                security_manager=security_manager
            )
            
            # Initialize worker manager
            self.worker_manager = RQWorkerManager(
                redis_connection=redis_connection,
                config=rq_config,
                db_manager=self.db_manager,
                app_context=app
            )
            
            if not self.worker_manager.initialize():
                logger.error("Failed to initialize worker manager")
                return False
            
            logger.info("Integrated worker runner initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize worker runner: {e}")
            return False
    
    def start(self) -> bool:
        """Start integrated workers"""
        if not self.worker_manager:
            logger.error("Worker manager not initialized")
            return False
        
        try:
            # Set worker mode to integrated
            os.environ['WORKER_MODE'] = 'integrated'
            
            # Start integrated workers
            if self.worker_manager.start_integrated_workers():
                self.running = True
                logger.info("Integrated workers started successfully")
                return True
            else:
                logger.error("Failed to start integrated workers")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start workers: {e}")
            return False
    
    def run(self) -> None:
        """Run workers and wait for shutdown signal"""
        if not self.running:
            logger.error("Workers not started")
            return
        
        try:
            logger.info("Integrated workers running. Press Ctrl+C to stop.")
            
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
                
                # Check worker health
                status = self.worker_manager.get_worker_status()
                if status['total_workers'] == 0:
                    logger.warning("No workers running - attempting restart")
                    self.worker_manager.start_integrated_workers()
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in worker run loop: {e}")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop workers gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping integrated workers...")
        self.running = False
        
        if self.worker_manager:
            self.worker_manager.stop_workers(graceful=True, timeout=30)
        
        logger.info("Integrated workers stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self.stop()


def main():
    """Main entry point"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run worker runner
    runner = IntegratedWorkerRunner()
    
    if not runner.initialize():
        logger.error("Failed to initialize worker runner")
        sys.exit(1)
    
    if not runner.start():
        logger.error("Failed to start workers")
        sys.exit(1)
    
    # Run workers
    runner.run()
    
    logger.info("Integrated worker runner finished")


if __name__ == '__main__':
    main()