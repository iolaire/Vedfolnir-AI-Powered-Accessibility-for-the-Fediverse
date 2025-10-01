-- Copyright (C) 2025 iolaire mcfadden.
-- This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

-- MySQL performance optimization for Vedfolnir Docker deployment
-- This script applies container-specific optimizations and creates performance monitoring views

USE vedfolnir;

-- Create performance monitoring views for easier access to metrics
CREATE OR REPLACE VIEW performance_summary AS
SELECT 
    'Buffer Pool Hit Rate' as metric,
    CONCAT(
        ROUND(
            (1 - (
                SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads'
            ) / NULLIF((
                SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests'
            ), 0)) * 100, 2
        ), '%'
    ) as value,
    CASE 
        WHEN (1 - (
            SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads'
        ) / NULLIF((
            SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests'
        ), 0)) * 100 >= 99 THEN 'Excellent'
        WHEN (1 - (
            SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads'
        ) / NULLIF((
            SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests'
        ), 0)) * 100 >= 95 THEN 'Good'
        ELSE 'Needs Attention'
    END as status

UNION ALL

SELECT 
    'Connection Usage' as metric,
    CONCAT(
        (SELECT COUNT(*) FROM information_schema.PROCESSLIST), 
        ' / ', 
        (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections'),
        ' (',
        ROUND(
            (SELECT COUNT(*) FROM information_schema.PROCESSLIST) / 
            (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections') * 100, 1
        ),
        '%)'
    ) as value,
    CASE 
        WHEN (SELECT COUNT(*) FROM information_schema.PROCESSLIST) / 
             (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections') * 100 < 70 THEN 'Good'
        WHEN (SELECT COUNT(*) FROM information_schema.PROCESSLIST) / 
             (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections') * 100 < 85 THEN 'Warning'
        ELSE 'Critical'
    END as status

UNION ALL

SELECT 
    'Slow Query Rate' as metric,
    CONCAT(
        ROUND(
            (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Slow_queries') / 
            NULLIF((SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Questions'), 0) * 100, 4
        ), '%'
    ) as value,
    CASE 
        WHEN (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Slow_queries') / 
             NULLIF((SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Questions'), 0) * 100 < 1 THEN 'Good'
        WHEN (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Slow_queries') / 
             NULLIF((SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Questions'), 0) * 100 < 5 THEN 'Warning'
        ELSE 'Critical'
    END as status;

-- Create a view for current active connections
CREATE OR REPLACE VIEW active_connections AS
SELECT 
    ID,
    USER,
    HOST,
    DB,
    COMMAND,
    TIME,
    STATE,
    LEFT(COALESCE(INFO, ''), 100) as QUERY_PREVIEW
FROM information_schema.PROCESSLIST 
WHERE COMMAND != 'Sleep'
ORDER BY TIME DESC;

-- Create a view for database size information
CREATE OR REPLACE VIEW database_size_info AS
SELECT 
    table_schema as 'Database',
    COUNT(*) as 'Tables',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as 'Size_MB',
    ROUND(SUM(data_length) / 1024 / 1024, 2) as 'Data_MB',
    ROUND(SUM(index_length) / 1024 / 1024, 2) as 'Index_MB'
FROM information_schema.tables 
WHERE table_schema = 'vedfolnir'
GROUP BY table_schema;

-- Create a view for table size information
CREATE OR REPLACE VIEW table_size_info AS
SELECT 
    table_name as 'Table',
    table_rows as 'Rows',
    ROUND((data_length + index_length) / 1024 / 1024, 2) as 'Total_MB',
    ROUND(data_length / 1024 / 1024, 2) as 'Data_MB',
    ROUND(index_length / 1024 / 1024, 2) as 'Index_MB',
    ROUND(index_length / NULLIF(data_length, 0) * 100, 1) as 'Index_Ratio_%'
FROM information_schema.tables 
WHERE table_schema = 'vedfolnir'
ORDER BY (data_length + index_length) DESC;

-- Create indexes for common query patterns (if tables exist)
-- Note: These will be created by SQLAlchemy migrations, but we can add additional performance indexes

-- Create a stored procedure for quick performance check
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS QuickPerformanceCheck()
BEGIN
    SELECT 'Vedfolnir MySQL Performance Summary' as title;
    SELECT * FROM performance_summary;
    
    SELECT 'Current Active Connections' as title;
    SELECT COUNT(*) as active_connections FROM active_connections;
    
    SELECT 'Database Size' as title;
    SELECT * FROM database_size_info;
    
    SELECT 'Top 5 Largest Tables' as title;
    SELECT * FROM table_size_info LIMIT 5;
END //
DELIMITER ;

-- Create a stored procedure for container health monitoring
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS ContainerHealthCheck()
BEGIN
    DECLARE health_score INT DEFAULT 100;
    DECLARE health_status VARCHAR(20) DEFAULT 'healthy';
    DECLARE buffer_hit_rate DECIMAL(5,2);
    DECLARE connection_usage DECIMAL(5,2);
    DECLARE slow_query_rate DECIMAL(5,4);
    
    -- Calculate buffer pool hit rate
    SELECT (1 - (
        SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads'
    ) / NULLIF((
        SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests'
    ), 0)) * 100 INTO buffer_hit_rate;
    
    -- Calculate connection usage
    SELECT (COUNT(*) / (
        SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections'
    )) * 100 INTO connection_usage FROM information_schema.PROCESSLIST;
    
    -- Calculate slow query rate
    SELECT (
        SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Slow_queries'
    ) / NULLIF((
        SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Questions'
    ), 0) * 100 INTO slow_query_rate;
    
    -- Adjust health score based on metrics
    IF buffer_hit_rate < 95 THEN
        SET health_score = health_score - 20;
    END IF;
    
    IF connection_usage > 85 THEN
        SET health_score = health_score - 30;
    END IF;
    
    IF slow_query_rate > 5 THEN
        SET health_score = health_score - 25;
    END IF;
    
    -- Determine health status
    IF health_score >= 90 THEN
        SET health_status = 'excellent';
    ELSEIF health_score >= 70 THEN
        SET health_status = 'good';
    ELSEIF health_score >= 50 THEN
        SET health_status = 'warning';
    ELSE
        SET health_status = 'critical';
    END IF;
    
    -- Update health check table
    INSERT INTO health_check (status) VALUES (health_status);
    
    -- Return health summary
    SELECT 
        health_status as overall_status,
        health_score as health_score,
        buffer_hit_rate as buffer_pool_hit_rate,
        connection_usage as connection_usage_percent,
        slow_query_rate as slow_query_rate_percent,
        NOW() as check_time;
END //
DELIMITER ;

-- Set optimal session variables for the container environment
SET GLOBAL innodb_adaptive_hash_index = ON;
SET GLOBAL innodb_adaptive_flushing = ON;
SET GLOBAL innodb_change_buffering = all;
SET GLOBAL innodb_old_blocks_time = 1000;

-- Enable query cache if available (MySQL 5.7 and earlier)
-- SET GLOBAL query_cache_type = ON;
-- SET GLOBAL query_cache_size = 268435456; -- 256MB

-- Optimize for containerized environment
SET GLOBAL innodb_flush_neighbors = 0; -- Good for SSD storage
SET GLOBAL innodb_random_read_ahead = OFF;
SET GLOBAL innodb_read_ahead_threshold = 56;

-- Log performance optimization completion
INSERT INTO health_check (status) VALUES ('performance_optimized');

SELECT 'MySQL performance optimization completed for Docker container' AS status;