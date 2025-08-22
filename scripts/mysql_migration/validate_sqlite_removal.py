#!/usr/bin/env python3
"""
SQLite Removal Validation Script

Validates that SQLite imports and dependencies have been properly removed from the codebase.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLiteRemovalValidator:
    """Validates that SQLite references have been removed"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.violations = []
        self.files_checked = 0
        
        # Patterns that should not exist after SQLite removal
        self.forbidden_patterns = [
            (r'import sqlite3', 'Direct sqlite3 import'),
            (r'from sqlite3', 'sqlite3 module import'),
            (r'sqlite3\.', 'sqlite3 module usage'),
            (r'SELECT name FROM sqlite_master', 'SQLite system table query'),
            (r'PRAGMA table_info', 'SQLite PRAGMA statement'),
            (r'PRAGMA foreign_keys', 'SQLite PRAGMA statement'),
            (r'sqlite:///.*\.db', 'SQLite database URL'),
            (r'\.db["\']?\s*$', 'SQLite database file reference'),
        ]
        
        # Files to skip (migration scripts, documentation, etc.)
        self.skip_files = {
            'validate_sqlite_removal.py',
            'remove_sqlite_references.py',
            'sqlite_removal_report.txt',
            'migrate_to_mysql.py',
            'task4-completion-summary.md',
            'README.md',
            'CHANGELOG.md',
        }
        
        # Directories to skip
        self.skip_dirs = {
            '__pycache__',
            '.git',
            'node_modules',
            '.pytest_cache',
        }
    
    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        return (
            file_path.name in self.skip_files or
            file_path.suffix not in ['.py', '.md', '.txt', '.yml', '.yaml'] or
            any(skip_dir in str(file_path) for skip_dir in self.skip_dirs)
        )
    
    def check_file(self, file_path: Path) -> List[Dict]:
        """Check a single file for SQLite references"""
        if self.should_skip_file(file_path):
            return []
        
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for pattern, description in self.forbidden_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': pattern,
                            'description': description
                        })
            
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
        
        return violations
    
    def check_requirements_file(self) -> List[Dict]:
        """Check requirements.txt for SQLite dependencies"""
        violations = []
        requirements_file = self.project_root / 'requirements.txt'
        
        if requirements_file.exists():
            try:
                with open(requirements_file, 'r') as f:
                    content = f.read()
                
                sqlite_deps = ['sqlite', 'sqlite3', 'pysqlite']
                
                for line_num, line in enumerate(content.split('\n'), 1):
                    line = line.strip().lower()
                    for dep in sqlite_deps:
                        if dep in line and not line.startswith('#'):
                            violations.append({
                                'file': str(requirements_file),
                                'line': line_num,
                                'content': line,
                                'pattern': dep,
                                'description': 'SQLite dependency in requirements'
                            })
            except Exception as e:
                logger.warning(f"Could not read requirements.txt: {e}")
        
        return violations
    
    def validate_project(self) -> Dict[str, any]:
        """Validate the entire project for SQLite removal"""
        logger.info("Starting SQLite removal validation...")
        
        all_violations = []
        
        # Check all Python files
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file():
                self.files_checked += 1
                violations = self.check_file(file_path)
                all_violations.extend(violations)
        
        # Check requirements.txt specifically
        req_violations = self.check_requirements_file()
        all_violations.extend(req_violations)
        
        self.violations = all_violations
        
        return {
            'files_checked': self.files_checked,
            'violations_found': len(all_violations),
            'violations': all_violations,
            'is_clean': len(all_violations) == 0
        }
    
    def generate_report(self, results: Dict) -> str:
        """Generate validation report"""
        report = [
            "=== SQLite Removal Validation Report ===",
            f"Files checked: {results['files_checked']}",
            f"Violations found: {results['violations_found']}",
            ""
        ]
        
        if results['is_clean']:
            report.extend([
                "✅ SUCCESS: No SQLite references found!",
                "The codebase has been successfully cleaned of SQLite dependencies.",
                ""
            ])
        else:
            report.extend([
                "❌ VIOLATIONS FOUND:",
                "The following SQLite references still exist and need to be addressed:",
                ""
            ])
            
            # Group violations by file
            violations_by_file = {}
            for violation in results['violations']:
                file_path = violation['file']
                if file_path not in violations_by_file:
                    violations_by_file[file_path] = []
                violations_by_file[file_path].append(violation)
            
            for file_path, file_violations in violations_by_file.items():
                report.append(f"📁 {file_path}")
                for violation in file_violations:
                    report.append(f"  Line {violation['line']}: {violation['description']}")
                    report.append(f"    Content: {violation['content']}")
                    report.append(f"    Pattern: {violation['pattern']}")
                report.append("")
        
        report.extend([
            "=== Validation Summary ===",
            f"Total files processed: {results['files_checked']}",
            f"SQLite violations: {results['violations_found']}",
            f"Status: {'CLEAN' if results['is_clean'] else 'NEEDS ATTENTION'}",
        ])
        
        return "\n".join(report)


def main():
    """Main validation function"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info(f"Validating SQLite removal in: {project_root}")
    
    validator = SQLiteRemovalValidator(project_root)
    results = validator.validate_project()
    
    # Generate report
    report = validator.generate_report(results)
    
    # Save report
    report_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'sqlite_removal_validation_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    
    # Print summary
    logger.info(f"Validation completed: {results['files_checked']} files checked")
    logger.info(f"Violations found: {results['violations_found']}")
    logger.info(f"Report saved to: {report_path}")
    
    if results['is_clean']:
        logger.info("✅ SUCCESS: No SQLite references found!")
        return True
    else:
        logger.error("❌ VIOLATIONS: SQLite references still exist")
        logger.error("Check the validation report for details")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
