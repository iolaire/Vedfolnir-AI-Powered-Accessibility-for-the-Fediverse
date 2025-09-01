// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Notification Integration Helper
 * 
 * Provides easy integration of the NotificationUIRenderer across all pages
 * Includes page-specific configurations and helper methods
 * 
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
 */

class NotificationIntegration {
    constructor() {
        this.renderer = null;
        this.pageType = this.detectPageType();
        this.isInitialized = false;
        
        // Page-specific configurations
        this.pageConfigs = {
            user: {
                position: 'top-right',
                maxNotifications: 5,
                theme: 'modern',
                autoHide: true,
                defaultDuration: 5000
            },
            admin: {
                position: 'top-center',
                maxNotifications: 8,
                theme: 'modern',
                autoHide: false, // Admin notifications stay visible longer
                defaultDuration: 8000,
                showTimestamp: true
            },
            login: {
                position: 'top-center',
                maxNotifications: 3,
                theme: 'minimal',
                autoHide: true,
                defaultDuration: 4000
            },
            error: {
                position: 'top-center',
                maxNotifications: 1,
                theme: 'minimal',
                autoHide: false,
                persistent: true
            }
        };
    }
    
    /**
     * Initialize the notification system for the current page
     */
    init(customOptions = {}) {
        if (this.isInitialized) {
            console.warn('Notification system already initialized');
            return this.renderer;
        }
        
        // Get page-specific configuration
        const pageConfig = this.pageConfigs[this.pageType] || this.pageConfigs.user;
        
        // Merge configurations
        const options = {
            ...pageConfig,
            ...customOptions
        };
        
        // Create renderer
        this.renderer = new NotificationUIRenderer('notification-container', options);
        
        // Setup global notification methods
        this.setupGlobalMethods();
        
        // Setup WebSocket integration
        this.setupWebSocketIntegration();
        
        // Setup page-specific features
        this.setupPageSpecificFeatures();
        
        this.isInitialized = true;
        
        console.log(`Notification system initialized for ${this.pageType} page`);
        
        return this.renderer;
    }
    
    /**
     * Detect the current page type
     */
    detectPageType() {
        const path = window.location.pathname;
        const body = document.body;
        
        // Check for admin pages
        if (path.startsWith('/admin') || body.classList.contains('admin-page')) {
            return 'admin';
        }
        
        // Check for login page
        if (path.includes('/login') || body.classList.contains('login-page')) {
            return 'login';
        }
        
        // Check for error pages
        if (path.includes('/error') || body.classList.contains('error-page') || 
            document.title.toLowerCase().includes('error')) {
            return 'error';
        }
        
        // Default to user page
        return 'user';
    }
    
    /**
     * Setup global notification methods for easy access
     */
    setupGlobalMethods() {
        // Create global Vedfolnir namespace if it doesn't exist
        if (typeof window.Vedfolnir === 'undefined') {
            window.Vedfolnir = {};
        }
        
        // Add notification methods to global namespace
        window.Vedfolnir.notify = (message, type = 'info', options = {}) => {
            return this.renderer.renderNotification({
                message: message,
                type: type,
                ...options
            });
        };
        
        window.Vedfolnir.notifySuccess = (message, options = {}) => {
            return this.renderer.renderNotification({
                message: message,
                type: 'success',
                ...options
            });
        };
        
        window.Vedfolnir.notifyWarning = (message, options = {}) => {
            return this.renderer.renderNotification({
                message: message,
                type: 'warning',
                ...options
            });
        };
        
        window.Vedfolnir.notifyError = (message, options = {}) => {
            return this.renderer.renderNotification({
                message: message,
                type: 'error',
                ...options
            });
        };
        
        window.Vedfolnir.notifyInfo = (message, options = {}) => {
            return this.renderer.renderNotification({
                message: message,
                type: 'info',
                ...options
            });
        };
        
        window.Vedfolnir.showProgress = (message, percentage = 0, options = {}) => {
            return this.renderer.renderProgressUpdate({
                message: message,
                percentage: percentage,
                ...options
            });
        };
        
        window.Vedfolnir.updateProgress = (id, percentage, message = null) => {
            return this.renderer.updateProgressNotification(id, {
                percentage: percentage,
                message: message
            });
        };
        
        window.Vedfolnir.systemAlert = (message, type = 'warning', options = {}) => {
            return this.renderer.renderSystemAlert({
                message: message,
                type: type,
                ...options
            });
        };
        
        window.Vedfolnir.clearNotifications = (type = null) => {
            return this.renderer.clearNotifications(type);
        };
        
        window.Vedfolnir.dismissNotification = (id) => {
            return this.renderer.dismissNotification(id);
        };
        
        // Legacy compatibility methods
        window.Vedfolnir.showToast = window.Vedfolnir.notify;
        window.Vedfolnir.toast = window.Vedfolnir.notify;
    }
    
    /**
     * Setup WebSocket integration for real-time notifications
     */
    setupWebSocketIntegration() {
        // Listen for WebSocket events and convert them to notifications
        document.addEventListener('websocketMessage', (event) => {
            this.handleWebSocketMessage(event.detail);
        });
        
        // Listen for WebSocket connection status changes
        document.addEventListener('websocketStatusChange', (event) => {
            this.handleWebSocketStatusChange(event.detail);
        });
        
        // Listen for progress updates from WebSocket
        document.addEventListener('progressUpdate', (event) => {
            this.handleProgressUpdate(event.detail);
        });
        
        // Listen for task completion events
        document.addEventListener('taskCompleted', (event) => {
            this.handleTaskCompleted(event.detail);
        });
        
        // Listen for task errors
        document.addEventListener('taskError', (event) => {
            this.handleTaskError(event.detail);
        });
    }
    
    /**
     * Handle WebSocket messages and convert to notifications
     */
    handleWebSocketMessage(data) {
        if (!data || !data.type) return;
        
        switch (data.type) {
            case 'user_notification':
                this.renderer.renderNotification({
                    type: data.notification_type || 'info',
                    title: data.title,
                    message: data.message,
                    actions: data.actions || []
                });
                break;
                
            case 'system_notification':
                this.renderer.renderSystemAlert({
                    type: data.alert_type || 'info',
                    title: data.title || 'System Notification',
                    message: data.message,
                    persistent: data.persistent || false
                });
                break;
                
            case 'admin_alert':
                if (this.pageType === 'admin') {
                    this.renderer.renderSystemAlert({
                        type: data.alert_type || 'warning',
                        title: data.title || 'Admin Alert',
                        message: data.message,
                        priority: 'high',
                        persistent: true
                    });
                }
                break;
        }
    }
    
    /**
     * Handle WebSocket connection status changes
     */
    handleWebSocketStatusChange(status) {
        switch (status.state) {
            case 'connected':
                this.renderer.renderNotification({
                    type: 'success',
                    message: 'Real-time connection established',
                    duration: 3000
                });
                break;
                
            case 'disconnected':
                this.renderer.renderNotification({
                    type: 'warning',
                    message: 'Real-time connection lost. Attempting to reconnect...',
                    persistent: true,
                    id: 'websocket-disconnected'
                });
                break;
                
            case 'reconnected':
                // Dismiss the disconnection warning
                this.renderer.dismissNotification('websocket-disconnected');
                this.renderer.renderNotification({
                    type: 'success',
                    message: 'Real-time connection restored',
                    duration: 3000
                });
                break;
                
            case 'error':
                this.renderer.renderNotification({
                    type: 'error',
                    message: status.message || 'Connection error occurred',
                    duration: 8000
                });
                break;
        }
    }
    
    /**
     * Handle progress updates
     */
    handleProgressUpdate(data) {
        const progressId = data.task_id ? `progress-${data.task_id}` : 'progress-default';
        
        this.renderer.renderProgressUpdate({
            id: progressId,
            title: data.title || 'Processing...',
            message: data.message || 'Please wait...',
            percentage: data.percentage || 0,
            label: data.label
        });
    }
    
    /**
     * Handle task completion
     */
    handleTaskCompleted(data) {
        const progressId = data.task_id ? `progress-${data.task_id}` : 'progress-default';
        
        // Dismiss any existing progress notification
        this.renderer.dismissNotification(progressId);
        
        // Show completion notification
        this.renderer.renderNotification({
            type: 'success',
            title: 'Task Completed',
            message: data.message || 'Task completed successfully',
            duration: 5000
        });
    }
    
    /**
     * Handle task errors
     */
    handleTaskError(data) {
        const progressId = data.task_id ? `progress-${data.task_id}` : 'progress-default';
        
        // Dismiss any existing progress notification
        this.renderer.dismissNotification(progressId);
        
        // Show error notification
        this.renderer.renderNotification({
            type: 'error',
            title: 'Task Failed',
            message: data.message || 'An error occurred while processing',
            duration: 10000,
            actions: data.retry_available ? [{
                label: 'Retry',
                action: 'retry',
                type: 'primary'
            }] : []
        });
    }
    
    /**
     * Setup page-specific features
     */
    setupPageSpecificFeatures() {
        switch (this.pageType) {
            case 'admin':
                this.setupAdminFeatures();
                break;
                
            case 'user':
                this.setupUserFeatures();
                break;
                
            case 'login':
                this.setupLoginFeatures();
                break;
        }
    }
    
    /**
     * Setup admin-specific notification features
     */
    setupAdminFeatures() {
        // Listen for system health updates
        document.addEventListener('systemHealthUpdate', (event) => {
            const health = event.detail;
            
            if (health.status === 'critical') {
                this.renderer.renderSystemAlert({
                    type: 'error',
                    title: 'System Health Alert',
                    message: health.message || 'Critical system issue detected',
                    persistent: true,
                    priority: 'critical'
                });
            } else if (health.status === 'warning') {
                this.renderer.renderNotification({
                    type: 'warning',
                    title: 'System Health Warning',
                    message: health.message || 'System performance issue detected',
                    duration: 10000
                });
            }
        });
        
        // Listen for user activity updates
        document.addEventListener('userActivityUpdate', (event) => {
            const activity = event.detail;
            
            if (activity.type === 'login_failure') {
                this.renderer.renderNotification({
                    type: 'warning',
                    title: 'Security Alert',
                    message: `Failed login attempt for user: ${activity.username}`,
                    duration: 8000
                });
            }
        });
    }
    
    /**
     * Setup user-specific notification features
     */
    setupUserFeatures() {
        // Listen for caption generation events
        document.addEventListener('captionGenerated', (event) => {
            const data = event.detail;
            
            this.renderer.renderNotification({
                type: 'success',
                title: 'Caption Generated',
                message: `Caption generated for ${data.filename || 'image'}`,
                duration: 4000
            });
        });
        
        // Listen for platform connection events
        document.addEventListener('platformConnected', (event) => {
            const data = event.detail;
            
            this.renderer.renderNotification({
                type: 'success',
                title: 'Platform Connected',
                message: `Successfully connected to ${data.platform_name}`,
                duration: 5000
            });
        });
        
        document.addEventListener('platformDisconnected', (event) => {
            const data = event.detail;
            
            this.renderer.renderNotification({
                type: 'warning',
                title: 'Platform Disconnected',
                message: `Connection to ${data.platform_name} was lost`,
                duration: 8000
            });
        });
    }
    
    /**
     * Setup login-specific notification features
     */
    setupLoginFeatures() {
        // Listen for authentication events
        document.addEventListener('authenticationFailed', (event) => {
            const data = event.detail;
            
            this.renderer.renderNotification({
                type: 'error',
                title: 'Login Failed',
                message: data.message || 'Invalid username or password',
                duration: 6000
            });
        });
        
        document.addEventListener('authenticationSuccess', (event) => {
            this.renderer.renderNotification({
                type: 'success',
                title: 'Login Successful',
                message: 'Welcome back!',
                duration: 3000
            });
        });
    }
    
    /**
     * Show a notification for form validation errors
     */
    showFormError(message, fieldName = null) {
        const title = fieldName ? `${fieldName} Error` : 'Form Error';
        
        return this.renderer.renderNotification({
            type: 'error',
            title: title,
            message: message,
            duration: 8000
        });
    }
    
    /**
     * Show a notification for form success
     */
    showFormSuccess(message) {
        return this.renderer.renderNotification({
            type: 'success',
            title: 'Success',
            message: message,
            duration: 5000
        });
    }
    
    /**
     * Show a maintenance notification
     */
    showMaintenanceNotification(message, duration = null) {
        return this.renderer.renderSystemAlert({
            type: 'warning',
            title: 'System Maintenance',
            message: message,
            persistent: duration === null,
            duration: duration || 0
        });
    }
    
    /**
     * Get notification statistics
     */
    getStats() {
        return this.renderer ? this.renderer.getStats() : null;
    }
    
    /**
     * Update notification configuration
     */
    updateConfig(newOptions) {
        if (this.renderer) {
            this.renderer.updateOptions(newOptions);
        }
    }
    
    /**
     * Destroy the notification system
     */
    destroy() {
        if (this.renderer) {
            this.renderer.destroy();
            this.renderer = null;
        }
        
        // Clean up global methods
        if (window.Vedfolnir) {
            delete window.Vedfolnir.notify;
            delete window.Vedfolnir.notifySuccess;
            delete window.Vedfolnir.notifyWarning;
            delete window.Vedfolnir.notifyError;
            delete window.Vedfolnir.notifyInfo;
            delete window.Vedfolnir.showProgress;
            delete window.Vedfolnir.updateProgress;
            delete window.Vedfolnir.systemAlert;
            delete window.Vedfolnir.clearNotifications;
            delete window.Vedfolnir.dismissNotification;
            delete window.Vedfolnir.showToast;
            delete window.Vedfolnir.toast;
        }
        
        this.isInitialized = false;
        
        console.log('Notification system destroyed');
    }
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Create global notification integration instance
    window.VedfolnirNotifications = new NotificationIntegration();
    
    // Auto-initialize unless explicitly disabled
    if (!window.DISABLE_AUTO_NOTIFICATIONS) {
        window.VedfolnirNotifications.init();
    }
});

// Export for manual initialization
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationIntegration;
} else if (typeof window !== 'undefined') {
    window.NotificationIntegration = NotificationIntegration;
}