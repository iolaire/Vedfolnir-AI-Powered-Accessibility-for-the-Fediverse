#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Database migration script to add original_post_date column to images table.

This script adds a new column to store the original Pixelfed post creation date,
which will be used for proper chronological sorting in the review interfaces.
"""

import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager

def migrate_database():
    """Add original_post_date column to images table"""
    print("Starting database migration: Adding original_post_date column")
    
    try:
        # Load configuration
        config = Config()
        
        # Create engine directly for migration
        engine = create_engine(config.storage.database_url)
        
        with engine.connect() as connection:
            # Check if column already exists
            try:
                result = connection.execute(text("SELECT original_post_date FROM images LIMIT 1"))
                print("Column original_post_date already exists, skipping migration")
                return True
            except SQLAlchemyError:
                # Column doesn't exist, proceed with migration
                pass
            
            # Add the new column
            print("Adding original_post_date column to images table...")
            connection.execute(text("ALTER TABLE images ADD COLUMN original_post_date DATETIME"))
            connection.commit()
            
            print("✓ Successfully added original_post_date column")
            
            # Optional: Update existing records with a default value based on created_at
            print("Updating existing records with default values...")
            connection.execute(text("""
                UPDATE images 
                SET original_post_date = created_at 
                WHERE original_post_date IS NULL
            """))
            connection.commit()
            
            print("✓ Updated existing records with default values")
            print("✓ Migration completed successfully")
            
            return True
            
    except SQLAlchemyError as e:
        print(f"❌ Database migration failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during migration: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful"""
    print("\nVerifying migration...")
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        session = db_manager.get_session()
        try:
            # Try to query the new column
            result = session.execute(text("SELECT COUNT(*) as count FROM images WHERE original_post_date IS NOT NULL"))
            count = result.fetchone()[0]
            print(f"✓ Found {count} images with original_post_date values")
            
            # Test that we can query with the new column
            result = session.execute(text("SELECT id, original_post_date FROM images LIMIT 3"))
            rows = result.fetchall()
            
            print("Sample records:")
            for row in rows:
                print(f"  Image {row[0]}: original_post_date = {row[1]}")
            
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        return False

if __name__ == "__main__":
    print("Vedfolnir Database Migration")
    print("=" * 40)
    
    # Run migration
    if migrate_database():
        # Verify migration
        if verify_migration():
            print("\n🎉 Migration completed successfully!")
            print("\nNext steps:")
            print("1. The original_post_date column has been added")
            print("2. Existing records have been populated with created_at values")
            print("3. New images will get proper Pixelfed post dates when processed")
            print("4. Review interfaces will now sort by original post date")
        else:
            print("\n⚠️  Migration completed but verification failed")
            sys.exit(1)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)