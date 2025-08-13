# platform_aware_caption_adapter

Platform-Aware Caption Generator Adapter

This module adapts the existing caption generation logic to work with database-stored
credentials and provides progress callback integration for web-based generation.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/platform_aware_caption_adapter.py`

## Classes

### PlatformAwareCaptionAdapter

```python
class PlatformAwareCaptionAdapter
```

Adapts existing caption generation logic for platform-aware web operations

**Methods:**

#### __init__

```python
def __init__(self, platform_connection: PlatformConnection, config: Config)
```

Initialize the adapter with a platform connection

Args:
    platform_connection: The platform connection to use
    config: Optional config override (uses default if not provided)

**Type:** Instance method

#### initialize

```python
async def initialize(self) -> bool
```

Initialize all components for caption generation

Returns:
    bool: True if initialization was successful

**Type:** Instance method

#### generate_captions_for_user

```python
async def generate_captions_for_user(self, settings: CaptionGenerationSettings, progress_callback: Optional[Callable[[str, int, Dict[str, Any]], None]]) -> GenerationResults
```

Generate captions for the user's posts on the connected platform

Args:
    settings: Caption generation settings
    progress_callback: Optional callback for progress updates
    
Returns:
    GenerationResults: Results of the caption generation process

**Type:** Instance method

#### _process_post

```python
async def _process_post(self, post: Dict[str, Any], settings: CaptionGenerationSettings, progress_callback: Optional[Callable], post_num: int, total_posts: int) -> Dict[str, Any]
```

Process a single post for caption generation

Args:
    post: The post data from ActivityPub
    settings: Caption generation settings
    
Returns:
    Dict with processing results for this post

**Type:** Instance method

#### _process_image

```python
async def _process_image(self, image_info: Dict[str, Any], db_post, settings: CaptionGenerationSettings, progress_callback: Optional[Callable], post_num: int, img_num: int, total_images: int, progress_percent: int) -> Dict[str, Any]
```

Process a single image to generate alt text

Args:
    image_info: Image information from ActivityPub
    db_post: Database post object
    settings: Caption generation settings
    
Returns:
    Dict with image processing results

**Type:** Instance method

#### _cleanup

```python
async def _cleanup(self)
```

Clean up resources

**Type:** Instance method

#### get_platform_info

```python
def get_platform_info(self) -> Dict[str, Any]
```

Get information about the connected platform

Returns:
    Dict with platform information

**Type:** Instance method

#### test_connection

```python
async def test_connection(self) -> Tuple[bool, str]
```

Test the platform connection

Returns:
    Tuple of (success, message)

**Type:** Instance method

