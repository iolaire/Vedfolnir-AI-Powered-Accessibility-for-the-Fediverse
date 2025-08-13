# web_caption_generation_service

Web Caption Generation Service

This is the main orchestration service for web-based caption generation.
It coordinates between the task queue, progress tracking, and caption generation components.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/web_caption_generation_service.py`

## Classes

### WebCaptionGenerationService

```python
class WebCaptionGenerationService
```

Main orchestration service for web-based caption generation

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager)
```

**Type:** Instance method

#### start_caption_generation

```python
async def start_caption_generation(self, user_id: int, platform_connection_id: int, settings: Optional[CaptionGenerationSettings]) -> str
```

Start caption generation for a user and platform

Args:
    user_id: The user ID
    platform_connection_id: The platform connection ID
    settings: Optional custom settings (uses user defaults if not provided)
    
Returns:
    str: The task ID
    
Raises:
    ValueError: If validation fails
    RuntimeError: If task creation fails

**Type:** Instance method

#### get_generation_status

```python
def get_generation_status(self, task_id: str, user_id: int) -> Optional[Dict[str, Any]]
```

Get the status of a caption generation task

Args:
    task_id: The task ID
    user_id: Optional user ID for authorization
    
Returns:
    Dict with task status information or None if not found

**Type:** Instance method

#### cancel_generation

```python
def cancel_generation(self, task_id: str, user_id: int) -> bool
```

Cancel a caption generation task

Args:
    task_id: The task ID to cancel
    user_id: The user ID for authorization
    
Returns:
    bool: True if cancellation was successful

**Type:** Instance method

#### get_generation_results

```python
async def get_generation_results(self, task_id: str, user_id: int) -> Optional[GenerationResults]
```

Get the results of a completed caption generation task

Args:
    task_id: The task ID
    user_id: Optional user ID for authorization
    
Returns:
    GenerationResults or None if not found or not completed

**Type:** Instance method

#### _validate_user_platform_access

```python
async def _validate_user_platform_access(self, user_id: int, platform_connection_id: int)
```

Validate that a user has access to a platform connection

Args:
    user_id: The user ID
    platform_connection_id: The platform connection ID
    
Raises:
    ValueError: If validation fails

**Type:** Instance method

#### _get_user_settings

```python
async def _get_user_settings(self, user_id: int, platform_connection_id: int) -> CaptionGenerationSettings
```

Get user's caption generation settings for a platform

Args:
    user_id: The user ID
    platform_connection_id: The platform connection ID
    
Returns:
    CaptionGenerationSettings: User settings or defaults

**Type:** Instance method

#### _ensure_background_processor

```python
def _ensure_background_processor(self)
```

Ensure background task processor is running

**Type:** Instance method

#### _background_processor

```python
async def _background_processor(self)
```

Background task processor that handles queued caption generation tasks

**Type:** Instance method

#### _process_task

```python
async def _process_task(self, task: CaptionGenerationTask)
```

Process a single caption generation task

Args:
    task: The task to process

**Decorators:**
- `@handle_caption_error(context={'operation': 'process_task'})`

**Type:** Instance method

#### shutdown

```python
async def shutdown(self)
```

Shutdown the service and clean up background tasks

**Type:** Instance method

#### get_service_stats

```python
def get_service_stats(self) -> Dict[str, Any]
```

Get service statistics

Returns:
    Dict with service statistics

**Type:** Instance method

#### save_user_settings

```python
async def save_user_settings(self, user_id: int, platform_connection_id: int, settings: CaptionGenerationSettings) -> bool
```

Save user's caption generation settings for a platform

Args:
    user_id: The user ID
    platform_connection_id: The platform connection ID
    settings: The settings to save
    
Returns:
    bool: True if settings were saved successfully

**Type:** Instance method

#### get_user_settings

```python
async def get_user_settings(self, user_id: int, platform_connection_id: int) -> CaptionGenerationSettings
```

Get user's caption generation settings for a platform

Args:
    user_id: The user ID
    platform_connection_id: The platform connection ID
    
Returns:
    CaptionGenerationSettings: User settings or defaults

**Type:** Instance method

#### _process_next_task_immediately

```python
async def _process_next_task_immediately(self)
```

Process the next available task immediately

**Type:** Instance method

#### get_user_task_history

```python
async def get_user_task_history(self, user_id: int, limit: int) -> list
```

Get task history for a user

Args:
    user_id: The user ID
    limit: Maximum number of tasks to return
    
Returns:
    List of task information dictionaries

**Type:** Instance method

