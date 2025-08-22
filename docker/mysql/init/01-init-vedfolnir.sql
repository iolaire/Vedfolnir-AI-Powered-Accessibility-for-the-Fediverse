-- MySQL initialization script for Vedfolnir Docker deployment
-- This replaces any SQLite-based database initialization

-- Ensure proper character set and collation for the database
ALTER DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant additional privileges to the vedfolnir user
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir'@'%';

-- Create indexes for better performance (these will be created by the application if they don't exist)
-- The application's init_db() function will handle table creation

-- Flush privileges to ensure changes take effect
FLUSH PRIVILEGES;

-- Log the initialization
SELECT 'Vedfolnir MySQL database initialized successfully' AS message;
