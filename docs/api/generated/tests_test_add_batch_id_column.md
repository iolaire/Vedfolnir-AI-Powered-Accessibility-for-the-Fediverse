# tests.test_add_batch_id_column

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_add_batch_id_column.py`

## Classes

### TestAddBatchIdColumn

```python
class TestAddBatchIdColumn(unittest.TestCase)
```

Test the add_batch_id_column migration script

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up a test database

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up after the test

**Type:** Instance method

#### test_add_batch_id_column

```python
def test_add_batch_id_column(self)
```

Test that the batch_id column is added to the processing_runs table

**Type:** Instance method

#### test_column_already_exists

```python
def test_column_already_exists(self)
```

Test the case where the batch_id column already exists

**Type:** Instance method

#### test_database_not_found

```python
def test_database_not_found(self)
```

Test the case where the database file doesn't exist

**Type:** Instance method

