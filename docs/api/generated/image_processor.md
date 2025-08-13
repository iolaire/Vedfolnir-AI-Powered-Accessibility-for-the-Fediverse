# image_processor

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/image_processor.py`

## Classes

### ImageProcessor

```python
class ImageProcessor
```

Handle image downloading and processing with persistent storage

**Methods:**

#### __init__

```python
def __init__(self, config: Config)
```

**Type:** Instance method

#### __aenter__

```python
async def __aenter__(self)
```

**Type:** Instance method

#### __aexit__

```python
async def __aexit__(self, exc_type, exc_val, exc_tb)
```

**Type:** Instance method

#### _get_image_filename

```python
def _get_image_filename(self, url: str, media_type: str) -> str
```

Generate consistent filename for image URL

**Type:** Instance method

#### validate_image

```python
def validate_image(self, image_path: str) -> Tuple[bool, str]
```

Validate an image file to ensure it's a valid image and meets requirements

Args:
    image_path: Path to the image file
    
Returns:
    Tuple of (is_valid, error_message)

**Type:** Instance method

#### download_and_store_image

```python
async def download_and_store_image(self, url: str, media_type: str) -> Optional[str]
```

Download image and store it permanently

**Type:** Instance method

#### _optimize_image

```python
def _optimize_image(self, image_path: str) -> str
```

Optimize image for storage and processing

**Type:** Instance method

#### get_image_info

```python
def get_image_info(self, image_path: str) -> dict
```

Get image information

**Type:** Instance method

#### close

```python
async def close(self)
```

Close the HTTP session

**Type:** Instance method

