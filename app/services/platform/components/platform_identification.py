# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Platform Identification Utility

This module provides shared functionality for identifying and retrieving user platform data
using a consistent 5-step approach across the application.
"""

from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from flask import current_app, g
from flask_login import current_user
from models import PlatformConnection
from app.core.security.middleware.platform_access_middleware import filter_platforms_for_user
import logging

logger = logging.getLogger(__name__)

@dataclass
class PlatformIdentificationResult:
    """
    Result of platform identification process.
    
    Attributes:
        current_platform: The identified current platform object (None if not found)
        platform_connection_id: ID of the current platform (None if not found)
        user_platforms: List of all user platforms (for template rendering)
        platform_stats: Platform statistics dictionary
        source: Source of platform data ('redis' or 'database')
    """
    current_platform: Optional[Any] = None
    platform_connection_id: Optional[int] = None
    user_platforms: List[Any] = None
    platform_stats: Dict[str, Any] = None
    source: str = 'unknown'

class PlatformObj:
    """Helper class to convert dictionary platform data to object for template compatibility"""
    def __init__(self, data: Dict[str, Any]):
        for key, value in data.items():
            setattr(self, key, value)

def identify_user_platform(
    user_id: int,
    redis_platform_manager: Any,
    db_manager: Any,
    include_stats: bool = True,
    update_session_context: bool = False  # Changed default to False
) -> PlatformIdentificationResult:
    """
    Identify user's current platform using 5-step approach.
    
    This function implements the standardized 5-step platform identification process:
    1. Redis-First Approach: Get Redis platform manager
    2. Get User Platforms from Redis: Try Redis cache first
    3. Database Fallback: Fall back to database if Redis fails
    4. Platform Selection Logic: Select default or first available platform
    5. Cache Back to Redis: Update Redis cache with fresh data
    
    Args:
        user_id: ID of the user to identify platform for
        redis_platform_manager: Redis platform manager instance
        db_manager: Database manager instance
        include_stats: Whether to include platform statistics (default: True)
        update_session_context: Whether to update session context with platform data (default: True)
        
    Returns:
        PlatformIdentificationResult containing platform data and metadata
        
    Example:
        result = identify_user_platform(
            current_user.id, 
            app.config.get('redis_platform_manager'),
            db_manager
        )
        if result.current_platform:
            platform_id = result.platform_connection_id
            # Use platform...
        else:
            # No platform found, redirect to platform management
    """
    result = PlatformIdentificationResult()
    
    # Step 1: Redis-First Approach
    if not redis_platform_manager:
        logger.warning("Redis platform manager not available, using database only")
        result = _identify_platform_from_database(user_id, db_manager, include_stats)
    else:
        # Step 2: Get User Platforms from Redis
        try:
            user_platforms_dict = redis_platform_manager.get_user_platforms(user_id)
            current_platform_dict = redis_platform_manager.get_default_platform(user_id)

            print(f"DEBUG: Redis returned {len(user_platforms_dict) if user_platforms_dict else 0} platforms for user {user_id}")
            print(f"DEBUG: Current platform dict: {current_platform_dict}")

            # CRITICAL FIX: Validate that Redis platform data belongs to current user
            if current_platform_dict and current_platform_dict.get('user_id') == user_id:
                # Convert dict platforms to objects for template compatibility
                result.user_platforms = [PlatformObj(p) for p in user_platforms_dict] if user_platforms_dict else []
                result.current_platform = PlatformObj(current_platform_dict)
                result.platform_connection_id = current_platform_dict['id']
                result.source = 'redis'

                # Get platform statistics if requested
                if include_stats:
                    try:
                        result.platform_stats = redis_platform_manager.get_platform_stats(
                            user_id,
                            current_platform_dict['id']
                        )
                    except Exception as stats_error:
                        logger.warning(f"Failed to get platform stats from Redis: {stats_error}")
                        result.platform_stats = {}

                print(f"DEBUG: Found platform from Redis: {result.current_platform.name} (ID: {result.platform_connection_id})")
            else:
                print(f"DEBUG: Invalid platform data in Redis for user {user_id}, falling back to database")
                # Platform data is invalid or belongs to different user, fall back to database
                result = _identify_platform_from_database(user_id, db_manager, include_stats, redis_platform_manager)

        except Exception as redis_error:
            print(f"DEBUG: Redis platform cache failed: {redis_error}")
            logger.warning(f"Redis platform cache failed, falling back to database: {redis_error}")
            # Step 3: Database Fallback (if Redis fails)
            result = _identify_platform_from_database(user_id, db_manager, include_stats, redis_platform_manager)
    
    # CRITICAL: Update session context with platform data (based on previous fix)
    if update_session_context and result.current_platform and result.platform_connection_id:
        try:
            _update_session_context_with_platform(result.platform_connection_id, result.current_platform)
            print(f"DEBUG: Updated session context with platform {result.platform_connection_id}")
        except Exception as session_error:
            logger.error(f"Failed to update session context with platform data: {session_error}")
    
    return result

def _identify_platform_from_database(
    user_id: int,
    db_manager: Any,
    include_stats: bool = True,
    redis_platform_manager: Any = None
) -> PlatformIdentificationResult:
    """
    Internal function to identify platform from database with optional Redis caching.
    
    Args:
        user_id: ID of the user
        db_manager: Database manager instance
        include_stats: Whether to include platform statistics
        redis_platform_manager: Optional Redis manager for caching results
        
    Returns:
        PlatformIdentificationResult from database lookup
    """
    result = PlatformIdentificationResult()
    result.source = 'database'
    
    session = db_manager.get_session()
    try:
        # Get user's platform connections - always filter by user_id for platform selection
        platforms_query = session.query(PlatformConnection).filter_by(
            user_id=user_id,
            is_active=True
        )
        user_platforms = platforms_query.order_by(
            PlatformConnection.is_default.desc(), 
            PlatformConnection.name
        ).all()
        
        # Step 4: Platform Selection Logic
        current_platform = None
        for platform in user_platforms:
            if platform.is_default:
                current_platform = platform
                break
        if not current_platform and user_platforms:
            current_platform = user_platforms[0]
        
        # Set result data
        result.user_platforms = user_platforms

        # CRITICAL FIX: Verify that the current platform belongs to the current user
        if current_platform and current_platform.user_id != user_id:
            logger.warning(f"Platform {current_platform.id} belongs to user {current_platform.user_id}, not current user {user_id}. Resetting platform selection.")
            current_platform = None
            result.platform_connection_id = None
        else:
            result.current_platform = current_platform
            result.platform_connection_id = current_platform.id if current_platform else None
        
        # Get platform statistics if requested and we have a current platform
        if include_stats and current_platform:
            try:
                user_summary = db_manager.get_user_platform_summary(user_id)
                result.platform_stats = {
                    'total_images': user_summary.get('total_images', 0),
                    'total_posts': user_summary.get('total_posts', 0),
                    'platform_name': current_platform.name,
                    'platform_type': current_platform.platform_type
                }
            except Exception as stats_error:
                logger.warning(f"Failed to get platform stats from database: {stats_error}")
                result.platform_stats = {}
        
        if current_platform:
            logger.debug(f"Found platform from database: {current_platform.name} (ID: {result.platform_connection_id})")
        else:
            logger.warning(f"No platforms found for user {user_id}")
        
        # Step 5: Cache Back to Redis
        if redis_platform_manager and current_platform:
            try:
                redis_platform_manager.load_user_platforms_to_redis(user_id)
                logger.debug(f"Cached platform data to Redis for user {user_id}")
            except Exception as cache_error:
                logger.warning(f"Failed to cache platforms to Redis: {cache_error}")
                
    finally:
        session.close()
    
    return result

def require_platform_selection(result: PlatformIdentificationResult) -> bool:
    """
    Check if platform selection is required based on identification result.
    
    Args:
        result: PlatformIdentificationResult from identify_user_platform()
        
    Returns:
        True if user needs to select a platform, False if platform is available
    """
    needs_selection = not result.current_platform or not result.platform_connection_id
    print(f"DEBUG: require_platform_selection - current_platform: {result.current_platform}, platform_connection_id: {result.platform_connection_id}, needs_selection: {needs_selection}")
    return needs_selection

def _update_session_context_with_platform(platform_connection_id: int, platform_obj: Any) -> None:
    """
    Update session context with platform data (based on previous platform session fix).
    
    This function ensures that platform data is properly stored in the session context
    so that other parts of the system (like @platform_required decorator) can access it.
    
    Args:
        platform_connection_id: ID of the platform connection
        platform_obj: Platform object with platform data
    """
    try:
        from flask import session, g
        
        # Handle both dictionary and object cases for platform data
        if isinstance(platform_obj, dict):
            platform_name = platform_obj.get('name')
            platform_type = platform_obj.get('platform_type')
            platform_instance_url = platform_obj.get('instance_url', '')
        else:
            platform_name = getattr(platform_obj, 'name', None)
            platform_type = getattr(platform_obj, 'platform_type', None)
            platform_instance_url = getattr(platform_obj, 'instance_url', '')
        
        # Update Flask session with platform data (critical for persistence)
        session['platform_connection_id'] = platform_connection_id
        session['platform_name'] = platform_name
        session['platform_type'] = platform_type
        session['platform_instance_url'] = platform_instance_url
        
        # CRITICAL: Mark Flask session as modified to ensure it gets saved
        # This was the key fix from the previous platform session issue
        session.modified = True
        
        # Update g.session_context for immediate use in current request
        if not hasattr(g, 'session_context'):
            g.session_context = {}
        
        g.session_context.update({
            'platform_connection_id': platform_connection_id,
            'platform_name': platform_name,
            'platform_type': platform_type,
            'platform_instance_url': platform_instance_url
        })
        
        logger.debug(f"Updated session context with platform {platform_connection_id} ({platform_name})")
        
    except Exception as e:
        logger.error(f"Failed to update session context with platform data: {e}")
        raise

def get_platform_redirect_message(result: PlatformIdentificationResult) -> str:
    """
    Get appropriate flash message for platform selection redirect.
    
    Args:
        result: PlatformIdentificationResult from identify_user_platform()
        
    Returns:
        Appropriate flash message string
    """
    if not result.user_platforms:
        return 'You need to set up at least one platform connection to access this feature.'
    else:
        return 'Please select a platform to continue.'
