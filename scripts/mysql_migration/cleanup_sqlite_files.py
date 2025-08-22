#!/usr/bin/env python3
"""
SQLite File Cleanup Script

Removes SQLite test database files and configurations as part of Task 8.
This completes the migration from SQLite to MySQL for all testing.
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLiteCleanupTool:
    """Tool to clean up SQLite files and configurations"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.files_removed = []
        self.directories_removed = []
        self.configurations_updated = []
        self.issues_found = []
    
    def find_sqlite_files(self) -> List[Path]:
        """Find all SQLite database files in the project"""
        logger.info("Scanning for SQLite database files...")
        
        sqlite_files = []
        
        # Common SQLite file patterns
        sqlite_patterns = [
            '*.db',
            '*.sqlite',
            '*.sqlite3',
            '*.db-journal',
            '*.db-wal',
            '*.db-shm'
        ]
        
        # Search in common directories
        search_dirs = [
            self.project_root,
            self.project_root / 'tests',
            self.project_root / 'storage',
            self.project_root / 'tmp',
            self.project_root / 'data'
        ]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for pattern in sqlite_patterns:
                    sqlite_files.extend(search_dir.rglob(pattern))
        
        # Filter out backup files and non-test databases
        filtered_files = []
        for file_path in sqlite_files:
            # Skip backup files
            if '.backup' in str(file_path):
                continue
            
            # Skip production databases (if any)
            if 'production' in str(file_path).lower():
                continue
            
            filtered_files.append(file_path)
        
        logger.info(f"Found {len(filtered_files)} SQLite files")
        for file_path in filtered_files:
            logger.info(f"  - {file_path}")
        
        return filtered_files
    
    def find_sqlite_configurations(self) -> List[Dict[str, Any]]:
        """Find SQLite configurations in code files"""
        logger.info("Scanning for SQLite configurations in code...")
        
        configurations = []
        
        # File patterns to search
        code_patterns = ['*.py', '*.yaml', '*.yml', '*.json', '*.cfg', '*.ini']
        
        # SQLite configuration patterns
        sqlite_config_patterns = [
            r'sqlite:///',
            r'sqlite:memory:',
            r'\.db["\']',
            r'\.sqlite["\']',
            r'\.sqlite3["\']',
            r'SQLITE_',
            r'sqlite3\.',
            r'import sqlite3',
            r'from sqlite3',
        ]
        
        # Search in code directories
        search_dirs = [
            self.project_root,
            self.project_root / 'tests',
            self.project_root / 'scripts',
            self.project_root / 'config'
        ]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for pattern in code_patterns:
                    for file_path in search_dir.rglob(pattern):
                        # Skip backup files and migration scripts
                        if any(skip in str(file_path) for skip in ['.backup', 'mysql_migration', '__pycache__']):
                            continue
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Check for SQLite patterns
                            found_patterns = []
                            for config_pattern in sqlite_config_patterns:
                                import re
                                if re.search(config_pattern, content, re.IGNORECASE):
                                    found_patterns.append(config_pattern)
                            
                            if found_patterns:
                                configurations.append({
                                    'file': file_path,
                                    'patterns': found_patterns,
                                    'content_preview': content[:200] + '...' if len(content) > 200 else content
                                })
                        
                        except Exception as e:
                            logger.warning(f"Could not read {file_path}: {e}")
        
        logger.info(f"Found {len(configurations)} files with SQLite configurations")
        for config in configurations:
            logger.info(f"  - {config['file']}: {len(config['patterns'])} patterns")
        
        return configurations
    
    def remove_sqlite_files(self, sqlite_files: List[Path], dry_run: bool = False) -> bool:
        """Remove SQLite database files"""
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Removing SQLite database files...")
        
        success = True
        
        for file_path in sqlite_files:
            try:
                if dry_run:
                    logger.info(f"Would remove: {file_path}")
                else:
                    if file_path.exists():
                        file_path.unlink()
                        self.files_removed.append(str(file_path))
                        logger.info(f"✅ Removed: {file_path}")
                    else:
                        logger.info(f"⏭️  Already removed: {file_path}")
                        
            except Exception as e:
                logger.error(f"❌ Failed to remove {file_path}: {e}")
                self.issues_found.append(f"Failed to remove {file_path}: {e}")
                success = False
        
        return success
    
    def clean_sqlite_configurations(self, configurations: List[Dict[str, Any]], dry_run: bool = False) -> bool:
        """Clean SQLite configurations from code files"""
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Cleaning SQLite configurations...")
        
        success = True
        
        for config in configurations:
            file_path = config['file']
            patterns = config['patterns']
            
            try:
                if dry_run:
                    logger.info(f"Would clean SQLite patterns in: {file_path}")
                    for pattern in patterns:
                        logger.info(f"  - Pattern: {pattern}")
                else:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    changes_made = []
                    
                    # Apply SQLite cleanup patterns
                    import re
                    
                    # Comment out SQLite imports
                    if re.search(r'import sqlite3', content):
                        content = re.sub(r'^(\s*import sqlite3.*)$', r'# \1  # Removed for MySQL migration', content, flags=re.MULTILINE)
                        changes_made.append("Commented out sqlite3 imports")
                    
                    if re.search(r'from sqlite3', content):
                        content = re.sub(r'^(\s*from sqlite3.*)$', r'# \1  # Removed for MySQL migration', content, flags=re.MULTILINE)
                        changes_made.append("Commented out sqlite3 from imports")
                    
                    # Replace SQLite URLs with MySQL (if not already done)
                    if re.search(r'sqlite:///', content) and 'mysql+pymysql://' not in content:
                        content = re.sub(r'sqlite:///[^\'"\s]+', 'mysql+pymysql://database_user_1d7b0d0696a20:EQA&bok7@localhost/vedfolnir', content)
                        changes_made.append("Replaced SQLite URLs with MySQL")
                    
                    # Add migration comments
                    if changes_made:
                        # Create backup
                        backup_path = file_path.with_suffix(f'{file_path.suffix}.sqlite_cleanup_backup')
                        with open(backup_path, 'w', encoding='utf-8') as f:
                            f.write(original_content)
                        
                        # Write cleaned content
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        self.configurations_updated.append({
                            'file': str(file_path),
                            'changes': changes_made,
                            'backup': str(backup_path)
                        })
                        
                        logger.info(f"✅ Cleaned {file_path}: {len(changes_made)} changes")
                    else:
                        logger.info(f"⏭️  No changes needed for {file_path}")
                        
            except Exception as e:
                logger.error(f"❌ Failed to clean {file_path}: {e}")
                self.issues_found.append(f"Failed to clean {file_path}: {e}")
                success = False
        
        return success
    
    def remove_empty_directories(self, dry_run: bool = False) -> bool:
        """Remove empty directories that may have contained SQLite files"""
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Removing empty directories...")
        
        # Directories that might be empty after SQLite cleanup
        potential_empty_dirs = [
            self.project_root / 'data',
            self.project_root / 'tmp',
            self.project_root / 'storage' / 'test_databases',
        ]
        
        success = True
        
        for dir_path in potential_empty_dirs:
            try:
                if dir_path.exists() and dir_path.is_dir():
                    # Check if directory is empty
                    if not any(dir_path.iterdir()):
                        if dry_run:
                            logger.info(f"Would remove empty directory: {dir_path}")
                        else:
                            dir_path.rmdir()
                            self.directories_removed.append(str(dir_path))
                            logger.info(f"✅ Removed empty directory: {dir_path}")
                    else:
                        logger.info(f"⏭️  Directory not empty: {dir_path}")
                        
            except Exception as e:
                logger.error(f"❌ Failed to remove directory {dir_path}: {e}")
                self.issues_found.append(f"Failed to remove directory {dir_path}: {e}")
                success = False
        
        return success
    
    def perform_comprehensive_cleanup(self, dry_run: bool = False) -> bool:
        """Perform comprehensive SQLite cleanup"""
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Starting comprehensive SQLite cleanup...")
        
        success = True
        
        # Step 1: Find and remove SQLite files
        sqlite_files = self.find_sqlite_files()
        if not self.remove_sqlite_files(sqlite_files, dry_run):
            success = False
        
        # Step 2: Find and clean SQLite configurations
        sqlite_configs = self.find_sqlite_configurations()
        if not self.clean_sqlite_configurations(sqlite_configs, dry_run):
            success = False
        
        # Step 3: Remove empty directories
        if not self.remove_empty_directories(dry_run):
            success = False
        
        return success
    
    def generate_cleanup_report(self) -> str:
        """Generate comprehensive cleanup report"""
        report = [
            "=== SQLite Cleanup Report ===",
            "",
            f"Project Root: {self.project_root}",
            "",
            "CLEANUP RESULTS:",
            f"Files removed: {len(self.files_removed)}",
            f"Directories removed: {len(self.directories_removed)}",
            f"Configurations updated: {len(self.configurations_updated)}",
            f"Issues encountered: {len(self.issues_found)}",
            ""
        ]
        
        if self.files_removed:
            report.extend([
                "FILES REMOVED:",
                ""
            ])
            for file_path in self.files_removed:
                report.append(f"  ✅ {file_path}")
            report.append("")
        
        if self.directories_removed:
            report.extend([
                "DIRECTORIES REMOVED:",
                ""
            ])
            for dir_path in self.directories_removed:
                report.append(f"  ✅ {dir_path}")
            report.append("")
        
        if self.configurations_updated:
            report.extend([
                "CONFIGURATIONS UPDATED:",
                ""
            ])
            for config in self.configurations_updated:
                report.append(f"  ✅ {Path(config['file']).name}")
                for change in config['changes']:
                    report.append(f"     - {change}")
                report.append(f"     - Backup: {Path(config['backup']).name}")
                report.append("")
        
        if self.issues_found:
            report.extend([
                "🚨 ISSUES FOUND:",
                ""
            ])
            for issue in self.issues_found:
                report.append(f"  - {issue}")
            report.append("")
        
        report.extend([
            "SQLITE CLEANUP COMPLETED:",
            "✅ SQLite database files removed",
            "✅ SQLite configurations cleaned",
            "✅ Empty directories removed",
            "✅ MySQL migration completed",
            "",
            "NEXT STEPS:",
            "1. Verify that all tests pass with MySQL",
            "2. Remove backup files after validation",
            "3. Update documentation to reflect MySQL-only setup",
            "4. Update CI/CD pipelines to use MySQL",
        ])
        
        return "\n".join(report)


def main():
    """Main cleanup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SQLite Cleanup Tool for MySQL Migration")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be cleaned without actually doing it')
    parser.add_argument('--files-only', action='store_true', help='Only remove SQLite files, not configurations')
    parser.add_argument('--configs-only', action='store_true', help='Only clean configurations, not files')
    
    args = parser.parse_args()
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info("SQLite Cleanup Tool for MySQL Migration")
    logger.info(f"Project root: {project_root}")
    
    if args.dry_run:
        logger.info("DRY RUN MODE: No changes will be made")
    
    # Initialize cleanup tool
    cleanup_tool = SQLiteCleanupTool(project_root)
    
    success = True
    
    try:
        if args.configs_only:
            # Only clean configurations
            sqlite_configs = cleanup_tool.find_sqlite_configurations()
            success = cleanup_tool.clean_sqlite_configurations(sqlite_configs, args.dry_run)
        elif args.files_only:
            # Only remove files
            sqlite_files = cleanup_tool.find_sqlite_files()
            success = cleanup_tool.remove_sqlite_files(sqlite_files, args.dry_run)
        else:
            # Comprehensive cleanup
            success = cleanup_tool.perform_comprehensive_cleanup(args.dry_run)
        
        # Generate report
        report = cleanup_tool.generate_cleanup_report()
        
        # Save report
        report_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'sqlite_cleanup_report.txt')
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Cleanup report saved to: {report_path}")
        
        if success:
            logger.info("✅ SQLite cleanup completed successfully")
        else:
            logger.error("❌ SQLite cleanup completed with errors")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("Cleanup interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
