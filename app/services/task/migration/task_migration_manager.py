# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Task Migration Manager

Handles migration of existing QUEUED tasks from database to RQ with data preservation
and validation during migration. Supports hybrid processing during transition period.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus, JobPriority
from app.services.task.rq.rq_queue_manager import RQQueueManager
from app.services.task.rq.rq_config import TaskPriority

logger = logging.getLogger(__name__)


class TaskMigrationManager:
    """Manages migration of database tasks to RQ with data preservation and validation"""
    
    def __init__(self, db_manager: DatabaseManager, rq_queue_manager: RQQueueManager):
        """
        Initialize Task Migration Manager
        
        Args:
            db_manager: Database manager instance
            rq_queue_manager: RQ queue manager instance
        """
        self.db_manager = db_manager
        self.rq_queue_manager = rq_queue_manager
        self._lock = threading.Lock()
        
        # Migration statistics
        self.migration_stats = {
            'total_tasks': 0,
            'migrated_tasks': 0,
            'failed_migrations': 0,
            'validation_errors': 0,
            'last_migration_time': None
        }
    
    def migrate_database_tasks_to_rq(self, batch_size: int = 50, validate_data: bool = True) -> Dict[str, Any]:
        """
        Migrate existing QUEUED tasks from database to RQ
        
        Args:
            batch_size: Number of tasks to migrate in each batch
            validate_data: Whether to validate task data during migration
            
        Returns:
            Dict containing migration results and statistics
        """
        with self._lock:
            logger.info("Starting database task migration to RQ")
            
            # Reset migration statistics
            self.migration_stats = {
                'total_tasks': 0,
                'migrated_tasks': 0,
                'failed_migrations': 0,
                'validation_errors': 0,
                'last_migration_time': datetime.now(timezone.utc),
                'migration_details': []
            }
            
            try:
                # Check if RQ is available
                if not self.rq_queue_manager.check_redis_health():
                    raise RuntimeError("RQ system is not available for migration")
                
                # Get total count of tasks to migrate
                total_tasks = self._get_queued_tasks_count()
                self.migration_stats['total_tasks'] = total_tasks
                
                if total_tasks == 0:
                    logger.info("No queued tasks found for migration")
                    return self.migration_stats
                
                logger.info(f"Found {total_tasks} queued tasks to migrate")
                
                # Migrate tasks in batches
                migrated_count = 0
                batch_number = 1
                
                while True:
                    batch_tasks = self._get_queued_tasks_batch(batch_size, migrated_count)
                    
                    if not batch_tasks:
                        break
                    
                    logger.info(f"Processing migration batch {batch_number} ({len(batch_tasks)} tasks)")
                    
                    batch_results = self._migrate_task_batch(batch_tasks, validate_data)
                    
                    # Update statistics
                    self.migration_stats['migrated_tasks'] += batch_results['migrated']
                    self.migration_stats['failed_migrations'] += batch_results['failed']
                    self.migration_stats['validation_errors'] += batch_results['validation_errors']
                    self.migration_stats['migration_details'].extend(batch_results['details'])
                    
                    migrated_count += len(batch_tasks)
                    batch_number += 1
                    
                    # Log progress
                    logger.info(f"Batch {batch_number - 1} completed: {batch_results['migrated']} migrated, "
                              f"{batch_results['failed']} failed")
                
                # Final statistics
                success_rate = (self.migration_stats['migrated_tasks'] / total_tasks * 100) if total_tasks > 0 else 0
                
                logger.info(f"Migration completed: {self.migration_stats['migrated_tasks']}/{total_tasks} tasks "
                          f"migrated successfully ({success_rate:.1f}% success rate)")
                
                return self.migration_stats
                
            except Exception as e:
                logger.error(f"Task migration failed: {sanitize_for_log(str(e))}")
                self.migration_stats['error'] = str(e)
                return self.migration_stats
    
    def _get_queued_tasks_count(self) -> int:
        """Get count of queued tasks in database"""
        session = self.db_manager.get_session()
        try:
            return session.query(CaptionGenerationTask).filter_by(status=TaskStatus.QUEUED).count()
        finally:
            session.close()
    
    def _get_queued_tasks_batch(self, batch_size: int, offset: int) -> List[CaptionGenerationTask]:
        """Get a batch of queued tasks from database"""
        session = self.db_manager.get_session()
        try:
            tasks = session.query(CaptionGenerationTask).filter_by(
                status=TaskStatus.QUEUED
            ).order_by(
                # Prioritize by priority, then by creation time
                CaptionGenerationTask.priority == JobPriority.URGENT,
                CaptionGenerationTask.priority == JobPriority.HIGH,
                CaptionGenerationTask.priority == JobPriority.NORMAL,
                CaptionGenerationTask.created_at
            ).offset(offset).limit(batch_size).all()
            
            # Detach from session to avoid issues
            for task in tasks:
                session.expunge(task)
            
            return tasks
            
        finally:
            session.close()
    
    def _migrate_task_batch(self, tasks: List[CaptionGenerationTask], validate_data: bool) -> Dict[str, Any]:
        """Migrate a batch of tasks to RQ"""
        batch_results = {
            'migrated': 0,
            'failed': 0,
            'validation_errors': 0,
            'details': []
        }
        
        for task in tasks:
            try:
                # Validate task data if requested
                if validate_data:
                    validation_result = self._validate_task_data(task)
                    if not validation_result['valid']:
                        batch_results['validation_errors'] += 1
                        batch_results['details'].append({
                            'task_id': task.id,
                            'status': 'validation_failed',
                            'error': validation_result['error']
                        })
                        continue
                
                # Migrate task to RQ
                migration_result = self._migrate_single_task(task)
                
                if migration_result['success']:
                    batch_results['migrated'] += 1
                    batch_results['details'].append({
                        'task_id': task.id,
                        'status': 'migrated',
                        'priority': task.priority.value if task.priority else 'normal',
                        'queue': migration_result.get('queue')
                    })
                else:
                    batch_results['failed'] += 1
                    batch_results['details'].append({
                        'task_id': task.id,
                        'status': 'migration_failed',
                        'error': migration_result.get('error')
                    })
                    
            except Exception as e:
                batch_results['failed'] += 1
                batch_results['details'].append({
                    'task_id': task.id,
                    'status': 'exception',
                    'error': str(e)
                })
                logger.error(f"Exception migrating task {sanitize_for_log(task.id)}: {sanitize_for_log(str(e))}")
        
        return batch_results
    
    def _validate_task_data(self, task: CaptionGenerationTask) -> Dict[str, Any]:
        """Validate task data before migration"""
        try:
            # Check required fields
            if not task.id:
                return {'valid': False, 'error': 'Task ID is missing'}
            
            if not task.user_id:
                return {'valid': False, 'error': 'User ID is missing'}
            
            if not task.platform_connection_id:
                return {'valid': False, 'error': 'Platform connection ID is missing'}
            
            # Validate task settings
            if task.settings_json:
                try:
                    settings = task.settings
                    if settings is None:
                        return {'valid': False, 'error': 'Invalid settings JSON'}
                except Exception as e:
                    return {'valid': False, 'error': f'Settings validation failed: {str(e)}'}
            
            # Validate priority
            if task.priority and task.priority not in JobPriority:
                return {'valid': False, 'error': f'Invalid priority: {task.priority}'}
            
            # Check if user exists
            session = self.db_manager.get_session()
            try:
                from models import User
                user = session.query(User).filter_by(id=task.user_id).first()
                if not user:
                    return {'valid': False, 'error': f'User {task.user_id} not found'}
                
                # Check if platform connection exists
                from models import PlatformConnection
                platform_conn = session.query(PlatformConnection).filter_by(
                    id=task.platform_connection_id
                ).first()
                if not platform_conn:
                    return {'valid': False, 'error': f'Platform connection {task.platform_connection_id} not found'}
                
            finally:
                session.close()
            
            return {'valid': True}
            
        except Exception as e:
            return {'valid': False, 'error': f'Validation exception: {str(e)}'}
    
    def _migrate_single_task(self, task: CaptionGenerationTask) -> Dict[str, Any]:
        """Migrate a single task to RQ"""
        try:
            # Convert JobPriority to TaskPriority
            task_priority = self._convert_job_priority_to_task_priority(task.priority)
            
            # Enqueue task to RQ
            # Note: The RQ queue manager will handle the actual enqueueing
            # We need to preserve the task data and ensure it's properly tracked
            
            # First, ensure the task is properly tracked in Redis
            if self.rq_queue_manager.user_task_tracker:
                # Check if user already has an active task in Redis
                existing_task = self.rq_queue_manager.user_task_tracker.get_user_active_task(task.user_id)
                if existing_task and existing_task != task.id:
                    return {
                        'success': False,
                        'error': f'User {task.user_id} already has active task {existing_task} in Redis'
                    }
            
            # Enqueue to appropriate RQ queue
            queue_name = task_priority.value
            queue = self.rq_queue_manager.queues.get(queue_name)
            
            if not queue:
                return {
                    'success': False,
                    'error': f'Queue {queue_name} not found'
                }
            
            # Enqueue the job
            job = queue.enqueue(
                'app.services.task.rq.rq_job_processor.process_caption_task',
                task.id,
                job_id=task.id,
                job_timeout=self.rq_queue_manager.config.queue_configs[queue_name].timeout
            )
            
            # Update user task tracking
            if self.rq_queue_manager.user_task_tracker:
                self.rq_queue_manager.user_task_tracker.set_user_active_task(task.user_id, task.id)
            
            logger.info(f"Successfully migrated task {sanitize_for_log(task.id)} to RQ queue {queue_name}")
            
            return {
                'success': True,
                'queue': queue_name,
                'job_id': job.id
            }
            
        except Exception as e:
            logger.error(f"Failed to migrate task {sanitize_for_log(task.id)}: {sanitize_for_log(str(e))}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _convert_job_priority_to_task_priority(self, job_priority: Optional[JobPriority]) -> TaskPriority:
        """Convert JobPriority to TaskPriority enum"""
        if not job_priority:
            return TaskPriority.NORMAL
        
        mapping = {
            JobPriority.URGENT: TaskPriority.URGENT,
            JobPriority.HIGH: TaskPriority.HIGH,
            JobPriority.NORMAL: TaskPriority.NORMAL,
            JobPriority.LOW: TaskPriority.LOW
        }
        return mapping.get(job_priority, TaskPriority.NORMAL)
    
    def create_hybrid_processing_support(self) -> Dict[str, Any]:
        """
        Create hybrid processing support for transition period
        
        Returns:
            Dict containing hybrid processing configuration
        """
        try:
            # Get current system state
            rq_health = self.rq_queue_manager.get_health_status()
            queue_stats = self.rq_queue_manager.get_queue_stats()
            
            # Determine processing strategy
            hybrid_config = {
                'rq_available': rq_health.get('redis_available', False),
                'fallback_mode': rq_health.get('fallback_mode', True),
                'processing_strategy': 'hybrid',
                'queue_distribution': {
                    'rq_queues': queue_stats.get('total_pending', 0),
                    'database_queued': queue_stats.get('db_queued', 0),
                    'database_running': queue_stats.get('db_running', 0)
                },
                'recommendations': []
            }
            
            # Add processing recommendations
            if hybrid_config['rq_available'] and not hybrid_config['fallback_mode']:
                hybrid_config['recommendations'].append('Migrate remaining database tasks to RQ')
                hybrid_config['primary_processor'] = 'rq'
                hybrid_config['fallback_processor'] = 'database'
            else:
                hybrid_config['recommendations'].append('Use database processing until RQ is stable')
                hybrid_config['primary_processor'] = 'database'
                hybrid_config['fallback_processor'] = 'none'
            
            # Add monitoring recommendations
            if queue_stats.get('db_queued', 0) > 0 and hybrid_config['rq_available']:
                hybrid_config['recommendations'].append(
                    f"Consider migrating {queue_stats['db_queued']} database tasks to RQ"
                )
            
            logger.info(f"Hybrid processing configuration created: {hybrid_config['processing_strategy']}")
            return hybrid_config
            
        except Exception as e:
            logger.error(f"Failed to create hybrid processing support: {sanitize_for_log(str(e))}")
            return {
                'error': str(e),
                'processing_strategy': 'database_only',
                'primary_processor': 'database',
                'fallback_processor': 'none'
            }
    
    def validate_migration_integrity(self, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate migration integrity by checking task data preservation
        
        Args:
            task_ids: Optional list of specific task IDs to validate
            
        Returns:
            Dict containing validation results
        """
        try:
            validation_results = {
                'total_checked': 0,
                'valid_tasks': 0,
                'invalid_tasks': 0,
                'missing_tasks': 0,
                'data_integrity_issues': [],
                'validation_time': datetime.now(timezone.utc)
            }
            
            # Get tasks to validate
            if task_ids:
                tasks_to_check = task_ids
            else:
                # Get recently migrated tasks (tasks in RQ queues)
                tasks_to_check = self._get_rq_task_ids()
            
            validation_results['total_checked'] = len(tasks_to_check)
            
            for task_id in tasks_to_check:
                try:
                    # Check if task exists in database
                    db_task = self._get_task_from_database(task_id)
                    if not db_task:
                        validation_results['missing_tasks'] += 1
                        validation_results['data_integrity_issues'].append({
                            'task_id': task_id,
                            'issue': 'Task not found in database'
                        })
                        continue
                    
                    # Validate task data integrity
                    integrity_check = self._validate_task_data(db_task)
                    if integrity_check['valid']:
                        validation_results['valid_tasks'] += 1
                    else:
                        validation_results['invalid_tasks'] += 1
                        validation_results['data_integrity_issues'].append({
                            'task_id': task_id,
                            'issue': integrity_check['error']
                        })
                        
                except Exception as e:
                    validation_results['invalid_tasks'] += 1
                    validation_results['data_integrity_issues'].append({
                        'task_id': task_id,
                        'issue': f'Validation exception: {str(e)}'
                    })
            
            # Calculate integrity percentage
            if validation_results['total_checked'] > 0:
                integrity_percentage = (validation_results['valid_tasks'] / 
                                     validation_results['total_checked'] * 100)
                validation_results['integrity_percentage'] = round(integrity_percentage, 2)
            else:
                validation_results['integrity_percentage'] = 100.0
            
            logger.info(f"Migration integrity validation completed: "
                       f"{validation_results['integrity_percentage']}% integrity")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Migration integrity validation failed: {sanitize_for_log(str(e))}")
            return {
                'error': str(e),
                'total_checked': 0,
                'integrity_percentage': 0.0
            }
    
    def _get_rq_task_ids(self) -> List[str]:
        """Get task IDs currently in RQ queues"""
        task_ids = []
        
        try:
            if self.rq_queue_manager.queues:
                for queue_name, queue in self.rq_queue_manager.queues.items():
                    # Get job IDs from queue
                    job_ids = queue.job_ids
                    task_ids.extend(job_ids)
            
        except Exception as e:
            logger.error(f"Error getting RQ task IDs: {sanitize_for_log(str(e))}")
        
        return task_ids
    
    def _get_task_from_database(self, task_id: str) -> Optional[CaptionGenerationTask]:
        """Get task from database by ID"""
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            if task:
                session.expunge(task)
            return task
        finally:
            session.close()
    
    def get_migration_statistics(self) -> Dict[str, Any]:
        """Get current migration statistics"""
        return self.migration_stats.copy()
    
    def cleanup_migration_resources(self) -> None:
        """Cleanup migration resources and temporary data"""
        try:
            # Reset migration statistics
            self.migration_stats = {
                'total_tasks': 0,
                'migrated_tasks': 0,
                'failed_migrations': 0,
                'validation_errors': 0,
                'last_migration_time': None
            }
            
            logger.info("Migration resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up migration resources: {sanitize_for_log(str(e))}")