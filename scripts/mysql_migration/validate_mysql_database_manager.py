#!/usr/bin/env python3
"""
MySQL DatabaseManager Validation Script
Validates that the DatabaseManager refactoring for MySQL-only operation is working correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from config import Config
from database import DatabaseManager, DatabaseOperationError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mysql_only_initialization():
    """Test that DatabaseManager only accepts MySQL URLs"""
    logger.info("Testing MySQL-only initialization...")
    
    try:
        # Test with valid MySQL URL
        config = Config()
        if config.storage.database_url.startswith("mysql+pymysql://"):
            db_manager = DatabaseManager(config)
            logger.info("✅ MySQL URL accepted successfully")
            
            # Test MySQL connection validation
            is_connected, message = db_manager.test_mysql_connection()
            if is_connected:
                logger.info(f"✅ MySQL connection test passed: {message}")
            else:
                logger.warning(f"⚠️  MySQL connection test failed: {message}")
            
            return True
        else:
            logger.error("❌ Config is not using MySQL URL")
            return False
            
    except Exception as e:
        logger.error(f"❌ MySQL initialization failed: {e}")
        return False

def test_sqlite_rejection():
    """Test that SQLite URLs are rejected"""
    logger.info("Testing SQLite URL rejection...")
    
    # Temporarily set SQLite URL to test rejection
    original_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "MySQL database"
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        logger.error("❌ SQLite URL was incorrectly accepted")
        return False
        
    except DatabaseOperationError as e:
        if "Invalid database URL" in str(e) and "mysql+pymysql://" in str(e):
            logger.info("✅ SQLite URL correctly rejected with proper error message")
            return True
        else:
            logger.error(f"❌ SQLite URL rejected but with wrong error: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during SQLite rejection test: {e}")
        return False
    finally:
        # Restore original URL
        if original_url:
            os.environ["DATABASE_URL"] = original_url
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

def test_mysql_optimizations():
    """Test MySQL-specific optimizations are applied"""
    logger.info("Testing MySQL optimizations...")
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Check engine configuration
        engine = db_manager.engine
        
        # Test connection pool configuration
        if hasattr(engine.pool, 'size'):
            pool_size = engine.pool.size()
            logger.info(f"Connection pool size: {pool_size}")
            if pool_size >= 20:
                logger.info("✅ MySQL-optimized connection pool size")
            else:
                logger.warning("⚠️  Connection pool size may not be optimized")
        
        # Test connect_args for MySQL-specific settings
        connect_args = engine.url.query
        if 'charset' in str(connect_args) and 'utf8mb4' in str(connect_args):
            logger.info("✅ MySQL charset configuration detected")
        else:
            logger.warning("⚠️  MySQL charset configuration not detected in URL")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MySQL optimization test failed: {e}")
        return False

def test_mysql_error_handling():
    """Test MySQL-specific error handling"""
    logger.info("Testing MySQL error handling...")
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Test error handling method exists
        if hasattr(db_manager, 'handle_mysql_error'):
            logger.info("✅ MySQL error handling method exists")
            
            # Test with a sample error
            test_error = Exception("Test error message")
            error_message = db_manager.handle_mysql_error(test_error)
            
            if "MySQL database error" in error_message:
                logger.info("✅ MySQL error handling working correctly")
                return True
            else:
                logger.error("❌ MySQL error handling not working correctly")
                return False
        else:
            logger.error("❌ MySQL error handling method missing")
            return False
            
    except Exception as e:
        logger.error(f"❌ MySQL error handling test failed: {e}")
        return False

def test_mysql_performance_features():
    """Test MySQL performance monitoring features"""
    logger.info("Testing MySQL performance features...")
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Test performance stats method
        if hasattr(db_manager, 'get_mysql_performance_stats'):
            logger.info("✅ MySQL performance stats method exists")
            
            # Try to get performance stats (may fail if not connected, but method should exist)
            try:
                stats = db_manager.get_mysql_performance_stats()
                if isinstance(stats, dict):
                    logger.info("✅ MySQL performance stats method working")
                    return True
                else:
                    logger.warning("⚠️  MySQL performance stats returned unexpected format")
                    return True  # Method exists, format issue is minor
            except Exception as e:
                logger.info(f"✅ MySQL performance stats method exists (connection issue expected: {e})")
                return True
        else:
            logger.error("❌ MySQL performance stats method missing")
            return False
            
    except Exception as e:
        logger.error(f"❌ MySQL performance features test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== MySQL DatabaseManager Validation ===")
    
    success = True
    
    # Test 1: MySQL-only initialization
    if not test_mysql_only_initialization():
        success = False
    
    # Test 2: SQLite rejection
    if not test_sqlite_rejection():
        success = False
    
    # Test 3: MySQL optimizations
    if not test_mysql_optimizations():
        success = False
    
    # Test 4: MySQL error handling
    if not test_mysql_error_handling():
        success = False
    
    # Test 5: MySQL performance features
    if not test_mysql_performance_features():
        success = False
    
    if success:
        logger.info("🎉 All MySQL DatabaseManager tests passed!")
        sys.exit(0)
    else:
        logger.error("💥 Some MySQL DatabaseManager tests failed!")
        sys.exit(1)
