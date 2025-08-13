# tests.test_multi_user

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_multi_user.py`

## Classes

### TestMultiUserProcessing

```python
class TestMultiUserProcessing(unittest.TestCase)
```

Test cases for multi-user processing feature

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_create_processing_run_with_batch_id

```python
def test_create_processing_run_with_batch_id(self)
```

Test creating a processing run with a batch ID

**Type:** Instance method

### TestMultiUserProcessingAsync

```python
class TestMultiUserProcessingAsync(unittest.TestCase)
```

Async test cases for multi-user processing feature

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_run_multi_user

```python
async def test_run_multi_user(self)
```

Test running the bot with multiple users

**Decorators:**
- `@async_test`

**Type:** Instance method

#### test_max_users_limit

```python
async def test_max_users_limit(self)
```

Test that the max users per run limit is enforced

**Decorators:**
- `@async_test`

**Type:** Instance method

## Functions

### async_test

```python
def async_test(coro)
```

