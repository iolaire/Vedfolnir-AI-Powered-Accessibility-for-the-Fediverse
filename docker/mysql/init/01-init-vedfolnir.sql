-- Copyright (C) 2025 iolaire mcfadden.
-- This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

-- MySQL initialization script for Vedfolnir Docker deployment
-- This script sets up the database with proper character sets and initial configuration

-- Ensure UTF8MB4 character set for proper Unicode support
ALTER DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create additional indexes for performance (will be created by SQLAlchemy migrations)
-- This is just a placeholder for any additional database setup needed

-- Set session variables for optimal performance
SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO';

-- Ensure proper time zone handling
SET SESSION time_zone = '+00:00';

-- Log initialization completion
SELECT 'Vedfolnir database initialization completed' AS status;