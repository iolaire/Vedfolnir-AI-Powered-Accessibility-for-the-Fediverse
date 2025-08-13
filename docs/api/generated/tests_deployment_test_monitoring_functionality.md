# tests.deployment.test_monitoring_functionality

Functional tests for monitoring and health check systems

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/deployment/test_monitoring_functionality.py`

## Classes

### TestHealthMonitoringFunctionality

```python
class TestHealthMonitoringFunctionality(unittest.TestCase)
```

Test health monitoring functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

**Type:** Instance method

#### test_platform_connection_check

```python
def test_platform_connection_check(self, mock_get)
```

Test platform connection health check

**Decorators:**
- `@patch('requests.get')`

**Type:** Instance method

#### test_platform_connection_failure

```python
def test_platform_connection_failure(self, mock_get)
```

Test platform connection failure detection

**Decorators:**
- `@patch('requests.get')`

**Type:** Instance method

#### test_database_health_check

```python
def test_database_health_check(self)
```

Test database health check functionality

**Type:** Instance method

#### test_system_resource_check

```python
def test_system_resource_check(self)
```

Test system resource monitoring

**Type:** Instance method

### TestBackupFunctionality

```python
class TestBackupFunctionality(unittest.TestCase)
```

Test backup tool functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

**Type:** Instance method

#### test_backup_script_help

```python
def test_backup_script_help(self)
```

Test backup script shows help

**Type:** Instance method

#### test_backup_dry_run_mode

```python
def test_backup_dry_run_mode(self, mock_exists, mock_copy)
```

Test backup dry run functionality

**Decorators:**
- `@patch('shutil.copy2')`
- `@patch('os.path.exists')`

**Type:** Instance method

### TestValidationFunctionality

```python
class TestValidationFunctionality(unittest.TestCase)
```

Test configuration validation functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

**Type:** Instance method

#### test_validator_detects_missing_config

```python
def test_validator_detects_missing_config(self)
```

Test validator detects missing configuration

**Type:** Instance method

#### test_validator_with_valid_config

```python
def test_validator_with_valid_config(self)
```

Test validator with valid configuration

**Decorators:**
- `@patch.dict(os.environ, {'ACTIVITYPUB_API_TYPE': 'mastodon', 'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.social', 'ACTIVITYPUB_USERNAME': 'testuser', 'ACTIVITYPUB_ACCESS_TOKEN': 'test_token', 'MASTODON_CLIENT_KEY': 'test_key', 'MASTODON_CLIENT_SECRET': 'test_secret'})`

**Type:** Instance method

### TestRollbackFunctionality

```python
class TestRollbackFunctionality(unittest.TestCase)
```

Test rollback tool functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

**Type:** Instance method

#### test_rollback_script_help

```python
def test_rollback_script_help(self)
```

Test rollback script shows help

**Type:** Instance method

#### test_rollback_dry_run_mode

```python
def test_rollback_dry_run_mode(self)
```

Test rollback dry run functionality

**Type:** Instance method

