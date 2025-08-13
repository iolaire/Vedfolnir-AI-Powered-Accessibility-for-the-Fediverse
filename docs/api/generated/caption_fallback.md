# caption_fallback

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/caption_fallback.py`

## Classes

### FallbackConfig

```python
class FallbackConfig
```

Configuration for caption generation fallback mechanisms

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create a FallbackConfig from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

### CaptionFallbackManager

```python
class CaptionFallbackManager
```

Manages fallback mechanisms for caption generation

This class provides fallback strategies when the primary caption generation fails:
1. Retry with the same model but a simplified prompt
2. Try with a backup model if available

**Class Variables:**
- `ULTRA_SIMPLIFIED_PROMPT`

**Methods:**

#### __init__

```python
def __init__(self, config: FallbackConfig, caption_config)
```

Initialize the fallback manager

Args:
    config: Optional fallback configuration
    caption_config: Optional caption configuration for max length

**Type:** Instance method

#### get_fallback_prompt

```python
def get_fallback_prompt(self, original_category: str, fallback_attempt: int) -> str
```

Get a fallback prompt based on the original category and attempt number

Args:
    original_category: The original image category
    fallback_attempt: The current fallback attempt number (1-based)
    
Returns:
    A simplified prompt for fallback

**Type:** Instance method

#### get_fallback_model

```python
def get_fallback_model(self, original_model: str, fallback_attempt: int) -> Optional[str]
```

Get a fallback model based on the original model and attempt number

Args:
    original_model: The original model name
    fallback_attempt: The current fallback attempt number (1-based)
    
Returns:
    A backup model name or None if no backup should be used

**Type:** Instance method

#### _map_to_simplified_category

```python
def _map_to_simplified_category(self, category: str) -> str
```

Map a specific category to a more general simplified category

Args:
    category: The original category
    
Returns:
    A simplified category

**Type:** Instance method

#### should_use_fallback

```python
def should_use_fallback(self, error: Exception, quality_metrics: Dict[str, Any]) -> bool
```

Determine if fallback mechanisms should be used

Args:
    error: Optional exception that occurred during caption generation
    quality_metrics: Optional quality metrics for a generated caption
    
Returns:
    True if fallback should be used

**Type:** Instance method

