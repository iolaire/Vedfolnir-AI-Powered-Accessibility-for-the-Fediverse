# Design Document: Complete SQLite to MySQL Migration

## Architecture Overview

This design outlines the complete migration from SQLite to MySQL for the Vedfolnir application, removing all SQLite dependencies and establishing MySQL as the sole database backend.

## Current Architecture Analysis

### Existing Components
- **DatabaseManager**: Supports both SQLite and MySQL with conditional configuration
- **Config System**: Defaults to SQLite but supports MySQL via environment variables
- **Models**: SQLAlchemy models compatible with both databases
- **Migration Scripts**: Partial MySQL migration infrastructure exists

### Dependencies to Remove
- SQLite-specific connection pooling logic
- SQLite file path configurations
- SQLite-specific query optimizations
- SQLite test fixtures and configurations

## Technical Design

### 1. Database Configuration Refactoring

#### Current State
```python
# config.py - Current default
database_url: str = "sqlite:///storage/database/vedfolnir.db"

# database.py - Current conditional logic
if 'sqlite' in config.storage.database_url:
    # SQLite configuration
elif 'mysql' in config.storage.database_url:
    # MySQL configuration
```

#### Target State
```python
# config.py - New MySQL default
database_url: str = "mysql+pymysql://user:password@localhost/vedfolnir?charset=utf8mb4"

# database.py - MySQL-only configuration
class DatabaseManager:
    def __init__(self, config: Config):
        # MySQL-specific engine configuration only
        engine_kwargs = {
            'poolclass': QueuePool,
            'pool_size': db_config.pool_size,
            'max_overflow': db_config.max_overflow,
            'pool_timeout': db_config.pool_timeout,
            'connect_args': {
                'charset': 'utf8mb4',
                'use_unicode': True,
                'autocommit': False,
            }
        }
```

### 2. Code Cleanup Strategy

#### Files Requiring Major Refactoring
1. **database.py**: Remove SQLite conditional logic, keep only MySQL configuration
2. **config.py**: Change default DATABASE_URL to MySQL, remove SQLite references
3. **models.py**: Optimize for MySQL-specific data types and constraints
4. **Test files**: Update all test configurations to use MySQL test databases

#### Files Requiring Minor Updates
- Migration scripts: Remove SQLite compatibility
- Documentation: Update all database references
- Environment examples: Replace SQLite examples with MySQL

### 3. MySQL Optimization Features

#### Connection Pooling
```python
engine_kwargs = {
    'poolclass': QueuePool,
    'pool_size': 20,           # Optimized for MySQL
    'max_overflow': 30,        # Handle traffic spikes
    'pool_timeout': 30,        # Connection timeout
    'pool_recycle': 3600,      # Recycle connections hourly
    'pool_pre_ping': True,     # Validate connections
}
```

#### MySQL-Specific Features
- **InnoDB Storage Engine**: For ACID compliance and foreign keys
- **UTF8MB4 Charset**: Full Unicode support including emojis
- **Connection Compression**: For network efficiency
- **SSL Support**: For secure connections
- **Query Optimization**: MySQL-specific index hints and query patterns

### 4. Environment Configuration

#### Required Environment Variables
```bash
# MySQL Configuration
DATABASE_URL=mysql+pymysql://user:password@host:port/database?charset=utf8mb4
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=vedfolnir
MYSQL_USER=vedfolnir_user
MYSQL_PASSWORD=secure_password

# Connection Pool Configuration
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# MySQL-Specific Options
MYSQL_CHARSET=utf8mb4
MYSQL_USE_SSL=true
MYSQL_SSL_CA=/path/to/ca.pem
```

### 5. Error Handling and Diagnostics

#### MySQL-Specific Error Handling
```python
class MySQLConnectionError(Exception):
    """MySQL-specific connection errors with diagnostic information"""
    
    def __init__(self, message, mysql_error_code=None, connection_params=None):
        self.mysql_error_code = mysql_error_code
        self.connection_params = connection_params
        super().__init__(message)

def handle_mysql_error(error):
    """Provide MySQL-specific error diagnostics and solutions"""
    error_mappings = {
        1045: "Access denied - check username and password",
        1049: "Unknown database - verify database name exists",
        2003: "Can't connect to MySQL server - check host and port",
        1146: "Table doesn't exist - run database migrations",
    }
    return error_mappings.get(error.args[0], "Unknown MySQL error")
```

### 6. Performance Monitoring

#### MySQL Performance Metrics
- Connection pool utilization
- Query execution times
- Index usage statistics
- Lock wait times
- Buffer pool hit ratio

#### Monitoring Integration
```python
class MySQLPerformanceMonitor:
    def track_query_performance(self, query, execution_time):
        """Track MySQL-specific performance metrics"""
        
    def monitor_connection_pool(self):
        """Monitor MySQL connection pool health"""
        
    def analyze_slow_queries(self):
        """Identify and log slow MySQL queries"""
```

## Implementation Sequence

### Phase 1: Configuration Migration
1. Update default DATABASE_URL in config.py
2. Remove SQLite conditional logic from database.py
3. Update environment variable documentation

### Phase 2: Code Cleanup
1. Remove SQLite imports and references
2. Clean up conditional database logic
3. Update error handling for MySQL-only

### Phase 3: Test Migration
1. Update test configurations for MySQL
2. Create MySQL test database fixtures
3. Validate all tests pass with MySQL

### Phase 4: Documentation and Deployment
1. Update all documentation references
2. Create MySQL deployment guides
3. Update Docker and deployment configurations

### Phase 5: File Cleanup
1. Remove SQLite database files
2. Clean up SQLite-related temporary files
3. Update .gitignore to exclude MySQL-specific files

## Data Schema Considerations

### MySQL-Optimized Schema
```sql
-- Use InnoDB engine for ACID compliance
CREATE TABLE posts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optimize foreign key constraints
ALTER TABLE images 
ADD CONSTRAINT fk_images_post_id 
FOREIGN KEY (post_id) REFERENCES posts(id) 
ON DELETE CASCADE ON UPDATE CASCADE;
```

### Index Optimization
- **Primary Keys**: Use AUTO_INCREMENT BIGINT for scalability
- **Foreign Keys**: Proper indexing for join performance
- **Text Search**: Full-text indexes for content search
- **Composite Indexes**: For common query patterns

## Security Considerations

### MySQL Security Features
- **SSL/TLS Encryption**: For data in transit
- **User Privilege Management**: Principle of least privilege
- **Connection Limits**: Prevent connection exhaustion attacks
- **Query Logging**: For security audit trails

### Configuration Security
```python
# Secure connection configuration
connect_args = {
    'ssl_ca': '/path/to/ca.pem',
    'ssl_cert': '/path/to/client-cert.pem',
    'ssl_key': '/path/to/client-key.pem',
    'ssl_verify_cert': True,
    'ssl_verify_identity': True,
}
```

## Testing Strategy

### MySQL Test Environment
- **Test Database**: Separate MySQL instance for testing
- **Test Data**: MySQL-compatible test fixtures
- **Performance Tests**: MySQL-specific performance benchmarks
- **Integration Tests**: Full application stack with MySQL

### Test Configuration
```python
# Test-specific MySQL configuration
TEST_DATABASE_URL = "mysql+pymysql://test_user:test_pass@localhost/vedfolnir_test"

class MySQLTestCase(unittest.TestCase):
    def setUp(self):
        # Create MySQL test database and tables
        
    def tearDown(self):
        # Clean up MySQL test data
```

## Rollback and Recovery

### Emergency Procedures
Since no data migration is required, rollback involves:
1. Reverting code changes to support SQLite
2. Restoring SQLite configuration defaults
3. Recreating empty SQLite database with fresh schema

### Monitoring and Alerts
- MySQL connection health monitoring
- Performance degradation alerts
- Error rate monitoring
- Connection pool exhaustion alerts
