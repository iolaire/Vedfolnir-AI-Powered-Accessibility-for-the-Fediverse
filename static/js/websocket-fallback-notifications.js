// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * WebSocket Fallback Notification System
 * 
 * Provides multiple fallback mechanisms for notifying users when primary
 * notification systems fail or are unavailable.
 */

class WebSocketFallbackNotifications {
    constructor(options = {}) {
        this.options = this._mergeOptions(options);
        this.logger = console;
        
        // Notification state
        this.state = {
            availableMethods: [],
            lastNotification: null,
            notificationQueue: [],
            isProcessingQueue: false
        };
        
        // Initialize available methods
        this._detectAvailableMethods();
        
        this.logger.log('WebSocket Fallback Notifications initialized');
    }
    
    /**
     * Merge options with defaults
     */
    _mergeOptions(userOptions) {
        const defaults = {
            // Method preferences (in order of preference)
            preferredMethods: ['toast', 'notification', 'banner', 'console', 'title', 'favicon'],
            
            // Method-specific options
            toast: {
                duration: 5000,
                position: 'top-right',
                enableBootstrap: true
            },
            
            notification: {
                requirePermission: true,
                icon: '/static/favicons/favicon-32x32.png',
                duration: 5000
            },
            
            banner: {
                position: 'top',
                autoHide: true,
                duration: 8000
            },
            
            console: {
                enableColors: true,
                enableGrouping: true
            },
            
            title: {
                blinkDuration: 10000,
                originalTitle: document.title
            },
            
            favicon: {
                errorIcon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><circle cx="8" cy="8" r="8" fill="red"/><text x="8" y="12" text-anchor="middle" fill="white" font-size="10">!</text></svg>',
                warningIcon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><circle cx="8" cy="8" r="8" fill="orange"/><text x="8" y="12" text-anchor="middle" fill="white" font-size="10">?</text></svg>',
                originalIcon: null
            },
            
            // Queue options
            enableQueue: true,
            maxQueueSize: 10,
            queueProcessingDelay: 1000
        };
        
        return { ...defaults, ...userOptions };
    }
}    
  
  /**
     * Detect available notification methods
     */
    _detectAvailableMethods() {
        this.state.availableMethods = [];
        
        // Check for Bootstrap Toast
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            this.state.availableMethods.push('toast');
        }
        
        // Check for Web Notifications API
        if ('Notification' in window) {
            this.state.availableMethods.push('notification');
        }
        
        // Banner is always available (we create it)
        this.state.availableMethods.push('banner');
        
        // Console is always available
        this.state.availableMethods.push('console');
        
        // Title manipulation is always available
        this.state.availableMethods.push('title');
        
        // Favicon manipulation is always available
        this.state.availableMethods.push('favicon');
        
        this.logger.log('Available notification methods:', this.state.availableMethods);
    }
    
    /**
     * Send notification using fallback methods
     */
    async notify(message, type = 'info', options = {}) {
        const notification = {
            message,
            type,
            options: { ...options },
            timestamp: Date.now(),
            id: this._generateNotificationId()
        };
        
        // Add to queue if enabled
        if (this.options.enableQueue) {
            this._addToQueue(notification);
        }
        
        // Try to send immediately
        return this._sendNotification(notification);
    }
    
    /**
     * Send notification using available methods
     */
    async _sendNotification(notification) {
        const { message, type, options } = notification;
        
        // Get ordered methods based on preferences and availability
        const methods = this._getOrderedMethods();
        
        let success = false;
        
        for (const method of methods) {
            try {
                const result = await this._sendUsingMethod(method, message, type, options);
                if (result) {
                    success = true;
                    this.logger.log(`Notification sent using ${method}:`, message);
                    break;
                }
            } catch (error) {
                this.logger.warn(`Failed to send notification using ${method}:`, error);
            }
        }
        
        if (!success) {
            this.logger.error('All notification methods failed for:', message);
        }
        
        this.state.lastNotification = notification;
        return success;
    }
    
    /**
     * Send notification using specific method
     */
    async _sendUsingMethod(method, message, type, options) {
        switch (method) {
            case 'toast':
                return this._sendToast(message, type, options);
            case 'notification':
                return this._sendWebNotification(message, type, options);
            case 'banner':
                return this._sendBanner(message, type, options);
            case 'console':
                return this._sendConsole(message, type, options);
            case 'title':
                return this._sendTitle(message, type, options);
            case 'favicon':
                return this._sendFavicon(message, type, options);
            default:
                return false;
        }
    }
    
    /**
     * Send Bootstrap toast notification
     */
    _sendToast(message, type, options) {
        if (typeof bootstrap === 'undefined' || !bootstrap.Toast) {
            return false;
        }
        
        const toastConfig = { ...this.options.toast, ...options };
        
        // Create toast container if it doesn't exist
        let container = document.getElementById('fallback-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'fallback-toast-container';
            container.className = `toast-container position-fixed ${toastConfig.position}`;
            container.style.zIndex = '1060';
            document.body.appendChild(container);
        }
        
        // Create toast element
        const toastId = `toast-${Date.now()}`;
        const toastHTML = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header">
                    <i class="bi ${this._getTypeIcon(type)} me-2 text-${this._getTypeColor(type)}"></i>
                    <strong class="me-auto">WebSocket</strong>
                    <small class="text-muted">now</small>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', toastHTML);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            delay: toastConfig.duration
        });
        
        toast.show();
        
        // Remove element after hiding
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
        
        return true;
    }
    
    /**
     * Send Web Notification
     */
    async _sendWebNotification(message, type, options) {
        if (!('Notification' in window)) {
            return false;
        }
        
        const notificationConfig = { ...this.options.notification, ...options };
        
        // Request permission if needed
        if (notificationConfig.requirePermission && Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            if (permission !== 'granted') {
                return false;
            }
        }
        
        if (Notification.permission !== 'granted') {
            return false;
        }
        
        const notification = new Notification(`WebSocket ${type.toUpperCase()}`, {
            body: message,
            icon: notificationConfig.icon,
            tag: 'websocket-notification',
            requireInteraction: type === 'error'
        });
        
        // Auto-close after duration
        setTimeout(() => {
            notification.close();
        }, notificationConfig.duration);
        
        return true;
    }
    
    /**
     * Send banner notification
     */
    _sendBanner(message, type, options) {
        const bannerConfig = { ...this.options.banner, ...options };
        
        // Remove existing banner
        const existingBanner = document.getElementById('fallback-notification-banner');
        if (existingBanner) {
            existingBanner.remove();
        }
        
        // Create banner
        const banner = document.createElement('div');
        banner.id = 'fallback-notification-banner';
        banner.className = `alert alert-${this._getTypeColor(type)} alert-dismissible fade show`;
        banner.style.cssText = `
            position: fixed;
            ${bannerConfig.position}: 0;
            left: 0;
            right: 0;
            z-index: 1055;
            margin: 0;
            border-radius: 0;
            text-align: center;
        `;
        
        banner.innerHTML = `
            <i class="bi ${this._getTypeIcon(type)} me-2"></i>
            <strong>WebSocket:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        document.body.appendChild(banner);
        
        // Auto-hide if enabled
        if (bannerConfig.autoHide) {
            setTimeout(() => {
                if (banner.parentNode) {
                    banner.remove();
                }
            }, bannerConfig.duration);
        }
        
        return true;
    }
    
    /**
     * Send console notification
     */
    _sendConsole(message, type, options) {
        const consoleConfig = { ...this.options.console, ...options };
        
        const consoleMethod = type === 'error' ? 'error' : 
                            type === 'warning' ? 'warn' : 'log';
        
        if (consoleConfig.enableGrouping) {
            console.group(`WebSocket ${type.toUpperCase()}`);
        }
        
        if (consoleConfig.enableColors && console[consoleMethod]) {
            const colors = {
                error: 'color: #dc3545; font-weight: bold;',
                warning: 'color: #fd7e14; font-weight: bold;',
                info: 'color: #0d6efd;',
                success: 'color: #198754;'
            };
            
            console[consoleMethod](`%c${message}`, colors[type] || colors.info);
        } else {
            console[consoleMethod](`WebSocket ${type}: ${message}`);
        }
        
        if (consoleConfig.enableGrouping) {
            console.groupEnd();
        }
        
        return true;
    }
    
    /**
     * Send title notification (blink title)
     */
    _sendTitle(message, type, options) {
        const titleConfig = { ...this.options.title, ...options };
        
        const originalTitle = titleConfig.originalTitle || document.title;
        const notificationTitle = `[${type.toUpperCase()}] ${message}`;
        
        let blinkCount = 0;
        const maxBlinks = Math.floor(titleConfig.blinkDuration / 1000);
        
        const blinkInterval = setInterval(() => {
            document.title = blinkCount % 2 === 0 ? notificationTitle : originalTitle;
            blinkCount++;
            
            if (blinkCount >= maxBlinks * 2) {
                clearInterval(blinkInterval);
                document.title = originalTitle;
            }
        }, 500);
        
        return true;
    }
    
    /**
     * Send favicon notification
     */
    _sendFavicon(message, type, options) {
        const faviconConfig = { ...this.options.favicon, ...options };
        
        // Store original favicon if not already stored
        if (!faviconConfig.originalIcon) {
            const existingIcon = document.querySelector('link[rel="icon"]') || 
                                document.querySelector('link[rel="shortcut icon"]');
            faviconConfig.originalIcon = existingIcon ? existingIcon.href : null;
        }
        
        // Get appropriate icon for type
        let iconUrl;
        if (type === 'error') {
            iconUrl = faviconConfig.errorIcon;
        } else if (type === 'warning') {
            iconUrl = faviconConfig.warningIcon;
        } else {
            return true; // Don't change favicon for info/success
        }
        
        // Update favicon
        this._updateFavicon(iconUrl);
        
        // Restore original favicon after delay
        setTimeout(() => {
            if (faviconConfig.originalIcon) {
                this._updateFavicon(faviconConfig.originalIcon);
            }
        }, 10000);
        
        return true;
    }
    
    /**
     * Update favicon
     */
    _updateFavicon(iconUrl) {
        // Remove existing favicon links
        const existingIcons = document.querySelectorAll('link[rel="icon"], link[rel="shortcut icon"]');
        existingIcons.forEach(icon => icon.remove());
        
        // Add new favicon
        const link = document.createElement('link');
        link.rel = 'icon';
        link.href = iconUrl;
        document.head.appendChild(link);
    }
    
    /**
     * Get ordered methods based on preferences and availability
     */
    _getOrderedMethods() {
        return this.options.preferredMethods.filter(method => 
            this.state.availableMethods.includes(method)
        );
    }
    
    /**
     * Get icon for notification type
     */
    _getTypeIcon(type) {
        const icons = {
            error: 'bi-exclamation-triangle',
            warning: 'bi-exclamation-circle',
            info: 'bi-info-circle',
            success: 'bi-check-circle'
        };
        return icons[type] || icons.info;
    }
    
    /**
     * Get color for notification type
     */
    _getTypeColor(type) {
        const colors = {
            error: 'danger',
            warning: 'warning',
            info: 'info',
            success: 'success'
        };
        return colors[type] || colors.info;
    }
    
    /**
     * Add notification to queue
     */
    _addToQueue(notification) {
        this.state.notificationQueue.push(notification);
        
        // Limit queue size
        if (this.state.notificationQueue.length > this.options.maxQueueSize) {
            this.state.notificationQueue.shift();
        }
        
        // Process queue if not already processing
        if (!this.state.isProcessingQueue) {
            this._processQueue();
        }
    }
    
    /**
     * Process notification queue
     */
    async _processQueue() {
        if (this.state.isProcessingQueue || this.state.notificationQueue.length === 0) {
            return;
        }
        
        this.state.isProcessingQueue = true;
        
        while (this.state.notificationQueue.length > 0) {
            const notification = this.state.notificationQueue.shift();
            
            try {
                await this._sendNotification(notification);
            } catch (error) {
                this.logger.error('Error processing queued notification:', error);
            }
            
            // Delay between notifications
            if (this.state.notificationQueue.length > 0) {
                await this._delay(this.options.queueProcessingDelay);
            }
        }
        
        this.state.isProcessingQueue = false;
    }
    
    /**
     * Generate unique notification ID
     */
    _generateNotificationId() {
        return `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Utility delay function
     */
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Request notification permissions
     */
    async requestPermissions() {
        const results = {};
        
        // Web Notifications
        if ('Notification' in window && Notification.permission === 'default') {
            try {
                results.webNotification = await Notification.requestPermission();
            } catch (error) {
                results.webNotification = 'denied';
            }
        } else {
            results.webNotification = Notification.permission || 'not-supported';
        }
        
        return results;
    }
    
    /**
     * Test all notification methods
     */
    async testAllMethods() {
        const results = {};
        
        for (const method of this.state.availableMethods) {
            try {
                const success = await this._sendUsingMethod(
                    method, 
                    `Test notification via ${method}`, 
                    'info', 
                    {}
                );
                results[method] = success ? 'success' : 'failed';
            } catch (error) {
                results[method] = `error: ${error.message}`;
            }
        }
        
        return results;
    }
    
    /**
     * Get notification statistics
     */
    getStats() {
        return {
            availableMethods: this.state.availableMethods,
            queueSize: this.state.notificationQueue.length,
            lastNotification: this.state.lastNotification,
            isProcessingQueue: this.state.isProcessingQueue
        };
    }
    
    /**
     * Clear notification queue
     */
    clearQueue() {
        this.state.notificationQueue = [];
        this.state.isProcessingQueue = false;
    }
    
    /**
     * Update configuration
     */
    updateOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
        this._detectAvailableMethods();
    }
    
    /**
     * Destroy the notification system
     */
    destroy() {
        // Clear queue
        this.clearQueue();
        
        // Remove created elements
        const elementsToRemove = [
            'fallback-toast-container',
            'fallback-notification-banner'
        ];
        
        elementsToRemove.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.remove();
            }
        });
        
        // Restore original favicon
        if (this.options.favicon.originalIcon) {
            this._updateFavicon(this.options.favicon.originalIcon);
        }
        
        // Restore original title
        if (this.options.title.originalTitle) {
            document.title = this.options.title.originalTitle;
        }
        
        this.logger.log('WebSocket Fallback Notifications destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketFallbackNotifications;
} else if (typeof window !== 'undefined') {
    window.WebSocketFallbackNotifications = WebSocketFallbackNotifications;
}