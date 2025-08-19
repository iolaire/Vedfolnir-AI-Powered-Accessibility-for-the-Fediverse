#!/usr/bin/env python3
"""
Update remaining database_session_middleware imports to redis_session_middleware

This script updates the remaining files that import from database_session_middleware
to use the new redis_session_middleware instead.
"""

import os
import re
from pathlib import Path

def update_file_imports(file_path):
    """Update imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace specific import patterns
        replacements = [
            # Basic imports
            (r'from database_session_middleware import DatabaseSessionMiddleware', 
             'from redis_session_middleware import get_current_session_context, get_current_session_id'),
            (r'from database_session_middleware import get_current_session_context', 
             'from redis_session_middleware import get_current_session_context'),
            (r'from database_session_middleware import get_current_session_id', 
             'from redis_session_middleware import get_current_session_id'),
            (r'from database_session_middleware import get_current_user_id', 
             'from redis_session_middleware import get_current_user_id'),
            (r'from database_session_middleware import get_current_platform_id', 
             'from redis_session_middleware import get_current_platform_id'),
            (r'from database_session_middleware import is_session_authenticated', 
             'from redis_session_middleware import validate_current_session as is_session_authenticated'),
            (r'from database_session_middleware import update_session_platform', 
             'from redis_session_middleware import update_session_platform'),
            (r'from database_session_middleware import clear_session_platform', 
             'from redis_session_middleware import clear_session_platform'),
            
            # Multi-line imports
            (r'from database_session_middleware import \(\s*get_current_session_context,\s*get_current_session_id,\s*is_session_authenticated\s*\)', 
             'from redis_session_middleware import get_current_session_context, get_current_session_id, validate_current_session as is_session_authenticated'),
            (r'from database_session_middleware import \(\s*get_current_session_context,\s*get_current_user_id,\s*get_current_platform_id,\s*is_session_authenticated\s*\)', 
             'from redis_session_middleware import get_current_session_context, get_current_user_id, get_current_platform_id, validate_current_session as is_session_authenticated'),
            
            # Comments
            (r'# .*database session middleware', '# Redis session middleware'),
            (r'# .*database session', '# Redis session'),
            (r'database session middleware', 'Redis session middleware'),
            (r'database session', 'Redis session'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.IGNORECASE)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
        else:
            print(f"No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Update all remaining files"""
    
    # Files that still need updating (from the grep output)
    files_to_update = [
        "tests/test_session_consolidation_minimal.py",
        "tests/test_database_session_middleware.py", 
        "tests/test_session_consolidation_final_e2e.py",
        "tests/test_session_consolidation_integration.py",
        "scripts/testing/validate_session_migration.py",
        "scripts/testing/validate_session_consolidation.py"
    ]
    
    updated_count = 0
    
    for file_path in files_to_update:
        full_path = Path(file_path)
        if full_path.exists():
            if update_file_imports(full_path):
                updated_count += 1
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nUpdated {updated_count} files")

if __name__ == "__main__":
    main()
