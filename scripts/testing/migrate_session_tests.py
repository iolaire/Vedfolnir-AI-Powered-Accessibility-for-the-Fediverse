#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Script to migrate test files from legacy session_manager to unified_session_manager
"""

import os
import re
import glob
import argparse
from pathlib import Path

def migrate_test_file(file_path, dry_run=False):
    """Migrate a single test file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_content = content
    changes_made = False
    
    # Replace imports
    import_replacements = [
        (r'from app.core.session.core.session_manager import SessionManager', 'from unified_session_manager import UnifiedSessionManager as SessionManager'),
        (r'from session_manager import get_current_platform_context', 'from unified_session_manager import get_current_platform_context'),
        (r'from session_manager import (.*)', r'from unified_session_manager import \1'),
        (r'import session_manager', 'import unified_session_manager as session_manager'),
    ]
    
    for old_pattern, new_pattern in import_replacements:
        if re.search(old_pattern, content):
            content = re.sub(old_pattern, new_pattern, content)
            changes_made = True
    
    # Replace class references (but not in import statements)
    # Look for SessionManager that's not part of an import
    lines = content.split('\n')
    updated_lines = []
    
    for line in lines:
        # Skip import lines
        if 'import' in line and 'SessionManager' in line:
            updated_lines.append(line)
            continue
            
        # Replace SessionManager with UnifiedSessionManager in other contexts
        if 'SessionManager' in line and 'UnifiedSessionManager' not in line:
            # Replace SessionManager instantiation
            line = re.sub(r'\bSessionManager\(', 'UnifiedSessionManager(', line)
            # Replace type hints
            line = re.sub(r': SessionManager', ': UnifiedSessionManager', line)
            # Replace variable assignments
            line = re.sub(r'= SessionManager', '= UnifiedSessionManager', line)
            changes_made = True
        
        updated_lines.append(line)
    
    content = '\n'.join(updated_lines)
    
    if changes_made:
        if not dry_run:
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✓ Migrated: {file_path}")
            except Exception as e:
                print(f"✗ Error writing {file_path}: {e}")
                return False
        else:
            print(f"[DRY RUN] Would migrate: {file_path}")
        return True
    
    return False

def find_test_files():
    """Find all test files that might need migration"""
    patterns = [
        'tests/**/*.py',
        'scripts/**/*.py',
        'security/**/*.py'
    ]
    
    all_files = []
    for pattern in patterns:
        all_files.extend(glob.glob(pattern, recursive=True))
    
    # Filter out files that shouldn't be migrated
    exclude_patterns = [
        '__pycache__',
        '.pyc',
        'unified_session_manager.py',
        'session_manager_compat.py',
        'migrate_session_tests.py'  # Don't migrate this script itself
    ]
    
    filtered_files = []
    for file_path in all_files:
        if not any(exclude in file_path for exclude in exclude_patterns):
            # Check if file actually imports session_manager
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if 'session_manager' in content and 'unified_session_manager' not in content:
                        filtered_files.append(file_path)
            except Exception:
                continue
    
    return filtered_files

def main():
    """Migrate all test files"""
    parser = argparse.ArgumentParser(description='Migrate test files to use unified_session_manager')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--file', help='Migrate a specific file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.file:
        files_to_migrate = [args.file]
    else:
        files_to_migrate = find_test_files()
    
    if not files_to_migrate:
        print("No files found that need migration.")
        return
    
    print(f"Found {len(files_to_migrate)} files to migrate:")
    if args.verbose:
        for file_path in files_to_migrate:
            print(f"  - {file_path}")
    
    if args.dry_run:
        print("\n--- DRY RUN MODE ---")
    
    migrated_count = 0
    for file_path in files_to_migrate:
        if migrate_test_file(file_path, dry_run=args.dry_run):
            migrated_count += 1
    
    print(f"\nMigration complete. {migrated_count} files {'would be ' if args.dry_run else ''}updated.")
    
    if not args.dry_run and migrated_count > 0:
        print("\nNext steps:")
        print("1. Run tests to verify migration: python -m unittest discover tests -v")
        print("2. Check for any remaining issues: grep -r 'from session_manager import' .")
        print("3. Update any remaining manual references")

if __name__ == '__main__':
    main()
