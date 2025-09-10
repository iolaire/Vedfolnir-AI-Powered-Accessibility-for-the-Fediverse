// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Intelligent WebSocket Connection Recovery System
 * 
 * Provides comprehensive connection recovery with:
 * - Exponential backoff retry logic with configurable parameters
 * - Transport fallback mechanism (WebSocket to polling)
 * - Browser suspension detection and automatic polling mode switch
 * - Connection state management and restoration
 * - Intelligent reconnection timing based on error types
 */

class WebSocketConnectionRecovery {
    constructor(client, config = {}) {
        this.client = client;
        this.config = this._mergeConfig(config);
        this.state = this._initializeState();
        this.logger = console;
        
        // Bind methods to preserve context
        this._handleConnectionError = this._handleConnectionError.bind(this);
        this._handleDisconnection = this._handleDisconnection.bind(this);
        this._handleVisibilityChange = this._handleVisibilityChange.bind(this);
        
        this._setupEventListeners();
        this._startBrowserSuspensionDetection();
        
        this.logger.log('WebSocket Connection Recovery initialized');
    }
    
    /**
     * Merge user config with defaults
     */
    _mergeConfig(userConfig) {
        const defaults = {
            // Exponential backoff configuration
            initialDelay: 1000,           // 1 second initial delay
            maxDelay: 30000,              // 30 seconds maximum delay
            backoffMultiplier: 2,         // Double delay each attempt
            jitterFactor: 0.1,            // 10% random jitter
            
            // Retry configuration
            maxRetries: 10,               // Maximum retry attempts
            resetThreshold: 300000,       // 5 minutes to reset retry count
            
            // Transport fallback configuration
            enableTransportFallback: true,
            fallbackTransports: ['polling'],
            fallbackDelay: 5000,          // 5 seconds before fallback
            
            // Browser suspension detection
            enableSuspensionDetection: true,
            suspensionThreshold: 60000,   // 1 minute to detect suspension
            pollingModeTimeout: 300000,   // 5 minutes in polling mode
            
            // Error-specific delays
            errorDelays: {
                'cors': 10000,            // 10 seconds for CORS errors
                'timeout': 5000,          // 5 seconds for timeout errors
                'transport': 3000,        // 3 seconds for transport errors
                'auth': 30000,            // 30 seconds for auth errors
                'rate_limit': 60000,      // 1 minute for rate limit errors
                'server': 15000,          // 15 seconds for server errors
                'network': 8000,          // 8 seconds for network errors
                'unknown': 5000           // 5 seconds for unknown errors
            }
        };
        
        return { ...defaults, ...userConfig };
    }  
  
    /**
     * Initialize recovery state
     */
    _initializeState() {
        return {
            // Connection state
            isConnected: false,
            isRecovering: false,
            isSuspended: false,
            isPollingMode: false,
            
            // Retry tracking
            retryCount: 0,
            lastRetryTime: null,
            lastSuccessfulConnection: null,
            
            // Error tracking
            lastError: null,
            lastErrorType: null,
            consecutiveErrors: 0,
            errorHistory: [],
            
            // Transport tracking
            currentTransport: null,
            originalTransports: null,
            transportFallbackActive: false,
            
            // Suspension detection
            lastActivityTime: Date.now(),
            suspensionDetected: false,
            visibilityChangeTime: null,
            
            // Recovery timers
            retryTimer: null,
            suspensionTimer: null,
            pollingModeTimer: null,
            
            // Connection metrics
            connectionAttempts: 0,
            totalDowntime: 0,
            recoveryStartTime: null
        };
    }
    
    /**
     * Setup event listeners for recovery system
     */
    _setupEventListeners() {
        // Client connection events
        this.client.on('connect', () => {
            this._handleSuccessfulConnection();
        });
        
        this.client.on('disconnect', (reason) => {
            this._handleDisconnection(reason);
        });
        
        this.client.on('connect_error', (error) => {
            this._handleConnectionError(error);
        });
        
        this.client.on('reconnect_error', (error) => {
            this._handleConnectionError(error);
        });
        
        this.client.on('reconnect_failed', () => {
            this._handleReconnectFailed();
        });
        
        // Browser visibility events for suspension detection
        if (typeof document !== 'undefined') {
            document.addEventListener('visibilitychange', this._handleVisibilityChange);
        }
        
        // Network status events if available
        if (typeof navigator !== 'undefined' && 'onLine' in navigator) {
            window.addEventListener('online', () => {
                this._handleNetworkStatusChange(true);
            });
            
            window.addEventListener('offline', () => {
                this._handleNetworkStatusChange(false);
            });
        }
    }
    
    /**
     * Start browser suspension detection
     */
    _startBrowserSuspensionDetection() {
        if (!this.config.enableSuspensionDetection) return;
        
        // Periodic check for suspension
        this.state.suspensionTimer = setInterval(() => {
            this._checkForSuspension();
        }, 30000); // Check every 30 seconds
        
        // Update activity time on various events
        const updateActivity = () => {
            this.state.lastActivityTime = Date.now();
        };
        
        if (typeof document !== 'undefined') {
            ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
                document.addEventListener(event, updateActivity, { passive: true });
            });
        }
    }   
 
    /**
     * Handle successful connection
     */
    _handleSuccessfulConnection() {
        this.logger.log('✅ WebSocket connection successful');
        
        // Update state
        this.state.isConnected = true;
        this.state.isRecovering = false;
        this.state.lastSuccessfulConnection = Date.now();
        this.state.consecutiveErrors = 0;
        this.state.lastError = null;
        
        // Calculate recovery time if we were recovering
        if (this.state.recoveryStartTime) {
            const recoveryTime = Date.now() - this.state.recoveryStartTime;
            this.logger.log(`🔄 Recovery completed in ${recoveryTime}ms`);
            this.state.recoveryStartTime = null;
        }
        
        // Reset retry count after successful connection
        this._resetRetryCount();
        
        // Clear any active timers
        this._clearRecoveryTimers();
        
        // Exit polling mode if active
        if (this.state.isPollingMode) {
            this._exitPollingMode();
        }
        
        // Restore original transports if fallback was active
        if (this.state.transportFallbackActive) {
            this._restoreOriginalTransports();
        }
        
        // Emit recovery success event
        this._emitRecoveryEvent('recovery_success', {
            recoveryTime: this.state.recoveryStartTime ? Date.now() - this.state.recoveryStartTime : 0,
            retryCount: this.state.retryCount,
            transport: this._getCurrentTransport()
        });
    }
    
    /**
     * Handle disconnection
     */
    _handleDisconnection(reason) {
        this.logger.log(`❌ WebSocket disconnected: ${reason}`);
        
        this.state.isConnected = false;
        
        // Don't start recovery for intentional disconnections
        if (reason === 'io client disconnect' || reason === 'io server disconnect') {
            this.logger.log('Disconnection was intentional, not starting recovery');
            return;
        }
        
        // Start recovery process
        this._startRecovery('disconnect', reason);
    }
    
    /**
     * Handle connection errors
     */
    _handleConnectionError(error) {
        // Analyze error type first
        const errorType = this._analyzeError(error);
        
        // Only log errors that aren't common network issues or if it's the first few errors
        if (this.state.consecutiveErrors < 3 && 
            !error.message?.includes('NetworkError') &&
            !error.message?.includes('ERR_NETWORK') &&
            errorType !== 'network') {
            this.logger.warn('WebSocket connection issue:', error.message || error.toString());
        }
        
        // Update error tracking
        this.state.lastError = error;
        this.state.lastErrorType = errorType;
        this.state.consecutiveErrors++;
        this.state.errorHistory.push({
            error: error.message || error.toString(),
            type: errorType,
            timestamp: Date.now()
        });
        
        // Keep error history manageable
        if (this.state.errorHistory.length > 50) {
            this.state.errorHistory = this.state.errorHistory.slice(-25);
        }
        
        // Start recovery with error-specific handling
        this._startRecovery('error', error, errorType);
    }
    
    /**
     * Handle reconnect failed
     */
    _handleReconnectFailed() {
        this.logger.error('❌ WebSocket reconnection failed after maximum attempts');
        
        // Try transport fallback if available
        if (this.config.enableTransportFallback && !this.state.transportFallbackActive) {
            this._attemptTransportFallback();
        } else {
            // Emit recovery failure event
            this._emitRecoveryEvent('recovery_failed', {
                retryCount: this.state.retryCount,
                lastError: this.state.lastError,
                errorType: this.state.lastErrorType
            });
        }
    }    

    /**
     * Start recovery process
     */
    _startRecovery(trigger, details, errorType = null) {
        if (this.state.isRecovering) {
            this.logger.log('Recovery already in progress, updating details');
            return;
        }
        
        this.logger.log(`🔄 Starting recovery process (trigger: ${trigger})`);
        
        this.state.isRecovering = true;
        this.state.recoveryStartTime = Date.now();
        
        // Emit recovery start event
        this._emitRecoveryEvent('recovery_start', {
            trigger,
            details,
            errorType,
            retryCount: this.state.retryCount
        });
        
        // Calculate delay based on error type and retry count
        const delay = this._calculateRecoveryDelay(errorType);
        
        this.logger.log(`⏱️ Scheduling recovery attempt in ${delay}ms`);
        
        // Schedule recovery attempt
        this.state.retryTimer = setTimeout(() => {
            this._attemptRecovery(errorType);
        }, delay);
    }
    
    /**
     * Calculate recovery delay with exponential backoff and error-specific timing
     */
    _calculateRecoveryDelay(errorType) {
        let baseDelay;
        
        // Use error-specific delay if available
        if (errorType && this.config.errorDelays[errorType]) {
            baseDelay = this.config.errorDelays[errorType];
        } else {
            // Use exponential backoff
            baseDelay = Math.min(
                this.config.initialDelay * Math.pow(this.config.backoffMultiplier, this.state.retryCount),
                this.config.maxDelay
            );
        }
        
        // Add jitter to prevent thundering herd
        const jitter = baseDelay * this.config.jitterFactor * (Math.random() - 0.5);
        const finalDelay = Math.max(baseDelay + jitter, 1000); // Minimum 1 second
        
        return Math.floor(finalDelay);
    }
    
    /**
     * Attempt recovery
     */
    _attemptRecovery(errorType) {
        if (!this.state.isRecovering) {
            this.logger.log('Recovery cancelled');
            return;
        }
        
        this.state.retryCount++;
        this.state.lastRetryTime = Date.now();
        this.state.connectionAttempts++;
        
        this.logger.log(`🔄 Recovery attempt ${this.state.retryCount}/${this.config.maxRetries}`);
        
        // Check if we've exceeded maximum retries
        if (this.state.retryCount > this.config.maxRetries) {
            this.logger.error('❌ Maximum recovery attempts exceeded');
            this._handleRecoveryFailure();
            return;
        }
        
        // Emit recovery attempt event
        this._emitRecoveryEvent('recovery_attempt', {
            attemptNumber: this.state.retryCount,
            errorType,
            transport: this._getCurrentTransport()
        });
        
        // Handle specific error types
        if (errorType === 'cors' || errorType === 'transport') {
            this._attemptTransportFallback();
        } else if (errorType === 'timeout' || errorType === 'network') {
            this._attemptWithIncreasedTimeouts();
        } else {
            // Standard reconnection attempt
            this._attemptStandardReconnection();
        }
    }
    
    /**
     * Attempt transport fallback
     */
    _attemptTransportFallback() {
        if (!this.config.enableTransportFallback || this.state.transportFallbackActive) {
            this._attemptStandardReconnection();
            return;
        }
        
        this.logger.log('🔄 Attempting transport fallback to polling');
        
        // Store original transports
        if (!this.state.originalTransports) {
            this.state.originalTransports = this._getCurrentTransports();
        }
        
        // Switch to fallback transports
        this._switchTransports(this.config.fallbackTransports);
        this.state.transportFallbackActive = true;
        
        // Attempt connection with fallback transport
        setTimeout(() => {
            this._attemptStandardReconnection();
        }, this.config.fallbackDelay);
    }    
 
   /**
     * Attempt connection with increased timeouts
     */
    _attemptWithIncreasedTimeouts() {
        this.logger.log('🔄 Attempting reconnection with increased timeouts');
        
        // Increase client timeouts temporarily
        if (this.client.io && this.client.io.opts) {
            const originalTimeout = this.client.io.opts.timeout;
            this.client.io.opts.timeout = Math.min(originalTimeout * 2, 60000);
            
            // Restore original timeout after connection attempt
            setTimeout(() => {
                if (this.client.io && this.client.io.opts) {
                    this.client.io.opts.timeout = originalTimeout;
                }
            }, 30000);
        }
        
        this._attemptStandardReconnection();
    }
    
    /**
     * Attempt standard reconnection
     */
    _attemptStandardReconnection() {
        try {
            if (this.client.connected) {
                this.logger.log('Client already connected, skipping reconnection');
                this._handleSuccessfulConnection();
                return;
            }
            
            this.logger.log('🔌 Attempting to reconnect...');
            this.client.connect();
            
            // Set timeout for this connection attempt
            const attemptTimeout = setTimeout(() => {
                if (!this.state.isConnected && this.state.isRecovering) {
                    this.logger.warn('⏰ Connection attempt timed out');
                    this._startRecovery('timeout', 'Connection attempt timeout');
                }
            }, this.config.errorDelays.timeout || 10000);
            
            // Clear timeout on successful connection
            const clearTimeoutOnConnect = () => {
                clearTimeout(attemptTimeout);
                this.client.off('connect', clearTimeoutOnConnect);
            };
            this.client.on('connect', clearTimeoutOnConnect);
            
        } catch (error) {
            this.logger.error('❌ Error during reconnection attempt:', error);
            this._startRecovery('error', error);
        }
    }
    
    /**
     * Handle recovery failure
     */
    _handleRecoveryFailure() {
        this.logger.error('❌ Recovery failed after maximum attempts');
        
        this.state.isRecovering = false;
        this._clearRecoveryTimers();
        
        // Try entering polling mode as last resort
        if (this.config.enableSuspensionDetection && !this.state.isPollingMode) {
            this._enterPollingMode('recovery_failure');
        } else {
            // Emit final failure event
            this._emitRecoveryEvent('recovery_failed', {
                retryCount: this.state.retryCount,
                totalDowntime: Date.now() - (this.state.recoveryStartTime || Date.now()),
                lastError: this.state.lastError,
                errorType: this.state.lastErrorType
            });
        }
    }
    
    /**
     * Check for browser suspension
     */
    _checkForSuspension() {
        if (!this.config.enableSuspensionDetection) return;
        
        const now = Date.now();
        const timeSinceActivity = now - this.state.lastActivityTime;
        
        // Check if browser might be suspended
        if (timeSinceActivity > this.config.suspensionThreshold && 
            this.state.isConnected && 
            !this.state.suspensionDetected) {
            
            this.logger.warn('⏸️ Browser suspension detected');
            this.state.suspensionDetected = true;
            this._handleSuspensionDetected();
        }
    }
    
    /**
     * Handle browser suspension detection
     */
    _handleSuspensionDetected() {
        this.logger.log('🔄 Handling browser suspension');
        
        // Enter polling mode to maintain connection
        this._enterPollingMode('suspension_detected');
        
        // Emit suspension event
        this._emitRecoveryEvent('suspension_detected', {
            timeSinceActivity: Date.now() - this.state.lastActivityTime,
            transport: this._getCurrentTransport()
        });
    }
    
    /**
     * Handle visibility change (tab switching, minimizing)
     */
    _handleVisibilityChange() {
        if (typeof document === 'undefined') return;
        
        const now = Date.now();
        
        if (document.hidden) {
            this.logger.log('👁️ Page hidden, preparing for potential suspension');
            this.state.visibilityChangeTime = now;
        } else {
            this.logger.log('👁️ Page visible again');
            
            // Check if we were hidden for a long time
            if (this.state.visibilityChangeTime) {
                const hiddenDuration = now - this.state.visibilityChangeTime;
                
                if (hiddenDuration > this.config.suspensionThreshold) {
                    this.logger.log('⏸️ Long suspension detected via visibility change');
                    this._handleSuspensionDetected();
                }
                
                this.state.visibilityChangeTime = null;
            }
            
            // Update activity time
            this.state.lastActivityTime = now;
            this.state.suspensionDetected = false;
        }
    }  
  
    /**
     * Enter polling mode
     */
    _enterPollingMode(reason) {
        if (this.state.isPollingMode) return;
        
        this.logger.log(`🔄 Entering polling mode (reason: ${reason})`);
        
        this.state.isPollingMode = true;
        this.state.isSuspended = true;
        
        // Switch to polling transport
        this._switchTransports(['polling']);
        
        // Set timer to exit polling mode
        this.state.pollingModeTimer = setTimeout(() => {
            this._exitPollingMode();
        }, this.config.pollingModeTimeout);
        
        // Emit polling mode event
        this._emitRecoveryEvent('polling_mode_entered', {
            reason,
            timeout: this.config.pollingModeTimeout
        });
        
        // Attempt reconnection in polling mode
        if (!this.state.isConnected) {
            setTimeout(() => {
                this._attemptStandardReconnection();
            }, 2000);
        }
    }
    
    /**
     * Exit polling mode
     */
    _exitPollingMode() {
        if (!this.state.isPollingMode) return;
        
        this.logger.log('🔄 Exiting polling mode');
        
        this.state.isPollingMode = false;
        this.state.isSuspended = false;
        
        // Clear polling mode timer
        if (this.state.pollingModeTimer) {
            clearTimeout(this.state.pollingModeTimer);
            this.state.pollingModeTimer = null;
        }
        
        // Restore original transports
        this._restoreOriginalTransports();
        
        // Emit polling mode exit event
        this._emitRecoveryEvent('polling_mode_exited', {
            duration: this.config.pollingModeTimeout
        });
    }
    
    /**
     * Handle network status change
     */
    _handleNetworkStatusChange(isOnline) {
        this.logger.log(`🌐 Network status changed: ${isOnline ? 'online' : 'offline'}`);
        
        if (isOnline && !this.state.isConnected && !this.state.isRecovering) {
            this.logger.log('🔄 Network back online, attempting reconnection');
            this._startRecovery('network_online', 'Network connection restored');
        } else if (!isOnline) {
            this.logger.log('📡 Network offline, pausing recovery attempts');
            this._pauseRecovery();
        }
    }
    
    /**
     * Pause recovery attempts
     */
    _pauseRecovery() {
        if (this.state.retryTimer) {
            clearTimeout(this.state.retryTimer);
            this.state.retryTimer = null;
        }
        
        this.state.isRecovering = false;
        
        this._emitRecoveryEvent('recovery_paused', {
            reason: 'network_offline'
        });
    }
    
    /**
     * Reset retry count after successful connection or timeout
     */
    _resetRetryCount() {
        const now = Date.now();
        
        // Reset if enough time has passed since last retry
        if (this.state.lastRetryTime && 
            (now - this.state.lastRetryTime) > this.config.resetThreshold) {
            this.logger.log('🔄 Resetting retry count due to time threshold');
            this.state.retryCount = 0;
        }
        
        // Always reset on successful connection
        if (this.state.isConnected) {
            this.state.retryCount = 0;
        }
    }
    
    /**
     * Clear all recovery timers
     */
    _clearRecoveryTimers() {
        if (this.state.retryTimer) {
            clearTimeout(this.state.retryTimer);
            this.state.retryTimer = null;
        }
        
        if (this.state.pollingModeTimer) {
            clearTimeout(this.state.pollingModeTimer);
            this.state.pollingModeTimer = null;
        }
    }    
    
/**
     * Switch transports
     */
    _switchTransports(transports) {
        if (!this.client.io || !this.client.io.opts) return;
        
        this.logger.log(`🔄 Switching transports to: ${transports.join(', ')}`);
        
        this.client.io.opts.transports = transports;
        this.state.currentTransport = transports[0];
        
        // Force reconnection with new transports
        if (this.client.connected) {
            this.client.disconnect();
        }
    }
    
    /**
     * Restore original transports
     */
    _restoreOriginalTransports() {
        if (!this.state.originalTransports || !this.client.io || !this.client.io.opts) return;
        
        this.logger.log(`🔄 Restoring original transports: ${this.state.originalTransports.join(', ')}`);
        
        this.client.io.opts.transports = this.state.originalTransports;
        this.state.transportFallbackActive = false;
        this.state.currentTransport = this.state.originalTransports[0];
    }
    
    /**
     * Get current transport
     */
    _getCurrentTransport() {
        if (this.client.io && this.client.io.engine && this.client.io.engine.transport) {
            return this.client.io.engine.transport.name;
        }
        return this.state.currentTransport || 'unknown';
    }
    
    /**
     * Get current transports configuration
     */
    _getCurrentTransports() {
        if (this.client.io && this.client.io.opts && this.client.io.opts.transports) {
            return [...this.client.io.opts.transports];
        }
        return ['websocket', 'polling']; // Default fallback
    }
    
    /**
     * Analyze error to determine type
     */
    _analyzeError(error) {
        const message = (error.message || error.toString()).toLowerCase();
        
        if (message.includes('cors') || message.includes('cross-origin') || 
            message.includes('access-control')) {
            return 'cors';
        } else if (message.includes('timeout') || message.includes('timed out')) {
            return 'timeout';
        } else if (message.includes('transport') || message.includes('websocket') || 
                   message.includes('polling')) {
            return 'transport';
        } else if (message.includes('auth') || message.includes('unauthorized') || 
                   message.includes('forbidden')) {
            return 'auth';
        } else if (message.includes('rate') || message.includes('limit') || 
                   message.includes('throttle')) {
            return 'rate_limit';
        } else if (message.includes('server') || message.includes('5')) {
            return 'server';
        } else if (message.includes('network') || message.includes('connection') || 
                   message.includes('refused')) {
            return 'network';
        } else {
            return 'unknown';
        }
    }
    
    /**
     * Emit recovery event
     */
    _emitRecoveryEvent(eventType, data = {}) {
        const event = {
            type: eventType,
            timestamp: Date.now(),
            state: { ...this.state },
            data
        };
        
        // Emit to client if it supports custom events
        if (this.client.emit && typeof this.client.emit === 'function') {
            try {
                this.client.emit('recovery_event', event);
            } catch (error) {
                // Ignore emit errors during recovery
            }
        }
        
        // Emit to window for global listeners
        if (typeof window !== 'undefined' && window.dispatchEvent) {
            try {
                window.dispatchEvent(new CustomEvent('websocket_recovery', {
                    detail: event
                }));
            } catch (error) {
                // Ignore event dispatch errors
            }
        }
        
        this.logger.log(`📡 Recovery event: ${eventType}`, data);
    }   
 
    /**
     * Get recovery statistics
     */
    getRecoveryStats() {
        return {
            // Connection state
            isConnected: this.state.isConnected,
            isRecovering: this.state.isRecovering,
            isSuspended: this.state.isSuspended,
            isPollingMode: this.state.isPollingMode,
            
            // Retry statistics
            retryCount: this.state.retryCount,
            maxRetries: this.config.maxRetries,
            connectionAttempts: this.state.connectionAttempts,
            
            // Error statistics
            consecutiveErrors: this.state.consecutiveErrors,
            lastErrorType: this.state.lastErrorType,
            errorHistoryCount: this.state.errorHistory.length,
            
            // Transport information
            currentTransport: this._getCurrentTransport(),
            transportFallbackActive: this.state.transportFallbackActive,
            originalTransports: this.state.originalTransports,
            
            // Timing information
            lastSuccessfulConnection: this.state.lastSuccessfulConnection,
            lastRetryTime: this.state.lastRetryTime,
            recoveryStartTime: this.state.recoveryStartTime,
            
            // Suspension detection
            suspensionDetected: this.state.suspensionDetected,
            lastActivityTime: this.state.lastActivityTime,
            
            // Configuration
            config: { ...this.config }
        };
    }
    
    /**
     * Force recovery attempt
     */
    forceRecovery() {
        this.logger.log('🔄 Forcing recovery attempt');
        
        // Clear existing recovery state
        this._clearRecoveryTimers();
        this.state.isRecovering = false;
        
        // Reset retry count for fresh start
        this.state.retryCount = 0;
        
        // Start immediate recovery
        this._startRecovery('manual', 'Manual recovery triggered');
    }
    
    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        this.config = this._mergeConfig(newConfig);
        this.logger.log('🔧 Recovery configuration updated');
    }
    
    /**
     * Destroy recovery system
     */
    destroy() {
        this.logger.log('🗑️ Destroying WebSocket recovery system');
        
        // Clear all timers
        this._clearRecoveryTimers();
        
        if (this.state.suspensionTimer) {
            clearInterval(this.state.suspensionTimer);
            this.state.suspensionTimer = null;
        }
        
        // Remove event listeners
        if (typeof document !== 'undefined') {
            document.removeEventListener('visibilitychange', this._handleVisibilityChange);
        }
        
        if (typeof window !== 'undefined') {
            window.removeEventListener('online', this._handleNetworkStatusChange);
            window.removeEventListener('offline', this._handleNetworkStatusChange);
        }
        
        // Reset state
        this.state.isRecovering = false;
        this.state.isPollingMode = false;
        this.state.transportFallbackActive = false;
        
        // Restore original transports if needed
        this._restoreOriginalTransports();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketConnectionRecovery;
} else if (typeof window !== 'undefined') {
    window.WebSocketConnectionRecovery = WebSocketConnectionRecovery;
}