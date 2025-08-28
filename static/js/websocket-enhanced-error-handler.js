// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Enhanced WebSocket Client Error Handling and User Feedback System
 * 
 * Provides comprehensive error handling with:
 * - User-friendly error message system with specific CORS guidance
 * - Visual connection status indicators with retry options
 * - Automatic error recovery with user notification
 * - Fallback notification mechanisms for connection failures
 * - Debug mode with detailed connection diagnostics
 */

class WebSocketEnhancedErrorHandler {
    constructor(client, options = {}) {
        this.client = client;
        this.options = this._mergeOptions(options);
        this.logger = console;
        
        // Error handling state
        this.errorState = {
            currentError: null,
            errorHistory: [],
            consecutiveErrors: 0,
            lastErrorTime: null,
            recoveryAttempts: 0,
            isRecovering: false,
            debugMode: false
        };
        
        // UI elements
        this.uiElements = {
            statusIndicator: null,
            errorModal: null,
            notificationContainer: null,
            debugPanel: null
        };
        
        // Error message templates
        this.errorMessages = this._initializeErrorMessages();
        
        // Recovery strategies
        this.recoveryStrategies = this._initializeRecoveryStrategies();
        
        // Initialize UI components
        this._initializeUI();
        
        // Setup event listeners
        this._setupEventListeners();
        
        this.logger.log('Enhanced WebSocket Error Handler initialized');
    }
    
    /**
     * Merge user options with defaults
     */
    _mergeOptions(userOptions) {
        const defaults = {
            // UI Configuration
            showStatusIndicator: true,
            showErrorModal: true,
            showNotifications: true,
            enableDebugMode: false,
            
            // Error Display Configuration
            maxErrorHistorySize: 50,
            errorDisplayDuration: 5000,
            notificationPosition: 'top-right',
            
            // Recovery Configuration
            enableAutoRecovery: true,
            maxRecoveryAttempts: 3,
            recoveryDelay: 2000,
            
            // Debug Configuration
            enableDetailedLogging: false,
            showStackTraces: false,
            enablePerformanceMetrics: false,
            
            // Fallback Configuration
            enableFallbackNotifications: true,
            fallbackMethods: ['toast', 'console', 'alert'],
            
            // Customization
            customErrorMessages: {},
            customRecoveryStrategies: {},
            onError: null,
            onRecovery: null
        };
        
        return { ...defaults, ...userOptions };
    }
    
    /**
     * Initialize error message templates
     */
    _initializeErrorMessages() {
        return {
            cors: {
                title: 'Connection Issue',
                message: 'Unable to connect due to security restrictions.',
                details: 'This usually happens when accessing the application from a different URL than expected.',
                actions: [
                    'Check that you\'re using the correct URL',
                    'Try refreshing the page',
                    'Clear your browser cache',
                    'Contact support if the issue persists'
                ],
                icon: 'bi-shield-exclamation',
                severity: 'warning'
            },
            
            authentication: {
                title: 'Authentication Required',
                message: 'Your session has expired or authentication is required.',
                details: 'Please log in again to continue using real-time features.',
                actions: [
                    'Click here to log in again',
                    'Check if cookies are enabled',
                    'Clear browser data if issue persists'
                ],
                icon: 'bi-person-lock',
                severity: 'error',
                actionButton: {
                    text: 'Log In',
                    action: () => window.location.href = '/login'
                }
            },
            
            network: {
                title: 'Connection Problem',
                message: 'Unable to establish a stable connection to the server.',
                details: 'This might be due to network issues or server maintenance.',
                actions: [
                    'Check your internet connection',
                    'Try refreshing the page',
                    'Wait a moment and try again',
                    'Switch to a different network if available'
                ],
                icon: 'bi-wifi-off',
                severity: 'error'
            },
            
            timeout: {
                title: 'Connection Timeout',
                message: 'The connection is taking longer than expected.',
                details: 'This might be due to slow network conditions or server load.',
                actions: [
                    'Wait for automatic retry',
                    'Check your internet speed',
                    'Try refreshing the page',
                    'Contact support if issue continues'
                ],
                icon: 'bi-clock-history',
                severity: 'warning'
            },
            
            transport: {
                title: 'Connection Method Issue',
                message: 'Having trouble with the current connection method.',
                details: 'Switching to a more compatible connection method.',
                actions: [
                    'Automatic fallback in progress',
                    'Please wait while we reconnect',
                    'Try refreshing if issue persists'
                ],
                icon: 'bi-arrow-repeat',
                severity: 'info'
            },
            
            server: {
                title: 'Server Issue',
                message: 'The server is experiencing difficulties.',
                details: 'This is likely temporary and should resolve automatically.',
                actions: [
                    'Wait for automatic retry',
                    'Try refreshing the page',
                    'Check server status page',
                    'Contact support if issue persists'
                ],
                icon: 'bi-server',
                severity: 'error'
            },
            
            unknown: {
                title: 'Connection Issue',
                message: 'An unexpected connection problem occurred.',
                details: 'We\'re working to resolve this automatically.',
                actions: [
                    'Wait for automatic retry',
                    'Try refreshing the page',
                    'Contact support with error details'
                ],
                icon: 'bi-exclamation-triangle',
                severity: 'warning'
            }
        };
    }
    
    /**
     * Initialize recovery strategies
     */
    _initializeRecoveryStrategies() {
        return {
            cors: async (errorInfo) => {
                this._showUserMessage('cors', {
                    additionalInfo: 'Attempting to use alternative connection method...'
                });
                
                // Try polling fallback
                if (this.client._reconfigureTransports) {
                    this.client._reconfigureTransports(['polling']);
                    await this._delay(2000);
                    return this.client.connect();
                }
                return false;
            },
            
            authentication: async (errorInfo) => {
                this._showUserMessage('authentication');
                
                // Attempt session refresh
                try {
                    const response = await fetch('/api/auth/refresh', {
                        method: 'POST',
                        credentials: 'same-origin'
                    });
                    
                    if (response.ok) {
                        await this._delay(1000);
                        return this.client.connect();
                    }
                } catch (e) {
                    this.logger.warn('Session refresh failed:', e);
                }
                
                return false;
            },
            
            network: async (errorInfo) => {
                this._showUserMessage('network', {
                    additionalInfo: 'Retrying connection with increased timeout...'
                });
                
                // Increase timeout and retry
                if (this.client._increaseTimeouts) {
                    this.client._increaseTimeouts();
                }
                
                await this._delay(this.options.recoveryDelay);
                return this.client.connect();
            },
            
            timeout: async (errorInfo) => {
                this._showUserMessage('timeout', {
                    additionalInfo: 'Using longer timeout for slow connections...'
                });
                
                // Increase timeout significantly
                if (this.client.io && this.client.io.opts) {
                    const originalTimeout = this.client.io.opts.timeout;
                    this.client.io.opts.timeout = Math.min(originalTimeout * 2, 60000);
                }
                
                await this._delay(this.options.recoveryDelay * 2);
                return this.client.connect();
            },
            
            transport: async (errorInfo) => {
                this._showUserMessage('transport');
                
                // Switch to polling transport
                if (this.client._reconfigureTransports) {
                    this.client._reconfigureTransports(['polling']);
                    await this._delay(1000);
                    return this.client.connect();
                }
                return false;
            },
            
            server: async (errorInfo) => {
                this._showUserMessage('server', {
                    additionalInfo: 'Waiting for server to become available...'
                });
                
                // Wait longer for server issues
                await this._delay(this.options.recoveryDelay * 3);
                return this.client.connect();
            }
        };
    }
    
    /**
     * Initialize UI components
     */
    _initializeUI() {
        this._createStatusIndicator();
        this._createNotificationContainer();
        this._createErrorModal();
        
        if (this.options.enableDebugMode) {
            this._createDebugPanel();
        }
    }
    
    /**
     * Create connection status indicator
     */
    _createStatusIndicator() {
        if (!this.options.showStatusIndicator) return;
        
        // Check if status indicator already exists
        let statusIndicator = document.getElementById('websocket-status-indicator');
        
        if (!statusIndicator) {
            statusIndicator = document.createElement('div');
            statusIndicator.id = 'websocket-status-indicator';
            statusIndicator.className = 'websocket-status-indicator';
            
            // Add to page (try multiple locations)
            const containers = [
                document.querySelector('.navbar'),
                document.querySelector('header'),
                document.querySelector('body')
            ];
            
            for (const container of containers) {
                if (container) {
                    container.appendChild(statusIndicator);
                    break;
                }
            }
        }
        
        this.uiElements.statusIndicator = statusIndicator;
        this._updateStatusIndicator('initializing', 'Initializing connection...');
        
        // Add CSS if not present
        this._addStatusIndicatorCSS();
    }
    
    /**
     * Create notification container
     */
    _createNotificationContainer() {
        if (!this.options.showNotifications) return;
        
        let container = document.getElementById('websocket-notifications');
        
        if (!container) {
            container = document.createElement('div');
            container.id = 'websocket-notifications';
            container.className = `websocket-notifications ${this.options.notificationPosition}`;
            document.body.appendChild(container);
        }
        
        this.uiElements.notificationContainer = container;
        this._addNotificationCSS();
    }
    
    /**
     * Create error modal
     */
    _createErrorModal() {
        if (!this.options.showErrorModal) return;
        
        const modalHTML = `
            <div class="modal fade" id="websocket-error-modal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                <span id="error-modal-title">Connection Issue</span>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="error-modal-message" class="mb-3"></div>
                            <div id="error-modal-details" class="text-muted mb-3"></div>
                            <div id="error-modal-actions" class="list-group list-group-flush"></div>
                            <div id="error-modal-debug" class="mt-3" style="display: none;">
                                <h6>Debug Information:</h6>
                                <pre class="bg-light p-2 rounded small"></pre>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" id="error-modal-action-btn" class="btn btn-primary" style="display: none;">
                                Action
                            </button>
                            <button type="button" id="error-modal-retry-btn" class="btn btn-success">
                                <i class="bi bi-arrow-clockwise me-1"></i>
                                Retry Connection
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if present
        const existingModal = document.getElementById('websocket-error-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.uiElements.errorModal = document.getElementById('websocket-error-modal');
        
        // Setup modal event listeners
        this._setupModalEventListeners();
    }
    
    /**
     * Create debug panel
     */
    _createDebugPanel() {
        const debugHTML = `
            <div id="websocket-debug-panel" class="websocket-debug-panel">
                <div class="debug-header">
                    <h6><i class="bi bi-bug me-1"></i> WebSocket Debug</h6>
                    <button type="button" class="btn-close btn-close-white" id="debug-panel-close"></button>
                </div>
                <div class="debug-content">
                    <div class="debug-section">
                        <strong>Connection Status:</strong>
                        <span id="debug-connection-status">Unknown</span>
                    </div>
                    <div class="debug-section">
                        <strong>Transport:</strong>
                        <span id="debug-transport">Unknown</span>
                    </div>
                    <div class="debug-section">
                        <strong>Error Count:</strong>
                        <span id="debug-error-count">0</span>
                    </div>
                    <div class="debug-section">
                        <strong>Last Error:</strong>
                        <div id="debug-last-error" class="debug-error-details">None</div>
                    </div>
                    <div class="debug-section">
                        <strong>Performance:</strong>
                        <div id="debug-performance" class="debug-performance-metrics">
                            <div>Latency: <span id="debug-latency">-</span>ms</div>
                            <div>Uptime: <span id="debug-uptime">-</span></div>
                        </div>
                    </div>
                    <div class="debug-actions">
                        <button type="button" class="btn btn-sm btn-outline-light" id="debug-clear-errors">
                            Clear Errors
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-light" id="debug-export-logs">
                            Export Logs
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', debugHTML);
        this.uiElements.debugPanel = document.getElementById('websocket-debug-panel');
        
        this._setupDebugPanelEventListeners();
        this._addDebugPanelCSS();
    }
    
    /**
     * Setup event listeners
     */
    _setupEventListeners() {
        // Client error events
        this.client.on('connect_error', (error) => {
            this.handleError(error, 'connect_error');
        });
        
        this.client.on('disconnect', (reason) => {
            this.handleDisconnect(reason);
        });
        
        this.client.on('reconnect_error', (error) => {
            this.handleError(error, 'reconnect_error');
        });
        
        this.client.on('reconnect_failed', () => {
            this.handleReconnectFailed();
        });
        
        // Server error events
        this.client.on('websocket_error', (errorData) => {
            this.handleServerError(errorData);
        });
        
        this.client.on('cors_error', (errorData) => {
            this.handleCORSError(errorData);
        });
        
        this.client.on('auth_error', (errorData) => {
            this.handleAuthError(errorData);
        });
        
        // Connection events
        this.client.on('connect', () => {
            this.handleConnectionSuccess();
        });
        
        this.client.on('reconnect', () => {
            this.handleReconnectionSuccess();
        });
        
        // Recovery events
        this.client.on('recovery_event', (eventData) => {
            this.handleRecoveryEvent(eventData);
        });
        
        // Global error handler
        window.addEventListener('error', (event) => {
            if (event.error && event.error.message && 
                event.error.message.toLowerCase().includes('websocket')) {
                this.handleError(event.error, 'global_error');
            }
        });
        
        // Visibility change for debug mode
        if (this.options.enableDebugMode) {
            document.addEventListener('visibilitychange', () => {
                this._updateDebugPanel();
            });
        }
    }
    
    /**
     * Handle general errors
     */
    handleError(error, context = 'unknown') {
        const errorInfo = this._analyzeError(error, context);
        
        // Update error state
        this.errorState.currentError = errorInfo;
        this.errorState.consecutiveErrors++;
        this.errorState.lastErrorTime = Date.now();
        this._addToErrorHistory(errorInfo);
        
        // Update UI
        this._updateStatusIndicator('error', errorInfo.message);
        
        // Show user-friendly message
        this._showUserMessage(errorInfo.category, errorInfo);
        
        // Attempt recovery if enabled
        if (this.options.enableAutoRecovery && !this.errorState.isRecovering) {
            this._attemptRecovery(errorInfo);
        }
        
        // Update debug panel
        if (this.options.enableDebugMode) {
            this._updateDebugPanel();
        }
        
        // Call custom error handler
        if (this.options.onError) {
            try {
                this.options.onError(errorInfo);
            } catch (e) {
                this.logger.error('Error in custom error handler:', e);
            }
        }
        
        this.logger.error('WebSocket error handled:', errorInfo);
    }
    
    /**
     * Handle disconnection
     */
    handleDisconnect(reason) {
        this._updateStatusIndicator('disconnected', `Disconnected: ${reason}`);
        
        if (reason !== 'io client disconnect' && reason !== 'io server disconnect') {
            this._showNotification('Connection lost. Attempting to reconnect...', 'warning');
        }
        
        if (this.options.enableDebugMode) {
            this._updateDebugPanel();
        }
    }
    
    /**
     * Handle reconnection failure
     */
    handleReconnectFailed() {
        const errorInfo = {
            category: 'network',
            message: 'Failed to reconnect after multiple attempts',
            severity: 'error',
            timestamp: new Date()
        };
        
        this._updateStatusIndicator('failed', 'Connection failed');
        this._showUserMessage('network', errorInfo);
        
        // Show error modal for critical failures
        if (this.options.showErrorModal) {
            this._showErrorModal(errorInfo);
        }
    }
    
    /**
     * Handle server-sent errors
     */
    handleServerError(errorData) {
        const errorInfo = {
            category: errorData.category || 'server',
            message: errorData.message || 'Server error occurred',
            severity: errorData.severity || 'error',
            code: errorData.error_code,
            suggestions: errorData.recovery_suggestions || [],
            timestamp: new Date(errorData.timestamp || Date.now())
        };
        
        this.handleError(new Error(errorInfo.message), 'server_error');
    }
    
    /**
     * Handle CORS-specific errors
     */
    handleCORSError(errorData) {
        const errorInfo = {
            category: 'cors',
            message: 'CORS policy blocked the connection',
            severity: 'warning',
            code: errorData.error_code,
            details: errorData,
            timestamp: new Date()
        };
        
        this._showUserMessage('cors', errorInfo);
        this._updateStatusIndicator('cors-error', 'CORS Issue');
        
        // Attempt CORS recovery
        if (this.options.enableAutoRecovery) {
            this._attemptRecovery(errorInfo);
        }
    }
    
    /**
     * Handle authentication errors
     */
    handleAuthError(errorData) {
        const errorInfo = {
            category: 'authentication',
            message: 'Authentication required',
            severity: 'error',
            code: errorData.error_code,
            action: errorData.action_required,
            timestamp: new Date()
        };
        
        this._showUserMessage('authentication', errorInfo);
        this._updateStatusIndicator('auth-error', 'Authentication Required');
        
        // Show modal for auth errors
        if (this.options.showErrorModal) {
            this._showErrorModal(errorInfo);
        }
    }
    
    /**
     * Handle successful connection
     */
    handleConnectionSuccess() {
        // Reset error state
        this.errorState.consecutiveErrors = 0;
        this.errorState.currentError = null;
        this.errorState.isRecovering = false;
        this.errorState.recoveryAttempts = 0;
        
        // Update UI
        this._updateStatusIndicator('connected', 'Connected');
        this._showNotification('Connected successfully!', 'success');
        
        // Hide error modal if showing
        if (this.uiElements.errorModal) {
            const modal = bootstrap.Modal.getInstance(this.uiElements.errorModal);
            if (modal) {
                modal.hide();
            }
        }
        
        // Update debug panel
        if (this.options.enableDebugMode) {
            this._updateDebugPanel();
        }
        
        // Call custom recovery handler
        if (this.options.onRecovery) {
            try {
                this.options.onRecovery();
            } catch (e) {
                this.logger.error('Error in custom recovery handler:', e);
            }
        }
    }
    
    /**
     * Handle successful reconnection
     */
    handleReconnectionSuccess() {
        this.handleConnectionSuccess();
        this._showNotification('Reconnected successfully!', 'success');
    }
    
    /**
     * Handle recovery events
     */
    handleRecoveryEvent(eventData) {
        if (this.options.enableDebugMode) {
            this.logger.log('Recovery event:', eventData);
            this._updateDebugPanel();
        }
        
        switch (eventData.type) {
            case 'recovery_start':
                this._updateStatusIndicator('recovering', 'Attempting recovery...');
                break;
            case 'recovery_success':
                this.handleConnectionSuccess();
                break;
            case 'recovery_failed':
                this.handleReconnectFailed();
                break;
            case 'polling_mode_entered':
                this._showNotification('Switched to compatibility mode', 'info');
                break;
        }
    }
    
    /**
     * Analyze error to determine category and details
     */
    _analyzeError(error, context) {
        const message = error.message || error.toString();
        const lowerMessage = message.toLowerCase();
        
        let category = 'unknown';
        let severity = 'error';
        
        // Categorize error
        if (lowerMessage.includes('cors') || lowerMessage.includes('cross-origin')) {
            category = 'cors';
            severity = 'warning';
        } else if (lowerMessage.includes('auth') || lowerMessage.includes('unauthorized')) {
            category = 'authentication';
            severity = 'error';
        } else if (lowerMessage.includes('timeout') || lowerMessage.includes('timed out')) {
            category = 'timeout';
            severity = 'warning';
        } else if (lowerMessage.includes('transport') || lowerMessage.includes('websocket')) {
            category = 'transport';
            severity = 'info';
        } else if (lowerMessage.includes('network') || lowerMessage.includes('connection')) {
            category = 'network';
            severity = 'error';
        } else if (lowerMessage.includes('server') || lowerMessage.includes('5')) {
            category = 'server';
            severity = 'error';
        }
        
        return {
            category,
            severity,
            message,
            originalError: error,
            context,
            timestamp: new Date(),
            stack: error.stack
        };
    }
    
    /**
     * Show user-friendly message
     */
    _showUserMessage(category, errorInfo = {}) {
        const messageTemplate = this.errorMessages[category] || this.errorMessages.unknown;
        
        // Show notification
        this._showNotification(messageTemplate.message, messageTemplate.severity);
        
        // Show detailed modal for critical errors
        if (messageTemplate.severity === 'error' && this.options.showErrorModal) {
            this._showErrorModal({
                ...messageTemplate,
                ...errorInfo
            });
        }
    }
    
    /**
     * Show notification
     */
    _showNotification(message, type = 'info', duration = null) {
        if (!this.options.showNotifications || !this.uiElements.notificationContainer) {
            // Fallback notification methods
            this._showFallbackNotification(message, type);
            return;
        }
        
        const notification = document.createElement('div');
        notification.className = `websocket-notification alert alert-${this._getBootstrapAlertClass(type)} alert-dismissible fade show`;
        
        const icon = this._getNotificationIcon(type);
        notification.innerHTML = `
            <i class="bi ${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        this.uiElements.notificationContainer.appendChild(notification);
        
        // Auto-remove after duration
        const displayDuration = duration || this.options.errorDisplayDuration;
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, displayDuration);
    }
    
    /**
     * Show error modal
     */
    _showErrorModal(errorInfo) {
        if (!this.uiElements.errorModal) return;
        
        const messageTemplate = this.errorMessages[errorInfo.category] || this.errorMessages.unknown;
        
        // Update modal content
        document.getElementById('error-modal-title').textContent = messageTemplate.title;
        document.getElementById('error-modal-message').textContent = messageTemplate.message;
        document.getElementById('error-modal-details').textContent = messageTemplate.details;
        
        // Update icon
        const titleIcon = this.uiElements.errorModal.querySelector('.modal-title i');
        if (titleIcon) {
            titleIcon.className = `bi ${messageTemplate.icon} me-2`;
        }
        
        // Update actions list
        const actionsList = document.getElementById('error-modal-actions');
        actionsList.innerHTML = '';
        
        messageTemplate.actions.forEach(action => {
            const actionItem = document.createElement('div');
            actionItem.className = 'list-group-item';
            actionItem.innerHTML = `<i class="bi bi-check-circle me-2 text-success"></i>${action}`;
            actionsList.appendChild(actionItem);
        });
        
        // Setup action button
        const actionBtn = document.getElementById('error-modal-action-btn');
        if (messageTemplate.actionButton) {
            actionBtn.textContent = messageTemplate.actionButton.text;
            actionBtn.style.display = 'inline-block';
            actionBtn.onclick = messageTemplate.actionButton.action;
        } else {
            actionBtn.style.display = 'none';
        }
        
        // Setup debug info
        if (this.options.enableDebugMode && errorInfo.stack) {
            const debugSection = document.getElementById('error-modal-debug');
            const debugPre = debugSection.querySelector('pre');
            debugPre.textContent = JSON.stringify({
                error: errorInfo.message,
                category: errorInfo.category,
                timestamp: errorInfo.timestamp,
                stack: errorInfo.stack
            }, null, 2);
            debugSection.style.display = 'block';
        }
        
        // Show modal
        const modal = new bootstrap.Modal(this.uiElements.errorModal);
        modal.show();
    }
    
    /**
     * Update status indicator
     */
    _updateStatusIndicator(status, message) {
        if (!this.uiElements.statusIndicator) return;
        
        const statusConfig = {
            initializing: { class: 'status-initializing', icon: 'bi-hourglass-split', color: '#6c757d' },
            connected: { class: 'status-connected', icon: 'bi-wifi', color: '#198754' },
            disconnected: { class: 'status-disconnected', icon: 'bi-wifi-off', color: '#fd7e14' },
            error: { class: 'status-error', icon: 'bi-exclamation-triangle', color: '#dc3545' },
            recovering: { class: 'status-recovering', icon: 'bi-arrow-clockwise', color: '#0d6efd' },
            'cors-error': { class: 'status-cors-error', icon: 'bi-shield-exclamation', color: '#fd7e14' },
            'auth-error': { class: 'status-auth-error', icon: 'bi-person-lock', color: '#dc3545' },
            failed: { class: 'status-failed', icon: 'bi-x-circle', color: '#dc3545' }
        };
        
        const config = statusConfig[status] || statusConfig.error;
        
        this.uiElements.statusIndicator.className = `websocket-status-indicator ${config.class}`;
        this.uiElements.statusIndicator.innerHTML = `
            <i class="bi ${config.icon}"></i>
            <span class="status-text">${message}</span>
        `;
        this.uiElements.statusIndicator.style.color = config.color;
        this.uiElements.statusIndicator.title = message;
    }
    
    /**
     * Attempt error recovery
     */
    async _attemptRecovery(errorInfo) {
        if (this.errorState.isRecovering || 
            this.errorState.recoveryAttempts >= this.options.maxRecoveryAttempts) {
            return;
        }
        
        this.errorState.isRecovering = true;
        this.errorState.recoveryAttempts++;
        
        this._updateStatusIndicator('recovering', 'Attempting recovery...');
        
        try {
            const strategy = this.recoveryStrategies[errorInfo.category] || 
                           this.options.customRecoveryStrategies[errorInfo.category];
            
            if (strategy) {
                const success = await strategy(errorInfo);
                
                if (success) {
                    this._showNotification('Recovery successful!', 'success');
                } else {
                    this._showNotification('Recovery failed. Please try manually.', 'warning');
                }
            } else {
                // Generic recovery attempt
                await this._delay(this.options.recoveryDelay);
                this.client.connect();
            }
        } catch (error) {
            this.logger.error('Recovery attempt failed:', error);
            this._showNotification('Recovery failed. Please try manually.', 'warning');
        } finally {
            this.errorState.isRecovering = false;
        }
    }
    
    /**
     * Show fallback notifications
     */
    _showFallbackNotification(message, type) {
        if (!this.options.enableFallbackNotifications) return;
        
        for (const method of this.options.fallbackMethods) {
            try {
                switch (method) {
                    case 'toast':
                        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
                            // Create Bootstrap toast
                            const toastHTML = `
                                <div class="toast" role="alert">
                                    <div class="toast-header">
                                        <i class="bi ${this._getNotificationIcon(type)} me-2"></i>
                                        <strong class="me-auto">WebSocket</strong>
                                        <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                                    </div>
                                    <div class="toast-body">${message}</div>
                                </div>
                            `;
                            
                            document.body.insertAdjacentHTML('beforeend', toastHTML);
                            const toastElement = document.body.lastElementChild;
                            const toast = new bootstrap.Toast(toastElement);
                            toast.show();
                            
                            // Remove after showing
                            toastElement.addEventListener('hidden.bs.toast', () => {
                                toastElement.remove();
                            });
                        }
                        break;
                        
                    case 'console':
                        const consoleMethod = type === 'error' ? 'error' : 
                                            type === 'warning' ? 'warn' : 'log';
                        console[consoleMethod](`WebSocket ${type}: ${message}`);
                        break;
                        
                    case 'alert':
                        if (type === 'error') {
                            alert(`WebSocket Error: ${message}`);
                        }
                        break;
                }
                
                // If one method succeeds, don't try others
                break;
            } catch (e) {
                this.logger.warn(`Fallback notification method '${method}' failed:`, e);
            }
        }
    }
    
    /**
     * Setup modal event listeners
     */
    _setupModalEventListeners() {
        if (!this.uiElements.errorModal) return;
        
        // Retry button
        const retryBtn = document.getElementById('error-modal-retry-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                this.client.connect();
                
                const modal = bootstrap.Modal.getInstance(this.uiElements.errorModal);
                if (modal) {
                    modal.hide();
                }
            });
        }
    }
    
    /**
     * Setup debug panel event listeners
     */
    _setupDebugPanelEventListeners() {
        if (!this.uiElements.debugPanel) return;
        
        // Close button
        const closeBtn = document.getElementById('debug-panel-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.uiElements.debugPanel.style.display = 'none';
            });
        }
        
        // Clear errors button
        const clearBtn = document.getElementById('debug-clear-errors');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.errorState.errorHistory = [];
                this.errorState.consecutiveErrors = 0;
                this._updateDebugPanel();
            });
        }
        
        // Export logs button
        const exportBtn = document.getElementById('debug-export-logs');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this._exportDebugLogs();
            });
        }
    }
    
    /**
     * Update debug panel
     */
    _updateDebugPanel() {
        if (!this.uiElements.debugPanel) return;
        
        // Connection status
        const statusElement = document.getElementById('debug-connection-status');
        if (statusElement) {
            statusElement.textContent = this.client.connected ? 'Connected' : 'Disconnected';
            statusElement.className = this.client.connected ? 'text-success' : 'text-danger';
        }
        
        // Transport
        const transportElement = document.getElementById('debug-transport');
        if (transportElement) {
            const transport = this._getCurrentTransport();
            transportElement.textContent = transport;
        }
        
        // Error count
        const errorCountElement = document.getElementById('debug-error-count');
        if (errorCountElement) {
            errorCountElement.textContent = this.errorState.consecutiveErrors;
        }
        
        // Last error
        const lastErrorElement = document.getElementById('debug-last-error');
        if (lastErrorElement) {
            if (this.errorState.currentError) {
                lastErrorElement.innerHTML = `
                    <div><strong>Category:</strong> ${this.errorState.currentError.category}</div>
                    <div><strong>Message:</strong> ${this.errorState.currentError.message}</div>
                    <div><strong>Time:</strong> ${this.errorState.currentError.timestamp.toLocaleTimeString()}</div>
                `;
            } else {
                lastErrorElement.textContent = 'None';
            }
        }
        
        // Performance metrics
        if (this.options.enablePerformanceMetrics) {
            this._updatePerformanceMetrics();
        }
    }
    
    /**
     * Export debug logs
     */
    _exportDebugLogs() {
        const debugData = {
            timestamp: new Date().toISOString(),
            errorState: this.errorState,
            clientState: {
                connected: this.client.connected,
                transport: this._getCurrentTransport()
            },
            options: this.options
        };
        
        const dataStr = JSON.stringify(debugData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `websocket-debug-${Date.now()}.json`;
        link.click();
        
        URL.revokeObjectURL(link.href);
    }
    
    /**
     * Add to error history
     */
    _addToErrorHistory(errorInfo) {
        this.errorState.errorHistory.push(errorInfo);
        
        // Limit history size
        if (this.errorState.errorHistory.length > this.options.maxErrorHistorySize) {
            this.errorState.errorHistory = this.errorState.errorHistory.slice(-this.options.maxErrorHistorySize);
        }
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
     * Get Bootstrap alert class for notification type
     */
    _getBootstrapAlertClass(type) {
        const mapping = {
            success: 'success',
            error: 'danger',
            warning: 'warning',
            info: 'info'
        };
        return mapping[type] || 'info';
    }
    
    /**
     * Get notification icon for type
     */
    _getNotificationIcon(type) {
        const mapping = {
            success: 'bi-check-circle',
            error: 'bi-exclamation-triangle',
            warning: 'bi-exclamation-circle',
            info: 'bi-info-circle'
        };
        return mapping[type] || 'bi-info-circle';
    }
    
    /**
     * Utility delay function
     */
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Add status indicator CSS
     */
    _addStatusIndicatorCSS() {
        if (document.getElementById('websocket-status-indicator-css')) return;
        
        const css = `
            .websocket-status-indicator {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.25rem 0.5rem;
                border-radius: 0.25rem;
                background: rgba(255, 255, 255, 0.1);
                font-size: 0.875rem;
                transition: all 0.3s ease;
            }
            
            .websocket-status-indicator i {
                font-size: 1rem;
            }
            
            .websocket-status-indicator.status-connected {
                background: rgba(25, 135, 84, 0.1);
                color: #198754;
            }
            
            .websocket-status-indicator.status-error {
                background: rgba(220, 53, 69, 0.1);
                color: #dc3545;
            }
            
            .websocket-status-indicator.status-recovering i {
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            
            @media (max-width: 768px) {
                .websocket-status-indicator .status-text {
                    display: none;
                }
            }
        `;
        
        const style = document.createElement('style');
        style.id = 'websocket-status-indicator-css';
        style.textContent = css;
        document.head.appendChild(style);
    }
    
    /**
     * Add notification CSS
     */
    _addNotificationCSS() {
        if (document.getElementById('websocket-notifications-css')) return;
        
        const css = `
            .websocket-notifications {
                position: fixed;
                z-index: 1050;
                max-width: 400px;
                pointer-events: none;
            }
            
            .websocket-notifications.top-right {
                top: 1rem;
                right: 1rem;
            }
            
            .websocket-notifications.top-left {
                top: 1rem;
                left: 1rem;
            }
            
            .websocket-notifications.bottom-right {
                bottom: 1rem;
                right: 1rem;
            }
            
            .websocket-notifications.bottom-left {
                bottom: 1rem;
                left: 1rem;
            }
            
            .websocket-notification {
                pointer-events: auto;
                margin-bottom: 0.5rem;
                animation: slideIn 0.3s ease-out;
            }
            
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        
        const style = document.createElement('style');
        style.id = 'websocket-notifications-css';
        style.textContent = css;
        document.head.appendChild(style);
    }
    
    /**
     * Add debug panel CSS
     */
    _addDebugPanelCSS() {
        if (document.getElementById('websocket-debug-panel-css')) return;
        
        const css = `
            .websocket-debug-panel {
                position: fixed;
                top: 1rem;
                left: 1rem;
                width: 300px;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                border-radius: 0.5rem;
                z-index: 1060;
                font-size: 0.875rem;
            }
            
            .debug-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .debug-header h6 {
                margin: 0;
                font-size: 0.875rem;
            }
            
            .debug-content {
                padding: 0.75rem;
            }
            
            .debug-section {
                margin-bottom: 0.75rem;
            }
            
            .debug-section:last-child {
                margin-bottom: 0;
            }
            
            .debug-error-details {
                background: rgba(220, 53, 69, 0.2);
                padding: 0.5rem;
                border-radius: 0.25rem;
                margin-top: 0.25rem;
                font-size: 0.75rem;
            }
            
            .debug-performance-metrics {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.5rem;
                margin-top: 0.25rem;
            }
            
            .debug-actions {
                display: flex;
                gap: 0.5rem;
                margin-top: 1rem;
            }
            
            .debug-actions .btn {
                font-size: 0.75rem;
                padding: 0.25rem 0.5rem;
            }
        `;
        
        const style = document.createElement('style');
        style.id = 'websocket-debug-panel-css';
        style.textContent = css;
        document.head.appendChild(style);
    }
    
    /**
     * Enable debug mode
     */
    enableDebugMode() {
        this.errorState.debugMode = true;
        this.options.enableDebugMode = true;
        
        if (!this.uiElements.debugPanel) {
            this._createDebugPanel();
        }
        
        this.uiElements.debugPanel.style.display = 'block';
        this._updateDebugPanel();
    }
    
    /**
     * Disable debug mode
     */
    disableDebugMode() {
        this.errorState.debugMode = false;
        this.options.enableDebugMode = false;
        
        if (this.uiElements.debugPanel) {
            this.uiElements.debugPanel.style.display = 'none';
        }
    }
    
    /**
     * Get error statistics
     */
    getErrorStatistics() {
        return {
            totalErrors: this.errorState.errorHistory.length,
            consecutiveErrors: this.errorState.consecutiveErrors,
            lastErrorTime: this.errorState.lastErrorTime,
            currentError: this.errorState.currentError,
            isRecovering: this.errorState.isRecovering,
            recoveryAttempts: this.errorState.recoveryAttempts,
            errorsByCategory: this._getErrorsByCategory()
        };
    }
    
    /**
     * Get errors grouped by category
     */
    _getErrorsByCategory() {
        const categories = {};
        
        this.errorState.errorHistory.forEach(error => {
            if (!categories[error.category]) {
                categories[error.category] = 0;
            }
            categories[error.category]++;
        });
        
        return categories;
    }
    
    /**
     * Clear error history
     */
    clearErrorHistory() {
        this.errorState.errorHistory = [];
        this.errorState.consecutiveErrors = 0;
        this.errorState.currentError = null;
        
        if (this.options.enableDebugMode) {
            this._updateDebugPanel();
        }
    }
    
    /**
     * Destroy error handler
     */
    destroy() {
        // Remove event listeners
        if (this.client) {
            this.client.off('connect_error');
            this.client.off('disconnect');
            this.client.off('reconnect_error');
            this.client.off('reconnect_failed');
            this.client.off('websocket_error');
            this.client.off('cors_error');
            this.client.off('auth_error');
            this.client.off('connect');
            this.client.off('reconnect');
            this.client.off('recovery_event');
        }
        
        // Remove UI elements
        Object.values(this.uiElements).forEach(element => {
            if (element && element.parentNode) {
                element.parentNode.removeChild(element);
            }
        });
        
        // Remove CSS
        ['websocket-status-indicator-css', 'websocket-notifications-css', 'websocket-debug-panel-css'].forEach(id => {
            const style = document.getElementById(id);
            if (style) {
                style.remove();
            }
        });
        
        this.logger.log('Enhanced WebSocket Error Handler destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketEnhancedErrorHandler;
} else if (typeof window !== 'undefined') {
    window.WebSocketEnhancedErrorHandler = WebSocketEnhancedErrorHandler;
}