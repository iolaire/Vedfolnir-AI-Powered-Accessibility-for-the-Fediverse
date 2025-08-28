// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * WebSocket Debug Diagnostics System
 * 
 * Provides comprehensive debugging and diagnostic capabilities for WebSocket connections,
 * including detailed connection diagnostics, performance metrics, and troubleshooting tools.
 */

class WebSocketDebugDiagnostics {
    constructor(client, errorHandler, options = {}) {
        this.client = client;
        this.errorHandler = errorHandler;
        this.options = this._mergeOptions(options);
        
        // Diagnostic state
        this.diagnostics = {
            connectionHistory: [],
            performanceMetrics: {
                latencyHistory: [],
                throughputHistory: [],
                errorRateHistory: []
            },
            networkInfo: {},
            browserInfo: {},
            serverInfo: {},
            troubleshootingData: {}
        };
        
        // Debug UI elements
        this.ui = {
            panel: null,
            console: null,
            metricsChart: null,
            exportButton: null
        };
        
        // Initialize diagnostics
        this._initialize();
    }
    
    /**
     * Merge options with defaults
     */
    _mergeOptions(userOptions) {
        const defaults = {
            // Debug panel options
            showDebugPanel: false,
            panelPosition: 'bottom-right',
            panelSize: 'normal', // compact, normal, large
            
            // Data collection options
            collectPerformanceMetrics: true,
            collectNetworkInfo: true,
            collectBrowserInfo: true,
            maxHistorySize: 1000,
            
            // Monitoring options
            enableRealTimeMonitoring: true,
            monitoringInterval: 5000,
            latencyTestInterval: 10000,
            
            // Export options
            enableDataExport: true,
            exportFormats: ['json', 'csv', 'txt'],
            
            // Troubleshooting options
            enableAutoDiagnostics: true,
            enableSuggestions: true,
            
            // UI options
            enableCharts: true,
            chartUpdateInterval: 2000,
            maxChartDataPoints: 50
        };
        
        return { ...defaults, ...userOptions };
    }
}    
 
   /**
     * Initialize diagnostics system
     */
    _initialize() {
        // Collect initial system information
        this._collectBrowserInfo();
        this._collectNetworkInfo();
        
        // Setup event listeners
        this._setupEventListeners();
        
        // Start monitoring if enabled
        if (this.options.enableRealTimeMonitoring) {
            this._startMonitoring();
        }
        
        // Create debug panel if requested
        if (this.options.showDebugPanel) {
            this._createDebugPanel();
        }
        
        console.log('WebSocket Debug Diagnostics initialized');
    }
    
    /**
     * Collect browser information
     */
    _collectBrowserInfo() {
        this.diagnostics.browserInfo = {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            
            // Browser capabilities
            webSocketSupport: 'WebSocket' in window,
            socketIOSupport: typeof io !== 'undefined',
            
            // Screen information
            screen: {
                width: screen.width,
                height: screen.height,
                colorDepth: screen.colorDepth
            },
            
            // Viewport information
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            
            // Connection information
            connection: this._getConnectionInfo(),
            
            // Performance information
            performance: this._getPerformanceInfo(),
            
            // Local storage support
            localStorage: this._testLocalStorage(),
            sessionStorage: this._testSessionStorage(),
            
            // Date and timezone
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * Collect network information
     */
    _collectNetworkInfo() {
        this.diagnostics.networkInfo = {
            // Current URL information
            url: {
                protocol: window.location.protocol,
                hostname: window.location.hostname,
                port: window.location.port,
                pathname: window.location.pathname,
                search: window.location.search,
                hash: window.location.hash
            },
            
            // Referrer information
            referrer: document.referrer,
            
            // Network connection (if available)
            connection: this._getNetworkConnection(),
            
            // DNS and connectivity tests
            dnsResolution: null, // Will be populated by tests
            connectivity: null,  // Will be populated by tests
            
            timestamp: new Date().toISOString()
        };
        
        // Run network tests
        this._runNetworkTests();
    }
    
    /**
     * Setup event listeners for diagnostics
     */
    _setupEventListeners() {
        // Client connection events
        this.client.on('connect', () => {
            this._recordConnectionEvent('connect', { timestamp: Date.now() });
            this._collectServerInfo();
        });
        
        this.client.on('disconnect', (reason) => {
            this._recordConnectionEvent('disconnect', { 
                reason, 
                timestamp: Date.now() 
            });
        });
        
        this.client.on('connect_error', (error) => {
            this._recordConnectionEvent('connect_error', {
                error: error.message || error.toString(),
                stack: error.stack,
                timestamp: Date.now()
            });
            
            this._runTroubleshootingDiagnostics(error);
        });
        
        this.client.on('reconnect', (attemptNumber) => {
            this._recordConnectionEvent('reconnect', {
                attemptNumber,
                timestamp: Date.now()
            });
        });
        
        // Performance monitoring
        this.client.on('pong', (latency) => {
            this._recordPerformanceMetric('latency', latency);
        });
        
        // Error handler events
        if (this.errorHandler) {
            // Monitor error handler events
            window.addEventListener('websocket_recovery', (event) => {
                this._recordConnectionEvent('recovery_event', event.detail);
            });
        }
        
        // Browser events
        window.addEventListener('online', () => {
            this._recordConnectionEvent('network_online', { timestamp: Date.now() });
        });
        
        window.addEventListener('offline', () => {
            this._recordConnectionEvent('network_offline', { timestamp: Date.now() });
        });
        
        // Visibility change events
        document.addEventListener('visibilitychange', () => {
            this._recordConnectionEvent('visibility_change', {
                hidden: document.hidden,
                timestamp: Date.now()
            });
        });
    }
    
    /**
     * Start real-time monitoring
     */
    _startMonitoring() {
        // Performance monitoring
        this.monitoringInterval = setInterval(() => {
            this._collectPerformanceSnapshot();
        }, this.options.monitoringInterval);
        
        // Latency testing
        this.latencyInterval = setInterval(() => {
            this._performLatencyTest();
        }, this.options.latencyTestInterval);
        
        // Chart updates
        if (this.options.enableCharts && this.ui.panel) {
            this.chartInterval = setInterval(() => {
                this._updateCharts();
            }, this.options.chartUpdateInterval);
        }
    }
    
    /**
     * Record connection event
     */
    _recordConnectionEvent(type, data) {
        const event = {
            type,
            data,
            timestamp: Date.now(),
            id: this._generateEventId()
        };
        
        this.diagnostics.connectionHistory.push(event);
        
        // Limit history size
        if (this.diagnostics.connectionHistory.length > this.options.maxHistorySize) {
            this.diagnostics.connectionHistory.shift();
        }
        
        // Update debug panel if visible
        if (this.ui.panel && this.ui.panel.style.display !== 'none') {
            this._updateDebugPanel();
        }
    }
    
    /**
     * Record performance metric
     */
    _recordPerformanceMetric(type, value) {
        const metric = {
            type,
            value,
            timestamp: Date.now()
        };
        
        if (!this.diagnostics.performanceMetrics[`${type}History`]) {
            this.diagnostics.performanceMetrics[`${type}History`] = [];
        }
        
        this.diagnostics.performanceMetrics[`${type}History`].push(metric);
        
        // Limit history size
        const history = this.diagnostics.performanceMetrics[`${type}History`];
        if (history.length > this.options.maxHistorySize) {
            history.shift();
        }
    }
    
    /**
     * Collect server information
     */
    _collectServerInfo() {
        if (!this.client.connected) return;
        
        // Request server info
        this.client.emit('debug_info_request', (response) => {
            if (response) {
                this.diagnostics.serverInfo = {
                    ...response,
                    timestamp: Date.now()
                };
            }
        });
        
        // Collect transport information
        this.diagnostics.serverInfo.transport = {
            name: this._getCurrentTransport(),
            upgrades: this._getAvailableUpgrades(),
            timestamp: Date.now()
        };
    }
    
    /**
     * Run troubleshooting diagnostics
     */
    _runTroubleshootingDiagnostics(error) {
        if (!this.options.enableAutoDiagnostics) return;
        
        const diagnostics = {
            error: {
                message: error.message || error.toString(),
                type: this._categorizeError(error),
                stack: error.stack
            },
            
            // Connection diagnostics
            connection: {
                clientConnected: this.client.connected,
                transport: this._getCurrentTransport(),
                networkOnline: navigator.onLine,
                lastSuccessfulConnection: this._getLastSuccessfulConnection()
            },
            
            // Browser diagnostics
            browser: {
                webSocketSupport: 'WebSocket' in window,
                socketIOSupport: typeof io !== 'undefined',
                cookiesEnabled: navigator.cookieEnabled,
                localStorageAvailable: this._testLocalStorage()
            },
            
            // Network diagnostics
            network: this._runNetworkDiagnostics(),
            
            // Suggestions
            suggestions: this._generateTroubleshootingSuggestions(error),
            
            timestamp: Date.now()
        };
        
        this.diagnostics.troubleshootingData = diagnostics;
    }
    
    /**
     * Generate troubleshooting suggestions
     */
    _generateTroubleshootingSuggestions(error) {
        const suggestions = [];
        const errorMessage = error.message || error.toString();
        const lowerMessage = errorMessage.toLowerCase();
        
        // CORS-related suggestions
        if (lowerMessage.includes('cors') || lowerMessage.includes('cross-origin')) {
            suggestions.push({
                category: 'CORS',
                priority: 'high',
                title: 'CORS Configuration Issue',
                description: 'The server is blocking cross-origin requests',
                actions: [
                    'Verify you are accessing the application from the correct URL',
                    'Check if the server CORS configuration allows your origin',
                    'Try accessing via the same protocol (HTTP/HTTPS)',
                    'Contact the administrator to update CORS settings'
                ]
            });
        }
        
        // Authentication suggestions
        if (lowerMessage.includes('auth') || lowerMessage.includes('unauthorized')) {
            suggestions.push({
                category: 'Authentication',
                priority: 'high',
                title: 'Authentication Required',
                description: 'Your session may have expired or authentication is required',
                actions: [
                    'Try logging in again',
                    'Clear browser cookies and cache',
                    'Check if cookies are enabled in your browser',
                    'Verify your account has the necessary permissions'
                ]
            });
        }
        
        // Network suggestions
        if (lowerMessage.includes('network') || lowerMessage.includes('timeout')) {
            suggestions.push({
                category: 'Network',
                priority: 'medium',
                title: 'Network Connectivity Issue',
                description: 'There may be a network connectivity problem',
                actions: [
                    'Check your internet connection',
                    'Try refreshing the page',
                    'Disable VPN or proxy if using one',
                    'Try connecting from a different network'
                ]
            });
        }
        
        // Browser suggestions
        if (!navigator.onLine) {
            suggestions.push({
                category: 'Browser',
                priority: 'high',
                title: 'Browser Offline',
                description: 'Your browser reports being offline',
                actions: [
                    'Check your internet connection',
                    'Verify network settings',
                    'Try refreshing the page when back online'
                ]
            });
        }
        
        // Transport suggestions
        if (lowerMessage.includes('websocket') || lowerMessage.includes('transport')) {
            suggestions.push({
                category: 'Transport',
                priority: 'medium',
                title: 'WebSocket Transport Issue',
                description: 'The WebSocket transport method is having problems',
                actions: [
                    'The system will automatically try polling mode',
                    'Check if your firewall blocks WebSocket connections',
                    'Try disabling browser extensions that might interfere',
                    'Contact IT support if on a corporate network'
                ]
            });
        }
        
        return suggestions;
    }
    
    /**
     * Create debug panel UI
     */
    _createDebugPanel() {
        // Remove existing panel
        const existingPanel = document.getElementById('websocket-debug-panel');
        if (existingPanel) {
            existingPanel.remove();
        }
        
        const panel = document.createElement('div');
        panel.id = 'websocket-debug-panel';
        panel.className = `websocket-debug-panel ${this.options.panelPosition} ${this.options.panelSize}`;
        
        panel.innerHTML = `
            <div class="debug-panel-header">
                <h6><i class="bi bi-bug me-2"></i>WebSocket Debug</h6>
                <div class="debug-panel-controls">
                    <button type="button" class="btn btn-sm btn-outline-light" id="debug-export-btn" title="Export Debug Data">
                        <i class="bi bi-download"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-light" id="debug-clear-btn" title="Clear Debug Data">
                        <i class="bi bi-trash"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-light" id="debug-minimize-btn" title="Minimize Panel">
                        <i class="bi bi-dash"></i>
                    </button>
                    <button type="button" class="btn-close btn-close-white" id="debug-close-btn"></button>
                </div>
            </div>
            <div class="debug-panel-content">
                <div class="debug-tabs">
                    <button class="debug-tab active" data-tab="overview">Overview</button>
                    <button class="debug-tab" data-tab="events">Events</button>
                    <button class="debug-tab" data-tab="performance">Performance</button>
                    <button class="debug-tab" data-tab="diagnostics">Diagnostics</button>
                </div>
                
                <div class="debug-tab-content">
                    <div id="debug-overview" class="debug-tab-panel active">
                        <div class="debug-section">
                            <h6>Connection Status</h6>
                            <div id="debug-connection-status" class="debug-status-grid">
                                <div class="status-item">
                                    <span class="label">Status:</span>
                                    <span class="value" id="status-connected">Unknown</span>
                                </div>
                                <div class="status-item">
                                    <span class="label">Transport:</span>
                                    <span class="value" id="status-transport">Unknown</span>
                                </div>
                                <div class="status-item">
                                    <span class="label">Latency:</span>
                                    <span class="value" id="status-latency">-</span>
                                </div>
                                <div class="status-item">
                                    <span class="label">Uptime:</span>
                                    <span class="value" id="status-uptime">-</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="debug-section">
                            <h6>System Information</h6>
                            <div id="debug-system-info" class="debug-info-grid">
                                <div class="info-item">
                                    <span class="label">Browser:</span>
                                    <span class="value" id="info-browser">-</span>
                                </div>
                                <div class="info-item">
                                    <span class="label">Platform:</span>
                                    <span class="value" id="info-platform">-</span>
                                </div>
                                <div class="info-item">
                                    <span class="label">Online:</span>
                                    <span class="value" id="info-online">-</span>
                                </div>
                                <div class="info-item">
                                    <span class="label">WebSocket:</span>
                                    <span class="value" id="info-websocket">-</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div id="debug-events" class="debug-tab-panel">
                        <div class="debug-section">
                            <h6>Recent Events</h6>
                            <div id="debug-events-list" class="debug-events-container">
                                <!-- Events will be populated here -->
                            </div>
                        </div>
                    </div>
                    
                    <div id="debug-performance" class="debug-tab-panel">
                        <div class="debug-section">
                            <h6>Performance Metrics</h6>
                            <div id="debug-performance-charts" class="debug-charts-container">
                                <!-- Charts will be populated here -->
                            </div>
                        </div>
                    </div>
                    
                    <div id="debug-diagnostics" class="debug-tab-panel">
                        <div class="debug-section">
                            <h6>Troubleshooting</h6>
                            <div id="debug-troubleshooting" class="debug-troubleshooting-container">
                                <!-- Troubleshooting info will be populated here -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(panel);
        this.ui.panel = panel;
        
        // Setup panel interactions
        this._setupDebugPanelInteractions();
        
        // Add CSS
        this._addDebugPanelCSS();
        
        // Initial update
        this._updateDebugPanel();
    }
    
    /**
     * Setup debug panel interactions
     */
    _setupDebugPanelInteractions() {
        if (!this.ui.panel) return;
        
        // Tab switching
        const tabs = this.ui.panel.querySelectorAll('.debug-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                this._switchDebugTab(tabName);
            });
        });
        
        // Control buttons
        const exportBtn = document.getElementById('debug-export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportDebugData();
            });
        }
        
        const clearBtn = document.getElementById('debug-clear-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearDebugData();
            });
        }
        
        const minimizeBtn = document.getElementById('debug-minimize-btn');
        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', () => {
                this._togglePanelMinimize();
            });
        }
        
        const closeBtn = document.getElementById('debug-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.hideDebugPanel();
            });
        }
    }
    
    /**
     * Update debug panel content
     */
    _updateDebugPanel() {
        if (!this.ui.panel) return;
        
        // Update overview tab
        this._updateOverviewTab();
        
        // Update events tab
        this._updateEventsTab();
        
        // Update performance tab
        this._updatePerformanceTab();
        
        // Update diagnostics tab
        this._updateDiagnosticsTab();
    }
    
    /**
     * Update overview tab
     */
    _updateOverviewTab() {
        // Connection status
        const statusConnected = document.getElementById('status-connected');
        if (statusConnected) {
            statusConnected.textContent = this.client.connected ? 'Connected' : 'Disconnected';
            statusConnected.className = `value ${this.client.connected ? 'text-success' : 'text-danger'}`;
        }
        
        const statusTransport = document.getElementById('status-transport');
        if (statusTransport) {
            statusTransport.textContent = this._getCurrentTransport();
        }
        
        const statusLatency = document.getElementById('status-latency');
        if (statusLatency) {
            const latency = this._getLatestLatency();
            statusLatency.textContent = latency ? `${latency}ms` : '-';
        }
        
        const statusUptime = document.getElementById('status-uptime');
        if (statusUptime) {
            statusUptime.textContent = this._getConnectionUptime();
        }
        
        // System information
        const infoBrowser = document.getElementById('info-browser');
        if (infoBrowser) {
            infoBrowser.textContent = this._getBrowserName();
        }
        
        const infoPlatform = document.getElementById('info-platform');
        if (infoPlatform) {
            infoPlatform.textContent = navigator.platform;
        }
        
        const infoOnline = document.getElementById('info-online');
        if (infoOnline) {
            infoOnline.textContent = navigator.onLine ? 'Yes' : 'No';
            infoOnline.className = `value ${navigator.onLine ? 'text-success' : 'text-danger'}`;
        }
        
        const infoWebSocket = document.getElementById('info-websocket');
        if (infoWebSocket) {
            const supported = 'WebSocket' in window;
            infoWebSocket.textContent = supported ? 'Supported' : 'Not Supported';
            infoWebSocket.className = `value ${supported ? 'text-success' : 'text-danger'}`;
        }
    }
    
    /**
     * Update events tab
     */
    _updateEventsTab() {
        const eventsList = document.getElementById('debug-events-list');
        if (!eventsList) return;
        
        // Get recent events (last 20)
        const recentEvents = this.diagnostics.connectionHistory.slice(-20).reverse();
        
        eventsList.innerHTML = recentEvents.map(event => `
            <div class="debug-event-item">
                <div class="event-header">
                    <span class="event-type ${this._getEventTypeClass(event.type)}">${event.type}</span>
                    <span class="event-time">${new Date(event.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="event-data">
                    ${this._formatEventData(event.data)}
                </div>
            </div>
        `).join('');
    }
    
    /**
     * Update performance tab
     */
    _updatePerformanceTab() {
        const chartsContainer = document.getElementById('debug-performance-charts');
        if (!chartsContainer) return;
        
        // Simple text-based metrics for now
        const latencyHistory = this.diagnostics.performanceMetrics.latencyHistory || [];
        const recentLatency = latencyHistory.slice(-10);
        
        chartsContainer.innerHTML = `
            <div class="performance-metric">
                <h6>Latency (Last 10 measurements)</h6>
                <div class="metric-values">
                    ${recentLatency.map(metric => `
                        <span class="metric-value">${metric.value}ms</span>
                    `).join('')}
                </div>
                <div class="metric-stats">
                    <span>Avg: ${this._calculateAverageLatency()}ms</span>
                    <span>Min: ${this._getMinLatency()}ms</span>
                    <span>Max: ${this._getMaxLatency()}ms</span>
                </div>
            </div>
        `;
    }
    
    /**
     * Update diagnostics tab
     */
    _updateDiagnosticsTab() {
        const troubleshootingContainer = document.getElementById('debug-troubleshooting');
        if (!troubleshootingContainer) return;
        
        const troubleshooting = this.diagnostics.troubleshootingData;
        
        if (!troubleshooting || !troubleshooting.suggestions) {
            troubleshootingContainer.innerHTML = '<p class="text-muted">No troubleshooting data available</p>';
            return;
        }
        
        troubleshootingContainer.innerHTML = `
            <div class="troubleshooting-suggestions">
                ${troubleshooting.suggestions.map(suggestion => `
                    <div class="suggestion-item priority-${suggestion.priority}">
                        <div class="suggestion-header">
                            <i class="bi ${this._getSuggestionIcon(suggestion.category)}"></i>
                            <strong>${suggestion.title}</strong>
                            <span class="priority-badge">${suggestion.priority}</span>
                        </div>
                        <p class="suggestion-description">${suggestion.description}</p>
                        <ul class="suggestion-actions">
                            ${suggestion.actions.map(action => `<li>${action}</li>`).join('')}
                        </ul>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    /**
     * Helper methods for UI updates
     */
    _getCurrentTransport() {
        if (this.client.io && this.client.io.engine && this.client.io.engine.transport) {
            return this.client.io.engine.transport.name;
        }
        return 'unknown';
    }
    
    _getLatestLatency() {
        const latencyHistory = this.diagnostics.performanceMetrics.latencyHistory || [];
        return latencyHistory.length > 0 ? latencyHistory[latencyHistory.length - 1].value : null;
    }
    
    _getConnectionUptime() {
        const connectEvent = this.diagnostics.connectionHistory
            .slice()
            .reverse()
            .find(event => event.type === 'connect');
        
        if (!connectEvent || !this.client.connected) return '-';
        
        const uptime = Date.now() - connectEvent.timestamp;
        return this._formatDuration(uptime);
    }
    
    _getBrowserName() {
        const userAgent = navigator.userAgent;
        if (userAgent.includes('Chrome')) return 'Chrome';
        if (userAgent.includes('Firefox')) return 'Firefox';
        if (userAgent.includes('Safari')) return 'Safari';
        if (userAgent.includes('Edge')) return 'Edge';
        return 'Unknown';
    }
    
    _getEventTypeClass(type) {
        const classMap = {
            connect: 'text-success',
            disconnect: 'text-warning',
            connect_error: 'text-danger',
            reconnect: 'text-info',
            recovery_event: 'text-primary'
        };
        return classMap[type] || 'text-muted';
    }
    
    _formatEventData(data) {
        if (!data || typeof data !== 'object') {
            return String(data || '');
        }
        
        return Object.entries(data)
            .map(([key, value]) => `<span class="data-item"><strong>${key}:</strong> ${value}</span>`)
            .join(' ');
    }
    
    _getSuggestionIcon(category) {
        const iconMap = {
            CORS: 'bi-shield-exclamation',
            Authentication: 'bi-person-lock',
            Network: 'bi-wifi-off',
            Browser: 'bi-browser-chrome',
            Transport: 'bi-arrow-repeat'
        };
        return iconMap[category] || 'bi-info-circle';
    }
    
    _calculateAverageLatency() {
        const latencyHistory = this.diagnostics.performanceMetrics.latencyHistory || [];
        if (latencyHistory.length === 0) return 0;
        
        const sum = latencyHistory.reduce((acc, metric) => acc + metric.value, 0);
        return Math.round(sum / latencyHistory.length);
    }
    
    _getMinLatency() {
        const latencyHistory = this.diagnostics.performanceMetrics.latencyHistory || [];
        if (latencyHistory.length === 0) return 0;
        
        return Math.min(...latencyHistory.map(metric => metric.value));
    }
    
    _getMaxLatency() {
        const latencyHistory = this.diagnostics.performanceMetrics.latencyHistory || [];
        if (latencyHistory.length === 0) return 0;
        
        return Math.max(...latencyHistory.map(metric => metric.value));
    }
    
    _formatDuration(ms) {
        const seconds = Math.floor(ms / 1000);
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
     * Utility methods for data collection and testing
     */
    _getConnectionInfo() {
        if ('connection' in navigator) {
            const conn = navigator.connection;
            return {
                effectiveType: conn.effectiveType,
                downlink: conn.downlink,
                rtt: conn.rtt,
                saveData: conn.saveData
            };
        }
        return null;
    }
    
    _getPerformanceInfo() {
        if ('performance' in window && performance.memory) {
            return {
                usedJSHeapSize: performance.memory.usedJSHeapSize,
                totalJSHeapSize: performance.memory.totalJSHeapSize,
                jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
            };
        }
        return null;
    }
    
    _testLocalStorage() {
        try {
            const test = 'test';
            localStorage.setItem(test, test);
            localStorage.removeItem(test);
            return true;
        } catch (e) {
            return false;
        }
    }
    
    _testSessionStorage() {
        try {
            const test = 'test';
            sessionStorage.setItem(test, test);
            sessionStorage.removeItem(test);
            return true;
        } catch (e) {
            return false;
        }
    }
    
    _getNetworkConnection() {
        if ('connection' in navigator) {
            const conn = navigator.connection;
            return {
                effectiveType: conn.effectiveType,
                downlink: conn.downlink,
                rtt: conn.rtt,
                saveData: conn.saveData,
                type: conn.type
            };
        }
        return null;
    }
    
    _runNetworkTests() {
        // Simple connectivity test
        fetch(window.location.origin + '/favicon.ico', { 
            method: 'HEAD',
            cache: 'no-cache'
        })
        .then(response => {
            this.diagnostics.networkInfo.connectivity = {
                status: 'success',
                responseTime: Date.now(),
                statusCode: response.status
            };
        })
        .catch(error => {
            this.diagnostics.networkInfo.connectivity = {
                status: 'failed',
                error: error.message
            };
        });
    }
    
    _runNetworkDiagnostics() {
        return {
            online: navigator.onLine,
            protocol: window.location.protocol,
            hostname: window.location.hostname,
            port: window.location.port,
            connection: this._getNetworkConnection(),
            timestamp: Date.now()
        };
    }
    
    _categorizeError(error) {
        const message = error.message || error.toString();
        const lowerMessage = message.toLowerCase();
        
        if (lowerMessage.includes('cors')) return 'CORS';
        if (lowerMessage.includes('auth')) return 'Authentication';
        if (lowerMessage.includes('network')) return 'Network';
        if (lowerMessage.includes('timeout')) return 'Timeout';
        if (lowerMessage.includes('transport')) return 'Transport';
        
        return 'Unknown';
    }
    
    _getLastSuccessfulConnection() {
        const connectEvent = this.diagnostics.connectionHistory
            .slice()
            .reverse()
            .find(event => event.type === 'connect');
        
        return connectEvent ? new Date(connectEvent.timestamp).toISOString() : null;
    }
    
    _collectPerformanceSnapshot() {
        // Collect current performance metrics
        const snapshot = {
            timestamp: Date.now(),
            connected: this.client.connected,
            transport: this._getCurrentTransport(),
            memoryUsage: this._getPerformanceInfo(),
            connectionCount: this.diagnostics.connectionHistory.length
        };
        
        // Store snapshot (could be used for trends)
        if (!this.diagnostics.performanceSnapshots) {
            this.diagnostics.performanceSnapshots = [];
        }
        
        this.diagnostics.performanceSnapshots.push(snapshot);
        
        // Limit snapshots
        if (this.diagnostics.performanceSnapshots.length > 100) {
            this.diagnostics.performanceSnapshots.shift();
        }
    }
    
    _performLatencyTest() {
        if (!this.client.connected) return;
        
        const startTime = Date.now();
        this.client.emit('ping', startTime, (response) => {
            const latency = Date.now() - startTime;
            this._recordPerformanceMetric('latency', latency);
        });
    }
    
    _generateEventId() {
        return `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Public API methods
     */
    
    /**
     * Show debug panel
     */
    showDebugPanel() {
        if (!this.ui.panel) {
            this._createDebugPanel();
        }
        
        this.ui.panel.style.display = 'block';
        this._updateDebugPanel();
    }
    
    /**
     * Hide debug panel
     */
    hideDebugPanel() {
        if (this.ui.panel) {
            this.ui.panel.style.display = 'none';
        }
    }
    
    /**
     * Toggle debug panel visibility
     */
    toggleDebugPanel() {
        if (!this.ui.panel) {
            this.showDebugPanel();
        } else {
            const isVisible = this.ui.panel.style.display !== 'none';
            if (isVisible) {
                this.hideDebugPanel();
            } else {
                this.showDebugPanel();
            }
        }
    }
    
    /**
     * Switch debug tab
     */
    _switchDebugTab(tabName) {
        // Update tab buttons
        const tabs = this.ui.panel.querySelectorAll('.debug-tab');
        tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });
        
        // Update tab panels
        const panels = this.ui.panel.querySelectorAll('.debug-tab-panel');
        panels.forEach(panel => {
            panel.classList.toggle('active', panel.id === `debug-${tabName}`);
        });
    }
    
    /**
     * Toggle panel minimize
     */
    _togglePanelMinimize() {
        const content = this.ui.panel.querySelector('.debug-panel-content');
        const minimizeBtn = document.getElementById('debug-minimize-btn');
        
        if (content && minimizeBtn) {
            const isMinimized = content.style.display === 'none';
            content.style.display = isMinimized ? 'block' : 'none';
            
            const icon = minimizeBtn.querySelector('i');
            if (icon) {
                icon.className = isMinimized ? 'bi bi-dash' : 'bi bi-plus';
            }
        }
    }
    
    /**
     * Export debug data
     */
    exportDebugData(format = 'json') {
        const debugData = {
            timestamp: new Date().toISOString(),
            diagnostics: this.diagnostics,
            clientInfo: {
                connected: this.client.connected,
                transport: this._getCurrentTransport()
            },
            exportFormat: format
        };
        
        let content, mimeType, filename;
        
        switch (format) {
            case 'json':
                content = JSON.stringify(debugData, null, 2);
                mimeType = 'application/json';
                filename = `websocket-debug-${Date.now()}.json`;
                break;
                
            case 'csv':
                content = this._convertToCSV(debugData);
                mimeType = 'text/csv';
                filename = `websocket-debug-${Date.now()}.csv`;
                break;
                
            case 'txt':
                content = this._convertToText(debugData);
                mimeType = 'text/plain';
                filename = `websocket-debug-${Date.now()}.txt`;
                break;
                
            default:
                throw new Error(`Unsupported export format: ${format}`);
        }
        
        // Create and download file
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        
        URL.revokeObjectURL(url);
    }
    
    /**
     * Clear debug data
     */
    clearDebugData() {
        this.diagnostics.connectionHistory = [];
        this.diagnostics.performanceMetrics = {
            latencyHistory: [],
            throughputHistory: [],
            errorRateHistory: []
        };
        this.diagnostics.troubleshootingData = {};
        
        if (this.diagnostics.performanceSnapshots) {
            this.diagnostics.performanceSnapshots = [];
        }
        
        this._updateDebugPanel();
    }
    
    /**
     * Get diagnostic summary
     */
    getDiagnosticSummary() {
        return {
            connectionStatus: this.client.connected,
            transport: this._getCurrentTransport(),
            eventCount: this.diagnostics.connectionHistory.length,
            latestLatency: this._getLatestLatency(),
            browserInfo: this.diagnostics.browserInfo,
            networkInfo: this.diagnostics.networkInfo,
            troubleshooting: this.diagnostics.troubleshootingData
        };
    }
    
    /**
     * Convert debug data to CSV format
     */
    _convertToCSV(data) {
        const events = data.diagnostics.connectionHistory;
        const headers = ['Timestamp', 'Type', 'Data'];
        
        const rows = events.map(event => [
            new Date(event.timestamp).toISOString(),
            event.type,
            JSON.stringify(event.data)
        ]);
        
        return [headers, ...rows]
            .map(row => row.map(cell => `"${cell}"`).join(','))
            .join('\n');
    }
    
    /**
     * Convert debug data to text format
     */
    _convertToText(data) {
        let text = `WebSocket Debug Report\n`;
        text += `Generated: ${data.timestamp}\n\n`;
        
        text += `Connection Status: ${data.clientInfo.connected ? 'Connected' : 'Disconnected'}\n`;
        text += `Transport: ${data.clientInfo.transport}\n\n`;
        
        text += `Browser Information:\n`;
        Object.entries(data.diagnostics.browserInfo).forEach(([key, value]) => {
            text += `  ${key}: ${JSON.stringify(value)}\n`;
        });
        
        text += `\nConnection Events:\n`;
        data.diagnostics.connectionHistory.forEach(event => {
            text += `  ${new Date(event.timestamp).toISOString()} - ${event.type}: ${JSON.stringify(event.data)}\n`;
        });
        
        return text;
    }
    
    /**
     * Add debug panel CSS
     */
    _addDebugPanelCSS() {
        if (document.getElementById('websocket-debug-panel-css')) return;
        
        const css = `
            .websocket-debug-panel {
                position: fixed;
                z-index: 1070;
                background: rgba(33, 37, 41, 0.95);
                color: white;
                border-radius: 0.5rem;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                backdrop-filter: blur(10px);
                font-size: 0.875rem;
                font-family: 'Courier New', monospace;
            }
            
            .websocket-debug-panel.bottom-right {
                bottom: 1rem;
                right: 1rem;
                width: 400px;
                max-height: 500px;
            }
            
            .websocket-debug-panel.compact {
                width: 300px;
                max-height: 300px;
                font-size: 0.75rem;
            }
            
            .websocket-debug-panel.large {
                width: 600px;
                max-height: 700px;
                font-size: 0.9rem;
            }
            
            .debug-panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
                background: rgba(0, 0, 0, 0.2);
                border-radius: 0.5rem 0.5rem 0 0;
            }
            
            .debug-panel-header h6 {
                margin: 0;
                font-size: 0.9rem;
                font-weight: 600;
            }
            
            .debug-panel-controls {
                display: flex;
                gap: 0.25rem;
            }
            
            .debug-panel-controls .btn {
                padding: 0.25rem 0.5rem;
                font-size: 0.75rem;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            
            .debug-panel-content {
                max-height: 400px;
                overflow: hidden;
            }
            
            .debug-tabs {
                display: flex;
                background: rgba(0, 0, 0, 0.2);
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .debug-tab {
                flex: 1;
                padding: 0.5rem;
                background: none;
                border: none;
                color: rgba(255, 255, 255, 0.7);
                font-size: 0.75rem;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .debug-tab:hover {
                background: rgba(255, 255, 255, 0.1);
                color: white;
            }
            
            .debug-tab.active {
                background: rgba(255, 255, 255, 0.2);
                color: white;
                font-weight: 600;
            }
            
            .debug-tab-content {
                height: 350px;
                overflow-y: auto;
            }
            
            .debug-tab-panel {
                display: none;
                padding: 0.75rem;
            }
            
            .debug-tab-panel.active {
                display: block;
            }
            
            .debug-section {
                margin-bottom: 1rem;
            }
            
            .debug-section h6 {
                margin: 0 0 0.5rem 0;
                font-size: 0.8rem;
                color: #ffc107;
                border-bottom: 1px solid rgba(255, 193, 7, 0.3);
                padding-bottom: 0.25rem;
            }
            
            .debug-status-grid,
            .debug-info-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.5rem;
            }
            
            .status-item,
            .info-item {
                display: flex;
                justify-content: space-between;
                padding: 0.25rem;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 0.25rem;
            }
            
            .label {
                font-weight: 500;
                color: rgba(255, 255, 255, 0.8);
            }
            
            .value {
                font-family: monospace;
                font-size: 0.8em;
            }
            
            .debug-events-container {
                max-height: 250px;
                overflow-y: auto;
            }
            
            .debug-event-item {
                margin-bottom: 0.5rem;
                padding: 0.5rem;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 0.25rem;
                border-left: 3px solid #0d6efd;
            }
            
            .event-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.25rem;
            }
            
            .event-type {
                font-weight: 600;
                font-size: 0.75rem;
                text-transform: uppercase;
            }
            
            .event-time {
                font-size: 0.7rem;
                color: rgba(255, 255, 255, 0.6);
            }
            
            .event-data {
                font-size: 0.7rem;
                color: rgba(255, 255, 255, 0.8);
            }
            
            .data-item {
                display: inline-block;
                margin-right: 0.5rem;
            }
            
            .debug-charts-container {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 0.25rem;
                padding: 0.75rem;
            }
            
            .performance-metric h6 {
                color: #20c997;
                margin-bottom: 0.5rem;
            }
            
            .metric-values {
                display: flex;
                flex-wrap: wrap;
                gap: 0.25rem;
                margin-bottom: 0.5rem;
            }
            
            .metric-value {
                background: rgba(32, 201, 151, 0.2);
                color: #20c997;
                padding: 0.125rem 0.25rem;
                border-radius: 0.125rem;
                font-size: 0.7rem;
            }
            
            .metric-stats {
                display: flex;
                gap: 1rem;
                font-size: 0.7rem;
                color: rgba(255, 255, 255, 0.8);
            }
            
            .debug-troubleshooting-container {
                max-height: 250px;
                overflow-y: auto;
            }
            
            .suggestion-item {
                margin-bottom: 0.75rem;
                padding: 0.75rem;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 0.25rem;
                border-left: 3px solid #ffc107;
            }
            
            .suggestion-item.priority-high {
                border-left-color: #dc3545;
            }
            
            .suggestion-item.priority-medium {
                border-left-color: #fd7e14;
            }
            
            .suggestion-item.priority-low {
                border-left-color: #6c757d;
            }
            
            .suggestion-header {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-bottom: 0.5rem;
            }
            
            .priority-badge {
                background: rgba(255, 193, 7, 0.2);
                color: #ffc107;
                padding: 0.125rem 0.25rem;
                border-radius: 0.125rem;
                font-size: 0.6rem;
                text-transform: uppercase;
                font-weight: 600;
            }
            
            .suggestion-description {
                margin: 0 0 0.5rem 0;
                font-size: 0.8rem;
                color: rgba(255, 255, 255, 0.9);
            }
            
            .suggestion-actions {
                margin: 0;
                padding-left: 1rem;
                font-size: 0.75rem;
                color: rgba(255, 255, 255, 0.8);
            }
            
            .suggestion-actions li {
                margin-bottom: 0.25rem;
            }
            
            /* Scrollbar styling */
            .debug-tab-content::-webkit-scrollbar,
            .debug-events-container::-webkit-scrollbar,
            .debug-troubleshooting-container::-webkit-scrollbar {
                width: 6px;
            }
            
            .debug-tab-content::-webkit-scrollbar-track,
            .debug-events-container::-webkit-scrollbar-track,
            .debug-troubleshooting-container::-webkit-scrollbar-track {
                background: rgba(255, 255, 255, 0.1);
            }
            
            .debug-tab-content::-webkit-scrollbar-thumb,
            .debug-events-container::-webkit-scrollbar-thumb,
            .debug-troubleshooting-container::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 3px;
            }
            
            /* Mobile responsiveness */
            @media (max-width: 768px) {
                .websocket-debug-panel {
                    width: calc(100vw - 2rem) !important;
                    max-width: 350px;
                    font-size: 0.75rem;
                }
                
                .debug-status-grid,
                .debug-info-grid {
                    grid-template-columns: 1fr;
                }
                
                .debug-panel-controls .btn {
                    padding: 0.125rem 0.25rem;
                    font-size: 0.7rem;
                }
            }
        `;
        
        const style = document.createElement('style');
        style.id = 'websocket-debug-panel-css';
        style.textContent = css;
        document.head.appendChild(style);
    }
    
    /**
     * Destroy diagnostics system
     */
    destroy() {
        // Clear intervals
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }
        
        if (this.latencyInterval) {
            clearInterval(this.latencyInterval);
        }
        
        if (this.chartInterval) {
            clearInterval(this.chartInterval);
        }
        
        // Remove event listeners
        if (this.client) {
            this.client.off('connect');
            this.client.off('disconnect');
            this.client.off('connect_error');
            this.client.off('reconnect');
            this.client.off('pong');
        }
        
        // Remove UI elements
        if (this.ui.panel && this.ui.panel.parentNode) {
            this.ui.panel.parentNode.removeChild(this.ui.panel);
        }
        
        // Remove CSS
        const css = document.getElementById('websocket-debug-panel-css');
        if (css) {
            css.remove();
        }
        
        console.log('WebSocket Debug Diagnostics destroyed');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketDebugDiagnostics;
} else if (typeof window !== 'undefined') {
    window.WebSocketDebugDiagnostics = WebSocketDebugDiagnostics;
}