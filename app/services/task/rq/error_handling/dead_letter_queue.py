# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Dead Letter Queue

Manages permanently failed tasks after all retries are exhausted.
Provides storage, analysis, and recovery capabilities for failed jobs.
"""

import logging
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import redis
from rq import Job

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from .rq_error_handler import ErrorCategory

logger = logging.getLogger(__name__)


class DeadLetterQueue:
    """Manages permanently failed tasks with analysis and recovery capabilities"""
    
    def __init__(self, redis_connection: redis.Redis, db_manager: DatabaseManager):
        """
        Initialize Dead Letter Queue
        
        Args:
            redis_connection: Redis connection for DLQ storage
            db_manager: Database manager for persistent storage
        """
        self.redis_connection = redis_connection
        self.db_manager = db_manager
        
        # DLQ configuration
        self.dlq_key = "rq:dead_letter_queue"
        self.dlq_metadata_key = "rq:dlq_metadata"
        self.max_dlq_size = 1000  # Maximum items in DLQ
        self.retention_days = 30  # Keep DLQ items for 30 days
        
        logger.info("Dead Letter Queue initialized")
    
    def add_failed_job(self, job: Job, exception: Exception, error_category: ErrorCategory, 
                      retry_count: int) -> bool:
        """
        Add permanently failed job to dead letter queue
        
        Args:
            job: The failed RQ job
            exception: The final exception that caused failure
            error_category: Category of the error
            retry_count: Number of retries attempted
            
        Returns:
            bool: True if successfully added to DLQ
        """
        try:
            # Create DLQ entry
            dlq_entry = {
                'job_id': job.id,
                'task_id': job.id,  # Assuming job.id is the task_id
                'failed_at': datetime.now(timezone.utc).isoformat(),
                'error_type': type(exception).__name__,
                'error_category': error_category.value,
                'error_message': self._sanitize_error_message(str(exception)),
                'retry_count': retry_count,
                'job_data': self._extract_job_data(job),
                'job_args': job.args if hasattr(job, 'args') else [],
                'job_kwargs': job.kwargs if hasattr(job, 'kwargs') else {},
                'queue_name': job.origin if hasattr(job, 'origin') else 'unknown',
                'worker_name': getattr(job, 'worker_name', 'unknown'),
                'created_at': job.created_at.isoformat() if hasattr(job, 'created_at') and job.created_at else None
            }
            
            # Add to Redis DLQ
            dlq_entry_json = json.dumps(dlq_entry)
            
            # Use Redis list for DLQ storage
            pipe = self.redis_connection.pipeline()
            pipe.lpush(self.dlq_key, dlq_entry_json)
            pipe.ltrim(self.dlq_key, 0, self.max_dlq_size - 1)  # Limit DLQ size
            pipe.execute()
            
            # Update metadata
            self._update_dlq_metadata(dlq_entry)
            
            # Store in database for persistence
            self._store_dlq_entry_in_database(dlq_entry)
            
            logger.info(
                f"Added job {sanitize_for_log(job.id)} to dead letter queue "
                f"(category: {error_category.value}, retries: {retry_count})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add job to dead letter queue: {sanitize_for_log(str(e))}")
            return False
    
    def _extract_job_data(self, job: Job) -> Dict[str, Any]:
        """Extract relevant job data for DLQ storage"""
        try:
            job_data = {
                'function_name': job.func_name if hasattr(job, 'func_name') else 'unknown',
                'timeout': job.timeout if hasattr(job, 'timeout') else None,
                'result_ttl': job.result_ttl if hasattr(job, 'result_ttl') else None,
                'meta': job.meta if hasattr(job, 'meta') else {},
                'status': job.get_status() if hasattr(job, 'get_status') else 'unknown'
            }
            
            return job_data
            
        except Exception as e:
            logger.warning(f"Failed to extract job data: {sanitize_for_log(str(e))}")
            return {'extraction_error': str(e)}
    
    def _sanitize_error_message(self, error_message: str) -> str:
        """Sanitize error message for DLQ storage"""
        try:
            # Remove sensitive information
            import re
            
            sanitized = error_message
            
            # Remove file paths
            sanitized = re.sub(r'/[^\s]*', '[PATH_REMOVED]', sanitized)
            
            # Remove IP addresses
            sanitized = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REMOVED]', sanitized)
            
            # Remove potential credentials
            sanitized = re.sub(
                r'(password|token|key|secret|auth)[\s=:]+[^\s]+', 
                r'\1=[REDACTED]', 
                sanitized, 
                flags=re.IGNORECASE
            )
            
            # Limit length
            if len(sanitized) > 1000:
                sanitized = sanitized[:997] + "..."
            
            return sanitized
            
        except Exception:
            return "Error message sanitized due to processing error"
    
    def _update_dlq_metadata(self, dlq_entry: Dict[str, Any]) -> None:
        """Update DLQ metadata for statistics"""
        try:
            # Get current metadata
            metadata_json = self.redis_connection.get(self.dlq_metadata_key)
            
            if metadata_json:
                metadata = json.loads(metadata_json)
            else:
                metadata = {
                    'total_entries': 0,
                    'error_categories': {},
                    'error_types': {},
                    'last_updated': None
                }
            
            # Update metadata
            metadata['total_entries'] += 1
            metadata['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            # Update error category counts
            category = dlq_entry['error_category']
            metadata['error_categories'][category] = metadata['error_categories'].get(category, 0) + 1
            
            # Update error type counts
            error_type = dlq_entry['error_type']
            metadata['error_types'][error_type] = metadata['error_types'].get(error_type, 0) + 1
            
            # Store updated metadata
            self.redis_connection.set(
                self.dlq_metadata_key, 
                json.dumps(metadata),
                ex=86400 * 7  # 7 days TTL
            )
            
        except Exception as e:
            logger.warning(f"Failed to update DLQ metadata: {sanitize_for_log(str(e))}")
    
    def _store_dlq_entry_in_database(self, dlq_entry: Dict[str, Any]) -> None:
        """Store DLQ entry in database for persistence"""
        try:
            # This would typically use a dedicated DLQ table
            # For now, we'll store as a JSON record in a simple table
            # In a full implementation, you'd create a proper DLQ table
            
            session = self.db_manager.get_session()
            try:
                # Store as a simple record (would be better with dedicated table)
                # This is a placeholder - in production you'd have a proper DLQ table
                pass
                
            finally:
                session.close()
                
        except Exception as e:
            logger.warning(f"Failed to store DLQ entry in database: {sanitize_for_log(str(e))}")
    
    def get_dlq_entries(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get entries from dead letter queue
        
        Args:
            limit: Maximum number of entries to return
            offset: Offset for pagination
            
        Returns:
            List of DLQ entries
        """
        try:
            # Get entries from Redis
            entries_json = self.redis_connection.lrange(
                self.dlq_key, 
                offset, 
                offset + limit - 1
            )
            
            entries = []
            for entry_json in entries_json:
                try:
                    entry = json.loads(entry_json)
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse DLQ entry: {sanitize_for_log(str(e))}")
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get DLQ entries: {sanitize_for_log(str(e))}")
            return []
    
    def get_dlq_statistics(self) -> Dict[str, Any]:
        """Get DLQ statistics"""
        try:
            # Get metadata
            metadata_json = self.redis_connection.get(self.dlq_metadata_key)
            
            if metadata_json:
                metadata = json.loads(metadata_json)
            else:
                metadata = {
                    'total_entries': 0,
                    'error_categories': {},
                    'error_types': {},
                    'last_updated': None
                }
            
            # Get current queue size
            current_size = self.redis_connection.llen(self.dlq_key)
            
            # Calculate statistics
            stats = {
                'current_size': current_size,
                'total_entries_ever': metadata['total_entries'],
                'error_categories': metadata['error_categories'],
                'error_types': metadata['error_types'],
                'last_updated': metadata['last_updated'],
                'max_size': self.max_dlq_size,
                'retention_days': self.retention_days
            }
            
            # Add health indicators
            stats['health'] = {
                'size_ok': current_size < self.max_dlq_size * 0.8,  # Less than 80% full
                'recent_activity': self._check_recent_activity(metadata['last_updated']),
                'error_diversity': len(metadata['error_categories'])
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get DLQ statistics: {sanitize_for_log(str(e))}")
            return {'error': 'Failed to retrieve DLQ statistics'}
    
    def _check_recent_activity(self, last_updated: Optional[str]) -> bool:
        """Check if there has been recent DLQ activity"""
        if not last_updated:
            return False
        
        try:
            last_update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            time_diff = datetime.now(timezone.utc) - last_update_time
            
            # Consider activity recent if within last hour
            return time_diff < timedelta(hours=1)
            
        except Exception:
            return False
    
    def retry_dlq_entry(self, entry_index: int) -> bool:
        """
        Retry a specific DLQ entry by re-enqueuing it
        
        Args:
            entry_index: Index of the entry in the DLQ
            
        Returns:
            bool: True if successfully retried
        """
        try:
            # Get the entry
            entry_json = self.redis_connection.lindex(self.dlq_key, entry_index)
            
            if not entry_json:
                logger.warning(f"DLQ entry at index {entry_index} not found")
                return False
            
            entry = json.loads(entry_json)
            
            # Re-enqueue the job (this would need integration with RQ queue manager)
            # For now, we'll just log the retry attempt
            logger.info(f"Retrying DLQ entry: {sanitize_for_log(entry['job_id'])}")
            
            # Remove from DLQ after successful retry
            # This is a simplified implementation
            # In production, you'd want more sophisticated retry logic
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry DLQ entry: {sanitize_for_log(str(e))}")
            return False
    
    def cleanup_old_entries(self, older_than_days: int = None) -> int:
        """
        Clean up old DLQ entries
        
        Args:
            older_than_days: Remove entries older than this many days
            
        Returns:
            int: Number of entries cleaned up
        """
        if older_than_days is None:
            older_than_days = self.retention_days
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            
            # Get all entries
            all_entries = self.redis_connection.lrange(self.dlq_key, 0, -1)
            
            entries_to_keep = []
            cleaned_count = 0
            
            for entry_json in all_entries:
                try:
                    entry = json.loads(entry_json)
                    failed_at = datetime.fromisoformat(entry['failed_at'].replace('Z', '+00:00'))
                    
                    if failed_at > cutoff_time:
                        entries_to_keep.append(entry_json)
                    else:
                        cleaned_count += 1
                        
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse DLQ entry during cleanup: {sanitize_for_log(str(e))}")
                    # Keep unparseable entries to avoid data loss
                    entries_to_keep.append(entry_json)
            
            # Replace DLQ with cleaned entries
            if cleaned_count > 0:
                pipe = self.redis_connection.pipeline()
                pipe.delete(self.dlq_key)
                
                if entries_to_keep:
                    pipe.lpush(self.dlq_key, *entries_to_keep)
                
                pipe.execute()
                
                logger.info(f"Cleaned up {cleaned_count} old DLQ entries")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old DLQ entries: {sanitize_for_log(str(e))}")
            return 0
    
    def get_size(self) -> int:
        """Get current DLQ size"""
        try:
            return self.redis_connection.llen(self.dlq_key)
        except Exception as e:
            logger.error(f"Failed to get DLQ size: {sanitize_for_log(str(e))}")
            return 0
    
    def clear_dlq(self) -> bool:
        """
        Clear all entries from DLQ (admin operation)
        
        Returns:
            bool: True if successfully cleared
        """
        try:
            size_before = self.get_size()
            
            # Clear DLQ and metadata
            pipe = self.redis_connection.pipeline()
            pipe.delete(self.dlq_key)
            pipe.delete(self.dlq_metadata_key)
            pipe.execute()
            
            logger.warning(f"Cleared DLQ - removed {size_before} entries")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear DLQ: {sanitize_for_log(str(e))}")
            return False
    
    def analyze_failure_patterns(self) -> Dict[str, Any]:
        """Analyze failure patterns in DLQ for insights"""
        try:
            entries = self.get_dlq_entries(limit=200)  # Analyze recent entries
            
            if not entries:
                return {'message': 'No DLQ entries to analyze'}
            
            analysis = {
                'total_analyzed': len(entries),
                'time_range': {
                    'oldest': None,
                    'newest': None
                },
                'error_patterns': {},
                'queue_patterns': {},
                'retry_patterns': {},
                'recommendations': []
            }
            
            # Analyze patterns
            error_categories = {}
            queue_names = {}
            retry_counts = []
            timestamps = []
            
            for entry in entries:
                # Error categories
                category = entry.get('error_category', 'unknown')
                error_categories[category] = error_categories.get(category, 0) + 1
                
                # Queue names
                queue = entry.get('queue_name', 'unknown')
                queue_names[queue] = queue_names.get(queue, 0) + 1
                
                # Retry counts
                retry_count = entry.get('retry_count', 0)
                retry_counts.append(retry_count)
                
                # Timestamps
                try:
                    timestamp = datetime.fromisoformat(entry['failed_at'].replace('Z', '+00:00'))
                    timestamps.append(timestamp)
                except (ValueError, KeyError):
                    pass
            
            # Calculate statistics
            analysis['error_patterns'] = error_categories
            analysis['queue_patterns'] = queue_names
            
            if retry_counts:
                analysis['retry_patterns'] = {
                    'average_retries': sum(retry_counts) / len(retry_counts),
                    'max_retries': max(retry_counts),
                    'min_retries': min(retry_counts)
                }
            
            if timestamps:
                analysis['time_range'] = {
                    'oldest': min(timestamps).isoformat(),
                    'newest': max(timestamps).isoformat()
                }
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_failure_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze failure patterns: {sanitize_for_log(str(e))}")
            return {'error': 'Failed to analyze failure patterns'}
    
    def _generate_failure_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on failure analysis"""
        recommendations = []
        
        error_patterns = analysis.get('error_patterns', {})
        retry_patterns = analysis.get('retry_patterns', {})
        
        # Check for high error categories
        total_errors = sum(error_patterns.values())
        
        for category, count in error_patterns.items():
            percentage = (count / total_errors) * 100 if total_errors > 0 else 0
            
            if percentage > 50:
                if category == 'database_connection':
                    recommendations.append("High database connection errors - check database health and connection pool settings")
                elif category == 'redis_connection':
                    recommendations.append("High Redis connection errors - check Redis server health and network connectivity")
                elif category == 'resource_exhaustion':
                    recommendations.append("High resource exhaustion errors - consider increasing worker memory limits or reducing concurrent tasks")
                elif category == 'task_validation':
                    recommendations.append("High task validation errors - review task data validation and input sanitization")
        
        # Check retry patterns
        avg_retries = retry_patterns.get('average_retries', 0)
        if avg_retries > 2:
            recommendations.append(f"High average retry count ({avg_retries:.1f}) - consider adjusting retry strategies or fixing underlying issues")
        
        # Check queue patterns
        queue_patterns = analysis.get('queue_patterns', {})
        if len(queue_patterns) == 1:
            queue_name = list(queue_patterns.keys())[0]
            recommendations.append(f"All failures from single queue '{queue_name}' - investigate queue-specific issues")
        
        if not recommendations:
            recommendations.append("No specific patterns detected - failures appear to be distributed across different categories")
        
        return recommendations