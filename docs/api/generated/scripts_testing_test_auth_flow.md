# scripts.testing.test_auth_flow

Test script for Task 4.2: Update Authentication Flow

This script tests the updated authentication flow including:
- Login with platform context setup
- First-time user setup
- Platform access validation
- User profile functionality
- Session management

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/testing/test_auth_flow.py`

## Classes

### AuthFlowTester

```python
class AuthFlowTester
```

Test the updated authentication flow

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### test_user_creation

```python
def test_user_creation(self)
```

Test creating users with different scenarios

**Type:** Instance method

#### test_platform_creation

```python
def test_platform_creation(self, user_id)
```

Test creating platform connections

**Type:** Instance method

#### test_session_management

```python
def test_session_management(self, user_id, platform_ids)
```

Test session management functionality

**Type:** Instance method

#### test_platform_access_validation

```python
def test_platform_access_validation(self, user_id, platform_ids)
```

Test platform access validation

**Type:** Instance method

#### test_database_platform_stats

```python
def test_database_platform_stats(self, platform_ids)
```

Test platform-specific database statistics

**Type:** Instance method

#### cleanup_test_data

```python
def cleanup_test_data(self, user_id)
```

Clean up test data

**Type:** Instance method

#### run_all_tests

```python
def run_all_tests(self)
```

Run all authentication flow tests

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main test function

