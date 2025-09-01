// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * WebSocket Transport Optimizer
 * 
 * Optimizes Socket.IO transport selection and upgrade behavior to minimize
 * "Invalid websocket upgrade" errors while maintaining functionality.
 */

class WebSocketTransportOptimizer {
    constructor() {
        this.browserInfo = this.detectBrowser();
        this.connectionHistory = this.loadConnectionHistory();
        this.optimizedConfig = null;
        
        console.log('🔧 WebSocket Transport Optimizer initialized');
        console.log(`📱 Browser: ${this.browserInfo.name} ${this.browserInfo.version}`);
        
        this.generateOptimizedConfig();
    }
    
    /**
     * Detect browser type and version for optimization
     */
    detectBrowser() {
        const userAgent = navigator.userAgent;
        let browser = { name: 'unknown', version: 'unknown', engine: 'unknown' };
        
        // Safari/WebKit detection
        if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
            browser.name = 'safari';
            browser.engine = 'webkit';
            const match = userAgent.match(/Version\/([0-9.]+)/);
            browser.version = match ? match[1] : 'unknown';
        }
        // Chrome detection
        else if (userAgent.includes('Chrome')) {
            browser.name = 'chrome';
            browser.engine = 'blink';
            const match = userAgent.match(/Chrome\/([0-9.]+)/);
            browser.version = match ? match[1] : 'unknown';
        }
        // Firefox detection
        else if (userAgent.includes('Firefox')) {
            browser.name = 'firefox';
            browser.engine = 'gecko';
            const match = userAgent.match(/Firefox\/([0-9.]+)/);
            browser.version = match ? match[1] : 'unknown';
        }
        
        return browser;
    }
    
    /**
     * Load connection history from localStorage
     */
    loadConnectionHistory() {
        try {
            const history = localStorage.getItem('websocket_connection_history');
            return history ? JSON.parse(history) : {
                websocketSuccessRate: 0,
                pollingSuccessRate: 100,
                lastWebSocketSuccess: null,
                upgradeFailures: 0,
                totalConnections: 0
            };
        } catch (error) {
            console.warn('Failed to load connection history:', error);
            return {
                websocketSuccessRate: 0,
                pollingSuccessRate: 100,
                lastWebSocketSuccess: null,
                upgradeFailures: 0,
                totalConnections: 0
            };
        }
    }
    
    /**
     * Save connection history to localStorage
     */
    saveConnectionHistory() {
        try {
            localStorage.setItem('websocket_connection_history', JSON.stringify(this.connectionHistory));
        } catch (error) {
            console.warn('Failed to save connection history:', error);
        }
    }
    
    /**
     * Generate optimized configuration based on browser and history
     */
    generateOptimizedConfig() {
        const config = {
            transports: ['polling', 'websocket'], // Default order
            upgrade: true,
            rememberUpgrade: false, // Don't remember failed upgrades
            forceNew: false,
            timeout: 20000,
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            autoConnect: true
        };
        
        // Browser-specific optimizations
        switch (this.browserInfo.name) {
            case 'safari':
                // Safari has stricter WebSocket validation
                config.transports = ['polling']; // Start with polling only
                config.upgrade = false; // Disable upgrade initially
                config.timeout = 30000; // Longer timeout for Safari
                config.reconnectionDelay = 2000; // Slower reconnection
                console.log('🍎 Safari detected - using polling-first configuration');
                break;
                
            case 'chrome':
                // Chrome handles WebSocket well, but be conservative
                config.transports = ['polling', 'websocket'];
                config.upgrade = true;
                config.rememberUpgrade = false; // Don't remember to avoid issues
                console.log('🌐 Chrome detected - using balanced configuration');
                break;
                
            case 'firefox':
                // Firefox has good WebSocket support
                config.transports = ['polling', 'websocket'];
                config.upgrade = true;
                config.rememberUpgrade = false;
                console.log('🦊 Firefox detected - using standard configuration');
                break;
                
            default:
                // Conservative configuration for unknown browsers
                config.transports = ['polling'];
                config.upgrade = false;
                console.log('❓ Unknown browser - using conservative polling-only configuration');
        }
        
        // History-based optimizations
        if (this.connectionHistory.upgradeFailures > 3) {
            console.log('⚠️ Multiple upgrade failures detected - disabling WebSocket upgrade');
            config.transports = ['polling'];
            config.upgrade = false;
        }
        
        if (this.connectionHistory.websocketSuccessRate < 50 && this.connectionHistory.totalConnections > 5) {
            console.log('📊 Low WebSocket success rate - preferring polling transport');
            config.transports = ['polling'];
            config.upgrade = false;
        }
        
        // Environment-based optimizations
        if (window.location.protocol === 'https:') {
            // HTTPS environments typically have better WebSocket support
            if (config.transports.includes('websocket')) {
                console.log('🔒 HTTPS detected - WebSocket should work better');
            }
        }
        
        // Mobile detection
        if (/Mobi|Android/i.test(navigator.userAgent)) {
            console.log('📱 Mobile device detected - using conservative configuration');
            config.transports = ['polling'];
            config.upgrade = false;
            config.timeout = 30000;
            config.reconnectionDelay = 3000;
        }
        
        this.optimizedConfig = config;
        console.log('⚙️ Generated optimized WebSocket configuration:', config);
        
        return config;
    }
    
    /**
     * Get optimized configuration for Socket.IO client
     */
    getOptimizedConfig() {
        return { ...this.optimizedConfig };
    }
    
    /**
     * Record connection attempt result
     */
    recordConnectionAttempt(transport, success, error = null) {
        this.connectionHistory.totalConnections++;
        
        if (transport === 'websocket') {
            if (success) {
                this.connectionHistory.lastWebSocketSuccess = Date.now();
                // Recalculate success rate
                const wsAttempts = this.connectionHistory.totalConnections;
                this.connectionHistory.websocketSuccessRate = 
                    ((this.connectionHistory.websocketSuccessRate * (wsAttempts - 1)) + 100) / wsAttempts;
            } else {
                this.connectionHistory.upgradeFailures++;
                // Recalculate success rate
                const wsAttempts = this.connectionHistory.totalConnections;
                this.connectionHistory.websocketSuccessRate = 
                    (this.connectionHistory.websocketSuccessRate * (wsAttempts - 1)) / wsAttempts;
            }
        } else if (transport === 'polling') {
            if (success) {
                const pollingAttempts = this.connectionHistory.totalConnections;
                this.connectionHistory.pollingSuccessRate = 
                    ((this.connectionHistory.pollingSuccessRate * (pollingAttempts - 1)) + 100) / pollingAttempts;
            }
        }
        
        // Save updated history
        this.saveConnectionHistory();
        
        // Log the attempt
        const status = success ? '✅' : '❌';
        console.log(`${status} Connection attempt: ${transport} - ${success ? 'Success' : 'Failed'}`);
        
        if (error) {
            console.log(`   Error: ${error}`);
        }
        
        // Update configuration if needed
        this.updateConfigurationBasedOnHistory();
    }
    
    /**
     * Update configuration based on connection history
     */
    updateConfigurationBasedOnHistory() {
        const shouldUpdate = 
            this.connectionHistory.upgradeFailures > 2 ||
            (this.connectionHistory.websocketSuccessRate < 30 && this.connectionHistory.totalConnections > 3);
            
        if (shouldUpdate) {
            console.log('📈 Updating configuration based on connection history');
            this.generateOptimizedConfig();
        }
    }
    
    /**
     * Enable WebSocket upgrade after successful polling connection
     */
    enableWebSocketUpgrade(socket) {
        if (!socket || !this.optimizedConfig) return;
        
        // Wait for stable polling connection before attempting upgrade
        setTimeout(() => {
            if (socket.connected && socket.io.engine.transport.name === 'polling') {
                console.log('🔄 Attempting WebSocket upgrade after stable polling connection');
                
                try {
                    // Enable upgrade
                    socket.io.engine.upgrade();
                } catch (error) {
                    console.warn('WebSocket upgrade attempt failed:', error);
                    this.recordConnectionAttempt('websocket', false, error.message);
                }
            }
        }, 5000); // Wait 5 seconds for stable connection
    }
    
    /**
     * Monitor socket connection and record results
     */
    monitorSocket(socket) {
        if (!socket) return;
        
        // Monitor connection events
        socket.on('connect', () => {
            const transport = socket.io.engine.transport.name;
            console.log(`🔗 Connected via ${transport} transport`);
            this.recordConnectionAttempt(transport, true);
        });
        
        socket.on('connect_error', (error) => {
            console.log('❌ Connection error:', error);
            this.recordConnectionAttempt('unknown', false, error.message);
        });
        
        socket.on('disconnect', (reason) => {
            console.log('🔌 Disconnected:', reason);
        });
        
        // Monitor transport changes
        socket.io.engine.on('upgrade', () => {
            const transport = socket.io.engine.transport.name;
            console.log(`⬆️ Upgraded to ${transport} transport`);
            this.recordConnectionAttempt('websocket', true);
        });
        
        socket.io.engine.on('upgradeError', (error) => {
            console.log('❌ Upgrade error:', error);
            this.recordConnectionAttempt('websocket', false, error.message);
        });
        
        // Enable upgrade for conservative configurations
        if (this.optimizedConfig.transports.includes('polling') && 
            !this.optimizedConfig.transports.includes('websocket')) {
            this.enableWebSocketUpgrade(socket);
        }
    }
    
    /**
     * Get connection statistics
     */
    getConnectionStats() {
        return {
            browser: this.browserInfo,
            history: this.connectionHistory,
            currentConfig: this.optimizedConfig,
            recommendations: this.getRecommendations()
        };
    }
    
    /**
     * Get recommendations based on current state
     */
    getRecommendations() {
        const recommendations = [];
        
        if (this.connectionHistory.upgradeFailures > 5) {
            recommendations.push('Consider disabling WebSocket upgrade due to frequent failures');
        }
        
        if (this.connectionHistory.websocketSuccessRate < 20 && this.connectionHistory.totalConnections > 10) {
            recommendations.push('WebSocket transport appears unreliable in this environment');
        }
        
        if (this.browserInfo.name === 'safari' && this.connectionHistory.upgradeFailures > 2) {
            recommendations.push('Safari WebSocket issues detected - using polling-only mode');
        }
        
        if (recommendations.length === 0) {
            recommendations.push('Transport configuration appears optimal');
        }
        
        return recommendations;
    }
    
    /**
     * Reset connection history (for testing)
     */
    resetHistory() {
        this.connectionHistory = {
            websocketSuccessRate: 0,
            pollingSuccessRate: 100,
            lastWebSocketSuccess: null,
            upgradeFailures: 0,
            totalConnections: 0
        };
        this.saveConnectionHistory();
        this.generateOptimizedConfig();
        console.log('🔄 Connection history reset');
    }
}

// Auto-initialize if enabled
if (typeof window !== 'undefined') {
    // Initialize transport optimizer
    window.webSocketTransportOptimizer = new WebSocketTransportOptimizer();
    
    // Provide global access to optimized configuration
    window.getOptimizedWebSocketConfig = function() {
        return window.webSocketTransportOptimizer.getOptimizedConfig();
    };
    
    // Provide monitoring function
    window.monitorWebSocketConnection = function(socket) {
        return window.webSocketTransportOptimizer.monitorSocket(socket);
    };
    
    console.log('🔧 WebSocket Transport Optimizer ready');
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketTransportOptimizer;
}