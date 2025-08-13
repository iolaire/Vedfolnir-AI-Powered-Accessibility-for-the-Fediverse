# tests.performance.test_platform_queries

Performance tests for platform-filtered queries

Tests query performance with platform filtering.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/performance/test_platform_queries.py`

## Classes

### TestPlatformQueryPerformance

```python
class TestPlatformQueryPerformance(PlatformTestCase)
```

Test performance of platform-filtered queries

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up performance test data

**Type:** Instance method

#### _create_performance_data

```python
def _create_performance_data(self)
```

Create test data for performance testing

**Type:** Instance method

#### test_platform_post_query_performance

```python
def test_platform_post_query_performance(self)
```

Test performance of platform-filtered post queries

**Type:** Instance method

#### test_platform_image_query_performance

```python
def test_platform_image_query_performance(self)
```

Test performance of platform-filtered image queries

**Type:** Instance method

#### test_complex_platform_query_performance

```python
def test_complex_platform_query_performance(self)
```

Test performance of complex platform-filtered queries

**Type:** Instance method

#### test_platform_statistics_query_performance

```python
def test_platform_statistics_query_performance(self)
```

Test performance of platform statistics queries

**Type:** Instance method

### TestQueryOptimization

```python
class TestQueryOptimization(PlatformTestCase)
```

Test query optimization for platform operations

**Methods:**

#### test_platform_index_effectiveness

```python
def test_platform_index_effectiveness(self)
```

Test that platform indexes improve query performance

**Type:** Instance method

#### test_bulk_query_performance

```python
def test_bulk_query_performance(self)
```

Test performance of bulk platform queries

**Type:** Instance method

#### test_pagination_performance

```python
def test_pagination_performance(self)
```

Test performance of paginated platform queries

**Type:** Instance method

### TestConcurrentQueryPerformance

```python
class TestConcurrentQueryPerformance(PlatformTestCase)
```

Test performance under concurrent query load

**Methods:**

#### test_concurrent_platform_queries

```python
def test_concurrent_platform_queries(self)
```

Test performance with concurrent platform queries

**Type:** Instance method

#### test_high_frequency_context_switching

```python
def test_high_frequency_context_switching(self)
```

Test performance with high-frequency context switching

**Type:** Instance method

