# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import os
import sys
import sqlite3
import logging
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_columns():
    """Add image category and prompt columns to the images table"""
    config = Config()
    db_path = config.storage.database_url.replace('sqlite:///', '')
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(images)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add image_category column if it doesn't exist
        if 'image_category' not in columns:
            logger.info("Adding image_category column to images table")
            cursor.execute("ALTER TABLE images ADD COLUMN image_category VARCHAR(50)")
        else:
            logger.info("image_category column already exists")
        
        # Add prompt_used column if it doesn't exist
        if 'prompt_used' not in columns:
            logger.info("Adding prompt_used column to images table")
            cursor.execute("ALTER TABLE images ADD COLUMN prompt_used TEXT")
        else:
            logger.info("prompt_used column already exists")
        
        # Add caption_quality_score column if it doesn't exist
        if 'caption_quality_score' not in columns:
            logger.info("Adding caption_quality_score column to images table")
            cursor.execute("ALTER TABLE images ADD COLUMN caption_quality_score INTEGER")
        else:
            logger.info("caption_quality_score column already exists")
        
        # Add needs_special_review column if it doesn't exist
        if 'needs_special_review' not in columns:
            logger.info("Adding needs_special_review column to images table")
            cursor.execute("ALTER TABLE images ADD COLUMN needs_special_review BOOLEAN DEFAULT 0")
        else:
            logger.info("needs_special_review column already exists")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info("Database migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error adding columns to database: {e}")
        return False

if __name__ == "__main__":
    success = add_columns()
    sys.exit(0 if success else 1)