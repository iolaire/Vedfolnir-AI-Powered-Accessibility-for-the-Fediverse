// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Enhanced WebSocket Client Integration Example
 * 
 * Demonstrates how to integrate the Enhanced Client Error Handler with
 * existing WebSocket implementations to provide comprehensive error handling
 * and user feedback.
 */

class WebSocketEnhancedClientIntegration {
    constructor(options = {}) {
        this.options = this._mergeOptions(options);
        this.client = null;
        this.enhancedErrorHandler = null;
        this.logger = console;
        
        // Initialize the integration
        this._initialize();
    }
    
    /**
     * Merge options with defaults
     */
    _mergeOptions(userOptions) {
        const defaults = {
            // WebSocket configuration
            serverUrl: window.location.origin,
            namespace: '/',
            transports: ['websocket', 'polling'],
            
            // Enhanced error handler configuration
            enableEnhancedErrorHandling: true,
            enableDebugMode: false,
            enableUserFeedback: true,
            enableAutoRecovery: true,
            
            // UI configuration
            showConnectionStatus: true,
            showErrorModal: true,
            showNotifications: true,
            notificationPosition: 'top-right',
            
            // CORS-specific configuration
            corsGuidanceEnabled: true,
            detailedErrorMessages: true,
            
            // Callbacks
            onConnect: null,
            onDisconnect: null,
            onError: null,
            onRecovery: null
        };
        
        return { ...defaults, ...userOptions };
    }
    
    /**
     * Initialize the WebSocket client with enhanced error handling
     */
    async _initialize() {
        try {
            // Create WebSocket client
            this._createWebSocketClient();
            
            // Initialize enhanced error handler
            if (this.options.enableEnhancedErrorHandling) {
                await this._initializeEnhancedErrorHandler();
            }
            
            // Setup application-specific event handlers
            this._setupApplicationEventHandlers();
            
            // Connect to server
            this._connect();
            
            this.logger.log('WebSocket Enhanced Client Integration initialized');
            
        } catch (error) {
            this.logger.error('Failed to initialize WebSocket Enhanced Client Integration:', error);
            throw error;
        }
    }
    
    /**
     * Create WebSocket client instance
     */
    _createWebSocketClient() {
        // Check if Socket.IO is available
        if (typeof io === 'undefined') {
            throw new Error('Socket.IO library is not available');
        }
        
        // Create Socket.IO client with configuration
        this.client = io(this.options.serverUrl + this.options.namespace, {
            transports: this.options.transports,
            autoConnect: false,
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            timeout: 20000
        });
        
        this.logger.log('WebSocket client created');
    }
    
    /**
     * Initialize enhanced error handler
     */
    async _initializeEnhancedErrorHandler() {
        if (typeof WebSocketEnhancedClientErrorHandler === 'undefined') {
            this.logger.warn('Enhanced Client Error Handler is not available');
            return;
        }
        
        // Create enhanced error handler with configuration
        this.enhancedErrorHandler = new WebSocketEnhancedClientErrorHandler(this.client, {
            enableUserFeedback: this.options.enableUserFeedback,
            enableAutoRecovery: this.options.enableAutoRecovery,
            enableDebugMode: this.options.enableDebugMode,
            
            showConnectionStatus: this.options.showConnectionStatus,
            showErrorModal: this.options.showErrorModal,
            showNotifications: this.options.showNotifications,
            notificationPosition: this.options.notificationPosition,
            
            corsGuidanceEnabled: this.options.corsGuidanceEnabled,
            detailedErrorMessages: this.options.detailedErrorMessages,
            
            // Custom callbacks
            onErrorCallback: (category, error, errorInfo) => {
                this._handleApplicationError(category, error, errorInfo);
            },
            
            onRecoveryCallback: () => {
                this._handleApplicationRecovery();
            }
        });
        
        this.logger.log('Enhanced error handler initialized');
    }
    
    /**
     * Setup application-specific event handlers
     */
    _setupApplicationEventHandlers() {
        // Connection events
        this.client.on('connect', () => {
            this.logger.log('Connected to WebSocket server');
            
            if (this.options.onConnect) {
                this.options.onConnect();
            }
            
            // Emit custom event for application components
            this._emitApplicationEvent('websocket_connected', {
                transport: this._getCurrentTransport(),
                timestamp: Date.now()
            });
        });
        
        this.client.on('disconnect', (reason) => {
            this.logger.log('Disconnected from WebSocket server:', reason);
            
            if (this.options.onDisconnect) {
                this.options.onDisconnect(reason);
            }
            
            // Emit custom event for application components
            this._emitApplicationEvent('websocket_disconnected', {
                reason,
                timestamp: Date.now()
            });
        });
        
        // Error events (these will be handled by the enhanced error handler)
        this.client.on('connect_error', (error) => {
            this.logger.error('WebSocket connection error:', error);
            
            if (this.options.onError) {
                this.options.onError(error);
            }
        });
        
        // Application-specific events
        this.client.on('message', (data) => {
            this._handleMessage(data);
        });
        
        this.client.on('notification', (data) => {
            this._handleNotification(data);
        });
        
        this.client.on('progress_update', (data) => {
            this._handleProgressUpdate(data);
        });
        
        // Server error events
        this.client.on('server_error', (data) => {
            this._handleServerError(data);
        });
    }
    
    /**
     * Connect to WebSocket server
     */
    _connect() {
        this.logger.log('Connecting to WebSocket server...');
        this.client.connect();
    }
    
    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.client && this.client.connected) {
            this.logger.log('Disconnecting from WebSocket server...');
            this.client.disconnect();
        }
    }
    
    /**
     * Handle application-specific errors
     */
    _handleApplicationError(category, error, errorInfo) {
        this.logger.log('Application error handled:', { category, error: error.message, errorInfo });
        
        // Application-specific error handling logic
        switch (category) {
            case 'cors':
                this._handleCORSError(error, errorInfo);
                break;
            case 'authentication':
                this._handleAuthenticationError(error, errorInfo);
                break;
            case 'network':
                this._handleNetworkError(error, errorInfo);
                break;
            default:
                this._handleGenericError(error, errorInfo);
        }
        
        // Emit custom event for application components
        this._emitApplicationEvent('websocket_error_handled', {
            category,
            error: error.message,
            errorInfo,
            timestamp: Date.now()
        });
    }
    
    /**
     * Handle application recovery
     */
    _handleApplicationRecovery() {
        this.logger.log('Application recovery completed');
        
        if (this.options.onRecovery) {
            this.options.onRecovery();
        }
        
        // Emit custom event for application components
        this._emitApplicationEvent('websocket_recovery_completed', {
            timestamp: Date.now()
        });
    }
    
    /**
     * Handle CORS-specific errors
     */
    _handleCORSError(error, errorInfo) {
        // Application-specific CORS handling
        this.logger.warn('CORS error detected, checking application configuration...');
        
        // Check if we're in development mode
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            this.logger.info('Development environment detected, CORS issues may be expected');
        }
        
        // Notify application components
        this._emitApplicationEvent('websocket_cors_error', {
            currentUrl: window.location.href,
            expectedOrigin: this.options.serverUrl,
            timestamp: Date.now()
        });
    }
    
    /**
     * Handle authentication errors
     */
    _handleAuthenticationError(error, errorInfo) {
        // Application-specific authentication handling
        this.logger.warn('Authentication error detected, checking session status...');
        
        // Check if user is still logged in
        this._checkAuthenticationStatus().then(isAuthenticated => {
            if (!isAuthenticated) {
                this.logger.info('User is not authenticated, redirecting to login...');
                // The enhanced error handler will handle the redirect
            } else {
                this.logger.warn('User appears authenticated but WebSocket auth failed');
            }
        });
    }
    
    /**
     * Handle network errors
     */
    _handleNetworkError(error, errorInfo) {
        // Application-specific network handling
        this.logger.warn('Network error detected, checking connectivity...');
        
        // Test basic connectivity
        this._testConnectivity().then(isOnline => {
            if (!isOnline) {
                this.logger.warn('Network connectivity issues detected');
                this._emitApplicationEvent('websocket_network_offline', {
                    timestamp: Date.now()
                });
            }
        });
    }
    
    /**
     * Handle generic errors
     */
    _handleGenericError(error, errorInfo) {
        // Application-specific generic error handling
        this.logger.warn('Generic WebSocket error:', error.message);
        
        // Log error for debugging
        this._logErrorForDebugging(error, errorInfo);
    }
    
    /**
     * Handle incoming messages
     */
    _handleMessage(data) {
        this.logger.log('Received message:', data);
        
        // Emit custom event for application components
        this._emitApplicationEvent('websocket_message_received', {
            data,
            timestamp: Date.now()
        });
    }
    
    /**
     * Handle notifications
     */
    _handleNotification(data) {
        this.logger.log('Received notification:', data);
        
        // Show notification using enhanced error handler's notification system
        if (this.enhancedErrorHandler && this.enhancedErrorHandler.components.fallbackNotifications) {
            this.enhancedErrorHandler.components.fallbackNotifications.notify(
                data.message || 'New notification',
                data.type || 'info'
            );
        }
        
        // Emit custom event for application components
        this._emitApplicationEvent('websocket_notification_received', {
            data,
            timestamp: Date.now()
        });
    }
    
    /**
     * Handle progress updates
     */
    _handleProgressUpdate(data) {
        this.logger.log('Received progress update:', data);
        
        // Update progress indicators in the application
        this._updateProgressIndicators(data);
        
        // Emit custom event for application components
        this._emitApplicationEvent('websocket_progress_update', {
            data,
            timestamp: Date.now()
        });
    }
    
    /**
     * Handle server errors
     */
    _handleServerError(data) {
        this.logger.error('Server error received:', data);
        
        // Show server error using enhanced error handler
        if (this.enhancedErrorHandler) {
            this.enhancedErrorHandler.handleServerError(data);
        }
    }
    
    /**
     * Utility methods
     */
    
    _getCurrentTransport() {
        if (this.client && this.client.io && this.client.io.engine && this.client.io.engine.transport) {
            return this.client.io.engine.transport.name;
        }
        return 'unknown';
    }
    
    _emitApplicationEvent(eventName, data) {
        if (typeof window !== 'undefined' && window.dispatchEvent) {
            try {
                window.dispatchEvent(new CustomEvent(eventName, {
                    detail: data
                }));
            } catch (error) {
                this.logger.warn('Failed to emit application event:', error);
            }
        }
    }
    
    async _checkAuthenticationStatus() {
        try {
            const response = await fetch('/api/auth/status', {
                method: 'GET',
                credentials: 'same-origin'
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    }
    
    async _testConnectivity() {
        try {
            const response = await fetch('/health', {
                method: 'HEAD',
                cache: 'no-cache'
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    }
    
    _updateProgressIndicators(data) {
        // Update any progress bars or indicators in the application
        const progressElements = document.querySelectorAll('[data-websocket-progress]');
        progressElements.forEach(element => {
            if (data.progress !== undefined) {
                element.style.width = `${data.progress}%`;
                element.setAttribute('aria-valuenow', data.progress);
            }
            
            if (data.message) {
                const messageElement = element.querySelector('.progress-message');
                if (messageElement) {
                    messageElement.textContent = data.message;
                }
            }
        });
    }
    
    _logErrorForDebugging(error, errorInfo) {
        // Log error information for debugging purposes
        const debugInfo = {
            timestamp: new Date().toISOString(),
            error: {
                message: error.message,
                stack: error.stack
            },
            errorInfo,
            client: {
                connected: this.client ? this.client.connected : false,
                transport: this._getCurrentTransport()
            },
            browser: {
                userAgent: navigator.userAgent,
                url: window.location.href
            }
        };
        
        // Store in session storage for debugging
        try {
            const existingLogs = JSON.parse(sessionStorage.getItem('websocket_error_logs') || '[]');
            existingLogs.push(debugInfo);
            
            // Keep only last 10 errors
            if (existingLogs.length > 10) {
                existingLogs.splice(0, existingLogs.length - 10);
            }
            
            sessionStorage.setItem('websocket_error_logs', JSON.stringify(existingLogs));
        } catch (e) {
            this.logger.warn('Failed to store error log:', e);
        }
    }
    
    /**
     * Public API methods
     */
    
    /**
     * Send message to server
     */
    send(event, data) {
        if (this.client && this.client.connected) {
            this.client.emit(event, data);
            return true;
        } else {
            this.logger.warn('Cannot send message: WebSocket not connected');
            return false;
        }
    }
    
    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            connected: this.client ? this.client.connected : false,
            transport: this._getCurrentTransport(),
            enhancedErrorHandler: this.enhancedErrorHandler ? this.enhancedErrorHandler.getStatus() : null
        };
    }
    
    /**
     * Enable/disable debug mode
     */
    setDebugMode(enabled) {
        if (this.enhancedErrorHandler) {
            if (enabled) {
                this.enhancedErrorHandler.toggleDebugMode();
            }
        }
        
        this.options.enableDebugMode = enabled;
    }
    
    /**
     * Export debug information
     */
    exportDebugInfo() {
        if (this.enhancedErrorHandler) {
            return this.enhancedErrorHandler.exportDebugInfo();
        }
        
        // Fallback debug info export
        const debugInfo = {
            timestamp: new Date().toISOString(),
            connectionStatus: this.getConnectionStatus(),
            errorLogs: JSON.parse(sessionStorage.getItem('websocket_error_logs') || '[]'),
            options: this.options
        };
        
        const blob = new Blob([JSON.stringify(debugInfo, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `websocket-debug-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    /**
     * Destroy the integration
     */
    destroy() {
        // Disconnect WebSocket
        this.disconnect();
        
        // Destroy enhanced error handler
        if (this.enhancedErrorHandler) {
            this.enhancedErrorHandler.destroy();
        }
        
        // Clear references
        this.client = null;
        this.enhancedErrorHandler = null;
        
        this.logger.log('WebSocket Enhanced Client Integration destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketEnhancedClientIntegration;
} else if (typeof window !== 'undefined') {
    window.WebSocketEnhancedClientIntegration = WebSocketEnhancedClientIntegration;
}

// Example usage
if (typeof window !== 'undefined') {
    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        // Example: Initialize WebSocket with enhanced error handling
        window.websocketClient = new WebSocketEnhancedClientIntegration({
            enableEnhancedErrorHandling: true,
            enableDebugMode: false, // Set to true for development
            enableUserFeedback: true,
            enableAutoRecovery: true,
            
            showConnectionStatus: true,
            showErrorModal: true,
            showNotifications: true,
            
            corsGuidanceEnabled: true,
            detailedErrorMessages: true,
            
            onConnect: () => {
                console.log('Application: WebSocket connected');
            },
            
            onDisconnect: (reason) => {
                console.log('Application: WebSocket disconnected:', reason);
            },
            
            onError: (error) => {
                console.error('Application: WebSocket error:', error);
            },
            
            onRecovery: () => {
                console.log('Application: WebSocket recovery completed');
            }
        });
        
        // Global debug mode toggle (Ctrl+Shift+D)
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.shiftKey && event.key === 'D') {
                if (window.websocketClient) {
                    window.websocketClient.setDebugMode(true);
                }
            }
        });
    });
}