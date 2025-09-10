# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Profile Notifications Migration Script

This script migrates user profile and settings notifications from legacy Flask flash
messages to the unified WebSocket notification system. It updates the user management
routes to use real-time notifications for profile updates, settings changes, password
changes, and account status changes.
"""

"""
⚠️  DEPRECATED: This file is deprecated and will be removed in a future version.
Please use the unified notification system instead:
- unified_notification_manager.py (core system)
- notification_service_adapters.py (service adapters)
- notification_helpers.py (helper functions)
- app/websocket/core/consolidated_handlers.py (WebSocket handling)

Migration guide: docs/implementation/notification-consolidation-final-summary.md
"""

import warnings
warnings.warn(
    "This notification system is deprecated. Use the unified notification system instead.",
    DeprecationWarning,
    stacklevel=2
)


import logging
import re
import os
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class UserProfileNotificationMigrator:
    """Migrates user profile notifications to unified system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.migration_patterns = self._setup_migration_patterns()
    
    def _setup_migration_patterns(self) -> List[Dict[str, Any]]:
        """Setup patterns for migrating flash messages to notifications"""
        return [
            # Registration notifications
            {
                'pattern': r"flash\(\s*f?['\"]Registration successful.*?['\"],\s*['\"]success['\"]\s*\)",
                'replacement': "send_profile_notification('email_verification', True, 'Registration successful! Please check your email for verification.')",
                'import_needed': True,
                'category': 'registration'
            },
            {
                'pattern': r"flash\(\s*f?['\"]Registration failed.*?['\"],\s*['\"]error['\"]\s*\)",
                'replacement': "send_profile_notification('profile_update', False, 'Registration failed. Please try again.')",
                'import_needed': True,
                'category': 'registration'
            },
            
            # Email verification notifications
            {
                'pattern': r"flash\(\s*f?['\"]Email verification successful.*?['\"],\s*['\"]success['\"]\s*\)",
                'replacement': "send_profile_notification('email_verification', True, 'Email verification successful! Your account is now active.')",
                'import_needed': True,
                'category': 'email_verification'
            },
            {
                'pattern': r"flash\(\s*f?['\"]Email verification failed.*?['\"],\s*['\"]error['\"]\s*\)",
                'replacement': "send_profile_notification('email_verification', False, 'Email verification failed. Please try again or contact support.')",
                'import_needed': True,
                'category': 'email_verification'
            },
            {
                'pattern': r"flash\(\s*['\"]Verification email sent.*?['\"],\s*['\"]success['\"]\s*\)",
                'replacement': "send_profile_notification('email_verification', True, 'Verification email sent! Please check your email.')",
                'import_needed': True,
                'category': 'email_verification'
            },
            
            # Login notifications
            {
                'pattern': r"flash\(\s*f?['\"]Welcome back.*?['\"],\s*['\"]success['\"]\s*\)",
                'replacement': "send_profile_notification('account_status', True, f'Welcome back, {username}!', status_change='login')",
                'import_needed': True,
                'category': 'login'
            },
            {
                'pattern': r"flash\(\s*['\"]Login failed.*?['\"],\s*['\"]error['\"]\s*\)",
                'replacement': "send_profile_notification('account_status', False, 'Login failed. Please check your credentials.', status_change='login_failed')",
                'import_needed': True,
                'category': 'login'
            },
            
            # Password change notifications
            {
                'pattern': r"flash\(\s*['\"]Password changed successfully.*?['\"],\s*['\"]success['\"]\s*\)",
                'replacement': "send_profile_notification('password_change', True, 'Password changed successfully!', security_details={'ip_address': ip_address, 'user_agent': user_agent})",
                'import_needed': True,
                'category': 'password_change'
            },
            {
                'pattern': r"flash\(\s*['\"]Password change failed.*?['\"],\s*['\"]error['\"]\s*\)",
                'replacement': "send_profile_notification('password_change', False, 'Password change failed. Please try again.')",
                'import_needed': True,
                'category': 'password_change'
            },
            
            # Profile update notifications
            {
                'pattern': r"flash\(\s*['\"]Profile updated successfully.*?['\"],\s*['\"]success['\"]\s*\)",
                'replacement': "send_profile_notification('profile_update', True, 'Profile updated successfully!')",
                'import_needed': True,
                'category': 'profile_update'
            },
            {
                'pattern': r"flash\(\s*f?['\"]Failed to update profile.*?['\"],\s*['\"]error['\"]\s*\)",
                'replacement': "send_profile_notification('profile_update', False, 'Failed to update profile. Please try again.')",
                'import_needed': True,
                'category': 'profile_update'
            },
            
            # Settings change notifications
            {
                'pattern': r"flash\(\s*['\"]Settings updated successfully.*?['\"],\s*['\"]success['\"]\s*\)",
                'replacement': "send_profile_notification('settings_change', True, 'Settings updated successfully!', setting_name='user_settings')",
                'import_needed': True,
                'category': 'settings_change'
            },
            {
                'pattern': r"flash\(\s*['\"]Caption generation settings saved successfully.*?['\"],\s*['\"]success['\"]\s*\)",
                'replacement': "send_profile_notification('settings_change', True, 'Caption generation settings saved successfully!', setting_name='caption_settings')",
                'import_needed': True,
                'category': 'settings_change'
            },
            
            # Account status notifications
            {
                'pattern': r"flash\(\s*['\"]You have been logged out successfully.*?['\"],\s*['\"]info['\"]\s*\)",
                'replacement': "send_profile_notification('account_status', True, 'You have been logged out successfully.', status_change='logout')",
                'import_needed': True,
                'category': 'logout'
            },
            
            # Generic error notifications
            {
                'pattern': r"flash\(\s*['\"].*?failed due to a system error.*?['\"],\s*['\"]error['\"]\s*\)",
                'replacement': "send_profile_notification('profile_update', False, 'Operation failed due to a system error. Please try again.')",
                'import_needed': True,
                'category': 'system_error'
            }
        ]
    
    def migrate_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Migrate a single file to use unified notifications
        
        Args:
            file_path: Path to the file to migrate
            
        Returns:
            Tuple of (success, list of changes made)
        """
        try:
            if not os.path.exists(file_path):
                return False, [f"File not found: {file_path}"]
            
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            changes = []
            import_added = False
            
            # Apply migration patterns
            for pattern_info in self.migration_patterns:
                pattern = pattern_info['pattern']
                replacement = pattern_info['replacement']
                category = pattern_info['category']
                
                matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
                if matches:
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
                    changes.append(f"Migrated {len(matches)} {category} notification(s)")
                    
                    # Add import if needed and not already added
                    if pattern_info.get('import_needed', False) and not import_added:
                        content = self._add_notification_import(content)
                        import_added = True
            
            # Only write if changes were made
            if content != original_content:
                # Create backup
                backup_path = f"{file_path}.backup"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Write updated content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                changes.append(f"Created backup: {backup_path}")
                self.logger.info(f"Migrated notifications in {file_path}")
                return True, changes
            else:
                return True, ["No flash messages found to migrate"]
                
        except Exception as e:
            self.logger.error(f"Error migrating file {file_path}: {e}")
            return False, [f"Error: {str(e)}"]
    
    def _add_notification_import(self, content: str) -> str:
        """Add the notification import to the file"""
        import_statement = "from user_profile_notification_helper import send_profile_notification\n"
        
        # Find the last import statement
        import_lines = []
        other_lines = []
        in_imports = True
        
        for line in content.split('\n'):
            if line.strip().startswith(('import ', 'from ')) and in_imports:
                import_lines.append(line)
            elif line.strip() == '' and in_imports:
                import_lines.append(line)
            else:
                if in_imports and line.strip():
                    in_imports = False
                other_lines.append(line)
        
        # Add our import after existing imports
        if import_lines:
            import_lines.append(import_statement.rstrip())
            return '\n'.join(import_lines + other_lines)
        else:
            # No existing imports, add at the top after copyright header
            lines = content.split('\n')
            insert_index = 0
            
            # Skip copyright header
            for i, line in enumerate(lines):
                if line.strip().startswith('"""') and 'Copyright' in line:
                    # Find end of copyright block
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().endswith('"""'):
                            insert_index = j + 1
                            break
                    break
                elif line.strip().startswith('#') and 'Copyright' in line:
                    # Skip comment-style copyright
                    for j in range(i, len(lines)):
                        if not lines[j].strip().startswith('#'):
                            insert_index = j
                            break
                    break
            
            lines.insert(insert_index, '')
            lines.insert(insert_index + 1, import_statement.rstrip())
            return '\n'.join(lines)
    
    def migrate_user_management_routes(self) -> Tuple[bool, List[str]]:
        """Migrate user management routes file"""
        return self.migrate_file('routes/user_management_routes.py')
    
    def migrate_web_app_settings(self) -> Tuple[bool, List[str]]:
        """Migrate web app settings routes"""
        return self.migrate_file('web_app.py')
    
    def run_full_migration(self) -> Dict[str, Any]:
        """
        Run full migration of user profile notifications
        
        Returns:
            Dictionary with migration results
        """
        results = {
            'success': True,
            'files_migrated': [],
            'files_failed': [],
            'total_changes': []
        }
        
        # Files to migrate
        files_to_migrate = [
            'routes/user_management_routes.py',
            'web_app.py'
        ]
        
        for file_path in files_to_migrate:
            success, changes = self.migrate_file(file_path)
            
            if success:
                results['files_migrated'].append(file_path)
                results['total_changes'].extend([f"{file_path}: {change}" for change in changes])
            else:
                results['files_failed'].append(file_path)
                results['success'] = False
                results['total_changes'].extend([f"{file_path}: {change}" for change in changes])
        
        return results


def main():
    """Main migration function"""
    logging.basicConfig(level=logging.INFO)
    
    print("=== User Profile Notifications Migration ===")
    print("Migrating from Flask flash messages to unified WebSocket notifications...")
    
    migrator = UserProfileNotificationMigrator()
    results = migrator.run_full_migration()
    
    print(f"\nMigration Results:")
    print(f"Success: {results['success']}")
    print(f"Files migrated: {len(results['files_migrated'])}")
    print(f"Files failed: {len(results['files_failed'])}")
    
    if results['files_migrated']:
        print(f"\nSuccessfully migrated:")
        for file_path in results['files_migrated']:
            print(f"  ✓ {file_path}")
    
    if results['files_failed']:
        print(f"\nFailed to migrate:")
        for file_path in results['files_failed']:
            print(f"  ✗ {file_path}")
    
    if results['total_changes']:
        print(f"\nChanges made:")
        for change in results['total_changes']:
            print(f"  - {change}")
    
    print(f"\n=== Migration Complete ===")
    return results['success']


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)