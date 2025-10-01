-- Copyright (C) 2025 iolaire mcfadden.
-- This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

-- Create MySQL exporter user for Prometheus metrics collection
CREATE USER IF NOT EXISTS 'exporter'@'%' IDENTIFIED BY 'exporter_password_change_me';

-- Grant necessary privileges for metrics collection
GRANT PROCESS ON *.* TO 'exporter'@'%';
GRANT REPLICATION CLIENT ON *.* TO 'exporter'@'%';
GRANT SELECT ON performance_schema.* TO 'exporter'@'%';
GRANT SELECT ON information_schema.* TO 'exporter'@'%';
GRANT SELECT ON mysql.* TO 'exporter'@'%';

-- Grant specific privileges for detailed metrics
GRANT SELECT ON sys.* TO 'exporter'@'%';

-- Flush privileges to ensure changes take effect
FLUSH PRIVILEGES;