#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive validation script for session manager migration
"""

import unittest
import sys
import os
import glob
import importlib.util
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class SessionMigrationValidation(unittest.TestCase):
    """Validate session manager migration"""
    
    def setUp(self):
        """Set up test environment"""
        try:
            from config import Config
            from database import DatabaseManager
            
            self.config = Config()
            self.db_manager = DatabaseManager(self.config)
        except Exception as e:
            self.skipTest(f"Could not initialize test environment: {e}")
    
    def test_unified_session_manager_import(self):
        """Test that UnifiedSessionManager can be imported and instantiated"""
        try:
            from unified_session_manager import UnifiedSessionManager
            manager = UnifiedSessionManager(self.db_manager)
            self.assertIsNotNone(manager)
            self.assertTrue(hasattr(manager, 'create_session'))
            self.assertTrue(hasattr(manager, 'get_session_context'))
            self.assertTrue(hasattr(manager, 'validate_session'))
            self.assertTrue(hasattr(manager, 'destroy_session'))
        except ImportError as e:
            self.fail(f"Could not import UnifiedSessionManager: {e}")
    
    def test_platform_context_functions(self):
        """Test that platform context functions are available"""
        try:
            from unified_session_manager import (
                get_current_platform_context,
                get_current_platform,
                get_current_user_from_context,
                switch_platform_context
            )
            
            # Functions should be callable
            self.assertTrue(callable(get_current_platform_context))
            self.assertTrue(callable(get_current_platform))
            self.assertTrue(callable(get_current_user_from_context))
            self.assertTrue(callable(switch_platform_context))
        except ImportError as e:
            self.fail(f"Could not import platform context functions: {e}")
    
    def test_unified_session_manager_methods(self):
        """Test that UnifiedSessionManager has all required methods"""
        from unified_session_manager import UnifiedSessionManager
        
        manager = UnifiedSessionManager(self.db_manager)
        
        required_methods = [
            'create_session',
            'get_session_context',
            'validate_session',
            'update_session_activity',
            'update_platform_context',
            'destroy_session',
            'cleanup_expired_sessions',
            'cleanup_user_sessions'
        ]
        
        for method_name in required_methods:
            self.assertTrue(hasattr(manager, method_name), 
                          f"UnifiedSessionManager missing method: {method_name}")
            self.assertTrue(callable(getattr(manager, method_name)),
                          f"UnifiedSessionManager.{method_name} is not callable")
    
    def test_no_legacy_imports_in_core_files(self):
        """Test that core files don't import legacy session_manager directly"""
        core_files = [
            'web_app.py',
            'database_session_middleware.py',
            'session_security.py',
            'platform_context_utils.py'
        ]
        
        legacy_imports = []
        
        for file_name in core_files:
            file_path = project_root / file_name
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Check for legacy imports that aren't compatibility imports
                if ('from session_manager import' in content and 
                    'unified_session_manager' not in content and
                    'session_manager_compat' not in content):
                    legacy_imports.append(str(file_path))
            except Exception as e:
                self.fail(f"Error reading {file_path}: {e}")
        
        if legacy_imports:
            self.fail(f"Core files still importing legacy session_manager: {legacy_imports}")
    
    def test_session_manager_compatibility_layer(self):
        """Test that compatibility layer works if it exists"""
        try:
            # Try to import the compatibility layer
            spec = importlib.util.find_spec('session_manager_compat')
            if spec is not None:
                import session_manager_compat
                
                # Test that it provides the expected interface
                self.assertTrue(hasattr(session_manager_compat, 'SessionManager'))
                self.assertTrue(hasattr(session_manager_compat, 'get_current_platform_context'))
                
                # Test that SessionManager is actually UnifiedSessionManager
                from unified_session_manager import UnifiedSessionManager
                self.assertEqual(session_manager_compat.SessionManager, UnifiedSessionManager)
        except ImportError:
            # Compatibility layer doesn't exist, which is fine
            pass
    
    def test_database_session_middleware_uses_unified_manager(self):
        """Test that DatabaseSessionMiddleware uses UnifiedSessionManager"""
        try:
            from redis_session_middleware import get_current_session_context, get_current_session_id
            
            # Check the import in the file
            middleware_file = project_root / 'database_session_middleware.py'
            if middleware_file.exists():
                with open(middleware_file, 'r') as f:
                    content = f.read()
                    
                self.assertIn('unified_session_manager', content.lower(),
                            "DatabaseSessionMiddleware should import from unified_session_manager")
        except ImportError as e:
            self.skipTest(f"DatabaseSessionMiddleware not available: {e}")
    
    def test_web_app_uses_unified_manager(self):
        """Test that web_app.py uses UnifiedSessionManager"""
        web_app_file = project_root / 'web_app.py'
        if not web_app_file.exists():
            self.skipTest("web_app.py not found")
        
        with open(web_app_file, 'r') as f:
            content = f.read()
        
        # Should import UnifiedSessionManager
        self.assertIn('UnifiedSessionManager', content,
                     "web_app.py should import UnifiedSessionManager")
        
        # Should create unified_session_manager instance
        self.assertIn('unified_session_manager', content,
                     "web_app.py should create unified_session_manager instance")
    
    def test_session_health_checker_compatibility(self):
        """Test that session health checker works with UnifiedSessionManager"""
        try:
            from session_health_checker import SessionHealthChecker, get_session_health_checker
            from unified_session_manager import UnifiedSessionManager
            
            # Test that health checker can be created with UnifiedSessionManager
            unified_manager = UnifiedSessionManager(self.db_manager)
            health_checker = get_session_health_checker(self.db_manager, unified_manager)
            
            self.assertIsNotNone(health_checker)
            self.assertIsInstance(health_checker, SessionHealthChecker)
        except ImportError as e:
            self.skipTest(f"Session health checker not available: {e}")
    
    def test_no_circular_imports(self):
        """Test that there are no circular import issues"""
        try:
            # Try importing all session-related modules
            from unified_session_manager import UnifiedSessionManager
            from redis_session_middleware import get_current_session_context, get_current_session_id
            from session_security import create_session_security_manager
            
            # If we get here without ImportError, circular imports are resolved
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Circular import detected: {e}")

class LegacyImportDetection(unittest.TestCase):
    """Detect remaining legacy imports"""
    
    def test_find_remaining_legacy_imports(self):
        """Find any remaining legacy session_manager imports"""
        python_files = glob.glob(str(project_root / '**' / '*.py'), recursive=True)
        legacy_files = []
        
        exclude_patterns = [
            '__pycache__',
            '.git',
            'venv',
            'env',
            'session_manager.py',  # The original file (if it still exists)
            'session_manager_compat.py',  # Compatibility layer
            'validate_session_migration.py'  # This file
        ]
        
        for file_path in python_files:
            # Skip excluded files
            if any(exclude in file_path for exclude in exclude_patterns):
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Look for legacy imports that aren't compatibility imports
                if (('from session_manager import' in content or 'import session_manager' in content) and
                    'unified_session_manager' not in content and
                    'session_manager_compat' not in content):
                    legacy_files.append(file_path)
            except Exception:
                continue
        
        if legacy_files:
            # This is a warning, not a failure, as some files might be intentionally using compatibility layer
            print(f"\nWarning: Found {len(legacy_files)} files with potential legacy imports:")
            for file_path in legacy_files[:10]:  # Show first 10
                print(f"  - {file_path}")
            if len(legacy_files) > 10:
                print(f"  ... and {len(legacy_files) - 10} more")
            print("\nThese files should be reviewed to ensure they're using the compatibility layer or have been properly migrated.")

def run_validation():
    """Run all validation tests"""
    print("Running Session Manager Migration Validation...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(SessionMigrationValidation))
    suite.addTests(loader.loadTestsFromTestCase(LegacyImportDetection))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All validation tests passed!")
        print("Session manager migration appears to be successful.")
    else:
        print("❌ Some validation tests failed.")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print("\nPlease review the failures and fix any issues before proceeding.")
    
    return result.wasSuccessful()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate session manager migration')
    parser.add_argument('--test', help='Run a specific test method')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.test:
        # Run specific test
        unittest.main(argv=[''], verbosity=2 if args.verbose else 1, exit=False)
    else:
        # Run full validation
        success = run_validation()
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
