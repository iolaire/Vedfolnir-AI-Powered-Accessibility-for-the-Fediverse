// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * WebSocket Client for Vedfolnir
 * Handles Socket.IO connections for real-time updates
 */

class VedfolnirWebSocket {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        this.eventHandlers = new Map();
        
        console.log('VedfolnirWebSocket initialized');
    }
    
    /**
     * Initialize WebSocket connection
     */
    connect() {
        if (this.socket && this.connected) {
            console.log('WebSocket already connected');
            return;
        }
        
        try {
            console.log('Attempting to connect to WebSocket server...');
            
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
            
        } catch (error) {
            console.error('Failed to initialize WebSocket connection:', error);
            this.handleConnectionError(error);
        }
    }
    
    /**
     * Setup Socket.IO event handlers
     */
    setupEventHandlers() {
        if (!this.socket) return;
        
        // Connection events
        this.socket.on('connect', () => {
            console.log('✅ WebSocket connected successfully');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.onConnect();
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('❌ WebSocket disconnected:', reason);
            this.connected = false;
            this.onDisconnect(reason);
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.handleConnectionError(error);
        });
        
        // Handle authentication errors
        this.socket.on('error', (error) => {
            console.error('WebSocket error:', error);
            if (error && error.message && error.message.includes('Rate limit')) {
                this.showConnectionStatus('rate_limited', 'Rate limit exceeded - please wait');
            } else {
                this.handleConnectionError(error);
            }
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnected after ${attemptNumber} attempts`);
            this.connected = true;
            this.reconnectAttempts = 0;
        });
        
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnection attempt ${attemptNumber}`);
        });
        
        this.socket.on('reconnect_error', (error) => {
            console.error('WebSocket reconnection error:', error);
        });
        
        this.socket.on('reconnect_failed', () => {
            console.error('❌ WebSocket reconnection failed after maximum attempts');
            this.onReconnectFailed();
        });
        
        // Admin dashboard events
        this.socket.on('system_metrics_update', (data) => {
            this.handleSystemMetricsUpdate(data);
        });
        
        this.socket.on('job_update', (data) => {
            this.handleJobUpdate(data);
        });
        
        this.socket.on('admin_alert', (data) => {
            this.handleAdminAlert(data);
        });
        
        // Progress tracking events
        this.socket.on('progress_update', (data) => {
            this.handleProgressUpdate(data);
        });
        
        this.socket.on('task_completed', (data) => {
            this.handleTaskCompleted(data);
        });
        
        this.socket.on('task_error', (data) => {
            this.handleTaskError(data);
        });
        
        this.socket.on('task_cancelled', (data) => {
            this.handleTaskCancelled(data);
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
     * Handle connection errors
     */
    handleConnectionError(error) {
        console.error('WebSocket connection error:', error);
        
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
        if (this.socket) {
            this.socket.disconnect();
        }
        
        console.log('Attempting to reconnect with polling-only mode...');
        this.showConnectionStatus('reconnecting', 'Switching to polling mode...');
        
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
        
        if (this.socket) {
            this.socket.disconnect();
        }
        
        // Wait a moment then reconnect
        setTimeout(() => {
            this.connect();
        }, 1000);
    }
    
    /**
     * Join admin dashboard room
     */
    joinAdminDashboard() {
        if (this.socket && this.connected) {
            console.log('Joining admin dashboard room...');
            this.socket.emit('join_admin_dashboard');
        }
    }
    
    /**
     * Leave admin dashboard room
     */
    leaveAdminDashboard() {
        if (this.socket && this.connected) {
            console.log('Leaving admin dashboard room...');
            this.socket.emit('leave_admin_dashboard');
        }
    }
    
    /**
     * Join task room for progress tracking
     */
    joinTask(taskId) {
        if (this.socket && this.connected && taskId) {
            console.log(`Joining task room: ${taskId}`);
            this.socket.emit('join_task', { task_id: taskId });
        }
    }
    
    /**
     * Leave task room
     */
    leaveTask(taskId) {
        if (this.socket && this.connected && taskId) {
            console.log(`Leaving task room: ${taskId}`);
            this.socket.emit('leave_task', { task_id: taskId });
        }
    }
    
    /**
     * Cancel task
     */
    cancelTask(taskId) {
        if (this.socket && this.connected && taskId) {
            console.log(`Cancelling task: ${taskId}`);
            this.socket.emit('cancel_task', { task_id: taskId });
        }
    }
    
    /**
     * Get task status
     */
    getTaskStatus(taskId) {
        if (this.socket && this.connected && taskId) {
            console.log(`Getting task status: ${taskId}`);
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
     * Show connection status in UI
     */
    showConnectionStatus(status, message = '') {
        const statusElement = document.getElementById('websocket-status');
        if (!statusElement) return;
        
        let statusClass = '';
        let statusIcon = '';
        let statusText = '';
        
        switch (status) {
            case 'connected':
                statusClass = 'text-success';
                statusIcon = 'bi-wifi';
                statusText = 'Connected';
                break;
            case 'disconnected':
                statusClass = 'text-warning';
                statusIcon = 'bi-wifi-off';
                statusText = 'Disconnected';
                break;
            case 'reconnecting':
                statusClass = 'text-info';
                statusIcon = 'bi-arrow-clockwise';
                statusText = 'Reconnecting';
                break;
            case 'suspended':
                statusClass = 'text-warning';
                statusIcon = 'bi-pause-circle';
                statusText = 'Suspended';
                break;
            case 'cors_error':
                statusClass = 'text-danger';
                statusIcon = 'bi-shield-x';
                statusText = 'CORS Error';
                break;
            case 'error':
                statusClass = 'text-danger';
                statusIcon = 'bi-exclamation-triangle';
                statusText = 'Connection Error';
                break;
            case 'failed':
                statusClass = 'text-danger';
                statusIcon = 'bi-x-circle';
                statusText = 'Connection Failed';
                break;
            case 'auth_required':
                statusClass = 'text-info';
                statusIcon = 'bi-shield-lock';
                statusText = 'Auth Required';
                break;
            case 'rate_limited':
                statusClass = 'text-warning';
                statusIcon = 'bi-hourglass-split';
                statusText = 'Rate Limited';
                break;
            default:
                statusClass = 'text-muted';
                statusIcon = 'bi-question-circle';
                statusText = 'Unknown';
        }
        
        statusElement.className = `${statusClass}`;
        statusElement.innerHTML = `<i class="bi ${statusIcon}"></i> ${statusText}`;
        
        if (message) {
            statusElement.title = message;
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
     * Disconnect WebSocket
     */
    disconnect() {
        if (this.socket) {
            console.log('Disconnecting WebSocket...');
            
            // Leave admin dashboard if connected
            if (this.isAdminPage()) {
                this.leaveAdminDashboard();
            }
            
            this.socket.disconnect();
            this.socket = null;
            this.connected = false;
        }
    }
    
    /**
     * Get connection status
     */
    isConnected() {
        return this.connected && this.socket && this.socket.connected;
    }
}

// Global WebSocket instance
window.VedfolnirWS = null;

// Initialize WebSocket when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if Socket.IO is available
    if (typeof io !== 'undefined') {
        console.log('Initializing Vedfolnir WebSocket client...');
        window.VedfolnirWS = new VedfolnirWebSocket();
        
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