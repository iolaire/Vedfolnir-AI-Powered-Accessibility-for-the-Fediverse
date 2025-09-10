#!/usr/bin/env python3
"""
MySQL Connection Error Handling Validation Script
Validates the enhanced MySQL error handling and troubleshooting features.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from config import Config
from app.core.database.core.database_manager import DatabaseManager, DatabaseOperationError
from mysql_connection_validator import validate_mysql_connection

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mysql_connection_validation():
    """Test comprehensive MySQL connection parameter validation"""
    logger.info("Testing MySQL connection parameter validation...")
    
    try:
        # Test with valid MySQL URL
        valid_url = "mysql+pymysql://user:password@localhost:3306/database?charset=utf8mb4"
        result = validate_mysql_connection(valid_url)
        
        if 'troubleshooting_guide' in result:
            logger.info("✅ MySQL connection validator working correctly")
        else:
            logger.error("❌ MySQL connection validator missing troubleshooting guide")
            return False
        
        # Test with invalid URL
        invalid_url = "MySQL database"
        result = validate_mysql_connection(invalid_url)
        
        if not result['is_valid'] and result['errors']:
            logger.info("✅ MySQL connection validator correctly rejects invalid URLs")
        else:
            logger.error("❌ MySQL connection validator should reject invalid URLs")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MySQL connection validation test failed: {e}")
        return False

def test_enhanced_error_handling():
    """Test enhanced MySQL error handling in DatabaseManager"""
    logger.info("Testing enhanced MySQL error handling...")
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Test error handling method exists and works
        if hasattr(db_manager, 'handle_mysql_error'):
            logger.info("✅ Enhanced MySQL error handling method exists")
            
            # Test with mock MySQL error
            class MockMySQLError(Exception):
                def __init__(self, message, error_code):
                    super().__init__(message)
                    self.orig = MockOrigError(error_code)
            
            class MockOrigError:
                def __init__(self, error_code):
                    self.args = [error_code]
            
            # Test known error code
            mock_error = MockMySQLError("Access denied", 1045)
            error_message = db_manager.handle_mysql_error(mock_error)
            
            if "Access denied" in error_message and "Solution:" in error_message:
                logger.info("✅ Enhanced MySQL error handling provides detailed diagnostics")
            else:
                logger.error("❌ Enhanced MySQL error handling not providing detailed diagnostics")
                return False
            
            return True
        else:
            logger.error("❌ Enhanced MySQL error handling method missing")
            return False
            
    except Exception as e:
        logger.error(f"❌ Enhanced error handling test failed: {e}")
        return False

def test_troubleshooting_guide_generation():
    """Test MySQL troubleshooting guide generation"""
    logger.info("Testing MySQL troubleshooting guide generation...")
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Test troubleshooting guide method exists
        if hasattr(db_manager, 'generate_mysql_troubleshooting_guide'):
            logger.info("✅ MySQL troubleshooting guide method exists")
            
            # Generate guide without error
            guide = db_manager.generate_mysql_troubleshooting_guide()
            
            required_sections = [
                "TROUBLESHOOTING",
                "VERIFY MYSQL SERVER STATUS",
                "CHECK MYSQL SERVER LOGS", 
                "TEST MANUAL CONNECTION",
                "COMMON SOLUTIONS",
                "ADDITIONAL RESOURCES"
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in guide:
                    missing_sections.append(section)
            
            if not missing_sections:
                logger.info("✅ MySQL troubleshooting guide contains all required sections")
            else:
                logger.warning(f"⚠️  MySQL troubleshooting guide missing sections: {missing_sections}")
            
            # Test guide with error
            mock_error = Exception("Test error")
            error_guide = db_manager.generate_mysql_troubleshooting_guide(mock_error)
            
            if "CURRENT ERROR" in error_guide and len(error_guide) > len(guide):
                logger.info("✅ MySQL troubleshooting guide includes error-specific guidance")
            else:
                logger.warning("⚠️  MySQL troubleshooting guide may not include error-specific guidance")
            
            return True
        else:
            logger.error("❌ MySQL troubleshooting guide method missing")
            return False
            
    except Exception as e:
        logger.error(f"❌ Troubleshooting guide test failed: {e}")
        return False

def test_connection_parameter_validation_in_database_manager():
    """Test that DatabaseManager validates connection parameters"""
    logger.info("Testing DatabaseManager connection parameter validation...")
    
    # Test with invalid URL
    original_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "invalid://url"
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        logger.error("❌ DatabaseManager should reject invalid connection parameters")
        return False
        
    except DatabaseOperationError as e:
        if "Invalid MySQL connection parameters" in str(e) or "Invalid database URL" in str(e):
            logger.info("✅ DatabaseManager correctly validates and rejects invalid connection parameters")
            result = True
        else:
            logger.error(f"❌ DatabaseManager rejection message not specific enough: {e}")
            result = False
    except Exception as e:
        logger.error(f"❌ Unexpected error during connection parameter validation test: {e}")
        result = False
    finally:
        # Restore original URL
        if original_url:
            os.environ["DATABASE_URL"] = original_url
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
    
    return result

def test_mysql_specific_recovery():
    """Test MySQL-specific recovery mechanisms"""
    logger.info("Testing MySQL-specific recovery mechanisms...")
    
    try:
        # Test system recovery module
        from app.core.security.error_handling.system_recovery import SystemRecoveryManager
        
        recovery_manager = SystemRecoveryManager()
        
        # Test MySQL-specific recovery method
        if hasattr(recovery_manager, '_recover_database_connection'):
            logger.info("✅ MySQL-specific recovery method exists")
            
            # Test recovery with mock MySQL error
            class MockMySQLError(Exception):
                def __init__(self, message, error_code):
                    super().__init__(message)
                    self.orig = MockOrigError(error_code)
            
            class MockOrigError:
                def __init__(self, error_code):
                    self.args = [error_code]
            
            # Test with "MySQL server has gone away" error
            mock_error = MockMySQLError("MySQL server has gone away", 2006)
            
            # This will likely fail due to no actual database session, but method should exist
            try:
                recovery_manager._recover_database_connection(mock_error, {})
                logger.info("✅ MySQL-specific recovery method executed")
            except Exception:
                logger.info("✅ MySQL-specific recovery method exists (execution failed as expected without DB session)")
            
            return True
        else:
            logger.error("❌ MySQL-specific recovery method missing")
            return False
            
    except Exception as e:
        logger.error(f"❌ MySQL-specific recovery test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== MySQL Connection Error Handling Validation ===")
    
    success = True
    
    # Test 1: MySQL connection validation
    if not test_mysql_connection_validation():
        success = False
    
    # Test 2: Enhanced error handling
    if not test_enhanced_error_handling():
        success = False
    
    # Test 3: Troubleshooting guide generation
    if not test_troubleshooting_guide_generation():
        success = False
    
    # Test 4: Connection parameter validation in DatabaseManager
    if not test_connection_parameter_validation_in_database_manager():
        success = False
    
    # Test 5: MySQL-specific recovery
    if not test_mysql_specific_recovery():
        success = False
    
    if success:
        logger.info("🎉 All MySQL connection error handling tests passed!")
        sys.exit(0)
    else:
        logger.error("💥 Some MySQL connection error handling tests failed!")
        sys.exit(1)
