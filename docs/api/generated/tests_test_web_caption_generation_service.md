# tests.test_web_caption_generation_service

Unit tests for Web Caption Generation Service

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_web_caption_generation_service.py`

## Classes

### TestWebCaptionGenerationService

```python
class TestWebCaptionGenerationService(unittest.TestCase)
```

Test cases for WebCaptionGenerationService

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_service_initialization

```python
def test_service_initialization(self)
```

Test service initialization

**Type:** Instance method

#### test_start_caption_generation_success

```python
async def test_start_caption_generation_success(self, mock_task_class)
```

Test successful caption generation start

**Decorators:**
- `@patch('web_caption_generation_service.CaptionGenerationTask')`

**Type:** Instance method

#### test_start_caption_generation_validation_failure

```python
async def test_start_caption_generation_validation_failure(self)
```

Test caption generation start with validation failure

**Type:** Instance method

#### test_get_generation_status_success

```python
def test_get_generation_status_success(self)
```

Test successful status retrieval

**Type:** Instance method

#### test_get_generation_status_unauthorized

```python
def test_get_generation_status_unauthorized(self)
```

Test status retrieval with unauthorized user

**Type:** Instance method

#### test_get_generation_status_not_found

```python
def test_get_generation_status_not_found(self)
```

Test status retrieval when task not found

**Type:** Instance method

#### test_cancel_generation_success

```python
def test_cancel_generation_success(self)
```

Test successful task cancellation

**Type:** Instance method

#### test_cancel_generation_failure

```python
def test_cancel_generation_failure(self)
```

Test task cancellation failure

**Type:** Instance method

#### test_get_generation_results_success

```python
async def test_get_generation_results_success(self)
```

Test successful results retrieval

**Type:** Instance method

#### test_get_generation_results_not_completed

```python
async def test_get_generation_results_not_completed(self)
```

Test results retrieval for incomplete task

**Type:** Instance method

#### test_validate_user_platform_access_success

```python
async def test_validate_user_platform_access_success(self)
```

Test successful user platform access validation

**Type:** Instance method

#### test_validate_user_platform_access_user_not_found

```python
async def test_validate_user_platform_access_user_not_found(self)
```

Test validation failure when user not found

**Type:** Instance method

#### test_validate_user_platform_access_platform_not_found

```python
async def test_validate_user_platform_access_platform_not_found(self)
```

Test validation failure when platform not found

**Type:** Instance method

#### test_validate_user_platform_access_active_task_exists

```python
async def test_validate_user_platform_access_active_task_exists(self)
```

Test validation failure when user has active task

**Type:** Instance method

#### test_get_user_settings_custom_settings

```python
async def test_get_user_settings_custom_settings(self)
```

Test getting user's custom settings

**Type:** Instance method

#### test_get_user_settings_default_settings

```python
async def test_get_user_settings_default_settings(self)
```

Test getting default settings when no custom settings exist

**Type:** Instance method

#### test_get_service_stats

```python
def test_get_service_stats(self)
```

Test getting service statistics

**Type:** Instance method

#### test_save_user_settings_new_settings

```python
async def test_save_user_settings_new_settings(self)
```

Test saving new user settings

**Type:** Instance method

#### test_save_user_settings_update_existing

```python
async def test_save_user_settings_update_existing(self)
```

Test updating existing user settings

**Type:** Instance method

#### test_get_user_task_history

```python
async def test_get_user_task_history(self)
```

Test getting user task history

**Type:** Instance method

