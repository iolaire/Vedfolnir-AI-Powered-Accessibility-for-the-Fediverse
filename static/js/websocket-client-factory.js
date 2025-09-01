// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Standardized WebSocket Client Factory for Vedfolnir
 * 
 * Provides consistent WebSocket client configuration based on server environment settings,
 * client-side environment detection, and standardized connection initialization patterns.
 */

class WebSocketClientFactory {
    constructor() {
        this.logger = console;
        this.configCache = null;
        this.environmentConfig = null;
        this.validationErrors = [];
        this.configPromise = null; // Track ongoing config fetch
        this.preloadAttempted = false; // Prevent multiple preload attempts
        
        // Initialize environment detection
        this._detectEnvironment();
        
        console.log('WebSocket Client Factory initialized');
        
        // Pre-load server configuration to avoid race conditions (with delay to avoid recursion)
        setTimeout(() => {
            this._preloadConfiguration();
        }, 100);
    }
    
    /**
     * Pre-load server configuration to avoid race conditions
     */
    async _preloadConfiguration() {
        if (this.preloadAttempted) {
            return; // Prevent multiple preload attempts
        }
        this.preloadAttempted = true;
        
        try {
            await this.getServerConfiguration();
            console.log('Server configuration pre-loaded successfully');
        } catch (error) {
            console.warn('Failed to pre-load server configuration:', error);
        }
    }
    
    /**
     * Create a standardized WebSocket client instance
     * 
     * @param {Object} options - Configuration options for the client
     * @param {string} options.namespace - WebSocket namespace (default: '/')
     * @param {boolean} options.autoConnect - Whether to auto-connect (default: false)
     * @param {Object} options.customConfig - Custom configuration overrides
     * @returns {Object} Configured WebSocket client instance
     */
    async createClient(options = {}) {
        try {
            // Validate and merge configuration
            const config = await this._buildClientConfiguration(options);
            
            // Validate configuration
            const validation = this._validateClientConfiguration(config);
            if (!validation.isValid) {
                throw new Error(`Client configuration validation failed: ${validation.errors.join(', ')}`);
            }
            
            // Create client instance
            const client = this._createClientInstance(config);
            
            // Setup standardized event handlers
            this._setupStandardizedEventHandlers(client, config);
            
            // Setup error handling
            this._setupErrorHandling(client, config);
            
            // Auto-connect if requested
            if (config.autoConnect) {
                setTimeout(() => {
                    client.connect();
                }, config.autoConnectDelay || 1000);
            }
            
            console.log(`WebSocket client created for namespace: ${config.namespace}`);
            return client;
            
        } catch (error) {
            console.error('Failed to create WebSocket client:', error);
            throw error;
        }
    }
    
    /**
     * Get server configuration for client initialization
     * 
     * @returns {Promise<Object>} Server configuration object
     */
    async getServerConfiguration() {
        if (this.configCache) {
            return this.configCache;
        }
        
        // If there's already a config fetch in progress, wait for it
        if (this.configPromise) {
            console.log('Config fetch already in progress, waiting...');
            return await this.configPromise;
        }
        
        // Start the config fetch and store the promise
        this.configPromise = this._fetchServerConfiguration();
        
        try {
            const config = await this.configPromise;
            this.configPromise = null; // Clear the promise
            return config;
        } catch (error) {
            this.configPromise = null; // Clear the promise on error
            throw error;
        }
    }
    
    async _fetchServerConfiguration() {
        try {
            console.log('Fetching server WebSocket configuration...');
            
            const response = await fetch('/api/websocket/client-config', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                mode: 'cors'  // Explicitly enable CORS mode
            });
            
            if (!response.ok) {
                throw new Error(`Failed to fetch server config: ${response.status} ${response.statusText}`);
            }
            
            const responseData = await response.json();
            
            // Extract the nested config from the response
            const config = responseData.success && responseData.config ? responseData.config : responseData;
            
            // Validate server configuration
            if (!this._validateServerConfiguration(config)) {
                throw new Error('Invalid server configuration received');
            }
            
            // Cache configuration
            this.configCache = config;
            
            console.log('Server WebSocket configuration loaded successfully');
            return config;
            
        } catch (error) {
            console.warn('Failed to fetch server configuration, using fallback:', error);
            return this._getFallbackConfiguration();
        }
    }
    
    /**
     * Detect client environment and adapt configuration
     */
    _detectEnvironment() {
        this.environmentConfig = {
            // Browser detection
            browser: this._detectBrowser(),
            
            // Protocol detection
            protocol: window.location.protocol === 'https:' ? 'https' : 'http',
            
            // Host detection
            host: window.location.hostname,
            port: window.location.port || (window.location.protocol === 'https:' ? '443' : '80'),
            
            // Development environment detection
            isDevelopment: this._isDevelopmentEnvironment(),
            
            // Mobile detection
            isMobile: this._isMobileDevice(),
            
            // Network quality estimation
            networkQuality: this._estimateNetworkQuality(),
            
            // WebSocket support detection
            webSocketSupport: this._detectWebSocketSupport()
        };
        
        console.log('Environment detected:', this.environmentConfig);
    }
    
    /**
     * Build client configuration by merging server config, environment config, and options
     */
    async _buildClientConfiguration(options) {
        // Get server configuration
        const serverConfig = await this.getServerConfiguration();
        
        // Base configuration from server
        const baseConfig = {
            url: serverConfig.url || this._buildServerUrl(),
            namespace: options.namespace || '/',
            transports: serverConfig.transports || ['websocket', 'polling'],
            reconnection: serverConfig.reconnection !== false,
            reconnectionAttempts: serverConfig.reconnectionAttempts || 5,
            reconnectionDelay: serverConfig.reconnectionDelay || 1000,
            reconnectionDelayMax: serverConfig.reconnectionDelayMax || 5000,
            timeout: serverConfig.timeout || 20000,
            forceNew: options.forceNew || false,
            upgrade: serverConfig.upgrade !== false,
            rememberUpgrade: serverConfig.rememberUpgrade !== false,
            withCredentials: true,
            autoConnect: options.autoConnect || false
        };
        
        // Apply environment-specific adaptations
        const environmentAdaptedConfig = this._adaptConfigurationForEnvironment(baseConfig);
        
        // Apply custom configuration overrides
        const finalConfig = {
            ...environmentAdaptedConfig,
            ...options.customConfig
        };
        
        console.log('Built client configuration:', finalConfig);
        return finalConfig;
    }
    
    /**
     * Adapt configuration based on detected environment
     */
    _adaptConfigurationForEnvironment(config) {
        const adapted = { ...config };
        
        // Mobile adaptations
        if (this.environmentConfig.isMobile) {
            adapted.timeout = Math.max(adapted.timeout, 30000); // Longer timeout for mobile
            adapted.reconnectionDelay = Math.max(adapted.reconnectionDelay, 2000); // Longer delay for mobile
            adapted.pingInterval = 30000; // Less frequent pings on mobile
            adapted.pingTimeout = 60000; // Longer ping timeout on mobile
        }
        
        // Development environment adaptations
        if (this.environmentConfig.isDevelopment) {
            adapted.reconnectionAttempts = Math.max(adapted.reconnectionAttempts, 10); // More attempts in dev
            adapted.forceNew = true; // Force new connections in dev for debugging
        }
        
        // Network quality adaptations
        if (this.environmentConfig.networkQuality === 'slow') {
            adapted.transports = ['polling']; // Use polling for slow networks
            adapted.timeout = Math.max(adapted.timeout, 45000); // Much longer timeout
            adapted.reconnectionDelay = Math.max(adapted.reconnectionDelay, 5000); // Longer delay
        } else if (this.environmentConfig.networkQuality === 'fast') {
            adapted.transports = ['websocket', 'polling']; // Prefer WebSocket for fast networks
            adapted.upgrade = true; // Allow upgrade to WebSocket
        }
        
        // Browser-specific adaptations
        if (this.environmentConfig.browser.name === 'safari') {
            // Safari has some WebSocket quirks
            adapted.transports = ['polling', 'websocket']; // Prefer polling first for Safari
            adapted.rememberUpgrade = false; // Don't remember upgrades in Safari
        }
        
        // WebSocket support adaptations
        if (!this.environmentConfig.webSocketSupport.native) {
            adapted.transports = ['polling']; // Fallback to polling only
        }
        
        console.log('Configuration adapted for environment:', adapted);
        return adapted;
    }
    
    /**
     * Create the actual client instance
     */
    _createClientInstance(config) {
        if (typeof io === 'undefined') {
            throw new Error('Socket.IO library not loaded');
        }
        
        // Extract URL and namespace from config
        const url = config.url || window.location.origin;
        const namespace = config.namespace || '/';
        
        // Remove URL and namespace from Socket.IO config to avoid conflicts
        const socketConfig = { ...config };
        delete socketConfig.url;
        delete socketConfig.namespace;
        
        // Create full URL with namespace
        const fullUrl = url + namespace;
        
        console.log('Creating Socket.IO client with URL:', fullUrl);
        console.log('Socket.IO config:', socketConfig);
        
        // Create Socket.IO instance
        const socket = io(fullUrl, socketConfig);
        
        // Create wrapper client with standardized interface
        const client = new StandardizedWebSocketClient(socket, config, this.environmentConfig);
        
        return client;
    }
    
    /**
     * Setup standardized event handlers for all clients
     */
    _setupStandardizedEventHandlers(client, config) {
        // Connection events
        client.on('connect', () => {
            console.log(`WebSocket connected to namespace: ${config.namespace || '/'}`);
            this._updateConnectionStatus('connected');
        });
        
        client.on('disconnect', (reason) => {
            console.log(`WebSocket disconnected from namespace: ${config.namespace || '/'}, reason: ${reason}`);
            this._updateConnectionStatus('disconnected', reason);
        });
        
        client.on('reconnect', (attemptNumber) => {
            console.log(`WebSocket reconnected after ${attemptNumber} attempts`);
            this._updateConnectionStatus('reconnected');
        });
        
        client.on('reconnect_attempt', (attemptNumber) => {
            console.log(`WebSocket reconnection attempt ${attemptNumber}`);
            this._updateConnectionStatus('reconnecting', `Attempt ${attemptNumber}`);
        });
        
        client.on('reconnect_error', (error) => {
            console.error('WebSocket reconnection error:', error);
            this._updateConnectionStatus('reconnect_error', error.message);
        });
        
        client.on('reconnect_failed', () => {
            console.error('WebSocket reconnection failed after maximum attempts');
            this._updateConnectionStatus('reconnect_failed');
        });
        
        // Error events
        client.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this._handleConnectionError(error, client, config);
        });
        
        client.on('error', (error) => {
            console.error('WebSocket error:', error);
            this._handleGeneralError(error, client, config);
        });
    }
    
    /**
     * Setup comprehensive error handling
     */
    _setupErrorHandling(client, config) {
        // Wrap client methods with error handling
        const originalEmit = client.emit.bind(client);
        client.emit = function(event, ...args) {
            try {
                return originalEmit(event, ...args);
            } catch (error) {
                console.error(`Error emitting event '${event}':`, error);
                return false;
            }
        };
        
        // Setup error recovery mechanisms
        client._errorRecovery = {
            consecutiveErrors: 0,
            lastErrorTime: null,
            maxConsecutiveErrors: 5,
            errorCooldownPeriod: 30000 // 30 seconds
        };
    }
    
    /**
     * Handle connection errors with intelligent recovery
     */
    _handleConnectionError(error, client, config) {
        const errorMessage = error.message || error.toString();
        
        // Analyze error type
        const errorType = this._analyzeConnectionError(errorMessage);
        
        console.log(`Connection error type: ${errorType}`);
        
        switch (errorType) {
            case 'cors':
                this._handleCORSError(error, client, config);
                break;
            case 'timeout':
                this._handleTimeoutError(error, client, config);
                break;
            case 'transport':
                this._handleTransportError(error, client, config);
                break;
            case 'auth':
                this._handleAuthError(error, client, config);
                break;
            default:
                this._handleGenericConnectionError(error, client, config);
        }
        
        // Update error recovery tracking
        this._updateErrorRecovery(client);
    }
    
    /**
     * Handle CORS-related errors
     */
    _handleCORSError(error, client, config) {
        console.warn('CORS error detected, attempting polling fallback');
        
        // Try to reconnect with polling only
        if (config.transports.includes('polling')) {
            client.disconnect();
            
            setTimeout(() => {
                const pollingConfig = { ...config, transports: ['polling'] };
                client._reconfigureTransports(['polling']);
                client.connect();
            }, 2000);
        }
        
        this._updateConnectionStatus('cors_error', 'Switching to polling mode');
    }
    
    /**
     * Handle timeout errors
     */
    _handleTimeoutError(error, client, config) {
        console.warn('Timeout error detected, increasing timeout values');
        
        // Increase timeout for next connection attempt
        client._increaseTimeouts();
        
        this._updateConnectionStatus('timeout_error', 'Increasing timeout values');
    }
    
    /**
     * Handle transport errors
     */
    _handleTransportError(error, client, config) {
        console.warn('Transport error detected, trying alternative transport');
        
        // Switch to alternative transport - check if client.io and opts exist
        if (client && client.io && client.io.opts && client.io.opts.transports) {
            const currentTransports = client.io.opts.transports;
            if (currentTransports.includes('websocket') && currentTransports.includes('polling')) {
                // Switch to polling only
                client._reconfigureTransports(['polling']);
            }
        } else if (config && config.transports && config.transports.includes('polling')) {
            // Fallback to config transports if client.io.opts is not available
            console.warn('Client opts not available, using config transports');
            if (client && typeof client._reconfigureTransports === 'function') {
                client._reconfigureTransports(['polling']);
            }
        }
        
        this._updateConnectionStatus('transport_error', 'Switching transport method');
    }
    
    /**
     * Handle authentication errors
     */
    _handleAuthError(error, client, config) {
        console.error('Authentication error detected');
        
        // Emit authentication required event
        client.emit('auth_required', error);
        
        this._updateConnectionStatus('auth_error', 'Authentication required');
    }
    
    /**
     * Handle generic connection errors
     */
    _handleGenericConnectionError(error, client, config) {
        console.error('Generic connection error:', error);
        
        this._updateConnectionStatus('connection_error', error.message);
    }
    
    /**
     * Handle general errors
     */
    _handleGeneralError(error, client, config) {
        console.error('General WebSocket error:', error);
        
        // Check if we should attempt recovery
        if (this._shouldAttemptErrorRecovery(client)) {
            console.log('Attempting error recovery...');
            
            setTimeout(() => {
                if (!client.connected) {
                    client.connect();
                }
            }, 5000);
        }
    }
    
    /**
     * Update error recovery tracking
     */
    _updateErrorRecovery(client) {
        const now = Date.now();
        const recovery = client._errorRecovery;
        
        // Reset counter if enough time has passed
        if (recovery.lastErrorTime && (now - recovery.lastErrorTime) > recovery.errorCooldownPeriod) {
            recovery.consecutiveErrors = 0;
        }
        
        recovery.consecutiveErrors++;
        recovery.lastErrorTime = now;
    }
    
    /**
     * Check if error recovery should be attempted
     */
    _shouldAttemptErrorRecovery(client) {
        const recovery = client._errorRecovery;
        return recovery.consecutiveErrors < recovery.maxConsecutiveErrors;
    }
    
    /**
     * Analyze connection error to determine type
     */
    _analyzeConnectionError(errorMessage) {
        const message = errorMessage.toLowerCase();
        
        if (message.includes('cors') || message.includes('cross-origin') || message.includes('access-control')) {
            return 'cors';
        } else if (message.includes('timeout') || message.includes('timed out')) {
            return 'timeout';
        } else if (message.includes('transport') || message.includes('websocket') || message.includes('polling')) {
            return 'transport';
        } else if (message.includes('auth') || message.includes('unauthorized') || message.includes('forbidden')) {
            return 'auth';
        } else {
            return 'generic';
        }
    }
    
    /**
     * Update connection status in UI
     */
    _updateConnectionStatus(status, message = '') {
        // Emit custom event for status updates
        window.dispatchEvent(new CustomEvent('websocketStatusChange', {
            detail: { status, message, timestamp: Date.now() }
        }));
        
        // Update status element if it exists
        const statusElement = document.getElementById('websocket-status');
        if (statusElement) {
            this._updateStatusElement(statusElement, status, message);
        }
    }
    
    /**
     * Update status element in DOM
     */
    _updateStatusElement(element, status, message) {
        const statusConfig = {
            connected: { class: 'text-success', icon: 'bi-wifi', text: 'Connected' },
            disconnected: { class: 'text-warning', icon: 'bi-wifi-off', text: 'Disconnected' },
            reconnecting: { class: 'text-info', icon: 'bi-arrow-clockwise', text: 'Reconnecting' },
            reconnected: { class: 'text-success', icon: 'bi-wifi', text: 'Reconnected' },
            cors_error: { class: 'text-warning', icon: 'bi-shield-x', text: 'CORS Issue' },
            timeout_error: { class: 'text-warning', icon: 'bi-clock', text: 'Timeout' },
            transport_error: { class: 'text-warning', icon: 'bi-arrow-repeat', text: 'Transport Issue' },
            auth_error: { class: 'text-danger', icon: 'bi-shield-lock', text: 'Auth Required' },
            connection_error: { class: 'text-danger', icon: 'bi-exclamation-triangle', text: 'Connection Error' },
            reconnect_error: { class: 'text-warning', icon: 'bi-exclamation-circle', text: 'Reconnect Error' },
            reconnect_failed: { class: 'text-danger', icon: 'bi-x-circle', text: 'Connection Failed' }
        };
        
        const config = statusConfig[status] || statusConfig.connection_error;
        
        element.className = config.class;
        element.innerHTML = `<i class="bi ${config.icon}"></i> ${config.text}`;
        
        if (message) {
            element.title = message;
        }
    }
    
    /**
     * Validate client configuration
     */
    _validateClientConfiguration(config) {
        const errors = [];
        
        // Required fields
        if (!config.url) {
            errors.push('Server URL is required');
        }
        
        if (!config.transports || !Array.isArray(config.transports) || config.transports.length === 0) {
            errors.push('At least one transport method is required');
        }
        
        // Validate timeout values
        if (config.timeout && config.timeout <= 0) {
            errors.push('Timeout must be positive');
        }
        
        if (config.reconnectionDelay && config.reconnectionDelay <= 0) {
            errors.push('Reconnection delay must be positive');
        }
        
        if (config.reconnectionDelayMax && config.reconnectionDelay && 
            config.reconnectionDelayMax < config.reconnectionDelay) {
            errors.push('Reconnection delay max must be >= reconnection delay');
        }
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }
    
    /**
     * Validate server configuration
     */
    _validateServerConfiguration(config) {
        return config && 
               typeof config === 'object' && 
               (config.url || config.transports);
    }
    
    /**
     * Build server URL from current location
     */
    _buildServerUrl() {
        const protocol = window.location.protocol === 'https:' ? 'https' : 'http';
        const host = window.location.hostname;
        const port = window.location.port;
        
        if (port && port !== '80' && port !== '443') {
            return `${protocol}://${host}:${port}`;
        } else {
            return `${protocol}://${host}`;
        }
    }
    
    /**
     * Get fallback configuration when server config is unavailable
     */
    _getFallbackConfiguration() {
        console.log('Using fallback WebSocket configuration');
        
        return {
            url: this._buildServerUrl(),
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000,
            upgrade: true,
            rememberUpgrade: true
        };
    }
    
    /**
     * Detect browser information
     */
    _detectBrowser() {
        const userAgent = navigator.userAgent;
        
        if (userAgent.includes('Chrome')) {
            return { name: 'chrome', version: this._extractVersion(userAgent, 'Chrome/') };
        } else if (userAgent.includes('Firefox')) {
            return { name: 'firefox', version: this._extractVersion(userAgent, 'Firefox/') };
        } else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
            return { name: 'safari', version: this._extractVersion(userAgent, 'Version/') };
        } else if (userAgent.includes('Edge')) {
            return { name: 'edge', version: this._extractVersion(userAgent, 'Edge/') };
        } else {
            return { name: 'unknown', version: 'unknown' };
        }
    }
    
    /**
     * Extract version from user agent string
     */
    _extractVersion(userAgent, prefix) {
        const index = userAgent.indexOf(prefix);
        if (index === -1) return 'unknown';
        
        const versionStart = index + prefix.length;
        const versionEnd = userAgent.indexOf(' ', versionStart);
        
        return userAgent.substring(versionStart, versionEnd === -1 ? undefined : versionEnd);
    }
    
    /**
     * Check if running in development environment
     */
    _isDevelopmentEnvironment() {
        return window.location.hostname === 'localhost' || 
               window.location.hostname === '127.0.0.1' ||
               window.location.hostname.startsWith('192.168.') ||
               window.location.hostname.startsWith('10.') ||
               window.location.port !== '' ||
               window.location.search.includes('debug=1');
    }
    
    /**
     * Detect if running on mobile device
     */
    _isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }
    
    /**
     * Estimate network quality based on available information
     */
    _estimateNetworkQuality() {
        // Use Network Information API if available
        if ('connection' in navigator) {
            const connection = navigator.connection;
            
            if (connection.effectiveType) {
                switch (connection.effectiveType) {
                    case 'slow-2g':
                    case '2g':
                        return 'slow';
                    case '3g':
                        return 'medium';
                    case '4g':
                        return 'fast';
                    default:
                        return 'unknown';
                }
            }
        }
        
        // Fallback estimation based on other factors
        if (this._isMobileDevice()) {
            return 'medium'; // Assume medium quality for mobile
        }
        
        return 'fast'; // Assume fast for desktop
    }
    
    /**
     * Detect WebSocket support capabilities
     */
    _detectWebSocketSupport() {
        return {
            native: 'WebSocket' in window,
            socketIO: typeof io !== 'undefined',
            binaryType: 'WebSocket' in window // Assume binary support if WebSocket is available
        };
    }
    
    /**
     * Get factory configuration summary
     */
    getConfigurationSummary() {
        return {
            environment: this.environmentConfig,
            cachedConfig: this.configCache,
            validationErrors: this.validationErrors,
            factoryVersion: '1.0.0'
        };
    }
    
    /**
     * Clear cached configuration
     */
    clearCache() {
        this.configCache = null;
        console.log('WebSocket client factory cache cleared');
    }
}
/*
*
 * Standardized WebSocket Client wrapper
 * 
 * Provides a consistent interface around Socket.IO with additional functionality
 * for error handling, reconnection management, and environment adaptation.
 */
class StandardizedWebSocketClient {
    constructor(socket, config, environmentConfig) {
        this.socket = socket;
        this.config = config;
        this.environmentConfig = environmentConfig;
        this.eventHandlers = new Map();
        this.connected = false;
        this.reconnectAttempts = 0;
        this.lastPingTime = null;
        this.connectionMetrics = {
            connectTime: null,
            disconnectTime: null,
            totalReconnects: 0,
            totalErrors: 0,
            averageLatency: 0,
            latencyMeasurements: []
        };
        
        // Setup internal event handlers
        this._setupInternalHandlers();
        
        console.log('Standardized WebSocket client initialized');
    }
    
    /**
     * Setup internal event handlers for metrics and state tracking
     */
    _setupInternalHandlers() {
        this.socket.on('connect', () => {
            this.connected = true;
            this.reconnectAttempts = 0;
            this.connectionMetrics.connectTime = Date.now();
            this._startLatencyMonitoring();
        });
        
        this.socket.on('disconnect', () => {
            this.connected = false;
            this.connectionMetrics.disconnectTime = Date.now();
            this._stopLatencyMonitoring();
        });
        
        this.socket.on('reconnect', () => {
            this.connectionMetrics.totalReconnects++;
        });
        
        this.socket.on('error', () => {
            this.connectionMetrics.totalErrors++;
        });
        
        this.socket.on('pong', (latency) => {
            this._recordLatency(latency);
        });
    }
    
    /**
     * Connect to the WebSocket server
     */
    connect() {
        try {
            console.log('Connecting WebSocket client...');
            this.socket.connect();
        } catch (error) {
            console.error('Error connecting WebSocket client:', error);
            throw error;
        }
    }
    
    /**
     * Disconnect from the WebSocket server
     */
    disconnect() {
        try {
            console.log('Disconnecting WebSocket client...');
            this.socket.disconnect();
        } catch (error) {
            console.error('Error disconnecting WebSocket client:', error);
        }
    }
    
    /**
     * Emit an event to the server
     */
    emit(event, data, callback) {
        try {
            if (!this.connected) {
                console.warn(`Cannot emit event '${event}': client not connected`);
                return false;
            }
            
            return this.socket.emit(event, data, callback);
        } catch (error) {
            console.error(`Error emitting event '${event}':`, error);
            return false;
        }
    }
    
    /**
     * Listen for an event from the server
     */
    on(event, handler) {
        try {
            // Store handler for management
            if (!this.eventHandlers.has(event)) {
                this.eventHandlers.set(event, []);
            }
            this.eventHandlers.get(event).push(handler);
            
            // Register with Socket.IO
            this.socket.on(event, handler);
        } catch (error) {
            console.error(`Error registering event handler for '${event}':`, error);
        }
    }
    
    /**
     * Remove event listener
     */
    off(event, handler) {
        try {
            // Remove from our tracking
            if (this.eventHandlers.has(event)) {
                const handlers = this.eventHandlers.get(event);
                const index = handlers.indexOf(handler);
                if (index > -1) {
                    handlers.splice(index, 1);
                }
            }
            
            // Remove from Socket.IO
            this.socket.off(event, handler);
        } catch (error) {
            console.error(`Error removing event handler for '${event}':`, error);
        }
    }
    
    /**
     * Listen for an event once
     */
    once(event, handler) {
        try {
            this.socket.once(event, handler);
        } catch (error) {
            console.error(`Error registering one-time event handler for '${event}':`, error);
        }
    }
    
    /**
     * Check if client is connected
     */
    isConnected() {
        return this.connected && this.socket && this.socket.connected;
    }
    
    /**
     * Get connection ID
     */
    getId() {
        return this.socket ? this.socket.id : null;
    }
    
    /**
     * Get current transport method
     */
    getTransport() {
        return this.socket && this.socket.io && this.socket.io.engine ? 
               this.socket.io.engine.transport.name : 'unknown';
    }
    
    /**
     * Force reconnection
     */
    forceReconnect() {
        console.log('Forcing WebSocket reconnection...');
        
        try {
            this.disconnect();
            
            setTimeout(() => {
                this.connect();
            }, 1000);
        } catch (error) {
            console.error('Error during forced reconnection:', error);
        }
    }
    
    /**
     * Reconfigure transports (internal method)
     */
    _reconfigureTransports(transports) {
        try {
            if (this.socket && this.socket.io) {
                this.socket.io.opts.transports = transports;
                console.log(`Reconfigured transports to: ${transports.join(', ')}`);
            }
        } catch (error) {
            console.error('Error reconfiguring transports:', error);
        }
    }
    
    /**
     * Increase timeout values (internal method)
     */
    _increaseTimeouts() {
        try {
            if (this.socket && this.socket.io) {
                const currentTimeout = this.socket.io.opts.timeout || 20000;
                const newTimeout = Math.min(currentTimeout * 1.5, 60000); // Max 60 seconds
                
                this.socket.io.opts.timeout = newTimeout;
                console.log(`Increased timeout to: ${newTimeout}ms`);
            }
        } catch (error) {
            console.error('Error increasing timeouts:', error);
        }
    }
    
    /**
     * Start latency monitoring
     */
    _startLatencyMonitoring() {
        if (this.latencyInterval) {
            clearInterval(this.latencyInterval);
        }
        
        this.latencyInterval = setInterval(() => {
            if (this.connected) {
                this.lastPingTime = Date.now();
                this.socket.emit('ping');
            }
        }, 30000); // Ping every 30 seconds
    }
    
    /**
     * Stop latency monitoring
     */
    _stopLatencyMonitoring() {
        if (this.latencyInterval) {
            clearInterval(this.latencyInterval);
            this.latencyInterval = null;
        }
    }
    
    /**
     * Record latency measurement
     */
    _recordLatency(latency) {
        const measurements = this.connectionMetrics.latencyMeasurements;
        measurements.push(latency);
        
        // Keep only last 10 measurements
        if (measurements.length > 10) {
            measurements.shift();
        }
        
        // Calculate average
        this.connectionMetrics.averageLatency = 
            measurements.reduce((sum, val) => sum + val, 0) / measurements.length;
    }
    
    /**
     * Get connection metrics
     */
    getMetrics() {
        return {
            ...this.connectionMetrics,
            connected: this.connected,
            transport: this.getTransport(),
            id: this.getId(),
            reconnectAttempts: this.reconnectAttempts,
            eventHandlers: Array.from(this.eventHandlers.keys())
        };
    }
    
    /**
     * Get client status for debugging
     */
    getStatus() {
        return {
            connected: this.isConnected(),
            transport: this.getTransport(),
            id: this.getId(),
            config: this.config,
            environment: this.environmentConfig,
            metrics: this.getMetrics()
        };
    }
    
    /**
     * Join a room (if supported by server)
     */
    joinRoom(room) {
        if (this.connected) {
            this.emit('join_room', { room: room });
            console.log(`Joined room: ${room}`);
        } else {
            console.warn(`Cannot join room '${room}': client not connected`);
        }
    }
    
    /**
     * Leave a room (if supported by server)
     */
    leaveRoom(room) {
        if (this.connected) {
            this.emit('leave_room', { room: room });
            console.log(`Left room: ${room}`);
        } else {
            console.warn(`Cannot leave room '${room}': client not connected`);
        }
    }
    
    /**
     * Send a ping to measure latency
     */
    ping() {
        if (this.connected) {
            this.lastPingTime = Date.now();
            this.emit('ping');
        }
    }
    
    /**
     * Cleanup resources
     */
    destroy() {
        console.log('Destroying WebSocket client...');
        
        try {
            // Stop latency monitoring
            this._stopLatencyMonitoring();
            
            // Clear event handlers
            this.eventHandlers.clear();
            
            // Disconnect socket
            if (this.socket) {
                this.socket.disconnect();
                this.socket = null;
            }
            
            console.log('WebSocket client destroyed');
        } catch (error) {
            console.error('Error destroying WebSocket client:', error);
        }
    }
}

// Global factory instance
window.WebSocketClientFactory = new WebSocketClientFactory();

// Convenience function for creating clients
window.createWebSocketClient = async function(options = {}) {
    return await window.WebSocketClientFactory.createClient(options);
};

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { WebSocketClientFactory, StandardizedWebSocketClient };
}

console.log('WebSocket Client Factory loaded and ready');