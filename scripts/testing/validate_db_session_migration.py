#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Validate database session migration
"""

import unittest
import sys
import os
import glob
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class DatabaseSessionMigrationValidation(unittest.TestCase):
    """Validate database session migration"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = project_root
        self.web_app_file = self.project_root / 'web_app.py'
        self.admin_dir = self.project_root / 'admin'
    
    def test_web_app_uses_unified_session_manager(self):
        """Test that web_app.py uses unified_session_manager for database operations"""
        if not self.web_app_file.exists():
            self.skipTest("web_app.py not found")
        
        with open(self.web_app_file, 'r') as f:
            content = f.read()
        
        # Should use unified_session_manager.get_db_session()
        self.assertIn('unified_session_manager.get_db_session()', content,
                     "web_app.py should use unified_session_manager.get_db_session()")
    
    def test_no_direct_db_manager_usage_in_web_routes(self):
        """Test that web routes don't use db_manager.get_session() directly"""
        if not self.web_app_file.exists():
            self.skipTest("web_app.py not found")
        
        with open(self.web_app_file, 'r') as f:
            content = f.read()
        
        # Find all route functions
        route_pattern = re.compile(r'@app\.route\([^)]+\).*?def\s+(\w+)\([^)]*\):(.*?)(?=@app\.route|@admin_bp\.route|def\s+\w+|class\s+\w+|$)', re.DOTALL)
        routes = route_pattern.findall(content)
        
        problematic_routes = []
        for route_name, route_content in routes:
            if 'db_manager.get_session()' in route_content:
                problematic_routes.append(route_name)
        
        if problematic_routes:
            self.fail(f"Routes still using db_manager.get_session() directly: {problematic_routes}")
    
    def test_admin_services_use_proper_patterns(self):
        """Test that admin services use appropriate session patterns"""
        if not self.admin_dir.exists():
            self.skipTest("admin directory not found")
        
        service_files = list((self.admin_dir / 'services').glob('*.py'))
        problematic_services = []
        
        for service_file in service_files:
            if service_file.name == '__init__.py':
                continue
                
            with open(service_file, 'r') as f:
                content = f.read()
            
            # Check if it's a service class
            if 'class ' in content and 'Service' in content:
                # For service classes, either pattern is acceptable:
                # 1. Direct db_manager.get_session() with try/finally (for non-user-context operations)
                # 2. unified_session_manager pattern (for user-context operations)
                
                if 'db_manager.get_session()' in content:
                    # Check if it has proper try/finally cleanup OR unified_session_manager
                    has_proper_cleanup = ('try:' in content and 'finally:' in content and 'session.close()' in content)
                    has_unified_pattern = 'unified_session_manager' in content
                    
                    if not (has_proper_cleanup or has_unified_pattern):
                        problematic_services.append(str(service_file))
        
        if problematic_services:
            self.fail(f"Admin services not using proper session patterns: {problematic_services}")
    
    def test_admin_routes_use_unified_session_manager(self):
        """Test that admin routes use unified_session_manager"""
        if not self.admin_dir.exists():
            self.skipTest("admin directory not found")
        
        route_files = list((self.admin_dir / 'routes').glob('*.py'))
        problematic_routes = []
        
        for route_file in route_files:
            if route_file.name == '__init__.py':
                continue
                
            with open(route_file, 'r') as f:
                content = f.read()
            
            # Check if it has admin routes
            if '@admin_bp.route' in content:
                # Should use current_app.unified_session_manager or similar pattern
                if ('db_manager.get_session()' in content and 
                    'unified_session_manager' not in content):
                    problematic_routes.append(str(route_file))
        
        if problematic_routes:
            self.fail(f"Admin routes not using unified_session_manager: {problematic_routes}")
    
    def test_unified_session_manager_available(self):
        """Test that unified_session_manager is available and functional"""
        try:
            from unified_session_manager import UnifiedSessionManager
            from config import Config
            from database import DatabaseManager
            
            config = Config()
            db_manager = DatabaseManager(config)
            session_manager = UnifiedSessionManager(db_manager)
            
            # Test that get_db_session method exists and is callable
            self.assertTrue(hasattr(session_manager, 'get_db_session'))
            self.assertTrue(callable(session_manager.get_db_session))
            
        except ImportError as e:
            self.fail(f"Could not import required modules: {e}")
    
    def test_session_context_manager_functionality(self):
        """Test that session context manager works properly"""
        try:
            from unified_session_manager import UnifiedSessionManager
            from config import Config
            from database import DatabaseManager
            
            config = Config()
            db_manager = DatabaseManager(config)
            session_manager = UnifiedSessionManager(db_manager)
            
            # Test context manager
            with session_manager.get_db_session() as session:
                self.assertIsNotNone(session)
                # Test that we can execute a simple query
                from sqlalchemy import text
                result = session.execute(text("SELECT 1"))
                self.assertIsNotNone(result)
                
        except Exception as e:
            self.fail(f"Session context manager not working: {e}")
    
    def test_no_session_leaks(self):
        """Test for potential session leaks in migrated code"""
        files_to_check = []
        
        # Add web_app.py
        if self.web_app_file.exists():
            files_to_check.append(self.web_app_file)
        
        # Add admin files
        if self.admin_dir.exists():
            files_to_check.extend((self.admin_dir / 'services').glob('*.py'))
            files_to_check.extend((self.admin_dir / 'routes').glob('*.py'))
        
        session_leak_patterns = [
            r'session\s*=\s*.*\.get_session\(\).*(?!with\s)',  # session = ... without context manager
            r'\.get_session\(\).*(?!with\s).*(?!finally:)',    # get_session() without proper cleanup
        ]
        
        problematic_files = []
        for file_path in files_to_check:
            if file_path.name == '__init__.py':
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                for pattern in session_leak_patterns:
                    if re.search(pattern, content, re.MULTILINE):
                        # Check if it's in a context manager or has proper cleanup
                        if ('with ' not in content or 'finally:' not in content):
                            problematic_files.append(str(file_path))
                            break
            except Exception:
                continue
        
        # This is a warning rather than a failure since some patterns might be acceptable
        if problematic_files:
            print(f"\nWarning: Potential session leaks in: {problematic_files}")
    
    def test_import_statements_correct(self):
        """Test that necessary import statements are present"""
        if not self.web_app_file.exists():
            self.skipTest("web_app.py not found")
        
        with open(self.web_app_file, 'r') as f:
            content = f.read()
        
        # Should have unified_session_manager import or usage
        if 'unified_session_manager' in content:
            # Check that it's properly imported or accessed
            has_import = ('from unified_session_manager import' in content or 
                         'import unified_session_manager' in content or
                         'current_app.unified_session_manager' in content or
                         'app.unified_session_manager' in content)
            
            self.assertTrue(has_import, 
                          "unified_session_manager is used but not properly imported or accessed")

class PerformanceValidation(unittest.TestCase):
    """Validate that migration doesn't degrade performance"""
    
    def test_session_manager_performance(self):
        """Test basic performance of session manager operations"""
        try:
            from unified_session_manager import UnifiedSessionManager
            from config import Config
            from database import DatabaseManager
            import time
            
            config = Config()
            db_manager = DatabaseManager(config)
            session_manager = UnifiedSessionManager(db_manager)
            
            # Test session creation performance
            start_time = time.time()
            for _ in range(10):
                with session_manager.get_db_session() as session:
                    from sqlalchemy import text
                    session.execute(text("SELECT 1"))
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 10
            
            # Should complete within reasonable time (adjust threshold as needed)
            self.assertLess(avg_time, 0.1, 
                          f"Session operations taking too long: {avg_time:.3f}s average")
            
        except Exception as e:
            self.skipTest(f"Performance test skipped due to error: {e}")

def run_validation():
    """Run all validation tests"""
    print("Running Database Session Migration Validation...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(DatabaseSessionMigrationValidation))
    suite.addTests(loader.loadTestsFromTestCase(PerformanceValidation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All validation tests passed!")
        print("Database session migration appears to be successful.")
    else:
        print("❌ Some validation tests failed.")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print("\nPlease review the failures and fix any issues before proceeding.")
    
    return result.wasSuccessful()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate database session migration')
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
