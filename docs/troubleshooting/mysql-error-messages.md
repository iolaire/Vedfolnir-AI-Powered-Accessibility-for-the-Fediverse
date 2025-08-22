# MySQL Error Messages and Solutions

This guide provides comprehensive solutions for MySQL-specific error messages encountered in Vedfolnir deployments.

## Table of Contents

1. [Connection Errors](#connection-errors)
2. [Authentication Errors](#authentication-errors)
3. [Database and Table Errors](#database-and-table-errors)
4. [Query Execution Errors](#query-execution-errors)
5. [Performance and Resource Errors](#performance-and-resource-errors)
6. [Data Integrity Errors](#data-integrity-errors)
7. [Configuration Errors](#configuration-errors)

## Connection Errors

### Error 2003: Can't connect to MySQL server

**Error Message:**
```
ERROR 2003 (HY000): Can't connect to MySQL server on 'localhost' (111)
```

**Causes:**
- MySQL server is not running
- Wrong host or port configuration
- Firewall blocking connection
- MySQL not listening on specified interface

**Solutions:**

1. **Check MySQL Service:**
   ```bash
   # Check if MySQL is running
   sudo systemctl status mysql
   
   # Start MySQL if stopped
   sudo systemctl start mysql
   
   # For Docker
   docker-compose ps mysql
   docker-compose up -d mysql
   ```

2. **Verify Connection Parameters:**
   ```bash
   # Test connection manually
   mysql -h localhost -P 3306 -u vedfolnir -p
   
   # Check MySQL configuration
   mysql -u root -p -e "SHOW VARIABLES LIKE 'port';"
   mysql -u root -p -e "SHOW VARIABLES LIKE 'bind_address';"
   ```

3. **Check Firewall:**
   ```bash
   # Check if port 3306 is open
   netstat -tlnp | grep 3306
   
   # Allow MySQL through firewall (if needed)
   sudo ufw allow 3306/tcp
   ```

### Error 2002: Can't connect through socket

**Error Message:**
```
ERROR 2002 (HY000): Can't connect to local MySQL server through socket '/var/run/mysqld/mysqld.sock' (2)
```

**Causes:**
- MySQL socket file missing or incorrect path
- Permission issues with socket file
- MySQL server not running

**Solutions:**

1. **Check Socket File:**
   ```bash
   # Find MySQL socket file
   mysql -u root -p -e "SHOW VARIABLES LIKE 'socket';"
   
   # Check if socket file exists
   ls -la /var/run/mysqld/mysqld.sock
   ```

2. **Fix Socket Permissions:**
   ```bash
   # Fix socket directory permissions
   sudo chown mysql:mysql /var/run/mysqld/
   sudo chmod 755 /var/run/mysqld/
   
   # Restart MySQL
   sudo systemctl restart mysql
   ```

3. **Use TCP Connection:**
   ```bash
   # Connect via TCP instead of socket
   mysql -h 127.0.0.1 -P 3306 -u vedfolnir -p
   ```

## Authentication Errors

### Error 1045: Access denied for user

**Error Message:**
```
ERROR 1045 (28000): Access denied for user 'vedfolnir'@'localhost' (using password: YES)
```

**Causes:**
- Incorrect username or password
- User doesn't exist or lacks privileges
- Host restrictions

**Solutions:**

1. **Verify User Exists:**
   ```bash
   # Check if user exists
   mysql -u root -p -e "SELECT user, host FROM mysql.user WHERE user='vedfolnir';"
   
   # Check user privileges
   mysql -u root -p -e "SHOW GRANTS FOR 'vedfolnir'@'localhost';"
   ```

2. **Reset User Password:**
   ```sql
   -- Connect as root
   mysql -u root -p
   
   -- Reset password
   ALTER USER 'vedfolnir'@'localhost' IDENTIFIED BY 'new_secure_password';
   FLUSH PRIVILEGES;
   ```

3. **Create User if Missing:**
   ```sql
   -- Create user and grant privileges
   CREATE USER 'vedfolnir'@'localhost' IDENTIFIED BY 'secure_password';
   GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir'@'localhost';
   FLUSH PRIVILEGES;
   ```

### Error 1698: Access denied for user 'root'

**Error Message:**
```
ERROR 1698 (28000): Access denied for user 'root'@'localhost'
```

**Causes:**
- Root user configured for auth_socket plugin
- Incorrect root password

**Solutions:**

1. **Use sudo to connect as root:**
   ```bash
   sudo mysql -u root
   ```

2. **Change root authentication method:**
   ```sql
   -- Connect with sudo mysql
   sudo mysql -u root
   
   -- Change to password authentication
   ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'new_root_password';
   FLUSH PRIVILEGES;
   ```

## Database and Table Errors

### Error 1049: Unknown database

**Error Message:**
```
ERROR 1049 (42000): Unknown database 'vedfolnir'
```

**Causes:**
- Database doesn't exist
- Typo in database name

**Solutions:**

1. **Check Existing Databases:**
   ```bash
   mysql -u root -p -e "SHOW DATABASES;"
   ```

2. **Create Database:**
   ```sql
   CREATE DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. **Initialize Database:**
   ```bash
   # Run database initialization
   python -c "
   from database import init_db
   init_db()
   print('Database initialized successfully')
   "
   ```

### Error 1146: Table doesn't exist

**Error Message:**
```
ERROR 1146 (42S02): Table 'vedfolnir.users' doesn't exist
```

**Causes:**
- Table not created
- Database not properly initialized
- Migration not run

**Solutions:**

1. **Check Existing Tables:**
   ```bash
   mysql -u vedfolnir -p vedfolnir -e "SHOW TABLES;"
   ```

2. **Run Database Initialization:**
   ```bash
   python -c "
   from database import init_db
   init_db()
   print('Database tables created')
   "
   ```

3. **Manual Table Creation:**
   ```sql
   -- Example: Create users table
   CREATE TABLE users (
       id INT AUTO_INCREMENT PRIMARY KEY,
       username VARCHAR(255) NOT NULL UNIQUE,
       email VARCHAR(255) NOT NULL UNIQUE,
       password_hash VARCHAR(255) NOT NULL,
       is_active BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
   ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
   ```

### Error 1054: Unknown column

**Error Message:**
```
ERROR 1054 (42S22): Unknown column 'column_name' in 'field list'
```

**Causes:**
- Column doesn't exist in table
- Schema mismatch
- Migration not applied

**Solutions:**

1. **Check Table Structure:**
   ```bash
   mysql -u vedfolnir -p vedfolnir -e "DESCRIBE table_name;"
   ```

2. **Add Missing Column:**
   ```sql
   ALTER TABLE table_name ADD COLUMN column_name VARCHAR(255);
   ```

3. **Run Migrations:**
   ```bash
   python -c "
   from database import run_migrations
   run_migrations()
   print('Migrations completed')
   "
   ```

## Query Execution Errors

### Error 1064: SQL syntax error

**Error Message:**
```
ERROR 1064 (42000): You have an error in your SQL syntax
```

**Causes:**
- Invalid SQL syntax
- Reserved word used without backticks
- Missing quotes or parentheses

**Solutions:**

1. **Check SQL Syntax:**
   ```bash
   # Use EXPLAIN to validate query
   mysql -u vedfolnir -p vedfolnir -e "EXPLAIN SELECT * FROM users WHERE id = 1;"
   ```

2. **Escape Reserved Words:**
   ```sql
   -- Use backticks for reserved words
   SELECT `order`, `date` FROM `table`;
   ```

3. **Validate Query Structure:**
   ```sql
   -- Check for common syntax issues
   -- Missing quotes around strings
   SELECT * FROM users WHERE username = 'admin';
   
   -- Proper parentheses in complex queries
   SELECT * FROM users WHERE (status = 'active' AND role = 'admin') OR role = 'superuser';
   ```

### Error 1062: Duplicate entry

**Error Message:**
```
ERROR 1062 (23000): Duplicate entry 'value' for key 'PRIMARY'
```

**Causes:**
- Attempting to insert duplicate primary key
- Unique constraint violation

**Solutions:**

1. **Use INSERT IGNORE:**
   ```sql
   INSERT IGNORE INTO users (username, email) VALUES ('admin', 'admin@example.com');
   ```

2. **Use ON DUPLICATE KEY UPDATE:**
   ```sql
   INSERT INTO users (username, email, updated_at) 
   VALUES ('admin', 'admin@example.com', NOW())
   ON DUPLICATE KEY UPDATE 
       email = VALUES(email),
       updated_at = NOW();
   ```

3. **Check for Existing Records:**
   ```sql
   SELECT * FROM users WHERE username = 'admin';
   ```

### Error 1452: Foreign key constraint fails

**Error Message:**
```
ERROR 1452 (23000): Cannot add or update a child row: a foreign key constraint fails
```

**Causes:**
- Referenced parent record doesn't exist
- Foreign key value is invalid

**Solutions:**

1. **Check Parent Record:**
   ```sql
   -- Verify parent record exists
   SELECT * FROM parent_table WHERE id = foreign_key_value;
   ```

2. **Insert Parent Record First:**
   ```sql
   -- Insert parent record before child
   INSERT INTO users (username, email) VALUES ('user1', 'user1@example.com');
   INSERT INTO posts (user_id, title) VALUES (LAST_INSERT_ID(), 'Post Title');
   ```

3. **Disable Foreign Key Checks (Temporarily):**
   ```sql
   SET FOREIGN_KEY_CHECKS = 0;
   -- Your INSERT/UPDATE statements here
   SET FOREIGN_KEY_CHECKS = 1;
   ```

## Performance and Resource Errors

### Error 1040: Too many connections

**Error Message:**
```
ERROR 1040 (HY000): Too many connections
```

**Causes:**
- Connection limit exceeded
- Connection pool not properly configured
- Connection leaks in application

**Solutions:**

1. **Increase Connection Limit:**
   ```sql
   -- Temporarily increase limit
   SET GLOBAL max_connections = 500;
   
   -- Permanently (add to my.cnf)
   -- max_connections = 500
   ```

2. **Check Current Connections:**
   ```bash
   mysql -u root -p -e "SHOW PROCESSLIST;"
   mysql -u root -p -e "SHOW STATUS LIKE 'Threads_connected';"
   ```

3. **Fix Application Connection Pool:**
   ```python
   # In config.py
   SQLALCHEMY_ENGINE_OPTIONS = {
       'pool_size': 20,
       'max_overflow': 30,
       'pool_timeout': 30,
       'pool_recycle': 3600
   }
   ```

### Error 1205: Lock wait timeout exceeded

**Error Message:**
```
ERROR 1205 (HY000): Lock wait timeout exceeded; try restarting transaction
```

**Causes:**
- Long-running transactions holding locks
- Deadlock situation
- Inefficient queries

**Solutions:**

1. **Check for Blocking Transactions:**
   ```sql
   -- Check current transactions
   SELECT * FROM information_schema.innodb_trx;
   
   -- Check locks
   SELECT * FROM information_schema.innodb_locks;
   
   -- Check lock waits
   SELECT * FROM information_schema.innodb_lock_waits;
   ```

2. **Kill Blocking Transactions:**
   ```sql
   -- Kill specific transaction (use trx_id from innodb_trx)
   KILL CONNECTION_ID;
   ```

3. **Optimize Queries:**
   ```sql
   -- Use smaller transactions
   START TRANSACTION;
   -- Minimal operations here
   COMMIT;
   
   -- Add appropriate indexes to reduce lock time
   CREATE INDEX idx_posts_user_id ON posts(user_id);
   ```

### Error 1114: Table is full

**Error Message:**
```
ERROR 1114 (HY000): The table 'table_name' is full
```

**Causes:**
- Disk space exhausted
- Table size limit reached
- Temporary directory full

**Solutions:**

1. **Check Disk Space:**
   ```bash
   df -h /var/lib/mysql
   du -sh /var/lib/mysql/vedfolnir/
   ```

2. **Clean Up Space:**
   ```bash
   # Remove old binary logs
   mysql -u root -p -e "PURGE BINARY LOGS BEFORE DATE(NOW() - INTERVAL 7 DAY);"
   
   # Optimize tables
   mysql -u vedfolnir -p vedfolnir -e "OPTIMIZE TABLE users, posts, captions;"
   ```

3. **Increase Table Limits:**
   ```sql
   -- For MyISAM tables (if used)
   ALTER TABLE table_name MAX_ROWS = 1000000000;
   ```

## Data Integrity Errors

### Error 1366: Incorrect string value

**Error Message:**
```
ERROR 1366 (HY000): Incorrect string value: '\xF0\x9F\x98\x80' for column 'text'
```

**Causes:**
- Character set mismatch
- Attempting to insert emoji/unicode in non-utf8mb4 column

**Solutions:**

1. **Convert to utf8mb4:**
   ```sql
   -- Convert database
   ALTER DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   
   -- Convert table
   ALTER TABLE table_name CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   
   -- Convert specific column
   ALTER TABLE table_name MODIFY column_name TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. **Check Current Character Set:**
   ```sql
   SHOW VARIABLES LIKE 'character_set%';
   SHOW TABLE STATUS FROM vedfolnir;
   ```

### Error 1264: Out of range value

**Error Message:**
```
ERROR 1264 (22003): Out of range value for column 'column_name'
```

**Causes:**
- Value exceeds column data type limits
- Negative value for unsigned column

**Solutions:**

1. **Modify Column Type:**
   ```sql
   -- Increase column size
   ALTER TABLE table_name MODIFY column_name BIGINT;
   
   -- Remove UNSIGNED constraint if needed
   ALTER TABLE table_name MODIFY column_name INT;
   ```

2. **Check Data Ranges:**
   ```sql
   -- Check current values
   SELECT MIN(column_name), MAX(column_name) FROM table_name;
   ```

## Configuration Errors

### Error 1067: Invalid default value

**Error Message:**
```
ERROR 1067 (42000): Invalid default value for 'created_at'
```

**Causes:**
- Invalid default value for timestamp column
- SQL mode restrictions

**Solutions:**

1. **Fix Column Definition:**
   ```sql
   -- Correct timestamp default
   ALTER TABLE table_name MODIFY created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
   ```

2. **Check SQL Mode:**
   ```sql
   SELECT @@sql_mode;
   
   -- Set less restrictive SQL mode if needed
   SET sql_mode = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION';
   ```

### Error 1419: You do not have the SUPER privilege

**Error Message:**
```
ERROR 1419 (HY000): You do not have the SUPER privilege and binary logging is enabled
```

**Causes:**
- Creating functions/procedures without SUPER privilege
- Binary logging restrictions

**Solutions:**

1. **Grant SUPER Privilege:**
   ```sql
   -- Connect as root
   GRANT SUPER ON *.* TO 'vedfolnir'@'localhost';
   FLUSH PRIVILEGES;
   ```

2. **Disable Binary Logging (if appropriate):**
   ```sql
   SET sql_log_bin = 0;
   -- Your function/procedure creation here
   SET sql_log_bin = 1;
   ```

3. **Use DEFINER Clause:**
   ```sql
   CREATE DEFINER='vedfolnir'@'localhost' FUNCTION function_name()
   RETURNS INT
   READS SQL DATA
   DETERMINISTIC
   BEGIN
       -- Function body
   END;
   ```

## Error Logging and Monitoring

### Enable Error Logging

```bash
# Add to MySQL configuration
[mysqld]
log_error = /var/log/mysql/error.log
log_warnings = 2

# Restart MySQL
sudo systemctl restart mysql
```

### Monitor Error Logs

```bash
# Watch error log in real-time
tail -f /var/log/mysql/error.log

# Search for specific errors
grep "ERROR" /var/log/mysql/error.log | tail -20

# Check for connection errors
grep "Access denied" /var/log/mysql/error.log
```

### Application Error Handling

```python
# Proper error handling in Python
import pymysql
import logging

def handle_mysql_error(e):
    error_code = e.args[0]
    error_message = e.args[1]
    
    if error_code == 1045:  # Access denied
        logging.error(f"MySQL authentication failed: {error_message}")
        return "Database authentication error"
    elif error_code == 2003:  # Can't connect
        logging.error(f"MySQL connection failed: {error_message}")
        return "Database connection error"
    elif error_code == 1146:  # Table doesn't exist
        logging.error(f"MySQL table missing: {error_message}")
        return "Database schema error"
    else:
        logging.error(f"MySQL error {error_code}: {error_message}")
        return "Database error"

try:
    # Database operations here
    pass
except pymysql.Error as e:
    error_msg = handle_mysql_error(e)
    # Handle error appropriately
```

This comprehensive error message guide should help quickly identify and resolve MySQL-specific issues in Vedfolnir deployments.
