#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Script to update all remaining session_manager imports to unified_session_manager
"""

import os
import re
import glob
import argparse
from pathlib import Path

def update_imports_in_file(file_path, dry_run=False):
    """Update imports in a single file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_content = content
    
    # Update import statements
    patterns = [
        # Direct imports
        (r'from session_manager import SessionManager', 'from unified_session_manager import UnifiedSessionManager'),
        (r'from session_manager import get_current_platform_context', 'from unified_session_manager import get_current_platform_context'),
        (r'from session_manager import get_current_platform', 'from unified_session_manager import get_current_platform'),
        (r'from session_manager import get_current_user_from_context', 'from unified_session_manager import get_current_user_from_context'),
        (r'from session_manager import switch_platform_context', 'from unified_session_manager import switch_platform_context'),
        
        # Wildcard imports
        (r'from session_manager import \*', 'from unified_session_manager import *'),
        
        # Module imports
        (r'import session_manager', 'import unified_session_manager as session_manager'),
        
        # Multi-line imports
        (r'from session_manager import \((.*?)\)', r'from unified_session_manager import (\1)', re.DOTALL),
    ]
    
    for old_pattern, new_pattern, *flags in patterns:
        flag = flags[0] if flags else 0
        if re.search(old_pattern, content, flag):
            content = re.sub(old_pattern, new_pattern, content, flags=flag)
    
    # Update class references in type hints and instantiation
    # But be careful not to change import statements we just updated
    lines = content.split('\n')
    updated_lines = []
    
    for line in lines:
        # Skip lines that are import statements for unified_session_manager
        if 'from unified_session_manager import' in line or 'import unified_session_manager' in line:
            updated_lines.append(line)
            continue
        
        # Update SessionManager references
        if 'SessionManager' in line and 'UnifiedSessionManager' not in line:
            # Type hints
            line = re.sub(r': SessionManager\b', ': UnifiedSessionManager', line)
            # Function parameters
            line = re.sub(r'session_manager: SessionManager', 'session_manager: UnifiedSessionManager', line)
            # Instantiation
            line = re.sub(r'= SessionManager\(', '= UnifiedSessionManager(', line)
            # Class inheritance (rare but possible)
            line = re.sub(r'class.*\(SessionManager\)', lambda m: m.group(0).replace('SessionManager', 'UnifiedSessionManager'), line)
        
        updated_lines.append(line)
    
    content = '\n'.join(updated_lines)
    
    if content != original_content:
        if not dry_run:
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✓ Updated: {file_path}")
            except Exception as e:
                print(f"✗ Error writing {file_path}: {e}")
                return False
        else:
            print(f"[DRY RUN] Would update: {file_path}")
        return True
    
    return False

def find_python_files():
    """Find all Python files that might need updating"""
    # Find all Python files
    python_files = []
    for pattern in ['*.py', '**/*.py']:
        python_files.extend(glob.glob(pattern, recursive=True))
    
    # Exclude certain files and directories
    exclude_patterns = [
        '__pycache__',
        '.pyc',
        '.git',
        'venv',
        'env',
        'node_modules',
        'unified_session_manager.py',
        'session_manager_compat.py',
        'update_session_imports.py',  # Don't update this script itself
        'migrate_session_tests.py'
    ]
    
    filtered_files = []
    for file_path in python_files:
        if not any(exclude in file_path for exclude in exclude_patterns):
            # Check if file actually imports session_manager
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    # Look for session_manager imports that aren't already unified
                    if ('from session_manager import' in content or 'import session_manager' in content) and \
                       'unified_session_manager' not in content:
                        filtered_files.append(file_path)
            except Exception:
                continue
    
    return filtered_files

def validate_migration():
    """Validate that migration was successful"""
    print("\nValidating migration...")
    
    # Find any remaining legacy imports
    python_files = glob.glob('**/*.py', recursive=True)
    legacy_files = []
    
    exclude_patterns = ['__pycache__', '.git', 'venv', 'env', 'session_manager.py']
    
    for file_path in python_files:
        if any(exclude in file_path for exclude in exclude_patterns):
            continue
            
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Check for legacy imports
            if ('from session_manager import' in content or 'import session_manager' in content) and \
               'unified_session_manager' not in content:
                legacy_files.append(file_path)
        except Exception:
            continue
    
    if legacy_files:
        print(f"⚠️  Found {len(legacy_files)} files with remaining legacy imports:")
        for file_path in legacy_files:
            print(f"   - {file_path}")
        return False
    else:
        print("✅ No legacy imports found. Migration appears successful!")
        return True

def main():
    """Update all Python files"""
    parser = argparse.ArgumentParser(description='Update session_manager imports to unified_session_manager')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--file', help='Update a specific file')
    parser.add_argument('--validate', action='store_true', help='Only validate migration (check for remaining legacy imports)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.validate:
        validate_migration()
        return
    
    if args.file:
        files_to_update = [args.file]
    else:
        files_to_update = find_python_files()
    
    if not files_to_update:
        print("No files found that need updating.")
        validate_migration()
        return
    
    print(f"Found {len(files_to_update)} files to update:")
    if args.verbose:
        for file_path in files_to_update:
            print(f"  - {file_path}")
    
    if args.dry_run:
        print("\n--- DRY RUN MODE ---")
    
    updated_count = 0
    for file_path in files_to_update:
        if update_imports_in_file(file_path, dry_run=args.dry_run):
            updated_count += 1
    
    print(f"\nImport update complete. {updated_count} files {'would be ' if args.dry_run else ''}updated.")
    
    if not args.dry_run:
        # Validate the migration
        validate_migration()
        
        if updated_count > 0:
            print("\nNext steps:")
            print("1. Run tests to verify imports work: python -m unittest discover tests -v")
            print("2. Check for any syntax errors: python -m py_compile <updated_files>")
            print("3. Review changes and commit if successful")

if __name__ == '__main__':
    main()
