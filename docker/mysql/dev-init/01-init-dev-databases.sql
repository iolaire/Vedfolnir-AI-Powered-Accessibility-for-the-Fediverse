-- MySQL development initialization script for Vedfolnir
-- Creates development and test databases

-- Create test database for development environment
CREATE DATABASE IF NOT EXISTS vedfolnir_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create test user
CREATE USER IF NOT EXISTS 'vedfolnir_test'@'%' IDENTIFIED BY 'test_password';
GRANT ALL PRIVILEGES ON vedfolnir_test.* TO 'vedfolnir_test'@'%';

-- Ensure proper character set and collation for development database
ALTER DATABASE vedfolnir_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant additional privileges to development users
GRANT ALL PRIVILEGES ON vedfolnir_dev.* TO 'vedfolnir_dev'@'%';
GRANT ALL PRIVILEGES ON vedfolnir_test.* TO 'vedfolnir_dev'@'%';

-- Allow development user to create/drop databases for testing
GRANT CREATE, DROP ON *.* TO 'vedfolnir_dev'@'%';

-- Flush privileges
FLUSH PRIVILEGES;

-- Log the initialization
SELECT 'Vedfolnir development MySQL databases initialized successfully' AS message;
