# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Profile Template Integration

This module provides template integration for user profile and settings pages
to include the unified notification system. It updates templates to include
the necessary JavaScript and CSS for real-time notifications.
"""

import logging
import os
import re
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class UserProfileTemplateIntegrator:
    """Integrates notification system into user profile templates"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.template_patterns = self._setup_template_patterns()
    
    def _setup_template_patterns(self) -> Dict[str, Any]:
        """Setup patterns for template integration"""
        return {
            'socket_io_script': {
                'pattern': r'<script.*?src.*?socket\.io.*?></script>',
                'replacement': '<script src="{{ url_for(\'static\', filename=\'js/socket.io.min.js\') }}"></script>',
                'required': True
            },
            'notification_script': {
                'pattern': r'<script.*?src.*?user_profile_notifications\.js.*?></script>',
                'replacement': '<script src="{{ url_for(\'static\', filename=\'js/user_profile_notifications.js\') }}"></script>',
                'required': True
            },
            'notification_container': {
                'pattern': r'<div.*?id=["\']notification-container["\'].*?></div>',
                'replacement': '<div id="notification-container" class="notification-container"></div>',
                'required': True
            },
            'page_class_profile': {
                'pattern': r'<body[^>]*>',
                'replacement': '<body class="profile-page">',
                'condition': 'profile'
            },
            'page_class_settings': {
                'pattern': r'<body[^>]*>',
                'replacement': '<body class="settings-page">',
                'condition': 'settings'
            },
            'page_class_password': {
                'pattern': r'<body[^>]*>',
                'replacement': '<body class="change-password-page">',
                'condition': 'password'
            }
        }
    
    def integrate_template(self, template_path: str, page_type: str = 'profile') -> Tuple[bool, List[str]]:
        """
        Integrate notification system into a template
        
        Args:
            template_path: Path to the template file
            page_type: Type of page (profile, settings, password)
            
        Returns:
            Tuple of (success, list of changes made)
        """
        try:
            if not os.path.exists(template_path):
                return False, [f"Template not found: {template_path}"]
            
            # Read the template
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            changes = []
            
            # Add Socket.IO script if not present
            if not re.search(self.template_patterns['socket_io_script']['pattern'], content, re.IGNORECASE):
                content = self._add_socket_io_script(content)
                changes.append("Added Socket.IO script")
            
            # Add notification script if not present
            if not re.search(self.template_patterns['notification_script']['pattern'], content, re.IGNORECASE):
                content = self._add_notification_script(content)
                changes.append("Added user profile notification script")
            
            # Add notification container if not present
            if not re.search(self.template_patterns['notification_container']['pattern'], content, re.IGNORECASE):
                content = self._add_notification_container(content)
                changes.append("Added notification container")
            
            # Add page-specific class to body
            content = self._add_page_class(content, page_type)
            changes.append(f"Added {page_type} page class")
            
            # Add CSRF token meta tag if not present
            if not re.search(r'<meta name=["\']csrf-token["\']', content, re.IGNORECASE):
                content = self._add_csrf_meta_tag(content)
                changes.append("Added CSRF token meta tag")
            
            # Only write if changes were made
            if content != original_content:
                # Create backup
                backup_path = f"{template_path}.backup"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Write updated content
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                changes.append(f"Created backup: {backup_path}")
                self.logger.info(f"Integrated notifications in template {template_path}")
                return True, changes
            else:
                return True, ["Template already integrated"]
                
        except Exception as e:
            self.logger.error(f"Error integrating template {template_path}: {e}")
            return False, [f"Error: {str(e)}"]
    
    def _add_socket_io_script(self, content: str) -> str:
        """Add Socket.IO script to template"""
        script_tag = '<script src="{{ url_for(\'static\', filename=\'js/socket.io.min.js\') }}"></script>'
        
        # Try to add before closing head tag
        if '</head>' in content:
            content = content.replace('</head>', f'    {script_tag}\n</head>')
        else:
            # Add after opening head tag
            content = re.sub(r'(<head[^>]*>)', f'\\1\n    {script_tag}', content)
        
        return content
    
    def _add_notification_script(self, content: str) -> str:
        """Add notification script to template"""
        script_tag = '<script src="{{ url_for(\'static\', filename=\'js/user_profile_notifications.js\') }}"></script>'
        
        # Try to add before closing body tag
        if '</body>' in content:
            content = content.replace('</body>', f'    {script_tag}\n</body>')
        else:
            # Add after Socket.IO script
            socket_pattern = r'(<script.*?socket\.io.*?></script>)'
            content = re.sub(socket_pattern, f'\\1\n    {script_tag}', content, flags=re.IGNORECASE)
        
        return content
    
    def _add_notification_container(self, content: str) -> str:
        """Add notification container to template"""
        container_div = '<div id="notification-container" class="notification-container"></div>'
        
        # Try to add after opening body tag
        if '<body' in content:
            content = re.sub(r'(<body[^>]*>)', f'\\1\n    {container_div}', content)
        else:
            # Add at the beginning of content
            content = f'{container_div}\n{content}'
        
        return content
    
    def _add_page_class(self, content: str, page_type: str) -> str:
        """Add page-specific class to body tag"""
        class_name = f"{page_type}-page"
        
        # Check if body tag already has a class
        body_match = re.search(r'<body([^>]*)>', content)
        if body_match:
            body_attrs = body_match.group(1)
            
            if 'class=' in body_attrs:
                # Add to existing class
                content = re.sub(
                    r'(<body[^>]*class=["\'])([^"\']*)',
                    f'\\1\\2 {class_name}',
                    content
                )
            else:
                # Add new class attribute
                content = re.sub(
                    r'<body([^>]*)>',
                    f'<body\\1 class="{class_name}">',
                    content
                )
        
        return content
    
    def _add_csrf_meta_tag(self, content: str) -> str:
        """Add CSRF token meta tag to template"""
        csrf_tag = '<meta name="csrf-token" content="{{ csrf_token() }}">'
        
        # Try to add in head section
        if '</head>' in content:
            content = content.replace('</head>', f'    {csrf_tag}\n</head>')
        else:
            # Add after opening head tag
            content = re.sub(r'(<head[^>]*>)', f'\\1\n    {csrf_tag}', content)
        
        return content
    
    def integrate_user_management_templates(self) -> Dict[str, Any]:
        """
        Integrate notification system into all user management templates
        
        Returns:
            Dictionary with integration results
        """
        results = {
            'success': True,
            'templates_integrated': [],
            'templates_failed': [],
            'total_changes': []
        }
        
        # Templates to integrate
        templates_to_integrate = [
            ('templates/user_management/profile.html', 'profile'),
            ('templates/user_management/edit_profile.html', 'profile'),
            ('templates/user_management/change_password.html', 'password'),
            ('templates/user_management/delete_profile.html', 'profile'),
            ('templates/caption_settings.html', 'settings'),
            ('admin/templates/admin/user_management.html', 'settings')
        ]
        
        for template_path, page_type in templates_to_integrate:
            if os.path.exists(template_path):
                success, changes = self.integrate_template(template_path, page_type)
                
                if success:
                    results['templates_integrated'].append(template_path)
                    results['total_changes'].extend([f"{template_path}: {change}" for change in changes])
                else:
                    results['templates_failed'].append(template_path)
                    results['success'] = False
                    results['total_changes'].extend([f"{template_path}: {change}" for change in changes])
            else:
                self.logger.warning(f"Template not found: {template_path}")
        
        return results
    
    def create_notification_css(self) -> bool:
        """Create CSS file for notifications if it doesn't exist"""
        try:
            css_path = 'static/css/user_profile_notifications.css'
            
            if os.path.exists(css_path):
                self.logger.info("Notification CSS already exists")
                return True
            
            css_content = """/* User Profile Notifications CSS */

.notification-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    max-width: 400px;
    pointer-events: none;
}

.notification {
    background: white;
    border-left: 4px solid #17a2b8;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 10px;
    padding: 12px 16px;
    pointer-events: auto;
    position: relative;
    animation: slideInRight 0.3s ease-out;
}

.notification.success {
    border-left-color: #28a745;
}

.notification.error {
    border-left-color: #dc3545;
}

.notification.warning {
    border-left-color: #ffc107;
}

.notification.info {
    border-left-color: #17a2b8;
}

.notification.security {
    border-left-color: #dc3545 !important;
    background: #fff5f5;
}

.notification.promotion {
    border-left-color: #28a745 !important;
    background: #f8fff8;
}

.notification.email {
    border-left-color: #17a2b8 !important;
    background: #f0f9ff;
}

.notification.loading {
    border-left-color: #6c757d !important;
    background: #f8f9fa;
}

.notification-header {
    display: flex;
    align-items: center;
    margin-bottom: 4px;
}

.notification-icon {
    margin-right: 8px;
    font-size: 16px;
}

.notification-title {
    font-weight: 600;
    color: #333;
}

.notification-close {
    margin-left: auto;
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: #666;
}

.notification-close:hover {
    color: #333;
}

.notification-message {
    color: #666;
    font-size: 14px;
}

@keyframes slideInRight {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes slideOutRight {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(100%);
        opacity: 0;
    }
}

/* Page-specific styles */
.profile-page .notification-container,
.settings-page .notification-container,
.change-password-page .notification-container {
    top: 80px; /* Account for navigation */
}

/* Mobile responsive */
@media (max-width: 768px) {
    .notification-container {
        left: 10px;
        right: 10px;
        max-width: none;
    }
    
    .notification {
        margin-bottom: 8px;
        padding: 10px 12px;
    }
}
"""
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(css_path), exist_ok=True)
            
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(css_content)
            
            self.logger.info(f"Created notification CSS: {css_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating notification CSS: {e}")
            return False


def main():
    """Main integration function"""
    logging.basicConfig(level=logging.INFO)
    
    print("=== User Profile Template Integration ===")
    print("Integrating unified notification system into user profile templates...")
    
    integrator = UserProfileTemplateIntegrator()
    
    # Create CSS file
    css_created = integrator.create_notification_css()
    print(f"Notification CSS: {'Created' if css_created else 'Failed'}")
    
    # Integrate templates
    results = integrator.integrate_user_management_templates()
    
    print(f"\nIntegration Results:")
    print(f"Success: {results['success']}")
    print(f"Templates integrated: {len(results['templates_integrated'])}")
    print(f"Templates failed: {len(results['templates_failed'])}")
    
    if results['templates_integrated']:
        print(f"\nSuccessfully integrated:")
        for template_path in results['templates_integrated']:
            print(f"  ✓ {template_path}")
    
    if results['templates_failed']:
        print(f"\nFailed to integrate:")
        for template_path in results['templates_failed']:
            print(f"  ✗ {template_path}")
    
    if results['total_changes']:
        print(f"\nChanges made:")
        for change in results['total_changes']:
            print(f"  - {change}")
    
    print(f"\n=== Integration Complete ===")
    return results['success']


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)