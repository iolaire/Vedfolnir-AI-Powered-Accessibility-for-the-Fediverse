#!/usr/bin/env python3
"""
Integration Test Migration Script for MySQL

Migrates all integration tests from SQLite-based fixtures to MySQL test infrastructure.
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegrationTestMigrator:
    """Migrates integration tests to MySQL infrastructure"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.integration_tests_dir = self.project_root / 'tests' / 'integration'
        self.migrations_applied = []
        self.issues_found = []
        
        # Patterns to find and replace
        self.migration_patterns = {
            # Old fixture imports
            r'from tests\.fixtures\.platform_fixtures import PlatformTestCase': 
                'from tests.mysql_test_base import MySQLIntegrationTestBase',
            
            r'from tests\.fixtures\.platform_fixtures import PlatformTestFixtures':
                'from tests.mysql_test_config import MySQLTestFixtures',
            
            # Base class replacements
            r'class\s+(\w+)\(PlatformTestCase\)':
                r'class \1(MySQLIntegrationTestBase)',
            
            r'class\s+(\w+)\(unittest\.TestCase\)':
                r'class \1(MySQLIntegrationTestBase)',
            
            # SQLite database setup patterns
            r'tempfile\.mkstemp\(\)':
                'tempfile.mkdtemp(prefix="mysql_integration_test_")',
            
            r'sqlite:///[^\'"\s]+':
                'mysql+pymysql://database_user_1d7b0d0696a20:EQA&bok7@localhost/vedfolnir',
            
            # Database manager creation patterns
            r'DatabaseManager\(.*?\)':
                'self.get_database_manager()',
            
            # Session creation patterns
            r'sessionmaker\(bind=.*?\)':
                'self.get_test_session',
        }
        
        # Required imports for MySQL integration tests
        self.required_imports = [
            'from tests.mysql_test_base import MySQLIntegrationTestBase',
            'from tests.mysql_test_config import MySQLTestFixtures',
            'import logging',
        ]
    
    def analyze_integration_tests(self) -> Dict[str, List[str]]:
        """Analyze integration tests for migration needs"""
        logger.info("Analyzing integration tests for migration...")
        
        analysis = {
            'files_needing_migration': [],
            'sqlite_patterns_found': [],
            'fixture_usage': [],
            'performance_tests': [],
        }
        
        for test_file in self.integration_tests_dir.glob('test_*.py'):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_issues = []
                
                # Check for SQLite patterns
                if 'sqlite' in content.lower() or 'tempfile.mkstemp' in content:
                    file_issues.append("Contains SQLite patterns")
                    analysis['sqlite_patterns_found'].append(str(test_file))
                
                # Check for old fixture usage
                if 'PlatformTestCase' in content or 'platform_fixtures' in content:
                    file_issues.append("Uses old platform fixtures")
                    analysis['fixture_usage'].append(str(test_file))
                
                # Check for performance tests
                if 'performance' in test_file.name.lower() or 'Performance' in content:
                    file_issues.append("Performance test")
                    analysis['performance_tests'].append(str(test_file))
                
                # Check if MySQL migration is needed
                if 'MySQLIntegrationTestBase' not in content and any([
                    'unittest.TestCase' in content,
                    'PlatformTestCase' in content,
                    'sqlite' in content.lower(),
                    'tempfile.mkstemp' in content
                ]):
                    file_issues.append("Needs MySQL migration")
                    analysis['files_needing_migration'].append(str(test_file))
                
                if file_issues:
                    logger.info(f"Issues found in {test_file.name}: {len(file_issues)} issues")
                
            except Exception as e:
                logger.error(f"Error analyzing {test_file}: {e}")
        
        return analysis
    
    def migrate_integration_test(self, test_file: Path) -> bool:
        """Migrate a single integration test file"""
        logger.info(f"Migrating integration test: {test_file}")
        
        try:
            # Read original content
            with open(test_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            changes_made = []
            
            # Apply migration patterns
            for pattern, replacement in self.migration_patterns.items():
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    changes_made.append(f"Applied pattern: {pattern}")
            
            # Add required imports if needed
            if changes_made and 'MySQLIntegrationTestBase' not in original_content:
                # Find the import section
                import_section_end = 0
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        import_section_end = i
                
                # Insert MySQL imports after existing imports
                mysql_import_lines = [
                    '',
                    '# MySQL integration test imports',
                    'from tests.mysql_test_base import MySQLIntegrationTestBase',
                    'from tests.mysql_test_config import MySQLTestFixtures',
                    ''
                ]
                
                lines[import_section_end + 1:import_section_end + 1] = mysql_import_lines
                content = '\n'.join(lines)
                changes_made.append("Added MySQL integration test imports")
            
            # Fix specific integration test patterns
            content = self._fix_integration_test_patterns(content, changes_made)
            
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
                
                logger.info(f"✅ Migrated {test_file.name}: {len(changes_made)} changes")
                return True
            else:
                logger.info(f"⏭️  No changes needed for {test_file.name}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to migrate {test_file}: {e}")
            self.issues_found.append(f"Migration failed for {test_file}: {e}")
            return False
    
    def _fix_integration_test_patterns(self, content: str, changes_made: List[str]) -> str:
        """Fix specific integration test patterns"""
        
        # Fix setUp method patterns
        setup_fixes = [
            # Replace old setUp patterns
            (
                r'def setUp\(self\):\s*"""[^"]*"""\s*super\(\)\.setUp\(\)',
                '''def setUp(self):
        """Set up integration test with MySQL"""
        super().setUp()'''
            ),
            
            # Fix database manager usage
            (
                r'self\.db_manager\s*=\s*DatabaseManager\([^)]*\)',
                '# Database manager available as self.db_manager'
            ),
            
            # Fix session creation
            (
                r'self\.session\s*=\s*sessionmaker\([^)]*\)',
                '# Session available as self.session'
            ),
        ]
        
        for pattern, replacement in setup_fixes:
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                changes_made.append(f"Fixed integration test setup pattern")
        
        return content
    
    def migrate_all_integration_tests(self) -> bool:
        """Migrate all integration tests to MySQL"""
        logger.info("Starting integration test migration to MySQL...")
        
        # Find all integration test files
        test_files = list(self.integration_tests_dir.glob('test_*.py'))
        logger.info(f"Found {len(test_files)} integration test files")
        
        # Migrate each test file
        success_count = 0
        for test_file in test_files:
            if self.migrate_integration_test(test_file):
                success_count += 1
        
        logger.info(f"Integration test migration completed: {success_count}/{len(test_files)} files processed")
        
        return success_count == len(test_files)
    
    def generate_migration_report(self) -> str:
        """Generate comprehensive migration report"""
        analysis = self.analyze_integration_tests()
        
        report = [
            "=== Integration Test MySQL Migration Report ===",
            "",
            f"Project Root: {self.project_root}",
            f"Integration Tests Directory: {self.integration_tests_dir}",
            "",
            "ANALYSIS RESULTS:",
            f"Files needing migration: {len(analysis['files_needing_migration'])}",
            f"SQLite patterns found: {len(analysis['sqlite_patterns_found'])}",
            f"Old fixture usage: {len(analysis['fixture_usage'])}",
            f"Performance tests: {len(analysis['performance_tests'])}",
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
                report.append(f"✅ {Path(migration['file']).name}")
                for change in migration['changes']:
                    report.append(f"   - {change}")
                report.append(f"   - Backup: {Path(migration['backup']).name}")
                report.append("")
        
        if self.issues_found:
            report.extend([
                "🚨 ISSUES FOUND:",
                ""
            ])
            for issue in self.issues_found:
                report.append(f"  - {issue}")
            report.append("")
        
        if analysis['performance_tests']:
            report.extend([
                "PERFORMANCE TESTS IDENTIFIED:",
                ""
            ])
            for test_file in analysis['performance_tests']:
                report.append(f"  - {Path(test_file).name}")
            report.append("")
        
        report.extend([
            "MYSQL INTEGRATION TEST FEATURES:",
            "✅ MySQL connection pooling validation",
            "✅ MySQL-specific performance characteristics testing",
            "✅ Automatic test data cleanup with unique identifiers",
            "✅ Integration with external service mocking",
            "✅ MySQL optimization feature testing",
            "",
            "NEXT STEPS:",
            "1. Review migrated integration test files for correctness",
            "2. Run integration test suite to validate migrations",
            "3. Update performance tests to measure MySQL-specific metrics",
            "4. Remove backup files after validation",
            "5. Update CI/CD pipelines to use MySQL for integration tests",
        ])
        
        return "\n".join(report)


def main():
    """Main migration function"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info("Starting integration test migration to MySQL...")
    logger.info(f"Project root: {project_root}")
    
    migrator = IntegrationTestMigrator(project_root)
    
    # Perform analysis first
    analysis = migrator.analyze_integration_tests()
    logger.info(f"Analysis complete: {len(analysis['files_needing_migration'])} files need migration")
    
    # Perform migration
    success = migrator.migrate_all_integration_tests()
    
    # Generate report
    report = migrator.generate_migration_report()
    
    # Save report
    report_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'integration_test_migration_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info("Integration test migration completed")
    logger.info(f"Report saved to: {report_path}")
    
    if success:
        logger.info("✅ All integration test files migrated successfully")
        return True
    else:
        logger.error("❌ Some integration test files failed to migrate")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
