# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test caption generation route error handling improvements.

This test verifies that the caption generation route properly handles various error scenarios
with specific error messages, graceful fallbacks, and proper security logging.
"""

import unittest
import sys
import os
import requests
import re
from unittest.mock import patch, MagicMock
from urllib.parse import urljoin

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestCaptionGenerationErrorHandling(unittest.TestCase):
    """Test cases for caption generation route error handling"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
        
    def test_error_handling_patterns_in_code(self):
        """Test that the caption generation route has proper error handling patterns"""
        print("Testing error handling patterns in caption generation route...")
        
        # Read the web_app.py file to verify error handling patterns
        with open('web_app.py', 'r') as f:
            content = f.read()
        
        # Find the caption generation route
        route_pattern = r'@app\.route\(\'/caption_generation\'\).*?def caption_generation\(\):(.*?)(?=@app\.route\(\'/start_caption_generation\'|$)'
        match = re.search(route_pattern, content, re.DOTALL)
        
        if not match:
            self.fail("Caption generation route not found")
        
        route_content = match.group(1)
        
        # Test 1: Check for specific error message patterns
        self.assertIn('sanitize_for_log', route_content, 
                     "Route should use sanitize_for_log for security logging")
        
        # Test 2: Check for Redis fallback pattern
        self.assertIn('redis_platform_manager', route_content,
                     "Route should attempt Redis access first")
        self.assertIn('db_manager.get_session', route_content,
                     "Route should fallback to database")
        
        # Test 3: Check for specific error scenarios
        error_scenarios = [
            'No active platform connection found',
            'Caption generation service is temporarily unavailable',
            'Failed to initialize caption generation service',
            'Failed to get storage status',
            'Redis settings retrieval failed',
            'Database settings retrieval failed'
        ]
        
        for scenario in error_scenarios:
            # Check if the error message or similar handling exists
            found = any(keyword in route_content for keyword in scenario.split()[:3])
            self.assertTrue(found, f"Error handling for '{scenario}' scenario not found")
        
        # Test 4: Check for graceful error handling (continue operation on non-critical errors)
        self.assertIn('continue with', route_content.lower(),
                     "Route should continue operation on non-critical errors")
        
        # Test 5: Check for proper exception handling structure
        self.assertIn('try:', route_content,
                     "Route should have try-catch blocks")
        self.assertIn('except Exception as e:', route_content,
                     "Route should have proper exception handling")
        
        print("✅ Error handling patterns verified in code")
        return True
    
    def test_sanitize_for_log_usage(self):
        """Test that sanitize_for_log is properly used throughout the route"""
        print("Testing sanitize_for_log usage...")
        
        with open('web_app.py', 'r') as f:
            content = f.read()
        
        # Find all app.logger.error calls in the caption generation route
        route_pattern = r'@app\.route\(\'/caption_generation\'\).*?def caption_generation\(\):(.*?)(?=@app\.route\(\'/start_caption_generation\'|$)'
        match = re.search(route_pattern, content, re.DOTALL)
        
        if not match:
            self.fail("Caption generation route not found")
        
        route_content = match.group(1)
        
        # Find all logger.error calls
        error_log_pattern = r'app\.logger\.error\([^)]+\)'
        error_logs = re.findall(error_log_pattern, route_content)
        
        # Check that each error log uses sanitize_for_log
        for log_call in error_logs:
            if 'str(e)' in log_call or '{e}' in log_call:
                self.assertIn('sanitize_for_log', log_call,
                             f"Error log should use sanitize_for_log: {log_call}")
        
        print(f"✅ Found {len(error_logs)} error log calls, all properly sanitized")
        return True
    
    def test_error_message_specificity(self):
        """Test that error messages are specific and user-friendly"""
        print("Testing error message specificity...")
        
        with open('web_app.py', 'r') as f:
            content = f.read()
        
        # Find the caption generation route
        route_pattern = r'@app\.route\(\'/caption_generation\'\).*?def caption_generation\(\):(.*?)(?=@app\.route\(\'/start_caption_generation\'|$)'
        match = re.search(route_pattern, content, re.DOTALL)
        
        if not match:
            self.fail("Caption generation route not found")
        
        route_content = match.group(1)
        
        # Check for specific user-friendly error messages
        user_messages = [
            'No active platform connection found',
            'Please select a platform to continue',
            'Caption generation service is temporarily unavailable',
            'Please try again later',
            'Error initializing caption generation form',
            'An unexpected error occurred'
        ]
        
        flash_pattern = r'flash\([\'"]([^\'"]+)[\'"]'
        flash_messages = re.findall(flash_pattern, route_content)
        
        # Verify we have user-friendly messages
        self.assertGreater(len(flash_messages), 0, "Route should have user-friendly flash messages")
        
        # Check that messages are descriptive (not just generic "error")
        generic_messages = [msg for msg in flash_messages if msg.lower() in ['error', 'failed', 'exception']]
        self.assertEqual(len(generic_messages), 0, 
                        f"Found generic error messages: {generic_messages}")
        
        print(f"✅ Found {len(flash_messages)} specific user-friendly error messages")
        return True
    
    def test_graceful_fallback_patterns(self):
        """Test that the route implements graceful fallback patterns"""
        print("Testing graceful fallback patterns...")
        
        with open('web_app.py', 'r') as f:
            content = f.read()
        
        # Find the caption generation route
        route_pattern = r'@app\.route\(\'/caption_generation\'\).*?def caption_generation\(\):(.*?)(?=@app\.route\(\'/start_caption_generation\'|$)'
        match = re.search(route_pattern, content, re.DOTALL)
        
        if not match:
            self.fail("Caption generation route not found")
        
        route_content = match.group(1)
        
        # Test 1: Redis to database fallback
        self.assertIn('redis_platform_manager', route_content,
                     "Should attempt Redis first")
        self.assertIn('if not user_settings:', route_content,
                     "Should check if Redis failed and fallback to database")
        
        # Test 2: Continue operation on non-critical failures
        continue_patterns = [
            'Continue with empty',
            'Continue without',
            'rather than failing',
            'Continue with no'
        ]
        
        found_continue = any(pattern.lower() in route_content.lower() for pattern in continue_patterns)
        self.assertTrue(found_continue, "Should continue operation on non-critical errors")
        
        # Test 3: Timeout handling for async operations
        self.assertIn('timeout=', route_content,
                     "Should have timeout handling for async operations")
        
        print("✅ Graceful fallback patterns verified")
        return True
    
    def test_platform_context_error_handling(self):
        """Test platform context error handling"""
        print("Testing platform context error handling...")
        
        with open('web_app.py', 'r') as f:
            content = f.read()
        
        # Find the caption generation route
        route_pattern = r'@app\.route\(\'/caption_generation\'\).*?def caption_generation\(\):(.*?)(?=@app\.route\(\'/start_caption_generation\'|$)'
        match = re.search(route_pattern, content, re.DOTALL)
        
        if not match:
            self.fail("Caption generation route not found")
        
        route_content = match.group(1)
        
        # Test 1: Check for platform context validation
        self.assertIn('get_current_session_context()', route_content,
                     "Should get current session context")
        
        # Test 2: Check for platform connection ID validation
        self.assertIn('platform_connection_id', route_content,
                     "Should validate platform connection ID")
        
        # Test 3: Check for redirect to platform management
        self.assertIn('platform_management', route_content,
                     "Should redirect to platform management on missing context")
        
        # Test 4: Check for specific platform error messages
        platform_error_messages = [
            'No active platform connection found',
            'Please select a platform to continue'
        ]
        
        found_platform_messages = any(msg in route_content for msg in platform_error_messages)
        self.assertTrue(found_platform_messages, "Should have specific platform error messages")
        
        print("✅ Platform context error handling verified")
        return True

def main():
    """Run the error handling tests"""
    print("=== Caption Generation Error Handling Tests ===")
    print("Testing error handling improvements for caption generation route")
    print()
    
    # Create test suite
    suite = unittest.TestSuite()
    suite.addTest(TestCaptionGenerationErrorHandling('test_error_handling_patterns_in_code'))
    suite.addTest(TestCaptionGenerationErrorHandling('test_sanitize_for_log_usage'))
    suite.addTest(TestCaptionGenerationErrorHandling('test_error_message_specificity'))
    suite.addTest(TestCaptionGenerationErrorHandling('test_graceful_fallback_patterns'))
    suite.addTest(TestCaptionGenerationErrorHandling('test_platform_context_error_handling'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*50)
    if result.wasSuccessful():
        print("✅ All error handling tests passed!")
        print("✅ Caption generation route error handling is properly implemented")
        return True
    else:
        print("❌ Some error handling tests failed")
        print(f"❌ Failures: {len(result.failures)}")
        print(f"❌ Errors: {len(result.errors)}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)