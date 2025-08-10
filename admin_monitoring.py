# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Administrative Monitoring and Controls

This module provides comprehensive monitoring and control capabilities for administrators
to manage caption generation tasks, system resources, and performance metrics.
"""

import logging
import psutil
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

from database import DatabaseManager
from models import (
    CaptionGenerationTask, TaskStatus, User, PlatformConnection, 
    Image, ProcessingStatus, ProcessingRun
)
from web_caption_generation_service import WebCaptionGenerationService
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class AdminMonitoringService:
    """Service for administrative monitoring and control of caption generation system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.caption_service = WebCaptionGenerationService(db_manager)
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system overview for admin dashboard"""
        session = self.db_manager.get_session()
        try:
            # Active tasks
            active_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
            ).count()
            
            # Recent tasks (last 24 hours)
            yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.created_at >= yesterday
            ).count()
            
            # System resource usage
            system_resources = self._get_system_resources()
            
            # Queue statistics
            queue_stats = self.caption_service.get_service_stats()
            
            # User activity
            active_users = session.query(User).filter(
                User.is_active == True,
                User.last_login >= yesterday
            ).count()
            
            return {
                'active_tasks': active_tasks,
                'recent_tasks': recent_tasks,
                'active_users': active_users,
                'system_resources': system_resources,
                'queue_stats': queue_stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system overview: {sanitize_for_log(str(e))}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def get_active_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of active caption generation tasks"""
        session = self.db_manager.get_session()
        try:
            tasks = session.query(CaptionGenerationTask).options(
                joinedload(CaptionGenerationTask.user),
                joinedload(CaptionGenerationTask.platform_connection)
            ).filter(
                CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
            ).order_by(desc(CaptionGenerationTask.created_at)).limit(limit).all()
            
            return [self._task_to_dict(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"Error getting active tasks: {sanitize_for_log(str(e))}")
            return []
        finally:
            session.close()
    
    def get_task_history(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get task history for specified time period"""
        session = self.db_manager.get_session()
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            tasks = session.query(CaptionGenerationTask).options(
                joinedload(CaptionGenerationTask.user),
                joinedload(CaptionGenerationTask.platform_connection)
            ).filter(
                CaptionGenerationTask.created_at >= cutoff_time
            ).order_by(desc(CaptionGenerationTask.created_at)).limit(limit).all()
            
            return [self._task_to_dict(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"Error getting task history: {sanitize_for_log(str(e))}")
            return []
        finally:
            session.close()
    
    def get_performance_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Get performance metrics for specified period"""
        session = self.db_manager.get_session()
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Task completion metrics
            completed_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.completed_at >= cutoff_time,
                CaptionGenerationTask.status == TaskStatus.COMPLETED
            ).all()
            
            # Calculate metrics
            total_completed = len(completed_tasks)
            total_images = sum(task.results.images_processed if task.results else 0 for task in completed_tasks)
            total_captions = sum(task.results.captions_generated if task.results else 0 for task in completed_tasks)
            total_time = sum(task.results.processing_time_seconds if task.results else 0 for task in completed_tasks)
            
            # Average processing times
            avg_task_time = total_time / total_completed if total_completed > 0 else 0
            avg_images_per_task = total_images / total_completed if total_completed > 0 else 0
            avg_captions_per_task = total_captions / total_completed if total_completed > 0 else 0
            
            # Failed tasks
            failed_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.created_at >= cutoff_time,
                CaptionGenerationTask.status == TaskStatus.FAILED
            ).count()
            
            # Success rate
            total_tasks = total_completed + failed_tasks
            success_rate = (total_completed / total_tasks * 100) if total_tasks > 0 else 0
            
            return {
                'period_days': days,
                'total_completed_tasks': total_completed,
                'total_failed_tasks': failed_tasks,
                'success_rate': round(success_rate, 2),
                'total_images_processed': total_images,
                'total_captions_generated': total_captions,
                'avg_task_time_seconds': round(avg_task_time, 2),
                'avg_images_per_task': round(avg_images_per_task, 2),
                'avg_captions_per_task': round(avg_captions_per_task, 2),
                'images_per_second': round(total_images / total_time, 2) if total_time > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {sanitize_for_log(str(e))}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def cancel_task(self, task_id: str, admin_user_id: int, reason: str = None) -> Dict[str, Any]:
        """Cancel a task as administrator"""
        try:
            success = self.caption_service.task_queue_manager.cancel_task(task_id, admin_user_id)
            
            if success:
                # Log admin action
                logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} cancelled task {sanitize_for_log(task_id)}: {sanitize_for_log(reason or 'No reason provided')}")
                
                return {
                    'success': True,
                    'message': f'Task {task_id[:8]}... cancelled successfully',
                    'task_id': task_id
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to cancel task - task may not exist or cannot be cancelled'
                }
                
        except Exception as e:
            logger.error(f"Error cancelling task {sanitize_for_log(task_id)}: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': str(e)}
    
    def cleanup_old_tasks(self, days: int = 7, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up old completed/failed tasks"""
        session = self.db_manager.get_session()
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Find old tasks to clean up
            old_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.completed_at < cutoff_time,
                CaptionGenerationTask.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED])
            ).all()
            
            count = len(old_tasks)
            
            if not dry_run and count > 0:
                # Delete old tasks
                for task in old_tasks:
                    session.delete(task)
                session.commit()
                
                logger.info(f"Cleaned up {count} old tasks older than {days} days")
            
            return {
                'success': True,
                'count': count,
                'dry_run': dry_run,
                'message': f"{'Would clean up' if dry_run else 'Cleaned up'} {count} tasks older than {days} days"
            }
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error during task cleanup: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': 'Database error during cleanup'}
        except Exception as e:
            session.rollback()
            logger.error(f"Error during task cleanup: {sanitize_for_log(str(e))}")
            return {'success': False, 'error': str(e)}
        finally:
            session.close()
    
    def get_user_activity(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get user activity statistics"""
        session = self.db_manager.get_session()
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Get user task statistics with simpler approach
            user_stats = session.query(
                User.id,
                User.username,
                User.role,
                func.count(CaptionGenerationTask.id).label('task_count')
            ).outerjoin(CaptionGenerationTask).filter(
                User.is_active == True
            ).filter(
                or_(
                    CaptionGenerationTask.created_at >= cutoff_time,
                    CaptionGenerationTask.created_at.is_(None)
                )
            ).group_by(User.id, User.username, User.role).all()
            
            # Calculate completed and failed tasks separately
            result = []
            for stat in user_stats:
                completed_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.user_id == stat.id,
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.created_at >= cutoff_time
                ).count()
                
                failed_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.user_id == stat.id,
                    CaptionGenerationTask.status == TaskStatus.FAILED,
                    CaptionGenerationTask.created_at >= cutoff_time
                ).count()
                
                result.append({
                    'user_id': stat.id,
                    'username': stat.username,
                    'role': stat.role.value,
                    'total_tasks': stat.task_count or 0,
                    'completed_tasks': completed_tasks,
                    'failed_tasks': failed_tasks,
                    'success_rate': round((completed_tasks / (stat.task_count or 1)) * 100, 2)
                })
            
            return result
            

            
        except Exception as e:
            logger.error(f"Error getting user activity: {sanitize_for_log(str(e))}")
            return []
        finally:
            session.close()
    
    def get_system_limits(self) -> Dict[str, Any]:
        """Get current system limits and configuration"""
        return {
            'max_concurrent_tasks': 5,  # Could be configurable
            'max_tasks_per_user_per_hour': 10,  # Could be configurable
            'task_timeout_minutes': 60,  # Could be configurable
            'max_images_per_task': 100,  # Could be configurable
            'cleanup_interval_hours': 24,  # Could be configurable
            'resource_monitoring_enabled': True
        }
    
    def update_system_limits(self, limits: Dict[str, Any]) -> Dict[str, Any]:
        """Update system limits (placeholder for future configuration management)"""
        # This would integrate with a configuration management system
        logger.info(f"System limits update requested: {sanitize_for_log(str(limits))}")
        return {
            'success': True,
            'message': 'System limits updated successfully',
            'updated_limits': limits
        }
    
    def _get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)
            
            # Load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()
                load_1min = load_avg[0]
            except (AttributeError, OSError):
                load_1min = None
            
            return {
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory_percent, 1),
                'memory_available_gb': round(memory_available_gb, 2),
                'disk_percent': round(disk_percent, 1),
                'disk_free_gb': round(disk_free_gb, 2),
                'load_1min': round(load_1min, 2) if load_1min is not None else None,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting system resources: {sanitize_for_log(str(e))}")
            return {'error': str(e)}
    
    def _task_to_dict(self, task: CaptionGenerationTask) -> Dict[str, Any]:
        """Convert task object to dictionary for JSON serialization"""
        return {
            'id': task.id,
            'user_id': task.user_id,
            'username': task.user.username if task.user else 'Unknown',
            'platform_name': task.platform_connection.name if task.platform_connection else 'Unknown',
            'platform_type': task.platform_connection.platform_type if task.platform_connection else 'Unknown',
            'status': task.status.value,
            'progress_percent': task.progress_percent or 0,
            'current_step': task.current_step,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'error_message': task.error_message,
            'results': task.results.to_dict() if task.results else None
        }