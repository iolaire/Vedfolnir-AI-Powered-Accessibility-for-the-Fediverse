#!/usr/bin/env python3
"""Fix indentation in test file"""

def fix_indentation():
    test_file = 'tests/integration/test_unified_notification_system.py'
    
    with open(test_file, 'r') as f:
        lines = f.readlines()
    
    # Fix the indentation issue around line 261-262
    for i, line in enumerate(lines):
        if 'def test_notification_helper_functions(self):' in line:
            # Ensure proper indentation for the method and its content
            if not line.startswith('    def '):
                lines[i] = '    ' + line.lstrip()
            
            # Fix subsequent lines
            j = i + 1
            while j < len(lines) and (lines[j].startswith('        ') or lines[j].strip() == '' or lines[j].startswith('    def ') == False):
                if lines[j].strip() and not lines[j].startswith('        ') and not lines[j].startswith('    def '):
                    lines[j] = '        ' + lines[j].lstrip()
                j += 1
                if j < len(lines) and lines[j].startswith('    def '):
                    break
            break
    
    with open(test_file, 'w') as f:
        f.writelines(lines)
    
    print("✅ Fixed indentation")

if __name__ == '__main__':
    fix_indentation()
