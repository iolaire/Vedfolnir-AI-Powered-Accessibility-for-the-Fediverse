# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Complete Notification Replacement Script

This script systematically replaces ALL remaining TODO notification comments
with actual unified notification system calls.
"""

import os
import re
import glob
import logging

logger = logging.getLogger(__name__)

def replace_session_aware_decorators():
    """Replace TODO comments in session_aware_decorators.py"""
    file_path = 'session_aware_decorators.py'
    
    replacements = [
        (
            r'# TODO: Replace with unified notification: Database session error\. Please try again\. \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Database session error. Please try again.", "Database Error")'
        ),
        (
            r'# TODO: Replace with unified notification: Database error occurred\. Please try again\. \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Database error occurred. Please try again.", "Database Error")'
        ),
        (
            r'# TODO: Replace with unified notification: An unexpected error occurred\. Please try again\. \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("An unexpected error occurred. Please try again.", "Unexpected Error")'
        ),
        (
            r'# TODO: Replace with unified notification: Please log in to access this page\. \(info\)',
            '# Send info notification\n                from notification_helpers import send_info_notification\n                send_info_notification("Please log in to access this page.", "Authentication Required")'
        ),
        (
            r'# TODO: Replace with unified notification: User authentication error\. Please log in again\. \(error\)',
            '# Send error notification\n                        from notification_helpers import send_error_notification\n                        send_error_notification("User authentication error. Please log in again.", "Authentication Error")'
        ),
        (
            r'# TODO: Replace with unified notification: You need to set up at least one platform connection to access this feature\. \(warning\)',
            '# Send warning notification\n                        from notification_helpers import send_warning_notification\n                        send_warning_notification("You need to set up at least one platform connection to access this feature.", "Platform Setup Required")'
        ),
        (
            r'# TODO: Replace with unified notification: Error loading platform information\. Please try again\. \(error\)',
            '# Send error notification\n                from notification_helpers import send_error_notification\n                send_error_notification("Error loading platform information. Please try again.", "Platform Error")'
        ),
        (
            r'# TODO: Replace with unified notification: Database session error\. Please log in again\. \(warning\)',
            '# Send warning notification\n            from notification_helpers import send_warning_notification\n            send_warning_notification("Database session error. Please log in again.", "Session Error")'
        ),
        (
            r'# TODO: Replace with unified notification: Your session has expired\. Please refresh the page or log in again\. \(warning\)',
            '# Send warning notification\n                from notification_helpers import send_warning_notification\n                send_warning_notification("Your session has expired. Please refresh the page or log in again.", "Session Expired")'
        ),
        (
            r'# TODO: Replace with unified notification: Platform session error\. Please select your platform again\. \(warning\)',
            '# Send warning notification\n                from notification_helpers import send_warning_notification\n                send_warning_notification("Platform session error. Please select your platform again.", "Platform Session Error")'
        ),
        (
            r'# TODO: Replace with unified notification: Session error occurred\. Please try again\. \(error\)',
            '# Send error notification\n                from notification_helpers import send_error_notification\n                send_error_notification("Session error occurred. Please try again.", "Session Error")'
        ),
        (
            r'# TODO: Replace with unified notification: Your session has expired\. Please log in again\. \(warning\)',
            '# Send warning notification\n                from notification_helpers import send_warning_notification\n                send_warning_notification("Your session has expired. Please log in again.", "Session Expired")'
        )
    ]
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated {file_path}")

def replace_session_error_handling():
    """Replace TODO comments in session_error_handling.py"""
    file_path = 'session_error_handling.py'
    
    replacements = [
        (
            r'# TODO: Replace with unified notification: session expired message',
            '# Send warning notification\n            from notification_helpers import send_warning_notification\n            send_warning_notification("Your session has expired. Please log in again.", "Session Expired")'
        ),
        (
            r'# TODO: Replace with unified notification: session not found message',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Session not found. Please log in again.", "Session Not Found")'
        ),
        (
            r'# TODO: Replace with unified notification: session validation error message',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Session validation failed. Please log in again.", "Session Validation Failed")'
        ),
        (
            r'# TODO: Replace with unified notification: session general error message',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("A session error occurred. Please try again.", "Session Error")'
        )
    ]
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated {file_path}")

def replace_admin_routes():
    """Replace TODO comments in admin routes"""
    admin_files = glob.glob('admin/routes/*.py')
    
    common_replacements = [
        (
            r'# TODO: Replace with unified notification: Access denied\. Admin privileges required\. \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Access denied. Admin privileges required.", "Access Denied")'
        ),
        (
            r'# TODO: Replace with unified notification: Access denied \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Access denied.", "Access Denied")'
        ),
        (
            r'# TODO: Replace with unified notification: ([^(]+) \(error\)',
            r'# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("\1", "Error")'
        ),
        (
            r'# TODO: Replace with unified notification: ([^(]+) \(success\)',
            r'# Send success notification\n            from notification_helpers import send_success_notification\n            send_success_notification("\1", "Success")'
        ),
        (
            r'# TODO: Replace with unified notification: ([^(]+) \(warning\)',
            r'# Send warning notification\n            from notification_helpers import send_warning_notification\n            send_warning_notification("\1", "Warning")'
        ),
        (
            r'# TODO: Replace with unified notification: ([^(]+) \(info\)',
            r'# Send info notification\n            from notification_helpers import send_info_notification\n            send_info_notification("\1", "Information")'
        )
    ]
    
    for file_path in admin_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            for pattern, replacement in common_replacements:
                content = re.sub(pattern, replacement, content)
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✅ Updated {file_path}")

def replace_routes():
    """Replace TODO comments in routes directory"""
    route_files = glob.glob('routes/*.py')
    
    for file_path in route_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Generic replacements for routes
            patterns = [
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(error\) - ([^)]+)',
                    r'# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("\1", "\2")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(success\) - ([^)]+)',
                    r'# Send success notification\n            from notification_helpers import send_success_notification\n            send_success_notification("\1", "\2")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(warning\) - ([^)]+)',
                    r'# Send warning notification\n            from notification_helpers import send_warning_notification\n            send_warning_notification("\1", "\2")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(info\) - ([^)]+)',
                    r'# Send info notification\n            from notification_helpers import send_info_notification\n            send_info_notification("\1", "\2")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(error\)',
                    r'# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("\1", "Error")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(success\)',
                    r'# Send success notification\n            from notification_helpers import send_success_notification\n            send_success_notification("\1", "Success")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(warning\)',
                    r'# Send warning notification\n            from notification_helpers import send_warning_notification\n            send_warning_notification("\1", "Warning")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(info\)',
                    r'# Send info notification\n            from notification_helpers import send_info_notification\n            send_info_notification("\1", "Information")'
                )
            ]
            
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✅ Updated {file_path}")

def replace_other_files():
    """Replace TODO comments in other Python files"""
    # Find all Python files with TODO comments
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', '.pytest_cache']):
            continue
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        if 'TODO: Replace with unified notification' in content:
                            python_files.append(file_path)
                except:
                    continue
    
    for file_path in python_files:
        if 'scripts/' in file_path and any(script in file_path for script in ['fix_notification', 'replace_flash', 'clean_pass', 'fix_indentation']):
            # Skip script files that contain the patterns as examples
            continue
            
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Generic replacements
            patterns = [
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(error\) - ([^)]+)',
                    r'# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("\1", "\2")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(success\) - ([^)]+)',
                    r'# Send success notification\n            from notification_helpers import send_success_notification\n            send_success_notification("\1", "\2")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(warning\) - ([^)]+)',
                    r'# Send warning notification\n            from notification_helpers import send_warning_notification\n            send_warning_notification("\1", "\2")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(info\) - ([^)]+)',
                    r'# Send info notification\n            from notification_helpers import send_info_notification\n            send_info_notification("\1", "\2")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(error\)',
                    r'# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("\1", "Error")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(success\)',
                    r'# Send success notification\n            from notification_helpers import send_success_notification\n            send_success_notification("\1", "Success")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(warning\)',
                    r'# Send warning notification\n            from notification_helpers import send_warning_notification\n            send_warning_notification("\1", "Warning")'
                ),
                (
                    r'# TODO: Replace with unified notification: ([^(]+) \(info\)',
                    r'# Send info notification\n            from notification_helpers import send_info_notification\n            send_info_notification("\1", "Information")'
                )
            ]
            
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✅ Updated {file_path}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")

def main():
    """Main function to replace all TODO comments"""
    print("🚀 Starting complete notification replacement...")
    print("=" * 50)
    
    # Replace specific files first
    replace_session_aware_decorators()
    replace_session_error_handling()
    replace_admin_routes()
    replace_routes()
    replace_other_files()
    
    print("=" * 50)
    print("✅ Complete notification replacement finished!")
    
    # Check for remaining TODO comments
    print("\n🔍 Checking for remaining TODO comments...")
    remaining_count = 0
    
    for root, dirs, files in os.walk('.'):
        if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', '.pytest_cache']):
            continue
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        if 'TODO: Replace with unified notification' in content:
                            # Skip script files
                            if 'scripts/' in file_path and any(script in file_path for script in ['fix_notification', 'replace_flash', 'clean_pass', 'fix_indentation']):
                                continue
                            remaining_count += content.count('TODO: Replace with unified notification')
                            print(f"  📝 {file_path}: {content.count('TODO: Replace with unified notification')} remaining")
                except:
                    continue
    
    if remaining_count == 0:
        print("🎉 All TODO comments have been replaced!")
    else:
        print(f"⚠️ {remaining_count} TODO comments still need manual review")

if __name__ == '__main__':
    main()