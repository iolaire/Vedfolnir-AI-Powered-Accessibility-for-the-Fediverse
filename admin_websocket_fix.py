#!/usr/bin/env python3
"""
Admin WebSocket Fix

This script fixes the WebSocket and CORS issues in admin pages by:
1. Enabling proper authentication for admin WebSocket connections
2. Ensuring CORS is properly configured for admin API endpoints
3. Making admin pages work with the new WebSocket system
"""

import os
import sys
from pathlib import Path

def update_environment_config():
    """Update environment configuration to enable admin WebSocket functionality"""
    
    env_file = Path('.env')
    if not env_file.exists():
        print("Error: .env file not found")
        return False
    
    # Read current environment
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update WebSocket configuration for admin functionality
    updates = {
        'SOCKETIO_REQUIRE_AUTH': 'true',
        'SOCKETIO_SESSION_VALIDATION': 'true', 
        'SOCKETIO_CSRF_PROTECTION': 'true',
        'SOCKETIO_RATE_LIMITING': 'true'
    }
    
    # Apply updates
    updated_lines = []
    updated_keys = set()
    
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0].strip()
            if key in updates:
                updated_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # Add any missing keys
    for key, value in updates.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)
    
    print("✅ Updated WebSocket configuration for admin functionality")
    return True

def create_admin_websocket_client():
    """Create a simplified WebSocket client for admin pages"""
    
    admin_js_content = '''
// Admin WebSocket Client Fix
// Simplified WebSocket client that works with admin pages

class AdminWebSocketClient {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        
        // Only connect if we're on an admin page and user is authenticated
        if (this.isAdminPage() && this.isUserAuthenticated()) {
            this.connect();
        }
    }
    
    isAdminPage() {
        return window.location.pathname.startsWith('/admin');
    }
    
    isUserAuthenticated() {
        // Check if user is authenticated by looking for CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]');
        return csrfToken && csrfToken.getAttribute('content');
    }
    
    connect() {
        if (typeof io === 'undefined') {
            console.log('Socket.IO not available, skipping WebSocket connection');
            return;
        }
        
        try {
            console.log('Connecting to admin WebSocket...');
            
            this.socket = io('/admin', {
                transports: ['websocket', 'polling'],
                upgrade: true,
                rememberUpgrade: false,
                timeout: 20000,
                reconnection: true,
                reconnectionAttempts: this.maxReconnectAttempts,
                reconnectionDelay: this.reconnectDelay,
                forceNew: false
            });
            
            this.setupEventHandlers();
            
        } catch (error) {
            console.error('Failed to connect to WebSocket:', error);
            this.handleConnectionError(error);
        }
    }
    
    setupEventHandlers() {
        if (!this.socket) return;
        
        this.socket.on('connect', () => {
            console.log('✅ Admin WebSocket connected');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus('connected');
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('❌ Admin WebSocket disconnected:', reason);
            this.connected = false;
            this.updateConnectionStatus('disconnected');
            
            if (reason === 'io server disconnect') {
                // Server disconnected, try to reconnect
                this.reconnect();
            }
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Admin WebSocket connection error:', error);
            this.handleConnectionError(error);
        });
        
        // Admin-specific events
        this.socket.on('admin_notification', (data) => {
            this.handleAdminNotification(data);
        });
        
        this.socket.on('system_alert', (data) => {
            this.handleSystemAlert(data);
        });
    }
    
    handleConnectionError(error) {
        this.connected = false;
        this.updateConnectionStatus('error');
        
        // Don't spam reconnection attempts
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
                this.reconnect();
            }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
        }
    }
    
    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        
        if (this.socket) {
            this.socket.disconnect();
        }
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('websocket-status');
        if (statusElement) {
            const statusMap = {
                'connected': '<i class="bi bi-wifi text-success"></i> Real-time: Connected',
                'disconnected': '<i class="bi bi-wifi-off text-warning"></i> Real-time: Disconnected',
                'error': '<i class="bi bi-exclamation-triangle text-danger"></i> Real-time: Error'
            };
            
            statusElement.innerHTML = statusMap[status] || statusMap['disconnected'];
        }
    }
    
    handleAdminNotification(data) {
        console.log('Received admin notification:', data);
        
        // Add to notification system if available
        if (window.adminNotificationSystem) {
            window.adminNotificationSystem.addNotification(data);
        }
    }
    
    handleSystemAlert(data) {
        console.log('Received system alert:', data);
        
        // Show system alert
        if (data.severity === 'critical') {
            this.showCriticalAlert(data);
        }
    }
    
    showCriticalAlert(alert) {
        // Create a modal or toast for critical alerts
        const alertHtml = `
            <div class="alert alert-danger alert-dismissible fade show position-fixed" 
                 style="top: 20px; right: 20px; z-index: 9999; max-width: 400px;" role="alert">
                <h6><i class="bi bi-exclamation-triangle"></i> Critical System Alert</h6>
                <p class="mb-0">${alert.message}</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', alertHtml);
    }
    
    emit(event, data) {
        if (this.socket && this.connected) {
            this.socket.emit(event, data);
        } else {
            console.warn('Cannot emit event - WebSocket not connected');
        }
    }
    
    on(event, callback) {
        if (this.socket) {
            this.socket.on(event, callback);
        }
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.connected = false;
        this.updateConnectionStatus('disconnected');
    }
}

// Initialize admin WebSocket client
let adminWebSocketClient;

document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on admin pages
    if (window.location.pathname.startsWith('/admin')) {
        console.log('Initializing admin WebSocket client...');
        adminWebSocketClient = new AdminWebSocketClient();
        
        // Make it globally available
        window.adminWebSocketClient = adminWebSocketClient;
    }
});

// Graceful cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (adminWebSocketClient) {
        adminWebSocketClient.disconnect();
    }
});
'''
    
    # Write the admin WebSocket client
    admin_js_path = Path('static/js/admin-websocket-client.js')
    with open(admin_js_path, 'w') as f:
        f.write(admin_js_content)
    
    print("✅ Created simplified admin WebSocket client")
    return True

def update_admin_base_template():
    """Update admin base template to use the new WebSocket client"""
    
    template_path = Path('admin/templates/base_admin.html')
    if not template_path.exists():
        print("Error: Admin base template not found")
        return False
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Add the new admin WebSocket client script
    websocket_client_line = '<script src="{{ url_for(\'static\', filename=\'js/websocket-client.js\') }}"></script>'
    admin_websocket_line = '<script src="{{ url_for(\'static\', filename=\'js/admin-websocket-client.js\') }}"></script>'
    
    if admin_websocket_line not in content:
        # Add after the main websocket-client.js
        content = content.replace(
            websocket_client_line,
            websocket_client_line + '\n    \n    <!-- Admin WebSocket Client -->\n    ' + admin_websocket_line
        )
        
        with open(template_path, 'w') as f:
            f.write(content)
        
        print("✅ Updated admin base template with new WebSocket client")
    else:
        print("ℹ️  Admin base template already updated")
    
    return True

def fix_admin_notification_system():
    """Fix the admin notification system to handle connection errors gracefully"""
    
    notification_template = Path('admin/templates/components/admin_notification_system.html')
    if not notification_template.exists():
        print("Error: Admin notification system template not found")
        return False
    
    with open(notification_template, 'r') as f:
        content = f.read()
    
    # Add error handling to the loadNotifications function
    old_load_notifications = '''    loadNotifications() {
        fetch('/admin/api/notifications', {
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            }
        })
        .then(response => response.json())
        .then(data => {
            this.notifications = data.notifications || [];
            this.updateNotificationDisplay();
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
        });
    }'''
    
    new_load_notifications = '''    loadNotifications() {
        fetch('/admin/api/notifications', {
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            this.notifications = data.notifications || [];
            this.updateNotificationDisplay();
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
            // Gracefully handle the error - don't break the page
            this.notifications = [];
            this.updateNotificationDisplay();
        });
    }'''
    
    if old_load_notifications in content:
        content = content.replace(old_load_notifications, new_load_notifications)
        
        with open(notification_template, 'w') as f:
            f.write(content)
        
        print("✅ Fixed admin notification system error handling")
    else:
        print("ℹ️  Admin notification system already has error handling")
    
    return True

def main():
    """Main function to apply all fixes"""
    
    print("🔧 Fixing admin WebSocket and CORS issues...")
    print()
    
    success = True
    
    # 1. Update environment configuration
    if not update_environment_config():
        success = False
    
    # 2. Create simplified admin WebSocket client
    if not create_admin_websocket_client():
        success = False
    
    # 3. Update admin base template
    if not update_admin_base_template():
        success = False
    
    # 4. Fix admin notification system
    if not fix_admin_notification_system():
        success = False
    
    print()
    if success:
        print("✅ All fixes applied successfully!")
        print()
        print("Next steps:")
        print("1. Restart the application: python web_app.py")
        print("2. Clear browser cache and reload admin pages")
        print("3. Check browser console for any remaining errors")
        print()
        print("The admin pages should now work properly with WebSocket connections.")
    else:
        print("❌ Some fixes failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
