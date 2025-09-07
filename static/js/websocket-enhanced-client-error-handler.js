// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Enhanced WebSocket Client Error Handling and User Feedback System
 * 
 * Integrates all WebSocket error handling components to provide:
 * - User-friendly error message system with specific CORS guidance
 * - Visual connection status indicators with retry options
 * - Automatic error recovery with user notification
 * - Fallback notification mechanisms for connection failures
 * - Debug mode with detailed connection diagnostics
 * 
 * Requirements: 4.4, 7.3, 9.1, 9.3, 9.4
 */

class WebSocketEnhancedClientErrorHandler {
    constructor(client, options = {}) {
        this.client = client;
        this.options = this._mergeOptions(options);
        this.logger = console;
        
        // Component instances
        this.components = {
            errorHandler: null,
            connectionStatus: null,
            debugDiagnostics: null,
            fallbackNotifications: null,
            connectionRecovery: null
        };
        
        // Enhanced error handling state
        this.state = {
            isInitialized: false,
            debugMode: false,
            userFeedbackEnabled: true,
            errorCategories: new Map(),
            recoveryStrategies: new Map(),
            userGuidance: new Map()
        };
        
        // Initialize the system
        this._initialize();
    }
    
    /**
     * Merge options with defaults
     */
    _mergeOptions(userOptions) {
        const defaults = {
            // Core functionality options
            enableUserFeedback: true,
            enableAutoRecovery: true,
            enableDebugMode: false,
            enableFallbackNotifications: true,
            
            // UI Configuration
            showConnectionStatus: true,
            showErrorModal: true,
            showNotifications: true,
            showDebugPanel: false,
            
            // Error handling configuration
            corsGuidanceEnabled: true,
            detailedErrorMessages: true,
            contextualHelp: true,
            
            // Recovery configuration
            maxRecoveryAttempts: 5,
            recoveryDelay: 2000,
            escalationThreshold: 3,
            
            // User guidance configuration
            showTroubleshootingSteps: true,
            showContactInfo: true,
            enableUserReporting: true,
            
            // Debug configuration
            debugPanelPosition: 'bottom-right',
            enablePerformanceMetrics: true,
            enableNetworkDiagnostics: true,
            
            // Notification configuration
            notificationPosition: 'top-right',
            fallbackMethods: ['toast', 'banner', 'console'],
            
            // Customization options
            customErrorMessages: {},
            customRecoveryStrategies: {},
            onErrorCallback: null,
            onRecoveryCallback: null
        };
        
        return { ...defaults, ...userOptions };
    }
    
    /**
     * Initialize the enhanced error handling system
     */
    async _initialize() {
        try {
            // Initialize core components
            await this._initializeComponents();
            
            // Setup error categories and guidance
            this._setupErrorCategories();
            this._setupRecoveryStrategies();
            this._setupUserGuidance();
            
            // Setup event listeners
            this._setupEventListeners();
            
            // Initialize UI components
            this._initializeUI();
            
            this.state.isInitialized = true;
            this.logger.log('Enhanced WebSocket Client Error Handler initialized');
            
        } catch (error) {
            this.logger.error('Failed to initialize Enhanced WebSocket Client Error Handler:', error);
            throw error;
        }
    }
    
    /**
     * Initialize core components
     */
    async _initializeComponents() {
        // Initialize fallback notifications first (most critical)
        this.components.fallbackNotifications = new WebSocketFallbackNotifications({
            preferredMethods: this.options.fallbackMethods,
            toast: { position: this.options.notificationPosition }
        });
        
        // Initialize connection recovery system
        if (typeof WebSocketConnectionRecovery !== 'undefined') {
            this.components.connectionRecovery = new WebSocketConnectionRecovery(this.client, {
                enableAutoRecovery: this.options.enableAutoRecovery,
                maxRetries: this.options.maxRecoveryAttempts,
                initialDelay: this.options.recoveryDelay
            });
        }
        
        // Initialize enhanced error handler
        if (typeof WebSocketEnhancedErrorHandler !== 'undefined') {
            this.components.errorHandler = new WebSocketEnhancedErrorHandler(this.client, {
                showErrorModal: this.options.showErrorModal,
                showNotifications: this.options.showNotifications,
                enableAutoRecovery: this.options.enableAutoRecovery,
                customErrorMessages: this.options.customErrorMessages,
                onError: (errorInfo) => this._handleEnhancedError(errorInfo),
                onRecovery: () => this._handleRecoverySuccess()
            });
        }
        
        // Initialize connection status indicator
        if (typeof WebSocketConnectionStatus !== 'undefined') {
            this.components.connectionStatus = new WebSocketConnectionStatus(
                this.client, 
                this.components.errorHandler,
                {
                    showStatusBar: this.options.showConnectionStatus,
                    position: this.options.notificationPosition,
                    enableManualRetry: true,
                    maxRetryAttempts: this.options.maxRecoveryAttempts
                }
            );
        }
        
        // Initialize debug diagnostics (if debug mode enabled)
        if (this.options.enableDebugMode && typeof WebSocketDebugDiagnostics !== 'undefined') {
            this.components.debugDiagnostics = new WebSocketDebugDiagnostics(
                this.client,
                this.components.errorHandler,
                {
                    showDebugPanel: this.options.showDebugPanel,
                    panelPosition: this.options.debugPanelPosition,
                    enablePerformanceMetrics: this.options.enablePerformanceMetrics,
                    enableNetworkDiagnostics: this.options.enableNetworkDiagnostics
                }
            );
        }
    }
    
    /**
     * Setup error categories with specific CORS guidance
     */
    _setupErrorCategories() {
        // CORS-specific error category with detailed guidance
        this.state.errorCategories.set('cors', {
            title: 'Cross-Origin Resource Sharing (CORS) Issue',
            severity: 'warning',
            icon: 'bi-shield-exclamation',
            description: 'The browser is blocking the WebSocket connection due to CORS policy restrictions.',
            
            // Specific CORS guidance
            guidance: {
                immediate: [
                    'Check that you are accessing the application from the correct URL',
                    'Verify the URL in your browser address bar matches the expected domain',
                    'Try refreshing the page to clear any temporary issues'
                ],
                
                technical: [
                    'Ensure the server CORS configuration allows your origin',
                    'Check if you are mixing HTTP and HTTPS protocols',
                    'Verify that the WebSocket endpoint URL is correct',
                    'Look for any proxy or firewall blocking the connection'
                ],
                
                advanced: [
                    'Check browser developer tools Network tab for CORS errors',
                    'Verify server Access-Control-Allow-Origin headers',
                    'Test from the same domain as the server',
                    'Contact system administrator if on corporate network'
                ]
            },
            
            // Auto-recovery strategies
            recoveryStrategies: ['transport_fallback', 'protocol_switch', 'retry_with_delay'],
            
            // User actions
            userActions: [
                {
                    text: 'Try Different URL',
                    action: () => this._showUrlGuidance(),
                    priority: 'high'
                },
                {
                    text: 'Check Network Settings',
                    action: () => this._showNetworkGuidance(),
                    priority: 'medium'
                },
                {
                    text: 'Contact Support',
                    action: () => this._showContactInfo(),
                    priority: 'low'
                }
            ]
        });
        
        // Authentication error category
        this.state.errorCategories.set('authentication', {
            title: 'Authentication Required',
            severity: 'error',
            icon: 'bi-person-lock',
            description: 'Your session has expired or authentication is required to establish the WebSocket connection.',
            
            guidance: {
                immediate: [
                    'Your login session may have expired',
                    'Click the login button below to authenticate again',
                    'Ensure cookies are enabled in your browser'
                ],
                
                technical: [
                    'Check if you are logged into the application',
                    'Verify your account has the necessary permissions',
                    'Clear browser cookies and cache if issues persist'
                ],
                
                advanced: [
                    'Check browser developer tools for authentication errors',
                    'Verify session cookies are being sent',
                    'Test with a different browser or incognito mode'
                ]
            },
            
            recoveryStrategies: ['session_refresh', 'redirect_to_login'],
            
            userActions: [
                {
                    text: 'Log In Again',
                    action: () => window.location.href = '/login',
                    priority: 'high'
                },
                {
                    text: 'Refresh Session',
                    action: () => this._attemptSessionRefresh(),
                    priority: 'medium'
                }
            ]
        });
        
        // Network connectivity error category
        this.state.errorCategories.set('network', {
            title: 'Network Connectivity Issue',
            severity: 'error',
            icon: 'bi-wifi-off',
            description: 'Unable to establish a stable network connection to the server.',
            
            guidance: {
                immediate: [
                    'Check your internet connection',
                    'Try refreshing the page',
                    'Wait a moment and the system will retry automatically'
                ],
                
                technical: [
                    'Test your internet connection with other websites',
                    'Check if you are behind a firewall or proxy',
                    'Try connecting from a different network'
                ],
                
                advanced: [
                    'Check browser developer tools for network errors',
                    'Test with different DNS servers',
                    'Disable VPN or proxy temporarily'
                ]
            },
            
            recoveryStrategies: ['retry_with_backoff', 'transport_fallback', 'network_test'],
            
            userActions: [
                {
                    text: 'Test Connection',
                    action: () => this._runNetworkTest(),
                    priority: 'high'
                },
                {
                    text: 'Retry Now',
                    action: () => this._forceReconnection(),
                    priority: 'medium'
                }
            ]
        });
        
        // Transport-specific error category
        this.state.errorCategories.set('transport', {
            title: 'Connection Method Issue',
            severity: 'info',
            icon: 'bi-arrow-repeat',
            description: 'The current connection method is having issues. Switching to a more compatible method.',
            
            guidance: {
                immediate: [
                    'The system is automatically switching to a more compatible connection method',
                    'This is normal and should resolve automatically',
                    'Please wait while the connection is re-established'
                ],
                
                technical: [
                    'WebSocket transport may be blocked by network infrastructure',
                    'Falling back to HTTP polling for compatibility',
                    'Performance may be slightly reduced but functionality will be maintained'
                ]
            },
            
            recoveryStrategies: ['transport_fallback', 'polling_mode'],
            
            userActions: [
                {
                    text: 'Wait for Automatic Recovery',
                    action: () => this._showRecoveryProgress(),
                    priority: 'high'
                }
            ]
        });
    }
    
    /**
     * Setup recovery strategies
     */
    _setupRecoveryStrategies() {
        // Transport fallback strategy
        this.state.recoveryStrategies.set('transport_fallback', {
            name: 'Transport Fallback',
            description: 'Switch to polling transport for better compatibility',
            
            execute: async () => {
                if (this.components.connectionRecovery) {
                    return this.components.connectionRecovery._attemptTransportFallback();
                }
                return false;
            },
            
            userMessage: 'Switching to compatibility mode...',
            estimatedTime: 5000
        });
        
        // Session refresh strategy
        this.state.recoveryStrategies.set('session_refresh', {
            name: 'Session Refresh',
            description: 'Attempt to refresh the authentication session',
            
            execute: async () => {
                try {
                    const response = await fetch('/api/auth/refresh', {
                        method: 'POST',
                        credentials: 'same-origin'
                    });
                    
                    if (response.ok) {
                        await this._delay(1000);
                        return this.client.connect();
                    }
                } catch (error) {
                    this.logger.warn('Session refresh failed:', error);
                }
                return false;
            },
            
            userMessage: 'Refreshing authentication...',
            estimatedTime: 3000
        });
        
        // Network test and retry strategy
        this.state.recoveryStrategies.set('network_test', {
            name: 'Network Test and Retry',
            description: 'Test network connectivity and retry connection',
            
            execute: async () => {
                const networkOk = await this._testNetworkConnectivity();
                if (networkOk) {
                    await this._delay(2000);
                    return this.client.connect();
                }
                return false;
            },
            
            userMessage: 'Testing network connectivity...',
            estimatedTime: 5000
        });
    }
    
    /**
     * Setup user guidance messages
     */
    _setupUserGuidance() {
        // CORS-specific guidance
        this.state.userGuidance.set('cors_url_check', {
            title: 'Check Your URL',
            content: `
                <div class="guidance-content">
                    <p><strong>Current URL:</strong> <code>${window.location.href}</code></p>
                    <p>Make sure you are accessing the application from the correct URL:</p>
                    <ul>
                        <li>Check for typos in the domain name</li>
                        <li>Ensure you're using the right protocol (HTTP vs HTTPS)</li>
                        <li>Verify the port number if specified</li>
                    </ul>
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle me-2"></i>
                        If you bookmarked this page, try accessing it directly from the main website.
                    </div>
                </div>
            `
        });
        
        // Network troubleshooting guidance
        this.state.userGuidance.set('network_troubleshooting', {
            title: 'Network Troubleshooting',
            content: `
                <div class="guidance-content">
                    <h6>Quick Network Checks:</h6>
                    <ol>
                        <li><strong>Internet Connection:</strong> Try visiting another website</li>
                        <li><strong>Browser Issues:</strong> Try refreshing the page or using incognito mode</li>
                        <li><strong>Firewall/Proxy:</strong> Check if your network blocks WebSocket connections</li>
                        <li><strong>VPN:</strong> Try disabling VPN temporarily</li>
                    </ol>
                    
                    <div class="mt-3">
                        <button type="button" class="btn btn-sm btn-outline-primary" onclick="window.open('https://www.google.com', '_blank')">
                            <i class="bi bi-globe me-1"></i>Test Internet Connection
                        </button>
                    </div>
                </div>
            `
        });
        
        // Contact information guidance
        this.state.userGuidance.set('contact_support', {
            title: 'Contact Support',
            content: `
                <div class="guidance-content">
                    <p>If you continue to experience issues, please contact support with the following information:</p>
                    
                    <div class="debug-info-summary">
                        <h6>System Information:</h6>
                        <ul>
                            <li><strong>Browser:</strong> ${navigator.userAgent}</li>
                            <li><strong>URL:</strong> ${window.location.href}</li>
                            <li><strong>Time:</strong> ${new Date().toISOString()}</li>
                            <li><strong>Error:</strong> <span id="current-error-summary">Connection issue</span></li>
                        </ul>
                    </div>
                    
                    <div class="mt-3">
                        <button type="button" class="btn btn-sm btn-primary" onclick="this.exportDebugInfo()">
                            <i class="bi bi-download me-1"></i>Export Debug Information
                        </button>
                    </div>
                </div>
            `
        });
    }
    
    /**
     * Setup event listeners
     */
    _setupEventListeners() {
        // Enhanced error handling
        this.client.on('connect_error', (error) => {
            this._handleConnectionError(error);
        });
        
        this.client.on('disconnect', (reason) => {
            this._handleDisconnection(reason);
        });
        
        this.client.on('reconnect_failed', () => {
            this._handleReconnectionFailure();
        });
        
        // Success events
        this.client.on('connect', () => {
            this._handleConnectionSuccess();
        });
        
        this.client.on('reconnect', () => {
            this._handleReconnectionSuccess();
        });
        
        // Custom error events
        this.client.on('cors_error', (data) => {
            this._handleCORSError(data);
        });
        
        this.client.on('auth_error', (data) => {
            this._handleAuthError(data);
        });
        
        // Recovery events
        window.addEventListener('websocket_recovery', (event) => {
            this._handleRecoveryEvent(event.detail);
        });
        
        // Debug mode toggle
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.shiftKey && event.key === 'D') {
                this.toggleDebugMode();
            }
        });
    }
    
    /**
     * Initialize UI components
     */
    _initializeUI() {
        // Create enhanced error modal
        this._createEnhancedErrorModal();
        
        // Create user guidance panel
        this._createUserGuidancePanel();
        
        // Create recovery progress indicator
        this._createRecoveryProgressIndicator();
        
        // Add CSS for enhanced components
        this._addEnhancedCSS();
    }
    
    /**
     * Handle connection errors with enhanced user feedback
     */
    _handleConnectionError(error) {
        const errorCategory = this._categorizeError(error);
        const errorInfo = this.state.errorCategories.get(errorCategory);
        
        if (!errorInfo) {
            this.logger.warn('Unknown error category:', errorCategory);
            return;
        }
        
        // Show user-friendly error message
        this._showEnhancedErrorMessage(errorCategory, error, errorInfo);
        
        // Attempt automatic recovery if enabled
        if (this.options.enableAutoRecovery) {
            this._attemptAutomaticRecovery(errorCategory, errorInfo);
        }
        
        // Update debug information
        if (this.state.debugMode && this.components.debugDiagnostics) {
            this.components.debugDiagnostics._runTroubleshootingDiagnostics(error);
        }
        
        // Call custom error callback
        if (this.options.onErrorCallback) {
            this.options.onErrorCallback(errorCategory, error, errorInfo);
        }
    }
    
    /**
     * Show enhanced error message with specific guidance
     */
    _showEnhancedErrorMessage(category, error, errorInfo) {
        // Use fallback notifications for immediate feedback
        this.components.fallbackNotifications.notify(
            errorInfo.description,
            errorInfo.severity,
            { category }
        );
        
        // Show detailed modal for critical errors
        if (errorInfo.severity === 'error' || category === 'cors') {
            this._showEnhancedErrorModal(category, error, errorInfo);
        }
        
        // Update connection status
        if (this.components.connectionStatus) {
            this.components.connectionStatus._updateStatus('error', errorInfo.title);
        }
    }
    
    /**
     * Show enhanced error modal with contextual help
     */
    _showEnhancedErrorModal(category, error, errorInfo) {
        const modal = document.getElementById('enhanced-websocket-error-modal');
        if (!modal) return;
        
        // Update modal content
        const titleElement = modal.querySelector('#enhanced-error-title');
        const iconElement = modal.querySelector('#enhanced-error-icon');
        const descriptionElement = modal.querySelector('#enhanced-error-description');
        const guidanceElement = modal.querySelector('#enhanced-error-guidance');
        const actionsElement = modal.querySelector('#enhanced-error-actions');
        
        if (titleElement) titleElement.textContent = errorInfo.title;
        if (iconElement) iconElement.className = `bi ${errorInfo.icon} me-2`;
        if (descriptionElement) descriptionElement.textContent = errorInfo.description;
        
        // Show guidance based on user's technical level
        if (guidanceElement && errorInfo.guidance) {
            guidanceElement.innerHTML = this._formatGuidanceContent(errorInfo.guidance);
        }
        
        // Show user actions
        if (actionsElement && errorInfo.userActions) {
            actionsElement.innerHTML = this._formatUserActions(errorInfo.userActions);
        }
        
        // Show debug information if debug mode is enabled
        const debugSection = modal.querySelector('#enhanced-error-debug');
        if (debugSection) {
            if (this.state.debugMode) {
                debugSection.style.display = 'block';
                debugSection.querySelector('pre').textContent = JSON.stringify({
                    error: error.message,
                    stack: error.stack,
                    category,
                    timestamp: new Date().toISOString()
                }, null, 2);
            } else {
                debugSection.style.display = 'none';
            }
        }
        
        // Show modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
    
    /**
     * Attempt automatic recovery with user notification
     */
    async _attemptAutomaticRecovery(category, errorInfo) {
        if (!errorInfo.recoveryStrategies || errorInfo.recoveryStrategies.length === 0) {
            return;
        }
        
        // Show recovery progress
        this._showRecoveryProgress('Starting automatic recovery...');
        
        for (const strategyName of errorInfo.recoveryStrategies) {
            const strategy = this.state.recoveryStrategies.get(strategyName);
            if (!strategy) continue;
            
            try {
                // Update progress
                this._updateRecoveryProgress(strategy.userMessage);
                
                // Execute recovery strategy
                const success = await strategy.execute();
                
                if (success) {
                    this._hideRecoveryProgress();
                    this.components.fallbackNotifications.notify(
                        'Connection recovered successfully!',
                        'success'
                    );
                    return;
                }
                
            } catch (error) {
                this.logger.warn(`Recovery strategy ${strategyName} failed:`, error);
            }
        }
        
        // All recovery strategies failed
        this._hideRecoveryProgress();
        this._showRecoveryFailureMessage(category);
    }
    
    /**
     * Handle CORS errors with specific guidance
     */
    _handleCORSError(data) {
        // Show immediate CORS-specific guidance
        this.components.fallbackNotifications.notify(
            'CORS policy is blocking the connection. Checking alternative connection methods...',
            'warning'
        );
        
        // Show detailed CORS guidance modal
        this._showCORSGuidanceModal(data);
        
        // Attempt CORS-specific recovery
        if (this.options.enableAutoRecovery) {
            setTimeout(() => {
                this._attemptAutomaticRecovery('cors', this.state.errorCategories.get('cors'));
            }, 2000);
        }
    }
    
    /**
     * Show CORS-specific guidance modal
     */
    _showCORSGuidanceModal(data) {
        const corsInfo = this.state.errorCategories.get('cors');
        
        // Create CORS-specific modal content
        const modalContent = `
            <div class="cors-guidance-modal">
                <div class="alert alert-warning">
                    <i class="bi bi-shield-exclamation me-2"></i>
                    <strong>CORS Policy Issue Detected</strong>
                </div>
                
                <p>The browser is blocking the WebSocket connection due to Cross-Origin Resource Sharing (CORS) policy restrictions.</p>
                
                <div class="cors-details">
                    <h6>What this means:</h6>
                    <ul>
                        <li>Your browser is protecting you from potentially unsafe cross-origin requests</li>
                        <li>The server needs to explicitly allow connections from your current URL</li>
                        <li>This is a security feature, not a bug</li>
                    </ul>
                    
                    <h6>What you can do:</h6>
                    <ol>
                        <li><strong>Check your URL:</strong> Make sure you're accessing the application from the correct address</li>
                        <li><strong>Try refreshing:</strong> Sometimes temporary issues resolve with a page refresh</li>
                        <li><strong>Contact support:</strong> If the issue persists, the server configuration may need updating</li>
                    </ol>
                </div>
                
                <div class="cors-actions mt-3">
                    <button type="button" class="btn btn-primary" onclick="window.location.reload()">
                        <i class="bi bi-arrow-clockwise me-1"></i>Refresh Page
                    </button>
                    <button type="button" class="btn btn-outline-secondary" onclick="this.showUrlGuidance()">
                        <i class="bi bi-info-circle me-1"></i>Check URL
                    </button>
                </div>
            </div>
        `;
        
        this._showCustomModal('CORS Configuration Issue', modalContent);
    }
    
    /**
     * Toggle debug mode
     */
    toggleDebugMode() {
        this.state.debugMode = !this.state.debugMode;
        
        if (this.state.debugMode) {
            // Enable debug mode
            if (!this.components.debugDiagnostics && typeof WebSocketDebugDiagnostics !== 'undefined') {
                this.components.debugDiagnostics = new WebSocketDebugDiagnostics(
                    this.client,
                    this.components.errorHandler,
                    {
                        showDebugPanel: true,
                        panelPosition: this.options.debugPanelPosition
                    }
                );
            }
            
            if (this.components.debugDiagnostics) {
                this.components.debugDiagnostics.showDebugPanel();
            }
            
            this.components.fallbackNotifications.notify(
                'Debug mode enabled. Press Ctrl+Shift+D to toggle.',
                'info'
            );
            
        } else {
            // Disable debug mode
            if (this.components.debugDiagnostics) {
                this.components.debugDiagnostics.hideDebugPanel();
            }
            
            this.components.fallbackNotifications.notify(
                'Debug mode disabled.',
                'info'
            );
        }
    }
    
    /**
     * Export debug information for user reporting
     */
    exportDebugInfo() {
        const debugInfo = {
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            
            // Connection information
            connection: {
                status: this.client.connected ? 'connected' : 'disconnected',
                transport: this._getCurrentTransport()
            },
            
            // Error information
            errors: this.components.debugDiagnostics ? 
                this.components.debugDiagnostics.diagnostics.connectionHistory.slice(-10) : [],
            
            // Performance metrics
            performance: this.components.debugDiagnostics ?
                this.components.debugDiagnostics.diagnostics.performanceMetrics : {},
            
            // Browser capabilities
            capabilities: {
                webSocket: 'WebSocket' in window,
                socketIO: typeof io !== 'undefined',
                notifications: 'Notification' in window,
                localStorage: this._testLocalStorage()
            }
        };
        
        // Create and download file
        const blob = new Blob([JSON.stringify(debugInfo, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `websocket-debug-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.components.fallbackNotifications.notify(
            'Debug information exported successfully',
            'success'
        );
    }
    
    /**
     * Utility methods
     */
    
    _categorizeError(error) {
        const message = error.message || error.toString();
        const lowerMessage = message.toLowerCase();
        
        if (lowerMessage.includes('cors') || lowerMessage.includes('cross-origin')) {
            return 'cors';
        } else if (lowerMessage.includes('auth') || lowerMessage.includes('unauthorized')) {
            return 'authentication';
        } else if (lowerMessage.includes('network') || lowerMessage.includes('timeout')) {
            return 'network';
        } else if (lowerMessage.includes('transport') || lowerMessage.includes('websocket')) {
            return 'transport';
        } else {
            return 'network'; // Default to network for unknown errors
        }
    }
    
    _getCurrentTransport() {
        if (this.client.io && this.client.io.engine && this.client.io.engine.transport) {
            return this.client.io.engine.transport.name;
        }
        return 'unknown';
    }
    
    _testLocalStorage() {
        try {
            localStorage.setItem('test', 'test');
            localStorage.removeItem('test');
            return true;
        } catch (e) {
            return false;
        }
    }
    
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    async _testNetworkConnectivity() {
        try {
            const response = await fetch('/health', { method: 'HEAD' });
            return response.ok;
        } catch (error) {
            return false;
        }
    }
    
    /**
     * Create enhanced error modal
     */
    _createEnhancedErrorModal() {
        const modalHTML = `
            <div class="modal fade" id="enhanced-websocket-error-modal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i id="enhanced-error-icon" class="bi bi-exclamation-triangle me-2"></i>
                                <span id="enhanced-error-title">Connection Issue</span>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="enhanced-error-description" class="mb-3"></div>
                            <div id="enhanced-error-guidance" class="mb-3"></div>
                            <div id="enhanced-error-actions" class="mb-3"></div>
                            <div id="enhanced-error-debug" class="mt-3 hidden">
                                <h6>Debug Information:</h6>
                                <pre class="bg-light p-2 rounded small"></pre>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-outline-info" onclick="this.toggleDebugMode()">
                                <i class="bi bi-bug me-1"></i>Debug Mode
                            </button>
                            <button type="button" class="btn btn-primary" onclick="this.exportDebugInfo()">
                                <i class="bi bi-download me-1"></i>Export Debug Info
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal
        const existingModal = document.getElementById('enhanced-websocket-error-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }
    
    /**
     * Add enhanced CSS styles
     */
    _addEnhancedCSS() {
        if (document.getElementById('enhanced-websocket-error-css')) return;
        
        const css = `
            .enhanced-websocket-error-modal .guidance-content {
                background: #f8f9fa;
                border-radius: 0.375rem;
                padding: 1rem;
                margin: 0.5rem 0;
            }
            
            .enhanced-websocket-error-modal .debug-info-summary {
                background: #e9ecef;
                border-radius: 0.375rem;
                padding: 0.75rem;
                font-size: 0.875rem;
            }
            
            .enhanced-websocket-error-modal .user-action-btn {
                margin: 0.25rem;
            }
            
            .cors-guidance-modal .cors-details {
                background: #f8f9fa;
                border-left: 4px solid #ffc107;
                padding: 1rem;
                margin: 1rem 0;
            }
            
            .recovery-progress-indicator {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid #dee2e6;
                border-radius: 0.5rem;
                padding: 2rem;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                z-index: 1060;
                text-align: center;
                min-width: 300px;
            }
            
            .recovery-progress-indicator .spinner-border {
                margin-bottom: 1rem;
            }
        `;
        
        const style = document.createElement('style');
        style.id = 'enhanced-websocket-error-css';
        style.textContent = css;
        document.head.appendChild(style);
    }
    
    /**
     * Helper methods for UI and user interaction
     */
    
    _formatGuidanceContent(guidance) {
        let content = '<div class="guidance-tabs">';
        
        // Immediate guidance (always shown)
        if (guidance.immediate) {
            content += `
                <div class="guidance-section active">
                    <h6><i class="bi bi-lightning me-1"></i>Immediate Steps</h6>
                    <ul>
                        ${guidance.immediate.map(step => `<li>${step}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        // Technical guidance (collapsible)
        if (guidance.technical) {
            content += `
                <div class="guidance-section">
                    <h6>
                        <button class="btn btn-link p-0" type="button" data-bs-toggle="collapse" data-bs-target="#technical-guidance">
                            <i class="bi bi-gear me-1"></i>Technical Steps
                        </button>
                    </h6>
                    <div class="collapse" id="technical-guidance">
                        <ul>
                            ${guidance.technical.map(step => `<li>${step}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }
        
        // Advanced guidance (collapsible)
        if (guidance.advanced) {
            content += `
                <div class="guidance-section">
                    <h6>
                        <button class="btn btn-link p-0" type="button" data-bs-toggle="collapse" data-bs-target="#advanced-guidance">
                            <i class="bi bi-tools me-1"></i>Advanced Troubleshooting
                        </button>
                    </h6>
                    <div class="collapse" id="advanced-guidance">
                        <ul>
                            ${guidance.advanced.map(step => `<li>${step}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }
        
        content += '</div>';
        return content;
    }
    
    _formatUserActions(actions) {
        return actions.map(action => `
            <button type="button" class="btn btn-${action.priority === 'high' ? 'primary' : action.priority === 'medium' ? 'outline-primary' : 'outline-secondary'} user-action-btn" 
                    onclick="(${action.action.toString()})()">
                ${action.text}
            </button>
        `).join('');
    }
    
    _showUrlGuidance() {
        const guidance = this.state.userGuidance.get('cors_url_check');
        this._showCustomModal(guidance.title, guidance.content);
    }
    
    _showNetworkGuidance() {
        const guidance = this.state.userGuidance.get('network_troubleshooting');
        this._showCustomModal(guidance.title, guidance.content);
    }
    
    _showContactInfo() {
        const guidance = this.state.userGuidance.get('contact_support');
        this._showCustomModal(guidance.title, guidance.content);
    }
    
    _showCustomModal(title, content) {
        // Create temporary modal
        const modalId = `temp-modal-${Date.now()}`;
        const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${content}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        const modal = document.getElementById(modalId);
        const bootstrapModal = new bootstrap.Modal(modal);
        
        // Remove modal after hiding
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
        
        bootstrapModal.show();
    }
    
    async _attemptSessionRefresh() {
        try {
            this._showRecoveryProgress('Refreshing session...');
            
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                this._hideRecoveryProgress();
                this.components.fallbackNotifications.notify(
                    'Session refreshed successfully. Reconnecting...',
                    'success'
                );
                
                setTimeout(() => {
                    this.client.connect();
                }, 1000);
            } else {
                throw new Error('Session refresh failed');
            }
        } catch (error) {
            this._hideRecoveryProgress();
            this.components.fallbackNotifications.notify(
                'Session refresh failed. Please log in again.',
                'error'
            );
        }
    }
    
    async _runNetworkTest() {
        this._showRecoveryProgress('Testing network connectivity...');
        
        const tests = [
            { name: 'Internet Connection', test: () => fetch('https://www.google.com/favicon.ico', { mode: 'no-cors' }) },
            { name: 'Server Connectivity', test: () => fetch('/health', { method: 'HEAD' }) },
            { name: 'WebSocket Support', test: () => Promise.resolve('WebSocket' in window) }
        ];
        
        const results = [];
        
        for (const { name, test } of tests) {
            try {
                await test();
                results.push({ name, status: 'success' });
            } catch (error) {
                results.push({ name, status: 'failed', error: error.message });
            }
        }
        
        this._hideRecoveryProgress();
        this._showNetworkTestResults(results);
    }
    
    _showNetworkTestResults(results) {
        const content = `
            <div class="network-test-results">
                <h6>Network Test Results:</h6>
                <div class="test-results">
                    ${results.map(result => `
                        <div class="test-result ${result.status}">
                            <i class="bi ${result.status === 'success' ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'} me-2"></i>
                            <strong>${result.name}:</strong> 
                            <span class="${result.status === 'success' ? 'text-success' : 'text-danger'}">
                                ${result.status === 'success' ? 'OK' : 'Failed'}
                            </span>
                            ${result.error ? `<br><small class="text-muted">${result.error}</small>` : ''}
                        </div>
                    `).join('')}
                </div>
                
                <div class="mt-3">
                    <button type="button" class="btn btn-primary" onclick="this._forceReconnection()">
                        <i class="bi bi-arrow-clockwise me-1"></i>Try Reconnecting
                    </button>
                </div>
            </div>
        `;
        
        this._showCustomModal('Network Test Results', content);
    }
    
    _forceReconnection() {
        this.components.fallbackNotifications.notify(
            'Attempting to reconnect...',
            'info'
        );
        
        if (this.client.connected) {
            this.client.disconnect();
        }
        
        setTimeout(() => {
            this.client.connect();
        }, 1000);
    }
    
    _createUserGuidancePanel() {
        // User guidance panel is created dynamically in modals
        // This method is a placeholder for future enhancements
    }
    
    _createRecoveryProgressIndicator() {
        const indicatorHTML = `
            <div id="recovery-progress-indicator" class="recovery-progress-indicator hidden">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div id="recovery-progress-message" class="mt-2">
                    Attempting recovery...
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', indicatorHTML);
    }
    
    _showRecoveryProgress(message) {
        const indicator = document.getElementById('recovery-progress-indicator');
        const messageElement = document.getElementById('recovery-progress-message');
        
        if (indicator && messageElement) {
            messageElement.textContent = message;
            indicator.style.display = 'block';
        }
    }
    
    _updateRecoveryProgress(message) {
        const messageElement = document.getElementById('recovery-progress-message');
        if (messageElement) {
            messageElement.textContent = message;
        }
    }
    
    _hideRecoveryProgress() {
        const indicator = document.getElementById('recovery-progress-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
    
    _showRecoveryFailureMessage(category) {
        const errorInfo = this.state.errorCategories.get(category);
        const message = `Automatic recovery failed. ${errorInfo ? errorInfo.title : 'Connection issue'} persists.`;
        
        this.components.fallbackNotifications.notify(message, 'error');
        
        // Show manual recovery options
        this._showManualRecoveryOptions(category);
    }
    
    _showManualRecoveryOptions(category) {
        const errorInfo = this.state.errorCategories.get(category);
        
        const content = `
            <div class="manual-recovery-options">
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Automatic recovery was unsuccessful. Please try the following options:
                </div>
                
                ${errorInfo && errorInfo.userActions ? `
                    <div class="recovery-actions">
                        <h6>Recommended Actions:</h6>
                        ${this._formatUserActions(errorInfo.userActions)}
                    </div>
                ` : ''}
                
                <div class="general-actions mt-3">
                    <h6>General Options:</h6>
                    <button type="button" class="btn btn-outline-primary" onclick="window.location.reload()">
                        <i class="bi bi-arrow-clockwise me-1"></i>Refresh Page
                    </button>
                    <button type="button" class="btn btn-outline-secondary" onclick="this.toggleDebugMode()">
                        <i class="bi bi-bug me-1"></i>Enable Debug Mode
                    </button>
                    <button type="button" class="btn btn-outline-info" onclick="this.exportDebugInfo()">
                        <i class="bi bi-download me-1"></i>Export Debug Info
                    </button>
                </div>
            </div>
        `;
        
        this._showCustomModal('Manual Recovery Required', content);
    }
    
    _handleEnhancedError(errorInfo) {
        // Additional processing for enhanced error handler events
        if (this.state.debugMode) {
            this.logger.log('Enhanced error handled:', errorInfo);
        }
    }
    
    _handleRecoverySuccess() {
        // Handle successful recovery
        this._hideRecoveryProgress();
        
        if (this.options.onRecoveryCallback) {
            this.options.onRecoveryCallback();
        }
    }
    
    _handleDisconnection(reason) {
        if (reason !== 'io client disconnect' && reason !== 'io server disconnect') {
            this.components.fallbackNotifications.notify(
                `Connection lost: ${reason}. Attempting to reconnect...`,
                'warning'
            );
        }
    }
    
    _handleReconnectionFailure() {
        this.components.fallbackNotifications.notify(
            'Failed to reconnect after multiple attempts. Manual intervention may be required.',
            'error'
        );
        
        this._showManualRecoveryOptions('network');
    }
    
    _handleConnectionSuccess() {
        this.components.fallbackNotifications.notify(
            'Connection established successfully!',
            'success'
        );
        
        this._hideRecoveryProgress();
    }
    
    _handleReconnectionSuccess() {
        this.components.fallbackNotifications.notify(
            'Reconnected successfully!',
            'success'
        );
        
        this._hideRecoveryProgress();
    }
    
    _handleAuthError(data) {
        this._handleConnectionError(new Error('Authentication required'));
    }
    
    _handleRecoveryEvent(eventData) {
        if (this.state.debugMode) {
            this.logger.log('Recovery event:', eventData);
        }
        
        switch (eventData.type) {
            case 'recovery_start':
                this._showRecoveryProgress('Starting recovery...');
                break;
            case 'recovery_success':
                this._handleRecoverySuccess();
                break;
            case 'recovery_failed':
                this._handleReconnectionFailure();
                break;
            case 'polling_mode_entered':
                this.components.fallbackNotifications.notify(
                    'Switched to compatibility mode for better connection stability',
                    'info'
                );
                break;
        }
    }
    
    /**
     * Public API methods
     */
    
    /**
     * Get system status
     */
    getStatus() {
        return {
            initialized: this.state.isInitialized,
            debugMode: this.state.debugMode,
            components: Object.keys(this.components).reduce((acc, key) => {
                acc[key] = this.components[key] !== null;
                return acc;
            }, {}),
            connectionStatus: this.client.connected ? 'connected' : 'disconnected'
        };
    }
    
    /**
     * Enable/disable user feedback
     */
    setUserFeedbackEnabled(enabled) {
        this.state.userFeedbackEnabled = enabled;
        this.options.enableUserFeedback = enabled;
    }
    
    /**
     * Update configuration
     */
    updateOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
        
        // Update component configurations
        Object.values(this.components).forEach(component => {
            if (component && typeof component.updateOptions === 'function') {
                component.updateOptions(newOptions);
            }
        });
    }
    
    /**
     * Destroy the enhanced error handler
     */
    destroy() {
        // Destroy all components
        Object.values(this.components).forEach(component => {
            if (component && typeof component.destroy === 'function') {
                component.destroy();
            }
        });
        
        // Remove UI elements
        const elementsToRemove = [
            'enhanced-websocket-error-modal',
            'enhanced-websocket-error-css'
        ];
        
        elementsToRemove.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.remove();
            }
        });
        
        this.logger.log('Enhanced WebSocket Client Error Handler destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketEnhancedClientErrorHandler;
} else if (typeof window !== 'undefined') {
    window.WebSocketEnhancedClientErrorHandler = WebSocketEnhancedClientErrorHandler;
}