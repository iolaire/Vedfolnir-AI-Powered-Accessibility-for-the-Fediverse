# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for the AuditLogger class.

Tests comprehensive audit logging functionality including job action logging,
querying, filtering, statistics, export, and cleanup capabilities.
"""

import unittest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from audit_logger import AuditLogger
from models import JobAuditLog, User, CaptionGenerationTask
from database import DatabaseManager
from config import Config


class TestAuditLogger(unittest.TestCase):
    """Test AuditLogger functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = Mock(spec=DatabaseManager)
        self.audit_logger = AuditLogger(self.db_manager)
        
        # Mock database session context manager
        self.mock_session = Mock()
        self.mock_context_manager = Mock()
        self.mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
        self.mock_context_manager.__exit__ = Mock(return_value=None)
        self.db_manager.get_session.return_value = self.mock_context_manager
        
        # Test data
        self.task_id = "test-task-123"
        self.user_id = 1
        self.admin_user_id = 2
        self.platform_connection_id = 1
    
    def test_log_job_action_basic(self):
        """Test basic job action logging"""
        # Mock JobAuditLog.log_action
        mock_audit_entry = Mock(spec=JobAuditLog)
        with patch.object(JobAuditLog, 'log_action', return_value=mock_audit_entry) as mock_log_action:
            
            result = self.audit_logger.log_job_action(
                task_id=self.task_id,
                user_id=self.user_id,
                action='created',
                details={'test': 'data'}
            )
            
            # Verify log_action was called with correct parameters
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args
            self.assertEqual(call_args[1]['task_id'], self.task_id)
            self.assertEqual(call_args[1]['user_id'], self.user_id)
            self.assertEqual(call_args[1]['action'], 'created')
            self.assertEqual(call_args[1]['details'], {'test': 'data'})
            
            # Verify session commit was called
            self.mock_session.commit.assert_called_once()
            
            # Verify return value
            self.assertEqual(result, mock_audit_entry)
    
    def test_log_job_action_with_flask_context(self):
        """Test job action logging with Flask request context"""
        # Mock Flask request and session objects
        mock_request = Mock()
        mock_request.headers.get.return_value = 'Test User Agent'
        mock_request.remote_addr = '192.168.1.1'
        
        mock_flask_session = Mock()
        mock_flask_session.get.return_value = 'test-session-id'
        
        # Mock _get_client_ip method
        with patch.object(self.audit_logger, '_get_client_ip', return_value='192.168.1.1'):
            with patch('audit_logger.request', mock_request):
                with patch('audit_logger.flask_session', mock_flask_session):
                    mock_audit_entry = Mock(spec=JobAuditLog)
                    with patch.object(JobAuditLog, 'log_action', return_value=mock_audit_entry) as mock_log_action:
                        
                        result = self.audit_logger.log_job_action(
                            task_id=self.task_id,
                            user_id=self.user_id,
                            action='created'
                        )
                        
                        # Verify context was auto-detected
                        call_args = mock_log_action.call_args
                        self.assertEqual(call_args[1]['ip_address'], '192.168.1.1')
                        self.assertEqual(call_args[1]['user_agent'], 'Test User Agent')
                        self.assertEqual(call_args[1]['session_id'], 'test-session-id')
    
    def test_log_job_creation(self):
        """Test job creation logging"""
        settings = {'max_posts': 10, 'platform': 'pixelfed'}
        
        with patch.object(self.audit_logger, 'log_job_action') as mock_log_action:
            mock_audit_entry = Mock(spec=JobAuditLog)
            mock_log_action.return_value = mock_audit_entry
            
            result = self.audit_logger.log_job_creation(
                task_id=self.task_id,
                user_id=self.user_id,
                platform_connection_id=self.platform_connection_id,
                settings=settings
            )
            
            # Verify log_job_action was called with correct parameters
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args
            self.assertEqual(call_args[1]['task_id'], self.task_id)
            self.assertEqual(call_args[1]['user_id'], self.user_id)
            self.assertEqual(call_args[1]['action'], 'created')
            self.assertEqual(call_args[1]['new_status'], 'queued')
            self.assertEqual(call_args[1]['platform_connection_id'], self.platform_connection_id)
            
            # Verify details contain settings
            details = call_args[1]['details']
            self.assertEqual(details['settings'], settings)
            self.assertEqual(details['action_type'], 'job_creation')
    
    def test_log_job_completion_success(self):
        """Test successful job completion logging"""
        results = {'images_processed': 5, 'captions_generated': 5, 'errors': 0}
        processing_time = 30000  # 30 seconds
        
        with patch.object(self.audit_logger, 'log_job_action') as mock_log_action:
            mock_audit_entry = Mock(spec=JobAuditLog)
            mock_log_action.return_value = mock_audit_entry
            
            result = self.audit_logger.log_job_completion(
                task_id=self.task_id,
                user_id=self.user_id,
                success=True,
                results=results,
                processing_time_ms=processing_time
            )
            
            # Verify log_job_action was called with correct parameters
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args
            self.assertEqual(call_args[1]['action'], 'completed')
            self.assertEqual(call_args[1]['previous_status'], 'running')
            self.assertEqual(call_args[1]['new_status'], 'completed')
            self.assertEqual(call_args[1]['processing_time_ms'], processing_time)
            
            # Verify details contain results
            details = call_args[1]['details']
            self.assertEqual(details['results'], results)
            self.assertTrue(details['success'])
            self.assertEqual(details['action_type'], 'job_completion')
    
    def test_log_job_completion_failure(self):
        """Test failed job completion logging"""
        results = {'images_processed': 2, 'captions_generated': 0, 'errors': 3}
        processing_time = 15000  # 15 seconds
        
        with patch.object(self.audit_logger, 'log_job_action') as mock_log_action:
            mock_audit_entry = Mock(spec=JobAuditLog)
            mock_log_action.return_value = mock_audit_entry
            
            result = self.audit_logger.log_job_completion(
                task_id=self.task_id,
                user_id=self.user_id,
                success=False,
                results=results,
                processing_time_ms=processing_time
            )
            
            # Verify log_job_action was called with correct parameters
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args
            self.assertEqual(call_args[1]['action'], 'failed')
            self.assertEqual(call_args[1]['new_status'], 'failed')
            
            # Verify details contain failure information
            details = call_args[1]['details']
            self.assertFalse(details['success'])
    
    def test_log_job_cancellation_user(self):
        """Test user job cancellation logging"""
        reason = "User requested cancellation"
        
        with patch.object(self.audit_logger, 'log_job_action') as mock_log_action:
            mock_audit_entry = Mock(spec=JobAuditLog)
            mock_log_action.return_value = mock_audit_entry
            
            result = self.audit_logger.log_job_cancellation(
                task_id=self.task_id,
                user_id=self.user_id,
                reason=reason
            )
            
            # Verify log_job_action was called with correct parameters
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args
            self.assertEqual(call_args[1]['action'], 'cancelled')
            self.assertEqual(call_args[1]['previous_status'], 'running')
            self.assertEqual(call_args[1]['new_status'], 'cancelled')
            self.assertIsNone(call_args[1]['admin_user_id'])
            
            # Verify details contain cancellation information
            details = call_args[1]['details']
            self.assertEqual(details['reason'], reason)
            self.assertFalse(details['cancelled_by_admin'])
    
    def test_log_job_cancellation_admin(self):
        """Test admin job cancellation logging"""
        reason = "Admin intervention - system maintenance"
        
        with patch.object(self.audit_logger, 'log_job_action') as mock_log_action:
            mock_audit_entry = Mock(spec=JobAuditLog)
            mock_log_action.return_value = mock_audit_entry
            
            result = self.audit_logger.log_job_cancellation(
                task_id=self.task_id,
                user_id=self.user_id,
                reason=reason,
                admin_user_id=self.admin_user_id
            )
            
            # Verify log_job_action was called with correct parameters
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args
            self.assertEqual(call_args[1]['admin_user_id'], self.admin_user_id)
            
            # Verify details contain admin cancellation information
            details = call_args[1]['details']
            self.assertTrue(details['cancelled_by_admin'])
    
    def test_log_admin_intervention(self):
        """Test admin intervention logging"""
        intervention_type = "priority_change"
        details = {'old_priority': 'normal', 'new_priority': 'high'}
        
        with patch.object(self.audit_logger, 'log_job_action') as mock_log_action:
            mock_audit_entry = Mock(spec=JobAuditLog)
            mock_log_action.return_value = mock_audit_entry
            
            result = self.audit_logger.log_admin_intervention(
                task_id=self.task_id,
                user_id=self.user_id,
                admin_user_id=self.admin_user_id,
                intervention_type=intervention_type,
                details=details
            )
            
            # Verify log_job_action was called with correct parameters
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args
            self.assertEqual(call_args[1]['action'], f'admin_{intervention_type}')
            self.assertEqual(call_args[1]['admin_user_id'], self.admin_user_id)
            
            # Verify details contain intervention information
            audit_details = call_args[1]['details']
            self.assertEqual(audit_details['intervention_type'], intervention_type)
            self.assertEqual(audit_details['action_type'], 'admin_intervention')
            self.assertEqual(audit_details['old_priority'], 'normal')
            self.assertEqual(audit_details['new_priority'], 'high')
    
    def test_query_audit_logs_basic(self):
        """Test basic audit log querying"""
        # Mock query results
        mock_logs = [Mock(spec=JobAuditLog) for _ in range(3)]
        mock_query = Mock()
        mock_query.all.return_value = mock_logs
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        self.mock_session.query.return_value = mock_query
        
        result = self.audit_logger.query_audit_logs(
            task_id=self.task_id,
            limit=10,
            offset=0
        )
        
        # Verify query was constructed correctly
        self.mock_session.query.assert_called_once_with(JobAuditLog)
        mock_query.filter.assert_called()
        mock_query.order_by.assert_called()
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(10)
        
        # Verify results
        self.assertEqual(result, mock_logs)
    
    def test_query_audit_logs_with_filters(self):
        """Test audit log querying with multiple filters"""
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        # Mock query results
        mock_logs = [Mock(spec=JobAuditLog)]
        mock_query = Mock()
        mock_query.all.return_value = mock_logs
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        self.mock_session.query.return_value = mock_query
        
        result = self.audit_logger.query_audit_logs(
            user_id=self.user_id,
            admin_user_id=self.admin_user_id,
            action='created',
            start_date=start_date,
            end_date=end_date,
            platform_connection_id=self.platform_connection_id,
            order_by='timestamp',
            order_direction='asc'
        )
        
        # Verify multiple filters were applied
        self.assertEqual(mock_query.filter.call_count, 6)  # All filters applied
        
        # Verify results
        self.assertEqual(result, mock_logs)
    
    def test_get_audit_statistics(self):
        """Test audit statistics generation"""
        # Mock query results
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.with_entities.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 100
        
        # Mock different query results for different statistics
        action_counts = [('created', 50), ('completed', 30), ('cancelled', 20)]
        user_activity = [(1, 40), (2, 35), (3, 25)]
        admin_activity = [(2, 15), (3, 10)]
        
        mock_query.all.side_effect = [action_counts, user_activity, admin_activity]
        
        self.mock_session.query.return_value = mock_query
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        result = self.audit_logger.get_audit_statistics(
            start_date=start_date,
            end_date=end_date,
            user_id=self.user_id
        )
        
        # Verify statistics structure
        self.assertIn('total_entries', result)
        self.assertIn('admin_interventions', result)
        self.assertIn('action_counts', result)
        self.assertIn('user_activity', result)
        self.assertIn('admin_activity', result)
        self.assertIn('date_range', result)
        
        # Verify statistics content
        self.assertEqual(result['action_counts'], dict(action_counts))
        self.assertEqual(result['user_activity'], dict(user_activity))
        self.assertEqual(result['admin_activity'], dict(admin_activity))
        self.assertEqual(result['date_range']['start'], start_date.isoformat())
        self.assertEqual(result['date_range']['end'], end_date.isoformat())
    
    def test_export_audit_logs_json(self):
        """Test audit log export in JSON format"""
        # Mock audit logs
        mock_log = Mock(spec=JobAuditLog)
        mock_log.id = 1
        mock_log.task_id = self.task_id
        mock_log.user_id = self.user_id
        mock_log.admin_user_id = None
        mock_log.action = 'created'
        mock_log.timestamp = datetime(2025, 1, 1, 12, 0, 0)
        mock_log.ip_address = '192.168.1.1'
        mock_log.user_agent = 'Test Agent'
        mock_log.session_id = 'test-session'
        mock_log.platform_connection_id = self.platform_connection_id
        mock_log.previous_status = None
        mock_log.new_status = 'queued'
        mock_log.error_code = None
        mock_log.processing_time_ms = None
        mock_log.get_details_dict.return_value = {'test': 'data'}
        
        with patch.object(self.audit_logger, 'query_audit_logs', return_value=[mock_log]):
            result = self.audit_logger.export_audit_logs(format_type='json')
            
            # Verify result is valid JSON
            export_data = json.loads(result)
            self.assertIn('export_timestamp', export_data)
            self.assertIn('total_records', export_data)
            self.assertIn('audit_logs', export_data)
            
            # Verify audit log data
            self.assertEqual(export_data['total_records'], 1)
            log_data = export_data['audit_logs'][0]
            self.assertEqual(log_data['id'], 1)
            self.assertEqual(log_data['task_id'], self.task_id)
            self.assertEqual(log_data['action'], 'created')
    
    def test_export_audit_logs_csv(self):
        """Test audit log export in CSV format"""
        # Mock audit logs
        mock_log = Mock(spec=JobAuditLog)
        mock_log.id = 1
        mock_log.task_id = self.task_id
        mock_log.user_id = self.user_id
        mock_log.admin_user_id = None
        mock_log.action = 'created'
        mock_log.timestamp = datetime(2025, 1, 1, 12, 0, 0)
        mock_log.ip_address = '192.168.1.1'
        mock_log.user_agent = 'Test Agent'
        mock_log.session_id = 'test-session'
        mock_log.platform_connection_id = self.platform_connection_id
        mock_log.previous_status = None
        mock_log.new_status = 'queued'
        mock_log.error_code = None
        mock_log.processing_time_ms = None
        mock_log.details = None
        mock_log.get_details_dict.return_value = {}
        
        with patch.object(self.audit_logger, 'query_audit_logs', return_value=[mock_log]):
            result = self.audit_logger.export_audit_logs(format_type='csv')
            
            # Verify result is CSV format
            lines = result.strip().split('\n')
            self.assertGreater(len(lines), 1)  # Header + data
            
            # Verify header
            header = lines[0]
            self.assertIn('id', header)
            self.assertIn('task_id', header)
            self.assertIn('action', header)
            
            # Verify data
            data_line = lines[1]
            self.assertIn(str(mock_log.id), data_line)
            self.assertIn(self.task_id, data_line)
            self.assertIn('created', data_line)
    
    def test_export_audit_logs_invalid_format(self):
        """Test audit log export with invalid format"""
        with self.assertRaises(ValueError) as context:
            self.audit_logger.export_audit_logs(format_type='xml')
        
        self.assertIn('Unsupported export format', str(context.exception))
    
    def test_cleanup_old_logs(self):
        """Test audit log cleanup functionality"""
        # Mock query and delete operations
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.delete.side_effect = [500, 300, 0]  # Simulate batch deletions
        
        self.mock_session.query.return_value = mock_query
        
        result = self.audit_logger.cleanup_old_logs(
            retention_days=365,
            batch_size=1000
        )
        
        # Verify total deleted count
        self.assertEqual(result, 800)  # 500 + 300
        
        # Verify delete was called multiple times
        self.assertEqual(mock_query.delete.call_count, 3)
        
        # Verify commit was called for each batch
        self.assertEqual(self.mock_session.commit.call_count, 2)  # Only for non-zero deletions
    
    def test_get_client_ip_x_forwarded_for(self):
        """Test client IP extraction from X-Forwarded-For header"""
        mock_request = Mock()
        mock_request.headers.get.side_effect = lambda header: {
            'X-Forwarded-For': '192.168.1.1, 10.0.0.1',
            'X-Real-IP': None
        }.get(header)
        
        with patch('audit_logger.request', mock_request):
            ip = self.audit_logger._get_client_ip()
            self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_x_real_ip(self):
        """Test client IP extraction from X-Real-IP header"""
        mock_request = Mock()
        mock_request.headers.get.side_effect = lambda header: {
            'X-Forwarded-For': None,
            'X-Real-IP': '192.168.1.2'
        }.get(header)
        
        with patch('audit_logger.request', mock_request):
            ip = self.audit_logger._get_client_ip()
            self.assertEqual(ip, '192.168.1.2')
    
    def test_get_client_ip_remote_addr(self):
        """Test client IP extraction from remote_addr"""
        mock_request = Mock()
        mock_request.headers.get.return_value = None
        mock_request.remote_addr = '192.168.1.3'
        
        with patch('audit_logger.request', mock_request):
            ip = self.audit_logger._get_client_ip()
            self.assertEqual(ip, '192.168.1.3')
    
    def test_get_client_ip_unknown(self):
        """Test client IP extraction when no IP available"""
        mock_request = Mock()
        mock_request.headers.get.return_value = None
        mock_request.remote_addr = None
        
        with patch('audit_logger.request', mock_request):
            ip = self.audit_logger._get_client_ip()
            self.assertEqual(ip, 'unknown')
    
    def test_error_handling_log_action(self):
        """Test error handling in log_job_action"""
        # Mock database error
        self.mock_session.commit.side_effect = Exception("Database error")
        
        with patch.object(JobAuditLog, 'log_action'):
            with self.assertRaises(Exception):
                self.audit_logger.log_job_action(
                    task_id=self.task_id,
                    user_id=self.user_id,
                    action='created'
                )
    
    def test_error_handling_query_logs(self):
        """Test error handling in query_audit_logs"""
        # Mock database error
        self.mock_session.query.side_effect = Exception("Query error")
        
        with self.assertRaises(Exception):
            self.audit_logger.query_audit_logs()
    
    def test_error_handling_cleanup(self):
        """Test error handling in cleanup_old_logs"""
        # Mock database error
        self.mock_session.query.side_effect = Exception("Cleanup error")
        
        with self.assertRaises(Exception):
            self.audit_logger.cleanup_old_logs()


if __name__ == '__main__':
    unittest.main()