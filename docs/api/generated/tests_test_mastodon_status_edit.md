# tests.test_mastodon_status_edit

Test for Mastodon status edit API functionality.
Tests the fix for "Text can't be blank" error when updating media captions.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_mastodon_status_edit.py`

## Classes

### TestMastodonStatusEdit

```python
class TestMastodonStatusEdit(unittest.TestCase)
```

Test Mastodon status edit functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_update_status_media_caption_success

```python
def test_update_status_media_caption_success(self)
```

Test successful media caption update with original text preserved

**Type:** Instance method

#### test_update_status_media_caption_html_stripping

```python
def test_update_status_media_caption_html_stripping(self)
```

Test that HTML tags are stripped from status text

**Type:** Instance method

#### test_update_status_media_caption_missing_params

```python
def test_update_status_media_caption_missing_params(self)
```

Test failure when required parameters are missing

**Type:** Instance method

#### test_update_status_media_caption_get_status_fails

```python
def test_update_status_media_caption_get_status_fails(self)
```

Test failure when getting current status fails

**Type:** Instance method

#### test_update_status_media_caption_put_fails

```python
def test_update_status_media_caption_put_fails(self)
```

Test failure when PUT request fails

**Type:** Instance method

#### test_update_status_media_caption_auth_required

```python
def test_update_status_media_caption_auth_required(self)
```

Test that authentication is required

**Type:** Instance method

