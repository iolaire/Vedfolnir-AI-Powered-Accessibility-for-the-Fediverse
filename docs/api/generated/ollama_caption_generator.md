# ollama_caption_generator

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/ollama_caption_generator.py`

## Classes

### OllamaCaptionGenerator

```python
class OllamaCaptionGenerator
```

Generate image captions using Ollama with llava:7b model

**Methods:**

#### __init__

```python
def __init__(self, config)
```

**Type:** Instance method

#### initialize

```python
async def initialize(self)
```

Initialize connection to Ollama and validate model availability

**Type:** Instance method

#### _validate_connection

```python
async def _validate_connection(self)
```

Validate connection to Ollama API

**Type:** Instance method

#### _validate_model

```python
async def _validate_model(self)
```

Validate that the specified model is available

**Type:** Instance method

#### cleanup

```python
def cleanup(self)
```

Clean up resources and log statistics

**Type:** Instance method

#### get_fallback_stats

```python
def get_fallback_stats(self) -> Dict[str, Any]
```

Get statistics about fallback attempts

Returns:
    Dictionary with fallback statistics

**Type:** Instance method

#### get_fallback_stats_summary

```python
def get_fallback_stats_summary(self) -> str
```

Get a human-readable summary of fallback statistics

Returns:
    String with fallback statistics summary

**Type:** Instance method

#### generate_caption

```python
async def generate_caption(self, image_path: str, prompt: str) -> Optional[Tuple[str, Dict[str, Any]]]
```

Generate caption for an image using Ollama with retry and fallback logic

**Type:** Instance method

#### _try_generate_caption

```python
async def _try_generate_caption(self, image_path: str, image_data: str, model_name: str, prompt: str) -> Optional[Tuple[str, Dict[str, Any]]]
```

Try to generate a caption with specific model and prompt

Args:
    image_path: Path to the image file
    image_data: Base64-encoded image data
    model_name: Model name to use
    prompt: Prompt to use
    
Returns:
    Tuple of (caption, quality_metrics) or None if failed

**Type:** Instance method

#### _clean_caption

```python
def _clean_caption(self, caption: str) -> str
```

Clean and format the generated caption

**Type:** Instance method

#### generate_multiple_captions

```python
async def generate_multiple_captions(self, image_paths: List[str]) -> List[Tuple[Optional[str], Optional[Dict[str, Any]]]]
```

Generate captions for multiple images

Returns:
    List of tuples containing (caption, quality_metrics) for each image

**Type:** Instance method

#### get_retry_stats

```python
def get_retry_stats(self) -> Dict[str, Any]
```

Get statistics about retry attempts

Returns:
    Dictionary with retry statistics

**Type:** Instance method

#### get_retry_stats_summary

```python
def get_retry_stats_summary(self) -> str
```

Get a human-readable summary of retry statistics

Returns:
    String with retry statistics summary

**Type:** Instance method

#### get_model_info

```python
def get_model_info(self) -> Dict[str, Any]
```

Get information about the current model

Returns:
    Dictionary with model information or None if not available

**Type:** Instance method

#### assess_caption_quality

```python
def assess_caption_quality(self, caption: str, prompt_used: str) -> Dict[str, Any]
```

Assess the quality of a generated caption

Args:
    caption: The caption text to assess
    prompt_used: Optional prompt used to generate the caption
    
Returns:
    Dictionary containing quality metrics and overall score

**Type:** Instance method

