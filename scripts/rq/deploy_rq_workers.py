#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Worker Deployment Script

Supports deployment of both integrated workers (within Gunicorn) and 
external worker processes for different deployment scenarios.
"""

import os
import sys
import argparse
import subprocess
import signal
import time
import logging
from typing import List, Dict, Any, Optional
import psutil

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.services.task.rq.rq_config import RQConfig, WorkerMode

logger = logging.getLogger(__name__)


class RQWorkerDeployment:
    """Manages deployment of RQ workers in different modes"""
    
    def __init__(self):
        self.config = Config()
        self.rq_config = RQConfig()
        self.processes: Dict[str, subprocess.Popen] = {}
        self.pid_file = os.path.join(os.getcwd(), 'rq_workers.pid')
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def deploy_integrated_mode(self) -> bool:
        """
        Deploy in integrated mode (workers run within Gunicorn)
        
        Returns:
            bool: True if deployment successful
        """
        logger.info("Deploying RQ workers in integrated mode")
        
        try:
            # Set environment variables for integrated mode
            env = os.environ.copy()
            env.update({
                'WORKER_MODE': 'integrated',
                'RQ_ENABLE_INTEGRATED_WORKERS': 'true',
                'RQ_ENABLE_EXTERNAL_WORKERS': 'false',
                'RQ_STARTUP_DELAY': '5'
            })
            
            # Start Gunicorn with integrated workers
            gunicorn_cmd = self._build_gunicorn_command()
            
            logger.info(f"Starting Gunicorn with integrated RQ workers: {' '.join(gunicorn_cmd)}")
            
            process = subprocess.Popen(
                gunicorn_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes['gunicorn'] = process
            self._save_pid_file()
            
            logger.info(f"Gunicorn started with PID {process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy integrated mode: {e}")
            return False
    
    def deploy_external_mode(self) -> bool:
        """
        Deploy in external mode (separate RQ worker processes)
        
        Returns:
            bool: True if deployment successful
        """
        logger.info("Deploying RQ workers in external mode")
        
        try:
            # Start Gunicorn without integrated workers
            env = os.environ.copy()
            env.update({
                'WORKER_MODE': 'external',
                'RQ_ENABLE_INTEGRATED_WORKERS': 'false',
                'RQ_ENABLE_EXTERNAL_WORKERS': 'false'  # Will start separately
            })
            
            gunicorn_cmd = self._build_gunicorn_command()
            
            logger.info(f"Starting Gunicorn: {' '.join(gunicorn_cmd)}")
            
            gunicorn_process = subprocess.Popen(
                gunicorn_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes['gunicorn'] = gunicorn_process
            
            # Wait for Gunicorn to start
            time.sleep(3)
            
            # Start external RQ workers
            if not self._start_external_workers():
                logger.error("Failed to start external workers")
                return False
            
            self._save_pid_file()
            
            logger.info("External mode deployment completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy external mode: {e}")
            return False
    
    def deploy_hybrid_mode(self) -> bool:
        """
        Deploy in hybrid mode (both integrated and external workers)
        
        Returns:
            bool: True if deployment successful
        """
        logger.info("Deploying RQ workers in hybrid mode")
        
        try:
            # Start Gunicorn with integrated workers
            env = os.environ.copy()
            env.update({
                'WORKER_MODE': 'hybrid',
                'RQ_ENABLE_INTEGRATED_WORKERS': 'true',
                'RQ_ENABLE_EXTERNAL_WORKERS': 'false',  # Will start separately
                'RQ_STARTUP_DELAY': '5'
            })
            
            gunicorn_cmd = self._build_gunicorn_command()
            
            logger.info(f"Starting Gunicorn with integrated workers: {' '.join(gunicorn_cmd)}")
            
            gunicorn_process = subprocess.Popen(
                gunicorn_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes['gunicorn'] = gunicorn_process
            
            # Wait for Gunicorn to start
            time.sleep(5)
            
            # Start additional external workers
            if not self._start_external_workers():
                logger.error("Failed to start external workers")
                return False
            
            self._save_pid_file()
            
            logger.info("Hybrid mode deployment completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy hybrid mode: {e}")
            return False
    
    def _build_gunicorn_command(self) -> List[str]:
        """Build Gunicorn command with appropriate settings"""
        workers = int(os.getenv('GUNICORN_WORKERS', '4'))
        bind = os.getenv('GUNICORN_BIND', '0.0.0.0:8000')
        timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
        
        cmd = [
            'gunicorn',
            '--workers', str(workers),
            '--bind', bind,
            '--timeout', str(timeout),
            '--worker-class', 'sync',
            '--max-requests', '1000',
            '--max-requests-jitter', '100',
            '--preload',
            'web_app:app'
        ]
        
        # Add additional Gunicorn options if specified
        if os.getenv('GUNICORN_ACCESS_LOG'):
            cmd.extend(['--access-logfile', os.getenv('GUNICORN_ACCESS_LOG')])
        
        if os.getenv('GUNICORN_ERROR_LOG'):
            cmd.extend(['--error-logfile', os.getenv('GUNICORN_ERROR_LOG')])
        
        return cmd
    
    def _start_external_workers(self) -> bool:
        """Start external RQ worker processes"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            
            # Configuration for external workers
            external_workers = [
                {
                    'name': 'urgent-high-worker',
                    'queues': ['urgent', 'high'],
                    'count': int(os.getenv('RQ_EXTERNAL_URGENT_HIGH_WORKERS', '1'))
                },
                {
                    'name': 'normal-worker',
                    'queues': ['normal'],
                    'count': int(os.getenv('RQ_EXTERNAL_NORMAL_WORKERS', '2'))
                },
                {
                    'name': 'low-worker',
                    'queues': ['low'],
                    'count': int(os.getenv('RQ_EXTERNAL_LOW_WORKERS', '2'))
                }
            ]
            
            for worker_config in external_workers:
                for i in range(worker_config['count']):
                    worker_name = f"{worker_config['name']}-{i}"
                    
                    cmd = [
                        'rq', 'worker',
                        '--url', redis_url,
                        '--name', worker_name,
                        '--job-timeout', str(self.rq_config.worker_timeout)
                    ]
                    
                    # Add queues
                    cmd.extend(worker_config['queues'])
                    
                    logger.info(f"Starting external worker {worker_name}: {' '.join(cmd)}")
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=os.environ.copy()
                    )
                    
                    self.processes[worker_name] = process
                    logger.info(f"External worker {worker_name} started with PID {process.pid}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start external workers: {e}")
            return False
    
    def _save_pid_file(self) -> None:
        """Save process PIDs to file"""
        try:
            with open(self.pid_file, 'w') as f:
                for name, process in self.processes.items():
                    f.write(f"{name}:{process.pid}\n")
            
            logger.info(f"PIDs saved to {self.pid_file}")
            
        except Exception as e:
            logger.error(f"Failed to save PID file: {e}")
    
    def stop_deployment(self) -> bool:
        """Stop all deployed processes"""
        logger.info("Stopping RQ worker deployment")
        
        success = True
        
        # Stop processes gracefully
        for name, process in self.processes.items():
            try:
                logger.info(f"Stopping {name} (PID: {process.pid})")
                
                # Send SIGTERM for graceful shutdown
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=30)
                    logger.info(f"{name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if timeout exceeded
                    logger.warning(f"Force killing {name}")
                    process.kill()
                    process.wait()
                    success = False
                    
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
                success = False
        
        # Clean up PID file
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                logger.info("PID file removed")
        except Exception as e:
            logger.error(f"Failed to remove PID file: {e}")
        
        self.processes.clear()
        
        return success
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get status of deployed processes"""
        status = {
            'processes': {},
            'total_processes': len(self.processes),
            'running_processes': 0,
            'failed_processes': 0
        }
        
        for name, process in self.processes.items():
            try:
                # Check if process is still running
                if process.poll() is None:
                    # Process is running
                    proc_info = psutil.Process(process.pid)
                    status['processes'][name] = {
                        'pid': process.pid,
                        'status': 'running',
                        'cpu_percent': proc_info.cpu_percent(),
                        'memory_mb': proc_info.memory_info().rss / 1024 / 1024,
                        'create_time': proc_info.create_time()
                    }
                    status['running_processes'] += 1
                else:
                    # Process has terminated
                    status['processes'][name] = {
                        'pid': process.pid,
                        'status': 'terminated',
                        'return_code': process.returncode
                    }
                    status['failed_processes'] += 1
                    
            except psutil.NoSuchProcess:
                status['processes'][name] = {
                    'pid': process.pid,
                    'status': 'not_found'
                }
                status['failed_processes'] += 1
            except Exception as e:
                status['processes'][name] = {
                    'pid': process.pid,
                    'status': 'error',
                    'error': str(e)
                }
                status['failed_processes'] += 1
        
        return status
    
    def restart_deployment(self, mode: str) -> bool:
        """Restart deployment in specified mode"""
        logger.info(f"Restarting deployment in {mode} mode")
        
        # Stop current deployment
        if not self.stop_deployment():
            logger.warning("Some processes did not stop gracefully")
        
        # Wait a moment
        time.sleep(2)
        
        # Start in new mode
        if mode == 'integrated':
            return self.deploy_integrated_mode()
        elif mode == 'external':
            return self.deploy_external_mode()
        elif mode == 'hybrid':
            return self.deploy_hybrid_mode()
        else:
            logger.error(f"Unknown deployment mode: {mode}")
            return False


def main():
    """Main deployment script"""
    parser = argparse.ArgumentParser(description='Deploy RQ workers')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'],
                       help='Action to perform')
    parser.add_argument('--mode', choices=['integrated', 'external', 'hybrid'],
                       default='integrated', help='Worker deployment mode')
    parser.add_argument('--config-check', action='store_true',
                       help='Check configuration before deployment')
    
    args = parser.parse_args()
    
    deployment = RQWorkerDeployment()
    
    # Configuration check
    if args.config_check or args.action == 'start':
        if not deployment.rq_config.validate_config():
            logger.error("Configuration validation failed")
            sys.exit(1)
        logger.info("Configuration validation passed")
    
    try:
        if args.action == 'start':
            success = False
            
            if args.mode == 'integrated':
                success = deployment.deploy_integrated_mode()
            elif args.mode == 'external':
                success = deployment.deploy_external_mode()
            elif args.mode == 'hybrid':
                success = deployment.deploy_hybrid_mode()
            
            if success:
                logger.info(f"RQ workers deployed successfully in {args.mode} mode")
                
                # Keep script running to monitor processes
                try:
                    while True:
                        time.sleep(30)
                        status = deployment.get_deployment_status()
                        if status['failed_processes'] > 0:
                            logger.warning(f"{status['failed_processes']} processes have failed")
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, stopping deployment")
                    deployment.stop_deployment()
            else:
                logger.error("Deployment failed")
                sys.exit(1)
        
        elif args.action == 'stop':
            if deployment.stop_deployment():
                logger.info("Deployment stopped successfully")
            else:
                logger.error("Some processes failed to stop gracefully")
                sys.exit(1)
        
        elif args.action == 'restart':
            if deployment.restart_deployment(args.mode):
                logger.info(f"Deployment restarted successfully in {args.mode} mode")
            else:
                logger.error("Restart failed")
                sys.exit(1)
        
        elif args.action == 'status':
            status = deployment.get_deployment_status()
            print(f"Total processes: {status['total_processes']}")
            print(f"Running processes: {status['running_processes']}")
            print(f"Failed processes: {status['failed_processes']}")
            
            for name, proc_status in status['processes'].items():
                print(f"  {name}: {proc_status}")
    
    except Exception as e:
        logger.error(f"Deployment script error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()