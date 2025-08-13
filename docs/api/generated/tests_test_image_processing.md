# tests.test_image_processing

Test script for image processing functionality.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_image_processing.py`

## Classes

### TestImageProcessing

```python
class TestImageProcessing(unittest.TestCase)
```

Test cases for image processing functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up after the test

**Type:** Instance method

#### create_test_image

```python
def create_test_image(self, path, format_name)
```

Create a test image file

**Type:** Instance method

#### test_image_validation_valid

```python
def test_image_validation_valid(self)
```

Test image validation with valid images

**Type:** Instance method

#### test_image_validation_corrupted

```python
def test_image_validation_corrupted(self)
```

Test image validation with corrupted image

**Type:** Instance method

#### test_image_validation_size_limits

```python
def test_image_validation_size_limits(self)
```

Test image validation with size limits

**Type:** Instance method

#### test_get_file_extension

```python
def test_get_file_extension(self)
```

Test getting file extension from URL and content type

**Type:** Instance method

#### test_download_and_store_image

```python
async def test_download_and_store_image(self, mock_aiofiles_open)
```

Test downloading and storing an image

**Decorators:**
- `@patch('aiofiles.open', new_callable=AsyncMock)`

**Type:** Instance method

#### test_download_error_handling

```python
async def test_download_error_handling(self, mock_aiofiles_open)
```

Test error handling during download

**Decorators:**
- `@patch('aiofiles.open', new_callable=AsyncMock)`

**Type:** Instance method

#### test_download_non_success_status

```python
async def test_download_non_success_status(self, mock_aiofiles_open)
```

Test handling of non-success HTTP status

**Decorators:**
- `@patch('aiofiles.open', new_callable=AsyncMock)`

**Type:** Instance method

### TestImageProcessingAsync

```python
class TestImageProcessingAsync(unittest.TestCase)
```

Async test cases for image processing functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up after the test

**Type:** Instance method

#### create_test_image

```python
def create_test_image(self, path, format_name)
```

Create a test image file

**Type:** Instance method

#### test_async_context_manager

```python
async def test_async_context_manager(self)
```

Test the async context manager functionality

**Decorators:**
- `@async_test`

**Type:** Instance method

## Functions

### async_test

```python
def async_test(coro)
```

