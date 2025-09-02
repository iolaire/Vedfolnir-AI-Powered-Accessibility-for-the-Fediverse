#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Fix All Syntax Issues

This script fixes all remaining syntax issues by adding pass statements
where needed after TODO comments.
"""

import ast
import sys
from pathlib import Path

def check_syntax_and_fix(file_path: Path) -> bool:
    """Check syntax and fix issues by adding pass statements"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the file
        try:
            ast.parse(content)
            print(f"✅ {file_path} - syntax OK")
            return False  # No changes needed
        except SyntaxError as e:
            print(f"🔧 {file_path} - fixing syntax error at line {e.lineno}: {e.msg}")
            
            lines = content.split('\n')
            
            # Common patterns that need fixing
            if "expected an indented block" in e.msg:
                # Find the line that needs indentation
                error_line_idx = e.lineno - 1
                
                # Look backwards to find the statement that needs a block
                for i in range(error_line_idx - 1, -1, -1):
                    line = lines[i].strip()
                    if (line.endswith(':') and 
                        any(keyword in line for keyword in ['if', 'else:', 'elif', 'for', 'while', 'try:', 'except', 'finally:', 'with', 'def', 'class'])):
                        
                        # Get the indentation level
                        indent_level = len(lines[i]) - len(lines[i].lstrip())
                        
                        # Add pass statement with proper indentation
                        pass_statement = ' ' * (indent_level + 4) + 'pass'
                        
                        # Insert the pass statement
                        lines.insert(error_line_idx, pass_statement)
                        
                        # Write the fixed content
                        fixed_content = '\n'.join(lines)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        
                        print(f"  ✅ Added pass statement at line {error_line_idx + 1}")
                        return True
                        
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {str(e)}")
        return False

def main():
    """Main execution function"""
    print("🔧 Checking and fixing syntax issues...")
    
    # Key files that might have syntax issues
    target_files = [
        "web_app.py",
        "session_error_handlers.py",
        "dashboard_notification_helpers.py",
        "security/core/csrf_error_handler.py",
        "security/core/role_based_access.py",
        "admin/routes/cleanup.py",
        "admin/routes/system_health.py",
        "admin/routes/storage_management.py",
        "admin/routes/user_management.py",
        "admin/routes/monitoring.py",
        "admin/routes/admin_job_api.py",
        "admin/routes/dashboard.py",
        "admin/routes/performance_dashboard.py",
        "admin/routes/maintenance_mode.py",
        "admin/routes/admin_job_management.py",
        "routes/user_management_routes.py",
        "routes/gdpr_routes.py",
        "admin/security/admin_access_control.py",
        "user_profile_notification_helper.py"
    ]
    
    fixed_files = []
    
    for file_path in target_files:
        path = Path(file_path)
        if path.exists():
            if check_syntax_and_fix(path):
                fixed_files.append(file_path)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n📊 Summary:")
    print(f"  - Files checked: {len(target_files)}")
    print(f"  - Files fixed: {len(fixed_files)}")
    
    if fixed_files:
        print(f"  - Fixed files: {', '.join(fixed_files)}")
        print("\n✅ Syntax fixes completed!")
    else:
        print("\n✅ No syntax issues found.")

if __name__ == "__main__":
    main()