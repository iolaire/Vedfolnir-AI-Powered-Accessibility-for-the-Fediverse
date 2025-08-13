# tests.test_activitypub_platforms

Tests for the ActivityPub platform adapters

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_activitypub_platforms.py`

## Classes

### TestActivityPubPlatforms

```python
class TestActivityPubPlatforms(unittest.TestCase)
```

Test cases for ActivityPub platform adapters

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_platform_detection_pixelfed

```python
def test_platform_detection_pixelfed(self)
```

Test detection of Pixelfed platforms

**Type:** Instance method

#### test_platform_detection_mastodon

```python
def test_platform_detection_mastodon(self)
```

Test detection of Mastodon platforms

**Type:** Instance method

#### test_platform_detection_pleroma

```python
def test_platform_detection_pleroma(self)
```

Test detection of Pleroma platforms

**Type:** Instance method

#### test_get_platform_adapter_explicit

```python
def test_get_platform_adapter_explicit(self)
```

Test getting platform adapter with explicit platform type

**Type:** Instance method

#### test_get_platform_adapter_auto_detect

```python
def test_get_platform_adapter_auto_detect(self)
```

Test getting platform adapter with auto-detection

**Type:** Instance method

#### test_legacy_is_pixelfed_flag

```python
def test_legacy_is_pixelfed_flag(self)
```

Test that the legacy is_pixelfed flag works

**Type:** Instance method

#### test_platform_detection_fallback

```python
def test_platform_detection_fallback(self)
```

Test platform detection fallback methods

**Type:** Instance method

