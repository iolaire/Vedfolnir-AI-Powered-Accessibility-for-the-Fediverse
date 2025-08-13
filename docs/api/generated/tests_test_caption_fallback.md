# tests.test_caption_fallback

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_caption_fallback.py`

## Classes

### TestCaptionFallback

```python
class TestCaptionFallback(unittest.TestCase)
```

Test the caption fallback mechanisms

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_fallback_config_from_env

```python
def test_fallback_config_from_env(self)
```

Test creating fallback config from environment variables

**Type:** Instance method

#### test_get_fallback_prompt

```python
def test_get_fallback_prompt(self)
```

Test getting fallback prompts

**Type:** Instance method

#### test_get_fallback_model

```python
def test_get_fallback_model(self)
```

Test getting fallback models

**Type:** Instance method

#### test_should_use_fallback

```python
def test_should_use_fallback(self)
```

Test determining if fallback should be used

**Type:** Instance method

#### test_map_to_simplified_category

```python
def test_map_to_simplified_category(self)
```

Test mapping specific categories to simplified categories

**Type:** Instance method

### TestOllamaCaptionGeneratorFallback

```python
class TestOllamaCaptionGeneratorFallback(unittest.TestCase)
```

Test the fallback mechanisms in OllamaCaptionGenerator

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_generate_caption_with_fallback

```python
def test_generate_caption_with_fallback(self)
```

Test generate_caption with fallback mechanisms

**Type:** Instance method

#### test_generate_caption_with_low_quality

```python
def test_generate_caption_with_low_quality(self)
```

Test generate_caption with low quality initial result

**Type:** Instance method

#### test_generate_caption_all_fallbacks_fail

```python
def test_generate_caption_all_fallbacks_fail(self)
```

Test generate_caption when all fallbacks fail

**Type:** Instance method

