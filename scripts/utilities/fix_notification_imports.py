#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Fix Notification Flash Replacement Imports

This script removes all imports of the notification_flash_replacement module
and replaces send_notification calls with TODO comments.
"""

import re
import os
from pathlib import Path

def fix_imports_in_file(file_path: Path) -> bool:
    """Fix notification imports in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace the import statement
        content = re.sub(
            r'# from notification_flash_replacement import send_notification  # Removed - using unified notification system',
            '# # from notification_flash_replacement import send_notification  # Removed - using unified notification system  # Removed - using unified notification system',
            content
        )
        
        # Replace send_notification calls with TODO comments
        send_notification_patterns = [
            # Basic patterns
            (r"send_notification\('([^']+)',\s*'([^']+)'\)", r"# TODO: Replace with unified notification: \1 (\2)"),
            (r'send_notification\("([^"]+)",\s*"([^"]+)"\)', r'# TODO: Replace with unified notification: \1 (\2)'),
            
            # Patterns with third parameter
            (r"send_notification\('([^']+)',\s*'([^']+)',\s*'([^']+)'\)", r"# TODO: Replace with unified notification: \1 (\2) - \3"),
            (r'send_notification\("([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\)', r'# TODO: Replace with unified notification: \1 (\2) - \3'),
            
            # Multi-line patterns
            (r'send_notification\(\s*message=([^,]+),\s*category=([^,)]+)\s*\)', r'# TODO: Replace with unified notification: message=\1, category=\2'),
        ]
        
        for pattern, replacement in send_notification_patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed notification imports in {file_path}")
            return True
        else:
            print(f"ℹ️  No notification imports found in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {str(e)}")
        return False

def find_files_with_notification_imports(root_dir: Path) -> list:
    """Find all files that import notification_flash_replacement"""
    files_with_imports = []
    
    for file_path in root_dir.rglob('*.py'):
        if any(exclude in str(file_path) for exclude in ['.git', '__pycache__', '.backup']):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'from notification_flash_replacement import' in content:
                files_with_imports.append(file_path)
                
        except (UnicodeDecodeError, PermissionError):
            continue
    
    return files_with_imports

def main():
    """Main execution function"""
    print("🔧 Fixing notification_flash_replacement imports...")
    
    root_dir = Path('.')
    files_with_imports = find_files_with_notification_imports(root_dir)
    
    print(f"Found {len(files_with_imports)} files with notification imports:")
    for file_path in files_with_imports:
        print(f"  - {file_path}")
    
    fixed_files = []
    
    for file_path in files_with_imports:
        if fix_imports_in_file(file_path):
            fixed_files.append(file_path)
    
    print(f"\n📊 Summary:")
    print(f"  - Files found: {len(files_with_imports)}")
    print(f"  - Files fixed: {len(fixed_files)}")
    
    if fixed_files:
        print("\n✅ All notification import fixes completed!")
    else:
        print("\n✅ No notification imports found to fix.")

if __name__ == "__main__":
    main()