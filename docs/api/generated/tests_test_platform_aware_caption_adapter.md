# tests.test_platform_aware_caption_adapter

Unit tests for Platform-Aware Caption Generator Adapter

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_platform_aware_caption_adapter.py`

## Classes

### TestPlatformAwareCaptionAdapter

```python
class TestPlatformAwareCaptionAdapter(unittest.TestCase)
```

Test cases for PlatformAwareCaptionAdapter

**Methods:**

#### setUp

```python
def setUp(self, mock_db_manager_class)
```

Set up test fixtures

**Decorators:**
- `@patch('platform_aware_caption_adapter.DatabaseManager')`

**Type:** Instance method

#### test_initialize_success

```python
async def test_initialize_success(self, mock_caption_gen, mock_image_proc, mock_ap_client)
```

Test successful initialization

**Decorators:**
- `@patch('platform_aware_caption_adapter.ActivityPubClient')`
- `@patch('platform_aware_caption_adapter.ImageProcessor')`
- `@patch('platform_aware_caption_adapter.OllamaCaptionGenerator')`

**Type:** Instance method

#### test_initialize_config_failure

```python
async def test_initialize_config_failure(self)
```

Test initialization failure when config creation fails

**Type:** Instance method

#### test_generate_captions_for_user_success

```python
async def test_generate_captions_for_user_success(self, mock_caption_gen, mock_image_proc, mock_ap_client)
```

Test successful caption generation

**Decorators:**
- `@patch('platform_aware_caption_adapter.ActivityPubClient')`
- `@patch('platform_aware_caption_adapter.ImageProcessor')`
- `@patch('platform_aware_caption_adapter.OllamaCaptionGenerator')`

**Type:** Instance method

#### test_generate_captions_no_posts

```python
async def test_generate_captions_no_posts(self, mock_caption_gen, mock_image_proc, mock_ap_client)
```

Test caption generation when no posts are found

**Decorators:**
- `@patch('platform_aware_caption_adapter.ActivityPubClient')`
- `@patch('platform_aware_caption_adapter.ImageProcessor')`
- `@patch('platform_aware_caption_adapter.OllamaCaptionGenerator')`

**Type:** Instance method

#### test_process_post_success

```python
async def test_process_post_success(self)
```

Test successful post processing

**Type:** Instance method

#### test_process_post_no_images

```python
async def test_process_post_no_images(self)
```

Test post processing when no images are found

**Type:** Instance method

#### test_process_image_success

```python
async def test_process_image_success(self)
```

Test successful image processing

**Type:** Instance method

#### test_process_image_already_processed

```python
async def test_process_image_already_processed(self)
```

Test image processing when image is already processed

**Type:** Instance method

#### test_process_image_reprocess_existing

```python
async def test_process_image_reprocess_existing(self)
```

Test image processing with reprocess_existing enabled

**Type:** Instance method

#### test_cleanup

```python
async def test_cleanup(self)
```

Test resource cleanup

**Type:** Instance method

#### test_get_platform_info

```python
def test_get_platform_info(self)
```

Test getting platform information

**Type:** Instance method

#### test_test_connection_success

```python
async def test_test_connection_success(self, mock_caption_gen, mock_image_proc, mock_ap_client)
```

Test successful connection test

**Decorators:**
- `@patch('platform_aware_caption_adapter.ActivityPubClient')`
- `@patch('platform_aware_caption_adapter.ImageProcessor')`
- `@patch('platform_aware_caption_adapter.OllamaCaptionGenerator')`

**Type:** Instance method

#### test_test_connection_init_failure

```python
async def test_test_connection_init_failure(self)
```

Test connection test when initialization fails

**Type:** Instance method

