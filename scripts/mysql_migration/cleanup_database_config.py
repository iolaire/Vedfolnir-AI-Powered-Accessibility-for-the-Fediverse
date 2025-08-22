#!/usr/bin/env python3
"""
Database Configuration Cleanup Script

Cleans up SQLite-specific configuration logic and ensures MySQL-only configuration.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConfigCleaner:
    """Cleans up SQLite-specific database configuration logic"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.changes_made = []
        self.files_processed = 0
        self.files_modified = 0
        
        # Patterns to find and replace for database configuration cleanup
        self.cleanup_patterns = [
            # SQLite file path patterns
            (r'db_path\s*=\s*["\'][^"\']*\.db["\']', 'database_url = os.getenv("DATABASE_URL")'),
            (r'database_path\s*=\s*["\'][^"\']*\.db["\']', 'database_url = os.getenv("DATABASE_URL")'),
            
            # SQLite file operations
            (r'os\.path\.exists\([^)]*\.db[^)]*\)', 'True  # MySQL server handles database existence'),
            (r'os\.path\.getsize\([^)]*\.db[^)]*\)', '0  # MySQL database size not available via file system'),
            (r'os\.makedirs\([^)]*database_dir[^)]*\)', '# MySQL doesn\'t require local database directory'),
            
            # SQLite-specific conditional logic
            (r'if.*\.endswith\(["\']\.db["\']\)', 'if database_url.startswith("mysql+pymysql://")'),
            (r'if.*["\']MySQL["\'].*in.*database_url', 'if database_url.startswith("mysql+pymysql://")'),
            
            # Database URL format corrections
            (r'MySQL:///', 'mysql+pymysql://'),
            (r'database_url\.replace\(["\']MySQL:///["\'][^)]*\)', 'database_url'),
            
            # File-based database operations
            (r'shutil\.copy\([^)]*\.db[^)]*\)', '# MySQL backup should use mysqldump'),
            (r'shutil\.move\([^)]*\.db[^)]*\)', '# MySQL operations don\'t use file moves'),
        ]
        
        # Files to skip
        self.skip_files = {
            'cleanup_database_config.py',
            'validate_sqlite_removal.py',
            'remove_sqlite_references.py',
            'migrate_to_mysql.py',
        }
    
    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        return (
            file_path.name in self.skip_files or
            file_path.suffix not in ['.py'] or
            '__pycache__' in str(file_path) or
            '.git' in str(file_path) or
            'docs/' in str(file_path) or
            'README' in file_path.name
        )
    
    def clean_database_config_in_file(self, file_path: Path) -> bool:
        """Clean database configuration in a single file"""
        if self.should_skip_file(file_path):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            modified_content = original_content
            file_changes = []
            
            # Apply cleanup patterns
            for pattern, replacement in self.cleanup_patterns:
                matches = re.findall(pattern, modified_content, re.MULTILINE | re.IGNORECASE)
                if matches:
                    modified_content = re.sub(pattern, replacement, modified_content, flags=re.MULTILINE | re.IGNORECASE)
                    file_changes.extend(matches)
            
            # Additional specific cleanups
            modified_content = self._apply_specific_cleanups(modified_content, file_path)
            
            # If content changed, write it back
            if modified_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                self.changes_made.append({
                    'file': str(file_path),
                    'changes': file_changes
                })
                
                logger.info(f"Cleaned database config in: {file_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return False
    
    def _apply_specific_cleanups(self, content: str, file_path: Path) -> str:
        """Apply file-specific cleanups"""
        
        # Clean up database directory references
        if 'database_dir' in content:
            # Remove database_dir field assignments
            content = re.sub(r'database_dir\s*=\s*[^,\n]+[,\n]?', '', content)
            
            # Remove database_dir from function parameters
            content = re.sub(r',\s*database_dir\s*=\s*[^,\)]+', '', content)
            content = re.sub(r'database_dir\s*=\s*[^,\)]+,?\s*', '', content)
            
            # Remove database_dir usage
            content = re.sub(r'config\.storage\.database_dir', '"storage"  # MySQL doesn\'t use local database directory', content)
        
        # Clean up SQLite-specific imports that might have been missed
        content = re.sub(r'import sqlite3\n', '', content)
        content = re.sub(r'from sqlite3 import[^\n]*\n', '', content)
        
        # Clean up file-based database operations
        if '.db' in content and file_path.suffix == '.py':
            # Replace .db file references with MySQL connection references
            content = re.sub(r'["\'][^"\']*\.db["\']', '"MySQL database"', content)
        
        return content
    
    def clean_project_database_config(self) -> Dict[str, int]:
        """Clean database configuration in all Python files"""
        stats = {
            'files_processed': 0,
            'files_modified': 0,
        }
        
        for file_path in self.project_root.rglob('*.py'):
            stats['files_processed'] += 1
            
            if self.clean_database_config_in_file(file_path):
                stats['files_modified'] += 1
        
        return stats
    
    def validate_mysql_only_config(self) -> List[str]:
        """Validate that configuration is MySQL-only"""
        issues = []
        
        # Check main config file
        config_file = self.project_root / 'config.py'
        if config_file.exists():
            with open(config_file, 'r') as f:
                content = f.read()
            
            # Check for SQLite references (excluding comments)
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                if line_stripped.startswith('#'):
                    continue  # Skip comments
                if 'sqlite' in line.lower():
                    issues.append(f"config.py line {line_num} contains SQLite reference: {line_stripped}")
            
            # Check for database_dir references (excluding comments)
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                if line_stripped.startswith('#'):
                    continue  # Skip comments
                if 'database_dir' in line and 'database_dir' not in line_stripped.split('#')[0]:
                    # Only flag if database_dir is not in a comment
                    if '#' in line:
                        code_part = line.split('#')[0].strip()
                        if 'database_dir' in code_part:
                            issues.append(f"config.py line {line_num} contains database_dir reference: {code_part}")
                    elif 'database_dir' in line:
                        issues.append(f"config.py line {line_num} contains database_dir reference: {line_stripped}")
            
            # Check for proper MySQL validation
            if 'mysql+pymysql://' not in content:
                issues.append("config.py missing MySQL URL validation")
        
        return issues
    
    def generate_report(self, stats: Dict[str, int], issues: List[str]) -> str:
        """Generate cleanup report"""
        report = [
            "=== Database Configuration Cleanup Report ===",
            f"Files processed: {stats['files_processed']}",
            f"Files modified: {stats['files_modified']}",
            f"Total changes: {len(self.changes_made)}",
            ""
        ]
        
        if issues:
            report.extend([
                "⚠️  VALIDATION ISSUES:",
                ""
            ])
            for issue in issues:
                report.append(f"  - {issue}")
            report.append("")
        
        if self.changes_made:
            report.extend([
                "📝 MODIFIED FILES:",
                ""
            ])
            for change in self.changes_made:
                report.append(f"  {change['file']}")
                for item in change['changes'][:3]:  # Show first 3 changes
                    report.append(f"    - {item}")
                if len(change['changes']) > 3:
                    report.append(f"    ... and {len(change['changes']) - 3} more")
                report.append("")
        
        if not self.changes_made and not issues:
            report.extend([
                "✅ SUCCESS: Database configuration is already clean!",
                "No SQLite-specific configuration logic found.",
            ])
        
        return "\n".join(report)


def main():
    """Main function to clean up database configuration"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info("Starting database configuration cleanup...")
    logger.info(f"Project root: {project_root}")
    
    cleaner = DatabaseConfigCleaner(project_root)
    
    # Clean database configuration
    stats = cleaner.clean_project_database_config()
    
    # Validate MySQL-only configuration
    issues = cleaner.validate_mysql_only_config()
    
    # Generate report
    report = cleaner.generate_report(stats, issues)
    
    # Save report
    report_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'database_config_cleanup_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info("Database configuration cleanup completed")
    logger.info(f"Files processed: {stats['files_processed']}")
    logger.info(f"Files modified: {stats['files_modified']}")
    logger.info(f"Validation issues: {len(issues)}")
    logger.info(f"Report saved to: {report_path}")
    
    if issues:
        logger.warning("⚠️  Validation issues found - check report for details")
        return False
    else:
        logger.info("✅ Database configuration cleanup successful")
        return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
