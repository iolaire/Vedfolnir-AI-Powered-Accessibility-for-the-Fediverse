#!/usr/bin/env python3

"""
Test to diagnose the database manager issue in Flask app vs tests
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager

def test_database_manager_initialization():
    """Test how the database manager is initialized"""
    
    print("=== Database Manager Initialization Test ===")
    
    # Test 1: Create config and database manager like the Flask app does
    print("\n1. Testing Flask app initialization pattern:")
    try:
        config = Config()
        db_manager = self.get_database_manager()
        print(f"✓ Config created: {type(config)}")
        print(f"✓ DatabaseManager created: {type(db_manager)}")
        print(f"✓ Database URL: {config.storage.database_url}")
        
        # Test getting a session
        session = db_manager.get_session()
        print(f"✓ Session created: {type(session)}")
        session.close()
        
    except Exception as e:
        print(f"✗ Error in Flask app pattern: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Check if the database manager has the expected methods
    print("\n2. Testing DatabaseManager methods:")
    try:
        expected_methods = [
            'get_session', 'close_session', 'create_tables',
            'get_or_create_post', 'save_image', 'update_image_caption',
            'get_pending_images', 'review_image', 'mark_image_posted'
        ]
        
        for method in expected_methods:
            if hasattr(db_manager, method):
                print(f"✓ Method {method} exists")
            else:
                print(f"✗ Method {method} missing")
                
    except Exception as e:
        print(f"✗ Error checking methods: {e}")
    
    # Test 3: Check database connection
    print("\n3. Testing database connection:")
    try:
        session = db_manager.get_session()
        # Try a simple query
        from sqlalchemy import text
        result = session.execute(text("SELECT 1")).scalar()
        print(f"✓ Database connection works: {result}")
        session.close()
        
    except Exception as e:
        print(f"✗ Database connection error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Check if tables exist
    print("\n4. Testing table creation:")
    try:
        from models import Base
        from sqlalchemy import inspect
        
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()
        print(f"✓ Tables in database: {tables}")
        
        # Check for expected tables
        expected_tables = ['users', 'platform_connections', 'posts', 'images', 'processing_runs']
        for table in expected_tables:
            if table in tables:
                print(f"✓ Table {table} exists")
            else:
                print(f"? Table {table} not found (might be created on demand)")
                
    except Exception as e:
        print(f"✗ Error checking tables: {e}")
        import traceback

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures

        traceback.print_exc()

if __name__ == "__main__":
    test_database_manager_initialization()