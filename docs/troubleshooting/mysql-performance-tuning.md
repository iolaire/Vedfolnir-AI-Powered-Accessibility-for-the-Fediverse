# MySQL Performance Tuning and Optimization Guide

This guide provides comprehensive MySQL performance tuning and optimization strategies specifically for Vedfolnir's MySQL deployment.

## Table of Contents

1. [Performance Monitoring](#performance-monitoring)
2. [Configuration Optimization](#configuration-optimization)
3. [Query Optimization](#query-optimization)
4. [Index Management](#index-management)
5. [Connection Pool Tuning](#connection-pool-tuning)
6. [Memory Optimization](#memory-optimization)
7. [Disk I/O Optimization](#disk-io-optimization)
8. [Troubleshooting Performance Issues](#troubleshooting-performance-issues)

## Performance Monitoring

### Key Performance Metrics

#### 1. Connection Metrics
```bash
# Monitor current connections
mysql -u vedfolnir -p -e "
SELECT 
    VARIABLE_NAME,
    VARIABLE_VALUE
FROM performance_schema.global_status 
WHERE VARIABLE_NAME IN (
    'Connections',
    'Max_used_connections',
    'Threads_connected',
    'Threads_running',
    'Aborted_connects',
    'Aborted_clients'
);
"

# Check connection usage percentage
mysql -u vedfolnir -p -e "
SELECT 
    ROUND(
        (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Threads_connected') /
        (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections') * 100, 2
    ) as connection_usage_percent;
"
```

#### 2. Query Performance Metrics
```bash
# Top 10 slowest queries
mysql -u vedfolnir -p -e "
SELECT 
    schema_name,
    LEFT(digest_text, 100) as query_sample,
    count_star as executions,
    ROUND(avg_timer_wait/1000000000, 2) as avg_time_seconds,
    ROUND(sum_timer_wait/1000000000, 2) as total_time_seconds,
    ROUND(max_timer_wait/1000000000, 2) as max_time_seconds
FROM performance_schema.events_statements_summary_by_digest 
WHERE schema_name = 'vedfolnir'
ORDER BY sum_timer_wait DESC 
LIMIT 10;
"

# Query execution statistics
mysql -u vedfolnir -p -e "
SELECT 
    VARIABLE_NAME,
    VARIABLE_VALUE
FROM performance_schema.global_status 
WHERE VARIABLE_NAME IN (
    'Questions',
    'Queries',
    'Slow_queries',
    'Select_scan',
    'Select_full_join'
);
"
```

#### 3. InnoDB Performance Metrics
```bash
# InnoDB buffer pool statistics
mysql -u vedfolnir -p -e "
SELECT 
    VARIABLE_NAME,
    VARIABLE_VALUE
FROM performance_schema.global_status 
WHERE VARIABLE_NAME LIKE 'Innodb_buffer_pool%'
ORDER BY VARIABLE_NAME;
"

# InnoDB I/O statistics
mysql -u vedfolnir -p -e "
SELECT 
    VARIABLE_NAME,
    VARIABLE_VALUE
FROM performance_schema.global_status 
WHERE VARIABLE_NAME LIKE 'Innodb_data%'
   OR VARIABLE_NAME LIKE 'Innodb_log%'
ORDER BY VARIABLE_NAME;
"
```

### Performance Monitoring Script

```bash
#!/bin/bash
# /usr/local/bin/vedfolnir-mysql-performance-monitor.sh

MYSQL_USER="vedfolnir"
MYSQL_PASSWORD="${MYSQL_PASSWORD}"
MYSQL_DATABASE="vedfolnir"

echo "=== Vedfolnir MySQL Performance Report - $(date) ==="

# Connection statistics
echo -e "\n--- Connection Statistics ---"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
SELECT 
    'Current Connections' as metric,
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Threads_connected') as value
UNION ALL
SELECT 
    'Max Connections',
    (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections')
UNION ALL
SELECT 
    'Connection Usage %',
    ROUND(
        (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Threads_connected') /
        (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections') * 100, 2
    );
"

# Query performance
echo -e "\n--- Query Performance ---"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
SELECT 
    'Total Queries' as metric,
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Questions') as value
UNION ALL
SELECT 
    'Slow Queries',
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Slow_queries')
UNION ALL
SELECT 
    'Full Table Scans',
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Select_scan');
"

# Table statistics
echo -e "\n--- Table Statistics ---"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT 
    table_name,
    table_rows,
    ROUND(data_length/1024/1024, 2) as data_mb,
    ROUND(index_length/1024/1024, 2) as index_mb,
    ROUND((data_length + index_length)/1024/1024, 2) as total_mb
FROM information_schema.tables 
WHERE table_schema = '$MYSQL_DATABASE'
ORDER BY (data_length + index_length) DESC;
"

# InnoDB buffer pool
echo -e "\n--- InnoDB Buffer Pool ---"
mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
SELECT 
    'Buffer Pool Size MB' as metric,
    ROUND((SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'innodb_buffer_pool_size')/1024/1024, 2) as value
UNION ALL
SELECT 
    'Buffer Pool Hit Rate %',
    ROUND(
        (1 - (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') /
        (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests')) * 100, 2
    );
"
```

## Configuration Optimization

### MySQL Configuration File

Create or update `/etc/mysql/conf.d/vedfolnir-performance.cnf`:

```ini
[mysqld]
# Basic settings
default_storage_engine = InnoDB
character_set_server = utf8mb4
collation_server = utf8mb4_unicode_ci

# Connection settings
max_connections = 200
max_connect_errors = 1000
connect_timeout = 60
wait_timeout = 28800
interactive_timeout = 28800

# InnoDB Buffer Pool (adjust based on available RAM)
# Use 70-80% of available RAM for dedicated MySQL server
innodb_buffer_pool_size = 2G
innodb_buffer_pool_instances = 8

# InnoDB Log settings
innodb_log_file_size = 512M
innodb_log_buffer_size = 64M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# InnoDB I/O settings
innodb_io_capacity = 200
innodb_io_capacity_max = 2000
innodb_read_io_threads = 8
innodb_write_io_threads = 8

# Query cache (MySQL 5.7 and earlier)
query_cache_type = 1
query_cache_size = 128M
query_cache_limit = 2M

# Temporary tables
tmp_table_size = 64M
max_heap_table_size = 64M

# MyISAM settings (if used)
key_buffer_size = 32M

# Logging
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
log_queries_not_using_indexes = 1

# Binary logging
log_bin = mysql-bin
binlog_format = ROW
expire_logs_days = 7
max_binlog_size = 100M

# Performance Schema
performance_schema = ON
performance_schema_max_table_instances = 12500
performance_schema_max_table_handles = 4000
```

### Dynamic Configuration Changes

```bash
# Apply configuration changes without restart (where possible)

# Connection settings
mysql -u root -p -e "SET GLOBAL max_connections = 300;"
mysql -u root -p -e "SET GLOBAL wait_timeout = 28800;"

# Query cache settings (MySQL 5.7 and earlier)
mysql -u root -p -e "SET GLOBAL query_cache_size = 134217728;"  # 128MB
mysql -u root -p -e "SET GLOBAL query_cache_type = 1;"

# InnoDB settings (some require restart)
mysql -u root -p -e "SET GLOBAL innodb_io_capacity = 400;"
mysql -u root -p -e "SET GLOBAL innodb_io_capacity_max = 2000;"

# Logging settings
mysql -u root -p -e "SET GLOBAL slow_query_log = 1;"
mysql -u root -p -e "SET GLOBAL long_query_time = 2;"
```

## Query Optimization

### Identifying Slow Queries

```bash
# Enable slow query log
mysql -u root -p -e "
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 1;
SET GLOBAL log_queries_not_using_indexes = 1;
"

# Analyze slow query log
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log

# Use pt-query-digest (if available)
pt-query-digest /var/log/mysql/slow.log
```

### Common Query Optimizations

#### 1. Optimize SELECT Queries
```sql
-- Bad: SELECT * without WHERE clause
SELECT * FROM posts;

-- Good: SELECT specific columns with WHERE clause
SELECT id, title, created_at FROM posts WHERE user_id = 1 LIMIT 20;

-- Bad: Using functions in WHERE clause
SELECT * FROM posts WHERE YEAR(created_at) = 2024;

-- Good: Using range conditions
SELECT * FROM posts WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';
```

#### 2. Optimize JOIN Operations
```sql
-- Ensure proper indexes exist for JOIN conditions
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_captions_post_id ON captions(post_id);

-- Use EXPLAIN to analyze JOIN performance
EXPLAIN SELECT 
    p.id, p.title, c.caption_text
FROM posts p
LEFT JOIN captions c ON p.id = c.post_id
WHERE p.user_id = 1;
```

#### 3. Optimize INSERT Operations
```sql
-- Use batch inserts instead of individual INSERTs
INSERT INTO posts (user_id, title, content, created_at) VALUES
    (1, 'Title 1', 'Content 1', NOW()),
    (1, 'Title 2', 'Content 2', NOW()),
    (1, 'Title 3', 'Content 3', NOW());

-- Use INSERT ... ON DUPLICATE KEY UPDATE for upserts
INSERT INTO captions (post_id, caption_text, created_at)
VALUES (1, 'New caption', NOW())
ON DUPLICATE KEY UPDATE 
    caption_text = VALUES(caption_text),
    updated_at = NOW();
```

### Query Analysis Tools

```bash
# Use EXPLAIN to analyze query execution plans
mysql -u vedfolnir -p vedfolnir -e "
EXPLAIN FORMAT=JSON 
SELECT p.*, c.caption_text 
FROM posts p 
LEFT JOIN captions c ON p.id = c.post_id 
WHERE p.user_id = 1 
ORDER BY p.created_at DESC 
LIMIT 10;
"

# Check query execution statistics
mysql -u vedfolnir -p -e "
SELECT 
    schema_name,
    digest_text,
    count_star,
    avg_timer_wait/1000000000 as avg_seconds,
    sum_timer_wait/1000000000 as total_seconds
FROM performance_schema.events_statements_summary_by_digest 
WHERE schema_name = 'vedfolnir'
ORDER BY sum_timer_wait DESC 
LIMIT 5;
"
```

## Index Management

### Essential Indexes for Vedfolnir

```sql
-- User-related indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- Platform connection indexes
CREATE INDEX idx_platform_connections_user_id ON platform_connections(user_id);
CREATE INDEX idx_platform_connections_type ON platform_connections(platform_type);
CREATE INDEX idx_platform_connections_active ON platform_connections(is_active);

-- Post indexes
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_platform_id ON posts(platform_connection_id);
CREATE INDEX idx_posts_created_at ON posts(created_at);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_composite ON posts(user_id, created_at DESC);

-- Caption indexes
CREATE INDEX idx_captions_post_id ON captions(post_id);
CREATE INDEX idx_captions_status ON captions(status);
CREATE INDEX idx_captions_created_at ON captions(created_at);

-- Session indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
```

### Index Analysis and Optimization

```bash
# Check index usage
mysql -u vedfolnir -p vedfolnir -e "
SELECT 
    table_name,
    index_name,
    cardinality,
    sub_part,
    nullable,
    index_type
FROM information_schema.statistics 
WHERE table_schema = 'vedfolnir'
ORDER BY table_name, seq_in_index;
"

# Find unused indexes
mysql -u vedfolnir -p -e "
SELECT 
    object_schema,
    object_name,
    index_name
FROM performance_schema.table_io_waits_summary_by_index_usage 
WHERE object_schema = 'vedfolnir'
  AND index_name IS NOT NULL
  AND count_star = 0
ORDER BY object_name, index_name;
"

# Check index efficiency
mysql -u vedfolnir -p vedfolnir -e "
SELECT 
    table_name,
    ROUND(data_length/1024/1024, 2) as data_mb,
    ROUND(index_length/1024/1024, 2) as index_mb,
    ROUND(index_length/data_length * 100, 2) as index_ratio_percent
FROM information_schema.tables 
WHERE table_schema = 'vedfolnir'
  AND data_length > 0
ORDER BY index_ratio_percent DESC;
"
```

### Index Maintenance

```bash
# Analyze tables to update index statistics
mysql -u vedfolnir -p vedfolnir -e "
ANALYZE TABLE users, platform_connections, posts, captions, sessions;
"

# Optimize tables to defragment and rebuild indexes
mysql -u vedfolnir -p vedfolnir -e "
OPTIMIZE TABLE users, platform_connections, posts, captions, sessions;
"

# Check for duplicate indexes
mysql -u vedfolnir -p -e "
SELECT 
    table_schema,
    table_name,
    GROUP_CONCAT(index_name) as duplicate_indexes,
    GROUP_CONCAT(column_name ORDER BY seq_in_index) as columns
FROM information_schema.statistics 
WHERE table_schema = 'vedfolnir'
GROUP BY table_schema, table_name, column_name
HAVING COUNT(*) > 1;
"
```

## Connection Pool Tuning

### Application-Level Connection Pool

```python
# In config.py - Optimize SQLAlchemy connection pool
SQLALCHEMY_ENGINE_OPTIONS = {
    # Connection pool size
    'pool_size': 20,                    # Number of connections to maintain
    'max_overflow': 30,                 # Additional connections beyond pool_size
    'pool_timeout': 30,                 # Seconds to wait for connection
    'pool_recycle': 3600,              # Recycle connections after 1 hour
    'pool_pre_ping': True,             # Validate connections before use
    
    # Connection parameters
    'connect_args': {
        'charset': 'utf8mb4',
        'connect_timeout': 60,
        'read_timeout': 30,
        'write_timeout': 30,
        'autocommit': False,
    },
    
    # Engine options
    'echo': False,                      # Set to True for SQL debugging
    'echo_pool': False,                 # Set to True for pool debugging
}
```

### Connection Pool Monitoring

```python
# Monitor connection pool status
def check_connection_pool():
    from database import get_db_engine
    
    engine = get_db_engine()
    pool = engine.pool
    
    print(f"Pool size: {pool.size()}")
    print(f"Checked out connections: {pool.checkedout()}")
    print(f"Overflow connections: {pool.overflow()}")
    print(f"Invalid connections: {pool.invalid()}")
    
    # Check MySQL connection statistics
    with engine.connect() as conn:
        result = conn.execute("""
            SELECT 
                VARIABLE_NAME,
                VARIABLE_VALUE
            FROM performance_schema.global_status 
            WHERE VARIABLE_NAME IN (
                'Threads_connected',
                'Max_used_connections',
                'Aborted_connects'
            )
        """)
        
        for row in result:
            print(f"{row[0]}: {row[1]}")
```

## Memory Optimization

### InnoDB Buffer Pool Optimization

```bash
# Calculate optimal buffer pool size (70-80% of available RAM)
TOTAL_RAM=$(free -b | awk 'NR==2{print $2}')
OPTIMAL_BUFFER_POOL=$(echo "$TOTAL_RAM * 0.75 / 1024 / 1024 / 1024" | bc)
echo "Recommended innodb_buffer_pool_size: ${OPTIMAL_BUFFER_POOL}G"

# Check current buffer pool usage
mysql -u vedfolnir -p -e "
SELECT 
    'Buffer Pool Size (MB)' as metric,
    ROUND(@@innodb_buffer_pool_size/1024/1024, 2) as value
UNION ALL
SELECT 
    'Buffer Pool Hit Rate (%)',
    ROUND(
        (1 - (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') /
        (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests')) * 100, 2
    )
UNION ALL
SELECT 
    'Buffer Pool Pages Free',
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_pages_free')
UNION ALL
SELECT 
    'Buffer Pool Pages Total',
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_pages_total');
"
```

### Memory Usage Monitoring

```bash
# Monitor MySQL memory usage
mysql -u vedfolnir -p -e "
SELECT 
    SUBSTRING_INDEX(event_name,'/',2) AS code_area, 
    FORMAT_BYTES(SUM(current_alloc)) AS current_alloc 
FROM performance_schema.memory_summary_global_by_event_name 
WHERE current_alloc > 0 
GROUP BY SUBSTRING_INDEX(event_name,'/',2) 
ORDER BY SUM(current_alloc) DESC;
"

# Check temporary table usage
mysql -u vedfolnir -p -e "
SELECT 
    'Created Tmp Tables' as metric,
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Created_tmp_tables') as value
UNION ALL
SELECT 
    'Created Tmp Disk Tables',
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Created_tmp_disk_tables')
UNION ALL
SELECT 
    'Tmp Disk Table Ratio (%)',
    ROUND(
        (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Created_tmp_disk_tables') /
        (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Created_tmp_tables') * 100, 2
    );
"
```

## Disk I/O Optimization

### InnoDB I/O Configuration

```ini
# Add to MySQL configuration file
[mysqld]
# I/O capacity settings (adjust based on storage type)
# For SSD storage:
innodb_io_capacity = 2000
innodb_io_capacity_max = 4000

# For traditional HDD:
# innodb_io_capacity = 200
# innodb_io_capacity_max = 400

# I/O threads
innodb_read_io_threads = 8
innodb_write_io_threads = 8

# Flush method (Linux)
innodb_flush_method = O_DIRECT

# Log file settings
innodb_log_file_size = 512M
innodb_log_files_in_group = 2
innodb_log_buffer_size = 64M

# Flush settings
innodb_flush_log_at_trx_commit = 2  # Better performance, slight durability trade-off
innodb_flush_neighbors = 0          # Good for SSD, set to 1 for HDD
```

### I/O Monitoring

```bash
# Monitor InnoDB I/O statistics
mysql -u vedfolnir -p -e "
SELECT 
    VARIABLE_NAME,
    VARIABLE_VALUE
FROM performance_schema.global_status 
WHERE VARIABLE_NAME LIKE 'Innodb_data%'
   OR VARIABLE_NAME LIKE 'Innodb_log%'
   OR VARIABLE_NAME LIKE 'Innodb_pages%'
ORDER BY VARIABLE_NAME;
"

# Check for I/O bottlenecks
iostat -x 1 5

# Monitor disk usage
df -h /var/lib/mysql
du -sh /var/lib/mysql/vedfolnir/
```

## Troubleshooting Performance Issues

### Common Performance Problems

#### 1. High CPU Usage

**Diagnostic Steps:**
```bash
# Check MySQL process CPU usage
top -p $(pgrep mysqld)

# Identify CPU-intensive queries
mysql -u vedfolnir -p -e "
SELECT 
    id,
    user,
    host,
    db,
    command,
    time,
    state,
    LEFT(info, 100) as query_sample
FROM information_schema.processlist 
WHERE command != 'Sleep'
ORDER BY time DESC;
"

# Check for full table scans
mysql -u vedfolnir -p -e "
SELECT 
    'Full Table Scans' as metric,
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Select_scan') as value
UNION ALL
SELECT 
    'Full Joins',
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Select_full_join');
"
```

**Solutions:**
- Add missing indexes
- Optimize slow queries
- Increase InnoDB buffer pool size
- Consider query result caching

#### 2. High Memory Usage

**Diagnostic Steps:**
```bash
# Check MySQL memory usage
ps aux | grep mysqld | awk '{print $6/1024 " MB"}'

# Check buffer pool usage
mysql -u vedfolnir -p -e "
SELECT 
    ROUND(@@innodb_buffer_pool_size/1024/1024/1024, 2) as buffer_pool_gb,
    ROUND(
        (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_pages_data') *
        (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'innodb_page_size') / 1024 / 1024 / 1024, 2
    ) as data_in_buffer_gb;
"
```

**Solutions:**
- Reduce InnoDB buffer pool size if over-allocated
- Optimize temporary table settings
- Check for memory leaks in application code

#### 3. Slow Query Performance

**Diagnostic Steps:**
```bash
# Enable and check slow query log
mysql -u root -p -e "
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 1;
"

# Analyze slow queries
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log

# Check query execution plans
mysql -u vedfolnir -p vedfolnir -e "
EXPLAIN FORMAT=JSON 
SELECT * FROM posts p 
JOIN captions c ON p.id = c.post_id 
WHERE p.user_id = 1;
"
```

**Solutions:**
- Add appropriate indexes
- Rewrite inefficient queries
- Consider query result caching
- Optimize JOIN operations

This comprehensive performance tuning guide should help optimize MySQL performance for Vedfolnir deployments.
