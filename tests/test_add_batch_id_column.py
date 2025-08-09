# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import unittest
import os
import sqlite3
import tempfile
import shutil
from unittest.mock import patch

# Import the migration function
from add_batch_id_column import add_batch_id_column

class TestAddBatchIdColumn(unittest.TestCase):
    """Test the add_batch_id_column migration script"""
    
    def setUp(self):
        """Set up a test database"""
        # Create a temporary directory for the test database
        self.temp_dir = tempfile.mkdtemp()
        self.db_dir = os.path.join(self.temp_dir, "storage", "database")
        os.makedirs(self.db_dir, exist_ok=True)
        
        # Create a test database file
        self.db_path = os.path.join(self.db_dir, "vedfolnir.db")
        
        # Create a connection to the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create the processing_runs table without the batch_id column
        cursor.execute('''
        CREATE TABLE processing_runs (
            id INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            posts_processed INTEGER DEFAULT 0,
            images_processed INTEGER DEFAULT 0,
            captions_generated INTEGER DEFAULT 0,
            errors_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running'
        )
        ''')
        
        # Insert some test data
        cursor.execute('''
        INSERT INTO processing_runs (user_id, status)
        VALUES ('test_user', 'completed')
        ''')
        
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up after the test"""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.temp_dir)
    
    def test_add_batch_id_column(self):
        """Test that the batch_id column is added to the processing_runs table"""
        # Patch the database path in the add_batch_id_column function
        with patch('add_batch_id_column.db_path', self.db_path):
            # Run the migration
            result = add_batch_id_column()
            
            # Check that the migration was successful
            self.assertTrue(result)
            
            # Verify that the column was added
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(processing_runs)")
            columns = [column[1] for column in cursor.fetchall()]
            conn.close()
            
            # Check that the batch_id column exists
            self.assertIn("batch_id", columns)
    
    def test_column_already_exists(self):
        """Test the case where the batch_id column already exists"""
        # First, add the column
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE processing_runs ADD COLUMN batch_id TEXT")
        conn.commit()
        conn.close()
        
        # Now run the migration again with our test database path
        with patch('add_batch_id_column.db_path', self.db_path):
            result = add_batch_id_column()
        
        # Check that the migration was successful
        self.assertTrue(result)
    
    def test_database_not_found(self):
        """Test the case where the database file doesn't exist"""
        # Use a non-existent path
        non_existent_path = os.path.join(self.temp_dir, "non_existent.db")
        
        # Run the migration with the non-existent path
        with patch('add_batch_id_column.db_path', non_existent_path):
            result = add_batch_id_column()
        
        # Check that the migration failed
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()