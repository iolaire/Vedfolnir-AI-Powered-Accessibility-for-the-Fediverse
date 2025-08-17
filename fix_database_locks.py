#!/usr/bin/env python3
"""
Fix database lock issues by adjusting SQLite configuration and connection management.
"""

import os
import sqlite3
import logging
from pathlib import Path

def fix_database_locks():
    """Fix database lock issues by optimizing SQLite configuration"""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Database path
    db_path = "storage/database/vedfolnir.db"
    
    if not os.path.exists(db_path):
        logger.info("Database file does not exist, no locks to fix")
        return
    
    logger.info(f"Fixing database locks for {db_path}")
    
    try:
        # Connect to database with optimized settings
        conn = sqlite3.connect(
            db_path,
            timeout=30.0,  # 30 second timeout
            isolation_level=None,  # Autocommit mode
            check_same_thread=False
        )
        
        # Set SQLite pragmas for better concurrency
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Set busy timeout
        cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds
        
        # Optimize synchronous mode
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Set cache size
        cursor.execute("PRAGMA cache_size=10000")
        
        # Set temp store to memory
        cursor.execute("PRAGMA temp_store=MEMORY")
        
        # Set locking mode to normal (not exclusive)
        cursor.execute("PRAGMA locking_mode=NORMAL")
        
        # Commit changes
        conn.commit()
        
        logger.info("Database configuration optimized for concurrency")
        
        # Close connection
        cursor.close()
        conn.close()
        
        logger.info("Database locks fixed successfully")
        
    except Exception as e:
        logger.error(f"Error fixing database locks: {e}")
        raise

if __name__ == "__main__":
    fix_database_locks()