# migrations.platform_aware_migration

Platform-Aware Database Migration

This module provides comprehensive migration functionality to upgrade existing
Vedfolnir databases to support platform-aware operations with user-managed
platform connections.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/migrations/platform_aware_migration.py`

## Classes

### PlatformAwareMigration

```python
class PlatformAwareMigration
```

Handles migration of existing Vedfolnir database to platform-aware schema.

This migration:
1. Creates new platform-aware tables (platform_connections, user_sessions)
2. Adds platform identification columns to existing tables
3. Creates a default platform connection from environment configuration
4. Migrates existing data to use the default platform connection
5. Creates performance indexes for platform-based queries
6. Validates data integrity after migration
7. Provides rollback functionality

**Methods:**

#### __init__

```python
def __init__(self, database_url: str, config: Optional[Dict])
```

Initialize migration with database connection and configuration.

Args:
    database_url: SQLAlchemy database URL
    config: Optional configuration dictionary with platform settings

**Type:** Instance method

#### __enter__

```python
def __enter__(self)
```

Context manager entry

**Type:** Instance method

#### __exit__

```python
def __exit__(self, exc_type, exc_val, exc_tb)
```

Context manager exit - cleanup session

**Type:** Instance method

#### check_migration_needed

```python
def check_migration_needed(self) -> bool
```

Check if migration is needed by inspecting database schema.

Returns:
    True if migration is needed, False if already migrated

**Type:** Instance method

#### validate_environment_config

```python
def validate_environment_config(self) -> Dict
```

Validate and extract platform configuration from environment.

Returns:
    Dictionary with validated platform configuration
    
Raises:
    ValueError: If required configuration is missing

**Type:** Instance method

#### create_backup_tables

```python
def create_backup_tables(self) -> None
```

Create backup tables for rollback functionality

**Type:** Instance method

#### create_platform_tables

```python
def create_platform_tables(self) -> None
```

Create new platform-aware tables

**Type:** Instance method

#### add_platform_columns_to_existing_tables

```python
def add_platform_columns_to_existing_tables(self) -> None
```

Add platform identification columns to existing tables

**Type:** Instance method

#### create_default_platform_connection

```python
def create_default_platform_connection(self, config: Dict) -> int
```

Create default platform connection from environment configuration.

Args:
    config: Platform configuration dictionary
    
Returns:
    ID of created platform connection

**Type:** Instance method

#### migrate_existing_data

```python
def migrate_existing_data(self, default_platform_id: int) -> None
```

Migrate existing data to use the default platform connection.

Args:
    default_platform_id: ID of the default platform connection

**Type:** Instance method

#### create_performance_indexes

```python
def create_performance_indexes(self) -> None
```

Create indexes for efficient platform-based queries

**Type:** Instance method

#### validate_data_integrity

```python
def validate_data_integrity(self) -> List[str]
```

Validate data integrity after migration.

Returns:
    List of validation errors (empty if all validations pass)

**Type:** Instance method

#### migrate_up

```python
def migrate_up(self) -> bool
```

Execute the complete migration to platform-aware schema.

Returns:
    True if migration successful, False otherwise

**Type:** Instance method

#### migrate_down

```python
def migrate_down(self) -> bool
```

Rollback the migration to previous state.

Returns:
    True if rollback successful, False otherwise

**Type:** Instance method

#### cleanup_backup_tables

```python
def cleanup_backup_tables(self) -> None
```

Clean up backup tables after successful migration

**Type:** Instance method

#### get_migration_status

```python
def get_migration_status(self) -> Dict
```

Get current migration status and statistics.

Returns:
    Dictionary with migration status information

**Type:** Instance method

