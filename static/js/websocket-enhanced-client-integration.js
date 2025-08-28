// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * WebSocket Enhanced Client Integration
 * 
 * Integrates all enhanced error handling, user feedback, and diagnostic components
 * into a unified WebSocket client experience.
 */

class WebSocketEnhancedClientIntegration {
    constructor(client, options = {}) {
        this.client = client;
        this.options = this._mergeOptions(options);
        
        // Component instances
        this.components = {
            errorHandler: null,
            connectionStatus: null,
            fallbackNotifications: null,
            debugDiagnostics: null
        };
        
        // Integration state
        this.state = {
            initialized: false,
            debugMode: false,
            componentsReady: false
        };
        
        // Initialize integration
        this._initialize();
    }
    
    /**
     * Merge options with defaults
     */
    _mergeOptions(userOptions) {
        const defaults = {
            // Component enablement
            enableErrorHandler: true,
            enableConnectionStatus: true,
            enableFallbackNotifications: true,
            enableDebugDiagnostics: false,
            
            // Error handler options
            errorHandler: {
                showStatusIndicator: true,
                showErrorModal: true,
                showNotifications: true,
                enableAutoRecovery: true,
                enableDebugMode: false
            },
            
            // Connection status options
            connectionStatus: {
                showStatusBar: true,
                showQualityIndicator: true,
                showRetryButton: true,
                position: 'top-right',
                enableQualityMonitoring: true
            },
            
            // Fallback notifications options
            fallbackNotifications: {
                preferredMethods: ['toast', 'notification', 'banner', 'console'],
                enableQueue: true
            },
            
            // Debug diagnostics options
            debugDiagnostics: {
                showDebugPanel: false,
                collectPerformanceMetrics: true,
                enableRealTimeMonitoring: true
            },
            
            // Integration options
            enableGlobalErrorHandling: true,
            enableKeyboardShortcuts: true,
            enableContextMenu: false,
            
            // Debug options
            enableDebugConsole: false,
            debugKeySequence: ['d', 'e', 'b', 'u', 'g']
        };
        
        return this._deepMerge(defaults, userOptions);
    }
}   
 
    /**
     * Initialize the integration system
     */
    _initialize() {
        console.log('Initializing WebSocket Enhanced Client Integration...');
        
        // Initialize components in order
        this._initializeComponents();
        
        // Setup global event handlers
        this._setupGlobalEventHandlers();
        
        // Setup keyboard shortcuts
        if (this.options.enableKeyboardShortcuts) {
            this._setupKeyboardShortcuts();
        }
        
        // Setup context menu
        if (this.options.enableContextMenu) {
            this._setupContextMenu();
        }
        
        // Mark as initialized
        this.state.initialized = true;
        this.state.componentsReady = true;
        
        console.log('WebSocket Enhanced Client Integration initialized successfully');
        
        // Emit ready event
        this._emitEvent('integration_ready', {
            components: Object.keys(this.components).filter(key => this.components[key] !== null),
            options: this.options
        });
    }
    
    /**
     * Initialize all components
     */
    _initializeComponents() {
        // Initialize fallback notifications first (other components may use it)
        if (this.options.enableFallbackNotifications) {
            this.components.fallbackNotifications = new WebSocketFallbackNotifications(
                this.options.fallbackNotifications
            );
        }
        
        // Initialize error handler
        if (this.options.enableErrorHandler) {
            this.components.errorHandler = new WebSocketEnhancedErrorHandler(
                this.client,
                {
                    ...this.options.errorHandler,
                    fallbackNotifications: this.components.fallbackNotifications
                }
            );
        }
        
        // Initialize connection status
        if (this.options.enableConnectionStatus) {
            this.components.connectionStatus = new WebSocketConnectionStatus(
                this.client,
                this.components.errorHandler,
                this.options.connectionStatus
            );
        }
        
        // Initialize debug diagnostics
        if (this.options.enableDebugDiagnostics) {
            this.components.debugDiagnostics = new WebSocketDebugDiagnostics(
                this.client,
                this.components.errorHandler,
                this.options.debugDiagnostics
            );
        }
        
        // Setup component cross-communication
        this._setupComponentCommunication();
    }
    
    /**
     * Setup communication between components
     */
    _setupComponentCommunication() {
        // Error handler -> Connection status communication
        if (this.components.errorHandler && this.components.connectionStatus) {
            // Listen for error handler status changes
            window.addEventListener('websocketStatusChange', (event) => {
                // Connection status component already listens for this
            });
        }
        
        // Error handler -> Debug diagnostics communication
        if (this.components.errorHandler && this.components.debugDiagnostics) {
            // Debug diagnostics already listens to client events
        }
        
        // Fallback notifications integration
        if (this.components.fallbackNotifications) {
            // Override error handler notification method if fallback is available
            if (this.components.errorHandler) {
                const originalShowNotification = this.components.errorHandler._showNotification;
                this.components.errorHandler._showNotification = (message, type, duration) => {
                    // Try original method first
                    try {
                        originalShowNotification.call(this.components.errorHandler, message, type, duration);
                    } catch (error) {
                        // Fall back to fallback notifications
                        this.components.fallbackNotifications.notify(message, type);
                    }
                };
            }
        }
    }
    
    /**
     * Setup global event handlers
     */
    _setupGlobalEventHandlers() {
        if (!this.options.enableGlobalErrorHandling) return;
        
        // Global error handler for WebSocket-related errors
        window.addEventListener('error', (event) => {
            if (this._isWebSocketRelatedError(event.error)) {
                this._handleGlobalError(event.error);
            }
        });
        
        // Unhandled promise rejection handler
        window.addEventListener('unhandledrejection', (event) => {
            if (this._isWebSocketRelatedError(event.reason)) {
                this._handleGlobalError(event.reason);
                event.preventDefault(); // Prevent console error
            }
        });
        
        // Page visibility change handler
        document.addEventListener('visibilitychange', () => {
            this._handleVisibilityChange();
        });
        
        // Network status change handlers
        window.addEventListener('online', () => {
            this._handleNetworkStatusChange(true);
        });
        
        window.addEventListener('offline', () => {
            this._handleNetworkStatusChange(false);
        });
    }
    
    /**
     * Setup keyboard shortcuts
     */
    _setupKeyboardShortcuts() {
        let keySequence = [];
        let sequenceTimeout;
        
        document.addEventListener('keydown', (event) => {
            // Debug mode toggle (Ctrl+Shift+D)
            if (event.ctrlKey && event.shiftKey && event.key === 'D') {
                event.preventDefault();
                this.toggleDebugMode();
                return;
            }
            
            // Connection status toggle (Ctrl+Shift+S)
            if (event.ctrlKey && event.shiftKey && event.key === 'S') {
                event.preventDefault();
                this.toggleConnectionStatus();
                return;
            }
            
            // Manual reconnect (Ctrl+Shift+R)
            if (event.ctrlKey && event.shiftKey && event.key === 'R') {
                event.preventDefault();
                this.forceReconnect();
                return;
            }
            
            // Debug sequence detection
            if (!event.ctrlKey && !event.altKey && !event.metaKey) {
                keySequence.push(event.key.toLowerCase());
                
                // Limit sequence length
                if (keySequence.length > this.options.debugKeySequence.length) {
                    keySequence.shift();
                }
                
                // Check for debug sequence
                if (this._matchesDebugSequence(keySequence)) {
                    this.enableDebugMode();
                    keySequence = [];
                }
                
                // Clear sequence after timeout
                clearTimeout(sequenceTimeout);
                sequenceTimeout = setTimeout(() => {
                    keySequence = [];
                }, 2000);
            }
        });
    }
    
    /**
     * Setup context menu
     */
    _setupContextMenu() {
        document.addEventListener('contextmenu', (event) => {
            // Only show context menu on WebSocket-related elements
            if (!this._isWebSocketElement(event.target)) return;
            
            event.preventDefault();
            this._showContextMenu(event.clientX, event.clientY);
        });
        
        // Hide context menu on click elsewhere
        document.addEventListener('click', () => {
            this._hideContextMenu();
        });
    }
    
    /**
     * Handle global WebSocket-related errors
     */
    _handleGlobalError(error) {
        if (this.components.errorHandler) {
            this.components.errorHandler.handleError(error, 'global');
        } else if (this.components.fallbackNotifications) {
            this.components.fallbackNotifications.notify(
                `WebSocket Error: ${error.message}`,
                'error'
            );
        }
    }
    
    /**
     * Handle visibility change
     */
    _handleVisibilityChange() {
        const isHidden = document.hidden;
        
        this._emitEvent('visibility_change', { hidden: isHidden });
        
        // Notify components
        if (this.components.debugDiagnostics) {
            // Debug diagnostics already handles this
        }
        
        // Adjust behavior based on visibility
        if (isHidden) {
            // Page is hidden - reduce activity
            this._reduceActivity();
        } else {
            // Page is visible - resume normal activity
            this._resumeActivity();
        }
    }
    
    /**
     * Handle network status change
     */
    _handleNetworkStatusChange(isOnline) {
        this._emitEvent('network_status_change', { online: isOnline });
        
        if (isOnline) {
            // Network is back - attempt reconnection if needed
            if (!this.client.connected) {
                setTimeout(() => {
                    this.client.connect();
                }, 1000);
            }
        } else {
            // Network is offline - notify user
            if (this.components.fallbackNotifications) {
                this.components.fallbackNotifications.notify(
                    'Network connection lost. Will reconnect automatically when back online.',
                    'warning'
                );
            }
        }
    }
    
    /**
     * Public API methods
     */
    
    /**
     * Enable debug mode
     */
    enableDebugMode() {
        this.state.debugMode = true;
        
        // Enable debug in error handler
        if (this.components.errorHandler) {
            this.components.errorHandler.enableDebugMode();
        }
        
        // Show debug diagnostics panel
        if (this.components.debugDiagnostics) {
            this.components.debugDiagnostics.showDebugPanel();
        } else {
            // Create debug diagnostics if not already created
            this.components.debugDiagnostics = new WebSocketDebugDiagnostics(
                this.client,
                this.components.errorHandler,
                { ...this.options.debugDiagnostics, showDebugPanel: true }
            );
        }
        
        // Enable debug console
        if (this.options.enableDebugConsole) {
            this._enableDebugConsole();
        }
        
        this._emitEvent('debug_mode_enabled');
        console.log('WebSocket debug mode enabled');
    }
    
    /**
     * Disable debug mode
     */
    disableDebugMode() {
        this.state.debugMode = false;
        
        // Disable debug in error handler
        if (this.components.errorHandler) {
            this.components.errorHandler.disableDebugMode();
        }
        
        // Hide debug diagnostics panel
        if (this.components.debugDiagnostics) {
            this.components.debugDiagnostics.hideDebugPanel();
        }
        
        this._emitEvent('debug_mode_disabled');
        console.log('WebSocket debug mode disabled');
    }
    
    /**
     * Toggle debug mode
     */
    toggleDebugMode() {
        if (this.state.debugMode) {
            this.disableDebugMode();
        } else {
            this.enableDebugMode();
        }
    }
    
    /**
     * Toggle connection status visibility
     */
    toggleConnectionStatus() {
        if (this.components.connectionStatus) {
            const isVisible = this.components.connectionStatus.elements.statusBar &&
                            this.components.connectionStatus.elements.statusBar.style.display !== 'none';
            
            if (isVisible) {
                this.components.connectionStatus.hide();
            } else {
                this.components.connectionStatus.show();
            }
        }
    }
    
    /**
     * Force reconnection
     */
    forceReconnect() {
        console.log('Forcing WebSocket reconnection...');
        
        // Disconnect first
        if (this.client.connected) {
            this.client.disconnect();
        }
        
        // Reconnect after short delay
        setTimeout(() => {
            this.client.connect();
        }, 1000);
        
        // Notify user
        if (this.components.fallbackNotifications) {
            this.components.fallbackNotifications.notify(
                'Forcing reconnection...',
                'info'
            );
        }
    }
    
    /**
     * Get comprehensive status
     */
    getStatus() {
        const status = {
            integration: {
                initialized: this.state.initialized,
                debugMode: this.state.debugMode,
                componentsReady: this.state.componentsReady
            },
            client: {
                connected: this.client.connected,
                transport: this._getCurrentTransport()
            },
            components: {}
        };
        
        // Get status from each component
        if (this.components.errorHandler) {
            status.components.errorHandler = this.components.errorHandler.getErrorStatistics();
        }
        
        if (this.components.connectionStatus) {
            status.components.connectionStatus = this.components.connectionStatus.getConnectionStats();
        }
        
        if (this.components.fallbackNotifications) {
            status.components.fallbackNotifications = this.components.fallbackNotifications.getStats();
        }
        
        if (this.components.debugDiagnostics) {
            status.components.debugDiagnostics = this.components.debugDiagnostics.getDiagnosticSummary();
        }
        
        return status;
    }
    
    /**
     * Export comprehensive debug data
     */
    exportDebugData(format = 'json') {
        const debugData = {
            timestamp: new Date().toISOString(),
            integration: this.getStatus(),
            client: {
                connected: this.client.connected,
                transport: this._getCurrentTransport(),
                url: this.client.io ? this.client.io.uri : 'unknown'
            }
        };
        
        // Add component-specific debug data
        if (this.components.debugDiagnostics) {
            debugData.diagnostics = this.components.debugDiagnostics.diagnostics;
        }
        
        if (this.components.errorHandler) {
            debugData.errorHistory = this.components.errorHandler.errorState.errorHistory;
        }
        
        // Export using debug diagnostics if available
        if (this.components.debugDiagnostics) {
            this.components.debugDiagnostics.exportDebugData(format);
        } else {
            // Fallback export
            this._exportData(debugData, format);
        }
    }
    
    /**
     * Update configuration for all components
     */
    updateConfiguration(newOptions) {
        this.options = this._deepMerge(this.options, newOptions);
        
        // Update each component
        if (this.components.errorHandler && newOptions.errorHandler) {
            // Error handler doesn't have update method, would need to recreate
        }
        
        if (this.components.connectionStatus && newOptions.connectionStatus) {
            this.components.connectionStatus.updateOptions(newOptions.connectionStatus);
        }
        
        if (this.components.fallbackNotifications && newOptions.fallbackNotifications) {
            this.components.fallbackNotifications.updateOptions(newOptions.fallbackNotifications);
        }
        
        if (this.components.debugDiagnostics && newOptions.debugDiagnostics) {
            // Debug diagnostics doesn't have update method, would need to recreate
        }
    }
    
    /**
     * Utility methods
     */
    
    /**
     * Check if error is WebSocket-related
     */
    _isWebSocketRelatedError(error) {
        if (!error) return false;
        
        const message = error.message || error.toString();
        const lowerMessage = message.toLowerCase();
        
        return lowerMessage.includes('websocket') ||
               lowerMessage.includes('socket.io') ||
               lowerMessage.includes('cors') ||
               (error.stack && error.stack.includes('socket'));
    }
    
    /**
     * Check if element is WebSocket-related
     */
    _isWebSocketElement(element) {
        // Check for WebSocket-related classes or IDs
        const wsClasses = ['websocket', 'socket-io', 'connection-status'];
        const wsIds = ['websocket-status', 'connection-indicator'];
        
        return wsClasses.some(cls => element.classList && element.classList.contains(cls)) ||
               wsIds.some(id => element.id === id) ||
               (element.closest && element.closest('[data-websocket]'));
    }
    
    /**
     * Check if key sequence matches debug sequence
     */
    _matchesDebugSequence(sequence) {
        if (sequence.length !== this.options.debugKeySequence.length) {
            return false;
        }
        
        return sequence.every((key, index) => 
            key === this.options.debugKeySequence[index]
        );
    }
    
    /**
     * Get current transport
     */
    _getCurrentTransport() {
        if (this.client.io && this.client.io.engine && this.client.io.engine.transport) {
            return this.client.io.engine.transport.name;
        }
        return 'unknown';
    }
    
    /**
     * Reduce activity when page is hidden
     */
    _reduceActivity() {
        // Reduce monitoring frequency
        if (this.components.debugDiagnostics) {
            // Could reduce monitoring intervals
        }
        
        // Reduce status updates
        if (this.components.connectionStatus) {
            // Could reduce quality monitoring
        }
    }
    
    /**
     * Resume normal activity when page is visible
     */
    _resumeActivity() {
        // Resume normal monitoring
        if (this.components.debugDiagnostics) {
            // Could restore normal intervals
        }
        
        // Resume normal status updates
        if (this.components.connectionStatus) {
            // Could restore normal quality monitoring
        }
    }
    
    /**
     * Show context menu
     */
    _showContextMenu(x, y) {
        // Remove existing context menu
        this._hideContextMenu();
        
        const menu = document.createElement('div');
        menu.id = 'websocket-context-menu';
        menu.className = 'websocket-context-menu';
        menu.style.cssText = `
            position: fixed;
            top: ${y}px;
            left: ${x}px;
            z-index: 1080;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            padding: 0.5rem 0;
            min-width: 150px;
        `;
        
        const menuItems = [
            { text: 'Toggle Debug Mode', action: () => this.toggleDebugMode() },
            { text: 'Force Reconnect', action: () => this.forceReconnect() },
            { text: 'Export Debug Data', action: () => this.exportDebugData() },
            { text: 'Show Status', action: () => console.log(this.getStatus()) }
        ];
        
        menuItems.forEach(item => {
            const menuItem = document.createElement('div');
            menuItem.textContent = item.text;
            menuItem.style.cssText = `
                padding: 0.5rem 1rem;
                cursor: pointer;
                font-size: 0.875rem;
            `;
            
            menuItem.addEventListener('click', () => {
                item.action();
                this._hideContextMenu();
            });
            
            menuItem.addEventListener('mouseenter', () => {
                menuItem.style.backgroundColor = '#f8f9fa';
            });
            
            menuItem.addEventListener('mouseleave', () => {
                menuItem.style.backgroundColor = 'transparent';
            });
            
            menu.appendChild(menuItem);
        });
        
        document.body.appendChild(menu);
    }
    
    /**
     * Hide context menu
     */
    _hideContextMenu() {
        const menu = document.getElementById('websocket-context-menu');
        if (menu) {
            menu.remove();
        }
    }
    
    /**
     * Enable debug console
     */
    _enableDebugConsole() {
        // Add debug methods to window for console access
        window.WebSocketDebug = {
            status: () => this.getStatus(),
            reconnect: () => this.forceReconnect(),
            export: (format) => this.exportDebugData(format),
            toggleDebug: () => this.toggleDebugMode(),
            components: this.components
        };
        
        console.log('WebSocket debug console enabled. Use WebSocketDebug.* methods.');
    }
    
    /**
     * Emit custom event
     */
    _emitEvent(eventType, data = {}) {
        const event = new CustomEvent(`websocket_integration_${eventType}`, {
            detail: { ...data, timestamp: Date.now() }
        });
        
        window.dispatchEvent(event);
    }
    
    /**
     * Deep merge objects
     */
    _deepMerge(target, source) {
        const result = { ...target };
        
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = this._deepMerge(target[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }
        
        return result;
    }
    
    /**
     * Fallback export method
     */
    _exportData(data, format) {
        let content, mimeType, filename;
        
        switch (format) {
            case 'json':
                content = JSON.stringify(data, null, 2);
                mimeType = 'application/json';
                filename = `websocket-integration-debug-${Date.now()}.json`;
                break;
                
            default:
                content = JSON.stringify(data, null, 2);
                mimeType = 'application/json';
                filename = `websocket-integration-debug-${Date.now()}.json`;
        }
        
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        
        URL.revokeObjectURL(url);
    }
    
    /**
     * Destroy integration and all components
     */
    destroy() {
        // Destroy all components
        Object.values(this.components).forEach(component => {
            if (component && typeof component.destroy === 'function') {
                component.destroy();
            }
        });
        
        // Remove global event listeners
        // (Would need to store references to remove properly)
        
        // Remove context menu
        this._hideContextMenu();
        
        // Clean up debug console
        if (window.WebSocketDebug) {
            delete window.WebSocketDebug;
        }
        
        // Reset state
        this.state.initialized = false;
        this.state.componentsReady = false;
        this.components = {};
        
        console.log('WebSocket Enhanced Client Integration destroyed');
    }
}

// Factory function for easy initialization
function createEnhancedWebSocketClient(client, options = {}) {
    return new WebSocketEnhancedClientIntegration(client, options);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { 
        WebSocketEnhancedClientIntegration,
        createEnhancedWebSocketClient
    };
} else if (typeof window !== 'undefined') {
    window.WebSocketEnhancedClientIntegration = WebSocketEnhancedClientIntegration;
    window.createEnhancedWebSocketClient = createEnhancedWebSocketClient;
}