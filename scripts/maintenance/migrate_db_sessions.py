#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Script to migrate db_manager.get_session() usage to unified session patterns
"""

import os
import re
import glob
import argparse
from pathlib import Path

def migrate_web_app_routes(file_path, dry_run=False):
    """Migrate web app routes to use unified_session_manager"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_content = content
    changes_made = False
    
    # Pattern 1: Simple session = db_manager.get_session() with try/finally
    pattern1 = re.compile(
        r'(\s+)session = db_manager\.get_session\(\)\s*\n'
        r'(\s+)try:\s*\n'
        r'(.*?)'
        r'(\s+)finally:\s*\n'
        r'(\s+)session\.close\(\)',
        re.DOTALL
    )
    
    def replace_pattern1(match):
        indent = match.group(1)
        try_content = match.group(3)
        
        # Replace with unified session manager pattern
        replacement = f'{indent}with unified_session_manager.get_db_session() as session:\n{try_content.rstrip()}'
        return replacement
    
    new_content = pattern1.sub(replace_pattern1, content)
    if new_content != content:
        content = new_content
        changes_made = True
    
    # Pattern 2: db_session = db_manager.get_session() with try/finally
    pattern2 = re.compile(
        r'(\s+)db_session = db_manager\.get_session\(\)\s*\n'
        r'(\s+)try:\s*\n'
        r'(.*?)'
        r'(\s+)finally:\s*\n'
        r'(\s+)db_session\.close\(\)',
        re.DOTALL
    )
    
    def replace_pattern2(match):
        indent = match.group(1)
        try_content = match.group(3)
        
        # Replace session variable name in content
        try_content = try_content.replace('db_session', 'session')
        
        replacement = f'{indent}with unified_session_manager.get_db_session() as session:\n{try_content.rstrip()}'
        return replacement
    
    new_content = pattern2.sub(replace_pattern2, content)
    if new_content != content:
        content = new_content
        changes_made = True
    
    if changes_made:
        if not dry_run:
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✓ Migrated web app route patterns in: {file_path}")
            except Exception as e:
                print(f"✗ Error writing {file_path}: {e}")
                return False
        else:
            print(f"[DRY RUN] Would migrate web app route patterns in: {file_path}")
        return True
    
    return False

def migrate_admin_services(file_path, dry_run=False):
    """Migrate admin services to use appropriate session patterns"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_content = content
    changes_made = False
    
    # Check if this is a service class file
    if 'class ' in content and 'Service' in content:
        # Add unified session manager property if not exists
        if 'unified_session_manager' not in content:
            # Find the __init__ method
            init_pattern = re.compile(r'(class \w+Service:.*?def __init__\(self[^)]*\):.*?\n)', re.DOTALL)
            
            def add_session_manager_property(match):
                init_method = match.group(1)
                property_code = '''        # Add unified session manager reference
        self._unified_session_manager = None
    
    @property
    def unified_session_manager(self):
        if self._unified_session_manager is None:
            try:
                from flask import current_app
                self._unified_session_manager = getattr(current_app, 'unified_session_manager', None)
            except RuntimeError:
                # Outside Flask context
                pass
        return self._unified_session_manager
    
'''
                return init_method + property_code
            
            new_content = init_pattern.sub(add_session_manager_property, content)
            if new_content != content:
                content = new_content
                changes_made = True
    
    # Pattern: session = self.db_manager.get_session() with try/finally
    pattern = re.compile(
        r'(\s+)session = self\.db_manager\.get_session\(\)\s*\n'
        r'(\s+)try:\s*\n'
        r'(.*?)'
        r'(\s+)finally:\s*\n'
        r'(\s+)session\.close\(\)',
        re.DOTALL
    )
    
    def replace_service_pattern(match):
        indent = match.group(1)
        try_content = match.group(3)
        
        replacement = f'''{indent}if self.unified_session_manager:
{indent}    with self.unified_session_manager.get_db_session() as session:
{try_content.rstrip()}
{indent}else:
{indent}    # Fallback for non-Flask contexts
{indent}    session = self.db_manager.get_session()
{indent}    try:
{try_content.rstrip()}
{indent}    finally:
{indent}        session.close()'''
        
        return replacement
    
    new_content = pattern.sub(replace_service_pattern, content)
    if new_content != content:
        content = new_content
        changes_made = True
    
    if changes_made:
        if not dry_run:
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✓ Migrated admin service patterns in: {file_path}")
            except Exception as e:
                print(f"✗ Error writing {file_path}: {e}")
                return False
        else:
            print(f"[DRY RUN] Would migrate admin service patterns in: {file_path}")
        return True
    
    return False

def migrate_admin_routes(file_path, dry_run=False):
    """Migrate admin routes to use unified session manager"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_content = content
    changes_made = False
    
    # Add import if not exists
    if 'from flask import current_app' not in content and '@admin_bp.route' in content:
        # Find the imports section
        import_pattern = re.compile(r'(from flask import [^\n]+)')
        
        def add_current_app_import(match):
            existing_import = match.group(1)
            if 'current_app' not in existing_import:
                return existing_import.replace('from flask import ', 'from flask import current_app, ')
            return existing_import
        
        new_content = import_pattern.sub(add_current_app_import, content)
        if new_content != content:
            content = new_content
            changes_made = True
    
    # Pattern: session = db_manager.get_session() in admin routes
    pattern = re.compile(
        r'(\s+)session = db_manager\.get_session\(\)\s*\n'
        r'(\s+)try:\s*\n'
        r'(.*?)'
        r'(\s+)finally:\s*\n'
        r'(\s+)session\.close\(\)',
        re.DOTALL
    )
    
    def replace_admin_route_pattern(match):
        indent = match.group(1)
        try_content = match.group(3)
        
        replacement = f'''{indent}unified_session_manager = current_app.unified_session_manager
{indent}with unified_session_manager.get_db_session() as session:
{try_content.rstrip()}'''
        
        return replacement
    
    new_content = pattern.sub(replace_admin_route_pattern, content)
    if new_content != content:
        content = new_content
        changes_made = True
    
    if changes_made:
        if not dry_run:
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✓ Migrated admin route patterns in: {file_path}")
            except Exception as e:
                print(f"✗ Error writing {file_path}: {e}")
                return False
        else:
            print(f"[DRY RUN] Would migrate admin route patterns in: {file_path}")
        return True
    
    return False

def find_files_with_db_manager_usage():
    """Find all files that use db_manager.get_session()"""
    files_to_migrate = {
        'web_app': [],
        'admin_services': [],
        'admin_routes': [],
        'other': []
    }
    
    # Web app files
    if os.path.exists('web_app.py'):
        with open('web_app.py', 'r') as f:
            if 'db_manager.get_session()' in f.read():
                files_to_migrate['web_app'].append('web_app.py')
    
    # Admin service files
    admin_service_files = glob.glob('admin/services/*.py')
    for file_path in admin_service_files:
        try:
            with open(file_path, 'r') as f:
                if 'db_manager.get_session()' in f.read():
                    files_to_migrate['admin_services'].append(file_path)
        except Exception:
            continue
    
    # Admin route files
    admin_route_files = glob.glob('admin/routes/*.py')
    for file_path in admin_route_files:
        try:
            with open(file_path, 'r') as f:
                if 'db_manager.get_session()' in f.read():
                    files_to_migrate['admin_routes'].append(file_path)
        except Exception:
            continue
    
    # Other files
    other_files = glob.glob('*.py')
    for file_path in other_files:
        if file_path not in ['web_app.py'] and not file_path.startswith('admin/'):
            try:
                with open(file_path, 'r') as f:
                    if 'db_manager.get_session()' in f.read():
                        files_to_migrate['other'].append(file_path)
            except Exception:
                continue
    
    return files_to_migrate

def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Migrate db_manager.get_session() usage to unified patterns')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--file', help='Migrate a specific file')
    parser.add_argument('--type', choices=['web_app', 'admin_services', 'admin_routes', 'all'], 
                       default='all', help='Type of files to migrate')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.file:
        # Migrate specific file
        if 'admin/services/' in args.file:
            success = migrate_admin_services(args.file, dry_run=args.dry_run)
        elif 'admin/routes/' in args.file:
            success = migrate_admin_routes(args.file, dry_run=args.dry_run)
        elif args.file == 'web_app.py':
            success = migrate_web_app_routes(args.file, dry_run=args.dry_run)
        else:
            print(f"Unknown file type: {args.file}")
            return
        
        if success:
            print(f"Successfully migrated {args.file}")
        else:
            print(f"No changes needed for {args.file}")
        return
    
    # Find all files that need migration
    files_to_migrate = find_files_with_db_manager_usage()
    
    if args.verbose:
        print("Files found for migration:")
        for category, files in files_to_migrate.items():
            if files:
                print(f"  {category}: {files}")
    
    total_migrated = 0
    
    # Migrate based on type
    if args.type in ['web_app', 'all']:
        for file_path in files_to_migrate['web_app']:
            if migrate_web_app_routes(file_path, dry_run=args.dry_run):
                total_migrated += 1
    
    if args.type in ['admin_services', 'all']:
        for file_path in files_to_migrate['admin_services']:
            if migrate_admin_services(file_path, dry_run=args.dry_run):
                total_migrated += 1
    
    if args.type in ['admin_routes', 'all']:
        for file_path in files_to_migrate['admin_routes']:
            if migrate_admin_routes(file_path, dry_run=args.dry_run):
                total_migrated += 1
    
    print(f"\nMigration complete. {total_migrated} files {'would be ' if args.dry_run else ''}updated.")
    
    if not args.dry_run and total_migrated > 0:
        print("\nNext steps:")
        print("1. Run tests to verify migration: python -m unittest discover tests -v")
        print("2. Run validation script: python scripts/testing/validate_db_session_migration.py")
        print("3. Test web application functionality")
        print("4. Test admin functionality")

if __name__ == '__main__':
    main()
