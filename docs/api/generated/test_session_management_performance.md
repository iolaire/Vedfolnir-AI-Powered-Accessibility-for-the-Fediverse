# test_session_management_performance

Session Management Performance Test

This script tests the performance improvements from the session management
optimization migration by running common queries and measuring execution time.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/test_session_management_performance.py`

## Classes

### SessionManagementPerformanceTest

```python
class SessionManagementPerformanceTest
```

Test performance of session management queries

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### time_query

```python
def time_query(self, query, description, params)
```

Time a query execution

**Type:** Instance method

#### test_user_queries

```python
def test_user_queries(self)
```

Test user-related queries that benefit from new indexes

**Type:** Instance method

#### test_platform_connection_queries

```python
def test_platform_connection_queries(self)
```

Test platform connection queries that benefit from new indexes

**Type:** Instance method

#### test_session_queries

```python
def test_session_queries(self)
```

Test user session queries that benefit from new indexes

**Type:** Instance method

#### test_relationship_queries

```python
def test_relationship_queries(self)
```

Test queries involving relationships that benefit from new indexes

**Type:** Instance method

#### test_explain_query_plans

```python
def test_explain_query_plans(self)
```

Test query plans to verify index usage

**Type:** Instance method

#### run_all_tests

```python
def run_all_tests(self)
```

Run all performance tests

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main function to run performance tests

