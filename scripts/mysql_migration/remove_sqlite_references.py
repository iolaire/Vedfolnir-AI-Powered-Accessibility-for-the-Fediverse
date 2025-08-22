#!/usr/bin/env python3
"""
SQLite Reference Removal Script

This script systematically removes SQLite imports and references from the codebase,
replacing them with MySQL equivalents where appropriate.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLiteReferenceRemover:
    """Removes SQLite references and replaces them with MySQL equivalents"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.changes_made = []
        self.files_processed = 0
        self.files_modified = 0
        
        # Patterns to find and replace
        self.sqlite_patterns = [
            # Import statements
            (r'^import sqlite3\s*$', ''),
            (r'^from sqlite3 import.*$', ''),
            (r'import sqlite3,', 'import'),
            (r', sqlite3', ''),
            
            # SQLite-specific code patterns
            (r'sqlite3\.connect\([^)]+\)', 'engine.connect()'),
            (r'sqlite3\.OperationalError', 'SQLAlchemyError'),
            (r'sqlite3\.Error', 'SQLAlchemyError'),
            (r'sqlite3\.IntegrityError', 'SQLAlchemyError'),
            
            # SQLite-specific SQL queries
            (r'SELECT name FROM sqlite_master', 'SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()'),
            (r'PRAGMA table_info\([^)]+\)', 'SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()'),
            (r'PRAGMA foreign_keys', '-- MySQL foreign keys are always enabled'),
            
            # SQLite-specific comments
            (r'# SQLite.*', '# MySQL'),
            (r'# sqlite.*', '# mysql'),
            (r'SQLite', 'MySQL'),
            (r'sqlite', 'mysql'),
        ]
        
        # Files to skip (already converted or not relevant)
        self.skip_files = {
            'mysql_connection_validator.py',
            'validate_mysql_config.py',
            'validate_mysql_database_manager.py',
            'validate_mysql_error_handling.py',
            'migrate_to_mysql.py',
            'remove_sqlite_references.py'
        }
    
    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        return (
            file_path.name in self.skip_files or
            file_path.suffix not in ['.py'] or
            '__pycache__' in str(file_path) or
            '.git' in str(file_path)
        )
    
    def process_file(self, file_path: Path) -> bool:
        """Process a single file to remove SQLite references"""
        if self.should_skip_file(file_path):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            modified_content = original_content
            file_changes = []
            
            # Apply pattern replacements
            for pattern, replacement in self.sqlite_patterns:
                matches = re.findall(pattern, modified_content, re.MULTILINE | re.IGNORECASE)
                if matches:
                    modified_content = re.sub(pattern, replacement, modified_content, flags=re.MULTILINE | re.IGNORECASE)
                    file_changes.extend(matches)
            
            # Remove empty import lines
            modified_content = re.sub(r'^\s*import\s*$', '', modified_content, flags=re.MULTILINE)
            
            # Clean up multiple empty lines
            modified_content = re.sub(r'\n\s*\n\s*\n', '\n\n', modified_content)
            
            # If content changed, write it back
            if modified_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                self.changes_made.append({
                    'file': str(file_path),
                    'changes': file_changes
                })
                
                logger.info(f"Modified: {file_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return False
    
    def remove_sqlite_test_configurations(self, file_path: Path) -> bool:
        """Remove SQLite-specific test configurations"""
        if not file_path.name.startswith('test_'):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Remove SQLite test database configurations
            sqlite_test_patterns = [
                r'DATABASE_URL.*sqlite.*',
                r'db_path.*\.db.*',
                r'sqlite:///.*',
                r'test.*\.db',
                r'memory.*database',
                r':memory:',
            ]
            
            for pattern in sqlite_test_patterns:
                content = re.sub(pattern, 'DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db', content, flags=re.IGNORECASE)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Updated test configuration: {file_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating test configuration {file_path}: {e}")
            return False
    
    def process_directory(self, directory: Path = None) -> Dict[str, int]:
        """Process all Python files in directory recursively"""
        if directory is None:
            directory = self.project_root
        
        stats = {
            'files_processed': 0,
            'files_modified': 0,
            'test_configs_updated': 0
        }
        
        for file_path in directory.rglob('*.py'):
            stats['files_processed'] += 1
            
            # Process SQLite references
            if self.process_file(file_path):
                stats['files_modified'] += 1
            
            # Update test configurations
            if self.remove_sqlite_test_configurations(file_path):
                stats['test_configs_updated'] += 1
        
        return stats
    
    def generate_report(self) -> str:
        """Generate a report of changes made"""
        report = [
            "=== SQLite Reference Removal Report ===",
            f"Files processed: {self.files_processed}",
            f"Files modified: {self.files_modified}",
            f"Total changes: {len(self.changes_made)}",
            "",
            "Modified files:"
        ]
        
        for change in self.changes_made:
            report.append(f"  {change['file']}")
            for item in change['changes'][:3]:  # Show first 3 changes
                report.append(f"    - {item}")
            if len(change['changes']) > 3:
                report.append(f"    ... and {len(change['changes']) - 3} more")
        
        return "\n".join(report)


def main():
    """Main function to remove SQLite references"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info("Starting SQLite reference removal process...")
    logger.info(f"Project root: {project_root}")
    
    remover = SQLiteReferenceRemover(project_root)
    stats = remover.process_directory()
    
    logger.info("SQLite reference removal completed")
    logger.info(f"Files processed: {stats['files_processed']}")
    logger.info(f"Files modified: {stats['files_modified']}")
    logger.info(f"Test configurations updated: {stats['test_configs_updated']}")
    
    # Generate and save report
    report = remover.generate_report()
    report_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'sqlite_removal_report.txt')
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info(f"Detailed report saved to: {report_path}")
    
    return stats['files_modified'] > 0


if __name__ == "__main__":
    success = main()
    if success:
        logger.info("✅ SQLite references removed successfully")
    else:
        logger.info("ℹ️  No SQLite references found to remove")
