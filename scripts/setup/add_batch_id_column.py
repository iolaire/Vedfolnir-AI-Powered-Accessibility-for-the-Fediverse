#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Migration script to add batch_id column to processing_runs table
"""

import logging
import sqlite3
import os
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def add_batch_id_column():
    """Add batch_id column to processing_runs table"""
    config = Config()
    db_path = config.storage.database_url.replace('sqlite:///', '')
    
    # Check if the database file exists
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the columns already exist
        cursor.execute("PRAGMA table_info(processing_runs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add the batch_id column if it doesn't exist
        if 'batch_id' not in columns:
            logger.info("Adding batch_id column to processing_runs table")
            cursor.execute("ALTER TABLE processing_runs ADD COLUMN batch_id TEXT")
        else:
            logger.info("batch_id column already exists in processing_runs table")
        
        # Add the retry_attempts column if it doesn't exist
        if 'retry_attempts' not in columns:
            logger.info("Adding retry_attempts column to processing_runs table")
            cursor.execute("ALTER TABLE processing_runs ADD COLUMN retry_attempts INTEGER DEFAULT 0")
        else:
            logger.info("retry_attempts column already exists in processing_runs table")
        
        # Add the retry_successes column if it doesn't exist
        if 'retry_successes' not in columns:
            logger.info("Adding retry_successes column to processing_runs table")
            cursor.execute("ALTER TABLE processing_runs ADD COLUMN retry_successes INTEGER DEFAULT 0")
        else:
            logger.info("retry_successes column already exists in processing_runs table")
        
        # Add the retry_failures column if it doesn't exist
        if 'retry_failures' not in columns:
            logger.info("Adding retry_failures column to processing_runs table")
            cursor.execute("ALTER TABLE processing_runs ADD COLUMN retry_failures INTEGER DEFAULT 0")
        else:
            logger.info("retry_failures column already exists in processing_runs table")
        
        # Add the retry_total_time column if it doesn't exist
        if 'retry_total_time' not in columns:
            logger.info("Adding retry_total_time column to processing_runs table")
            cursor.execute("ALTER TABLE processing_runs ADD COLUMN retry_total_time INTEGER DEFAULT 0")
        else:
            logger.info("retry_total_time column already exists in processing_runs table")
        
        # Add the retry_stats_json column if it doesn't exist
        if 'retry_stats_json' not in columns:
            logger.info("Adding retry_stats_json column to processing_runs table")
            cursor.execute("ALTER TABLE processing_runs ADD COLUMN retry_stats_json TEXT")
        else:
            logger.info("retry_stats_json column already exists in processing_runs table")
        
        # Commit the changes
        conn.commit()
        conn.close()
        
        logger.info("Successfully updated processing_runs table")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error adding batch_id column: {e}")
        return False

if __name__ == "__main__":
    success = add_batch_id_column()
    if success:
        print("Migration completed successfully")
    else:
        print("Migration failed")
        exit(1)