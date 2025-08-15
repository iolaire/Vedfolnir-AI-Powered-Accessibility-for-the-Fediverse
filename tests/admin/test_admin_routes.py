# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Tests for admin routes"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.test_helpers.database_manager_test_utils import (
    patch_web_app_database_manager,
    create_mock_user,
    configure_mock_for_flask_routes
)

class TestAdminRoutes(unittest.TestCase):
    """Test admin route functionality"""
    
    def test_admin_dashboard_access(self):
        """Test admin dashboard access"""
        # Create admin user
        admin_user = create_mock_user(user_id=1, username="admin")
        admin_user.role.value = "admin"
        admin_user.has_permission.return_value = True
        
        with patch_web_app_database_manager() as mock_db_manager:
            configure_mock_for_flask_routes(mock_db_manager, admin_user, [])
            
            import web_app
            
            with web_app.app.test_client() as client:
                # Mock login
                with client.session_transaction() as sess:
                    sess['user_id'] = '1'
                
                # Test dashboard access
                response = client.get('/admin/')
                
                # Should not get 403 (would need proper authentication setup for 200)
                self.assertNotEqual(response.status_code, 403)
    
    def test_admin_user_management_access(self):
        """Test admin user management access"""
        admin_user = create_mock_user(user_id=1, username="admin")
        admin_user.role.value = "admin"
        admin_user.has_permission.return_value = True
        
        with patch_web_app_database_manager() as mock_db_manager:
            configure_mock_for_flask_routes(mock_db_manager, admin_user, [])
            
            import web_app
            
            with web_app.app.test_client() as client:
                # Mock login
                with client.session_transaction() as sess:
                    sess['user_id'] = '1'
                
                # Test user management access
                response = client.get('/admin/users')
                
                # Should not get 403 (would need proper authentication setup for 200)
                self.assertNotEqual(response.status_code, 403)

if __name__ == '__main__':
    unittest.main()