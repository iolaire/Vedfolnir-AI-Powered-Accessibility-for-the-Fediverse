# MySQL Migration Guide

This guide walks you through migrating your Vedfolnir Flask application from SQLite to MySQL while preserving your Redis configuration.

## Prerequisites

- MySQL server running with unix_socket authentication
- Database: `database_user_1d7b0d0696a20`
- User: `database_user_1d7b0d0696a20`
- Password: `EQA&bok7`
- Unix socket: `/var/run/mysqld/mysqld.sock`
- Redis server (unchanged)

## Migration Steps

### Step 1: Install MySQL Dependencies

```bash
# Install PyMySQL connector
pip install pymysql>=1.1.0

# Or update from requirements.txt
pip install -r requirements.txt
```

### Step 2: Backup Current Data (Optional)

If you have existing data in SQLite that you want to preserve:

```bash
# Backup SQLite database
cp storage/database/vedfolnir.db storage/database/vedfolnir.db.backup

# Export data (if needed for manual migration)
sqlite3 storage/database/vedfolnir.db .dump > vedfolnir_sqlite_backup.sql
```

### Step 3: Update Environment Configuration

Update your `.env` file with MySQL settings:

```bash
# Copy the MySQL template
cp .env.mysql.template .env

# Edit .env with your specific values
# The key changes are:

# Database Configuration - MySQL with Unix Socket
DB_TYPE=mysql
DB_NAME=database_user_1d7b0d0696a20
DB_USER=database_user_1d7b0d0696a20
DB_PASSWORD=EQA&bok7
DB_UNIX_SOCKET=/var/run/mysqld/mysqld.sock
DATABASE_URL=mysql+pymysql://database_user_1d7b0d0696a20:EQA%26bok7@localhost/database_user_1d7b0d0696a20?unix_socket=/var/run/mysqld/mysqld.sock&charset=utf8mb4

# Keep all Redis settings unchanged
REDIS_URL=redis://:your-redis-password@localhost:6379/0
# ... other Redis settings remain the same
```

**Important Notes:**
- The `&` character in the password is URL-encoded as `%26` in the DATABASE_URL
- All Redis configuration remains unchanged
- Update `FLASK_SECRET_KEY` and `PLATFORM_ENCRYPTION_KEY` with secure values

### Step 4: Run the Migration

Execute the migration script:

```bash
# Run the MySQL migration script
python scripts/mysql_migration/migrate_to_mysql.py
```

This script will:
1. Test MySQL connection
2. Create all required tables with proper charset (utf8mb4)
3. Set up indexes and foreign key constraints
4. Verify the schema

### Step 5: Verify the Migration

Run the verification script:

```bash
# Verify the migration was successful
python scripts/mysql_migration/verify_mysql_migration.py
```

This will check:
- MySQL connection and configuration
- Table structure and charset
- Redis connection (should be unchanged)
- SQLAlchemy model compatibility
- Foreign key constraints

### Step 6: Test Your Application

Start your application and test functionality:

```bash
# Start the web application
python web_app.py
```

Test the following:
- [ ] Application starts without errors
- [ ] User login/logout works
- [ ] Platform connections can be added/edited
- [ ] Caption generation works
- [ ] Session management works (Redis-backed)
- [ ] Database operations (CRUD) work correctly

## Database Schema Changes

The migration includes these MySQL-specific optimizations:

### Table Options
All tables now include:
```sql
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
```

### Primary Keys
All primary key columns now explicitly use `AUTO_INCREMENT`:
```sql
id INT NOT NULL AUTO_INCREMENT PRIMARY KEY
```

### Data Type Mappings

| SQLite Type | MySQL Type | Notes |
|-------------|------------|-------|
| INTEGER PRIMARY KEY | INT AUTO_INCREMENT PRIMARY KEY | Explicit auto-increment |
| TEXT | TEXT | Unchanged |
| VARCHAR(n) | VARCHAR(n) | Unchanged |
| BOOLEAN | TINYINT(1) | MySQL boolean equivalent |
| DATETIME | DATETIME | Unchanged |
| REAL/FLOAT | FLOAT | Unchanged |

### Character Set
- Database charset: `utf8mb4`
- Collation: `utf8mb4_unicode_ci`
- Supports full Unicode including emojis

## Connection Configuration

### MySQL Connection String Format
```
mysql+pymysql://username:password@localhost/database?unix_socket=/path/to/socket&charset=utf8mb4
```

### Connection Pool Settings (MySQL Optimized)
```python
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=50
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused
```
Error: (2002, "Can't connect to MySQL server")
```
**Solution:** Check that MySQL is running and the unix socket path is correct.

#### 2. Authentication Failed
```
Error: (1045, "Access denied for user")
```
**Solution:** Verify username, password, and database name are correct.

#### 3. Charset Issues
```
Error: Incorrect string value
```
**Solution:** Ensure all tables use `utf8mb4` charset.

#### 4. Foreign Key Constraints
```
Error: Cannot add or update a child row: a foreign key constraint fails
```
**Solution:** Check that referenced tables exist and have correct structure.

### Debugging Commands

```bash
# Test MySQL connection directly
mysql -u database_user_1d7b0d0696a20 -p database_user_1d7b0d0696a20

# Check table structure
mysql> SHOW TABLES;
mysql> DESCRIBE users;
mysql> SHOW CREATE TABLE users;

# Check charset and collation
mysql> SELECT @@character_set_database, @@collation_database;

# Check foreign keys
mysql> SELECT * FROM information_schema.KEY_COLUMN_USAGE 
       WHERE REFERENCED_TABLE_SCHEMA = 'database_user_1d7b0d0696a20';
```

### Performance Tuning

For production environments, consider these MySQL optimizations:

```sql
-- Increase connection limits
SET GLOBAL max_connections = 200;

-- Optimize InnoDB settings
SET GLOBAL innodb_buffer_pool_size = 1G;
SET GLOBAL innodb_log_file_size = 256M;

-- Enable query cache (if using MySQL < 8.0)
SET GLOBAL query_cache_type = ON;
SET GLOBAL query_cache_size = 64M;
```

## Rollback Procedure

If you need to rollback to SQLite:

1. **Stop the application**
2. **Restore the original .env file:**
   ```bash
   # Restore SQLite configuration
   DATABASE_URL=sqlite:///storage/database/vedfolnir.db
   ```
3. **Restore SQLite database (if backed up):**
   ```bash
   cp storage/database/vedfolnir.db.backup storage/database/vedfolnir.db
   ```
4. **Restart the application**

## Redis Configuration (Unchanged)

Your Redis configuration should remain exactly the same:

```bash
# Redis settings (no changes needed)
REDIS_URL=redis://:your-password@localhost:6379/0
REDIS_SESSION_PREFIX=vedfolnir:session:
REDIS_SESSION_TIMEOUT=7200
# ... all other Redis settings unchanged
```

## Post-Migration Checklist

- [ ] MySQL connection successful
- [ ] All tables created with correct structure
- [ ] Foreign key constraints working
- [ ] Character set is utf8mb4
- [ ] Redis connection unchanged and working
- [ ] Application starts without errors
- [ ] User authentication works
- [ ] Platform management works
- [ ] Caption generation works
- [ ] Session management works
- [ ] All CRUD operations work
- [ ] Performance is acceptable

## Support

If you encounter issues during migration:

1. Check the application logs in `logs/webapp.log`
2. Run the verification script for detailed diagnostics
3. Review the troubleshooting section above
4. Check MySQL error logs: `/var/log/mysql/error.log`

## Security Notes

- The MySQL connection uses unix_socket authentication for enhanced security
- All credentials are encrypted in the database using the `PLATFORM_ENCRYPTION_KEY`
- Redis session data remains encrypted and secure
- Ensure proper file permissions on the `.env` file (600)
- Never commit the `.env` file to version control

## Performance Benefits

MySQL offers several advantages over SQLite for production use:

- **Concurrent Access:** Better handling of multiple simultaneous connections
- **Performance:** Optimized for larger datasets and complex queries
- **Scalability:** Can handle higher loads and more users
- **Backup:** Better backup and replication options
- **Monitoring:** More comprehensive monitoring and optimization tools

The migration maintains all existing functionality while providing these performance improvements.
