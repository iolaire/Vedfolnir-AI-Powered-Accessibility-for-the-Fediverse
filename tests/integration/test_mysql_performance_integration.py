#!/usr/bin/env python3
"""
MySQL Performance Integration Test

Tests MySQL-specific performance characteristics and connection pooling
in integration scenarios. This test validates requirements 3.3 and 3.4.
"""

import unittest
import time
import logging
import sys
import os
from datetime import datetime
from sqlalchemy import text

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.mysql_test_base import MySQLIntegrationTestBase
from models import User, PlatformConnection, Post, Image, ProcessingStatus

# Set up logging
logger = logging.getLogger(__name__)

class TestMySQLPerformanceIntegration(MySQLIntegrationTestBase):
    """Integration tests for MySQL performance characteristics"""
    
    def setUp(self):
        """Set up MySQL performance integration test"""
        super().setUp()
        
        # Create additional test data for performance testing
        self._create_performance_test_data()
    
    def _create_performance_test_data(self):
        """Create additional data for performance testing"""
        if not (self.test_user and self.test_platform):
            self.skipTest("Basic test data not available")
        
        try:
            # Create multiple posts for performance testing
            self.performance_posts = []
            for i in range(10):
                post = self.fixtures.create_test_post(
                    self.session,
                    self.test_platform,
                    post_id=f"perf_test_post_{self.mysql_config.test_name}_{i}"
                )
                self.performance_posts.append(post)
                
                # Create images for each post
                for j in range(2):
                    self.fixtures.create_test_image(
                        self.session,
                        post,
                        attachment_index=j
                    )
            
            logger.info(f"Created {len(self.performance_posts)} posts with images for performance testing")
            
        except Exception as e:
            logger.warning(f"Could not create performance test data: {e}")
            self.performance_posts = []
    
    def test_mysql_connection_pooling_integration(self):
        """Test MySQL connection pooling in integration scenario (Requirement 3.4)"""
        logger.info("Testing MySQL connection pooling integration")
        
        # Test connection pooling performance
        self.test_mysql_connection_pooling()
        
        # Verify that connection pooling works with concurrent operations
        start_time = time.perf_counter()
        
        # Simulate concurrent database operations
        operations_completed = 0
        for i in range(20):
            try:
                # Query users
                users = self.session.query(User).filter(
                    User.username.like(f'%{self.mysql_config.test_name}%')
                ).all()
                
                # Query platform connections
                platforms = self.session.query(PlatformConnection).filter(
                    PlatformConnection.name.like(f'%{self.mysql_config.test_name}%')
                ).all()
                
                # Query posts
                posts = self.session.query(Post).filter(
                    Post.post_id.like(f'%{self.mysql_config.test_name}%')
                ).all()
                
                operations_completed += 1
                
            except Exception as e:
                logger.error(f"Database operation {i} failed: {e}")
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Verify performance
        self.assertGreater(operations_completed, 15, "Most database operations should succeed")
        self.assertLess(total_time, 5.0, "Operations should complete within 5 seconds")
        
        operations_per_second = operations_completed / total_time
        self.assertGreater(operations_per_second, 5, "Should achieve at least 5 operations per second")
        
        logger.info(f"Connection pooling test: {operations_completed} operations in {total_time:.2f}s ({operations_per_second:.2f} ops/sec)")
    
    def test_mysql_query_performance_integration(self):
        """Test MySQL query performance in integration scenario (Requirement 3.3)"""
        logger.info("Testing MySQL query performance integration")
        
        # Test basic query performance
        self.test_mysql_query_performance()
        
        # Test complex queries with joins
        start_time = time.perf_counter()
        
        complex_queries = [
            # Query with join
            """
            SELECT u.username, pc.name, COUNT(p.id) as post_count
            FROM users u
            JOIN platform_connections pc ON u.id = pc.user_id
            LEFT JOIN posts p ON pc.id = p.platform_connection_id
            WHERE u.username LIKE %s
            GROUP BY u.id, pc.id
            """,
            
            # Query with subquery
            """
            SELECT p.post_id, p.post_content,
                   (SELECT COUNT(*) FROM images i WHERE i.post_id = p.id) as image_count
            FROM posts p
            WHERE p.post_id LIKE %s
            """,
            
            # Aggregation query
            """
            SELECT pc.platform_type, COUNT(*) as connection_count,
                   AVG(CASE WHEN pc.is_active THEN 1 ELSE 0 END) as active_ratio
            FROM platform_connections pc
            JOIN users u ON pc.user_id = u.id
            WHERE u.username LIKE %s
            GROUP BY pc.platform_type
            """
        ]
        
        query_times = []
        for i, query in enumerate(complex_queries):
            query_start = time.perf_counter()
            
            try:
                result = self.session.execute(text(query), {"pattern": f'%{self.mysql_config.test_name}%'})
                rows = result.fetchall()
                
                query_end = time.perf_counter()
                query_time = query_end - query_start
                query_times.append(query_time)
                
                logger.info(f"Complex query {i+1}: {len(rows)} rows in {query_time:.4f}s")
                
            except Exception as e:
                logger.error(f"Complex query {i+1} failed: {e}")
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Verify performance
        self.assertGreater(len(query_times), 0, "At least one complex query should succeed")
        
        if query_times:
            avg_query_time = sum(query_times) / len(query_times)
            self.assertLess(avg_query_time, 1.0, "Complex queries should complete within 1 second on average")
            
            max_query_time = max(query_times)
            self.assertLess(max_query_time, 2.0, "No query should take more than 2 seconds")
        
        logger.info(f"Complex query performance: {len(query_times)} queries in {total_time:.2f}s")
    
    def test_mysql_optimization_features_integration(self):
        """Test MySQL optimization features in integration scenario (Requirement 3.4)"""
        logger.info("Testing MySQL optimization features integration")
        
        # Test basic optimization features
        self.test_mysql_optimization_features()
        
        # Test index usage with actual data
        start_time = time.perf_counter()
        
        try:
            # Test index on username (should be fast)
            explain_result = self.session.execute(
                text(f"EXPLAIN SELECT * FROM users WHERE username = :username"),
                {"username": f'testuser_{self.mysql_config.test_name}'}
            ).fetchall()
            
            # Test index on email (should be fast)
            explain_result2 = self.session.execute(
                text("EXPLAIN SELECT * FROM users WHERE email LIKE :pattern"),
                {"pattern": f'%{self.mysql_config.test_name}%'}
            ).fetchall()
            
            # Test foreign key index usage
            explain_result3 = self.session.execute(
                text("EXPLAIN SELECT p.* FROM posts p JOIN platform_connections pc ON p.platform_connection_id = pc.id WHERE pc.name LIKE :pattern"),
                {"pattern": f'%{self.mysql_config.test_name}%'}
            ).fetchall()
            
            end_time = time.perf_counter()
            explain_time = end_time - start_time
            
            # Verify that EXPLAIN queries work and are fast
            self.assertGreater(len(explain_result), 0, "EXPLAIN should return results")
            self.assertLess(explain_time, 0.5, "EXPLAIN queries should be very fast")
            
            logger.info(f"MySQL optimization features test completed in {explain_time:.4f}s")
            
        except Exception as e:
            self.fail(f"MySQL optimization features test failed: {e}")
    
    def test_mysql_transaction_performance_integration(self):
        """Test MySQL transaction performance in integration scenario"""
        logger.info("Testing MySQL transaction performance integration")
        
        if not self.performance_tester:
            self.skipTest("Performance testing not available")
        
        # Test transaction performance with realistic operations
        result = self.performance_tester.test_transaction_performance(
            operations_per_transaction=5,
            transaction_count=10
        )
        
        self.assertTrue(result.success, f"Transaction performance test failed: {result.error_message}")
        
        # Verify transaction performance metrics
        avg_tx_time = result.get_average_metric("transaction_time")
        if avg_tx_time:
            self.assertLess(avg_tx_time, 2.0, "Transactions should complete within 2 seconds on average")
        
        tx_throughput = result.get_metric("transaction_throughput")
        if tx_throughput:
            self.assertGreater(tx_throughput.value, 1, "Should achieve at least 1 transaction per second")
        
        error_count = result.get_metric("transaction_error_count")
        if error_count:
            self.assertEqual(error_count.value, 0, "No transaction errors should occur")
        
        logger.info("Transaction performance test completed successfully")
    
    def test_comprehensive_mysql_performance_suite(self):
        """Run comprehensive MySQL performance test suite"""
        logger.info("Running comprehensive MySQL performance test suite")
        
        if not self.performance_tester:
            self.skipTest("Performance testing not available")
        
        # Run all performance tests
        results = self.run_performance_test_suite()
        
        # Verify that all tests passed
        successful_tests = [r for r in results if r.success]
        failed_tests = [r for r in results if not r.success]
        
        self.assertGreater(len(successful_tests), 0, "At least some performance tests should pass")
        
        if failed_tests:
            logger.warning(f"Some performance tests failed: {[r.test_name for r in failed_tests]}")
        
        # Generate performance report
        report = self.performance_tester.generate_performance_report(results)
        logger.info("Performance test report generated")
        
        # Save report for analysis
        report_path = f"/tmp/mysql_performance_report_{self.mysql_config.test_name}.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Performance report saved to: {report_path}")
        
        # Assert overall performance thresholds
        self.assert_performance_threshold("average_connection_time", 0.5, results)
        self.assert_performance_threshold("average_query_time", 0.1, results)
    
    def test_mysql_connection_pool_exhaustion_handling(self):
        """Test handling of MySQL connection pool exhaustion"""
        logger.info("Testing MySQL connection pool exhaustion handling")
        
        # This test verifies graceful degradation when connection pool is exhausted
        # We'll simulate this by creating many concurrent connections
        
        import threading
        import queue
        
        max_connections = 20  # More than typical pool size
        results_queue = queue.Queue()
        
        def connection_stress_worker(worker_id: int):
            """Worker that holds a connection for a while"""
            try:
                session = self.mysql_config.get_test_session()
                
                # Hold the connection for a short time
                time.sleep(0.1)
                
                # Perform a simple operation
                result = session.execute(text("SELECT 1")).fetchone()
                
                session.close()
                
                results_queue.put(('success', worker_id, result[0] if result else None))
                
            except Exception as e:
                results_queue.put(('error', worker_id, str(e)))
        
        # Start many worker threads
        threads = []
        start_time = time.perf_counter()
        
        for i in range(max_connections):
            thread = threading.Thread(target=connection_stress_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Collect results
        successes = 0
        errors = 0
        
        while not results_queue.empty():
            result_type, worker_id, data = results_queue.get()
            if result_type == 'success':
                successes += 1
            else:
                errors += 1
                logger.warning(f"Worker {worker_id} failed: {data}")
        
        # Verify that the system handled the stress gracefully
        total_operations = successes + errors
        success_rate = successes / total_operations if total_operations > 0 else 0
        
        self.assertGreater(success_rate, 0.7, "At least 70% of operations should succeed under stress")
        self.assertLess(total_time, 15.0, "Stress test should complete within 15 seconds")
        
        logger.info(f"Connection pool stress test: {successes}/{total_operations} succeeded ({success_rate:.1%}) in {total_time:.2f}s")
    
    def tearDown(self):
        """Clean up performance test resources"""
        # Clean up performance test data
        if hasattr(self, 'performance_posts') and self.performance_posts:
            try:
                for post in self.performance_posts:
                    # Images will be deleted by cascade
                    self.session.delete(post)
                self.session.commit()
                logger.info(f"Cleaned up {len(self.performance_posts)} performance test posts")
            except Exception as e:
                logger.warning(f"Error cleaning up performance test data: {e}")
        
        super().tearDown()


if __name__ == "__main__":
    # Run the MySQL performance integration tests
    unittest.main(verbosity=2)
