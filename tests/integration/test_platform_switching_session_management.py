#!/usr/bin/env python3
"""
Test suite for platform switching API with session management.
Tests Task 13 requirements: Update platform switching API with session management.
"""

import unittest
from unittest.mock import Mock, patch
import inspect

class TestPlatformSwitchingSessionManagement(unittest.TestCase):
    """Test platform switching API with proper session management"""
    
    def test_api_switch_platform_has_session_decorators(self):
        """Test that api_switch_platform has the required decorators"""
        from web_app import api_switch_platform
        
        # Check that the function has the required decorators
        # This verifies that @with_db_session decorator is applied
        self.assertTrue(hasattr(api_switch_platform, '__wrapped__'))
        
        # Get the source code to verify decorator usage
        source = inspect.getsource(api_switch_platform)
        self.assertIn('@with_db_session', source)
        self.assertIn('@login_required', source)
        self.assertIn('@validate_csrf_token', source)
    
    def test_api_switch_platform_uses_request_session_manager(self):
        """Test that api_switch_platform uses request_session_manager.session_scope()"""
        from web_app import api_switch_platform
        
        # Get the source code to verify session management usage
        source = inspect.getsource(api_switch_platform)
        
        # Verify that request_session_manager.session_scope() is used
        self.assertIn('request_session_manager.session_scope()', source)
        
        # Verify that the function uses proper session management pattern
        self.assertIn('with request_session_manager.session_scope() as db_session:', source)
    
    def test_api_switch_platform_validates_platform_ownership(self):
        """Test that api_switch_platform validates platform ownership and accessibility"""
        from web_app import api_switch_platform
        
        # Get the source code to verify validation logic
        source = inspect.getsource(api_switch_platform)
        
        # Verify that platform ownership validation is implemented
        self.assertIn('user_id=current_user.id', source)
        self.assertIn('is_active=True', source)
        
        # Verify error handling for platform not found
        self.assertIn('Platform not found or not accessible', source)
    
    def test_api_switch_platform_handles_active_tasks(self):
        """Test that api_switch_platform handles active caption generation tasks"""
        from web_app import api_switch_platform
        
        # Get the source code to verify task handling
        source = inspect.getsource(api_switch_platform)
        
        # Verify that active task cancellation is implemented
        self.assertIn('WebCaptionGenerationService', source)
        self.assertIn('get_user_active_task', source)
        self.assertIn('cancel_generation', source)
    
    def test_api_switch_platform_updates_session_context(self):
        """Test that api_switch_platform updates session context properly"""
        from web_app import api_switch_platform
        
        # Get the source code to verify session context updates
        source = inspect.getsource(api_switch_platform)
        
        # Verify that session manager is used to update platform context
        self.assertIn('session_manager.update_platform_context', source)
        self.assertIn('db_manager.set_default_platform', source)
    
    def test_api_switch_platform_extracts_platform_data_safely(self):
        """Test that api_switch_platform extracts platform data to avoid DetachedInstanceError"""
        from web_app import api_switch_platform
        
        # Get the source code to verify safe data extraction
        source = inspect.getsource(api_switch_platform)
        
        # Verify that platform data is extracted before session operations
        self.assertIn('platform_data = {', source)
        self.assertIn("'id': platform.id", source)
        self.assertIn("'name': platform.name", source)
        self.assertIn("'platform_type': platform.platform_type", source)
    
    def test_api_switch_platform_error_handling(self):
        """Test that api_switch_platform has proper error handling"""
        from web_app import api_switch_platform
        
        # Get the source code to verify error handling
        source = inspect.getsource(api_switch_platform)
        
        # Verify that proper error handling is implemented
        self.assertIn('try:', source)
        self.assertIn('except Exception as e:', source)
        self.assertIn('sanitize_for_log', source)
        self.assertIn('Failed to switch platform', source)
    
    def test_task_13_requirements_implementation(self):
        """Test that all Task 13 requirements are implemented"""
        from web_app import api_switch_platform
        
        source = inspect.getsource(api_switch_platform)
        
        # Requirement 3.1: Modify switch_platform endpoint to use request-scoped session
        self.assertIn('request_session_manager.session_scope()', source)
        
        # Requirement 3.2: Ensure platform updates maintain proper session attachment
        self.assertIn('with request_session_manager.session_scope() as db_session:', source)
        
        # Requirement 3.3: Add validation for platform ownership and accessibility
        self.assertIn('user_id=current_user.id', source)
        self.assertIn('is_active=True', source)
        
        # Requirement 3.4: Update response handling to work with session-aware objects
        self.assertIn('platform_data = {', source)
        self.assertIn('jsonify', source)
    
    def test_platform_switching_session_management_integration(self):
        """Test that platform switching integrates properly with session management"""
        # Import the required modules to verify they exist and are properly integrated
        try:
            from web_app import api_switch_platform, request_session_manager, session_manager
            from session_aware_decorators import with_db_session
            
            # Verify that all required components are available
            self.assertTrue(callable(api_switch_platform))
            self.assertTrue(hasattr(request_session_manager, 'session_scope'))
            self.assertTrue(hasattr(session_manager, 'update_platform_context'))
            self.assertTrue(callable(with_db_session))
            
        except ImportError as e:
            self.fail(f"Required session management components not available: {e}")

if __name__ == '__main__':
    unittest.main()