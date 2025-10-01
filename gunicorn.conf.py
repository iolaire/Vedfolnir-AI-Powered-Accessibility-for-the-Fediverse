# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Gunicorn configuration for Vedfolnir Docker deployment
Optimized for containerized environment with WebSocket support and integrated RQ workers
"""

import os
import multiprocessing
import logging

# Container environment detection
IS_CONTAINER = os.path.exists('/.dockerenv') or os.getenv('CONTAINER_ENV') == 'true'

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes - optimized for container environment
if IS_CONTAINER:
    # In containers, be more conservative with worker count
    cpu_count = multiprocessing.cpu_count()
    workers = max(2, min(cpu_count, int(os.getenv("GUNICORN_WORKERS", str(cpu_count)))))
else:
    workers = multiprocessing.cpu_count() * 2 + 1

worker_class = "eventlet"  # Required for WebSocket support
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "1000"))
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# Timeout settings - adjusted for container environment
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))  # Increased for RQ worker operations
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "2"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "60"))  # Increased for RQ cleanup

# Logging - container-optimized
if IS_CONTAINER:
    # In containers, log to stdout/stderr for container log aggregation
    accesslog = "-"  # stdout
    errorlog = "-"   # stderr
    capture_output = True
else:
    # Traditional file logging for non-container environments
    accesslog = "/app/logs/gunicorn_access.log"
    errorlog = "/app/logs/gunicorn_error.log"

loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "vedfolnir"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
preload_app = True
enable_stdio_inheritance = True

# Resource limits for container environment
if IS_CONTAINER:
    # Container-specific resource management
    worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance
    
    # Memory management
    memory_limit = os.getenv("MEMORY_LIMIT", "2g")
    if memory_limit.endswith('g'):
        memory_mb = int(memory_limit[:-1]) * 1024
    elif memory_limit.endswith('m'):
        memory_mb = int(memory_limit[:-1])
    else:
        memory_mb = 2048  # Default 2GB
    
    # Adjust max_requests based on available memory
    if memory_mb < 1024:  # Less than 1GB
        max_requests = 500
    elif memory_mb < 2048:  # Less than 2GB
        max_requests = 750
    else:  # 2GB or more
        max_requests = 1000

# RQ Worker Integration Settings
RQ_ENABLE_INTEGRATED_WORKERS = os.getenv('RQ_ENABLE_INTEGRATED_WORKERS', 'true').lower() == 'true'
RQ_STARTUP_DELAY = int(os.getenv('RQ_STARTUP_DELAY', '10'))  # Delay RQ startup in containers

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Vedfolnir server is ready. Listening on: %s", server.address)
    
    # Log container environment info
    if IS_CONTAINER:
        server.log.info("Running in container environment")
        server.log.info(f"Workers: {workers}, Worker class: {worker_class}")
        server.log.info(f"RQ integrated workers: {RQ_ENABLE_INTEGRATED_WORKERS}")
        
        # Log resource limits
        memory_limit = os.getenv("MEMORY_LIMIT", "not set")
        cpu_limit = os.getenv("CPU_LIMIT", "not set")
        server.log.info(f"Resource limits - Memory: {memory_limit}, CPU: {cpu_limit}")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")
    
    # Cleanup RQ workers if integrated
    if RQ_ENABLE_INTEGRATED_WORKERS:
        try:
            from app.services.task.rq.gunicorn_integration import cleanup_rq_workers
            cleanup_rq_workers()
            worker.log.info("RQ workers cleaned up successfully")
        except Exception as e:
            worker.log.error(f"Error cleaning up RQ workers: {e}")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    worker.log.info("Worker spawned (pid: %s)", worker.pid)
    
    # Container-specific worker initialization
    if IS_CONTAINER:
        worker.log.info(f"Worker {worker.pid} initialized in container environment")
        
        # Set up structured logging for container environment
        try:
            # Configure JSON logging for container log aggregation
            if os.getenv('ENABLE_JSON_LOGGING', 'false').lower() == 'true':
                import json
                import sys
                
                class JSONFormatter(logging.Formatter):
                    def format(self, record):
                        log_entry = {
                            'timestamp': self.formatTime(record),
                            'level': record.levelname,
                            'logger': record.name,
                            'message': record.getMessage(),
                            'worker_pid': worker.pid,
                            'service': 'vedfolnir'
                        }
                        if record.exc_info:
                            log_entry['exception'] = self.formatException(record.exc_info)
                        return json.dumps(log_entry)
                
                # Apply JSON formatter to worker logger
                handler = logging.StreamHandler(sys.stdout)
                handler.setFormatter(JSONFormatter())
                worker.log.logger.handlers = [handler]
                worker.log.info("JSON logging enabled for container environment")
                
        except Exception as e:
            worker.log.error(f"Failed to configure container logging: {e}")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")
    
    # Emergency RQ cleanup
    if RQ_ENABLE_INTEGRATED_WORKERS:
        try:
            from app.services.task.rq.gunicorn_integration import cleanup_rq_workers
            cleanup_rq_workers()
            worker.log.info("Emergency RQ cleanup completed")
        except Exception as e:
            worker.log.error(f"Emergency RQ cleanup failed: {e}")

def on_exit(server):
    """Called just before the master process is initialized."""
    server.log.info("Vedfolnir server shutting down")
    
    # Final RQ cleanup
    if RQ_ENABLE_INTEGRATED_WORKERS:
        try:
            from app.services.task.rq.gunicorn_integration import cleanup_rq_workers
            cleanup_rq_workers()
            server.log.info("Final RQ cleanup completed")
        except Exception as e:
            server.log.error(f"Final RQ cleanup failed: {e}")

# Health check configuration for containers
def health_check():
    """Health check function for container orchestration"""
    try:
        import requests
        response = requests.get('http://localhost:5000/health', timeout=5)
        return response.status_code == 200
    except Exception:
        return False