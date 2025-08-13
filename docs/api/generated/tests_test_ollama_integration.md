# tests.test_ollama_integration

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_ollama_integration.py`

## Classes

### TestOllamaIntegration

```python
class TestOllamaIntegration(unittest.TestCase)
```

Test cases for Ollama integration

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_initialize_success

```python
async def test_initialize_success(self, mock_post, mock_get)
```

Test successful initialization of Ollama caption generator

**Decorators:**
- `@patch('httpx.AsyncClient.get')`
- `@patch('httpx.AsyncClient.post')`

**Type:** Instance method

#### test_initialize_connection_error

```python
async def test_initialize_connection_error(self, mock_get)
```

Test initialization with connection error

**Decorators:**
- `@patch('httpx.AsyncClient.get')`

**Type:** Instance method

#### test_generate_caption_success

```python
async def test_generate_caption_success(self, mock_post)
```

Test successful caption generation

**Decorators:**
- `@patch('httpx.AsyncClient.post')`

**Type:** Instance method

#### test_generate_caption_with_retry

```python
async def test_generate_caption_with_retry(self, mock_post)
```

Test caption generation with retry

**Decorators:**
- `@patch('httpx.AsyncClient.post')`

**Type:** Instance method

#### test_generate_caption_max_retries_exceeded

```python
async def test_generate_caption_max_retries_exceeded(self, mock_post)
```

Test caption generation with max retries exceeded

**Decorators:**
- `@patch('httpx.AsyncClient.post')`

**Type:** Instance method

#### test_get_retry_stats_summary

```python
def test_get_retry_stats_summary(self)
```

Test getting retry stats summary

**Type:** Instance method

## Functions

### run_tests

```python
def run_tests()
```

Run the tests

