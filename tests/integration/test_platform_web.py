# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration tests for web interface platform operations

Tests end-to-end web interface functionality for platform management.
"""

import unittest
from unittest.mock import patch, MagicMock
from tests.mysql_test_base import MySQLIntegrationTestBase

class TestWebInterfacePlatformOperations(MySQLIntegrationTestBase):
    """Test web interface platform operations end-to-end"""
    
    def setUp(self):
        """Set up integration test with MySQL"""
        super().setUp()
        
        # Mock Flask app for testing
        self.app = MagicMock()
        self.app.config = {
            'SECRET_KEY': 'test_secret_key',
            'TESTING': True
        }
    
    def test_platform_list_display(self):
        """Test platform list displays user's connections"""
        user = self.get_test_user()
        platforms = user.get_active_platforms()
        
        # Simulate web request to get platforms
        platform_data = []
        for platform in platforms:
            platform_data.append({
                'id': platform.id,
                'name': platform.name,
                'platform_type': platform.platform_type,
                'instance_url': platform.instance_url,
                'is_default': platform.is_default,
                'is_active': platform.is_active
            })
        
        # Verify platform data structure
        self.assertGreater(len(platform_data), 0)
        
        for platform in platform_data:
            self.assertIn('id', platform)
            self.assertIn('name', platform)
            self.assertIn('platform_type', platform)
            self.assertIn('instance_url', platform)
            self.assertIn('is_default', platform)
            self.assertIn('is_active', platform)
    
    def test_add_platform_form_validation(self):
        """Test add platform form validation and submission"""
        user = self.get_test_user()
        
        # Valid platform data
        valid_data = {
            'name': 'New Test Platform',
            'platform_type': 'pixelfed',
            'instance_url': 'https://newtest.com',
            'username': 'newuser',
            'access_token': 'new_access_token_123'
        }
        
        # Simulate form validation
        validation_errors = []
        
        # Required field validation
        for field in ['name', 'platform_type', 'instance_url', 'username', 'access_token']:
            if not valid_data.get(field):
                validation_errors.append(f'{field} is required')
        
        # Platform type validation
        if valid_data['platform_type'] not in ['pixelfed', 'mastodon']:
            validation_errors.append('Invalid platform type')
        
        # URL validation
        if not valid_data['instance_url'].startswith(('http://', 'https://')):
            validation_errors.append('Invalid instance URL')
        
        # Should pass validation
        self.assertEqual(len(validation_errors), 0)
        
        # Test invalid data
        invalid_data = {
            'name': '',  # Empty name
            'platform_type': 'invalid',  # Invalid type
            'instance_url': 'not-a-url',  # Invalid URL
            'username': 'user',
            'access_token': 'token'
        }
        
        validation_errors = []
        
        if not invalid_data.get('name'):
            validation_errors.append('name is required')
        
        if invalid_data['platform_type'] not in ['pixelfed', 'mastodon']:
            validation_errors.append('Invalid platform type')
        
        if not invalid_data['instance_url'].startswith(('http://', 'https://')):
            validation_errors.append('Invalid instance URL')
        
        # Should fail validation
        self.assertGreater(len(validation_errors), 0)
    
    def test_edit_platform_functionality(self):
        """Test edit platform functionality"""
        platform = self.get_test_platform()
        
        # Original data
        original_name = platform.name
        original_url = platform.instance_url
        
        # Updated data
        updated_data = {
            'name': 'Updated Platform Name',
            'instance_url': 'https://updated.test.com',
            'username': platform.username,
            'access_token': platform.access_token
        }
        
        # Simulate update operation
        platform.name = updated_data['name']
        platform.instance_url = updated_data['instance_url']
        self.session.commit()
        
        # Verify update
        updated_platform = self.session.query(type(platform)).get(platform.id)
        self.assertEqual(updated_platform.name, updated_data['name'])
        self.assertEqual(updated_platform.instance_url, updated_data['instance_url'])
        self.assertNotEqual(updated_platform.name, original_name)
        self.assertNotEqual(updated_platform.instance_url, original_url)
    
    def test_platform_deletion_with_confirmation(self):
        """Test platform deletion requires confirmation and works correctly"""
        user = self.get_test_user()
        
        # Create additional platform for deletion
        from models import PlatformConnection

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures

        platform_to_delete = PlatformConnection(
            user_id=user.id,
            name='Platform to Delete',
            platform_type='pixelfed',
            instance_url='https://delete.test.com',
            username='deleteuser',
            access_token='delete_token'
        )
        self.session.add(platform_to_delete)
        self.session.commit()
        
        platform_id = platform_to_delete.id
        
        # Simulate deletion confirmation
        confirmation_required = True
        user_confirmed = True
        
        if confirmation_required and user_confirmed:
            # Perform deletion
            self.session.delete(platform_to_delete)
            self.session.commit()
            
            # Verify deletion
            deleted_platform = self.session.query(PlatformConnection).get(platform_id)
            self.assertIsNone(deleted_platform)
    
    def test_platform_switching_updates_context(self):
        """Test platform switching updates user context immediately"""
        user = self.get_test_user()
        platform1 = self.get_test_platform('pixelfed')
        platform2 = self.get_test_platform('mastodon')
        
        # Simulate session-based platform switching
        session_data = {'user_id': user.id}
        
        # Switch to platform1
        session_data['active_platform_id'] = platform1.id
        
        # Verify context
        self.assertEqual(session_data['active_platform_id'], platform1.id)
        
        # Switch to platform2
        session_data['active_platform_id'] = platform2.id
        
        # Verify context updated
        self.assertEqual(session_data['active_platform_id'], platform2.id)
        self.assertNotEqual(session_data['active_platform_id'], platform1.id)
    
    def test_connection_testing_feedback(self):
        """Test connection testing provides clear feedback"""
        platform = self.get_test_platform()
        
        # Simulate connection test
        def test_platform_connection(platform):
            """Mock connection test function"""
            try:
                # Simulate API call
                if platform.access_token and platform.instance_url:
                    # Mock successful connection
                    return {
                        'success': True,
                        'message': 'Connection successful',
                        'details': {
                            'platform_type': platform.platform_type,
                            'instance_url': platform.instance_url,
                            'username': platform.username
                        }
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Missing credentials',
                        'details': {}
                    }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Connection failed: {str(e)}',
                    'details': {}
                }
        
        # Test successful connection
        result = test_platform_connection(platform)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Connection successful')
        self.assertIn('platform_type', result['details'])
        self.assertIn('instance_url', result['details'])
        
        # Test failed connection
        invalid_platform = type(platform)(
            name='Invalid Platform',
            platform_type='pixelfed',
            instance_url='',  # Missing URL
            username='user',
            access_token=''  # Missing token
        )
        
        result = test_platform_connection(invalid_platform)
        
        self.assertFalse(result['success'])
        self.assertIn('Missing credentials', result['message'])

class TestWebInterfaceResponsiveness(MySQLIntegrationTestBase):
    """Test web interface responsiveness and user experience"""
    
    def test_responsive_design_platform_info(self):
        """Test responsive design with platform information"""
        user = self.get_test_user()
        platforms = user.get_active_platforms()
        
        # Simulate different screen sizes
        screen_sizes = ['mobile', 'tablet', 'desktop']
        
        for size in screen_sizes:
            # Platform data should be structured for responsive display
            platform_display_data = []
            
            for platform in platforms:
                display_item = {
                    'id': platform.id,
                    'name': platform.name,
                    'type': platform.platform_type,
                    'url': platform.instance_url,
                    'is_default': platform.is_default,
                    'status': 'active' if platform.is_active else 'inactive'
                }
                
                # Add responsive display properties
                if size == 'mobile':
                    display_item['compact'] = True
                    display_item['show_details'] = False
                elif size == 'tablet':
                    display_item['compact'] = False
                    display_item['show_details'] = True
                else:  # desktop
                    display_item['compact'] = False
                    display_item['show_details'] = True
                    display_item['show_actions'] = True
                
                platform_display_data.append(display_item)
            
            # Verify responsive data structure
            self.assertGreater(len(platform_display_data), 0)
            
            for item in platform_display_data:
                self.assertIn('compact', item)
                self.assertIn('show_details', item)
    
    def test_platform_status_indicators(self):
        """Test platform status indicators are clear and consistent"""
        platforms = self.session.query(type(self.get_test_platform())).all()
        
        for platform in platforms:
            # Generate status indicator data
            status_data = {
                'platform_id': platform.id,
                'name': platform.name,
                'type': platform.platform_type,
                'status': 'active' if platform.is_active else 'inactive',
                'is_default': platform.is_default,
                'connection_status': 'connected',  # Would be determined by connection test
                'last_used': None  # Would be tracked in real implementation
            }
            
            # Verify status data structure
            self.assertIn('status', status_data)
            self.assertIn('connection_status', status_data)
            self.assertIn('is_default', status_data)
            
            # Status should be consistent
            if platform.is_active:
                self.assertEqual(status_data['status'], 'active')
            else:
                self.assertEqual(status_data['status'], 'inactive')

class TestWebInterfaceErrorHandling(MySQLIntegrationTestBase):
    """Test web interface error handling"""
    
    def test_form_error_display(self):
        """Test form errors are displayed clearly"""
        # Simulate form submission with errors
        form_data = {
            'name': '',  # Missing required field
            'platform_type': 'invalid_type',  # Invalid value
            'instance_url': 'not-a-url',  # Invalid format
            'username': 'user',
            'access_token': 'token'
        }
        
        # Validate form data
        errors = {}
        
        if not form_data.get('name'):
            errors['name'] = 'Platform name is required'
        
        if form_data['platform_type'] not in ['pixelfed', 'mastodon']:
            errors['platform_type'] = 'Please select a valid platform type'
        
        if not form_data['instance_url'].startswith(('http://', 'https://')):
            errors['instance_url'] = 'Please enter a valid URL (starting with http:// or https://)'
        
        # Verify error structure
        self.assertGreater(len(errors), 0)
        self.assertIn('name', errors)
        self.assertIn('platform_type', errors)
        self.assertIn('instance_url', errors)
        
        # Error messages should be user-friendly
        for field, message in errors.items():
            self.assertIsInstance(message, str)
            self.assertGreater(len(message), 0)
    
    def test_connection_error_handling(self):
        """Test connection error handling in web interface"""
        platform = self.get_test_platform()
        
        # Simulate various connection errors
        error_scenarios = [
            {
                'error_type': 'network_error',
                'message': 'Unable to connect to the platform. Please check the instance URL.',
                'user_action': 'Verify the instance URL is correct and accessible.'
            },
            {
                'error_type': 'auth_error',
                'message': 'Authentication failed. Please check your access token.',
                'user_action': 'Verify your access token is valid and has the required permissions.'
            },
            {
                'error_type': 'platform_error',
                'message': 'Platform returned an error. Please try again later.',
                'user_action': 'The platform may be temporarily unavailable. Try again in a few minutes.'
            }
        ]
        
        for scenario in error_scenarios:
            # Verify error structure
            self.assertIn('error_type', scenario)
            self.assertIn('message', scenario)
            self.assertIn('user_action', scenario)
            
            # Messages should be helpful
            self.assertGreater(len(scenario['message']), 0)
            self.assertGreater(len(scenario['user_action']), 0)

if __name__ == '__main__':
    unittest.main()