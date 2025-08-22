#!/usr/bin/env python3
"""
Test Migration Script for MySQL

Migrates existing test files from SQLite-specific configurations to MySQL-compatible configurations.
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Set

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestMigrationTool:
    """Tool to migrate tests from SQLite to MySQL configurations"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.tests_dir = self.project_root / 'tests'
        self.migrations_applied = []
        self.issues_found = []
        
        # Patterns to find and replace
        self.sqlite_patterns = {
            # SQLite database URLs
            r'sqlite:///[^\'"\s]+': 'mysql+pymysql://test_user:test_pass@localhost/test_db',
            r'\'sqlite:///[^\']+\'': '\'mysql+pymysql://test_user:test_pass@localhost/test_db\'',
            r'"sqlite:///[^"]+"': '"mysql+pymysql://test_user:test_pass@localhost/test_db"',
            
            # Temporary file database patterns
            r'tempfile\.mkstemp\(\)': 'tempfile.mkdtemp(prefix="mysql_test_")',
            r'self\.db_fd,\s*self\.db_path\s*=\s*tempfile\.mkstemp\(\)': 'self.db_path = tempfile.mkdtemp(prefix="mysql_test_")',
            
            # SQLite-specific imports
            r'from\s+sqlite3\s+import': '# SQLite import removed for MySQL',
            r'import\s+sqlite3': '# SQLite import removed for MySQL',
            
            # Database cleanup patterns
            r'os\.close\(self\.db_fd\)': '# MySQL: No file descriptor to close',
            r'os\.unlink\(self\.db_path\)': 'shutil.rmtree(self.db_path, ignore_errors=True)',
            
            # In-memory database patterns
            r':memory:': 'mysql+pymysql://test_user:test_pass@localhost/test_db',
            r'\'memory\'': '\'mysql+pymysql://test_user:test_pass@localhost/test_db\'',
        }
        
        # MySQL-specific imports to add
        self.mysql_imports = [
            'from tests.mysql_test_base import MySQLTestBase, MySQLIntegrationTestBase, MySQLWebTestBase',
            'from tests.mysql_test_config import MySQLTestConfig, MySQLTestFixtures',
            'import shutil',
        ]
        
        # Base class replacements
        self.base_class_replacements = {
            'unittest.TestCase': 'MySQLTestBase',
            'TestCase': 'MySQLTestBase',
        }
    
    def analyze_test_files(self) -> Dict[str, List[str]]:
        """Analyze test files for SQLite-specific patterns"""
        logger.info("Analyzing test files for SQLite patterns...")
        
        analysis = {
            'sqlite_patterns_found': [],
            'files_needing_migration': [],
            'base_class_issues': [],
            'import_issues': [],
        }
        
        for test_file in self.tests_dir.rglob('test_*.py'):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_issues = []
                
                # Check for SQLite patterns
                for pattern in self.sqlite_patterns.keys():
                    if re.search(pattern, content, re.IGNORECASE):
                        file_issues.append(f"SQLite pattern: {pattern}")
                        analysis['sqlite_patterns_found'].append(str(test_file))
                
                # Check for base class issues
                if 'unittest.TestCase' in content or 'class Test' in content:
                    if 'MySQLTestBase' not in content:
                        file_issues.append("Uses unittest.TestCase instead of MySQLTestBase")
                        analysis['base_class_issues'].append(str(test_file))
                
                # Check for import issues
                if 'tempfile.mkstemp' in content:
                    file_issues.append("Uses tempfile.mkstemp (SQLite pattern)")
                    analysis['import_issues'].append(str(test_file))
                
                if file_issues:
                    analysis['files_needing_migration'].append(str(test_file))
                    logger.info(f"Issues found in {test_file}: {len(file_issues)} issues")
                
            except Exception as e:
                logger.error(f"Error analyzing {test_file}: {e}")
        
        return analysis
    
    def migrate_test_file(self, test_file: Path) -> bool:
        """Migrate a single test file to MySQL configuration"""
        logger.info(f"Migrating test file: {test_file}")
        
        try:
            # Read original content
            with open(test_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            changes_made = []
            
            # Apply SQLite pattern replacements
            for pattern, replacement in self.sqlite_patterns.items():
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    changes_made.append(f"Replaced SQLite pattern: {pattern}")
            
            # Replace base classes
            for old_base, new_base in self.base_class_replacements.items():
                if old_base in content:
                    content = content.replace(old_base, new_base)
                    changes_made.append(f"Replaced base class: {old_base} -> {new_base}")
            
            # Add MySQL imports if needed
            if changes_made and 'MySQLTestBase' not in original_content:
                # Find the import section
                import_section_end = 0
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        import_section_end = i
                
                # Insert MySQL imports after existing imports
                mysql_import_lines = [
                    '',
                    '# MySQL test configuration imports',
                    'from tests.mysql_test_base import MySQLTestBase, MySQLIntegrationTestBase, MySQLWebTestBase',
                    'from tests.mysql_test_config import MySQLTestConfig, MySQLTestFixtures',
                    ''
                ]
                
                lines[import_section_end + 1:import_section_end + 1] = mysql_import_lines
                content = '\n'.join(lines)
                changes_made.append("Added MySQL test imports")
            
            # Fix specific test setup patterns
            content = self._fix_test_setup_patterns(content, changes_made)
            
            # Only write if changes were made
            if changes_made:
                # Create backup
                backup_file = test_file.with_suffix('.py.backup')
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Write migrated content
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.migrations_applied.append({
                    'file': str(test_file),
                    'changes': changes_made,
                    'backup': str(backup_file)
                })
                
                logger.info(f"✅ Migrated {test_file}: {len(changes_made)} changes")
                return True
            else:
                logger.info(f"⏭️  No changes needed for {test_file}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to migrate {test_file}: {e}")
            self.issues_found.append(f"Migration failed for {test_file}: {e}")
            return False
    
    def _fix_test_setup_patterns(self, content: str, changes_made: List[str]) -> str:
        """Fix common test setup patterns for MySQL"""
        
        # Fix setUp method patterns
        setup_fixes = [
            # Replace tempfile.mkstemp with MySQL test config
            (
                r'def setUp\(self\):\s*"""[^"]*"""\s*# Create temporary database\s*self\.db_fd,\s*self\.db_path\s*=\s*tempfile\.mkstemp\(\)',
                '''def setUp(self):
        """Set up test with MySQL database"""
        super().setUp()'''
            ),
            
            # Fix database URL configuration
            (
                r'self\.config\.storage\.database_url\s*=\s*f\'mysql\+pymysql://\{self\.db_path\}\'',
                '# MySQL database URL configured by MySQLTestBase'
            ),
            
            # Fix tearDown method
            (
                r'def tearDown\(self\):\s*"""[^"]*"""\s*os\.close\(self\.db_fd\)\s*os\.unlink\(self\.db_path\)',
                '''def tearDown(self):
        """Clean up test resources"""
        super().tearDown()'''
            ),
        ]
        
        for pattern, replacement in setup_fixes:
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                changes_made.append(f"Fixed test setup pattern")
        
        return content
    
    def create_mysql_test_examples(self) -> bool:
        """Create example test files showing MySQL test patterns"""
        logger.info("Creating MySQL test examples...")
        
        examples_dir = self.tests_dir / 'examples'
        examples_dir.mkdir(exist_ok=True)
        
        # Example 1: Basic MySQL test
        basic_example = '''#!/usr/bin/env python3
"""
Example: Basic MySQL Test

Shows how to create a basic test using MySQL test base classes.
"""

from tests.mysql_test_base import MySQLTestBase
from models import User, PlatformConnection


class ExampleBasicMySQLTest(MySQLTestBase):
    """Example of basic MySQL test"""
    
    def test_user_creation(self):
        """Test creating a user in MySQL database"""
        # Test data is automatically created by MySQLTestBase
        self.assertIsNotNone(self.test_user)
        self.assertEqual(self.test_user.username, "testuser")
        
        # Test database state
        self.assert_database_state(User, 1)
        self.assert_record_exists(User, username="testuser")
    
    def test_platform_connection(self):
        """Test platform connection functionality"""
        self.assertIsNotNone(self.test_platform)
        self.assertEqual(self.test_platform.platform_type, "pixelfed")
        
        # Test database relationships
        self.assertEqual(self.test_platform.user_id, self.test_user.id)
        self.assert_database_state(PlatformConnection, 1)


if __name__ == "__main__":
    import unittest
    unittest.main()
'''
        
        # Example 2: Integration test
        integration_example = '''#!/usr/bin/env python3
"""
Example: MySQL Integration Test

Shows how to create integration tests with external service mocking.
"""

from tests.mysql_test_base import MySQLIntegrationTestBase
from models import Post, Image, ProcessingStatus


class ExampleMySQLIntegrationTest(MySQLIntegrationTestBase):
    """Example of MySQL integration test"""
    
    def test_post_processing_workflow(self):
        """Test complete post processing workflow"""
        # Test data is automatically created by MySQLIntegrationTestBase
        self.assertIsNotNone(self.test_post)
        self.assertIsNotNone(self.test_image)
        
        # Test initial state
        self.assertEqual(self.test_image.status, ProcessingStatus.PENDING)
        
        # Mock external service calls
        self.mock_ollama.generate_caption.return_value = "Test caption"
        
        # Test processing logic here
        # ... your integration test logic ...
        
        # Verify database state
        self.assert_database_state(Post, 1)
        self.assert_database_state(Image, 1)
    
    def test_error_handling(self):
        """Test error handling in integration scenarios"""
        # Mock service failures
        self.mock_ollama.generate_caption.side_effect = Exception("Service unavailable")
        
        # Test error handling logic
        # ... your error handling test logic ...


if __name__ == "__main__":
    import unittest
    unittest.main()
'''
        
        # Example 3: Web test
        web_example = '''#!/usr/bin/env python3
"""
Example: MySQL Web Test

Shows how to create web/Flask tests with MySQL backend.
"""

from tests.mysql_test_base import MySQLWebTestBase


class ExampleMySQLWebTest(MySQLWebTestBase):
    """Example of MySQL web test"""
    
    def test_login_functionality(self):
        """Test user login with MySQL backend"""
        # Login with test user
        response = self.login_user()
        self.assertEqual(response.status_code, 200)
        
        # Test authenticated access
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
    
    def test_platform_management(self):
        """Test platform management interface"""
        # Login first
        self.login_user()
        
        # Test platform list
        response = self.client.get('/platforms')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Platform', response.data)
    
    def test_logout_functionality(self):
        """Test user logout"""
        # Login and logout
        self.login_user()
        response = self.logout_user()
        self.assertEqual(response.status_code, 200)
        
        # Test access after logout
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)  # Redirect to login


if __name__ == "__main__":
    import unittest
    unittest.main()
'''
        
        # Write example files
        examples = [
            ('example_basic_mysql_test.py', basic_example),
            ('example_mysql_integration_test.py', integration_example),
            ('example_mysql_web_test.py', web_example),
        ]
        
        for filename, content in examples:
            example_file = examples_dir / filename
            with open(example_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Created example: {example_file}")
        
        return True
    
    def generate_migration_report(self) -> str:
        """Generate comprehensive migration report"""
        analysis = self.analyze_test_files()
        
        report = [
            "=== MySQL Test Migration Report ===",
            "",
            f"Project Root: {self.project_root}",
            f"Tests Directory: {self.tests_dir}",
            "",
            "ANALYSIS RESULTS:",
            f"Files with SQLite patterns: {len(analysis['sqlite_patterns_found'])}",
            f"Files needing migration: {len(analysis['files_needing_migration'])}",
            f"Base class issues: {len(analysis['base_class_issues'])}",
            f"Import issues: {len(analysis['import_issues'])}",
            "",
            "MIGRATION RESULTS:",
            f"Files migrated: {len(self.migrations_applied)}",
            f"Issues encountered: {len(self.issues_found)}",
            ""
        ]
        
        if self.migrations_applied:
            report.extend([
                "SUCCESSFULLY MIGRATED FILES:",
                ""
            ])
            for migration in self.migrations_applied:
                report.append(f"✅ {migration['file']}")
                for change in migration['changes']:
                    report.append(f"   - {change}")
                report.append(f"   - Backup: {migration['backup']}")
                report.append("")
        
        if self.issues_found:
            report.extend([
                "🚨 ISSUES FOUND:",
                ""
            ])
            for issue in self.issues_found:
                report.append(f"  - {issue}")
            report.append("")
        
        if analysis['files_needing_migration']:
            report.extend([
                "FILES THAT NEED MANUAL REVIEW:",
                ""
            ])
            for file_path in analysis['files_needing_migration']:
                report.append(f"  - {file_path}")
            report.append("")
        
        report.extend([
            "MYSQL TEST CONFIGURATION:",
            "✅ MySQL test base classes created",
            "✅ MySQL test configuration module created",
            "✅ MySQL test fixtures and utilities available",
            "✅ Example test files created",
            "",
            "NEXT STEPS:",
            "1. Review migrated test files for correctness",
            "2. Update any remaining SQLite-specific test logic",
            "3. Ensure MySQL server is available for testing",
            "4. Run test suite to validate migrations",
            "5. Remove backup files after validation",
        ])
        
        return "\n".join(report)
    
    def migrate_all_tests(self) -> bool:
        """Migrate all test files to MySQL configuration"""
        logger.info("Starting comprehensive test migration to MySQL...")
        
        # Create MySQL test examples first
        self.create_mysql_test_examples()
        
        # Find all test files
        test_files = list(self.tests_dir.rglob('test_*.py'))
        logger.info(f"Found {len(test_files)} test files to analyze")
        
        # Migrate each test file
        success_count = 0
        for test_file in test_files:
            if self.migrate_test_file(test_file):
                success_count += 1
        
        logger.info(f"Migration completed: {success_count}/{len(test_files)} files processed")
        
        return success_count == len(test_files)


def main():
    """Main migration function"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info("Starting MySQL test migration...")
    logger.info(f"Project root: {project_root}")
    
    migrator = TestMigrationTool(project_root)
    
    # Perform analysis first
    analysis = migrator.analyze_test_files()
    logger.info(f"Analysis complete: {len(analysis['files_needing_migration'])} files need migration")
    
    # Perform migration
    success = migrator.migrate_all_tests()
    
    # Generate report
    report = migrator.generate_migration_report()
    
    # Save report
    report_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'test_migration_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info("MySQL test migration completed")
    logger.info(f"Report saved to: {report_path}")
    
    if success:
        logger.info("✅ All test files migrated successfully")
        return True
    else:
        logger.error("❌ Some test files failed to migrate")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
