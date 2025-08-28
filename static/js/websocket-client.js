// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Refactored WebSocket Client for Vedfolnir
 * Uses WebSocketClientFactory for standardized configuration and error handling
 */

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
        if (this.connected) {
            console.log('WebSocket already connected');
            return;
        }
        
        try {
            console.log('Attempting to connect to WebSocket server...');
            
            if (this.useFactory) {
                await this._connectWithFactory();
            } else {
                this._connectLegacy();
            }
            
        } catch (error) {
            console.error('Failed to initialize WebSocket connection:', error);
            this.handleConnectionError(error);
        }
    }
    
    /**
     * Connect using the WebSocket factory (preferred method)
     */
    async _connectWithFactory() {
        try {
            // Determine if we're on admin page
            const isAdminPage = this.isAdminPage();
            this.connectionState.isAdminMode = isAdminPage;
            
            // Create user client (always needed)
            this.userClient = this.factory.createClient({
                namespace: '/',
                autoConnect: false,
                customConfig: {
                    logger: this.config.enableDebugMode,
                    engineio_logger: false
                }
            });
            
            // Create admin client if on admin page
            if (isAdminPage) {
                this.adminClient = this.factory.createClient({
                    namespace: '/admin',
                    autoConnect: false,
                    customConfig: {
                        logger: this.config.enableDebugMode,
                        engineio_logger: false
                    }
                });
                
                // Use admin client as primary
                this.currentClient = this.adminClient;
                this.connectionState.currentNamespace = '/admin';
            } else {
                // Use user client as primary
                this.currentClient = this.userClient;
                this.connectionState.currentNamespace = '/';
            }
            
            // Setup legacy compatibility
            this.socket = this.currentClient.socket;
            
            // Setup event handlers
            this.setupEventHandlers();
            
            // Connect the client
            this.currentClient.connect();
            
            console.log(`Connected using factory to namespace: ${this.connectionState.currentNamespace}`);
            
        } catch (error) {
            console.error('Factory connection failed, falling back to legacy:', error);
            this._connectLegacy();
        }
    }
    
    /**
     * Legacy connection method (fallback)
     */
    _connectLegacy() {
        console.log('Using legacy WebSocket connection method');
        
        // Initialize Socket.IO connection with improved configuration
        this.socket = io({
            transports: ['polling', 'websocket'], // Allow both transports
            upgrade: true, // Allow upgrade to WebSocket if available
            timeout: 10000, // Longer timeout for better reliability
            forceNew: false, // Allow connection reuse
            reconnection: true, // Enable auto-reconnection
            reconnectionAttempts: this.maxReconnectAttempts,
            reconnectionDelay: this.reconnectDelay,
            reconnectionDelayMax: this.maxReconnectDelay,
            maxHttpBufferSize: 1e6,
            pingTimeout: 60000, // 60 seconds ping timeout
            pingInterval: 25000, // 25 seconds ping interval
            withCredentials: true, // Include cookies for authentication
            auth: {
                // Include any authentication data if needed
                timestamp: Date.now()
            }
        });
        
        this.setupEventHandlers();
    }
    
    /**
     * Setup Socket.IO event handlers for both factory and legacy clients
     */
    setupEventHandlers() {
        if (this.useFactory && this.currentClient) {
            this._setupFactoryEventHandlers();
        } else if (this.socket) {
            this._setupLegacyEventHandlers();
        }
        
        // Setup shared event handlers for both user and admin clients
        if (this.useFactory) {
            this._setupSharedEventHandlers();
        }
    }
    
    /**
     * Setup event handlers for factory-created clients
     */
    _setupFactoryEventHandlers() {
        // Connection events for current client
        this.currentClient.on('connect', () => {
            console.log(`✅ WebSocket connected successfully to ${this.connectionState.currentNamespace}`);
            this.connected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.connectionState.status = 'connected';
            this.connectionState.lastConnected = Date.now();
            this.onConnect();
        });
        
        this.currentClient.on('disconnect', (reason) => {
            console.log(`❌ WebSocket disconnected from ${this.connectionState.currentNamespace}:`, reason);
            this.connected = false;
            this.connectionState.status = 'disconnected';
            this.connectionState.lastDisconnected = Date.now();
            this.onDisconnect(reason);
        });
        
        this.currentClient.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.connectionState.status = 'error';
            this.handleConnectionError(error);
        });
        
        this.currentClient.on('reconnect', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnected after ${attemptNumber} attempts`);
            this.connected = true;
            this.reconnectAttempts = 0;
            this.connectionState.totalReconnects++;
            this.connectionState.status = 'connected';
        });
        
        this.currentClient.on('reconnect_attempt', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnection attempt ${attemptNumber}`);
            this.connectionState.status = 'reconnecting';
        });
        
        this.currentClient.on('reconnect_error', (error) => {
            console.error('WebSocket reconnection error:', error);
            this.connectionState.status = 'reconnect_error';
        });
        
        this.currentClient.on('reconnect_failed', () => {
            console.error('❌ WebSocket reconnection failed after maximum attempts');
            this.connectionState.status = 'failed';
            this.onReconnectFailed();
        });
        
        // Error handling
        this.currentClient.on('error', (error) => {
            console.error('WebSocket error:', error);
            if (error && error.message && error.message.includes('Rate limit')) {
                this.showConnectionStatus('rate_limited', 'Rate limit exceeded - please wait');
            } else {
                this.handleConnectionError(error);
            }
        });
    }
    
    /**
     * Setup event handlers for legacy Socket.IO client
     */
    _setupLegacyEventHandlers() {
        // Connection events
        this.socket.on('connect', () => {
            console.log('✅ WebSocket connected successfully (legacy)');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.connectionState.status = 'connected';
            this.connectionState.lastConnected = Date.now();
            this.onConnect();
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('❌ WebSocket disconnected (legacy):', reason);
            this.connected = false;
            this.connectionState.status = 'disconnected';
            this.connectionState.lastDisconnected = Date.now();
            this.onDisconnect(reason);
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
            } else {
                this.handleConnectionError(error);
            }
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnected after ${attemptNumber} attempts (legacy)`);
            this.connected = true;
            this.reconnectAttempts = 0;
            this.connectionState.totalReconnects++;
            this.connectionState.status = 'connected';
        });
        
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnection attempt ${attemptNumber} (legacy)`);
            this.connectionState.status = 'reconnecting';
        });
        
        this.socket.on('reconnect_error', (error) => {
            console.error('WebSocket reconnection error (legacy):', error);
            this.connectionState.status = 'reconnect_error';
        });
        
        this.socket.on('reconnect_failed', () => {
            console.error('❌ WebSocket reconnection failed after maximum attempts (legacy)');
            this.connectionState.status = 'failed';
            this.onReconnectFailed();
        });
    }
    
    /**
     * Setup shared event handlers for both user and admin functionality
     */
    _setupSharedEventHandlers() {
        // Setup handlers for user client
        if (this.userClient) {
            this._setupApplicationEventHandlers(this.userClient, 'user');
        }
        
        // Setup handlers for admin client
        if (this.adminClient) {
            this._setupApplicationEventHandlers(this.adminClient, 'admin');
            this._setupAdminSpecificEventHandlers(this.adminClient);
        }
    }
    
    /**
     * Setup application-specific event handlers
     */
    _setupApplicationEventHandlers(client, clientType) {
        // Progress tracking events (available on both user and admin)
        client.on('progress_update', (data) => {
            console.log(`Progress update (${clientType}):`, data);
            this.handleProgressUpdate(data);
        });
        
        client.on('task_completed', (data) => {
            console.log(`Task completed (${clientType}):`, data);
            this.handleTaskCompleted(data);
        });
        
        client.on('task_error', (data) => {
            console.error(`Task error (${clientType}):`, data);
            this.handleTaskError(data);
        });
        
        client.on('task_cancelled', (data) => {
            console.log(`Task cancelled (${clientType}):`, data);
            this.handleTaskCancelled(data);
        });
        
        // User notification events
        client.on('user_notification', (data) => {
            console.log(`User notification (${clientType}):`, data);
            this.handleUserNotification(data);
        });
    }
    
    /**
     * Setup admin-specific event handlers
     */
    _setupAdminSpecificEventHandlers(adminClient) {
        // Admin dashboard events
        adminClient.on('system_metrics_update', (data) => {
            console.log('Admin: System metrics update:', data);
            this.handleSystemMetricsUpdate(data);
        });
        
        adminClient.on('job_update', (data) => {
            console.log('Admin: Job update:', data);
            this.handleJobUpdate(data);
        });
        
        adminClient.on('admin_alert', (data) => {
            console.log('Admin: Alert received:', data);
            this.handleAdminAlert(data);
        });
        
        // System health events
        adminClient.on('system_health_update', (data) => {
            console.log('Admin: System health update:', data);
            this.handleSystemHealthUpdate(data);
        });
        
        // User management events
        adminClient.on('user_activity_update', (data) => {
            console.log('Admin: User activity update:', data);
            this.handleUserActivityUpdate(data);
        });
    }
    
    /**
     * Handle successful connection
     */
    onConnect() {
        // Join admin dashboard room if on admin page
        if (this.isAdminPage()) {
            this.joinAdminDashboard();
        }
        
        // Show connection status
        this.showConnectionStatus('connected');
        
        // Trigger custom connect handlers
        this.triggerEvent('connect');
    }
    
    /**
     * Handle disconnection
     */
    onDisconnect(reason) {
        this.showConnectionStatus('disconnected', reason);
        this.triggerEvent('disconnect', reason);
    }
    
    /**
     * Handle connection errors with enhanced factory support
     */
    handleConnectionError(error) {
        console.error('WebSocket connection error:', error);
        
        // If using factory, let it handle the error
        if (this.useFactory && this.currentClient && this.currentClient._handleConnectionError) {
            this.currentClient._handleConnectionError(error);
            return;
        }
        
        // Legacy error handling
        this._handleConnectionErrorLegacy(error);
    }
    
    /**
     * Legacy connection error handling
     */
    _handleConnectionErrorLegacy(error) {
        // Check for specific error types
        const errorMessage = error && error.message ? error.message.toLowerCase() : '';
        
        if (errorMessage.includes('unauthorized') || errorMessage.includes('forbidden')) {
            console.warn('WebSocket connection failed due to authentication. This is normal if not logged in.');
            this.showConnectionStatus('auth_required', 'Authentication required for real-time updates');
            this.triggerEvent('auth_required', error);
            return;
        }
        
        if (errorMessage.includes('suspension') || errorMessage.includes('suspended')) {
            console.warn('WebSocket connection suspended by browser. Switching to polling mode.');
            this.showConnectionStatus('suspended', 'Connection suspended - using polling mode');
            // Try to reconnect with polling only
            this.reconnectWithPolling();
            return;
        }
        
        if (errorMessage.includes('cors') || errorMessage.includes('cross-origin') || 
            errorMessage.includes('access control') || errorMessage.includes('xhr poll error')) {
            console.error('CORS/Network error detected. This may be a temporary issue.');
            this.showConnectionStatus('cors_error', 'Network/CORS error - will retry automatically');
            
            // For CORS errors, try a different approach after a delay
            setTimeout(() => {
                console.log('Attempting to reconnect after CORS error...');
                this.reconnectWithPolling();
            }, 3000);
            
            this.triggerEvent('cors_error', error);
            return;
        }
        
        this.reconnectAttempts++;
        
        if (this.reconnectAttempts <= this.maxReconnectAttempts) {
            // Exponential backoff
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
            console.log(`Will retry connection in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            this.showConnectionStatus('reconnecting', `Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        } else {
            this.showConnectionStatus('error', 'Connection failed after maximum retry attempts');
        }
        
        this.triggerEvent('error', error);
    }
    
    /**
     * Handle reconnection failure
     */
    onReconnectFailed() {
        this.showConnectionStatus('failed', 'Unable to establish connection');
        this.triggerEvent('reconnect_failed');
    }
    
    /**
     * Reconnect with polling-only mode
     */
    reconnectWithPolling() {
        console.log('Attempting to reconnect with polling-only mode...');
        this.showConnectionStatus('reconnecting', 'Switching to polling mode...');
        
        if (this.useFactory && this.currentClient) {
            // Use factory's transport fallback mechanism
            if (this.currentClient._reconfigureTransports) {
                this.currentClient._reconfigureTransports(['polling']);
                this.currentClient.forceReconnect();
            } else {
                // Fallback to recreating client with polling only
                this._recreateClientWithPolling();
            }
        } else {
            // Legacy polling reconnection
            this._reconnectWithPollingLegacy();
        }
    }
    
    /**
     * Recreate client with polling-only transport
     */
    async _recreateClientWithPolling() {
        try {
            // Disconnect current client
            if (this.currentClient) {
                this.currentClient.disconnect();
            }
            
            // Create new client with polling only
            const isAdminMode = this.connectionState.isAdminMode;
            const namespace = isAdminMode ? '/admin' : '/';
            
            this.currentClient = this.factory.createClient({
                namespace: namespace,
                autoConnect: false,
                customConfig: {
                    transports: ['polling'],
                    upgrade: false,
                    timeout: 20000,
                    forceNew: true,
                    logger: this.config.enableDebugMode
                }
            });
            
            // Update socket reference for legacy compatibility
            this.socket = this.currentClient.socket;
            
            // Setup event handlers
            this.setupEventHandlers();
            
            // Connect
            this.currentClient.connect();
            
        } catch (error) {
            console.error('Failed to recreate client with polling, falling back to legacy:', error);
            this._reconnectWithPollingLegacy();
        }
    }
    
    /**
     * Legacy polling reconnection
     */
    _reconnectWithPollingLegacy() {
        if (this.socket) {
            this.socket.disconnect();
        }
        
        this.socket = io({
            transports: ['polling'], // Polling only to avoid suspension
            upgrade: false, // Don't upgrade to WebSocket
            timeout: 20000, // Longer timeout for polling
            forceNew: true, // Force new connection
            reconnection: true,
            reconnectionAttempts: 5, // More attempts for polling fallback
            reconnectionDelay: 3000,
            reconnectionDelayMax: 10000,
            maxHttpBufferSize: 1e6,
            withCredentials: true, // Include credentials for CORS
            auth: {
                timestamp: Date.now(),
                fallback: 'polling'
            }
        });
        
        this.setupEventHandlers();
    }
    
    /**
     * Force reconnection with fresh configuration
     */
    forceReconnect() {
        console.log('Force reconnecting WebSocket...');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.connectionState.status = 'reconnecting';
        
        if (this.useFactory && this.currentClient) {
            // Use factory's force reconnect if available
            if (this.currentClient.forceReconnect) {
                this.currentClient.forceReconnect();
            } else {
                // Fallback to disconnect and reconnect
                this.currentClient.disconnect();
                setTimeout(() => {
                    this.currentClient.connect();
                }, 1000);
            }
        } else {
            // Legacy force reconnect
            if (this.socket) {
                this.socket.disconnect();
            }
            
            // Wait a moment then reconnect
            setTimeout(() => {
                this.connect();
            }, 1000);
        }
    }
    
    /**
     * Join admin dashboard room
     */
    joinAdminDashboard() {
        if (this.useFactory && this.adminClient) {
            console.log('Joining admin dashboard room (factory)...');
            if (this.adminClient.joinRoom) {
                this.adminClient.joinRoom('admin_dashboard');
            } else {
                this.adminClient.emit('join_admin_dashboard');
            }
        } else if (this.socket && this.connected) {
            console.log('Joining admin dashboard room (legacy)...');
            this.socket.emit('join_admin_dashboard');
        }
    }
    
    /**
     * Leave admin dashboard room
     */
    leaveAdminDashboard() {
        if (this.useFactory && this.adminClient) {
            console.log('Leaving admin dashboard room (factory)...');
            if (this.adminClient.leaveRoom) {
                this.adminClient.leaveRoom('admin_dashboard');
            } else {
                this.adminClient.emit('leave_admin_dashboard');
            }
        } else if (this.socket && this.connected) {
            console.log('Leaving admin dashboard room (legacy)...');
            this.socket.emit('leave_admin_dashboard');
        }
    }
    
    /**
     * Join task room for progress tracking
     */
    joinTask(taskId) {
        if (!taskId) return;
        
        const roomName = `task_${taskId}`;
        console.log(`Joining task room: ${roomName}`);
        
        if (this.useFactory) {
            // Join on both clients if available
            if (this.userClient && this.userClient.joinRoom) {
                this.userClient.joinRoom(roomName);
            }
            if (this.adminClient && this.adminClient.joinRoom) {
                this.adminClient.joinRoom(roomName);
            }
            
            // Fallback to emit if joinRoom not available
            if (this.currentClient && this.currentClient.connected) {
                this.currentClient.emit('join_task', { task_id: taskId });
            }
        } else if (this.socket && this.connected) {
            this.socket.emit('join_task', { task_id: taskId });
        }
    }
    
    /**
     * Leave task room
     */
    leaveTask(taskId) {
        if (!taskId) return;
        
        const roomName = `task_${taskId}`;
        console.log(`Leaving task room: ${roomName}`);
        
        if (this.useFactory) {
            // Leave on both clients if available
            if (this.userClient && this.userClient.leaveRoom) {
                this.userClient.leaveRoom(roomName);
            }
            if (this.adminClient && this.adminClient.leaveRoom) {
                this.adminClient.leaveRoom(roomName);
            }
            
            // Fallback to emit if leaveRoom not available
            if (this.currentClient && this.currentClient.connected) {
                this.currentClient.emit('leave_task', { task_id: taskId });
            }
        } else if (this.socket && this.connected) {
            this.socket.emit('leave_task', { task_id: taskId });
        }
    }
    
    /**
     * Cancel task
     */
    cancelTask(taskId) {
        if (!taskId) return;
        
        console.log(`Cancelling task: ${taskId}`);
        
        if (this.useFactory && this.currentClient && this.currentClient.connected) {
            this.currentClient.emit('cancel_task', { task_id: taskId });
        } else if (this.socket && this.connected) {
            this.socket.emit('cancel_task', { task_id: taskId });
        }
    }
    
    /**
     * Get task status
     */
    getTaskStatus(taskId) {
        if (!taskId) return;
        
        console.log(`Getting task status: ${taskId}`);
        
        if (this.useFactory && this.currentClient && this.currentClient.connected) {
            this.currentClient.emit('get_task_status', { task_id: taskId });
        } else if (this.socket && this.connected) {
            this.socket.emit('get_task_status', { task_id: taskId });
        }
    }
    
    /**
     * Handle system metrics update
     */
    handleSystemMetricsUpdate(data) {
        console.log('System metrics update:', data);
        this.triggerEvent('system_metrics_update', data);
    }
    
    /**
     * Handle job update
     */
    handleJobUpdate(data) {
        console.log('Job update:', data);
        this.triggerEvent('job_update', data);
    }
    
    /**
     * Handle admin alert
     */
    handleAdminAlert(data) {
        console.log('Admin alert:', data);
        this.triggerEvent('admin_alert', data);
        
        // Show alert in UI
        if (window.Vedfolnir && window.Vedfolnir.showToast) {
            const alertType = data.alert && data.alert.level ? data.alert.level : 'info';
            const alertMessage = data.alert && data.alert.message ? data.alert.message : 'System alert received';
            window.Vedfolnir.showToast(alertMessage, alertType);
        }
    }
    
    /**
     * Handle progress update
     */
    handleProgressUpdate(data) {
        console.log('Progress update:', data);
        this.triggerEvent('progress_update', data);
    }
    
    /**
     * Handle task completion
     */
    handleTaskCompleted(data) {
        console.log('Task completed:', data);
        this.triggerEvent('task_completed', data);
    }
    
    /**
     * Handle task error
     */
    handleTaskError(data) {
        console.error('Task error:', data);
        this.triggerEvent('task_error', data);
    }
    
    /**
     * Handle task cancellation
     */
    handleTaskCancelled(data) {
        console.log('Task cancelled:', data);
        this.triggerEvent('task_cancelled', data);
    }
    
    /**
     * Handle user notifications
     */
    handleUserNotification(data) {
        console.log('User notification:', data);
        this.triggerEvent('user_notification', data);
        
        // Show notification in UI if available
        if (window.Vedfolnir && window.Vedfolnir.showToast) {
            const notificationType = data.type || 'info';
            const notificationMessage = data.message || 'Notification received';
            window.Vedfolnir.showToast(notificationMessage, notificationType);
        }
    }
    
    /**
     * Handle system health updates (admin only)
     */
    handleSystemHealthUpdate(data) {
        console.log('System health update:', data);
        this.triggerEvent('system_health_update', data);
        
        // Update health indicators in admin UI
        if (typeof updateSystemHealthIndicators === 'function') {
            updateSystemHealthIndicators(data);
        }
    }
    
    /**
     * Handle user activity updates (admin only)
     */
    handleUserActivityUpdate(data) {
        console.log('User activity update:', data);
        this.triggerEvent('user_activity_update', data);
        
        // Update user activity displays in admin UI
        if (typeof updateUserActivityDisplay === 'function') {
            updateUserActivityDisplay(data);
        }
    }
    
    /**
     * Show connection status in UI with enhanced factory support
     */
    showConnectionStatus(status, message = '') {
        // If using factory, emit custom event for factory's status system to handle
        if (this.useFactory) {
            window.dispatchEvent(new CustomEvent('websocketStatusChange', {
                detail: { 
                    status, 
                    message, 
                    timestamp: Date.now(),
                    namespace: this.connectionState.currentNamespace,
                    source: 'vedfolnir-client'
                }
            }));
        }
        
        // Also update our own status element for backward compatibility
        this._updateStatusElement(status, message);
        
        // Update connection state
        this.connectionState.status = status;
    }
    
    /**
     * Update status element in DOM
     */
    _updateStatusElement(status, message = '') {
        const statusElement = document.getElementById('websocket-status');
        if (!statusElement) return;
        
        const statusConfig = {
            connected: { class: 'text-success', icon: 'bi-wifi', text: 'Connected' },
            disconnected: { class: 'text-warning', icon: 'bi-wifi-off', text: 'Disconnected' },
            reconnecting: { class: 'text-info', icon: 'bi-arrow-clockwise', text: 'Reconnecting' },
            suspended: { class: 'text-warning', icon: 'bi-pause-circle', text: 'Suspended' },
            cors_error: { class: 'text-danger', icon: 'bi-shield-x', text: 'CORS Error' },
            error: { class: 'text-danger', icon: 'bi-exclamation-triangle', text: 'Connection Error' },
            failed: { class: 'text-danger', icon: 'bi-x-circle', text: 'Connection Failed' },
            auth_required: { class: 'text-info', icon: 'bi-shield-lock', text: 'Auth Required' },
            rate_limited: { class: 'text-warning', icon: 'bi-hourglass-split', text: 'Rate Limited' },
            timeout_error: { class: 'text-warning', icon: 'bi-clock', text: 'Timeout' },
            transport_error: { class: 'text-warning', icon: 'bi-arrow-repeat', text: 'Transport Issue' }
        };
        
        const config = statusConfig[status] || { 
            class: 'text-muted', 
            icon: 'bi-question-circle', 
            text: 'Unknown' 
        };
        
        statusElement.className = config.class;
        statusElement.innerHTML = `<i class="bi ${config.icon}"></i> ${config.text}`;
        
        if (message) {
            statusElement.title = message;
        }
        
        // Add namespace info for debugging
        if (this.config.enableDebugMode && this.connectionState.currentNamespace !== '/') {
            statusElement.innerHTML += ` (${this.connectionState.currentNamespace})`;
        }
    }
    
    /**
     * Check if current page is admin page
     */
    isAdminPage() {
        return window.location.pathname.startsWith('/admin');
    }
    
    /**
     * Add event handler
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }
    
    /**
     * Remove event handler
     */
    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            const handlers = this.eventHandlers.get(event);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }
    
    /**
     * Trigger event handlers
     */
    triggerEvent(event, data = null) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }
    
    /**
     * Disconnect WebSocket with enhanced factory support
     */
    disconnect() {
        console.log('Disconnecting WebSocket...');
        
        // Leave admin dashboard if connected
        if (this.isAdminPage()) {
            this.leaveAdminDashboard();
        }
        
        if (this.useFactory) {
            // Disconnect factory clients
            if (this.userClient) {
                this.userClient.disconnect();
            }
            if (this.adminClient) {
                this.adminClient.disconnect();
            }
            this.currentClient = null;
        } else if (this.socket) {
            // Legacy disconnect
            this.socket.disconnect();
        }
        
        // Reset state
        this.socket = null;
        this.connected = false;
        this.connectionState.status = 'disconnected';
        this.connectionState.lastDisconnected = Date.now();
    }
    
    /**
     * Get connection status
     */
    isConnected() {
        if (this.useFactory && this.currentClient) {
            return this.currentClient.connected || (this.currentClient.socket && this.currentClient.socket.connected);
        }
        return this.connected && this.socket && this.socket.connected;
    }
    
    /**
     * Get detailed connection state information
     */
    getConnectionState() {
        return {
            ...this.connectionState,
            connected: this.isConnected(),
            useFactory: this.useFactory,
            hasUserClient: !!this.userClient,
            hasAdminClient: !!this.adminClient,
            currentClientConnected: this.currentClient ? this.currentClient.connected : false
        };
    }
    
    /**
     * Switch between user and admin contexts
     */
    switchContext(isAdmin = false) {
        if (!this.useFactory) {
            console.warn('Context switching requires factory support');
            return false;
        }
        
        const targetClient = isAdmin ? this.adminClient : this.userClient;
        const targetNamespace = isAdmin ? '/admin' : '/';
        
        if (!targetClient) {
            console.error(`Target client for ${targetNamespace} not available`);
            return false;
        }
        
        console.log(`Switching context to ${targetNamespace}`);
        
        // Update current client
        this.currentClient = targetClient;
        this.connectionState.currentNamespace = targetNamespace;
        this.connectionState.isAdminMode = isAdmin;
        
        // Update socket reference for legacy compatibility
        this.socket = targetClient.socket;
        this.connected = targetClient.connected;
        
        return true;
    }
    
    /**
     * Emit event to appropriate client based on context
     */
    emit(event, data, callback) {
        if (this.useFactory && this.currentClient) {
            return this.currentClient.emit(event, data, callback);
        } else if (this.socket) {
            return this.socket.emit(event, data, callback);
        }
        
        console.warn('No active WebSocket client available for emit');
        return false;
    }
}

// Global WebSocket instance
window.VedfolnirWS = null;

// Initialize WebSocket when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if Socket.IO is available
    if (typeof io !== 'undefined') {
        console.log('Initializing Vedfolnir WebSocket client...');
        
        // Always use the new VedfolnirWebSocket class which handles factory detection internally
        window.VedfolnirWS = new VedfolnirWebSocket({
            autoConnect: false, // We'll handle connection timing manually
            enableDebugMode: window.location.search.includes('debug=1'),
            maxReconnectAttempts: 5,
            reconnectDelay: 1000
        });
        
        // Auto-connect for admin pages with improved error handling
        if (window.location.pathname.startsWith('/admin')) {
            console.log('WebSocket client initialized for admin page');
            
            // Add status indicator first
            setTimeout(() => {
                addWebSocketStatusIndicator();
            }, 500);
            
            // Check authentication status before connecting
            setTimeout(() => {
                checkAuthenticationAndConnect();
            }, 2000); // Longer delay to ensure page is fully loaded
        } else {
            // For non-admin pages, still add status indicator and connect
            setTimeout(() => {
                addWebSocketStatusIndicator();
                checkAuthenticationAndConnect();
            }, 1000);
        }
        
        // Function to check authentication before connecting
        function checkAuthenticationAndConnect() {
            // Check if user is authenticated by looking for user-specific elements
            const userElements = document.querySelectorAll('[data-user-id], .user-authenticated, .admin-authenticated');
            const logoutLinks = document.querySelectorAll('a[href*="logout"]');
            
            if (userElements.length > 0 || logoutLinks.length > 0) {
                console.log('User appears to be authenticated, connecting WebSocket...');
                window.VedfolnirWS.connect();
            } else {
                console.log('User authentication status unclear, attempting connection anyway...');
                window.VedfolnirWS.connect();
            }
        }
        
        // Function to add status indicator and connect button
        function addWebSocketStatusIndicator() {
            const statusElement = document.getElementById('websocket-status');
            if (statusElement) {
                if (!window.VedfolnirWS.isConnected()) {
                    statusElement.innerHTML = `
                        <div class="d-flex align-items-center">
                            <span class="text-muted me-2">
                                <i class="bi bi-wifi-off"></i> Real-time: Connecting...
                            </span>
                            <button class="btn btn-sm btn-outline-secondary" onclick="window.VedfolnirWS.connect()" title="Retry WebSocket connection">
                                <i class="bi bi-arrow-clockwise"></i>
                            </button>
                        </div>
                    `;
                }
            }
        }
        
        // Add event listeners for connection status updates
        window.VedfolnirWS.on('connect', function() {
            const statusElement = document.getElementById('websocket-status');
            if (statusElement) {
                statusElement.innerHTML = `
                    <span class="text-success" title="WebSocket connected - real-time updates active">
                        <i class="bi bi-wifi"></i> Real-time: Connected
                    </span>
                `;
            }
            
            // Show success toast if available
            if (window.Vedfolnir && window.Vedfolnir.showToast) {
                window.Vedfolnir.showToast('Real-time updates connected', 'success');
            }
        });
        
        window.VedfolnirWS.on('disconnect', function() {
            const statusElement = document.getElementById('websocket-status');
            if (statusElement) {
                statusElement.innerHTML = `
                    <div class="d-flex align-items-center">
                        <span class="text-warning me-2">
                            <i class="bi bi-wifi-off"></i> Real-time: Disconnected
                        </span>
                        <button class="btn btn-sm btn-outline-warning" onclick="window.VedfolnirWS.connect()" title="Reconnect WebSocket">
                            <i class="bi bi-arrow-clockwise"></i>
                        </button>
                    </div>
                `;
            }
        });
        
        window.VedfolnirWS.on('error', function() {
            const statusElement = document.getElementById('websocket-status');
            if (statusElement) {
                statusElement.innerHTML = `
                    <div class="d-flex align-items-center">
                        <span class="text-danger me-2">
                            <i class="bi bi-exclamation-triangle"></i> Real-time: Error
                        </span>
                        <button class="btn btn-sm btn-outline-danger me-1" onclick="window.VedfolnirWS.forceReconnect()" title="Force reconnect WebSocket">
                            <i class="bi bi-arrow-clockwise"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-warning" onclick="window.VedfolnirWS.reconnectWithPolling()" title="Try polling mode">
                            <i class="bi bi-wifi-off"></i>
                        </button>
                    </div>
                `;
            }
        });
        
        window.VedfolnirWS.on('cors_error', function() {
            const statusElement = document.getElementById('websocket-status');
            if (statusElement) {
                statusElement.innerHTML = `
                    <div class="d-flex align-items-center">
                        <span class="text-warning me-2">
                            <i class="bi bi-shield-x"></i> Real-time: CORS Issue
                        </span>
                        <button class="btn btn-sm btn-outline-warning" onclick="window.VedfolnirWS.forceReconnect()" title="Retry connection">
                            <i class="bi bi-arrow-clockwise"></i> Retry
                        </button>
                    </div>
                `;
            }
        });
        
        // Listen for factory status updates
        window.addEventListener('websocketStatusChange', function(event) {
            const { status, message, namespace } = event.detail;
            console.log(`WebSocket status change: ${status} (${namespace}) - ${message}`);
            
            // Update UI based on factory status updates
            if (window.VedfolnirWS && window.VedfolnirWS.showConnectionStatus) {
                window.VedfolnirWS.showConnectionStatus(status, message);
            }
        });
        
    } else {
        console.warn('Socket.IO library not loaded, WebSocket functionality disabled');
        
        // Show fallback status if on admin page
        if (window.location.pathname.startsWith('/admin')) {
            setTimeout(() => {
                const statusElement = document.getElementById('websocket-status');
                if (statusElement) {
                    statusElement.innerHTML = `
                        <span class="text-muted">
                            <i class="bi bi-exclamation-circle"></i> Real-time: Unavailable
                        </span>
                    `;
                }
            }, 1000);
        }
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.VedfolnirWS) {
        window.VedfolnirWS.disconnect();
    }
});