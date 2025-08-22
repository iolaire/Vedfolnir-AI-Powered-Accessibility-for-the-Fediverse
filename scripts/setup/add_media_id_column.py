# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config import Config

def add_media_id_column():
    """Add media_id column to images table in MySQL database"""
    
    config = Config()
    database_url = config.storage.database_url
    
    if not database_url.startswith("mysql+pymysql://"):
        raise ValueError("This script requires a MySQL database URL")
    
    print(f"Adding media_id column to images table in MySQL database")
    
    engine = create_engine(database_url)
    
    with engine.connect() as connection:
        try:
            # Check if media_id column already exists
            result = connection.execute(text("""
                SELECT COUNT(*) FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'images' 
                AND COLUMN_NAME = 'media_id'
            """))
            
            column_exists = result.fetchone()[0] > 0
            
            if not column_exists:
                # Add the media_id column
                connection.execute(text("""
                    ALTER TABLE images 
                    ADD COLUMN media_id VARCHAR(255)
                """))
                
                # Create index for better performance
                connection.execute(text("""
                    CREATE INDEX idx_images_media_id ON images(media_id)
                """))
                
                connection.commit()
                print("Successfully added media_id column and index to images table")
            else:
                print("media_id column already exists in images table")
                
        except SQLAlchemyError as e:
            print(f"Error adding media_id column: {e}")
            connection.rollback()
            raise

if __name__ == "__main__":
    add_media_id_column()
