# scripts.testing.run_comprehensive_tests

Comprehensive test runner for the Vedfolnir web-integrated caption generation system

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/testing/run_comprehensive_tests.py`

## Constants

- `TEST_SUITES`

## Classes

### TestResult

```python
class TestResult
```

Test result tracking

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

### ComprehensiveTestRunner

```python
class ComprehensiveTestRunner
```

Comprehensive test runner with detailed reporting

**Methods:**

#### __init__

```python
def __init__(self, verbosity)
```

**Type:** Instance method

#### run_test_suite

```python
def run_test_suite(self, suite_name, test_modules)
```

Run a specific test suite

**Type:** Instance method

#### run_all_suites

```python
def run_all_suites(self, selected_suites)
```

Run all or selected test suites

**Type:** Instance method

#### print_summary

```python
def print_summary(self, total_duration)
```

Print comprehensive test summary

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main test runner function

