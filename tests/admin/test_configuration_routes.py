# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Configuration Management Routes

Tests the REST API endpoints for system configuration management
including validation, export/import, and history functionality.
"""

import unittest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from flask import Flask
from werkzeug.test import Client

from app.blueprints.admin.configuration_routes import configuration_bp
from app.core.configuration.core.system_configuration_manager import (
    SystemConfigurationManager, ConfigurationCategory, 
    ConfigurationExport, ConfigurationValidationResult,
    ConfigurationChange, ConfigurationSchema, ConfigurationDataType
)


class TestConfigurationRoutes(unittest.TestCase):
    """Test cases for configuration management routes"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Register blueprint
        self.app.register_blueprint(configuration_bp)
        
        # Create test client
        self.client = self.app.test_client()
        
        # Mock configuration manager
        self.mock_config_manager = Mock(spec=SystemConfigurationManager)
        self.app.config['system_configuration_manager'] = self.mock_config_manager
        
        # Mock session data
        self.admin_user_id = 1
        
        # Set up application context
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment"""
        self.app_context.pop()
    
    def _mock_session(self, user_id=None, is_admin=True):
        """Mock Flask session with user data"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id or self.admin_user_id
            sess['role'] = 'admin' if is_admin else 'reviewer'
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    def test_get_configuration_schema_all(self, mock_require_admin):
        """Test getting all configuration schemas"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        
        # Mock schema data
        mock_schema = {
            "test_key": Mock(
                key="test_key",
                data_type=ConfigurationDataType.STRING,
                category=ConfigurationCategory.SYSTEM,
                description="Test configuration",
                default_value="default",
                is_sensitive=False,
                validation_rules={},
                environment_override=True,
                requires_restart=False
            )
        }
        self.mock_config_manager.get_configuration_schema.return_value = mock_schema
        
        # Make request
        response = self.client.get('/admin/api/configuration/schema')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('schemas', data)
        self.assertIn('test_key', data['schemas'])
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    def test_get_configuration_schema_specific(self, mock_require_admin):
        """Test getting specific configuration schema"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        
        # Mock schema data
        mock_schema = Mock(
            key="test_key",
            data_type=ConfigurationDataType.STRING,
            category=ConfigurationCategory.SYSTEM,
            description="Test configuration",
            default_value="default",
            is_sensitive=False,
            validation_rules={},
            environment_override=True,
            requires_restart=False
        )
        self.mock_config_manager.get_configuration_schema.return_value = mock_schema
        
        # Make request
        response = self.client.get('/admin/api/configuration/schema?key=test_key')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('schema', data)
        self.assertEqual(data['schema']['key'], 'test_key')
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    def test_get_configuration_documentation(self, mock_require_admin):
        """Test getting configuration documentation"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        
        # Mock documentation data
        mock_docs = {
            "system": {
                "name": "System",
                "description": "System configurations",
                "configurations": []
            }
        }
        self.mock_config_manager.get_configuration_documentation.return_value = mock_docs
        
        # Make request
        response = self.client.get('/admin/api/configuration/documentation')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('documentation', data)
        self.assertIn('system', data['documentation'])
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_get_configurations(self, mock_session, mock_require_admin):
        """Test getting all configurations"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock configurations data
        mock_configs = {
            "config1": "value1",
            "config2": "value2"
        }
        self.mock_config_manager.get_all_configurations.return_value = mock_configs
        
        # Make request
        response = self.client.get('/admin/api/configuration/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('configurations', data)
        self.assertEqual(len(data['configurations']), 2)
        self.assertEqual(data['total_count'], 2)
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_get_configurations_with_category_filter(self, mock_session, mock_require_admin):
        """Test getting configurations with category filter"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock configurations data
        mock_configs = {"system_config": "value"}
        self.mock_config_manager.get_all_configurations.return_value = mock_configs
        
        # Make request with category filter
        response = self.client.get('/admin/api/configuration/?category=system')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['category'], 'system')
        
        # Verify manager was called with correct category
        self.mock_config_manager.get_all_configurations.assert_called_with(
            self.admin_user_id, ConfigurationCategory.SYSTEM, False
        )
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_get_configuration_specific(self, mock_session, mock_require_admin):
        """Test getting specific configuration"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock configuration value
        self.mock_config_manager.get_configuration.return_value = "test_value"
        
        # Make request
        response = self.client.get('/admin/api/configuration/test_key')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['key'], 'test_key')
        self.assertEqual(data['value'], 'test_value')
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_get_configuration_not_found(self, mock_session, mock_require_admin):
        """Test getting non-existent configuration"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock configuration not found
        self.mock_config_manager.get_configuration.return_value = None
        
        # Make request
        response = self.client.get('/admin/api/configuration/nonexistent')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_set_configuration_success(self, mock_session, mock_require_admin):
        """Test setting configuration successfully"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock successful configuration update
        self.mock_config_manager.set_configuration.return_value = True
        
        # Make request
        response = self.client.put('/admin/api/configuration/test_key',
                                 json={'value': 'new_value', 'reason': 'test update'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertEqual(data['key'], 'test_key')
        self.assertEqual(data['value'], 'new_value')
        
        # Verify manager was called correctly
        self.mock_config_manager.set_configuration.assert_called_with(
            'test_key', 'new_value', self.admin_user_id, 'test update'
        )
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_set_configuration_failure(self, mock_session, mock_require_admin):
        """Test setting configuration failure"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock failed configuration update
        self.mock_config_manager.set_configuration.return_value = False
        
        # Make request
        response = self.client.put('/admin/api/configuration/test_key',
                                 json={'value': 'new_value'})
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_set_configurations_batch_success(self, mock_session, mock_require_admin):
        """Test batch configuration update success"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock validation success
        validation_result = ConfigurationValidationResult(
            is_valid=True, errors=[], warnings=[], conflicts=[]
        )
        self.mock_config_manager.validate_configuration_set.return_value = validation_result
        
        # Mock successful configuration updates
        self.mock_config_manager.set_configuration.return_value = True
        
        # Make request
        configurations = {'config1': 'value1', 'config2': 'value2'}
        response = self.client.put('/admin/api/configuration/batch',
                                 json={'configurations': configurations, 'reason': 'batch update'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['success_count'], 2)
        self.assertEqual(len(data['failed_configurations']), 0)
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_set_configurations_batch_validation_failure(self, mock_session, mock_require_admin):
        """Test batch configuration update with validation failure"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock validation failure
        validation_result = ConfigurationValidationResult(
            is_valid=False, errors=['Invalid value'], warnings=[], conflicts=[]
        )
        self.mock_config_manager.validate_configuration_set.return_value = validation_result
        
        # Make request
        configurations = {'config1': 'invalid_value'}
        response = self.client.put('/admin/api/configuration/batch',
                                 json={'configurations': configurations})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('validation_errors', data)
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    def test_validate_configurations(self, mock_require_admin):
        """Test configuration validation endpoint"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        
        # Mock validation result
        validation_result = ConfigurationValidationResult(
            is_valid=True, errors=[], warnings=['Warning message'], conflicts=[]
        )
        self.mock_config_manager.validate_configuration_set.return_value = validation_result
        
        # Make request
        configurations = {'config1': 'value1'}
        response = self.client.post('/admin/api/configuration/validate',
                                  json={'configurations': configurations})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['is_valid'])
        self.assertEqual(len(data['warnings']), 1)
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_get_configuration_history(self, mock_session, mock_require_admin):
        """Test getting configuration history"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock history data
        mock_history = [
            ConfigurationChange(
                key="test_key",
                old_value="old",
                new_value="new",
                changed_by=1,
                changed_at=datetime.now(timezone.utc),
                reason="test change"
            )
        ]
        self.mock_config_manager.get_configuration_history.return_value = mock_history
        
        # Make request
        response = self.client.get('/admin/api/configuration/test_key/history')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['key'], 'test_key')
        self.assertEqual(len(data['history']), 1)
        self.assertEqual(data['history'][0]['old_value'], 'old')
        self.assertEqual(data['history'][0]['new_value'], 'new')
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_rollback_configuration_success(self, mock_session, mock_require_admin):
        """Test configuration rollback success"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock successful rollback
        self.mock_config_manager.rollback_configuration.return_value = True
        
        # Make request
        target_timestamp = datetime.now(timezone.utc).isoformat()
        response = self.client.post('/admin/api/configuration/test_key/rollback',
                                  json={'target_timestamp': target_timestamp, 'reason': 'rollback test'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertEqual(data['key'], 'test_key')
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_rollback_configuration_failure(self, mock_session, mock_require_admin):
        """Test configuration rollback failure"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock failed rollback
        self.mock_config_manager.rollback_configuration.return_value = False
        
        # Make request
        target_timestamp = datetime.now(timezone.utc).isoformat()
        response = self.client.post('/admin/api/configuration/test_key/rollback',
                                  json={'target_timestamp': target_timestamp})
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_export_configurations(self, mock_session, mock_require_admin):
        """Test configuration export"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock export data
        export_data = ConfigurationExport(
            configurations={'config1': 'value1'},
            metadata={'version': '1.0'},
            export_timestamp=datetime.now(timezone.utc),
            exported_by=self.admin_user_id
        )
        self.mock_config_manager.export_configurations.return_value = export_data
        
        # Make request
        response = self.client.get('/admin/api/configuration/export')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('configurations', data)
        self.assertIn('metadata', data)
        self.assertEqual(data['exported_by'], self.admin_user_id)
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_import_configurations_success(self, mock_session, mock_require_admin):
        """Test configuration import success"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock successful import
        self.mock_config_manager.import_configurations.return_value = (True, ['Import successful'])
        
        # Make request
        import_data = {
            'configurations': {'config1': 'value1'},
            'metadata': {'version': '1.0'},
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'exported_by': 1
        }
        response = self.client.post('/admin/api/configuration/import', json=import_data)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('Import successful', data['messages'])
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_import_configurations_failure(self, mock_session, mock_require_admin):
        """Test configuration import failure"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Mock failed import
        self.mock_config_manager.import_configurations.return_value = (False, ['Import failed'])
        
        # Make request
        import_data = {
            'configurations': {'config1': 'invalid_value'},
            'metadata': {'version': '1.0'},
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'exported_by': 1
        }
        response = self.client.post('/admin/api/configuration/import', json=import_data)
        
        self.assertEqual(response.status_code, 200)  # Still 200, but success=False
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Import failed', data['messages'])
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    def test_get_configuration_categories(self, mock_require_admin):
        """Test getting configuration categories"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        
        # Make request
        response = self.client.get('/admin/api/configuration/categories')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('categories', data)
        
        # Check that all categories are present
        category_values = [cat['value'] for cat in data['categories']]
        for category in ConfigurationCategory:
            self.assertIn(category.value, category_values)
    
    def test_missing_configuration_manager(self):
        """Test endpoints when configuration manager is not available"""
        # Remove configuration manager from app config
        self.app.config.pop('system_configuration_manager', None)
        
        with patch('app.blueprints.admin.configuration_routes.require_admin') as mock_require_admin:
            mock_require_admin.return_value = lambda f: f  # Bypass decorator
            
            # Make request
            response = self.client.get('/admin/api/configuration/schema')
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertIn('error', data)
            self.assertIn('Configuration manager not available', data['error'])
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    def test_missing_session_user_id(self, mock_require_admin):
        """Test endpoints when user ID is not in session"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        
        with patch('app.blueprints.admin.configuration_routes.session') as mock_session:
            mock_session.get.return_value = None  # No user ID in session
            
            # Make request
            response = self.client.get('/admin/api/configuration/')
            
            self.assertEqual(response.status_code, 401)
            data = json.loads(response.data)
            self.assertIn('error', data)
            self.assertIn('Admin user ID not found in session', data['error'])
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_invalid_category_filter(self, mock_session, mock_require_admin):
        """Test invalid category filter"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Make request with invalid category
        response = self.client.get('/admin/api/configuration/?category=invalid_category')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Invalid category', data['error'])
    
    @patch('app.blueprints.admin.configuration_routes.require_admin')
    @patch('app.blueprints.admin.configuration_routes.session')
    def test_missing_request_data(self, mock_session, mock_require_admin):
        """Test endpoints with missing request data"""
        mock_require_admin.return_value = lambda f: f  # Bypass decorator
        mock_session.get.return_value = self.admin_user_id
        
        # Test set configuration without value
        response = self.client.put('/admin/api/configuration/test_key', json={})
        self.assertEqual(response.status_code, 400)
        
        # Test batch update without configurations
        response = self.client.put('/admin/api/configuration/batch', json={})
        self.assertEqual(response.status_code, 400)
        
        # Test validate without configurations
        response = self.client.post('/admin/api/configuration/validate', json={})
        self.assertEqual(response.status_code, 400)
        
        # Test rollback without target_timestamp
        response = self.client.post('/admin/api/configuration/test_key/rollback', json={})
        self.assertEqual(response.status_code, 400)
        
        # Test import without required fields
        response = self.client.post('/admin/api/configuration/import', json={})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()