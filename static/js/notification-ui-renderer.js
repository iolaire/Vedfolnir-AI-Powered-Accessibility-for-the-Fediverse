// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * NotificationUIRenderer - Unified Notification System UI Component
 * 
 * Provides consistent notification display across all pages with support for:
 * - Multiple notification types (success, warning, error, info, progress)
 * - Auto-hide and manual dismiss functionality
 * - Notification stacking and queue management
 * - Consistent styling and behavior
 * 
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
 */

class NotificationUIRenderer {
    constructor(containerId = 'notification-container', options = {}) {
        this.containerId = containerId;
        this.container = null;
        this.notifications = new Map(); // Track active notifications
        this.notificationQueue = [];
        this.isProcessingQueue = false;
        
        // Configuration options
        this.options = {
            // Display settings
            position: options.position || 'top-right', // top-right, top-left, bottom-right, bottom-left, top-center, bottom-center
            maxNotifications: options.maxNotifications || 5,
            stackDirection: options.stackDirection || 'down', // down, up
            
            // Auto-hide settings
            autoHide: options.autoHide !== false, // Default to true
            defaultDuration: options.defaultDuration || 5000, // 5 seconds
            progressDuration: options.progressDuration || 0, // Progress notifications don't auto-hide by default
            
            // Animation settings
            animationDuration: options.animationDuration || 300,
            enableAnimations: options.enableAnimations !== false,
            
            // Styling options
            theme: options.theme || 'modern', // modern, classic, minimal
            showIcons: options.showIcons !== false,
            showTimestamp: options.showTimestamp || false,
            
            // Interaction settings
            allowDismiss: options.allowDismiss !== false,
            pauseOnHover: options.pauseOnHover !== false,
            clickToClose: options.clickToClose || false,
            
            // Queue settings
            enableQueue: options.enableQueue !== false,
            queueProcessingDelay: options.queueProcessingDelay || 100,
            
            // Accessibility
            announceToScreenReader: options.announceToScreenReader !== false,
            
            ...options
        };
        
        // Initialize the renderer
        this.init();
        
        console.log('NotificationUIRenderer initialized with options:', this.options);
    }
    
    /**
     * Initialize the notification renderer
     */
    init() {
        this.createContainer();
        this.setupEventListeners();
        this.setupAccessibility();
    }
    
    /**
     * Create the notification container
     */
    createContainer() {
        // Remove existing container if it exists
        const existingContainer = document.getElementById(this.containerId);
        if (existingContainer) {
            existingContainer.remove();
        }
        
        // Create new container
        this.container = document.createElement('div');
        this.container.id = this.containerId;
        this.container.className = this.getContainerClasses();
        this.container.setAttribute('role', 'region');
        this.container.setAttribute('aria-label', 'Notifications');
        this.container.setAttribute('aria-live', 'polite');
        
        // Add container to body
        document.body.appendChild(this.container);
    }
    
    /**
     * Get CSS classes for the container based on position and theme
     */
    getContainerClasses() {
        const baseClasses = ['notification-container', `notification-container-${this.options.theme}`];
        
        // Position classes
        const positionClasses = {
            'top-right': ['notification-position-top', 'notification-position-right'],
            'top-left': ['notification-position-top', 'notification-position-left'],
            'bottom-right': ['notification-position-bottom', 'notification-position-right'],
            'bottom-left': ['notification-position-bottom', 'notification-position-left'],
            'top-center': ['notification-position-top', 'notification-position-center'],
            'bottom-center': ['notification-position-bottom', 'notification-position-center']
        };
        
        const positionClass = positionClasses[this.options.position] || positionClasses['top-right'];
        baseClasses.push(...positionClass);
        
        // Stack direction
        baseClasses.push(`notification-stack-${this.options.stackDirection}`);
        
        return baseClasses.join(' ');
    }
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Handle page visibility changes to pause/resume auto-hide timers
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseAllTimers();
            } else {
                this.resumeAllTimers();
            }
        });
        
        // Handle window resize to adjust container position if needed
        window.addEventListener('resize', () => {
            this.adjustContainerPosition();
        });
    }
    
    /**
     * Setup accessibility features
     */
    setupAccessibility() {
        // Create screen reader announcement area
        if (this.options.announceToScreenReader) {
            let announcer = document.getElementById('notification-announcer');
            if (!announcer) {
                announcer = document.createElement('div');
                announcer.id = 'notification-announcer';
                announcer.setAttribute('aria-live', 'assertive');
                announcer.setAttribute('aria-atomic', 'true');
                announcer.className = 'sr-only';
                document.body.appendChild(announcer);
            }
        }
    }
    
    /**
     * Render a notification
     * @param {Object} notification - Notification object
     * @param {string} notification.type - Type: success, warning, error, info, progress
     * @param {string} notification.title - Notification title
     * @param {string} notification.message - Notification message
     * @param {Object} notification.options - Additional options
     * @returns {string} Notification ID
     */
    renderNotification(notification) {
        // Validate notification
        if (!notification || !notification.message) {
            console.warn('Invalid notification object:', notification);
            return null;
        }
        
        // Generate unique ID
        const id = this.generateNotificationId();
        
        // Normalize notification object
        const normalizedNotification = this.normalizeNotification(notification, id);
        
        // Add to queue if enabled and container is busy
        if (this.options.enableQueue && this.shouldQueue(normalizedNotification)) {
            this.addToQueue(normalizedNotification);
            return id;
        }
        
        // Render immediately
        return this.renderNotificationImmediate(normalizedNotification);
    }
    
    /**
     * Normalize notification object with defaults
     */
    normalizeNotification(notification, id) {
        return {
            id: id,
            type: notification.type || 'info',
            title: notification.title || '',
            message: notification.message || '',
            duration: notification.duration !== undefined ? notification.duration : this.getDefaultDuration(notification.type),
            priority: notification.priority || 'normal', // low, normal, high, critical
            persistent: notification.persistent || false,
            actions: notification.actions || [],
            data: notification.data || {},
            timestamp: Date.now(),
            progress: notification.progress || null, // For progress notifications
            options: notification.options || {}
        };
    }
    
    /**
     * Get default duration for notification type
     */
    getDefaultDuration(type) {
        const durations = {
            success: this.options.defaultDuration,
            info: this.options.defaultDuration,
            warning: this.options.defaultDuration * 1.5, // 7.5 seconds
            error: this.options.defaultDuration * 2, // 10 seconds
            progress: this.options.progressDuration // 0 = no auto-hide
        };
        
        return durations[type] || this.options.defaultDuration;
    }
    
    /**
     * Check if notification should be queued
     */
    shouldQueue(notification) {
        const activeCount = this.notifications.size;
        const maxNotifications = this.options.maxNotifications;
        
        // Always show critical notifications immediately
        if (notification.priority === 'critical') {
            return false;
        }
        
        // Queue if at max capacity
        return activeCount >= maxNotifications;
    }
    
    /**
     * Add notification to queue
     */
    addToQueue(notification) {
        this.notificationQueue.push(notification);
        
        // Process queue if not already processing
        if (!this.isProcessingQueue) {
            this.processQueue();
        }
    }
    
    /**
     * Process notification queue
     */
    async processQueue() {
        if (this.isProcessingQueue || this.notificationQueue.length === 0) {
            return;
        }
        
        this.isProcessingQueue = true;
        
        while (this.notificationQueue.length > 0 && this.notifications.size < this.options.maxNotifications) {
            const notification = this.notificationQueue.shift();
            
            try {
                await this.renderNotificationImmediate(notification);
                
                // Small delay between processing queued notifications
                if (this.notificationQueue.length > 0) {
                    await this.delay(this.options.queueProcessingDelay);
                }
            } catch (error) {
                console.error('Error processing queued notification:', error);
            }
        }
        
        this.isProcessingQueue = false;
    }
    
    /**
     * Render notification immediately
     */
    renderNotificationImmediate(notification) {
        // Remove oldest notification if at max capacity and this is critical
        if (notification.priority === 'critical' && this.notifications.size >= this.options.maxNotifications) {
            this.removeOldestNotification();
        }
        
        // Create notification element
        const element = this.createNotificationElement(notification);
        
        // Add to container
        this.addToContainer(element, notification);
        
        // Track notification
        this.notifications.set(notification.id, {
            ...notification,
            element: element,
            timer: null,
            isPaused: false
        });
        
        // Setup auto-hide timer
        if (this.options.autoHide && notification.duration > 0 && !notification.persistent) {
            this.setupAutoHideTimer(notification.id, notification.duration);
        }
        
        // Announce to screen reader
        this.announceToScreenReader(notification);
        
        // Trigger show animation
        this.animateShow(element);
        
        console.log(`Notification rendered: ${notification.id} (${notification.type})`);
        
        return notification.id;
    }
    
    /**
     * Create notification DOM element
     */
    createNotificationElement(notification) {
        const element = document.createElement('div');
        element.className = this.getNotificationClasses(notification);
        element.setAttribute('role', 'alert');
        element.setAttribute('aria-live', notification.priority === 'critical' ? 'assertive' : 'polite');
        element.setAttribute('data-notification-id', notification.id);
        element.setAttribute('data-notification-type', notification.type);
        
        // Build notification content
        element.innerHTML = this.buildNotificationHTML(notification);
        
        // Setup event listeners
        this.setupNotificationEventListeners(element, notification);
        
        return element;
    }
    
    /**
     * Get CSS classes for notification element
     */
    getNotificationClasses(notification) {
        const baseClasses = [
            'notification',
            `notification-${notification.type}`,
            `notification-priority-${notification.priority}`,
            `notification-theme-${this.options.theme}`
        ];
        
        if (notification.persistent) {
            baseClasses.push('notification-persistent');
        }
        
        if (notification.actions && notification.actions.length > 0) {
            baseClasses.push('notification-with-actions');
        }
        
        if (notification.progress !== null) {
            baseClasses.push('notification-with-progress');
        }
        
        return baseClasses.join(' ');
    }
    
    /**
     * Build notification HTML content
     */
    buildNotificationHTML(notification) {
        const iconHTML = this.options.showIcons ? this.getNotificationIcon(notification.type) : '';
        const titleHTML = notification.title ? `<div class="notification-title">${this.escapeHTML(notification.title)}</div>` : '';
        const messageHTML = `<div class="notification-message">${this.escapeHTML(notification.message)}</div>`;
        const timestampHTML = this.options.showTimestamp ? `<div class="notification-timestamp">${this.formatTimestamp(notification.timestamp)}</div>` : '';
        const progressHTML = notification.progress !== null ? this.buildProgressHTML(notification.progress) : '';
        const actionsHTML = notification.actions.length > 0 ? this.buildActionsHTML(notification.actions, notification.id) : '';
        const dismissHTML = this.options.allowDismiss ? `<button type="button" class="notification-dismiss" aria-label="Close notification" data-action="dismiss"><i class="bi bi-x"></i></button>` : '';
        
        return `
            <div class="notification-content">
                ${iconHTML}
                <div class="notification-body">
                    ${titleHTML}
                    ${messageHTML}
                    ${timestampHTML}
                    ${progressHTML}
                </div>
                ${dismissHTML}
            </div>
            ${actionsHTML}
        `;
    }
    
    /**
     * Get icon HTML for notification type
     */
    getNotificationIcon(type) {
        const icons = {
            success: 'bi-check-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            error: 'bi-x-circle-fill',
            info: 'bi-info-circle-fill',
            progress: 'bi-arrow-clockwise'
        };
        
        const iconClass = icons[type] || icons.info;
        return `<div class="notification-icon"><i class="bi ${iconClass}"></i></div>`;
    }
    
    /**
     * Build progress bar HTML
     */
    buildProgressHTML(progress) {
        const percentage = Math.max(0, Math.min(100, progress.percentage || 0));
        const label = progress.label || `${percentage}%`;
        
        return `
            <div class="notification-progress">
                <div class="notification-progress-bar">
                    <div class="notification-progress-fill" style="width: ${percentage}%"></div>
                </div>
                <div class="notification-progress-label">${this.escapeHTML(label)}</div>
            </div>
        `;
    }
    
    /**
     * Build actions HTML
     */
    buildActionsHTML(actions, notificationId) {
        if (!actions || actions.length === 0) {
            return '';
        }
        
        const actionsHTML = actions.map(action => {
            const buttonClass = `notification-action notification-action-${action.type || 'default'}`;
            return `<button type="button" class="${buttonClass}" data-action="${action.action}" data-notification-id="${notificationId}">${this.escapeHTML(action.label)}</button>`;
        }).join('');
        
        return `<div class="notification-actions">${actionsHTML}</div>`;
    }
    
    /**
     * Setup event listeners for notification element
     */
    setupNotificationEventListeners(element, notification) {
        // Dismiss button
        const dismissButton = element.querySelector('.notification-dismiss');
        if (dismissButton) {
            dismissButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.dismissNotification(notification.id);
            });
        }
        
        // Action buttons
        const actionButtons = element.querySelectorAll('.notification-action');
        actionButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = button.getAttribute('data-action');
                this.handleNotificationAction(notification.id, action, notification);
            });
        });
        
        // Click to close
        if (this.options.clickToClose) {
            element.addEventListener('click', () => {
                this.dismissNotification(notification.id);
            });
        }
        
        // Pause on hover
        if (this.options.pauseOnHover) {
            element.addEventListener('mouseenter', () => {
                this.pauseTimer(notification.id);
            });
            
            element.addEventListener('mouseleave', () => {
                this.resumeTimer(notification.id);
            });
        }
    }
    
    /**
     * Add notification element to container
     */
    addToContainer(element, notification) {
        if (this.options.stackDirection === 'up') {
            // Add to top (newest first)
            this.container.insertBefore(element, this.container.firstChild);
        } else {
            // Add to bottom (newest last)
            this.container.appendChild(element);
        }
    }
    
    /**
     * Setup auto-hide timer
     */
    setupAutoHideTimer(notificationId, duration) {
        const notification = this.notifications.get(notificationId);
        if (!notification) return;
        
        notification.timer = setTimeout(() => {
            this.dismissNotification(notificationId);
        }, duration);
    }
    
    /**
     * Pause timer for notification
     */
    pauseTimer(notificationId) {
        const notification = this.notifications.get(notificationId);
        if (!notification || !notification.timer || notification.isPaused) return;
        
        clearTimeout(notification.timer);
        notification.isPaused = true;
        notification.pausedAt = Date.now();
    }
    
    /**
     * Resume timer for notification
     */
    resumeTimer(notificationId) {
        const notification = this.notifications.get(notificationId);
        if (!notification || !notification.isPaused) return;
        
        const elapsed = Date.now() - notification.pausedAt;
        const remaining = Math.max(0, notification.duration - elapsed);
        
        if (remaining > 0) {
            notification.timer = setTimeout(() => {
                this.dismissNotification(notificationId);
            }, remaining);
        }
        
        notification.isPaused = false;
        delete notification.pausedAt;
    }
    
    /**
     * Pause all timers
     */
    pauseAllTimers() {
        this.notifications.forEach((notification, id) => {
            if (notification.timer && !notification.isPaused) {
                this.pauseTimer(id);
            }
        });
    }
    
    /**
     * Resume all timers
     */
    resumeAllTimers() {
        this.notifications.forEach((notification, id) => {
            if (notification.isPaused) {
                this.resumeTimer(id);
            }
        });
    }
    
    /**
     * Dismiss notification
     */
    dismissNotification(notificationId) {
        const notification = this.notifications.get(notificationId);
        if (!notification) return;
        
        // Clear timer
        if (notification.timer) {
            clearTimeout(notification.timer);
        }
        
        // Animate hide
        this.animateHide(notification.element, () => {
            // Remove from DOM
            if (notification.element.parentNode) {
                notification.element.parentNode.removeChild(notification.element);
            }
            
            // Remove from tracking
            this.notifications.delete(notificationId);
            
            // Process queue
            if (this.notificationQueue.length > 0) {
                this.processQueue();
            }
            
            console.log(`Notification dismissed: ${notificationId}`);
        });
    }
    
    /**
     * Handle notification action
     */
    handleNotificationAction(notificationId, action, notification) {
        console.log(`Notification action: ${action} for ${notificationId}`);
        
        // Emit custom event
        const event = new CustomEvent('notificationAction', {
            detail: {
                notificationId: notificationId,
                action: action,
                notification: notification
            }
        });
        document.dispatchEvent(event);
        
        // Auto-dismiss after action unless it's a persistent notification
        if (!notification.persistent) {
            this.dismissNotification(notificationId);
        }
    }
    
    /**
     * Animate show
     */
    animateShow(element) {
        if (!this.options.enableAnimations) {
            element.style.opacity = '1';
            element.style.transform = 'translateX(0)';
            return;
        }
        
        // Initial state
        element.style.opacity = '0';
        element.style.transform = this.getInitialTransform();
        element.style.transition = `all ${this.options.animationDuration}ms ease-out`;
        
        // Trigger animation
        requestAnimationFrame(() => {
            element.style.opacity = '1';
            element.style.transform = 'translateX(0) translateY(0) scale(1)';
        });
    }
    
    /**
     * Animate hide
     */
    animateHide(element, callback) {
        if (!this.options.enableAnimations) {
            callback();
            return;
        }
        
        element.style.transition = `all ${this.options.animationDuration}ms ease-in`;
        element.style.opacity = '0';
        element.style.transform = this.getExitTransform();
        
        setTimeout(callback, this.options.animationDuration);
    }
    
    /**
     * Get initial transform for animation
     */
    getInitialTransform() {
        const position = this.options.position;
        
        if (position.includes('right')) {
            return 'translateX(100%) scale(0.8)';
        } else if (position.includes('left')) {
            return 'translateX(-100%) scale(0.8)';
        } else if (position.includes('top')) {
            return 'translateY(-100%) scale(0.8)';
        } else {
            return 'translateY(100%) scale(0.8)';
        }
    }
    
    /**
     * Get exit transform for animation
     */
    getExitTransform() {
        const position = this.options.position;
        
        if (position.includes('right')) {
            return 'translateX(100%) scale(0.8)';
        } else if (position.includes('left')) {
            return 'translateX(-100%) scale(0.8)';
        } else {
            return 'translateY(-20px) scale(0.9)';
        }
    }
    
    /**
     * Render system alert (high priority notification)
     */
    renderSystemAlert(alert) {
        return this.renderNotification({
            type: alert.type || 'warning',
            title: alert.title || 'System Alert',
            message: alert.message,
            priority: 'critical',
            persistent: alert.persistent || true,
            duration: 0, // Don't auto-hide system alerts
            actions: alert.actions || []
        });
    }
    
    /**
     * Render progress update
     */
    renderProgressUpdate(progress) {
        const existingId = progress.id || `progress-${progress.taskId || 'default'}`;
        
        // Update existing progress notification if it exists
        const existing = this.notifications.get(existingId);
        if (existing) {
            this.updateProgressNotification(existingId, progress);
            return existingId;
        }
        
        // Create new progress notification
        return this.renderNotification({
            id: existingId,
            type: 'progress',
            title: progress.title || 'Processing...',
            message: progress.message || 'Please wait...',
            progress: {
                percentage: progress.percentage || 0,
                label: progress.label || `${progress.percentage || 0}%`
            },
            duration: 0, // Progress notifications don't auto-hide
            persistent: true
        });
    }
    
    /**
     * Update existing progress notification
     */
    updateProgressNotification(notificationId, progress) {
        const notification = this.notifications.get(notificationId);
        if (!notification) return;
        
        // Update progress data
        notification.progress = {
            percentage: progress.percentage || 0,
            label: progress.label || `${progress.percentage || 0}%`
        };
        
        // Update message if provided
        if (progress.message) {
            notification.message = progress.message;
        }
        
        // Update DOM
        const progressElement = notification.element.querySelector('.notification-progress');
        if (progressElement) {
            progressElement.innerHTML = this.buildProgressHTML(notification.progress);
        }
        
        const messageElement = notification.element.querySelector('.notification-message');
        if (messageElement && progress.message) {
            messageElement.textContent = progress.message;
        }
        
        // If progress is complete, convert to success notification
        if (progress.percentage >= 100 && progress.autoComplete !== false) {
            setTimeout(() => {
                this.convertProgressToSuccess(notificationId, progress.completeMessage || 'Completed successfully!');
            }, 1000);
        }
    }
    
    /**
     * Convert progress notification to success
     */
    convertProgressToSuccess(notificationId, message) {
        const notification = this.notifications.get(notificationId);
        if (!notification) return;
        
        // Update notification data
        notification.type = 'success';
        notification.message = message;
        notification.persistent = false;
        notification.duration = this.options.defaultDuration;
        
        // Update DOM classes
        notification.element.className = this.getNotificationClasses(notification);
        
        // Update content
        const iconElement = notification.element.querySelector('.notification-icon i');
        if (iconElement) {
            iconElement.className = 'bi bi-check-circle-fill';
        }
        
        const messageElement = notification.element.querySelector('.notification-message');
        if (messageElement) {
            messageElement.textContent = message;
        }
        
        // Remove progress bar
        const progressElement = notification.element.querySelector('.notification-progress');
        if (progressElement) {
            progressElement.remove();
        }
        
        // Setup auto-hide timer
        this.setupAutoHideTimer(notificationId, notification.duration);
    }
    
    /**
     * Clear notifications by type
     */
    clearNotifications(type = null) {
        const toRemove = [];
        
        this.notifications.forEach((notification, id) => {
            if (!type || notification.type === type) {
                toRemove.push(id);
            }
        });
        
        toRemove.forEach(id => {
            this.dismissNotification(id);
        });
        
        console.log(`Cleared ${toRemove.length} notifications${type ? ` of type: ${type}` : ''}`);
    }
    
    /**
     * Set notification limit
     */
    setNotificationLimit(limit) {
        this.options.maxNotifications = Math.max(1, limit);
        
        // Remove excess notifications if needed
        while (this.notifications.size > this.options.maxNotifications) {
            this.removeOldestNotification();
        }
    }
    
    /**
     * Enable auto-hide with duration
     */
    enableAutoHide(duration = null) {
        this.options.autoHide = true;
        
        if (duration !== null) {
            this.options.defaultDuration = duration;
        }
        
        // Apply to existing notifications that don't have timers
        this.notifications.forEach((notification, id) => {
            if (!notification.timer && !notification.persistent && notification.duration > 0) {
                this.setupAutoHideTimer(id, notification.duration);
            }
        });
    }
    
    /**
     * Disable auto-hide
     */
    disableAutoHide() {
        this.options.autoHide = false;
        
        // Clear existing timers
        this.notifications.forEach((notification) => {
            if (notification.timer) {
                clearTimeout(notification.timer);
                notification.timer = null;
            }
        });
    }
    
    /**
     * Remove oldest notification
     */
    removeOldestNotification() {
        let oldestId = null;
        let oldestTimestamp = Infinity;
        
        this.notifications.forEach((notification, id) => {
            if (notification.timestamp < oldestTimestamp && notification.priority !== 'critical') {
                oldestTimestamp = notification.timestamp;
                oldestId = id;
            }
        });
        
        if (oldestId) {
            this.dismissNotification(oldestId);
        }
    }
    
    /**
     * Announce notification to screen reader
     */
    announceToScreenReader(notification) {
        if (!this.options.announceToScreenReader) return;
        
        const announcer = document.getElementById('notification-announcer');
        if (!announcer) return;
        
        const message = `${notification.type} notification: ${notification.title ? notification.title + '. ' : ''}${notification.message}`;
        announcer.textContent = message;
        
        // Clear after announcement
        setTimeout(() => {
            announcer.textContent = '';
        }, 1000);
    }
    
    /**
     * Adjust container position (for responsive design)
     */
    adjustContainerPosition() {
        // This can be extended for responsive positioning
        // Currently, CSS handles most responsive behavior
    }
    
    /**
     * Utility: Generate unique notification ID
     */
    generateNotificationId() {
        return `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Utility: Escape HTML
     */
    escapeHTML(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Utility: Format timestamp
     */
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    }
    
    /**
     * Utility: Delay function
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Get notification statistics
     */
    getStats() {
        return {
            activeNotifications: this.notifications.size,
            queuedNotifications: this.notificationQueue.length,
            maxNotifications: this.options.maxNotifications,
            isProcessingQueue: this.isProcessingQueue,
            notificationsByType: this.getNotificationsByType()
        };
    }
    
    /**
     * Get notifications grouped by type
     */
    getNotificationsByType() {
        const byType = {};
        
        this.notifications.forEach((notification) => {
            byType[notification.type] = (byType[notification.type] || 0) + 1;
        });
        
        return byType;
    }
    
    /**
     * Update configuration
     */
    updateOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
        
        // Recreate container if position changed
        if (newOptions.position) {
            this.createContainer();
            
            // Re-render existing notifications
            const existingNotifications = Array.from(this.notifications.values());
            this.notifications.clear();
            
            existingNotifications.forEach(notification => {
                this.renderNotificationImmediate(notification);
            });
        }
    }
    
    /**
     * Destroy the renderer
     */
    destroy() {
        // Clear all timers
        this.notifications.forEach((notification) => {
            if (notification.timer) {
                clearTimeout(notification.timer);
            }
        });
        
        // Clear notifications
        this.notifications.clear();
        this.notificationQueue = [];
        
        // Remove container
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
        
        // Remove screen reader announcer
        const announcer = document.getElementById('notification-announcer');
        if (announcer) {
            announcer.remove();
        }
        
        console.log('NotificationUIRenderer destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationUIRenderer;
} else if (typeof window !== 'undefined') {
    window.NotificationUIRenderer = NotificationUIRenderer;
}