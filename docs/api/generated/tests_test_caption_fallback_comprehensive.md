# tests.test_caption_fallback_comprehensive

Comprehensive tests for caption generation fallback mechanisms.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_caption_fallback_comprehensive.py`

## Classes

### TestFallbackConfig

```python
class TestFallbackConfig(unittest.TestCase)
```

Test FallbackConfig functionality

**Methods:**

#### test_default_config

```python
def test_default_config(self)
```

Test default fallback configuration

**Type:** Instance method

#### test_custom_config

```python
def test_custom_config(self)
```

Test custom fallback configuration

**Type:** Instance method

#### test_config_from_env

```python
def test_config_from_env(self)
```

Test creating config from environment variables

**Type:** Instance method

### TestCaptionFallbackManager

```python
class TestCaptionFallbackManager(unittest.TestCase)
```

Test CaptionFallbackManager functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_manager_initialization

```python
def test_manager_initialization(self)
```

Test fallback manager initialization

**Type:** Instance method

#### test_get_fallback_prompt_first_attempt

```python
def test_get_fallback_prompt_first_attempt(self)
```

Test getting fallback prompt for first attempt

**Type:** Instance method

#### test_get_fallback_prompt_final_attempt

```python
def test_get_fallback_prompt_final_attempt(self)
```

Test getting fallback prompt for final attempt

**Type:** Instance method

#### test_get_fallback_prompt_disabled

```python
def test_get_fallback_prompt_disabled(self)
```

Test getting fallback prompt when simplified prompts are disabled

**Type:** Instance method

#### test_get_fallback_model_first_attempt

```python
def test_get_fallback_model_first_attempt(self)
```

Test getting fallback model for first attempt

**Type:** Instance method

#### test_get_fallback_model_second_attempt

```python
def test_get_fallback_model_second_attempt(self)
```

Test getting fallback model for second attempt

**Type:** Instance method

#### test_get_fallback_model_same_as_original

```python
def test_get_fallback_model_same_as_original(self)
```

Test getting fallback model when backup is same as original

**Type:** Instance method

#### test_get_fallback_model_disabled

```python
def test_get_fallback_model_disabled(self)
```

Test getting fallback model when backup model is disabled

**Type:** Instance method

#### test_map_to_simplified_category

```python
def test_map_to_simplified_category(self)
```

Test mapping specific categories to simplified categories

**Type:** Instance method

#### test_should_use_fallback_with_error

```python
def test_should_use_fallback_with_error(self)
```

Test should_use_fallback with error

**Type:** Instance method

#### test_should_use_fallback_with_poor_quality

```python
def test_should_use_fallback_with_poor_quality(self)
```

Test should_use_fallback with poor quality metrics

**Type:** Instance method

#### test_should_use_fallback_with_good_quality

```python
def test_should_use_fallback_with_good_quality(self)
```

Test should_use_fallback with good quality metrics

**Type:** Instance method

#### test_should_use_fallback_disabled

```python
def test_should_use_fallback_disabled(self)
```

Test should_use_fallback when fallback is disabled

**Type:** Instance method

### TestOllamaCaptionGeneratorFallback

```python
class TestOllamaCaptionGeneratorFallback(unittest.IsolatedAsyncioTestCase)
```

Test fallback mechanisms in OllamaCaptionGenerator

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_generate_caption_primary_success

```python
async def test_generate_caption_primary_success(self)
```

Test generate_caption when primary attempt succeeds

**Type:** Instance method

#### test_generate_caption_fallback_after_failure

```python
async def test_generate_caption_fallback_after_failure(self)
```

Test generate_caption with fallback after primary failure

**Type:** Instance method

#### test_generate_caption_fallback_after_poor_quality

```python
async def test_generate_caption_fallback_after_poor_quality(self)
```

Test generate_caption with fallback after poor quality result

**Type:** Instance method

#### test_generate_caption_multiple_fallbacks

```python
async def test_generate_caption_multiple_fallbacks(self)
```

Test generate_caption with multiple fallback attempts

**Type:** Instance method

#### test_generate_caption_all_fallbacks_fail

```python
async def test_generate_caption_all_fallbacks_fail(self)
```

Test generate_caption when all fallbacks fail

**Type:** Instance method

#### test_generate_caption_with_different_prompts

```python
async def test_generate_caption_with_different_prompts(self)
```

Test that fallback uses different prompts

**Type:** Instance method

#### test_generate_caption_with_backup_model

```python
async def test_generate_caption_with_backup_model(self)
```

Test that fallback uses backup model when configured

**Type:** Instance method

