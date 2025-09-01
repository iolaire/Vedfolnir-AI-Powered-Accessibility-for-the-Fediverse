// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * User Profile Notifications Client
 * 
 * Handles real-time WebSocket notifications for user profile and settings pages.
 * Integrates with the unified notification system to provide consistent notification
 * display and behavior across user management features.
 */

class UserProfileNotificationClient {
    constructor(options = {}) {
        this.options = {
            namespace: '/',
            autoConnect: true,
            notificationContainer: '#notification-container',
            maxNotifications: 5,
            autoHideDelay: 5000,
            enableSound: false,
            ...options
        };
        
        this.socket = null;
        this.connected = false;
        this.notifications = [];
        this.notificationContainer = null;
        
        this.init();
    }
    
    init() {
        console.log('Initializing User Profile Notification Client...');
        
        // Create notification container if it doesn't exist
        this.createNotificationContainer();
        
        // Initialize WebSocket connection
        if (this.options.autoConnect) {
            this.connect();
        }
        
        // Set up page-specific event handlers
        this.setupPageEventHandlers();
        
        console.log('User Profile Notification Client initialized');
    }
    
    createNotificationContainer() {
        this.notificationContainer = document.querySelector(this.options.notificationContainer);
        
        if (!this.notificationContainer) {
            // Create notification container
            this.notificationContainer = document.createElement('div');
            this.notificationContainer.id = 'notification-container';
            this.notificationContainer.className = 'notification-container';
            
            // Add CSS styles
            this.notificationContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
                pointer-events: none;
            `;
            
            document.body.appendChild(this.notificationContainer);
        }
    }
    
    connect() {
        if (typeof io === 'undefined') {
            console.error('Socket.IO not loaded');
            return;
        }
        
        try {
            this.socket = io(this.options.namespace, {
                transports: ['websocket', 'polling'],
                upgrade: true,
                rememberUpgrade: true
            });
            
            this.setupSocketEventHandlers();
            
        } catch (error) {
            console.error('Failed to connect to WebSocket:', error);
        }
    }
    
    setupSocketEventHandlers() {
        this.socket.on('connect', () => {
            console.log('Connected to notification WebSocket');
            this.connected = true;
            this.onConnect();
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from notification WebSocket');
            this.connected = false;
            this.onDisconnect();
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.onConnectionError(error);
        });
        
        // User profile notification events
        this.socket.on('user_notification', (data) => {
            this.handleUserNotification(data);
        });
        
        this.socket.on('profile_update_notification', (data) => {
            this.handleProfileUpdateNotification(data);
        });
        
        this.socket.on('settings_change_notification', (data) => {
            this.handleSettingsChangeNotification(data);
        });
        
        this.socket.on('password_change_notification', (data) => {
            this.handlePasswordChangeNotification(data);
        });
        
        this.socket.on('account_status_notification', (data) => {
            this.handleAccountStatusNotification(data);
        });
        
        this.socket.on('permission_change_notification', (data) => {
            this.handlePermissionChangeNotification(data);
        });
        
        this.socket.on('email_verification_notification', (data) => {
            this.handleEmailVerificationNotification(data);
        });
    }
    
    setupPageEventHandlers() {
        // Handle form submissions for real-time feedback
        this.setupFormHandlers();
        
        // Handle page-specific events
        this.setupProfilePageHandlers();
        this.setupSettingsPageHandlers();
        
        // Handle page unload cleanup
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }
    
    setupFormHandlers() {
        // Profile update forms
        const profileForms = document.querySelectorAll('form[action*="profile"], form[action*="edit_profile"]');
        profileForms.forEach(form => {
            form.addEventListener('submit', (event) => {
                this.showLoadingNotification('Updating profile...');
            });
        });
        
        // Settings forms
        const settingsForms = document.querySelectorAll('form[action*="settings"], form[action*="caption_settings"]');
        settingsForms.forEach(form => {
            form.addEventListener('submit', (event) => {
                this.showLoadingNotification('Saving settings...');
            });
        });
        
        // Password change forms
        const passwordForms = document.querySelectorAll('form[action*="password"], form[action*="change_password"]');
        passwordForms.forEach(form => {
            form.addEventListener('submit', (event) => {
                this.showLoadingNotification('Changing password...');
            });
        });
    }
    
    setupProfilePageHandlers() {
        // Profile-specific event handlers
        const profilePage = document.querySelector('.profile-page, .edit-profile-page');
        if (profilePage) {
            console.log('Setting up profile page handlers');
            
            // Handle profile image uploads
            const imageUpload = document.querySelector('input[type="file"][name*="image"]');
            if (imageUpload) {
                imageUpload.addEventListener('change', () => {
                    this.showInfoNotification('Profile image selected. Save to apply changes.');
                });
            }
        }
    }
    
    setupSettingsPageHandlers() {
        // Settings-specific event handlers
        const settingsPage = document.querySelector('.settings-page, .caption-settings-page');
        if (settingsPage) {
            console.log('Setting up settings page handlers');
            
            // Handle settings changes
            const settingsInputs = settingsPage.querySelectorAll('input, select, textarea');
            settingsInputs.forEach(input => {
                input.addEventListener('change', () => {
                    this.showInfoNotification('Settings changed. Save to apply changes.');
                });
            });
        }
    }
    
    // Notification handlers
    handleUserNotification(data) {
        console.log('Received user notification:', data);
        this.displayNotification(data);
    }
    
    handleProfileUpdateNotification(data) {
        console.log('Received profile update notification:', data);
        
        // Clear any loading notifications
        this.clearLoadingNotifications();
        
        // Display the notification
        this.displayNotification({
            ...data,
            icon: data.success ? '✓' : '✗',
            className: data.success ? 'success' : 'error'
        });
        
        // Refresh profile data if successful
        if (data.success) {
            this.refreshProfileData();
        }
    }
    
    handleSettingsChangeNotification(data) {
        console.log('Received settings change notification:', data);
        
        // Clear any loading notifications
        this.clearLoadingNotifications();
        
        // Display the notification
        this.displayNotification({
            ...data,
            icon: data.success ? '⚙️' : '✗',
            className: data.success ? 'success' : 'error'
        });
        
        // Update settings display if successful
        if (data.success && data.setting_name) {
            this.updateSettingsDisplay(data.setting_name, data.new_value);
        }
    }
    
    handlePasswordChangeNotification(data) {
        console.log('Received password change notification:', data);
        
        // Clear any loading notifications
        this.clearLoadingNotifications();
        
        // Display the notification with security emphasis
        this.displayNotification({
            ...data,
            icon: data.success ? '🔒' : '⚠️',
            className: data.success ? 'success security' : 'error security',
            priority: 'high'
        });
        
        // Clear password form if successful
        if (data.success) {
            this.clearPasswordForms();
        }
    }
    
    handleAccountStatusNotification(data) {
        console.log('Received account status notification:', data);
        
        // Display the notification
        this.displayNotification({
            ...data,
            icon: this.getStatusIcon(data.status_change),
            className: this.getStatusClass(data.status_change),
            priority: 'high'
        });
        
        // Handle specific status changes
        if (data.status_change === 'logout') {
            // Redirect to login page after a delay
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        }
    }
    
    handlePermissionChangeNotification(data) {
        console.log('Received permission change notification:', data);
        
        // Display the notification
        this.displayNotification({
            ...data,
            icon: data.is_promotion ? '⬆️' : '⬇️',
            className: data.is_promotion ? 'success promotion' : 'info demotion',
            priority: 'high'
        });
        
        // Refresh page to update UI permissions
        setTimeout(() => {
            window.location.reload();
        }, 3000);
    }
    
    handleEmailVerificationNotification(data) {
        console.log('Received email verification notification:', data);
        
        // Display the notification
        this.displayNotification({
            ...data,
            icon: data.success ? '📧' : '⚠️',
            className: data.success ? 'success email' : 'error email'
        });
        
        // Update email verification status display
        if (data.success) {
            this.updateEmailVerificationStatus(true);
        }
    }
    
    // Notification display methods
    displayNotification(data) {
        const notification = this.createNotificationElement(data);
        this.addNotificationToContainer(notification);
        
        // Auto-hide if configured
        if (this.options.autoHideDelay > 0 && !data.requires_action) {
            setTimeout(() => {
                this.removeNotification(notification);
            }, this.options.autoHideDelay);
        }
        
        // Play sound if enabled
        if (this.options.enableSound) {
            this.playNotificationSound(data.type);
        }
    }
    
    createNotificationElement(data) {
        const notification = document.createElement('div');
        notification.className = `notification ${data.className || data.type || 'info'}`;
        notification.style.cssText = `
            background: white;
            border-left: 4px solid ${this.getTypeColor(data.type)};
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 10px;
            padding: 12px 16px;
            pointer-events: auto;
            position: relative;
            animation: slideInRight 0.3s ease-out;
        `;
        
        const icon = data.icon || this.getTypeIcon(data.type);
        const title = data.title || 'Notification';
        const message = data.message || '';
        
        notification.innerHTML = `
            <div class="notification-header" style="display: flex; align-items: center; margin-bottom: 4px;">
                <span class="notification-icon" style="margin-right: 8px; font-size: 16px;">${icon}</span>
                <span class="notification-title" style="font-weight: 600; color: #333;">${title}</span>
                <button class="notification-close" style="margin-left: auto; background: none; border: none; font-size: 18px; cursor: pointer; color: #666;">&times;</button>
            </div>
            <div class="notification-message" style="color: #666; font-size: 14px;">${message}</div>
        `;
        
        // Add close handler
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            this.removeNotification(notification);
        });
        
        return notification;
    }
    
    addNotificationToContainer(notification) {
        this.notificationContainer.appendChild(notification);
        this.notifications.push(notification);
        
        // Remove oldest notifications if we exceed the limit
        while (this.notifications.length > this.options.maxNotifications) {
            const oldest = this.notifications.shift();
            this.removeNotification(oldest);
        }
    }
    
    removeNotification(notification) {
        if (notification && notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
        
        // Remove from tracking array
        const index = this.notifications.indexOf(notification);
        if (index > -1) {
            this.notifications.splice(index, 1);
        }
    }
    
    // Utility methods
    showLoadingNotification(message) {
        this.displayNotification({
            type: 'info',
            title: 'Processing...',
            message: message,
            icon: '⏳',
            className: 'loading',
            isLoading: true
        });
    }
    
    showInfoNotification(message) {
        this.displayNotification({
            type: 'info',
            title: 'Information',
            message: message,
            icon: 'ℹ️'
        });
    }
    
    clearLoadingNotifications() {
        const loadingNotifications = this.notificationContainer.querySelectorAll('.notification.loading');
        loadingNotifications.forEach(notification => {
            this.removeNotification(notification);
        });
    }
    
    clearPasswordForms() {
        const passwordInputs = document.querySelectorAll('input[type="password"]');
        passwordInputs.forEach(input => {
            input.value = '';
        });
    }
    
    refreshProfileData() {
        // Refresh profile data display without full page reload
        const profileData = document.querySelector('.profile-data');
        if (profileData) {
            // Could implement AJAX refresh here
            console.log('Profile data refresh would happen here');
        }
    }
    
    updateSettingsDisplay(settingName, newValue) {
        // Update settings display to reflect new values
        const settingElement = document.querySelector(`[data-setting="${settingName}"]`);
        if (settingElement) {
            settingElement.textContent = newValue;
        }
    }
    
    updateEmailVerificationStatus(verified) {
        const statusElements = document.querySelectorAll('.email-verification-status');
        statusElements.forEach(element => {
            element.textContent = verified ? 'Verified' : 'Not Verified';
            element.className = verified ? 'verified' : 'not-verified';
        });
    }
    
    getTypeColor(type) {
        const colors = {
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        };
        return colors[type] || colors.info;
    }
    
    getTypeIcon(type) {
        const icons = {
            'success': '✓',
            'error': '✗',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        return icons[type] || icons.info;
    }
    
    getStatusIcon(statusChange) {
        const icons = {
            'login': '🔓',
            'logout': '🔒',
            'activated': '✅',
            'deactivated': '❌',
            'locked': '🔒',
            'unlocked': '🔓',
            'verified': '✅'
        };
        return icons[statusChange] || 'ℹ️';
    }
    
    getStatusClass(statusChange) {
        if (['activated', 'unlocked', 'verified', 'login'].includes(statusChange)) {
            return 'success';
        } else if (['deactivated', 'locked', 'login_failed'].includes(statusChange)) {
            return 'error';
        } else {
            return 'info';
        }
    }
    
    playNotificationSound(type) {
        // Could implement sound notifications here
        console.log(`Playing ${type} notification sound`);
    }
    
    // Connection event handlers
    onConnect() {
        console.log('WebSocket connected for user profile notifications');
        
        // Show connection status
        this.displayNotification({
            type: 'success',
            title: 'Connected',
            message: 'Real-time notifications enabled',
            icon: '🔗'
        });
    }
    
    onDisconnect() {
        console.log('WebSocket disconnected for user profile notifications');
        
        // Show disconnection status
        this.displayNotification({
            type: 'warning',
            title: 'Disconnected',
            message: 'Real-time notifications disabled. Trying to reconnect...',
            icon: '🔌'
        });
    }
    
    onConnectionError(error) {
        console.error('WebSocket connection error:', error);
        
        // Show error status
        this.displayNotification({
            type: 'error',
            title: 'Connection Error',
            message: 'Failed to connect to notification service',
            icon: '⚠️'
        });
    }
    
    cleanup() {
        if (this.socket) {
            this.socket.disconnect();
        }
        
        // Clear all notifications
        this.notifications.forEach(notification => {
            this.removeNotification(notification);
        });
    }
}

// CSS animations
const style = document.createElement('style');
style.textContent = `
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
`;
document.head.appendChild(style);

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a user profile or settings page
    const isProfilePage = document.querySelector('.profile-page, .edit-profile-page, .settings-page, .caption-settings-page, .change-password-page');
    
    if (isProfilePage) {
        console.log('Initializing user profile notifications...');
        window.userProfileNotifications = new UserProfileNotificationClient({
            autoConnect: true,
            enableSound: false,
            maxNotifications: 3,
            autoHideDelay: 5000
        });
    }
});