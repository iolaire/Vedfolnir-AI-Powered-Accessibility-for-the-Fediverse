#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Fix Indentation Issues After Flash Message Replacement

This script fixes indentation issues that occurred after replacing flash messages
with TODO comments.
"""

import re
from pathlib import Path

def fix_indentation_in_file(file_path: Path) -> bool:
    """Fix indentation issues in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.split('\n')
        fixed_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this line has a TODO comment that needs a pass statement
            if '# TODO: Replace with unified notification:' in line:
                fixed_lines.append(line)
                
                # Check if the next line is indented properly or if we need to add pass
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    current_indent = len(line) - len(line.lstrip())
                    
                    # If next line is not indented more than current or is empty/comment, add pass
                    if (not next_line.strip() or 
                        len(next_line) - len(next_line.lstrip()) <= current_indent or
                        next_line.strip().startswith('#') or
                        next_line.strip().startswith('return') or
                        next_line.strip().startswith('except') or
                        next_line.strip().startswith('else:') or
                        next_line.strip().startswith('elif')):
                        
                        # Add pass statement with proper indentation
                        pass_indent = ' ' * (current_indent + 4)
                        fixed_lines.append(f"{pass_indent}pass")
                else:
                    # This is the last line, add pass
                    current_indent = len(line) - len(line.lstrip())
                    pass_indent = ' ' * (current_indent + 4)
                    fixed_lines.append(f"{pass_indent}pass")
            else:
                fixed_lines.append(line)
            
            i += 1
        
        new_content = '\n'.join(fixed_lines)
        
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Fixed indentation issues in {file_path}")
            return True
        else:
            print(f"ℹ️  No indentation issues found in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {str(e)}")
        return False

def main():
    """Main execution function"""
    print("🔧 Fixing indentation issues after flash message replacement...")
    
    # Files that were modified and might have indentation issues
    target_files = [
        "web_app.py",
        "session_error_handlers.py",
        "dashboard_notification_helpers.py",
        "security/core/csrf_error_handler.py",
        "security/core/role_based_access.py",
        "admin/routes/cleanup.py",
        "admin/routes/system_health.py",
        "admin/routes/storage_management.py"
    ]
    
    fixed_files = []
    
    for file_path in target_files:
        path = Path(file_path)
        if path.exists():
            if fix_indentation_in_file(path):
                fixed_files.append(file_path)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n📊 Summary:")
    print(f"  - Files processed: {len(target_files)}")
    print(f"  - Files fixed: {len(fixed_files)}")
    
    if fixed_files:
        print(f"  - Fixed files: {', '.join(fixed_files)}")
        print("\n✅ Indentation fixes completed!")
    else:
        print("\n✅ No indentation issues found.")

if __name__ == "__main__":
    main()