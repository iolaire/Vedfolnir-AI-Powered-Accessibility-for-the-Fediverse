// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Page Notification Integrator - Client Side
 * 
 * Provides seamless page integration for the unified notification system,
 * including WebSocket connection management, event handler registration,
 * and proper cleanup on page unload.
 */

class PageNotificationIntegrator {
    constructor(pageId, pageType, config = {}) {
        this.pageId = pageId;
        this.pageType = pageType;
        this.config = config;
        
        // WebSocket connection
        this.socket = null;
        this.namespace = config.websocket_config?.namespace || '/';
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        // Event handlers
        this.eventHandlers = new Map();
        this.middlewareFunctions = [];
        
        // UI components
        this.notificationContainer = null;
        this.activeNotifications = new Map();
        
        // State management
        this.initialized = false;
        this.cleanedUp = false;
        this.connectionChangeCallback = null;
        
        // Statistics
        this.stats = {
            connectionsEstablished: 0,
            messagesReceived: 0,
            errorsEncountered: 0,
            reconnectAttempts: 0
        };
        
        // Bind methods
        this.handleConnect = this.handleConnect.bind(this);
        this.handleDisconnect = this.handleDisconnect.bind(this);
        this.handleConnectError = this.handleConnectError.bind(this);
        this.handleReconnect = this.handleReconnect.bind(this);
        this.handleNotification = this.handleNotification.bind(this);
        this.cleanup = this.cleanup.bind(this);
        
        console.log(`PageNotificationIntegrator initialized for ${pageId} (${pageType})`);
    }
    
    /**
     * Initialize page notifications
     */
    async initialize() {
        try {
            if (this.initialized) {
                console.warn('PageNotificationIntegrator already initialized');
                return;
            }
            
            console.log(`Initializing notifications for page ${this.pageId}`);
            
            // Setup notification UI
            this.setupNotificationUI();
            
            // Register event handlers
            this.registerEventHandlers();
            
            // Setup middleware
            this.setupMiddleware();
            
            // Initialize WebSocket connection
            await this.initializeWebSocket();
            
            // Setup page unload cleanup
            this.setupCleanupHandlers();
            
            this.initialized = true;
            console.log(`Page notifications initialized successfully for ${this.pageId}`);
            
        } catch (error) {
            console.error('Failed to initialize page notifications:', error);
            this.stats.errorsEncountered++;
            throw error;
        }
    }
    
    /**
     * Setup notification UI container and styling
     */
    setupNotificationUI() {
        const uiConfig = this.config.ui_config || {};
        const containerId = uiConfig.container_id || `notifications-${this.pageId}`;
        
        // Create notification container if it doesn't exist
        this.notificationContainer = document.getElementById(containerId);
        if (!this.notificationContainer) {
            this.notificationContainer = document.createElement('div');
            this.notificationContainer.id = containerId;
            this.notificationContainer.className = 'notification-container';
            
            // Apply positioning
            const position = this.config.notification_config?.position || 'top-right';
            this.applyContainerPositioning(position);
            
            // Add to page
            document.body.appendChild(this.notificationContainer);
        }
        
        // Apply styling
        this.applyNotificationStyling();
        
        console.log(`Notification UI setup complete for container: ${containerId}`);
    }
    
    /**
     * Apply container positioning based on configuration
     */
    applyContainerPositioning(position) {
        const container = this.notificationContainer;
        
        // Reset positioning
        container.style.position = 'fixed';
        container.style.zIndex = '9999';
        container.style.pointerEvents = 'none';
        
        switch (position) {
            case 'top-right':
                container.style.top = '20px';
                container.style.right = '20px';
                break;
            case 'top-left':
                container.style.top = '20px';
                container.style.left = '20px';
                break;
            case 'top-center':
                container.style.top = '20px';
                container.style.left = '50%';
                container.style.transform = 'translateX(-50%)';
                break;
            case 'bottom-right':
                container.style.bottom = '20px';
                container.style.right = '20px';
                break;
            case 'bottom-left':
                container.style.bottom = '20px';
                container.style.left = '20px';
                break;
            case 'bottom-center':
                container.style.bottom = '20px';
                container.style.left = '50%';
                container.style.transform = 'translateX(-50%)';
                break;
            case 'full-width':
                container.style.top = '0';
                container.style.left = '0';
                container.style.right = '0';
                break;
            default:
                container.style.top = '20px';
                container.style.right = '20px';
        }
    }
    
    /**
     * Apply notification styling
     */
    applyNotificationStyling() {
        // Add CSS if not already present
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                .notification-container {
                    max-width: 400px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                
                .notification {
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    margin-bottom: 12px;
                    padding: 16px;
                    pointer-events: auto;
                    position: relative;
                    transition: all 0.3s ease;
                    border-left: 4px solid #007bff;
                }
                
                .notification.success { border-left-color: #28a745; }
                .notification.warning { border-left-color: #ffc107; }
                .notification.error { border-left-color: #dc3545; }
                .notification.info { border-left-color: #17a2b8; }
                .notification.progress { border-left-color: #6f42c1; }
                
                .notification-title {
                    font-weight: 600;
                    margin-bottom: 4px;
                    color: #333;
                }
                
                .notification-message {
                    color: #666;
                    font-size: 14px;
                    line-height: 1.4;
                }
                
                .notification-progress {
                    margin-top: 8px;
                    height: 4px;
                    background: #e9ecef;
                    border-radius: 2px;
                    overflow: hidden;
                }
                
                .notification-progress-bar {
                    height: 100%;
                    background: #007bff;
                    width: var(--progress-width, 0%);
                    transition: width 0.3s ease;
                }
                
                .notification-close {
                    position: absolute;
                    top: 8px;
                    right: 8px;
                    background: none;
                    border: none;
                    font-size: 18px;
                    cursor: pointer;
                    color: #999;
                    padding: 4px;
                    line-height: 1;
                }
                
                .notification-close:hover {
                    color: #333;
                }
                
                .notification-actions {
                    margin-top: 12px;
                    display: flex;
                    gap: 8px;
                }
                
                .notification-action {
                    padding: 6px 12px;
                    border: 1px solid #ddd;
                    background: white;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                    text-decoration: none;
                    color: #333;
                }
                
                .notification-action:hover {
                    background: #f8f9fa;
                }
                
                .notification-action.primary {
                    background: #007bff;
                    color: white;
                    border-color: #007bff;
                }
                
                .notification-action.primary:hover {
                    background: #0056b3;
                }
                
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
                
                .notification.entering {
                    animation: slideInRight 0.3s ease;
                }
                
                .notification.exiting {
                    animation: slideOutRight 0.3s ease;
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    /**
     * Initialize WebSocket connection
     */
    async initializeWebSocket() {
        // Use the global WebSocket from websocket-bundle.js instead of creating new connections
        if (window.VedfolnirWS && window.VedfolnirWS.socket) {
            this.socket = window.VedfolnirWS.socket;
            this.setupWebSocketHandlers();
            console.log('Using existing WebSocket connection for notifications');
            return;
        }
        
        // If no global WebSocket exists, wait for it to be initialized
        const checkForWebSocket = () => {
            if (window.VedfolnirWS && window.VedfolnirWS.socket) {
                this.socket = window.VedfolnirWS.socket;
                this.setupWebSocketHandlers();
                console.log('Connected to WebSocket for notifications');
            } else {
                setTimeout(checkForWebSocket, 100);
            }
        };
        
        checkForWebSocket();
    }
    
    /**
     * Setup WebSocket event handlers for notifications
     */
    setupWebSocketHandlers() {
        if (!this.socket) return;
        
        // Register notification event handlers
        this.socket.on('notification', this.handleNotification.bind(this));
        this.socket.on('system_notification', this.handleSystemNotification.bind(this));
        this.socket.on('admin_notification', this.handleAdminNotification.bind(this));
        
        console.log('WebSocket notification handlers registered');
    }
    
    /**
     * Register event handlers
     */
    registerEventHandlers() {
        const handlerConfig = this.config.event_handlers || {};
        
        // Register page-specific handlers
        Object.entries(handlerConfig).forEach(([event, handlerName]) => {
            if (typeof window[handlerName] === 'function') {
                this.eventHandlers.set(event, window[handlerName]);
            } else {
                console.warn(`Handler function ${handlerName} not found for event ${event}`);
            }
        });
        
        console.log(`Registered ${this.eventHandlers.size} event handlers`);
    }
    
    /**
     * Setup middleware functions
     */
    setupMiddleware() {
        const middlewareConfig = this.config.middleware || [];
        
        middlewareConfig.forEach(middlewareName => {
            if (typeof window[middlewareName] === 'function') {
                this.middlewareFunctions.push(window[middlewareName]);
            } else {
                console.warn(`Middleware function ${middlewareName} not found`);
            }
        });
        
        console.log(`Setup ${this.middlewareFunctions.length} middleware functions`);
    }
    
    /**
     * Setup cleanup handlers for page unload
     */
    setupCleanupHandlers() {
        // Cleanup on page unload
        window.addEventListener('beforeunload', this.cleanup);
        
        // Cleanup on page hide (mobile/tab switching)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.handlePageHidden();
            } else {
                this.handlePageVisible();
            }
        });
        
        // Cleanup on navigation (SPA)
        if (window.history && window.history.pushState) {
            const originalPushState = window.history.pushState;
            window.history.pushState = (...args) => {
                this.cleanup();
                return originalPushState.apply(window.history, args);
            };
        }
    }
    
    /**
     * Handle WebSocket connection established
     */
    handleConnect() {
        console.log(`WebSocket connected to namespace: ${this.namespace}`);
        const wasConnected = this.connected;
        this.connected = true;
        this.reconnectAttempts = 0;
        this.stats.connectionsEstablished++;
        
        // Call connection change callback if status changed
        if (!wasConnected && this.connectionChangeCallback) {
            this.connectionChangeCallback(true);
        }
        
        // Show connection notification
        this.showNotification({
            type: 'success',
            title: 'Connected',
            message: 'Real-time notifications enabled',
            auto_hide: true,
            duration: 3000
        });
        
        // Execute middleware
        this.executeMiddleware('connect', { namespace: this.namespace });
        
        // Call page-specific connect handler
        const connectHandler = this.eventHandlers.get('connect');
        if (connectHandler) {
            connectHandler({ namespace: this.namespace, pageId: this.pageId });
        }
    }
    
    /**
     * Handle WebSocket disconnection
     */
    handleDisconnect(reason) {
        console.log(`WebSocket disconnected from namespace: ${this.namespace}, reason: ${reason}`);
        const wasConnected = this.connected;
        this.connected = false;
        
        // Call connection change callback if status changed
        if (wasConnected && this.connectionChangeCallback) {
            this.connectionChangeCallback(false);
        }
        
        // Show disconnection notification if not intentional
        if (reason !== 'io client disconnect' && !this.cleanedUp) {
            this.showNotification({
                type: 'warning',
                title: 'Connection Lost',
                message: 'Attempting to reconnect...',
                auto_hide: false
            });
        }
        
        // Execute middleware
        this.executeMiddleware('disconnect', { namespace: this.namespace, reason });
        
        // Call page-specific disconnect handler
        const disconnectHandler = this.eventHandlers.get('disconnect');
        if (disconnectHandler) {
            disconnectHandler({ namespace: this.namespace, reason, pageId: this.pageId });
        }
    }
    
    /**
     * Handle WebSocket connection error
     */
    handleConnectError(error) {
        console.error('WebSocket connection error:', error);
        this.stats.errorsEncountered++;
        
        // Show error notification
        this.showNotification({
            type: 'error',
            title: 'Connection Error',
            message: 'Failed to establish real-time connection',
            auto_hide: true,
            duration: 5000
        });
        
        // Execute middleware
        this.executeMiddleware('connect_error', { error });
        
        // Call page-specific error handler
        const errorHandler = this.eventHandlers.get('connect_error');
        if (errorHandler) {
            errorHandler({ error, pageId: this.pageId });
        }
    }
    
    /**
     * Handle WebSocket reconnection
     */
    handleReconnect(attemptNumber) {
        console.log(`WebSocket reconnected after ${attemptNumber} attempts`);
        this.stats.reconnectAttempts = attemptNumber;
        
        // Show reconnection notification
        this.showNotification({
            type: 'success',
            title: 'Reconnected',
            message: 'Real-time notifications restored',
            auto_hide: true,
            duration: 3000
        });
        
        // Execute middleware
        this.executeMiddleware('reconnect', { attemptNumber });
        
        // Call page-specific reconnect handler
        const reconnectHandler = this.eventHandlers.get('reconnect');
        if (reconnectHandler) {
            reconnectHandler({ attemptNumber, pageId: this.pageId });
        }
    }
    
    /**
     * Handle notification message
     */
    handleNotification(data) {
        console.log('Received notification:', data);
        this.stats.messagesReceived++;
        
        // Execute middleware
        const processedData = this.executeMiddleware('notification', data);
        
        // Show notification
        this.showNotification(processedData || data);
        
        // Call page-specific notification handler
        const notificationHandler = this.eventHandlers.get('notification');
        if (notificationHandler) {
            notificationHandler(data);
        }
    }
    
    /**
     * Handle system notification
     */
    handleSystemNotification(data) {
        console.log('Received system notification:', data);
        this.stats.messagesReceived++;
        
        // Execute middleware
        const processedData = this.executeMiddleware('system_notification', data);
        
        // Show system notification with higher priority
        this.showNotification({
            ...processedData || data,
            type: 'info',
            auto_hide: false,
            priority: 'high'
        });
        
        // Call page-specific system notification handler
        const systemHandler = this.eventHandlers.get('system_notification');
        if (systemHandler) {
            systemHandler(data);
        }
    }
    
    /**
     * Handle admin notification
     */
    handleAdminNotification(data) {
        console.log('Received admin notification:', data);
        this.stats.messagesReceived++;
        
        // Execute middleware
        const processedData = this.executeMiddleware('admin_notification', data);
        
        // Show admin notification with highest priority
        this.showNotification({
            ...processedData || data,
            type: 'warning',
            auto_hide: false,
            priority: 'critical'
        });
        
        // Call page-specific admin notification handler
        const adminHandler = this.eventHandlers.get('admin_notification');
        if (adminHandler) {
            adminHandler(data);
        }
    }
    
    /**
     * Handle page-specific events
     */
    handlePageEvent(event, data) {
        console.log(`Received page event: ${event}`, data);
        this.stats.messagesReceived++;
        
        // Execute middleware
        const processedData = this.executeMiddleware(event, data);
        
        // Call registered handler
        const handler = this.eventHandlers.get(event);
        if (handler) {
            handler(processedData || data);
        } else {
            console.warn(`No handler registered for event: ${event}`);
        }
    }
    
    /**
     * Show notification in UI
     */
    showNotification(notification) {
        try {
            const notificationId = notification.id || this.generateNotificationId();
            
            // Check notification limits
            const maxNotifications = this.config.notification_config?.max_notifications || 5;
            if (this.activeNotifications.size >= maxNotifications) {
                this.removeOldestNotification();
            }
            
            // Create notification element
            const notificationElement = this.createNotificationElement(notification);
            notificationElement.dataset.notificationId = notificationId;
            
            // Add to container
            this.notificationContainer.appendChild(notificationElement);
            this.activeNotifications.set(notificationId, {
                element: notificationElement,
                data: notification,
                createdAt: Date.now()
            });
            
            // Apply entrance animation
            notificationElement.classList.add('entering');
            setTimeout(() => {
                notificationElement.classList.remove('entering');
            }, 300);
            
            // Auto-hide if configured
            if (notification.auto_hide !== false && this.config.notification_config?.auto_hide !== false) {
                const duration = notification.duration || 5000;
                setTimeout(() => {
                    this.hideNotification(notificationId);
                }, duration);
            }
            
            console.log(`Notification displayed: ${notificationId}`);
            
        } catch (error) {
            console.error('Failed to show notification:', error);
            this.stats.errorsEncountered++;
        }
    }
    
    /**
     * Create notification DOM element
     */
    createNotificationElement(notification) {
        const element = document.createElement('div');
        element.className = `notification ${notification.type || 'info'}`;
        
        // Close button
        const closeButton = document.createElement('button');
        closeButton.className = 'notification-close';
        closeButton.innerHTML = '×';
        closeButton.onclick = () => this.hideNotification(notification.id);
        element.appendChild(closeButton);
        
        // Title
        if (notification.title) {
            const title = document.createElement('div');
            title.className = 'notification-title';
            title.textContent = notification.title;
            element.appendChild(title);
        }
        
        // Message
        const message = document.createElement('div');
        message.className = 'notification-message';
        message.textContent = notification.message || '';
        element.appendChild(message);
        
        // Progress bar
        if (notification.progress !== undefined || this.config.notification_config?.show_progress) {
            const progressContainer = document.createElement('div');
            progressContainer.className = 'notification-progress';
            
            const progressBar = document.createElement('div');
            progressBar.className = 'notification-progress-bar';
            progressBar.style.setProperty('--progress-width', `${notification.progress || 0}%`);
            
            progressContainer.appendChild(progressBar);
            element.appendChild(progressContainer);
        }
        
        // Actions
        if (notification.actions && notification.actions.length > 0) {
            const actionsContainer = document.createElement('div');
            actionsContainer.className = 'notification-actions';
            
            notification.actions.forEach(action => {
                const actionElement = document.createElement('a');
                actionElement.className = `notification-action ${action.type || ''}`;
                actionElement.textContent = action.text;
                actionElement.href = action.url || '#';
                actionElement.onclick = (e) => {
                    if (action.handler) {
                        e.preventDefault();
                        action.handler();
                    }
                };
                actionsContainer.appendChild(actionElement);
            });
            
            element.appendChild(actionsContainer);
        }
        
        return element;
    }
    
    /**
     * Hide notification
     */
    hideNotification(notificationId) {
        const notification = this.activeNotifications.get(notificationId);
        if (!notification) return;
        
        const element = notification.element;
        
        // Apply exit animation
        element.classList.add('exiting');
        
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.activeNotifications.delete(notificationId);
        }, 300);
    }
    
    /**
     * Remove oldest notification when limit exceeded
     */
    removeOldestNotification() {
        let oldestId = null;
        let oldestTime = Date.now();
        
        for (const [id, notification] of this.activeNotifications) {
            if (notification.createdAt < oldestTime) {
                oldestTime = notification.createdAt;
                oldestId = id;
            }
        }
        
        if (oldestId) {
            this.hideNotification(oldestId);
        }
    }
    
    /**
     * Execute middleware functions
     */
    executeMiddleware(event, data) {
        let processedData = data;
        
        for (const middleware of this.middlewareFunctions) {
            try {
                const result = middleware(event, processedData, this);
                if (result !== undefined) {
                    processedData = result;
                }
            } catch (error) {
                console.error('Middleware error:', error);
                this.stats.errorsEncountered++;
            }
        }
        
        return processedData;
    }
    
    /**
     * Handle page hidden (tab switching, mobile background)
     */
    handlePageHidden() {
        console.log('Page hidden, pausing notifications');
        // Could implement notification queuing here
    }
    
    /**
     * Handle page visible (tab focus, mobile foreground)
     */
    handlePageVisible() {
        console.log('Page visible, resuming notifications');
        // Could implement queued notification replay here
    }
    
    /**
     * Generate unique notification ID
     */
    generateNotificationId() {
        return `notification-${this.pageId}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Send message through WebSocket
     */
    sendMessage(event, data) {
        if (this.socket && this.connected) {
            this.socket.emit(event, data);
            console.log(`Sent message: ${event}`, data);
        } else {
            console.warn('Cannot send message: WebSocket not connected');
        }
    }
    
    /**
     * Join a room
     */
    joinRoom(roomId) {
        this.sendMessage('join_room', { room_id: roomId });
    }
    
    /**
     * Leave a room
     */
    leaveRoom(roomId) {
        this.sendMessage('leave_room', { room_id: roomId });
    }
    
    /**
     * Register connection change callback
     */
    onConnectionChange(callback) {
        if (typeof callback === 'function') {
            this.connectionChangeCallback = callback;
            // Immediately call with current status
            callback(this.connected);
        }
    }
    
    /**
     * Get integration status
     */
    getStatus() {
        return {
            pageId: this.pageId,
            pageType: this.pageType,
            initialized: this.initialized,
            connected: this.connected,
            namespace: this.namespace,
            activeNotifications: this.activeNotifications.size,
            stats: { ...this.stats }
        };
    }
    
    /**
     * Cleanup page integration
     */
    cleanup() {
        if (this.cleanedUp) return;
        
        console.log(`Cleaning up page integration: ${this.pageId}`);
        
        try {
            // Disconnect WebSocket
            if (this.socket) {
                this.socket.disconnect();
                this.socket = null;
            }
            
            // Clear notifications
            this.activeNotifications.forEach((notification, id) => {
                this.hideNotification(id);
            });
            
            // Remove event listeners
            window.removeEventListener('beforeunload', this.cleanup);
            
            // Clear containers
            if (this.notificationContainer && this.notificationContainer.parentNode) {
                this.notificationContainer.parentNode.removeChild(this.notificationContainer);
            }
            
            // Reset state
            this.connected = false;
            this.initialized = false;
            this.cleanedUp = true;
            
            console.log(`Page integration cleanup complete: ${this.pageId}`);
            
        } catch (error) {
            console.error('Error during cleanup:', error);
        }
    }
}

// Global utility functions for page integration

/**
 * Initialize page notifications
 */
window.initializePageNotifications = function(pageId, pageType, config = {}) {
    if (window.pageNotificationIntegrator) {
        console.warn('Page notifications already initialized');
        return window.pageNotificationIntegrator;
    }
    
    window.pageNotificationIntegrator = new PageNotificationIntegrator(pageId, pageType, config);
    return window.pageNotificationIntegrator.initialize().then(() => {
        return window.pageNotificationIntegrator;
    });
};

/**
 * Get current page notification integrator
 */
window.getPageNotificationIntegrator = function() {
    return window.pageNotificationIntegrator;
};

/**
 * Cleanup page notifications
 */
window.cleanupPageNotifications = function() {
    if (window.pageNotificationIntegrator) {
        window.pageNotificationIntegrator.cleanup();
        window.pageNotificationIntegrator = null;
    }
};

// Default middleware functions

/**
 * Validate notification permissions
 */
window.validateNotificationPermissions = function(event, data, integrator) {
    // Implement permission validation logic
    return data;
};

/**
 * Log notification events
 */
window.logNotificationEvents = function(event, data, integrator) {
    console.log(`[${integrator.pageId}] ${event}:`, data);
    return data;
};

/**
 * Handle notification errors
 */
window.handleNotificationErrors = function(event, data, integrator) {
    if (data && data.error) {
        console.error(`Notification error in ${event}:`, data.error);
        integrator.stats.errorsEncountered++;
    }
    return data;
};

// Default event handlers

/**
 * Handle page connect
 */
window.handlePageConnect = function(data) {
    console.log('Page connected to notifications:', data);
};

/**
 * Handle page disconnect
 */
window.handlePageDisconnect = function(data) {
    console.log('Page disconnected from notifications:', data);
};

/**
 * Handle page notification
 */
window.handlePageNotification = function(data) {
    console.log('Page notification received:', data);
};

/**
 * Handle page error
 */
window.handlePageError = function(data) {
    console.error('Page notification error:', data);
};

// Export PageNotificationIntegrator to global scope
window.PageNotificationIntegrator = PageNotificationIntegrator;

console.log('Page Notification Integrator loaded');