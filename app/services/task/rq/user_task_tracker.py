# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Task Tracker

Enforces single-task-per-user constraint using Redis-based tracking.
"""

import logging
from typing import Optional
import redis
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


class UserTaskTracker:
    """Enforces single-task-per-user constraint using Redis"""
    
    def __init__(self, redis_connection: redis.Redis):
        """
        Initialize User Task Tracker
        
        Args:
            redis_connection: Redis connection instance
        """
        self.redis = redis_connection
        self.user_task_prefix = "vedfolnir:user_active_task:"
        self.task_ttl = 7200  # 2 hours TTL for safety
    
    def set_user_active_task(self, user_id: int, task_id: str) -> bool:
        """
        Set active task for user (atomic operation)
        
        Args:
            user_id: User ID
            task_id: Task ID to set as active
            
        Returns:
            bool: True if task was set (no existing active task), False if user already has active task
        """
        try:
            key = f"{self.user_task_prefix}{user_id}"
            
            # Use SET with NX (only set if key doesn't exist) for atomic operation
            result = self.redis.set(key, task_id, nx=True, ex=self.task_ttl)
            
            if result:
                logger.info(f"Set active task {sanitize_for_log(task_id)} for user {sanitize_for_log(str(user_id))}")
                return True
            else:
                existing_task = self.redis.get(key)
                if existing_task:
                    existing_task = existing_task.decode('utf-8') if isinstance(existing_task, bytes) else existing_task
                    logger.warning(f"User {sanitize_for_log(str(user_id))} already has active task: {sanitize_for_log(existing_task)}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting active task for user {sanitize_for_log(str(user_id))}: {sanitize_for_log(str(e))}")
            return False
    
    def get_user_active_task(self, user_id: int) -> Optional[str]:
        """
        Get active task for user
        
        Args:
            user_id: User ID
            
        Returns:
            str: Active task ID or None if no active task
        """
        try:
            key = f"{self.user_task_prefix}{user_id}"
            task_id = self.redis.get(key)
            
            if task_id:
                task_id = task_id.decode('utf-8') if isinstance(task_id, bytes) else task_id
                return task_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting active task for user {sanitize_for_log(str(user_id))}: {sanitize_for_log(str(e))}")
            return None
    
    def clear_user_active_task(self, user_id: int) -> None:
        """
        Clear active task for user
        
        Args:
            user_id: User ID
        """
        try:
            key = f"{self.user_task_prefix}{user_id}"
            result = self.redis.delete(key)
            
            if result:
                logger.info(f"Cleared active task for user {sanitize_for_log(str(user_id))}")
            
        except Exception as e:
            logger.error(f"Error clearing active task for user {sanitize_for_log(str(user_id))}: {sanitize_for_log(str(e))}")
    
    def has_active_task(self, user_id: int) -> bool:
        """
        Check if user has an active task
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if user has active task, False otherwise
        """
        try:
            key = f"{self.user_task_prefix}{user_id}"
            return self.redis.exists(key) > 0
            
        except Exception as e:
            logger.error(f"Error checking active task for user {sanitize_for_log(str(user_id))}: {sanitize_for_log(str(e))}")
            return False
    
    def extend_task_ttl(self, user_id: int, ttl_seconds: int = None) -> bool:
        """
        Extend TTL for user's active task
        
        Args:
            user_id: User ID
            ttl_seconds: TTL in seconds (defaults to self.task_ttl)
            
        Returns:
            bool: True if TTL was extended, False if no active task or error
        """
        try:
            key = f"{self.user_task_prefix}{user_id}"
            ttl = ttl_seconds or self.task_ttl
            
            # Only extend if key exists
            if self.redis.exists(key):
                result = self.redis.expire(key, ttl)
                if result:
                    logger.debug(f"Extended TTL for user {sanitize_for_log(str(user_id))} active task to {ttl} seconds")
                return result
            
            return False
            
        except Exception as e:
            logger.error(f"Error extending TTL for user {sanitize_for_log(str(user_id))}: {sanitize_for_log(str(e))}")
            return False
    
    def cleanup_expired_tasks(self) -> int:
        """
        Clean up expired task tracking entries
        
        Returns:
            int: Number of expired entries cleaned up
        """
        try:
            # Redis automatically handles TTL expiration, but we can scan for any orphaned keys
            pattern = f"{self.user_task_prefix}*"
            keys = self.redis.keys(pattern)
            
            expired_count = 0
            for key in keys:
                ttl = self.redis.ttl(key)
                if ttl == -1:  # Key exists but has no TTL (shouldn't happen)
                    self.redis.expire(key, self.task_ttl)
                    expired_count += 1
                elif ttl == -2:  # Key doesn't exist (race condition)
                    expired_count += 1
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} user task tracking entries")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Error during user task cleanup: {sanitize_for_log(str(e))}")
            return 0
    
    def get_all_active_tasks(self) -> dict:
        """
        Get all active tasks (for monitoring/debugging)
        
        Returns:
            dict: Mapping of user_id -> task_id for all active tasks
        """
        try:
            pattern = f"{self.user_task_prefix}*"
            keys = self.redis.keys(pattern)
            
            active_tasks = {}
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                
                # Extract user_id from key
                user_id_str = key.replace(self.user_task_prefix, '')
                try:
                    user_id = int(user_id_str)
                    task_id = self.redis.get(key)
                    if task_id:
                        if isinstance(task_id, bytes):
                            task_id = task_id.decode('utf-8')
                        active_tasks[user_id] = task_id
                except ValueError:
                    logger.warning(f"Invalid user ID in key: {sanitize_for_log(key)}")
                    continue
            
            return active_tasks
            
        except Exception as e:
            logger.error(f"Error getting all active tasks: {sanitize_for_log(str(e))}")
            return {}
    
    def force_clear_user_task(self, user_id: int, task_id: str) -> bool:
        """
        Force clear specific task for user (admin operation)
        
        Args:
            user_id: User ID
            task_id: Task ID that should be cleared
            
        Returns:
            bool: True if task was cleared, False if different task or error
        """
        try:
            key = f"{self.user_task_prefix}{user_id}"
            current_task = self.redis.get(key)
            
            if current_task:
                if isinstance(current_task, bytes):
                    current_task = current_task.decode('utf-8')
                
                if current_task == task_id:
                    result = self.redis.delete(key)
                    if result:
                        logger.info(f"Force cleared task {sanitize_for_log(task_id)} for user {sanitize_for_log(str(user_id))}")
                        return True
                else:
                    logger.warning(f"Cannot force clear task {sanitize_for_log(task_id)} for user {sanitize_for_log(str(user_id))} - current task is {sanitize_for_log(current_task)}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error force clearing task for user {sanitize_for_log(str(user_id))}: {sanitize_for_log(str(e))}")
            return False
    
    def get_stats(self) -> dict:
        """
        Get statistics about user task tracking
        
        Returns:
            dict: Statistics including active task count, etc.
        """
        try:
            pattern = f"{self.user_task_prefix}*"
            keys = self.redis.keys(pattern)
            
            stats = {
                'active_tasks_count': len(keys),
                'prefix': self.user_task_prefix,
                'default_ttl': self.task_ttl
            }
            
            # Count tasks by TTL ranges
            ttl_ranges = {
                'expired': 0,
                'expiring_soon': 0,  # < 300 seconds
                'normal': 0
            }
            
            for key in keys:
                ttl = self.redis.ttl(key)
                if ttl == -2:  # Expired
                    ttl_ranges['expired'] += 1
                elif 0 <= ttl < 300:  # Expiring soon
                    ttl_ranges['expiring_soon'] += 1
                else:
                    ttl_ranges['normal'] += 1
            
            stats['ttl_distribution'] = ttl_ranges
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user task tracker stats: {sanitize_for_log(str(e))}")
            return {'error': str(e)}