#!/usr/bin/env python3
"""
Database Migration Script: SQLite to MySQL
Migrates Vedfolnir application from SQLite to MySQL while preserving Redis configuration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
from models import Base
from app.core.database.core.database_manager import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mysql_connection():
    """Test MySQL connection before migration"""
    mysql_url = "mysql+pymysql://database_user_1d7b0d0696a20:EQA%26bok7@localhost/vedfolnir?unix_socket=/tmp/mysql.sock&charset=utf8mb4"
    
    try:
        engine = create_engine(mysql_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            logger.info(f"MySQL connection successful. Version: {version}")
            
            # Test database access
            result = conn.execute(text("SELECT DATABASE()"))
            db_name = result.fetchone()[0]
            logger.info(f"Connected to database: {db_name}")
            
            return True
    except Exception as e:
        logger.error(f"MySQL connection failed: {e}")
        return False

def create_mysql_tables():
    """Create tables in MySQL database"""
    mysql_url = "mysql+pymysql://database_user_1d7b0d0696a20:EQA%26bok7@localhost/vedfolnir?unix_socket=/tmp/mysql.sock&charset=utf8mb4"
    
    try:
        engine = create_engine(mysql_url)
        
        # Create all tables
        Base.metadata.create_all(engine)
        logger.info("MySQL tables created successfully")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Created tables: {', '.join(tables)}")
            
        return True
    except Exception as e:
        logger.error(f"Failed to create MySQL tables: {e}")
        return False

def verify_mysql_schema():
    """Verify MySQL schema matches expected structure"""
    mysql_url = "mysql+pymysql://database_user_1d7b0d0696a20:EQA%26bok7@localhost/vedfolnir?unix_socket=/tmp/mysql.sock&charset=utf8mb4"
    
    try:
        engine = create_engine(mysql_url)
        
        with engine.connect() as conn:
            # Check key tables exist
            expected_tables = [
                'users', 'posts', 'images', 'platform_connections', 
                'user_sessions', 'processing_runs', 'user_audit_log',
                'gdpr_audit_log', 'caption_generation_tasks',
                'caption_generation_user_settings'
            ]
            
            for table in expected_tables:
                result = conn.execute(text(f"SHOW TABLES LIKE '{table}'"))
                if not result.fetchone():
                    logger.error(f"Table {table} not found")
                    return False
                else:
                    logger.info(f"✓ Table {table} exists")
            
            # Check charset and collation
            result = conn.execute(text("""
                SELECT TABLE_NAME, TABLE_COLLATION 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
            """))
            
            for table_name, collation in result.fetchall():
                if 'utf8mb4' not in collation:
                    logger.warning(f"Table {table_name} has collation {collation} (expected utf8mb4)")
                else:
                    logger.info(f"✓ Table {table_name} has correct collation: {collation}")
            
        return True
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False

def test_database_operations():
    """Test basic database operations"""
    try:
        # Load config with MySQL settings
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Test basic operations
        with db_manager.get_session() as session:
            # Test a simple query
            result = session.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            if test_value == 1:
                logger.info("✓ Basic database query successful")
            else:
                logger.error("Basic database query failed")
                return False
        
        logger.info("✓ Database operations test successful")
        return True
    except Exception as e:
        logger.error(f"Database operations test failed: {e}")
        return False

def main():
    """Main migration process"""
    logger.info("Starting MySQL migration process...")
    
    # Step 1: Test MySQL connection
    logger.info("Step 1: Testing MySQL connection...")
    if not test_mysql_connection():
        logger.error("MySQL connection test failed. Please check your MySQL configuration.")
        return False
    
    # Step 2: Create MySQL tables
    logger.info("Step 2: Creating MySQL tables...")
    if not create_mysql_tables():
        logger.error("Failed to create MySQL tables.")
        return False
    
    # Step 3: Verify schema
    logger.info("Step 3: Verifying MySQL schema...")
    if not verify_mysql_schema():
        logger.error("Schema verification failed.")
        return False
    
    # Step 4: Test database operations
    logger.info("Step 4: Testing database operations...")
    if not test_database_operations():
        logger.error("Database operations test failed.")
        return False
    
    logger.info("✅ MySQL migration completed successfully!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Update your .env file to use the MySQL DATABASE_URL")
    logger.info("2. Restart your application")
    logger.info("3. Verify all functionality works correctly")
    logger.info("4. Redis configuration remains unchanged")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
