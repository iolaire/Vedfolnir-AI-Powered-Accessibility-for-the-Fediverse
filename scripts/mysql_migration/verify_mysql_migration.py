#!/usr/bin/env python3
"""
MySQL Migration Verification Script
Verifies that the MySQL migration was successful and all systems are working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from sqlalchemy import create_engine, text
from config import Config
from app.core.database.core.database_manager import DatabaseManager
import redis

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_mysql_connection():
    """Verify MySQL connection and basic functionality"""
    try:
        config = Config()
        
        # Check if we're using MySQL
        if database_url.startswith("mysql+pymysql://"):
            logger.error("Database URL is not configured for MySQL")
            return False
        
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as session:
            # Test basic query
            result = session.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            logger.info(f"✓ MySQL connection successful. Version: {version}")
            
            # Test database name
            result = session.execute(text("SELECT DATABASE()"))
            db_name = result.fetchone()[0]
            logger.info(f"✓ Connected to database: {db_name}")
            
            # Test charset
            result = session.execute(text("SELECT @@character_set_database, @@collation_database"))
            charset, collation = result.fetchone()
            logger.info(f"✓ Database charset: {charset}, collation: {collation}")
            
        return True
    except Exception as e:
        logger.error(f"MySQL connection verification failed: {e}")
        return False

def verify_table_structure():
    """Verify all expected tables exist with correct structure"""
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        expected_tables = [
            'users', 'posts', 'images', 'platform_connections', 
            'user_sessions', 'processing_runs', 'user_audit_log',
            'gdpr_audit_log', 'caption_generation_tasks',
            'caption_generation_user_settings'
        ]
        
        with db_manager.get_session() as session:
            for table in expected_tables:
                result = session.execute(text(f"SHOW TABLES LIKE '{table}'"))
                if result.fetchone():
                    logger.info(f"✓ Table {table} exists")
                    
                    # Check table engine and charset
                    result = session.execute(text(f"""
                        SELECT ENGINE, TABLE_COLLATION 
                        FROM information_schema.TABLES 
                        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}'
                    """))
                    engine, collation = result.fetchone()
                    logger.info(f"  - Engine: {engine}, Collation: {collation}")
                else:
                    logger.error(f"✗ Table {table} missing")
                    return False
        
        return True
    except Exception as e:
        logger.error(f"Table structure verification failed: {e}")
        return False

def verify_redis_connection():
    """Verify Redis connection is still working (should be unchanged)"""
    try:
        config = Config()
        
        # Parse Redis URL
        redis_url = config.redis.url if hasattr(config, 'redis') else os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        # Connect to Redis
        r = redis.from_url(redis_url)
        
        # Test Redis connection
        r.ping()
        logger.info("✓ Redis connection successful")
        
        # Test basic operations
        test_key = "vedfolnir:migration:test"
        r.set(test_key, "test_value", ex=60)
        value = r.get(test_key)
        if value and value.decode() == "test_value":
            logger.info("✓ Redis read/write operations working")
            r.delete(test_key)
        else:
            logger.error("✗ Redis read/write operations failed")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Redis connection verification failed: {e}")
        return False

def verify_application_models():
    """Verify that SQLAlchemy models work with MySQL"""
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        from models import User, UserRole
        
        with db_manager.get_session() as session:
            # Test querying users (should work even if empty)
            users = session.query(User).limit(1).all()
            logger.info(f"✓ User model query successful (found {len(users)} users)")
            
            # Test enum handling
            admin_users = session.query(User).filter(User.role == UserRole.ADMIN).limit(1).all()
            logger.info(f"✓ Enum filtering works (found {len(admin_users)} admin users)")
        
        return True
    except Exception as e:
        logger.error(f"Application models verification failed: {e}")
        return False

def verify_foreign_keys():
    """Verify foreign key constraints are working"""
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as session:
            # Check foreign key constraints
            result = session.execute(text("""
                SELECT 
                    TABLE_NAME,
                    COLUMN_NAME,
                    CONSTRAINT_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE REFERENCED_TABLE_SCHEMA = DATABASE()
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """))
            
            fk_count = 0
            for row in result.fetchall():
                table, column, constraint, ref_table, ref_column = row
                logger.info(f"✓ FK: {table}.{column} -> {ref_table}.{ref_column}")
                fk_count += 1
            
            logger.info(f"✓ Found {fk_count} foreign key constraints")
        
        return True
    except Exception as e:
        logger.error(f"Foreign key verification failed: {e}")
        return False

def main():
    """Main verification process"""
    logger.info("Starting MySQL migration verification...")
    
    all_checks_passed = True
    
    # Check 1: MySQL Connection
    logger.info("\n1. Verifying MySQL connection...")
    if not verify_mysql_connection():
        all_checks_passed = False
    
    # Check 2: Table Structure
    logger.info("\n2. Verifying table structure...")
    if not verify_table_structure():
        all_checks_passed = False
    
    # Check 3: Redis Connection (should be unchanged)
    logger.info("\n3. Verifying Redis connection...")
    if not verify_redis_connection():
        all_checks_passed = False
    
    # Check 4: Application Models
    logger.info("\n4. Verifying application models...")
    if not verify_application_models():
        all_checks_passed = False
    
    # Check 5: Foreign Keys
    logger.info("\n5. Verifying foreign key constraints...")
    if not verify_foreign_keys():
        all_checks_passed = False
    
    # Summary
    logger.info("\n" + "="*50)
    if all_checks_passed:
        logger.info("✅ All verification checks PASSED!")
        logger.info("MySQL migration was successful.")
        logger.info("Your application is ready to use MySQL database.")
    else:
        logger.error("❌ Some verification checks FAILED!")
        logger.error("Please review the errors above and fix any issues.")
    
    return all_checks_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
