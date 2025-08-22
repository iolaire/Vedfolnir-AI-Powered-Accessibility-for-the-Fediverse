#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Migration script to add batch_id column to processing_runs table
"""

import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def add_batch_id_column():
    """Add batch_id column to processing_runs table in MySQL"""
    config = Config()
    database_url = config.storage.database_url
    
    if not database_url.startswith("mysql+pymysql://"):
        logger.error("This script requires a MySQL database URL")
        return False
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Check if batch_id column already exists
            result = connection.execute(text("""
                SELECT COUNT(*) FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'processing_runs' 
                AND COLUMN_NAME = 'batch_id'
            """))
            
            column_exists = result.fetchone()[0] > 0
            
            if not column_exists:
                logger.info("Adding batch_id column to processing_runs table")
                
                # Add the batch_id column
                connection.execute(text("""
                    ALTER TABLE processing_runs 
                    ADD COLUMN batch_id VARCHAR(255)
                """))
                
                # Create index for better performance
                connection.execute(text("""
                    CREATE INDEX idx_processing_runs_batch_id ON processing_runs(batch_id)
                """))
                
                connection.commit()
                logger.info("Successfully added batch_id column and index to processing_runs table")
                return True
            else:
                logger.info("batch_id column already exists in processing_runs table")
                return True
                
    except SQLAlchemyError as e:
        logger.error(f"Error adding batch_id column: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = add_batch_id_column()
    if success:
        logger.info("Batch ID column addition completed successfully")
    else:
        logger.error("Batch ID column addition failed")
        sys.exit(1)
