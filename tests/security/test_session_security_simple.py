# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simple tests for session security hardening features without Flask context
"""

import unittest
from unittest.mock import Mock
from datetime import datetime, timezone, timedelta

from security.features.session_security import (
    SessionSecurityHardening, SessionFingerprint, SecurityAuditEvent,
    SuspiciousActivityType
)


class TestSessionSecurityBasic(unittest.TestCase):
    """Basic tests for session security hardening functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_session_manager = Mock()
        self.security = SessionSecurityHardening(self.mock_session_manager)
    
    def test_session_fingerprint_creation_with_data(self):
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
        
        self.assertIsInstance(fingerprint, SessionFingerprint)
        self.assertEqual(fingerprint.accept_language, 'fr-FR')
        self.assertEqual(fingerprint.accept_encoding, 'br, gzip')
        self.assertEqual(fingerprint.timezone_offset, -300)
        self.assertEqual(fingerprint.screen_resolution, '1920x1080')
        self.assertIsNotNone(fingerprint.user_agent_hash)
        self.assertIsNotNone(fingerprint.ip_address_hash)
    
    def test_session_fingerprint_serialization(self):
        """Test session fingerprint serialization/deserialization"""
        request_data = {
            'user_agent': 'Test Browser',
            'ip_address': '192.168.1.1',
            'accept_language': 'en-US',
            'accept_encoding': 'gzip'
        }
        
        fingerprint = self.security.create_session_fingerprint(request_data)
        
        # Test to_dict
        data = fingerprint.to_dict()
        self.assertIsInstance(data, dict)
        self.assertIn('user_agent_hash', data)
        self.assertIn('created_at', data)
        
        # Test from_dict
        restored_fingerprint = SessionFingerprint.from_dict(data)
        self.assertEqual(fingerprint.user_agent_hash, restored_fingerprint.user_agent_hash)
        self.assertEqual(fingerprint.ip_address_hash, restored_fingerprint.ip_address_hash)
        self.assertEqual(fingerprint.accept_language, restored_fingerprint.accept_language)
    
    def test_validate_session_fingerprint_first_time(self):
        """Test fingerprint validation for first time (should store and pass)"""
        session_id = 'test_session_123'
        request_data = {'user_agent': 'Test Browser', 'ip_address': '127.0.0.1'}
        fingerprint = self.security.create_session_fingerprint(request_data)
        
        is_valid, reason = self.security.validate_session_fingerprint(session_id, fingerprint)
        
        self.assertTrue(is_valid)
        self.assertIsNone(reason)
        self.assertIn(session_id, self.security.fingerprint_cache)
    
    def test_validate_session_fingerprint_matching(self):
        """Test fingerprint validation with matching fingerprint"""
        session_id = 'test_session_123'
        request_data = {'user_agent': 'Test Browser', 'ip_address': '127.0.0.1'}
        fingerprint = self.security.create_session_fingerprint(request_data)
        
        # Store initial fingerprint
        self.security.fingerprint_cache[session_id] = fingerprint
        
        # Validate with same fingerprint
        is_valid, reason = self.security.validate_session_fingerprint(session_id, fingerprint)
        
        self.assertTrue(is_valid)
        self.assertIsNone(reason)
    
    def test_validate_session_fingerprint_user_agent_change(self):
        """Test fingerprint validation with user agent change (should fail)"""
        session_id = 'test_session_123'
        
        # Create original fingerprint
        original_data = {'user_agent': 'Original Browser', 'ip_address': '127.0.0.1'}
        original_fingerprint = self.security.create_session_fingerprint(original_data)
        self.security.fingerprint_cache[session_id] = original_fingerprint
        
        # Create new fingerprint with different user agent
        new_data = {'user_agent': 'Different Browser', 'ip_address': '127.0.0.1'}
        new_fingerprint = self.security.create_session_fingerprint(new_data)
        
        is_valid, reason = self.security.validate_session_fingerprint(session_id, new_fingerprint)
        
        self.assertFalse(is_valid)
        self.assertIn('user_agent_change', reason)
    
    def test_validate_session_fingerprint_ip_change(self):
        """Test fingerprint validation with IP change (should pass but update)"""
        session_id = 'test_session_123'
        
        # Create original fingerprint
        original_data = {'user_agent': 'Test Browser', 'ip_address': '127.0.0.1'}
        original_fingerprint = self.security.create_session_fingerprint(original_data)
        self.security.fingerprint_cache[session_id] = original_fingerprint
        
        # Create new fingerprint with different IP
        new_data = {'user_agent': 'Test Browser', 'ip_address': '192.168.1.1'}
        new_fingerprint = self.security.create_session_fingerprint(new_data)
        
        is_valid, reason = self.security.validate_session_fingerprint(session_id, new_fingerprint)
        
        self.assertTrue(is_valid)
        self.assertIn('ip_address_change', reason)
        # Should update stored fingerprint
        self.assertEqual(self.security.fingerprint_cache[session_id], new_fingerprint)
    
    def test_detect_suspicious_rapid_platform_switching(self):
        """Test detection of rapid platform switching"""
        session_id = 'test_session_123'
        user_id = 1
        
        # Simulate rapid platform switches within 5 minutes
        current_time = datetime.now(timezone.utc)
        
        # First add 11 switches over 24h to meet the threshold
        for i in range(11):
            self.security.activity_log.setdefault(session_id, []).append({
                'timestamp': current_time - timedelta(hours=i),
                'activity_type': 'platform_switch',
                'details': {'platform_id': i}
            })
        
        # Now add 5 switches in quick succession (within 5 minutes)
        for i in range(5):
            self.security.activity_log[session_id].append({
                'timestamp': current_time,
                'activity_type': 'platform_switch',
                'details': {'platform_id': i + 100}
            })
        
        # The next switch should trigger suspicious detection
        is_suspicious = self.security.detect_suspicious_session_activity(
            session_id, user_id, 'platform_switch',
            {'platform_id': 999}
        )
        
        # Should be detected as suspicious
        self.assertTrue(is_suspicious)
    
    def test_detect_suspicious_unusual_access_pattern(self):
        """Test detection of unusual access patterns"""
        session_id = 'test_session_123'
        user_id = 1
        
        # Simulate many activities
        is_suspicious = False
        for i in range(101):  # More than 100 activities
            is_suspicious = self.security.detect_suspicious_session_activity(
                session_id, user_id, 'page_view',
                {'page': f'page_{i}'}
            )
        
        # Should detect unusual pattern
        self.assertTrue(is_suspicious)
        activities = self.security.activity_log[session_id]
        self.assertGreater(len(activities), 100)
    
    def test_detect_suspicious_concurrent_session_abuse(self):
        """Test detection of concurrent session abuse"""
        session_id = 'test_session_123'
        user_id = 1
        
        # Simulate multiple session creates
        is_suspicious = False
        for i in range(6):  # More than 5 session creates
            is_suspicious = self.security.detect_suspicious_session_activity(
                session_id, user_id, 'session_create'
            )
        
        # Should detect abuse
        self.assertTrue(is_suspicious)
    
    def test_get_session_security_metrics(self):
        """Test getting session security metrics"""
        session_id = 'test_session_123'
        
        # Add some test data
        request_data = {'user_agent': 'Test Browser', 'ip_address': '127.0.0.1'}
        fingerprint = self.security.create_session_fingerprint(request_data)
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
        request_data = {'user_agent': 'Test Browser', 'ip_address': '127.0.0.1'}
        recent_fingerprint = self.security.create_session_fingerprint(request_data)
        self.security.fingerprint_cache['recent_session'] = recent_fingerprint
        
        stats = self.security.cleanup_expired_data(max_age_hours=24)
        
        self.assertGreater(stats['expired_fingerprints'], 0)
        self.assertNotIn('old_session', self.security.fingerprint_cache)
        self.assertIn('recent_session', self.security.fingerprint_cache)
    
    def test_security_audit_event_creation(self):
        """Test security audit event creation without Flask context"""
        session_id = 'test_session_123'
        user_id = 1
        event_type = 'test_event'
        details = {'test': 'data'}
        
        # Mock the methods that require Flask context
        with unittest.mock.patch.object(self.security, '_get_client_ip', return_value='127.0.0.1'):
            with unittest.mock.patch.object(self.security, '_log_audit_event'):
                # Create a mock request object
                mock_request = unittest.mock.Mock()
                mock_request.headers = {'User-Agent': 'Test Browser'}
                
                with unittest.mock.patch('security.features.session_security.request', mock_request):
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
    
    def test_security_audit_event_serialization(self):
        """Test security audit event serialization"""
        event = SecurityAuditEvent(
            event_id='test_id',
            session_id='test_session',
            user_id=1,
            event_type='test_event',
            severity='info',
            timestamp=datetime.now(timezone.utc),
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            details={'test': 'data'}
        )
        
        data = event.to_dict()
        self.assertIsInstance(data, dict)
        self.assertIn('event_id', data)
        self.assertIn('timestamp', data)
        self.assertEqual(data['event_type'], 'test_event')
    
    def test_error_handling(self):
        """Test error handling in security hardening"""
        # Test with invalid session data
        fingerprint = self.security.create_session_fingerprint({'invalid': 'data'})
        # Should still create a fingerprint with defaults
        self.assertIsInstance(fingerprint, SessionFingerprint)
        
        # Test validation with corrupted data
        session_id = 'test_session'
        self.security.fingerprint_cache[session_id] = "invalid_data"
        
        # Should handle gracefully
        request_data = {'user_agent': 'Test Browser', 'ip_address': '127.0.0.1'}
        new_fingerprint = self.security.create_session_fingerprint(request_data)
        is_valid, reason = self.security.validate_session_fingerprint(session_id, new_fingerprint)
        self.assertIsInstance(is_valid, bool)
    
    def test_hash_value_method(self):
        """Test the hash value method"""
        # Test with normal value
        hash1 = self.security._hash_value('test_value')
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 16)  # Should be truncated to 16 chars
        
        # Test with empty value
        hash2 = self.security._hash_value('')
        self.assertIsInstance(hash2, str)
        self.assertEqual(len(hash2), 16)
        
        # Test consistency
        hash3 = self.security._hash_value('test_value')
        self.assertEqual(hash1, hash3)


if __name__ == '__main__':
    unittest.main()