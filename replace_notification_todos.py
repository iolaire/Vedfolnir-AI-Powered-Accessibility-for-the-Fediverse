# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Script to systematically replace TODO notification comments with unified notification system calls
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

def replace_access_denied_notifications(file_path):
    """Replace access denied TODO comments"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace access denied patterns
    patterns = [
        (
            r'# TODO: Replace with unified notification: Access denied\. Admin privileges required\. \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Access denied. Admin privileges required.", "Access Denied")'
        ),
        (
            r'# TODO: Replace with unified notification: Access denied \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Access denied.", "Access Denied")'
        )
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w') as f:
        f.write(content)

def replace_error_notifications(file_path):
    """Replace error notification TODO comments"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Common error patterns
    patterns = [
        (
            r"# TODO: Replace with unified notification: f'Error loading health dashboard: \{str\(e\)\}' \(error\)",
            "# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification(f'Error loading health dashboard: {str(e)}', 'Dashboard Error')"
        ),
        (
            r'# TODO: Replace with unified notification: User not found \(error\)',
            '# Send error notification\n                        from notification_helpers import send_error_notification\n                        send_error_notification("User not found.", "User Not Found")'
        ),
        (
            r'# TODO: Replace with unified notification: Failed to update user \(error\)',
            '# Send error notification\n                    from notification_helpers import send_error_notification\n                    send_error_notification("Failed to update user.", "Update Failed")'
        ),
        (
            r'# TODO: Replace with unified notification: An error occurred while updating the user \(error\)',
            '# Send error notification\n                from notification_helpers import send_error_notification\n                send_error_notification("An error occurred while updating the user.", "Update Error")'
        ),
        (
            r'# TODO: Replace with unified notification: You cannot delete your own account \(error\)',
            '# Send error notification\n                from notification_helpers import send_error_notification\n                send_error_notification("You cannot delete your own account.", "Invalid Operation")'
        ),
        (
            r'# TODO: Replace with unified notification: An error occurred while deleting the user \(error\)',
            '# Send error notification\n                from notification_helpers import send_error_notification\n                send_error_notification("An error occurred while deleting the user.", "Delete Error")'
        ),
        (
            r'# TODO: Replace with unified notification: Missing required fields \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Missing required fields.", "Invalid Input")'
        ),
        (
            r'# TODO: Replace with unified notification: Invalid role specified \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Invalid role specified.", "Invalid Role")'
        ),
        (
            r'# TODO: Replace with unified notification: An error occurred while updating user role \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("An error occurred while updating user role.", "Role Update Error")'
        ),
        (
            r'# TODO: Replace with unified notification: Missing user ID \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("Missing user ID.", "Invalid Input")'
        ),
        (
            r'# TODO: Replace with unified notification: An error occurred while updating user status \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("An error occurred while updating user status.", "Status Update Error")'
        ),
        (
            r'# TODO: Replace with unified notification: An error occurred while resetting password \(error\)',
            '# Send error notification\n            from notification_helpers import send_error_notification\n            send_error_notification("An error occurred while resetting password.", "Password Reset Error")'
        )
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w') as f:
        f.write(content)

def process_file(file_path):
    """Process a single file to replace TODO comments"""
    try:
        print(f"Processing {file_path}...")
        replace_access_denied_notifications(file_path)
        replace_error_notifications(file_path)
        print(f"Completed {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    """Main function to process all files"""
    # Files to process
    files_to_process = [
        'admin/routes/system_health.py',
        'admin/routes/user_management.py',
        'admin/routes/storage_management.py',
        'admin/routes/monitoring.py',
        'admin/routes/job_api.py'
    ]
    
    for file_path in files_to_process:
        if os.path.exists(file_path):
            process_file(file_path)
        else:
            print(f"File not found: {file_path}")

if __name__ == '__main__':
    main()