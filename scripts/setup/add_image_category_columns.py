# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import sys
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_columns():
    """Add image category and prompt columns to the images table in MySQL"""
    config = Config()
    database_url = config.storage.database_url
    
    if not database_url.startswith("mysql+pymysql://"):
        logger.error("This script requires a MySQL database URL")
        return False
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Check which columns already exist
            result = connection.execute(text("""
                SELECT COLUMN_NAME FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'images'
            """))
            
            existing_columns = {row[0] for row in result}
            
            columns_to_add = {
                'image_category': 'VARCHAR(100)',
                'generation_prompt': 'TEXT',
                'confidence_score': 'DECIMAL(5,4)',
                'processing_metadata': 'JSON'
            }
            
            added_columns = []
            for column_name, column_type in columns_to_add.items():
                if column_name not in existing_columns:
                    try:
                        connection.execute(text(f"""
                            ALTER TABLE images ADD COLUMN {column_name} {column_type}
                        """))
                        added_columns.append(column_name)
                        logger.info(f"Added column: {column_name}")
                    except SQLAlchemyError as e:
                        logger.error(f"Failed to add column {column_name}: {e}")
                        return False
                else:
                    logger.info(f"Column {column_name} already exists")
            
            # Create indexes for new columns
            if 'image_category' in added_columns:
                try:
                    connection.execute(text("""
                        CREATE INDEX idx_images_category ON images(image_category)
                    """))
                    logger.info("Created index for image_category")
                except SQLAlchemyError as e:
                    logger.warning(f"Could not create index for image_category: {e}")
            
            if 'confidence_score' in added_columns:
                try:
                    connection.execute(text("""
                        CREATE INDEX idx_images_confidence ON images(confidence_score)
                    """))
                    logger.info("Created index for confidence_score")
                except SQLAlchemyError as e:
                    logger.warning(f"Could not create index for confidence_score: {e}")
            
            connection.commit()
            logger.info("Successfully added image category columns to MySQL database")
            return True
            
    except Exception as e:
        logger.error(f"Error adding columns: {e}")
        return False

if __name__ == "__main__":
    success = add_columns()
    if success:
        logger.info("Column addition completed successfully")
    else:
        logger.error("Column addition failed")
        sys.exit(1)
