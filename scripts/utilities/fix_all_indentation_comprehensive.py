#!/usr/bin/env python3
"""
Comprehensive indentation fix for notification imports
"""

import re
import os

def fix_file_indentation(filepath):
    """Fix indentation issues in a Python file"""
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check if this is a notification import that needs fixing
            if 'from notification_helpers import' in line and not line.strip().startswith('#'):
                # Check if it's improperly indented
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line.endswith(':') or 'else:' in prev_line:
                        # Find the proper indentation level by looking at the context
                        indent_level = 0
                        
                        # Look backwards to find the proper indentation
                        for j in range(i-1, -1, -1):
                            if lines[j].strip():
                                current_indent = len(lines[j]) - len(lines[j].lstrip())
                                if lines[j].strip().endswith(':'):
                                    indent_level = current_indent + 4
                                    break
                                elif 'if ' in lines[j] or 'else:' in lines[j] or 'elif ' in lines[j]:
                                    indent_level = current_indent + 4
                                    break
                                else:
                                    indent_level = current_indent
                        
                        # Apply the correct indentation
                        line = ' ' * indent_level + line.strip() + '\n'
                        
                        # Also fix the next line if it's a send_notification call
                        if i + 1 < len(lines) and 'send_' in lines[i + 1] and 'notification' in lines[i + 1]:
                            next_line = lines[i + 1]
                            lines[i + 1] = ' ' * indent_level + next_line.strip() + '\n'
            
            fixed_lines.append(line)
            i += 1
        
        # Write back the fixed content
        with open(filepath, 'w') as f:
            f.writelines(fixed_lines)
        
        return True
        
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False

def main():
    """Fix indentation in all Python files"""
    files_to_fix = [
        'admin/routes/admin_job_api.py',
        'admin/routes/admin_job_management.py',
        'admin/security/admin_access_control.py'
    ]
    
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            print(f"Fixing {filepath}...")
            if fix_file_indentation(filepath):
                print(f"✅ Fixed {filepath}")
            else:
                print(f"❌ Failed to fix {filepath}")
        else:
            print(f"⚠️ File not found: {filepath}")

if __name__ == "__main__":
    main()