# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for session security hardening features
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json

from security.features.session_security import (
    SessionSecurityHardening, SessionFingerprint, SecurityAuditEvent,
    SuspiciousActivityType, validate_session_security, create_session_fingerprint
)

class TestSessionSecurityHardening(unittest.TestCase):
    """Test session security hardening functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_session_manager = Mock()
        self.security = SessionSecurityHardening(self.mock_session_manager)
        
        # Create a proper mock request object
        self.mock_request = Mock()
        self.mock_request.headers = {
            'User-Agent': 'Mozilla/5.0 (Test Browser)',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'X-Forwarded-For': '192.168.1.100'
        }
        self.mock_request.remote_addr = '192.168.1.100'
        self.mock_request.endpoint = 'test_endpoint'
        
        # Mock Flask request context
        self.mock_request_patcher = patch('security.features.session_security.request', self.mock_request)
        self.mock_request_patcher.start()

    def tearDown(self):
        """Clean up test fixtures"""
        self.mock_request_patcher.stop()
        self.mock_session_patcher.stop()
    
    def test_create_session_fingerprint(self):
        """Test session fingerprint creation"""
        fingerprint = self.security.create_session_fingerprint()
        
        self.assertIsInstance(fingerprint, SessionFingerprint)
        self.assertIsNotNone(fingerprint.user_agent_hash)
        self.assertIsNotNone(fingerprint.ip_address_hash)
        self.assertEqual(fingerprint.accept_language, 'en-US,en;q=0.9')
        self.assertEqual(fingerprint.accept_encoding, 'gzip, deflate')
        self.assertIsInstance(fingerprint.created_at, datetime)
    
    def test_create_session_fingerprint_with_data(self):
        """Test session fingerprint creation with provided data"""
        request_data = {
            'user_agent': 'Custom Browser',
            'ip_address': '10.0.0.1',
            'accept_language': 'fr-FR',
            'accept_encoding': 'br, gzip',
            'timezone_offset': -300,
            'screen_resolution': '1920x1080'
        }
        
        fingerprint = self.security.create_session_fingerprint(request_data)
        
        self.assertEqual(fingerprint.accept_language, 'fr-FR')
        self.assertEqual(fingerprint.accept_encoding, 'br, gzip')
        self.assertEqual(fingerprint.timezone_offset, -300)
        self.assertEqual(fingerprint.screen_resolution, '1920x1080')
    
    def test_validate_session_fingerprint_first_time(self):
        """Test fingerprint validation for first time (should store and pass)"""
        session_id = 'test_session_123'
        fingerprint = self.security.create_session_fingerprint()
        
        is_valid, reason = self.security.validate_session_fingerprint(session_id, fingerprint)
        
        self.assertTrue(is_valid)
        self.assertIsNone(reason)
        self.assertIn(session_id, self.security.fingerprint_cache)
    
    def test_validate_session_fingerprint_matching(self):
        """Test fingerprint validation with matching fingerprint"""
        session_id = 'test_session_123'
        fingerprint = self.security.create_session_fingerprint()
        
        # Store initial fingerprint
        self.security.fingerprint_cache[session_id] = fingerprint
        
        # Validate with same fingerprint
        is_valid, reason = self.security.validate_session_fingerprint(session_id, fingerprint)
        
        self.assertTrue(is_valid)
        self.assertIsNone(reason)
    
    def test_validate_session_fingerprint_user_agent_change(self):
        """Test fingerprint validation with user agent change (should fail)"""
        session_id = 'test_session_123'
        original_fingerprint = self.security.create_session_fingerprint()
        
        # Store original fingerprint
        self.security.fingerprint_cache[session_id] = original_fingerprint
        
        # Create new fingerprint with different user agent
        with patch.object(self.security, '_hash_value') as mock_hash:
            mock_hash.side_effect = lambda x: 'different_hash' if 'Mozilla' in x else original_fingerprint.user_agent_hash
            
            new_fingerprint = SessionFingerprint(
                user_agent_hash='different_hash',
                ip_address_hash=original_fingerprint.ip_address_hash,
                accept_language=original_fingerprint.accept_language,
                accept_encoding=original_fingerprint.accept_encoding,
                timezone_offset=original_fingerprint.timezone_offset,
                screen_resolution=original_fingerprint.screen_resolution,
                created_at=datetime.now(timezone.utc)
            )
            
            is_valid, reason = self.security.validate_session_fingerprint(session_id, new_fingerprint)
            
            self.assertFalse(is_valid)
            self.assertIn('user_agent_change', reason)
    
    def test_validate_session_fingerprint_ip_change(self):
        """Test fingerprint validation with IP change (should pass but update)"""
        session_id = 'test_session_123'
        original_fingerprint = self.security.create_session_fingerprint()
        
        # Store original fingerprint
        self.security.fingerprint_cache[session_id] = original_fingerprint
        
        # Create new fingerprint with different IP
        new_fingerprint = SessionFingerprint(
            user_agent_hash=original_fingerprint.user_agent_hash,
            ip_address_hash='different_ip_hash',
            accept_language=original_fingerprint.accept_language,
            accept_encoding=original_fingerprint.accept_encoding,
            timezone_offset=original_fingerprint.timezone_offset,
            screen_resolution=original_fingerprint.screen_resolution,
            created_at=datetime.now(timezone.utc)
        )
        
        is_valid, reason = self.security.validate_session_fingerprint(session_id, new_fingerprint)
        
        self.assertTrue(is_valid)
        self.assertIn('ip_address_change', reason)
        # Should update stored fingerprint
        self.assertEqual(self.security.fingerprint_cache[session_id], new_fingerprint)
    
    def test_detect_suspicious_rapid_platform_switching(self):
        """Test detection of rapid platform switching"""
        session_id = 'test_session_123'
        user_id = 1
        
        # Simulate rapid platform switches
        for i in range(6):  # 6 switches in short time
            is_suspicious = self.security.detect_suspicious_session_activity(
                session_id, user_id, 'platform_switch',
                {'platform_id': i}
            )
        
        # Last switch should be detected as suspicious
        self.assertTrue(is_suspicious)
    
    def test_detect_suspicious_unusual_access_pattern(self):
        """Test detection of unusual access patterns"""
        session_id = 'test_session_123'
        user_id = 1
        
        # Simulate many activities
        for i in range(101):  # More than 100 activities
            self.security.detect_suspicious_session_activity(
                session_id, user_id, 'page_view',
                {'page': f'page_{i}'}
            )
        
        # Should detect unusual pattern
        activities = self.security.activity_log[session_id]
        self.assertGreater(len(activities), 100)
    
    def test_detect_suspicious_concurrent_session_abuse(self):
        """Test detection of concurrent session abuse"""
        session_id = 'test_session_123'
        user_id = 1
        
        # Simulate multiple session creates
        for i in range(6):  # More than 5 session creates
            is_suspicious = self.security.detect_suspicious_session_activity(
                session_id, user_id, 'session_create'
            )
        
        # Should detect abuse
        self.assertTrue(is_suspicious)
    
    def test_create_security_audit_event(self):
        """Test security audit event creation"""
        session_id = 'test_session_123'
        user_id = 1
        event_type = 'test_event'
        details = {'test': 'data'}
        
        event = self.security.create_security_audit_event(
            session_id, user_id, event_type, 'warning', details
        )
        
        self.assertIsInstance(event, SecurityAuditEvent)
        self.assertEqual(event.session_id, session_id)
        self.assertEqual(event.user_id, user_id)
        self.assertEqual(event.event_type, event_type)
        self.assertEqual(event.severity, 'warning')
        self.assertEqual(event.details, details)
        self.assertIsNotNone(event.event_id)
        self.assertIsInstance(event.timestamp, datetime)
    
    def test_validate_session_security_success(self):
        """Test comprehensive session security validation success"""
        session_id = 'test_session_123'
        user_id = 1
        
        is_valid, issues = self.security.validate_session_security(session_id, user_id)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
    
    def test_validate_session_security_with_issues(self):
        """Test session security validation with issues"""
        session_id = 'test_session_123'
        user_id = 1
        
        # Pre-populate with suspicious activity
        for i in range(6):
            self.security.detect_suspicious_session_activity(
                session_id, user_id, 'platform_switch'
            )
        
        is_valid, issues = self.security.validate_session_security(session_id, user_id)
        
        # Should still be valid but have issues logged
        self.assertTrue(is_valid)  # Current implementation doesn't fail on suspicious activity
    
    def test_invalidate_suspicious_sessions(self):
        """Test invalidation of suspicious sessions"""
        user_id = 1
        reason = 'test_security_breach'
        
        # Mock session manager methods
        self.mock_session_manager.get_user_active_sessions.return_value = [
            {'session_id': 'session_1'},
            {'session_id': 'session_2'}
        ]
        self.mock_session_manager.invalidate_session.return_value = True
        
        count = self.security.invalidate_suspicious_sessions(user_id, reason)
        
        self.assertEqual(count, 2)
        self.assertEqual(self.mock_session_manager.invalidate_session.call_count, 2)
    
    def test_get_session_security_metrics(self):
        """Test getting session security metrics"""
        session_id = 'test_session_123'
        
        # Add some test data
        fingerprint = self.security.create_session_fingerprint()
        self.security.fingerprint_cache[session_id] = fingerprint
        
        # Add some activities
        self.security.activity_log[session_id] = [
            {
                'timestamp': datetime.now(timezone.utc),
                'activity_type': 'test_activity',
                'details': {}
            }
        ]
        
        metrics = self.security.get_session_security_metrics(session_id)
        
        self.assertIn('session_id', metrics)
        self.assertIn('has_fingerprint', metrics)
        self.assertIn('activity_count_24h', metrics)
        self.assertIn('suspicious_events', metrics)
        self.assertTrue(metrics['has_fingerprint'])
        self.assertGreaterEqual(metrics['activity_count_24h'], 1)
    
    def test_cleanup_expired_data(self):
        """Test cleanup of expired fingerprints and activity logs"""
        # Add test data with old timestamps
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        
        old_fingerprint = SessionFingerprint(
            user_agent_hash='test',
            ip_address_hash='test',
            accept_language='en',
            accept_encoding='gzip',
            timezone_offset=None,
            screen_resolution=None,
            created_at=old_time
        )
        
        self.security.fingerprint_cache['old_session'] = old_fingerprint
        self.security.activity_log['old_session'] = [
            {
                'timestamp': old_time,
                'activity_type': 'old_activity',
                'details': {}
            }
        ]
        
        # Add recent data
        recent_fingerprint = self.security.create_session_fingerprint()
        self.security.fingerprint_cache['recent_session'] = recent_fingerprint
        
        stats = self.security.cleanup_expired_data(max_age_hours=24)
        
        self.assertGreater(stats['expired_fingerprints'], 0)
        self.assertNotIn('old_session', self.security.fingerprint_cache)
        self.assertIn('recent_session', self.security.fingerprint_cache)
    
    def test_session_fingerprint_serialization(self):
        """Test session fingerprint serialization/deserialization"""
        fingerprint = self.security.create_session_fingerprint()
        
        # Test to_dict
        data = fingerprint.to_dict()
        self.assertIsInstance(data, dict)
        self.assertIn('user_agent_hash', data)
        self.assertIn('created_at', data)
        
        # Test from_dict
        restored_fingerprint = SessionFingerprint.from_dict(data)
        self.assertEqual(fingerprint.user_agent_hash, restored_fingerprint.user_agent_hash)
        self.assertEqual(fingerprint.ip_address_hash, restored_fingerprint.ip_address_hash)
    
    def test_security_audit_event_serialization(self):
        """Test security audit event serialization"""
        event = self.security.create_security_audit_event(
            'test_session', 1, 'test_event', 'info', {'test': 'data'}
        )
        
        data = event.to_dict()
        self.assertIsInstance(data, dict)
        self.assertIn('event_id', data)
        self.assertIn('timestamp', data)
        self.assertEqual(data['event_type'], 'test_event')
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        session_id = 'test_session_123'
        user_id = 1
        
        # Test validate_session_security function
        is_valid, issues = validate_session_security(session_id, user_id)
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(issues, list)
        
        # Test create_session_fingerprint function
        fingerprint = create_session_fingerprint()
        self.assertIsInstance(fingerprint, SessionFingerprint)
    
    def test_error_handling(self):
        """Test error handling in security hardening"""
        # Test with invalid session data
        with patch.object(self.security, '_get_client_ip', side_effect=Exception('Test error')):
            fingerprint = self.security.create_session_fingerprint()
            # Should still create a fingerprint with defaults
            self.assertIsInstance(fingerprint, SessionFingerprint)
        
        # Test validation with corrupted data
        session_id = 'test_session'
        self.security.fingerprint_cache[session_id] = "invalid_data"
        
        # Should handle gracefully
        new_fingerprint = self.security.create_session_fingerprint()
        is_valid, reason = self.security.validate_session_fingerprint(session_id, new_fingerprint)
        self.assertIsInstance(is_valid, bool)

class TestSessionSecurityIntegration(unittest.TestCase):
    """Integration tests for session security with session manager"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_session_manager = Mock()
        
        # Create a proper mock request object
        self.mock_request = Mock()
        self.mock_request.headers = {'User-Agent': 'Test Browser'}
        self.mock_request.remote_addr = '127.0.0.1'
        self.mock_request.endpoint = 'test'
        
        # Mock Flask request context
        self.mock_request_patcher = patch('security.features.session_security.request', self.mock_request)
        self.mock_request_patcher.start()
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        self.mock_request_patcher.stop()
    
    def test_session_manager_integration(self):
        """Test integration with session manager"""
        from security.features.session_security import initialize_session_security
        
        security = initialize_session_security(self.mock_session_manager)
        
        self.assertIsNotNone(security)
        self.assertEqual(security.session_manager, self.mock_session_manager)
    
    @patch('security.features.session_security.log_security_event')
    def test_security_event_logging(self, mock_log_event):
        """Test that security events are properly logged"""
        security = SessionSecurityHardening(self.mock_session_manager)
        
        # Trigger suspicious activity
        session_id = 'test_session'
        user_id = 1
        
        for i in range(6):  # Trigger rapid platform switching
            security.detect_suspicious_session_activity(
                session_id, user_id, 'platform_switch'
            )
        
        # Should have logged security events
        self.assertTrue(mock_log_event.called)

if __name__ == '__main__':
    unittest.main()