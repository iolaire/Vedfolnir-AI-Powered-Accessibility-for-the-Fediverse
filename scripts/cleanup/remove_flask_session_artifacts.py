#!/usr/bin/env python3
"""
Remove Flask Session Artifacts - Task 20

This script removes all deprecated Flask session code and artifacts from the codebase
as part of the session consolidation cleanup.
"""

import os
import sys
import shutil
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def remove_deprecated_files():
    """Remove deprecated Flask session files"""
    
    files_to_remove = [
        # Migration scripts (no longer needed)
        "migrate_to_flask_sessions.py",
        
        # Test files for deprecated functionality
        "tests/integration/test_flask_sessions.py",
        
        # Documentation for deprecated system
        "docs/session-management-api.md",
        "docs/session-management-examples.md", 
        "docs/session-management-troubleshooting.md",
        "docs/summary/FLASK_SESSION_MIGRATION.md",
        
        # Generated API docs for deprecated components
        "docs/api/generated/flask_session_manager.md",
        "docs/api/generated/migrate_to_flask_sessions.md",
        "docs/api/generated/test_flask_sessions.md",
    ]
    
    removed_files = []
    
    for file_path in files_to_remove:
        full_path = project_root / file_path
        if full_path.exists():
            try:
                full_path.unlink()
                removed_files.append(file_path)
                print(f"✓ Removed: {file_path}")
            except Exception as e:
                print(f"✗ Failed to remove {file_path}: {e}")
        else:
            print(f"- Not found: {file_path}")
    
    return removed_files

def clean_flask_session_references():
    """Remove Flask session references from remaining files"""
    
    files_to_clean = [
        "unified_session_manager.py",
        "tests/integration/test_session_management_e2e.py",
        "tests/test_dashboard_session_management.py",
        "tests/test_session_decorators_integration.py",
        "scripts/deployment/session_management_deployment_checklist.py",
    ]
    
    cleaned_files = []
    
    for file_path in files_to_clean:
        full_path = project_root / file_path
        if full_path.exists():
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Remove Flask session imports and references
                lines = content.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    # Skip lines with Flask session manager imports
                    if any(term in line for term in [
                        'from flask_session_manager import',
                        'import flask_session_manager',
                        'FlaskSessionManager',
                        'FlaskPlatformContextMiddleware'
                    ]):
                        continue
                    
                    # Skip comments about Flask session manager
                    if 'flask_session_manager' in line.lower() and line.strip().startswith('#'):
                        continue
                    
                    cleaned_lines.append(line)
                
                # Write back if changes were made
                new_content = '\n'.join(cleaned_lines)
                if new_content != content:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    cleaned_files.append(file_path)
                    print(f"✓ Cleaned references in: {file_path}")
                
            except Exception as e:
                print(f"✗ Failed to clean {file_path}: {e}")
    
    return cleaned_files

def update_documentation_references():
    """Update documentation to remove references to deprecated Flask session system"""
    
    # Update README.md to remove legacy documentation references
    readme_path = project_root / "README.md"
    if readme_path.exists():
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove legacy documentation links
            legacy_docs = [
                "- [**Legacy Session API**](docs/session-management-api.md) - Deprecated dual-session system API",
                "- [**Legacy Session Examples**](docs/session-management-examples.md) - Deprecated session examples", 
                "- [**Legacy Session Troubleshooting**](docs/session-management-troubleshooting.md) - Deprecated troubleshooting guide"
            ]
            
            for legacy_doc in legacy_docs:
                content = content.replace(legacy_doc + '\n', '')
            
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✓ Updated README.md to remove legacy documentation references")
            
        except Exception as e:
            print(f"✗ Failed to update README.md: {e}")

def clean_generated_api_docs():
    """Clean up generated API documentation index"""
    
    index_path = project_root / "docs/api/generated/index.md"
    if index_path.exists():
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove references to deprecated Flask session manager
            lines = content.split('\n')
            cleaned_lines = []
            
            for line in lines:
                if 'flask_session_manager.md' in line:
                    continue
                if 'migrate_to_flask_sessions.md' in line:
                    continue
                if 'test_flask_sessions.md' in line:
                    continue
                cleaned_lines.append(line)
            
            new_content = '\n'.join(cleaned_lines)
            if new_content != content:
                with open(index_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print("✓ Cleaned generated API documentation index")
            
        except Exception as e:
            print(f"✗ Failed to clean API docs index: {e}")

def main():
    """Main cleanup function"""
    
    print("Starting Flask session artifacts cleanup (Task 20)...")
    print("=" * 60)
    
    # Remove deprecated files
    print("\n1. Removing deprecated files...")
    removed_files = remove_deprecated_files()
    
    # Clean Flask session references
    print("\n2. Cleaning Flask session references...")
    cleaned_files = clean_flask_session_references()
    
    # Update documentation
    print("\n3. Updating documentation...")
    update_documentation_references()
    
    # Clean generated API docs
    print("\n4. Cleaning generated API documentation...")
    clean_generated_api_docs()
    
    # Summary
    print("\n" + "=" * 60)
    print("Flask session artifacts cleanup completed!")
    print(f"Files removed: {len(removed_files)}")
    print(f"Files cleaned: {len(cleaned_files)}")
    
    if removed_files:
        print("\nRemoved files:")
        for file_path in removed_files:
            print(f"  - {file_path}")
    
    if cleaned_files:
        print("\nCleaned files:")
        for file_path in cleaned_files:
            print(f"  - {file_path}")
    
    print("\nTask 20 cleanup completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())