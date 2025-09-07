// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * WebSocket Connection Status Component
 * 
 * Provides visual connection status indicators with retry options and user feedback.
 * Integrates with the enhanced error handler to provide comprehensive status information.
 */

class WebSocketConnectionStatus {
    constructor(client, errorHandler, options = {}) {
        this.client = client;
        this.errorHandler = errorHandler;
        this.options = this._mergeOptions(options);
        
        // Status state
        this.status = {
            current: 'initializing',
            lastUpdate: Date.now(),
            connectionQuality: 'unknown',
            latency: null,
            uptime: 0,
            reconnectCount: 0
        };
        
        // UI elements
        this.elements = {
            statusBar: null,
            statusIcon: null,
            statusText: null,
            qualityIndicator: null,
            retryButton: null,
            detailsPanel: null
        };
        
        // Initialize component
        this._initialize();
    }
    
    /**
     * Merge options with defaults
     */
    _mergeOptions(userOptions) {
        const defaults = {
            // Display options
            showStatusBar: true,
            showQualityIndicator: true,
            showRetryButton: true,
            showDetailsPanel: false,
            
            // Position and styling
            position: 'top-right',
            theme: 'auto', // auto, light, dark
            size: 'normal', // compact, normal, large
            
            // Behavior options
            autoHide: false,
            autoHideDelay: 5000,
            enableAnimations: true,
            enableSounds: false,
            
            // Quality monitoring
            enableQualityMonitoring: true,
            latencyThresholds: {
                excellent: 50,
                good: 150,
                fair: 300,
                poor: 500
            },
            
            // Retry options
            enableManualRetry: true,
            showRetryCount: true,
            maxRetryAttempts: 5
        };
        
        return { ...defaults, ...userOptions };
    }
}    
  
  /**
     * Initialize the connection status component
     */
    _initialize() {
        this._createStatusBar();
        this._setupEventListeners();
        this._startQualityMonitoring();
        
        console.log('WebSocket Connection Status component initialized');
    }
    
    /**
     * Create the main status bar
     */
    _createStatusBar() {
        if (!this.options.showStatusBar) return;
        
        // Create status bar container
        const statusBar = document.createElement('div');
        statusBar.id = 'websocket-status-bar';
        statusBar.className = `websocket-status-bar ${this.options.position} ${this.options.size}`;
        
        // Create status content
        statusBar.innerHTML = `
            <div class="status-content">
                <div class="status-main">
                    <i class="status-icon bi bi-hourglass-split"></i>
                    <span class="status-text">Initializing...</span>
                    <div class="quality-indicator ${this.options.showQualityIndicator ? '' : 'hidden'}">
                        <div class="quality-bars">
                            <div class="quality-bar"></div>
                            <div class="quality-bar"></div>
                            <div class="quality-bar"></div>
                            <div class="quality-bar"></div>
                        </div>
                    </div>
                </div>
                <div class="status-actions">
                    <button type="button" class="retry-button btn btn-sm btn-outline-secondary" 
                            class="hidden" 
                            title="Retry connection">
                        <i class="bi bi-arrow-clockwise"></i>
                        <span class="retry-text">Retry</span>
                    </button>
                    <button type="button" class="details-toggle btn btn-sm btn-outline-secondary" 
                            title="Show connection details">
                        <i class="bi bi-info-circle"></i>
                    </button>
                </div>
            </div>
            <div class="details-panel hidden">
                <div class="detail-row">
                    <span class="detail-label">Status:</span>
                    <span class="detail-value status-detail">Initializing</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Latency:</span>
                    <span class="detail-value latency-detail">-</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Uptime:</span>
                    <span class="detail-value uptime-detail">-</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Transport:</span>
                    <span class="detail-value transport-detail">-</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Reconnects:</span>
                    <span class="detail-value reconnect-detail">0</span>
                </div>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(statusBar);
        
        // Store element references
        this.elements.statusBar = statusBar;
        this.elements.statusIcon = statusBar.querySelector('.status-icon');
        this.elements.statusText = statusBar.querySelector('.status-text');
        this.elements.qualityIndicator = statusBar.querySelector('.quality-indicator');
        this.elements.retryButton = statusBar.querySelector('.retry-button');
        this.elements.detailsPanel = statusBar.querySelector('.details-panel');
        
        // Add CSS
        this._addStatusBarCSS();
        
        // Setup interactions
        this._setupStatusBarInteractions();
    }
    
    /**
     * Setup event listeners
     */
    _setupEventListeners() {
        // Client connection events
        this.client.on('connect', () => {
            this._updateStatus('connected', 'Connected');
            this._startUptimeTracking();
        });
        
        this.client.on('disconnect', (reason) => {
            this._updateStatus('disconnected', `Disconnected: ${reason}`);
            this._stopUptimeTracking();
        });
        
        this.client.on('connect_error', (error) => {
            this._updateStatus('error', 'Connection failed');
            this._showRetryButton();
        });
        
        this.client.on('reconnect', (attemptNumber) => {
            this.status.reconnectCount++;
            this._updateStatus('connected', 'Reconnected');
            this._updateDetailsPanel();
        });
        
        this.client.on('reconnect_attempt', (attemptNumber) => {
            this._updateStatus('reconnecting', `Reconnecting... (${attemptNumber})`);
        });
        
        this.client.on('reconnect_failed', () => {
            this._updateStatus('failed', 'Connection failed');
            this._showRetryButton();
        });
        
        // Error handler events
        if (this.errorHandler) {
            // Listen for error handler status updates
            window.addEventListener('websocketStatusChange', (event) => {
                const { status, message } = event.detail;
                this._updateStatus(status, message);
            });
        }
        
        // Latency monitoring
        this.client.on('pong', (latency) => {
            this.status.latency = latency;
            this._updateConnectionQuality();
            this._updateDetailsPanel();
        });
    }
    
    /**
     * Setup status bar interactions
     */
    _setupStatusBarInteractions() {
        if (!this.elements.statusBar) return;
        
        // Retry button
        if (this.elements.retryButton) {
            this.elements.retryButton.addEventListener('click', () => {
                this._handleRetryClick();
            });
        }
        
        // Details toggle
        const detailsToggle = this.elements.statusBar.querySelector('.details-toggle');
        if (detailsToggle) {
            detailsToggle.addEventListener('click', () => {
                this._toggleDetailsPanel();
            });
        }
        
        // Auto-hide functionality
        if (this.options.autoHide) {
            let hideTimeout;
            
            this.elements.statusBar.addEventListener('mouseenter', () => {
                clearTimeout(hideTimeout);
                this.elements.statusBar.style.opacity = '1';
            });
            
            this.elements.statusBar.addEventListener('mouseleave', () => {
                if (this.status.current === 'connected') {
                    hideTimeout = setTimeout(() => {
                        this.elements.statusBar.style.opacity = '0.3';
                    }, this.options.autoHideDelay);
                }
            });
        }
    }
    
    /**
     * Update connection status
     */
    _updateStatus(status, message) {
        this.status.current = status;
        this.status.lastUpdate = Date.now();
        
        if (this.elements.statusText) {
            this.elements.statusText.textContent = message;
        }
        
        if (this.elements.statusIcon) {
            this._updateStatusIcon(status);
        }
        
        if (this.elements.statusBar) {
            this._updateStatusBarClass(status);
        }
        
        // Update details panel
        this._updateDetailsPanel();
        
        // Handle retry button visibility
        this._updateRetryButtonVisibility(status);
        
        // Play sound if enabled
        if (this.options.enableSounds) {
            this._playStatusSound(status);
        }
        
        // Trigger animations if enabled
        if (this.options.enableAnimations) {
            this._triggerStatusAnimation(status);
        }
    }
    
    /**
     * Update status icon
     */
    _updateStatusIcon(status) {
        const iconMap = {
            initializing: 'bi-hourglass-split',
            connected: 'bi-wifi',
            disconnected: 'bi-wifi-off',
            reconnecting: 'bi-arrow-clockwise',
            error: 'bi-exclamation-triangle',
            failed: 'bi-x-circle',
            'cors-error': 'bi-shield-exclamation',
            'auth-error': 'bi-person-lock'
        };
        
        const icon = iconMap[status] || 'bi-question-circle';
        this.elements.statusIcon.className = `status-icon bi ${icon}`;
        
        // Add spinning animation for reconnecting
        if (status === 'reconnecting') {
            this.elements.statusIcon.classList.add('spinning');
        } else {
            this.elements.statusIcon.classList.remove('spinning');
        }
    }
    
    /**
     * Update status bar CSS class
     */
    _updateStatusBarClass(status) {
        // Remove existing status classes
        this.elements.statusBar.classList.remove(
            'status-connected', 'status-disconnected', 'status-error', 
            'status-reconnecting', 'status-failed', 'status-initializing'
        );
        
        // Add new status class
        this.elements.statusBar.classList.add(`status-${status}`);
    }
    
    /**
     * Update retry button visibility
     */
    _updateRetryButtonVisibility(status) {
        if (!this.elements.retryButton || !this.options.showRetryButton) return;
        
        const showRetry = ['error', 'failed', 'disconnected'].includes(status);
        this.elements.retryButton.style.display = showRetry ? 'inline-flex' : 'none';
        
        // Update retry count if showing
        if (showRetry && this.options.showRetryCount) {
            const retryText = this.elements.retryButton.querySelector('.retry-text');
            if (retryText && this.status.reconnectCount > 0) {
                retryText.textContent = `Retry (${this.status.reconnectCount})`;
            }
        }
    }
    
    /**
     * Show retry button
     */
    _showRetryButton() {
        if (this.elements.retryButton && this.options.enableManualRetry) {
            this.elements.retryButton.style.display = 'inline-flex';
        }
    }
    
    /**
     * Handle retry button click
     */
    _handleRetryClick() {
        if (this.status.reconnectCount >= this.options.maxRetryAttempts) {
            this._showMaxRetriesMessage();
            return;
        }
        
        this._updateStatus('reconnecting', 'Retrying connection...');
        
        // Attempt reconnection
        try {
            this.client.connect();
        } catch (error) {
            console.error('Manual retry failed:', error);
            this._updateStatus('error', 'Retry failed');
        }
    }
    
    /**
     * Show max retries reached message
     */
    _showMaxRetriesMessage() {
        if (this.errorHandler && this.errorHandler._showNotification) {
            this.errorHandler._showNotification(
                `Maximum retry attempts (${this.options.maxRetryAttempts}) reached. Please refresh the page.`,
                'warning'
            );
        } else {
            alert(`Maximum retry attempts reached. Please refresh the page.`);
        }
    }
    
    /**
     * Toggle details panel
     */
    _toggleDetailsPanel() {
        if (!this.elements.detailsPanel) return;
        
        const isVisible = this.elements.detailsPanel.style.display !== 'none';
        this.elements.detailsPanel.style.display = isVisible ? 'none' : 'block';
        
        // Update toggle button icon
        const toggleButton = this.elements.statusBar.querySelector('.details-toggle i');
        if (toggleButton) {
            toggleButton.className = isVisible ? 'bi bi-info-circle' : 'bi bi-x-circle';
        }
    }
    
    /**
     * Update details panel
     */
    _updateDetailsPanel() {
        if (!this.elements.detailsPanel) return;
        
        // Status detail
        const statusDetail = this.elements.detailsPanel.querySelector('.status-detail');
        if (statusDetail) {
            statusDetail.textContent = this.status.current;
        }
        
        // Latency detail
        const latencyDetail = this.elements.detailsPanel.querySelector('.latency-detail');
        if (latencyDetail) {
            latencyDetail.textContent = this.status.latency ? `${this.status.latency}ms` : '-';
        }
        
        // Uptime detail
        const uptimeDetail = this.elements.detailsPanel.querySelector('.uptime-detail');
        if (uptimeDetail) {
            uptimeDetail.textContent = this._formatUptime();
        }
        
        // Transport detail
        const transportDetail = this.elements.detailsPanel.querySelector('.transport-detail');
        if (transportDetail) {
            transportDetail.textContent = this._getCurrentTransport();
        }
        
        // Reconnect detail
        const reconnectDetail = this.elements.detailsPanel.querySelector('.reconnect-detail');
        if (reconnectDetail) {
            reconnectDetail.textContent = this.status.reconnectCount.toString();
        }
    }
    
    /**
     * Start quality monitoring
     */
    _startQualityMonitoring() {
        if (!this.options.enableQualityMonitoring) return;
        
        // Send periodic pings to measure latency
        this.qualityInterval = setInterval(() => {
            if (this.client.connected) {
                const startTime = Date.now();
                this.client.emit('ping', startTime);
            }
        }, 5000); // Every 5 seconds
    }
    
    /**
     * Update connection quality indicator
     */
    _updateConnectionQuality() {
        if (!this.options.showQualityIndicator || !this.elements.qualityIndicator) return;
        
        const latency = this.status.latency;
        if (latency === null) return;
        
        let quality = 'poor';
        let bars = 1;
        
        if (latency <= this.options.latencyThresholds.excellent) {
            quality = 'excellent';
            bars = 4;
        } else if (latency <= this.options.latencyThresholds.good) {
            quality = 'good';
            bars = 3;
        } else if (latency <= this.options.latencyThresholds.fair) {
            quality = 'fair';
            bars = 2;
        }
        
        this.status.connectionQuality = quality;
        
        // Update quality bars
        const qualityBars = this.elements.qualityIndicator.querySelectorAll('.quality-bar');
        qualityBars.forEach((bar, index) => {
            bar.classList.toggle('active', index < bars);
            bar.classList.remove('excellent', 'good', 'fair', 'poor');
            if (index < bars) {
                bar.classList.add(quality);
            }
        });
    }
    
    /**
     * Start uptime tracking
     */
    _startUptimeTracking() {
        this.uptimeStart = Date.now();
        
        this.uptimeInterval = setInterval(() => {
            this.status.uptime = Date.now() - this.uptimeStart;
            this._updateDetailsPanel();
        }, 1000);
    }
    
    /**
     * Stop uptime tracking
     */
    _stopUptimeTracking() {
        if (this.uptimeInterval) {
            clearInterval(this.uptimeInterval);
            this.uptimeInterval = null;
        }
        this.status.uptime = 0;
    }
    
    /**
     * Format uptime for display
     */
    _formatUptime() {
        if (!this.status.uptime) return '-';
        
        const seconds = Math.floor(this.status.uptime / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }
    
    /**
     * Get current transport method
     */
    _getCurrentTransport() {
        if (this.client.io && this.client.io.engine && this.client.io.engine.transport) {
            return this.client.io.engine.transport.name;
        }
        return 'unknown';
    }
    
    /**
     * Play status sound
     */
    _playStatusSound(status) {
        // Simple beep sounds for different statuses
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        const frequencies = {
            connected: 800,
            disconnected: 400,
            error: 200
        };
        
        const frequency = frequencies[status];
        if (!frequency) return;
        
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
    }
    
    /**
     * Trigger status animation
     */
    _triggerStatusAnimation(status) {
        if (!this.elements.statusBar) return;
        
        // Add animation class
        this.elements.statusBar.classList.add('status-change-animation');
        
        // Remove animation class after animation completes
        setTimeout(() => {
            this.elements.statusBar.classList.remove('status-change-animation');
        }, 300);
    }
    
    /**
     * Add status bar CSS
     */
    _addStatusBarCSS() {
        if (document.getElementById('websocket-status-bar-css')) return;
        
        const css = `
            .websocket-status-bar {
                position: fixed;
                z-index: 1055;
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 0.5rem;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                backdrop-filter: blur(10px);
                font-size: 0.875rem;
                min-width: 200px;
                max-width: 400px;
                transition: all 0.3s ease;
            }
            
            .websocket-status-bar.top-right {
                top: 1rem;
                right: 1rem;
            }
            
            .websocket-status-bar.top-left {
                top: 1rem;
                left: 1rem;
            }
            
            .websocket-status-bar.bottom-right {
                bottom: 1rem;
                right: 1rem;
            }
            
            .websocket-status-bar.bottom-left {
                bottom: 1rem;
                left: 1rem;
            }
            
            .websocket-status-bar.compact {
                font-size: 0.75rem;
                min-width: 150px;
            }
            
            .websocket-status-bar.large {
                font-size: 1rem;
                min-width: 250px;
            }
            
            .status-content {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0.75rem;
            }
            
            .status-main {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                flex: 1;
            }
            
            .status-icon {
                font-size: 1.1em;
                transition: all 0.3s ease;
            }
            
            .status-icon.spinning {
                animation: spin 1s linear infinite;
            }
            
            .status-text {
                font-weight: 500;
            }
            
            .quality-indicator {
                margin-left: 0.5rem;
            }
            
            .quality-bars {
                display: flex;
                gap: 2px;
                align-items: end;
            }
            
            .quality-bar {
                width: 3px;
                background: #dee2e6;
                border-radius: 1px;
                transition: all 0.3s ease;
            }
            
            .quality-bar:nth-child(1) { height: 6px; }
            .quality-bar:nth-child(2) { height: 9px; }
            .quality-bar:nth-child(3) { height: 12px; }
            .quality-bar:nth-child(4) { height: 15px; }
            
            .quality-bar.active.excellent { background: #198754; }
            .quality-bar.active.good { background: #20c997; }
            .quality-bar.active.fair { background: #ffc107; }
            .quality-bar.active.poor { background: #dc3545; }
            
            .status-actions {
                display: flex;
                gap: 0.25rem;
                margin-left: 0.5rem;
            }
            
            .status-actions .btn {
                padding: 0.25rem 0.5rem;
                font-size: 0.75rem;
                border-radius: 0.25rem;
            }
            
            .details-panel {
                border-top: 1px solid rgba(0, 0, 0, 0.1);
                padding: 0.75rem;
                background: rgba(248, 249, 250, 0.8);
            }
            
            .detail-row {
                display: flex;
                justify-content: space-between;
                margin-bottom: 0.25rem;
            }
            
            .detail-row:last-child {
                margin-bottom: 0;
            }
            
            .detail-label {
                font-weight: 500;
                color: #6c757d;
            }
            
            .detail-value {
                font-family: monospace;
                font-size: 0.8em;
            }
            
            /* Status-specific styling */
            .websocket-status-bar.status-connected {
                border-color: rgba(25, 135, 84, 0.3);
                background: rgba(25, 135, 84, 0.05);
            }
            
            .websocket-status-bar.status-connected .status-icon {
                color: #198754;
            }
            
            .websocket-status-bar.status-error,
            .websocket-status-bar.status-failed {
                border-color: rgba(220, 53, 69, 0.3);
                background: rgba(220, 53, 69, 0.05);
            }
            
            .websocket-status-bar.status-error .status-icon,
            .websocket-status-bar.status-failed .status-icon {
                color: #dc3545;
            }
            
            .websocket-status-bar.status-reconnecting {
                border-color: rgba(13, 110, 253, 0.3);
                background: rgba(13, 110, 253, 0.05);
            }
            
            .websocket-status-bar.status-reconnecting .status-icon {
                color: #0d6efd;
            }
            
            .websocket-status-bar.status-disconnected {
                border-color: rgba(253, 126, 20, 0.3);
                background: rgba(253, 126, 20, 0.05);
            }
            
            .websocket-status-bar.status-disconnected .status-icon {
                color: #fd7e14;
            }
            
            /* Animations */
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            
            .status-change-animation {
                animation: statusPulse 0.3s ease-out;
            }
            
            @keyframes statusPulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            /* Dark theme */
            @media (prefers-color-scheme: dark) {
                .websocket-status-bar {
                    background: rgba(33, 37, 41, 0.95);
                    border-color: rgba(255, 255, 255, 0.1);
                    color: #fff;
                }
                
                .details-panel {
                    background: rgba(52, 58, 64, 0.8);
                    border-color: rgba(255, 255, 255, 0.1);
                }
                
                .detail-label {
                    color: #adb5bd;
                }
            }
            
            /* Mobile responsiveness */
            @media (max-width: 768px) {
                .websocket-status-bar {
                    min-width: 150px;
                    max-width: 250px;
                    font-size: 0.75rem;
                }
                
                .status-content {
                    padding: 0.5rem;
                }
                
                .status-actions .btn {
                    padding: 0.125rem 0.25rem;
                    font-size: 0.7rem;
                }
                
                .quality-indicator {
                    display: none;
                }
            }
        `;
        
        const style = document.createElement('style');
        style.id = 'websocket-status-bar-css';
        style.textContent = css;
        document.head.appendChild(style);
    }
    
    /**
     * Get connection statistics
     */
    getConnectionStats() {
        return {
            status: this.status.current,
            quality: this.status.connectionQuality,
            latency: this.status.latency,
            uptime: this.status.uptime,
            reconnectCount: this.status.reconnectCount,
            lastUpdate: this.status.lastUpdate,
            transport: this._getCurrentTransport()
        };
    }
    
    /**
     * Update configuration
     */
    updateOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
        
        // Re-apply options that affect UI
        if (this.elements.statusBar) {
            this.elements.statusBar.className = `websocket-status-bar ${this.options.position} ${this.options.size}`;
        }
        
        if (this.elements.qualityIndicator) {
            this.elements.qualityIndicator.style.display = this.options.showQualityIndicator ? 'block' : 'none';
        }
        
        if (this.elements.retryButton) {
            this.elements.retryButton.style.display = this.options.showRetryButton ? 'inline-flex' : 'none';
        }
    }
    
    /**
     * Show status bar
     */
    show() {
        if (this.elements.statusBar) {
            this.elements.statusBar.style.display = 'block';
        }
    }
    
    /**
     * Hide status bar
     */
    hide() {
        if (this.elements.statusBar) {
            this.elements.statusBar.style.display = 'none';
        }
    }
    
    /**
     * Destroy the component
     */
    destroy() {
        // Clear intervals
        if (this.qualityInterval) {
            clearInterval(this.qualityInterval);
        }
        
        if (this.uptimeInterval) {
            clearInterval(this.uptimeInterval);
        }
        
        // Remove event listeners
        if (this.client) {
            this.client.off('connect');
            this.client.off('disconnect');
            this.client.off('connect_error');
            this.client.off('reconnect');
            this.client.off('reconnect_attempt');
            this.client.off('reconnect_failed');
            this.client.off('pong');
        }
        
        // Remove UI elements
        if (this.elements.statusBar && this.elements.statusBar.parentNode) {
            this.elements.statusBar.parentNode.removeChild(this.elements.statusBar);
        }
        
        // Remove CSS
        const css = document.getElementById('websocket-status-bar-css');
        if (css) {
            css.remove();
        }
        
        console.log('WebSocket Connection Status component destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketConnectionStatus;
} else if (typeof window !== 'undefined') {
    window.WebSocketConnectionStatus = WebSocketConnectionStatus;
}