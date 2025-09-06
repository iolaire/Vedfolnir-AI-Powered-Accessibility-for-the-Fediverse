# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config


class TestSystemOptimizerIntegration(unittest.TestCase):
    """Integration test for SystemOptimizer with ResponsivenessConfig"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
    
    def test_responsiveness_config_integration(self):
        """Test that ResponsivenessConfig is properly integrated into main Config"""
        # Test that responsiveness config is loaded
        self.assertIsNotNone(self.config.responsiveness)
        
        # Test default values
        self.assertEqual(self.config.responsiveness.memory_warning_threshold, 0.8)
        self.assertEqual(self.config.responsiveness.memory_critical_threshold, 0.9)
        self.assertEqual(self.config.responsiveness.cpu_warning_threshold, 0.8)
        self.assertEqual(self.config.responsiveness.cpu_critical_threshold, 0.9)
        self.assertTrue(self.config.responsiveness.cleanup_enabled)
    
    def test_environment_variable_override(self):
        """Test that environment variables properly override default values"""
        with patch.dict(os.environ, {
            'RESPONSIVENESS_MEMORY_WARNING_THRESHOLD': '0.75',
            'RESPONSIVENESS_CLEANUP_ENABLED': 'false'
        }):
            # Create new config to pick up environment changes
            test_config = Config()
            
            self.assertEqual(test_config.responsiveness.memory_warning_threshold, 0.75)
            self.assertFalse(test_config.responsiveness.cleanup_enabled)
    
    def test_config_validation_includes_responsiveness(self):
        """Test that configuration validation works with responsiveness config"""
        validation_errors = self.config.validate_configuration()
        
        # Should not have errors related to responsiveness config
        responsiveness_errors = [error for error in validation_errors if 'responsiveness' in error.lower()]
        self.assertEqual(len(responsiveness_errors), 0)
    
    def test_config_reload_includes_responsiveness(self):
        """Test that configuration reload includes responsiveness config"""
        # Set environment variable
        with patch.dict(os.environ, {
            'RESPONSIVENESS_MONITORING_INTERVAL': '60'
        }):
            # Reload configuration
            self.config.reload_configuration()
            
            # Check that new value is loaded
            self.assertEqual(self.config.responsiveness.monitoring_interval, 60)
    
    def test_config_status_includes_responsiveness(self):
        """Test that configuration status includes responsiveness information"""
        status = self.config.get_configuration_status()
        
        # Should be valid configuration
        self.assertTrue(status['valid'])
        
        # Should not have responsiveness-related errors
        responsiveness_errors = [error for error in status['errors'] if 'responsiveness' in error.lower()]
        self.assertEqual(len(responsiveness_errors), 0)


if __name__ == '__main__':
    unittest.main()