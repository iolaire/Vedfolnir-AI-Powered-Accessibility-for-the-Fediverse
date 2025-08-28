// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Enhanced WebSocket Error Handling Demo Application
 * 
 * Demonstrates the comprehensive error handling and user feedback system
 * implemented for task 10: Enhanced Client Error Handling and User Feedback
 */

class WebSocketEnhancedErrorDemo {
    constructor() {
        this.client = null;
        this.enhancedErrorHandler = null;
        this.recoveryCount = 0;
        this.errorCount = 0;
        this.debugMode = false;
        
        // Initialize demo
        this._initialize();
    }
    
    /**
     * Initialize the demo application
     */
    _initialize() {
        this._setupUI();
        this._createWebSocketClient();
        this._initializeEnhancedErrorHandler();
        this._setupEventListeners();
        
        this._log('Demo application initialized');
        this._updateStatus();
    }
    
    /**
     * Setup UI event listeners
     */
    _setupUI() {
        // Connection controls
        document.getElementById('connect-btn').addEventListener('click', () => {
            this._connect();
        });
        
        document.getElementById('disconnect-btn').addEventListener('click', () => {
            this._disconnect();
        });
        
        // Error simulation buttons
        document.getElementById('simulate-cors-btn').addEventListener('click', () => {
            this._simulateError('cors');
        });
        
        document.getElementById('simulate-auth-btn').addEventListener('click', () => {
            this._simulateError('auth');
        });
        
        document.getElementById('simulate-network-btn').addEventListener('click', () => {
            this._simulateError('network');
        });
        
        // Debug controls
        document.getElementById('toggle-debug-btn').addEventListener('click', () => {
            this._toggleDebugMode();
        });
        
        // Testing buttons
        document.getElementById('test-cors-guidance-btn').addEventListener('click', () => {
            this._testCORSGuidance();
        });
        
        document.getElementById('test-fallback-notifications-btn').addEventListener('click', () => {
            this._testFallbackNotifications();
        });
        
        document.getElementById('test-recovery-system-btn').addEventListener('click', () => {
            this._testRecoverySystem();
        });
        
        document.getElementById('export-debug-btn').addEventListener('click', () => {
            this._exportDebugInfo();
        });
        
        // Notification testing
        document.getElementById('test-success-notification-btn').addEventListener('click', () => {
            this._testNotification('success', 'This is a success notification!');
        });
        
        document.getElementById('test-warning-notification-btn').addEventListener('click', () => {
            this._testNotification('warning', 'This is a warning notification!');
        });
        
        document.getElementById('test-error-notification-btn').addEventListener('click', () => {
            this._testNotification('error', 'This is an error notification!');
        });
        
        document.getElementById('test-info-notification-btn').addEventListener('click', () => {
            this._testNotification('info', 'This is an info notification!');
        });
        
        // Debug controls
        document.getElementById('show-system-info-btn').addEventListener('click', () => {
            this._showSystemInfo();
        });
        
        document.getElementById('clear-log-btn').addEventListener('click', () => {
            this._clearLog();
        });
    }
    
    /**
     * Create WebSocket client
     */
    _createWebSocketClient() {
        this.client = io('/', {
            autoConnect: false,
            transports: ['websocket', 'polling']
        });
        
        this._log('WebSocket client created');
    }
    
    /**
     * Initialize enhanced error handler
     */
    _initializeEnhancedErrorHandler() {
        if (typeof WebSocketEnhancedClientErrorHandler !== 'undefined') {
            this.enhancedErrorHandler = new WebSocketEnhancedClientErrorHandler(this.client, {
                enableUserFeedback: true,
                enableAutoRecovery: true,
                enableDebugMode: false,
                
                showConnectionStatus: true,
                showErrorModal: true,
                showNotifications: true,
                
                corsGuidanceEnabled: true,
                detailedErrorMessages: true,
                
                onErrorCallback: (category, error, errorInfo) => {
                    this._handleDemoError(category, error, errorInfo);
                },
                
                onRecoveryCallback: () => {
                    this._handleDemoRecovery();
                }
            });
            
            this._log('Enhanced error handler initialized');
        } else {
            this._log('Enhanced error handler not available', 'error');
        }
    }
    
    /**
     * Setup event listeners
     */
    _setupEventListeners() {
        // WebSocket events
        this.client.on('connect', () => {
            this._log('Connected to WebSocket server', 'success');
            this._updateStatus();
        });
        
        this.client.on('disconnect', (reason) => {
            this._log(`Disconnected: ${reason}`, 'warning');
            this._updateStatus();
        });
        
        this.client.on('connect_error', (error) => {
            this.errorCount++;
            this._log(`Connection error: ${error.message}`, 'error');
            this._updateStatus();
        });
        
        this.client.on('reconnect', () => {
            this.recoveryCount++;
            this._log('Reconnected successfully', 'success');
            this._updateStatus();
        });
        
        // Enhanced error handler events
        window.addEventListener('websocket_recovery', (event) => {
            this._log(`Recovery event: ${event.detail.type}`, 'info');
        });
    }
    
    /**
     * Connect to WebSocket
     */
    _connect() {
        this._log('Attempting to connect...');
        this.client.connect();
    }
    
    /**
     * Disconnect from WebSocket
     */
    _disconnect() {
        this._log('Disconnecting...');
        this.client.disconnect();
    }
    
    /**
     * Simulate different types of errors
     */
    _simulateError(type) {
        this._log(`Simulating ${type} error...`, 'warning');
        
        if (this.client && typeof this.client.simulateError === 'function') {
            this.client.simulateError(type);
        } else {
            // Fallback error simulation
            let error;
            switch (type) {
                case 'cors':
                    error = new Error('CORS policy blocked the connection');
                    break;
                case 'auth':
                    error = new Error('Authentication required');
                    break;
                case 'network':
                    error = new Error('Network connection failed');
                    break;
            }
            
            if (this.enhancedErrorHandler) {
                this.enhancedErrorHandler._handleConnectionError(error);
            }
        }
    }
    
    /**
     * Toggle debug mode
     */
    _toggleDebugMode() {
        this.debugMode = !this.debugMode;
        
        if (this.enhancedErrorHandler) {
            this.enhancedErrorHandler.toggleDebugMode();
        }
        
        this._log(`Debug mode ${this.debugMode ? 'enabled' : 'disabled'}`, 'info');
        this._updateStatus();
    }
    
    /**
     * Test CORS guidance functionality
     */
    _testCORSGuidance() {
        this._log('Testing CORS guidance system...', 'info');
        
        if (this.enhancedErrorHandler) {
            const corsError = new Error('CORS policy blocked the connection');
            this.enhancedErrorHandler._handleCORSError({
                message: 'CORS policy violation detected',
                category: 'cors',
                severity: 'warning'
            });
        }
        
        this._log('CORS guidance test completed', 'success');
    }
    
    /**
     * Test fallback notifications
     */
    _testFallbackNotifications() {
        this._log('Testing fallback notification system...', 'info');
        
        if (this.enhancedErrorHandler && this.enhancedErrorHandler.components.fallbackNotifications) {
            const notifications = this.enhancedErrorHandler.components.fallbackNotifications;
            
            // Test different notification methods
            notifications.notify('Testing toast notification', 'info');
            
            setTimeout(() => {
                notifications.notify('Testing banner notification', 'warning');
            }, 1000);
            
            setTimeout(() => {
                notifications.notify('Testing console notification', 'error');
            }, 2000);
        }
        
        this._log('Fallback notification test completed', 'success');
    }
    
    /**
     * Test recovery system
     */
    _testRecoverySystem() {
        this._log('Testing automatic recovery system...', 'info');
        
        // Simulate connection failure and recovery
        this._simulateError('network');
        
        setTimeout(() => {
            this._log('Simulating recovery attempt...', 'info');
            this.recoveryCount++;
            this._updateStatus();
            
            if (this.enhancedErrorHandler) {
                this.enhancedErrorHandler._handleRecoverySuccess();
            }
        }, 3000);
        
        this._log('Recovery system test initiated', 'success');
    }
    
    /**
     * Test notification with specific type
     */
    _testNotification(type, message) {
        this._log(`Testing ${type} notification: ${message}`, 'info');
        
        if (this.enhancedErrorHandler && this.enhancedErrorHandler.components.fallbackNotifications) {
            this.enhancedErrorHandler.components.fallbackNotifications.notify(message, type);
        }
    }
    
    /**
     * Export debug information
     */
    _exportDebugInfo() {
        this._log('Exporting debug information...', 'info');
        
        if (this.enhancedErrorHandler) {
            this.enhancedErrorHandler.exportDebugInfo();
        } else {
            // Fallback debug export
            const debugInfo = {
                timestamp: new Date().toISOString(),
                client: {
                    connected: this.client ? this.client.connected : false,
                    url: this.client ? this.client.url : null
                },
                demo: {
                    errorCount: this.errorCount,
                    recoveryCount: this.recoveryCount,
                    debugMode: this.debugMode
                },
                browser: {
                    userAgent: navigator.userAgent,
                    url: window.location.href
                }
            };
            
            const blob = new Blob([JSON.stringify(debugInfo, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `websocket-demo-debug-${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        this._log('Debug information exported', 'success');
    }
    
    /**
     * Show system information
     */
    _showSystemInfo() {
        const systemInfo = {
            'Browser': navigator.userAgent,
            'Platform': navigator.platform,
            'Language': navigator.language,
            'Online': navigator.onLine,
            'WebSocket Support': 'WebSocket' in window,
            'Socket.IO Available': typeof io !== 'undefined',
            'Enhanced Error Handler': typeof WebSocketEnhancedClientErrorHandler !== 'undefined',
            'Connection Status': this.client ? (this.client.connected ? 'Connected' : 'Disconnected') : 'Not initialized',
            'Debug Mode': this.debugMode,
            'Error Count': this.errorCount,
            'Recovery Count': this.recoveryCount
        };
        
        this._log('=== System Information ===', 'info');
        Object.entries(systemInfo).forEach(([key, value]) => {
            this._log(`${key}: ${value}`, 'info');
        });
        this._log('=== End System Information ===', 'info');
    }
    
    /**
     * Handle demo-specific errors
     */
    _handleDemoError(category, error, errorInfo) {
        this.errorCount++;
        this._log(`Demo error handled - Category: ${category}, Error: ${error.message}`, 'error');
        this._updateStatus();
    }
    
    /**
     * Handle demo recovery
     */
    _handleDemoRecovery() {
        this.recoveryCount++;
        this._log('Demo recovery completed', 'success');
        this._updateStatus();
    }
    
    /**
     * Update status display
     */
    _updateStatus() {
        // Connection status
        const connectionStatus = document.getElementById('connection-status');
        if (connectionStatus) {
            const status = this.client ? (this.client.connected ? 'Connected' : 'Disconnected') : 'Not initialized';
            const className = this.client && this.client.connected ? 'text-success' : 'text-danger';
            connectionStatus.textContent = status;
            connectionStatus.className = className;
        }
        
        // Error handler status
        const errorHandlerStatus = document.getElementById('error-handler-status');
        if (errorHandlerStatus) {
            const status = this.enhancedErrorHandler ? 'Initialized' : 'Not available';
            const className = this.enhancedErrorHandler ? 'text-success' : 'text-warning';
            errorHandlerStatus.textContent = status;
            errorHandlerStatus.className = className;
        }
        
        // Counters
        const recoveryCountElement = document.getElementById('recovery-count');
        if (recoveryCountElement) {
            recoveryCountElement.textContent = this.recoveryCount;
        }
        
        const errorCountElement = document.getElementById('error-count');
        if (errorCountElement) {
            errorCountElement.textContent = this.errorCount;
        }
        
        // Debug mode button
        const debugButton = document.getElementById('toggle-debug-btn');
        if (debugButton) {
            debugButton.className = this.debugMode ? 'btn btn-warning' : 'btn btn-info';
            debugButton.innerHTML = `<i class="bi bi-bug me-1"></i>${this.debugMode ? 'Disable' : 'Enable'} Debug Mode`;
        }
    }
    
    /**
     * Log message to debug output
     */
    _log(message, type = 'info') {
        const logOutput = document.getElementById('debug-log');
        if (!logOutput) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const typeColors = {
            info: '#17a2b8',
            success: '#28a745',
            warning: '#ffc107',
            error: '#dc3545'
        };
        
        const color = typeColors[type] || typeColors.info;
        const logEntry = document.createElement('div');
        logEntry.innerHTML = `<span style="color: #6c757d;">[${timestamp}]</span> <span style="color: ${color};">[${type.toUpperCase()}]</span> ${message}`;
        
        logOutput.appendChild(logEntry);
        logOutput.scrollTop = logOutput.scrollHeight;
        
        // Also log to console
        console.log(`[WebSocket Demo] [${type.toUpperCase()}] ${message}`);
    }
    
    /**
     * Clear debug log
     */
    _clearLog() {
        const logOutput = document.getElementById('debug-log');
        if (logOutput) {
            logOutput.innerHTML = '<div class="text-muted">Debug log cleared...</div>';
        }
    }
}

// Initialize demo when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.websocketDemo = new WebSocketEnhancedErrorDemo();
});