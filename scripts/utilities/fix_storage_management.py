#!/usr/bin/env python3
"""
Fix all indentation issues in storage_management.py
"""

import re

def fix_storage_management():
    """Fix indentation issues in storage_management.py"""
    
    with open('admin/routes/storage_management.py', 'r') as f:
        content = f.read()
    
    # Split into lines for processing
    lines = content.split('\n')
    fixed_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Fix notification import indentation issues
        if 'from notification_helpers import' in line:
            # Check if it's improperly indented
            if line.startswith('                from notification_helpers'):
                # This is too indented, fix it
                line = '            ' + line.strip()
            elif line.startswith('        from notification_helpers'):
                # This might be correct for some contexts
                pass
            elif not line.startswith('    ') and not line.startswith('#'):
                # This needs proper indentation
                line = '            ' + line.strip()
        
        # Fix send_notification calls
        elif ('send_error_notification' in line or 
              'send_success_notification' in line or 
              'send_warning_notification' in line or 
              'send_info_notification' in line):
            if line.startswith('                send_'):
                # Too indented
                line = '            ' + line.strip()
            elif not line.startswith('    ') and not line.startswith('#'):
                # Needs proper indentation
                line = '            ' + line.strip()
        
        # Fix return statements that might be misaligned
        elif 'return redirect(' in line and line.startswith('            return'):
            # This is correct indentation for most cases
            pass
        elif 'return redirect(' in line and not line.startswith('    '):
            # Needs proper indentation
            line = '            ' + line.strip()
        
        fixed_lines.append(line)
        i += 1
    
    # Join back together
    fixed_content = '\n'.join(fixed_lines)
    
    # Write back
    with open('admin/routes/storage_management.py', 'w') as f:
        f.write(fixed_content)
    
    print("Fixed storage_management.py indentation issues")

if __name__ == "__main__":
    fix_storage_management()