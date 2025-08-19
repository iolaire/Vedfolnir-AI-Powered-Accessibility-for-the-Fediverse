# Redis Caption Generation Fix Summary

## Issue
The `/caption_generation` route was not using the Redis session manager for platform management, instead relying on database sessions which could cause performance issues and session conflicts.

## Changes Made

### 1. Enhanced Redis Platform Manager (`redis_platform_manager.py`)
Added user settings management to the Redis platform manager:

- **`get_user_settings(user_id, platform_id)`**: Retrieves user caption generation settings from Redis cache with database fallback
- **`update_user_settings(user_id, platform_id, settings)`**: Updates user settings in both database and Redis cache
- **`invalidate_user_settings_cache(user_id, platform_id)`**: Invalidates Redis cache for user settings
- **`_get_user_settings_key(user_id, platform_id)`**: Generates Redis keys for user settings

### 2. Updated Caption Generation Route (`web_app.py`)
Modified the `/caption_generation` route to use Redis platform management:

**Before:**
```python
# Get user's current settings
user_settings = None
with unified_session_manager.get_db_session() as session:
    from models import CaptionGenerationUserSettings
    user_settings_record = session.query(CaptionGenerationUserSettings).filter_by(
        user_id=current_user.id,
        platform_connection_id=platform_connection_id
    ).first()
    
    if user_settings_record:
        user_settings = user_settings_record.to_settings_dataclass()
```

**After:**
```python
# Get user's current settings using Redis platform manager
user_settings = None
try:
    # Use Redis platform manager for both platform data and user settings
    platform_data = redis_platform_manager.get_platform_by_id(platform_connection_id, current_user.id)
    if not platform_data:
        app.logger.warning(f"Platform {platform_connection_id} not found in Redis cache for user {current_user.id}")
        flash('Platform connection not found.', 'error')
        return redirect(url_for('platform_management'))
    
    # Get user settings from Redis (with database fallback)
    user_settings_dict = redis_platform_manager.get_user_settings(current_user.id, platform_connection_id)
    if user_settings_dict:
        # Convert to dataclass if needed
        from models import CaptionGenerationUserSettings
        # Create a mock settings record to use the to_settings_dataclass method
        mock_settings = CaptionGenerationUserSettings()
        for key, value in user_settings_dict.items():
            if hasattr(mock_settings, key):
                setattr(mock_settings, key, value)
        user_settings = mock_settings.to_settings_dataclass()
        app.logger.debug(f"Retrieved user settings from Redis for user {current_user.id}, platform {platform_connection_id}")
    else:
        app.logger.info(f"No user settings found for user {current_user.id}, platform {platform_connection_id}")
        
except Exception as e:
    app.logger.error(f"Error getting platform data/settings from Redis: {sanitize_for_log(str(e))}")
    # Fallback to database if Redis fails
    with unified_session_manager.get_db_session() as session:
        from models import CaptionGenerationUserSettings
        user_settings_record = session.query(CaptionGenerationUserSettings).filter_by(
            user_id=current_user.id,
            platform_connection_id=platform_connection_id
        ).first()
        
        if user_settings_record:
            user_settings = user_settings_record.to_settings_dataclass()
```

### 3. Updated Settings Save Route
Modified the settings save functionality to use Redis:

**Before:**
```python
# Update or create user settings
with unified_session_manager.get_db_session() as session:
    from models import CaptionGenerationUserSettings
    # ... database operations
```

**After:**
```python
# Update or create user settings using Redis platform manager
try:
    # Prepare settings data
    settings_data = {
        'max_posts_per_run': max_posts_per_run or 50,
        'max_caption_length': 500,
        'optimal_min_length': 80,
        'optimal_max_length': 200,
        'reprocess_existing': False,
        'processing_delay': 1.0
    }
    
    # Update settings using Redis platform manager
    success = redis_platform_manager.update_user_settings(
        current_user.id, 
        platform_connection_id, 
        settings_data
    )
    
    if success:
        # Success response
    else:
        # Fallback to database if Redis update fails
```

### 4. Updated Caption Settings Form Route
Modified the caption settings form to use Redis for retrieving current settings.

## Benefits

1. **Performance**: Redis caching reduces database queries for frequently accessed platform and settings data
2. **Consistency**: All platform-related data now uses the same Redis-based caching system
3. **Reliability**: Database fallback ensures functionality even if Redis is temporarily unavailable
4. **Scalability**: Redis-based session management scales better than database sessions

## Testing

Created `test_redis_platform_manager.py` to verify:
- Redis connection functionality
- Platform data caching and retrieval
- User settings management
- Cache invalidation

## Configuration

The system uses Redis when `SESSION_STORAGE=redis` is set in the environment variables. The current configuration:

```bash
SESSION_STORAGE=redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=ZkjBdCsoodbvY6EpXF
REDIS_SSL=false
```

## Backward Compatibility

All changes include database fallbacks to ensure the system continues to work even if Redis is unavailable, maintaining backward compatibility with existing deployments.
