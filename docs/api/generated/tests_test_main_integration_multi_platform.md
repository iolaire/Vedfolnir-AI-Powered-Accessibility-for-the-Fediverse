# tests.test_main_integration_multi_platform

Integration test to verify that the main application works with the refactored ActivityPub client.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_main_integration_multi_platform.py`

## Classes

### MockConfig

```python
class MockConfig
```

Mock configuration for testing

**Decorators:**
- `@dataclass`

**Methods:**

#### __post_init__

```python
def __post_init__(self)
```

**Type:** Instance method

### TestMainApplicationIntegration

```python
class TestMainApplicationIntegration(unittest.TestCase)
```

Test integration with main application workflow

**Methods:**

#### test_pixelfed_main_workflow

```python
async def test_pixelfed_main_workflow(self)
```

Test main application workflow with Pixelfed

**Type:** Instance method

#### test_mastodon_main_workflow

```python
async def test_mastodon_main_workflow(self)
```

Test main application workflow with Mastodon

**Type:** Instance method

#### test_platform_agnostic_error_handling

```python
async def test_platform_agnostic_error_handling(self)
```

Test that error handling works consistently across platforms

**Type:** Instance method

#### test_platform_info_consistency

```python
def test_platform_info_consistency(self)
```

Test that platform info is consistent across platforms

**Type:** Instance method

#### test_pixelfed_main_workflow_sync

```python
def test_pixelfed_main_workflow_sync(self)
```

Sync wrapper for async test

**Type:** Instance method

#### test_mastodon_main_workflow_sync

```python
def test_mastodon_main_workflow_sync(self)
```

Sync wrapper for async test

**Type:** Instance method

#### test_platform_agnostic_error_handling_sync

```python
def test_platform_agnostic_error_handling_sync(self)
```

Sync wrapper for async test

**Type:** Instance method

