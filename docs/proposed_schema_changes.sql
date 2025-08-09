-- Copyright (C) 2025 iolaire mcfadden.
-- This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
-- Proposed database schema changes for multi-platform support

-- Add platform identification to posts table
ALTER TABLE posts ADD COLUMN platform_type VARCHAR(50) DEFAULT 'pixelfed';
ALTER TABLE posts ADD COLUMN instance_url VARCHAR(500);

-- Add platform identification to images table  
ALTER TABLE images ADD COLUMN platform_type VARCHAR(50) DEFAULT 'pixelfed';

-- Add platform identification to processing runs
ALTER TABLE processing_runs ADD COLUMN platform_type VARCHAR(50) DEFAULT 'pixelfed';
ALTER TABLE processing_runs ADD COLUMN instance_url VARCHAR(500);

-- Create indexes for efficient platform-based queries
CREATE INDEX idx_posts_platform ON posts(platform_type);
CREATE INDEX idx_images_platform ON images(platform_type);
CREATE INDEX idx_processing_runs_platform ON processing_runs(platform_type);

-- Example of how data would look:
-- posts: id=1, post_id="123", platform_type="pixelfed", instance_url="https://pixelfed.social"
-- posts: id=2, post_id="456", platform_type="mastodon", instance_url="https://mastodon.social"