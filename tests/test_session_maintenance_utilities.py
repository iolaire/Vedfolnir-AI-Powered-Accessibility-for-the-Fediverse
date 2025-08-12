# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for Session Maintenance Utilities

Tests the session cleanup, analytics, and database maintenance utilities
to ensure they work correctly and provide the required functionality.
"""

import unittest
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from config import Config
from database import DatabaseManager
from models import User, UserSession, PlatformConnection
from scripts.maintenance.session_cleanup import SessionCleanupService
from scripts.maintenance.session_analytics import SessionAnalytics
from scripts.maintenance.session_db_maintenance import SessionDatabaseMaintenance

class TestSessionMaintenanceUtilities(unittest.TestCase):
    """Test session maintenance utilities"""
    
    def setUp(self):
        """Set up test environment"""
        # Set encryption key for testing
        from cryptography.fernet import Fernet
        os.environ['PLATFORM_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
        
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create test config
        self.config = Config()
        self.config.DATABASE_URL = f"sqlite:///{self.temp_db.name}"
        
        # Initialize database
        self.db_manager = DatabaseManager(self.config)
        self.db_manager.create_tables()
        
        # Create test data
        self._create_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def _create_test_data(self):
        """Create test data for maintenance utilities"""
        with self.db_manager.get_session() as db_session:
            # Create test user with unique data
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            user = User(
                username=f'testuser_{unique_id}',
                email=f'test_{unique_id}@example.com',
                password_hash='hashed_password'
            )
            db_session.add(user)
            db_session.flush()
            
            # Create platform connection
            platform = PlatformConnection(
                user_id=user.id,
                name='Test Platform',
                platform_type='pixelfed',
                instance_url='https://test.example.com',
                access_token='test_token'
            )
            db_session.add(platform)
            db_session.flush()
            
            # Create test sessions with different ages
            now = datetime.now(timezone.utc)
            
            # Recent session (active)
            recent_session = UserSession(
                session_id='recent_session_123',
                user_id=user.id,
                active_platform_id=platform.id,
                created_at=now - timedelta(hours=1),
                updated_at=now - timedelta(minutes=5)
            )
            db_session.add(recent_session)
            
            # Old session (should be cleaned up)
            old_session = UserSession(
                session_id='old_session_456',
                user_id=user.id,
                active_platform_id=platform.id,
                created_at=now - timedelta(days=3),
                updated_at=now - timedelta(days=2)
            )
            db_session.add(old_session)
            
            # Very old session (should be cleaned up)
            very_old_session = UserSession(
                session_id='very_old_session_789',
                user_id=user.id,
                active_platform_id=platform.id,
                created_at=now - timedelta(days=10),
                updated_at=now - timedelta(days=8)
            )
            db_session.add(very_old_session)
            
            db_session.commit()
    
    def test_session_cleanup_service_initialization(self):
        """Test SessionCleanupService initialization"""
        cleanup_service = SessionCleanupService(self.config)
        
        self.assertIsNotNone(cleanup_service.db_manager)
        self.assertIsNotNone(cleanup_service.session_manager)
        self.assertIsNotNone(cleanup_service.monitor)
        self.assertGreater(cleanup_service.cleanup_interval, 0)
        self.assertGreater(cleanup_service.batch_size, 0)
        self.assertGreater(cleanup_service.max_session_age, 0)
    
    def test_session_cleanup_statistics(self):
        """Test getting cleanup statistics"""
        cleanup_service = SessionCleanupService(self.config)
        stats = cleanup_service.get_cleanup_statistics()
        
        self.assertIn('timestamp', stats)
        self.assertIn('total_sessions', stats)
        self.assertIn('recent_sessions_24h', stats)
        self.assertIn('old_sessions_48h', stats)
        self.assertIn('cleanup_interval', stats)
        
        # Should have 3 total sessions from test data
        self.assertEqual(stats['total_sessions'], 3)
        
        # Should have 1 recent session (within 24h)
        self.assertEqual(stats['recent_sessions_24h'], 1)
        
        # Should have 2 old sessions (older than 48h)
        self.assertEqual(stats['old_sessions_48h'], 2)
    
    def test_session_cleanup_cycle(self):
        """Test running a cleanup cycle"""
        cleanup_service = SessionCleanupService(self.config)
        results = cleanup_service.run_cleanup_cycle()
        
        self.assertIn('timestamp', results)
        self.assertIn('expired_sessions_cleaned', results)
        self.assertIn('orphaned_sessions_cleaned', results)
        self.assertIn('duration_seconds', results)
        
        # Should clean up expired sessions
        self.assertGreaterEqual(results['expired_sessions_cleaned'], 0)
        
        # Should have reasonable duration
        self.assertGreater(results['duration_seconds'], 0)
        self.assertLess(results['duration_seconds'], 10)  # Should be fast
    
    def test_session_analytics_initialization(self):
        """Test SessionAnalytics initialization"""
        analytics = SessionAnalytics(self.config)
        
        self.assertIsNotNone(analytics.db_manager)
        self.assertIsNotNone(analytics.session_manager)
        self.assertIsNotNone(analytics.monitor)
    
    def test_session_health_report_generation(self):
        """Test generating session health report"""
        analytics = SessionAnalytics(self.config)
        report = analytics.generate_health_report()
        
        self.assertIn('timestamp', report)
        self.assertIn('health_status', report)
        self.assertIn('detailed_analytics', report)
        self.assertIn('performance_metrics', report)
        self.assertIn('security_analysis', report)
        self.assertIn('recommendations', report)
        
        # Health status should have required fields
        health_status = report['health_status']
        self.assertIn('overall_health', health_status)
        self.assertIn('issues', health_status)
        self.assertIn('recommendations', health_status)
    
    def test_session_trends_analysis(self):
        """Test session trends analysis"""
        analytics = SessionAnalytics(self.config)
        trends = analytics.get_session_trends(days=7)
        
        self.assertIn('period_days', trends)
        self.assertIn('daily_session_creation', trends)
        self.assertIn('total_sessions_created', trends)
        self.assertIn('average_daily_sessions', trends)
        
        self.assertEqual(trends['period_days'], 7)
        self.assertIsInstance(trends['daily_session_creation'], dict)
        self.assertGreaterEqual(trends['total_sessions_created'], 0)
    
    def test_database_maintenance_initialization(self):
        """Test SessionDatabaseMaintenance initialization"""
        db_maintenance = SessionDatabaseMaintenance(self.config)
        
        self.assertIsNotNone(db_maintenance.db_manager)
        self.assertIsNotNone(db_maintenance.session_manager)
    
    def test_session_table_analysis(self):
        """Test session table analysis"""
        db_maintenance = SessionDatabaseMaintenance(self.config)
        analysis = db_maintenance.analyze_session_tables()
        
        self.assertIn('timestamp', analysis)
        self.assertIn('tables', analysis)
        self.assertIn('indexes', analysis)
        self.assertIn('recommendations', analysis)
        
        # Should analyze user_sessions table
        self.assertIn('user_sessions', analysis['tables'])
        table_stats = analysis['tables']['user_sessions']
        
        self.assertIn('row_count', table_stats)
        self.assertIn('unique_users', table_stats)
        
        # Should have 3 sessions from test data
        self.assertEqual(table_stats['row_count'], 3)
        self.assertEqual(table_stats['unique_users'], 1)
    
    def test_database_statistics(self):
        """Test getting database statistics"""
        db_maintenance = SessionDatabaseMaintenance(self.config)
        stats = db_maintenance.get_database_statistics()
        
        self.assertIn('timestamp', stats)
        self.assertIn('database_size_bytes', stats)
        self.assertIn('database_size_mb', stats)
        self.assertIn('connection_pool', stats)
        self.assertIn('table_analysis', stats)
        
        # Should have reasonable database size
        self.assertGreater(stats['database_size_bytes'], 0)
        self.assertGreater(stats['database_size_mb'], 0)
    
    def test_recommended_indexes_creation_dry_run(self):
        """Test creating recommended indexes in dry run mode"""
        db_maintenance = SessionDatabaseMaintenance(self.config)
        results = db_maintenance.create_recommended_indexes(dry_run=True)
        
        self.assertIn('timestamp', results)
        self.assertIn('dry_run', results)
        self.assertIn('indexes_created', results)
        self.assertIn('indexes_skipped', results)
        self.assertIn('errors', results)
        
        self.assertTrue(results['dry_run'])
        
        # Should identify indexes to create
        total_actions = len(results['indexes_created']) + len(results['indexes_skipped'])
        self.assertGreater(total_actions, 0)
    
    def test_database_integrity_check(self):
        """Test database integrity check"""
        db_maintenance = SessionDatabaseMaintenance(self.config)
        results = db_maintenance.check_database_integrity()
        
        self.assertIn('timestamp', results)
        self.assertIn('integrity_check', results)
        self.assertIn('foreign_key_check', results)
        self.assertIn('issues_found', results)
        self.assertIn('recommendations', results)
        
        # Fresh database should pass integrity checks
        self.assertEqual(results['integrity_check'], 'passed')
        self.assertEqual(results['foreign_key_check'], 'passed')
        self.assertEqual(len(results['issues_found']), 0)
    
    def test_table_optimization(self):
        """Test table optimization"""
        db_maintenance = SessionDatabaseMaintenance(self.config)
        results = db_maintenance.optimize_session_tables(vacuum=False)
        
        self.assertIn('timestamp', results)
        self.assertIn('operations_performed', results)
        self.assertIn('duration_seconds', results)
        self.assertIn('errors', results)
        
        # Should perform some optimization operations
        self.assertGreater(len(results['operations_performed']), 0)
        
        # Should complete quickly
        self.assertGreater(results['duration_seconds'], 0)
        self.assertLess(results['duration_seconds'], 5)
        
        # Should not have errors
        self.assertEqual(len(results['errors']), 0)
    
    @patch('scripts.maintenance.session_cleanup.time.sleep')
    def test_cleanup_service_daemon_mode_setup(self, mock_sleep):
        """Test cleanup service daemon mode setup (without actually running)"""
        cleanup_service = SessionCleanupService(self.config)
        
        # Mock sleep to prevent actual daemon execution
        mock_sleep.side_effect = KeyboardInterrupt()
        
        # Should handle KeyboardInterrupt gracefully
        try:
            cleanup_service.start_daemon()
        except KeyboardInterrupt:
            pass
        
        # Service should be stopped
        self.assertFalse(cleanup_service.running)
    
    def test_force_cleanup_with_custom_age(self):
        """Test force cleanup with custom age limit"""
        cleanup_service = SessionCleanupService(self.config)
        
        # Force cleanup with 1 hour age limit (should clean more sessions)
        results = cleanup_service.force_cleanup(max_age_hours=1)
        
        self.assertIn('forced_cleanup', results)
        self.assertIn('custom_max_age_hours', results)
        self.assertTrue(results['forced_cleanup'])
        self.assertEqual(results['custom_max_age_hours'], 1)
    
    def test_analytics_export_functionality(self):
        """Test analytics report export"""
        analytics = SessionAnalytics(self.config)
        
        # Create temporary file for export
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_filename = temp_file.name
        
        try:
            # Export report
            exported_file = analytics.export_analytics_report(temp_filename)
            
            self.assertEqual(exported_file, temp_filename)
            self.assertTrue(os.path.exists(temp_filename))
            
            # Verify file has content
            with open(temp_filename, 'r') as f:
                content = f.read()
                self.assertGreater(len(content), 0)
                
                # Should be valid JSON
                import json
                data = json.loads(content)
                self.assertIn('timestamp', data)
                self.assertIn('health_status', data)
        
        finally:
            # Clean up
            try:
                os.unlink(temp_filename)
            except:
                pass

class TestSessionMaintenanceIntegration(unittest.TestCase):
    """Integration tests for session maintenance utilities"""
    
    def setUp(self):
        """Set up integration test environment"""
        # Set encryption key for testing
        from cryptography.fernet import Fernet
        os.environ['PLATFORM_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
        
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create test config
        self.config = Config()
        self.config.DATABASE_URL = f"sqlite:///{self.temp_db.name}"
        
        # Initialize database
        self.db_manager = DatabaseManager(self.config)
        self.db_manager.create_tables()
    
    def tearDown(self):
        """Clean up integration test environment"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_maintenance_utilities_integration(self):
        """Test that all maintenance utilities work together"""
        # Initialize all utilities
        cleanup_service = SessionCleanupService(self.config)
        analytics = SessionAnalytics(self.config)
        db_maintenance = SessionDatabaseMaintenance(self.config)
        
        # Run basic operations from each utility
        cleanup_stats = cleanup_service.get_cleanup_statistics()
        health_report = analytics.generate_health_report()
        db_analysis = db_maintenance.analyze_session_tables()
        
        # All should complete without errors
        self.assertNotIn('error', cleanup_stats)
        self.assertNotIn('error', health_report)
        self.assertNotIn('error', db_analysis)
        
        # All should have expected structure
        self.assertIn('total_sessions', cleanup_stats)
        self.assertIn('health_status', health_report)
        self.assertIn('tables', db_analysis)

if __name__ == '__main__':
    unittest.main()