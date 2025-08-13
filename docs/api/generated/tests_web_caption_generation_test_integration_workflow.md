# tests.web_caption_generation.test_integration_workflow

Integration tests for complete caption generation workflow

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/web_caption_generation/test_integration_workflow.py`

## Classes

### TestCaptionGenerationWorkflow

```python
class TestCaptionGenerationWorkflow(unittest.TestCase)
```

Integration tests for complete caption generation workflow

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_complete_generation_workflow

```python
async def test_complete_generation_workflow(self, mock_adapter_class)
```

Test complete caption generation workflow from start to finish

**Decorators:**
- `@patch('web_caption_generation_service.PlatformAwareCaptionAdapter')`

**Type:** Instance method

#### test_service_statistics_workflow

```python
def test_service_statistics_workflow(self)
```

Test service statistics retrieval

**Type:** Instance method

