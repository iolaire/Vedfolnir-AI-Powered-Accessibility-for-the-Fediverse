#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Hybrid RQ Deployment

Script to start both integrated and external RQ workers for optimal resource utilization.
Integrated workers handle urgent/high priority tasks, external workers handle normal/low priority.
"""

import os
import sys
import logging
import signal
import time
import subprocess
from pathlib import Path
from typing import List, Optional

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


class HybridDeploymentManager:
    """Manages hybrid deployment of integrated and external RQ workers"""
    
    def __init__(self):
        self.config = None
        self.db_manager = None
        self.worker_manager = None
        self.external_processes: List[subprocess.Popen] = []
        self.running = False
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def initialize(self) -> bool:
        """Initialize hybrid deployment manager"""
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
            
            logger.info("Hybrid deployment manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize hybrid deployment manager: {e}")
            return False
    
    def start_integrated_workers(self) -> bool:
        """Start integrated workers for urgent/high priority tasks"""
        if not self.worker_manager:
            logger.error("Worker manager not initialized")
            return False
        
        try:
            # Configure for integrated workers only (urgent/high priority)
            os.environ['WORKER_MODE'] = 'integrated'
            os.environ['RQ_URGENT_HIGH_WORKERS'] = '2'
            os.environ['RQ_NORMAL_WORKERS'] = '0'  # Disable normal workers
            os.environ['RQ_LOW_WORKERS'] = '0'     # Disable low workers
            
            # Start integrated workers
            if self.worker_manager.start_integrated_workers():
                logger.info("Integrated workers started for urgent/high priority tasks")
                return True
            else:
                logger.error("Failed to start integrated workers")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start integrated workers: {e}")
            return False
    
    def start_external_workers(self) -> bool:
        """Start external workers for normal/low priority tasks"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            worker_timeout = int(os.getenv('RQ_EXTERNAL_WORKER_TIMEOUT', '7200'))
            
            # External worker configurations
            external_configs = [
                {
                    'name': 'external-normal-1',
                    'queues': ['normal'],
                    'timeout': worker_timeout
                },
                {
                    'name': 'external-normal-2',
                    'queues': ['normal'],
                    'timeout': worker_timeout
                },
                {
                    'name': 'external-low-1',
                    'queues': ['low'],
                    'timeout': worker_timeout
                },
                {
                    'name': 'external-low-2',
                    'queues': ['low'],
                    'timeout': worker_timeout
                }
            ]
            
            success_count = 0
            
            for config in external_configs:
                try:
                    # Build RQ worker command
                    cmd = [
                        'rq', 'worker',
                        '--url', redis_url,
                        '--name', config['name'],
                        '--job-timeout', str(config['timeout']),
                        '--verbose'
                    ]
                    cmd.extend(config['queues'])
                    
                    # Start external process
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=os.environ.copy()
                    )
                    
                    self.external_processes.append(process)
                    success_count += 1
                    
                    logger.info(f"Started external worker {config['name']} (PID: {process.pid}) for queues {config['queues']}")
                    
                except Exception as e:
                    logger.error(f"Failed to start external worker {config['name']}: {e}")
            
            if success_count > 0:
                logger.info(f"Started {success_count} external workers successfully")
                return True
            else:
                logger.error("No external workers started successfully")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start external workers: {e}")
            return False
    
    def start(self) -> bool:
        """Start hybrid deployment"""
        try:
            logger.info("Starting hybrid RQ deployment...")
            
            # Start integrated workers first
            if not self.start_integrated_workers():
                logger.error("Failed to start integrated workers")
                return False
            
            # Start external workers
            if not self.start_external_workers():
                logger.error("Failed to start external workers")
                # Don't fail completely if external workers fail
                logger.warning("Continuing with integrated workers only")
            
            self.running = True
            logger.info("Hybrid deployment started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start hybrid deployment: {e}")
            return False
    
    def run(self) -> None:
        """Run hybrid deployment and monitor workers"""
        if not self.running:
            logger.error("Hybrid deployment not started")
            return
        
        try:
            logger.info("Hybrid deployment running. Press Ctrl+C to stop.")
            
            # Keep the main thread alive and monitor workers
            while self.running:
                time.sleep(10)  # Check every 10 seconds
                
                # Check integrated worker health
                if self.worker_manager:
                    status = self.worker_manager.get_worker_status()
                    if status['total_workers'] == 0:
                        logger.warning("No integrated workers running - attempting restart")
                        self.worker_manager.start_integrated_workers()
                
                # Check external worker health
                self._check_external_workers()
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in hybrid deployment run loop: {e}")
        finally:
            self.stop()
    
    def _check_external_workers(self) -> None:
        """Check health of external workers"""
        for i, process in enumerate(self.external_processes[:]):
            if process.poll() is not None:  # Process has terminated
                logger.warning(f"External worker process {process.pid} has terminated")
                self.external_processes.remove(process)
                
                # Optionally restart the worker here
                # For now, just log the termination
    
    def stop(self) -> None:
        """Stop hybrid deployment gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping hybrid deployment...")
        self.running = False
        
        # Stop integrated workers
        if self.worker_manager:
            self.worker_manager.stop_workers(graceful=True, timeout=30)
        
        # Stop external workers
        self._stop_external_workers()
        
        logger.info("Hybrid deployment stopped")
    
    def _stop_external_workers(self) -> None:
        """Stop external worker processes"""
        for process in self.external_processes:
            try:
                logger.info(f"Stopping external worker process {process.pid}")
                
                # Send SIGTERM for graceful shutdown
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=30)
                    logger.info(f"External worker {process.pid} stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if timeout exceeded
                    process.kill()
                    process.wait()
                    logger.warning(f"Force killed external worker {process.pid}")
                    
            except Exception as e:
                logger.error(f"Error stopping external worker {process.pid}: {e}")
        
        self.external_processes.clear()
    
    def get_status(self) -> dict:
        """Get deployment status"""
        status = {
            'running': self.running,
            'integrated_workers': 0,
            'external_workers': len(self.external_processes),
            'total_workers': 0
        }
        
        if self.worker_manager:
            worker_status = self.worker_manager.get_worker_status()
            status['integrated_workers'] = worker_status['total_workers']
        
        status['total_workers'] = status['integrated_workers'] + status['external_workers']
        
        return status
    
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
    
    # Create and run hybrid deployment manager
    manager = HybridDeploymentManager()
    
    if not manager.initialize():
        logger.error("Failed to initialize hybrid deployment manager")
        sys.exit(1)
    
    if not manager.start():
        logger.error("Failed to start hybrid deployment")
        sys.exit(1)
    
    # Run deployment
    manager.run()
    
    logger.info("Hybrid deployment finished")


if __name__ == '__main__':
    main()