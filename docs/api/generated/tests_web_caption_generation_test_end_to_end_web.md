# tests.web_caption_generation.test_end_to_end_web

End-to-end tests for web interface functionality

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/web_caption_generation/test_end_to_end_web.py`

## Classes

### TestWebInterfaceEndToEnd

```python
class TestWebInterfaceEndToEnd(unittest.TestCase)
```

End-to-end tests for web interface functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_caption_generation_page_load

```python
def test_caption_generation_page_load(self, mock_service, mock_session_manager)
```

Test caption generation page loads correctly

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

#### test_start_caption_generation_success

```python
def test_start_caption_generation_success(self, mock_service, mock_session_manager)
```

Test successful caption generation start via web interface

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

#### test_start_caption_generation_validation_error

```python
def test_start_caption_generation_validation_error(self, mock_service, mock_session_manager)
```

Test caption generation start with validation error

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

#### test_get_generation_status

```python
def test_get_generation_status(self, mock_service, mock_session_manager)
```

Test getting generation status via API

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

#### test_cancel_generation

```python
def test_cancel_generation(self, mock_service, mock_session_manager)
```

Test cancelling generation via API

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

#### test_get_generation_results

```python
def test_get_generation_results(self, mock_service, mock_session_manager)
```

Test getting generation results via API

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

#### test_save_user_settings

```python
def test_save_user_settings(self, mock_service, mock_session_manager)
```

Test saving user settings via API

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

#### test_unauthorized_access

```python
def test_unauthorized_access(self, mock_session_manager)
```

Test unauthorized access to caption generation endpoints

**Decorators:**
- `@patch('web_app.session_manager')`

**Type:** Instance method

#### test_websocket_connection

```python
def test_websocket_connection(self, mock_service, mock_session_manager)
```

Test WebSocket connection for progress updates

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

#### test_settings_page_functionality

```python
def test_settings_page_functionality(self, mock_service, mock_session_manager)
```

Test caption settings page functionality

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

#### test_task_history_display

```python
def test_task_history_display(self, mock_service, mock_session_manager)
```

Test task history display functionality

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

#### test_error_handling_in_web_interface

```python
def test_error_handling_in_web_interface(self, mock_service, mock_session_manager)
```

Test error handling in web interface

**Decorators:**
- `@patch('web_app.session_manager')`
- `@patch('web_app.web_caption_service')`

**Type:** Instance method

