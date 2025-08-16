#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive tests for database optimization features.
"""
import unittest
import tempfile
import os
import sys
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager
from models import Base, Post, Image, ProcessingRun, ProcessingStatus, User, UserRole
from config import Config, StorageConfig, DatabaseConfig


class TestDatabaseOptimizations(unittest.TestCase):
    """Test database optimization features"""
    
    def setUp(self):
        """Set up test database"""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create test config
        config = Config()
        
        # Override storage config for testing
        db_config = DatabaseConfig(
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
            query_logging=True
        )
        
        config.storage = StorageConfig(
            database_url=f"sqlite:///{self.temp_db.name}",
            db_config=db_config
        )
        
        # Create database manager
        self.db_manager = DatabaseManager(config)
        
        # Create test data
        self._create_test_data()
    
    def tearDown(self):
        """Clean up test database"""
        self.db_manager.close_session()
        os.unlink(self.temp_db.name)
    
    def _create_test_data(self):
        """Create test data for optimization tests"""
        session = self.db_manager.get_session()
        try:
            # Create test posts
            for i in range(10):
                post = Post(
                    post_id=f"post_{i}",
                    user_id=f"user_{i % 3}",  # 3 different users
                    post_url=f"https://example.com/post_{i}",
                    post_content=f"Test post content {i}"
                )
                session.add(post)
            
            session.commit()
            
            # Create test images
            posts = session.query(Post).all()
            for i, post in enumerate(posts):
                for j in range(2):  # 2 images per post
                    image = Image(
                        post_id=post.id,
                        image_url=f"https://example.com/image_{i}_{j}.jpg",
                        local_path=f"/storage/images/image_{i}_{j}.jpg",
                        attachment_index=j,
                        media_type="image/jpeg",
                        image_post_id=f"img_{i}_{j}",
                        status=ProcessingStatus.PENDING if i % 2 == 0 else ProcessingStatus.POSTED,
                        generated_caption=f"Generated caption for image {i}_{j}",
                        final_caption=f"Final caption for image {i}_{j}",
                        original_post_date=datetime.now(datetime.UTC)- timedelta(days=i)
                    )
                    session.add(image)
            
            # Create test users
            for i in range(3):
                user = User(
                    username=f"testuser_{i}",
                    email=f"test{i}@test.com",
                    role=UserRole.ADMIN if i == 0 else UserRole.REVIEWER,
                    is_active=True
                )
                user.set_password("testpassword")
                session.add(user)
            
            # Create test processing runs
            for i in range(5):
                run = ProcessingRun(
                    user_id=f"user_{i % 3}",
                    started_at=datetime.now(datetime.UTC)- timedelta(hours=i),
                    completed_at=datetime.now(datetime.UTC)- timedelta(hours=i) + timedelta(minutes=30),
                    posts_processed=10,
                    images_processed=20,
                    captions_generated=18,
                    errors_count=2,
                    status="completed"
                )
                session.add(run)
            
            session.commit()
        finally:
            session.close()
    
    def test_connection_pooling(self):
        """Test that connection pooling is configured correctly"""
        engine = self.db_manager.engine
        
        # Check pool configuration
        self.assertEqual(engine.pool.size(), 5)  # pool_size
        self.assertEqual(engine.pool._max_overflow, 10)  # max_overflow
        
        # Test that multiple sessions can be created
        sessions = []
        for i in range(3):
            session = self.db_manager.get_session()
            sessions.append(session)
        
        # All sessions should be valid
        for session in sessions:
            self.assertIsNotNone(session)
            result = session.execute(text("SELECT 1")).scalar()
            self.assertEqual(result, 1)
        
        # Clean up sessions
        for session in sessions:
            session.close()
    
    def test_query_logging(self):
        """Test that query logging is working"""
        import logging
        
        # Set up a test handler to capture log messages
        log_messages = []
        
        class TestHandler(logging.Handler):
            def emit(self, record):
                log_messages.append(record.getMessage())
        
        # Add test handler to query logger
        query_logger = logging.getLogger('sqlalchemy.query')
        test_handler = TestHandler()
        query_logger.addHandler(test_handler)
        query_logger.setLevel(logging.INFO)
        
        try:
            # Execute a query that should be logged
            session = self.db_manager.get_session()
            posts = session.query(Post).limit(5).all()
            session.close()
            
            # Check that query was logged
            query_logged = any("SELECT" in msg for msg in log_messages)
            self.assertTrue(query_logged, "Query should have been logged")
            
        finally:
            query_logger.removeHandler(test_handler)
    
    def test_database_indexes_performance(self):
        """Test that database queries perform well with indexes"""
        session = self.db_manager.get_session()
        
        try:
            # Test query performance on indexed fields
            start_time = time.time()
            
            # Query by status (should be indexed)
            pending_images = session.query(Image).filter_by(status=ProcessingStatus.PENDING).all()
            
            query_time = time.time() - start_time
            
            # Query should complete quickly (less than 1 second for test data)
            self.assertLess(query_time, 1.0)
            self.assertGreater(len(pending_images), 0)
            
            # Test query by user_id (should be indexed)
            start_time = time.time()
            user_posts = session.query(Post).filter_by(user_id="user_0").all()
            query_time = time.time() - start_time
            
            self.assertLess(query_time, 1.0)
            self.assertGreater(len(user_posts), 0)
            
        finally:
            session.close()
    
    def test_bulk_operations_performance(self):
        """Test performance of bulk database operations"""
        session = self.db_manager.get_session()
        
        try:
            # Test bulk insert performance
            start_time = time.time()
            
            # Create multiple posts in a single transaction
            posts = []
            for i in range(100):
                post = Post(
                    post_id=f"bulk_post_{i}",
                    user_id=f"bulk_user_{i % 5}",
                    post_url=f"https://example.com/bulk_post_{i}",
                    post_content=f"Bulk test post {i}"
                )
                posts.append(post)
            
            session.add_all(posts)
            session.commit()
            
            bulk_insert_time = time.time() - start_time
            
            # Bulk insert should be reasonably fast
            self.assertLess(bulk_insert_time, 5.0)
            
            # Test bulk update performance
            start_time = time.time()
            
            # Update multiple records
            session.query(Post).filter(Post.post_id.like("bulk_post_%")).update(
                {"post_content": "Updated bulk content"},
                synchronize_session=False
            )
            session.commit()
            
            bulk_update_time = time.time() - start_time
            
            # Bulk update should be reasonably fast
            self.assertLess(bulk_update_time, 2.0)
            
        finally:
            session.close()
    
    def test_transaction_management(self):
        """Test proper transaction management and rollback"""
        session = self.db_manager.get_session()
        
        try:
            # Count initial posts
            initial_count = session.query(Post).count()
            
            # Start a transaction that will fail
            try:
                post1 = Post(
                    post_id="transaction_test_1",
                    user_id="test_user",
                    post_url="https://example.com/test1",
                    post_content="Test post 1"
                )
                session.add(post1)
                
                # This should succeed
                session.flush()
                
                # Create a duplicate post_id (should fail due to unique constraint)
                post2 = Post(
                    post_id="transaction_test_1",  # Duplicate post_id
                    user_id="test_user",
                    post_url="https://example.com/test2",
                    post_content="Test post 2"
                )
                session.add(post2)
                
                # This should fail
                session.commit()
                
            except Exception:
                # Transaction should be rolled back
                session.rollback()
            
            # Count should be unchanged due to rollback
            final_count = session.query(Post).count()
            self.assertEqual(initial_count, final_count)
            
        finally:
            session.close()
    
    def test_session_management(self):
        """Test proper session management and cleanup"""
        # Test that sessions are properly created and closed
        session1 = self.db_manager.get_session()
        self.assertIsNotNone(session1)
        
        # Execute a query
        result = session1.execute(text("SELECT COUNT(*) FROM posts")).scalar()
        self.assertIsInstance(result, int)
        
        # Close session
        session1.close()
        
        # Create a new session
        session2 = self.db_manager.get_session()
        self.assertIsNotNone(session2)
        
        # Should be able to execute queries
        result = session2.execute(text("SELECT COUNT(*) FROM images")).scalar()
        self.assertIsInstance(result, int)
        
        session2.close()
    
    def test_database_statistics_performance(self):
        """Test performance of statistics queries"""
        start_time = time.time()
        
        # Get processing statistics
        stats = self.db_manager.get_processing_stats()
        
        stats_time = time.time() - start_time
        
        # Statistics query should be fast
        self.assertLess(stats_time, 2.0)
        
        # Verify statistics structure
        expected_keys = ['total_posts', 'total_images', 'pending_review', 'approved', 'posted', 'rejected']
        for key in expected_keys:
            self.assertIn(key, stats)
            self.assertIsInstance(stats[key], int)
        
        # Verify statistics values make sense
        self.assertGreaterEqual(stats['total_posts'], 0)
        self.assertGreaterEqual(stats['total_images'], 0)
        self.assertEqual(
            stats['total_images'],
            stats['pending_review'] + stats['approved'] + stats['posted'] + stats['rejected']
        )
    
    def test_complex_query_performance(self):
        """Test performance of complex queries with joins"""
        session = self.db_manager.get_session()
        
        try:
            start_time = time.time()
            
            # Complex query with joins
            results = session.query(Image, Post).join(Post).filter(
                Image.status == ProcessingStatus.PENDING
            ).order_by(Image.original_post_date.desc().nullslast()).limit(10).all()
            
            query_time = time.time() - start_time
            
            # Complex query should still be reasonably fast
            self.assertLess(query_time, 2.0)
            
            # Verify results
            self.assertIsInstance(results, list)
            for image, post in results:
                self.assertIsInstance(image, Image)
                self.assertIsInstance(post, Post)
                self.assertEqual(image.post_id, post.id)
                
        finally:
            session.close()
    
    def test_concurrent_access(self):
        """Test concurrent database access"""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def worker(worker_id):
            try:
                session = self.db_manager.get_session()
                try:
                    # Each worker performs some database operations
                    posts = session.query(Post).filter_by(user_id=f"user_{worker_id % 3}").all()
                    
                    # Create a new image
                    if posts:
                        image = Image(
                            post_id=posts[0].id,
                            image_url=f"https://example.com/concurrent_{worker_id}.jpg",
                            local_path=f"/storage/concurrent_{worker_id}.jpg",
                            attachment_index=0,
                            status=ProcessingStatus.PENDING
                        )
                        session.add(image)
                        session.commit()
                    
                    results.put(f"Worker {worker_id} completed successfully")
                    
                finally:
                    session.close()
                    
            except Exception as e:
                errors.put(f"Worker {worker_id} failed: {e}")
        
        # Start multiple worker threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Check results
        self.assertEqual(results.qsize(), 5)  # All workers should succeed
        self.assertEqual(errors.qsize(), 0)   # No errors should occur
    
    def test_memory_usage_optimization(self):
        """Test that database operations don't consume excessive memory"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive database operations
        session = self.db_manager.get_session()
        
        try:
            # Query large amounts of data
            for _ in range(10):
                images = session.query(Image).all()
                posts = session.query(Post).all()
                
                # Process the data to simulate real usage
                for image in images:
                    _ = image.generated_caption
                    _ = image.status
                
                for post in posts:
                    _ = post.post_content
                    _ = post.user_id
        
        finally:
            session.close()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for test data)
        self.assertLess(memory_increase, 50 * 1024 * 1024)


class TestDatabaseMigrations(unittest.TestCase):
    """Test database migration functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create basic config
        self.config = Config()
        self.config.storage = StorageConfig(database_url=f"sqlite:///{self.temp_db.name}")
    
    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.temp_db.name)
    
    def test_table_creation(self):
        """Test that all tables are created correctly"""
        db_manager = DatabaseManager(self.config)
        
        # Check that all tables exist
        engine = db_manager.engine
        
        # Get table names
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            table_names = [row[0] for row in result]
        
        expected_tables = ['posts', 'images', 'processing_runs', 'users']
        for table in expected_tables:
            self.assertIn(table, table_names)
        
        db_manager.close_session()
    
    def test_schema_integrity(self):
        """Test that database schema has proper constraints and indexes"""
        db_manager = DatabaseManager(self.config)
        
        try:
            session = db_manager.get_session()
            
            # Test unique constraints
            post1 = Post(post_id="unique_test", user_id="user1", post_url="http://test.com")
            session.add(post1)
            session.commit()
            
            # Try to add duplicate post_id (should fail)
            post2 = Post(post_id="unique_test", user_id="user2", post_url="http://test2.com")
            session.add(post2)
            
            with self.assertRaises(Exception):  # Should raise integrity error
                session.commit()
            
            session.rollback()
            
        finally:
            session.close()
            db_manager.close_session()


if __name__ == "__main__":
    unittest.main()