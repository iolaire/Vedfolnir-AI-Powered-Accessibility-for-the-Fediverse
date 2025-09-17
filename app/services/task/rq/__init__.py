# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ (Redis Queue) Integration Module

Provides Redis Queue integration for Vedfolnir's task processing system.
Includes configuration, health monitoring, connection management, queue management,
worker management, and progress tracking.
"""

from .rq_config import RQConfig, WorkerMode, TaskPriority, QueueConfig, WorkerConfig, RetryPolicy, rq_config
from .redis_health_monitor import RedisHealthMonitor
from .redis_connection_manager import RedisConnectionManager
from .rq_queue_manager import RQQueueManager
from .rq_worker_manager import RQWorkerManager
from .integrated_rq_worker import IntegratedRQWorker
from .worker_session_manager import WorkerSessionManager
from .rq_job_processor import RQJobProcessor, RQWorkerHealthMonitor, process_caption_task
from .rq_progress_tracker import RQProgressTracker, RQProgressData
from .flask_rq_integration import FlaskRQIntegration, rq_integration, initialize_rq_workers, setup_rq_with_flask_app, create_rq_enabled_app

__all__ = [
    # Configuration
    'RQConfig',
    'WorkerMode', 
    'TaskPriority',
    'QueueConfig',
    'WorkerConfig',
    'RetryPolicy',
    'rq_config',
    
    # Redis Management
    'RedisHealthMonitor',
    'RedisConnectionManager',
    
    # Queue Management
    'RQQueueManager',
    
    # Worker Management
    'RQWorkerManager',
    'IntegratedRQWorker',
    'WorkerSessionManager',
    
    # Job Processing
    'RQJobProcessor',
    'RQWorkerHealthMonitor',
    'process_caption_task',
    
    # Progress Tracking
    'RQProgressTracker',
    'RQProgressData',
    
    # Flask Integration
    'FlaskRQIntegration',
    'rq_integration',
    'initialize_rq_workers',
    'setup_rq_with_flask_app',
    'create_rq_enabled_app'
]