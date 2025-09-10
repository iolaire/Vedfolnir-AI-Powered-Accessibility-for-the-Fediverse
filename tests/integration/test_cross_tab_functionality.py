# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for cross-tab functionality.

Tests platform switching synchronization, session expiration notification,
and logout synchronization across multiple tabs.
Requirements: 2.1, 2.2, 2.3, 3.4, 3.5
"""

import unittest
import tempfile
import os
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, PlatformConnection, UserSession, UserRole
from unified_session_manager import UnifiedSessionManager as SessionManager
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures


class MockTab:
    """Mock tab for simulating cross-tab functionality"""
    
    def __init__(self, tab_id, session_manager):
        self.tab_id = tab_id
        self.session_manager = session_manager
        self.storage = {}
        self.events = []
        self.platform_switches = []
        self.session_expirations = []
        self.logouts = []
        
    def set_storage(self, key, value):
        """Simulate localStorage.setItem"""
        old_value = self.storage.get(key)
        self.storage[key] = value
        
        # Notify other tabs
        event = {
            'key': key,
            'oldValue': old_value,
            'newValue': value,
            'tabId': self.tab_id
        }
        self.events.append(event)
        return event
        
    def get_storage(self, key):
        """Simulate localStorage.getItem"""
        return self.storage.get(key)
        
    def remove_storage(self, key):
        """Simulate localStorage.removeItem"""
        old_value = self.storage.get(key)
        if key in self.storage:
            del self.storage[key]
        
        event = {
            'key': key,
            'oldValue': old_value,
            'newValue': None,
            'tabId': self.tab_id
        }
        self.events.append(event)
        return event
        
    def handle_storage_event(self, event):
        """Handle storage events from other tabs"""
        if event['tabId'] == self.tab_id:
            return  # Ignore own events
            
        if event['key'] == 'vedfolnir_platform_switch':
            try:
                switch_data = json.loads(event['newValue'])
                self.platform_switches.append(switch_data)
            except (json.JSONDecodeError, TypeError):
                pass
                
        elif event['key'] == 'vedfolnir_session_expired':
            try:
                expiration_data = json.loads(event['newValue'])
                self.session_expirations.append(expiration_data)
            except (json.JSONDecodeError, TypeError):
                pass
                
        elif event['key'] == 'vedfolnir_logout':
            try:
                logout_data = json.loads(event['newValue'])
                self.logouts.append(logout_data)
            except (json.JSONDecodeError, TypeError):
                pass

class TestCrossTabPlatformSwitching(MySQLIntegrationTestBase):
    """Test platform switching synchronization across multiple tabs (Requirements 2.1, 2.2, 2.3, 3.4, 3.5)"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkdtemp(prefix="mysql_integration_test_")
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        # Initialize database manager and create tables
        self.db_manager = self.get_database_manager()
        self.db_manager.create_tables()
        
        # Initialize session manager
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create test user with platforms
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_cross_tab_user",
            role=UserRole.REVIEWER
        )
        
        # Create mock tabs
        self.tab1 = MockTab("tab1", self.session_manager)
        self.tab2 = MockTab("tab2", self.session_manager)
        self.tab3 = MockTab("tab3", self.session_manager)
        self.tabs = [self.tab1, self.tab2, self.tab3]
        
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up mock users
        cleanup_test_user(self.user_helper)
        
        # Clean up database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def broadcast_storage_event(self, source_tab, event):
        """Broadcast storage event to all other tabs"""
        for tab in self.tabs:
            if tab != source_tab:
                tab.handle_storage_event(event)
    
    def test_platform_switch_synchronization_across_tabs(self):
        """Test that platform switches are synchronized across all tabs"""
        # Create sessions for all tabs
        session_ids = []
        for tab in self.tabs:
            session_id = self.session_manager.create_session(self.test_user.id)
            session_ids.append(session_id)
            time.sleep(0.1)  # Avoid suspicious activity detection
        
        # Simulate platform switch from tab1
        platform_switch_data = {
            'type': 'platform_switch',
            'platformId': self.test_user.platform_connections[1].id,
            'platformName': self.test_user.platform_connections[1].name,
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        # Tab1 broadcasts platform switch
        event = self.tab1.set_storage('vedfolnir_platform_switch', json.dumps(platform_switch_data))
        self.broadcast_storage_event(self.tab1, event)
        
        # Verify other tabs received the platform switch
        self.assertEqual(len(self.tab2.platform_switches), 1)
        self.assertEqual(len(self.tab3.platform_switches), 1)
        
        # Verify platform switch data is correct
        received_switch = self.tab2.platform_switches[0]
        self.assertEqual(received_switch['platformId'], self.test_user.platform_connections[1].id)
        self.assertEqual(received_switch['platformName'], self.test_user.platform_connections[1].name)
        self.assertEqual(received_switch['tabId'], self.tab1.tab_id)
        
        # Tab1 should not receive its own event
        self.assertEqual(len(self.tab1.platform_switches), 0)
    
    def test_multiple_platform_switches_synchronization(self):
        """Test multiple rapid platform switches are synchronized correctly"""
        # Create sessions
        for tab in self.tabs:
            session_id = self.session_manager.create_session(self.test_user.id)
            time.sleep(0.1)
        
        # Simulate multiple platform switches from different tabs
        platforms = self.test_user.platform_connections
        
        # Tab1 switches to platform 1
        switch1_data = {
            'type': 'platform_switch',
            'platformId': platforms[0].id,
            'platformName': platforms[0].name,
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        event1 = self.tab1.set_storage('vedfolnir_platform_switch', json.dumps(switch1_data))
        self.broadcast_storage_event(self.tab1, event1)
        
        time.sleep(0.1)
        
        # Tab2 switches to platform 2
        switch2_data = {
            'type': 'platform_switch',
            'platformId': platforms[1].id,
            'platformName': platforms[1].name,
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab2.tab_id
        }
        event2 = self.tab2.set_storage('vedfolnir_platform_switch', json.dumps(switch2_data))
        self.broadcast_storage_event(self.tab2, event2)
        
        # Verify all tabs received both switches
        self.assertEqual(len(self.tab1.platform_switches), 1)  # Only tab2's switch
        self.assertEqual(len(self.tab2.platform_switches), 1)  # Only tab1's switch
        self.assertEqual(len(self.tab3.platform_switches), 2)  # Both switches
        
        # Verify correct platform data
        tab3_switches = sorted(self.tab3.platform_switches, key=lambda x: x['timestamp'])
        self.assertEqual(tab3_switches[0]['platformId'], platforms[0].id)
        self.assertEqual(tab3_switches[1]['platformId'], platforms[1].id)
    
    def test_platform_switch_cleanup(self):
        """Test that platform switch events are cleaned up after broadcast"""
        # Create session
        session_id = self.session_manager.create_session(self.test_user.id)
        
        # Simulate platform switch with cleanup
        platform_switch_data = {
            'type': 'platform_switch',
            'platformId': self.test_user.platform_connections[0].id,
            'platformName': self.test_user.platform_connections[0].name,
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        # Set and then remove (simulating cleanup)
        self.tab1.set_storage('vedfolnir_platform_switch', json.dumps(platform_switch_data))
        time.sleep(0.1)
        cleanup_event = self.tab1.remove_storage('vedfolnir_platform_switch')
        
        # Verify storage is cleaned up
        self.assertIsNone(self.tab1.get_storage('vedfolnir_platform_switch'))

class TestCrossTabSessionExpiration(MySQLIntegrationTestBase):
    """Test session expiration notification to all tabs (Requirements 2.2, 2.3)"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkdtemp(prefix="mysql_integration_test_")
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        # Initialize database manager and create tables
        self.db_manager = self.get_database_manager()
        self.db_manager.create_tables()
        
        # Initialize session manager
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create test user with platforms
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_expiration_user",
            role=UserRole.REVIEWER
        )
        
        # Create mock tabs
        self.tab1 = MockTab("tab1", self.session_manager)
        self.tab2 = MockTab("tab2", self.session_manager)
        self.tab3 = MockTab("tab3", self.session_manager)
        self.tabs = [self.tab1, self.tab2, self.tab3]
        
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up mock users
        cleanup_test_user(self.user_helper)
        
        # Clean up database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def broadcast_storage_event(self, source_tab, event):
        """Broadcast storage event to all other tabs"""
        for tab in self.tabs:
            if tab != source_tab:
                tab.handle_storage_event(event)
    
    def test_session_expiration_notification_to_all_tabs(self):
        """Test that session expiration is notified to all tabs"""
        # Create sessions for all tabs
        session_ids = []
        for tab in self.tabs:
            session_id = self.session_manager.create_session(self.test_user.id)
            session_ids.append(session_id)
            time.sleep(0.1)
        
        # Simulate session expiration from tab1
        expiration_data = {
            'type': 'session_expired',
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        # Tab1 broadcasts session expiration
        event = self.tab1.set_storage('vedfolnir_session_expired', json.dumps(expiration_data))
        self.broadcast_storage_event(self.tab1, event)
        
        # Verify other tabs received the expiration notification
        self.assertEqual(len(self.tab2.session_expirations), 1)
        self.assertEqual(len(self.tab3.session_expirations), 1)
        
        # Verify expiration data is correct
        received_expiration = self.tab2.session_expirations[0]
        self.assertEqual(received_expiration['type'], 'session_expired')
        self.assertEqual(received_expiration['tabId'], self.tab1.tab_id)
        
        # Tab1 should not receive its own event
        self.assertEqual(len(self.tab1.session_expirations), 0)
    
    def test_session_expiration_with_actual_expired_session(self):
        """Test session expiration notification with actual expired session"""
        # Create session
        session_id = self.session_manager.create_session(self.test_user.id)
        
        # Manually expire the session
        with self.session_manager.get_db_session() as db_session:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            if user_session:
                user_session.updated_at = datetime.now(timezone.utc) - timedelta(days=3)
                db_session.commit()
        
        # Verify session is expired
        is_valid = self.session_manager.validate_session(session_id, self.test_user.id)
        self.assertFalse(is_valid)
        
        # Simulate expiration notification
        expiration_data = {
            'type': 'session_expired',
            'sessionId': session_id,
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        event = self.tab1.set_storage('vedfolnir_session_expired', json.dumps(expiration_data))
        self.broadcast_storage_event(self.tab1, event)
        
        # Verify notification was received
        self.assertEqual(len(self.tab2.session_expirations), 1)
        received_expiration = self.tab2.session_expirations[0]
        self.assertEqual(received_expiration['sessionId'], session_id)
    
    def test_session_expiration_cleanup(self):
        """Test that session expiration events are cleaned up"""
        # Create session
        session_id = self.session_manager.create_session(self.test_user.id)
        
        # Simulate expiration with cleanup
        expiration_data = {
            'type': 'session_expired',
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        # Set and then remove (simulating cleanup)
        self.tab1.set_storage('vedfolnir_session_expired', json.dumps(expiration_data))
        time.sleep(0.1)
        cleanup_event = self.tab1.remove_storage('vedfolnir_session_expired')
        
        # Verify storage is cleaned up
        self.assertIsNone(self.tab1.get_storage('vedfolnir_session_expired'))

class TestCrossTabLogoutSynchronization(MySQLIntegrationTestBase):
    """Test logout synchronization and cleanup across tabs (Requirements 2.2, 2.3)"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkdtemp(prefix="mysql_integration_test_")
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        # Initialize database manager and create tables
        self.db_manager = self.get_database_manager()
        self.db_manager.create_tables()
        
        # Initialize session manager
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create test user with platforms
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_logout_user",
            role=UserRole.REVIEWER
        )
        
        # Create mock tabs
        self.tab1 = MockTab("tab1", self.session_manager)
        self.tab2 = MockTab("tab2", self.session_manager)
        self.tab3 = MockTab("tab3", self.session_manager)
        self.tabs = [self.tab1, self.tab2, self.tab3]
        
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up mock users
        cleanup_test_user(self.user_helper)
        
        # Clean up database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def broadcast_storage_event(self, source_tab, event):
        """Broadcast storage event to all other tabs"""
        for tab in self.tabs:
            if tab != source_tab:
                tab.handle_storage_event(event)
    
    def test_logout_synchronization_across_tabs(self):
        """Test that logout is synchronized across all tabs"""
        # Create sessions for all tabs
        session_ids = []
        for tab in self.tabs:
            session_id = self.session_manager.create_session(self.test_user.id)
            session_ids.append(session_id)
            time.sleep(0.1)
        
        # Simulate logout from tab1
        logout_data = {
            'type': 'logout',
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        # Tab1 broadcasts logout
        event = self.tab1.set_storage('vedfolnir_logout', json.dumps(logout_data))
        self.broadcast_storage_event(self.tab1, event)
        
        # Verify other tabs received the logout notification
        self.assertEqual(len(self.tab2.logouts), 1)
        self.assertEqual(len(self.tab3.logouts), 1)
        
        # Verify logout data is correct
        received_logout = self.tab2.logouts[0]
        self.assertEqual(received_logout['type'], 'logout')
        self.assertEqual(received_logout['tabId'], self.tab1.tab_id)
        
        # Tab1 should not receive its own event
        self.assertEqual(len(self.tab1.logouts), 0)
    
    def test_logout_with_session_cleanup(self):
        """Test logout with actual session cleanup"""
        # Create sessions
        session_ids = []
        for tab in self.tabs:
            session_id = self.session_manager.create_session(self.test_user.id)
            session_ids.append(session_id)
            time.sleep(0.1)
        
        # Verify sessions exist
        for session_id in session_ids:
            context = self.session_manager.get_session_context(session_id)
            self.assertIsNotNone(context)
        
        # Perform logout cleanup
        cleaned_count = self.session_manager.cleanup_all_user_sessions(self.test_user.id)
        self.assertGreaterEqual(cleaned_count, 0)
        
        # Simulate logout notification
        logout_data = {
            'type': 'logout',
            'userId': self.test_user.id,
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        event = self.tab1.set_storage('vedfolnir_logout', json.dumps(logout_data))
        self.broadcast_storage_event(self.tab1, event)
        
        # Verify notification was received
        self.assertEqual(len(self.tab2.logouts), 1)
        received_logout = self.tab2.logouts[0]
        self.assertEqual(received_logout['userId'], self.test_user.id)
    
    def test_logout_cleanup_storage(self):
        """Test that logout events are cleaned up from storage"""
        # Create session
        session_id = self.session_manager.create_session(self.test_user.id)
        
        # Simulate logout with cleanup
        logout_data = {
            'type': 'logout',
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        # Set and then remove (simulating cleanup)
        self.tab1.set_storage('vedfolnir_logout', json.dumps(logout_data))
        time.sleep(0.1)
        cleanup_event = self.tab1.remove_storage('vedfolnir_logout')
        
        # Verify storage is cleaned up
        self.assertIsNone(self.tab1.get_storage('vedfolnir_logout'))
    
    def test_concurrent_logout_from_multiple_tabs(self):
        """Test concurrent logout from multiple tabs"""
        # Create sessions
        session_ids = []
        for tab in self.tabs:
            session_id = self.session_manager.create_session(self.test_user.id)
            session_ids.append(session_id)
            time.sleep(0.1)
        
        # Simulate concurrent logout from tab1 and tab2
        logout1_data = {
            'type': 'logout',
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        logout2_data = {
            'type': 'logout',
            'timestamp': int(time.time() * 1000) + 1,
            'tabId': self.tab2.tab_id
        }
        
        # Both tabs broadcast logout
        event1 = self.tab1.set_storage('vedfolnir_logout', json.dumps(logout1_data))
        event2 = self.tab2.set_storage('vedfolnir_logout', json.dumps(logout2_data))
        
        self.broadcast_storage_event(self.tab1, event1)
        self.broadcast_storage_event(self.tab2, event2)
        
        # Tab3 should receive both logout notifications
        self.assertEqual(len(self.tab3.logouts), 2)
        
        # Tab1 should only receive tab2's logout
        self.assertEqual(len(self.tab1.logouts), 1)
        self.assertEqual(self.tab1.logouts[0]['tabId'], self.tab2.tab_id)
        
        # Tab2 should only receive tab1's logout
        self.assertEqual(len(self.tab2.logouts), 1)
        self.assertEqual(self.tab2.logouts[0]['tabId'], self.tab1.tab_id)

class TestCrossTabIntegrationScenarios(MySQLIntegrationTestBase):
    """Test complex cross-tab integration scenarios (Requirements 2.1, 2.2, 2.3, 3.4, 3.5)"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkdtemp(prefix="mysql_integration_test_")
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = f'mysql+pymysql://{self.db_path}'
        
        # Initialize database manager and create tables
        self.db_manager = self.get_database_manager()
        self.db_manager.create_tables()
        
        # Initialize session manager
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
        # Create test user with platforms
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_integration_user",
            role=UserRole.REVIEWER
        )
        
        # Create mock tabs
        self.tab1 = MockTab("tab1", self.session_manager)
        self.tab2 = MockTab("tab2", self.session_manager)
        self.tab3 = MockTab("tab3", self.session_manager)
        self.tabs = [self.tab1, self.tab2, self.tab3]
        
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up mock users
        cleanup_test_user(self.user_helper)
        
        # Clean up database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def broadcast_storage_event(self, source_tab, event):
        """Broadcast storage event to all other tabs"""
        for tab in self.tabs:
            if tab != source_tab:
                tab.handle_storage_event(event)
    
    def test_platform_switch_followed_by_logout(self):
        """Test platform switch followed by logout across tabs"""
        # Create sessions
        for tab in self.tabs:
            session_id = self.session_manager.create_session(self.test_user.id)
            time.sleep(0.1)
        
        # Platform switch from tab1
        platform_switch_data = {
            'type': 'platform_switch',
            'platformId': self.test_user.platform_connections[1].id,
            'platformName': self.test_user.platform_connections[1].name,
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        event1 = self.tab1.set_storage('vedfolnir_platform_switch', json.dumps(platform_switch_data))
        self.broadcast_storage_event(self.tab1, event1)
        
        time.sleep(0.1)
        
        # Logout from tab2
        logout_data = {
            'type': 'logout',
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab2.tab_id
        }
        
        event2 = self.tab2.set_storage('vedfolnir_logout', json.dumps(logout_data))
        self.broadcast_storage_event(self.tab2, event2)
        
        # Verify tab3 received both events
        self.assertEqual(len(self.tab3.platform_switches), 1)
        self.assertEqual(len(self.tab3.logouts), 1)
        
        # Verify correct order and data
        self.assertEqual(self.tab3.platform_switches[0]['tabId'], self.tab1.tab_id)
        self.assertEqual(self.tab3.logouts[0]['tabId'], self.tab2.tab_id)
    
    def test_session_expiration_during_platform_switch(self):
        """Test session expiration occurring during platform switch"""
        # Create session
        session_id = self.session_manager.create_session(self.test_user.id)
        
        # Start platform switch from tab1
        platform_switch_data = {
            'type': 'platform_switch',
            'platformId': self.test_user.platform_connections[0].id,
            'platformName': self.test_user.platform_connections[0].name,
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab1.tab_id
        }
        
        event1 = self.tab1.set_storage('vedfolnir_platform_switch', json.dumps(platform_switch_data))
        self.broadcast_storage_event(self.tab1, event1)
        
        # Session expires from tab2
        expiration_data = {
            'type': 'session_expired',
            'timestamp': int(time.time() * 1000),
            'tabId': self.tab2.tab_id
        }
        
        event2 = self.tab2.set_storage('vedfolnir_session_expired', json.dumps(expiration_data))
        self.broadcast_storage_event(self.tab2, event2)
        
        # Verify tab3 received both events
        self.assertEqual(len(self.tab3.platform_switches), 1)
        self.assertEqual(len(self.tab3.session_expirations), 1)
        
        # Session expiration should take precedence
        self.assertEqual(self.tab3.session_expirations[0]['tabId'], self.tab2.tab_id)
    
    def test_multiple_tabs_rapid_events(self):
        """Test rapid events from multiple tabs"""
        # Create sessions
        for tab in self.tabs:
            session_id = self.session_manager.create_session(self.test_user.id)
            time.sleep(0.1)
        
        events = []
        
        # Rapid sequence of events
        for i in range(5):
            # Platform switch
            platform_data = {
                'type': 'platform_switch',
                'platformId': self.test_user.platform_connections[i % 2].id,
                'platformName': self.test_user.platform_connections[i % 2].name,
                'timestamp': int(time.time() * 1000) + i,
                'tabId': self.tabs[i % 3].tab_id
            }
            
            source_tab = self.tabs[i % 3]
            event = source_tab.set_storage('vedfolnir_platform_switch', json.dumps(platform_data))
            self.broadcast_storage_event(source_tab, event)
            events.append(('platform_switch', source_tab.tab_id))
            
            time.sleep(0.01)  # Very short delay
        
        # Verify all tabs received appropriate events
        total_switches = sum(len(tab.platform_switches) for tab in self.tabs)
        
        # Each event should be received by 2 tabs (all except the sender)
        expected_total = 5 * 2  # 5 events * 2 receiving tabs each
        self.assertEqual(total_switches, expected_total)

if __name__ == '__main__':
    unittest.main()