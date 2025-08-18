# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Factory

This module provides a factory for creating session managers based on configuration.
It can create either Redis-based or database-based session managers.
"""

import os
from logging import getLogger
from typing import Optional, Union

from database import DatabaseManager
from session_config import get_session_config, SessionConfig

logger = getLogger(__name__)

def create_session_manager(db_manager: DatabaseManager, config: Optional[SessionConfig] = None, 
                          security_manager=None, monitor=None):
    """
    Create appropriate session manager based on configuration
    
    Args:
        db_manager: Database manager instance
        config: Session configuration
        security_manager: Security manager instance
        monitor: Session monitor instance
        
    Returns:
        Session manager instance (Redis or Database based)
    """
    session_storage = os.getenv('SESSION_STORAGE', 'database').lower()
    
    if session_storage == 'redis':
        try:
            from redis_session_manager import RedisSessionManager
            
            # Get Redis configuration from environment
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_db = int(os.getenv('REDIS_DB', '0'))
            redis_password = os.getenv('REDIS_PASSWORD')
            redis_ssl = os.getenv('REDIS_SSL', 'false').lower() == 'true'
            
            logger.info(f"Creating Redis session manager: {redis_host}:{redis_port}")
            
            return RedisSessionManager(
                db_manager=db_manager,
                config=config,
                redis_host=redis_host,
                redis_port=redis_port,
                redis_db=redis_db,
                redis_password=redis_password,
                redis_ssl=redis_ssl,
                security_manager=security_manager,
                monitor=monitor
            )
            
        except ImportError as e:
            logger.error(f"Redis not available, falling back to database sessions: {e}")
            logger.error("Install redis with: pip install redis")
            session_storage = 'database'
        except Exception as e:
            logger.error(f"Failed to create Redis session manager, falling back to database: {e}")
            session_storage = 'database'
    
    if session_storage == 'database':
        from unified_session_manager import UnifiedSessionManager
        
        logger.info("Creating database session manager")
        
        return UnifiedSessionManager(
            db_manager=db_manager,
            config=config,
            security_manager=security_manager,
            monitor=monitor
        )
    
    else:
        raise ValueError(f"Unknown session storage type: {session_storage}")

def get_session_manager_type() -> str:
    """Get the configured session manager type"""
    return os.getenv('SESSION_STORAGE', 'database').lower()

def is_redis_session_manager() -> bool:
    """Check if Redis session manager is configured"""
    return get_session_manager_type() == 'redis'

def is_database_session_manager() -> bool:
    """Check if database session manager is configured"""
    return get_session_manager_type() == 'database'