# test_coverage_analysis

Comprehensive Test Coverage Analysis

Analyzes the current test coverage and identifies gaps.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/test_coverage_analysis.py`

## Classes

### TestCoverageAnalyzer

```python
class TestCoverageAnalyzer
```

Analyzes test coverage across the project

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### analyze_coverage

```python
def analyze_coverage(self) -> Dict
```

Run comprehensive coverage analysis

**Type:** Instance method

#### _discover_files

```python
def _discover_files(self)
```

Discover all Python source and test files

**Type:** Instance method

#### _analyze_source_files

```python
def _analyze_source_files(self)
```

Analyze source files to identify functions and classes

**Type:** Instance method

#### _analyze_test_files

```python
def _analyze_test_files(self)
```

Analyze test files to identify test methods

**Type:** Instance method

#### _identify_coverage_gaps

```python
def _identify_coverage_gaps(self)
```

Identify modules without test coverage

**Type:** Instance method

#### _generate_recommendations

```python
def _generate_recommendations(self)
```

Generate recommendations for improving test coverage

**Type:** Instance method

#### generate_report

```python
def generate_report(self) -> str
```

Generate a comprehensive coverage report

**Type:** Instance method

## Functions

### main

```python
def main()
```

Run test coverage analysis

