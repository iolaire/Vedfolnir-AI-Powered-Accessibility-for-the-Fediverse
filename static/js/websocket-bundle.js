// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Combined WebSocket Bundle for Vedfolnir
 * 
 * This bundle combines all essential WebSocket functionality into a single file
 * to reduce initialization chain and improve loading performance:
 * - WebSocket Client Factory
 * - WebSocket Client
 * - Keep-Alive Manager
 * - Debug Utilities (when enabled)
 */

// =============================================================================
// WebSocket Client Factory
// =============================================================================

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
     * @param {Object} options - Client configuration options
     * @returns {Promise<Object>} Configured WebSocket client
     */
    async createClient(options = {}) {
        try {
            console.log('Creating WebSocket client with factory...');
            
            // Build client configuration
            // Get optimized configuration from transport optimizer
        if (typeof window !== 'undefined' && window.webSocketTransportOptimizer) {
            const optimizedConfig = window.webSocketTransportOptimizer.getOptimizedConfig();
            options = { ...optimizedConfig, ...options };
            console.log('🔧 Using optimized transport configuration:', options);
        }
        
        const clientConfig = await this._buildClientConfiguration(options);
            
            // Create Socket.IO client with configuration
            const client = io(clientConfig.url, clientConfig.options);
            
            // Add factory metadata
            client._factoryConfig = clientConfig;
            client._factoryVersion = '1.0.0';
            client._createdAt = new Date().toISOString();
            
            console.log('WebSocket client created successfully');
            
            // Set up transport monitoring
            if (typeof window !== 'undefined' && window.webSocketTransportOptimizer) {
                window.webSocketTransportOptimizer.monitorSocket(client);
                console.log('🔍 WebSocket monitoring enabled');
            }
            
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
            
            // Cache the configuration
            this.configCache = config;
            console.log('Server configuration cached successfully');
            
            return config;
            
        } catch (error) {
            console.error('Failed to fetch server configuration:', error);
            
            // Return fallback configuration
            const fallbackConfig = this._getFallbackConfiguration();
            console.warn('Using fallback WebSocket configuration');
            
            return fallbackConfig;
        }
    }
    
    async _buildClientConfiguration(options) {
        // Get server configuration
        const serverConfig = await this.getServerConfiguration();
        
        // Base configuration from server
        const baseConfig = {
            url: serverConfig.url || this._getDefaultUrl(),
            options: {
                transports: serverConfig.transports || ['websocket', 'polling'],
                reconnection: serverConfig.reconnection !== false,
                reconnectionAttempts: serverConfig.reconnectionAttempts || 5,
                reconnectionDelay: serverConfig.reconnectionDelay || 1000,
                reconnectionDelayMax: serverConfig.reconnectionDelayMax || 5000,
                timeout: serverConfig.timeout || 20000,
                forceNew: serverConfig.forceNew || false,
                upgrade: serverConfig.upgrade !== false,
                rememberUpgrade: serverConfig.rememberUpgrade !== false,
                ...options
            }
        };
        
        return baseConfig;
    }
    
    _detectEnvironment() {
        this.environmentConfig = {
            isLocalhost: ['localhost', '127.0.0.1'].includes(window.location.hostname),
            isSecure: window.location.protocol === 'https:',
            port: window.location.port || (window.location.protocol === 'https:' ? '443' : '80'),
            pathname: window.location.pathname,
            isAdminPage: window.location.pathname.startsWith('/admin'),
            userAgent: navigator.userAgent,
            timestamp: new Date().toISOString()
        };
    }
    
    _validateServerConfiguration(config) {
        if (!config || typeof config !== 'object') {
            return false;
        }
        
        // Basic validation - config should have at least a URL or be an object
        return true;
    }
    
    _getFallbackConfiguration() {
        return {
            url: this._getDefaultUrl(),
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000,
            forceNew: false,
            upgrade: true,
            rememberUpgrade: true
        };
    }
    
    _getDefaultUrl() {
        const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
        const host = window.location.hostname;
        const port = window.location.port ? `:${window.location.port}` : '';
        return `${protocol}//${host}${port}`;
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
            initializing: { class: 'text-muted', icon: 'bi-hourglass-split', text: 'Initializing' },
            loading: { class: 'text-info', icon: 'bi-hourglass-split', text: 'Loading' }
        };
        
        const config = statusConfig[status] || statusConfig.connection_error;
        const displayMessage = message || config.text;
        
        element.className = `text-muted small ${config.class}`;
        element.innerHTML = `<i class="bi ${config.icon}"></i> Real-time: ${displayMessage}`;
    }
}

// =============================================================================
// WebSocket Client
// =============================================================================

class VedfolnirWebSocket {
    constructor(options = {}) {
        // Use factory for client creation if available
        this.useFactory = typeof WebSocketClientFactory !== 'undefined';
        this.factory = this.useFactory ? new WebSocketClientFactory() : null;
        
        // Client instances
        this.userClient = null;
        this.adminClient = null;
        this.currentClient = null;
        
        // Legacy compatibility properties
        this.socket = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.eventHandlers = new Map();
        
        // Connection state management
        this.connectionState = {
            status: 'disconnected',
            lastConnected: null,
            lastDisconnected: null,
            totalReconnects: 0,
            currentNamespace: '/',
            isAdminMode: false
        };
        
        // Configuration
        this.config = {
            autoConnect: options.autoConnect !== false,
            enableDebugMode: options.enableDebugMode || false,
            maxReconnectAttempts: options.maxReconnectAttempts || 5,
            reconnectDelay: options.reconnectDelay || 1000,
            ...options
        };
        
        console.log('VedfolnirWebSocket initialized with factory support:', this.useFactory);
    }
    
    /**
     * Initialize WebSocket connection using factory or fallback to legacy
     */
    async connect() {
        try {
            if (this.useFactory && this.factory) {
                console.log('Connecting using WebSocket factory...');
                await this._connectWithFactory();
            } else {
                console.log('Factory not available, using legacy connection...');
                this._connectLegacy();
            }
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this._connectLegacy(); // Fallback to legacy
        }
    }
    
    /**
     * Connect using WebSocket factory
     */
    async _connectWithFactory() {
        try {
            // Update status to show we're connecting
            this._updateStatusElement('loading', 'Connecting...');
            
            // Determine namespace based on current page
            const isAdminPage = window.location.pathname.startsWith('/admin');
            const namespace = isAdminPage ? '/admin' : '/';
            
            console.log(`Connecting to namespace: ${namespace}`);
            
            // Create client using factory
            const client = await this.factory.createClient({
                forceNew: true,
                upgrade: true,
                rememberUpgrade: true
            });
            
            // Store client reference
            if (isAdminPage) {
                this.adminClient = client;
                this.connectionState.isAdminMode = true;
            } else {
                this.userClient = client;
                this.connectionState.isAdminMode = false;
            }
            
            this.currentClient = client;
            this.socket = client; // Legacy compatibility
            this.connectionState.currentNamespace = namespace;
            
            // Set up event handlers
            this._setupFactoryEventHandlers(client);
            
            console.log('WebSocket factory connection established');
            
        } catch (error) {
            console.error('Factory connection failed:', error);
            throw error;
        }
    }
    
    /**
     * Set up event handlers for factory-created client
     */
    _setupFactoryEventHandlers(client) {
        // Connection events
        client.on('connect', () => {
            console.log('✅ WebSocket connected successfully (factory)');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.connectionState.status = 'connected';
            this.connectionState.lastConnected = new Date();
            this._updateStatusElement('connected');
            this._emitEvent('connect');
        });
        
        client.on('disconnect', (reason) => {
            console.log('❌ WebSocket disconnected (factory):', reason);
            this.connected = false;
            this.connectionState.status = 'disconnected';
            this.connectionState.lastDisconnected = new Date();
            this._updateStatusElement('disconnected');
            this._emitEvent('disconnect', reason);
        });
        
        client.on('connect_error', (error) => {
            console.error('WebSocket connection error (factory):', error);
            this.connectionState.status = 'error';
            this._updateStatusElement('connection_error');
            this.handleConnectionError(error);
        });
        
        client.on('reconnect', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnected after ${attemptNumber} attempts (factory)`);
            this.connected = true;
            this.reconnectAttempts = 0;
            this.connectionState.totalReconnects++;
            this._updateStatusElement('reconnected');
            this._emitEvent('reconnect', attemptNumber);
        });
        
        client.on('reconnect_attempt', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnection attempt ${attemptNumber} (factory)`);
            this.connectionState.status = 'reconnecting';
            this._updateStatusElement('reconnecting');
        });
        
        client.on('reconnect_error', (error) => {
            console.error('WebSocket reconnection error (factory):', error);
            this.connectionState.status = 'reconnect_error';
            this._updateStatusElement('reconnect_error');
        });
        
        client.on('reconnect_failed', () => {
            console.error('❌ WebSocket reconnection failed after maximum attempts (factory)');
            this.connectionState.status = 'failed';
            this._updateStatusElement('connection_error', 'Connection failed');
            this.onReconnectFailed();
        });
    }
    
    /**
     * Legacy connection method (fallback)
     */
    _connectLegacy() {
        console.log('Using legacy WebSocket connection method');
        
        // Initialize Socket.IO connection with improved configuration
        const socketConfig = {
            transports: ['websocket', 'polling'],
            upgrade: true,
            rememberUpgrade: true,
            reconnection: true,
            reconnectionAttempts: this.maxReconnectAttempts,
            reconnectionDelay: this.reconnectDelay,
            reconnectionDelayMax: this.maxReconnectDelay,
            timeout: 20000,
            forceNew: false
        };
        
        // Determine namespace based on current page
        const isAdminPage = window.location.pathname.startsWith('/admin');
        const namespace = isAdminPage ? '/admin' : '/';
        
        console.log(`Connecting to namespace: ${namespace} (legacy)`);
        
        this.socket = io(namespace, socketConfig);
        this.connectionState.currentNamespace = namespace;
        this.connectionState.isAdminMode = isAdminPage;
        
        // Connection events
        this.socket.on('connect', () => {
            console.log('✅ WebSocket connected successfully (legacy)');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.connectionState.status = 'connected';
            this.connectionState.lastConnected = new Date();
            this._updateStatusElement('connected');
            this._emitEvent('connect');
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('❌ WebSocket disconnected (legacy):', reason);
            this.connected = false;
            this.connectionState.status = 'disconnected';
            this.connectionState.lastDisconnected = new Date();
            this._updateStatusElement('disconnected');
            this._emitEvent('disconnect', reason);
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error (legacy):', error);
            this.connectionState.status = 'error';
            this.handleConnectionError(error);
        });
        
        // Handle authentication errors
        this.socket.on('error', (error) => {
            console.error('WebSocket error (legacy):', error);
            if (error && error.message && error.message.includes('Rate limit')) {
                this.showConnectionStatus('rate_limited', 'Rate limit exceeded - please wait');
            }
            this._emitEvent('error', error);
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnected after ${attemptNumber} attempts (legacy)`);
            this.connected = true;
            this.reconnectAttempts = 0;
            this.connectionState.totalReconnects++;
            this._updateStatusElement('reconnected');
            this._emitEvent('reconnect', attemptNumber);
        });
        
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnection attempt ${attemptNumber} (legacy)`);
            this.connectionState.status = 'reconnecting';
            this._updateStatusElement('reconnecting');
        });
        
        this.socket.on('reconnect_error', (error) => {
            console.error('WebSocket reconnection error (legacy):', error);
            this.connectionState.status = 'reconnect_error';
            this._updateStatusElement('reconnect_error');
        });
        
        this.socket.on('reconnect_failed', () => {
            console.error('❌ WebSocket reconnection failed after maximum attempts (legacy)');
            this.connectionState.status = 'failed';
            this._updateStatusElement('connection_error', 'Connection failed');
            this.onReconnectFailed();
        });
    }
    
    /**
     * Update status element in DOM
     */
    _updateStatusElement(status, message = '') {
        if (this.factory && this.factory._updateConnectionStatus) {
            this.factory._updateConnectionStatus(status, message);
        } else {
            // Fallback status update
            const statusElement = document.getElementById('websocket-status');
            if (statusElement) {
                const statusConfig = {
                    connected: { class: 'text-success', icon: 'bi-wifi', text: 'Connected' },
                    disconnected: { class: 'text-warning', icon: 'bi-wifi-off', text: 'Disconnected' },
                    reconnecting: { class: 'text-info', icon: 'bi-arrow-clockwise', text: 'Reconnecting' },
                    loading: { class: 'text-info', icon: 'bi-hourglass-split', text: 'Loading' },
                    connection_error: { class: 'text-danger', icon: 'bi-exclamation-triangle', text: 'Connection Error' }
                };
                
                const config = statusConfig[status] || statusConfig.connection_error;
                const displayMessage = message || config.text;
                
                statusElement.className = `text-muted small ${config.class}`;
                statusElement.innerHTML = `<i class="bi ${config.icon}"></i> Real-time: ${displayMessage}`;
            }
        }
    }
    
    /**
     * Handle connection errors
     */
    handleConnectionError(error) {
        console.error('WebSocket connection error:', error);
        
        if (error && error.message) {
            if (error.message.includes('CORS')) {
                this._updateStatusElement('cors_error', 'CORS Issue');
            } else if (error.message.includes('timeout')) {
                this._updateStatusElement('timeout_error', 'Timeout');
            } else if (error.message.includes('transport')) {
                this._updateStatusElement('transport_error', 'Transport Issue');
            } else {
                this._updateStatusElement('connection_error', 'Connection Error');
            }
        } else {
            this._updateStatusElement('connection_error', 'Connection Error');
        }
        
        this._emitEvent('error', error);
    }
    
    /**
     * Handle reconnection failure
     */
    onReconnectFailed() {
        console.error('WebSocket reconnection failed permanently');
        this._emitEvent('reconnect_failed');
    }
    
    /**
     * Emit custom events
     */
    _emitEvent(eventName, data = null) {
        if (this.eventHandlers.has(eventName)) {
            const handlers = this.eventHandlers.get(eventName);
            handlers.forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in ${eventName} handler:`, error);
                }
            });
        }
    }
    
    /**
     * Add event listener
     */
    on(eventName, handler) {
        if (!this.eventHandlers.has(eventName)) {
            this.eventHandlers.set(eventName, []);
        }
        this.eventHandlers.get(eventName).push(handler);
    }
    
    /**
     * Remove event listener
     */
    off(eventName, handler) {
        if (this.eventHandlers.has(eventName)) {
            const handlers = this.eventHandlers.get(eventName);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }
    
    /**
     * Check if WebSocket is connected
     */
    isConnected() {
        return this.connected && this.socket && this.socket.connected;
    }
    
    /**
     * Emit event to server
     */
    emit(eventName, data) {
        if (this.socket && this.socket.connected) {
            this.socket.emit(eventName, data);
        } else {
            console.warn('Cannot emit event - WebSocket not connected');
        }
    }
    
    /**
     * Disconnect WebSocket
     */
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
        this.connected = false;
        this.connectionState.status = 'disconnected';
    }
}

// =============================================================================
// WebSocket Keep-Alive Manager
// =============================================================================

class WebSocketKeepAlive {
    constructor(socket) {
        this.socket = socket;
        this.keepAliveInterval = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.isPageVisible = true;
        
        this.setupKeepAlive();
        this.setupVisibilityHandling();
        this.setupReconnectionLogic();
    }
    
    setupKeepAlive() {
        // Send ping every 20 seconds to prevent suspension
        this.keepAliveInterval = setInterval(() => {
            if (this.socket && this.socket.connected && this.isPageVisible) {
                this.socket.emit('ping', { timestamp: Date.now() });
                console.log('🏓 WebSocket keep-alive ping sent');
            }
        }, 20000);
        
        // Handle pong responses
        this.socket.on('pong', (data) => {
            console.log('🏓 WebSocket keep-alive pong received');
            this.reconnectAttempts = 0; // Reset reconnect attempts on successful ping
        });
    }
    
    setupVisibilityHandling() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            this.isPageVisible = !document.hidden;
            
            if (this.isPageVisible) {
                console.log('📱 Page became visible - resuming WebSocket');
                this.resumeConnection();
            } else {
                console.log('📱 Page became hidden - WebSocket may be suspended by browser');
            }
        });
    }
    
    setupReconnectionLogic() {
        // Enhanced reconnection logic
        this.socket.on('disconnect', () => {
            if (this.isPageVisible) {
                console.log('🔄 WebSocket disconnected while page visible - attempting reconnection');
                this.attemptReconnection();
            }
        });
        
        this.socket.on('connect_error', () => {
            if (this.isPageVisible && this.reconnectAttempts < this.maxReconnectAttempts) {
                console.log('🔄 WebSocket connection error - attempting reconnection');
                this.attemptReconnection();
            }
        });
    }
    
    resumeConnection() {
        if (!this.socket.connected && this.isPageVisible) {
            console.log('🔄 Resuming WebSocket connection after page became visible');
            this.attemptReconnection();
        }
    }
    
    attemptReconnection() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ Maximum reconnection attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000);
        
        console.log(`🔄 Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (!this.socket.connected && this.isPageVisible) {
                this.socket.connect();
            }
        }, delay);
    }
    
    destroy() {
        if (this.keepAliveInterval) {
            clearInterval(this.keepAliveInterval);
            this.keepAliveInterval = null;
        }
    }
}

// =============================================================================
// WebSocket Debug Utilities (Development Only)
// =============================================================================

window.WebSocketDebug = {
    
    /**
     * Check WebSocket environment and configuration
     */
    checkEnvironment: function() {
        console.log('=== WebSocket Environment Check ===');
        
        // Check Socket.IO availability
        if (typeof io !== 'undefined') {
            console.log('✅ Socket.IO library loaded');
            console.log('   Version:', io.version || 'Unknown');
        } else {
            console.error('❌ Socket.IO library not loaded');
            return false;
        }
        
        // Check VedfolnirWS instance
        if (window.VedfolnirWS) {
            console.log('✅ VedfolnirWS instance available');
            console.log('   Connected:', window.VedfolnirWS.isConnected());
            console.log('   Reconnect attempts:', window.VedfolnirWS.reconnectAttempts);
        } else {
            console.error('❌ VedfolnirWS instance not available');
            return false;
        }
        
        // Check page context
        console.log('📍 Page context:');
        console.log('   Path:', window.location.pathname);
        console.log('   Is admin page:', window.location.pathname.startsWith('/admin'));
        
        // Check authentication indicators
        const userElements = document.querySelectorAll('[data-user-id], .user-authenticated, .admin-authenticated');
        const logoutLinks = document.querySelectorAll('a[href*="logout"]');
        console.log('🔐 Authentication indicators:');
        console.log('   User elements found:', userElements.length);
        console.log('   Logout links found:', logoutLinks.length);
        
        // Check WebSocket status element
        const statusElement = document.getElementById('websocket-status');
        if (statusElement) {
            console.log('✅ WebSocket status element found');
            console.log('   Current status:', statusElement.textContent);
        } else {
            console.warn('⚠️ WebSocket status element not found');
        }
        
        return true;
    },
    
    /**
     * Test WebSocket connection
     */
    testConnection: function() {
        console.log('=== WebSocket Connection Test ===');
        
        if (!window.VedfolnirWS) {
            console.error('❌ VedfolnirWS not available');
            return false;
        }
        
        const ws = window.VedfolnirWS;
        
        console.log('Connection state:', ws.connectionState);
        console.log('Is connected:', ws.isConnected());
        
        if (ws.isConnected()) {
            console.log('✅ WebSocket is connected');
            
            // Test ping
            ws.emit('ping', { test: true, timestamp: Date.now() });
            console.log('📤 Test ping sent');
            
            return true;
        } else {
            console.log('❌ WebSocket is not connected');
            console.log('Attempting to connect...');
            
            ws.connect().then(() => {
                console.log('✅ Connection attempt completed');
            }).catch((error) => {
                console.error('❌ Connection attempt failed:', error);
            });
            
            return false;
        }
    },
    
    /**
     * Get connection statistics
     */
    getStats: function() {
        if (!window.VedfolnirWS) {
            return null;
        }
        
        const ws = window.VedfolnirWS;
        return {
            connected: ws.isConnected(),
            reconnectAttempts: ws.reconnectAttempts,
            connectionState: ws.connectionState,
            config: ws.config,
            factory: ws.factory ? {
                configCache: !!ws.factory.configCache,
                environmentConfig: ws.factory.environmentConfig,
                validationErrors: ws.factory.validationErrors
            } : null
        };
    }
};

// =============================================================================
// Global Initialization
// =============================================================================

// Initialize global WebSocket instance
window.VedfolnirWS = null;
window.WebSocketKeepAlive = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is authenticated before initializing WebSocket
    const isLoginPage = window.location.pathname.includes('/login') || 
                       window.location.pathname === '/' && !document.body.classList.contains('authenticated');
    
    if (isLoginPage) {
        console.log('🔒 Skipping WebSocket initialization on login page');
        return;
    }
    
    console.log('🚀 Initializing WebSocket bundle...');
    
    // Update status to show initialization
    const statusElement = document.getElementById('websocket-status');
    if (statusElement) {
        statusElement.innerHTML = '<i class="bi bi-hourglass-split"></i> Real-time: Loading...';
    }
    
    // Initialize WebSocket client
    window.VedfolnirWS = new VedfolnirWebSocket({
        autoConnect: false,  // Don't auto-connect, we'll check authentication first
        enableDebugMode: false
    });
    
    // Only connect WebSocket if user is authenticated
    if (document.body.dataset.authenticated === 'true') {
        console.log('User is authenticated, connecting WebSocket...');
        // Connect WebSocket
        window.VedfolnirWS.connect().then(() => {
        console.log('✅ WebSocket bundle initialization completed');
        
        // Initialize keep-alive manager
        if (window.VedfolnirWS.socket) {
            window.WebSocketKeepAlive = new WebSocketKeepAlive(window.VedfolnirWS.socket);
            console.log('✅ WebSocket keep-alive initialized');
        }
        
        }).catch((error) => {
            console.error('❌ WebSocket bundle initialization failed:', error);
        });
    } else {
        console.log('User not authenticated, skipping WebSocket connection');
    }
});

// Global function to initialize WebSocket after login
window.initializeWebSocketAfterLogin = function() {
    console.log('🚀 Initializing WebSocket after login...');
    
    // Update status to show initialization
    const statusElement = document.getElementById('websocket-status');
    if (statusElement) {
        statusElement.innerHTML = '<i class="bi bi-hourglass-split"></i> Real-time: Loading...';
    }
    
    try {
        // Initialize WebSocket factory
        window.WebSocketFactory = new WebSocketClientFactory();
        
        // Initialize main WebSocket connection
        window.VedfolnirWS = new VedfolnirWebSocket(window.WebSocketFactory);
        
        // Connect WebSocket
        window.VedfolnirWS.connect().then(() => {
            console.log('✅ WebSocket bundle initialization completed');
            
            // Initialize keep-alive manager
            if (window.VedfolnirWS.socket) {
                window.WebSocketKeepAlive = new WebSocketKeepAlive(window.VedfolnirWS.socket);
                console.log('✅ WebSocket keep-alive initialized');
            }
            
            // Update status to show success
            if (statusElement) {
                statusElement.innerHTML = '<i class="bi bi-wifi text-success"></i> Real-time: Connected';
            }
            
        }).catch((error) => {
            console.error('❌ WebSocket initialization failed after login:', error);
            
            // Update status to show error
            if (statusElement) {
                statusElement.innerHTML = '<i class="bi bi-wifi-off text-danger"></i> Real-time: Error';
            }
        });
        
    } catch (error) {
        console.error('❌ WebSocket bundle initialization failed:', error);
        
        // Update status to show error
        if (statusElement) {
            statusElement.innerHTML = '<i class="bi bi-wifi-off text-danger"></i> Real-time: Error';
        }
    }
};

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.WebSocketKeepAlive) {
        window.WebSocketKeepAlive.destroy();
    }
    
    if (window.VedfolnirWS) {
        window.VedfolnirWS.disconnect();
    }
});

console.log('📦 WebSocket bundle loaded successfully');