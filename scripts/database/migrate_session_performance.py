#!/usr/bin/env python3
"""Database migration for session performance optimization"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text, inspect
from config import Config
from app.core.database.core.database_manager import DatabaseManager

def migrate_session_performance():
    """Migrate database for session performance optimization"""
    config = Config()
    db_manager = DatabaseManager(config)
    
    print("Starting session performance migration...")
    
    with db_manager.get_session() as db_session:
        inspector = inspect(db_manager.engine)
        
        # Check if user_sessions table exists
        if 'user_sessions' not in inspector.get_table_names():
            print("UserSession table doesn't exist - creating tables...")
            from models import Base
            Base.metadata.create_all(db_manager.engine)
            print("Tables created successfully")
            return
        
        # Get current columns
        columns = inspector.get_columns('user_sessions')
        column_names = [col['name'] for col in columns]
        
        print(f"Current columns: {column_names}")
        
        # Check for required columns and add if missing
        required_columns = {
            'last_activity': 'ALTER TABLE user_sessions ADD COLUMN last_activity DATETIME',
            'expires_at': 'ALTER TABLE user_sessions ADD COLUMN expires_at DATETIME',
            'is_active': 'ALTER TABLE user_sessions ADD COLUMN is_active BOOLEAN DEFAULT 1'
        }
        
        for col_name, sql in required_columns.items():
            if col_name not in column_names:
                print(f"Adding missing column: {col_name}")
                try:
                    db_session.execute(text(sql))
                    db_session.commit()
                    print(f"Added column {col_name}")
                except Exception as e:
                    print(f"Error adding column {col_name}: {e}")
                    db_session.rollback()
        
        # Update expires_at and last_activity for existing sessions if null
        try:
            result = db_session.execute(text("""
                UPDATE user_sessions 
                SET expires_at = datetime(created_at, '+24 hours'),
                    last_activity = COALESCE(updated_at, created_at)
                WHERE expires_at IS NULL OR last_activity IS NULL
            """))
            if result.rowcount > 0:
                print(f"Updated expires_at and last_activity for {result.rowcount} existing sessions")
            db_session.commit()
        except Exception as e:
            print(f"Error updating session columns: {e}")
            db_session.rollback()
        
        # Apply performance optimizations
        try:
            from session_performance_optimizer import initialize_session_optimizations
            results = initialize_session_optimizations(db_manager)
            print(f"Performance optimizations applied: {results}")
        except Exception as e:
            print(f"Error applying performance optimizations: {e}")
    
    print("Session performance migration completed")

if __name__ == '__main__':
    migrate_session_performance()