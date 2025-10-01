-- Copyright (C) 2025 iolaire mcfadden.
-- This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

-- MySQL health check setup for Docker container monitoring
-- This script creates necessary components for comprehensive health monitoring

-- Create a dedicated health check user with minimal privileges
CREATE USER IF NOT EXISTS 'healthcheck'@'localhost' IDENTIFIED BY 'healthcheck_password';
GRANT PROCESS ON *.* TO 'healthcheck'@'localhost';
GRANT SELECT ON performance_schema.* TO 'healthcheck'@'localhost';
FLUSH PRIVILEGES;

-- Create a simple health check table for monitoring
USE vedfolnir;
CREATE TABLE IF NOT EXISTS health_check (
    id INT PRIMARY KEY AUTO_INCREMENT,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'healthy'
) ENGINE=InnoDB;

-- Insert initial health check record
INSERT INTO health_check (status) VALUES ('initialized');

-- Create a stored procedure for comprehensive health checks
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS CheckDatabaseHealth()
BEGIN
    DECLARE connection_count INT DEFAULT 0;
    DECLARE buffer_pool_hit_rate DECIMAL(5,2) DEFAULT 0.0;
    DECLARE health_status VARCHAR(20) DEFAULT 'healthy';
    
    -- Check connection count
    SELECT COUNT(*) INTO connection_count FROM information_schema.PROCESSLIST;
    
    -- Check buffer pool hit rate
    SELECT ROUND(
        (1 - (
            SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads'
        ) / (
            SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests'
        )) * 100, 2
    ) INTO buffer_pool_hit_rate;
    
    -- Determine health status
    IF connection_count > 180 OR buffer_pool_hit_rate < 95.0 THEN
        SET health_status = 'warning';
    END IF;
    
    IF connection_count > 190 OR buffer_pool_hit_rate < 90.0 THEN
        SET health_status = 'critical';
    END IF;
    
    -- Update health check table
    INSERT INTO health_check (status) VALUES (health_status);
    
    -- Return health information
    SELECT 
        health_status as status,
        connection_count as active_connections,
        buffer_pool_hit_rate as buffer_pool_hit_rate_percent,
        NOW() as check_time;
END //
DELIMITER ;

-- Log health check setup completion
SELECT 'MySQL health check setup completed' AS status;