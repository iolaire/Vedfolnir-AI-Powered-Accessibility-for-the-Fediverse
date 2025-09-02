#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Clean Up Unnecessary Pass Statements

This script removes unnecessary pass statements that were added after TODO comments
where they're not needed (i.e., when there's already other code in the block).
"""

import re
from pathlib import Path

def clean_pass_statements_in_file(file_path: Path) -> bool:
    """Remove unnecessary pass statements from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.split('\n')
        cleaned_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this is a pass statement that might be unnecessary
            if line.strip() == 'pass':
                # Look at the previous line to see if it's a TODO comment
                if i > 0 and '# TODO: Replace with unified notification:' in lines[i-1]:
                    # Check if there's actual code after this pass statement in the same block
                    current_indent = len(line) - len(line.lstrip())
                    has_code_after = False
                    
                    # Look ahead to see if there's code at the same or greater indentation
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j]
                        if not next_line.strip():  # Skip empty lines
                            continue
                        
                        next_indent = len(next_line) - len(next_line.lstrip())
                        
                        # If we find code at the same indentation level, pass is unnecessary
                        if next_indent == current_indent and not next_line.strip().startswith('#'):
                            has_code_after = True
                            break
                        # If indentation is less, we've left the block
                        elif next_indent < current_indent:
                            break
                    
                    # If there's code after, skip the pass statement
                    if has_code_after:
                        i += 1
                        continue
            
            cleaned_lines.append(line)
            i += 1
        
        new_content = '\n'.join(cleaned_lines)
        
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Cleaned unnecessary pass statements in {file_path}")
            return True
        else:
            print(f"ℹ️  No unnecessary pass statements found in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {str(e)}")
        return False

def main():
    """Main execution function"""
    print("🧹 Cleaning up unnecessary pass statements...")
    
    # Files that might have unnecessary pass statements
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
    
    cleaned_files = []
    
    for file_path in target_files:
        path = Path(file_path)
        if path.exists():
            if clean_pass_statements_in_file(path):
                cleaned_files.append(file_path)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n📊 Summary:")
    print(f"  - Files processed: {len(target_files)}")
    print(f"  - Files cleaned: {len(cleaned_files)}")
    
    if cleaned_files:
        print(f"  - Cleaned files: {', '.join(cleaned_files)}")
        print("\n✅ Pass statement cleanup completed!")
    else:
        print("\n✅ No unnecessary pass statements found.")

if __name__ == "__main__":
    main()