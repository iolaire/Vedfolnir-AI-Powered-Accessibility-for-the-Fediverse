# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Platform Connection Manager

Manages platform connections in Redis for better performance and to avoid
database connection pool issues. Provides caching and fast access to
platform connection data.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import redis

from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

@dataclass
class PlatformConnectionData:
    """Platform connection data structure for Redis storage"""
    id: int
    user_id: int
    name: str
    platform_type: str
    instance_url: str
    username: Optional[str]
    access_token: str  # Will be encrypted
    client_key: Optional[str]
    client_secret: Optional[str]
    is_active: bool
    is_default: bool
    created_at: str
    updated_at: str
    last_used: Optional[str]

class RedisPlatformManager:
    """Redis-based platform connection manager"""
    
    def __init__(self, redis_client: redis.Redis, db_manager, encryption_key: str):
        self.redis_client = redis_client
        self.db_manager = db_manager
        self.encryption_key = encryption_key
        self.cache_ttl = 3600  # 1 hour cache TTL
    
    def _safe_decode_redis_data(self, data) -> str:
        """Safely decode Redis data that might be bytes or string"""
        if data is None:
            return None
        if isinstance(data, bytes):
            return data.decode('utf-8')
        elif isinstance(data, str):
            return data
        else:
            # Handle other types by converting to string
            return str(data)
        
    def _get_user_platforms_key(self, user_id: int) -> str:
        """Get Redis key for user's platform connections"""
        return f"user_platforms:{user_id}"
    
    def _get_platform_key(self, platform_id: int) -> str:
        """Get Redis key for individual platform connection"""
        return f"platform:{platform_id}"
    
    def _encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive platform data"""
        try:
            from cryptography.fernet import Fernet
            f = Fernet(self.encryption_key.encode())
            return f.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Error encrypting platform data: {e}")
            return data  # Fallback to unencrypted (not recommended for production)
    
    def _decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive platform data"""
        try:
            from cryptography.fernet import Fernet
            f = Fernet(self.encryption_key.encode())
            return f.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Error decrypting platform data: {e}")
            return encrypted_data  # Return as-is if decryption fails
    
    def _platform_to_dict(self, platform) -> Dict[str, Any]:
        """Convert database platform object to dictionary"""
        return {
            'id': platform.id,
            'user_id': platform.user_id,
            'name': platform.name,
            'platform_type': platform.platform_type,
            'instance_url': platform.instance_url,
            'username': platform.username,
            'access_token': platform.access_token,  # Already encrypted in DB
            'client_key': platform.client_key,
            'client_secret': platform.client_secret,
            'is_active': platform.is_active,
            'is_default': platform.is_default,
            'created_at': platform.created_at.isoformat() if platform.created_at else None,
            'updated_at': platform.updated_at.isoformat() if platform.updated_at else None,
            'last_used': platform.last_used.isoformat() if platform.last_used else None
        }
    
    def load_user_platforms_to_redis(self, user_id: int) -> List[Dict[str, Any]]:
        """Load user's platform connections from database to Redis"""
        try:
            # Get platforms from database
            session = self.db_manager.get_session()
            try:
                from models import PlatformConnection
                platforms = session.query(PlatformConnection).filter_by(
                    user_id=user_id, 
                    is_active=True
                ).order_by(
                    PlatformConnection.is_default.desc(), 
                    PlatformConnection.name
                ).all()
                
                # Convert to dictionaries
                platform_dicts = [self._platform_to_dict(p) for p in platforms]
                
                # Store in Redis
                if platform_dicts:
                    user_platforms_key = self._get_user_platforms_key(user_id)
                    self.redis_client.setex(
                        user_platforms_key,
                        self.cache_ttl,
                        json.dumps(platform_dicts)
                    )
                    
                    # Store individual platforms
                    for platform_dict in platform_dicts:
                        platform_key = self._get_platform_key(platform_dict['id'])
                        self.redis_client.setex(
                            platform_key,
                            self.cache_ttl,
                            json.dumps(platform_dict)
                        )
                
                logger.info(f"Loaded {len(platform_dicts)} platforms for user {user_id} to Redis")
                return platform_dicts
                
            finally:
                self.db_manager.close_session(session)
                
        except Exception as e:
            logger.error(f"Error loading platforms to Redis for user {user_id}: {e}")
            return []
    
    def get_user_platforms(self, user_id: int, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get user's platform connections from Redis (with database fallback)"""
        try:
            user_platforms_key = self._get_user_platforms_key(user_id)
            
            # Try to get from Redis first (unless force refresh)
            if not force_refresh:
                cached_data = self.redis_client.get(user_platforms_key)
                if cached_data:
                    decoded_data = self._safe_decode_redis_data(cached_data)
                    platforms = json.loads(decoded_data)
                    logger.debug(f"Retrieved {len(platforms)} platforms for user {user_id} from Redis cache")
                    return platforms
            
            # Load from database if not in cache or force refresh
            return self.load_user_platforms_to_redis(user_id)
            
        except Exception as e:
            logger.error(f"Error getting platforms for user {user_id}: {e}")
            return []
    
    def get_platform_by_id(self, platform_id: int, user_id: int = None) -> Optional[Dict[str, Any]]:
        """Get specific platform connection by ID"""
        try:
            platform_key = self._get_platform_key(platform_id)
            
            # Try Redis first
            cached_data = self.redis_client.get(platform_key)
            if cached_data:
                # Handle both bytes and string data from Redis
                decoded_data = self._safe_decode_redis_data(cached_data)
                platform = json.loads(decoded_data)
                    
                # Verify user access if user_id provided
                if user_id and platform.get('user_id') != user_id:
                    return None
                return platform
            
            # Fallback to database
            session = self.db_manager.get_session()
            try:
                from models import PlatformConnection
                query = session.query(PlatformConnection).filter_by(id=platform_id)
                if user_id:
                    query = query.filter_by(user_id=user_id)
                
                platform = query.first()
                if platform:
                    platform_dict = self._platform_to_dict(platform)
                    # Cache in Redis
                    self.redis_client.setex(
                        platform_key,
                        self.cache_ttl,
                        json.dumps(platform_dict)
                    )
                    return platform_dict
                return None
                
            finally:
                self.db_manager.close_session(session)
                
        except Exception as e:
            logger.error(f"Error getting platform {platform_id}: {e}")
            return None
    
    def get_default_platform(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's default platform connection"""
        platforms = self.get_user_platforms(user_id)
        
        # Look for default platform
        for platform in platforms:
            if platform.get('is_default'):
                return platform
        
        # Return first platform if no default set
        return platforms[0] if platforms else None
    
    def invalidate_user_cache(self, user_id: int):
        """Invalidate Redis cache for user's platforms"""
        try:
            user_platforms_key = self._get_user_platforms_key(user_id)
            
            # Get current platforms to invalidate individual caches
            cached_data = self.redis_client.get(user_platforms_key)
            if cached_data:
                decoded_data = self._safe_decode_redis_data(cached_data)
                platforms = json.loads(decoded_data)
                for platform in platforms:
                    platform_key = self._get_platform_key(platform['id'])
                    self.redis_client.delete(platform_key)
            
            # Delete user platforms cache
            self.redis_client.delete(user_platforms_key)
            logger.info(f"Invalidated platform cache for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error invalidating cache for user {user_id}: {e}")
    
    def get_platform_stats(self, user_id: int, platform_id: int = None) -> Dict[str, Any]:
        """Get platform statistics (cached in Redis)"""
        try:
            # Use default platform if none specified
            if not platform_id:
                default_platform = self.get_default_platform(user_id)
                if not default_platform:
                    return {}
                platform_id = default_platform['id']
            
            # Check Redis cache for stats
            stats_key = f"platform_stats:{user_id}:{platform_id}"
            cached_stats = self.redis_client.get(stats_key)
            
            if cached_stats:
                decoded_stats = self._safe_decode_redis_data(cached_stats)
                return json.loads(decoded_stats)
            
            # Calculate stats from database and cache
            stats = self._calculate_platform_stats(user_id, platform_id)
            
            # Cache for 5 minutes
            self.redis_client.setex(stats_key, 300, json.dumps(stats))
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting platform stats: {e}")
            return {}
    
    def _calculate_platform_stats(self, user_id: int, platform_id: int) -> Dict[str, Any]:
        """Calculate platform statistics from database"""
        try:
            session = self.db_manager.get_session()
            try:
                from models import Image, Post, ProcessingRun
                
                # Get platform connection
                platform = self.get_platform_by_id(platform_id, user_id)
                if not platform:
                    return {}
                
                # Calculate stats - Images are linked to Posts, which have user_id
                total_images = session.query(Image).join(Post).filter(Post.user_id == user_id).count()
                total_posts = session.query(Post).filter_by(user_id=user_id).count()
                
                # Processing runs for this platform
                processing_runs = session.query(ProcessingRun).filter_by(
                    user_id=user_id,
                    platform_type=platform['platform_type'],
                    instance_url=platform['instance_url']
                ).count()
                
                return {
                    'total_images': total_images,
                    'total_posts': total_posts,
                    'processing_runs': processing_runs,
                    'platform_name': platform['name'],
                    'platform_type': platform['platform_type']
                }
                
            finally:
                self.db_manager.close_session(session)
                
        except Exception as e:
            logger.error(f"Error calculating platform stats: {e}")
            return {}
    
    def _get_user_settings_key(self, user_id: int, platform_id: int) -> str:
        """Get Redis key for user's caption generation settings"""
        return f"user_settings:{user_id}:{platform_id}"
    
    def get_user_settings(self, user_id: int, platform_id: int) -> Optional[Dict[str, Any]]:
        """Get user's caption generation settings from Redis (with database fallback)"""
        try:
            settings_key = self._get_user_settings_key(user_id, platform_id)
            
            # Try Redis first
            cached_data = self.redis_client.get(settings_key)
            if cached_data:
                decoded_data = self._safe_decode_redis_data(cached_data)
                settings = json.loads(decoded_data)
                logger.debug(f"Retrieved user settings for user {user_id}, platform {platform_id} from Redis cache")
                return settings
            
            # Fallback to database
            session = self.db_manager.get_session()
            try:
                from models import CaptionGenerationUserSettings
                settings_record = session.query(CaptionGenerationUserSettings).filter_by(
                    user_id=user_id,
                    platform_connection_id=platform_id
                ).first()
                
                if settings_record:
                    settings_dict = {
                        'id': settings_record.id,
                        'user_id': settings_record.user_id,
                        'platform_connection_id': settings_record.platform_connection_id,
                        'max_posts_per_run': settings_record.max_posts_per_run,
                        'max_caption_length': settings_record.max_caption_length,
                        'optimal_min_length': settings_record.optimal_min_length,
                        'optimal_max_length': settings_record.optimal_max_length,
                        'reprocess_existing': settings_record.reprocess_existing,
                        'processing_delay': settings_record.processing_delay,
                        'created_at': settings_record.created_at.isoformat() if settings_record.created_at else None,
                        'updated_at': settings_record.updated_at.isoformat() if settings_record.updated_at else None
                    }
                    
                    # Cache in Redis for 1 hour
                    self.redis_client.setex(settings_key, self.cache_ttl, json.dumps(settings_dict))
                    logger.info(f"Loaded user settings for user {user_id}, platform {platform_id} to Redis")
                    return settings_dict
                
                return None
                
            finally:
                self.db_manager.close_session(session)
                
        except Exception as e:
            logger.error(f"Error getting user settings for user {user_id}, platform {platform_id}: {e}")
            return None
    
    def update_user_settings(self, user_id: int, platform_id: int, settings: Dict[str, Any]) -> bool:
        """Update user's caption generation settings in both database and Redis"""
        try:
            session = self.db_manager.get_session()
            try:
                from models import CaptionGenerationUserSettings
                from datetime import datetime, timezone
                
                # Get or create settings record
                settings_record = session.query(CaptionGenerationUserSettings).filter_by(
                    user_id=user_id,
                    platform_connection_id=platform_id
                ).first()
                
                if not settings_record:
                    settings_record = CaptionGenerationUserSettings(
                        user_id=user_id,
                        platform_connection_id=platform_id,
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(settings_record)
                
                # Update settings
                settings_record.max_posts_per_run = settings.get('max_posts_per_run', 50)
                settings_record.max_caption_length = settings.get('max_caption_length', 500)
                settings_record.optimal_min_length = settings.get('optimal_min_length', 150)
                settings_record.optimal_max_length = settings.get('optimal_max_length', 450)
                settings_record.reprocess_existing = settings.get('reprocess_existing', False)
                settings_record.processing_delay = settings.get('processing_delay', 1.0)
                settings_record.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                # Update Redis cache
                settings_dict = {
                    'id': settings_record.id,
                    'user_id': settings_record.user_id,
                    'platform_connection_id': settings_record.platform_connection_id,
                    'max_posts_per_run': settings_record.max_posts_per_run,
                    'max_caption_length': settings_record.max_caption_length,
                    'optimal_min_length': settings_record.optimal_min_length,
                    'optimal_max_length': settings_record.optimal_max_length,
                    'reprocess_existing': settings_record.reprocess_existing,
                    'processing_delay': settings_record.processing_delay,
                    'created_at': settings_record.created_at.isoformat() if settings_record.created_at else None,
                    'updated_at': settings_record.updated_at.isoformat() if settings_record.updated_at else None
                }
                
                settings_key = self._get_user_settings_key(user_id, platform_id)
                self.redis_client.setex(settings_key, self.cache_ttl, json.dumps(settings_dict))
                
                logger.info(f"Updated user settings for user {user_id}, platform {platform_id}")
                return True
                
            finally:
                self.db_manager.close_session(session)
                
        except Exception as e:
            logger.error(f"Error updating user settings for user {user_id}, platform {platform_id}: {e}")
            return False
    
    def invalidate_user_settings_cache(self, user_id: int, platform_id: int):
        """Invalidate Redis cache for user's settings"""
        try:
            settings_key = self._get_user_settings_key(user_id, platform_id)
            self.redis_client.delete(settings_key)
            logger.info(f"Invalidated settings cache for user {user_id}, platform {platform_id}")
        except Exception as e:
            logger.error(f"Error invalidating settings cache for user {user_id}, platform {platform_id}: {e}")

# Global instance
_redis_platform_manager = None

def get_redis_platform_manager(redis_client: redis.Redis, db_manager, encryption_key: str) -> RedisPlatformManager:
    """Get or create Redis platform manager instance"""
    global _redis_platform_manager
    
    if _redis_platform_manager is None:
        _redis_platform_manager = RedisPlatformManager(redis_client, db_manager, encryption_key)
        logger.info("Redis platform manager initialized")
    
    return _redis_platform_manager
