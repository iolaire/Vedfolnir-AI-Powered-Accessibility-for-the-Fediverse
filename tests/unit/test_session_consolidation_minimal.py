# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Minimal session consolidation test to validate core functionality
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestSessionConsolidationMinimal(unittest.TestCase):
    """Minimal test to validate session consolidation components exist and work"""
    
    def test_unified_session_manager_import(self):
        """Test that UnifiedSessionManager can be imported"""
        try:
            from unified_session_manager import UnifiedSessionManager
            self.assertTrue(True, "UnifiedSessionManager imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import UnifiedSessionManager: {e}")
    
    def test_session_cookie_manager_import(self):
        """Test that SessionCookieManager can be imported"""
        try:
            from session_cookie_manager import SessionCookieManager
            self.assertTrue(True, "SessionCookieManager imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import SessionCookieManager: {e}")
    
    def test_database_session_middleware_import(self):
        """Test that Redis session middleware can be imported"""
        try:
            from redis_session_middleware import get_current_session_context, get_current_user_id, get_current_platform_id, validate_current_session as is_session_authenticated
            self.assertTrue(True, "Redis session middleware imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import Redis session middleware: {e}")
    
    def test_unified_session_manager_basic_functionality(self):
        """Test basic UnifiedSessionManager functionality with mocks"""
        try:
            from unified_session_manager import UnifiedSessionManager
            
            # Mock database manager
            mock_db_manager = MagicMock()
            
            # Mock config with proper structure
            mock_config = MagicMock()
            mock_config.timeout.session_lifetime = 86400  # seconds, not timedelta
            
            # Create session manager with mocked config
            session_manager = UnifiedSessionManager(mock_db_manager, config=mock_config)
            
            # Verify it was created
            self.assertIsNotNone(session_manager)
            self.assertEqual(session_manager.session_timeout, timedelta(seconds=86400))
            
        except Exception as e:
            self.fail(f"UnifiedSessionManager basic functionality failed: {e}")
    
    def test_session_cookie_manager_basic_functionality(self):
        """Test basic SessionCookieManager functionality"""
        try:
            from session_cookie_manager import SessionCookieManager
            
            # Create cookie manager
            cookie_manager = SessionCookieManager()
            
            # Verify it was created with defaults
            self.assertIsNotNone(cookie_manager)
            self.assertEqual(cookie_manager.cookie_name, 'session_id')
            self.assertTrue(cookie_manager.secure)
            
        except Exception as e:
            self.fail(f"SessionCookieManager basic functionality failed: {e}")
    
    def test_database_session_middleware_functions_exist(self):
        """Test that middleware functions exist and can be called"""
        try:
            from redis_session_middleware import get_current_session_context, get_current_user_id, get_current_platform_id, validate_current_session as is_session_authenticated
            from flask import Flask
            
            # Create Flask app and context
            app = Flask(__name__)
            
            with app.app_context():
                with app.test_request_context():
                    # Mock Flask g object within app context
                    with patch('database_session_middleware.g') as mock_g:
                        mock_g.session_context = {
                            'user_id': 123,
                            'platform_connection_id': 456
                        }
                        
                        # Test functions return expected values
                        context = get_current_session_context()
                        user_id = get_current_user_id()
                        platform_id = get_current_platform_id()
                        authenticated = is_session_authenticated()
                        
                        self.assertEqual(context, mock_g.session_context)
                        self.assertEqual(user_id, 123)
                        self.assertEqual(platform_id, 456)
                        self.assertTrue(authenticated)
                
        except Exception as e:
            self.fail(f"Redis session middleware functions failed: {e}")
    
    def test_session_consolidation_components_integration(self):
        """Test that all components can work together"""
        try:
            from unified_session_manager import UnifiedSessionManager
            from session_cookie_manager import SessionCookieManager
            from redis_session_middleware import get_current_session_context, get_current_session_id
            from flask import Flask
            
            # Create Flask app
            app = Flask(__name__)
            
            # Mock database manager
            mock_db_manager = MagicMock()
            
            # Mock config
            mock_config = MagicMock()
            mock_config.timeout.session_lifetime = 86400
            
            # Create components
            session_manager = UnifiedSessionManager(mock_db_manager, config=mock_config)
            cookie_manager = SessionCookieManager()
            middleware = DatabaseSessionMiddleware(app, session_manager, cookie_manager)
            
            # Verify all components were created
            self.assertIsNotNone(session_manager)
            self.assertIsNotNone(cookie_manager)
            self.assertIsNotNone(middleware)
            
            # Verify middleware was registered with app
            self.assertTrue(len(app.before_request_funcs[None]) > 0)
            self.assertTrue(len(app.after_request_funcs[None]) > 0)
            
        except Exception as e:
            self.fail(f"Session consolidation integration failed: {e}")

if __name__ == '__main__':
    unittest.main()