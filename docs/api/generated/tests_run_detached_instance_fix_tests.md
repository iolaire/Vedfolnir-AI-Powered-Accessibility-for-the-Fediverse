# tests.run_detached_instance_fix_tests

Test Runner for DetachedInstanceError Fix

Comprehensive test runner for all DetachedInstanceError fix tests,
including Flask application context tests with standardized mock user helpers.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/run_detached_instance_fix_tests.py`

## Classes

### DetachedInstanceFixTestRunner

```python
class DetachedInstanceFixTestRunner
```

Test runner for DetachedInstanceError fix tests

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### discover_tests

```python
def discover_tests(self, test_modules: List[str]) -> unittest.TestSuite
```

Discover tests from specified modules

**Type:** Instance method

#### run_test_suite

```python
def run_test_suite(self, suite_name: str, verbosity: int) -> bool
```

Run a specific test suite

**Type:** Instance method

#### run_flask_context_tests

```python
def run_flask_context_tests(self, verbosity: int) -> bool
```

Run all Flask context tests

**Type:** Instance method

#### run_comprehensive_tests

```python
def run_comprehensive_tests(self, verbosity: int) -> bool
```

Run comprehensive test suite

**Type:** Instance method

#### list_available_suites

```python
def list_available_suites(self)
```

List all available test suites

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main test runner function

