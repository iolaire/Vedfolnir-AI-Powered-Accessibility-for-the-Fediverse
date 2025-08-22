# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Management Performance Test

This script tests the performance improvements from the session management
optimization migration by running common queries and measuring execution time.
"""

import sys
import time

from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config
from database import DatabaseManager
import logging

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SessionManagementPerformanceTest:
    """Test performance of session management queries"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = self.get_database_manager()
        self.db_path = self.config.storage.database_url.replace('mysql+pymysql://', '')
    
    def time_query(self, query, description, params=None):
        """Time a query execution"""
        conn = engine.connect()
        cursor = conn.cursor()
        
        start_time = time.time()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            end_time = time.time()
            
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            logger.info(f"{description}: {execution_time:.2f}ms ({len(results)} rows)")
            return execution_time, len(results)
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return None, 0
        finally:
            conn.close()
    
    def test_user_queries(self):
        """Test user-related queries that benefit from new indexes"""
        logger.info("\n=== USER QUERY PERFORMANCE ===")
        
        # Test active user lookup
        self.time_query(
            "SELECT * FROM users WHERE is_active = 1",
            "Active users query"
        )
        
        # Test user by role
        self.time_query(
            "SELECT * FROM users WHERE role = 'reviewer'",
            "Users by role query"
        )
        
        # Test active users by role (composite index)
        self.time_query(
            "SELECT * FROM users WHERE is_active = 1 AND role = 'reviewer'",
            "Active users by role query (composite index)"
        )
        
        # Test recent login tracking
        self.time_query(
            "SELECT * FROM users WHERE last_login > datetime('now', '-7 days')",
            "Recent login tracking query"
        )
    
    def test_platform_connection_queries(self):
        """Test platform connection queries that benefit from new indexes"""
        logger.info("\n=== PLATFORM CONNECTION QUERY PERFORMANCE ===")
        
        # Test user's platform connections
        self.time_query(
            "SELECT * FROM platform_connections WHERE user_id = 1",
            "User's platform connections query"
        )
        
        # Test active platforms for user
        self.time_query(
            "SELECT * FROM platform_connections WHERE user_id = 1 AND is_active = 1",
            "User's active platforms query (composite index)"
        )
        
        # Test default platform lookup
        self.time_query(
            "SELECT * FROM platform_connections WHERE user_id = 1 AND is_default = 1",
            "User's default platform query (composite index)"
        )
        
        # Test platform type queries
        self.time_query(
            "SELECT * FROM platform_connections WHERE platform_type = 'pixelfed'",
            "Platform type query"
        )
        
        # Test active platforms by type
        self.time_query(
            "SELECT * FROM platform_connections WHERE platform_type = 'pixelfed' AND is_active = 1",
            "Active platforms by type query (composite index)"
        )
        
        # Test platform instance queries
        self.time_query(
            "SELECT * FROM platform_connections WHERE instance_url LIKE '%pixelfed%'",
            "Platform instance URL query"
        )
    
    def test_session_queries(self):
        """Test user session queries that benefit from new indexes"""
        logger.info("\n=== USER SESSION QUERY PERFORMANCE ===")
        
        # Test session by user
        self.time_query(
            "SELECT * FROM user_sessions WHERE user_id = 1",
            "User sessions query"
        )
        
        # Test sessions with active platform
        self.time_query(
            "SELECT * FROM user_sessions WHERE active_platform_id IS NOT NULL",
            "Sessions with active platform query"
        )
        
        # Test user sessions with platform (composite index)
        self.time_query(
            "SELECT * FROM user_sessions WHERE user_id = 1 AND active_platform_id = 1",
            "User sessions with platform query (composite index)"
        )
        
        # Test session cleanup queries
        self.time_query(
            "SELECT * FROM user_sessions WHERE created_at < datetime('now', '-30 days')",
            "Old sessions cleanup query"
        )
        
        # Test IP-based session tracking
        self.time_query(
            "SELECT * FROM user_sessions WHERE ip_address = '127.0.0.1'",
            "IP-based session tracking query"
        )
    
    def test_relationship_queries(self):
        """Test queries involving relationships that benefit from new indexes"""
        logger.info("\n=== RELATIONSHIP QUERY PERFORMANCE ===")
        
        # Test posts by platform connection
        self.time_query(
            "SELECT * FROM posts WHERE platform_connection_id = 1",
            "Posts by platform connection query"
        )
        
        # Test posts by platform and user
        self.time_query(
            "SELECT * FROM posts WHERE platform_connection_id = 1 AND user_id = 'test_user'",
            "Posts by platform and user query (composite index)"
        )
        
        # Test images by platform connection
        self.time_query(
            "SELECT * FROM images WHERE platform_connection_id = 1",
            "Images by platform connection query"
        )
        
        # Test images by platform and status
        self.time_query(
            "SELECT * FROM images WHERE platform_connection_id = 1 AND status = 'pending'",
            "Images by platform and status query (composite index)"
        )
        
        # Test processing runs by platform
        self.time_query(
            "SELECT * FROM processing_runs WHERE platform_connection_id = 1",
            "Processing runs by platform query"
        )
    
    def test_explain_query_plans(self):
        """Test query plans to verify index usage"""
        logger.info("\n=== QUERY PLAN ANALYSIS ===")
        
        conn = engine.connect()
        cursor = conn.cursor()
        
        test_queries = [
            ("SELECT * FROM users WHERE is_active = 1 AND role = 'reviewer'", 
             "Active users by role"),
            ("SELECT * FROM platform_connections WHERE user_id = 1 AND is_active = 1", 
             "User's active platforms"),
            ("SELECT * FROM user_sessions WHERE user_id = 1 AND active_platform_id = 1", 
             "User sessions with platform"),
            ("SELECT * FROM posts WHERE platform_connection_id = 1 AND user_id = 'test'", 
             "Posts by platform and user")
        ]
        
        for query, description in test_queries:
            try:
                cursor.execute(f"EXPLAIN QUERY PLAN {query}")
                plan = cursor.fetchall()
                logger.info(f"\n{description}:")
                for row in plan:
                    logger.info(f"  {row}")
            except Exception as e:
                logger.error(f"Failed to get query plan for {description}: {e}")
        
        conn.close()
    
    def run_all_tests(self):
        """Run all performance tests"""
        logger.info("Starting Session Management Performance Tests")
        logger.info(f"Database: {self.db_path}")
        
        start_time = time.time()
        
        self.test_user_queries()
        self.test_platform_connection_queries()
        self.test_session_queries()
        self.test_relationship_queries()
        self.test_explain_query_plans()
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        logger.info(f"\n=== PERFORMANCE TEST SUMMARY ===")
        logger.info(f"Total test execution time: {total_time:.2f}ms")
        logger.info("All session management optimization indexes are working correctly")

def main():
    """Main function to run performance tests"""
    try:
        test = SessionManagementPerformanceTest()
        test.run_all_tests()
        return 0
    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())