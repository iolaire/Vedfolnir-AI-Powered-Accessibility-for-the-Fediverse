#!/usr/bin/env python3
"""
MySQL Configuration Validation Script
Validates that the configuration changes for MySQL migration are working correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_mysql_config():
    """Validate MySQL configuration changes"""
    logger.info("Starting MySQL configuration validation...")
    
    try:
        # Load configuration
        config = Config()
        
        # Check default database URL
        logger.info(f"Default database URL: {config.storage.database_url}")
        
        if config.storage.database_url.startswith("mysql+pymysql://"):
            logger.info("✅ Default database URL is MySQL")
        else:
            logger.error("❌ Default database URL is not MySQL")
            return False
        
        # Check database configuration defaults
        db_config = config.storage.db_config
        logger.info(f"Database pool size: {db_config.pool_size}")
        logger.info(f"Database max overflow: {db_config.max_overflow}")
        logger.info(f"Database pool timeout: {db_config.pool_timeout}")
        logger.info(f"Database pool recycle: {db_config.pool_recycle}")
        
        # Validate MySQL-optimized defaults
        if db_config.pool_size >= 20:
            logger.info("✅ MySQL-optimized pool size")
        else:
            logger.warning("⚠️  Pool size may be too small for MySQL")
        
        if db_config.pool_recycle == 3600:
            logger.info("✅ MySQL-optimized pool recycle time")
        else:
            logger.warning("⚠️  Pool recycle time not optimized for MySQL")
        
        # Run configuration validation
        validation_errors = config.validate_configuration()
        
        if not validation_errors:
            logger.info("✅ Configuration validation passed")
        else:
            logger.error("❌ Configuration validation failed:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("✅ MySQL configuration validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration validation failed with exception: {e}")
        return False

def test_sqlite_deprecation_warning():
    """Test that SQLite URLs trigger deprecation warnings"""
    logger.info("Testing SQLite deprecation warning...")
    
    # Temporarily set SQLite URL to test validation
    original_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "MySQL database"
    
    try:
        config = Config()
        validation_errors = config.validate_configuration()
        
        # Check if SQLite deprecation error is present
        sqlite_error_found = any("SQLite is deprecated" in error for error in validation_errors)
        
        if sqlite_error_found:
            logger.info("✅ SQLite deprecation warning working correctly")
            result = True
        else:
            logger.error("❌ SQLite deprecation warning not triggered")
            result = False
            
    except Exception as e:
        logger.error(f"❌ SQLite deprecation test failed: {e}")
        result = False
    finally:
        # Restore original URL
        if original_url:
            os.environ["DATABASE_URL"] = original_url
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
    
    return result

if __name__ == "__main__":
    logger.info("=== MySQL Configuration Validation ===")
    
    success = True
    
    # Test 1: Validate MySQL configuration
    if not validate_mysql_config():
        success = False
    
    # Test 2: Test SQLite deprecation warning
    if not test_sqlite_deprecation_warning():
        success = False
    
    if success:
        logger.info("🎉 All MySQL configuration tests passed!")
        sys.exit(0)
    else:
        logger.error("💥 Some MySQL configuration tests failed!")
        sys.exit(1)
